#!/usr/bin/env python3
"""issueq.py — 从影子缓存里打出某个号在一段本地拍内发的每一条指令，以及它在录像里落地的服务器拍（不重跑重放）。

out/cache/<mid>-shadow.json 的 bots[号].cmds 每条：[本地发令拍, 种类(1陆攻 2捐款 3船), pct, 目标, 本地是否受理, 发令时余额, 发令时领土, 调用栈]
bots[号].match.execOf[i] = 第 i 条在录像里的落地拍（-1 = 没落地）。

用法：
  python3 scripts/issueq.py <mid> <号|squad> <t0> <t1> [--flush]
  --flush  按落地拍合并：每个落地拍收了哪些本地拍发出的指令、最早/最晚一条等了多少拍；没落地的单列
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NEUTRAL = 512
KIND = {1: "攻", 2: "捐", 3: "船"}


def k(v):
    v = float(v)
    a = abs(v)
    if a >= 1e6:
        return "%.2fM" % (v / 1e6)
    if a >= 1e4:
        return "%.0fk" % (v / 1e3)
    if a >= 1e3:
        return "%.1fk" % (v / 1e3)
    return "%d" % v


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 4:
        print(__doc__)
        sys.exit(2)
    mid, who, t0, t1 = args[0], args[1], int(args[2]), int(args[3])
    sh = json.load(open(os.path.join(ROOT, "out", "cache", f"{mid}-shadow.json")))
    rs = json.load(open(os.path.join(ROOT, "out", "cache", f"{mid}-resim.json")))
    H, names = rs["H"], rs["names"]
    sq = {v["id"]: n for n, v in rs["squad"].items()}

    def nm(p):
        if p == NEUTRAL:
            return "无主地"
        if p in sq:
            return sq[p]
        if isinstance(p, int) and 0 <= p < H:
            return f"{names[p][:12]}#{p}T{rs['teams'][p]}"
        return f"AI{p}" if isinstance(p, int) and p < NEUTRAL else str(p)

    bots = list(sh["bots"]) if who == "squad" else who.split(",")
    for bot in bots:
        b = sh["bots"][bot]
        ex = b["match"]["execOf"]
        rows = [(i, c) for i, c in enumerate(b["cmds"]) if t0 <= c[0] <= t1]
        print(f"# {mid} {bot}（me={b['me']}）本地 {t0}~{t1} 拍发令 {len(rows)} 条；落地 {sum(1 for i, _ in rows if ex[i] >= 0)} 条")
        if "--flush" in sys.argv:
            by = {}
            for i, c in rows:
                by.setdefault(ex[i], []).append(c)
            for e in sorted(by, key=lambda x: (x < 0, x)):
                lst = by[e]
                ts = [c[0] for c in lst]
                tg = {}
                for c in lst:
                    key = KIND.get(c[1], str(c[1])) + nm(c[3]) if c[1] != 3 else "船"
                    tg[key] = tg.get(key, 0) + 1
                rej = sum(1 for c in lst if not c[4])
                if e < 0:
                    print(f"  没落地 {len(lst)} 条（其中本地就被拒 {rej}）：本地拍 {min(ts)}~{max(ts)} | {' '.join(f'{a}×{n}' for a, n in tg.items())} | pct {min(c[2] for c in lst)}~{max(c[2] for c in lst)}")
                else:
                    print(f"  落地拍 {e}：{len(lst)} 条，本地拍 {min(ts)}~{max(ts)}（等了 {e - max(ts)}~{e - min(ts)} 拍）| {' '.join(f'{a}×{n}' for a, n in tg.items())} | pct {[c[2] for c in lst]}")
            continue
        print("#  本地拍 种类 pct 目标 | 发令时余额 领土 | 本地受理 | 落地拍（等待）| 源码行")
        for i, c in rows:
            t, kind, pct, q, acc, B, L = c[:7]
            st = c[7].split(">") if len(c) > 7 and c[7] else []
            src = next((s for s in reversed(st) if not s.startswith("send:")), "")
            e = ex[i]
            print(f"  {t:5d} {KIND.get(kind, kind)} pct={pct:4d} → {('船' if kind == 3 else nm(q)):20s} | {k(B):>7s} {L:6d} | {'受理' if acc else '被拒'} | "
                  f"{(str(e) + '（+' + str(e - t) + '）') if e >= 0 else '没落地'} | {src}")


if __name__ == "__main__":
    main()
