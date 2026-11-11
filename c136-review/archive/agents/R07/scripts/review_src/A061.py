# -*- coding: utf-8 -*-
"""A061 手写分析（R07）。数字来自 out/A061/ 下的 digest.txt、truth_view.txt / rank.txt / team_density.txt / truth_all.tsv / truth_bots.tsv / truth_border.tsv（真引擎重放）、
side_flow.txt / side_flow_tp.txt / humans_cmd.tsv（全场真人分组流水、发兵矩阵与逐条指令）、pair_cmds_*.txt（逐对合计）、troop_flow.txt / troop_flow_tp.txt / cmd_effect.tsv /
drop30_recon.txt / drop30_class.txt、interest.txt（按引擎公式逐人重算利率）、bot_share_frozen6.txt、outlet_gap.txt、boat_targets.txt、quota_truth.txt、replay_ledger.txt、repeat_sends.txt、
same_tick_batches.txt、front_width.txt、death_chain.txt、help_table.txt、donation_yield.txt、spawn_truth.txt、cmd_loss.txt、patterns.json、
shadow_check.txt / shadow_early.txt / shadow_early_humans.txt / shadow_late_ai.txt / shadow_cmds.tsv / shadow_nofull.tsv / shadow_trace_*.txt / trace_blocked_*.txt（影子运行）、watch_*.txt（盯人）；
代码路径指 /agent/repos/c136-data/src/strategy/v27-team-c116-vb.js 与 spawn-coordinator-c116-vb.mjs，引擎指 /agent/repos/c136-data/src/sim/sim/。"""
from common import np, VB, SPVB

SRC = {
    "oneLine": "T2 输给 T5（8822 拍），我方从没领先过。10 个号按协调器的角落扇形阵出生在 209×183 像素里（最近队友 51~64 像素，T5 的人是 108）：540 拍还和全场持平，"
               "1080 起 9 个席位贴着敌方真人、只剩 2 个贴着内置 AI，990~1500 全队只多 9,185 格（T5 多 69,645 格），882 还丢了两个席位。"
               "t=1500 换成核心逻辑的那一拍，三个号各连发三条同比例的单子把余额打到自己的留底以下，1977~2646 四个号出局、一个兵都没收到。"
               "剩下四个号 2700~5310 从 9.4% 打到 18.6%，之后停在 19%：kaito9（4.6 万格、500 万兵）被「唯一真人邻居」这道闸和调度门槛卡成银行，1,848 拍一条进攻没发、捐出 820 万。"
               "这一段 T2 的利息进账比 T5 还多（3,228 万对 2,962 万），T2 这边打 T5 薄号的却只有同队真人 Player 769 一个人；他 7567 / 7658 两次梭哈后被吃光，T5 横扫。",
    "narrative": [
        "**出生到 990（t<990）**：协调器求解 42 次，间距从 70 像素缩到 51~52；10 个号落在 209×183 像素里，最近队友 51~63.9 像素（中位 55.4），T5 的 10 个真人是 107.7。"
        "外圈贴上来的是 T1 的五个人、T3 的两个、T4 的一个（990），T5 一个都不挨着。开局本身没吃亏：OPENING-CHECK@221 10/10 OK，540 拍单号中位数 1,879 格、名次中位数 22/53（全体真人中位数 1,833）。"
        "之后圈里的内置 AI 很快分完：贴着 AI 的号 10 个（720）→6 个（990）→2 个（1080）。540~990 我方往 AI 身上发了 110,644 兵，另外四队各发 146,973~198,091；"
        "影子里 t=300~1499 有 AI 邻居的 1,457 个决策拍只出手 149 个，零指令里 384 拍卡在「以队友余额为准」的留底。882 talon5、noah88 两个客户端相隔 136 毫秒报离开（当时 2,771 / 4,682 格）。990 时名次中位数 39/48。",
        "**没有 AI 可吃的 500 拍（990~1500）**：9 个席位贴着敌方真人。六个号（alex_k、kaito9、riku_x、ryan_m、zero_7、zexos1）领土 22,455→24,988 格几乎不动，余额 17.5 万→95.9 万，占全队余额的 82%~89%。"
        "全队这一段 36 条进攻、101,088 兵打 AI，+9,185 格；T5 87 条、483,340 兵，+69,645 格。贴着的真人并不强：1440 时这六个号各自最弱的真人邻居密度只有 5.4~12.1，自己是 22~92；"
        "Big Boss 990 时 5,592 格 / 14,351 兵、1440 时 10,295 格 / 55,937 兵，同时贴着 alex_k、zero_7、ryan_m、sora_w。开局逻辑对这种真人只按「猎杀规则」出手：留下一半常规留底后，一次发的兵要够吃光对方。影子里这段「没有 AI 邻居、也没有无主地」的 525 个决策拍只发了 5 条："
        "142 拍的留底是队友余额的 2 倍（多数参照 ryan_m），101 拍是价格留底，81 拍是 100×领土的一半，69 拍过了留底但一次吃不光。1530：T5 26.9%，我方 9.03%，名次中位数 38/46。",
        "**1500 解锁，四个号出局（1500~2700）**：t=1500 全队同一拍换成核心逻辑，上面那些留底一起消失。zero_7、alex_k、zexos1 在 1500 / 1505 / 1510 三个决策拍看到的余额没变（第一条 1512 才落地），各发了三条同比例的单子："
        "zero_7 三条 pct=374，201,816→125,544→78,098→49,677，而它当拍给自己算的留底是 122,812；alex_k 232,654→37,512；zexos1 243,737→32,724。14 拍里三个号打出 545,192 兵，"
        "其中 339,248（加上 sora_w 共 419,206）压在 Big Boss 一个人身上，吃光它约需 171,916。zero_7 家里剩密度 14，Eyup 1610、Yolo 1617 先后压上来，1977 出局；"
        "sora_w（Player 915 八条 23.3 万）2523、riku_x（指令延迟中位数 32 拍，2079 一拍落地 5 条）2559、ryan_m（Yolo 一条 pct=321 19 万）2646。四个号死前 500 拍各挨 11~15 万兵，收捐 0 笔——"
        "1500~2700 的 341 个相位拍里 225 个没有合格的收方（不是围死号的捐方要密度 ≥102 / ≥108），全段只有一笔 39,163。同一段 kaito9 1635 趁 HD.MAX 把兵全压到别人身上，三条 54,334 兵吃下 8,507 格（7,727→16,234）；"
        "之后 1652~2870 一条指令没有（256 个决策拍价高），余额 22 万→163 万。全队 9.03%→12.43%（2160）→9.40%（2700），8 个号剩 4 个。",
        "**四个号追到 18.6%（2700~5310）**：密度过 100（过软上限后不比价）才出手。kaito9 2870 起 9 条 113 万打 Yolo（3547 出局）、15 条 341 万打 Eyup、6 条 169 万打 JM LEPEN（5294 出局）、两条 113 万吃下 Kalmar 离开后的席位（22,220 格）："
        "16,234→46,253 格。zexos1 12 条 60 万把 Player 625 打出局（3912），leo_tx 打 Player 171、Micha、🙉🙈🙊。4795 Eyup 把 121.6 万余额全压到 kaito9 身上，kaito9 4809~4837 六条 pct=122 共 114 万把它磨光，"
        "自己只丢约 330 格，Eyup 5010 出局。全队 9.40%→18.62%，T2 13.1%→25.3%；同期 T5 35.8%→51.0%（吃 T4 离开的席位）。zexos1 4445 起被 Player 915 三条 78 万从 8,515 格打到 4,646 格。",
        "**停在 19%（5310~7020）**：kaito9 46,319 格、余额 380~526 万，只剩 Norman 一个真人邻居（密度 101~127）。buyLand 的「唯一真人邻居」闸要余额 ≥593 万（1.28×100×领土）才打，留底抬到 519 万；"
        "而调度在密度 108~114 时每次捐走约 100 万、另付约 32 万手续费，密度回到 81~85。1,710 拍里 kaito9 0 条进攻、8 笔捐款 820 万、手续费 258 万（同期利息的 21%）；alex_k 同样（唯一邻居 Micha），5 笔 195 万。"
        "兵都到了 leo_tx 手里：收 13 笔 983 万，37 条 1,027 万打出去——20 条 583 万打 Norman（Norman 12 条 675 万打回来），15 条 382 万把 Twój stary 从 219 万兵磨到 6342 梭哈；"
        "Twój stary 剩下的 1.7~2.2 万格（每格十几兵）leo_tx 有 34 个决策拍发不出指令（留底 88×领土高过余额），地被 Norman 的一条船收走（Norman 39,535→57,328 格）。全队 18.62%→18.96%。"
        "同一段 T5 的薄处在另一头：Player 384 6030 时 93,812 格 / 194 万兵（密度 21），Player 937 密度 12；T2 这边打它们的只有 Player 769（21 条 676 万，32,127→91,479 格），他全场没收到一笔捐款——调度的收方只认我方号。",
        "**Player 769 梭哈与横扫（7020~8822）**：7060 Micha 贴上 kaito9（第二个真人邻居），闸松开，6 条 272 万打 Norman（46,319→53,754 格）。7567 Player 769 pct=1023 把 501 万兵压到 Player 915 身上，撤回后 7658 又装船 431 万；"
        "他 6.4 万格只剩 3 个兵，被 Player 384、dih、Micha、Player 915 分掉。Player 384 93,934 格（7650）→141,313 格 / 1,682 万兵（8280）。kaito9 7658~8449 八条 483 万打 T1 的 Micha、6 条 247 万打 Player 915，长到 69,501 格。"
        "8337 给顶着硬上限的 leo_tx 捐了一笔：到账 624,669、手续费 490,200，19 拍后 leo_tx 出局。8554 Player 915 把 213 万兵全装船去打 alex_k，自己 2.95 万格只剩 3~11 万兵、贴着 kaito9；"
        "kaito9 有 240~630 万兵，33 个决策拍发不出一条（留底 88×领土）。8561 起 Player 384 七条 pct=150 共 1,639 万、Norman 八条 617 万，kaito9 8822 出局。",
    ],
    "extraCommands": [
        "bash c136-review/tools/run-heavy.sh node /agent/repos/c136-data/src/tools/replay_cmds.mjs A061 --out c136-review/agents/R07/out/A061/cmds.tsv",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/60_truth.cjs A061",
        "python3 61_truth_view.py A061", "python3 62_rank.py A061 --at 180,540,900,990,1530,1980,2160,2700,3240,4050,4770,5400,6030,6300,6840,7650,8280,8730,8820 --top 14",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/67_troop_flow.mjs A061 --cuts 0,990,2142,3213,4284,5400,6480,7560",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/67_troop_flow.mjs A061 --cuts 0,540,990,1500,1980,2700,3510,4770,5310,6030,7020,7560,8280 --tag tp",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/74_side_flow.mjs A061 --cuts 0,990,2142,3213,4284,5400,6480,7560 --top 8",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/74_side_flow.mjs A061 --cuts 0,540,990,1500,1980,2700,3510,4770,5310,6030,7020,7560,8280 --top 6 --tag tp",
        "python3 63_replay_ledger.py A061",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/69_quota_truth.mjs A061",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/66_spawn_truth.mjs A061",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/65_shadow.mjs A061 --trace zero_7:1400:1980 --trace alex_k:1400:2700 --trace zexos1:1400:2700 --trace kaito9:1400:2900 "
        "--trace sora_w:1500:2520 --trace riku_x:1400:2560 --trace ryan_m:1400:2650 --trace leo_tx:1400:2700 --trace kaito9:5300:7100 --trace alex_k:5300:6600 --trace leo_tx:5300:7100 "
        "--trace kaito9:7100:8822 --trace kaito9:2850:5300 --trace zexos1:4300:6030 --trace leo_tx:7100:8356 --trace alex_k:6600:8786",
        "python3 64_cmd_loss.py A061",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/76_boat_targets.mjs A061",
        "python3 70_team_density.py A061 --at 990,1530,1980,2160,2700,3240,4050,4770,5400,6030,6300,6840,7650,8280,8730", "python3 71_death_chain.py A061", "python3 72_repeat_sends.py A061",
        "python3 73_front_width.py A061", "python3 75_interest.py A061 --at 990,1530,1980,2160,2700,3240,4050,4770,5400,6030,6300,6840,7650,8280,8730", "python3 77_drop30_classify.py A061",
        "python3 80_donation_yield.py A061", "python3 81_same_tick_batches.py A061", "python3 82_outlet_gap.py A061",
        "python3 78_bot_share.py A061 --bots alex_k,kaito9,riku_x,ryan_m,zero_7,zexos1 --at 990,1080,1170,1260,1350,1440,1530 --tag frozen6",
        "python3 79_help_table.py A061 --who zero_7:1600:1980 --who sora_w:2000:2523 --who riku_x:2280:2560 --who ryan_m:2450:2650 --who zexos1:4360:6030 --who leo_tx:7850:8356 "
        "--span 1500:2700 --span 2701:5310 --span 5311:7020 --span 7021:8822",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/68_watch.mjs A061 --ids 49,zero_7,alex_k,zexos1,43,1 --t0 1480 --t1 2000 --step 20 --tag bigboss --cmds 1",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/68_watch.mjs A061 --ids kaito9,43 --t0 4760 --t1 4960 --step 10 --tag eyup_allin --cmds 1",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/68_watch.mjs A061 --ids 50,23,leo_tx,47 --t0 6180 --t1 6780 --step 30 --tag norman_boat --cmds 1",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/68_watch.mjs A061 --ids 6,24,29,35,kaito9 --t0 7380 --t1 8100 --step 30 --tag p769_exit --cmds 1",
        "bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/68_watch.mjs A061 --ids 24,alex_k,kaito9,29 --t0 8540 --t1 8820 --step 20 --tag p915_empty --cmds 1",
        "python3 84_pair_cmds.py A061 --on zero_7 --on sora_w --on riku_x --on ryan_m --on zexos1 --on leo_tx --on alex_k --on kaito9 --tag deaths",
        "python3 84_pair_cmds.py A061 --by alex_k:1500:2700 --by zero_7:1500:2000 --by zexos1:1500:2700 --by sora_w:1500:2523 --by riku_x:1500:2560 --by ryan_m:1500:2650 --by kaito9:1500:2700 "
        "--by leo_tx:1500:2700 --on 49 --on 31:1500:3912 --on 1:1500:3547 --tag tp2",
        "python3 84_pair_cmds.py A061 --by kaito9:2701:5309 --by leo_tx:2701:5309 --by alex_k:2701:5309 --by zexos1:2701:6030 --on 43 --on 15 --on 23 --on 47:5310:8600 --tag mid",
        "python3 84_pair_cmds.py A061 --by leo_tx:5310:7020 --by kaito9:5310:7020 --by alex_k:5310:7020 --by 6:5310:7020 --by 6:7021:8100 --by 29:5310:7020 --by 38:5310:7020 --by 50:5310:7020 "
        "--by 24:5310:7020 --by 35:5310:7020 --by 29:7021:8859 --by kaito9:7021:8859 --tag tp3",
        "python3 84_pair_cmds.py A061 --on 6 --on 6:7021:8100 --on 29:5310:7020 --on 38:5310:7020 --on 50 --on 24:5310:8100 --by 6 --tag p769",
        "python3 84_pair_cmds.py A061 --on 50:5310:7020 --on 23:5310:7020 --on 6:5310:7020 --by 45 --by 36 --tag t5bank",
        "python3 85_trace_blocked.py A061 leo_tx:5300:7100 zexos1:4300:6030 kaito9:2850:5300 leo_tx:7100:8356 alex_k:6600:8786 kaito9:7100:8822",
        "python3 86_enemy_neighbors.py A061 --at 360,540,720,990,1080,1260,1440,1530,1980,2160", "python3 87_trace_classify.py A061",
    ],
    "timelineTs": [180, 540, 990, 1530, 1980, 2160, 2700, 3240, 4050, 4770, 5310, 6030, 6300, 7020, 7560, 8100, 8280, 8730],
    "timelineNotes": {
        180: "出生阶段结束：10 个号挤在 209×183 像素里，最近队友 51~63.9 像素",
        540: "真值 19,250 格（3.98%）；单号中位数 1,879 格、名次中位数 22/53（全体真人中位数 1,833）：和全场持平",
        990: "882 talon5 / noah88 离开（当时合计 7,453 格）；在场 8 个号 32,204 格；名次中位数 39/48；贴着内置 AI 的席位只剩 6 个（1080 剩 2 个）；T5 12.1%",
        1530: "1512~1526 三个号 9 条指令打出 545,192 兵；六个不动的号此前拿着全队 85% 的余额；名次中位数 38/46；T5 26.9%",
        1980: "zero_7 1977 出局；Big Boss 1799、HD.MAX 1793 出局；kaito9 16,234 格；T5 32.6%",
        2160: "这一段的峰值 12.43%；kaito9 16,234 格 / 58.8 万兵不动；sora_w、riku_x、ryan_m 正在挨打",
        2700: "sora_w 2523、riku_x 2559、ryan_m 2646 出局；剩 4 个号 45,451 格 / 257 万兵；T2 13.1%、T5 35.8%",
        3240: "四个号密度 81~96；kaito9 2870 过软上限后才开始打 Yolo",
        4050: "Yolo 3547、Player 625 3912 出局；2261 之后的头两笔调度 4074 / 4102 给 kaito9；zexos1 密度 112、alex_k 108",
        4770: "kaito9 35,861 格；4795 Eyup 把 121.6 万兵全压上来，kaito9 4809~4837 六条脉冲磨光它",
        5310: "Eyup 5010、JM LEPEN 5294 出局；89,972 格 / 659 万兵；T2 25.3%、T5 51.0%、T4 15.0%",
        6030: "zexos1 出局；kaito9 46,319 格 / 460 万兵不动（密度 99）；T5 七个人 1,637 万兵、加权利率 64，每 10 拍利息 105,046（我方三个号 118,800）",
        6300: "全局峰值 95,607 格 / 943 万兵；T2 36.4%（Player 769 80,311 格）、T5 54.1%；6342 Twój stary 梭哈打 leo_tx",
        7020: "5310~7020：捐款 14 笔到账 1,021 万、手续费 326 万，领土 +1,680 格；T2 37.9%、T5 57.4%",
        7560: "alex_k 被 Micha、Player 915 打到 8,113 格；7567 Player 769 把 501 万兵全压到 Player 915 身上",
        8100: "Player 769 的地被分光（8010 之后消失）；T2 18.8%、T5 71.9%；kaito9 68,402 格",
        8280: "kaito9 69,501 格 / 727 万兵；Player 384 141,313 格 / 1,682 万兵；8337 给 leo_tx 的一笔到账 62 万、手续费 49 万",
        8730: "leo_tx 8356 出局；kaito9 59,698 格 / 511 万兵，8561 起挨 Player 384 七条 1,639 万；alex_k 8786、kaito9 8822 出局",
    },
    "contextExtra": {
        "strategyVersion": f"{VB}（名牌 [APEX]，Vb 批次）+ {SPVB}（出生协调器）。全场 0 条策略报错；慢拍 3 条（talon5 t=850 26.6 ms、sora_w t=930 28.7 ms、ryan_m t=1120 25.3 ms）",
        "gameVersion": "引擎 2.17.x。真引擎重放（60_truth.cjs）与干净模拟器重演都和 traj.csv 的 476 个快照（领土、余额）逐条一致；录像到 8859 拍（我方最后一个号 8822 出局）",
        "contamination": [
            "IO：talon5、noah88 两个席位 t=882 离开（结算表 event=left；两个客户端 05:51:14.951Z / 05:51:15.087Z 相隔 136 毫秒，in_game.log L500 / L501；录像里 903 离开）。"
            "当时 2,771 / 4,682 格；之后由内置 AI 接管，1340 / 2040 被吃光。原因不明",
            "同队真人 Player 769#6[T2]：全程和我方号不接壤，没有捐款往来。5310~7020 他一个人把 T2 从 25.3% 带到 37.9%；7567 pct=1023 把 501 万兵压到 Player 915 身上、7658 再装船 431 万，"
            "自己的地只剩 3 个兵，8010 之后消失。终局的塌方从这里开始，不是我方号的决策",
            "名义 6 队、实际 5 队，54 个真人位。990 时贴着我方号的敌方真人 8 个：T1 5 个、T3 2 个、T4 1 个，T5 一个都没有（86_enemy_neighbors.py）",
            "对局卡 teamSplitCounts 只数到 8 个号（882 离开的两个没有结算队伍）；按录像头 10 个号全在 T2。时间线的「我方号份额 / 兵力」只统计当拍有 HL-TICK 的号",
        ],
        "notes": "影子运行（65_shadow.mjs）：同一份 Vb 源码在重演出的真实局面上逐拍决策、指令只记不执行。476 条 HL-TICK 的领土 / 余额 / nb / neut 全部对上，21 条 HL-DISPATCH 与 73 条 HL-OPENING 逐条同拍同数；"
                 "影子的指令数比录像多 8 条（kaito9 1、zexos1 1、riku_x 6，都是同一拍的第二条或没落地的）。影子给出的内部量（need、worth、safe、keep、avail、各道闸的归类）按源码公式重算，文中标「影子」；真号内存里的值看不到。"
                 "本局新增两段影子诊断：buyLand 里「唯一真人邻居 / crowdedHard / 缩圈」各道闸逐拍归类；t<1500 没有 AI 邻居的号为什么不打贴身真人（floorAt 逐项复刻，392 次核对 0 次不一致）。",
    },
    "phases": {
        "opening": {
            "facts": [
                "出生点（重演真值）：10 个号在 x 728~937、y 973~1156 的 209×183 像素里，最近队友 51~63.9 像素（中位 55.4）；全场对照 T5 107.7、T3 85.5、T4 65.5、T1 54.7（66_spawn_truth.mjs）",
                "协调器 42 次求解（in_game.log L3 minSep=70px → L322~L324 minSep=51~52px）；角色：sora_w CORNER_APEX_BANK，alex_k / talon5 / zexos1 INNER_ARC_BANK，其余 6 个 OUTER_SHIELD_WALL（L325~L334）",
                "t=221 的 OPENING-CHECK 10/10 OK（L375，单号 144~377 格）；73 条 [HL-OPENING] 影子逐条复现",
                "t=540：19,250 格（3.98%），单号中位数 1,879 格、名次中位数 22/53；各队真人的单号中位数 T1 1,611 / T3 1,724 / T4 1,726 / T5 1,883",
                "540~990（side_flow_tp.txt A）：我方 106 条进攻（24 无主 / 82 AI），打 AI 110,644 兵，19,250→39,716 格；T1 150,053 兵→56,045 格，T3 146,973→55,413，T4 198,091→61,357，T5 150,250→58,594",
                "贴着内置 AI（或离开席位）的我方席位：10 个（720）→9（900）→6（990）→2（1080）；贴着敌方真人的：5（540）→7（720）→9（1080）（outlet_gap.txt A）",
                "882：talon5（2,771 格 / 17,676 兵）、noah88（4,682 格 / 17,753 兵）离开",
            ],
            "issues": [
                "SP：十个号挤在 209×183 像素里，外面一圈是 T1 / T3 / T4 的八个真人，圈里的 AI 一千拍分完",
                "OP（影子）：t=300~1499 有 AI 邻居的 1,457 个决策拍只出手 149 个；零指令 1,268 个里 568 个是 AI 单价高于当拍出价，384 个卡在参照队友余额的 safeFinite 留底（其中 246 个最好的目标每格 ≤3 兵）",
                "IO：两个席位在 882 离开，原因不明",
            ],
        },
        "expansion": {
            "facts": [
                "990~1500（side_flow_tp.txt A）：我方 8 个号 36 条进攻（8 无主 / 28 AI / 0 真人），打 AI 101,088 兵，39,716→48,901 格（+9,185），余额 248,769→1,400,414；"
                "T5 87 条（5 / 79 / 3），打 AI 483,340 + 打真人 132,504，58,594→128,239 格（+69,645）；T1 +33,407、T3 +25,288、T4 +25,471 格",
                "六个号（alex_k、kaito9、riku_x、ryan_m、zero_7、zexos1）990→1440：22,455→24,988 格，余额 174,814→958,938，占全队余额 83.6%→85.4%（最高 88.9%，bot_share_frozen6.txt）；长地的只有 leo_tx（6,237→11,899）和 sora_w（3,512→6,225）",
                "影子（shadow_early_humans.txt）：t=300~1499 没有 AI 邻居、也没有无主地的决策拍 525 个，发令 5 个；零指令 520 个 = 留底参照队友 142 + 价格留底 101 + keepCap 封顶 81 + 过了留底但一次吃不光 69 + 四周只有队友 59 + defenseNeed 按最低单价 53 + 参照敌方真人 15",
                "t=1500 解锁：1512~1526 zero_7 / alex_k / zexos1 各三条，合计 545,192 兵；Big Boss 挨 419,206 兵（全部来自我方），1799 出局",
                "1977~2646 zero_7、sora_w、riku_x、ryan_m 出局；1500~2700 全队只有一笔调度（2261 ryan_m→leo_tx 到账 39,163）",
                "kaito9：1645~1652 三条 54,334 兵吃 HD.MAX（7,727→16,234 格）；1652~2870 没有指令，1890~2790 领土一直是 16,234 格，余额 37.4 万（1890）→131.4 万（2700）",
            ],
            "issues": [
                "OP：没有 AI 邻居的号在 t<1500 对贴身真人只走猎杀规则，留底又参照队友的余额——六个号 500 拍不长地",
                "AT：解锁那一拍连发三条同比例的单子，余额被打到自己的留底以下",
                "DN：不是围死号的捐方要密度 ≥102（协防）/ ≥108（余粮），四个号被打时没有一个捐方够得着",
                "EC：kaito9 1,218 拍只攒不打（目标每格成本一直高于出价，直到过软上限）",
            ],
        },
        "midgame": {
            "facts": [
                "2700~5310：四个号 45,451→89,972 格（9.40%→18.62%），余额 257 万→659 万；T2 13.1%→25.3%，T5 35.8%→51.0%，T4 25.5%→15.0%，T1 19.7%→8.3%，T3 5.2%→0",
                "kaito9 2701~5309 32 条 7,363,962 兵（手续费 826,957）：Eyup 15 条 3,412,590、JM LEPEN 6 条 1,686,392、Yolo 9 条 1,133,240、Kalmar 离开后的席位 2 条 1,131,740；16,234→46,253 格",
                "影子：kaito9 2850~5300 出手 32 拍，17 拍是过软上限时发的（c/worth 1.56~3.70），其余是对濒死 / 失血目标的脉冲；396 个决策拍价高",
                "我方打出局的真人席位（F 表：我方兵占它挨的兵的比例）：Yolo 3547（94%）、Player 625 3912（53%）、Eyup 5010（93%）、JM LEPEN 5294（76%）",
                "4795 Eyup pct=1023 把 1,202,092 兵压到 kaito9 身上；kaito9 4809~4837 六条 pct=122 共 1,142,950 兵，Eyup 的进攻槽 4840 归零，kaito9 领土 37,673→37,344→43,258（4960）",
                "调度只有 2 笔：4074（zexos1→kaito9 183,492）、4102（alex_k→kaito9 253,707）；2701~5310 的 417 个相位拍里 328 个没有合格的收方（984 个捐方-候选对里 951 个卡在余粮的捐方密度）",
                "zexos1：4445~4634 Player 915 三条 783,477 兵，8,515 格（4050）→4,646 格（4770）",
            ],
            "issues": [
                "AT：出手的开关是「过软上限」——密度到 100 之前有敌邻也不打，到了之后不比价",
                "DF：zexos1 被 Player 915 削的时候 0 笔收捐",
            ],
        },
        "endgame": {
            "facts": [
                "5310~7020（side_flow_tp.txt A 两档相加）：我方利息地租 20,969,950，45 条进攻（42 条打真人 11,085,807 兵），捐款 14 笔到账 10,214,402、手续费 3,259,183，进攻手续费 1,206,033，挨打掉 4,741,090；领土 89,972→91,652（+1,680）",
                "同一段 Player 769：利息地租 11,313,841，21 条 6,764,495 兵，32,127→91,479 格（+59,352）；T5：利息地租 29,622,841，246,388→277,560 格",
                "kaito9 5222 之后到 7070 之前没有进攻；影子 5300~7100：118 个决策拍卡在「唯一真人邻居」（5470~6955），8 拍捐兵，232 拍价高，出手 3 拍（7060~7070）",
                "leo_tx 5310~7020：收捐 13 笔 9,827,832；37 条 10,266,204 兵（手续费 1,057,198）= Norman 20 条 5,830,535 + Twój stary 15 条 3,818,471 + 🙉🙈🙊 2 条 617,198；22,091→29,243 格",
                "6300→6840：Twój stary 17,444→0 格，Norman 39,535→57,328（+17,793），leo_tx 30,250→28,703",
                "7567 / 7658 Player 769 两次 pct=1023（5,012,438 兵陆攻、4,305,442 兵装船）；7650→8280 Player 384 93,934→141,313 格，T2 31.9%→18.1%，T5 62.8%→73.2%",
                "kaito9 7021~8859：24 条 11,593,778 兵（手续费 1,845,217）= Micha 8 条 4,830,072 + Norman 6 条 2,724,166 + Player 915 6 条 2,469,888 + 无主地 3 条 944,983 + 捐款 1 笔 624,669",
                "8561~8813 Player 384 七条 pct=150 共 16,392,024 兵打 kaito9；Norman 八条 6,170,035",
            ],
            "issues": [
                "EC / DN：最大的号被「唯一真人邻居」闸和调度门槛卡成银行，利息的两成交了手续费",
                "AT：贴着空壳（Twój stary 6345~6510、Player 915 8630~8790）发不出指令，留底顶在 88×自己的领土",
                "EG：T5 的薄处不和我方号接壤，兵到不了同队真人手里",
                "DN：最后一笔协防给了顶着硬上限、19 拍后出局的号",
            ],
        },
    },
    "turningPoints": [
        {
            "t0": 540, "t1": 1530,
            "what": "从持平到垫底。540 拍我方单号中位数 1,879 格、名次中位数 22/53；1530 是 4,623 格、38/46（全体中位数 7,767）。先是圈里的内置 AI 被分完（贴着 AI 的席位 10→2），"
                    "990 之后 9 个席位贴着敌方真人却不出手：990~1500 全队只多 9,185 格，T5 多 69,645 格。六个号 500 拍不长地，拿着全队 82%~89% 的余额；882 还丢了两个席位",
            "shareBefore": 0.0398, "shareAfter": 0.0903,
            "ourBots": ["alex_k", "kaito9", "riku_x", "ryan_m", "zero_7", "zexos1", "leo_tx", "sora_w", "talon5", "noah88"],
            "enemies": ["T5 十个真人：990~1500 87 条进攻，483,340 兵打 AI，58,594→128,239 格（990→1530：Player 384 5,581→19,406、Player 915 5,837→19,415、Player 937 5,073→15,358）；全程不和我方号接壤",
                        "[UNSC] Big Boss#49[T1]：5,592 格 / 14,351 兵（990）→10,295 格 / 55,937 兵（1440），密度 3~5，贴着我方四个号",
                        "Player 625#31[T1]：7,918 格（990）→14,648 格 / 188,613 兵（1530），1260 起贴着 zexos1"],
            "evidence": [
                "side_flow_tp.txt A：990~1500 我方 36 条进攻（8 无主 / 28 AI / 0 真人），发兵 8,038 / 101,088 / 0，39,716→48,901 格，余额 248,769→1,400,414（密度 6→29）；"
                "T5 87 条（5 / 79 / 3），发兵 23,397 / 483,340 / 132,504，58,594→128,239 格，余额 330,720→1,461,107（密度 6→11）。540~990 我方打 AI 110,644 兵，其余四队 146,973~198,091",
                "shadow_early_humans.txt（影子）：t=300~1499 没有 AI 邻居、也没有无主地的决策拍 525 个，发令 5 个。零指令 520 个：留底 = 队友余额的 2 倍（preyFloor 0.5 × kDef 4 × 邻居的另一个最弱邻居）142 拍，"
                "价格留底 101，keepCap 封顶 81，过了留底但 sendFrac×可用兵 < 吃光所需 69，四周只有队友 59，按最低单价的 defenseNeed 53，参照敌方真人 15。"
                "例：t=1400 zero_7 余额 152,105，Big Boss 10,134 格 / 54,440 兵（每格 19.2），留底 161,294（= 2×ryan_m 的 80,647），可用 −9,189，吃光要 112,238",
                "bot_share_frozen6.txt：alex_k、kaito9、riku_x、ryan_m、zero_7、zexos1 六个号 990 / 1260 / 1440 的领土 22,455 / 24,768 / 24,988，余额 174,814 / 548,256 / 958,938，占全队余额 83.6% / 88.9% / 85.4%",
                "outlet_gap.txt A + rank.txt：贴着内置 AI 或离开席位的我方席位 10（720）→9（900）→6（990）→2（1080）；贴敌方真人的 7（990）→9（1080）。名次中位数 22/53（540）→39/48（990）→38/46（1530）",
                "spawn_truth.txt + enemy_neighbors.txt：我方最近队友 51~63.9 像素（中位 55.4），包围盒 209×183 像素；T5 最近同队 107.7、最近任一真人 78.8。990 时贴着我方号的敌方真人 8 个（T1 5 / T3 2 / T4 1 / T5 0）；"
                "1440 时六个不动的号各自最弱的真人邻居：Big Boss 密度 5.4（贴着 alex_k、zero_7、ryan_m）、JM LEPEN 11.5（kaito9）、Micha 11.1（riku_x）、Player 625 12.1（zexos1），自己的密度 22~92。in_game.log L3 / L324：协调器 42 次求解，minSep 70→51 像素",
                "shadow_early.txt（影子）：有 AI 邻居的 1,457 个决策拍出手 149 个；零指令 1,268 个里 AI 单价高于出价 568、参照队友余额的 safeFinite 384（其中 246 拍最好的目标每格 ≤3 兵，平均 399 格）；"
                "各号最后一个有 AI 邻居的决策拍：talon5 820、noah88 900、alex_k / zexos1 915、riku_x 1005、ryan_m 1025、kaito9 1055、zero_7 1190",
                "results.csv + death_chain.txt + in_game.log L500 / L501：talon5（2,771 格）、noah88（4,682 格）t=882 离开；两个席位 990 时还有 7,512 格，talon5 的地 1340 前被吃光（Player 625 1080 贴上这个席位，1260 起贴上 zexos1）",
                "truth_view.txt A：各队份额 540 拍 T1 3.8 / T2 4.3 / T3 3.5 / T4 4.0 / T5 3.6；990 拍 11.6 / 9.4 / 11.5 / 12.7 / 12.1；1530 拍 18.6 / 13.4 / 16.7 / 17.9 / 26.9",
            ],
            "priorDecisions": [
                {"t": -1, "bot": "全队", "action": "协调器按「全图陆地 ÷ 真人数」算格距（54 个真人位 → 约 53 像素），把 10 个号排成间距 51 像素的角落扇形阵；外面一圈是 T1 / T3 / T4 的真人", "logRef": "in_game.log L3、L322~L334；spawn_truth.txt A / B；enemy_neighbors.txt A",
                 "codePath": f"{SPVB}:L838 `rCell = sqrt(max(10000, land) / (π × totalActiveHumans))`、L1065-1077 CORNER SECTOR PHALANX（`minReqSep = clamp(round(0.95*rCell), 42, 68)`）、L1344-1368（指派）→ {VB}:Policy.chooseSpawn:L3983-4037"},
                {"t": 935, "bot": "alex_k / zero_7 / ryan_m / kaito9 / zexos1", "action": "没有 AI 邻居之后，开局逻辑对贴身真人只走猎杀规则：留一半常规留底，0.746×可用兵要一次够吃光对方；常规留底里的 defenseNeed 取「邻居的另一个最弱邻居」余额的 4 倍，不排除队友",
                 "logRef": "shadow_early_humans.txt（各号 70~113 个决策拍，发令 0~1 条）",
                 "codePath": f"{VB}:Style.pickTarget:L1152-1165 → V13.floorFor0:L2233-2241（L2240 `P.preyFloor * f`）→ General.floors:L819-831（L829 floorAt）→ General.defenseNeed:L899-913（L909 `P.kDef * Math.max(a.minBal - sent, …)`）→ General.altOf:L918-941（只排除目标和我）；"
                             "V13.amount0:L2347-2349（`P.sendFrac * avail >= P.preyKill * need` 才发，否则 0）"},
                {"t": 450, "bot": "zero_7 / ryan_m / zexos1 / sora_w / leo_tx 等", "action": "有 AI 邻居时，打 AI 的留底取「这个 AI 的其他邻居里余额最小的那个」的余额，不排除队友：例 t=450 zero_7 余额 3,020，隔壁 AI#218 有 247 格 / 8 兵（每格 2.1），留底 3,322 正好是 ryan_m 的余额",
                 "logRef": "shadow_early.txt",
                 "codePath": f"{VB}:Style.pickTarget:L1144-1177 → V13.floorFor0:L2233-2241 → Policy.winFloor:L4562-4570 → V13.safeFinite:L2500-2510 → threatOf:L417-444"},
                {"t": 882, "bot": "talon5 / noah88", "action": "两个客户端同时离开（不是策略决策）；席位交给内置 AI，利息归零", "logRef": "in_game.log L499~L501；results.csv",
                 "codePath": "不在策略代码里；引擎 game.js leave L223-234（state=2，不再生息，按内置 AI 的定时器出兵）"},
            ],
            "alternatives": "Big Boss 在 990~1440 一直是密度 3~5、贴着四个号；t=1400 时 alex_k 一个号的余额 175,332 就超过吃光它所需的 112,238（影子），0.746×余额也够——卡住的只是那一半留底。"
                            "1500 解锁后三个号确实去打了它（41.9 万兵，1799 出局），但那时 T5 已经 26.9%。如果这 500 拍里六个号的 96 万兵能换成地，按 1500~1980 我方每净增一格 58 兵的实价是 1.6 万格上下（全图 3% 多）；"
                            "站位如果像 T5 那样分开，每个号都有 AI 可吃，差距会小得多——没有可对照的局，是推断。",
            "statementType": "observed",
            "confidence": "两边的发兵、领土、余额、名次：高（引擎重演的逐条真值，逐人逐窗核对差额为 0）。「为什么不打」的归类：中高（影子；floorAt 逐项复刻与策略自己的值 392 次核对全部一致，与真日志的 nb / neut 逐条一致）。差距归因到站位和这两条留底规则：推断。",
        },
        {
            "t0": 1500, "t1": 2700,
            "what": "解锁那一拍把兵打穿，四个号接连出局。t=1500 全队同拍换成核心逻辑：zero_7、alex_k、zexos1 各在三个决策拍里发了三条同比例的单子，余额剩 16%~25%；"
                    "三个号 14 拍打出 545,192 兵，其中 339,248 压在 Big Boss 一个人身上。zero_7 1977 出局，随后 sora_w 2523、riku_x 2559、ryan_m 2646——四个号各挨 11~15 万兵，一笔捐款都没收到；"
                    "同一段 kaito9 在 16,234 格上把余额从 22 万攒到 131 万，一条指令没有。全队 9.03%→12.43%（2160）→9.40%（2700），8 个号剩 4 个",
            "shareBefore": 0.0903, "shareAfter": 0.094,
            "ourBots": ["zero_7", "alex_k", "zexos1", "sora_w", "riku_x", "ryan_m", "kaito9", "leo_tx"],
            "enemies": ["[UNSC] Big Boss#49[T1]：10,972 格 / 87,336 兵（1512）→1799 出局；挨的 419,206 兵全部来自我方三个号",
                        "Eyup#43[T1]：6,164 格 / 288,433 兵（1610），9 条 pct=75 共 173,388 兵打 zero_7", "Yolo🙋‍♂️#1[T3]：打 zero_7 3 条 93,848 兵；打 ryan_m 4 条 411,401 兵（2590 一条 pct=321 190,485）",
                        "Player 915#24[T5]：8 条 pct=109 共 232,877 兵打 sora_w", "Player 775#41[T3]：2429 一条 pct=301 79,071 兵打 riku_x"],
            "evidence": [
                "watch_bigboss.txt + humans_cmd.tsv：1512 zero_7 pct=374（201,816→125,544）、1519（→78,098）、1526（→49,677）；alex_k 1512 ×2 / 1519 pct=453~454（232,654→126,779→68,962→37,512）；"
                "zexos1 1512 / 1519 ×2 pct=486~487 打 Player 625（243,737→124,964→63,947→32,724）。1520 时 zero_7 家里 79,855 兵（密度 22）、进攻槽里 119,154；1620 时 4,562 格 / 62,396 兵（密度 14），Eyup 14,809 + Yolo 27,689 压在身上",
                "shadow_trace_zero_7_1400_1980.txt（影子）：t=1500 余额 197,318，Big Boss need=168,654，safe=122,812，avail=72,194 → pct=374；1505、1510 同一条（余额还是 197,318 / 201,816）；1515 avail=−1,606；之后 35 拍可用兵 ≤0、58 拍价高，零指令",
                "death_chain.txt：zero_7 最后 500 拍挨打掉 154,658 兵（Eyup、Yolo），sora_w 125,249（Player 915、Player 625），riku_x 109,702（Player 775、Micha、Player 625），ryan_m 153,603（Yolo）；四个号收捐合计 0 笔",
                "help_table.txt D（1500~2700）：341 个相位拍，没有合格的收方 225、捐方压在真人身上的兵 >8% 50、捐方自己在挨打 44、捐出 1 笔；1,473 个（捐方, 候选）对里 1,075 个卡在余粮的捐方密度、186 个卡在协防的捐方密度。"
                "C（zero_7 1600~1980）：108 个相位拍，捐方密度不到协防门槛 29、收方领土太小 27、捐方有兵压在真人身上 23、判成弃子 17",
                "troop_flow_tp.txt B + pair_cmds_tp2.txt + shadow_trace_kaito9_1400_2900.txt：kaito9 1980~2700 0 条进攻，余额 437,726→1,313,745，16,234 格；1652 之后到 2870 之前没有指令；256 个决策拍价高"
                "（t=1900 出价 35.0，Kalmar 52.5 / JM LEPEN 59.6 / Yolo 64.0；t=2700 出价 72.8）",
                "pair_cmds_tp2.txt：Big Boss 全程只挨我方的兵——alex_k 3 条 190,123、zero_7 3 条 149,125、sora_w 6 条 79,958；repeat_sends.txt：吃光 Big Boss 约需 171,916",
                "cmd_loss.txt + same_tick_batches.txt：riku_x 想发 62 条、收下 56 条，延迟中位数 32 拍（其他号 10~18），24 条晚到 ≥35 拍；t=2079 一拍落地 5 条（余额 150,849→99,874）",
                "truth_view.txt A：我方 9.03%（1530）→11.79%（1800）→12.43%（2160）→9.40%（2700）；T2 在场真人席位 10→5",
            ],
            "priorDecisions": [
                {"t": 1500, "bot": "zero_7 / alex_k / zexos1", "action": "换成核心逻辑后的头三个决策拍各发一条：每条都按「留够 safe」算的，但上一条 12 拍后才落地，三拍看到的余额和目标身上自己的兵都没变；指令带的是比例，落地时各按当拍余额扣一次",
                 "logRef": "shadow_cmds.tsv t=1500~1510（发令行 buyLand:5616）；shadow_trace_zero_7_1400_1980.txt",
                 "codePath": f"{VB}:V17.act:L2690-2693（`g.t < P.coreFrom` 才走开局逻辑）→ Policy.act:L4942 buyLand → Policy.buyLand:L5444 `keep = Math.max(keep, safe)`、L5446 `avail = B - fee - keep`、"
                             "L5611-5616（`want = 1.25*need + 3*cnt; x = min(avail, want)`）→ Policy.send:L3838-3925"},
                {"t": 1600, "bot": "ryan_m / kaito9 / alex_k / leo_tx / zexos1", "action": "队友挨打时没人捐得出：不是围死号的捐方，协防要密度 ≥102 且高出收方 16，余粮要 ≥108；自己身上有真人的进攻或压在真人身上的兵 >8% 余额也直接返回。"
                                                                                  "这一段密度最高的 ryan_m 是 41~109，kaito9 20~81",
                 "logRef": "help_table.txt C / D；in_game.log L627（2250 唯一一条调度）",
                 "codePath": f"{VB}:Policy.tryDonateToTeammate:L4343（`myHumanInAtk > 0 || myHumanOutAtk > 0.08*B → return false`）、L4463-4466 Case A `reqD = boxedIn ? … : 102`、L4479-4481 Case B `reqD = boxedIn ? 58 : 108`"},
                {"t": 1652, "bot": "kaito9", "action": "没过软上限时只打每格成本低于自己出价（m×自己的密度）的目标；m 从 1.48 降到 0.9，三个真人邻居的单价一直高于出价，直到 2860 密度过 100",
                 "logRef": "shadow_trace_kaito9_1400_2900.txt",
                 "codePath": f"{VB}:Policy.buyLand:L5350 `m = P.maxW * this.winRatio(g.t)`、L5352 `worth = m * refDens`、L5353 `over = … B > 100 * L`、L5359 `if (c >= worth && c >= cheap && !over) break`"},
                {"t": 2079, "bot": "riku_x", "action": "指令比别的号晚到 20 拍，在途时策略看不到、照旧每个决策拍再发；2079 五条同拍落地（两条无主地、两条 Micha、一条 Player 625），一拍花掉余额的 35%", "logRef": "same_tick_batches.txt；cmd_loss.txt",
                 "codePath": f"执行层（客户端延迟）；{VB}:Policy.act:L4941 expandNeutral + L4942 buyLand（同一拍各发一条）"},
            ],
            "alternatives": "zero_7 如果只落地一条，余额是 125,544（密度 35），高于它自己算的留底；Eyup（密度 47）第一条才 21,407 兵。三个号压在 Big Boss 身上的兵是所需的 2.4 倍，多出的在进攻槽里既不防守也不吃利息。"
                            "四个号死前 500 拍合计挨了 54 万兵，同一段 kaito9 一个号就多攒了 88 万——但它密度只有 20~81，够不着 102 的协防线。四个小号（1890 时 1,172~7,139 格）贴着 Yolo（1980 时 9,460 格）、Eyup（10,709 格）、Player 915（23,065 格）这些邻居，"
                            "就算拿到协防也未必守得住：推断。",
            "statementType": "observed",
            "confidence": "逐条指令、余额、进攻槽、谁打了谁：高（引擎真值）。zero_7 三条是同一个决策重复三次：中高（影子的 need / safe / avail 与录像里的 pct 一致）。没人协防的原因归类：中高（影子复刻 1,187 行调度判定全部一致）。四个号能不能救：推断。",
        },
        {
            "t0": 5310, "t1": 7020,
            "what": "追到 18.6% 之后停住。这 1,710 拍 T2 的利息地租（我方 2,097 万 + Player 769 1,131 万）比 T5 的 2,962 万还多，T4 留下的 15% 地正在被分。我方的兵却出不去："
                    "kaito9（46,319 格、500 万兵）只贴着 Norman 一个真人，被「唯一真人邻居」闸卡住，每次密度涨到 108~114 就被调度削走两成；8 笔 820 万（手续费 258 万）都给了 leo_tx，"
                    "leo_tx 把 1,027 万兵按高价打在 Norman 和 Twój stary 身上，净增 7,152 格；Twój stary 被它一个人磨到梭哈，空出来的地大半被 Norman 的一条船收走。全队 +1,680 格；同一段 Player 769 一个人用 676 万兵拿了 59,352 格",
            "shareBefore": 0.1862, "shareAfter": 0.1896,
            "ourBots": ["kaito9", "leo_tx", "alex_k", "zexos1"],
            "enemies": ["Norman Invasion#50[T5]：38,666→57,988 格，密度 101~127；12 条 pct=110 共 6,751,845 兵打 leo_tx；这一段收 T5 队友捐款 5 笔 2,365,027",
                        "Twój stary 69#23[T1]：24,993 格 / 219 万兵（5418）→6342 pct=971 把 150 万兵压到 leo_tx 身上 →6715 出局",
                        "Player 384#29[T5]：68,323→93,812 格、密度 27→21（6030）→79,957 格 / 585 万兵（7020）；这一段 T2 一侧打它的只有 Player 769（14 条 4,514,871 兵），另有 T4 残部 8 条 999,020 兵",
                        "Player 937#38[T5]：密度 89→12（6030），两笔 pct=1023 把 731,244 兵捐给 Player 384", "Micha [🇩🇪]#47[T1]：alex_k 唯一的真人邻居，密度 118~134"],
            "evidence": [
                "shadow_trace_kaito9_5300_7100.txt（影子）：118 个决策拍归到「唯一真人邻居」（5470~6955，avail −601,344~26,841），8 拍捐兵，232 拍价高，出手只有 7060~7070 三拍。"
                "例 t=5545：余额 5,155,423、46,319 格（密度 111.3），Norman 37,316 格 / 4,359,991 兵，每格成本 449.3 对出价 100.2，keep=5,187,728（1.12×100×领土），avail=−92,720；闸要余额 ≥5,928,832 才放行，窗口内峰值 5,263,018。"
                "t=7060 Micha 成为第二个真人邻居，keep 降到 4,168,710，当拍出手",
                "troop_flow_tp.txt B + pair_cmds_tp3.txt + donation_yield.txt：kaito9 5310~7020 0 条进攻、8 笔捐款到账 8,201,421、手续费 2,584,962，利息地租 12,075,369；每笔落地前密度 109~114、落地后 81~85。"
                "alex_k 5 笔 1,948,509（手续费 652,037）。leo_tx 收 13 笔 9,827,832，其中 5908 / 6111 / 6307 三笔把它推到密度 121~133（利率 137~139→48~83）",
                "pair_cmds_tp3.txt + watch_norman_boat.txt：leo_tx 37 条 10,266,204 兵 = Norman 20 条 5,830,535（Norman 39,117 格 / 399 万→57,998 格 / 585 万）+ Twój stary 15 条 3,818,471 + 🙉🙈🙊 2 条 617,198；Norman 12 条 6,751,845 打 leo_tx。"
                "Twój stary 这一段只挨 leo_tx 的陆攻。6329 Norman 的船带 477,511 兵落在 Twój stary 岸上，6342 Twój stary pct=971 梭哈打 leo_tx（6420 时它 22,267 格 / 8 万兵）；6300→6840 Twój stary 17,444→0 格，Norman 39,535→57,328，leo_tx 30,250→28,703",
                "trace_blocked_leo_tx_5300_7100.txt（影子）：6345~6510 的 34 个决策拍，排第一的目标是 Twój stary（17,376~22,484 格 / 60,767~82,682 兵，每格成本 11.4~41.8，出价 67.4~88.7），leo_tx 余额 157~211 万，"
                "safe 210~253 万（= 84~88×自己的领土），avail −614,310~−421,902；6510 kaito9 的 105 万到账后才在 6515 发出一条（6531 落地，6540 时进攻槽里 211,741 兵；6540→6690 leo_tx 23,237→29,634 格）",
                "side_flow_tp.txt A / D + pair_cmds_p769.txt：Player 769 5310~7020 21 条 6,764,495 兵（Player 384 14 条 4,514,871、Player 915 4 条、Player 937 2 条），32,127→91,479 格，每净增一格 106~160 兵；全场收捐 0 笔。"
                "我方同一段每净增一格 1,201 兵（5310~6030），6030~7020 领土净减",
                "interest.txt A：6030 时我方三个号 8,712,607 兵（密度 93）、每 10 拍利息 118,800，Player 769 48,924；T5 七个人 1,637 万兵（密度 63）、加权利率 64、利息 105,046。6300：114,775 + 71,434 对 117,331；6840：124,183 + 68,487 对 203,204",
                "help_table.txt D（5311~7020）：234 个相位拍，没有合格的收方 156、捐出 14（协防 9、生息余粮 4、进攻余粮 1）；kaito9 68 个相位拍（密度 60~114）里 57 个没有合格的收方、捐出 8",
                "truth_view.txt A + front_width.txt：T2 25.3%→37.9%，T5 51.0%→57.4%，T4 15.0%→0；我方 18.62%→19.78%（6300）→18.96%。kaito9 这一段接壤的敌方真人只有 Norman（156~243 格），alex_k 只有 Micha；我方号全程不和 Player 769 接壤",
            ],
            "priorDecisions": [
                {"t": 5470, "bot": "kaito9 / alex_k / zexos1", "action": "只贴着一个健康真人时，目标价高就要余额 ≥1.28×100×领土才打，过软上限后的留底也从 0.9 抬到 1.12×100×领土：kaito9 118 拍、alex_k 90 拍、zexos1 36 拍卡在这里",
                 "logRef": "shadow_trace_kaito9_5300_7100.txt；shadow_trace_alex_k_5300_6600.txt；shadow_trace_zexos1_4300_6030.txt",
                 "codePath": f"{VB}:Policy.buyLand:L5361-5365（`isSoleHealthyBuffer && c >= worth && c >= cheap && B < P.overHumanCap * 100 * L → continue`）、L5440-5443（`overKeepMult = dMe >= 122 ? 0.82 : isSoleHealthyBuffer ? P.overHumanKeep : P.hold`）"},
                {"t": 5550, "bot": "kaito9 / alex_k", "action": "不是围死号的调度在捐方密度 ≥102（协防，且高出收方 16）/ ≥108（余粮）时发，一次 18%~22% 余额，手续费按全部余额的 6.25%；收方只看密度 <115。于是 kaito9 的密度每到 108~114 就被削回 81~85，永远到不了 128",
                 "logRef": "in_game.log L790~L855（kaito9 8 条、alex_k 5 条）；donation_yield.txt B",
                 "codePath": f"{VB}:Policy.tryDonateToTeammate:L4418 `if (dAlly >= (boxedIn ? 142 : 115)) continue`、L4463-4473 Case A、L4474-4495 Case B、L4500-4508（`idealPct = … 240 / 220`，`pct < 180 → return false`）"},
                {"t": 6345, "bot": "leo_tx", "action": "对真人的留底 safe = min(按最强真人邻居算的 dpKeep, 88×自己的领土)，和这一条打的是谁无关；Twój stary 梭哈后每格只要十几兵，leo_tx 密度 64~71、留底 84~88×领土，34 拍发不出指令",
                 "logRef": "trace_blocked_leo_tx_5300_7100.txt；watch_norman_boat.txt",
                 "codePath": f"{VB}:Policy.buyLand:L5414-5418（`safe = this.safeAt(g, q)`；濒死目标只把封顶换成 collapseFloorCap 85 / oppFloorCap 88 ×领土）、L5444 `keep = Math.max(keep, safe)` → Policy.safeAt:L4543-4560（`s = Math.min(s, P.oppFloorCap * L)`）"
                             " → V17.safeAt:L2728-2738（`P.killW * this.dpKeep(g)`）→ V13.dpKeep:L2459-2464（最强真人邻居的余额 + 它压在我身上的兵）"},
                {"t": 5775, "bot": "kaito9 / alex_k", "action": "调度的收方必须是我方号（或 Boss）：同队真人 Player 769 正在打 T5 密度 12~21 的号，不在候选里；引擎从 4284 起对同队捐款不查配额、也不要求接壤",
                 "logRef": "pair_cmds_p769.txt（Player 769 全场收捐 0 笔）；help_table.txt D",
                 "codePath": f"{VB}:Policy.tryDonateToTeammate:L4414（`!this.isOurSquadBot(g, p) && !this.isBossNpl(g, p) → continue`）→ isOurSquadBot:L3960-3972；引擎 game.js donate L404-416、donationFree L360-362"},
            ],
            "alternatives": "这一段 kaito9 的 1,208 万利息地租里 820 万经捐款到了 leo_tx、258 万交了手续费，自己一格没长。同样的兵有三个去处可以对照："
                            "①留在 kaito9 手里自己打 Norman——Norman 密度 101~127、背后有两个捐方，按 leo_tx 的实价是亏本换地，但至少不付 258 万手续费、也不把 leo_tx 推过软上限；"
                            "②leo_tx 在 6345~6510 吃 Twój stary 的空壳：那是 1.7~2.2 万格（全图 3.6%~4.6%）、家里只有 6~8 万兵；等它 6531 终于发出一条时，21 万兵 150 拍换回 6,397 格，其余被 Norman 拿走（6300→6840 +17,793 格）；"
                            "③给 Player 769：他用 676 万兵拿了 5.9 万格，每格 106~160 兵，是我方同期的十分之一。哪一个去处在当前代码里都走不通（闸 / 留底 / 收方名单）。能不能因此翻盘是推断：T5 当时 51%~57%，6840 起利息已经反超。",
            "statementType": "inferred",
            "confidence": "发兵、捐款、手续费、领土、利息：高（引擎真值，逐人逐窗核对差额为 0）。kaito9 / alex_k 不出手的归类和 leo_tx 对空壳的可用兵：中高（影子按源码公式重算；同一段的 13 条调度日志影子逐条同拍同数）。"
                          "「换个去处会怎样」：推断，没法重演。",
        },
    ],
    "deaths": [
        {"bot": "zero_7", "killers": ["Eyup#43（T1）：9 条 pct=75 共 173,388 兵（1610~1911）", "Yolo🙋‍♂️#1（T3）：3 条 pct=144 共 93,848 兵（1617~1960）", "[UNSC] Big Boss#49（T1）：2 条 5,403 兵"],
         "lastDecisions": ["1500 / 1505 / 1510：三条 pct=374 打 Big Boss（落地 1512~1526，149,125 兵 + 费 4,771），余额 201,816→49,677", "1515~1975：35 个决策拍可用兵 ≤0、58 个价高，零指令（影子）"],
         "cause": "外盾号。1060 起 3,394~3,545 格不动，余额攒到 18.5 万（密度 52），留底参照队友 ryan_m 的余额、打不了贴身的 Big Boss（密度 3~5）。1500 解锁那一拍连发三条：给自己算的留底是 122,812，实际剩 49,677；"
                  "压在 Big Boss 身上的 11.8 万兵不算防守。Eyup（密度 47）1610、Yolo 1617 先后压上来，4,584→2,721 格（1780）；队友 108 个相位拍没有一个过得了捐方门槛，收捐 0 笔，1977 出局。",
         "patternIds": ["NEW:R07-AT-INFLIGHT-REPEAT", "NEW:R07-DF-SPENT-THEN-HIT", "NEW:R07-DN-NO-DONOR"]},
        {"bot": "sora_w", "killers": ["Player 915#24（T5）：8 条 pct=109 共 232,877 兵（1722~2429）", "Player 625#31（T1）：4 条 49,292 兵（2317~2492）"],
         "lastDecisions": ["1526~1659：6 条 79,958 兵打 Big Boss（1659 是最后一条指令）", "1535~2515：53 个决策拍可用兵 ≤0、122 个价高、18 个没有可打的邻居（影子）"],
         "cause": "角顶号。1530 时 6,376 格 / 10.3 万兵（密度 16）。吃到 Big Boss 的一角后（峰值 9,218 格）贴上 Player 915（T5，1530 时 19,415 格）：对方每隔几十拍一条 pct=109，"
                  "它 1659 之后 860 拍没有发出一条指令（留底高过余额，或价高）。队友 126 个相位拍里 77 个卡在捐方密度，唯一过线的一拍（2250 ryan_m）给了 leo_tx。收捐 0 笔，2523 出局。",
         "patternIds": ["NEW:R07-DF-PASSIVE-BLEED", "NEW:R07-DN-NO-DONOR"]},
        {"bot": "riku_x", "killers": ["Player 775#41（T3）：2429 一条 pct=301 79,071 兵", "Micha [🇩🇪]#47（T1）：2 条 pct=99 共 73,232 兵（2366~2520）", "Player 625#31（T1）：3 条 35,078 兵（2499~2548）"],
         "lastDecisions": ["2079~2107：7 条 73,427 兵打 Player 625、2 条 29,387 兵打 Micha（2079 一拍落地 5 条，余额 150,849→99,874）", "2107 之后零指令"],
         "cause": "外盾号，指令延迟中位数 32 拍（其他号 10~18），24 条晚到 ≥35 拍、6 条没落地；1535~1555 五个决策拍被 isNoFullSend 换成 1 兵试探（影子）。1561~2107 用 18 条小单把 Player 625 的地啃到 8,840 格，"
                  "但 2079 那一批把密度打到 6~8。2290 起 Player 775、Micha、Player 625 轮流上，270 拍打光；66 个相位拍里 40 个卡在协防的捐方密度，收捐 0 笔，2559 出局。",
         "patternIds": ["NEW:R07-IO-LAG-BATCH", "NEW:R07-AT-INFLIGHT-REPEAT", "NEW:R07-DN-NO-DONOR"]},
        {"bot": "ryan_m", "killers": ["Yolo🙋‍♂️#1（T3）：4 条 411,401 兵（1589~2590；2590 一条 pct=321 190,485 兵）", "[VN]HD.MAX🇻🇳#37（T3）：2 条 41,992 兵（1470~1519）"],
         "lastDecisions": ["2261：协防调度给 leo_tx（到账 39,163，手续费 12,723）", "2443~2450：3 条 48,183 兵打 Yolo（过软上限后发的，c/worth 2.55~2.59，影子）"],
         "cause": "全队最小的号（峰值 2,457 格），夹在 zero_7、alex_k 和 Yolo、Big Boss 之间。1500~2150 的 100 个决策拍留底高过余额，之后价高；余额攒到 18 万（密度 99）。"
                  "2443 过软上限后三条小单打 Yolo（9,486 格 / 69 万兵），对方 2590 回了一条 19 万，50 拍打光，2646 出局。",
         "patternIds": ["NEW:R07-SP-CLUSTER", "NEW:R07-AT-OVER-BURN", "NEW:R07-DF-SPENT-THEN-HIT"]},
        {"bot": "zexos1", "killers": ["Micha [🇩🇪]#47（T1）：6 条 pct=99 共 1,229,960 兵（4858~5992）", "Player 915#24（T5）：3 条 pct=109 共 783,477 兵（4445~4634）"],
         "lastDecisions": ["5502：生息余粮调度给 leo_tx（到账 64,472，手续费 22,184；自己当时 3,106 格 / 35.5 万兵）", "5901：一条 19,591 兵打 Micha",
                           "4300~6025：263 个决策拍价高、39 个可用兵 ≤0、36 个卡在唯一真人邻居（影子）"],
         "cause": "内弧号。1500 那一拍三条 pct=486~487 打 Player 625，后来 3416~3850 把它打出局，峰值 9,288 格。4445 起 Player 915 三条 78 万兵把它从 8,515 格打到 4,646 格；"
                  "之后只剩 Micha 一个真人邻居（例 t=5700：Micha 16,500 格 / 215 万兵，每格成本 668.7，zexos1 出价 81.1），价高不打，过软上限时又卡在唯一邻居那道闸。Micha 六条 pct=99 逐刀削；"
                  "队友 201 个相位拍里 107 个卡在余粮门槛、24 个卡在协防门槛，它挨打的 76 个决策拍里 24 个被判成弃子。收捐 0 笔，6030 出局。",
         "patternIds": ["NEW:R07-EC-SOLE-BUFFER-BANK", "NEW:R07-DF-DOOMED-SKIP", "NEW:R07-DN-NO-DONOR"]},
        {"bot": "leo_tx", "killers": ["Norman Invasion#50（T5）：24 条 pct=110 共 14,451,529 兵（5565~8344）", "Twój stary 69#23（T1）：2 条 1,811,467 兵（6342 一条 pct=971 1,502,402 兵）"],
         "lastDecisions": ["7756~7770：4 条 947,270 兵打 Micha（7770 是最后一条指令）", "7865~8015：31 个决策拍可用兵 −83~−55 万（影子）", "8078 / 8099 / 8337：收到 alex_k 两笔 265,850、kaito9 一笔 624,669"],
         "cause": "外盾号，全队的兵都往它这里送：全程收 17 笔 1,076 万，70 条 1,571 万兵打真人，峰值 31,194 格。7860 起 Norman 每隔几十拍一条 pct=110（最重一条 71 万兵），它密度 60~78、留底高过余额，"
                  "最后 586 拍没有一条指令，28,054→6,729 格。8337 kaito9 的协防落地时它已经顶到硬上限（6,729 格 / 1,009,350 兵），19 拍后带着 100 万兵出局（8356）。",
         "patternIds": ["NEW:R07-DF-RICH-BLEED", "NEW:R07-DN-CAP-TRUNC"]},
        {"bot": "alex_k", "killers": ["Micha [🇩🇪]#47（T1）：15 条 pct=99 共 3,285,244 兵（6335~7896）", "Player 915#24（T5）：6 条 pct=109 共 1,771,902 兵（2541~7595）；8554 pct=1023 装船，8639 带 1,802,338 兵靠在它岸上", "Player 384#29（T5）：8771 一条 1,978,802 兵"],
         "lastDecisions": ["8078 / 8099：两笔围死号的协防调度给 leo_tx（到账 265,850）", "8575：协防调度给 kaito9（到账 109,435；自己密度 57、对方 74）",
                           "8055~8640：115 个决策拍没有可打的邻居；7570~8775：105 个可用兵 ≤0（影子）"],
         "cause": "内弧号。990~1500 停在 4,105 格（留底参照队友），1500 三条打 Big Boss；5130~6030 停在 18,522 格（唯一真人邻居 Micha，密度 118~134），5 笔调度捐出 195 万。"
                  "6335 起 Micha 15 条 329 万兵、7413 起再加上 Player 915，把它从 19,038 格削到 5,025 格（8010），它 6517~7182 回了 7 条 127 万。8055 起被队友围住，按围死号的规矩每次把近四成余额捐给 leo_tx、kaito9。"
                  "8639 Player 915 的整船兵靠岸，8771 Player 384 再补一条，8786 出局。",
         "patternIds": ["NEW:R07-EC-SOLE-BUFFER-BANK", "NEW:R07-DF-PASSIVE-BLEED", "NEW:R07-DN-INVERTED"]},
        {"bot": "kaito9", "killers": ["Player 384#29（T5）：7 条 pct=150 共 16,392,024 兵（8561~8813）", "Norman Invasion#50（T5）：8 条 pct=110 共 6,170,035 兵（7399~8820）", "Micha [🇩🇪]#47（T1）：8533 一条 280,417 兵"],
         "lastDecisions": ["8337：协防调度给 leo_tx（到账 624,669，手续费 490,200）", "8365~8372：3 条 pct=47 共 944,983 兵（手续费 236,245）吃 leo_tx 留下的无主地", "8414~8449：3 条 2,195,116 兵打 Micha",
                           "8630~8790：33 个决策拍贴着只剩 3~11 万兵的 Player 915（29,523~31,510 格），留底 88×领土高过余额，零指令（影子）"],
         "cause": "全队最大的号（峰值 88,598 格）。5222~7070 当了 1,848 拍银行；7070 起才又出手（Norman 272 万、Micha 483 万、Player 915 247 万），8280 时 69,501 格 / 727 万兵。"
                  "这时 Player 384 已经吃下 Player 769 留下的地：141,313 格 / 1,682 万兵（8280），8449 再用两条 501 万收掉 Micha。8561 起他七条 pct=150 共 1,639 万兵，Norman 同时八条 617 万；"
                  "8555 时 kaito9 余额 643 万，Player 384 1,561 万、Norman 771 万（影子），261 拍从 88,566 格被打到出局（8822）。",
         "patternIds": ["NEW:R07-EC-SOLE-BUFFER-BANK", "NEW:R07-DN-CAP-TRUNC", "NEW:R07-AT-CARCASS-FLOOR"]},
    ],
    "decisions": [
        {"t": -1, "bot": "全队", "kind": "spawn", "verdict": "error",
         "state": "54 个真人位、全图 483,274 格；协调器 42 次求解，间距 70→51 像素；10 个号落在 209×183 像素里，最近队友 51~63.9 像素。990 时外面贴着 8 个敌方真人（T1 5 / T3 2 / T4 1）",
         "codePath": f"{SPVB}:L838 rCell、L1065-1077 CORNER SECTOR PHALANX（`minReqSep = clamp(round(0.95*rCell), 42, 68)`）、L1144 / L1155 / L1167（角色）、L1344-1368（指派）→ {VB}:Policy.chooseSpawn:L3983-4037",
         "why": "格距按「陆地 ÷ 真人数」算，真人越多阵型越密：十个号挤成一团、外面一圈敌方真人，圈里的内置 AI 一千拍分完（贴着 AI 的席位 1080 只剩 2 个）。T5 的十个人最近同队 107.7 像素，990~1500 多拿 69,645 格",
         "estCost": "990~1500 我方 +9,185 格，T5 +69,645 格", "patternId": "NEW:R07-SP-CLUSTER", "evidenceRef": "out/A061/spawn_truth.txt；outlet_gap.txt A；in_game.log L3 / L324"},
        {"t": 60, "bot": "全队", "kind": "expand", "verdict": "good",
         "state": "OPENING-CHECK@221 10/10 OK（单号 144~377 格）；t=540 单号中位数 1,879 格，全体真人中位数 1,833，名次中位数 22/53",
         "codePath": f"{VB}:V13.expandNeutral:L2373 `g.t < this.p.dpEnd → dpNeutral`（L2383，发令 L2406，日志 L2409）",
         "why": "按地租周期整圈吃无主地；挤成这样 540 拍时还和全场持平，73 条 [HL-OPENING] 影子逐条同拍同数。落后是 540 之后的事",
         "estCost": "—", "patternId": "NEW:R07-GOOD-OPENING-DP", "evidenceRef": "in_game.log L375；rank.txt t=540；shadow_check.txt"},
        {"t": 450, "bot": "zero_7 / ryan_m / zexos1 / sora_w / leo_tx 等", "kind": "idle", "verdict": "error",
         "state": "例：t=450 zero_7 余额 3,020，隔壁 AI#218 有 247 格 / 8 兵（每格 2.1），留底 3,322 正好是 ryan_m 的余额（影子）",
         "codePath": f"{VB}:Style.pickTarget:L1144-1177（`avail = bal − floorFor(...)`）→ V13.floorFor0:L2233-2241 → Policy.winFloor:L4562-4570 → V13.safeFinite:L2500-2510 → threatOf:L417-444（只排除目标和我，不排除队友）",
         "why": "t=300~1499 有 AI 邻居的 1,457 个决策拍零指令 1,268 个，其中 384 个（30.3%）的留底是「这个 AI 的另一个邻居——我方队友——的余额」：zero_7 77 拍、ryan_m 65、zexos1 59、sora_w 49、leo_tx 49。其中 246 拍最好的目标每格 ≤3 兵",
         "estCost": "384 个决策拍；540~990 我方打 AI 110,644 兵，其余四队 146,973~198,091", "patternId": "NEW:R07-OP-WINFLOOR-MATE", "evidenceRef": "out/A061/shadow_early.txt；side_flow_tp.txt A"},
        {"t": 882, "bot": "talon5 / noah88", "kind": "other", "verdict": "unclear",
         "state": "talon5 2,771 格 / 17,676 兵（四周只有队友，868 / 882 刚发了两条船）；noah88 4,682 格 / 17,753 兵（还贴着 AI 和无主地）。两个客户端相隔 136 毫秒报 left",
         "codePath": "不在策略代码里（客户端 / 托管层）；引擎 game.js leave L223-234：state=2，利息归零，按内置 AI 的定时器出兵",
         "why": "日志里只有 talon5 t=850 一条 26.6 ms 的慢拍，没有报错；两个号各发 40 条指令、全部被接受。离开后两个席位的 7,512 格（990）被 Player 625 等吃掉，zexos1 从此贴上 Player 625",
         "estCost": "两个席位，990 时 7,512 格（全图 1.6%）", "patternId": "NEW:R07-IO-SEAT-LOST", "evidenceRef": "in_game.log L499~L501；results.csv；out/A061/replay_ledger.txt A；death_chain.txt"},
        {"t": 1100, "bot": "alex_k / zero_7 / ryan_m / kaito9 / zexos1", "kind": "idle", "verdict": "error",
         "state": "例：t=1200 alex_k 余额 93,266，Big Boss 吃光要 66,387，留底 84,826（= 2×ryan_m 的 42,413），可用 8,440；t=1200 zexos1 余额 101,903（密度 45.7），Player 625 9,557 格 / 75,222 兵，过了留底但 0.746×51,365 < 148,412，一个兵不发（影子）",
         "codePath": f"{VB}:Style.pickTarget:L1152-1165 → V13.allow:L2110-2119 → V13.floorFor0:L2233-2241（L2240 `P.preyFloor * f`）→ General.floors:L819-831 → General.defenseNeed:L899-913 → General.altOf:L918-941；V13.amount0:L2347-2349（一次吃不光就返回 0）",
         "why": "没有 AI 邻居、也没有无主地的 525 个决策拍只发了 5 条。alex_k 113 拍 0 条（84 拍卡在队友余额的 2 倍）、zexos1 101 拍 0 条（51 拍一次吃不光、50 拍四周只有队友）、ryan_m 88 拍 1 条、kaito9 85 拍 0 条、zero_7 70 拍 0 条。"
                "贴着的 Big Boss 全程密度 3~5",
         "estCost": "六个号 500 拍 +2,533 格，余额 17.5 万→95.9 万", "patternId": "NEW:R07-OP-PREY-FLOOR", "evidenceRef": "out/A061/shadow_early_humans.txt；bot_share_frozen6.txt；truth_all.tsv"},
        {"t": 1500, "bot": "zero_7 / alex_k / zexos1", "kind": "attack", "verdict": "error",
         "state": "zero_7 3,545 格 / 197,318 兵（密度 55.7）：Big Boss 10,972 格 / 85,390 兵，need=168,654，safe=122,812，avail=72,194。1500 / 1505 / 1510 三个决策拍各发一条 pct=374（影子）",
         "codePath": f"{VB}:V17.act:L2690-2693 → Policy.act:L4942 → Policy.buyLand:L5444 / L5446、L5611-5616（`x = min(avail, want)`；没有「上一条还在路上」的判断）→ Policy.send:L3838-3925",
         "why": "每一条单独看都留够了 safe，但指令 12 拍后才落地、带的是比例：三条落地后（1512 / 1519 / 1526）zero_7 剩 49,677（留底的 40%），alex_k 剩 37,512，zexos1 剩 32,724。三个号 14 拍打出 545,192 兵，"
                "Big Boss 一个人挨了 339,248（所需约 171,916）。zero_7 110 拍后被 Eyup、Yolo 压上来",
         "estCost": "545,192 兵 + 手续费；zero_7 出局", "patternId": "NEW:R07-AT-INFLIGHT-REPEAT", "evidenceRef": "out/A061/watch_bigboss.txt；shadow_trace_zero_7_1400_1980.txt；repeat_sends.txt"},
        {"t": 1635, "bot": "kaito9", "kind": "attack", "verdict": "good",
         "state": "7,727 格 / 277,562 兵（密度 35.9）。1631 HD.MAX pct=1023 把 217,769 兵全压到 JM LEPEN 身上，家里 10,402 格 / 0 兵：每格成本 1.4 对出价 53.2，need=15,604，avail=184,203（影子）",
         "codePath": f"{VB}:Policy.offers:L5238-5310 → Policy.buyLand:L5359（c < worth）、L5595-5608 脉冲（发令 L5607）",
         "why": "对方梭哈后 4 拍就出手：1645~1652 三条 pct=69~70 共 54,334 兵（手续费 9,269），7,727→16,234 格，每格 6.4 兵；HD.MAX 1793 出局。这是 kaito9 后来成为最大号的起点",
         "estCost": "54,334 兵换 8,507 格", "patternId": "NEW:R07-GOOD-SAVED-PUSH", "evidenceRef": "out/A061/shadow_trace_kaito9_1400_2900.txt t=1635；pair_cmds_tp2.txt；humans_cmd.tsv t=1631"},
        {"t": 1652, "bot": "kaito9", "kind": "keep", "verdict": "unclear",
         "state": "16,234 格。t=1900 余额 395,070（密度 24.3），出价 35.0：Kalmar 26,928 格 / 57 万兵每格 52.5，JM LEPEN 59.6，Yolo 64.0。t=2700 余额 1,313,745（密度 80.9），出价 72.8（影子）",
         "codePath": f"{VB}:Policy.buyLand:L5350-5353（`worth = m × 自己的密度`，m 1.48→0.9）、L5359 `if (c >= worth && c >= cheap && !over) break`",
         "why": "1652~2870 没有一条指令，256 个决策拍价高，余额 22 万→163 万。攒下的兵后来换成了地（2870 起），但这 1,218 拍里旁边四个号被打光，其中 ryan_m 就死在它的邻居 Yolo 手里。"
                "早打 Yolo 值不值看不清：Yolo 1900 时 9,392 格 / 24.6 万兵（密度 26）、2860 时 11,316 格 / 66 万兵（密度 59），每格成本一直高于 kaito9 的出价",
         "estCost": "1,218 拍没有指令", "patternId": "NEW:R07-EC-IDLE-RICH", "evidenceRef": "out/A061/shadow_trace_kaito9_1400_2900.txt；troop_flow_tp.txt B；pair_cmds_tp2.txt"},
        {"t": 2079, "bot": "riku_x", "kind": "attack", "verdict": "error",
         "state": "7,139 格 / 150,849 兵（密度 21）。此前几个决策拍发出的五条在 2079 同一拍落地（Player 625 一条、Micha 两条、无主地两条空单），余额→98,710；2086~2107 再落地 6 条",
         "codePath": f"执行层（指令延迟中位数 32 拍）；{VB}:Policy.act:L4941 expandNeutral + L4942 buyLand、Policy.buyLand:L5595-5608（在途的兵不算已有进攻）",
         "why": "延迟比别的号长 20 拍，每个决策拍照旧再发一条，落地时成批：2079~2107 九条 102,814 兵（手续费 10,027），密度从 21 掉到 6（2160）；2429 Player 775 一条 pct=301（79,071 兵）压上来。全场它想发 62 条、落地 56 条",
         "estCost": "余额 150,849→52,876（2160）", "patternId": "NEW:R07-IO-LAG-BATCH", "evidenceRef": "out/A061/same_tick_batches.txt；cmd_loss.txt；death_chain.txt"},
        {"t": 2250, "bot": "ryan_m", "kind": "donate", "verdict": "unclear",
         "state": "ryan_m 1,852 格 / 201,796 兵（密度 109）——1500~2700 唯一过了协防线的一拍。候选里 leo_tx 得分 7,537、sora_w 7,424（影子）；leo_tx 14,251 格（2160）/ 密度 21，正被 Player 171 打；sora_w 4,735 格 / 密度 16（2220），正被 Player 915 打",
         "codePath": f"{VB}:Policy.tryDonateToTeammate:L4463-4473 Case A（`score = 5000 + (inHumanAtk / Bp) * 1200 + (105 - dAlly) * 20 + Math.min(2200, Lp / 18)`）、L4500-4508",
         "why": "得分里领土大的收方多加分，113 分之差给了 leo_tx：到账 39,163、手续费 12,723。sora_w 270 拍后出局；但 3.9 万兵给谁都改变不了什么",
         "estCost": "到账 39,163 + 手续费 12,723", "patternId": "NEW:R07-DN-NO-DONOR", "evidenceRef": "in_game.log L627；out/A061/shadow_donor_gate.tsv t=2250；help_table.txt C"},
        {"t": 2870, "bot": "kaito9", "kind": "attack", "verdict": "good",
         "state": "t=2860 余额 1,630,307、16,234 格（密度 100.4，刚过软上限）：Yolo 11,316 格 / 66 万兵，每格成本 141.1 对出价 90.4。之后 2870~5222 共 32 条",
         "codePath": f"{VB}:Policy.buyLand:L5353 over、L5440-5443（过软上限后的留底封顶 0.9×100×领土）、L5449-5453（离开的席位，发令 L5453）、L5574-5586（t≥3800 对濒死 / 失血目标的脉冲，发令 L5585）、L5595-5608（发令 L5607）",
         "why": "7,363,962 兵（手续费 826,957）换来 16,234→46,253 格：Yolo、Eyup、JM LEPEN 三个真人出局，Kalmar 离开后的 22,220 格两条吃下。贵（连手续费每格约 273 兵），但全队 9.4%→18.6% 主要靠这一串",
         "estCost": "7,363,962 兵 + 手续费 826,957，+30,019 格", "patternId": "NEW:R07-GOOD-SAVED-PUSH", "evidenceRef": "out/A061/pair_cmds_mid.txt；shadow_trace_kaito9_2850_5300.txt；side_flow_tp.txt F"},
        {"t": 4809, "bot": "kaito9", "kind": "attack", "verdict": "good",
         "state": "t=4795 Eyup（9,489 格）pct=1023 把 1,216,346 兵全压到 kaito9 身上。t=4800 kaito9 37,673 格 / 223 万兵：Eyup 家里 9,490 兵，need=1,229,851（含压在我身上的兵），avail=523,489（影子）",
         "codePath": f"{VB}:Policy.offers:L5238-5310（onMe / nearCollapse / bleeding）→ Policy.buyLand:L5574-5586（发令 L5585）",
         "why": "连续六个决策拍各一条 pct=122（4809~4837 落地，1,142,950 兵 + 手续费 111,504）：Eyup 的进攻槽 1,202,092→868,936→566,514→295,493→0，kaito9 只丢约 330 格，随后吃到 43,258 格（4960），Eyup 5010 出局。"
                "72_repeat_sends.py 把这一组标成多发 1,111,277，是没算对方压上来的兵",
         "estCost": "1,142,950 兵 + 手续费 111,504", "patternId": "NEW:R07-GOOD-COUNTER-ALLIN", "evidenceRef": "out/A061/watch_eyup_allin.txt；shadow_trace_kaito9_2850_5300.txt t=4800~4835"},
        {"t": 5470, "bot": "kaito9 / alex_k", "kind": "keep", "verdict": "error",
         "state": "kaito9 46,319 格、余额 380~526 万（密度 82~114），唯一的真人邻居 Norman（密度 101~127，每格成本 332~449 对出价约 100）；alex_k 18,522 格，唯一邻居 Micha（密度 118~134）",
         "codePath": f"{VB}:Policy.buyLand:L5361-5365（`B < P.overHumanCap * 100 * L → continue`）、L5440-5443（`isSoleHealthyBuffer ? P.overHumanKeep : P.hold`）",
         "why": "闸要余额 ≥593 万、留底 519 万；kaito9 的余额峰值 526 万——因为密度一到 108~114 调度就削走两成。118 个决策拍卡在这里，5222~7070 之间一条进攻没有，46,319 格不动；alex_k 90 拍。"
                "7060 Micha 贴上来成了第二个邻居，闸当拍松开",
         "estCost": "1,848 拍没有进攻；同期利息地租 1,208 万", "patternId": "NEW:R07-EC-SOLE-BUFFER-BANK", "evidenceRef": "out/A061/shadow_trace_kaito9_5300_7100.txt；shadow_trace_alex_k_5300_6600.txt；troop_flow_tp.txt B"},
        {"t": 5550, "bot": "kaito9 / alex_k", "kind": "donate", "verdict": "error",
         "state": "kaito9 每次余额到 499~526 万（密度 108~114）发一笔：5558、5712、5908、6111、6307、6510、6734、6958 共 8 笔 pct=187~224；alex_k 5 笔。收方 leo_tx 当时密度 55~94",
         "codePath": f"{VB}:Policy.tryDonateToTeammate:L4418（收方密度 <115 就行）、L4463-4473 Case A（`dMe < dAlly + 16 → continue`）、L4474-4495 Case B、L4500-4508",
         "why": "13 笔到账 10,149,930、手续费 3,236,999（费 / 到账 0.32）。5908 / 6111 / 6307 三笔落地后 leo_tx 密度 121~133，利率从 137~139 掉到 48~83，两边每 10 拍利息合计 −48,382；"
                "leo_tx 过了软上限就不比价地打 Norman。同场 T5 的捐方整笔全捐（pct=1023），费 / 到账 0.067",
         "estCost": "手续费 3,236,999（同期全队利息地租的 15.4%）", "patternId": "NEW:R07-DN-IDLE-RECV", "evidenceRef": "out/A061/donation_yield.txt B；replay_ledger.txt B；pair_cmds_tp3.txt"},
        {"t": 5418, "bot": "leo_tx", "kind": "attack", "verdict": "error",
         "state": "leo_tx 22,474~31,194 格，靠调度维持在密度 55~133。Norman 39,117 格 / 399 万兵（密度 101~127），每格成本是 leo_tx 出价的 1.07~3.53 倍（影子）",
         "codePath": f"{VB}:Policy.buyLand:L5353 `over = P.surplus > 0 && B > 100 * L`、L5359（over 时不停）、L5440-5443、L5595-5608（一条约 12% 余额）",
         "why": "影子里这一段出手 40 拍全部是过软上限时发的。20 条 5,830,535 兵（手续费 582,708）打 Norman，对方 12 条 6,751,845 打回来、还收了队友 5 笔 237 万；Norman 的领土不降反升。leo_tx 这一段只多 7,152 格",
         "estCost": "5,830,535 兵 + 手续费 582,708", "patternId": "NEW:R07-AT-OVER-BURN", "evidenceRef": "out/A061/shadow_trace_leo_tx_5300_7100.txt；pair_cmds_tp3.txt；side_flow_tp.txt D"},
        {"t": 6345, "bot": "leo_tx", "kind": "keep", "verdict": "error",
         "state": "6342 Twój stary pct=971 把 150 万兵压到 leo_tx 身上，家里 17,376~22,484 格 / 6~8 万兵（每格成本 11.4~41.8，leo_tx 出价 67~89）。leo_tx 余额 157~211 万（密度 64~71），safe 210~253 万，avail −61~−42 万（影子）",
         "codePath": f"{VB}:Policy.buyLand:L5414-5418、L5444 `keep = Math.max(keep, safe)` → Policy.safeAt:L4543-4560（`s = Math.min(s, P.oppFloorCap * L)`）→ V17.safeAt:L2728-2738 → V13.dpKeep:L2459-2464",
         "why": "留底按最强的真人邻居（Norman 450 万兵）算、封顶 88×自己的领土，和要打的是谁无关：34 个决策拍发不出指令。6510 kaito9 的 105 万到账、密度到 114.5 才发出一条——6531 落地，21 万兵 150 拍换回 6,397 格（23,237→29,634）。"
                "被卡的 165 拍里 Norman 6329 靠岸的 477,511 兵在收地：6300→6840 Twój stary 17,444→0，Norman +17,793 格，leo_tx −1,547 格。把 Twój stary 从 219 万兵磨光的是 leo_tx 一个人（15 条 3,818,471 兵）",
         "estCost": "约 1.7 万格（全图 3.6%）到了 Norman 手里", "patternId": "NEW:R07-AT-CARCASS-FLOOR", "evidenceRef": "out/A061/trace_blocked_leo_tx_5300_7100.txt；watch_norman_boat.txt；truth_all.tsv"},
        {"t": 5775, "bot": "kaito9 / alex_k", "kind": "donate", "verdict": "error",
         "state": "Player 769（T2，不是我方号）5775~7014 14 条 4,514,871 兵打 Player 384（6030 时密度 21），另打 Player 915、Player 937；自己密度 43~72。同时 kaito9 密度 108~114、每 200 拍捐一笔给 leo_tx",
         "codePath": f"{VB}:Policy.tryDonateToTeammate:L4414 → isOurSquadBot:L3960-3972 / isBossNpl:L3932-3951；引擎 game.js donate L404-416（同队即可）、donationFree L360-362（t ≥ 4284）",
         "why": "这一段 T2 真正在换地的是他：32,127→91,479 格，每格 106~160 兵；我方 14 笔 1,021 万里 13 笔 983 万给了每格要花上千兵的 leo_tx。他全场收捐 0 笔，7567 之后独自崩掉。引擎不拦，拦的是收方名单",
         "estCost": "同期我方 +1,680 格，Player 769 +59,352 格", "patternId": "NEW:R07-EG-SQUAD-ONLY-RECV", "evidenceRef": "out/A061/pair_cmds_p769.txt；pair_cmds_tp3.txt；side_flow_tp.txt A / D"},
        {"t": 7658, "bot": "kaito9", "kind": "attack", "verdict": "unclear",
         "state": "7650 kaito9 53,064 格 / 536 万兵（密度 101）。邻居：Norman（T5，53,817 格）、Micha（T1 最后一个号，7658 时 24,790 格 / 215 万兵）。Player 769 正被 T5 分食",
         "codePath": f"{VB}:Policy.offers:L5238-5310（按每格成本排序）→ Policy.buyLand:L5353 over、L5595-5608（发令 L5607）",
         "why": "7658~8449 八条 4,830,072 兵（手续费 543,227）打 Micha，6 条 2,469,888 打 Player 915：53,064→69,501 格（8280）。地是长了，但 Micha 最后被 Player 384 两条 501 万收走；"
                "同一段 Player 384 93,934→141,313 格、余额 800 万→1,682 万，kaito9 没有一条打在他身上（不接壤）",
         "estCost": "7,299,960 兵，+16,437 格", "patternId": "NEW:R07-EG-WRONG-FRONT", "evidenceRef": "out/A061/pair_cmds_tp3.txt；rank.txt t=7650 / 8280；front_width.txt"},
        {"t": 8325, "bot": "kaito9", "kind": "donate", "verdict": "error",
         "state": "kaito9 69,501 格 / 7,747,144 兵（密度 111）；leo_tx 决策拍密度 59，落地时（8337）6,729 格 / 384,681 兵，硬上限 1,009,350",
         "codePath": f"{VB}:Policy.tryDonateToTeammate:L4418（只看收方密度）、L4455-4457（弃子 / underFire）、L4463-4473、L4500-4508；引擎 game.js transfer L388-400（到账封顶在 150×收方领土，手续费按捐方全部余额）",
         "why": "名义 1,654,426，到账 624,669，手续费 490,200（费 / 到账 0.785）；leo_tx 19 拍后带着 100 万兵出局。调度不看收方离硬上限还有多少空间，也不看它 12 拍后还剩多少地（8260→8350 从 12,586 格掉到 6,729 格）",
         "estCost": "手续费 490,200；到账的 624,669 随 leo_tx 一起没了", "patternId": "NEW:R07-DN-CAP-TRUNC", "evidenceRef": "in_game.log L903 / L904；out/A061/replay_ledger.txt B；donation_yield.txt B"},
        {"t": 8630, "bot": "kaito9", "kind": "keep", "verdict": "error",
         "state": "8554 Player 915 pct=1023 把 2,125,831 兵全装船去打 alex_k；8630 起它贴着 kaito9：29,523~31,510 格 / 3~11 万兵，每格成本 5.5~14.7，吃光要 92,558~239,504。kaito9 余额 242~635 万（密度 68~86）",
         "codePath": f"{VB}:Policy.buyLand:L5414-5418、L5444 → Policy.safeAt:L4543-4560（`s = Math.min(s, P.oppFloorCap * L)`）→ V17.safeAt:L2728-2738 → V13.dpKeep:L2459-2464",
         "why": "留底被 Player 384（1,600 万兵）顶到 88×领土 = 313~740 万，高过余额：33 个决策拍 avail −132~−18 万，一条没发。吃光那 3 万格（全图 6%）只要 9~24 万兵（影子的 need）；alex_k 同一段 27 拍也是这样。"
                "当时 kaito9 正挨 Player 384 的 1,639 万，结局不会变",
         "estCost": "约 3 万格没有去拿", "patternId": "NEW:R07-AT-CARCASS-FLOOR", "evidenceRef": "out/A061/trace_blocked_kaito9_7100_8822.txt；watch_p915_empty.txt；trace_blocked_alex_k_6600_8786.txt"},
    ],
    "newPatterns": [
        np("R07-SP-CLUSTER", [{"t": -1, "bot": "全队"}], "A061：10 个号最近队友 51~63.9 像素（中位 55.4），T5 107.7；T1 的 11 个真人在同一片；没有重叠"),
        np("R07-GOOD-OPENING-DP", [{"t": 60, "bot": "全队"}], "A061：10/10 OK；t=540 名次中位数 22/53（持平）"),
        np("R07-OP-AI-RACE", [{"t": 540, "bot": "全队"}, {"t": 990, "bot": "全队"}], "A061：540~990 我方打 AI 110,644 兵，其余四队 146,973~198,091；990~1500 我方 101,088 / +9,185 格，T5 483,340 / +69,645 格"),
        np("R07-OP-WINFLOOR-MATE", [{"t": 450, "bot": "zero_7"}], "A061（影子）：1,457 个有 AI 邻居的决策拍，零指令 1,268，参照我方队友的 safeFinite 384（zero_7 77、ryan_m 65、zexos1 59、sora_w 49、leo_tx 49）"),
        np("R07-OP-PREY-FLOOR", [{"t": 1100, "bot": "alex_k"}, {"t": 1200, "bot": "zexos1"}, {"t": 1400, "bot": "zero_7"}, {"t": 1400, "bot": "kaito9"}, {"t": 1200, "bot": "ryan_m"}],
           "A061（影子）：525 个决策拍只发 5 条；留底参照队友 142、价格留底 101、keepCap 81、一次吃不光 69；六个号 990~1440 +2,533 格、余额 17.5 万→95.9 万"),
        np("R07-OP-BOXED-EARLY", [{"t": 990, "bot": "zexos1"}, {"t": 850, "bot": "talon5"}], "A061：zexos1 t=990 四周全是队友（2,231 格，密度 19.8）；talon5 850~900 的 11 个决策拍没有 AI 邻居也没有无主地"),
        np("R07-IO-SEAT-LOST", [{"t": 882, "bot": "talon5"}, {"t": 882, "bot": "noah88"}], "A061：两个席位同时离开（相隔 136 毫秒），当时 2,771 / 4,682 格"),
        np("R07-SE-BOAT-MATE-SHORE", [{"t": 868, "bot": "talon5"}, {"t": 882, "bot": "talon5"}], "A061：talon5 两条船靠在 sora_w 岸上，到账 5,155，没有被拒"),
        np("R07-AT-INFLIGHT-REPEAT", [{"t": 1500, "bot": "zero_7"}, {"t": 1500, "bot": "alex_k"}, {"t": 1500, "bot": "zexos1"}, {"t": 3843, "bot": "zexos1"}, {"t": 7924, "bot": "kaito9"}, {"t": 8365, "bot": "kaito9"}],
           "A061：463 条生效的进攻里 346 条在连发组里；对真人 69 组 214 条，第 2 条起 22,345,889 兵 / 手续费 2,446,852；1512~1526 三个号各三条是余额的 74%~84%"),
        np("R07-DF-SPENT-THEN-HIT", [{"t": 1610, "bot": "zero_7"}, {"t": 2590, "bot": "ryan_m"}, {"t": 2429, "bot": "riku_x"}], "A061：zero_7 三条后密度 14，84 拍后被 Eyup / Yolo 打；ryan_m 2443 出手后 140 拍被 pct=321 打"),
        np("R07-GOOD-SAVED-PUSH", [{"t": 1635, "bot": "kaito9"}, {"t": 4704, "bot": "kaito9"}, {"t": 2870, "bot": "kaito9"}], "A061：kaito9 54,334 兵吃 HD.MAX 8,507 格；2870~5222 16,234→46,253 格；42_patterns 共 7 个窗口 29,206 格"),
        np("R07-GOOD-COUNTER-ALLIN", [{"t": 4809, "bot": "kaito9"}], "A061：Eyup 梭哈 1,202,092 兵，kaito9 六条 1,142,950 兵磨光，只丢约 330 格"),
        np("R07-EC-IDLE-RICH", [{"t": 1652, "bot": "kaito9"}, {"t": 5310, "bot": "kaito9"}], "A061：152 个窗口；kaito9 1652~2870 和 5222~7070 两段没有进攻"),
        np("R07-MT-PRE2400-HOLD", [{"t": 1620, "bot": "全队"}], "A061：无主地吃完（1620）到 2400，份额 10.33%→11.68%；有敌邻的 56 个窗口里 46 个不出手"),
        np("R07-IO-LAG-BATCH", [{"t": 2079, "bot": "riku_x"}, {"t": 987, "bot": "riku_x"}], "A061：riku_x 延迟中位数 32 拍，24 条晚到 ≥35 拍；全场同拍 ≥3 条的批 12 个 49 条"),
        np("R07-IO-ONE-CMD-DROP", [{"t": 1515, "bot": "riku_x"}, {"t": 460, "bot": "kaito9"}], "A061（影子）：8 个双指令拍，影子比录像多 8 条"),
        np("R07-MT-NOFULL-LOCK", [{"t": 1535, "bot": "riku_x"}, {"t": 477, "bot": "leo_tx"}], "A061（影子）：8/10 个号被锁上，挡掉 23 次出兵，riku_x 5 次换成 1 兵试探"),
        np("R07-DN-NO-DONOR", [{"t": 1610, "bot": "zero_7"}, {"t": 2250, "bot": "ryan_m"}, {"t": 4445, "bot": "zexos1"}], "A061：1500~4065 只有一条调度日志；五个号出局前收捐 0 笔"),
        np("R07-DF-PASSIVE-BLEED", [{"t": 1722, "bot": "sora_w"}, {"t": 6335, "bot": "alex_k"}, {"t": 7860, "bot": "leo_tx"}], "A061：51 个窗口 132,710 格"),
        np("R07-DF-RICH-BLEED", [{"t": 7860, "bot": "leo_tx"}, {"t": 4445, "bot": "zexos1"}], "A061：34 个窗口 114,159 格"),
        np("R07-DF-DOOMED-SKIP", [{"t": 4635, "bot": "zexos1"}, {"t": 1730, "bot": "zero_7"}], "A061（影子）：zexos1 24 个决策拍被判弃子（分支 B），zero_7 19 个（分支 A）"),
        np("R07-AT-OVER-BURN", [{"t": 2443, "bot": "ryan_m"}, {"t": 5418, "bot": "leo_tx"}, {"t": 7340, "bot": "kaito9"}], "A061（影子）：leo_tx 5300~7100 出手 40 拍全是过软上限时发的，约 1,298 万兵 c ≥ worth"),
        np("R07-EC-SOLE-BUFFER-BANK", [{"t": 5470, "bot": "kaito9"}, {"t": 5320, "bot": "alex_k"}, {"t": 5390, "bot": "zexos1"}, {"t": 8260, "bot": "kaito9"}],
           "A061（影子）：kaito9 118 + 15 拍、alex_k 90 + 9 拍、zexos1 36 拍；kaito9 5222~7070 0 条进攻、8 笔捐款 820 万、手续费 258 万"),
        np("R07-DN-IDLE-RECV", [{"t": 5908, "bot": "kaito9"}, {"t": 6111, "bot": "kaito9"}, {"t": 6307, "bot": "kaito9"}], "A061：收方密度 ≥60 的 18 笔 10,516,217（手续费 3,290,714）；5 笔协防落地后收方过软上限"),
        np("R07-DN-TAX51", [{"t": 5558, "bot": "kaito9"}], "A061：21 笔到账 11,690,718、手续费 3,973,417（0.340）；T5 35 笔 0.185"),
        np("R07-AT-CARCASS-FLOOR", [{"t": 6345, "bot": "leo_tx"}, {"t": 8630, "bot": "kaito9"}, {"t": 8645, "bot": "alex_k"}],
           "A061（影子）：leo_tx 34 拍对 Twój stary（1.7~2.2 万格 / 6~8 万兵），kaito9 33 拍、alex_k 27 拍对 Player 915（3 万格 / 3~11 万兵）；safe ÷ 自己的领土 = 84~88"),
        np("R07-EG-SQUAD-ONLY-RECV", [{"t": 5775, "bot": "kaito9"}], "A061：Player 769 5310~7020 +59,352 格、全场收捐 0 笔；我方同期 14 笔 1,021 万都在我方号之间"),
        np("R07-EG-WRONG-FRONT", [{"t": 7658, "bot": "kaito9"}], "A061：kaito9 483 万打 T1 的 Micha，同一段 Player 384 吃下 Player 769 的地"),
        np("R07-DN-CAP-TRUNC", [{"t": 8337, "bot": "kaito9"}], "A061：1 笔，名义 1,654,426、到账 624,669、手续费 490,200"),
        np("R07-DN-DEAD-RECV", [{"t": 8065, "bot": "alex_k"}, {"t": 8090, "bot": "alex_k"}, {"t": 6725, "bot": "kaito9"}], "A061：5 笔 1,557,467（手续费 401,370）；另有 8337 那一笔 19 拍后收方出局"),
        np("R07-DN-INVERTED", [{"t": 8090, "bot": "alex_k"}, {"t": 8565, "bot": "alex_k"}], "A061：2 笔 206,379"),
        np("R07-EC-SOFTCAP", [{"t": 2860, "bot": "kaito9"}], "A061：32 个快照；alex_k 800 拍、kaito9 950 拍在软上限以上"),
    ],
    "lossArchetype": "outscaled",
    "winnerNotes": "T5 获胜（8820 拍时 95.3%）。①站位：10 个真人出生时最近同队 107.7 像素（我方 55.4），每个人都有一圈内置 AI 可吃——990~1500 往 AI 身上发了 483,340 兵（87 条），+69,645 格，1530 时 26.9%，其他四队 13.4%~18.6%。"
                   "②分工：Player 559（峰值 9,382 格）全场没有打过一个在位真人，14 笔把 405 万兵捐出去（11 笔 342 万给 Norman）；Player 797（峰值 13,524 格）1974 之后只捐不打，19 笔 191 万（16 笔给 Player 384）；Player 937 两笔 pct=1023 把 73 万全给了 Player 384。"
                   "T5 这三个捐方 35 笔的手续费是捐出额的 18.5%（我方 34.0%）。③Player 384 专吃残局——5310~7020 打 black magic 离开后的席位 7 条 132 万兵，"
                   "全程利息地租 52,492,679（kaito9 36,171,313）、发船费 2,826,841。7650 之后吃下 Player 769 留的地（93,934→141,313 格），8449 两条 501 万收掉 Micha，8561 起七条 pct=150 共 1,639 万打死 kaito9。"
                   "④T5 也有浪费：dih 4050~6840 一直顶在密度 146~150，6030 时全队加权利率只有 64，5310~7020 的利息进账还不如 T2。它赢在 1530 之前拿到的地，和最后 1,300 拍 T2 一侧自己塌了。",
    "wentWell": [
        "开局 10/10 通过检查，出生没有重叠；全场 0 条策略报错；配额记账 23 笔 0 笔被拒，没有来回倒手",
        "kaito9 两次抓住对方梭哈：1635 HD.MAX 的空壳，三条 54,334 兵吃下 8,507 格；4795 Eyup 压上来，六条脉冲磨光对方、只丢约 330 格",
        "2700~5310 四个号从 9.40% 打到 18.62%：Big Boss、Yolo、Eyup、JM LEPEN、Twój stary 挨的兵 75%~100% 来自我方，Player 625 53%",
        "5310~7020 我方三个号加 Player 769 的利息进账超过 T5（3,228 万对 2,962 万）——兵是够的",
    ],
    "unknowns": [
        "talon5、noah88 两个客户端为什么在 882 同时离开（相隔 136 毫秒）：日志里没有报错，只有 talon5 t=850 一条 26.6 ms 的慢拍",
        "riku_x 的指令为什么比别的号晚 20 拍（延迟中位数 32 对 10~18）；6 条没落地的是没发出去还是被丢了：桥接层不在本包里",
        "Player 769 为什么在 7567 / 7658 两次把全部余额压出去（人的操作）；他不这样做 T2 能撑多久",
        "kaito9 在 5310~7020 如果自己打 Norman（密度 101~127、背后有两个捐方）会换来多少地：没法重演",
        "十个号如果像 T5 那样分开出生，990~1500 能多拿多少：没有可对照的站位",
        "协调器 42 次求解里点位改了很多次（第一次给 ryan_m 的是 (721,1063)，最后是 (881,972)）：为什么改，日志里只有结果",
        "真号内存里的 isNoFullSend 是否和影子一致（标记不进日志）",
    ],
    "mechanicsQuestions": [
        "一条进攻指令带的是比例（pct/1024），落地那一拍按当时的余额执行，另按全部余额收 12/1024。相邻三个决策拍各发一条同比例的指令，落地后剩 (1 − p − 1.17%)³：zero_7 三条 pct=374 是 201,816→125,544→78,098→49,677。",
        "压在进攻槽里的兵不算家里的防守，也不吃利息；两个玩家互相打时双方进攻槽里的兵先对消——kaito9 六条脉冲 114 万把 Eyup 压上来的 120 万磨光，自己只丢约 330 格。",
        "捐款手续费按捐方全部余额的 64/1024 收，和捐多少无关：捐两成余额时手续费约是到账的三分之一，全捐（pct=1023）时是 6.7%。Player 937、Player 559 就是整笔全捐（6622 一笔到账 972,726、手续费 64,848）。",
        "利率只看个人领土份额，过软上限后按超出部分扣减：6030 时 T5 七个人 1,637 万兵的加权利率只有 64（dih 密度 146、Player 915 132、Norman 127），我方三个号 871 万兵是 136，每 10 拍利息 118,800 对 105,046。",
        "离开的席位（state=2）不再生息，由内置 AI 的定时器出兵；它的地谁吃到算谁的：black magic 的席位被 Player 384 用 7 条 132 万兵吃掉，Kalmar 的 22,220 格被 kaito9 两条 113 万吃掉。",
        "船靠在敌人岸上直接变成一条进攻，不需要接壤：Norman 6202 的船 6329 带 477,511 兵落在 Twój stary 身上；Player 915 8554 的船 8639 带 1,802,338 兵落在 alex_k 身上。发船费 32/1024。",
        "一个号出局后剩下的地变成无主地：leo_tx 8356 出局，kaito9 8365~8372 三条 pct=47 去吃（944,983 兵，各付 7.4~8.3 万手续费）。",
    ],
    "drop30Notes": {
        "zero_7@1440": "1512 / 1519 / 1526 三条 pct=374 打 Big Boss（149,125 兵 + 费 4,771）：同一个决策在三个决策拍各发一次，余额 201,816→49,677，自己算的留底是 122,812",
        "alex_k@1440": "1512 ×2 / 1519 三条 pct=453~454 打 Big Boss（190,123 兵）：余额 232,654→37,512",
        "zexos1@1440": "1512 / 1519 ×2 三条 pct=486~487 打 Player 625（205,944 兵）：余额 243,737→32,724",
        "riku_x@2070": "2079 一拍落地 5 条（延迟中位数 32 拍），到 2107 共 9 条 102,814 兵 + 费 10,027 打 Player 625（73,427）/ Micha（29,387）",
        "kaito9@4770": "4795 Eyup 梭哈 1,202,092 兵压上来；4809~4837 六条 pct=122 共 1,142,950 兵 + 费 111,504 反打（对的），挨打掉 121,936 兵；领土 35,861→38,784",
        "leo_tx@6120": "过软上限后的脉冲：5 条 1,661,701 兵 + 费 162,116（Norman 1,410,981、Twój stary 250,720）；领土 27,059→29,258。此前 6097 / 6111 刚收到 alex_k、kaito9 两笔 1,472,075",
        "kaito9@7920": "7924 一拍落地三条 pct=122 打 Player 915（1,450,259 兵 + 费 141,487）；窗口内 4 条 1,817,848 兵 + 费 177,349，59,914→68,402 格",
        "kaito9@8730": "8561 起 Player 384 七条 pct=150 共 16,392,024 兵、Norman 八条；窗口内挨打掉 4,420,317 兵（Player 384 进攻槽峰值 6,347,320），59,698→21,192 格",
    },
    "mechanismChecks": {
        "1_quotaRejections": "没有拒绝。引擎记账 23 笔（21 笔调度 + 2 条靠在队友岸上的船），0 笔被拒；21 条 [HL-DISPATCH] 全部执行（到账 11,690,718）。配额期（t<4284）只有 3 笔 476,362 兵 / 49 点；其余 18 笔在免检期。"
                             "1500~4065 之间只有 2250 一条调度日志——不是配额拦的，是捐方密度够不着 102 / 108。",
        "2_donationTax": "证实，而且集中在停滞的那一段。全程 21 笔到账 11,690,718、手续费 3,973,417（费 / 到账 0.340），占全程利息地租 63,871,444 的 6.2%；三种手续费合计 8,646,354（13.5%）。"
                         "5310~7020 一段 14 笔到账 10,214,402、手续费 3,259,183，是同期利息地租 20,969,950 的 15.5%（5400~6480 一档三种手续费占 24.0%）。同场 T5 三个捐方 35 笔 6,691,395、手续费 1,235,553（0.185）。",
        "3_inlandStagnation": "证实，但不是被队友围死的那种：990~1500 六个号贴着敌方真人却不长地（22,455→24,988 格），拿着全队 82%~89% 的余额；5222~7070 kaito9 46,319 格不动、余额 380~526 万。"
                              "围死且高密度的快照 0 个；顶到硬上限只有 leo_tx 死前 20 拍；软上限以上 kaito9 950 拍、alex_k 800 拍、zexos1 440 拍、leo_tx 400 拍、ryan_m 110 拍（32 个快照）。",
        "4_spawnOpening": "Vb 协调器的角落扇形阵：42 次求解、间距 70→51 像素；10 个号最近队友 51~63.9 像素，没有重叠。990 时外面贴着 8 个敌方真人（T1 5 / T3 2 / T4 1，T5 没有）。开局 10/10 OK、540 拍名次中位数 22/53；"
                          "之后圈里的 AI 一千拍分完，990 名次中位数 39/48、1530 是 38/46。",
        "5_frontlineFloors": "本局没有领先期。和留底有关的四件事：①t<1500 对贴身真人的猎杀规则 + 以队友余额为准的 defenseNeed（525 个决策拍只发 5 条）；②1500 那一拍连发三条把余额打穿自己的留底；"
                             "③「唯一真人邻居」闸把过软上限后的留底从 0.9 抬到 1.12×100×领土（kaito9 133 拍、alex_k 99 拍、zexos1 36 拍）；④对真人的留底顶在 88×领土，贴着空壳也发不出指令（leo_tx 34 拍、kaito9 33 拍、alex_k 27 拍）。",
        "6_teamSplit": "没有分队：10 个号全在 T2。T2 另有一个真人 Player 769，全程和我方号不接壤、没有捐款往来；5310~7020 他一个人打 T5（21 条 676 万兵，+59,352 格），7567 / 7658 两次梭哈后被吃光。",
        "7_lagBatches": "有，集中在 riku_x：想发 62 条、收下 56 条，延迟中位数 32 拍（90 分位 50、最大 64），24 条晚到 ≥35 拍；其余号中位数 10~18 拍。同一拍落地 ≥3 条的批 12 个共 49 条"
                        "（发兵 2,269,698、手续费 245,251）；最重的是 7924 kaito9 三条打 Player 915（一拍花掉余额的 35%）和 3843 zexos1 六条打 Player 625（42%）。按日志落盘先后只有 kaito9 在 t=1260 落后过一次 90 拍。",
        "8_noFullSendLock": "影子里 8 个号被锁上（noah88 463、leo_tx 477、riku_x 571、talon5 610、alex_k 750、ryan_m 958、kaito9 1014、zexos1 3837；sora_w、zero_7 没有），之后挡掉 23 次出兵（leo_tx 7、kaito9 6、alex_k 5）。"
                            "有后果的一处：riku_x 1535~1555 五个决策拍本来各要发 1.7~1.9 万兵打 Player 625，被换成 1 兵试探——录像里 1575 ×2、1582 三条 pct=0 的单子各带 122~124 兵、各付 1,474~1,493 手续费。",
        "9_invertedFeeding": "2 条：8090 alex_k（密度 51）→leo_tx（72）到账 96,944；8565 alex_k（56）→kaito9（74）到账 109,435——都是 alex_k 被队友围住之后按围死号的门槛发的。"
                             "不是围死号的 18 条捐方密度 107~114、收方 21~93。",
        "10_spawnRecompute": "有重算、没有出事：协调器 42 次求解、每号 23~32 次指派，我方 268 条出生指令（每号 22~31 条）；没有两个号指向同一点。riku_x 的落点离最后一次指派 29.3 像素"
                             "（它最后一条生效的指令还是上一次的点），其余 9 个号都在 3.5 像素以内。",
        "11_winFloorMateLock": "影子里证实。t=300~1499 有内置 AI 邻居的 1,457 个决策拍：出手 149、只打无主地 40、零指令 1,268。零指令里 AI 单价高于当拍出价 568 拍，safeFinite 留底 559 拍（参照我方队友 384 拍，占零指令 30.3%），"
                               "价格项或 dpKeep 113 拍，过了底线没发 28 拍。参照队友的 384 拍里 246 拍最好的目标每格 ≤3 兵（平均 399 格）。同一条「不排除队友」的毛病在没有 AI 邻居之后换了个地方继续（defenseNeed，142 拍）。",
        "12_oneCmdPerTick": "有，量小。影子里同一决策拍发两条的 8 拍：kaito9 460、zexos1 470、riku_x 1515~1530 四拍和 2035 / 2040；影子的指令数比录像多 8 条（kaito9 1、zexos1 1、riku_x 6）。"
                            "riku_x 1515~1530 的四条「第二条」（pct=122 打 Player 625）录像里落地 2 条（1561、1568）。",
        "13_inflightRepeat": "证实，是转折点 2 的起点。463 条生效的进攻里 346 条在「同一目标、落地间隔 ≤12 拍」的连发组里（116 组）；对真人 69 组 214 条发兵 36,325,013，其中第 2 条起 22,345,889（手续费 2,446,852）。"
                             "超过吃掉整块所需的 9 组 2,829,630——其中 1,111,277 是 kaito9 反打 Eyup 梭哈的那一组，属于误标（没算对方压上来的兵）。害处最大的是 1512~1526 三个号各三条，叠起来是余额的 74%~84%。",
        "14_capTruncPingPong": "截断 1 笔：8337 kaito9→leo_tx 名义 1,654,426，收方离硬上限只剩 624,669 的空间，到账 624,669、手续费 490,200（费 / 到账 0.785）；截下的部分留在 kaito9 手里，收方 19 拍后出局。来回倒手 0 笔。",
        "15_lateAiFloors": "基本不适用：t≥1500 身边还有内置 AI 的决策拍只有 33 个（都是 leo_tx，1500~1660），32 个的留底被敌方真人邻居的余额占满，1 个 AI 价高；没有队友互锁。"
                           "打「已离开的真人席位」走同一段代码：leo_tx 2002~2016 四条 175,433 兵打 Burito 的席位（所需约 5 万），kaito9 4704~4711 两条 1,131,740 兵吃下 Kalmar 的席位（22,220 格）。",
        "16_overSkipsPrice": "证实，2700 之后的出手大半是这样来的。影子：kaito9 2850~5300 出手 32 拍，17 拍是过软上限时发的（约 400 万兵，c/worth 1.56~3.70）；leo_tx 5300~7100 出手 40 拍全部是（39 拍 c ≥ worth，约 1,298 万兵）；"
                             "kaito9 7100~8822 出手 17 拍里 11 拍（约 684 万兵）。这条规则是四个号 2700~5310 涨到 18.6% 的来源，也是 5310 之后 leo_tx 把调度来的兵按高价打在 Norman 身上的原因。",
        "17_yieldDispatch": "生息余粮 4 笔（到账 1,810,513、手续费 612,348），落地当拍捐收两边每 10 拍利息合计 +19,340；进攻余粮 3 笔 +22,196；协防 14 笔 −3,667（其中 5 笔为负，合计 −48,509）。"
                            "全部 21 笔合计 +37,869 / 10 拍——按这个速度，397 万手续费要 1,049 拍才生得回来。",
        "18_doomedPocket": "有。分支 A（挨的兵 >1.65×余额）：zero_7 挨打的 61 个决策拍里 19 个、ryan_m 24 里 5 个、riku_x 50 里 4 个；分支 B（t≥4500、领土不到最大号的 22%、挨的兵 >0.45×余额）：zexos1 76 里 24 个、leo_tx 207 里 11 个。"
                           "但早死的四个号没人协防的主因不是这条，是捐方密度不到 102。",
        "19_boatVoyage": "船很少：5 条带兵 52,199、船费 4,855（9.3%），靠岸时剩 28,975。talon5 868 / 882 两条靠在队友 sora_w 岸上（到账 5,155）；ryan_m 1078 一条 17,541 兵 292 拍后带 11,069 兵靠在 HD.MAX 的地上，没有换到地。"
                         "1078 之后我方没再发过船：t≥1500 没有邻居也没有无主地的 174 个决策拍里 171 个因为「有队友还贴着敌人、自己密度 <115」不出船。对面 Player 384 全程发船费 2,826,841。",
    },
    "extraScripts": ["60_truth.cjs", "61_truth_view.py", "62_rank.py", "63_replay_ledger.py", "64_cmd_loss.py", "65_shadow.mjs", "66_spawn_truth.mjs", "67_troop_flow.mjs", "68_watch.mjs",
                     "69_quota_truth.mjs", "70_team_density.py", "71_death_chain.py", "72_repeat_sends.py", "73_front_width.py", "74_side_flow.mjs", "75_interest.py", "76_boat_targets.mjs",
                     "77_drop30_classify.py", "78_bot_share.py", "79_help_table.py", "80_donation_yield.py", "81_same_tick_batches.py", "82_outlet_gap.py", "84_pair_cmds.py", "85_trace_blocked.py",
                     "86_enemy_neighbors.py", "87_trace_classify.py",
                     "review_src/A061.py", "review_src/common.py"],
    "extraOutputs": [f"c136-review/agents/R07/out/A061/{f}" for f in
                     ("truth_view.txt", "truth_check.txt", "truth_all.tsv", "truth_bots.tsv", "truth_border.tsv", "rank.txt", "team_density.txt", "side_flow.txt", "side_flow_tp.txt", "humans_cmd.tsv",
                      "troop_flow.txt", "troop_flow_tp.txt", "cmd_effect.tsv", "drop30_recon.txt", "drop30_class.txt", "interest.txt", "bot_share_frozen6.txt", "outlet_gap.txt", "boat_targets.txt",
                      "replay_ledger.txt", "quota_truth.txt", "repeat_sends.txt", "same_tick_batches.txt", "front_width.txt", "death_chain.txt", "spawn_truth.txt", "cmd_loss.txt", "patterns.json",
                      "help_table.txt", "donation_yield.txt", "shadow_check.txt", "shadow_early.txt", "shadow_early_humans.txt", "shadow_late_ai.txt", "shadow_boat_gate.txt", "shadow_donor_gate.tsv",
                      "shadow_cmds.tsv", "shadow_nofull.tsv", "shadow_trace_zero_7_1400_1980.txt", "shadow_trace_alex_k_1400_2700.txt", "shadow_trace_zexos1_1400_2700.txt",
                      "shadow_trace_kaito9_1400_2900.txt", "shadow_trace_sora_w_1500_2520.txt", "shadow_trace_riku_x_1400_2560.txt", "shadow_trace_ryan_m_1400_2650.txt", "shadow_trace_leo_tx_1400_2700.txt",
                      "shadow_trace_kaito9_2850_5300.txt", "shadow_trace_zexos1_4300_6030.txt", "shadow_trace_kaito9_5300_7100.txt", "shadow_trace_alex_k_5300_6600.txt", "shadow_trace_leo_tx_5300_7100.txt",
                      "shadow_trace_kaito9_7100_8822.txt", "shadow_trace_leo_tx_7100_8356.txt", "shadow_trace_alex_k_6600_8786.txt", "trace_blocked_leo_tx_5300_7100.txt", "trace_blocked_kaito9_7100_8822.txt",
                      "trace_blocked_alex_k_6600_8786.txt", "trace_classify.txt", "enemy_neighbors.txt", "pair_cmds_deaths.txt", "pair_cmds_tp2.txt", "pair_cmds_mid.txt", "pair_cmds_tp3.txt", "pair_cmds_p769.txt", "pair_cmds_t5bank.txt",
                      "watch_bigboss.txt", "watch_eyup_allin.txt", "watch_norman_boat.txt", "watch_p769_exit.txt", "watch_p915_empty.txt")],
    "confidenceOverall": "高（事实层）：全场真值来自真引擎重放，与 476 个日志快照逐条一致；两边每条指令的扣款、到账、退兵、船、配额记账都是引擎里记下来的，逐人逐窗核对差额为 0；利率按引擎公式重算，2,785 个桶里 2,719 个与真值相同（差得最多的一桶在离开席位 noah88 上）。"
                         "中高（原因层）：出价 / 留底 / 可用兵、各道闸的归类、t<1500 不打贴身真人的原因来自影子运行——影子与真日志的 21 条调度、73 条开局指令逐条相同，floorAt 复刻 392 次核对无差，但真号内存里的值看不到。"
                         "推断：落后主要来自站位（十个号挤成一团、外面一圈敌方真人）和 t<1500 的两条留底规则；5310~7020 的兵如果有别的去处结果会不同。未知：两个席位离开的原因、Player 769 梭哈的原因。"
                         "分型取 outscaled：T5 从 1080 起一直第一，我方从没领先；5310~7020 有过一段进账不输对面的窗口，但没有换成地。",
}
