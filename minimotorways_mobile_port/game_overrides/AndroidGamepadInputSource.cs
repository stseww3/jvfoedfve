using System;
using System.Collections.Generic;
using Factory;
using RewiredConsts;
using UnityEngine;

/// <summary>
/// Android Gamepad & Razer Kishi V2 Input Bridge for RuntimeAppCommandSource.
/// Replaces Windows-only Rewired_DirectInput / Rewired_Windows polling on Android
/// with standard Android HID / Unity Input polling supporting:
///   - Razer Kishi V2 (USB-C HID, Vendor 0x1532, standard Android gamepad layout)
///   - Xbox Wireless Controller (Bluetooth / USB)
///   - Sony DualSense / DualShock 4
///   - 8BitDo & generic Android Bluetooth/USB gamepads
///   - Seamless live switching between Touchscreen and Controller without restart
///   - Hot-plug detection (Input.GetJoystickNames) and Android hardware Back button
/// </summary>
public sealed class AndroidGamepadInputSource
{
	private const float StickDeadzone = 0.18f;
	private const float TriggerThreshold = 0.45f;
	private const float DpadRepeatInitialDelay = 0.35f;
	private const float DpadRepeatInterval = 0.11f;
	private const float HotplugCheckInterval = 1.0f;

	private readonly Dictionary<int, bool> _previousButtons = new Dictionary<int, bool>();
	private readonly Dictionary<int, float> _previousAxes = new Dictionary<int, float>();
	private readonly Dictionary<int, float> _nextDpadRepeatTime = new Dictionary<int, float>();

	private float _lastHotplugCheckTime = -10f;
	private bool _hasConnectedGamepad;
	private string _activeGamepadName = string.Empty;

	public bool HasConnectedGamepad => _hasConnectedGamepad;
	public string ActiveGamepadName => _activeGamepadName;
	public bool IsRazerKishiConnected =>
		!string.IsNullOrEmpty(_activeGamepadName) &&
		(_activeGamepadName.IndexOf("Kishi", StringComparison.OrdinalIgnoreCase) >= 0 ||
		 _activeGamepadName.IndexOf("Razer", StringComparison.OrdinalIgnoreCase) >= 0);

	public event Action<string> GamepadConnected;
	public event Action GamepadDisconnected;

	public void Poll(
		IScope scope,
		InputState inputState,
		float appTime,
		List<IAppCommand> frameCommands)
	{
		CheckHotplug(appTime);

		// Always poll Android hardware Back key (KeyCode.Escape) -> InputAction.Back (7)
		if (Input.GetKeyDown(KeyCode.Escape))
		{
			EmitButtonEvent(scope, frameCommands, appTime, InputAction.Back, InputEventButtonState.JustDown);
		}
		else if (Input.GetKeyUp(KeyCode.Escape))
		{
			EmitButtonEvent(scope, frameCommands, appTime, InputAction.Back, InputEventButtonState.JustUp);
		}

		// Read analog sticks with radial deadzone
		Vector2 leftStick = ApplyRadialDeadzone(new Vector2(
			ReadAxisSafe("Horizontal", "Joy1Axis1"),
			ReadAxisSafe("Vertical", "Joy1Axis2", invertSecondary: true)));

		Vector2 rightStick = ApplyRadialDeadzone(new Vector2(
			ReadAxisSafe("RightStickHorizontal", "Joy1Axis3"),
			ReadAxisSafe("RightStickVertical", "Joy1Axis4", invertSecondary: true)));

		PollAxis(scope, inputState, frameCommands, appTime, InputAction.MoveHorizontal, leftStick.x);
		PollAxis(scope, inputState, frameCommands, appTime, InputAction.MoveVertical, leftStick.y);
		PollAxis(scope, inputState, frameCommands, appTime, InputAction.PanHorizontal, rightStick.x);
		PollAxis(scope, inputState, frameCommands, appTime, InputAction.PanVertical, rightStick.y);

		// Read D-Pad (axes 6 & 7 on Android HID, plus KeyCode fallbacks)
		float dpadX = ReadAxisSafe("DPadHorizontal", "Joy1Axis6");
		float dpadY = ReadAxisSafe("DPadVertical", "Joy1Axis7", invertSecondary: true);

		bool dpadUp = dpadY > 0.5f || Input.GetKey(KeyCode.UpArrow);
		bool dpadDown = dpadY < -0.5f || Input.GetKey(KeyCode.DownArrow);
		bool dpadRight = dpadX > 0.5f || Input.GetKey(KeyCode.RightArrow);
		bool dpadLeft = dpadX < -0.5f || Input.GetKey(KeyCode.LeftArrow);

		PollDpadDirection(scope, frameCommands, appTime, InputAction.NavigateUp, dpadUp);
		PollDpadDirection(scope, frameCommands, appTime, InputAction.NavigateDown, dpadDown);
		PollDpadDirection(scope, frameCommands, appTime, InputAction.NavigateRight, dpadRight);
		PollDpadDirection(scope, frameCommands, appTime, InputAction.NavigateLeft, dpadLeft);

		// Standard Android Gamepad / Razer Kishi V2 button mappings:
		//   JoystickButton0 = South (A) -> Confirm (2)
		//   JoystickButton1 = East (B)  -> Back / Cancel (7)
		//   JoystickButton2 = West (X)  -> DrawModeToggle (9)
		//   JoystickButton3 = North (Y) -> ToggleZoomAction (31)
		//   JoystickButton4 = L1 / LB   -> DecreaseSpeed (11) & PageLeft (42)
		//   JoystickButton5 = R1 / RB   -> IncreaseSpeed (10) & PageRight (43)
		//   JoystickButton6 = Select/Share -> OpenElectiveUpgradeScreen (44)
		//   JoystickButton7 = Start/Menu/Options -> Menu (8) & TogglePause (16)
		//   JoystickButton8 = L3 (Left Stick Click) -> LeftStickPress (36) & ToggleGameUI (32)
		//   JoystickButton9 = R3 (Right Stick Click) -> RightStickPress (37) & ToggleZoomAction (31)
		PollButton(scope, frameCommands, appTime, InputAction.Confirm,
			Input.GetKey(KeyCode.JoystickButton0) || Input.GetKey(KeyCode.Return));
		PollButton(scope, frameCommands, appTime, InputAction.Back,
			Input.GetKey(KeyCode.JoystickButton1));
		PollButton(scope, frameCommands, appTime, InputAction.DrawModeToggle,
			Input.GetKey(KeyCode.JoystickButton2));
		PollButton(scope, frameCommands, appTime, InputAction.ToggleZoomAction,
			Input.GetKey(KeyCode.JoystickButton3) || Input.GetKey(KeyCode.JoystickButton9));

		bool lbHeld = Input.GetKey(KeyCode.JoystickButton4);
		bool rbHeld = Input.GetKey(KeyCode.JoystickButton5);
		PollButton(scope, frameCommands, appTime, InputAction.DecreaseSpeed, lbHeld);
		PollButton(scope, frameCommands, appTime, InputAction.PageLeft, lbHeld);
		PollButton(scope, frameCommands, appTime, InputAction.IncreaseSpeed, rbHeld);
		PollButton(scope, frameCommands, appTime, InputAction.PageRight, rbHeld);

		PollButton(scope, frameCommands, appTime, InputAction.OpenElectiveUpgradeScreen,
			Input.GetKey(KeyCode.JoystickButton6));

		bool startHeld = Input.GetKey(KeyCode.JoystickButton7);
		PollButton(scope, frameCommands, appTime, InputAction.Menu, startHeld);
		PollButton(scope, frameCommands, appTime, InputAction.TogglePause, startHeld);

		bool l3Held = Input.GetKey(KeyCode.JoystickButton8);
		PollButton(scope, frameCommands, appTime, InputAction.LeftStickPress, l3Held);
		PollButton(scope, frameCommands, appTime, InputAction.ToggleGameUI, l3Held);

		// Analog triggers L2 / LT (DeleteRoads = 18 / LowerToolbar = 22) and R2 / RT (RaiseToolbar = 21)
		float leftTrigger = Mathf.Max(ReadAxisSafe("LeftTrigger", "Joy1Axis5"), ReadAxisSafe("L2", "Joy1Axis9"));
		float rightTrigger = Mathf.Max(ReadAxisSafe("RightTrigger", "Joy1Axis10"), ReadAxisSafe("R2", "Joy1Axis8"));
		bool ltHeld = leftTrigger > TriggerThreshold || Input.GetKey(KeyCode.JoystickButton10);
		bool rtHeld = rightTrigger > TriggerThreshold || Input.GetKey(KeyCode.JoystickButton11);

		PollButton(scope, frameCommands, appTime, InputAction.DeleteRoads, ltHeld);
		PollButton(scope, frameCommands, appTime, InputAction.LowerToolbar, ltHeld);
		PollButton(scope, frameCommands, appTime, InputAction.RaiseToolbar, rtHeld);
	}

	private void CheckHotplug(float appTime)
	{
		if (appTime - _lastHotplugCheckTime < HotplugCheckInterval)
		{
			return;
		}
		_lastHotplugCheckTime = appTime;

		string[] names = Input.GetJoystickNames();
		string detected = string.Empty;
		if (names != null)
		{
			for (int i = 0; i < names.Length; i++)
			{
				if (!string.IsNullOrWhiteSpace(names[i]))
				{
					detected = names[i].Trim();
					break;
				}
			}
		}

		bool nowConnected = !string.IsNullOrEmpty(detected);
		if (nowConnected && !_hasConnectedGamepad)
		{
			_hasConnectedGamepad = true;
			_activeGamepadName = detected;
			GamepadConnected?.Invoke(detected);
		}
		else if (!nowConnected && _hasConnectedGamepad)
		{
			_hasConnectedGamepad = false;
			_activeGamepadName = string.Empty;
			_previousButtons.Clear();
			_nextDpadRepeatTime.Clear();
			GamepadDisconnected?.Invoke();
		}
	}

	private void PollAxis(
		IScope scope,
		InputState inputState,
		List<IAppCommand> frameCommands,
		float appTime,
		int actionId,
		float value)
	{
		_previousAxes.TryGetValue(actionId, out float prev);
		if (!Mathf.Approximately(prev, value) || !Mathf.Approximately(inputState.GetAxis(actionId), value))
		{
			_previousAxes[actionId] = value;
			AxisInputEvent evt = AxisInputEvent.CreateAxisEvent(scope, actionId, value, InputEventSource.Generic);
			ProcessInputEventCommand cmd = scope.Get<ProcessInputEventCommand>();
			cmd.Configure(appTime, evt);
			frameCommands.Add(cmd);
		}
	}

	private void PollButton(
		IScope scope,
		List<IAppCommand> frameCommands,
		float appTime,
		int actionId,
		bool isDown)
	{
		_previousButtons.TryGetValue(actionId, out bool wasDown);
		if (isDown && !wasDown)
		{
			_previousButtons[actionId] = true;
			EmitButtonEvent(scope, frameCommands, appTime, actionId, InputEventButtonState.JustDown);
		}
		else if (!isDown && wasDown)
		{
			_previousButtons[actionId] = false;
			EmitButtonEvent(scope, frameCommands, appTime, actionId, InputEventButtonState.JustUp);
		}
	}

	private void PollDpadDirection(
		IScope scope,
		List<IAppCommand> frameCommands,
		float appTime,
		int actionId,
		bool isDown)
	{
		_previousButtons.TryGetValue(actionId, out bool wasDown);
		if (isDown && !wasDown)
		{
			_previousButtons[actionId] = true;
			_nextDpadRepeatTime[actionId] = appTime + DpadRepeatInitialDelay;
			EmitButtonEvent(scope, frameCommands, appTime, actionId, InputEventButtonState.JustDown);
		}
		else if (isDown && wasDown)
		{
			if (_nextDpadRepeatTime.TryGetValue(actionId, out float nextTime) && appTime >= nextTime)
			{
				_nextDpadRepeatTime[actionId] = appTime + DpadRepeatInterval;
				EmitButtonEvent(scope, frameCommands, appTime, actionId, InputEventButtonState.JustDown);
			}
		}
		else if (!isDown && wasDown)
		{
			_previousButtons[actionId] = false;
			_nextDpadRepeatTime.Remove(actionId);
			EmitButtonEvent(scope, frameCommands, appTime, actionId, InputEventButtonState.JustUp);
		}
	}

	private static void EmitButtonEvent(
		IScope scope,
		List<IAppCommand> frameCommands,
		float appTime,
		int actionId,
		InputEventButtonState state)
	{
		InputEvent evt = InputEvent.CreateEvent(scope, actionId, state, InputEventSource.Generic);
		ProcessInputEventCommand cmd = scope.Get<ProcessInputEventCommand>();
		cmd.Configure(appTime, evt);
		frameCommands.Add(cmd);
	}

	private static Vector2 ApplyRadialDeadzone(Vector2 stick)
	{
		float mag = stick.magnitude;
		if (mag <= StickDeadzone || float.IsNaN(mag))
		{
			return Vector2.zero;
		}
		float rescaled = Mathf.Clamp01((mag - StickDeadzone) / (1f - StickDeadzone));
		return (stick / mag) * rescaled;
	}

	private static float ReadAxisSafe(string primaryAxis, string fallbackAxis, bool invertSecondary = false)
	{
		try
		{
			float v = Input.GetAxisRaw(primaryAxis);
			if (Mathf.Abs(v) > 0.001f)
			{
				return v;
			}
		}
		catch (Exception)
		{
		}
		try
		{
			float v2 = Input.GetAxisRaw(fallbackAxis);
			return invertSecondary ? -v2 : v2;
		}
		catch (Exception)
		{
			return 0f;
		}
	}
}
