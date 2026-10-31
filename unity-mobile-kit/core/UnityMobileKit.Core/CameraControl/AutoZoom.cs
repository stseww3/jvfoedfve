using System;
using System.Collections.Generic;
using UnityMobileKit.Geometry;
using UnityMobileKit.Gestures;

namespace UnityMobileKit.CameraControl
{
    /// <summary>
    /// Smoothly frames a set of world points of interest (units, buildings, whatever matters) on a
    /// <see cref="ZoomPanCamera"/>. It steps aside while the player is panning or pinching and
    /// resumes after <see cref="ResumeDelaySeconds"/> without input. Bind <see cref="Enabled"/> to
    /// the player's auto-zoom setting.
    /// </summary>
    public sealed class AutoZoom
    {
        private readonly ZoomPanCamera _camera;
        private double _suspendedUntil = double.NegativeInfinity;
        private float _screenMargin = 0.1f;

        public AutoZoom(ZoomPanCamera camera)
        {
            _camera = camera ?? throw new ArgumentNullException(nameof(camera));
        }

        public bool Enabled { get; set; } = true;

        /// <summary>Fraction of the screen kept free on every side of the framed points (0 to 0.45).</summary>
        public float ScreenMargin
        {
            get => _screenMargin;
            set
            {
                if (!(value >= 0f && value <= 0.45f)) throw new ArgumentOutOfRangeException(nameof(value), "Must be between 0 and 0.45.");
                _screenMargin = value;
            }
        }

        /// <summary>How quickly the camera converges, per second. Roughly 95% of the way after 3 / Sharpness seconds.</summary>
        public float Sharpness { get; set; } = 2.5f;

        public double ResumeDelaySeconds { get; set; } = 3.0;

        /// <summary>Call whenever the player moves the camera by hand.</summary>
        public void NotifyUserInput(double time)
        {
            _suspendedUntil = Math.Max(_suspendedUntil, time + ResumeDelaySeconds);
        }

        /// <summary>Convenience: suspends auto-zoom whenever this frame's gestures moved the camera.</summary>
        public void Observe(GestureFrame frame, double time)
        {
            if (frame.IsDragging || frame.IsPinching || frame.Pan != Float2.Zero) NotifyUserInput(time);
        }

        public bool IsSuspended(double time) => time < _suspendedUntil;

        /// <summary>
        /// The camera center and size that fit <paramref name="points"/> with the screen margin,
        /// clamped to the camera's zoom limits. False when there are no points.
        /// </summary>
        public bool TryGetTarget(IReadOnlyList<Float2> points, out Float2 center, out float size)
        {
            center = Float2.Zero;
            size = 0f;
            if (points == null || points.Count == 0) return false;

            Float2 min = points[0];
            Float2 max = points[0];
            for (int i = 1; i < points.Count; i++)
            {
                Float2 p = points[i];
                min = new Float2(Math.Min(min.X, p.X), Math.Min(min.Y, p.Y));
                max = new Float2(Math.Max(max.X, p.X), Math.Max(max.Y, p.Y));
            }

            center = Float2.Midpoint(min, max);
            float neededHalfHeight = Math.Max((max.Y - min.Y) * 0.5f, (max.X - min.X) * 0.5f / _camera.Aspect);
            float usable = 1f - 2f * _screenMargin;
            size = Math.Min(Math.Max(neededHalfHeight / usable, _camera.MinSize), _camera.MaxSize);
            return true;
        }

        /// <summary>
        /// Moves the camera part of the way toward framing <paramref name="points"/> using exponential
        /// smoothing, so the motion does not depend on frame rate (away from bounds, one 1/30 s step
        /// lands where two 1/60 s steps would). Returns false when auto-zoom is off, suspended, or
        /// has nothing to frame.
        /// </summary>
        public bool Update(IReadOnlyList<Float2> points, double time, float deltaTime)
        {
            if (!Enabled || IsSuspended(time) || !(deltaTime > 0f)) return false;
            if (!TryGetTarget(points, out Float2 targetCenter, out float targetSize)) return false;

            float t = 1f - (float)Math.Exp(-Sharpness * deltaTime);
            _camera.SetSize(_camera.Size + (targetSize - _camera.Size) * t);
            _camera.SetCenter(_camera.Center + (targetCenter - _camera.Center) * t);
            return true;
        }
    }
}
