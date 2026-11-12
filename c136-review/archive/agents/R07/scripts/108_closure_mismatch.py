#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""108_closure_mismatch.py — R07：C2（历史实录轨迹）不扰动时为什么有几局不能逐拍复现历史。

C2 在历史原位置执行的是影子策略发的指令，不是录像里那一条。两者逐条对齐后（101_release_map.py 的对法），
把录像里每条落地的指令分成：
  完全相同
  目标不同，但影子的目标在落地时已经死了：引擎对「打一个已死的玩家」本来就按打空地处理，与录像等价
  目标不同，影子的目标落地时还活着（录像里落地的是打空地）：不等价
  其他目标不同 / 比例或种类不同 / 影子发令里找不到对应：不等价
  赠兵（donFlip）：录像里落地并生效，而影子在发令那一拍判定「额度不够」。离线通道对这种发令按「不发」处理，
    录像里它却发了出去，落地时额度已经放宽（规则换档的 2142 / 3213 / 4284 拍，或每 100 拍一次的额度增加）：不等价
输出每局、每个观察窗里各类的条数，以及第一条不等价指令的落地拍，和 C2 种子 0 第一处与历史不同的记录拍放在一起；
另列整局里 donFlip 的每一条。

读：out/_cache/cp/<局>/H.json、out/_cross/checkpoint_attribution.json（103 的 closure）
写：out/_cross/closure_mismatch.txt / .json
用法：python3 108_closure_mismatch.py
"""
import collections
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
CROSS = os.path.join(OUT, "_cross")
GAMES = ["A007", "A033", "A039", "A053", "A061", "A062", "A070", "A079", "A082", "A089", "A091"]
WINDOWS = [(0, 1500), (630, 1530), (1500, 2400), (4284, 5184)]
KINDS = ["exact", "deadEq", "aliveNeutral", "otherTarget", "mis", "donFlip", "unmatched"]
NAMES = {"exact": "完全相同", "deadEq": "目标已死，按空地算（等价）", "aliveNeutral": "目标还活着，录像里是空地", "otherTarget": "其他目标不同",
         "mis": "比例或种类不同", "donFlip": "赠兵：发令时额度不够、落地时够了", "unmatched": "影子发令里找不到对应"}
BAD = ("aliveNeutral", "otherTarget", "mis", "donFlip", "unmatched")
DON_STEPS = (2142, 3213, 4284)   # 引擎里赠兵额度规则换档的时点（sim/game.js 的 donationCost / donationFree）

spec = importlib.util.spec_from_file_location("rm", os.path.join(HERE, "101_release_map.py"))
rm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rm)


def don_gate(t_issue, t_land):
    """赠兵额度在发令拍和落地拍之间放宽过没有：规则换档的时点（2142 / 3213 / 4284 拍），或每 100 拍一次的额度增加（拍号尾数 99）。"""
    for th in DON_STEPS:
        if t_issue < th <= t_land:
            return f"规则换档（{th} 拍）"
    k = (t_issue // 100) * 100 + 99
    if t_issue <= k < t_land:
        return f"额度增加（{k} 拍）"
    return "其他"


def classify(mid):
    """返回 [(落地拍, 号, 类别, 指令种类, 备注, 对上的影子发令拍或 None)]。
    赠兵另分一类 donFlip：录像里落地并生效的赠兵，影子在发令那一拍判定「额度不够」（离线通道按不发处理）。"""
    h = json.load(open(os.path.join(OUT, "_cache", "cp", mid, "H.json"), encoding="utf-8"))
    death = h["deathAll"]
    intents = collections.defaultdict(list)
    rejDon = collections.defaultdict(list)
    for t, b, kind, pct, target, rej in h["intents"]:
        if not rej:
            intents[b].append((t, kind, pct, target))
        elif kind == "donate":
            rejDon[b].append((t, pct, target))
    landed = collections.defaultdict(list)
    for r in h["landed"]:
        if r[2] != "leave":
            landed[r[1]].append(r)
    ev = []
    for s in h["squad"]:
        b = s["bot"]
        I = intents[b]
        fr = collections.OrderedDict()
        for r in sorted(landed[b], key=lambda x: x[0]):
            fr.setdefault(r[0], []).append(r)
        frames = list(fr.items())
        path = rm.align(frames, I)
        for k, (T, L) in enumerate(frames):
            j = path[k]
            if j < 0:
                for a in L:
                    hit = None
                    if a[2] == "donate":
                        c = [t for t, pct, target in rejDon[b] if T - 35 <= t < T and pct == a[3] and target == a[4]]
                        if c:
                            hit = max(c)
                    if hit is None:
                        ev.append((T, b, "unmatched", a[2], "", None))
                    else:
                        ev.append((T, b, "donFlip", a[2], f"{hit}|{don_gate(hit, T)}", hit))
                continue
            for a, ii in zip(L[::-1], range(j, j + len(L))):
                c = rm.cost(a, I[ii])
                ti = I[ii][0]
                if c == 0:
                    ev.append((T, b, "exact", a[2], "", ti))
                elif c >= 1:
                    ev.append((T, b, "mis", a[2], "", ti))
                else:
                    tgt = I[ii][3]
                    if a[2] == "attack" and a[4] >= 512 and isinstance(tgt, int) and 0 <= tgt < 512:
                        d = death[tgt]
                        ev.append((T, b, "deadEq" if 0 <= d <= T else "aliveNeutral", a[2], "", ti))
                    else:
                        ev.append((T, b, "otherTarget", a[2], "", ti))
    ev.sort(key=lambda e: e[:4])
    return ev


def main():
    J = json.load(open(os.path.join(CROSS, "checkpoint_attribution.json"), encoding="utf-8"))
    L = ["# C2 不扰动时与历史的差别从哪来：录像里落地的指令 vs 影子策略在同一位置发的指令（108_closure_mismatch.py）",
         "# 「不等价」= 目标还活着而录像里是空地 + 其他目标不同 + 比例或种类不同 + 赠兵发令时额度不够而落地时够了 + 影子发令里找不到对应", ""]
    res = {}
    tot = {w: collections.Counter() for w in WINDOWS}
    for a, b in WINDOWS:
        L.append(f"## 落地拍在 {a}~{b} 之间")
        L.append("局\t落地\t" + "\t".join(NAMES[k] for k in KINDS) + "\t不等价合计\t第一条不等价指令的落地拍\tC2 种子 0 第一处领土与历史不同的记录拍")
        for g in GAMES:
            ev = res.setdefault(g, {}).get("_ev")
            if ev is None:
                ev = classify(g)
                res[g]["_ev"] = ev
            c = collections.Counter(e[2] for e in ev if a < e[0] <= b)
            n = sum(c.values())
            badl = [e for e in ev if a < e[0] <= b and e[2] in BAD]
            bad = [e[0] for e in badl]
            cl = (J.get("closure") or {}).get(f"{g}@{a}")
            fd = "未跑" if cl is None else ("没有" if cl["firstDiff"] is None else cl["firstDiff"])
            L.append(f"{g}\t{n}\t" + "\t".join(str(c[k]) for k in KINDS) + f"\t{len(bad)}\t{bad[0] if bad else '没有'}\t{fd}")
            res[g][f"{a}_{b}"] = dict({k: c[k] for k in KINDS}, n=n, bad=len(bad), firstBad=bad[0] if bad else None,
                                      badList=[[e[0], e[1], e[2], e[3]] for e in badl])
            tot[(a, b)].update(c)
            tot[(a, b)]["n"] += n
            tot[(a, b)]["bad"] += len(bad)
        t = tot[(a, b)]
        L.append(f"合计\t{t['n']}\t" + "\t".join(str(t[k]) for k in KINDS) + f"\t{t['bad']}\t\t")
        res.setdefault("all", {})[f"{a}_{b}"] = dict({k: t[k] for k in KINDS}, n=t["n"], bad=t["bad"])
        L.append("")
    # 整局：录像里落地的赠兵里，影子在发令那一拍判定「额度不够」的那些（离线通道不发，录像里却生效了）
    L.append("## 整局的赠兵：录像里落地并生效、而影子在发令那一拍判定额度不够的")
    L.append("局\t号\t影子发令拍\t录像落地拍\t在途拍数\t发令到落地之间额度放宽的原因")
    flips, donAll = [], 0
    for g in GAMES:
        ev = res[g]["_ev"]
        donAll += sum(1 for e in ev if e[3] == "donate")
        for e in ev:
            if e[2] == "donFlip":
                ti, why = e[4].split("|")
                flips.append({"g": g, "bot": e[1], "issue": int(ti), "land": e[0], "why": why})
                L.append(f"{g}\t{e[1]}\t{ti}\t{e[0]}\t{e[0] - int(ti)}\t{why}")
    other = [e for g in GAMES for e in res[g]["_ev"] if e[3] == "donate" and e[2] in BAD and e[2] != "donFlip"]
    L.append(f"合计 {len(flips)} 条；整局录像里落地的赠兵共 {donAll} 条；赠兵里其他不等价的 {len(other)} 条")
    L.append("")
    res["donFlip"] = {"n": len(flips), "donAll": donAll, "donOtherBad": len(other), "list": flips,
                      "games": sorted({f["g"] for f in flips}),
                      "byWhy": dict(collections.Counter(f["why"].split("（")[0] for f in flips))}
    # 接管那一拍在途的指令：录像里实际的（发令在断面之前、落地在断面那一拍或之后）对 离线通道当作在途的条数
    #   离线通道多放行 = 影子发了、录像里始终没落地的指令被当作在途放行了；
    #   离线通道少放行 = 发令时额度不够的赠兵（donFlip）录像里在断面那一拍或之后落地，离线通道不发
    L.append("## 接管那一拍在途的指令：录像 对 离线通道（C2 种子 0）")
    L.append("局\t断面\t录像里在途并落地的（离线通道会发的）\t录像里在途并落地、离线通道不发的赠兵\t其中正好在断面那一拍落地的\t离线通道当作在途的条数\t离线通道多放行的条数")
    res["inflight"] = {}
    for g in GAMES:
        ev = res[g]["_ev"]
        for T0 in (630, 1500, 4284):
            hin = [e for e in ev if e[5] is not None and e[2] != "donFlip" and e[5] < T0 <= e[0]]
            fin = [e for e in ev if e[2] == "donFlip" and e[5] < T0 <= e[0]]
            try:
                arm = json.load(open(os.path.join(OUT, "_cache", "cp", g, f"C2-t{T0}-s0.json"), encoding="utf-8"))
                ain = arm["chanStat"].get("inflight")
            except (OSError, ValueError):
                ain = None
            extra = None if ain is None else ain - len(hin)
            res["inflight"][f"{g}@{T0}"] = {"hist": len(hin), "flip": len(fin), "flipAtT0": sum(1 for e in fin if e[0] == T0), "arm": ain, "extra": extra}
            L.append(f"{g}\t{T0}\t{len(hin)}\t{len(fin)}\t{sum(1 for e in fin if e[0] == T0)}\t{'未跑' if ain is None else ain}\t{'-' if extra is None else extra}")
    L.append("")
    for g in GAMES:
        res[g].pop("_ev", None)
    open(os.path.join(CROSS, "closure_mismatch.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(res, open(os.path.join(CROSS, "closure_mismatch.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()
