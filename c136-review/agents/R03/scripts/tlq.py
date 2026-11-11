#!/usr/bin/env python3
"""tlq.py — 把 out/dossier/<mid>-facts.json 的 timeline 打成复盘时间线表要用的三列（只做单位换算，不算新数）。

用法：python3 scripts/tlq.py <mid> [拍,拍,…]
每行：拍 | 各队地%（全图陆地）与在线真人的兵（万）| 编队：号数 · 地% · 兵（万；密度）| AI% 中立%
不给拍表就打全部采样拍。输出给 reviews/<mid>.md 第 2 节直接抄。
自由混战（没有队伍）的局：拍 | 全体真人/AI/无主地 %、在线真人数、编队之外最大的真人 | 编队：号数 · 地% · 兵、编队里最大的号（在真人里排第几）、空壳。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def wan(v):
    v = float(v)
    if v >= 1e8:
        return "%.2f 亿" % (v / 1e8)
    if v >= 1e7:
        return "{:,.0f} 万".format(v / 1e4)
    if v >= 1e6:
        return "%.0f 万" % (v / 1e4)
    if v >= 1e5:
        return "%.1f 万" % (v / 1e4)
    if v >= 1e4:
        return "%.2f 万" % (v / 1e4)
    return "{:,.0f}".format(v)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    mid = sys.argv[1]
    want = None
    if len(sys.argv) > 2:
        want = {int(x) for x in sys.argv[2].split(",") if x}
    f = json.load(open(os.path.join(ROOT, "out", "dossier", f"{mid}-facts.json")))
    print(f"# {mid} 时间线换算（facts.json 的 timeline；兵按万）")
    for r in f["timeline"]:
        t = r["t"]
        if want and t not in want:
            continue
        if "teamSharePct" not in r and "humanSharePct" in r:
            # 自由混战（没有队伍）的局：全体真人 / AI / 无主地、编队之外最大的真人、编队与编队里最大的号
            to, tq = r.get("topOther"), r.get("topSquad")
            other = f"编队外最大 {to['who']} {to['sharePct']}%（{to['terr']:,} 格、{wan(to['bal'])}兵）" if to else "编队外没有在线真人"
            top = f"；最大的号 {tq['bot']} {tq['sharePct']}%（{tq['terr']:,} 格、{wan(tq['bal'])}兵，真人里第 {tq['rankAmongHumans']}）" if tq else ""
            husk = r.get("husks")
            hs = f"；另有空壳 {husk['n']} 个 {husk['sharePct']}%（{husk['terr']:,} 格、{wan(husk['bal'])}兵）" if husk else ""
            print(
                f"{t:>5} | 真人 {r['humanSharePct']}%（在线 {r['onlineHumans']} 人）AI {r['aiSharePct']}% 无主 {r['neutralSharePct']}%；{other}"
                f" | 编队 {r['alive']} 个号 · {r['sqSharePct']}%（{r['sqTerr']:,} 格）· {wan(r['sqBal'])}兵（密度 {r['sqDens']}）{top}{hs}"
            )
            continue
        ts = r.get("teamSharePct", {})
        tb = r.get("teamOnlineBal", {})
        th = r.get("teamOnlineHumans", {})
        teams = "；".join(
            f"{k.replace('T', '队')} {ts[k]}%" + (f"（在线 {th.get(k)} 人 {wan(tb[k])}兵）" if k in tb else "")
            for k in sorted(ts, key=lambda x: int(x[1:]))
        )
        print(
            f"{t:>5} | {teams} | 编队 {r['alive']} 个号 · {r['sqSharePct']}%（{r['sqTerr']:,} 格）· {wan(r['sqBal'])}兵（密度 {r['sqDens']}）"
            f" | AI {r.get('aiSharePct')}% 中立 {r.get('neutralSharePct')}%"
        )


if __name__ == "__main__":
    main()
