// NOT RUNTIME-TESTED. Written for Unity 2021.3 LTS or newer but never run in Unity or on a device.
// It is only compile-checked against hand-written stand-ins for the UnityEngine API
// (tests/UnityApiStubs).

using System;
using UnityEngine;

namespace UnityMobileKit.Runtime
{
    internal static class DisplayRefresh
    {
        /// <summary>
        /// The highest refresh rate among the display modes Unity reports, so Auto can use a 90 or
        /// 120 Hz panel; the current mode's rate if none are reported; 0 if unknown (Auto then uses 60).
        /// </summary>
        public static int HighestRate()
        {
            int highest = 0;
            Resolution[] modes = Screen.resolutions;
            if (modes != null)
            {
                for (int i = 0; i < modes.Length; i++) highest = Math.Max(highest, RateOf(modes[i]));
            }
            return highest > 0 ? highest : RateOf(Screen.currentResolution);
        }

        private static int RateOf(Resolution mode)
        {
#if UNITY_2022_2_OR_NEWER
            double hz = mode.refreshRateRatio.value;
            return hz > 0.0 && hz < 1000.0 ? (int)Math.Round(hz) : 0;
#else
            return mode.refreshRate;
#endif
        }
    }
}
