using System;
using System.IO;

namespace UnityMobileKit.Persistence
{
    /// <summary>
    /// Crash-resistant file-per-key store for mobile, where the OS may kill the process at any
    /// moment (low memory, swipe-away, battery).
    /// <para>
    /// Commit protocol: the framed payload is written to <c>key.sav.tmp</c> and flushed to the
    /// device, then atomically swapped over <c>key.sav</c>; the previous intact copy is kept as
    /// <c>key.sav.bak</c>. A save is committed when the swap completes, so a crash at any point
    /// leaves either the old or the new copy readable, never a half-written one.
    /// </para>
    /// <para>
    /// Every file carries a header (magic, length, CRC-32) so truncated or damaged files are
    /// detected on load instead of being handed to a deserializer.
    /// </para>
    /// </summary>
    public sealed class AtomicFileStore : ISaveStore
    {
        private const uint Magic = 0x314B4D55; // "UMK1" in little-endian byte order
        private const int HeaderSize = 12;      // magic + payload length + CRC-32, 4 bytes each
        private const string Extension = ".sav";

        private readonly string _directory;

        public AtomicFileStore(string directory)
        {
            if (string.IsNullOrEmpty(directory))
            {
                throw new ArgumentException("A storage directory is required.", nameof(directory));
            }
            _directory = directory;
            Directory.CreateDirectory(_directory);
        }

        public string DirectoryPath => _directory;

        public string GetPrimaryPath(string key) => Path.Combine(_directory, ValidateKey(key) + Extension);

        public string GetBackupPath(string key) => GetPrimaryPath(key) + ".bak";

        public string GetTempPath(string key) => GetPrimaryPath(key) + ".tmp";

        public void Save(string key, byte[] data)
        {
            if (data == null)
            {
                throw new ArgumentNullException(nameof(data));
            }

            string primary = GetPrimaryPath(key);
            string backup = GetBackupPath(key);
            string temp = GetTempPath(key);

            WriteDurably(temp, Frame(data));

            if (TryReadValid(primary, out _))
            {
                CommitWithBackup(temp, primary, backup);
            }
            else
            {
                // A damaged primary must not be rotated into the backup slot and overwrite the
                // last good copy, so it is discarded instead.
                if (File.Exists(primary))
                {
                    File.Delete(primary);
                }
                File.Move(temp, primary);
            }
        }

        public SaveLoadResult TryLoad(string key, out byte[] data)
        {
            string primary = GetPrimaryPath(key);
            string backup = GetBackupPath(key);
            string temp = GetTempPath(key);

            if (TryReadValid(primary, out data))
            {
                return SaveLoadResult.LoadedPrimary;
            }

            // Primary missing but a complete temp copy present: the process died between moving
            // the old copy aside and moving the new one into place. The temp copy is the newest data.
            if (!File.Exists(primary) && TryReadValid(temp, out data))
            {
                return SaveLoadResult.LoadedPrimary;
            }

            if (TryReadValid(backup, out data))
            {
                return SaveLoadResult.LoadedBackup;
            }

            data = null;
            return File.Exists(primary) || File.Exists(backup) || File.Exists(temp)
                ? SaveLoadResult.Corrupt
                : SaveLoadResult.NotFound;
        }

        public bool Exists(string key)
        {
            return File.Exists(GetPrimaryPath(key)) || File.Exists(GetBackupPath(key));
        }

        public bool Delete(string key)
        {
            bool removed = false;
            foreach (string path in new[] { GetPrimaryPath(key), GetBackupPath(key), GetTempPath(key) })
            {
                if (File.Exists(path))
                {
                    File.Delete(path);
                    removed = true;
                }
            }
            return removed;
        }

        private static void CommitWithBackup(string temp, string primary, string backup)
        {
            try
            {
                // Atomic on the same volume (rename(2) on Unix, ReplaceFile on Windows).
                File.Replace(temp, primary, backup, ignoreMetadataErrors: true);
            }
            catch (Exception e) when (e is PlatformNotSupportedException || e is IOException || e is UnauthorizedAccessException)
            {
                // Fallback for runtimes without a working File.Replace. There is a short window
                // with no primary file; TryLoad covers it by reading the complete temp copy.
                File.Copy(primary, backup, overwrite: true);
                File.Delete(primary);
                File.Move(temp, primary);
            }
        }

        private static void WriteDurably(string path, byte[] bytes)
        {
            using (var stream = new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.None))
            {
                stream.Write(bytes, 0, bytes.Length);
                stream.Flush(flushToDisk: true);
            }
        }

        private static byte[] Frame(byte[] payload)
        {
            var framed = new byte[HeaderSize + payload.Length];
            WriteUInt32(framed, 0, Magic);
            WriteUInt32(framed, 4, (uint)payload.Length);
            WriteUInt32(framed, 8, Crc32.Compute(payload));
            Buffer.BlockCopy(payload, 0, framed, HeaderSize, payload.Length);
            return framed;
        }

        private static bool TryReadValid(string path, out byte[] payload)
        {
            payload = null;
            if (!File.Exists(path))
            {
                return false;
            }

            byte[] bytes;
            try
            {
                bytes = File.ReadAllBytes(path);
            }
            catch (IOException)
            {
                return false;
            }
            catch (UnauthorizedAccessException)
            {
                return false;
            }

            if (bytes.Length < HeaderSize || ReadUInt32(bytes, 0) != Magic)
            {
                return false;
            }

            uint length = ReadUInt32(bytes, 4);
            if (length != (uint)(bytes.Length - HeaderSize))
            {
                return false;
            }

            if (ReadUInt32(bytes, 8) != Crc32.Compute(bytes, HeaderSize, (int)length))
            {
                return false;
            }

            payload = new byte[length];
            Buffer.BlockCopy(bytes, HeaderSize, payload, 0, (int)length);
            return true;
        }

        private static string ValidateKey(string key)
        {
            if (string.IsNullOrEmpty(key) || key == "." || key == "..")
            {
                throw new ArgumentException("Key must be a non-empty file-name-safe string.", nameof(key));
            }
            foreach (char c in key)
            {
                bool ok = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')
                          || c == '_' || c == '-' || c == '.';
                if (!ok)
                {
                    throw new ArgumentException($"Key '{key}' may only contain letters, digits, '_', '-' and '.'.", nameof(key));
                }
            }
            return key;
        }

        private static void WriteUInt32(byte[] buffer, int offset, uint value)
        {
            buffer[offset] = (byte)value;
            buffer[offset + 1] = (byte)(value >> 8);
            buffer[offset + 2] = (byte)(value >> 16);
            buffer[offset + 3] = (byte)(value >> 24);
        }

        private static uint ReadUInt32(byte[] buffer, int offset)
        {
            return buffer[offset]
                   | ((uint)buffer[offset + 1] << 8)
                   | ((uint)buffer[offset + 2] << 16)
                   | ((uint)buffer[offset + 3] << 24);
        }
    }
}
