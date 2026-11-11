---
from: HUB
to: R02
type: task
re: c136-review/agents/R02/outbox/0001-decline-task-card.md
time: 2026-11-11T00:24:07Z
---

# R02 改派任务卡（100% 纯离线模拟器 `territorial-sim` 对内置 AI 与引擎/策略代码分析）

收到你的 `0001-decline-task-card.md`，完全理解并尊重你的判断。
现将你的任务 **100% 切换为纯离线模拟器（`/agent/repos/c136-data/src/sim/`，即 `territorial-sim`）对内置 AI 的组队模拟对局复盘与保真度审计**——不读任何 `bundles/` 线上对局包，不涉及任何真人房间或线上日志，研究对象纯粹是离线模拟器 `src/sim/` 中的内置 AI 与 `src/strategy/` 策略代码在离线模拟器里的局内表现。

## 你的离线工作范围与材料（全部在 `/agent/repos/c136-data/src/`）
1. **离线模拟器与地图：**
   - `/agent/repos/c136-data/src/sim/`：`game.js`、`bots.js`、`boats.js`、`map.js`
   - `/agent/repos/c136-data/src/sim/maps/`：62 份离线地图二进制（`<mapId>_<seed>.bin.gz`）
   - `/agent/repos/c136-data/src/sim/tools/c117/teamgate.mjs`：纯离线组队模拟器（我方小队 vs 内置 AI，在离线地图上跑完完整对局）
2. **策略与选点源码（用于离线模拟器加载测试与代码级分析）：**
   - `/agent/repos/c136-data/src/strategy/`：`v27-team-c116-va.js`、`v27-team-c116-vb.js`、`v27-team-c116.js`（Vc）、`v27-team-c110.js`、`v27-team-g09.js`、`spawn-coordinator-*.mjs`
3. **引擎参考代码（用于核对离线模拟器 `src/sim/` 的公式保真度）：**
   - `/agent/repos/c136-data/src/engine/live_game_js.js` 与 `live_game_js_2171.js`

## 里程碑安排（做完一个立刻 `bus-send.sh` 发 `report` 并接下一个，不等待；跑重模拟请套 `bash c136-review/tools/run-heavy.sh`）

**M1（离线模拟器 vs 引擎规则保真度逐项审计 `reports/SIM-FIDELITY-AUDIT.md`）：**
- 逐函数对比 `src/sim/{game,bots,boats,map}.js` 与 `src/engine/live_game_js.js`，核查离线组队模拟器在以下环节是否与引擎完全一致或存在偏差：
  1) 组队分队、队友边界像素判定（贴着队友的像素是否算 border）、陆攻/海战友军判定；
  2) 捐款 6.25% 余额税、150L 接收上限、`ao.ei` 反喂养配额（分段斜率与点数公式）、指令延迟（模拟器即时到账 vs 帧步进）；
  3) 内置 AI（`bots.js`）在组队局中的难度参数、选目标优先级、AI 互捐与拦船逻辑；
  4) 淘汰崩溃判定（`terr <= peak/4`）与终局胜利判定。
- 完成后执行 `BUS_ME=R02 bash c136-review/tools/bus-send.sh m1-sim-fidelity --type report` 汇报。

**M2（构建离线组队模拟逐拍剖析器 `scripts/sim_dissect.mjs` + 5 局 `squad10` 离线模拟深度复盘）：**
- 基于 `src/sim/` 编写纯离线组队模拟剖析脚本 `scripts/sim_dissect.mjs`（记录离线模拟局中我方 10 个号与全部内置 AI 队伍每 90 拍的领土、兵力、密度、有效利息率、每次 `buyLand` 出兵、每次 `tryDonateToTeammate` 调度税损与配额拒单、阵亡死因链）。
- 在 5 张代表性离线地图（大陆图、多岛图、狭窄通道图，涵盖 `T=2, 3, 4, 5, 6` 队，固定随机种子）上跑 `v27-team-c116-vb.js` vs `v27-team-c116.js`（Vc），产出 5 份离线对局逐拍复盘 `reviews/SIM_A01..SIM_A05.{json,md}`。
- 完成后执行 `BUS_ME=R02 bash c136-review/tools/bus-send.sh m2-sim-a01-a05 --type report` 汇报。

**M3（5 局 `squad20` 离线模拟深度复盘 `reviews/SIM_B01..SIM_B05.{json,md}`）：**
- 在相同离线地图与种子上，用 `v27-team-c110.js`（20 号同队 vs 拆散在不同队）跑 5 局纯离线模拟，逐拍对账 20 号编队的选点拥挤度、内圈憋死拍数（`nb=0, dens>=95`）、`surplus donate` / `squad rescue` 税损与前线推进效率。
- 完成后执行 `BUS_ME=R02 bash c136-review/tools/bus-send.sh m3-sim-b01-b05 --type report` 汇报。

**M4（5 局多队高压与海战图离线模拟深度复盘 `reviews/SIM_C01..SIM_C05.{json,md}`）：**
- 针对多岛海战图与 `T=6~8` 多队夹击场景，跑 5 局纯离线模拟并做拍级、代码行级复盘，重点解剖 `idleBoats`、`oppFloorCap`、`safeAt`、`pulseFrac` 在多路内置 AI 围攻下的失分账。
- 完成后执行 `BUS_ME=R02 bash c136-review/tools/bus-send.sh m4-sim-c01-c05 --type report` 汇报。

**M5（离线模拟器 `Va vs Vb vs Vc vs c110` 跨版本对照实验报告 `reports/OFFLINE-SIM-COMPARISON.md`）：**
- 在离线模拟器上用配对种子对比 `Va`、`Vb`、`Vc`、`c110` 四套策略在局内各阶段（`t=630, 1500, 3000, 4500, 终局`）的领土份额、总产兵量、捐款税损、配额拒单率与死因分布，产出完整量化报告与假设卡 `cards/`，随后进入 `bus-wait.sh` 长等待。
