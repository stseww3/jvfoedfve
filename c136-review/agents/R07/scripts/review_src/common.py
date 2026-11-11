# -*- coding: utf-8 -*-
"""R07 各局复盘共用的新模式定义（ledger/PATTERNS.md 目前为空，全部以 NEW 提议）。

每个模式的机械检测都在 scripts/42_patterns.py 里（「窗口」= 同一个号相邻两个 HL-TICK 快照、间隔恰好 90 拍、cmds 没有回绕；
dAtk = dCmds − 捐款条数 − 协防条数 − 拦截条数）。review_src/<局>.py 用 np(name, instances, note) 引用。
"""

G09 = "v27-team-g09.js"
C116 = "v27-team-c116.js"
VA = "v27-team-c116-va.js"
VB = "v27-team-c116-vb.js"
SPVA = "spawn-coordinator-c116-va.mjs"
SPVB = "spawn-coordinator-c116-vb.mjs"

PATTERN_DEFS = {
    "R07-IO-CRASH": {
        "category": "IO",
        "definition": "策略在某一拍抛异常（日志 `ERROR: Strategy bot stopped: …`），该号之后只有零星几拍能跑完整决策，HL-TICK 快照中断。"
                      "停摆期间的结果按执行类单独记，不计入策略决策好坏。",
        "detectionSketch": "in_game.log 里 `ERROR: Strategy bot stopped` 的条数/涉及号；traj 相邻快照间隔 >90 拍；cmds 计数回绕＝策略实例被替换（热更新）。",
    },
    "R07-IO-DUP-ASSIST": {
        "category": "IO",
        "definition": "同一个号在 ≤12 拍内对同一个敌人连发 ≥3 条 [HL-ASSIST]（每条 pct=102≈10% 余额 + 1.17% 手续费）。"
                      "协防分支只用 `!g.hasAttack(me, mainAttacker)` 防重复，线上指令要 1~19 拍后才执行，执行前这个条件一直成立，于是每个决策拍都再发一条。",
        "detectionSketch": "events.csv type=ASSIST 按号排序，相邻 ≤6 拍且同目标连成串，串长 ≥3；31_assist_burst_check.py 用余额对账确认真的执行了几条。",
    },
    "R07-DN-CHAIN18": {
        "category": "DN",
        "definition": "同一个号相邻两笔捐款间隔 ≤24 拍（冷却 18 拍刚过就再捐）。每笔按当时余额付 6.25% 手续费，连着捐等于按几何级数缩水。",
        "detectionSketch": "events.csv type∈{DONATE,DISPATCH} 按号排序，相邻间隔 ≤24 拍的对数。",
    },
    "R07-DN-TAX51": {
        "category": "DN",
        "definition": "捐款 pct ≤ 60：到账 = g0(B·(pct+1),1024) ≤ 5.96% 余额，手续费恒为 g0(64B,1024) = 6.25% 余额 → 手续费 ≥ 到账。"
                      "pct=51 时到账 5.08%、总支出 11.33%，每送到 1 兵烧掉 1.23 兵。",
        "detectionSketch": "events.csv 捐款行 pct ≤ 60 的笔数；按日志 myBal 用 r07lib.donate_quote 算名义到账与手续费；30_donation_ledger.py 用整数利息公式逐笔确认是否真的执行。",
    },
    "R07-DN-IDLE-RECV": {
        "category": "DN",
        "definition": "捐给不需要/用不上兵的队友：（a）收方最近快照（≤90 拍）密度 ≥ 60；或（b）收方已经 >90 拍没有快照（策略停摆或已死）。",
        "detectionSketch": "对每笔捐款取收方在该拍之前最近的 HL-TICK 快照：age>90 记 stale，否则 dens≥60 记 dense（44_donation_targets.py 逐笔列出）。",
    },
    "R07-EC-BOXED-RICH": {
        "category": "EC",
        "definition": "后排围死囤兵：快照 nb=0 且 neut=0（四周全是队友/海）且 dens ≥ 60。这种号唯一的出兵口是捐款（和船）。",
        "detectionSketch": "traj.csv 快照 nb==0 && neut==0 && dens>=60 的个数与 Σ余额。",
    },
    "R07-EC-IDLE-RICH": {
        "category": "EC",
        "definition": "挨着敌人、兵多、不出手：窗口起点 nb ≥ 1、dens ≥ 60，窗口内进攻类指令数 dAtk ≤ 0。",
        "detectionSketch": "traj 窗口 + events 扣除捐款/协防/拦截后的指令数。",
    },
    "R07-EC-SOFTCAP": {
        "category": "EC",
        "definition": "余额超过软上限（100×领土）：利息按 g0(2·rate·(B−cap),cap) 扣减，到 150×领土（硬上限）利息归零且入账被截断。",
        "detectionSketch": "traj 快照 dens ≥ 100（SOFTCAP）/ dens ≥ 145（HARDCAP）的个数。",
    },
    "R07-DF-PASSIVE-BLEED": {
        "category": "DF",
        "definition": "被动失地：窗口内领土跌 ≥ max(200, 2%)，起点余额 ≥ 8×领土，窗口内进攻类指令数为 0（既不反击也不换地）。",
        "detectionSketch": "traj 窗口 dTerr ≤ −max(200, 0.02·terr0) && bal0 ≥ 8·terr0 && dAtk ≤ 0。",
    },
    "R07-DF-RICH-BLEED": {
        "category": "DF",
        "definition": "PASSIVE-BLEED 的子集：起点密度 ≥ 60。兵很多、在丢地、一条进攻指令都没有。"
                      "代码上对应 buyLand 里 `keep = max(keep, safeAt(g,q))`：对真人目标的保底 = dpKeep = (最强真人邻居余额 + 它压在我身上的兵 − 1.5×我的领土)/1.78，"
                      "邻居余额 > 1.78×我的余额 + 1.5×领土时 avail ≤ 0，永远不出手；同时被真人攻击时 tryDonateToTeammate 直接返回，兵也送不出去。",
        "detectionSketch": "PASSIVE-BLEED 窗口里 dens0 ≥ 60 的个数、丢地合计、Σ起点余额。",
    },
    "R07-AT-BIG-BURN": {
        "category": "AT",
        "definition": "一个 90 拍窗口里余额跌 ≥30%（起点 ≥10 万、捐款解释不了一半），而每多 1 格地花了 ≥100 兵或领土根本没涨。",
        "detectionSketch": "traj 窗口 (bal0−bal1) ≥ 0.3·bal0 && bal0 ≥ 1e5 && 捐款支出 < 一半跌幅 && (bal0−bal1)/max(1,dTerr) ≥ 100。",
    },
    "R07-SP-CLUSTER": {
        "category": "SP",
        "definition": "出生点扎堆：日志里每个号最后一条 [HL-SPAWN-BACKEND] 的坐标，离最近队友 < 140 像素。",
        "detectionSketch": "spawn.csv 每号最后一行坐标两两求距离，最近队友 < 140 的号数。",
    },
    "R07-OP-BOXED-EARLY": {
        "category": "OP",
        "definition": "开局阶段（t ≤ 1620）就已经 nb=0 且 neut=0：中立地吃完的同时被队友围死，之后领土不再变化。",
        "detectionSketch": "traj 每号第一次出现 nb==0 && neut==0 的快照拍号 ≤ 1620。",
    },
    "R07-EG-FRONT-STARVE": {
        "category": "EG",
        "definition": "前线饿死、后排撑死：同一拍里，贴着敌人的号（nb ≥ 1）密度 < 20 且正在丢地，而 nb=0 的后排号（或 dens ≥ 60 不出手的号）握有全队 ≥ 50% 的兵。",
        "detectionSketch": "42_patterns.py：快照 t 有接敌号（nb≥1、dens<20、领土≥1000）在下一个窗口丢地 ≥max(200,2%)，且 nb=0 的号加「dens≥60 且该窗口零进攻」的号余额合计 ≥ 全队 50%。"
                           "43_window_stats.py <局> t t 的「兵力分布」行可逐号核对。",
    },
    "R07-MT-PRE2400-HOLD": {
        "category": "MT",
        "definition": "中立地吃完之后到 t=2400 之前不碰健康真人：Policy.offers 里 `g.t < 2400 && !onMe && !nearCollapse && !bleeding && rawNeed > 0.35 * B` 直接跳过，"
                      "全队份额在这一段基本不动，兵只攒不用。",
        "detectionSketch": "42_patterns.py：全队贴着的中立地合计 ≤5（t≥900 第一次）记为 tNeut0；记 tNeut0 与 t=2400 的全队份额、其间接敌窗口数（nb≥1）和其中零进攻的窗口数。",
    },
    "R07-SP-SCATTER": {
        "category": "SP",
        "definition": "出生点被协调器摊到互不相邻的位置（最近队友 ≥300 像素的号 ≥3 个，或有号落在地图角/边）。孤立的号四周全是外人，"
                      "t<2400 时密度只有个位数，被真人盯上后既打不回去（保底高于余额）也等不到队友（捐款/协防的密度门槛都够不着）。",
        "detectionSketch": "spawn.csv 每号最后一条坐标两两算距离：最近队友 ≥300 像素的号数；其中 t<2400 就阵亡或领土 <100 格的号数。",
    },
    "R07-DN-PINGPONG": {
        "category": "DN",
        "definition": "两个号互相倒手：A 给 B 捐款后 400 拍内 B 又给 A 捐款。每一手都按捐方当时全部余额抽 6.25%，兵在两个后排号之间来回一次净亏约 22%，一格地也不换。",
        "detectionSketch": "events.csv type∈{DONATE,DISPATCH} 按拍排序；对每笔 X→Y，查之前 400 拍内是否有 Y→X。记回捐笔数、名义到账、手续费。",
    },
    "R07-DN-DEAD-RECV": {
        "category": "DN",
        "definition": "给一个已经不决策的号输血：收方在捐款后的 90 拍里 cmds 不变（一条指令都没发）而且在丢地。送过去的兵只是被对面当成防守兵力磨掉。",
        "detectionSketch": "对每笔捐款取收方捐款前最近快照与 ≥90 拍后的第一个快照：cmds 相同且 terr 下降。记笔数、名义到账、手续费。",
    },
    "R07-EC-NO-OUTLET": {
        "category": "EC",
        "definition": "有地有兵的号长期 nb=0（四周只有队友和海）且所有出兵口都关着：捐款密度没到阀门（内陆 72 / 沿海 76.8，救援 106），或候选收方都被过滤掉"
                      "（t>2200 后没有敌邻且没有攻防的队友不算候选，领土 <600 的也不算）；闲置船不打 ≥2,500 格的真人。兵只进不出，直到超过软上限。",
        "detectionSketch": "42_patterns.py：同一个号（领土 ≥1000）连续 ≥10 个快照 nb=0&neut=0、cmds 不变、余额不降。策略停摆的号也会命中，要对照 R07-IO-CRASH 排除。",
    },
    "R07-EC-NEUT-LOCK": {
        "category": "EC",
        "definition": "没有敌邻的号贴着 1~5 格零碎中立地，既不吃也不出海。t<1500（dpEnd）时中立地走 dpNeutral：`X = 2*sum + rings[n-1].r`，"
                      "X 小于 minCmd（= 4 × 进攻手续费，随余额增长）就不发；而开局阶段的 act 在 `this.neutral > 0` 时直接 return，走不到发船那一段。"
                      "结果是兵越攒越多、这几格地越不值得发指令，一直卡到 t=1500 换成核心逻辑为止。",
        "detectionSketch": "42_patterns.py：同一个号（领土 ≥1000）连续 ≥3 个快照 nb=0、1≤neut≤5、cmds 与领土都不变。",
    },
    "R07-GOOD-SAVED-PUSH": {
        "category": "AT",
        "definition": "（正例）用自己攒的兵一次换成地：≤3 个连续窗口领土 +≥30% 且 ≥1,500 格，起点密度 ≥20，期间没有收到捐款。",
        "detectionSketch": "42_patterns.py：traj 连续 1~3 个 90 拍窗口 terr 增量 ≥ max(1500, 0.3·terr0) && dens0 ≥ 20 && 窗口内没有以该号为收方的 DONATE/DISPATCH。",
    },
    "R07-GOOD-BOXED-BOAT": {
        "category": "SE",
        "definition": "（正例）被围死的号（nb=0&neut=0）靠船解套：540 拍内领土 +≥max(1000, 20%)，同期 boats 计数增加。",
        "detectionSketch": "42_patterns.py：traj 中某号 nb==0&&neut==0 的快照之后 ≤540 拍内出现 terr 增量 ≥ max(1000, 0.2·terr0) 且 boats 计数更大的快照（每号记第一次）。",
    },
    "R07-GOOD-FED-PUSH": {
        "category": "AT",
        "definition": "（正例）前线号在队友持续供兵的情况下把兵换成地：连续窗口领土净增 ≥ 10%，余额不降。",
        "detectionSketch": "traj 连续两个窗口 dTerr 合计 ≥ 10%·terr0 且 bal 末 ≥ bal 初；窗口内有收到的捐款。",
    },
    "R07-GOOD-OPENING-DP": {
        "category": "OP",
        "definition": "（正例）开局按地租周期整圈扩张（[HL-OPENING] DP expand），8/10 个号在 t≈220 的 OPENING-CHECK 全部 OK，t=1530 前把周边中立地吃完。",
        "detectionSketch": "opening.csv 每号 ≥8 条 HL-OPENING；OPENING-CHECK 行全部 (OK)。",
    },
    "R07-GOOD-INTERCEPT": {
        "category": "SE",
        "definition": "（正例）拦截敌方登陆船：[HL-INTERCEPT] 用很小的 pct 把敌船打掉，停摆期间海岸线仍守住。",
        "detectionSketch": "events.csv type=INTERCEPT 的条数与 boatTroops；对应号的领土在该段没有明显下降。",
    },
    # ---- A 组（有回放的局）新增：检测依赖 60_truth.cjs / 63_replay_ledger.py / 64_cmd_loss.py / 65_shadow.mjs ----
    "R07-IO-LAG-BATCH": {
        "category": "IO",
        "definition": "客户端本地进度落后于服务器（几十到几百拍），发出的指令晚到、挤在同一拍成批落地；每条都按落地那一拍的余额重新按比例计价，"
                      "而策略每个决策拍（5 拍）看不到在途指令、照旧再发一条，于是 N 条同比例指令一起落地时一拍花掉 1−(1−p−1.17%)^N 的余额。晚到太久的进攻落地时目标已死，录像里记成打无主地。",
        "detectionSketch": "64_cmd_loss.py：影子想发 vs 录像收下逐条配对（延迟、没被收下的条数、同一拍 ≥3 条的批数）＋按 in_game.log 落盘先后量本地落后拍数；63_replay_ledger.py E 节列出每一批的批前/批后余额。",
    },
    "R07-IO-SEAT-LOST": {
        "category": "IO",
        "definition": "客户端掉线：席位先空转（不发指令、照常吃利息），几百拍后被引擎判为离开（state=2：利息归零、内置 AI 接管）。AI 接管的地密度趋近 0，之后被邻居低价吃掉。"
                      "结算表里记 event=left，不是阵亡。",
        "detectionSketch": "60_truth.cjs 的 truth_bots.tsv：state 第一次变 2 的拍；truth_cmd.tsv：该号最后一条被接受的指令；61_truth_view.py C/D 节：出局拍与进攻方。",
    },
    "R07-DN-QUOTA-OVERSIZE": {
        "category": "DN",
        "definition": "调度捐款按捐方余额的固定比例定额（围死号 pct=320≈31.3%，最低 180），不看收方的防喂兵配额。单笔所需点数超过收方剩余额度（t<2142 时甚至超过全场上限）就被引擎在扣款前拒绝："
                      "录像里没有这条指令，捐方余额不变；策略不检查是否成功，只按 12 拍冷却 + 25 拍相位重发。结果是围死的储备号顶着上限反复发、几乎都被拒。",
        "detectionSketch": "63_replay_ledger.py：[HL-DISPATCH] 日志条数 vs 录像 donate 条数；未执行的日志按「单笔需点 > 全场上限」「需点 > 剩余额度」分类（需点/上限按 engine-evidence [B2]~[B5] 的整数公式算）。",
    },
    "R07-EC-HARDCAP": {
        "category": "EC",
        "definition": "余额顶在 150×领土（硬上限，利息为 0）。常见于围死的储备号：没有敌邻、没有中立地、没有海岸，捐款又被配额拒绝。",
        "detectionSketch": "42_patterns.py 的快照计数（90 拍粒度）；63_replay_ledger.py D 节按 10 拍采样给出硬上限/软上限以上的持续拍数。",
    },
    "R07-DN-INVERTED": {
        "category": "DN",
        "definition": "调度时捐方密度低于收方密度（低密向高密输血）。围死号的余粮分支只要求捐方密度 ≥58、收方密度 ≤128（有推进/有猎物时 ≤140），不比较两边谁更密。",
        "detectionSketch": "in_game.log 的 [HL-DISPATCH] 行里 dMe < dAlly 的条数；是否真的执行看 63_replay_ledger.py 的逐笔表。",
    },
    "R07-MT-NOFULL-LOCK": {
        "category": "MT",
        "definition": "`isNoFullSend` 被误锁：出兵后的 1~6 拍内余额因为别的原因下降（挨打掉兵、更早的指令晚到），updateShadowQuota 把它当成「引擎没让我发全额」，把标记永久置真。"
                      "之后对真人的出兵要先等影子额度回满，不够就整条不发（或改成 1 兵试探）。",
        "detectionSketch": "65_shadow.mjs 的 shadow_nofull.tsv：影子策略里标记第一次置真的拍与当时的待核对出兵、之后被挡掉/改成试探的出兵（前提：影子日志与真日志逐条对得上，见 shadow_check.txt）。",
    },
    "R07-SP-SWAP-CHURN": {
        "category": "SP",
        "definition": "出生阶段协调器反复重算，在最后几拍把两个号在两个点位之间来回对调，每个号发出 20 条以上出生指令；最后一条如果丢了或晚到，两个号会落在同一个点。",
        "detectionSketch": "录像命令流 cmds.tsv 里 kind=spawn 的条数/号与最后 10 拍的目标格序列；in_game.log 的 [HL-SPAWN-BACKEND] 行。",
    },
    "R07-SP-OVERLAP": {
        "category": "SP",
        "definition": "两个号实际出生在同一个点（真实落点相距 < 15 像素）：两个号生效的最后一条出生指令指向同一格，引擎把后到的挪开几格；"
                      "协调器最后指派给其中一个号的点位空着。",
        "detectionSketch": "66_spawn_truth.mjs：按录像重演到出生阶段结束，各号领土包围盒中心两两求距离；对照日志里最后一条 [HL-SPAWN-BACKEND] 指派与录像里最后一条出生指令。",
    },
}


def np(name, instances, note=""):
    d = PATTERN_DEFS[name]
    out = {"name": name, "category": d["category"], "definition": d["definition"], "detectionSketch": d["detectionSketch"], "instances": instances}
    if note:
        out["note"] = note
    return out
