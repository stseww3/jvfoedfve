using System;

namespace UnityMobileKit.Controllers
{
    /// <summary>
    /// Per-frame press/release edges for gamepad buttons, plus held-button auto-repeat for menu
    /// navigation (hold the D-pad and the selection keeps moving). Call <see cref="Update"/> once
    /// per frame. Not thread-safe.
    /// </summary>
    public sealed class ButtonTracker
    {
        private const int ButtonCount = 14;

        private readonly double[] _nextRepeat = new double[ButtonCount];
        private GamepadButtons _held;
        private GamepadButtons _pressed;
        private GamepadButtons _released;
        private GamepadButtons _repeated;

        /// <summary>How long a button must be held before it starts repeating.</summary>
        public double RepeatDelaySeconds { get; set; } = 0.4;

        public double RepeatIntervalSeconds { get; set; } = 0.1;

        public GamepadButtons Held => _held;

        public void Update(GamepadButtons buttons, double time)
        {
            _pressed = buttons & ~_held;
            _released = _held & ~buttons;
            _held = buttons;
            _repeated = GamepadButtons.None;

            for (int i = 0; i < ButtonCount; i++)
            {
                var bit = (GamepadButtons)(1 << i);
                if ((_pressed & bit) != 0)
                {
                    _nextRepeat[i] = time + RepeatDelaySeconds;
                }
                else if ((_held & bit) != 0 && time >= _nextRepeat[i])
                {
                    _repeated |= bit;
                    // After a frame hitch, resume the normal cadence instead of firing a burst.
                    double next = _nextRepeat[i] + RepeatIntervalSeconds;
                    _nextRepeat[i] = next > time ? next : time + RepeatIntervalSeconds;
                }
            }
        }

        /// <summary>Forgets all state, e.g. when the controller disconnects. Buttons still held afterwards count as new presses.</summary>
        public void Reset()
        {
            _held = _pressed = _released = _repeated = GamepadButtons.None;
            Array.Clear(_nextRepeat, 0, _nextRepeat.Length);
        }

        /// <summary>True if every button in <paramref name="buttons"/> is down.</summary>
        public bool IsHeld(GamepadButtons buttons) => buttons != GamepadButtons.None && (_held & buttons) == buttons;

        /// <summary>True if any button in <paramref name="buttons"/> went down this frame.</summary>
        public bool WasPressed(GamepadButtons buttons) => (_pressed & buttons) != 0;

        public bool WasReleased(GamepadButtons buttons) => (_released & buttons) != 0;

        /// <summary>Press edges plus auto-repeat ticks: use for moving a menu selection.</summary>
        public bool WasPressedOrRepeated(GamepadButtons buttons) => ((_pressed | _repeated) & buttons) != 0;
    }
}
