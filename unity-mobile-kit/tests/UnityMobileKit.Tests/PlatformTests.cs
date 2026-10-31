using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityMobileKit.Achievements;
using UnityMobileKit.Geometry;
using UnityMobileKit.Gestures;
using UnityMobileKit.Lifecycle;
using UnityMobileKit.Performance;
using UnityMobileKit.Persistence;
using UnityMobileKit.ScreenLayout;
using UnityMobileKit.Settings;

namespace UnityMobileKit.Tests
{
    public static class PlatformTests
    {
        private const float W = 2400f;
        private const float H = 1080f;

        private sealed class FakeSaveable : ISaveable
        {
            public bool HasUnsavedChanges { get; set; }

            public int SaveCount { get; private set; }

            public Exception Failure { get; set; }

            public void Save()
            {
                if (Failure != null) throw Failure;
                SaveCount++;
                HasUnsavedChanges = false;
            }
        }

        private static void AssertNear(Float2 expected, Float2 actual, double tolerance, string what)
        {
            Assert.Near(expected.X, actual.X, tolerance, what + ".X");
            Assert.Near(expected.Y, actual.Y, tolerance, what + ".Y");
        }

        /// <summary>
        /// Runs the policy against a device whose frames need <paramref name="workAt"/> seconds of work;
        /// each frame lasts the longer of that and the current cap's frame budget. Returns every
        /// change of target as (time, target).
        /// </summary>
        private static List<(double Time, int Target)> Simulate(FrameRatePolicy policy, int displayHz, Func<double, double> workAt, double duration)
        {
            var changes = new List<(double, int)>();
            double t = 0.0;
            int target = FrameRate.Resolve(FrameRateMode.Auto, displayHz);
            int last = -1;
            while (t < duration)
            {
                double interval = Math.Max(1.0 / target, workAt(t));
                t += interval;
                target = policy.Update(FrameRateMode.Auto, displayHz, DeviceConditions.Unknown, (float)interval, t);
                if (target != last)
                {
                    changes.Add((t, target));
                    last = target;
                }
            }
            return changes;
        }

        private static string Targets(List<(double Time, int Target)> changes) => string.Join(",", changes.Select(c => c.Target));

        public static void Register()
        {
            TestHarness.Add("Safe-area anchors avoid a punch-hole camera (A72 landscape)", _ =>
            {
                var safe = new RectF(80f, 0f, 2320f, 1080f);
                SafeArea.GetAnchors(safe, W, H, symmetric: false, out var min, out var max);
                AssertNear(new Float2(80f / W, 0f), min, 1e-6, "anchorMin");
                AssertNear(new Float2(1f, 1f), max, 1e-6, "anchorMax");

                SafeArea.GetAnchors(safe, W, H, symmetric: true, out var smin, out var smax);
                AssertNear(new Float2(80f / W, 0f), smin, 1e-6, "symmetric anchorMin");
                AssertNear(new Float2(1f - 80f / W, 1f), smax, 1e-6, "symmetric anchorMax");
            });

            TestHarness.Add("Symmetric anchors stay the same when rotation moves the notch to the other side", dir =>
            {
                SafeArea.GetAnchors(new RectF(80f, 0f, 2320f, 1080f), W, H, true, out var leftMin, out var leftMax);
                SafeArea.GetAnchors(new RectF(0f, 0f, 2320f, 1080f), W, H, true, out var rightMin, out var rightMax);
                AssertNear(leftMin, rightMin, 1e-6, "anchorMin");
                AssertNear(leftMax, rightMax, 1e-6, "anchorMax");
                SafeArea.GetAnchors(new RectF(0f, 0f, 2320f, 1080f), W, H, false, out _, out var asymMax);
                Assert.Near(2320.0 / W, asymMax.X, 1e-6, "asymmetric follows the notch");
            });

            TestHarness.Add("Unusable safe areas fall back to the screen; overhanging ones are clipped", _ =>
            {
                var full = new RectF(0f, 0f, W, H);
                Assert.Equal(full, SafeArea.Sanitize(new RectF(0f, 0f, 0f, 0f), W, H), "empty");
                Assert.Equal(full, SafeArea.Sanitize(new RectF(float.NaN, 0f, 100f, 100f), W, H), "NaN");
                Assert.Equal(full, SafeArea.Sanitize(new RectF(5000f, 0f, 100f, 100f), W, H), "entirely off-screen");
                Assert.Equal(new RectF(0f, 0f, 2300f, H), SafeArea.Sanitize(new RectF(-50f, -10f, 2350f, 2000f), W, H), "clipped");
                SafeArea.GetAnchors(new RectF(0f, 0f, 10f, H), W, H, true, out var min, out var max);
                Assert.True(max.X > min.X, "absurd symmetric input still gives a valid panel");
                Assert.Throws<ArgumentOutOfRangeException>(() => SafeArea.Sanitize(full, 0f, H), "zero screen");
            });

            TestHarness.Add("UI scale matches CanvasScaler's width/height match in log space", _ =>
            {
                Assert.Near(1.0, UiScale.ScaleWithScreenSize(W, H, 1920f, 1080f, 1f), 1e-6, "match height on 20:9");
                Assert.Near(1.25, UiScale.ScaleWithScreenSize(W, H, 1920f, 1080f, 0f), 1e-6, "match width on 20:9");
                Assert.Near(Math.Sqrt(1.25), UiScale.ScaleWithScreenSize(W, H, 1920f, 1080f, 0.5f), 1e-6, "halfway");
                Assert.Near(1.0, UiScale.ScaleWithScreenSize(3840f, 540f, 1920f, 1080f, 0.5f), 1e-6, "2x wide, half tall at 0.5");
                Assert.Throws<ArgumentOutOfRangeException>(() => UiScale.ScaleWithScreenSize(W, H, 1920f, 1080f, 1.5f), "match > 1");
                Assert.Throws<ArgumentOutOfRangeException>(() => UiScale.ScaleWithScreenSize(W, H, 0f, 1080f, 0.5f), "zero reference");
            });

            TestHarness.Add("Touch targets: 48 dp in canvas units for a given density and scale", _ =>
            {
                Assert.Near(121.5, UiScale.TouchTargetInReferenceUnits(405f, 1f), 1e-4, "405 dpi, scale 1");
                Assert.Near(97.2, UiScale.TouchTargetInReferenceUnits(405f, 1.25f), 1e-4, "405 dpi, scale 1.25");
                Assert.Near(96.0, UiScale.TouchTargetInReferenceUnits(0f, 1f), 1e-4, "unknown dpi uses 320");
                Assert.Near(10.0, ScreenDensity.DpToPixels(10f, 160f), 1e-6, "160 dpi: 1 dp = 1 px");
                Assert.Near(20.0, ScreenDensity.DpToPixels(10f, float.NaN), 1e-6, "NaN dpi uses fallback");
                Assert.Equal(ScreenDensity.FallbackDpi, GestureRecognizer.FallbackDpi, "one fallback everywhere");
                Assert.Throws<ArgumentOutOfRangeException>(() => UiScale.TouchTargetInReferenceUnits(400f, 0f), "zero scale");
            });

            TestHarness.Add("Fixed frame rates are respected except under critical heat", _ =>
            {
                var policy = new FrameRatePolicy();
                var draining = new DeviceConditions(0.05f, false, true, ThermalLevel.Serious);
                Assert.Equal(60, policy.Update(FrameRateMode.Fps60, 90, draining, 1f / 60f, 0.0), "Fps60 despite battery saver, low battery, serious heat");
                Assert.Equal(FrameRateReason.Preferred, policy.Reason, "reason");
                Assert.Equal(30, policy.Update(FrameRateMode.Fps30, 90, DeviceConditions.Unknown, 1f / 30f, 0.1), "Fps30");
                var critical = new DeviceConditions(0.9f, true, false, ThermalLevel.Critical);
                Assert.Equal(30, policy.Update(FrameRateMode.Fps60, 60, critical, 1f / 60f, 0.2), "critical heat caps Fps60");
                Assert.Equal(FrameRateReason.Thermal, policy.Reason, "thermal reason");
            });

            TestHarness.Add("Auto follows the display and saves power when it should", _ =>
            {
                var policy = new FrameRatePolicy();
                Assert.Equal(90, policy.Update(FrameRateMode.Auto, 90, DeviceConditions.Unknown, 1f / 90f, 0.0), "90 Hz display");
                Assert.Equal(60, policy.Update(FrameRateMode.Auto, 60, DeviceConditions.Unknown, 1f / 60f, 0.1), "60 Hz display");

                void Expect(DeviceConditions c, int rate, FrameRateReason reason, string what)
                {
                    var p = new FrameRatePolicy();
                    Assert.Equal(rate, p.Update(FrameRateMode.Auto, 90, c, 1f / 60f, 0.0), what);
                    Assert.Equal(reason, p.Reason, what + " (reason)");
                }
                Expect(new DeviceConditions(0.8f, false, true, ThermalLevel.Nominal), 30, FrameRateReason.LowPowerMode, "battery saver");
                Expect(new DeviceConditions(0.10f, false, false, ThermalLevel.Nominal), 30, FrameRateReason.LowBattery, "10% unplugged");
                Expect(new DeviceConditions(0.10f, true, false, ThermalLevel.Nominal), 90, FrameRateReason.Preferred, "10% charging");
                Expect(new DeviceConditions(-1f, false, false, ThermalLevel.Nominal), 90, FrameRateReason.Preferred, "unknown battery");
                Expect(new DeviceConditions(0.8f, false, false, ThermalLevel.Serious), 30, FrameRateReason.Thermal, "serious heat");
                Expect(new DeviceConditions(0.8f, false, false, ThermalLevel.Fair), 90, FrameRateReason.Preferred, "fair heat");
            });

            TestHarness.Add("A device that can't hold 60 FPS drops to 30 after about 3 seconds", _ =>
            {
                var changes = Simulate(new FrameRatePolicy(), 60, t => 0.025, 10.0);
                Assert.Equal("60,30", Targets(changes), "targets");
                Assert.True(changes[1].Time > 3.0 && changes[1].Time < 3.6, $"step-down at {changes[1].Time:F2} s");
            });

            TestHarness.Add("One long loading hitch does not lower the frame rate", _ =>
            {
                bool hitched = false;
                var changes = Simulate(new FrameRatePolicy(), 60, t =>
                {
                    if (t < 5.0 || hitched) return 0.01;
                    hitched = true;
                    return 2.0;
                }, 15.0);
                Assert.True(hitched, "precondition: hitch happened");
                Assert.Equal("60", Targets(changes), "stayed at 60");
            });

            TestHarness.Add("Failed retries back off 30, 60, 120, 240 s, then stay at the 300 s cap", _ =>
            {
                var changes = Simulate(new FrameRatePolicy(), 60, t => 0.025, 770.0);
                Assert.Equal("60,30,60,30,60,30,60,30,60,30,60,30", Targets(changes), "targets");
                double[] expected = { 30.0, 60.0, 120.0, 240.0, 300.0 };
                for (int i = 0; i < expected.Length; i++)
                {
                    double wait = changes[2 * i + 2].Time - changes[2 * i + 1].Time;
                    Assert.Near(expected[i], wait, 0.05, $"wait {i + 1}");
                }
            });

            TestHarness.Add("Short slowdowns separated by recovery don't add up to a step-down", _ =>
            {
                bool Slow(double t) => (t >= 5.0 && t < 7.0) || (t >= 12.0 && t < 14.0);
                var changes = Simulate(new FrameRatePolicy(), 60, t => Slow(t) ? 0.025 : 0.01, 20.0);
                Assert.Equal("60", Targets(changes), "two 2-second slowdowns 5 s apart");
            });

            TestHarness.Add("ResetMeasurements restarts the evidence window", _ =>
            {
                var policy = new FrameRatePolicy();
                double t = 0;
                while (t < 2.9) policy.Update(FrameRateMode.Auto, 60, DeviceConditions.Unknown, 0.025f, t += 0.025);
                Assert.Equal(60, policy.Target, "precondition: slow, but not for long enough yet");

                policy.ResetMeasurements();
                double resetAt = t;
                while (policy.Target == 60 && t < resetAt + 10.0) policy.Update(FrameRateMode.Auto, 60, DeviceConditions.Unknown, 0.025f, t += 0.025);
                Assert.Equal(30, policy.Target, "still steps down when the slowness continues");
                Assert.True(t - resetAt > 3.2, $"old average discarded: stepped down {t - resetAt:F2} s after the reset");
            });

            TestHarness.Add("A retry that sticks resets the backoff", _ =>
            {
                var changes = Simulate(new FrameRatePolicy(), 60, t => t < 50.0 || t >= 200.0 ? 0.025 : 0.01, 235.0);
                Assert.Equal("60,30,60,30,60,30,60", Targets(changes), "targets");
                Assert.Near(60.0, changes[4].Time - changes[3].Time, 0.05, "doubled wait before the device recovered");
                Assert.Near(30.0, changes[6].Time - changes[5].Time, 0.05, "wait back to 30 s after a stable minute");
            });

            TestHarness.Add("On a 90 Hz screen the policy steps down to 60 before 30", _ =>
            {
                Assert.Equal("90,60", Targets(Simulate(new FrameRatePolicy(), 90, t => 0.014, 10.0)), "71 FPS device settles at 60");
                Assert.Equal("90,60,30", Targets(Simulate(new FrameRatePolicy(), 90, t => 0.025, 10.0)), "40 FPS device settles at 30");
            });

            TestHarness.Add("Choosing a fixed rate clears the performance step-down", _ =>
            {
                var policy = new FrameRatePolicy();
                double t = 0;
                for (int i = 0; i < 200; i++) policy.Update(FrameRateMode.Auto, 60, DeviceConditions.Unknown, 0.025f, t += 0.025);
                Assert.Equal(FrameRateReason.Performance, policy.Reason, "precondition: stepped down");
                Assert.Equal(60, policy.Update(FrameRateMode.Fps60, 60, DeviceConditions.Unknown, 0.025f, t += 0.025), "fixed 60");
                Assert.Equal(60, policy.Update(FrameRateMode.Auto, 60, DeviceConditions.Unknown, 0.0167f, t += 0.0167), "back on Auto without the old cap");
            });

            TestHarness.Add("Losing focus suspends and saves once; restoring needs focus and no pause", _ =>
            {
                var dirty = new FakeSaveable { HasUnsavedChanges = true };
                var clean = new FakeSaveable();
                var life = new LifecycleCoordinator(dirty, clean);
                var events = new List<string>();
                life.Suspended += () => events.Add("suspended");
                life.Restored += () => events.Add("restored");

                life.OnFocusChanged(false);
                life.OnPauseChanged(true);
                life.OnPauseChanged(false);
                Assert.True(life.IsSuspended, "still unfocused");
                life.OnFocusChanged(true);

                Assert.Equal("suspended,restored", string.Join(",", events), "one transition each way");
                Assert.Equal(1, dirty.SaveCount, "dirty saved once");
                Assert.Equal(0, clean.SaveCount, "clean not rewritten");
            });

            TestHarness.Add("A failing save doesn't stop the others or escape the platform callback", _ =>
            {
                var broken = new FakeSaveable { HasUnsavedChanges = true, Failure = new IOException("disk full (simulated)") };
                var denied = new FakeSaveable { HasUnsavedChanges = true, Failure = new UnauthorizedAccessException("read-only (simulated)") };
                var fine = new FakeSaveable { HasUnsavedChanges = true };
                var life = new LifecycleCoordinator(broken, denied, fine);

                life.OnPauseChanged(true);
                Assert.Equal(1, fine.SaveCount, "healthy item still saved");
                Assert.True(life.LastSaveError is UnauthorizedAccessException, "last error recorded");

                broken.Failure = null;
                denied.Failure = null;
                Assert.Equal(0, life.SaveAll(), "retry succeeds");
                Assert.True(life.LastSaveError == null, "error cleared after a clean save");
            });

            TestHarness.Add("Quit saves; registration ignores duplicates and rejects null", _ =>
            {
                var item = new FakeSaveable { HasUnsavedChanges = true, Failure = new IOException("disk full (simulated)") };
                var life = new LifecycleCoordinator(item);
                life.Register(item);
                Assert.Equal(1, life.SaveAll(), "registered twice, attempted once");

                item.Failure = null;
                life.OnQuit();
                Assert.Equal(1, item.SaveCount, "saved once on quit");
                Assert.Throws<ArgumentNullException>(() => life.Register(null), "null");
            });

            TestHarness.Add("Backgrounding the app flushes real settings and achievements to disk", dir =>
            {
                var store = new AtomicFileStore(dir);
                var settings = new GameSettings(store);
                var achievements = new AchievementTracker(new[] { new AchievementDefinition("trips", "Trips", "", 100) }, store)
                {
                    AutoSaveOnUnlock = false,
                };
                var life = new LifecycleCoordinator(settings, achievements);

                settings.FrameRate = FrameRateMode.Fps30;
                achievements.Report("trips", 42);
                life.OnFocusChanged(false);
                life.OnPauseChanged(true);

                var reloadedSettings = new GameSettings(new AtomicFileStore(dir));
                var reloadedAchievements = new AchievementTracker(new[] { new AchievementDefinition("trips", "Trips", "", 100) }, new AtomicFileStore(dir));
                Assert.Equal(SaveLoadResult.LoadedPrimary, reloadedSettings.Load(), "settings file");
                Assert.Equal(SaveLoadResult.LoadedPrimary, reloadedAchievements.Load(), "achievements file");
                Assert.Equal(FrameRateMode.Fps30, reloadedSettings.FrameRate, "setting persisted");
                Assert.Equal(42, reloadedAchievements.GetState("trips").Progress, "progress persisted");
            });
        }
    }
}
