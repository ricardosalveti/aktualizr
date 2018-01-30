#include "aktualizr.h"

#include "timer.h"

#include <openssl/evp.h>
#include <openssl/rand.h>
#include <sodium.h>

#include "channel.h"
#include "commands.h"
#include "events.h"
#include "eventsinterpreter.h"
#include "fsstorage.h"
#include "httpclient.h"

#ifdef BUILD_OSTREE
#include "ostree.h"
#include "sotauptaneclient.h"
#endif

Aktualizr::Aktualizr(const Config &config) : config_(config) {
  if (sodium_init() == -1) {  // Note that sodium_init doesn't require a matching 'sodium_deinit'
    throw std::runtime_error("Unable to initialize libsodium");
  }

  LOG_TRACE << "Seeding random number generator from /dev/random...";
  Timer timer;
  unsigned int seed;
  std::ifstream urandom("/dev/urandom", std::ios::in | std::ios::binary);
  urandom.read(reinterpret_cast<char *>(&seed), sizeof(seed));
  urandom.close();
  std::srand(seed);  // seeds pseudo random generator with random number
  LOG_TRACE << "... seeding complete in " << timer;
}

int Aktualizr::run() {
  command::Channel commands_channel;
  event::Channel events_channel;

  EventsInterpreter events_interpreter(config_, &events_channel, &commands_channel);

  // run events interpreter in background
  events_interpreter.interpret();

#ifdef BUILD_OSTREE
  // TODO: compile unconditionally
  boost::shared_ptr<INvStorage> storage = INvStorage::newStorage(config_.storage);
  storage->importData(config_.import);
  HttpClient http;
  Uptane::Repository repo(config_, storage, http);
  SotaUptaneClient uptane_client(config_, &events_channel, repo, storage, http);
  uptane_client.runForever(&commands_channel);
#else
  LOG_ERROR << "OSTree support is disabled, but currently required for UPTANE";
  return EXIT_FAILURE;
#endif

  return EXIT_SUCCESS;
}
