using System;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.EnhancedTouch;
using UnityEngine.InputSystem.UI;
using Touch = UnityEngine.InputSystem.EnhancedTouch.Touch;

public enum InputMode { Touch, Gamepad }

/// <summary>
/// Controller support for anything Android exposes as a standard gamepad: Razer Kishi V2, Xbox,
/// DualShock 4 / DualSense, 8BitDo and so on. The Input System maps them all onto the same Gamepad
/// layout (buttonSouth = A / Cross, buttonEast = B / Circle...), so nothing here is controller-specific.
///
/// - Switches between touch and gamepad mode based on whichever the player used last.
/// - During play, shows the VirtualMouseInput cursor: left stick moves it and the virtual mouse buttons
///   (bound to A and X in the VirtualMouseInput component) draw and erase through your normal mouse code.
///   Right stick pans and the triggers zoom the MapCamera; Y recenters it.
/// - In menus, hides the cursor and relies on normal UI navigation (D-pad/stick, A to confirm, B to go
///   back), so one press can never hit both the button under the cursor and the selected button.
/// - Raises ControllerDisconnected when the active controller goes away so the game can pause.
/// </summary>
public class ControllerSupport : MonoBehaviour
{
    [Tooltip("Put this on a separate object from the cursor image; the cursor object is hidden in touch mode.")]
    [SerializeField] VirtualMouseInput virtualMouse;
    [SerializeField] MapCamera mapCamera;
    [SerializeField, Range(0f, 0.9f)] float stickDeadzone = 0.2f;
    [Tooltip("Right-stick pan speed at full tilt, in screen heights per second.")]
    [SerializeField] float panSpeed = 0.9f;
    [Tooltip("Zoom speed at full trigger, as a zoom factor per second.")]
    [SerializeField] float zoomSpeed = 2.5f;

    public static ControllerSupport Instance { get; private set; }
    public static InputMode Mode { get; private set; } = InputMode.Touch;
    public static event Action<InputMode> ModeChanged;
    public static event Action ControllerDisconnected;
    public static event Action PausePressed;

    bool menuOpen;
    GameObject menuFirstSelected;

    void Awake()
    {
        Instance = this;
    }

    void OnDestroy()
    {
        if (Instance == this)
            Instance = null;
    }

    void OnEnable()
    {
        EnhancedTouchSupport.Enable();
        InputSystem.onDeviceChange += OnDeviceChange;
        SetMode(Gamepad.current != null ? InputMode.Gamepad : InputMode.Touch, true);
    }

    void OnDisable()
    {
        InputSystem.onDeviceChange -= OnDeviceChange;
        EnhancedTouchSupport.Disable();
    }

    /// <summary>Call when any menu, pause screen or upgrade picker opens.</summary>
    public void OpenMenu(GameObject firstSelected)
    {
        menuOpen = true;
        menuFirstSelected = firstSelected;
        RefreshCursorAndSelection();
    }

    /// <summary>Call when the menu closes and play resumes.</summary>
    public void CloseMenu()
    {
        menuOpen = false;
        menuFirstSelected = null;
        RefreshCursorAndSelection();
    }

    void Update()
    {
        Gamepad pad = Gamepad.current;
        if (Touch.activeTouches.Count > 0)
            SetMode(InputMode.Touch);
        else if (pad != null && HasInput(pad))
            SetMode(InputMode.Gamepad);

        if (pad == null || Mode != InputMode.Gamepad)
            return;

        if (pad.startButton.wasPressedThisFrame)
            PausePressed?.Invoke();

        if (menuOpen || mapCamera == null)
            return;

        if (pad.buttonNorth.wasPressedThisFrame)
            mapCamera.Recenter();

        Vector2 pan = pad.rightStick.ReadValue();
        if (pan.sqrMagnitude > stickDeadzone * stickDeadzone)
            mapCamera.PanByScreenDelta(-pan * panSpeed * Screen.height * Time.unscaledDeltaTime);

        float zoom = pad.rightTrigger.ReadValue() - pad.leftTrigger.ReadValue();
        if (Mathf.Abs(zoom) > stickDeadzone)
            mapCamera.ZoomBy(Mathf.Pow(zoomSpeed, zoom * Time.unscaledDeltaTime), CursorPosition());
    }

    void SetMode(InputMode mode, bool force = false)
    {
        if (mode == Mode && !force)
            return;
        Mode = mode;
        RefreshCursorAndSelection();
        ModeChanged?.Invoke(mode);
    }

    void RefreshCursorAndSelection()
    {
        bool gamepad = Mode == InputMode.Gamepad;
        bool showCursor = gamepad && !menuOpen;
        if (virtualMouse != null)
        {
            virtualMouse.enabled = showCursor;
            if (virtualMouse.cursorTransform != null)
                virtualMouse.cursorTransform.gameObject.SetActive(showCursor);
        }

        EventSystem eventSystem = EventSystem.current;
        if (eventSystem != null)
            eventSystem.SetSelectedGameObject(gamepad && menuOpen ? menuFirstSelected : null);
    }

    Vector2 CursorPosition()
    {
        if (virtualMouse != null && virtualMouse.enabled && virtualMouse.virtualMouse != null)
            return virtualMouse.virtualMouse.position.ReadValue();
        return new Vector2(Screen.width * 0.5f, Screen.height * 0.5f);
    }

    bool HasInput(Gamepad pad)
    {
        float deadzoneSquared = stickDeadzone * stickDeadzone;
        return pad.leftStick.ReadValue().sqrMagnitude > deadzoneSquared
            || pad.rightStick.ReadValue().sqrMagnitude > deadzoneSquared
            || pad.dpad.ReadValue().sqrMagnitude > 0f
            || pad.leftTrigger.ReadValue() > stickDeadzone
            || pad.rightTrigger.ReadValue() > stickDeadzone
            || pad.buttonSouth.isPressed || pad.buttonEast.isPressed
            || pad.buttonWest.isPressed || pad.buttonNorth.isPressed
            || pad.leftShoulder.isPressed || pad.rightShoulder.isPressed
            || pad.startButton.isPressed || pad.selectButton.isPressed
            || pad.leftStickButton.isPressed || pad.rightStickButton.isPressed;
    }

    void OnDeviceChange(InputDevice device, InputDeviceChange change)
    {
        if (!(device is Gamepad))
            return;
        bool lost = change == InputDeviceChange.Removed || change == InputDeviceChange.Disconnected;
        if (lost && Mode == InputMode.Gamepad && (Gamepad.current == null || Gamepad.current == device))
        {
            SetMode(InputMode.Touch);
            ControllerDisconnected?.Invoke();
        }
    }
}
