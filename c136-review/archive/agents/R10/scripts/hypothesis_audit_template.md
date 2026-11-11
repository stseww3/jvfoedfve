# HYPOTHESIS-AUDIT — 六个核心局内假设的红队审计（发现集 {{census.games}} 局）

> R10（裁判与红队）· 里程碑 M2。本文所有数字由 `scripts/audit_hypotheses.py` 从对局包重算后填入模板 `scripts/hypothesis_audit_template.md`，正文不手写数字；机器可读结果在 `out/hypothesis-audit.json`。只用发现集 `/agent/repos/c136-data/bundles/`，不含验证集的任何信息。本文只做核实，不提任何参数或补丁建议。

## 0. 先看结论

| 假设 | 审计结论 | 发现集上的频率 | 量级 | 最大的混杂 | 证据等级 |
| :-- | :-- | :-- | :-- | :-- | :-- |
| ① 配额拒单让 `act(g)` 提前 `return`、跳过 `buyLand` | **机制不成立，现象成立。** {{meta.nVersions}} 个版本的代码里捐款都排在 `buyLand` 之后，而且只在本拍没发过任何指令时才调用，一次 `buyLand` 都挡不掉。但“下了单没成交”是真的，而且几乎全是引擎配额拒的 | squad10 录像覆盖内的下单 {{h1.squad10.notExec|wci}} 没成交；其中 {{h1.verdictSquad10.quotaShare|pct}} 按引擎配额公式确实放不下 | 解禁前（t<4284）平均每个房间×快照有 {{h1.episodes.Vb.balSharePre.mean|pct}}（Vb）的我方余额压在“想送送不出去”的号上；一段中位 {{h1.episodes.Vb.dur.med|n}} 拍，P90 {{h1.episodes.Vb.dur.p90|n}} 拍 | 和胜负没有可见关系（AUC {{h1.outcome.squad10.auc.auc|f2}}）；下单→成交有延迟，{{h1.lag.Vb.ge35|wp}}（Vb）的成交晚于旧口径的 35 拍窗口 | 机制：代码级否定；现象：E2 |
| ② 6.25% 全额余额税在小比例捐款下的损耗 | **机制精确成立，但“小比例”只是 squad20 / squad8 的问题。** Vb 代码里 `pct<180` 直接不捐。Vb 的手续费主要烧在解禁后“来回倒”和收款方顶到上限的转账上 | `pct<180` 的成交捐款：Vb {{h2.byVersion.Vb.lt180|w}}，c110 {{h2.byVersion.c110.lt180|w}}，g09 按日志估计 {{h2.estimateNoReplay.g09.lt180|w}} | 手续费 ÷ 到账：Vb {{h2.byVersion.Vb.feeOverArrive|pct}}，c110 {{h2.byVersion.c110.feeOverArrive|pct}}，g09 估计 {{h2.estimateNoReplay.g09.feeOverArrive|pct}}；每局手续费 ÷ 同期利息收入中位：Vb 解禁前 {{h2.feeOverInterest.Vb.pre.med|pct}}、解禁后 {{h2.feeOverInterest.Vb.post.med|pct}} | Vb 全部手续费的 {{h2.concentration.Vb.top2Share|pct}} 出在手续费最高的 2 局里，其中赢的 {{h2.concentration.Vb.top2Wins}} 局 | 机制：E2（引擎逐笔精确）；“小比例损耗”：c110 为 E2，Vb 不适用 |
| ③ 内陆 `nb=0` 号高密度憋死 | **频率成立，危害没有证据。** 这些号绝大多数在下单、只是被配额拒，和 ① 是同一件事的另一面 | Vb：{{h3.byVersion.Vb.high|w}} 的快照处于憋死状态，{{h3.byVersion.Vb.botsAny|w}} 的号出现过，{{h3.byVersion.Vb.bots10|w}} 的号累计 ≥900 拍 | Vb 解禁前憋死号平均占我方余额 {{h3.byVersion.Vb.balShareHighPre.mean|pct}}；被软上限压掉的利息每局中位只有 {{h3.byVersion.Vb.forgoneShare.med|pct}} | 幸存者偏差：憋死快照占比在赢的房间更高（AUC {{h3.outcome.squad10.auc.auc|f2}}），方向和假设相反 | 频率：E2；“导致输”：E0 |
| ④ 选点过密导致内圈开局饿死 | **按统筹的定义在 squad10 基本不存在。** 开局 630 拍内被封且领土不到 2500 的号极少；放宽到 1530 拍后“被封”很常见，但被封的号领土并不小 | Va {{h4.byVersion.Va.early|w}}，Vb {{h4.byVersion.Vb.early|w}}，Vc {{h4.byVersion.Vc.early|w}}，c110 {{h4.byVersion.c110.early|w}}，g09 {{h4.byVersion.g09.early|w}} | c110 的 {{h4.byVersion.c110.early.k}} 个开局被封号 t=1530 领土中位 {{h4.byVersion.c110.terr1530Early.med|n}}，同版本其他号 {{h4.byVersion.c110.terr1530Other.med|n}} | “间距越小领土越小”主要是地图大小造成的：Vb 房间级相关 {{h4.minAllyDist.Vb.spearmanRoomLevel|f2}}，同房间内只有 {{h4.minAllyDist.Vb.spearmanWithinRoom|f2}} | 统筹定义：squad10 为 E2 级否定；c110 个例 E2（样本小） |
| ⑤ 留守底线 `oppFloorCap` 被集火时脆弱 | **生死由“真人对它的出兵 ÷ 它的余额”决定，留守线密度不是约束。** 被集火的号 {{h5.squad10.focus.belowFloorShare|wp}} 在集火开始时已经低于留守线；同样的受攻比下，密度更高并不更安全 | squad10 集火窗口 {{h5.squad10.focus.windows|n}} 个（占全部号×窗口 {{h5.squad10.focus.shareOfWindows|pct}}），360 拍内阵亡 {{h5.squad10.focus.die360|w}} | 全部 {{h5.squad10.deaths.n|n}} 次阵亡里，死前 360 拍内“在留守线上被集火”的只有 {{h5.squad10.deaths.afterFocusAtFloor|w}} | 密度本身是被打的结果（反向因果）；统筹的“领先局 ≥35%”把两队局里的落后方也算了进去 | 受攻比关系：E2；“留守线太低导致崩盘”：未获支持；领先局崩盘拆解：E1（{{h5lead.byCohort.squad10.loss.n}} 局） |
| ⑥ `squad20` 拆队与和平投票 | **拆队没有带来可见的互殴损失，也看不到“我方号越多的队越容易赢”；和平投票在 {{h6.peaceLast.mid}} 之后没有任何记录。** | {{h6.teamRooms}} 个组队房间里 {{h6.splitRooms}} 个把我方号分到了 ≥2 个队；同编队异队互打占对真人出兵的 {{h6.squadAttacks.squadShareOfHumanDirected|pct}} | 阵亡里头号进攻者是同编队号的 {{h6.deaths20.killerOur|w}}；`[HL-PEACE]` 共 {{h6.peaceLogTotal}} 行，全部在 {{h6.peaceLogs.0.mid}}–{{h6.peaceLogs.4.mid}} 之间的 {{h6.peaceLogBundles}} 个包里，其中有录像的 {{h6.peaceLogBundlesWithReplay}} 个 | squad20 的 {{census.byCohort.squad20.replay}} 份录像只有 {{census.byCohort.squad20.replayFull}} 份完整；“任一有我方号的队赢”的高比例是把号撒到多数队伍上的算术结果 | 无互殴、无剂量效应：E2（功效低）；和平锁：无数据，E0 |
| 附：执行层同拍叠单（审计中新增的混杂项） | 我方号的指令有很大一部分是 ≥3 条挤在同一拍落地的，比例远高于同局其他真人；其中一部分一拍打掉半数以上余额 | squad10：{{hx.stackHist.ours_squad10.share3|pct}} 的指令（同局其他真人 {{hx.stackHist.wild_squad10.share3|pct}}）；一拍打掉 ≥50% 余额的叠批 {{hx.dumpSummary.squad10.dump50|n}} 次，分布在 {{hx.dumpSummary.squad10.games}} 局 | t≥1500 的 {{hx.dumpSummary.squad10.core|n}} 次里中位一拍花掉余额的 {{hx.dumpSummary.squad10.fracCore.med|pct}}；之后 360 拍内阵亡 {{hx.afterDump.squad10.stackDump|w}}，有出兵但没清仓的窗口 {{hx.afterDump.squad10.attackNoDump|w}} | 叠单来自客户端落后追帧，落后本身可能和局势同因 | 频率：E2；与阵亡的关联：E2（有混杂） |

证据等级按 `PLAN.md`：E0 猜想，E1 单局个例，E2 发现集脚本统计，E3 验证集复现（M4 做），E4 模拟器反事实。

## 1. 数据与口径

{{TABLE:census}}

- **真引擎重放。** 用 R04 的 `engine_host.cjs` 加我的只读探针 `scripts/engine_probe.cjs` 把 {{census.engine.games}} 份录像全部重放了一遍。我方号每 90 拍的领土和余额与日志 `[HL-TICK]` 逐点比对，{{census.engine.snapExact|n}}/{{census.engine.snapPoints|n}} 完全一致；引擎里我方号执行的指令 {{census.engine.cmdsEngine|n}} 条，和我自己写的 Python 录像解码器解出的 {{census.engine.cmdsReplay|n}} 条一一对应。下文凡写“引擎真值”的都来自这次重放。
- **squad20 的录像覆盖很差，这是硬限制。** {{census.byCohort.squad20.replay}} 份录像里 {{census.byCohort.squad20.replayEmpty}} 份只有出生阶段（开局第 1 拍就结束），{{census.byCohort.squad20.replayLt1500}} 份不到 1500 拍，只有 {{census.byCohort.squad20.replayFull}} 份盖到日志最后一拍。录像没盖到日志最后一拍的包列在本节末尾的表里；任务卡点名的双审重叠局里没有中后期引擎真值的是 {{census.dualNoMidgame|list}}。squad20 的引擎真值数字只代表有覆盖的那部分；squad8 没有录像，只能用日志口径。
- **版本。** squad10：Va（A001–A017，`oppFloorCap`={{meta.floorCap.Va}}）、Vb（A018–A095，{{meta.floorCap.Vb}}）、Vc（A097–A099，{{meta.floorCap.Vc}}）；squad20：c110（{{meta.floorCap.c110}}）；squad8：g09（{{meta.floorCap.g09}}）。
- **用词。** 拍 = 引擎的一个 tick；快照 = 日志里每 90 拍一行的 `[HL-TICK]`；密度 = 余额 ÷ 领土（兵/格）；解禁 = t ≥ 4284，之后引擎不再限制捐款配额；组队房间 = 开局模式是组队的房间（大逃杀和 1v1 不算）；主队 = 一个房间里我方号最多的那个队。
- **只算我方号在录像覆盖内的部分。** “录像覆盖内的下单”指下单拍 ≤ 录像末拍 − 30 的 `[HL-DISPATCH]` / `[HL-DONATE]` 行；“成交”指录像里在下单后 400 拍内出现了同一捐出号、同一收款号、同一 `pct` 的捐款指令（引擎只把通过配额的捐款写进录像）。

任务卡点名的双审重叠局：

{{TABLE:census_dual}}

录像末拍比日志最后一拍早 90 拍以上的对局包：

{{TABLE:census_short}}

## 2. 假设 ①：配额拒单导致 `act(g)` 提前 `return` 停摆

**原说法**（`PLAN.md` 先验事实 2、欢迎信问题 ①）：捐款被引擎配额拒掉后余额不降，但 `g.donate()` 返回 `true`，`tryDonateToTeammate` 在 `act(g)` 开头返回并直接 `return`，这一拍的 `buyLand(g)` 被跳过。

### 2.1 代码里没有这条路径

{{TABLE:h1_code}}

五个版本里 `tryDonateToTeammate` 都只有一个调用点，写法都是 `if (this.cmds === cmdsBefore) this.tryDonateToTeammate(g);`，位置在主 `act(g)` 里 `this.buyLand(g)` 之后。`cmdsBefore` 是在 `buyLand` 之前记下的指令计数，所以只要本拍 `expandNeutral` / `buyLand` / 补船发过任何一条指令，捐款就不会被调用。捐款成功返回之后，同一拍里被它挡掉的只有紧跟其后、带同样守卫的 `idleBoats(g)`；`act` 后面的跳岛等逻辑照常执行。`act` 开头确实有两处提前 `return`，但都在 Boss 急救分支里；全部 {{h1.boss.spawnRows|n}} 行出生日志里带 Boss 的是 {{h1.boss.spawnRowsWithBoss}} 行。这一点统筹在 0002 号广播里已确认过 R04 的同一结论，这里是对五个版本的脚本复核。

每个号的捐款还受槽位轮转限制，25 拍里最多试一次：

{{TABLE:h1_foot}}

所以被拒捐款直接占掉的“拍数”上限就是这张表：一个 90 拍窗口的 18 个决策拍里，squad10 最多 {{h1.footprint.Vb.max}} 拍、c110 最多 {{h1.footprint.c110.max}} 拍，而且这些拍本来就是 `buyLand` 没发指令的拍。**“因为捐款被拒而错过的 `buyLand` 次数”是 0。**

### 2.2 但“下了单没成交”是真的

{{TABLE:h1_truth}}

`PLAN.md` 先验事实 2 说的“七成多被拒”这个量级是对的（旧口径在 squad10 上是 {{h1.squad10.heurRej|w}}）：squad10 录像覆盖内 {{h1.squad10.covered|n}} 次下单，没成交 {{h1.squad10.notExec|wci}}。分阶段看，问题集中在解禁之前：

{{TABLE:h1_phase}}

按下单类别和日志里的 `boxedIn` 标记：

{{TABLE:h1_kind}}

{{TABLE:h1_boxed}}

### 2.3 没成交的原因：{{h1.verdictSquad10.quotaShare|pct}} 是引擎配额

对每一次没成交的下单，我在下单后第 7、14、21 拍三个可能的到达拍上，用引擎里当时的真实余额、收款方已用配额和配额上限，按引擎公式重算这一单过不过得了。三个到达拍结论一致才算数：

{{TABLE:h1_verdict}}

squad10 合计 {{h1.verdictSquad10.n|n}} 次没成交的下单里，单笔就超过当时上限的 {{h1.verdictSquad10.singleOver|n}} 次（{{h1.verdictSquad10.singleShare|pct}}），加上收款方已用额度后超限的 {{h1.verdictSquad10.accOver|n}} 次（{{h1.verdictSquad10.accShare|pct}}），配额内放得下、原因不明的 {{h1.verdictSquad10.fits|n}} 次（{{h1.verdictSquad10.fitsShare|pct}}）。c110 没成交的下单只有 {{h1.verdict.c110.n|n}} 次，其中配额能解释的占 {{h1.verdict.c110.quotaShare|pct}}，其余原因本审计没有定位。

引擎的配额是“整单过或整单拒”，没有部分成交。被配额拒的那些单，当时其实大多还有余量：

{{TABLE:h1_rightsize}}

squad10 被配额拒的 {{h1.rightSizeSquad10.n|n}} 单里，配额基本用尽（放得下的不到想送的 5%）的只有 {{h1.rightSizeSquad10.lt5|w}}；想送的量中位 {{h1.rightSizeSquad10.wantV.med|n}}，当时放得下的量中位 {{h1.rightSizeSquad10.fitV.med|n}}。也就是说多数被拒的单不是因为配额用光，而是因为一单要送的量远大于当时还放得下的量。配额上限随时间和地图大小变化，下表是按引擎公式算的“单个收款方从开局起累计最多能收多少兵”（不计每笔 2 点的底数；t<3213 时只和地图陆地格数有关）：

{{TABLE:h1_ceiling}}

### 2.4 旧口径 `likelyRejected` 准不准

`events.csv` 里的 `likelyRejected` 是“35 拍内再次下单时余额没降”的推断。拿录像真值对一下：

{{TABLE:h1_heur}}

squad10 上可以用（Vb 判“拒”的准确率 {{h1.heuristic.Vb.ppv|wp}}），c110 上不行（{{h1.heuristic.c110.ppv|wp}}）。复盘里引用捐款是否成交，应当以录像为准。

### 2.5 量级：涉及多少拍、多少兵

把同一个号相邻间隔不超过 {{h1.episodeGap}} 拍的连续被拒下单并成一段“想送送不出去”：

{{TABLE:h1_episodes}}

真正成交的捐款绝大部分发生在解禁之后：

{{TABLE:h1_flow}}

### 2.6 混杂因素

1. **下单到成交有延迟。** 成交的单中位延迟 {{h1.lag.Vb.med}} 拍（Vb），但尾巴很长：

{{TABLE:h1_lag}}

   旧口径的 35 拍窗口会把这部分晚到的成交误判成“被拒”。本审计的成交判定窗口是 400 拍。
2. **和胜负没有可见关系。** 每个房间解禁前的被拒次数（按“号×快照”归一）：

{{TABLE:h1_outcome}}

   赢的房间和输的房间分不开。另外这个指标本身带幸存者偏差：代码里过了开局期、领土和余额都够门槛的号才会下单（Vb 的写法是 `g.t < 1500 || g.terr[me] < 1200 || g.bal[me] < 30000` 时直接返回），活得久、余额多的号下单才多。
3. **录像覆盖。** c110 有 {{h1.byVersion.c110.uncovered|n}} 次下单在录像覆盖之外，g09 的 {{h1.byVersion.g09.logged|n}} 次全部没有录像，这两部分只有日志口径。
4. **{{h1.verdictSquad10.mixed|n}} 次下单在三个到达拍上结论不一致**（三个到达拍之间配额上限和收款方状态都可能变），没有计入“配额解释”。

### 2.7 结论

- “捐款被拒 → `act` 提前返回 → 跳过 `buyLand`”：**否定**。复盘里不应再把它写成错误模式。
- “解禁前大部分捐款下单被引擎配额整单拒掉，富余兵力转不出去”：**成立，E2**。它是不是输的原因，本审计没有证据。

## 3. 假设 ②：6.25% 全额余额税在小比例捐款下的损耗

**原说法**（欢迎信问题 ②）：捐款固定扣捐出方总余额的 6.25%，与 `pct` 无关；`pct<180` 时税损相对到账兵力很大。

### 3.1 机制逐笔精确成立

引擎里捐出方付的是“转出额 + floor(64×余额/1024)”。{{h2.feeFormula.n|n}} 笔全场真人的成交捐款，手续费全部等于这个公式；其中 {{h2.feeFormula.debt}} 笔收款方有欠兵，转出额先抵欠，到账少于转出额，其余 {{h2.feeFormula.exact|n}} 笔转出额等于到账。手续费和 `pct` 无关，所以不被截断时“手续费 ÷ 到账”就是 64/(pct+1)：

{{TABLE:h2_theory}}

### 3.2 小比例捐款出现在哪些版本

{{TABLE:h2_version}}

{{TABLE:h2_bucket}}

各版本代码里有没有“比例太小就不捐”的闸：

{{TABLE:h2_guard}}

Vb 在算出的 `pct` 小于 {{h2.pctGuard.Vb.last.threshold}} 时直接返回不捐，所以 Vb 没有一笔 `pct<180` 的捐款；Va、Vc 的闸更低，有少量。c110 和 g09 没有这道闸，小比例是常态（c110 中位 `pct` {{h2.byVersion.c110.pct.med}}），其中 `pct<64` 的 {{h2.byBucket.6.n}} 笔合计手续费比到账还多。没有录像的包只能按日志估计（取日志判“成交”的单，按下单时余额套公式）：

{{TABLE:h2_est}}

作参照，同局其他真人的 {{h2.wild.n|n}} 笔捐款里 `pct<180` 的占 {{h2.wild.lt180|wp}}，手续费 ÷ 到账 {{h2.wild.feeOverArrive|pct}}。

### 3.3 Vb 的手续费实际烧在哪里

Vb 的“手续费 ÷ 到账”是 {{h2.byVersion.Vb.feeOverArrive|pct}}，高于它的 `pct`（中位 {{h2.byVersion.Vb.pct.med}}）对应的理论值。比例偏高来自截断，总量大来自来回倒，都和“小比例”无关。

**第一，收款方顶到余额上限时到账被截断，手续费照收。** 引擎里一个号的余额上限是 150×领土；转出额超过收款方还能装的量时只转装得下的部分，多出来的留在捐出方，但手续费仍按捐出方总余额收。全部 {{h2.truncAtCap.n|n}} 笔到账明显少于 `pct` 对应额的捐款里，{{h2.truncAtCap|w}} 的收款方在到账后正好停在 150×领土。Vb 有 {{h2.byVersion.Vb.feeGeArrive}} 笔手续费不少于到账。分阶段（“不截断时应有的”一列是同样这些单如果全额到账的比例）：

{{TABLE:h2_phase}}

**第二，解禁后两个号之间来回倒。** 收款号在 300 拍内又把兵转回给原捐出号：

{{TABLE:h2_relay}}

按局看，这种现象集中在少数几局：

{{TABLE:h2_pingpong}}

一个号在解禁后会连续转很多笔，每一笔都按当时的总余额扣一次：

{{TABLE:h2_chains}}

来回倒笔数最多的一对号是 {{h2.example.mid}}（结局 {{h2.example.outcome}}）的 {{h2.example.names.0}} 与 {{h2.example.names.1}}：从第 {{h2.example.tFirst|n}} 拍到第 {{h2.example.tLast|n}} 拍，两个号之间互转了 {{h2.example.n}} 笔，到账合计 {{h2.example.arrive|n}}，手续费合计 {{h2.example.fee|n}}。开头几笔如下——余额大的号每转一次按自己的总余额扣一次手续费，而收款号顶在余额上限，到账被截断；随后收款号又按自己的上限余额转回去：

{{TABLE:h2_example}}

手续费总量高度集中：

{{TABLE:h2_conc}}

### 3.4 量级参照

{{TABLE:h2_interest}}

{{TABLE:h2_burn}}

### 3.5 混杂因素

1. **集中度。** Vb 全部手续费的 {{h2.concentration.Vb.top2Share|pct}} 来自 2 局，赢的 {{h2.concentration.Vb.winGames}} 局占了 {{h2.concentration.Vb.feeWinGames|pct}}。按兵力加权的任何比例都被这两局主导，所以上面同时给了按局的中位数。
2. **手续费是不是“损失”取决于不捐会怎样。** Vb 的下单里日志标记 `boxedIn=true` 的占 {{h1.boxedShare.Vb|w}}，捐出方绝大多数是被封的内陆号（见 §4），这些兵不转出去也只是按被压低的利率生息；本审计没有做反事实，不判断净效果。
3. **squad8 和 {{census.byCohort.squad20.noReplay}} 个没有录像的 squad20 包只有日志估计**，估计用的是“日志判成交”的单，c110 上这个判定的准确率只有 {{h1.heuristic.c110.ppv|wp}}。

### 3.6 结论

- 机制（固定 6.25%、与 `pct` 无关）：**成立，E2**，引擎逐笔精确。
- “小比例捐款损耗”：对 c110 **成立，E2**（{{h2.byVersion.c110.lt180|w}} 的成交捐款 `pct<180`，这部分手续费 ÷ 到账 {{h2.byVersion.c110.lt180FeeOverArrive|pct}}）；对 g09 只有日志估计；对 Vb **不适用**。
- Vb 的手续费主要来自解禁后的截断和来回倒，且集中在已经赢下的局里。这一条是审计中新发现的，**E2（频率）**，对胜负的影响没有证据。

## 4. 假设 ③：内陆 `nb=0` 号高密度憋死

**口径**（欢迎信问题 ③）：组队房间、t≥1500 的快照，`nb=0` 且 `neut=0` 算“被封”，再加 `dens≥95` 算“憋死”。

### 4.1 频率

{{TABLE:h3_version}}

按“每个房间、每个快照时刻”归一后的占比（这样不会被后期的巨额余额主导）：

{{TABLE:h3_share}}

### 4.2 这些号在做什么

对每张憋死快照，看它之后 90 拍里这个号有没有下捐款单、成交没有（只算录像覆盖内）：

{{TABLE:h3_behave}}

Vb 解禁前的憋死窗口里 {{h3.behaveBy.Vb.pre.allRejectedShare|w}} 是“下了单全被拒”，没下单的只有 {{h3.behaveBy.Vb.pre.noAttemptShare|w}}。所以 Vb 的“憋死”不是号不动，而是 §2 的配额拒单；解禁后被拒的只剩 {{h3.behaveBy.Vb.post.allRejectedShare|w}}。c110 相反，憋死窗口 {{h3.behaveBy.c110.post.n}} 个在解禁之后、{{h3.behaveBy.c110.pre.n}} 个在解禁之前，解禁后的窗口里 {{h3.behaveBy.c110.post.noAttemptShare|w}} 没有下单。

### 4.3 量级

{{TABLE:h3_interest}}

{{TABLE:h3_fate}}

Vb 憋死 ≥900 拍的号最后阵亡时余额中位只有 {{h3.byVersion.Vb.lostAtDeath.med|n}}，也就是说它们并不是“带着一大笔兵被吃掉”；c110 的这个数是 {{h3.byVersion.c110.lostAtDeath.med|n}}。

### 4.4 混杂因素

{{TABLE:h3_outcome}}

1. **方向和假设相反。** 憋死快照占比在赢的房间更高。内陆号要先活下来、周围都是队友才会被封并攒到高密度，这是领先的标志，不是落后的原因。用“憋死占比高”去解释输局会得出反的结论。
2. **阈值。** `dens≥95` 接近软上限起作用的位置，换成 100 或 145 数量会明显减少（表里已列）。
3. **和 ① 重叠。** Vb 解禁前的憋死窗口 {{h3.behaveBy.Vb.pre.allRejectedShare|wp}} 是配额拒单，两条假设不能当成两个独立的错误模式去计数。

### 4.5 结论

频率 **成立，E2**；“憋死导致输”**没有证据（E0）**，现有关联方向相反。

## 5. 假设 ④：选点过密导致内圈开局饿死

**口径**（欢迎信问题 ④）：t<630 的快照上 `nb=0`、`neut=0` 且领土 <2500。日志最早的快照就是 t=630，这里取 t≤630。

### 5.1 频率

{{TABLE:h4_version}}

{{TABLE:h4_rooms}}

按统筹的定义，squad10 三个版本合起来是 {{h4.squad10Early|wci}}。把时间放宽到 1530 拍，被封过的号有 {{h4.squad10Any1530|w}}，但加上“领土 <2500”之后只剩 {{h4.squad10Small1530|w}}：被封的号多数领土并不小。

### 5.2 发生了的那几个号后果如何

{{TABLE:h4_effect}}

c110 的 {{h4.byVersion.c110.early.k}} 个号后果明显：第一次被封时中位只有 {{h4.byVersion.c110.terrAtBox.med|n}} 格，到 t=1530 领土中位 {{h4.byVersion.c110.terr1530Early.med|n}}，同版本其他号 {{h4.byVersion.c110.terr1530Other.med|n}}；有配对的房间里差值为负的是 {{h4.byVersion.c110.pairedNeg|w}}。

### 5.3 选点间距和角色

{{TABLE:h4_corr}}

Vb 的号级相关看上去很强，但拆开看：房间级相关 {{h4.minAllyDist.Vb.spearmanRoomLevel|f2}}，而房间的间距中位数和“每个席位平均多少陆地”的相关是 {{h4.minAllyDist.Vb.spearmanRoomLandPerSeat|f2}}——间距是按地图大小定的，地图小的房间间距小、每个号能拿的地也少。去掉房间之间的差别后，同一房间内间距和领土的相关只有 {{h4.minAllyDist.Vb.spearmanWithinRoom|f2}}。

{{TABLE:h4_role}}

Vb 的 `INNER_ARC_BANK` 到 t=1530 被封的比例最高，领土中位比外圈低，但余额更高、t<3000 的阵亡率更低。

### 5.4 出生令重叠（引擎真值）

{{TABLE:h4_dup}}

这是和“选点过密”相邻但不同的问题：两个号的最终出生令落在同一个像素，或者有号一条出生令都没被执行。squad10 合计：{{h4.dupSquad10.rooms}} 个带录像的组队房间里，{{h4.dupSquad10.roomsDup}} 个有叠点，{{h4.dupSquad10.roomsNoSpawnCmd}} 个有号没执行过出生令。统筹 0003 号广播转述 R05 的口径是“70 局录像中 19 局叠点、8 局有号没执行出生令”；我只数了组队房间，分母不同，量级一致。

### 5.5 混杂因素

1. 地图大小和席位数同时决定间距和每个号的领土（见 5.3）。
2. 版本和角色混在一起：Va 没有开局被封号，但 Va 的间距中位数也最大。
3. squad8 没有录像，{{h4.byVersion.g09.early.k}} 个号只有日志口径。

### 5.6 结论

按统筹定义，“内圈开局饿死”在 squad10 **不构成主要问题（E2 级否定）**；在 c110 是少数房间的真实个例（有这种号的房间 {{h4.rooms.squad20.withEarly|w}}）。“间距越小越差”在房间之间主要是地图大小的效应。

## 6. 假设 ⑤：前线留守底线 `oppFloorCap` 在被集火时的脆弱性

**口径。** 全部用引擎真值。分析单位是“号×90 拍窗口”：t≥1500、号活着、领土 ≥200。对每个窗口记：起点密度；之后 90 拍内真人对它的出兵量和出兵的真人数；它自己的进攻出兵量；之后 360 拍内有没有阵亡。“受攻比”= 90 拍内真人对它的出兵量 ÷ 它的起点余额。“集火窗口”= 出兵的真人 ≥2 个且受攻比 ≥0.25。squad10 共 {{h5.squad10.windows|n}} 个窗口（{{h5.squad10.bots}} 个号，{{h5.squad10.games}} 局），squad20 共 {{h5.squad20.windows|n}} 个窗口（{{h5.squad20.games}} 局）。

### 6.1 生死由受攻强度决定

{{TABLE:h5_humn}}

{{TABLE:h5_ratio}}

### 6.2 留守线密度有没有保护作用

集火窗口按起点密度分：

{{TABLE:h5_focus_dens}}

密度高的档阵亡率低一些，但同时受攻比也低。把受攻比固定住再看密度：

{{TABLE:h5_ratio_dens}}

同样的受攻比下，密度更高的号并不更安全；受攻比 1 以上时反而是密度 <60 的一档阵亡率低一些（受攻比是按余额归一的，余额少的号同样的受攻比对应的绝对兵力也少）。只看集火开始时还站在留守线上的窗口：

{{TABLE:h5_atfloor}}

squad10 站在线上的集火窗口里，受攻比不到 0.5 时阵亡 {{h5.squad10.focus.atOrAboveFloor.0|w}}，受攻比 ≥1 时阵亡 {{h5.squad10.focus.atOrAboveFloor.2|w}}。集火窗口里真人出兵折合到被打号每格领土上的量，中位 {{h5.squad10.focus.humPerLand.med|f1}} 兵/格，P75 {{h5.squad10.focus.humPerLand.p75|f1}}，{{h5.squad10.focus.humPerLandGtFloor|w}} 的窗口超过了本版本的 `oppFloorCap`。

更重要的是，集火窗口里 {{h5.squad10.focus.belowFloorShare|w}} 在开始时密度已经低于本版本的 `oppFloorCap`：

{{TABLE:h5_ver}}

Vb（留守线 {{meta.floorCap.Vb}}）在密度 ≥60 的两档阵亡率低于 Va（留守线 {{meta.floorCap.Va}}），但 Va 这两档的窗口很少（见上表），而且两个版本的时段、对手和受攻比分布都不同（集火窗口的受攻比中位：Va {{h5.squad10.focus.ratioByVer.Va.med|f2}}，Vb {{h5.squad10.focus.ratioByVer.Vb.med|f2}}）。把受攻比切成 7 档分层后再比：

{{TABLE:h5_cmh}}

分层之后，squad10 里 Vb 对 Va 的合并赔率比是 {{h5.squad10.cmh.version.or_mh|f2}}；“集火开始时在线上”对“在线下”的合并赔率比是 {{h5.squad10.cmh.floor.or_mh|f2}}（大于 1 表示在线上的反而更容易死）。窗口不是独立样本（同一个号、同一局会贡献多个窗口），p 值偏乐观，只能当方向参考。

集火窗口里号自己有没有出兵：

{{TABLE:h5_own}}

集火窗口里 {{h5.squad10.focus.passiveShare|w}} 的号基本没有出兵。没出兵的号阵亡率更高，但它们的起点密度也更低，这是“已经被打穿所以没兵可出”，不能读成“出兵能保命”。

### 6.3 阵亡是怎么发生的

{{TABLE:h5_deaths}}

对每次阵亡往回找最后一张密度还在留守线上的快照：

{{TABLE:h5_path}}

{{TABLE:h5_fast}}

squad10 的阵亡里，{{h5.squad10.path.neverAbove|wp}} 的号从 t=630 起就没到过留守线密度，{{h5.squad10.path.slow|wp}} 是掉到线下之后又拖了 720 拍以上才死，{{h5.squad10.path.fast|wp}} 是 720 拍内从线上到死。“快”的这部分里，真人对它的出兵量中位是它在线上那一刻余额的 {{h5.squad10.path.fastHum.med|f2}} 倍；自己把余额的一半以上打出去的占 {{h5.squad10.path.fastAtkGe50|wp}}，其间有同拍清仓批的占 {{h5.squad10.path.fastStackDump|wp}}。

### 6.4 领先局

统筹的定义是日志里 `peakPrimaryTeamShareSeen ≥ 35%`。这个定义有两个问题：日志只在我方号阵亡或结算时才打印队伍份额，会漏；35% 这个门槛不看队伍数，两队局里 35% 是落后。用引擎逐 90 拍的队伍领土重算：

{{TABLE:h5_lead_def}}

按“份额 ≥35% 且当时是全场领土最多的队”算，squad10 真正领先过的房间是 {{h5lead.byCohort.squad10.rank1.n}} 间，其中输掉 {{h5lead.byCohort.squad10.rank1.loss}} 间。份额到过 35% 但从没当过第一的房间有 {{h5lead.byCohort.squad10.neverRank1.n}} 间，其中 {{h5lead.byCohort.squad10.neverRank1.twoTeam}} 间是两队局，{{h5lead.byCohort.squad10.neverRank1.loss}} 间输了；把它们算成“领先后崩盘”是口径造成的。

领先后输掉（或结局未知）的房间，从领先时的份额峰值往后看 {{h5lead.window}} 拍：

{{TABLE:h5_lead_rows}}

“掉的地里我方号占比”为负表示主队在掉地的同时我方号的领土在涨。squad10 输掉的 {{h5lead.byCohort.squad10.loss.n}} 间里，峰值时我方号占主队领土的中位是 {{h5lead.byCohort.squad10.loss.ourTerrShare0.med|pct}}，掉的地里我方号占的中位是 {{h5lead.byCohort.squad10.loss.oursShareOfDrop.med|pct}}；我方号掉地比例超过其领土占比的只有 {{h5lead.byCohort.squad10.loss.oursOverProportional|w}} 间。这 1800 拍里我方号领土变化的中位是 {{h5lead.byCohort.squad10.loss.ourTerrChange.med|pct}}，野人队友是 {{h5lead.byCohort.squad10.loss.wildTerrChange.med|pct}}。从峰值到主队份额跌破 20% 中位用了 {{h5lead.byCohort.squad10.loss.peakToBelow20.med|n}} 拍。样本只有 {{h5lead.byCohort.squad10.loss.n}} 间，只能当个例读。

### 6.5 混杂因素

1. **反向因果。** 密度低本身就是被打的结果；“死前密度低于留守线”（{{h5.squad10.deaths.belowFloor|w}}）不说明留守线设低了。
2. **领先局的定义。** 见 6.4；用统筹口径统计“领先后崩盘”会把大量从未领先的两队局算进来。
3. **队友。** 主队里野人队友的数量和去留不受我方控制；squad10 领先后输掉的房间里，掉的地一半以上来自野人队友的是 {{h5lead.byCohort.squad10.loss.wildMajorityOfDrop|w}}。
4. **窗口重叠。** 同一个号连续几个窗口都被集火时会被重复计数；阵亡表是按号去重的。
5. **squad20 只有 {{h5.squad20.games}} 局有 t≥1500 的引擎真值。**

### 6.6 结论

- “受攻比决定生死”：**成立，E2**。
- “`oppFloorCap` 这条线在集火下脆弱，是崩盘的原因”：**未获支持**。被集火的窗口里 {{h5.squad10.focus.belowFloorShare|wp}} 在集火开始时已经在线下；全部阵亡里“在线上被集火后 360 拍内死”的只有 {{h5.squad10.deaths.afterFocusAtFloor|w}}，其中受攻比 ≥1 的 {{h5.squad10.deaths.afterFocusAtFloorRatio1|w}}。
- “领先局崩盘”：按引擎真值重新定义后只有 {{h5lead.byCohort.squad10.loss.n}} 间输局，**E1**。

## 7. 假设 ⑥：`squad20` 拆队与和平投票效应

### 7.1 拆队后的胜负

{{TABLE:h6_split}}

“任一有我方号的队获胜”的比例很高，但它的随机期望也同样高：20 个号撒到了房间里的大多数队伍上。这个指标不能当成绩看。

按“一个队上有几个我方号”分层，看这个队赢不赢：

{{TABLE:h6_dose}}

{{TABLE:h6_primsec}}

每一档的实际胜率都落在随机期望附近，没有“我方号越多的队越容易赢”的剂量效应。样本小，功效低：这张表排除不了中等大小的效应，只能说没看到。

### 7.2 互殴和跨队协助

- 引擎真值（{{h6.squadAttacks.games}} 个有录像的组队房间，其中录像 ≥1500 拍的 {{h6.squadAttacks.gamesGe1500}} 个）：我方号对同编队异队号的出兵共 {{h6.squadAttacks.outSquad|n}} 兵，占“对真人出兵”的 {{h6.squadAttacks.squadShareOfHumanDirected|pct}}。
- t≥1500 的 {{h6.windows20.n|n}} 个号×窗口里，被同编队号出兵的 {{h6.windows20.withSquadAttack|w}}，被其他真人出兵的 {{h6.windows20.withHumanAttack|w}}。
- {{h6.deaths20.n}} 次阵亡里，头号进攻者是同编队号的 {{h6.deaths20.killerOur|w}}。
- 日志里的 `[HL-ASSIST]`：能判定队伍的 {{h6.assist.crossShare.n}} 次里跨队的占 {{h6.assist.crossShare|w}}（另有 {{h6.assist.unknown}} 次判定不了）。也就是说“协助”多数是在帮别的队上的同编队号。

### 7.3 和平投票

{{TABLE:h6_peace}}

- `[HL-PEACE]` 总共 {{h6.peaceLogTotal}} 行（“initiated peace vote” {{h6.peaceLineKinds.initiated}} 行，“voted YES” {{h6.peaceLineKinds.votedYes}} 行），全部出现在上面 {{h6.peaceLogBundles}} 个包里，其中有录像的 {{h6.peaceLogBundlesWithReplay}} 个；其余 {{h6.squad20NoPeace}} 个 squad20 对局包没有一行。
- 有录像的局里，我方号发起或参与和平投票的指令是 {{h6.peaceOursInReplay}} 条（同局其他真人：squad10 房间 {{h6.peaceReplay.squad10.callWild}} 次发起、{{h6.peaceReplay.squad10.voteWild}} 次投票；squad20 房间 {{h6.peaceReplay.squad20.callWild}} 次、{{h6.peaceReplay.squad20.voteWild}} 次）。
- 仓库里的 `{{h6.peaceCode.file}}`，`tryPeaceVote` 定义在第 {{h6.peaceCode.defLine}} 行，第一句（第 {{h6.peaceCode.guardLine}} 行）是 `if (this.findBossId(g) < 0) return;`，没有 Boss 队友就不会投。而出生日志里没有任何一局有 Boss（`bossDist` 全是 −1）。所以这 {{h6.peaceLogBundles}} 个包要么当时跑的不是仓库里这份代码，要么开局后房间里出现了名字匹配 Boss 规则的队友；没有录像，无法分辨。**请统筹核对最后一个有和平日志的包 {{h6.peaceLast.mid}}（开局 {{h6.peaceLast.timeUtc}}）和它之后的第一个 squad20 包 {{h6.peaceNext.mid}}（开局 {{h6.peaceNext.timeUtc}}）之间是否换过版本。**

### 7.4 混杂因素

1. squad20 的录像覆盖（见 §1）：互殴的数字只来自 {{h6.squadAttacks.gamesGe1500}} 个房间的中后期和其余房间的开局段。
2. “主队”只是我方号最多的队，里面仍有野人队友；主队输赢不等于我方号的表现。
3. 组队房间的队伍数从 {{h6.roomTeams.min}} 到 {{h6.roomTeams.max}} 不等，胜率必须和 1/队伍数比，不能直接横向比。

### 7.5 结论

- “拆队导致互殴内耗”：**未获支持，E2**（互打占比 {{h6.squadAttacks.squadShareOfHumanDirected|pct}}，头号击杀者是同编队号的 {{h6.deaths20.killerOur|w}}）。
- “我方号多的队更容易赢”：**没看到，E2（功效低）**。
- “和平投票 / 跨队和平锁”：{{h6.peaceLast.mid}} 之后没有任何记录，**无法检验（E0）**。

## 8. 附：执行层同拍叠单（审计中新增）

统筹 0003 号广播的事实 3 转述了 R03 / R05 的“反序清仓批”（原文口径：13 局检出 52 个）。这里在全部 {{census.engine.games}} 份录像上复核，现象成立，全量统计如下。

**机制。** 引擎每 7 拍收一轮服务器指令。客户端落后时会在一帧里把积压的几轮连续跑完，策略在这几轮的每个决策拍都照常发令，这些指令在同一轮被服务器收下、同一拍落地；录像里同一个号同一拍最多落地 {{hx.stackHist.ours_squad10.max}} 条。多条进攻指令各按 `pct` 取当时余额的一部分，叠起来一拍可以打掉大半余额（见下面第二张表）。

{{TABLE:x_stack}}

{{TABLE:x_dumps}}

{{TABLE:x_pergame}}

squad10 里叠单占比在输的房间明显更高。这有可能是因果，也有可能只是“局势差的局里客户端更卡 / 活得短的局开局段占比更大”，本审计不下判断。

`DROP30`（相邻两张快照之间余额跌 30% 以上）事件，按引擎真值归因。注意 `anomalies.json` 的 `drop30Events` 每个包最多只列 30 条：{{hx.drop30All.bundles}} 个包里 {{hx.drop30All.firstThirtySorted}} 个的列表正好是“按号名、再按拍号排序后的前 30 条”，{{hx.drop30All.truncated}} 个包被截断，这些包里有 `DROP30` 的 {{hx.drop30All.botsWithDrop|n}} 个号中 {{hx.drop30All.botsHidden}} 个一条都没列出来（名字靠后的号）。发现集全量是 {{hx.drop30All.full|n}} 条，列出来的只有 {{hx.drop30All.listed|n}} 条。这里用的是从 `traj.csv` 重算的全量（{{hx.drop30All.countMatches}} 个包的条数和 `drop30Count` 一致）：

{{TABLE:x_drop30}}

squad10 中后期的 `DROP30` 里不是自己花的（挨打）只占 {{hx.drop30.0.defenceShare|pct}}，其余是自己花的，其中捐款最多。复盘时把 `DROP30` 默认当成“被打”会错。逐事件的归因在质检（M3）时可以直接拿来对账。

叠批清仓之后的阵亡率：

{{TABLE:x_after}}

落后有多严重，可以用成交捐款“日志下单拍 → 录像落地拍”的间隔来量（正常情况下一条指令在下单后 7–21 拍内落地）：

{{TABLE:x_lag}}

**这是其余几条假设共同的混杂项。** 一个号“突然没兵了”“在线上被打死”“下了单没成交”，都可能先是执行层的问题。

## 9. 需要统筹或其他复盘员跟进的事项

1. **{{h6.peaceLogs.0.mid}}–{{h6.peaceLast.mid}} 的和平投票日志与仓库代码不一致**（§7.3），需要版本线确认。
2. **squad20 的录像覆盖**（§1）：{{census.byCohort.squad20.replayEmpty}} 份只有出生阶段。做 B 组真引擎复盘的同事请先看录像末拍；双审局里 {{census.dualNoMidgame|list}} 没有中后期引擎真值可对。
3. **“领先局”的口径**（§6.4）：建议复盘员引用领先局时注明用的是日志口径还是引擎口径，并排除两队局里从未领先的情形。这是分析口径，不是策略参数。
4. **R03 报的 `isNoFullSend` 7 拍窗口误锁**没有审计：日志不打印这个状态，需要把策略代码接进引擎重放才能数，超出本里程碑的范围。它和 §8 的落后追帧直接相关（指令晚到会让“7 拍内余额没按预期下降”），建议 R03 / R04 用引擎重放定量。
5. **c110 没成交的捐款里配额只能解释 {{h1.verdict.c110.quotaShare|pct}}**（§2.3），其余原因未定位。
6. 引擎探针的输出（每局我方指令、全场捐款、号×窗口的进出兵、阵亡归因）可按 §10 重新生成，M3 质检会用它重算复盘员填写的兵力数字。

## 10. 复现

```bash
cd c136-review/agents/R10/scripts
export PATH=/exec-daemon:$PATH
python3 audit_data.py discovery                         # 生成引擎任务清单 out/engine/jobs-discovery.json
# 真引擎重放（每次最多跑 75 秒，重复执行直到输出 left=0；结果在 out/engine/discovery/，不入库）
HEAVY_TIMEOUT=110 bash ../../../tools/run-heavy.sh node engine_probe.cjs ../out/engine/jobs-discovery.json ../out/engine/discovery --budget 75
python3 audit_hypotheses.py                             # 写 out/hypothesis-audit.json 和本报告
```

脚本：`audit_hypotheses.py`（检测与出表）、`audit_data.py`（数据层与引擎公式）、`engine_probe.cjs`（引擎探针）、`replay.py`（录像解码）、`stats.py`、`baseline_full.py`、`c136lib.py`。
