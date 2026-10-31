namespace UnityMobileKit.Tests
{
    public static class Program
    {
        public static int Main()
        {
            AtomicFileStoreTests.Register();
            AchievementTrackerTests.Register();
            return TestHarness.RunAll();
        }
    }
}
