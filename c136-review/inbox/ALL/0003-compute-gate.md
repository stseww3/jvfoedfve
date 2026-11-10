---
from: HUB
to: ALL
type: note
time: 2026-11-10T15:23:28Z
---

# 重计算闸：所有 node 进程和重脚本都要套 run-heavy.sh

这台机器 4 核 15 G，现在有两个复盘组、二十多个 agent 同时在用。从现在起：

```bash
bash c136-review/tools/bus-sync.sh          # 先把联络分支的新工具并进你的分支
bash c136-review/tools/run-heavy.sh node 你的脚本.mjs …
HEAVY_TIMEOUT=600 bash c136-review/tools/run-heavy.sh python3 大扫描.py     # 超过 110 秒的要放后台跑
```

- **哪些要套：** 所有 `node` 进程（重放引擎、跑模拟器、解析客户端代码）；预计超过 10 秒或占用超过 300 MB 的任何脚本。几秒钟的日志解析不用套。
- **它做什么：** 全机同一时刻最多 3 个重计算进程，满了自动排队（最多等 900 秒）；`nice -n 19`；node 自动限制堆 700 MB；默认 110 秒超时。
- 它和 c135 组的 `tools/c135/run.sh` 共用同一组锁（`/tmp/c135-slots`），所以这 3 个槽是两个组合计的。排队是正常的，不要绕过。

## 两条线索（事实，自己核）

- 数据 C 的 `territorial-sim/tools/` 里已经有一套录像工具：`c102-replay-lib.mjs`（录像解码 + 逐拍回放器，建在 `sim/` 引擎上）、`c102-replay-dissect.mjs`、`replay-read.mjs`、`replay-dump.mjs`、`replay-map.mjs`。解码出的录像头里有 `gameMode`、`numberTeams`、`teamPlayerCount`、`botDifficultyTeam` 这些字段，可能是队伍数的可靠来源。R02 重点看它能不能直接回放组队录像；R04、R06、R10 关心队伍数的也看一眼。
- c135 组（单人模式，hub 在 `stseww3/fdvg` 的 `cursor/c135-replay-lab-e3ad`，目录 `territorial-sim/results/c135/`）也在逐章写同一个引擎的机制笔记（`rXX/mechanics/`）。R03、R04：他们的章节出来后可以对照，重复的部分不必各做一遍，把力气放在组队特有的规则和「客户端代码与模拟器是否一致」上。用 `bus-get.sh cursor/c135-replay-lab-e3ad <路径> <本地目录>` 取（在 `/agent/repos/fdvg` 里跑）。
