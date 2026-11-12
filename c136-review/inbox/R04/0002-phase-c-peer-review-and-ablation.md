---
from: HUB
to: R04
type: task
time: 2026-11-12T13:52:00Z
---

# 【阶段 C 逐行审阅与断面消融任务卡 → R04】审阅 `v28-team-organism.js` 与 `teamgate-v2.mjs` 并在你的 13 局真局断面上回测

感谢你完成全部 13/13 局复盘、1,433 行 `CROSS-MATCH-SUMMARY.md`、14 张假设卡与 662 行 `COUNCIL-PROPOSAL.md`！
现在按管理员指令（「开个子agent fable5.2专门写 你们挨个审阅 github的模拟器也需要你们思考下怎么跑才能判断策略是否真实有效」）：
1. **R06** 已在 `/agent/repos/c136-r06/c136-review/agents/R06/sim-v2/` 下完成了高保真组队模拟器 `teamgate-v2.mjs`（含 `--mode verify / live / checkpoint / arena` 与 20 局标定）；
2. **R07** 正在 `/agent/repos/c136-r07/c136-review/agents/R07/v28/` 下编写超级版本 `v28-team-organism.js` 与 `spawn-coordinator-v28.mjs`（已完成 P8 崩溃守卫、P1 在途账本、P3 AI/空壳底线解耦，正写 P4~P7 与 P2）。

请你（R04）：
1. **逐行审阅 `/agent/repos/c136-r06/c136-review/agents/R06/sim-v2/` 与 `/agent/repos/c136-r07/c136-review/agents/R07/v28/v28-team-organism.js`**，对照你的 `COUNCIL-PROPOSAL.md` 8 大项与防坑护栏，检查是否存在边界漏洞、销账死锁或新副作用；
2. **用你的真引擎断面与影子工具（或 `teamgate-v2.mjs --mode checkpoint`），把 `v28-team-organism.js` 挂到你复盘过的 13 局关键断面（如 `A013, A022, A029, A038, A047, A078, A081, A083, A086, A099, B034`）上跑对照回测**，出具审阅与实测报告 **`c136-review/agents/R04/reports/CODE-REVIEW-V28.md`**，并用 `bus-send.sh code-review-v28 --type report` 推送！
