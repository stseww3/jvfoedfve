# c370 / c116 live-ops: v2.17.14 (`dx=1775`) restore & local launch on `d3` (2026-11-20)

## Cause of initial `error 4211` on startup

1. Between `2026-11-17` and `2026-11-20`, `territorial.io` updated its client from `2.17.13` (`dx=1774`, `14 Nov 2026`) to `2.17.14` (`dx=1775`, `20 Nov 2026`, `rVersion=26`).
2. Launching `c116/node_apex.exe` with `dx=1774` immediately produced `socket close index 0 error 4211` on Server 0.
3. Captured live HTML (`fresh_20261120.html`, 639,084 bytes) via Firefox BiDi `:9228` and ran full AST skeleton diff (`deep_diff_20261120.mjs`) against `fresh_20261117.html` (`dx=1774`):
   - `S` string table (`177` entries): **100% identical**.
   - Map catalog (`37` total, `25` realistic): **100% identical**.
   - Top-level function count (`363` -> `363`): only `6` functions changed: `dR` (version bump `1774 -> 1775`, `2.17.13 -> 2.17.14`, `"14 Nov 2026" -> "20 Nov 2026"`) plus `5` DOM chat-UI cleanup functions (`pL`, `wC/wD`, `xs`, `aHA`, `aHE`).
   - All lobby/match WebSocket packet layouts, map decoding, Turnstile, and `bw.show` logic are **unchanged**.

## Fix & Live Startup (`d3`)

1. Backed up `c116/live_game_js.js` to `live_game_js.js.bak-1774-20261120` and patched `this.dx=1774;...var e1=13;` -> `this.dx=1775;...var e1=14;` (`patch_v2_17_14.mjs`).
2. Started `c136/apex_watchdog.py` (which launched and guards `c116/tun_apex_socks5.py` across `127.0.0.1:10821..10860`) and detached `c116/node_apex.exe tsb-apex-squad.mjs` with 4 Firefox BiDi donors (`:9228..:9231`, `:9228` via Clash `:7890`).
3. Live verification (`Room 529`, `4T`, `map=23`, `51` players):
   - Turnstile / BiDi stability: **`mint ok: 41/41` (`0` failures)**, `error 4211: 0`, `error 4591: 0`, `error 4563: 0`, `BiDi locked/failed: 0`, `BW-SOLVE: 0`.
   - `DYNAMIC-POOL` scaled smoothly (`10 -> 12 -> 14`) as outsiders grew `13 -> 37`, landing **13 `[APEX]` bots** (~100% full-team fill in a 51-player 4T room).
   - **`OPENING-CHECK`: 13/13 (100%) OK** (`Curry t=700 terr=2662`, `Qin t=720 terr=2608 avgMs=5.74ms skip=0`), `node_apex.exe` RSS `~2.7 GB`, left running continuously per admin request (`#129719`).
