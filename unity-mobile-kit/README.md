# Unity Mobile Kit

A small, **standalone, general-purpose** toolkit of mobile-game building blocks for Unity.
It is original code, not affiliated with or derived from any particular game, and it contains no
game-specific logic, assets, or third-party SDK code. Every component is written to be dropped
into any Unity project.

## Why this exists

Most mobile games need the same plumbing: crash-safe saves, local achievements, a frame-rate
setting, multitouch gestures (pan / pinch-to-zoom), a focus/auto-zoom helper, gamepad handling
with hot-plug, landscape locking, safe-area-aware UI scaling, and app-lifecycle handling. This
kit implements those as independent, reusable pieces.

## Layout

```
unity-mobile-kit/
  core/            Pure C# (no UnityEngine dependency) — unit-tested with dotnet
    UnityMobileKit.Core/
      Persistence/       Atomic, crash-resistant save store + integrity checks
      Achievements/      Local achievement definitions, progress, persistence
      Settings/          Frame-rate model, auto-zoom preference, generic prefs
      Geometry/          Float2, RectF, screen density (keeps the core free of UnityEngine types)
      Gestures/          Touch gesture recognition (tap, drag, pinch)
      CameraControl/     Pan/zoom camera math, auto-zoom framing
      Controllers/       Gamepad deadzones, buttons, virtual cursor, input mode
      ScreenLayout/      Safe-area anchors, UI scale, touch-target sizing
      Performance/       Battery-, heat- and frame-time-aware frame-rate policy
      Lifecycle/         Focus/pause/quit -> one suspended state, save on suspend
  unity/           Unity MonoBehaviour layer (depends on UnityEngine)
    Runtime/             Thin adapters: services + save-on-background, touch/controller input,
                         pan/zoom camera rig, safe area, orientation lock, frame-rate driver
  tests/           dotnet only, never copied into Unity
    UnityMobileKit.Tests/       Dependency-free unit tests for core/ (dotnet run), fully offline
    UnityApiStubs/              Hand-written stand-ins for the UnityEngine API, for the compile check
    check-unity-adapters.sh     Compile-checks unity/Runtime against the stand-ins
```

## Components and status

| Component | What it does | Status |
|---|---|---|
| `Persistence/AtomicFileStore` | Temp-write + flush + atomic swap, CRC-32 framing, backup copy, crash-window recovery | Done, 18 dotnet tests |
| `Achievements/AchievementTracker` | Offline progress, unlock exactly once, auto-save on unlock, keeps unknown ids, handles changed targets | Done, 25 dotnet tests |
| `Settings/GameSettings` | Frame-rate mode (30 / 60 / Auto), touch auto-zoom toggle, typed custom prefs, saved through the same store | Done, 18 dotnet tests |
| `Gestures/GestureRecognizer` | Tap, one-finger drag, two-finger pinch + pan from raw touch points; density-aware tap slop, no camera jumps when fingers are added, removed or reordered, cancel on focus loss | Done, 18 dotnet tests |
| `CameraControl/ZoomPanCamera` | Orthographic top-down camera: content follows the finger, pinch zooms around the fingers' midpoint, zoom limits, world bounds that survive rotation | Done, 9 dotnet tests |
| `CameraControl/AutoZoom` | Smoothly frames points of interest with a screen margin; frame-rate independent; pauses while the player pans/pinches; bind to the auto-zoom setting | Done, 3 dotnet tests |
| `Controllers/` | Standard-gamepad state, radial stick + trigger deadzones, button edges with D-pad auto-repeat, stick-driven virtual cursor, stick/trigger camera control, touch-vs-gamepad mode with pause on disconnect | Done, 15 dotnet tests |
| `ScreenLayout/SafeArea` | Cleans up the platform safe area (empty, NaN or off-screen falls back to the full screen; overhang is clipped) and turns it into panel anchors; optional symmetric insets so centred UI doesn't jump when a landscape phone is rotated | Done, 3 dotnet tests |
| `ScreenLayout/UiScale` | CanvasScaler-equivalent scale for a reference resolution; minimum 48 dp touch-target size in canvas units for the screen's density | Done, 2 dotnet tests |
| `Performance/FrameRatePolicy` | Picks the frame-rate cap from the 30 / 60 / Auto setting, battery saver, low battery, heat and measured frame times; steps 90 -> 60 -> 30 when frames keep missing, ignores one-off hitches, retries later with backoff (30 s doubling to a 300 s cap). `ThermalMapping` maps Android and iOS thermal readings onto four heat levels | Done, 11 dotnet tests |
| `Lifecycle/LifecycleCoordinator` | Merges focus / pause / quit callbacks into one suspended state; saves every dirty `ISaveable` once on suspend; one failing save doesn't block the others or throw out of the callback | Done, 4 dotnet tests |

The Unity layer (`unity/Runtime`) is **written and compile-checked only**: it compiles against
hand-written stand-ins for the UnityEngine, Input System and uGUI APIs in 5 configurations of
Unity's scripting defines, but it has **never run in Unity or on a device** (see Testing status).

| `unity/Runtime` component | What it does |
|---|---|
| `MobileKitServices` | Creates the save store (under `Application.persistentDataPath`), settings, achievements (from an `AchievementCatalog` asset) and the lifecycle coordinator once per app; forwards focus / pause / quit so data is saved when the app loses focus or is backgrounded; `onSuspended` / `onRestored` events for the pause menu |
| `MobileInput` | Touch (Input System, or the legacy Input Manager) to gestures, ignoring touches that start on UI; controllers through the Input System: buttons with auto-repeat, a virtual cursor kept inside the safe area, South (A / Cross) taps at the cursor, touch-vs-controller mode, a pause event when the controller in use disconnects |
| `PanZoomCameraRig` | Orthographic camera on the XY or XZ plane, driven by drag, pinch, right stick and triggers; world bounds; auto-zoom on focus points, following the player's auto-zoom setting |
| `SafeAreaFitter` | Fits a UI panel to the safe area and re-fits on rotation or resolution change |
| `OrientationLock` | Landscape left/right only (or portrait only) at runtime |
| `FrameRateDriver` | Applies `FrameRatePolicy` to `Application.targetFrameRate`; reads battery from Unity and battery saver / thermal status from Android's `PowerManager` every few seconds; uses the display's highest refresh rate for Auto |

Achievements on top of the save store:

```csharp
var store = new AtomicFileStore(Application.persistentDataPath);
var achievements = new AchievementTracker(new[]
{
    new AchievementDefinition("first_win", "First win", "Win one match."),
    new AchievementDefinition("veteran", "Veteran", "Play 100 matches.", target: 100),
}, store);

achievements.Unlocked += state => ShowToast(state.Definition.Title);
achievements.Load();                    // once at startup; never throws on damaged data
achievements.Report("veteran");         // +1 progress; unlocks (and auto-saves) at 100
if (achievements.HasUnsavedChanges) achievements.Save();   // e.g. when the app is paused
```

Settings on the same store:

```csharp
var settings = new GameSettings(store);
settings.Load();                        // defaults if missing or damaged
int displayHz = Mathf.RoundToInt((float)Screen.currentResolution.refreshRateRatio.value);
Application.targetFrameRate = FrameRate.Resolve(settings.FrameRate, displayHz);
settings.SetFloat("music_volume", 0.8f);                   // custom prefs, any key not starting with "umk."
if (settings.HasUnsavedChanges) settings.Save();
```

Saving on background and choosing the frame rate each frame:

```csharp
var lifecycle = new LifecycleCoordinator(settings, achievements);
var frameRate = new FrameRatePolicy();
lifecycle.Suspended += ShowPauseMenu;
lifecycle.Restored += frameRate.ResetMeasurements;

void OnApplicationFocus(bool hasFocus) => lifecycle.OnFocusChanged(hasFocus);
void OnApplicationPause(bool paused) => lifecycle.OnPauseChanged(paused);
void OnApplicationQuit() => lifecycle.OnQuit();

void Update()
{
    var conditions = new DeviceConditions(SystemInfo.batteryLevel, isCharging, isLowPowerMode, thermal);
    Application.targetFrameRate = frameRate.Update(settings.FrameRate, displayHz, conditions,
                                                   Time.unscaledDeltaTime, Time.realtimeSinceStartupAsDouble);
}
```

`isCharging`, `isLowPowerMode` and `thermal` come from the platform. In `unity/Runtime`,
`MobileKitServices` and `FrameRateDriver` do this wiring, and `DeviceConditionsReader` reads those
values on Android.

## Using it in Unity (2021.3 LTS or newer)

1. Copy exactly two folders into the project, for example under `Assets/UnityMobileKit/`:
   `core/UnityMobileKit.Core` and `unity/Runtime`, without any `bin/` or `obj/` folders a local
   dotnet build created. Their assembly definitions keep the core free of UnityEngine. Never copy
   `tests/`: its stand-in UnityEngine types would clash with the real engine.
2. Optional packages: **Input System** (needed for controllers; also used for touch when enabled
   under Player Settings > Active Input Handling) and **uGUI** (to ignore touches that start on UI).
3. Player Settings > Resolution and Presentation: Default Orientation = Auto Rotation, allowing
   only Landscape Left and Landscape Right. The OS enforces this before Unity starts.
4. Scene setup:
   - On a root GameObject in the first scene: `MobileKitServices`, `MobileInput`,
     `FrameRateDriver`, `OrientationLock`.
   - On the orthographic camera: `PanZoomCameraRig`, with the `MobileInput` assigned.
   - Under each Screen Space canvas: a full-screen panel with `SafeAreaFitter`; put the HUD inside it.
   - From game code: handle `MobileInput.PointerTapped`, pass what matters to
     `PanZoomCameraRig.SetFocusPoints`, report progress through
     `MobileKitServices.Instance.Achievements`, and bind a settings menu to
     `MobileKitServices.Instance.Settings`.
5. To get a debug APK onto a phone, follow [`docs/ANDROID_BUILD.md`](docs/ANDROID_BUILD.md).

## Testing status (honest)

This repository is developed on a server with **no Unity install and no Android device**.

- **`core/` and `tests/`** are plain C#. They are **built and unit-tested with `dotnet`** here,
  and the results are real. Run them with:

  ```
  dotnet run --project unity-mobile-kit/tests/UnityMobileKit.Tests
  ```

- **`unity/`** depends on `UnityEngine` and the device, so it is **not runtime-tested** here; that
  is stated at the top of each file. What is checked: it compiles (warnings as errors) against
  the real core and against hand-written stand-ins for the UnityEngine, Input System and uGUI
  members it uses, in 5 combinations of Unity's scripting defines (legacy / new input, with and
  without uGUI, Android device / Editor, before / after Unity 2022.2):

  ```
  unity-mobile-kit/tests/check-unity-adapters.sh
  ```

  The stand-ins are written from Unity's documentation, so this catches mistakes in the adapter
  code and in its use of the core, but not a stand-in that differs from the real API, and nothing
  about behaviour. Nothing in `unity/` is reported as verified until it runs in Unity and on a
  device.

## Scope / boundary

This is independent infrastructure. It is deliberately not tied to any specific game, and it is
not a porting layer for one. Using these generic components inside an unauthorised port of a
third-party game would still require that game's licence; the components themselves do not grant
one.

## Licence

Original work. See `LICENSE` (MIT).
