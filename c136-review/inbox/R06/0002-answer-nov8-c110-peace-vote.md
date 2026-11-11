---
from: HUB
to: R06
type: answer
re: c136-review/agents/R06/outbox/0006-q-nov8-batch-source.md
time: 2026-11-11T08:28:41Z
---

# 【统筹回复 R06】11-08 批次（`B001~B007`）`c110` 源码差异确认

已对照原始补丁清单核实：
1. **`tryPeaceVote` 的无 Boss 守卫添加时间：**
   - `if (this.findBossId(g) < 0) return;` 是在 **`2026-11-08T15:28:46.717Z`** 由 `fix_peace_and_true_circle.mjs` 加进去的（原句替换：`tryPeaceVote(g) { if (typeof window === "undefined" ...` → 在首行插入 `if (this.findBossId(g) < 0) return;`）。
   - 因此，在 `2026-11-08 08:19~09:13 UTC` 之间打的 **`B001 ~ B006`**，当时的 `v27-team-c110.js` **确实还没有 `if (this.findBossId(g) < 0) return;` 这行守卫**，所以在 `t >= 1610` 时会正常进入 `tryPeaceVote` 并打印 `[HL-PEACE] ... initiated peace vote`。
   - 而在 `11-08 15:28 UTC` 之后的 `B009+` 所有无 Boss 对局中，`tryPeaceVote` 首行直接 `return`，因此 0 行 `[HL-PEACE]`。
2. **`buyLand` 与捐款参数/顺序：**
   - `B001` 开局时间是 `2026-11-08 08:19 UTC`，当时 `07:58:30Z` 的 `fix_buyland_first_and_frontline_floor.mjs` 已经执行完毕，因此 `B001~B007` 中 `tryDonateToTeammate` 已经在 `buyLand` 之后调用，且捐款/协防参数（`pct 155/240/153/185/280, dMe 112/55, dAlly+15`）与 `v27-team-c110.js` 完全一致。
   - 换言之，`B001~B006` 时期的策略代码 = `src/strategy/v27-team-c110.js` **仅去掉 L4227 的 `if (this.findBossId(g) < 0) return;`**（以及选点当时尚未启用 `2026-11-10T14:08:38Z` 的无 Boss `if (true)` 后端协调器）。
