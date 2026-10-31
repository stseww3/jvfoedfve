using UnityMobileKit.Geometry;

namespace UnityMobileKit.Input
{
    /// <summary>One finger that is currently down, in screen pixels (origin bottom-left, as in Unity).</summary>
    public readonly struct TouchSample
    {
        public TouchSample(int id, Float2 position)
        {
            Id = id;
            Position = position;
        }

        public TouchSample(int id, float x, float y) : this(id, new Float2(x, y))
        {
        }

        /// <summary>Stable for as long as the finger stays down (Unity's <c>fingerId</c> / touch id).</summary>
        public int Id { get; }

        public Float2 Position { get; }
    }
}
