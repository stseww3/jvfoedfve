using UnityEngine;
using UnityEngine.Rendering;

/// <summary>
/// Frame-rate and battery policy. Unity on Android runs at 30 fps unless told otherwise, and a calm
/// puzzle game doesn't need to redraw a pause screen at full rate.
/// - Player setting: 30 / 60 / 90 fps (90 only makes a difference on high-refresh screens like the Galaxy A72's).
/// - Menus, pause and game over render every Nth frame while input keeps running every frame.
/// - Optional automatic battery saver: 30 fps while the battery is low and not charging.
/// - The screen is kept awake during play only.
/// Call SetInGameplay(true) when a run starts or resumes and SetInGameplay(false) for menus/pause/game over.
/// </summary>
public class PerformanceSettings : MonoBehaviour
{
    public enum FrameRateOption { Fps30 = 30, Fps60 = 60, Fps90 = 90 }

    const string FrameRatePrefKey = "settings.frameRate";
    const string BatterySaverPrefKey = "settings.autoBatterySaver";
    const float BatteryCheckInterval = 30f;

    [SerializeField] FrameRateOption defaultFrameRate = FrameRateOption.Fps60;
    [Tooltip("While paused or in menus, render only every Nth frame. Input still runs every frame.")]
    [SerializeField, Range(1, 4)] int menuRenderInterval = 2;
    [Tooltip("Battery level (0-1) below which the automatic battery saver drops to 30 fps.")]
    [SerializeField, Range(0f, 1f)] float lowBatteryLevel = 0.2f;

    public static PerformanceSettings Instance { get; private set; }

    FrameRateOption frameRate;
    bool autoBatterySaver;
    bool inGameplay;
    bool batteryLow;
    float nextBatteryCheck;

    public FrameRateOption FrameRate
    {
        get => frameRate;
        set
        {
            frameRate = value;
            PlayerPrefs.SetInt(FrameRatePrefKey, (int)value);
            PlayerPrefs.Save();
            Apply();
        }
    }

    public bool AutoBatterySaver
    {
        get => autoBatterySaver;
        set
        {
            autoBatterySaver = value;
            PlayerPrefs.SetInt(BatterySaverPrefKey, value ? 1 : 0);
            PlayerPrefs.Save();
            Apply();
        }
    }

    /// <summary>The display's current refresh rate in Hz. Offer the 90 fps option only when this is 90 or more.</summary>
    public static int DisplayRefreshRate
    {
        get
        {
#if UNITY_2022_2_OR_NEWER
            return Mathf.RoundToInt((float)Screen.currentResolution.refreshRateRatio.value);
#else
            return Screen.currentResolution.refreshRate;
#endif
        }
    }

    void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;
        DontDestroyOnLoad(gameObject);

        frameRate = (FrameRateOption)PlayerPrefs.GetInt(FrameRatePrefKey, (int)defaultFrameRate);
        if (!System.Enum.IsDefined(typeof(FrameRateOption), frameRate))
            frameRate = defaultFrameRate;
        autoBatterySaver = PlayerPrefs.GetInt(BatterySaverPrefKey, 1) == 1;
        batteryLow = IsBatteryLow();
        Apply();
    }

    public void SetInGameplay(bool active)
    {
        inGameplay = active;
        Apply();
    }

    void Update()
    {
        if (Time.unscaledTime < nextBatteryCheck)
            return;
        nextBatteryCheck = Time.unscaledTime + BatteryCheckInterval;
        bool low = IsBatteryLow();
        if (low != batteryLow)
        {
            batteryLow = low;
            Apply();
        }
    }

    void Apply()
    {
        int fps = (int)frameRate;
        if (autoBatterySaver && batteryLow)
            fps = 30;
        if (!inGameplay)
            fps = Mathf.Min(fps, 60);

        Application.targetFrameRate = fps;
        OnDemandRendering.renderFrameInterval = inGameplay ? 1 : menuRenderInterval;
        Screen.sleepTimeout = inGameplay ? SleepTimeout.NeverSleep : SleepTimeout.SystemSetting;
    }

    bool IsBatteryLow()
    {
        float level = SystemInfo.batteryLevel;
        BatteryStatus status = SystemInfo.batteryStatus;
        return level >= 0f && level < lowBatteryLevel
            && status != BatteryStatus.Charging && status != BatteryStatus.Full;
    }
}
