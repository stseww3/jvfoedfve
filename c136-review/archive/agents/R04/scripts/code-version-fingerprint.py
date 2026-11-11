#!/usr/bin/env python3
"""code-version-fingerprint.py — 用局内日志里的捐款/调度事件给每一局的「实际运行的策略版本」打指纹。

动机：/agent/repos/c136-data/src/strategy/ 里每个编队只有一份源码快照（v27-team-c116.js 等），
而对局跨了三天。若某局日志里出现了快照源码不可能打印出来的事件（pct、最小间隔、dMe 门槛、kind 名称），
说明该局跑的不是这份快照，代码行级复盘就不能直接套用快照里的阈值。

输入：/agent/repos/c136-data/bundles/<matchId>/{card.json,events.csv}
输出：TSV（标准输出），每局一行；末尾按指纹分组汇总。

用法：python3 code-version-fingerprint.py [bundles 目录] > ../out/code-version-fingerprint.tsv
"""
import csv
import json
import os
import sys
from collections import Counter, defaultdict

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/agent/repos/c136-data/bundles"


def fnum(x):
    try:
        return float(x)
    except Exception:
        return None


rows = []
for mid in sorted(os.listdir(ROOT)):
    d = os.path.join(ROOT, mid)
    cp = os.path.join(d, "card.json")
    ep = os.path.join(d, "events.csv")
    if not (os.path.isfile(cp) and os.path.isfile(ep)):
        continue
    card = json.load(open(cp))
    types = Counter()
    kinds = Counter()
    pcts = defaultdict(Counter)  # (type,kind) -> pct counter
    min_dme = {}
    max_dally = {}
    min_bal = {}
    last_t = {}
    min_gap = {}
    with open(ep, newline="") as f:
        for r in csv.DictReader(f):
            ty = r["type"]
            types[ty] += 1
            if ty not in ("DISPATCH", "DONATE"):
                continue
            k = (ty, r["kind"])
            kinds[k] += 1
            p = fnum(r["pct"])
            if p is not None:
                pcts[k][int(p)] += 1
            dme = fnum(r["dMe"])
            dal = fnum(r["dAlly"])
            bal = fnum(r["myBal"])
            t = fnum(r["t"])
            if dme is not None:
                min_dme[k] = min(min_dme.get(k, 1e18), dme)
            if dal is not None:
                max_dally[k] = max(max_dally.get(k, -1), dal)
            if bal is not None:
                min_bal[ty] = min(min_bal.get(ty, 1e18), bal)
            key = (ty, r["bot"])
            if t is not None:
                if key in last_t and t > last_t[key]:
                    g = t - last_t[key]
                    min_gap[ty] = min(min_gap.get(ty, 1e18), g)
                last_t[key] = t
    rows.append(dict(mid=mid, cohort=card.get("cohort"), time=card.get("timeUtc"), types=types, kinds=kinds, pcts=pcts,
                     min_dme=min_dme, max_dally=max_dally, min_bal=min_bal, min_gap=min_gap))

rows.sort(key=lambda r: (r["time"] or "", r["mid"]))


def fmt_kind(r):
    out = []
    for k in sorted(r["kinds"]):
        pc = r["pcts"][k]
        if pc:
            lo, hi = min(pc), max(pc)
            top = ",".join(f"{p}x{n}" for p, n in pc.most_common(3))
            ps = f"pct[{lo}..{hi}] top={top}"
        else:
            ps = "pct[-]"
        md = r["min_dme"].get(k)
        ma = r["max_dally"].get(k)
        out.append(f"{k[0]}:{k[1] or '-'} n={r['kinds'][k]} {ps} minDMe={md:.0f}" + (f" maxDAlly={ma:.0f}" if ma is not None and ma >= 0 else "") if md is not None else f"{k[0]}:{k[1] or '-'} n={r['kinds'][k]} {ps}")
    return " ; ".join(out)


def fingerprint(r):
    """粗指纹：DISPATCH 事件的 (kind 集合, 最大 pct, 最小间隔档)；没有 DISPATCH 则看 DONATE 的 kind 集合。"""
    dk = sorted(k[1] for k in r["kinds"] if k[0] == "DISPATCH")
    nk = sorted(k[1] for k in r["kinds"] if k[0] == "DONATE")
    if dk:
        mx = max(max(r["pcts"][("DISPATCH", k)]) for k in dk if r["pcts"][("DISPATCH", k)])
        mn = min(min(r["pcts"][("DISPATCH", k)]) for k in dk if r["pcts"][("DISPATCH", k)])
        gap = r["min_gap"].get("DISPATCH")
        return f"DISPATCH maxPct={mx} minPct={mn} minGap={int(gap) if gap is not None else '-'}"
    if nk:
        return "DONATE-only kinds=" + "/".join(nk)
    return "no-transfer-events"


print("matchId\tcohort\ttimeUtc\tfingerprint\tminBalDISPATCH\tdetail")
groups = defaultdict(list)
for r in rows:
    fp = fingerprint(r)
    groups[(r["cohort"], fp)].append(r)
    mb = r["min_bal"].get("DISPATCH")
    print(f"{r['mid']}\t{r['cohort']}\t{r['time']}\t{fp}\t{int(mb) if mb is not None else '-'}\t{fmt_kind(r)}")

print("\n# 按 (编队, 指纹) 汇总：局数、时间范围、对局列表")
for (coh, fp), rs in sorted(groups.items(), key=lambda kv: (kv[0][0], min(x["time"] for x in kv[1]))):
    ts = sorted(x["time"] for x in rs)
    print(f"# {coh}\t{fp}\tn={len(rs)}\t{ts[0]} .. {ts[-1]}\t{','.join(x['mid'] for x in rs)}")
