#ifndef PRIMARY_VIRTUALSECONDARY_H_
#define PRIMARY_VIRTUALSECONDARY_H_

#include <string>

#include "managedsecondary.h"
#include "utilities/types.h"

namespace Primary {

class VirtualSecondaryConfig : public ManagedSecondaryConfig {
 public:
  VirtualSecondaryConfig() : ManagedSecondaryConfig(Type) {}
  VirtualSecondaryConfig(const Json::Value& json_config);

  static VirtualSecondaryConfig create_from_file(const boost::filesystem::path& file_full_path);
  void dump(const boost::filesystem::path& file_full_path) const;

 public:
  static const char* const Type;
};

class VirtualSecondary : public ManagedSecondary {
 public:
  explicit VirtualSecondary(Primary::VirtualSecondaryConfig sconfig_in);
  ~VirtualSecondary() override = default;

 private:
  bool storeFirmware(const std::string& target_name, const std::string& content) override;
  bool getFirmwareInfo(std::string* target_name, size_t& target_len, std::string* sha256hash) override;
};

}  // namespace Primary

#endif  // PRIMARY_VIRTUALSECONDARY_H_
