// NOT RUNTIME-TESTED. Written for Unity 2021.3 LTS or newer but never run in Unity or on a device.
// It is only compile-checked against hand-written stand-ins for the UnityEngine API
// (tests/UnityApiStubs). The logic it calls into (core/) is unit-tested with dotnet.

using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.Events;
using UnityMobileKit.Achievements;
using UnityMobileKit.Lifecycle;
using UnityMobileKit.Persistence;
using UnityMobileKit.Settings;

namespace UnityMobileKit.Runtime
{
    /// <summary>
    /// Creates the save store, settings, achievements and lifecycle coordinator once per app and
    /// forwards Unity's focus / pause / quit callbacks, so unsaved data is written as soon as the app
    /// loses focus or goes to the background. Put it on a root GameObject in the first scene; it
    /// survives scene loads, and duplicates in later scenes remove themselves.
    /// </summary>
    [DefaultExecutionOrder(-1000)]
    [DisallowMultipleComponent]
    public sealed class MobileKitServices : MonoBehaviour
    {
        [Tooltip("Folder under Application.persistentDataPath that holds the save files.")]
        [SerializeField] private string saveFolder = "UnityMobileKit";

        [SerializeField] private AchievementCatalog achievementCatalog = null;

        [Tooltip("Raised after saving when the app loses focus or goes to the background. Show the pause menu here.")]
        [SerializeField] private UnityEvent onSuspended = new UnityEvent();

        [Tooltip("Raised when the app is in the foreground with focus again. Let the player resume; don't resume automatically.")]
        [SerializeField] private UnityEvent onRestored = new UnityEvent();

        private Exception _reportedSaveError;

        public static MobileKitServices Instance { get; private set; }

        public ISaveStore Store { get; private set; }

        public GameSettings Settings { get; private set; }

        public AchievementTracker Achievements { get; private set; }

        public LifecycleCoordinator Lifecycle { get; private set; }

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            transform.SetParent(null);
            DontDestroyOnLoad(gameObject);

            Store = new AtomicFileStore(Path.Combine(Application.persistentDataPath, saveFolder));
            Settings = new GameSettings(Store);
            Settings.Load();
            Achievements = new AchievementTracker(CreateDefinitions(), Store);
            Achievements.Load();

            Lifecycle = new LifecycleCoordinator(Settings, Achievements);
            Lifecycle.Suspended += onSuspended.Invoke;
            Lifecycle.Restored += onRestored.Invoke;
        }

        private void OnDestroy()
        {
            if (Instance == this) Instance = null;
        }

        private void OnApplicationFocus(bool hasFocus)
        {
            if (Lifecycle == null) return;
            Lifecycle.OnFocusChanged(hasFocus);
            ReportSaveError();
        }

        private void OnApplicationPause(bool paused)
        {
            if (Lifecycle == null) return;
            Lifecycle.OnPauseChanged(paused);
            ReportSaveError();
        }

        private void OnApplicationQuit()
        {
            if (Lifecycle == null) return;
            Lifecycle.OnQuit();
            ReportSaveError();
        }

        private IEnumerable<AchievementDefinition> CreateDefinitions()
        {
            if (achievementCatalog == null) return Array.Empty<AchievementDefinition>();
            try
            {
                return achievementCatalog.CreateDefinitions();
            }
            catch (ArgumentException e)
            {
                // A broken catalog must not take settings and saving down with it. Progress for
                // unknown ids is kept in the save file, so nothing is lost once the catalog is fixed.
                Debug.LogError($"[UnityMobileKit] Achievement catalog '{achievementCatalog.name}' is invalid: {e.Message}");
                return Array.Empty<AchievementDefinition>();
            }
        }

        private void ReportSaveError()
        {
            Exception error = Lifecycle.LastSaveError;
            if (error != null && error != _reportedSaveError)
            {
                Debug.LogWarning($"[UnityMobileKit] Saving failed, will retry on the next suspend: {error.Message}");
            }
            _reportedSaveError = error;
        }
    }
}
