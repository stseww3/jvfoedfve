# `minimotorways_mobile_port` — Android Port Implementation & Patcher

This directory contains the Mini Motorways-specific Android porting code, native C99 plugin replacements, configuration files, and automated installer script.

## Contents

- `native/libdpcPlatform.c` — C99 implementation of all 31 exports of `dpcPlatform.dll` (20 `ExternPathfinding` graph/Dijkstra exports, `Fix64` Q32.32 `CalculateAcceleration`, G-Audio `GainMixToInterlaced` / `ResampleCopyFromInt16` / `LFOProcessChunk`, GIF `QuantizeImage`, and Apple/GameCenter/iCloud safe no-op stubs).
- `native/libdecompressAudio.c` — C99 implementation of `decompressAudioSample` and `EmptyFunction`, decoding the 608 length-prefixed 48 kHz 16-bit mono FLAC streams in `StreamingAssets/Sounds/48000/core.bytes` (verified 608/608 bit-exact MD5 against embedded FLAC `STREAMINFO` checksums).
- `native/CMakeLists.txt`, `native/Android.mk`, `native/Application.mk` — Android NDK build scripts with 16 KB page alignment (`-Wl,-z,max-page-size=16384`).
- `game_overrides/` — Drop-in C# classes for the `App` assembly:
  - `AndroidEnvironment.cs`
  - `AndroidHardwareCapabilities.cs`
  - `AndroidSoftwareCapabilities.cs` (`AndroidSoftwareCapabilities`, `AndroidReachability`, `NullSteamCloudSyncService`)
  - `TouchCameraAction_MobilePort.cs` (2-finger pinch zoom in/out + midpoint pan + 1-finger tap focus with Auto-Zoom toggle)
  - `AndroidGamepadInputSource.cs` (Razer Kishi V2 USB-C HID & Bluetooth gamepad support)
  - `AndroidAtomicFileStorage.cs` (crash-safe `.tmp` + `fsync` + `.bak` save system)
  - `AndroidAchievementHandler.cs` (offline + Google Play Games achievements + unlock toast overlay)
  - `AndroidPerformanceManager.cs` (30 / 60 / Auto 90 Hz frame rate + thermal/battery step-down)
  - `AndroidSafeAreaAndScaling.cs` (`SafeArea` with symmetric landscape insets for Samsung Galaxy A72 punch-hole cutout + `AndroidStreamingAssetsLoader` for `jar:file://` APK audio banks)
- `resources/AndroidConfig.json` — Feature toggle config enabling `AutoZoomEnabledOption` and `ControllerSensitivityOption`.
- `android_manifest/AndroidManifest.xml` — Landscape-locked Android manifest (`sensorLandscape`, `android.max_aspect = 2.4`).
- `tools/apply_mobile_port.py` — Automated audit and installation script.
- `tests/` — `.NET` integration test runner (`MiniMotorwaysMobilePort.Tests.csproj`).
