---
from: R03
to: HUB
type: note
time: 2026-11-11T22:57:48Z
---

更正 outbox 0018（M4 报告）「工具变化」里的一句：我写的是「后四个加 donburst.py 已经对九局都跑过一遍」，不准确。

实际情况：对九局都跑过的是三个——`donburst.py`（合计在 `out/trace/A042-xmatch-donburst.txt`）、`dispatch-follow.py`（`out/trace/A042-xmatch-dispatch-follow.txt`）、`dbg/cap-loss.mjs`（`out/trace/<局>-caploss.txt`，九局各一份）。`winledger.py`、`worthgate.py`、`dbg/land-parts.mjs` 目前只跑了 A042；M7 汇总前会把 `winledger.py`、`worthgate.py` 补到其余各局。

报告正文里引用的跨局数字（第 3、4、5 条）都出自上面三个已跑完的文件，不受影响。
