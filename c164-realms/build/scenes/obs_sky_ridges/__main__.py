"""python -m scenes.obs_sky_ridges (in build/): writes this scene's shots.json, then prints where the
ridges stand and how high they read from the terrace."""
import json
import math
import os
import sys

from scenes.obs.common import skeleton as S
from scenes.obs.sky import ridges

from . import build, shots


def main():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("[\n" + ",\n".join(" " + json.dumps(shot) for shot in shots()) + "\n]\n")
    print(f"{len(shots())} shots -> {path}\n")

    canvas = build()
    print(f"ridges: {len(canvas.entities)} display entities at {ridges.DISTANCE:.0f} cells")
    print(f"(ceiling {ridges.MAX_ANGLE} degrees from the terrace)")
    for key, bearing, tall, dist in ridges.peaks():
        print(f"  {key}: bearing {bearing:5.1f}, tallest {tall:5.1f} cells, "
              f"elevation {math.degrees(math.atan(tall / dist)):4.2f} degrees")
    covered = sorted(r[1] for r in ridges.peaks())
    print(f"  bearings with hills: {covered}; the west (270) is open: "
          f"{all(abs(b - 270.0) > 20.0 for b in covered)}")
    print(f"the card allows 3 to 6 panels and 8 entities: {len(canvas.entities)}")

    missing = [n for n in ("sky_ridge_a", "sky_ridge_b", "sky_ridge_c") if n not in ridges.models()]
    if missing:
        print(f"PROBLEM: models missing: {missing}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
