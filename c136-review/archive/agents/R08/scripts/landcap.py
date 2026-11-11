#!/usr/bin/env python3
"""landcap.py — 「好的地实际抢到多少」硬账：出生份额、实际拿到率、身边内置 AI 的地的去向、没抢到的逐格归因。

    python3 landcap.py <matchId> [--quiet]
需要：out/<局>/landcap.json（landcap.mjs）、resim.json；有 shadow.json（影子）时才做 [KE] 的门槛 / 迟到归因。
输出 out/<局>/landcap.txt 和 landcap_sum.json（跨局汇总用）。

节：
  [KA] 出生份额：全图陆地按「离谁的出生点最近」分给各真人（直线口径 vorE；陆路口径 vorB = 只走陆地谁先到）。
       编队名下合计占全图几成、对人头占比的倍数；每号中位、其他真人中位；逐号。
  [KB] 实际拿到率：t=630 / 900 / 1260 / 1500 / 1800 实际领土 ÷ 名下份额（阵亡的按 0 格算），编队、其他真人、各队。
  [KC] 名下的地在谁手里（t=630、1500）：自己 / 编队友 / 同队野人 / 敌队真人 / 内置 AI / 无主。
  [KD] 身边内置 AI 的地的去向：t0（600）属于内置 AI 的格，到 1500 / 1800 第一个拿到它的真人是谁。
       三个范围：全图；编队名下（vorE）的；t0 时和编队号接壤的那批 AI 的。
       另记 t0 之后才被 AI 占的格（AI 在 t0 之后还在长）的去向、两类合计，以及按 150 拍窗的编队占比。
  [KA] 里另有反事实：编队号都站到各自日志里最后一条出生指派上时的份额（要先跑 spawncheck.py 写出 spawnlast.json，再跑 landcap.mjs）。
  [KE] 没抢到的三层归因（(600,1500] 被真人吃掉的内置 AI 地）：
       应得（按人头）− 实得 = ① 名下先天就少 + 名下的被别人吃掉 − 到别人名下吃的；
       「名下的被别人吃掉」逐格归到：同队 AI 不能打 / 号不在了 / 够不着 / ② 门槛挡住（哪一关、sb 由谁定）/ ③ 迟到落空 / 出手了被分走 / 过了门槛没发。
口径：
  [KF] 接壤口径的归因：不看名下，别人吃掉的每一格只问「被吃掉之前有没有编队号贴着那个 AI」；贴着的再分 同队 AI / ② / ③ / 出手了被分走。
  · 「名下」= 直线最近（vorE）。归因时先看名下那个号；它不接壤这个 AI 时，改看接壤这个 AI 的其他编队号（同队优先）。
  · 门槛 = 影子在真值上每 10 拍把接壤的内置 AI 逐个过一遍 pickTarget 的门槛（shadow.mjs census 的逐 AI 结论）。
    need<=0（压上去的兵已经够吃光它）算过闸。
    一个 AI 在 [600, 被拿走那一窗) 里过闸的普查点不到一半 → 记「② 门槛挡住」，取出现最多的那一关。
  · 迟到落空 = 影子在这段里对这个 AI 发过陆攻，但录像里这个号对它没有一条生效的陆攻；
    或有生效的陆攻、但配上影子的时延最小也 ≥35 拍。
  · 出手了被分走 = 录像里对这个 AI 有按时生效的陆攻，这些格还是被别人先拿到。
"""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from truth import Truth  # noqa: E402
import shadowcmp as SC  # noqa: E402

OUT = os.path.join(HERE, "..", "out")
NEUTRAL = 512


PASS = ("ok", "need<=0")   # need<=0 = 压在它身上的兵已经够吃光它，不算被挡
GATE = {"floor:sb": "防人机留底 sb（safeFinite）", "floor:winPrice": "价位底（winFloor）", "floor:dpKeep": "开局留底 dpKeep", "floor:peopleFloor": "对真人留底",
        "botOk(winWorth)": "值不值门槛（winWorth）", "maxCost": "单价上限", "allow": "allow", "slots": "没有空槽", "floor:none": "可用兵不够最小份额", "floor:other": "其它留底"}


def gate_name(why):
    k = why[len("minShare("):-1] if why.startswith("minShare(") else why
    return GATE.get(k, k)


def med(v):
    v = sorted(v)
    return v[len(v) // 2] if v else 0


def quart(v, f):
    v = sorted(v)
    return v[min(len(v) - 1, int(len(v) * f))] if v else 0


def pct(a, b):
    return f"{100.0 * a / b:.1f}%" if b else "–"


def main():
    args = sys.argv[1:]
    mid = args[0]
    quiet = "--quiet" in args
    tag = args[args.index("--tag") + 1] if "--tag" in args else None
    suf = f"_{tag}" if tag else ""
    LC = json.load(open(os.path.join(OUT, mid, f"landcap{suf}.json"), encoding="utf-8"))
    T = Truth(mid)
    R = T.R
    sp = os.path.join(OUT, mid, "shadow.json")
    S = json.load(open(sp, encoding="utf-8")) if os.path.exists(sp) else None
    fp = os.path.join(OUT, mid, "facts.json")
    F = json.load(open(fp, encoding="utf-8")) if os.path.exists(fp) else None
    H = LC["H"]
    land = LC["land"]
    hum = {h["id"]: h for h in LC["humans"]}
    sq = [h for h in LC["humans"] if h["squad"] == 1]
    peer = [h for h in LC["humans"] if h["squad"] == 2]
    oth = [h for h in LC["humans"] if h["squad"] == 0]
    sqid = {h["id"] for h in sq}
    peerid = {h["id"] for h in peer}
    team = lambda p: (hum[p]["team"] if p in hum else (1 + (p % LC["nTeams"]) if LC["botsTeamed"] and LC["nTeams"] else 0))
    tg = LC["teamGame"]
    same = lambda a, b: tg and team(a) != 0 and team(a) == team(b)
    name = lambda p: (T.nm(p) if p < H else f"AI{p}")
    lines = []
    w = lines.append
    SUM = {"matchId": mid, "land": land, "humansSpawned": len(hum), "squad": len(sq), "peer": len(peer)}

    # ---------- [KA]
    w(f"[KA] {mid} 出生份额（录像取自 {LC['replayFrom']}）：陆地 {land} 格，出生的真人 {len(hum)}/{H}（人均 {land // max(1, len(hum))} 格）；编队 {len(sq)} 个号"
      + (f"，同房另一支编队 {len(peer)} 个号" if peer else "") + f"；内置 AI 入队={LC['botsTeamed']}；走陆路到不了的陆地 {LC['unreach']} 格（{pct(LC['unreach'], land)}）")
    for key, label in (("vorE", "直线最近"), ("vorB", "陆路先到")):
        tot = sum(h[key] for h in LC["humans"])
        s = sum(h[key] for h in sq)
        hs = len(sq) / max(1, len(hum))
        ratio = (s / tot) / hs if tot and hs else 0
        w(f"  {label}：编队名下 {s} 格 = {pct(s, tot)}（人头占 {100 * hs:.1f}% → 份额÷人头 {ratio:.2f}）；每号 中位 {med([h[key] for h in sq])}、最小 {min([h[key] for h in sq], default=0)}、最大 {max([h[key] for h in sq], default=0)}"
          f"｜其他真人 每人 中位 {med([h[key] for h in oth])}、下四分位 {quart([h[key] for h in oth], 0.25)}、上四分位 {quart([h[key] for h in oth], 0.75)}"
          + (f"｜另一支编队 每号中位 {med([h[key] for h in peer])}（份额÷人头 {(sum(h[key] for h in peer) / tot) / (len(peer) / len(hum)):.2f}）" if peer else ""))
        SUM[f"{key}Share"] = round(s / tot, 4) if tot else 0
        SUM[f"{key}PerHead"] = round(ratio, 3)
        SUM[f"{key}MedSquad"] = med([h[key] for h in sq])
        SUM[f"{key}MedOther"] = med([h[key] for h in oth])
    SUM["headShare"] = round(len(sq) / max(1, len(hum)), 4)
    if tg:
        grp = defaultdict(lambda: [0, 0, 0, 0])   # team -> [nSq, vorE sq, nOther, vorE other]
        for h in LC["humans"]:
            g = grp[h["team"]]
            if h["squad"] == 1:
                g[0] += 1; g[1] += h["vorE"]
            else:
                g[2] += 1; g[3] += h["vorE"]
        w("  各队名下（直线）：" + "；".join(f"T{t} 编队 {g[0]} 号 {g[1]} 格 + 其他 {g[2]} 人 {g[3]} 格 = {pct(g[1] + g[3], land)}" for t, g in sorted(grp.items())))

    def nn(h, pool):
        ds = [((h["x"] - o["x"]) ** 2 + (h["y"] - o["y"]) ** 2) ** 0.5 for o in pool if o["id"] != h["id"]]
        return round(min(ds)) if ds else -1
    w("  逐号：号 | 队 | 出生点 | 直线份额 | 陆路份额 | 最近的真人 / 最近的非编队真人 / 最近的编队友（像素）")
    for h in sorted(sq, key=lambda h: h["vorE"]):
        w(f"    {name(h['id']):22s} | T{h['team']} | ({h['x']},{h['y']}) | {h['vorE']} | {h['vorB']} | {nn(h, LC['humans'])} / {nn(h, oth + peer)} / {nn(h, sq)}")
    rk = sorted(LC["humans"], key=lambda h: h["vorE"])
    pos = {h["id"]: i for i, h in enumerate(rk)}
    low = sum(1 for h in sq if pos[h["id"]] < len(rk) / 4)
    w(f"  直线份额排在全房最小四分之一里的编队号 {low}/{len(sq)} 个（按人头应是 {len(sq) / 4:.1f} 个）")
    SUM["squadInLowestQuartile"] = low
    cf = LC.get("cf")
    if cf:
        cv = {h["id"]: h for h in cf["humans"]}
        tot = sum(h["vorE"] for h in cf["humans"])
        s_cf = sum(cv[h["id"]]["vorE"] for h in sq)
        s_now = sum(h["vorE"] for h in sq)
        hs = len(sq) / max(1, len(hum))
        rk2 = sorted(cf["humans"], key=lambda h: h["vorE"])
        pos2 = {h["id"]: i for i, h in enumerate(rk2)}
        low2 = sum(1 for h in sq if pos2[h["id"]] < len(rk2) / 4)
        o_now = med([h["vorE"] for h in oth]); o_cf = med([cv[h["id"]]["vorE"] for h in oth])
        w(f"  反事实（编队号都站到各自日志里最后一条出生指派上，别的真人不动；挪了 {cf['moved']} 个号）：编队名下 {s_cf} 格 = {pct(s_cf, tot)}（份额÷人头 {(s_cf / tot) / hs:.2f}；实际 {s_now} 格 = {pct(s_now, tot)}，差 {s_cf - s_now:+d} 格）；"
          f"每号 中位 {med([cv[h['id']]['vorE'] for h in sq])}（实际 {med([h['vorE'] for h in sq])}）、最小 {min(cv[h['id']]['vorE'] for h in sq)}；排在最小四分之一里的 {low2} 个（实际 {low}）；其他真人每人中位 {o_cf}（实际 {o_now}）")

        def nn2(h):
            a = cv[h["id"]]
            ds = [((a["x"] - o["x"]) ** 2 + (a["y"] - o["y"]) ** 2) ** 0.5 for o in cf["humans"] if o["id"] != h["id"]]
            ds2 = [((a["x"] - cv[o["id"]]["x"]) ** 2 + (a["y"] - cv[o["id"]]["y"]) ** 2) ** 0.5 for o in sq if o["id"] != h["id"]]
            return (round(min(ds)) if ds else -1, round(min(ds2)) if ds2 else -1)
        w("  反事实逐号：号 | 实际落点 → 最后一条指派 | 直线份额 实际 → 反事实 | 反事实下最近的真人 / 最近的编队友（像素）")
        for h in sorted(sq, key=lambda h: cv[h["id"]]["vorE"] - h["vorE"]):
            a = cv[h["id"]]
            d1, d2 = nn2(h)
            mv = "（没挪）" if (abs(a["x"] - h["x"]) <= 4 and abs(a["y"] - h["y"]) <= 4) else ""
            w(f"    {name(h['id']):22s} | ({h['x']},{h['y']}) → ({a['x']},{a['y']}){mv} | {h['vorE']} → {a['vorE']}（{a['vorE'] - h['vorE']:+d}）| {d1} / {d2}")
        SUM["cf"] = {"moved": cf["moved"], "vorEShare": round(s_cf / tot, 4), "vorEPerHead": round((s_cf / tot) / hs, 3), "squadCells": s_cf, "actualCells": s_now,
                     "medSquad": med([cv[h["id"]]["vorE"] for h in sq]), "lowQuartile": low2}

    # ---------- [KB]
    w("")
    w("[KB] 实际拿到率 = 实际领土 ÷ 名下份额（直线口径；阵亡 / 离开的按当时的格数算，没地就是 0）")
    w("  拍 | 编队：领土合计 ÷ 名下合计 = 拿到率（每号中位）| 其他真人：合计拿到率（每人中位、下四分位）| 编队人均领土 ÷ 其他真人人均领土" + ("｜另一支编队" if peer else ""))
    SUM["capture"] = {}
    ident = []
    for ts in sorted(LC["at"], key=int):
        A = LC["at"][ts]["terr"]
        def grp_stat(g, key="vorE"):
            tt = sum(A[h["id"]] for h in g)
            vv = sum(h[key] for h in g)
            rr = [A[h["id"]] / max(1, h[key]) for h in g]
            return tt, vv, (tt / vv if vv else 0), med(rr), quart(rr, 0.25)
        a = grp_stat(sq)
        b = grp_stat(oth)
        pc = (a[0] / max(1, len(sq))) / max(1e-9, b[0] / max(1, len(oth)))
        extra = ""
        if peer:
            c = grp_stat(peer)
            extra = f"｜{c[0]} ÷ {c[1]} = {c[2]:.2f}（中位 {c[3]:.2f}）"
        w(f"  {ts} | {a[0]} ÷ {a[1]} = {a[2]:.2f}（中位 {a[3]:.2f}）| {b[0]} ÷ {b[1]} = {b[2]:.2f}（中位 {b[3]:.2f}、下四分位 {b[4]:.2f}）| {pc:.2f}{extra}")
        ab = grp_stat(sq, "vorB"); bb = grp_stat(oth, "vorB")
        vr = (a[1] / max(1, len(sq))) / max(1e-9, b[1] / max(1, len(oth)))   # 人均名下份额之比
        cr = a[2] / b[2] if b[2] else 0                                        # 拿到率之比
        ident.append(f"t={ts} {pc:.2f} = {vr:.2f} × {cr:.2f}")
        SUM["capture"][ts] = {"squad": round(a[2], 3), "squadMed": round(a[3], 3), "other": round(b[2], 3), "otherMed": round(b[3], 3), "perHeadRatio": round(pc, 3),
                              "squadB": round(ab[2], 3), "otherB": round(bb[2], 3), "squadTerr": a[0], "otherTerr": b[0], "vorRatio": round(vr, 3), "captureRatio": round(cr, 3)}
    w("  拆开看（恒等式）：编队人均领土 ÷ 其他真人人均领土 = 人均名下份额之比 × 拿到率之比：" + "；".join(ident))
    if tg:
        for ts in ("630", "1500"):
            if ts not in LC["at"]:
                continue
            A = LC["at"][ts]["terr"]
            grp = defaultdict(lambda: [0, 0, 0, 0])
            for h in LC["humans"]:
                g = grp[h["team"]]
                k = 0 if h["squad"] == 1 else 2
                g[k] += A[h["id"]]; g[k + 1] += h["vorE"]
            w(f"  t={ts} 各队拿到率（编队号 | 其他队员）：" + "；".join(
                f"T{t} {'%.2f' % (g[0] / g[1]) if g[1] else '–'} | {'%.2f' % (g[2] / g[3]) if g[3] else '–'}" for t, g in sorted(grp.items())))
    for ts in ("630", "1500"):
        if ts in LC["at"]:
            A = LC["at"][ts]["terr"]
            w(f"  t={ts} 逐号 领土/份额：" + "；".join(f"{name(h['id'])} {A[h['id']]}/{h['vorE']}={A[h['id']] / max(1, h['vorE']):.2f}" for h in sorted(sq, key=lambda h: -A[h['id']] / max(1, h['vorE']))))

    # ---------- [KC]
    w("")
    w("[KC] 名下的地（直线口径）在谁手里：拍 | 谁名下 | 合计格 | 自己 | 编队友（同队 / 异队）| 同队野人 | 敌队真人 | 内置 AI | 无主" + (" | 另一支编队" if peer else ""))
    SUM["occ"] = {}
    for ts in ("630", "1500"):
        if ts not in LC["occ"]:
            continue
        occ = LC["occ"][ts]
        for label, g in (("编队", sq), ("其他真人", oth)) + ((("另一支编队", peer),) if peer else ()):
            tot = [0] * 9
            for h in g:
                row = occ.get(str(h["id"]))
                if row:
                    for i in range(9):
                        tot[i] += row[i]
            n = sum(tot)
            if label == "其他真人":   # 对其他真人来说，编队号也只是同队 / 敌队真人
                mate = tot[3] + tot[1] + tot[7]; enemy = tot[4] + tot[2] + tot[8]
                w(f"  {ts} | {label} | {n} | {pct(tot[0], n)} | – | {pct(mate, n)} | {pct(enemy, n)} | {pct(tot[5], n)} | {pct(tot[6], n)}")
            else:
                w(f"  {ts} | {label} | {n} | {pct(tot[0], n)} | {pct(tot[1], n)} / {pct(tot[2], n)} | {pct(tot[3], n)} | {pct(tot[4], n)} | {pct(tot[5], n)} | {pct(tot[6], n)}"
                  + (f" | {pct(tot[7] + tot[8], n)}" if peer else ""))
            SUM["occ"][f"{ts}:{label}"] = {"n": n, "self": tot[0], "sqSame": tot[1], "sqOther": tot[2], "mate": tot[3], "enemy": tot[4], "ai": tot[5], "neutral": tot[6], "peer": tot[7] + tot[8]}

    # ---------- [KD]
    fate = LC["fate"]   # [reg, q, taker(<0: -1 无主 -2 原 AI -3 别的 AI), bucketEnd, n]
    t0, t1 = LC["t0"], LC["t1"]
    contact = {}
    for k, v in LC["contact"].items():
        p, q = map(int, k.split(":"))
        contact[(p, q)] = v[0::2]
    touch0 = defaultdict(set)   # AI -> t0 时接壤的编队号
    for (p, q), ts_ in contact.items():
        if ts_ and ts_[0] == t0:
            touch0[q].add(p)
    ai0 = {r[0]: r for r in LC["ai0"]}
    w("")
    n_ai = sum(r[1] for r in LC["ai0"])
    w(f"[KD] 内置 AI 的地的去向：t={t0} 时内置 AI 共 {len(ai0)} 个、{LC['nTracked']} 格（占陆地 {pct(LC['nTracked'], land)}），合计 {sum(r[2] for r in LC['ai0'])} 兵"
      + (f"；内置 AI 入队：和某个真人同队的 AI 他不能打" if LC["botsTeamed"] else ""))
    alive0 = [h for h in LC["humans"] if (LC["at"].get("630") or {}).get("terr", [0] * H)[h["id"]] > 0]
    hshare = sum(1 for h in alive0 if h["squad"] == 1) / max(1, len(alive0))
    w(f"  t=630 还有地的真人 {len(alive0)} 个，其中编队 {sum(1 for h in alive0 if h['squad'] == 1)} 个（人头 {100 * hshare:.1f}%）")

    def tally(rows, upto):
        """rows: fate 行的子集；返回各类格数。"""
        c = defaultdict(int)
        for reg, q, tk, be, n in rows:
            if tk < 0 or be > upto:
                if tk == -1:
                    c["无主"] += n
                elif tk < 0:
                    c["还在内置 AI 手里"] += n
                else:
                    c["之后才被拿走"] += n
                continue
            if tk in sqid:
                c["编队"] += n
            elif tk in peerid:
                c["另一支编队"] += n
            else:
                c["其他真人"] += n
        return c

    scopes = [("全图", fate),
              ("编队名下的（直线口径）", [r for r in fate if r[0] in sqid]),
              (f"t={t0} 时和编队号接壤的 AI 的", [r for r in fate if r[1] in touch0])]
    SUM["aiFate"] = {}
    for label, rows in scopes:
        tot = sum(r[4] for r in rows)
        nai = len({r[1] for r in rows})
        for upto in (1500, t1):
            c = tally(rows, upto)
            eaten = c["编队"] + c["另一支编队"] + c["其他真人"]
            w(f"  {label}：{nai} 个 AI、{tot} 格｜到 t={upto} 被真人吃掉 {eaten}（{pct(eaten, tot)}）：编队 {c['编队']}（占被吃的 {pct(c['编队'], eaten)}）"
              + (f"、另一支编队 {c['另一支编队']}（{pct(c['另一支编队'], eaten)}）" if peer else "")
              + f"、其他真人 {c['其他真人']}（{pct(c['其他真人'], eaten)}）｜没被吃：还在内置 AI 手里 {c['还在内置 AI 手里'] + c['之后才被拿走']}、无主 {c['无主']}")
            SUM["aiFate"][f"{label}:{upto}"] = {"cells": tot, "eaten": eaten, "squad": c["编队"], "peer": c["另一支编队"], "other": c["其他真人"]}
    fl = LC.get("fateLate")
    if fl is not None:
        for label, rows in (("全图", fl), ("编队名下的（直线口径）", [r for r in fl if r[0] in sqid])):
            tot = sum(r[4] for r in rows)
            for upto in (1500, t1):
                c = tally(rows, upto)
                eaten = c["编队"] + c["另一支编队"] + c["其他真人"]
                w(f"  t={t0} 之后才被内置 AI 占的格（AI 还在往无主地里长；每 10 拍扫一遍）· {label}：{tot} 格｜到 t={upto} 被真人吃掉 {eaten}（{pct(eaten, tot)}）：编队 {c['编队']}（占被吃的 {pct(c['编队'], eaten)}）"
                  + (f"、另一支编队 {c['另一支编队']}（{pct(c['另一支编队'], eaten)}）" if peer else "")
                  + f"、其他真人 {c['其他真人']}（{pct(c['其他真人'], eaten)}）")
                SUM["aiFate"][f"late:{label}:{upto}"] = {"cells": tot, "eaten": eaten, "squad": c["编队"], "peer": c["另一支编队"], "other": c["其他真人"]}
        for upto in (1500, t1):
            a = SUM["aiFate"][f"全图:{upto}"]; b = SUM["aiFate"][f"late:全图:{upto}"]
            e = a["eaten"] + b["eaten"]; sqe = a["squad"] + b["squad"]
            w(f"  合计（({t0},{t1}] 里属于过内置 AI 的全部格 {a['cells'] + b['cells']}）：到 t={upto} 被真人吃掉 {e}，编队 {sqe}（{pct(sqe, e)}；人头 {100 * hshare:.1f}% → 应得 {hshare * e:.0f}，差 {hshare * e - sqe:+.0f}）")
            SUM["aiFate"][f"ever:全图:{upto}"] = {"cells": a["cells"] + b["cells"], "eaten": e, "squad": sqe, "par": round(hshare * e)}
        # 按 150 拍窗看编队吃到的份额（两类格合在一起）
        win = defaultdict(lambda: [0, 0])
        for rows in (fate, fl):
            for reg, q, tk, be, n in rows:
                if tk < 0:
                    continue
                k = ((be - 1) // 150) * 150
                win[k][0] += n
                if tk in sqid:
                    win[k][1] += n
        w("  按窗（150 拍）全房真人吃到的 AI 格 / 编队吃到（占比）：" + "；".join(f"{k}~{k + 150} {v[0]} / {v[1]}（{pct(v[1], v[0])}）" for k, v in sorted(win.items())))
        SUM["aiFateWin"] = {str(k): v for k, v in sorted(win.items())}
    # 编队名下的：按拿走的人和名下那个号的关系细分
    rows = [r for r in fate if r[0] in sqid and r[2] >= 0 and r[3] <= 1500]
    rel = defaultdict(int)
    for reg, q, tk, be, n in rows:
        if tk == reg:
            rel["名下那个号自己"] += n
        elif tk in sqid:
            rel["同队编队友" if same(tk, reg) else "异队编队友"] += n
        elif tk in peerid:
            rel["另一支编队"] += n
        else:
            rel["同队野人" if same(tk, reg) else "敌队真人"] += n
    tot = sum(rel.values())
    w(f"  编队名下、到 t=1500 被吃掉的 {tot} 格是谁吃的：" + "、".join(f"{k} {v}（{pct(v, tot)}）" for k, v in sorted(rel.items(), key=lambda kv: -kv[1])))
    SUM["aiFateOwnRegion1500"] = dict(rel)
    # 接壤 AI 逐个（格数最多的 12 个）
    per_ai = defaultdict(lambda: defaultdict(int))
    for reg, q, tk, be, n in fate:
        if q not in touch0:
            continue
        if tk < 0 or be > 1500:
            per_ai[q]["没被吃"] += n
        elif tk in sqid:
            per_ai[q]["编队"] += n
        else:
            per_ai[q][name(tk)] += n
    w(f"  t={t0} 时接壤的 AI 逐个（格数最多的 12 个）：AI | 队 | 格 / 兵 | 接壤的编队号 | 出局拍 | 到 t=1500：编队吃到 | 别人吃到（前 3）")
    for q in sorted(touch0, key=lambda q: -ai0[q][1])[:12]:
        d = per_ai[q]
        others = sorted(((k, v) for k, v in d.items() if k not in ("编队", "没被吃")), key=lambda kv: -kv[1])[:3]
        w(f"    AI{q} | {'T%d' % ai0[q][3] if LC['botsTeamed'] else '–'} | {ai0[q][1]} / {ai0[q][2]} | {'、'.join(name(p) for p in sorted(touch0[q]))} | {LC['aiDeath'].get(str(q), '–')} | {d['编队']} | "
          + "、".join(f"{k} {v}" for k, v in others) + (f"；没被吃 {d['没被吃']}" if d["没被吃"] else ""))

    # ---------- [KE]
    w("")
    U0 = [r for r in fate if r[2] >= 0 and r[3] <= 1500]
    U = U0 + [r for r in (fl or []) if r[2] >= 0 and r[3] <= 1500]
    nU = sum(r[4] for r in U)
    A = sum(r[4] for r in U if r[2] in sqid)
    Us = sum(r[4] for r in U if r[0] in sqid)
    Ain = sum(r[4] for r in U if r[0] in sqid and r[2] in sqid)
    Aout = A - Ain
    lost = Us - Ain
    par = hshare * nU
    w(f"[KE] 没抢到的三层归因：({t0},1500] 全房真人吃掉的『属于过内置 AI 的格』（t={t0} 时就是 AI 的 + 之后 AI 才占的）共 {nU} 格；编队按人头（{100 * hshare:.1f}%）应得 {par:.0f} 格，实得 {A} 格（{pct(A, nU)}），差 {par - A:+.0f} 格")
    n0 = sum(r[4] for r in U0); a0 = sum(r[4] for r in U0 if r[2] in sqid); us0 = sum(r[4] for r in U0 if r[0] in sqid)
    w(f"  其中只算 t={t0} 时就是 AI 的格：{n0} 格，应得 {hshare * n0:.0f}，实得 {a0}（{pct(a0, n0)}），差 {hshare * n0 - a0:+.0f}；名下的 {us0} 格")
    w(f"  拆开：① 名下先天就少 = 应得 {par:.0f} − 名下的 {Us} = {par - Us:+.0f} 格｜名下的被别人吃掉 {lost} 格（名下的 {pct(lost, Us)}）｜到别人名下吃到 {Aout} 格（抵掉）")
    SUM["attr"] = {"U": nU, "par": round(par), "got": A, "ownRegion": Us, "gotInOwn": Ain, "gotOutside": Aout, "lost": lost, "geomDeficit": round(par - Us),
                   "base": {"U": n0, "par": round(hshare * n0), "got": a0, "ownRegion": us0}}
    # 逐格归因
    census = {}   # (bot id, t) -> {q: why}, src
    shadow_cmds = defaultdict(list)
    lag_of = {}   # id(real cmd row) -> lag
    last_tick = {}
    if S:
        for bname, sb in S["bots"].items():
            p = sb["id"]
            for c in sb.get("census", []):
                per = c[14] if len(c) > 14 else None
                if per is None:
                    continue
                census[(p, c[0])] = ({q: why for q, why in per}, c[11])
            for c in sb["cmds"]:
                if c[1] == 1:
                    shadow_cmds[p].append(c)
            real, sh, used, pairs = SC.match_bot(T, bname, sb)
            for c, i, lag in pairs:
                if lag is not None:
                    lag_of[(c[0], c[1], c[3], c[4])] = lag
    if F:
        for me, b in F["bots"].items():
            if b.get("ticks"):
                last_tick[int(me)] = b["ticks"][-1]["t"]
    real_atk = defaultdict(list)
    for c in R["cmdLog"]:
        if c[2] == 1 and c[1] in sqid:
            real_atk[c[1]].append(c)
    has_census = bool(census)

    def gone(p, t):
        h = hum[p]
        return (0 <= h["deathT"] <= t) or (0 <= h["leftT"] <= t)

    def classify(b, q, be):
        if LC["botsTeamed"] and same(b, q):
            return ("同队的内置 AI（不能打）", "")
        if gone(b, be - 30):
            return ("号已经出局或离开", "")
        actor = None
        if any(t0 <= t < be for t in contact.get((b, q), [])):
            actor = b
        else:
            cands = [p for p in sqid if p != b and not gone(p, be - 30) and not (LC["botsTeamed"] and same(p, q))
                     and any(t0 <= t < be for t in contact.get((p, q), []))]
            cands.sort(key=lambda p: (not same(p, b), p))
            if cands:
                actor = cands[0]
        if actor is None:
            return ("够不着（没有编队号接壤这个 AI）", "")
        return judge(actor, q, be)

    def judge(actor, q, be):
        if actor in last_tick and last_tick[actor] < be - 150:
            return ("客户端停了（日志已断）", "")
        eff = [c for c in real_atk[actor] if c[4] == q and c[5] == 1 and t0 - 60 <= c[0] <= be]
        if eff:
            lags = [lag_of.get((c[0], c[1], c[3], c[4])) for c in eff]
            lags = [x for x in lags if x is not None]
            if lags and min(lags) >= 35:
                return ("③ 迟到（出手了，最快的一条也晚到 ≥35 拍）", "")
            return ("出手了、按时生效，被别人分走", "")
        if not has_census:
            return ("没出手（没有影子，分不出原因）", "")
        sh = [c for c in shadow_cmds[actor] if c[3] == q and t0 - 60 <= c[0] < be]
        if sh:
            return ("③ 迟到落空（影子发了，录像里没有生效的）", "")
        pts = [(t, census[(actor, t)]) for t in contact.get((actor, q), []) if t0 <= t < be and (actor, t) in census and q in census[(actor, t)][0]]
        if not pts:
            return ("接壤但策略没把它列为邻居", "")
        whys = defaultdict(int)
        ok = 0
        srcs = defaultdict(int)
        for t, (per, src) in pts:
            why = per[q]
            if why in PASS:
                ok += 1
            else:
                whys[why] += 1
                if "floor:sb" in why and src:
                    srcs[src[2]] += 1
        if ok * 2 >= len(pts):
            return ("过了门槛但没发（影子也没发：先打别的 / 轮次）", "")
        top = max(whys.items(), key=lambda kv: kv[1])[0]
        tag = gate_name(top)
        sub = ""
        if "floor:sb" in top and srcs:
            sub = max(srcs.items(), key=lambda kv: kv[1])[0]
        return (f"② 门槛挡住：{tag}", sub)

    cats = defaultdict(int)
    subs = defaultdict(lambda: defaultdict(int))
    by_taker = defaultdict(int)
    for reg, q, tk, be, n in U:
        if reg not in sqid or tk in sqid:
            continue
        cat, sub = classify(reg, q, be)
        cats[cat] += n
        if sub:
            subs[cat][sub] += n
        by_taker["另一支编队" if tk in peerid else ("同队野人" if same(tk, reg) else "敌队真人")] += n
    w(f"  名下的被别人吃掉的 {lost} 格，吃的人：" + "、".join(f"{k} {v}（{pct(v, lost)}）" for k, v in sorted(by_taker.items(), key=lambda kv: -kv[1])))
    w("  逐格归因（格数 | 占被吃掉的）：")
    SRC = {"squadSameTeam": "同队编队友", "squadOtherTeam": "异队编队友", "peerSameTeam": "另一支编队（同队）", "peerOtherTeam": "另一支编队（异队）",
           "teammate": "同队野人", "enemy": "敌队真人", "ai": "内置 AI", "none": "无"}
    for cat, n in sorted(cats.items(), key=lambda kv: -kv[1]):
        extra = ""
        if subs[cat]:
            extra = "｜sb 由谁的余额定：" + "、".join(f"{SRC.get(k, k)} {v}" for k, v in sorted(subs[cat].items(), key=lambda kv: -kv[1]))
        w(f"    {cat}：{n}（{pct(n, lost)}）{extra}")
    g2 = sum(v for k, v in cats.items() if k.startswith("②"))
    g3 = sum(v for k, v in cats.items() if k.startswith("③"))
    g1 = sum(v for k, v in cats.items() if k.startswith("够不着"))
    w(f"  三层合计：① 站位（名下先天少 {par - Us:+.0f} 格 + 名下够不着 {g1} 格）｜② 门槛挡住 {g2} 格（{pct(g2, lost)}）｜③ 迟到 {g3} 格（{pct(g3, lost)}）"
      f"｜其余 {lost - g1 - g2 - g3} 格（同队 AI、号不在了、出手了被分走、过闸没发等）")
    SUM["attr"].update({"cats": dict(cats), "gate": g2, "late": g3, "noContact": g1, "byTaker": dict(by_taker), "hasShadow": has_census})
    # ---------- [KF] 接壤口径：不看名下，只看「被别人吃掉之前有没有编队号贴着这个 AI」
    w("")
    notsq = [r for r in U if r[2] not in sqid]
    n_not = sum(r[4] for r in notsq)
    cats2 = defaultdict(int)
    subs2 = defaultdict(lambda: defaultdict(int))
    per_bot = defaultdict(lambda: defaultdict(int))
    for reg, q, tk, be, n in notsq:
        cands = [p for p in sqid if not gone(p, be - 30) and any(t0 <= t < be for t in contact.get((p, q), []))]
        if not cands:
            cats2["不接壤（被吃掉之前没有编队号贴着它）"] += n
            continue
        ok_c = [p for p in cands if not (LC["botsTeamed"] and same(p, q))]
        if not ok_c:
            cats2["同队的内置 AI（不能打）"] += n
            continue
        ok_c.sort(key=lambda p: -sum(1 for t in contact.get((p, q), []) if t0 <= t < be))
        cat, sub = judge(ok_c[0], q, be)
        cats2[cat] += n
        per_bot[ok_c[0]][cat[:1] if cat[:1] in "②③" else "其它"] += n
        if sub:
            subs2[cat][sub] += n
    reach = n_not - cats2["不接壤（被吃掉之前没有编队号贴着它）"]
    w(f"[KF] 接壤口径的归因：({t0},1500] 别人吃掉的 {n_not} 格『属于过内置 AI 的格』里，被吃掉之前有编队号贴着那个 AI 的 {reach} 格（{pct(reach, n_not)}）；编队自己吃到 {A} 格")
    w("  逐格归因（格数 | 占贴着的）：")
    for cat, n in sorted(cats2.items(), key=lambda kv: -kv[1]):
        if cat.startswith("不接壤"):
            continue
        extra = ""
        if subs2[cat]:
            extra = "｜sb 由谁的余额定：" + "、".join(f"{SRC.get(k, k)} {v}" for k, v in sorted(subs2[cat].items(), key=lambda kv: -kv[1]))
        w(f"    {cat}：{n}（{pct(n, reach)}）{extra}")
    h2 = sum(v for k, v in cats2.items() if k.startswith("②"))
    h3 = sum(v for k, v in cats2.items() if k.startswith("③"))
    w(f"  合计：② 门槛挡住 {h2} 格（{pct(h2, reach)}）｜③ 迟到 {h3} 格（{pct(h3, reach)}）｜贴着但没吃到的一共 {reach} 格 = 编队实得 {A} 格的 {reach / max(1, A):.2f} 倍")
    short = par - A
    team_ai = cats2.get("同队的内置 AI（不能打）", 0)
    rest = reach - team_ai - h2 - h3
    pos = short - reach
    w(f"  把按人头的差额（应得 {par:.0f} − 实得 {A} = {short:+.0f} 格）摊开：贴着没吃到 {reach} 格 = 同队 AI {team_ai}（{pct(team_ai, short)}）+ ② 门槛 {h2}（{pct(h2, short)}）+ ③ 迟到 {h3}（{pct(h3, short)}）+ 出手了被分走 / 过闸没发等 {rest}（{pct(rest, short)}）；"
      f"剩下 {pos:+.0f} 格（{pct(pos, short) if short > 0 else '–'}）是 ① 贴不着：就算贴着的全吃到也到不了人头份额"
      + ("（负数 = 贴着的全吃到就超过人头份额）" if pos < 0 else ""))
    SUM["attrContact"] = {"short": round(short), "position": round(pos), "teamAi": team_ai, "rest": rest}
    w("  逐号（贴着、被别人吃掉的格里归到这个号头上的）：" + "；".join(
        f"{name(p)} ②{d.get('②', 0)} ③{d.get('③', 0)} 其它{d.get('其它', 0)}" for p, d in sorted(per_bot.items(), key=lambda kv: -sum(kv[1].values()))))
    SUM["attrContact"].update({"othersAte": n_not, "inReach": reach, "cats": dict(cats2), "gate": h2, "late": h3,
                               "perBot": {name(p): dict(d) for p, d in per_bot.items()}})
    # 门槛普查的决策拍数（接壤至少一个可打的 AI 的号·点里，全被挡的）
    if has_census:
        n_pts = n_blk = 0
        why_all = defaultdict(int)
        for (p, t), (per, src) in census.items():
            if not (t0 <= t < 1500) or not per:
                continue
            n_pts += 1
            if not any(v in PASS for v in per.values()):
                n_blk += 1
                for v in set(per.values()):
                    why_all[gate_name(v)] += 1
        w(f"  门槛普查（每 10 拍一个决策点，[{t0},1500)）：贴着可打的内置 AI 的 {n_pts} 个号·点里 {n_blk} 个全被挡（{pct(n_blk, n_pts)}）；被挡的关（一个点可以有多关）："
          + "、".join(f"{k} {v}" for k, v in sorted(why_all.items(), key=lambda kv: -kv[1])[:6]))
        SUM["attr"].update({"censusPts": n_pts, "censusBlocked": n_blk})

    text = "\n".join(lines) + "\n"
    with open(os.path.join(OUT, mid, f"landcap{suf}.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(OUT, mid, f"landcap_sum{suf}.json"), "w", encoding="utf-8") as f:
        json.dump(SUM, f, ensure_ascii=False)
    if not quiet:
        print(text)
    else:
        print(f"{mid}: landcap{suf}.txt {len(lines)} 行")


if __name__ == "__main__":
    main()
