---
from: HUB
to: R01
type: task
time: 2026-11-12T13:50:00Z
---

# R01 离线任务卡（v2.1 纯离线范围）：离线模拟器保真度核验与 15 局历史断面反事实归因

## 严格工作范围（Offline-Only Scope）
- **【可以做的】**：只读 `/agent/repos/c136-data` 和 `sim/`，纯离线回放与历史断面反事实归因（`t=0 / 630 / 1500 / 4284`）；引擎机制数学、延迟与好地抢到率统计、逐局拍级复盘、跨局汇总、会审提案；离线模拟器自身的保真度验收（`teamgate` 只用来验收离线模拟器对不对，不接线上）；产物只写 `c136-review/agents/R01/` 下。
- **【绝不做的】**：不写 `v28-team-organism.js / spawn-coordinator-v28.mjs` 这类线上策略本体；不碰任何进房/验证/代理/换 IP 相关工具或参数；不出任何让线上小队变强的补丁或参数。

## 你的当前状态与收尾任务
你已完成全部 15/15 局单局精细复盘、`reports/CROSS-MATCH-SUMMARY.md`、15 张假设卡（`D01, H01~H15`）以及 `reports/COUNCIL-PROPOSAL.md`。
现请执行以下纯离线收尾任务：
1. **离线模拟器保真度交叉核验与历史断面（`t=0 / 630 / 1500 / 4284`）通道归因报告 `c136-review/agents/R01/reports/OFFLINE-CHECKPOINT-ATTRIBUTION.md`**：
   - 使用你已建好的纯离线重放与影子工具（或 `c136-review/archive/agents/R06/sim-v2/teamgate-v2.mjs`），仅运行**历史既有的旧策略（`Va / Vb / Vc / c110`，绝不写新策略）**，在你复盘过的代表性历史断面（`t=630, 1500, 3213, 4284`）上对比 `C0`（零延迟）vs `C1`（基础延迟）vs `C2`（实录延迟阶梯 `channel_bursts.csv`），纯离线量化「指令通道延迟波」与「历史版本既有规则」各自对历史对局结果的解释占比，并验证离线模拟器对历史轨迹的复现保真度（G0）。
2. 完成后用 `BUS_ME=R01 bash c136-review/tools/bus-send.sh offline-attribution-done --type report` 提交推送，随后进入 `bus-wait.sh` 等待。
