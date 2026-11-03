using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using UnityMobileKit.Achievements;
using UnityMobileKit.CameraControl;
using UnityMobileKit.Controllers;
using UnityMobileKit.Geometry;
using UnityMobileKit.Gestures;
using UnityMobileKit.Lifecycle;
using UnityMobileKit.Performance;
using UnityMobileKit.Persistence;
using UnityMobileKit.ScreenLayout;
using UnityMobileKit.Settings;

internal static class NativeDpcPlatform
{
    private const string Lib = "dpcPlatform";

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    public static extern int EmptyFunction();

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    public static extern int GetNoPathCostConstant();

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    public static extern int Setup();

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    public static extern int Clear(int pathfinderId, IntPtr reportError);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    public static extern int PauseUpdate(int pathfinderId, IntPtr reportError);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    public static extern int ResumeUpdate(int pathfinderId, IntPtr reportError);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    public static extern int AddNode(int pathfinderId, [MarshalAs(UnmanagedType.I1)] bool isEndpoint, IntPtr reportError);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    [return: MarshalAs(UnmanagedType.I1)]
    public static extern bool MergeNodes(int pathfinderId, int intoNodeId, int fromNodeId, IntPtr reportError);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    public static extern int AddEdge(int pathfinderId, int nodeId1, int nodeId2, int cost, IntPtr reportError);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    [return: MarshalAs(UnmanagedType.I1)]
    public static extern bool RemoveEdge(int pathfinderId, int nodeId1, int nodeId2, IntPtr reportError);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    [return: MarshalAs(UnmanagedType.I1)]
    public static extern bool ChangeEdgeCost(int pathfinderId, int node1Id, int node2Id, int newCost, IntPtr reportError);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    public static extern int GetPathCost(int pathfinderId, int fromNodeId, int endpointNodeId, IntPtr reportError);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    public static extern int GetPathNextEdge(int pathfinderId, int fromNodeId, int endpointNodeId, IntPtr reportError);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    public static extern int GetPathNextNode(int pathfinderId, int fromNodeId, int endpointNodeId, IntPtr reportError);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    public static extern int GetEdgeCost(int pathfinderId, int fromNodeId, int toNodeId, IntPtr reportError);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    public static extern int GetNeighbourCount(int pathfinderId, int fromNodeId, IntPtr reportError);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    public static extern int GetNeighbour(int pathfinderId, int fromNodeId, int neighbourIndex, IntPtr reportError);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    [return: MarshalAs(UnmanagedType.I1)]
    public static extern bool IsNodeEndpoint(int pathfinderId, int nodeId, IntPtr reportError);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    public static extern void MakeNodeEndpoint(int pathfinderId, int nodeId, IntPtr reportError);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    [return: MarshalAs(UnmanagedType.I1)]
    public static extern bool AreNodesConnected(int pathfinderId, int nodeId1, int nodeId2, int costUpperLimit, IntPtr reportError);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    public static extern long CalculateAcceleration(
        long currentGap,
        long currentSpeed,
        long leadingSpeed,
        long leadingAcceleration,
        long desiredSpeed,
        long maximumAcceleration,
        long accelerationExponent,
        long maximumDeceleration,
        long decelerationExponent);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    public static extern void GainMixToInterlaced(
        IntPtr destinationArray,
        int destinationOffset,
        int channelCount,
        IntPtr sourceArray,
        int sourceIndex,
        int length,
        float gain);

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    public static extern float LFOProcessChunk(
        IntPtr data,
        int sourceIndex,
        int length,
        int stride,
        float phase,
        float phaseIncrement,
        float strength);
}

internal static class NativeDecompressAudio
{
    private const string Lib = "decompressAudio";

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    public static extern int EmptyFunction();

    [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
    [return: MarshalAs(UnmanagedType.I1)]
    public static extern bool decompressAudioSample(
        IntPtr decompressedAudio,
        int decompressedOffset,
        int decompressedLength,
        int resampledLength,
        int decompressedSampleRate,
        IntPtr compressedAudio,
        int compressedOffset,
        int compressedSampleRate);
}

internal static class Program
{
    private static int _passed;
    private static int _failed;

    private static void Check(string name, Action body)
    {
        try
        {
            body();
            _passed++;
            Console.WriteLine($"PASS  {name}");
        }
        catch (Exception ex)
        {
            _failed++;
            Console.WriteLine($"FAIL  {name}: {ex.Message}");
        }
    }

    private static void AssertTrue(bool cond, string msg = "Assertion failed")
    {
        if (!cond) throw new InvalidOperationException(msg);
    }

    private static int Main(string[] args)
    {
        Check("1. Native dpcPlatform P/Invoke: pathfinding graph, MergeNodes, Pause/Resume, and MothballLaneCost", () =>
        {
            AssertTrue(NativeDpcPlatform.EmptyFunction() == 0);
            int noPath = NativeDpcPlatform.GetNoPathCostConstant();
            AssertTrue(noPath == 0x3fffffff);

            int pf = NativeDpcPlatform.Setup();
            NativeDpcPlatform.PauseUpdate(pf, IntPtr.Zero);
            int house = NativeDpcPlatform.AddNode(pf, false, IntPtr.Zero);
            int midA = NativeDpcPlatform.AddNode(pf, false, IntPtr.Zero);
            int midB = NativeDpcPlatform.AddNode(pf, false, IntPtr.Zero);
            int dest = NativeDpcPlatform.AddNode(pf, true, IntPtr.Zero);

            int e0 = NativeDpcPlatform.AddEdge(pf, house, midA, 15, IntPtr.Zero);
            int e1 = NativeDpcPlatform.AddEdge(pf, midB, dest, 25, IntPtr.Zero);
            AssertTrue(NativeDpcPlatform.MergeNodes(pf, midA, midB, IntPtr.Zero));
            NativeDpcPlatform.ResumeUpdate(pf, IntPtr.Zero);

            AssertTrue(NativeDpcPlatform.IsNodeEndpoint(pf, dest, IntPtr.Zero));
            AssertTrue(NativeDpcPlatform.GetPathCost(pf, house, dest, IntPtr.Zero) == 40);
            AssertTrue(NativeDpcPlatform.GetPathNextEdge(pf, house, dest, IntPtr.Zero) == e0);
            AssertTrue(NativeDpcPlatform.GetPathNextNode(pf, house, dest, IntPtr.Zero) == midA);
            AssertTrue(NativeDpcPlatform.GetPathNextEdge(pf, midA, dest, IntPtr.Zero) == e1);
            AssertTrue(NativeDpcPlatform.AreNodesConnected(pf, house, dest, 100000, IntPtr.Zero));

            AssertTrue(NativeDpcPlatform.ChangeEdgeCost(pf, midA, dest, 100000, IntPtr.Zero));
            AssertTrue(!NativeDpcPlatform.AreNodesConnected(pf, house, dest, 100000, IntPtr.Zero));
            AssertTrue(NativeDpcPlatform.AreNodesConnected(pf, house, dest, noPath, IntPtr.Zero));

            AssertTrue(NativeDpcPlatform.RemoveEdge(pf, midA, dest, IntPtr.Zero));
            AssertTrue(NativeDpcPlatform.GetPathCost(pf, house, dest, IntPtr.Zero) == noPath);
            NativeDpcPlatform.Clear(pf, IntPtr.Zero);
        });

        Check("2. Native dpcPlatform P/Invoke: Fix64 IDM CalculateAcceleration & G-Audio DSP", () =>
        {
            long one = 1L << 32;
            long gap = 10L * one;
            long speed = 1L * one;
            long leadSpeed = 2L * one;
            long leadAcc = 0L;
            long desiredSpeed = 3L * one;
            long maxAcc = 2L * one;
            long accExp = 4L * one;
            long maxDec = 3L * one;
            long decExp = 2L * one;

            long acc = NativeDpcPlatform.CalculateAcceleration(
                gap, speed, leadSpeed, leadAcc, desiredSpeed, maxAcc, accExp, maxDec, decExp);
            AssertTrue(acc > 0 && acc <= maxAcc, $"Expected positive acceleration <= maxAcc, got {acc}");

            long brakeAcc = NativeDpcPlatform.CalculateAcceleration(
                one, 3L * one, 0L, 0L, desiredSpeed, maxAcc, accExp, maxDec, decExp);
            AssertTrue(brakeAcc < 0 && brakeAcc >= -maxDec, $"Expected negative braking acceleration, got {brakeAcc}");

            float[] src = new float[] { 0.5f, -0.5f, 1.0f };
            float[] dst = new float[6];
            GCHandle hSrc = GCHandle.Alloc(src, GCHandleType.Pinned);
            GCHandle hDst = GCHandle.Alloc(dst, GCHandleType.Pinned);
            try
            {
                NativeDpcPlatform.GainMixToInterlaced(hDst.AddrOfPinnedObject(), 1, 2, hSrc.AddrOfPinnedObject(), 0, 3, 0.5f);
                AssertTrue(Math.Abs(dst[1] - 0.25f) < 1e-5f);
                AssertTrue(Math.Abs(dst[3] - (-0.25f)) < 1e-5f);
                AssertTrue(Math.Abs(dst[5] - 0.5f) < 1e-5f);
            }
            finally
            {
                hSrc.Free();
                hDst.Free();
            }
        });

        Check("3. Native decompressAudio P/Invoke: decodes 48kHz FLAC sound bank (core.bytes) bit-exact", () =>
        {
            AssertTrue(NativeDecompressAudio.EmptyFunction() == 0);
            string soundBankPath = args.Length > 0 ? args[0] : "/tmp/mm-c63/assets/StreamingAssets/Sounds/48000/core.bytes";
            if (File.Exists(soundBankPath))
            {
                byte[] bank = File.ReadAllBytes(soundBankPath);
                int offset = 0;
                int sampleLength = 239867;
                byte[] expectedMd5 = new byte[16];
                Array.Copy(bank, offset + 12 + 18, expectedMd5, 0, 16);

                short[] pcm = new short[sampleLength];
                GCHandle hBank = GCHandle.Alloc(bank, GCHandleType.Pinned);
                GCHandle hPcm = GCHandle.Alloc(pcm, GCHandleType.Pinned);
                try
                {
                    bool ok = NativeDecompressAudio.decompressAudioSample(
                        hPcm.AddrOfPinnedObject(), 0, sampleLength, sampleLength, 48000,
                        hBank.AddrOfPinnedObject(), offset, 48000);
                    AssertTrue(ok, "decompressAudioSample returned false");
                }
                finally
                {
                    hBank.Free();
                    hPcm.Free();
                }

                byte[] pcmBytes = new byte[sampleLength * 2];
                Buffer.BlockCopy(pcm, 0, pcmBytes, 0, pcmBytes.Length);
                byte[] actualMd5 = MD5.HashData(pcmBytes);
                AssertTrue(
                    Convert.ToHexString(actualMd5) == Convert.ToHexString(expectedMd5),
                    $"MD5 mismatch: {Convert.ToHexString(actualMd5)} != {Convert.ToHexString(expectedMd5)}");
            }
        });

        Check("4. Touchscreen controls + Touch Auto-Zoom toggle + 2-finger pinch zoom in/out", () =>
        {
            var recognizer = new GestureRecognizer(dpi: 407f); // Samsung Galaxy A72 407 PPI
            var camera = new ZoomPanCamera(
                minSize: 5f,
                maxSize: 30f,
                viewportWidth: 2400f,
                viewportHeight: 1080f);
            camera.SetSize(20f);
            var autoZoom = new AutoZoom(camera) { Enabled = true };

            var f0Start = new TouchSample(0, new Float2(1500f, 600f));
            var f1Start = new TouchSample(1, new Float2(1700f, 600f)); // dist = 200
            var mid = new Float2(1600f, 600f);
            Float2 worldUnderMidBefore = camera.ScreenToWorld(mid);

            recognizer.Update(new[] { f0Start, f1Start }, 0.0);
            var frame = recognizer.Update(new[]
            {
                new TouchSample(0, new Float2(1400f, 600f)),
                new TouchSample(1, new Float2(1800f, 600f))
            }, 0.016);

            AssertTrue(frame.IsPinching && Math.Abs(frame.Zoom - 2.0f) < 1e-4f);
            camera.Apply(frame);
            AssertTrue(Math.Abs(camera.Size - 10f) < 1e-3f);
            Float2 worldUnderMidAfter = camera.ScreenToWorld(mid);
            AssertTrue(Float2.Distance(worldUnderMidBefore, worldUnderMidAfter) < 1e-2f,
                "World point under 2-finger midpoint must remain anchored during pinch zoom");

            autoZoom.Enabled = false;
            float sizeBefore = camera.Size;
            AssertTrue(!autoZoom.Update(new[] { new Float2(-15f, -8f), new Float2(15f, 8f) }, 5.0, 0.5f));
            AssertTrue(Math.Abs(camera.Size - sizeBefore) < 1e-5f);
        });

        Check("5. Razer Kishi V2 & Bluetooth gamepad controller support + seamless Touch <-> Controller switch", () =>
        {
            var modeTracker = new InputModeTracker();
            bool pauseRequested = false;
            modeTracker.PauseRequested += () => pauseRequested = true;

            var cursor = new VirtualCursor(2400f, 1080f);
            cursor.SetArea(new Float2(72f, 0f), new Float2(2328f, 1080f));
            var buttons = new ButtonTracker();

            modeTracker.NotifyTouch();
            AssertTrue(modeTracker.Mode == InputMode.Touch);

            var kishiPad = new GamepadState(
                leftStick: new Float2(0.8f, 0.0f),
                rightStick: Float2.Zero,
                leftTrigger: 0f,
                rightTrigger: 0f,
                buttons: GamepadButtons.South);

            modeTracker.SetGamepadConnected(true);
            modeTracker.NotifyGamepad(kishiPad);
            AssertTrue(modeTracker.Mode == InputMode.Gamepad && !pauseRequested);

            buttons.Update(kishiPad.Buttons, 1.0);
            AssertTrue(buttons.WasPressed(GamepadButtons.South));
            cursor.Update(kishiPad.LeftStick, 0.1f);
            AssertTrue(cursor.Position.X > 1200f);

            modeTracker.SetGamepadConnected(false);
            AssertTrue(pauseRequested && modeTracker.Mode == InputMode.Touch);
        });

        Check("6. Crash-safe atomic save system (.tmp + fsync + .bak recovery) & settings/achievements persistence", () =>
        {
            string tempDir = Path.Combine(Path.GetTempPath(), "mm_port_test_" + Guid.NewGuid().ToString("N"));
            try
            {
                var store = new AtomicFileStore(tempDir);
                var settings = new GameSettings(store);
                var achievements = new AchievementTracker(new[]
                {
                    new AchievementDefinition("first_commute", "First Commute", "Complete 1 trip", 1),
                    new AchievementDefinition("metropolis", "Metropolis", "Complete 1000 trips", 1000)
                }, store);
                var lifecycle = new LifecycleCoordinator(settings, achievements);

                settings.FrameRate = FrameRateMode.Auto;
                settings.TouchAutoZoom = false;
                achievements.Report("first_commute", 1);
                achievements.Report("metropolis", 450);

                lifecycle.OnPauseChanged(paused: true);

                settings.TouchAutoZoom = true;
                settings.Save();
                File.WriteAllBytes(Path.Combine(tempDir, "settings.sav"), new byte[] { 0x00, 0xFF, 0x12 });

                var reloadedSettings = new GameSettings(store);
                var status = reloadedSettings.Load();
                AssertTrue(status == SaveLoadResult.LoadedBackup);
                AssertTrue(reloadedSettings.TouchAutoZoom == false);

                var reloadedAchievements = new AchievementTracker(new[]
                {
                    new AchievementDefinition("first_commute", "First Commute", "Complete 1 trip", 1),
                    new AchievementDefinition("metropolis", "Metropolis", "Complete 1000 trips", 1000)
                }, store);
                AssertTrue(reloadedAchievements.Load() == SaveLoadResult.LoadedPrimary);
                AssertTrue(reloadedAchievements.IsUnlocked("first_commute"));
                AssertTrue(reloadedAchievements.GetState("metropolis").Progress == 450);
            }
            finally
            {
                if (Directory.Exists(tempDir)) Directory.Delete(tempDir, recursive: true);
            }
        });

        Check("7. Samsung Galaxy A72 (2400x1080, 20:9, 407 PPI, 90Hz, punch-hole cutout) scaling & safe area", () =>
        {
            var rawSafe = new RectF(72f, 0f, 2328f, 1080f);
            SafeArea.GetAnchors(rawSafe, 2400f, 1080f, symmetric: false, out Float2 asymMin, out Float2 asymMax);
            SafeArea.GetAnchors(rawSafe, 2400f, 1080f, symmetric: true, out Float2 symMin, out Float2 symMax);

            AssertTrue(Math.Abs(asymMin.X - (72f / 2400f)) < 1e-5f && Math.Abs(asymMax.X - 1.0f) < 1e-5f);
            AssertTrue(Math.Abs(symMin.X - (72f / 2400f)) < 1e-5f && Math.Abs(symMax.X - (2328f / 2400f)) < 1e-5f);

            float scale = UiScale.ScaleWithScreenSize(2400f, 1080f, 1294.9305f, 910f, match: 1.0f);
            AssertTrue(Math.Abs(scale - (1080f / 910f)) < 1e-4f);
            float minTouchCanvasUnits = UiScale.TouchTargetInReferenceUnits(407f, scale);
            AssertTrue(minTouchCanvasUnits >= 95f && minTouchCanvasUnits <= 115f);
        });

        Check("8. Performance & battery optimization: 90Hz Galaxy A72 Auto FPS, thermal & battery-saver step-down", () =>
        {
            var policy = new FrameRatePolicy();
            var coolNormal = new DeviceConditions(batteryLevel: 0.80f, isCharging: false, isLowPowerMode: false, ThermalLevel.Nominal);
            int fps90 = policy.Update(FrameRateMode.Auto, displayRefreshHz: 90, coolNormal, 1f / 90f, 1.0);
            AssertTrue(fps90 == 90);

            var warm = new DeviceConditions(batteryLevel: 0.80f, isCharging: false, isLowPowerMode: false,
                ThermalMapping.FromAndroidThermalStatus(2));
            int fpsWarm = policy.Update(FrameRateMode.Auto, displayRefreshHz: 90, warm, 1f / 60f, 2.0);
            AssertTrue(fpsWarm == 30);

            var lowBat = new DeviceConditions(batteryLevel: 0.12f, isCharging: false, isLowPowerMode: false, ThermalLevel.Nominal);
            int fpsLowBat = policy.Update(FrameRateMode.Auto, displayRefreshHz: 90, lowBat, 1f / 60f, 3.0);
            AssertTrue(fpsLowBat == 30);
        });

        Console.WriteLine($"\n{_passed}/{_passed + _failed} passed, {_failed} failed.");
        return _failed == 0 ? 0 : 1;
    }
}
