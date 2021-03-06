set(SOURCES aktualizr_version.cc
            apiqueue.cc
            dequeue_buffer.cc
            sockaddr_io.cc
            timer.cc
            types.cc
            utils.cc)

set(HEADERS apiqueue.h
            aktualizr_version.h
            config_utils.h
            dequeue_buffer.h
            exceptions.h
            fault_injection.h
            sockaddr_io.h
            timer.h
            types.h
            utils.h)

set_property(SOURCE aktualizr_version.cc PROPERTY COMPILE_DEFINITIONS AKTUALIZR_VERSION="${AKTUALIZR_VERSION}")

add_library(utilities OBJECT ${SOURCES})
include(AddAktualizrTest)

add_aktualizr_test(NAME dequeue_buffer SOURCES dequeue_buffer_test.cc)
add_aktualizr_test(NAME timer SOURCES timer_test.cc)
add_aktualizr_test(NAME types SOURCES types_test.cc)
add_aktualizr_test(NAME utils SOURCES utils_test.cc PROJECT_WORKING_DIRECTORY)

aktualizr_source_file_checks(${SOURCES} ${HEADERS} ${TEST_SOURCES})
