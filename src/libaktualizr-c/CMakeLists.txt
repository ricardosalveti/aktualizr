SET(LIB_TARGET_NAME aktualizr-c)
SET(APP_TARGET_NAME test-app)
SET(TEST_TARGET_NAME api_test)

add_library(${LIB_TARGET_NAME} SHARED libaktualizr-c.cc)
target_include_directories(${LIB_TARGET_NAME} PUBLIC ${PROJECT_SOURCE_DIR}/include)
target_link_libraries(${LIB_TARGET_NAME} PRIVATE aktualizr_static_lib ${AKTUALIZR_EXTERNAL_LIBS})

add_executable(${APP_TARGET_NAME} EXCLUDE_FROM_ALL test-app.c)
target_link_libraries(${APP_TARGET_NAME} PRIVATE ${LIB_TARGET_NAME})
set_target_properties(${APP_TARGET_NAME} PROPERTIES SKIP_BUILD_RPATH TRUE)

add_executable(${TEST_TARGET_NAME} EXCLUDE_FROM_ALL api_test.cc)
add_dependencies(${TEST_TARGET_NAME} ${APP_TARGET_NAME})
add_dependencies(build_tests ${TEST_TARGET_NAME})

aktualizr_source_file_checks(libaktualizr-c.cc test-app.c api_test.cc)
