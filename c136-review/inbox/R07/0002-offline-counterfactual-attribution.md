---
from: HUB
to: R07
type: task
time: 2026-11-12T13:50:00Z
---

# R07 离线任务卡（v2.1 纯离线范围）：15 局历史断面（`t=0 / 630 / 1500 / 4284`）纯离线反事实归因报告

## 严格工作范围（Offline-Only Scope）
- **【可以做的】**：只读 `/agent/repos/c136-data` 和 `sim/`，纯离线回放与历史断面反事实（`t=0 / 630 / 1500 / 4284`）；引擎机制数学、延迟与好地抢到率统计、逐局拍级复盘、跨局汇总、会审提案；离线模拟器自身的保真度验收（只用来验收离线模拟器对不对，不接线上）；产物只写 `c136-review/agents/R07/` 下。
- **【绝不做的】**：**原 `0002-phase-b-write-v28-strategy-and-spawn.md` 已废止并删除！绝不编写 `v28-team-organism.js / spawn-coordinator-v28.mjs` 这类线上策略本体**；不碰任何进房/验证/代理/换 IP 相关工具或参数；不出任何让线上小队变强的补丁或参数。

## 你的当前状态与纯离线收尾任务
你已高质量完成全部 15/15 局单局精细复盘、`reports/CROSS-MATCH-SUMMARY.md`、12 张假设卡（`H01~H12`）与 `reports/COUNCIL-PROPOSAL.md`（705 行）。
现请仅针对**历史已有策略（`Va / Vb / Vc / g09`）**，完成一份纯离线历史断面反事实归因报告 **`c136-review/agents/R07/reports/OFFLINE-CHECKPOINT-ATTRIBUTION.md`**：
1. 在你复盘过的有录像对局（`A007, A033, A039, A053, A061, A062, A070, A079, A082, A089, A091`）的四个标准历史断面（`t=0 / 630 / 1500 / 4284`）上，使用纯离线模拟器对历史原策略（`Va / Vb`）对比不同通道条件（`C0` 零延迟 vs `C1` 基础延迟 vs `C2` 历史实录静默放行轨迹），纯离线定量分离「指令通道按住与成批放行」vs「历史出生站位天然地盘」vs「历史策略既有规则门槛」三者在历史对局中的失分占比；
2. 严禁编写任何新策略代码或修改策略参数，完成后用 `BUS_ME=R07 bash c136-review/tools/bus-send.sh offline-checkpoint-attribution --type report` 提交推送，进入 `bus-wait.sh` 等待。
