# B015 人工分析部分。一个物理房间，8 队、53 个出生的真人；编队 11 个号分在 5 个队（T2×2、T4×1、T5×3、T7×2、T8×3）。
#   真值：scripts/resim_r08.mjs 用自带录像逐拍重演到 t=13176（8 队局内置 AI 也分队：AI p 属于 1+(p%8) 队），487/487 条 traj 快照地、兵都一致。
#   出处：out/B015/truth.txt [TA]~[TO]、shadowcmp.txt [SA]~[SJ]、lagledger.txt [GA]~[GG]、landcap.txt [KA]~[KF]、spawncheck.txt [PA]~[PC]、harvest.txt、perhead.txt [PH-A]~[PH-C]、
#         bursts.txt [BA]、lagstats.txt [LA]~[LC]、squadfog.txt [HA]~[HI]、flow.txt、donfit.txt、donrej.txt、top.txt、digest.txt；逐拍追踪 shadow_tr1/2/3.json（trshow.py 打印）。
#   L 号 = bundles/B015/in_game.log 每行开头的原始行号。「执行拍」= 录像里的服务器拍；「决策拍」= 影子（按真值逐拍重走策略）做出同一决策的拍。
from patterns_catalog import pick

C110 = "src/strategy/v27-team-c110.js"
SIM = "src/sim/sim"

SPAWN = (f"{C110}: Policy.chooseSpawn L4007-4153（L4010-4020 squadIds = 自己 + 名字在名字池里的真人，不核对是不是本编队；自主分支 minSep = max(85, min(145, 0.14×对角线))；"
         "每个号在自己的客户端里各算各的，没有 [HL-SPAWN-BACKEND]）")
DRIVER = f"{C110}: 文件头 L2-47（驱动层 afterTick 包装：只有 450 ms / 8 拍的在途保护，没有时延检测）；Strategy.send L526-540（pct 在决策时按当时余额算好，同目标 15 拍冷却后可重发）"
ENG_ATK = (f"{SIM}/game.js attack L1263-1285（执行时才按当时余额×(pct+1)/1024 抽兵）/ redirectAttackToNeutral L858-869（目标出局后这一路改成打无主地；身边没有无主地就作废）"
           " / endAttack L1076-1080（没用上的兵原数退回）")
SB = (f"{C110}: winFloor L4542-4550（打人机前的留底 = max(价位底, dpKeep, sb)）→ safeFinite L2532-2541 / L2773-2784 → threatOf L464-490"
      "（sb 取的是共用同一个人机邻居的另一个真人的余额，不分是不是编队友、是不是队友）")
ANALYZE = (f"{C110}: analyze L420-448（L440：isProtectedSquadMate 为真的邻居不进 nb）；isProtectedSquadMate L3993-3996 → isOurSquadBot L3973-3976"
           "（只看名字在不在 SQUAD_POOL_SET，不核对是不是本编队的号）")
DON_HEAD = f"{C110}: tryDonateToTeammate L4369-4497"
DON_RESCUE = (f"{DON_HEAD} 的救援分支 L4423-4445（L4434 对方挨真人打且（进攻兵 ≥8% 余额 或 密度 <75）；L4436-4437 同队且自己密度 ≥ max(55, 对方密度+15) 就捐 min(maxSafePct, 155)，"
              "不看对方还剩多少地、撑不撑得住）")
DON_SURPLUS = (f"{DON_HEAD} 的盈余分支 L4462-4497（L4467 收款方必须是同队的 Boss 或名字池里的名字；L4469 对方密度 ≥132 才跳过；L4489 pct = 被围 ? (密度>110 ? 280 : 185) : 153，"
               "不看对方刚才是不是捐过来）")
BUY = (f"{C110}: Policy.buyLand L5250-5372（L5258-5260 worth = maxW×winRatio×max(自己密度, marketFloor×其他真人密度中位)；L5261 over = 余额 > 100×领土；"
       "L5267 最便宜的报价 ≥ worth 且没超软上限就整轮停；L5269-5273 唯一缓冲；L5279-5282 crowdedHard 要 1.26~1.50×100×领土；L5358-5360 可用兵 = 余额 − 手续费 − max(keep, safe)）")
SAFE = f"{C110}: Policy.safeAt L4524-4541 → safeAt L2744-2754（对真人的留底 =（最富真人邻居余额 − 1.5×领土）÷1.78；只在目标正在流血 / 快坍时封顶到 88×领土）"
COUNTER = f"{C110}: counterAttack L871-887（L650 counterK = 0、L825 只在 counterK > 0 时才调用——专门的反击分支是关着的；挨打时只剩 buyLand 的报价 / 留底两道闸）"
MINCMD = f"{C110}: Policy.buyLand L5363-5369（对非真人：x = min(可用兵, 1.25×need + 3×边界)，x < minCmd 就跳过）；minCmd = feeK×⌊12×余额/1024⌋"
BOAT = (f"{C110}: Policy.idleBoats L4979-5006（L4996 没有陆上邻居时 maxEff = Infinity）→ boatOut L1035-1051 → searchWater L1056-1115（L1104 跳过受保护的编队友）；"
        f"{SIM}/game.js boat 手续费 = 余额的 32/1024，和船上装多少兵无关")
ENG_DON = f"{SIM}/game.js donate L404-416 / transfer L388-401（手续费 = 捐出方余额的 64/1024，按全额余额收）/ receiverRoom L340-345（到账 ≤ 150×收款方领土 − 收款方余额）"
ENG_ELIM = f"{SIM}/game.js aliveTick L1298-1312（领土 ≤ 历史峰值的 1/4 就出局，剩下的地变成无主地、余额清零）"
ENG_WIN = f"{SIM}/game.js victoryTick L1398-1412（领先的队要占全部陆地才结束）/ teamHuntTick L1414-1435 / leaderHas L1437；归档引擎里没有『占到 64% 就结束』的规则"
ENG_TEAM = f"{SIM}/game.js isEnemy L266-268（同队不能打）；8 队局内置 AI 也分队（AI p 属于 1+(p%8) 队；按这个设定重演 487/487 条快照逐兵一致）"

R = dict(
    contextExtra=dict(
        replay="自带 replay.txt 录到 t=13176（比 end 行的 13175 多 1 拍）。scripts/resim_r08.mjs 逐拍重演 512 个玩家，487/487 条 traj 快照地、兵逐兵一致。",
        truthTeamSplit="真值分队：T2 = Aurelian、Panzergrenadier；T4 = Guts；T5 = Cataphract、Don、Luigi；T7 = Darius、System32；T8 = Kaiser、ProGamer99、Yi Sun-sin。"
                       "53 个出生的真人（8 队：7/7/7/7/7/7/6/7；另 2 个没出生），编队占人头 20.8%（11/53）；5 个队里各有 1~3 个号，彼此互为敌队。",
        builtInAiTeamed="8 队局内置 AI 也分队：AI p 属于 1+(p%8) 队，和它同队的真人不能打它（isEnemy）。t=600 时 451 个内置 AI 占 198734 格（陆地的 29.9%），t=810 涨到 54.5%。",
        namePoolCollision="Cascadia（7 号，T6，出生点 (384,897)）不是本编队的号，名字在 c110 第 1 行的 SQUAD_POOL_SET 里。各号的 [HL-SPAWN] 行写 squad=12（11 个号 + 它）；"
                          "isProtectedSquadMate 对它恒为真：不进任何号的 nb，全程没有一个号对它下过陆攻。",
        labelRenames="traj 标签中途换名：Kaiser>Senna>Konbaung>Halsey；Guts>Ryuk>404 Not Found>Bongcloud>Switzerland>Meiji>MobilePlayer>Orange；Cataphract>HighPing>Kutuzov>Celtic>Inosuke>Toungoo>ArchdukeCharles>Texas；"
                     "System32>Dzungar；Yi Sun-sin>NoLife>Pontus>Papal States>MrBeast；Aurelian>DarkKnight；Darius>PCMasterRace>GG_WP>CSA。本文一律用第一个名字。",
        fairSharePerCapita="本文的『人均比』= 编队在线号人均领土 ÷ 全房在线真人人均领土（0.97 @630、0.99 @900、0.71 @1260、0.61 @1500、0.62 @1800、0.76 @2250、0.64 @3060、0.60 @3960、0.69 @6300、0.44 @7020、0.34 @9000、0.05 终局）；"
                           "landcap 的恒等式用的是出生人头口径（编队 11 个号、其他真人 42 个，不剔掉线的），数值略有出入。『人头份额』= 20.8%。",
        notes="开局没有后端出生协调器（0 条 [HL-SPAWN-BACKEND]）；HL-TICK avgMs ≤1.16，HL-SLOW-TICK 343 行、最大 73.5 ms——策略计算本身不慢。",
    ),
    outcomeExtra=dict(
        endState="t=13175 结束（763 秒）：T5 64.24%（426843 格，其中 [JP]tukki 一个人 425358 格 / 6310 万兵）、T2 31.4%（[OG] Phoenix A* 208578 格）、T4 1.9%（Guts 12510 格 / 155.5 万兵）。"
                 "结果行 L8578289（Guts，over，第 3 名）、L8578290（Cataphract，won，第 6 名）。",
        squadFinal="活到终局 2 个：Guts（T4，12510 格）和 Cataphract（T5，1485 格 / 222750 兵，自 t=7920 起一直顶着 150×领土的硬上限）。"
                   "Cataphract 所在的 T5 获胜，T5 的地 99.7% 是野人队友 [JP]tukki 的；编队 3 个 T5 号里 Don 3919、Luigi 5362 阵亡。",
        primaryTeam="对局卡的主队 T8（Kaiser、ProGamer99、Yi Sun-sin + 野人 SONion🥀、Name、Player 47、Player 750）在 t=8640 到过全场第一 36.3%，随后 34.7%（9360）→18.7%（10440）→0%（11880）；"
                    "T8 的地主要是野人 SONion🥀 的（t=9000 129324 格）。",
        earlyEnd="录像最后一拍 T5 只有 64.24%，录像里 over=0；归档引擎的 victoryTick 要领先的队占全部陆地。对局为什么在这里结束，数据包里没有记录。",
    ),
    phases=dict(
        spawn=dict(
            window=[0, 350],
            facts=[
                "出生指派 110 行、全部是 [HL-SPAWN]（各号客户端自己算），没有后端协调器。每个号重选 4~13 次（中位 11），相邻两次的点中位相距 336 像素；"
                "Guts 的 11 条：(306,706)→(354,818)→(1474,114)→(1186,1058)→(1314,610)→(1474,114)→(962,1058)→(642,1058)→(1314,610)→(1506,882)→(1122,1058)。",
                "最后一条指派落地的只有 3/11（Kaiser、Panzergrenadier、Don）。另 8 个号的引擎落点是更早的某一条：Guts (1506,882) 对最后一条 (1122,1058)；Cataphract (1186,1058) 对 (1058,450)；"
                "System32 (1234,290) 对 (466,178)；ProGamer99 (642,1058) 对 (1006,534)；Luigi (978,1058) 对 (1506,882)；Yi Sun-sin (1314,1058) 对 (658,1058)；Aurelian (18,98) 对 (642,306)；Darius (1474,114) 对 (1314,610)。",
                "录像里编队每个号落地的出生指令中位 9 条（其他真人 2 条）；8/11 个号最后一次落地在出生期 50 步里的第 49~50 步。出生期开局时延 P50 12 拍——最后一两次改点发出时出生期已经结束。",
                "落点：没有同像素、没有 <40 像素的号对；最近编队友距离中位 230、最小 128（Cataphract–Yi Sun-sin）。5 个号排在地图下沿 y≈1058 一条线上（x=383、642、978、1186、1314）。",
                "按实际出生点的直线 Voronoi：编队名下 107568 格 = 16.2%，人头 20.8%（人均 0.78）；陆路口径 13.9%（0.67）。逐号中位 7476 格，其他真人中位 12594；6/11 个号在全房最低四分位（Yi 2390、Darius 3317、Panzergrenadier 5087、Aurelian 5134）。",
                "反事实（8 个号都挪到自己最后一条指派）：113358 格 = 17.1%（0.82），只多 5790 格；中位 9820，最低四分位 4 个。Darius +12143、Luigi +5293、Yi +4329、Aurelian +3791，System32 −7552、Don −6009；"
                "最后一条指派里 Cataphract / Don / ProGamer99 三个点互相只隔 97~109 像素。",
                "Cascadia（撞名野人）被各号算进编队：日志 squad=12、rankIdx 给它留了名次。",
            ],
            problems=[
                "各号各算各的出生点，反复改到出生期结束，8/11 落在旧点上（NEW-SP-05）。",
                "就算最后一条全落地，名下份额也只有人头的 0.82：差额主要不在『没落地』，而在各号自己挑的点（下沿一条线、角上、互相隔 100 像素左右）。",
                "Aurelian 落在左上角 (18,98)（它自己的第 5、11 条指派都是这个点），名下 5134 格。",
            ],
        ),
        opening=dict(
            window=[350, 900],
            facts=[
                "t=630 人均比 0.97（编队 4.56%）；t=900 0.99（8.72%），编队中位 5301 格、其他真人中位 5219。开局 76 条指令全部生效，时延 P50 / P90 / 最大 = 12 / 15 / 18 拍。",
                "(630,900] 人均有效陆攻 6.6 条（其他真人 4.5 条）；人均从内置 AI 手里拿 1612 格（其他真人 893 格）。按格追踪：600~750 全房真人吃到的『属于过内置 AI 的格』里编队占 44.0%，750~900 占 30.6%（人头 20.8%）。",
                "t=600 时贴着编队号的 31 个内置 AI（13003 格）：到 t=1500 被真人吃掉 11187 格，编队吃到 9406（84.1%）——贴着的基本吃到了。",
                "内置 AI 在 t=600 之后还在往无主地里长：29.9%（600）→54.5%（810）；(600,1800] 里属于过内置 AI 的格共 430905，是 t=600 那一刻的 2.2 倍。",
                "按名下份额算，t=630 编队拿到名下的 28%（其他真人 21%）、t=900 54%（39%）——起步比别人快，但名下的盘子只有别人的 0.74。",
                "t=810 Yi Sun-sin（3950 格）被异队编队友 Cataphract 一个号围住；t≈1170 Cataphract（5612 格）又被 Yi 和 Luigi 围住。",
            ],
            problems=[
                "门槛普查 630~900：贴着可打内置 AI 的 242 个号·点里 176 个全被挡（防人机留底 sb / 值不值门槛）。",
                "下沿一条线上的号互相围住：Yi、Cataphract 两个号在收割期开始前就没有出口。",
            ],
        ),
        midgame=dict(
            window=[900, 3600],
            facts=[
                "收割中途掉队：人均比 0.99（900）→0.71（1260）→0.61（1500）。按 150 拍窗，全房真人吃到的 AI 格里编队占 9.8%（900~1050）、5.7%（1050~1200）、6.9%（1200~1350）、6.9%（1350~1500）；"
                "(900,1260] 人均吃人机 1078 格对 3667 格，人均派出的兵 14318 对 38482，而 t=1260 人均余额相等（60970 对 60546）——兵在手里没出去。",
                "(600,1500] 属于过内置 AI 的格被真人吃掉 356305，编队 41736（11.7%），按人头应得 73950，差 32214 格。按接壤口径摊开：同队 AI 不能打 5868（18.2%）、门槛挡住 5709（17.7%）、迟到 6729（20.9%）、"
                "出手了被分走等 3599（11.2%）、贴不着 10309（32.0%）。",
                "门槛普查 900~1260：贴着可打 AI 的 201 个号·点里 153 个全被挡，其中 135 个卡在防人机留底 sb；sb 是谁的余额定的：敌队真人 59、同队编队友 39、同队野人 22、异队编队友 15；两个号互相把对方余额当底线的互锁 44 个。",
                "时延波 t≈900~1800：按 180 拍窗的时延中位 / P90 = 43 / 64（900~1079）、80 / 109、124 / 194、185 / 242（1440~1619）、162 / 229（1620~1799），1800 之后回到 13 拍。11 个号里 10 个的最大时延 ≥157 拍。",
                "600~1500 执行的陆攻 160 条里 29 条落地时目标已经出局：22 条被引擎改成打无主地（65934 兵）、7 条作废（本意 28559 兵）；按时到的落空 6%，晚 ≥35 拍的落空 38%。1500~3000：84 条里 16 条没生效。",
                "补拍成批只出现在编队号身上：一个服务器拍落地 ≥3 条的批，600~1500 有 7 批、1500~3000 有 14 批（7 批抽走余额 ≥50%），其他真人 0 批。Kaiser t=1778 一拍 9 条（决策拍 1560~1695）、Darius t=1708 一拍 9 条、System32 t=1722 一拍 8 条（5 条作废）。",
                "t=1700~2250 时延波尾声的便宜地：Guts 16.9 兵/格吃掉 365（11988 格），Kaiser 20.6 兵/格吃 Harris [MEME] 8815 格，Yi 3.9~8.1 兵/格 4455→17140 格；人均比 0.62→0.76，编队占地 18.20%（t=2430，全程峰值）。",
                "t=2250~3500 全队停手：10 个在线号 1250 拍合计 14 条陆攻 / 船（人均 1.4 条、派出 4.3 万兵；其他真人人均 4.4 条、36.2 万兵）；Kaiser、System32、Yi、ProGamer99、Luigi 0 条。编队占地 18.07%→15.31%，Kaiser 余额 13.7 万→114.3 万。",
                "Cascadia（撞名野人，T6）t=1440 起吃 Panzergrenadier 2834 格（50.3 兵/格），t=2160~3390 吃 ProGamer99 2132 格；两个号的 nb 里都没有它，没有一条反击。Panzergrenadier 1983 阵亡、ProGamer99 3389 阵亡（最后一条指令在 t=1981）。",
            ],
            problems=[
                "收割后半段（900~1500）掉队：门槛、时延、站位、同队 AI 四层叠加。",
                "补拍成批把一条 12%~26% 的本意放大成 63%~87% 的余额（NEW-IO-02 / NEW-EX-01）。",
                "中立地和人机吃完后，对真人的报价全部过不了 worth / safe 两道闸，全队停手 1250 拍（NEW-EC-04）。",
                "按名字保护的陌生人吃掉两个号（NEW-MT-04 / NEW-MT-06）。",
            ],
        ),
        endgame=dict(
            window=[3600, 13176],
            facts=[
                "t=3389~5362 连死五个：ProGamer99（3389）、Don（3919）、Aurelian（3966）、System32（4878）、Luigi（5362）；在线号 10→5，编队占地 17.03%（3060）→13.76%（5400）。",
                "Don（T5）是被 T8 的三个野人（Player 47 3414 格、SONion🥀 2458 格、Name 1570 格）和 T2 的 Phoenix A 吃掉的；T8 是 Kaiser、Yi 所在的队。System32（T7）被 T2 的 KOKUTEK、Phoenix A 和 T1 的 ✨ 吃掉。",
                "KOKUTEK t=4655 清仓去打 [JP]tukki，t=4750 剩 20129 格 / 2 兵；贴着它的 System32 有 698783 兵，对它的留底算出来 763470，没有出手；Kaiser 用 874432 兵吃到 10101 格（86.6 兵/格），[JP]tukki 吃到 13742 格。",
                "Kaiser↔Yi 互捐 18 笔：Yi→Kaiser 13 笔到账 443.1 万（税 184.1 万）、Kaiser→Yi 5 笔到账 250.5 万（税 104.1 万）；净流向 Kaiser 192.5 万，税 288.2 万。t=6090~6356 的 266 拍里双向各 170~184 万、税 134.6 万、净流量 14.0 万。",
                "Kaiser t=5362 起每次密度过 100 就把超出的兵放给 [JP]tukki：5 条共 3995975 兵拿 13177 格（303 兵/格），[JP]tukki 前后拿回 19741 格（318 兵/格）。t=5950 到峰值 37264 格；t=6622 之后 388 拍没有一条指令，"
                "t=6690 还有 3155820 兵（密度 94），330 拍里 33482 格被 [JP]tukki、✨、Phoenix A、Mongol Empire 花 792 万兵吃光，7010 阵亡。Yi t=7000 捐给它的 165102 兵（另付税 165102）10 拍后随它一起清零。",
                "Darius t=2880~5670 的 2790 拍只从 11283 格长到 11782 格，t=7908 阵亡（[JP]tukki 8137 格、✨ 6080 格）。t=7020 编队剩 4 个在线号、9.68%，人均比 0.44。",
                "Guts t=5760~6300 顶着硬上限 3486750 兵不动；t=10710 到峰值 34375 格，270 拍内被 [JP]tukki 吃掉 28070 格（8704907 兵，310 兵/格），剩 8414 格。Yi Sun-sin t=6300~9270 陆上邻居只有 Guts、队友 SONion🥀、Cataphract（都不能打），领土 25435~26772 不动，靠 6 条船打 ✨（552 兵/格）；t=9360~9930 ✨ 吃它 9716 格、它 693 拍没有一条指令；t=11267 阵亡（[JP]tukki 15783 格、✨ 12091 格）。",
                "赢家 [JP]tukki（T5 野人）t=3960 所在的队还是全场最小（6.7%），之后 12.3%（7020）→20.0%（9540）→33.7%（11340）→64.2%（13140）。它从编队号身上吃到 71731 格（Guts 28070、Kaiser 19741、Yi 15783、Darius 8137）。",
                "船：全程 159 条、装兵 1336.9 万、手续费 389.3 万；58 条的手续费比船上的兵还多（159.8 万）。Guts 40 条里 16 条是这种（装 5.1 万兵、手续费 93.8 万）。",
            ],
            problems=[
                "对真人出不了手：报价 ≥ worth 整轮停，或留底 safe 高过自己全部余额；挨打时同样出不了手（NEW-DF-01 / NEW-DF-04）。",
                "捐款来回倒手，税比净流量大一个数量级（NEW-DN-07）。",
                "每个号都在高密度、少邻居的状态下等到别人来买：五个死在 3389~5362，三个大号死在 7010~11267。",
            ],
        ),
    ),
    turningPoints=[
        dict(
            t0=900, t1=1500, shareBefore=0.99, shareAfter=0.61, shareUnit="编队在线号人均领土 ÷ 全房在线真人人均领土",
            what="人机收割的后半段掉队：全房真人在 900~1500 吃掉 29.6 万格内置 AI 的地，编队只拿到 7.3%（人头 20.8%）。",
            evidence=[
                "landcap [KD]：按 150 拍窗全房真人吃到的 AI 格 / 编队吃到：600~750 12322 / 5422（44.0%）；750~900 47836 / 14657（30.6%）；900~1050 77687 / 7594（9.8%）；1050~1200 80278 / 4565（5.7%）；1200~1350 80047 / 5503（6.9%）；1350~1500 58135 / 3995（6.9%）。",
                "landcap [KB]（按出生人头：编队 11、其他真人 42）：人均领土之比 = 人均名下份额之比 × 拿到率之比：0.98 = 0.74 × 1.33（630）；1.01 = 0.74 × 1.37（900）；0.70 = 0.74 × 0.95（1260）；0.61 = 0.74 × 0.83（1500）。站位那一项全程 0.74，掉下去的是拿到率。",
                "landcap [KF]：差额 32214 格 = 同队 AI 5868（18.2%）+ 门槛 5709（17.7%）+ 迟到 6729（20.9%）+ 出手了被分走 / 过闸没发 3599（11.2%）+ 贴不着 10309（32.0%）。逐号（门槛 / 迟到）：System32 2394 / 2715、Kaiser 980 / 2095、Don 2230 / 880、Guts 2 / 875。",
                "shadowcmp [SH]：900~1260 贴着可打 AI 的 201 个号·点里 153 个全被挡，135 个卡在 sb。Don 42 个点（970~1490）被 Phoenix A 的余额锁住：自己 47705 兵、sb 79356，面前的 AI 985 格 / 47 兵、吃光要 1166 兵。"
                "Kaiser 29 个点（880~1230，✨）；System32 29 个点（610~1140，同队野人 Player 814）；Luigi 26 个点（910~1260，同队编队友 Cataphract）；Cataphract 21 个点（720~1120，Luigi）。",
                "lagledger [GB] / shadowcmp [SF]：时延中位 17（720~899）→43→80→124→185（1440~1619）；600~1500 P50 / P90 / 最大 = 30 / 121 / 242 拍，46% 的指令晚 ≥35 拍。",
                "lagledger [GE]：600~1500 落地的 160 条陆攻里 29 条目标已经没了（22 条改打无主地 65934 兵、7 条作废 28559 兵）；时延 <35 拍的落空 6%，≥35 拍的 38%。",
                "perhead [PH-B]：(900,1260] 人均有效陆攻 4.5 条 / 14318 兵，其他真人 7.4 条 / 38482 兵；t=1260 人均余额 60970 对 60546。harvest：人均吃人机 1078 对 3667 格。",
                "top / truth：编队中位 5301→5622 格（900→1500），其他真人中位 5219→12227。",
            ],
            priorDecisions=[
                dict(t="0~350", bot="全队", decision="出生点各算各的：名下份额只有人头的 0.78，5 个号排在下沿一条线上，Yi、Cataphract 在 t=810~1170 就被编队友围住。", codePath=SPAWN),
                dict(t="610~1490", bot="Don / Kaiser / System32 / Luigi / Cataphract / ProGamer99", decision="打人机前的留底 sb 取了共用这个人机的另一个真人的余额，比自己全部余额还高，面前几十兵的人机不出手。", codePath=SB),
                dict(t="900~1800", bot="全队", decision="客户端落后服务器几十到两百多拍时照常在旧局面上决策、发令，没有『我落后了』的判断。", codePath=DRIVER + "；" + ENG_ATK),
            ],
            statementType="observed",
        ),
        dict(
            t0=3060, t1=5400, shareBefore=17.03, shareAfter=13.76, shareUnit="编队占全图陆地 %",
            what="停手囤兵之后连死五个号（ProGamer99 3389、Don 3919、Aurelian 3966、System32 4878、Luigi 5362），在线号 10→5。",
            evidence=[
                "真值指令账：(2250,3500] 10 个在线号合计 14 条陆攻 / 船（人均 1.4 条、4.3 万兵）；同期其他 30 个在线真人人均 4.4 条、36.2 万兵。编队密度 16.6（2250）→96（3870）。",
                "逐拍追踪（shadow_tr1/tr2，t=2100~4100）：每个真人邻居的结论都是 break:price>=worth、skip:avail<=0(safe) 或 crowdedHard。Don t=2100：Name 报价 32.7 < worth 43.8，但留底 328940 → 可用兵 −2846；t=3600 密度 111、留底 1940079 → 可用兵 −991685。",
                "ProGamer99 t=3100：𐱅𐰇𐰼𐰰🐺 身上压着 171035 兵，留底 477792→可用兵 −68103；t=1981 之后 1408 拍没有任何指令，5823（2250）→1431 格。truth：𐱅𐰇𐰼𐰰🐺 3136 格 / 560595 兵、Cascadia 2132 格。",
                "Aurelian：[SOLO]MINOLO 用 897342 兵吃 5518 格（t=1560~3960）；追踪里 break:price>=worth，t=3600 留底 803543 → 可用兵 −519588。",
                "System32：峰值 20154（2270~2700）。KOKUTEK 从 t=2760 起 8 次进攻买走 8942 格（2629057 兵，294 兵/格），System32 t=2170~3703 没有一条指令（追踪 t=2700 / 3300 / 3900：最便宜报价 70.6 / 100.7 / 138.4 对 worth 33.6 / 68.4 / 82.5）；"
                "t=4522 / 4536 反手 545887 兵只换回 1842 格（296 兵/格）。t=4750 KOKUTEK 20129 格 / 2 兵、报价 2.1 兵/格、吃光要 26095 兵；System32 余额 698783，留底 763470 → 不出手。阵亡时身上还有 230969 兵。",
                "Darius→System32 7 笔救援捐（t=4200~4851）到账 910459、税 557084；其中 4 笔比例 58~61 的到账约 7 万、税约 7.4 万。System32 t=4878 阵亡。",
                "Don 是被 T8 的野人吃掉的（Player 47 3414 格 / 789537 兵、SONion🥀 2458 / 789902、Name 1570 / 563066），T8 = Kaiser、Yi 的队；Luigi 被 Empire Monkey（3995 格）、𐱅𐰇𐰼𐰰🐺（3853）、Cascadia（2057）吃掉。",
                "truth [TC]：t=3060 八队 9.9 / 14.9 / 10.5 / 14.7 / 8.3 / 12.9 / 8.8 / 17.8；编队 17.03%→15.31%（3510）→13.54%（3960）→13.76%（5400）。",
            ],
            priorDecisions=[
                dict(t="2250~3500", bot="全队", decision="中立地、人机吃完后，对真人的报价都 ≥ worth 且没超软上限，buyLand 整轮停；余额涨到密度 96。", codePath=BUY),
                dict(t="2100~4850", bot="Don / ProGamer99 / Aurelian / System32", decision="对真人的留底按最富邻居的余额算，高过自己全部余额；挨打、对方只剩 2 兵时也一样。", codePath=SAFE),
                dict(t="1440~5070", bot="Panzergrenadier / ProGamer99 / Luigi", decision="Cascadia 按名字受保护，不进 nb：反击、买地、『正在挨真人打』都看不到它。", codePath=ANALYZE),
            ],
            statementType="observed",
        ),
        dict(
            t0=6300, t1=7920, shareBefore=14.83, shareAfter=8.40, shareUnit="编队占全图陆地 %",
            what="最大的号 Kaiser（35409 格）和 [JP]tukki 高价互啃 1260 拍后停手，330 拍内被四家吃光，Darius 随后阵亡；人均比 0.69→0.45，在线号 5→3。",
            evidence=[
                "真值指令账 Kaiser：t=5362 / 5621 / 5894 / 6440 / 6622 五条打 [JP]tukki 共 3995975 兵（拿 13177 格，303 兵/格）；t=6090 / 6216 / 6328 三笔捐给 Yi 共到账 1835644、税 762865；t=6622 之后 388 拍没有指令。",
                "逐拍追踪 Kaiser（shadow_tr4）：t=5350 密度 119.3（超软上限）→ 对 [JP]tukki 报价 194.2、留底 2879127、可用兵 801657 → 发；t=5500 密度 100.2、留底 3381443 > 余额 → 全部跳过；t=5900 / 6100 密度 99.4 / 97.9 → break:price>=worth；"
                "t=6300 密度 116.2、可用兵 41653 < 一次出手的下限 822679 → 跳过（✨ 已有 482927 兵压在它身上）。",
                "truth 逐对战损（整局）：[JP]tukki（T5）吃 Kaiser 19741 格 / 6286962 兵（t=5490 起）、✨（T1）8842 / 2781417（t=6330 起）、Phoenix A（T2）6264 / 1818788（t=6750 起）、Mongol Empire（T1）2374 / 712840。其中 t=6690~7020：33482 格、四家合计约 792 万兵（292 兵/格）。",
                "逐拍追踪 Kaiser t=6650~6950（shadow_tr3）：密度 92~95（没超软上限），所有真人邻居 break:price>=worth。",
                "Yi→Kaiser t=7000 比例 63：到账 165102、税 165102，Kaiser 当时 10461 格、10 拍后阵亡。",
                "Darius：t=2880~5670 只从 11283 长到 11782 格；追踪 t=6500 / 6700 / 7100 / 7500 break:price>=worth，6900 skip:soleBuffer，7000 留底 3762740 → 可用兵 −2475740，7300 留底 4995587 → 可用兵 −3788765。"
                "[JP]tukki 吃 8137 格 / 2274350 兵（t=6540 起）、✨ 6080 / 1738723（t=7290 起）；Darius 自己打 [JP]tukki 1012658 兵只拿 2131 格（475 兵/格）。",
                "truth [TC]：t=6300 T4 22.6 / T5 10.0 / T8 30.8；t=7920 26.2 / 15.0 / 31.8。编队 14.83%→9.68%（7020）→8.40%（7920）。",
            ],
            priorDecisions=[
                dict(t="6090~6356", bot="Kaiser / Yi Sun-sin", decision="盈余捐款来回倒手：266 拍里 Kaiser→Yi 3 笔、Yi→Kaiser 5 笔，双向各约 170~184 万，税 134.6 万。", codePath=DON_SURPLUS + "；" + ENG_DON),
                dict(t="5362~6622", bot="Kaiser", decision="只在密度过 100 时出手：把超出留底的兵放给 [JP]tukki，报价 194~232 兵/格也照发（实付 303 兵/格），一掉回 100 以下就停。", codePath=BUY),
                dict(t="6622~7010", bot="Kaiser", decision="挨四家打的 388 拍里没有一条指令：密度 92~95 不算超软上限，报价 ≥ worth 整轮停；专门的反击分支是关着的。", codePath=BUY + "；" + COUNTER),
            ],
            statementType="observed",
        ),
    ],
    deathNotes={
        "Panzergrenadier": dict(
            cause="t=1440 起被 Cascadia（T6，名字在名字池里的陌生真人）吃：20 个窗共 2834 格、对方只花 142580 兵（50.3 兵/格）。它的 nb 里没有 Cascadia（逐拍追踪 1650 / 1750 / 1850：真人邻居 0 个、没有报价），"
                  "同期把兵装船送走：1620~1710 四条船 50187 兵（余额 70191→20794），全程 13 条船 84688 兵、手续费 12992。𐱅𐰇𐰼𐰰🐺（T6）另吃 667 格。",
            chain=["t=1260 5612 格附近、被围", "t=1440 Cascadia 开始吃", "t=1620~1710 4 条船，余额 70191→20794", "t=1440~1800 nb=0 / neut=0 的 4 个快照窗丢 1360 格", "t=1983 阵亡"], statementType="observed"),
        "ProGamer99": dict(
            cause="最后一条指令在 t=1981（两条船 52062 兵），之后 1408 拍没有任何指令，5823（t=2250）→1431 格。𐱅𐰇𐰼𐰰🐺（T6）t=2130~3120 用 560595 兵吃 3136 格（179 兵/格），Cascadia t=2160~3390 吃 2132 格（433891 兵，它看不见）。"
                  "追踪 t=3100：𐱅𐰇𐰼𐰰🐺 身上压着 171035 兵，对它的留底 477792（封顶后 185680）→ 可用兵 −68103；另一个邻居 Empire Monkey break:price>=worth。",
            chain=["t=1981 最后一条指令", "t=2130 / 2160 𐱅𐰇𐰼𐰰🐺、Cascadia 开始吃", "t=2250 5823 格 / 218778 兵", "t=3100 留底 > 余额，不出手", "t=3389 阵亡"], statementType="observed"),
        "Don": dict(
            cause="峰值 11380（2360），9942 格从 1710 平到 2250。t=2310 / 2345 两条打 Name 之后 1570 拍只有 3 笔捐款（给 Cataphract 两笔比例 58~61：到账 109315、税 115618）。"
                  "t=2430 起 Player 47（T8）蚕食；t=3600~3900 Name、SONion🥀（都是 T8，Kaiser / Yi 的野人队友）和 Phoenix A（T2）一起吃：Player 47 3414 格、SONion🥀 2458、Phoenix A 1643、Name 1570。"
                  "追踪：t=2100 Name 报价 32.7 < worth 43.8，但留底 328940 → 可用兵 −2846；t=2700 / 3300 break:price>=worth；t=3600 密度 111、留底 1940079 → 可用兵 −991685。Luigi t=3915 的救援捐在它死后（3919）才到，没成交。",
            chain=["t=2360 11380 格（峰值）", "t=2430~3560 被 Player 47 蚕食到 9112 格，余额涨到 100.9 万", "t=3633 捐给 Luigi 148222（税 61599）", "t=3740 7468 格 / 79.3 万", "t=3919 阵亡"], statementType="observed"),
        "Aurelian": dict(
            cause="出生在左上角 (18,98)，名下 5134 格。t=938~1449 七条船 56110 兵，其中靠在 [SOLO]MINOLO（T3）地上的拿到 1388 格（34311 兵）；MINOLO 从 t=1290 起反过来吃它，26 个窗共 5518 格（897342 兵，163 兵/格）。"
                  "全程陆攻只有开局 2 条（t=609、791），t=1449 之后 1393 拍没有指令，再往后只有 4 条船。追踪：break:price>=worth；t=3600 留底 803543 → 可用兵 −519588。t=3745 / 3808 两条船各装 1241 / 591 兵、手续费 9933 / 6311。",
            chain=["t=938~1449 7 条船，从 MINOLO 手里拿 1388 格", "t=1290 MINOLO 开始反吃", "t=1400 5185 格 / 55093 兵", "t=2900 2174 格", "t=3800 2533 格 / 320151 兵（密度 126）", "t=3966 阵亡"], statementType="observed"),
        "System32": dict(
            cause="峰值 20154（t=2270~2700）。KOKUTEK（T2）从 t=2760 起分 8 次买走 8942 格（2629057 兵，294 兵/格）；System32 在 t=2170~3703 的 1533 拍里没有一条指令"
                  "（追踪 t=2700 / 3300 / 3900：最便宜的报价 70.6 / 100.7 / 138.4 兵/格，worth 33.6 / 68.4 / 82.5 → break:price>=worth）。过了软上限后 t=3703 / 4186 两条打的是 Waximus（822991 兵换 2840 格，290 兵/格），"
                  "t=4522 / 4536 才反手打 KOKUTEK：545887 兵换回 1842 格（296 兵/格）。KOKUTEK t=4655 清仓打 [JP]tukki 后只剩 2 兵（t=4750 20129 格），"
                  "System32 余额 698783、对它的留底 763470，不出手（t=4850 吃光只要 6202 兵，留底 463420，仍不出手）；这块地被 [JP]tukki（13742 格）和 Kaiser（10101 格）吃走。"
                  "✨（T1）t=4620 起吃 6465 格、Phoenix A（T2）t=4410 起吃 5352 格。Darius 7 笔救援捐到账 910459（税 557084）；阵亡时身上 230969 兵。",
            chain=["t=2270~2700 20154 格（峰值）", "t=2760 KOKUTEK 开始买（8 次、294 兵/格）", "t=2170~3703 1533 拍 0 条指令", "t=4522~4536 反手 545887 兵 / 1842 格", "t=4750 贴着 2 兵的 KOKUTEK 不出手", "t=4878 阵亡（余额 230969）"], statementType="observed"),
        "Luigi": dict(
            cause="Empire Monkey（T7）t=1500~3420 吃 3995 格（555472 兵，139 兵/格）；最后是 𐱅𐰇𐰼𐰰🐺（T6，t=4830~5370，3853 格 / 1055244 兵）和 Cascadia（T6，t=4740~5070，2057 格 / 701906 兵，它看不见）。"
                  "t=2107~4963 的 12 条指令 = 1 条船 + 6 笔捐款（给 Cataphract 4 笔 249328、给 Don 2 笔 207806）+ 4 条打 [VN] AM（3 条是替 Cataphract 的协防戳刺；整局 394743 兵换 1012 格，390 兵/格）+ 1 条打 Empire Monkey。"
                  "追踪 t=4700：Empire Monkey（空壳）skip:chunk、[VN] AM skip:soleBuffer；t=5000 / 5200 break:price>=worth。",
            chain=["t=1500~3420 Empire Monkey 吃 3995 格", "t=2250 7293 格", "t=3500 5763 格 / 616689 兵", "t=4740 Cascadia、𐱅𐰇𐰼𐰰🐺 开始吃", "t=5285 2391 格", "t=5362 阵亡"], statementType="observed"),
        "Kaiser": dict(
            cause="编队最大的号（峰值 37264，t=5950）。t=5362 起每次密度过 100 就把超出留底的兵放给 [JP]tukki：5 条（5362 / 5621 / 5894 / 6440 / 6622）共 3995975 兵拿 13177 格（303 兵/格），[JP]tukki 前后拿回 19741 格（318 兵/格）。"
                  "战事中 t=6090~6328 三笔捐给 Yi 到账 1835644、税 762865（合计 260 万，是当时余额的 65%）。t=6330 起 ✨ 加入（8842 格）、t=6750 起 Phoenix A（6264 格）、Mongol Empire（2374 格）。"
                  "t=6622 之后 388 拍 0 条指令：t=6690 还有 3155820 兵（密度 94），330 拍里 33482 格被四家花约 792 万兵吃光。"
                  "追踪 t=6650~6950：密度 92~95、所有真人报价 break:price>=worth。Yi t=7000 的救援捐 165102（税 165102）10 拍后清零。",
            chain=["t=5362 密度 119 → 放兵打 [JP]tukki（303 兵/格）", "t=5950 37264 格（峰值）", "t=6090~6328 捐给 Yi 183.6 万（税 76.3 万）", "t=6330 ✨ 开打", "t=6622 最后一条指令", "t=6690 33482 格 / 315.6 万兵，四家开吃，0 条还手", "t=7010 阵亡"], statementType="observed"),
        "Darius": dict(
            cause="t=2880~5670 的 2790 拍只从 11283 格长到 11782 格（峰值 13315，t=6300）。t=4200~4851 把 910459 兵（另付税 557084）捐给正在坍的 System32。t=7000 起 [JP]tukki（8137 格 / 2274350 兵）和 ✨（6080 格 / 1738723 兵）来吃；"
                  "追踪 t=7000：留底 3762740 → 可用兵 −2475740；t=7400 crowdedHard；t=7600 / 7800 break:price>=worth。",
            chain=["t=2880 11283 格", "t=4200~4851 7 笔救援捐给 System32", "t=5670 11782 格", "t=7000 留底 > 余额", "t=7908 阵亡"], statementType="observed"),
        "Yi Sun-sin": dict(
            cause="t=810 被 Cataphract 围住（3950 格）；t=1710~2250 吃 AI317 / AI457 / 365 的地 4455→17140 格（3.9~8.1 兵/格）；t=6120~6330 花 1288514 兵吃 𐱅𐰇𐰼𐰰🐺 3204 格（402 兵/格）。"
                  "t=6300~9270 的 3000 拍陆上邻居只有 Guts（129 格边界）、队友 SONion🥀、Cataphract，都不能打：领土 25435~26772 不动，t=7455~9268 六条船 2823570 兵（手续费 658352）打 ✨，整局 Yi→✨ 2920272 兵换 5290 格（552 兵/格）；期间给 Kaiser 捐 13 笔 443.1 万（税 184.1 万）。"
                  "t=9360~9930 ✨（6.6 万格 / 800 多万兵）吃它 9716 格，它从 t=9268 到 9961 的 693 拍没有一条指令（追踪 t=9400~9900：对 ✨ 的留底 453.7~508.0 万 > 余额 220~314 万，skip:avail<=0(safe)）。"
                  "✨ t=9996 离开；[JP]tukki t=10890 压上来，390 拍吃 15783 格（4550397 兵，288 兵/格），追踪 t=10900 break:price>=worth。",
            chain=["t=810 3950 格、被围", "t=2250 17140 格", "t=6300~9270 25435~26772 格、陆上没有可打的邻居，6 条船打 ✨", "t=9360~9930 ✨ 吃 9716 格，693 拍 0 条指令", "t=10890 [JP]tukki 开吃", "t=11267 阵亡"], statementType="observed"),
    },
    decisions=[
        dict(id="D01", t="0~350", bot="全队", decision="出生点没有后端协调器，各号自己重选 4~13 次；最后一条指派只落地 3/11，8 个号留在旧点上，5 个号排在下沿一条线上。名下份额 16.2%（人头 20.8%）。",
             codePath=SPAWN, verdict="error", patternId="NEW-SP-05",
             evidence=["spawncheck [PA][PB][PC]：110 行 [HL-SPAWN]、0 行 [HL-SPAWN-BACKEND]；最后一条执行了的 3/11；8/11 最后一次落地在第 49~50 步", "landcap [KA]：直线口径 107568 格 = 16.2%（0.78），陆路 13.9%（0.67）；逐号中位 7476 对 12594；6/11 在最低四分位",
                       "lagledger [GA]：编队每号落地的出生指令中位 9 条，其他真人 2 条"], statementType="observed"),
        dict(id="D02", t="0~350", bot="全队", decision="各号自己挑的点本身就偏：就算 8 个号的最后一条指派都落地，名下份额也只到 17.1%（人头的 0.82），多 5790 格；最后一条里 Cataphract / Don / ProGamer99 互相只隔 97~109 像素，Aurelian 两次选到左上角。",
             codePath=SPAWN, verdict="error", patternId="NEW-SP-07",
             evidence=["landcap [KA] 反事实：113358 格 = 17.1%，中位 9820，最低四分位 4 个；Darius +12143、Luigi +5293、System32 −7552、Don −6009", "spawncheck [PA]：Aurelian 引擎落点 (18,98) 是它的第 5、11 条指派",
                       "out/B015/spawnlast.json（各号最后一条指派）"], statementType="inferred"),
        dict(id="D03", t="0~5070", bot="全队", decision="把撞名的陌生真人 Cascadia（T6）算成编队友：出生排位给它留名次（squad=12），之后全程按名字保护——不进 nb、不反击、不买它的地。它吃掉三个号 7023 格。",
             codePath=ANALYZE + f"；{C110}: Policy.chooseSpawn L4010-4020", verdict="error", patternId="NEW-MT-04",
             evidence=["[HL-SPAWN] 行 squad=12（本编队 11 个号）；resim names[7] = Cascadia，T6，出生 (384,897)", "truth 逐对战损：Cascadia → Panzergrenadier 2834 格 / 142580 兵、→ ProGamer99 2132 格 / 433891 兵、→ Luigi 2057 格 / 701906 兵",
                       "真值指令账：11 个号对 Cascadia 的陆攻 0 条；Panzergrenadier 有 4 条船靠岸时落点已经是它的地（t=1437~1888，26941 兵，按进攻结算，拿到 0 格）", "squadfog [HC]：Panzergrenadier 4 个『看不见的失地』窗丢 1360 格"], statementType="observed"),
        dict(id="D04", t="350~900", bot="全队", decision="开局扩张和头一段人机收割按期完成：t=630 人均比 0.97、t=900 0.99；600~900 全房真人吃到的 AI 格里编队占 33%（人头 20.8%）。",
             codePath=f"{C110}: expandNeutral L2408-2417 → dpNeutral L2418-2490；Policy.buyLand L5363-5369（对非真人）", verdict="good", patternId="NEW-OP-G1",
             evidence=["lagledger [GB]：0~600 76 条指令 P50 / P90 / 最大 12 / 15 / 18 拍，没生效 0", "landcap [KD]：600~750 5422 / 12322（44.0%）、750~900 14657 / 47836（30.6%）", "harvest：(630,900] 人均吃人机 1612 对 893 格",
                       "landcap [KD]：t=600 贴着的 31 个 AI 的 13003 格，到 1500 编队吃到 9406 / 11187（84.1%）"], statementType="observed"),
        dict(id="D05", t="900~1500", bot="全队", decision="收割后半段掉队：全房真人 900~1500 吃掉 296147 格 AI 的地，编队 21657 格（7.3%）；人均派出的兵只有别人的 37%，而手里的余额一样多。",
             codePath=SB + "；" + DRIVER, verdict="error", patternId="NEW-EC-10",
             evidence=["landcap [KD] 150 拍窗：9.8% / 5.7% / 6.9% / 6.9%", "perhead [PH-B]：(900,1260] 人均 4.5 条 / 14318 兵对 7.4 条 / 38482 兵；t=1260 人均余额 60970 对 60546", "harvest：(900,1260] 人均 1078 对 3667 格",
                       "landcap [KB]：拿到率之比 1.37（900）→0.95（1260）→0.83（1500）"], statementType="observed"),
        dict(id="D06", t="610~1490", bot="Don / Kaiser / System32 / Luigi / ProGamer99 / Cataphract / Darius", decision="贴着几十兵的人机不出手：打人机前的留底 sb 取了共用这个人机的另一个真人的余额。Don 42 个决策点（970~1490）自己 47705 兵、sb 79356，面前 985 格 / 47 兵的人机吃光只要 1166 兵。",
             codePath=SB, verdict="error", patternId="NEW-EC-05",
             evidence=["landcap [KF] 门槛普查 [600,1500)：贴着可打 AI 的 583 个号·点里 372 个全被挡（63.8%）；sb 198、winWorth 187、winFloor 74、dpKeep 9", "shadowcmp [SH]：900~1260 201 / 153，sb 135（敌队真人 59、同队编队友 39、同队野人 22、异队编队友 15；互锁 44）",
                       "逐号被 sb 挡死的点：Don 42（Phoenix A ×36）、Kaiser 29（✨）、System32 29（Player 814 ×26）、Luigi 26（Cataphract ×19）、ProGamer99 24、Cataphract 21（Luigi ×20）、Darius 10",
                       "landcap [KF]：贴着、被别人吃掉的 21905 格里门槛挡住 5709（sb 5518）"], statementType="observed"),
        dict(id="D07", t="900~1800", bot="全队（10/11 个号）", decision="客户端落后服务器时照常决策发令：时延中位 43→185 拍，600~1500 落地的陆攻里 29 条目标已经出局（22 条被改成打无主地、7 条作废），1500~3000 又 16 条没生效。",
             codePath=DRIVER + "；" + ENG_ATK, verdict="error", patternId="NEW-IO-01",
             evidence=["lagledger [GB]：600~1500 P50 / P90 / 最大 30 / 121 / 242；1500~3000 88 / 218 / 290；3000+ 12 / 22 / 194", "shadowcmp [SF]：900~1079 43 / 64；1080~1259 80 / 109；1260~1439 124 / 194；1440~1619 185 / 242；1620~1799 162 / 229；1800~1979 13 / 45",
                       "lagledger [GE]：600~1500 改打无主地 22 条 65934 兵、作废 7 条 28559 兵；按时的落空 6%，晚 ≥35 拍的 38%", "lagledger [GC]：最大时延 Kaiser 218、Guts 260、System32 290、Darius 263、Don 247、ProGamer99 242、Cataphract 235",
                       "landcap [KF]：贴着、被别人吃掉的 21905 格里迟到 6729（落空 4895、晚 ≥35 拍 1834）"], statementType="observed"),
        dict(id="D08", t="1232~1813", bot="Kaiser / Guts / Darius / System32 / Luigi", decision="补拍时积压的指令成批落地、同一目标连发：本意 12%~26% 的一条变成 63%~87% 的余额。Guts t=1778 一拍 5 条打 365（余额 174778→58476），到 t=1883 又 7 条（最后一条比例 1012 = 99%），t=1890 余额只剩 1 兵（领土 20662 格）。",
             codePath=DRIVER + f"；{C110}: Strategy.send L526-540（同目标 15 拍冷却，按本地拍算）", verdict="error", patternId="NEW-IO-02",
             evidence=["lagledger [GG]：600~1500 连发 20 串 / 多出 29 条 / 12.2 万兵、成批 7 批；1500~3000 28 串 / 61 条 / 64.2 万兵、14 批（7 批抽走 ≥50%，批里第 2 条起 55.3 万兵）；其他真人 0 批",
                       "shadowcmp [SB2]：Kaiser t=1778 一拍 9 条（决策拍 1560~1695）、t=1701 5 条；Darius t=1708 9 条（1445~1700）；System32 t=1722 8 条（5 条作废）",
                       "truth [TG]：Guts 1799~1813 →365 ×5 59294→51538（87%，本意 12%）；Kaiser 1778 →Harris ×6（75%，本意 26%）；Guts 1778 →365 ×5（67%）；Luigi 1232~1239 →AI342 ×4（65%）",
                       "lagstats [LC]：编队一拍落地条数 1:476 2:11 3:10 4:3 5:2 6:3 8:1 9:2；其他真人 1:2122 2:12"], statementType="observed"),
        dict(id="D09", t="1700~2250", bot="Guts / Kaiser / Yi Sun-sin / Darius / System32", decision="时延波尾声趁邻居便宜出手：Guts 16.9 兵/格吃掉 365 的 11988 格，Kaiser 20.6 兵/格吃 Harris [MEME] 8815 格，Yi 3.9~8.1 兵/格长到 17140 格；人均比 0.62→0.76。",
             codePath=BUY, verdict="good", patternId="NEW-AT-G3",
             evidence=["truth 逐对战损：Guts→365 11988 格 / 202320 兵；Kaiser→Harris 8815 / 181702；System32→Harris 3006 / 71710；Darius→Harris 2720 / 75014；Yi→365 2147 / 17338", "truth：编队占地 13.42%（1800）→18.07%（2250）→18.20%（2430）",
                       "365、Harris [MEME] 都在 t=1965~2020 出局、2037~2114 才登记离开：打的时候它们还在线", "Guts 这 11988 格就是 D08 那几批补拍打下来的：对手正在坍，清仓赌赢了；t=1890~1990 它 2 万格只有 1~3900 兵"], statementType="observed"),
        dict(id="D10", t="2250~3500", bot="全队", decision="中立地和人机吃完后全队停手 1250 拍：10 个在线号合计 14 条陆攻 / 船，5 个号 0 条；占地 18.07%→15.31%，密度 16.6→80.9。",
             codePath=BUY, verdict="error", patternId="NEW-EC-04",
             evidence=["真值指令账 (2250,3500]：编队人均 1.4 条 / 4.3 万兵，其他 30 个在线真人人均 4.4 条 / 36.2 万兵", "Kaiser 最后一条在 t=1778、下一条在 3703；余额 136890→1143479，领土 18481→15737",
                       "逐拍追踪 t=2100~3600：真人报价 break:price>=worth 或 skip:avail<=0(safe)", "perhead [PH-B]：(2700,3600] 人均派出 47399 对 152023 兵；harvest：从真人手里拿 781 格对 52344 格"], statementType="observed"),
        dict(id="D11", t="1620~1710", bot="Panzergrenadier", decision="正在被（看不见的）Cascadia 吃的时候把兵装船送走：4 条船 50187 兵，余额 70191→20794，密度从 12 掉到 4。",
             codePath=BOAT + "；" + ANALYZE, verdict="error", patternId="NEW-MT-06",
             evidence=["真值指令账 Panzergrenadier：t=1638 25702 兵、1708 三条 18773 兵、1715 240 兵、1771 三条 4966 兵", "逐拍追踪 t=1650 / 1750 / 1850：真人邻居 0 个、没有报价", "truth：Cascadia 在 t=1440~2010 的 20 个窗里吃 2834 格"], statementType="observed"),
        dict(id="D12", t="1981~3389", bot="ProGamer99", decision="t=1981 之后 1408 拍没有任何指令，被 𐱅𐰇𐰼𐰰🐺 和 Cascadia 吃光：对 𐱅𐰇𐰼𐰰🐺 的留底高过自己全部余额，另一个邻居报价过不了 worth，第三个（Cascadia）看不见。",
             codePath=SAFE + "；" + COUNTER + "；" + ENG_ELIM, verdict="error", patternId="NEW-DF-01",
             evidence=["逐拍追踪 t=3100：𐱅𐰇𐰼𐰰🐺 onMe 171035、safeRaw 477792→keep 185680→avail −68103（skip:avail<=0(safe)）；Empire Monkey break:price>=worth", "真值指令账：ProGamer99 最后两条指令是 t=1918 / 1981 的船；5823（2250）→1431 格", "truth：𐱅𐰇𐰼𐰰🐺 3136 格 / 560595 兵（t=2130~3120）、Cascadia 2132 格 / 433891 兵（t=2160~3390）"], statementType="observed"),
        dict(id="D13", t="2100~3919", bot="Don", decision="被三家野人蚕食 1500 拍只发了 2 条陆攻：留底按最富邻居的余额算，t=3600 是自己余额的 2 倍；期间两笔比例 58~61 的救援捐税比到账还多。",
             codePath=SAFE + "；" + DON_RESCUE, verdict="error", patternId="NEW-DF-04",
             evidence=["逐拍追踪：t=2100 Name 报价 32.7 < worth 43.8，留底 328940 → avail −2846；t=3600 留底 1940079 → avail −991685", "donfit / 真值：Don→Cataphract t=3290 到账 56416 / 税 58236、t=3388 到账 52899 / 税 57382",
                       "truth：Player 47 3414 格 / 789537 兵、SONion🥀 2458 / 789902、Phoenix A 1643 / 560974、Name 1570 / 563066"], statementType="observed"),
        dict(id="D14", t="4655~4878", bot="System32", decision="贴着只剩 2 兵、20129 格的 KOKUTEK 不出手（吃光只要 26095 兵，自己有 698783）：留底 763470 是按别的邻居的余额算的。200 拍后阵亡，身上还有 230969 兵。",
             codePath=SAFE + "；" + BUY, verdict="error", patternId="NEW-DF-04",
             evidence=["逐拍追踪 System32 t=4750：KOKUTEK 报价 2.1 兵/格、need 26095，safeRaw 2599952→keep 763470 > 余额 698783；t=4850 need 6202、keep 463420", "truth：KOKUTEK t=4700 22640 格 / 22645 兵、t=4750 20129 格 / 2 兵；[JP]tukki 13742 格 / 1352083 兵、Kaiser 10101 格 / 874432 兵",
                       "真值指令账：System32 t=4522 / 4536 反手 545887 兵换 1842 格（296 兵/格）；此前 KOKUTEK 已从它身上买走 8942 格（294 兵/格）"], statementType="observed"),
        dict(id="D15", t="4680~4950", bot="Kaiser", decision="KOKUTEK 清仓后，Kaiser 用 874432 兵吃到 10101 格（86.6 兵/格），18702→28364 格。",
             codePath=BUY + "（目标正在流血 / 快坍时留底封顶到 88×领土）", verdict="good", patternId="NEW-AT-G1",
             evidence=["truth 逐对战损：Kaiser→KOKUTEK 10101 格 / 874432 兵", "真值指令账 Kaiser：t=4501 协防戳刺 228697、4550 pct 279 620921、4711 89514", "同一个目标 [JP]tukki 花了 98.4 兵/格"], statementType="observed"),
        dict(id="D16", t="3178~7000", bot="Kaiser / Yi Sun-sin", decision="两个同队号互相捐 18 笔：净流向 Kaiser 192.5 万，税 288.2 万。t=6090~6356 的 266 拍里 8 笔来回，净流量 14.0 万、税 134.6 万；11 笔是捐给密度 ≥100 的号。",
             codePath=DON_SURPLUS + "；" + ENG_DON, verdict="error", patternId="NEW-DN-07",
             evidence=["真值指令账：Yi→Kaiser 13 笔到账 4430832 / 税 1840863；Kaiser→Yi 5 笔到账 2505347 / 税 1041182", "t=6090 K→Y 643024、6216 K→Y 598373、6272 Y→K 563087、6293 Y→K 286192、6328 K→Y 594247、6342 Y→K 479298、6356 Y→K 366991",
                       "全程 42 笔成交：到账 8995662、税 4047820；收款方密度 ≥100 的 11 笔（到账 2177554、税 874129）"], statementType="observed"),
        dict(id="D17", t="4200~4851、7000", bot="Darius / Yi Sun-sin", decision="往正在坍的队友身上捐：Darius→System32 7 笔到账 910459、税 557084，System32 t=4878 阵亡；Yi→Kaiser t=7000 到账 165102、税 165102，Kaiser 10 拍后阵亡。",
             codePath=DON_RESCUE + "；" + ENG_DON + "；" + ENG_ELIM, verdict="error", patternId="NEW-DN-12",
             evidence=["真值指令账：Darius→System32 t=4200 214488、4396 200179、4501 217620、4550 72031（税 74355）、4641 67612（税 73342）、4746 70004（税 73447）、4851 68525（税 74332）", "System32 领土 15920（4200）→5400（4851）→0（4878）",
                       "比例 ≤75 的 9 笔：到账 633845、税 654167"], statementType="observed"),
        dict(id="D18", t="6622~7010", bot="Kaiser", decision="编队最大的号挨四家打 388 拍没有一条指令：密度 92~95 不算超软上限，真人报价 ≥ worth 整轮停，专门的反击分支是关着的（counterK = 0）；t=6690 的 33482 格、315.6 万兵在 330 拍内清零。",
             codePath=BUY + "；" + COUNTER + "；" + ENG_ELIM, verdict="error", patternId="NEW-DF-01",
             evidence=["逐拍追踪 Kaiser t=6650 / 6750 / 6850 / 6950：break:price>=worth，密度 92~95", "真值指令账：t=6622 之后没有指令；此前 5 条打 [JP]tukki 3995975 兵 / 13177 格（303 兵/格）", "truth：[JP]tukki 19741 格 / 6286962 兵、✨ 8842 / 2781417、Phoenix A 6264 / 1818788、Mongol Empire 2374 / 712840"], statementType="observed"),
        dict(id="D19", t="5760~9930", bot="Yi Sun-sin / Guts", decision="两个最大的幸存号互相贴着 129 格边界、互相保护：Yi t=6300~9270 陆上没有一个可打的邻居（领土 25435~26772 不动、t=9000 338 万兵），只能发船打 ✨（552 兵/格）；"
             "Guts t=5760~6300 顶着硬上限 3486750 兵。✨ t=9360~9930 吃 Yi 9716 格时，Yi 对它的留底 453.7~508.0 万 > 余额，693 拍 0 条指令。",
             codePath=ANALYZE + "；" + BUY, verdict="error", patternId="NEW-EC-09",
             evidence=["truth 逐号轨迹：Guts 的邻居 = Yi Sun-sin 129 格边界 + ✨ 19~49；Yi 的邻居（6300~9270）= Guts 129 / SONion🥀（队友）45 / Cataphract 13", "逐拍追踪 Guts t=5760~6300：✨ 的留底 3568740~3906256 > 硬上限 3486750",
                       "逐拍追踪 Yi t=9000：humanNb=0；t=9400 / 9500 / 9600 / 9700 / 9900（shadow_tr4）：✨ onMe=1、safeRaw 5080172 / 4787103 / 4858818 / 4537023 / 4717115、avail −198~−246 万；t=9800 skip:soleBuffer",
                       "truth：✨→Yi t=9360~9930 9716 格；Yi 指令 t=9268（船）之后下一条是 t=9961"], statementType="observed"),
        dict(id="D20", t="8000~9000", bot="Guts", decision="余额 400 万的号吃不动贴着的 116~153 格小人机 AI190：吃光只要 174~230 兵，低于最小指令门槛（余额的 4.7% ≈ 17~19 万）。",
             codePath=MINCMD, verdict="error", patternId="NEW-EC-07",
             evidence=["逐拍追踪 Guts t=8000 / 9000：AI190 116~153 格、need 174~230，skip:x<minCmd(188408 / 173488)", "shadowcmp [SJ]：Yi Sun-sin 135 个点（1510~3000）里 101 个 minCmd(want)：余额 428379、minCmd 20080、AI 923 格 0 兵 need 1866",
                       "truth：内置 AI 整局从编队手里啃走 6744 格；Yi 在 t=2250~3330 被 AI349 啃走 506 格"], statementType="observed"),
        dict(id="D21", t="10465~10980", bot="Guts", decision="[JP]tukki 压境前后：t=10465~10612 四条船付手续费 504756（3 条只装 6869~8474 兵）；t=10710 起 270 拍丢 28070 格，追踪里 soleBuffer / 留底 1377 万 / price>=worth 轮流挡住，没有一条陆攻打 [JP]tukki。",
             codePath=BOAT + "；" + BUY + "；" + SAFE, verdict="error", patternId="NEW-SE-03",
             evidence=["真值指令账 Guts：t=10465 8062 兵 / 费 129007；10500 521036 / 130259（靠在自己地上，原数退回）；10507 6869 / 109906；10612 8474 / 135584", "逐拍追踪 t=10650 skip:soleBuffer；10750 safe 13773635；10850 break:price>=worth",
                       "truth：[JP]tukki 吃 Guts 28070 格 / 8704907 兵（34375→17684→11780→8414）", "全程：Guts 40 条船手续费 1981356，其中 16 条手续费 > 船上兵（装 5.1 万、费 93.8 万）"], statementType="observed"),
        dict(id="D22", t="1100~12700", bot="Cataphract / Guts / Yi Sun-sin / Darius / Aurelian", decision="被围的号持续发船：全程 159 条船、装兵 1336.9 万、手续费 389.3 万；靠到无主地 73.0 万、敌人地上 747.9 万、自己地上 320.4 万（原数退回、白付手续费）、没靠岸 195.0 万。",
             codePath=BOAT, verdict="unclear", patternId="NEW-SE-05",
             evidence=["truth 船账：58 条手续费 > 船上兵（159.8 万）；Cataphract 43 条里 27 条", "Cataphract t=4050~4140 余额 172976→0、领土归 0，靠在途的船重新上岸，终局 1485 格（T5 获胜）", "Guts t=6496~6811 三条船 150.5 万兵打 ✨、t=9331 再 61.8 万：Guts→✨ 全程 16499 格 / 6270819 兵（380 兵/格）"],
             statementType="observed"),
        dict(id="D23", t="1699、2308", bot="Darius / Cataphract", decision="船靠在异队编队友的地上，引擎按进攻结算：Darius→Kaiser 11571 兵（t=1699）、Cataphract→Yi Sun-sin 33466 兵（t=2308）；编队内部互吃 1092 格。",
             codePath=BOAT + f"；{SIM}/game.js 船靠岸在敌队地上按进攻结算", verdict="error", patternId="NEW-SE-04",
             evidence=["truth 靠岸记录：t=1699 Darius→Kaiser 11571；t=2308 Cataphract→Yi 33466", "truth 逐对战损：Cataphract→Yi 369 格 / 33458 兵；Darius→Kaiser 723 格 / 11566 兵"], statementType="observed"),
        dict(id="D24", t="全程", bot="全队", decision="协防戳刺 30 条里 27 条是替别的队里的编队号出兵（Guts 为 Yi 打 ✨ 11 条）。Guts→✨ 全程 380 兵/格。",
             codePath=f"{C110}: assist / poke L4447-4458（受益人按名字池挑，不看是不是同队）", verdict="unclear", patternId="NEW-MT-02",
             evidence=["digest [HL-ASSIST]：30 条，跨队 27 条", "truth 逐对战损：Guts→✨ 16499 格 / 6270819 兵（含 11 条跨队戳刺和 4 条船）"], statementType="observed"),
        dict(id="D25", t="全程", bot="全队", decision="发令后 7 拍额度自检：在线时被 8 拍静默窗整个跳过，isNoFullSend 0/11 个号置位。",
             codePath=f"{C110}: updateShadowQuota（7 拍检查窗）；文件头 L19-31（发令后 8 拍不调用策略）", verdict="unclear", patternId="NEW-EX-04",
             evidence=["shadow.json：isNoFullSend 置位 0/11", "shadowcmp [SI]：同一次决策发两条指令时第 2 条配上录像的 1/8"], statementType="inferred"),
    ],
    newPatterns=pick("NEW-SP-05", "NEW-SP-07", "NEW-MT-04", "NEW-MT-06", "NEW-MT-01", "NEW-MT-02", "NEW-OP-G1", "NEW-AT-G1", "NEW-AT-G3", "NEW-EC-04", "NEW-EC-05", "NEW-EC-07", "NEW-EC-09",
                     "NEW-IO-01", "NEW-IO-02", "NEW-EX-01", "NEW-EX-04", "NEW-DF-01", "NEW-DF-04", "NEW-DN-02", "NEW-DN-07", "NEW-DN-12", "NEW-DN-14", "NEW-SE-03", "NEW-SE-04", "NEW-SE-05", "NEW-IO-06", "NEW-IO-09", "NEW-EC-10", "NEW-MT-08", "NEW-IO-14"),
    lossArchetype="never-grew",
    archetypeNote="主型 never-grew：人均比从 t=1260 起再没有回到 0.76 以上（0.71 @1260、0.61 @1500、0.76 @2250、0.60 @3960、0.44 @7020），编队占地峰值 18.2%（人头 20.8%）。"
                  "差距在 t=900~1500 的人机收割后半段拉开（站位 0.74 全程不变，拿到率之比 1.37→0.83），之后的停手和不还手让 9 个号在 3389~11267 之间被逐个买走。"
                  "次型 outscaled：终局前全场只剩三个大真人（[JP]tukki、Phoenix A、HitIerRapíst67），编队最大的号也只有它们的三分之一以下。"
                  "对局卡的 SPLIT_WON 来自 Cataphract（1485 格）所在的 T5 获胜，T5 的地是野人 [JP]tukki 一个人打下来的。",
    winnerNotes="T5 获胜（t=13175 时 64.24%，对局在这里结束，原因不明）。T5 的 426843 格里 425358 格是野人 [JP]tukki 的：t=900 它已是全场第一（9843 格），t=2700~3600 也停在 32710 格（密度 122），"
                "之后每一步都在吃正在坍的邻居——KOKUTEK 清仓后的 13742 格、Kaiser 19741 格、Darius 8137 格、Yi 15783 格、Guts 28070 格（从编队号身上合计 71731 格），再吃 T8 的 SONion🥀 和 T4 的 HitIerRapíst67。"
                "它对 Kaiser 的买价 318 兵/格、对 Guts 310 兵/格——出得起价，而编队号在同样的密度下被 worth 门槛挡着不出价。T5 在 t=3960 还是全场最小的队（6.7%）。",
    peerComparison="本房间没有另一支受控编队。可比的是其他 42 个真人：t=1500 他们的中位 12227 格（编队 5622），拿到自己名下份额的 88%（编队 73%），并且有 25.5% 的地来自名下之外（编队 13%）。"
                   "补拍成批（一拍 ≥3 条）编队 21 批、其他真人 0 批；一拍 2 条的编队 11 次、其他真人 12 次。",
    teamSplitNotes="11 个号没有战队标签，被分进 8 个队里的 5 个（T2×2、T4×1、T5×3、T7×2、T8×3），彼此是敌队，但按名字互相保护、互不攻击（analyze L440）。后果："
                   "① Yi（T8）t=810 被 Cataphract（T5）围住，Cataphract t≈1170 被 Yi、Luigi 围住；Yi 与 Guts（T4）贴着 129 格边界 9000 拍互不动手。"
                   "② 各队的野人照常打别队的编队号：Don（T5）死于 T8 的三个野人，Guts / Kaiser / Darius / Yi 被 T5 的 [JP]tukki 吃掉 71731 格；丢给野人的 182798 格里 63.6% 是丢给『有编队号的队』（8 队里的 5 队）。"
                   "③ sb 留底把异队 / 同队编队友的余额当威胁（900~1260 被 sb 挡死的 135 个点里 54 个）。④ 协防戳刺 30 条里 27 条跨队。⑤ 两条船靠在异队编队友地上按进攻结算。",
    ledgerExtra=dict(
        truthDonations=dict(executed=42, logged=43, arrived=8995662, tax=4047820, notExecuted="t=3915 Luigi→Don（Don 3919 阵亡，没成交）",
                            byPair={"Yi Sun-sin→Kaiser": dict(n=13, arrived=4430832, tax=1840863), "Kaiser→Yi Sun-sin": dict(n=5, arrived=2505347, tax=1041182),
                                    "Darius→System32": dict(n=7, arrived=910459, tax=557084), "System32→Darius": dict(n=1, arrived=281358, tax=116928),
                                    "Luigi→Cataphract": dict(n=4, arrived=249328, tax=166644), "Don→Cataphract": dict(n=2, arrived=109315, tax=115618),
                                    "Luigi→Don": dict(n=2, arrived=207806, tax=88252), "Don→Luigi": dict(n=1, arrived=148222, tax=61599),
                                    "Cataphract→Luigi": dict(n=6, arrived=129962, tax=49269), "Cataphract→Don": dict(n=1, arrived=23033, tax=10381)},
                            receiverDensityGe100=dict(n=11, arrived=2177554, tax=874129), pctLe75=dict(n=9, arrived=633845, tax=654167),
                            pingPong6090to6356=dict(kaiserToYi=1835644, yiToKaiser=1695568, tax=1346284, net=140076)),
        cardLikelyRejectedCheck="对局卡 likelyRejectedTransfers=2；真值只有 1 笔没成交（受捐方 4 拍后阵亡）。digest 按『20 拍后余额没扣』判的 REJ 6 / ? 5 是时延假象。",
        drop30Truth=dict(windows=47, byCause={"挨打": 27, "陆攻": 12, "发船": 6, "捐款": 2}, src="truth.txt [TK]（90 拍窗，真值余额）；digest [F] 日志口径 38 行，对局卡 37"),
        boats=dict(count=159, troops=13369216, fees=3892675, feeGtTroops=dict(n=58, fees=1597951), landedNeutral=729530, landedEnemy=7478825, landedOwnLand=3203896, landedTeammate=7176, notLanded=1949789,
                   byBot={"Guts": dict(n=40, troops=6364527, fees=1981356), "Yi Sun-sin": dict(n=20, troops=5357710, fees=1286016, notLanded=1345802), "Cataphract": dict(n=43, feeGtTroops=27), "Darius": 18, "Panzergrenadier": 13, "Aurelian": 11},
                   onOtherTeamSquadMates=[dict(t=1699, bot="Darius", owner="Kaiser", troops=11571), dict(t=2308, bot="Cataphract", owner="Yi Sun-sin", troops=33466)]),
        intraSquadFights=dict(cells=1092, pairs=["Cataphract→Yi Sun-sin 369 格 / 33458 兵", "Darius→Kaiser 723 格 / 11566 兵"]),
        assistPokes=dict(count=30, crossTeam=27, top="Guts→✨ ×11"),
        lostToWildHumans=dict(cells=182798, toTeamsWithSquadBots=116193, byAttackerTeam={"T1": 46408, "T2": 33025, "T3": 5518, "T5": 71731, "T6": 14679, "T7": 3995, "T8": 7442}, gainedFromWildHumans=105803, lostToBuiltInAI=6744),
        cascadia=dict(player=7, team=6, tookFromSquad=7023, detail={"Panzergrenadier": [2834, 142580], "ProGamer99": [2132, 433891], "Luigi": [2057, 701906]}, squadLandAttacksOnIt=0, left=6713, died=6879),
        idle2250to3500=dict(squadOnline=10, landAndBoatCmds=14, perCapita=1.4, troopsPerCapita=43202, othersOnline=30, othersPerCapita=4.4, othersTroopsPerCapita=361886, zeroCmdBots=["Kaiser", "System32", "ProGamer99", "Luigi", "Yi Sun-sin"]),
        latencyDigest=dict(
            spawn="[GA] 110 条指派、后端 0 条；每号重选中位 11 次、落地的出生指令中位 9 条（其他真人 2 条）；最后一条落地 3/11、8 个号落在旧点；同像素 0 对。",
            lagByPeriod="[GB] 执行拍 0~600 P50 / P90 / 最大 12 / 15 / 18（76 条）；600~1500 30 / 121 / 242（186 条，46% ≥35 拍）；1500~3000 88 / 218 / 290（127 条，61% ≥35 拍）；3000+ 12 / 22 / 194（205 条）。",
            funnel="[GD] 影子想发 → 配上录像 → 真机 cmds 增量 → 录像落地 → 生效：600~1500 226 → 193 → 209 → 186 → 177；1500~3000 108 → 93 → 114 → 127 → 111。真机本地发出 596 条、录像 594 条：没有丢，只是晚。",
            lateLoss="[GE] 600~1500 陆攻 160 条：目标已经没了 29 条（改打无主地 22 条 65934 兵；作废 7 条、本意 28559 兵）；1500~3000 84 条：没生效 16 条，目标没了 9 条（改打无主地 1 条 24327 兵；作废 8 条、本意 123758 兵）。",
            refund="[GF] 600~1500 回到余额的兵 ÷ 派出的兵：编队 55%，其他真人 43%。",
            dupAndBatch="[GG] 连发串：600~1500 20 串、多出 29 条、12.2 万兵；1500~3000 28 串、61 条、64.2 万兵。成批：7 批 / 28 条；14 批 / 68 条（7 批抽走余额 ≥50%，批里第 2 条起 55.3 万兵）。其他真人 0 批。",
            staleAmplify="过期放大（时延 ≥35 拍已生效的陆攻 / 船）：600~1500 73 条、本意 33.8 万 → 实发 39.9 万（1.18）；1500~3000 58 条、110.6 万 → 85.6 万（0.77）。"),
        landDigest=dict(
            voronoi="[KA] 直线口径 107568 格 = 16.2%（人头 20.8%，0.78）；陆路 13.9%（0.67）；逐号中位 7476 对 12594；最低四分位 6/11。反事实（最后一条指派都落地）17.1%（0.82）、+5790 格。",
            capture="[KB] 拿到名下份额的比例（编队 / 其他真人）：0.28 / 0.21（630）、0.54 / 0.39（900）、0.67 / 0.71（1260）、0.73 / 0.88（1500）、0.83 / 0.94（1800）。"
                    "t=1500 编队名下的地：自己 60.1%、异队编队友 3.1%、敌队真人 21.2%、内置 AI 10.1%、无主 4.9%；其他真人 25.5% 的地来自名下之外，编队 13%。",
            identity="按出生人头（编队 11、其他真人 42）的人均领土之比 = 人均名下份额之比 × 拿到率之比：0.98 = 0.74 × 1.33（630）；1.01 = 0.74 × 1.37（900）；0.70 = 0.74 × 0.95（1260）；0.61 = 0.74 × 0.83（1500）；0.65 = 0.74 × 0.88（1800）。",
            aiLand="[KD] t=600 内置 AI 451 个、198734 格（29.9%）；之后又占 232171 格。属于过 AI 的 430905 格：到 1500 被真人吃掉 356305，编队 41736（11.7%，应得 73950，差 32214）；到 1800 吃掉 391392，编队 46693（11.9%，差 34539）。"
                   "t=600 贴着编队的 31 个 AI、13003 格：到 1500 编队吃到 9406 / 11187（84.1%）。",
            attribution="[KF] 差额 32214 格 = ① 贴不着 10309（32.0%）+ 同队 AI 不能打 5868（18.2%）+ ② 门槛 5709（17.7%；sb 5518）+ ③ 迟到 6729（20.9%；落空 4895、晚 ≥35 拍 1834）+ 出手了被分走 / 过闸没发 3599（11.2%）。"
                        "名下口径 [KE]：① 名下先天少 19680 格；名下的被别人吃掉 20944 格（够不着 8392、同队 AI 5682、② 4028、③ 2180）。",
            gateCensus="[600,1500) 贴着可打 AI 的 583 个号·点里 372 个全被挡（63.8%）：sb 198、winWorth 187、winFloor 74、dpKeep 9。"),
    ),
    wentWell=[
        "开局与头一段收割：t=630 人均比 0.97、t=900 0.99；600~900 全房真人吃到的 AI 格里编队占 33%（人头 20.8%）；t=600 贴着的 AI 吃到 84%。",
        "t=1700~2250 时延波尾声的便宜地：Guts 16.9 兵/格、Kaiser 20.6 兵/格、Yi 3.9~8.1 兵/格，编队占地 13.42%→18.20%。",
        "Kaiser t=4680~4950 抓住 KOKUTEK 清仓：10101 格、86.6 兵/格。",
        "出生点没有同像素、没有 <40 像素的号对；t>1800 时延回到 8~14 拍，3000 拍以后只有 1 条陆攻没生效。",
        "真引擎重演 487/487 条快照逐兵一致；影子与真机的 HL-OPENING / cmds 计数对得上，时延按决策逐条配对。",
    ],
    unknowns=[
        "对局为什么在 T5 只有 64.24% 时结束：归档引擎要领先的队占全部陆地，录像最后一拍 over=0。B019 也是在 64.45% 结束；48 个对局包的结束行里领先队份额从 64% 到 100% 都有。线上服务器可能有归档里没有的结束规则（猜测）。",
        "时延波（t≈900~1800，10/11 个号同时）的根因：策略自身耗时 avgMs ≤1.16。B043 的时延波也在 t≈1800 收尾，和内置 AI 被吃光的时间重合——像是客户端模拟的开销随 AI 数量下降，但没有主机侧数据（猜测）。",
        "『贴不着』那 10309 格里有多少是站位、多少是前面的门槛和迟到造成的后果，分不开：早一步吃掉面前的 AI 就能贴上后面的 AI。",
        "一拍 ≥3 条的批只出现在编队号身上：是驱动层补拍时把积压的本地决策一次发出，还是服务器按连接排队，数据包里没有驱动层源码。",
        "Cascadia 是什么人：名字在名字池里、T6、t=6713 离开；没有它的日志。",
        "365、Harris [MEME] 在被吃掉时（t=1700~2000）是不是已经没人操作：录像里的离开登记在出局之后。",
    ],
    mechanicsQuestions=[
        "8 队局内置 AI 分队（AI p 属于 1+(p%8) 队）是从快照反推出来的设定：按它重演 487/487 条逐兵一致、不按它对不上。线上是不是所有 ≥8 队的局都这样，只有这一局能证实。",
        "目标出局后进攻槽改成打无主地（redirectAttackToNeutral）：身边没有无主地时整条作废、一兵不扣——600~3000 有 15 条这样作废，本意 152317 兵。",
        "船靠在自己地上：兵原数退回余额，手续费（余额的 32/1024）不退。全程 320.4 万兵这样打了个来回。",
        "收款方离阵亡只剩几拍时捐款照常成交、照常收税；阵亡时余额清零（aliveTick）。",
    ],
    scripts=[
        "c136-review/agents/R08/scripts/resim_r08.mjs B015（真引擎重演 → out/B015/resim.json；487/487 条快照一致）",
        "c136-review/agents/R08/scripts/truth.py B015（[TA]~[TO] 全场真值）",
        "c136-review/agents/R08/scripts/shadow.mjs B015 [--until T --trace 号:拍 --tag trN]；trshow.py 打印逐拍追踪",
        "c136-review/agents/R08/scripts/shadowcmp.py B015（[SA]~[SJ] 时延、成批、门槛普查）",
        "c136-review/agents/R08/scripts/spawncheck.py B015（出生指派 vs 引擎落点；写 spawnlast.json）",
        "c136-review/agents/R08/scripts/landcap.mjs B015 + landcap.py B015（[KA]~[KF] 好地硬账：名下份额、反事实、拿到率、AI 地去向、三层归因）",
        "c136-review/agents/R08/scripts/atkfate.mjs B015 + lagledger.py B015（[GA]~[GG] 延迟硬账）",
        "c136-review/agents/R08/scripts/harvest.py / perhead.py / bursts.py / lagstats.py / squadfog.py / flow.py / donfit.py / donrej.py / top.py B015",
        "c136-review/agents/R08/scripts/facts.py B015 → out/B015/digest.txt；build_review.py B015（合成本 JSON 并自检）",
    ],
    confidenceOverall="high",
    confidenceNote="领土、余额、指令、战损、捐款、船靠岸都来自逐兵对上的真引擎重演。时延依赖影子决策与录像的配对（600~1500 配上 85%、1500~3000 86%，其余 ≥99%），数量级可靠、单条可能配错。"
                   "三层归因里『门槛』来自影子在真值局面上重走策略（真机当时看到的是晚几十到两百拍的局面），『贴不着』是余项。反事实出生份额只挪了编队的号、别人不动，是静态估计。",
)
