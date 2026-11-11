#!/usr/bin/env python3
"""bursts.py — 指令是「一条一条到」还是「攒一批同拍到」：录像真值（out/<局>/resim.json 的 cmdLog）× 日志 cmds 计数。

    python3 bursts.py <matchId> [<matchId> ...]            # 写 out/<matchId>/bursts.txt 并打印
    python3 bursts.py <matchId> --bot <名字> [--t0 a --t1 b]   # 单个号：录像里每一批（同一执行拍）× 影子在本地哪几拍发的（要 out/<局>/shadow.json）

节：
  [BA] 同一个号同一执行拍到达的指令条数分布：本编队 vs 同房其他真人，分 t<700 / 700~2100 / ≥2100 三段
  [BB] 每个号：本地发出的指令数（日志最后一条 HL-TICK 的 cmds）vs 录像里记下的条数（陆攻/发船/捐款），差额；
       日志里的捐款笔数 vs 录像里的捐款条数（被额度拒的捐款不进录像，要从差额里扣掉）
  [BC] 每个号 ≥3 条的批：执行拍、条数、其中没生效的条数、目标已不在（记成空地 512）的条数
口径：
  · 录像只记通过了前置校验的指令（引擎 qj.i6：记录 rg.rh 在 jt 战线校验之前、在目标/空槽校验之后）；
    目标阵亡时引擎把目标改成 512（空地）再记，所以录像里的「→空地 且没生效」可能是原本打某个已阵亡的号。
  · 本地发出数取 HL-TICK 的 cmds（陆攻、发船、捐款、助攻都算）；最后一条快照之后发的不在内，所以差额是下限。
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facts  # noqa: E402

OUT = os.path.join(HERE, "..", "out")
NEUTRAL = 512
KIND = {1: "陆攻", 2: "捐款", 3: "发船", 4: "追船", 5: "撤军"}
PERIODS = (("t<700", 0, 700), ("700~2100", 700, 2100), ("≥2100", 2100, 10 ** 9))


def load(mid):
    R = json.load(open(os.path.join(OUT, mid, "resim.json"), encoding="utf-8"))
    F = facts.build(mid)
    cl = [c for c in R["cmdLog"] if c[2] in KIND and c[0] >= 0]
    return R, F, cl


def groups(cl, players, t0, t1):
    per = collections.Counter()
    for c in cl:
        if c[1] in players and t0 <= c[0] < t1:
            per[(c[1], c[0])] += 1
    h = collections.Counter(per.values())
    n = sum(per.values())
    big = sum(k * v for k, v in h.items() if k >= 3)
    return n, dict(sorted(h.items())), big


def analyse(mid):
    R, F, cl = load(mid)
    H = R["H"]
    ours = {int(m) for m in F["bots"]}
    others = set(range(H)) - ours
    P = [f"[BA] {mid} 同一个号同一执行拍到达的指令条数（陆攻/发船/捐款/撤军）：时段 | 本编队 条数、批大小分布、落在 ≥3 条批里的条数(占比) | 同房其他真人 同口径"]
    for lab, a, b in PERIODS:
        n1, h1, b1 = groups(cl, ours, a, b)
        n2, h2, b2 = groups(cl, others, a, b)
        P.append(f"     {lab} | 本编队 {n1} 条 {h1} ≥3 条批 {b1}（{100 * b1 / max(1, n1):.0f}%）| 其他真人 {n2} 条 {h2} ≥3 条批 {b2}（{100 * b2 / max(1, n2):.0f}%）")
    by = collections.defaultdict(list)
    for c in cl:
        by[c[1]].append(c)
    P.append("[BB] 号 队 结局 | 最后快照拍 本地发出 cmds(其中船) | 录像记下 条数(生效) 陆攻/发船/捐款 | 日志捐款笔数 | 差额=发出−录像−(日志捐款−录像捐款)")
    ti = tr = td = 0
    for me, b in F["bots"].items():
        tk = b["ticks"]
        if not tk:
            continue
        last = tk[-1]
        cs = by[int(me)]
        k = collections.Counter(c[2] for c in cs)
        ok = sum(1 for c in cs if c[5])
        ndon = len(b.get("donations") or [])
        gap = last["cmds"] - len(cs) - max(0, ndon - k[2])
        ti += last["cmds"]
        tr += len(cs)
        td += gap
        P.append(f"     {b['name']}({me}) T{b['team']} {b['event']}@{b.get('deathTick')} | t={last['t']} {last['cmds']}({last['boats']}) | {len(cs)}({ok}) {k[1]}/{k[3]}/{k[2]} | {ndon} | {gap}")
    P.append(f"     合计：本地发出 {ti}，录像记下 {tr}，扣掉被拒捐款后的差额 {td}（{100 * td / max(1, ti):.0f}%）")
    P.append("[BC] ≥3 条的批：号 | 执行拍 | 条数 | 没生效 | 记成空地(512)且没生效 | pct 序列（到达顺序）")
    nb = nfail = ndead = ncmd = 0
    rows = []
    for me in sorted(ours):
        per = collections.defaultdict(list)
        for c in by[me]:
            per[c[0]].append(c)
        for t in sorted(per):
            g = per[t]
            if len(g) < 3:
                continue
            fail = sum(1 for c in g if not c[5])
            dead = sum(1 for c in g if not c[5] and c[2] == 1 and c[4] == NEUTRAL)
            nb += 1
            ncmd += len(g)
            nfail += fail
            ndead += dead
            rows.append((F["bots"][me]["name"], t, len(g), fail, dead, [c[3] for c in g]))
    for r in rows[:60]:
        P.append(f"     {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]}")
    if len(rows) > 60:
        P.append(f"     …（共 {len(rows)} 批，只列前 60）")
    P.append(f"     合计：{nb} 批 {ncmd} 条，其中没生效 {nfail} 条（{100 * nfail / max(1, ncmd):.0f}%），记成空地且没生效 {ndead} 条；最大批 {max([r[2] for r in rows] or [0])} 条")
    return P


def one_bot(mid, name, t0, t1):
    R, F, cl = load(mid)
    me = next(int(m) for m, b in F["bots"].items() if b["name"] == name)
    names = [str(n).strip() for n in R["names"]]
    H = R["H"]

    def tgt(q):
        return "空地" if q >= NEUTRAL else (names[q] if q < H and q < len(names) else f"AI{q}")

    per = collections.defaultdict(list)
    for c in cl:
        if c[1] == me and t0 <= c[0] <= t1:
            per[c[0]].append(c)
    sh = None
    p = os.path.join(OUT, mid, "shadow.json")
    if os.path.exists(p):
        S = json.load(open(p, encoding="utf-8"))
        sh = [c for c in S["bots"].get(name, {}).get("cmds", []) if c[1] == 1]
    P = [f"{name}({me}) 录像里的每一批（执行拍 | 条数 | 到达顺序的 pct→目标 生效?）；影子 = 干净策略在真局面上不滞后时在本地哪一拍发的同 pct 指令（按到达顺序倒着对）"]
    for t in sorted(per):
        g = per[t]
        P.append(f"   执行拍 {t} | {len(g)} 条 | " + "  ".join(f"{KIND[c[2]]}{c[3]}→{tgt(c[4]) if c[2] == 1 else c[4]}{'✓' if c[5] else '✗'}" for c in g))
        if sh and len(g) >= 3:
            want = [c[3] for c in g if c[2] == 1]
            best = None
            for i in range(len(sh)):
                seq = [x[2] for x in sh[i:i + len(want)]][::-1]
                if seq == want:
                    best = sh[i:i + len(want)]
                    break
            if best:
                P.append(f"       影子逐条对上（倒序）：本地发出拍 {[x[0] for x in best][::-1]}，原目标 {[tgt(x[3]) for x in best][::-1]} → 晚了 {t - best[-1][0]}~{t - best[0][0]} 拍")
            else:
                P.append("       影子里没有逐条相同的 pct 串（影子内部状态与真机不完全一致时会这样）")
    return P


def main():
    a = sys.argv[1:]
    if "--bot" in a:
        mid = a[0]
        name = a[a.index("--bot") + 1]
        t0 = int(a[a.index("--t0") + 1]) if "--t0" in a else 0
        t1 = int(a[a.index("--t1") + 1]) if "--t1" in a else 10 ** 9
        print("\n".join(one_bot(mid, name, t0, t1)))
        return
    for mid in a:
        P = analyse(mid)
        with open(os.path.join(OUT, mid, "bursts.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(P) + "\n")
        print("\n".join(P))


if __name__ == "__main__":
    main()
