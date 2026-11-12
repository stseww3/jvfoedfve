#!/usr/bin/env python3
"""seam.py — 断面接缝（会审稿 G0 的 S4 条）：断面那一拍，有多少条指令「已经决策、还没落地」。

    timeout 120 python3 c136-review/agents/R08/scripts/seam.py [--quiet]

为什么量：做断面反事实时，断面之前发出、断面之后才落地的指令归哪一边（照旧落地 / 作废），是一条必须写明的规则；
这里量历史上这样的指令有多少，好知道这条规则的分量。只量历史，不改规则、不跑新策略。

口径：
  指令 = 录像里落地的陆攻 / 捐款 / 发船（resim.json 的 cmdLog）。
  决策拍 = 影子（不落后的客户端在全场真值上逐拍跑同一份策略源码，只记不发）做出同一决策的拍；
          配对规则同 shadowcmp.py / lagledger.py（先 ≤40 拍、再放宽到 1500 拍；配不上的指令不算在途，单列条数）。
  在途 = 决策拍 ≤ 断面 T < 执行拍。
  范围 = 有主房间录像、有影子重跑的局（out/<局>/lagledger_sum.json 存在的 10 局）；录像没走到 T 的局不计。
只读 out/<局>/resim.json、shadow.json；不重演。
输出 out/_cross/seam.txt、seam.json
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from truth import Truth  # noqa: E402
import shadowcmp as SC  # noqa: E402

OUT = os.path.join(HERE, "..", "out")
CUTS = [630, 1500, 3000, 4284]
KIND = {1: "陆攻", 2: "捐款", 3: "船"}


def q(v, f):
    if not v:
        return None
    s = sorted(v)
    return s[min(len(s) - 1, int(f * (len(s) - 1) + 0.5))]


def pct(a, b):
    return "–" if not b else f"{100 * a / b:.0f}%"


def main():
    quiet = "--quiet" in sys.argv
    mids = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(OUT, "*", "lagledger_sum.json")))
    lines = []
    w = lines.append
    J = {"matches": mids, "cuts": {}}
    data = {}
    for mid in mids:
        T = Truth(mid)
        S = json.load(open(os.path.join(OUT, mid, "shadow.json"), encoding="utf-8"))
        pairs_all = []
        for name, sb in S["bots"].items():
            real, sh, used, pairs = SC.match_bot(T, name, sb)
            for c, i, lag in pairs:
                pairs_all.append((sb["id"], c, sh[i] if i is not None else None, lag))
        data[mid] = (T, [sb["id"] for sb in S["bots"].values()], pairs_all)

    w(f"seam.py — 断面接缝：断面那一拍已经决策、还没落地的指令（有影子重跑的 {len(mids)} 局：{' '.join(mids)}）")
    w("  在途 = 影子决策拍 ≤ 断面 T < 录像执行拍；配不上影子的指令不算在途")
    for cut in CUTS:
        w("")
        w(f"[SM-{cut}] 断面 t={cut}")
        w("  局 | 断面时在线、有地的我方号 | 在途指令：合计（陆攻 / 捐款 / 船）| 牵涉的号 | 落地时生效的 | 落地时派出的兵 | 断面那一拍这些我方号账上的兵合计 | 派出的兵 ÷ 账上的兵 | "
          "在途指令的时延 P50 / 最大 | 断面后 90 拍内落地的指令：合计 / 其中在途的 / 配不上影子的")
        tot = dict(matches=0, seats=0, n=0, k1=0, k2=0, k3=0, who=0, ok=0, troops=0, bank=0, after=0, afterIn=0, afterUn=0, withAny=0)
        lags_all = []
        rows = []
        for mid in mids:
            T, ids, pairs_all = data[mid]
            end = T.R["endTick"]
            if end <= cut:
                continue
            seats = [p for p in ids if T.active(p, cut) and T.terr(p, cut) > 0]
            infl = [(p, c, s, lag) for p, c, s, lag in pairs_all if s is not None and s[0] <= cut < c[0]]
            by = {k: sum(1 for _, c, _, _ in infl if c[2] == k) for k in (1, 2, 3)}
            who = len(set(p for p, _, _, _ in infl))
            ok = sum(1 for _, c, _, _ in infl if c[5] == 1)
            troops = sum(c[6] for _, c, _, _ in infl if c[5] == 1 and c[2] in (1, 3)) + sum(c[6] + c[7] for _, c, _, _ in infl if c[5] == 1 and c[2] == 2)
            bank = sum(T.bal(p, cut) for p in seats)
            lags = [lag for _, _, _, lag in infl]
            after = [(p, c, s) for p, c, s, _ in pairs_all if cut < c[0] <= cut + 90]
            after_in = sum(1 for p, c, s in after if s is not None and s[0] <= cut)
            after_un = sum(1 for p, c, s in after if s is None)
            w(f"  {mid} | {len(seats)} | {len(infl)}（{by[1]} / {by[2]} / {by[3]}）| {who} | {ok} | {troops} | {bank} | {pct(troops, bank)} | "
              f"{q(lags, 0.5) if lags else '–'} / {max(lags) if lags else '–'} | {len(after)} / {after_in} / {after_un}")
            rows.append(dict(mid=mid, seats=len(seats), n=len(infl), land=by[1], don=by[2], boat=by[3], who=who, ok=ok, troops=troops, bank=bank,
                             lagP50=q(lags, 0.5), lagMax=max(lags) if lags else None, after=len(after), afterIn=after_in, afterUn=after_un))
            tot["matches"] += 1
            tot["seats"] += len(seats)
            tot["n"] += len(infl)
            tot["k1"] += by[1]
            tot["k2"] += by[2]
            tot["k3"] += by[3]
            tot["who"] += who
            tot["ok"] += ok
            tot["troops"] += troops
            tot["bank"] += bank
            tot["after"] += len(after)
            tot["afterIn"] += after_in
            tot["afterUn"] += after_un
            tot["withAny"] += 1 if infl else 0
            lags_all += lags
        if tot["matches"]:
            w(f"  合计 {tot['matches']} 局 | {tot['seats']} | {tot['n']}（{tot['k1']} / {tot['k2']} / {tot['k3']}）| {tot['who']} | {tot['ok']} | {tot['troops']} | {tot['bank']} | {pct(tot['troops'], tot['bank'])} | "
              f"{q(lags_all, 0.5) if lags_all else '–'} / {max(lags_all) if lags_all else '–'} | {tot['after']} / {tot['afterIn']} / {tot['afterUn']}")
            w(f"  有在途指令的局 {tot['withAny']} / {tot['matches']}；牵涉的号占断面时在线有地的我方号 {pct(tot['who'], tot['seats'])}；"
              f"断面后 90 拍内落地的指令里在途的占 {pct(tot['afterIn'], tot['after'])}；在途指令里落地时生效的占 {pct(tot['ok'], tot['n'])}")
        J["cuts"][str(cut)] = dict(total=tot, lagP50=q(lags_all, 0.5), lagMax=max(lags_all) if lags_all else None, rows=rows)
    w("")
    ffa = [mid for mid in mids if data[mid][0].R.get("gameMode") == 0]
    heavy = 0
    for mid in mids:
        lag = json.load(open(os.path.join(OUT, mid, "lagledger_sum.json"), encoding="utf-8")).get("lag", [])
        p50 = next((x.get("p50") for x in lag if x.get("period") == "600~1500"), None)
        heavy += 1 if p50 is not None and p50 >= 35 else 0
    w(f"读法：这是有影子的 {len(mids)} 局，都是 squad20（其中自由混战：{' '.join(ffa) if ffa else '无'}），600~1500 拍时延中位 ≥35 拍的 {heavy} 局，不代表全部的局；")
    w("      决策拍用的是影子（不落后的客户端），真机的决策更晚，所以「在途」是上界方向的估计；配不上影子的指令没有算进来，又是下界方向。")

    os.makedirs(os.path.join(OUT, "_cross"), exist_ok=True)
    open(os.path.join(OUT, "_cross", "seam.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump(J, open(os.path.join(OUT, "_cross", "seam.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not quiet:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
