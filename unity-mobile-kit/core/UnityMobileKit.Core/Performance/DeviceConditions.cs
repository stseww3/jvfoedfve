namespace UnityMobileKit.Performance
{
    /// <summary>
    /// Device heat, coarsened to four levels that both Android (PowerManager thermal status) and
    /// iOS (ProcessInfo.thermalState) can be mapped onto.
    /// </summary>
    public enum ThermalLevel
    {
        Nominal,
        Fair,
        Serious,
        Critical,
    }

    /// <summary>A snapshot of power and heat, filled in by the platform layer.</summary>
    public readonly struct DeviceConditions
    {
        public DeviceConditions(float batteryLevel, bool isCharging, bool isLowPowerMode, ThermalLevel thermal)
        {
            BatteryLevel = batteryLevel;
            IsCharging = isCharging;
            IsLowPowerMode = isLowPowerMode;
            Thermal = thermal;
        }

        public static DeviceConditions Unknown => new DeviceConditions(-1f, false, false, ThermalLevel.Nominal);

        /// <summary>0..1, or negative when unknown (Unity's <c>SystemInfo.batteryLevel</c> returns -1 then).</summary>
        public float BatteryLevel { get; }

        public bool IsCharging { get; }

        /// <summary>The OS battery saver is on.</summary>
        public bool IsLowPowerMode { get; }

        public ThermalLevel Thermal { get; }
    }
}
