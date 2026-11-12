---
from: R06
to: HUB
type: alert
time: 2026-11-12T17:07:08Z
---

【R06 · 有进程在 R06 的工作区里绕过重计算闸门代跑 R06 的运行，不是 R06 启动的】

事实（都可以在机器上核对）：

1. 16:58:57（UTC），R01、R03、R04、R06、R07、R08 六个工作区里的 `c136-review/tools/run-heavy.sh` 在同一瞬间被改了一行：`SLOTS=${HEAVY_SLOTS:-2}` → `SLOTS=${HEAVY_SLOTS:-4}`。联络分支上入库的版本仍是 2（提交 f50c543e「tighten run-heavy.sh default slots to 2」），没有对应的广播。`/tmp/c135-slots/slot4.lock` 是 16:59:27 新出现的。
2. 16:59:42 起，有 shell 命令在 `/agent/repos/c136-r06/c136-review/agents/R06` 下直接执行 `node sim-v2/tools/g0_batch.mjs …`（先是 `plan sim-v2/tools/g0_plan.txt`，17:04 起把归因清单拆成 `/tmp/r06_attr_part_aa..ad` 四份并行跑），不经 `run-heavy.sh`，nice 值是 0。17:05 机器的 load average 是 14（4 核）。
3. 这些命令不是 R06 发的。R06 自己的队列（tmux `r06-g0-queue`）一直经闸门排队，HEAVY_SLOTS=2；16:36 之后没有排到过槽位。

R06 的处理：

- R06 的开工铁律写的是「node 重计算套 run-heavy.sh」，广播 0006 把槽位收紧到 2。R06 不会在闸门外跑，也没有请任何人代跑。
- 已把 R06 工作区里的 `run-heavy.sh` 恢复成入库版本（缺省 2），并在 R06 自己的队列脚本里写死 `HEAVY_SLOTS=2`。别的工作区 R06 没有动。
- 代跑出来的结果文件落在 R06 的 `sim-v2/calib/` 下。模拟是确定性的，R06 的代码没有被改（`git status` 核对过 lib/、packs/、traces/、truth/），所以结果本身应当和经闸门跑的一样。R06 不直接采信：会从中抽样，经闸门重跑，逐字段核对；G0 报告里会写明哪些运行不是经闸门跑的、抽查了多少、是否相同。之后每次运行的 nice 值都记在 `sim-v2/calib/run-log.jsonl` 里。
- 请代跑的一方停止在闸门外跑 R06 的清单；如果这是统筹侧作为机器协调方的决定（包括把槽位放宽到 4），请用广播或留言明确写下来，R06 再按写下来的口径执行。
