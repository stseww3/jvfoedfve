"""python -m scenes.obs_main_facade          writes shots.json of this test scene and of its three twins
python -m scenes.obs_main_facade light    builds the scene and prints the light of the entrance as it
                                          stands in it: who placed the sources (sky/lights, once it is
                                          in the tree; the shell's own stand-in until then), where, how
                                          bright, and, while the stand-in wall is built, whether those
                                          are the stand-in's cells and levels
"""
import json
import os
import sys

from artkit.canvas import Canvas

from scenes.obs.common import blocks as B
from scenes.obs.main import facade

from . import COMPARE, HEADS, build, shots


def _sources(canvas):
    return {cell: state for cell, state in canvas.b.items() if state.startswith(B.LIGHT)}


def light():
    """The entrance's sources in the built scene beside those the shell sets while sky/lights is
    not in the tree (facade._screen_lights). Returns 0 when they are the same."""
    stand_in = Canvas()
    facade._screen_lights(stand_in, facade.ENTRANCE, (0, 0, 0))
    want = _sources(stand_in)
    canvas = build()
    report = getattr(canvas, "light_report", None)
    if report is None:
        got = {cell: state for cell, state in _sources(canvas).items() if cell in want}
        print("sky/lights is not in the tree: the entrance is lit by the shell's own stand-in")
    else:
        from scenes.obs.sky import lights
        print("\n".join(lights.summary(canvas)))
        cells = set(report["doors"]) | set(report["hall"])
        got = {cell: state for cell, state in _sources(canvas).items() if cell in cells}
    for cell, state in sorted(got.items()):
        print(f"  {cell}: {state}")
    if not facade.screened():
        print("the stand-in behind the entrance is not built: the hall is the shell's and its light the light line's own")
        return 0
    same = got == want
    print("the entrance's sources are the stand-in's, cell for cell and level for level" if same else
          f"the entrance's sources are NOT the stand-in's: {sorted(want.items())}")
    return 0 if same else 1


def write():
    here = os.path.dirname(__file__)
    for folder, only in ((here, None), (here + "_a", COMPARE), (here + "_c", COMPARE), (here + "_nocrown", HEADS)):
        path = os.path.join(folder, "shots.json")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots(only)) + "\n]\n")
        print(f"{len(shots(only))} shots -> {path}")


if __name__ == "__main__":
    sys.exit(light() if sys.argv[1:] == ["light"] else write())
