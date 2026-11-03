using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text;
using UnityEngine;

/// <summary>
/// Android Achievement Handler implementing IAchievementHandler.
///   1. Persists unlocked achievements and incremental statistics offline in
///      Application.persistentDataPath/android_achievements.json using atomic file writes.
///   2. Displays a non-intrusive on-screen toast notification banner when an achievement
///      unlocks with showNotification = true.
///   3. Optionally forwards unlocks to Google Play Games Services / Unity Social API
///      via reflection when present.
/// </summary>
public class AndroidAchievementHandler : IAchievementHandler
{
	private const string SaveFileName = "android_achievements.json";

	private readonly HashSet<string> _unlockedIds = new HashSet<string>(StringComparer.Ordinal);
	private readonly Dictionary<string, int> _statistics = new Dictionary<string, int>(StringComparer.Ordinal);
	private string _saveFilePath;
	private bool _initialized;

	public IReadOnlyCollection<string> UnlockedAchievementIds => _unlockedIds;

	public void OnAppStart()
	{
		if (_initialized)
		{
			return;
		}
		_initialized = true;
		_saveFilePath = Path.Combine(Application.persistentDataPath, SaveFileName);
		LoadFromDisk();
		AndroidAchievementToastOverlay.EnsureInstance();
	}

	public bool CompleteAchievement(Achievement achievement, bool showNotification)
	{
		if (achievement == null || string.IsNullOrEmpty(achievement.Id))
		{
			return false;
		}
		EnsureInitialized();
		bool newlyUnlocked = _unlockedIds.Add(achievement.Id);
		if (newlyUnlocked)
		{
			SaveToDisk();
			if (showNotification)
			{
				AndroidAchievementToastOverlay.EnqueueToast(achievement.Id);
			}
			TryReportToPlatform(achievement.Id);
		}
		return true;
	}

	public bool IsAchievementCompleted(AchievementDefinition achievement)
	{
		if (achievement == null || string.IsNullOrEmpty(achievement.Id))
		{
			return false;
		}
		EnsureInitialized();
		return _unlockedIds.Contains(achievement.Id);
	}

	public bool IncrementStatistic(string statisticId, int increment)
	{
		if (string.IsNullOrEmpty(statisticId) || increment <= 0)
		{
			return false;
		}
		EnsureInitialized();
		_statistics.TryGetValue(statisticId, out int current);
		long updated = (long)current + increment;
		_statistics[statisticId] = (updated > int.MaxValue) ? int.MaxValue : (int)updated;
		SaveToDisk();
		return true;
	}

	public int GetStatistic(string statisticId)
	{
		EnsureInitialized();
		return _statistics.TryGetValue(statisticId, out int val) ? val : 0;
	}

	private void EnsureInitialized()
	{
		if (!_initialized)
		{
			OnAppStart();
		}
	}

	private void LoadFromDisk()
	{
		try
		{
			string path = _saveFilePath;
			if (!File.Exists(path))
			{
				if (File.Exists(path + ".bak"))
				{
					path = path + ".bak";
				}
				else
				{
					return;
				}
			}
			string content = File.ReadAllText(path, Encoding.UTF8);
			foreach (string rawLine in content.Split('\n'))
			{
				string line = rawLine.Trim();
				if (line.StartsWith("UNLOCK:", StringComparison.Ordinal))
				{
					string id = line.Substring("UNLOCK:".Length).Trim();
					if (!string.IsNullOrEmpty(id))
					{
						_unlockedIds.Add(id);
					}
				}
				else if (line.StartsWith("STAT:", StringComparison.Ordinal))
				{
					string rest = line.Substring("STAT:".Length);
					int eq = rest.LastIndexOf('=');
					if (eq > 0 && int.TryParse(rest.Substring(eq + 1), out int val))
					{
						_statistics[rest.Substring(0, eq)] = val;
					}
				}
			}
		}
		catch (Exception)
		{
		}
	}

	private void SaveToDisk()
	{
		try
		{
			StringBuilder sb = new StringBuilder();
			foreach (string id in _unlockedIds)
			{
				sb.Append("UNLOCK:").Append(id).Append('\n');
			}
			foreach (KeyValuePair<string, int> kv in _statistics)
			{
				sb.Append("STAT:").Append(kv.Key).Append('=').Append(kv.Value).Append('\n');
			}
			byte[] bytes = Encoding.UTF8.GetBytes(sb.ToString());
			AndroidAtomicFileStorage.AtomicWrite(_saveFilePath, bytes);
		}
		catch (Exception)
		{
		}
	}

	private static void TryReportToPlatform(string achievementId)
	{
		try
		{
			Type socialType = Type.GetType("UnityEngine.Social, UnityEngine.CoreModule")
			                  ?? Type.GetType("UnityEngine.Social, UnityEngine.GameCenterModule");
			MethodInfo reportMethod = socialType?.GetMethod("ReportProgress", BindingFlags.Public | BindingFlags.Static);
			if (reportMethod != null)
			{
				Action<bool> callback = delegate { };
				reportMethod.Invoke(null, new object[] { achievementId, 100.0, callback });
			}
		}
		catch (Exception)
		{
		}
	}
}

public sealed class AndroidAchievementToastOverlay : MonoBehaviour
{
	private static AndroidAchievementToastOverlay _instance;
	private static readonly Queue<string> _pendingToasts = new Queue<string>();

	private string _currentToastText;
	private float _toastTimer;
	private const float ToastDurationSeconds = 3.5f;

	public static void EnsureInstance()
	{
		if (_instance != null)
		{
			return;
		}
		GameObject go = new GameObject("AndroidAchievementToastOverlay");
		DontDestroyOnLoad(go);
		_instance = go.AddComponent<AndroidAchievementToastOverlay>();
	}

	public static void EnqueueToast(string achievementId)
	{
		EnsureInstance();
		_pendingToasts.Enqueue(FormatAchievementTitle(achievementId));
	}

	private void Update()
	{
		if (_toastTimer > 0f)
		{
			_toastTimer -= Time.unscaledDeltaTime;
			if (_toastTimer <= 0f)
			{
				_currentToastText = null;
			}
		}
		if (_currentToastText == null && _pendingToasts.Count > 0)
		{
			_currentToastText = _pendingToasts.Dequeue();
			_toastTimer = ToastDurationSeconds;
		}
	}

	private void OnGUI()
	{
		if (string.IsNullOrEmpty(_currentToastText))
		{
			return;
		}
		Rect safe = Screen.safeArea;
		if (safe.width <= 0f || safe.height <= 0f)
		{
			safe = new Rect(0f, 0f, Screen.width, Screen.height);
		}
		float scale = Mathf.Clamp(Screen.height / 1080f, 0.75f, 2.0f);
		float width = 420f * scale;
		float height = 64f * scale;
		float x = safe.x + (safe.width - width) * 0.5f;
		float y = safe.y + 18f * scale;

		GUIStyle boxStyle = new GUIStyle(GUI.skin.box)
		{
			alignment = TextAnchor.MiddleCenter,
			fontSize = Mathf.RoundToInt(22f * scale),
			fontStyle = FontStyle.Bold
		};
		boxStyle.normal.textColor = Color.white;
		GUI.Box(new Rect(x, y, width, height), new GUIContent("Achievement Unlocked: " + _currentToastText), boxStyle);
	}

	private static string FormatAchievementTitle(string rawId)
	{
		if (string.IsNullOrEmpty(rawId))
		{
			return "Achievement";
		}
		return rawId.Replace('_', ' ');
	}
}
