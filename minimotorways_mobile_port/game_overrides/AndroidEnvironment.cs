using System.Collections.Generic;
using Factory;
using Factory.Allocators;
using Helpers.GameCenter;
using Motorways.Leaderboards;
using Motorways.Leaderboards.Backends;
using NotificationService.Persistence;
using Notifications;
using Notifications.Services;
using UnityEngine;

public class AndroidEnvironment : IEnvironment
{
	private const float TabletMinDiagonalInches = 7.0f;
	private const float PhoneMinAspectRatio = 1.85f;
	private const float DefaultAndroidDpi = 407f; // Samsung Galaxy A72 (2400x1080 @ 6.7") is ~394-407 PPI

	public DeviceCategory DeviceCategory
	{
		get
		{
			if (FeatureToggle.IsFeatureEnabled(Feature.MockPhone))
			{
				return DeviceCategory.Phone;
			}
			int width = Mathf.Max(Screen.width, Screen.height);
			int height = Mathf.Min(Screen.width, Screen.height);
			float aspect = (height > 0) ? ((float)width / (float)height) : 1.7777778f;

			// Ultra-wide screens (18.5:9, 19.5:9, 20:9 like Samsung Galaxy A72 2400x1080) use the Phone UI layout
			if (aspect >= PhoneMinAspectRatio)
			{
				return DeviceCategory.Phone;
			}

			float dpi = (Screen.dpi > 20f && Screen.dpi < 1000f) ? Screen.dpi : DefaultAndroidDpi;
			float widthInches = (float)width / dpi;
			float heightInches = (float)height / dpi;
			float diagonalInches = Mathf.Sqrt(widthInches * widthInches + heightInches * heightInches);

			return (diagonalInches >= TabletMinDiagonalInches) ? DeviceCategory.Tablet : DeviceCategory.Phone;
		}
	}

	public List<string> FeatureConfigs => new List<string> { "AndroidConfig", "ArcadeConfig" };

	public BaseInputOverride AddInputOverrideToGameObject(GameObject gameObject)
	{
		return gameObject.AddComponent<BaseInputOverride>();
	}

	public void PopulateAppAssembler(Assembler baseAssembler)
	{
		baseAssembler.Register<IGameCenterAuthentication, NullGameCenterAuthentication>().Allocator(new HeapAllocator<NullGameCenterAuthentication>()).Binding(Binding.Scope);
		baseAssembler.Register<IGameCenterAccessPoint, NullGameCenterAccessPoint>().Allocator(new HeapAllocator<NullGameCenterAccessPoint>()).Binding(Binding.Scope);
		baseAssembler.Register<IAchievementHandler, AndroidAchievementHandler>().Allocator(new HeapAllocator<AndroidAchievementHandler>()).Binding(Binding.Scope);
		baseAssembler.Register<ILeaderboardBackend, NullLeaderboardBackend>().Allocator(new HeapAllocator<NullLeaderboardBackend>()).Binding(Binding.Scope);
		baseAssembler.Register<IHistogramBackend, NullHistogramBackend>().Allocator(new HeapAllocator<NullHistogramBackend>()).Binding(Binding.Scope);
		baseAssembler.Register<IPersistentStorageProvider, AndroidAtomicFileStorage>().Allocator(new HeapAllocator<AndroidAtomicFileStorage>()).Binding(Binding.Scope);
		baseAssembler.Register<IContentProfile, RetailContentProfile>().Allocator(new HeapAllocator<RetailContentProfile>()).Binding(Binding.Scope);
		baseAssembler.Register<IHardwareCapabilities, AndroidHardwareCapabilities>().Allocator(new HeapAllocator<AndroidHardwareCapabilities>()).Binding(Binding.Scope);
		baseAssembler.Register<IReachability, AndroidReachability>().Allocator(new HeapAllocator<AndroidReachability>()).Binding(Binding.Scope);
		baseAssembler.Register<ISoftwareCapabilities, AndroidSoftwareCapabilities>().Allocator(new HeapAllocator<AndroidSoftwareCapabilities>()).Binding(Binding.Scope);
		baseAssembler.Register<IControllerButtonToSymbolService, DefaultControllerButtonToSymbolService>().Allocator(new HeapAllocator<DefaultControllerButtonToSymbolService>()).Binding(Binding.Scope);
		baseAssembler.Register<ISystemNotificationService, NullSystemNotificationService>().Allocator(new HeapAllocator<NullSystemNotificationService>()).Binding(Binding.Scope);
		baseAssembler.Register<INotificationEventSystem, NotificationEventSystem>().Allocator(new HeapAllocator<NotificationEventSystem>()).Binding(Binding.Scope);
		baseAssembler.Register<INotificationEventPersistence, ActivePlayerNotificationEventPersistence>().Allocator(new HeapAllocator<ActivePlayerNotificationEventPersistence>()).Binding(Binding.Scope);
		baseAssembler.Register<INotificationScheduleDebugger, NullNotificationScheduleDebugger>().Allocator(new HeapAllocator<NullNotificationScheduleDebugger>()).Binding(Binding.Scope);
		baseAssembler.Register<IFileSystem, DefaultFileSystem>().Allocator(new HeapAllocator<DefaultFileSystem>()).Binding(Binding.Scope);
		baseAssembler.Register<ISteamCloudSyncService, NullSteamCloudSyncService>().Allocator(new HeapAllocator<NullSteamCloudSyncService>()).Binding(Binding.Scope);
	}

	public void PopulateGameAssembler(Assembler baseAssembler)
	{
	}
}
