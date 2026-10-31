using System;
using UnityMobileKit.Geometry;

namespace UnityMobileKit.ScreenLayout
{
    /// <summary>Resolution-independent UI sizing helpers.</summary>
    public static class UiScale
    {
        /// <summary>Android's minimum recommended touch target.</summary>
        public const float MinTouchTargetDp = 48f;

        /// <summary>
        /// The scale factor of Unity's CanvasScaler in "Scale With Screen Size" / "Match Width Or
        /// Height" mode: width and height ratios blended in log space, so a screen twice as wide and
        /// half as tall with match 0.5 gives 1. <paramref name="match"/> 0 follows width, 1 height.
        /// </summary>
        public static float ScaleWithScreenSize(float screenWidth, float screenHeight, float referenceWidth, float referenceHeight, float match)
        {
            if (!(screenWidth > 0f) || !(screenHeight > 0f) || !(referenceWidth > 0f) || !(referenceHeight > 0f))
            {
                throw new ArgumentOutOfRangeException(nameof(screenWidth), "Sizes must be positive.");
            }
            if (!(match >= 0f && match <= 1f)) throw new ArgumentOutOfRangeException(nameof(match), "Must be between 0 and 1.");

            double logWidth = Math.Log(screenWidth / referenceWidth, 2.0);
            double logHeight = Math.Log(screenHeight / referenceHeight, 2.0);
            return (float)Math.Pow(2.0, logWidth + (logHeight - logWidth) * match);
        }

        /// <summary>
        /// Size in canvas reference units that comes out as <paramref name="dp"/> physical size on this
        /// screen. Design buttons at least this large to keep them comfortably tappable.
        /// </summary>
        public static float TouchTargetInReferenceUnits(float dpi, float uiScale, float dp = MinTouchTargetDp)
        {
            if (!(uiScale > 0f) || float.IsInfinity(uiScale)) throw new ArgumentOutOfRangeException(nameof(uiScale), "Must be a positive number.");
            return ScreenDensity.DpToPixels(dp, dpi) / uiScale;
        }
    }
}
