# -*- coding: utf-8 -*-
"""A033 手写分析（R07）。数字来自 out/A033/ 下的 digest.txt、truth_view.txt / rank.txt / team_density.txt（真引擎重放）、
troop_flow.txt / troop_flow_tp.txt / cmd_effect.tsv / drop30_recon.txt（逐条指令的真实扣款与分阶段流水）、replay_ledger.txt、
quota_truth.txt（引擎配额账）、repeat_sends.txt、front_width.txt、death_chain.txt、spawn_truth.txt、cmd_loss.txt、
shadow_check.txt / shadow_early.txt / shadow_trace_*.txt / shadow_nofull.tsv（影子运行）、watch_*.txt（盯人）；
代码路径指 /agent/repos/c136-data/src/strategy/v27-team-c116-vb.js 与 spawn-coordinator-c116-vb.mjs。"""
from common import np, VB, SPVB

SRC = {
    "oneLine": "T2 输给 T1（8504 拍）。T2 在 4770~7380 一直领先（6120 时 47.1% 对 34.8%），我方 9 个号占 T2 四到五成的地，兵却只有 T2 的 24%~39%："
               "免检期全队把利息地租的两到三成交了手续费（127 笔执行的调度里 92 笔是密度低的号捐给密度高的号），过了软上限的兵又不看价地打出去"
               "（6120~7470 进攻净消耗 862 万、净丢 2,599 格）。T1 的 i🍇TV 花 941 万兵吃掉 T2 最大的真人之后，7465 起把我方密度 20~60 的号逐个打掉。",
    "narrative": [
        "**出生到开局（t<1500）**：协调器选了右上角，9 个号落在 183×213 像素里，最近队友 53~61 像素（同场其他真人到最近同队的中位数是 99~145）；没有重叠，9 个号都落在最后指派的点上。"
        "开局扩张正常（t=195 检查 9/9 OK；t=540 单号中位数 1,993 格、名次中位数 22/57），之后圈里的地分完：riku_x 990、alex_k 1170、noah88 1350、sora_w 1530 起四周全是队友，"
        "前三个从此一格没长（3,322 / 4,363 / 5,217 格）。名次中位数 39/55（990）→40/48（1530，我方 6,102 格对全场 10,438 格）。"
        "这一段打内置 AI 也慢：有 AI 邻居的 1,544 个决策拍里只出手 162 个，零指令的 1,349 拍里 474 拍卡在一条以我方队友余额为准的留底上（影子）。",
        "**配额期前半（1500~2700）**：四个围死号每 25 拍调度一次 31%~37% 余额，1505~2176 的 71 条里 63 条单笔就超过全场上限，只成了 1 条。"
        "ryan_m 300 拍从 Susland 手里拿下 9,489 格，余额只剩 3.6 万（密度 2），随即被 Emo Femboy 3 用 5 万多兵的进攻槽打回去 7,868 格——当时 riku_x、alex_k 各有 36~38 万兵送不出来。"
        "sora_w（11,549 格）被围在里面，1,200 拍没有一条指令生效，余额 13 万→98 万。kaito9、zexos1、ryan_m 随后合力把 Emo Femboy 3 从 20,956 格打到 4,369 格。",
        "**喂出来的推进（2700~4284）**：配额公式换档后每笔能过的额度变大，这一段 37 笔入账把几个收方的额度几乎用满（zero_7 305/309 点、zexos1 268/309、talon5 213/219）。"
        "zero_7 拿到 17 笔 294 万兵，3374~3878 把 McRep（T1）从 21,702 格打到 6,425 格，自己 11,129→29,851 格；全队份额 13.76%（2970）→18.57%（4050）。"
        "4116 ryan_m 的进程掉线（原因不明），引擎 490 拍后把席位判为离开，接管的内置 AI 把 107 万兵分两笔送给了 sora_w 和 alex_k。",
        "**领先期前半（4284~6120）**：配额免检，调度从此几乎每条都成。T2 4770 升到第一，6120 到顶（47.1%）。但兵开始空转：4284~5400 三种手续费占利息地租的 29.7%（其中捐款费 221 万）。"
        "5040 时全队余额 851 万是全局峰值，之后 630 拍利息地租进账 554 万、余额却掉到 541 万，只净增 3,215 格——zero_7 三条连发打一个 3,767 格的目标（多发 136 万兵），"
        "退回的兵撞上硬上限，接着发船（海上掉 36 万）、四笔调度给 sora_w（三笔被对方的硬上限截断，手续费 82 万），密度从 150 掉到 46。",
        "**领先丢掉（6120~7470）**：T1 的 i🍇TV（6120 时 47,551 格 / 649 万兵）先吃 😶‍🌫️，再用 7 条进攻共 941 万吃掉 T2 最大的真人 Player 329（6030 时 46,914 格 / 572 万兵），T2 47.1%→39.9%、T1 34.8%→41.5%。"
        "同一段我方 9 个席位里 6 个没有一格边界贴着敌人，全队的余粮经调度流向 sora_w，由它在一条中位数 57 格宽的边界上打 T3 的两个号：39 条进攻 909 万兵，净 +1,766 格。"
        "zero_7（27,810~34,341 格，隔着 Player 329 面对 i🍇TV）五次把余额的 23%~37% 捐给 sora_w，7200 时密度 33。全队密度 62→46，同队其他真人是 114→117。",
        "**被横扫（7465~8504）**：Player 329 的地归了 i🍇TV，talon5、zero_7 直接贴上它。i🍇TV（7470 时 80,758 格 / 807 万兵，之后又收到 Qq、Thuja 的大额捐款）每次压上 120~200 万兵："
        "talon5 7804 出局、zero_7 8064、alex_k 8168、kaito9 8298、noah88 8319、riku_x 8449；sora_w、zexos1 在最后 30 拍也被打光（断开时结算记 left）。全程打向 i🍇TV 的只有 2 条进攻（talon5 58,960 兵、zero_7 78,800 兵）和 zexos1 终局前的一条船；sora_w 7470 之后的 10 条进攻仍然全部打在 T3 身上。",
    ],
    "extraCommands": [
        "node /agent/repos/c136-data/src/tools/replay_cmds.mjs A033 --out c136-review/agents/R07/out/A033/cmds.tsv",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/60_truth.cjs A033",
        "python3 61_truth_view.py A033", "python3 62_rank.py A033 --at 180,540,990,1530,1980,2970,3960,4590,5400,6120,6570,7020,7380,7470,7740,8010,8190,8370",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/67_troop_flow.mjs A033 --cuts 0,1500,2700,4284,5400,6200,7470",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/67_troop_flow.mjs A033 --cuts 0,5040,5670,6120,7470 --tag tp",
        "python3 63_replay_ledger.py A033", "python3 64_cmd_loss.py A033",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/69_quota_truth.mjs A033",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/66_spawn_truth.mjs A033",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/65_shadow.mjs A033 --trace ryan_m:1500:2300:30 --trace sora_w:1500:2700:30 --trace sora_w:2700:4670:30 "
        "--trace sora_w:4660:5610:30 --trace sora_w:5470:5600 --trace sora_w:6060:7740:30 --trace sora_w:6225:6460 --trace talon5:3240:4490:30 --trace talon5:4500:7380:30 --trace talon5:7460:7800 "
        "--trace zero_7:1750:3380:30 --trace zero_7:3370:3880:30 --trace zero_7:4400:4420 --trace zero_7:4400:7000:30 --trace zero_7:4600:5100:30 --trace zero_7:5040:5080 --trace zero_7:5225:5250 "
        "--trace zero_7:6280:6760:30 --trace zero_7:7640:8060:30 --trace zexos1:3960:4920:30 --trace zexos1:5040:8100:30",
        "python3 70_team_density.py A033 --at 990,1530,1980,2970,3960,4590,5400,6120,6480,7200,7470,7740,8010,8190", "python3 71_death_chain.py A033",
        "python3 72_repeat_sends.py A033", "python3 73_front_width.py A033 --t0 6120 --t1 7470",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/68_watch.mjs A033 --ids 44,8 --t0 6000 --t1 7500 --step 60 --cmds 1 --tag itv_p329",
        "68_watch.mjs 其余几次：--ids talon5 --t0 7460 --t1 7630 --step 5 --tag talon5_doomed；--ids sora_w,zero_7 --t0 7085 --t1 7130 --step 5 --tag sora_7120；"
        "--ids zero_7 --t0 4380 --t1 5240 --step 20 --tag zero7_hoard；--ids zero_7 --t0 5200 --t1 5700 --step 20 --tag zero7_boat；--ids zero_7,40 --t0 5524 --t1 5700 --step 4 --tag z7land；"
        "--ids zero_7,18 --t0 6280 --t1 6800 --step 30 --tag zero7_furry；--ids talon5,zero_7,44 --t0 7380 --t1 8080 --step 30 --tag sweep1；--ids ryan_m --t0 4590 --t1 8500 --step 300 --tag ryan_seat；"
        "--ids ryan_m,kaito9 --t0 1500 --t1 2300 --step 40 --tag ryan_kaito_early（都带 --cmds 1）",
    ],
    "timelineTs": [180, 540, 990, 1530, 1800, 2160, 2970, 4050, 4590, 5040, 5400, 5670, 6120, 6480, 7200, 7470, 7740, 8010, 8280, 8460],
    "timelineNotes": {
        180: "9 个号 144~174 格；三队真人领土中位数 144 / 144 / 220",
        540: "单号中位数 1,993 格、名次中位数 22/57（全场中位数 1,917）",
        990: "riku_x 3,322 格起 nb=0&neut=0；单号中位数 4,538（全场 5,482），名次中位数 39/55",
        1530: "4 个号被围（riku_x、alex_k、noah88、sora_w）；单号中位数 6,102（全场 10,438），名次 40/48；我方密度 24，同队其他真人 15",
        1800: "ryan_m 吃 Susland 到 15,998 格、余额 3.6 万（密度 2）；riku_x 密度 113、alex_k 83，调度全被拒",
        2160: "ryan_m 被 Emo Femboy 3 打回 8,396 格；2177 第一笔调度才成（alex_k→ryan_m 168,505）",
        2970: "kaito9 12,792 格（打 Emo Femboy 3）；sora_w 仍被围，余额 134.8 万；我方密度 61 = 同队其他真人 61",
        4050: "zero_7 29,851 格（3330 时 11,129）；ryan_m 最后一条快照，4116 进程掉线",
        4590: "ryan_m 的席位不再计入（10,526 格由内置 AI 管）；T2 37.8% 对 T1 38.4%，4770 反超",
        5040: "全队余额 851 万（全局峰值，密度 85）；T2 43.3% 对 T1 38.3%；zero_7 即将三条连发打 Thy Hoarders",
        5400: "zero_7 34,341 格 / 159 万（密度 46）；sora_w 17,900 格 / 242 万（密度 135）；5257~5383 四笔调度三笔被截断",
        5670: "全队余额 541 万（密度 52）：630 拍里利息地租进账 554 万，净增 3,215 格",
        6120: "T2 到顶 47.1%（T1 34.8% / T3 18.0%）；我方密度 62，同队其他真人 114；i🍇TV 47,551 格 / 649 万",
        6480: "全队余额 484 万（密度 45）；6327 [furry] 的船上了 zero_7 的岸，zero_7 丢到 31,896 格",
        7200: "zero_7 27,810 格 / 92.5 万（密度 33）；Player 329 剩 21,384 格；T2 43.4% / T1 37.5%",
        7470: "T1 41.5% 反超 T2 39.9%；i🍇TV 80,758 格 / 807 万，7465 第一波 123 万兵压上 talon5",
        7740: "talon5 剩 5,392 格（7804 出局）；i🍇TV 95,829 格 / 1,134 万",
        8010: "zero_7 被打到 7 千格上下（8064 出局）；i🍇TV 114,718 格 / 1,192 万",
        8280: "还剩 5 个号；alex_k 8168 已出局，kaito9 正在被 i🍇TV 打（8298 出局）",
        8460: "只剩 sora_w、zexos1；T1 58.9% / T2 23.7% / T3 17.2%；i🍇TV 176,962 格 / 1,473 万",
    },
    "contextExtra": {
        "strategyVersion": f"{VB}（名牌 [APEX]，Vb 批次）+ {SPVB}（出生协调器）。全场 0 条策略报错；慢拍 2 条（zero_7 t=5230 28.7 ms、kaito9 t=8215 35.2 ms）",
        "gameVersion": "引擎 2.17.x。真引擎重放（60_truth.cjs）与干净模拟器重演（resim）都和 traj.csv 的 775 个快照（领土、余额）逐条一致",
        "contamination": [
            "IO：ryan_m 的进程 4116 记 left（日志里没有报错和慢拍，原因不明）；引擎到 ≈4606 才把席位判为离开，之后由内置 AI 接管，10,526 格留到 8280 前后。不算阵亡",
            "sora_w（8483）、zexos1（8504）结算记 left：断开时 sora_w 还有 8,179 格、zexos1 的陆地刚被打光（8490 时 3,450 格），两个号都正被 i🍇TV 压着，引擎里 sora_w 8510 出局。按统筹口径它们不进阵亡链",
            "时间线的「我方号份额 / 兵力」只统计当拍有 HL-TICK 的号：4140 起不含 ryan_m 的席位",
            "anomalies.json 的 drop30Events 只留 30 条；本复盘的 62 条取自 traj.csv 全量扫描（与 drop30Count 相同），每条的去向由 67_troop_flow.mjs 按引擎扣款自动对账",
        ],
        "notes": "影子运行（65_shadow.mjs）：同一份 Vb 源码在重演出的真实局面上逐拍决策、指令只记不执行。775 条 HL-TICK 的领土 / 余额 / nb / neut 全部对上，"
                 "390 条 HL-DISPATCH 与 68 条 HL-OPENING 逐条同拍同数；cmds 计数有 6 个号从 t=455~560 起恒差 1（见机制核实第 12 项）。"
                 "影子给出的内部量（need、worth、keep、avail、over、留底）按源码公式重算，文中标「影子」；真号内存里的值看不到。",
    },
    "phases": {
        "opening": {
            "facts": [
                "出生点（重演真值）：9 个号在 x 730~913、y 87~300 的 183×213 像素里，最近队友 53.2~60.7 像素（中位 58.2）；其他真人到最近同队的中位数 T1 99.3、T2 144.6、T3 123.6（66_spawn_truth.mjs）",
                "角色：zexos1 CORNER_APEX_BANK，kaito9、alex_k INNER_ARC_BANK，其余 6 个 OUTER_SHIELD_WALL（in_game.log L179~L199）；9 个号的真实落点离最后指派都不到 2 像素",
                "t=195 的 OPENING-CHECK 9/9 OK（L240）；68 条 [HL-OPENING] 影子逐条复现",
                "t=540：我方 18,300 格（3.35%），单号中位数 1,993 格、名次中位数 22/57；0~1500 全队 224 条进攻共 394,545 兵，净增 53,554 格",
            ],
            "issues": [
                "圈里的地分完：riku_x 990、alex_k 1170、noah88 1350、sora_w 1530 起 nb=0&neut=0；名次中位数 39/55（990）→40/48（1530）",
                "t=300~1499 有内置 AI 邻居的 1,544 个决策拍只出手 162 个；零指令 1,349 拍里 safeFinite 留底绑定的 712 拍（其中参照我方队友的 474 拍）、AI 单价高于当拍出价的 479 拍（shadow_early.txt）",
                "影子里 8 个号的 isNoFullSend 在 t=463~794 就被锁上（zero_7 在 3872）",
                "6 个号各有一个决策拍（t=455~560）影子发了「打无主地 + 打 AI」两条，真号的 cmds 只加 1",
            ],
        },
        "expansion": {
            "facts": [
                "1500~2700：全队 60 条进攻 1,535,017 兵，净增 14,158 格（约 104 兵 / 格）；余额 163 万→455 万",
                "ryan_m 1512~1743 对 Susland 10 条 240,318 兵：6,509→15,998 格；kaito9 1512~1519 三条 199,784 兵：3,684→5,739 格（其中 141,914 兵在 Susland 死后压在无主地上到 1800 前后才退回）",
                "Emo Femboy 3#46（T1）1820~2110 打 ryan_m（进攻槽 50,884~55,909 兵）：16,264→8,396 格",
                "kaito9 / zexos1 / ryan_m 1974~2989 对 Emo Femboy 3 共 47 条 1,343,373 兵：它从 20,956 格掉到 4,369 格；kaito9 6,802→12,792 格，zexos1 5,796→10,127 格",
                "这一段执行的调度 5 笔：到账 748,892、手续费 142,223；第一笔在 2177",
            ],
            "issues": [
                "1505~2176 的 71 条调度日志：63 条单笔需点（125~353）超过全场上限（85~121），7 条超过收方剩余额度，1 条执行",
                "sora_w 1500~2700 的 223 个决策拍全是「没有可打的邻居」，18 次调度全被拒；余额 13.2 万→98.0 万；它到 5400 才有海岸",
                "riku_x 密度 113（1800）→143（2250）；alex_k 148、noah88 136（3150）。全场快照里余额过软上限的 59 个、顶到硬上限的 4 个",
            ],
        },
        "midgame": {
            "facts": [
                "2700~4284：配额入账 37 笔 5,466,829 兵（用掉 1,078 点）；收方额度 zero_7 305/309、zexos1 268/309、talon5 213/219、kaito9 153/153、ryan_m 139/153",
                "同期 94 条进攻 6,929,329 兵，净增 29,720 格（约 222 兵 / 格）；全队份额 13.76%（2970）→18.57%（4050）",
                "zero_7 → McRep 19 条 2,262,339 兵（21,702→6,425 格）；zexos1 → tung sahur 24 条 2,338,328 兵（25,063→7,892 格）；talon5 → Player 999 16 条 1,240,087 兵（8,664→3,235 格）",
                "4284~5400：30 笔调度到账 7,632,320、手续费 2,207,695；sora_w → REVOLUTION 22 条 4,051,080 兵（它从 24,323 格 / 315 万兵打到 13,949 格 / 1 万兵），sora_w 12,268→17,900 格",
                "T2 31.9%（2970）→35.7%（3960）→39.8%（4770，反超 T1 39.1%）→44.0%（5400）",
            ],
            "issues": [
                "t<4284 的 295 条调度日志执行 33 条：85 条单笔超全场上限，167 条超收方剩余额度，10 条卡在换档 / 额度边界；没有一条对不上账",
                "ryan_m 4116 掉线；引擎 ≈4606 判离开，4652 / 4732 内置 AI 把 558,932 / 513,699 兵送给 sora_w / alex_k（手续费 112,797）",
                "4284~5400 三种手续费 3,207,902 = 利息地租的 29.7%；每净增一格的花费从 222 兵涨到 443 兵",
                "zero_7 5068~5383：三条连发（多发 1,364,029 兵）→ 退兵顶格丢 73,140 → 发船（费 160,973，海上掉 364,018）→ 四笔调度（手续费 823,960，三笔被截断）",
            ],
        },
        "endgame": {
            "facts": [
                "6120：T2 47.1% / T1 34.8% / T3 18.0%；我方 106,640 格 / 659 万兵（密度 62），同队其他真人 140,120 格 / 1,602 万兵（密度 114）",
                "6120~7470：利息地租 10,756,712；46 条进攻 9,567,463 兵（手续费 1,024,436，退回 950,010）；37 笔调度到账 7,064,297、手续费 1,452,312；挨打掉 1,972,686；领土 −2,599 格",
                "同期 i🍇TV 对 Player 329 的 7 条进攻共花 9,408,701；Qq 给 i🍇TV 捐 2 笔 2,599,594；Player 329 从同队只收到 338,628",
                "7470：T1 226,772 格 / 1,974 万兵（密度 87）；我方 104,041 格 / 480 万（密度 46）；同队其他真人 103,541 格 / 1,215 万（密度 117）",
                "7470~终局：挨打掉 7,749,104 兵；我方份额 19.05%→3.64%（8460）；终局 T1 58.9% / T2 23.7% / T3 17.2%",
            ],
            "issues": [
                "6120~7470 的 16 个采样里 alex_k、kaito9、noah88、riku_x、zexos1 和 ryan_m 的席位贴敌边界一直是 0 格；talon5 到 7470 才贴上 i🍇TV（41 格）；sora_w 贴 T3 的边界 26~68 格（中位 57）",
                "talon5 4500~7380 有 565 个决策拍「没有可打的邻居」、只做了 11 次调度；zexos1 5040~8100 是 568 拍、13 次调度",
                "全场只发了 3 条船（3962 zexos1 带 1,373 兵却付了 43,967 发船费；5243 zero_7；8316 zexos1 35,468 兵）",
                "同一目标的连发：503 条生效的进攻里 376 条在连发组里；对真人的 91 组里第 2 条起的兵 18,964,055、手续费 2,005,350",
            ],
        },
    },
    "turningPoints": [
        {
            "t0": 5040, "t1": 5670,
            "what": "全队余额的峰值在 630 拍里花掉。5040 时我方 851 万兵（密度 85）、T2 43.3% 领先 T1 38.3%。之后 630 拍利息地租进账 554 万，余额反而掉到 541 万："
                    "进攻净消耗 463 万、三种手续费 231 万（利息地租的 41.6%）、挨打掉 69 万，换来净增 3,215 格（每格约 1,984 兵；5040 之前全程平均 117 兵）。"
                    "最大的号 zero_7 从密度 150 掉到 46，领土从此没再超过 34,341 格",
            "shareBefore": 0.1832, "shareAfter": 0.1891,
            "ourBots": ["zero_7", "sora_w", "zexos1", "talon5", "kaito9"],
            "enemies": ["Thy Hoarders#15（T3）：5068 时 3,767 格 / 495,914 兵，≈5170 出局", "[furry]嗷呜#18（T1）：5480~5640 对 zero_7 的进攻槽峰值 1,045,050 兵", "rey playa#40（T3）：zero_7 的船 5530 靠岸处，27,074 格 / 137 万兵"],
            "evidence": [
                "troop_flow_tp.txt A / E2：5040~5670 余额 8,524,065→5,412,597；利息地租 5,535,981；25 条进攻 6,840,592 兵（退回 2,212,884）；1 条船 996,023 兵；23 笔调度到账 5,692,479、手续费 1,551,266；领土 +3,215 格",
                "repeat_sends.txt C + shadow_trace_zero_7_5040_5080.txt：zero_7 在 5055 / 5060 / 5065 三个决策拍各发一条 pct≈238（影子：三拍的 need 都是 76.7~77.2 万，over=1），5068 / 5068 / 5075 落地共 2,252,406 兵；吃掉整块所需约 888,377，多发 1,364,029",
                "watch_zero7_hoard.txt + troop_flow.txt H：进攻槽 2,226,118（5080）；Thy Hoarders 死后 1,655,085 兵转打无主地；5229 退兵应加 1,654,321、实加 1,581,181（顶在 150×34,341 = 5,151,150），丢 73,140",
                "troop_flow.txt G + watch_z7land.txt：5243 发船 pct=197，带 996,023 兵、发船费 160,973；5530 在 (657,678) 靠上 rey playa 的岸时剩 632,005 兵，打下 3 格后撤回",
                "replay_ledger.txt B：5257 / 5278 / 5327 / 5383 四笔 pct=320 给 sora_w，名义 1,263,968 / 1,136,157 / 972,005 / 760,553，到账 248,839 / 538,285 / 674,917 / 760,553，手续费 252,006 / 226,523 / 193,795 / 151,636（日志 L1103 / L1104 / L1113：dMe 116 / 106 / 90，dAlly 115 / 131 / 124）",
                "watch_zero7_boat.txt：5480~5640 [furry]嗷呜打 zero_7（进攻槽 537,218→1,045,050），34,341→32,567 格；5481~5502 六个队友付出 1,208,087 捐回给 zero_7；5551~5558 zero_7 又是三条连发打 [furry]（1,118,158 兵）",
            ],
            "priorDecisions": [
                {"t": 5055, "bot": "zero_7", "action": "相邻三个决策拍对同一目标各发一条 pct≈238：前面的指令还没生效，余额和目标身上的兵都没变，算出来的需求一模一样", "logRef": "shadow_trace_zero_7_5040_5080.txt；cmd_effect.tsv t=5068~5075",
                 "codePath": f"{VB}:Policy.buyLand:L5353 `over = P.surplus > 0 && B > 100*L`、L5359 `c >= worth && c >= cheap && !over → break`（过软上限时不看价）→ L5440-5443 `over → keep = min(keep, …×100×L)` → "
                             "L5611-5616 `want = 1.25*need + 3*cnt`、`x = min(avail, want)` → Policy.send:L3838-3925（发出后只登记 pendingQuotaCheck，没有「已发未生效」的记账；need 里的 `g.attackTroopsOn(me,q)` 在生效前一直是 0）"},
                {"t": 5230, "bot": "zero_7", "action": "余额顶在硬上限、没有敌邻也没有中立地 → 闲置船：装走至少 24% 的可用兵，航程 2500 像素", "logRef": "in_game.log L1101（HL-SLOW-TICK t=5230）；shadow_trace_zero_7_5225_5250.txt",
                 "codePath": f"{VB}:Policy.act:L4962-4963 → Policy.idleBoats:L5019-5071（L5031 `activeLandFrontBrothers >= 1 && dMe < 115 → return`；L5039 `P.boatFrac = Math.max(oldFrac, 0.24)`）"},
                {"t": 5245, "bot": "zero_7", "action": "同一状态下每 25 拍向 sora_w 做「产出最优」调度 pct=320，只看收方密度是否低于 128~142，不看它离硬上限还剩多少", "logRef": "in_game.log L1103 / L1104 / L1113 / L1114",
                 "codePath": f"{VB}:Policy.tryDonateToTeammate:L4355 boxedIn、L4382 `prodOptFloor = boxedIn ? (hasExposedCoast ? 44*L : 34*L) : max(92*L, safeAt)`、L4418 `dAlly >= (boxedIn ? 142 : 115) → continue`、"
                             "L4474-4495 Case B（`reqD = boxedIn ? 58 : 108`、`maxAllyD = boxedIn ? 128~140 : 96`）、L4500-4508 `idealPct = 320`；引擎 donate：到账受收方 150×领土封顶，手续费按捐方全部余额照收"},
            ],
            "alternatives": "按统筹广播 0003 的口径，5068 时吃掉 Thy Hoarders 需要约 89 万兵，第一条 964,625 兵已经够；后两条的 1,287,781 兵（手续费 64,505）是照原样重发的。"
                            "之后的顶格、发船、截断都是这批多发的兵退回来以后「找出口」的连锁：能直接点到的损失有重发的手续费 64,505、顶格 73,140、发船费 160,973、海上 364,018、四笔调度的手续费 823,960。"
                            "只发一条会不会就没有后面的事，是推断：zero_7 当时密度 128，即使不连发，余额也会在一两百拍内自己涨到硬上限。",
            "statementType": "observed",
            "confidence": "指令、扣款、退兵、船、到账：高（全部是引擎重演的逐拍真值，重演与 775 个日志快照一致）。zero_7 连发的内部原因：中高（影子逐拍复现了三条同比例的指令和同一个 need；真号内存看不到）。连锁的因果：推断。",
        },
        {
            "t0": 6120, "t1": 7470,
            "what": "领先丢掉。T2 在 6120 到顶（47.1% 对 T1 34.8%），7470 被 T1 反超（39.9% 对 41.5%）。这 1,350 拍 T1 的 i🍇TV 用 7 条进攻共 941 万兵吃掉 T2 最大的真人 Player 329（46,914 格），自己 47,551→80,758 格。"
                    "我方同期利息地租进账 1,076 万：进攻净消耗 862 万、手续费 248 万、挨打掉 197 万，领土 −2,599 格，全队密度 62→46。没有一条指令打 i🍇TV，没有一个兵给 Player 329",
            "shareBefore": 0.1953, "shareAfter": 0.1905,
            "ourBots": ["sora_w", "zero_7", "zexos1", "talon5", "kaito9", "alex_k", "noah88", "riku_x"],
            "enemies": ["[UA]i🍇TV#44（T1）：47,551 格 / 649 万（6120）→80,758 格 / 807 万（7470）", "Holy British Empire#31（T3）：31,960 格 / 458 万（6120）→28,340 格 / 203 万（7470）",
                        "rey playa#40（T3）：29,206 格 / 319 万（6840）→29,788 格 / 139 万（7470）", "[furry]嗷呜#18（T1）：6327 船靠 zero_7 的岸，478,559 兵"],
            "evidence": [
                "truth_view.txt A + watch_itv_p329.txt：T1 / T2 / T3 = 34.8 / 47.1 / 18.0（6120）→37.5 / 43.4 / 19.1（7200）→41.5 / 39.9 / 18.4（7470）；i🍇TV→Player 329 7 条进攻共花 9,408,701（6482~7350），Qq→i🍇TV 2 笔 2,599,594；Player 329 46,914 格 / 572 万（6030）→21,384 格（7200）→7380 已出局",
                "troop_flow_tp.txt A / B / E2（6120~7470）：46 条进攻 9,567,463 兵 + 手续费 1,024,436，其中 sora_w 39 条 9,091,378 兵（收捐 31 笔 6,508,952），它的领土 18,451→20,217；37 笔调度到账 7,064,297、手续费 1,452,312",
                "front_width.txt：这一段 16 个采样里，alex_k、kaito9、noah88、riku_x、zexos1 和 ryan_m 的席位贴敌边界全是 0 格；sora_w 贴 Holy British Empire / rey playa 26~68 格（中位 57，它自己的边界 727~800 格）；zero_7 有 7 个采样是 0，8 个采样贴 [furry] 40~83 格，7470 贴上 i🍇TV 139 格",
                "shadow_trace_sora_w_6060_7740.txt：sora_w 出手 51 次约 11,973,493 兵，41 次是过软上限时发的；36 次（约 9,175,106 兵）目标每格成本高于自己的出价，c/worth = 1.15~11.17。例：t=6225 余额 2,128,391、20,100 格，出价 95.3，Holy British Empire 每格 216.6",
                "watch_sora_7120.txt + in_game.log L1311 / L1321：zero_7 7105 pct=380（余额 2,333,999→1,319,714）、7126 pct=351（1,355,854→805,040）都捐给 sora_w，后一笔时 sora_w 密度 124；zero_7 27,810 格的密度 25 拍里 84→29",
                "team_density.txt：我方密度 62（6120）→45（6480）→44（7200）→46（7470），同队其他真人 114→113→106→117；我方占 T2 领土的 41%~48%、兵的 24%~29%",
                "watch_zero7_furry.txt：6327 [furry] 的船把 478,559 兵送上 zero_7 的岸，6328 zero_7 的协防调度落地（付出 910,515 给 sora_w），密度 61→35，到 6630 丢 7,113 格",
            ],
            "priorDecisions": [
                {"t": 6225, "bot": "sora_w", "action": "余额一过 100×领土就向接壤的真人发 12% 余额一条的进攻，不比较对方每格成本和自己的出价", "logRef": "shadow_trace_sora_w_6225_6460.txt；shadow_trace_sora_w_6060_7740.txt",
                 "codePath": f"{VB}:Policy.buyLand:L5353 `over`、L5359 `… && !over → break`、L5440-5443（留底降到 0.82~0.9×100×领土）、L5457 usePulseBlock、L5590 `pulse = min(avail, max(floor(pulseFrac*B), …))`（pulseFrac=0.12）"},
                {"t": 6320, "bot": "zero_7", "action": "没有陆地敌邻就按「后方银行」处理：队友挨打时把余额的 37% 捐过去，自己只留 32×领土", "logRef": "in_game.log L1227 / L1299 / L1311 / L1321 / L1340",
                 "codePath": f"{VB}:Policy.tryDonateToTeammate:L4355 `boxedIn = !anyEnemyNb && this.nb.length === 0 && this.neutral === 0`（不看海上、不看领土大小）、L4386 `emergDefFloor = boxedIn ? (hasExposedCoast ? 32*L : 22*L) : max(88*L, safeAt)`、"
                             "L4457 `underFire = inHumanAtk > 0 && (inHumanAtk >= 0.06*Bp || dAlly < 88)`、L4463-4473 Case A（围死号不要求 `dMe >= dAlly + 16`）、L4500-4506 `idealPct = 380`、`pct = min(maxSafePct, idealPct)`"},
                {"t": 6540, "bot": "talon5 / zexos1 / kaito9 等", "action": "调度的收方只能是我方号；没有敌邻的号不进攻，密度不到 115 也不发船，兵只有捐给 sora_w / zero_7 一条路", "logRef": "shadow_trace_talon5_4500_7380.txt；shadow_trace_zexos1_5040_8100.txt",
                 "codePath": f"{VB}:Policy.tryDonateToTeammate:L4414 `(!this.isOurSquadBot(g, p) && !this.isBossNpl(g, p)) → continue`；Policy.idleBoats:L5031 `activeLandFrontBrothers >= 1 && dMe < 115 → return`"},
            ],
            "alternatives": "这一段 i🍇TV 打 Player 329 花了 941 万，我方同期打 T3 两个号的进攻净消耗 862 万、内部倒手的手续费 145 万，量级相同、方向不同。"
                            "Player 329 的地（6030 时密度 122）倒下后归了 i🍇TV，我方密度 33~49 的号直接贴上去。这些兵如果留在号里，7470 时全队密度不会是 46——但能不能因此挡住 i🍇TV、"
                            "或者给了 Player 329 它能不能守住，都没法重演，是推断。",
            "statementType": "observed",
            "confidence": "各队份额、i🍇TV 与 Player 329 的攻防、我方每条指令的扣款、接壤格数：高（引擎真值）。sora_w 出手时的出价与目标单价：中高（影子）。「兵留着会怎样」：推断。",
        },
        {
            "t0": 7465, "t1": 8460,
            "what": "被 i🍇TV 逐个打掉。i🍇TV（7470 时 80,758 格 / 807 万兵，密度 100）吃完 Player 329 后贴上 talon5、zero_7，每次压上 120~200 万兵：talon5 7804 出局、zero_7 8064、alex_k 8168、kaito9 8298、noah88 8319、riku_x 8449，"
                    "sora_w、zexos1 在最后 30 拍也被打光（结算记 left）。被打的号当时各有 9~132 万兵、密度 20~60。我方份额 19.05%→3.64%",
            "shareBefore": 0.1905, "shareAfter": 0.0364,
            "ourBots": ["talon5", "zero_7", "alex_k", "kaito9", "noah88", "riku_x", "sora_w", "zexos1"],
            "enemies": ["[UA]i🍇TV#44（T1）：80,758 格 / 807 万（7470）→114,718 格 / 1,192 万（8010）→176,962 格 / 1,473 万（8460）；期间 Qq 两次各拿出余额的三分之一捐给它（7700 付出 1,453,520、8036 付出 1,443,444）"],
            "evidence": [
                "death_chain.txt：i🍇TV 的进攻槽峰值 talon5 1,506,041、zero_7 1,825,280、alex_k 1,677,140、kaito9 1,678,240、noah88 1,807,624、riku_x 303,579、sora_w 2,018,631、zexos1 1,746,346；我方挨打掉的兵依次 1,331,046 / 2,844,674 / 116,519 / 825,277 / 216,865 / 194,563 / 985,921 / 702,820",
                "watch_talon5_doomed.txt：7465 i🍇TV 压上 1,233,058 兵，talon5 13,016 格 / 576,565 兵（敌兵 ÷ 余额 = 2.14）；之后 2.07（7490）、1.97（7515）、1.89（7540）、1.81（7565）、1.69（7590）、1.60（7600）、1.52（7615）",
                "in_game.log L1371 / L1372：第一批指向 talon5 的协防调度在 t=7615（zexos1 pct=323、alex_k pct=312），7623 / 7630 到账 234,537 / 43,174；这时 talon5 剩 7,378 格",
                "team_density.txt（7470）：T1 226,772 格 / 1,974 万（密度 87）；我方 104,041 格 / 480 万（密度 46）；同队其他真人 103,541 格 / 1,215 万（密度 117）",
                "shadow_trace_talon5_7460_7800.txt + shadow_nofull.tsv：talon5 7460~7770 的 63 个决策拍都是「目标价高」；7775~7795 出手 2 次，7780~7790 三次有可用兵的脉冲被 isNoFullSend 保护挡掉；录像里它对 i🍇TV 只有 7784 一条（58,960 兵）",
                "troop_flow.txt A / E + cmd_effect.tsv（7470~终局）：全队挨打掉 7,749,104 兵；进攻 14 条 1,496,021 兵，其中 sora_w 的 10 条 1,344,250 兵（7581~7735）仍然打 Holy British Empire / rey playa，打 i🍇TV 的只有 talon5 7784（58,960）和 zero_7 7966（78,800）",
            ],
            "priorDecisions": [
                {"t": 7465, "bot": "zexos1 / alex_k / kaito9 等", "action": "队友身上的敌兵超过它余额的 1.65 倍就不救；talon5 挨打的前 150 拍没有收到一个兵", "logRef": "in_game.log L1371 / L1372；watch_talon5_doomed.txt",
                 "codePath": f"{VB}:Policy.tryDonateToTeammate:L4455-4456 `isDoomedPocket = !isBeachhead && (inHumanAtk > 1.65 * Bp || (g.t >= 4500 && Lp < 0.22 * maxSquadTerr && inHumanAtk > 0.45 * Bp)) → continue`；"
                             "L4330-4331（每号 25 拍一个相位拍）；L4463-4466 `reqD = boxedIn ? (hasExposedCoast ? 42 : 30) : 102`"},
                {"t": 7120, "bot": "zero_7 / kaito9 / riku_x / noah88 / alex_k", "action": "「后方银行」的留底是 22~44×领土：这些号在被打之前已经把兵捐到密度 21~49", "logRef": "in_game.log L1321 / L1352 / L1353 / L1362",
                 "codePath": f"{VB}:Policy.tryDonateToTeammate:L4382-4388（prodOptFloor 34 / 44×L、emergDefFloor 22 / 32×L）、L4504-4506 `maxSafePct = floor((B − bestFloor)*1024/B)`"},
                {"t": 7780, "bot": "talon5", "action": "对 i🍇TV 的反击脉冲被 isNoFullSend 保护挡掉 3 次（标记在 t=463 就被误锁）", "logRef": "shadow_nofull.tsv；shadow_trace_talon5_7460_7800.txt",
                 "codePath": f"{VB}:Policy.updateShadowQuota:L3800-3836 → Policy.send:L3844-3862"},
            ],
            "alternatives": "按「每格成本 ≈ 2 + 2×守方密度」的口径，i🍇TV 第一波 123 万兵打密度 44 的 talon5 够买一万多格；同样的兵打密度 117 的同队其他真人只够五千格上下。我方的号是这张图上最便宜的地。"
                            "7470 时我方 480 万兵全部加起来也只有 i🍇TV 一家的六成，这一段靠调度救不回来（推断）；决定这一段的是之前 3,000 拍里兵去了哪。",
            "statementType": "observed",
            "confidence": "谁打的、何时、多少兵、各号被打前的密度：高（引擎真值）。talon5 前 150 拍没人救的原因：中高（敌兵 ÷ 余额降到 1.65 以下后的第一个够格的相位拍正好是日志里第一条协防，逐拍吻合；真号内部的判断看不到）。",
        },
    ],
    "deaths": [
        {"bot": "talon5", "killers": ["[UA]i🍇TV#44（T1）：7470~7790 进攻槽峰值 1,506,041 兵（7465 第一波 1,233,058，7770 第二波 1,294,199）"],
         "lastDecisions": ["7392~7399：3 条打无主地（71,541 兵）", "7460~7770：63 个决策拍都嫌 i🍇TV 贵（每格 192~400，自己出价 74~78），零指令（影子）", "7784：pct=122 打 i🍇TV（58,960 兵）；7780~7790 另有 3 次脉冲被 isNoFullSend 保护挡掉（影子）"],
         "cause": "4500~7380 没有敌邻（隔着 Player 329 和 🌋），2,880 拍只做了 11 次调度，密度 29~78（7300 时 39）。Player 329 倒下后直接贴上 i🍇TV：7465 一波 123 万兵（是它余额的 2.14 倍），150 拍丢 5,638 格；"
                  "队友的协防要等敌兵 ÷ 余额降到 1.65 以下才发，7623 才到，共 3 笔 632,495。第一波在 5,392 格停住（7680~7740），7770 第二波 129 万，7804 出局。",
         "patternIds": ["NEW:R07-DF-BANK-DRAIN", "NEW:R07-DF-DOOMED-SKIP"]},
        {"bot": "zero_7", "killers": ["[UA]i🍇TV#44（T1）：7650~8050 进攻槽峰值 1,825,280 兵", "[furry]嗷呜#18（T1）：6327 船靠岸 478,559 兵，6363~6510 进攻槽峰值 1,080,651（丢 7,113 格）"],
         "lastDecisions": ["7105 / 7126 / 7308：三笔协防调度给 sora_w（pct=380 / 351 / 380）", "7640~8060：82 个决策拍嫌贵、出手 1 次（影子）", "7966：pct=120 打 i🍇TV（78,800 兵）"],
         "cause": "全队最大的号（峰值 34,341 格@5310）。5055 起的连发—顶格—发船—调度把密度从 150 打到 46；6328、6979、7105、7126、7308 五次把余额的 23%~37% 捐给正在打 T3 的 sora_w（其中四次是在没有陆地敌邻、按「后方银行」留底 32×领土的状态下），7200 时 27,810 格 / 92.5 万兵（密度 33）。"
                  "Player 329 倒下后 7650 起 i🍇TV 压上（峰值 183 万），400 拍从 29,514 格打到出局（8064）；期间收到 5 笔 911,529。",
         "patternIds": ["NEW:R07-DF-BANK-DRAIN", "NEW:R07-AT-INFLIGHT-REPEAT"]},
        {"bot": "alex_k", "killers": ["[UA]i🍇TV#44（T1）：8100~8160 进攻槽峰值 1,677,140 兵"],
         "lastDecisions": ["7630：协防调度到账 talon5 43,174", "7952：协防调度到账 zero_7 52,798（手续费 9,360）", "之后零指令"],
         "cause": "内圈储备号：1170 起被队友围住，全程 4,363 格、没有海岸。95 条调度日志执行 22 条；免检期把兵捐到密度 20~30。8100 i🍇TV 压上 168 万兵时它有 4,363 格 / 9~13 万兵，60 拍出局（8168）。",
         "patternIds": ["NEW:R07-SP-CLUSTER", "NEW:R07-DF-BANK-DRAIN"]},
        {"bot": "kaito9", "killers": ["[UA]i🍇TV#44（T1）：8240~8290 进攻槽峰值 1,678,240 兵"],
         "lastDecisions": ["7425 / 7700：调度给 sora_w（日志 L1352 / L1381）", "8215 / 8275：影子想发船，真号的 cmds 没有增加、录像里没有", "最后 500 拍没有一条指令被执行"],
         "cause": "2880 起被队友和海围住（12,792 格），之后 5,400 拍没有进攻，只做调度（19 条日志执行 17 条），密度 30~62。i🍇TV 吃完 zero_7、alex_k 后 8240 压上 168 万兵，50 拍从 12,792 格 / 77 万兵（密度 60）打到 3,876 格，8298 出局。",
         "patternIds": ["NEW:R07-DF-BANK-DRAIN", "NEW:R07-DF-PASSIVE-BLEED"]},
        {"bot": "noah88", "killers": ["[UA]i🍇TV#44（T1）：8280~8310 进攻槽峰值 1,807,624 兵"],
         "lastDecisions": ["7530：调度给 sora_w（日志 L1362）", "7868：协防调度到账 zero_7 54,205（手续费 10,641）", "之后零指令"],
         "cause": "内圈储备号：1350 起被围，全程 5,217 格、没有海岸；83 条调度日志执行 19 条。被打时 5,217 格 / 14~21 万兵（密度 27~41），30 拍出局（8319）。",
         "patternIds": ["NEW:R07-SP-CLUSTER", "NEW:R07-DF-BANK-DRAIN"]},
        {"bot": "riku_x", "killers": ["[UA]i🍇TV#44（T1）：8340~8430 进攻槽峰值 303,579 兵"],
         "lastDecisions": ["7430 / 7705：调度给 sora_w（日志 L1353 / L1382）", "8183~8190：2 条打无主地（14,011 兵）", "之后零指令"],
         "cause": "最早被围的号：990 起 nb=0&neut=0，3,322 格，没有海岸，开局阶段打过几次内置 AI 之后领土再没变过。80 条调度日志执行 20 条。被打时 3,322 格 / 9.5 万兵（密度 28），i🍇TV 用 30 万兵 90 拍打掉（8449）。",
         "patternIds": ["NEW:R07-OP-BOXED-EARLY", "NEW:R07-SP-CLUSTER"]},
    ],
    "decisions": [
        {"t": -18, "bot": "全队", "kind": "spawn", "verdict": "error",
         "state": "9 个号出生在 183×213 像素里，最近队友 53~61 像素（中位 58）；其他真人到最近同队的中位数是 T1 99、T2 145、T3 124。角色 1 个 CORNER_APEX_BANK、2 个 INNER_ARC_BANK、6 个 OUTER_SHIELD_WALL",
         "codePath": f"{SPVB}:L1065-1077 CORNER SECTOR PHALANX、L1144 / L1155 / L1167（角色）、L1344-1368（指派）→ {VB}:Policy.chooseSpawn:L3983-4037（采用 `window.__tsbAssignedSpawn`）",
         "why": "圈里的地 990~1530 就分完：riku_x、alex_k、noah88、sora_w 先后被队友围住，前三个之后一格没长、也没有海岸。角色和结果对不上：四个早早被围的号里三个（riku_x、noah88、sora_w）标的是「外圈盾墙」，标着「银行」的 zexos1、kaito9 反而打到了前线",
         "estCost": "t=1530 单号中位数 6,102 格（全场 10,438），名次中位数 40/48", "patternId": "NEW:R07-SP-CLUSTER", "evidenceRef": "out/A033/spawn_truth.txt A / B；rank.txt；in_game.log L179~L199"},
        {"t": 65, "bot": "全队", "kind": "expand", "verdict": "good",
         "state": "OPENING-CHECK@195 9/9 OK；t=540 单号中位数 1,993 格（全场 1,917），名次中位数 22/57",
         "codePath": f"{VB}:V13.expandNeutral:L2373 `g.t < this.p.dpEnd → dpNeutral`（L2383，日志 [HL-OPENING] 在 L2409）",
         "why": "9 个号挤在一起的情况下，前 540 拍的地仍略多于全场中位数；68 条 [HL-OPENING] 影子逐条同拍同数",
         "estCost": "—", "patternId": "NEW:R07-GOOD-OPENING-DP", "evidenceRef": "in_game.log L204 / L240；rank.txt t=540；shadow_check.txt"},
        {"t": 650, "bot": "alex_k / zexos1 / riku_x / zero_7 等", "kind": "idle", "verdict": "error",
         "state": "例：t=650 alex_k 余额 5,885、2,450 格，隔壁 AI#139 有 390 格 / 11 兵（每格 2.1 兵）；留底 5,144 正好是 zexos1 当时的余额，可用兵 741（影子）",
         "codePath": f"{VB}:Style.pickTarget:L1144-1176（`avail = bal − floorFor(...)`）→ V13.floorFor0:L2234 → Policy.winFloor:L4562-4570 `max(价格项, dpKeep, sb)` → V13.safeFinite:L2500-2510 → threatOf:L417-444（邻居里只排除 q 自己和我，不排除队友，也不看 AI 自己的兵）",
         "why": "t=300~1499 有 AI 邻居的 1,544 个决策拍里零指令 1,349 个，其中 712 个是 safeFinite 这条留底绑定的，474 个参照的「AI 最弱的其他邻居」是我方队友；这 474 拍里 302 拍最便宜的目标每格不到 3 兵、平均 573 格。夹着同一个空 AI 的两个号互相拿对方的余额当留底",
         "estCost": "474 个决策拍（零指令拍的 35.1%）", "patternId": "NEW:R07-OP-WINFLOOR-MATE", "evidenceRef": "out/A033/shadow_early.txt"},
        {"t": 1512, "bot": "ryan_m", "kind": "attack", "verdict": "unclear",
         "state": "6,509 格、余额 22 万（1500）。隔壁是 Susland#26（T1，12,526 格），kaito9 同时也在打它；ryan_m 1512~1743 对它发 10 条共 240,318 兵（手续费 9,484）",
         "codePath": f"{VB}:Policy.act:L4801（t≥1500 走核心逻辑）→ Policy.buyLand:L5342-5450（`c < cheap → keep = 0`，对便宜的地不留底）",
         "why": "1800 时 15,998 格（+9,489 格，约 26 兵 / 格），是这一段全队拿地最多的号；但余额只剩 3.6 万（密度 2）。1820 起 Emo Femboy 3 用 5 万多兵的进攻槽打回来，2120 剩 8,396 格（−7,868）。地买得便宜，守不住是因为后面的兵过不来（见下一条）",
         "estCost": "拿到 9,489 格、丢回 7,868 格", "patternId": "NEW:R07-EG-FRONT-STARVE", "evidenceRef": "watch_ryan_kaito_early.txt；troop_flow.txt C 节；truth_bots.tsv"},
        {"t": 1505, "bot": "riku_x / alex_k / noah88 / sora_w", "kind": "donate", "verdict": "error",
         "state": "四个围死号密度 33~135，每 25 拍向 kaito9 / ryan_m / zero_7 / zexos1 调度 pct=320 或 380（单笔 6.7~19 万兵）；全场上限 85~121 点，这样的单笔要 125~353 点",
         "codePath": f"{VB}:Policy.tryDonateToTeammate:L4329-4331（12 拍冷却 + 25 拍相位）、L4500-4508（`idealPct` 320 / 380，`pct < 180 → return false`，`g.donate(...)` 之后不看结果）；只有 Boss 分支（L4359-4374）查 `window.ao.iD`",
         "why": "1505~2176 的 71 条日志里 63 条单笔就超过全场上限、7 条超过收方剩余额度，只有 2177 那一笔执行。整个配额期 295 条日志执行 33 条；被拒的不扣款、不进录像，策略没有任何反馈",
         "estCost": "ryan_m 1820~2110 丢 7,868 格时，riku_x、alex_k 各有 37.6 万 / 36.1 万兵（1800）", "patternId": "NEW:R07-DN-QUOTA-OVERSIZE", "evidenceRef": "quota_truth.txt A / D 节；in_game.log L417~L559"},
        {"t": 1530, "bot": "sora_w", "kind": "idle", "verdict": "error",
         "state": "11,549 格（当时全队最大），四周全是队友、没有中立地、没有海岸。1500~2700 的 223 个决策拍影子都是「没有可打的邻居」",
         "codePath": f"{VB}:Policy.act:L4962-4963（没发别的指令才调度 / 发船）；Policy.idleBoats:L5032 `!g.boatsAllowed(me) → return`；tryDonateToTeammate:L4355 boxedIn",
         "why": "余额 13.2 万→98.0 万（密度 12→85），18 次调度全被配额拒绝，1,200 拍没有一条指令生效。它标的角色是「外圈盾墙」",
         "estCost": "98 万兵闲置到 2700", "patternId": "NEW:R07-EC-BOXED-RICH", "evidenceRef": "shadow_trace_sora_w_1500_2700.txt；in_game.log L420 / L677；quota_logs.tsv"},
        {"t": 1974, "bot": "kaito9", "kind": "attack", "verdict": "good",
         "state": "6,802 格、余额 24.8 万（1980）。Emo Femboy 3#46（T1，约 2.1 万格）正在打 ryan_m；kaito9 1974~2821 对它发 18 条共 520,394 兵（手续费 62,919），期间收到 2 笔调度 274,609",
         "codePath": f"{VB}:Policy.offers:L5072（目标排序）→ Policy.buyLand:L5342-5450 → L5611-5616（`want = 1.25*need + 3*cnt`）",
         "why": "2970 时 12,792 格（+5,990 格，约 97 兵 / 格）。同一段 zexos1（21 条 596,949 兵）、ryan_m（8 条 226,030 兵）也在打它，Emo Femboy 3 从 20,956 格掉到 4,369 格，ryan_m 那边止住失血（8,396→10,526 格）",
         "estCost": "—", "patternId": "NEW:R07-GOOD-FED-PUSH", "evidenceRef": "troop_flow.txt C 节；truth_bots.tsv；quota_truth.txt C 节"},
        {"t": 3374, "bot": "zero_7", "kind": "attack", "verdict": "good",
         "state": "11,129 格、余额 60.5 万（3330）。2700~4284 收到 17 笔调度 2,938,737 兵；3374~3878 对 McRep#13（T1，21,702 格、密度 62）发 19 条共 2,262,339 兵（手续费 272,517）",
         "codePath": f"{VB}:Policy.buyLand:L5359（`c >= worth && c >= cheap && !over → break`：影子里这一段 22 次出手只有 2 次是过软上限放行的）→ L5446 `avail = B − fee − max(keep, safe)`",
         "why": "4050 时 29,851 格（+18,722 格，约 135 兵 / 格），McRep 剩 6,425 格；全队份额 14.15%（3330）→18.57%（4050）。兵从储备号流到前线、按价换成地，是全局效率最高的一段",
         "estCost": "—", "patternId": "NEW:R07-GOOD-FED-PUSH", "evidenceRef": "shadow_trace_zero_7_3370_3880.txt；troop_flow.txt B / C 节；quota_truth.txt C 节"},
        {"t": 4116, "bot": "ryan_m", "kind": "other", "verdict": "unclear",
         "state": "10,526 格、余额约 60 万。4050 最后一条快照（avgMs 0.45），4100 最后一条调度日志，4116 结算记 left；日志里没有报错和慢拍",
         "codePath": f"执行层（进程 / 连接），不在策略代码里；{VB}:Policy.tryDonateToTeammate:L4393 / L4415 跳过 `window.__quitPlayers`",
         "why": "引擎到 ≈4606 才把席位判为离开，这 490 拍它照常吃利息（649,651→1,214,535）。接管的内置 AI 在 4652 / 4732 把 558,932 / 513,699 兵送给 sora_w / alex_k，之后每 80 拍送出约 1 万；10,526 格以密度 ≈1 留到 8280 前后。不算阵亡",
         "estCost": "一个 10,526 格的席位停止决策 4,400 拍", "patternId": "NEW:R07-IO-SEAT-LOST", "evidenceRef": "in_game.log L950 / L959 / L1018；watch_ryan_seat.txt；troop_flow.txt F 节"},
        {"t": 5055, "bot": "zero_7", "kind": "attack", "verdict": "error",
         "state": "32,345 格、余额 413 万（密度 128）。影子：5055 / 5060 / 5065 各发一条 pct≈238 打 Thy Hoarders#15（3,767 格 / 49.6 万兵），三拍的 need 都是 76.7~77.2 万，over=1",
         "codePath": f"{VB}:Policy.buyLand:L5353 `over`、L5611-5616 `x = min(avail, 1.25*need + 3*cnt)` → Policy.send:L3838-3925（need 里的 `g.attackTroopsOn(me,q)` 在指令生效前一直是 0）",
         "why": "三条在 5068 / 5068 / 5075 落地，共 2,252,406 兵（手续费 112,938），是吃掉整块所需（约 888,377）的 2.5 倍。目标死后 165.5 万兵转打无主地，5229 退回时撞上硬上限。全场对真人的连发 91 组，第 2 条起的兵 18,964,055",
         "estCost": "多发 1,364,029 兵；顶格丢 73,140", "patternId": "NEW:R07-AT-INFLIGHT-REPEAT", "evidenceRef": "repeat_sends.txt A / C 节；shadow_trace_zero_7_5040_5080.txt；watch_zero7_hoard.txt；troop_flow.txt H 节"},
        {"t": 5230, "bot": "zero_7", "kind": "boat", "verdict": "error",
         "state": "34,341 格、余额 5,151,150（= 150×领土），没有敌邻、没有中立地。5230 决策拍（耗时 28.7 ms）发船 pct=197",
         "codePath": f"{VB}:Policy.act:L4962-4963 → Policy.idleBoats:L5019-5071（L5031、L5039 `P.boatFrac = Math.max(oldFrac, 0.24)`，航程 2500）",
         "why": "5243 生效：带走 996,023 兵、发船费 160,973。船 5530 才在 (657,678) 靠上 rey playa（T3，27,074 格 / 137 万兵）的岸，剩 632,005 兵，打下 3 格后撤回",
         "estCost": "发船费 160,973 + 海上掉 364,018，换 3 格", "patternId": "NEW:R07-AT-BOAT-FAR", "evidenceRef": "troop_flow.txt G 节；watch_zero7_boat.txt；watch_z7land.txt；in_game.log L1101"},
        {"t": 5245, "bot": "zero_7", "kind": "donate", "verdict": "error",
         "state": "发完船仍有 399 万兵（密度 116），boxedIn=true。5245~5370 每 25 拍一条 pct=320 给 sora_w；日志里 sora_w 的密度依次是 115 / 131 / 124 / 93；前三笔落地时它离硬上限只剩 25~67 万",
         "codePath": f"{VB}:Policy.tryDonateToTeammate:L4382（prodOptFloor）、L4418 `dAlly >= (boxedIn ? 142 : 115) → continue`、L4474-4495（`maxAllyD = boxedIn ? 128~140 : 96`）、L4500-4508",
         "why": "四笔共付出 3,046,554：到账 2,222,594、手续费 823,960；前三笔的到账被 sora_w 的硬上限截到 248,839 / 538,285 / 674,917（名义 126 万 / 114 万 / 97 万）。全场被截断 4 笔：名义 3,901,913、到账 1,816,825、手续费 761,316。zero_7 密度 150→46（5400）",
         "estCost": "手续费 823,960；三笔共截掉 1,910,089 兵", "patternId": "NEW:R07-DN-CAP-TRUNC", "evidenceRef": "replay_ledger.txt B 节（顶格截断）；in_game.log L1103 / L1104 / L1113 / L1114"},
        {"t": 6225, "bot": "sora_w", "kind": "attack", "verdict": "error",
         "state": "20,100 格、余额 2,128,391（密度 105.9）。影子：自己的出价 95.3 兵 / 格，Holy British Empire#31（T3，密度 143）每格 216.6；over=1 → pct=122（约 25.6 万兵）",
         "codePath": f"{VB}:Policy.buyLand:L5353 `over = P.surplus > 0 && B > 100*L`、L5359 `… && !over → break`、L5440-5443、L5590（脉冲 = 12% 余额）",
         "why": "6060~7740 影子出手 51 次约 1,197 万兵，36 次（约 918 万）目标每格成本高于自己的出价。引擎账：6120~7470 它 39 条进攻 9,091,378 兵（手续费 946,228），收捐 31 笔 6,508,952，领土 +1,766 格，挨打掉 1,296,672。它和 T3 两个号的接壤只有 26~68 格",
         "estCost": "909 万兵 + 95 万手续费换 1,766 格", "patternId": "NEW:R07-AT-OVER-BURN", "evidenceRef": "shadow_trace_sora_w_6060_7740.txt；troop_flow_tp.txt B 节；front_width.txt"},
        {"t": 6320, "bot": "zero_7", "kind": "donate", "verdict": "error",
         "state": "34,341 格、余额 2,095,211（密度 61），nb=0、neut=0（四周是队友和海）。sora_w 正被 T3 反打 → 协防调度 pct=380（日志 boxedIn=true）",
         "codePath": f"{VB}:Policy.tryDonateToTeammate:L4355 boxedIn（不看海上）、L4386 `emergDefFloor = boxedIn ? (hasExposedCoast ? 32*L : 22*L) : …`、L4463-4473 Case A、L4500-4506 `idealPct = 380`",
         "why": "6328 落地（到账 779,565、手续费 130,950），而 6327 [furry]嗷呜的船刚把 478,559 兵送上 zero_7 的岸。zero_7 密度 61→35，[furry] 再压 594,633（6363）、520,265（6482），到 6630 丢 7,113 格；6342~6622 七笔队友调度又付出 754,854 捐回来",
         "estCost": "丢 7,113 格", "patternId": "NEW:R07-DF-BANK-DRAIN", "evidenceRef": "in_game.log L1219 / L1227；watch_zero7_furry.txt；drop30_recon.txt zero_7@6300"},
        {"t": 7120, "bot": "zero_7", "kind": "donate", "verdict": "error",
         "state": "27,810 格。7105 第一笔 pct=380 落地（余额 2,333,999→1,319,714）后密度 49，sora_w 收到后密度 124~143；7120 又发 pct=351（日志 dMe=49、dAlly=125）",
         "codePath": f"{VB}:Policy.tryDonateToTeammate:L4457 underFire、L4463-4466（围死号只要 `dMe >= 42` 且 `B > 1.12*emergDefFloor`，不比较两边密度）、L4504-4506（351 正好留下 32×27,810）",
         "why": "7126 落地：1,355,854→805,040（密度 29）。25 拍里 zero_7 的密度 84→29；sora_w 拿到兵后 7119 / 7126 各发一条 pct=122 打 rey playa（346,352 / 363,052）。全场执行的 127 笔调度里 92 笔发出时捐方密度低于收方，到账 15,277,277",
         "estCost": "第二笔付出 550,814；7200 时 zero_7 密度 33", "patternId": "NEW:R07-DN-INVERTED", "evidenceRef": "watch_sora_7120.txt；in_game.log L1311 / L1321 / L1324；quota_truth.txt D2 节"},
        {"t": 7465, "bot": "zexos1 / alex_k 等", "kind": "assist", "verdict": "unclear",
         "state": "i🍇TV 7465 压上 1,233,058 兵打 talon5（13,016 格 / 576,565 兵）。zexos1、alex_k 的相位拍上「敌兵 ÷ talon5 余额」依次是 2.14（7465）、2.07、1.97、1.89、1.81、1.69（7590）",
         "codePath": f"{VB}:Policy.tryDonateToTeammate:L4455-4456（isDoomedPocket：`inHumanAtk > 1.65 * Bp → continue`）；L4330-4331（25 拍相位）；L4463-4466（reqD 30 / 42）",
         "why": "比值 7600 降到 1.60，这两个号的下一个相位拍 7615 同时发出协防（pct=323 / 312），7623 / 7630 到账 234,537 / 43,174；这时 talon5 剩 7,378 格。规则挡住了往两倍兵力压着的口袋里填兵，也让第一波的 150 拍没有任何支援；哪个更亏没法验证",
         "estCost": "talon5 150 拍丢 5,638 格", "patternId": "NEW:R07-DF-DOOMED-SKIP", "evidenceRef": "watch_talon5_doomed.txt；in_game.log L1371 / L1372"},
        {"t": 7780, "bot": "talon5", "kind": "attack", "verdict": "error",
         "state": "i🍇TV 第二波 129 万兵压上（它当时有 1,134 万兵）。影子：7780 / 7785 / 7790 三个决策拍有可用兵 6.0~18.9 万，都被 isNoFullSend 保护挡掉",
         "codePath": f"{VB}:Policy.updateShadowQuota:L3800-3836（发令后 1~6 拍内余额下降就把 isNoFullSend 永久置真）→ Policy.send:L3844-3862（影子额度不够 → 不发）",
         "why": "影子里 9 个号的标记全部被锁上（talon5 在 t=463），全场挡掉 48 次出兵（sora_w 25 次，其中 14 次在 5490~5575 打 REVOLUTION 时）。这三拍录像里只有 7784 一条 pct=122（58,960 兵）。对结局没有影响，但这个保护在线上只会误判",
         "estCost": "3 次脉冲", "patternId": "NEW:R07-MT-NOFULL-LOCK", "evidenceRef": "shadow_nofull.tsv；shadow_trace_talon5_7460_7800.txt；cmd_effect.tsv t=7784"},
    ],
    "newPatterns": [
        np("R07-SP-CLUSTER", [{"t": -18, "bot": "全队"}], "A033：9 个号最近队友的距离中位数 58 像素（其他真人到最近同队 99~145）；没有重叠"),
        np("R07-OP-BOXED-EARLY", [{"t": 990, "bot": "riku_x"}, {"t": 1170, "bot": "alex_k"}, {"t": 1350, "bot": "noah88"}, {"t": 1530, "bot": "sora_w"}], "A033：4 个号；前三个全程 3,322 / 4,363 / 5,217 格"),
        np("R07-OP-WINFLOOR-MATE", [{"t": 650, "bot": "alex_k"}, {"t": 650, "bot": "zexos1"}, {"t": 700, "bot": "riku_x"}, {"t": 750, "bot": "zero_7"}],
           "A033（影子）：t=300~1499 有 AI 邻居的 1,544 个决策拍，零指令 1,349 个，safeFinite 绑定 712 个，其中参照我方队友 474 个；A062 同口径 415 个"),
        np("R07-GOOD-OPENING-DP", [{"t": 65, "bot": "全队"}]),
        np("R07-DN-QUOTA-OVERSIZE", [{"t": 1505, "bot": "riku_x"}, {"t": 1530, "bot": "alex_k"}, {"t": 2035, "bot": "sora_w"}],
           "A033：390 条日志执行 127 条；配额期 295 条里 85 条单笔超全场上限、167 条超剩余额度、10 条卡在边界、执行 33 条"),
        np("R07-EG-FRONT-STARVE", [{"t": 1840, "bot": "ryan_m"}], "A033：ryan_m 密度 2 丢 7,868 格，同时 riku_x / alex_k 密度 83~113"),
        np("R07-EC-BOXED-RICH", [{"t": 1530, "bot": "sora_w"}, {"t": 1800, "bot": "riku_x"}, {"t": 3150, "bot": "alex_k"}], "A033：68 个快照"),
        np("R07-GOOD-FED-PUSH", [{"t": 1974, "bot": "kaito9"}, {"t": 3374, "bot": "zero_7"}], "A033：kaito9 +5,990 格、zero_7 +18,722 格"),
        np("R07-IO-SEAT-LOST", [{"t": 4116, "bot": "ryan_m"}], "A033：1 个席位（10,526 格）；接管的内置 AI 把 107 万兵送给两个队友"),
        np("R07-AT-INFLIGHT-REPEAT", [{"t": 5055, "bot": "zero_7"}, {"t": 3479, "bot": "zero_7"}, {"t": 5488, "bot": "sora_w"}, {"t": 1512, "bot": "kaito9"}],
           "A033：503 条生效的进攻里 376 条在连发组里；对真人 91 组，第 2 条起 18,964,055 兵 / 手续费 2,005,350；超出吃掉整块所需的 2,857,456 兵（8 组）"),
        np("R07-AT-BOAT-FAR", [{"t": 5243, "bot": "zero_7"}], "A033：带 996,023 兵，靠岸剩 632,005，换 3 格"),
        np("R07-DN-CAP-TRUNC", [{"t": 5257, "bot": "zero_7"}, {"t": 5278, "bot": "zero_7"}, {"t": 5327, "bot": "zero_7"}, {"t": 7770, "bot": "sora_w"}], "A033：4 笔，名义 3,901,913、到账 1,816,825、手续费 761,316"),
        np("R07-AT-OVER-BURN", [{"t": 6225, "bot": "sora_w"}, {"t": 5055, "bot": "zero_7"}, {"t": 4600, "bot": "zexos1"}],
           "A033（影子）：sora_w 6060~7740 36 次约 918 万兵、zero_7 4400~7000 18 次约 823 万、zexos1 3960~4920 15 次约 191 万、talon5 3240~4490 13 次约 135 万"),
        np("R07-DF-BANK-DRAIN", [{"t": 6320, "bot": "zero_7"}, {"t": 7120, "bot": "zero_7"}, {"t": 7425, "bot": "kaito9"}],
           "A033：boxedIn=true 的调度日志 376/390 条、执行 121 条；我方密度 44~63 对同队其他真人 106~117（3960~7470）"),
        np("R07-DN-INVERTED", [{"t": 5270, "bot": "zero_7"}, {"t": 7120, "bot": "zero_7"}, {"t": 3410, "bot": "sora_w"}], "A033：101 条日志捐方密度低于收方，执行 92 条，到账 15,277,277（A062 是 16 条、0 条执行）"),
        np("R07-DN-PINGPONG", [{"t": 5054, "bot": "zexos1"}, {"t": 5257, "bot": "zero_7"}], "A033（300 拍口径，引擎账）：6 笔，到账 3,132,765、手续费 1,005,427；捐出前 300 拍内自己刚收过捐款的 14 笔，到账 7,007,573"),
        np("R07-EG-WRONG-FRONT", [{"t": 6540, "bot": "全队"}], "A033：6120~7470 我方进攻 9,567,463 兵里 sora_w 打 T3 的 9,091,378；i🍇TV 同期花 9,408,701 吃掉 Player 329"),
        np("R07-DF-DOOMED-SKIP", [{"t": 7465, "bot": "talon5"}], "A033：talon5 挨打 150 拍后才有第一笔协防"),
        np("R07-MT-NOFULL-LOCK", [{"t": 463, "bot": "talon5"}, {"t": 5490, "bot": "sora_w"}, {"t": 7780, "bot": "talon5"}], "A033（影子）：9/9 个号被锁上，挡掉 48 次出兵"),
        np("R07-DF-PASSIVE-BLEED", [{"t": 8240, "bot": "kaito9"}, {"t": 8100, "bot": "alex_k"}, {"t": 8280, "bot": "noah88"}], "A033：31 个窗口，65,064 格（多数在 7465 之后）"),
    ],
    "lossArchetype": "lead-thrown",
    "winnerNotes": "T1 获胜（终局 58.9%）。T1 在 3960 时只剩 10 个真人、5400 剩 8 个、6570 起一直是 6 个，人数始终比 T2 少（T2 15→14→13→11），但兵没有少过：3960 时 T1 2,168 万对 T2 1,603 万，"
                   "7470 时 1,974 万对 1,696 万，密度 87~113 对 75~95。它把兵集中在一个号上：i🍇TV 30,256 格 / 294 万（3960）→47,551 格 / 649 万（6120，密度 136）→80,758 格 / 807 万（7470）→176,962 格 / 1,473 万（8460）；"
                   "队友 Qq 四次给它捐款，每次都是 pct=337（自己余额的三分之一）：7028、7252 共付出 2,599,594，7700 付出 1,453,520，8036 付出 1,443,444；Thuja 也捐了两笔（7938、8022），Qq 还在 6650 给 [furry]嗷呜付出 1,307,471。"
                   "i🍇TV 的打法是挑密度低的邻居下重手：先 😶‍🌫️（密度 44），再 Player 329（它 6041~6391 先花 308 万打 Popeye，密度从 122 掉到 103 之后才被打），然后是我方密度 20~60 的号。"
                   "T2 从 4770 到 6120 涨的 7.3 个点里，我方 8 个号贡献 12,807 格（2.3 个点）。T3 从 5220 起只剩 4 个真人，份额一直在 17%~19%，我方 6120 之后的进攻却几乎全打在它身上。",
    "wentWell": [
        "开局 9/9 通过检查，t=540 单号中位数略高于全场；出生没有重叠，9 个号都落在指派的点上",
        "配额期后半的调度把收方额度几乎用满（zero_7 305/309 点），zero_7 3330→4050 +18,722 格，全队份额 13.76%→18.57%",
        "前线号先后把 T1 的 Emo Femboy 3、McRep、tung sahur、REVOLUTION 和 T3 的 Player 999、Thy Hoarders 打残；T2 在这期间从 31.9%（2970）涨到 44.0%（5400）",
        "没有卡顿：各号指令延迟中位数 8~15 拍；0 条策略报错；免检期 95 条调度日志执行 94 条",
    ],
    "unknowns": [
        "ryan_m 的进程为什么在 4116 掉线：日志里没有报错和慢拍，其余 8 个号的日志没有异常；从掉线到引擎判离开隔了约 490 拍",
        "kaito9 8215 / 8275 影子想发船（8215 有一条 35.2 ms 的慢拍日志），真号的 cmds 没有增加、录像里没有这两条：是没发出去还是被拒",
        "zexos1 3962 那条船（pct=0，带 1,373 兵、发船费 43,967）是策略的哪个分支发的、去了哪：重演里没有记到它靠岸",
        "真号内存里的 isNoFullSend 是否和影子一致（标记不进日志）",
        "一个决策拍里的第二条指令是在桥接层被丢的还是被服务器拒的：桥接代码不在本包里",
        "我方如果保持和同队其他真人一样的密度（106~117），i🍇TV 会不会改打别人、T2 能不能守住：没法重演",
        "Qq、Thuja 给 i🍇TV 和 [furry]嗷呜的大额捐款（每笔 130~145 万）是真人配合还是脚本",
        "sora_w 6120~7470 挨打掉的 130 万兵里，多少是它自己的脉冲招来的反击、多少是 T3 主动打的",
    ],
    "mechanicsQuestions": [
        "捐款到账受收方硬上限封顶（到账 = min(名义额, 150×收方领土 − 收方余额)），截掉的兵消失，手续费仍按捐方全部余额的 6.25% 收：5257 那一笔到账 248,839、手续费 252,006。",
        "进攻结束退回的兵也走同一个封顶：5229 zero_7 退兵应加 1,654,321、实加 1,581,181。压在进攻槽里的兵不算防守、不吃利息，退回来还可能丢。",
        "离开的席位由难度 6 的内置 AI 接管，在团队局里它会把整个余额捐给正在打仗的队友（按收方空间封顶、照付 6.25%）：ryan_m 的席位 130 拍内送出 107 万兵，之后每 80 拍约 1 万。",
        "船在海上掉兵：zero_7 的船 287 拍从 996,023 掉到 632,005（−36.5%）；发船费是全部余额的 3.1%，与装多少兵无关（zexos1 3962 那条带 1,373 兵付了 43,967）。",
        "配额期的 37 笔入账把几个收方的额度用到 87%~100%，但这是 295 次尝试里成的 33 次：其余 262 次每次都照发、照被拒，储备号的兵在这期间只能等。",
        "攻方每格成本随守方密度线性涨：我方密度 46、同队其他真人 117 时，最大的敌人打我方每格便宜一半以上。「把兵捐出去 / 打出去」在这条公式下等于降低自己的地价。",
    ],
    "drop30Notes": {
        "zero_7@5310": "5327 / 5383 两笔 pct=320 给 sora_w：付出 868,712 + 912,189；前一笔被 sora_w 的硬上限截断（名义 972,005，到账 674,917，手续费 193,795）",
        "zero_7@6300": "6328 协防调度给 sora_w（到账 779,565、手续费 130,950），落地前一拍 [furry]嗷呜的船刚把 478,559 兵送上 zero_7 的岸；之后 300 拍丢 7,113 格",
        "zero_7@7110": "7126 第二笔协防调度（pct=351，正好留下 32×27,810）：到账 466,074、手续费 84,740；收方 sora_w 当时密度 124",
        "kaito9@1440": "1512~1519 三条连发打 Susland（199,784 兵、手续费 5,291）；Susland 死后 141,914 兵压在无主地上，1800 前后退回",
    },
    "mechanismChecks": {
        "1_quotaRejections": "证实，逐条对上账。390 条调度日志、引擎执行 127 条（32.6%）。配额期（t<4284）295 条里执行 33 条：85 条单笔需点超过全场上限（t=1505~3185）、167 条超过收方剩余额度、10 条卡在换档 / 额度边界，没有一条解释不了。"
                             "入账侧：37 笔（含同队其他真人的 5 笔）5,466,829 兵、1,078 点，zero_7 用到 305/309、zexos1 268/309、talon5 213/219、kaito9 153/153。免检后 95 条执行 94 条。被拒的捐款不扣款、不进录像，策略没有反馈。",
        "2_donationTax": "证实。127 笔到账 25,398,634、手续费 5,822,265（费 / 到账 0.229），相当于全程利息地租 49,261,316 的 11.8%；加上进攻费 3,661,409 和发船费 213,807，三种手续费占 19.7%。"
                         "分阶段：4284~5400 占 29.7%，5040~5670 这 630 拍占 41.6%。",
        "3_inlandStagnation": "证实，但本局分两段。配额期：riku_x（990 起）、alex_k（1170）、noah88（1350）、sora_w（1530~≈4600）被围，nb=0&neut=0 且密度 ≥60 的快照 68 个，过软上限 59 个、顶硬上限 4 个。"
                              "免检期反过来：围死号被调度抽到密度 20~50（留底 22~44×领土），不再囤兵，而是没兵。前三个号全程没长过一格。",
        "4_spawnOpening": "Vb 协调器的角落扇形阵：9 个号最近队友 53~61 像素，没有重叠。开局正常（9/9 OK，t=540 名次中位数 22/57），圈里的地 990~1530 分完，名次掉到 40/48。角色标签和实际不符（见决策表第 1 条）。",
        "5_frontlineFloors": "本局是领先局，这一项是主因。①有敌邻的号余额一过 100×领土就不看价出兵：影子里 sora_w / zero_7 / zexos1 / talon5 共 82 次约 2,067 万兵是目标单价高于出价时发的。"
                             "②没有敌邻的号按「后方银行」留底 22~44×领土，协防时一次捐 37%。两条加起来，我方密度 3960~7470 一直在 44~63，同队其他真人 106~117。"
                             "③6120~7470 九个席位里六个贴敌边界为 0，全队的兵从 sora_w 一条中位 57 格宽的边界打出去。",
        "6_teamSplit": "不适用：9 个号全在 T2。",
        "7_lagBatches": "本局没有卡顿：各号指令延迟中位数 8~15 拍、最大 45 拍，没有号落后 ≥90 拍；同一拍落地 ≥3 条的批只有 4 个。",
        "8_noFullSendLock": "影子里证实：9/9 个号的 isNoFullSend 被锁上（talon5、sora_w 463，kaito9 477，alex_k 680，zexos1 701，noah88 772，ryan_m 785，riku_x 794，zero_7 3872），之后挡掉 48 次出兵"
                            "（sora_w 25、talon5 10、zexos1 6、noah88 3、riku_x 2、ryan_m 1、alex_k 1）。后果不大，但 talon5 临死前的 3 次反击脉冲在其中。",
        "9_invertedFeeding": "证实，而且大量执行。101 条日志发出时捐方密度低于收方，其中 92 条被引擎执行，到账 15,277,277（全部到账的 60%）；执行的 127 笔里捐方密度中位数 58、收方 76。"
                             "原因是围死号的两个分支都不比较两边密度（余粮分支只要求捐方 ≥58、收方 ≤128~140；协防分支只要求捐方 ≥30 / 42）。",
        "10_spawnRecompute": "有重算、没有出事。我方 151 条出生指令（每号 12~22 条），12 条指向已被占的点、被引擎挪开 >6 像素；最后 8 条里 zexos1 和 alex_k 在 (819,166) 与 (860,200) 两个点之间来回换（alex_k 换了 3 次边），最后一条在 −18 拍，各自落在指派点上。",
        "11_winFloorMateLock": "影子里证实。t=300~1499 有内置 AI 邻居的 1,544 个决策拍：出手 162、只打无主地 33、零指令 1,349。零指令里 safeFinite 留底绑定 712 拍（参照我方队友 474、同队真人 / 敌方真人 238），"
                               "AI 单价高于当拍出价 479 拍，价格项或 dpKeep 124 拍。参照队友的 474 拍里 302 拍最便宜的目标每格不到 3 兵。A062 同口径是 415 拍。",
        "12_oneCmdPerTick": "证实 6 例。ryan_m、zero_7、kaito9、alex_k、riku_x（t=455~470）和 talon5（t=560）各有一个决策拍影子发了「打无主地 + 打内置 AI」两条，真号的 cmds 计数只加 1，此后一直差 1。本局没有看到它造成大单被挤掉。",
        "13_inflightRepeat": "证实，量很大。503 条生效的进攻里 376 条在「同一目标、落地间隔 ≤12 拍」的连发组里。对真人 91 组 248 条：发兵 31,440,482，其中第 2 条起 18,964,055（手续费 2,005,350）；"
                             "发兵超过吃掉整块所需的有 8 组、多出 2,857,456 兵（zero_7 5068~5075 多 1,364,029；sora_w 5488~5495 对只剩 1 兵的 REVOLUTION 发了 664,653；zero_7 3479~3486 多 392,867）。",
        "14_capTruncPingPong": "证实。硬上限截断 4 笔：名义 3,901,913、到账 1,816,825、手续费 761,316。300 拍内来回倒手 6 笔，到账 3,132,765、手续费 1,005,427；捐出前 300 拍内自己刚收过捐款的 14 笔，到账 7,007,573（占全部到账的 27.6%）、手续费 1,912,628。",
    },
    "extraScripts": ["60_truth.cjs", "61_truth_view.py", "62_rank.py", "63_replay_ledger.py", "64_cmd_loss.py", "65_shadow.mjs", "66_spawn_truth.mjs", "67_troop_flow.mjs", "68_watch.mjs",
                     "69_quota_truth.mjs", "70_team_density.py", "71_death_chain.py", "72_repeat_sends.py", "73_front_width.py", "review_src/A033.py", "review_src/common.py"],
    "extraOutputs": [f"c136-review/agents/R07/out/A033/{f}" for f in
                     ("truth_view.txt", "truth_check.txt", "rank.txt", "team_density.txt", "troop_flow.txt", "troop_flow_tp.txt", "cmd_effect.tsv", "drop30_recon.txt", "replay_ledger.txt",
                      "quota_truth.txt", "quota_logs.tsv", "repeat_sends.txt", "front_width.txt", "death_chain.txt", "spawn_truth.txt", "cmd_loss.txt",
                      "shadow_check.txt", "shadow_early.txt", "shadow_nofull.tsv", "shadow_coast.tsv",
                      "shadow_trace_zero_7_5040_5080.txt", "shadow_trace_zero_7_3370_3880.txt", "shadow_trace_zero_7_4400_7000.txt", "shadow_trace_sora_w_1500_2700.txt", "shadow_trace_sora_w_6060_7740.txt",
                      "shadow_trace_sora_w_6225_6460.txt", "shadow_trace_talon5_4500_7380.txt", "shadow_trace_talon5_7460_7800.txt", "shadow_trace_zexos1_5040_8100.txt",
                      "watch_itv_p329.txt", "watch_talon5_doomed.txt", "watch_sora_7120.txt", "watch_zero7_hoard.txt", "watch_zero7_boat.txt", "watch_z7land.txt", "watch_zero7_furry.txt",
                      "watch_sweep1.txt", "watch_ryan_seat.txt", "watch_ryan_kaito_early.txt")],
    "confidenceOverall": "高（事实层）：全场真值来自真引擎重放，与 775 个日志快照逐条一致；每条指令的扣款、到账、退兵、船、配额入账都是引擎里记下来的，分阶段流水逐号逐窗核对差额为 0。"
                         "中高（原因层）：出手时的出价 / 留底 / 需求量和 isNoFullSend 来自影子运行——影子与真日志的 390 条调度、68 条开局指令逐条相同，但真号内存里的值看不到。"
                         "推断：兵如果留在号里 T2 能不能守住领先；talon5 没被及时协防的原因（与代码逐拍吻合）。未知：ryan_m 掉线的原因。"
                         "分型取 lead-thrown：T2 领先了约 2,600 拍、峰值领先 12 个点，丢掉领先的那一段我方没有丢地，丢的是兵。",
}
