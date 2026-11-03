using System;
using Factory;
using GAudio;
using UnityEngine;

public class AndroidHardwareCapabilities : IHardwareCapabilities
{
	[Dependency]
	protected IScope _scope;

	[Dependency]
	private LocaleDatabase _localeDatabase;

	[Dependency]
	private IInputState _inputState;

	private string _deviceId;
	private bool _preventingSleep;

	public RuntimePlatform Platform => Application.platform;

	public LocaleDatabase.LocaleId PreferredLocaleId
	{
		get
		{
			return SystemLanguageToLocaleId(Application.systemLanguage);
		}
	}

	public string PersistentStoragePath => Application.persistentDataPath;

	public string UniqueDeviceId
	{
		get
		{
			if (_deviceId == null)
			{
				_deviceId = HashUtils.GetMD5(SystemInfo.deviceUniqueIdentifier);
			}
			return _deviceId;
		}
	}

	public bool SupportsHapticFeedback => true;

	public bool IsPreventingSleep
	{
		get
		{
			return _preventingSleep;
		}
		set
		{
			_preventingSleep = value;
			Screen.sleepTimeout = value ? SleepTimeout.NeverSleep : SleepTimeout.SystemSetting;
		}
	}

	public bool SupportsManualExit => false;

	public bool SupportsChangingResolution => false;

	public Vector2Int DefaultMaximumResolution => new Vector2Int(-1, -1);

	public bool SupportsAntiAliasingOptions => false;

	public int DefaultAntiAliasingLevel => 0;

	public bool SupportsMultipleDisplays => false;

	public int DisplayCount => 1;

	public DeviceInputType DefaultDeviceInputType => DeviceInputType.Touch;

	public DeviceInputGamepadStyle CurrentGamepadStyle => DeviceInputGamepadStyle.Generic;

	public event Action<DeviceInputGamepadStyle> OnGamepadStyleChanged
	{
		add { }
		remove { }
	}

	public void GenerateHapticFeedback(HapticFeedbackType feedback)
	{
		long milliseconds = 15L;
		int amplitude = 80;
		switch (feedback)
		{
		case HapticFeedbackType.LightImpact:
		case HapticFeedbackType.Selection:
			milliseconds = 10L;
			amplitude = 60;
			break;
		case HapticFeedbackType.MediumImpact:
		case HapticFeedbackType.Success:
			milliseconds = 20L;
			amplitude = 128;
			break;
		case HapticFeedbackType.HeavyImpact:
		case HapticFeedbackType.Warning:
		case HapticFeedbackType.Error:
			milliseconds = 35L;
			amplitude = 220;
			break;
		}
		TriggerAndroidVibration(milliseconds, amplitude);
	}

	public void Exit()
	{
		Application.Quit();
	}

	public virtual void OnAppStart()
	{
		// 1. Always Horizontal (Landscape Left & Landscape Right auto-rotation)
		Screen.autorotateToPortrait = false;
		Screen.autorotateToPortraitUpsideDown = false;
		Screen.autorotateToLandscapeLeft = true;
		Screen.autorotateToLandscapeRight = true;
		if (Screen.orientation != ScreenOrientation.LandscapeLeft &&
		    Screen.orientation != ScreenOrientation.LandscapeRight &&
		    Screen.orientation != ScreenOrientation.AutoRotation)
		{
			Screen.orientation = ScreenOrientation.LandscapeLeft;
		}
		Screen.orientation = ScreenOrientation.AutoRotation;

		// 2. Use managed C# audio DSP fallbacks in G-Audio so audio never fails if native DSP is absent
		GATData.UseNativeGainMixToInterlaced = false;
		GATData.UseNativeResampleCopyFrom = false;
		GATLFO.UseNative = false;

		// 3. Always allow at least 2 simultaneous touches so 2-finger pinch-to-zoom works in both overview and edit mode
		_inputState.MaxRecognizedTouchCount = 2;

		// 4. Connect both Touch and Gamepad (Razer Kishi V2, Xbox, DualSense) simultaneously
		_inputState.ControllerConnected(_scope.Get<IGamepadController>());
		_inputState.ControllerConnected(_scope.Get<ITouchScreenController>());

		// 5. Initialize frame-rate & thermal/battery optimizer (30 / 60 / Auto up to 90Hz on Galaxy A72)
		QualitySettings.vSyncCount = 0;
		Application.targetFrameRate = 60;
		AndroidPerformanceManager.EnsureInstance(_scope);
	}

	private static void TriggerAndroidVibration(long milliseconds, int amplitude)
	{
#if UNITY_ANDROID && !UNITY_EDITOR
		try
		{
			using AndroidJavaClass unityPlayer = new AndroidJavaClass("com.unity3d.player.UnityPlayer");
			using AndroidJavaObject activity = unityPlayer.GetStatic<AndroidJavaObject>("currentActivity");
			using AndroidJavaObject vibrator = activity?.Call<AndroidJavaObject>("getSystemService", "vibrator");
			if (vibrator == null || !vibrator.Call<bool>("hasVibrator"))
			{
				return;
			}
			using AndroidJavaClass buildVersion = new AndroidJavaClass("android.os.Build$VERSION");
			int sdkInt = buildVersion.GetStatic<int>("SDK_INT");
			if (sdkInt >= 26)
			{
				using AndroidJavaClass vibrationEffectClass = new AndroidJavaClass("android.os.VibrationEffect");
				using AndroidJavaObject effect = vibrationEffectClass.CallStatic<AndroidJavaObject>("createOneShot", milliseconds, Mathf.Clamp(amplitude, 1, 255));
				vibrator.Call("vibrate", effect);
			}
			else
			{
				vibrator.Call("vibrate", milliseconds);
			}
		}
		catch (Exception)
		{
		}
#endif
	}

	private static LocaleDatabase.LocaleId SystemLanguageToLocaleId(SystemLanguage language)
	{
		return language switch
		{
			SystemLanguage.Arabic => LocaleDatabase.LocaleId.ar,
			SystemLanguage.German => LocaleDatabase.LocaleId.de,
			SystemLanguage.Spanish => LocaleDatabase.LocaleId.es_ES,
			SystemLanguage.French => LocaleDatabase.LocaleId.fr,
			SystemLanguage.Italian => LocaleDatabase.LocaleId.it,
			SystemLanguage.Japanese => LocaleDatabase.LocaleId.ja,
			SystemLanguage.Korean => LocaleDatabase.LocaleId.ko,
			SystemLanguage.Dutch => LocaleDatabase.LocaleId.nl,
			SystemLanguage.Portuguese => LocaleDatabase.LocaleId.pt_BR,
			SystemLanguage.Russian => LocaleDatabase.LocaleId.ru,
			SystemLanguage.Turkish => LocaleDatabase.LocaleId.tr,
			SystemLanguage.ChineseSimplified => LocaleDatabase.LocaleId.zh_CN,
			SystemLanguage.ChineseTraditional => LocaleDatabase.LocaleId.zh_TW,
			SystemLanguage.Chinese => LocaleDatabase.LocaleId.zh_CN,
			_ => LocaleDatabase.LocaleId.en_US,
		};
	}
}
