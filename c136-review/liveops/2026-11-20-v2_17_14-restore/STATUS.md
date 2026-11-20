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

## CPU 100% Root-Cause Investigation & 3-Phase Optimization (`patch_c116_cpu_fix.mjs`)

On Ryzen 7 9700X (8C/16T), `node_apex.exe` pegged all 16 threads at ~95-100% CPU both while idle in lobby and during 19-22 bot mid-game matches. Isolated and fixed all three independent bottlenecks (clean backups saved as `*.bak-pre-cpufix-20261120`):

### Phase 1 — Idle Lobby Thumbnail Render Storm & Spawn Coordinator Freeze (**Live Verified**)
- **Root causes**:
  1. `headless-bot.mjs` used `.replace('bV.zf.dk();', '')` (missed 2nd call inside `aOt()` realistic-map decoder) and did not disable `bq.wC.ee()` (lobby 256×256 preview thumbnail renderer) or 2.17.x `be.a7W`/`be.a3K`. Every ~20s lobby card rotation triggered all 39 idle worker threads to generate full map terrain + preview thumbnails simultaneously (~1.18s × 39 = 46 CPU-seconds + 4.76 GB canvas RAM bloat).
  2. `spawn-coordinator.mjs` returned uncached `this.lastPlan` without refreshing `lastSolvedAt`, causing `tsb-apex-squad.mjs` to re-solve spawn on every tick (`2,417ms` main-thread freezes) and keep firing after the 22s spawn window.
- **Fixes**: `.replaceAll('bV.zf.dk();', '')`, disabled `bV.zf` / `bq.wC` / `be.a7W` / `be.a3K`, marked cached freeze returns + 350ms fallback budget in `spawn-coordinator.mjs`, and 22s spawn-window cutoff in `tsb-apex-squad.mjs`.
- **Live results**: Idle lobby CPU (25 bots) dropped from **`15.12 / 16` cores (94.5%, 4.76 GB RSS)** → **`0.12–0.44 / 16` cores (0.8%–2.7%, 1.3–1.5 GB RSS)**; `BACKEND-SPAWN-COORD` dropped from **`2,417ms` → `322–374ms`** with 0 mid-game spam.

### Phase 2 — `v27-team-live.js` Hot-Loop `O(pixels × humans)` Cache (**Live Verified**)
- **Root cause**: `Strategy.analyze()` and `General.searchWater()` called `Policy.isProtectedSquadMate(g, o)` per border/coast pixel (300k–500k× per `searchWater` every 45 ticks), which ran un-cached `isBossNpl()` (28 `.includes()` + RegExp) and `vRoster()` → `vRoomKey()` (FNV-1a hash of all 150 human names on every pixel). Micro-benchmark: 300k checks dropped from **`910.5ms` → `1.225ms` (743× faster)**.
- **Fixes (100% behavior-preserving)**: Per-match (`g.pixels`) caches for `vRoomKey`, `_vRosterMask` (`Uint8Array(512)`), `isBossNpl`, `isSquadName`; per-tick (`g.t`) caches for `hasWildOutsidersAlive` and `isProtectedSquadMate`; same-tick online dedup for `analyze()`; hoisted `Math.exp(decay * dc)` per BFS ring; reused typed arrays in `V27.compSize`.
- **Live results (same `map=22`, 22 bots, `Room 803` win at 96.8% map)**: `[HL-SLOW-TICK]` dropped from **`2,274` → `2` (1,137× reduction)**; `afterTick()` dropped from `avgMs=6.3–7.8ms, maxMs=1,923ms` → **`avgMs=0.23–1.49ms, maxMs=3.3–24.1ms`** (`~0.45 / 16` cores across all 22 bots).

### Phase 3 — `live_game_js.js` Engine `vm.Context` Global-Proxy Deopt (**Offline Verified 9.18×–28× Faster, Staged on Disk**)
- **Root cause**: Profiling all 39 subsystems of `n8()` / `nD()` on a 512-player `map=22` match revealed `aG.ee()` (`gd()` territory expansion) took **`82.7%` (`9,939ms / 655 ticks`, peak `56.84ms/tick`)** and `ag.ee()` (pure-visual `Math.random()` nameplate rect search `aO2`) took **`8.8%` (`1,056ms`)**. Running `live_game_js.js` at top level of `vm.runInContext` forced every access to hot globals (`aFA`, `ad`, `ah`, `bv`, `bO`, `gX`, `gZ`, `ga`) through Node.js V8's C++ `ContextifyContext` named-property interceptor.
- **Fixes (`headless-bot.mjs`)**:
  1. Wrap `live_game_js.js` in an IIFE `(function(){ ... Object.defineProperties(window, { ...get()... }); })()` so all internal simulation globals become fast V8 lexical closure slots while all 480 top-level symbols remain live-readable on `window` for `page.js` / `v27-team-live.js` / `evalJs`.
  2. Strip pure-visual `ag.aO2` (client-only `Math.random()` nameplate layout) and `ad.aKw` (viewport dirty-rect check while `be.render` is a no-op).
- **Offline benchmark (`512` players, `map=22`)**:
  - 500 ticks: **`4,994.1ms` (`9.99ms/t`) → `543.9ms` (`1.09ms/t`, `9.18×` faster)**, 100% bit-exact state parity (`sumLand=322583, top0=916`).
  - 1,500 ticks (early + mid + late): **`>45,000ms` (`>30ms/t`, timed out) → `1,579.1ms` (`1.05ms/t`, `~28×` faster)**, 100% bit-exact pixel+balance hash parity (`hash=3843778001`).
  - Full-stack integration (`page.js` + IIFE `live_game_js.js` + `v27-team-live.js`, 1,500 ticks): `0` errors, `replayLen=410`, `2.85ms/t` combined (projected **~1.5–2.0 / 16 cores total** for 22 bots in mid-game instead of 16/16 pegged).
- **Deployment & Live Verification (`PID 34968`, restarted cleanly at `22:45:20` with `free=24` Turnstile mint headroom)**:
  - All 40 workers booted with `0` errors (`err.log` empty, `hlErr=0`), `24` Turnstile mints succeeded cleanly, `OPENING-CHECK: 9/9 (100%) OK`, `BACKEND-SPAWN-COORD: 14.2–67.0ms`.
  - **Idle lobby (23 bots, 40 workers)**: `node_apex = 0.38 / 16 cores (2.4%)`, `SysCPU = 10.2%–10.8%`, `RSS = 1,636 MB`, `threads >= 50% = 0` (top thread `4.8%`).
  - **Live mid-game (`Room 955`, `4T`, `map=23`, `t=1260..1440`, 9 active bots)**:
    - `node_apex`: **`0.57 / 16 cores (3.6%)`**, `SysCPU = 14.1%–15.8%`, `RSS = 2,357 MB`, `threads >= 20% = 0`.
    - Per active mid-game bot thread: **`3.9%–5.9%` of 1 core** (down from **`82%–94%` of 1 core** before Phase 3 — **~16×–18× reduction per bot**).
  - **Live late-mid-game (`Room 955`, `t=2160..2250`, 9 active bots + active boats)**:
    - `node_apex`: **`0.31 / 16 cores (2.0%)`**, `SysCPU = 12.7%–17.1%`, `RSS = 2,455 MB`, per-bot **`1.8%–3.3%` of 1 core**.
    - `HL-SLOW-TICK = 0`, `error 4229 = 0`, `error 4591 = 0`, `error 4211 = 0`, `hlErr = 0`, `skip = 0`, `afterTick avgMs = 0.58–0.67ms`.


