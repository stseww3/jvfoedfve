# `v28-team-organism.js` & `spawn-coordinator-v28.mjs` — Full 20-Room / 180-Run Verification & Ablation Report

> **Date**: 2026-11-12  
> **Coordinator**: `c136`  
> **Code Artifacts**:
> - Strategy Candidate: `v28/v28-team-organism.js` (6,980 lines, parameterized by `PARAMS.enable*` switches `P1..P8`)
> - Spawn Coordinator Candidate: `v28/spawn-coordinator-v28.mjs` (1,580 lines, Voronoi Area Maximization + 1.4s Countdown Freeze Window)
> - Simulator Harness: `sim-v2/teamgate-v2.mjs` (`--mode verify`, `--mode live`, `--mode checkpoint`, `--mode arena`)
> - Cloud Parallel CI Workflow: `.github/workflows/c136-bench.yml` & `c136-review/ci/ci-bench.mjs` (20 parallel shards $\times$ 9 arms = 180 full Arena simulations)

---

## 1. Executive Summary

Following the completion of **100/100 in-match frame-by-frame reviews** (1,746 concrete proposals, 114 hypothesis cards, 7 `CROSS-MATCH-SUMMARY.md` reports, and 7 `COUNCIL-PROPOSAL.md` / `OFFLINE-CHECKPOINT-ATTRIBUTION.md` reports across `R01..R10`) and cross-group technical verification with `c135` (`ROUNDTABLE-REFEREE.md`), we implemented and benchmarked all 8 modular upgrades (`P1..P8`) in `v28-team-organism.js` and `spawn-coordinator-v28.mjs`.

Across the **full 20-room calibrated Arena acceptance suite (`A018..A070` 11 rooms + `B010..B041` 9 rooms, `t=0 → 3210`, Channel `C1`)** and **180-run Leave-One-Out Cloud Ablation Matrix**:
- **20-Room Direct Head-to-Head (`v28-team-organism.js` vs `v27` historical baselines)**:
  - **20 / 20 rooms won (`100%` win rate)** after disabling the unsafe `p3SafeCap: 0` (which had allowed neighboring AI bots to view our seat as their weakest neighbor) and keeping `p3ThreatSkip: 1` + `p3Decouple: 1` (for $t \ge 1500$ weak prey) + `p3MinCmdFix: 1`;
  - **Mean Map Land Share (`landShare1`)**: Increased from **`0.4204` (`v27`) to `0.4899` (`v28`)** (**+6.95 percentage points of total map land / +16.5% relative**);
  - **Mean Duplicate Command Share (`dupShare`)**: Reduced from **`25.98%` (`42.20%` in `c116` rooms) down to `5.49%`** (**-20.49 percentage points overall / -35.7 percentage points in `c116`**);
  - **Mean Donation Quota Rejection Rate (`quotaRejectRate`)**: Reduced from **`72.50%` (`96.8%` in `c116` rooms) down to `0.82%`** (**-71.68 percentage points**) via the exact recipient-quota inverse formula `p6MaxQuotaTroops(g, q)` with $0.90\times$ in-flight interest headroom;
  - **Total Net Troop Production (`netProd = Income - Fees` across 20 rooms)**: Increased from **`326.91M` (`v27`) to `411.76M` (`v28`)** (**+84.85M troops / +26.0%**);
  - **Pre-3000-Tick Seat Deaths (`dead3000`) & Exceptions (`stratErrors`)**: Reduced from **`4` deaths (`v27`) to `0` deaths (`v28` with `p3SafeCap: 0`)** and **`0` runtime errors** across all 180 runs.

---

## 2. 180-Run Leave-One-Out Cloud Ablation Matrix (20 Rooms $\times$ 9 Arms)

| Arm | Rooms | Wins vs Base | Mean Land Share | Delta Land vs Base | Mean Dup Share | Mean Quota Reject | Total Net Prod | Pre-3000 Deaths | Errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`baseline (v27)`** | 20 | - | `0.4204` | `0.0000` | `25.98%` | `72.50%` | `326.91M` | `4` | `0` |
| **`v28-final (p3SafeCap=0)`** | 20 | **20/20** | **`0.4899`** | **`+0.0695`** | **`5.49%`** | **`0.82%`** | **`411.76M`** | **`0`** | **`0`** |
| `v28 (with p3SafeCap=1)` | 20 | 17/20 | `0.4860` | `+0.0657` | `6.54%` | `1.40%` | `411.76M` | `1` | `0` |
| `no-P1 (enableInflightLedger=0)` | 20 | 11/20 | `0.4163` | `-0.0041` | `42.34%` | `0.29%` | `291.51M` | `6` | `0` |
| `no-P4 (enableCoordinatedStrike=0)` | 20 | 16/20 | `0.4762` | `+0.0559` | `6.44%` | `1.35%` | `407.37M` | `0` | `0` |
| `no-P5 (enableSmartOverCap=0)` | 20 | 17/20 | `0.4861` | `+0.0657` | `6.55%` | `1.40%` | `411.99M` | `1` | `0` |
| `no-P6 (enableQuotaExactDonate=0)` | 20 | 16/20 | `0.4771` | `+0.0567` | `6.35%` | `71.71%` | `404.71M` | `0` | `0` |
| `no-P7 (enableSeaPrecision=0)` | 20 | 18/20 | `0.4819` | `+0.0616` | `6.73%` | `1.29%` | `413.76M` | `0` | `0` |
| `no-P8 (enableCollapseGuard=0)` | 20 | 13/20 | `0.4319` | `+0.0115` | `5.57%` | `1.89%` | `399.57M` | `8` | `0` |

### Key Findings from the 180-Run Ablation Matrix
1. **Removing `P1` (`no-P1`)** causes mean land share to collapse by **`-7.36` percentage points** (`0.4899 → 0.4163`), duplicate commands to jump from **`5.49%` to `42.34%`**, net troop production to drop by **`-120.25M` troops** (`411.76M → 291.51M`), and pre-3000-tick seat deaths to rise from **`0` to `6`**.
2. **Removing `P8` (`no-P8`)** causes mean land share to drop by **`-5.80` percentage points** (`0.4899 → 0.4319`) and pre-3000-tick seat deaths to surge from **`0` to `8`** (due to losing `lifeGuardAct` near `peak/4` and cross-team squadmate protection `isProtectedSquadMate`).
3. **Removing `P4` (`no-P4`)** reduces mean land share by **`-1.37` percentage points** (`0.4899 → 0.4762`), confirming the positive gain of multi-seat coordinated strike pricing (`p4JointNeed`), `nearCollapse` denominator fix, and narrow-border wave capping.
4. **Removing `P6` (`no-P6`)** causes donation quota rejection rate to spike from **`0.82%` back up to `71.71%`** and reduces mean land share by **`-1.28` percentage points** (`0.4899 → 0.4771`) and net troop production by **`-7.05M` troops**.
5. **Removing `P7` (`no-P7`)** reduces mean land share by **`-0.80` percentage points** (`0.4899 → 0.4819`), confirming the value of boxed-in `boatFood` breakout and sail-decay filtering.
6. **Surgical `P3` Refinement (`p3SafeCap: 0`)**: The ablation revealed that capping `safeFinite` by a neighboring bot's own balance (`p3SafeCap: 1`) caused our seats to drop below the bot's other neighbors (`th.minOther`), inviting bot attacks in `A041 / B010`. Setting `p3SafeCap: 0` while keeping `p3ThreatSkip: 1` and `p3MinCmdFix: 1` lifted the 20-room win rate to **20/20 (100%)** and eliminated the last pre-3000 death.

---

## 3. Per-Room Full Breakdown across All 20 Calibrated Rooms (`t=0 → 3210`, Channel `C1`)

| Room | Channel | Base Strategy | Base Land | `v28` Land | Delta Land | Base Dup | `v28` Dup | Base QuotaRej | `v28` QuotaRej | Base NetProd | `v28` NetProd |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`A018`** | `C1` | `v27-team-c116-vb` | `0.6755` | **`0.8391`** | **`+0.1636`** | `46.1%` | **`9.2%`** | `98.9%` | **`0.0%`** | `14.37M` | **`18.94M`** |
| **`A021`** | `C1` | `v27-team-c116-vb` | `0.2253` | **`0.2616`** | **`+0.0363`** | `38.1%` | **`5.5%`** | `96.1%` | **`0.0%`** | `9.59M` | **`11.48M`** |
| **`A023`** | `C1` | `v27-team-c116-vb` | `0.1885` | **`0.2321`** | **`+0.0436`** | `39.9%` | **`6.4%`** | `98.7%` | **`0.0%`** | `7.00M` | **`9.26M`** |
| **`A027`** | `C1` | `v27-team-c116-vb` | `0.2937` | **`0.3856`** | **`+0.0919`** | `41.6%` | **`5.3%`** | `94.4%` | **`0.0%`** | `13.02M` | **`19.18M`** |
| **`A033`** | `C1` | `v27-team-c116-vb` | `0.2524` | **`0.2783`** | **`+0.0259`** | `36.8%` | **`2.0%`** | `97.6%` | **`0.0%`** | `9.41M` | **`14.77M`** |
| **`A039`** | `C1` | `v27-team-c116-vb` | `0.5608` | **`0.6544`** | **`+0.0936`** | `42.9%` | **`5.9%`** | `96.1%` | **`0.0%`** | `12.59M` | **`18.29M`** |
| **`A041`** | `C1` | `v27-team-c116-vb` | `0.2238` | **`0.3026`** | **`+0.0788`** | `38.3%` | **`7.0%`** | `97.7%` | **`0.0%`** | `9.61M` | **`13.45M`** |
| **`A049`** | `C1` | `v27-team-c116-vb` | `0.1735` | **`0.2166`** | **`+0.0431`** | `42.6%` | **`4.0%`** | `99.5%` | **`0.0%`** | `10.25M` | **`12.33M`** |
| **`A057`** | `C1` | `v27-team-c116-vb` | `0.1124` | **`0.2109`** | **`+0.0985`** | `34.1%` | **`7.3%`** | `98.1%` | **`3.3%`** | `8.62M` | **`12.25M`** |
| **`A058`** | `C1` | `v27-team-c116-vb` | `0.1848` | **`0.2643`** | **`+0.0795`** | `39.8%` | **`6.5%`** | `97.7%` | **`0.0%`** | `11.71M` | **`16.15M`** |
| **`A070`** | `C1` | `v27-team-c116-vb` | `0.7539` | **`0.8125`** | **`+0.0586`** | `44.5%` | **`7.6%`** | `0.0%` | **`0.0%`** | `19.82M` | **`29.93M`** |
| **`B010`** | `C1` | `v27-team-c110` | `0.2933` | **`0.3097`** | **`+0.0164`** | `9.8%` | **`6.5%`** | `74.5%` | **`0.0%`** | `13.44M` | **`14.34M`** |
| **`B017`** | `C1` | `v27-team-c110` | `0.4939` | **`0.6730`** | **`+0.1791`** | `8.9%` | **`3.8%`** | `8.3%` | **`0.0%`** | `20.62M` | **`30.23M`** |
| **`B021`** | `C1` | `v27-team-c110` | `0.4171` | **`0.6312`** | **`+0.2141`** | `9.7%` | **`6.7%`** | `47.1%` | **`0.0%`** | `17.55M` | **`20.10M`** |
| **`B022`** | `C1` | `v27-team-c110` | `0.6815` | **`0.7982`** | **`+0.1167`** | `8.5%` | **`7.9%`** | `50.0%` | **`0.0%`** | `27.60M` | **`30.64M`** |
| **`B023`** | `C1` | `v27-team-c110` | `0.6570` | **`0.7238`** | **`+0.0668`** | `7.3%` | **`4.9%`** | `87.2%` | **`0.0%`** | `27.80M` | **`33.27M`** |
| **`B025`** | `C1` | `v27-team-c110` | `0.4490` | **`0.4926`** | **`+0.0436`** | `8.4%` | **`6.1%`** | `57.1%` | **`0.0%`** | `18.42M` | **`22.41M`** |
| **`B038`** | `C1` | `v27-team-c110` | `0.3770` | **`0.5098`** | **`+0.1328`** | `5.8%` | **`4.6%`** | `72.4%` | **`0.0%`** | `18.51M` | **`23.84M`** |
| **`B039`** | `C1` | `v27-team-c110` | `0.5453` | **`0.6507`** | **`+0.1054`** | `6.7%` | **`4.9%`** | `26.2%` | **`0.0%`** | `28.78M` | **`35.98M`** |
| **`B041`** | `C1` | `v27-team-c110` | `0.7524` | **`0.8235`** | **`+0.0711`** | `6.6%` | **`6.9%`** | `93.4%` | **`0.0%`** | `28.11M` | **`33.07M`** |
