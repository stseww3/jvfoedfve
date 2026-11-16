"""The fire's light in numbers (cr2, 11-16): where the block light of the boilers' fire doors falls
in the master scene.

    cd build && python -m scenes.obs_mach_switchboard_boiler.probe [out.txt]

Builds the master scene and prints, for the power house: the sources the light line placed there
(cell, level, who asked) and the offers it turned down, cut or moved; then the block light in the
row of the feet and the two rows over it, spread as the game spreads it (sky/_lightkit.levels): a
hex digit for each cell of the room, '#' for a cell that stops light, '.' for none. The firing
floor is the two columns west of boiler.FRONT_X.
"""
import os
import sys

from artkit import blockfacts as F
from artkit import blocks as AB
from scenes import obs
from scenes.obs.machines import boiler
from scenes.obs.site import powerhouse as shell
from scenes.obs.sky import _lightkit as L
from scenes.obs.sky import lights

AROUND = 4      # cells round the room that are counted with it: the sources before the glass stand there
ROWS = 3        # rows printed, from the row of the feet up


def lines():
    c = obs.build()
    x0, z0, x1, z1 = shell.ROOM
    y = int(boiler.FLOOR)
    lo, hi = (x0 - AROUND, y - 1, z0 - AROUND), (x1 + AROUND, y + 12, z1 + AROUND)

    def near(cell):
        return all(lo[i] <= cell[i] <= hi[i] for i in range(3))

    r = lights.report(c)
    out = ["sources in and round the power house (cell, level, who asked):"]
    out += [f"  {cell} {level} {why}" for cell, (level, why) in sorted(r["placed"].items()) if near(cell)]
    for key in ("rejected", "capped", "moved", "merged"):
        out += [f"  {key}: {e}" for e in r[key] if near(e[0])]
    own = set(r["placed"])
    out += [f"  not the light line's: {cell} {state}" for cell, state in sorted(c.b.items())
            if near(cell) and cell not in own and F.emission(*AB.parse(state)) > 0]
    level = L.levels(c, lo, hi)
    for row in range(y, y + ROWS):
        out.append(f"block light in row {row}: x {x0}..{x1} across, z {z0}..{z1} down")
        out.append("      " + "".join(str(x % 10) for x in range(x0, x1 + 1)))
        for z in range(z0, z1 + 1):
            cells = ""
            for x in range(x0, x1 + 1):
                state = c.b.get((x, row, z))
                if state is not None and L._stops_light(state):
                    cells += "#"
                else:
                    cells += "0123456789abcdef"[level[(x, row, z)]] if level.get((x, row, z)) else "."
            out.append(f"  {z:3d} {cells}")
    fx = int(boiler.FRONT_X)
    out.append("under the firing floor and at the wall's foot: "
               + ", ".join(f"{cell} {AB.name_of(c.b[cell]) if cell in c.b else 'air'}"
                           for cell in ((fx - 1, y - 1, z0 + 2), (fx - 2, y - 1, z0 + 6), (fx - 1, y, z0 - 1),
                                        (fx - 1, y + 1, z0 - 1), (x0 - 1, y, z0 + 6))))
    return out


def main(argv):
    text = "\n".join(lines())
    print(text)
    if argv:
        os.makedirs(os.path.dirname(os.path.abspath(argv[0])), exist_ok=True)
        with open(argv[0], "w") as f:
            f.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
