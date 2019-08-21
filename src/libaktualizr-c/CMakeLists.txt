SET(LIB_TARGET aktualizr-c)
SET(TEST_TARGET test-app)

add_library(${LIB_TARGET} SHARED libaktualizr-c.cc)
target_include_directories(${LIB_TARGET} PUBLIC ${PROJECT_SOURCE_DIR}/include)
target_link_libraries(${LIB_TARGET} PRIVATE aktualizr_static_lib ${AKTUALIZR_EXTERNAL_LIBS})

add_executable(${TEST_TARGET} EXCLUDE_FROM_ALL test-app.c)
target_link_libraries(${TEST_TARGET} PRIVATE ${LIB_TARGET})
set_target_properties(${TEST_TARGET} PROPERTIES SKIP_BUILD_RPATH TRUE)

add_dependencies(build_tests ${TEST_TARGET})
add_test(NAME test_c_api COMMAND $<TARGET_FILE:${TEST_TARGET}>)


aktualizr_source_file_checks(libaktualizr-c.cc test-app.c)
