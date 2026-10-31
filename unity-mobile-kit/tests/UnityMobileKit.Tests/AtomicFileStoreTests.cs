using System;
using System.IO;
using System.Linq;
using System.Text;
using UnityMobileKit.Persistence;

namespace UnityMobileKit.Tests
{
    public static class AtomicFileStoreTests
    {
        private static byte[] Utf8(string s) => Encoding.UTF8.GetBytes(s);

        private static void FlipByte(string path, int indexFromEnd)
        {
            byte[] bytes = File.ReadAllBytes(path);
            bytes[bytes.Length - indexFromEnd] ^= 0xFF;
            File.WriteAllBytes(path, bytes);
        }

        public static void Register()
        {
            TestHarness.Add("Crc32 matches the standard check value", _ =>
            {
                Assert.Equal(0xCBF43926u, Crc32.Compute(Encoding.ASCII.GetBytes("123456789")), "CRC-32(\"123456789\")");
            });

            TestHarness.Add("Save then load returns the same bytes from the primary copy", dir =>
            {
                var store = new AtomicFileStore(dir);
                store.Save("profile", Utf8("level=3"));
                Assert.Equal(SaveLoadResult.LoadedPrimary, store.TryLoad("profile", out var data), "result");
                Assert.Bytes(Utf8("level=3"), data, "payload");
            });

            TestHarness.Add("Empty payload round-trips", dir =>
            {
                var store = new AtomicFileStore(dir);
                store.Save("empty", new byte[0]);
                Assert.Equal(SaveLoadResult.LoadedPrimary, store.TryLoad("empty", out var data), "result");
                Assert.Equal(0, data.Length, "length");
            });

            TestHarness.Add("1 MB random payload round-trips", dir =>
            {
                var store = new AtomicFileStore(dir);
                var payload = new byte[1 << 20];
                new Random(1234).NextBytes(payload);
                store.Save("big", payload);
                Assert.Equal(SaveLoadResult.LoadedPrimary, store.TryLoad("big", out var data), "result");
                Assert.Bytes(payload, data, "payload");
            });

            TestHarness.Add("Missing key reports NotFound", dir =>
            {
                var store = new AtomicFileStore(dir);
                Assert.Equal(SaveLoadResult.NotFound, store.TryLoad("nothing", out var data), "result");
                Assert.True(data == null, "data should be null");
                Assert.True(!store.Exists("nothing"), "Exists should be false");
            });

            TestHarness.Add("Overwrite returns the newest data", dir =>
            {
                var store = new AtomicFileStore(dir);
                store.Save("s", Utf8("A"));
                store.Save("s", Utf8("B"));
                Assert.Equal(SaveLoadResult.LoadedPrimary, store.TryLoad("s", out var data), "result");
                Assert.Bytes(Utf8("B"), data, "payload");
            });

            TestHarness.Add("Damaged primary falls back to the previous good copy", dir =>
            {
                var store = new AtomicFileStore(dir);
                store.Save("s", Utf8("A"));
                store.Save("s", Utf8("B"));
                FlipByte(store.GetPrimaryPath("s"), 1);
                Assert.Equal(SaveLoadResult.LoadedBackup, store.TryLoad("s", out var data), "result");
                Assert.Bytes(Utf8("A"), data, "payload");
            });

            TestHarness.Add("Truncated primary (torn write) falls back to backup", dir =>
            {
                var store = new AtomicFileStore(dir);
                store.Save("s", Utf8("first save"));
                store.Save("s", Utf8("second save"));
                using (var fs = new FileStream(store.GetPrimaryPath("s"), FileMode.Open)) fs.SetLength(5);
                Assert.Equal(SaveLoadResult.LoadedBackup, store.TryLoad("s", out var data), "result");
                Assert.Bytes(Utf8("first save"), data, "payload");
            });

            TestHarness.Add("Header with wrong length is rejected even if bytes look plausible", dir =>
            {
                var store = new AtomicFileStore(dir);
                store.Save("s", Utf8("A"));
                store.Save("s", Utf8("BB"));
                File.AppendAllText(store.GetPrimaryPath("s"), "extra");
                Assert.Equal(SaveLoadResult.LoadedBackup, store.TryLoad("s", out var data), "result");
                Assert.Bytes(Utf8("A"), data, "payload");
            });

            TestHarness.Add("Only damaged copies reports Corrupt", dir =>
            {
                var store = new AtomicFileStore(dir);
                store.Save("s", Utf8("only copy"));
                FlipByte(store.GetPrimaryPath("s"), 2);
                Assert.Equal(SaveLoadResult.Corrupt, store.TryLoad("s", out var data), "result");
                Assert.True(data == null, "data should be null");
            });

            TestHarness.Add("Saving over a damaged primary keeps the last good backup", dir =>
            {
                var store = new AtomicFileStore(dir);
                store.Save("s", Utf8("A"));
                store.Save("s", Utf8("B"));             // backup = A
                FlipByte(store.GetPrimaryPath("s"), 1); // primary (B) damaged on disk
                store.Save("s", Utf8("C"));             // must not rotate damaged B into backup
                Assert.Equal(SaveLoadResult.LoadedPrimary, store.TryLoad("s", out var now), "after save");
                Assert.Bytes(Utf8("C"), now, "current");
                FlipByte(store.GetPrimaryPath("s"), 1);
                Assert.Equal(SaveLoadResult.LoadedBackup, store.TryLoad("s", out var old), "backup result");
                Assert.Bytes(Utf8("A"), old, "backup is still the last good copy");
            });

            TestHarness.Add("Crash between moving old copy aside and committing new one recovers the new data", dir =>
            {
                var store = new AtomicFileStore(dir);
                store.Save("s", Utf8("old"));
                store.Save("scratch", Utf8("new"));
                // Reproduce the fallback-path window: complete temp copy present, primary gone.
                File.Copy(store.GetPrimaryPath("scratch"), store.GetTempPath("s"), overwrite: true);
                File.Copy(store.GetPrimaryPath("s"), store.GetBackupPath("s"), overwrite: true);
                File.Delete(store.GetPrimaryPath("s"));
                Assert.Equal(SaveLoadResult.LoadedPrimary, store.TryLoad("s", out var data), "result");
                Assert.Bytes(Utf8("new"), data, "payload");
            });

            TestHarness.Add("Crash during temp write (torn temp) is ignored; committed data still loads", dir =>
            {
                var store = new AtomicFileStore(dir);
                store.Save("s", Utf8("committed"));
                File.WriteAllBytes(store.GetTempPath("s"), new byte[] { 0x55, 0x4D, 0x4B });
                Assert.Equal(SaveLoadResult.LoadedPrimary, store.TryLoad("s", out var data), "result");
                Assert.Bytes(Utf8("committed"), data, "payload");
                store.Save("s", Utf8("next"));
                Assert.Equal(SaveLoadResult.LoadedPrimary, store.TryLoad("s", out var after), "after next save");
                Assert.Bytes(Utf8("next"), after, "payload after next save");
            });

            TestHarness.Add("Crash before first commit (complete temp, no primary) still recovers", dir =>
            {
                var store = new AtomicFileStore(dir);
                store.Save("scratch", Utf8("first"));
                File.Copy(store.GetPrimaryPath("scratch"), store.GetTempPath("s"));
                Assert.Equal(SaveLoadResult.LoadedPrimary, store.TryLoad("s", out var data), "result");
                Assert.Bytes(Utf8("first"), data, "payload");
            });

            TestHarness.Add("200 sequential saves leave only .sav and .sav.bak (no temp files)", dir =>
            {
                var store = new AtomicFileStore(dir);
                for (int i = 0; i < 200; i++) store.Save("loop", Utf8("v" + i));
                Assert.Equal(SaveLoadResult.LoadedPrimary, store.TryLoad("loop", out var data), "result");
                Assert.Bytes(Utf8("v199"), data, "payload");
                var names = Directory.GetFiles(dir).Select(Path.GetFileName).OrderBy(n => n).ToArray();
                Assert.Equal("loop.sav|loop.sav.bak", string.Join("|", names), "files on disk");
            });

            TestHarness.Add("Delete removes every copy", dir =>
            {
                var store = new AtomicFileStore(dir);
                store.Save("s", Utf8("A"));
                store.Save("s", Utf8("B"));
                Assert.True(store.Delete("s"), "first delete removes files");
                Assert.True(!store.Exists("s"), "Exists after delete");
                Assert.Equal(SaveLoadResult.NotFound, store.TryLoad("s", out _), "load after delete");
                Assert.True(!store.Delete("s"), "second delete finds nothing");
            });

            TestHarness.Add("Keys that could escape the directory or collide are rejected", dir =>
            {
                var store = new AtomicFileStore(dir);
                foreach (var bad in new[] { "", ".", "..", "a/b", "a\\b", "x y", "../evil", "c:" })
                {
                    Assert.Throws<ArgumentException>(() => store.Save(bad, new byte[1]), $"key '{bad}'");
                }
                Assert.Throws<ArgumentNullException>(() => store.Save("ok", null), "null payload");
            });

            TestHarness.Add("Separate keys are independent", dir =>
            {
                var store = new AtomicFileStore(dir);
                store.Save("settings", Utf8("fps=60"));
                store.Save("profile", Utf8("xp=10"));
                store.Delete("settings");
                Assert.Equal(SaveLoadResult.LoadedPrimary, store.TryLoad("profile", out var data), "profile result");
                Assert.Bytes(Utf8("xp=10"), data, "profile payload");
            });
        }
    }
}
