using System;
using UnityMobileKit.Settings;

namespace UnityMobileKit.Performance
{
    public enum FrameRateReason
    {
        /// <summary>The player's setting (or the display rate for Auto) applies unchanged.</summary>
        Preferred,
        Thermal,
        LowPowerMode,
        LowBattery,
        /// <summary>The device could not sustain the higher rate.</summary>
        Performance,
    }

    /// <summary>
    /// Chooses the frame-rate cap each frame from the player's <see cref="FrameRateMode"/>, power,
    /// heat and measured frame times.
    /// <list type="bullet">
    /// <item>Fixed 30/60 is respected, except that critical heat caps every mode at 30.</item>
    /// <item>Auto also drops to 30 for serious heat, battery saver, or low battery while unplugged.</item>
    /// <item>Auto steps down (above 60 to 60, otherwise to 30) when frames keep missing the target,
    /// then retries the higher rate later, waiting twice as long after each failed retry.</item>
    /// </list>
    /// Not thread-safe.
    /// </summary>
    public sealed class FrameRatePolicy
    {
        public const int MinimumRate = 30;

        // Long hitches (loading, returning from background) would otherwise dominate the average.
        private const float MaxCountedInterval = 0.25f;
        private const float AverageTimeConstant = 0.5f;
        private const float MissFactor = 1.2f;

        private int _performanceCap;
        private int _measuredTarget;
        private float _averageInterval;
        private double _missingSince = double.NaN;
        private double _retryAt;
        private double _retryDelay;
        private double _lastRetry = double.NegativeInfinity;

        public FrameRatePolicy()
        {
            _retryDelay = RetryAfterSeconds;
        }

        /// <summary>Battery fraction at or below which Auto saves power when unplugged.</summary>
        public float LowBatteryLevel { get; set; } = 0.15f;

        /// <summary>How long frames must keep missing the target before stepping down.</summary>
        public double DowngradeAfterSeconds { get; set; } = 3.0;

        /// <summary>First wait before retrying a higher rate after a performance step-down.</summary>
        public double RetryAfterSeconds { get; set; } = 30.0;

        public double MaxRetryAfterSeconds { get; set; } = 300.0;

        /// <summary>A retry that survives this long counts as a success and resets the wait.</summary>
        public double StableAfterSeconds { get; set; } = 60.0;

        public int Target { get; private set; } = 60;

        public FrameRateReason Reason { get; private set; }

        /// <param name="frameInterval">Unscaled seconds since the previous frame.</param>
        /// <param name="time">Monotonic time in seconds.</param>
        /// <returns>The frame-rate cap to apply (e.g. to <c>Application.targetFrameRate</c>).</returns>
        public int Update(FrameRateMode mode, int displayRefreshHz, DeviceConditions conditions, float frameInterval, double time)
        {
            int target = FrameRate.Resolve(mode, displayRefreshHz);
            FrameRateReason reason = FrameRateReason.Preferred;

            if (conditions.Thermal == ThermalLevel.Critical)
            {
                Cap(ref target, ref reason, FrameRateReason.Thermal);
            }

            if (mode != FrameRateMode.Auto)
            {
                ResetPerformance();
                return Publish(target, reason);
            }

            if (conditions.Thermal == ThermalLevel.Serious) Cap(ref target, ref reason, FrameRateReason.Thermal);
            if (conditions.IsLowPowerMode) Cap(ref target, ref reason, FrameRateReason.LowPowerMode);
            if (conditions.BatteryLevel >= 0f && conditions.BatteryLevel <= LowBatteryLevel && !conditions.IsCharging)
            {
                Cap(ref target, ref reason, FrameRateReason.LowBattery);
            }

            if (_performanceCap > 0 && time >= _retryAt)
            {
                _performanceCap = 0;
                _lastRetry = time;
            }
            if (_performanceCap == 0 && time - _lastRetry >= StableAfterSeconds)
            {
                _retryDelay = RetryAfterSeconds;
            }
            if (_performanceCap > 0 && _performanceCap < target)
            {
                target = _performanceCap;
                reason = FrameRateReason.Performance;
            }

            TrackPerformance(target, frameInterval, time);
            if (_performanceCap > 0 && _performanceCap < target)
            {
                target = _performanceCap;
                reason = FrameRateReason.Performance;
            }
            return Publish(target, reason);
        }

        /// <summary>Forget frame-time history, e.g. after returning from the background.</summary>
        public void ResetMeasurements()
        {
            _measuredTarget = 0;
            _missingSince = double.NaN;
        }

        private void TrackPerformance(int target, float frameInterval, double time)
        {
            if (target <= MinimumRate)
            {
                _measuredTarget = 0;
                _missingSince = double.NaN;
                return;
            }
            if (target != _measuredTarget)
            {
                _measuredTarget = target;
                _averageInterval = 1f / target;
                _missingSince = double.NaN;
            }
            if (!(frameInterval > 0f)) return;

            float interval = Math.Min(frameInterval, MaxCountedInterval);
            float blend = 1f - (float)Math.Exp(-interval / AverageTimeConstant);
            _averageInterval += (interval - _averageInterval) * blend;

            if (_averageInterval <= MissFactor / target)
            {
                _missingSince = double.NaN;
                return;
            }
            if (double.IsNaN(_missingSince))
            {
                _missingSince = time;
                return;
            }
            if (time - _missingSince < DowngradeAfterSeconds) return;

            bool failedRetry = time - _lastRetry < StableAfterSeconds;
            if (failedRetry) _retryDelay = Math.Min(_retryDelay * 2.0, MaxRetryAfterSeconds);
            _performanceCap = target > 60 ? 60 : MinimumRate;
            _retryAt = time + _retryDelay;
            _missingSince = double.NaN;
        }

        private void ResetPerformance()
        {
            _performanceCap = 0;
            _retryDelay = RetryAfterSeconds;
            _lastRetry = double.NegativeInfinity;
            ResetMeasurements();
        }

        private static void Cap(ref int target, ref FrameRateReason reason, FrameRateReason cause)
        {
            if (target > MinimumRate)
            {
                target = MinimumRate;
                reason = cause;
            }
        }

        private int Publish(int target, FrameRateReason reason)
        {
            Target = target;
            Reason = reason;
            return target;
        }
    }
}
