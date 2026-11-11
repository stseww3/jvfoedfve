#!/usr/bin/env python3
"""clockskew.py — 同一份日志里装了两个房间时，用日志行号的先后给两个房间的『客户端本地拍』对表。

    python3 clockskew.py <matchId> [--ref-room 1] [--room 0] [--stable-from 1800]

原理：HL-TICK 是各号的客户端在自己的本地模拟走到 t 拍时打的；整份日志按到达顺序编了全局行号。
两个房间的服务器都按固定节拍走，所以「参照房间的号打 t1 拍那一刻，另一个房间的号打到了第几拍」
在两边都不卡的时候是个常数（= 两个房间开局时间差 ÷ 每拍时长）。常数变小 = 另一个房间的客户端落后得更多。
参照房间有录像时，它自己的时延可以用 lagstats.py 实测（B049 房间 1），两者相加就是另一个房间客户端落后服务器的拍数下限估计。

输出：
  [KA] 参照拍 t1 | 对应的本房间各号本地拍（在该号前后两条快照之间按行号线性插值）| 中位差值 | 相对稳定差值少了多少（=多落后的拍数）
  [KB] 逐号：最落后的时刻、落后拍数；最后一条快照
  [KC] 结果行对表：结果行带写入时间和本地拍，相邻两条之间每本地拍多少毫秒（不掉拍时 = 服务器每拍时长）
"""
import os
import sys
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facts  # noqa: E402


def interp(tk, line):
    prev = nxt = None
    for s in tk:
        if s["line"] <= line:
            prev = s
        else:
            nxt = s
            break
    if prev is None or nxt is None:
        return None
    f = (line - prev["line"]) / max(1, nxt["line"] - prev["line"])
    return prev["t"] + f * (nxt["t"] - prev["t"])


def result_clock(mid):
    """[KC] 结果行自带写入时间（at）和本地拍（tick）：同一个房间相邻两条结果行之间『每本地拍多少毫秒』。
    服务器按固定节拍走，客户端不掉拍时这个数就是服务器的每拍时长；客户端在追赶时会更小，在掉队时会更大。
    按结果行的 land 列分房间（多房间的包里各房间陆地格数不同）。"""
    import csv
    import datetime as dt
    import r08lib as L
    rows = list(csv.DictReader(open(os.path.join(L.bundle_dir(mid), "results.csv"), encoding="utf-8")))
    P = ["[KC] 结果行对表：房间（按 land 分）| 结果行 号 本地拍 写入时间 | 与上一条之间每本地拍毫秒 | 按首末两条的斜率反推的 0 拍时刻"]
    by = {}
    for r in rows:
        try:
            by.setdefault(r["land"], []).append((int(float(r["tick"])), dt.datetime.fromisoformat(r["at"].replace("Z", "+00:00")), r["bot"], r["event"]))
        except (ValueError, KeyError):
            continue
    for land, rs in by.items():
        rs.sort()
        slope = None
        if len(rs) >= 2 and rs[-1][0] > rs[0][0]:
            slope = (rs[-1][1] - rs[0][1]).total_seconds() * 1000 / (rs[-1][0] - rs[0][0])
        prev = None
        for t, at, bot, ev in rs:
            ms = f"{(at - prev[1]).total_seconds() * 1000 / (t - prev[0]):.2f}" if prev and t > prev[0] else "-"
            P.append(f"     land={land} | {bot} {ev} t={t} {at.strftime('%H:%M:%S.%f')[:-3]} | {ms}")
            prev = (t, at)
        if slope:
            t0 = rs[0][1] - dt.timedelta(milliseconds=slope * rs[0][0])
            P.append(f"     land={land}：首末两条之间每本地拍 {slope:.2f} 毫秒；按此反推 0 拍在 {t0.strftime('%H:%M:%S.%f')[:-3]}")
    return P


def main():
    args = sys.argv[1:]
    mid = args[0]
    ref_room = int(args[args.index("--ref-room") + 1]) if "--ref-room" in args else 1
    room = int(args[args.index("--room") + 1]) if "--room" in args else 0
    stable_from = int(args[args.index("--stable-from") + 1]) if "--stable-from" in args else 1800
    FR = facts.full(mid, room=ref_room)
    F0 = facts.full(mid, room=room)
    ref = {}
    for b in FR["bots"].values():
        for s in b["ticks"]:
            if s["t"] not in ref or s["line"] < ref[s["t"]]:
                ref[s["t"]] = s["line"]
    bots = [b for b in F0["bots"].values() if b["ticks"]]
    rows = []
    for t1 in sorted(ref):
        line = ref[t1]
        vals = {}
        for b in bots:
            v = interp(b["ticks"], line)
            if v is not None:
                vals[b["name"]] = v
        if vals:
            rows.append((t1, line, vals))
    stable = median([median(v.values()) - t1 for t1, _, v in rows if t1 >= stable_from and t1 <= stable_from + 1800])
    P = [f"[KA] {mid} 参照=房间{ref_room}，对表=房间{room}。两边都不卡时的差值（参照拍 {stable_from}~{stable_from + 1800} 的中位数）= {stable:.0f} 拍",
         "     参照拍 t1 | 行号 | 本房间有数的号数 | 本房间本地拍 中位 (最小~最大) | 差值 | 比稳定差值少（本房间多落后的拍数）| 最落后的号"]
    worst = {}
    for t1, line, vals in rows:
        md = median(vals.values())
        lo = min(vals, key=vals.get)
        for n, v in vals.items():
            lag = stable - (v - t1)
            if n not in worst or lag > worst[n][0]:
                worst[n] = (lag, t1, v)
        if t1 <= 3600 or t1 % 900 == 0:
            P.append(f"     {t1:>5} | {line} | {len(vals):>2} | {md:7.0f} ({min(vals.values()):.0f}~{max(vals.values()):.0f}) | {md - t1:5.0f} | {stable - (md - t1):5.0f} | {lo} {stable - (vals[lo] - t1):.0f}")
    P.append("[KB] 号 | 相对参照房间最落后的时刻：参照拍 / 本地拍 / 多落后的拍数 | 最后一条快照拍")
    for b in bots:
        w = worst.get(b["name"])
        P.append(f"     {b['name']} | " + (f"{w[1]} / {w[2]:.0f} / {w[0]:.0f}" if w else "-") + f" | {b['ticks'][-1]['t']}")
    P += result_clock(mid)
    txt = "\n".join(P)
    od = os.path.join(HERE, "..", "out", mid)
    os.makedirs(od, exist_ok=True)
    open(os.path.join(od, "clockskew.txt"), "w", encoding="utf-8").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
