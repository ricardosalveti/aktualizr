#include <stdlib.h>
#include <iostream>
#include <sstream>
#include <string>

#include <boost/filesystem.hpp>
#include <boost/program_options.hpp>
#include "json/json.h"

#include "bootstrap.h"
#include "crypto.h"
#include "httpclient.h"
#include "logger.h"
#include "utils.h"

namespace bpo = boost::program_options;

const std::string pkey_file = "pkey.pem";
const std::string cert_file = "client.pem";
const std::string ca_file = "root.crt";

void check_info_options(const bpo::options_description &description, const bpo::variables_map &vm) {
  if (vm.count("help") != 0) {
    std::cout << description << '\n';
    exit(EXIT_SUCCESS);
  }
  if (vm.count("version") != 0) {
    std::cout << "Current aktualizr_cert_provider version is: " << AKTUALIZR_VERSION << "\n";
    exit(EXIT_SUCCESS);
  }
}

bpo::variables_map parse_options(int argc, char *argv[]) {
  bpo::options_description description("aktualizr_cert_provider command line options");
  // clang-format off
  description.add_options()
      ("help,h", "print usage")
      ("version,v", "Current aktualizr_cert_provider version")
      ("credentials,c", bpo::value<std::string>()->required(), "zipped credentials file")
      ("target,t", bpo::value<std::string>(), "target device to scp credentials to (or [user@]host)")
      ("port,p", bpo::value<int>(), "target port")
      ("directory,d", bpo::value<std::string>()->default_value("/var/sota/token"), "directory on target to write credentials to")
      ("root-ca,r", "provide root CA")
      ("local,l", bpo::value<std::string>(), "local directory to write credentials to");
  // clang-format on

  bpo::variables_map vm;
  std::vector<std::string> unregistered_options;
  try {
    bpo::basic_parsed_options<char> parsed_options =
        bpo::command_line_parser(argc, argv).options(description).allow_unregistered().run();
    bpo::store(parsed_options, vm);
    check_info_options(description, vm);
    bpo::notify(vm);
    unregistered_options = bpo::collect_unrecognized(parsed_options.options, bpo::include_positional);
    if (vm.count("help") == 0 && !unregistered_options.empty()) {
      std::cout << description << "\n";
      exit(EXIT_FAILURE);
    }
  } catch (const bpo::required_option &ex) {
    // print the error and append the default commandline option description
    std::cout << ex.what() << std::endl << description;
    exit(EXIT_SUCCESS);
  } catch (const bpo::error &ex) {
    check_info_options(description, vm);

    // print the error message to the standard output too, as the user provided
    // a non-supported commandline option
    std::cout << ex.what() << '\n';

    // set the returnValue, thereby ctest will recognize
    // that something went wrong
    exit(EXIT_FAILURE);
  }

  return vm;
}

int main(int argc, char *argv[]) {
  loggerInit();
  loggerSetSeverity(static_cast<LoggerLevels>(2));

  bpo::variables_map commandline_map = parse_options(argc, argv);

  std::string credentials_path = commandline_map["credentials"].as<std::string>();
  std::string target = "";
  if (commandline_map.count("target") != 0) {
    target = commandline_map["target"].as<std::string>();
  }
  int port = 0;
  if (commandline_map.count("port") != 0) {
    port = (commandline_map["port"].as<int>());
  }
  std::string directory = commandline_map["directory"].as<std::string>();
  bool provide_ca = commandline_map.count("root-ca") != 0;
  std::string local_dir = "";
  if (commandline_map.count("local") != 0) {
    local_dir = commandline_map["local"].as<std::string>();
  }

  TemporaryFile tmp_pkey_file(pkey_file);
  TemporaryFile tmp_cert_file(cert_file);
  TemporaryFile tmp_ca_file(ca_file);

  std::string device_id = Utils::genPrettyName();
  std::cout << "Random device ID is " << device_id << "\n";

  Bootstrap boot(credentials_path, "");
  HttpClient http;
  Json::Value data;
  data["deviceId"] = device_id;
  data["ttl"] = 36000;
  std::string serverUrl = Bootstrap::readServerUrl(credentials_path);

  std::cout << "Provisioning against server...\n";
  http.setCerts(boot.getCa(), kFile, boot.getCert(), kFile, boot.getPkey(), kFile);
  HttpResponse response = http.post(serverUrl + "/devices", data);
  if (!response.isOk()) {
    Json::Value resp_code = response.getJson()["code"];
    if (resp_code.isString() && resp_code.asString() == "device_already_registered") {
      std::cout << "Device ID" << device_id << "is occupied.\n";
      return -1;
    } else {
      std::cout << "Provisioning failed, response: " << response.body << "\n";
      return -1;
    }
  }
  std::cout << "...success\n";

  std::string pkey;
  std::string cert;
  std::string ca;
  FILE *device_p12 = fmemopen(const_cast<char *>(response.body.c_str()), response.body.size(), "rb");
  if (!Crypto::parseP12(device_p12, "", &pkey, &cert, &ca)) {
    return -1;
  }
  fclose(device_p12);

  tmp_pkey_file.PutContents(pkey);
  tmp_cert_file.PutContents(cert);
  if (provide_ca) {
    tmp_ca_file.PutContents(ca);
  }

  if (!local_dir.empty()) {
    std::cout << "Writing client certificate and keys to " << local_dir << " ...\n";
    if (boost::filesystem::exists(local_dir)) {
      boost::filesystem::remove(local_dir + "/" + pkey_file);
      boost::filesystem::remove(local_dir + "/" + cert_file);
      if (provide_ca) {
        boost::filesystem::remove(local_dir + "/" + ca_file);
      }
    } else {
      boost::filesystem::create_directory(local_dir);
    }
    boost::filesystem::copy_file(tmp_pkey_file.PathString(), local_dir + "/" + pkey_file);
    boost::filesystem::copy_file(tmp_cert_file.PathString(), local_dir + "/" + cert_file);
    if (provide_ca) {
      boost::filesystem::copy_file(tmp_ca_file.PathString(), local_dir + "/" + ca_file);
    }
    std::cout << "...success\n";
  }

  if (!target.empty()) {
    std::cout << "Copying client certificate and keys to " << target << ":" << directory;
    if (port) {
      std::cout << " on port " << port;
    }
    std::cout << " ...\n";
    std::ostringstream ssh_prefix;
    std::ostringstream scp_prefix;
    ssh_prefix << "ssh ";
    scp_prefix << "scp ";
    if (port) {
      ssh_prefix << "-p " << port << " ";
      scp_prefix << "-P " << port << " ";
    }

    int ret = system((ssh_prefix.str() + target + " mkdir -p " + directory).c_str());
    if (ret != 0) {
      std::cout << "Error connecting to target device: " << ret << "\n";
      return -1;
    }

    ret = system(
        (scp_prefix.str() + tmp_pkey_file.PathString() + " " + target + ":" + directory + "/" + pkey_file).c_str());
    if (ret != 0) {
      std::cout << "Error copying files to target device: " << ret << "\n";
    }

    ret = system(
        (scp_prefix.str() + tmp_cert_file.PathString() + " " + target + ":" + directory + "/" + cert_file).c_str());
    if (ret != 0) {
      std::cout << "Error copying files to target device: " << ret << "\n";
    }

    if (provide_ca) {
      ret = system(
          (scp_prefix.str() + tmp_ca_file.PathString() + " " + target + ":" + directory + "/" + ca_file).c_str());
      if (ret != 0) {
        std::cout << "Error copying files to target device: " << ret << "\n";
      }
    }

    std::cout << "...success\n";
  }

  return 0;
}