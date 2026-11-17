# c370 / c116 live-ops: v2.17.13 (`dx=1774`) restore + 37-map binary decoder (2026-11-17, d3 clock)

## Root cause of the outage (`2026-11-14 16:21` -> `2026-11-17 09:06`)

1. `territorial.io` updated its client from `2.17.9` (`dx=1773`, `12 Nov 2026`) to `2.17.13` (`dx=1774`, `14 Nov 2026`, `rVersion=26`).
2. `c116\live_game_js.js` (and `c110\live_game_js.js`) was still on `dx=1773`, causing every `Server 0` connection to close immediately with `socket close index 0 error 4211`.
3. Full AST skeleton comparison between `fresh_today.html` (`1773`) and `fresh_20261117.html` (`1774`) confirmed:
   - All lobby and match WebSocket packet bit layouts are **unchanged**.
   - Total maps expanded from `25` (`13` realistic) to **`37` (`25` realistic)**, adding 12 new realistic maps (`25: Denmark`, `26: Iberia`, `27: Japan`, `28: India`, `29: Black Sea`, `30: Italy`, `31: Iceland`, `32: Anatolia`, `33: Falklands`, `34: Antarctica`, `35: Hong Kong`, `36: Singapore`).
   - Realistic map storage moved from the old 102 KB inline path-string (`aOt`) to arithmetic range-coded contour binaries (`/maps/0-1.bin` .. `/maps/24-1.bin`, 69,945 bytes total across all 25 maps).

## Fix applied on `d3`

1. Downloaded all 25 official `/maps/<0..24>-1.bin` files into `c116\maps\`.
2. Ported `dx=1774` (`2.17.13`), `aOj=37 / aOk=25`, `aOm` metadata (`zX[25..36]` + `aPu[13..24]`), and the exact `1774` range-coder contour decoder (`__decMapBin1774`) with all 25 `.bin` maps embedded synchronously in `aOt()` into `live_game_js.js` (preserving 100% of `live_dictionary.json`, `headless-bot.mjs`, and `__fx.strategyBot` symbols/hooks).
3. Verified in VM sandbox (`smoke_test_1774.mjs`):
   - Maps `0..24`: **`vs1773_diffPx = 0`** across every single pixel compared to `1773`.
   - Maps `25..36`: all 12 new maps decode synchronously and cleanly with zero XHR dependency.
4. Backed up `c116\live_game_js.js.bak-1773` and `c110\live_game_js.js.bak-1773`, deployed updated `live_game_js.js` to both `c116` and `c110`, rotated `c116\tsb-apex-squad.log` -> `tsb-apex-squad.log.pre1774-20261117-090621`, and restarted `node_apex.exe tsb-apex-squad.mjs` (`PID 39520`).

## Post-restart verification (`2026-11-17 09:06 ~ 09:09` d3 local time)

- `error 4211`: **0**
- `SELF-CHECK REDACTED`: **0**
- `mint ok`: **22** in first ~2 minutes (`4s ~ 10s` silent passes, `clicks=0`), **21** bots already `sendTokenToLobby success` in Room 0 under stealth ordinary names (`tag=[G3K]`, `taggedInRoom=0`).
- Live lobby room cards on new map IDs (`map=33`, `map=28`, `map=34`, `map=32`) parsed and queued cleanly.
