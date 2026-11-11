#!/usr/bin/env python3
"""dupcmds.py — 从录像命令流里数「盲目重发」：同一个号对同一个目标的同类指令，在前一条生效之前又发了一条。

背景：指令从发出到引擎执行有延迟（录像里指令只在 7 拍一个的回合点执行，exec-layer.tsv 的中位延迟 12~16 拍），
策略每 period 拍决策一次（g09=2，c110/c116=5），决策时看到的余额还没扣掉在途指令，于是同一笔出兵会被重复下单。
每条指令按「执行时余额」的 (pct+1)/1024 抽兵，所以 n 条重复指令合计抽走 1-∏(1-f_i)，远大于本意的 f_1。

口径：
  同号、同类（attack/boat/donate）、同目标的指令，相邻两条的执行拍相差 ≤ GAP（默认 14 拍 = 两个回合）算一串。
  串长 ≥2 记为一次「重发串」。严格口径另给「同一执行拍」的串（GAP=0）。
  合计抽兵比例 comb = 1-∏(1-(pct+1)/1024)；本意 first = 第一条的 (pct+1)/1024。

输入：replay_cmds.mjs 生成的 TSV（tick id kind player name a b targetName），以及 identity-map-discovery.csv 里的席位。
用法：
  python3 dupcmds.py <matchId> [--gap 14] [--cohort squad20] [--top 12]
  需要先生成 out/<matchId>/cmds.tsv：
    bash c136-review/tools/run-heavy.sh node /agent/repos/c136-data/src/tools/replay_cmds.mjs <matchId> --out c136-review/agents/R08/out/<matchId>/cmds.tsv
输出：stdout 文本 + out/<matchId>/dupcmds.json
"""
import csv
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
DATA = os.environ.get("C136_DATA", "/agent/repos/c136-data")
IDMAP = os.path.join(DATA, "src", "tools", "identity-map-discovery.csv")


def seats_of(mid):
    """返回 {cohort: {me: 名字链}}。同一局录像里可能有两支编队（B 组与 A 组碰撞）。"""
    rows = list(csv.DictReader(open(IDMAP, encoding="utf-8")))
    mine = [r for r in rows if r["matchId"] == mid]
    out = defaultdict(dict)
    for r in mine:
        if r["me"].strip().lstrip("-").isdigit():   # 没解析出席位号的行跳过
            out[r["cohort"]][int(r["me"])] = r["nameChain"]
    return out


def peer_of(mid):
    card = json.load(open(os.path.join(DATA, "bundles", mid, "card.json"), encoding="utf-8"))
    p = card.get("sameMatchPeer") or {}
    return p.get("peerMatchId")


def load_cmds(mid):
    path = os.path.join(OUT, mid, "cmds.tsv")
    cmds = []
    with open(path, encoding="utf-8") as f:
        next(f)
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) < 7:
                continue
            tick, cid, kind, player, name, a, b = p[:7]
            tname = p[7] if len(p) > 7 else ""
            cmds.append(dict(t=int(tick), id=int(cid), kind=kind, me=int(player), name=name, a=a, b=b, tname=tname))
    return cmds


def clusters(cmds, seats, gap):
    per = defaultdict(list)
    for c in cmds:
        if c["me"] in seats and c["kind"] in ("attack", "boat", "donate") and c["t"] >= 0:
            per[(c["me"], c["kind"], c["b"])].append(c)
    out = []
    for (me, kind, tgt), lst in per.items():
        cur = [lst[0]]
        for c in lst[1:]:
            if c["t"] - cur[-1]["t"] <= gap:
                cur.append(c)
            else:
                out.append(cur)
                cur = [c]
        out.append(cur)
    return out


def frac(c):
    return min(1.0, (int(c["a"]) + 1) / 1024)


def summarize(mid, cohort, seats, cmds, gap, top):
    res = {}
    for label, g in (("gap", gap), ("sameTick", 0)):
        cl = clusters(cmds, seats, g)
        by_kind = defaultdict(lambda: dict(cmds=0, clusters=0, dupClusters=0, dupCmds=0, extraCmds=0, sizes=defaultdict(int)))
        dups = []
        for c in cl:
            k = by_kind[c[0]["kind"]]
            k["cmds"] += len(c)
            k["clusters"] += 1
            k["sizes"][min(len(c), 9)] += 1
            if len(c) >= 2:
                k["dupClusters"] += 1
                k["dupCmds"] += len(c)
                k["extraCmds"] += len(c) - 1
                keep = 1.0
                for x in c:
                    keep *= 1 - frac(x)
                dups.append(dict(me=c[0]["me"], name=c[0]["name"], kind=c[0]["kind"], target=c[0]["b"], targetName=c[0]["tname"],
                                 t0=c[0]["t"], t1=c[-1]["t"], n=len(c), pcts=[int(x["a"]) for x in c],
                                 first=round(frac(c[0]), 4), comb=round(1 - keep, 4)))
        res[label] = dict(gap=g, byKind={k: dict(v, sizes=dict(v["sizes"])) for k, v in by_kind.items()},
                          dups=sorted(dups, key=lambda d: -d["comb"]))
    print(f"== {mid} / {cohort}：{len(seats)} 个席位")
    for label in ("gap", "sameTick"):
        r = res[label]
        print(f"  [{'相邻执行拍相差≤%d' % r['gap'] if label == 'gap' else '同一执行拍'}]")
        for kind, v in sorted(r["byKind"].items()):
            share = 100 * v["extraCmds"] / max(1, v["cmds"])
            sizes = " ".join(f"{n}条×{c}" for n, c in sorted(v["sizes"].items()) if n >= 2)
            print(f"    {kind:<7} 指令 {v['cmds']:>5}，其中多发的 {v['extraCmds']:>4}（{share:.0f}%）；重发串 {v['dupClusters']}：{sizes}")
        big = [d for d in r["dups"] if d["kind"] != "donate"][:top if label == "gap" else max(3, top // 3)]
        for d in big:
            print(f"      t={d['t0']}~{d['t1']} {d['name']}({d['me']}) {d['kind']}→{d['targetName'] or d['target']} ×{d['n']} pct={d['pcts']} "
                  f"本意 {100 * d['first']:.0f}% 合计 {100 * d['comb']:.0f}%")
    return res


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    mid = args[0]
    gap = int(args[args.index("--gap") + 1]) if "--gap" in args else 14
    top = int(args[args.index("--top") + 1]) if "--top" in args else 12
    only = args[args.index("--cohort") + 1] if "--cohort" in args else None
    cmds = load_cmds(mid)
    allseats = dict(seats_of(mid))
    peer = peer_of(mid)
    if peer:
        for coh, s in seats_of(peer).items():
            allseats[coh + ":" + peer] = s
    out = {}
    for coh, seats in allseats.items():
        if only and not coh.startswith(only):
            continue
        out[coh] = summarize(mid, coh, seats, cmds, gap, top)
    with open(os.path.join(OUT, mid, "dupcmds.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
