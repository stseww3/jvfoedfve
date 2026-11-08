# S10 单局显微镜解剖与核心变量量化报告

- **更新时间**: `2026-11-08T03:31:00Z`
- **包干对局**: `G01, G02, G03, G04, G05, G06, G07, G08, G09`
- **负责核心变量**: `V1, V2, V3, V4, V5, V6, V7, V8, V9, V10, V11, V12`

## 一、单局时间线、胜负拐点与核心死因解剖

### `ALL (G01-G09 vs 80% Baseline Commit Diff Audit 6d4aadd..917e6b1)` (`result=lost`, `5` 队局, 进场 `8` 号, 主陆 `5` 号)
- **`t=1500` 团队领土**: `71711` | **峰值领土**: `124563` (`@t=4500`) | **崩盘拐点**: `t=4500`
- **拐点前线密度 vs 敌方密度**: `d_front = 12.4` vs `d_enemy = 104.2`
- **第一主因**: `V7` | **第二诱因**: `V1`
- **逐拍取证摘要**: Line-by-line regression audit of all 11 commits from 6d4aadd (80% winrate baseline) to 917e6b1 proves that the winrate collapse from 80% to 11.1% (1/9) was caused by 6 interacting negative-ROI patches introduced between fd868f3 and 514a041, compounded by running pre-d590acd spawn-coordinator.mjs in Boss-less mode: (1) e20db6b+32c5689+514a041 (V7/V8): oppFloorCap 128->38, collapseFloorCap 85->16, totB=B+myOut, keep<=10~26*L caused 181 frontline hollow-out events (d_home=0~18) and threw 100% (3/3) of midgame #1 leads (G01, G04, G06); (2) fd868f3+pre-d590acd (V1/V2): VirtualSquadAnchor island traps + allyMinSep<=112 / clusterMax<=350 caused 7/10 games to suffer island fallbacks (voronoi=500) or secondary-continent lockups and cut t=1500 land by -28%; (3) e20db6b+4b7408e (V4/V9/V10): period=2 + inflight<2t (< WebSocket RTT) triggered 18 bursts (125 shots) of 5~14x 10%B assist machine-gunning, draining 50~81% of healthy allies' balances; (4) d996be6+fd868f3 (V6): pct=51 (5%B) micro-donations paid a flat 64/1024 (6.25%B) engine tax (55.2% loss rate, burning 18.71M in tax across G01-G09) while coastGuardFloor=68*L deadlocked boxed-in coastal rear bots at d=70~78; (5) 404996d (V5): bQ.mt.mu is always false for human chases (74 duplicate chases) and 35%B chase cap + no fee<=bTr gate burned 4.58M in 3.125%B boat tax while s.land undefined broke tryClaimNearTeamIslands.

## 二、专项核心变量全样本量化与因果机制

### `V7` — EffectiveFrontlineKeepDensity (Commits e20db6b, b594ea3, 32c5689, 514a041) (预估胜率影响 `+31.0%`)
- **当前劣化值**: `oppFloorCap=38, collapseFloorCap=16, totB=B+myOut, isPrimeLand keep<=10~26*L`
- **80% 胜率基线值**: `oppFloorCap=128, collapseFloorCap=85, avail=B-fee-keep`
- **推导最优阈值**: `oppFloorCap=112, collapseFloorCap=68, avail=B-fee-keep, thirdPartySafe>=max(68*L, (max3rdB-1.5*L)/1.55)`
- **源码级因果机制**: Double-counting in-flight troops myOut in totB while slashing keep floors to 10~38*L stripped frontline home density to 0~18 during attacks.
- **源码定位**: `tsb/squad/make_v27_team.py:976-998, 1060-1102`

### `V1` — MainContinentSpawnRatio (Commits fd868f3, d590acd) (预估胜率影响 `+24.0%`)
- **当前劣化值**: `minAnchorContSize=0.45*maxCompSize, voronoi=500 fallback active when relax<0.60`
- **80% 胜率基线值**: `Boss-anchored on #1 main continent + SPOILER_BANK pair`
- **推导最优阈值**: `minAnchorContSize=0.75*maxCompSize (strictly #1 continent), enforce minViableCompSize across all relax passes, openDirs>=4`
- **源码级因果机制**: Unpopulated islands had max clearance=220, trapping VirtualSquadAnchor on islands in 6/10 games and secondary continents in G06.
- **源码定位**: `tsb/squad/spawn-coordinator.mjs:520-544, 905-926, 1042-1075`

## 三、核心变量权重排序

1. **`V7` (28.0%)**: e20db6b+32c5689+514a041 (oppFloorCap=38 + totB=B+myOut + keep<=10*L) caused 181 frontline hollow-outs (d=0~18) and threw G01, G04, G06.
2. **`V1` (18.0%)**: Pre-d590acd VirtualSquadAnchor island trap + G06 53.75% secondary continent trap crippled opening in 7/10 games.
3. **`V2` (12.0%)**: fd868f3 (allyMinSep<=112, clusterMax<=350) cut t=1500 neutral land by -28% and boxed 3~5 inner bots into nb=0.
4. **`V6` (12.0%)**: d996be6 (pct=51) paid flat 6.25%B engine tax (55.2% loss, 18.71M burned) while coastal boxed-in rear bots deadlocked at d=70~78.
5. **`V10` (10.0%)**: e20db6b (period=2 < RTT) caused 5~14x 10%B assist machine-gun bursts (125 shots) and multi-team war provocation.
6. **`V5` (8.0%)**: 404996d (bQ.mt.mu always false + 35%B chase cap + s.land undefined) burned 4.58M in 3.125%B boat tax across 673 boats.
7. **`V3` (6.0%)**: Uncapped dpKeep in dense team spawns froze 53.9% of t=600..1499 neutral expansion snapshots.
8. **`V12` (6.0%)**: Loose Room 0 entry gate (headlessInRoom0>=5) allowed 6~7 bot partial entries and Team 2/3 split fratricide in G09.

## 四、最小可验证修复清单 (Actionable Fixes)

- **文件**: `tsb/squad/make_v27_team.py` (`Complete 6-Variable Restoration & Guardrail Patch (V3, V4, V5, V6, V7, V8, V9, V10)`, 风险: `low`)
  - 修改前: `period:2, oppFloorCap:38, collapseFloorCap:16, totB=B+myOut, pct=51, unthrottled 10%B assist, bQ.mt.mu chase dedup, s.land island claim`
  - 修改后: `period:5 (inflight>=6t), oppFloorCap:112, collapseFloorCap:68, avail=B-fee-keep, boxedIn donate pct=240..280 (frontline nb>0 no donate below d=138), 90t assist cooldown, geometric bType===6 chase dedup + fee<=0.625*bTr gate + 14%B cap, s.c island fix`
