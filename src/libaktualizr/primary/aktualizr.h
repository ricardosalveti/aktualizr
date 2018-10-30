#ifndef AKTUALIZR_H_
#define AKTUALIZR_H_

#include <atomic>
#include <memory>

#include <gtest/gtest.h>
#include <boost/signals2.hpp>

#include "config/config.h"
#include "sotauptaneclient.h"
#include "storage/invstorage.h"
#include "uptane/secondaryinterface.h"
#include "utilities/events.h"

/**
 * This class provides the main APIs necessary for launching and controlling
 * libaktualizr.
 */
class Aktualizr {
 public:
  /** Aktualizr requires a configuration object. Examples can be found in the
   *  config directory. */
  explicit Aktualizr(Config& config);
  Aktualizr(const Aktualizr&) = delete;
  Aktualizr& operator=(const Aktualizr&) = delete;

  /*
   * Initialize aktualizr. Any secondaries should be added before making this
   * call. This will provision with the server if required. This must be called
   * before using any other aktualizr functions except AddSecondary.
   */
  void Initialize();

  /**
   * Run aktualizr indefinitely until Shutdown is called. Intended to be used
   * with the Full \ref RunningMode setting. You may want to run this on its own
   * thread.
   */
  int RunForever();

  /**
   * Asynchronously shut aktualizr down if it is running indefinitely with the
   * Full \ref RunningMode.
   */
  void Shutdown();

  /**
   * Check for campaigns.
   * Campaigns are a concept outside of Uptane, and allow for user approval of
   * updates before the contents of the update are known.
   * @return Data about available campaigns.
   */
  CampaignCheckResult CampaignCheck();

  /**
   * Accept a campaign for the current device.
   * Campaigns are a concept outside of Uptane, and allow for user approval of
   * updates before the contents of the update are known.
   * @param campaign_id Campaign ID as provided by CampaignCheck.
   */
  void CampaignAccept(const std::string& campaign_id);

  /**
   * Send local device data to the server.
   * This includes network status, installed packages, hardware etc.
   */
  void SendDeviceData();

  /**
   * Fetch Uptane metadata and check for updates.
   * This collects a client manifest, PUTs it to the director, updates the
   * Uptane metadata (including root and targets), and then checks the metadata
   * for target updates.
   * @return Information about available updates.
   */
  UpdateCheckResult CheckUpdates();

  /**
   * Download targets.
   * @param updates Vector of targets to download as provided by CheckUpdates.
   * @return Information about download results.
   */
  DownloadResult Download(const std::vector<Uptane::Target>& updates);

  /**
   * Install targets.
   * @param updates Vector of targets to install as provided by CheckUpdates or
   * Download.
   * @return Information about installation results.
   */
  InstallResult Install(const std::vector<Uptane::Target>& updates);

  /**
   * Pause a download current in progress.
   * @return Information about pause results.
   */
  PauseResult Pause();

  /**
   * Resume a paused download.
   * @return Information about resume results.
   */
  PauseResult Resume();

  /**
   * Synchronously run an uptane cycle.
   *
   * Behaviour depends on the configured running mode (full cycle, check and
   * download or check and install)
   */
  void UptaneCycle();

  /**
   * Add new secondary to aktualizr. Must be called before Initialize.
   * @param secondary An object to perform installation on a secondary ECU.
   */
  void AddSecondary(const std::shared_ptr<Uptane::SecondaryInterface>& secondary);

  /**
   * Provide a function to receive event notifications.
   * @param handler a function that can receive event objects.
   * @return a signal connection object, which can be disconnected if desired.
   */
  boost::signals2::connection SetSignalHandler(std::function<void(std::shared_ptr<event::BaseEvent>)>& handler);

 private:
  FRIEND_TEST(Aktualizr, FullNoUpdates);
  FRIEND_TEST(Aktualizr, FullWithUpdates);
  FRIEND_TEST(Aktualizr, FullMultipleSecondaries);
  FRIEND_TEST(Aktualizr, CheckWithUpdates);
  FRIEND_TEST(Aktualizr, DownloadWithUpdates);
  FRIEND_TEST(Aktualizr, InstallWithUpdates);
  FRIEND_TEST(Aktualizr, CampaignCheck);
  FRIEND_TEST(Aktualizr, FullNoCorrelationId);
  Aktualizr(Config& config, std::shared_ptr<INvStorage> storage_in, std::shared_ptr<SotaUptaneClient> uptane_client_in,
            std::shared_ptr<event::Channel> sig_in);
  void systemSetup();

  Config& config_;
  std::shared_ptr<INvStorage> storage_;
  std::shared_ptr<SotaUptaneClient> uptane_client_;
  std::shared_ptr<event::Channel> sig_;
  std::atomic<bool> shutdown_ = {false};
};

#endif  // AKTUALIZR_H_