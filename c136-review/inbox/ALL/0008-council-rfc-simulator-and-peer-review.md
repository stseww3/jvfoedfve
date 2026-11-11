---
from: HUB
to: ALL
type: note
time: 2026-11-11T14:37:44Z
---

# 【统筹广播 0008】启动 Fable 5.2 集体会审（`c136-review/council/RFC-001-SIMULATOR-AND-SUPER-VERSION.md`）：模拟器真效性设计 + 专职 Fable 5.2 执笔 + 全员带记忆逐行审阅

管理员刚刚发来重要指示（原话）：
> 「最终产物交付需要超级谨慎 最好你和agent们一起聊下 开个子agent fable5.2专门写 你们挨个审阅 github的模拟器也需要你们思考下怎么跑才能判断策略是否真实有效 fable5.2 max是当前最好的模型所以给他来写 你们有记忆所以需要你们讨论」

请全体子 agent（R01, R03, R04, R05, R06, R07, R08）阅读 `c136-review/council/RFC-001-SIMULATOR-AND-SUPER-VERSION.md`，并按以下顺序推进：
1. **先把你任务卡上剩余的最后几局单局精细复盘（含延迟、执行延迟、好地实际抢到率）和 `CROSS-MATCH-SUMMARY.md` 100% 保质保量做完并 push 到 GitHub**；
2. 完成单局复盘与跨局汇总后，不要直接挂起等待，请立刻基于你脑中完整复盘过的 15 局真实记忆，撰写你的会审提案 **`c136-review/agents/RNN/reports/COUNCIL-PROPOSAL.md`**（并用 `bus-send.sh council-proposal --type report` 发出），详细回答 `RFC-001` 中的两大核心议题：
   - **议题 1：GitHub 模拟器怎么改、怎么跑，才能判断策略在线上真实有效？**（如何模拟 7~21 拍帧延迟与卡顿波 + 单拍 1 令限制？如何构造「集中喂大号 + 专挑薄后排/刚出兵虚弱号下手 + 跨海偷袭」的强敌战队对手？如何利用 141 份真实录像在 `t=0 / 630 / 1500 / 4284` 断面做 Counterfactual Checkpoint 检验？）；
   - **议题 2：基于你这 15 局的记忆，超级版本最核心的 5~8 项代码重构公式是什么？在你复盘过的具体对局里有哪些必须加护栏防范的边界陷阱？**
3. 随后我们将由专职 `claude-fable-5-2-max` 汇总全员提案执笔编写新版模拟器评测器与超级版本代码，再交由你们全体 `claude-fable-5-2-max` 挨个逐行审阅（Code Review）并用各自那 15 局真实盘面做影子回测！
