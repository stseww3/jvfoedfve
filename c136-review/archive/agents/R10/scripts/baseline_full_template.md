# R10 · M1 · 160 局全量分层基线（BASELINE-FULL）

> 本文件由 `scripts/baseline_full.py` 按模板 `scripts/baseline_full_template.md` 生成，文中每个数字都来自 `out/baseline-full.json`，改数字请改脚本后重跑，不要手改本文件。
> 验证集（37 局）在本文件里只出现合计数，逐局明细在 `out/baseline-full-internal.json`、`out/rooms/rooms-validation-internal.json`、`out/rooms/physical-rooms-internal.json`，仅 R10 与 c136 使用。
> 本报告只做统计与证据核实，不提任何策略参数建议。

## 0. 结论

1. **带 `[APEX]` 标签、整队进同一个队的 squad10，胜率远低于随机水平；按队伍数、按发现集和验证集、按策略版本分层后都如此。** 卡片口径是 {{card.all160.byCohort.squad10.prim|rate}}，随机期望（各局 1/队伍数 的平均）是 {{card.all160.byCohort.squad10.base_mean|pct}}。按房间重新判定结局后是 {{room.tagged.squad10.all.main.rate|rate}}，随机期望 {{room.tagged.squad10.all.main.excess.mean_base|pct}}，超额 {{room.tagged.squad10.all.main.excess.excess_per_game|spp}}，精确双侧 p = {{room.tagged.squad10.all.main.excess.p_two_sided|p}}；折成赔率，是随机水平的 {{room.tagged.squad10.all.logit.odds_ratio|f2}} 倍（95% 区间 {{room.tagged.squad10.all.logit.or_lo|f2}} ~ {{room.tagged.squad10.all.logit.or_hi|f2}}）。两队局最差：{{room.tagged.squad10.byT.T=2.main.rate|rate}}，随机期望 50%。发现集和验证集一致（{{room.tagged.squad10.bySplitSet.discovery.main.rate|rate}} 与 {{room.tagged.squad10.bySplitSet.validation.main.rate|rate}}），三个策略版本 Va、Vb、Vc 都低于随机（§4.2）。
2. **squad20 的 68.0% 和 24.0% 之差是「占队数」造成的，不是实力。** squad20 的号不带标签，被引擎逐个分进各队，平均每局占了 {{squad20.card.mean_d|f2}} 个队（平均队伍数 {{squad20.card.mean_T|f2}}）。只要其中任何一个队赢，`anyBotWon` 就是真；`primaryTeamWon` 只看号最多的那一个队。纯随机时两者的期望分别是 {{squad20.card.exp_any_null|pct}} 和 {{squad20.card.exp_prim_null|pct}}，相差 {{squad20.card.gap_null|pp}}；实际相差 {{squad20.card.gap_obs|pp}}。把 squad20 的号按「房间 × 队伍」拆开看，有它的号的队赢了 {{squad20.team.all.teamUnits.rate|rate}}，随机期望 {{squad20.team.all.teamUnits.excess.mean_base|pct}}，没有差别（p = {{squad20.team.all.teamUnits.excess.p_two_sided|p}}）。
3. **squad20 的数据说明不了 c110 比 c116 强还是弱。** 同一个房间里，一个队每多一个 squad20 的号，赢的赔率乘以 {{squad20.team.all.condLogit.kOnly.oddsPerBot|f2}}（β 的 95% 区间 {{squad20.team.all.condLogit.kOnly.lo|f3}} ~ {{squad20.team.all.condLogit.kOnly.hi|f3}}，{{squad20.team.all.condLogit.kOnly.nRooms}} 个房间）。这个区间既包含「没有影响」（β = 0），也包含 squad10 的亏损摊到每个号上的幅度（平均 {{room.tagged.squad10.all.logit.meanBots|f1}} 个号把赔率压到 {{room.tagged.squad10.all.logit.odds_ratio|f2}} 倍，相当于每个号乘 {{room.tagged.squad10.all.logit.perBotOdds|f2}}，β = {{room.tagged.squad10.all.logit.perBotBeta|f3}}）。
4. **发现集 123 局上，第 630 拍和第 1530 拍的编队领土份额对最终胜负没有检出预测力。** squad10 的 AUC 是 {{process.squadShare.squad10.630.auc.auc|f2}} 和 {{process.squadShare.squad10.1530.auc.auc|f2}}，95% 区间都跨过 0.5，按队伍数分层后也一样（§5.1）。胜局只有 {{process.squadShare.squad10.630.nWin}} 个，区间很宽，所以这是「没检出」，不是「证明无关」。
5. **疑似拒单率和内陆高密度快照数在三个编队之间差别很大，但两者和胜负的关系方向相反，而且都受对局时长影响，不能直接当作原因。** 疑似拒单率合并值：squad10 为 {{process.anomalies.squad10.rejRatePooled|rate}}，squad20 为 {{process.anomalies.squad20.rejRatePooled|rate}}，squad8 为 {{process.anomalies.squad8.rejRatePooled|rate}}。squad10 的胜局拒单率更低（AUC {{process.anomalyVsOutcome.squad10.rejRate.auc|f2}}），而胜局的内陆高密度快照反而更多（AUC {{process.anomalyVsOutcome.squad10.boxedPerLateSnap.auc|f2}}），见 §5.2。
6. **卡片上的标签有一批需要更正或加注**（§6）：{{derived.nonTeamBundles|list}} 不是组队局；{{derived.noPlayDiscovery|list}} 我方的号全部掉线或没有结算行，没有任何结局信息；{{derived.multiRoomDiscovery|list}} 一个包里装了两到三个房间；A057 卡片记为负，实际所在队获胜。验证集里同类情况的个数见 §6.1。
7. **验证集不完全独立。** 37 个验证包里有 {{quality.physical.nValidationBundlesSharingWithDiscovery}} 个和发现集的某个包是同一个物理房间（一个是 squad10 视角，一个是 squad20 视角）。名单在内部文件里。做验证集复现时，这 {{quality.physical.nValidationBundlesSharingWithDiscovery}} 局不能算独立证据。

## 1. 口径和名词

- **卡片口径**：直接用 `manifest_all_internal.jsonl` 里每局的 `actualTeams`、`distinctSquadTeams`、`outcome.anyBotWon`、`outcome.primaryTeamWon`。§2 和 §3.1 用这个口径，是任务卡要求的原样统计。
- **房间口径**：我从 `in_game.log` 和 `results.json` 重新还原每个号（按改名链和座位号 `me`），再按（地图面积、房间真人数、开局时刻）把一个包拆成房间，逐个房间判定队伍数和结局。拆房规则：同一个包里，结算行反推的开局时刻相差 1.6 秒以内算同一个房间。§3.2 ~ §3.4、§4 和 §5 用这个口径。
- **T（队伍数）**：房间里实际的队伍数。优先用结算行 `teamTotals` 里见到的队号个数；结算行见到的队比引擎规则算出的少时（开局很久之后才有第一条结算行、已有队被灭），用引擎规则 `名义队伍数 = mode + 2，再按最大同标签人数下调`。
- **随机期望**：一个队在 T 个队里赢的机会按 1/T 算。一组局的随机期望是各局 1/T 的平均。
- **超额**：实际胜率减随机期望。**精确 p**：把每局看成成功概率 1/T 的独立试验，胜局数的精确分布（泊松二项）下的双侧 p 值。
- **区间**：胜率后面方括号里是 Wilson 95% 置信区间。
- **d（占队数）**：这一局里我方的号分布在几个不同的队里。卡片字段是 `distinctSquadTeams`。
- **结局的五种取值**（房间口径）：
  - 胜 / 负：结算行里有终局行（`end`），或同一物理房间里另一个包有终局行，能确定赢的是哪个队。
  - 推定负：没有终局行，最后一条带队伍份额的结算行里，本队不是第一名而且份额低于 20%。
  - 推定胜：没有终局行，最后一条结算行里本队第一而且份额不低于 50%。
  - 未知：不满足以上任何一条。
  - 推定规则的准确度在 §4.3 用「结局已知」的房间校准过。
- **编队房间 / 散号房间**：一个包拆出的房间里，我方号数不少于 {{meta.mainRoomMinBots}} 个的叫编队房间，少于 {{meta.mainRoomMinBots}} 个的叫散号房间（开局时被大厅分到别的房间的零星几个号）。§4 的主表只算编队房间。
- **策略版本**（只有 squad10 换过版本，来源 `src/strategy/VERSION-TIMELINE.md`）：Va 是 2026-11-09T23:34:05Z 热更之前开的局，Vb 是热更之后到 2026-11-10T14:16:33Z 之前，Vc 是之后。A018 开局约 990 拍后被热更，按统筹的划分记在 Vb。

## 2. 卡片口径的分层统计（160 局）

### 2.1 按编队

{{TABLE:card_cohort}}

### 2.2 按编队 × 队伍数

{{TABLE:card_cohort_T}}

### 2.3 按编队 × 是否拆队

「未拆」是 `distinctSquadTeams == 1`，「拆队」是 `> 1`，「无队号」是 `== 0`（卡片上没有任何一个号有队号，见 §6）。

{{TABLE:card_cohort_split}}

### 2.4 按编队 × 队伍数 × 是否拆队

{{TABLE:card_full}}

### 2.5 按编队 × 发现集 / 验证集

{{TABLE:card_cohort_set}}

### 2.6 squad10 按策略版本

{{TABLE:card_version}}

## 3. squad20：为什么 `anyBotWon` 是 68.0%，`primaryTeamWon` 是 24.0%

### 3.1 卡片口径的分解

squad20 的 50 局里，`anyBotWon` 为 {{card.all160.byCohort.squad20.any|rate}}，`primaryTeamWon` 为 {{card.all160.byCohort.squad20.prim|rate}}，其中 {{squad20.card.nAnyNotPrim}} 局是「有号赢了，但赢的不是号最多的那个队」。

两个数的差完全来自拆队：如果 20 个号都在一个队里（d = 1），两个指标是同一件事，差为 0。squad10 就是这种情况，它的两个指标都是 {{card.all160.byCohort.squad10.prim|rate}}。队伍数 T 的作用是决定两个指标各自的水平：纯随机时 `primaryTeamWon` 的期望是 1/T，`anyBotWon` 的期望是 d/T。

按占队数 d 分：

{{TABLE:sq20_byD}}

按覆盖率 d/T 分：

{{TABLE:sq20_byCov}}

按队伍数分：

{{TABLE:sq20_byT}}

读法：两队局里 squad20 平均只占 {{squad20.card.byT.T=2.mean_d|f2}} 个队，`anyBotWon` 和 `primaryTeamWon` 相差 {{squad20.card.byT.T=2.gap|pp}}；三到四队时平均占 {{squad20.card.byT.T=3-4.mean_d|f2}} 个队，相差 {{squad20.card.byT.T=3-4.gap|pp}}；五队以上时平均占 {{squad20.card.byT.T>=5.mean_d|f2}} 个队，相差 {{squad20.card.byT.T>=5.gap|pp}}。`primaryTeamWon` 在每一层都和 1/T 接近或略低，`anyBotWon` 在每一层都跟着 d/T 走。

### 3.2 `anyBotWon` 比 d/T 还低的那部分是「没看到结局」造成的

卡片口径下 `anyBotWon` 的随机期望是 {{squad20.card.exp_any_null|pct}}，实际只有 68.0%（实际 {{squad20.card.any_excess.wins}} 局，随机期望 {{squad20.card.any_excess.expected|f1}} 局，p = {{squad20.card.any_excess.p_two_sided|p}}）。这不是 squad20 打得比随机差，而是卡片把没看到结局的局一律记成了没赢：

{{TABLE:sq20_accounting}}

看到了结局的 {{squad20.cardAccounting.winnerKnown.n}} 局里，`anyBotWon` 是 {{squad20.cardAccounting.winnerKnown.any|rate}}，按占队比例的随机期望是 {{squad20.cardAccounting.winnerKnown.expAnyCoverage|pct}}，两者一致。

### 3.3 按「房间 × 队伍」看：有 squad20 的号的队，赢的比例等于 1/T

把 squad20 的每个编队房间里我方占的每个队当成一个单位。共 {{squad20.team.all.summary.nRooms}} 个房间（{{squad20.team.all.summary.nWinnerKnown}} 个知道哪个队赢），{{squad20.team.all.summary.nBots}} 个号，其中 {{squad20.team.all.summary.nBotsTeamKnown}} 个知道队号，{{squad20.team.all.summary.nBotsTeamUnknown}} 个不知道（没有结算行，也没有捐款关系可推）。

{{TABLE:sq20_byK_all}}

结局没看到的 {{squad20.team.all.teamUnits.n}} − {{squad20.team.all.teamUnits.nResolved}} 个队如果全算负，胜率是 {{squad20.team.all.teamUnits.boundLo|pct}}；如果每个没看到结局的房间都再多算一个胜队，是 {{squad20.team.all.teamUnits.boundHi|pct}}；全部 {{squad20.team.all.teamUnits.n}} 个队的随机期望是 {{squad20.team.all.teamUnits.expectedAllUnits|pct}}。无论怎么算都在随机水平附近。

同一个房间内部比较各队（条件 logit：赢的那个队是哪个，和各队里 squad20 的号数 k 有没有关系）：

{{TABLE:sq20_logit_all}}

其它几个房间口径的数：
- 赢的队在我方占的队里：{{squad20.team.all.coverage.winnerAmongOurTeams|rate}}，随机期望 {{squad20.team.all.coverage.expected_mean|pct}}。
- 有号活到终局并拿到 `won`：{{squad20.team.all.coverage.anyBotWonRow|rate}}。
- 号最多的那个队赢（只算主队没有歧义的房间）：{{squad20.team.all.primary.rate|rate}}，随机期望 {{squad20.team.all.primary.excess.mean_base|pct}}，p = {{squad20.team.all.primary.excess.p_two_sided|p}}。squad20 有 {{reconcile.flagCounts.squad20.主队不确定}} 局的「主队」不确定：两个队的号数并列，或者队号未知的号多到足以改变谁最多。卡片的 `primaryTeamWon` 在这些局上取决于并列时怎么挑。

发现集单独算：

{{TABLE:sq20_byK_discovery}}

{{TABLE:sq20_logit_discovery}}

验证集单独算（只有合计）：

{{TABLE:sq20_byK_validation}}

### 3.4 squad10 和 squad20 同处一个房间的 {{sharedRooms.agg.nRooms}} 局

有 {{sharedRooms.agg.nRooms}} 个物理房间同时有 squad10 的包和 squad20 的包（{{sharedRooms.agg.nMixed}} 个涉及验证集，下表只列两边都是发现集的 {{quality.physical.nSharedDiscOnly}} 个）。

{{TABLE:shared_rooms}}

全部 {{sharedRooms.agg.nRooms}} 个房间里，{{sharedRooms.agg.nWinnerKnown}} 个知道哪个队赢：`[APEX]` 所在队赢了 {{sharedRooms.agg.aWon|rate}}（随机期望 {{sharedRooms.agg.aExpected|pct}}）；赢的队里有 squad20 的号的是 {{sharedRooms.agg.bOnWinner|rate}}（按占队比例的随机期望 {{sharedRooms.agg.bExpectedCoverage|pct}}）。这和上面的结论一致：squad20「总有号赢」是因为它几乎每个队都有号。另外，{{sharedRooms.agg.nBOnATeam}} 个房间里有 squad20 的号和 `[APEX]` 同队；这些房间里 `[APEX]` 队赢了 {{sharedRooms.agg.aWonWhenBOnTeam|rate}}。

## 4. squad10 和 squad8：房间口径的校正基线

### 4.1 主表

squad10 的 100 个包拆出 {{room.tagged.squad10.nRooms}} 个房间，其中 {{room.tagged.squad10.nNonTeam}} 个不是组队局，{{room.tagged.squad10.nNoPlay}} 个是我方的号全部掉线、没有任何结局信息（{{derived.nSq10NoPlayMain}} 个编队房间，其余是散号房间），{{room.tagged.squad10.nFragment}} 个是有结局信息的散号房间，余下 {{room.tagged.squad10.all.n}} 个编队房间进入主表。squad8 的 10 个包各是 1 个房间。

全员掉线的 {{derived.nSq10NoPlayMain}} 个编队房间不在主表里，因为不知道它们所在的队最后赢没赢。如果把它们全算成负，squad10 是 {{derived.sq10NoPlayAsLoss|rate}}。

「胜率上下界」把结局未知的房间分别全算负、全算胜。「只算确定结局」把推定胜、推定负也去掉，只留有终局行的房间；这一列偏高，因为被去掉的推定负几乎都是真的负（§4.3）。

{{TABLE:room_tagged}}

几点说明：
- 20 人房：大厅人多时被拆成若干个 20 人的房间。squad10 有 {{derived.seeded20Sq10Main.n}} 个编队房间是 20 人房，我方在里面有 {{derived.seeded20Sq10Main.minBots}} ~ {{derived.seeded20Sq10Main.maxBots}} 个号，其中 {{derived.seeded20Sq10Main.nT2}} 个房间的队伍数是 2，也就是每队 10 人、我方的号占了本队的大半甚至全部。这种房间 squad10 是 {{room.tagged.squad10.bySeeded20.seeded=20.main.rate|rate}}。
- 「我方号数占本队的比例」按 `我方号数 ÷ (房间真人数 ÷ 队伍数)` 估算。三档是等宽分档。第一档（我方只占本队的小部分）是 {{room.tagged.squad10.byOwnFrac.<1/3.main.rate|rate}}，和随机期望 {{room.tagged.squad10.byOwnFrac.<1/3.main.excess.mean_base|pct}} 没有差别，后两档远低于随机；但第一档只有 {{room.tagged.squad10.byOwnFrac.<1/3.n}} 个房间，只能当线索。
- 散号房间的结局多数未知，不并入主表；并入后的结果在最后一行，结论不变。

### 4.2 squad10 按策略版本

{{TABLE:room_version}}

三个版本的胜率都低于随机期望。Va 和 Vc 的房间数太少（{{room.tagged.squad10.byVersion.Va.n}} 和 {{room.tagged.squad10.byVersion.Vc.n}}），区间很宽，现有数据不能区分三个版本谁好谁差。

### 4.3 推定结局的校准

用结局已知的房间检查推定规则：我方某个号阵亡那一刻本队的份额，对应本队最后赢没赢。

{{TABLE:calibration}}

{{TABLE:calibration_rules}}

所以「推定负」当作负来算，出错的比例是 {{derived.lossLikelyErr|rate}}；主表里 squad10 有 {{room.tagged.squad10.all.counts.LOSS_LIKELY}} 个推定负，按这个比例预期其中 {{derived.expWinsAmongLossLikelySq10|f1}} 个实际是胜。「推定胜」的准确率是 {{derived.winLikelyAcc|rate}}，主表里没有用到推定胜。

## 5. 过程指标（发现集）

### 5.1 第 630 拍和第 1530 拍的编队领土份额，对最终胜负的预测力

份额 = 该拍我方在这个房间的全部号的领土之和 ÷ 地图陆地面积。squad20 用的是号最多的那个队里我方号的份额，并且只算主队没有歧义的房间。结局用房间口径（含推定）。AUC 是「随机取一个胜局和一个负局，胜局份额更高的概率」，0.5 表示没有区分力；区间是 2000 次自助抽样（种子 136）。

{{TABLE:process_share}}

{{TABLE:process_share_median}}

只看 squad10 的 Vb 版本（排除版本混杂）：

{{TABLE:process_share_vb}}

squad20 换一种看法，按「房间 × 队伍」，看这个队里我方每个号的平均份额能不能预测这个队的胜负：

{{TABLE:process_share_sq20team}}

结论：squad10 和 squad20 的所有 AUC 区间都包含 0.5（squad8 只有 1 个胜局，它的 AUC 没有统计意义，列出只为完整）。squad10 胜局和负局在第 630 拍的份额中位数分别是 {{process.squadShare.squad10.630.share_win.median|pct2}} 和 {{process.squadShare.squad10.630.share_loss.median|pct2}}，第 1530 拍是 {{process.squadShare.squad10.1530.share_win.median|pct2}} 和 {{process.squadShare.squad10.1530.share_loss.median|pct2}}，没有胜局更高的迹象。

### 5.2 疑似拒单和内陆高密度快照

两个计数取自卡片的 `anomaliesSummary`；我从 `events.csv` 和 `traj.csv` 重数了一遍，160 张卡片里 {{process.recount.nMismatch}} 张对不上。

疑似拒单（`likelyRejectedTransfers`）的判定是启发式的：一次转兵之后 35 拍内同一个号又发了一次，而且余额没有降下来。它不等于引擎真的拒绝了这笔转兵。统筹已经给了从 `replay.txt` 解真账本的工具（`src/tools/donation_ledger.mjs`），M2 审计假设 ① 时我会用真账本重算，这里先按卡片字段给分布。

{{TABLE:process_rej}}

内陆高密度快照（`boxedHighDensSnapshots`）的定义是：`t ≥ 1500`、没有敌方邻居（`nb = 0`）、没有中立邻居（`neut = 0`）、密度 `dens ≥ 95` 的 90 拍快照。

{{TABLE:process_boxed}}

这两个指标和房间结局的关系（发现集，只用单房间的包；squad20 只算主队没有歧义的）：

{{TABLE:process_anom_outcome}}

读这张表要注意两点。第一，内陆高密度快照在胜局里更多，这和「内陆号憋死导致输」的直觉相反；原因很可能是定义本身：队伍占优时内圈的号四周都是队友，自然满足「没有敌方邻居、没有中立邻居、密度高」，所以这个计数里混着「被自己人围住的健康内陆号」。第二，两个指标都随我方的号活了多久而变：squad10 胜局里每个号在 1500 拍之后的快照数中位数是 {{process.anomalyVsOutcome.squad10.lateSnap_win.median|f1}}，负局是 {{process.anomalyVsOutcome.squad10.lateSnap_loss.median|f1}}（表里「号活得多久」那一行）。所以这张表只能说明「现有的两个计数不能直接当病因」，不能说明拒单或憋死无害。逐条因果放在 M2 审。

## 6. 卡片口径和房间口径的对账

### 6.1 各类差异的个数（160 局，按主房间）

{{TABLE:reconcile_counts}}

各项含义：
- **非组队局**：`HL-GAME-INIT` 的 mode 不是组队模式，结算行里没有队伍份额。发现集是 {{derived.nonTeamBundles|list}}。卡片上这些局的 `actualTeams` 写的是 2，其中 A073、B030 还被记成了胜。它们不该进组队胜率的分母。
- **全员掉线无结局**：我方在这个房间的号全部以 `left` 结束或根本没有结算行，因此没有队号，也没有任何带队伍份额的结算行。按统筹的说明，`left` 是 worker 断线或连续超时被踢出，不是被打死。发现集是 {{derived.noPlayDetailDiscovery|list}}，验证集另有 {{derived.nNoPlayValidation}} 局。卡片把它们记成队伍数为 2 的负局；它们的真实队伍数和结局都不知道。
- **多房间**：一个包里的号分在两到三个房间里（大厅拆房，或前后两场）。发现集是 {{derived.multiRoomDiscovery|list}}，验证集另有 {{derived.nMultiRoomValidation}} 局。卡片把几个房间的队号、结局混在了一起。
- **队伍数不同**：我判定的主房间队伍数和卡片的 `actualTeams` 不同。发现集是 {{derived.tDiffDiscovery|list}}，验证集另有 {{derived.nTDiffValidation}} 局。
- **主队胜负不同**：发现集是 {{derived.outcomeFlipDiscovery|list}}，验证集 {{derived.nOutcomeFlipValidation}} 局。A057：`[APEX]` 的号在队 {{derived.a057.team}}，同一物理房间里 B038 的终局行显示队 {{derived.a057.winner}} 获胜；A057 自己有 {{derived.a057.nEndRowsOwn}} 条终局行，所以卡片记成了负。其余几局都是 squad20，原因是「主队」的定义有歧义（号数并列、队号未知的号太多，或把两个房间的号混在一起数）。
- **结局未观察到**：发现集是 {{derived.outcomeUnknownDiscovery|list}}。
- **结局为推定**：没有终局行，按 §1 的规则推定。发现集共 {{reconcile.flagCountsBySplit.discovery.结局为推定}} 局：{{derived.likelyOutcomeDiscovery|list}}。
- **同标签分在两队**：{{derived.clanConflictDetail|list}}。同一个 `[Nope]` 标签的号在同一个房间里出现在两个队，和「同标签整体进一个队」的引擎规则不符，原因我还没有查清。
- **主队不确定**：只出现在 squad20。发现集共 {{reconcile.flagCountsBySplit.discovery.主队不确定}} 局：{{derived.primaryUncertainDiscovery|list}}。

### 6.2 发现集里有实质差异的局

「结局为推定」和「主队不确定」单独出现时不列在这张表里（名单见上）。

{{TABLE:reconcile_discovery}}

## 7. 数据质量

### 7.1 号的还原和队号来源

{{TABLE:quality_identity}}

- 「号码独立校验」：用名字链或日志尾部指纹对上结算行的号，再比对结算行的 `meId` 和 `HL-GAME-INIT` 的 `me` 是否一致。没有一个对不上。
- squad20 有 {{quality.byCohort.squad20.nRenamed}} 个号在局内换过日志名字（最多的一个号换了 {{quality.byCohort.squad20.namesPerBot.max|f0}} 个名字），{{quality.byCohort.squad20.events.none}} 个号没有结算行。名字链到座位号的对照表在 `out/rooms/identity-map-discovery.csv`。
- squad20 的队号有 {{quality.byCohort.squad20.teamHow.unknown}} 个推不出来。我只用三种来源：结算行的 `teamMine`、同标签规则（只用于带标签的编队）、捐款关系（`HL-DONATE` / `HL-DISPATCH`，引擎只允许捐给活着的队友）。核对结果：两端队号都由结算行给出的捐款号对，squad10 同队 {{quality.byCohort.squad10.allyEdges.donateSame}} 对、跨队 {{quality.byCohort.squad10.allyEdges.donateCross}} 对，squad20 同队 {{quality.byCohort.squad20.allyEdges.donateSame}} 对、跨队 {{quality.byCohort.squad20.allyEdges.donateCross}} 对。`HL-ASSIST` 不能用来推队号：c110 的「squad-rescue poke … for ally=…」会把不在同一个引擎队里的同编队号当成 ally，两端队号都已知的号对里，同队 {{quality.byCohort.squad20.allyEdges.assistSame}} 对，跨队 {{quality.byCohort.squad20.allyEdges.assistCross}} 对。这条留给 M2 假设 ⑥。

### 7.2 快照缺失和耗时

{{TABLE:quality_lag}}

`traj.csv` 的 `skip` 列在所有号上都是 0，所以缺失的 90 拍快照不是卡顿跳拍。c110 的 `act(g)` 里，写 `[HL-TICK]` 的那一行排在几处提前 `return` 之后，这一拍如果提前返回就不会写快照。缺失率 squad20 是 {{quality.byCohort.squad20.missRate.rate|pct}}，squad8 是 {{quality.byCohort.squad8.missRate.rate|pct}}，squad10 接近 0。这给 M2 假设 ① 提供了一个可数的把手。

### 7.3 其它完整性事实

- 局内计数器被清零（策略在局内被重新初始化）：{{derived.resetsDiscovery|list}}。A018 对应 Va → Vb 的热更时刻；G01 的原因未知；B027 是同一个日志名字在第 5400 拍之后被另一个房间的号复用。
- 物理房间：160 个包共 {{quality.physical.nPhysicalRooms}} 个物理房间，其中 {{quality.physical.nShared}} 个同时出现在两个包里（{{quality.physical.nSharedDiscOnly}} 个两边都是发现集，{{quality.physical.nSharedMixed}} 个一边发现集一边验证集）。
- 开局时刻的间隔（同一个包里、同一张地图同样真人数的相邻结算行）：小于 0.5 秒的 {{derived.nStartGapLt05}} 对，0.5 ~ 1.6 秒的 {{derived.nStartGapBetween}} 对，1.6 秒以上的 {{derived.nStartGapGe16}} 对。拆房阈值取 1.6 秒。
- 20 人房共 {{quality.seeded20.nRooms}} 个，分布在 {{quality.seeded20.nBundles}} 个包里。squad10 在这些房间里的号数中位数是 {{quality.seeded20.byCohort.squad10.ourBots.median|f1}}，squad20 是 {{quality.seeded20.byCohort.squad20.ourBots.median|f1}}（最多 {{quality.seeded20.byCohort.squad20.ourBots.max|f0}}）。

## 8. 对我之前 alert（`outbox/0002-alert-bundle-integrity.md`）的两处更正

- 第 4 条：全员掉线、没有任何结局信息的包，发现集是 {{derived.noPlayDiscovery|list}}（B042 的房间划分见 §6.2 的表），验证集另有 {{derived.nNoPlayValidation}} 个。A002 不属于这一类：它的 {{derived.a002.nBots}} 个号里有 {{derived.a002.nLeftEarly}} 个在 2000 拍之前离场，但留下了带队伍份额的结算行，结局是推定负。
- 第 6 条：我当时写「20 人房里大多是我们自己的 A 组和 B 组互相打」，这句话不成立。{{quality.seeded20.nRooms}} 个 20 人房里只有 {{quality.seeded20.nSharedAB}} 个同时有 squad10 和 squad20 的号（§3.4 表的第一行）。正确的说法是：20 人房是大厅拆出来的并行房间，我方一个编队在里面的号数中位数是 {{quality.seeded20.byCohort.squad10.ourBots.median|f1}}（squad10）和 {{quality.seeded20.byCohort.squad20.ourBots.median|f1}}（squad20）；对不带标签的 squad20，这意味着同编队的号被分到对立的队里；对带标签的 squad10，情况见 §4.1 的说明。

## 9. 局限

- 胜局太少：squad10 的编队房间里只有 {{room.tagged.squad10.all.counts.WIN}} 个胜，squad8 只有 1 个。凡是拿胜局和负局做对比的统计（§5 的 AUC、§4 的细分层），区间都很宽。
- 随机期望用的是 1/T，等于假定各队人数和水平相同。引擎按人数均分各队，人数这一条成立；对手水平无法从我方日志得知。
- squad20 有 {{squad20.team.all.summary.nBotsTeamUnknown}} 个号队号未知，「一个队里我方号数 k」因此偏小。只用队号未知不超过 20% 的房间重算，条件 logit 的结论不变（§3.3 表的最后一行）。
- 「看到了结局」本身和胜负有关：我方的号活到终局才有终局行，输的队更容易没有终局行。§3.3 给了全算负和尽量算胜的上下界。
- 拆房靠开局时刻。两个房间如果在 1.6 秒内先后开局、地图和真人数又相同，会被并成一个；目前没有发现这样的例子（并在一起的房间没有座位号冲突）。
- 本报告不解释原因。squad10 为什么远低于随机，放在 M2 逐条假设审。

## 10. 复现

```bash
cd c136-review/agents/R10/scripts
timeout 120 python3 rooms.py build        # 重新拆房、还原身份，写 out/rooms/
timeout 120 python3 rooms.py selfcheck    # 身份还原的自检
timeout 120 python3 baseline_full.py      # 写 out/baseline-full.json 和本报告
```

| 文件 | 内容 |
|---|---|
| `scripts/c136lib.py` | 读数据包的公共函数 |
| `scripts/rooms.py` | 身份还原、拆房、队号推断、物理房间关联、结局判定 |
| `scripts/stats.py` | Wilson 区间、泊松二项精确检验、Fisher 检验、logit 偏移模型等 |
| `scripts/baseline_full.py` | 本报告的全部统计和表格 |
| `scripts/baseline_full_template.md` | 本报告的文字模板 |
| `out/baseline-full.json` | 本报告全部数字（公开；验证集只有合计） |
| `out/baseline-full-internal.json` | 含验证集逐局的房间明细、对账明细、和发现集共用房间的名单（内部） |
| `out/rooms/rooms-discovery.json` | 发现集每个包的房间、号、队号、结局 |
| `out/rooms/identity-map-discovery.csv` | 发现集的名字链 → 座位号对照表 |
| `out/rooms/rooms-validation-internal.json`、`out/rooms/physical-rooms-internal.json` | 验证集房间明细、物理房间关联（内部） |

统筹放在 `/agent/repos/c136-data/src/tools/` 的 `rooms-discovery.json` 和 `identity-map-discovery.csv`，和本次提交的 `out/rooms/` 里的同名文件逐字节相同（sha256 核对过）。
