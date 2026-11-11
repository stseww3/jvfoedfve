#!/usr/bin/env python3
"""win.py — 打印一局里某个时间窗内的原始日志行（按玩家号归并后的身份），用于逐拍核对。

    python3 win.py <matchId> <t0> <t1> [me|name ...] [--no-slow] [--tags HL-TICK,HL-DONATE]

每行：日志行号 | 玩家(me) | 标签 | 正文。没有 t= 的行（RESULT、出生）按相邻行的拍号归位。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r08lib as L  # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mid, t0, t1 = args[0], int(args[1]), int(args[2])
    who = set(args[3:])
    tags = None
    for i, a in enumerate(sys.argv):
        if a == "--tags":
            tags = set(sys.argv[i + 1].split(","))
    who = {w for w in who if w not in (tags or set()) and not w.startswith("HL-")}
    no_slow = "--no-slow" in sys.argv
    recs = L.parse_log(mid)
    tracks, _, _ = L.resolve_identities(recs)
    owner = {}
    for me, tr in tracks.items():
        for r in tr.lines:
            owner[r["line"]] = (me, tr.name)
    res = {r.get("tick"): r for r in L.load_results(mid)}
    last_t = -1
    for r in recs:
        m = re.search(r"\bt=(\d+)", r["raw"])
        t = int(m.group(1)) if m and r["tag"] not in ("HL-SPAWN", "HL-SPAWN-BACKEND", "HL-GAME-INIT") else last_t
        if m:
            last_t = t
        if not (t0 <= t <= t1):
            continue
        if no_slow and r["tag"] == "HL-SLOW-TICK":
            continue
        if tags and r["tag"] not in tags:
            continue
        me, name = owner.get(r["line"], (None, r["label"]))
        if who and str(me) not in who and name not in who and (r["label"] not in who):
            continue
        body = r["raw"]
        body = re.sub(r" avgMs=[\d.]+ maxMs=[\d.]+ skip=\d+", "", body)
        print(f"L{r['line']} | {name}({me}) | {body[:300]}")


if __name__ == "__main__":
    main()
