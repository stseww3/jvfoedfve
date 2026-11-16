#!/usr/bin/env python3
"""Turn dealer for the nodes that still take jobs (node12, and pool nodes lent to us).

State: /tmp/c164_aide/deal.json.  One holder per lane; a queue of jobs.

  deal.py add <code> <class> <minutes> <what...>   queue one job (class 0 = the director's fixed first round,
                                                   1 s2's gate, 2 one or two jobs from delivery, 3 s1's real
                                                   machine, 4 draft pictures, 5 the walk's big batches)
  deal.py show                                     holders (with minutes held) and the queue in order
  deal.py give <lane> [<code>|#<id>]               hand the lane to the first job (or to that person's first job)
  deal.py done <lane> [note...]                    the holder's receipt is in; the lane is free
  deal.py skip <lane> [back]                       the holder did not answer; 'back' puts the job at the end
  deal.py drop #<id>                               take a job out of the queue
  deal.py asked <lane>                             note that the holder was asked once
"""
import json
import os
import re
import sys
import time

STATE = "/tmp/c164_aide/deal.json"
ROSTER = "/agent/repos/c164-aide-f3-b9ab/c164-realms/plan/ROSTER.md"
LANES = ("node12", "node4", "node5", "node6")


def chats():
    out = {}
    for line in open(ROSTER, encoding="utf-8"):
        m = re.match(r"\| ([a-z0-9]+) \| (c3\d\d) \|", line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def load():
    if os.path.exists(STATE):
        return json.load(open(STATE, encoding="utf-8"))
    return {"seq": 0, "queue": [], "holders": {}, "log": []}


def save(st):
    tmp = STATE + ".tmp"
    json.dump(st, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, STATE)


def hhmm(t):
    return time.strftime("%H:%M", time.gmtime(t + 8 * 3600))


def key(e):
    return (e["cls"], e["id"]) if e["cls"] == 0 else (e["cls"], e["min"], e["id"])


def ordered(st):
    return sorted(st["queue"], key=key)


def show(st):
    now = time.time()
    for lane in LANES:
        h = st["holders"].get(lane)
        if h:
            held = (now - h["since"]) / 60
            flag = "  LATE (ask)" if held >= 15 and not h.get("asked") else ("  LATE (asked %s; skip?)" % hhmm(h["asked"]) if held >= 15 else "")
            print("%-7s held by %-7s %s since %s (%.0f min of %s)  #%d %s%s" % (lane, h["code"], h["chat"], hhmm(h["since"]), held, h["min"], h["id"], h["what"], flag))
        elif lane == "node12" or lane in st.get("lent", []):
            print("%-7s FREE" % lane)
    q = ordered(st)
    print("queue: %d jobs, about %d minutes" % (len(q), sum(e["min"] for e in q)))
    for n, e in enumerate(q, 1):
        print("  %2d. #%-3d %-7s %s  class %d  %2d min  %s" % (n, e["id"], e["code"], e["chat"], e["cls"], e["min"], e["what"]))


def main():
    a = sys.argv[1:]
    st = load()
    if not a or a[0] == "show":
        show(st)
        return
    cmd = a[0]
    if cmd == "add":
        code, cls, minutes = a[1], int(a[2]), int(a[3])
        what = " ".join(a[4:])
        c = chats()
        if code not in c:
            sys.exit("deal: nobody called %s in the roster" % code)
        st["seq"] += 1
        st["queue"].append({"id": st["seq"], "code": code, "chat": c[code], "cls": cls, "min": minutes, "what": what, "added": time.time()})
        save(st)
        pos = [e["id"] for e in ordered(st)].index(st["seq"]) + 1
        print("queued #%d %s (%s) at place %d of %d" % (st["seq"], code, c[code], pos, len(st["queue"])))
    elif cmd == "give":
        lane = a[1]
        if lane not in LANES:
            sys.exit("deal: no lane %s" % lane)
        if st["holders"].get(lane):
            sys.exit("deal: %s is held by %s" % (lane, st["holders"][lane]["code"]))
        q = ordered(st)
        busy = {h["code"] for h in st["holders"].values() if h}
        pick = None
        if len(a) > 2:
            for e in q:
                if a[2] == "#%d" % e["id"] or a[2] == e["code"]:
                    pick = e
                    break
        else:
            for e in q:
                if e["code"] not in busy and e.get("lane", lane) == lane and not e.get("hold"):
                    pick = e
                    break
        if not pick:
            sys.exit("deal: nothing to give")
        st["queue"] = [e for e in st["queue"] if e["id"] != pick["id"]]
        st["holders"][lane] = dict(pick, since=time.time(), asked=None)
        if lane != "node12":
            st.setdefault("lent", [])
            if lane not in st["lent"]:
                st["lent"].append(lane)
        save(st)
        print("GIVE %s to %s (%s): #%d %s, %d min" % (lane, pick["code"], pick["chat"], pick["id"], pick["what"], pick["min"]))
    elif cmd in ("done", "skip"):
        lane = a[1]
        h = st["holders"].get(lane)
        if not h:
            sys.exit("deal: %s is free already" % lane)
        now = time.time()
        st["log"].append({"lane": lane, "code": h["code"], "id": h["id"], "what": h["what"], "from": h["since"], "to": now, "how": cmd, "note": " ".join(a[2:])})
        st["holders"][lane] = None
        if cmd == "skip" and len(a) > 2 and a[2] == "back":
            st["seq"] += 1
            st["queue"].append({"id": st["seq"], "code": h["code"], "chat": h["chat"], "cls": max(h["cls"], 4), "min": h["min"], "what": h["what"] + "（跳过一次）", "added": now})
        save(st)
        print("%s: %s %s after %.0f min" % (lane, h["code"], cmd, (now - h["since"]) / 60))
    elif cmd == "drop":
        before = len(st["queue"])
        st["queue"] = [e for e in st["queue"] if "#%d" % e["id"] != a[1]]
        save(st)
        print("dropped %d" % (before - len(st["queue"])))
    elif cmd == "asked":
        st["holders"][a[1]]["asked"] = time.time()
        save(st)
    elif cmd == "hold":
        lane, code, minutes = a[1], a[2], int(a[3])
        what = " ".join(a[4:])
        c = chats()
        st["seq"] += 1
        st["holders"][lane] = {"id": st["seq"], "code": code, "chat": c[code], "cls": 0, "min": minutes, "what": what, "added": time.time(), "since": time.time(), "asked": None}
        save(st)
        print("%s held by %s" % (lane, code))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
