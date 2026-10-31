// NOT RUNTIME-TESTED. Written for Unity 2021.3 LTS or newer but never run in Unity or on a device.
// It is only compile-checked against hand-written stand-ins for the UnityEngine API
// (tests/UnityApiStubs). The logic it calls into (core/) is unit-tested with dotnet.

using System;
using System.Collections.Generic;
using UnityEngine;
using UnityMobileKit.Achievements;

namespace UnityMobileKit.Runtime
{
    /// <summary>The game's achievements, edited in the Inspector and passed to <see cref="MobileKitServices"/>.</summary>
    [CreateAssetMenu(fileName = "AchievementCatalog", menuName = "Unity Mobile Kit/Achievement Catalog")]
    public sealed class AchievementCatalog : ScriptableObject
    {
        [Serializable]
        public sealed class Entry
        {
            [Tooltip("Stable id stored in save files. Never rename it after release.")]
            public string id = "";

            public string title = "";

            [TextArea]
            public string description = "";

            [Min(1)]
            public int target = 1;

            [Tooltip("Hide the description until unlocked.")]
            public bool hidden;
        }

        [SerializeField] private List<Entry> entries = new List<Entry>();

        public IReadOnlyList<Entry> Entries => entries;

        /// <summary>Throws <see cref="ArgumentException"/> for an empty id, a target below 1 or a duplicate id.</summary>
        public List<AchievementDefinition> CreateDefinitions()
        {
            var definitions = new List<AchievementDefinition>(entries.Count);
            var ids = new HashSet<string>(StringComparer.Ordinal);
            foreach (Entry entry in entries)
            {
                if (entry == null) continue;
                if (entry.target < 1) throw new ArgumentException($"Achievement '{entry.id}' needs a target of at least 1.");
                if (!ids.Add(entry.id ?? "")) throw new ArgumentException($"Duplicate achievement id '{entry.id}'.");
                definitions.Add(new AchievementDefinition(entry.id, entry.title, entry.description, entry.target, entry.hidden));
            }
            return definitions;
        }
    }
}
