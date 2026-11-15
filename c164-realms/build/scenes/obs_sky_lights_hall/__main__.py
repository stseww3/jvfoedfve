import json
import os

from scenes.obs.sky import _lightkit as L

from . import TRIES, build, origin, shots


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "shots.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("[\n" + ",\n".join(" " + json.dumps(shot) for shot in shots()) + "\n]\n")
    print(f"{len(shots())} shots")
    c = build()
    r = c.light_report
    print("doors", r["doors"])
    print("hall", r["hall"])
    print("problems", r["problems"])
    for i, name in enumerate(TRIES):
        o = origin(i)
        lv = L.levels(c, (o[0] - 10, -1, -8), (o[0] + 20, 16, 8))

        def at(x, y, z):
            return lv.get((o[0] + x, y, z), 0)

        print(f"\n{name}: {TRIES[name]}")
        print("  before the pier's east face (x 6), rows y 13..0, z -1..1:")
        for y in range(13, -1, -1):
            print(f"    y {y:>2}  " + " ".join(f"{at(6, y, z):>2}" for z in (-1, 0, 1)))
        print("  the floor's cells (y 0), x 15..-6 left to right, rows z -5..5:")
        for z in range(-5, 6):
            print("    " + " ".join(f"{at(x, 0, z):>2}" for x in range(15, -7, -1)))
        print("  before the north cross wall (z -5), rows y 5..0, x 15..-6:")
        for y in range(5, -1, -1):
            print("    " + " ".join(f"{at(x, y, -5):>2}" for x in range(15, -7, -1)))
        print("  the doorway's cells (x 16), rows y 4..0, z -1..1:", [[at(16, y, z) for z in (-1, 0, 1)] for y in range(4, -1, -1)])


if __name__ == "__main__":
    main()
