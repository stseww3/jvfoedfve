using System;
using UnityEngine;

/// <summary>
/// App lifecycle events for Android. Android can kill a backgrounded app without ever calling
/// OnApplicationQuit, so Backgrounded is the last reliable moment to save. FocusLost fires when the
/// notification shade, a system dialog or the recent-apps screen covers the game; pause the simulation then.
/// Created automatically; just subscribe to the static events.
/// </summary>
public class AppLifecycle : MonoBehaviour
{
    public static event Action Backgrounded;
    public static event Action Foregrounded;
    public static event Action FocusLost;
    public static event Action FocusGained;

    static AppLifecycle instance;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Create()
    {
        if (instance != null)
            return;
        var host = new GameObject(nameof(AppLifecycle));
        instance = host.AddComponent<AppLifecycle>();
        DontDestroyOnLoad(host);
    }

    void OnEnable()
    {
        Application.lowMemory += OnLowMemory;
    }

    void OnDisable()
    {
        Application.lowMemory -= OnLowMemory;
    }

    void OnApplicationPause(bool paused)
    {
        if (paused)
            Backgrounded?.Invoke();
        else
            Foregrounded?.Invoke();
    }

    void OnApplicationFocus(bool focused)
    {
        if (focused)
            FocusGained?.Invoke();
        else
            FocusLost?.Invoke();
    }

    void OnApplicationQuit()
    {
        Backgrounded?.Invoke();
    }

    static void OnLowMemory()
    {
        Resources.UnloadUnusedAssets();
    }
}
