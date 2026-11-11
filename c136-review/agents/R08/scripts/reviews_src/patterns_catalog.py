"""R08 自拟模式目录（ledger/PATTERNS.md 为空，全部以 NEW- 提议）。

每条模式的 definition 都写成能在 bundles/ 的 in_game.log / card.json 上机械计数的条件；
计数实现统一放在 scripts/patterns.py（M7），逐局复盘 JSON 的 newPatterns 用 pick() 取本局命中的条目。

口径约定：
  · 「快照」= 一条 HL-TICK（每 90 拍一条），bal 是本土余额（不含在途进攻兵），dens = bal/terr；
  · 「公式余额」= 从上一条快照起不发任何指令、领土不变，只按引擎利息/地租公式滚到本条快照的余额（facts.interest_gain）；
  · 「两段口径」= 一段的净流出（公式余额 - 实际余额）减去下一段的回流（实际 - 公式），除以两段净增领土。
    因为在途兵不在 bal 里，单段数字会把「派出去还没打完的兵」算成花费，两段合计才稳。
"""

CATALOG = [
    # ---- 出生 / 开局 ----
    dict(id="NEW-SP-01", prefix="SP", name="出生点走兜底分支被打散",
         definition="该号最后一条 HL-SPAWN-BACKEND 的 voronoi=500（协调器 pickNextTarget 四档放宽都无解后走『离已选队友最远』兜底，voronoiPixels 写死 500）；一局内 ≥2 个号命中记为该局命中",
         detect="scripts/patterns.py: sp_fallback"),
    dict(id="NEW-SP-02", prefix="SP", name="出生点同队扎堆：≥3 个号互相贴着，分到的地盘不足 3000 格",
         definition="最后一条 HL-SPAWN-BACKEND 的 minAllyDist≤110 的号 ≥3 个，且其中至少一个 voronoi<3000",
         detect="scripts/patterns.py: sp_cluster"),
    dict(id="NEW-OP-01", prefix="OP", name="开局被围：t<900 就没有敌邻也没有中立地，领土不足 2500",
         definition="t<900 的任一快照 nb=0 且 neut=0 且 terr<2500",
         detect="scripts/patterns.py: op_boxed_early"),
    dict(id="NEW-OP-02", prefix="OP", name="碎中立地卡死：没有敌邻、只贴着几格中立地，既不扩张也不发船",
         definition="连续 ≥6 条快照 nb=0 且 1≤neut≤8、领土变化 <2%（策略里『有中立地就不发船』与『这点地不值一条指令』两个条件同时成立）；记卡住的拍数",
         detect="scripts/patterns.py: op_crumb_lock"),
    dict(id="NEW-OP-G2", prefix="OP", name="（正面）被围后及时发船突围",
         definition="t<1500 的某条快照 nb=0 且 neut=0 且 terr<3000，其后 180 拍内 Δboats≥1，且 450 拍内领土 ≥1.5 倍",
         detect="scripts/patterns.py: op_boat_breakout"),
    dict(id="NEW-OP-G1", prefix="OP", name="（正面）开局 DP 扩张按期完成",
         definition="第一条 HL-TICK（t≤630）人均领土 ≥2500；日志里有 OPENING-CHECK 行的局还要求全部 OK（G08 这类没有该行的局只看前一条）",
         detect="scripts/patterns.py: op_on_schedule"),
    # ---- 经济 ----
    dict(id="NEW-EC-01", prefix="EC", name="开局结束时地大兵薄，随后被吃",
         definition="t∈[1440,1710] 的任一快照 terr≥8000 且 dens<5；命中后 900 拍内领土较该快照跌 ≥30% 记为『兑现』",
         detect="scripts/patterns.py: ec_thin_big"),
    dict(id="NEW-EC-02", prefix="EC", name="少邻囤兵：只有 1~2 个敌邻、无中立地，长期不出手",
         definition="连续 ≥8 条快照（≥630 拍）1≤nb≤2 且 neut=0、领土变化 <2%、Δcmds≤2，期间 dens 至少翻倍；同窗内同队有编队友阵亡或领土腰斩记为『有代价』",
         detect="scripts/patterns.py: ec_hoard_1nb"),
    dict(id="NEW-EC-03", prefix="EC", name="超软上限滞留：余额 > 100×领土",
         definition="连续 ≥2 条快照 bal>100×terr（超出部分利息按 [E6] 扣减）；记命中号数与累计快照数",
         detect="scripts/patterns.py: ec_over_softcap"),
    dict(id="NEW-EC-G1", prefix="EC", name="（正面）t<2400 不打密度更高的单邻，存活更久",
         definition="t∈[1500,2400] 连续 ≥5 条快照 nb=1、Δcmds≤2，且该号存活到 t≥3500",
         detect="scripts/patterns.py: ec_hold_survive"),
    # ---- 捐款 / 后勤 ----
    dict(id="NEW-DN-01", prefix="DN", name="救援门槛够不着：队友开始失地时全队没有一个号达到捐款密度门槛",
         definition="阵亡号从峰值后第一个失地段开始的那条快照上，同队存活编队友里 dens≥106 的个数为 0，且该号到死没有收到任何成交捐款",
         detect="scripts/patterns.py: dn_threshold_unreachable"),
    dict(id="NEW-DN-03", prefix="DN", name="t<1500 没有捐款通道：囤到上限的号帮不了缺兵的队友",
         definition="t<1500 的同一拍快照里，有编队号 bal>100×terr，同时有同队编队号 dens<1；按快照计数（t<coreFrom=1500 时 Policy.act 不调用 tryDonateToTeammate）",
         detect="scripts/patterns.py: dn_no_channel_early"),
    dict(id="NEW-DN-02", prefix="DN", name="小额捐款税大于到账",
         definition="HL-DONATE 的 pct<63（到账 (pct+1)/1024 < 税 64/1024）；按笔计数并累计 税-到账",
         detect="scripts/patterns.py: dn_tax_gt_gift"),
    # ---- 进攻 ----
    dict(id="NEW-AT-01", prefix="AT", name="超软上限后高价倾泻",
         definition="某快照 bal>100×terr，其后 180 拍内出现 DROP30 且领土增加、两段口径 ≥150 兵/格",
         detect="scripts/patterns.py: at_overcap_dump"),
    dict(id="NEW-AT-02", prefix="AT", name="出手后变薄，随后被吃",
         definition="一段进攻性掉款（相邻快照 bal 跌 ≥30% 且领土增加）结束时 dens ≤ 起点的一半，且下一段没有回流把 dens 拉回一半以上；兑现：其后 450 拍内领土较出手后跌 ≥30% 或阵亡",
         detect="scripts/patterns.py: at_drained"),
    dict(id="NEW-AT-03", prefix="AT", name="高价零敲：单段派出 ≥30% 余额，每格花费 ≥90 兵且 ≥3 倍自身密度",
         definition="DROP30 且该段领土增加；每格花费取两段口径（下一段净增 ≤0 时退回单段口径），≥90 且 ≥3×该段起点 dens",
         detect="scripts/patterns.py: at_pricey_bite"),
    dict(id="NEW-AT-04", prefix="AT", name="出手后敌邻变多（只有 1 个敌邻时即拆掉唯一缓冲）",
         definition="连续 ≥3 条快照 nb 不变（=k≥1），随后 180 拍内领土 +≥5% 且 nb≥k+1（k=1）或 ≥k+2（k≥2）；兑现：其后 450 拍内领土较峰值跌 ≥30%",
         detect="scripts/patterns.py: at_buffer_removed"),
    dict(id="NEW-AT-G1", prefix="AT", name="（正面）低价买地：两段口径 ≤12 兵/格",
         definition="DROP30 且两段净增领土 ≥500，两段口径的每格花费 ≤12",
         detect="scripts/patterns.py: at_cheap_buy"),
    # ---- 防守 ----
    dict(id="NEW-DF-01", prefix="DF", name="挨打不还手：失地 ≥30% 的过程中没有打向进攻者的指令",
         definition="从某条快照起连续若干段合计失地 ≥30%（相对起点领土）。严格口径：全程 Δcmds=0、Δboats=0。"
                    "宽口径：这段时间的指令只有捐款、替别人的协防戳刺和船，陆攻 ≤1 条（有录像时按真值指令账确认没有一条打向进攻者）。两个口径分开计数",
         detect="scripts/patterns.py: df_passive（严格口径）；scripts/logstats.py [QD]（宽口径：领土从局部峰值掉 ≥30%，列出期间的指令数 / 船数）"),
    # ---- 海上 ----
    dict(id="NEW-SE-01", prefix="SE", name="大额或连续海上拦截",
         definition="HL-INTERCEPT 的 pct≥200（≥19.6% 余额），或同一个号 900 拍内 ≥5 次拦截；同时记这些段的净花费（公式余额 - 实际余额）",
         detect="scripts/patterns.py: se_big_intercept"),
    # ---- 执行层（指令从发出到生效之间）----
    dict(id="NEW-EX-01", prefix="EX", name="在途重复下单：前一条指令还没生效，又对同一目标发同类指令",
         definition="录像命令流里，同一个号、同类指令（进攻/发船）、同一目标，相邻两条的执行拍相差 ≤14 拍（两个 7 拍回合）记为一串；串长 ≥2 命中。"
                    "同时记串内合计抽兵比例 1-∏(1-(pct+1)/1024) 与第一条的比例；合计 ≥50% 余额的记为『清仓串』。严格口径另数『同一执行拍』的串",
         detect="scripts/dupcmds.py（需要 replay.txt；G 组没有录像，用 NEW-EX-02 代替）"),
    dict(id="NEW-EX-02", prefix="EX", name="连发清仓：一个快照段里连发多条指令，本土余额掉到策略留底以下",
         definition="相邻两条快照之间非发船指令数 Δcmds-Δboats ≥5，段首密度 ≥5，本土余额下降 ≥60%，且该段领土没有减少 10% 以上（排除被吃空的段）。"
                    "只看日志就能数，是 NEW-EX-01 在没有录像时的替代口径；"
                    "兑现口径：此后 450 拍内领土比该段结束时少 ≥30% 或阵亡",
         detect="scripts/patterns.py: ex_burst_drain"),
    dict(id="NEW-EX-03", prefix="EX", name="协防戳刺连发：同一个号对同一个敌人连着发多条 10% 戳刺",
         definition="同一个号的 HL-ASSIST 行，目标敌人相同、相邻两条相差 ≤4 拍，串长 n≥3 命中。"
                    "每条按执行时余额抽 (102+1)/1024 再付 12/1024 手续费，n 条合计抽走 1-0.8877^n（n=4 是 38%，n=7 是 57%）；"
                    "同时记该号所在快照段的净流出（公式余额 - 实际余额）与预测值的差",
         detect="scripts/patterns.py: ex_assist_burst"),
    dict(id="NEW-EC-04", prefix="EC", name="全队停手囤兵：中立地吃完后领土不涨、余额成倍涨",
         definition="连续 ≥10 条快照（≥900 拍）里，窗口首尾都存活的编队号合计领土增幅 ≤5%，合计本土余额 ≥3 倍，合计指令数 ≤ 号数×10；"
                    "记窗口长度、余额倍数，以及窗口内阵亡或领土腰斩的编队号数",
         detect="scripts/patterns.py: ec_team_standoff"),
    dict(id="NEW-SP-03", prefix="SP", name="出生点重解混用：最后一解没有全员执行，队友落点撞在一起",
         definition="≥1 个号最后一条 HL-SPAWN-BACKEND 的点，与最后一条 BACKEND-SPAWN-COORD 里分给它的点不一致（相差 >4 像素）；"
                    "兑现口径：按各号最后收到的点算，有两个队友相距不到最后一解 minSep 的一半",
         detect="scripts/patterns.py: sp_mixed_solutions"),
    # ================= 以下为 B 组（有录像、能做真引擎重演）新增 =================
    # 口径：「真值」= scripts/resim_r08.mjs 用录像逐拍重演 512 个玩家得到的全场状态（out/<局>/resim.json）；
    #       「影子决策」= scripts/shadow.mjs 在真值的每一拍上跑干净策略源码、只记不发得到的「不落后的客户端此刻会发什么」；
    #       「时延」= 录像里的执行拍 − 配上的影子决策拍（scripts/shadowcmp.py，同类型、同 pct、同目标）。
    # ---- 输入输出 / 客户端（IO）----
    dict(id="NEW-IO-01", prefix="IO", name="客户端卡顿波：指令比决策晚几十到几百拍才落地",
         definition="按执行拍每 180 拍一窗，本编队配上影子的已执行指令时延中位 ≥35 拍（5 个服务器回合）的窗口连续 ≥2 个记为一波；"
                    "记起止拍、峰值窗口的中位 / P90、受影响号数（该波内自身中位 ≥35 的号）、波内陆攻落地时已无效的比例",
         detect="scripts/shadowcmp.py [SF][SB]（需要录像）"),
    dict(id="NEW-IO-02", prefix="IO", name="补拍成批落地：一个服务器拍里冲出 ≥3 条指令，原本分散在 ≥30 拍里",
         definition="同一个号同一个执行拍 ≥3 条指令，且配上的影子决策拍跨度 ≥30 拍；记批数、每批条数（实测上限 9 条）、"
                    "该批合计派出占执行前余额的比例；≥50% 记为『清仓批』。只有录像没有影子时退回『同一执行拍 ≥3 条』",
         detect="scripts/shadowcmp.py [SB2]；scripts/truth.py [TG]"),
    dict(id="NEW-IO-03", prefix="IO", name="旧比例放大：单子按余额比例下，落地时余额已是下单时的 ≥2 倍",
         definition="时延 ≥35 拍、落地生效的陆攻或发船，实发兵力（执行时余额×(pct+1)/1024）≥ 2×本意兵力（决策时余额×(pct+1)/1024）且实发 ≥5000；"
                    "记条数、最大倍数、多发出去的兵",
         detect="scripts/shadowcmp.py [SG]"),
    dict(id="NEW-IO-04", prefix="IO", name="掉线成空壳：号在录像里执行『离开』，领土和兵留给引擎托管",
         definition="真值 leftT ≥ 0 且离开时领土 >0；记号数、离开拍、离开时领土 / 余额合计，以及这些地最后被哪一队拿走（按队合计）",
         detect="scripts/truth.py [TI]"),
    dict(id="NEW-IO-05", prefix="IO", name="决策了没落地：影子在卡顿窗里要发的指令，录像里找不到",
         definition="影子决策拍落在卡顿波内的指令里，后来在录像中配不上的比例 ≥40%；另记 HL-DONATE 有日志、录像没有的笔数及拒因（scripts/donrej.py：受捐方已死 / 超额度 / 到硬上限 / 没发到引擎）",
         detect="scripts/shadowcmp.py [SC]；scripts/donrej.py"),
    # ---- 执行层 ----
    dict(id="NEW-EX-04", prefix="EX", name="发令后 7 拍额度自检：在线时被 8 拍静默窗整个跳过；去掉静默窗则大面积误锁",
         definition="影子按『发令后 8 拍不调用策略』模拟时，updateShadowQuota 的 7 拍检查窗一次都没执行、isNoFullSend 置位号数 = 0；"
                    "同一局把静默窗设为 0 再跑，置位号数 ≥1。记两种设定下的置位号数",
         detect="scripts/shadow.mjs --guard 0 --tag g0 对比 --tag g8"),
    # ---- 出生 ----
    dict(id="NEW-SP-04", prefix="SP", name="同像素 / 贴脸出生：两个编队号的引擎落点相距 <40 像素",
         definition="真值出生点两两距离 <40 像素的号对数（0 像素另计）；兑现：该对里较小的号 t=630 领土 < 全房在线真人中位的 70%",
         detect="scripts/spawncheck.py [PB]"),
    dict(id="NEW-SP-05", prefix="SP", name="最后一条出生指派没执行",
         definition="引擎落点 ≠ 日志里该号最后一条 [HL-SPAWN] 的点；记号数 / 总号数、人均指派条数、『最后一条指派相同』的号对数",
         detect="scripts/spawncheck.py [PC]"),
    # ---- 经济 ----
    dict(id="NEW-EC-05", prefix="EC", name="贴着白给的人机不出手：防人机留底 sb 取了邻居（常是编队友）的余额，互锁",
         definition="t<1500 的影子普查（按真值每 10 拍）里，该号接壤的内置 AI 没有一个过得了门槛，且最便宜那个的原因是 floor:sb 或 minShare(floor:sb)（可用兵 = 余额 − safeFinite ≤ 最小出手比例×余额）；"
                    "按 sb 的来源分账（本编队同队 / 异队、另一支受控编队、同队真人、敌队真人），并数互锁（对方同一点也被我定的 sb 挡住）与「吃光该人机所需 ≤10% 余额」的点数。每局记号·点数（×10 拍）",
         detect="scripts/shadow.mjs census（sbSource）+ shadowcmp.py [SH]"),
    dict(id="NEW-EC-06", prefix="EC", name="人机收割落后：t=630~1260 人均吃到的人机地不到其它真人的一半",
         definition="真值逐对战损账里，(630,1260] 本编队在线号人均从内置 AI 手里拿到的格数 < 0.5×其它真人人均",
         detect="scripts/harvest.py"),
    # ---- 捐款 ----
    dict(id="NEW-DN-04", prefix="DN", name="捐给空壳：受捐方已经离开",
         definition="已执行的捐款里，受捐方在执行拍是空壳（leftT ≤ 执行拍 < 阵亡拍）；记笔数、到账、税，以及这些空壳最后被谁吃掉",
         detect="scripts/truth.py [TH]"),
    dict(id="NEW-DN-05", prefix="DN", name="名字池误认：给名字撞上编队名字池的陌生真人捐款 / 协防",
         definition="HL-DONATE / HL-ASSIST 的受益人不是本编队的号（按引擎号核对），却通过了 isOurSquadBot（名字池）；记笔数、到账、税",
         detect="scripts/truth.py [TH] + 身份表"),
    dict(id="NEW-DN-06", prefix="DN", name="同拍多号捐同一人：第一笔把受捐方顶到上限，其余被拒",
         definition="≥2 个号在同一个本地拍对同一受捐方打印 HL-DONATE，其中 ≥1 笔没进录像（拒因：到 150×领土硬上限或超额度）",
         detect="scripts/donrej.py"),
    # ---- 海上 ----
    dict(id="NEW-SE-02", prefix="SE", name="船靠岸在同队真人的地上：兵并给队友，超额度时整船蒸发",
         definition="真值 landings 里地主是同队真人；记次数、船上兵合计、到账 0（蒸发）的次数与兵数",
         detect="scripts/truth.py [TJ]"),
    # ---- 进攻 ----
    dict(id="NEW-AT-05", prefix="AT", name="清仓打一个真人，兵压在进攻槽里，本土被别人吃掉",
         definition="180 拍内对同一个真人目标的陆攻 / 发船合计派出 ≥70% 余额，打完本土密度 <10；兑现：420 拍内阵亡，且拿走最多地的不是该目标",
         detect="scripts/truth.py [TK] + --death"),
    # ---- 多队 ----
    dict(id="NEW-MT-01", prefix="MT", name="编队被分到多个队",
         definition="真值里本编队的号分属 ≥2 个队；记各队号数、各分支峰值份额、哪个分支所在队获胜",
         detect="scripts/truth.py [TA]"),
    dict(id="NEW-MT-02", prefix="MT", name="跨队协防戳刺：为别的队里的编队号出兵",
         definition="HL-ASSIST 的受益人与出手号不同队；记条数、派出兵、受益人是空壳或编队外真人的条数",
         detect="scripts/truth.py + in_game.log HL-ASSIST"),
    # ---- 终局 ----
    dict(id="NEW-EG-01", prefix="EG", name="小号顶着软上限等死：领土 <6000、密度 ≥85，被大号高价买走",
         definition="t≥2000 连续 ≥10 条真值快照（每 270 拍）领土 <6000、密度 ≥85、领土变化 <5%；兑现：阵亡，且主攻手领土 ≥3×该号、买价 ≥200 兵/格",
         detect="scripts/truth.py [TD][TE]"),
    dict(id="NEW-EG-G1", prefix="EG", name="（正面）终局吃空壳和残血邻居持续长大",
         definition="t≥3500 起 1800 拍内领土 +≥60%，新增领土里 ≥50% 来自空壳或已被第三方打掉一半以上领土的邻居，且该号存活到终局",
         detect="scripts/truth.py [TE]"),
    # ---- B033 起新增 ----
    dict(id="NEW-DN-07", prefix="DN", name="来回倒手：两个号在 600 拍内互相捐款",
         definition="已执行的捐款里，A→B 与 B→A 在 600 拍内都出现过；记两个方向的到账、手续费（每笔收捐出方余额的 64/1024），净流量 = |A→B − B→A|，倒手损耗 = 两个方向手续费合计",
         detect="scripts/truth.py [TH]"),
    dict(id="NEW-DN-08", prefix="DN", name="救援捐款单笔超过受捐额度：整单被拒，冷却后原样重发",
         definition="日志里同一对（捐出→受捐）连续 ≥3 笔相同 pct 的捐款都没进录像，且按引擎口径（game.js donationCost / donCap）那一笔的额度成本 > 当时额度上限 − 已用；记笔数与受捐方结局",
         detect="scripts/donrej.py + digest [G] 的额度栏"),
    dict(id="NEW-DN-G1", prefix="DN", name="（正面）救援捐款到账后受捐方活下来",
         definition="受捐方当时身上有真人进攻兵 ≥ 自己余额的 30%，捐款到账 ≥ 该进攻兵，且受捐方之后 600 拍没有阵亡",
         detect="scripts/truth.py [TH] + --bot"),
    dict(id="NEW-SE-03", prefix="SE", name="小船高费：船上只有几百兵，手续费却是余额的 32/1024",
         definition="已执行的发船指令里手续费 > 船上兵的那些：记条数、手续费合计、同期领土净增；每局手续费合计 ≥ 该号发船时余额中位数的 20% 算命中",
         detect="scripts/truth.py [TL]"),
    dict(id="NEW-DF-02", prefix="DF", name="留底只看现有陆上邻居：邻居是空壳或没兵时把 ≥90% 余额一次派出",
         definition="影子决策里单条陆攻 pct ≥ 921（≥90% 余额）、时延 <35 拍（不是补拍造成）、决策时 safeAt ≤ 余额的 5%；兑现：600 拍内该号被当时不接壤的真人吃掉 ≥50% 领土",
         detect="scripts/shadow.mjs --trace（core.safeNone）+ truth.py --death"),
    dict(id="NEW-EX-05", prefix="EX", name="同一次决策发两条指令，只有第一条落地：零星空地单占掉名额",
         definition="影子同一次 act 发出 ≥2 条指令时，第 1 条在录像里配得上、第 2 条及以后配不上；记被丢掉的第 2 条的本意兵力合计",
         detect="scripts/shadowcmp.py [SI]"),
    # ---- B034 起新增 ----
    dict(id="NEW-MT-03", prefix="MT", name="空壳兄弟仍受保护：异队编队号离开后被引擎托管，照样来打；编队号按名字把它排除在可打名单外",
         definition="真值交战账里攻方是已离开的编队号（空壳）、守方是在线的异队编队号、被拿走 ≥300 格；同期守方对该空壳的陆攻指令数为 0（影子逐拍追踪里该空壳不在 nb 里）",
         detect="scripts/truth.py [TF]『编队内』行 + --cmds；scripts/shadow.mjs --trace（nb 列表）"),
    dict(id="NEW-MT-04", prefix="MT", name="撞名野人算进编队：名字在名字池里的陌生真人占出生名次、受保护、被协防",
         definition="房间里名字在 SQUAD_POOL_SET、但不在本编队日志身份表（HL-GAME-INIT 的 me）里的真人；命中任一：[HL-SPAWN] 的 rankIdx 序列为它留了空位；与某个编队号接壤 ≥30 格持续 ≥180 拍而该号对它 0 条陆攻；[HL-ASSIST]/[HL-DONATE] 的 ally 是它",
         detect="scripts/facts.py digest [B][H] + resim.json names；scripts/shadow.mjs --trace（nb 列表里没有它）"),
    dict(id="NEW-IO-06", prefix="IO", name="日志标签中途换名 / 对局卡少数号：同一个 me 先后用几个名字，掉线号没有结果行",
         definition="traj.csv 的标签数 > HL-GAME-INIT 的 me 个数，或 card.squadBots < HL-GAME-INIT 的 me 个数；记同一个 me 的标签链和没有结果行的 me",
         detect="scripts/facts.py digest [A][B]"),
    dict(id="NEW-DN-09", prefix="DN", name="空壳赠兵（引擎规则）：离开的号没有可打的目标时把全部余额交给一个队友",
         definition="真值重演里 bots.js botGive 的每一次成交：记空壳、收款方（在线编队号 / 其它真人 / 另一个空壳）、到账；单笔 ≥ 收款方当时余额的 50% 算命中",
         detect="scripts/truth.py [TM]（resim_r08.mjs 的 huskGifts）"),
    dict(id="NEW-EC-07", prefix="EC", name="1500 拍后最小指令门槛反过来挡住小人机：吃光它所需的兵小于 minCmd（余额的 4.7%）就跳过，余额越多越吃不动",
         definition="影子在真值上每 10 拍按 Policy.buyLand 对非真人邻居的那条路重算（c110 L5363-5369）：t≥1500、接壤至少一个内置 AI、没有一个过门槛，"
                    "且最便宜那个的 want = 1.25×need + 3×边界 < minCmd = feeK×⌊12×余额/1024⌋；一个号累计 ≥5 个点算命中。记被挡 AI 的格数、兵、want、当时余额，以及这块地后来被谁吃走",
         detect="scripts/shadow.mjs（census2）+ scripts/shadowcmp.py [SJ]"),
    dict(id="NEW-DF-03", prefix="DF", name="没兵的人机赊账啃地（引擎规则）：内置 AI 新开进攻的第一圈必赢，被啃的号每格掉 1.6 倍自身密度的兵；号既不压兵在它身上、也不吃它",
         definition="真值交战账里攻方是内置 AI、守方是本编队的号：整局丢 ≥100 格且守方余额损失 > 攻方实际耗兵（正常交换守方损失 ≤ 攻方耗兵的一半）。"
                    "机制：game.js expandAttack L1016-1020 的 fresh && counter === 0 分支，不够的兵由 takeBalance L766-776 记欠账（上限 5 万）；"
                    "记每一对的格数、AI 实际耗兵、号的余额损失，以及全房三组人（本编队 / 同房另一支 / 其它真人）的『余额损失 ÷ AI 耗兵』",
         detect="scripts/truth.py [TN]；scripts/aiprobe.mjs <局> --ai <号> --bot <名字>（逐窗：新开进攻次数、靠赊账赢的圈数、赊的兵、号压在 AI 身上的反击兵）"),
    dict(id="NEW-EC-08", prefix="EC", name="1500 拍后防人机留底的锁还在：打人机前的留底 = min(sb, 88×领土)，sb 由更富的邻居（常是编队友）定出，密度不到 88 的号对任何人机都出不了手",
         definition="影子在真值上每 10 拍按 Policy.buyLand 对非真人邻居的那条路重算：t≥1500、接壤至少一个内置 AI、全部被挡，且最便宜那个的原因是 safe:sb 或 safe:sb(cap)"
                    "（buyLand L5322 → Policy.safeAt L4524-4541 → safeAt L2744-2754，botSkip=0 时不跳过任何人机 → safeFinite L2532-2541）；一个号累计 ≥5 个点算命中。记 sb 是谁的余额定的",
         detect="scripts/shadow.mjs（census2）+ scripts/shadowcmp.py [SJ]"),
    dict(id="NEW-SE-04", prefix="SE", name="船靠岸在异队编队友的地上：下单时落点是空地或人机，航行和时延期间被编队友占了，引擎按进攻结算",
         definition="真值船靠岸记录里船主和地主都是本编队的号、不同队、地主在线；记船上兵、吃掉的格数、双方损失，以及影子决策拍那个落点当时的地主",
         detect="scripts/truth.py [TO][TF]；scripts/boattrack.mjs；shadow.json 里该船指令的 targetOwner"),
    dict(id="NEW-IO-07", prefix="IO", name="全队断流：编队所有在线号先后停止向服务器发指令，结果表全是 left，对局没有打完",
         definition="结果表所有行 event=left 且写入时间相差 ≤60 秒；录像最后 ≥150 拍里本编队执行的指令 ≤1 个号，而同期其它真人每 90 拍仍有 ≥10 条指令",
         detect="results.csv 的 at / tick；scripts/lagstats.py [LA][LB]；scripts/truth.py --cmds"),
    dict(id="NEW-DN-10", prefix="DN", name="捐款连发：18 拍冷却短于指令时延，前一笔还没扣款又对同一人捐一笔，两笔都成交",
         definition="同一捐出方、同一收款方、间隔 ≤25 拍的两条 HL-DONATE，后一条的 myBal 没有比前一条少（前一笔还没落地），余额序列拟合判两笔都成交；记多付的到账与税",
         detect="scripts/donfit.py [FA][FD]（连发@）"),
    dict(id="NEW-DN-11", prefix="DN", name="盈余捐款不受自己的留底约束：pct 固定 153/185/280，捐完密度掉到同一函数刚算出的留底以下",
         definition="surplus donate 成交后（含 6.25% 税）捐出方余额 ÷ 领土 < 68（tryDonateToTeammate 对有海岸的号用的留底密度）；记笔数、发令时密度与捐后密度的中位数",
         detect="scripts/donfit.py [FE]"),
    dict(id="NEW-DN-12", prefix="DN", name="往正在崩的队友身上捐：到账被受捐方 150 倍上限夹小，6.25% 的税按捐出方余额全额收",
         definition="余额序列拟合判『成交（夹小）』的捐款，且收款方在其后 300 拍内阵亡或失地 ≥30%；记到账、税、收款方阵亡拍",
         detect="scripts/donfit.py [FA][FD]（夹小）"),
    dict(id="NEW-EC-09", prefix="EC", name="顶硬上限空转：余额 = 150×领土（引擎硬上限，利息截掉），有敌邻、指令数不变",
         definition="HL-TICK 里 bal ≥ 149.5×terr 的快照 ≥2 条，且期间 nb≥1、cmds 不变；记首末拍，以及『有敌邻、密度 ≥95、不发指令』的最长连续拍数",
         detect="scripts/logstats.py [QB]"),
    dict(id="NEW-IO-08", prefix="IO", name="一个对局包混了两个物理房间：对局卡的人数、分队、份额是混房统计",
         definition="rooms-discovery.json 里该局 nRooms ≥2；card.json 的 squadBots / teamSplitCounts / peakPrimaryTeamShareSeen 与按房间重算的不一致",
         detect="scripts/facts.py <局> --room N（复盘 JSON 的 context.cardOriginal 对照）"),
    dict(id="NEW-IO-09", prefix="IO", name="『疑似被拒捐款』是时延假象：发令 20 拍后的余额还没扣，实际晚落地",
         definition="按『发令 ≥20 拍后第一条余额观测』判拒的捐款里，余额序列拟合判成交的笔数；记旧判定→新定案的转移表",
         detect="scripts/donfit.py [FA]"),
    dict(id="NEW-SP-06", prefix="SP", name="后端出生协调器按整支启动名单求解：名单里的名字大半不在这个房间",
         definition="[BACKEND-SPAWN-COORD] Solved N bots 的 N ≥ 本房间实际在线的编队号数 ×2；记 N、本房间号数、每次求解的 minSep",
         detect="scripts/spawncheck.py [PA]；in_game.log 的 BACKEND-SPAWN-COORD 行"),
    dict(id="NEW-IO-10", prefix="IO", name="只看日志的『指令没生效』：cmds 涨了，余额没少、地没涨（客户端落后服务器时的日志侧影子）",
         definition="相邻两条 HL-TICK（间隔 90 拍）cmds 增加，但余额比只吃利息的预期少的部分 < 期初余额 2%、领土增幅 ≤0.5%；按 270 拍桶记没生效的指令数 / 指令数。"
                    "同包有另一个带录像的房间时，用日志行号的先后给两个房间的本地拍对表，量出多落后的拍数",
         detect="scripts/noeffect.py [NA][NB]；scripts/clockskew.py [KA][KB]"),
    dict(id="NEW-DF-04", prefix="DF", name="被更富的真人邻居压住：对真人的留底 safe =（最富真人邻居余额 − 1.5×领土）÷1.78 高过自己全部余额，对谁都出不了手；挨打时也不能捐，余额随地一起被打掉",
         definition="影子追踪里 safeNone > 余额 的点 ≥5 个、跨度 ≥300 拍，且该号最后阵亡；记阵亡前余额被打掉多少（真值交战账）",
         detect="scripts/shadow.mjs --trace + scripts/trshow.py；scripts/truth.py [TE]"),
    dict(id="NEW-DN-G2", prefix="DN", name="（正面）被围的号把兵持续输给前线队友，前线号长大",
         definition="同一对（捐出方被围 nb=0 且 neut=0 → 收款方）成交 ≥10 笔，收款方在首末笔之间领土 ≥2 倍；记到账、税",
         detect="scripts/donfit.py [FB][FC]"),
    dict(id="NEW-SE-05", prefix="SE", name="被围时的闲置船不设价格上限：没有陆上邻居时每 60 拍一条船去拿几格小岛，每条先付余额的 32/1024",
         definition="快照窗开头 nb=0 且 neut=0、窗内新增指令全是船（Δcmds == Δboats ≥ 1）的『纯船窗』：一个号累计 ≥10 条这样的船，"
                    "且纯船窗里少掉的兵（公式余额 − 实际）÷ 窗内净增领土 ≥ 1000 兵/格（净增 ≤0 也算）；记船数、少掉的兵、净增领土",
         detect="scripts/logstats.py [QE]（只看日志；有录像的局用 NEW-SE-03 的口径）"),
    dict(id="NEW-AT-G2", prefix="AT", name="（正面）超软上限后把超出的兵放给正在崩的邻居",
         definition="余额 >100×领土 的号按 over 档留底放兵，目标所在的队 900 拍内全队份额掉 ≥50%；之后 1800 拍内该号领土 +≥30% 且存活到终局",
         detect="scripts/truth.py [TC][TE]；scripts/shadow.mjs --trace（放兵那一拍的 avail / keep）"),
    dict(id="NEW-SE-G1", prefix="SE", name="（正面）中后期靠船换出一片新地",
         definition="t≥1500，一个号连续 ≤540 拍的快照窗里新增指令全是船（≥5 条），期末领土 ≥ 期初的 1.5 倍",
         detect="scripts/logstats.py [QE]"),
    # ---- B006（11-08 的旧版本，只有日志）新增 ----
    dict(id="NEW-SP-07", prefix="SP", name="各算各的槽位：每个号在自己的视图里排 20 个槽位，候选不够时按『离已选点最远』补位，几个号补到同一个点",
         definition="最后一条 [HL-SPAWN]（不是 HL-SPAWN-BACKEND）的坐标完全相同的编队号 ≥2 个；记撞点的点数、号数，以及这些号 t≈900 的领土",
         detect="scripts/spawnlog.py [SB][SC]"),
    dict(id="NEW-EX-06", prefix="EX", name="每 5 拍重发一条：一个 90 拍快照窗里非船指令 ≥16 条（归档 c110 的在途保护 + 同目标冷却下最多 9~11 条）",
         definition="t=700~2100 的任一 90 拍快照窗 Δcmds − Δboats ≥16；记窗数。跨局统计里只有 B001~B007（2026-11-08 08:19~09:13 UTC）出现",
         detect="scripts/cadence.py（out/_cross/cadence_B.txt）"),
    dict(id="NEW-IO-11", prefix="IO", name="整段零花费：连续 ≥270 拍每个快照窗都有新指令，余额却和『只滚利息』的公式逐兵相等，领土不涨",
         definition="连续 ≥3 个 90 拍快照窗，每窗 cmds 增加、余额与利息公式相差 <0.1%、领土不涨；记段数、指令数（扣掉日志里的捐款条数）、涉及的号数。"
                    "这些指令没有被服务器扣过一兵：没送到，或送到时目标已经不在（免费失败）",
         detect="scripts/noeffect.py [ND]"),
    dict(id="NEW-IO-12", prefix="IO", name="（只看日志）积压后清仓：之前累计 ≥30 条指令没生效，随后一个快照窗里花掉 ≥40% 余额",
         definition="noeffect [NB] 的『其后第一次单窗花掉 ≥40%』一栏有值且『之前没生效』≥30 条；记号数。有录像的局里对应 NEW-IO-02 / NEW-IO-03",
         detect="scripts/noeffect.py [NB]；scripts/logstats.py [QA]"),
    dict(id="NEW-DN-13", prefix="DN", name="累计额度墙：t<4284 受捐方的累计点数顶到全场额度，之后对它的捐款整单被拒；捐出方每 20 拍按固定比例原样重试",
         definition="donwall [WA] 里 t<4284 的『累计超』笔数 ≥10；记笔数、t<4284 的成交率、t≥4284 的成交率。"
                    "引擎口径：t<2142 每 402 兵 1 点（陆地 40 万格时），t<3213 每 1341 兵 1 点，之后 4 + 到账÷受捐方领土；额度每 100 拍只涨 4/6/8/10 点",
         detect="scripts/donwall.py [WA][WC][WE]"),
    dict(id="NEW-DN-14", prefix="DN", name="喂给已经超软上限的号：受捐方自己的余额 ≥100×领土，照样收盈余捐（策略只排除密度 ≥132 的受捐方）",
         definition="donfit 判成交的捐款里，受捐方当拍之前最近一条快照的密度 ≥100 的笔数 ≥5；记笔数、到账、税，以及受捐方在收款期间的领土变化",
         detect="scripts/donwall.py [WG]"),
    dict(id="NEW-SE-G2", prefix="SE", name="（正面）一两条船换出成倍的地：发船后 450 拍内领土 ≥ 发船前的 2 倍，船上的兵 ≤ 发船前余额的 60%",
         definition="一个号在 ≤180 拍内发 1~2 条船，按利息公式少掉的兵 ≤ 发船前余额的 60%，发船后 450 拍内的最高领土 ≥ 发船前的 2 倍",
         detect="scripts/logstats.py [QE]（Konev 一行）；scripts/facts.py [E]"),
    dict(id="NEW-DF-G1", prefix="DF", name="（正面）协防戳刺后队友不再丢地",
         definition="HL-ASSIST 之后 270 拍内受益的队友领土不再下降（此前 180 拍内掉过 ≥10%）",
         detect="scripts/logstats.py [QC]；scripts/facts.py [E]"),
    dict(id="NEW-DN-G3", prefix="DN", name="（正面）前线号一出手，银行集中补给：一个受捐方 360 拍内从 ≥5 个捐出方收到的成交捐款 ≥ 窗前余额的 40%，同期领土 +≥25%",
         definition="donwall [WI] 的窗：捐出方 ≥5 个、到账 ÷ 受捐方窗前余额 ≥40%、受捐方窗内自己发过指令、窗后领土 ≥ 窗前的 1.25 倍；记到账、税、领土前后",
         detect="scripts/donwall.py [WI]"),
    # ---- B030 起新增 ----
    dict(id="NEW-MT-05", prefix="MT", name="房间里没有野人时编队号互相当敌人：超软上限后按『唯一缓冲留 1.12×100×领土』一次放出 20% 余额打编队友，每格 200~460 兵",
         definition="真值指令账里攻守双方都是本编队的号、且发令时房间里没有『不是内置 AI、不在名字池、领土 ≥80』的活人（c110 isProtectedSquadMate L3993-3996 → hasWildOutsidersAlive L3978-3990 返回 false）："
                    "记条数、格数、攻方耗兵、守方余额损失，以及同一拍攻方接壤的内置 AI 合计格数和吃光所需。没有录像的局：自由混战房间（结果行 team 为空）里一个编队号阵亡前 900 拍内，另一个编队号有 DROP30 且领土在涨",
         detect="scripts/truth.py [TF]；scripts/aigate.py [GG][GH]"),
    dict(id="NEW-DF-05", prefix="DF", name="防人机留底 sb 连打真人也挡：两个号共用人机邻居时 sb = 对方的余额，对真人报价不封顶，较穷的号对谁都出不了手；只在对方『正在流血』时封顶放行",
         definition="影子逐报价重走 buyLand（walkBuyLand）里，真人报价的结论是 skip:avail<=0(safe) 且 safeRaw ≥ 自己余额的追踪点 ≥5 个、跨度 ≥300 拍，期间该号领土掉 ≥30%；"
                    "另记该号发出的陆攻里目标带 bleeding 标记的条数（c110 L5323-5326：只有 nearCollapse / bleeding / tD<0.45 的真人目标才按 oppFloorCap×领土封顶）",
         detect="scripts/shadow.mjs --trace（walk）+ scripts/aigate.py [GH]"),
    dict(id="NEW-EG-02", prefix="EG", name="赢面局拖成马拉松：全场只剩一个真人以后还打了 ≥10000 拍",
         definition="本房间除最终赢家以外的最后一个真人（含编队友）出局的拍号到终局拍 ≥10000 拍；记多出来的拍数、秒数（结果行 seconds），以及这段时间里赢家密度 ≥149 的快照占比、领土最低占比。"
                    "没有录像时用结果行：最后一个不是赢家的编队号的出局拍 → 赢家的 end 拍",
         detect="scripts/aigate.py [GD][GF]；bundles/<局>/results.csv"),
    dict(id="NEW-EG-03", prefix="EG", name="打坍的人机靠在途的船回来（引擎规则）：坍缩时有船在海上就不除名，船靠岸后带几格地重新长；号因为 minCmd 不打它",
         definition="真值逐拍盯（aiwatch）：某内置 AI 领土归 0 但 alive=1 且在途船 ≥1，之后领土又 >0（game.js collapse L1314-1335，有船的分支 L1316-1331）；记坍缩拍、靠岸拍、回来时的格数和兵，以及此后它长到多大、号什么时候才再打它。"
                    "只有日志时：号进入扫尾状态（nb=0、neut=0、领土 ≥98% 陆地）之后又出现 nb≥1 且领土连续下降 ≥900 拍",
         detect="scripts/aiwatch.mjs；scripts/aigate.py [GF][GJ]"),
    dict(id="NEW-SE-06", prefix="SE", name="扫尾船被在途上限卡住：base boatOut 按 maxBoats（2 条）放行，扫尾分支写的 6 条不生效；找岛按『手续费÷岛的格数』先挑最大的、不看远近，最后几条船在路上的几百拍里一次搜索都不做",
         definition="HL-TICK 里连续 ≥3 条快照（≥270 拍）nb=0、neut=0、领土 ≥98% 陆地但 < 陆地总格数、boats 不变，且这段时间里没有 HL-SLOW-TICK（找船的水路搜索一次没做）；"
                    "记空档拍数、剩下的格数，以及这段时间之后是赢了还是又冒出敌邻",
         detect="scripts/aigate.py [GJ]"),
    dict(id="NEW-DN-15", prefix="DN", name="银行没处捐：盈余捐款的收款方只认同队的编队名字 / Boss（c110 L4467），这些号都 ≥132 密度（L4469）或太平无战事（L4477-4478）时，被围的号顶着硬上限空转；同队野人前线拿不到一兵",
         definition="同一队 ≥2 个在线编队号连续 ≥900 拍 nb=0、neut=0 且密度 ≥140，这段时间全队 HL-DONATE 0 条、这些号的 cmds 不变；"
                    "记段长、号数、合计兵力、被截掉的利息，以及同期结果行里两队的全队份额",
         detect="scripts/squadfog.py [HE][HH]；scripts/logstats.py [QB]"),
    dict(id="NEW-MT-06", prefix="MT", name="看不见的失地（只看日志）：快照窗两端都是 nb=0、neut=0，领土却在掉——吃它的号在受保护名单里（按名字保护的异队编队账号，停摆后由引擎托管），"
                                           "analyze 不把它算进 nb，反击、买地、『正在挨真人打』的判断都看不到它",
         definition="HL-TICK 相邻两条快照都是 nb=0 且 neut=0、后一条领土比前一条少的窗 ≥5 个且合计丢 ≥1000 格；记窗数、丢的格数、这些窗里的陆攻指令数，"
                    "以及同期成交的、收款方是异队停摆编队账号的捐款（按 450 拍分桶）。有录像时对应 NEW-MT-03",
         detect="scripts/squadfog.py [HC][HF]"),
    dict(id="NEW-IO-13", prefix="IO", name="部分账号停摆（只看日志）：≥3 个号的 HL-TICK 在终局前断掉、没有结果行，对局照常打完；停摆的号在别的号眼里仍是活着的编队友（照样受保护、收捐款），"
                                           "队友救援日志里它们的密度不随时间涨（没有利息 = 引擎里已是离开状态）",
         definition="HL-GAME-INIT 的 me 里，HL-TICK 最后一拍比终局拍早 ≥500 且没有结果行的号 ≥3 个；记号数、停摆的本地拍、当时的领土合计，"
                    "以及之后 squad rescue donate 行里它们的 dAlly 读数（最小 / 中位 / 最大）对照在线号同期密度",
         detect="scripts/squadfog.py [HA][HL]"),
    dict(id="NEW-EG-G2", prefix="EG", name="（正面）贴身的号出局后，当窗接收它留下的空地",
         definition="一个编队号的结果行 died（引擎把它剩下的地变成空地）落在另一个编队号的某个 90 拍快照窗里，后者这一窗发出非船指令（Δcmds − Δboats ≥1）、领土 +≥500 格，"
                    "之后两条快照没有吐回去；记号、格数、指令数。只看日志时『拿的就是那片空地』是推断（两端快照的 neut 可能都是 0）",
         detect="bundles/<局>/results.csv 的 died 拍 + traj.csv 跨过该拍的快照窗（scripts/patterns.py）"),
]

BY_ID = {p["id"]: p for p in CATALOG}


def pick(*ids):
    return [dict(BY_ID[i]) for i in ids]
