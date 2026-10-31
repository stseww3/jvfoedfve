using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityMobileKit.Persistence;

namespace UnityMobileKit.Achievements
{
    /// <summary>
    /// Offline achievement tracking: progress, unlock-exactly-once (also across restarts) and
    /// persistence through an <see cref="ISaveStore"/>. No platform services are required.
    /// Not thread-safe: use it from one thread (normally Unity's main thread).
    /// <para>
    /// Saved records whose ids are not in the current definitions are kept and written back, so
    /// temporarily removing a definition (or rolling back an update) does not erase progress.
    /// </para>
    /// </summary>
    public sealed class AchievementTracker
    {
        private const string Header = "UMK-ACH 1";

        // DateTimeOffset cannot represent instants after 9999-12-31T23:59:59.999Z.
        private const long MaxUnixMs = 253402300799999;

        private sealed class Record
        {
            public int Progress;
            public long? UnlockedUnixMs;
        }

        private readonly List<AchievementDefinition> _definitions = new List<AchievementDefinition>();
        private readonly Dictionary<string, AchievementDefinition> _byId = new Dictionary<string, AchievementDefinition>(StringComparer.Ordinal);
        private readonly Dictionary<string, Record> _records = new Dictionary<string, Record>(StringComparer.Ordinal);
        private readonly ISaveStore _store;
        private readonly string _saveKey;
        private readonly Func<DateTime> _utcClock;

        public AchievementTracker(IEnumerable<AchievementDefinition> definitions, ISaveStore store,
                                  string saveKey = "achievements", Func<DateTime> utcClock = null)
        {
            if (definitions == null) throw new ArgumentNullException(nameof(definitions));
            if (string.IsNullOrEmpty(saveKey)) throw new ArgumentException("Save key must be non-empty.", nameof(saveKey));
            _store = store ?? throw new ArgumentNullException(nameof(store));
            _saveKey = saveKey;
            _utcClock = utcClock ?? (() => DateTime.UtcNow);

            foreach (var definition in definitions)
            {
                if (definition == null) throw new ArgumentException("Definitions must not contain null.", nameof(definitions));
                if (_byId.ContainsKey(definition.Id))
                {
                    throw new ArgumentException($"Duplicate achievement id '{definition.Id}'.", nameof(definitions));
                }
                _byId.Add(definition.Id, definition);
                _definitions.Add(definition);
            }
        }

        /// <summary>Raised once per achievement, at the moment it unlocks.</summary>
        public event Action<AchievementState> Unlocked;

        /// <summary>
        /// Persist immediately whenever something unlocks (unlocks are rare and must not be lost).
        /// A failed auto-save does not throw; see <see cref="LastAutoSaveError"/>.
        /// </summary>
        public bool AutoSaveOnUnlock { get; set; } = true;

        /// <summary>True when progress changed since the last load or save; lets callers skip needless writes.</summary>
        public bool HasUnsavedChanges { get; private set; }

        /// <summary>
        /// The I/O error from the most recent failed auto-save, or null. The unlock stays in memory
        /// and <see cref="HasUnsavedChanges"/> stays true, so a later <see cref="Save"/> persists it.
        /// </summary>
        public Exception LastAutoSaveError { get; private set; }

        public int Count => _definitions.Count;

        public int UnlockedCount
        {
            get
            {
                int n = 0;
                foreach (var d in _definitions)
                {
                    if (IsUnlocked(d.Id)) n++;
                }
                return n;
            }
        }

        /// <summary>
        /// Replaces in-memory progress with the saved progress, so call it before reporting.
        /// Damaged or unreadable data leaves the tracker empty rather than throwing; the result says
        /// what happened so the caller can log it. Achievements whose saved progress already meets
        /// the current target are unlocked (and raise <see cref="Unlocked"/>), which covers a game
        /// update lowering a target.
        /// </summary>
        public SaveLoadResult Load()
        {
            _records.Clear();
            HasUnsavedChanges = false;

            SaveLoadResult result = _store.TryLoad(_saveKey, out byte[] bytes);
            if (result != SaveLoadResult.LoadedPrimary && result != SaveLoadResult.LoadedBackup)
            {
                return result;
            }

            if (!TryParse(bytes))
            {
                _records.Clear();
                return SaveLoadResult.Corrupt;
            }

            foreach (var definition in _definitions)
            {
                if (!_records.TryGetValue(definition.Id, out var record)) continue;
                if (record.UnlockedUnixMs.HasValue || record.Progress > definition.Target)
                {
                    record.Progress = definition.Target;
                }
                if (record.Progress >= definition.Target)
                {
                    UnlockRecord(definition, record);
                }
            }
            return result;
        }

        public void Save()
        {
            _store.Save(_saveKey, Serialize());
            HasUnsavedChanges = false;
            LastAutoSaveError = null;
        }

        /// <summary>Adds to an incremental achievement. Returns true if this call unlocked it.</summary>
        public bool Report(string id, int amount = 1)
        {
            if (amount < 0) throw new ArgumentOutOfRangeException(nameof(amount), "Amount must not be negative.");
            var definition = GetDefinition(id);
            var record = GetOrCreate(id);
            if (record.UnlockedUnixMs.HasValue || amount == 0) return false;

            record.Progress = (int)Math.Min(definition.Target, (long)record.Progress + amount);
            HasUnsavedChanges = true;
            return record.Progress >= definition.Target && UnlockRecord(definition, record);
        }

        /// <summary>Raises progress to <paramref name="value"/> if higher (best score, furthest day, ...). Returns true if this call unlocked it.</summary>
        public bool ReportMax(string id, int value)
        {
            if (value < 0) throw new ArgumentOutOfRangeException(nameof(value), "Value must not be negative.");
            var definition = GetDefinition(id);
            var record = GetOrCreate(id);
            if (record.UnlockedUnixMs.HasValue) return false;

            int clamped = Math.Min(value, definition.Target);
            if (clamped <= record.Progress) return false;

            record.Progress = clamped;
            HasUnsavedChanges = true;
            return record.Progress >= definition.Target && UnlockRecord(definition, record);
        }

        /// <summary>Unlocks regardless of progress. Returns false if it was already unlocked.</summary>
        public bool Unlock(string id)
        {
            return UnlockRecord(GetDefinition(id), GetOrCreate(id));
        }

        public bool IsUnlocked(string id)
        {
            GetDefinition(id);
            return _records.TryGetValue(id, out var record) && record.UnlockedUnixMs.HasValue;
        }

        public AchievementState GetState(string id)
        {
            var definition = GetDefinition(id);
            _records.TryGetValue(id, out var record);
            return ToState(definition, record);
        }

        /// <summary>All achievements in definition order, for an achievements screen.</summary>
        public IReadOnlyList<AchievementState> GetAll()
        {
            var list = new List<AchievementState>(_definitions.Count);
            foreach (var definition in _definitions)
            {
                _records.TryGetValue(definition.Id, out var record);
                list.Add(ToState(definition, record));
            }
            return list;
        }

        /// <summary>Clears all progress, including records for unknown ids, and saves.</summary>
        public void ResetAll()
        {
            _records.Clear();
            Save();
        }

        private bool UnlockRecord(AchievementDefinition definition, Record record)
        {
            if (record.UnlockedUnixMs.HasValue) return false;

            record.Progress = definition.Target;
            record.UnlockedUnixMs = ToUnixMs(_utcClock());
            HasUnsavedChanges = true;
            if (AutoSaveOnUnlock)
            {
                try
                {
                    Save();
                }
                catch (IOException e)
                {
                    LastAutoSaveError = e;
                }
                catch (UnauthorizedAccessException e)
                {
                    LastAutoSaveError = e;
                }
            }
            Unlocked?.Invoke(ToState(definition, record));
            return true;
        }

        private AchievementDefinition GetDefinition(string id)
        {
            if (id == null || !_byId.TryGetValue(id, out var definition))
            {
                throw new ArgumentException($"Unknown achievement id '{id}'.", nameof(id));
            }
            return definition;
        }

        private Record GetOrCreate(string id)
        {
            if (!_records.TryGetValue(id, out var record))
            {
                record = new Record();
                _records.Add(id, record);
            }
            return record;
        }

        private static AchievementState ToState(AchievementDefinition definition, Record record)
        {
            if (record == null) return new AchievementState(definition, 0, null);
            DateTime? unlocked = record.UnlockedUnixMs.HasValue
                ? DateTimeOffset.FromUnixTimeMilliseconds(record.UnlockedUnixMs.Value).UtcDateTime
                : (DateTime?)null;
            return new AchievementState(definition, record.Progress, unlocked);
        }

        // Device clocks can be wrong (e.g. reset to before 1970); clamping keeps the file parseable.
        private static long ToUnixMs(DateTime time)
        {
            DateTime utc = time.Kind == DateTimeKind.Local ? time.ToUniversalTime() : DateTime.SpecifyKind(time, DateTimeKind.Utc);
            long ms = new DateTimeOffset(utc).ToUnixTimeMilliseconds();
            return Math.Max(0, Math.Min(MaxUnixMs, ms));
        }

        private byte[] Serialize()
        {
            var sb = new StringBuilder();
            sb.Append(Header).Append('\n');
            foreach (var pair in _records)
            {
                sb.Append(pair.Key).Append('\t')
                  .Append(pair.Value.Progress.ToString(CultureInfo.InvariantCulture)).Append('\t')
                  .Append(pair.Value.UnlockedUnixMs.HasValue ? pair.Value.UnlockedUnixMs.Value.ToString(CultureInfo.InvariantCulture) : "-")
                  .Append('\n');
            }
            return Encoding.UTF8.GetBytes(sb.ToString());
        }

        private bool TryParse(byte[] bytes)
        {
            string text;
            try
            {
                text = new UTF8Encoding(false, true).GetString(bytes);
            }
            catch (ArgumentException)
            {
                return false;
            }

            string[] lines = text.Split('\n');
            if (lines[0] != Header) return false;

            for (int i = 1; i < lines.Length; i++)
            {
                if (lines[i].Length == 0) continue;
                string[] fields = lines[i].Split('\t');
                if (fields.Length != 3 || fields[0].Length == 0) return false;
                if (!int.TryParse(fields[1], NumberStyles.None, CultureInfo.InvariantCulture, out int progress)) return false;

                long? unlocked = null;
                if (fields[2] != "-")
                {
                    if (!long.TryParse(fields[2], NumberStyles.None, CultureInfo.InvariantCulture, out long ms) || ms > MaxUnixMs) return false;
                    unlocked = ms;
                }
                _records[fields[0]] = new Record { Progress = progress, UnlockedUnixMs = unlocked };
            }
            return true;
        }
    }
}
