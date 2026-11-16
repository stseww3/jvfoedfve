#!/bin/bash
# The floors of the three rooms and the station report of stretches B, F, L (run in c164-realms/).
set -u
C=/tmp/c164_walk/m3-canvas.pickle
O=renders/_wip/walkfix
mkdir -p $O /tmp/c164_walk
python tools/walk.py check plan/reviews/walk/in-route.json | tail -3
python tools/walk.py floors --canvas $C --box=-2,-10,20,10 --levels=0 --out $O/floors-B.txt | tail -2
python tools/walk.py floors --canvas $C --box=0,-27,16,-3 --levels=7 --out $O/floors-F.txt | tail -2
python tools/walk.py floors --canvas $C --box=66,14,91,42 --levels=-6 --out $O/floors-L.txt | tail -2
python tools/walk.py stations plan/reviews/walk/in-route.json --canvas $C --out $O/stations.json > $O/stations-report.txt 2>&1
tail -12 $O/stations-report.txt
python - <<'PY'
import json
t = json.load(open("renders/_wip/walkfix/stations.json"))
rows = []
for s in t["stations"]:
    name = s.get("name") or s.get("id") or ""
    if any(f"-{c}" in name for c in "BFL"):
        rows.append(" ".join(f"{k}={s[k]}" for k in ("name", "at", "feet", "floor", "reach", "leg", "round", "from", "how") if k in s))
open("renders/_wip/walkfix/stations-BFL.txt", "w").write("\n".join(rows) + "\n")
print("\n".join(rows))
PY
