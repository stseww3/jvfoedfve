# B019 人工分析部分。一个物理房间，3 队 × 17 个真人；编队 20 个账号全在这个房间里，被分到三个队（T1×5、T2×9、T3×6）。
#   真值：scripts/resim_r08.mjs 逐拍重演到 t=1246（录像由 xX_Shadow_Xx 的客户端上报，它冻在 1246 拍；占全场 10%），202/202 条 traj 快照地、兵都一致。
#   t>1246 只有日志：HL-TICK（每 90 拍）、HL-DONATE、HL-ASSIST、结果行；HL-TICK 的 t 是各号客户端的本地拍。
#   出处：out/B019/digest.txt、truth.txt [TA]~[TO]、shadowcmp.txt [SA]~[SI]、lagstats.txt、bursts.txt、harvest.txt、top.txt、perhead.txt [PH-A]~[PH-C]、spawncheck.txt、
#         lagorder.txt、clockskew.txt、logstats.txt [QA]~[QG]、noeffect.txt [NA]~[ND]、donfit.txt [FA]~[FE]、donwall.txt [WA]~[WI]、squadfog.txt [HA]~[HI]。
#   L 号 = bundles/B019/in_game.log 每行开头的原始行号。
from patterns_catalog import pick

C110 = "src/strategy/v27-team-c110.js"
SIM = "src/sim/sim"

SPAWN = f"{C110}: Policy.chooseSpawn L4007-4064（每个号在自己的客户端里排槽位：HL-SPAWN 行的 slot / rankIdx / chosenSlots 各号不同）"
DRIVER = f"{C110}: 文件头 L2-47（驱动层 afterTick 包装：只有 450 ms / 8 拍的在途保护，没有时延检测，也没有掉线检测）"
SB = (f"{C110}: winFloor L4542-4550（打人机前的留底 = max(价位底, dpKeep, sb)）→ safeFinite L2532-2541 / L2773-2784 → threatOf L464-490"
      "（sb 取的是共用同一个人机邻居的另一个真人的余额，不分是不是编队友）")
ANALYZE = (f"{C110}: analyze L420-448（L440：isProtectedSquadMate 为真的邻居不进 nb）；isProtectedSquadMate L3993-3996"
           "（队友 / Boss，或『场上还有野人』且名字在名字池里 isOurSquadBot L3973-3976——只看名字，不看 g.isBot）")
DON_HEAD = f"{C110}: tryDonateToTeammate L4369-4497"
DON_FLOOR = (f"{DON_HEAD}（L4372 冷却 18 拍；L4382-4385 留底 = max(有海岸且 t≥1100 时 68×领土, 对真人留底)，自己正挨真人打就不捐；"
             "L4387-4389 可捐比例 maxSafePct ≥55/1024 才捐 → 有海岸的号密度到 77.6 就开始捐）")
DON_RESCUE = (f"{DON_HEAD} 的救援分支 L4423-4444（L4424 只按 isOurSquadBot 的名字挑人，不看 g.isBot；L4428 只数『不是空壳、不是受保护编队友』的进攻兵；"
              "L4434 对方挨真人打且（进攻兵 ≥8% 余额 或 密度 <75）；L4436-4437 同队且自己密度 ≥ max(55, 对方密度+15) 就捐 min(maxSafePct, 155)）")
DON_SURPLUS = (f"{DON_HEAD} 的盈余分支 L4462-4497（L4462-4463 被围的号密度 ≥55 就进来；L4467 收款方必须是同队的 Boss 或名字池里的名字，不看 g.isBot；L4469 对方密度 ≥132 跳过；"
               "L4477-4478 对方没有真人敌邻、没有在途进攻且 t>2200 跳过；L4482 捐出方被围时不再要求对方在打仗；L4489 pct = 被围 ? (密度>110 ? 280 : 185) : 153，不看对方还装得下多少）")
BUY = f"{C110}: Policy.act L4781-4944 → Policy.buyLand L5250-5548（对真人的留底：Policy.safeAt L4524-4541 → safeAt L2744-2754 =（最富真人邻居余额 − 1.5×领土）÷1.78）"
BOAT = (f"{C110}: Policy.idleBoats L4979-5006（L4996 没有陆上邻居时 maxEff = Infinity）→ boatOut L1035-1051（落点不是空地时船上的兵 = boatFrac ×（余额 − 留底））"
        "→ searchWater L1056-1115（L1104 跳过受保护的编队友）")
ENG_DON = (f"{SIM}/game.js donate L404-416 / transfer L388-401（手续费 = 捐出方余额的 64/1024，按全额余额收）/ receiverRoom L340-345（到账 ≤ 150×收款方领土 − 收款方余额；装不下 1 兵时整单不成交）"
           " / donationFree L360-362（t≥4284 或收款方是空壳时不查额度）")
ENG_LEAVE = (f"{SIM}/game.js leave L229-233、isBot L215-217（离开的号 state=2：不再有利息，由引擎托管，每 80 拍向随机一个邻居出兵，1.5% 起、每次加 0.5%、最多 25%）；"
             f"{SIM}/bots.js botAttackTeam L142-169")
ENG_ELIM = f"{SIM}/game.js aliveTick L1298-1312（任何玩家的领土 ≤ 历史峰值的 1/4 就出局，剩下的地变成空地、余额清零）"

R = dict(
    contextExtra=dict(
        truthTeamSplit="录像头和重演：编队 20 个账号全在这个房间，T1×5（Swiss Guard 12、Watermelon 14、Farnese 16、Zenobia 26、CJ 27）、"
                       "T2×9（Kandy 8、Charlemagne 10、New York 15、Barbary 17、bruh 20、Mansa Musa 22、Goguryeo 28、Genos 29、Raiden 30）、"
                       "T3×6（xX_Shadow_Xx 9、EZ_Clap 11、Denmark 13、Carthage 18、Sukuna 19、Leif Erikson 23）。房间 51 个真人里名字在名字池（740 个）里的正好是这 20 个，没有撞名的野人。",
        cardMismatch="card.json 的 squadBots=11、teamSplitCounts={1:2,2:5,3:3} 只数了有结果行的号；另外 9 个号（Barbary、bruh、Sukuna、Zenobia、CJ、Charlemagne、Swiss Guard、Mansa Musa、EZ_Clap）"
                     "日志在本地拍 900~1080 断掉、没有结果行。context.squad 按 HL-GAME-INIT 的 20 个 me 列。",
        labels="7 个号的日志标签和录像里的名字不同：Swiss Guard = Cao Cao、Denmark = Makima、Watermelon = Three Kingdoms、New York = CIA、Farnese = Tyrol、Carthage = Cascadia、Sukuna = Nelson"
               "（按玩家号对上：20 个号的每条 HL-TICK 和重演逐兵一致）。HL-DONATE 行里的 ally= 名字是录像里的名字。日志标签中途换名：Kandy>Erwin（L8585179）、xX_Shadow_Xx>Aragon（L8584212）。本文一律用第一个日志标签。",
        replayCoverage="录像到 t=1246：上报录像的是 xX_Shadow_Xx 的客户端，它的模拟停在 1246 拍；它的结果行 left 写在 00:19:01.135，按日志行序那时别的号已经记到 t=2790 的 HL-TICK（squadfog [HA]）。"
                       "t>1246 的 11040 拍没有全场真值：谁打了谁、停摆账号后来怎样，只能从日志间接推。",
        clock="结果行：Carthage t=2351 / 156 秒，Genos t=12286 / 713 秒 → 每拍 56.1 毫秒；New York 的 end 行比 Genos 晚 3.0 秒。",
        strategyVersion="squad20 = c110（归档 v27-team-c110.js）；出生点由各号客户端自己算（[HL-SPAWN] 101 行，没有后端协调器的行）。",
        fairSharePerCapita="51 个真人里编队 20 个（39.2%）；三队各 17 人，编队占 T1 的 5/17、T2 的 9/17、T3 的 6/17。",
        notes="t>1246 的时间线只合计『这一拍有 HL-TICK 的号』：t=1260 起是 9 个号，不是 20 个。停摆账号的地和兵在 t>1246 没有数据，没有补数。",
    ),
    outcomeExtra=dict(
        winnerHow="T2 获胜：Genos、New York 的结果行 end / won（t=12286，L8585193 / L8585202），当时全队领土 T2 491580 格（64.4%）、T1 264734 格（34.7%）、活着 9 人。"
                  "引擎源码里的胜利条件是领先的队拿下全部陆地（game.js victoryTick L1398-1412）；这一局在 64.4% 就结束，原因不在包里。",
        squadOnWinningTeam="T2 的 9 个编队账号：4 个停摆（Barbary、bruh、Charlemagne、Mansa Musa），Raiden t=5180、Goguryeo t=11162、Kandy t=12267 阵亡，Genos（12062 格，第 6 名）和 New York（7711 格，第 7 名）活到终局。"
                           "终局这两个号合计 19773 格，是 T2 领土的 4.0%（squadfog [HI]）。",
        squadOnLosingTeams="T1 的 5 个：Farnese t=164 阵亡，Swiss Guard、Zenobia、CJ 停摆，Watermelon t=6221 阵亡。T3 的 6 个：xX_Shadow_Xx 冻结后离开，EZ_Clap、Sukuna 停摆，Carthage t=2351、Denmark t=4907、Leif Erikson t=5173 阵亡。",
        survivors=dict(alive=2, of=20, withResultLine=11, died=8, left=1, noResultLine=9),
    ),
    phases=dict(
        spawn=dict(
            window="t=0~90",
            facts=[
                "日志出生指派 101 行，人均 5.0 条；最后一条指派被执行的 11 个号，引擎落点都在各自的日志指派里（spawncheck [PA][PC]）。最近编队友距离：中位 120 像素，最小 0。",
                "两对同像素：Farnese（T1，slot=11，L8583590）和 Genos（T2，slot=15，L8583587）都落在 (1874,98)；Carthage（slot=13，L8583609）和 Sukuna（slot=14，L8583598）都落在 (18,66)，同在 T3。"
                "Carthage / Sukuna 的最后一条指派又是同一个点 (1426,162)（L8583616 / L8583617），都没执行；Farnese 的最后一条 (1474,434)、Genos 的最后一条 (1266,482) 也没执行。Barbary（T2）和 Swiss Guard（T1）相距 49 像素。",
                "每个号自己排槽位：同一个点在 Farnese 那里是 11 号槽、在 Genos 那里是 15 号槽；早期的行 chosenSlots=12/8~16/8（要排 12~16 个槽，候选只有 8 个），后面是 /48。",
                "引擎的起始方块：Genos [1873,97]~[1876,100]，Farnese 被挤到 [1877,101]~[1880,104]，再往外 [1880,106]~[1883,109] 是 T2 的野人 Israel empire（resim.json startBox）。"
                "t=90 Farnese 12 格，接触边界 = 空地 7 格 + Israel empire 5 格（truth [TD]）。",
            ],
            problems=[
                "20 个号各算各的槽位，两对号算到同一个点；重解 3~9 次，9 个号停在不是最后一解的点上。",
                "Farnese 落在异队编队友 Genos 和 T2 野人之间，起始方块周围只剩 7 格空地。",
            ],
        ),
        opening=dict(
            window="t=90~630",
            facts=[
                "OPENING-CHECK @190：19 个号全 OK。影子（同版本策略按真值重跑）的 HL-OPENING 行和真机逐字相同（20 个号，shadowcmp [SA]）。执行拍 0~540 的指令时延中位 11~12 拍、P90 16~19（[SF]）。",
                "(270,630] 人均吃空地：编队 2478 格、其他真人 2402 格；人均吃人机 189 对 21 格（harvest）。t=630 编队 19 个号 57291 格（7.51%），人均 3015 格，其他真人人均 2838 格，比值 1.06（perhead [PH-A]）。",
                "Farnese：t=65 的第一手扩张（rings=7 spend=326/759，L8583641）和 Genos 的（332/759，L8583634）是同一张单子；Genos 的在 t=84 执行，Farnese 的在 t=91 执行，只拿到 5 格。"
                "Israel empire t=70 全仓打空地（801 兵），t=90 82 格；t=105 用 139 兵打 Farnese，拿走 8 格，Farnese 余额被打掉 693。Farnese t=112 用 52 兵（pct=193）回打，拿 17 格。"
                "t=126~161 Israel empire 余额为 0 时连发 5 条进攻（每条实发 0 兵），拿走 24 格；Farnese t=161 出局（结果行 t=164，L8583671，第 510 名，峰值 26 格）（resim.json cmdLog / pairLog）。",
            ],
            problems=[
                "Farnese 161 拍出局：T1 的编队账号从 5 个变成 4 个。",
            ],
        ),
        midgame=dict(
            window="t=630~6300",
            facts=[
                "卡顿波（录像实测，按执行拍）：540~719 时延中位 25 拍（P90 43）；720~899 中位 70 / P90 112，陆攻落地无效 11%；900~1079 中位 187 / P90 253 / 最大 583，无效 42%（67 条里 28 条）；"
                "1080~1259 中位 288 / P90 373 / 最大 687，无效 20%（shadowcmp [SF]）。20 个号无一例外（630~1260 各号中位 52~334 拍，[SB]）。",
                "成批落地：700~2100 编队 197 条指令里 121 条（61%）落在同一拍 ≥3 条的批里，其他真人 411 条里 0 条（bursts [BA]）。Kandy t=1204 一拍 9 条（决策拍 825~1175）、Swiss Guard t=1176 9 条、Zenobia t=1113 9 条、"
                "Mansa Musa t=1232 8 条（决策拍 545~1225）（[SB2]）。按下单时的比例、落地时的余额出兵：121 条本意 243858 兵，实发 559601 兵（2.29 倍，[SG]）。",
                "人机收割：(900,1246] 编队吃人机 21941 格（占 13%），人均 1155 格；其他真人 145406 格，人均 4847 格；每格花费 4.5 对 4.6 兵（harvest）。同期生效的陆攻：编队人均 2.1 条（900~1080）/ 2.9 条（1080~1240），"
                "其他真人 5.0 / 4.4 条（perhead [PH-B]）。t=1240 编队人均 6597 格 / 85119 兵，其他真人人均 12013 格 / 59554 兵，人均领土比 0.55。",
                "sb 互锁（影子按真值每 10 拍普查）：900~1260 贴着人机的 494 个号·点里 222 个全被挡，其中 212 个是 sb 挡的；定出 sb 的是同队编队友 53、异队编队友 95、敌队真人 60、同队真人 4；118 个是互锁；"
                "被挡的人机 137 个余额为 0。Sukuna 50 点全由 Carthage 定，Carthage 27 点由 Sukuna 定；New York 35 点由 Denmark 定，Denmark 34 点由 New York 定（[SH]）。",
                "停摆：9 个号的日志停在本地拍 900~1080，没有结果行；录像里它们最后一条已执行指令在服务器拍 1008~1232；xX_Shadow_Xx 冻在 1246 拍（squadfog [HA]）。t=1260 起有日志的只剩 9 个号。",
                "录像之后的相对落后（HL-TICK 行序，分辨率 90 拍）：Kandy、Denmark、New York、Carthage、Leif Erikson、Goguryeo 在本地拍 1440~1980 比领跑的号落后 180~360 拍，2070~2250 追平（lagorder [LA][LB]）。"
                "落后段里本地发出 191 条指令，余额只花掉 189841 兵（[LC]）；t<2300 的 50 笔捐款日志按余额序列拟合：成交 0、没成交 25、定不了 25（squadfog [HH]）。",
                "追平时积压一起落地：Kandy t=2070→2250 6236→11295 格（2160~2250 余额 464071→281264）；Leif Erikson t=2160→2610 8559→18206 格（2160~2250 余额 497112→202606）；"
                "Goguryeo t=1800 7284 格 / 434580 兵 → t=2340 17901 格 / 18162 兵（密度 1.0）→ t=2520 22480 格；New York t=2160~2340 余额 660108→23910、领土 5894 不变；"
                "Carthage 余额 313768（t=2160）→3471（t=2340）、领土 2603→1496，t=2351 出局（noeffect [NB]、logstats [QA]、squadfog [HG]）。",
                "T3 的三个在线号：Carthage t=2351、Denmark t=4907、Leif Erikson t=5173 出局；T3 全队 30.6%（t=2351）→ 14.2%（t=4907）→ 6.0%（t=5173）→ 1.9%（t=6221）。",
                "Watermelon（T1）：t=3060~6210 有 27 个快照窗两端都是 nb=0、neut=0，领土却掉了 15787 格；这些窗里新指令 8 条（船 4 条），陆攻 0 条（squadfog [HC]）。t=6221 出局。",
                "编队份额峰值 17.93%（t=4860，8 个号 136794 格，其中 Leif Erikson 56535 格）；t=5180 6 个号 83106 格（10.90%）；t=6221 5 个号 59998 格（7.87%）。",
            ],
            problems=[
                "20 个客户端从 t≈540 起一起变慢，10 个在 t≈1000~1250 停掉；录像期人均领土从其他真人的 1.06 倍掉到 0.55 倍。",
                "贴着余额为 0 的人机不出手：sb 被编队友的余额定住，两个号互相锁。",
                "落后的号每 20 拍照旧发一笔捐款，看不到上一笔已经在路上；追平时一起扣款。",
                "按名字保护：异队的编队账号停摆以后照样受保护，被它吃的号在 nb 里看不到它。",
            ],
        ),
        endgame=dict(
            window="t=6300~12286",
            facts=[
                "t=6300 起有日志的只剩 T2 的 4 个号（Kandy、New York、Goguryeo、Genos）。t=7200~9000 四个号合计 59230~59948 格、8372731~8590869 兵（密度 140~143），全部超过 100×，3~4 个被围（squadfog [HE]）。",
                "Kandy 和 Genos 在 t=6300~9360 一条指令没发（cmds 128、74 不变）；t=7380~9360 余额钉在 150×领土（2253900、1809300），被截掉的利息 296623 + 253509（logstats [QB]）。"
                "t=6300~9400 全队没有一条捐款日志（squadfog [HH]）。同期全队领土 T2 51.3%（t=6221）→ 56.1%（t=11162），T1 46.2% → 43.0%。",
                "t=9410 起四个号互相捐：t≥9400 收款方也是在线号的 52 笔里成交 22 笔，到账 4455518、税 2060516；其中 17 笔被收款方的 150 倍上限夹小，到账 2954371、税 1634432（[HH]）。"
                "例：Genos→New York t=9775 到账 5878、税 87126；t=9880 到账 4576、税 89594；Genos→Goguryeo t=10640 到账 23299、税 110494（L8585058）。",
                "Goguryeo：t=10710 24917 格 / 3689016 兵（密度 148.1，nb=1），之后 360 拍 cmds=191 不变，t=11070 8851 格 / 1138593 兵，t=11162 出局（结果行余额 700963）。"
                "t=10420~11150 队友对它发了 22 笔捐款，成交 11 笔，到账 2258461、税 902692，其中 9 笔被夹小（到账 1848862、税 780244）（squadfog [HJ]）。",
                "t=11120~11900 Kandy、Genos、New York 对停摆的 Mansa Musa 发了 16 笔，成交 13 笔，到账 2390307、税 800560（[HJ]）。Kandy t=11790 15026 格 / 1076594 兵，t=11880 起失地，t=12267 出局（余额 225870）。",
                "终局：T2 64.4%（491580 格）、T1 34.7%；编队剩 Genos 12062 格 / 743052 兵、New York 7711 格 / 596076 兵。",
            ],
            problems=[
                "被围的号的盈余只能捐给名字池里的同队账号：候选全都超过 132 密度或太平无战事时，四个号顶着硬上限空转 2000 拍。",
                "收款方密度一掉到 132 以下，三个号同一拍各捐 18%~27% 的余额过去，收款方只装得下几万兵，手续费照余额全额收。",
                "Goguryeo、Kandy 带着 369 万、108 万兵开始失地，失地窗里一条指令没有。",
            ],
        ),
    ),
    turningPoints=[
        dict(
            t0=0, t1=164, shareBefore=20, shareAfter=19, shareUnit="活着的编队账号数（T1 分支 5 → 4）",
            what="出生点各算各的，两对号落在同一个像素：Farnese（T1）和 Genos（T2）、Carthage 和 Sukuna（T3）。Farnese 被挤到 Genos 和 T2 野人 Israel empire 之间，161 拍出局；"
                 "Carthage / Sukuna 从此共用一片地，Carthage 到录像结束只有 2874 格，是 19 个号里最小的。",
            evidence=[
                "spawncheck [PB]：Tyrol(T1) 与 Genos(T2) 0 像素 (1874,98)；Cascadia(T3) 与 Nelson(T3) 0 像素 (18,66)。L8583587（Genos slot=15 rankIdx=18 chosenSlots=16/48）、L8583590（Farnese slot=11 rankIdx=8 chosenSlots=12/48）、"
                "L8583598 / L8583609（Sukuna slot=14、Carthage slot=13）。",
                "resim.json startBox：Genos [1873,97]~[1876,100]、Farnese [1877,101]~[1880,104]、Israel empire [1880,106]~[1883,109]。truth [TD] t=90：Farnese 12 格，接壤空地 7 格、Israel empire 5 格。",
                "resim.json cmdLog：同一张第一手单子（t=65 决策），Genos 的 t=84 执行，Farnese 的 t=91 执行；Israel empire t=70 全仓 801 兵打空地，t=90 已有 82 格。truth [TE]：Farnese 从空地只拿到 5 格。",
                "truth [TE]：Farnese 打出去 44 兵拿 22 格（空地 5、Israel empire 17）；被 Israel empire 拿走 32 格，对方只花 139 兵，自己余额被打掉 975。cmdLog：Israel empire t=126~161 的 5 条进攻实发 0 兵，pairLog 这段它拿走 24 格。",
                "L8583671：Farnese 结果行 died，第 510 名，峰值 26 格（录像里 t=161 出局）。",
                "perhead [PH-C] t=1230：Carthage 2874 格（包围盒 13,65~130,123），和 Sukuna 接壤 130 格；Sukuna 4818 格。",
            ],
            priorDecisions=[
                dict(t="<0", bot="Farnese / Genos", decision="各自的客户端排槽位，引擎落点是同一个像素 (1874,98)；之后各自又收到新指派 (1474,434) / (1266,482)，都没执行",
                     codePath=SPAWN, judgement="error", why="同一个点在 Farnese 的视图里是 11 号槽、在 Genos 的视图里是 15 号槽，没有全队一致的分配；异队的编队友受保护，谁也不会打谁，后到的号只能被挤走"),
                dict(t="<0", bot="Carthage / Sukuna", decision="同队的两个号落在同一个像素 (18,66)；最后一条指派又是同一个点 (1426,162)，都没执行",
                     codePath=SPAWN, judgement="error", why="两个号平分一片出生地，之后 620~1240 拍互相用对方的余额当 sb（见转折 ②）"),
                dict(t="65~112", bot="Farnese", decision="第一手扩张 t=65 决策、t=91 才执行，只拿到 5 格；t=90 决定用 pct=193 打余额只有 2 兵的 Israel empire，t=112 执行时自己余额只剩 277，实发 52 兵",
                     codePath=f"{C110}: Policy.act L4781-4944（开局 DP 扩张 → HL-OPENING；t=90 的陆攻走 Policy.buyLand L5250-5548）；{SIM}/game.js expandAttack L958-1057（新开进攻的第一圈必赢，余额为 0 也能拿地）",
                     judgement="unclear", why="两条指令各晚 26 / 22 拍；9~26 格的号扛不住对手每 7~14 拍一条的零兵进攻。决策本身（打一个没兵的邻居）没有问题"),
            ],
            statementType="observed",
        ),
        dict(
            t0=540, t1=1246, shareBefore=1.06, shareAfter=0.55, shareUnit="编队人均领土 ÷ 同房其他真人人均领土（真值；t=630 → t=1240）",
            what="20 个客户端一起变慢：指令时延中位 25 拍 → 288 拍，成批落地，四成落地无效；9 个号的日志在本地拍 900~1080 断掉，xX_Shadow_Xx 冻在 1246 拍。"
                 "这 700 拍正是全场分人机地的时候：其他真人人均吃掉 4847 格人机，编队 1155 格。",
            evidence=[
                "shadowcmp [SF]（执行拍 − 影子决策拍）：540~719 中位 25 / P90 43；720~899 70 / 112；900~1079 187 / 253 / 最大 583，陆攻 67 条里 28 条落地无效；1080~1259 288 / 373 / 最大 687。[SB]：20 个号 630~1260 的中位时延 52~334 拍，没有一个号例外。",
                "lagstats [LA]：影子在 900~1080 想发 168 条、录像里配上 26 条（15%）；1080~1260 想发 164 条、配上 7 条（4%）。",
                "bursts [BA]：700~2100 编队 197 条指令里 121 条（61%）落在同一拍 ≥3 条的批里；其他真人 411 条里 0 条。[SB2]：Kandy t=1204 一拍 9 条（决策拍 825~1175）、Swiss Guard t=1176 9 条、Zenobia t=1113 9 条、Mansa Musa t=1232 8 条（545~1225）。",
                "shadowcmp [SG]：时延 ≥35 拍、已生效的 121 条按下单时的比例和落地时的余额出兵，本意 243858 兵，实发 559601 兵（2.29 倍）。",
                "harvest (900,1246]：吃人机 167347 格，编队 21941 格（13%，人均 1155），其他真人 145406 格（人均 4847）。perhead [PH-B]：(900,1080] 生效的陆攻编队人均 2.1 条 / 9468 兵，其他真人 5.0 条 / 19341 兵。",
                "perhead [PH-A]：编队人均领土 3015 / 5296 / 5838 / 6597 格（t=630 / 900 / 1080 / 1240），其他真人 2838 / 5950 / 8873 / 12013 格；t=1240 编队人均余额 85119，其他真人 59554。",
                "shadowcmp [SH]：900~1260 贴着人机的 494 个号·点里 222 个全被挡，212 个是 sb；定 sb 的是编队友 148（同队 53、异队 95）、敌队真人 60、同队真人 4；互锁 118；被挡的人机余额为 0 的 137 个、吃光它所需 ≤ 自己余额 10% 的 206 个。",
                "squadfog [HA]：Barbary、Sukuna、bruh、Zenobia、CJ 最后一条 HL-TICK 在本地拍 900，Charlemagne、Swiss Guard、Mansa Musa 990，EZ_Clap 1080，都没有结果行；录像里它们最后一条已执行指令在 t=1008~1232。"
                "xX_Shadow_Xx 的结果行 left（L8584212，本地拍 1246）写在别的号 t=2790 的 HL-TICK 之间。",
                "squadfog [HM]：策略自己不慢——本地拍 540~1260 的 124 条 HL-TICK avgMs 最大 1.13 ms、maxMs 最大 13.9 ms，一拍是 56 ms。",
            ],
            priorDecisions=[
                dict(t="540~1246", bot="全部 20 个号", decision="不是策略决策：客户端落后服务器几十到几百拍，照常在旧局面上决策、按比例下单；驱动层没有时延检测",
                     codePath=DRIVER, judgement="unclear", why="策略单拍耗时 ≤1.13 ms（平均），慢在客户端 / 主机一侧，包里没有主机数据；同房其他真人没有成批落地的现象"),
                dict(t="900~1260", bot="Sukuna / Carthage / New York / Denmark / Zenobia / Mansa Musa / bruh 等", decision="贴着余额为 0 的人机不出手：打人机前的留底 sb 取了共用这个人机的另一个真人的余额，148 个号·点是编队友定的，118 个互锁",
                     codePath=SB, judgement="error", why="被挡的人机 137 个余额为 0、206 个吃光只要自己余额的 10% 以内；同一时间其他真人人均吃掉 4847 格人机"),
                dict(t="本地拍 900~1246", bot="Barbary / Sukuna / bruh / Zenobia / CJ / Charlemagne / Swiss Guard / Mansa Musa / EZ_Clap / xX_Shadow_Xx", decision="不是策略决策：客户端停止记日志、之后没有结果行（xX_Shadow_Xx 之后记了 left）",
                     codePath=DRIVER, judgement="unclear", why="10 个号在 350 拍里先后停掉，前面 400 拍全队时延一路变大；根因在主机侧"),
            ],
            statementType="observed",
        ),
        dict(
            t0=1440, t1=2351, shareBefore=3744475, shareAfter=2797338, shareUnit="9 个在线号的余额合计（t=2070 → t=2351；同期领土合计 71631 → 96718 格）",
            what="录像结束后还在线的 9 个号里 6 个仍比领跑的号落后 180~360 拍。落后时本地发的 191 条指令当时几乎没扣款，t=2070~2340 追平时一起落地："
                 "Kandy、Leif Erikson、Goguryeo 的旧陆攻换来 5000~15000 格；Carthage 和 New York 每 20 拍一笔的捐款成串扣款，余额掉到 1%~4%，Carthage 出局。",
            evidence=[
                "lagorder [LA][LB]：Kandy、Denmark、New York、Carthage、Leif Erikson、Goguryeo 在本地拍 1440~1980 落后 180~360 拍（Carthage 最多 360），本地拍 2070~2250 追平。[LC]：落后段里本地发出 191 条指令，段内余额实际只花掉 189841 兵。",
                "noeffect [NA]：桶 1620 的 57 条指令里 44 条没生效，桶 1890 的 68 条里 53 条没生效；桶 2160 花掉期初余额的 26.8%、领土 +24327 格。[ND]：整段零花费 3 段——Kandy 900~1350（20 条）、Carthage 1710~2070（34 条，其中捐款 16）、New York 1800~2160（22 条，其中捐款 16）。",
                "squadfog [HH]：发令拍 <2300 的 50 笔捐款日志，按余额序列拟合成交 0、没成交 25、定不了 25。发令的是 Carthage 24 笔、New York 18 笔、Kandy 4 笔、Goguryeo 4 笔；收款方 42 笔是停摆账号（Sukuna 9、xX_Shadow_Xx 7、EZ_Clap 6、bruh 17、Barbary 3）。",
                "squadfog [HG]：New York t=2160~2340 余额 660108→23910（比值 0.0362），领土 5894 不变；它最后 11 笔捐款（t=1990~2190）逐笔按 (pct+1+64)/1024 连乘正好是 0.0362。"
                "Carthage 313768→3471（0.0111），最后 19 笔连乘 0.0103。",
                "L8584060：第一笔救援捐款日志，Carthage t=1645 → Nelson（Sukuna），dAlly=11；squadfog [HL]：Sukuna 的读数 11→6（t=1645~1910），bruh 19→9（t=1850~2225）。",
                "Carthage：L8584153（t=2250，2603 格 / 332672 兵）→ L8584158（t=2340，1496 格 / 3471 兵）→ L8584164 结果行 died t=2351，第 47 名。",
                "noeffect [NB]：Kandy 2160~2250 花掉 52%（464071→281264，地 8842→11295），之前 20 条没生效；Leif Erikson 花掉 72%（497112→202606），之前 29 条；Goguryeo 2250~2340 151858→18162，地 8625→17901。",
            ],
            priorDecisions=[
                dict(t="1645~2260", bot="Carthage", decision="每 20 拍对停摆的 Sukuna / xX_Shadow_Xx / EZ_Clap 和 Leif Erikson 发一笔捐款，共 24 笔，pct 多数 155 / 153；发令时余额没有变化（326k→334k 照常涨），下一笔照发",
                     codePath=DON_FLOOR + "；" + DON_RESCUE, judgement="error",
                     why="冷却 18 拍远短于当时 180~360 拍的时延：每一笔都按『前面的还没发生』的余额算。19 笔叠在一起落地，余额只剩 1%（按连乘推断），2603 格的号以 2.3 的密度面对 2 个敌邻，11 拍后出局"),
                dict(t="1850~2190", bot="New York", decision="被围后每 20 拍对 bruh / Barbary / Raiden 发一笔，共 18 笔（pct 155 / 185 / 280）",
                     codePath=DON_FLOOR + "；" + DON_SURPLUS, judgement="error", why="同上；最后 11 笔一起落地，余额 660108→23910（密度 4.1）。它被围、没人能打它，才没有出局"),
                dict(t="1260~2250", bot="Kandy / Leif Erikson / Goguryeo", decision="落后时照常下陆攻单（三个号落后段里 109 条），追平时成批落地",
                     codePath=DRIVER + f"；{C110}: Policy.buyLand L5250-5548", judgement="unclear",
                     why="结果是三个号各多出 5000~15000 格（Goguryeo 7284→22480 格，花掉 76.7 万兵，每格 50.5 兵），但不是策略在当时局面下的决策，单子的比例是几百拍前定的"),
            ],
            statementType="inferred",
        ),
        dict(
            t0=2351, t1=6221, shareBefore=12.68, shareAfter=7.87, shareUnit="有日志的编队号合计占陆地 %（t=2351 是 9 个号 96718 格，t=6221 是 5 个号 59998 格；中间 t=4860 到过 17.93%）",
            what="T3 的 Denmark、Leif Erikson，T2 的 Raiden，T1 的 Watermelon 先后出局，T3 从 30.6% 掉到 1.9%。这一段全队成交的捐款有 70 笔进了停摆账号；"
                 "Watermelon 是被受保护名单里的号吃掉的——27 个快照窗两端都看不到对手，领土掉了 15787 格。",
            evidence=[
                "squadfog [HI]：全队领土 T1 / T2 / T3 = 40.4 / 28.0 / 30.6%（t=2351）→ 38.0 / 46.3 / 14.2%（t=4907）→ 41.6 / 50.9 / 6.0%（t=5173）→ 46.2 / 51.3 / 1.9%（t=6221）。T2 在线的 5 个编队号 61608→66463 格（t=2351→4907），全队 213719→353107 格。",
                "squadfog [HB]：收款方是停摆账号的捐款 126 笔，成交 70 笔，到账 8833877（全部到账的 49%），税 4193699。[HL]：救援日志里停摆账号的密度 65 条读数，最小 1 / 中位 14 / 最大 59；一直在线的号 t≥1800 的 593 条 HL-TICK 密度中位 75。",
                "squadfog [HC]：Watermelon 两端都被围（nb=0、neut=0）的 39 个窗里 27 个在掉地，合计 15787 格（t=3060~6210，单窗最多 2642 格）；这些窗里新指令 8 条、其中船 4 条，陆攻 0 条。L8584603（t=5310，14995 格 / 726849 兵）→ L8584687（t=6210，2915 格 / 132859 兵），cmds=71 不变。",
                "squadfog [HJ][HF]：Mansa Musa 的收款段 t=3000~3320（3 笔 356938）、t=4330~6195（15 笔 2240535），之后到 t=11120 没有一笔；Watermelon 出局在 t=6221。perhead [PH-C] t=1230：Watermelon 贴着 Zenobia（T1 停摆，143 格）和 Kandy（T2，65 格），Zenobia 贴着 Mansa Musa（T2 停摆，41 格）。",
                "Denmark：squadfog [HN] t=2340~4140 的 20 个窗 nb=1，17 个窗各掉一口（92 94 96 … 116 117，共 1783 格），窗首密度 61~80，陆攻和船 0 条；13 笔救援捐款给 xX_Shadow_Xx / EZ_Clap，到账 798709、税 680335（[HJ]）。t=4590 9802 格 → t=4860 3202 格，cmds=60 不变（L8584469、L8584508）。",
                "Leif Erikson：t=3690~4410 nb=1、cmds=140 不变，余额 614270→2076690；t=4410~4590 发了 7 条指令，18799→56535 格（t=4860）；t=4950 56133 格 / 1753686 兵 → t=5130 16495 格 / 413831 兵，cmds=148 不变（L8584525、L8584563）。",
                "Raiden：t=3870 19794 格 / 2222743 兵；t=3870~4595 6 笔捐款（对 Barbary、Charlemagne、New York、Mansa Musa），成交的 3 笔到账 609893、税 392543；t=4230~4860 19794→10789 格。t=4500~5110 收到 10 笔 1812082（[HJ]），t=5180 出局时余额 499193。",
                "squadfog [HK]：出局前最后一次领土 ÷ 峰值 = Denmark 0.204、Leif Erikson 0.241、Raiden 0.201、Watermelon 0.194；出局时余额 51346 / 327612 / 499193 / 124109。",
            ],
            priorDecisions=[
                dict(t="2530~3950", bot="Denmark", decision="唯一的邻居每 90 拍啃走约 100 格，1800 拍没有一条陆攻；密度一到 78 就对停摆的 xX_Shadow_Xx / EZ_Clap 发救援捐款（pct 59~111），13 笔付出 1479044 兵，一半是税",
                     codePath=DON_FLOOR + "；" + DON_RESCUE + f"；{SB}", judgement="error",
                     why="捐款线（密度 77.6）低于 t≥1500 打人机的留底线（88×领土）：兵攒不到能出手的密度就被捐走；收款方是没人在控制的账号（密度读数 5~38）。"
                         "邻居是谁没有录像；17 口 / 1800 拍、每口比上一口多 2 格，和引擎里内置 AI 每 100 拍出手一次、新进攻第一圈必赢的规则对得上（推断）"),
                dict(t="3870~4595", bot="Raiden", decision="密度 112、有 4 个敌邻时把盈余捐给停摆的 Barbary（pct 153），之后一边丢地一边发 5 笔 pct 59~73 的救援捐款",
                     codePath=DON_SURPLUS + "；" + DON_RESCUE, judgement="error", why="成交的 3 笔付出 1002436 兵，到账 609893；同一段自己从 19794 格掉到 10789 格，没有一条反击"),
                dict(t="3060~6210", bot="Watermelon", decision="27 个窗里对手不在 nb 里：没有反击、没有买地；期间还对停摆的同队 Swiss Guard 捐了 4 笔（到账 362344、税 179348），只靠船换地",
                     codePath=ANALYZE + f"；{C110}: counterAttack L871-887（只遍历 nb，且跳过 g.isBot）；tryDonateToTeammate L4376-4379（自己挨打只数 !g.isBot 的进攻者）",
                     judgement="error", why="对手是名字池里的异队账号：按名字受保护，不进 nb；它由引擎托管以后照样出兵。号的三条防线（反击、买地、挨打时停捐）都以 nb / 真人进攻者为前提"),
                dict(t="3000~6195", bot="Kandy / Genos / New York / Goguryeo", decision="被围后把盈余捐给同队停摆的 Mansa Musa：18 笔成交，到账 2597473、税 881359",
                     codePath=DON_SURPLUS, judgement="error", why="收款条件只看活着、同队、名字在名字池里；Mansa Musa 的日志早在本地拍 990 就停了。它拿到兵的这段时间正是 Watermelon 看不见地失地的时间（推断）"),
                dict(t="4950~5130", bot="Leif Erikson", decision="56133 格 / 175 万兵，180 拍丢 39638 格，一条指令没有",
                     codePath=BUY + f"；{C110}: counterAttack L871-887", judgement="error", why="密度 31 的大地盘刚由 7 条指令从 19220 格撑到 56535 格；对手是谁、余额多少没有录像，留底高于余额是按代码推的"),
            ],
            statementType="inferred",
        ),
        dict(
            t0=6300, t1=9410, shareBefore=7.74, shareAfter=7.86, shareUnit="有日志的 4 个号（都在 T2）合计占陆地 %（t=7020 → t=9000）；同期合计余额 8251351 → 8590869",
            what="T2 的 4 个在线号被自己的队友和受保护的号围在里面，合计 6 万格、840~860 万兵，密度 140 以上。3100 拍里全队没有一笔捐款；Kandy 和 Genos 一条指令没发，余额钉在引擎的 150 倍硬上限。"
                 "同期 T2 对 T1 是 51.3% 对 46.2%，胜负未分。",
            evidence=[
                "squadfog [HE]：T2 在线 4 个号 t=7200 59230 格 / 8374997 兵（密度 141.4），t=8100 59694 格 / 8372731 兵，t=9000 59948 格 / 8590869 兵；4 个都超过 100×，3~4 个被围。",
                "logstats [QB]：余额 ≥149.5×领土 的快照 Genos 24 条（t=7380~9450）、Kandy 23 条（t=7380~9360）、New York 9 条（t=6300~9900）；被截掉的利息 253509 + 296623 + 32857。L8584760 / L8584917：Kandy t=7380 和 t=9360 都是 15026 格 / 2249359、2253900 兵，cmds=128。",
                "squadfog [HH]：发令拍 6300~9400 的捐款日志 0 笔。logstats [QG]：Genos t=2250~12240 的 40 条指令全是捐款，陆攻 0、船 0；Kandy t=6300 之后没有陆攻也没有船。",
                "digest [J]：被围（nb=0、neut=0）的快照 Kandy 102 / 129、Genos 111 / 132、New York 77 / 130、Goguryeo 62 / 110。",
                "squadfog [HI]：全队领土 T1 / T2 = 46.2 / 51.3%（t=6221）→ 43.0 / 56.1%（t=11162）；T2 在线的编队号占 T2 领土的 14.6% → 8.0%。",
                "logstats [QE]：这一段还在动的是船——整局 Goguryeo 纯船窗 50 条船少掉 4588400 兵、窗内领土 +169 格；New York 33 条 / 929895 兵 / −826 格；Kandy 20 条 / 1025190 兵 / +664 格。",
            ],
            priorDecisions=[
                dict(t="6300~9410", bot="Kandy / Genos / New York / Goguryeo", decision="盈余捐款找不到收款方：候选只有同队名字池里的号，四个在线号彼此密度都 ≥132 或没有战事，停摆的 Mansa Musa 这一段也没有战事；同队的野人不在候选里",
                     codePath=DON_SURPLUS, judgement="error", why="840 万兵停了 3100 拍，Kandy / Genos 被硬上限截掉利息 55 万；同期 T2 的地是野人队友在前线打下来的"),
                dict(t="2070~12286", bot="Genos", decision="12062 格被围 10200 拍，一条船没发",
                     codePath=BOAT, judgement="unclear", why="被围时闲置船分支每 60 拍会找一次落点；Genos 一次没成，是没有落点还是别的门槛，没有录像和影子追踪到这一段"),
                dict(t="2250~11070", bot="Goguryeo / New York", decision="被围时每 60 拍一条闲置船，不设价格上限：Goguryeo 纯船窗 50 条船少掉 458.8 万兵换 +169 格（之后 180 拍内最高 +2470 格），New York 33 条少掉 93.0 万兵、领土反而 −826 格",
                     codePath=BOAT, judgement="error", why="每条船先付余额的 32/1024 手续费；落点是几格小岛或很快被拿回去的滩头。船落在谁身上没有录像"),
            ],
            statementType="observed",
        ),
        dict(
            t0=9410, t1=12286, shareBefore=7.90, shareAfter=2.59, shareUnit="有日志的编队号合计占陆地 %（t=9990 4 个号 60230 格 → 终局 Genos + New York 19773 格）",
            what="四个号里一有谁的密度掉到 132 以下，另外三个同一拍各捐 18%~27% 的余额过去，收款方离 150 倍上限只差几万兵，手续费照捐出方余额全额收。"
                 "Goguryeo 被这样补到密度 148 时开始挨打，360 拍丢 16066 格、一条指令没有，t=11162 带着 70 万兵出局；Kandy 接着把 148 万兵捐给停摆的 Mansa Musa，t=12267 出局，离终局 19 拍。",
            evidence=[
                "squadfog [HH]：发令拍 ≥9400、收款方也是在线号的 52 笔，成交 22、没成交 21、定不了 9；到账 4455518、税 2060516；其中 17 笔被收款方的 150 倍上限夹小，到账 2954371、税 1634432。同一拍 ≥2 个号捐同一人 30 组 75 笔。",
                "L8585056~8585058：t=10640 Kandy、New York、Genos 同一拍捐给 Goguryeo，到账 375039 / 254351 / 23299，税 109163 / 57930 / 110494。Genos→New York t=9775 到账 5878、税 87126，t=9880 到账 4576、税 89594（out/B019/donfit.json）。",
                "Goguryeo：L8585051（t=10620，26221 格 / 3362456 兵，nb=0）→ L8585062（t=10710，24917 格 / 3689016 兵，密度 148.1，nb=1）→ L8585109（t=11070，8851 格 / 1138593 兵），cmds=191 不变 → L8585124 结果行 t=11162，余额 700963。",
                "squadfog [HJ]：Goguryeo t=10420~11150 收款段 22 笔，成交 11，到账 2258461、税 902692，9 笔被夹小。Mansa Musa t=11120~11900 收款段 16 笔，成交 13，到账 2390307、税 800560（Kandy 6 笔、Genos 4 笔、New York 3 笔）。",
                "Kandy：t=11130 余额 2046113（密度 136）→ t=11130~11900 对 Mansa Musa 6 笔，到账 1477118、税 486345 → L8585166（t=11790，15026 格 / 1076594 兵）→ L8585189（t=12240，4941 格 / 332087 兵，cmds 150→151）→ L8585192 结果行 t=12267，余额 225870。",
                "L8585177：Kandy t=11900 对 Mansa Musa 的救援捐款 pct=61，到账 63075、税 65110，dAlly=15。",
                "squadfog [HI]：T2 的全队领土 56.1%（t=11162）→ 63.9%（t=12267）→ 64.4%（终局）；T2 在线编队号 34222 格（8.0%）→ 19773 格（4.0%）。",
            ],
            priorDecisions=[
                dict(t="9410~11150", bot="Kandy / Genos / New York", decision="按固定比例（pct 280 / 185 / 153）给密度 <132 的在线队友捐款，不看对方还装得下多少；三个号同一拍各发一笔",
                     codePath=DON_SURPLUS + "；" + ENG_DON, judgement="error", why="t≥9400 在线号之间成交的 22 笔里 17 笔被夹小：到账 2954371，税 1634432；另有 21 笔因为对方已经顶满整单不成交"),
                dict(t="10710~11070", bot="Goguryeo", decision="24917 格 / 369 万兵（密度 148）、1 个敌邻，360 拍丢 16066 格，一条指令没有",
                     codePath=BUY + f"；{C110}: counterAttack L871-887（出兵 = min(余额 − 留底, counterK×净进攻兵)，不够就不发）", judgement="error",
                     why="按代码，对真人的留底由最富的真人邻居的余额定；对手的余额没有录像，留底高于 369 万是推断。结果是余额随地一起被打掉，领土到峰值的 23% 时按引擎规则出局，剩下的 70 万兵清零"),
                dict(t="11130~11900", bot="Kandy", decision="Goguryeo 出局前后，把 6 笔、连税 1963463 兵捐给停摆的 Mansa Musa，自己的密度从 136 降到 72",
                     codePath=DON_SURPLUS + "；" + DON_RESCUE, judgement="error", why="收款方是没人控制的账号（最后一笔的 dAlly=15）；Kandy t=11880 起挨打，t=11790~12240 丢 10085 格，这段只有 1 条指令，就是 t=11900 那笔救援捐款（到账 63075、税 65110）"),
            ],
            statementType="observed",
        ),
    ],
    deathNotes={
        "Farnese": dict(
            cause="出生点和异队编队友 Genos 是同一个像素，被挤到 Genos 和 T2 野人 Israel empire 之间，起始方块周围只剩 7 格空地；第一手扩张晚 26 拍执行，只拿到 5 格。"
                  "Israel empire 用 139 兵加 5 条零兵进攻拿走 32 格，t=161 领土不到峰值（26 格）的 1/4，出局。",
            chain=["出生 (1874,98)，与 Genos 同像素；起始方块被挤到 [1877,101]~[1880,104]", "t=70 Israel empire 全仓 801 兵扩张，t=90 82 格", "t=91 第一手扩张执行（决策拍 65），空地只拿到 5 格",
                   "t=105 Israel empire 139 兵打来，丢 8 格", "t=112 回打 52 兵（决策拍 90，当时余额 922；落地时 277），拿 17 格，峰值 26 格（t=130）",
                   "t=126~161 Israel empire 5 条零兵进攻，丢 24 格", "t=161 出局（结果行 t=164，第 510 名）"],
            statementType="observed"),
        "Carthage": dict(
            cause="和同队的 Sukuna 同像素出生，地盘只有 2600~3300 格；录像期被 Sukuna 的余额锁住不打人机（42 个号·点）；客户端落后 180~360 拍时每 20 拍发一笔捐款，"
                  "24 笔里的 19 笔叠在一起落地（按连乘推断），余额 313768→3471；密度 2.3、2 个敌邻，11 拍后出局。",
            chain=["出生 (18,66) 与 Sukuna 同像素；t=1230 2874 格，19 个号里最小", "t=620~1240 sb 被 Sukuna（27 点）和 T1 的 Kobal（15 点）的余额定住，贴着 0 兵的人机不出手",
                   "t=1080~2250 本地发出 82 条指令，t=1530~2070 领土 2694 格不变、余额 179086→356958", "t=1645~2260 24 笔捐款日志：Sukuna 9、xX_Shadow_Xx 7、EZ_Clap 6、Leif Erikson 2",
                   "t=2250 2603 格 / 332672 兵 → t=2340 1496 格 / 3471 兵", "t=2351 出局（第 47 名；结果行的峰值 4502 格出现在两条快照之间）"],
            statementType="inferred"),
        "Denmark": dict(
            cause="1800 拍里被唯一的邻居一口一口啃掉 1783 格，从不还手：密度一到 78 就把兵捐给停摆的 xX_Shadow_Xx / EZ_Clap（13 笔，到账 798709、税 680335），攒不到打人机要的 88 倍留底。"
                  "t=4320~4590 被围，又给 Leif Erikson 捐了 4 笔 510002；t=4590 新邻居出现，270 拍丢 6600 格，一条指令没有。",
            chain=["t=2160~2250 积压的旧单子落地：余额 648972→420256，领土不涨（下一窗回流 217222）", "t=2340~4140 nb=1，17 口共 1783 格（11360→9577）；陆攻 0，救援捐款 13 笔",
                   "t=4230 邻居消失（neut=30），t=4320 9802 格被围", "t=4285~4580 对 Leif Erikson 捐 5 笔，成交 4 笔 510002（税 178272）",
                   "t=4590 9802 格 / 613659 兵 → t=4680 8699 → t=4770 7586 → t=4860 3202 格 / 83367 兵，cmds=60 不变", "t=4907 出局（第 25 名），余额 51346"],
            statementType="inferred"),
        "Leif Erikson": dict(
            cause="t=2700~3510 被围在 18209 格；t=3690~4410 只有 1 个敌邻，720 拍一条指令没有，余额 61 万→208 万（密度 110）；t=4410~4590 的 7 条指令把领土从 18799 撑到 56535 格（密度 30）。"
                  "t=4950 起 180 拍丢 39638 格，一条指令没有；领土掉到峰值 58598 的 1/4 以下出局，带走 327612 兵。HL-ASSIST 记下的进攻者是 T1 的 Plant。",
            chain=["t=2160~2610 积压的旧单子落地：8559→18206 格", "t=2700~3510 被围（18209 格）；t=2610~3690 发了 10 条船，纯船窗里领土 +593 格", "t=3690~4410 nb=1、cmds=140 不变，余额 614270→2076690",
                   "t=4285~4580 收到 Denmark 4 笔 510002", "t=4410~4500 余额 2076690→1401446；t=4410~4590 共 7 条指令；t=4860 56535 格 / 1700053 兵（nb=3，neut=49）",
                   "t=4950 56133 格 / 1753686 兵 → t=5040 34162 → t=5130 16495 格 / 413831 兵，cmds=148 不变", "t=5173 出局（第 23 名），最后一次领土 14151 格，余额 327612"],
            statementType="observed"),
        "Raiden": dict(
            cause="t=3870 有 19794 格 / 222 万兵（密度 112）、4 个敌邻，把盈余捐给停摆的 Barbary，之后一边丢地一边发救援捐款；t=4230~4860 丢 9005 格，没有一条打向吃它的人。"
                  "队友在它最后 700 拍里捐来 181 万；t=5180 领土到峰值的 20% 出局，带走 499193 兵。",
            chain=["t=2250~3150 有 3~5 个敌邻，900 拍没有陆攻也没有船", "t=3780~3870 19794 格，余额 1996009→2222743", "t=3870~4080 对 Barbary / Charlemagne 成交 3 笔，到账 609893、税 392543",
                   "t=4230 18271 格 → t=4590 11613 格 → t=4860 10789 格", "t=4500~5110 收到 19 笔日志、成交 10 笔 1812082（Genos 5、New York 3、Goguryeo 2）",
                   "t=4935 / 4960 两次 10% 戳刺打 Plant（替 T3 的 Leif Erikson），估计出兵 225961", "t=5040 10703 格 / 1043918 兵 → t=5180 出局（第 23 名），余额 499193"],
            statementType="observed"),
        "Watermelon": dict(
            cause="T1 分支只剩它一个在线号。t=2160 起四周只有同队的停摆账号和受保护的异队编队账号（nb=0）；t=3060 起被一个不在 nb 里的号吃，27 个窗掉 15787 格。"
                  "对手不在 nb 里，它没有反击，只靠船换回地（两次 +4132 / +4825 格），还把 36 万兵捐给了停摆的 Swiss Guard。t=5310~6210 14995→2915 格，一条指令没有，出局时带走 124109 兵。"
                  "推断吃它的是同样停摆、由引擎托管的 T2 账号 Mansa Musa。",
            chain=["t=2160 nb=0（t=1230 时贴着 Zenobia 143 格、Kandy 65 格），之后 39 个窗两端都被围", "t=3060~3870 9745→8248 格，陆攻 0；t=3140~3640 对 Swiss Guard 捐 4 笔 362344（税 179348）",
                   "t=4050~4410 5 条船，7936→12068 格", "t=4500~5130 11744→10170 格", "t=5130~5310 2 条船，10170→14995 格",
                   "t=5310~6210 14995→2915 格（单窗最多 2642 格），cmds=71 不变，余额 726849→132859", "t=6221 出局（第 17 名），余额 124109；t=6210~6300 Kandy（T2）用 2 条指令多出 1266 格"],
            statementType="inferred"),
        "Goguryeo": dict(
            cause="T2 分支最大的号（峰值 26239 格）。被围的 7000 拍里兵花在 61 条船上；t=9410 起四个号互相捐，它被补到密度 148（硬上限）。t=10710 出现 1 个敌邻，360 拍丢 16066 格、余额 369 万→114 万，一条指令没有；"
                  "领土到峰值的 23% 出局，带走 700963 兵。",
            chain=["t=1800~2520 积压的旧单子落地：7284→22480 格，余额 434580→18162（t=2340）", "t=3510~10620 领土 23905→26221 格，余额 931181→3362456；整局 66 条船",
                   "t=3990~4370 5 笔 pct 57~83 的救援捐款（Charlemagne / Barbary / New York），每笔到账 10.7~14.7 万、税 11.2~12.5 万", "t=10420~11150 队友对它 22 笔、成交 11 笔 2258461（9 笔被夹小）",
                   "t=10710 24917 格 / 3689016 兵（密度 148.1），nb=1 → t=10800 20786 → t=10890 17629 → t=10980 12997 → t=11070 8851 格 / 1138593 兵，cmds=191 不变",
                   "t=11162 出局（第 12 名），最后一次领土 6047 格，余额 700963"],
            statementType="observed"),
        "Kandy": dict(
            cause="t=2340 起被围在 11295~15026 格，t=6300 以后没有陆攻也没有船，t=7380~9360 余额钉在硬上限 225 万。t=11130~11900 把 6 笔、连税 196 万兵捐给停摆的 Mansa Musa，密度从 136 降到 72；"
                  "t=11880 出现 1 个敌邻，t=11790~12240 丢 10085 格，唯一的一条指令还是救援捐款。t=12267 出局，离终局 19 拍，带走 225870 兵。",
            chain=["t=2070~2250 积压的旧单子落地：6236→11295 格，之后被围", "整局 20 条船（18 条是被围时发的），纯船窗里少掉 1025190 兵、领土 +664 格；t=6210~6300 用 2 条指令多出 1266 格（到 15026 格），正是 Watermelon 出局的时候",
                   "t=6300~9360 cmds=128 不变，余额 1134617→2253900（150×）", "t=9410~10640 对 Goguryeo / New York 成交 7 笔，到账 2189178、税 821827",
                   "t=11130~11900 对 Mansa Musa 成交 6 笔，到账 1477118、税 486345", "t=11790 15026 格 / 1076594 兵 → t=11880 13393（nb=1）→ t=12150 9261 → t=12240 4941 格 / 332087 兵",
                   "t=12267 出局（第 10 名），最后一次领土 3861 格，余额 225870"],
            statementType="observed"),
        "xX_Shadow_Xx": dict(
            cause="不是阵亡：客户端冻在本地拍 1246（4963 格 / 92819 兵；录像就是它上报的），结果行 left 写在别的号 t=2790 的时候。t=1810~3950 Carthage / Denmark 对它发了 16 笔救援捐款，成交 9 笔 587249（税 474475）；"
                  "救援日志里它的密度 57（t=1810）→ 5（t=3950）。之后的下落不明。",
            chain=["本地拍 1170 最后一条 HL-TICK（4963 格 / 69864 兵，4 个敌邻：T1 的 Princeso、Akt21 和 2 个人机）", "本地拍 1246 冻结", "≈t=2790 结果行 left（第 43 名，当时活着 221 人）"],
            statementType="observed"),
        "Mansa Musa": dict(
            cause="没有阵亡记录：日志停在本地拍 990（7900 格 / 32584 兵），录像里最后一条已执行指令 t=1232（一拍 8 条），录像末拍 9641 格 / 104899 兵。"
                  "t=3000~11900 队友对它成交 31 笔捐款 4987780（税 1681919），全队收得最多；t=11900 还活着，密度 15。推断：吃掉 Watermelon 的是它。",
            chain=["本地拍 990 日志断", "t=3000~3320 收 3 笔 356938", "t=4330~6195 收 15 笔 2240535", "t=11120~11900 收 13 笔 2390307"], statementType="inferred"),
        "Barbary": dict(cause="没有阵亡记录：日志停在本地拍 900（5041 格 / 22420 兵），最后一条已执行指令 t=1057，录像末拍 7247 格 / 91328 兵。t=3090~4230 队友对它成交 12 笔 1613088（税 978142），救援日志里密度 29~59。之后没有读数。",
                        chain=["本地拍 900 日志断", "t=3090~4230 收 12 笔 1613088"], statementType="observed"),
        "Charlemagne": dict(cause="没有阵亡记录：日志停在本地拍 990（6373 格 / 39830 兵），最后一条已执行指令 t=1176，录像末拍 6386 格 / 120770 兵。t=3220~5925 收到 10 笔 1071956（税 673955），密度读数 8~34，t=5905 是 1。之后没有读数。",
                            chain=["本地拍 990 日志断", "t=3220~4305 收 9 笔 936341", "t=5905 收 1 笔 135615，dAlly=1"], statementType="observed"),
        "bruh": dict(cause="没有阵亡记录：日志停在本地拍 900（3504 格 / 26471 兵），最后一条已执行指令 t=1008，录像末拍 4886 格 / 70280 兵。t=1850~2225 New York / Kandy / Goguryeo 对它发了 17 笔捐款（窗内成交 0），密度读数 19→9。之后没有读数。",
                     chain=["本地拍 900 日志断", "t=1850~2225 17 笔捐款日志"], statementType="observed"),
        "Swiss Guard": dict(cause="没有阵亡记录：日志停在本地拍 990（6692 格 / 38550 兵），最后一条已执行指令 t=1211，录像末拍 8216 格 / 23478 兵。t=3140~3640 Watermelon 对它成交 4 笔 362344（税 179348），密度读数 16。之后没有读数。",
                            chain=["本地拍 990 日志断", "t=3140~3640 收 4 笔 362344"], statementType="observed"),
        "Zenobia": dict(cause="没有阵亡记录：日志停在本地拍 900（4121 格 / 30248 兵），最后一条已执行指令 t=1141，录像末拍 4970 格 / 96858 兵，夹在同队的 Watermelon 和 T2 的 Mansa Musa 之间。没有人给它捐款，之后没有任何读数。",
                        chain=["本地拍 900 日志断"], statementType="observed"),
        "CJ": dict(cause="没有阵亡记录：日志停在本地拍 900（4624 格 / 28123 兵），最后一条已执行指令 t=1022，录像末拍 4975 格 / 104989 兵，只贴着一个人机。之后没有任何读数。",
                   chain=["本地拍 900 日志断"], statementType="observed"),
        "Sukuna": dict(cause="没有阵亡记录：日志停在本地拍 900（2736 格 / 21702 兵），最后一条已执行指令 t=1134（一拍 5 条），录像末拍 4818 格 / 57160 兵。t=1645~1910 Carthage 对它发了 9 笔救援捐款，日志里它的密度 11→6。之后没有读数。",
                       chain=["本地拍 900 日志断", "t=1645~1910 9 笔救援捐款日志，dAlly 11→6"], statementType="observed"),
        "EZ_Clap": dict(cause="没有阵亡记录：日志停在本地拍 1080（7881 格 / 55389 兵），最后一条已执行指令 t=1015，录像末拍 8777 格 / 117615 兵。t=3160~3490 Denmark 对它成交 4 笔 211460（税 205860），密度读数 9~10。之后没有读数。",
                        chain=["本地拍 1080 日志断", "t=3160~3490 收 4 笔 211460"], statementType="observed"),
    },
    decisions=[
        dict(id="D01", t="<0", bot="Farnese（T1）/ Genos（T2）", decision="两个号各自排槽位，引擎落点是同一个像素 (1874,98)；Farnese 的起始方块被挤到 Genos 和 T2 野人之间，161 拍出局。",
             codePath=SPAWN, verdict="error", patternId="NEW-SP-04",
             evidence=["spawncheck [PB]：Tyrol(T1) 与 Genos(T2) 0 像素", "L8583587 / L8583590：同一个点，Genos 记 slot=15 rankIdx=18，Farnese 记 slot=11 rankIdx=8", "resim.json startBox；truth [TD] t=90 Farnese 接壤空地 7 格、Israel empire 5 格；L8583671 结果行"],
             statementType="observed"),
        dict(id="D02", t="<0", bot="Carthage / Sukuna（T3）等 9 个号", decision="每个号在自己的视图里排槽位、重解 3~9 次：Carthage 和 Sukuna 落在同一个像素 (18,66)，最后一条指派又是同一个点；20 个号里 9 个没有停在最后一解上。",
             codePath=SPAWN, verdict="error", patternId="NEW-SP-07",
             evidence=["spawncheck [PA][PC]：指派 101 行、人均 5.0 条，最后一条被执行的 11 个；最后一条指派相同的号对 1", "L8583598 / L8583609 / L8583616 / L8583617；早期行 chosenSlots=12/8~16/8",
                       "perhead [PH-C] t=1230：Carthage 2874 格、Sukuna 4818 格，互相接壤 130 格"],
             statementType="observed"),
        dict(id="D03", t="65~630", bot="19 个号", decision="开局 DP 扩张按期出手：t=190 检查全 OK；(270,630] 人均吃空地 2478 格（其他真人 2402）、人机 189 格（其他真人 21）；t=630 人均领土是其他真人的 1.06 倍。",
             codePath=f"{C110}: Policy.act L4781-4944（开局 DP 周期出手，HL-OPENING）", verdict="good", patternId="NEW-OP-G1",
             evidence=["L8583695：OPENING-CHECK 20 bots @ tick 190 全部 OK", "shadowcmp [SA]：20 个号的 HL-OPENING 行影子逐字相同；[SF] 执行拍 0~540 时延中位 11~12 拍", "harvest (270,630]；perhead [PH-A] t=630：3015 对 2838 格"],
             statementType="observed"),
        dict(id="D04", t="630~900", bot="19 个号", decision="卡顿还轻的时候吃人机：人均 605 格（其他真人 531），每格 3.3 兵（其他真人 4.3）。",
             codePath=f"{C110}: Policy.buyLand L5250-5548 → botOk L2499-2505 / winFloor L4542-4550（价位门槛过了才打人机）", verdict="good", patternId="NEW-AT-G1",
             evidence=["harvest (630,900]：吃人机 27406 格，编队 11488 格（42%）", "shadowcmp [SH] 630~900：435 个号·点里 153 个至少一个人机过门槛", "perhead [PH-B] (630,900]：生效的陆攻编队人均 4.4 条 / 9340 兵，其他真人 6.3 条 / 10239 兵"],
             statementType="observed"),
        dict(id="D05", t="900~1260", bot="Sukuna / Carthage / New York / Denmark / Zenobia / Mansa Musa / bruh / Goguryeo / xX_Shadow_Xx 等", decision="贴着余额为 0 的人机不出手：打人机前的留底 sb 取了共用这个人机的另一个真人的余额。212 个号·点被 sb 挡，148 个是编队友定的，118 个是两个号互锁。",
             codePath=SB, verdict="error", patternId="NEW-EC-05",
             evidence=["shadowcmp [SH] 900~1260：494 个号·点、222 个全被挡（floor:sb 124、minShare(floor:sb) 88）", "定 sb 的：同队编队友 53、异队编队友 95、敌队真人 60、同队真人 4；被挡的人机 137 个余额为 0、206 个吃光只要自己余额 ≤10%",
                       "逐号：Sukuna 50 点全由 Carthage 定；Carthage 42 点（Sukuna 27、Kobal 15）；New York 35 点由 Denmark 定、Denmark 34 点由 New York 定；Zenobia 10 点由 Mansa Musa 定、Mansa Musa 10 点由 Zenobia 定"],
             statementType="observed"),
        dict(id="D06", t="900~1246", bot="19 个号", decision="分人机地的 350 拍里，编队人均吃到 1155 格，其他真人 4847 格；人均领土从其他真人的 0.89 倍掉到 0.55 倍，人均余额却是 1.43 倍（85119 对 59554）。",
             codePath=SB + f"；{DRIVER}", verdict="error", patternId="NEW-EC-06",
             evidence=["harvest (900,1246]：吃人机 167347 格，编队 21941 格（13%）", "perhead [PH-A]：t=900 5296 对 5950 格，t=1240 6597 对 12013 格", "perhead [PH-B]：(900,1080] 已执行 67 条、生效 39 条；(1080,1240] 70 条、生效 56 条；其他真人 150 / 150、129 / 128"],
             statementType="observed"),
        dict(id="D07", t="540~1260", bot="全部 20 个号", decision="客户端落后服务器时照常决策：指令晚 25~288 拍（中位）落地，61% 成批到达，按下单时的比例和落地时的余额出兵，实发是本意的 2.29 倍；900~1080 的陆攻 42% 落地无效。",
             codePath=DRIVER + f"；{C110}: Strategy.send L526-540（pct 落地时按当时余额折算）", verdict="unclear", patternId="NEW-IO-01",
             evidence=["shadowcmp [SF][SB][SB2][SG]", "bursts [BA]：700~2100 编队 197 条里 121 条在 ≥3 条的批里，其他真人 411 条里 0 条", "squadfog [HM]：策略 avgMs ≤1.13 ms，一拍 56 ms——慢的不是策略"],
             statementType="observed"),
        dict(id="D08", t="900~1260", bot="19 个号", decision="影子在 900~1260 想发 332 条指令，录像里只配上 33 条。",
             codePath=DRIVER, verdict="unclear", patternId="NEW-IO-05",
             evidence=["lagstats [LA]：900~1080 168 条配上 26（15%），1080~1260 164 条配上 7（4%）", "bursts [BB]：本地发出 1293 条，录像记下 376 条", "shadowcmp [SC]"],
             statementType="observed"),
        dict(id="D09", t="本地拍 900~1246", bot="Barbary / Sukuna / bruh / Zenobia / CJ / Charlemagne / Swiss Guard / Mansa Musa / EZ_Clap / xX_Shadow_Xx", decision="10 个号的客户端先后停掉：9 个没有结果行，1 个冻在 1246 拍后记了 left。停摆时它们合计 62200 多格，是编队的一半。",
             codePath=DRIVER, verdict="unclear", patternId="NEW-IO-13",
             evidence=["squadfog [HA]：9 个号最后一条 HL-TICK 在本地拍 900~1080，录像里最后一条已执行指令 t=1008~1232；录像末拍它们各有 4818~9641 格", "L8584212：xX_Shadow_Xx 的 left 行夹在别的号 t=2790 的 HL-TICK 之间",
                       "squadfog [HL]：之后救援日志里这些号的密度 65 条读数 最小 1 / 中位 14 / 最大 59，在线号同期中位 75——没有利息，按引擎规则是已离开、由引擎托管的状态"],
             statementType="inferred"),
        dict(id="D10", t="1645~2260", bot="Carthage / New York", decision="落后服务器 180~360 拍时每 20 拍发一笔捐款（Carthage 24 笔、New York 18 笔），发令时余额没变就接着发；追平时 19 笔 / 11 笔一起扣款，余额掉到 1.1% / 3.6%。",
             codePath=DON_FLOOR, verdict="error", patternId="NEW-DN-10",
             evidence=["squadfog [HH]：发令拍 <2300 的 50 笔，窗内成交 0", "squadfog [HG]：New York 660108→23910（0.0362）= 最后 11 笔连乘 0.0362；Carthage 313768→3471（0.0111），最后 19 笔连乘 0.0103",
                       "noeffect [ND]：Carthage t=1710~2070、New York t=1800~2160 整段零花费，各有 16 条捐款日志", "L8584158 / L8584164：Carthage t=2340 剩 3471 兵，t=2351 出局"],
             statementType="inferred"),
        dict(id="D11", t="1260~2520", bot="Kandy / Leif Erikson / Goguryeo", decision="落后时下的陆攻单追平时成批落地：Kandy 6236→11295 格，Leif Erikson 8559→18206 格，Goguryeo 7284→22480 格（余额 434580→18162，密度 1.0）。",
             codePath=DRIVER + f"；{C110}: Policy.buyLand L5250-5548", verdict="unclear", patternId="NEW-IO-12",
             evidence=["noeffect [NB]：三个号之前各有 20 / 29 / 12 条指令没生效，随后单窗花掉 52% / 72% / 105% 的余额", "lagorder [LC]：三个号落后段里本地发出 109 条指令", "digest [F]：Goguryeo t=1800~2520 花掉 767054 兵、多出 15196 格（每格 50.5 兵）"],
             statementType="observed"),
        dict(id="D12", t="2530~11900", bot="Kandy / Genos / New York / Goguryeo / Denmark / Raiden / Watermelon", decision="把兵捐给停摆的账号：126 笔里成交 70 笔，到账 8833877（全部到账的 49%），税 4193699。收得最多的是 Mansa Musa（31 笔 4987780）、Barbary（12 笔 1613088）、Charlemagne（10 笔 1071956）。",
             codePath=DON_RESCUE + "；" + DON_SURPLUS, verdict="error", patternId="NEW-DN-04",
             evidence=["squadfog [HB]：停摆 126 / 70 / 8833877 / 4193699；在跑 98 / 48 / 9075895 / 3803083", "squadfog [HL]：停摆账号的密度读数中位 14", "L8585177：最后一笔，Kandy t=11900 → Mansa Musa，dAlly=15"],
             statementType="observed"),
        dict(id="D13", t="2530~4370", bot="Denmark / Raiden / Goguryeo / Watermelon / Kandy", decision="救援捐款的比例被自己的留底压到 pct 55~111：手续费按余额的 6.25% 收，和到账差不多。pct ≤70 的 22 笔成交，到账 1456089、税 1499782。",
             codePath=DON_RESCUE + "；" + ENG_DON, verdict="error", patternId="NEW-DN-02",
             evidence=["squadfog [HH]：pct ≤70/1024 的 26 笔，成交 22，税 ≥ 到账的 13 笔；救援类 75 笔成交 35，到账 2692054、税 2369288", "例：Goguryeo t=4080 → Barbary pct=57，到账 107088、税 118166（L8584377）；Raiden t=4080 → Barbary pct=64，到账 127376、税 125416（L8584376）"],
             statementType="observed"),
        dict(id="D14", t="2340~4140", bot="Denmark", decision="唯一的邻居每 100 拍左右啃一口（92→117 格，共 1783 格），1800 拍没有一条陆攻；密度到 78 就捐，从没攒到 88。",
             codePath=SB + f"；{C110}: Policy.safeAt L4524-4540（对人机的留底封顶在 oppFloorCap×领土）；{DON_FLOOR}", verdict="error", patternId="NEW-EC-08",
             evidence=["squadfog [HN]：t=2340~4140 20 个窗、17 口，序列 92 94 0 96 98 100 102 104 106 0 108 110 112 114 116 117 116 0 115 83，窗首密度 61~80，陆攻和船 0 条", "同期 13 笔救援捐款日志的 dMe 都是 78~82（out/B019/donfit.json）",
                       f"{SIM}/bots.js L63-68、L107：难度 ≤5 的内置 AI 每 100 拍出手一次；game.js expandAttack L958-1057 新进攻第一圈必赢"],
             statementType="inferred"),
        dict(id="D15", t="3060~6210", bot="Watermelon", decision="被一个不在 nb 里的号吃掉 15787 格（27 个窗），没有一条陆攻；同期还给停摆的 Swiss Guard 捐了 4 笔。",
             codePath=ANALYZE + f"；{C110}: counterAttack L871-887", verdict="error", patternId="NEW-MT-06",
             evidence=["squadfog [HC]：39 个两端被围的窗里 27 个掉地，合计 15787 格，窗内新指令 8 条（船 4 条）", "L8584603 → L8584687：t=5310~6210 14995→2915 格，cmds=71 不变",
                       "squadfog [HF][HJ]：Mansa Musa 收款的两段 t=3000~3320、t=4330~6195 和失地同期，Watermelon 出局（t=6221）后到 t=11120 没有一笔", "perhead [PH-C]：t=1230 Watermelon — Zenobia — Mansa Musa 依次相邻；其余异队停摆账号都在地图西、北"],
             statementType="inferred"),
        dict(id="D16", t="4050~5310", bot="Watermelon", decision="四周没有能打的邻居时改走海路：14 条船，纯船窗里领土 +8415 格（之后 180 拍内最高 +17560 格）；t=4050~4410 5 条船 7936→12068 格，t=5130~5310 2 条船 10170→14995 格。",
             codePath=BOAT, verdict="good", patternId="NEW-SE-G1",
             evidence=["logstats [QE]：Watermelon 14 条船、8 个纯船窗，少掉 1197997 兵，窗内 +8415 格", "logstats [QE] 明细：4050~4230 3 条船 7936→9262（之后最高 12068）；5130~5310 2 条船 10170→14995"],
             statementType="observed"),
        dict(id="D17", t="4410~4860", bot="Leif Erikson", decision="囤到密度 110 以后 7 条指令把领土从 18799 撑到 56535 格，密度降到 30；300 拍后被 T1 的 Plant 打穿。",
             codePath=BUY, verdict="unclear", patternId="NEW-AT-02",
             evidence=["L8584422（t=4410，18799 格 / 2076690 兵）→ L8584515（t=4860，56535 格 / 1700053 兵，nb=3、neut=49）", "digest [F]：t=4410~4500 花掉 865086 兵；之后快照 neut=125 / 35 / 137 / 49，新地多半是旁边出局的号留下的空地（猜测）", "L8584522 / L8584530：Raiden 的戳刺日志记下打 Leif Erikson 的是 Plant"],
             statementType="observed"),
        dict(id="D18", t="4950~5130", bot="Leif Erikson", decision="56133 格 / 175 万兵，180 拍丢 39638 格，一条指令没有；领土跌破峰值的 1/4 出局，327612 兵清零。",
             codePath=BUY + f"；{C110}: counterAttack L871-887；{ENG_ELIM}", verdict="error", patternId="NEW-DF-01",
             evidence=["L8584525 → L8584563：56133 格 / 1753686 兵 → 16495 格 / 413831 兵，cmds=148 不变", "logstats [QD]：Leif Erikson 4860→5173 领土 56535→0，期间指令 0 / 船 0", "squadfog [HK]：最后一次领土 14151 ÷ 峰值 58598 = 0.241"],
             statementType="observed"),
        dict(id="D19", t="3870~5040", bot="Raiden", decision="19794 格、4 个敌邻，丢掉 9005 格的过程里 10 条指令是 6 笔捐款、2 次替别人的戳刺、1 条船、1 条陆攻。",
             codePath=DON_SURPLUS + "；" + DON_RESCUE + f"；{C110}: counterAttack L871-887", verdict="error", patternId="NEW-DF-01",
             evidence=["logstats [QD]：Raiden 3780→5180 领土 19794→0，期间指令 10 / 船 1", "logstats [QG]：t=2250~5040 的 15 条 = 陆攻 6 + 船 1 + 捐款 6 + 戳刺 2", "squadfog [HB]：Raiden 给停摆账号 3 笔，付出 1002436"],
             statementType="observed"),
        dict(id="D20", t="4935~4960", bot="Raiden（T2）", decision="自己正在丢地时，两次各出约 10% 的余额去打 T1 的 Plant，为的是 T3 的 Leif Erikson。",
             codePath=f"{DON_HEAD} L4448-4458（主攻者和自己接壤、自己密度 ≥65、25 拍冷却 → g.attack(102, mainAttacker)，跨队也打）", verdict="unclear", patternId="NEW-MT-02",
             evidence=["logstats [QC]：2 次，估计出兵 106919 + 119042", "L8584522 / L8584530", "Leif Erikson t=5173 出局，Raiden t=5180 出局"],
             statementType="observed"),
        dict(id="D21", t="6300~9410", bot="Kandy / Genos / New York / Goguryeo", decision="4 个被围的号合计 840~860 万兵停了 3100 拍：盈余捐款的候选只有同队名字池里的号，全都超过 132 密度或没有战事；同队野人不在候选里。Kandy / Genos 一条指令没发。",
             codePath=DON_SURPLUS, verdict="error", patternId="NEW-DN-15",
             evidence=["squadfog [HE]：t=7200 / 8100 / 9000 合计 8374997 / 8372731 / 8590869 兵，密度 141~143", "squadfog [HH]：发令拍 6300~9400 捐款日志 0 笔", "logstats [QB]：硬上限快照 Genos 24、Kandy 23、New York 9 条，被截掉的利息 582989",
                       "squadfog [HI]：同期 T2 51.3%→56.1%，在线编队号占 T2 的 14.6%→8.0%"],
             statementType="observed"),
        dict(id="D22", t="2250~11070", bot="Goguryeo / New York / Kandy", decision="被围时每 60 拍一条闲置船，不设价格上限：三个号纯船窗 103 条船少掉 6543485 兵，窗内领土合计 +7 格。",
             codePath=BOAT, verdict="error", patternId="NEW-SE-05",
             evidence=["logstats [QE]：Goguryeo 50 条 / 4588400 兵 / +169 格；New York 33 条 / 929895 兵 / −826 格；Kandy 20 条 / 1025190 兵 / +664 格", "logstats [QE] 明细：Kandy t=3780~3870 2 条船少掉 532848 兵（余额的 66%），领土 13092 不变",
                       "squadfog [HM]：HL-SLOW-TICK 316 行里 Goguryeo 110、Kandy 85、New York 79 行（找落点的水路搜索）"],
             statementType="observed"),
        dict(id="D23", t="9410~11150", bot="Kandy / Genos / New York", decision="给离 150 倍上限只差几万兵的队友按固定比例捐：成交 22 笔里 17 笔被夹小，到账 2954371、税 1634432。Genos→New York 三笔各到账 5878 / 4576 / 5331，各付税 87126 / 89594 / 111667。",
             codePath=DON_SURPLUS + "；" + ENG_DON, verdict="error", patternId="NEW-DN-12",
             evidence=["squadfog [HH]：发令拍 ≥9400 且收款方在线的 52 笔", "squadfog [HJ]：New York t=9465~10445 收款段 24 笔，成交 9，到账 1408264、税 958361", "L8584969 / L8584980 / L8585025"],
             statementType="observed"),
        dict(id="D24", t="9410~11150", bot="Kandy / Genos / New York / Goguryeo", decision="同一拍 2~3 个号捐同一个人：30 组 75 笔，成交 37、没成交 23、定不了 15；先到的把收款方顶满，后到的整单不成交或只进几千兵。",
             codePath=DON_SURPLUS + "（各号各自挑 bestAlly，互相不知道）", verdict="error", patternId="NEW-DN-06",
             evidence=["squadfog [HH]：同一拍 ≥2 个号捐同一人 30 组", "L8584924~8584926：t=9410 Kandy / Genos / New York 同时捐 Goguryeo，只有 Kandy 的成交（618501）", "L8585056~8585058：t=10640 三笔到账 375039 / 254351 / 23299"],
             statementType="observed"),
        dict(id="D25", t="9410~11110", bot="Kandy / Genos / New York", decision="收款方自己已经超过 100 倍软上限还照收：Goguryeo 在密度 ≥100 时收了 12 笔 2876962（税 1043560），同期它的领土 26011→8851。",
             codePath=DON_SURPLUS, verdict="error", patternId="NEW-DN-14",
             evidence=["donwall [WG]：受捐方密度 ≥100 的成交 16 笔，到账 3428398、税 1241019", "donwall [WG]：Goguryeo 12 笔（t=9410~11110）、Raiden 4 笔（t=4590~4990）"],
             statementType="observed"),
        dict(id="D26", t="10710~11070", bot="Goguryeo", decision="24917 格 / 369 万兵（密度 148）、1 个敌邻，360 拍丢 16066 格，一条指令没有；跌破峰值的 1/4 出局，700963 兵清零。",
             codePath=BUY + f"；{C110}: counterAttack L871-887；{ENG_ELIM}", verdict="error", patternId="NEW-DF-04",
             evidence=["L8585062 → L8585109：cmds=191 不变，余额 3689016→1138593", "logstats [QF]：Goguryeo 单邻、密度 ≥128 的 3 个窗都没有指令，丢 11920 格", "squadfog [HK]：最后一次领土 6047 ÷ 峰值 26239 = 0.230；对手的余额没有录像，留底高于自己余额是按代码推的"],
             statementType="inferred"),
        dict(id="D27", t="11130~12267", bot="Kandy", decision="把 6 笔、连税 1963463 兵捐给停摆的 Mansa Musa（密度 136→72），随后 t=11790~12240 丢 10085 格，唯一的一条指令还是救援捐款。",
             codePath=DON_SURPLUS + "；" + DON_RESCUE, verdict="error", patternId="NEW-DF-01",
             evidence=["squadfog [HJ]：Mansa Musa t=11120~11900 收款段，Kandy 6 笔到账 1477118、税 486345", "L8585166 → L8585189：15026 格 / 1076594 兵 → 4941 格 / 332087 兵，cmds 150→151", "L8585177：t=11900 救援捐款 pct=61；L8585192 结果行 t=12267"],
             statementType="observed"),
        dict(id="D28", t="2250~6221", bot="Kandy（T2）对 Watermelon（T1）", decision="跨队保护：Kandy 贴着敌队的 Watermelon 4000 拍不打它（被围、密度 44~78），Watermelon 也不打它；Watermelon 出局后 Kandy 才用 2 条指令拿到 1266 格。",
             codePath=ANALYZE, verdict="unclear", patternId="NEW-MT-01",
             evidence=["perhead [PH-C]：t=1230 Kandy 与 Watermelon 接壤 65~66 格", "digest [J]：Kandy 129 条快照里 102 条被围", "truth [TF]：录像期编队内部互打 0 格"],
             statementType="observed"),
        dict(id="D29", t="6210~6300", bot="Kandy", decision="Watermelon 出局留下空地，Kandy 当窗用 2 条指令（不是船）拿到 1266 格，13760→15026。",
             codePath=f"{C110}: Policy.act L4781-4944 → Policy.buyLand L5250-5548（空地报价）", verdict="good", patternId="NEW-EG-G1",
             evidence=["Kandy t=6210 13760 格 cmds=126 → L8584691 t=6300 15026 格 cmds=128，boats=20 不变", "L8584689：Watermelon 结果行 t=6221，最后一次领土 2795 格"],
             statementType="inferred"),
    ],
    # ==TAIL==
)
