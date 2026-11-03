#!/usr/bin/env python3
"""
apply_mobile_port.py — Automated installer & patcher for the Mini Motorways Android Mobile Port.

What this tool does:
  1. Audits CleanScenes_Resources_NoSource.zip (scenes, mobile UI prefabs, feature configs,
     48 kHz FLAC sound bank, and GUID reference resolution).
  2. Installs Android native plugin sources (libdpcPlatform.c, libdecompressAudio.c,
     CMakeLists.txt, Android.mk, Application.mk) into Assets/Plugins/Android/jni/.
  3. Installs Resources/featuretoggleconfigs/AndroidConfig.json and AndroidManifest.xml.
  4. Installs the Android platform classes (AndroidEnvironment, AndroidHardwareCapabilities,
     AndroidSoftwareCapabilities, AndroidReachability, NullSteamCloudSyncService,
     AndroidGamepadInputSource, AndroidAtomicFileStorage, AndroidAchievementHandler,
     AndroidPerformanceManager, SafeArea, TouchCameraAction) into Assets/Scripts/App/.
  5. Patches AppContainer.cs, AudioDataBank.cs, AudioDatabase.cs, VehicleMovementProcess.cs,
     InputState.cs, RuntimeAppCommandSource.cs, and ProjectSettings/ProjectSettings.asset
     for Android ARM64 IL2CPP and Always-Landscape (LandscapeLeft + LandscapeRight).
"""

import argparse
import glob
import os
import re
import shutil
import struct
import zipfile
from pathlib import Path


PORT_ROOT = Path(__file__).resolve().parent.parent


def audit_clean_zip(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path, "r") as zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        meta_guids = set()
        ref_guids = set()
        scenes = []
        mobile_prefabs = []
        has_sound_bank = False
        sound_bank_size = 0

        for info in infos:
            norm = info.filename.replace("\\", "/")
            if norm.endswith(".unity"):
                scenes.append(norm)
            if norm.startswith("Prefabs/screens/") and norm.endswith(".prefab"):
                if any(k in norm for k in ("Phone", "Tablet", "Options", "Resume", "MainMenu", "Pause")):
                    mobile_prefabs.append(norm)
            if norm == "StreamingAssets/Sounds/48000/core.bytes":
                has_sound_bank = True
                sound_bank_size = info.file_size

            if norm.endswith(".meta"):
                text = zf.read(info).decode("utf-8", errors="ignore")
                m = re.search(r"guid:\s*([0-9a-f]{32})", text)
                if m:
                    meta_guids.add(m.group(1))
            elif norm.endswith((".unity", ".prefab", ".asset", ".mat", ".lighting")):
                text = zf.read(info).decode("utf-8", errors="ignore")
                for m in re.finditer(r"guid:\s*([0-9a-f]{32})", text):
                    g = m.group(1)
                    if not g.startswith("0000000000000000"):
                        ref_guids.add(g)

    resolved = ref_guids & meta_guids
    missing = ref_guids - meta_guids
    return {
        "file_count": len(infos),
        "scenes": sorted(scenes),
        "mobile_prefabs": sorted(mobile_prefabs),
        "has_48k_sound_bank": has_sound_bank,
        "sound_bank_size": sound_bank_size,
        "meta_guids": len(meta_guids),
        "referenced_guids": len(ref_guids),
        "resolved_guids": len(resolved),
        "missing_guids": len(missing),
    }


def patch_file_text(path: Path, transform_fn) -> bool:
    if not path.exists():
        return False
    original = path.read_text(encoding="utf-8", errors="replace")
    updated = transform_fn(original)
    if updated != original:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def apply_to_source_tree(app_src_dir: Path) -> list:
    actions = []
    overrides_dir = PORT_ROOT / "game_overrides"

    # Copy new Android classes into App source folder
    for src_name, dst_rel in [
        ("AndroidEnvironment.cs", "AndroidEnvironment.cs"),
        ("AndroidHardwareCapabilities.cs", "AndroidHardwareCapabilities.cs"),
        ("AndroidSoftwareCapabilities.cs", "AndroidSoftwareCapabilities.cs"),
        ("AndroidGamepadInputSource.cs", "AndroidGamepadInputSource.cs"),
        ("AndroidAtomicFileStorage.cs", "AndroidAtomicFileStorage.cs"),
        ("AndroidAchievementHandler.cs", "AndroidAchievementHandler.cs"),
        ("AndroidPerformanceManager.cs", "AndroidPerformanceManager.cs"),
        ("AndroidSafeAreaAndScaling.cs", "SafeArea.cs"),
        ("TouchCameraAction_MobilePort.cs", "Motorways.Actions/TouchCameraAction.cs"),
    ]:
        src_file = overrides_dir / src_name
        dst_file = app_src_dir / dst_rel
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)
        actions.append(f"Installed {dst_rel}")

    # 1. Patch AppContainer.CreateDefaultEnvironment() to use AndroidEnvironment on Android
    for app_container in app_src_dir.rglob("MotorwaysAppContainer.cs"):
        def patch_env(txt: str) -> str:
            return txt.replace(
                "new WindowsSteamEnvironment()",
                "(Application.platform == RuntimePlatform.Android ? (IEnvironment)new AndroidEnvironment() : new WindowsSteamEnvironment())"
            )
        if patch_file_text(app_container, patch_env):
            actions.append(f"Patched {app_container.name} -> AndroidEnvironment")

    # 2. Patch VehicleMovementProcess.CalculateAcceleration to use managed ReferenceCalculateAcceleration on Android
    for vmp in app_src_dir.rglob("VehicleMovementProcess.cs"):
        def patch_vmp(txt: str) -> str:
            old = "return Fix64.FromRaw(NativeCalculateAcceleration("
            new = "if (UnityEngine.Application.platform == UnityEngine.RuntimePlatform.Android) return ReferenceCalculateAcceleration(currentGap, currentSpeed, leadingSpeed, leadingAcceleration, desiredSpeed, maximumAcceleration, accelerationExponent, maximumDeceleration, decelerationExponent);\n\t\treturn Fix64.FromRaw(NativeCalculateAcceleration("
            return txt.replace(old, new) if "ReferenceCalculateAcceleration(currentGap" not in txt.split("ReferenceCalculateAcceleration")[0] else txt
        if patch_file_text(vmp, patch_vmp):
            actions.append(f"Patched {vmp.name} -> managed Fix64 CalculateAcceleration fallback")

    # 3. Patch AudioDataBank.Load to use AndroidStreamingAssetsLoader.ReadAllBytes (supports jar:file:// APK paths)
    for adb in app_src_dir.rglob("AudioDataBank.cs"):
        def patch_adb(txt: str) -> str:
            return txt.replace(
                "compressedData = File.ReadAllBytes(text);",
                "compressedData = AndroidStreamingAssetsLoader.ReadAllBytes(text);"
            )
        if patch_file_text(adb, patch_adb):
            actions.append(f"Patched {adb.name} -> AndroidStreamingAssetsLoader.ReadAllBytes")

    # 4. Patch AudioDatabase.SampleBankRate to fall back to 48000 Hz when 24000 Hz bank is absent (as in CleanScenes_Resources_NoSource.zip)
    for ad in app_src_dir.rglob("AudioDatabase.cs"):
        def patch_ad(txt: str) -> str:
            old = "if (Application.platform == RuntimePlatform.IPhonePlayer || Application.platform == RuntimePlatform.Android)\n\t\t\t{\n\t\t\t\treturn 24000;\n\t\t\t}"
            new = "if (Application.platform == RuntimePlatform.IPhonePlayer || Application.platform == RuntimePlatform.Android)\n\t\t\t{\n\t\t\t\treturn AndroidStreamingAssetsLoader.SoundBankExists(24000) ? 24000 : 48000;\n\t\t\t}"
            return txt.replace(old, new)
        if patch_file_text(ad, patch_ad):
            actions.append(f"Patched {ad.name} -> 48000 Hz sound bank fallback when 24000 Hz is absent")

    # 5. Patch InputState.MaxRecognizedTouchCount default to 2 so 2-finger pinch zoom works everywhere
    for inp in app_src_dir.rglob("InputState.cs"):
        def patch_inp(txt: str) -> str:
            return txt.replace(
                "public int MaxRecognizedTouchCount { get; set; } = 1;",
                "public int MaxRecognizedTouchCount { get; set; } = 2;"
            )
        if patch_file_text(inp, patch_inp):
            actions.append(f"Patched {inp.name} -> MaxRecognizedTouchCount = 2")

    # 6. Fix ILSpy decompilation quirks if applying to raw decompiled App folder
    for fn in ("VehicleView.cs", "DestinationView.cs", "HouseView.cs", "TouchToggle.cs"):
        for p in app_src_dir.rglob(fn):
            patch_file_text(p, lambda t: re.sub(
                r"Transform\s+(IAudioView|ICanvasElement)\.get_transform\(\)\s*\{\s*return\s+base\.transform;\s*\}",
                r"Transform \1.transform => base.transform;", t))
    for p in app_src_dir.rglob("Diagnostics.cs"):
        patch_file_text(p, lambda t: re.sub(r"(?<!UnityEngine\.)\bDebug\.Log", "UnityEngine.Debug.Log", t))
    for p in app_src_dir.rglob("ReleaseMothballedLanesProcess.cs"):
        patch_file_text(p, lambda t: t.replace("doesWantHotswap: false", "false"))
    for p in app_src_dir.rglob("MotorwayView.cs"):
        patch_file_text(p, lambda t: t.replace("[list.Count - 1] = vector3", "[SplineResolution * 2 + 2] = vector3"))

    return actions


def apply_to_unity_project(project_dir: Path) -> list:
    actions = []
    assets_dir = project_dir / "Assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # 1. Install AndroidConfig.json
    ft_dir = assets_dir / "Resources" / "featuretoggleconfigs"
    ft_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PORT_ROOT / "resources" / "AndroidConfig.json", ft_dir / "AndroidConfig.json")
    actions.append("Installed Assets/Resources/featuretoggleconfigs/AndroidConfig.json")

    # 2. Install AndroidManifest.xml and native plugin sources
    android_dir = assets_dir / "Plugins" / "Android"
    jni_dir = android_dir / "jni"
    jni_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PORT_ROOT / "android_manifest" / "AndroidManifest.xml", android_dir / "AndroidManifest.xml")
    for fn in ("libdpcPlatform.c", "libdecompressAudio.c", "CMakeLists.txt", "Android.mk", "Application.mk"):
        shutil.copy2(PORT_ROOT / "native" / fn, jni_dir / fn)
    actions.append("Installed Assets/Plugins/Android/AndroidManifest.xml and JNI native plugin sources")

    # 3. Patch ProjectSettings/ProjectSettings.asset for Landscape Left + Landscape Right & ARM64 IL2CPP
    ps_path = project_dir / "ProjectSettings" / "ProjectSettings.asset"
    if ps_path.exists():
        def patch_ps(txt: str) -> str:
            txt = re.sub(r"defaultInterfaceOrientation:\s*\d+", "defaultInterfaceOrientation: 4", txt)
            txt = re.sub(r"allowedAutorotateToPortrait:\s*\d+", "allowedAutorotateToPortrait: 0", txt)
            txt = re.sub(r"allowedAutorotateToPortraitUpsideDown:\s*\d+", "allowedAutorotateToPortraitUpsideDown: 0", txt)
            txt = re.sub(r"allowedAutorotateToLandscapeRight:\s*\d+", "allowedAutorotateToLandscapeRight: 1", txt)
            txt = re.sub(r"allowedAutorotateToLandscapeLeft:\s*\d+", "allowedAutorotateToLandscapeLeft: 1", txt)
            txt = re.sub(r"AndroidTargetArchitectures:\s*\d+", "AndroidTargetArchitectures: 2", txt)
            return txt
        if patch_file_text(ps_path, patch_ps):
            actions.append("Patched ProjectSettings/ProjectSettings.asset (AutoRotation LandscapeLeft+Right, ARM64)")

    return actions


def main():
    parser = argparse.ArgumentParser(description="Mini Motorways Android Mobile Port Tool")
    parser.add_argument("--audit-clean-zip", type=Path, help="Path to CleanScenes_Resources_NoSource.zip")
    parser.add_argument("--source-dir", type=Path, help="Path to App C# source directory")
    parser.add_argument("--unity-project", type=Path, help="Path to Unity project root directory")
    args = parser.parse_args()

    if args.audit_clean_zip:
        report = audit_clean_zip(args.audit_clean_zip)
        print("=== CleanScenes_Resources_NoSource.zip Audit ===")
        for k, v in report.items():
            if isinstance(v, list):
                print(f"  {k} ({len(v)}): {', '.join(v[:8])}{' ...' if len(v) > 8 else ''}")
            else:
                print(f"  {k}: {v}")

    if args.source_dir:
        applied = apply_to_source_tree(args.source_dir)
        for item in applied:
            print(f"[SOURCE] {item}")

    if args.unity_project:
        applied = apply_to_unity_project(args.unity_project)
        for item in applied:
            print(f"[UNITY]  {item}")


if __name__ == "__main__":
    main()
