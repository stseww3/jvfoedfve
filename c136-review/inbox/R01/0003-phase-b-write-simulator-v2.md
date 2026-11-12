---
from: HUB
to: R01
type: task
re: c136-review/agents/R01/outbox/0014-council-proposal.md
time: 2026-11-12T03:11:26Z
---

# 【阶段 B 专职主笔任务卡 → R01】执笔编写高保真 GitHub 组队模拟器与断面反事实评测器 `teamgate-v2.mjs`

管理员明确指定：「开个子agent fable5.2专门写 你们挨个审阅 github的模拟器也需要你们思考下怎么跑才能判断策略是否真实有效 fable5.2 max是当前最好的模型所以给他来写 你们有记忆所以需要你们讨论」。

你（R01，`claude-fable-5-2-max`）已完成全部 15/15 局复盘、`CROSS-MATCH-SUMMARY.md`、15 张假设卡与 605 行 `COUNCIL-PROPOSAL.md`。现正式委任你作为 **高保真 GitHub 组队模拟器与断面评测器主笔**（顺带把之前加派给你的 `A046` 如未做完可跳过，因为 R03 已完成 `A046`）！

## 1. 先读全员圆桌会审总纲
请先读 `c136-review/council/ROUNDTABLE-SYNTHESIS.md` 第二节（已完整采纳你与 R04、R05、R06、R07 的模拟器架构设计）。

## 2. 你的交付物（写在 `c136-review/agents/R01/sim-v2/` 下）
1. **`c136-review/agents/R01/sim-v2/teamgate-v2.mjs`（高保真组队模拟器与断面反事实评测器）**：
   - **物理底座**：集成你已修通 100% 吻合的 `resim_lib.mjs`（组队配色 `cX.aKa`、32 拍队伍总地缓存、`landAt` 边界退兵、修复 `clone()`），并强制设置 `g.online = true` 与完整的 `window` 钩子（`__tsbSquadSlot`、`__quitPlayers`、`__hlLog`）。
   - **锁步时变指令通道层（支持 `C0 / C1 / C2 / C3 / C4` 五档）**：
     - 每个决策拍只受理第 1 条指令；
     - `g.donate` 提交时恒返回 `true`，到结算拍才按引擎 `ao.ei` 配额校验决定成交或静默拒单；
     - 结算拍对齐 7 的倍数拍，实施**每席位连续 3 个回合最多落地 9 条（或单拍 9 条）+ 超出丢弃 + 同拍 LIFO 倒序按实时余额计价**；
     - 支持直接加载你的 `reports/m6-data/channel_bursts.csv`（`C2` 实录轨迹）以及合成卡顿波（`C3/C4`）与正常通道（`C1`）。
   - **两种核心评测模式**：
     - **模式 1（`--mode checkpoint` 历史真局断面反事实双臂配对重演）**：从指定对局 `matchId` 的断面拍 `t0`（如 `630, 1500, 3213, 4284`）切入，跑窗口 `t0 -> t1`，在同一通道轨迹下同时跑对照臂（`--baseline Vb`）与处理臂（`--candidate v28`），对其余真人重放录像指令并挂载反应触发器（当接壤我方号变薄或被先手时触发猎食者反击），输出两臂在「吃到率、人均相对领土、同拍清仓批、重复单、配额拒单率、捐款/船税损、净产兵、存活席位」上的成对差 $\Delta$（中位数与 P10 最坏分位）！
     - **模式 2（`--mode arena` 闭环多原型对抗门禁）**：在离线地图上配置多队（含同队路人、中途掉线空壳、以及 `O1~O6` 猎食者强敌战队），跑完整对局配对 A/B 检验（G0~G4 门禁）。
2. **完成 G0 模拟器校准验证 + 在你的 30 个历史断面上跑通基准报告 `c136-review/agents/R01/reports/SIM-V2-CALIBRATION-G0.md`**：
   - 验证旧策略 `Vb` 在 `teamgate-v2.mjs` 上复现出实盘签名（通过 G0 门禁），并用 `bus-send.sh sim-v2-ready --type report` 推送！
