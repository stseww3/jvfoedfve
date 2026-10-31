using System.Globalization;
using UnityMobileKit.Geometry;
using UnityMobileKit.Input;

namespace UnityMobileKit.Tests
{
    public static class GestureTests
    {
        private const double Dt = 1.0 / 60.0;

        private static TouchSample T(int id, float x, float y) => new TouchSample(id, x, y);

        private static void AssertNear(Float2 expected, Float2 actual, string what)
        {
            Assert.Near(expected.X, actual.X, 1e-4, what + ".X");
            Assert.Near(expected.Y, actual.Y, 1e-4, what + ".Y");
        }

        /// <summary>160 dpi makes 1 dp = 1 px, so the default slop is exactly 10 px.</summary>
        private static GestureRecognizer New160() => new GestureRecognizer(160f);

        public static void Register()
        {
            TestHarness.Add("Float2 arithmetic, distance, midpoint, clamp and invariant formatting", _ =>
            {
                var a = new Float2(1f, 2f);
                var b = new Float2(4f, 6f);
                Assert.Equal(new Float2(5f, 8f), a + b, "add");
                Assert.Equal(new Float2(3f, 4f), b - a, "subtract");
                Assert.Equal(new Float2(2f, 4f), a * 2f, "scale");
                Assert.Equal(new Float2(2f, 4f), 2f * a, "scale (left)");
                Assert.Equal(new Float2(2f, 3f), b / 2f, "divide");
                Assert.Near(5.0, Float2.Distance(a, b), 1e-6, "3-4-5 distance");
                Assert.Equal(new Float2(2.5f, 4f), Float2.Midpoint(a, b), "midpoint");
                Assert.Equal(new Float2(0f, 10f), Float2.Clamp(new Float2(-5f, 50f), Float2.Zero, new Float2(10f, 10f)), "clamp");
                Assert.True(a == new Float2(1f, 2f) && a != b, "equality operators");

                var original = CultureInfo.CurrentCulture;
                try
                {
                    CultureInfo.CurrentCulture = new CultureInfo("de-DE");
                    Assert.Equal("(1.5, -2)", new Float2(1.5f, -2f).ToString(), "ToString ignores device locale");
                }
                finally
                {
                    CultureInfo.CurrentCulture = original;
                }
            });

            TestHarness.Add("A quick touch is one tap at the place the finger went down", _ =>
            {
                var g = New160();
                Assert.True(!g.Update(new[] { T(0, 100, 200) }, 0.0).Tapped, "down");
                Assert.True(!g.Update(new[] { T(0, 103, 198) }, 0.1).Tapped, "small wobble");
                var up = g.Update(new TouchSample[0], 0.2);
                Assert.True(up.Tapped, "tap on release");
                Assert.Equal(new Float2(100, 200), up.TapPosition, "tap position");
                Assert.True(!g.Update(new TouchSample[0], 0.3).Tapped, "tap reported once");
            });

            TestHarness.Add("Wobble inside the slop never pans the camera", _ =>
            {
                var g = New160();
                g.Update(new[] { T(0, 100, 100) }, 0.0);
                var f = g.Update(new[] { T(0, 107, 106) }, Dt);
                Assert.Equal(Float2.Zero, f.Pan, "no pan within slop (9.2 px of 10)");
                Assert.True(!f.IsDragging, "not dragging");
            });

            TestHarness.Add("A press held longer than the tap limit is not a tap", _ =>
            {
                var g = New160();
                g.Update(new[] { T(0, 100, 100) }, 0.0);
                g.Update(new[] { T(0, 100, 100) }, 0.25);
                Assert.True(!g.Update(new TouchSample[0], 0.31).Tapped, "0.31 s press");
            });

            TestHarness.Add("Dragging catches up on the first move, then follows the finger exactly", _ =>
            {
                var g = New160();
                var path = new[] { (100f, 100f), (104f, 100f), (108f, 101f), (115f, 103f), (140f, 110f), (139f, 150f) };
                var total = Float2.Zero;
                for (int i = 0; i < path.Length; i++)
                {
                    var f = g.Update(new[] { T(7, path[i].Item1, path[i].Item2) }, i * Dt);
                    total += f.Pan;
                    if (i < 3) Assert.Equal(Float2.Zero, f.Pan, $"no pan before slop, frame {i}");
                    if (i == 3) AssertNear(new Float2(15, 3), f.Pan, "first drag frame includes the movement inside the slop");
                    if (i >= 3) Assert.True(f.IsDragging, $"dragging, frame {i}");
                }
                AssertNear(new Float2(39, 50), total, "sum of pans equals finger displacement");
                Assert.True(!g.Update(new TouchSample[0], 0.1).Tapped, "a drag is not a tap");
            });

            TestHarness.Add("The tap slop scales with screen density", _ =>
            {
                bool IsTap(GestureRecognizer g)
                {
                    g.Update(new[] { T(0, 0, 0) }, 0.0);
                    g.Update(new[] { T(0, 20, 0) }, 0.05);
                    return g.Update(new TouchSample[0], 0.1).Tapped;
                }
                Assert.True(!IsTap(new GestureRecognizer(160f)), "20 px is a drag at 160 dpi (slop 10 px)");
                Assert.True(IsTap(new GestureRecognizer(480f)), "20 px is a tap at 480 dpi (slop 30 px)");
                Assert.Near(20.0, new GestureRecognizer(0f).TapSlopPixels, 1e-6, "unknown dpi uses 320 dpi");
                Assert.Near(20.0, new GestureRecognizer(float.PositiveInfinity).TapSlopPixels, 1e-6, "infinite dpi uses fallback");
            });

            TestHarness.Add("Pinch: first frame is a baseline, then zoom is the ratio of finger distances", _ =>
            {
                var g = New160();
                var start = g.Update(new[] { T(0, 100, 100), T(1, 200, 100) }, 0.0);
                Assert.True(start.IsPinching, "pinching");
                Assert.Near(1.0, start.Zoom, 0, "baseline zoom");
                Assert.Equal(Float2.Zero, start.Pan, "baseline pan");

                var spread = g.Update(new[] { T(0, 75, 100), T(1, 225, 100) }, Dt);
                Assert.Near(1.5, spread.Zoom, 1e-6, "100 -> 150 px apart");
                AssertNear(new Float2(150, 100), spread.Focus, "focus is the midpoint");
                AssertNear(Float2.Zero, spread.Pan, "symmetric spread does not pan");

                double product = spread.Zoom;
                product *= g.Update(new[] { T(0, 100, 100), T(1, 200, 100) }, 2 * Dt).Zoom;
                product *= g.Update(new[] { T(0, 50, 100), T(1, 250, 100) }, 3 * Dt).Zoom;
                Assert.Near(2.0, product, 1e-5, "zoom factors multiply to final/initial distance (200/100)");
            });

            TestHarness.Add("Two fingers moving together pan by the midpoint's movement", _ =>
            {
                var g = New160();
                g.Update(new[] { T(0, 100, 100), T(1, 200, 100) }, 0.0);
                var f = g.Update(new[] { T(0, 110, 105), T(1, 210, 105) }, Dt);
                AssertNear(new Float2(10, 5), f.Pan, "pan");
                Assert.Near(1.0, f.Zoom, 1e-6, "no zoom");
            });

            TestHarness.Add("The order the platform lists fingers in does not matter, even if it changes", _ =>
            {
                var g1 = New160();
                var g2 = New160();
                g1.Update(new[] { T(3, 100, 100), T(8, 300, 100) }, 0.0);
                g2.Update(new[] { T(8, 300, 100), T(3, 100, 100) }, 0.0);
                var f1 = g1.Update(new[] { T(3, 90, 120), T(8, 330, 80) }, Dt);
                var f2 = g2.Update(new[] { T(3, 90, 120), T(8, 330, 80) }, Dt);
                Assert.True(f1.Zoom > 1.2f, "precondition: the fingers spread");
                Assert.Equal(f1.Zoom, f2.Zoom, "zoom");
                Assert.Equal(f1.Pan, f2.Pan, "pan");
                Assert.Equal(f1.Focus, f2.Focus, "focus");
            });

            TestHarness.Add("A second finger during a tap cancels the tap", _ =>
            {
                var g = New160();
                g.Update(new[] { T(0, 100, 100) }, 0.0);
                g.Update(new[] { T(0, 100, 100), T(1, 300, 100) }, 0.05);
                g.Update(new[] { T(0, 100, 100) }, 0.1);
                Assert.True(!g.Update(new TouchSample[0], 0.15).Tapped, "no tap after a two-finger touch");
            });

            TestHarness.Add("Drag to pinch and pinch to drag switch over without a jump", _ =>
            {
                var g = New160();
                g.Update(new[] { T(0, 100, 100) }, 0.0);
                Assert.True(g.Update(new[] { T(0, 150, 100) }, Dt).IsDragging, "dragging");

                var toPinch = g.Update(new[] { T(0, 150, 100), T(1, 400, 400) }, 2 * Dt);
                Assert.True(toPinch.IsPinching && !toPinch.IsDragging, "now pinching");
                Assert.Equal(Float2.Zero, toPinch.Pan, "no pan on the switch frame");
                Assert.Near(1.0, toPinch.Zoom, 0, "no zoom on the switch frame");

                var toOne = g.Update(new[] { T(1, 400, 400) }, 3 * Dt);
                Assert.Equal(Float2.Zero, toOne.Pan, "remaining finger does not jump");
                Assert.True(!toOne.IsPinching, "pinch over");

                var moved = g.Update(new[] { T(1, 430, 400) }, 4 * Dt);
                AssertNear(new Float2(30, 0), moved.Pan, "remaining finger can drag after the slop");
            });

            TestHarness.Add("A finger left over from a pinch never taps", _ =>
            {
                var g = New160();
                g.Update(new[] { T(0, 100, 100), T(1, 200, 100) }, 0.0);
                g.Update(new[] { T(1, 200, 100) }, 0.05);
                Assert.True(!g.Update(new TouchSample[0], 0.1).Tapped, "quick release after a pinch");
            });

            TestHarness.Add("With three fingers the two lowest ids pinch; swapping the pair rebaselines", _ =>
            {
                var g = New160();
                g.Update(new[] { T(0, 100, 100), T(1, 200, 100), T(2, 900, 900) }, 0.0);
                var thirdMoves = g.Update(new[] { T(0, 100, 100), T(1, 200, 100), T(2, 500, 500) }, Dt);
                Assert.Near(1.0, thirdMoves.Zoom, 0, "third finger is ignored");
                Assert.Equal(Float2.Zero, thirdMoves.Pan, "third finger does not pan");

                var swapped = g.Update(new[] { T(1, 200, 100), T(2, 500, 500) }, 2 * Dt);
                Assert.Near(1.0, swapped.Zoom, 0, "new pair: baseline, not a 4x jump");
                Assert.Equal(Float2.Zero, swapped.Pan, "new pair: no pan jump");
                var next = g.Update(new[] { T(1, 200, 100), T(2, 600, 600) }, 3 * Dt);
                Assert.True(next.Zoom > 1f, "pinch continues with the new pair");
            });

            TestHarness.Add("Fingers on the same spot never produce NaN or infinite zoom", _ =>
            {
                var g = New160();
                g.Update(new[] { T(0, 100, 100), T(1, 100, 100) }, 0.0);
                var apart = g.Update(new[] { T(0, 90, 100), T(1, 110, 100) }, Dt);
                var together = g.Update(new[] { T(0, 100, 100), T(1, 100, 100) }, 2 * Dt);
                foreach (var z in new[] { apart.Zoom, together.Zoom })
                {
                    Assert.True(!float.IsNaN(z) && !float.IsInfinity(z) && z > 0f, $"zoom {z} is finite and positive");
                }
            });

            TestHarness.Add("Cancel ends the gesture; fingers still down are ignored until they lift", _ =>
            {
                var g = New160();
                g.Update(new[] { T(0, 100, 100) }, 0.0);
                g.Update(new[] { T(0, 160, 100) }, Dt);
                g.Cancel();

                var held = g.Update(new[] { T(0, 200, 100) }, 2 * Dt);
                Assert.Equal(Float2.Zero, held.Pan, "held finger ignored after cancel");
                Assert.True(!held.IsDragging, "not dragging");
                Assert.True(!g.Update(new TouchSample[0], 3 * Dt).Tapped, "no tap from the canceled finger");

                g.Update(new[] { T(0, 50, 50) }, 1.0);
                Assert.True(g.Update(new TouchSample[0], 1.1).Tapped, "same finger id works normally after lifting");
            });

            TestHarness.Add("Cancel during a press suppresses the tap", _ =>
            {
                var g = New160();
                g.Update(new[] { T(0, 100, 100) }, 0.0);
                g.Cancel();
                Assert.True(!g.Update(new TouchSample[0], 0.1).Tapped, "no tap");
            });

            TestHarness.Add("One finger lifting as another lands in the same frame gives two taps", _ =>
            {
                var g = New160();
                g.Update(new[] { T(0, 100, 100) }, 0.0);
                var swap = g.Update(new[] { T(1, 500, 500) }, 0.1);
                Assert.True(swap.Tapped, "first finger's tap");
                Assert.Equal(new Float2(100, 100), swap.TapPosition, "first tap position");
                var up = g.Update(new TouchSample[0], 0.2);
                Assert.True(up.Tapped, "second finger's tap");
                Assert.Equal(new Float2(500, 500), up.TapPosition, "second tap position");
            });

            TestHarness.Add("Duplicate ids and a null touch list are handled", _ =>
            {
                var g = New160();
                var f = g.Update(new[] { T(0, 100, 100), T(0, 900, 900) }, 0.0);
                Assert.True(!f.IsPinching, "duplicate id is not a second finger");
                Assert.True(g.Update(null, 0.1).Tapped, "null list means no fingers (tap ends)");
            });
        }
    }
}
