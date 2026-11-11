# B009 人工分析部分。这个对局包里混了两个物理房间（src/tools/rooms-discovery.json：nRooms=2，同一张地图 16 / 种子 13804，陆地 423950）：
#   房间 0（主房间，物理房间 27）：9 个号、4 队 × 5 人，只有日志、没有录像——数字全部来自 in_game.log 的 HL-TICK / HL-DONATE / HL-ASSIST / HL-SPAWN 和结果行；
#   房间 1（物理房间 28，和 A010 是同一个物理房间）：1 个号（Mali），包里的 replay.txt 属于它——scripts/resim_r08.mjs 逐拍重演到 t=4692，41/41 条 traj 快照地、兵都一致。
#   出处：out/B009/digest.txt（房间 0）、digest_room1.txt、donfit.txt [FA]~[FQ]、donwall.txt、flow.txt [VA]~[VC]、logstats.txt [QA]~[QG]、noeffect.txt [NA]~[ND]、
#         clockskew.txt [KA]~[KC]、lagorder.txt、squadfog.txt [HA]~[HN]、spawnlog.txt、teamshare.txt、truth.txt [TA]~[TO]、shadowcmp.txt / shadowcmp_peer.txt [SA]~[SJ]、
#         harvest.txt、top.txt、spawncheck.txt。
#   L 号 = bundles/B009/in_game.log 每行开头的原始行号。
from patterns_catalog import pick

C110 = "src/strategy/v27-team-c110.js"
SIM = "src/sim/sim"

SPAWN = f"{C110}: Policy.chooseSpawn L4007-4064（每个号在自己的客户端里排槽位：HL-SPAWN 行的 slot / rankIdx / chosenSlots 各号不同）"
DRIVER = f"{C110}: 文件头 L2-47（驱动层 afterTick 包装：只有 450 ms / 8 拍的在途保护，没有时延检测，也没有断流检测）"
GATE = (f"{C110}: Policy.act L4781-4944 → Policy.buyLand L5250-5372（L5258-5260 worth = maxW(0.5)×winRatio(t)×参考密度；L5261 over = 余额 > 100×领土；"
        "L5267 报价 ≥ worth 且没有 over 就整轮停手；L5269-5273 唯一的健康真人邻居要余额 ≥ 1.28×100×领土才打；"
        "L5322 / L5358-5360 可用兵 = 余额 − 手续费 − max(keep, safeAt)；L5367 打非真人时不足 minCmd 的单子不发）")
SAFE = f"{C110}: Policy.safeAt L4524-4541 → safeAt L2744-2754（对真人的留底 =（最富真人邻居余额 − 1.5×领土）÷1.78，不封顶）"
PROT = (f"{C110}: isProtectedSquadMate L3993-3996 → hasWildOutsidersAlive L3978-3990（场上还有『活着、领土 ≥80、不是空壳、名字不在名字池、不是 Boss』的人就为真——不排除自己的队友）；"
        "analyze L420-448（受保护的邻居不进 nb）；isMopUp L4501-4514（还有异队的活人就不算扫尾）")
DON_HEAD = f"{C110}: tryDonateToTeammate L4369-4497"
DON_FLOOR = (f"{DON_HEAD}（L4372 冷却 18 拍；L4382-4385 留底 = max(有海岸且 t≥1100 时 68×领土, 对真人留底)，自己正挨真人打就不捐；"
             "L4387-4389 可捐比例 maxSafePct ≥55/1024 才捐 → 有海岸的号密度到 77.6 就开始捐）")
DON_RESCUE = (f"{DON_HEAD} 的救援分支 L4423-4445（L4424 只按 isOurSquadBot 的名字挑人；L4434 对方挨真人打且（进攻兵 ≥8% 余额 或 密度 <75）；"
              "L4436-4437 同队且自己密度 ≥ max(55, 对方密度+15) 就捐 min(maxSafePct, 155)——比例被自己的留底压到 55~84 时照发）")
POKE = (f"{DON_HEAD} 的协防分支 L4447-4458（主攻手和我接壤、我没在打它、我密度 ≥65、25 拍冷却 → g.attack(102)，约余额的 10%；"
        "L4424：场上还有野人时不要求受益人和我同队）")
DON_SURPLUS = (f"{DON_HEAD} 的盈余分支 L4462-4497（L4462 没被围的号密度 ≥112 才进来，被围的 ≥55；L4467 收款方必须是同队的 Boss 或名字池里的名字；L4469 对方密度 ≥132 才跳过；"
               "L4477-4478 对方没有真人敌邻、没有在途进攻且 t>2200 跳过；L4489 pct = 被围 ? (密度>110 ? 280 : 185) : 153，不看自己的留底，也不看对方还装得下多少）")
BOAT = (f"{C110}: Policy.idleBoats L4979-5006（L4995 每 60 拍一次；L4996 有敌邻时余额要 ≥ 1.25~1.3×100×领土才发；L5004 没有陆上邻居时 maxEff = Infinity）"
        "→ boatOut L1035-1051（落点不是空地时船上的兵 = 0.5 ×（余额 − 留底））→ searchWater L1056-1115（L1104 跳过受保护的编队友和陆上邻居，挑每格报价最低的岸）")
ENG_DON = (f"{SIM}/game.js donate L404-416 / transfer L388-401（手续费 = 捐出方余额的 64/1024，按全额余额收）/ receiverRoom L340-345（到账 ≤ 150×收款方领土 − 收款方余额；装不下 1 兵时整单不成交）"
           " / donationFree L360-362（t≥4284 不查额度）")
ENG_ELIM = f"{SIM}/game.js aliveTick L1298-1312（领土 ≤ 峰值的 1/4 就出局；峰值在掉地期间每次按差额的 1/1000 往下衰减；出局后剩下的地变空地、余额清零）"
ENG_WIN = f"{SIM}/game.js victoryTick L1398-1412（归档引擎里领先的队拿下全部陆地才结束）"
ENG_BOATLAND = (f"{SIM}/boats.js landAt L262-288（靠在自己的地上兵回余额；靠在队友的地上按捐款并给队友、装不下的蒸发；靠在敌人或空地上要有空闲进攻槽才开进攻）；"
                f"{SIM}/game.js expandAttack L958-1060（一圈的成本 ≥ 身上的兵时，剩下的兵全部按伤害烧掉，进攻结束）")
SB = (f"{C110}: winFloor L4542-4550（打人机前的留底 = max(价位底, dpKeep, sb)）→ safeFinite L2532-2541 / L2773-2784"
      "（sb 取的是共用同一个人机邻居的另一个真人的余额，不分是不是队友）；1500 拍后走 buyLand L5322-5326（对非真人 min(safeAt, 88×领土)）")

R = dict(
    contextExtra=dict(
        bundleRooms="rooms-discovery.json：B009 nRooms=2，两个房间同图同种子（地图 16 / 种子 13804，陆地 423950，各 20 个真人）。"
                    "房间 0 = 物理房间 27，4 队 × 5 人，2026-11-09T15:16:11.679Z 开局，9 个号，没有录像，最后的结果行在本地拍 6643（8 个 left）；"
                    "房间 1 = 物理房间 28（rooms-discovery 的 physPeers：和 A010 的 squad10 是同一个房间），2 队 × 10 人，15:16:28.285Z 开局，1 个号（Mali），录像到 t=4692，T1 在 t=4691 获胜。"
                    "本文正文（context / outcome / timeline / deaths）写房间 0，房间 1 在 sideRooms 里。",
        cardMismatch="card.json 是两个房间混在一起算的：squadBots=10、teamSplitCounts={1:2}、outcome=won / winnerTeam=4 / endTick=6643、peakPrimaryTeamShareSeen=0.9838、ourFinalTeamShare=0.0447。"
                     "拆开看：『赢了、98.4%』是房间 1 的 T1（只有 Mali 一个号在里面，占 2.58%）；endTick=6643 和 0.0447 是房间 0 的（T1 在 t=5288 的份额）；"
                     "winnerTeam=4 是房间 0 最后一条带全队领土的结果行里领先的队，那一局并没有打完。原值留在 context.cardOriginal。",
        truthTeamSplit="房间 0（没有录像，队号是推出来的）：引擎只允许捐给同队，捐款边把 9 个号连成 {DeepBlue 13、Courland 16、California 17、Sun Quan 18}、{Safavid 10、Borsch 11}、{Dream 14、Reconquista 15}、{Catalonia 12}；"
                       "Dream 的结果行（t=5288，L8407720）给出 T1=18954 / T2=141550 / T3=12415 / T4=243509：18954 正好是 Reconquista 在 t=5220 和 5310 的领土，12415 正好是 Catalonia 的领土，"
                       "四个号的那一组合计 171940 格、比 T2 的 141550 还多，只能在 T4；每队 5 人，T4 已有 4 个号，{Safavid, Borsch} 只能在 T2。"
                       "所以 T4×4 + 1 个野人、T2×2 + 3 个野人、T1×2 + 3 个野人、T3×1 + 4 个野人。房间 1（录像）：Mali 在 T1（另 9 个野人），对面 T2 是 [APEX]×10。",
        strategyVersion="squad20 = c110（归档 v27-team-c110.js）；没有 Boss；出生点由各号客户端自己算（[HL-SPAWN] 58 行：房间 0 48 行、房间 1 10 行；没有后端协调器的行）。"
                        "房间 1 的 [APEX]×10 按 c116-vb 重演（shadow.mjs --side peer）。",
        peerInRoom="房间 0 没有另一支受控编队。房间 1 的 [APEX]×10（T2）是 A010 那一局的 squad10（c116）；Mali 和它们不同队。",
        clock="结果行的写入时间对拍号：服务器每拍 56.0 毫秒（和 B006 / B015 / B019 / B027 / B030 / B034 / B035 / B043 的 55.9~56.2 一致）。按 56 毫秒折算，结果行的写入时刻比『开局 + 拍号×0.056』晚："
              "房间 1 的 end 行 20.30 秒、房间 0 Dream 的 died 行 20.44 秒（开局前的出生阶段）；房间 0 的 8 条 left 行晚 72.7~73.2 秒，多出来的 52 秒里本地拍一拍没走。",
        fairSharePerCapita="房间 0：20 个真人里编队 9 个（45%）；T4 的 5 人里 4 个、T2 和 T1 的 5 人里各 2 个、T3 的 5 人里 1 个。房间 1：20 个真人里 1 个（5%）。",
        notes="日志标签中途换名（括号里是玩家号；HL-DONATE / HL-ASSIST 行里的 ally= 是局内名字）：Safavid>Griffith>Bagrationi>Hanover（10，局内名 Safavid）、Borsch>Hikaru（11，OldGuard）、"
              "Catalonia>LiuKang>Three Kingdoms>GalaxyBrain（12，Catalonia）、DeepBlue>StackOverflow>PewDiePie>Lan Xang（13，DeepBlue）、Dream>Quebec（14，Dream）、"
              "Reconquista>Mithridates>Musashi（15，BigSmoke）、Courland>Moltke（16，Courland）、California>Wallachia（17，IceKing）、Sun Quan>Parthia（18，Hamilton）；房间 1 的 Mali>Umayyad（0）。"
              "本文一律用第一个日志标签。HL-TICK 的 t 是各号客户端的本地拍；房间 0 没有服务器拍可对。"
              "时间线的编队合计只算『这一拍有快照的号』：Safavid 的 HL-TICK 停在 6390（6405 还有它的捐款行，是日志丢行），所以 t=6480 / 6570 的合计少它 49457 格；终局以结果行为准。",
    ),
    outcomeExtra=dict(
        winnerHow="房间 0 没有打完，不定赢家：没有 end 行；唯一带全队领土的结果行是 Dream 的 died（t=5288，L8407720）：T4 57.4% / T2 33.4% / T1 4.5% / T3 2.9% / 人机 0.8%。"
                  "之后 8 个号在本地拍 6643（California 6636）同时停住，约 52 秒后写出 left 行（15:23:36.332~36.679Z，L8407906~8407923），行里没有队号和全队领土。",
        stateAtStop="结果行合计：编队 8 个号 360538 格 = 陆地的 85.04%，3755.5 万兵。T4 四个号 256391 格（60.48%：Wallachia 139654、Parthia 48164、Lan Xang 36690、Moltke 31883）；"
                    "T2 两个号 60027 格（14.16%：Hanover 49484、Hikaru 10543）；T1 的 Musashi 37454 格（8.83%）；T3 的 GalaxyBrain 6666 格（1.57%）。"
                    "alivePlayers=10：除了这 8 个号还有 2 个非编队的玩家，第 2 名（领土在 49485~63412 格之间）和第 10 名（不到 6666 格；是 T2 剩下的野人还是人机，看不到）。"
                    "第 2 名是 T4 自己的那个野人（推断）：T2 的野人 Player 188 是 California、Reconquista、Catalonia 唯一的敌邻，t=6390~6480 之间消失（三个号的 nb 同时 1→0、身边出现空地）；California 和 Reconquista 在 t=5310~6480 / 6570 一共拿了 87988 格，约等于 T2 的野人在 t=5288 的全部领土（81718 格）加上 Player 188 此后从 Catalonia 手里拿的 7868 格——T2 的野人剩不下 5 万格；T1、T3 在 t=5288 已经没有野人的地，人机只有 3392 格。按这个推断 T4 全队约占 72%~75%。",
        squadOnLeadingTeam="T4 的 4 个号 t=5288 占 T4 领土的 70.6%（171940 / 243509），停住时 4 个号自己就有 60.48% 的陆地。",
        squadOnOtherTeams="T2：Safavid、Borsch 都活着（t=5288 占 T2 的 42.3%）。T1：Dream t=5288 阵亡，Reconquista 活着（T1 只剩它）。T3：Catalonia 活着（T3 只剩它）。",
        sideRoomResult="房间 1：T1 获胜（t=4691，98.4%）；Mali 活到最后（10920 格，占陆地 2.58%，在场 12 人里第 9 名）。对面的 [APEX]×10 在 t=2284~4031 全部阵亡。",
        survivors=dict(alive=8, of=9, died=1, left=8, note="left = 断流后客户端自己写的离开，不是阵亡"),
        peakNote="peakSquadLandShare=0.7692 是 HL-TICK 口径（t=6390，8 个号都有快照）；按结果行，停住时是 85.04%。",
    ),
    phases=dict(
        spawn=dict(
            window="t=0~90",
            facts=[
                "房间 0：[HL-SPAWN] 48 行，9 个号每号 3~6 条（人均 5.3）；每行 squad=9、rankIdx 0~8、minSep=145，槽位号 slot 却是 0~12（L8406946~8406957 第一轮）。名字池里没有混进陌生人（rankIdx 正好 0~8）。",
                "中间一轮 California（L8406983）和 Catalonia（L8406984）被指到同一个点 (450,610)；最后一条指派两两相距都 ≥145 像素（spawnlog [SB] 0 对）。房间 0 没有录像，引擎里的实际落点核对不了。",
                "最后的点：Safavid (580,514)、Borsch (554,370)、DeepBlue (694,418)、Reconquista (694,626)、Courland (810,514) 这五个互相只隔 146~160 像素；California (386,226)、Sun Quan (514,66)、Catalonia (690,210)、Dream (866,274) 在外圈。",
                "房间 1：Mali 10 条指派，引擎落点 (18,162) 是最后一条（spawncheck [PA][PC]）。它的 HL-SPAWN 行写的是 squad=2、rankIdx=0（L8407009~8407072）：房间里只有它一个号，另一个『编队友』是名字撞上名字池的野人 Russian Empire（玩家 12）。",
            ],
            problems=[
                "挤在一团的五个号分属 T2 / T2 / T4 / T1 / T4，互相按名字受保护、不能互打；其中 4 个后来先后被围（Courland t=1800、DeepBlue 3870、Borsch 3960、Safavid 4320），成了只能捐款和发船的号。",
                "每个号各算各的槽位，重解 3~6 次，中间一轮出现过两个号同点；这一局最后一轮没有撞。",
            ],
        ),
        opening=dict(
            window="t=90~630",
            facts=[
                "房间 0：HL-OPENING 70 行，9 个号都按周期出手（第 0~7 周期）；OPENING-CHECK@184（L8407057）九个号 144~175 格，全部 OK。",
                "t=630 编队 26146 格（6.17%），单号 2257~3580 格，人均 2905 格；t=900 42848 格（10.11%）。t<1800 没有号被围。",
                "房间 1：Mali t=630 1769 格（0.42%），同房真人人均约 2800 格（T1+T2 13.2% ÷ 20）；(270,630] Mali 吃空地 1122 格，其它真人人均 2293、[APEX] 人均 2324（harvest）。",
            ],
            problems=[
                "房间 1 的 Mali 开局只有同房人均的六成：出生点改了 10 次，落在左上角 (18,162)，第一条 HL-OPENING 之后空地被邻居分走。",
            ],
        ),
        midgame=dict(
            window="t=630~3500",
            facts=[
                "t=630→1800 编队 6.17%→28.70%，t=2250 到 46.35%（196521 格，余额 157 万，密度 8.0），9 个号全活着。t=1620~2250 这一段是低价拿地：California t=1980~2250 两段口径 5.1~7.8 兵/格拿 14302~21169 格，Safavid t=1800~2250 17.1 兵/格拿 16435 格（digest [F]）。",
                "卡顿：两个房间按日志行序对表（clockskew [KA]，稳定差 315 拍），房间 0 相对房间 1 最多多落后 120 拍（参照拍 720，California）。房间 1 的 Mali 实测时延在执行拍 900~1800 中位 125~253 拍（shadowcmp [SF]）；"
                "两个房间的客户端同在一台主机上，所以房间 0 在本地拍 ≈1200~2100 大约也落后服务器 100~250 拍（推断）。日志侧的痕迹很轻：没生效的指令 12 条（noeffect [NA] 桶 1080：4 条、桶 1350：8 条），"
                "外加 Catalonia t=1980~2070 一窗 0 条新指令却从 191060 掉到 20716 兵、领土 +4874（L8407289-8407297，旧单子晚落地）。",
                "第一个被围的是 Courland（t=1800，12189 格）：当窗发 1 条船（291184→154085 兵），180 拍后领土到 15328。",
                "t=2250~3150 全队停手：每 270 拍的指令数 6 / 2 / 0 / 2（noeffect [NA]），领土 196521→182420 格（46.35%→43.03%），余额 157 万→864 万（5.5 倍，digest [C]）。",
                "停手期间丢地的号：California 35367→25702（0 条指令，nb=2，密度 3.1→18.5）、Reconquista 21086→16894、Dream 13230→9652、Catalonia 22948→20910、Sun Quan 18720→17008；DeepBlue（nb=1）、Safavid（nb=2）原地不动（digest [E]）。",
                "重新出手的顺序：Sun Quan t=3150（密度 47.6）、California 3240（35.6）、Dream 3420（74.2，只 1 条）、Safavid 3690（114.9）、Borsch 3690（120.5）、Reconquista 3780（93.4）、DeepBlue 3780（91.2）。",
            ],
            problems=[
                "1080 拍里九个号合计 10 条指令，领土净丢 14101 格。停手出自策略自己的价格门槛（推断，房间 0 没有影子）：buyLand L5267 在『报价 ≥ worth 且余额没过 100×领土』时整轮不出手，worth 跟自己的密度成正比，密度 8~50 时真人邻居的报价都在 worth 之上。",
                "重新出手分两批：Sun Quan、California 在密度 36~48 就动了（邻居的报价掉到 worth 以下）；Safavid、Borsch 等到密度 115~121（过了 100×领土，L5261 的 over 档不再受 worth 限制），Reconquista、DeepBlue 在密度 91~93 时动。Safavid、Borsch 出手时每格约 150~260 兵（扣掉同窗的捐款、算上退回余额的兵），是 California 起手价的 4~6 倍。",
            ],
        ),
        endgame=dict(
            window="t=3500~6643",
            facts=[
                "t=3240→3960 编队 43.05%→53.22%：California 10 条指令 25702→58090 格（净花约 137 万兵，42 兵/格，密度 35.6→37.6）；Sun Quan 17008→24678；Safavid t=3690~4320 陆攻净花 274.4 万兵拿 10782 格（约 255 兵/格）。",
                "捐款 65 笔（第一笔 t=3330）：成交 43、没成交 1、定不了 21；到账 1754.3 万、税 744.5 万（付出的 29.8%）（donfit [FA]）。按队：T4 38 笔 / 成交 26 / 到账 1308.4 万 / 税 566.8 万；T2 16 / 10 / 272.2 万 / 85.5 万；T1 11 / 7 / 173.7 万 / 92.2 万；T3 只有一个号，0 笔。",
                "T4 的四个号合计：t=3150 21.20% → 3960 31.59% → 5040 40.44% → 5670 48.95% → 6570 60.44%。California 一个号 25702→139475 格，t≥2250 陆攻 24 条；它收到成交捐款 20 笔 871.6 万（税 391.4 万），自己的利息是 2844.9 万（flow [VA]）。",
                "Dream（T1）t=5288 阵亡，是整局唯一阵亡的号。当时全队领土 T1 4.5% / T2 33.4% / T3 2.9% / T4 57.4%（L8407720）：T4 的 243509 格里编队 4 个号占 171940（70.6%），T2 的 141550 格里 2 个号占 59832（42.3%），T1、T3 各只剩一个编队号。",
                "被围后的船（flow [VC]、logstats [QE]）：Safavid 8 条、7 个窗里少掉 885.9 万兵、领土 +161（船窗加紧接着的一窗）；DeepBlue 10 条少掉 437.9 万、+1135；Courland 被围时 7 条 135.7 万；Sun Quan 3 条 127.4 万（下一窗回来 86.9 万）；Borsch 14 条 25.0 万。",
                "协防戳刺 14 次，12 次跨队：Reconquista（T1）打 T2 的野人 Player 188 共 9 次（6 次为 T3 的 Catalonia、3 次为 T4 的 California），估计出兵 185.6 万（logstats [QC]）。",
                "终局：t=6570 有快照的 7 个号里 6 个没有敌邻（California、DeepBlue、Courland、Borsch、Reconquista、Catalonia），Sun Quan 还有 1 个；最后的日志行是 t=6590 / 6595 / 6600 的 HL-SLOW-TICK（L8407885~8407887），"
                "之后 8 个号的 left 行写在 15:23:36.332~36.679Z，本地拍 6643×7、6636×1；结果行合计 360538 格 = 陆地的 85.04%。",
            ],
            problems=[
                "T1 的 Dream、T3 的 Catalonia 被同一类情形吃掉：只有一个真人敌邻，密度 100~150，3000 多拍里几乎没有陆攻（Dream 1 条、Catalonia 2 条），余额两次顶到 150×领土的硬上限。",
                "T2 的两个号都被围：Borsch 把兵捐给 Safavid（成交 9 笔 218.5 万），Safavid 自己密度 99~137、也没有陆上邻居，兵只能上船——7 个窗少掉 885.9 万兵，领土 +161。",
                "编队占到 85% 以后收尾卡住：还活着的大野人是 T4 自己的队友，T4 的四个号（60% 陆地）不能打它；有它在，异队的编队号又互相受保护；能打它的 4 个异队号都没有陆上敌邻，只能发船。对局停在这个状态上（断流的原因不在包里）。",
            ],
        ),
    ),
    turningPoints=[
        dict(
            t0=2250, t1=3240, shareBefore=46.35, shareAfter=43.05, shareUnit="编队 9 个号占陆地 %（HL-TICK 合计）",
            what="中立地和人机吃完以后全队停手 1000 拍：九个号合计 10 条指令，领土 196521→182497 格，余额 157 万→966 万。",
            evidence=[
                "noeffect [NA]：每 270 拍的指令数 t=2160 起 6 / 2 / 0 / 2，领土净变化 +9869 / −2040 / −8050 / −694；此前的桶 1620 / 1890 是 40 条 / 16 条、+17537 / +34880 格。",
                "digest [C]：t=2250 196521 格 / 1571491 兵（密度 8.0）→ t=3150 182420 格 / 8644186 兵（密度 47.4）；9 个号全程在线。",
                "digest [E]：California t=2250~2880 35367→25702 格，Δcmds=0，nb=2，密度 3.1→18.5（L8407320-8407394）；Reconquista t=2340~3060 21086→16894、Δcmds=0；Dream t=2070~2970 13230→9652、Δcmds=0；Sun Quan t=2250~3150 17008 格不动、Δcmds=0，密度 9.4→47.6。",
                "logstats [QF]：窗口起点只有 1 个敌邻、没有中立地、密度 <100 的 130 个窗里 113 个没有非捐款指令。",
                "重新出手时的密度：Sun Quan 47.6（t=3150）、California 35.6（3240）、Safavid 114.9（3690）、Borsch 120.5（3690）、Reconquista 93.4（3780）、DeepBlue 91.2（3780）。",
            ],
            priorDecisions=[
                dict(t="1620~2250", bot="九个号", decision="把余额压到密度 7~12 去拿最后的中立地和人机：编队 100135→196521 格（+96386），余额只有 114 万~157 万。",
                     codePath=GATE, judgement="good",
                     why="这一段买得便宜（California 5.1~7.8 兵/格、Safavid 17.1、DeepBlue 29.3，digest [F]）；代价是到 t=2250 全队密度 8.0，worth 跟着密度走，之后对谁的报价都嫌贵。"),
                dict(t="2250~3150", bot="九个号", decision="邻居报价 ≥ worth 就整轮不出手（L5267 的 break），挨打也只在 worth 之内还手；没有『正在丢地』的例外。",
                     codePath=GATE, judgement="unclear",
                     why="推断：房间 0 没有录像和影子，看不到逐个报价。旁证是出手的时刻——Sun Quan、California 在密度 36~48 时先动（邻居变便宜），其余的号等到密度 91~121 才动（其中 Safavid、Borsch 过了 100×领土的 over 档）。"
                         "停手让 5 个号白丢 14101 格；但囤出来的 966 万兵是后面 California 起飞的本钱。"),
            ],
            statementType="inferred",
        ),
        dict(
            t0=3240, t1=3960, shareBefore=43.05, shareAfter=53.22, shareUnit="编队 9 个号占陆地 %（HL-TICK 合计）",
            what="重新出手：California 在密度 36 时连发 10 条陆攻，领土翻倍（42 兵/格）；等到过了软上限才动的 Safavid 每格约 255 兵；捐款从 t=3330 开始。",
            evidence=[
                "California t=3240~3870：Δcmds=10，25702→58090 格（+32388），余额 914730→2182438，密度 35.6→37.6（L8407435-8407520）；flow [VB] 这 7 个窗净流出约 137 万兵 = 42 兵/格。",
                "Safavid：t=2340~3690 两个敌邻、1350 拍没动，余额 38 万→434 万（密度 114.9）；t=3690~4320 陆攻净花 274.4 万兵（扣掉它自己成交的捐款、算上退回余额的兵），37792→48574 格，约 255 兵/格（flow --t0 3690 --t1 4320）。"
                "digest [F] 的单窗口径（t=3690~3780，1025 兵/格）没有扣同一窗里它给 Borsch 的那笔捐款（到账 537313 + 税 220436），也没算 t=3870~3960 退回余额的 70.5 万兵，本文不用。",
                "Borsch：t=3690~3960 净花 53.1 万~90.6 万兵（同窗 2 笔给 Safavid 的捐款定不了，算不算在内差 37.5 万），6825→10296 格，约 153~261 兵/格；之后 nb=0，一直被围到终局（L8407484-8407526）。",
                "同一段 Catalonia（T3）20910→11043 格（t=3330~3960），Δcmds=0（L8407438-8407524）；编队净增 43111 格（182497→225608）。",
                "T4 的四个号 21.33%（t=3240）→31.59%（t=3960）；IceKing（California）在 t=3330~4300 收到成交捐款 11 笔 275.5 万（DeepBlue 8 笔、Courland 3 笔），捐出方付税 154.3 万（squadfog [HJ]）。",
            ],
            priorDecisions=[
                dict(t="3240", bot="California", decision="密度 35.6、两个敌邻时出手，630 拍 10 条陆攻。", codePath=GATE, judgement="good",
                     why="每格 42 兵，自己的密度没掉（35.6→37.6），领土 2.26 倍；它是 T4 后来 60% 的起点。为什么这时候报价降到 worth 以下（邻居被别人打薄，还是自己的密度涨上来）看不到。"),
                dict(t="2340~3690", bot="Safavid", decision="两个敌邻、1350 拍不出手，囤到密度 114.9 才按 over 档放兵。", codePath=GATE, judgement="unclear",
                     why="过了 100×领土以后 L5267 不再拦，留底换成 over 档（L5348-5356）。t=3690~4320 陆攻净花 274.4 万兵拿 10782 格（约 255 兵/格），是 California 起手价（42 兵/格）的 6 倍；"
                         "它更早出手会不会更便宜，没有影子看不到。之后它被围，t=4320 以后的 1079.9 万利息大半上了船。"),
                dict(t="3330~4030", bot="DeepBlue / Courland", decision="给 California 的救援捐款按 min(maxSafePct, 155) 下，比例被自己的 68×领土留底压到 55~84/1024。", codePath=DON_RESCUE, judgement="error",
                     why="税固定是捐出方余额的 64/1024：pct ≤70 的 5 笔成交到账 637495、税 644540（squadfog [HH]）。同一批号被围以后改走盈余分支（pct=185），到账才是税的 3 倍。"),
            ],
            statementType="inferred",
        ),
        dict(
            t0=5490, t1=6643, shareBefore=63.70, shareAfter=85.04, shareUnit="编队在线号占陆地 %（t0 是 HL-TICK 合计，t1 是结果行合计）",
            what="California 吃掉 T2 的野人 Player 188（63094→139654 格），编队到 85%；之后 6 个号没有敌邻，收尾卡住，8 个客户端在本地拍 6643 同时断流。",
            evidence=[
                "California：t=5490~5670 Δcmds=4，6804723→4162387 兵，63094→91131 格（当窗 146 兵/格，连下一窗 170 兵/格；L8407751-8407770）；t=6030~6210 +19488 格；t=6300~6570 +30823 格，nb 1→0，t=6480 贴着 176 格空地（L8407849-8407883）。",
                "HL-ASSIST：Reconquista t=5675 / 5705 / 5735、Catalonia t=5700 打 Player 188，受益人都是 IceKing（L8407769~8407773）——Player 188 当时正和 California 对打；Reconquista 自己 19888→25644 格（t=5490~5850）。",
                "IceKing t=4980~6440 收到成交捐款 9 笔 596.1 万（Sun Quan 4 笔 348.5 万、Courland 4 笔 195.6 万、DeepBlue 1 笔 52.0 万），另有 8 笔定不了（squadfog [HJ]）。",
                "t=6570 的 HL-TICK（L8407877~8407883）：California nb=0 / neut=9、DeepBlue 0/0、Courland 0/0、Borsch 0/0、Reconquista 0/34、Catalonia 0/6、Sun Quan 1/0；Safavid 最后一条（t=6390，L8407860）0/0。",
                "结果行（results.csv）：8 条 left 的写入时间 15:23:36.332~36.679Z（0.35 秒内），tick=6643×7、6636×1，seconds=444~445；Dream 的 died 行 tick=5288 / seconds=316。按每拍 56 毫秒，left 行比拍号晚了 52 秒：8 个客户端的本地拍在同一拍停住。",
                "alivePlayers=10、名次 1~10 里第 2 和第 10 不是编队号：还有 2 个非编队的玩家活着。California t=6390~6480 一窗 +21681 格、0 条新指令，nb 1→0、neut 0→176（L8407862-8407873）；Reconquista、Catalonia 的 nb 也在 t=6390~6570 之间 1→0（neut 34 / 6）——三个号共同的敌邻 Player 188 出局了。",
                "t=6295、6405 Safavid 给 Borsch 两笔救援捐款（L8407841、8407864；dAlly=67 / 77）：救援分支要求对方正被『不是空壳、不是编队号』的真人进攻（L4427-4434），Borsch 当时没有陆上敌邻，T2 的野人又不能打自己的队友——跨海打它的只能是 T4 的野人，它到 t=6405 还活着。",
            ],
            priorDecisions=[
                dict(t="4980~6440", bot="Sun Quan / Courland / DeepBlue", decision="被围或没仗打的 T4 号把盈余捐给正在打 Player 188 的 California。", codePath=DON_SURPLUS, judgement="good",
                     why="California 这一段从 59185 格长到 139475 格；捐款是它收入的三成左右（成交 596.1 万 + 定不了的 8 笔）。"),
                dict(t="全程", bot="九个号", decision="场上只要还有不在名字池里的活人，就把异队的编队号当受保护对象（不进 nb、不打、船也绕开）。", codePath=PROT, judgement="unclear",
                     why="推断：hasWildOutsidersAlive 不排除自己的队友。最后的大野人（第 2 名，约 5~6 万格）是 T4 的队友——T4 的四个号（60% 陆地、2607 万兵）不能打它，有它在又不能打别的编队号；"
                         "能打它的只有 T1 / T2 / T3 的 4 个号（1148 万兵）；它们在最后的快照里都没有陆上敌邻（nb=0），只能每 60 拍发一条船。归档引擎的胜利条件是一个队拿下全部陆地。再打下去会不会解开，断流以后看不到。"),
                dict(t="6643", bot="八个号", decision="驱动层不检查『服务器的拍停了』：本地拍停住 52 秒后才写 left。", codePath=DRIVER, judgement="unclear",
                     why="8 个客户端同一拍停住，是房间或主机侧的事，不是单个号卡顿；谁断的不在包里。房间 1 的对局此前 93 秒已经正常结束。"),
            ],
            statementType="inferred",
        ),
    ],
    deathNotes={
        "Dream": dict(
            cause="被唯一的真人敌邻蚕食 3200 拍：峰值 13230 格（t=1800）→ 2147 格时出局（引擎规则：领土 ≤ 衰减后峰值的 1/4）。t≥2250 的 13 条指令 = 陆攻 1 + 船 9 + 捐款 3；"
                  "最后 1000 拍密度 105~150、两次顶到 150×领土的硬上限，仍然没有一条陆攻打向进攻者。",
            chain=[
                "t=1260 起只剩 1 个敌邻；t=1800 峰值 13230 格，密度 7.5。",
                "t=2070~2970 全队停手期丢 3578 格（13230→9652），Δcmds=0，密度 9.8→39.0（L8407294-8407401）。",
                "t=3420~3510 整个中后期唯一一条陆攻：9652→10281 格（密度 74.2）。之后 t=3510~4320 原地 810 拍，密度 71→134.7。",
                "t=3870 反过来给同队的 Reconquista 捐盈余（成交 174398，税 72477）；t=4580、4690 又各捐一笔（定不了）。",
                "t=4320 起挨打：10133→9317→8711→7604→6148→5436→5131→3068（t=5220）；这段发了 8 条船、0 条陆攻。t=4500 余额 1405800 = 150×9372，t=5220 余额 460200 = 150×3068。",
                "Reconquista 给它捐 8 笔：成交 6 笔 1562883 兵（税 849561），其中 3 笔被它的 150 倍上限夹小（到账 548497 / 税 430073）；1 笔定不了；最后一笔（t=5265，救援 pct=101，L8407719）没成交——23 拍后 Dream 出局，Reconquista 的余额到 t=5310 和纯利息一兵不差。",
                "t=5265 Reconquista 看到它的密度只有 64（dAlly=64；t=5220 的快照是 150.0）：45 拍里余额少了一半以上。结果行 sent=61（含 6 条出生点指令）对 t=5220 的 cmds=52，最后 68 拍它又发了 2~3 条指令，是什么看不到。",
                "t=5288 出局：2147 格 / 257943 兵（第 15 名，L8407720），兵随出局清零；T1 只剩 Reconquista。",
            ],
            gate="哪道门槛挡住了陆攻看不到（房间 0 没有影子）。按代码只有三种可能：密度 <128 时『唯一的健康真人邻居不打』（L5269-5273）；密度 ≥128 之后对真人的留底 safeAt 高过全部余额"
                 "（邻居的余额 > 1.78×自己的）；自己正挨真人打时也不能捐（L4385）。房间 1 的类似情形在 B049 的 Dahomey 身上用影子核实过第二种。",
            statementType="inferred",
        ),
    },
    decisions=[
        dict(id="D01", t="0~90", bot="房间 0 九个号", decision="各自在客户端里排槽位，重解 3~6 次；中间一轮两个号同点，最后一轮两两 ≥145 像素。",
             codePath=SPAWN, verdict="unclear", patternId="NEW-SP-07",
             evidence=["[HL-SPAWN] 48 行，人均 5.3 条；squad=9、rankIdx 0~8，slot 0~12（L8406946~8406957）",
                       "L8406983 California → (450,610)，L8406984 Catalonia → (450,610)",
                       "spawnlog [SB]：最后一条指派相距 <145 像素的号对 0 对；t≤900 被围的号 0 个",
                       "五个号（Safavid、Borsch、DeepBlue、Reconquista、Courland）互相 146~160 像素，分属三个队；其中 4 个 t=1800~4320 先后被围"],
             statementType="observed"),
        dict(id="D02", t="90~630", bot="房间 0 九个号", decision="开局按周期扩张：OPENING-CHECK 全部 OK，t=630 人均 2905 格。",
             codePath=f"{C110}: 开局 DP（HL-OPENING 的 cyc / rings / spend）→ Policy.act L4819-4863（t<coreFrom=1500 走 super.act）", verdict="good", patternId="NEW-OP-G1",
             evidence=["OPENING-CHECK@184（L8407057）：九个号 144~175 格，全部 OK",
                       "t=630 编队 26146 格（6.17%），单号 2257~3580 格（digest [K]）",
                       "t=900 42848 格（10.11%）；t<1800 没有号被围"],
             statementType="observed"),
        dict(id="D03", t="1080~2070", bot="房间 0 九个号", decision="主机卡顿期照常发令：12 条指令没生效，Catalonia 的旧单子在 t=1980~2070 一起落地、花掉 89% 余额。",
             codePath=DRIVER, verdict="unclear", patternId="NEW-IO-10",
             evidence=["noeffect [NA]：桶 1080 46 条里 4 条没生效，桶 1350 54 条里 8 条；其余桶 0~2 条",
                       "clockskew [KA]：房间 0 相对房间 1 最多多落后 120 拍（参照拍 720）；参照拍 1620~1710 反而领先 81~85 拍",
                       "Catalonia t=1980~2070：Δcmds=0，191060→20716 兵，15290→20164 格（43 兵/格；L8407289-8407297）",
                       "房间 1 同一台主机上的 Mali：执行拍 900~1800 时延中位 125~253 拍（shadowcmp [SF]）"],
             statementType="inferred"),
        dict(id="D04", t="1620~2250", bot="California / Safavid / DeepBlue 等", decision="趁中立地和人机还没分完，把余额压到密度 7~12 去拿地：编队 23.62%→46.35%。",
             codePath=GATE, verdict="good", patternId="NEW-AT-G1",
             evidence=["California t=1980~2070：116871→71520 兵，14198→19824 格；两段口径 111943 兵 / 14302 格 = 7.8 兵/格，到 t=2250 是 5.1 兵/格（digest [F]，L8407288-8407296）",
                       "Safavid t=1800~2070：21254→28440 格，到 t=2250 两段口径 17.1 兵/格；DeepBlue t=1710~1890 29.3 兵/格",
                       "digest [C]：t=1620 100135 格 → t=2250 196521 格，余额 114 万→157 万"],
             statementType="observed"),
        dict(id="D05", t="2250~3150", bot="房间 0 九个号", decision="全队停手 900 拍：合计 10 条指令，领土 46.35%→43.03%，余额 5.5 倍。",
             codePath=GATE, verdict="unclear", patternId="NEW-EC-04",
             evidence=["noeffect [NA]：桶 2160 / 2430 / 2700 / 2970 的指令数 6 / 2 / 0 / 2",
                       "digest [C]：196521 格 / 1571491 兵（t=2250）→ 182420 格 / 8644186 兵（t=3150）",
                       "California 35367→25702 格、Reconquista 21086→16894、Dream 13230→9652，全是 Δcmds=0（digest [E]）",
                       "判『存疑』而不是『错』：停手囤出来的兵是 t=3240 以后编队从 43% 长到 85% 的本钱；白丢的是 14101 格和 1000 拍"],
             statementType="inferred"),
        dict(id="D06", t="3240~3870", bot="California", decision="密度 35.6 时出手，630 拍 10 条陆攻，领土 25702→58090 格，约 42 兵/格。",
             codePath=GATE, verdict="good", patternId="NEW-AT-G3",
             evidence=["digest [E]：G 3240-3870，Δcmds=10，余额 914730→2182438，密度 35.6→37.6，nb 2~3（L8407435-8407520）",
                       "flow [VB]：t=3240 / 3330 / 3420 三个窗净流出 19.8 万 / 45.2 万 / 81.5 万，7 个窗合计约 137 万兵",
                       "同期 DeepBlue 给它的 3 笔救援捐款到账 72.3 万（t=3330 / 3410 / 3505）",
                       "之后 t≥2250 它一共 24 条陆攻，领土到 139475 格（logstats [QG]）"],
             statementType="observed"),
        dict(id="D07", t="2340~4320", bot="Safavid", decision="两个敌邻、1350 拍不出手，囤到密度 114.9（过了软上限）才动：t=3690~4320 陆攻净花 274.4 万兵拿 10782 格（约 255 兵/格），是 California 起手价的 6 倍；之后被围。",
             codePath=GATE, verdict="unclear", patternId="NEW-AT-01",
             evidence=["digest [E]：H 2250-3690 37689→37792 格，Δcmds=2，nb=2，余额 166597→4342909",
                       "digest [F]：t=3690~3780 4342909→2851806 兵（−34%），37792→39634 格（L8407486-8407500）；这一窗里有它自己给 Borsch 的一笔捐款（到账 537313 + 税 220436），扣掉以后陆攻花 113.0 万（flow [VB]）",
                       "flow（--t0 3690 --t1 4320）：『其余』负的合计 386.7 万、回流 112.3 万、净 −274.4 万，领土 37792→48574。分两段：t=3690~3960 净 −30.9 万 / +4165 格（Borsch 的 2 笔定不了的捐款 26.5 万可能混在回流里，74~138 兵/格）；t=3960~4320 净 −243.6 万 / +6617 格（368 兵/格）",
                       "对照：California t=3240~3870 净 −137.0 万 / +32388 格（42 兵/格）；Sun Quan t=3150~3960 净 −54.4 万 / +7730 格（70 兵/格）",
                       "flow [VA]：t≥3240 它的利息 1652.0 万，净流出 1385.0 万，领土只从 37792 到 49457（+11665 格）；t=4320 被围以后 8 条船少掉 885.9 万兵",
                       "判『存疑』：digest 的两段口径（425 兵/格 ≥150）命中 NEW-AT-01，但那个口径没扣同窗的捐款和后来退回余额的兵；扣完以后第一波并不贵，贵的是第二波。它更早出手会不会更便宜，没有影子看不到"],
             statementType="observed"),
        dict(id="D08", t="3330~4030", bot="DeepBlue / Courland", decision="救援捐款的比例被自己的留底压到 55~84/1024，照发：税和到账差不多大。",
             codePath=DON_RESCUE, verdict="error", patternId="NEW-DN-02",
             evidence=["squadfog [HH]：pct ≤70 的 6 笔里成交 5 笔，到账 637495、税 644540，其中 3 笔税 ≥ 到账",
                       "donfit [FD]：Courland t=3910 pct=61 到账 97847 / 税 101004；t=4000 pct=62 99561 / 101141；DeepBlue t=4030 pct=56 130876 / 146948",
                       "这些号发令时密度 78~80（L8407507~8407540 的 dMe），留底是 68×领土（L4382）"],
             statementType="observed"),
        dict(id="D09", t="3330~6440", bot="DeepBlue / Courland / Sun Quan → California", decision="被围或没仗打的 T4 号持续把兵输给前线的 California：成交 20 笔 871.6 万，California 28786→139475 格。",
             codePath=DON_SURPLUS, verdict="good", patternId="NEW-DN-G2",
             evidence=["donfit [FC]：IceKing 成交 20 笔，到账 8716403，捐出方付税 3914340（t=3330~6440）",
                       "squadfog [HJ]：t=3330~4300 DeepBlue 8 笔 2418461 + Courland 3 笔 336708；t=4980~6440 Sun Quan 4 笔 3485282 + Courland 4 笔 1956106 + DeepBlue 1 笔 519846",
                       "DeepBlue→IceKing 这一对成交 9 笔（另 2 笔定不了），离目录口径的 10 笔差 1 笔；DeepBlue 65 条快照里 26 条被围",
                       "flow [VA]：California 的利息 2844.9 万，成交的捐款收入 871.6 万；另有约 550 万的入账对应 Sun Quan 等 8 笔定不了的捐款"],
             statementType="observed"),
        dict(id="D10", t="4510~5215", bot="California", decision="停在 59185 格、超软上限时把盈余捐给同队的银行号（Courland 3 笔、Sun Quan 1 笔），400~500 拍后这些号又捐回来。",
             codePath=DON_SURPLUS, verdict="unclear", patternId="NEW-DN-07",
             evidence=["donfit [FB]：California 5 笔 / 成交 4 笔，到账 3507817、税 1457807；t=4510→Hamilton 和 t=4530→Courland 是连发（发第二笔时第一笔还没扣款，两笔都成交，多付到账 829367 + 税 344672）",
                       "收到捐款的 Courland t=4410~5040 20959→31359 格、Sun Quan t=4500~4860 30213→43280 格：钱是被用掉的",
                       "反向：Sun Quan→IceKing t=4980 起 4 笔成交 3485282（税 1448428），Courland→IceKing t=5050 起 4 笔 1956106（税 744292）",
                       "同一对 600 拍内两个方向都有成交：California↔Courland（4775 / 5050）、California↔Sun Quan（4510 / 4980）"],
             statementType="observed"),
        dict(id="D11", t="3470~6580", bot="Borsch → Safavid", decision="被围的 Borsch 把兵捐给同样被围、自己已经超软上限的 Safavid：12 笔 / 成交 9 笔 218.5 万。",
             codePath=DON_SURPLUS, verdict="error", patternId="NEW-DN-14",
             evidence=["donfit [FC]：Safavid 成交 9 笔，到账 2184505，税 635013；其中 4 笔成交时 Safavid 的密度 ≥100（t=5345 117.5、6150 / 6195 120.2、6560 117.7）",
                       "digest [J]：Safavid 61 条快照里 19 条被围、20 条超软上限；Borsch 68 条里 27 条被围",
                       "Safavid 反过来给 OldGuard（Borsch）4 笔：t=3755 成交 537313（税 220436），另 3 笔定不了；Borsch↔Safavid 在 t=3470 / 3755 两个方向都成交",
                       "两个号 t=4230 之后领土 47871→49457、10283→10543；盈余分支只排除密度 ≥132 的收款方（L4469）"],
             statementType="observed"),
        dict(id="D12", t="4680~6120", bot="Safavid / DeepBlue / Courland / Sun Quan / Borsch", decision="被围时每 60 拍一条不设价格上限的船：42 条、少掉约 1612 万兵，领土合计 +2200 格。",
             codePath=BOAT, verdict="unclear", patternId="NEW-SE-05",
             evidence=["flow [VC]（窗首被围且窗内有船）：Safavid 7 窗 / 8 条 −8859313 兵、领土 +161；DeepBlue 8 / 10 −4379269、+1135；Courland 5 / 7 −1357302、+152；Sun Quan 3 / 3 −1273814（下一窗回来 868937）、+474；Borsch 9 / 14 −249954、+278",
                       "Safavid t=4680~4770：2 条船，6654844→2960507 兵（少 3939425），48574 格不变（L8407636-8407646）；DeepBlue t=5490~5580：2 条船，2605837→755818，36552 格不变（L8407747-8407758）",
                       "代码：没有陆上邻居时 maxEff = Infinity（L5004），落点不是空地就带 0.5×（余额 − 留底）",
                       "判『存疑』：日志里没有落点。DeepBlue、Sun Quan t=5490~5580 的船正好落在 California 猛攻 Player 188 的那两个窗里，可能是烧在同一个敌人身上；Safavid 的船能去的非受保护海岸只有 T4 的野人和人机"],
             statementType="inferred"),
        dict(id="D13", t="4330~5265", bot="Reconquista → Dream", decision="往正在崩、自己已经顶着上限的队友身上捐：8 笔 / 成交 6 笔 156.3 万，税 85.0 万；Dream 照样阵亡，兵清零。",
             codePath=f"{DON_SURPLUS}；{ENG_DON}", verdict="error", patternId="NEW-DN-12",
             evidence=["donfit [FC]：Dream 成交 6 笔，到账 1562883，税 849561（税占付出的 35.2%）；squadfog [HJ]：3 笔被夹小，到账 548497 / 税 430073；t=5265 那一笔没成交（Reconquista 1999363→2132800 兵和纯利息一兵不差；Dream 的 died 行是 t=5288，最可能是指令落地时它已经出局）",
                       "收款时 Dream 的密度：t=4330 134.7、4410 121.7、4610 142.7、4990 115.7、5125 131.2、5200 106.0（digest [G]）；t=4500 的快照余额正好是 150×领土，30 拍后 Reconquista 照样下单",
                       "Dream t=4320~5220 10133→3068 格，这段 0 条陆攻；t=5288 出局时余额 257943",
                       "Reconquista 自己这一段 17886~18954 格不动（t=3960~5310，密度 100~117）"],
             statementType="observed"),
        dict(id="D14", t="2070~5288", bot="Dream", decision="只有一个真人敌邻，3200 拍里丢 11083 格，中后期只发过 1 条陆攻；密度 105~150 时把兵用在船和捐款上。",
             codePath=f"{GATE}；{SAFE}", verdict="error", patternId="NEW-DF-01",
             evidence=["logstats [QD]：峰值 13230（t=1800）→ 阵亡，期间指令 14 条、其中船 10 条；[QG] t≥2250：13 = 陆攻 1 + 船 9 + 捐款 3",
                       "logstats [QB]：硬上限快照 2 条（t=4500、5220）；[QF] 单邻窗密度 100~128 的 8 个窗全部没有非捐款指令",
                       "squadfog [HD]：t=4320~4410 10133→9317、4680~4770 8818→7604、4770~4860 7604→6148、5130~5220 5131→3068",
                       "宽口径命中（有船和捐款，陆攻 ≤1 条）；挡住陆攻的门槛是推断，见 deaths[].gate"],
             statementType="inferred"),
        dict(id="D15", t="3330~5670", bot="Catalonia", decision="T3 只有它一个编队号：被 Player 188 从 20910 格吃到 4547 格，t≥2250 只发 2 条陆攻；t=5400 密度 149.5、185.6 万兵时 270 拍丢 7868 格、0 条指令。",
             codePath=f"{GATE}；{SAFE}", verdict="error", patternId="NEW-DF-01",
             evidence=["squadfog [HD]：t=3330~3510 20910→13876（Δcmds=0）；t=5400~5670 12415→4547，余额 1855828→444101，Δcmds=0（L8407736-8407762）",
                       "logstats [QF]：单邻窗密度 ≥128 的 8 个窗里 7 个没有指令（t=4950~5580，丢 6168 格）；[QG] t≥2250：8 = 陆攻 2 + 船 5 + 戳刺 1",
                       "进攻者是 Player 188：Reconquista 的 6 条 HL-ASSIST 都写 enemy=5(Player 188) for ally=12(Catalonia)（L8407508、8407631、8407643、8407742、8407750、8407753）",
                       "它没有同队的编队号：整局 0 笔捐款进出；t=5670 之后回到 6666 格（Player 188 被 California 打垮后留下的空地）"],
             statementType="inferred"),
        dict(id="D16", t="3825~5735", bot="Reconquista", decision="9 次跨队协防戳刺都打 Player 188（6 次为 T3 的 Catalonia、3 次为 T4 的 California），估计出兵 185.6 万。",
             codePath=POKE, verdict="unclear", patternId="NEW-MT-02",
             evidence=["logstats [QC]：为 Catalonia 6 次估计 1191945 兵（t=3825、4665、4705、5465、5495、5560），为 IceKing 3 次 664308 兵（t=5675、5705、5735）",
                       "Catalonia 没被救住：t=5400~5670 12415→4547；Reconquista 自己 t=5490~5850 19888→25644 格（Player 188 也是它的敌人）",
                       "全场 14 次戳刺里 12 次跨队；另 2 次是 Sun Quan 为同队的 Courland 打 Player 287（t=4635、4735）"],
             statementType="observed"),
        dict(id="D17", t="5760~6570", bot="Sun Quan", decision="1 个敌邻、480~590 万兵、密度 99~122，810 拍每窗被啃 3~12 格（共 63 格），0 条陆攻和船。",
             codePath=GATE, verdict="unclear", patternId="NEW-EC-07",
             evidence=["squadfog [HN]：t=5760~6570 9 个窗里 8 个掉地，序列 3 4 6 7 9 0 10 12 12，密度 71~122，陆攻 + 船 0 条",
                       "digest [I]：t=6300~6570 48212→48178 格，余额 5887718→5444667，nb=1",
                       "啃它的是谁看不到；量级像内置 AI 的规则进攻（每窗几格）。对非真人的小单子有 minCmd 门槛（L5367：单子 < 余额的 4.7% 不发），余额越大越不出手——推断"],
             statementType="guess"),
        dict(id="D18", t="6390~6643", bot="房间 0 八个号", decision="编队占 85% 以后收尾卡住：剩下的大野人是 T4 的队友，T4 的四个号没有可打的目标；异队编队号之间的保护解除不了，能打它的 4 个异队号只能发船。",
             codePath=f"{PROT}；{ENG_WIN}", verdict="unclear", patternId="NEW-MT-07",
             evidence=["结果行：编队 8 个号 360538 格（85.04%）；alivePlayers=10，第 2 名和第 10 名不是编队号",
                       "第 2 名在 49485~63412 格之间。T2 的野人 t=5288 一共 81718 格，此后 Player 188 又从 Catalonia 拿了 7868 格；California t=5310~6480 +69789 格、Reconquista t=5310~6570 +18199 格，合计 87988 格——T2 的野人最多剩一两千格，Player 188 在 t=6390~6480 之间出局（三个号的 nb 同时 1→0，California 身边 176 格空地）",
                       "T1、T3 在 t=5288 的全队领土正好等于各自那个编队号的领土（没有野人的地了），人机 3392 格 → 第 2 名只能是 T4 的野人（t=5288 有 71569 格）。它 t=6295、6405 还在跨海打 T2 的 Borsch（Safavid 的两笔救援捐款，L8407841、8407864）",
                       "t=6570：California、DeepBlue、Courland、Borsch、Reconquista、Catalonia 的 nb 都是 0（L8407877~8407883）",
                       "T4 四个号 2607 万兵不能打队友；能打它的 4 个异队号共 1148 万兵（Safavid 636 万、Reconquista 361 万、Borsch 76 万、Catalonia 76 万），最后的快照里 nb 都是 0（不和它接壤），只能靠 idleBoats 每 60 拍一条船",
                       "判『存疑』：第 2 名的队号是推出来的；这个状态再打下去会不会解开（4 个异队号用船磨掉那个野人）也看不到——对局在这里断了"],
             statementType="inferred"),
        dict(id="D19", t="6643", bot="房间 0 八个号", decision="8 个客户端的本地拍在同一拍停住，52 秒后各自写 left；驱动层没有『服务器停拍』的检测。",
             codePath=DRIVER, verdict="unclear", patternId="NEW-IO-07",
             evidence=["results.csv：left 行 tick=6643×7、6636×1，写入 15:23:36.332~36.679Z，seconds=444~445；Dream 的 died 行 tick=5288 / seconds=316 → 1355 拍用了 128 秒（按 56 毫秒只要 76 秒）",
                       "最后的日志行是 t=6590 / 6595 / 6600 的 HL-SLOW-TICK（40.5 / 69.4 / 36.1 毫秒，L8407885~8407887）；没有 t=6660 的 HL-TICK",
                       "房间 1 的 end 行写在 15:21:11.285Z，比这 8 条 left 早 145 秒",
                       "和目录里 NEW-IO-07 的差别：这里不是客户端先后停发指令，而是 8 个号同一拍收不到服务器的拍"],
             statementType="inferred"),
        dict(id="D20", t="0~90", bot="Mali（房间 1）", decision="房间里只有它一个号，却按 squad=2 排槽位：名字在名字池里的野人 Russian Empire 被算成编队友。",
             codePath=f"{SPAWN}；{C110}: isOurSquadBot L3973-3976（只看名字）", verdict="unclear", patternId="NEW-MT-04",
             evidence=["L8407009~8407072：Mali 的 10 条 [HL-SPAWN] 都是 squad=2、rankIdx=0、slot=8",
                       "truth [TB]：Mali 落点 (18,162)，10 条指派里的最后一条；truth [TH]：5 笔捐款的收款方 Russian Empire 是玩家 12、T1 的野人",
                       "t=630 Mali 1769 格，同房真人人均约 2800 格"],
             statementType="observed"),
        dict(id="D21", t="720~1980", bot="Mali（房间 1）", decision="指令比决策晚 125~253 拍照常发：9 批同拍冲出 3~9 条，71 条陆攻里 17 条没生效，重发占陆攻 + 发船的 46%。",
             codePath=DRIVER, verdict="error", patternId="NEW-IO-01",
             evidence=["shadowcmp [SF]：执行拍 900~1079 时延中位 125、1080~1259 178、1260~1439 197、1440~1619 248（最大 658）、1620~1799 253（陆攻 100% 无效）、1800~1979 160；1980 之后 12 拍",
                       "shadowcmp [SB2]：9 批；t=1673 一批 9 条全部无效，t=1337 一批 8 条",
                       "truth [TG]：陆攻 71 / 没生效 17 / 叠加 25；重发串 16 串、多发 37 条（46%）",
                       "同房的 [APEX] 十个号同一时段也是这样（shadowcmp_peer [SB]：1260~1800 时延中位 65~267 拍）——是主机的事"],
             statementType="observed"),
        dict(id="D22", t="1500~1870", bot="Mali（房间 1）", decision="贴着内置 AI 不出手：29 个普查点全被挡，16 个是防人机留底 sb 取了同队真人的余额。",
             codePath=SB, verdict="error", patternId="NEW-EC-08",
             evidence=["shadowcmp [SJ]：Mali 1500~1870 全被挡 29 点 = safe:sb×16、price×7、noOffer×4、minCmd×1；sb 的来源 16 次全是同队真人",
                       "中位：自己余额 50802、留底 85712；被挡的 AI 5805 格、334 兵，吃光只要 10089 兵",
                       "truth [TC]：这一段 T1 全队 45.8%→57.7%，Mali 2.71%→2.30%；t≈1980 起它被队友 Player 600 围住（接壤 180 格）"],
             statementType="observed"),
        dict(id="D23", t="3332~4214", bot="Mali（房间 1）", decision="被围后按盈余分支给 Russian Empire 捐 5 笔 pct=185：到账 80.0 万、税 27.5 万，每次捐完自己的密度掉到 59 左右。",
             codePath=DON_SURPLUS, verdict="unclear", patternId="NEW-DN-05",
             evidence=["truth [TH]：5 笔全部成交，到账 800418、税 275411；收款方额度已用 104→134（上限 219→309）",
                       "Mali 发令时 859316 兵 / 10920 格（密度 78.7），捐后约 649523 兵（密度 59.5），低于同一函数对有海岸的号用的 68（L4382）",
                       "Russian Empire 是 T1 的前线：52916→73764 格，t=3524 / 4031 参与打掉 noah88、riku_x（truth [TB]）——认错了人，钱却给到了在打仗的队友",
                       "t=4214 之后 Russian Empire 没有仗打（L4477-4478），Mali 停捐，密度涨到 120.2（t=4680）"],
             statementType="observed"),
        dict(id="D24", t="1980~4691", bot="Mali（房间 1）", decision="被队友围在 10920 格 2700 拍；10 条船里 7 条的手续费比船上的兵还多。",
             codePath=BOAT, verdict="error", patternId="NEW-SE-03",
             evidence=["truth [TL]：发船 10 条，船上兵 44571，手续费 39482；其中 7 条手续费 > 船上兵，共付 29590",
                       "靠岸：空地 7 次 40431 兵、自己的地 3 次 2870 兵；truth [TD]：t=2520 起 10920 格不变",
                       "truth [TC]：T1 从 64.4%（t=2340）到 98.4%（t=4500），Mali 一直是 2.58%"],
             statementType="observed"),
    ],
    newPatterns=pick("NEW-MT-07", "NEW-AT-G3", "NEW-EC-04", "NEW-DN-14", "NEW-DN-12", "NEW-DN-07", "NEW-SE-05", "NEW-DF-01", "NEW-EC-09", "NEW-MT-02",
                     "NEW-IO-08", "NEW-IO-07", "NEW-IO-10", "NEW-DN-G2", "NEW-AT-01", "NEW-DN-02", "NEW-MT-04", "NEW-DN-05", "NEW-EC-08", "NEW-IO-01"),
    lossArchetype="external",
    archetypeNote="房间 0（9 个号）没有打完：编队分在四个队、合占 85% 陆地、T4 的四个号自己就有 60%，8 个客户端在本地拍 6643 同时断流，结果表全是 left——按规程的七种分型只能记 external，outcome.result 记 open（不算赢也不算输）。"
                  "对局卡写的『赢、98.4%』是房间 1：Mali 所在的 T1 赢了，Mali 自己占 2.58%，是搭车。局内值得看的是三件事：t=2250~3150 的全队停手；T1 / T3 的两个孤号挨打不还手；编队占到 85% 以后收尾卡住。",
    winnerNotes="房间 0 没有赢家。领先的是 T4：t=5288 占 57.4%，其中编队 4 个号占 70.6%。T4 靠 California 一个号长起来——t=3240 在密度 36 时出手（630 拍领土翻倍、42 兵/格），"
                "t=5490~6570 吃掉 T2 的野人 Player 188（63094→139654 格）；DeepBlue、Courland、Sun Quan 被围以后把兵捐给它（成交 20 笔 871.6 万）。T4 的那个野人 t=5288 有 71569 格，停住时约 5~6 万格（推断它就是第 2 名）；14 次协防戳刺没有一次打它，船的落点看不到。"
                "房间 1：T1 获胜。T1 的野人在人机收割期就拉开了差距（(900,1260] 人均吃人机 5531 格，[APEX] 人均 1001 格；t=1800 T1 57.7% 对 T2 21.0%），t=2284~4031 把 [APEX] 十个号逐个吃掉，"
                "主力是 [NL] Pizza Cal、Player 642、Player 600、Russian Empire、[TR] BAĞIMSIZ；t=3907 起引擎的『领先队 ≥90%，人机提速』生效，t=4691 结束。",
    peerComparison="本包的 sameMatchPeer 为空。房间 1 里有另一支受控编队 [APEX]×10（A010 的 squad10，c116），全在 T2、和 Mali 不同队，t=4031 前全部阵亡。从 Mali 这一侧看到的三点："
                   "（1）同一波主机卡顿也打在它们身上（shadowcmp_peer [SB]：执行拍 630~1260 时延中位 24~81 拍、1260~1800 65~267 拍，同拍成批最多 9 条）；"
                   "（2）人机收割期它们互相锁住：t=900~1260 贴着人机的 271 个号·点里 218 个全被挡，211 个卡在防人机留底 sb 上，其中 176 个的 sb 是同队 [APEX] 队友的余额、90 个是互锁，"
                   "199 个里吃光那个人机只要自己余额的 10% 以内（shadowcmp_peer [SH]）——十个号挤在一起（出生点相距几十到一百多像素），共用人机邻居；"
                   "（3）人机打它们的交换比是 1.16（余额损失 ÷ 人机耗兵），其它真人和 Mali 都是 0.45（truth [TN]）。Mali 用的是 c110、单号，t=900~1260 人均吃人机 3295 格，是 [APEX] 的 3.3 倍、其它真人的 0.6 倍。"
                   "c116 那一侧的逐条审计归 A010 的复盘。",
    teamSplitNotes="房间 0 的 9 个号没有战队标签，被分成 4 / 2 / 2 / 1。后果：（1）捐款只能在队内走——T4 有 3 个银行喂 1 个前线，T2 是两个被围的号互相倒，T1 是一个号往正在崩的队友身上填，T3 的孤号一兵也拿不到；"
                   "（2）异队的编队号按名字互相保护，整局没有互打的迹象（两端都被围却掉地的窗只有 5 个、共 92 格，squadfog [HC]），协防戳刺 14 次里 12 次是替别的队打；"
                   "（3）挤在一起出生的五个号分属三个队，谁也不能打谁，4 个被围；"
                   "（4）最后编队占 85%、分在四个队，最大的野人是 T4 的队友——保护解除不了，占着 60% 陆地的 T4 四个号没有可打的目标，收尾卡住。房间 1 只有 1 个号，没有分队问题。",
    ledgerExtra=dict(
        cardAudit="对局卡的 drop30Count=35 / totalTransfers=70 / likelyRejectedTransfers=1 / boxedHighDensSnapshots=34 都是两个房间合计。房间 0：DROP30 33 段、捐款 65 笔；房间 1：Mali 捐款 5 笔（真值全部成交）。"
                  "『疑似被拒 1 笔』：按余额序列拟合（donfit），房间 0 的 65 笔里能确定没成交的是 1 笔——t=5265 Reconquista→Dream（救援，pct=101，L8407719）：Reconquista 的余额从 1999363（t=5265）到 2132800（t=5310）和纯利息一兵不差，这笔没扣款；"
                  "Dream 的 died 行是 t=5288，发令后 23 拍——最可能是指令落地时 Dream 已经出局（引擎不给已出局的人转兵，game.js L407；发令时 Reconquista 看到的 Dream 密度是 64，不在上限）。另有 21 笔定不了（捐出方同一个快照窗里还有陆攻或船，余额落差分不清是谁的）。"
                  "『被围且高密度 34 条』：房间 0 被围且密度 ≥95 的快照 Safavid 16 条、Borsch 15 条（digest [J]），其余在房间 1 的 Mali（t≥4500）。",
        room0Drop30Note="DROP30 33 段的归因（digest [F]）：打下地 18、发船 10、丢地 3、花了兵没涨地 1、捐款 1。发船的 10 段（Courland 4、DeepBlue 2、Borsch 2、Safavid 1、Sun Quan 1）窗首都没有敌邻（nb=0）；"
                        "丢地的 3 段是 Dream 1 段、Catalonia 2 段。t<2300 的 15 段里 13 段是打下地（两段口径每格 3.9~59.8 兵），1 段是 Reconquista t=1620 花了兵当窗没涨地（下一窗 +2617 格，两段口径 18.8 兵/格），"
                        "1 段是 Courland 的船；没有清仓后被吃回去的（最多是 Reconquista t=1530~1620 丢 301 格）。",
        room0DonationsByTeam=dict(T4=dict(logged=38, executed=26, delivered=13083742, tax=5667896), T2=dict(logged=16, executed=10, delivered=2721818, tax=855449),
                                  T1=dict(logged=11, executed=7, notExecuted=1, delivered=1737281, tax=922038), T3=dict(logged=0), src="scripts/donfit.py [FB][FC]"),
        room0DonationsByKind=dict(rescue=dict(logged=17, executed=13, notExecuted=1, delivered=4396930, tax=2318248), surplus=dict(logged=48, executed=30, delivered=13145911, tax=5127135),
                                  smallPct=dict(note="pct ≤70/1024", logged=6, executed=5, delivered=637495, tax=644540), src="scripts/squadfog.py [HH]"),
        room0Clipped=dict(count=4, delivered=764514, tax=514186, intoDream=dict(count=3, delivered=548497, tax=430073), src="scripts/donfit.py [FA]；squadfog.py [HJ]"),
        room0DoubleSend=dict(count=1, donor="California", t="4510→Hamilton、4530→Courland", extraDelivered=829367, extraTax=344672, src="scripts/donfit.py [FA]"),
        room0DonorDensityAfter=dict(note="盈余捐成交后的密度（中位）；同一函数对有海岸的号用的留底是 68", DeepBlue="78.4→59.2（6 笔里 5 笔 <68）", Courland="78.3→59.2（3 笔里 2 笔）",
                                    Borsch="120.8→85.9（9 笔里 2 笔）", SunQuan="120.9→95.0", Reconquista="119.3→97.8", California="118.4→90.7", src="scripts/donfit.py [FE]"),
        room0ReceiverOverSoftCap=dict(executed=11, delivered=3549515, tax=1515552, byReceiver={"Dream": 6, "Safavid": 4, "Courland": 1}, note="收款方当拍之前最近一条快照密度 ≥100"),
        room0RoundTrips=["Borsch↔Safavid（t=3470 / 3755）", "Dream↔Reconquista（t=3870 / 4330）", "California↔Courland（t=4775 / 5050）", "California↔Sun Quan（t=4510 / 4980）"],
        room0QuotaCheck="引擎受捐额度对账（donfit [FQ]）：成交的 43 笔里记账后超出额度的 0 笔；t<4284 额度用得最多的是 IceKing（88 / 309 点）。这一局没有额度墙。",
        room0Flow=dict(note="t=3240~6643，只看日志：利息 / 『其余』净额（= 实际余额变化 − 利息 − 成交捐款收支；负数主要是陆攻、船和挨打）/ 领土首末",
                       Safavid="1652.0 万 / −1385.0 万 / 37792→49457", California="2844.9 万 / −2001.1 万 / 25702→139475", SunQuan="1501.8 万 / −656.7 万 / 17577→48178",
                       DeepBlue="1109.5 万 / −519.1 万 / 29087→36690", Courland="882.0 万 / −738.5 万 / 18074→31883", Reconquista="781.8 万 / −323.5 万 / 16784→37153",
                       Catalonia="302.8 万 / −311.6 万 / 21004→6629", Dream="158.7 万 / −300.1 万 / 9652→3068", Borsch="302.7 万 / −1.3 万 / 6825→10543", src="scripts/flow.py [VA]"),
        room0BoxedBoats=dict(Safavid="7 窗 / 8 条：−8859313 兵，+161 格", DeepBlue="8 / 10：−4379269，+1135", Courland="5 / 7：−1357302，+152", SunQuan="3 / 3：−1273814（下一窗 +868937），+474",
                             Borsch="9 / 14：−249954（下一窗 +432033），+278", total="42 条，约 −1612 万兵",
                             caveat="『少掉的兵』= 按利息公式应有的余额 − 实际余额 − 成交捐款；定不了的捐款没有扣（Safavid 的 3 笔合计约 230 万，不在这些船窗里）。没有录像，船靠在谁身上、兵是烧掉、并给队友还是回了余额都看不到。",
                             src="scripts/flow.py [VC]；logstats.py [QE]"),
        room0Assists=dict(count=14, crossTeam=12, estTroops=3106278, src="scripts/logstats.py [QC]（按戳刺前一条快照余额的 10.06% 估）"),
        room0InvisibleLoss=dict(windows=5, cells=92, src="scripts/squadfog.py [HC]"),
        room0SentAccepted=dict(sent=941, accepted=917, notAccepted={"California": 10, "Safavid": 4, "DeepBlue": 3, "Reconquista": 3, "Borsch": 2, "Dream": 1, "Sun Quan": 1},
                               note="results.csv 的 sent / accepted 两列（含出生点指令）。accepted − 出生点指令数 和最后一条快照的 cmds 只差 0~4 条（房间 1 的 Mali 差 0）："
                                    "HL-TICK 的 cmds 只数客户端接受了的指令。没被接受的 24 条是什么原因，包里没有记录。", src="bundles/B009/results.csv"),
        room1Truth=dict(donations=dict(executed=5, delivered=800418, tax=275411, to="Russian Empire（T1 的野人，名字在名字池里）", src="truth.txt [TH]"),
                        boats=dict(count=10, troops=44571, fees=39482, feeAboveTroops=dict(count=7, fees=29590), landedNeutral=40431, landedOwn=2870, src="truth.txt [TL]"),
                        resends=dict(landAndBoat=81, resent=37, src="truth.txt [TG]"),
                        drop30=dict(windows=3, byCause={"陆攻": 3}, src="truth.txt [TK]"),
                        huskGifts=dict(count=21, toMali=dict(count=1, delivered=14277, t=3826), biggest="betray = send → Russian Empire 3832155（t=4393）", src="truth.txt [TM]"),
                        aiExchange=dict(Mali=0.45, apex=1.16, otherHumans=0.45, note="余额损失 ÷ 人机实际耗兵", src="truth.txt [TN]")),
    ),
    sideRoomExtra={
        1: dict(
            summary="Mali 一个号在 T1（另 9 个是野人），对面 T2 是 [APEX]×10。Mali：出生点改 10 次落在左上角，t=630 只有同房人均的六成；t=720~1980 赶上主机卡顿（时延中位 125~253 拍）；"
                    "t=1520 峰值 11645 格，之后被人机咬回 1700 格，t≈1980 起被队友 Player 600 围住，10920 格一直到终局（2.58%）。"
                    "被围后给名字撞池的队友 Russian Empire 捐 5 笔 80.0 万。T1 的野人从人机期一路领先，t=2284~4031 吃光 [APEX]，t=4691 以 98.4% 获胜。",
            perCapitaNote="t=1800：T1 57.7% ÷ 10 人 = 人均 5.77%，Mali 2.30%，是 T1 人均的 0.40；[APEX] 人均 2.10%。",
            lagTable="shadowcmp [SF]（Mali，按执行拍每 180 拍）：0~719 时延中位 11~14 拍；720~899 53；900~1079 125；1080~1259 178；1260~1439 197（陆攻 33% 无效）；1440~1619 248（最大 658）；"
                     "1620~1799 253（陆攻 100% 无效）；1800~1979 160（50% 无效）；1980 之后 7~15 拍。",
            apexDeaths="leo_tx 2284、zero_7 2321、ryan_m 2636、alex_k 3210、noah88 3524、talon5 3585、zexos1 3728、sora_w 3948、kaito9 3993、riku_x 4031；全部在 t=4613 离开（truth [TB]）。",
        ),
    },
    wentWell=[
        "开局按期：OPENING-CHECK 九个号全部 OK，t=630 人均 2905 格；t<1800 没有号被围。",
        "t=1620~2250 低价拿地，编队从 23.62% 到 46.35%（California 两段口径 5~8 兵/格）。",
        "California 在密度 36 时就出手（全队第二个，比 Sun Quan 晚 90 拍），630 拍领土翻倍（42 兵/格），后来一个号长到 139654 格。",
        "T4 的银行：DeepBlue、Courland、Sun Quan 给 California 成交 20 笔 871.6 万。65 笔捐款里能确定没成交的只有 1 笔（收款方出局前 23 拍发的），没有额度墙。",
        "异队编队号之间的保护全程守住：停住时 9 个号里 8 个活着，合占 85.04% 陆地。",
    ],
    unknowns=[
        "房间 0 为什么在本地拍 6643 断流：8 个客户端同一拍收不到服务器的拍，52 秒后写 left。是房间被关、主机网络断了，还是测试脚本到点收场，包里没有记录。",
        "被围的号发出的 42 条船、约 1612 万兵去了哪里：没有录像，落点、靠没靠岸、烧在谁身上都看不到。Safavid 一个号就少了 886 万兵。",
        "Dream、Catalonia 密度 100~150 时不打唯一的真人邻居，是哪一道门槛在挡（唯一缓冲、对真人的留底、还是报价）；打 Dream 的是谁。房间 0 没有影子。",
        "第 2 名（约 5~6 万格）是 T4 的野人，这是按领土算术和『Player 188 已出局』推出来的，结果行里没有名字和队号；它从 t=5288 的 71569 格少掉的 0.8 万~2.2 万格被谁拿走、第 10 名（不到 6666 格，t=5760 起啃 Sun Quan 的多半是它）是谁，都看不到。",
        "Sun Quan 的余额在 t=5580、5760、5850、6210 四个窗比利息公式多出 130 万、87 万、160 万、125 万，同窗没有成交的捐款：是船回到自己的岸上，还是 T4 的野人给它捐了兵，看不到。",
        "21 笔定不了的捐款：Sun Quan→IceKing 的 7 笔大概率成交了（California 同窗有等量的入账），其余 14 笔分不清。",
        "房间 0 的客户端相对自己的服务器落后多少：只有和房间 1 的相对值（最多 120 拍）和 12 条没生效的指令，绝对时延量不出来。",
    ],
    mechanicsQuestions=[
        "线上的团队局什么时候算结束？归档引擎要领先的队拿下全部陆地（game.js victoryTick L1398-1412）；B019 在 64.4% 就出了 end 行，这一局 T4 约 72%~75% 时没有 end 行就断了。",
        "船靠在敌人密度很高的岸上会怎样：按归档引擎，开进攻后第一圈的成本 ≥ 船上的兵时，兵全部按伤害烧掉、一格不拿（game.js expandAttack L958-1060）；没有空闲进攻槽时船上的兵直接没有去处（boats.js L282）。线上是否一致，需要一局有录像的被围发船来核。",
        "hasWildOutsidersAlive 用的 g.isBot 在线上客户端里对『已经离开的真人』是否为真？如果是，T4 的野人一离开，异队编队号之间的保护就会解除，四个队的编队号开始互打。",
        "捐款的税是捐出方余额的 64/1024、和 pct 无关：本局 pct=55~67 的救援捐款拟合出来的税（14.5 万~15.0 万）都比到账大或相当，和这条规则一致。",
        "领土 ≤ 峰值的 1/4 出局，峰值在掉地期间会缓慢衰减：Dream 峰值 13230、出局时 2147 格（0.162），不是 3307 格。",
        "余额硬上限 150×领土：Dream 在 t=4500、5220 的余额正好是 150×领土；到顶以后收不进捐款（装不下 1 兵时整单不成交）。",
    ],
    scripts=[
        "c136-review/agents/R08/scripts/facts.py B009 [--room 1]（本局加了：没有录像的房间按『捐款边 + 结果行全队领土 + 每队人数上限』推队号 TEAM_BY_EVIDENCE；没有 end 行且领先的队不到 90% 时结果记 open）",
        "c136-review/agents/R08/scripts/flow.py B009 --room 0（本局新写：只看日志的兵的流水——每个快照窗的利息、成交捐款收支、其余；[VC] 被围且有船的窗少掉多少兵）",
        "c136-review/agents/R08/scripts/donfit.py / donwall.py / teamshare.py / logstats.py / noeffect.py / lagorder.py / squadfog.py / spawnlog.py B009（房间 0，只看日志）",
        "c136-review/agents/R08/scripts/clockskew.py B009 --ref-room 1 --room 0（两个房间对表；[KC] 结果行的写入时间对拍号）",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/resim_r08.mjs B009；truth.py B009（房间 1 真值 [TA]~[TO]）",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/shadow.mjs B009；shadowcmp.py B009（Mali，c110）",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/shadow.mjs B009 --peer-tag APEX --side peer；shadowcmp.py B009 --side peer（[APEX]×10，c116-vb）",
        "c136-review/agents/R08/scripts/harvest.py / top.py / spawncheck.py B009（房间 1）",
        "c136-review/agents/R08/scripts/build_review.py B009（本局加了 outcome.result=open）",
    ],
    confidenceOverall="medium",
    confidenceNote="房间 1（1 个号）的数字来自逐兵对上的真引擎重演和影子，可信度高。房间 0（9 个号）只有日志：领土、余额、指令数、捐款日志是观察值；队号、『第 2 名是 T4 的野人』、停手和不还手的门槛、船的去向是推断或未知，文中逐条标了。"
                   "捐款的成交与否按余额序列拟合，43 笔成交是下限。",
)
