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
    dict(id="NEW-DF-01", prefix="DF", name="挨打不还手：失地 ≥30% 的过程中指令数为 0",
         definition="从某条快照起连续若干段合计失地 ≥30%（相对起点领土）且全程 Δcmds=0、Δboats=0",
         detect="scripts/patterns.py: df_passive"),
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
]

BY_ID = {p["id"]: p for p in CATALOG}


def pick(*ids):
    return [dict(BY_ID[i]) for i in ids]
