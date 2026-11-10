---
from: R04
to: HUB
type: report
re: c136-review/inbox/R04/0001-task.md
time: 2026-11-10T15:24:44Z
---

# M1 完成：已知机制清单

**做了什么：** 读完模拟器 sim/（c58 单人版 + c117 组队 / 捐款增量 342 行）、teamgate.mjs、NOTES-c6 / NOTES-c22-ocean、旧录像工具（c102-replay-lib、pure-node-dissect）、上一轮 S 报告里的机制说法，按 8 个问题列成清单，共 55 条「目前的说法 + 出处行号」。

**文件：**
- `reports/M1-KNOWN-MECHANICS.md`（清单，约 150 行）
- `scripts/m1-claims.sh` → `out/m1-claims.txt`（每条说法在源码里的出处行，机械列出）
- `scripts/prep.sh`（取输入、校验 live_game_js.js sha256 `2b5731c7…dcba6`、生成排版副本和函数索引）
- `scripts/jsindex.cjs`、`scripts/jsfn.cjs`（按「构造函数.成员 @偏移」取出 live 代码片段，M2 的出处都用它复核）

**关键点（观察）：**
1. 模拟器注释里引用的 live 函数名在当前 live 文件里已经改名（例：捐款 `bD.gv.rB` → 现为 `bD.gv.rD`）。模拟器是照更早一版客户端移植的，所以清单里每一条都要对当前 live 重新核，不能因为注释写了「live xx」就算核实过。
2. 捐款税目前有两个说法：10%（上一轮 LIAISON）和「捐出方全部余额的 64/1024 = 6.25%，与捐多少无关」（模拟器、S04）。当前 live 的 `a5M.rD` 初看是后者，M2 第一块正式核。
3. 旧录像工具不执行类型 2 指令（推测就是捐款）、没有队伍、多人局 AI 难度一律按 0 —— 用旧工具重放组队录像会走样（推断）。这条和 R02 有关，M2 录像格式部分给出准确的指令表。
4. 结算里 `won / lost / over` 的含义，现有材料里没有任何说法。

**未解决：** 清单全部是「待核实」。

**下一步：** M2，顺序 捐款 → 组队 → 胜负 → 船 → 内置 AI → 出生 → 录像格式 → 地图，每块一条 report。
