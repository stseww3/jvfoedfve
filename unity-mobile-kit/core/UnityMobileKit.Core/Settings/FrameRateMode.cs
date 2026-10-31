using System;

namespace UnityMobileKit.Settings
{
    /// <summary>
    /// How the game should cap its frame rate. <see cref="Auto"/> follows the display's refresh
    /// rate; the fixed modes trade smoothness for battery life on mobile.
    /// </summary>
    public enum FrameRateMode
    {
        Auto = 0,
        Fps30 = 1,
        Fps60 = 2,
    }

    public static class FrameRate
    {
        /// <summary>
        /// Turns a mode into the integer target a renderer can apply (e.g. Unity's
        /// <c>Application.targetFrameRate</c>). <paramref name="displayRefreshHz"/> is only used for
        /// <see cref="FrameRateMode.Auto"/>; when it is unknown (0 or less) Auto falls back to 60.
        /// </summary>
        public static int Resolve(FrameRateMode mode, int displayRefreshHz)
        {
            switch (mode)
            {
                case FrameRateMode.Fps30: return 30;
                case FrameRateMode.Fps60: return 60;
                case FrameRateMode.Auto: return displayRefreshHz > 0 ? displayRefreshHz : 60;
                default: throw new ArgumentOutOfRangeException(nameof(mode));
            }
        }
    }
}
