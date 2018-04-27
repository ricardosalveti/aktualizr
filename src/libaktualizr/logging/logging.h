#ifndef SOTA_CLIENT_TOOLS_LOGGING_H_
#define SOTA_CLIENT_TOOLS_LOGGING_H_

#include <boost/log/trivial.hpp>
#include <boost/property_tree/ini_parser.hpp>

#include "utilities/config_utils.h"

/** Log an unrecoverable error */
#define LOG_FATAL BOOST_LOG_TRIVIAL(fatal)

/** Log that something has definitely gone wrong */
#define LOG_ERROR BOOST_LOG_TRIVIAL(error)

/** Warn about behaviour that is probably bad, but hasn't yet caused the system
 * to operate out of spec. */
#define LOG_WARNING BOOST_LOG_TRIVIAL(warning)

/** Report a user-visible message about operation */
#define LOG_INFO BOOST_LOG_TRIVIAL(info)

/** Report a message for developer debugging */
#define LOG_DEBUG BOOST_LOG_TRIVIAL(debug)

/** Report very-verbose debugging information */
#define LOG_TRACE BOOST_LOG_TRIVIAL(trace)

// Use like:
// curl_easy_setopt(curl_handle, CURLOPT_VERBOSE, get_curlopt_verbose());
int64_t get_curlopt_verbose();

void logger_init();

void logger_set_threshold(boost::log::trivial::severity_level threshold);

int loggerGetSeverity();

struct LoggerConfig {
  int loglevel{2};

  void updateFromPropertyTree(const boost::property_tree::ptree& pt);
  void writeToStream(std::ostream& out_stream) const;

  void setLogLevel();

 private:
  bool initialized{false};
};

#endif
