#!/usr/bin/env python3
"""发船审计（读 out/cache/<局>-resim.json，重放精确值，不跑引擎）。

用法：python3 scripts/boat-audit.py <局> [--cuts t1,t2,...] [--burst 60] [--json 输出文件]

每个号、每个时间段（--cuts 给分段点，默认 0/1500/4284/结束）一行：
  发船数、船上兵合计、船费合计（引擎每条船收余额的 32/1024，与装兵多少无关）、装兵少于船费的条数；
  出港当拍落点归属（中立 / 敌方真人 / AI / 自己 / 队友）；
  同落点连发：同一个号、同一个落点格、相邻两条间隔 ≤ --burst 拍的并成一串，「多余」= 串里第 1 条以外的条数与它们的船费；
  靠岸：落在中立 / 敌方 / 自己的地（整船兵退回余额，受 150×领土 封顶）/ 队友的地（移交，超额蒸发）各多少条多少兵；
  没有靠岸记录的条数 = 该段发船数 − 该段出港的船里有靠岸记录的条数（按「同一个号先发先到」配对，只作近似）。
口径：cmdLog 发船行 [t, 号, 3, pct, 落点码, ok, 船上兵, 船费, 余额, 领土, 出港当拍落点归属]；landings 行 [t, 号, 落点归属, 船上兵, 对方到账, 额度, 上限]。
  落点码 = 指令里的 dZ = (落点旁的水格 << 3) | 方向（resim.mjs L477：water = dZ >> 3, dir = dZ & 7），不是 y×W+x；这里只把它当「同一个落点」的键用，不解成坐标。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NEUTRAL = 512


def k(x):
    x = float(x)
    if abs(x) >= 1e6:
        return f"{x / 1e6:.2f}M"
    if abs(x) >= 1e4:
        return f"{x / 1e3:.0f}k"
    if abs(x) >= 1e3:
        return f"{x / 1e3:.1f}k"
    return f"{x:.0f}"


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)
    mid = args[0]

    def opt(name, default=None):
        if name in args:
            return args[args.index(name) + 1]
        return default

    R = json.load(open(os.path.join(ROOT, "out", "cache", f"{mid}-resim.json")))
    H, names, teams, end = R["H"], R["names"], R["teams"], R["endTick"]
    squad = {b: s["id"] for b, s in R["squad"].items() if s["id"] >= 0}
    my_team = teams[next(iter(squad.values()))]
    left = R["leftT"]
    cuts = [int(x) for x in opt("--cuts", "0,1500,4284").split(",")]
    if cuts[0] != 0:
        cuts = [0] + cuts
    cuts = cuts + [end + 1]
    burst_gap = int(opt("--burst", "60"))

    def cls(owner, p):
        if owner == NEUTRAL:
            return "中立"
        if owner == p:
            return "自己"
        if owner >= H:
            return "AI"
        if teams[owner] == my_team:
            return "队友"
        return "敌方真人"

    out = {}
    for bot, p in sorted(squad.items(), key=lambda kv: kv[1]):
        boats = [c for c in R["cmdLog"] if c[2] == 3 and c[1] == p and c[5]]
        lands = [l for l in R["landings"] if l[1] == p]
        if not boats:
            continue
        # 同落点连发串
        chains = []
        for c in boats:
            if chains and chains[-1][-1][4] == c[4] and c[0] - chains[-1][-1][0] <= burst_gap:
                chains[-1].append(c)
            else:
                chains.append([c])
        extra_of = {}
        for ch in chains:
            for i, c in enumerate(ch):
                extra_of[id(c)] = (i > 0, len(ch))
        rows = []
        for a, b in zip(cuts, cuts[1:]):
            bs = [c for c in boats if a <= c[0] < b]
            ls = [l for l in lands if a <= l[0] < b]
            if not bs and not ls:
                continue
            dest = {}
            for c in bs:
                d = cls(c[10], p)
                dest[d] = dest.get(d, 0) + 1
            extra = [c for c in bs if extra_of[id(c)][0]]
            n_chain = len([ch for ch in chains if a <= ch[0][0] < b and len(ch) > 1])
            lc = {}
            for l in ls:
                d = cls(l[2], p)
                e = lc.setdefault(d, [0, 0, 0])
                e[0] += 1
                e[1] += l[3]
                e[2] += l[4]
            row = {
                "from": a, "to": min(b, end), "boats": len(bs), "troops": sum(c[6] for c in bs), "fee": sum(c[7] for c in bs),
                "feeGtTroops": sum(1 for c in bs if c[7] > c[6]), "pct0": sum(1 for c in bs if c[3] == 0),
                "destAtLaunch": dest, "sameDestChains": n_chain, "extraBoats": len(extra), "extraFee": sum(c[7] for c in extra),
                "landings": {d: {"n": e[0], "troops": e[1], "got": e[2]} for d, e in lc.items()},
                "online": left[p] < 0 or left[p] >= b,
            }
            rows.append(row)
        out[bot] = {"id": p, "leftT": left[p], "totalBoats": len(boats), "totalLandings": len(lands), "rows": rows,
                    "longestChain": max((len(ch) for ch in chains), default=0)}

    print(f"{mid} 发船审计（结束拍 {end}；分段点 {cuts[:-1]}；同落点连发间隔 ≤{burst_gap} 拍）")
    tot = {}
    for bot, o in out.items():
        print(f"  {bot}#{o['id']}{'（离线 ' + str(o['leftT']) + '，离线后的船是内置 AI 发的）' if o['leftT'] >= 0 else ''}：整局发船 {o['totalBoats']} 条，靠岸记录 {o['totalLandings']} 条，最长同落点连发 {o['longestChain']} 条")
        for r in o["rows"]:
            d = " ".join(f"{kk}{v}" for kk, v in r["destAtLaunch"].items())
            ld = " ".join(f"{kk} {v['n']}条/{k(v['troops'])}兵" + (f"(到账 {k(v['got'])})" if kk in ("队友", "自己") else "") for kk, v in r["landings"].items())
            print(f"    {r['from']:>5}~{r['to']:<5} 发 {r['boats']:>3} 条 兵 {k(r['troops']):>7} 船费 {k(r['fee']):>7}（装兵<船费 {r['feeGtTroops']} 条，pct=0 的 {r['pct0']} 条）| 出港时落点：{d or '-'} | 同落点连发 {r['sameDestChains']} 串，多余 {r['extraBoats']} 条 船费 {k(r['extraFee'])} | 靠岸：{ld or '无'}")
            key = (r["from"], r["to"])
            t = tot.setdefault(key, {"boats": 0, "troops": 0, "fee": 0, "extra": 0, "extraFee": 0, "neutralLand": 0, "ownLand": 0, "mateLand": 0, "mateTroops": 0, "mateGot": 0})
            if o["leftT"] < 0 or o["leftT"] >= r["to"]:
                t["boats"] += r["boats"]; t["troops"] += r["troops"]; t["fee"] += r["fee"]; t["extra"] += r["extraBoats"]; t["extraFee"] += r["extraFee"]
                t["neutralLand"] += r["landings"].get("中立", {}).get("n", 0)
                t["ownLand"] += r["landings"].get("自己", {}).get("n", 0)
                m = r["landings"].get("队友", {})
                t["mateLand"] += m.get("n", 0); t["mateTroops"] += m.get("troops", 0); t["mateGot"] += m.get("got", 0)
    print("  在线号合计：")
    for (a, b), t in sorted(tot.items()):
        print(f"    {a:>5}~{b:<5} 发 {t['boats']} 条 兵 {k(t['troops'])} 船费 {k(t['fee'])} | 同落点多余 {t['extra']} 条 船费 {k(t['extraFee'])} | 靠岸：中立 {t['neutralLand']} 自己的地 {t['ownLand']} 队友的地 {t['mateLand']}（船上 {k(t['mateTroops'])} 到账 {k(t['mateGot'])}）")
    j = opt("--json")
    if j:
        json.dump({"cuts": cuts, "bots": out, "total": {f"{a}-{b}": t for (a, b), t in tot.items()}}, open(j, "w"), ensure_ascii=False)


if __name__ == "__main__":
    main()
