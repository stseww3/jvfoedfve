#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""108_closure_mismatch.py — R07：C2（历史实录轨迹）不扰动时为什么有几局不能逐拍复现历史。

C2 在历史原位置执行的是影子策略发的指令，不是录像里那一条。两者逐条对齐后（101_release_map.py 的对法），
把录像里每条落地的指令分成：
  完全相同
  目标不同，但影子的目标在落地时已经死了：引擎对「打一个已死的玩家」本来就按打空地处理，与录像等价
  目标不同，影子的目标落地时还活着（录像里落地的是打空地）：不等价
  其他目标不同 / 比例或种类不同 / 影子发令里找不到对应：不等价
输出每局、每个观察窗里各类的条数，以及第一条不等价指令的落地拍，和 C2 种子 0 第一处与历史不同的记录拍放在一起。

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
KINDS = ["exact", "deadEq", "aliveNeutral", "otherTarget", "mis", "unmatched"]
NAMES = {"exact": "完全相同", "deadEq": "目标已死，按空地算（等价）", "aliveNeutral": "目标还活着，录像里是空地", "otherTarget": "其他目标不同",
         "mis": "比例或种类不同", "unmatched": "影子发令里找不到对应"}

spec = importlib.util.spec_from_file_location("rm", os.path.join(HERE, "101_release_map.py"))
rm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rm)


def classify(mid):
    h = json.load(open(os.path.join(OUT, "_cache", "cp", mid, "H.json"), encoding="utf-8"))
    death = h["deathAll"]
    intents = collections.defaultdict(list)
    for t, b, kind, pct, target, rej in h["intents"]:
        if not rej:
            intents[b].append((t, kind, pct, target))
    landed = collections.defaultdict(list)
    for r in h["landed"]:
        if r[2] != "leave":
            landed[r[1]].append(r)
    ev = []   # (落地拍, 号, 类别)
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
                ev += [(T, b, "unmatched")] * len(L)
                continue
            for a, ii in zip(L[::-1], range(j, j + len(L))):
                c = rm.cost(a, I[ii])
                if c == 0:
                    ev.append((T, b, "exact"))
                elif c >= 1:
                    ev.append((T, b, "mis"))
                else:
                    tgt = I[ii][3]
                    if a[2] == "attack" and a[4] >= 512 and isinstance(tgt, int) and 0 <= tgt < 512:
                        d = death[tgt]
                        ev.append((T, b, "deadEq" if 0 <= d <= T else "aliveNeutral"))
                    else:
                        ev.append((T, b, "otherTarget"))
    ev.sort()
    return ev


def main():
    J = json.load(open(os.path.join(CROSS, "checkpoint_attribution.json"), encoding="utf-8"))
    L = ["# C2 不扰动时与历史的差别从哪来：录像里落地的指令 vs 影子策略在同一位置发的指令（108_closure_mismatch.py）",
         "# 「不等价」= 目标还活着而录像里是空地 + 其他目标不同 + 比例或种类不同 + 影子发令里找不到对应", ""]
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
            c = collections.Counter(k for t, _, k in ev if a < t <= b)
            n = sum(c.values())
            bad = [t for t, _, k in ev if a < t <= b and k in ("aliveNeutral", "otherTarget", "mis", "unmatched")]
            cl = (J.get("closure") or {}).get(f"{g}@{a}")
            fd = "未跑" if cl is None else ("没有" if cl["firstDiff"] is None else cl["firstDiff"])
            L.append(f"{g}\t{n}\t" + "\t".join(str(c[k]) for k in KINDS) + f"\t{len(bad)}\t{bad[0] if bad else '没有'}\t{fd}")
            res[g][f"{a}_{b}"] = dict({k: c[k] for k in KINDS}, n=n, bad=len(bad), firstBad=bad[0] if bad else None)
            tot[(a, b)].update(c)
            tot[(a, b)]["n"] += n
            tot[(a, b)]["bad"] += len(bad)
        t = tot[(a, b)]
        L.append(f"合计\t{t['n']}\t" + "\t".join(str(t[k]) for k in KINDS) + f"\t{t['bad']}\t\t")
        res.setdefault("all", {})[f"{a}_{b}"] = dict({k: t[k] for k in KINDS}, n=t["n"], bad=t["bad"])
        L.append("")
    for g in GAMES:
        res[g].pop("_ev", None)
    open(os.path.join(CROSS, "closure_mismatch.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(res, open(os.path.join(CROSS, "closure_mismatch.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()
