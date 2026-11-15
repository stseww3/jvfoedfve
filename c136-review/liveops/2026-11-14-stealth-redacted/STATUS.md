# c136 live-ops: Option A stealth run audit (checked 2026-11-15 23:35 d3 clock)

## Process status on `d3` (`workspaces\c116`) as of 2026-11-15 23:33

- `node_apex.exe` (PID 2320): running `tsb-apex-squad.mjs` since `2026-11-14 13:29:39` (~2.81 GB RSS).
- `python.exe` (PID 24612): running `tun_apex_socks5.py` since `2026-11-14 11:21:54`.
- `python.exe` (PID 11052): running `c136\apex_watchdog.py` since `2026-11-14 11:38:32` (heartbeat current, 0 proxy restarts).

## Run results (`2026-11-14 13:29:39` -> `16:21:35` d3 local time)

Source: `c116\tsb-apex-squad.log` (502k lines) and `c116\tsb-team-results.jsonl`.

- **Games played**: **12** (all Mode 1 / 3-Team 512-slot rooms) -> **7 WON / 5 LOST (58.3% win rate)**.
- **6 of 7 wins took `place=1` overall**:
  1. G01 (`[Y5B]`, room 1402, map 10, 31 humans, 4 bots entered, est fill 91%): **WON**, `place=1`, peak `188,840`
  2. G02 (`[K9T]`, room 1430, map 1, 22 humans, 7 bots entered, est fill 143%): **WON**, `place=1`, peak `334,603`
  3. G03 (`[V7K]`, room 1458, map 10, 33 humans, 2 bots entered, est fill 100%): **LOST**, `place=5`, peak `223,673`
  4. G04 (`[S8P]`, room 1516, map 1, 46 humans, 7 bots entered, est fill 120%): **WON**, `place=1`, peak `236,016`
  5. G05 (`[T7L]`, room 1531, map 16, 96 humans, 12 bots entered, est fill 55%): **LOST**, `place=27`, peak `14,605`
  6. G06 (`[D5H]`, room 1552, map 10, 46 humans, 11 bots entered, est fill 100%): **WON**, `place=1`, peak `117,417`
  7. G07 (`[X9D]`, room 1576, map 10, 101 humans, 21 bots entered, est fill 89%): **LOST**, `place=31`, peak `30,184`
  8. G08 (`[M5J]`, room 1593, map 10, 83 humans, 18 bots entered, est fill 100%): **WON**, `place=7`, peak `21,051` (team score `543,887 : 542`)
  9. G09 (`[J7R]`, room 1630, map 10, 75 humans, 8 bots entered, est fill 100%): **WON**, `place=1`, peak `188,064`
  10. G10 (`[X9D]`, room 1648, map 10, 94 humans, 21 bots entered, est fill 97%): **LOST**, `place=15`, peak `36,499`
  11. G11 (`[A4Z]`, room 1676, map 1, 33 humans, 10 bots entered, est fill 111%): **WON**, `place=1`, peak `139,758`
  12. G12 (`[Y5B]`, room 1696, map 16, 73 humans, 15 bots entered, est fill 64%): **LOST**, `place=11`, peak `52,040`

- **Redacted behavior**:
  - `SELF-CHECK OK`: 1,206.
  - `SELF-CHECK REDACTED`: 3 total, all at cold-start lines 335-441 before G01 (single slot rotated to a fresh account and tag rotated `[U2C] -> [Y5B]`).
  - **0 Redacted events** across all 12 matches afterward.

## Why matches stopped after `2026-11-14 16:21:35`

- Shortly after G12 ended (`2026-11-14T08:21:35Z` / `16:21:35` local), all Room 0 connections closed (`error 1006` at log lines 67056-67067) and every subsequent `Connection to Server 0` immediately closed with **`socket close index 0 error 4211`** (client bundle version mismatch; `c116\live_game_js.js` mtime is `2026-11-12 22:50:29`).
- Over 216k `error 4211` reconnect lines accumulated between `11-14 16:22` and `11-15 23:35`. No processes were modified during this inspection.
