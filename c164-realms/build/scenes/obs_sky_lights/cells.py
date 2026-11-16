"""python -m scenes.obs_sky_lights.cells x0 y0 z0 x1 y1 z1 [...] (in build/): what stands in a box
of the master scene and how much block light each of its cells gets, row by row from the top. For
settling where a lamp can hang when another package has taken its cell: one sees the wall, the free
cell before it and what the source leaves on the floor. Several boxes may follow one another.

A cell is printed as the light it gets (0..15) when it is open, as `#` when a whole block stands in
it, as a letter when something else does: `x` a barrier, `L` a light source (its level follows in
the list under the rows), `o` anything that lets light by. The whole master scene is built: run it
on a node. The notes of sky/lights (what it left out and why) are printed first.
"""
import sys

from artkit import blocks as AB

from scenes import obs
from scenes.obs.common import blocks as B
from scenes.obs.sky import _lightkit as L
from scenes.obs.sky import lights

REACH = 15                  # the light is spread in the box and this far around it


def mark(state, level):
    if state is None:
        return f"{level:x}"
    name = AB.name_of(state)
    if name == B.LIGHT:
        return "L"
    if name == B.BARRIER:
        return "x"
    return "#" if L._stops_light(state) else "o"


def box(canvas, lo, hi):
    light = L.levels(canvas, tuple(v - REACH for v in lo), tuple(v + REACH for v in hi))
    out, sources, kinds = [], [], {}
    for y in range(hi[1], lo[1] - 1, -1):
        out.append(f"  y {y}   x {lo[0]}..{hi[0]} across, z {lo[2]}..{hi[2]} down")
        for z in range(lo[2], hi[2] + 1):
            row = ""
            for x in range(lo[0], hi[0] + 1):
                state = canvas.b.get((x, y, z))
                row += mark(state, light.get((x, y, z), 0))
                if state is not None:
                    name = AB.name_of(state)
                    if name == B.LIGHT:
                        sources.append(((x, y, z), light.get((x, y, z), 0)))
                    else:
                        kinds[name] = kinds.get(name, 0) + 1
            out.append(f"    z {z:>4}  {row}")
    out.append("  sources: " + (", ".join(f"{cell} {level}" for cell, level in sources) or "none"))
    out.append("  stands there: " + ", ".join(f"{n} {name}" for name, n in sorted(kinds.items())))
    return out


def main(argv):
    if not argv or len(argv) % 6:
        print(__doc__)
        return 2
    canvas = obs.build()
    for line in lights.summary(canvas):
        if line.startswith(("note", "PROBLEM")):
            print(line)
    for i in range(0, len(argv), 6):
        a, b = [int(v) for v in argv[i:i + 3]], [int(v) for v in argv[i + 3:i + 6]]
        lo, hi = [min(p, q) for p, q in zip(a, b)], [max(p, q) for p, q in zip(a, b)]
        print(f"box {tuple(lo)}..{tuple(hi)}")
        print("\n".join(box(canvas, lo, hi)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
