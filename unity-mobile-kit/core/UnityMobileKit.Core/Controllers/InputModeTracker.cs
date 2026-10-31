using System;
using UnityMobileKit.Geometry;

namespace UnityMobileKit.Controllers
{
    public enum InputMode
    {
        Touch,
        Gamepad,
    }

    /// <summary>
    /// Tracks whether the player is currently using touch or a controller (to show or hide the
    /// virtual cursor and button prompts) and asks the game to pause when the controller in use
    /// disconnects, so a dead battery mid-game doesn't leave the player stuck.
    /// </summary>
    public sealed class InputModeTracker
    {
        public InputMode Mode { get; private set; } = InputMode.Touch;

        public bool GamepadConnected { get; private set; }

        public event Action<InputMode> ModeChanged;

        /// <summary>Raised when the controller disconnects while it was the active input.</summary>
        public event Action PauseRequested;

        public void NotifyTouch() => SetMode(InputMode.Touch);

        /// <summary>
        /// Call every frame with deadzone-filtered input. Switches to <see cref="InputMode.Gamepad"/>
        /// only on deliberate input (a button, a stick past its deadzone, a pulled trigger), so a
        /// controller that is merely connected doesn't hide the touch UI.
        /// </summary>
        public void NotifyGamepad(GamepadState filtered)
        {
            bool active = filtered.Buttons != GamepadButtons.None
                || filtered.LeftStick != Float2.Zero
                || filtered.RightStick != Float2.Zero
                || filtered.LeftTrigger > 0f
                || filtered.RightTrigger > 0f;
            if (!active) return;

            GamepadConnected = true;
            SetMode(InputMode.Gamepad);
        }

        public void SetGamepadConnected(bool connected)
        {
            if (connected == GamepadConnected) return;
            GamepadConnected = connected;
            if (!connected && Mode == InputMode.Gamepad)
            {
                SetMode(InputMode.Touch);
                PauseRequested?.Invoke();
            }
        }

        private void SetMode(InputMode mode)
        {
            if (Mode == mode) return;
            Mode = mode;
            ModeChanged?.Invoke(mode);
        }
    }
}
