// Compile-only stand-ins for the parts of the UnityEngine API that unity/Runtime uses, written by
// hand from Unity's public Scripting Reference so the adapters can be compile-checked without a
// Unity install. They contain no Unity code, do nothing at runtime and are never shipped: inside
// Unity the real engine assemblies are used instead. Passing the check means the adapters are valid
// C# against these signatures, not that they behave correctly in Unity.

using System;

namespace UnityEngine
{
    public class Object
    {
        public string name { get; set; }

        public static void Destroy(Object obj) { }

        public static void DontDestroyOnLoad(Object target) { }
    }

    public class Component : Object
    {
        public Transform transform => null;

        public GameObject gameObject => null;

        public T GetComponent<T>() => default;
    }

    public class Behaviour : Component
    {
        public bool enabled { get; set; }
    }

    public class MonoBehaviour : Behaviour { }

    public class ScriptableObject : Object { }

    public sealed class GameObject : Object
    {
        public Transform transform => null;
    }

    public class Transform : Component
    {
        public Vector3 position { get; set; }

        public void SetParent(Transform parent) { }
    }

    public sealed class RectTransform : Transform
    {
        public Vector2 anchorMin { get; set; }

        public Vector2 anchorMax { get; set; }

        public Vector2 offsetMin { get; set; }

        public Vector2 offsetMax { get; set; }
    }

    public sealed class Camera : Behaviour
    {
        public bool orthographic { get; set; }

        public float orthographicSize { get; set; }

        public int pixelWidth => 0;

        public int pixelHeight => 0;
    }

    public struct Vector2
    {
        public float x;
        public float y;

        public Vector2(float x, float y)
        {
            this.x = x;
            this.y = y;
        }

        public static Vector2 zero => new Vector2(0f, 0f);

        public static Vector2 Min(Vector2 lhs, Vector2 rhs) => new Vector2(Math.Min(lhs.x, rhs.x), Math.Min(lhs.y, rhs.y));

        public static Vector2 Max(Vector2 lhs, Vector2 rhs) => new Vector2(Math.Max(lhs.x, rhs.x), Math.Max(lhs.y, rhs.y));
    }

    public struct Vector3
    {
        public float x;
        public float y;
        public float z;

        public Vector3(float x, float y, float z)
        {
            this.x = x;
            this.y = y;
            this.z = z;
        }
    }

    public struct Rect : IEquatable<Rect>
    {
        public Rect(float x, float y, float width, float height)
        {
            this.x = x;
            this.y = y;
            this.width = width;
            this.height = height;
        }

        public float x { get; set; }

        public float y { get; set; }

        public float width { get; set; }

        public float height { get; set; }

        public static bool operator ==(Rect lhs, Rect rhs) => lhs.Equals(rhs);

        public static bool operator !=(Rect lhs, Rect rhs) => !lhs.Equals(rhs);

        public bool Equals(Rect other) => x == other.x && y == other.y && width == other.width && height == other.height;

        public override bool Equals(object other) => other is Rect rect && Equals(rect);

        public override int GetHashCode() => x.GetHashCode() ^ y.GetHashCode() ^ width.GetHashCode() ^ height.GetHashCode();
    }

#if UNITY_2022_2_OR_NEWER
    public struct RefreshRate
    {
        public uint numerator;
        public uint denominator;

        public double value => (double)numerator / denominator;
    }
#endif

    public struct Resolution
    {
        public int width { get; set; }

        public int height { get; set; }

#if UNITY_2022_2_OR_NEWER
        [Obsolete("Resolution.refreshRate is obsolete. Use refreshRateRatio instead.", false)]
#endif
        public int refreshRate { get; set; }

#if UNITY_2022_2_OR_NEWER
        public RefreshRate refreshRateRatio { get; set; }
#endif
    }

    public enum ScreenOrientation
    {
        Portrait = 1,
        PortraitUpsideDown = 2,
        LandscapeLeft = 3,
        LandscapeRight = 4,
        AutoRotation = 5,
    }

    public sealed class Screen
    {
        public static int width => 0;

        public static int height => 0;

        public static float dpi => 0f;

        public static Rect safeArea => default;

        public static Resolution currentResolution => default;

        public static Resolution[] resolutions => Array.Empty<Resolution>();

        public static ScreenOrientation orientation { get; set; }

        public static bool autorotateToPortrait { get; set; }

        public static bool autorotateToPortraitUpsideDown { get; set; }

        public static bool autorotateToLandscapeLeft { get; set; }

        public static bool autorotateToLandscapeRight { get; set; }
    }

    public sealed class Application
    {
        public static string persistentDataPath => "";

        public static int targetFrameRate { get; set; }
    }

    public sealed class Time
    {
        public static float unscaledDeltaTime => 0f;

        public static double unscaledTimeAsDouble => 0.0;

        public static double realtimeSinceStartupAsDouble => 0.0;
    }

    public enum BatteryStatus
    {
        Unknown = 0,
        Charging = 1,
        Discharging = 2,
        NotCharging = 3,
        Full = 4,
    }

    public sealed class SystemInfo
    {
        public static float batteryLevel => -1f;

        public static BatteryStatus batteryStatus => BatteryStatus.Unknown;
    }

    public enum TouchPhase
    {
        Began = 0,
        Moved = 1,
        Stationary = 2,
        Ended = 3,
        Canceled = 4,
    }

    public struct Touch
    {
        public int fingerId { get; set; }

        public Vector2 position { get; set; }

        public TouchPhase phase { get; set; }
    }

    public sealed class Input
    {
        public static int touchCount => 0;

        public static Touch GetTouch(int index) => default;
    }

    public struct Mathf
    {
        public static int Max(int a, int b) => Math.Max(a, b);

        public static float Max(float a, float b) => Math.Max(a, b);

        public static float Min(float a, float b) => Math.Min(a, b);
    }

    public sealed class Debug
    {
        public static void LogWarning(object message) { }

        public static void LogWarning(object message, Object context) { }

        public static void LogError(object message) { }
    }

    [AttributeUsage(AttributeTargets.Field)]
    public sealed class SerializeField : Attribute { }

    [AttributeUsage(AttributeTargets.Field)]
    public sealed class TooltipAttribute : Attribute
    {
        public TooltipAttribute(string tooltip) { }
    }

    [AttributeUsage(AttributeTargets.Field)]
    public sealed class RangeAttribute : Attribute
    {
        public RangeAttribute(float min, float max) { }
    }

    [AttributeUsage(AttributeTargets.Field)]
    public sealed class MinAttribute : Attribute
    {
        public MinAttribute(float min) { }
    }

    [AttributeUsage(AttributeTargets.Field)]
    public sealed class TextAreaAttribute : Attribute { }

    [AttributeUsage(AttributeTargets.Class, AllowMultiple = true)]
    public sealed class RequireComponent : Attribute
    {
        public RequireComponent(Type requiredComponent) { }
    }

    [AttributeUsage(AttributeTargets.Class)]
    public sealed class DisallowMultipleComponent : Attribute { }

    [AttributeUsage(AttributeTargets.Class)]
    public sealed class DefaultExecutionOrder : Attribute
    {
        public DefaultExecutionOrder(int order) { }
    }

    [AttributeUsage(AttributeTargets.Class)]
    public sealed class CreateAssetMenuAttribute : Attribute
    {
        public string fileName { get; set; }

        public string menuName { get; set; }

        public int order { get; set; }
    }

    public class AndroidJavaObject : IDisposable
    {
        public AndroidJavaObject(string className, params object[] args) { }

        public T Call<T>(string methodName, params object[] args) => default;

        public T GetStatic<T>(string fieldName) => default;

        public void Dispose() { }
    }

    public class AndroidJavaClass : AndroidJavaObject
    {
        public AndroidJavaClass(string className) : base(className) { }
    }

    public sealed class AndroidJavaException : Exception
    {
        public AndroidJavaException(string message) : base(message) { }
    }
}

namespace UnityEngine.Events
{
    public delegate void UnityAction();

    public abstract class UnityEventBase { }

    [Serializable]
    public class UnityEvent : UnityEventBase
    {
        public void Invoke() { }

        public void AddListener(UnityAction call) { }

        public void RemoveListener(UnityAction call) { }
    }
}
