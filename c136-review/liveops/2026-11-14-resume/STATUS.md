# c136 live-ops: resume + proxy watchdog (2026-11-14 ~11:45 d3 clock)

Continuation of `../2026-11-13-cf-turnstile-block/`. A previous session applied the patient-mint
patch overnight and the team ran; this note records what the patch actually achieved, why the team
was down this morning, and the restart + reliability work done on takeover.

## What the overnight patient-mint run proved (big win)

The patch `../2026-11-13-cf-turnstile-block/patch_patient_mint.mjs` was applied to the live engine at
~01:08 and the engine ran ~01:08 -> ~07:25. Counts from that run's log
(`tsb-apex-squad.log.preresume-20261114-112402`):

- `mint ok` **239**, `mint gave no token` **5** -> ~98% mint success (was ~1 token per run before).
- `sendTokenToLobby success` **223**, `HL-GAME-INIT` **394** -> tokens reused across the 60-min pass.
- hourly budget was hit 8 times and respected; donor cooldown fired 48 times. CF stayed under the cap.
- Both mint paths work: most tokens are silent passes (`clicks=0`); at least one this morning came
  back with `clicks=6`, i.e. Cloudflare asked for a click and the `remote.events.async.mouse.enabled`
  fix let the click reach the checkbox iframe and still produced a token.

Conclusion: the admin's plan (patient mint + one batch per hour + 60-min reuse + CF <= 100/h) is
verified in production on d3. The Turnstile outage from 2026-11-13 evening is resolved.

## Why the team was down this morning (not a token problem)

- Game results stopped at **03:57**; the engine kept running until 07:25 but every bot was in a
  1006/4406/4573 disconnect-reconnect storm.
- Root cause: the proxy process `tun_apex_socks5.py` **died silently around 03:57**. On takeover it
  was confirmed dead (no python running it, nothing listening on 10821-10860). Donors mint direct
  (`tsb-donor-direct.flag`), so minting was unaffected, but every bot's game traffic goes through the
  proxy, so with the proxy gone no bot could reach the game server. Nobody was watching, so it sat
  dead for hours.

## Done on takeover (2026-11-14 ~11:20-11:45)

1. Restarted the proxy (`pythoncore-3.15-64 python tun_apex_socks5.py`, cwd c116, hidden). Verified
   it listens on all 40 ports and the upstream residential proxy is alive (US exit IP returned,
   `territorial.io` 200 through :10821).
2. Rotated the old engine log to `tsb-apex-squad.log.preresume-20261114-112402` for a clean run log.
3. Restarted the patched engine (`node_apex.exe tsb-apex-squad.mjs`, cwd c116, hidden). It came up
   clean: donors mint (silent passes, 29-50 s), tokens import, squad enters games in formation.
   Within ~22 min: 35/40 bots minted, 34 in the lobby, first team game played (3-team mode, map 10,
   512 slots = 53 humans + 459 AI; our 16 bots on team 2, lost). Mint rate stayed well under 90/h.
4. Deployed `apex_watchdog.py` (this folder) to d3 and started it. It polls the proxy every 20 s and
   restarts it within seconds if 10821 stops accepting, logging every event to
   `c116\apex_watchdog.log`. This closes the silent-death hole that caused the 03:57 outage.

## Game/lobby shape (for reference)

- Big rooms are 512-slot. They wait for real humans, then fill the rest with the game's AI bots when
  the start timer expires. Typical lobbies seen: `3T` (3 teams) and `8T` (8 teams) on 512 slots, plus
  small modes (e.g. `M7` = 20 slots). Only ~40-55 of the 512 are usually real humans; the "100-player"
  feel is mostly AI.
- Our squad groups ~16 bots into one game on one team (`squad=16` in `HL-SPAWN`).

## How to operate on d3 (cwd = c116 unless noted)

- Start proxy:   `<pythoncore python> tun_apex_socks5.py`  (reads `gproxy.conf`; do NOT commit it)
- Start engine:  `node_apex.exe tsb-apex-squad.mjs`  (self-logs to `tsb-apex-squad.log`, append)
- Start watchdog: run `c136\apex_watchdog.py` with the pythoncore python (hidden)
- Stop watchdog cleanly: delete `c116\apex_watchdog.run`
- Mint knobs (optional files in c116): `tsb-mint-hourly-cap.txt` (default 90, max 100),
  `tsb-mint-parallel.txt` (default 3 with the direct flag), `tsb-donor-direct.flag` (present = donors
  bypass the proxy), `tsb-engine-guard.flag` (present = watchdog also auto-restarts the engine; OFF
  by default because an engine restart re-mints ~40 tokens).

## Open items (admin's 4-step plan)

- Step 2 (reliable mint + 60-min reuse + CF <= 100/h): DONE, verified in production.
- Step 4 (team up + monitor): DONE; monitoring continues.
- Step 3 (in-match proxy latency): NOT started. Admin wanted lobby traffic on the proxy but match
  traffic on the low-latency line, tested on 1-2 bots first. Measurements from 2026-11-13 00:43 are
  in the prior handoff. To be proposed to the admin once play is confirmed stable; it is a riskier
  change and should not be made blind while the team is live.
- Win rate is a separate (strategy) workstream, not this liveops thread.
