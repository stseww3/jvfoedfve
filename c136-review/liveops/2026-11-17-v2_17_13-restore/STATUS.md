# c370 / c116 live-ops: v2.17.13 (`dx=1774`) restore + 37-map binary decoder + `bw.show` 360° solver + `[APEX]` Player XX fix (2026-11-17, d3 clock)

## Root cause of the outage (`2026-11-14 16:21` -> `2026-11-17 09:06`)

1. `territorial.io` updated its client from `2.17.9` (`dx=1773`, `12 Nov 2026`) to `2.17.13` (`dx=1774`, `14 Nov 2026`, `rVersion=26`).
2. `c116\live_game_js.js` (and `c110\live_game_js.js`) was still on `dx=1773`, causing every `Server 0` connection to close immediately with `socket close index 0 error 4211`.
3. Full AST skeleton comparison between `fresh_today.html` (`1773`) and `fresh_20261117.html` (`1774`) confirmed:
   - All lobby and match WebSocket packet bit layouts are **unchanged**.
   - Total maps expanded from `25` (`13` realistic) to **`37` (`25` realistic)**, adding 12 new realistic maps (`25: Denmark`, `26: Iberia`, `27: Japan`, `28: India`, `29: Black Sea`, `30: Italy`, `31: Iceland`, `32: Anatolia`, `33: Falklands`, `34: Antarctica`, `35: Hong Kong`, `36: Singapore`).
   - Realistic map storage moved from the old 102 KB inline path-string (`aOt`) to arithmetic range-coded contour binaries (`/maps/0-1.bin` .. `/maps/24-1.bin`, 69,945 bytes total across all 25 maps).

## Post-16:15 deadlock + BiDi flash/CPU spike fix (`2026-11-17 20:34`, d3 clock)

1. **`rotateClanTag('match-finished')` `V7K` fallback**:
   - After Match 1 (`Room 4225`) ended at `16:15:41`, `rotateClanTag()` filtered out `"APEX"` from single-element `CLAN_TAG_POOL = ["APEX"]` and fell back to `|| 'V7K'`, switching `activeClanTag` to unregistered `[V7K]`.
   - Server 1 stripped `[V7K]` to `"Player XX"`, while existing slots still held `"[APEX] Player XX"`; `verifiedApexIndices` counted `[APEX]` bots while `hasRightTag` (`line 2077`) required `[V7K]`, blocking all bots from readying for 4 hours and triggering `triggerRetag` reconnect/captcha storms.
   - Fix: `rotateClanTag` stays on `CLAN_TAG_POOL[0]` (`"APEX"`) when `choices` is empty, post-match reset retains `[${activeClanTag}]`, `verifiedApexIndices` enforces `startsWith('[' + activeClanTag + ']')`, and `"Player XX"` slots stop spamming Server 1 retags (`300s` cooldown).
2. **Firefox BiDi concurrency race & window flashing**:
   - `doOneTimed` (`92s` `Promise.race`) previously released `donorMintInflight` while the underlying `doOne()` was still executing `killFirefoxOnPort` / `spawn(firefox)` / `session.new`, causing two coroutines to fight over the same `:9228..:9231` profile and loop `BiDi session locked` + `execSync('powershell ...')`.
   - Fix: removed racing `Promise.race` in favor of serialized `donorMintChains` with an internal `hardDeadline`, async `killFirefoxOnPort` (`execFile`), `about:blank` initial launch + `browser.sessionstore.resume_from_crash=false` + `sessionstore-backups` cleanup, and `130s` outer guard in `headless-bot.mjs`.
3. **Live verification & clean shutdown (`2026-11-17 20:34 -> 21:04`, d3 clock)**:
   - `mint ok: 55`, `BW-SOLVE: 11`, **`error 4591: 0`**, **`BiDi session failed/locked: 0`**, zero window flashing.
   - Completed Match 1 (`Room 5045`, `3T`, 64 humans, `squad=15`, `Qin` 21st `peak=32,289`) -> auto-transitioned (`[APEX]`) -> Completed Match 2 (`Room 5074`, `4T`, 93 humans, `map=28`, `squad=11`, `Senna` **9th/93 `peak=109,220 (24.6%)`**, `TokyoGhoul` 10th/93 `peak=27,613`) -> auto-transitioned (`[APEX]`) -> Launched Match 3 (`Room 5101`, `3T`, 111 humans, `squad=25`).
   - Per admin request (`#98067`), cleanly stopped `node_apex.exe` and all donor `firefox.exe` processes (`CPU` back to ~`9%`). Note for future large `K>=25` rooms: `tsb-apex-squad.mjs` `stalledPolls` currently only triggers when `s.tick > 0`, so 22 bots that stalled at `tick=0` during a `25`-bot Server 3 spawn burst stayed un-reaped until `TokyoGhoul` played solo.

## Root causes of `2026-11-17 09:06 -> 15:55` 0-match deadlock (`Player XX` + `bw.show` + CF burn)

1. **`2.17.13` `"Player XX"` rule + unregistered tag stripping**:
   - Live lobby audit (`147` Room 0 players) showed `70/147` players are in `"Player XX"` / `"[CLAN] Player XX"` mode (accounts with `0` punishments `aSJ=aSK=aSL=0`).
   - In `"Player XX"` mode, the server **strips unregistered 3-letter tags** (`[T7L]`, `[G3K]`, `[U2C]`, `[Y5B]`, `[NPL]`) down to `"Player XX"`, causing `verifiedApexIndices` (`!startsWith("Player ")`) to stay at `0`.
   - Recognized clan tags like **`[APEX]`** are preserved by the server as `"[APEX] Player XX"` on healthy saved accounts while fresh 0-day accounts or `4591`-flagged slots still strip to `"Player XX"`.
2. **`bw.show` 16-tile solver bugs (v1)**:
   - v1 in `patch_c116_bw_and_bidi.mjs` only searched `-75°..+75°` while live `bw.show` tiles rotate full `0°..360°` (e.g. `155°`, `160°`, `165°`), used fixed `th=8` (amputating thinner glyph strokes), and heavy 3x3 blur (confusing `2` vs `5` and `P` vs `9`), causing `0/34` pass rate and `4591` bot-detection after `>6` reloads.
3. **`eh(5)` Propaganda spam & `4563` Turnstile quota burn**:
   - `b1.eg.eh(5)` requests Propaganda ad popups (`aXA()` -> `bX.eS.ei`), not name unlock.
   - `tsb-apex-squad.mjs` cleared `c.freshToken = false` on `lobbyFailCount >= 4` during `error 4563` lobby bounces, exhausting the `90/90` hourly Cloudflare Turnstile budget.

## Fix applied on `d3` (`patch_c116_bw_and_bidi.mjs` v2)

1. **Map & `1774` bundle (`patch_v2_17_13.mjs`)**: all 25 `.bin` maps embedded synchronously in `live_game_js.js` (`vs1773_diffPx = 0` on `0..24`, clean decode on `25..36`).
2. **Upgraded `bw.show` solver (`0°..360°` sharp ZNCC + adaptive `th`)**:
   - Searches full `0°..360°` (step `5°`) across 5 subpixel shifts, with sharp 5-tap kernel `[10, 1.5]` + zero-mean normalized cross-correlation (ZNCC) and `th=8 -> th=7` fallback.
   - Caps consecutive reloads at `3` (falling back to best cluster cut instead of triggering `4591` after 7 reloads) with human-like `1.1s..1.7s` submit delay.
3. **`[APEX]` Player XX compatibility + Turnstile preservation**:
   - Restored `CLAN_TAG_POOL = ["APEX"]` so non-flagged accounts display `"[APEX] Player XX"` in Room 0 and automatically pass `verifiedApexIndices` (while any tag-stripped slot stays `"Player XX"` and is safely excluded from `DYNAMIC-POOL`).
   - Removed `eh(5)` Propaganda polling; raised `lobbyFailCount` token discard threshold from `4` to `24` so `4563` lobby bounces keep valid 60-min Turnstile passes; synced `d122` right before `openMultiplayer(0)` in `readyToEnter`.
   - Preserved `tsb-accounts.json` backup at `tsb-accounts.json.bak-20261117` and restarted `node_apex.exe tsb-apex-squad.mjs` (`PID 46028`).
