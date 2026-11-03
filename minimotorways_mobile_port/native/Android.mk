LOCAL_PATH := $(call my-dir)

include $(CLEAR_VARS)
LOCAL_MODULE    := dpcPlatform
LOCAL_SRC_FILES := libdpcPlatform.c
LOCAL_CFLAGS    := -std=c99 -O2 -fvisibility=hidden
LOCAL_LDLIBS    := -lm
LOCAL_LDFLAGS   := -Wl,-z,max-page-size=16384
include $(BUILD_SHARED_LIBRARY)

include $(CLEAR_VARS)
LOCAL_MODULE    := decompressAudio
LOCAL_SRC_FILES := libdecompressAudio.c
LOCAL_CFLAGS    := -std=c99 -O2 -fvisibility=hidden
LOCAL_LDFLAGS   := -Wl,-z,max-page-size=16384
include $(BUILD_SHARED_LIBRARY)
