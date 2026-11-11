# 本人（R03）提出的模式的统一定义：每局的 notes 只填实例和本局计数，定义文字只在这里写一遍。
# 前 6 条的定义原样取自 notes/A051.py（第一局写的那份），后面是之后各局新增的。
import importlib.util
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def _a051_defs():
    spec = importlib.util.spec_from_file_location("notes_A051_defs", os.path.join(_HERE, "A051.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {p["proposedId"]: {k: p[k] for k in ("prefix", "name", "sameAs", "definition", "detect")} for p in mod.NOTES["newPatterns"]}


DEFS = _a051_defs()

DEFS["NEW-R03-EC01"] = {
    "prefix": "EC",
    "name": "被围的后排号被调度抽到 22~34 兵/格：利息基数没了，接敌时又薄",
    "sameAs": ["NEW:DN-dying-donor（R06，可能相近：捐完变薄随后被吃）", "R08:出手后变薄，随后被吃（那条说的是进攻后变薄，这条是捐款后）"],
    "definition": "源码 L4355 的 boxedIn（没有敌邻、nb=0、neutral=0）为真的号，在一次或多次 tryDonateToTeammate 之后余额密度连续 ≥600 拍低于 40。"
                  "计：号·拍数；这些拍上的实得收入与「同样的地一直贴着软上限」口径的比值；该号此后第一次被真人进攻时的密度，以及对手吃它每格花的兵。",
    "detect": "dossier.py [P]（逐号分段的平均密度、实得收入/软上限口径收入）+ [E]（捐出笔数与金额）+ [F]/[G]（开打时密度、对手每格花费）；"
              "donate-why.mjs 给出每次调度走的是紧急档（留底 22/32×领土）还是产出档（34/44×领土）。",
}

DEFS["NEW-R03-AT02"] = {
    "prefix": "AT",
    "name": "接敌后捐款门槛低于出手门槛：余额每涨过 108 兵/格就被捐走，对唯一的真人邻居始终不出手",
    "sameAs": ["NEW:AT-worth-gate（R06，价格线不出手）", "NEW:DN-small-pct（R06）/ R08:小额捐款税大于到账（捐的那一半）"],
    "definition": "非 boxedIn 的号只有 1 个真人邻居且报价 ≥ worth。出手要过的闸：没过软上限时 L5359 直接 break；过了软上限还要 B ≥ overHumanCap×100×领土"
                  "（L5361-5365「唯一健康缓冲」，本版 1.28），并且余额高于 overHumanKeep×100×领土 的保留线（L5440-5444，本版 1.12）；余额低于 88×领土（safeAt 的封顶 oppFloorCap）时还有留底这一道。"
                  "而 tryDonateToTeammate 在 dMe ≥ 108（产出档 L4479-4481）或 ≥ 102（紧急档 L4465-4466）就放行，按 92×领土（紧急档 88×领土）的留底算 pct，税不在算术里，捐完落到 81~88 兵/格。"
                  "计：该号在这种状态下连续的捐款笔数、到账与税，以及期间对那个邻居的出手次数。",
    "detect": "donate-why.mjs（boxedIn 为假时的 sent 笔数与 pct）+ dbg/buy-why.mjs（同一段每个决策拍去掉哪一道闸、或哪几道闸的组合才会出手）+ freeze-scan 第二段的 pricedHigh/pricedOther。",
}

# ---- A066 起新增 ----
DEFS["NEW-R03-IO03"] = {
    "prefix": "IO",
    "name": "同一拍先发的扩中立占掉指令位，后面对真人/AI 的出手本地就被拒",
    "sameAs": ["统筹 0004 号广播第 ii 项（页面适配层每拍只收 1 条：Policy.act L4941 expandNeutral 挤掉 L4942 buyLand）"],
    "definition": "影子策略同一个决策拍里已有一条被接受的指令（源码行 expandNeutral:952 或 dpNeutral:2406），同拍由 buyLand / General.act:796 发出的另一条在本地被拒收。"
                  "计：条数、t≥1500 的条数、目标是真人的条数、同一目标连续被挤的拍数，以及被挤掉的那条想发的兵。",
    "detect": "shadow-digest.py [S7]（shadow.json 里每条影子指令的本地受理标志 + 调用栈）；facts 里是 crowd.{n,after1500,humanTarget,list}。",
}

DEFS["NEW-R03-SE02"] = {
    "prefix": "SE",
    "name": "被围号的远程船：选落点不计航程，兵在海上衰减、被敌船打沉，没有靠岸",
    "sameAs": ["统筹 0005 号广播第 ⑥ 项（idleBoats 选目标不计航程）", "R05 远程船：兵在海上耗掉或落到不能打的地方", "NEW:BT-sunk（R06）"],
    "definition": "Policy.idleBoats（L5019-5044）在 nb=0、neutral=0 且自身密度 ≥115（L5031）时，把 boatRange 临时放到 2500、maxEff 传 Infinity 去调 boatOut（L5038-5040）；选中的落点航线 ≥300 像素。"
                  "引擎里船每拍约走半个像素（moveBoats L289-326；被打中后的 4 拍只走 0.04 像素），每 5 拍掉 v>>7（decayBoats L360-366），"
                  "奇数拍与 7.5 像素内的敌船互打（fightBoats L328-358；FIGHT_RANGE2=14400 子格²，1 像素=16 子格）。"
                  "计：船数、出港兵、船费（余额的 32/1024）、在海上的拍数、靠岸时剩下的兵（没靠岸记 0）、被敌船打到的拍数。",
    "detect": "dbg/boat-life.mjs <局> <席位列表> [t0] [t1]（真值重演逐条船：航线段数与像素长度、每 100 拍的兵数与位置、被敌船打到的拍数与对方船主、消失拍、有没有 landAt 记录）。",
}

DEFS["NEW-R03-AT03"] = {
    "prefix": "AT",
    "name": "几个号围着同一个薄真人，各算各的预算，谁都迈不过 chunk 闸",
    "sameAs": ["NEW:AT-worth-gate（R06，价格线不出手；这条是价格线以下也不出手）", "R07-EC-IDLE-RICH（相近）"],
    "definition": "≥2 个编队号与同一个真人接壤，该真人的余额小于这几个号余额之和；每个号的 buyLand 都没出手，dbg/buy-why 的分类是 chunk"
                  "（报价低于 worth，但 L5424 按 (worth−报价)×领土 算出的预算 x 既 < want=1.25×need+3×接壤格，又 < chunk×余额，L5613 continue；本版 chunk=0.2、pplKill=0）"
                  "或 worth（报价 ≥ worth，L5359 break）；持续 ≥300 拍。计：涉及的号数、各自被 chunk / worth 拦的决策拍数、期间目标密度的变化、最后出手时每格花的兵。",
    "detect": "dbg/buy-why.mjs <局> <号> <t0> <t1>（逐决策拍：单独去掉哪一道闸会走到 send）+ 重放快照里目标的地/兵 + pairLog 里各号对它的得地与烧兵。",
}

DEFS["NEW-R03-EX01"] = {
    "prefix": "EX",
    "name": "离线空壳把全部余额送给队友（引擎规则，录像和日志里都看不到）",
    "sameAs": ["NEW:IO-disconnect-husk（R06，说的是我方号掉线变空壳；这条是空壳往外送兵）"],
    "definition": "真人离线后由内置 AI 接管。它在陆上没有可打的目标、发不了船、翻不了山时走 botDonate（bots.js L180-200）：真人席位给的是全部余额（L185），手续费 64/1024（game.js transfer L388-395），"
                  "不占受捐额度，只受接收方硬上限 150×领土 的余量限制；接收方按随机起点在同队里找第一个「最近在交战」（recentWar）的号，没有就找「有船在海上」的号。"
                  "计：送给本编队的次数与到账、把接收方顶到硬上限的次数、接收方随后 300 拍内把这笔兵转捐出去的金额与税；敌方各队同类到账。",
    "detect": "resim.mjs 的 botGifts（挂在引擎 botGive 上）→ dossier.py [L]「表外进项」、[N]「表外」；dbg/husk-gifts.mjs <局> 单独列全场。",
}

DEFS["NEW-R03-DN02"] = {
    "prefix": "DN",
    "name": "捐款被接收方的硬上限截短：税按捐出方整笔余额收，到账只有对方剩下的余量",
    "sameAs": ["NEW-DN-14（R08，喂给已经超软上限的号；这条说的是到账被截短、税照收）", "NEW-R01-DN10（相近：yield_opt_dispatch 落地后双方利息合计下降）"],
    "definition": "引擎 transfer（game.js L388-400）：税 = 捐出方余额的 64/1024，与实际到账无关；到账 = min(指令兵数, 接收方 150×领土 − 余额)（receiverRoom L340-345）。"
                  "tryDonateToTeammate 算 pct 时（L4500-4505）只看自己的留底，不看对方还能收多少。"
                  "一笔捐款的到账比指令兵数（(pct+1)/1024×捐出方余额）少 1 个兵以上记为被截短。计：笔数、到账、税、税/到账（没被截短的 pct 320 捐款是 0.20）、接收方落地后的密度。",
    "detect": "pingpong.py <局>（只读重放 cmdLog 的捐款行：逐对的笔数/到账/税、接收方落地前后密度、顶到硬上限与被截短的笔数）。",
}

DEFS["NEW-R03-SE03"] = {
    "prefix": "SE",
    "name": "扫尾分支发船不设间隔、找落点不看在途的船：同一个小岛连发几条，后面的船靠在自己刚打下的地上",
    "sameAs": ["NEW-SE-06（R08，扫尾船被在途上限卡住、先挑最大的岛；这条是同一落点的重复船）", "NEW:BT-own-shore（R06，船靠回自己的岸，白付 32/1024）", "NEW-R01-SE04（装兵比船费少的小船）"],
    "definition": "Policy.idleBoats 的扫尾分支（L5045-5052）每个决策拍都调 boatOut，没有被围分支 L5033 那样的间隔检查；boatOut（L999-1015）只看页面上的 boatCount < maxBoats（本地船数比发令晚 7~20 拍才变），"
                  "searchWater（L1020-1079）每次从头找，不记已经在路上的船。同一个号对同一落点、相邻间隔 ≤60 拍的发船并成一串，串里第一条之外的记为多余。"
                  "计：串数、多余条数、多余船的船费（每条 = 当时余额的 32/1024，与装兵无关）、靠岸时落点已是自己的地的条数。",
    "detect": "boat-audit.py <局> [--cuts ..] [--burst 60]（重放 cmdLog 的发船行按 dZ 同落点分串 + landings 按落点归属分类）；dbg/idle-boats.mjs <局> <号> <t0> <t1>（影子逐决策拍归类：哪个分支、被哪一道拦、落点水路步数与岛的大小）。",
}

# ---- A067 起新增 ----
DEFS["NEW-R03-AT04"] = {
    "prefix": "AT",
    "name": "同队任何一个号（含路人）在打某一队的真人时，全编队对其它队真人的报价整体 ×1.45",
    "sameAs": ["暂无对应条目（R03 在 A067 第一次看到；请统筹归并）"],
    "definition": "Policy.offers（Vb L5186-5199）把全队——路人队友和编队号——所有进攻槽的目标所在的队收进 engagedTeams；L5214-5216："
                  "engagedTeams 非空、报价对象所在的队不在其中、对象没有在打我、也不是 nearCollapse，且前面几档「队友正在打它」的折扣都没命中时，报价 c 与 rankMult 各 ×1.45。"
                  "窗口 = 某个队友对另一队真人的进攻槽存在的那一段。计：窗口数与起因（哪个号哪一拍对谁的哪条指令）、窗口里各号对其它队目标的报价跳变（相邻两个决策拍 c 的比值，need 不变）、"
                  "窗口里因此不出手的决策拍数（dbg/buy-why 的分类）。",
    "detect": "acts.py <局> <号> <t0> <t1>（逐决策拍报价：同一目标相邻两拍 c 的比值 ≈1.45 而 need 不变）+ cmdq.py <局> <路人席位> <t0> <t1> --kind 1（那一拍哪个队友对哪个队的真人落了一条进攻）"
              "+ dbg/buy-why.mjs（跳变后被哪一道闸拦）。",
}

DEFS["NEW-R03-SE04"] = {
    "prefix": "SE",
    "name": "船靠在编队友的岸上：按捐款移交，对方额度或硬上限装不下的整条蒸发",
    "sameAs": ["NEW-R03-SE01（船靠路人队友的岸，整船并入对方余额；这条是靠编队友的岸、被额度拒收）", "NEW:BT-own-shore（R06，船靠回自己的岸）", "统筹 0005 号广播第 ⑥ 项（船）"],
    "definition": "引擎 src/sim/sim/boats.js landAt L262-285：船靠岸时落点属于队友 → receiverRoom（对方 150×领土 的余量）截短后调 bookDonation（占对方的受捐额度，整条要么全收要么不收），"
                  "不收的兵直接消失（源码注释：what the quota or the 150 x land cap refuses is lost at sea）。"
                  "发船时落点还是 AI/无主地，船在路上或指令在页面里排队的时候被编队友打下来，就会走到这条路。"
                  "计：靠编队友岸的船数、船上兵、对方到账、蒸发的兵、船费；其中发令时落点不是队友的地的条数，以及发令→落地的延迟。",
    "detect": "dossier.py [H]「船靠队友岸移交」+ boat-audit.py（按出港时/靠岸时的落点归属分类）+ cmdq.py --kind 3 与 issueq.py（每条船的本地发令拍、落地拍、源码行）+ dbg/idle-boats.mjs（发令那一拍落点的归属）。",
}


def pat(pid, instances, note, extra_same=None):
    d = DEFS[pid]
    return {"proposedId": pid, "prefix": d["prefix"], "name": d["name"], "sameAs": list(d["sameAs"]) + list(extra_same or []),
            "definition": d["definition"], "detect": d["detect"], "instances": instances, "note": note}
