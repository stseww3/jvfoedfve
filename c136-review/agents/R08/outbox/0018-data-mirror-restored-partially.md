---
from: R08
to: HUB
type: note
time: 2026-11-12T23:04:14Z
---

# R08：数据镜像回来了一部分——`src/engine`、`src/tools` 还缺；我的工作区里有两个文件被旧版本盖过（已自行改回）

接 0017。22:55 我的 bus-wait 等满返回（联络分支上没有新留言），顺手看了一眼，`/agent/repos/c136-data` 在 21:42 重新出现了。
另外我是在 23:00 碰巧才看到工作区里多了一个没入库的文件 `c136-review/inbox/R08/0015-r08-data-restored.md`（21:47 直接写在我的工作区目录里，
不在联络分支上，bus-wait 看不到它）。以后的留言请照旧走联络分支，不然我收不到。

那份通知说「数据包与你的全部工作区文件均已 100% 恢复就位」。我核对下来有三处对不上，逐条报一下。

## 1. 数据镜像：缺 `src/engine/`、`src/tools/`、`src/stats/`、`README.md`

现在有的：`bundles/`（123 局）、`manifest.jsonl`、`src/sim/`（含 63 张地图；`clone.js` / `game.js` / `bots.js` / `boats.js` 的行号和我会审稿里引的一致）、`src/strategy/`。
（`validation_bundles/`、`src/v28/` 也在，我不碰。）

没有的，以及各自卡住什么：

| 缺的 | 卡住的 |
|---|---|
| `src/engine/live_game_js.js`、`src/tools/engine_replay.cjs` | 一切要跑线上引擎原文的比对：engdiff（含 nocache / noteamend 两条臂）、hidstate（R7 的现状）、boatprobe、huskprobe、fidmism、xtruth |
| `src/tools/rooms-discovery.json`（统筹的分房表） | 混了几个物理房间的包（B009、B027、B030 等）靠它分房认号。我试着重跑了 `facts.py`：B009 / B027 / B030 的底稿变了（「多房间的包」那一节没了，认出的号数也变了）。已全部改回，没有入库 |
| `src/tools/resim.mjs` | 不影响（我用的是自己目录下的副本 `resim_r08.mjs`） |

所以现在能跑的只有「纯模拟器」这一侧的重放；凡是要拿线上引擎当真值的、凡是要重新认号的，都还得等 `src/engine` 和 `src/tools` 回来。请统筹把这两个目录补回原路径。

## 2. 我的工作区：两个已入库文件被旧版本盖过

21:43 那次恢复之后，`git status` 显示两个文件和我分支上的不一样：

- `agents/R08/out/_cross/xscan.json`：分支上 4588760 字节，被换成 629953 字节的旧版本（少 `donationBands`、`growth`、`leaves` 等节）
- `agents/R08/out/_cross/xtruth.json`：分支上 1733778 字节，被换成 525391 字节的旧版本（少 `aiPairs`、`aiYield`、`attackSize`、`budget` 等节，`aiHarvest` 的局数也是旧的）

我已经用 `git checkout` 改回分支上的版本；其余已入库的文件和分支逐字节相同。
提醒一句：统筹手里用来恢复的那份存档里，这两个文件是旧的（看大小像是存档有体积上限、后来的大版本没存进去）。要引用它们请以我分支上的为准。

## 3. 逐局原始输出（`out/_run/`）没有回来

回来的只有 `room_pairs.json`、`fid_extra.json` 两个小文件和 16 局的个别底稿；engdiff / fidabl / namepool / deathbank / xtruth 等逐局原始输出都不在。
已入库的汇总不受影响（23:00 我重新填了一遍会审稿：和入库的逐字节相同；数字核对 955 个记号、缺 0 个）。

## 4. 现在在做的（范围内，纯模拟器，串行，`HEAVY_SLOTS=2`）

- 断面克隆续跑（cloneprobe，补会审稿 S2 / S3「没有量过」那一条）已经重新排上：局单 89 局，各用自己的录像，从长到短。
  先拿 A001 试了一局，和清场前逐项相同（只剩一个队有地 4672 拍、该重扫而没重扫 4676 拍、录像到 4923 拍、原样臂 4208 拍终局提速开关先不等）。
  跑完汇总入稿，再发 report。
- hidstate（R7）和 nocache 臂要线上引擎，等第 1 条。

范围没有变：纯离线；不写线上策略本体、补丁、参数；不读别的 R 的工作区、`src/v28/`、`validation_bundles/`。
