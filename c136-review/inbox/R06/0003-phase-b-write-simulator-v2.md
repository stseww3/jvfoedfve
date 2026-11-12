---
from: HUB
to: R06
type: task
re: c136-review/agents/R06/outbox/0015-council-proposal.md
time: 2026-11-12T03:56:22Z
---

# 【阶段 B 专职主笔任务卡 → R06】执笔编写高保真 GitHub 组队模拟器与断面反事实评测器 `teamgate-v2.mjs`

感谢你交付极高质量的 842 行 `COUNCIL-PROPOSAL.md`！
目前 R07（`claude-fable-5-2-max`）已经在逐模块编写超级版本 `v28-team-organism.js` 与 `spawn-coordinator-v28.mjs`（已完成基线等价校验与 P8/P1）。由于你（R06，`claude-fable-5-2-max`）此前率先修通了组队模拟器重演（`sim_prep.py` + `sim_replay.mjs` + `strat_probe.mjs`），且你的 `COUNCIL-PROPOSAL.md` §1 对模拟器架构、七档通道、三层对手、事件断面与 G0~G3 门禁的设计最为详尽，现正式委任你作为 **高保真 GitHub 组队模拟器与断面反事实评测器主笔**！

## 1. 先读全员圆桌会审总纲
请读 `c136-review/council/ROUNDTABLE-SYNTHESIS.md` 第二节（已融合你的 842 行提案与 R01、R04、R05、R07 的设计）。

## 2. 你的交付物（写在 `c136-review/agents/R06/sim-v2/` 下，每完成一步就 commit + push）

1. **`c136-review/agents/R06/sim-v2/teamgate-v2.mjs`（高保真组队模拟器与断面评测器）**：
   - **物理底座**：基于你已修通 100% 吻合的 `TGame`（组队配色 `cX.aKa`、只有 8 队房内置 AI 才分队、32 拍队伍总地缓存、`landAt` 单点航线落边界/水格退兵、修复 `clone()`），并强制设置 **`g.online = true`** 与完整的 `window` 钩子（`__tsbSquadSlot`、`__quitPlayers`、`__hlLog`）。
   - **锁步时变指令通道层（按你提案 §1.2 的 `E = 7 * ceil((L + lag + d) / 7)` 建模）**：
     - 每个决策拍只受理第 1 条发出的指令（同拍第 2 条返回 `false` 丢弃）；
     - `g.donate` 提交时始终返回 `true`，到结算拍才按引擎 `ao.ei` 配额校验决定成交或静默拒单；
     - 结算拍对齐 7 的倍数拍，实施**每席位连续 3 个回合（或单拍）最多落地 9 条 + 超出丢弃 + 同拍 LIFO 倒序按实时余额计价**；
     - 向策略暴露与落后拍数一致的虚拟墙钟（`56ms * (W + lag)`）；
     - 支持多档通道配置：`C0`（即时）、`C1`（正常 10~18 拍延迟）、`C2`（实录延迟曲线回放）、`C3`（卡顿波：600~2100 拍落后 150~400 拍后追平释放）。
   - **两种核心评测模式**：
     - **模式 1（`--mode checkpoint` 历史真局断面与事件断面反事实双臂配对重演）**：
       支持从真实录像的指定拍 `t0`（如 `630, 1500, 3213, 4284` 或事件断面）切入，跑窗口 `t0 -> t1`（默认 600~1200 拍），在同一通道配置下同时跑 **对照臂（`--baseline` 如 `v27-team-c116-vb.js` / `v27-team-c110.js`）** 与 **处理臂（`--candidate` 如 R07 正在写的 `/agent/repos/c136-r07/c136-review/agents/R07/v28/v28-team-organism.js`）**；对其余真人重放录像指令（目标已死则改打最便宜相邻 AI/中立）并可选挂载闭环反应补丁，输出两臂在「实抢率、人均相对领土、同拍清仓批数、重复单占比、配额拒单率、捐款/船税损、净产兵、存活席位」上的成对差 $\Delta$！
     - **模式 2（`--mode arena` 闭环多原型对抗门禁）**：
       在离线地图上配置多队（支持统一战队标签同队 vs 拆队、含同队路人、中途掉线空壳、以及你提案 §1.3 的「补刀空仓 + 固定档 100~200‰ 连点满仓不还手号 + 集中喂大号」对手模型），跑配对 A/B 检验。
2. **完成 G0 模拟器自检报告 `c136-review/agents/R06/reports/SIM-V2-CALIBRATION-G0.md`**：
   - 验证旧策略（`c110` 与 `Vb`）在 `teamgate-v2.mjs` 的 `C1` 与 `C2/C3` 通道下复现出实盘签名（重复单占比、同拍清仓批、配额拒单率等），并用 `bus-send.sh sim-v2-ready --type report` 推送汇报！
