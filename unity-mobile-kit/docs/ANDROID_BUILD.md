# Building a debug APK with Unity Mobile Kit

How to build an installable debug APK from **a Unity project you own** that uses this kit. The kit
contains no game, assets or scenes; it is the mobile plumbing (touch, controller, camera, safe
area, orientation, frame rate, saves, achievements) that your project's content plugs into.

These steps were written from Unity's documentation. **They have not been run here**: this
repository is developed without a Unity install or an Android device, so no APK was built.

## 1. Unity version and modules

- **Unity 2022.3 LTS**, latest patch. The kit itself needs 2021.3 LTS or newer.
- In Unity Hub > Installs > (your 2022.3 install) > Add modules, tick **Android Build Support**
  and both of its children, **OpenJDK** and **Android SDK & NDK Tools**. These provide the SDK,
  NDK and JDK that Unity pins for that editor version, so you don't install them separately.
- Packages (Window > Package Manager): **Input System** (needed for controllers such as a Razer
  Kishi; also handles touch). **uGUI** is included by default.

## 2. Add the kit

Copy `core/UnityMobileKit.Core` and `unity/Runtime` into `Assets/UnityMobileKit/` (not `tests/`,
and no `bin/` or `obj/` folders). Set up the scene as described in the main README under
"Using it in Unity".

## 3. Player Settings (Edit > Project Settings > Player > Android tab)

| Setting | Value | Why |
|---|---|---|
| Other Settings > Identification > Package Name | e.g. `com.yourstudio.yourgame` | Must be unique on the device |
| Other Settings > Identification > Minimum API Level | 26 (Android 8.0) or higher | Covers current phones, including a Galaxy A72 |
| Other Settings > Configuration > Scripting Backend | **IL2CPP** | Required for 64-bit (ARM64) Android |
| Other Settings > Configuration > Target Architectures | **ARM64** (ARMv7 optional) | Modern phones are 64-bit |
| Other Settings > Configuration > Active Input Handling | **Input System Package (New)** or **Both** | `MobileInput` reads controllers through the Input System |
| Resolution and Presentation > Default Orientation | **Auto Rotation**, only Landscape Left and Landscape Right ticked | Landscape-only before Unity starts (manifest, splash) |
| Resolution and Presentation > Optimized Frame Pacing | On | Smoother frame pacing at the rate `FrameRateDriver` sets |

## 4. Build the debug APK

1. File > Build Settings > select **Android** > **Switch Platform**.
2. **Add Open Scenes** (or drag your scenes into "Scenes In Build").
3. Tick **Development Build**. Leave **Build App Bundle (Google Play)** unticked so you get an
   `.apk` rather than an `.aab`.
4. Click **Build**, choose a folder, and wait. The first IL2CPP build takes a while.

Unity signs development builds with a debug key automatically, so no keystore is needed for
testing.

## 5. Install it on the phone

1. On the phone: Settings > About phone > Software information > tap **Build number** seven times
   to unlock Developer options, then Settings > Developer options > turn on **USB debugging**.
2. Connect by USB and accept the "Allow USB debugging?" prompt.
3. Either use **Build And Run** in step 4, or install the APK you built:

   ```
   adb install -r path/to/YourGame.apk
   ```

   `adb` ships with Unity's Android module under the editor's
   `Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/` folder.

## 6. What to check on the device

These are the behaviours the kit's code implements but that have never been observed on hardware:

- One finger drags the map; two fingers pinch-zoom around their midpoint; taps on UI don't move it.
- The HUD panel stays clear of the camera punch-hole and the rounded corners, in both landscape
  directions.
- With a controller: the left stick moves a cursor, A taps at the cursor, the right stick pans,
  the triggers zoom; disconnecting the controller mid-game raises the pause event.
- Frame rate: Auto follows the display (90 Hz on a Galaxy A72) and drops to 30 with battery saver
  on, at 15% battery or less when unplugged, or when the phone gets hot.
- Settings and achievement progress survive swiping the app away from the recent-apps screen.
