# Decompiled source archive — static security review

> Complements the binary audit in `README.md` / `INDEX.md` (which covered the original
> `Mini.Motorways.rar`, including the crack). This review covers the decompiled archive shared
> in the group. Static only: nothing from the archive was built or executed.

| Item | Value |
|---|---|
| Archive | `MiniMotorways_source_private.zip`, two uploads (`new_files` and `Lost` release tags) |
| SHA-256 (`new_files`) | `3d3e7c2aee2af8322b640d2e39476e225a33eb6ed39ded53a0a433e570eaf006`, 9,645 entries |
| SHA-256 (`Lost`) | `0f402f2e6cbfb9d901acb15f4bd530a3f1b216108d4cacb16fcfed3e0796c309`, 9,644 entries |
| Difference | Every entry has the same CRC-32 in both; the `Lost` upload only lacks `README.md` (the ownership and do-not-redistribute notice) |

## Verdict

**No malicious code found.** The decompiled game and third-party code contain no process
execution, no runtime code generation, no reachable dynamic assembly loading, no registry,
clipboard, microphone, camera or location access, and no raw sockets. Every network destination
belongs to the studio, Steam or Apple. Analytics is opt-in. This agrees with the binary audit.

Opening or reading the archive is safe: it holds C# and pseudo-C text plus standard Mono class
library resources (collation tables, system sounds, message-box icons, one XML file). No file
starts with a PE, ELF, Mach-O or Java class signature.

## Method

- Scope: game assemblies (`App`, `Assembly-CSharp(-firstpass)`, `WebCore`, `Version`,
  `DinoPoloClub.Analytics.Runtime`, `MOAnalytics.Runtime`, `FixedMath`) and third-party
  libraries (`Rewired_Core`, `Rewired_Windows`, `Facepunch.Steamworks.Win32`, `Newtonsoft.Json`,
  `G-Audio`, `NaughtyAttributes.Core`, `MiniJson`, `Easing`). Unity engine modules and Mono class
  libraries were excluded because the binary audit showed them IL-identical to Unity's official
  2022.3.62f2 copies.
- Pattern scan for sensitive APIs, then every hit read in context.
- File-type and magic-number scan of every file in the archive.

## Results

| Check | Hits | Finding |
|---|---|---|
| Process execution (`Process.Start`, `ProcessStartInfo`) | 1 | False positive: a method call named `StartRealtimeTimer`. No process execution. |
| Dynamic assembly loading (`Assembly.Load*`) | 3 | All in `Rewired_Core`: the legacy loader for platform DLLs stored as text assets. Guarded by a Unity-version check (runs only below Unity 5.0); this game is Unity 2022.3, so it cannot run. Matches the binary audit. |
| Runtime code generation (`Reflection.Emit`, CodeDom) | 0 | — |
| Registry | 0 | None in managed code. The crack's registry writes are native and covered by the binary audit. |
| Clipboard, microphone, webcam, location | 0 | — |
| Raw networking (`Socket`, `TcpClient`, `UdpClient`, `WebClient`, `HttpClient`) | 0 | All traffic uses `UnityWebRequest` (14 call sites in 7 files). |
| Raw IP addresses | 0 | Only assembly version strings matched. |
| Environment variables | 6 | Three developer overrides for the analytics domain, application id and key. Benign. |
| Base64 decoding | 5 | Four in Newtonsoft.Json (standard `byte[]` handling); one reads the local analytics event cache. |
| Polymorphic JSON (`TypeNameHandling.All/Auto/Objects`) | 0 | No Newtonsoft type-name deserialization in game code, so save and cache files cannot trigger gadget chains. |
| Remote content | 1 | Asset bundles from `build.dinopoloclub.com`, only when the `LoadRemotePrefabs` feature flag is on and not in the editor. Asset bundles carry data, not executable code. |

### Network destinations

| Destination | Purpose |
|---|---|
| `api.dinopoloclub.com` | Leaderboards and histograms, daily/weekly challenges, deep-linked challenges, diagnostics (bug reports with attachments), Steam account linking for cloud sync |
| `build.dinopoloclub.com` | Remote asset bundles (feature-flagged, see above) |
| `dinopoloclub.com` | Support page link |
| `*.execute-api.ap-southeast-2.amazonaws.com` | The studio's analytics ingestion (AWS API Gateway, production and development stages) |
| `api.steampowered.com`, `store.steampowered.com`, `steamcommunity.com` | Steam Cloud file listing, store and community links |
| `apps.apple.com`, `apple.co` | Store links |

Other URL strings (`james.newtonking.com`, `guavaman.com`, `w3.org`, `nuget.org`, `github.com`)
are documentation or XML-namespace constants inside libraries, not requests.

### Analytics and privacy
- Sending is gated: data is sent only when consent is `Accepted`. The default is
  `NotYetGiven`; the main menu prompts once, and the Options screen has a toggle. `Declined`
  stops collection.
- Pending events are cached locally as Base64-encoded JSON lines and parsed into a fixed event
  type.

### Native interop
`dpcPlatform` (67 imports: pathfinding, vehicle acceleration, audio DSP, GIF encoding,
multi-display, Apple service bridges) and `decompressAudio` (2 imports). Both native libraries
were fully decompiled and reviewed in the binary audit: clean.

## Observations (not malicious)

- **Embedded service credentials.** The client contains the studio's analytics API keys
  (production and development) and application id. This is normal for a game client (ingestion
  keys), but they belong to the studio. Publishing the decompiled archive exposes them; they
  should not be reused. Values are intentionally not reproduced here.
- **Public exposure.** Both uploads are downloadable without authentication from a public
  GitHub release. The archive is the studio's proprietary code, and the second upload removed
  the notice saying so.
- **Real risks are the ones from the binary audit:** the download was a pirated copy with a
  Steam crack, its README advises disabling antivirus and running as Administrator (neither is
  needed), and the crack writes fake Steam values to the registry.
