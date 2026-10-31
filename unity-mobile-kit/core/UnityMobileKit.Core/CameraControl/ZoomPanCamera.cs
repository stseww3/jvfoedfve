using System;
using UnityMobileKit.Geometry;
using UnityMobileKit.Gestures;

namespace UnityMobileKit.CameraControl
{
    /// <summary>
    /// State and math for a top-down orthographic camera driven by touch: the content follows the
    /// finger when panning, and pinching zooms around the point between the fingers. Pure math;
    /// the Unity layer copies <see cref="Center"/> and <see cref="Size"/> onto a real camera.
    /// <para>
    /// Screen coordinates are pixels with the origin at the bottom-left (Unity's convention).
    /// <see cref="Size"/> is the half-height of the view in world units, like Unity's
    /// <c>Camera.orthographicSize</c>, so a smaller size means zoomed in.
    /// </para>
    /// </summary>
    public sealed class ZoomPanCamera
    {
        private Float2 _boundsMin;
        private Float2 _boundsMax;

        public ZoomPanCamera(float minSize, float maxSize, float viewportWidth, float viewportHeight)
        {
            if (!(minSize > 0f) || float.IsInfinity(minSize)) throw new ArgumentOutOfRangeException(nameof(minSize), "Must be a positive number.");
            if (!(maxSize >= minSize) || float.IsInfinity(maxSize)) throw new ArgumentOutOfRangeException(nameof(maxSize), "Must be at least minSize.");
            MinSize = minSize;
            MaxSize = maxSize;
            Size = maxSize;
            SetViewport(viewportWidth, viewportHeight);
        }

        public Float2 Center { get; private set; }

        public float Size { get; private set; }

        public float MinSize { get; }

        public float MaxSize { get; }

        public float ViewportWidth { get; private set; }

        public float ViewportHeight { get; private set; }

        public bool HasBounds { get; private set; }

        public float Aspect => ViewportWidth / ViewportHeight;

        public float WorldUnitsPerPixel => 2f * Size / ViewportHeight;

        /// <summary>Half the visible width and height in world units.</summary>
        public Float2 HalfExtents => new Float2(Size * Aspect, Size);

        /// <summary>Call when the screen size or orientation changes.</summary>
        public void SetViewport(float width, float height)
        {
            if (!(width > 0f) || float.IsInfinity(width)) throw new ArgumentOutOfRangeException(nameof(width), "Must be a positive number.");
            if (!(height > 0f) || float.IsInfinity(height)) throw new ArgumentOutOfRangeException(nameof(height), "Must be a positive number.");
            ViewportWidth = width;
            ViewportHeight = height;
            ClampCenter();
        }

        /// <summary>
        /// Keeps the view inside a world rectangle. When the view is larger than the rectangle on an
        /// axis, the camera centers on the rectangle on that axis instead.
        /// </summary>
        public void SetBounds(Float2 min, Float2 max)
        {
            if (!(max.X >= min.X) || !(max.Y >= min.Y)) throw new ArgumentException("Bounds max must not be below min.");
            _boundsMin = min;
            _boundsMax = max;
            HasBounds = true;
            ClampCenter();
        }

        public void ClearBounds() => HasBounds = false;

        public void SetCenter(Float2 center)
        {
            Center = center;
            ClampCenter();
        }

        public void SetSize(float size)
        {
            if (float.IsNaN(size)) throw new ArgumentOutOfRangeException(nameof(size));
            Size = Math.Min(Math.Max(size, MinSize), MaxSize);
            ClampCenter();
        }

        public Float2 ScreenToWorld(Float2 screen)
        {
            var fromMiddle = new Float2(screen.X - ViewportWidth * 0.5f, screen.Y - ViewportHeight * 0.5f);
            return Center + fromMiddle * WorldUnitsPerPixel;
        }

        public Float2 WorldToScreen(Float2 world)
        {
            Float2 fromCenter = (world - Center) / WorldUnitsPerPixel;
            return new Float2(fromCenter.X + ViewportWidth * 0.5f, fromCenter.Y + ViewportHeight * 0.5f);
        }

        /// <summary>Moves the view so the content travels <paramref name="screenDelta"/> pixels with the finger.</summary>
        public void Pan(Float2 screenDelta)
        {
            Center -= screenDelta * WorldUnitsPerPixel;
            ClampCenter();
        }

        /// <summary>
        /// Zooms by <paramref name="factor"/> (above 1 zooms in) while keeping the world point under
        /// <paramref name="screenFocus"/> fixed on screen, unless a size limit or bound intervenes.
        /// </summary>
        public void ZoomAt(Float2 screenFocus, float factor)
        {
            if (!(factor > 0f) || float.IsInfinity(factor)) throw new ArgumentOutOfRangeException(nameof(factor), "Must be a positive number.");
            Float2 before = ScreenToWorld(screenFocus);
            Size = Math.Min(Math.Max(Size / factor, MinSize), MaxSize);
            Float2 after = ScreenToWorld(screenFocus);
            Center += before - after;
            ClampCenter();
        }

        /// <summary>
        /// Applies one frame of gestures. Panning first and then zooming at the new midpoint keeps the
        /// world point that was between the fingers between the fingers.
        /// </summary>
        public void Apply(GestureFrame frame)
        {
            if (frame.Pan != Float2.Zero) Pan(frame.Pan);
            if (frame.IsPinching && frame.Zoom != 1f) ZoomAt(frame.Focus, frame.Zoom);
        }

        private void ClampCenter()
        {
            if (!HasBounds) return;
            Float2 half = HalfExtents;
            Center = new Float2(
                ClampAxis(Center.X, _boundsMin.X, _boundsMax.X, half.X),
                ClampAxis(Center.Y, _boundsMin.Y, _boundsMax.Y, half.Y));
        }

        private static float ClampAxis(float value, float min, float max, float half)
        {
            if (max - min <= 2f * half) return (min + max) * 0.5f;
            return Math.Min(Math.Max(value, min + half), max - half);
        }
    }
}
