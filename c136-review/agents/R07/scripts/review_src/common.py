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
    # ---- A033 起新增：检测依赖 67_troop_flow.mjs（cmd_effect.tsv）/ 69_quota_truth.mjs / 70_team_density.py / 72_repeat_sends.py / 65_shadow.mjs ----
    "R07-DN-CAP-TRUNC": {
        "category": "DN",
        "definition": "捐款被收方的硬上限截断：引擎里到账 = min(名义额, 150×收方领土 − 收方余额)，截下的部分不扣、留在捐方手里（game.js transfer L388-400：`bal[p] = B − v − fee`，v 是封顶后的数），"
                      "而手续费仍按捐方全部余额的 6.25% 全额收取——到账越少，手续费占到账的比例越高，到账几千、手续费几万的都有。"
                      "调度逻辑只看收方密度是否低于 128~142，不看它离硬上限还剩多少空间，所以收方密度 115 以上时一笔 31% 余额的调度大半到不了账。"
                      "（船靠到队友岸上是另一回事：过不了上限或配额的兵直接丢掉，boats.js landAt L273-279。）",
        "detectionSketch": "67_troop_flow.mjs 的 cmd_effect.tsv（每条指令扣款前后的真实余额）→ 63_replay_ledger.py B 节标「顶格截断」的行：名义额、实际到账、手续费。",
    },
    "R07-AT-INFLIGHT-REPEAT": {
        "category": "AT",
        "definition": "上一条进攻还没生效就照原样再发：策略每 5 拍决策一次，指令 6~19 拍后才生效，期间 `attackTroopsOn(me,q)` 仍是 0、余额没变，于是相邻决策拍对同一目标连发 2~4 条同比例的指令。"
                      "几条一起落地后发兵合计超过吃掉整块目标所需，多出的兵压在进攻槽里（不算防守、不吃利息），目标死后转去打它留下的无主地，退回时可能撞上硬上限。",
        "detectionSketch": "72_repeat_sends.py：cmd_effect.tsv 里同一个号对同一目标、落地拍相差 ≤12 的进攻分组；组内第 2 条起的兵与手续费；发兵合计 − (1.5×目标领土 + 1.78×目标余额)。"
                           "逐拍原因看 65_shadow.mjs --trace（相邻决策拍的 need 相同）。",
    },
    "R07-AT-OVER-BURN": {
        "category": "AT",
        "definition": "只因为余额过了软上限就出兵：buyLand 里 `over = B > 100×领土` 时跳过「目标每格成本 ≥ 自己的出价就停」的判断，留底降到 0.82~0.9×100×领土，按 12% 余额一条往接壤的真人身上发。"
                      "兵多半来自队友的调度（把收方推过软上限），打的是密度比自己高的目标，净增领土很少。",
        "detectionSketch": "65_shadow.mjs --trace 的汇总行：对人 / bot 的出兵条数、其中 over=1 的条数、c>=worth 的条数与兵数、c/worth 范围；67_troop_flow.mjs C 节给每个目标的发兵合计与目标领土前后。",
    },
    "R07-AT-BOAT-FAR": {
        "category": "AT",
        "definition": "顶格之后的闲置船：没有敌邻、没有中立地的号在密度 ≥115 时把至少 24% 的可用兵装船，航程放到 2500 像素。发船费是全部余额的 3.1%，海上每拍掉兵，靠岸后打的是随便一块敌岸。",
        "detectionSketch": "67_troop_flow.mjs G 节：发船时的余额 / 密度、带兵、手续费；靠岸拍、靠岸时剩的兵、落在谁的岸上。68_watch.mjs --cmds 1 看靠岸后那次进攻换了几格。",
    },
    "R07-DF-BANK-DRAIN": {
        "category": "DF",
        "definition": "被队友围住的号按「后方银行」留底：tryDonateToTeammate 里 `boxedIn = 没有敌邻 && 没有 AI 邻居 && 没有中立地`（不看海岸、不看领土大小、不看隔着的那个队友还撑不撑得住），"
                      "协防时留底 22×领土（有海岸 32×），余粮调度时 34×（有海岸 44×），一次捐 31%~37% 余额。结果是这些号在领先期被抽到密度 20~50；隔着的队友一倒或敌船一靠岸，它们就以这个密度直接面对敌人。",
        "detectionSketch": "69_quota_truth.mjs D2 节：boxedIn=true 的调度日志与执行条数、执行时捐方 / 收方密度；70_team_density.py：我方号密度 vs 同队其他真人密度；71_death_chain.py：被打前 500 拍的密度。",
    },
    "R07-DF-DOOMED-SKIP": {
        "category": "DF",
        "definition": "挨打最重的队友被排除在协防之外：收方身上的敌兵 > 1.65×它的余额时判为「没救的口袋」直接跳过，要等敌人的这一波烧到 1.65 倍以下（这时它已经丢了一大半地）才开始调度。",
        "detectionSketch": "68_watch.mjs --step 5：逐决策拍的「压在身上的敌兵 ÷ 余额」，对照 in_game.log 里第一条指向该号的 defense_dispatch 的拍号与各捐方的 25 拍相位。",
    },
    "R07-EG-WRONG-FRONT": {
        "category": "EG",
        "definition": "领先期兵流向错的方向：全队的余粮经调度集中到一个正在打最弱一队的号身上，被它按高价打出去；同时最强的敌人在吃我方主队里不是我方号的真人，"
                      "而调度的收方只能是我方号（或 Boss），挨着那个真人的我方号没有敌邻、既不能打也不能给。",
        "detectionSketch": "67_troop_flow.mjs C 节按目标所在队汇总发兵；68_watch.mjs 盯最强敌人与被吃的队友（进攻、收捐）；70_team_density.py 的各队 / 我方 / 同队其他真人密度。",
    },
    "R07-OP-WINFLOOR-MATE": {
        "category": "OP",
        "definition": "t<1500 打内置 AI 的留底互锁（统筹广播 0004-①）：winFloor 取 safeFinite，而 safeFinite 是「这个 AI 的其他邻居里余额最小的那个」的余额——不排除队友，也不看 AI 自己有没有兵。"
                      "两个我方号夹着一个 0 兵的 AI 时，各自要求自己的余额高过对方才肯出手，谁也不动。",
        "detectionSketch": "65_shadow.mjs 的 shadow_early.txt：t=300~1499 有 AI 邻居的决策拍里，零指令拍按绑定的底线分类（safeFinite / 价格项 / dpKeep / 不让打），safeFinite 再按参照对象（我方队友 / 同队真人 / 敌方真人）分。",
    },
    "R07-SP-OVERLAP": {
        "category": "SP",
        "definition": "两个号实际出生在同一个点（真实落点相距 < 15 像素）：两个号生效的最后一条出生指令指向同一格，引擎把后到的挪开几格；"
                      "协调器最后指派给其中一个号的点位空着。",
        "detectionSketch": "66_spawn_truth.mjs：按录像重演到出生阶段结束，各号领土包围盒中心两两求距离；对照日志里最后一条 [HL-SPAWN-BACKEND] 指派与录像里最后一条出生指令。",
    },
    # ---- A039 起新增：检测依赖 74_side_flow.mjs（全场真人分组流水）/ 75_interest.py / 76_boat_targets.mjs / 65_shadow.mjs 的发令位置 ----
    "R07-OP-AI-RACE": {
        "category": "OP",
        "definition": "抢内置 AI 的地这一段（无主地吃完到 AI 的地被分完，约 t=990~1800）落后：同一个时间窗里对面的真人往内置 AI 身上发的兵是我方的两倍上下、净增领土也是两倍以上，"
                      "而我方的余额涨得比对面快——利息攒在已经没有 AI 邻居的内圈号手里，前沿的号各自的余额并不多。",
        "detectionSketch": "74_side_flow.mjs A 节（分组 × 阶段：对无主地 / 内置 AI / 真人的发兵、领土与余额的期初期末）；67_troop_flow.mjs B 节（我方每号同一阶段的进攻条数、发兵、领土）；"
                           "65_shadow.mjs 的 shadow_early.txt（每号最后一个有 AI 邻居的决策拍）。",
    },
    "R07-SE-BOAT-MATE-SHORE": {
        "category": "SE",
        "definition": "船靠到了队友的岸上：决策拍选中的是海对面的无主地或内置 AI 的岸，航行几十到几百拍之后那块地已经被队友吃掉。引擎把船上的兵当成一笔捐款交给队友，"
                      "要过收方的防喂兵额度和 150×领土上限，过不了的整船丢在海里；同一个号的两段发船逻辑（boatOut / boatFood）还会隔 5 拍各发一条去同一个点。",
        "detectionSketch": "76_boat_targets.mjs：每条船的目标格在决策拍 / 发船拍 / 靠岸拍的主人、靠岸时队友实收多少；69_quota_truth.mjs 的入账表里来源为「船」的被拒行。",
    },
    "R07-IO-ONE-CMD-DROP": {
        "category": "IO",
        "definition": "一个决策拍只有一条指令能发出去（统筹广播 0004-②）：Policy.act 先调 expandNeutral、再调 buyLand，前者发了一条打无主地之后，同一拍 buyLand 给出的第二条（多半是打真人的大单）被丢掉，"
                      "策略自己的 cmds 计数只加 1，下一拍局面变了也不一定再发。",
        "detectionSketch": "65_shadow.mjs：同一决策拍影子发出 ≥2 条指令的拍（shadow_cmds.tsv，带发令的源码行）；真日志 HL-TICK 的 cmds 与影子 cmds 的差在哪个 90 拍窗口变了；录像里该拍之后 20 拍内实际落地的指令。",
    },
    "R07-DN-NO-DONOR": {
        "category": "DN",
        "definition": "被横扫的时候没有人能捐：捐方自己身上有真人的进攻（或自己有超过 8% 余额压在打真人的进攻上）时 tryDonateToTeammate 直接返回；不是围死号的捐方还要密度 ≥102（协防）/ ≥108（余粮）。"
                      "到了全员接敌的终局，这两条把每个号都挡在外面：最后一条调度日志之后直到终局一笔调度都没有，几个握着几百万兵的号眼看着旁边的队友被逐个打掉。",
        "detectionSketch": "in_game.log 最后一条 [HL-DISPATCH] 的拍号对比终局拍；71_death_chain.py：每个出局号最后 500 拍的收捐笔数；70_team_density.py：同一时刻其余号的余额 / 密度 / 是否贴敌。",
    },
    "R07-EC-LOW-RATE-BANK": {
        "category": "EC",
        "definition": "兵存在利率最低的号里。引擎的利率只看个人领土占全图的份额（每 10 拍万分之 100 + 约 160×sqrt(份额)）：占 0.5%~2% 的内圈号是 110~121，占 17%~48% 的大号是 166~211。"
                      "我方把一大块余额放在几个小号手里（它们一格不长），对面的兵多数在一两个大号手里，同样多的兵每 10 拍生的利息差两到四成。",
        "detectionSketch": "75_interest.py：按引擎公式逐人重算利率（C 节用 tick_net.tsv 逐桶核对），分组给出余额加权利率、组内最大的号的份额 / 利率 / 余额占比。",
    },
    "R07-DF-SPENT-THEN-HIT": {
        "category": "DF",
        "definition": "刚把兵打出去就被攒着兵的邻居下重手：我方号对一个弱邻居连发几条脉冲（或一批晚到的指令同拍落地），密度掉到那个强邻居的六成以下，"
                      "100 拍之内对方用一条两成到四成半余额的进攻压上来。buyLand 的留底只按当拍接壤的真人算，新邻居一贴上来留底才跳高，这时在途的几条已经收不回。",
        "detectionSketch": "74_side_flow.mjs 的 humans_cmd.tsv（全场真人逐条指令：pct、发令前余额、目标当时领土 / 余额）里敌方 pct ≥ 190 的进攻，对照同一目标之前 100 拍内我方自己的出兵合计（cmd_effect.tsv）与出兵前后的密度；"
                           "65_shadow.mjs --trace 里 safe 一栏在新邻居出现那一拍的跳变。",
    },
    "R07-DF-AI-NIBBLE": {
        "category": "DF",
        "definition": "被 0 兵的内置 AI 一圈一圈啃而不还手。引擎里新发的进攻第一圈可以赊账（game.js expandAttack L990-1025：`fresh && counter === 0` 时不够的兵由 takeBalance 记成 debt，照样赢下这一圈），"
                      "所以余额是 0 的内置 AI 每出手一次都能拿走一圈接壤格，守方按密度掉兵。我方对内置 AI 出手也要先过按真人邻居算的留底"
                      "（buyLand `keep = max(keep, safeAt)`，safeAt 里 killKeep =（最强真人邻居的余额 − 1.5×领土）÷1.78）：真人邻居的兵比自己多一倍上下时可用兵是负的，哪怕吃掉这个 AI 只要几百兵，直到余额过软上限才出手。",
        "detectionSketch": "65_shadow.mjs 的 shadow_late_ai.txt（t≥1500 身边有内置 AI 的决策拍归类，「留底占满：真人邻居的兵」的拍数、目标格数、每格成本、当拍余额）；"
                           "68_watch.mjs --ids <AI>,<号> 看两边领土逐段变化；tick_net.tsv 的 hit 栏（挨打掉的兵）。",
    },
    "R07-DN-NOFRONT-LOOP": {
        "category": "DN",
        "definition": "全队没有一个号贴着敌人之后，「生息余粮」调度在几个沿海的围死号之间空转：tryDonateToTeammate 里没有敌邻、没有攻防的队友本来不算候选，但留了一个口子——"
                      "捐方围死且密度 ≥105、收方有海岸且密度 ≤112 就放行（L4453），随后走余粮分支按 pct=320 捐走约三成余额（L4474-4508）。收方收完过了 105 又成了捐方，再捐给下一个有海岸的号。"
                      "每一手按捐方全部余额收 6.25%，收方顶到 150×领土时到账被截、手续费照收。兵在两三个号之间来回，没有一个兵离开这个圈子，手续费吃掉大半利息。",
        "detectionSketch": "82_outlet_gap.py：A 节找出最后一个还有我方号贴着敌队真人的采样拍，D / G 节给出此后每号的利息地租、捐出 / 收到、手续费 ÷ 利息，以及调度日志的类别与 dMe / dAlly 范围；"
                           "80_donation_yield.py --span：这一段按「捐方→收方」的合计、接力笔数、落地后收方过软上限 / 顶到硬上限的笔数；63_replay_ledger.py：300 拍内来回倒手的笔数。",
    },
    "R07-SE-NEUT-BOAT-FEE": {
        "category": "SE",
        "definition": "闲置船去无主地时带兵按目标大小算、发船费按余额算：boatOut 对无主地目标取 `min(max, max(3×目标格数 + 300, 60))`，目标只有一两格时折成 pct=0，船上是余额的 1/1024，"
                      "引擎照收全部余额的 32/1024——手续费是带兵的 14~32 倍。引擎里船速随带兵增减（boats.js moveBoats），带几千兵的船只有满载的四到七成、兵越掉越慢，几百格水路要走两千拍，途中每 5 拍掉 1/128；"
                      "这些船一直占着 maxBoats 的名额，后面的决策拍都卡在「船数已满」。靠岸时那块地如果已经归了队友，剩下的兵按捐款交给他。",
        "detectionSketch": "76_boat_targets.mjs A 节：每条船的 pct、带兵（手续费）、目标格主人、航行拍数、靠岸结果；65_shadow.mjs 的 shadow_boat_gate.txt：没有邻居的决策拍按 idleBoats → boatOut → searchWater 的先后归类"
                           "（「在海上的船已到 maxBoats 上限」的拍数、每次发船的 余额 / 留底 / 上限 / 带兵 / 船费）。",
    },
    "R07-EG-SQUAD-ONLY-RECV": {
        "category": "EG",
        "definition": "领先收尾期我方的余粮到不了本队的前线：我方号都被自己人和海围住，本队还在打的是同队的其他真人；调度的收方只认我方号（名字在固定名单里）或 Boss，"
                      "同队其他真人即使密度只有二三十、离 150×领土还有几百万的空间，也不在候选里。t≥4284 引擎对任何同队捐款都不再查配额，拦住这笔兵的只有策略自己的名单。"
                      "结果是我方号密度顶在 100 上下不动，同队的大号把密度打到 20~30 去收尾。",
        "detectionSketch": "82_outlet_gap.py：B 节窗口内各组的发兵去向与捐款（给组内 / 给组外），C 节同队其他真人的密度（窗口内最低）、离硬上限的空间、打出去和挨的兵、收到的捐款及来源，"
                           "E 节我方占本队领土 / 余额的比例，F 节全场「我方号 → 同队其他真人」的捐款笔数。",
    },
    "R07-EC-SOLE-BUFFER-BANK": {
        "category": "EC",
        "definition": "只剩一个真人邻居、对方又健康的大号变成银行：buyLand 里 isSoleHealthyBuffer（场上真人 ≥3、自己只贴着一个真人、对方不濒死不失血、没在打我、打掉它会多贴上别的真人）成立时，"
                      "目标价高就要余额 ≥ overHumanCap(1.28)×100×领土 才出手，过软上限后的留底封顶也从 0.9 抬到 overHumanKeep(1.12)×100×领土；"
                      "而不是围死号的调度门槛是密度 ≥102（协防）/ ≥108（余粮），一次捐走两成上下的余额、另按全部余额付 6.25% 手续费。"
                      "于是密度每涨到 108~114 就被调度削回 82~86，永远到不了 128：这个号一条进攻不发、一格地不长，利息的两成多交了手续费，兵流到另一个队友手里。",
        "detectionSketch": "65_shadow.mjs --trace：决策拍分类里「唯一真人邻居」的拍数与当拍的 B / L / keep / avail（avail 为负），以及这段里出手的拍数；67_troop_flow.mjs B 节：该号同一窗口的进攻条数、"
                           "捐出笔数 / 到账 / 手续费、利息地租；73_front_width.py：窗口内它接壤的敌方真人只有一个；in_game.log [HL-DISPATCH] 的 dMe（108~114）；80_donation_yield.py：每笔落地前后捐方的密度。",
    },
    "R07-OP-PREY-FLOOR": {
        "category": "OP",
        "definition": "t<1500 没有内置 AI 邻居、也没有无主地的号打不了贴着的敌方真人。开局逻辑对「没有别的理由要打」的真人只走猎杀规则（preyKill=1、preyFloor=0.5）："
                      "留下一半常规留底之后，sendFrac(0.746)×可用兵要一次够吃光对方才发，差一点就一个兵都不发；可用兵还得超过 minSend(21.4%)×余额。"
                      "常规留底 floorAt 里的 defenseNeed = kDef(4)×「我的某个邻居的另一个最弱邻居」的余额，altOf 只排除目标自己和我、不排除队友——"
                      "几个号围着同一批敌人时，各自按队友余额的 2 倍留底，另外的拍数卡在价格留底（100×领土×单价/60）或 keepCap（100×领土）的一半上。"
                      "领土几百拍不动、余额越攒越高；t=1500 换成核心逻辑的那一拍这些留底一起消失，几个号同拍把兵打向同一个目标。",
        "detectionSketch": "65_shadow.mjs 的 shadow_early_humans.txt：t=300~1499 身边没有内置 AI、也没有无主地的决策拍按原因分类（留底由 defenseNeed 参照我方队友 / 敌方真人、价格留底、keepCap 定；"
                           "过了留底但一次吃不光；四周只有队友），每号最便宜的敌方真人邻居的单价与领土 / 余额，floorAt 逐项复刻并与策略自己的值核对；78_bot_share.py：这些号同期的领土与余额。",
    },
    "R07-AT-CARCASS-FLOOR": {
        "category": "AT",
        "definition": "贴着一个空壳真人（刚把全部余额压出去，或被别人打空：上万格地、家里几万兵，每格成本十几兵）却发不出指令。buyLand 对真人的留底 safe = min(killW×dpKeep, oppFloorCap(88)×自己的领土)，"
                      "dpKeep 按最强的那个真人邻居算（(它的余额 + 它压在我身上的兵 − 1.5×我的领土) / 1.78），和这一条要打的是谁无关；目标濒死时也只是把封顶降到 collapseFloorCap(85)~88×领土。"
                      "身边另有一个余额大得多的邻居时 safe 就顶在 88×领土上，自己密度不到 88 就 avail<0——要等队友的调度把余额垫过这条线才发得出一条。"
                      "这段时间那块地被第三方（常常就是那个强邻居）用一条船或一条进攻收走。",
        "detectionSketch": "85_trace_blocked.py（读 65_shadow.mjs --trace 的明细）：排第一的报价是真人、c < worth、对方密度 ≤10、结论是「无可用(avail<=0)」的决策拍数，以及 safe ÷ 自己的领土（84~88）；"
                           "68_watch.mjs --cmds 1：那个空壳是怎么空的（pct ≥ 900 的进攻）、之后谁的进攻槽压在它身上；60_truth.cjs 的 truth_all.tsv：它的地最后到了谁手里。",
    },
    "R07-GOOD-COUNTER-ALLIN": {
        "category": "DF",
        "definition": "（正例）对方把全部余额一次压上来（pct=1023）时就地反打：对方家里只剩几千兵，报价里 onMe / nearCollapse / bleeding 同时成立，need 把它压在我身上的兵也算进去，"
                      "buyLand 的 t≥3800 脉冲分支每个决策拍发一条 12% 余额的脉冲。两边进攻槽里的兵先对消，对消完剩下的直接吃地：几十拍内把对方的进攻磨光，随后吃掉它的领土。"
                      "72_repeat_sends.py 的「超出吃掉整块所需」不算对方压在进攻槽里的兵，这种组会被误标成多发。",
        "detectionSketch": "74_side_flow.mjs 的 humans_cmd.tsv：敌方 pct ≥ 900 的进攻；68_watch.mjs --cmds 1：该进攻落地后对方进攻槽逐拍的余量、我方随后的指令与双方领土；"
                           "65_shadow.mjs --trace：这些决策拍的 need / avail、报价标记（onMe / nearCollapse / bleeding）与发令行（buyLand:5585）。",
    },
}


def np(name, instances, note=""):
    d = PATTERN_DEFS[name]
    out = {"name": name, "category": d["category"], "definition": d["definition"], "detectionSketch": d["detectionSketch"], "instances": instances}
    if note:
        out["note"] = note
    return out
