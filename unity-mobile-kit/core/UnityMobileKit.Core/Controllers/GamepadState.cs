using System;
using UnityMobileKit.Geometry;

namespace UnityMobileKit.Controllers
{
    /// <summary>
    /// Buttons of a standard (Xbox-style) gamepad, named by position so they mean the same thing on
    /// every brand: South is A on Xbox-style pads and Cross on PlayStation pads. Phone controllers
    /// such as clip-on handhelds report this layout through the platform's standard gamepad mapping.
    /// </summary>
    [Flags]
    public enum GamepadButtons
    {
        None = 0,
        South = 1 << 0,
        East = 1 << 1,
        West = 1 << 2,
        North = 1 << 3,
        LeftShoulder = 1 << 4,
        RightShoulder = 1 << 5,
        Start = 1 << 6,
        Select = 1 << 7,
        DpadUp = 1 << 8,
        DpadDown = 1 << 9,
        DpadLeft = 1 << 10,
        DpadRight = 1 << 11,
        LeftStick = 1 << 12,
        RightStick = 1 << 13,
    }

    /// <summary>One frame of gamepad input, filled in by the platform layer.</summary>
    public readonly struct GamepadState
    {
        public GamepadState(Float2 leftStick, Float2 rightStick, float leftTrigger, float rightTrigger, GamepadButtons buttons)
        {
            LeftStick = leftStick;
            RightStick = rightStick;
            LeftTrigger = leftTrigger;
            RightTrigger = rightTrigger;
            Buttons = buttons;
        }

        /// <summary>-1..1 per axis, +Y up.</summary>
        public Float2 LeftStick { get; }

        public Float2 RightStick { get; }

        /// <summary>0..1.</summary>
        public float LeftTrigger { get; }

        public float RightTrigger { get; }

        public GamepadButtons Buttons { get; }
    }
}
