using System;
using System.Collections.Generic;
using System.IO;
using UnityMobileKit.Persistence;

namespace UnityMobileKit.Lifecycle
{
    /// <summary>
    /// Turns the platform's focus/pause/quit callbacks into one "suspended" state and flushes
    /// unsaved data when the app is suspended. Mobile OSes may kill a backgrounded app without any
    /// further callback, so suspension is the last reliable moment to save.
    /// <para>
    /// Wire Unity's <c>OnApplicationFocus</c>, <c>OnApplicationPause</c> and <c>OnApplicationQuit</c>
    /// to the matching methods. Show a pause menu on <see cref="Suspended"/>; don't resume gameplay
    /// automatically on <see cref="Restored"/>, let the player do it.
    /// </para>
    /// </summary>
    public sealed class LifecycleCoordinator
    {
        private readonly List<ISaveable> _saveables = new List<ISaveable>();
        private bool _hasFocus = true;
        private bool _paused;

        public LifecycleCoordinator(params ISaveable[] saveables)
        {
            if (saveables == null) return;
            foreach (var saveable in saveables) Register(saveable);
        }

        public bool IsSuspended => !_hasFocus || _paused;

        /// <summary>
        /// The error from the last <see cref="SaveAll"/> that had a failure, cleared by one without
        /// failures. Saving never throws out of a platform callback.
        /// </summary>
        public Exception LastSaveError { get; private set; }

        public event Action Suspended;

        public event Action Restored;

        public void Register(ISaveable saveable)
        {
            if (saveable == null) throw new ArgumentNullException(nameof(saveable));
            if (!_saveables.Contains(saveable)) _saveables.Add(saveable);
        }

        public void OnFocusChanged(bool hasFocus) => Transition(() => _hasFocus = hasFocus);

        public void OnPauseChanged(bool paused) => Transition(() => _paused = paused);

        public void OnQuit() => SaveAll();

        /// <summary>
        /// Saves everything that has unsaved changes. Each item is attempted even if an earlier one
        /// fails. Returns the number of items that failed.
        /// </summary>
        public int SaveAll()
        {
            int failures = 0;
            foreach (var saveable in _saveables)
            {
                if (!saveable.HasUnsavedChanges) continue;
                try
                {
                    saveable.Save();
                }
                catch (IOException e)
                {
                    LastSaveError = e;
                    failures++;
                }
                catch (UnauthorizedAccessException e)
                {
                    LastSaveError = e;
                    failures++;
                }
            }
            if (failures == 0) LastSaveError = null;
            return failures;
        }

        private void Transition(Action change)
        {
            bool wasSuspended = IsSuspended;
            change();
            if (IsSuspended == wasSuspended) return;

            if (IsSuspended)
            {
                SaveAll();
                Suspended?.Invoke();
            }
            else
            {
                Restored?.Invoke();
            }
        }
    }
}
