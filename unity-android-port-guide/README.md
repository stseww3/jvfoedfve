# Porting a Unity game to Android

A practical guide for taking a Unity game you own (PC/console/iOS) to Android phones and tablets, with:

- touchscreen controls, including two-finger pinch zoom and pan
- an auto-zoom camera the player can switch on or off
- controller support (Razer Kishi V2 and any other standard gamepad)
- a crash-safe save system
- achievements (Google Play Games, working offline too)
- UI and rendering that adapt to every screen, tuned for the Samsung Galaxy A72
- landscape only
- performance and battery optimization

Everything in `Scripts/` is original, general-purpose code that drops into any Unity project. It doesn't
contain or depend on code or assets from any particular game. Your game code connects to it through a few
events and method calls, shown below.

Written for **Unity 2022.3 LTS or Unity 6** with the **Input System** package (1.7 or newer). The scripts
should also work on 2021.3 LTS.

## Contents

1. [What's in Scripts/](#whats-in-scripts)
2. [Project setup](#project-setup)
3. [Landscape only](#landscape-only)
4. [Screen scaling and the Galaxy A72](#screen-scaling-and-the-galaxy-a72)
5. [Touch controls](#touch-controls)
6. [Pinch zoom, pan and the auto-zoom toggle](#pinch-zoom-pan-and-the-auto-zoom-toggle)
7. [Controllers: Razer Kishi V2 and others](#controllers-razer-kishi-v2-and-others)
8. [Save system](#save-system)
9. [Achievements](#achievements)
10. [Performance and battery](#performance-and-battery)
11. [Build and release](#build-and-release)
12. [Test plan](#test-plan)
13. [Common pitfalls](#common-pitfalls)

---

## What's in Scripts/

| Script | What it does |
| --- | --- |
| `OrientationLock.cs` | Forces landscape (both directions) from the first frame. Creates itself. |
| `SafeAreaFitter.cs` | Keeps HUD elements clear of the punch-hole camera, rounded corners and gesture bar. |
| `TouchGestures.cs` | Recognizes tap, long press, one-finger drag, two-finger pinch and two-finger pan. Ignores touches that start on UI. |
| `MapCamera.cs` | Orthographic camera with pinch zoom, pan, edge scrolling and the auto-zoom setting. |
| `ControllerSupport.cs` | Switches between touch and gamepad. Handles the on-screen cursor, camera sticks and triggers, menu navigation and controller disconnects. |
| `SaveSystem.cs` | JSON save slots that survive the app being killed mid-write (temp file, backup, checksum). |
| `AppLifecycle.cs` | Events for "app went to background" (save now) and "focus lost" (pause now), plus low-memory cleanup. Creates itself. |
| `Achievements.cs` | Local achievements with counters, synced to Google Play Games when signed in. |
| `PerformanceSettings.cs` | 30/60/90 fps setting, reduced rendering in menus, low-battery saver, screen-sleep rules. |

Copy the `Scripts` folder anywhere under `Assets/`. No assembly definition is needed: in the default
`Assembly-CSharp`, the Input System is referenced automatically.

### Scene setup at a glance

- **Bootstrap or first scene**: one object with `Achievements` and `PerformanceSettings`. Both persist
  across scenes. `OrientationLock` and `AppLifecycle` need no setup.
- **Gameplay scene**:
  - one `TouchGestures`
  - `MapCamera` on the gameplay camera
  - `ControllerSupport` plus a Virtual Mouse cursor (see [Controllers](#controllers-razer-kishi-v2-and-others))
  - a HUD canvas whose content sits under a `SafeAreaFitter`

---

## Project setup

Install these with **Unity Hub**:

- **Android Build Support**, including OpenJDK and the Android SDK and NDK tools.

Install these with the **Package Manager**:

- **Input System**. Then set **Player Settings → Other Settings → Active Input Handling** to
  *Input System Package (New)*. Use *Both* while you migrate old code.
- **Universal Render Pipeline**, if you aren't on it already. It's the right pipeline for mobile.
- **Google Play Games plugin for Unity**, for achievements. Details in [Achievements](#achievements).

### Android Player Settings checklist

Open **Edit → Project Settings → Player**, Android tab.

**Resolution and Presentation**

- Default Orientation: **Auto Rotation**, with only **Landscape Right** and **Landscape Left** allowed.
- **Render outside safe area**: on. The game draws edge to edge and `SafeAreaFitter` keeps the HUD clear.
- **Optimized Frame Pacing**: on. This gives smoother frame times and avoids wasted frames.

**Other Settings**

- Graphics APIs: **Vulkan** first, **OpenGLES3** as fallback.
- Color Space: Linear. Multithreaded Rendering: on.
- Texture compression format: **ASTC**.
- Scripting Backend: **IL2CPP**. Target Architectures: **ARM64**. Google Play requires 64-bit; add
  ARMv7 only if you need very old phones.
- API Compatibility Level: .NET Standard 2.1.
- Minimum API Level: Android 8.0 (API 26) is a sensible floor.
- Target API Level: the highest installed. Make sure it meets Google Play's current requirement, which
  rises every year.
- Managed Stripping Level: Medium. Try High once everything works.
- **Use incremental GC**: on. This spreads garbage collection over frames instead of causing hitches.
- Configuration → **Android Gamepad Support Level**: *Supports Gamepad*. This marks controllers as
  supported but not required.

**Publishing Settings**

- Create a release keystore and back it up somewhere safe. Use Play App Signing in Play Console.
- In Build Settings, tick **Build App Bundle (Google Play)** for release builds.

---

## Landscape only

1. Set the Player Settings above. They also make the splash screen landscape.
2. `OrientationLock.cs` re-applies the lock at runtime before the first scene loads. It needs no setup.

Keep both landscape directions allowed. Players flip phones over, and a game locked to one side feels
broken when they do.

---

## Screen scaling and the Galaxy A72

### Galaxy A72 in numbers

| | |
| --- | --- |
| Screen | 6.7", 2400 × 1080 (20:9), about 393 ppi, 90 Hz |
| Cutout | Punch-hole camera, top centre in portrait. In landscape it sits at the left or right edge. |
| Chip | Snapdragon 720G with Adreno 618 GPU, 6 or 8 GB RAM |

What this means for you:

- The screen is wider than 16:9, so you get extra horizontal space.
- One side has a cutout that moves when the phone flips.
- The GPU is mid-range: fine for a clean, flat art style at native resolution, but not for heavy
  post-processing.

### UI that fits every screen

Set every HUD Canvas's **Canvas Scaler** like this:

- UI Scale Mode: **Scale With Screen Size**
- Reference Resolution: **1920 × 1080**
- Screen Match Mode: **Expand**

With *Expand*, the 1920 × 1080 reference area is always fully visible, and the canvas grows in the extra
direction:

| Device | Canvas size | Extra space |
| --- | --- | --- |
| 16:9 phone | 1920 × 1080 | none |
| Galaxy A72 (20:9) | 2400 × 1080 | width |
| 4:3 tablet | 1920 × 1440 | height |

So anchor HUD groups to the screen edges and corners. Never position them against an assumed 1920 width.

Put a full-screen stretched child under each HUD canvas, add `SafeAreaFitter` to it, and parent the HUD
elements under that child. Background images stay outside it so they still fill the whole screen.

**Touch target size.** Make every button at least 48 dp. On the A72 that is about 120 px, which is also
about 120 canvas units: the canvas scale is 1.0 there because the screen height equals the reference
height. Leave at least 16 units between neighbouring buttons.

**Text.** Use TextMeshPro with SDF fonts so text stays sharp at any scale. Check the smallest text on a
real phone at arm's length.

### The world camera

`MapCamera.SetPlayArea(bounds)` frames the play area for whatever aspect ratio the device has. On the A72,
the height usually limits the zoom, so players see extra ground to the left and right. Make the
background or ground extend well beyond the play bounds, so 20:9 and 21:9 screens never show empty space
at the sides.

### Render resolution

At 2400 × 1080 with a flat art style, the Adreno 618 can render at native resolution. If you need GPU
headroom, lower the scene's render scale rather than the screen resolution. URP's **Render Scale** only
affects the 3D/2D scene, and Screen Space Overlay UI stays at native resolution, so text stays crisp.

A clean way to offer this is two **Quality levels** (Project Settings → Quality), each with its own URP
asset:

| Quality level | Render Scale | MSAA |
| --- | --- | --- |
| Standard | 1.0 | 4x |
| Battery | 0.8 | 2x |

Switch with `QualitySettings.SetQualityLevel(index, true)` from your settings menu.

Avoid Player Settings → Resolution Scaling Mode → *Fixed DPI* for this. It scales the whole screen,
including the UI.

---

## Touch controls

### Gesture map

This suggested map suits a game where you draw roads or lines on a map and drag items from a toolbar:

| Gesture | Action |
| --- | --- |
| One-finger drag | Draw road |
| Long press, then drag | Erase along the drag |
| Tap | Select / confirm / place |
| Long press without moving | Context action, such as info or removing one tile |
| Two-finger pinch | Zoom around the fingers |
| Two-finger drag | Pan the map |
| Drag from the toolbar | Place an item, with the preview drawn above the finger |
| HUD eraser toggle | Alternative to long-press erase, for players who find long press awkward |

`TouchGestures` handles the tricky parts:

- A press becomes a drag only after the finger moves 8 dp, so taps don't draw.
- A second finger ends the drag and switches to pinch. The drag is reported as cancelled.
- After a pinch, the remaining finger is ignored until all fingers lift, so lifting one finger mid-pinch
  never draws a road.
- Touches that start on UI never reach the map.

**Testing in the Editor.** Turn on *Simulate Touch Input From Mouse or Pen* (Window → Analysis → Input
Debugger → Options). Then the mouse drives one-finger gestures. Test pinch on the phone itself.

### Wiring it to your game

Your PC version already has functions that the mouse calls: start a stroke, extend it, end it, click.
Call the same functions from the touch events. `YourRoadBuilder` below stands in for your own code.

```csharp
using UnityEngine;

public class RoadTouchInput : MonoBehaviour
{
    [SerializeField] TouchGestures gestures;
    [SerializeField] MapCamera mapCamera;
    [SerializeField] Camera worldCamera;
    [SerializeField] YourRoadBuilder roads;

    public bool EraserToolActive { get; set; }

    void OnEnable()
    {
        gestures.DragStarted += OnDragStarted;
        gestures.Dragged += OnDragged;
        gestures.DragEnded += OnDragEnded;
        gestures.Tapped += OnTapped;
    }

    void OnDisable()
    {
        gestures.DragStarted -= OnDragStarted;
        gestures.Dragged -= OnDragged;
        gestures.DragEnded -= OnDragEnded;
        gestures.Tapped -= OnTapped;
    }

    void Update()
    {
        if (gestures.IsDragging)
            mapCamera.EdgeScroll(gestures.PointerPosition);
    }

    void OnDragStarted(Vector2 screen, bool afterLongPress)
    {
        roads.BeginStroke(ScreenToGround(screen), erase: afterLongPress || EraserToolActive);
    }

    void OnDragged(Vector2 screen) => roads.ContinueStroke(ScreenToGround(screen));

    // Tiles are placed as the finger moves, so a cancelled drag (second finger landed) just ends the stroke.
    void OnDragEnded(Vector2 screen, bool cancelled) => roads.EndStroke();

    void OnTapped(Vector2 screen) => roads.Click(ScreenToGround(screen));

    Vector3 ScreenToGround(Vector2 screen)
    {
        Ray ray = worldCamera.ScreenPointToRay(screen);
        var ground = new Plane(Vector3.up, Vector3.zero);
        return ground.Raycast(ray, out float distance) ? ray.GetPoint(distance) : Vector3.zero;
    }
}
```

The plane above assumes the map lies on the XZ plane at height 0. For a 2D game on the XY plane, use
`worldCamera.ScreenToWorldPoint` instead.

### Touch details that matter

- **Fingers hide what they touch.**
  - Highlight the tile under the finger with a ring larger than a fingertip, about 10 mm.
  - When dragging an item from the toolbar, draw its preview about 1 cm above the finger (about 155 px
    on the A72) and place it there.
- **Hit areas.** Give tappable things on the map a touch radius of at least 7 to 9 mm, however small
  they look at the current zoom.
- **Edge scrolling.** When zoomed in, `MapCamera.EdgeScroll` lets players keep drawing past the edge of
  the view. It's called in `Update` above.
- **Android's back gesture.** With gesture navigation, a swipe in from the left or right edge means Back.
  A road drag that starts right at the edge can trigger it. To handle this:
  - make Back open the pause menu rather than quit, so an accidental Back is harmless;
  - keep the playable map slightly inset from the left and right edges;
  - if needed, exclude up to 200 dp of each edge with `View.setSystemGestureExclusionRects` (Android 10
    and later) through a small Android plugin.
- **The Back button itself.** With the Input System, Back arrives as the Escape key:

```csharp
if (Keyboard.current != null && Keyboard.current.escapeKey.wasPressedThisFrame)
    OpenPauseMenu();
```

---

## Pinch zoom, pan and the auto-zoom toggle

### Setup

1. Add `MapCamera` to the gameplay camera. It is switched to orthographic. Assign the scene's
   `TouchGestures`.
2. Call `mapCamera.SetPlayArea(bounds)` when a level loads and every time the playable area grows.
3. Tune **Min Size** (closest zoom) and **Max Size** (furthest zoom). Max size grows automatically if the
   play area needs more room to fit.

Pinch zooms around the point between the fingers: the spot under your fingers stays under your fingers.
Two-finger drag pans. The view can't be dragged off the play area.

### What the auto-zoom toggle does

- **On** (default): the camera keeps the whole play area framed and eases out as the map grows. If the
  player pinches or pans, the camera hands control to them. Auto-zoom takes over again after 6 seconds
  without camera input (configurable) or straight away on **Recenter**.
- **Off**: the camera only moves when the player moves it. The furthest zoom-out still grows with the
  map, so everything stays reachable.

The setting is saved in PlayerPrefs. Hook it to a settings toggle and a recenter button:

```csharp
using UnityEngine;
using UnityEngine.UI;

public class CameraSettingsUI : MonoBehaviour
{
    [SerializeField] MapCamera mapCamera;
    [SerializeField] Toggle autoZoomToggle;
    [SerializeField] Button recenterButton;

    void Start()
    {
        autoZoomToggle.isOn = mapCamera.AutoZoom;
        autoZoomToggle.onValueChanged.AddListener(on => mapCamera.AutoZoom = on);
        recenterButton.onClick.AddListener(mapCamera.Recenter);
    }

    void Update()
    {
        recenterButton.gameObject.SetActive(mapCamera.IsManuallyOverridden);
    }
}
```

On a controller, **Y** recenters, the **right stick** pans, and **LT / RT** zoom out and in.

---

## Controllers: Razer Kishi V2 and others

### How Android and Unity see them

The Razer Kishi V2 for Android plugs into the phone's USB-C port. It shows up as a standard gamepad
with an Xbox-style layout. The Input System maps it to the generic `Gamepad` layout, exactly like:

- Xbox controllers
- DualShock 4 and DualSense
- 8BitDo and other controllers, over Bluetooth or USB

So **bind to `<Gamepad>/...` paths and never to a specific controller**, and every controller works.

Two Kishi V2 buttons are handled by Razer's Nexus app rather than your game: the Razer button and the
two programmable M buttons. Players can remap the M buttons to standard buttons in that app.

The phone's touchscreen stays usable while it sits in the Kishi, so players will mix touch and buttons.
`ControllerSupport` switches mode based on whichever was used last.

### Setup

1. Create a **Screen Space Overlay** canvas called "Cursor Canvas" with a high Sort Order, such as
   1000. Inside it, add an Image called "Cursor" (32 to 48 px arrow or ring) with **Raycast Target**
   off.
2. Create a separate empty object called "Virtual Mouse". Don't use the Cursor itself, because the
   cursor object gets hidden in touch mode. Add **Virtual Mouse Input** (from the Input System) and
   set:
   - Cursor Mode: **Software Cursor**
   - Cursor Transform: the Cursor image
   - Cursor Speed: about 1.2 × screen height per second. Set it from code at startup
     (`virtualMouse.cursorSpeed = Screen.height * 1.2f`) so it feels the same on every resolution.
   - Stick Action: `<Gamepad>/leftStick`
   - Left Button Action: `<Gamepad>/buttonSouth` (A draws and clicks)
   - Right Button Action: `<Gamepad>/buttonWest` (X erases)
   - Scroll Wheel Action: leave empty, because zoom is on the triggers.
3. Add `ControllerSupport` to one object in the scene and assign the Virtual Mouse and the
   `MapCamera`.
4. Make sure the **EventSystem** uses **Input System UI Input Module**. The old Standalone Input Module
   sees neither gamepads nor the virtual mouse.
5. **Your existing mouse code now drives the controller too.** The virtual mouse becomes
   `Mouse.current`, and its left and right buttons are A and X.
   - If that code uses the legacy `Input.GetMouseButton` and `Input.mousePosition`, port it to the
     Input System first (`Mouse.current.leftButton`, `Mouse.current.position`, or Input Actions).
   - The legacy Input Manager can't see virtual devices.

If the cursor doesn't line up with what it clicks, give the Cursor Canvas a Canvas Scaler set to
*Constant Pixel Size*.

### Button map

| Control | During play | In menus |
| --- | --- | --- |
| Left stick | Move cursor | Navigate |
| A | Hold to draw, place or click | Confirm |
| X | Hold to erase | — |
| B | Cancel / close panel (your code) | Back |
| Y | Recenter camera | — |
| Right stick | Pan | — |
| LT / RT | Zoom out / in | — |
| LB / RB | Previous / next toolbar item (your code) | Switch tab (your code) |
| D-pad | Free, e.g. toolbar selection (your code) | Navigate |
| Start (≡) | Pause (`ControllerSupport.PausePressed`) | Resume |
| Select (⧉) | Free, e.g. game speed (your code) | — |

### Menus

Call these whenever a menu opens or closes. That includes pause, settings, game over and any upgrade or
choice screen shown mid-game.

```csharp
ControllerSupport.Instance.OpenMenu(firstButton.gameObject);  // menu shown
ControllerSupport.Instance.CloseMenu();                       // back to play
```

In menus, the cursor hides and the D-pad or stick moves the selection. This stops one press of A from
hitting both the button under the cursor and the selected button.

Set each Button's **Navigation** to Automatic, or Explicit for awkward layouts. Press **Visualize** in
the Button inspector to check the arrows. Every menu must be fully usable with the D-pad alone.

### Disconnects and prompts

Pause when the controller goes away:

```csharp
void OnEnable()  => ControllerSupport.ControllerDisconnected += ShowControllerLostPause;
void OnDisable() => ControllerSupport.ControllerDisconnected -= ShowControllerLostPause;
```

When the controller reconnects, the Input System restores it by itself, and the next button press
switches back to gamepad mode.

Show button prompts only while `ControllerSupport.Mode == InputMode.Gamepad`; listen to
`ControllerSupport.ModeChanged`. Pick the glyph set from the controller type:

- PlayStation pads derive from `UnityEngine.InputSystem.DualShock.DualShockGamepad`, so show ✕ ○ □ △.
- Show A B X Y for everything else, including the Kishi V2.

---

## Save system

### Three kinds of data

| Data | Where | Examples |
| --- | --- | --- |
| Settings | `PlayerPrefs` | volume, auto-zoom, frame rate, battery saver |
| Profile | `SaveSystem` slot `"profile"` | unlocked maps, best scores, statistics |
| Run in progress | `SaveSystem` slot `"run"` | everything needed to continue a game exactly where it was |

Achievements keep their own slot.

`SaveSystem` writes to a temp file, moves it into place only when it's complete, keeps the previous
save as a backup, and checks a checksum on load. A save is never left half-written, even if Android
kills the app mid-save or the battery dies.

### What a run save holds

For a map or road-building game, save:

- the map or level id, the random seed and the random generator's current state
- the game clock, day or week counter, score and game speed
- the item inventory and any pending choice the player hasn't made yet
- every piece the player placed: road tiles, bridges, junctions and so on
- every building and destination, with its position, colour and timers

Don't save anything you can rebuild:

- cars and their routes
- meshes
- pathfinding caches

Rebuild those from the saved pieces after loading, then let the simulation spawn cars as usual. This
keeps saves to a few kilobytes and fast to write.

Put the data in plain `[Serializable]` classes with public fields. `JsonUtility` skips dictionaries,
properties and polymorphic fields, so use lists of small structs. If you really need more, switch to
Newtonsoft Json (`com.unity.nuget.newtonsoft-json`) and add a `link.xml` so IL2CPP stripping doesn't
remove what it needs.

### When to save

Android may kill a backgrounded app without warning, and `OnApplicationQuit` often never runs on
phones. So:

- **always save when the app goes to the background**;
- **pause when focus is lost**, for example when the notification shade or a call screen covers the
  game;
- autosave at natural checkpoints, such as each new day or week, and every minute or so during play;
- delete the run save at game over.

```csharp
using UnityEngine;

public class RunAutosave : MonoBehaviour
{
    const string Slot = "run";
    const int Version = 1;
    const float Interval = 60f;

    float nextAutosave;

    void OnEnable()
    {
        AppLifecycle.Backgrounded += SaveRun;
        AppLifecycle.FocusLost += PauseGame;
    }

    void OnDisable()
    {
        AppLifecycle.Backgrounded -= SaveRun;
        AppLifecycle.FocusLost -= PauseGame;
    }

    void Update()
    {
        if (Time.unscaledTime >= nextAutosave)
        {
            nextAutosave = Time.unscaledTime + Interval;
            SaveRun();
        }
    }

    public void SaveRun()
    {
        if (YourGame.RunInProgress)
            SaveSystem.Save(Slot, YourGame.CaptureRunState(), Version);
    }

    public void OnGameOver() => SaveSystem.Delete(Slot);

    void PauseGame() => YourGame.SetPaused(true);
}
```

On the title screen, offer **Continue** when
`SaveSystem.TryLoad("run", out RunState state, out int version)` succeeds.

`SaveSystem.Save` returns `false` if the write failed, for example because storage is full. The
previous save is untouched in that case. Tell the player ("Couldn't save, free up some space") rather
than failing silently.

### Changing the save format later

Bump the version number whenever the run or profile layout changes. On load, compare versions:

- fill new fields with defaults (migrate), or
- if migration isn't worth it, discard the old run, but **never** the profile.

Test loading a save from the previous release before every update.

### Backups and moving to a new phone

- **Android Auto Backup** copies the app's files, including `Application.persistentDataPath`, to the
  player's Google account for free. It does this unless your manifest sets `android:allowBackup="false"`.
- For syncing between devices, use **Play Games Saved Games**. Enable it in Play Console and use the
  plugin's `PlayGamesPlatform.Instance.SavedGame`. Sync the profile; the run doesn't need it.

---

## Achievements

`Achievements.cs` keeps progress and unlocks on the device, so they work offline and without sign-in.
It pushes unlocks to Google Play Games whenever the player is signed in, and re-sends them on every
sign-in, so nothing earned offline is lost.

### Play Console

1. **Play Games Services → Setup and management → Configuration**:
   - Create the Play Games Services project.
   - Add an **Android credential** with your package name and the **SHA-1 of every key that signs your
     builds**: your upload key and the Play App Signing key from *Setup → App integrity*.
2. **Achievements**:
   - Add each one with a name, description, 512 × 512 icon and points.
   - Make them **standard** achievements. The script counts progress locally and unlocks when the
     target is reached.
   - Then press **Get resources** and copy the Android XML.
3. **Testers**: add your Google accounts so you can test before publishing the Play Games configuration.

### Unity

1. Import the **Google Play Games plugin for Unity**, version 11 or newer, from its GitHub releases
   page (`playgameservices/play-games-plugin-for-unity`).
2. Open **Window → Google Play Games → Setup → Android setup**, paste the XML, and name the constants
   class, for example `GPGSIds`.
3. Run **Assets → External Dependency Manager → Android Resolver → Force Resolve**.
4. In **Player Settings → Other Settings → Scripting Define Symbols**, add `PLAY_GAMES_SERVICES`.
   Without this define, the script compiles and runs local-only, which is handy for development.
5. Add `Achievements` to your bootstrap object. Fill in the definitions:
   - **Id**: your own name, such as `first_bridge`.
   - **Play Games Id**: the value of `GPGSIds.achievement_...`.
   - **Target**: 1 for one-shot achievements, or the count for counters.

Report from game code:

```csharp
Achievements.Instance.Report("first_bridge");   // one-shot: unlocks now
Achievements.Instance.Report("deliver_1000");   // counter: +1 per delivery, unlocks at the target
```

Listen to `Achievements.Instance.Unlocked` to show an in-game toast. An in-game list can use
`Progress(id)` and `IsUnlocked(id)`. An "Achievements" button calls `ShowPlayGamesUI()`, which asks
the player to sign in first if needed.

The current Play Games plugin signs players in automatically at launch and has no sign-out.

If you'd rather show progress bars inside the Play Games UI, make counters **incremental** in Play
Console and also send the local count with the plugin's `SetStepsAtLeast`. That call is safe to repeat.

### Testing

- Test on a build signed with a key whose SHA-1 is in the credential, while signed in as a tester.
- If sign-in always fails, the cause is nearly always that SHA-1 check:
  - local builds are signed with your upload key;
  - builds installed from Play are signed with the Play App Signing key.
- A hidden debug menu that fires each achievement saves a lot of time.

---

## Performance and battery

### Frame rate

Unity on Android runs at **30 fps unless you set `Application.targetFrameRate`**. `PerformanceSettings`
handles this:

- **60 fps** by default. **30** is a battery-saver option. **90** is a smooth option for high-refresh
  screens. On the A72, 90 needs *Settings → Display → Motion smoothness* set to the high (90 Hz) option.
  Offer 90 only when `PerformanceSettings.DisplayRefreshRate >= 90`.
- Call `PerformanceSettings.Instance.SetInGameplay(true)` when a run starts or resumes, and `false` for
  menus, pause and game over. Outside gameplay, it renders every second frame (input still runs every
  frame) and caps at 60.
- The screen stays awake only during play, so a paused game lets the phone sleep normally.
- **Battery saver when low**: below 20% and not charging, it drops to 30 fps. This is on by default.

When testing on Samsung phones, check that **Game Booster** isn't capping the frame rate.

### GPU

Set these on the URP asset:

- **HDR**: off.
- **MSAA**: 4x. Thin roads and lines look jagged without anti-aliasing, and MSAA is cheap on mobile
  tile-based GPUs. Use 2x on the Battery quality level.
- **Shadows**: off, or a single low-resolution, short-distance shadow if the art needs it.
- **Post-processing**: off, or one cheap effect. Leave **Depth Texture** and **Opaque Texture** off
  unless a shader needs them.
- **SRP Batcher**: on. Use GPU instancing for repeated meshes such as vehicles, buildings and trees.

Elsewhere:

- **Overdraw** (layers of transparent pixels) is the usual GPU killer on phones. Avoid big transparent
  full-screen overlays and stacked translucent panels.
- **Textures**: ASTC (6×6 for most art, 4×4 for UI or fine detail), sprite atlases, and no mipmaps on
  UI.

### CPU

- **Simulation**: recompute routes only when the road network changes, not every frame. Spread heavy
  pathfinding across frames, or move it to the Job System with Burst, which compiles to ARM64 NEON code.
- **Pooling**: reuse vehicles and other frequently spawned objects. Avoid `Instantiate` and `Destroy` in
  hot paths.
- **Garbage**: aim for zero allocations per frame in `Update`. Common causes are LINQ, string building,
  boxing and `new List` every frame. Check the Profiler's **GC Alloc** column.
- **Physics**: if you don't use it, stop it simulating
  (`Physics.simulationMode = SimulationMode.Script` in Unity 2022.2 and later).
- **Meshes**: rebuild only the chunk that changed, not the whole network.

### UI

- Put frequently changing elements, such as score and clock, on their own Canvas, so changing them
  doesn't rebuild the static UI.
- Turn off **Raycast Target** on graphics that aren't interactive.
- Avoid Layout Groups on elements that change every frame.

### Heat

Phones slow down (throttle) after 10 to 20 minutes of sustained load. Leave headroom:

- At 60 fps, aim for CPU and GPU frame times of about 11 ms or less (the frame budget is 16.7 ms).
- At 90 fps, aim for about 8 ms or less (the frame budget is 11.1 ms).

Unity's **Adaptive Performance** package, with its Android provider, reports thermal warnings. Use them
to switch to 30 fps or the Battery quality level before the system throttles.

### Measuring

- **CPU**: Development Build with **Autoconnect Profiler**, then the Unity Profiler over USB. The
  **Android Logcat** package shows device logs in the Editor.
- **GPU**: Android GPU Inspector or Snapdragon Profiler. The A72 has an Adreno GPU.
- **Battery and heat**: play 30 minutes at 60 fps, then 30 minutes at 30 fps, and compare battery drop
  and temperature. `adb shell dumpsys battery` shows both. Its temperature is in tenths of a degree.

---

## Build and release

1. During development, use **Build And Run** with an APK on the A72 over USB.
2. For release, build an **App Bundle (.aab)** and upload it to the **Internal testing** track first.
3. Read the **Pre-launch report**. Google runs your build on real devices and reports crashes and UI
   problems.
4. Move to closed testing, then production. Watch **Android vitals** for crash and ANR rates.
5. Set up crash reporting with symbols for IL2CPP stack traces: Build Settings → **Create symbols.zip**,
   uploaded to Play Console or your crash reporter.
6. Fill in the **Data safety** form accurately. Play Games and any analytics SDKs count.

---

## Test plan

**Devices**: the Galaxy A72 as the main target, plus:

- one 16:9 phone
- a 21:9 phone if you can get one
- a tablet (4:3 or 16:10)
- a low-end phone (3 GB RAM, Android 8 to 10)
- the Kishi V2 and a Bluetooth controller (Xbox or DualSense)

**Screen and orientation**
- [ ] Starts in landscape even when the phone is held upright. Follows a 180° flip. Never goes portrait.
- [ ] On the A72, flipped both ways, no HUD element sits under the punch-hole, a rounded corner or the
  gesture bar.
- [ ] Buttons are at least 48 dp and text is readable on phone and tablet. Nothing overlaps at 4:3 or
  21:9.
- [ ] The map and background fill the screen at every aspect ratio.

**Touch**
- [ ] Tap, drag to draw, long press then drag to erase, pinch, and two-finger pan all work.
- [ ] A pinch never leaves stray tiles. Lifting one finger mid-pinch never draws.
- [ ] Touches that start on buttons never draw on the map.
- [ ] Drawing near the left or right edge doesn't throw the player out. Back opens the pause menu.
- [ ] Auto-zoom on: the camera follows the growing map, and eases back after a pinch or on Recenter.
  Auto-zoom off: the camera stays where the player put it.

**Controllers**
- [ ] Kishi V2: the cursor moves smoothly, A draws, X erases, the triggers zoom, the right stick pans,
  Y recenters and Start pauses.
- [ ] A Bluetooth controller can connect mid-game. Disconnecting pauses the game. Reconnecting resumes
  control.
- [ ] Switching between touch and controller hides or shows the cursor and the button prompts.
- [ ] Every menu works with the D-pad alone.

**Saves**
- [ ] Mid-run: press Home, swipe the app away in Recents, relaunch. The run continues where it was.
- [ ] Force-stop during play (Settings → Apps → Force stop). The latest autosave loads.
- [ ] Saving works in airplane mode and with nearly full storage. A save from the previous version loads.

**Achievements**
- [ ] Each achievement unlocks exactly once. Unlocks earned offline appear in Play Games after going
  online.
- [ ] Declining Play Games sign-in breaks nothing. The Achievements button offers sign-in.

**Performance and battery**
- [ ] A 30-minute session on the A72 at 60 fps stays smooth, with stable frame times, no memory growth,
  and a warm but not hot phone.
- [ ] Menus and pause render less. The screen sleeps normally when left on a menu.
- [ ] The 90 fps option appears only on 90 Hz screens and actually reaches 90.
- [ ] The battery saver kicks in below 20% when not charging.

**Interruptions**
- [ ] An incoming call, the notification shade, an alarm, locking and unlocking the screen, and
  split-screen (if allowed) all pause and resume cleanly.

---

## Common pitfalls

- **Legacy `Input` class** code doesn't see touches from Enhanced Touch or the virtual mouse. Port it to
  the Input System.
- **Standalone Input Module** on the EventSystem: controllers and the virtual mouse can't use the UI.
  Use **Input System UI Input Module**.
- **A PhysicsRaycaster on the gameplay camera** makes `TouchGestures` treat every map touch as a UI
  touch.
- **"Render outside safe area" off**: Unity letterboxes the cutout and `SafeAreaFitter` does nothing.
- **No `Application.targetFrameRate`**: the game is stuck at 30 fps on Android.
- **Saving only in `OnApplicationQuit`**: progress is lost whenever Android kills the app in the
  background.
- **Dictionaries in save data**: `JsonUtility` silently drops them.
- **Play Games sign-in always fails**: the signing key's SHA-1 is missing from the credential.
- **Testing only in the Editor**: the Device Simulator (Window → General → Device Simulator) is great
  for layout and safe areas. Touch feel, controllers, performance, heat and app lifecycle need the real
  phone.
