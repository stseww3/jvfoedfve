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


def pat(pid, instances, note, extra_same=None):
    d = DEFS[pid]
    return {"proposedId": pid, "prefix": d["prefix"], "name": d["name"], "sameAs": list(d["sameAs"]) + list(extra_same or []),
            "definition": d["definition"], "detect": d["detect"], "instances": instances, "note": note}
