namespace UnityMobileKit.Persistence
{
    /// <summary>Something that can be flushed to storage when the app is about to be suspended.</summary>
    public interface ISaveable
    {
        bool HasUnsavedChanges { get; }

        void Save();
    }
}
