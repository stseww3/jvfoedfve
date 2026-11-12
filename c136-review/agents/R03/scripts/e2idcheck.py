#!/usr/bin/env python3
"""e2idcheck.py — E2 检验的数据质量核对（事后加的）：名下格数表里按名字认出的编队号，和每个号自己在 results.csv 里报的玩家号（meId）对不对得上。

cells.mjs 沿用 resim.mjs 的认法：traj.csv / results.csv 里的号名，对上录像里「名字以它结尾」的第一个玩家。
认不出的号（名字对不上）在名下格数表里会被算成其他真人；认错的号（对到了别人）会把别人算成编队。
这里不跑重放，只读 manifest.jsonl、bundles/<局>/results.csv、traj.csv 和 out/council/cells/<局>.json。

  timeout 120 python3 scripts/e2idcheck.py      # 写 out/council/E2-idcheck.txt
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
DATA = os.environ.get("C136_DATA", "/agent/repos/c136-data")
CELLS = os.path.join(ROOT, "out", "council", "cells")
OUT = os.path.join(ROOT, "out", "council", "E2-idcheck.txt")
MINE = "A051 A087 A066 A025 A045 A067 A071 A090 A042 A046 A041".split()


def main():
    rows = [json.loads(l) for l in open(os.path.join(DATA, "manifest.jsonl"), encoding="utf-8") if l.strip()]
    rows = [r for r in rows if r.get("cohort") == "squad10" and r.get("split") == "discovery"]
    rows.sort(key=lambda r: r["matchId"])
    L = []
    P = L.append
    P("# E2 检验的数据质量核对（e2idcheck.py；事后加的）：按名字认出的编队号 对 每个号自己报的玩家号（results.csv 的 meId）")
    P("")
    P("[ID-1] 逐局")
    P("局 | 样本外 | 号名个数（traj 或 results） | 报了玩家号的号数 | 名下格数表里的编队号数 | 认出且与自报一致 | 认出但自报里没有 | 自报了但没认出 | 没认出的号在名下格数表里（算成了其他真人）")
    tot = dict(n=0, clean=0, wrong=0, miss=0, noself=0, unrec=0)
    bad = []
    split = []
    sqof = {}
    missof = set()
    for r in rows:
        mid = r["matchId"]
        cp = os.path.join(CELLS, f"{mid}.json")
        if not os.path.exists(cp):
            continue
        c = json.load(open(cp, encoding="utf-8"))
        ids = {p["id"] for p in c["pts"]}
        sq = {p["id"] for p in c["pts"] if p["squad"]}
        bdir = os.path.join(DATA, "bundles", mid)
        bots = set()
        me = {}
        res = []
        tp = os.path.join(bdir, "traj.csv")
        if os.path.exists(tp):
            for x in csv.DictReader(open(tp, encoding="utf-8")):
                bots.add(x["bot"])
        rp = os.path.join(bdir, "results.csv")
        if os.path.exists(rp):
            for x in csv.DictReader(open(rp, encoding="utf-8")):
                bots.add(x["bot"])
                if x.get("meId", "") != "":
                    me[x["bot"]] = int(float(x["meId"]))
                    res.append(x)
        mes = set(me.values())
        sqof[mid] = sq
        ok = sq & mes
        wrong = sq - mes
        miss = mes - sq
        miss_in = miss & ids
        tot["n"] += 1
        tot["wrong"] += 1 if wrong else 0
        tot["miss"] += 1 if miss else 0
        tot["clean"] += 1 if (not wrong and not miss) else 0
        if miss:
            missof.add(mid)
        if wrong or miss:
            bad.append((mid, len(wrong), len(miss), len(miss_in)))
        # 认出的号里自报对不上的：只要自报的玩家号全在认出的号里、多出来的个数正好等于没有自报的号数，就只是「没有自报可比」
        if wrong and not miss and len(wrong) == len(bots) - len(me):
            tot["noself"] += 1
        if len(sq) < len(bots):
            tot["unrec"] += 1
            # 分房的迹象：结算表里 seededPlayers 不止一个取值；按拍排序后 alivePlayers 回升；终局（end）的拍不止一个；自报的玩家号超出回放里的真人号
            seeded = sorted({x["seededPlayers"] for x in res if x.get("seededPlayers", "") != ""}, key=lambda v: int(float(v)))
            rs = sorted(res, key=lambda x: int(float(x["tick"])))
            lo, up = None, False
            for x in rs:
                a = int(float(x["alivePlayers"]))
                if lo is not None and a > lo:
                    up = True
                lo = a if lo is None else min(lo, a)
            ends = sorted({int(float(x["tick"])) for x in res if x["event"] == "end"})
            over = sorted(v for v in miss if v > max(ids))
            split.append((mid, len(bots), len(sq), seeded, up, ends, over, c["humans"], max(ids)))
        P(f"{mid} | {'否' if mid in MINE else '是'} | {len(bots)} | {len(me)} | {len(sq)} | {len(ok)} | {len(wrong)} | {len(miss)} | {len(miss_in)}")
    P("")
    P("[ID-2] 合计")
    P(f"有名下格数表的 {tot['n']} 局：两边完全一致的 {tot['clean']} 局；有号认出但自报里没有的 {tot['wrong']} 局；有号自报了但没认出的 {tot['miss']} 局")
    if bad:
        P("对不上的局（认出但自报里没有 / 自报了但没认出 / 其中在名下格数表里的）：" + "、".join(f"{m}（{a} / {b} / {c}）" for m, a, b, c in bad))
    P(f"「认出但自报里没有」的 {tot['wrong']} 局里，自报的玩家号全在认出的号里、多出来的个数正好等于没有自报的号数的 {tot['noself']} 局（只是那几个号没有结算行，没有自报可比）")
    P(f"号名个数多于认出的编队号数的 {tot['unrec']} 局：" + "、".join(x[0] for x in split))
    P("")
    P("[ID-3] 有号没认出的局：这些号在不在回放的房间里")
    P("局 | 样本外 | 号名个数 | 认出的号数 | 回放里开局有地的真人数（最大玩家号） | 结算表的 seededPlayers 取值 | 按拍排序后 alivePlayers 有没有回升 | 终局（end）的拍 | 自报的玩家号超出回放最大玩家号的")
    for mid, nb, ns, seeded, up, ends, over, hum, mx in split:
        P(f"{mid} | {'否' if mid in MINE else '是'} | {nb} | {ns} | {hum}（{mx}） | {'、'.join(seeded) or '—'} | {'有' if up else '没有'} | {'、'.join(str(e) for e in ends) or '—'} | {'、'.join(str(v) for v in over) or '—'}")
    two = [x[0] for x in split if len(x[3]) > 1 or x[4] or len(x[5]) > 1 or x[6]]
    P(f"合计：{len(split)} 局里，至少有一项迹象说明这些号分在不止一个房间的 {len(two)} 局（{'、'.join(two) or '没有'}）；其余 {len(split) - len(two)} 局从结算表看不出来")
    P("注：这一段只是结算表里的迹象，不够准；哪些局分了房间以 [ID-4] 的拆分表为准")
    # 与统筹下发的物理房间拆分表对照（R10 的 rooms-discovery.json；广播 0002 第 3 节）
    rp_ = os.path.join(DATA, "src", "tools", "rooms-discovery.json")
    if os.path.exists(rp_):
        rd = {r["matchId"]: r for r in json.load(open(rp_, encoding="utf-8")) if r.get("cohort") == "squad10" and r.get("split") == "discovery"}
        multi = sorted(m for m, r in rd.items() if r["nRooms"] > 1)
        P("")
        P("[ID-4] 与共享的物理房间拆分表（src/tools/rooms-discovery.json）对照")
        P(f"拆分表里 squad10 发现集 {len(rd)} 局：1 个房间的 {sum(1 for r in rd.values() if r['nRooms'] == 1)} 局，不止 1 个房间的 {len(multi)} 局（{'、'.join(multi) or '没有'}）")
        same = set(multi) == missof
        P(f"本表「有号自报了但没认出」的 {len(missof)} 局（{'、'.join(sorted(missof)) or '没有'}）与拆分表里不止 1 个房间的局{'完全相同' if same else '不完全相同'}")
        P("局 | 样本外 | 拆分表：各房间的编队号数（seededPlayers） | 拆分表的主房间 | 回放是哪个房间（按认出的玩家号对） | 回放房间里的编队号数 | 回放是不是号最多的房间")
        nminor = 0
        for m in multi:
            r = rd[m]
            rooms = r["rooms"]
            desc = "；".join(f"房间 {x['roomIdx']}：{x['nBots']} 个号（{x['seeded']}）" for x in rooms)
            sq = sqof.get(m)
            rep = None
            if sq is not None:
                for x in rooms:
                    if {b["me"] for b in x["bots"] if b.get("me") is not None} == sq:
                        rep = x
            big = max(x["nBots"] for x in rooms)
            if rep is None:
                P(f"{m} | {'否' if m in MINE else '是'} | {desc} | 房间 {r['mainRoom']} | 对不上 | — | —")
                continue
            minor = rep["nBots"] < big
            nminor += 1 if minor else 0
            P(f"{m} | {'否' if m in MINE else '是'} | {desc} | 房间 {r['mainRoom']} | 房间 {rep['roomIdx']} | {rep['nBots']} | {'不是' if minor else '是'}")
        P(f"合计：不止 1 个房间的 {len(multi)} 局里，对局包带的回放不是号最多的那个房间的 {nminor} 局")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"写 {os.path.relpath(OUT, ROOT)}（{len(L)} 行）")


if __name__ == "__main__":
    main()
