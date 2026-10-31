using System;
using UnityMobileKit.Persistence;

namespace UnityMobileKit.Settings
{
    /// <summary>
    /// Player settings persisted through an <see cref="ISaveStore"/>, so they survive a crash the
    /// same way saves do. It exposes two common mobile toggles (<see cref="FrameRate"/> and
    /// <see cref="TouchAutoZoom"/>) over a generic <see cref="PreferenceStore"/> that callers can
    /// also use for their own game-specific preferences.
    /// <para>Not thread-safe: use it from one thread (normally Unity's main thread).</para>
    /// </summary>
    public sealed class GameSettings : ISaveable
    {
        // Known settings live under this prefix; the generic setters refuse it so user preferences
        // can never collide with or clobber a built-in setting.
        private const string ReservedPrefix = "umk.";
        private const string FrameRateKey = "umk.frameRate";
        private const string TouchAutoZoomKey = "umk.touchAutoZoom";

        private readonly PreferenceStore _prefs = new PreferenceStore();
        private readonly ISaveStore _store;
        private readonly string _saveKey;

        public GameSettings(ISaveStore store, string saveKey = "settings")
        {
            if (string.IsNullOrEmpty(saveKey)) throw new ArgumentException("Save key must be non-empty.", nameof(saveKey));
            _store = store ?? throw new ArgumentNullException(nameof(store));
            _saveKey = saveKey;
        }

        /// <summary>Raised after any setting changes value (one event per changing call).</summary>
        public event Action Changed;

        /// <summary>True when something changed since the last load or save.</summary>
        public bool HasUnsavedChanges { get; private set; }

        public FrameRateMode FrameRate
        {
            get
            {
                int raw = _prefs.GetInt(FrameRateKey, (int)FrameRateMode.Auto);
                return IsDefinedMode(raw) ? (FrameRateMode)raw : FrameRateMode.Auto;
            }
            set
            {
                if (!IsDefinedMode((int)value)) throw new ArgumentOutOfRangeException(nameof(value));
                if (value != FrameRate && _prefs.SetInt(FrameRateKey, (int)value)) MarkChanged();
            }
        }

        /// <summary>Whether the camera auto-zooms to follow the action; defaults to on.</summary>
        public bool TouchAutoZoom
        {
            get => _prefs.GetBool(TouchAutoZoomKey, true);
            set { if (value != TouchAutoZoom && _prefs.SetBool(TouchAutoZoomKey, value)) MarkChanged(); }
        }

        /// <summary>
        /// Loads saved settings. Missing or damaged data leaves every setting at its default (rather
        /// than throwing); the result says what happened so the caller can log it.
        /// </summary>
        public SaveLoadResult Load()
        {
            _prefs.Clear();
            HasUnsavedChanges = false;

            SaveLoadResult result = _store.TryLoad(_saveKey, out byte[] bytes);
            if (result != SaveLoadResult.LoadedPrimary && result != SaveLoadResult.LoadedBackup)
            {
                return result;
            }
            if (!_prefs.TryDeserialize(bytes))
            {
                _prefs.Clear();
                return SaveLoadResult.Corrupt;
            }
            return result;
        }

        public void Save()
        {
            _store.Save(_saveKey, _prefs.Serialize());
            HasUnsavedChanges = false;
        }

        public bool GetBool(string key, bool defaultValue = false) => _prefs.GetBool(Guard(key), defaultValue);

        public int GetInt(string key, int defaultValue = 0) => _prefs.GetInt(Guard(key), defaultValue);

        public float GetFloat(string key, float defaultValue = 0f) => _prefs.GetFloat(Guard(key), defaultValue);

        public string GetString(string key, string defaultValue = null) => _prefs.GetString(Guard(key), defaultValue);

        public void SetBool(string key, bool value) { if (_prefs.SetBool(Guard(key), value)) MarkChanged(); }

        public void SetInt(string key, int value) { if (_prefs.SetInt(Guard(key), value)) MarkChanged(); }

        public void SetFloat(string key, float value) { if (_prefs.SetFloat(Guard(key), value)) MarkChanged(); }

        public void SetString(string key, string value) { if (_prefs.SetString(Guard(key), value)) MarkChanged(); }

        public bool HasKey(string key) => _prefs.ContainsKey(Guard(key));

        public void Remove(string key) { if (_prefs.Remove(Guard(key))) MarkChanged(); }

        /// <summary>Clears every setting (built-in and custom) back to defaults and saves.</summary>
        public void ResetToDefaults()
        {
            if (_prefs.Count > 0)
            {
                _prefs.Clear();
                MarkChanged();
            }
            Save();
        }

        private void MarkChanged()
        {
            HasUnsavedChanges = true;
            Changed?.Invoke();
        }

        private static bool IsDefinedMode(int value)
        {
            return value == (int)FrameRateMode.Auto
                || value == (int)FrameRateMode.Fps30
                || value == (int)FrameRateMode.Fps60;
        }

        private static string Guard(string key)
        {
            if (key != null && key.StartsWith(ReservedPrefix, StringComparison.Ordinal))
            {
                throw new ArgumentException($"Keys starting with '{ReservedPrefix}' are reserved for built-in settings.", nameof(key));
            }
            return key;
        }
    }
}
