namespace UnityMobileKit.Geometry
{
    /// <summary>Density-independent pixel (dp) conversions; 1 dp is 1/160 inch, as on Android.</summary>
    public static class ScreenDensity
    {
        /// <summary>Used when the platform reports an unknown density (Unity's <c>Screen.dpi</c> can be 0).</summary>
        public const float FallbackDpi = 320f;

        public static float UsableDpi(float dpi) => dpi > 0f && !float.IsInfinity(dpi) ? dpi : FallbackDpi;

        public static float PixelsPerDp(float dpi) => UsableDpi(dpi) / 160f;

        public static float DpToPixels(float dp, float dpi) => dp * PixelsPerDp(dpi);
    }
}
