using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityMobileKit.Persistence;
using UnityMobileKit.Settings;

namespace UnityMobileKit.Tests
{
    public static class SettingsTests
    {
        private sealed class MemoryStore : ISaveStore
        {
            private readonly Dictionary<string, byte[]> _data = new Dictionary<string, byte[]>();

            public int SaveCount { get; private set; }

            public void Save(string key, byte[] data)
            {
                _data[key] = (byte[])data.Clone();
                SaveCount++;
            }

            public SaveLoadResult TryLoad(string key, out byte[] data)
            {
                bool found = _data.TryGetValue(key, out var stored);
                data = found ? (byte[])stored.Clone() : null;
                return found ? SaveLoadResult.LoadedPrimary : SaveLoadResult.NotFound;
            }

            public bool Exists(string key) => _data.ContainsKey(key);

            public bool Delete(string key) => _data.Remove(key);
        }

        private static PreferenceStore RoundTrip(PreferenceStore prefs)
        {
            var copy = new PreferenceStore();
            Assert.True(copy.TryDeserialize(prefs.Serialize()), "deserialize own output");
            return copy;
        }

        public static void Register()
        {
            TestHarness.Add("Frame-rate modes resolve to 30, 60, or the display's rate", _ =>
            {
                Assert.Equal(30, FrameRate.Resolve(FrameRateMode.Fps30, 120), "Fps30 on 120 Hz");
                Assert.Equal(60, FrameRate.Resolve(FrameRateMode.Fps60, 120), "Fps60 on 120 Hz");
                Assert.Equal(120, FrameRate.Resolve(FrameRateMode.Auto, 120), "Auto on 120 Hz");
                Assert.Equal(90, FrameRate.Resolve(FrameRateMode.Auto, 90), "Auto on 90 Hz");
                Assert.Equal(60, FrameRate.Resolve(FrameRateMode.Auto, 0), "Auto with unknown rate");
                Assert.Equal(60, FrameRate.Resolve(FrameRateMode.Auto, -1), "Auto with invalid rate");
                Assert.Throws<ArgumentOutOfRangeException>(() => FrameRate.Resolve((FrameRateMode)7, 60), "undefined mode");
            });

            TestHarness.Add("Preferences of every type round-trip, including edge values", _ =>
            {
                var prefs = new PreferenceStore();
                prefs.SetBool("on", true);
                prefs.SetBool("off", false);
                prefs.SetInt("min", int.MinValue);
                prefs.SetInt("max", int.MaxValue);
                prefs.SetFloat("tenth", 0.1f);
                prefs.SetFloat("tiny", float.Epsilon);
                prefs.SetFloat("huge", -float.MaxValue);
                prefs.SetString("empty", "");
                prefs.SetString("tricky", "tab\there\nnew line\r\\ back\\slash \\t literal ü 漢字 🚗 \\");

                var copy = RoundTrip(prefs);
                Assert.Equal(9, copy.Count, "count");
                Assert.True(copy.GetBool("on") && !copy.GetBool("off", true), "bools");
                Assert.Equal(int.MinValue, copy.GetInt("min"), "int min");
                Assert.Equal(int.MaxValue, copy.GetInt("max"), "int max");
                Assert.Equal(0.1f, copy.GetFloat("tenth"), "0.1f exact");
                Assert.Equal(float.Epsilon, copy.GetFloat("tiny"), "epsilon exact");
                Assert.Equal(-float.MaxValue, copy.GetFloat("huge"), "-max exact");
                Assert.Equal("", copy.GetString("empty", "default"), "empty string is a value, not missing");
                Assert.Equal(prefs.GetString("tricky"), copy.GetString("tricky"), "escaped string");
            });

            TestHarness.Add("Numbers are stored the same on a decimal-comma device locale", _ =>
            {
                var original = CultureInfo.CurrentCulture;
                try
                {
                    CultureInfo.CurrentCulture = new CultureInfo("de-DE");
                    Assert.Equal("0,35", 0.35f.ToString(), "precondition: German formatting active");

                    var prefs = new PreferenceStore();
                    prefs.SetFloat("volume", 0.35f);
                    prefs.SetInt("offset", -1200);
                    string text = Encoding.UTF8.GetString(prefs.Serialize());
                    Assert.True(text.Contains("\t0.35\n") && text.Contains("\t-1200\n"), "invariant text: " + text.Replace("\n", "\\n"));

                    var copy = RoundTrip(prefs);
                    Assert.Equal(0.35f, copy.GetFloat("volume"), "float");
                    Assert.Equal(-1200, copy.GetInt("offset"), "int");
                }
                finally
                {
                    CultureInfo.CurrentCulture = original;
                }
            });

            TestHarness.Add("Keys containing backslashes round-trip", _ =>
            {
                var prefs = new PreferenceStore();
                prefs.SetInt(@"a\b", 1);
                prefs.SetInt(@"ends with \", 2);
                prefs.SetInt(@"\t not a tab", 3);
                var copy = RoundTrip(prefs);
                Assert.Equal(1, copy.GetInt(@"a\b"), "a\\b");
                Assert.Equal(2, copy.GetInt(@"ends with \"), "trailing backslash");
                Assert.Equal(3, copy.GetInt(@"\t not a tab"), "literal backslash-t");
            });

            TestHarness.Add("Typed getters fall back to the default on missing keys or other types", _ =>
            {
                var prefs = new PreferenceStore();
                prefs.SetString("volume", "loud");
                Assert.Equal(7, prefs.GetInt("missing", 7), "missing int");
                Assert.Equal(0.5f, prefs.GetFloat("volume", 0.5f), "string read as float");
                Assert.Equal(true, prefs.GetBool("volume", true), "string read as bool");
                Assert.Equal("loud", prefs.GetString("volume"), "right type");
                Assert.True(prefs.GetString("missing") == null, "missing string defaults to null");
            });

            TestHarness.Add("Setters report whether anything changed", _ =>
            {
                var prefs = new PreferenceStore();
                Assert.True(prefs.SetInt("n", 5), "first set");
                Assert.True(!prefs.SetInt("n", 5), "same value");
                Assert.True(prefs.SetInt("n", 6), "new value");
                Assert.True(prefs.SetString("n", "6"), "same text but different type is a change");
                Assert.True(!prefs.SetString("n", "6"), "same type and value");
            });

            TestHarness.Add("Invalid keys and values are rejected", _ =>
            {
                var prefs = new PreferenceStore();
                foreach (var bad in new[] { null, "", "a\tb", "a\nb", "a\rb" })
                {
                    Assert.Throws<ArgumentException>(() => prefs.SetInt(bad, 1), $"set key '{bad}'");
                    Assert.Throws<ArgumentException>(() => prefs.GetInt(bad), $"get key '{bad}'");
                }
                Assert.Throws<ArgumentNullException>(() => prefs.SetString("s", null), "null string");
                Assert.Throws<ArgumentOutOfRangeException>(() => prefs.SetFloat("f", float.NaN), "NaN");
                Assert.Throws<ArgumentOutOfRangeException>(() => prefs.SetFloat("f", float.PositiveInfinity), "+inf");
            });

            TestHarness.Add("Malformed preference data is rejected and leaves the store unchanged", _ =>
            {
                var cases = new[]
                {
                    "",
                    "UMK-PREF 2\n",
                    "UMK-PREF 1\ni\tn\n",
                    "UMK-PREF 1\nx\tn\t1\n",
                    "UMK-PREF 1\nii\tn\t1\n",
                    "UMK-PREF 1\nb\tn\tyes\n",
                    "UMK-PREF 1\ni\tn\t1.5\n",
                    "UMK-PREF 1\ni\tn\t99999999999\n",
                    "UMK-PREF 1\nf\tn\tNaN\n",
                    "UMK-PREF 1\nf\tn\tInfinity\n",
                    "UMK-PREF 1\ns\tn\tbad escape \\q\n",
                    "UMK-PREF 1\ns\tn\tdangling \\\n",
                    "UMK-PREF 1\ns\t\tempty key\n",
                    "UMK-PREF 1\ni\tok\t1\ni\tbad\n",
                };
                foreach (var content in cases)
                {
                    var prefs = new PreferenceStore();
                    prefs.SetInt("keep", 42);
                    Assert.True(!prefs.TryDeserialize(Encoding.UTF8.GetBytes(content)), $"accepted: {content.Replace("\n", "\\n").Replace("\t", "\\t")}");
                    Assert.Equal(1, prefs.Count, "count unchanged");
                    Assert.Equal(42, prefs.GetInt("keep"), "value unchanged");
                }
                Assert.True(!new PreferenceStore().TryDeserialize(new byte[] { 0xC3, 0x28 }), "invalid UTF-8");
                Assert.True(!new PreferenceStore().TryDeserialize(null), "null");
            });

            TestHarness.Add("Settings default to Auto frame rate and auto-zoom on", _ =>
            {
                var settings = new GameSettings(new MemoryStore());
                Assert.Equal(FrameRateMode.Auto, settings.FrameRate, "frame rate");
                Assert.True(settings.TouchAutoZoom, "auto-zoom");
                Assert.True(!settings.HasUnsavedChanges, "nothing to save");
            });

            TestHarness.Add("Settings survive a restart (real files on disk)", dir =>
            {
                var settings = new GameSettings(new AtomicFileStore(dir));
                settings.FrameRate = FrameRateMode.Fps30;
                settings.TouchAutoZoom = false;
                settings.SetFloat("music_volume", 0.35f);
                settings.SetString("language", "de-CH");
                settings.Save();

                var reloaded = new GameSettings(new AtomicFileStore(dir));
                Assert.Equal(SaveLoadResult.LoadedPrimary, reloaded.Load(), "result");
                Assert.Equal(FrameRateMode.Fps30, reloaded.FrameRate, "frame rate");
                Assert.True(!reloaded.TouchAutoZoom, "auto-zoom");
                Assert.Equal(0.35f, reloaded.GetFloat("music_volume"), "custom float");
                Assert.Equal("de-CH", reloaded.GetString("language"), "custom string");
                Assert.True(!reloaded.HasUnsavedChanges, "fresh load is clean");
            });

            TestHarness.Add("Changed fires and marks unsaved only when a value really changes", _ =>
            {
                var settings = new GameSettings(new MemoryStore());
                int changes = 0;
                settings.Changed += () => changes++;

                settings.FrameRate = FrameRateMode.Fps60;
                settings.FrameRate = FrameRateMode.Fps60;
                settings.TouchAutoZoom = false;
                settings.TouchAutoZoom = false;
                settings.SetInt("difficulty", 2);
                settings.SetInt("difficulty", 2);
                settings.Remove("not-there");
                Assert.Equal(3, changes, "change events");
                Assert.True(settings.HasUnsavedChanges, "unsaved");

                settings.Save();
                Assert.True(!settings.HasUnsavedChanges, "clean after save");
                settings.Remove("difficulty");
                Assert.Equal(4, changes, "remove of an existing key is a change");
            });

            TestHarness.Add("Built-in keys cannot be read or overwritten through the generic API", _ =>
            {
                var settings = new GameSettings(new MemoryStore());
                Assert.Throws<ArgumentException>(() => settings.SetString("umk.frameRate", "fast"), "set reserved");
                Assert.Throws<ArgumentException>(() => settings.GetInt("umk.frameRate"), "get reserved");
                Assert.Throws<ArgumentException>(() => settings.Remove("umk.touchAutoZoom"), "remove reserved");
                Assert.Throws<ArgumentOutOfRangeException>(() => settings.FrameRate = (FrameRateMode)9, "undefined mode");
                settings.SetInt("umk_not_reserved", 1);
                Assert.Equal(FrameRateMode.Auto, settings.FrameRate, "built-in untouched");
            });

            TestHarness.Add("An out-of-range saved frame-rate value reads as Auto", _ =>
            {
                var store = new MemoryStore();
                store.Save("settings", Encoding.UTF8.GetBytes("UMK-PREF 1\ni\tumk.frameRate\t42\n"));
                var settings = new GameSettings(store);
                Assert.Equal(SaveLoadResult.LoadedPrimary, settings.Load(), "result");
                Assert.Equal(FrameRateMode.Auto, settings.FrameRate, "unknown mode falls back to Auto");
            });

            TestHarness.Add("Missing or damaged settings load as defaults without throwing", dir =>
            {
                var store = new AtomicFileStore(dir);
                var settings = new GameSettings(store);
                settings.FrameRate = FrameRateMode.Fps30;
                Assert.Equal(SaveLoadResult.NotFound, settings.Load(), "no file");
                Assert.Equal(FrameRateMode.Auto, settings.FrameRate, "load replaces unsaved in-memory values");

                store.Save("settings", Encoding.UTF8.GetBytes("garbage"));
                Assert.Equal(SaveLoadResult.Corrupt, settings.Load(), "unparseable payload");
                Assert.Equal(FrameRateMode.Auto, settings.FrameRate, "defaults after corrupt load");

                settings.FrameRate = FrameRateMode.Fps60;
                settings.Save();
                File.WriteAllBytes(store.GetPrimaryPath("settings"), new byte[] { 1, 2, 3 });
                Assert.Equal(SaveLoadResult.Corrupt, new GameSettings(new AtomicFileStore(dir)).Load(), "damaged file, garbage backup");
            });

            TestHarness.Add("Damaged latest settings file falls back to the previous save", dir =>
            {
                var store = new AtomicFileStore(dir);
                var settings = new GameSettings(store);
                settings.FrameRate = FrameRateMode.Fps30;
                settings.Save();
                settings.FrameRate = FrameRateMode.Fps60;
                settings.Save();
                using (var fs = new FileStream(store.GetPrimaryPath("settings"), FileMode.Open)) fs.SetLength(fs.Length - 1);

                var reloaded = new GameSettings(new AtomicFileStore(dir));
                Assert.Equal(SaveLoadResult.LoadedBackup, reloaded.Load(), "result");
                Assert.Equal(FrameRateMode.Fps30, reloaded.FrameRate, "previous value");
            });

            TestHarness.Add("ResetToDefaults clears built-in and custom settings and persists", _ =>
            {
                var store = new MemoryStore();
                var settings = new GameSettings(store);
                settings.FrameRate = FrameRateMode.Fps30;
                settings.SetBool("haptics", false);
                settings.Save();

                int changes = 0;
                settings.Changed += () => changes++;
                settings.ResetToDefaults();
                Assert.Equal(1, changes, "one change event");
                Assert.True(!settings.HasUnsavedChanges, "saved");

                var reloaded = new GameSettings(store);
                reloaded.Load();
                Assert.Equal(FrameRateMode.Auto, reloaded.FrameRate, "frame rate default");
                Assert.True(!reloaded.HasKey("haptics"), "custom key gone");
                Assert.True(reloaded.GetBool("haptics", true), "custom default");
            });

            TestHarness.Add("Saved settings file is deterministic, readable text", _ =>
            {
                var store = new MemoryStore();
                var settings = new GameSettings(store);
                settings.FrameRate = FrameRateMode.Fps60;
                settings.SetString("zoom_hint", "a\tb");
                settings.SetInt("audio", 3);
                settings.Save();
                store.TryLoad("settings", out var first);
                Assert.Equal("UMK-PREF 1\ni\taudio\t3\ni\tumk.frameRate\t2\ns\tzoom_hint\ta\\tb\n",
                             Encoding.UTF8.GetString(first), "file contents, keys sorted");

                var otherStore = new MemoryStore();
                var other = new GameSettings(otherStore);
                other.SetInt("audio", 3);
                other.SetString("zoom_hint", "a\tb");
                other.FrameRate = FrameRateMode.Fps60;
                other.Save();
                otherStore.TryLoad("settings", out var second);
                Assert.Bytes(first, second, "same contents in a different insertion order give the same bytes");
            });

            TestHarness.Add("Setting a built-in to its current value is not a change", _ =>
            {
                var store = new MemoryStore();
                var settings = new GameSettings(store);
                int changes = 0;
                settings.Changed += () => changes++;
                settings.TouchAutoZoom = true;
                settings.FrameRate = FrameRateMode.Auto;
                Assert.Equal(0, changes, "change events");
                Assert.True(!settings.HasUnsavedChanges, "nothing to save");
            });
        }
    }
}
