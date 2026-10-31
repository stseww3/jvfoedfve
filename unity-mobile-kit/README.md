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
  tests/           Dependency-free test harness (dotnet run), fully offline
  unity/           Unity MonoBehaviour layer (depends on UnityEngine)
    Runtime/
      Input/             Multitouch gestures, pinch-to-zoom, gamepad wrapper
      Camera/            Pan/zoom camera controller, auto-zoom focus
      Display/           Landscape lock, safe-area scaler
      Lifecycle/         Pause/resume, save-on-background, frame-rate applier
```

## Components and status

| Component | What it does | Status |
|---|---|---|
| `Persistence/AtomicFileStore` | Temp-write + flush + atomic swap, CRC-32 framing, backup copy, crash-window recovery | Done, 18 dotnet tests |
| `Achievements/AchievementTracker` | Offline progress, unlock exactly once, auto-save on unlock, keeps unknown ids, handles changed targets | Done, 25 dotnet tests |
| `Settings/GameSettings` | Frame-rate mode (30 / 60 / Auto), touch auto-zoom toggle, typed custom prefs, saved through the same store | Done, 18 dotnet tests |
| `unity/` layer | Gestures, camera, gamepad, display, lifecycle | Planned (will not be runtime-tested here) |

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
