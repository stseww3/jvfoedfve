using System;
using UnityMobileKit.CameraControl;
using UnityMobileKit.Geometry;

namespace UnityMobileKit.Controllers
{
    /// <summary>
    /// Drives a <see cref="ZoomPanCamera"/> from a controller: a stick pans the view, an axis zooms
    /// (for example right trigger minus left trigger). Frame-rate independent.
    /// </summary>
    public sealed class GamepadCamera
    {
        /// <summary>Pan speed at full deflection, in screen heights per second.</summary>
        public float PanSpeed { get; set; } = 0.8f;

        /// <summary>Zoom speed at full axis, in doublings per second (1 halves the view size each second).</summary>
        public float ZoomSpeed { get; set; } = 1.5f;

        /// <param name="panStick">Deadzone-filtered stick; pushing right reveals more of the world to the right.</param>
        /// <param name="zoomAxis">-1..1, positive zooms in.</param>
        /// <param name="zoomFocus">Screen point to zoom around, e.g. the screen center or the virtual cursor.</param>
        /// <returns>True if the camera was moved, so auto-zoom can be told about manual input.</returns>
        public bool Update(ZoomPanCamera camera, Float2 panStick, float zoomAxis, Float2 zoomFocus, float deltaTime)
        {
            if (camera == null) throw new ArgumentNullException(nameof(camera));
            if (!(deltaTime > 0f)) return false;

            bool moved = false;
            if (panStick != Float2.Zero && !float.IsNaN(panStick.X) && !float.IsNaN(panStick.Y))
            {
                camera.Pan(panStick * (-PanSpeed * camera.ViewportHeight * deltaTime));
                moved = true;
            }
            if (zoomAxis != 0f && !float.IsNaN(zoomAxis))
            {
                float axis = Math.Max(-1f, Math.Min(1f, zoomAxis));
                camera.ZoomAt(zoomFocus, (float)Math.Pow(2.0, axis * ZoomSpeed * deltaTime));
                moved = true;
            }
            return moved;
        }
    }
}
