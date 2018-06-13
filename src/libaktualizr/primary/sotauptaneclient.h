#include <json/json.h>
#include <atomic>
#include <map>
#include <string>
#include <utility>
#include <vector>

#include "bootloader/bootloader.h"
#include "commands.h"
#include "config/config.h"
#include "events.h"
#include "http/httpclient.h"
#include "package_manager/packagemanagerinterface.h"
#include "storage/invstorage.h"
#include "uptane/fetcher.h"
#include "uptane/ipsecondarydiscovery.h"
#include "uptane/secondaryinterface.h"
#include "uptane/uptanerepository.h"

class SotaUptaneClient {
 public:
  SotaUptaneClient(Config &config_in, std::shared_ptr<event::Channel> events_channel_in, Uptane::Repository &repo,
                   std::shared_ptr<INvStorage> storage_in, HttpInterface &http_client, const Bootloader &bootloader_in);

  bool initialize();
  void getUpdateRequests();
  void runForever(const std::shared_ptr<command::Channel> &commands_channel);
  Json::Value AssembleManifest();
  std::string secondaryTreehubCredentials() const;

  // ecu_serial => secondary*
  std::map<Uptane::EcuSerial, std::shared_ptr<Uptane::SecondaryInterface> > secondaries;

 private:
  bool isInstalled(const Uptane::Target &target);
  std::vector<Uptane::Target> findForEcu(const std::vector<Uptane::Target> &targets, const Uptane::EcuSerial &ecu_id);
  data::InstallOutcome PackageInstall(const Uptane::Target &target);
  void PackageInstallSetResult(const Uptane::Target &target);
  void reportHwInfo();
  void reportInstalledPackages();
  void schedulePoll(const std::shared_ptr<command::Channel> &commands_channel);
  void reportNetworkInfo();
  void initSecondaries();
  void verifySecondaries();
  void sendMetadataToEcus(std::vector<Uptane::Target> targets);
  void sendImagesToEcus(std::vector<Uptane::Target> targets);
  bool hasPendingUpdates(const Json::Value &manifests);
  bool putManifest();

  Config &config;
  std::shared_ptr<event::Channel> events_channel;
  Uptane::Repository &uptane_repo;
  std::shared_ptr<INvStorage> storage;
  std::shared_ptr<PackageManagerInterface> pacman;
  HttpInterface &http;
  Uptane::Fetcher uptane_fetcher;
  const Bootloader &bootloader;
  int last_targets_version;
  Json::Value operation_result;
  std::atomic<bool> shutdown = {false};
  Json::Value last_network_info_reported;
};

class SerialCompare {
 public:
  explicit SerialCompare(Uptane::EcuSerial target_in) : target(std::move(target_in)) {}
  bool operator()(std::pair<Uptane::EcuSerial, Uptane::HardwareIdentifier> &in) { return (in.first == target); }

 private:
  Uptane::EcuSerial target;
};