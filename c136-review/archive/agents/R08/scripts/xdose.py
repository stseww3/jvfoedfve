#!/usr/bin/env python3
"""xdose.py — 「卡顿越重，掉得越多吗」：把 xbatch（成批落地）、xtruth（陆攻没生效、发出 vs 落地、人均对照、AI 地份额）
按局对起来，看剂量—反应关系。只读 out/_cross/xbatch.json、xtruth.json（先跑那两个脚本），不碰数据包。

    python3 xdose.py [--quiet]        → out/_cross/xdose.txt、xdose.json

每局取 own 席位的三个「卡顿剂量」和四个「结果」：
  剂量  A 成批占比 = 600~1500 里 own 落地的指令有多少落在同拍 ≥3 条的批里（xbatch）
        B 没生效占比 = 600~1500 里 own 落地的陆攻有多少条一兵没派出去（xtruth [XT-D]）
        C 没落地占比 = 1 − 录像落地的陆攻 ÷ 日志发出的陆攻，600~1500（xtruth [XT-F]；负数按 0）
  结果  R1500 = t=1500 的人均对照；DROP = R1500 ÷ R630；AISHARE = (600,1500] AI 地的份额对照；R900 = t=900 的人均对照
  另外  EDGE = own 贴边比例；H = 房间真人数；DENS1500 = t=1500 兵密度对照
节：
  [XD-A] 样本   [XD-B] 秩相关（Spearman）   [XD-C] 按剂量三分位看结果   [XD-D] 几乎没有卡顿的局   [XD-E] 赢的局和没赢的局
  [XD-F] 贴边 / 房间大小 和结果的秩相关（混杂项）   [XD-G] 不靠卡顿的两个量（挨着白给的 AI 出不出手、每条派多少）
  [XD-H] 留底门槛的剂量（被留底挡住的样本占比）和结果、和卡顿剂量的关系；门槛 × 卡顿 两层交叉
  [XD-I] 别的解释量（门槛、贴边、扎堆、续兵、对数、每条派多少）和结果的秩相关：原始 / 扣掉卡顿剂量 B 之后的偏相关 / 只看几乎不卡的局
         偏相关 = 两个量各自对 B 取秩回归后的残差之间的相关（秩口径）；AIRATIO = own 人均从内置 AI 吃到的格 ÷ 同局野人人均
"""
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out", "_cross")


def rank(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x, y):
    if len(x) < 5:
        return None
    rx, ry = rank(x), rank(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sx = sum((a - mx) ** 2 for a in rx) ** 0.5
    sy = sum((b - my) ** 2 for b in ry) ** 0.5
    if sx == 0 or sy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / (sx * sy)


def partial_spearman(x, y, z):
    """秩口径的偏相关：x、y 各自对 z 的秩做一元线性回归，取残差的 Pearson 相关。"""
    if len(x) < 8:
        return None
    rx, ry, rz = rank(x), rank(y), rank(z)
    n = len(rz)
    mz = sum(rz) / n
    szz = sum((c - mz) ** 2 for c in rz)
    if szz == 0:
        return None

    def resid(r):
        m = sum(r) / n
        b = sum((c - mz) * (a - m) for a, c in zip(r, rz)) / szz
        return [(a - m) - b * (c - mz) for a, c in zip(r, rz)]

    ex, ey = resid(rx), resid(ry)
    sx = sum(a * a for a in ex) ** 0.5
    sy = sum(b * b for b in ey) ** 0.5
    if sx == 0 or sy == 0:
        return None
    return sum(a * b for a, b in zip(ex, ey)) / (sx * sy)


def med(v):
    return statistics.median(v) if v else None


def f2(x):
    return "—" if x is None else f"{x:.2f}"


def main():
    quiet = "--quiet" in sys.argv
    XB = json.load(open(os.path.join(OUT, "xbatch.json"), encoding="utf-8"))
    XT = json.load(open(os.path.join(OUT, "xtruth.json"), encoding="utf-8"))
    brow = {r["matchId"]: r for r in XB["rows"]}
    rows = []
    for r in XT["matches"]:
        if not r.get("valid") or r.get("spawnOnly"):
            continue
        mid = r["matchId"]
        b = brow.get(mid)
        ro = r["ratio"]["own"]
        g = lambda t: ro.get(str(t))  # noqa: E731
        d = dict(matchId=mid, cohort=r["cohort"], won=r["won"], H=r["H"], R630=g(630), R900=g(900), R1260=g(1260), R1500=g(1500),
                 DROP=(g(1500) / g(630)) if g(630) and g(1500) is not None else None)
        if r.get("ai600_1500") and r.get("heads600_1500"):
            a = sum(r["ai600_1500"].values())
            h = sum(r["heads600_1500"][k] for k in ("own", "apex", "pool", "wild"))
            if a > 0 and r["heads600_1500"]["own"] >= 3 and r["heads600_1500"]["wild"] >= 5:
                d["AISHARE"] = (r["ai600_1500"]["own"] / a) / (r["heads600_1500"]["own"] / h)
        if b and b["stat"]["own"][1]["cmds"] >= 20:
            d["A"] = b["stat"]["own"][1]["batchCmds"] / b["stat"]["own"][1]["cmds"]
        c = r["cmds"][1] if len(r["cmds"]) > 1 else None
        if c and c["own"]["land"] >= 20:
            d["B"] = 1 - c["own"]["ok"] / c["own"]["land"]
        fl = r["flow"][1] if len(r["flow"]) > 1 else None
        if fl and fl["atkIssued"] >= 20:
            d["C"] = max(0.0, 1 - fl["land"] / fl["atkIssued"])
        sp = r["spawn"]["own"]
        d["EDGE"] = sp["nearEdge"] / sp["n"] if sp["n"] else None
        d["DENS1500"] = (r.get("densRatio") or {}).get("1500")
        if r.get("reach"):
            fr = sum(r["reach"][k]["own"][4] for k in range(3))
            fh = sum(r["reach"][k]["own"][5] for k in range(3))
            wf = sum(r["reach"][k]["wild"][4] for k in range(3))
            wh = sum(r["reach"][k]["wild"][5] for k in range(3))
            if fr >= 20:
                d["ACT"] = fh / fr
            if wf >= 20:
                d["ACTW"] = wh / wf
        sz = r["atkSize"][1] if len(r.get("atkSize") or []) > 1 else None
        if sz and sz["own"][0] >= 20:
            d["SIZE"] = sz["own"][2] / sz["own"][0]
        if sz and sz["wild"][0] >= 20:
            d["SIZEW"] = sz["wild"][2] / sz["wild"][0]
        for k_src, k_dst in (("gateShare", "GATE"), ("sbShare", "SB"), ("allowedHit", "ALLOWHIT")):
            if r.get(k_src) is not None:
                d[k_dst] = r[k_src]
        if sp["n"]:
            d["CLUSTER"] = sp["nnBot"] / sp["n"]
        spw = r["spawn"]["wild"]
        if sp.get("nnMed") and spw.get("nnMed"):
            d["NNDIST"] = sp["nnMed"] / spw["nnMed"]
        pr_, yl_, bd_ = r.get("pairs"), r.get("yield600_1500"), r.get("budget600_1500")
        if pr_ and yl_ and yl_["own"]["heads"] >= 3 and yl_["wild"]["heads"] >= 5:
            po = [sum(pr_["own"][c][i] for c in ("alone", "mate", "wild")) for i in range(14)]
            pw = [sum(pr_["wild"][c][i] for c in ("alone", "mate", "wild")) for i in range(14)]
            if po[0] >= 10 and pw[0] >= 10:
                d["PAIRS"] = (po[0] / yl_["own"]["heads"]) / (pw[0] / yl_["wild"]["heads"])
                d["REINF"] = po[11] / po[1]
                d["CMDSPAIR"] = po[1] / po[0]
                d["AISIZE"] = (po[7] / po[0]) / (pw[7] / pw[0])
        if bd_ and bd_["own"]["heads"] >= 3 and bd_["wild"]["heads"] >= 5 and bd_["wild"]["ai"] > 0:
            d["AIRATIO"] = (bd_["own"]["ai"] / bd_["own"]["heads"]) / (bd_["wild"]["ai"] / bd_["wild"]["heads"])
            if bd_["wild"]["neutral"] > 0:
                d["NEUTRATIO"] = (bd_["own"]["neutral"] / bd_["own"]["heads"]) / (bd_["wild"]["neutral"] / bd_["wild"]["heads"])
        rows.append(d)
    out = []
    P = out.append
    P(f"[XD-A] 样本：对得上且有对局段的 {len(rows)} 局；其中 R630、R1500 都有的 {sum(1 for d in rows if d['DROP'] is not None)} 局；"
      f"三个剂量齐全的 {sum(1 for d in rows if all(k in d for k in 'ABC'))} 局")
    for k, nm in (("A", "成批占比"), ("B", "没生效占比"), ("C", "没落地占比")):
        v = sorted(d[k] for d in rows if k in d)
        P(f"  剂量 {k}（{nm}）：{len(v)} 局，中位 {med(v):.2f}，下四分位 {v[len(v) // 4]:.2f}，上四分位 {v[3 * len(v) // 4]:.2f}，最小 {v[0]:.2f}，最大 {v[-1]:.2f}")
    P("  三个剂量之间的秩相关：" + "；".join(
        f"{a}×{b} {f2(spearman(*zip(*[(d[a], d[b]) for d in rows if a in d and b in d])))}" for a, b in (("A", "B"), ("A", "C"), ("B", "C"))))

    P("")
    P("[XD-B] 秩相关（Spearman；负号 = 剂量越大结果越低）：剂量 × 结果 | 全部（局数） | squad10（局数） | squad20（局数）")
    corr = {}
    for k in "ABC":
        for res in ("R900", "R1500", "DROP", "AISHARE"):
            cells = []
            for sel_name, sel in (("all", rows), ("squad10", [d for d in rows if d["cohort"] == "squad10"]), ("squad20", [d for d in rows if d["cohort"] == "squad20"])):
                pr = [(d[k], d[res]) for d in sel if k in d and d.get(res) is not None]
                rho = spearman(*zip(*pr)) if len(pr) >= 5 else None
                cells.append(f"{f2(rho)}（{len(pr)}）")
                corr[f"{k}|{res}|{sel_name}"] = dict(rho=rho, n=len(pr))
            P(f"  {k} × {res} | " + " | ".join(cells))

    P("")
    P("[XD-C] 按剂量三分位看结果（每格：中位；括号里是局数）：剂量 | 三分位 | 剂量范围 | R900 | R1500 | DROP | AISHARE | 主队赢")
    terc = {}
    for k, nm in (("A", "成批占比"), ("B", "没生效占比"), ("C", "没落地占比")):
        sel = sorted([d for d in rows if k in d and d.get("R1500") is not None], key=lambda d: d[k])
        n = len(sel)
        for i, tn in enumerate(("低", "中", "高")):
            part = sel[i * n // 3:(i + 1) * n // 3]
            if not part:
                continue
            P(f"  {k}（{nm}） | {tn} | {part[0][k]:.2f} ~ {part[-1][k]:.2f} | {f2(med([d['R900'] for d in part if d.get('R900') is not None]))} | {f2(med([d['R1500'] for d in part]))} | "
              f"{f2(med([d['DROP'] for d in part if d.get('DROP') is not None]))} | {f2(med([d['AISHARE'] for d in part if d.get('AISHARE') is not None]))} | {sum(1 for d in part if d['won'])}/{len(part)}")
            terc[f"{k}|{tn}"] = dict(n=len(part), lo=part[0][k], hi=part[-1][k], R1500=med([d["R1500"] for d in part]),
                                     AISHARE=med([d["AISHARE"] for d in part if d.get("AISHARE") is not None]), won=sum(1 for d in part if d["won"]))

    P("")
    calm = [d for d in rows if d.get("A", 1) <= 0.10 and d.get("B", 1) <= 0.05]
    P(f"[XD-D] 几乎没有卡顿的局（成批占比 ≤10% 且 没生效占比 ≤5%）：{len(calm)} 局")
    for d in sorted(calm, key=lambda d: d["matchId"]):
        P(f"  {d['matchId']}（{d['cohort']}，{d['H']} 席{'，赢' if d['won'] else ''}）：成批 {d.get('A', 0):.0%}、没生效 {d.get('B', 0):.0%}、没落地 {f2(d.get('C'))}｜"
          f"R630 {f2(d.get('R630'))} → R900 {f2(d.get('R900'))} → R1260 {f2(d.get('R1260'))} → R1500 {f2(d.get('R1500'))}｜AISHARE {f2(d.get('AISHARE'))}｜贴边 {f2(d.get('EDGE'))}｜兵密度对照 {f2(d.get('DENS1500'))}")
    rest = [d for d in rows if d not in calm and d.get("R1500") is not None]
    cr = [d for d in calm if d.get("R1500") is not None]
    P(f"  这些局 R1500 中位 {f2(med([d['R1500'] for d in cr]))}（{len(cr)} 局）、AISHARE 中位 {f2(med([d['AISHARE'] for d in cr if d.get('AISHARE') is not None]))}；"
      f"其余的局 R1500 中位 {f2(med([d['R1500'] for d in rest]))}（{len(rest)} 局）、AISHARE 中位 {f2(med([d['AISHARE'] for d in rest if d.get('AISHARE') is not None]))}")

    P("")
    P("[XD-E] 赢的局和没赢的局（中位；括号里是局数）：组 | A 成批 | B 没生效 | C 没落地 | R630 | R1500 | AISHARE | 贴边")
    for nm, sel in (("主队赢", [d for d in rows if d["won"]]), ("没赢", [d for d in rows if not d["won"]])):
        P(f"  {nm}（{len(sel)}） | " + " | ".join(f2(med([d[k] for d in sel if d.get(k) is not None])) for k in ("A", "B", "C", "R630", "R1500", "AISHARE", "EDGE")))

    P("")
    P("[XD-F] 混杂项和结果的秩相关：项 × 结果 | 全部（局数）")
    for k in ("EDGE", "H", "DENS1500", "R630"):
        for res in ("R1500", "DROP", "AISHARE"):
            pr = [(d[k], d[res]) for d in rows if d.get(k) is not None and d.get(res) is not None]
            P(f"  {k} × {res} | {f2(spearman(*zip(*pr)) if len(pr) >= 5 else None)}（{len(pr)}）")
    for k in "ABC":
        pr = [(d["H"], d[k]) for d in rows if k in d]
        P(f"  H × 剂量 {k} | {f2(spearman(*zip(*pr)))}（{len(pr)}）")

    P("")
    P("[XD-G] 不靠卡顿的两个量（xtruth [XT-I] / [XT-D]）：ACT = own 挨着白给的内置 AI 时 90 拍内出手的比例；SIZE = own 打 AI 的生效陆攻每条派出占余额的平均")
    for k in ("ACT", "SIZE"):
        v = sorted(d[k] for d in rows if k in d)
        P(f"  {k}：{len(v)} 局，中位 {med(v):.2f}，下四分位 {v[len(v) // 4]:.2f}，上四分位 {v[3 * len(v) // 4]:.2f}；同局野人 中位 {f2(med([d[k + 'W'] for d in rows if k + 'W' in d]))}")
    for k in ("ACT", "SIZE"):
        for res in ("R1500", "DROP", "AISHARE"):
            pr = [(d[k], d[res]) for d in rows if k in d and d.get(res) is not None]
            P(f"  {k} × {res} | {f2(spearman(*zip(*pr)) if len(pr) >= 5 else None)}（{len(pr)}）")
        for dose in "ABC":
            pr = [(d[k], d[dose]) for d in rows if k in d and dose in d]
            P(f"  {k} × 剂量 {dose} | {f2(spearman(*zip(*pr)) if len(pr) >= 5 else None)}（{len(pr)}）")
    lowlag = [d for d in rows if d.get("B") is not None and d["B"] <= 0.05]
    P(f"  只看几乎不卡的局（没生效占比 ≤5%，{len(lowlag)} 局）：ACT 中位 {f2(med([d['ACT'] for d in lowlag if 'ACT' in d]))}（同局野人 {f2(med([d['ACTW'] for d in lowlag if 'ACTW' in d]))}）、"
      f"SIZE 中位 {f2(med([d['SIZE'] for d in lowlag if 'SIZE' in d]))}（野人 {f2(med([d['SIZEW'] for d in lowlag if 'SIZEW' in d]))}）、R1500 中位 {f2(med([d['R1500'] for d in lowlag if d.get('R1500') is not None]))}、AISHARE 中位 {f2(med([d['AISHARE'] for d in lowlag if d.get('AISHARE') is not None]))}")
    for k in ("ACT", "SIZE"):
        for res in ("R1500", "AISHARE"):
            pr = [(d[k], d[res]) for d in lowlag if k in d and d.get(res) is not None]
            P(f"    几乎不卡的局里 {k} × {res} | {f2(spearman(*zip(*pr)) if len(pr) >= 5 else None)}（{len(pr)}）")

    P("")
    P("[XD-H] 留底门槛的剂量（xtruth [XT-J]）：GATE = own 挨着白给的内置 AI 的样本里，被留底（地价项 / dpKeep / sb）挡住的占比；SB = 其中 AI 仇恨项 sb 的占比；")
    P("  ALLOWHIT = 规则放行的样本里 90 拍内出手的比例（放行了却没出手 = 指令通道那一层）")
    for k in ("GATE", "SB", "ALLOWHIT"):
        v = sorted(d[k] for d in rows if k in d)
        P(f"  {k}：{len(v)} 局，中位 {med(v):.2f}，下四分位 {v[len(v) // 4]:.2f}，上四分位 {v[3 * len(v) // 4]:.2f}，最小 {v[0]:.2f}，最大 {v[-1]:.2f}")
    gate = {}
    for k in ("GATE", "SB", "ALLOWHIT"):
        for res in ("R1500", "DROP", "AISHARE", "ACT"):
            cells = []
            for sel_name, sel in (("all", rows), ("squad10", [d for d in rows if d["cohort"] == "squad10"]), ("squad20", [d for d in rows if d["cohort"] == "squad20"])):
                pr = [(d[k], d[res]) for d in sel if k in d and d.get(res) is not None]
                rho = spearman(*zip(*pr)) if len(pr) >= 5 else None
                cells.append(f"{f2(rho)}（{len(pr)}）")
                gate[f"{k}|{res}|{sel_name}"] = dict(rho=rho, n=len(pr))
            P(f"  {k} × {res} | 全部 {cells[0]} | squad10 {cells[1]} | squad20 {cells[2]}")
        for dose in "ABC":
            pr = [(d[k], d[dose]) for d in rows if k in d and dose in d]
            P(f"  {k} × 剂量 {dose} | {f2(spearman(*zip(*pr)) if len(pr) >= 5 else None)}（{len(pr)}）")
    both = [d for d in rows if "GATE" in d and "B" in d and d.get("R1500") is not None]
    if both:
        gm, bm = med([d["GATE"] for d in both]), med([d["B"] for d in both])
        P(f"  两层交叉（{len(both)} 局；GATE 以中位 {gm:.2f} 分、没生效占比 B 以中位 {bm:.2f} 分）：格 | 局数 | R1500 中位 | AISHARE 中位 | ACT 中位 | 主队赢")
        for gn, gf in (("门槛轻", lambda d: d["GATE"] <= gm), ("门槛重", lambda d: d["GATE"] > gm)):
            for bn, bf in (("卡得轻", lambda d: d["B"] <= bm), ("卡得重", lambda d: d["B"] > bm)):
                part = [d for d in both if gf(d) and bf(d)]
                P(f"    {gn} × {bn} | {len(part)} | {f2(med([d['R1500'] for d in part]))} | {f2(med([d['AISHARE'] for d in part if d.get('AISHARE') is not None]))} | "
                  f"{f2(med([d['ACT'] for d in part if 'ACT' in d]))} | {sum(1 for d in part if d['won'])}")
                gate[f"cross|{gn}|{bn}"] = dict(n=len(part), R1500=med([d["R1500"] for d in part]), AISHARE=med([d["AISHARE"] for d in part if d.get("AISHARE") is not None]),
                                               won=sum(1 for d in part if d["won"]))
    for k in ("GATE", "SB"):
        for res in ("R1500", "AISHARE", "ACT"):
            pr = [(d[k], d[res]) for d in lowlag if k in d and d.get(res) is not None]
            P(f"    几乎不卡的局里 {k} × {res} | {f2(spearman(*zip(*pr)) if len(pr) >= 5 else None)}（{len(pr)}）")
    P("  几乎不卡的局逐局：局 | GATE | SB | ALLOWHIT | ACT | R1500 | AISHARE")
    for d in sorted(lowlag, key=lambda d: d.get("GATE", 9)):
        P(f"    {d['matchId']}（{d['cohort']}{'，赢' if d['won'] else ''}） | {f2(d.get('GATE'))} | {f2(d.get('SB'))} | {f2(d.get('ALLOWHIT'))} | {f2(d.get('ACT'))} | {f2(d.get('R1500'))} | {f2(d.get('AISHARE'))}")

    P("")
    P("[XD-I] 别的解释量和结果（秩相关）：量 | 局数 | × R1500：原始 / 扣掉 B 的偏相关 | × AISHARE：原始 / 偏 | × AIRATIO：原始 / 偏 || 只看几乎不卡的局（局数）：× R1500 | × AISHARE | × AIRATIO")
    P("  GATE = 白给样本里被留底挡住的占比；SB = 其中 AI 仇恨项；EDGE = 贴边比例；CLUSTER = own 的号里最近的真人是机器号的比例；NNDIST = own 最近真人距离中位 ÷ 野人的；")
    P("  H = 房间真人数；R630 = t=630 人均对照；SIZE = 打 AI 每条派出占余额；REINF = 打 AI 的生效陆攻里续兵的占比；CMDSPAIR = 每对（号 → AI）的条数；")
    P("  PAIRS = 人均对几个 AI 下过手 ÷ 野人的；AISIZE = 下手时 AI 的地 ÷ 野人下手时的；AIRATIO = own 人均从内置 AI 吃到的格 ÷ 野人人均（600~1500）；NEUTRATIO = 无主地同口径")
    other = {}
    XV = ("B", "GATE", "SB", "EDGE", "CLUSTER", "NNDIST", "H", "R630", "SIZE", "REINF", "CMDSPAIR", "PAIRS", "AISIZE", "ACT", "ALLOWHIT")
    for k in XV:
        cells = []
        nmax = 0
        for res in ("R1500", "AISHARE", "AIRATIO"):
            tr = [(d[k], d[res], d["B"]) for d in rows if d.get(k) is not None and d.get(res) is not None and "B" in d]
            nmax = max(nmax, len(tr))
            raw = spearman([a for a, _, _ in tr], [b for _, b, _ in tr]) if len(tr) >= 8 else None
            par = partial_spearman([a for a, _, _ in tr], [b for _, b, _ in tr], [c for _, _, c in tr]) if (len(tr) >= 8 and k != "B") else None
            cells.append(f"{f2(raw)} / {f2(par)}")
            other[f"{k}|{res}"] = dict(n=len(tr), raw=raw, partial=par)
        ccells = []
        ncalm = 0
        for res in ("R1500", "AISHARE", "AIRATIO"):
            pr = [(d[k], d[res]) for d in lowlag if d.get(k) is not None and d.get(res) is not None]
            ncalm = max(ncalm, len(pr))
            rho = spearman(*zip(*pr)) if len(pr) >= 8 else None
            ccells.append(f2(rho))
            other[f"calm|{k}|{res}"] = dict(n=len(pr), rho=rho)
        P(f"  {k} | {nmax} | " + " | ".join(cells) + f" || （{ncalm}）" + " | ".join(ccells))
    P("  解释量之间（全部局）：" + "；".join(
        f"{a}×{b} {f2(spearman(*zip(*[(d[a], d[b]) for d in rows if d.get(a) is not None and d.get(b) is not None])))}"
        for a, b in (("GATE", "B"), ("GATE", "CLUSTER"), ("GATE", "EDGE"), ("GATE", "H"), ("SB", "CLUSTER"), ("REINF", "B"), ("PAIRS", "B"), ("PAIRS", "GATE"), ("AISIZE", "B"),
                     ("CLUSTER", "EDGE"), ("CLUSTER", "H"), ("EDGE", "H"))))
    P("  几乎不卡的局（没生效占比 ≤5%）各量的中位：" + "；".join(f"{k} {f2(med([d[k] for d in lowlag if d.get(k) is not None]))}" for k in XV + ("AIRATIO", "NEUTRATIO", "R1500", "AISHARE")))
    rest_ = [d for d in rows if d not in lowlag]
    P("  其余的局各量的中位：" + "；".join(f"{k} {f2(med([d[k] for d in rest_ if d.get(k) is not None]))}" for k in XV + ("AIRATIO", "NEUTRATIO", "R1500", "AISHARE")))

    with open(os.path.join(OUT, "xdose.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    with open(os.path.join(OUT, "xdose.json"), "w", encoding="utf-8") as f:
        json.dump(dict(rows=rows, corr=corr, terciles=terc, calm=[d["matchId"] for d in calm], gate=gate, other=other), f, ensure_ascii=False, separators=(",", ":"))
    if not quiet:
        print("\n".join(out))


if __name__ == "__main__":
    main()
