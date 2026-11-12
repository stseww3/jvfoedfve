## 2. 物理底座对真引擎（`--mode verify`）

### 2.1 做法

每一局把录像从头放到尾，不挂策略。每 30 拍把全体真人的（领土、兵力）压成一个指纹，和真引擎重放同一局、同一拍的指纹比。真引擎的指纹由 `scripts/run_truth.sh` 用数据包里的引擎代码重放得到，存在 `sim-v2/truth/`。

另外三样一起查：

- **日志快照**：当年的策略每 90 拍在日志里打一条 `[HL-TICK]`，写着这个号当时看到的自己的领土和兵力。重放到同一拍、同一席位，两个数要相同。这一条不经过真引擎重放，直接拿当年线上的记录核对。
- **分队**：模拟器按引擎的算法现算每个真人的队号，和真引擎算的比。
- **分叉自检**：在第 1200 拍把世界复制一份，两份各走 300 拍，逐拍指纹要相同，原来那个世界不能受影响。断面重演和闭环都靠「复制世界」，这一条不过，后面全不可信。

### 2.2 结果

{{T:verify}}

<!-- assert: n('verify.n') >= 20 && n('verify.full') === n('verify.n') - n('verify.partial.n') && n('verify.partial.n') <= 2 -->
<!-- if: n('verify.n') === n('pack.n') -->
对局包里的 {{v:pack.n}} 局全部核对过。
<!-- else -->
核对了 {{v:verify.n}} 局：任务卡说的核心 20 局全部在内。为覆盖 Va / Vc 新接的 {{v:pack.ext}} 局，物理底座的核对排在队列后面，这一版没有跑完的不在下表里，也不计入下面的数字。
<!-- endif -->

- {{v:verify.n}} 局里 {{v:verify.full}} 局从第 0 拍到录像最后一拍，每个采样拍的指纹都与真引擎相同。合计核对了 {{v:verify.samples}} 个采样拍。
- 没有一致到最后的：{{v:verify.partial}}。两局都是胜负已定之后的终局（2.3 节）。
- 日志快照 {{v:verify.snaps}} 条相同（不同的那 1 条在 A001 的分歧之后，2.3 节）；分队 {{v:verify.teams}} 局与真引擎相同；分叉自检 {{v:verify.clone}} 局通过。
<!-- if: n('verify.va.n') > 0 && n('verify.vc.n') > 0 -->
- 四个版本都有覆盖：Va {{v:verify.va.n}} 局、Vb {{v:verify.vb.n}} 局、Vc {{v:verify.vc.n}} 局、c110 {{v:verify.c110.n}} 局。物理底座和策略版本无关，这里分开数只是说明各版本的房间（人数、队数、内置 AI 是否入队）都验到了。
<!-- else -->
- 按版本：Vb {{v:verify.vb.n}} 局、c110 {{v:verify.c110.n}} 局（Va {{v:verify.va.n}} 局、Vc {{v:verify.vc.n}} 局）。物理底座和策略版本无关，这里分开数只是说明各版本的房间（人数、队数、内置 AI 是否入队）验到了哪些。
<!-- endif -->
- 速度：每 1000 拍约 {{v:verify.cpuPer1000}} 秒 CPU。

### 2.3 两局的终局分歧

<!-- assert: s('verify.partial.mids') === 'A001、B023' && n('verify.partial.n') === 2 -->
<!-- assert: ['A001', 'B023'].every((m) => n(`verify.tail.${m}.leadLand`) >= 99.9 && n(`verify.tail.${m}.leadOwned`) === 100) -->
<!-- assert: ['A001', 'B023'].every((m) => n(`verify.tail.${m}.diff.n`) === 2 && n(`verify.tail.${m}.diff.husk`) === 1 && s(`verify.tail.${m}.diff.leadTeamOnly`) === '是' && n(`verify.tail.${m}.diff.restLand`) === 0) -->
<!-- assert: ['A001', 'B023'].every((m) => n(`verify.tail.${m}.diff.cmdsBetween`) === 0 && n(`verify.tail.${m}.diff.huskLeaveT`) < n(`verify.tail.${m}.t`) && n(`verify.tail.${m}.t`) - n(`verify.tail.${m}.diff.huskLeaveT`) <= 60) -->
<!-- assert: ['A001', 'B023'].every((m) => s(`verify.tail.${m}.diff.huskLessSim`) === '是' && s(`verify.tail.${m}.diff.restMoreSim`) === '是') -->
没有一致到最后的有两局，情形相同：

| | A001（Va，新接进来的局） | B023（c110） |
|---|---|---|
| 指纹一致到（含） | 第 {{v:verify.tail.A001.t}} 拍 | 第 {{v:verify.tail.B023.t}} 拍 |
| 第一个不同的采样 | 第 {{v:verify.tail.A001.firstBadT}} 拍 | 第 {{v:verify.tail.B023.firstBadT}} 拍 |
| 录像共 | {{v:verify.tail.A001.replayTicks}} 拍 | {{v:verify.tail.B023.replayTicks}} 拍 |
| 分歧之前，地最多的一队占全图陆地 | {{v:verify.tail.A001.leadLand}}（有主的地全在它手里，无主的只剩 {{v:verify.tail.A001.unowned}} 格） | {{v:verify.tail.B023.leadLand}}（同左，无主的剩 {{v:verify.tail.B023.unowned}} 格） |
| 在场真人 / 已离场、由内置 AI 托管的席位 | {{v:verify.tail.A001.humansPresent}} / {{v:verify.tail.A001.humansHusk}} | {{v:verify.tail.B023.humansPresent}} / {{v:verify.tail.B023.humansHusk}} |
| 我方席位还在场 | {{v:verify.tail.A001.squadPresent}} | {{v:verify.tail.B023.squadPresent}} |
| 第一个不同的采样上，不同的真人 | {{v:verify.tail.A001.diff.humans}} 个里 {{v:verify.tail.A001.diff.n}} 个，都在占满全图的那一队 | {{v:verify.tail.B023.diff.humans}} 个里 {{v:verify.tail.B023.diff.n}} 个，都在占满全图的那一队 |
| 是哪两个（模拟器 ↔ 真引擎） | {{v:verify.tail.A001.diff.list}} | {{v:verify.tail.B023.diff.list}} |
| 托管的那个席位什么时候离场 | 第 {{v:verify.tail.A001.diff.huskLeaveT}} 拍 | 第 {{v:verify.tail.B023.diff.huskLeaveT}} 拍 |
| 这两个席位在最后一个相同采样到第一个不同采样之间的录像指令 | {{v:verify.tail.A001.diff.cmdsBetween}} 条 | {{v:verify.tail.B023.diff.cmdsBetween}} 条 |

分歧之前的局面由 `tools/verify_tail.mjs` 重放得到；逐人的比较用的是本机留着的真引擎逐人采样。

- **两局都是胜负已定之后才分歧。** 一队已经占了全部有主的地，录像只是还没放完。
- **不同的都是同一对：一个刚离场、由内置 AI 托管的席位，和它的一个在场队友。** 两人的领土相同或几乎相同，差在兵上，而且方向一致：模拟器里托管席位的兵比真引擎少，队友的兵比真引擎多。A001 里托管席位的兵是 {{v:verify.tail.A001.diff.huskBalSim}} 对 {{v:verify.tail.A001.diff.huskBalTruth}}，队友是 {{v:verify.tail.A001.diff.restBalSim}} 对 {{v:verify.tail.A001.diff.restBalTruth}}；B023 里队友在模拟器里正好顶在「领土 × 150」这个能收下的上限上。
<!-- assert: s('verify.tail.B023.diff.restAtCapSim') === '是' && s('verify.tail.B023.diff.restAtCapTruth') === '否' && n('verify.tail.B023.diff.huskLand') > 0 && n('verify.tail.A001.diff.huskLand') === 0 -->
- **原因在托管 AI，不在录像指令。** 这两个席位在那 30 拍里一条录像指令都没有，录像指令两边喂的又是同一份，所以差别只能出在不由录像驱动的一方：托管离场席位的内置 AI。模拟器的物理底座里，这个 AI 的规则是「陆上没有可打的 → 试船 → 试翻山 → 都不成就把兵给队友，离场托管的席位给出全部」（数据包 `src/sim/sim/bots.js` 的 `botAttackTeam`、`botDonate`）。模拟器里它走到了最后一步，把兵给了队友。真引擎里它没有给：A001 里兵留在自己手上，B023 里它多占了 {{v:verify.tail.B023.diff.huskLand}} 格地。两边在「全图没有敌人以后」这一步选得不同。具体是真引擎的哪一条判断没有被底座复刻，没有再往下查。
<!-- if: has('verify.tail.A001.snapBadT') -->
- **以真引擎为准。** A001 的日志快照里有 1 条对不上，在第 {{v:verify.tail.A001.snapBadT}} 拍，正落在分歧之后：当年线上的记录和真引擎一致，和模拟器不一致。
<!-- endif -->

<!-- assert: n('verify.tail.B023.t') > 5184 && n('verify.tail.A001.t') < 5184 -->
这种分歧出现的条件是「一队占满全图之后，队里还有托管席位」。入库的 {{v:verify.n}} 局里出现了 2 次，都在终局；其余各局、以及这两局分歧之前的每一个采样拍都相同。边界记为：**一队占满全图之后的局面不用；具体到这两局，A001 在第 {{v:verify.tail.A001.t}} 拍之后、B023 在第 {{v:verify.tail.B023.t}} 拍之后的结果不用。**

<!-- if: n('verify.tail.skipped.n') > 0 -->
本报告用到的窗口最晚到第 5184 拍。B023 不受影响。A001 受影响的是从第 4284 拍起的那个断面（窗口伸到了第 {{v:verify.tail.A001.t}} 拍之后）：已经跑出来的 {{v:verify.tail.skipped.n}} 次运行（{{v:verify.tail.skipped}}）不进后面任何一张表。
<!-- else -->
本报告用到的窗口最晚到第 5184 拍。B023 不受影响。A001 受影响的只有从第 4284 拍起的那个断面（窗口会伸到第 {{v:verify.tail.A001.t}} 拍之后）；这一版里这个断面还没有 A001 的运行，以后跑出来也不进表（`tools/g0_report.mjs` 按上面的边界自动跳过）。
<!-- endif -->

### 2.4 判定

第 1 项（引擎）通过，带一条边界：一队占满全图之后的终局不用（A001、B023 两局各自的最后一段）。
