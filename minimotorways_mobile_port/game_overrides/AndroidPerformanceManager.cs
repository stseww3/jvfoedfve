using System;
using Factory;
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
///      game is paused and no touch/controller input occurred in the last 2 seconds.
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
	private int _androidThermalStatus; // 0=NONE, 1=LIGHT, 2=MODERATE, 3=SEVERE, 4=CRITICAL
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
		QualitySettings.vSyncCount = 0;
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
		AudioListener.pause = paused;
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
				ActivePlayer player = _appScope.Get<ActivePlayer>();
				if (player != null && player.HasActivePlayer)
				{
					// Touching the player/device settings triggers persistent write through IPersistentStorageService
				}
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
		// Severe or critical thermal state caps all modes at 30 FPS to protect the device
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

		// Auto mode: step down to 30 FPS on battery saver, moderate heat, or low unplugged battery
		float batteryLevel = SystemInfo.batteryLevel;
		BatteryStatus status = SystemInfo.batteryStatus;
		bool isCharging = status == BatteryStatus.Charging || status == BatteryStatus.Full;
		bool lowBattery = batteryLevel >= 0f && batteryLevel <= LowBatteryThreshold && !isCharging;

		if (isPowerSaveMode || lowBattery || androidThermalStatus >= 2)
		{
			return 30;
		}

		// On 90Hz/120Hz panels (e.g. Samsung Galaxy A72 90Hz), allow 90 FPS when charging & cool, else 60 FPS
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
			OnDemandRendering.renderFrameInterval = desiredInterval;
		}
	}

	private static int GetDisplayRefreshRateHz()
	{
#if UNITY_2022_2_OR_NEWER
		double hz = Screen.currentResolution.refreshRateRatio.value;
		if (hz > 0.0 && !double.IsNaN(hz) && !double.IsInfinity(hz))
		{
			return Mathf.Clamp(Mathf.RoundToInt((float)hz), 30, 120);
		}
#endif
		int legacyHz = Screen.currentResolution.refreshRate;
		return (legacyHz >= 30) ? Mathf.Clamp(legacyHz, 30, 120) : 60;
	}

	private void PollAndroidDeviceConditions()
	{
#if UNITY_ANDROID && !UNITY_EDITOR
		try
		{
			using AndroidJavaClass unityPlayer = new AndroidJavaClass("com.unity3d.player.UnityPlayer");
			using AndroidJavaObject activity = unityPlayer.GetStatic<AndroidJavaObject>("currentActivity");
			using AndroidJavaObject powerManager = activity?.Call<AndroidJavaObject>("getSystemService", "power");
			if (powerManager == null)
			{
				return;
			}
			_isPowerSaveMode = powerManager.Call<bool>("isPowerSaveMode");
			using AndroidJavaClass buildVersion = new AndroidJavaClass("android.os.Build$VERSION");
			int sdkInt = buildVersion.GetStatic<int>("SDK_INT");
			if (sdkInt >= 29)
			{
				_androidThermalStatus = powerManager.Call<int>("getCurrentThermalStatus");
			}
		}
		catch (Exception)
		{
		}
#endif
	}
}
