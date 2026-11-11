#!/usr/bin/env python3
"""lag-from-log.py — 从 in_game.log 的全局行序号估计每个号的本地时钟相对队友落后多少拍。

用法：
  python3 lag-from-log.py A051            # 每个号的最大落后、落后 ≥90 拍的区间
  python3 lag-from-log.py A051 --detail   # 逐条 HL-TICK 的落后量
  python3 lag-from-log.py                 # R03 全部对局各一行

原理：in_game.log 第一列是采集层给所有号共用的递增行序号，行的先后 = 墙钟先后。
每个号每 90 拍打一行 [HL-TICK] t=…。某号打出 t=T 这一行时，取此前（序号更小）所有本局号
已经打出的最大 t 作为「队内最前的本地时钟」F，落后量 = F − T（精度 90 拍，只能看出 ≥90 拍的落后）。
只是相对量：如果全队一起落后于服务器，这里看不出来（那要用 cmd-exec.py 的捐款决策→执行延迟）。
另：回放里的掉线拍（id 9）对比 results.csv 的本地离场拍，给出离场号当时落后服务器多少拍。
"""
import os
import re
import sys
from collections import defaultdict

import c136lib as L

TICK_RE = re.compile(r"^(\d+)\t\[([^\]]+)\] \[HL-TICK\] t=(\d+)")


def analyze(mid, detail=False):
    path = os.path.join(L.bundle_dir(mid), "in_game.log")
    if not os.path.exists(path):
        print(f"{mid}: 没有 in_game.log")
        return
    rep = L.load_replay(mid)
    valid = set(L.squad_map(mid, rep).values()) if rep else None
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = TICK_RE.match(line)
            if not m:
                continue
            bot = m.group(2)
            if valid is not None and bot not in valid:
                continue
            rows.append((int(m.group(1)), bot, int(m.group(3))))
    rows.sort()
    front = 0
    lag = defaultdict(list)
    for seq, bot, t in rows:
        front = max(front, t)
        lag[bot].append((t, front - t, seq))
    parts = []
    for bot in sorted(lag):
        mx = max(lag[bot], key=lambda x: x[1])
        spans = []
        cur = None
        for t, d, _ in lag[bot]:
            if d >= 90:
                if cur is None:
                    cur = [t, t, d]
                else:
                    cur[1] = t
                    cur[2] = max(cur[2], d)
            elif cur is not None:
                spans.append(cur)
                cur = None
        if cur is not None:
            spans.append(cur)
        if mx[1] >= 90:
            parts.append(f"{bot} 最大落后{mx[1]}拍(本地t={mx[0]}) 区间" + ",".join(f"{a}~{b}(峰{c})" for a, b, c in spans))
        if detail:
            print(f"  {bot}: " + " ".join(f"{t}:{d}" for t, d, _ in lag[bot]))
    leave = []
    if rep:
        squad = L.squad_map(mid, rep)
        res = {r["bot"]: r for r in L.load_results(mid)}
        for pid, bot in squad.items():
            dc = [t for t, cid, p, a, b in rep["cmds"] if p == pid and cid in (L.CMD_SURRENDER, L.CMD_DISCONNECT)]
            r = res.get(bot)
            if dc and r and r["event"] == "left":
                leave.append(f"{bot} 本地离场拍{r['tick']} 服务器掉线拍{dc[0]}(落后{dc[0] - r['tick']})")
    print(f"{mid} 队内相对落后≥90拍的号 {len(parts)} 个：" + ("；".join(parts) if parts else "无")
          + (" | 离场：" + "；".join(leave) if leave else ""))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    detail = "--detail" in sys.argv
    for mid in (args or L.R03_MATCHES):
        analyze(mid, detail)


if __name__ == "__main__":
    main()
