# A071 手写判断。事实数字全部取自脚本输出，写之前逐条对过：
#   out/dossier/A071.txt（卷宗 [A]~[P]）、out/dossier/A071-shadow.txt（影子摘要 [S0]~[S7]）、
#   out/dossier/A071-freeze.txt（freeze-scan 两段）、out/dossier/A071-donwhy.txt（donate-why：9,474 次调用，照抄判定 100% 一致）、
#   out/dossier/A071-delay.txt [L1]~[L5]、A071-land.txt [G1]~[G4]、A071-ledger-brief.txt [B1]~[B9]、
#   out/trace/A071-*.txt（cmdq / issueq / snapq / dispatchq 对缓存和 events.csv 的查询，acts，pingpong，boat-audit，boat-life），
#   bundles/A071/{card.json,results.csv,events.csv}。
# 口径：逐对战损（卷宗[E]/[F]/[K]、snapq --press）按 30 拍一桶、桶末拍记账；只引各输出文件里印出来的数，不写自己加出来的合计。
from notes._patterns import pat

VB = "src/strategy/v27-team-c116-vb.js"
SPAWN = "src/strategy/spawn-coordinator-c116-vb.mjs"
SIM = "src/sim/sim"

NOTES = {
    "context": {
        "peerSquad": "riku_x 进了另一个房间（results.csv 记它 1169 拍 left、9,552 格；那个房间的图陆地 695,915 格）。本房间 9 个号全在队4；队4 另有 2 个路人："
                     "Portugal#17（出生 (950,227)，在这一团的西边；4500 拍 58,980 格/527 万兵，6000 拍 84,169 格/900 万兵、密度 107，6610 拍峰值 92,052 格 = 13.85%；"
                     "5894~7301 拍 16 条陆攻全是 pct 103，打 =[、stormy、Player 224、StayObsessed；7840 拍出局）、"
                     "Jun#13（出生 (1147,186)，离 sora_w 9 像素；5859 拍离线成空壳，6010 拍峰值 44,318 格；6000~6100 拍被 🌞 吃 10,182 格，6600~7200 拍剩下的被 StayObsessed 吃掉，7108 拍出局）",
        "tickRate": "results.csv：zero_7 6589 拍@390 秒，noah88 7685 拍@451 秒（约 17 拍/秒）",
        "pageStops": "9 个号都控到出局；出局时页面拍号 − 服务器拍号 +5~+16。本包日志缺这 9 个号本地 720 拍之前的行（HL-TICK 每号 66~78 行，开局日志只有 4 条）",
        "liveAdapterModel": "影子策略用的页面适配规则（每拍只收 1 条指令、陆攻按相邻受理、船不发队友地）是从日志计数器反推的；"
                            "本局 630/630 行 HL-TICK 的 cmds、nb、neut 全对，134/134 条调度、4/4 条开局日志、775/775 条成交配回影子发令；整局重放 630/630 行地、兵与 traj 逐行相等",
        "cardNote": "card.json 的 mapId=12、mapSeed=103、mapLand=695,915、seededPlayers=42 是 riku_x 那个房间的；本房间录像头是图 22（种子 8663，和 A067 同一张图）、陆地 664,497 格、44 个真人。"
                    "card 记 endTick=7685 是 noah88 出局那一行；录像到 8066 拍 over=0（队3 99.1%），引擎事件 7777 拍提速（队3）。录像头写 8 队，实际 4 队各 11 人。"
                    "peakSquadLandShare=0.2091、peakPrimaryTeamShareSeen=0.3317 是 results.csv 各行里的最大值；重放里编队峰值是 5210 拍的 21.89%（145,491 格），队4 峰值是 6010 拍的 39.80%。"
                    "card 的 likelyRejectedTransfers=19 是页面自己标的；重放里没成交的调度是 24 条（额度拒 22、其它 2）。"
                    "traj.csv 的 53 个 DROP30 区间里 1 个是 riku_x 的（它在另一个房间，这份重放里没有），本房间 9 个号 52 个（reviews/A071.json 的 drop30.count）",
        "execDelay": "延迟局。成交延迟（服务器落地拍 − 本地发令拍）P50/P90/最大：0~600 拍 12/16/34，600~1500 拍 90/148/201，1500~3000 拍 83/154/180，3000 拍后 11/15/20；"
                     "775 条里 300 条超过 30 拍。9 个号一起落后：全队窗口的延迟中位 600 拍 15、900 拍 93、1200 拍 137、1500 拍 104、1800 拍 12",
    },
    "outcome": {
        "note": "输。四队图（真人各 11，另有 468 个不入队的内置 AI）。队4 的地：1500 拍 11.6%（四队里最少，队3 25.2%），6010 拍 39.80%（整局峰值，含两个路人），6900 拍 24.3%，7800 拍 4.8%。"
                "编队 9 个号 1500 拍 8.41%（人头占 20.45%），5210 拍峰值 21.89%，6300 拍 18.66%。6579~6914 拍 7 个号先后出局，都是被队3 的 StayObsessed 吃掉的；"
                "zexos1 7178 拍、noah88 7351 拍触到出局线被清场，靠在途的船各留到 7549、7679 拍",
        "archetypeSecondary": "never-grew 的成分：9 个号里 6 个整局峰值不到全图 2%（0.68%~1.96%），kaito9 峰值 2.92%；4420~5590 拍 8 个号同时没有陆上邻居；"
                              "mid-collapse 的成分：6600~6900 拍队4 34.8%→24.3%，6900~7200 拍 →15.8%",
    },
    "timelineNotes": {
        90: "9 个号出生在东北角一团：x 1086~1202、y 80~374。叠点 2 对：alex_k 和 zexos1 相距 5 像素，kaito9 和 talon5 相距 6 像素；路人 Jun 离 sora_w 9 像素；队3 的 [USA]（567 拍离线）离 kaito9、talon5 18、19 像素",
        630: "AI 35.2%、中立 47.0%。编队单号地中位 2,674（2,418~3,360），其他真人单人地中位 2,490；0~600 拍延迟 P50 12 拍",
        1080: "页面落后：900 拍这一窗发令 153 条、落地 136 条，延迟中位 93 拍；1200 拍这一窗 72 条落 57 条，中位 137 拍。单号地中位 4,406（900 拍）→4,997（1200 拍），其他真人 4,921→8,845",
        1530: "AI 还有 23.4%。1500 拍编队 55,854 格 = 全图 8.41%，单号地中位 5,155（其他真人 13,137）；余额 124 万、密度 22.1。兵在没有地可买的号手里：talon5 18.6 万（密度 51）、zero_7 16.3 万（41）、kaito9 16.3 万（32）、leo_tx 13.3 万（42）；"
              "名下最大的 zexos1（37,671 格）只有 8.4 万兵",
        1800: "1500 拍起对真人出手，指令等 83~154 拍：noah88 1589、1652 拍两批 6 + 9 条打 simba（18.1 万→2.6 万、3.1 万→4.9 千），地 8,748→19,209（1800 拍）；zero_7 1638 拍 9 条花掉余额 93%，leo_tx 1743 拍 9 条 80%，都打 [EU]Player 615。"
              "编队 11.24%、112 万兵（密度 15.0）",
        2130: "[PL] Recover 1740~2100 拍吃 zero_7 3,196 格（烧 12.8 万），1830~2220 拍吃 leo_tx 3,831 格（烧 6.3 万）。ryan_m 给 sora_w、leo_tx 的两条协防被额度拒。simba 2273 拍出局",
        2700: "队2 开始垮（在线真人 8 个，3000 拍 5 个）。zexos1 1860~3510 拍吃 [EU]Player 615 15,102 格（烧 125 万）；编队余额 395 万（密度 40.3）",
        3060: "编队 14.71%、615 万兵（密度 62.9）。kaito9 给 zexos1 的调度 2925~3075 拍连续 7 条被额度拒，talon5 给 zexos1 的 3020~3095 拍 4 条被拒",
        3600: "编队 18.4%。zexos1 3720 拍 44,555 格（峰值）；noah88 3270~3510 拍吃 [EU]Player 615 4,946 格；alex_k 3120~4440 拍吃 [PL] Recover 6,919 格（烧 222 万，收捐 344 万）。队3 在线 6 个真人 1,617 万兵，队4 在线 11 个 900 万",
        4500: "AI 没有了，队2 只剩 2.8%。4420 拍起 9 个号里 8 个没有陆上邻居，只有 kaito9 在西北角贴着敌人。4315 拍起后排开始把兵调给 kaito9；kaito9 4320~4800 拍吃 [OG] Pugo 7,291 格（烧 172 万）。"
              "队3 在线 6 个真人 40.1%、2,438 万兵；编队 20.3%、874 万兵",
        5100: "kaito9 4795 拍起和 =[ 对打：同一拍双方的第一条指令落地。编队 5210 拍到峰值 21.89%，余额却从 874 万掉到 684 万（密度 47.4）。4500~5100 拍队1 22.1%→12.2%，队3 40.1%→47.8%，队4 33.7%→36.3%",
        5400: "stormy 5250 拍起也打 kaito9。5000~5999 拍后排给 kaito9 的调度 26 条全是协防档。队3 50.3%",
        6000: "队1 没了。队3 55.7%、在线 6 个真人 2,930 万兵；队4 39.7%、1,505 万兵（Portugal 900 万）。编队 20.38%、604 万兵（密度 44.6）；后排各号密度 31~45（talon5 74），kaito9 剩 9,363 格。Jun 5859 拍离线",
        6300: "StayObsessed（6300 拍 1,112 万兵、密度 125）5908 拍一条 135 万兵的船开过来，6030 拍起吃 zexos1，6300 拍起吃 alex_k。6062~6615 拍 10 笔协防 185 万给 zexos1，6321~6356 拍 6 笔 71.0 万给 alex_k。编队 18.66%",
        6600: "StayObsessed 一条指令吃一个号：6517 拍 zero_7（129 万兵压在 6480 拍只有 11.1 万兵的号上，6579 拍出局）、6566 拍 sora_w、6615 拍 leo_tx。🌞 6398 拍起用船、6594 拍起走陆路打 zexos1",
        7200: "6682~6914 拍 sora_w、leo_tx、alex_k、kaito9、ryan_m、talon5 出局。zexos1 7178 拍被清场（8,419 格/43.2 万兵）。只剩 noah88 19,290 格/139 万兵",
        7685: "noah88 7351 拍被清场（6,470 格/24.3 万兵），7679 拍出局；zexos1 7549 拍出局。Portugal 7500~7800 拍 77,711→31,830 格（StayObsessed 吃 25,781 格、Player 436 9,727 格、=[ 6,129 格），7840 拍出局",
    },
    "phases": {
        "spawn_0_90": {
            "facts": [
                "9 个号的出生框中心：ryan_m (1118,80)、sora_w (1140,190)、zexos1 (1146,374)、noah88 (1202,246)、talon5 (1092,148)、alex_k (1142,370)、zero_7 (1086,310)、kaito9 (1088,144)、leo_tx (1140,264)；选点期 41 步，各号落地 8~32 条选点指令",
                "叠点 2 对：alex_k 和 zexos1 的最后一条选点指令都是 (1142,370)，相距 5 像素；kaito9 和 talon5 都是 (1087,144)，相距 6 像素。alex_k 最后一步落地 2 条，先发的旧坐标生效",
                "按出生点分地：编队名下 95,168 格 = 全图 14.32%，人头占 20.45%，份额÷人头 0.70。逐号：zexos1 37,671、noah88 26,484，其余 7 个号 3,271~8,275，9 个号的中位 4,275；其他真人名下中位 14,892，35 个里只有 1 个比编队中位小。"
                "人均名下：队1 20,240、队3 18,011、队2 12,236，编队 10,574",
                "敌方真人：队3 的 [USA]#7 离 kaito9、talon5 18、19 像素、离 ryan_m 55（567 拍离线成空壳）；队2 的 [PL] Recover 离 zero_7 31；[EU]Player 615 离 leo_tx 48、noah88 70、zexos1 72",
            ],
            "problems": [
                "两对叠点的号只能分一份地：talon5 名下 3,271、alex_k 3,379、kaito9 4,275 格",
                "本包日志里没有本房间的选点求解行（日志里的 16 轮求解是另一个房间的图），解和落地对不了账；叠点是求解器给了同一个坐标还是指派落空，查不到",
            ],
        },
        "opening_90_630": {
            "facts": [
                "0~600 拍 77 条指令延迟 P50/P90/最大 12/16/34 拍；想发 81 → 落地 77 → 生效 77",
                "630 拍编队 25,366 格 = 全图 3.82%，单号 2,418~3,360（中位 2,674）；其他真人单人地中位 2,490。实际÷名下 编队 0.27 对其他真人 0.16",
                "isNoFullSend 在 463~995 拍被翻成 true（noah88 3340 拍），9 个号全部翻转",
            ],
            "problems": [
                "名下小的号 630 拍已经占掉名下的 0.60~0.95（alex_k 0.95、kaito9 0.75、talon5 0.74、sora_w 0.73），之后只能等队友让路",
            ],
        },
        "midgame_630_3500": {
            "facts": [
                "600~1500 拍：259 条落地指令延迟 P50/P90/最大 90/148/201 拍，192 条 >30 拍、129 条 >90 拍；想发 293 → 落地 259 → 生效 217。打 AI/真人的 56.0 万兵里 19.7 万（35.2%）落地时目标已死、改打无主地，34 条作废",
                "实际÷名下：900 拍编队 0.38 对其他真人 0.30，1200 拍 0.52 对 0.52，1500 拍 0.59 对 0.75，1800 拍 0.78 对 0.92。1500 拍逐号：zexos1 0.35、noah88 0.33，其余 7 个号 0.74~1.68",
                "1500 拍我方名下范围：编队 46.7%、敌方真人 12.3%、AI 36.0%；1800 拍 53.5%、22.1%、18.1%。600 拍接壤的 29 个 AI 共 11,346 格，1800 拍编队拿到 82.8%；名下范围内的 AI 地 30,757 格，编队拿到 44.9%、敌方真人 25.7%、还在 AI 手里 25.8%",
                "600~1500 拍 1,620 个决策拍：选到目标 286、扩无主地 548、没有 AI 邻居 298、被 safeFinite 冻结 446（27.5%；卡在编队友 278、同队路人 21、敌方真人 147；去掉这一项当拍能出手 399）。talon5 117、kaito9 100、ryan_m 77 拍，三个号互相卡",
                "1500~3000 拍：153 条 P50/P90/最大 83/154/180；同一拍落 ≥3 条的批里花掉余额 ≥80% 的 3 批：zero_7 1638 拍 9 条 93%（20.2 万/21.8 万）、noah88 1589 拍 6 条 86%、noah88 1652 拍 9 条 84%；leo_tx 1743 拍 9 条 80%",
                "逐对：noah88 → simba 烧 18.5 万拿 13,057 格；zexos1 → [EU]Player 615 烧 125 万拿 15,102 格；leo_tx → [EU]Player 615 烧 41.3 万拿 10,331 格；[PL] Recover → zero_7 3,196 格、→ leo_tx 3,831 格",
                "调度日志按 1000 拍：2000~2999 拍 进攻 6、协防 3 条；3000~3999 拍 进攻 14、协防 7、产出 5 条；4000~4999 拍 产出 28、进攻 17、协防 12 条。额度拒 22 条里 kaito9→zexos1 7 条（2925~3075 拍，首次需 69 点、剩 64 点）、talon5→zexos1 4 条、leo_tx→alex_k 3 条、noah88→alex_k 4 条",
            ],
            "problems": [
                "名下最大的两个号转化最差：zexos1 600~1500 拍均密 4、实得利息 15.0 万，noah88 均密 7、18.6 万；noah88 1442、1519 拍两批各 9 条一条都没生效（空令：目标已不相邻、已无中立地）",
                "兵在名下小的号手里出不去：1500 拍前不捐款（tryDonateToTeammate 的 t<1500 闸），之后受额度限制",
                "zero_7 1638 拍把 21.8 万里的 20.2 万打向 [EU]Player 615，只拿 1,058 格；兵在外面时 [PL] Recover 烧 12.8 万吃它 3,196 格（地 3,990→1,852）。leo_tx 1743 拍同样的一批换到了地（3,179→7,319 格，2220 拍），其间被 [PL] Recover 吃 3,831 格",
            ],
        },
        "endgame_3500_end": {
            "facts": [
                "被围（没有陆上邻居）的区间：ryan_m 1865~4110、4225~6740，zexos1 3440~6050，leo_tx 4010~6575，noah88 4140~6545，talon5 4400~5590，alex_k 4405~6300，zero_7 4415~6465，sora_w 4420~6545，kaito9 4685~4775、6160~6720。"
                "1500 拍后 9,831 个决策拍里没有陆上邻居 4,176 个（这些拍的平均余额 67.1 万）、报价高于 worth 3,545 个、出手 339 个",
                "调度日志 134 条 = 协防 64 + 进攻 37 + 产出 33；成交 110 笔，到账 2,373 万、税 655 万（税/到账 28%）；按落地拍 4284 拍之后 1,727 万。kaito9 收 57 笔 1,284 万（4326~5943 拍）",
                "给 kaito9 的 59 条调度：捐方全部是被围的号；协防 37 条捐方密度 31/44/60（最小/中位/最大），受捐方 69/91/135；产出 19 条捐方 58/59/105，受捐方 91/114/140。协防 + 产出 56 条里受捐方比捐方密的 56 条；受捐方密度 ≥100 的：产出 12/19、协防 16/37",
                "pingpong：全场 129 笔成交捐款（编队 110 笔）里 106 笔落地当拍让双方「每 10 拍利息」合计 ≤0（这些笔的税 562 万）；zexos1→kaito9 10 笔、noah88→kaito9 7 笔、alex_k→kaito9 8 笔全部 ≤0。"
                "逐对看接收方落地后的密度中位：zexos1→kaito9 95.8→150.0（10 笔里 5 笔被硬上限截短），alex_k→kaito9 111.2→128.4，sora_w→kaito9 125.6→134.1；捐出方 59.5→40.5、59.5→40.8、58.0→32.8",
                "kaito9：4320~4800 拍打 [OG] Pugo 烧 172 万拿 7,291 格（交换比 0.38）；4800~5910 拍打 =[ 烧 480 万拿 9,530 格（0.26，另有 227 万在反击槽里对消），被 =[ 吃回 8,901 格（对方烧 490 万）；"
                "5250~6030 拍打 stormy 烧 112 万拿 1,225 格（0.21），被 stormy 吃 10,373 格（对方烧 343 万）。地 8,806（4500 拍）→19,402（5210 拍）→9,363（6000 拍）→7,263（6200 拍）",
                "kaito9 4780~5025 拍每个脉冲 pct 122、同一个决定发 2~3 条：余额 215~247 万、密度 125~150、over=1，worth 112~135，对 =[ 的报价 193~386。整局 3000 拍后落地前重发 52 串，首条 831.9 万、后续 1,167.5 万",
                "4500→6000 拍：队1 22.1%→0.0%，队3 40.1%→55.7%，队4 33.7%→39.7%；编队 20.3%→20.38%，余额 874 万→604 万。队3 在线真人的兵 2,438 万→2,930 万",
                "StayObsessed：4500 拍 34,799 格/346 万兵 → 6000 拍 77,513 格/915 万（密度 118）→ 6300 拍 1,112 万（125）。5908 拍一条船 135 万兵开向 alex_k 的岸；6097 拍 140 万打 zexos1，6440 拍 136 万打 alex_k，6517 拍 129 万打 zero_7，6566 拍 121 万打 sora_w，"
                "6615 拍 128 万打 leo_tx，6713 拍 112 万打 talon5，6776 拍 99.7 万打 kaito9，6790 拍 90.6 万打 ryan_m，7098 拍 243 万打 noah88。整局吃编队 81,349 格（自烧 1,444 万）",
                "6300 拍编队各号：zexos1 271 万（密度 77）、noah88 112 万（38）、talon5 78.8 万、alex_k 55.0 万、ryan_m 41.3 万、leo_tx 40.8 万、kaito9 39.9 万、sora_w 37.9 万、zero_7 13.1 万（29）",
                "🌞（6000 拍 114,598 格/335 万兵、密度 29）6398 拍起用船、6594 拍起走陆路打 zexos1（每条 pct 187），整局吃 28,125 格、自烧 876 万；zexos1 6552~6671 拍还手烧 73.5 万拿 550 格（66.5 万在反击槽里对消）",
            ],
            "problems": [
                "后排把兵捐给比自己密的 kaito9，自己掉到密度 31~45；kaito9 过了软上限就按 2~3 倍 worth 的报价对比自己大的 =[、stormy 出手",
                "被围的号的兵没有别的出口：noah88 4151 拍 49.7 万兵的船 542 拍后在海上被 N***** 的船打光；zexos1 6364、6420 拍两条船去同一个落点",
                "被 StayObsessed 打的号压在身上的兵是自己余额的数倍，候选受捐判定 doomed:x1.65 106 次、A:dMe 425 次，协防只到了 zexos1、alex_k",
            ],
        },
    },
    "turningPoints": [
        {
            "t0": 0, "t1": 1500,
            "what": "9 个号挤在东北角、两对叠点，名下的地只有人头份额的 0.70；页面又从 900 拍起落后 90~200 拍，名下最大的两个号只拿到名下的三分之一",
            "shareKind": "队4 占全图陆地", "shareBefore": 0.0, "shareAfter": 0.116,
            "enemyShareBefore": 0.0, "enemyShareAfter": 0.252,
            "squadShareBefore": 0.0, "squadShareAfter": 0.0841,
            "ourBots": ["zexos1", "noah88", "talon5", "kaito9", "alex_k", "ryan_m"],
            "enemies": ["队3（1500 拍 25.2%）", "队1（20.0%）", "[USA]#7（队3，空壳）", "[EU]Player 615#2（队2）"],
            "evidence": [
                "out/dossier/A071-land.txt [G1]：编队名下 95,168 格 = 全图 14.3%，人头占 20.5%，份额÷人头 0.70；逐号 zexos1 37,671、noah88 26,484、ryan_m 8,275、leo_tx 4,324、kaito9 4,275、zero_7 4,087、sora_w 3,402、alex_k 3,379、talon5 3,271；其他真人名下中位 14,892",
                "卷宗[D]：alex_k、zexos1 相距 5 像素，kaito9、talon5 相距 6 像素；A071-ledger-brief.txt [B1]：叠点 2 对，alex_k 最后一步落地 ≥2 条、先发的旧坐标生效",
                "A071-land.txt [G2]：1500 拍编队 55,854 ÷ 名下 95,168 = 0.59，其他真人 0.75；逐号 zexos1 13,166/37,671 = 0.35、noah88 8,748/26,484 = 0.33，其余 0.74~1.68。[G3]：1500 拍名下范围里 AI 还占 36.0%、敌方真人 12.3%",
                "A071-ledger-brief.txt [B9]：人均地 6,206 对 12,378 = 0.50 = 出生份额 0.64 × 转化 0.78；按其他真人的转化算该有 71,411 格，实际 55,854 格，少 15,557 格",
                "A071-delay.txt [L2]/[B2]：600~1500 拍 259 条 P50/P90/最大 90/148/201，192 条 >30 拍；[B4]：打 AI/真人 56.0 万兵里 19.7 万（35.2%）目标已死改打无主地，34 条作废。卷宗[J]：noah88 1442 拍 9 条（生效 0）、1519 拍 9 条（生效 0）",
                "A071-freeze.txt 第一段：1,620 个决策拍里 safeFinite 冻结 446（卡在编队友 278），talon5 117、kaito9 100、ryan_m 77；zexos1 0、noah88 24。卷宗[P]：600~1500 拍 zexos1 均密 4、noah88 均密 7",
                "out/trace/A071-q-squad-snap.txt：1500 拍 talon5 18.6 万兵（密度 51）、zero_7 16.3 万（41）、kaito9 16.3 万（32）、leo_tx 13.3 万（42）；zexos1 8.4 万（6）",
            ],
            "priorDecisions": [
                {"t": "选点期", "bot": "全部 9 个号", "what": "9 个号落在东北角 x 1086~1202、y 80~374 的一团，其中两对落在同一个坐标",
                 "codePath": f"{SPAWN} solve L790（角落扇形 L1065-1170；评分 L1262-1268）→ matchBotsToTargets L1431-1493；本房间的求解行不在日志里，叠点出在哪一步查不到",
                 "why": "7 个号名下只有 3,271~8,275 格，其中 6 个 630 拍就占掉了名下的 0.60~0.95（ryan_m 0.37）；有地可拿的只剩南边的 zexos1 和东边的 noah88"},
                {"t": "900~1500", "bot": "zexos1、noah88", "what": "页面落后，指令等 90~200 拍才落地，目标已经被别人吃掉",
                 "codePath": f"{VB} General.act L794-797（act:796）→ Policy.send L3800-3877；页面桥接层不在策略源码里",
                 "why": "这两个号身边有地，但 600~1500 拍均密只有 4、7（有兵就发），指令晚到：noah88 成交 128 条里 41 条目标已死、26 条空令"},
                {"t": "600~1495", "bot": "talon5、kaito9、ryan_m 等", "what": "贴着 AI 被 safeFinite 冻住 446 个决策拍",
                 "codePath": f"{VB} Style.pickTarget L1144-1177 → Policy.winFloor L4562-4570 → V17.safeFinite L2757-2768",
                 "why": "278 拍的绑定方是编队友；这些号本来名下就小，冻住的兵攒到 1500 拍也没有地可买"},
            ],
            "alternatives": [
                "按其他真人的 地÷名下（0.7504）算，编队 1500 拍该有 71,411 格，实际 55,854 格（算术，不是重演）",
                "叠点的两对如果各有自己的点，名下会多多少没有重算；出生点摊开能不能守住也没有重演",
                "talon5、zero_7、kaito9、leo_tx 1500 拍手里的 13.3~18.6 万兵在这套规则里到不了 zexos1：1500 拍前不捐，船靠队友岸要走额度（0~1500 拍 6 条船船上 6.9 万到账 3.5 万）",
            ],
            "statementType": "observed", "confidence": "high",
        },
        {
            "t0": 1500, "t1": 2100,
            "what": "1500 拍对真人开打，指令仍然晚 83~154 拍：noah88 两批吃下 simba，zero_7、leo_tx 一批花掉余额的 80~93%",
            "shareKind": "队4 占全图陆地", "shareBefore": 0.116, "shareAfter": 0.193,
            "enemyShareBefore": 0.252, "enemyShareAfter": 0.315,
            "squadShareBefore": 0.0841, "squadShareAfter": 0.1304,
            "ourBots": ["noah88", "zero_7", "leo_tx", "zexos1", "talon5"],
            "enemies": ["simba#42（队3）", "[EU]Player 615#2（队2）", "[PL] Recover#15（队2）", "[USA]#7（队3，空壳）"],
            "evidence": [
                "卷宗[J]：noah88 1589 拍 6 条打 simba 18.1 万→2.6 万（pct 254~278）、1652 拍 9 条 3.1 万→4.9 千；zero_7 1638 拍 9 条打 [EU]Player 615 21.8 万→1.6 万（pct 212~270）；leo_tx 1743 拍 9 条 17.7 万→3.6 万；talon5 1680、1757 拍各 9 条打 [USA] 的空壳（pct 14~18）",
                "A071-ledger-brief.txt [B5]：zero_7 1638 拍花掉余额 93%（20.2 万/21.8 万）、noah88 1589 拍 86%、1652 拍 84%、leo_tx 1743 拍 80%",
                "out/trace/A071-acts-samples.txt：noah88 1500 拍余额 15.3 万/8,748 格，simba 报价 15.01 对 worth 26.16；zero_7 1500 拍余额 16.3 万/3,990 格，[EU]Player 615 报价 39.48 对 worth 61.41；1500~1530 拍每个决策拍各发 1 条",
                "卷宗[F]：noah88 → simba 1590~2280 拍烧 18.5 万拿 13,057 格；zero_7 → [EU]Player 615 烧 2.6 万拿 1,058 格；[PL] Recover → zero_7 1740~2100 拍 3,196 格（对方烧 12.8 万）、→ leo_tx 1830~2220 拍 3,831 格（烧 6.3 万）；leo_tx → [EU]Player 615 1710~3510 拍烧 41.3 万拿 10,331 格",
                "out/trace/A071-q-tinycmd.txt：talon5 本地 1500~1680 拍对 [USA] 的空壳发 37 条 pct 12~18，落地 18 条；kaito9 1806~1834 拍 8 条 pct 0~4",
            ],
            "priorDecisions": [
                {"t": "1500~1530", "bot": "noah88", "what": "对密度 5 的 simba 每个决策拍发一条，6 + 9 条分两批落地",
                 "codePath": f"{VB} Policy.buyLand L5420-5427 → L5611-5616（buyLand:5616）",
                 "why": "报价 15.01 对 worth 26.16，是该打的目标；重发让它一批花掉 86%，这回 simba 没有还手，烧 18.5 万拿 13,057 格"},
                {"t": "1500~1545", "bot": "zero_7", "what": "对 [EU]Player 615 发 9 条，等 93~138 拍后 1638 拍一起落地",
                 "codePath": f"{VB} Policy.buyLand L5420-5427 → L5611-5616；每条只看 x ≥ chunk×余额，不看在途的兵",
                 "why": "3,990 格的号一批把 21.8 万里的 20.2 万送出去，1650 拍余额 1.7 万（密度 4）；1740~1860 拍 [PL] Recover（27.2~32.0 万兵）吃它，1890 拍出去的兵退回来时地只剩 1,989 格"},
            ],
            "alternatives": [
                "只发首条会怎样没有重演。noah88 这一批烧 18.5 万拿 13,057 格，是整局最划算的一笔；一批花掉 86% 之后它碰巧没被反打",
                "zero_7 2100 拍只剩 1,852 格，之后整局峰值 4,503 格；同样一批清仓的 leo_tx 是净赚的（3,179→7,319 格）",
            ],
            "statementType": "observed", "confidence": "high",
        },
        {
            "t0": 2100, "t1": 4200,
            "what": "吃垮掉的队2：编队 13.04%→19.04%，地集中在 zexos1、noah88 两个号手里；其余 7 个号陆续没有陆上邻居",
            "shareKind": "队4 占全图陆地", "shareBefore": 0.193, "shareAfter": 0.310,
            "enemyShareBefore": 0.315, "enemyShareAfter": 0.371,
            "squadShareBefore": 0.1304, "squadShareAfter": 0.1904,
            "ourBots": ["zexos1", "noah88", "alex_k", "leo_tx", "kaito9", "talon5"],
            "enemies": ["[EU]Player 615#2（队2）", "[PL] Recover#15（队2）", "Player 255#23（队2）", "Potato Empire#3（队2）"],
            "evidence": [
                "卷宗[B]：队2 2100 拍 15.9% → 4200 拍 5.0%（在线真人 8→3）；队4 19.3%→31.0%，编队 13.04%→19.04%，余额 171 万→991 万（密度 78.3）",
                "卷宗[F]：zexos1 → [EU]Player 615 1860~3510 拍烧 125 万拿 15,102 格（交换比 0.49）；noah88 → [EU]Player 615 3270~3510 拍烧 53.7 万拿 4,946 格；alex_k → [PL] Recover 3120~4440 拍烧 222 万拿 6,919 格；"
                "kaito9、talon5 → Player 255 烧 45.1 万、37.0 万各拿 799、807 格",
                "out/trace/A071-q-squad-snap.txt：3000 拍 zexos1 28,377 格、noah88 23,365 格，其余 7 个号 2,772~8,047 格；kaito9 84.5 万兵（密度 122）、talon5 73.5 万（112）",
                "卷宗[H]：kaito9→zexos1 2925~3075 拍 7 条 pct 193 被额度拒（首次需 69 点、剩 64 点；捐方余额 78.8 万→88.1 万，密度 113 对 38）；talon5→zexos1 3020~3095 拍 4 条（需 68 点、剩 14 点）",
                "A071-freeze.txt 第二段：talon5、kaito9 对 Player 255 的报价 233~788 对 worth 30~90（1960~4285 拍）",
                "卷宗[P]：1500~4284 拍均密 talon5 82、kaito9 79、zero_7 78（超软 880、790、640 拍），zexos1 30、noah88 32；利息实得÷满额 49%",
            ],
            "priorDecisions": [
                {"t": "1860~3510", "bot": "zexos1", "what": "一路吃正在垮的 [EU]Player 615",
                 "codePath": f"{VB} Policy.buyLand L5595-5607（buyLand:5607）、L5574-5585（buyLand:5585）",
                 "why": "交换比 0.49，拿 15,102 格，是编队这一段拿地最多的一笔"},
                {"t": "2925~3095", "bot": "kaito9、talon5", "what": "密度 113、114 的号想把兵调给正在推进的 zexos1（密度 38、49），11 条都被额度拒",
                 "codePath": f"{VB} Policy.tryDonateToTeammate L4474-4494 → L4500-4506（不读额度）；{SIM}/game.js donationCost L348-357、bookDonation L370-376",
                 "why": "方向是对的（密的给薄的、给在推进的），却发不出去：4284 拍前受捐额度每 100 拍只涨 4~10 点"},
            ],
            "alternatives": [
                "kaito9、talon5 2925~3095 拍的兵如果到了 zexos1 手里能多换多少地没有重演；zexos1 这一段是烧 125 万拿 15,102 格",
                "西北角的 kaito9、talon5 对 Player 255 一直是报价高于 worth：这一段两个号超软上限 790、880 拍",
            ],
            "statementType": "observed", "confidence": "high",
        },
        {
            "t0": 4200, "t1": 6000,
            "what": "8 个被围的号把兵调给唯一有前线的 kaito9，kaito9 过软上限后和 =[、stormy 对耗；同一段队3 吃完队1，编队的地 19.04%→20.38%、余额 991 万→604 万",
            "shareKind": "队4 占全图陆地", "shareBefore": 0.310, "shareAfter": 0.397,
            "enemyShareBefore": 0.371, "enemyShareAfter": 0.557,
            "squadShareBefore": 0.1904, "squadShareAfter": 0.2038,
            "ourBots": ["kaito9", "zexos1", "noah88", "alex_k", "sora_w", "leo_tx", "ryan_m", "talon5", "zero_7"],
            "enemies": ["=[#41（队3）", "stormy#30（队3）", "[OG] Pugo#1（队1）", "StayObsessed#27（队3）", "🌞#12（队3）"],
            "evidence": [
                "out/trace/A071-q-dispatch-kaito9.txt（dispatchq.py）：给 kaito9 的调度 59 条 = 协防 37 + 产出 19 + 进攻 3，捐方 boxedIn 全是 True；捐方密度 协防 31/44/60、产出 58/59/105；受捐方密度 协防 69/91/135、产出 91/114/140；"
                "受捐方比捐方密：协防 37/37、产出 19/19；受捐方密度 ≥100：协防 16/37、产出 12/19。例：4635 拍 sora_w（密度 83）、leo_tx（59）各一条产出档给密度 140 的 kaito9；4945 拍 zero_7 密度 31 给密度 135 的 kaito9",
                "卷宗[H]/[N]：kaito9 收 57 笔 1,284 万（4326~5943 拍）：zexos1 10 笔 516 万（税 149 万）、noah88 7 笔 278 万（税 66.6 万）、alex_k 8 笔 164 万、leo_tx 7 笔 89.0 万、sora_w 7 笔 86.6 万、ryan_m 7 笔 70.3 万、talon5 5 笔 48.8 万、zero_7 6 笔 31.9 万",
                "out/trace/A071-pingpong.txt [3]：129 笔里 106 笔落地当拍双方每 10 拍利息合计下降（税 562 万）；zexos1→kaito9 10 笔全部 ≤0（中位 −1.7 万）",
                "out/trace/A071-q-kaito9-batch.txt、影子摘要[S6]：kaito9 4780~4795 拍对 =[ 3 条（首条 30.3 万、多花 49.6 万），5015~5025 拍 3 条（32.5 万、53.1 万），5260~5270 拍对 stormy 3 条（31.0 万、50.0 万）。"
                "out/trace/A071-acts-samples.txt：5260 拍余额 235 万、密度 124.6、over=1，worth 112.14，stormy 报价 240.32、=[ 173.66",
                "卷宗[F]：kaito9 → =[ 4800~5910 拍烧 480 万拿 9,530 格（交换比 0.26、反击槽 227 万），=[ → kaito9 烧 490 万吃 8,901 格；kaito9 → stormy 烧 112 万拿 1,225 格（0.21），stormy → kaito9 烧 343 万吃 10,373 格。"
                "卷宗[L]：kaito9 利息 468 万、收捐 1,284 万；真人对消 330 万、反击槽被消 270 万、攻击费 125 万",
                "out/trace/A071-q-squad-snap.txt：4500→6000 拍 ryan_m 46.3 万→27.2 万（密度 56→33）、sora_w 63.3 万→37.2 万（70→41）、zexos1 271 万→173 万（61→39）、noah88 156 万→101 万（52→34）、alex_k 140 万→58.7 万（107→45）、leo_tx 48.0 万→39.6 万（50→41）",
                "卷宗[B]：4500→6000 拍队1 22.1%→0.0%、队3 40.1%→55.7%、队4 33.7%→39.7%（路人的地 13.41%→19.33%）；编队 20.3%→20.38%，余额 874 万→604 万；队3 在线真人的兵 2,438 万→2,930 万",
                "A071-freeze.txt 第二段：1500 拍后没有陆上邻居的决策拍 4,176 个（平均余额 67.1 万）",
            ],
            "priorDecisions": [
                {"t": "4440~4840", "bot": "zexos1、alex_k、sora_w、leo_tx、ryan_m、talon5、zero_7", "what": "产出档调度 19 条给 kaito9，发令时 kaito9 的密度 91~140，12 条时已过软上限",
                 "codePath": f"{VB} Policy.tryDonateToTeammate L4474-4494（Case B：被围的捐方 reqD 58、maxAllyD 128/140，L4479-4481）→ L4500-4506；L4476-4478 的注释写的是捐方 ≥98、受捐方 <92",
                 "why": "捐方密度 58~105、受捐方更密：兵从正利息的地方搬到负利息的地方，还要交整笔余额 64/1024 的税"},
                {"t": "4505~5943", "bot": "8 个被围的号", "what": "协防档调度 37 条给 kaito9，捐方密度 31~60",
                 "codePath": f"{VB} L4457（underFire）→ L4463-4473（Case A：被围的捐方 reqD 30/42，留底 22/32×领土 L4386-4388）→ L4500-4506",
                 "why": "kaito9 一直在被 =[、stormy 打，所以一直够得上协防档；后排密度从 49~107（4500 拍）掉到 31~45（6000 拍，talon5 74）"},
                {"t": "4780~5960", "bot": "kaito9", "what": "过软上限后对 =[、stormy 按 pct 122 连发，报价是 worth 的 1.5~3 倍",
                 "codePath": f"{VB} Policy.buyLand L5353（over）→ L5359（!over 才 break）→ L5440-5444 → L5595-5607、L5574-5585",
                 "why": "对 =[ 交换比 0.26、对 stormy 0.21；打下的 9,530 + 1,225 格到 6200 拍又丢回去了（kaito9 7,263 格，比 4326 拍收第一笔时的 7,629 格还少）"},
            ],
            "alternatives": [
                "不调给 kaito9 会怎样没有重演。可以确认的是两边的账：这一段 kaito9 收 1,284 万（捐方另交税），=[、stormy 为了吃它 8,901、10,373 格烧了 490 万、343 万——前线让对方每格付 371 兵，后排各号后来只让对方付 58~109 兵",
                "同一段队4 的路人 Portugal 一个号 527 万→900 万兵、58,980→84,169 格；它 5100 拍密度 141，也过了软上限",
                "被围的号能走的只有船：见 D14、D15",
            ],
            "statementType": "inferred", "confidence": "medium",
        },
        {
            "t0": 6000, "t1": 6900,
            "what": "StayObsessed 坐船过来，一条指令吃一个号：6579~6914 拍 7 个号出局",
            "shareKind": "队4 占全图陆地", "shareBefore": 0.397, "shareAfter": 0.243,
            "enemyShareBefore": 0.557, "enemyShareAfter": 0.733,
            "squadShareBefore": 0.2038, "squadShareAfter": 0.0882,
            "ourBots": ["zero_7", "sora_w", "leo_tx", "alex_k", "kaito9", "ryan_m", "talon5", "zexos1"],
            "enemies": ["StayObsessed#27（队3）", "🌞#12（队3）", "stormy#30（队3）"],
            "evidence": [
                "out/trace/A071-q-p27-cmds.txt：StayObsessed 5908 拍船 pct 143、135 万兵（落点是 alex_k 的地），6097 拍 140 万 → zexos1，6440 拍 136 万 → alex_k，6517 拍 129 万 → zero_7，6566 拍 121 万 → sora_w，6615 拍 128 万 → leo_tx，6664 拍 122 万 → Jun，"
                "6713 拍 112 万 → talon5，6755 拍 110 万 → alex_k，6776 拍 99.7 万 → kaito9，6790 拍 90.6 万 → ryan_m，6909 拍 109 万 → talon5；发令前余额 821 万~1,232 万",
                "卷宗[G]：zero_7 6540 拍 3,089 格/6.7 万兵、压在身上 118 万；sora_w 6600 拍 31.4 万兵、压 104 万；leo_tx 6660 拍 31.8 万、压 102 万；kaito9 6780 拍 27.3 万、压 93.6 万；ryan_m 6780~6840 拍丢 5,088 格",
                "卷宗[O]：6600~6900 拍队4 34.8%→24.3%：在控的号 −7.67 点、Jun 的空壳 −1.80 点（11,950 格，对方只烧 7.1 万）。卷宗[F]：StayObsessed 吃 alex_k 10,350 格（烧 287 万）、leo_tx 7,454（85.1 万）、sora_w 6,894（75.5 万）、ryan_m 6,281（60.1 万）、talon5 5,887（135 万）、kaito9 4,495（50.7 万）、zero_7 3,420（22.7 万）",
                "out/trace/A071-q-squad-6040-6950.txt（cmdq.py --sum）：这一段编队 35 条指令——给 zexos1 的协防 10 笔 185 万（6062~6615 拍，7 个号）、给 alex_k 6 笔 71.0 万（6321~6356 拍）；alex_k 6461 拍 11.3 万打 StayObsessed（全在反击槽里对消）；zexos1 6552~6874 拍 7 条 170 万打 🌞；leo_tx、talon5 各 3 条 pct 47 扩无主地；zexos1 3 条船送出 103 万",
                "A071-donwhy.txt：正在挨打的候选受捐人判定合计 A:dMe 425、doomed:x1.65 106、ok 75、doomed:small 23；zero_7 doomed 26、sora_w doomed 25、leo_tx doomed 38 / A:dMe 46",
                "out/trace/A071-q-t3-vs-portugal.txt：6300 拍 StayObsessed 88,785 格/1,112 万兵（密度 125）、Portugal 89,349 格/841 万（94）、🌞 126,230 格/494 万（39）。out/trace/A071-q-portugal-5800-7400.txt：Portugal 6664 拍一条 92.4 万打 StayObsessed，其余 15 条打 =[、stormy、Player 224",
            ],
            "priorDecisions": [
                {"t": "4500~6000", "bot": "后排 8 个号", "what": "把兵调给 kaito9，6000 拍各号密度 31~45",
                 "codePath": f"{VB} Policy.tryDonateToTeammate L4463-4473、L4474-4494",
                 "why": "StayObsessed 每条 90.6~140 万兵；6300 拍后排 7 个小号的余额 13.1~78.8 万（zexos1 271 万、noah88 112 万）；zero_7、leo_tx、ryan_m、sora_w 让对方每格只付 58~109 兵"},
                {"t": "6040~6790", "bot": "还没挨打的号", "what": "正在挨打的小号被判 doomed（压在身上的兵 > 1.65 倍余额），不救；自己也不够密",
                 "codePath": f"{VB} L4455-4456（isDoomedPocket）、L4463-4466（Case A 的 dMe 门槛）",
                 "why": "zero_7、sora_w、leo_tx 最后 500 拍收捐都是 0；一条 129 万的指令压上来，6480 拍只有 11.1 万兵的号怎么救都不够"},
            ],
            "alternatives": [
                "后排如果留着 4500 拍的密度（49~107），StayObsessed 这几条指令够不够吃没有重演；能确认的只是单价：kaito9 那条线上对方每格付 371 兵，被抽薄的后排 58~109 兵",
                "路人 Jun 5859 拍离线：空壳 6000~6100 拍被 🌞 吃 10,182 格、6600~7200 拍被 StayObsessed 吃其余，对方几乎不花兵；空壳的地队友接不过来",
            ],
            "statementType": "observed", "confidence": "high",
        },
        {
            "t0": 6900, "t1": 7800,
            "what": "剩下的 zexos1、noah88 被 🌞、StayObsessed 吃掉，路人 Portugal 最后被三家分掉",
            "shareKind": "队4 占全图陆地", "shareBefore": 0.243, "shareAfter": 0.048,
            "enemyShareBefore": 0.733, "enemyShareAfter": 0.942,
            "squadShareBefore": 0.0882, "squadShareAfter": 0.0,
            "ourBots": ["zexos1", "noah88"],
            "enemies": ["🌞#12（队3）", "StayObsessed#27（队3）", "Player 436#31（队3）"],
            "evidence": [
                "卷宗[F]：🌞 → zexos1 6420~7560 拍吃 28,125 格、烧 876 万（zexos1 掉 387 万 + 反击槽 96.1 万）；StayObsessed → noah88 7080~7650 拍吃 23,371 格、烧 495 万",
                "out/trace/A071-q-p12-cmds.txt、A071-q-t3-vs-portugal.txt：🌞 的余额 6300 拍 494 万 → 7200 拍 53.3 万（密度 3）；out/trace/A071-acts-samples.txt：zexos1 6540 拍余额 324 万/33,502 格，🌞 报价 67.24 对 worth 86.92，压在身上 112 万",
                "卷宗[G]：zexos1 7178 拍被清场（8,419 格/43.2 万兵），noah88 7351 拍（6,470 格/24.3 万兵）；之后靠船在无主地上各留 76~809、64~202 格。out/trace/A071-q-p27-cmds.txt：StayObsessed 7098 拍 pct 225、243 万兵打 noah88，7245、7343 拍 227 万、225 万",
                "卷宗[O]：7500~7800 拍 Portugal 77,711→31,830 格，被 StayObsessed 吃 25,781 格（烧 917 万）、Player 436 9,727 格、=[ 6,129 格",
            ],
            "priorDecisions": [
                {"t": "6540~6660", "bot": "zexos1", "what": "对正在用船打自己的 🌞 还手：两串各 3 条",
                 "codePath": f"{VB} Policy.buyLand L5595-5607（buyLand:5607）",
                 "why": "报价 67~77 低于 worth 87~99，价格上该打；但出去的兵先和 🌞 压过来的兵 1:1 对消：烧 73.5 万里 66.5 万是对消，只拿 550 格"},
            ],
            "alternatives": [
                "这时队3 81.7%（7200 拍），怎么打都守不住；记在这里是因为 🌞 是队3 最薄的大号（6000~6900 拍密度 23~39），编队整局对它只烧过 73.5 万",
            ],
            "statementType": "observed", "confidence": "medium",
        },
    ],
    "deaths": {
        "zero_7": {"cause": "名下 4,087 格，1638 拍一批 9 条把 21.8 万里的 20.2 万打出去，随后被 [PL] Recover 吃 3,196 格；整局峰值 4,503 格。4415 拍起被围，6 笔 31.9 万调给 kaito9（4945 拍那条发令时自己密度 31）。"
                             "StayObsessed 6517 拍一条 129 万兵压上来，它 6480 拍只有 11.1 万兵；对方吃 3,420 格只烧 22.7 万；判 doomed 26 次，最后 500 拍收捐 0。1,083 格/1.3 万兵时出局",
                    "patternIds": ["R07-SP-CLUSTER", "NEW:IO-lag-burst", "NEW-R03-DN03", "NEW-R03-EC01", "R08:挨打的小号被判弃子"]},
        "sora_w": {"cause": "和路人 Jun 出生点只隔 9 像素，名下 3,402 格。4420 拍起被围，7 笔 86.6 万调给 kaito9，6300 拍 37.9 万兵（密度 42）。StayObsessed 6566 拍一条 121 万兵，吃 6,894 格烧 75.5 万；判 doomed 25 次。2,119 格/4.3 万兵时出局",
                   "patternIds": ["R07-SP-CLUSTER", "NEW-R03-DN03", "NEW-R03-EC01", "R08:挨打的小号被判弃子"]},
        "leo_tx": {"cause": "名下 4,324 格。1743 拍一批 9 条花掉余额 80%，被 [PL] Recover 吃 3,831 格；之后吃 [EU]Player 615 10,331 格。4010 拍起被围，7 笔 89.0 万调给 kaito9，4284 拍后均密 41。"
                            "StayObsessed 6615 拍一条 128 万兵（它 6600 拍 40.7 万兵），吃 7,454 格烧 85.1 万；判 doomed 38 次。2,258 格/4.9 万兵时出局",
                   "patternIds": ["R07-SP-CLUSTER", "NEW:IO-lag-burst", "NEW-R03-DN03", "NEW-R03-EC01", "R08:挨打的小号被判弃子"]},
        "alex_k": {"cause": "和 zexos1 叠点，名下 3,379 格。整局收捐 344 万，吃 [PL] Recover 6,919 格（烧 222 万），4500 拍 13,054 格；之后 8 笔 164 万调给 kaito9，密度 107（4500 拍）→45（6000 拍）。"
                            "StayObsessed 的船 5908 拍开向它的岸，6300 拍起吃它，6440、6755 拍两条 136 万、110 万；收到协防 71.0 万，对方烧 287 万吃 10,350 格。2,704 格/17.3 万兵时出局",
                   "patternIds": ["R07-SP-OVERLAP", "NEW-R03-DN03", "NEW-R03-EC01", "R08:救援门槛够不着"]},
        "kaito9": {"cause": "和 talon5 叠点，名下 4,275 格；1500~4284 拍超软上限 790 拍，对 Player 255 一直报价高于 worth。4326 拍起收 57 笔 1,284 万，过软上限后对 =[、stormy 按 2~3 倍 worth 的报价连发："
                            "烧 480 万、112 万换来的 9,530、1,225 格又被吃回 8,901、10,373 格。6160 拍起被围、39.9 万兵（6300 拍），反过来给 zexos1 协防。StayObsessed 6776 拍一条 99.7 万兵，吃 4,495 格。2,768 格/7.2 万兵时出局",
                   "patternIds": ["R07-SP-OVERLAP", "NEW-AT-CAPDUMP", "NEW-R03-IO01", "NEW-R03-DN03", "R08:出手后变薄，随后被吃"]},
        "ryan_m": {"cause": "最北的号，1865 拍起被围，2100 拍后 8,047~8,256 格没动过。每 300 拍左右捐一次（整局捐出到账 182 万、税 40.5 万），4284 拍后均密 40。StayObsessed 6790 拍一条 90.6 万兵（它 6780 拍 30.7 万兵），60 拍丢 5,088 格。1,975 格/3.4 万兵时出局",
                   "patternIds": ["R07-SP-CLUSTER", "R07-EC-BOXED-RICH", "NEW-R03-DN03", "NEW-R03-EC01"]},
        "talon5": {"cause": "和 kaito9 叠点，名下 3,271 格（最小）。1500~1680 拍对 [USA] 的空壳发 37 条小指令；1500~4284 拍均密 82、超软上限 880 拍。4291 拍的船靠在 kaito9 的岸上（船上 11.4 万到账 3.5 万）。"
                            "StayObsessed 6713、6909 拍两条 112 万、109 万兵，吃 5,887 格（烧 135 万）；stormy 最后补了 190 格。1,741 格/8.2 万兵时出局",
                   "patternIds": ["R07-SP-OVERLAP", "NEW-R03-OP01", "NEW:FE-tiny-cmd-fee", "NEW-R03-SE04", "R07-EC-BOXED-RICH"]},
        "zexos1": {"cause": "名下最大（37,671 格），吃 AI 和 [EU]Player 615 到 44,555 格（3720 拍）；3440 拍起被围。整局利息 1,449 万，捐出到账 696 万、税 242 万（给 kaito9 10 笔 516 万）。"
                            "6000 拍 173 万兵（密度 39）；6030 拍起 StayObsessed 吃 13,197 格，🌞 6398 拍起用船打，吃 28,125 格（烧 876 万）。还手 73.5 万里 66.5 万在槽里对消。7178 拍 8,419 格/43.2 万兵时被清场，靠船留到 7549 拍",
                   "patternIds": ["NEW-R03-DN03", "NEW-R03-DN02", "NEW-R03-EC01", "NEW-R03-SE03", "R08:出手后变薄，随后被吃"]},
        "noah88": {"cause": "名下 26,484 格，1589、1652 拍两批吃下 simba，4140 拍 29,685 格后被围。4151 拍 49.7 万兵的船在海上 542 拍被打光；7 笔 278 万调给 kaito9，4284 拍后均密 47。"
                            "7098 拍起 StayObsessed 4 条 243 万、227 万、225 万、439 万兵，吃 23,371 格（烧 495 万）；7080 拍它 232 万兵。7351 拍 6,470 格/24.3 万兵时被清场，7679 拍出局",
                   "patternIds": ["NEW:IO-lag-burst", "NEW-R03-SE02", "NEW-R03-DN03", "NEW-MT-OUTNUMBERED"]},
    },
    "decisions": [
        {"t": "选点期", "bot": "全部 9 个号", "kind": "spawn", "verdict": "error",
         "state": "9 个号落在东北角一团；alex_k+zexos1、kaito9+talon5 两对各落在同一个坐标（相距 5、6 像素）",
         "codePath": f"{SPAWN} solve L790、L1065-1170、L1262-1268 → matchBotsToTargets L1431-1493（本房间的求解行不在日志里）",
         "why": "名下 95,168 格 = 全图 14.32%，份额÷人头 0.70；7 个号名下 3,271~8,275 格",
         "estCost": "按其他真人人均名下 16,496 格算，编队人均 10,574 格（0.64 倍）", "patternId": "R07-SP-CLUSTER / R07-SP-OVERLAP",
         "evidenceRef": "out/dossier/A071-land.txt [G1]；卷宗[D]；A071-ledger-brief.txt [B1]"},
        {"t": "60~600", "bot": "全部", "kind": "attack", "verdict": "good",
         "state": "开局扩中立：0~600 拍 77 条指令延迟 P50 12 拍，全部生效",
         "codePath": f"{VB} V13.dpNeutral L2383-2412（dpNeutral:2406）",
         "why": "630 拍单号地中位 2,674 对其他真人 2,490；实际÷名下 0.27 对 0.16",
         "estCost": "无", "patternId": "NEW:OP-cycle-open",
         "evidenceRef": "A071-ledger-brief.txt [B2][B3][B7]；卷宗[D]"},
        {"t": "600~1495", "bot": "talon5、kaito9、ryan_m 等", "kind": "attack", "verdict": "error",
         "state": "贴着 AI 的决策拍被 safeFinite 冻住 446 个（27.5%），399 个去掉这一项就出手；talon5 117（kaito9×46、ryan_m×32）、kaito9 100、ryan_m 77",
         "codePath": f"{VB} Style.pickTarget L1144-1177 → Policy.winFloor L4562-4570 → V17.safeFinite L2757-2768",
         "why": "278 拍的绑定方是编队友——队友的余额被当成威胁。名下范围内的 AI 地到 1800 拍编队只拿到 44.9%，敌方真人 25.7%",
         "estCost": "1500 拍比其他真人的转化少 15,557 格（三层合计，不能单独归到这一层）", "patternId": "NEW-R03-OP01",
         "evidenceRef": "out/dossier/A071-freeze.txt 第一段；A071-ledger-brief.txt [B8][B9]"},
        {"t": "900~1500", "bot": "noah88、zexos1 等", "kind": "attack", "verdict": "error",
         "state": "页面落后：指令等 90~201 拍，同一个决定每个决策拍再发一遍。noah88 成交 128 条里 41 条目标已死、62 条是同批重复落地",
         "codePath": f"{VB} General.act L794-797（act:796）、Policy.buyLand L5449-5453（buyLand:5453）→ Policy.send L3800-3877，都不看在途的兵",
         "why": "600~1500 拍打 AI/真人的 56.0 万兵里 19.7 万落地时目标已死，34 条作废；名下最大的 zexos1、noah88 1500 拍只拿到名下的 0.35、0.33",
         "estCost": "同上（1500 拍少 15,557 格）", "patternId": "NEW:IO-lag-burst / NEW-R03-IO01",
         "evidenceRef": "A071-delay.txt [L2][L4]；影子摘要[S1][S3]；卷宗[J]"},
        {"t": "1500~1575", "bot": "noah88", "kind": "attack", "verdict": "good",
         "state": "对密度 5 的 simba（1530 拍 3.1% 的地、11.0 万兵）出手：报价 15.01 对 worth 26.16",
         "codePath": f"{VB} Policy.buyLand L5420-5427 → L5611-5616（buyLand:5616）",
         "why": "烧 18.5 万拿 13,057 格，地 8,748→19,209（1800 拍），simba 2273 拍出局。指令是 6 + 9 条分两批落地的（花掉余额 86%、84%），这回没人来打",
         "estCost": "无", "patternId": "NEW-R03-AT01 / NEW:IO-lag-burst",
         "evidenceRef": "卷宗[F][J]；out/trace/A071-acts-samples.txt"},
        {"t": "1500~1545", "bot": "zero_7", "kind": "attack", "verdict": "error",
         "state": "3,990 格、16.3 万兵；对 [EU]Player 615 每个决策拍发一条，9 条等 93~138 拍后 1638 拍一起落地",
         "codePath": f"{VB} Policy.buyLand L5420-5427 → L5611-5616",
         "why": "21.8 万里出去 20.2 万（93%），对 [EU]Player 615 只烧 2.6 万、拿 1,058 格；兵在外面的 250 拍里余额 7.6 千~2.4 万，被 [PL] Recover 吃 3,196 格（对方烧 12.8 万），1890 拍退回 14.0 万兵时地剩 1,989 格",
         "estCost": "3,196 格（它当时 3,990 格）", "patternId": "NEW:IO-lag-burst / NEW-R03-IO01",
         "evidenceRef": "卷宗[J][F][E]；A071-ledger-brief.txt [B5]；out/trace/A071-q-flush-880-1800.txt；out/trace/A071-q-zero7-1620-2100.txt"},
        {"t": "1500~1834", "bot": "talon5、kaito9", "kind": "attack", "verdict": "error",
         "state": "talon5 本地 1500~1680 拍对 [USA] 的空壳发 37 条 pct 12~18，落地 18 条（出 7.1 万）；kaito9 1806~1834 拍 8 条 pct 0~4 扩无主地",
         "codePath": f"{VB} General.act L794-797（act:796）；攻击费按整笔余额的 12/1024 收（{SIM}/game.js）",
         "why": "talon5 手续费 5.0 万、实际烧 4.4 千（拿 2,211 格）；kaito9 送出 5.5 千、手续费 2.0 万",
         "estCost": "手续费 5.0 万、2.0 万", "patternId": "NEW:FE-tiny-cmd-fee",
         "evidenceRef": "out/trace/A071-q-tinycmd.txt；卷宗[E]（talon5 1500~1800 拍）[J]"},
        {"t": "1860~3510", "bot": "zexos1、leo_tx、noah88", "kind": "attack", "verdict": "good",
         "state": "三个号吃正在垮的 [EU]Player 615（队2）",
         "codePath": f"{VB} Policy.buyLand L5595-5607（buyLand:5607）、L5574-5585（buyLand:5585）",
         "why": "烧 125 万、41.3 万、53.7 万，拿 15,102、10,331、4,946 格（交换比 0.47~0.49）；zexos1 3720 拍到 44,555 格",
         "estCost": "无", "patternId": "NEW-R03-AT01",
         "evidenceRef": "卷宗[F]"},
        {"t": "2925~3095", "bot": "kaito9、talon5", "kind": "donate", "verdict": "error",
         "state": "密度 113、114 的号给正在推进的 zexos1（密度 38、49）发进攻档调度 pct 193、200，连续 7 + 4 条被额度拒",
         "codePath": f"{VB} Policy.tryDonateToTeammate L4474-4494 → L4500-4506（不读额度）；{SIM}/game.js donationCost L348-357",
         "why": "方向是对的，发不出去：首次需 69、68 点，剩 64、14 点。整局调度 134 条里额度拒 22 条",
         "estCost": "kaito9 78.8 万→88.1 万兵一直贴在软上限以上", "patternId": "NEW-R03-DN01",
         "evidenceRef": "卷宗[H]"},
        {"t": "3120~4440", "bot": "alex_k（收款）", "kind": "donate", "verdict": "good",
         "state": "ryan_m、talon5、leo_tx 等给贴着 [PL] Recover 的 alex_k 21 笔 344 万",
         "codePath": f"{VB} Policy.tryDonateToTeammate L4474-4494（进攻档）；Policy.buyLand L5595-5607",
         "why": "alex_k 烧 222 万从 [PL] Recover 手里拿 6,919 格（交换比 0.46），地 5,455（1800 拍）→13,054（4500 拍）",
         "estCost": "无", "patternId": "R07-GOOD-FED-PUSH",
         "evidenceRef": "卷宗[F][N]"},
        {"t": "4440~4840", "bot": "zexos1、alex_k、sora_w、leo_tx 等 7 个号", "kind": "donate", "verdict": "error",
         "state": "被围的捐方（密度 58~105）给 kaito9 发产出档调度 19 条；发令时 kaito9 密度 91~140，12 条时 ≥100",
         "codePath": f"{VB} Policy.tryDonateToTeammate L4474-4494：L4479 reqD = 58、L4480 maxAllyD = 128/140（注释 L4476-4478 写的是 ≥98、<92）→ L4500-4506",
         "why": "19 条里受捐方都比捐方密：兵从利息为正的地方搬到利息为负的地方，税另收。pingpong：106/129 笔落地当拍双方利息合计下降",
         "estCost": "4000~4999 拍全场成交 47 笔 1,214 万、税 364 万", "patternId": "NEW-R03-DN03",
         "evidenceRef": "out/trace/A071-q-dispatch-kaito9.txt；out/trace/A071-pingpong.txt [3]；卷宗[H]"},
        {"t": "4505~5943", "bot": "8 个被围的号", "kind": "donate", "verdict": "unclear",
         "state": "协防档调度 37 条给正在被 =[、stormy 打的 kaito9；捐方密度 31/44/60，受捐方 69/91/135",
         "codePath": f"{VB} L4457（underFire）→ L4463-4473（Case A：被围 reqD 30/42，留底 22/32×领土）→ L4500-4506",
         "why": "前线确实让对方每格付 371 兵（后排 58~109），但 kaito9 最后比收第一笔时还少地；后排密度掉到 31~45，6000 拍后被 StayObsessed 一条指令吃一个",
         "estCost": "kaito9 收 1,284 万；=[、stormy 吃它烧 490 万 + 343 万", "patternId": "NEW-R03-DN03 / NEW-R03-EC01",
         "evidenceRef": "out/trace/A071-q-dispatch-kaito9.txt；卷宗[F][L]；out/trace/A071-q-squad-snap.txt"},
        {"t": "4780~5960", "bot": "kaito9", "kind": "attack", "verdict": "error",
         "state": "余额 215~247 万、密度 125~150、over=1；对 =[ 的报价 193~386、对 stormy 240 对 worth 112~135，每个脉冲 pct 122",
         "codePath": f"{VB} Policy.buyLand L5353、L5359（!over 才 break）、L5440-5444 → L5595-5607、L5574-5585",
         "why": "对 =[ 烧 480 万拿 9,530 格（交换比 0.26，227 万在反击槽对消），对 stormy 烧 112 万拿 1,225 格（0.21）；两家同时吃回 8,901 + 10,373 格",
         "estCost": "攻击费 125 万；真人对消 330 万", "patternId": "NEW-AT-CAPDUMP",
         "evidenceRef": "卷宗[F][L]；out/trace/A071-acts-samples.txt；out/trace/A071-q-kaito9-press.txt"},
        {"t": "3090~6660", "bot": "kaito9、alex_k、zexos1 等", "kind": "attack", "verdict": "error",
         "state": "延迟正常时每个脉冲也在第一条落地前再发 1~2 遍：3000 拍后 52 串，首条 831.9 万、后续 1,167.5 万",
         "codePath": f"{VB} Policy.buyLand L5596 的在途检查在上一条没落地时是 0",
         "why": "kaito9 4780~4795 拍对 =[：首条 30.3 万、多花 49.6 万；zexos1 6540~6550 拍对 🌞：首条 32.3 万、多花 80.7 万",
         "estCost": "后续÷首条 1.40", "patternId": "NEW-R03-IO01",
         "evidenceRef": "A071-delay.txt [L5]；影子摘要[S6]"},
        {"t": "4151", "bot": "noah88", "kind": "boat", "verdict": "error",
         "state": "被围、374 万兵；发一条 pct 135 的船（49.7 万兵、船费 11.7 万），落点是队1 的 N***** 的岸，航线 276 像素",
         "codePath": f"{VB} Policy.idleBoats L5019-5070 → boatOut L1011",
         "why": "在海上 542 拍：衰减到 24.5 万（4600 拍），4624 拍起被 N***** 的船打 70 拍，4694 拍只剩 95 兵消失，没有靠岸",
         "estCost": "49.7 万兵 + 船费 11.7 万", "patternId": "NEW-R03-SE02",
         "evidenceRef": "out/trace/A071-boatlife-noah88-zexos1.txt；out/trace/A071-q-squad-boats.txt"},
        {"t": "6069~6419", "bot": "zexos1", "kind": "boat", "verdict": "error",
         "state": "StayObsessed、🌞 正在打它时发 3 条船去无主地：6069 拍 26.0 万，6363、6419 拍 40.0 万、36.5 万去同一个落点 (1450,697)",
         "codePath": f"{VB} Policy.idleBoats L5019-5070 → boatFood L2017",
         "why": "后两条在海上 228、229 拍，到岸 27.9 万、25.7 万——第二条到的时候落点已是自己的地。三条船费 6.5 万、10.0 万、9.1 万",
         "estCost": "三条送出 103 万、船费 25.6 万；后两条有 228、229 拍不在家", "patternId": "NEW-R03-SE03",
         "evidenceRef": "out/trace/A071-boatlife-noah88-zexos1.txt；out/trace/A071-boat-audit.txt；out/trace/A071-q-squad-6040-6950.txt"},
        {"t": "4676、4837", "bot": "kaito9", "kind": "boat", "verdict": "error",
         "state": "两条 pct 0 的船：送出 1.1 千、2.0 千兵，船费 3.4 万、6.5 万",
         "codePath": f"{VB} Policy.idleBoats L5019-5070 → boatOut L1011；船费按整笔余额的 32/1024 收",
         "why": "余额 108 万、208 万的号发一条装兵比船费少的船",
         "estCost": "船费 3.4 万、6.5 万", "patternId": "NEW:FE-tiny-cmd-fee",
         "evidenceRef": "out/trace/A071-q-squad-boats.txt；out/trace/A071-boat-audit.txt"},
        {"t": "6062~6356", "bot": "kaito9、noah88 等（捐给 zexos1、alex_k）", "kind": "donate", "verdict": "unclear",
         "state": "StayObsessed 上岸后，6062~6615 拍 10 笔协防 185 万给 zexos1，6321~6356 拍 6 笔 71.0 万给 alex_k",
         "codePath": f"{VB} Policy.tryDonateToTeammate L4463-4473（Case A）",
         "why": "给到了：alex_k 让对方烧 287 万才吃掉 10,350 格。但捐方自己随后就是下一个：kaito9 6062 拍捐出到账 22.3 万、税 6.6 万（pct 216，余额 105 万），6300 拍只剩 39.9 万",
         "estCost": "不明", "patternId": "R08:救援门槛够不着 / NEW-R03-EC01",
         "evidenceRef": "out/trace/A071-q-squad-6040-6950.txt；卷宗[F][G]"},
        {"t": "6510~6850", "bot": "zero_7、sora_w、leo_tx、ryan_m、kaito9（挨打）", "kind": "defend", "verdict": "unclear",
         "state": "StayObsessed 每条 90.6~129 万兵压在 11.1~40.7 万兵的号上；候选受捐判定 doomed:x1.65 106 次",
         "codePath": f"{VB} L4455-4456（isDoomedPocket：压在身上 > 1.65×余额）",
         "why": "5 个号最后 500 拍收捐都是 0。按规则不救是对的（救不动），问题在更早：后排的兵 4500~6000 拍已经搬走了",
         "estCost": "不明", "patternId": "NEW-DF-NORESCUE / R08:挨打的小号被判弃子",
         "evidenceRef": "A071-donwhy.txt；卷宗[G]"},
        {"t": "6540~6660", "bot": "zexos1", "kind": "attack", "verdict": "unclear",
         "state": "6540~6550 拍余额 324~364 万，对正在打它的 🌞 报价 67~77、worth 87~99；6650~6660 拍余额 309~313 万，报价 73~74、worth 85。两串各 3 条",
         "codePath": f"{VB} Policy.buyLand L5595-5607（buyLand:5607）",
         "why": "烧 73.5 万里 66.5 万是和 🌞 压过来的兵对消，只拿 550 格；另有 4 次对 🌞 的出手被守卫挡掉",
         "estCost": "不明（对消掉的兵本来也要用来守）", "patternId": "NEW-R03-IO01 / NEW-R03-IO02",
         "evidenceRef": "卷宗[F]；out/trace/A071-acts-samples.txt；影子摘要[S5][S6]"},
        {"t": "463~6870", "bot": "全部", "kind": "attack", "verdict": "error",
         "state": "isNoFullSend 9/9 被翻成 true；之后 60 次出手被 Policy.send 的守卫挡掉：kaito9 33（=[×19、stormy×8、Pugo×4）、alex_k 8（StayObsessed×3）、zexos1 8（🌞×4）、talon5 6",
         "codePath": f"{VB} Policy.updateShadowQuota L3821-3834 → Policy.send L3844 守卫",
         "why": "翻转的起因是一条小指令的「实发」比想发的少（talon5 694 拍想发 1.3 千、余额只降 440）；之后整局生效",
         "estCost": "不明", "patternId": "NEW-R03-IO02",
         "evidenceRef": "影子摘要[S5]"},
        {"t": "6543、6623", "bot": "zexos1、alex_k（收款）", "kind": "donate", "verdict": "good",
         "state": "路人 Jun 的空壳把余额送给队友：6543 拍 zexos1 收 41.8 万（送出方原有 44.6 万），6623 拍 alex_k 2.8 万",
         "codePath": f"{SIM}（引擎 botDonate→botGive，不是玩家指令，不占受捐额度）",
         "why": "表外进项 44.7 万 = 编队总利息的 1.0%；对面队3 的空壳一共送了 316 万（Player 224 → =[ 162 万）",
         "estCost": "无", "patternId": "NEW-R03-EX01",
         "evidenceRef": "卷宗[L][N]"},
    ],
    "newPatterns": [
        pat("NEW-R03-DN03",
            [{"t": "4440~4840", "bot": "zexos1、alex_k、sora_w、leo_tx、ryan_m、talon5、zero_7 → kaito9", "note": "产出档 19 条：捐方密度 58/59/105，受捐方 91/114/140；19/19 受捐方更密，12/19 受捐方 ≥100"},
             {"t": "4505~5943", "bot": "8 个被围的号 → kaito9", "note": "协防档 37 条：捐方密度 31/44/60，受捐方 69/91/135；37/37 受捐方更密，16/37 受捐方 ≥100"},
             {"t": "4326~5943", "bot": "kaito9（收款）", "note": "57 笔 1,284 万；zexos1→kaito9 10 笔落地当拍双方利息合计全部 ≤0"}],
            "本局计数：全部 134 条调度里受捐方比捐方密的 协防 48/64、产出 25/33、进攻 6/37；受捐方密度 ≥100 的 协防 16/64、产出 12/33。全场成交 129 笔（编队 110 笔）里 106 笔落地当拍双方每 10 拍利息合计 ≤0（这些笔的税 562 万）。"
            "受捐方随后的出手：kaito9 对 =[ 烧 480 万拿 9,530 格（交换比 0.26）"),
        pat("NEW-R03-EC01",
            [{"t": "4284~6579", "bot": "zero_7", "note": "4284 拍后均密 34；StayObsessed 吃它每格 58 兵"},
             {"t": "4284~6753", "bot": "leo_tx", "note": "均密 41；每格 81 兵"},
             {"t": "4284~6851", "bot": "ryan_m", "note": "均密 40；每格 90 兵"},
             {"t": "4284~6682", "bot": "sora_w", "note": "均密 48；每格 109 兵"}],
            "对照：没被抽薄的 kaito9 让对方每格付 371 兵，zexos1 268、alex_k 246。4284 拍后利息实得÷满额：zero_7 38%、ryan_m 44%、leo_tx 45%、sora_w 49%"),
        pat("NEW-R03-DN01",
            [{"t": "2925~3075", "bot": "kaito9 → zexos1", "note": "7 条 pct 193：首次需 69 点、剩 64 点"},
             {"t": "3020~3095", "bot": "talon5 → zexos1", "note": "4 条 pct 200：需 68 点、剩 14 点"},
             {"t": "4180~4255", "bot": "noah88 → alex_k", "note": "4 条 pct 320：需 57 点、剩 17 点"},
             {"t": "4010~4060", "bot": "leo_tx → alex_k", "note": "3 条 pct 320：需 36 点、剩 27 点"}],
            "调度日志 134 条，没成交 24 条，其中额度拒 22 条"),
        pat("NEW-R03-OP01",
            [{"t": "600~1495", "bot": "talon5", "note": "117 个决策拍：kaito9×46、ryan_m×32、Player 255×26"},
             {"t": "600~1495", "bot": "kaito9", "note": "100 个：Player 255×47、ryan_m×30、talon5×23"},
             {"t": "600~1495", "bot": "ryan_m", "note": "77 个：kaito9×50、talon5×26"}],
            "1,620 个决策拍里冻结 446（27.5%），卡在编队友 278、同队路人 21、敌方真人 147；去掉这一项当拍能出手 399"),
        pat("NEW-R03-IO01",
            [{"t": "4780~4795", "bot": "kaito9 → =[", "note": "3 条：首条 30.3 万、多花 49.6 万"},
             {"t": "6540~6550", "bot": "zexos1 → 🌞", "note": "3 条：首条 32.3 万、多花 80.7 万"},
             {"t": "4345~4360", "bot": "alex_k → [PL] Recover", "note": "4 条：首条 17.8 万、多花 40.8 万"}],
            "整局 84 串 225 条：首条 853.7 万、后续 141 条 1,199.1 万（1.40 倍）；3000 拍后 52 串首条 831.9 万、后续 1,167.5 万"),
        pat("NEW-R03-IO02",
            [{"t": "780~5950", "bot": "kaito9", "note": "33 次：=[×19、stormy×8、Pugo×4"},
             {"t": "785~6460", "bot": "alex_k", "note": "8 次，其中 StayObsessed×3"},
             {"t": "1305~6870", "bot": "zexos1", "note": "8 次，其中 🌞×4"}],
            "9/9 个号被翻转（463~995 拍，noah88 3340 拍）；守卫挡掉 60 次出手"),
        pat("NEW-R03-SE02",
            [{"t": "4151", "bot": "noah88", "note": "49.7 万兵、船费 11.7 万；航线 276 像素，在海上 542 拍，4694 拍剩 95 兵消失"}],
            "本局 1 条。落点是队1 的 N*****（4500 拍 6.8% 的地、103 万兵、密度 23）的岸，目标本身不差，是路上太久、被对方的船拦下"),
        pat("NEW-R03-SE03",
            [{"t": "6363、6419", "bot": "zexos1", "note": "两条去 (1450,697)：40.0 万、36.5 万兵，船费 10.0 万、9.1 万；第二条靠岸时落点已是自己的地"}],
            "同落点多余 1 条、船费 9.1 万"),
        pat("NEW-R03-SE04",
            [{"t": "4291→4574", "bot": "talon5 → kaito9 的岸", "note": "发船 17.8 万兵、船费 3.4 万，航程 283 拍；靠岸 11.4 万、到账 3.5 万"},
             {"t": "1358→1494", "bot": "sora_w → talon5 的岸", "note": "靠岸 3.4 万、到账 0"}],
            "整局 7 次靠队友岸：船上 18.3 万、到账 7.0 万、蒸发 11.3 万"),
        pat("NEW-R03-DN02",
            [{"t": "4277", "bot": "zexos1 → talon5", "note": "pct 320：到账 53.4 万、税 22.4 万（捐方余额 358 万）"},
             {"t": "4305", "bot": "zexos1 → sora_w", "note": "到账 1.6 万、税 18.7 万"}],
            "zexos1 给 kaito9 的 10 笔里 5 笔被硬上限截短；另有 zexos1→zero_7 到账 25.2 万、税 23.3 万，zexos1→alex_k 到账 27.8 万、税 12.2 万"),
        pat("NEW-R03-EX01",
            [{"t": "6543", "bot": "Jun（空壳）→ zexos1", "note": "到账 41.8 万（送出方原有 44.6 万）"},
             {"t": "6623", "bot": "Jun（空壳）→ alex_k", "note": "到账 2.8 万"}],
            "编队收到 44.7 万；队3 的空壳送出 316 万"),
    ],
    # 时间线表里「编队余额」的万位换算（数取自 out/dossier/A071-facts.json 的 timeline.sqBal；只做单位换算）：
    # 630 拍 44,718；1080 拍 36.3 万；1530 拍 132 万；1800 拍 112 万；2130 拍 172 万；2700 拍 395 万；3060 拍 615 万；3600 拍 675 万；4500 拍 874 万；
    # 5100 拍 684 万；5400 拍 695 万；6000 拍 604 万；6300 拍 691 万；6600 拍 622 万；7200 拍 139 万。
    # 各队在线真人的兵（teamOnlineBal）：1530 拍 队1 109 万、队2 140 万、队3 93.4 万、队4 160 万；3600 拍 队1 1,256 万、队3 1,617 万、队4 900 万；
    # 5100 拍 队3 2,913 万、队4 1,732 万；6300 拍 队3 3,130 万、队4 1,532 万。AI 的地：1080 拍 53.0%、1530 拍 23.4%、1800 拍 9.2%。
    "lossArchetype": "outscaled",
    "winnerNotes": "赢家队3。在线真人 3000 拍起只有 6 个（6300 拍起 5 个），但 4500~6000 拍把队1 的 22.1% 全吃了：40.1%→55.7%，在线真人的兵 2,438 万→2,930 万。"
                   "对编队伤害最大的是 StayObsessed：630 拍 0.3% → 4500 拍 5.2%/346 万兵 → 6300 拍 13.4%/1,112 万 → 7500 拍 31.0%/1,590 万；整局吃编队 81,349 格，自烧 1,444 万。"
                   "打法是一次一个号、一条大指令（pct 112，每条 90.6~140 万兵）：zero_7 11.1 万兵对 129 万、sora_w 31.4 万对 121 万、leo_tx 40.7 万对 128 万、kaito9 28.4 万对 99.7 万、ryan_m 30.7 万对 90.6 万；alex_k、talon5 厚一些（104 万、68.3 万）。"
                   "🌞 是队3 地最多的号（6000 拍 17.2%），兵一直很薄（6000~6900 拍密度 23~39），用船吃 zexos1 28,125 格、自烧 876 万，7200 拍只剩 53.3 万兵。"
                   "=[、stormy 4795、5250 拍起用 pct 112、103 的指令和 kaito9 对耗。队3 的空壳一共给队友送了 316 万兵。别队的捐款是整笔给：BY→Ghadir 一笔 pct 1023 到账 112 万、税 7.5 万",
    "wentWell": [
        "开局扩中立没有问题：0~600 拍延迟 P50 12 拍，630 拍单号地中位 2,674 对其他真人 2,490",
        "noah88 1500 拍选中密度 5 的 simba：烧 18.5 万拿 13,057 格",
        "zexos1、leo_tx、noah88 吃垮掉的 [EU]Player 615：各拿 15,102、10,331、4,946 格，交换比 0.47~0.49",
        "给 alex_k 的进攻档捐款（21 笔 344 万）换到了 [PL] Recover 的 6,919 格",
        "编队 5210 拍到全图 21.89%（人头占 20.45%）；9 个号都活到 6500 拍以后",
    ],
    "unknowns": [
        "页面为什么 900~1800 拍一起落后（全队延迟中位 93、137、104 拍）、1800 拍恢复：9 个号同时发生，日志里没有原因。「一拍最多落 9 条」是从落地记录反推的，桥接层的代码没看",
        "两对叠点出在哪一步：本包日志缺 9 个号本地 720 拍前的行，也没有本房间的选点求解行（全局行 7149367~7149821 一带），只能从录像看到两对号最后一条选点指令的坐标相同",
        "没重演的反事实：后排不把兵调给 kaito9；kaito9 过软上限后不出手；zero_7 1500 拍只发首条；noah88 4151 拍的 49.7 万兵留在家里；kaito9、talon5 2925~3095 拍的兵到了 zexos1 手里",
        "StayObsessed 为什么 5908 拍选了这一团、而不是同样贴着它的 Portugal（6300 拍 841 万兵、密度 94）：真人行为不可见。它的船发令时落点是 alex_k 的地，6030 拍起记到的是吃 zexos1，船在哪儿上的岸没有逐拍查",
        "2 条不是额度拒的未成交调度（talon5→kaito9 4820 拍、zexos1→kaito9 4940 拍）原因没查",
        "kaito9 4354 拍一条 pct 498 的船（36.9 万兵）去 AI69 的地，拿到多少没有单独对账",
    ],
    "mechanicsQuestions": [
        {"q": "整局兵力去向（编队在控期间，卷宗[L]）", "a": "总利息 4,674 万。打真人 34.5%（其中槽内对消 9.2%；83,616 格、141.4 兵/格，不含对消）、挨打掉兵 29.4%、三种手续费 21.0%（攻击费 5.7%、捐款税 14.0%、船费 1.3%）、打中立 1.2%（53,861 格、10.4 兵/格）、打 AI 0.3%（37,700 格、3.9 兵/格）。"
                                               "捐出到账 2,373 万、税 655 万；船出兵 250 万、船费 63.0 万。被真人吃掉 142,277 格，对方烧 3,290 万（每格 231 兵）。"
                                               "全场捐款网络（卷宗[N]）：本编队 110 笔 2,373 万、税 655 万；队1 4 笔 197 万、税 15.9 万；队2 14 笔 20.2 万；队3 1 笔 37.5 万"},
        {"q": "DROP30（卷宗[I]）最重的几个区间", "a": "按主因：捐款 24、挨打 15、攻真人 10、攻 AI 3。zero_7 1620~1710 拍 21.4 万→2.3 万（−89%，9 条打 [EU]Player 615）、leo_tx 1710~1800 拍 20.7 万→2.3 万（−89%，15 条）、"
                                            "noah88 1530~1620 拍 16.3 万→2.9 万（−82%，7 条打 simba）；捐款的：alex_k 4500~4590 拍 140 万→60.6 万（−57%，给 kaito9 连税 87.3 万）、"
                                            "noah88 4140~4230 拍 372 万→219 万（−41%，给 zexos1 连税 120 万 + 发船 61.4 万）、zexos1 4950~5040 拍 221 万→147 万（−34%，给 kaito9 连税 102 万）"},
        {"q": "船在海上会被敌船打吗？", "a": "会。noah88 4151 拍的船在 4624~4694 拍有 70 拍被 N***** 的船打到（40 像素内），35 次一拍内掉兵超过衰减，最后剩 95 兵消失、没有调用 landAt（dbg/boat-life.mjs 逐拍读的引擎状态）"},
        {"q": "进攻兵和对方压过来的兵怎么结算？", "a": "先在槽里 1:1 对消：zexos1 6540~6900 拍打 🌞 烧 73.5 万，其中 66.5 万是「掉反击槽」，只拿 550 格（卷宗[F]）"},
        {"q": "空壳（离线后由内置 AI 托管）送兵要走受捐额度吗？", "a": "不走。Jun 的空壳 6543 拍给 zexos1 41.8 万、费 2.8 万，是引擎 botDonate→botGive（卷宗[L]/[N] 的表外进项）"},
    ],
    "donationAudit": {
        "byBand": "按落地拍：2142 拍前 0，2142~3212 拍 63.8 万，3213~4283 拍 582 万，4284 拍之后 1,727 万",
        "executedByBand": "全场成交按 1000 拍：4000~4999 拍 47 笔 1,214 万（税 364 万），5000~5999 拍 27 笔 579 万（税 144 万），6000~6999 拍 16 笔 256 万（税 57.6 万）",
        "fromRandoms": "路人没有给编队捐过；Jun 的空壳送来 44.7 万（表外）",
        "clipped": "给 kaito9 的 57 笔逐对被硬上限截短：zexos1 5、sora_w 3、noah88 2、alex_k 2、leo_tx 1、ryan_m 1、talon5 1、zero_7 1 笔；zexos1→sora_w 4305 拍到账 1.6 万、税 18.7 万",
        "toOverCap": "给 kaito9 的调度发令时 kaito9 密度 ≥100 的：产出 19 条里 12 条、协防 37 条里 16 条",
        "boats": "靠队友岸 7 次：船上 18.3 万、到账 7.0 万、蒸发 11.3 万",
    },
    "scripts": [
        "scripts/dispatchq.py A071 [--to kaito9 --list]（events.csv 的调度行按类型、捐方是否被围、双方密度统计）",
        "scripts/cmdq.py A071 27 5900 7700；scripts/cmdq.py A071 17 5800 7400；scripts/cmdq.py A071 kaito9 4300 6100 --batch；scripts/cmdq.py A071 squad 6040 6950",
        "scripts/snapq.py A071 squad 1500,3000,4500,5100,6000,6300；scripts/snapq.py A071 17,27,12,41,30 <拍表>；scripts/snapq.py A071 13 5700:7200:100 --press",
        "scripts/acts.py A071 <号> <t0> <t1> --sent；scripts/pingpong.py A071；scripts/boat-audit.py A071；node scripts/dbg/boat-life.mjs A071 noah88,zexos1",
    ],
    "ledgerNotes": {
        "statementType": "observed",
        "sources": "out/dossier/A071-delay.txt [L1]~[L5]；A071-land.txt [G1]~[G4]；A071-ledger-brief.txt [B1]~[B9]；A071-freeze.txt；卷宗[J]；out/trace/A071-q-flush-880-1800.txt",
        "spawn": "本包日志里没有本房间的选点求解行（日志里的 16 轮求解是另一个房间的），解和落地对不了账。录像里 9 个号各落地 8~32 条选点指令，没有号一条都没落地；"
                 "alex_k 最后一步落地 ≥2 条、先发的旧坐标生效；叠点 2 对（alex_k+zexos1、kaito9+talon5）。",
        "latency": "四个时段的发令→落地延迟 P50/P90/最大：0~600 拍 12/16/34，600~1500 拍 90/148/201（259 条里 192 条 >30 拍、129 条 >90 拍），1500~3000 拍 83/154/180，3000 拍后 11/15/20；全局 775 条里 300 条 >30 拍。"
                   "9 个号一起落后（全队窗口的延迟中位：600 拍 15、900 拍 93、1200 拍 137、1500 拍 104、1800 拍 12），没有一个号落后队友 ≥90 拍；出局时页面拍号 − 服务器拍号 +5~+16。"
                   "漏斗：想发 891 → 受理 878 → 落地 775 → 生效 720；600~1500 拍 293→291→259→217，1500~3000 拍 210→203→153→141，3000 拍后 307→307→286→285。捐款受理 134、落地 110（主要是撞额度）。",
        "lateAndReissue": "600~1500 拍打 AI/真人 240 条 56.0 万兵里，103 条 19.7 万兵（35.2%）落地时目标已死、改打无主地，其中 34 条作废；打无主地发出 21.9 万、只烧 3.07 万，至少 86% 回到余额。"
                          "落地前重发：整局 84 串 225 条，首条 853.7 万、后续 141 条 1,199.1 万（1.40 倍），其中 3000 拍后 52 串首条 831.9 万、后续 1,167.5 万（延迟正常时的连发，主要是 kaito9）；"
                          "延迟 >45 拍的补发串 49 串（发 317、落 262，花 150.0 万）。同一拍落 ≥3 条的 35 批（最多 9 条），一批花掉余额 ≥50% 的 11 批 80.0 万兵、≥80% 的 3 批："
                          "zero_7 1638 拍 9 条 93%、noah88 1589 拍 6 条 86%、noah88 1652 拍 9 条 84%；leo_tx 1743 拍 9 条 80%、zexos1 1638 拍 7 条 70%。",
        "land": "出生份额：编队名下 95,168 格 = 全图 14.32%，人头占 20.45%，份额÷人头 0.70；每号名下中位 4,275（3,271~37,671），其他真人中位 14,892（35 个里只有 1 个比编队中位小）。"
                "实际÷份额：630 拍编队 0.27 对其他真人 0.16，900 拍 0.38 对 0.30，1200 拍 0.52 对 0.52，1500 拍 0.59 对 0.75，1800 拍 0.78 对 0.92。"
                "600 拍与编队接壤的 29 个 AI 共 11,346 格，到 1800 拍编队拿到 82.8%、敌方真人 16.1%；名下范围内的 AI 地 30,757 格，编队拿到 44.9%、敌方真人 25.7%、仍属 AI 25.8%。"
                "1500 拍我方名下范围里编队占 46.7%、敌方真人 12.3%、AI 36.0%；编队另有 11,430 格在名下范围之外。",
        "threeLayer": "1500 拍人均地 编队 6,206 对其他真人 12,378 = 0.50 倍 = 出生份额 0.64 倍 × 转化 0.78 倍；按其他真人的转化算该有 71,411 格，实际 55,854 格，少 15,557 格。"
                      "第①层（选点）和第②③层都亏：第②层 600~1500 拍 1,620 个决策拍里 446 个（27.5%）被 safeFinite 冻结，278 个卡在编队友，去掉这一项当拍能出手的 399 个；"
                      "第③层 35.2% 的兵落地时目标已死、34 条作废，186 条延迟 >30 拍。转化的缺口集中在名下最大的两个号：zexos1 0.35、noah88 0.33（其余 7 个号 0.74~1.68）——"
                      "它们没有被冻结（0、24 拍），是指令晚到。",
    },
    "confidenceOverall": "high：重放与 traj 630/630 行逐行相等，影子策略与日志的 HL-TICK 630/630、调度 134/134、开局 4/4、成交 775/775 对上，donate-why 9,474/9,474；数字都是重放精确值。"
                         "判断部分：TP4（把兵调给 kaito9 是亏是赚）是推断——对方确实在这条线上烧了 490 万（=[）、343 万（stormy），不调会怎样没有重演；"
                         "「页面停住→补发」是从落地记录反推的；本包日志缺开局 720 拍，选点求解行不在包里，叠点的成因查不到。tryDonateToTeammate L4325-4518 本局逐行读过",
}
