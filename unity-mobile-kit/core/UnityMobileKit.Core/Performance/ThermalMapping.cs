namespace UnityMobileKit.Performance
{
    /// <summary>Maps the platforms' raw thermal readings onto <see cref="ThermalLevel"/>.</summary>
    public static class ThermalMapping
    {
        /// <summary>
        /// Android <c>PowerManager.getCurrentThermalStatus()</c> (API 29+): NONE 0, LIGHT 1,
        /// MODERATE 2, SEVERE 3, CRITICAL 4, EMERGENCY 5, SHUTDOWN 6. MODERATE already means the
        /// system is throttling, so it counts as serious (Auto drops to 30); SEVERE and above cap
        /// every mode. Unknown negative values count as nominal.
        /// </summary>
        public static ThermalLevel FromAndroidThermalStatus(int status)
        {
            if (status >= 3) return ThermalLevel.Critical;
            if (status == 2) return ThermalLevel.Serious;
            if (status == 1) return ThermalLevel.Fair;
            return ThermalLevel.Nominal;
        }

        /// <summary>iOS <c>ProcessInfo.thermalState</c>: nominal 0, fair 1, serious 2, critical 3.</summary>
        public static ThermalLevel FromIosThermalState(int state)
        {
            if (state >= 3) return ThermalLevel.Critical;
            if (state == 2) return ThermalLevel.Serious;
            if (state == 1) return ThermalLevel.Fair;
            return ThermalLevel.Nominal;
        }
    }
}
