using System;

namespace UnityMobileKit.Achievements
{
    /// <summary>Read-only snapshot of one achievement, suitable for binding to an achievements screen.</summary>
    public readonly struct AchievementState
    {
        public AchievementState(AchievementDefinition definition, int progress, DateTime? unlockedAtUtc)
        {
            Definition = definition;
            Progress = progress;
            UnlockedAtUtc = unlockedAtUtc;
        }

        public AchievementDefinition Definition { get; }

        public int Progress { get; }

        public DateTime? UnlockedAtUtc { get; }

        public bool IsUnlocked => UnlockedAtUtc.HasValue;

        /// <summary>0..1, for progress bars.</summary>
        public float Fraction => Definition == null ? 0f : Math.Min(1f, (float)Progress / Definition.Target);
    }
}
