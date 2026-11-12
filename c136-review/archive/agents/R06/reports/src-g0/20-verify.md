## 2. 物理底座对真引擎（`--mode verify`）

### 2.1 做法

每一局把录像从头放到尾，不挂策略。每 30 拍把全体真人的（领土、兵力）压成一个指纹，和真引擎重放同一局、同一拍的指纹比。真引擎的指纹由 `scripts/run_truth.sh` 用数据包里的引擎代码重放得到，存在 `sim-v2/truth/`。

另外三样一起查：

- **日志快照**：当年的策略每 90 拍在日志里打一条 `[HL-TICK]`，写着这个号当时看到的自己的领土和兵力。重放到同一拍、同一席位，两个数要相同。这一条不经过真引擎重放，直接拿当年线上的记录核对。
- **分队**：模拟器按引擎的算法现算每个真人的队号，和真引擎算的比。
- **分叉自检**：在第 1200 拍把世界复制一份，两份各走 300 拍，逐拍指纹要相同，原来那个世界不能受影响。断面重演和闭环都靠「复制世界」，这一条不过，后面全不可信。

### 2.2 结果

{{T:verify}}

<!-- assert: n('verify.n') === n('pack.n') -->
<!-- assert: n('verify.full') >= n('verify.n') - 1 -->
- {{v:verify.n}} 局里 {{v:verify.full}} 局从第 0 拍到录像最后一拍，每个采样拍的指纹都与真引擎相同。合计核对了 {{v:verify.samples}} 个采样拍。
- 没有一致到最后的：{{v:verify.partial}}。
- 日志快照 {{v:verify.snaps}} 条相同；分队 {{v:verify.teams}} 局与真引擎相同；分叉自检 {{v:verify.clone}} 局通过。
- 四个版本都有覆盖：Va {{v:verify.va.n}} 局、Vb {{v:verify.vb.n}} 局、Vc {{v:verify.vc.n}} 局、c110 {{v:verify.c110.n}} 局。物理底座和策略版本无关，这里分开数只是说明各版本的房间（人数、队数、内置 AI 是否入队）都验到了。
- 速度：每 1000 拍约 {{v:verify.cpuPer1000}} 秒 CPU。

### 2.3 B023 的终局分歧

<!-- assert: s('verify.partial').startsWith('B023') && n('verify.partial.n') === 1 -->
<!-- assert: n('verify.tail.B023.leadLand') >= 99 && n('verify.tail.B023.leadOwned') === 100 -->
<!-- assert: n('verify.tail.B023.diff.n') === 2 && n('verify.tail.B023.diff.husk') === 1 && s('verify.tail.B023.diff.leadTeamOnly') === '是' -->
<!-- assert: n('verify.tail.B023.diff.restLand') === 0 -->
唯一没有一致到最后的是 B023：指纹到第 {{v:verify.tail.B023.t}} 拍（含）为止全部相同，第 {{v:verify.tail.B023.firstBadT}} 拍那个采样起不同，录像共 {{v:verify.tail.B023.replayTicks}} 拍。

- **分歧之前的局面**（`tools/verify_tail.mjs`）。第 {{v:verify.tail.B023.t}} 拍，地最多的那一队占全图陆地的 {{v:verify.tail.B023.leadLand}}，所有有主的地都在它手里；在场真人 {{v:verify.tail.B023.humansPresent}} 个，另有 {{v:verify.tail.B023.humansHusk}} 个席位已离场、由内置 AI 托管；我方席位还在场 {{v:verify.tail.B023.squadPresent}}。胜负已经分出，录像只是还没放完。
- **是谁不同**（同一个脚本，拿本机留着的真引擎逐人采样比）。第 {{v:verify.tail.B023.firstBadT}} 拍，{{v:verify.tail.B023.diff.humans}} 个真人里只有 {{v:verify.tail.B023.diff.n}} 个不同，都在占满全图的那一队里：{{v:verify.tail.B023.diff.list}}（前一个数是模拟器，后一个是真引擎）。一个是离场托管的席位，真引擎里它的地多 {{v:verify.tail.B023.diff.huskLand}} 格；另一个是在场的队友，领土相同，只是兵不同。
<!-- assert: n('verify.tail.B023.diff.cmdsBetween') === 0 && n('verify.tail.B023.diff.huskLeaveT') < n('verify.tail.B023.t') -->
<!-- assert: s('verify.tail.B023.diff.restAtCapSim') === '是' && s('verify.tail.B023.diff.restAtCapTruth') === '否' -->
- **原因**。这两个席位在第 {{v:verify.tail.B023.t}} 拍到第 {{v:verify.tail.B023.firstBadT}} 拍之间，录像里一条指令都没有（{{v:verify.tail.B023.diff.cmdsBetween}} 条）；托管的那个席位早在第 {{v:verify.tail.B023.diff.huskLeaveT}} 拍就离场了。录像指令两边喂的是同一份，所以差别只能出在不由录像驱动的那一方，也就是托管离场席位的内置 AI。两边各自留下的痕迹也对得上：模拟器里，在场队友的兵正好等于「领土 × 150」，这是引擎规定的一个席位能收下的兵的上限，说明它刚被塞满；真引擎里它没有到上限，而托管席位多了 {{v:verify.tail.B023.diff.huskLand}} 格地、兵也多 {{v:verify.tail.B023.diff.huskBal}}。也就是：全图没有敌人可打之后，托管 AI 在模拟器里把兵给了队友，在真引擎里去占了最后几块无主地。两边为什么选得不同，没有再往下查（它只在这种终局出现）。

这个分歧只在胜负已定之后出现。本报告用到的窗口最晚到 5184 拍，不受影响。边界记为：**B023 在 {{v:verify.tail.B023.t}} 拍之后的结果不用**。

### 2.4 判定

第 1 项（引擎）通过，带一条边界（B023 的终局）。
