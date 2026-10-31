# Mini Motorways → Android: technical feasibility assessment and porting plan

> Scope: analysis only. Nothing was compiled, modified or redistributed. The plan below is
> written for whoever holds the rights (Codepoint Limited / Dinosaur Polo Club) or works under
> a licence from them, and assumes it is executed from the studio's real Unity project.
>
> Input analysed: the decompiled archive shared in the group (`MiniMotorways_source_private.zip`,
> SHA-256 `3d3e7c2aee2af8322b640d2e39476e225a33eb6ed39ded53a0a433e570eaf006`), plus the earlier
> backdoor audit of the original `Mini.Motorways.rar` (`../minimotorways_audit/README.md`).
> The archive itself is copyrighted code and is not included in this repository.

## 1. Verdict

| Question | Answer |
|---|---|
| Can the game technically run on Android? | **Yes, with high confidence**, from the real project. The codebase is already a multi-platform mobile codebase (it ships on iOS/tvOS through Apple Arcade): touch controls, gamepad support, phone/tablet UI layouts, safe-area handling, app-lifecycle saves and IL2CPP/AOT hints all exist. |
| Can a faithful port be produced from this archive? | **No.** It is not a Unity project: no scenes, prefabs, ScriptableObjects, art, audio, shaders or project settings. The two native libraries that run pathfinding, vehicle physics and audio DSP exist only as x86 Windows binaries/Ghidra pseudo-C. Platform `#if` branches were compiled out. |
| Is it lawful without permission? | **No.** Game code, assets and the "Mini Motorways" trademark belong to Codepoint Limited; Rewired and G-Audio are commercial libraries. See section 6. |
| How big is the Android work for the rights holder? | Moderate. Most mobile features already exist because of iOS. New work: an Android platform layer, ARM64 builds of two native plugins, pinch-to-zoom, a frame-rate option, save-write hardening, removal of Steam, and Android-specific services. |

## 2. What the archive contains (and what it does not)

| Present | Count / notes |
|---|---|
| ILSpy C# projects | 71 assemblies, 8,995 `.cs` files. Game code: `App` (1,277 files), `Assembly-CSharp(-firstpass)`, `WebCore`, `Version`, `DinoPoloClub.Analytics.Runtime`, `MOAnalytics.Runtime`, `FixedMath` |
| Third-party C# | `Rewired_Core`, `Rewired_Windows`, `Facepunch.Steamworks.Win32`, `Newtonsoft.Json`, `G-Audio`, `NaughtyAttributes.Core`, `MiniJson`, `Easing` |
| Unity packages / engine | URP, SRP Core, TextMeshPro, UGUI, Burst, Mathematics, MemoryProfiler; `UnityEngine.*Module`; Mono class libraries |
| Native code | Ghidra pseudo-C of `dpcPlatform.dll`, `decompressAudio.dll`, `lib_burst_generated.dll`, `Rewired_DirectInput.dll` (x86 Windows) |

| Missing (required to build the game) |
|---|
| Unity project: `Assets/`, `ProjectSettings/`, `Packages/manifest.json`, `.meta` GUIDs |
| Scenes, prefabs (including the per-device UI prefabs `InGameUI-Phone`, `InGameUI-Tablet`, `GameUpgradeScreen-*`, `GameOverScreen-*`), asset bundles |
| ScriptableObjects: `AchievementDatabase` (achievement names, descriptions, unlock data), feature configs (`SteamConfig`, `ArcadeConfig`, ...), visual constants and zoom parameters, map definitions |
| Art, meshes, materials, shaders, audio banks, localisation tables |
| Rewired Input Manager configuration (joystick maps, action maps) |
| Compilable source of the native plugins |

Build identity (from `Version.cs`): `release-24-RC4`, timestamp `202608131133`, commit
`03e75a505086295362f23ed838ae9d297c484987`. Engine (from the audit): Unity 2022.3.62f2, Mono
scripting backend, 32-bit Windows, build target `win32.steam`.

## 3. Architecture relevant to a port

### 3.1 Dependency injection and platform abstraction
Services are registered in an `Assembler` (`Register<IInterface, Impl>()`), and each platform
supplies one `IEnvironment` that registers its implementations. Three interfaces carry almost all
platform differences:

- `IEnvironment`: `DeviceCategory` (Desktop / Phone / Tablet / Console), `FeatureConfigs`,
  `PopulateAppAssembler`, `PopulateGameAssembler`, `AddInputOverrideToGameObject`.
- `IHardwareCapabilities`: platform, `PersistentStoragePath`, unique device id,
  `DefaultDeviceInputType` (Touch / Mouse / Remote / Controller), gamepad style, haptics,
  sleep prevention, resolution and anti-aliasing support, displays, `OnAppStart`, `Exit`.
- `ISoftwareCapabilities`: locale, cloud saves, image sharing, screenshot size, HiDPI,
  profiles, display options, rich presence, app start/shutdown hooks.

Existing implementations: Windows (Steam, Humble, WeGame), macOS (Steam, Humble, App Store),
iOS (App Store, Arcade intro, retail demo), tvOS (App Store, retail demo), Switch hardware
capabilities, plus Null and Mock variants. **There is no Android implementation.**

### 3.2 Platform selection is compile-time
`AppContainer.CreateDefaultEnvironment()` contains only `new WindowsSteamEnvironment()`, followed by
an assertion whose message refers to "platform and variant combination". The original source
clearly selects the environment with preprocessor symbols; only the Windows/Steam branch survived
compilation. The same applies inside methods: for example, the iOS haptics and idle-timer
methods are empty in this build. **Any Android/iOS-specific logic guarded by `#if` in the real
source is invisible here**, which is one reason a port from decompilation would silently differ
from the real game.

### 3.3 Feature toggles and per-platform configs
`Feature` has 88 toggles. Each environment names feature-config assets (`SteamConfig`,
`ArcadeConfig`, `ArcadeIntroConfig`). Relevant toggles: `AutoZoomEnabledOption`,
`ControllerSensitivityOption`, `ToggleGameUIWithController`, `MockPhone` (forces the phone UI on
desktop), `MockControllerAsRemote`. An Android port needs an `AndroidConfig` asset.

### 3.4 Per-device UI
`MotorwaysAppContainer` loads UI prefabs by device category from the `core` asset bundle
(`InGameUI-{DeviceCategory}`, `GameUpgradeScreen-{DeviceCategory}`,
`GameOverScreen-{DeviceCategory}`). `GameUIScreen` has a `SafeArea`, indicator views clamp to it,
and `CameraView.GetCameraOffsetToFitPlayableArea` fits the camera to the UI's playable area.
Phone and tablet layouts already exist for iOS.

## 4. Brief requirements vs what already exists

| Requirement | Already in the game | Android work |
|---|---|---|
| Native touch controls | Yes. `TouchScreenController` registers touch actions for road drawing, editing motorways, dragging motorways/traffic lights/roundabouts/motorway handles from the toolbar, placing houses/destinations from the upgrade menu, creative-mode editing. `DoubleTapToggleDrawModeAction` and `DisableUITouchInputOverride` exist. Tap thresholds are relative to on-screen tile size, so they scale with density. | Verify on devices; tune thresholds only if testing shows a need. |
| Touch Auto-Zoom ON/OFF | Yes. `TouchCameraAction`: a single tap focuses (zooms) into the tapped area and enters edit mode; another tap returns to the overview. `IsZoomEnabled` switches between zooming focus and non-zooming focus. Persisted in device settings as `TouchZoomEnabled` (default on), merged by timestamp. The Options screen has the toggle, shown when `AutoZoomEnabledOption` is enabled. | Enable `AutoZoomEnabledOption` in `AndroidConfig`. |
| Two-finger pinch-to-zoom | **No.** Two fingers currently pan only (`TouchCameraAction`, `TouchCount == 2`). | New: in the two-finger branch, compute the finger-distance ratio, drive `CameraView`'s desired zoom clamped to `MinZoom`/`MaxZoom`, keep the world point under the midpoint fixed, reuse the existing interpolation, and reconcile with the tap-focus state (`IsFocussedIn`, `potentialTapZoomLevels`). |
| Razer Kishi V2 / generic gamepads | Yes, at gameplay level. `GenericGamepadController` maps menu navigation (d-pad/stick, accept, back, page left/right) and in-game actions (left stick moves focus, right stick moves camera, game speed, draw mode, zoom toggle, upgrade bar, activate). Controller drag actions exist for every placeable object. `ControllerSensitivityOption` exists. Rewired is polled in `RuntimeAppCommandSource` (5 files in `App` touch Rewired at all); Rewired's Unity integration (`RewiredStandaloneInputModule`, `UserDataStore_PlayerPrefs`, which persists user mappings) is in `Assembly-CSharp-firstpass`. | Rewired's Android platform support from a licensed Rewired package; Android joystick maps in the Input Manager; Android back button mapped to "back"; hot-plug via Rewired connect/disconnect events; Xbox-style glyphs through `DefaultControllerButtonToSymbolService`. No remapping UI was found (mapping persistence exists); a UI would be new if required. |
| Switching touch ↔ controller without restart | Yes. The input state accepts several connected controllers at once (desktop connects mouse, keyboard, gamepad and touch together; iOS connects touch and gamepad). | Connect touch and gamepad in the Android `OnAppStart`. |
| 30 / 60 / Auto FPS | Partly. iOS/tvOS set 60 FPS at start (30 on old devices). No user-facing option. | New option: device-settings field, Options UI entry, `Application.targetFrameRate`. Unity defaults to 30 FPS on Android when no target is set, so it must be set explicitly. The Galaxy A72 has a 90 Hz panel: check frame pacing on device. |
| Persistent saves | Yes. `IPersistentStorageProvider` with `LocalFileStorage` on `Application.persistentDataPath` (works on Android). Settings and profile files carry UTC timestamps and merge. In-progress games are journaled (`Autosave`, `PlayerQuit`, `AppDeactivated`) and resumable from `ResumeGameScreen`, which shows the save's date and device. | Register `LocalFileStorage` (or a Google Play Saved Games provider). **Harden `LocalFileStorage.Write`**: it overwrites with a plain `File.WriteAllBytes`, and the loader skips files it cannot parse, so a process kill mid-write can lose that file. Write to a temp file, flush, replace, keep a `.bak`, and fall back to it on load. Configure Android Auto Backup if saves should survive reinstalls. |
| Achievements | Yes. `AchievementDatabase` (ScriptableObject) holds definitions; completion is stored in the player profile (JSON, mergeable); some maps unlock through achievements; map buttons show per-map achievement tick boxes. Platform reporting goes through `IAchievementHandler` (Game Center, Steamworks, Null). | Android handler: Null (local only, which already works offline) or Google Play Games. A dedicated achievements list screen does not exist (platform overlays were used); build one from existing data if required. |
| Responsive scaling / Galaxy A72 | Yes. Safe area, phone/tablet/desktop prefabs, aspect-based selection, camera fit to the playable area. | Android environment must report Phone vs Tablet (for example from physical screen size). Verify 20:9 (2400×1080) with the punch-hole camera, plus 16:9, 19.5:9 and tablets. |
| Landscape only | n/a (project setting) | Player Settings: auto-rotation limited to Landscape Left and Landscape Right. |
| App lifecycle / battery | Yes. Backgrounding saves the in-progress game and statistics (`GameContainerScreen.OnApplicationPause`); focus loss pauses through `ScreenStack.OnApplicationPaused`. Decompressed audio has a memory cap (about 10.5 million 16-bit samples, roughly 20 MB, at 48 kHz). | Verify audio and simulation stop while paused; profile on device. |
| Haptics | iOS only (native calls). | Optional: Android vibration through JNI. |

## 5. Blockers and components to replace for Android

1. **`dpcPlatform` native plugin (studio-owned).** Gameplay depends on it:
   - pathfinding graph (`ExternPathfinding`, 20 imports: build nodes/edges, path cost, next edge/node, pause/resume, setup),
   - vehicle acceleration (`VehicleMovementProcess`),
   - audio DSP inside G-Audio (`LFOProcessChunk`, `GainMixToInterlaced`, `ResampleCopyFromInt16`),
   - GIF encoding, multi-display support, and the Apple service bridges (Game Center, iCloud, reachability),
   - a load check (`DllUtilities.EmptyLibraryFunction`): if the library cannot load, the game shows a "could not load library" popup with a support link.

   Android needs `libdpcPlatform.so` for `arm64-v8a` (optionally `armeabi-v7a`), built with the NDK from the studio's C/C++ source and aligned for 16 KB memory pages (current Google Play requirement). Pseudo-C is not compilable, and a reimplementation would risk changing pathfinding and traffic behaviour.
2. **`decompressAudio` native plugin.** Decompresses and resamples audio samples for `AudioDataBank`. Same treatment as above.
3. **`lib_burst_generated`.** Only URP and Burst package jobs use `[BurstCompile]`; Unity regenerates this for ARM64. Not a blocker.
4. **Rewired.** `Rewired_Windows` and `Rewired_DirectInput` are Windows-only. Use the licensed Rewired package, which includes Android support.
5. **Steamworks.** Remove `Facepunch.Steamworks.Win32` and `steam_api`. Steam-dependent classes: `SteamworksShared`, `SteamSoftwareCapabilities`, `SteamworksAchievementHandler`, `SteamworksLeaderboardBackend`, `SteamHistogramBackend`, `SteamCloud`, `SteamworksCloudSyncService` (registered unconditionally in `AppContainer` in this build), the static leaderboard-id helper used by `ScrapedHistogramBackend`, and the Steamworks entry in `AchievementData`'s platform list. Exclude them with scripting defines or assembly-definition platform filters, and register Null implementations where an interface is required.
6. **Apple-only services** (Game Center, iCloud, Apple reachability, SF Symbols glyphs, iOS notifications) serve as templates only.
7. **Scripting backend.** The Windows build uses Mono; 64-bit Android requires IL2CPP. AOT readiness is good: 92 `AOTTarget_*` classes and `AOTGenericTypes` exist from the iOS/Switch builds. Reflection on non-public members (34 matches in 8 files of `App`) needs `link.xml` entries or a conservative stripping level.
8. **Online services.** Leaderboards, challenges, diagnostics and analytics talk to `api.dinopoloclub.com`. Android needs server-side support (platform id, authentication) or these features disabled.
9. **Toolchain currency.** Confirm that the Unity 2022.3 patch in use can target the Android API level Google Play currently requires and supports 16 KB page sizes; otherwise update the editor patch first.

## 6. Licences and permissions required

| Component | Rights holder | Status | Needed for an Android port |
|---|---|---|---|
| Game code, assets, audio, "Mini Motorways" name | Codepoint Limited (Dinosaur Polo Club). Steam page: "© Codepoint Limited 2021. Mini Motorways is a registered trademark of Codepoint Limited." | All rights reserved | Written licence or porting agreement covering code, assets, trademark and distribution. Confirm music and sound rights cover a new platform (composer and sound agreements can be separate). |
| `dpcPlatform`, `decompressAudio` sources | Presumably the studio | Not public | Source access as part of the agreement |
| Unity 2022.3 + Android Build Support | Unity Technologies | Commercial | A Unity plan appropriate to the licensee's revenue |
| URP, SRP Core, TextMeshPro, UGUI, Burst, Mathematics | Unity Technologies | Unity Companion Licence | Usable inside a licensed Unity project |
| Rewired | Guavaman Enterprises ("Copyright © 2014 Augie R. Maddox. All rights reserved.") | Commercial Asset Store licence | Own seats; use the official package, not DLLs extracted from a shipped game |
| G-Audio | Asset Store publisher | Commercial | Own licence; the studio-modified copy comes with the studio's project |
| Newtonsoft.Json | James Newton-King | MIT | Keep notice (Unity ships it as a package) |
| NaughtyAttributes, MiniJson | Open source | MIT | Keep notices |
| Easing | Unknown origin | To confirm | Identify origin and licence |
| Facepunch.Steamworks, Steamworks SDK | Facepunch / Valve | MIT / Valve SDK terms | Not used on Android; remove |
| Google Play distribution | Google | Developer account, Play policies | Play App Signing, Data safety form (the game sends analytics), privacy policy, content rating; optional Play Games Services for achievements and cloud saves |

In practice, "obtaining authorisation" means the studio carries out or commissions the port
with its own project and source. A licence would not normally extend to a decompilation of a
cracked retail build.

## 7. Porting plan (contingent on authorisation, from the real Unity project)

**Stage 0: access.** Licence signed; repository access at the shipped commit; native plugin
sources; Rewired and G-Audio seats; Google Play developer account.

**Stage 1: Android foundation.**
- Install Android Build Support (SDK, NDK, OpenJDK) for Unity 2022.3.
- Player Settings: IL2CPP, ARM64 (plus ARMv7 if desired), required target API, landscape-left/right only, Optimized Frame Pacing on.
- Build `libdpcPlatform.so` and `libdecompressAudio.so` with CMake and the NDK, 16 KB aligned, into `Plugins/Android/libs/<abi>/`. The existing `DllImport("dpcPlatform")` names resolve to `lib<name>.so` without code changes.
- Exclude Steam assemblies and classes for Android; add an `UNITY_ANDROID` branch to `CreateDefaultEnvironment`.
- Exit criterion: the game boots to the main menu on a device, pathfinding works, audio plays.

**Stage 2: Android platform layer** (modelled on the iOS classes).
- `AndroidEnvironment`: Phone/Tablet by physical size; `FeatureConfigs = ["AndroidConfig"]`; registrations for hardware and software capabilities, hardened `LocalFileStorage`, Null Game Center services, achievement handler (Null or Play Games), leaderboard backend (studio server, Play Games or disabled), reachability via `Application.internetReachability`, default controller glyphs, notifications (Null or Android local notifications), Null Steam cloud sync.
- `AndroidHardwareCapabilities`: `persistentDataPath`; default input Touch; gamepad style Generic; haptics via vibration; `Screen.sleepTimeout` for sleep prevention; frame rate from the new setting; connect touch and gamepad controllers at start.
- `AndroidSoftwareCapabilities`: share via Android intent (or disabled at first), no rich presence, cloud saves only if Play Games is used.
- `AndroidConfig` feature asset: enable `AutoZoomEnabledOption` and `ControllerSensitivityOption`; disable desktop-only options.

**Stage 3: touch.** Reuse all existing touch actions. Add pinch-to-zoom (section 4). Test
gesture conflicts: drawing with one finger vs panning/pinching with two, toolbar drags, UI
blocking.

**Stage 4: controllers.** Rewired Android joystick maps; test the Kishi V2 over USB-C, plus
Bluetooth pads (Xbox, DualSense); hot-plug and reconnect; back-button behaviour; glyphs.

**Stage 5: mobile systems.** Atomic save writes with backup and load fallback; 30/60/Auto
frame-rate option; achievements screen if required; Auto Backup or Play Games Saved Games.

**Stage 6: performance and battery.** Unity Profiler plus Android GPU Inspector / Perfetto on
device. Review the URP asset for mobile (MSAA, render scale, HDR, shadows). Confirm simulation,
rendering and audio stop while paused. Watch thermal throttling at 60 FPS.

**Stage 7: verification.** Galaxy A72 (2400×1080, 20:9, punch-hole, 90 Hz) and at least one
16:9 phone, one 19.5:9 phone and a tablet; landscape-left/right flips; Kishi V2; save survival
across `adb shell am kill`, backgrounding and reboot; resume of an in-progress game; offline
play. Record each item as implemented / tested / untested.

**Stage 8: release.** Signed AAB for Google Play (APK for sideload testing), store listing,
Data safety form, privacy policy, content rating.

### Main risks
- Availability and buildability of the native plugin sources (the critical path).
- Rewired behaviour with specific Android controllers, including the Kishi V2.
- Whether the phone UI prefabs in the asset bundles need changes for very wide aspect ratios.
- Server-side support for an Android platform (leaderboards, challenges).
- Toolchain: target API level and 16 KB page-size support in the chosen Unity patch.

## 8. Key evidence (paths inside the decompiled archive)

| Topic | Where |
|---|---|
| Platform interfaces | `App/IEnvironment.cs`, `App/IHardwareCapabilities.cs`, `App/ISoftwareCapabilities.cs` |
| Compile-time environment choice | `App/AppContainer.cs` (`CreateDefaultEnvironment`) |
| iOS service set (template) | `App/iOSAppStoreEnvironment.cs`, `App/iOSHardwareCapabilities.cs` |
| Desktop and Steam service sets | `App/WindowsBaseEnvironment.cs`, `App/WindowsSteamEnvironment.cs`, `App/DesktopHardwareCapabilities.cs` |
| Touch actions | `App/TouchScreenController.cs`, `App/Motorways.Actions/TouchCameraAction.cs` |
| Auto-zoom setting | `App/MotorwaysDeviceSettings.cs` (`TouchZoomEnabled`), `App/Motorways.Views/OptionsScreenBase.cs` |
| Camera zoom API | `App/Motorways.Views/CameraView.cs` |
| Gamepad mapping | `App/GenericGamepadController.cs`, `App/RewiredConsts/InputAction.cs`, `App/RuntimeAppCommandSource.cs`, `Assembly-CSharp-firstpass/Rewired.*` |
| Saves | `App/IPersistentStorageProvider.cs`, `App/LocalFileStorage.cs`, `App/SteamCloud.cs`, `App/Motorways.UI/ResumeMapButton.cs` |
| Lifecycle | `App/AppRuntime.cs`, `App/Motorways.Views/GameContainerScreen.cs` |
| Achievements | `App/IAchievementHandler.cs`, `App/AchievementDatabase.cs`, `App/Achievement.cs`, `App/Motorways.UI/MapButton.cs`, `App/Motorways.UI/AchievementTickBox.cs` |
| Native dependencies | `App/Motorways.Pathfinding/ExternPathfinding.cs`, `App/Motorways.Processes/VehicleMovementProcess.cs`, `App/Motorways.Audio/AudioDataBank.cs`, `App/DllUtilities.cs`, `G-Audio/GAudio/GATData.cs`, `G-Audio/GAudio/GATLFO.cs` |
| Per-device UI prefabs | `App/Motorways/MotorwaysAppContainer.cs` |
| Feature toggles | `App/Feature.cs` |
