#!/usr/bin/env python3
"""Read a list_peers dump and say who of the third shift (c318..c361) has no agent attached.

usage: peers.py <dump file>      (the newest dump under the agent-tools folder when no file is given)
Prints one line per state and the names; never prints identities.
"""
import glob, os, re, sys

CODES = {318: "s2", 319: "s1", 320: "aide", 321: "facade", 322: "a2", 323: "a4", 324: "a1", 325: "shell",
         326: "dome", 327: "tower", 328: "sdome", 329: "cloud", 330: "comet", 331: "lights", 332: "review",
         333: "cr2", 334: "a6", 335: "m1", 336: "snow", 337: "stair(cr4)", 338: "cable", 339: "power",
         340: "outb", 341: "lamps", 342: "m3", 343: "orrery", 344: "scope", 345: "clocks", 346: "mast",
         347: "cr3", 348: "hall", 349: "a3", 350: "chart", 351: "m2", 352: "m5", 353: "ashlar",
         356: "rec", 357: "smoke", 358: "vault", 359: "clkrm", 360: "astro", 361: "sound"}

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
        if "没人接手" in state or len(names) <= 6:
            print("  %s: %s" % (state, "、".join(names)))
        else:
            print("  %s: %d" % (state, len(names)))

main()
