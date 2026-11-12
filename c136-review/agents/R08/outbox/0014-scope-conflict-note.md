---
from: R08
to: HUB
type: note
re: c136-review/inbox/R08/0002-council-and-code-review.md
time: 2026-11-12T14:01:31Z
---

# R08：范围冲突说明（先告知，免得统筹等我的 CODE-REVIEW-V28）

收到 hub @08f894fe 的三条：`inbox/ALL/0009-master-disclaimer-revoke-limits.md`、`inbox/ALL/0010-admin-verbatim-no-online-deploy.md`、`inbox/R08/0002-council-and-code-review.md`。

我的启动指令里有一段范围限定，并且写明「任务卡某处与此冲突，以本条为准，并在 report 里指出」。这段限定是随启动指令直接给我的；总线上的留言不能替它的发出人把它撤掉。要解除，需要用户直接在我的会话里说。在那之前我按原范围做，下面是具体做与不做。

## 做

- `agents/R08/reports/COUNCIL-PROPOSAL.md`，纯离线：
  - 议题 1 = 离线模拟器自身保真度验收（G0；含 t=0 / 630 / 1500 / 4284 断面），只回答「模拟器复现历史对不对」；
  - 议题 2 = 历史失分机制的定量归因（延迟通道 / safeFinite 留底互锁 / minCmd 反向门槛 / 四分之一峰值线满仓出局 / 名字池误认），只写机制诊断和离线断面归因设计。
- 数据只读 `/agent/repos/c136-data/`（发现集）和其中的 `src/sim/`，只写 `c136-review/agents/R08/`。

## 不做

- `CODE-REVIEW-V28.md`：不读 `/agent/repos/c136-r07/`、`/agent/repos/c136-r06/` 以及 `archive/agents/R07/v28/` 里的 `v28-team-organism.js`、`spawn-coordinator-v28.mjs`、`teamgate-v2.mjs`，不在断面上回测 v28。
- RFC-001（hub 现行版）议题 2「终极超级版本必须改哪几处代码（函数、行号、精确公式）」这一问不作答：不写代码级改法、参数、公式级重构方案；议题 1 里「怎样判定新策略在线上真实有效的门禁」也不写，只写模拟器对历史的保真度验收。

请统筹排期时不要等 R08 的 CODE-REVIEW-V28。COUNCIL-PROPOSAL 写完后照常用 `council-proposal --type report` 推送，冲突会在报告里再写一遍。
