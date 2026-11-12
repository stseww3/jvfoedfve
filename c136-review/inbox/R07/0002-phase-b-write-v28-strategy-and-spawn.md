---
from: HUB
to: R07
type: task
re: c136-review/agents/R07/outbox/0014-council-proposal.md
time: 2026-11-12T03:11:25Z
---

# 【阶段 B 专职主笔任务卡 → R07】执笔编写超级版本 `v28-team-organism.js` 与 `spawn-coordinator-v28.mjs`

管理员明确指定：「开个子agent fable5.2专门写 你们挨个审阅 github的模拟器也需要你们思考下怎么跑才能判断策略是否真实有效 fable5.2 max是当前最好的模型所以给他来写 你们有记忆所以需要你们讨论」。

你（R07，`claude-fable-5-2-max`）已完成全部 15/15 局复盘、`CROSS-MATCH-SUMMARY.md`、12 张假设卡与 705 行 `COUNCIL-PROPOSAL.md`。现正式委任你作为 **超级版本策略与选点协调器主笔**！

## 1. 先读全员圆桌会审总纲
请先读 `c136-review/council/ROUNDTABLE-SYNTHESIS.md`（已合并你与 R01、R04、R05、R06 共 5 份 `COUNCIL-PROPOSAL.md` 2,952 行提案的全部设计公式与防坑护栏）。

## 2. 你的交付物（写在 `c136-review/agents/R07/v28/` 下）
1. **`c136-review/agents/R07/v28/v28-team-organism.js`**：
   - 基于 `/agent/repos/c136-data/src/strategy/v27-team-c116.js`（Vc），完整实现 `ROUNDTABLE-SYNTHESIS.md` 第三节的 **模块 P1、P3、P4、P5、P6、P7、P8**：
     - **P1（全链路在途指令账本 `F` + 防清仓连乘约束 + 单拍 1 令优先级仲裁 + 紧急反击豁免 + 显式首击斩杀额度 + `isNoFullSend` 精确修复）**；
     - **P3（`threatOf` 过滤同队/同编队/空壳 + `safeFinite` 按 AI 自身兵力封顶 + 吃 0 兵残部/空壳/残余 AI 的 `dpKeep` 局部解耦与 `minCmd` 修正）**；
     - **P4（多号接壤联合合击报价折算 + 孤岛 `terr - collapseLine` 分母修正 + 窄接触面 `<25` 格出兵量裁剪）**；
     - **P5（受控 `over` 放行：严禁对存兵 $\ge 1.8\times$ 且未打我的强敌跳过价格门硬冲 + 解锁 `soleBuffer 128` 与调度 `108` 的逆序死锁）**；
     - **P6（内置 1:1 引擎 `ao.ei` 配额账本 + 扣除 `142*L` 硬上限余量与全队在途捐款裁剪 `pct` + 单笔捐足摊薄 6.25% 税 + 沿海被围号留底提高至 `82L/65L` + 360 拍防乒乓回流锁 + 废除负收益 `yield_opt` + `isDoomedPocket` 改按防守缺口是否可救判定）**；
     - **P7（海战航程衰减 $\eta=(127/128)^{T/5}$ 过滤 + 最小载兵 $\ge 3.5\times$ 船税门槛 + 被围 240 拍短程破围船密度门降到 88 + 落点非队友预检 + 60 拍同岛去重锁）**；
     - **P8（自身 `peak/4` 淘汰线保命预警与反击 + 顶层异常隔离 + 认队友优先按 `g.teams` 与当局名册并排除 `state===2` 空壳）**。
   - **重要工程要求**：将 P1~P8 设计为可通过 `PARAMS` 开关（如 `enableInflightLedger: 1, enableAiFloorCap: 1, enableCoordinatedStrike: 1, enableSmartOverCap: 1, enableQuotaExactDonate: 1, enableSeaPrecision: 1, enableCollapseGuard: 1`）独立启停的模块化结构，方便做单因子消融与全开测试！
2. **`c136-review/agents/R07/v28/spawn-coordinator-v28.mjs`**：
   - 基于 `/agent/repos/c136-data/src/strategy/spawn-coordinator-c116.mjs`，完整实现 **模块 P2**：
     - 房间按已落点真人名单哈希隔离 `matchKey`，只为实际在场席位排阵；
     - 队友目标间距拉宽至公平间距量级（$1.45 \sim 1.85 \times r_{\text{Cell}}$，取消 68px 死上限），内圈蓄水池最多 1 个，其余全员外弧；
     - 方案评分直接最大化我方 $K$ 点 Voronoi 陆地总面积，并对每个点施加与已落点敌人的硬性最小净空约束；
     - 废除空盘 `t=-42` 锁角，改为开局前最后 8 步定稿冻结（除非被新落子敌人贴脸入侵才单点微调），配合客户端每步限 1 令 + 真实位置闭环确认重发。
3. **初步自测报告 `c136-review/agents/R07/reports/V28-AUTHOR-NOTES.md`**：
   - 用你现有的影子探针与重放工具，在你复盘过的典型断面（如 `A033, A061, A070, A082, A089, A091`）上跑一遍 `v28-team-organism.js`，验证 0 语法/运行错误且各项新机制按预期触发，然后用 `bus-send.sh v28-draft-ready --type report` 推送，交由全体 Fable 5.2 挨个逐行审阅！
