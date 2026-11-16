"""Scratch (never delivered): the blocks and the block light about the dark heaps of the ways, as
text, for placing lamps. Run in build/ on a node:

    python ways_probe.py [--dark <dark.json of tools/darkfloor.py>] [--out ../renders/_wip/ways/probe.txt]

A cell is two characters: what stands there and its block light (hex). A dark cell of the list is
marked with ! in the place of the first character.
"""
import argparse
import json
import os

from artkit import blocks as AB
from scenes import obs
from scenes.obs.common import blocks as B
from scenes.obs.sky import _lightkit as L
from scenes.obs.sky import lights

REGIONS = [
    ("clock tower's foot", (7, 16, -36), (19, 25, -24)),
]


def char_of(name):
    if name is None:
        return "."
    short = name.split(":")[-1]
    if short == "air":
        return "."
    if name == B.LIGHT or short == "light":
        return "L"
    if short.endswith("_stairs"):
        return "<"
    if short.endswith("_slab"):
        return "_"
    if "glass" in short:
        return "g"
    if short.endswith(("_fence", "_bars", "_wall", "_pane", "chain", "_rod")) or short in ("iron_bars", "chain"):
        return "f"
    if short.endswith("_trapdoor"):
        return "t"
    if short.endswith("_door"):
        return "d"
    if short == "barrier":
        return "b"
    if short.endswith(("carpet", "_button", "_pressure_plate", "torch", "lantern", "ladder", "_sign", "candle")):
        return "o"
    return "#"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dark", default="")
    ap.add_argument("--out", default="../renders/_wip/ways/probe.txt")
    args = ap.parse_args()
    canvas = obs.build()
    cells = canvas.b
    lo = [min(k[i] for k in cells) for i in range(3)]
    hi = [max(k[i] for k in cells) for i in range(3)]
    light = L.levels(canvas, tuple(lo), tuple(hi))
    dark = {}
    if args.dark and os.path.exists(args.dark):
        with open(args.dark, encoding="utf-8") as fh:
            data = json.load(fh)
        for s in data.get("sections", ()):
            for hp in s["heaps"]:
                for c in hp["list"]:
                    dark[tuple(c[:3])] = (s["name"], c[3], c[4] if len(c) > 4 else "floor")
    placed = dict(lights.report(canvas)["placed"])
    names = {}

    def name_of(state):
        if state not in names:
            names[state] = AB.name_of(state)
        return names[state]

    lines = [f"blocks {len(cells)}, lit cells {len(light)}, dark cells of the list {len(dark)}, sources placed {len(placed)}"]
    for title, (x0, y0, z0), (x1, y1, z1) in REGIONS:
        lines.append("")
        lines.append(f"==== {title}: x {x0}..{x1}, y {y0}..{y1}, z {z0}..{z1} (rows z, north on top; columns x, west on the left)")
        near = sorted((cell, what) for cell, what in placed.items()
                      if x0 - 2 <= cell[0] <= x1 + 2 and y0 - 2 <= cell[1] <= y1 + 2 and z0 - 2 <= cell[2] <= z1 + 2)
        for cell, what in near:
            lines.append(f"   source {cell}: {what}")
        kinds = {}
        for y in range(y0, y1 + 1):
            lines.append(f"-- y {y}")
            lines.append("      " + "".join(f"{x:>3d}"[-2:] + " " for x in range(x0, x1 + 1)))
            for z in range(z0, z1 + 1):
                row = []
                for x in range(x0, x1 + 1):
                    state = cells.get((x, y, z))
                    name = name_of(state) if state is not None else None
                    ch = char_of(name)
                    if ch in "#o" and name:
                        kinds[name.split(":")[-1]] = kinds.get(name.split(":")[-1], 0) + 1
                    if (x, y, z) in dark:
                        ch = "!"
                    level = light.get((x, y, z), 0)
                    row.append(ch + ("%x" % level if ch in ".!L<_ftdgo" else " ") + " ")
                lines.append(f"{z:>4d}  " + "".join(row))
        lines.append("   blocks: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1])[:14]))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print(lines[0])
    print("written", args.out, len(lines), "lines")


if __name__ == "__main__":
    main()
