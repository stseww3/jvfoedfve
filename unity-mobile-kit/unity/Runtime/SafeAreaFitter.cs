// NOT RUNTIME-TESTED. Written for Unity 2021.3 LTS or newer but never run in Unity or on a device.
// It is only compile-checked against hand-written stand-ins for the UnityEngine API
// (tests/UnityApiStubs). The anchor math (core/ScreenLayout/SafeArea) is unit-tested with dotnet.

using UnityEngine;
using UnityMobileKit.Geometry;
using UnityMobileKit.ScreenLayout;

namespace UnityMobileKit.Runtime
{
    /// <summary>
    /// Fits this RectTransform to the screen's safe area, clear of notches, punch-hole cameras and
    /// rounded corners. Use it on a full-screen panel directly under a Screen Space canvas and put
    /// interactive UI inside the panel. Re-fits when the safe area, resolution or orientation changes.
    /// </summary>
    [RequireComponent(typeof(RectTransform))]
    [DisallowMultipleComponent]
    public sealed class SafeAreaFitter : MonoBehaviour
    {
        [Tooltip("Use the larger inset on both opposite sides, so centred UI stays centred when a landscape phone is turned around and the notch changes side.")]
        [SerializeField] private bool symmetric = true;

        private RectTransform _rect;
        private Rect _fittedSafeArea;
        private int _fittedWidth;
        private int _fittedHeight;
        private bool _fittedSymmetric;

        private void Awake() => _rect = GetComponent<RectTransform>();

        private void OnEnable() => Fit(force: true);

        private void Update() => Fit(force: false);

        public void Fit(bool force)
        {
            int width = Screen.width;
            int height = Screen.height;
            if (width <= 0 || height <= 0) return;
            Rect safeArea = Screen.safeArea;
            if (!force && safeArea == _fittedSafeArea && width == _fittedWidth && height == _fittedHeight && symmetric == _fittedSymmetric) return;

            SafeArea.GetAnchors(new RectF(safeArea.x, safeArea.y, safeArea.width, safeArea.height), width, height, symmetric,
                                out Float2 anchorMin, out Float2 anchorMax);
            _rect.anchorMin = new Vector2(anchorMin.X, anchorMin.Y);
            _rect.anchorMax = new Vector2(anchorMax.X, anchorMax.Y);
            _rect.offsetMin = Vector2.zero;
            _rect.offsetMax = Vector2.zero;

            _fittedSafeArea = safeArea;
            _fittedWidth = width;
            _fittedHeight = height;
            _fittedSymmetric = symmetric;
        }
    }
}
