# B049 人工分析部分。这个对局包里混了两个物理房间（src/tools/rooms-discovery.json）：
#   房间 0（主房间，物理房间 159）：13 个号，只有日志、没有录像——数字全部来自 in_game.log 的 HL-TICK / HL-DONATE / HL-ASSIST 和结果行；
#   房间 1（物理房间 160）：2 个号，包里的 replay.txt 属于它——scripts/resim_r08.mjs 逐拍重演到 t=6099，67/67 条 traj 快照地、兵都一致。
#   出处：out/B049/digest.txt（房间 0）、digest_room1.txt、donfit.txt [FA]~[FE]、logstats.txt [QA]~[QD]、noeffect.txt [NA][NB]、clockskew.txt [KA][KB]、
#         truth.txt [TA]~[TO]、shadowcmp.txt [SA]~[SJ]、lagstats.txt、harvest.txt、top.txt、spawncheck.txt、shadow_tr1.json（trshow.py）。
#   L 号 = bundles/B049/in_game.log 每行开头的原始行号。
from patterns_catalog import pick

C110 = "src/strategy/v27-team-c110.js"
SIM = "src/sim/sim"

R = dict(
    contextExtra=dict(
        bundleRooms="rooms-discovery.json：B049 nRooms=2。房间 0 = 物理房间 159，陆地 762763，53 个真人，3 队，2026-11-10T14:30:40Z 开局，日志从本地拍 350 开始，没有录像，"
                    "最后一条结果行在 t=11510；房间 1 = 物理房间 160，地图 10 / 种子 3633，陆地 546152，45 个真人，3 队各 15 人，14:31:20Z 开局，录像到 t=6099。"
                    "本文正文（context / outcome / timeline / deaths）写房间 0，房间 1 在 sideRooms 里。",
        cardMismatch="card.json 是两个房间混在一起算的：squadBots=10、teamSplitCounts={1:1,2:4,3:5}、peakPrimaryTeamShareSeen=0.665、likelyRejectedTransfers=27/124。"
                     "按房间拆开：房间 0 有 13 个号（8 个有结果行，5 个日志中途断掉、没有结果行），房间 1 有 2 个号。原值留在 context.cardOriginal。",
        truthTeamSplit="房间 0（没有录像）：结果行给出 T3×5（Satoshi、Brittany、EnPassant、Golden Horde、Lannes）、T2×2（Dzungar、Portugal）、T1×1（GalaxyBrain）。"
                       "断流的 5 个号里 Tomato(48)、Ghana(40)、Palmyra(44)、SmurfAccount(37) 也是 T3：它们收到过 squad rescue donate，而这条分支要求 isTeammate（c110 L4436），"
                       "捐出方全是 T3 的号；玩家号取自 HL-DONATE 行的 ally=。SonHeungMin 没有被捐过、也没有结果行，队号不明。所以 T3 是 9 个号，其中 4 个从 t≈1000 起没有日志。"
                       "房间 1（录像）：BlackRock(3)、Dahomey(4) 都在 T2。",
        strategyVersion="squad20 = c110；本局在 14:08:38Z 的改动之后：没有 Boss，出生点走后端协调器（[BACKEND-SPAWN-COORD] / [HL-SPAWN-BACKEND]）。",
        notes="日志标签中途换名：Dzungar>Cringe>BurgerKing>Patton、GalaxyBrain>Sardinia>ArchdukeCharles>KaiCenat、Lannes>DoomSlayer>Tang>Kakashi>Thanos>Cleopatra、Portugal>Ptolemy；"
              "房间 1 的 BlackRock>Musashi>ProGamer99。本文一律用第一个名字。HL-TICK 的 t 是各号客户端的本地拍；房间 0 没有服务器拍可对，写的都是本地拍。"
              "房间 0 的日志有丢行：行号 8648330~8649680 之间缺 69 行（52 处），大多是 HL-TICK；时间线合计时某个号缺的那一拍沿用它的前一条快照（botsCarriedForward）。",
        fairSharePerCapita="房间 0：53 个真人里编队 13 个（24.5%）；房间 1：45 个里 2 个（4.4%）。",
    ),
    outcomeExtra=dict(
        winnerHow="房间 0 没有 over 行：最后一条结果行（Lannes t=11510，L8649680）的全队领土是 T1 99.3% / T3 0.2%，按它定 T1 获胜。",
        squadOnWinningTeam="GalaxyBrain 在 T1，t=10766 阵亡（当时 T1 占 67.7%）。",
        sideRoomResult="房间 1：T3 获胜（t=6099 占 92.9%）；BlackRock 活到最后（21864 格，第 8 名），Dahomey t=2933 阵亡。",
    ),
    phases=dict(
        spawn=dict(
            window="t=0~90",
            facts=[
                "房间 0 的出生阶段不在这个包里（日志从本地拍 350 开始）。",
                "房间 1：日志出生指派 28 行，其中后端协调器 26 行；BlackRock、Dahomey 各 14 条指派。引擎落点 BlackRock (38,760)、Dahomey (466,902) 都是各自的第 13 条；"
                "最后一条（(740,732)、(620,356)）都没有执行（spawncheck [PA][PC]）。两个号相距 451 像素。",
                "[BACKEND-SPAWN-COORD] 18 行，每行都是 Solved 20 bots（map=931x959，minSep 57~93 像素）：名单是整支启动名单——SmurfAccount、Golden Horde、Palmyra、SonHeungMin、"
                "EnPassant、Dzungar、Satoshi、Portugal 等在房间 0，Zenitsu、Florida Man、Wallachia、Lusitania、HighPing 不在任何房间；这个房间里只有 2 个号（L8648332、L8648455、L8648475）。",
                "协调器给 BlackRock 报的 minAllyDist 74~123、voronoi 2936~18955 像素，是对着 19 个名字算的，其中 18 个不在这个房间。",
            ],
            problems=[
                "协调器把不在本房间的 18 个名字也排进同一张图，2 个真正在场的号拿到的是『20 个号分一张图』的解；每次重解都换点，两个号都停在倒数第二解上。",
            ],
        ),
        opening=dict(
            window="t=90~630",
            facts=[
                "房间 0：HL-OPENING 73 行，13 个号在本地拍 350~800 都按周期出手（第 3~8 周期）；t=630 编队 13 个号合计 38928 格（5.10%），t=900 79523 格（10.43%），13 个号全在长（digest [C][K]）。",
                "房间 1：(270,630] 人均吃空地 我方 2289 格、其它真人 1924 格；人均吃人机 232 对 99 格（harvest）。t=630 BlackRock 3350 格、Dahomey 2270 格。",
                "房间 1 的指令时延：执行拍 0~540 中位 15 拍、P90 20，陆攻落地无效 0 条（lagstats [LB]）。",
            ],
            problems=[],
        ),
        midgame=dict(
            window="t=630~3500",
            facts=[
                "两个房间的客户端同时变慢。房间 1（录像实测，lagstats [LB]）：执行拍 540~1260 时延中位 77 / P90 163 / 最大 208 拍，陆攻落地无效 21%；1260~1800 中位 197 / P90 309 / 最大 424，无效 61%。"
                "同一个服务器拍里冲出 7~8 条指令的批次 5 次（其它真人最多 3 条，[LC]）。",
                "房间 0 比房间 1 落后得更多（clockskew [KA]，按日志行号先后给两个房间的本地拍对表；两边都不卡时房间 0 领先 666 拍）：房间 1 打到 450 拍时房间 0 少走了 166 拍，"
                "630 拍时 253，900 拍时 316，990 拍时 333（房间 0 本地拍 ≈1323）；到房间 1 的 1350 拍（房间 0 本地拍 ≈2022）差值回到 0。加上房间 1 自己的时延，房间 0 在本地拍 1300 前后落后服务器约 400~500 拍（推断）。",
                "5 个号的日志在这段时间断掉：Tomato、Palmyra、SmurfAccount 最后一条 HL-TICK 在 t=990（7372 / 9088 / 6577 格），Ghana t=1080（9800 格），SonHeungMin t=1170（8882 格）。"
                "t=900 这 5 个号合计 33370 格，占编队 79523 格的 42%。之后它们没有任何日志行，也没有结果行。",
                "指令没生效（noeffect [NA]，cmds 涨了、余额没少、地没涨）：本地拍 810~1080 的 175 条里 18 条，1080~1350 的 92 条里 29 条，1350~1620 的 55 条里 39 条，1620~1890 的 56 条里 39 条。"
                "Portugal 在 1530~1800 每 90 拍记 6 条指令（= 同目标 15 拍冷却一到就重发），余额只按利息涨、领土 7474 不变。",
                "本地拍 1800~2250 七个号先后清仓（logstats [QA]）：编队余额 262 万（t=1980）→83 万（t=2250），领土 77010→107485 格。"
                "Satoshi 539031→13899（7601→18305 格，密度 0.8）；Golden Horde 448667→4959；Portugal 338330→14025（7474→19921 格）；GalaxyBrain 501081→49410；"
                "Lannes 275243→8775（只多 49 格，下一窗回流 265709）；Brittany 562418→58610（cmds 没变，回流 216389）；EnPassant 392906→26181（6 条船，领土没变）。",
                "清仓之后：Satoshi t=2160~2340 丢 8747 格、0 条指令，t=2420 阵亡（第 43 名）。编队领土 107485（t=2250）→83791（t=3600），余额 83 万→522 万。",
                "t=2340 起各号停住囤兵：Portugal 20168 格被围（nb=0），Brittany 9558 格（t=2340~4950），Golden Horde 19113~19180 格（t=2340~4770，余额 11.5 万→138 万），"
                "GalaxyBrain 8030 格（t=3060~4500，密度 30→143），EnPassant 9656 格（t=3690~6750）。",
                "房间 1：BlackRock 在服务器拍 1596 和 1624 各落地 3 条过期的陆攻（本意各占余额 28% / 27%，实发 60% / 57%，[TG]），t=1530~1710 领土 10797→18971 格，约 18 兵/格；"
                "密度掉到 1.4~2.8，Player 676（T3）趁机吃回 1314 格。之后 t=1800~3690 领土 17657 格不动、0 条指令，余额 71712→2040130。",
                "房间 1：Dahomey 的最后一条指令在服务器拍 1512；t=1512~2933 0 条指令，余额 53546→310595（t=2760），之后被 🇱🇾🥵 和 Hetos [EU]（都是 T3）吃光。",
                "房间 1 的人机收割：(900,1260] 人均吃人机 我方 2470 格、其它真人 3458 格；(1260,1800] 1763 对 2970 格（harvest）。(1800,3600] 其它真人人均从真人手里拿 4092 格，我方 0 格。",
            ],
            problems=[
                "客户端落后服务器几百拍时，策略看不到自己发的单子生效，冷却一过就原样再发；补拍时这些单子成批落地，按落地时的余额比例扣兵——七个号在同一段里把余额打空（推断，房间 1 有录像实证同一机制）。",
                "13 个号里 5 个的客户端在 t≈1000~1170 停掉，T3 的 9 个号只剩 5 个有人管。",
            ],
        ),
        endgame=dict(
            window="t=3500~11510",
            facts=[
                "全队领土（结果行）：t=2420 T1 30.4% / T2 35.2% / T3 33.0%；t=5302 28.4 / 41.0 / 29.7；t=9682 56.2 / 33.2 / 9.6；t=10766 67.7 / 21.2 / 9.9；t=10871 79.3 / 11.2 / 8.1；"
                "t=11046 85.6 / 0 / 11.0；t=11403 96.0 / – / 1.1；t=11510 99.3 / – / 0.2。",
                "t=9682 时 T3 的 72892 格里，Golden Horde 65839 格、Lannes 6512 格——T3 只剩这两个号。",
                "编队（有日志的号）占陆地：t=3600 10.99%（7 个号）→t=5490 14.45%→t=7650 18.23%→t=8730 26.02%→峰值 t=9540 31.12%（6 个号，237347 格，余额 2772 万，密度 116.8）→"
                "t=10080 23.02%→t=10890 10.57%→t=11430 0.85%（digest [C]）。",
                "长大的两个号：Dzungar（T2）9216 格（t=4230）→103429 格（t=9720，13.6%，余额 1231 万）；Golden Horde（T3）19180 格（t=4770）→65839 格（t=9450）→82308 格（t=11070）。",
                "捐款（donfit [FA]~[FC]）：日志 124 笔，成交 113、没成交 4、定不了 7；到账 1843.1 万，税 890.7 万（占捐出方付出的 32.6%）。"
                "Portugal→Dzungar 35 笔，到账 966.1 万、税 340.9 万；Golden Horde 收 22 笔 240.7 万；EnPassant 收 10 笔 238.1 万（税 199.9 万）；"
                "断流的 4 个 T3 号收 43 笔，到账 368.9 万、税 240.8 万（t=3060~4875）。",
                "连发 24 笔（同一个号 ≤25 拍内对同一人再捐一笔，发令时前一笔还没扣款，两笔都成交）：多付到账 376.3 万 + 税 171.1 万；其中 Portugal 11 笔。成交的 113 笔里 25 笔在发令 20 拍后还没扣款。",
                "跨队协防戳刺 17 次（logstats [QC]），每次约 10% 余额：GalaxyBrain（T1）为 T3 的 Brittany / Golden Horde 打 [FR] 9 次、打 Player [og]69 1 次，估计出兵 137.8 万；"
                "Golden Horde（T3）为 T1 的 GalaxyBrain 打 [FR] 3 次、Player 631 1 次、Player [og]69 3 次，估计出兵 326.6 万。",
                "GalaxyBrain t=8730~10170 cmds=118 不变（1440 拍），敌邻 1 个，密度 91→150.0；t=9540、9630、10170 三条快照余额正好等于 150×领土（4129950 / 4129950 / 3577200）。"
                "t=9630~9810 丢 3685 格没有还手。t=10440~10710 27554→10456 格、0 条指令，t=10766 阵亡。",
                "Dzungar t=9720~10800：103429→20295 格，cmds 111→113（2 条指令），密度一直在 92~133，t=10871 带着 270 万余额阵亡。",
                "EnPassant t=9540~9630 15182→9811 格，t=9682 阵亡；Golden Horde 在 t=9555~9655 给它捐了 5 笔，4 笔成交、到账被 150 倍上限夹小：到账 194.9 万，税 180.5 万。",
                "Portugal 20107 格 / 143 万（t=10980）→t=11046 阵亡；Golden Horde 82308 格（t=11070）→t=11403 阵亡，期间 0 条指令；Lannes 6512 格，t=11510 最后一个阵亡。",
                "房间 1：BlackRock t=3717 起出手（[TE]）：整局从 Player 582（T1）手里拿 16789 格（耗兵 202.8 万，120.8 兵/格），从 Player 676（T3）拿 1274 格（60.9 万，477.9 兵/格）；"
                "被 Player 676 吃走 6543 格、Player 582 2090 格。T1 在 t=5220 清零，T3 50.0%（t=3600）→76.3%（t=5400）→92.9%（t=6099）。",
            ],
            problems=[
                "T3 的 4 个断流号在 t=3060~4875 被打时，T3 在线的 4 个号给它们捐了 43 笔（付出 609.7 万，其中税 240.8 万）；受捐方读数里的密度一直是 0~19。",
                "盈余捐款的比例是固定的 153/185/280，不看捐出方自己的留底：Portugal 35 笔成交，发令时密度中位 79.7，捐后中位 58.6、最低 44.7，30 笔捐完低于 68（donfit [FE]）。",
                "三个最大的号（Dzungar、GalaxyBrain、Golden Horde）最后都是高密度挨打、几乎不发指令地被吃完；阵亡前最后一条快照的余额合计 722 万。",
            ],
        ),
    ),
    turningPoints=[
        dict(
            t0=900, t1=1170, shareBefore=10.43, shareAfter=8.68, shareUnit="有日志的编队号合计占房间 0 陆地 %（t=900 是 13 个号，t=1170 是 9 个号）",
            what="5 个号的客户端停掉：Tomato、Palmyra、SmurfAccount 的日志停在本地拍 990，Ghana 1080，SonHeungMin 1170；t=900 它们合计 33370 格，是编队的 42%。同一时间两个房间的客户端都在变慢。",
            evidence=[
                "digest [B][I]：5 个号 HL-TICK 首末拍 360..990 / 360..1080 / 360..990 / 360..990 / 360..1170，没有结果行（event=None）。最后一条快照 7372 / 9800 / 9088 / 6577 / 8882 格，余额 1.7~4.8 万。",
                "clockskew [KB]：这 5 个号停掉前相对房间 1 已经多落后 145~287 拍（Tomato 147、Palmyra 145、SmurfAccount 189、Ghana 250、SonHeungMin 287）。",
                "clockskew [KA]：房间 1 的 450 拍→990 拍，房间 0 多落后的拍数 166→333；房间 1 自己的时延在执行拍 540~1260 是中位 77 / P90 163 拍（lagstats [LB]，录像实测）。",
                "bundles/B049/in_game.log 行号 8648330~8649680 缺 69 行（52 处），最长一处缺 5 行；这 5 个号各自之后还应该有上百条快照，不是丢行能解释的。",
                "策略自身不慢：HL-SLOW-TICK 123 行，单次最长 115.4 ms，t<2500 最长 40.6 ms；873 条 HL-TICK 的 avgMs 最大 1.24 ms。",
                "它们没有死：t=3060~4875 的 43 条 HL-DONATE 以它们为收款方（ally=48/40/44/37），读到的密度 dAlly 0~19。",
            ],
            priorDecisions=[
                dict(t="本地拍 900~1170", bot="Tomato / Palmyra / SmurfAccount / Ghana / SonHeungMin", decision="不是策略决策：客户端停止打日志、之后没有结果行。策略和驱动层里没有时延或掉线检测。",
                     codePath=f"{C110}: 文件头 L19-31（驱动层 afterTick 包装，只有 450 ms / 8 拍的在途保护，没有时延检测）",
                     judgement="unclear", why="根因在主机侧（同一台机器上两个房间 15 个客户端同时变慢），包里没有主机数据"),
            ],
            statementType="observed",
        ),
        dict(
            t0=1800, t1=2420, shareBefore=10.10, shareAfter=12.89, shareUnit="有日志的编队号合计占房间 0 陆地 %（t=1980 → t=2520；中间 t=2250 冲到 14.09%）",
            what="积压的旧单子成批落地：七个号在本地拍 1800~2250 把余额打空（编队余额 262 万→83 万），领土先涨 3 万格再吐回去；Satoshi 密度掉到 0.8，t=2420 阵亡。",
            evidence=[
                "logstats [QA]：7 起清仓，全部落在本地拍 1800~2250——Portugal 338330→14025、Satoshi 539031→13899、Golden Horde 448667→4959、EnPassant 392906→26181、GalaxyBrain 501081→49410、Lannes 275243→8775、Brittany 562418→58610。",
                "noeffect [NA]：清仓之前，本地拍 1080~1890 的 203 条指令里 107 条没有生效（余额只按利息涨、领土不变）；1890~2160 的 53 条里 24 条；2430 之后几乎没有。",
                "noeffect --bot Satoshi：t=1350~1890 cmds 40→50（10 条，脚本按 90 拍窗数到 8 条，另 2 条落在缺快照的 180 拍窗里），余额 170304→539031 一路按利息涨、领土 7601 不变；t=1890~1980 花掉 359669（66.7%）领土 7601→14065，t=1980~2070 再花 269798，余额剩 19745。",
                "noeffect --bot Portugal：t=1530~1800 每 90 拍 6 条指令、合计 18 条全没生效（敌邻 1 个）；6 条 / 90 拍 = Strategy.send 的同目标 15 拍冷却；t=1800~1890 花掉 172557（51%），t=2250 余额 14025、领土 19921。",
                "最干净的一例是 Brittany（HL-TICK）：本地拍 1260~1620 发了 12 条船（cmds 43→55、boats 0→12），余额只按利息涨（96292→282760）、领土 8185 不变；t=1620~2070 没有再发任何指令（cmds=55），余额继续涨到 562418；"
                "t=2070~2160 仍然一条指令没发，余额 562418→58610，领土随后 8204→9057→9558——450~900 本地拍之前发的船在这一窗一起落地。EnPassant 同样：t=1620~1980 的 12 条船余额一兵没少，t=1980~2160 一窗少掉 494842（logstats [QE]）。",
                "clockskew [KA]：房间 0 的本地拍在 1323 前后比房间 1 多落后 333 拍，到 2022 前后追平——追平的这一段正是清仓的这一段。",
                "clockskew [KC]：结果行自带写入时间。房间 0 的 8 条结果行（本地拍 2420~11510）首末之间每本地拍 56.02 毫秒，房间 1 是 56.03 毫秒——本地拍 2420 之后房间 0 的客户端按服务器的节拍走，不再掉拍。",
                "房间 1 的录像实证同一机制（truth [TG]）：BlackRock 在服务器拍 1596、1624 各落地 3 条同目标陆攻，本意各 28% / 27%，实发 60% / 57%；全局陆攻 + 发船 114 条里 48 条是重发（42%）。",
                "digest [N]：清仓后的回流——Lannes t=2160~2250 +265709、Brittany t=2250~2340 +216389、GalaxyBrain t=2340~2430 +290813、Dzungar t=1980~2070 +197879（进攻的兵打完目标后退回）。",
                "digest [I]：Satoshi t=2160 18305 格 / 13899 兵（密度 0.8）→t=2250 13969 格→t=2340 9558 格，cmds=57 不变，t=2420 阵亡；当时 T3 其它在线号的密度 0.4~7.1。",
            ],
            priorDecisions=[
                dict(t="本地拍 1080~1890", bot="Satoshi / Portugal / Golden Horde / GalaxyBrain / Dzungar / Lannes / Brittany", decision="本地看不到上一条陆攻生效，同目标 15 拍冷却一到就原样再发；每条单子带的是『占余额的比例』，落地时按当时的余额扣。",
                     codePath=f"{C110}: Strategy.send L526-540（在线时同目标 15 拍冷却；pct = ceil(troops×1024/bal)−1 按本地余额折算）；文件头 L19-31（没有时延检测）",
                     judgement="error", why="落后服务器几百拍时，冷却挡不住重发；Portugal 对同一个邻居记了 22 条"),
                dict(t="本地拍 1980~2160", bot="EnPassant", decision="被围（没有敌邻和中立地）时连发 6 条船，余额 392906→26181，领土 14497 没变。",
                     codePath=f"{C110}: Policy.act L4781-4925 → idleBoats（L4923，本拍没有别的指令时发船）",
                     judgement="unclear", why="没有录像，看不到 6 条船的去向"),
            ],
            statementType="inferred",
        ),
        dict(
            t0=5302, t1=9682, shareBefore=29.7, shareAfter=9.6, shareUnit="T3（编队 9 个号所在的队）全队占房间 0 陆地 %（结果行的 team.totals）",
            what="T3 从三分天下掉到只剩 Golden Horde 和 Lannes：T1 28.4%→56.2%。这 4400 拍里 T3 的编队在线号其实在长（Golden Horde 33241→65839 格），丢掉的是 T3 的野人和 4 个断流号的地。",
            evidence=[
                "结果行 team.totals：t=5302（Brittany 阵亡，L8649088）T1 28.4 / T2 41.0 / T3 29.7；t=9682（EnPassant 阵亡，L8649531）56.2 / 33.2 / 9.6。",
                "t=9682 T3 共 72892 格，其中 Golden Horde 65839、Lannes 6512，其余不到 600 格。t=5302 T3 约 22.7 万格，其中有日志的编队号（Golden Horde、EnPassant、Lannes）约 4.6 万格。",
                "断流的 4 个 T3 号在 t=3060~4875 还活着并且在挨打：43 条 HL-DONATE 写着 squad rescue（35 条）/ surplus（8 条）→ ally=48/44/37/40，dAlly 读数 0~19。"
                "Tomato 在 t=3840~3865 连收 3 笔（约 28 万兵）后密度从 1 变成 12，按此估它当时约 2.5 万格（推断）。t=4875 之后日志里再没有以它们为对象的捐款。",
                "donfit [FC]：这 4 个号共收 43 笔，到账 3688937，捐出方付税 2408321；捐出方是 EnPassant 12 笔、Lannes 11、Brittany 10、Golden Horde 10。",
                "同一时期在线的 T3 号都停着：Brittany 9558 格（t=2340~4950）密度 33→93，t=5302 被 [FR]（T2）吃光；EnPassant 9656 格（t=3690~6750）；Lannes 2158~6512 格。",
                "t=5470 起 EnPassant、Lannes 给 Golden Horde 捐了 22 笔 240.7 万，Golden Horde 活下来并长到 65839 格（t=9450）。",
            ],
            priorDecisions=[
                dict(t="3060~4875", bot="EnPassant / Lannes / Brittany / Golden Horde", decision="按名字池认出『编队兄弟』正在被真人打，就捐；不看对方是不是还在线。受捐方密度 0~19，捐进去的兵留不住。",
                     codePath=f"{C110}: tryDonateToTeammate L4419-4445（isOurSquadBot 只查名字 L3973；救援条件 inHumanAtk>0 且 (≥8% 余额 或 dAlly<75)）",
                     judgement="error", why="43 笔付出 609.7 万（税 240.8 万），受捐方之后还是没了"),
                dict(t="2340~4950", bot="Brittany / Golden Horde / EnPassant / Portugal", decision="清仓后各号停在 1 万~2 万格上囤兵，密度涨到 90 以上才通过捐款或零星出手放出去。",
                     codePath=f"{C110}: Policy.buyLand L5250+（对真人：c ≥ worth 且没超软上限就 break；拥挤门槛、唯一缓冲门槛）",
                     judgement="unclear", why="房间 0 没有录像，跑不了影子，哪一道门槛在挡只能参照房间 1 的 BlackRock"),
            ],
            statementType="inferred",
        ),
        dict(
            t0=9540, t1=10890, shareBefore=31.12, shareAfter=10.57, shareUnit="有日志的编队号合计占房间 0 陆地 %",
            what="编队三个队的大号在 1350 拍里相继被吃：EnPassant（T3，t=9682）、GalaxyBrain（T1，t=10766）、Dzungar（T2，t=10871）；T1 56.2%→79.3%。Dzungar 一个号就丢了 83134 格，期间只发了 2 条指令。",
            evidence=[
                "digest [C]：t=9540 6 个号 237347 格（31.12%）、余额 2771.7 万、密度 116.8，3 个号超软上限；t=10080 175572 格；t=10620 139379 格；t=10890 80601 格（3 个号）。",
                "Dzungar 的 HL-TICK（L 行见 digest [E]）：t=9720 103429 格 / 12307936 兵 / 密度 119.0 / 敌邻 2 → t=9900 87477 → t=10080 59204 → t=10170 49375 → t=10620 33782 → t=10710 20295（密度 125.8）；"
                "cmds 111（t=9720）→112（t=9900）→113（t=10170）之后不变；t=10871 阵亡，最后一条快照余额 2700420。",
                "GalaxyBrain：t=8730~10170 cmds=118 不变，密度 91.2→150.0；t=10170~10260 2 条指令（其中一条是 t=10195 为 Golden Horde 打 Player [og]69 的戳刺）花掉 135 万，+276 格；t=10440~10710 27554→10456 格、0 条指令。",
                "EnPassant：t=9540 15182 格 / 1194521 兵 → t=9630 9811 格 / 1399105 兵（密度 142.6）→ t=9682 阵亡。Golden Horde 的 5 笔盈余捐（t=9555/9575/9605/9625/9655，pct 280/280/185/280/185）："
                "donfit 判 5 笔里 4 笔成交、到账都被夹小（1188729 / 176221 / 332213 / 218627），税 544845 / 414495 / 464276 / 394803；1 笔没成交（同 pct 的单子余额分不出是哪一笔，归到第 1 笔）。",
                "logstats [QC]：Golden Horde 在 t=10530 / 10670 / 10740 为 GalaxyBrain 打 Player [og]69 三次，估计出兵 76.3 万 / 70.7 万 / 62.2 万；GalaxyBrain 在 t=10766 阵亡。",
                "Portugal 在 t=9620~10660 又给 Dzungar 捐了 7 笔（3 组连发），自己的密度在 50~80 之间来回。",
                "结果行：t=9682 T1 56.2%；t=10766 67.7%；t=10871 79.3%。",
            ],
            priorDecisions=[
                dict(t="9720~10800", bot="Dzungar", decision="丢掉 80% 领土的 1080 拍里只发了 2 条指令，密度保持在 92~133。",
                     codePath=f"{C110}: Policy.peerAggressor L4586-4625（打我的人要满足 bal[q]+inc ≤ 1.6×B 且 inc ≤ 12%×B + 我压在他身上的兵，才算『该反击的对象』）；"
                              f"Policy.buyLand L5250+（留底 keep = max(keep, safeAt)，对真人的 safeAt 不封顶）",
                     judgement="error", why="270 万兵随最后 2 万格一起没了；哪道门槛挡的没法用影子核实（没有录像）"),
                dict(t="8730~10170", bot="GalaxyBrain", decision="只有 1 个敌邻、密度从 91 涨到 150（硬上限）的 1440 拍里一条指令都没有。",
                     codePath=f"{C110}: Policy.buyLand L5250+（唯一缓冲 isSoleHealthyBuffer：只有一个真人邻居时 B < 1.28×100×领土 就跳过；留底 safeAt）",
                     judgement="error", why="余额顶在 150×领土上不再生息；之后 330 拍被吃光"),
                dict(t="9555~9655", bot="Golden Horde", decision="被围、密度 130，按固定比例 280/185 连捐 5 笔给正在崩的 EnPassant。",
                     codePath=f"{C110}: tryDonateToTeammate L4457-4489（盈余分支：bestAlly 的打分里 (outAtk+inAtk)/500 越大越优先；pct L4488 不看收款方还能收多少）；{SIM}/game.js L340-425（到账按 150×领土−余额 夹小，税按捐出方余额全额收）",
                     judgement="error", why="到账 194.9 万、税 180.5 万，EnPassant 在最后一笔之后 27 拍阵亡"),
            ],
            statementType="observed",
        ),
    ],
    deathNotes={
        "Satoshi": dict(
            cause="积压的旧单子成批落地：本地拍 1350~1890 记的 10 条指令没有一条生效，t=1890~2070 连同新发的 7 条一起落地，余额 539031→19745（96%），领土 7601→18305 格、密度 0.8。"
                  "t=2160~2340 丢 8747 格，cmds=57 没变，t=2420 阵亡（第 43 名）。同队在线的编队号当时密度 0.4~7.1，一笔也捐不出。",
            chain=["t=1350~1890 10 条指令没生效，余额 170304→539031", "t=1890~1980 花掉 359669，7601→14065 格", "t=1980~2070 再花 269798，余额 19745", "t=2160 18305 格 / 13899 兵（密度 0.8）",
                   "t=2250 13969 格", "t=2340 9558 格 / 88710 兵", "t=2420 阵亡"],
            statementType="inferred"),
        "Brittany": dict(
            cause="t=2340~4950 停在 9558 格上囤兵（密度 33→93，敌邻 1 个），期间给 EnPassant 和断流的 Ghana / Tomato / Palmyra 捐了 14 笔（成交 11 笔，到账 100 万、税 47 万）。"
                  "t=4950 起被 [FR]（T2，按 GalaxyBrain t=5020 / 5090 的戳刺对象认定）吃：9558→7865→4252→2676 格，t=5302 阵亡；最后一条快照还有 295700 兵（密度 110.5）。挨打期间收到 3 笔救援捐款共 292896。",
            chain=["t=2340 9558 格 / 315493 兵", "t=4950 9558 格 / 887746 兵（密度 92.9）", "t=5040 7865 格", "t=5130 4252 格 / 298988 兵", "t=5220 2676 格 / 295700 兵", "t=5302 阵亡"],
            statementType="observed"),
        "EnPassant": dict(
            cause="t=9540 15182 格 / 119 万兵（密度 78.7，nb=0、中立 153 格），90 拍后只剩 9811 格，t=9682 阵亡；谁打的看不到（没有录像，也没有针对它的戳刺日志）。"
                  "阵亡前 127 拍里 Golden Horde 给它捐了 5 笔盈余捐，成交 4 笔、到账 191.6 万（被 150 倍上限夹小）、税 181.8 万；结果行里它阵亡时还有 634242 兵。",
            chain=["t=7650 15040 格", "t=9540 15182 格 / 1194521 兵", "t=9555~9625 收 4 笔，到账 1949230", "t=9630 9811 格 / 1399105 兵（密度 142.6）", "t=9682 阵亡（余额 634242）"],
            statementType="observed"),
        "GalaxyBrain": dict(
            cause="T1（获胜队）里唯一的编队号。t=8730~10170 只有 1 个敌邻（Player [og]69，T2），1440 拍没有一条指令，密度 91→150（硬上限）；t=9630~9810 丢 3685 格没有还手。"
                  "t=10170~10260 出手 2 条（135 万，+276 格，之后涨到 27554 格），t=10440 起被 Player [og]69 反推：27554→22645→15684→10456 格、0 条指令，t=10766 阵亡，最后一条快照 845528 兵。",
            chain=["t=8730 27111 格 / 密度 91.2 / cmds=118", "t=9540 27533 格 / 4129950 兵（= 150×领土）", "t=9810 23848 格", "t=10170 23848 格 / 3577200 兵（= 150×领土）", "t=10260 24124 格 / 2222909 兵 / cmds=120",
                   "t=10440 27554 格", "t=10710 10456 格 / 845528 兵", "t=10766 阵亡"],
            statementType="observed"),
        "Dzungar": dict(
            cause="编队最大的号（T2）。靠 Portugal 的 35 笔捐款（966.1 万）从 9216 格（t=4230）长到 103429 格（t=9720，占陆地 13.6%）。之后 1080 拍丢掉 83134 格，只发了 2 条指令（cmds 111→113），"
                  "密度一直 92~133；t=10871 阵亡，最后一条快照 20295 格 / 2700420 兵。打它的是谁看不到；同期 T1 从 56.2% 涨到 79.3%。",
            chain=["t=9720 103429 格 / 12307936 兵（密度 119.0）", "t=9900 87477 格 / 8556525 兵（1 条指令）", "t=10080 59204 格", "t=10170 49375 格（1 条指令）", "t=10530 41287 格 / 密度 131.9",
                   "t=10710 20295 格 / 2554088 兵", "t=10871 阵亡"],
            statementType="observed"),
        "Portugal": dict(
            cause="t=2250 起被围在 20168 格上（112 条快照里 92 条 nb=0），整局当银行：35 笔盈余捐全部给 Dzungar。Dzungar 阵亡（t=10871）后 175 拍，t=11046 阵亡——t=10980 还有 20107 格 / 1429631 兵，66 拍内被吃光；当时 T1 占 85.6%。",
            chain=["t=2250 19921 格 / 14025 兵", "t=4040~10660 捐 35 笔", "t=10980 20107 格 / 1429631 兵 / 敌邻 1", "t=11046 阵亡"],
            statementType="observed"),
        "Golden Horde": dict(
            cause="T3 最后的大号。t=11070 82308 格 / 3877278 兵（密度 47.1），t=11160~11340 76573→69725→50826 格，0 条指令，t=11403 阵亡；最后一条快照 3678981 兵。当时 T1 占 96%，T2 已经清零。"
                  "t=10530~10740 它为 T1 的 GalaxyBrain 打了 3 次戳刺（估计 209 万兵）。",
            chain=["t=9450 65839 格", "t=9555~9655 给 EnPassant 捐 5 笔（付出 375 万）", "t=10530~10740 3 次戳刺", "t=11070 82308 格 / 3877278 兵", "t=11340 50826 格 / 3678981 兵", "t=11403 阵亡"],
            statementType="observed"),
        "Lannes": dict(
            cause="整局没超过 6512 格：t=1080 5844 格，清仓窗只多 49 格，t=6570 掉到 2158 格，t=6840 回到 6512 格后被围到最后。给队友捐了 33 笔（成交 31，到账 184 万）。t=11430 重新接壤（nb=1），t=11510 最后一个阵亡（第 6 名）。",
            chain=["t=2160 5606 格 / 8775 兵", "t=6570 2158 格", "t=6840 6512 格", "t=11430 6512 格 / 519476 兵 / 敌邻 1", "t=11510 阵亡"],
            statementType="observed"),
        "Tomato": dict(cause="没有阵亡记录：日志停在本地拍 990（7372 格 / 17543 兵），之后没有任何行、也没有结果行。t=3400~4540 它还活着并在挨打（18 笔捐款以它为对象，到账 1657647，dAlly 读数 1~17）。之后去向不明。",
                       chain=["t=990 最后一条 HL-TICK", "t=3400~4540 收 18 笔捐款", "t=4540 之后没有记录"], statementType="observed"),
        "Ghana": dict(cause="没有阵亡记录：日志停在本地拍 1080（9800 格 / 47157 兵）。t=3060~4710 收 6 笔捐款（到账 403170）。之后去向不明。",
                      chain=["t=1080 最后一条 HL-TICK", "t=3060~4710 收 6 笔捐款"], statementType="observed"),
        "Palmyra": dict(cause="没有阵亡记录：日志停在本地拍 990（9088 格 / 33829 兵）。t=4015~4875 收 11 笔捐款（到账 916605，dAlly 读数 0~19）。之后去向不明。",
                        chain=["t=990 最后一条 HL-TICK", "t=4015 dAlly=0", "t=4015~4875 收 11 笔捐款"], statementType="observed"),
        "SmurfAccount": dict(cause="没有阵亡记录：日志停在本地拍 990（6577 格 / 27262 兵）。t=3630~4835 收 8 笔捐款（到账 711515）。之后去向不明。",
                             chain=["t=990 最后一条 HL-TICK", "t=3630~4835 收 8 笔捐款"], statementType="observed"),
        "SonHeungMin": dict(cause="没有阵亡记录：日志停在本地拍 1170（8882 格 / 48251 兵），没有结果行，也从没出现在别的号的捐款或戳刺日志里；队号不明。",
                            chain=["t=1170 最后一条 HL-TICK"], statementType="observed"),
    },
    sideRoomDeathNotes={
        1: {
            "Dahomey": dict(
                cause="5181 格的小号夹在两个更富的 T3 真人中间。服务器拍 1512 之后 0 条指令：对真人的留底 safe 在每个追踪点都高过它的全部余额（t=2000 195812 对 143888，t=2800 606740 对 206414），"
                      "报价也始终高于 worth（t=2800 🇱🇾🥵 每格 140.7 对 53.6）。t=2647 引擎把空壳 Türkiye 的 370931 兵交给了 🇱🇾🥵（余额 378378→749309）。"
                      "t=2340 起被 🇱🇾🥵 吃 5569 格（对方耗兵 619077）、被 Hetos [EU] 吃 924 格（167003），自己的余额被打掉 385877；t=2933 阵亡，身上还压着两家 142310 兵。挨打时不能捐（L4385），同队编队号 BlackRock 当时密度 32。",
                chain=["t=1440 峰值 5315 格", "t=1512 最后一条指令（t=1315 的旧单子落地，吃掉 AI456）", "t=2160 Hetos [EU] 试探", "t=2340 🇱🇾🥵 开打", "t=2647 空壳赠兵 370931→🇱🇾🥵",
                       "t=2760 4547 格 / 310595 兵（密度 68.3）", "t=2790 3465 格 / 207133 兵", "t=2880 2054 格 / 93761 兵", "t=2933 阵亡"],
                statementType="observed"),
        },
    },
    decisions=[
        dict(id="D01", t="0~90", bot="房间 1：BlackRock / Dahomey", decision="后端协调器给 20 个名字排点（只有 2 个在这个房间），18 次重解每次换点；两个号各收到 14 条指派，引擎落点都是第 13 条，最后一条没执行。",
             codePath=f"{C110}: Policy.chooseSpawn L4007-4064（__hlSpawnReq 上报 → __tsbAssignedSpawn 下发）；src/strategy/spawn-coordinator-c110.mjs L1205（K = bots.length，按登记的全部号求解）",
             verdict="error", patternId="NEW-SP-06", evidence=["spawncheck [PA][PC]", "L8648332 / L8648455 / L8648475：Solved 20 bots，名单含房间 0 的号和不在任何房间的 Zenitsu、Florida Man、Wallachia、Lusitania、HighPing",
                                                               "L8648453-8648454：第 13 条 (38,760) / (466,902)；L8648462 / L8648468：最后一条 (740,732) / (620,356)"],
             statementType="observed"),
        dict(id="D02", t="270~630", bot="房间 1：BlackRock / Dahomey", decision="开局按周期扩张：(270,630] 人均吃空地 2289 格（其它真人 1924），吃人机 232 格（其它真人 99）。",
             codePath=f"{C110}: Policy.act L4781+（开局 DP 周期出手，HL-OPENING）", verdict="good", patternId="NEW-OP-G1",
             evidence=["harvest：窗口 (270,630]", "truth [TD]：t=630 BlackRock 3350 格、Dahomey 2270 格", "lagstats [LB]：执行拍 0~540 时延中位 15 拍、无效 0"], statementType="observed"),
        dict(id="D03", t="540~1800", bot="房间 1：BlackRock / Dahomey", decision="客户端落后服务器 77~424 拍时照常在旧局面上决策；同目标 15 拍冷却一过就重发，114 条陆攻 + 发船里 48 条是重发，补拍时 7~8 条一起落地。",
             codePath=f"{C110}: Strategy.send L526-540；文件头 L19-31", verdict="error", patternId="NEW-EX-01",
             evidence=["truth [TG]：BlackRock 陆攻 69 条里没生效 25、叠加 14，重发串 12 个 / 多发 30 条；Dahomey 42 条里没生效 13，多发 18 条",
                       "lagstats [LB][LC]：执行拍 1260~1800 时延中位 197 / 最大 424，陆攻无效 61%；同拍 7 条 1 次、8 条 4 次",
                       "truth [TG]：BlackRock t=1274 / 1407 / 1519 各 5~7 条打空地的单子同拍落地，全部无效"], statementType="observed"),
        dict(id="D04", t="1596~1624", bot="房间 1：BlackRock", decision="两批各 3 条过期陆攻打 Player 582（T1）：本意各占余额 28% / 27%，落地时实发 60% / 57%（115120 + 43875 兵），t=1530~1710 领土 10797→18971 格，约 18 兵/格。"
                                                                    "代价是密度掉到 1.4~2.8，Player 676（T3）吃回 1314 格。这是它整局最便宜的一笔地，却不是策略本意。",
             codePath=f"{C110}: Strategy.send L526-540（pct 落地时按当时余额折算）；Policy.buyLand L5250+（本意的出兵量 chunk / avail）", verdict="unclear", patternId="NEW-IO-03",
             evidence=["truth [TG]：t=1596 ×3 pct=[281,259,270]，192336→实发 115120（60%），首条本意 28%；t=1624 ×3，76840→43875（57%）",
                       "truth [TK]：1530-1620 余额 165589→76840、10797→14100 格；1620-1710 76840→53378、14100→18971 格",
                       "truth [TD]：t=1710 密度 2.8，身上压着 Player 676 的 15435 兵；t=1980 17657 格"], statementType="observed"),
        dict(id="D05", t="1370~1512", bot="房间 1：Dahomey", decision="贴着 0 兵的 AI456（518~568 格，吃光只要 242~368 兵）不出手：防人机留底 sb 取了同队真人 CØLØSSΛL 的余额（155529~179971，自己只有 4.5~5.4 万）。"
                                                                    "t=1512 AI456 被吃掉，靠的是一条 t=1315 发出、晚了 197 拍才落地的旧单子。",
             codePath=f"{C110}: Policy.buyLand L5322 → Policy.safeAt L4524-4541 → safeAt L2744-2754 → safeFinite L2532-2541（sb 取邻居里最高的余额）", verdict="error", patternId="NEW-EC-05",
             evidence=["shadowcmp [SH][SJ]：Dahomey t=1370~1480 被 sb 挡；t=1500 原因 safe:sb", "trshow shadow_tr1.json Dahomey t=1500：余额 53546、sb=179971，AI456 568 格 / 0 兵 need=368，avail=−55610",
                       "truth --cmds Dahomey：t=1512 陆攻→AI456（影子决策拍 1315）"], statementType="observed"),
        dict(id="D06", t="1512~2933", bot="房间 1：Dahomey", decision="1421 拍没有一条指令：对真人的留底 safe =（最富真人邻居余额 − 1.5×领土）÷1.78，从头到尾高过自己的全部余额，对谁都出不了手；挨打时捐款函数直接返回。"
                                                                    "余额 53546→310595（t=2760）之后随地一起被打掉 385877。",
             codePath=f"{C110}: Policy.buyLand L5250+（keep = max(keep, safe)，avail = B − fee − keep）；Policy.safeAt L4524-4541 / safeAt L2744（killKeep）；tryDonateToTeammate L4385（myHumanInAtk>0 即返回）；"
                      f"Policy.peerAggressor L4586-4625（bal[q]+inc ≤ 1.6×B 才算反击对象）",
             verdict="error", patternId="NEW-DF-04",
             evidence=["trshow shadow_tr1.json Dahomey：safe / 余额 = t=1600 140683 / 67477，t=2000 195812 / 143888，t=2300 291590 / 204274，t=2600 456412 / 255024，t=2800 606740 / 206414，t=2900 634496 / 92012",
                       "t=2800：Hetos [EU] 余额 1085194 →（1085194 − 1.5×3465）÷1.78 = 606739；🇱🇾🥵 报价 c=140.7、worth=53.6",
                       "truth [TE]：←🇱🇾🥵 丢 5569 格，对方耗兵 619077，自己余额被打掉 303532；←Hetos [EU] 丢 924 格，167003，82345",
                       "truth [TM]：t=2647 Türkiye~（T3 空壳）→🇱🇾🥵 到账 370931，余额 378378→749309"], statementType="observed"),
        dict(id="D07", t="1800~3690", bot="房间 1：BlackRock", decision="两个真人邻居（Player 582 T1 13291 格、Player 676 T3 15591 格）都在囤兵，报价一直是 worth 的 4 倍左右（t=1800 23.7 对 5.9，t=3500 342.9 对 82.8）→ 价位门槛 break；"
                                                                    "t=3580 超软上限后换成拥挤门槛（要 B ≥ 1.50×100×领土）继续挡。1890 拍 0 条指令，余额 71712→2040130。两个邻居这段时间领土也没动。",
             codePath=f"{C110}: Policy.buyLand L5250+（c ≥ worth 且 c ≥ cheap 且 !over → break；isCrowdedHard：hardCapMult 1.50）；Policy.offers L5170-5194（baseHard：dq > 1.08×dMe 且 Bq ≥ 0.70×B）；winRatio L2885",
             verdict="unclear", patternId="NEW-EC-02",
             evidence=["trshow shadow_tr1.json BlackRock：t=1800 c=23.7 / worth 5.9；t=2500 85.7 / 23.3；t=3000 176.2 / 40.7；t=3500 342.9 / 82.8；t=3600 over=True、isCrowdedHard=True",
                       "truth [TD]：t=1980~3600 17657 格不动，接壤 Player 582 307 格、Player 676 70 格；trshow：Player 582 13291 格（t=1800~3700 不变）、Player 676 15570~15591 格",
                       "harvest：(1800,3600] 其它真人人均从真人手里拿 4092 格（42.0~101.6 兵/格），我方 0 格", "top：t=3600 头部真人密度 41~101，BlackRock 105"], statementType="observed"),
        dict(id="D08", t="3710~3717", bot="房间 1：BlackRock", decision="Player 582 的密度不再高出自己 8% 时拥挤门槛松开，按『超软上限留 0.9×100×领土』放出 48 万兵打它（T1 正在崩：23.9%→0）。之后 t=4760 / 5019 / 5166 / 5173 又打了 4 次，"
                                                                   "t=3717 之后从 Player 582 手里拿到约 8400 格，自己从 17657 格长到 25596 格（t=5220）。",
             codePath=f"{C110}: Policy.buyLand L5250+（over 时 keep = min(keep, overKeepMult×100×领土)，hold 档 0.9）", verdict="good", patternId="NEW-AT-G2",
             evidence=["shadow --trace BlackRock:3710：avail = 2093381 − 24531 − 1589130 = 479720；truth --cmds：t=3717 陆攻→Player 582 480414",
                       "truth --cmds BlackRock：t=4760 900030（余额 2633231，密度 139.5）、t=5019 485634、t=5166 658330、t=5173 166296，都打 Player 582",
                       "truth [TC]：T1 23.9%（t=3600）→10.1%（4500）→0（5220）；truth [TD]：BlackRock t=5220 25596 格"], statementType="observed"),
        dict(id="D09", t="3990~4249", bot="房间 1：BlackRock", decision="两次各 48 万左右的陆攻打 Player 676（T3，密度比自己高）：整局从它手里只拿到 1274 格，耗兵 608886，每格 477.9 兵；反过来被它吃走 6543 格。",
             codePath=f"{C110}: Policy.buyLand L5250+（over 之后跳过价位门槛，按 keep 放兵）", verdict="error", patternId="NEW-AT-03",
             evidence=["truth --cmds BlackRock：t=3990 陆攻→Player 676 483081；t=4249 →Player 676 465294", "truth [TE]：→Player 676T3 1274 格 耗兵 608886（477.9/格）；←Player 676T3 丢 6543 格",
                       "truth [TD]：t=3870~4410 领土 18272→18871 格，密度 104~110"], statementType="observed"),
        dict(id="D10", t="1890~2250", bot="房间 0：Satoshi / Portugal / Golden Horde / GalaxyBrain / Lannes / Brittany / Dzungar", decision="落后服务器几百拍时，同目标 15 拍冷却一到就把同一条陆攻再发一遍；积压的单子在追平时成批落地，每条按当时余额的比例扣兵，七个号在 450 本地拍里清仓。",
             codePath=f"{C110}: Strategy.send L526-540；文件头 L19-31", verdict="error", patternId="NEW-EX-02",
             evidence=["logstats [QA]：7 起清仓，最密的 360 拍窗里 7 个号", "noeffect [NA][NB]：1080~1890 的 203 条指令 107 条没生效；Portugal 清仓前累计 28 条没生效、GalaxyBrain 18、Dzungar 13、Satoshi 8",
                       "clockskew [KA]：房间 0 多落后 333 拍（本地拍 ≈1323），本地拍 ≈2022 追平", "truth [TG]（房间 1 实证）：同一机制下本意 28% 的单子实发 60%"], statementType="inferred"),
        dict(id="D11", t="3060~4875", bot="房间 0：EnPassant / Lannes / Brittany / Golden Horde", decision="给 4 个日志早已停掉的 T3 号捐了 43 笔（救援 35、盈余 8）：到账 3688937、税 2408321。受捐方读数里的密度 0~19，捐进去的兵没有留下来。",
             codePath=f"{C110}: tryDonateToTeammate L4419-4445（救援）/ L4460-4489（盈余）；isOurSquadBot L3973（只查名字池，不查对方是否还由策略控制）", verdict="error", patternId="NEW-DN-04",
             evidence=["donfit [FC]：Tomato 18 笔 1657647 / 税 969791；Palmyra 11 笔 916605 / 653604；SmurfAccount 8 笔 711515 / 460081；Ghana 6 笔 403170 / 324845",
                       "L8648906 t=3840 Golden Horde→Tomato dAlly=1；L8648910 t=3865 dAlly=12；L8648931 t=4015 Golden Horde→Palmyra dAlly=0",
                       "digest [B]：这 4 个号的 HL-TICK 停在 t=990~1080，没有结果行"], statementType="observed"),
        dict(id="D12", t="4040~10660", bot="房间 0：Portugal 等", decision="捐款冷却 18 拍，短于指令时延：前一笔还没扣款，同一个号又对同一人捐一笔，两笔都成交。24 笔连发多付到账 3763031 + 税 1711034。",
             codePath=f"{C110}: tryDonateToTeammate L4372（g.t − lastDonateTick < 18 才拦）", verdict="error", patternId="NEW-DN-10",
             evidence=["donfit [FA]：连发 24 笔；成交的 113 笔里 25 笔发令 20 拍后还没扣款，时延上界中位 55 拍", "donfit [FB]：Portugal 11 笔连发、Lannes 7、Brittany 4、Golden Horde 1、EnPassant 1",
                       "L 行：Portugal t=10240 myBal=1575585、t=10260 myBal=1615219（余额没少反而多了，第一笔还没落地）；t=10710 快照密度 49.9"], statementType="observed"),
        dict(id="D13", t="4040~10660", bot="房间 0：Portugal", decision="被围后密度一到 78 就按固定比例 185/1024 捐给 Dzungar，连税付出 24.3% 的余额：捐后密度中位 58.6、最低 44.7，35 笔里 30 笔捐完低于同一函数自己用的留底 68。",
             codePath=f"{C110}: tryDonateToTeammate L4380-4388（coastGuardFloor 68×领土、maxSafePct）对 L4488（pct = boxedIn ? (dMe>110 ? 280 : 185) : 153，没有用 maxSafePct）", verdict="error", patternId="NEW-DN-11",
             evidence=["donfit [FE]：Portugal 35 笔，发令时密度中位 79.7，捐后中位 58.6 / 最低 44.7，<68 的 30 笔、<55 的 10 笔；Lannes 16 笔里 10 笔、Brittany 5 笔里 5 笔捐后 <68",
                       "HL-DONATE：Portugal 35 笔里 24 笔的 dMe 是 78~80（68×领土的留底乘 1.08 再留出 55/1024，正好是 77.6）；连发的第二笔读数比第一笔高 2", "digest [I]：Portugal t=10710 密度 49.9，t=11046 阵亡"], statementType="observed"),
        dict(id="D14", t="4040~9720", bot="房间 0：Portugal → Dzungar", decision="被围的 Portugal 把 35 笔、966.1 万兵输给同队的 Dzungar；Dzungar 从 9216 格长到 103429 格（占陆地 13.6%），是编队整局最大的号。代价是税 340.9 万（26%）。",
             codePath=f"{C110}: tryDonateToTeammate L4457-4489（boxedIn 且 dMe ≥ 55 → 盈余捐给同队编队号）", verdict="good", patternId="NEW-DN-G2",
             evidence=["donfit [FB][FC]：Portugal 35 / 35 成交，到账 9661249，税 3409018；收款方全是 Dzungar（t=4040~10660）", "digest [E]：Dzungar t=4230 9216 格 → t=8730 68811 → t=9720 103429",
                       "digest [J]：Portugal 112 条快照里 92 条被围"], statementType="observed"),
        dict(id="D15", t="5470~10820", bot="房间 0：EnPassant / Lannes → Golden Horde", decision="T3 的两个小号把 22 笔、240.7 万兵捐给 Golden Horde；Golden Horde 从 19180 格（t=4770）长到 82308 格（t=11070），活到 t=11403。",
             codePath=f"{C110}: tryDonateToTeammate L4419-4445 / L4457-4489", verdict="good", patternId="NEW-DN-G1",
             evidence=["donfit [FC]：Golden Horde 收 22 笔（Lannes 14、EnPassant 8），到账 2407428，税 940092（t=5470~10820）；另有 5 笔定不了", "digest [E]：Golden Horde t=4770 19180 格 → t=5400 33241 → t=9000 60461 → t=9450 65839", "digest [N]：t=5400~5490、t=8460~8550 的额外入账与捐款对上"],
             statementType="observed"),
        dict(id="D16", t="9555~9655", bot="房间 0：Golden Horde", decision="被围、密度 130，按固定比例 280 / 280 / 185 / 280 / 185 给正在崩的 EnPassant 连捐 5 笔：4 笔成交，到账被受捐方的 150 倍上限夹到 191.6 万，税按自己的余额全额收 181.8 万；EnPassant 27 拍后阵亡。",
             codePath=f"{C110}: tryDonateToTeammate L4460-4489（bestAlly 打分 (outAtk+inAtk)/500 + (135−dAlly)×3；不看收款方剩余容量）；{SIM}/game.js L340-425", verdict="error", patternId="NEW-DN-12",
             evidence=["donfit [FD]：t=9555 没成交；t=9575 到账 1188729 / 税 544845；t=9605 176221 / 414495；t=9625 332213 / 464276（连发）；t=9655 218627 / 394803（同 pct 的单子归属按『新单先到』定，合计不受影响）",
                       "EnPassant 的容量（150×领土 − 余额）：t=9540 1082779，t=9630 72545", "digest [I]：EnPassant t=9682 阵亡；Golden Horde 余额 8519034（t=9540）→6313118（t=9720）"], statementType="observed"),
        dict(id="D17", t="5020~10740", bot="房间 0：GalaxyBrain（T1）/ Golden Horde（T3）", decision="跨队协防戳刺 17 次，每次约 10% 余额，对象都是 T2 的真人（[FR]、Player 631、Player [og]69）：GalaxyBrain 估计出兵 137.8 万，Golden Horde 326.6 万。"
                                                                              "Golden Horde 最后 3 次（t=10530~10740，209 万）是为 GalaxyBrain 打的，GalaxyBrain t=10766 阵亡。",
             codePath=f"{C110}: tryDonateToTeammate L4446-4455（mainAttacker 接壤、dMe ≥ 65、25 拍冷却 → g.attack(102, mainAttacker)，跨队也打）", verdict="unclear", patternId="NEW-MT-02",
             evidence=["logstats [QC]：17 行全是跨队", "digest [H]：ASSIST 行 L8649053~L8649648", "没有录像，戳刺打掉了对方多少兵、被救的号少丢了多少地看不到"], statementType="observed"),
        dict(id="D18", t="8730~10170", bot="房间 0：GalaxyBrain", decision="T1 领先（56%~68%）时，身边只有 1 个 T2 邻居，1440 拍没有一条指令，密度 91→150；余额三次顶在 150×领土上。之后 330 拍被这个邻居吃光。",
             codePath=f"{C110}: Policy.buyLand L5250+（isSoleHealthyBuffer：唯一真人邻居且 B < 1.28×100×领土 → 跳过；keep = max(keep, safeAt)）；Policy.offers L5156（humanNbs.length === 1）", verdict="error", patternId="NEW-EC-09",
             evidence=["logstats [QB]：硬上限快照 3 条（t=9540 / 9630 / 10170），有敌邻、密度 ≥95、不发指令的最长段 t=8820~10170（1350 拍）",
                       "HL-TICK：t=9540 bal=4129950 = 150×27533；t=10170 bal=3577200 = 150×23848；cmds=118 从 t=8730 到 t=10170", "digest [I]：t=10440 27554 格 → t=10710 10456 格，t=10766 阵亡"],
             statementType="observed"),
        dict(id="D19", t="9720~10800", bot="房间 0：Dzungar", decision="103429 格、1231 万兵的号在 1080 拍里丢掉 83134 格，只发了 2 条指令，密度一直 92~133；最后带着 270 万兵阵亡。",
             codePath=f"{C110}: Policy.peerAggressor L4586-4625（L4613：counterClearMode ≥ 5 时，压过来的兵 > 12%×B + 我已压上去的兵就跳过这个进攻者；L4614：bal[q]+inc ≤ 1.6×B）；"
                      f"Policy.offers L5103-5107（只有被认作 aggQ 才给防守折扣）；Policy.buyLand L5250+", verdict="error", patternId="NEW-DF-01",
             evidence=["logstats [QD]：Dzungar 9720→10871，103429→0 格，期间指令 2 条 / 发船 0 条，余额 12307936→2700420", "HL-TICK：t=9900 cmds=112、t=10170 cmds=113，之后到 t=10800 不变",
                       "结果行：T1 56.2%（t=9682）→79.3%（t=10871）"], statementType="observed"),
        dict(id="D20", t="2340~4950", bot="房间 0：Brittany", decision="9558 格、1 个敌邻，停了 2610 拍（密度 33→93），兵只通过捐款出去（14 笔，其中 10 笔给了断流的号）；t=4950 起 350 拍内被 [FR] 吃光，阵亡时还有 29.6 万兵。",
             codePath=f"{C110}: Policy.buyLand L5250+（isSoleHealthyBuffer / 价位门槛）；tryDonateToTeammate L4369+", verdict="error", patternId="NEW-EC-02",
             evidence=["digest [E][J]：Brittany t=2340~4950 领土 9558 不变", "donfit [FB]：Brittany 日志 14 笔、成交 11，到账 1000939、税 467646", "digest [I]：t=5040 7865 格 → t=5220 2676 格 / 295700 兵 → t=5302 阵亡"],
             statementType="observed"),
        dict(id="D21", t="1530~2160", bot="房间 0：EnPassant / Brittany", decision="被围后连续下船单（EnPassant 每 180 拍 6 条），但客户端落后、船单当时没有生效：EnPassant t=1530~1980 记了 14 条船、Brittany t=1260~1620 记了 12 条，余额一兵没少；"
                                                                           "追平时成批落地——EnPassant t=1980~2160 一窗少掉 494842（余额 392906→26181，领土 14497 没涨），Brittany t=2070~2160 没发任何指令、余额 562418→58610（之后领土 8185→9558）。",
             codePath=f"{C110}: Policy.act L4923（本拍没有别的指令 → idleBoats L4979-5006 → boatOut L1035-1050；boatEvery 60、maxBoats 2 只看本地的 g.boatCount）", verdict="unclear", patternId="NEW-EX-02",
             evidence=["logstats [QE]：EnPassant 1620~1800 / 1800~1980 各 6 条船、少掉的兵 0；1980~2160 6 条船、少掉 494842（窗前余额的 126%）", "HL-TICK：Brittany cmds 43（t=1260）→55（t=1620）之后到 t=2430 不变，boats 0→12；t=2070 562418 兵 → t=2160 58610 兵",
                       "digest [F]：DROP30 归因 EnPassant BOAT、Brittany PASSIVE-LOSS（窗内 0 条指令）", "没有录像，船去了哪、落在谁身上看不到"], statementType="inferred"),
        dict(id="D22", t="7650~9450", bot="房间 0：EnPassant", decision="被围（nb=0、中立 0）的 1800 拍里发了 30 条船，约每 60 拍一条；新增指令全是船的 11 个快照窗（23 条船）少掉 1037536 兵，整段领土只从 15040 到 15181（+141 格）。"
                                                             "典型一条船少掉余额的 3.3%~3.6%（手续费就占 3.125%），换来 2~13 格。",
             codePath=f"{C110}: Policy.idleBoats L4979-5006（L5004：有邻居时 maxEff = boatFee×minNbPrice，没有邻居时 maxEff = Infinity）→ boatOut L1035-1050（中立落点：船上兵 = 3×size+300，另付余额 32/1024 的手续费）；参数 boatEvery 60、boatFee 1、maxBoats 2",
             verdict="error", patternId="NEW-SE-05",
             evidence=["logstats [QE]：EnPassant 总船数 58，被围时发的 48 条；t=8010~8190 3 条船少掉 89550（11%），15108→15134 格；t=8190~8370 3 条 105049，15134→15147；t=8550~8730 3 条 107892，15155→15162；t=9180~9270 2 条 389394（32%），15177→15179",
                       "同一口径下 Portugal 6 条船少掉 775853 兵、+242 格（t=9630~9720 一条船 481559，领土没变）；Lannes 4 条 192506 兵、0 格",
                       "out/params-c110.json：boatFee=1、idleCap=1.25、boatEvery=60、maxBoats=2、boatFood=1、botMax=60（boatFood 有 60 兵/格的价位上限，idleBoats 在没有邻居时没有）",
                       "没有录像：船上的兵最后落在哪看不到，只能看到余额少了、地没涨"], statementType="observed"),
        dict(id="D23", t="4140~4680", bot="房间 0：Dzungar", decision="只有 1 个敌邻、密度 135 时改走海路：540 拍里的 9 条指令全是船，领土 9409→19227 格（之后 t=5400 22421 格）。这是它从 1 万格长到 10 万格的第一步，Portugal 的捐款同时开始到账（t=4040 起）。",
             codePath=f"{C110}: Policy.act L4923 → idleBoats L4979-5006（L4996：有邻居时余额 ≥ idleCap×100×领土 才发船）/ boatFood L5536+；HL 日志不区分是哪条发船分支",
             verdict="good", patternId="NEW-SE-G1",
             evidence=["logstats [QE]：Dzungar t=4140~4230 2 条船、4230~4320 1 条、4320~4410 2 条、4410~4500 1 条、4500~4590 2 条、4590~4680 1 条，每窗 Δcmds == Δboats",
                       "HL-TICK：领土 9409（t=4140）→9216→10017→10444→12957→17054→19227（t=4680）", "donfit [FC]：Portugal→Dzungar 第一笔在 t=4040"], statementType="observed"),
    ],
    newPatterns=pick("NEW-IO-08", "NEW-IO-09", "NEW-IO-10", "NEW-SP-06", "NEW-DN-10", "NEW-DN-11", "NEW-DN-12", "NEW-DN-G2", "NEW-EC-09", "NEW-DF-04",
                     "NEW-SE-05", "NEW-SE-G1", "NEW-AT-G2", "NEW-EX-01", "NEW-EX-02", "NEW-IO-03", "NEW-DN-04", "NEW-MT-02", "NEW-DF-01", "NEW-EC-02", "NEW-EC-05", "NEW-AT-03", "NEW-SP-05"),
    lossArchetype="external",
    archetypeNote="房间 0：主机侧的问题先把编队打残——13 个号里 5 个的客户端在本地拍 990~1170 停掉（T3 的 9 个号只剩 5 个有人管），其余 8 个在追平服务器时被积压的旧单子清仓，Satoshi 因此阵亡。"
                  "局内的次要归类是 mid-collapse：编队在 t=9540 占到 31.1%（分在三个队里），之后 1350 拍三个大号高密度挨打不还手，掉到 10.6%。"
                  "房间 1（2 个号）是 outscaled：T3 从人机收割期就领先，T2 输在整队。",
    winnerNotes="房间 0：T1 获胜（最后一条结果行 99.3%），没有录像，只知道全队份额——t=2420 三队 30.4 / 35.2 / 33.0，T1 在 t=5302 还是最小的（28.4%），到 t=9682 翻到 56.2%，同期 T3 从 29.7% 掉到 9.6%、T2 从 41.0% 掉到 33.2%；"
                "之后 1800 拍吃完 T2（t=11046 清零）和 T3。T1 里有 1 个编队号（GalaxyBrain），峰值 27554 格，占 T1 的不到 7%，t=10766 被 T2 的 Player [og]69 吃掉。T1 的头部是谁、怎么长的，日志里看不到。"
                "房间 1（录像）：T3 获胜。t=900 三队 12.2 / 11.7 / 14.0，人机收割期 T3 拉开（t=1800 29.1 / 25.6 / 42.5），t=3600 23.9 / 26.0 / 50.0；T1 在 t=3600~5220 被吃光（地大半归 T3），t=6099 T3 92.9%。"
                "T3 的头部 [VOID] Migo 95642 格（t=5400）、europe4europea 74384 格；T3 的两个空壳（[T.C]ATATÜRK 3.95 万格、Türkiye 0.94 万格）按引擎规则把余额交给 T3 队友 38 次、387.7 万兵（[T.C]ATATÜRK 6 次 320.2 万），其中一笔 37 万给了正在吃 Dahomey 的 🇱🇾🥵。"
                "(1800,3600] T3 等其它真人人均从真人手里拿 4092 格，我方两个号一格没拿。",
    peerComparison="本包没有同房的另一支受控编队（sameMatchPeer 为空；rooms-discovery 里两个物理房间的 physPeers 都是空）。",
    teamSplitNotes="房间 0：13 个号没有战队标签，被分到 3 个队——T3×9（其中 4 个从 t≈1000 起断流）、T2×2、T1×1，SonHeungMin 不明。跨队的表现：互相之间没有捐款（引擎不允许），"
                   "有 17 次跨队协防戳刺（T1 的 GalaxyBrain 和 T3 的 Golden Horde 互相帮着打 T2 的真人）。三个队里各有一个编队大号（Dzungar 13.6%、Golden Horde 10.8%、GalaxyBrain 3.6%），"
                   "到终局它们分属互相敌对的三方：T1 获胜意味着 Dzungar、Golden Horde 必须被吃掉，GalaxyBrain 又先被 T2 吃了。编队号之间有没有直接交战，没有录像看不到。"
                   "房间 1：2 个号同在 T2，相距 451 像素，不接壤；编队内部互打 0 格（truth [TF]）。",
    ledgerExtra=dict(
        room0DonationsByKind=dict(rescue=dict(executed=44, delivered=3337449, tax=2357751), surplus=dict(executed=69, delivered=15093677, tax=6548901), src="scripts/donfit.py + out/B049/donfit.json"),
        room0DonationsToUnloggedBots=dict(count=43, delivered=3688937, tax=2408321, window="3060~4875", src="scripts/donfit.py [FC]"),
        room0Refires=dict(count=24, extraDelivered=3763031, extraTax=1711034, src="scripts/donfit.py [FA]"),
        room0ClippedIntoCollapsingAlly=dict(count=4, delivered=1949230, tax=1804586, donor="Golden Horde", ally="EnPassant", src="scripts/donfit.py [FD]",
                                            caveat="『夹小』是按捐出方余额序列反推的；捐出方同窗有别的开销时会偏（EnPassant t=8825→Golden Horde 那一笔被误判成夹小，收款方入账其实是足额的）"),
        room0Boats=dict(total=109, byBot={"EnPassant": 58, "Dzungar": 24, "Brittany": 12, "Portugal": 7, "Lannes": 5, "GalaxyBrain": 2, "Golden Horde": 1},
                        staleBoatOrders="EnPassant 14 条（t=1530~1980）、Brittany 12 条（t=1260~1620）发令时没有扣款，追平时成批落地",
                        boxedIdleBoats=dict(bot="EnPassant", window="7650~9450", boats=30, pureWindowBoats=23, pureWindowTroopsGone=1037536, terrBefore=15040, terrAfter=15181),
                        others="Portugal 纯船窗 6 条 775853 兵 / +242 格；Lannes 4 条 192506 兵 / 0 格；Dzungar t=4140~4680 9 条船 9409→19227 格，t=5400~6750 11 条船、7 个纯船窗少掉 2598746 兵、22421→24174 格",
                        caveat="『少掉的兵』= 按利息公式应有的余额 − 实际余额，窗内有捐款入账时会偏小；没有录像，船靠没靠岸、靠在谁身上看不到",
                        src="scripts/logstats.py [QE]"),
        room0CrossTeamPokes=dict(count=17, estTroops=4644349, src="scripts/logstats.py [QC]（按戳刺前一条快照余额 ×103/1024 估）"),
        room0Drop30ByClassNote="DROP30 53 段：DONATE 19、ATTACK-GAIN 12、LOST-LAND 10、SPEND-NO-LAND 7、BOAT 3、PASSIVE-LOSS 2（digest [F]，按旧的捐款判定归类）。SPEND-NO-LAND 的 7 段：Portugal t=1800~1890、Lannes t=2070~2160（下一窗回流 265709）属于清仓波；"
                               "Brittany t=3420~3510 / 3870~3960 其实是连发捐款（旧判定当成被拒）；GalaxyBrain 和 Golden Horde 同在 t=10170~10260 各花掉 135 万 / 308 万只多出 276 / 1145 格；Lannes t=10800~10890。",
        cardLikelyRejectedNote="对局卡的『疑似被拒 27/124』和 facts.py 旧口径的 REJ=31 都是只看发令 20 拍后那一条余额得出的；按余额序列拟合，旧口径判拒的 31 笔里 26 笔其实晚落地成交了，1 笔定不了，真正没成交的 4 笔"
                               "（Brittany→EnPassant t=2980 / 3000 / 3080，Golden Horde→EnPassant t=9555），另有 7 笔定不了。",
        room1Truth=dict(donationsExecuted=0, drop30=dict(windows=7, byCause={"陆攻": 4, "挨打": 3}, src="truth.txt [TK]"),
                        boats=dict(count=3, troops=246147, fees=61535, landedOnOwnLand=6564, landedOnTeammate=9214, neverLanded=230369,
                                   neverLandedNote="= 第 3 条船 226629（t=5747 发往空地，录像结束时还在海上）+ 前两条船在海上损耗的 3740", src="truth.txt [TL][TJ]；truth.py --cmds BlackRock"),
                        huskGifts=dict(count=38, delivered=3877485, allFromTeam=3, allToTeam=3, src="truth.txt [TM] + out/B049/resim.json huskGifts"),
                        resends=dict(landAndBoat=114, resent=48, src="truth.txt [TG]")),
    ),
    sideRoomExtra={
        1: dict(
            summary="2 个号都在 T2。BlackRock：过期单子的意外放大让它在 t=1596~1710 从 10797 格长到 18971 格，之后 1890 拍不动，t=3717 起随着 T1 崩盘吃邻居，活到最后（21864 格，T2 终局 6.9% 里它占 4.0%）。"
                    "Dahomey：5181 格的小号，留底高过余额、从头到尾出不了手，t=2933 被两个 T3 真人吃掉。T3 从人机期一路领先到 92.9%。",
            perCapitaNote="编队在线号人均领土 ÷ 全房在线真人人均：见 sideRooms[0].timeline[].truth.squadPerCapitaVsRoomActive。",
            lagTable="lagstats [LB]：执行拍 0~540 时延中位 15 / P90 20 / 最大 21；540~1260 77 / 163 / 208（陆攻无效 21%）；1260~1800 197 / 309 / 424（61%）；3500 之后 10 / 16 / 16（0%）。",
        ),
    },
    wentWell=[
        "房间 0 的『银行→前线』捐款链跑通了：被围的 Portugal 给 Dzungar 输了 966.1 万兵，Dzungar 从 9216 格长到 103429 格（占陆地 13.6%）；Golden Horde 靠 22 笔 240.7 万长到 82308 格。编队在 t=9540 合计占到 31.1%。",
        "房间 0 开局正常：13 个号 t=900 合计 10.43%，全部在长；清仓那一波虽然不是本意，编队领土从 77010 涨到 107485 格。",
        "房间 1 的 BlackRock 活到终局（45 人里第 8 名），t=3717 之后踩着 T1 崩盘的节奏吃到 25596 格；两个房间里编队号之间没有录到互打（房间 1 真值 0 格）。",
        "房间 1 开局 (270,630] 人均吃空地和人机都高于其它真人（2289 对 1924、232 对 99）。",
        "余额序列拟合把 124 笔捐款定案到 113 成交 / 4 没成交 / 7 定不了；房间 1 的真引擎重演 67/67 条快照逐兵一致。",
    ],
    unknowns=[
        "房间 0 没有录像：谁打的 Dzungar / EnPassant / Golden Horde，T3 的野人和 4 个断流号的地是被谁、在什么时候吃掉的，T1 的头部是谁，都看不到。",
        "5 个断流的号到底是不是按引擎的『离开』规则被托管：只有间接证据（没有结果行；受捐时密度 0~19，像引擎空壳把余额打出去或转交）。引擎对空壳收款不查额度，所以捐款成交与否也区分不了。",
        "两个房间的客户端为什么在 14:31~14:34 同时变慢、5 个为什么停掉：只能排除策略自身耗时（HL-SLOW-TICK 最长 115 ms）。主机侧数据不在包里（猜测：同一台机器上开的客户端太多）。",
        "房间 0 的清仓波是旧单子成批落地——这是从三条日志侧证据（指令没生效、两房间对表、清仓后回流）加房间 1 的录像实证推出来的，房间 0 自己没有服务器拍可以逐条对。",
        "Dzungar、GalaxyBrain、Golden Horde 末段不发指令，是哪一道门槛在挡（留底 safeAt 高过余额、唯一缓冲、围城收缩、还是进攻者太强不算反击对象）：房间 0 跑不了影子，只在房间 1 的 Dahomey 身上核实了『留底高过余额』这一条。",
        "协防戳刺的效果：17 次、估计 464 万兵，被救的号少丢了多少地、对方损失多少，没有录像算不出。",
        "donfit 的『夹小』判定在捐出方同窗有别的开销时不可靠；Golden Horde→EnPassant 那 4 笔的到账是按 Golden Horde 的余额序列反推的，量级可信、单笔可能有出入。",
        "房间 1 BlackRock 的第 3 条船（t=5747，船上 226629 兵 + 手续费 56657）到终局还没靠岸，去向不明。",
        "SonHeungMin 的队号。",
    ],
    mechanicsQuestions=[
        "捐款的税是捐出方余额的 64/1024（6.25%），和 pct 无关；到账先按 pct 算，再按收款方的剩余容量（150×领土 − 余额）夹小，税不退（game.js L340-425）。所以往快满的或正在丢地的队友身上捐，税占比可以超过一半——Golden Horde→EnPassant 4 笔税占 49%。",
        "收款方已阵亡、不是队友、到账 <1 或超额度时整单拒绝、不收税；t≥4284 或收款方是内置 AI / 已离开的空壳时不查额度（game.js，live-donation-check.txt）。这意味着给空壳捐款永远『成交』。",
        "离开的号由引擎当机器人托管（bots.js）：每个决策周期先打敌人 / 空地，没有可打的就把全部余额交给一个最近在打仗的队友（botDonate，同样收 6.25% 税、不查额度）。房间 1 里 T3 的两个空壳这样送出 387.7 万兵（38 次，全部给 T3）。",
        "余额硬上限 150×领土：到顶后利息全部截掉（GalaxyBrain t=9540~9630 余额一兵没涨）。软上限 100×领土之上利息已经在衰减。",
        "陆攻指令带的是『占余额的 pct/1024』而不是兵数：单子晚落地时按落地那一拍的余额折算，囤兵期余额翻倍，实发也翻倍（房间 1：本意 28% 的三条连发实发 60%）。",
        "挨打时丢的不只是地：守方余额按丢掉的格数成比例被打掉（Dahomey 丢 6493 格被打掉 385877 兵；Dzungar 丢 83134 格，余额 1231 万→270 万）。攻方每格的花费约是守方密度的 2 倍。",
    ],
    scripts=[
        "c136-review/agents/R08/scripts/facts.py B049 [--room 1]（多房间的包按房间拆；[C] 时间线对丢行的快照沿用前一条）",
        "c136-review/agents/R08/scripts/donfit.py B049（本局新写：用捐出方的余额观测序列逐段拟合，给每笔捐款定案——成交 / 夹小 / 没成交 / 定不了，时延区间、连发、[FE] 盈余捐后的密度）",
        "c136-review/agents/R08/scripts/noeffect.py B049 [--bot 名字]（本局新写：只看日志的『指令没生效』指标）",
        "c136-review/agents/R08/scripts/clockskew.py B049（本局新写：[KA][KB] 用日志行号给两个房间的本地拍对表，量出一个房间比另一个多落后多少拍；[KC] 用结果行的写入时间量每本地拍多少毫秒）",
        "c136-review/agents/R08/scripts/logstats.py B049（本局新写：[QA] 清仓事件、[QB] 顶上限空转、[QC] 协防戳刺估兵、[QD] 挨打不还手、[QE] 发船的纯船窗收支）",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/resim_r08.mjs B049；truth.py B049（房间 1 真值 [TA]~[TO]；--cmds / --bot）",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/shadow.mjs B049 --trace \"BlackRock:1650,...,3700;Dahomey:1500,...,2900\" --tag tr1；trshow.py out/B049/shadow_tr1.json <号>",
        "c136-review/agents/R08/scripts/shadowcmp.py / lagstats.py / harvest.py / top.py / spawncheck.py B049（房间 1）",
        "c136-review/agents/R08/scripts/build_review.py B049（本局改成按房间出：主房间正文 + sideRooms；录像只并进它所属的房间）",
    ],
    confidenceOverall="medium",
    confidenceNote="房间 1（2 个号）的所有数字来自逐兵对上的真引擎重演和影子追踪，可信度高。房间 0（13 个号，本文正文）只有日志：各号自己的地、兵、指令数、捐款和结果行的全队份额是直接读数；"
                   "捐款的成交与到账是余额序列拟合（115 笔里 8 笔『夹小』的金额可能有出入）；清仓波的成因、断流号的状态、末段不还手的原因是推断或没查清，所以整体标 medium。",
)
