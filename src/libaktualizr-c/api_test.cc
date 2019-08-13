#include <gtest/gtest.h>

#include <iostream>
#include <string>
#include <random>
#include <thread>

#include <boost/process.hpp>

#include "uptane_test_common.h"

#include "config/config.h"
#include "logging/logging.h"
#include "test_utils.h"

boost::filesystem::path aktualizr_repo_path;
static std::string server = "http://127.0.0.1:";
static boost::filesystem::path sysroot;

TEST(Aktualizr, ApiTest) {
  TemporaryDirectory temp_dir;
  Config conf = UptaneTestCommon::makeTestConfig(temp_dir, server);
  conf.pacman.type = PackageManager::kOstree;
  conf.pacman.sysroot = sysroot.string();
  conf.pacman.ostree_server = treehub_server;
  conf.pacman.os = "dummy-os";
  conf.provision.device_id = "device_id";
  conf.provision.ecu_registration_endpoint = server + "/director/ecus";
  conf.tls.server = server;

  LOG_INFO << "conf: " << conf;

}

#ifndef __NO_MAIN__
int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);

  logger_init();

  if (argc != 3) {
    std::cerr << "Error: " << argv[0] << " requires the path to the aktualizr-repo utility "
              << "and an OStree sysroot\n";
    return EXIT_FAILURE;
  }
  aktualizr_repo_path = argv[1];

  TemporaryDirectory meta_dir;

  std::string port = TestUtils::getFreePort();
  server += port;
  boost::process::child http_server_process("tests/fake_http_server/fake_test_server.py", port, "-m", meta_dir.Path());
  TestUtils::waitForServer(server + "/");

  Process akt_repo(aktualizr_repo_path.string());
  akt_repo.run({"generate", "--path", meta_dir.PathString(), "--correlationid", "abc123"});
  akt_repo.run({"image", "--path", meta_dir.PathString(), "--targetname", "update_1.0", "--targetsha256", new_rev,
                "--targetlength", "0", "--targetformat", "OSTREE", "--hwid", "primary_hw"});
  akt_repo.run({"addtarget", "--path", meta_dir.PathString(), "--targetname", "update_1.0", "--hwid", "primary_hw",
                "--serial", "CA:FE:A6:D2:84:9D"});
  akt_repo.run({"signtargets", "--path", meta_dir.PathString(), "--correlationid", "abc123"});
  LOG_INFO << akt_repo.lastStdOut();
  // Work around inconsistent directory naming.
  Utils::copyDir(meta_dir.Path() / "repo/image", meta_dir.Path() / "repo/repo");

  return RUN_ALL_TESTS();
}
#endif  // __NO_MAIN__
