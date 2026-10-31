using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;

/// <summary>
/// Crash-safe JSON saves in Application.persistentDataPath.
/// Every write goes to "slot.json.tmp" first and is only moved into place once it is fully on disk, the
/// previous save is kept as "slot.json.bak", and a checksum rejects files that were cut off mid-write.
/// If the app is killed at any point during a save, the next load still finds a complete file.
/// </summary>
public static class SaveSystem
{
    [Serializable]
    class Envelope
    {
        public int version;
        public string checksum;
        public string payload;
    }

    public static string PathFor(string slot) => Path.Combine(Application.persistentDataPath, slot + ".json");

    /// <summary>
    /// Writes <paramref name="data"/> (any [Serializable] class JsonUtility can handle) to the slot.
    /// Bump <paramref name="version"/> whenever the data layout changes so loads can migrate old saves.
    /// </summary>
    public static void Save<T>(string slot, T data, int version = 1)
    {
        string path = PathFor(slot);
        string tempPath = path + ".tmp";
        string backupPath = path + ".bak";

        string payload = JsonUtility.ToJson(data);
        var envelope = new Envelope { version = version, checksum = Hash(payload), payload = payload };
        byte[] bytes = Encoding.UTF8.GetBytes(JsonUtility.ToJson(envelope));

        using (var stream = new FileStream(tempPath, FileMode.Create, FileAccess.Write, FileShare.None))
        {
            stream.Write(bytes, 0, bytes.Length);
            stream.Flush(true);
        }

        // File.Move is a single rename() on Android, so each step is atomic; Load() also checks .tmp
        // in case the app dies between the two moves.
        if (File.Exists(path))
        {
            if (File.Exists(backupPath))
                File.Delete(backupPath);
            File.Move(path, backupPath);
        }
        File.Move(tempPath, path);
    }

    public static bool TryLoad<T>(string slot, out T data)
    {
        return TryLoad(slot, out data, out _);
    }

    /// <summary>Loads the newest intact copy of the slot. <paramref name="version"/> is the value passed to Save.</summary>
    public static bool TryLoad<T>(string slot, out T data, out int version)
    {
        string path = PathFor(slot);
        foreach (string candidate in new[] { path, path + ".tmp", path + ".bak" })
        {
            if (TryRead(candidate, out data, out version))
                return true;
        }
        data = default;
        version = 0;
        return false;
    }

    public static bool Exists(string slot)
    {
        string path = PathFor(slot);
        return File.Exists(path) || File.Exists(path + ".tmp") || File.Exists(path + ".bak");
    }

    public static void Delete(string slot)
    {
        string path = PathFor(slot);
        foreach (string file in new[] { path, path + ".tmp", path + ".bak" })
        {
            if (File.Exists(file))
                File.Delete(file);
        }
    }

    static bool TryRead<T>(string file, out T data, out int version)
    {
        data = default;
        version = 0;
        try
        {
            if (!File.Exists(file))
                return false;
            var envelope = JsonUtility.FromJson<Envelope>(File.ReadAllText(file, Encoding.UTF8));
            if (envelope == null || envelope.payload == null || envelope.checksum != Hash(envelope.payload))
                return false;
            data = JsonUtility.FromJson<T>(envelope.payload);
            version = envelope.version;
            return data != null;
        }
        catch (Exception e)
        {
            Debug.LogWarning($"Skipping unreadable save file {file}: {e.Message}");
            return false;
        }
    }

    static string Hash(string text)
    {
        using (var sha = SHA256.Create())
            return Convert.ToBase64String(sha.ComputeHash(Encoding.UTF8.GetBytes(text)));
    }
}
