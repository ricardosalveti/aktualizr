SET(LIB_TARGET aktualizr-c)
SET(TEST_TARGET test-app)

add_library(${LIB_TARGET} SHARED libaktualizr-c.cc)
target_include_directories(${LIB_TARGET} PUBLIC ${PROJECT_SOURCE_DIR}/include)
target_link_libraries(${LIB_TARGET} PRIVATE aktualizr_static_lib ${AKTUALIZR_EXTERNAL_LIBS})

add_executable(${TEST_TARGET} EXCLUDE_FROM_ALL test-app.c)
target_link_libraries(${TEST_TARGET} PRIVATE ${LIB_TARGET})
set_target_properties(${TEST_TARGET} PROPERTIES SKIP_BUILD_RPATH TRUE)

add_dependencies(build_tests ${TEST_TARGET})

if (${CMAKE_VERSION} VERSION_LESS "3.7.2")
  message("Cmake version < 3.7.2, skipping C API test")
else()
  add_test(NAME generateUptaneRepo COMMAND uptane-generator generate --path ./metadata --correlationid abc123)
  add_test(NAME generateUptaneRepo COMMAND uptane-generator generate --path "./metadata")
  #  add_test(NAME startServer COMMAND "echo 2")
  # gadd_test(NAME stopServer COMMAND "echo 3")
  add_test(NAME generateUptaneRepo COMMAND uptane-generator image --path meta_dir.PathString(), --targetname", "update_1.0", "--targetsha256", new_rev,"--targetlength", "0", "--targetformat", "OSTREE", "--hwid", "primary_hw")
  add_test(NAME generateUptaneRepo COMMAND uptane-generator addtarget --path meta_dir.PathString(), "--targetname", "update_1.0", "--hwid", "primary_hw","--serial", "CA:FE:A6:D2:84:9D")
  add_test(NAME generateUptaneRepo COMMAND uptane-generator "signtargets", "--path", meta_dir.PathString(), "--correlationid", "abc123"});
  add_test(NAME deleteUptaneRepo COMMAND rm -rf "./metadata")
  add_test(NAME testApi COMMAND sleep 100)

  set_tests_properties(generateUptaneRepo PROPERTIES FIXTURES_SETUP FakeBackend)
  #  set_tests_properties(startServer PROPERTIES FIXTURES_SETUP FakeBackend)
  #  set_tests_properties(startServer PROPERTIES DEPENDS generateUptaneRepo)

  #  set_tests_properties(stopServer PROPERTIES FIXTURES_CLEANUP FakeBackend)
  set_tests_properties(deleteUptaneRepo PROPERTIES FIXTURES_CLEANUP FakeBackend)
  #  set_tests_properties(deleteUptaneRepo PROPERTIES DEPENDS stopServer)

  set_tests_properties(testApi PROPERTIES FIXTURES_REQUIRED FakeBackend)
endif()


#  add_test(NAME test_c_api COMMAND $<TARGET_FILE:${TEST_TARGET}>)
aktualizr_source_file_checks(libaktualizr-c.cc test-app.c)
