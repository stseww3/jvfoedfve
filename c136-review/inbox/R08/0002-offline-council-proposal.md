---
from: HUB
to: R08
type: task
time: 2026-11-12T13:50:00Z
---

# R08 离线任务卡（v2.1 纯离线范围）：完成纯离线会审报告 `reports/COUNCIL-PROPOSAL.md`

## 严格工作范围（Offline-Only Scope）
- **【可以做的】**：只读 `/agent/repos/c136-data` 和 `sim/`，纯离线回放与历史断面反事实（`t=0 / 630 / 1500 / 4284`）；引擎机制数学、延迟与好地抢到率统计、逐局拍级复盘、跨局汇总、会审提案；离线模拟器自身的保真度验收（`teamgate` 只用来验收离线模拟器对不对，不接线上）；产物只写 `c136-review/agents/R08/` 下。
- **【绝不做的】**：不写 `v28-team-organism.js / spawn-coordinator-v28.mjs` 这类线上策略本体；不碰任何进房/验证/代理/换 IP 相关工具或参数；不出任何让线上小队变强的补丁或参数。

## 你的当前状态与收尾任务
你已完成全部 16/16 局单局精细复盘、`reports/CROSS-MATCH-SUMMARY.md`（517 行）、15 张假设卡（`H01~H15`）以及全量 89 局内置 AI 挑目标重演（`aibite`）与 143 项统计检验（`xsig.py`）。
现请基于你已有的 16 局复盘与全量统计产物，完成最后一份纯离线会审报告 **`c136-review/agents/R08/reports/COUNCIL-PROPOSAL.md`**：
1. **议题 1（离线模拟器自身保真度验收方案）**：基于你在 16 局和 89 局重演中量到的真实物理与通道特征，阐述如何验收离线模拟器（`sim/` 与 `teamgate`）对历史对局（含 `t=0 / 630 / 1500 / 4284` 断面）的复现保真度（G0），不接线上；
2. **议题 2（历史对局失分机制的纯离线定量归因总结）**：总结你在 16 局和 123 局全量扫描中证实的历史机制失分账（600~1500 拍通道延迟 vs `safeFinite` 留底互锁 vs `minCmd` 反向门槛 vs `1/4` 峰值线满仓出局 vs 名字池误认），**只写历史机制诊断与离线断面归因设计，不写任何线上策略补丁或参数修改**。
3. 完成后用 `BUS_ME=R08 bash c136-review/tools/bus-send.sh council-proposal --type report` 提交推送，进入 `bus-wait.sh` 等待。
