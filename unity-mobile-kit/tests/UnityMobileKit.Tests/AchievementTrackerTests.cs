using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityMobileKit.Achievements;
using UnityMobileKit.Persistence;

namespace UnityMobileKit.Tests
{
    public static class AchievementTrackerTests
    {
        private static readonly DateTime FixedNow = new DateTime(2026, 10, 31, 12, 34, 56, 789, DateTimeKind.Utc);

        /// <summary>In-memory store that can be told to fail, for testing error paths.</summary>
        private sealed class MemoryStore : ISaveStore
        {
            private readonly Dictionary<string, byte[]> _data = new Dictionary<string, byte[]>();

            public bool FailSaves { get; set; }

            public int SaveCount { get; private set; }

            public void Save(string key, byte[] data)
            {
                if (FailSaves) throw new IOException("disk full (simulated)");
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

        private static AchievementDefinition[] Defs(int roadsTarget = 10) => new[]
        {
            new AchievementDefinition("first_trip", "First trip", "Complete one trip."),
            new AchievementDefinition("roads", "Road builder", "Build roads.", roadsTarget),
            new AchievementDefinition("best_day", "Long haul", "Survive many days.", 50),
            new AchievementDefinition("secret", "Secret", "Find the secret.", 1, hidden: true),
        };

        private static AchievementTracker NewTracker(ISaveStore store, AchievementDefinition[] defs = null)
            => new AchievementTracker(defs ?? Defs(), store, utcClock: () => FixedNow);

        public static void Register()
        {
            TestHarness.Add("Definition rejects empty ids, tabs/line breaks and targets below 1", _ =>
            {
                foreach (var bad in new[] { null, "", "a\tb", "a\nb", "a\rb" })
                {
                    Assert.Throws<ArgumentException>(() => new AchievementDefinition(bad, "t", "d"), $"id '{bad}'");
                }
                Assert.Throws<ArgumentOutOfRangeException>(() => new AchievementDefinition("x", "t", "d", 0), "target 0");
                Assert.Equal(string.Empty, new AchievementDefinition("x", null, null).Title, "null title becomes empty");
            });

            TestHarness.Add("Tracker rejects duplicate ids, null entries and an empty save key", _ =>
            {
                var store = new MemoryStore();
                var dup = new[] { new AchievementDefinition("a", "", ""), new AchievementDefinition("a", "", "") };
                Assert.Throws<ArgumentException>(() => new AchievementTracker(dup, store), "duplicate id");
                Assert.Throws<ArgumentException>(() => new AchievementTracker(new AchievementDefinition[] { null }, store), "null entry");
                Assert.Throws<ArgumentException>(() => new AchievementTracker(Defs(), store, ""), "empty key");
                Assert.Throws<ArgumentNullException>(() => new AchievementTracker(Defs(), null), "null store");
            });

            TestHarness.Add("One-shot unlock returns true and fires the event exactly once", _ =>
            {
                var tracker = NewTracker(new MemoryStore());
                var fired = new List<string>();
                tracker.Unlocked += s => fired.Add(s.Definition.Id);

                Assert.True(tracker.Report("first_trip"), "first report unlocks");
                Assert.True(!tracker.Report("first_trip"), "second report does not unlock again");
                Assert.True(!tracker.Unlock("first_trip"), "explicit unlock of an unlocked achievement");
                Assert.Equal("first_trip", string.Join(",", fired), "events");
                Assert.True(tracker.IsUnlocked("first_trip"), "IsUnlocked");
                Assert.Equal(1, tracker.UnlockedCount, "UnlockedCount");
            });

            TestHarness.Add("Incremental progress unlocks exactly at the target and clamps overshoot", _ =>
            {
                var tracker = NewTracker(new MemoryStore());
                for (int i = 0; i < 9; i++) Assert.True(!tracker.Report("roads"), $"report {i + 1} of 9");
                Assert.Equal(9, tracker.GetState("roads").Progress, "progress before target");
                Assert.True(!tracker.IsUnlocked("roads"), "locked before target");
                Assert.True(tracker.Report("roads", 5), "crossing the target unlocks");
                Assert.Equal(10, tracker.GetState("roads").Progress, "progress clamped to target");
                Assert.True(!tracker.Report("roads", int.MaxValue), "reports after unlock are ignored");
                Assert.Equal(10, tracker.GetState("roads").Progress, "progress unchanged after unlock");
            });

            TestHarness.Add("Huge report amounts do not overflow", _ =>
            {
                var tracker = NewTracker(new MemoryStore());
                tracker.Report("best_day", int.MaxValue - 1);
                Assert.True(tracker.IsUnlocked("best_day"), "unlocked");
                Assert.Equal(50, tracker.GetState("best_day").Progress, "progress");
            });

            TestHarness.Add("Zero amount changes nothing; negative amounts throw", _ =>
            {
                var tracker = NewTracker(new MemoryStore());
                Assert.True(!tracker.Report("roads", 0), "zero report");
                Assert.True(!tracker.HasUnsavedChanges, "zero report is not a change");
                Assert.Throws<ArgumentOutOfRangeException>(() => tracker.Report("roads", -1), "negative Report");
                Assert.Throws<ArgumentOutOfRangeException>(() => tracker.ReportMax("roads", -1), "negative ReportMax");
            });

            TestHarness.Add("ReportMax only ever raises progress and unlocks at the target", _ =>
            {
                var tracker = NewTracker(new MemoryStore());
                Assert.True(!tracker.ReportMax("best_day", 20), "20");
                Assert.True(!tracker.ReportMax("best_day", 12), "lower value");
                Assert.Equal(20, tracker.GetState("best_day").Progress, "lower value ignored");
                Assert.True(!tracker.ReportMax("best_day", 49), "49");
                Assert.True(tracker.ReportMax("best_day", 75), "reaching the target unlocks");
                Assert.Equal(50, tracker.GetState("best_day").Progress, "clamped");
            });

            TestHarness.Add("Unknown ids throw instead of silently doing nothing", _ =>
            {
                var tracker = NewTracker(new MemoryStore());
                Assert.Throws<ArgumentException>(() => tracker.Report("nope"), "Report");
                Assert.Throws<ArgumentException>(() => tracker.ReportMax("nope", 1), "ReportMax");
                Assert.Throws<ArgumentException>(() => tracker.Unlock("nope"), "Unlock");
                Assert.Throws<ArgumentException>(() => tracker.IsUnlocked("nope"), "IsUnlocked");
                Assert.Throws<ArgumentException>(() => tracker.GetState(null), "GetState(null)");
            });

            TestHarness.Add("Event handler observes the tracker already updated", _ =>
            {
                var tracker = NewTracker(new MemoryStore());
                bool sawUnlocked = false;
                tracker.Unlocked += s => sawUnlocked = tracker.IsUnlocked(s.Definition.Id) && s.IsUnlocked && s.Fraction == 1f;
                tracker.Unlock("secret");
                Assert.True(sawUnlocked, "handler saw consistent state");
            });

            TestHarness.Add("GetAll lists every achievement in definition order with progress fractions", _ =>
            {
                var tracker = NewTracker(new MemoryStore());
                tracker.Report("roads", 4);
                var all = tracker.GetAll();
                Assert.Equal("first_trip,roads,best_day,secret", string.Join(",", all.Select(s => s.Definition.Id)), "order");
                Assert.Near(0.4, all[1].Fraction, 1e-6, "roads fraction");
                Assert.Near(0.0, all[2].Fraction, 1e-6, "untouched fraction");
                Assert.True(all[3].Definition.Hidden, "hidden flag carried through");
                Assert.Near(0.0, default(AchievementState).Fraction, 0, "default state is safe to read");
            });

            TestHarness.Add("Progress and unlock time survive a restart (real files on disk)", dir =>
            {
                var first = NewTracker(new AtomicFileStore(dir));
                first.Report("roads", 7);
                first.ReportMax("best_day", 31);
                first.Unlock("first_trip");
                first.Save();

                var second = NewTracker(new AtomicFileStore(dir));
                Assert.Equal(SaveLoadResult.LoadedPrimary, second.Load(), "load result");
                Assert.Equal(7, second.GetState("roads").Progress, "roads");
                Assert.Equal(31, second.GetState("best_day").Progress, "best_day");
                Assert.Equal(FixedNow, second.GetState("first_trip").UnlockedAtUtc, "unlock time, to the millisecond");
                Assert.Equal(DateTimeKind.Utc, second.GetState("first_trip").UnlockedAtUtc.Value.Kind, "unlock time kind");
                Assert.True(!second.IsUnlocked("secret"), "untouched stays locked");
                Assert.True(!second.HasUnsavedChanges, "fresh load has no unsaved changes");
            });

            TestHarness.Add("Unlocked achievements do not unlock or fire again after a restart", dir =>
            {
                var first = NewTracker(new AtomicFileStore(dir));
                first.Unlock("secret");

                var second = NewTracker(new AtomicFileStore(dir));
                int events = 0;
                second.Unlocked += _ => events++;
                second.Load();
                Assert.True(!second.Unlock("secret"), "unlock after reload");
                Assert.True(!second.Report("secret"), "report after reload");
                Assert.Equal(0, events, "events after reload");
            });

            TestHarness.Add("Unlocks are auto-saved without an explicit Save call", dir =>
            {
                var tracker = NewTracker(new AtomicFileStore(dir));
                tracker.Report("first_trip");
                Assert.True(!tracker.HasUnsavedChanges, "nothing pending after auto-save");

                var reloaded = NewTracker(new AtomicFileStore(dir));
                reloaded.Load();
                Assert.True(reloaded.IsUnlocked("first_trip"), "unlock persisted");
            });

            TestHarness.Add("With auto-save off nothing is written until Save", _ =>
            {
                var store = new MemoryStore();
                var tracker = NewTracker(store);
                tracker.AutoSaveOnUnlock = false;
                tracker.Unlock("first_trip");
                tracker.Report("roads", 3);
                Assert.Equal(0, store.SaveCount, "writes before Save");
                Assert.True(tracker.HasUnsavedChanges, "pending changes");
                tracker.Save();
                Assert.Equal(1, store.SaveCount, "writes after Save");
                Assert.True(!tracker.HasUnsavedChanges, "no pending changes after Save");
            });

            TestHarness.Add("Progress-only changes are not auto-saved but are flagged as unsaved", _ =>
            {
                var store = new MemoryStore();
                var tracker = NewTracker(store);
                tracker.Report("roads", 2);
                tracker.ReportMax("best_day", 5);
                Assert.Equal(0, store.SaveCount, "no write for progress");
                Assert.True(tracker.HasUnsavedChanges, "flagged");
            });

            TestHarness.Add("No save file loads as NotFound with everything locked", dir =>
            {
                var tracker = NewTracker(new AtomicFileStore(dir));
                Assert.Equal(SaveLoadResult.NotFound, tracker.Load(), "result");
                Assert.Equal(0, tracker.UnlockedCount, "unlocked");
                Assert.Equal(4, tracker.Count, "count");
            });

            TestHarness.Add("Damaged latest save falls back to the previous save's progress", dir =>
            {
                var store = new AtomicFileStore(dir);
                var tracker = NewTracker(store);
                tracker.Report("roads", 3);
                tracker.Save();
                tracker.Report("roads", 4);
                tracker.Save();

                byte[] bytes = File.ReadAllBytes(store.GetPrimaryPath("achievements"));
                bytes[bytes.Length - 2] ^= 0xFF;
                File.WriteAllBytes(store.GetPrimaryPath("achievements"), bytes);

                var reloaded = NewTracker(new AtomicFileStore(dir));
                Assert.Equal(SaveLoadResult.LoadedBackup, reloaded.Load(), "result");
                Assert.Equal(3, reloaded.GetState("roads").Progress, "previous progress");
            });

            TestHarness.Add("Well-framed but malformed content loads as Corrupt and empty", _ =>
            {
                var cases = new[]
                {
                    "not an achievements file",
                    "UMK-ACH 2\nroads\t3\t-\n",
                    "UMK-ACH 1\nroads\t3\n",
                    "UMK-ACH 1\nroads\t-3\t-\n",
                    "UMK-ACH 1\nroads\t99999999999\t-\n",
                    "UMK-ACH 1\nroads\t3\tyesterday\n",
                    "UMK-ACH 1\nroads\t3\t999999999999999999\n",
                    "UMK-ACH 1\n\t3\t-\n",
                };
                foreach (var content in cases)
                {
                    var store = new MemoryStore();
                    store.Save("achievements", Encoding.UTF8.GetBytes(content));
                    var tracker = NewTracker(store);
                    Assert.Equal(SaveLoadResult.Corrupt, tracker.Load(), $"result for {content.Replace("\n", "\\n").Replace("\t", "\\t")}");
                    Assert.Equal(0, tracker.GetState("roads").Progress, "progress after corrupt load");
                }

                var invalidUtf8 = new MemoryStore();
                invalidUtf8.Save("achievements", new byte[] { 0x55, 0x4D, 0xFF, 0xFE });
                Assert.Equal(SaveLoadResult.Corrupt, NewTracker(invalidUtf8).Load(), "invalid UTF-8");
            });

            TestHarness.Add("Saved progress for ids missing from this version is preserved", _ =>
            {
                var store = new MemoryStore();
                var withBoth = NewTracker(store);
                withBoth.Report("roads", 6);
                withBoth.Save();

                var withoutRoads = NewTracker(store, Defs().Where(d => d.Id != "roads").ToArray());
                withoutRoads.Load();
                withoutRoads.Report("best_day", 2);
                withoutRoads.Save();

                var again = NewTracker(store);
                again.Load();
                Assert.Equal(6, again.GetState("roads").Progress, "roads progress kept through older version");
                Assert.Equal(2, again.GetState("best_day").Progress, "best_day progress");
            });

            TestHarness.Add("Lowering a target unlocks on load; raising it keeps the unlock", _ =>
            {
                var store = new MemoryStore();
                var v1 = NewTracker(store, Defs(roadsTarget: 10));
                v1.Report("roads", 6);
                v1.Save();

                var v2 = NewTracker(store, Defs(roadsTarget: 5));
                var fired = new List<string>();
                v2.Unlocked += s => fired.Add(s.Definition.Id);
                v2.Load();
                Assert.Equal("roads", string.Join(",", fired), "unlock event during load");
                Assert.True(v2.IsUnlocked("roads"), "unlocked by lowered target");

                var v3 = NewTracker(store, Defs(roadsTarget: 20));
                v3.Load();
                Assert.True(v3.IsUnlocked("roads"), "stays unlocked when the target rises");
                Assert.Equal(20, v3.GetState("roads").Progress, "unlocked shows full progress");
                Assert.Near(1.0, v3.GetState("roads").Fraction, 0, "fraction");
            });

            TestHarness.Add("A device clock before 1970 still produces a loadable save", _ =>
            {
                var store = new MemoryStore();
                var tracker = new AchievementTracker(Defs(), store, utcClock: () => new DateTime(1969, 7, 20, 0, 0, 0, DateTimeKind.Utc));
                tracker.Unlock("first_trip");

                var reloaded = NewTracker(store);
                Assert.Equal(SaveLoadResult.LoadedPrimary, reloaded.Load(), "result");
                Assert.Equal(DateTimeOffset.FromUnixTimeMilliseconds(0).UtcDateTime, reloaded.GetState("first_trip").UnlockedAtUtc, "clamped to epoch");
            });

            TestHarness.Add("Local-time clocks are converted to UTC", _ =>
            {
                var local = new DateTime(2026, 1, 2, 3, 4, 5, DateTimeKind.Local);
                var tracker = new AchievementTracker(Defs(), new MemoryStore(), utcClock: () => local);
                tracker.Unlock("first_trip");
                Assert.Equal(local.ToUniversalTime(), tracker.GetState("first_trip").UnlockedAtUtc, "stored as UTC");
            });

            TestHarness.Add("Failed auto-save keeps the unlock, does not throw, and a later Save recovers", _ =>
            {
                var store = new MemoryStore { FailSaves = true };
                var tracker = NewTracker(store);
                int events = 0;
                tracker.Unlocked += _ => events++;

                Assert.True(tracker.Unlock("first_trip"), "unlock still succeeds");
                Assert.Equal(1, events, "event still fires");
                Assert.True(tracker.LastAutoSaveError is IOException, "error recorded");
                Assert.True(tracker.HasUnsavedChanges, "still pending");

                store.FailSaves = false;
                tracker.Save();
                Assert.True(tracker.LastAutoSaveError == null, "error cleared by successful save");
                Assert.True(!tracker.HasUnsavedChanges, "nothing pending");
                var reloaded = NewTracker(store);
                reloaded.Load();
                Assert.True(reloaded.IsUnlocked("first_trip"), "persisted after recovery");
            });

            TestHarness.Add("Explicit Save still throws so callers can see I/O failures", _ =>
            {
                var tracker = NewTracker(new MemoryStore { FailSaves = true });
                Assert.Throws<IOException>(() => tracker.Save(), "Save");
            });

            TestHarness.Add("ResetAll clears everything, including unknown ids, and persists", _ =>
            {
                var store = new MemoryStore();
                var full = NewTracker(store);
                full.Report("roads", 3);
                full.Unlock("secret");

                var partial = NewTracker(store, Defs().Where(d => d.Id != "roads").ToArray());
                partial.Load();
                partial.ResetAll();

                var reloaded = NewTracker(store);
                Assert.Equal(SaveLoadResult.LoadedPrimary, reloaded.Load(), "result");
                Assert.Equal(0, reloaded.UnlockedCount, "unlocked after reset");
                Assert.Equal(0, reloaded.GetState("roads").Progress, "unknown-id record cleared too");
            });
        }
    }
}
