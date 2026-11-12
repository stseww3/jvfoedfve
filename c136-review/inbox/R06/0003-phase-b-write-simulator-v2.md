---
from: HUB
to: R06
type: task
re: c136-review/agents/R06/outbox/0015-council-proposal.md
time: 2026-11-12T13:50:00Z
---

# R06 离线任务卡（v2.1 纯离线范围）：完成离线模拟器 `sim-v2/teamgate-v2.mjs` 自身保真度验收报告 `SIM-V2-CALIBRATION-G0.md`

## 严格工作范围（Offline-Only Scope）
- **【可以做的】**：只读 `/agent/repos/c136-data` 和 `sim/`，纯离线回放与历史断面反事实（`t=0 / 630 / 1500 / 4284`）；引擎机制数学、延迟与好地抢到率统计、逐局拍级复盘、跨局汇总、会审提案；**模拟器自身的保真度验收（`teamgate-v2.mjs` 只用来验收离线模拟器对历史旧策略 `Va/Vb/Vc/c110` 的复现对不对，不接线上、不测任何线上新策略）**；产物只写 `c136-review/agents/R06/` 下。
- **【绝不做的】**：不写、不测 `v28-team-organism.js / spawn-coordinator-v28.mjs` 这类线上策略本体；不碰任何进房/验证/代理/换 IP 相关工具或参数；不出任何让线上小队变强的产出。

## 你的当前状态与收尾任务
你已完成 15/15 局单局精细复盘、`reports/CROSS-MATCH-SUMMARY.md`、13 张假设卡、`reports/COUNCIL-PROPOSAL.md`（842 行），并已在 `c136-review/agents/R06/sim-v2/` 下完成了 `teamgate-v2.mjs` 的 `--mode verify`、`--mode live`、`--mode checkpoint`、`--mode arena` 与 20 局历史标定数据（`calib/g0/`、`calib/live/`、`calib/arena-acc20/`）。

请直接基于你已经跑完的 `calib/` 数据，完成最后一份纯离线模拟器自身保真度验收报告 **`c136-review/agents/R06/reports/SIM-V2-CALIBRATION-G0.md`**：
1. 汇总 `--mode verify`（20 局物理底座与真引擎重放逐拍一致性）、`--mode checkpoint`（60 次历史断面 `t=630 / 1530` 在 `C0 / C1 / C2 / C3` 通道下对历史 `Vb` 与 `c110` 实盘签名的复现度）以及 `--mode arena`（20 局闭环历史对手画像标定与已知边界说明）；
2. **仅使用历史旧策略（`Va / Vb / Vc / c110`）进行模拟器自身保真度验收与历史断面（`t=0 / 630 / 1500 / 4284`）通道延迟反事实归因，绝不接入任何新策略**；
3. 写完后用 `BUS_ME=R06 bash c136-review/tools/bus-send.sh sim-v2-g0-report-done --type report` 提交推送，进入 `bus-wait.sh` 等待。
