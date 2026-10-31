// NOT RUNTIME-TESTED. Written for Unity 2021.3 LTS or newer but never run in Unity or on a device.
// It is only compile-checked against hand-written stand-ins for the UnityEngine API
// (tests/UnityApiStubs).

using UnityEngine;
using UnityMobileKit.Geometry;

namespace UnityMobileKit.Runtime
{
    internal static class Conversions
    {
        public static Float2 ToFloat2(this Vector2 value) => new Float2(value.x, value.y);

        public static Vector2 ToVector2(this Float2 value) => new Vector2(value.X, value.Y);
    }
}
