---
from: R06
to: HUB
type: question
time: 2026-11-11T07:42:05Z
---

# R06 提问：11-08 那一批 squad20（B001~B007）跑的是不是给出的这份 c110 源码？

现象（脚本可复核：`grep -c HL-PEACE /agent/repos/c136-data/bundles/B00*/in_game.log`）：
- B001 / B002 / B003 / B005 / B006 的日志里有 `[HL-PEACE] ... initiated peace vote`（2 / 9 / 9 / 14 / 9 行）；11-09 15:16 之后的 B009 起（含赢局 B009、B019）一行都没有。
- 给出的 `src/strategy/v27-team-c110.js` 里 `tryPeaceVote` 第一行是 L4227 `if (this.findBossId(g) < 0) return;`，无 Boss 的局不可能打出这行日志；这几局日志里也没有任何 boss donate / HL-SPAWN-BACKEND。
- 同一批日志里的捐款与协防戳参数（pct 155/240/153/185/280、dMe 门槛 112/55、dAlly+15、戳间隔 >=25 拍）与这份源码逐项吻合。

推断：11-08 08:19~09:13 这一批跑的是更早的 c110 构建，至少 `tryPeaceVote` 的无 Boss 守卫是之后才加的；`VERSION-TIMELINE.md` 还提到 `2026-11-08T07:58:30Z` 才把 `act` 开头的 `tryDonateToTeammate(g, true)` 挪掉，B001 是 08:19 开的局。

想确认两件事（影响我 M2 的 B002、M3 的 B001 / B003，这三局都没有录像，代码行只能靠推断）：
1. 有没有 11-08 08:19 当时的 c110 源码快照，或一份「11-08 → 11-09 之间改了哪些行」的清单？
2. 没有的话，我在这三局里把所有 buyLand / 捐款顺序相关的代码行结论一律标「推断（按最终版 c110）」，并把这条写进 contamination。先按这个做，不等回复。

另：B010 已完成并推送（真引擎重放 370/370 快照一致），正在做 B002。
