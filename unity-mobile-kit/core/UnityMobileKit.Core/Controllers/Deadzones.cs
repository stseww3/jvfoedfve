using System;
using UnityMobileKit.Geometry;

namespace UnityMobileKit.Controllers
{
    /// <summary>
    /// Radial stick deadzone. Readings inside <see cref="Inner"/> are zero (worn sticks rarely rest
    /// at exactly 0); the rest of the range is rescaled so output starts at 0 just past the deadzone
    /// (no jump) and reaches full magnitude at <see cref="Outer"/> (many sticks never report 1.0).
    /// Direction is preserved, and square-gate diagonals above 1 are capped at 1.
    /// <para>Feed unprocessed values: if the input layer already applies a deadzone, they stack.</para>
    /// </summary>
    public sealed class StickDeadzone
    {
        public StickDeadzone(float inner = 0.15f, float outer = 0.95f, float exponent = 1f)
        {
            if (!(inner >= 0f) || !(outer > inner) || !(outer <= 1f))
            {
                throw new ArgumentOutOfRangeException(nameof(inner), "Requires 0 <= inner < outer <= 1.");
            }
            if (!(exponent > 0f) || float.IsInfinity(exponent))
            {
                throw new ArgumentOutOfRangeException(nameof(exponent), "Must be a positive number.");
            }
            Inner = inner;
            Outer = outer;
            Exponent = exponent;
        }

        public float Inner { get; }

        public float Outer { get; }

        /// <summary>Response curve: 1 is linear; above 1 gives finer control near the center.</summary>
        public float Exponent { get; }

        public Float2 Apply(Float2 raw)
        {
            float magnitude = raw.Length;
            if (!(magnitude > Inner) || float.IsInfinity(magnitude)) return Float2.Zero;

            float t = Math.Min(1f, (magnitude - Inner) / (Outer - Inner));
            if (Exponent != 1f) t = (float)Math.Pow(t, Exponent);
            return raw * (t / magnitude);
        }
    }

    /// <summary>The one-dimensional version, for triggers (0..1).</summary>
    public sealed class AxisDeadzone
    {
        public AxisDeadzone(float inner = 0.1f, float outer = 0.95f)
        {
            if (!(inner >= 0f) || !(outer > inner) || !(outer <= 1f))
            {
                throw new ArgumentOutOfRangeException(nameof(inner), "Requires 0 <= inner < outer <= 1.");
            }
            Inner = inner;
            Outer = outer;
        }

        public float Inner { get; }

        public float Outer { get; }

        public float Apply(float raw)
        {
            if (!(raw > Inner)) return 0f;
            return Math.Min(1f, (raw - Inner) / (Outer - Inner));
        }
    }
}
