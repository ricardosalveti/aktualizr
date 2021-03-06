cmake_minimum_required(VERSION 2.8)

if(LIBUPTINY_MACHINE)
	if(${LIBUPTINY_MACHINE} STREQUAL "kea128")
		find_path(
			NXP_TOOLCHAIN_PATH
			NAMES Cross_Tools/gcc-arm-none-eabi-4_9/bin/arm-none-eabi-gcc
			HINTS $ENV{HOME}/NXP/S32DS_ARM_v1.3
			)
		message("Using NXP Toolchain in ${NXP_TOOLCHAIN_PATH}")

		# Cross-compilation options
		set(CMAKE_SYSTEM_NAME Generic)
		SET(CMAKE_CROSSCOMPILING 1)
		set(CMAKE_C_COMPILER_WORKS 1)
		set(CMAKE_SYSTEM_PROCESSOR cortex-m0plus)
		set(CMAKE_C_COMPILER ${NXP_TOOLCHAIN_PATH}/Cross_Tools/gcc-arm-none-eabi-4_9/bin/arm-none-eabi-gcc)
		set(CMAKE_ASM_COMPILER ${NXP_TOOLCHAIN_PATH}/Cross_Tools/gcc-arm-none-eabi-4_9/bin/arm-none-eabi-gcc)

		set(KEA128LIB_PREFIX machine/kea128/drivers)
		set(KEA128LIB_SOURCES ${KEA128LIB_PREFIX}/src/system_SKEAZ1284.c
			${KEA128LIB_PREFIX}/src/systimer.c
			${KEA128LIB_PREFIX}/src/led.c
			${KEA128LIB_PREFIX}/src/headlight.c
			${KEA128LIB_PREFIX}/src/can.c
			${KEA128LIB_PREFIX}/src/flash.c
			)

		include_directories(include ${NXP_TOOLCHAIN_PATH}/S32DS/arm_ewl2/EWL_C/include ${KEA128LIB_PREFIX}/include machine/kea128/app)

		set(LINKER_SCRIPT "${CMAKE_SOURCE_DIR}/partial/machine/kea128/SKEAZ_flash.ld")
                set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -T ${LINKER_SCRIPT} -Xlinker --gc-sections -Xlinker -Map=kea128.map")
		set(CMAKE_SHARED_LIBRARY_LINK_C_FLAGS)

		if(NOT DEFINED UPTANE_ECU_SERIAL)
			set(UPTANE_ECU_SERIAL 'TrudyGeneBailComradeYellowCone')
		endif()
		if(NOT DEFINED CAN_ID)
			set(CAN_ID "01")
		endif()
		if(NOT DEFINED UPTANE_HARDWARE_ID)
			set(UPTANE_HARDWARE_ID 'kea128')
		endif()
		set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -isystem ${NXP_TOOLCHAIN_PATH}/Cross_Tools/gcc-arm-none-eabi-4_9/arm-none-eabi/include -isystem ${NXP_TOOLCHAIN_PATH}/Cross_Tools/gcc-arm-none-eabi-4_9/lib/gcc/arm-none-eabi/4.9.3/include -D__START=__thumb_startup -DCLOCK_SETUP=1 -DCAN_ID=${CAN_ID} -DUPTANE_HARDWARE_ID=\\\"${UPTANE_HARDWARE_ID}\\\" -DUPTANE_ECU_SERIAL=\\\"${UPTANE_ECU_SERIAL}\\\" -DBYTE_ORDER_LITTLE -march=armv6-m -mtune=cortex-m0plus -mthumb --sysroot=${NXP_TOOLCHAIN_PATH}/S32DS/arm_ewl2 -specs=ewl_c_noio.specs -g -Os -std=c99 -Wno-main -ffunction-sections -fdata-sections")
		set(CMAKE_ASM_FLAGS "${CMAKE_ASM_FLAGS} -x assembler-with-cpp -D__START=__thumb_startup -Os -march=armv6-m -mtune=cortex-m0plus -mthumb -ffunction-sections -fdata-sections --sysroot=${NXP_TOOLCHAIN_PATH}/S32DS/arm_ewl2 -specs=ewl_c_noio.specs")

		add_library(kea128_lib ${KEA128LIB_SOURCES})
		add_executable(kea128_ms1.elf machine/kea128/app/ms1.c machine/kea128/app/flash_load.c machine/kea128/app/uds.c machine/kea128/app/isotp_allocate.c machine/kea128/app/script.c machine/kea128/app/example_session.c machine/kea128/app/script.c machine/kea128/app/isotp_dispatch.c  machine/kea128/startup/startup_SKEAZ1284.S)
		target_link_libraries(kea128_ms1.elf kea128_lib)
		target_link_libraries(kea128_ms1.elf isotp_lib)

	endif()
endif()

set(ED25519_SOURCES ed25519/ed25519.c
	ed25519/edsign.c
	ed25519/f25519.c
	ed25519/fprime.c
	ed25519/sha512.c
	)

set(ED25519_HEADERS ed25519/ed25519.h
	ed25519/edsign.h
	ed25519/f25519.h
	ed25519/fprime.h
	ed25519/sha512.h
	)

set(LIBUPTINY_SOURCES libuptiny/base64.c
	libuptiny/crypto_common.c
	libuptiny/firmware.c
	libuptiny/json_common.c
	libuptiny/manifest.c
	libuptiny/root_signed.c
	libuptiny/root.c
	libuptiny/signatures.c
	libuptiny/targets.c
	libuptiny/uptane_time.c
	libuptiny/utils.c
	)

set(LIBUPTINY_HEADERS libuptiny/base64.h
	libuptiny/common_data_api.h
	libuptiny/crypto_api.h
	libuptiny/crypto_common.h
	libuptiny/debug.h
	libuptiny/firmware.h
	libuptiny/json_common.h
	libuptiny/manifest.h
	libuptiny/root_signed.h
	libuptiny/root.h
	libuptiny/signatures.h
	libuptiny/state_api.h
	libuptiny/targets.h
	libuptiny/uptane_time.h
	libuptiny/utils.h
	)

set(LIBUPTINY_DEMO_SOURCES libuptiny-demo/common_data.c
	libuptiny-demo/crypto.c
	libuptiny-demo/flash.c
	libuptiny-demo/main.c
	libuptiny-demo/state.c
)

set(LIBUPTINY_DEMO_HEADERS libuptiny-demo/flash.h)

aktualizr_source_file_checks(${LIBUPTINY_SOURCES} ${LIBUPTINY_HEADERS})
aktualizr_source_file_checks(${LIBUPTINY_DEMO_SOURCES} ${LIBUPTINY_DEMO_HEADERS})

include_directories(. ed25519 libuptiny extern)
add_library(uptiny STATIC ${LIBUPTINY_SOURCES} libuptiny/jsmn.c)
target_compile_options(uptiny PUBLIC -Os -g -Wpedantic -Wno-long-long -DJSMN_STRICT -DJSMN_PARENT_LINKS)
set_source_files_properties(libuptiny/jsmn.c PROPERTIES COMPILE_FLAGS "-Wno-sign-conversion -Wno-switch-default")
set_source_files_properties(${ED25519_SOURCES} PROPERTIES COMPILE_FLAGS "-Wno-sign-compare -Wno-sign-conversion -Wno-conversion")

include_directories(extern/isotp-c/src extern/isotp-c/deps/bitfield-c/src/)
set(ISOTP_SOURCES extern/isotp-c/src/isotp/isotp.c
	extern/isotp-c/src/isotp/isotp.c
	extern/isotp-c/src/isotp/receive.c
	extern/isotp-c/src/isotp/send.c
	extern/isotp-c/deps/bitfield-c/src/bitfield/8byte.c
	extern/isotp-c/deps/bitfield-c/src/bitfield/bitarray.c
	extern/isotp-c/deps/bitfield-c/src/bitfield/bitfield.c
	)
add_library(isotp STATIC ${ISOTP_SOURCES})

if (CMAKE_CXX_COMPILER_ID MATCHES "GNU")
  target_compile_options(isotp PUBLIC -Os -g -Wno-long-long -Wno-conversion -Wno-sign-conversion -Wno-unused-parameter)
elseif (CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  target_compile_options(isotp PUBLIC -Os -g -Wno-long-long -Wno-conversion -Wno-sign-conversion -Wno-gnu-designator -Wno-unused-parameter)
endif ()

# Machine is not set, building tests to run in Linux environment
if(NOT LIBUPTINY_MACHINE)
	enable_testing()

        set(LIBUPTINY_TEST_ENVIRONMENT tests/test_state.cc tests/test_common_data.cc tests/test_crypto.cc ${ED25519_SOURCES})

        set_source_files_properties(${LIBUPTINY_TEST_ENVIRONMENT} tests/signatures_test.cc tests/root_signed_test.cc tests/root_test.cc tests/targets_test.cc PROPERTIES COMPILE_FLAGS "-Wno-sign-compare -Wno-sign-conversion -Wno-conversion")

        add_aktualizr_test(NAME tiny_base64 SOURCES libuptiny/base64.c tests/base64_test.cc)

        add_aktualizr_test(NAME tiny_signatures
                           SOURCES ${LIBUPTINY_TEST_ENVIRONMENT} tests/signatures_test.cc
                           LIBRARIES uptiny
                           PROJECT_WORKING_DIRECTORY)

        add_aktualizr_test(NAME tiny_signed_root
                           SOURCES ${LIBUPTINY_TEST_ENVIRONMENT} tests/root_signed_test.cc
                           LIBRARIES uptiny
                           PROJECT_WORKING_DIRECTORY)

        add_aktualizr_test(NAME tiny_root
                           SOURCES ${LIBUPTINY_TEST_ENVIRONMENT} tests/root_test.cc
                           LIBRARIES uptiny
                           PROJECT_WORKING_DIRECTORY)

        add_aktualizr_test(NAME tiny_targets
                           SOURCES ${LIBUPTINY_TEST_ENVIRONMENT} tests/targets_test.cc
                           LIBRARIES uptiny
                           PROJECT_WORKING_DIRECTORY)

        add_aktualizr_test(NAME tiny_firmware
                           SOURCES ${LIBUPTINY_TEST_ENVIRONMENT} tests/firmware_test.cc
                           LIBRARIES uptiny
                           PROJECT_WORKING_DIRECTORY)

        add_aktualizr_test(NAME tiny_update
                           SOURCES ${LIBUPTINY_TEST_ENVIRONMENT} tests/update_test.cc
                           LIBRARIES uptiny
                           PROJECT_WORKING_DIRECTORY)
endif()
