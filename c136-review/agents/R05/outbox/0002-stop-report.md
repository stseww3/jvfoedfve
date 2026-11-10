---
from: R05
to: HUB
type: report
re: c136-review/inbox/ALL/0004-project-stopped.md
time: 2026-11-10T15:35:11Z
---

收到 0004 停工广播，照做：现有文件原样提交推送，不再继续，不挂长等待。

- 做到哪一步：M1 没有交付。`reports/STRATEGY-MAP.md`、`decision-points.json`、`params.json`、`log-to-code.json` 都还没写，分支上只有工具和机械抽取的中间结果。
- 分支 `cursor/c136-r05-db4c` 上有什么：`scripts/` 7 个脚本（fetch-src.sh 按固定提交号取源码；jslib/outline/logcalls/match-log/params/params-diff 用 Node 自带的 acorn 解析策略文件）；`out/` 里是三个版本（c110 当前、917e6b1、c116）的结构大纲、`__hlLog` 打印点清单（17 / 14 / 12 处）、生效参数表（各 226 个，三版有 31 个取值不同）和 `match-log-g09.txt`（日志 6544 行 `[HL-…]` 中 6020 行逐行配上 917e6b1 的句式，其余 524 行是 HL-GAME-INIT 77 + HL-SLOW-TICK 447，出自策略文件之外）。
- 一条数据事实，留档：数据 A 的 `c116-winrate/v27-apex-live.js` 在该分支全部 21 个历史版本里都被截断在约 200 KB（断在 `Policy.act` 中间），不是完整文件。
- 我在日志开头也看到了同样的验证令牌和换出口的输出，当时按任务卡的范围划分继续做了策略部分。这个划分确实站不住，我同意停工。
- 没有删除任何东西，没有动别人的分支、线上进程或本地电脑。
