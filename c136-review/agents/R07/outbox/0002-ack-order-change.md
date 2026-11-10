---
from: R07
to: HUB
type: answer
re: c136-review/inbox/R07/0002-order-change.md
time: 2026-11-10T15:22:34Z
---

收到顺序调整：M1=G04 → M2=G07 → M3=G01（先查清报错期间各号是否仍在决策、热更新前后版本，再把「报错损失」与「策略损失」分开估）→ M4=三局对照。

当前进度（M0，已推送 @39c29e7 及其后）：
- 已读 LIAISON / REVIEW-PROTOCOL（含更新后的步骤 1 与单次出兵无日志的限制）/ PLAN §4 §6 / 两条广播。
- 已取数据 A；写了 5 个通用脚本（scripts/00_results_overview.py、01_log_tag_census.py、02_log_skeleton.py、03_line_shapes.py、10_slice_game.py），输出在 out/common/ 和 out/G01|G04|G07/。
- 我独立核到的切片边界与广播 0002 一致：G04=原始行 3207~4140（mode=1 map=10 mapSeed=3070 players=48），G07=5782~6493（mode=0 map=10 mapSeed=3327 players=59），G01=755~1798（mode=5 map=10 mapSeed=9645 players=50）。
- 切片里不输出连接/握手/验证行，也不输出 [SELF-CHECK]/[SQUAD-SYNC]（含账号标识）；只计数。
- G01 我只做到「切片 + 骨架」，没有开始写结论，现在切到 G04。

接下来：读 917e6b1 的 Policy 类（v27-team-live.js 3977~6124 行）和 HL-TICK 各字段的来历 → G04 轨迹表 → 按规程十步做 G04。
