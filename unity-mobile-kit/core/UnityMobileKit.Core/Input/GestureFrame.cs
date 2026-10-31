using UnityMobileKit.Geometry;

namespace UnityMobileKit.Input
{
    /// <summary>What the fingers did during one frame, ready to apply to a camera.</summary>
    public readonly struct GestureFrame
    {
        public GestureFrame(Float2 pan, float zoom, Float2 focus, bool isDragging, bool isPinching, bool tapped, Float2 tapPosition)
        {
            Pan = pan;
            Zoom = zoom;
            Focus = focus;
            IsDragging = isDragging;
            IsPinching = isPinching;
            Tapped = tapped;
            TapPosition = tapPosition;
        }

        public static GestureFrame None => new GestureFrame(Float2.Zero, 1f, Float2.Zero, false, false, false, Float2.Zero);

        /// <summary>Screen pixels the content should move this frame to stay under the finger (or the two fingers' midpoint).</summary>
        public Float2 Pan { get; }

        /// <summary>Pinch scale this frame: above 1 when the fingers spread (zoom in), below 1 when they close, otherwise 1.</summary>
        public float Zoom { get; }

        /// <summary>Midpoint between the pinching fingers in screen pixels; zoom around this point.</summary>
        public Float2 Focus { get; }

        public bool IsDragging { get; }

        public bool IsPinching { get; }

        public bool Tapped { get; }

        /// <summary>Where the tapping finger went down.</summary>
        public Float2 TapPosition { get; }
    }
}
