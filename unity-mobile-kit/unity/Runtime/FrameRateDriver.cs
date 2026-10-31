// NOT RUNTIME-TESTED. Written for Unity 2021.3 LTS or newer but never run in Unity or on a device.
// It is only compile-checked against hand-written stand-ins for the UnityEngine API
// (tests/UnityApiStubs). The policy it calls into (core/Performance) is unit-tested with dotnet.

using UnityEngine;
using UnityMobileKit.Performance;
using UnityMobileKit.Settings;

namespace UnityMobileKit.Runtime
{
    /// <summary>
    /// Sets <c>Application.targetFrameRate</c> each frame from the player's 30 / 60 / Auto setting,
    /// battery, battery saver, device heat and measured frame times (see <see cref="FrameRatePolicy"/>).
    /// On Android and iOS Unity ignores <c>QualitySettings.vSyncCount</c> and paces to this target.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class FrameRateDriver : MonoBehaviour
    {
        [Tooltip("Used when there is no MobileKitServices. With it, the player's frame-rate setting decides.")]
        [SerializeField] private FrameRateMode modeWithoutServices = FrameRateMode.Auto;

        [Tooltip("Seconds between reads of battery, battery saver and heat. Each read calls into Java on Android.")]
        [SerializeField, Min(0.5f)] private float conditionsPollSeconds = 5f;

        private double _nextPoll = double.NegativeInfinity;
        private int _displayHz;

        public FrameRatePolicy Policy { get; } = new FrameRatePolicy();

        public DeviceConditions Conditions { get; private set; } = DeviceConditions.Unknown;

        private void OnEnable()
        {
            _displayHz = DisplayRefresh.HighestRate();
            _nextPoll = double.NegativeInfinity;
        }

        private void OnApplicationPause(bool paused)
        {
            if (paused) return;
            // Frame times from before the pause say nothing about now, and the display mode, battery
            // or heat may have changed in the background.
            Policy.ResetMeasurements();
            _displayHz = DisplayRefresh.HighestRate();
            _nextPoll = double.NegativeInfinity;
        }

        private void Update()
        {
            double now = Time.realtimeSinceStartupAsDouble;
            if (now >= _nextPoll)
            {
                Conditions = DeviceConditionsReader.Read();
                _nextPoll = now + conditionsPollSeconds;
            }

            MobileKitServices services = MobileKitServices.Instance;
            FrameRateMode mode = services != null && services.Settings != null ? services.Settings.FrameRate : modeWithoutServices;
            int target = Policy.Update(mode, _displayHz, Conditions, Time.unscaledDeltaTime, now);
            if (Application.targetFrameRate != target) Application.targetFrameRate = target;
        }
    }
}
