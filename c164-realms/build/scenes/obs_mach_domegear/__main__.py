"""Writes shots.json of this test scene from the stage's numbers and says whether the gear fits the
shell and the room it is built into:  python -m scenes.obs_mach_domegear"""
import json
import os

from scenes.obs.machines import dome

from . import build, shots

if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "shots.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n")
    print(f"{len(shots())} shots -> {path}")
    canvas = build()
    print(f"barrier cells: {len(dome.barrier_cells())} {list(dome.barrier_cells())}")
    for title, found in (("stands in a block", dome.clash(canvas)), ("hangs on nothing", dome.unheld(canvas)),
                         ("a barrier that is not inside the gear", dome.barred(canvas))):
        print(f"{title}: {len(found)}")
        for line in sorted(set(str(item) for item in found)):
            print("  " + line)
