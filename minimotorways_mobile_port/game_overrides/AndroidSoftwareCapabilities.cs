using System;
using System.Collections.Generic;
using System.IO;
using Factory;
using JetBrains.Annotations;
using UnityEngine;

public class AndroidSoftwareCapabilities : ISoftwareCapabilities
{
	[Dependency]
	protected IHardwareCapabilities _hardwareCapabilities;

	public LocaleDatabase.LocaleId PreferredLocaleId => _hardwareCapabilities.PreferredLocaleId;

	public bool SupportsCloudSaves => false;

	public bool CanShareImage => true;

	public Vector2Int ScreenshotDimensions => new Vector2Int(Screen.width, Screen.height);

	public bool SupportsHighDPI => false;

	public bool SupportsMultipleProfiles => true;

	public bool SupportsMovieScreen => false;

	public bool SupportsDisplayOptions => false;

	public StringId DeleteCloudGameStringId => StringId.DeleteSpecificJournalPrompt_Steam;

	public bool SupportsEvergreenButton => true;

	public StringId TenYearCelebrationPopupBody => StringId.Popup_Body_CrossPromo_AuroraBorealis;

	public string TenYearCelebrationMiniMetroStoreLink => "https://play.google.com/store/apps/details?id=nz.co.codepoint.minimetro";

	public void SetIsInMainMenuScreen(bool isInMainMenuScreen)
	{
	}

	public void SetIsInGame(bool isInGame)
	{
	}

	public virtual void OnAppStart()
	{
	}

	public void OnAppShutdown()
	{
	}

	public bool SaveScreenshot(Texture2D screenshot, string tag, string parentFolder, out StringId messageId)
	{
		messageId = StringId.None;
		try
		{
			byte[] pngBytes = screenshot.EncodeToPNG();
			string dir = Path.Combine(Application.persistentDataPath, "Screenshots");
			Directory.CreateDirectory(dir);
			string filename = $"MiniMotorways_{tag}_{DateTime.UtcNow:yyyyMMdd_HHmmss}.png";
			File.WriteAllBytes(Path.Combine(dir, filename), pngBytes);
			return true;
		}
		catch (Exception)
		{
			return false;
		}
	}

	public bool SaveGif(byte[] data, string tag, string parentFolder, out StringId messageId, out StringId messageHeaderId)
	{
		messageId = StringId.None;
		messageHeaderId = StringId.None;
		return false;
	}

	public void SetRichPresence(Dictionary<string, string> tokens)
	{
	}

	public bool AllowsTimedChallengeMessages()
	{
		return true;
	}
}

public class AndroidReachability : IReachability
{
	private InternetConnectivity _lastConnectivity = InternetConnectivity.Unknown;

	public InternetConnectivity Connectivity
	{
		get
		{
			NetworkReachability current = Application.internetReachability;
			InternetConnectivity mapped = (current == NetworkReachability.NotReachable)
				? InternetConnectivity.Disconnected
				: InternetConnectivity.Connected;
			if (mapped != _lastConnectivity)
			{
				_lastConnectivity = mapped;
				ConnectivityChanged?.Invoke(mapped);
			}
			return mapped;
		}
	}

	public bool CanConnectManually => false;

	public event Action<InternetConnectivity> ConnectivityChanged;

	public void OpenSilentConnection([NotNull] IReachability.ConnectionOpened connectionOpened)
	{
		connectionOpened?.Invoke(new InternetConnectionHandle(this));
	}

	public void OpenManualConnection([NotNull] IReachability.ConnectionOpened connectionOpened)
	{
		connectionOpened?.Invoke(new InternetConnectionHandle(this));
	}

	public void CloseConnection([NotNull] InternetConnectionHandle handle)
	{
	}
}

public class NullSteamCloudSyncService : ISteamCloudSyncService
{
	public bool IsSupported => false;

	public AsyncRequestHandle Authenticate([NotNull] SteamCloudAuthenticationCompleted authenticationCompleted)
	{
		authenticationCompleted?.Invoke(SteamCloudSyncError.NotSupported, null);
		return AsyncRequestHandle.CompletedRequestHandle;
	}

	public AsyncRequestHandle DownloadProfiles([NotNull] string accessToken, [NotNull] SteamCloudProfileDownloadCompleted downloadCompleted)
	{
		downloadCompleted?.Invoke(SteamCloudSyncError.NotSupported, null, null);
		return AsyncRequestHandle.CompletedRequestHandle;
	}
}
