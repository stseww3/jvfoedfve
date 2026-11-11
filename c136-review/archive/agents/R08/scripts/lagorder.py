#!/usr/bin/env python3
"""lagorder.py — 只用日志的行序，量同一房间里每个号的本地时钟比「跑在最前面的号」落后多少拍。

    python3 lagorder.py <matchId> [--room N] [--bot 名字]     # 写 out/<matchId>/lagorder[_roomN].txt 并打印

原理：in_game.log 是所有号的输出按到达先后合并的（行号全局递增）。同一个房间里所有号跑的是同一条服务器拍序，
     所以某个号打出 HL-TICK t=T 这一行时，如果别的号早已打过 t=T+450，说明这个号的本地模拟比它们至少落后 360 拍
     （HL-TICK 每 90 拍一条，所以分辨率是 90 拍：落后量 = 之前本房间出现过的最大 t − T，真实值在 [量值, 量值+90) 里）。
     跑在最前面的号本身也可能落后于服务器，所以这是「相对落后」的下限，不是对服务器的绝对落后。
节：
  [LA] 每个号：快照数 | 落后 ≥180 拍的快照数、起止本地拍 | 最大落后量@本地拍 | 追平（落后 <90）的本地拍
  [LB] 每 90 拍：全体落后量的分布（0 / 90 / 180~360 / ≥450 各几个号）、最落后的号
  [LC] 落后段里的指令：号 | 落后 ≥180 的本地拍段 | 这一段本地发出的指令数（cmds 增量）| 这一段余额实际花掉的兵
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facts  # noqa: E402

OUT = os.path.join(HERE, "..", "out")


def series(F):
    """[(line, me, t)] 按行号排序；只取 HL-TICK 快照。"""
    rows = []
    for me, b in F["bots"].items():
        for s in b["ticks"]:
            if s.get("line") is not None:
                rows.append((s["line"], me, s["t"]))
    rows.sort()
    return rows


def analyse(mid, room=None, only=None):
    F = facts.build(mid, room=room) if room is not None else facts.build(mid)
    land = F["land"]
    rows = series(F)
    lead = -1
    lag = collections.defaultdict(dict)       # me -> {t: lag}
    for line, me, t in rows:
        lead = max(lead, t)
        lag[me][t] = lead - t
    P = [f"[LA] {mid} 相对落后（HL-TICK 行序；分辨率 90 拍）：号 队 | 快照数 | 落后≥180 的快照数 起止本地拍 | 最大落后@本地拍 | 之后第一次落后<90 的本地拍"]
    segs = {}
    for me, b in F["bots"].items():
        L = lag.get(me, {})
        if not L:
            continue
        ts = sorted(L)
        late = [t for t in ts if L[t] >= 180]
        mx = max(ts, key=lambda t: L[t])
        back = next((t for t in ts if t > mx and L[t] < 90), None)
        segs[me] = late
        P.append(f"     {b['name']}({me}) T{b['team']} | {len(ts)} | {len(late)} {(str(late[0]) + '~' + str(late[-1])) if late else '-'} | {L[mx]}@{mx} | {back if back is not None else '-'}")
    P.append("[LB] 本地拍 | 有快照的号数 | 落后 0 / 90 / 180~360 / ≥450 的号数 | 最落后的号(落后量)")
    allt = sorted({t for L in lag.values() for t in L})
    for t in allt:
        v = [(L[t], me) for me, L in lag.items() if t in L]
        if not v:
            continue
        c = [sum(1 for x, _ in v if x == 0), sum(1 for x, _ in v if x == 90), sum(1 for x, _ in v if 180 <= x <= 360), sum(1 for x, _ in v if x >= 450)]
        w = max(v)
        if c[2] + c[3] == 0 and t % 450:
            continue
        P.append(f"     {t} | {len(v)} | {c[0]} / {c[1]} / {c[2]} / {c[3]} | {F['bots'][w[1]]['name']}({w[0]})")
    P.append("[LC] 落后段里的指令：号 | 落后≥180 的本地拍段 | 段内本地发出的指令数（其中船）| 段内余额实际花掉的兵（按利息公式反推）| 段首→段末 领土")
    tot_c = tot_s = 0
    for me, late in segs.items():
        if not late:
            continue
        b = F["bots"][me]
        tk = {s["t"]: s for s in b["ticks"]}
        ts = sorted(tk)
        # 把相邻（间隔 90）的落后快照并成段
        runs, cur = [], [late[0]]
        for t in late[1:]:
            if t - cur[-1] <= 90:
                cur.append(t)
            else:
                runs.append(cur)
                cur = [t]
        runs.append(cur)
        for r in runs:
            a = max([t for t in ts if t < r[0]] or [r[0]])
            z = r[-1]
            cm = tk[z]["cmds"] - tk[a]["cmds"]
            bt = tk[z]["boats"] - tk[a]["boats"]
            spent = 0
            prev = a
            for t in [x for x in ts if a < x <= z]:
                should = facts.interest_gain(tk[prev]["terr"], land, tk[prev]["bal"], prev, t)
                spent += max(0, should - tk[t]["bal"])
                prev = t
            tot_c += cm
            tot_s += spent
            if only and b["name"] != only:
                continue
            P.append(f"     {b['name']}({me}) | {a}~{z} | {cm}({bt}) | {int(spent)} | {tk[a]['terr']}→{tk[z]['terr']}")
    P.append(f"     合计：落后段里本地发出 {tot_c} 条指令，段内余额实际花掉 {int(tot_s)} 兵")
    return P


def main():
    a = sys.argv[1:]
    mid = a[0]
    room = int(a[a.index("--room") + 1]) if "--room" in a else None
    only = a[a.index("--bot") + 1] if "--bot" in a else None
    P = analyse(mid, room, only)
    fn = "lagorder.txt" if room is None else f"lagorder_room{room}.txt"
    os.makedirs(os.path.join(OUT, mid), exist_ok=True)
    with open(os.path.join(OUT, mid, fn), "w", encoding="utf-8") as f:
        f.write("\n".join(P) + "\n")
    print("\n".join(P))


if __name__ == "__main__":
    main()
