// NOT RUNTIME-TESTED. Written for Unity 2021.3 LTS or newer but never run in Unity or on a device.
// It is only compile-checked against hand-written stand-ins for the UnityEngine API
// (tests/UnityApiStubs).

using UnityEngine;

namespace UnityMobileKit.Runtime
{
    public enum OrientationMode
    {
        /// <summary>Landscape left and right, following the device's sensor.</summary>
        Landscape,
        /// <summary>Upright portrait only.</summary>
        Portrait,
    }

    /// <summary>
    /// Restricts rotation at runtime. Also set Player Settings > Resolution and Presentation >
    /// Default Orientation to Auto Rotation with only the matching orientations allowed: that is
    /// what the OS enforces before Unity starts (splash screen, Android manifest).
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class OrientationLock : MonoBehaviour
    {
        [SerializeField] private OrientationMode mode = OrientationMode.Landscape;

        private bool _waitingForRotation;

        public OrientationMode Mode
        {
            get => mode;
            set
            {
                mode = value;
                Apply();
            }
        }

        private void Awake() => Apply();

        private void Update()
        {
            // Hand rotation back to the sensor once the forced orientation has taken effect.
            if (_waitingForRotation && IsAllowed(Screen.orientation))
            {
                Screen.orientation = ScreenOrientation.AutoRotation;
                _waitingForRotation = false;
            }
        }

        private void Apply()
        {
            bool landscape = mode == OrientationMode.Landscape;
            Screen.autorotateToLandscapeLeft = landscape;
            Screen.autorotateToLandscapeRight = landscape;
            Screen.autorotateToPortrait = !landscape;
            Screen.autorotateToPortraitUpsideDown = false;

            if (IsAllowed(Screen.orientation))
            {
                Screen.orientation = ScreenOrientation.AutoRotation;
                _waitingForRotation = false;
            }
            else
            {
                Screen.orientation = landscape ? ScreenOrientation.LandscapeLeft : ScreenOrientation.Portrait;
                _waitingForRotation = true;
            }
        }

        private bool IsAllowed(ScreenOrientation orientation)
        {
            return mode == OrientationMode.Landscape
                ? orientation == ScreenOrientation.LandscapeLeft || orientation == ScreenOrientation.LandscapeRight
                : orientation == ScreenOrientation.Portrait;
        }
    }
}
