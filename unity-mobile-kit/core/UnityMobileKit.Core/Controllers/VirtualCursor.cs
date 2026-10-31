using System;
using UnityMobileKit.Geometry;

namespace UnityMobileKit.Controllers
{
    /// <summary>
    /// A screen-space pointer driven by a stick, for picking things with a controller. Speeds are in
    /// screen heights per second so the feel is the same at any resolution. Holding the stick fully
    /// over gradually boosts the speed for crossing the screen; partial deflection stays precise.
    /// </summary>
    public sealed class VirtualCursor
    {
        private const float FullDeflection = 0.9f;

        private Float2 _areaMin;
        private Float2 _areaMax;
        private float _screenHeight;
        private float _fullDeflectionSeconds;

        public VirtualCursor(float screenWidth, float screenHeight)
        {
            SetScreen(screenWidth, screenHeight);
            Position = Float2.Midpoint(_areaMin, _areaMax);
        }

        /// <summary>Screen pixels, origin bottom-left.</summary>
        public Float2 Position { get; private set; }

        /// <summary>Speed at full deflection before boost, in screen heights per second.</summary>
        public float Speed { get; set; } = 0.9f;

        /// <summary>Speed multiplier reached after holding full deflection for <see cref="BoostRampSeconds"/>. 1 disables boost.</summary>
        public float MaxBoost { get; set; } = 2f;

        public float BoostRampSeconds { get; set; } = 0.6f;

        /// <summary>Resets the movement area to the whole screen; call on resolution or orientation change.</summary>
        public void SetScreen(float width, float height)
        {
            if (!(width > 0f) || !(height > 0f) || float.IsInfinity(width) || float.IsInfinity(height))
            {
                throw new ArgumentOutOfRangeException(nameof(width), "Screen size must be positive.");
            }
            _screenHeight = height;
            SetArea(Float2.Zero, new Float2(width, height));
        }

        /// <summary>Restricts the cursor to a rectangle, typically the safe area (away from notches and rounded corners).</summary>
        public void SetArea(Float2 min, Float2 max)
        {
            if (!(max.X >= min.X) || !(max.Y >= min.Y)) throw new ArgumentException("Area max must not be below min.");
            _areaMin = min;
            _areaMax = max;
            Position = Float2.Clamp(Position, _areaMin, _areaMax);
        }

        /// <summary>Jumps to a position, e.g. where the player last touched when switching to the controller.</summary>
        public void Warp(Float2 position)
        {
            Position = Float2.Clamp(position, _areaMin, _areaMax);
        }

        /// <param name="stick">Deadzone-filtered stick value.</param>
        /// <returns>True if the cursor moved.</returns>
        public bool Update(Float2 stick, float deltaTime)
        {
            float magnitude = stick.Length;
            if (!(deltaTime > 0f) || !(magnitude > 0f) || float.IsInfinity(magnitude))
            {
                _fullDeflectionSeconds = 0f;
                return false;
            }

            float boost = 1f;
            if (magnitude >= FullDeflection)
            {
                _fullDeflectionSeconds += deltaTime;
                float ramp = BoostRampSeconds > 0f ? Math.Min(1f, _fullDeflectionSeconds / BoostRampSeconds) : 1f;
                boost = 1f + (MaxBoost - 1f) * ramp;
            }
            else
            {
                _fullDeflectionSeconds = 0f;
            }

            Float2 before = Position;
            Position = Float2.Clamp(Position + stick * (Speed * _screenHeight * boost * deltaTime), _areaMin, _areaMax);
            return Position != before;
        }
    }
}
