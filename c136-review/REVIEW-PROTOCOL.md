# 逐局精细复盘规程（v2.0）

> 适用：R01~R09 全体局内复盘员。
> 目标：把每一局从 tick 0 选点到终局结算的**具体局内情况**复盘到拍、复盘到兵力收支、复盘到策略源码行与引擎数学公式。

## 1. 输入：标准化局内对局包（`/agent/repos/c136-data/bundles/<matchId>/`）

每个 `<matchId>` 目录下已经为你准备好了全套局内文件（直接读取）：

| 文件 | 内容 |
| :-- | :-- |
| `card.json` | 对局卡：编队（`squad8`/`squad10`/`squad20`）、地图、总陆地 `mapLand`、名义与实际队数 `actualTeams`、我方主队 `ourPrimaryTeam`、是否拆队 `teamSplitCounts`、结局 `outcome`、同局碰撞信息 `sameMatchPeer`、异常摘要 `anomaliesSummary` |
| `timeline.txt` / `timeline.csv` | 预生成的整局每 90 拍全局时间线（存活数、编队总地、占全图份额、总兵力、平均密度、逐号 `terr/bal/dens/nb/neut`）+ 各号结算时刻的全场各队真实领土表（`team.totals`） |
| `stories/story_<bot>.txt` | 预生成的每个号逐拍变化表：相邻快照间的 `dTerr`、`dBal`、`dBal%`、`dCmds`、`dBoats`、自动标记的 `DROP30`（90 拍内兵力跌 ≥30%），以及该区间内发生的开局扩张、捐出 `DON>`、收到 `RCV<`、调度 `DIS>`、被拒标记 `[REJ?]`、协防 `AST`、海战拦截 `INT` |
| `traj.csv` / `opening.csv` / `spawn.csv` / `events.csv` / `results.csv` | 结构化 CSV 表，供你写脚本做精确计算 |
| `anomalies.json` | 预扫描的 `DROP30` 列表、疑似配额/上限拒单统计、内陆高密度滞留拍数 |
| `in_game.log` | 本局原始局内日志行 |
| `replay.txt` | 本局完整录像编码（141/160 局具备） |

配套源码与机制参考在 `/agent/repos/c136-data/src/`：
- 引擎机制与公式：`src/engine/engine-evidence.txt`、`m1-sim-facts.txt`、`live-donation-check.txt`
- 策略与选点源码：`src/strategy/v27-team-c116.js`（对应 `A` 组）、`v27-team-c110.js`（对应 `B` 组）、`v27-team-g09.js`（对应 `G` 组）、`params-diff.txt`、`logcalls-*.txt`、`spawn-coordinator-*.mjs`

---

## 2. 每局必做的十步深度复盘

1. **核对本局结构与分队状态（读 `card.json` 与 `timeline.txt` 末尾）：**
   - 确认实际队伍数 `actualTeams`、基础胜率期望 `1/actualTeams`、我方主队编号 `ourPrimaryTeam`。
   - 检查 `teamSplitCounts`：我方各号是全部在同一支队伍，还是被拆到了多支队伍？如果被拆队，各队分别有几个号？
2. **全局时间线与四阶段体检（读 `timeline.txt`）：**
   - 在 t≈90、270、630、1530、3060、4500、6030… 及各号阵亡拍，追踪两部分数据：① 我方编队存活数、总领土份额 `sqShare%`、总兵力 `sqBal`、总密度 `sqDens`；② 结算快照里的**整支队伍份额** `T<mine>` 与头号敌队份额。
   - 分四阶段写出具体事实与问题：**出生与选点几何（t=0~90）**、**开局中立扩张（t=90~630）**、**中盘交战与后勤输血（t=630~3500）**、**残局收口或崩盘（t>3500）**。
3. **定位关键转折窗口（1~3 个）：**
   - 输局找我方份额/排名跌得最猛、或从领先变落后的拍号窗口 `[t0, t1]`；胜局找拉开差距或顶住敌方反扑的窗口。
   - 查清窗口**之前**（`t0 - 300` 到 `t0`）我方涉及的号做了什么决策（出兵、留守底线、捐款/调度、发船），为什么这么做。
4. **逐个阵亡号的死因链（Death Chain）：**
   - 对本局每一个阵亡（`event=died`）的号，读它的 `stories/story_<bot>.txt`：阵亡拍号、阵亡前 500 拍的领土峰值与密度变化、死前最后几次兵力暴跌（`DROP30`）、死前有没有收到队友捐款/协防（还是捐款带了 `[REJ?]` 被配额拒单？或者死前自己还在往外捐兵？）。
5. **大额兵力损耗（`DROP30`）与输血效率逐笔对账：**
   - 对 `anomalies.json` 和 `story_<bot>.txt` 里的主要 `DROP30` 区间，查明兵去了哪里：① 主动陆攻（`dTerr > 0` 且 `dCmds > 0`）；② 发船/拦截（`dBoats > 0`）；③ 捐款/调度（`DON>` / `DIS>`，核对 6.25% 余额税与实际到账）；④ 被敌方进攻打穿（`dTerr < 0`）。
   - 特别审计本局的 `events.csv`：有多少笔 `DONATE` / `DISPATCH` 标记了 `likelyRejected=True`？哪些号在 `nb=0, neut=0` 的内陆后排长期卡在 `dens >= 100` 浪费利息？哪些号在 `pct < 150` 下频繁小额捐款被 6.25% 全额税抽干？
6. **具体决策审计（不少于 10 条决策实例，追到策略源码函数与分支）：**
   - 对照 `src/strategy/` 源码，把本局的关键错误决策与正确决策（至少含 2 条有效/正确决策）追到具体函数与条件（例如 `tryDonateToTeammate`、`buyLand`、`offers`、`safeAt`、`floors`、`tryEmergencySquadAssist`、`tryInterceptEnemyBoats`、`openingExpand`、`spawn-coordinator`）。
7. **赢家与对手分析：**
   - 结合 `team.totals`（及录像重放数据，如有），说明获胜队伍是什么时候建立优势的，我方在多队博弈中是否陷入两线作战或打错目标。
8. **归类与模式打标：**
   - 给出本局 `lossArchetype`（`early-wipe` / `never-grew` / `mid-collapse` / `lead-thrown` / `outscaled` / `team-split` / `win`），并为每个决策实例标注模式编号（见 `ledger/PATTERNS.md` 或提议 `NEW`）。

---

## 3. 输出格式（每局两份文件）

保存在你自己的分支目录下：
- `c136-review/agents/RNN/reviews/<matchId>.json`（结构化 JSON，供 `collect-reviews.py` 跨局汇总）
- `c136-review/agents/RNN/reviews/<matchId>.md`（深度复盘叙述报告，建议 80~180 行，写透细节）

JSON 必填字段与原规程一致（`matchId`, `reviewer`, `protocol`, `context`, `outcome`, `timeline`, `phases`, `turningPoints`, `deaths`, `decisions`, `newPatterns`, `lossArchetype`, `winnerNotes`, `wentWell`, `unknowns`, `mechanicsQuestions`, `scripts`, `confidenceOverall`）。
