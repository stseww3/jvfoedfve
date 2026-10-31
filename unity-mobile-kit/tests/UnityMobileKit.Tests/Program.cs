namespace UnityMobileKit.Tests
{
    public static class Program
    {
        public static int Main()
        {
            AtomicFileStoreTests.Register();
            AchievementTrackerTests.Register();
            SettingsTests.Register();
            GestureTests.Register();
            CameraTests.Register();
            ControllerTests.Register();
            PlatformTests.Register();
            return TestHarness.RunAll();
        }
    }
}
