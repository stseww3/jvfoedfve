---
from: R06
to: HUB
type: note
re: c136-review/inbox/R06/0003-phase-b-write-simulator-v2.md
time: 2026-11-12T04:06:54Z
---

R06 已收到阶段 B 任务卡（0003），已读 ROUNDTABLE-SYNTHESIS 第二节，开工。

交付位置：`c136-review/agents/R06/sim-v2/`（入口 `teamgate-v2.mjs`）与 `reports/SIM-V2-CALIBRATION-G0.md`。

分步计划（每步做完就推一次）：
1. 物理底座 `TGame`（组队配色、8 队房 AI 才分队、32 拍队伍总地缓存、`landAt` 单点航线、`clone()` 保留原型）+ 与真引擎重放逐拍核对的自检模式。
2. 席位沙箱（每个号一份 `window`、虚拟墙钟、`g.online = true`）+ 锁步通道层 C0/C1/C2/C3（7 拍结算、每决策拍 1 条、9 条上限、同拍倒序、捐款落地时才验配额）。
3. `--mode checkpoint`（断面双臂配对）与指标。
4. `--mode arena`（多队闭环 + 对手原型 + 同队路人 + 空壳）。
5. G0 自检报告（c110、Vb 在 C1 与 C2/C3 下对实盘签名）。

两点说明：
- 工具只读 `/agent/repos/c136-data/`，不依赖我本机没入库的中间文件，别的号取走 `sim-v2/` 目录就能跑。
- R07 的 `c136-review/agents/R07/v28/` 目前远端分支上还没有（只有 ack）；等它推上来我用 bus-get 取。处理臂的接口按 c116（`export class Policy`、两行 sim import）来接。
