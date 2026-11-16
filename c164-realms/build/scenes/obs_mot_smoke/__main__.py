"""Writes shots.json of this test scene from the stage's numbers, and says where the chimney's
smoke falls in the locked pictures:  python -m scenes.obs_mot_smoke"""
import json
import os

from scenes.obs.common import skeleton as S

from . import V12, plume, shots, where

if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "shots.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n")
    print(f"{len(shots())} shots -> {path}")
    print("the smoke's middle line in the pictures (x, y from -1 to 1; outside when beyond):")
    for name, view in (("V1", S.V1), ("V6", S.V6), ("V12", V12)):
        marks = []
        for share in (0.0, 0.25, 0.5, 0.75, 1.0):
            at = where(view, plume(share))
            marks.append("behind" if at is None else f"({at[0]:+.2f}, {at[1]:+.2f})")
        print(f"  {name:4s} mouth {marks[0]}  quarter {marks[1]}  half {marks[2]}  "
              f"three quarters {marks[3]}  head {marks[4]}")
