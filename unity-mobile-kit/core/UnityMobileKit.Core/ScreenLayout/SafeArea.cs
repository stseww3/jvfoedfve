using System;
using UnityMobileKit.Geometry;

namespace UnityMobileKit.ScreenLayout
{
    /// <summary>
    /// Keeps UI clear of notches, punch-hole cameras and rounded corners. Feed it the platform's
    /// safe area (Unity's <c>Screen.safeArea</c>) and apply the anchors to a full-screen UI panel.
    /// </summary>
    public static class SafeArea
    {
        /// <summary>
        /// Clips the reported safe area to the screen. Some devices report areas that are empty,
        /// NaN or extend past the screen; anything unusable falls back to the whole screen.
        /// </summary>
        public static RectF Sanitize(RectF safeArea, float screenWidth, float screenHeight)
        {
            ValidateScreen(screenWidth, screenHeight);
            var full = new RectF(0f, 0f, screenWidth, screenHeight);
            if (safeArea.IsEmpty || float.IsNaN(safeArea.X) || float.IsNaN(safeArea.Y)) return full;

            float minX = Math.Max(0f, safeArea.X);
            float minY = Math.Max(0f, safeArea.Y);
            float maxX = Math.Min(screenWidth, safeArea.X + safeArea.Width);
            float maxY = Math.Min(screenHeight, safeArea.Y + safeArea.Height);
            var clipped = RectF.FromMinMax(new Float2(minX, minY), new Float2(maxX, maxY));
            return clipped.IsEmpty ? full : clipped;
        }

        /// <summary>
        /// Normalized anchors (0..1) for a panel that should fill the safe area, matching Unity's
        /// <c>RectTransform.anchorMin</c>/<c>anchorMax</c>. With <paramref name="symmetric"/> the
        /// larger inset is used on both opposite sides, so centered UI stays centered when only one
        /// side has a notch (landscape phones flip the notch side when rotated).
        /// </summary>
        public static void GetAnchors(RectF safeArea, float screenWidth, float screenHeight, bool symmetric,
                                      out Float2 anchorMin, out Float2 anchorMax)
        {
            RectF area = Sanitize(safeArea, screenWidth, screenHeight);
            float left = area.X;
            float bottom = area.Y;
            float right = screenWidth - (area.X + area.Width);
            float top = screenHeight - (area.Y + area.Height);

            if (symmetric)
            {
                left = right = Math.Max(left, right);
                bottom = top = Math.Max(bottom, top);
                // A symmetric inset can exceed half the screen only with absurd input; keep a valid panel.
                left = right = Math.Min(left, screenWidth * 0.49f);
                bottom = top = Math.Min(bottom, screenHeight * 0.49f);
            }

            anchorMin = new Float2(left / screenWidth, bottom / screenHeight);
            anchorMax = new Float2(1f - right / screenWidth, 1f - top / screenHeight);
        }

        private static void ValidateScreen(float width, float height)
        {
            if (!(width > 0f) || !(height > 0f) || float.IsInfinity(width) || float.IsInfinity(height))
            {
                throw new ArgumentOutOfRangeException(nameof(width), "Screen size must be positive.");
            }
        }
    }
}
