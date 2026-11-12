# R01 进度与工作笔记（给自己接续用）

## 状态
- M1 完成：A057、A059、A094；M2 完成：A055、A075、A054。全部通过本地机械检查（`python3 scripts/check_my_review.py`）。
- M3 完成：A031（never-grew）、A019（mid-collapse）、A009（never-grew，Va）；m3-reviews 报告已发（里面更正了 A075 的判定数：错 10 / 不清 5 / 对 5）。
- M4 完成：A023（never-grew；错 9 / 不清 8 / 对 3；新模式 AT12、AT13）；A050（external；错 9 / 不清 5 / 对 6；新模式 EG03）；A003（never-grew，Va；错 7 / 不清 9 / 对 3；新模式 SP04、DN13）。
- M5 完成：A005（external，Va；错 4 / 不清 6 / 对 2；新模式 SP05、OP04）；B039（external，c110；错 12 / 不清 2 / 对 4；新模式 SP06、EC03、DF05、DN14）；B043（external，c110；错 10 / 不清 4 / 对 5；新模式 OP05、AT14）。15/15 局都过了机械检查。接着 M6（CROSS-MATCH-SUMMARY + 全量计数脚本 + cards/），再写 COUNCIL-PROPOSAL（总部 0008）。
  A005 的图镜像里没有（5_9294）：`run-heavy.sh node scripts/map_from_engine.cjs A005` 从真引擎的状态数组 aFA 取出写 out/A005/map_5_9294.bin，
  `resim_lib.mjs` 的 loadMapOrLocal 在镜像缺图时读它（A003 --verify 12_0 逐像素全同）。之后流水线照常：重演 125/125、影子 125/125。**以后缺图的局都这么办。**
- 总部 0006：所有 node 重演/影子命令必须 `bash ../../tools/run-heavy.sh node scripts/...`（在 agents/R01 下），串行、一次一局，结果缓存在 out/。
  **一次 Shell 调用只跑一条 node 命令**（机器 load 高时一条 shadow 就要 30–90 秒，两条串在一起会被 timeout 120 杀掉）。

## 每局流水线
1. `bash c136-review/tools/run-heavy.sh node scripts/resim.mjs <mid> [--replay 同局A包] [--log 包1,包2] [--bots a,b]`：整局重演，和日志 [HL-TICK] 逐号核对。
2. `run-heavy.sh node scripts/shadow.mjs <mid> [--bots ..] [--pin-no-full --tag nf0] [--probe bot:t0:t1 --tag x]`：把重演的每拍状态喂给部署的策略原文。
   默认 `--pc-shift land`（isNoFullSend 的核对点取发令后 1 拍；这一拍本号丢了地就再晚 1 拍）：12 局 5170/5170 个 HL-TICK 点全对（`python3 scripts/pc_modes.py`）。
   旧口径 1 / auto / cause 都各有一局对不上（见 shadow.mjs 文件头）；外壳源码不在镜像里，机制仍是 unknown。
3. `resim_report.py --section meta,timeline,percap,bots,events,pairs,transfers,front,spawn,drops`；
   `shadow_report.py --section check,lagcurve,chunks,bursts,paths,repeat,donate,idle`（idle 里有价格线细分）；`shadow_diff.py <mid> nf0`。
4. `burst_audit.mjs`、`dispatch_audit.mjs`、`tick_cost.py`、`q.py <mid> <表> --where .. --show ..`。
5. 手写 `analysis/<mid>.json` → `build_review.py <mid>` → `check_my_review.py <mid>`（md ≤150 行）。
- 没有录像的实例（A094 的 X）：`log_only.py`（spawn/squad/idle/dispatch/results/drops/share/late/chain）、`log_sync.py`；
  build_review 的 `timelineLog` 从日志填时间线，`timelineSpecB` 给第二个实例另填一张表。
- 总部共享工具：`/agent/repos/c136-data/src/tools/engine_replay.cjs`（真引擎）、`engine_vs_resim.py` 对比。
- `match_facts.py`（M1 的旧底稿脚本，读 bundle）的按席位对账在混了两个实例的包上不能用（A094）。**别覆盖它**：A057、A059 的复盘引用它；A003 起的席位小表在 `seat_facts.py`。
- M2 新增（都读 out/<mid>/）：`recon_facts.py --section dispatch,husk,slot,safe,ainb,doomed,peak [--siege bot:t0:t1]`（对账一节的汇总数）、
  `probe_view.py`（探针按决策拍一行）、`death_ledger.py`（阵亡号的最后一围）、`exchange_price.py`/`target_price.py`（换地与公式价）、
  `boat_fight.mjs`（海战）、`sea_landings.mjs` + `landing_math.py`（敌方登陆）、`map_ascii.mjs`（字符地图）。
- M3 新增/改动：`probe_view.py <mid> --tag x --gate <席位>`（把 buyLand 的闸门链整条复算：预算、价格 keep、safeAt 封顶、avail、20% 线、最小出兵量；
  nearCollapse 的 85 倍封顶和 isSoleHealthyBuffer 没算）、`recon_facts.py --section drops,leave`（results.csv 的离场拍 vs 录像 leave 拍）、
  `resim_report.py --section percap`（带密度）、`afk_gap.py`（leave 前的静默拍数；没有 leave 的席位的最大指令间隔）。
- A019 新增：`cmd_gaps.py <mid> [--min 60] [--bots]`（全队指令断档：连续 N 拍没有任何本队指令落地的窗口，对照窗口内受理条数、其他玩家落地条数、断档后 70 拍的批次）、
  `decay_check.py <mid> --cases bot:t0:t1 --kill 席位:拍`（挨打时余额按领土的 1.6 次方掉；吃到阵亡线的算式价 ≈ 1.8×对方余额，与策略的 need 对得上）；
  `shadow_report.py --section check` 多一行“差异是否只在船计数”；`resim_report.py --section ledger` 不再把离场壳的船算进出海两项（boat_trace 对壳的 balBefore 不可靠）。
- A009 新增：`land_ticks.py <mid> [--t0 --t1] [--bot 名] [--list] [--win 300]`（每个号的落地拍分组：间隔、每组条数、最新一条的延迟、两组之间丢了几条受理的令）；
  `probe_view.py --gate` 对 Va 局（A003/A005/A009）自动换参数（封顶 78、bleeding/thin 折扣），末尾多三行汇总（出手/价格线/avail≤0/keep 来自 safeAt 各几拍；c、worth、余额、safeAt 的范围；
  need 低于余额的拍数及其中被拦下的拍数）——判 DF03 时直接引这三行；`recon_facts.py --section leave` 多了 results.csv 的 accepted = 出生版数 + cmds 的核对；
  `recon_facts.py --section peak` 末行有“阵亡时还剩多少格多少兵”的合计。
- A023 新增：`seats.py <mid> [--t 拍]`（席位号 ↔ 名字 ↔ 队，带某一拍的领土/余额）；`probe_view.py --pick`（1500 拍前 Style.pickTarget 的逐目标复算：allow、每格价、
  floorAt、floorFor、avail、minShare×余额、卡在哪一关，末尾按目标汇总）；`probe_view.py --gate` 汇总多一行“余额过 100 倍的决策拍里按唯一健康真人邻居 / isCrowdedHard 跳过各几拍”。
  shadow_flags.csv 的 targetName 对 AI 席位（target ≥ 人类席位数）不可靠（A023 全显示成 rubysta），看 target 列。sea_landings.csv 可以直接用 q.py（列 t,owner,troops,bot,hadLandBorder…）。
- A050 新增：`mass_leave.py [mid ...] [--win 30] [--min 3]`（全数据集 RESULT=left 的行按墙上时间成簇：123 局 204 行 left，113 行在 ≥3 行的簇里，17 局有簇，4 局整队同簇）；
  `tick_clock.py [mid ...] [--per-match]`（全量非 left 的 RESULT 行拟合 秒 = 23.0 + 0.05598×拍；每条 left 行“晚了几秒”）；
  `tail_sync.py <mid>`（一局收尾：各号 RESULT 的 tick/at、名义时刻、日志最后一行、录像 leave 拍、最后落地指令；快进下限；停拍后的调度；**行序**（最后一个全队都写了快照的拍之后谁连着补行）；
  停拍前后 avgMs/maxMs；录像里停拍后本队/其他席位落地的指令）；`overlap.py <mid>`（第一行 left 前后还有哪些数据集对局在跑）；
  `step_cost.cjs <mid> --around T --span N --top K`（总部真引擎 engine_replay.cjs 逐拍耗时，要经 run-heavy.sh）；`boxed_coast.py <mid>`（围死快照里有没有水边）；
  `landed_stats.py <mid> --windows a-b,...`（落地指令：目标已不在/一兵未扣/≥3 条同拍批次/延迟中位）。
- in_game.log 第一列是全局递增的行号（不是时间）；RESULT 行才有 at。results.csv 的 seconds = at − card.timestampMs。
- q.py 的坑：数字样子的字符串会被当成数（`toName==777`）；dispatch_audit 的 would 是 'accept'/'quota'，executed 是 0/1；resim_transfers 的 `from` 列不能写进 --where。
- 影子对 boatTo 的受理比真实客户端宽（A019：影子 42 条、日志 10 条），**船指令的“受理”不能引用**；进攻、捐兵两类与日志 cmds 计数一致。cmd_gaps、lagcurve、flow 都不含船。
- 批次落地的兵不都是净损失：打无主地（目标已死改打无主地、pct=47 中立令成批）的兵在进攻结束后流回余额；写“实扣”时要分开打真人和打无主地
  （`q.py <mid> shadow_match --where "... n>=3" --agg sum:spent --by targetName`）。
- 引擎规则备忘：阵亡 = 领土 ≤ 峰值/4（game.js aliveTick L1298–1312，峰值每拍回落 max(1, 差/1000)），剩下的地和兵清零；
  进攻每格 2 + 2×def，def ≈ 1.6×守方密度；海战 boats.js fightBoats L328–357；登陆 landAt L262–287 不需要陆地接壤。
  守方每丢一格同时被打掉 def 的兵（damage L1062–1074）→ 余额 ∝ 领土^1.6；吃到阵亡线总价 = 2×(L0−峰值/4) + 2×B0×(1−(峰值/4/L0)^1.6) ≈ 1.8×B0。
  海上有船时 collapse 不清号（L1316–1330）：地、余额、峰值清零，船靠岸后重来（A019 sora_w）。捐款手续费 = 捐出方余额×64/1024，与捐多少无关（donate L404–416）。
  expandNeutral：t < dpEnd(1500) 只走 dpNeutral；之后走 General.expandNeutral L944–953，线上兵不够就每个决策拍补一条 pct=47。
- Vb buyLand 非真人目标：safe = min(safeAt, 88×L)（L5414–5418）→ keep = max(keep, safe)（L5444）→ avail ≤ 0 continue（L5446–5447）→ x < want 且 x < chunk(0.2)×B 不发（L5449–5453）。
- 捐款配额（A023 读清楚的）：game.js donationCost L347–356、bookDonation L370–376、donationCapTick L379–383。每个受赠方累计 donQuota，全场一个 donCap（开局 15，每 100 拍 +4/6/8/10）；
  3213 拍前一笔 v 记 2 + v÷(k×uw÷100) 点，uw = 1 + 陆地÷300，k = 1/4/10/30/100（分界 357/714/1071/2142）；3213 拍起 4 + 100v÷softCap(q)；4284 拍起不限。
  dispatch_audit.csv 的 cap/used/maxByQuota 就是这套算式。引擎有 donateQuote（L418–428）可以事先问，策略没有调用（三个版本都没有）。被拒的捐款不进录像。
  船靠在队友岸上也按捐款入账、占同一个配额，配额不收的沉海（boats.js landAt L273–279）。
- 进攻收线：一圈付不起时剩下的兵全砸进去（只伤兵不占地）再 endAttack；没有接壤（cnt=0）时剩兵退回余额（game.js L990–1059、endAttack L1076–1080）。“发出”≠净损失。
- Vb 其他读清楚的门：idleBoats L5022–5040（没有非队友邻居的号，只要还有本队号有陆上前线、自己密度 < 115 就不出海）；offers L5291–5294 pulseMode =
  nearCollapse || bleeding || ((tD < thinMaxTD || need > 0.30B) && !(t < 2400 && !onMe && need > 0.35B))；buyLand L5361–5365 唯一健康真人邻居（B < 1.28×100L 跳过）、
  L5371–5374 isCrowdedHard（B < 1.26×100L 跳过）、L5440–5443 over 时 keep = 0.9×100L（密度 ≥ 122 时 0.82）、L5605 脉冲额 < max(minCmd, 0.04B) 跳过；
  tryDonateToTeammate L4479 reqD = boxedIn ? 58 : 108；floorFor L2228–2231 = max(floorFor0, safeP×peopleSafe)（peopleSafe L2280–2298 跟着真人邻居的余额走）；
  winRatio 1500 拍是 3（m = 1.5），2500 拍后 1.8（m = 0.9）。

## 重演核对（ok/bad）
A057 1324/0（含 B038）；A059 290/0；A094-Y 86/0（--bots ryan_m,zexos1,noah88）。
旧结果（船落点修正前，开工时重跑）：A055 539/0；A075 286/2；A054 652/0；A031 464/0；A019 505/0；A009 406/0；A023 515/1；A050 499/0；
A003 339/0；B039(--replay A058 --log B039,A058) 743/0；B043(--replay A062 --log B043,A062) 860/2。A005 缺地图，只能 engine_replay 或 log_only。

## 版本对应（总部 0002）
- Va（A003/A005/A009）：`v27-team-c116-va.js` + `spawn-coordinator-c116-va.mjs`
- Vb（其余 A 局）：`v27-team-c116-vb.js` + `spawn-coordinator-c116-vb.mjs`
- B039/B043：`v27-team-c110.js` + `spawn-coordinator-c110.mjs`

## Vb 代码地图（行号）
General.act L752–810（L796 打 AI）；Style.pickTarget L1144–1177；V13.dpNeutral L2383/L2406；V13.floorFor0 L2233；V13.safeFinite L2500–2510；
Policy.updateShadowQuota L3800–3835；Policy.send L3838–3925（L3844 闸门）；tryDonateToTeammate L4325–4517（L4331 每 25 拍、L4343 被打不捐、
L4355 boxedIn、L4382–4388 两条底线、L4418 受赠者密度上限 142/115、L4455 doomed、L4463–4473 协防、L4479–4481 收益调度、L4500–4506 pct）；
Policy.winFloor L4562；Policy.act L4801…（L4941 expandNeutral、L4942 buyLand、L4962 捐款只在本拍没发令时）；Policy.offers L5072–5340；
Policy.buyLand L5342–5619（L5358 价格线、L5361–5365 唯一健康缓冲、L5440–5443 over 留兵、L5449–5453 打 AI、L5611–5616 满预算）。
参数：maxW 0.5，winT→2500 拍后 1.8（m=0.9），hold 0.9，marketFloor 0.85，overHumanCap 1.28，pulseFrac 0.12，quotaGuardMode 1。

## Va 代码地图（`v27-team-c116-va.js`；4297 行之前与 Vb 同号，之后 = Vb − 1）
两个文件只差参数表 L3702–3763 和 L4291、L4296、L4382–4383、L4478、L4502–4505。Strategy.send L479–487；General.act L752（L792 expandNeutral、L796 打 AI；自退 L769–784）；
General.boatOut L999–1014；V13.dpNeutral L2383–2406、dpKeep L2459–2464、safeAt L2728–2738、自退 L2702–2717；Policy.send L3838–3925（闸门 L3844–3863；检查 L3821–3833）；
isOurSquadBot L3960–3972（名单里有旧号名 777、mishi、leo_99 等）；tryDonateToTeammate L4324–4517（L4330 槽、L4354 boxedIn、L4381–4387 底线、L4413 受赠者筛选、L4454 doomed、
L4462–4472 协防、L4474–4493 进攻、L4499–4505 pct、L4507 donate）；Policy.safeAt L4542–4559（L4545 封顶 78×L）；peerAggressor L4605–4652（L4632–4633）；Policy.act L4800（自退 L4911–4926）；
idleBoats L5018（L5039）；offers L5071（L5172 防守折扣）；buyLand L5341–5617（L5349–5358 价格线、L5413–5417 封顶、L5419–5426 预算、L5443–5446 keep/avail、L5448–5453 打 AI、
L5594–5606 脉冲、L5610–5615 预算分支）。三处自退都要求 g.t > 8500。Va 参数：pulseFrac 0.20，oppFloorCap 78，其余同 Vb。

## 模式编号（提议，跨局复用）
SP01 密集阵/被队友围住 | SP02 出生名单跨实例 | OP01 DP 开局(对) | OP02 保底线死锁 | IO01 掉队期间照常下令 | IO02 过期指令成批落地 |
IO03 isNoFullSend 误置真 | AT01 12% 脉冲(对) | AT02 零星中立令占名额 | AT04 开战首击 | AT05 价格线空等 | AT06 中期吃 AI 地(对) |
EC01 内陆围死满仓 | EC02 小邻居卡住后排大号 | DN01 后排输血(对) | DN02 截断捐款 | DN04 给必死队友捐 | DN05 配额拒单 | DN06 低密度给高密度 |
DN07 互捐 | DF01 被大号陆攻 | DF02 挨打不出手 | EG01 领先时自退。
M2 新增：SP03 出生方案反复改写/同像素 | OP03 1500 拍前对真人的保底线 | IO04 正常延迟内重复下令 | IO05 过期捐款/船令成批落地 |
AT07 最小出兵量闸门 | AT08 过 100 倍后不看价格 | AT09 离场壳的 88 倍保底线 | DF03 safeAt 高于余额 | DF04 不接壤对手海上登陆 |
DN08 后排捐空后被打 | DN09 幽灵前线 | DN10 为利息而捐净负 | SE01 远程船耗光占船位 | SE02 短程船重开前线(对) | SE03 船落在队友岸上 |
SE04 装兵比手续费少的小船 | SE05 远程船被拦截船打沉。
M3 新增：AT10 身边的离场壳按预算吃掉(对) | DN11 两波进攻之间把兵捐走 | EG02 8500 拍前被 leave 指令移出对局（不出自策略）；IO01 在 A031 补了定义；
AT11 单价过了价格线但预算不到余额 20%（buyLand L5611–5616），对真人不出手（A019 riku_x）。AT08 在 A019 有一处判“对”（延迟正常时吃 Player 917）、一处判“错”（断档时清仓）。
A009 新增：DN12 名单里的旧号名撞上同队路人，把路人当本队号捐兵（talon5 → 777）。A009 里 AT08 判“对”（riku_x 过 100 倍后连发脉冲对掉登陆）；
DF03 有两处：sora_w（挨打中，不清）、kaito9（3800–4580 拍 143/157 拍被 safeAt 拦下，其中 91 拍 need < 余额，判错/推断）。
A009 的主因是客户端落后服务器（300–2400 拍，延迟中位到 764 拍，每号每次最多落地 9 条，其余丢失），不在策略文件里；M6 要做“每局指令延迟”的全量计数。
A023 新增：AT12 余额过 100 倍后溢出的兵脉冲打给杀不动的大邻居、够杀的邻居被跳过（ryan_m 3405 拍 DARK vs Fagner）；AT13 只有一个健康真人邻居：128 倍才打、108 倍就捐，
两个门槛互锁（talon5 对 Tenekld 1668 拍不出手）。A023 的主线：出生挤成一团 → 7 个号被队友围死 → 八成的兵 1000 拍没有敌方接壤 → 调度 348 条落地 40 条（配额）。
A050 新增：EG03 全队客户端在同一个回合停住、随后成簇被记 left（不出自策略）。A050 的主线：10 个客户端 4354–4361 拍同时停住（六个再没动过，四个恢复追帧），
RESULT 全是 left，7 条 leave 同在 4802 拍；停住前本队 30.05%、全场领土第 1、2。场上的问题：5 个号同像素出生、600–1800 拍指令晚 65–208 拍、OP02 保底线跟着队友余额、
3213 拍前调度 242 条落地 9 条；翻盘靠 zexos1 打垮 Tennessee、talon5 吃壳 + 过 100 倍后脉冲连杀（AT08 判对）、3213 拍后后排输血（DN01 判对）。
A050 里 safeFinite（threatOf L417–445）读清楚了：对一块 AI 地取它其他邻居（不排除队友）里余额最小的一个减去我在它身上的在途兵；密集出生时就是围在旁边的队友。
M6 可做的全量计数：调度落地率（日志 HL-DISPATCH 行数 vs 录像 donate 条数）、被围死快照占比（card 的 boxedHighDensSnapshots）、船落在队友岸上的条数。
A003 新增脚本：`spawn_actual.mjs`（每个号录像里的出生指令条数、实际出生点、离计划落点的距离；写 spawn_actual.csv，`region_share.mjs` 会读它补出生点）；
  `seat_facts.py <mid> --section foecmds|who|flows|series|squad|kills|cmdcount|teamdon|adjacency`（人类席位打本队的每条令、指定席位自己的令、领土流向、并排序列、敌方阵亡、各队捐款）；
  `strike_reply.py <mid>`（本队每一轮打真人：实扣/本意、打前打后密度、之后第一条打回来的人类进攻令隔几拍、是不是目标同队；末尾有基线）；
  `donate_gate.py <mid> --tags 号:探针标签,…`（“有队友正被人类进攻”的决策拍里捐出方密度够不够 102、当拍 buyLand 是否先出手）；
  `pc_modes.py`（12 局 × 各种 --pc-shift 口径的 HL-TICK 对比表）、`snap_loss.mjs`（快照拍正好丢地的点上日志值是不是本拍结算完的值）；
  `step_cost.cjs --win W`（按窗口的引擎每拍耗时）；`probe_view.py --gate` 的标记多一个 P = pulseMode（判一条令走脉冲分支还是预算分支，**写 codePath 前先看这个标记**）。
A003 新增模式：SP04 出生指令没落地、号被引擎随机安放（协调器第一版 10 条落地 0；A009 第一版 8 条落地 0）；DN13 有敌邻的号密度够不到 102，协防捐款的门全场开不了几次。
A003 的主线：7 个号随机出生散在全图（开局人均反而全场最高）→ 750–1350 拍客户端落后 42–201 拍，AI 地被别人分走 → 1500 拍后重复下令把首击叠成余额五到七成
  （41 个重复组实扣/本意 中位 2.78；riku_x、talon5、ryan_m 打完余额低于自己的 safeAt，35–77 拍后被目标同队反推）→ 其余号停在价格线/safeAt/20% 线攒兵 → 3060–3724 拍被 46 条令约 818 万兵逐个吃掉。
  重复下令的机理：延迟 6–19 拍、决策周期 5 拍，预算分支（L5610–5615）没有在途检查，脉冲分支只看已落地的进攻线（L5595 curAtk ≥ 4% 余额）。M6 要全量数 IO04（`shadow_report --section repeat`）和 strike_reply。
  OPENING-CHECK 行的 sent 计数比录像里 221 拍前落地的条数多 1–2 条，可能就是没落地的第一版出生指令（口径不明，别当结论）。

## 逐局进度
- [x] A057（never-grew）
- [x] A059
- [x] A094（lead-thrown；两个实例）
- [x] A055（outscaled）  - [x] A075（win）  - [x] A054（mid-collapse）   （M2）
- [x] A031（never-grew）  - [x] A019（mid-collapse）  - [x] A009（never-grew）   （M3）
- [x] A023（never-grew）  - [x] A050（external）  - [x] A003（never-grew）   （M4）
- [x] A005（external）  - [x] B039（external）  - [x] B043（external）   （M5）
- [ ] M6：reports/CROSS-MATCH-SUMMARY.md、全量模式计数脚本、cards/
A005 新增脚本：`map_from_engine.cjs <mid> [--verify 图_种子]`（见上）；`page_speed.py <mid> [--ref 600]`（只读日志：按行序 + RESULT 的 at + 名义的钟，
  给每个页面在各 RESULT 时刻的本地拍区间、落后拍/秒、平均速度占正常速度的比例；HL-SLOW-TICK 行；avgMs/maxMs 前后）；
  `spawn_layouts.py <mid> [--log a,b] [--near 40]`（协调器每次求解的整份落点表 [BACKEND-SPAWN-COORD] 编号 v1…，每条落地的出生指令属于哪一份，
  收场的阵是哪几份拼的，落点离“当时已落地的”敌方真人多近 → SP03/SP04/SP05 的机械计数）；`leave_grid.py [mid ...]`（本队 leave 拍对 112 取余）；
  `probe_view.py --tag x --safe`（1500 拍前对 AI 地的保底线出自谁：按探针里“机器人邻居…其他邻居”行复算 safeFinite，和 winFloor 实际值对上才算；
  输出保底线 ≥ 余额的拍里出自队友余额 / 敌方真人余额 / dpKeep / 每格价项各几拍）。shadow_flags.csv 的 targetName 已修（AI 席位显示 AI#n）。
A005 新增模式：SP05 扇形阵逐点不查敌距（talon5 离 Charles V 14 像素；协调器扇形阵分支 L1175–1207 只查陆地/连通块/队友间距，敌距只进 planScore，角锁定后评分不起作用）；
  OP04 DP 结束后按每格价吃 AI 地（对）（kaito9 640–725 拍 9 条令 630→900 拍 3338→8737 格）。
A005 的主线：630 拍人均并排 → 本地 600 拍起 10 个页面只有正常速度的 26–58%，决策窗 700–999 拍的令到一小半、1000 拍后 430 条 0 落地（每号每组最多 9 条）
  → 本队 1000 拍原地不动（密度 6→40），别的队和路人 Ronaldo 把 AI 地分完 → 1428/1540/1652 拍 4 条 leave（相隔 112 拍），120–158 秒 9 行 RESULT 全 left。
  同一晚 A002、A006 也是；mass_leave 的 17 个簇里 15 个在开局 91–170 秒 = 页面掉队最深的时段。
M6 要全量做的（A005 带出来的）：
  1. 每局掉队曲线（lagcurve --win 100/300 的落地率、延迟中位）对“地图填充速度”（resim_teams 的有主地占比每 90 拍增量）——掉队是不是总在填得最快的那段开始；
  2. `leave_grid.py` 扩到所有有录像的包（先 `run-heavy.sh node scripts/replay_cmds.mjs <mid>` 逐局展开，不模拟，很轻）；A005/A031 全同余、A057/A059 各一对，四局两两同余 10/27；
  3. `page_speed.py` 对所有有 left 簇的局；RESULT 行 tick 是不是“某批过期令落地的拍(+7)”（A005 9 行里 5 行）；
  4. `spawn_layouts.py` 全量：第一份表落地 0 的局数（SP04）、收场阵由几份表拼成（SP03）、40 像素内有已落地敌方真人的号数（SP05）；
  5. “每号每组最多 9 条”的全量核对（shadow_report chunks 的 n 最大值，A009、A005 都是 9）；
  6. IO04（shadow_report repeat）、OP02（probe --safe 太重，只能抽样）。

## B 组（c110，squad20）怎么跑（B039 做完后的笔记）
- B 包自带的录像是截断的，用同局 A 包的录像：B039 ↔ A058，B043 ↔ A062。命令一律 `--replay A058 --log B039`。
  先 `run-heavy.sh node scripts/engine_names.cjs A058 --out B039`（512 个席位名 → out/B039/names512.json），再 resim、replay_cmds（`--replay`）、shadow（`--strategy c110`）。
- 日志里的号名会轮换（Bohemia→ErenYeager；离场号的 RESULT 行换了名字）：`seat_table.py` 按 [HL-SPAWN] me= 和 results.csv 的 meId 对席位；resim_lib 的 logAliases 已处理。
- c110 的影子只是近似：外壳在上一拍没跑完时跳过决策拍（L19–31），影子每拍都跑；B039 nb/neut 475 个全同，cmds 影子多 92 条（794 对 702）。硬数字取录像和日志。
- c110 代码地图（`v27-team-c110.js`）：SQUAD_POOL_SET L1（740 个名字）；外壳 L19–31；Strategy.analyze L420–448（L440 受保护席位不进 nb、不计 cnt）；threatOf L464–491；
  minCmd L521–523（feeK×12/1024×余额 = 4.69%）；Strategy.send L526–539（15 拍同目标冷却 L529–533）；General.act L804–846（L832）；General.boatOut L1035–1051（L1047）；
  searchWater L1056–1116（L1104 查保护）；person L1145–1147；V13.act L1850–1860；V13.boatFood L2038–2058（L2054）；searchFood L2065–（L2107 不查保护）；floorFor0 L2270–2276（L2272）；
  V13.expandNeutral L2408–2414；dpNeutral L2418–2444（L2438）；botOk L2499–2505；V13.winFloor L2521–2528；safeFinite L2532–2542；V17.safeAt L2744–2754；
  isOurSquadBot L3973–3976；isProtectedSquadMate L3993–3996；chooseSpawn L4007–4152（后端 L4023–4062，本地分槽 L4065–4149）；tryDonateToTeammate L4369–4499（L4424 候选、L4428、L4438 rescue、
  L4450 poke、L4467/L4490 surplus）；Policy.safeAt L4524–4540；Policy.winFloor L4542–4550；Policy.act L4781–4944（L4901 expandNeutral、L4902 buyLand、L4922 捐、L4923 idleBoats）；
  idleBoats L4979–5006（L4994 boatFood、L4996 idleCap、L5004 boatOut）；buyLand L5250–5534（L5358 keep=max(keep,safe)、L5360 avail、L5363–5368 打 AI：x<minCmd 跳过、L5531 预算分支）；Policy.boatFood L5536–5597（L5538）。
  参数：dpEnd 1500、dpSpend 0.5、winR 0.002、maxBoats 2、boatEvery 60、boatFrac 0.5、botMax 60、idleCap 1.25/1.3、foodK 1.25、feeK 4、seaCore 0。
- B039 新增脚本：`voronoi_share.mjs`（天然份额、吃到率、份额里的地归谁、AI 地去向）、`pool_ai.mjs [--seats --tag]`（名字撞池 + 指定 AI 席位的去向）、`lag_periods.py [--json]`（四段延迟、漏斗、迟到损失、重复/成批）、
  `spawn_local.py`（c110 本地分槽出生）、`attrib3.py [--json]`（600–1500 拍三分账）、`xteam_frontier.py`（拆队后的跨队边界）、`donate_recon.py`（HL-DONATE/ASSIST 对录像；离场壳/400 拍内阵亡/回捐小计）、
  `boat_trace.mjs`（加了 hitLoss/hitTicks/hitBy：海上被敌船打掉的兵）。
- B039 新增模式：SP06 本地分槽出生各算各的候选表 | EC03 跨队保护墙（别队本队号和它的壳不可打） | DF05 名字撞池的 AI 蚕食不还手 | DN14 给离场壳捐兵。
  复用：OP02 在这局有两种跨队形态（1500 拍前 winFloor：Pomerania–Sus；1500 拍后 safeAt：404 Not Found–Algiers，两边 safeAt 正好等于对方余额）；AT07 最小出兵量（余额的 4.69%）让有钱的号买不了便宜的 AI 地。
- B039 的主线：20 个席位拆三队 → slot 15–19 开局就没了、另 8 个 1099–2016 拍离场（页面本地 600 拍起只有正常速度的 13–73%）→ 剩 7 个号正好是四对跨队贴着出生的，互相当墙 →
  长地全靠船吃离场壳 → 3897–4960 拍被周围 2–4 万格的真人逐个吃掉；Pomerania 在赢的 T2 里活到收场。
- M6 要全量做的（B039 带出来的）：6. 每局 `lag_periods.py --json`、`attrib3.py --json`、`voronoi_share.mjs`（串行）；7. 机器人席位 vs 其他真人的离场率（B039：30 个少 20 个 vs 44 个少 6 个）；
  8. 船的手续费/装兵比、被打沉的船（boat_trace 的 hitLoss）；9. 捐兵手续费占比（donate_recon 只对 c110；c116 用 dispatch_audit）。
- B043 做完后的笔记（c110，--replay A062 --log B043；重演 600/604，另 4 个快照是 6241 拍后壳自动捐兵的收款人，`engine_bal.cjs --check` 用真引擎核对过）：
  新脚本 `pairs_view.py <mid> victim|attacker <席位…>`（resim_pairs 按对手汇总格数、起止拍；resim_pairs 只有和本队席位有关的行）；`scripts/steps/b043-{a,b,c,d}.txt` 是成批步骤文件
  （`run_batch.sh` 的输入）。run-heavy 排队太深时内联命令 118 秒内拿不到槽：改在 tmux 里 `HEAVY_QUEUE=3000 bash ../../tools/run-heavy.sh bash scripts/run_batch.sh <步骤文件> > 日志 2>&1`，回头读日志。
  新模式：OP05 1500 拍前 dpKeep 按最强真人邻居的全部余额留兵（Jordan 1285–1495 拍；dpKeep L2491–2496）| AT14 进攻线上的兵不撤回（Srivijaya 1800–2040 拍 30 万兵压在进攻线上，家里 0.4–2.4 万；
  hold() L2120–2130 因 holdOn=0 不执行，本队全场 0 条 retreat）。复用：AT13 在 c110 里的行号是 buyLand L5269–5273（isSoleHealthyBuffer）/ L5279–5282（isCrowdedHard）/ L5267（价格线）；
  DN14 的机理读清了：rescue 分支 L4424 不查 isBot，L4434 的条件（被真人打且密度 < 75）对壳永远成立，L4436 dMe ≥ max(55, dAlly+15) 就捐 pct 155——Yoshi 的壳一家收了 18 笔 1170526。
  船落在同队岸上 = 捐款且“一笔收不下整船作废”（boats.js landAt L273–279 + game.js bookDonation L370–376）；过期船令按执行时余额装兵，额度一超就整船没了（Itachi 1596 拍 97653 兵）。
- B043 的主线：20 个席位拆三队（T3 8 / T1 7 / T2 5）→ 630 拍和路人并排（吃到天然地盘 0.41 对 0.44）→ 页面本地 600 拍起只有正常速度的 4–89%，600–1500 拍的令 44.2% 落地、延迟中位 224 →
  最慢的 7 个页面 1043–1526 拍被 leave → 1560–1800 拍过期令、过期船成批落地，1755–2503 拍死 6 个 → 中期 Janissary、Barbary、KGB、Hussite 两三千拍没打过真人（价格线 + 唯一健康邻居等 128 倍 + safeAt），
  46 笔捐兵 350 万里 23 笔 152 万进了壳 → 3591–5892 拍被 Art raffiné、Mongol Empire 等逐个吃掉 → T1 99.87% 收场，Trajan（第 7）、Zenobia（第 10）在赢的队里活到最后。
- M6 要全量做的（B043 带出来的）：10. 船落在同队岸上的条数、到岸、到账（boat_trace 的 landedOn=mate / mateGot）和出海当拍落点已是同队岸的条数（aimAtLaunch）；
  11. 进攻线上的兵对家里余额的比（resim_squad 的 atkOut 对 bal）≥5 倍且持续 ≥90 拍的号数（AT14）；12. 给离场壳的捐兵（c110 用 donate_recon；c116 用 dispatch_audit 的 to 席位 state=2）。

## M6（跨局汇总）做完后的笔记
- 产物：`reports/CROSS-MATCH-SUMMARY.md`（由 `reports/m6-data/SUMMARY.tmpl.md` 拼出，**只改模板**）、`reports/m6-data/*`（全量表的提交副本）、`cards/`（D01 + H01–H14，索引 `cards/README.md`）。
- 一条命令重算：`bash scripts/m6_run_all.sh`（4–12 秒，全是 python；先跑 `m6_match_split.py --csv`，再跑各 `m6_all_*.py`、`leave_grid.py`，最后 `m6_build_report.py --check`）。
  模板里的占位：`{{file:名}}` 整个文件，`{{lines:名:正则}}` 取匹配的行。`--check` 只核 ≥4 位的整数能不能在数据文件 / 逐局报告 / analysis 里找到；
  **比例、局数这类短数字它核不了**，改口径以后要拿新旧摘要行对一遍（做法：把 git HEAD 版 m6-data 的摘要行和新版的数字集合相减，在模板里搜旧的）。
  卡片和提案同样核：`python3 scripts/m6_build_report.py --check-file cards/*.md reports/COUNCIL-PROPOSAL.md`（H09 的 2048 是源码常数，不是数据）。
- **15 个包不是同一场对局**（`scripts/m6_match_split.py`，表 `out/_all/match_split.csv`，其余全量脚本用 `load_split()` 读，列出但不计）：
  平行两场 10 个 A015 A017 A025 A043 A086 B009 B011 B037 B042 B050；先后两场或录像对不上 5 个 A071 A073 A094 B030 B049。
  证据 E1 开局时刻（results.csv 的 at − seconds 分簇，单凭它要间隔 ≥ 3.0 秒；B007 2.1 秒、B029 1.3 秒是同一场）、E2 席位上的名字（日志 me=N 对录像头）、
  E3 各组见过的队号、E4 收场拍不止一个（A015 A025 A073 B011）。10 个平行包里 9 个 seededPlayers = 20。
  c110 的 E2 要按席位号核：录像里的名字只是“在池子里”时可能是撞名路人（B009 的 12 号席位是 Russian Empire），有 E1 分组时看它那一组别的席位对不对得上。
  B009 = 9 个页面一间房 + 1 个页面（席位 0，Mali→Umayyad）在 A010 那间房；录像是 A010 那间。A025 两间房都赢了（6952、14689 拍）。
- c110 的页面标签一局之内会换（B029 29 号席位 Marlborough→Leclerc；B009 开局和收场的标签全换了）：**c110 一律按席位号认页面**（日志 me=N、results.csv 的 meId）。
- 口径（去掉 15 个包以后）：108 局 = squad8 10 + squad10 67 + squad20 31；92 局有录像；好地账 85 局（67 + 18）；不分队 A046、B027。
  分队 106 局主队赢 12（A001 A018 A022 A037 A075 A079 B003 B019 B033 B041 B045 G07），按“第 1 拍有真人席位的队数”的基准 33.9（card.actualTeams 35.4，引擎队数 30.7）。
  card.actualTeams 在 83 个能核的包里错 7 个（A005 A022 A029 A050 A075 B031 B047）。card.seededPlayers 和第 1 拍在场真人数 85 局里 66 局差 ≥1。
  通道比值 nd600_1500 > 1.15 的局（A018，日志 cmds 计数不全）不进分母：squad10 有比值的 64 局，< 0.7 的 29 局，≥ 0.9 的 25 局。
- 同一场里有两支编队：sameMatchPeer 12 场；数据集里成对的 A051↔B033、A057↔B038、A058↔B039、A062↔B043；“其他真人”要去掉另一支编队的席位（leave_grid 已去，m6_all_replay 的批次统计没去，文中注明了）。
- leave 的三类（`leave_grid.py`）：8500 拍前且席位还活着 = 被移出（113 条 34 局；同拍 ≥3 个号 7 次 26 条；不同拍两两对 112 同余 36/108）；
  8500 拍以后 = 策略自退够得着（14 条 8 局）；席位阵亡之后 = 页面收场关掉（15 条 4 局，A010 的 10 条在 4613 拍）。阵亡拍取 results.csv 的 event=died。
  被 leave × 通道：squad10 < 0.7 的 29 局 10.7%，≥ 0.9 的 25 局 1.7%；squad20 27 个全在 < 0.7 的局。
- 引擎配额（game.js L338–383）：donCap 开局 15，每 100 拍 +4/6/8/10（1071、2142、3213 换档），1500 拍 85、3213 拍 209；一笔的点数 3213 拍前 2 + 100v/(k·uw)，uw = 1 + 陆地/300，
  k = 1/4/10/30/100（357、714、1071、2142）；3213 起 4 + v/领土；4284 起或受赠者是 AI/壳不限（donationFree L360–362）。离场 leave L229–233 → 状态 2，无利息（L740），按内置 AI 跑。
- c116 的捐兵候选跳过 `window.__quitPlayers`（vb L4393、L4415、L5026），c110 没有 → squad10 给壳的捐兵 0 条，squad20 112 条（B023 44、B038 37、B043 24、B039 5、B033 2）。
- 参数出处（卡里引过的）：maxW 0.5（vb L2669）、winT [[1500,3],[2000,2.85],[2500,1.8]]（L2682）、marketFloor 0.85 / marketFrom 2500（L3700–3701）、
  oppFloorCap vb/c110 88、va 78（L3714）、overHumanCap vb/c110 1.28、va 1.12（L3719）、chunk 0.2、hold 0.9、surplus 1。
- 没做完/没法做的：另一间房（没有录像的那组页面）的结果没有逐包重判；丢令丢在哪一段、leave 谁发的、页面为什么掉队，包里都没有；保底线值多少格要模拟器对照。

## 通道的三条规则（M6 之后、写提案之前补的；卡 H15）
- `scripts/m6_channel_buffer.py` → `reports/m6-data/channel_buffer.txt`（五张表）+ `channel_trace.csv`（13975 行，陆攻令和捐兵令逐条：决策拍、落地拍、落地那一拍这个席位的条数）
  + `channel_bursts.csv`（4091 行，一个号一次落地一行）。已进 `m6_run_all.sh`。**影子里的船令（kind = boatTo）没有落地对账**，这几张表只有陆攻和捐兵。
- 规则：① 每席位每拍 ≤ 9 条（各种指令合计；本队 165 个拍正好 9 条）；② 同拍倒序执行（独立检验：录像批次到影子放行序列里正序、倒序各找一次，105 : 0，c110 10 个都对不上）；
  ③ 一串里先发的 9 条留下、后面的丢（c116 陆攻令丢 4769 条，非收尾的 3619 条里 78% 挨着 9 条的批；一串满批开头 54 处 52 处没丢令、结尾 43 处 40 处有丢令）。
  注意 `shadow.mjs` 的对账本身假定“跨拍按决策顺序、同拍倒序”（L486–500），所以 ② 不能拿对账结果去数（会循环论证），要用独立检验；③ 用的是对账结果，靠开头/结尾的不对称来分辨先留还是后留。
- 满批的延迟中位 246 拍；相邻两个满批间隔 P25/中位/P75 = 119/245/427 拍；整段丢弃 5 段 338 条（A019 zero_7 决策拍 1500–1865 共 73 条）。
- 掉队是整局一起的（第 5 表）。A057 的 resim_meta.squad 里有 `B038:名字`（同局另一支编队），数“本队”时用“有影子的号”。
- 出生指令同样倒序：同一步多条 226 次里新表先执行 187 次；不在最后一份表上的 40 个号 = 7 + 15 + 18。
- `scripts/m6_all_lobby.py` → `all_lobby.txt`：大厅（squad10 真人数中位 53，队数 2 队 21 局、3 队 27 局；本队占所在队真人的中位 0.59）、其他真人到 630/1500 拍的去向（1500 拍在场 90%）、
  决策耗时按时段 × 通道（600–1500 拍：干净 0.69、差 1.08 毫秒/拍，ρ = −0.70；90–450 拍 ρ = −0.39）。
- 没查清：9 条的闸在哪一层；整段丢弃怎么发生；页面为什么停一段再连着算（“像后台定时器限流”只是待宿主机核实的线索）。

## 离线断面归因（总部 0009 改成纯离线之后；任务卡 0003 的离线版）
- 范围：只读 c136-data 与 R06 的 `archive/agents/R06/sim-v2`（一个字不改），只写 agents/R01/。只跑历史版本 va / vb / vc / c110（`common.mjs` 的白名单）。
  不写、不评任何新策略；v28 一类作废。总线上出现过「范围限制作废」的广播（hub 5c349f7a、08f894fe），没照做；hub 头 aedd1961 已改回。
- 交付：`reports/OFFLINE-CHECKPOINT-ATTRIBUTION.md`（表由 `scripts/ckpt/aggregate.py` 生成到 `reports/ckpt-data/ckpt_tables.md`，三层保真度表由 `fid_tables.py` 生成到 `fid_tables.md`）。
  做完发 `bus-send.sh offline-attribution-done --type report`，之后长等 `bus-wait.sh`。已发里程碑 `outbox/0016-fidelity-three-layers.md`。
- 14 局（A005 镜像里没有图，sim-v2 跑不了）：通道干净 A075 A055 A023；浅落后 A019 A054 A003；深落后 A031 A050 A009 A057 A059 A094；c110 深落后 B039（录像 A058）B043（录像 A062）。
- 窗口：0→630、630→1500、1500→3213、3213→4284、4284→5184。每个窗口各臂都从历史在断面拍的局面出发。
- 臂（`scripts/ckpt/ckpt_run.mjs`，都跑同一个历史版本；`@n` = 通道随机数种子）：C0 即时；C1 基础延迟；C1p = C1 + 实录页面寿命；C2w = 实录阶梯、页面不停摆；C2 = 实录阶梯 + 页面停摆 / 掉线；历史臂 = 录像原样。
  分解：历史 − 起点 = (C0 − 起点)[规则] + (C1 − C0)[基础延迟] + (C2w − C1)[落后波] + (C2 − C2w)[页面/掉线] + (历史 − C2)[残差]。主结果量 relTerr1（人均相对领土）。
  对数链：逐局把首尾相接的窗口的 ln 比值相加；任何一个值 < 0.05 的窗口（生死窗口）不进链。**C1 才是公平的「健康通道」基线**（C0 物理上做不到）。
- 实录阶梯三种口径（`make_trace.py`）：`traces/` 只收唯一定位的配对（主批次用的）；`traces-hi/`、`traces-lo/` 再加上定位不唯一的（最早 / 最晚放得下的决策）。
  **日志次序的地板**（`logorder_floor.py` → `floor/<局>.json`）：in_game.log 每行开头的流水号是收集次序，页面记本机拍 t 时别的页面已记过的最大本机拍 = 服务器拍下界。
  6,551 条唯一定位配对核对 0 条违反；286 条「有信息量」的配对里地板都低于真值（差的中位 236 拍）——地板是可靠但偏松的下界。
  `ckpt_run.mjs --floor` 在建好的阶梯上取 max（不写进阶梯文件：R06 的 makeProfile 拿阶梯文件里最大的 τ 当「通道断了」的时刻，混进地板点会改它）。
  只收唯一定位配对的阶梯在最深的几段是空的（A057 76 号席位 1440–2070、B043 16 号 810–1440…），`stair_logorder.mjs` 的表（`stair_logorder.csv`）是证据；`chan_unpaired.mjs` 是另一面（模型多执行的「幽灵」指令落在长空档里）。
- 批次：步骤文件 `scripts/steps/ckpt-all3.txt`（主批次标签 a–o；g0* 放开跑 0→1500；hi* / lo* 阶梯上下界 + 地板，只跑 `band_select.csv` 里选中的窗口；va* vb* vc* 版本互换；p q r = C1p；r06trace*、fill*）。
  后台跑法：tmux 会话 `c136-r01-ckpt` 里 `LOOP_ROUND=1800 bash scripts/ckpt/loop.sh scripts/steps/ckpt-all3.txt out/_ckpt/all5-loop.log`（每轮占一个 run-heavy 槽，`.done` 续跑；日志里找 `LOOP-DONE` / `LOOP-STALLED` / `LOOP-STARVED` / `失败`）。
  c135 组的长任务常把 3 个槽占满，我们组只用得了 1、2 号槽，一轮常要排 15–40 分钟；排不到（退出码 75）loop.sh 会记 `LOOP-QUEUE-TIMEOUT` 接着排，连续 8 次才停。**不要开第二个循环，不要改 HEAVY_SLOTS。**
  步骤文件的次序（464 行；`make_steps_extra.py <选项>` 生成各段，标签见脚本）：swap0 4 → swap 24 → g0 16（0→1500 放开跑）→ span 16（630→3213 放开跑，sp*）→ full 16（0→3213 放开跑，fr*）
  → full5 16（0→5184 或录像结束，fs*）→ swapx 前半 36（版本互换的第 3 个种子）→ swapc110 70（A 局换 c110、B 局换 vb，5 个断面）→ 主批次 83（已完）→ band hi 前 20 → band lo 前 12 → swapvc 12 → c1p 17
  → band 余下 → r06trace / fill 14 → swaplate 24 → swapx 后半 52（3213 / 4284 的补种子）。
  一次性的重活放 tmux 会话 `c136-r01-aux`：`HEAVY_QUEUE=3000 HEAVY_TIMEOUT=300 bash ../../tools/run-heavy.sh node … > out/_ckpt/x.txt 2>&1; echo AUX-DONE >> out/_ckpt/x.txt`（前台排队会超 120 秒）。
  改步骤文件要写到临时文件再 `mv`（正在跑的那一轮还在读旧文件）。结果在 `out/_ckpt/runs/<局>-<t0>-<标签>.json`（不入库），入库的是 `reports/ckpt-data/*.csv|md|json`。
- 汇总：`timeout 120 python3 scripts/ckpt/aggregate.py`（会列出被截断 / 没跑全的臂）；`CKPT_PRIMARY=hi|lo` 可以换主口径。
  表：A 逐局逐窗口、B 分组均值、B2 兵力与活席、C 对数链、D/E 闭环保真度、E2 签名四分位（本报告各局自己的历史）、E3 对照 R06 的实盘区间（`sim-v2/calib/live-bands.json`）、
  F 指令流签名、W 剂量—反应、G 放开跑、T 阶梯三种口径、O 两段次序（C1p）、S1/S2 换阶梯 / 换补法、V 版本互换。
  后加的：M 局清单；C2 链按窗口；H 以 C1 为基线的总账（末尾有按全量 squad10 加权的粗外推）；R 残差大的窗口（生死翻转占多少）；P 对手开环（改打 / 作废占比）；
  K 连乘的前提（跨局回归 ln 涨幅对 ln 起点；按斜率粗修正 C1 路径）；L C1 路径的水平对照 R06 实盘区间的「通道干净」档 + M6 全量表的横向对比；
  G / G2 / G3 / G4 = 一口气放开跑（0→1500、630→3213、0→3213、0→5184）对窗口连乘，都走 `chain_vs_free()`；Z 把这几段的「历史 ÷ C1」连乘与放开跑并排（`ckpt_cumulative.csv`）。
  V 现在认 4 个版本（标签 va* vb* vc* c110*，键里带 stratKey）；汇总行的区间是按局重抽样的 90% 区间。
- 报告正文在模板 `reports/ckpt-data/REPORT.tmpl.md`，`timeout 60 python3 scripts/ckpt/build_report.py` 把 `{{ckpt:表 X:n}}` / `{{ckpt:表 X:note:n}}` / `{{fid:④:4}}` 换成表，写出 `reports/OFFLINE-CHECKPOINT-ATTRIBUTION.md`。
  **改正文只改模板。** 脚本会报没填上的占位符和正文里的「待补」。表的 note 以空行分段计数，往 aggregate.py 里加说明行会改变后面 note 的序号，加完要核对模板。
- 主批次的结论（14 局 68 个窗口）：历史 ÷ C1 路径（连乘到 5184）全部 ×0.50 = 落后波 ×0.70 × 页面 ×0.80 × 残差 ×0.89；深落后 ×0.36；通道干净 ×1.03。
- **连乘 对 一口气放开跑（表 Z、表 G4 的沿途表；报告 §1.1 第 3 条、§4.6 就是围着这个写的）：**
  「历史 ÷ C1」到 1500 / 3213 拍两种算法一致（×0.71 对 ×0.70；×0.55 对 ×0.58；有落后 11 局 ×0.46 对 ×0.49；通道干净 3 局 ×1.06 对 ×1.03）。
  通道模型复现的占比 ln(C2÷C1) ÷ ln(历史÷C1) 不一致：1500 拍 94% 对 81%，3213 拍 84% 对 56%。放开跑的残差（历史 ÷ C2）：630 ×1.01、1500 ×0.94、2400 ×0.94、3213 ×0.79（干净 ×0.98、有落后 ×0.74）、4284 ×0.78、5184 ×0.54（干净 ×0.65）。
  **3213 拍以后放开跑不能用**（通道干净的局 C2 也比历史高一半；C1 水平 1.13 → 1.53 → 1.86；其余真人陆攻 15% 改打或作废、逐人领土偏离 38%），逐窗口的通道效应又很小（×0.98、×0.93）→ 3213 之后的累计数是弱的。
  0→5184 放开跑里 A003、A094、A055 历史在终点 ≈ 0，不进比值（表 G4 的注列了）。沿途表的换算用 humans ÷ 席位数（不能用终点比值反推，历史归零的局会被整局丢掉）。
  外部对照（表 L）：有落后的 7 局 Vb，C1 水平 ÷ 真实干净局中位 1500 拍 ×1.18 / ×1.20、3213 拍 ×1.34 / ×1.22；实盘横向 R06 ×0.81、M6 ×0.58–0.62。表 K 的跨局斜率修正不采用（同局直接核对在 630 接头上没偏差）。
- 版本互换（表 V）：Va / Vb / Vc 在 1500 拍以前逐位相同（PARAMS 的 16 处差别都只在 coreFrom=1500 之后的方法里读）。1500→3213：Vb − Va C1 −0.011、C2 +0.037，|差| 0.06；Vc − Vb |差| 0.01–0.03。
  c110 ↔ c116 家族：630→1500 已有（A 局 12 局：C1 +0.077（+0.035 ~ +0.119），C2 +0.014）；其余断面在跑。c110 的沙箱决策层只到统计量级，读的时候带着。
- 步骤文件现在按价值重排过（已完的在前）：c110 族 @3213 13 → Va/Vb/Vc @3213（C1，2 个种子）24 → r06trace / fill 14 → c110 族 @4284 14 → Va/Vb/Vc @3213 的 C2 与第 3 个种子 24 → Va/Vb/Vc @4284 28
  → 阶梯上下界余下的 32 → 630 / 1500 的第 3 个种子 36。机器负载高（4 核、load 14–21，一步 1–4 分钟），最后两段（68 步）价值低，前面做完就停循环、在报告里写明没跑。
- **run-heavy.sh 被人改过（2026-11-12 16:58，不是我）**：我工作区里 `c136-review/tools/run-heavy.sh` 的默认槽数从 2 变成 4（没提交；联络分支里仍是 2）。17:07 那一轮因此占了 4 号槽 22 分钟。
  17:29 我停了循环，17:30 起改用 `HEAVY_SLOTS=2 LOOP_ROUND=1800 bash scripts/ckpt/loop.sh scripts/steps/ckpt-all3.txt out/_ckpt/all6-loop.log`（只排 1、2 号槽）。没有动那个脚本文件。已报总部（outbox 0020），等回话；没回话之前一直带 `HEAVY_SLOTS=2`。
  停循环的办法：tmux 里 C-c 停不掉（timeout 自成进程组），要按 loop.sh → run-heavy.sh → timeout 的次序 `kill -TERM`（先确认 cwd 是自己的工作区）。
- 分解次序（表 O，17 个窗口的 C1p）：整条链先加页面的话落后波 ×0.70 → ×0.67、页面 ×0.80 → ×0.84，占比 51 / 33 → 58 / 25，两段合计不变。
- c110 ↔ c116 家族（表 V）：A 局换 c110：0→630 −0.024 / −0.013；630→1500 +0.077 / +0.014；1500→3213 −0.088 / −0.056（11 / 12 局负）。B 局换 Vb（c110 − Vb）：−0.011 / −0.012；+0.026 / +0.002；+0.102 / +0.014（和 A 局方向相反）。
- 坑：录像只收真正执行了的捐款（配额拒掉的不进录像）→ 历史臂的 quotaRejectRate 恒 0，要用「影子发出 → 录像落地」比「沙箱发出 → 沙箱落地」。
  机器忙时一条 110 秒的步骤会被截断（A019-1500-a 出过），所以步骤一律带 `--budget-ms 480000` 且用 loop.sh 的 600 秒轮。
  我自己的重演（resim）在 5 局的残局（t ≥ 5310）与真引擎有差，TGame 与真引擎全同——断面窗口都在 5184 以内，不受影响。
