#!/usr/bin/env python3
"""Read a list_peers dump and say who of the third shift (c318..c361) has no agent attached.

usage: peers.py <dump file>      (the newest dump under the agent-tools folder when no file is given)
Prints one line per state and the names; never prints identities.
"""
import glob, os, re, sys

CODES = {318: "s2", 319: "s1", 320: "aide", 321: "facade", 322: "a2", 323: "a4", 324: "a1", 325: "shell",
         326: "dome", 327: "tower", 328: "sdome", 329: "cloud", 331: "lights", 332: "review",
         333: "cr2", 334: "a6", 335: "m1", 336: "snow", 338: "cable", 339: "power",
         340: "outb", 341: "lamps", 342: "m3", 344: "scope", 345: "clocks", 346: "mast",
         347: "cr3", 349: "a3", 350: "chart", 351: "m2", 352: "m5", 353: "ashlar",
         356: "rec", 357: "smoke", 358: "vault", 359: "clkrm", 360: "astro", 361: "sound",
         # 11-16 13:00: new chats replace the dropped c343, c348, c337, c330 (archived, not counted)
         363: "orrery", 364: "hall", 365: "stair", 366: "comet"}

# whose node is which (11-16 13:00); the public pool is the director's and handed out by the aide
OWN = {"facade": 35, "a2": 36, "a4": 37, "a1": 38, "shell": 39, "dome": 40, "tower": 83, "sdome": 42,
       "cloud": 117, "comet": 44, "lights": 45, "review": 118, "cr2": 8, "a6": 48, "m1": 119, "snow": 50,
       "stair": 51, "cable": 120, "power": 53, "outb": 54, "lamps": 121, "m3": 56, "orrery": 57, "scope": 122,
       "clocks": 59, "mast": 60, "cr3": 61, "hall": 62, "a3": 63, "chart": 64, "m2": 65, "m5": 66, "ashlar": 67,
       "rec": 68, "smoke": 69, "vault": 70, "clkrm": 71, "astro": 72, "sound": 9, "s2": 33}
POOL = list(range(73, 81)) + list(range(84, 93)) + list(range(107, 117))
DEAD = {41, 43, 46, 47, 49, 52, 55, 58}

def newest():
    files = glob.glob("/home/ubuntu/.cursor/projects/agent/agent-tools/*.txt")
    files = [f for f in files if os.path.getsize(f) > 50000]
    return max(files, key=os.path.getmtime) if files else None

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else newest()
    if not path:
        sys.exit("peers: no dump")
    states = {}
    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"- c(\d+)「c164-[^」]*」(?:（你自己）)?：(\S+) ([^，]+)，", line)
        if not m:
            continue
        n = int(m.group(1))
        if n in CODES:
            states.setdefault(m.group(3).strip(), []).append(CODES[n])
    seen = sum(len(v) for v in states.values())
    print("peers: %d of %d seen (%s)" % (seen, len(CODES), os.path.basename(path)[:8]))
    for state, names in sorted(states.items(), key=lambda kv: -len(kv[1])):
        if "没人接手" in state or "等待" in state or len(names) <= 6:
            print("  %s: %s" % (state, "、".join(names)))
        else:
            print("  %s: %d" % (state, len(names)))
    # nodes: state, and for a running one how long the current step has lasted
    nodes, last = {}, None
    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"- node(\d+)「[^」]*」：(\S+) ([^，\n]+)", line)
        if m:
            last = int(m.group(1))
            nodes[last] = [m.group(3).strip(), ""]
            continue
        if last is not None and line.startswith("    实时追踪"):
            m = re.search(r"当前步已持续 ([^）]+)）", line)
            run = re.search(r"进程直跑\((\d+)s/(\d+)s\)", line)
            nodes[last][1] = ("跑单 %ss/%ss" % run.groups()) if run else ("闲 " + m.group(1) if m else "")
            last = None
        elif not line.startswith("    "):
            last = None
    if not nodes:
        return
    bad = []
    for code, n in sorted(OWN.items(), key=lambda kv: kv[1]):
        st = nodes.get(n, ["不在表里", ""])[0]
        if st not in ("在线", "处理中"):
            bad.append("%s node%d %s" % (code, n, st))
    print("  自己的机器不好的: %s" % ("；".join(bad) if bad else "没有"))
    free = [n for n in POOL if nodes.get(n, ["", ""])[0] == "在线"]
    busy = ["node%d(%s)" % (n, nodes[n][1]) for n in POOL if nodes.get(n, ["", ""])[0] == "处理中"]
    off = ["node%d %s" % (n, nodes.get(n, ["不在表里", ""])[0]) for n in POOL
           if nodes.get(n, ["", ""])[0] not in ("在线", "处理中")]
    print("  公共池闲着: %s" % " ".join(str(n) for n in free))
    print("  公共池在跑: %s" % (" ".join(busy) or "没有"))
    print("  公共池不通: %s" % ("；".join(off) or "没有"))


if __name__ == "__main__":
    main()
