using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem.EnhancedTouch;
using Touch = UnityEngine.InputSystem.EnhancedTouch.Touch;
using TouchPhase = UnityEngine.InputSystem.TouchPhase;

/// <summary>
/// Turns raw touches into the gestures a road-drawing game needs: tap, long press, one-finger drag
/// (draw), and two-finger pinch + pan (camera). Touches that start on UI are left to the EventSystem.
///
/// Rules that keep it from placing roads by accident:
/// - a press only becomes a drag after the finger travels <see cref="dragThresholdDp"/>;
/// - a second finger ends the current drag (reported as cancelled) and switches to pinch;
/// - after a pinch, the remaining finger is ignored until every finger has lifted.
/// </summary>
public class TouchGestures : MonoBehaviour
{
    [Tooltip("How far a finger must move, in dp, before a press turns into a drag.")]
    [SerializeField] float dragThresholdDp = 8f;
    [Tooltip("How long a finger must stay still to count as a long press.")]
    [SerializeField] float longPressSeconds = 0.45f;

    public event Action<Vector2> Tapped;
    public event Action<Vector2> LongPressed;
    /// <summary>Where the drag began, and whether it began with a long press (handy as an "erase" gesture).</summary>
    public event Action<Vector2, bool> DragStarted;
    public event Action<Vector2> Dragged;
    /// <summary>Last finger position, and true if the drag was cut short (second finger, or the OS cancelled the touch).</summary>
    public event Action<Vector2, bool> DragEnded;
    /// <summary>Zoom factor since last frame (above 1 means the fingers moved apart) and the midpoint between the fingers.</summary>
    public event Action<float, Vector2> Pinched;
    /// <summary>How far the midpoint between the two fingers moved since last frame, in pixels.</summary>
    public event Action<Vector2> TwoFingerPanned;

    public bool IsDragging => state == State.Dragging;
    public bool IsPinching => state == State.Pinching;
    public Vector2 PointerPosition => lastPosition;

    enum State { Idle, Pressing, Dragging, Pinching, WaitingForRelease }

    static readonly Comparison<Touch> ByTouchId = (a, b) => a.touchId.CompareTo(b.touchId);

    readonly List<Touch> down = new List<Touch>();
    readonly List<RaycastResult> uiHits = new List<RaycastResult>();

    State state;
    int fingerId = -1;
    Vector2 pressPosition;
    Vector2 lastPosition;
    float pressTime;
    bool longPressFired;
    bool releasedCleanly;
    Vector2 releasePosition;
    int pinchIdA = -1;
    int pinchIdB = -1;
    float lastPinchDistance;
    Vector2 lastPinchCenter;

    float DragThresholdPixels => dragThresholdDp * (Screen.dpi > 0f ? Screen.dpi : 160f) / 160f;

    void OnEnable()
    {
        EnhancedTouchSupport.Enable();
    }

    void OnDisable()
    {
        if (state == State.Dragging)
            DragEnded?.Invoke(lastPosition, true);
        state = State.Idle;
        fingerId = -1;
        EnhancedTouchSupport.Disable();
    }

    void Update()
    {
        CollectTouches();

        switch (state)
        {
            case State.Idle:
                if (down.Count == 0)
                    break;
                if (IsOverUI(down[0].screenPosition))
                    state = State.WaitingForRelease;
                else if (down.Count >= 2)
                    BeginPinch();
                else
                    BeginPress(down[0]);
                break;

            case State.Pressing:
                if (down.Count >= 2)
                {
                    BeginPinch();
                    break;
                }
                if (TryGetDown(fingerId, out Touch pressing))
                {
                    lastPosition = pressing.screenPosition;
                    float threshold = DragThresholdPixels;
                    if ((lastPosition - pressPosition).sqrMagnitude > threshold * threshold)
                    {
                        state = State.Dragging;
                        DragStarted?.Invoke(pressPosition, longPressFired);
                        Dragged?.Invoke(lastPosition);
                    }
                    else if (!longPressFired && Time.unscaledTime - pressTime >= longPressSeconds)
                    {
                        longPressFired = true;
                        LongPressed?.Invoke(pressPosition);
                    }
                }
                else
                {
                    if (releasedCleanly && !longPressFired)
                        Tapped?.Invoke(releasePosition);
                    FinishGesture();
                }
                break;

            case State.Dragging:
                if (down.Count >= 2)
                {
                    DragEnded?.Invoke(lastPosition, true);
                    BeginPinch();
                    break;
                }
                if (TryGetDown(fingerId, out Touch dragging))
                {
                    if (dragging.screenPosition != lastPosition)
                    {
                        lastPosition = dragging.screenPosition;
                        Dragged?.Invoke(lastPosition);
                    }
                }
                else
                {
                    if (releasedCleanly)
                        lastPosition = releasePosition;
                    DragEnded?.Invoke(lastPosition, !releasedCleanly);
                    FinishGesture();
                }
                break;

            case State.Pinching:
                if (down.Count < 2)
                    FinishGesture();
                else
                    UpdatePinch();
                break;

            case State.WaitingForRelease:
                if (down.Count == 0)
                    state = State.Idle;
                break;
        }
    }

    void CollectTouches()
    {
        down.Clear();
        releasedCleanly = false;
        var touches = Touch.activeTouches;
        for (int i = 0; i < touches.Count; i++)
        {
            Touch touch = touches[i];
            TouchPhase phase = touch.phase;
            if (phase == TouchPhase.Ended || phase == TouchPhase.Canceled)
            {
                if (touch.touchId == fingerId && phase == TouchPhase.Ended)
                {
                    releasedCleanly = true;
                    releasePosition = touch.screenPosition;
                }
            }
            else if (phase != TouchPhase.None)
            {
                down.Add(touch);
            }
        }
        if (down.Count > 1)
            down.Sort(ByTouchId);
    }

    bool TryGetDown(int touchId, out Touch touch)
    {
        for (int i = 0; i < down.Count; i++)
        {
            if (down[i].touchId == touchId)
            {
                touch = down[i];
                return true;
            }
        }
        touch = default;
        return false;
    }

    void BeginPress(Touch touch)
    {
        state = State.Pressing;
        fingerId = touch.touchId;
        pressPosition = touch.screenPosition;
        lastPosition = pressPosition;
        pressTime = Time.unscaledTime;
        longPressFired = false;
    }

    void BeginPinch()
    {
        state = State.Pinching;
        fingerId = -1;
        pinchIdA = down[0].touchId;
        pinchIdB = down[1].touchId;
        lastPinchDistance = Vector2.Distance(down[0].screenPosition, down[1].screenPosition);
        lastPinchCenter = (down[0].screenPosition + down[1].screenPosition) * 0.5f;
    }

    void UpdatePinch()
    {
        Touch a = down[0];
        Touch b = down[1];
        if (a.touchId != pinchIdA || b.touchId != pinchIdB)
        {
            BeginPinch();
            return;
        }

        float distance = Vector2.Distance(a.screenPosition, b.screenPosition);
        Vector2 center = (a.screenPosition + b.screenPosition) * 0.5f;

        // Pan before zoom: the world point that was under the old midpoint moves to the new midpoint,
        // then zooming around the new midpoint keeps it there.
        if (center != lastPinchCenter)
            TwoFingerPanned?.Invoke(center - lastPinchCenter);
        if (lastPinchDistance > 1f && distance > 1f && !Mathf.Approximately(distance, lastPinchDistance))
            Pinched?.Invoke(distance / lastPinchDistance, center);

        lastPinchDistance = distance;
        lastPinchCenter = center;
    }

    void FinishGesture()
    {
        fingerId = -1;
        state = down.Count > 0 ? State.WaitingForRelease : State.Idle;
    }

    bool IsOverUI(Vector2 screenPosition)
    {
        EventSystem eventSystem = EventSystem.current;
        if (eventSystem == null)
            return false;
        // Every EventSystem raycaster counts, so keep PhysicsRaycaster / Physics2DRaycaster off the
        // gameplay camera or taps on the map will be treated as UI.
        var pointer = new PointerEventData(eventSystem) { position = screenPosition };
        uiHits.Clear();
        eventSystem.RaycastAll(pointer, uiHits);
        return uiHits.Count > 0;
    }
}
