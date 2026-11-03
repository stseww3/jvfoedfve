using System;
using System.Reflection;
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
			SetScreenProperty("sleepTimeout", value ? -1 : -2);
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
		SetScreenProperty("autorotateToPortrait", false);
		SetScreenProperty("autorotateToPortraitUpsideDown", false);
		SetScreenProperty("autorotateToLandscapeLeft", true);
		SetScreenProperty("autorotateToLandscapeRight", true);
		if (Screen.orientation != ScreenOrientation.LandscapeLeft &&
		    Screen.orientation != ScreenOrientation.LandscapeRight &&
		    Screen.orientation != ScreenOrientation.AutoRotation)
		{
			SetScreenProperty("orientation", ScreenOrientation.LandscapeLeft);
		}
		SetScreenProperty("orientation", ScreenOrientation.AutoRotation);

		// 2. Use managed C# audio DSP fallbacks in G-Audio so audio never fails if native DSP is absent
		GATData.UseNativeGainMixToInterlaced = false;
		GATData.UseNativeResampleCopyFrom = false;
		GATLFO.UseNative = false;

		// 3. Always allow at least 2 simultaneous touches so 2-finger pinch-to-zoom works in both overview and edit mode
		if (_inputState is InputState concreteInputState)
		{
			concreteInputState.MaxRecognizedTouchCount = 2;
		}

		// 4. Connect both Touch and Gamepad (Razer Kishi V2, Xbox, DualSense) simultaneously
		_inputState.ControllerConnected(_scope.Get<IGamepadController>());
		_inputState.ControllerConnected(_scope.Get<ITouchScreenController>());

		// 5. Initialize frame-rate & thermal/battery optimizer (30 / 60 / Auto up to 90Hz on Galaxy A72)
		Application.targetFrameRate = 60;
		AndroidPerformanceManager.EnsureInstance(_scope);
	}

	private static void SetScreenProperty(string propertyName, object value)
	{
		try
		{
			PropertyInfo prop = typeof(Screen).GetProperty(propertyName, BindingFlags.Public | BindingFlags.Static);
			if (prop != null && prop.CanWrite)
			{
				prop.SetValue(null, value);
			}
		}
		catch (Exception)
		{
		}
	}

	private static void TriggerAndroidVibration(long milliseconds, int amplitude)
	{
		try
		{
			if (Application.platform != RuntimePlatform.Android)
			{
				return;
			}
			Type jcType = Type.GetType("UnityEngine.AndroidJavaClass, UnityEngine.AndroidJNIModule");
			if (jcType == null)
			{
				return;
			}
			using IDisposable unityPlayer = (IDisposable)Activator.CreateInstance(jcType, "com.unity3d.player.UnityPlayer");
			MethodInfo getStaticObj = jcType.GetMethod("GetStatic", new[] { typeof(string) });
			if (getStaticObj == null)
			{
				return;
			}
			MethodInfo getStaticActivity = getStaticObj.MakeGenericMethod(typeof(AndroidJavaObject));
			using AndroidJavaObject activity = (AndroidJavaObject)getStaticActivity.Invoke(unityPlayer, new object[] { "currentActivity" });
			using AndroidJavaObject vibrator = activity?.Call<AndroidJavaObject>("getSystemService", new object[] { "vibrator" });
			if (vibrator == null || !vibrator.Call<bool>("hasVibrator", Array.Empty<object>()))
			{
				return;
			}
			MethodInfo callVoid = typeof(AndroidJavaObject).GetMethod("Call", new[] { typeof(string), typeof(object[]) });
			callVoid?.Invoke(vibrator, new object[] { "vibrate", new object[] { milliseconds } });
		}
		catch (Exception)
		{
		}
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
