# S03 单局显微镜解剖与核心变量量化报告

- **更新时间**: `2026-11-08T03:30:00Z`
- **包干对局**: `G04`
- **负责核心变量**: `V7`

## 一、单局时间线、胜负拐点与核心死因解剖

### `G04 (00:50 CST, 3-team map=10 931x959 land=546,152, t=8736 lost)` (`result=lost`, `3` 队局, 进场 `8` 号, 主陆 `6` 号)
- **`t=1500` 团队领土**: `61616` | **峰值领土**: `248433` (`@t=5422`) | **崩盘拐点**: `t=6570`
- **拐点前线密度 vs 敌方密度**: `d_front = 27.8` vs `d_enemy = 118.0`
- **第一主因**: `V7` | **第二诱因**: `V10`
- **逐拍取证摘要**: In G04 (3-team match, map=10, land=546,152), our Team 1 held #1 with 248,433 land (45.5% of map vs Team 2's 226,797 and collapsing Team 3's 66,931) at t=5422, led by leo_tx (28,816L), noah88 (20,018L), and lucas94 (18,243L). Between t=5042 and t=6660, V7 (oppFloorCap=38, collapseFloorCap=16, totB=B+myOut, isPrimeLand keep<=10~26*L) combined with V10 (14x10%B RTT assist machine-gunning by noah88 at t=6594..6622) caused noah88 to fire 18 commands in 90 ticks (crashing home density from 96.9 to 33.8) and lucas94 to drop to d=27.8 while bordering 3 enemies. Meanwhile, boxed-in rear carry leo_tx (27,199L, nb=0) was continuously bled down to d=70~76 by 5% micro-donations (paying 6.25%B flat engine tax). Team 2 counter-attacked the hollowed-out d=27.8~33.8 frontline at t=6660 and swept lucas94 (t=6988), leo_tx (t=7237), and noah88 (t=7404).

## 二、专项核心变量全样本量化与因果机制

### `V7` — EffectiveFrontlineKeepDensity (预估胜率影响 `+31.0%`)
- **当前劣化值**: `oppFloorCap=38, collapseFloorCap=16, totB = B + myOut, isPrimeLand keep <= 10*L~26*L`
- **80% 胜率基线值**: `oppFloorCap=128, collapseFloorCap=85, avail = B - fee - keep (home B only, no 10*L prime override)`
- **推导最优阈值**: `oppFloorCap=112, collapseFloorCap=68, avail = B - fee - keep (never include in-flight myOut in person attack defense floor), thirdPartySafe floor >= max(68*L, (max3rdB - 1.5*L)/1.55)`
- **源码级因果机制**: When totB = B + myOut is used to compute avail = Math.min(B - fee, (B + myOut) - fee - keep) and keep is clamped to 10~38*L, every outgoing attack pulse myOut is double-counted as if it were still defending home territory. Under period=2 (112ms) and maxTargets=6, a frontline bot launches 3~5 concurrent pulses totaling myOut = 35%~65% of B, driving actual home balance B_home down to 0~28*L (181 hollow-out snapshots across G01-G09, 44/54 frontline deaths). Adjacent full-density enemies (d=100~135) immediately counter-sweep the defenseless frontline.
- **源码定位**: `tsb/squad/make_v27_team.py:976-998, 1060-1102 (tsb/squad/v27-team-live.js:3921, 3963, 5810-5868)`

## 三、核心变量权重排序

1. **`V7` (35.0%)**: totB=B+myOut + oppFloorCap=38 + keep<=10*L hollowed out frontline home density to d=27.8~33.8 in G04 (and d=0~14.6 across G01-G09), causing 100% of midgame #1 leads to get counter-swept.
2. **`V10` (20.0%)**: 2-tick RTT assist machine-gun bug caused noah88 to fire 10x10%B (t=5042) and 14x10%B (t=6594, -81% B) in G04 right before Team 2 counter-attacked.
3. **`V6` (16.0%)**: 79 micro-donations (pct=51) in G04 burned 6.10M troops in flat 6.25%B engine tax to deliver 4.96M (55.2% loss) and drained frontline carry leo_tx.
4. **`V5` (15.0%)**: 145 boats (61 sea intercepts) in G04 burned >1.8M troops/tax due to broken bQ.mt.mu deduplication and 35%B chase cap.
5. **`V1` (14.0%)**: 2/8 bots in G04 hit voronoi=500 island fallback at spawn, reducing main-continent opening presence to 6 bots.

## 四、最小可验证修复清单 (Actionable Fixes)

- **文件**: `tsb/squad/make_v27_team.py` (`buyLand (remove totB=B+myOut double-counting & restore oppFloorCap=112, collapseFloorCap=68)`, 风险: `low`)
  - 修改前: `oppFloorCap: 38, collapseFloorCap: 16; const totB = B + myOut; if (isPrimeLand && B >= 12 * L) keep = Math.min(keep, (o.nearCollapse || dqNow < 14 ? 10 : 26) * L); const avail = Math.min(B - fee, totB - fee - keep);`
  - 修改后: `oppFloorCap: 112, collapseFloorCap: 68; const avail = B - fee - keep; // enforce thirdPartySafe >= max(68*L, (max3rdB - 1.5*L)/1.55) when bordering any healthy enemy human`
