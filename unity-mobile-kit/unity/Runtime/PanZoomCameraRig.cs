// NOT RUNTIME-TESTED. Written for Unity 2021.3 LTS or newer but never run in Unity or on a device.
// It is only compile-checked against hand-written stand-ins for the UnityEngine API
// (tests/UnityApiStubs). The camera, auto-zoom and controller-camera math it calls into (core/)
// is unit-tested with dotnet.

using System.Collections.Generic;
using UnityEngine;
using UnityMobileKit.CameraControl;
using UnityMobileKit.Controllers;
using UnityMobileKit.Geometry;
using UnityMobileKit.Gestures;

namespace UnityMobileKit.Runtime
{
    public enum CameraPlane
    {
        /// <summary>2D: the camera has no rotation and looks along +Z.</summary>
        XY,
        /// <summary>Top-down 3D: the camera looks straight down (rotation 90, 0, 0), so screen up is +Z.</summary>
        XZ,
    }

    /// <summary>
    /// Orthographic pan / pinch-zoom camera. One finger drags the map; two fingers pan and zoom
    /// around their midpoint; the right stick pans and the triggers zoom (right in, left out) around
    /// the virtual cursor. Auto-zoom keeps <see cref="SetFocusPoints"/> in view while the player's
    /// auto-zoom setting is on, and pauses for a few seconds after manual camera input.
    /// Assumes the camera renders to the whole screen.
    /// </summary>
    [RequireComponent(typeof(Camera))]
    [DisallowMultipleComponent]
    public sealed class PanZoomCameraRig : MonoBehaviour
    {
        [SerializeField] private MobileInput input = null;

        [SerializeField] private CameraPlane plane = CameraPlane.XY;

        [Tooltip("Closest zoom, as the orthographic half-height in world units.")]
        [SerializeField, Min(0.01f)] private float minSize = 3f;

        [Tooltip("Widest zoom, as the orthographic half-height in world units.")]
        [SerializeField, Min(0.01f)] private float maxSize = 20f;

        [SerializeField] private bool limitToBounds = false;

        [Tooltip("World rectangle the view stays inside, on the camera plane (x and y, or x and z).")]
        [SerializeField] private Vector2 boundsMin = new Vector2(-50f, -50f);

        [SerializeField] private Vector2 boundsMax = new Vector2(50f, 50f);

        [Tooltip("Whether auto-zoom runs when there is no MobileKitServices. With it, the player's auto-zoom setting decides.")]
        [SerializeField] private bool autoZoomWithoutServices = true;

        private readonly List<Float2> _focusPoints = new List<Float2>();
        private readonly GamepadCamera _gamepadCamera = new GamepadCamera();
        private Camera _camera;
        private bool _warnedNoInput;

        public ZoomPanCamera View { get; private set; }

        public AutoZoom AutoZoom { get; private set; }

        private void Awake()
        {
            _camera = GetComponent<Camera>();
            _camera.orthographic = true;
            View = new ZoomPanCamera(Mathf.Min(minSize, maxSize), Mathf.Max(minSize, maxSize),
                                     Mathf.Max(1, _camera.pixelWidth), Mathf.Max(1, _camera.pixelHeight));
            if (limitToBounds)
            {
                View.SetBounds(Vector2.Min(boundsMin, boundsMax).ToFloat2(), Vector2.Max(boundsMin, boundsMax).ToFloat2());
            }
            View.SetSize(_camera.orthographicSize);
            View.SetCenter(ToPlane(transform.position));
            AutoZoom = new AutoZoom(View);
        }

        /// <summary>
        /// World positions auto-zoom should keep in view, such as the player's units. Replaces the
        /// previous set; with an empty set auto-zoom leaves the camera alone.
        /// </summary>
        public void SetFocusPoints(IReadOnlyList<Vector3> worldPoints)
        {
            _focusPoints.Clear();
            if (worldPoints == null) return;
            for (int i = 0; i < worldPoints.Count; i++) _focusPoints.Add(ToPlane(worldPoints[i]));
        }

        /// <summary>Screen pixel (origin bottom-left) to a point on the camera plane: (x, y) or (x, z).</summary>
        public Vector2 ScreenToPlane(Vector2 screen) => View.ScreenToWorld(screen.ToFloat2()).ToVector2();

        private void LateUpdate()
        {
            double now = Time.unscaledTimeAsDouble;
            float deltaTime = Time.unscaledDeltaTime;
            int width = _camera.pixelWidth;
            int height = _camera.pixelHeight;
            if (width > 0 && height > 0 && (width != View.ViewportWidth || height != View.ViewportHeight))
            {
                View.SetViewport(width, height);
            }

            if (input != null)
            {
                GestureFrame gestures = input.Gestures;
                View.Apply(gestures);
                AutoZoom.Observe(gestures, now);

                GamepadState pad = input.Pad;
                Float2 zoomFocus = input.Mode.Mode == InputMode.Gamepad
                    ? input.VirtualCursor.Position
                    : new Float2(View.ViewportWidth * 0.5f, View.ViewportHeight * 0.5f);
                if (_gamepadCamera.Update(View, pad.RightStick, pad.RightTrigger - pad.LeftTrigger, zoomFocus, deltaTime))
                {
                    AutoZoom.NotifyUserInput(now);
                }
            }
            else if (!_warnedNoInput)
            {
                Debug.LogWarning("[UnityMobileKit] PanZoomCameraRig has no MobileInput assigned; only auto-zoom will move the camera.", this);
                _warnedNoInput = true;
            }

            MobileKitServices services = MobileKitServices.Instance;
            AutoZoom.Enabled = services != null && services.Settings != null ? services.Settings.TouchAutoZoom : autoZoomWithoutServices;
            AutoZoom.Update(_focusPoints, now, deltaTime);

            _camera.orthographicSize = View.Size;
            Vector3 position = transform.position;
            transform.position = FromPlane(View.Center, plane == CameraPlane.XY ? position.z : position.y);
        }

        private Float2 ToPlane(Vector3 world) => plane == CameraPlane.XY ? new Float2(world.x, world.y) : new Float2(world.x, world.z);

        private Vector3 FromPlane(Float2 point, float depth) =>
            plane == CameraPlane.XY ? new Vector3(point.X, point.Y, depth) : new Vector3(point.X, depth, point.Y);
    }
}
