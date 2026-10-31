namespace UnityMobileKit.Persistence
{
    public enum SaveLoadResult
    {
        /// <summary>No primary or backup copy exists.</summary>
        NotFound,

        /// <summary>The primary copy was intact and returned.</summary>
        LoadedPrimary,

        /// <summary>The primary copy was missing or damaged; the previous good copy was returned.</summary>
        LoadedBackup,

        /// <summary>Copies exist but none passed the integrity check.</summary>
        Corrupt,
    }

    /// <summary>Key/value persistence of opaque byte payloads.</summary>
    public interface ISaveStore
    {
        void Save(string key, byte[] data);

        SaveLoadResult TryLoad(string key, out byte[] data);

        bool Exists(string key);

        /// <summary>Removes the primary and backup copies. Returns true if anything was removed.</summary>
        bool Delete(string key);
    }
}
