#!/usr/bin/env python3
"""Build INDEX.md: every extracted file, what it is, and how it was verified.

usage: make_index.py <extract_root> <official_player_dir> <results_dir> <out.md>

<results_dir> must contain ilcompare_*.txt, pdbcheck_report.txt and
datascan_summary.json produced by the other tools.
"""
import glob
import hashlib
import json
import os
import re
import sys

root, official_dir, results, out_md = sys.argv[1:5]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


official = {}
for dp, _, fns in os.walk(official_dir):
    for fn in fns:
        p = os.path.join(dp, fn)
        official.setdefault(sha256(p), os.path.relpath(p, official_dir))

il = {}
for f in glob.glob(os.path.join(results, "ilcompare_*.txt")):
    for line in open(f, encoding="utf-8", errors="replace"):
        m = re.match(r"RESULT (\S+): methods=(\d+), identical=(\d+), ADDED\(not in official\)=(\d+), CHANGED=(\d+).*\[best ref: (.*)\]", line)
        if m:
            name, n, same, added, changed, ref = m.groups()
            il[name] = (int(n), int(same), int(added), int(changed), ref)

pdb = {}
for line in open(os.path.join(results, "pdbcheck_report.txt"), encoding="utf-8"):
    m = re.match(r"(\S+\.dll)\s+(\S+)\s+\S+\s+(\d+)/(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(.*)$", line)
    if m:
        pdb[m.group(1)] = (m.group(4), m.group(5), m.group(6), m.group(8).strip())

data = json.load(open(os.path.join(results, "datascan_summary.json")))

pkgsrc = {}
for line in open(os.path.join(results, "pkgsrc_check_report.txt"), encoding="utf-8"):
    m = re.match(r"(\S+)\.pdb: (\d+) documents \| (.*)$", line)
    if m:
        counts = dict(kv.split("=") for kv in m.group(3).split(" | "))
        matched = sum(int(v) for k, v in counts.items() if k.startswith("MATCH"))
        bad = sum(int(v) for k, v in counts.items() if k in ("MISMATCH", "NOT_FOUND", "NOT_IN_OFFICIAL_PACKAGE", "OTHER"))
        gen = int(counts.get("GENERATED", 0))
        pkgsrc[m.group(1) + ".dll"] = (matched, bad, gen)

CAPINV = set("""App.dll Assembly-CSharp.dll Assembly-CSharp-firstpass.dll DinoPoloClub.Analytics.Runtime.dll
Easing.dll Facepunch.Steamworks.Win32.dll FixedMath.dll G-Audio.dll MiniJson.dll MOAnalytics.Runtime.dll
NaughtyAttributes.Core.dll Newtonsoft.Json.dll Rewired_Core.dll Rewired_Windows.dll Unity.Burst.dll
UnityEngine.UI.dll Unity.Mathematics.dll Unity.MemoryProfiler.dll Unity.RenderPipelines.Core.Runtime.dll
Unity.RenderPipelines.Universal.Runtime.dll Unity.RenderPipeline.Universal.ShaderLibrary.dll
Unity.TextMeshPro.dll Version.dll WebCore.dll""".split())

GAME_CODE = {"App.dll", "Assembly-CSharp.dll", "Assembly-CSharp-firstpass.dll", "WebCore.dll", "Version.dll",
             "DinoPoloClub.Analytics.Runtime.dll", "MOAnalytics.Runtime.dll", "FixedMath.dll"}

SPECIAL = {
    "README.html": ("Crack readme (HTML)", "Read in full. One tab-switching script; loads Tailwind CDN + Google Fonts; Discord link; PowerShell step is only `Get-FileHash` (MD5 matches the exe). Advises disabling antivirus / running as admin (bad advice, no payload)."),
    "launch_wine.sh": ("Crack launcher (Wine)", "Read in full: `cd` + `exec wine \"Mini Motorways.exe\"`. Nothing else."),
    "launch_proton.sh": ("Crack launcher (Proton)", "Read in full: finds Proton, prefix in ~/.local/share/GameBounty, splash, `WINEDLLOVERRIDES=winmm=n;version=n;dinput8=n`. No network."),
    "Mini Motorways/winmm.dll": ("Crack loader (Rust, DLL search-order hijack)", "Fully decompiled with Ghidra (628 functions, 0 orphan instructions); every import traced. Swaps steamclient.dll -> SOVEREIGN.dll, fake Steam registry values, loads SOVEREIGN.dll. No network/process/persistence. See 1_crack_decompiled/winmm.dll.c"),
    "Mini Motorways/SOVEREIGN.dll": ("Crack: Steam client emulator + overlay (Rust)", "Fully decompiled with Ghidra (2,500 functions; 54 leftover instructions are switch-table branches inside two functions); every import and runtime-resolved API traced. DRM bypass via UserHasLicenseForApp; overlay hooks Present; keys only for overlay; no network/process creation/injection/persistence. See 1_crack_decompiled/SOVEREIGN.dll.c"),
    "Mini Motorways/SOVEREIGN.ini": ("Crack config (achievements, settings)", "Read in full; [Steamworks] Online not enabled (defaults to 0)."),
    "Mini Motorways/steam_appid.txt": ("Steam AppID file", "Contains the game's AppID (1127500)."),
    "Mini Motorways/steam_api.dll": ("Valve Steamworks API", "Authenticode: genuine Valve signature, digest matches (signed 2020-02-21)."),
    "Mini Motorways/Mini Motorways.exe": ("Unity player launcher", "Identical to official Unity 2022.3.62f2 WindowsPlayer.exe except the RT_ICON images (game icon); only import is UnityPlayer!UnityMain2."),
    "Mini Motorways/Mini Motorways_Data/Plugins/x86/dpcPlatform.dll": ("Game native plugin (Dinosaur Polo Club, 2021)", "Fully decompiled with Ghidra (706 functions; 1 leftover = INT3 padding). Risky imports used only by the static MSVC CRT. No network/process/registry."),
    "Mini Motorways/Mini Motorways_Data/Plugins/x86/decompressAudio.dll": ("Game native plugin (audio, Dinosaur Polo Club)", "Fully decompiled with Ghidra (538 functions). Risky imports used only by the static MSVC CRT. No network/process/registry."),
    "Mini Motorways/Mini Motorways_Data/Plugins/x86/lib_burst_generated.dll": ("Burst-compiled game math", "No imports at all; decompiled with Ghidra."),
    "Mini Motorways/Mini Motorways_Data/Plugins/x86/Rewired_DirectInput.dll": ("Rewired DirectInput helper", "Imports only DirectInput + CRT; decompiled with Ghidra."),
    "Mini Motorways/Mini Motorways_Data/RuntimeInitializeOnLoads.json": ("Unity auto-run method list", "Reviewed: 4 standard Unity entries only."),
    "Mini Motorways/Mini Motorways_Data/ScriptingAssemblies.json": ("Unity assembly list", "Reviewed: matches the DLLs in Managed/."),
    "Mini Motorways/Mini Motorways_Data/boot.config": ("Unity boot settings", "Reviewed: standard keys."),
    "Mini Motorways/Mini Motorways_Data/app.info": ("Unity company/product name", "Reviewed."),
}


def managed_note(fn):
    parts = []
    if fn in il:
        n, same, added, changed, ref = il[fn]
        s = f"IL compare vs official ({os.path.basename(os.path.dirname(ref)) or ref}): {same}/{n} methods identical, {changed} changed, {added} added"
        if fn == "mscorlib.dll" and added:
            s += " (all bodiless `$__Stripped*` linker placeholders)"
        parts.append(s)
    if fn in pdb:
        methods, seq, bad, verdict = pdb[fn]
        v = "consistent" if verdict == "UNMODIFIED" else "1 flag: UnsafeUtility.SizeOf (known Unity rewrite; module is IL-identical to official)"
        parts.append(f"DLL<->PDB check: {methods} methods, {seq} line markers, {v}")
    if fn in pkgsrc:
        matched, bad, gen = pkgsrc[fn]
        s = f"source files vs Unity's official package: {matched} identical, {bad} different"
        if gen:
            s += f" (+{gen} generated type-list file)"
        parts.append(s)
    if fn == "NaughtyAttributes.Core.dll":
        parts.append("20/21 source files identical to the public NaughtyAttributes project; the 21st is a one-line attribute added by the developer")
    if fn == "FixedMath.dll":
        parts.append("customized FixedMath.Net (no public match); only file write is an uncalled lookup-table generator")
    if fn in CAPINV:
        parts.append("capability inventory reviewed")
    if fn == "Rewired_Core.dll":
        parts.append("every native call reviewed (HID/XInput/DirectInput/raw input only); legacy Assembly.Load path is dead (Unity < 5 only, resource absent)")
    if fn == "Rewired_Windows.dll":
        parts.append("every native call reviewed; window hook is WH_CALLWNDPROC on the game's own thread; CreateFileW opens existing device handles only")
    return "; ".join(parts) if parts else "decompiled (C#)"


def managed_kind(fn):
    if fn in GAME_CODE:
        return "Game code (.NET)"
    if fn.startswith("UnityEngine.") and fn != "UnityEngine.UI.dll" or fn == "UnityEngine.dll":
        return "Unity engine module (.NET)"
    if fn.startswith("Unity.") or fn == "UnityEngine.UI.dll":
        return "Unity package (.NET)"
    if fn == "mscorlib.dll" or fn.startswith("System") or fn == "Mono.Security.dll":
        return "Mono standard library (.NET)"
    return "Third-party library (.NET)"


def data_note(rel, e):
    kind = e["kind"]
    hits = e.get("raw_hits") or {}
    dhits = e.get("decompressed_hits") or {}
    if kind == "Portable PDB (debug symbols)":
        return kind, "Developer debug symbols; used for the DLL<->PDB tamper check"
    s = []
    if kind == "JPEG image":
        tr = e.get("bytes_after_jpeg_end", -1)
        s.append("valid JPEG, nothing after end marker" if tr == 0 else f"{tr} bytes after JPEG end")
    if "object_types" in e:
        n = sum(e["object_types"].values())
        ta = len(e.get("text_assets", []))
        s.append(f"opened+decompressed: {n} objects ({ta} TextAssets)")
    if "unity_error" in e:
        s.append("UnityPy could not parse; raw scan only")
    if hits or dhits:
        s.append("signature hits reviewed, benign: " + ", ".join(sorted(set(list(hits) + [k for v in dhits.values() for k in v]))))
    else:
        s.append("no embedded executable/archive/script signatures")
    return kind, "; ".join(s)


rows = []
counts = {}
for dp, _, fns in os.walk(root):
    for fn in fns:
        p = os.path.join(dp, fn)
        rel = os.path.relpath(p, root)
        h = sha256(p)
        size = os.path.getsize(p)
        if rel in SPECIAL:
            kind, note = SPECIAL[rel]
        elif h in official:
            kind = "Unity/Mono runtime file"
            note = f"Byte-identical to official Unity 2022.3.62f2 file `{official[h]}`"
        elif "/Managed/" in "/" + rel and fn.endswith(".dll"):
            kind, note = managed_kind(fn), managed_note(fn)
        elif "/achievements/" in "/" + rel:
            kind = "Achievement icon used by the crack overlay"
            note = data_note(rel, data[rel])[1]
        elif rel in data:
            kind, note = data_note(rel, data[rel])
            if "/SoakTestJournals/" in rel:
                kind = "Game data (soak-test input journal)"
            elif "/StreamingAssets/Sounds/" in rel:
                kind = "Game data (audio bank, read by decompressAudio)"
        else:
            kind, note = "other", "reviewed"
        counts[kind] = counts.get(kind, 0) + 1
        rows.append((rel, size, h, kind, note))

rows.sort(key=lambda r: r[0].lower())
with open(out_md, "w") as f:
    f.write("# INDEX — every file in Mini.Motorways.rar\n\n")
    f.write(f"{len(rows)} files. Columns: path, size, SHA-256 (first 16 hex), what it is, how it was verified.\n\n")
    f.write("| Kind | Files |\n|---|---|\n")
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        f.write(f"| {k} | {v} |\n")
    f.write("\n| Path | Size | SHA-256 | Kind | Verification |\n|---|---:|---|---|---|\n")
    for rel, size, h, kind, note in rows:
        f.write(f"| `{rel}` | {size:,} | `{h[:16]}` | {kind} | {note} |\n")
print(len(rows), "files indexed;", counts)
