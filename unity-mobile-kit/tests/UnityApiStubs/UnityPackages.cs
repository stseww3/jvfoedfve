// Compile-only stand-ins for the parts of the uGUI (com.unity.ugui) and Input System
// (com.unity.inputsystem) package APIs that unity/Runtime uses, written by hand from their public
// documentation. Same caveats as UnityEngine.cs: no Unity code, nothing runs, never shipped.

using System.Collections.Generic;

#if UMK_UGUI
namespace UnityEngine.EventSystems
{
    public abstract class UIBehaviour : MonoBehaviour { }

    public abstract class AbstractEventData { }

    public class BaseEventData : AbstractEventData
    {
        public BaseEventData(EventSystem eventSystem) { }
    }

    public class PointerEventData : BaseEventData
    {
        public PointerEventData(EventSystem eventSystem) : base(eventSystem) { }

        public Vector2 position { get; set; }
    }

    public struct RaycastResult { }

    public class EventSystem : UIBehaviour
    {
        public static EventSystem current { get; set; }

        public void RaycastAll(PointerEventData eventData, List<RaycastResult> raycastResults) { }
    }
}
#endif

#if UMK_INPUT_SYSTEM
namespace UnityEngine.InputSystem
{
    using UnityEngine.InputSystem.Controls;

    public enum TouchPhase
    {
        None,
        Began,
        Moved,
        Ended,
        Canceled,
        Stationary,
    }

    public abstract class InputControl { }

    public abstract class InputControl<TValue> : InputControl where TValue : struct
    {
        public TValue ReadValue() => default;
    }

    public class InputDevice : InputControl { }

    public class Gamepad : InputDevice
    {
        public static Gamepad current { get; }

        public ButtonControl buttonSouth { get; protected set; }

        public ButtonControl buttonEast { get; protected set; }

        public ButtonControl buttonWest { get; protected set; }

        public ButtonControl buttonNorth { get; protected set; }

        public ButtonControl leftShoulder { get; protected set; }

        public ButtonControl rightShoulder { get; protected set; }

        public ButtonControl startButton { get; protected set; }

        public ButtonControl selectButton { get; protected set; }

        public ButtonControl leftStickButton { get; protected set; }

        public ButtonControl rightStickButton { get; protected set; }

        public ButtonControl leftTrigger { get; protected set; }

        public ButtonControl rightTrigger { get; protected set; }

        public StickControl leftStick { get; protected set; }

        public StickControl rightStick { get; protected set; }

        public DpadControl dpad { get; protected set; }
    }
}

namespace UnityEngine.InputSystem.Controls
{
    public class AxisControl : InputControl<float> { }

    public class ButtonControl : AxisControl
    {
        public bool isPressed => false;
    }

    public class Vector2Control : InputControl<Vector2> { }

    public class StickControl : Vector2Control { }

    public class DpadControl : Vector2Control
    {
        public ButtonControl up { get; set; }

        public ButtonControl down { get; set; }

        public ButtonControl left { get; set; }

        public ButtonControl right { get; set; }
    }
}

namespace UnityEngine.InputSystem.Utilities
{
    public struct ReadOnlyArray<TValue>
    {
        public int Count => 0;

        public TValue this[int index] => default;
    }
}

namespace UnityEngine.InputSystem.EnhancedTouch
{
    using UnityEngine.InputSystem.Utilities;

    public static class EnhancedTouchSupport
    {
        public static void Enable() { }

        public static void Disable() { }
    }

    public struct Touch
    {
        public static ReadOnlyArray<Touch> activeTouches => default;

        public int touchId => 0;

        public Vector2 screenPosition => default;

        public TouchPhase phase => TouchPhase.None;
    }
}
#endif
