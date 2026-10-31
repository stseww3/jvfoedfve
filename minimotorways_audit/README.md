# Mini.Motorways.rar — backdoor audit

> Repository copy: report, file index and tool sources only (`tools/` = `3_tools/`).
> The decompiled crack code and raw check outputs are only in the delivered `MiniMotorways_audit.zip`.

**Verdict: no backdoor, no malware, no data theft found.**
Every executable file in the archive is either identical to the official original
(byte-for-byte or method-for-method) or was fully decompiled and reviewed by hand.
Nothing was executed; the whole analysis is static.

The real risks are not hidden code:

1. It is a pirated copy with a Steam crack (DRM bypass). Legal risk is yours.
2. `README.html` tells users to **disable antivirus** and **run as Administrator**.
   Neither is needed for this crack to work. Don't do either; that advice is how
   other, actually malicious, cracks get their foothold.
3. The crack writes fake "Steam is running" values under
   `HKCU\Software\Valve\Steam` (harmless, but can confuse a real Steam install).

| Item | Value |
|---|---|
| Archive | `Mini.Motorways.rar`, 186,241,986 bytes, 446 files |
| SHA-256 | `214d349e4da10e2135b635dce4e3fddb19c76b20ae9abc3b6faa0fa39294e6ae` |
| Game | Mini Motorways (Dinosaur Polo Club), Steam AppID 1127500 |
| Engine | Unity 2022.3.62f2, Mono backend, 32-bit Windows, build target `win32.steam` |
| Crack | "SOVEREIGN" (author tag `sov`, branding Lumisere / GameBounty), written in Rust |

## What was checked, and how

| Component | Files | Method | Result |
|---|---|---|---|
| Unity engine | `UnityPlayer.dll`, `UnityCrashHandler32.exe` | Byte compare with Unity's official 2022.3.62f2 Windows Mono package + Authenticode | **Byte-identical**, valid Unity signatures |
| Game launcher | `Mini Motorways.exe` | Byte compare with official `WindowsPlayer.exe` | Identical except the 9 icon images (Unity swaps in the game icon at build time) |
| Mono runtime | `mono-2.0-bdwgc.dll`, `MonoPosixHelper.dll`, 19 config files | Byte compare | **Byte-identical** |
| Mono standard library | `mscorlib`, `System`, `System.Core`, `System.Xml`, `System.Data`, `Mono.Security` + 5 more | Method-by-method IL compare with the copies inside Unity's official 2022.3.62f2 Editor installer (4,652 assemblies extracted) | **0 changed / 0 added** across 40,105 methods. mscorlib's 60 "extra" entries are bodiless `$__Stripped*` placeholders the linker leaves on COM-interop interfaces |
| UnityEngine modules | 36 DLLs | IL compare with official copies | **0 changed / 0 added** |
| Newtonsoft.Json | 1 DLL | IL compare with Unity's official package (13.0.2) | **2,338 / 2,338 identical** |
| Facepunch.Steamworks | 1 DLL | IL compare with official NuGet 2.3.3 | **1,247 / 1,247 identical** |
| Steam API | `steam_api.dll` | Authenticode | Genuine Valve file, digest matches Valve's signature of 2020-02-21 |
| Game code (Dinosaur Polo Club) | `App.dll` (13,964 methods), `WebCore`, `Version`, analytics, `G-Audio`, … | DLL ↔ debug-symbol (.pdb) consistency + full capability inventory | Unmodified; PDBs come from the developer's CI (`/Users/mumbai/.buildkite-agent/.../mini-motorways/...`); network only to the developer, Steam, Apple |
| Unity packages | UI, TextMeshPro, URP, SRP Core, Burst, Mathematics, MemoryProfiler | The .pdb records a SHA-256 of every source file the DLL was compiled from; each one compared with Unity's official package files (registry tarballs for Burst 1.8.21, Mathematics 1.2.6, MemoryProfiler 1.1.6, TextMeshPro 3.0.7; the official 2022.3.62f2 Editor installer for SRP Core/URP 14.0.12 and UGUI 1.0.0) + DLL ↔ .pdb consistency + capability inventory | **464 / 464 source files byte-identical to Unity's originals.** The only other inputs are 4 files from Unity's own type-list source generator (one method returning two data tables of file paths and type names) |
| Other third-party code | NaughtyAttributes, FixedMath.Net, MiniJson, Easing, G-Audio | Source hashes vs every version in the public git history (where public) + DLL ↔ .pdb consistency + capability inventory | NaughtyAttributes: 20/21 files identical to the public project (the 21st is a one-line attribute the developer added). FixedMath.Net was customized by the developer; pure math, its only file write is an uncalled lookup-table generator. MiniJson, Easing, G-Audio (paid asset): no public reference; nothing sensitive beyond their features |
| Rewired (paid controller library) | `Rewired_Core`, `Rewired_Windows` | Capability inventory + review of every native call | Controller/HID/XInput/DirectInput only; see notes |
| Native plugins | `dpcPlatform`, `decompressAudio`, `lib_burst_generated`, `Rewired_DirectInput` | Full Ghidra decompile + review of every sensitive import's call sites | Clean |
| **The crack** | `winmm.dll`, `SOVEREIGN.dll` | Full Ghidra decompile (628 + 2,500 functions, incl. hook routines Ghidra misses on a normal pass), every import and dynamically resolved API traced to its callers | Steam emulator, no backdoor (details below) |
| Data | 363 non-executable files | Every asset bundle and Unity data file opened and decompressed (UnityPy); raw and decompressed bytes searched for PE/ELF/Mach-O/.NET/ZIP/RAR/7z/script signatures; all `TextAsset`s listed; JPEGs checked for data after the end marker; `boot.config`, `RuntimeInitializeOnLoads.json`, `ScriptingAssemblies.json`, embedded .NET resources reviewed | Clean. The only 3 signature hits are benign: the `#!/bin/sh` line of `launch_wine.sh`, the README's "type powershell" hash-check step, and the Unity Timeline class name `BasicScriptPlayable` |

## The crack in detail

### `winmm.dll` — loader ("SOVEREIGN Steamclient Proxy")
Windows loads DLLs from the game folder first, so this file is loaded instead of the
system `winmm.dll`. It forwards all real `winmm` functions to the system copy, then:

- hooks `LoadLibrary*` / `GetModuleHandle*` so a request for `steamclient.dll`
  returns `SOVEREIGN.dll`; every other DLL passes through untouched;
- writes fake "Steam is running" values (`ActiveUser`, `pid`, `Universe`,
  `SteamClientDll`) to `HKCU\Software\Valve\Steam\ActiveProcess`;
- sets the `SteamAppId` / `SteamGameId` environment variables;
- starts one thread that tries up to 30 times to load `SOVEREIGN.dll`, then starts its overlay.

Imports: 3 registry functions, kernel32, ntdll file I/O used by Rust's standard
library, the C runtime. No network library at all. 628 functions decompiled,
0 failures, 0 instructions left outside functions.

### `SOVEREIGN.dll` — Steam client emulator + overlay
- Implements the Steam client interfaces locally. Achievements are stored in
  `SOVEREIGN.ini`; Steam Cloud saves are kept in local files.
- **DRM bypass:** answers `UserHasLicenseForApp` as "owned". That is the crack.
- **Overlay:** hooks the D3D9/D3D11/D3D12/OpenGL `Present` call with an embedded
  MinHook-style hooking engine. While patching, it pauses only the game's own
  threads (thread list filtered by `GetCurrentProcessId`).
- **Keyboard:** `GetAsyncKeyState` and raw input are used only for overlay
  navigation (Shift+Tab, arrows, Enter, Esc) against a fixed key table. Nothing is
  recorded, written to disk, or sent anywhere. Not a keylogger.
- **Registry:** only Steam keys (`ActiveProcess`, `Apps\<AppID>`, `RunningAppID`).
- **Process access:** opens the real Steam client's process with query-only rights
  to check whether it is still running and whether its admin level matches the
  game's (to show a warning in "Online" mode, which is off by default). It never
  writes to, injects into, or starts any process.
- **Crash handling:** a vectored exception handler writes a local crash report;
  Rust's panic backtrace loads `dbghelp.dll`. Wine/Proton detection selects the Linux path.
- **Not present anywhere:** network APIs (no ws2_32 / wininet / winhttp, not even as
  strings resolved at runtime), process creation, injection into other processes,
  persistence (Run keys, services, scheduled tasks), browser/password/wallet/Discord/
  clipboard access.

### Launch scripts and `README.html`
- `launch_wine.sh` is three lines: `cd` into the game folder, `exec wine "Mini Motorways.exe"`.
- `launch_proton.sh` finds a Proton install under `~/.steam` / `~/.local/share/Steam`,
  creates a Wine prefix in `~/.local/share/GameBounty/Mini Motorways`, shows a
  "Brought to you by Lumisere" splash, and runs the game with
  `WINEDLLOVERRIDES="winmm=n;version=n;dinput8=n"` so the bundled `winmm.dll` is used.
  (`version.dll` / `dinput8.dll` are generic overrides from the crack group's
  template; neither file exists in this archive.) No downloads, no network.
- `README.html` has one small script that only switches tabs, loads Tailwind CSS from
  `cdn.tailwindcss.com` and Google Fonts when opened, and links the crack group's
  Discord (`discord.gg/ZxfHKtC9Ba`). Its PowerShell step is just
  `Get-FileHash "Mini Motorways.exe" -Algorithm MD5`, and the MD5 it lists
  (`9710bcac8f23fa176271297b7c227c35`) matches the real file. No clipboard tricks,
  no commands to paste. Its only real problem is the "disable antivirus / run as
  admin" advice.

## Notes on the parts that could not be diffed against an official binary

- **Game code** has no public binary or source to diff against. It was
  verified against the shipped debug symbols (every one of 73,187 source-line
  markers in `App.dll` still lands on a real instruction; method counts and PDB IDs
  match) and by listing every call to networking, process, code-loading, registry,
  file, clipboard, screenshot, microphone/camera/location and native APIs. All
  calls belong to normal features (analytics, bug reports, challenges, leaderboards,
  Steam Cloud sync for cross-platform saves, photo mode).
- **Rewired** contains a routine that can load a .NET assembly from raw bytes. It is
  Rewired's legacy loader for Unity 4: it only runs when the Unity version is below
  5.0 (this game is 2022.3), the second entry point has no callers anywhere, and the
  encrypted resource it needs (`Rewired.Decrypter.bin`) is not in the DLL. Its
  window hook is `WH_CALLWNDPROC` on the game's own thread (not a system-wide
  keyboard hook) and it opens only existing device handles.
- **Microphone:** G-Audio has an optional "ask for microphone permission before
  loading a level" switch; no code anywhere ever calls `UnityEngine.Microphone`.

## What is in this package

| Folder | Contents |
|---|---|
| `1_crack_decompiled/` | Full readable pseudo-C of `winmm.dll` and `SOVEREIGN.dll`, plus the crack's ini, launch scripts, README and extracted strings |
| `2_audit_results/` | Raw outputs of every check above (IL diffs, capability inventory, PDB check, data scan, resources, orphan-code listings) |
| `3_tools/` | Source of every tool and script used, so every result can be reproduced |
| `INDEX.md` | Every one of the 446 files, what it is, and how it was verified |

The decompiled code of the game itself (C# of all 71 .NET assemblies and pseudo-C of
the four native plugins) is Dinosaur Polo Club's and the library vendors' proprietary
code, so it is delivered separately and privately, not in this package.
