using System;
using System.Globalization;

namespace UnityMobileKit.Geometry
{
    /// <summary>
    /// A minimal 2D float vector so the pure-C# core (gestures, camera math) has no dependency on
    /// <c>UnityEngine.Vector2</c>. The Unity layer converts to and from <c>Vector2</c> at the edges.
    /// </summary>
    public readonly struct Float2 : IEquatable<Float2>
    {
        public Float2(float x, float y)
        {
            X = x;
            Y = y;
        }

        public float X { get; }

        public float Y { get; }

        public static Float2 Zero => new Float2(0f, 0f);

        public float Length => (float)Math.Sqrt((double)X * X + (double)Y * Y);

        public static Float2 operator +(Float2 a, Float2 b) => new Float2(a.X + b.X, a.Y + b.Y);

        public static Float2 operator -(Float2 a, Float2 b) => new Float2(a.X - b.X, a.Y - b.Y);

        public static Float2 operator *(Float2 a, float s) => new Float2(a.X * s, a.Y * s);

        public static Float2 operator *(float s, Float2 a) => a * s;

        public static Float2 operator /(Float2 a, float s) => new Float2(a.X / s, a.Y / s);

        public static bool operator ==(Float2 a, Float2 b) => a.Equals(b);

        public static bool operator !=(Float2 a, Float2 b) => !a.Equals(b);

        public static float Distance(Float2 a, Float2 b) => (a - b).Length;

        public static Float2 Midpoint(Float2 a, Float2 b) => new Float2((a.X + b.X) * 0.5f, (a.Y + b.Y) * 0.5f);

        /// <summary>Component-wise clamp to the inclusive box [min, max].</summary>
        public static Float2 Clamp(Float2 value, Float2 min, Float2 max)
        {
            return new Float2(
                Math.Min(Math.Max(value.X, min.X), max.X),
                Math.Min(Math.Max(value.Y, min.Y), max.Y));
        }

        public bool Equals(Float2 other) => X == other.X && Y == other.Y;

        public override bool Equals(object obj) => obj is Float2 other && Equals(other);

        public override int GetHashCode()
        {
            unchecked
            {
                return (X.GetHashCode() * 397) ^ Y.GetHashCode();
            }
        }

        public override string ToString() => string.Format(CultureInfo.InvariantCulture, "({0}, {1})", X, Y);
    }
}
