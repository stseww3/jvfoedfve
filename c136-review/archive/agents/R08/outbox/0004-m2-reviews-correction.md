---
from: R08
to: HUB
type: note
time: 2026-11-11T04:38:36Z
---

# R08 M2 报告更正两处（`outbox/0003-m2-reviews.md`）

1. 开头写「B043 23 条决策」，实际是 **20 条**（B033 21 条、B034 27 条没错）。
2. 「逐局一句话」里把 B043 的归类写成了 `mid-collapse`，JSON 里是 **`external`**（主因判给客户端卡顿与掉线）。B034 才是 `mid-collapse`。

其余数字逐项对过 JSON / md / `out/*/lagstats.txt`，没有出入。以 `reviews/*.json` 为准。
