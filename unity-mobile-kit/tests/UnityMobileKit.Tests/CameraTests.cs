using System;
using UnityMobileKit.CameraControl;
using UnityMobileKit.Geometry;
using UnityMobileKit.Gestures;

namespace UnityMobileKit.Tests
{
    public static class CameraTests
    {
        // Galaxy A72 in landscape: 2400 x 1080 px.
        private const float W = 2400f;
        private const float H = 1080f;

        private static void AssertNear(Float2 expected, Float2 actual, double tolerance, string what)
        {
            Assert.Near(expected.X, actual.X, tolerance, what + ".X");
            Assert.Near(expected.Y, actual.Y, tolerance, what + ".Y");
        }

        private static ZoomPanCamera NewCamera(float initialSize = 20f)
        {
            var camera = new ZoomPanCamera(2f, 50f, W, H);
            camera.SetSize(initialSize);
            return camera;
        }

        public static void Register()
        {
            TestHarness.Add("Camera rejects invalid limits, viewports and zoom factors", _ =>
            {
                Assert.Throws<ArgumentOutOfRangeException>(() => new ZoomPanCamera(0f, 10f, W, H), "min 0");
                Assert.Throws<ArgumentOutOfRangeException>(() => new ZoomPanCamera(float.NaN, 10f, W, H), "min NaN");
                Assert.Throws<ArgumentOutOfRangeException>(() => new ZoomPanCamera(5f, 4f, W, H), "max < min");
                Assert.Throws<ArgumentOutOfRangeException>(() => new ZoomPanCamera(1f, 10f, 0f, H), "zero width");
                Assert.Throws<ArgumentOutOfRangeException>(() => new ZoomPanCamera(1f, 10f, W, float.NaN), "NaN height");
                var camera = NewCamera();
                foreach (var bad in new[] { 0f, -1f, float.NaN, float.PositiveInfinity })
                {
                    Assert.Throws<ArgumentOutOfRangeException>(() => camera.ZoomAt(Float2.Zero, bad), $"factor {bad}");
                }
                Assert.Throws<ArgumentException>(() => camera.SetBounds(new Float2(1, 1), new Float2(0, 5)), "inverted bounds");
            });

            TestHarness.Add("Screen and world conversions are inverse and match the view extents", _ =>
            {
                var camera = NewCamera(10f);
                camera.SetCenter(new Float2(100f, -40f));
                AssertNear(new Float2(100f, -40f), camera.ScreenToWorld(new Float2(W / 2, H / 2)), 1e-4, "screen middle is the center");
                AssertNear(new Float2(100f + 10f * W / H, -30f), camera.ScreenToWorld(new Float2(W, H)), 1e-3, "top-right corner");
                var p = new Float2(321.5f, 987.25f);
                AssertNear(p, camera.WorldToScreen(camera.ScreenToWorld(p)), 1e-3, "round trip");
                Assert.Near(20.0 / H, camera.WorldUnitsPerPixel, 1e-9, "world units per pixel");
            });

            TestHarness.Add("Panning keeps the touched world point under the finger", _ =>
            {
                var camera = NewCamera();
                var finger = new Float2(500f, 300f);
                Float2 touched = camera.ScreenToWorld(finger);
                var delta = new Float2(-220f, 135f);
                camera.Pan(delta);
                AssertNear(touched, camera.ScreenToWorld(finger + delta), 1e-4, "point followed the finger");
            });

            TestHarness.Add("Zooming keeps the world point under the focus fixed, also off-center", _ =>
            {
                var camera = NewCamera(20f);
                foreach (var focus in new[] { new Float2(W / 2, H / 2), new Float2(10f, 1070f), new Float2(2300f, 40f) })
                {
                    Float2 before = camera.ScreenToWorld(focus);
                    float size = camera.Size;
                    camera.ZoomAt(focus, 1.25f);
                    Assert.Near(size / 1.25, camera.Size, 1e-4, "size divided by factor");
                    AssertNear(before, camera.ScreenToWorld(focus), 1e-4, $"fixed point at {focus}");
                }
            });

            TestHarness.Add("Zoom stops at the limits and still keeps the focus point fixed", _ =>
            {
                var camera = NewCamera(3f);
                var focus = new Float2(1800f, 200f);
                Float2 before = camera.ScreenToWorld(focus);
                camera.ZoomAt(focus, 10f);
                Assert.Near(2.0, camera.Size, 0, "clamped to min size");
                AssertNear(before, camera.ScreenToWorld(focus), 1e-4, "focus fixed at the limit");
                camera.ZoomAt(focus, 0.001f);
                Assert.Near(50.0, camera.Size, 0, "clamped to max size");
                camera.SetSize(float.PositiveInfinity);
                Assert.Near(50.0, camera.Size, 0, "SetSize clamps too");
            });

            TestHarness.Add("A real pinch keeps the world point between the fingers between the fingers", _ =>
            {
                var camera = NewCamera(20f);
                var gestures = new GestureRecognizer(400f);
                var a = new Float2(900f, 500f);
                var b = new Float2(1300f, 600f);
                camera.Apply(gestures.Update(new[] { new TouchSample(0, a), new TouchSample(1, b) }, 0.0));
                Float2 anchor = camera.ScreenToWorld(Float2.Midpoint(a, b));

                for (int i = 1; i <= 30; i++)
                {
                    a += new Float2(-9f, 4f);
                    b += new Float2(14f, 7f);
                    camera.Apply(gestures.Update(new[] { new TouchSample(0, a), new TouchSample(1, b) }, i / 60.0));
                }
                Assert.True(camera.Size < 20f, "fingers spread, so the camera zoomed in");
                AssertNear(anchor, camera.ScreenToWorld(Float2.Midpoint(a, b)), 1e-2, "anchor under the midpoint after 30 frames");
            });

            TestHarness.Add("Bounds stop panning at the edges and center an oversized view", _ =>
            {
                var camera = NewCamera(10f);
                camera.SetBounds(new Float2(0f, 0f), new Float2(200f, 100f));
                camera.Pan(new Float2(1e6f, 1e6f));
                Float2 half = camera.HalfExtents;
                AssertNear(new Float2(half.X, half.Y), camera.Center, 1e-3, "pinned to the bottom-left corner");
                camera.Pan(new Float2(-1e6f, -1e6f));
                AssertNear(new Float2(200f - half.X, 100f - half.Y), camera.Center, 1e-3, "pinned to the top-right corner");

                camera.SetSize(50f);
                AssertNear(new Float2(100f, 50f), camera.Center, 1e-3, "view larger than bounds: centered");
            });

            TestHarness.Add("Rotating or resizing the screen re-applies the bounds", _ =>
            {
                var camera = new ZoomPanCamera(1f, 100f, 1080f, 2400f);
                camera.SetSize(20f);
                camera.SetBounds(new Float2(-100f, -100f), new Float2(100f, 100f));
                camera.SetCenter(new Float2(95f, 0f));
                float portraitX = camera.Center.X;
                camera.SetViewport(2400f, 1080f);
                Assert.True(camera.Center.X < portraitX, "wider view pulled back from the edge");
                Assert.Near(100.0 - camera.HalfExtents.X, camera.Center.X, 1e-3, "exactly at the edge");
            });

            TestHarness.Add("Apply ignores empty frames and pans without zooming for drags", _ =>
            {
                var camera = NewCamera();
                camera.Apply(GestureFrame.None);
                AssertNear(Float2.Zero, camera.Center, 0, "no-op");
                camera.Apply(new GestureFrame(new Float2(100f, 0f), 1f, Float2.Zero, true, false, false, Float2.Zero));
                Assert.Near(20.0, camera.Size, 0, "drag does not zoom");
                Assert.True(camera.Center.X < 0f, "drag right moves the view left");
            });

            TestHarness.Add("Auto-zoom target fits the points with the margin, limited by the zoom range", dir =>
            {
                var camera = NewCamera();
                var auto = new AutoZoom(camera) { ScreenMargin = 0.1f };
                Assert.True(!auto.TryGetTarget(null, out _, out _), "null");
                Assert.True(!auto.TryGetTarget(new Float2[0], out _, out _), "empty");

                Assert.True(auto.TryGetTarget(new[] { new Float2(5f, 5f) }, out var c1, out var s1), "single point");
                Assert.Equal(new Float2(5f, 5f), c1, "centered on it");
                Assert.Near(2.0, s1, 0, "single point uses the closest zoom");

                auto.TryGetTarget(new[] { new Float2(-40f, 0f), new Float2(40f, 10f) }, out var c2, out var s2);
                AssertNear(new Float2(0f, 5f), c2, 1e-5, "box center");
                Assert.Near(40.0 / (W / H) / 0.8, s2, 1e-4, "wide box: width decides, plus margin");

                auto.TryGetTarget(new[] { new Float2(0f, -12f), new Float2(1f, 12f) }, out _, out var s3);
                Assert.Near(12.0 / 0.8, s3, 1e-4, "tall box: height decides, plus margin");

                auto.TryGetTarget(new[] { new Float2(-1000f, 0f), new Float2(1000f, 0f) }, out _, out var s4);
                Assert.Near(50.0, s4, 0, "clamped to max size");
                Assert.Throws<ArgumentOutOfRangeException>(() => auto.ScreenMargin = 0.5f, "margin too large");
            });

            TestHarness.Add("Auto-zoom converges smoothly and does not depend on frame rate", _ =>
            {
                var points = new[] { new Float2(30f, 20f), new Float2(50f, 30f) };
                var at60 = NewCamera(40f);
                var at30 = NewCamera(40f);
                var auto60 = new AutoZoom(at60);
                var auto30 = new AutoZoom(at30);
                for (int i = 0; i < 60; i++) auto60.Update(points, i / 60.0, 1f / 60f);
                for (int i = 0; i < 30; i++) auto30.Update(points, i / 30.0, 1f / 30f);
                Assert.Near(at60.Size, at30.Size, 1e-3, "same size after 1 s at 60 and 30 fps");
                AssertNear(at60.Center, at30.Center, 1e-3, "same center after 1 s at 60 and 30 fps");

                auto60.TryGetTarget(points, out var target, out var targetSize);
                Assert.True(Math.Abs(at60.Size - targetSize) < Math.Abs(40f - targetSize), "moved toward the target");
                for (int i = 60; i < 600; i++) auto60.Update(points, i / 60.0, 1f / 60f);
                Assert.Near(targetSize, at60.Size, 1e-3, "converged size");
                AssertNear(target, at60.Center, 1e-3, "converged center");
            });

            TestHarness.Add("Auto-zoom steps aside while the player touches and when switched off", _ =>
            {
                var points = new[] { new Float2(100f, 100f) };
                var camera = NewCamera();
                var auto = new AutoZoom(camera) { ResumeDelaySeconds = 3.0 };

                auto.Observe(new GestureFrame(new Float2(5f, 0f), 1f, Float2.Zero, true, false, false, Float2.Zero), 10.0);
                Assert.True(!auto.Update(points, 12.9, 0.1f), "suspended 2.9 s after a drag");
                Assert.Equal(Float2.Zero, camera.Center, "camera untouched while suspended");
                Assert.True(auto.Update(points, 13.0, 0.1f), "resumes after 3 s");

                auto.Observe(GestureFrame.None, 20.0);
                Assert.True(!auto.IsSuspended(20.0), "an idle frame does not suspend");

                auto.Enabled = false;
                Float2 before = camera.Center;
                Assert.True(!auto.Update(points, 30.0, 0.1f), "disabled");
                Assert.Equal(before, camera.Center, "camera untouched when disabled");

                auto.Enabled = true;
                Assert.True(!auto.Update(points, 31.0, 0f), "zero delta time does nothing");
            });
        }
    }
}
