#!/usr/bin/env python3
"""cfprobe.py — 「历史真局断面反事实」探针（cfprobe.mjs）的逐局结果汇总。

    cd /agent/repos/c136-r08 && export PYTHONDONTWRITEBYTECODE=1
    timeout 120 python3 c136-review/agents/R08/scripts/cfprobe.py [--quiet]

读 out/_run/cfprobe/<局>.json（cfprobe.mjs）和 out/_run/xtruth/<局>.json（席位分组、对不对得上日志；和 xtruth.py 同一个判定）。
只用「对得上且有对局段、录像走到 900 拍以后」的局。输出 out/_cross/cfprobe.txt / cfprobe.json。

臂的定义见 cfprobe.mjs 文件头：fact 录像原样 / idle 本编队 630 拍起不下指令 / wj 本编队的录像指令各推迟 7~19 拍 /
p0 探针规则立即执行 / p14 固定 14 拍 / pj 7~19 拍抖动 / ph 抖动 + 这个号在这一局的历史卡顿。
探针规则不是候选策略，只是一把固定的尺子；别的真人照录像走（开环）。

  [CF-A] 覆盖和核对（fact 臂的 R 和 xtruth.txt 的是不是同一个数）。
  [CF-B] 各臂在 900 / 1260 / 1500 拍的 R（own 人均地 ÷ 野人人均地）。
  [CF-C] 同一条规则换通道：成对差和符号检验；按这一局历史卡顿的多少分档。
  [CF-D] 630~1500 拍从内置 AI 手里拿到的地：各臂 own 人均、own 占全部真人的份额。
  [CF-E] 通道签名：成批落地占比、落地生效占比、单拍限流丢掉的条数、想派的兵和实际派出去的兵。
  [CF-F] 开环偏差：别的真人的录像陆攻有多少条「生效 / 没生效」翻了面，分窗。
  [CF-G] own 在 630~1500 拍出局的人数。
"""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xtruth as XT  # noqa: E402
from xbatch import name_pool, discovery_ids  # noqa: E402

OUT = os.path.join(HERE, "..", "out")
RUN = os.path.join(OUT, "_run", "cfprobe")
RUNX = os.path.join(OUT, "_run", "xtruth")
ARMS = ["fact", "idle", "wj", "p0", "p14", "pj", "ph"]
AN = {"fact": "fact 录像原样", "idle": "idle 不下指令", "wj": "wj 录像指令再推迟 7~19 拍", "p0": "p0 探针·立即",
      "p14": "p14 探针·固定 14 拍", "pj": "pj 探针·7~19 拍抖动", "ph": "ph 探针·抖动+历史卡顿"}
CPS = [630, 900, 1260, 1500]
WN = ["630~900", "900~1260", "1260~1500"]


def q(v, p):
    if not v:
        return None
    v = sorted(v)
    i = p * (len(v) - 1)
    lo = int(i)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (i - lo)


def fmt(x, nd=2):
    return "—" if x is None else f"{x:.{nd}f}"


def pct(a, b, nd=0):
    return "—" if not b else f"{100 * a / b:.{nd}f}%"


def sign_p(k, n):
    """双侧符号检验（二项，p=0.5）。"""
    if n == 0:
        return None
    from math import comb
    lo = min(k, n - k)
    tail = sum(comb(n, i) for i in range(lo + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def fp(p):
    return "—" if p is None else (f"{p:.2g}" if p < 0.001 else f"{p:.3f}")


def ratio(cp, own, wild):
    a = [cp["terr"][p] for p in own if cp["terr"][p] > 0]
    b = [cp["terr"][p] for p in wild if cp["terr"][p] > 0]
    if not a or not b:
        return None
    return (sum(a) / len(a)) / (sum(b) / len(b))


def main():
    quiet = "--quiet" in sys.argv
    pool = name_pool()
    ids = discovery_ids()
    lines = []

    def P(x=""):
        lines.append(x)

    rows = []
    n_files = n_skip = n_err = n_invalid = 0
    for mid, card in ids:
        p = os.path.join(RUN, f"{mid}.json")
        px = os.path.join(RUNX, f"{mid}.json")
        if not os.path.exists(p):
            continue
        n_files += 1
        A = json.load(open(p, encoding="utf-8"))
        if "error" in A:
            n_err += 1
            continue
        if "skip" in A:
            n_skip += 1
            continue
        if not os.path.exists(px):
            n_invalid += 1
            continue
        X = json.load(open(px, encoding="utf-8"))
        if "error" in X:
            n_invalid += 1
            continue
        names, low, F, own, valid, spawn_only, grp = XT.seat_groups(X, mid, pool)
        if not valid or spawn_only:
            n_invalid += 1
            continue
        H = A["H"]
        own_s = sorted(set(own) & set(A["own"]))
        wild = [p_ for p_ in range(H) if grp[p_] == "wild"]
        if not own_s or not wild:
            n_invalid += 1
            continue
        row = dict(matchId=mid, cohort=card.get("cohort"), endTick=A["endTick"], own=len(own_s), ownProbe=len(A["own"]),
                   wild=len(wild), stalls=sum(len(v) for v in A["stalls"].values()), R={}, ai={}, aiShare={}, sig={}, div={}, dead={})
        heads0 = sum(1 for p_ in own_s if A["arms"]["fact"]["cp"]["630"]["terr"][p_] > 0)
        row["heads630"] = heads0
        for arm in ARMS:
            V = A["arms"][arm]
            row["R"][arm] = {str(t): ratio(V["cp"][str(t)], own_s, wild) for t in CPS if str(t) in V["cp"]}
            ai_own = sum(V["aiCells"][p_] for p_ in own_s)
            ai_all = sum(V["aiCells"][:H])
            row["ai"][arm] = ai_own / heads0 if heads0 else None
            row["aiShare"][arm] = ai_own / ai_all if ai_all else None
            row["dead"][arm] = V["ownDead"]
            if V.get("probe"):
                pr = V["probe"]
                row["sig"][arm] = dict(dec=pr["dec"], exec=pr["exec"], ok=pr["ok"], capDrop=pr["capDrop"], intended=pr["intended"], sent=pr["sent"],
                                       n=pr["batch"][0], inBatch=pr["batch"][1], toAi=pr["toAi"], okAi=pr["okAi"])
            else:
                rc = V["rec"]
                row["sig"][arm] = dict(exec=rc["exec"], atk=rc["atk"], ok=rc["ok"], n=rc["batch"][0], inBatch=rc["batch"][1])
            if arm != "fact":
                row["div"][arm] = dict(win=V["wildDiv"], same=V["wildLenSame"])
        rows.append(row)

    n = len(rows)
    r15 = [r for r in rows if r["endTick"] >= 1500]
    P("cfprobe.py — 「历史真局断面反事实」探针汇总（cfprobe.mjs；从 t=630 的真实断面起换掉本编队的指令，别的真人照录像走；发现集）")
    P("")
    P("[CF-A] 覆盖和核对")
    P(f"  有结果的局 {n_files}（重演出错 {n_err}、录像不到 900 拍或没认出本编队 {n_skip}、对不上日志或没有野人 {n_invalid}）→ 可用 {n} 局；"
      f"其中录像走到 1500 拍的 {len(r15)} 局（十人编队 {sum(1 for r in r15 if r['cohort'] == 'squad10')} / 二十人编队 {sum(1 for r in r15 if r['cohort'] == 'squad20')}）")
    diff_own = sum(1 for r in rows if r["own"] != r["ownProbe"])
    P(f"  探针认出的本编队席位和 xtruth 的 own 席位不一致的局 {diff_own}（R 一律按两者都认的席位算）")
    f630 = [r["R"]["fact"]["630"] for r in rows if r["R"]["fact"].get("630")]
    f1500 = [r["R"]["fact"]["1500"] for r in r15 if r["R"]["fact"].get("1500")]
    P(f"  fact 臂（= 历史）的 R：t=630 中位 {fmt(q(f630, 0.5))}（xtruth.txt [XT-B] 1.08）；t=1500 中位 {fmt(q(f1500, 0.5))}（[XT-B] 0.51）")
    P("")

    # ---------- [CF-B]
    P("[CF-B] 各臂的 R（own 人均地 ÷ 野人人均地；人头 = 当拍在线且有地）：中位（P25~P75），局数")
    P("  臂 | t=900 | t=1260 | t=1500 | t=1500 时 R ≥ 1 的局")
    J = dict(n=n, n1500=len(r15), R={}, pairs={}, ai={}, sig={}, div={}, dead={})
    for arm in ARMS:
        cells = []
        J["R"][arm] = {}
        for t in (900, 1260, 1500):
            v = [r["R"][arm][str(t)] for r in rows if r["endTick"] >= t and r["R"][arm].get(str(t)) is not None]
            cells.append(f"{fmt(q(v, 0.5))}（{fmt(q(v, 0.25))}~{fmt(q(v, 0.75))}），{len(v)}")
            J["R"][arm][str(t)] = dict(n=len(v), p25=q(v, 0.25), p50=q(v, 0.5), p75=q(v, 0.75))
        v = [r["R"][arm]["1500"] for r in r15 if r["R"][arm].get("1500") is not None]
        ge1 = sum(1 for x in v if x >= 1)
        J["R"][arm]["ge1"] = [ge1, len(v)]
        P(f"  {AN[arm]} | " + " | ".join(cells) + f" | {ge1}/{len(v)}")
    P("")

    # ---------- [CF-C]
    P("[CF-C] 换通道 / 换指令的成对差（t=1500 的 R，同一局两臂相减）：中位差（P25~P75）｜前者更高的局 / 更低的局｜双侧符号检验 p")
    PAIRS = [("fact", "idle", "历史指令值多少：fact − idle"), ("fact", "wj", "历史指令再晚 7~19 拍：fact − wj"),
             ("p0", "fact", "探针·立即 − 历史"), ("ph", "fact", "探针·抖动+历史卡顿 − 历史"),
             ("p0", "p14", "同一条规则：立即 − 固定 14 拍"), ("p0", "pj", "同一条规则：立即 − 7~19 拍抖动"),
             ("p14", "pj", "同一条规则：固定 14 拍 − 7~19 拍抖动"), ("pj", "ph", "同一条规则：抖动 − 抖动+历史卡顿"),
             ("p0", "ph", "同一条规则：立即 − 抖动+历史卡顿")]
    for a, b, lab in PAIRS:
        d = [r["R"][a]["1500"] - r["R"][b]["1500"] for r in r15 if r["R"][a].get("1500") is not None and r["R"][b].get("1500") is not None]
        up = sum(1 for x in d if x > 1e-9)
        dn = sum(1 for x in d if x < -1e-9)
        p = sign_p(up, up + dn)
        P(f"  {lab}：{fmt(q(d, 0.5))}（{fmt(q(d, 0.25))}~{fmt(q(d, 0.75))}）｜{up} / {dn}｜p={fp(p)}（{len(d)} 局）")
        J["pairs"][f"{a}-{b}"] = dict(n=len(d), p50=q(d, 0.5), p25=q(d, 0.25), p75=q(d, 0.75), up=up, down=dn, p=p)
    P("  按这一局录像里本编队的历史卡顿段数（每个号的「沉默 ≥70 拍后一拍落地 ≥3 条」，630~1500 拍）÷ 630 拍在线人数分档：")
    P("  档 | 局数 | 每号卡顿段数 中位 | R1500：fact | p0 | pj | ph | ph ÷ pj 中位 | ph ÷ p0 中位")
    r15s = sorted(r15, key=lambda r: r["stalls"] / max(1, r["heads630"]))
    k = len(r15s)
    cuts = [("少（下三分之一）", r15s[: k // 3]), ("中", r15s[k // 3: 2 * k // 3]), ("多（上三分之一）", r15s[2 * k // 3:])]
    J["dose"] = []
    for lab, grp_ in cuts:
        st = [r["stalls"] / max(1, r["heads630"]) for r in grp_]

        def med(arm):
            return q([r["R"][arm]["1500"] for r in grp_ if r["R"][arm].get("1500") is not None], 0.5)

        rel = [r["R"]["ph"]["1500"] / r["R"]["pj"]["1500"] for r in grp_ if r["R"]["pj"].get("1500")]
        rel0 = [r["R"]["ph"]["1500"] / r["R"]["p0"]["1500"] for r in grp_ if r["R"]["p0"].get("1500")]
        P(f"  {lab} | {len(grp_)} | {fmt(q(st, 0.5), 1)} | {fmt(med('fact'))} | {fmt(med('p0'))} | {fmt(med('pj'))} | {fmt(med('ph'))} | {fmt(q(rel, 0.5))} | {fmt(q(rel0, 0.5))}")
        J["dose"].append(dict(label=lab, n=len(grp_), stallsPerSeat=q(st, 0.5), fact=med("fact"), p0=med("p0"), pj=med("pj"), ph=med("ph"),
                              phOverPj=q(rel, 0.5), phOverP0=q(rel0, 0.5)))
    P("")

    # ---------- [CF-D]
    P("[CF-D] 630~1500 拍从内置 AI / 空壳手里拿到的地（走到 1500 拍的局）")
    P("  臂 | own 人均（÷630 拍在线人数）中位（P25~P75）| own 占全部真人拿到的份额 中位 | 合计 own 拿到的格")
    for arm in ARMS:
        v = [r["ai"][arm] for r in r15 if r["ai"][arm] is not None]
        s = [r["aiShare"][arm] for r in r15 if r["aiShare"][arm] is not None]
        tot = sum(r["ai"][arm] * r["heads630"] for r in r15 if r["ai"][arm] is not None)
        P(f"  {AN[arm]} | {fmt(q(v, 0.5), 0)}（{fmt(q(v, 0.25), 0)}~{fmt(q(v, 0.75), 0)}）| {fmt(q(s, 0.5))} | {tot:.0f}")
        J["ai"][arm] = dict(perHead=q(v, 0.5), p25=q(v, 0.25), p75=q(v, 0.75), share=q(s, 0.5), total=tot)
    hs = [r["heads630"] / (r["heads630"] + sum(1 for _ in range(r["wild"]))) for r in r15]
    P(f"  对照：own 占（own + 野人）席位的份额 中位 {fmt(q(hs, 0.5))}")
    P("")

    # ---------- [CF-E]
    P("[CF-E] 通道签名（630~1500 拍，全部可用局合计）")
    P("  臂 | 落地指令 | 成批落地占比（同号同拍 ≥3 条）| 陆攻生效占比 | 单拍限流丢掉 | 想派的兵 | 实际派出的兵 | 实际 ÷ 想派")
    for arm in ARMS:
        if arm in ("idle", "wj"):
            continue
        S = defaultdict(float)
        for r in rows:
            for k_, v in r["sig"][arm].items():
                S[k_] += v
        if arm == "fact":
            P(f"  {AN[arm]} | {S['exec']:.0f}（陆攻 {S['atk']:.0f}）| {pct(S['inBatch'], S['n'])} | {pct(S['ok'], S['atk'])} | — | — | — | —")
            J["sig"][arm] = dict(exec=S["exec"], atk=S["atk"], batchShare=S["inBatch"] / S["n"] if S["n"] else None, okShare=S["ok"] / S["atk"] if S["atk"] else None)
        else:
            P(f"  {AN[arm]} | {S['exec']:.0f}（决策 {S['dec']:.0f}）| {pct(S['inBatch'], S['n'])} | {pct(S['ok'], S['exec'])} | {S['capDrop']:.0f} | {S['intended']:.0f} | {S['sent']:.0f} | "
              f"{fmt(S['sent'] / S['intended'] if S['intended'] else None)}")
            J["sig"][arm] = dict(dec=S["dec"], exec=S["exec"], batchShare=S["inBatch"] / S["n"] if S["n"] else None, okShare=S["ok"] / S["exec"] if S["exec"] else None,
                                 capDrop=S["capDrop"], intended=S["intended"], sent=S["sent"])
    v = [r["sig"]["fact"]["inBatch"] / r["sig"]["fact"]["n"] for r in rows if r["sig"]["fact"]["n"]]
    v2 = [r["sig"]["ph"]["inBatch"] / r["sig"]["ph"]["n"] for r in rows if r["sig"]["ph"]["n"]]
    P(f"  逐局的成批落地占比：fact 中位 {fmt(q(v, 0.5))}（P25~P75 {fmt(q(v, 0.25))}~{fmt(q(v, 0.75))}）；ph 中位 {fmt(q(v2, 0.5))}（{fmt(q(v2, 0.25))}~{fmt(q(v2, 0.75))}）")
    P("")

    # ---------- [CF-F]
    P("[CF-F] 开环偏差：别的真人在录像里的陆攻，和 fact 臂比「生效 / 没生效」翻了面的占比（合计翻面 ÷ 合计条数；括号里是逐局中位 / P90）")
    P("  臂 | 630~900 | 900~1260 | 1260~1500 | 条数对不齐的局")
    for arm in ARMS[1:]:
        cells = []
        J["div"][arm] = []
        for k_ in range(3):
            nn = sum(r["div"][arm]["win"][k_][0] for r in rows)
            ff = sum(r["div"][arm]["win"][k_][1] for r in rows)
            per = [r["div"][arm]["win"][k_][1] / r["div"][arm]["win"][k_][0] for r in rows if r["div"][arm]["win"][k_][0] >= 20]
            cells.append(f"{pct(ff, nn, 1)}（{pct(q(per, 0.5) or 0, 1, 1)} / {pct(q(per, 0.9) or 0, 1, 1)}；{nn} 条）")
            J["div"][arm].append(dict(n=nn, flipped=ff, perMatchP50=q(per, 0.5), perMatchP90=q(per, 0.9)))
        bad = sum(1 for r in rows if not r["div"][arm]["same"])
        P(f"  {AN[arm]} | " + " | ".join(cells) + f" | {bad}")
    P("  翻面的方向（ph 臂）：历史生效 → 现在没生效 / 历史没生效 → 现在生效")
    for k_ in range(3):
        a = sum(r["div"]["ph"]["win"][k_][2] for r in rows)
        b = sum(r["div"]["ph"]["win"][k_][3] for r in rows)
        P(f"    {WN[k_]}：{a:.0f} / {b:.0f}")
    P("")

    # ---------- [CF-G]
    P("[CF-G] own 在 630~1500 拍出局的人数（全部可用局合计）")
    P("  " + "｜".join(f"{arm} {sum(r['dead'][arm] for r in rows)}" for arm in ARMS))
    for arm in ARMS:
        J["dead"][arm] = sum(r["dead"][arm] for r in rows)
    P("")
    P("读数时的三条限制：")
    P("  1. 别的真人是开环的（照录像走，不会因为本编队变强而改打法、也不会来打变厚或变薄的号），[CF-F] 的翻面比例就是这个偏差的量；探针臂的绝对水平偏乐观。")
    P("  2. 探针规则不是候选策略：它只吃内置 AI 和无主地，不防真人、不发船、不捐款，看的是当拍真实局面、没有在途账本。")
    P("  3. ph 臂只把「沉默后成批落地」当卡顿；线上卡的时候单条指令也晚（lagledger：卡顿局 600~1500 拍时延中位 89~182 拍），所以 ph 低估了真实卡顿。")

    os.makedirs(os.path.join(OUT, "_cross"), exist_ok=True)
    with open(os.path.join(OUT, "_cross", "cfprobe.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    J["rows"] = rows
    with open(os.path.join(OUT, "_cross", "cfprobe.json"), "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False)
    if not quiet:
        print("\n".join(lines))
    else:
        print(f"cfprobe.py: {n} 局 → out/_cross/cfprobe.txt")


if __name__ == "__main__":
    main()
