// NOT RUNTIME-TESTED. Written for Unity 2021.3 LTS or newer but never run in Unity or on a device,
// and never used with a real touchscreen or controller. It is only compile-checked against
// hand-written stand-ins for the UnityEngine API (tests/UnityApiStubs). The gesture, deadzone,
// button and cursor logic it calls into (core/) is unit-tested with dotnet.

using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Events;
using UnityMobileKit.Controllers;
using UnityMobileKit.Geometry;
using UnityMobileKit.Gestures;
using UnityMobileKit.ScreenLayout;
#if UMK_UGUI
using UnityEngine.EventSystems;
#endif
#if UMK_INPUT_SYSTEM && ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem.EnhancedTouch;
using InputSystemGamepad = UnityEngine.InputSystem.Gamepad;
using InputSystemTouch = UnityEngine.InputSystem.EnhancedTouch.Touch;
using InputSystemTouchPhase = UnityEngine.InputSystem.TouchPhase;
#endif

namespace UnityMobileKit.Runtime
{
    /// <summary>
    /// Reads touches and the current controller once per frame and turns them into gestures, button
    /// presses with auto-repeat, a virtual cursor and a touch-or-controller mode, using the core.
    /// <para>
    /// Uses the Input System package when it is installed and enabled in Player Settings, otherwise
    /// the legacy Input Manager, which gives touch only: controllers need the Input System. Stick
    /// deadzones then come from the Input System (Project Settings > Input System Package > Default
    /// Deadzone Min/Max). In the Editor, test touch with the Device Simulator.
    /// </para>
    /// Runs before other scripts so their Update sees this frame's input.
    /// </summary>
    [DefaultExecutionOrder(-100)]
    [DisallowMultipleComponent]
    public sealed class MobileInput : MonoBehaviour
    {
        [Tooltip("Touches that start on UI (anything the EventSystem's raycasters hit) don't pan, zoom or tap the world. Needs the uGUI package.")]
        [SerializeField] private bool ignoreTouchesStartingOnUi = true;

        [Tooltip("Trigger travel ignored at rest, so worn triggers don't zoom or switch to controller mode.")]
        [SerializeField, Range(0f, 0.9f)] private float triggerDeadzone = 0.1f;

        [Tooltip("Raised when the controller in use disconnects. Pause the game here.")]
        [SerializeField] private UnityEvent onControllerDisconnected = new UnityEvent();

        private readonly List<TouchSample> _touches = new List<TouchSample>();
        private readonly HashSet<int> _presentIds = new HashSet<int>();
        private readonly HashSet<int> _uiTouchIds = new HashSet<int>();
        private Predicate<int> _isGone;
        private GestureRecognizer _gestures;
        private AxisDeadzone _trigger;
        private int _screenWidth;
        private int _screenHeight;
        private Rect _safeArea;
        private Float2 _lastTouch;
        private bool _hasLastTouch;
        private bool _touchCanceled;
#if UMK_UGUI
        private readonly List<RaycastResult> _uiHits = new List<RaycastResult>();
#endif

        public GestureFrame Gestures { get; private set; } = GestureFrame.None;

        /// <summary>This frame's controller input, triggers deadzone-filtered. All zero without a controller.</summary>
        public GamepadState Pad { get; private set; }

        public ButtonTracker Buttons { get; } = new ButtonTracker();

        public InputModeTracker Mode { get; } = new InputModeTracker();

        /// <summary>Moved by the left stick in controller mode. Draw a pointer here while <see cref="Mode"/> is Gamepad.</summary>
        public VirtualCursor VirtualCursor { get; private set; }

        /// <summary>A touch tap, or South (A / Cross) at the virtual cursor in controller mode. Screen pixels, origin bottom-left.</summary>
        public event Action<Vector2> PointerTapped;

        private void Awake()
        {
            _gestures = new GestureRecognizer(Screen.dpi);
            _trigger = new AxisDeadzone(triggerDeadzone);
            _isGone = id => !_presentIds.Contains(id);
            VirtualCursor = new VirtualCursor(Mathf.Max(1, Screen.width), Mathf.Max(1, Screen.height));
            Mode.PauseRequested += onControllerDisconnected.Invoke;
            Mode.ModeChanged += OnModeChanged;
        }

#if UMK_INPUT_SYSTEM && ENABLE_INPUT_SYSTEM
        private void OnEnable() => EnhancedTouchSupport.Enable();
#endif

        private void OnDisable()
        {
#if UMK_INPUT_SYSTEM && ENABLE_INPUT_SYSTEM
            EnhancedTouchSupport.Disable();
#endif
            // Other scripts read these every frame; don't leave a drag or stick deflection behind.
            Gestures = GestureFrame.None;
            Pad = default;
            if (_gestures != null) _gestures.Cancel();
        }

        private void Update()
        {
            double now = Time.unscaledTimeAsDouble;
            RefreshScreen();

            _touches.Clear();
            _presentIds.Clear();
            _touchCanceled = false;
            ReadTouches();
            _uiTouchIds.RemoveWhere(_isGone);
            if (_touchCanceled) _gestures.Cancel();
            if (_presentIds.Count > 0) Mode.NotifyTouch();
            Gestures = _gestures.Update(_touches, now);

            GamepadState raw = ReadGamepad(out bool connected);
            Mode.SetGamepadConnected(connected);
            Pad = new GamepadState(raw.LeftStick, raw.RightStick, _trigger.Apply(raw.LeftTrigger), _trigger.Apply(raw.RightTrigger), raw.Buttons);
            Buttons.Update(Pad.Buttons, now);
            Mode.NotifyGamepad(Pad);

            if (Mode.Mode == InputMode.Gamepad)
            {
                VirtualCursor.Update(Pad.LeftStick, Time.unscaledDeltaTime);
                if (Buttons.WasPressed(GamepadButtons.South)) PointerTapped?.Invoke(VirtualCursor.Position.ToVector2());
            }
            if (Gestures.Tapped) PointerTapped?.Invoke(Gestures.TapPosition.ToVector2());
        }

        private void OnApplicationFocus(bool hasFocus)
        {
            // Fingers that are down when focus goes away may never report lifting.
            if (!hasFocus && _gestures != null) _gestures.Cancel();
        }

        private void OnModeChanged(InputMode mode)
        {
            // Continue from where the player last touched rather than from the old cursor position.
            if (mode == InputMode.Gamepad && _hasLastTouch) VirtualCursor.Warp(_lastTouch);
        }

        private void RefreshScreen()
        {
            int width = Screen.width;
            int height = Screen.height;
            if (width <= 0 || height <= 0) return;
            Rect safeArea = Screen.safeArea;
            if (width == _screenWidth && height == _screenHeight && safeArea == _safeArea) return;

            _screenWidth = width;
            _screenHeight = height;
            _safeArea = safeArea;
            VirtualCursor.SetScreen(width, height);
            RectF usable = SafeArea.Sanitize(new RectF(safeArea.x, safeArea.y, safeArea.width, safeArea.height), width, height);
            VirtualCursor.SetArea(usable.Min, usable.Max);
        }

        private void ReadTouches()
        {
#if UMK_INPUT_SYSTEM && ENABLE_INPUT_SYSTEM
            var active = InputSystemTouch.activeTouches;
            for (int i = 0; i < active.Count; i++)
            {
                InputSystemTouch touch = active[i];
                InputSystemTouchPhase phase = touch.phase;
                AddTouch(touch.touchId, touch.screenPosition,
                         began: phase == InputSystemTouchPhase.Began,
                         lifted: phase == InputSystemTouchPhase.Ended || phase == InputSystemTouchPhase.Canceled,
                         canceled: phase == InputSystemTouchPhase.Canceled);
            }
#elif ENABLE_LEGACY_INPUT_MANAGER
            int count = Input.touchCount;
            for (int i = 0; i < count; i++)
            {
                UnityEngine.Touch touch = Input.GetTouch(i);
                TouchPhase phase = touch.phase;
                AddTouch(touch.fingerId, touch.position,
                         began: phase == TouchPhase.Began,
                         lifted: phase == TouchPhase.Ended || phase == TouchPhase.Canceled,
                         canceled: phase == TouchPhase.Canceled);
            }
#endif
        }

        private void AddTouch(int id, Vector2 position, bool began, bool lifted, bool canceled)
        {
            _presentIds.Add(id);
            _lastTouch = position.ToFloat2();
            _hasLastTouch = true;

            // Decided once per touch, when it starts: a drag that begins on a button and slides onto
            // the map must not pan the map. Ids are reused, so every new touch is checked afresh.
            if (began)
            {
                if (StartsOnUi(position)) _uiTouchIds.Add(id);
                else _uiTouchIds.Remove(id);
            }
            if (_uiTouchIds.Contains(id)) return;

            if (canceled) _touchCanceled = true;
            if (!lifted) _touches.Add(new TouchSample(id, position.ToFloat2()));
        }

        private bool StartsOnUi(Vector2 position)
        {
            if (!ignoreTouchesStartingOnUi) return false;
#if UMK_UGUI
            EventSystem eventSystem = EventSystem.current;
            if (eventSystem == null) return false;
            var pointer = new PointerEventData(eventSystem) { position = position };
            _uiHits.Clear();
            eventSystem.RaycastAll(pointer, _uiHits);
            return _uiHits.Count > 0;
#else
            return false;
#endif
        }

        private static GamepadState ReadGamepad(out bool connected)
        {
#if UMK_INPUT_SYSTEM && ENABLE_INPUT_SYSTEM
            InputSystemGamepad pad = InputSystemGamepad.current;
            if (pad != null)
            {
                connected = true;
                GamepadButtons buttons = GamepadButtons.None;
                if (pad.buttonSouth.isPressed) buttons |= GamepadButtons.South;
                if (pad.buttonEast.isPressed) buttons |= GamepadButtons.East;
                if (pad.buttonWest.isPressed) buttons |= GamepadButtons.West;
                if (pad.buttonNorth.isPressed) buttons |= GamepadButtons.North;
                if (pad.leftShoulder.isPressed) buttons |= GamepadButtons.LeftShoulder;
                if (pad.rightShoulder.isPressed) buttons |= GamepadButtons.RightShoulder;
                if (pad.startButton.isPressed) buttons |= GamepadButtons.Start;
                if (pad.selectButton.isPressed) buttons |= GamepadButtons.Select;
                if (pad.dpad.up.isPressed) buttons |= GamepadButtons.DpadUp;
                if (pad.dpad.down.isPressed) buttons |= GamepadButtons.DpadDown;
                if (pad.dpad.left.isPressed) buttons |= GamepadButtons.DpadLeft;
                if (pad.dpad.right.isPressed) buttons |= GamepadButtons.DpadRight;
                if (pad.leftStickButton.isPressed) buttons |= GamepadButtons.LeftStick;
                if (pad.rightStickButton.isPressed) buttons |= GamepadButtons.RightStick;
                return new GamepadState(pad.leftStick.ReadValue().ToFloat2(), pad.rightStick.ReadValue().ToFloat2(),
                                        pad.leftTrigger.ReadValue(), pad.rightTrigger.ReadValue(), buttons);
            }
#endif
            connected = false;
            return default;
        }
    }
}
