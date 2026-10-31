using System;
using System.Collections.Generic;
using UnityEngine;
#if PLAY_GAMES_SERVICES
using GooglePlayGames;
using GooglePlayGames.BasicApi;
#endif

/// <summary>
/// Achievements that work offline. Progress and unlocks are saved locally (SaveSystem slot
/// "achievements") and pushed to Google Play Games whenever the player is signed in, so anything earned
/// in airplane mode or before signing in still reaches Play Games later.
/// Install the Google Play Games plugin and add the scripting define PLAY_GAMES_SERVICES to switch the
/// Play Games side on; without the define this compiles and runs as a local-only system.
/// </summary>
public class Achievements : MonoBehaviour
{
    [Serializable]
    public class Definition
    {
        [Tooltip("Your own id, used from code, e.g. \"first_bridge\".")]
        public string id;
        [Tooltip("Achievement id from Play Console (starts with Cg). Leave empty for a local-only achievement.")]
        public string playGamesId;
        [Tooltip("1 = unlocks on the first Report. Higher = a counter, e.g. 1000 for \"deliver 1000 cars\".")]
        public int target = 1;
    }

    [Serializable]
    class SavedState
    {
        public List<string> ids = new List<string>();
        public List<int> counts = new List<int>();
        public List<string> unlocked = new List<string>();
    }

    const string SaveSlot = "achievements";

    [SerializeField] List<Definition> definitions = new List<Definition>();

    public static Achievements Instance { get; private set; }

    /// <summary>Raised the moment an achievement unlocks, e.g. to show an in-game toast.</summary>
    public event Action<Definition> Unlocked;

    readonly Dictionary<string, Definition> byId = new Dictionary<string, Definition>();
    readonly Dictionary<string, int> counts = new Dictionary<string, int>();
    readonly HashSet<string> unlocked = new HashSet<string>();
    bool dirty;
#if PLAY_GAMES_SERVICES
    bool signedIn;
#endif

    void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;
        DontDestroyOnLoad(gameObject);

        foreach (Definition definition in definitions)
            byId[definition.id] = definition;
        Load();

#if PLAY_GAMES_SERVICES
        PlayGamesPlatform.Activate();
        PlayGamesPlatform.Instance.Authenticate(OnAuthenticated);
#endif
    }

    /// <summary>Adds progress towards an achievement. One-shot achievements: just call Report("id").</summary>
    public void Report(string id, int amount = 1)
    {
        if (amount <= 0 || unlocked.Contains(id) || !byId.TryGetValue(id, out Definition definition))
            return;

        counts.TryGetValue(id, out int count);
        count = Mathf.Min(count + amount, definition.target);
        counts[id] = count;
        dirty = true;

        if (count < definition.target)
            return;

        unlocked.Add(id);
        Save();
        Unlocked?.Invoke(definition);
        SendToPlayGames(definition);
    }

    public bool IsUnlocked(string id)
    {
        return unlocked.Contains(id);
    }

    /// <summary>Progress from 0 to 1, for an in-game achievements list.</summary>
    public float Progress(string id)
    {
        if (unlocked.Contains(id))
            return 1f;
        if (!byId.TryGetValue(id, out Definition definition) || definition.target <= 0)
            return 0f;
        counts.TryGetValue(id, out int count);
        return (float)count / definition.target;
    }

    /// <summary>Opens the Play Games achievements screen, asking the player to sign in first if needed.</summary>
    public void ShowPlayGamesUI()
    {
#if PLAY_GAMES_SERVICES
        if (signedIn)
        {
            PlayGamesPlatform.Instance.ShowAchievementsUI();
            return;
        }
        PlayGamesPlatform.Instance.ManuallyAuthenticate(status =>
        {
            OnAuthenticated(status);
            if (signedIn)
                PlayGamesPlatform.Instance.ShowAchievementsUI();
        });
#endif
    }

    void OnApplicationPause(bool paused)
    {
        if (paused && dirty)
            Save();
    }

    void OnApplicationQuit()
    {
        if (dirty)
            Save();
    }

#if PLAY_GAMES_SERVICES
    void OnAuthenticated(SignInStatus status)
    {
        signedIn = status == SignInStatus.Success;
        if (!signedIn)
            return;
        foreach (string id in unlocked)
        {
            if (byId.TryGetValue(id, out Definition definition))
                SendToPlayGames(definition);
        }
    }
#endif

    void SendToPlayGames(Definition definition)
    {
#if PLAY_GAMES_SERVICES
        if (!signedIn || string.IsNullOrEmpty(definition.playGamesId))
            return;
        PlayGamesPlatform.Instance.ReportProgress(definition.playGamesId, 100.0, success =>
        {
            if (!success)
                Debug.LogWarning($"Play Games did not accept achievement '{definition.id}'; it is re-sent on the next sign-in.");
        });
#endif
    }

    void Load()
    {
        if (!SaveSystem.TryLoad(SaveSlot, out SavedState state) || state == null)
            return;
        for (int i = 0; i < state.ids.Count && i < state.counts.Count; i++)
            counts[state.ids[i]] = state.counts[i];
        unlocked.UnionWith(state.unlocked);
    }

    void Save()
    {
        var state = new SavedState();
        foreach (KeyValuePair<string, int> pair in counts)
        {
            state.ids.Add(pair.Key);
            state.counts.Add(pair.Value);
        }
        state.unlocked.AddRange(unlocked);
        SaveSystem.Save(SaveSlot, state);
        dirty = false;
    }
}
