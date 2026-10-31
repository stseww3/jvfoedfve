// NOT RUNTIME-TESTED. Written for Unity 2021.3 LTS or newer but never run in Unity or on a device.
// It is only compile-checked against hand-written stand-ins for the UnityEngine API
// (tests/UnityApiStubs). The thermal mapping it uses (core/Performance) is unit-tested with dotnet.

using UnityEngine;
using UnityMobileKit.Performance;

namespace UnityMobileKit.Runtime
{
    /// <summary>
    /// Reads battery level, external power, battery saver and heat. Battery comes from Unity on every
    /// platform. Battery saver (Android 5+) and thermal status (Android 10+) are read from Android's
    /// PowerManager; other platforms report them as off and nominal.
    /// </summary>
    public static class DeviceConditionsReader
    {
#if UNITY_ANDROID && !UNITY_EDITOR
        private static int s_sdkInt = -1;
        private static bool s_warned;
#endif

        /// <summary>Calls into Java on Android, so poll it every few seconds rather than every frame.</summary>
        public static DeviceConditions Read()
        {
            BatteryStatus status = SystemInfo.batteryStatus;
            bool externalPower = status == BatteryStatus.Charging || status == BatteryStatus.Full || status == BatteryStatus.NotCharging;
            bool lowPowerMode = false;
            ThermalLevel thermal = ThermalLevel.Nominal;
#if UNITY_ANDROID && !UNITY_EDITOR
            ReadAndroidPowerState(ref lowPowerMode, ref thermal);
#endif
            return new DeviceConditions(SystemInfo.batteryLevel, externalPower, lowPowerMode, thermal);
        }

#if UNITY_ANDROID && !UNITY_EDITOR
        private static void ReadAndroidPowerState(ref bool lowPowerMode, ref ThermalLevel thermal)
        {
            try
            {
                if (s_sdkInt < 0)
                {
                    using (var version = new AndroidJavaClass("android.os.Build$VERSION"))
                    {
                        s_sdkInt = version.GetStatic<int>("SDK_INT");
                    }
                }
                using (var player = new AndroidJavaClass("com.unity3d.player.UnityPlayer"))
                using (var activity = player.GetStatic<AndroidJavaObject>("currentActivity"))
                using (var power = activity?.Call<AndroidJavaObject>("getSystemService", "power"))
                {
                    if (power == null) return;
                    lowPowerMode = power.Call<bool>("isPowerSaveMode");
                    if (s_sdkInt >= 29) thermal = ThermalMapping.FromAndroidThermalStatus(power.Call<int>("getCurrentThermalStatus"));
                }
            }
            catch (AndroidJavaException e)
            {
                if (s_warned) return;
                s_warned = true;
                Debug.LogWarning($"[UnityMobileKit] Could not read battery saver or thermal status: {e.Message}");
            }
        }
#endif
    }
}
