cmake_minimum_required(VERSION 3.18)
project(MiniMotorwaysAndroidNative C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_library(dpcPlatform SHARED libdpcPlatform.c)
target_link_libraries(dpcPlatform PRIVATE m)

add_library(decompressAudio SHARED libdecompressAudio.c)

# Align ELF segments to 16 KB page boundaries (required by Android 15+ / Google Play)
if(ANDROID OR UNIX AND NOT APPLE)
    target_link_options(dpcPlatform PRIVATE "-Wl,-z,max-page-size=16384")
    target_link_options(decompressAudio PRIVATE "-Wl,-z,max-page-size=16384")
endif()
