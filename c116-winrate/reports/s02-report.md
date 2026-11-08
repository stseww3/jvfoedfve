# S02 单局显微镜解剖与核心变量量化报告

- **更新时间**: `2026-11-08T03:10:00Z`
- **包干对局**: `G02, G03`
- **负责核心变量**: `V3`

## 一、单局时间线、胜负拐点与核心死因解剖

### `G02 (00:35 CST, mw6mdnq5-65li02..mw6mdns6-4snhkn)` (`result=lost`, `6` 队局, 进场 `8` 号, 主陆 `2` 号)
- **`t=1500` 团队领土**: `80132` | **峰值领土**: `84451` (`@t=1620`) | **崩盘拐点**: `t=1800`
- **拐点前线密度 vs 敌方密度**: `d_front = 9.7` vs `d_enemy = 68.4`
- **第一主因**: `V1` | **第二诱因**: `V3`
- **逐拍取证摘要**: In G02 (map=22, 1541x1080, land=664,497, 6 teams, H=61), pre-d590acd findVirtualSquadAnchor + clusterMax<=350 caused 4 of 8 bots (mark07, ethan21, ryan_m, noah88) to fail minVoronoi and hit the voronoi=500 fallback, scattering the squad across 6 disconnected landmasses: only 2/8 bots (mark07, leo_tx) spawned on the 244,592px main continent, while ethan21 was trapped on a 275px micro-island (1480,748) and dave_w on a 2,331px island (452,72). During t=600..1500, V3 opening bottlenecks (dpKeep uncapped against human neighbors + minCmd>=4.69%B blocking 18/44 neutral-border snapshots) capped squad land at L_team(1530)=80,132 (12.06% of map, d_avg=7.1). At inflection t=1800..2070, dave_w collapsed on his island (L: 5,443->0), ryan_m (L=17,130, 183 cmds, d=2.5->9.7) was overrun at t=2356 when Team 1 already held 204,109px (30.7%), and lucas94/kevin_k burned 43.3% of their balances firing 14 sea-intercept boats (t=3000..3200) before Team 1 swept the map (356,396px, 53.6%).

### `G03 (00:41 CST, mw6mk3l1-auq7y..mw6mk3dm-d5cqij)` (`result=lost`, `4` 队局, 进场 `8` 号, 主陆 `8` 号)
- **`t=1500` 团队领土**: `60318` | **峰值领土**: `73102` (`@t=1710`) | **崩盘拐点**: `t=1800`
- **拐点前线密度 vs 敌方密度**: `d_front = 6.2` vs `d_enemy = 74.0`
- **第一主因**: `V2` | **第二诱因**: `V3`
- **逐拍取证摘要**: In G03 (map=17, 690x925, land=292,727, 4 teams, H=58), all 8 bots spawned on the single 291,709px main continent (99.65% of map), but fd868f3 compressed allyMinSep to 88px (relaxing to 48px between kevin_k (604,322) and noah88 (644,296)) and clusterMax<=289px, packing all 8 brothers into a 230x324px corner box (11.7% of map area). In t=600..1499, V3 opening bottlenecks blocked 30 of 41 neutral-border snapshots (73.2% blocked; only 15/72 DP cycles fired in cyc 6..14) because bordering 10~17 human neighbors inflated dpKeep(g) above dpSpend*bal, freezing lucas94 at L=4,411 (neut=10 ungrabbed for 450 ticks) and ethan21 at L=7,292 (neut=11 ungrabbed), then triggering 17 duplicate expandNeutral commands at t=1500..1526 that burned ~34.8k troops for 38px. By t=1530, L_squad=60,318 (20.61%) was 24% below the >=27% 4-team survival threshold, and 3/8 bots (kevin_k, dave_w, noah88, 22,188px=36.8% of squad land) were 100% boxed-in (nb=0, neut=0). At inflection t=1800..2024, frontline guard mark07 (L=10,573, d=4.9->6.2) was crushed at t=2024 while the 3 boxed-in rear bots sat at d=49..78 until t=2700 and then burned 812k in 6.25%B donation tax across 43 micro-donations.

## 二、专项核心变量全样本量化与因果机制

### `V3` — TeamLandShareAt1500 (预估胜率影响 `+24.0%`)
- **当前劣化值**: `Mean L_squad(1500)/L_map = 13.59% across G01-G09 (G02: 12.06% [80,132/664,497], G03: 20.61% [60,318/292,727]); 53.9% (230/427) of neutral-border snapshots in t=600..1440 blocked in dpNeutral(); t=1500..1528 double-expandNeutral + 2-tick period triggers 5~14 duplicate neutral commands burning 15k~35k troops for <50px`
- **80% 胜率基线值**: `L_team(1500)/L_map >= 1.25 / N_teams + 2.5% (22.0% in 6-team, 27.0% in 4-team, 35.0% in 3-team) with L_squad(1500)/L_map >= 18.0%~22.0%, boxedIn_ratio(1500) <= 12.5% (<=1 bot), and d_front(1500) >= 14.0`
- **推导最优阈值**: `1) In dpNeutral(g): cap dpKeep at 0.55*bal while this.neutral > 0, relax effMinCmd to Math.min(this.minCmd(g), Math.max(120, 2*fee)) when n === rings.length (finite pocket), and bypass later>=n wait when n === rings.length && rings.length <= 6 && g.t >= 500; 2) In expandNeutral(g): remove minGrab=Math.min(0.22*B, 10*neutral+3000) override when have >= 2*neutral, and remove the duplicate pre-buyLand expandNeutral call at v27-team-live.js:5335; 3) Restore P.period = 5`
- **源码级因果机制**: Four stacked code defects crippled V3 opening neutral land harvest (t=0..1500) and the t=1500 transition: (1) In dpNeutral (v27-team-live.js:2367, 2435), dpKeep(g) = (max_nb_human_B - 1.5*L)/1.78 is uncapped; in dense Team games where a bot borders 5..17 human neighbors (e.g. G03 lucas94 nb=14, leo_tx nb=17), a single passive neighbor with B=25k pushes dpKeep above 0.5*B, making max = min(0.5*B, B - dpKeep) - fee <= 0 and completely freezing neutral expansion from t=600 to t=1499 (blocking 73.2% of neutral snapshots in G03 and 53.9% across G00-G09); (2) Line 2381 (if (X < this.minCmd(g)) return) requires X >= 4.69% * B, so finite neutral pockets of 3..25px (costing 7..51 troops) are ignored for 500+ ticks while bots sit with neut=3..24; (3) At t=1500 (P.coreFrom), act(g) calls expandNeutral TWICE per tick (lines 5337 and 5350) with minGrab = Math.min(0.22*B, max(minCmd+50, 10*neutral+3000)) and period=2 / inflight<2t, firing 5..12 duplicate commands across WebSocket RTT before neutral troops land and burning 15k..35k troops + 8..14% tax for a few pixels; (4) Coupled with V1 (pre-d590acd island anchor + relax<0.60 dropping minViableCompSize) and V2 (allyMinSep<=112, clusterMax<=350), the squad's reachable neutral envelope is cut by 35%..55% before t=600.
- **源码定位**: `tsb/squad/v27-team-live.js:2349-2440, 5335-5351; tsb/squad/make_v27_team.py:976-995, 1033-1044, 1176-1183; tsb/squad/spawn-coordinator.mjs:830-835, 905-925, 1042-1075`

## 三、核心变量权重排序

1. **`V7` (26.0%)**: oppFloorCap=38 + collapseFloorCap=16 + totB=B+myOut drained frontline home density to d=2.5..9.7 (ryan_m in G02, mark07/leo_tx in G03), causing instant frontline collapse against d=65..95 enemies.
2. **`V3` (22.0%)**: Uncapped dpKeep + minCmd>=4.69%B blocked 53.9% of t=600..1499 neutral-border snapshots (73.2% in G03), and the t=1500 double-expandNeutral + minGrab bug burned 15k..35k troops, keeping L_team(1500)/L_map well below the 80%-winrate survival line.
3. **`V1` (20.0%)**: Pre-d590acd VirtualSquadAnchor + relax<0.60 dropping minViableCompSize + voronoi=500 fallback scattered 4/8 bots in G02 across 6 islands (including 275px and 2,331px traps), forfeiting 63% of the main continent at t=0.
4. **`V2` (18.0%)**: fd868f3 compressed allyMinSep to 62..112px (relaxing to 48px in G03) and clusterMax<=350px, boxing 3/8 bots in G03 (36.8% of squad land) into nb=0, neut=0 internal lockup by t=1260.
5. **`V6` (8.0%)**: Boxed-in rear bots in G03 (kevin_k, dave_w, noah88) were blocked from donating until dMe>=72 (t=2700, 676 ticks after mark07 died) and burned 55.2% of donated troops to the flat 6.25%B engine tax via pct=51 micro-donations.
6. **`V5` (6.0%)**: 23 sea intercepts in G02 and 44 in G03 (up to 35%B per boat) drained lucas94 (B: 377k->237k at t=3000 in G02) and ryan_m (B: 530k->294k at t=3350..3510 in G03) right before enemy land pushes.

## 四、最小可验证修复清单 (Actionable Fixes)

- **文件**: `tsb/squad/make_v27_team.py` (`dpNeutral (cap dpKeep at 0.55*bal while neutral>0, allow finite-pocket cleanup below minCmd, and fire immediately on small pockets <=6 rings)`, 风险: `low`)
  - 修改前: `const max = Math.min(P.dpSpend * bal, bal - this.dpKeep(g)) - fee; ... if (later >= n) return; const X = 2 * sum + rings[n - 1].r; if (X < this.minCmd(g)) return;`
  - 修改后: `const keepCap = this.neutral > 0 ? Math.min(this.dpKeep(g), Math.floor(0.55 * bal)) : this.dpKeep(g); const max = Math.min(P.dpSpend * bal, bal - keepCap) - fee; ... const isFinitePocket = n === rings.length && rings.length <= 6 && g.t >= 500; if (!isFinitePocket && later >= n) return; const X = 2 * sum + rings[n - 1].r; const effMin = (n === rings.length && g.t >= 600) ? Math.min(this.minCmd(g), Math.max(120, 2 * fee)) : this.minCmd(g); if (X < effMin) return;`
- **文件**: `tsb/squad/make_v27_team.py` (`expandNeutral & act (remove duplicate pre-buyLand expandNeutral call and gate minGrab so it never over-sends 3000+ troops for tiny 3..15px neutral remnants)`, 风险: `low`)
  - 修改前: `const minGrab = Math.min(Math.floor(0.22 * B), Math.max(this.minCmd(g) + 50, 10 * this.neutral + 3000)); ... spend = Math.min(B, Math.max(spend, minGrab)); super.expandNeutral(g, spend);`
  - 修改后: `const haveN = g.attackTroopsOn(this.me, NEUTRAL); const minGrab = (this.neutral > 0 && haveN === 0) ? Math.min(Math.floor(0.12 * B), Math.max(2 * this.neutral + 200, Math.min(this.minCmd(g), 6 * this.neutral + 400))) : 0; ... spend = Math.min(B - iV(12 * B, 1024), Math.max(spend, minGrab)); super.expandNeutral(g, spend);`
- **文件**: `tsb/squad/spawn-coordinator.mjs` (`scales (allyMinSep, clusterMax) & pickNextTarget (enforce minViableCompSize across all relax passes and fallback)`, 风险: `low`)
  - 修改前: `allyMinSep: clamp(Math.round(Math.max(1.05 * rCell, 0.075 * diag)), 62, 112), ... clusterMax: clamp(Math.round(Math.max(3.0 * rCell, 0.25 * diag)), 195, 350), ... else if (relax >= 0.60 && this.compSize[c] < minViableCompSize) continue;`
  - 修改后: `allyMinSep: clamp(Math.round(Math.max(1.42 * rCell, 0.110 * diag)), 96, 172), ... clusterMax: clamp(Math.round(Math.max(4.4 * rCell, 0.40 * diag)), 280, 540), ... else if (this.compSize[c] < minViableCompSize) continue;`
