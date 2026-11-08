# c116 十路子 Agent (`S01 ~ S10`) 80% 胜率根因与核心变量终极汇总报告 (`MASTER-SYNTHESIS.md`)

> **状态**: ✅ **10 / 10 子 Agent (`S01 ~ S10`) 报告与结构化数据已 100% 全部合入双仓库 (`jvfoedfve` & `fdvg` 分支 `cursor/c116-winrate-liaison-b3bc`)**

## 一、10 子 Agent 全局核心变量权重总排序 (10/10 交叉验证)

| 总排名 | 核心变量 | 10-Agent 平均权重 | 认领 Agent 数 | 核心定性结论 |
| :---: | :---: | :---: | :---: | :--- |
| **#1** | **`V7`** | **`28.9%`** | `10/10` | In G01, oppFloorCap=38 + keep<=10~26*L + totB=B+myOut caused frontline bots to dump 5.33M troops in 180 ticks (t=4320->4500) and drained ryan_m (51.2k land) to dens=7.1 at t=5040. |
| **#2** | **`V1`** | **`17.1%`** | `10/10` | In 7/10 live games (G00,G02,G04,G05,G06,G07,G09), VirtualSquadAnchor picked tiny islands (48~50 voronoi=500 fallbacks) or secondary continents (G06 190k vs 354k main continent). |
| **#3** | **`V6`** | **`11.5%`** | `10/10` | Boxed-in coastal teammates (kevin_k 1.05M, ethan21 473k in G01) had isPureInlandSafe=false, deadlocking squad rescue donate (requires dMe>=106) below coastGuardFloor=68*L. |
| **#4** | **`V2`** | **`9.4%`** | `7/10` | fd868f3's allyMinSep<=112px & clusterMax<=350px cut t=1500 team land by -28% (0/9 multi-team games reached >=22% land at t=1530) and boxed in 3 bots in G01 with 2.02M stranded troops. |
| **#5** | **`V5`** | **`8.1%`** | `8/10` | 23 sea intercepts in G02 and 44 in G03 (up to 35%B per boat) drained lucas94 (B: 377k->237k at t=3000 in G02) and ryan_m (B: 530k->294k at t=3350..3510 in G03) right before enemy land pushes. |
| **#6** | **`V10`** | **`6.0%`** | `4/10` | 2-tick RTT assist machine-gun bug caused noah88 to fire 10x10%B (t=5042) and 14x10%B (t=6594, -81% B) in G04 right before Team 2 counter-attacked. |
| **#7** | **`V12`** | **`4.6%`** | `5/10` | Lobby team count and allied human mass determined baseline margin for error: G07 was won only because it was a 2-team game where ~21 allied humans held 43.4% of the map by t=1776. |
| **#8** | **`V4`** | **`3.8%`** | `3/10` | period=2 (112ms) + 2-tick inflight lock inflated total commands in G06 to 2,836 (354/bot), multiplying 1.17%B land attack tax burn during micro-pulses. |
| **#9** | **`V9`** | **`3.2%`** | `1/10` | hardCapMult=1.16 + beachhead false-positive + 2-tick unthrottled 10% squad-rescue machine-gun bursts (5~14x 10%B in 12t) directly drained 50%~88% of healthy frontline bots' balances in G08 and 6 of 8 losses. |
| **#10** | **`V3`** | **`2.8%`** | `2/10` | Uncapped dpKeep + minCmd>=4.69%B blocked 53.9% of t=600..1499 neutral-border snapshots (73.2% in G03), and the t=1500 double-expandNeutral + minGrab bug burned 15k..35k troops, keeping L_team(1500)/L_map well below the 80%-winrate survival line. |
| **#11** | **`V11`** | **`2.4%`** | `1/10` | Zero lead-closing protocol when #1 (no frontline density lock, 46%~62% of squad land frozen in coastal rear bots at d=70~78, and unthrottled 2-tick [HL-ASSIST] spam). |
| **#12** | **`V8`** | **`2.2%`** | `1/10` | isPrimeLand unconditionally overwrote keep to 10~26*L and raised curAtk caps to 14~16%B without checking 3rd-party strong neighbors, causing 44/54 prime-land harvesters across G01..G09 to hollow out and die. |

## 二、10 个子 Agent 交付文件索引

- **`S01`**: `c116-winrate/reports/s01-report.md` | `c116-winrate/reports/s01-data.json`
- **`S02`**: `c116-winrate/reports/s02-report.md` | `c116-winrate/reports/s02-data.json`
- **`S03`**: `c116-winrate/reports/s03-report.md` | `c116-winrate/reports/s03-data.json`
- **`S04`**: `c116-winrate/reports/s04-report.md` | `c116-winrate/reports/s04-data.json`
- **`S05`**: `c116-winrate/reports/s05-report.md` | `c116-winrate/reports/s05-data.json`
- **`S06`**: `c116-winrate/reports/s06-report.md` | `c116-winrate/reports/s06-data.json`
- **`S07`**: `c116-winrate/reports/s07-report.md` | `c116-winrate/reports/s07-data.json`
- **`S08`**: `c116-winrate/reports/s08-report.md` | `c116-winrate/reports/s08-data.json`
- **`S09`**: `c116-winrate/reports/s09-report.md` | `c116-winrate/reports/s09-data.json`
- **`S10`**: `c116-winrate/reports/s10-report.md` | `c116-winrate/reports/s10-data.json`
