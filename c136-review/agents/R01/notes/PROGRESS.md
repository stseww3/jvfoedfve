# R01 进度与工作笔记（给自己接续用）

## 状态
- M1 完成：A057、A059、A094；M2 完成：A055、A075、A054。全部通过本地机械检查（`python3 scripts/check_my_review.py`）。
- M3 完成：A031（never-grew）、A019（mid-collapse）、A009（never-grew，Va）；m3-reviews 报告已发（里面更正了 A075 的判定数：错 10 / 不清 5 / 对 5）。
- M4 完成：A023（never-grew；错 9 / 不清 8 / 对 3；新模式 AT12、AT13）；A050（external；错 9 / 不清 5 / 对 6；新模式 EG03）；A003（never-grew，Va；错 7 / 不清 9 / 对 3；新模式 SP04、DN13）。
- M5 进行中：A005 完成（external，Va；错 4 / 不清 6 / 对 2；新模式 SP05、OP04）→ B039 → B043；然后 M6。
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
- [ ] A005  - [ ] B039  - [ ] B043   （M5）
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

