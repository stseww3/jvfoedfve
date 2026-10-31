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
  tests/           Dependency-free test harness (dotnet run), fully offline
  unity/           Unity MonoBehaviour layer (depends on UnityEngine)
    Runtime/             Thin adapters: touch/gamepad input, camera rig, safe area,
                         landscape lock, lifecycle relay, frame-rate driver
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
| `Performance/FrameRatePolicy` | Picks the frame-rate cap from the 30 / 60 / Auto setting, battery saver, low battery, heat and measured frame times; steps 90 -> 60 -> 30 when frames keep missing, ignores one-off hitches, retries later with backoff (30 s doubling to a 300 s cap) | Done, 10 dotnet tests |
| `Lifecycle/LifecycleCoordinator` | Merges focus / pause / quit callbacks into one suspended state; saves every dirty `ISaveable` once on suspend; one failing save doesn't block the others or throw out of the callback | Done, 4 dotnet tests |
| `unity/` layer | Thin adapters: touch/gamepad input, camera, safe area, landscape lock, lifecycle, frame-rate driver | Next (will not be runtime-tested here) |

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

`isCharging`, `isLowPowerMode` and `thermal` come from the platform (Android `PowerManager`, iOS
`ProcessInfo`); the `unity/` layer will provide them.

## Testing status (honest)

This repository is developed on a server with **no Unity install and no Android device**.

- **`core/` and `tests/`** are plain C#. They are **built and unit-tested with `dotnet`** here,
  and the results are real. Run them with:

  ```
  dotnet run --project unity-mobile-kit/tests/UnityMobileKit.Tests
  ```

- **`unity/`** depends on `UnityEngine` and the device. It is written to compile inside Unity and
  is reviewed for correctness, but it is **not runtime-tested** in this environment. That is
  stated at the top of each file. Nothing in `unity/` is reported as verified until it runs on a
  device.

## Scope / boundary

This is independent infrastructure. It is deliberately not tied to any specific game, and it is
not a porting layer for one. Using these generic components inside an unauthorised port of a
third-party game would still require that game's licence; the components themselves do not grant
one.

## Licence

Original work. See `LICENSE` (MIT).
