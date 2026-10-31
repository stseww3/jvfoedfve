using System;
using System.Collections.Generic;
using UnityMobileKit.Geometry;

namespace UnityMobileKit.Input
{
    /// <summary>
    /// Turns the set of fingers that are down each frame into tap, one-finger drag and two-finger
    /// pinch/pan gestures. Call <see cref="Update"/> once per frame with only the touches that are
    /// still down (leave out ended and canceled ones); a finger counts as lifted when its id is no
    /// longer present. Not thread-safe.
    /// </summary>
    public sealed class GestureRecognizer
    {
        /// <summary>Used when the platform reports an unknown screen density (Unity's <c>Screen.dpi</c> can be 0).</summary>
        public const float FallbackDpi = 320f;

        // Two touch points closer than this give a meaningless scale ratio, so such frames don't zoom.
        private const float MinPinchDistance = 1f;

        private enum Mode
        {
            Idle,
            Pending,   // one finger down, still within the tap slop
            Dragging,  // one finger moved past the slop
            Pinching,  // two or more fingers
        }

        private readonly List<TouchSample> _current = new List<TouchSample>();
        private readonly HashSet<int> _currentIds = new HashSet<int>();
        private readonly HashSet<int> _ignored = new HashSet<int>();
        private readonly List<int> _ignoredGone = new List<int>();
        private readonly float _pixelsPerDp;

        private Mode _mode;
        private int _primaryId;
        private Float2 _primaryStart;
        private Float2 _lastReported;
        private double _primaryStartTime;
        private bool _tapAllowed;
        private int _pinchA;
        private int _pinchB;
        private float _pinchDistance;
        private Float2 _pinchMidpoint;

        /// <param name="dpi">Screen density in dots per inch; 0 or less means unknown (see <see cref="FallbackDpi"/>).</param>
        public GestureRecognizer(float dpi)
        {
            float usable = dpi > 0f && !float.IsInfinity(dpi) ? dpi : FallbackDpi;
            _pixelsPerDp = usable / 160f;
        }

        /// <summary>How far (in dp, 1/160 inch) a finger may wander and still count as a tap.</summary>
        public float TapSlopDp { get; set; } = 10f;

        /// <summary>Longest press that still counts as a tap.</summary>
        public double TapMaxSeconds { get; set; } = 0.3;

        public float TapSlopPixels => TapSlopDp * _pixelsPerDp;

        /// <param name="touches">Fingers currently down. Duplicate ids are ignored after the first.</param>
        /// <param name="time">Monotonic time in seconds (e.g. <c>Time.unscaledTimeAsDouble</c>).</param>
        public GestureFrame Update(IReadOnlyList<TouchSample> touches, double time)
        {
            CollectTouches(touches);

            Float2 pan = Float2.Zero;
            float zoom = 1f;
            Float2 focus = Float2.Zero;
            bool tapped = false;
            Float2 tapPosition = Float2.Zero;

            if (_current.Count >= 2)
            {
                SelectPinchPair(out TouchSample a, out TouchSample b);
                float distance = Float2.Distance(a.Position, b.Position);
                Float2 midpoint = Float2.Midpoint(a.Position, b.Position);

                // Same pair as last frame: report the change. A new pair (pinch start, or a finger of
                // the pair swapped) only sets the baseline, so the camera never jumps.
                if (_mode == Mode.Pinching && a.Id == _pinchA && b.Id == _pinchB)
                {
                    if (distance >= MinPinchDistance && _pinchDistance >= MinPinchDistance)
                    {
                        zoom = distance / _pinchDistance;
                    }
                    pan = midpoint - _pinchMidpoint;
                }

                _mode = Mode.Pinching;
                _pinchA = a.Id;
                _pinchB = b.Id;
                _pinchDistance = distance;
                _pinchMidpoint = midpoint;
                focus = midpoint;
            }
            else if (_current.Count == 1)
            {
                TouchSample touch = _current[0];
                bool sameFinger = (_mode == Mode.Pending || _mode == Mode.Dragging) && touch.Id == _primaryId;

                if (!sameFinger)
                {
                    // The previous finger lifted in the same frame another one landed.
                    if (_mode == Mode.Pending && IsTap(time))
                    {
                        tapped = true;
                        tapPosition = _primaryStart;
                    }
                    // A finger left over from a pinch may still drag but must never fire a tap.
                    StartPrimary(touch, time, tapAllowed: _mode != Mode.Pinching);
                }
                else if (_mode == Mode.Pending)
                {
                    if (Float2.Distance(touch.Position, _primaryStart) > TapSlopPixels)
                    {
                        _mode = Mode.Dragging;
                        _tapAllowed = false;
                        pan = touch.Position - _lastReported;
                        _lastReported = touch.Position;
                    }
                }
                else
                {
                    pan = touch.Position - _lastReported;
                    _lastReported = touch.Position;
                }
            }
            else
            {
                if (_mode == Mode.Pending && IsTap(time))
                {
                    tapped = true;
                    tapPosition = _primaryStart;
                }
                _mode = Mode.Idle;
            }

            return new GestureFrame(pan, zoom, focus, _mode == Mode.Dragging, _mode == Mode.Pinching, tapped, tapPosition);
        }

        /// <summary>
        /// Abandons the current gesture without a tap, e.g. when the app loses focus or the platform
        /// reports a canceled touch. Fingers that are still down are ignored until they lift.
        /// </summary>
        public void Cancel()
        {
            foreach (var touch in _current) _ignored.Add(touch.Id);
            _current.Clear();
            _mode = Mode.Idle;
        }

        private bool IsTap(double time) => _tapAllowed && time - _primaryStartTime <= TapMaxSeconds;

        private void StartPrimary(TouchSample touch, double time, bool tapAllowed)
        {
            _mode = Mode.Pending;
            _primaryId = touch.Id;
            _primaryStart = touch.Position;
            _lastReported = touch.Position;
            _primaryStartTime = time;
            _tapAllowed = tapAllowed;
        }

        private void CollectTouches(IReadOnlyList<TouchSample> touches)
        {
            _current.Clear();
            _currentIds.Clear();
            if (touches != null)
            {
                for (int i = 0; i < touches.Count; i++)
                {
                    TouchSample touch = touches[i];
                    if (!_currentIds.Add(touch.Id)) continue;
                    if (!_ignored.Contains(touch.Id)) _current.Add(touch);
                }
            }

            _ignoredGone.Clear();
            foreach (int id in _ignored)
            {
                if (!_currentIds.Contains(id)) _ignoredGone.Add(id);
            }
            foreach (int id in _ignoredGone) _ignored.Remove(id);
        }

        // The two lowest ids, so the pair is stable no matter what order the platform lists touches in.
        private void SelectPinchPair(out TouchSample a, out TouchSample b)
        {
            int first = -1;
            int second = -1;
            for (int i = 0; i < _current.Count; i++)
            {
                int id = _current[i].Id;
                if (first < 0 || id < _current[first].Id)
                {
                    second = first;
                    first = i;
                }
                else if (second < 0 || id < _current[second].Id)
                {
                    second = i;
                }
            }
            a = _current[first];
            b = _current[second];
        }
    }
}
