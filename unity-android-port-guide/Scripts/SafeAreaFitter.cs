using UnityEngine;

/// <summary>
/// Shrinks a full-screen RectTransform to Screen.safeArea so HUD elements stay clear of the punch-hole
/// camera, rounded corners and the gesture bar. Put it on a stretched child of the Canvas and parent all
/// HUD elements under it. Requires "Render outside safe area" in the Android Player Settings, otherwise
/// Unity letterboxes the cutout instead and the safe area is always the full screen.
/// </summary>
[RequireComponent(typeof(RectTransform))]
public class SafeAreaFitter : MonoBehaviour
{
    RectTransform rect;
    Rect appliedSafeArea;
    Vector2Int appliedScreenSize;

    void Awake()
    {
        rect = (RectTransform)transform;
    }

    void OnEnable()
    {
        Apply();
    }

    void Update()
    {
        if (Screen.safeArea != appliedSafeArea || Screen.width != appliedScreenSize.x || Screen.height != appliedScreenSize.y)
            Apply();
    }

    void Apply()
    {
        appliedSafeArea = Screen.safeArea;
        appliedScreenSize = new Vector2Int(Screen.width, Screen.height);
        if (Screen.width <= 0 || Screen.height <= 0)
            return;

        Vector2 anchorMin = appliedSafeArea.min;
        Vector2 anchorMax = appliedSafeArea.max;
        anchorMin.x /= Screen.width;
        anchorMin.y /= Screen.height;
        anchorMax.x /= Screen.width;
        anchorMax.y /= Screen.height;

        rect.anchorMin = anchorMin;
        rect.anchorMax = anchorMax;
        rect.offsetMin = Vector2.zero;
        rect.offsetMax = Vector2.zero;
    }
}
