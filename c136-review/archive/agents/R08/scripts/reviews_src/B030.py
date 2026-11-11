# B030 人工分析部分。这个对局包里混了三个物理房间（同一个开局键 mode=7 / map=19 / mapSeed=8091 / seeded=6），只有录像所在的房间 0 有局内数据。
#   房间 0 是自由混战（录像头 numberTeams=0）：6 个真人 + 506 个内置 AI；5 个编队账号进场，2 个在 t=168 离开，剩下 3 个打到最后只剩 1 个，t=113679 获胜。
#   真值：scripts/resim_r08.mjs 逐拍重演到 t=37561（录像只到这里，占全场 33%），214/214 条 traj 快照地、兵都一致；之后只有赢家自己的日志。
#   出处：out/B030/digest.txt、truth.txt [TA]~[TO]、shadowcmp.txt [SA]~[SJ]、aigate.txt [GA]~[GJ]、aiwatch_ai101.txt、harvest.txt、top.txt、spawncheck.txt、
#         shadow_full.json（trshow.py 看逐报价重走 buyLand 的 walk）。L 号 = bundles/B030/in_game.log 每行开头的原始行号。
from patterns_catalog import pick

C110 = "src/strategy/v27-team-c110.js"
SIM = "src/sim/sim"

BUY_AI = f"{C110}: Policy.buyLand L5250-5548 的非真人分支 L5363-5368（L5367：x < minCmd 就 continue）；minCmd L521-523（feeK × ⌊12×余额/1024⌋，feeK=4 → 余额的 4.69%）"
BUY_PERSON = f"{C110}: Policy.buyLand L5250-5548（L5261 over；L5265 超软上限后不再按价格收手；L5267-5271 唯一缓冲；L5322-5326 safe 及封顶；L5348-5358 超软上限留底；L5360-5361 avail；L5543-5548 chunk 门槛后发出）"
SAFE = f"{C110}: Policy.safeAt L4524-4541 → safeAt L2744-2754 → safeFinite L2532-2541 / L2773-2784 → threatOf L464-490（sb = 人机邻居眼里『除我以外最弱的邻居』的余额）"

R = dict(
    contextExtra=dict(
        bundleRooms="对局包把同一个开局键的三个物理房间混在一起：15 个编队账号记了 HL-GAME-INIT（L8606333~8606365），只有 Luxembourg、Nader Shah、Landsknecht 三个有 HL-TICK。"
                    "另外两个房间的 10 个号（Doncic、Madara、Sasuke、Oyo、JessePinkman / First Empire、Netherlands、Cheese、Song、Panama）只有开局前的出生行，没有任何局内数据，本文不写。"
                    "房间表把玩家号 1、2、5 记成了别的房间的号，按录像头改回：1 = sudo_rm_rf、2 = Vasa、5 = Player 765（不是编队号）（r08lib._fix_rooms_by_replay，context.replayFixes）。",
        replayFixes=["玩家号 1：房间表写 Doncic，录像头是 sudo_rm_rf", "玩家号 2：房间表写 Madara，录像头是 Vasa", "玩家号 5：房间表写 JessePinkman，录像头是 Player 765（名字不在名字池里）"],
        roomTruth=dict(mode="自由混战：录像头 numberTeams=0，结果行 team=null；引擎里每个人互为敌人，不能捐款，胜利条件是一个人拿下全部陆地（game.js victoryTick L1398-1412）",
                       land=402147, players=512, humans=6, builtInAi=506,
                       humansList=[dict(me=0, name="Luxembourg", note="编队号，在线；t=5647 阵亡"),
                                   dict(me=1, name="sudo_rm_rf", note="编队账号（名字在名字池里，日志有 HL-GAME-INIT 和 3 条 HL-SPAWN，squad=5）；一条进攻指令没发，t=168 执行『离开』，t=884 被 AI27 吃掉"),
                                   dict(me=2, name="Vasa", note="同上；t=168 离开，t=899 被 AI165、AI15 吃掉"),
                                   dict(me=3, name="Nader Shah", note="编队号，在线；t=5359 阵亡"),
                                   dict(me=4, name="Landsknecht", note="编队号，在线；t=113679 获胜"),
                                   dict(me=5, name="Player 765", note="不是编队号；t=0 离开，一格地没有")]),
        squadMateProtection="房间里从头到尾没有『不在名字池、领土 ≥80 的活人』：hasWildOutsidersAlive（c110 L3978-3990）一直是 false，isProtectedSquadMate（L3993-3996）对编队友返回 false。"
                            "所以三个在线号在策略眼里从第 0 拍起互为普通真人敌人；源码注释写明这是有意的（野人死光后解除跨队保护，只留一家）。",
        labels="日志标签中途换名：玩家号 0 = Luxembourg>MasterChief>Transvaal；玩家号 4 先后用了 77 个名字（Landsknecht>Heisenberg>…>CocaCola，结果行写的是 CocaCola）。本文一律用录像头里的名字。",
        clock="结果行：Nader Shah t=5363 / 320 秒，Luxembourg（Transvaal）t=5653 / 336 秒，Landsknecht（CocaCola）t=113679 / 6386 秒（02:24:11Z~04:10:37Z），全场平均每拍 56.2 毫秒。",
        replayCoverage="录像到 t=37561；之后的 76118 拍只有赢家自己的 846 条 HL-TICK 和 HL-SLOW-TICK，内置 AI 的状态看不到。",
        cardNote="对局卡写 nominalTeams=2、actualTeams=2、squadBots=3、peakSquadLandShare=1.0、won、endTick=113679、slowTicks=1621。『2 队』是名义值，真值没有队；"
                 "facts.py 对『没有队、但有编队号拿到 won』的房间记 ffaWin，result 才是 won。",
        truthScriptCaveat="truth.py / harvest.py 把没有 HL-TICK 的 sudo_rm_rf、Vasa 算在『其它真人』里（[TN] 的 2 人、[TI] 说编队没人离开）；它们是编队账号，离开拍取自 resim.json 的 leftT。",
    ),
    outcomeExtra=dict(
        winnerHow="Landsknecht（玩家号 4）在 t=113679 拿下全部 402147 格，结果行 end / won / place=1，余额 48801819，发令 232 条、被接受 225 条（日志计数 cmds=219、boats=47）。",
        ticksAfterLastOtherHuman=dict(lastOtherHumanDied=5647, endTick=113679, ticks=108032, note="全场只剩一个真人以后又打了 108032 拍；按每拍 56.2 毫秒是 101 分钟"),
        squadPlaces="Nader Shah 第 23 名（峰值 63584 格）、Luxembourg 第 22 名（峰值 103938 格）、Landsknecht 第 1 名：前两个都是被编队友打死的。",
    ),
    phases=dict(
        spawn=dict(
            window="0~90",
            facts=[
                "房间 0 进了 5 个编队账号，各自按『squad=5』排槽位（L8606362~8606391 三轮指派）。在线的三个号各 4 条指派，引擎落点都是第 3 条：Luxembourg (434,274)、Nader Shah (210,466)、Landsknecht (722,498)（spawncheck [PA]）。",
                "第 4 条指派（L8606399 / 8606402 / 8606404，候选点从 9 个变成 48 个）紧挨着 t=70 的第一条 HL-OPENING 打出来，引擎没有执行。",
                "三个在线号的引擎落点两两相距 295 / 365 / 513 像素，没有 <40 像素的号对。sudo_rm_rf 落在 (210,642)、Vasa 落在 (738,194)，都是各自的最后一条指派。",
            ],
            problems=[
                "5 个进场的编队账号里 2 个没有打：sudo_rm_rf、Vasa 没有一条 HL-OPENING / HL-TICK，录像里唯一的指令是 t=168 的『离开』（同一拍）。原因不在数据里。",
            ],
        ),
        opening=dict(
            window="90~630",
            facts=[
                "[OPENING-CHECK 3 bots @ tick 208] 三个号都是 sent=6(OK)（L8606421）。第一条开局单决策拍 70，执行拍 119 / 147 / 154（晚 49~84 拍，shadowcmp [SG]），之后时延中位 9~17 拍。",
                "t=630：3468 / 3097 / 2853 格，合计 2.34%。(270,630] 吃空地 7667 格（全房 7897 格）、吃人机 598 格（2.7 兵/格）（harvest）。",
                "t=160 sudo_rm_rf、Vasa 各 12 格 / 1420 兵没动过；t=168 离开后由引擎托管（峰值 66 / 120 格），t=884 / t=899 被内置 AI 吃掉。",
            ],
            problems=[],
        ),
        midgame=dict(
            window="630~3500",
            facts=[
                "吃人机：(630,900] 9310 格（3.1 兵/格）、(900,1260] 34636 格（3.5）、(1260,1800] 114004 格（3.7）、(1800,2700] 103839 格（3.5）；到 t=2700 共 262387 格（harvest）。",
                "编队份额 5.41%（t=900）→ 23.57%（1440）→ 59.91%（1980）→ 73.66%（2520）→ 峰值 74.99%（t=2730，301584 格）。活着的内置 AI 448 → 142 → 48 → 27 → 25 个（aigate [GK]）。",
                "三个号最后一条打人机的指令：Nader Shah t=2177（AI91）、Landsknecht t=2310（AI236）、Luxembourg t=2422（AI91）。t=2700 之后到 t=9709，编队从内置 AI 手里一格没拿（真值逐对战损账）。",
                "门槛普查（影子每 30 拍）：t=1500~2400 的 69 个号·点里 20 个有人机过门槛，49 个全被挡（留底 sb 34、minCmd 12、价格 2、chunk 1）；t=2400~3300 的 89 个点全被挡（sb 56、minCmd 29、sb 封顶 4），"
                "其中 78 个点『单个最大的 want』小于 minCmd、51 个点『吃光所有人机邻居所需合计』小于 minCmd（aigate [GA]）。",
                "t=2100~3000 的 10 拍普查：267 个点 259 个被挡，其中 231 个是 sb，全部由编队友的余额定出（Nader Shah 121 个点、Luxembourg 105 个点）；minCmd 87 个点里 Landsknecht 占 79 个（shadowcmp [SJ]）。",
                "编队余额 565 万（t=2730）→ 1656 万（t=3300）→ 2769 万（t=3600），密度 18~28 → 53~70 → 96~110。同期内置 AI 23 个 / 合计 3120 兵（t=2790，15 个 0 兵）→ 22 个 / 5813 兵（t=3600，19 个 0 兵）（aigate [GK]）。",
                "同一次决策发两条指令的 19 次里，第 2 条（都是打人机的陆攻，本意兵力最大 50567）一条没落地（shadowcmp [SI]）。",
            ],
            problems=[
                "t=2422 起没有一个号对人机出得了手：最富的 Landsknecht 被 minCmd 挡（余额越多门槛越高，人机越小越过不了），另外两个被留底 sb 挡（sb = 共用人机邻居的编队友的余额，高过自己全部余额）。",
                "t=2790~4010 编队被合计不到 1 万兵的人机拿走 36038 格：人机只花了 177080 兵，编队余额被打掉 4329046（每格 120.1）（aigate [GI]）。",
            ],
        ),
        endgame=dict(
            window="3500~113679",
            facts=[
                "t=3990：三个号 126702 / 90907 / 48156 格，密度 141.0 / 141.8 / 142.7，合计 37632011 兵；22 个内置 AI 合计 136172 格、9544 兵（20 个是 0 兵），按策略自己的算法吃光它们要 221246 兵。",
                "t=4011~5621 编队号互打 16 条陆攻：122998 格，攻方耗兵 41671619（每格 338.8），守方余额被打掉 20359286（aigate [GG]）。同一段（t=4010~5670）编队从人机手里拿 0 格，被人机拿走 40913 格。",
                "Nader Shah t=5359、Luxembourg t=5647 阵亡，Landsknecht 220162 格（54.75%）独自面对 20 个内置 AI（176638 格、4347 兵）。",
                "t=5670~9700：Landsknecht 被人机拿走 110912 格（人机耗兵 2395950，自己余额被打掉 25667280，每格 231.4），自己拿人机 0 格、空地 18352 格；领土 54.75% → 31.73%，密度 93 → 148.9。",
                "t=9709 打 AI101（927474 兵 + 手续费 222593）：AI101 145080 格在 t=9752 坍缩，t=9840 Landsknecht 265828 格（66.10%）。此刻剩 3 个内置 AI 合计 131525 格、0 兵。",
                "之后是同一个循环：顶在 150 倍硬上限上丢地 → 人机长到够大 → 一条指令打回来。t=21511 打 AI124（142691 → 290274 格）；日志尾段 t=39510（117207 → 251021）、t=52290（174476 → 393966）、t=112680（165546 → 364063）。",
                "t≥1500 的录像段里 Landsknecht 密度 ≥149 的拍数 27370 / 36080；密度 ≥100 时被人机拿走 421264 格（人机耗兵 29973544，自己余额被打掉 98553560），自己从人机手里拿 96266 格只花 846393 兵（aigate [GD]）。",
                "两次扫尾：t=52560~53010 24 条船把缺口从 8181 格收到 74 格，随后 405 拍一次水路搜索都没做，t=53370 冒出一个敌邻；之后 59670 拍一条指令没发，领土 100% → 41.2%。"
                "第二次 t=112860 起 23 条船，中间同样停了 400 拍，t=113679 获胜（aigate [GJ]）。",
            ],
            problems=[
                "三个号超过软上限后只有编队友过得了门槛：t=4000 Landsknecht 跳过 10 个人机报价（每格 14.9~68.7 兵，吃光合计 132888 兵），把 3655334 兵（余额的 20%）按每格 499 兵打向 Luxembourg。",
                "t=9840 全场的内置 AI 都是 0 兵，吃光要 197290 兵，Landsknecht 有 21965507 兵，没有打；t=10039 AI101 靠一条在途的船带着 1 格地回来，也没有打。",
                "从全场只剩一个真人（t=5647）到获胜又打了 108032 拍（101 分钟）。",
            ],
        ),
    ),
    turningPoints=[
        dict(
            t0=2730, t1=4010, shareBefore=74.99, shareAfter=65.91, shareUnit="三个在线编队号合计占陆地 %（真值；t=2730 是全场峰值 301584 格，t=4010 是 265065 格）",
            what="吃到 75% 以后三个号同时停手：1280 拍里从内置 AI 手里一格没拿，余额从 565 万囤到 3763 万（密度 141~143），反被合计不到 1 万兵的人机拿走 3.6 万格。"
                 "挡住最富的 Landsknecht 的是最小指令门槛，挡住另外两个的是防人机留底 sb（= 编队友的余额），密度过 88 以后也换成最小指令门槛。",
            evidence=[
                "aigate [GA]：t=2400~3300 89 个号·点全被挡（sb 56、minCmd 29、sb 封顶 4），中位余额 2124558、minCmd 99588、人机邻居合计 42476 格 / 12685 兵、吃光合计 82599；"
                "t=3300~4200 88 个点全被挡（minCmd 73、sb 封顶 12、sb 3），中位余额 9596549、minCmd 449836、人机邻居 52597 格 / 0 兵、吃光合计 80911——88 个点全部是『吃光所有人机邻居的总花费 < minCmd』。",
                "aigate [GH] Landsknecht t=3000：11 个人机报价（66160 格 / 22982 兵，吃光合计 139239，每格 9.4~23.8）全部 skip:x<minCmd（197488）；t=3600：10 个（78955 格 / 0 兵，吃光 117996）全部跳过，minCmd 604896。",
                "aigate [GH] Luxembourg t=2520 / 3000：6 / 9 个人机报价全部 skip:avail<=0（留底高过余额）；Nader Shah t=2100 / 2520 / 3000 同样。shadowcmp [SJ]：这段 231 个 sb 点全部由编队友的余额定出。",
                "真值逐对战损账：三个号最后一条打人机的指令在 t=2177 / 2310 / 2422；(2700,4010] 编队拿人机 0 格、空地 1799 格；被人机拿走 36038 格，人机耗兵 177080，编队余额被打掉 4329046（aigate [GI]）。",
                "aigate [GK] t=3990：22 个内置 AI 合计 136172 格 / 9544 兵（20 个 0 兵），吃光 221246 兵；编队三个号合计 37632011 兵，是它的 170 倍。",
            ],
            priorDecisions=[
                dict(t="2422~4000", bot="Landsknecht", decision="每 5 拍重算一次，人机报价的 x = min(可用兵, 1.25×吃光所需 + 3×接壤格数) 小于 minCmd 就跳过；余额从 99 万涨到 1806 万，minCmd 从 4.6 万涨到 84.6 万，人机越吃越过不了门槛",
                     codePath=BUY_AI, judgement="error", why="门槛按自己余额的比例定，目标却是越小越便宜；到 t=3300 以后连『把所有人机邻居一次吃光』都不到门槛"),
                dict(t="2100~3300", bot="Luxembourg / Nader Shah", decision="打人机前的留底取 sb；两个号和 Landsknecht 共用人机邻居，sb 就是 Landsknecht（或彼此）的余额，高过自己的全部余额，可用兵 ≤0",
                     codePath=SAFE + "；buyLand L5322-5326（非真人目标按 88×领土封顶）", judgement="error", why="留底防的是『人机挑最弱的邻居下手』，但这里人机全是 0 兵；密度不到 88 的号被锁死"),
                dict(t="2790~4010", bot="三个号", decision="人机来啃地时不还手：counterAttack 跳过内置 AI，counterK=0 时本身也不发",
                     codePath=f"{C110}: counterAttack L871-887（L874-875 对 g.isBot 的进攻者 continue；L884 send = min(…, counterK×most)，counterK=0）；{SIM}/game.js expandAttack L1016-1020（fresh && counter === 0 必赢）",
                     judgement="error", why="守方只要有兵压在人机身上，人机新开进攻的第一圈就不再白拿；三个号一个兵没压"),
            ],
            statementType="observed",
        ),
        dict(
            t0=4000, t1=5647, shareBefore=65.91, shareAfter=54.75, shareUnit="在线编队号合计占陆地 %（真值；t=4010 三个号 265065 格，t=5670 只剩 Landsknecht 220162 格）",
            what="三个号超过软上限后互相开打：Landsknecht t=4000 先打 Luxembourg（每格 499 兵），Nader Shah 15 拍后跟进；Luxembourg 被 sb 锁着 2583 拍一条指令没发，快死时反打 Nader Shah；"
                 "Landsknecht 再回头把两个都吃掉。1636 拍里烧掉 4167 万兵换编队内部的 12.3 万格，同期人机（合计不到 3.5 万兵）从编队手里拿走 4.1 万格。",
            evidence=[
                "aigate [GH] Landsknecht t=4000：余额 18057570 / 126702 格（密度 142.5），minCmd 846448；10 个人机报价（88649 格 / 0 兵，吃光合计 132888，单个最大 want 40847，每格 14.9~68.7）全部 skip:x<minCmd；"
                "Luxembourg 报价每格 499：safe 12978295（= Luxembourg 的余额）、keep 14190624（= 1.12×100×领土，唯一缓冲的留底）、avail 3655334 ≥ chunk×余额 3611514 → SEND。录像 t=4011 实发 3678580 + 手续费 212225。",
                "aigate [GH] Landsknecht t=3900 / 3995：同一个报价 skip:x<chunk（3002049 < 3521715；3470071 < 3574022）——差的只是可用兵够不够余额的 20%，5 拍后利息把它推过线。",
                "aigate [GH] Nader Shah t=3600 skip:soleBuffer、t=3900 skip:avail<=0(safe)（safe 12623250 = Luxembourg 的余额）；t=4015 Luxembourg 带 bleeding 标记，safe 封顶到 88×领土 = 4221624、keep 4317570、avail 2508536 → SEND（录像 t=4032 实发 2518493）。",
                "aigate [GH] Luxembourg t=3600~4990 七个追踪点：8~11 个人机报价全部 skip:x<minCmd，两个真人报价全部 skip:avail<=0(safe)，safe = Landsknecht 的余额（t=4000：18057570，自己只有 12978295）。"
                "录像里 Luxembourg 从 t=2422 到 t=5005 没有一条指令，领土 94524 → 32785 格。t=4995 Nader Shah 带 bleeding 标记才放行（实发 1039685）。",
                "aigate [GG]：16 条互打的陆攻，Landsknecht→Luxembourg 55311 格 / 耗兵 22375959（404.5/格），Nader Shah→Luxembourg 20022 格 / 9240185（461.5），Landsknecht→Nader Shah 43130 格 / 9127863（211.6），"
                "Luxembourg→Nader Shah 4535 格 / 927612（204.5）；每一条发出的那一拍，攻方都接壤 6~18 个人机（44826~172031 格，吃光合计 67236~282031 兵）。",
                "aigate [GI] t=4010~5670：编队被人机拿走 40913 格（人机耗兵 209840，编队余额被打掉 7386225），编队拿人机 0 格；内置 AI 136172 → 176638 格。",
            ],
            priorDecisions=[
                dict(t="4000", bot="Landsknecht", decision="超软上限（over）后不再按价格收手；人机报价全被 minCmd 挡，唯一过得了门槛的是编队友 Luxembourg：留 1.12×100×领土，其余 3655334 兵（余额的 20.2%）按每格 499 兵发出",
                     codePath=BUY_PERSON + f"；isProtectedSquadMate L3993-3996（没有野人活着 → false）", judgement="error",
                     why="同一拍 10 个人机报价每格 14.9~68.7 兵、吃光只要 132888 兵（余额的 0.7%），被跳过；选中的是全场最贵的目标"),
                dict(t="4015 / 4400", bot="Nader Shah", decision="Luxembourg 一挨打就带上 bleeding，对它的 safe 从『Luxembourg 的余额』改成 88×领土封顶，立刻放行：2518493、1977876、1471622、1842188、1430527 五条",
                     codePath=f"{C110}: Policy.buyLand L5323-5326（person 目标只有 nearCollapse / bleeding / tD<0.45 时才按 oppFloorCap×领土封顶）、L5348-5358（非唯一缓冲时 keep = 0.9×100×领土）", judgement="error",
                     why="跟着最富的号一起打编队友，每格 461.5 兵；自己随后被 Landsknecht 以每格 211.6 兵吃掉"),
                dict(t="2422~5005", bot="Luxembourg", decision="对两个真人邻居的 safe = Landsknecht 的余额（不封顶），可用兵一直是负的；对人机被 minCmd 挡。2583 拍零指令，挨打期间也不还手；t=4995 Nader Shah 流血才放行，打出 1039685 + 812858 兵",
                     codePath=SAFE + "；buyLand L5358 keep = max(keep, safe)、L5360-5361", judgement="error",
                     why="三个号里第二富的号，从 12978295 兵 / 90721 格被打到 4198843 兵 / 34045 格，期间一条指令没发"),
            ],
            statementType="observed",
        ),
        dict(
            t0=9700, t1=10050, shareBefore=31.73, shareAfter=65.18, shareUnit="Landsknecht 占陆地 %（真值；t=9700 127602 格，t=9840 265828 格 = 66.10%，t=10050 262121 格）",
            what="唯一一次『人机全是 0 兵、一手就能收官』的窗口没有收：t=9709 一条指令打坍 AI101 之后，剩下的 3 个内置 AI 合计 131525 格、0 兵，吃光要 197290 兵，Landsknecht 有 2197 万兵，全部被 minCmd 跳过。"
                 "AI101 坍缩时有一条船在海上，引擎不除名，t=10039 靠岸带着 1 格地回来，同样没人打。之后的一万多拍 Landsknecht 顶着硬上限又丢回 13.3 万格。",
            evidence=[
                "aigate [GH] Landsknecht t=9700：AI101 的 want 916040 ≥ minCmd 890372 → SEND（录像 t=9709 实发 927474 + 手续费 222593）；t=9690 还是 5 个人机报价全部跳过。",
                "aiwatch_ai101：t=9700 AI101 145080 格 / 286364 兵、在途船 1 条；t=9737 余额 153684 → 2854；t=9752 领土 36854 → 0（坍缩）但『活着』仍是 1；t=10039 船靠岸，t=10042 1 格，t=10050 7 格 / 1 兵，t=10078 84 格 / 3 兵。",
                "aigate [GH] Landsknecht t=9840：余额 21965507 / 265828 格，minCmd 1029632；3 个人机报价（AI312 66264 格、AI124 48819 格、AI347 16442 格，合计 131525 格 / 0 兵，吃光合计 197290，单个最大 want 127122）全部 skip:x<minCmd。",
                "aigate [GI] t=9700~9840：拿人机 111397 格只花 671810 兵（6.0/格）、顺带拿空地 29766 格；t=9840~21500：拿人机 0 格，被人机拿走 133087 格（人机耗兵 13069081，自己余额被打掉 31643241，每格 237.8）。",
                "aigate [GH] t=12000：3 个人机报价（165054 格 / 46778 兵，吃光合计 330960）全部跳过，minCmd 1638056，密度 150.0。AI101 到 t=36000 长回 103939 格，录像期内再没挨过 Landsknecht 的打。",
            ],
            priorDecisions=[
                dict(t="9709", bot="Landsknecht", decision="AI101 长到 145080 格 / 28.6 万兵时 want 才第一次超过 minCmd，按 1.25×吃光所需 + 3×接壤格数一次打坍",
                     codePath=BUY_AI + f"；elimCost L511-517", judgement="good", why="111397 格只花 671810 兵；这一手本身没有问题，问题是它要等到人机比自己还大才触发"),
                dict(t="9840~21500", bot="Landsknecht", decision="剩下 3 个 0 兵人机和回来的 AI101 的 want 都小于 minCmd（103 万~164 万），每 5 拍重算、每次跳过",
                     codePath=BUY_AI, judgement="error", why="吃光全部人机只要余额的 0.9%；不吃的结果是又丢 13.3 万格、被打掉 3164 万兵"),
                dict(t="9752~10050", bot="引擎规则", decision="玩家坍缩时如果有船在海上：清空领土但不除名，船靠岸后重新有地",
                     codePath=f"{SIM}/game.js collapse L1314-1335（有船的分支 L1316-1331）、aliveTick L1298-1312", judgement="unclear", why="不是策略决策；策略里没有『盯住坍缩后还活着的对手』这一条"),
            ],
            statementType="observed",
        ),
        dict(
            t0=52560, t1=53370, shareBefore=98.0, shareAfter=100.0, shareUnit="Landsknecht 占陆地 %（只有日志：t=52560 393966 格，t=53010~53280 402073 格，t=53370 402067 格且 nb=1）",
            what="第一次打到 100%（差 74 格）没有赢下来：24 条扫尾船之后 405 拍一次水路搜索都没做，t=53370 重新冒出一个敌邻（-6 格）。"
                 "之后 59670 拍一条指令没发，顶着硬上限从 402073 格被啃到 165546 格（41.2%），t=112680 才打回去，第二次扫尾在 t=113679 获胜。这一段没有录像，敌邻是谁、怎么来的是推断。",
            evidence=[
                "aigate [GJ]：t=52560~53280 9 条快照 nb=0，领土 393966 → 402073（缺口 8181 → 74 格），船 0 → 24；慢拍（水路搜索）24 条，从 52595 到 52985，三条一组；t=52985 → 53390 之间 405 拍没有慢拍，"
                "期间 4 条快照领土都是 402073、nb=0、neut=0，余额 44409983 → 58327106。",
                "L（HL-TICK）t=53370：terr=402067、nb=1；t=53460：402086、nb=1、cmds=195、boats=24 不变。之后的慢拍每 60 拍一条（53390、53450、53510…），船数一直是 24。",
                "aigate [GF]：全程最长的零指令段 t=53010~112680（59670 拍），领土 402073 → 165546（100.0% → 41.2%），余额 44409983 → 24831900，密度 110.5 → 150.0。",
                "aigate [GJ] 第二次：t=112860~113670 领土 364063 → 402139，船 24 → 47；同样在 402073 格（差 74 格）停住，t=113210 → 113610 之间 400 拍没有慢拍，之后 65 拍里 10 次搜索、8 条船，t=113679 结果行 won。",
                "引擎侧可以解释的机制：victoryTick 要求全部陆地且没有敌方的船在海上；坍缩时有船在海上的玩家不除名（本局 t=9752 的 AI101 就是实证）。",
            ],
            priorDecisions=[
                dict(t="52595~52985", bot="Landsknecht", decision="扫尾分支每次决策发一条船去最大的那块空地；在途条数由 base boatOut 按 maxBoats=2 卡，扫尾分支自己写的 6 条上限轮不到",
                     codePath=f"{C110}: Policy.idleBoats L4979-5006 的扫尾分支 L4981-4988（boatCount ≥ 6 才不发）→ boatOut L2360-2365 → base boatOut L1035-1051（L1037：boatCount ≥ P.maxBoats 就返回，maxBoats=2）；"
                              f"searchWater L1056-1115（空地的 eff = 2×exp(0.004×距离) + 手续费÷这块空地的格数，手续费是余额的 32/1024）",
                     judgement="unclear", why="405 拍 / 400 拍的空档两次都出现在同一个 402073 格上；推断是最后几条船去了远处的岛、占着在途名额。真机的 boatCount 看不到，定不了"),
                dict(t="53370~112680", bot="Landsknecht", decision="重新出现的敌邻只有几格地，want 远小于 minCmd（余额 5959 万时是 279 万），每 5 拍跳过一次；一直等到自己只剩 165546 格（对方最多 23.7 万格）才打",
                     codePath=BUY_AI + f"；isMopUp L4501-4514（nb≥1 时不是扫尾，改走普通闲置船分支 L4989-5005：每 60 拍搜一次、要求比最便宜的邻居划算）", judgement="error",
                     why="59670 拍（按每拍 56.2 毫秒是 56 分钟）顶着硬上限不动；和 t=9840、t=5700 是同一道门槛"),
            ],
            statementType="inferred",
        ),
    ],
    deathNotes={
        "Nader Shah": dict(
            cause="被编队友 Landsknecht 打死。自己先在 t=4032~4956 对 Luxembourg 发了 5 条陆攻（9240185 兵换 20022 格，每格 461.5），余额从 6932626（t=4032）掉到 4131608（t=4991），密度 144.5 → 66.4；"
                  "t=4991 起 Landsknecht 以 3 条陆攻（3465169 + 3654761 + 2628426 兵）吃掉它 43130 格，Luxembourg 也趁它流血打了 2 条（4535 格）。t=5359 阵亡时还有 14113 格、657949 兵。"
                  "从 t=2177 到阵亡没有对人机发过一条指令：t<3300 被 sb 锁（sb = Luxembourg 或 Landsknecht 的余额），之后被 minCmd 挡。",
            chain=["t=2177 最后一条打人机的指令（AI91）", "t=3990 48156 格 / 6870673 兵（密度 142.7）", "t=4032 打 Luxembourg 2518493 兵", "t=4403 / 4417 / 4942 / 4956 再打 4 条",
                   "t=4991 Landsknecht 打来 3465169 兵；62177 格 / 4131608 兵（密度 66.4）", "t=5005 / 5222 Luxembourg 也打来", "t=5313 Landsknecht 第 3 条；26250 格 / 1664895 兵", "t=5359 阵亡（14113 格 / 657949 兵）"],
            statementType="observed"),
        "Luxembourg": dict(
            cause="被两个编队友打死。t=2422 之后 2583 拍一条指令没发：对人机被 sb / minCmd 挡，对两个真人邻居的 safe = Landsknecht 的余额（比自己全部余额还多）。"
                  "t=4011 起挨 Landsknecht 6 条（55311 格）、Nader Shah 5 条（20022 格），余额被打掉 15379848；t=4995 才因为 Nader Shah 流血放行，打出 2 条共 1852543 兵。t=5647 阵亡时还有 13227 格、1076952 兵。",
            chain=["t=2422 最后一条打人机的指令（AI91）", "t=2750 峰值 103938 格", "t=3990 90907 格 / 12891228 兵（密度 141.8）", "t=4011 Landsknecht 打来 3678580 兵", "t=4032 Nader Shah 打来 2518493 兵",
                   "t=4500 49828 格 / 6215440 兵", "t=5005 第一条指令：打 Nader Shah 1039685 兵", "t=5488 / 5621 Landsknecht 最后 2 条（4527884 + 4104922 兵）", "t=5647 阵亡（13227 格 / 1076952 兵）"],
            statementType="observed"),
        "sudo_rm_rf": dict(
            cause="不是局内决策：编队账号进了房间、排了出生点（3 条 HL-SPAWN，引擎落点 (210,642) 是最后一条），之后没有一条 HL-OPENING / HL-TICK，录像里唯一的指令是 t=168 的『离开』。"
                  "12 格 / 1420 兵留给引擎托管（空壳自己长到过 66 格），t=884 被 AI27 吃掉（阵亡时 13 格）。",
            chain=["t=0 出生 (210,642)", "t=160 12 格 / 1420 兵，没有发过进攻指令", "t=168 执行『离开』（和 Vasa 同一拍）", "空壳峰值 66 格", "t=884 被 AI27 吃掉"],
            statementType="observed"),
        "Vasa": dict(
            cause="同 sudo_rm_rf：出生在 (738,194)（最后一条指派），没有任何局内日志，t=168 执行『离开』；空壳由引擎托管，长到过 120 格，t=899 被 AI165、AI15 吃掉（阵亡时 24 格）。",
            chain=["t=0 出生 (738,194)", "t=160 12 格 / 1420 兵", "t=168 执行『离开』", "空壳峰值 120 格", "t=899 被 AI165 / AI15 吃掉"],
            statementType="observed"),
    },
    decisions=[
        dict(id="D01", t="0~90", bot="Luxembourg / Nader Shah / Landsknecht", decision="出生点：各 4 条指派，引擎落点是第 3 条；第 4 条（候选从 9 个变 48 个）在开局后才算出来，没有执行。三个号相距 295~513 像素。",
             codePath=f"{C110}: Policy.chooseSpawn L4007-4064", verdict="unclear", patternId="NEW-SP-05",
             evidence=["spawncheck [PA][PC]：3 个号人均 4.0 条指派，最后一条被执行 0 个；<40 像素号对 0", "L8606399 / 8606402 / 8606404：第 4 条指派 chosenSlots=15/48、9/48、16/48，紧挨 t=70 的 HL-OPENING"],
             statementType="observed"),
        dict(id="D02", t="90~630", bot="三个号", decision="开局按周期扩张：OPENING-CHECK 三个号全部 OK；t=630 人均 3139 格，(270,630] 拿下全房 97% 的空地。",
             codePath=f"{C110}: Policy.act L4781-4944（开局 DP 周期，HL-OPENING）", verdict="good", patternId="NEW-OP-G1",
             evidence=["L8606421 [OPENING-CHECK 3 bots @ tick 208] 三个号 sent=6(OK)", "harvest 窗口 (270,630]：吃空地 7667 / 7897 格", "真值 t=630：3468 / 3097 / 2853 格"], statementType="observed"),
        dict(id="D03", t="630~2700", bot="三个号", decision="人机期收割：262387 格人机地，每格 3.1~3.7 兵；编队份额从 5.41%（t=900）到 74.99%（t=2730），活着的内置 AI 从 448 个降到 25 个。",
             codePath=f"{C110}: Policy.buyLand L5250-5548 的非真人分支 L5363-5368（want = 1.25×吃光所需 + 3×接壤格数）；t<1500 的口粮门槛 winFloor L4542-4550 / dpKeep L2491-2496 / safeFinite L2532-2541（shadowcmp [SH]）",
             verdict="good", patternId="NEW-AT-G1",
             evidence=["harvest：(630,900] 9310 格 3.1 兵/格、(900,1260] 34636 格 3.5、(1260,1800] 114004 格 3.7、(1800,2700] 103839 格 3.5", "aigate [GK] t=2730：301584 格（74.99%）", "aigate [GH] Luxembourg t=2100：AI 报价每格 5.6 → SEND"],
             statementType="observed"),
        dict(id="D04", t="1500~2265", bot="三个号", decision="同一次决策先发空地单、再发打人机的单：19 次里第 2 条一条没落地，被丢掉的都是打人机的陆攻（本意兵力最大 50567）。",
             codePath=f"{C110}: Policy.act L4901（expandNeutral）→ L4902（buyLand）同一拍各发一条；文件头 L19-31 的在途保护（450 毫秒 / 8 拍）", verdict="error", patternId="NEW-EX-05",
             evidence=["shadowcmp [SI]：单条 308/327 配上，多条的第 1 条 18/19，第 2 条及以后 0/19", "shadowcmp [SI] 逐次：t=2200 Luxembourg →AI91 50567 无；t=2060 Nader Shah →AI91 45358 无；t=2265 Nader Shah →AI501 39154 无"],
             statementType="observed"),
        dict(id="D05", t="2100~3300", bot="Luxembourg / Nader Shah", decision="打人机前的留底取 sb：共用人机邻居的编队友越富，自己的留底越高；两个号的可用兵一直 ≤0，贴着 0 兵的人机不出手。",
             codePath=SAFE, verdict="error", patternId="NEW-EC-08",
             evidence=["shadowcmp [SJ]：t=2100~3000 231 个 sb 点全部由编队友的余额定出（Nader Shah 121、Luxembourg 105）", "aigate [GA]：t=2400~3300 safe:sb 56 个点 + 封顶 4 个点",
                       "aigate [GH] Luxembourg t=3000：9 个人机报价（42307 格 / 7380 兵，每格 9.5~25.7）全部 skip:avail<=0"],
             statementType="observed"),
        dict(id="D06", t="2422~4000", bot="Landsknecht", decision="最富的号被最小指令门槛挡：人机报价的 x 小于余额的 4.69% 就跳过。t=3000 跳过 11 个（吃光合计 139239，minCmd 197488），t=3600 跳过 10 个（117996 对 604896）。",
             codePath=BUY_AI, verdict="error", patternId="NEW-EC-07",
             evidence=["aigate [GB]：Landsknecht t≥1500 的 1189 个点里 1173 个全被挡，其中 minCmd 1171 个；超软上限的 1102 个点里 1100 个被挡", "aigate [GH] Landsknecht t=3000 / 3600",
                       "aigate [GC]：t≥2250 整个录像期落地的打人机陆攻只有 4 条（2310、2422、9709、21511）"],
             statementType="observed"),
        dict(id="D07", t="2790~4010", bot="三个号", decision="0 兵的人机来啃地时不压兵、不还手：36038 格被拿走，人机只花 177080 兵，编队余额被打掉 4329046。",
             codePath=f"{C110}: counterAttack L871-887（L874-875 跳过内置 AI；counterK=0）；{SIM}/game.js expandAttack L958-1057（L1016-1020 fresh && counter === 0 必赢）、takeBalance L766-776（不够的兵记欠账）",
             verdict="error", patternId="NEW-DF-03",
             evidence=["aigate [GI] 2790~4010：36038 / 177080 / 4329046（每格 120.1）", "truth [TN]：整个录像期编队被内置 AI 拿走 499182 格，AI 耗兵 30691948，编队余额被打掉 105722158（3.44 倍）；33 对『余额损失 > AI 耗兵』",
                       "truth [TN]：Landsknecht ← AI453 18510 格 / AI 耗兵 6247 / 余额被打掉 3391141；← AI478 16033 格 / 1045 / 2623543"],
             statementType="observed"),
        dict(id="D08", t="4000（执行拍 4011）", bot="Landsknecht", decision="超软上限后对编队友 Luxembourg 发 3655334 兵（余额的 20.2%），报价每格 499 兵；同一拍 10 个人机报价（每格 14.9~68.7，吃光合计 132888）被跳过。之后又发 5 条。",
             codePath=BUY_PERSON + "；isProtectedSquadMate L3993-3996", verdict="error", patternId="NEW-MT-05",
             evidence=["aigate [GH] Landsknecht 4000：Luxembourg 499 SEND 3655334（safe 12978295 / keep 14190624 / avail 3655334）", "aigate [GG] t=4011：实发 3678580 + 212225；攻方 AI 邻居 11 个 / 89395 格 / 吃光 134018",
                       "aigate [GG] 合计：Landsknecht→Luxembourg 55311 格 / 22375959 兵（404.5/格），守方余额被打掉 11131389"],
             statementType="observed"),
        dict(id="D09", t="4015~4956", bot="Nader Shah", decision="Luxembourg 一流血，对它的留底就从『它的余额』降到 88×领土，立刻跟打：5 条共 9240185 兵换 20022 格。打完密度从 144 掉到 66，随即成为 Landsknecht 的下一个目标。",
             codePath=f"{C110}: Policy.buyLand L5323-5326（bleeding → safe 封顶）、L5348-5358、L5543-5548", verdict="error", patternId="NEW-DF-05",
             evidence=["aigate [GH] Nader Shah 3900：Luxembourg skip:avail<=0(safe)（safe 12623250）；4015：SEND 2508536 [bleeding]（safe 4221624 / keep 4317570）", "aigate [GG]：Nader Shah→Luxembourg 20022 格 / 9240185 兵（461.5/格）",
                       "truth [TK]：3960~4050 Nader Shah 余额 6818721 → 4454462（-35%），主因陆攻 2599734 → Luxembourg"],
             statementType="observed"),
        dict(id="D10", t="2422~5005", bot="Luxembourg", decision="2583 拍零指令：对人机被 minCmd 挡，对两个真人邻居 safe = Landsknecht 的余额、可用兵为负；挨了 11 条陆攻不还手。t=4995 Nader Shah 流血才放行，打出 2 条。",
             codePath=SAFE + "；buyLand L5358、L5360-5361；counterAttack L871-887（counterK=0 不发）", verdict="error", patternId="NEW-DF-05",
             evidence=["aigate [GH] Luxembourg 3600 / 3900 / 4000 / 4100 / 4400 / 4700 / 4990：真人报价全部 skip:avail<=0(safe)，safe 12904451~18297139 都高过自己的余额", "真值指令账：Luxembourg 在 (2422, 5005) 之间 0 条指令；领土 94524 → 32785",
                       "aigate [GH] Luxembourg 4995：Nader Shah 183.9 SEND 1085588 [bleeding][onMe]"],
             statementType="observed"),
        dict(id="D11", t="4980~5621", bot="Landsknecht", decision="回头吃掉 Nader Shah（3 条，每格 211.6 兵）和 Luxembourg 的残部（2 条）。自由混战里只能留一家，这两个迟早要吃；但每一条发出时都有 10~18 个人机邻居（吃光 18.1 万~28.2 万兵）被跳过。",
             codePath=BUY_PERSON, verdict="unclear", patternId="NEW-AT-01",
             evidence=["aigate [GG] t=4991 / 5180 / 5313 / 5488 / 5621", "aigate [GH] Landsknecht 4980：Nader Shah 165.3 SEND 3413589；5300：187.7 SEND 2569987 [bleeding]", "truth [TK]：5130~5220 Nader Shah -40%、5490~5580 Luxembourg -43%，主因都是挨 Landsknecht 的打"],
             statementType="observed"),
        dict(id="D12", t="5670~9700", bot="Landsknecht", decision="独自面对 20 个内置 AI，4030 拍不打人机：t=5700 的 14 个人机报价（170675 格 / 20739 兵，吃光 288970）13 个被 minCmd（1022984）挡、1 个被价格挡；t=6300 跳过 17 个；t=9000 跳过 7 个（单个最大 want 567660 对 minCmd 974484）。领土 54.75% → 31.73%。",
             codePath=BUY_AI, verdict="error", patternId="NEW-EC-09",
             evidence=["aigate [GH] Landsknecht 5700 / 6300 / 9000 / 9690", "aigate [GI] 5670~9700：被人机拿走 110912 格，人机耗兵 2395950，自己余额被打掉 25667280（231.4/格）；拿人机 0 格",
                       "aigate [GD]：Landsknecht 录像期密度 ≥149 的拍数 27370 / 36080"],
             statementType="observed"),
        dict(id="D13", t="9700（执行拍 9709）", bot="Landsknecht", decision="AI101 长到 145080 格 / 28.6 万兵，want 916040 第一次超过 minCmd 890372：一条 927474 兵的指令把它打坍，43 拍后领土翻倍。",
             codePath=BUY_AI + f"；elimCost L511-517", verdict="good", patternId="NEW-AT-G1",
             evidence=["aigate [GC] t=9709：AI101 145080 格 → 300 拍后 0；自己 127602 → 263910 格", "aigate [GI] 9700~9840：拿人机 111397 格 / 671810 兵（6.0/格），空地 29766 格", "aiwatch_ai101：t=9752 坍缩"],
             statementType="observed"),
        dict(id="D14", t="9840~21500", bot="Landsknecht", decision="剩下的 3 个内置 AI 全是 0 兵（131525 格，吃光 197290 兵），自己 21965507 兵，全部跳过；t=10039 回来的 AI101（1 格）也不打。11660 拍后又只剩 35.5%。",
             codePath=BUY_AI + f"；{SIM}/game.js collapse L1314-1335", verdict="error", patternId="NEW-EG-03",
             evidence=["aigate [GH] Landsknecht 9840：3 个报价全部 skip:x<minCmd（1029632），单个最大 want 127122", "aiwatch_ai101：t=9752 领土 0 / 活着 1 / 在途船 1；t=10042 1 格；t=10078 84 格 / 3 兵",
                       "aigate [GI] 9840~21500：被人机拿走 133087 格，自己余额被打掉 31643241"],
             statementType="observed"),
        dict(id="D15", t="21500（执行拍 21511）", bot="Landsknecht", decision="同样的触发：AI124 长到 215261 格 / 32 万兵才打，1107806 兵拿下 147921 格；AI124 剩 67931 格没有坍缩，之后又过不了 minCmd，到 t=36000 长回 135804 格。",
             codePath=BUY_AI, verdict="unclear", patternId="NEW-EC-07",
             evidence=["aigate [GC] t=21511：AI124 215261 格 / 320830 兵 → 300 拍后 67931 格；自己 142691 → 289342 格", "aigate [GI] 21500~37561：拿人机 147921 格 / 1107785 兵（7.5/格），被人机拿走 149860 格 / 自己余额被打掉 35861184"],
             statementType="observed"),
        dict(id="D16", t="2250~37561", bot="Landsknecht", decision="打空地的单子被抬到 minCmd：36 条全部是 pct 47（余额的 4.69%），实发合计 26783267 兵（多的打完退回），手续费 6695808 不退，换来 30047 格空地（坍缩的人机留下的）。",
             codePath=f"{C110}: base expandNeutral L980-989（L987 want = min(max(…, minCmd), spend)）；Policy.expandNeutral L2408-2414", verdict="unclear", patternId="NEW-EC-03",
             evidence=["aigate [GE]：Landsknecht 36 条（1 条没生效）/ 26783267 / 6695808 / 30047 格 / 每格连手续费 224.8；其中密度 ≥100 时 21 条", "truth [TK]：1800~1890 Landsknecht 10 条空地单 104582 兵，余额 -31%"],
             statementType="observed"),
        dict(id="D17", t="52560~53370（只有日志）", bot="Landsknecht", decision="第一次扫尾：t=52595~52985 24 条船把缺口从 8181 格收到 74 格，然后 405 拍没有搜过一次水路；t=53370 出现一个敌邻，扫尾状态解除，之后 59670 拍零指令。",
             codePath=f"{C110}: Policy.idleBoats L4979-5006（扫尾分支 L4981-4988）→ base boatOut L1035-1051（L1037 maxBoats=2）；isMopUp L4501-4514", verdict="error", patternId="NEW-SE-06",
             evidence=["aigate [GJ] 段 t=52560~53280：船 0 → 24，空档 t=52985 → 53390（405 拍）", "aigate [GF]：最长零指令段 t=53010~112680", "L（HL-TICK）t=53370 terr=402067 nb=1"],
             statementType="inferred"),
        dict(id="D18", t="112680~113679（只有日志）", bot="Landsknecht", decision="敌邻长到 23.7 万格后一条陆攻打回去（165546 → 364063 格），接着 23 条扫尾船，t=113679 拿下全部陆地。",
             codePath=BUY_AI + f"；Policy.idleBoats L4981-4988", verdict="good", patternId="NEW-EG-G1",
             evidence=["aigate [GF]：112680→112770 165546 → 247822（指令 +1），112770→112860 → 364063", "aigate [GJ] 段 t=112860~113670：船 24 → 47，领土 364063 → 402139", "结果行 L（CocaCola）：end / won / t=113679 / place=1"],
             statementType="observed"),
    ],
    newPatterns=pick("NEW-EC-07", "NEW-EC-08", "NEW-DF-05", "NEW-MT-05", "NEW-DF-03", "NEW-EC-09", "NEW-EG-02", "NEW-EG-03", "NEW-SE-06", "NEW-AT-01", "NEW-EC-03", "NEW-EX-05",
                     "NEW-SP-05", "NEW-IO-08", "NEW-IO-06", "NEW-IO-04", "NEW-OP-G1", "NEW-AT-G1", "NEW-EG-G1"),
    lossArchetype="win",
    archetypeNote="结果是胜：自由混战房间里只有我们自己的号在打（另外 3 个真人席位 t≤168 就空了），Landsknecht 最后拿下全图。"
                  "但这是一局『赢面在 t=2730 就定了、却打到 t=113679』的对局：三个号占 75% 时人机合计只有几千兵，之后 1280 拍不吃人机、1636 拍互打、再用 10.8 万拍在硬上限上和 2~20 个人机来回拉锯。"
                  "按落败口径看，两个阵亡的号属于 lead-thrown（领先时被自己人吃掉），根因是 minCmd 反向门槛 + 留底 sb 把编队友的余额当底线 + 没有野人时解除编队保护。",
    winnerNotes="赢家就是本编队的 Landsknecht。它赢在两点：一是 t=4000 时它是三个号里最富的（1806 万对 1298 万、691 万），留底 sb 取的是『别人的余额』，所以只有它不被锁、第一个出手，另外两个只能挨打或跟打；"
                "二是内置 AI 吃不死一个顶着硬上限的号——号越小 minCmd 越低（上限处 = 7.03×自己的领土），人机越大 want 越高，丢到 29%~43% 时门槛自动翻过来，一条指令之后领土回到 62%~98%。"
                "这个循环在录像期和日志里一共出现 5 次（t=9709、21511、39510、52290、112680），收官靠的是最后一个人机恰好被一次打坍、且没有船在海上。全场没有别的真人对手可比。",
    peerComparison="本包没有同房的另一支受控编队，房间里也没有在线的野人（Player 765 t=0 离开）。可比的只有内置 AI：整个录像期它们从编队手里拿走 499182 格只花 30691948 兵，编队余额被打掉 105722158；"
                   "编队从它们手里拿 521705 格（t≤2700 的 262387 格 + t=9709 / 21511 两条指令的 259318 格）只花了 2710704 兵（每格 5.2）。",
    teamSplitNotes="自由混战，没有队：引擎里三个在线号互为敌人，不能互相捐款（日志 0 笔 HL-DONATE），船靠岸在对方地上按进攻结算（本局没有发生）。"
                   "策略侧的编队保护只在『有野人活着』时生效，本房间从第 0 拍起就没有；三个号 t≤3990 没有互打只是因为价格和留底的门槛没过。",
    ledgerExtra=dict(
        civilWar=dict(window="4011~5621", orders=16, tiles=122998, attackerTroopsBurnt=41671619, defenderBalanceDestroyed=20359286, perTile=338.8,
                      byPair={"Landsknecht→Luxembourg": dict(orders=6, tiles=55311, burnt=22375959, perTile=404.5, defenderLost=11131389),
                              "Nader Shah→Luxembourg": dict(orders=5, tiles=20022, burnt=9240185, perTile=461.5, defenderLost=4248459),
                              "Landsknecht→Nader Shah": dict(orders=3, tiles=43130, burnt=9127863, perTile=211.6, defenderLost=4520289),
                              "Luxembourg→Nader Shah": dict(orders=2, tiles=4535, burnt=927612, perTile=204.5, defenderLost=459149)},
                      src="scripts/aigate.py [GG]；scripts/truth.py [TF]"),
        vsBuiltInAiByPeriod=[
            dict(window="1500~2790", lostTiles=24515, aiSpent=381167, squadBalanceDestroyed=347708, gainedTiles=176636, squadSpent=647792, neutralTiles=38254, squadTilesEnd=300004, aiTilesEnd=100207, aiTroopsEnd=3120, aiAlive=23),
            dict(window="2790~4010", lostTiles=36038, aiSpent=177080, squadBalanceDestroyed=4329046, gainedTiles=0, squadSpent=0, neutralTiles=1799, squadTilesEnd=265065, aiTilesEnd=136172, aiTroopsEnd=9544, aiAlive=22),
            dict(window="4010~5670", lostTiles=40913, aiSpent=209840, squadBalanceDestroyed=7386225, gainedTiles=0, squadSpent=0, neutralTiles=22650, squadTilesEnd=220162, aiTilesEnd=176638, aiTroopsEnd=4347, aiAlive=20),
            dict(window="5670~9700", lostTiles=110912, aiSpent=2395950, squadBalanceDestroyed=25667280, gainedTiles=0, squadSpent=0, neutralTiles=18352, squadTilesEnd=127602, aiTilesEnd=273893, aiTroopsEnd=138569, aiAlive=5),
            dict(window="9700~9840", lostTiles=2937, aiSpent=80758, squadBalanceDestroyed=484554, gainedTiles=111397, squadSpent=671810, neutralTiles=29766, squadTilesEnd=265828, aiTilesEnd=131525, aiTroopsEnd=0, aiAlive=3),
            dict(window="9840~21500", lostTiles=133087, aiSpent=13069081, squadBalanceDestroyed=31643241, gainedTiles=0, squadSpent=0, neutralTiles=10287, squadTilesEnd=142691, aiTilesEnd=255029, aiTroopsEnd=94606, aiAlive=2),
            dict(window="21500~37561", lostTiles=149860, aiSpent=14369812, squadBalanceDestroyed=35861184, gainedTiles=147921, squadSpent=1107785, neutralTiles=0, squadTilesEnd=141089, aiTilesEnd=261058, aiTroopsEnd=0, aiAlive=2),
        ],
        vsBuiltInAiSrc="scripts/aigate.py [GI]（真值逐对战损账，30 拍一窗）",
        aiExchangeWholeReplay=dict(squadLostTiles=499182, aiSpent=30691948, squadBalanceDestroyed=105722158, ratio=3.44, pairsWhereLossExceedsAiSpend=33, src="scripts/truth.py [TN]"),
        neutralOrdersAfter2250=dict(bot="Landsknecht", orders=36, noEffect=1, troopsSent=26783267, feesNotRefunded=6695808, neutralTilesGained=30047, perTileWithFee=224.8,
                                    atDensity100plus=dict(orders=21, troopsSent=23158689, fees=5789667, tiles=24030), src="scripts/aigate.py [GE]"),
        hardCap=dict(bot="Landsknecht", replayTicksFrom1500=36080, ticksDensity100plus=33210, ticksDensity140plus=30700, ticksDensity149plus=27370,
                     logTailSnapshots=846, logTailSnapshotsDensity149plus=815, src="scripts/aigate.py [GD][GF]"),
        drop30Reconciled="对局卡 DROP30 = 5 段；真值单窗（90 拍）跌 ≥30% 的有 8 段（truth [TK]）：Landsknecht 1800~1890（10 条空地单 104582 兵）；Nader Shah 3960~4050（打 Luxembourg 2599734）；"
                         "Luxembourg 4410~4500（挨 Nader Shah 3579094）、4950~5040（自己打 Nader Shah 1086765 + 挨 Nader Shah 2651443）、5490~5580（挨 Landsknecht 2268576）；"
                         "Nader Shah 5130~5220（挨 Landsknecht 1849269）；加两个阵亡窗。主因：挨打 6、陆攻 2；8 段里 7 段是编队号互打。",
        donations="0 笔（自由混战不能捐款；日志没有 HL-DONATE）。对局卡 likelyRejectedTransfers=0。",
        boats=dict(replayPeriod=0, logTail=47, firstMopUp=dict(window="52595~52985", boats=24, tilesLeftBefore=8181, tilesLeftAfter=74, searchGapTicks=405),
                   secondMopUp=dict(window="112925~113675", boats=23, tilesLeftBefore=38084, tilesLeftAfter=8, searchGapTicks=400),
                   note="pct 最小是 0 = 余额的 1/1024，所以每条扫尾船实际带 4 万多兵，另付余额的 32/1024 手续费（base boatOut L1045-1046；game.js quote L1239-1248）", src="scripts/aigate.py [GJ]"),
    ),
    wentWell=[
        "人机期收割干净：t=630~2700 吃下 262387 格人机地，每格 3.1~3.7 兵；t=2730 三个号合占 74.99%，活着的内置 AI 只剩 25 个。",
        "执行层干净：指令时延中位 9~17 拍，影子的单条指令 308/327 在录像里配得上，isNoFullSend 从未置位；逐报价重走 buyLand 得到的 SEND 金额和录像里的实发对得上（t=4000：3655334 对 3678580，差的是 11 拍利息）。",
        "打人机的两手都一击见效：t=9709 927474 兵换 111397 格 + 空地 29766 格；t=21511 1107806 兵换 147921 格（每格 6.0 / 7.5 兵）。",
        "最后赢了：Landsknecht 在 2~20 个人机的轮番啃咬下没有被吃死，五次从 29%~43% 打回 62%~98%，两次扫尾后拿下全图。",
        "编队号之间在 t≤3990 没有互打，开局出生点相距 295 像素以上。",
    ],
    unknowns=[
        "sudo_rm_rf、Vasa 为什么在 t=168 同一拍离开：两个号有 HL-GAME-INIT 和出生行，没有任何开局日志。另外两个房间的 10 个号为什么没有局内数据也不清楚（不在本房间）。",
        "t=37561 以后没有录像：t=39510 / 52290 / 112680 三次反打的对象是谁、t=53370 重新出现的敌邻是哪个人机、怎么来的（推断：和 AI101 一样靠在途的船，或者一直活在小岛上），都看不到。",
        "两次扫尾都在 402073 格（差 74 格）停 400~405 拍：推断是最后几条船去了远处的岛、占着 maxBoats=2 的在途名额（搜索按『手续费 ÷ 岛的格数』先挑最大的岛、不看远近）；真机的 boatCount 和船的去向不在数据里，没有实证。",
        "t=21511 那一手按『吃光所需』定的兵力没有打坍 AI124（剩 67931 格，坍缩线是峰值的 1/4）：elimCost 的估算差在哪一项没有逐拍核对。",
        "三个号都准时的前提下，D04 被丢掉的 19 条『第 2 条指令』对人机期的进度影响多大，没有量。",
        "如果 t=4000 之前把人机吃光，三个号之间的结局（谁吃谁、花多少兵）是另一回事，本文没有推演。",
    ],
    mechanicsQuestions=[
        "内置 AI 新开进攻的第一圈：守方没有兵压在它身上时必赢，不够的兵记欠账（game.js expandAttack L1016-1020、takeBalance L766-776，欠账上限 5 万）。守方每丢一格掉约 1.6×自身密度的兵——密度 150 时每格 240 兵，而人机可能一兵不花。",
        "余额硬上限 150×领土：economyTick（game.js L778-791）的利息和每格 +1 都走 addBalance，到顶就截掉；丢地时上限跟着降。顶在上限上的号，花掉的兵下一轮利息就补回来，不花才是净损失。",
        "坍缩：领土 ≤ 峰值的 1/4 就坍缩，剩下的地变空地、打它的兵转去打空地（collapse L1314-1335）；但坍缩时有船在海上的玩家不除名，船靠岸后重新有地（本局 AI101：t=9752 坍缩，t=10039 靠岸）。",
        "胜利条件（victoryTick L1398-1412）：领先者拿下全部陆地、没有任何进攻在途、没有敌方的船在海上。自由混战里必须一个人拿全图，几格的小岛也算。",
        "指令手续费按余额比例收、和发多少兵无关：陆攻 12/1024，船 32/1024（quote L1239-1248）。pct 最小是 0 = 余额的 1/1024，所以余额几千万时『几百兵的小船』实际带 4 万多兵。",
        "船速随船上兵数变（boats.js moveBoats L289-304）：每拍进度 = 25 万 + min(20×兵, 30 万) + min(兵/8, 5 万)，除以这一段航线的长度（1 像素 = 16 个单位，满 65535 走完一段）；带 1.5 万兵以上约每拍 0.52 像素，几百兵约 0.24 像素。",
    ],
    scripts=[
        "bash c136-review/agents/R08/scripts/pipeline.sh B030（facts.py / resim_r08.mjs / truth.py / shadow.mjs / shadowcmp.py / harvest.py / top.py / spawncheck.py）",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/shadow.mjs B030 --core-census-until 37561 --census-every 30 --tag full --quiet --trace \"Landsknecht:2400,…,21500;Luxembourg:2100,…,5210;Nader Shah:2100,…,4930\""
        "（本局新加 walkBuyLand：照抄 Policy.buyLand 的每一关、逐报价给出结论；census2 多了 5 列人机邻居合计）；trshow.py out/B030/shadow_full.json <号>",
        "c136-review/agents/R08/scripts/aigate.py B030 --tag full（本局新写：[GA][GB] 打人机的门槛普查、[GC] 落地的打人机陆攻、[GD] 顶上限的拍数、[GE] 空地单、[GF] 日志尾段、[GG] 编队互打、[GH] 逐报价重走、[GI] 分时段来回账、[GJ] 扫尾段和水路搜索空档、[GK] 时间线）",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/aiwatch.mjs B030 --ids 101 --from 9700 --to 10080 --vs 4 --tag ai101（本局新写：逐拍盯指定玩家号的 活着 / 地 / 兵 / 峰值 / 在途船 / 欠账）",
        "c136-review/agents/R08/scripts/r08lib.py（本局改：房间表和录像头对不上时按录像头改，_fix_rooms_by_replay）；facts.py / build_review.py（本局改：没有队的房间里编队号拿到 won 记 ffaWin）；"
        "spawncheck.py（本局改：混房的包只数录像所在房间的出生行）",
        "c136-review/agents/R08/scripts/build_review.py B030",
    ],
    confidenceOverall="high",
    confidenceNote="t≤37561 的所有数字来自逐兵对上的真引擎重演（214/214 条快照一致）和在真值上重走的策略源码；转折 1~3 的每一步都有逐报价的门槛结论，和录像里的实发金额对得上。"
                   "t>37561 只有赢家自己的日志：领土、余额、指令数、船数、慢拍是实测，敌邻是谁、船去了哪是推断（转折 4 标 inferred）。",
)
