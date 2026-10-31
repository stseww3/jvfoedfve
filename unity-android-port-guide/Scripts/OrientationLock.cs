using UnityEngine;

/// <summary>
/// Keeps the game in landscape at all times. Both landscape directions stay allowed so the game follows
/// the phone when the player flips it over. Set the same thing in Player Settings so the splash screen
/// is landscape too.
/// </summary>
public static class OrientationLock
{
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
    static void LockToLandscape()
    {
        Screen.autorotateToPortrait = false;
        Screen.autorotateToPortraitUpsideDown = false;
        Screen.autorotateToLandscapeLeft = true;
        Screen.autorotateToLandscapeRight = true;
        Screen.orientation = ScreenOrientation.AutoRotation;
    }
}
