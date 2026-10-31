using System;

namespace UnityMobileKit.Achievements
{
    /// <summary>Static description of one achievement. <see cref="Target"/> of 1 means a one-shot unlock.</summary>
    public sealed class AchievementDefinition
    {
        public AchievementDefinition(string id, string title, string description, int target = 1, bool hidden = false)
        {
            if (string.IsNullOrEmpty(id) || id.IndexOfAny(new[] { '\t', '\n', '\r' }) >= 0)
            {
                throw new ArgumentException("Id must be non-empty and contain no tabs or line breaks.", nameof(id));
            }
            if (target < 1)
            {
                throw new ArgumentOutOfRangeException(nameof(target), "Target must be at least 1.");
            }

            Id = id;
            Title = title ?? string.Empty;
            Description = description ?? string.Empty;
            Target = target;
            Hidden = hidden;
        }

        public string Id { get; }

        public string Title { get; }

        public string Description { get; }

        public int Target { get; }

        /// <summary>Hidden achievements should not reveal their title/description until unlocked.</summary>
        public bool Hidden { get; }
    }
}
