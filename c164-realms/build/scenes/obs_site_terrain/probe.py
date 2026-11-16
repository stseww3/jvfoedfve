"""The mountain's numbers round a spot, for whoever builds against it (run from build/):

    python -m scenes.obs_site_terrain.probe x0 z0 x1 z1 [x0 z0 x1 z1 ...] [--piers]

For every box a table of terrain.top(x, z): x across, z down, '..' where there is no rock, '^^' on
the upper terrace. --piers lists the cells of the terrace's outline that carry a railing pier west
of the west front (the sunset terrace's arc).
"""
import sys

from scenes.obs.site import _kit as K
from scenes.obs.site import terrain


def table(x0, z0, x1, z1):
    upper = terrain.upper_cells()
    rows = ["      " + "".join(f"{x:4d}" for x in range(x0, x1 + 1))]
    for z in range(z0, z1 + 1):
        cells = []
        for x in range(x0, x1 + 1):
            y = terrain.top(x, z)
            cells.append("  ^^" if (x, z) in upper else "  .." if y is None else f"{y:4d}")
        rows.append(f"z{z:4d} " + "".join(cells))
    return "\n".join(rows)


def main(argv):
    piers = "--piers" in argv
    nums = [int(a) for a in argv if a != "--piers"]
    if len(nums) % 4:
        print(__doc__)
        return 2
    for i in range(0, len(nums), 4):
        x0, z0, x1, z1 = nums[i:i + 4]
        print(f"top(x, z), x {x0}..{x1}, z {z0}..{z1}")
        print(table(x0, z0, x1, z1))
        print()
    if piers:
        ring = K.outline(terrain.upper_cells())
        arc = sorted(p for p in terrain.rail_piers(ring) if p[0] < terrain.TX0)
        print(f"piers on the arc ({len(arc)}): {arc}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
