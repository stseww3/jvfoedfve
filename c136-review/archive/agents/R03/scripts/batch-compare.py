#!/usr/bin/env python3
"""batch-compare.py — 把已完成的逐局复盘 JSON 里的机械计数并排列出来（跨局对照用）。

只读 reviews/<mid>.json（mkreview.py 的产物），不重算；每个数的出处是 JSON 里的字段名，写在表头。
用法：python3 batch-compare.py [mid ...]      # 不给参数就列 reviews/ 下全部
输出：标准输出；--out 写到 out/batch-compare.txt
"""
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def g(d, *path, default=None):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "-"


def wan(x):
    return f"{x / 10000:.0f}万" if x is not None else "-"


def row(mid):
    d = json.load(open(os.path.join(ROOT, "reviews", f"{mid}.json"), encoding="utf-8"))
    el = d.get("execLayer") or {}
    per = el.get("perBot") or {}
    issued = sum((v.get("issued") or 0) for v in per.values())
    executed = sum((v.get("executed") or 0) for v in per.values())
    mis = el.get("misfire") or {}
    rei = el.get("reissueBeforeExec") or {}
    nfs = el.get("nfsFlips") or {}
    crowd = el.get("sameTickRejected") or {}
    fz = g(d, "openingFreeze", "team") or {}
    core = g(d, "coreDecisionTicks", "team") or {}
    da = d.get("donationAudit") or {}
    ie = g(d, "interestEfficiency", "phases") or []
    mid_phase = next((p for p in ie if p.get("from") == 1500), None)
    verd = {}
    for x in d.get("decisions") or []:
        verd[x.get("verdict")] = verd.get(x.get("verdict"), 0) + 1
    led = d.get("squadLedger") or {}
    tl = d.get("timeline") or []
    peak = max((p.get("sqSharePct") or 0) for p in tl) if tl else None
    return {
        "mid": mid,
        "arch": d.get("lossArchetype"),
        "end": g(d, "outcome", "endTick"),
        "teams": g(d, "context", "teams"),
        "bots": g(d, "context", "bots"),
        "ver": (g(d, "context", "strategyVersion") or "")[:2],
        "peakSq": peak,
        "freeze": f"{fz.get('frozen', '-')}/{fz.get('ticks', '-')}" if fz else "-",
        "freezeSquad": g(fz, "frozenBy", "squad", default="-"),
        "noai": fz.get("noai", "-") if fz else "-",
        "core": f"{core.get('noOffer', '-')}/{core.get('ticks', '-')}" if core else "-",
        "corePct": pct(core.get("noOffer", 0), core.get("ticks", 0)) if core else "-",
        "pricedHigh": core.get("pricedHigh", "-") if core else "-",
        "issued": issued, "executed": executed, "execPct": pct(executed, issued),
        "late30": mis.get("late30", "-"), "dead": mis.get("deadTarget", "-"), "dup": mis.get("dupInBatch", "-"),
        "syncBursts": rei.get("syncBursts", "-"), "syncFirst": wan(rei.get("syncFirst")), "syncExtra": wan(rei.get("syncExtra")),
        "nfs": f"{len(nfs)}号/{sum((v.get('blockedSends') or 0) for v in nfs.values())}次",
        "crowd": f"{crowd.get('total', '-')}（真人 {crowd.get('withHumanTarget', '-')}）",
        "don": f"{da.get('exec', '-')}/{da.get('logged', '-')}",
        "donQuota": da.get("quota", "-"),
        "donAmt": wan(da.get("amount")), "donFee": wan(da.get("fee")),
        "donFeePct": pct(da.get("fee") or 0, da.get("amount") or 0),
        "intMid": pct(mid_phase["income"], mid_phase["incomeAtSoftCap"]) if mid_phase else "-",
        "hardTicks": mid_phase.get("ticksAtHardCap") if mid_phase else "-",
        "drop30": g(d, "drop30", "count"),
        "dropDon": g(d, "drop30", "byMainCause", "捐款", default=0),
        "dropHit": g(d, "drop30", "byMainCause", "挨打", default=0),
        "verd": f"对{verd.get('good', 0)}/错{verd.get('error', 0)}/不明{verd.get('unclear', 0)}",
        "ledger": bool(led),
    }


COLS = [
    ("mid", "局"), ("ver", "版本"), ("arch", "分型（lossArchetype）"), ("end", "结束拍"), ("teams", "队数"), ("bots", "号数"),
    ("peakSq", "时间线里编队份额最大值%"),
    ("freeze", "600~1500 拍 safeFinite 冻结/决策拍（openingFreeze.team）"), ("freezeSquad", "其中卡在编队友"), ("noai", "没有 AI 邻居"),
    ("core", "t≥1500 四周无可打邻居/决策拍（coreDecisionTicks.team.noOffer）"), ("corePct", "占比"), ("pricedHigh", "报价≥worth"),
    ("issued", "本地发令（execLayer.perBot.issued）"), ("executed", "成交"), ("execPct", "成交率"),
    ("late30", "成交里延迟>30 拍"), ("dead", "落地时目标已死"), ("dup", "同一决定重复落地"),
    ("syncBursts", "首条成交前重发的串（reissueBeforeExec.syncBursts）"), ("syncFirst", "首条合计"), ("syncExtra", "多发合计"),
    ("nfs", "isNoFullSend 翻转号数/被挡次数"), ("crowd", "同拍被挤掉（sameTickRejected）"),
    ("don", "调度成交/日志（donationAudit）"), ("donQuota", "额度拒"), ("donAmt", "到账"), ("donFee", "税"), ("donFeePct", "税/到账"),
    ("intMid", "1500~4284 实得利息/软上限口径"), ("hardTicks", "同段贴硬上限的号·拍"),
    ("drop30", "DROP30 区间数"), ("dropDon", "主因捐款"), ("dropHit", "主因挨打"), ("verd", "决策判定"),
]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mids = args or sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, "reviews")) if f.endswith(".json"))
    rows = [row(m) for m in mids]
    lines = ["batch-compare：" + " ".join(mids), ""]
    for key, title in COLS:
        lines.append(f"{title}")
        lines.append("    " + " | ".join(f"{r['mid']} {r[key]}" for r in rows))
    text = "\n".join(lines) + "\n"
    sys.stdout.write(text)
    if "--out" in sys.argv:
        with open(os.path.join(ROOT, "out", "batch-compare.txt"), "w", encoding="utf-8") as f:
            f.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
