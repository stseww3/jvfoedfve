using System;
using System.IO;
using UnityEngine;
using UnityEngine.Networking;

/// <summary>
/// Adaptive SafeArea, Screen Scaling (specifically targeting Samsung Galaxy A72 2400x1080 20:9
/// punch-hole cutout & 407 PPI display), and Android APK StreamingAssets loader.
///
/// Key fixes for CleanScenes_Resources_NoSource.zip on Android:
///   1. SafeArea sanitizes invalid/off-screen rects and supports symmetric horizontal insets
///      in landscape so the Samsung Galaxy A72 punch-hole camera cutout never clips HUD buttons
///      or shifts centered menus when rotating between Landscape Left and Landscape Right.
///   2. AndroidStreamingAssetsLoader loads StreamingAssets/Sounds/48000/core.bytes from inside
///      the Android APK ("jar:file:///.../base.apk!/assets/...") via UnityWebRequest where
///      File.ReadAllBytes would throw DirectoryNotFoundException.
///   3. AudioDatabase fallback automatically selects the 48000 Hz sound bank when the 24000 Hz
///      bank is absent (as in CleanScenes_Resources_NoSource.zip).
/// </summary>
[ExecuteAlways]
[RequireComponent(typeof(RectTransform))]
public class SafeArea : MonoBehaviour
{
	private RectTransform _panel;
	private Rect _lastSafeArea = new Rect(0f, 0f, 0f, 0f);
	private Vector2Int _lastScreenSize = Vector2Int.zero;
	private ScreenOrientation _lastOrientation = ScreenOrientation.Unknown;

	[SerializeField]
	private bool _conformX = true;

	[SerializeField]
	private bool _conformY = true;

	[SerializeField]
	private bool _symmetricHorizontalInsets = true;

	private void OnEnable()
	{
		_panel = GetComponent<RectTransform>();
		if (_panel == null)
		{
			Destroy(base.gameObject);
			return;
		}
		Refresh();
	}

	public void Update()
	{
		Refresh();
	}

	private void Refresh()
	{
		int sw = Screen.width;
		int sh = Screen.height;
		if (sw <= 0 || sh <= 0)
		{
			return;
		}
		Rect safeArea = SanitizeSafeArea(Screen.safeArea, sw, sh);
		Vector2Int screenSize = new Vector2Int(sw, sh);
		if (safeArea != _lastSafeArea || screenSize != _lastScreenSize || Screen.orientation != _lastOrientation)
		{
			_lastSafeArea = safeArea;
			_lastScreenSize = screenSize;
			_lastOrientation = Screen.orientation;
			ApplySafeArea(safeArea, sw, sh);
		}
	}

	public static Rect SanitizeSafeArea(Rect rawSafe, int screenWidth, int screenHeight)
	{
		if (screenWidth <= 0 || screenHeight <= 0)
		{
			return new Rect(0f, 0f, 0f, 0f);
		}
		if (float.IsNaN(rawSafe.x) || float.IsNaN(rawSafe.y) ||
		    float.IsNaN(rawSafe.width) || float.IsNaN(rawSafe.height) ||
		    rawSafe.width <= 0f || rawSafe.height <= 0f)
		{
			return new Rect(0f, 0f, screenWidth, screenHeight);
		}
		float xMin = Mathf.Clamp(rawSafe.xMin, 0f, screenWidth);
		float yMin = Mathf.Clamp(rawSafe.yMin, 0f, screenHeight);
		float xMax = Mathf.Clamp(rawSafe.xMax, xMin, screenWidth);
		float yMax = Mathf.Clamp(rawSafe.yMax, yMin, screenHeight);
		if (xMax - xMin <= 0f || yMax - yMin <= 0f)
		{
			return new Rect(0f, 0f, screenWidth, screenHeight);
		}
		return Rect.MinMaxRect(xMin, yMin, xMax, yMax);
	}

	private void ApplySafeArea(Rect r, int screenWidth, int screenHeight)
	{
		if (!_conformX)
		{
			r.x = 0f;
			r.width = screenWidth;
		}
		else if (_symmetricHorizontalInsets)
		{
			float leftInset = r.xMin;
			float rightInset = screenWidth - r.xMax;
			float maxHorizontalInset = Mathf.Max(leftInset, rightInset);
			if (screenWidth - 2f * maxHorizontalInset > screenWidth * 0.5f)
			{
				r.xMin = maxHorizontalInset;
				r.xMax = screenWidth - maxHorizontalInset;
			}
		}

		if (!_conformY)
		{
			r.y = 0f;
			r.height = screenHeight;
		}

		Vector2 anchorMin = new Vector2(r.xMin / screenWidth, r.yMin / screenHeight);
		Vector2 anchorMax = new Vector2(r.xMax / screenWidth, r.yMax / screenHeight);
		_panel.anchorMin = anchorMin;
		_panel.anchorMax = anchorMax;
	}
}

public static class AndroidStreamingAssetsLoader
{
	public static byte[] ReadAllBytes(string path)
	{
		if (string.IsNullOrEmpty(path))
		{
			return null;
		}
		if (path.Contains("://") || path.Contains(":///"))
		{
			using UnityWebRequest req = UnityWebRequest.Get(path);
			UnityWebRequestAsyncOperation op = req.SendWebRequest();
			while (!op.isDone)
			{
			}
			if (req.result != UnityWebRequest.Result.Success)
			{
				return null;
			}
			return req.downloadHandler.data;
		}
		return File.Exists(path) ? File.ReadAllBytes(path) : null;
	}

	public static bool SoundBankExists(int frequency, string bankId = "core")
	{
		string path = Path.Combine(Application.streamingAssetsPath, "Sounds", frequency.ToString(), bankId + ".bytes");
		if (path.Contains("://") || path.Contains(":///"))
		{
			byte[] bytes = ReadAllBytes(path);
			return bytes != null && bytes.Length > 0;
		}
		return File.Exists(path);
	}
}
