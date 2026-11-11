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
                    "每条按执行时余额抽 (102+1)/1024 再付 12/1024 手续费，n 条合计抽走 1-0.8883^n（n=4 是 38%，n=7 是 56%）；"
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
]

BY_ID = {p["id"]: p for p in CATALOG}


def pick(*ids):
    return [dict(BY_ID[i]) for i in ids]
