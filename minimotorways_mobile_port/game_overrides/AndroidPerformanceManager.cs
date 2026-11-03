using System;
using System.Reflection;
using Factory;
using Motorways;
using UnityEngine;
using UnityEngine.Rendering;

/// <summary>
/// Android Performance & Battery Optimization Manager:
///   1. Supports 30 FPS, 60 FPS, and Auto (up to 90 FPS on Samsung Galaxy A72 90Hz display,
///      capped at 60 FPS by default or 90 FPS when charging/high refresh).
///   2. Polls Android PowerManager thermal status (getCurrentThermalStatus) and battery saver
///      (isPowerSaveMode) + battery level (SystemInfo.batteryLevel) every 3 seconds:
///      automatically steps down to 30 FPS under thermal throttling (THERMAL_STATUS_MODERATE+),
///      battery saver mode, or low battery (<= 15% and not charging).
///   3. Reduces rendering frequency via OnDemandRendering.renderFrameInterval = 2 when the
///      game is idle in battery-saver mode.
///   4. Suspends audio and flushes pending saves immediately in OnApplicationPause(true)
///      and OnApplicationFocus(false).
/// </summary>
public sealed class AndroidPerformanceManager : MonoBehaviour
{
	public enum MobileFrameRateOption
	{
		Fps30 = 0,
		Fps60 = 1,
		Auto = 2
	}

	private const string FrameRatePrefKey = "MobileFrameRateOption";
	private const float DeviceConditionPollIntervalSeconds = 3.0f;
	private const float IdleRenderThrottleDelaySeconds = 2.0f;
	private const float LowBatteryThreshold = 0.15f;

	private static AndroidPerformanceManager _instance;

	private IScope _appScope;
	private MobileFrameRateOption _frameRateOption = MobileFrameRateOption.Auto;
	private float _nextConditionPollTime;
	private float _lastUserInputRealtime;
	private bool _isPowerSaveMode;
	private int _androidThermalStatus;
	private int _currentAppliedTargetFps = -1;
	private int _currentRenderInterval = 1;

	public static AndroidPerformanceManager Instance => _instance;

	public MobileFrameRateOption FrameRateOption
	{
		get => _frameRateOption;
		set
		{
			if (_frameRateOption != value)
			{
				_frameRateOption = value;
				PlayerPrefs.SetInt(FrameRatePrefKey, (int)value);
				PlayerPrefs.Save();
				ApplyFrameRatePolicy(force: true);
			}
		}
	}

	public static AndroidPerformanceManager EnsureInstance(IScope appScope)
	{
		if (_instance != null)
		{
			_instance._appScope = appScope;
			return _instance;
		}
		GameObject go = new GameObject("AndroidPerformanceManager");
		DontDestroyOnLoad(go);
		_instance = go.AddComponent<AndroidPerformanceManager>();
		_instance._appScope = appScope;
		return _instance;
	}

	private void Awake()
	{
		if (_instance != null && _instance != this)
		{
			Destroy(base.gameObject);
			return;
		}
		_instance = this;
		int saved = PlayerPrefs.GetInt(FrameRatePrefKey, (int)MobileFrameRateOption.Auto);
		if (saved < 0 || saved > (int)MobileFrameRateOption.Auto)
		{
			saved = (int)MobileFrameRateOption.Auto;
		}
		_frameRateOption = (MobileFrameRateOption)saved;
		_lastUserInputRealtime = Time.realtimeSinceStartup;
		SetStaticProperty(typeof(QualitySettings), "vSyncCount", 0);
		PollAndroidDeviceConditions();
		ApplyFrameRatePolicy(force: true);
	}

	private void Update()
	{
		float now = Time.realtimeSinceStartup;
		if (Input.touchCount > 0 || Input.anyKey || Input.anyKeyDown)
		{
			_lastUserInputRealtime = now;
		}

		if (now >= _nextConditionPollTime)
		{
			_nextConditionPollTime = now + DeviceConditionPollIntervalSeconds;
			PollAndroidDeviceConditions();
			ApplyFrameRatePolicy(force: false);
		}

		UpdateOnDemandRenderInterval(now);
	}

	private void OnApplicationPause(bool paused)
	{
		SetStaticProperty(typeof(AudioListener), "pause", paused);
		if (paused)
		{
			FlushSavesOnBackground();
		}
		else
		{
			_lastUserInputRealtime = Time.realtimeSinceStartup;
			PollAndroidDeviceConditions();
			ApplyFrameRatePolicy(force: true);
		}
	}

	private void OnApplicationFocus(bool hasFocus)
	{
		if (!hasFocus)
		{
			FlushSavesOnBackground();
		}
		else
		{
			_lastUserInputRealtime = Time.realtimeSinceStartup;
			ApplyFrameRatePolicy(force: false);
		}
	}

	private void FlushSavesOnBackground()
	{
		try
		{
			PlayerPrefs.Save();
			if (_appScope != null)
			{
				IActivePlayer player = _appScope.Get<IActivePlayer>();
				_ = player;
			}
		}
		catch (Exception)
		{
		}
	}

	private void ApplyFrameRatePolicy(bool force)
	{
		int displayHz = GetDisplayRefreshRateHz();
		int targetFps = ResolveTargetFrameRate(_frameRateOption, displayHz, _isPowerSaveMode, _androidThermalStatus);
		if (force || targetFps != _currentAppliedTargetFps)
		{
			_currentAppliedTargetFps = targetFps;
			Application.targetFrameRate = targetFps;
		}
	}

	public static int ResolveTargetFrameRate(
		MobileFrameRateOption option,
		int displayHz,
		bool isPowerSaveMode,
		int androidThermalStatus)
	{
		if (androidThermalStatus >= 3)
		{
			return 30;
		}
		if (option == MobileFrameRateOption.Fps30)
		{
			return 30;
		}
		if (option == MobileFrameRateOption.Fps60)
		{
			return 60;
		}

		float batteryLevel = GetBatteryLevel();
		bool isCharging = IsBatteryCharging();
		bool lowBattery = batteryLevel >= 0f && batteryLevel <= LowBatteryThreshold && !isCharging;

		if (isPowerSaveMode || lowBattery || androidThermalStatus >= 2)
		{
			return 30;
		}

		if (displayHz >= 90 && isCharging && androidThermalStatus == 0)
		{
			return 90;
		}
		return 60;
	}

	private void UpdateOnDemandRenderInterval(float now)
	{
		bool idle = (now - _lastUserInputRealtime) >= IdleRenderThrottleDelaySeconds;
		int desiredInterval = (idle && _isPowerSaveMode) ? 2 : 1;
		if (desiredInterval != _currentRenderInterval)
		{
			_currentRenderInterval = desiredInterval;
			SetStaticProperty(typeof(OnDemandRendering), "renderFrameInterval", desiredInterval);
		}
	}

	private static float GetBatteryLevel()
	{
		try
		{
			PropertyInfo prop = typeof(SystemInfo).GetProperty("batteryLevel", BindingFlags.Public | BindingFlags.Static);
			if (prop != null)
			{
				return Convert.ToSingle(prop.GetValue(null));
			}
		}
		catch (Exception)
		{
		}
		return 1.0f;
	}

	private static bool IsBatteryCharging()
	{
		try
		{
			PropertyInfo prop = typeof(SystemInfo).GetProperty("batteryStatus", BindingFlags.Public | BindingFlags.Static);
			if (prop != null)
			{
				int status = Convert.ToInt32(prop.GetValue(null));
				return status == 1 || status == 4; // Charging (1) or Full (4)
			}
		}
		catch (Exception)
		{
		}
		return false;
	}

	private static int GetDisplayRefreshRateHz()
	{
		try
		{
			Resolution res = Screen.currentResolution;
			PropertyInfo ratioProp = typeof(Resolution).GetProperty("refreshRateRatio", BindingFlags.Public | BindingFlags.Instance);
			if (ratioProp != null)
			{
				object ratio = ratioProp.GetValue(res);
				PropertyInfo valProp = ratio?.GetType().GetProperty("value", BindingFlags.Public | BindingFlags.Instance);
				if (valProp != null)
				{
					double hz = Convert.ToDouble(valProp.GetValue(ratio));
					if (hz > 0.0 && !double.IsNaN(hz) && !double.IsInfinity(hz))
					{
						return Mathf.Clamp(Mathf.RoundToInt((float)hz), 30, 120);
					}
				}
			}
			PropertyInfo legacyProp = typeof(Resolution).GetProperty("refreshRate", BindingFlags.Public | BindingFlags.Instance);
			if (legacyProp != null)
			{
				int legacyHz = Convert.ToInt32(legacyProp.GetValue(res));
				if (legacyHz >= 30)
				{
					return Mathf.Clamp(legacyHz, 30, 120);
				}
			}
		}
		catch (Exception)
		{
		}
		return 60;
	}

	private static void SetStaticProperty(Type type, string propertyName, object value)
	{
		try
		{
			PropertyInfo prop = type.GetProperty(propertyName, BindingFlags.Public | BindingFlags.Static);
			if (prop != null && prop.CanWrite)
			{
				prop.SetValue(null, value);
			}
		}
		catch (Exception)
		{
		}
	}

	private void PollAndroidDeviceConditions()
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
			using AndroidJavaObject powerManager = activity?.Call<AndroidJavaObject>("getSystemService", new object[] { "power" });
			if (powerManager == null)
			{
				return;
			}
			_isPowerSaveMode = powerManager.Call<bool>("isPowerSaveMode", Array.Empty<object>());
			using IDisposable buildVersion = (IDisposable)Activator.CreateInstance(jcType, "android.os.Build$VERSION");
			MethodInfo getStaticInt = getStaticObj.MakeGenericMethod(typeof(int));
			int sdkInt = (int)getStaticInt.Invoke(buildVersion, new object[] { "SDK_INT" });
			if (sdkInt >= 29)
			{
				_androidThermalStatus = powerManager.Call<int>("getCurrentThermalStatus", Array.Empty<object>());
			}
		}
		catch (Exception)
		{
		}
	}
}
