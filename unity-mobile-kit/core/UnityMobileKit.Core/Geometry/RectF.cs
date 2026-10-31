using System;
using System.Globalization;

namespace UnityMobileKit.Geometry
{
    /// <summary>Axis-aligned rectangle (x, y is the bottom-left corner), e.g. Unity's <c>Screen.safeArea</c>.</summary>
    public readonly struct RectF : IEquatable<RectF>
    {
        public RectF(float x, float y, float width, float height)
        {
            X = x;
            Y = y;
            Width = width;
            Height = height;
        }

        public static RectF FromMinMax(Float2 min, Float2 max) => new RectF(min.X, min.Y, max.X - min.X, max.Y - min.Y);

        public float X { get; }

        public float Y { get; }

        public float Width { get; }

        public float Height { get; }

        public Float2 Min => new Float2(X, Y);

        public Float2 Max => new Float2(X + Width, Y + Height);

        public Float2 Center => new Float2(X + Width * 0.5f, Y + Height * 0.5f);

        /// <summary>True for zero, negative or NaN sizes.</summary>
        public bool IsEmpty => !(Width > 0f) || !(Height > 0f);

        public bool Equals(RectF other) => X == other.X && Y == other.Y && Width == other.Width && Height == other.Height;

        public override bool Equals(object obj) => obj is RectF other && Equals(other);

        public override int GetHashCode()
        {
            unchecked
            {
                int hash = X.GetHashCode();
                hash = (hash * 397) ^ Y.GetHashCode();
                hash = (hash * 397) ^ Width.GetHashCode();
                return (hash * 397) ^ Height.GetHashCode();
            }
        }

        public override string ToString() => string.Format(CultureInfo.InvariantCulture, "(x {0}, y {1}, w {2}, h {3})", X, Y, Width, Height);
    }
}
