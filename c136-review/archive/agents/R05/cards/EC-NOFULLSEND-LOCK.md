# EC-NOFULLSEND-LOCK　`isNoFullSend` 被误置位，之后不复位

- 类别：IO（执行）/ EC｜证据：E1×13（影子策略复算，13 局都做了不锁对照）｜13 局里 5 局登记（错 3、不确定 2）[RO §6]，置位本身 13/13 局
- 一句话：策略用「发令后 7 拍内余额掉得比预期少」来推断引擎开了「禁全兵」模式。指令要 11–13 拍才执行，这个推断看的是别的指令造成的余额变化。标志一旦置位就不再复位。

## 定义

影子策略里某个号的 `isNoFullSend` 由 false 变 true 的那一拍 = 置位拍。配额闸拒发 = `Policy.send` 被调用但没有走到最后一句 `return ok` 的次数。引擎真实规则取录像头的 `battleRoyaleMode`（`rules_header.mjs`）。

## 脚本

`scripts/quota_guard.py`（读 `shadow.mjs --json` 的 `nfsAt`、`sendExits`）；不锁对照 `scripts/shadow_unlock.sh` + `scripts/unlock_diff.py`；汇总在 `accounts_table.py` 第 7 节。要跑影子策略，全量没有。日志里不打印这个标志，没有只读日志的代理口径。

## 13 局

- 引擎的禁全兵模式 13 局全是关的。[DL §7]
- 被置位的号：A014、A030、A037、A065、A095 10/10，A034 9/9，A021 9/10，A093 8/9，A058 7/10，A026 6/9，B010 12/13，A043 2/2，A017 1/1。各局第一个置位拍：A093 64 拍，其余 12 局在 442–855 拍之间。[DL §7]
- 配额闸拒发占全部 `Policy.send` 调用的 0.6–10.0%（A014 61/609、A037 69/796、A095 44/539、A017 1/179）；600–1500 拍每局 1–45 次。[DL §7]
- 不锁对照（每拍把标志清回 false 重跑影子；一阶量，不是重演）：两边不同的指令占 2.0–10.6%。5000 拍以后「锁挡掉的」A014 26 条、A030 13 条、A037 12 条、A065 8 条，其余局 0–6 条；「锁着才发的」0–4 条。[DL §7]

## 机制

- `Policy.send` L3876：线上发令后记 `pendingQuotaCheck = { t: g.t + 1, bal0, fee, want }`。
- `updateShadowQuota` L3821–3834：此后 1–7 拍内只要余额 `< bal0 − fee`，就算 `actualSent = bal0 − 余额 − fee`；`want ≥ 1.12 × actualSent` 且 `actualSent < bal0 − fee − 50` → `isNoFullSend = true`、`shadowQuota = 0`。
- 这 7 拍里这条指令还没执行。余额变少只可能是更早的指令落地，或者被人打。
- 置位后 `Policy.send` L3844：`shadowQuota < min(0.55 × 兵数, 0.06 × 存兵)` 时，对机器人目标直接不发；对真人目标改发 1 兵或不发。
- 同一个标志还关着另外几道门（条件里都有 `!isNoFullSend`）。Vb/Vc 里是三道：`shadowedByTop` L5262、`isLeaderFortress` L5264–5272、`isSiegeShrink` L5428–5436（`leaderHardFrom = 5000`、`siegeShrinkRatio = 0.72`），本该在 5000 拍后生效；标志置位之后它们一直是关的。c110 再加两道：`isStaleHardAgg`、`isGiantTopRival`（`a06AggMemGate = 1`、`a06AloneSafe = 1`）。Va 这几个参数都是 0，没有这几道门。

## 与胜负的方向

13 局都有，赢的 A037 同样 10/10 置位。按条数是小项。

## 反例与混杂

- 不锁对照是一阶量：两个影子跑在同一份录像局面上，某条决策不同以后真实对局会走向别处，这里看不到。
- 把标志修对会同时放开配额闸、打开那几道门，两头的效果方向相反（多发 / 少发）。一阶对照里 5000 拍后前者 0–26 条、后者 0–4 条。

## 还没验证

修对之后同一局的走向（E4）。全量有多少号被置位（要全量影子，跑不动）。
