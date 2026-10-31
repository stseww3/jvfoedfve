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
