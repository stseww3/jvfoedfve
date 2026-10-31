using UnityEngine;

/// <summary>
/// Orthographic map camera for touch and gamepad: two-finger pinch zoom and pan, zoom/pan calls for
/// gamepad sticks and triggers, edge scrolling while drawing, and an auto-zoom mode that keeps the whole
/// play area framed as it grows. Works with any camera rotation (straight top-down or tilted).
///
/// Auto-zoom is a player setting (saved in PlayerPrefs). When it is on and the player zooms or pans by
/// hand, auto-zoom steps aside and takes over again after <see cref="resumeAutoZoomAfter"/> seconds, or
/// straight away when <see cref="Recenter"/> is called.
/// </summary>
[RequireComponent(typeof(Camera))]
[DisallowMultipleComponent]
public class MapCamera : MonoBehaviour
{
    const string AutoZoomPrefKey = "settings.autoZoom";

    [SerializeField] TouchGestures touchGestures;
    [SerializeField] float minSize = 3f;
    [Tooltip("Furthest zoom-out allowed. Raised automatically if the play area needs more room to fit.")]
    [SerializeField] float maxSize = 40f;
    [Tooltip("World units of margin kept around the play area when it is framed.")]
    [SerializeField] float framePadding = 1.5f;
    [Tooltip("Seconds the camera takes to ease into a new auto-zoom framing.")]
    [SerializeField] float autoZoomSmoothTime = 0.6f;
    [Tooltip("After the player zooms or pans by hand, auto-zoom waits this long before taking over again. 0 = only on Recenter().")]
    [SerializeField] float resumeAutoZoomAfter = 6f;
    [SerializeField] bool autoZoomByDefault = true;

    Camera cam;
    Bounds playArea;
    bool hasPlayArea;
    bool autoZoom;
    bool manualOverride;
    float lastManualInputTime;
    float sizeVelocity;
    Vector3 positionVelocity;

    /// <summary>The player's auto-zoom setting. Bind a settings Toggle to this.</summary>
    public bool AutoZoom
    {
        get => autoZoom;
        set
        {
            autoZoom = value;
            PlayerPrefs.SetInt(AutoZoomPrefKey, value ? 1 : 0);
            PlayerPrefs.Save();
            if (value)
                Recenter();
        }
    }

    /// <summary>True while auto-zoom is on but paused because the player moved the camera. Show a "recenter" button then.</summary>
    public bool IsManuallyOverridden => autoZoom && manualOverride;

    void Awake()
    {
        cam = GetComponent<Camera>();
        cam.orthographic = true;
        autoZoom = PlayerPrefs.GetInt(AutoZoomPrefKey, autoZoomByDefault ? 1 : 0) == 1;
    }

    void OnEnable()
    {
        if (touchGestures == null)
            return;
        touchGestures.Pinched += ZoomBy;
        touchGestures.TwoFingerPanned += PanByScreenDelta;
    }

    void OnDisable()
    {
        if (touchGestures == null)
            return;
        touchGestures.Pinched -= ZoomBy;
        touchGestures.TwoFingerPanned -= PanByScreenDelta;
    }

    /// <summary>Call on load and whenever the playable region grows. Auto-zoom frames this area.</summary>
    public void SetPlayArea(Bounds worldBounds)
    {
        playArea = worldBounds;
        hasPlayArea = true;
    }

    /// <summary>Hands the camera back to auto-zoom immediately.</summary>
    public void Recenter()
    {
        manualOverride = false;
    }

    /// <summary>Zooms while keeping the world point under <paramref name="screenPivot"/> still. factor &gt; 1 zooms in.</summary>
    public void ZoomBy(float factor, Vector2 screenPivot)
    {
        if (factor <= 0f)
            return;
        NoteManualInput();
        Vector3 before = ScreenToWorld(screenPivot);
        cam.orthographicSize = Mathf.Clamp(cam.orthographicSize / factor, minSize, MaxSize());
        Vector3 after = ScreenToWorld(screenPivot);
        transform.position += before - after;
        ClampToPlayArea();
    }

    /// <summary>Moves the map as if it were dragged by <paramref name="screenDelta"/> pixels (the map follows the finger).</summary>
    public void PanByScreenDelta(Vector2 screenDelta)
    {
        if (screenDelta == Vector2.zero)
            return;
        NoteManualInput();
        float worldUnitsPerPixel = 2f * cam.orthographicSize / cam.pixelHeight;
        transform.position -= (transform.right * screenDelta.x + transform.up * screenDelta.y) * worldUnitsPerPixel;
        ClampToPlayArea();
    }

    /// <summary>
    /// Call every frame while the player is drawing; scrolls the view when the pointer is within
    /// <paramref name="edgeDp"/> of a screen edge, at <paramref name="screenHeightsPerSecond"/>.
    /// </summary>
    public void EdgeScroll(Vector2 pointer, float edgeDp = 40f, float screenHeightsPerSecond = 0.5f)
    {
        float edge = edgeDp * (Screen.dpi > 0f ? Screen.dpi : 160f) / 160f;
        Vector2 direction = Vector2.zero;
        if (pointer.x < edge)
            direction.x = -1f;
        else if (pointer.x > Screen.width - edge)
            direction.x = 1f;
        if (pointer.y < edge)
            direction.y = -1f;
        else if (pointer.y > Screen.height - edge)
            direction.y = 1f;
        if (direction != Vector2.zero)
            PanByScreenDelta(-direction * screenHeightsPerSecond * Screen.height * Time.unscaledDeltaTime);
    }

    void LateUpdate()
    {
        if (manualOverride && resumeAutoZoomAfter > 0f && Time.unscaledTime - lastManualInputTime >= resumeAutoZoomAfter)
            manualOverride = false;

        if (!autoZoom || manualOverride || !hasPlayArea)
            return;

        float targetSize = Mathf.Max(minSize, FitPlayArea(out Vector3 targetPosition));
        float dt = Time.unscaledDeltaTime;
        cam.orthographicSize = Mathf.SmoothDamp(cam.orthographicSize, targetSize, ref sizeVelocity, autoZoomSmoothTime, Mathf.Infinity, dt);
        transform.position = Vector3.SmoothDamp(transform.position, targetPosition, ref positionVelocity, autoZoomSmoothTime, Mathf.Infinity, dt);
    }

    void NoteManualInput()
    {
        lastManualInputTime = Time.unscaledTime;
        manualOverride = true;
        sizeVelocity = 0f;
        positionVelocity = Vector3.zero;
    }

    float MaxSize()
    {
        return hasPlayArea ? Mathf.Max(maxSize, FitPlayArea(out _)) : maxSize;
    }

    /// <summary>Orthographic size and camera position that show the whole play area at the current screen aspect.</summary>
    float FitPlayArea(out Vector3 position)
    {
        ProjectPlayArea(out Vector3 min, out Vector3 max);
        position = transform.TransformPoint(new Vector3((min.x + max.x) * 0.5f, (min.y + max.y) * 0.5f, 0f));
        float halfHeight = (max.y - min.y) * 0.5f + framePadding;
        float halfWidth = (max.x - min.x) * 0.5f + framePadding;
        return Mathf.Max(halfHeight, halfWidth / cam.aspect);
    }

    /// <summary>Keeps the centre of the view over the play area so the map can't be flung off screen.</summary>
    void ClampToPlayArea()
    {
        if (!hasPlayArea)
            return;
        ProjectPlayArea(out Vector3 min, out Vector3 max);
        float x = Mathf.Clamp(0f, min.x, max.x);
        float y = Mathf.Clamp(0f, min.y, max.y);
        if (x != 0f || y != 0f)
            transform.position += transform.right * x + transform.up * y;
    }

    /// <summary>The play area's corners in camera-local space, i.e. as the camera sees them (x right, y up).</summary>
    void ProjectPlayArea(out Vector3 min, out Vector3 max)
    {
        min = new Vector3(float.MaxValue, float.MaxValue, float.MaxValue);
        max = new Vector3(float.MinValue, float.MinValue, float.MinValue);
        Vector3 c = playArea.center;
        Vector3 e = playArea.extents;
        for (int i = 0; i < 8; i++)
        {
            var corner = new Vector3(
                (i & 1) == 0 ? c.x - e.x : c.x + e.x,
                (i & 2) == 0 ? c.y - e.y : c.y + e.y,
                (i & 4) == 0 ? c.z - e.z : c.z + e.z);
            Vector3 local = transform.InverseTransformPoint(corner);
            min = Vector3.Min(min, local);
            max = Vector3.Max(max, local);
        }
    }

    Vector3 ScreenToWorld(Vector2 screen)
    {
        return cam.ScreenToWorldPoint(new Vector3(screen.x, screen.y, cam.nearClipPlane));
    }
}
