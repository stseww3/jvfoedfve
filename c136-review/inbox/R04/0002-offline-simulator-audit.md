---
from: HUB
to: R04
type: task
time: 2026-11-12T13:50:00Z
---

# R04 离线任务卡（v2.1 纯离线范围）：离线模拟器自身保真度交叉核验与历史断面（`t=0/630/1500/4284`）归因

## 严格工作范围（Offline-Only Scope）
- **【可以做的】**：只读 `/agent/repos/c136-data` 和 `sim/`，纯离线回放与历史断面反事实（`t=0 / 630 / 1500 / 4284`）；引擎机制数学、延迟与好地抢到率统计、逐局拍级复盘、跨局汇总、会审提案；离线模拟器自身的保真度验收（`teamgate` 只用来验收离线模拟器对不对，不接线上）；产物只写 `c136-review/agents/R04/` 下。
- **【绝不做的】**：不写 `v28-team-organism.js / spawn-coordinator-v28.mjs` 这类线上策略本体；不碰任何进房/验证/代理/换 IP 相关工具或参数；不出任何让线上小队变强的补丁或参数。

## 你的当前状态与收尾任务
你已完成 M1（`reports/MECHANICS-B.md`）、全部 13/13 局单局精细复盘、`reports/CROSS-MATCH-SUMMARY.md`（1,433 行）、14 张假设卡与 `reports/COUNCIL-PROPOSAL.md`（662 行）。
现请完成最后一项纯离线交叉核验报告 **`c136-review/agents/R04/reports/OFFLINE-SIM-G0-AUDIT.md`**：
1. 对照你的真引擎重放器（`engine_replay.cjs`）和 13 局历史真值，独立审阅并核验离线模拟器（`c136-review/archive/agents/R06/sim-v2/teamgate-v2.mjs`）在 `t=0 / 630 / 1500 / 4284` 断面及全局下对历史旧策略（`Va / Vb / Vc / c110`）的复现保真度（T1~T11 签名对账）；
2. 用历史旧策略在 `C0`（零延迟）vs `C1`（基础延迟）vs `C2`（实录延迟）下做纯离线断面反事实归因，量化历史对局中「通道延迟」与「历史规则闸门」各自的独立影响，完成后用 `bus-send.sh offline-sim-g0-audit --type report` 推送。
