"""A scratch probe of cable (c338), never delivered: the plan of a box of the master scene, row by
row, with the block light of every cell. Run from build/:

    python probe_cable.py x0 x1 z0 z1 y0 y1 [extra sources "x,y,z,level" ...]

Each cell: two letters of the block's name (.. is air) and its block light as a hex digit."""
import sys

from scenes import obs
from scenes.obs.sky import _lightkit as L


def short(name):
    if name is None:
        return ".."
    name = name.split(":")[-1]
    parts = name.split("_")
    if len(parts) == 1:
        return name[:2]
    return parts[0][0] + parts[-1][0]


def main(argv):
    x0, x1, z0, z1, y0, y1 = (int(v) for v in argv[:6])
    canvas = obs.build()
    for extra in argv[6:]:
        x, y, z, level = (int(v) for v in extra.split(","))
        canvas.set(x, y, z, L.light(level))
    pad = 16
    light = L.levels(canvas, (x0 - pad, y0 - pad, z0 - pad), (x1 + pad, y1 + pad, z1 + pad))
    names = {}
    for y in range(y1, y0 - 1, -1):
        print(f"y {y}    x {x0}..{x1} across, z down")
        for z in range(z0, z1 + 1):
            row = []
            for x in range(x0, x1 + 1):
                name = canvas.name(x, y, z)
                code = short(name)
                names.setdefault(code, set()).add(name)
                row.append(f"{code}{light.get((x, y, z), 0):x}")
            print(f"{z:4d}  " + " ".join(row))
    print("codes: " + "; ".join(f"{k}={'/'.join(sorted(str(n) for n in v))}" for k, v in sorted(names.items())))
    try:
        from scenes.obs.sky import lights
        placed = dict(lights.report(canvas)["placed"])
        near = {c: v for c, v in placed.items() if x0 - 4 <= c[0] <= x1 + 4 and y0 - 4 <= c[1] <= y1 + 4 and z0 - 4 <= c[2] <= z1 + 4}
        print("sources of sky/lights near: " + "; ".join(f"{c}: {v}" for c, v in sorted(near.items())))
    except Exception as e:  # noqa: BLE001
        print(f"sources not read ({e})")


if __name__ == "__main__":
    main(sys.argv[1:])
