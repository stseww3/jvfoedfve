# c116-winrate Overnight Autonomous Team Games Raw Data (G01 ~ G09)

## 1. File Inventory & Exact Byte Sizes

- `tsb-team-results.jsonl` (`114,604` bytes, 119 JSONL records):
  Complete raw match result log from `d3 (C:\Users\workstation\Desktop\远程\workspaces\c110\tsb-team-results.jsonl)`, covering `2026-11-07T14:42:40Z` (`22:42 CST`) through `2026-11-07T17:28:03Z` (`01:28 CST`).
- `tsb-team-squad.log` (`2,648,376` bytes, 23,517 lines):
  Complete, byte-exact raw stdout log from `tsb-team-squad.mjs` during the autonomous 8-bot Team session (`00:10 CST` ~ `01:28 CST`, covering all 9 games `G01 ~ G09`).
- `G01-G09-results.jsonl` (`77,981` bytes, 77 JSONL records):
  Filtered slice of `tsb-team-results.jsonl` for `at >= 2026-11-07T16:20:00Z` (`00:20 CST` ~ `01:28 CST`), corresponding to the 9 autonomous games `G01 ~ G09`.
- `G01-G09-squad.log` (`2,648,376` bytes):
  Copy of `tsb-team-squad.log` covering the exact `G01 ~ G09` autonomous run.

## 2. Field Descriptions

### `tsb-team-results.jsonl` / `G01-G09-results.jsonl`
Each line is a JSON object emitted per bot upon leaving or finishing a match:
- `bot`: Bot display name (`[Nope] mark07`, `[Nope] kevin_k`, `[Nope] ethan21`, `[Nope] lucas94`, `[Nope] dave_w`, `[Nope] ryan_m`, `[Nope] noah88`, `[Nope] leo_tx`)
- `port`: Worker virtual port (`9302 .. 9309`)
- `result`: `"won"` | `"lost"` | `"over"` | `"left"`
- `event`: `"end"` | `"died"` | `"left"`
- `game`: Replay/match ID
- `mode`: `"team"`
- `tick` / `time` / `seconds`: Final game tick and duration when the bot exited/finished
- `place` / `players` / `alivePlayers`: Final rank and player counts
- `territory` / `peak` / `land`: Final territory, peak territory, and total map land pixels
- `balance` / `sent` / `accepted`: Final troop balance and command counters
- `team`: `{ "mine": <ourTeamId>, "best": <winningTeamId>, "totals": { "<teamId>": <landPixels>, ... } }`
- `at`: ISO-8601 UTC timestamp (`CST = UTC + 8 hours`)

### `tsb-team-squad.log` / `G01-G09-squad.log`
Contains tick-by-tick and event-by-event telemetry across all 8 Headless Workers:
- `[HL-GAME-INIT] mode=<m> map=<id> mapSeed=<seed> players=<H> me=<pid>`: Match initialization
- `[BACKEND-SPAWN-COORD] Solved 8 bots in <ms> (map=<W>x<H>, minSep=<px>, boss=<pos>)`: Unified spawn coordinator solution
- `[HL-SPAWN-BACKEND] me=<pid> slot=<s> role=<role> -> (x,y) bossDist=<d> minAllyDist=<d> voronoi=<px>`: Per-bot spawn assignment and Voronoi basin size
- `[HL-OPENING] t=<tick> cyc=<c> DP expand rings=<r> spend=<X>/<bal> terr=<L>`: Opening DP expansion pulses
- `[OPENING-CHECK 8 bots @ tick <t>]`: Tick ~180-220 opening expansion verification across all 8 bots
- `[HL-TICK] t=<tick> terr=<L>(<pct>%) bal=<B> dens=<d> nb=<n> neut=<n> cmds=<c> boats=<b> avgMs=<ms> maxMs=<ms> skip=<s>`: Periodic state snapshot (every 90 ticks)
- `[HL-DONATE] t=<tick> <type> donate pct=<p>/1024 (~5%) -> ally/boss=<id>(<name>) myBal=<B> dMe=<d>`: Cash donation logs
- `[HL-ASSIST] t=<tick> 10% squad-rescue/boss-assist poke -> enemy=<id>(<name>)`: Coordinated 10% assist attacks
- `[HL-INTERCEPT] t=<tick> unified sea intercept pct=<p>/1024 -> boatId=<id> owner=<id>(<name>) boatTroops=<trp>`: Sea radar boat interception (`g.chase`)
- `[RESULT <bot>] result=<r> event=<e> place=<p> peak=<pk> team=<json>`: Match end summary
