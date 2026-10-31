using System;
using System.Collections.Generic;
using UnityMobileKit.CameraControl;
using UnityMobileKit.Controllers;
using UnityMobileKit.Geometry;

namespace UnityMobileKit.Tests
{
    public static class ControllerTests
    {
        private const float W = 2400f;
        private const float H = 1080f;

        private static void AssertNear(Float2 expected, Float2 actual, double tolerance, string what)
        {
            Assert.Near(expected.X, actual.X, tolerance, what + ".X");
            Assert.Near(expected.Y, actual.Y, tolerance, what + ".Y");
        }

        private static GamepadState Pad(GamepadButtons buttons = GamepadButtons.None, float lx = 0f, float ly = 0f, float rt = 0f)
            => new GamepadState(new Float2(lx, ly), Float2.Zero, 0f, rt, buttons);

        public static void Register()
        {
            TestHarness.Add("Stick deadzone zeroes the rest position and bad readings", _ =>
            {
                var dz = new StickDeadzone(0.15f, 0.95f);
                Assert.Equal(Float2.Zero, dz.Apply(new Float2(0.1f, -0.1f)), "inside (0.141)");
                Assert.Equal(Float2.Zero, dz.Apply(new Float2(0.15f, 0f)), "exactly on the edge");
                Assert.Equal(Float2.Zero, dz.Apply(new Float2(float.NaN, 0.5f)), "NaN");
                Assert.Equal(Float2.Zero, dz.Apply(new Float2(float.PositiveInfinity, 0f)), "infinity");
            });

            TestHarness.Add("Stick deadzone output starts at zero, is monotonic, and reaches 1 at the outer edge", _ =>
            {
                var dz = new StickDeadzone(0.15f, 0.95f);
                Assert.True(dz.Apply(new Float2(0.155f, 0f)).Length < 0.01f, "no jump just past the deadzone");
                Assert.Near(0.5, dz.Apply(new Float2(0f, 0.55f)).Length, 1e-5, "halfway between inner and outer gives 0.5");
                Assert.Near(1.0, dz.Apply(new Float2(0.95f, 0f)).Length, 1e-6, "outer edge is full");
                Assert.Near(1.0, dz.Apply(new Float2(0f, -1f)).Length, 1e-6, "beyond outer stays full");

                float previous = 0f;
                for (int i = 0; i <= 100; i++)
                {
                    float m = dz.Apply(new Float2(i / 100f, 0f)).Length;
                    Assert.True(m >= previous - 1e-6f, $"monotonic at {i / 100f}");
                    previous = m;
                }
            });

            TestHarness.Add("Stick deadzone keeps the direction and caps square-gate diagonals at 1", _ =>
            {
                var dz = new StickDeadzone(0.15f, 0.95f);
                AssertNear(new Float2(0.6f, 0.8f), dz.Apply(new Float2(0.6f * 0.97f, 0.8f * 0.97f)), 1e-5, "direction preserved at full");
                Float2 diag = dz.Apply(new Float2(1f, 1f));
                Assert.Near(1.0, diag.Length, 1e-6, "diagonal magnitude capped");
                Assert.Near(diag.X, diag.Y, 1e-6, "still 45 degrees");
                var curved = new StickDeadzone(0.15f, 0.95f, exponent: 2f);
                Assert.Near(0.25, curved.Apply(new Float2(0.55f, 0f)).Length, 1e-5, "exponent 2 halves -> quarter");
            });

            TestHarness.Add("Deadzone settings are validated", _ =>
            {
                Assert.Throws<ArgumentOutOfRangeException>(() => new StickDeadzone(-0.1f, 0.9f), "negative inner");
                Assert.Throws<ArgumentOutOfRangeException>(() => new StickDeadzone(0.5f, 0.5f), "outer == inner");
                Assert.Throws<ArgumentOutOfRangeException>(() => new StickDeadzone(0.1f, 1.1f), "outer > 1");
                Assert.Throws<ArgumentOutOfRangeException>(() => new StickDeadzone(0.1f, 0.9f, 0f), "exponent 0");
                Assert.Throws<ArgumentOutOfRangeException>(() => new AxisDeadzone(0.9f, 0.2f), "axis outer < inner");
            });

            TestHarness.Add("Trigger deadzone ignores resting pressure and rescales to 0..1", _ =>
            {
                var dz = new AxisDeadzone(0.1f, 0.9f);
                Assert.Equal(0f, dz.Apply(0.05f), "resting");
                Assert.Equal(0f, dz.Apply(float.NaN), "NaN");
                Assert.Near(0.5, dz.Apply(0.5f), 1e-6, "middle");
                Assert.Equal(1f, dz.Apply(0.95f), "past the outer edge");
            });

            TestHarness.Add("Buttons report one press edge, hold, and one release edge", _ =>
            {
                var b = new ButtonTracker();
                b.Update(GamepadButtons.South, 0.0);
                Assert.True(b.WasPressed(GamepadButtons.South) && b.IsHeld(GamepadButtons.South), "pressed and held");
                b.Update(GamepadButtons.South, 0.1);
                Assert.True(!b.WasPressed(GamepadButtons.South) && b.IsHeld(GamepadButtons.South), "held, no second press");
                b.Update(GamepadButtons.None, 0.2);
                Assert.True(b.WasReleased(GamepadButtons.South) && !b.IsHeld(GamepadButtons.South), "released");
                b.Update(GamepadButtons.None, 0.3);
                Assert.True(!b.WasReleased(GamepadButtons.South), "release reported once");
            });

            TestHarness.Add("Button combos: IsHeld needs all, WasPressed takes any", _ =>
            {
                var b = new ButtonTracker();
                b.Update(GamepadButtons.LeftShoulder, 0.0);
                Assert.True(!b.IsHeld(GamepadButtons.LeftShoulder | GamepadButtons.RightShoulder), "only one shoulder");
                b.Update(GamepadButtons.LeftShoulder | GamepadButtons.RightShoulder, 0.1);
                Assert.True(b.IsHeld(GamepadButtons.LeftShoulder | GamepadButtons.RightShoulder), "both shoulders");
                Assert.True(b.WasPressed(GamepadButtons.LeftShoulder | GamepadButtons.RightShoulder), "any-of press");
                Assert.True(!b.IsHeld(GamepadButtons.None), "None is never held");
            });

            TestHarness.Add("Holding a D-pad direction auto-repeats after a delay at a steady rate", _ =>
            {
                var b = new ButtonTracker { RepeatDelaySeconds = 0.4, RepeatIntervalSeconds = 0.1 };
                var fired = new List<int>();
                for (int i = 0; i <= 63; i++)
                {
                    b.Update(GamepadButtons.DpadDown, i / 60.0);
                    if (b.WasPressedOrRepeated(GamepadButtons.DpadDown)) fired.Add(i);
                }
                Assert.Equal("0,24,30,36,42,48,54,60", string.Join(",", fired), "frames that moved the selection");
                Assert.True(!b.WasPressedOrRepeated(GamepadButtons.DpadUp), "other buttons unaffected");
            });

            TestHarness.Add("A frame hitch gives one repeat, not a burst", _ =>
            {
                var b = new ButtonTracker { RepeatDelaySeconds = 0.4, RepeatIntervalSeconds = 0.1 };
                b.Update(GamepadButtons.DpadRight, 0.0);
                b.Update(GamepadButtons.DpadRight, 0.39);
                Assert.True(!b.WasPressedOrRepeated(GamepadButtons.DpadRight), "before the delay");
                b.Update(GamepadButtons.DpadRight, 2.0);
                Assert.True(b.WasPressedOrRepeated(GamepadButtons.DpadRight), "one repeat after the hitch");
                b.Update(GamepadButtons.DpadRight, 2.016);
                Assert.True(!b.WasPressedOrRepeated(GamepadButtons.DpadRight), "no catch-up burst");
                b.Update(GamepadButtons.DpadRight, 2.1);
                Assert.True(b.WasPressedOrRepeated(GamepadButtons.DpadRight), "normal cadence resumes");
            });

            TestHarness.Add("Releasing restarts the repeat delay; Reset turns held buttons into new presses", _ =>
            {
                var b = new ButtonTracker { RepeatDelaySeconds = 0.4, RepeatIntervalSeconds = 0.1 };
                b.Update(GamepadButtons.DpadUp, 0.0);
                b.Update(GamepadButtons.DpadUp, 0.45);
                b.Update(GamepadButtons.None, 0.47);
                b.Update(GamepadButtons.DpadUp, 0.5);
                b.Update(GamepadButtons.DpadUp, 0.85);
                Assert.True(!b.WasPressedOrRepeated(GamepadButtons.DpadUp), "new delay after re-press");
                b.Update(GamepadButtons.DpadUp, 0.9);
                Assert.True(b.WasPressedOrRepeated(GamepadButtons.DpadUp), "repeats 0.4 s after re-press");

                b.Reset();
                Assert.True(!b.IsHeld(GamepadButtons.DpadUp), "cleared");
                b.Update(GamepadButtons.DpadUp, 1.0);
                Assert.True(b.WasPressed(GamepadButtons.DpadUp), "held after reset counts as a press");
            });

            TestHarness.Add("Virtual cursor speed is in screen heights per second and frame-rate independent", _ =>
            {
                var at60 = new VirtualCursor(W, H) { Speed = 0.9f, MaxBoost = 1f };
                var at30 = new VirtualCursor(W, H) { Speed = 0.9f, MaxBoost = 1f };
                AssertNear(new Float2(W / 2, H / 2), at60.Position, 0, "starts in the middle");
                for (int i = 0; i < 30; i++) at60.Update(new Float2(1f, 0f), 1f / 60f);
                for (int i = 0; i < 15; i++) at30.Update(new Float2(1f, 0f), 1f / 30f);
                AssertNear(new Float2(W / 2 + 0.45f * H, H / 2), at60.Position, 1e-2, "0.5 s at 0.9 screen heights/s");
                AssertNear(at60.Position, at30.Position, 1e-2, "same at 30 fps");
            });

            TestHarness.Add("Virtual cursor stays inside its area (e.g. the safe area)", _ =>
            {
                var cursor = new VirtualCursor(W, H);
                cursor.SetArea(new Float2(100f, 0f), new Float2(2300f, 1080f));
                for (int i = 0; i < 300; i++) cursor.Update(new Float2(-1f, -1f), 1f / 60f);
                AssertNear(new Float2(100f, 0f), cursor.Position, 0, "pinned to the area corner");
                cursor.Warp(new Float2(5000f, 500f));
                AssertNear(new Float2(2300f, 500f), cursor.Position, 0, "warp is clamped too");
                cursor.SetScreen(1080f, 2400f);
                Assert.True(cursor.Position.X <= 1080f, "re-clamped after rotation");
            });

            TestHarness.Add("Virtual cursor boosts only when held fully over", _ =>
            {
                var cursor = new VirtualCursor(W, H) { Speed = 0.5f, MaxBoost = 2f, BoostRampSeconds = 0.5f };
                cursor.Warp(new Float2(0f, H / 2));
                for (int i = 0; i < 60; i++) cursor.Update(new Float2(1f, 0f), 1f / 60f);
                float boosted = cursor.Position.X;
                Assert.True(boosted > 0.5f * H * 1.5f, $"full deflection for 1 s goes faster than base speed ({boosted})");

                var gentle = new VirtualCursor(W, H) { Speed = 0.5f, MaxBoost = 2f, BoostRampSeconds = 0.5f };
                gentle.Warp(new Float2(0f, H / 2));
                for (int i = 0; i < 60; i++) gentle.Update(new Float2(0.5f, 0f), 1f / 60f);
                Assert.Near(0.5 * 0.5 * H, gentle.Position.X, 1e-2, "half deflection: no boost");
                Assert.True(!gentle.Update(Float2.Zero, 1f / 60f), "no input, no movement");
            });

            TestHarness.Add("Gamepad camera pans toward the stick and zooms by doublings per second", _ =>
            {
                var camera = new ZoomPanCamera(1f, 100f, W, H);
                camera.SetSize(40f);
                var pad = new GamepadCamera { PanSpeed = 0.8f, ZoomSpeed = 1f };
                Assert.True(pad.Update(camera, new Float2(1f, 0f), 0f, Float2.Zero, 0.5f), "moved");
                Assert.Near(0.8 * H * 0.5 * (80.0 / H), camera.Center.X, 1e-3, "view moved right by 0.4 screen heights");

                var focus = new Float2(W / 2 + 300f, H / 2);
                Float2 anchor = camera.ScreenToWorld(focus);
                for (int i = 0; i < 60; i++) pad.Update(camera, Float2.Zero, 1f, focus, 1f / 60f);
                Assert.Near(20.0, camera.Size, 1e-3, "one doubling in 1 s halves the size");
                AssertNear(anchor, camera.ScreenToWorld(focus), 1e-3, "zoom keeps the focus point");
                Assert.True(!pad.Update(camera, Float2.Zero, 0f, focus, 1f / 60f), "no input");
            });

            TestHarness.Add("Input mode follows deliberate input; disconnecting mid-game requests a pause", _ =>
            {
                var tracker = new InputModeTracker();
                var modes = new List<InputMode>();
                int pauses = 0;
                tracker.ModeChanged += m => modes.Add(m);
                tracker.PauseRequested += () => pauses++;

                tracker.SetGamepadConnected(true);
                tracker.NotifyGamepad(Pad());
                Assert.Equal(InputMode.Touch, tracker.Mode, "connected but idle controller does not take over");

                tracker.NotifyGamepad(Pad(lx: 0.4f));
                Assert.Equal(InputMode.Gamepad, tracker.Mode, "stick input switches");
                tracker.NotifyGamepad(Pad(GamepadButtons.South));
                tracker.NotifyTouch();
                Assert.Equal(InputMode.Touch, tracker.Mode, "touch switches back");
                tracker.NotifyGamepad(Pad(rt: 0.3f));
                Assert.Equal("Gamepad,Touch,Gamepad", string.Join(",", modes), "one event per actual change");

                tracker.SetGamepadConnected(false);
                Assert.Equal(1, pauses, "pause on disconnect while in use");
                Assert.Equal(InputMode.Touch, tracker.Mode, "falls back to touch");

                tracker.NotifyGamepad(Pad(GamepadButtons.Start));
                Assert.True(tracker.GamepadConnected, "input implies connected");
                tracker.NotifyTouch();
                tracker.SetGamepadConnected(false);
                Assert.Equal(1, pauses, "no pause when the controller was not in use");
            });
        }
    }
}
