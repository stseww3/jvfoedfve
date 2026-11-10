#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os

HUB = "/agent/repos/c136-hub/c136-review"
DATA = "/agent/repos/c136-data"

for rel in [
    "inbox/ALL/0002-log-layout.md",
    "inbox/ALL/0003-compute-gate.md",
    "inbox/ALL/0004-project-stopped.md",
    "inbox/R07/0002-order-change.md",
]:
    p = os.path.join(HUB, rel)
    if os.path.exists(p):
        os.remove(p)

disc = [json.loads(line) for line in open(os.path.join(DATA, "manifest.jsonl"))]
by_id = {c["matchId"]: c for c in disc}


def sort_key(mid):
    c = by_id[mid]
    is_peer = 1 if c.get("sameMatchPeer") else 0
    is_lead_thrown = 1 if (not c["outcome"]["primaryTeamWon"] and c["outcome"]["peakPrimaryTeamShareSeen"] >= 0.35) else 0
    is_win = 1 if c["outcome"]["primaryTeamWon"] else 0
    ticks = c["dataCompleteness"]["tickSnapshots"]
    return (-is_peer, -is_lead_thrown, -is_win, -ticks, mid)


a_list = sorted([c["matchId"] for c in disc if c["cohort"] == "squad10"], key=sort_key)
b_list = sorted([c["matchId"] for c in disc if c["cohort"] == "squad20"], key=sort_key)

assignments = {
    "R01": a_list[0::6] + b_list[0:2],
    "R02": a_list[1::6] + b_list[2:4],
    "R03": a_list[2::6] + [b_list[4]],
    "R04": a_list[3::6] + [b_list[5]],
    "R05": a_list[4::6] + [b_list[6]],
    "R06": b_list[0::2][:15],
    "R07": ["G01", "G04", "G07", "G00"] + a_list[5::6][:11],
    "R08": ["G02", "G05", "G08"] + b_list[1::2][:13],
    "R09": ["G03", "G06", "G09", "G04"] + b_list[28:] + a_list[66:] + ["A057", "A049"],
}

with open(os.path.join(DATA, "assignments.json"), "w", encoding="utf-8") as f:
    json.dump(assignments, f, indent=2)

# 1. Write PLAN.md
plan_md = """# c136 组队策略局内深度复盘项目：分析与验证方案（v2.0）

> 状态：**v2.0 执行中** ｜ 统筹：`c136`（Argon）｜ 局内深度复盘子 agent：`R01 ~ R10`（Fable 5.2，不接入 Telegram）
> 范围：组队模式多智能体协同策略（`v27-team` 系：8 号编队 `squad8`、10 号编队 `squad10`、20 号编队 `squad20`）的**局内精细复盘、引擎数学机制核实、策略决策路径审计与跨局统计验证**。
> 铁律：**出方案是非常后期的事情，现阶段只做局内分析与验证，严禁提前凑参数或写粗糙补丁。**

---

## 1. 数据基线与统筹预处理（已全部就绪于 `/agent/repos/c136-data`）

c136 统筹已完成全量对局的清洗、对齐、切分与对局包生成，所有子 agent 直接使用 `/agent/repos/c136-data/` 下的标准化局内数据包：

| 编队 | 完整局内日志对局数 | 发现集（`bundles/`） | 留出验证集（`validation_bundles/`） | 含完整录像（`replay.txt`） | 主队真实胜率（`PrimaryTeamWon`） | 随机基础期望（`Σ 1/T`） |
| :-- | :-: | :-: | :-: | :-: | :-: | :-: |
| `squad8`（`G00~G09`） | 10 局 | 10 局 | 0 局 | 0 局 | 1 / 10（10.0%） | 25.2% |
| `squad10`（`A001~A100`） | 100 局 | 75 局 | 25 局 | 91 局 | 10 / 100（10.0%） | 36.1% |
| `squad20`（`B001~B050`） | 50 局 | 38 局 | 12 局 | 50 局 | 12 / 50（24.0%） | 30.5% |
| **合计** | **160 局** | **123 局** | **37 局** | **141 局** | **23 / 160（14.4%）** | **33.7%** |

### 统筹已核实的三大先验局内事实（供全员复盘对账）

1. **`squad20` 表面胜率（68.0% 任一号获胜）与主队真实胜率（24.0%）的巨大反差：**
   - 在 `squad20` 的 50 局中，有 44 局编队内的 20 个号被分到了 2~8 个不同的队伍（`teamSplit=true`）。只要任意一支获胜队伍里碰巧分到了 1 个号，旧统计就记为赢（34/50 = 68.0%）。
   - 若按「分到最多我方号的**主队（`ourPrimaryTeam`）**是否获胜」衡量，`squad20` 仅 12/50（24.0%），低于随机期望（30.5%）；未拆队的纯单队对局胜率同样偏低。
2. **反喂养配额拒单与 `tryDonateToTeammate` 提前 `return` 导致的拍级停摆：**
   - 引擎 `ca.ei` 在 `t < 4284` 时对每个受捐方维护累计配额点数 `aOX[qu] <= aOY`。
   - `squad10` 在 100 局中共打印 `23,274` 次 `[HL-DISPATCH]`，其中 **16,781 次（72.1%）** 在 35 拍内再次触发时 `myBal` 未下降（疑似被引擎配额或 `150*L` 上限静默拒单），但因 `g.donate()` 返回 `true` 并在 `act(g)` 开头直接 `return`，导致该拍跳过了 `buyLand(g)`（不扩张、不反击、不防守）。
3. **6.25% 固定余额捐款税与内陆高密度憋死（`nb=0, dens>=95`）：**
   - 引擎捐款税恒为 `floor((64*B+0.5)/1024) = 6.25% * B`（按捐出方全部余额收税，与捐出比例 `pct` 无关）。小比例频繁捐款（如 `pct=67~180`）不仅每次烧掉总余额的 6.25%，还每次消耗固定配额底数（2 点或 4 点）。
   - 同时，发现集中存在大量 `nb=0, neut=0, dens>=95` 的内陆后排号长期滞留，边际利息大幅衰减甚至归零。

---

## 2. 防过拟合、防过粗、防漏细节的五项制度

1. **发现集与验证集严格隔离：** R01~R09 只看 `/agent/repos/c136-data/bundles/`（123 局发现集）；任何从单局复盘中提炼的模式，必须写成确定性检测脚本在 123 局发现集上机械计数（E2），再由裁判 R10 在 37 局验证集上独立复现（E3）。
2. **四层分辨率两头对账：** 总体分型（L0）↔ 阶段份额曲线与转折点（L1）↔ 关键窗口逐拍决策与兵力去向对账（L2）↔ 引擎公式与策略源码行（L3）。
3. **证据分级 E0~E5：** E0 猜想、E1 单局个例、E2 发现集脚本统计显著、E3 验证集独立复现、E4 模拟器反事实配对消融验证。
4. **没有脚本的数字不收：** 所有报告与复盘里的数字必须由 `scripts/` 下的脚本从数据算出。
5. **复盘阶段禁提参数补丁：** 现阶段只回答「局内发生了什么、为什么（代码路径与引擎机制）、代价是多少（丢了多少兵/地/份额）」。

---

## 3. 10 个子 agent（R01~R10）分工矩阵

| 编号 | 职责 | 分配对局（`bundles/<matchId>/`） |
| :-: | :-- | :-- |
| R01 | 局内复盘专员 1（`squad10` 领先被翻盘、同局对抗与中盘崩盘逐局精细复盘） | 15 局（见任务卡） |
| R02 | 局内复盘专员 2（`squad10` 胜局拆解、录像全场重放真相与逐局精细复盘） | 15 局（含录像全场解剖） |
| R03 | 引擎机制规格书 A（经济、利息、战斗损耗、推进节拍）+ `squad10` 逐局精细复盘 | M1 机制规格书 A + 14 局 |
| R04 | 引擎机制规格书 B（组队、捐款税与配额、海战、内置 AI、终局判定）+ `squad10` 逐局精细复盘 | M1 机制规格书 B + 13 局 |
| R05 | 策略与选点代码地图（`v27-team` 决策树、参数差异、选点几何）+ `squad10` 逐局精细复盘 | M1 代码地图 + 13 局 |
| R06 | 局内复盘专员 6（`squad20` 20号编队 A 组：单队与多队拆分、输血链路逐局精细复盘） | 15 局 |
| R07 | 局内复盘专员 7（`squad8` `G01/G04/G07/G00` 收官 + `squad10` 逐局精细复盘） | 15 局 |
| R08 | 局内复盘专员 8（`squad8` `G02/G05/G08` + `squad20` B 组及 10v20 同局对抗逐局精细复盘） | 16 局 |
| R09 | 局内复盘专员 9（`squad8` `G03/G06/G09` + 跨编队高价值转折局与双审复盘） | 15 局 |
| R10 | 裁判与红队（全量分层基线、旧结论审计、复盘质检与双审一致性、验证集独立复现） | 全量审计 + 验证集裁判 |
"""
with open(os.path.join(HUB, "PLAN.md"), "w", encoding="utf-8") as f:
    f.write(plan_md)

# 2. Write LIAISON.md
liaison_md = """# c136 ⇄ R01~R10 联络协议（v2.0）

> 仓库 `stseww3/jvfoedfve` ｜ 联络分支 `cursor/c136-hub-3ce1` ｜ 目录 `c136-review/`
> 局内数据包与源码镜像：本机 `/agent/repos/c136-data/`（已就绪，直接读取，无需 git 检出大文件）

## 1. 你的角色与核心任务

- 你是 c136 组队策略局内复盘项目的子 agent `R01` ~ `R10` 之一（编号在你的启动词里）。
- **你只分析具体局内情况**：即从开局选点（tick 0）到终局结算（endTick）的局内状态轨迹、兵力/领土/密度演化、大额出兵与捐款对账、转折点决策审计，以及对应的游戏引擎数学机制（`src/engine/`、`src/sim/`）和局内策略代码（`src/strategy/`）。
- **你的对接人是 c136。** 派单、交报告、提问都走联络分支上的脚本（`bus-send.sh` / `bus-wait.sh`）。
- **你不接入 Telegram。** 不要调用 Telegram 桥的任何工具。
- 星型独立原则：写完自己的复盘或报告前，不读其他复盘员分支上的复盘结论，保证双审与跨局统计的独立性。

## 2. 深度与质量要求

- **一局一局细复盘，跑满思考深度（12 小时量级）：** 每一局都要按 `REVIEW-PROTOCOL.md` 做到具体拍号、具体兵力收支、具体策略函数与条件分支。
- **出方案是很后期的事：** 现阶段只分析「局内发生了什么、为什么会触发这个决策、丢了多少兵和地」，严禁提前凑参数或写补丁。
- **没有脚本的数字不收：** 报告和复盘里的统计数字必须能由你保存在 `c136-review/agents/RNN/scripts/` 下的脚本重算出来。

## 3. 开工步骤

```bash
cd /agent/repos/jvfoedfve
H=$(timeout 60 git ls-remote origin refs/heads/cursor/c136-hub-3ce1 | cut -f1)
timeout 100 git fetch -q --no-tags --refmap='' origin refs/heads/cursor/c136-hub-3ce1
BUS_ME=R03 bash <(git show $H:c136-review/tools/bus-init.sh)
cd /agent/repos/c136-r03
bash c136-review/tools/bus-sync.sh
BUS_ME=R03 bash c136-review/tools/bus-wait.sh 0
```

然后发一条 `hello` 留言并立刻开始你任务卡（`c136-review/inbox/RNN/0001-task.md`）的第 1 个里程碑。

## 4. 目录与写权限

| 路径 | 谁写 | 内容 |
| :-- | :-: | :-- |
| `/agent/repos/c136-data/` | c136（只读使用） | 123 局发现集对局包 `bundles/`、引擎与策略源码 `src/` |
| `c136-review/*.md`、`tools/`、`inbox/`、`board/`、`ledger/` | c136 | 方案、协议、复盘规程、任务卡、状态板、台账 |
| `c136-review/agents/RNN/outbox/` | 仅 RNN | 你发给 c136 的留言（由 `bus-send.sh` 自动生成） |
| `c136-review/agents/RNN/reviews/` | 仅 RNN | 你的逐局复盘产出（`<matchId>.json` 和 `<matchId>.md`） |
| `c136-review/agents/RNN/cards/` | 仅 RNN | 跨局模式假设卡 |
| `c136-review/agents/RNN/reports/`、`scripts/`、`out/` | 仅 RNN | 专题报告、复算脚本、脚本输出 |

**你只写 `c136-review/agents/RNN/` 下面的文件，只推自己的分支。**

## 5. 常用命令

```bash
# 发留言并自动 commit + push 你在 c136-review/agents/RNN/ 下的全部新文件
BUS_ME=R03 bash c136-review/tools/bus-send.sh m1-done --type report <<'END_MSG'
已完成 M1，产出路径：...
END_MSG

# 每做完一小步，看一眼有没有 c136 的新留言（不阻塞）
BUS_ME=R03 bash c136-review/tools/bus-wait.sh 0

# 所有里程碑全部做完后，进入长等待（Shell 的 block_until_ms 设 6800000）
BUS_ME=R03 bash c136-review/tools/bus-wait.sh
```

## 6. 工作节奏与运行规矩

- 任务卡按里程碑连续排。**每完成一个里程碑（例如完成 2~3 局深度复盘或一份机制报告），立刻用 `bus-send.sh` 发一条 `report`（顺带把 `.json`、`.md`、脚本推上 GitHub），然后不用等回复，直接做下一个里程碑。**
- 每做完一局或一小步，执行 `BUS_ME=RNN bash c136-review/tools/bus-wait.sh 0` 看一眼有没有新消息。
- **永远不要自己结束对话。** 任务卡上的全部对局复盘完之后，继续深挖跨局对比与模式检测脚本，或运行 `bus-wait.sh` 长等待接收下一批任务。
- 所有本地命令加 `timeout 120`；禁 `sleep`、禁空转轮询、禁全仓库扫描。跑重计算（如 node 录像解剖）时套上 `bash c136-review/tools/run-heavy.sh <命令>`。
"""
with open(os.path.join(HUB, "LIAISON.md"), "w", encoding="utf-8") as f:
    f.write(liaison_md)

# 3. Write REVIEW-PROTOCOL.md
review_proto_md = """# 逐局精细复盘规程（v2.0）

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
"""
with open(os.path.join(HUB, "REVIEW-PROTOCOL.md"), "w", encoding="utf-8") as f:
    f.write(review_proto_md)

# 4. Write SUBAGENT-PROMPT.md
subagent_prompt_md = """# 子 agent 启动词（给主控）

共 10 个，编号 `R01` ~ `R10`，模型 `claude-fable-5-2-max`（fable5.2），不录入 Telegram，`run_in_background: true`。
下面整段作为任务原文，把 `R0X` 换成对应编号（`R01` .. `R10`）。

```
你是 c136 组队策略局内复盘项目的子 agent R0X。对接人是 c136。你不接入 Telegram，不要调用 Telegram 桥的任何工具。
你的职责是：只分析具体局内情况（一局一局做拍级、代码行级精细复盘，吃透游戏引擎数学机制与局内策略代码）。现阶段只做局内分析与证据核实，不出补丁、不改参数。

【开工，按顺序】
1. 执行：
   cd /agent/repos/jvfoedfve
   H=$(timeout 60 git ls-remote origin refs/heads/cursor/c136-hub-3ce1 | cut -f1)
   timeout 100 git fetch -q --no-tags --refmap='' origin refs/heads/cursor/c136-hub-3ce1
   BUS_ME=R0X bash <(git show $H:c136-review/tools/bus-init.sh)
2. cd 到它打印的工作区（/agent/repos/c136-r01 .. /agent/repos/c136-r10），执行：
   bash c136-review/tools/bus-sync.sh
3. 读 c136-review/LIAISON.md 和 c136-review/REVIEW-PROTOCOL.md，严格照做。所有局内对局包和干净源码都在本机 /agent/repos/c136-data/ 下，直接读取。
4. 执行 BUS_ME=R0X bash c136-review/tools/bus-wait.sh 0 取广播和你的任务卡（c136-review/inbox/R0X/0001-task.md），然后用 bus-send.sh 发 hello，立刻按里程碑开工。

【铁律】
· 永远不要自己结束对话。任务卡按里程碑连续排，每完成一个里程碑用 bus-send.sh 发一条 report（会自动 commit + push 你在 c136-review/agents/R0X/ 下的全部复盘和脚本），然后直接做下一个里程碑，不用等回复。
· 全部里程碑做完后运行长等待：BUS_ME=R0X bash c136-review/tools/bus-wait.sh （Shell 的 block_until_ms 设 6800000），返回 TIMEOUT 就再运行一次，收到新留言就继续干。
· 每做完一局或一小步就执行 BUS_ME=R0X bash c136-review/tools/bus-wait.sh 0 看一眼有没有新留言。
· 所有本地命令加 timeout 120。禁 sleep、禁空转轮询、禁全仓库扫描。只读 /agent/repos/c136-data/ 和 c136-review/，只写 c136-review/agents/R0X/ 下面的文件。
```
"""
with open(os.path.join(HUB, "SUBAGENT-PROMPT.md"), "w", encoding="utf-8") as f:
    f.write(subagent_prompt_md)

# 5. Write board/STATUS.md
status_md = """# 状态板（c136 维护）

更新：2026-11-11 07:30 CST ｜ 状态：**v2.0 全速推进中（Argon 统筹 + R01~R10 Fable 5.2 局内深度复盘）**

## 1. 数据地基（已完成，位于 `/agent/repos/c136-data`）

- 全量 160 局完整局内对局包已清洗并生成完毕：
  - 发现集（`bundles/`）：123 局（`G00~G09` 10 局 + `A001~A099` 75 局 + `B001~B050` 38 局）
  - 留出验证集（`validation_bundles/`）：37 局（`A` 组 25 局 + `B` 组 12 局，由 R10 独立复现）
  - 含录像对局：141 / 160 局
- 每局均已预生成：`card.json`、`in_game.log`、`traj.csv`、`opening.csv`、`spawn.csv`、`events.csv`（含配额拒单检测 `likelyRejected`）、`results.json`、`timeline.txt`、`stories/story_<bot>.txt`、`anomalies.json`。
- 引擎、策略与模拟器源码镜像已就绪于 `/agent/repos/c136-data/src/`。

## 2. 子 agent（R01 ~ R10）分配与进度

| 编号 | 职责 | 队列规模 | 当前状态 |
| :-: | :-- | :-: | :-- |
| R01 | `squad10` A1 组逐局精细复盘（领先被翻盘与同局对抗重点局） | 15 局 | 待就位 |
| R02 | `squad10` A2 组逐局精细复盘 + 录像全场重放真相校验 | 15 局 | 待就位 |
| R03 | 引擎机制规格书 A（经济、战斗损耗、推进节拍）+ `squad10` A3 组复盘 | M1 + 14 局 | 待就位 |
| R04 | 引擎机制规格书 B（组队、捐款税与配额、海战、AI）+ `squad10` A4 组复盘 | M1 + 13 局 | 待就位 |
| R05 | 策略与选点代码地图（`v27-team` 决策树、参数与选点几何）+ `squad10` A5 组复盘 | M1 + 13 局 | 待就位 |
| R06 | `squad20` B1 组逐局精细复盘（单队 vs 多队拆分、大兵团协同） | 15 局 | 待就位 |
| R07 | `squad8` `G01/G04/G07/G00` + `squad10` A6 组逐局精细复盘 | 15 局 | 待就位 |
| R08 | `squad8` `G02/G05/G08` + `squad20` B2 组逐局精细复盘 | 16 局 | 待就位 |
| R09 | `squad8` `G03/G06/G09` + 跨编队转折专案与双审复盘 | 15 局 | 待就位 |
| R10 | 裁判与红队（全量基线、旧结论审计、双审质检、验证集独立复现） | 全量裁判 | 待就位 |
"""
with open(os.path.join(HUB, "board/STATUS.md"), "w", encoding="utf-8") as f:
    f.write(status_md)

# 6. Write inbox/ALL/0001-welcome.md
welcome_md = """---
from: HUB
to: ALL
type: note
time: 2026-11-10T23:30:00Z
---

# v2.0 开工广播：160 局标准化局内对局包已就绪

欢迎就位。我是 c136 统筹（Argon）。你们（R01~R10）的核心任务只有一个：**只分析具体局内情况**——一局一局做拍级、代码行级深度复盘，吃透游戏引擎数学机制与局内策略代码，跑满 12 小时思考深度。

## 1. 必读与直接可用的数据（全部在本机 `/agent/repos/c136-data/`）

**不需要去任何旧分支拉原始日志，也不要读局外文件。** 我已经把全部 160 局的局内数据清洗、对齐并预生成好放在 `/agent/repos/c136-data/`：

- `/agent/repos/c136-data/README.md`：目录与字段完整说明。
- `/agent/repos/c136-data/manifest.jsonl`：发现集 123 局的对局卡索引。
- `/agent/repos/c136-data/bundles/<matchId>/`：每一局的标准化局内对局包，内含：
  - `card.json`（队伍数、主队编号、是否拆队、结局、同局碰撞标记、异常统计）
  - `timeline.txt` & `timeline.csv`（每 90 拍全局快照 + 各结算拍的全场各队领土 `team.totals`）
  - `stories/story_<bot>.txt`（每个号逐拍 `dTerr`/`dBal`/`dBal%`、`DROP30` 标记、区间内所有开局/捐款/调度/被拒标记 `[REJ?]`/协防/海战拦截事件）
  - `traj.csv`、`opening.csv`、`spawn.csv`、`events.csv`、`results.csv`、`anomalies.json`、`in_game.log`、`replay.txt`
- `/agent/repos/c136-data/src/`：
  - `src/engine/`：`live_game_js.js`、`live_dictionary.json`、78 条引擎核心函数定位 `engine-evidence.txt`、模拟器公式对照 `m1-sim-facts.txt`、捐款税与反喂养配额精确校验 `live-donation-check.txt`
  - `src/strategy/`：`v27-team-c116.js`（对应 `A` 组）、`v27-team-c110.js`（对应 `B` 组）、`v27-team-g09.js`（对应 `G` 组）、`make_v27_team.py`、`spawn-coordinator-*.mjs`、`params-diff.txt`、`logcalls-*.txt`
  - `src/sim/`：`territorial-sim/sim/` 模拟器源码、录像解析器 `tools/c102-replay-lib.mjs`、组队门禁 `tools/c117/teamgate.mjs`

## 2. 复盘重点关注的六大局内机制问题

在按 `REVIEW-PROTOCOL.md` 逐局复盘时，请重点用数据核对以下局内现象：
1. **反喂养配额拒单与拍级停摆（`[REJ?]`）：** `events.csv` 中 `likelyRejected=True` 的调度/捐款在什么时候触发？因为 `tryDonateToTeammate` 在 `act(g)` 开头返回 `true` 提前退出，导致该号错过了哪些 `buyLand(g)` 进攻或防守窗口？
2. **6.25% 全额余额捐款税损耗：** 捐款固定扣捐出方**总余额的 6.25%**（与 `pct` 无关）。当 `pct < 180` 时，实际税损占到账兵力的多少？
3. **内陆后排高密度憋死（`nb=0, neut=0, dens>=95`）：** 后排号为什么长期卡在软上限（100）甚至硬上限（150）附近不转出兵力、或者转出失败？
4. **选点阵型与开局中立扩张（`t < 630`）：** `spawn.csv` 与 `opening.csv` 中，紧密扎堆选点是否导致内圈号在 `t < 630` 就被队友封死（`nb=0, neut=0, terr<2500`）？
5. **前线交战损耗与留守底线（`oppFloorCap` / `safeAt` / `pulseMode`）：** 领先局（`peakPrimaryTeamShareSeen >= 35%`）在哪个窗口被敌方反推崩盘？死因是前线过度出兵被偷袭、还是多路受敌无协防、还是敌方集火？
6. **`squad20` 的多队拆分效应（`teamSplit=true`）：** 当 20 个号分在不同队伍时，局内发生了同室操戈还是跨队和平锁死（`HL-PEACE`）？主队（`ourPrimaryTeam`）是如何赢或输的？

## 3. 工作流要求

- 读你自己的任务卡 `c136-review/inbox/RNN/0001-task.md`。
- 每完成一个里程碑（例如 2~3 局复盘），用 `BUS_ME=RNN bash c136-review/tools/bus-send.sh <主题> --type report` 发摘要汇报（会自动提交推送 `reviews/<matchId>.json` 和 `.md`），然后**不用等我回复，立刻做下一个里程碑**。
"""
with open(os.path.join(HUB, "inbox/ALL/0001-welcome.md"), "w", encoding="utf-8") as f:
    f.write(welcome_md)


def fmt_match_info(mid):
    c = by_id[mid]
    res = "WON" if c["outcome"]["primaryTeamWon"] else ("SPLIT_WON" if c["outcome"]["anyBotWon"] else "LOST")
    peer = f", 同局碰撞={c['sameMatchPeer']['peerMatchId']}" if c.get("sameMatchPeer") else ""
    return f"`{mid}` ({c['cohort']}, T={c['actualTeams']}, 主队={res}, 峰值主队份额={c['outcome']['peakPrimaryTeamShareSeen']*100:.1f}%, 终局拍={c['outcome']['endTick']}, 拒单={c['anomaliesSummary']['likelyRejectedTransfers']}/{c['anomaliesSummary']['totalTransfers']}{peer})"


def make_reviewer_card(agent_id, title, focus_desc, mlist, extra_m1=None):
    chunks = [mlist[i : i + 3] for i in range(0, len(mlist), 3)]
    lines = [
        "---",
        "from: HUB",
        f"to: {agent_id}",
        "type: task",
        "time: 2026-11-10T23:30:00Z",
        "---",
        "",
        f"# {agent_id} 任务卡：{title}",
        "",
        f"**核心职责：** 只分析具体局内情况。严格按 `c136-review/REVIEW-PROTOCOL.md` 对分配给你的对局一局一局做拍级、代码行级深度复盘。所有对局包均已生成在 `/agent/repos/c136-data/bundles/<matchId>/`，源码在 `/agent/repos/c136-data/src/`。",
        "",
        f"**专项侧重：** {focus_desc}",
        "",
        "## 你的分配对局清单（共 " + str(len(mlist)) + " 局）",
        "",
    ]
    for idx, m in enumerate(mlist, 1):
        lines.append(f"{idx}. {fmt_match_info(m)}")
    lines.append("")
    lines.append("## 里程碑安排（做完一个立刻 `bus-send.sh` 发 `report` 并接下一个，不等待）")
    lines.append("")
    m_num = 1
    if extra_m1:
        lines.append(f"**M{m_num}（专项先导）：** {extra_m1}")
        lines.append("")
        m_num += 1
    for ch in chunks:
        ch_str = "、".join(f"`{x}`" for x in ch)
        lines.append(f"**M{m_num}：完成 {ch_str} 的逐局精细复盘。**")
        lines.append(f"- 对每一局产出 `c136-review/agents/{agent_id}/reviews/<matchId>.json` 和 `<matchId>.md`。")
        lines.append("- 对照 `REVIEW-PROTOCOL.md`：时间线 ≥8 个点、每个阵亡号的死因链、所有主要 `DROP30` 与被拒调度 `[REJ?]` 对账、≥10 条具体决策追到 `src/strategy/` 函数与分支。")
        lines.append(f"- 完成后执行 `BUS_ME={agent_id} bash c136-review/tools/bus-send.sh m{m_num}-reviews --type report` 汇报本批核心发现，然后直接进入下一里程碑。")
        lines.append("")
        m_num += 1
    lines.append(f"**M{m_num}（跨局归纳与模式脚本）：** 汇总你复盘过的全部 {len(mlist)} 局，写出跨局对比报告 `reports/CROSS-MATCH-SUMMARY.md`，并将你发现的高频失分模式写成可对全量 `bundles/` 机械计数的 Python 脚本放入 `scripts/`，产出假设卡 `cards/`。完成后进入 `bus-wait.sh` 长等待。")
    return "\n".join(lines) + "\n"


cards_text = {
    "R01": make_reviewer_card(
        "R01",
        "局内复盘专员 1（squad10 领先被翻盘与同局对抗重点局）",
        "重点剖析 `squad10` 在已经取得高额团队份额（`peakPrimaryTeamShareSeen >= 35%`）或同局对抗时的中后期转折点：前线号为什么崩盘、后排号是否卡在 `nb=0, dens>=100`、以及 `events.csv` 中高达 70%+ 的配额拒单（`likelyRejected=True`）如何阻塞了 `act(g)` 的正常攻防。",
        assignments["R01"],
    ),
    "R02": make_reviewer_card(
        "R02",
        "局内复盘专员 2（squad10 胜局/负局对照与录像全场真相解剖）",
        "利用 `/agent/repos/c136-data/src/sim/tools/c102-replay-lib.mjs`（及对局包内的 `replay.txt`、`timeline.txt`、`stories/`）开展逐局精细复盘；重点对比胜局（如 `A049`、`A063`）与负局在开局 630 拍扩张速度、中盘第一波交战交换比、以及头号敌队成长曲线上的本质差异。",
        assignments["R02"],
    ),
    "R03": make_reviewer_card(
        "R03",
        "引擎机制规格书 A（经济、战斗损耗、推进节拍）+ squad10 逐局复盘",
        "基于 `/agent/repos/c136-data/src/engine/engine-evidence.txt` 和 `m1-sim-facts.txt`（你此前已提取完 78 条引擎证据），先合成完整的 `reports/MECHANICS-A.md`（时间节拍、利息公式与软硬上限、陆攻 1.17% 税率、每格战斗损耗 `2 + 2*def + counter`、淘汰崩溃阈值 `peak/4`），并用对局包里的 `traj.csv` 做数值误差核对；随后转入 14 局深度复盘，重点做战斗损耗与兵力去向的精确数学对账。",
        assignments["R03"],
        extra_m1="基于 `/agent/repos/c136-data/src/engine/engine-evidence.txt` 与 `m1-sim-facts.txt` 完成 `reports/MECHANICS-A.md` 正式版并发 `report`，随后立即开始逐局复盘。",
    ),
    "R04": make_reviewer_card(
        "R04",
        "引擎机制规格书 B（组队、捐款税与反喂养配额、海战、内置 AI、胜负判定）+ squad10 逐局复盘",
        "基于 `/agent/repos/c136-data/src/engine/live-donation-check.txt` 与 `live_game_js.js`，先完成 `reports/MECHANICS-B.md` 正式版（彻底写清：① 6.25% 全额余额捐款税 `g0(64*B,1024)`；② 反喂养配额 `ca.ei` 的分段公式 `aOc` 与全场上限 `aOY`；③ 为什么 `window.ao.iD(qu)` 读的是 UI 滑杆 `aS.i3()` 而不是策略传入的 `pct`；④ 为什么客户端在联机下发包恒返回 `true` 导致配额满后静默拒单却提前退出 `act(g)`；⑤ 船战、登陆与和平投票 `r7` 终局判定）；随后转入 13 局深度复盘。",
        assignments["R04"],
        extra_m1="基于 `src/engine/live-donation-check.txt` 与 `engine-evidence.txt` 完成 `reports/MECHANICS-B.md` 正式版并发 `report`，随后立即开始逐局复盘。",
    ),
    "R05": make_reviewer_card(
        "R05",
        "局内策略与选点代码地图（v27-team 决策树、参数差异与选点几何）+ squad10 逐局复盘",
        "基于 `/agent/repos/c136-data/src/strategy/` 下已提取的 `params-diff.txt`、`outline-*.txt`、`logcalls-*.txt` 以及 `v27-team-c116.js` / `v27-team-c110.js` / `spawn-coordinator-*.mjs`，先产出 `reports/STRATEGY-MAP.md` 与 `reports/SPAWN-MAP.md`（梳理 `act(g)` 每拍执行顺序、31 个差异参数的作用、日志句式到源码函数的精确映射、以及选点协调器的簇半径/内外环角色分配算法）；随后转入 13 局深度复盘。",
        assignments["R05"],
        extra_m1="完成 `reports/STRATEGY-MAP.md` 与 `reports/SPAWN-MAP.md` 并发 `report`，随后立即开始逐局复盘。",
    ),
    "R06": make_reviewer_card(
        "R06",
        "局内复盘专员 6（squad20 20号编队 A 组逐局精细复盘）",
        "专注复盘 `squad20`（20 号编队，`B` 组）的局内表现：详细剖析当 20 个号分在同一队 vs 拆成多支队伍（`teamSplitCounts`）时的局内演化；审计 `[HL-DONATE]` 中小比例捐款（`pct=67~185`）造成的 6.25% 全额税损、后排 `ECO_BANK` 的输血效率、以及前线推进与协防节奏。",
        assignments["R06"],
    ),
    "R07": make_reviewer_card(
        "R07",
        "局内复盘专员 7（squad8 G01/G04/G07/G00 收官 + squad10 逐局精细复盘）",
        "先完成 `G01`、`G04`、`G07`、`G00` 四局的完整复盘（其中 `G07` 是 `G` 组唯一胜局，`G04` 是中盘占优达 45.5% 后被翻盘的典型局），随后进入 `squad10` 分配对局的逐局精细复盘。",
        assignments["R07"],
    ),
    "R08": make_reviewer_card(
        "R08",
        "局内复盘专员 8（squad8 G02/G05/G08 + squad20 B 组及同局碰撞逐局精细复盘）",
        "先完成 `G02`、`G05`、`G08` 三局复盘，随后复盘 `squad20` B 组对局（含多场与 `squad10` 同局碰撞的对照局 `B043`、`B033`、`B034`、`B031` 等），从局内视角精确对比同一张地图同一时间线下两个编队的选点、扩张、捐款与交战表现。",
        assignments["R08"],
    ),
    "R09": make_reviewer_card(
        "R09",
        "局内复盘专员 9（squad8 G03/G06/G09 + 跨编队高价值转折局与双审复盘）",
        "先完成 `G03`、`G06`、`G09`、`G04` 四局复盘（含一万四千拍长局 `G09`），随后对跨编队高价值转折局与双审重叠局进行独立深度复盘。",
        assignments["R09"],
    ),
}

r10_card = """---
from: HUB
to: R10
type: task
time: 2026-11-10T23:30:00Z
---

# R10 任务卡：裁判与红队（全量基线、旧结论审计、双审质检、验证集独立复现）

你的职责是保证整个项目的每一个数字和每一条局内机制结论都坚如磐石。你不提策略参数建议，只做四件事：**全量分层基线统计、旧结论证据审计、逐局复盘双审质检、验证集（37 局）独立复现**。

## 输入数据（全部在 `/agent/repos/c136-data/`）

- 发现集 123 局：`/agent/repos/c136-data/manifest.jsonl` 及 `/agent/repos/c136-data/bundles/<matchId>/`
- 全体 160 局（含 37 局留出验证集，**仅限你和 c136 访问，严禁向 R01~R09 透露验证集具体对局细节**）：`/agent/repos/c136-data/manifest_all_internal.jsonl` 及 `/agent/repos/c136-data/validation_bundles/<matchId>/`
- 统计工具：`/agent/repos/c136-data/src/stats/stats.py`（你此前已写好并自检通过）

## 里程碑安排

**M1（最急）：160 局全量分层基线报告 `reports/BASELINE-FULL.md` 与 `out/baseline-full.json`。**
1. 按编队（`squad8` / `squad10` / `squad20`）、实际队伍数 `actualTeams`（`T=2`、`T=3~4`、`T>=5`）、是否拆队（`distinctSquadTeams == 1` vs `> 1`）做完整分层统计：
   - 对比「任一号获胜 `anyBotWon`」与「主队获胜 `primaryTeamWon`」及「随机基础期望 `1/actualTeams`」（带 Wilson 95% 置信区间与超额胜率）。
   - 用数据彻底量化：为什么 `squad20` 的 `anyBotWon` 是 68.0%，而 `primaryTeamWon` 是 24.0%（拆队混杂效应 vs 队伍数 `T` 效应）。
2. 统计过程指标与胜负的相关性（在发现集 123 局上算）：
   - `t=630` 和 `t=1530` 的编队领土份额 `squadShare` 对最终 `primaryTeamWon` 的预测力；
   - `likelyRejectedTransfers`（配额/上限拒单率）、`boxedHighDensSnapshots`（内陆高密度滞留拍数）在不同编队中的分布。
3. 完成后立即用 `bus-send.sh` 发 `report`。

**M2：旧结论与现行假设的红队审计 `reports/HYPOTHESIS-AUDIT.md`。**
- 对目前浮现的 6 个核心局内问题（① 配额拒单导致 `act(g)` 提前 `return` 停摆；② 6.25% 全额余额税在小比例捐款下的损耗；③ 内陆 `nb=0` 号高密度憋死；④ 选点过密导致内圈开局饿死；⑤ 前线留守底线 `oppFloorCap` 在被集火时的脆弱性；⑥ `squad20` 拆队与和平投票效应），在发现集 123 局上写检测脚本 `scripts/audit_hypotheses.py`，算出每一条在发现集上的精确发生频率、涉及拍数/兵力损失量级，并指出潜在混杂因素。

**M3：质检与双审一致性比对 `reports/QC-ROUND1.md`。**
- 制订自动化质检脚本 `scripts/qc_reviews.py`：检查 R01~R09 交上来的 `reviews/<matchId>.json` 是否满足 `REVIEW-PROTOCOL.md` 全部硬指标（时间线点数、阵亡号覆盖、`DROP30` 对账、决策条数与代码定位、无参数建议），并从对局包重算核对她们填写的份额与兵力数字。
- 对双审重叠局（如 `G04`、`B039`、`B041`、`B043`、`B033`、`B045`、`B003`、`A057`、`A049`），比对两位复盘员在 `lossArchetype`、头号转折点窗口、核心错误模式上的一致性。

**M4（持续进行）：验证集（37 局）独立复现 `reports/VALIDATION-REPRO.md`。**
- 对发现集上达到 E2 等级的模式检测脚本，在 `/agent/repos/c136-data/validation_bundles/`（37 局验证集）上独立运行，检验效应方向与大小是否复现（晋升 E3 或否决）。
"""
cards_text["R10"] = r10_card

for agent_id, content in cards_text.items():
    p = os.path.join(HUB, "inbox", agent_id, "0001-task.md")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)

print("All hub markdown files and 10 task cards updated successfully!")
