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


def pat(pid, instances, note, extra_same=None):
    d = DEFS[pid]
    return {"proposedId": pid, "prefix": d["prefix"], "name": d["name"], "sameAs": list(d["sameAs"]) + list(extra_same or []),
            "definition": d["definition"], "detect": d["detect"], "instances": instances, "note": note}
