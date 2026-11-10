---
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
