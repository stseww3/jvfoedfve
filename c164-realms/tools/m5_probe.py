"""A look at the master scene by numbers, for placing lamps: for every box named on the command
line, the blocks row by row (a code to a kind of block, the block light in a free cell), the
light sources in it and around it, the display entities in it.

    env PYTHONPATH=build python m5_probe.py --out <dir> name:x0,x1,y0,y1,z0,z1 [...]

Reads only. The whole master scene is built: for a node.
"""
import math
import os
import sys

from artkit import blocks as AB

from scenes import obs
from scenes.obs.common import blocks as B
from scenes.obs.sky import _lightkit as L
from scenes.obs.sky import lights

REACH = 15


def code_of(name, codes):
    if name not in codes:
        short = name.rpartition(":")[2]
        parts = short.split("_")
        tries = [(parts[0][0] + parts[-1][0]) if len(parts) > 1 else short[:2]]
        tries += [parts[0][0] + ch for ch in "abcdefghijklmnopqrstuvwxyz0123456789"]
        tries += [a + b for a in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" for b in "abcdefghijklmnopqrstuvwxyz"]
        used = set(codes.values())
        codes[name] = next(t for t in tries if t not in used)
    return codes[name]


def main(argv):
    out_dir = None
    if "--out" in argv:
        i = argv.index("--out")
        out_dir = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    boxes = []
    for arg in argv:
        name, _, nums = arg.partition(":")
        x0, x1, y0, y1, z0, z1 = (int(v) for v in nums.split(","))
        boxes.append((name, (x0, y0, z0), (x1, y1, z1)))
    canvas = obs.build()
    lo = tuple(min(b[1][i] for b in boxes) - REACH for i in range(3))
    hi = tuple(max(b[2][i] for b in boxes) + REACH for i in range(3))
    light = L.levels(canvas, lo, hi)
    placed = lights.report(canvas)["placed"]
    print(f"ways: {len(lights.report(canvas)['ways'])} lamps; way_lamps() has {len(lights.way_lamps())} rows")
    for row in lights.way_lamps():
        if "door" in row[3]:
            print("  row:", row)
    for note in lights.report(canvas)["notes"] + [f"PROBLEM: {p}" for p in lights.report(canvas)["problems"]]:
        print("  note:", str(note)[:200])
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    for name, (x0, y0, z0), (x1, y1, z1) in boxes:
        codes, states, text = {}, {}, []
        text.append(f"{name}: x {x0}..{x1}, y {y0}..{y1}, z {z0}..{z1}; a free cell shows its block light, "
                    f"'*n' is a light source of level n (hex)")
        for y in range(y1, y0 - 1, -1):
            text.append("")
            text.append(f"y {y}")
            text.append("  z\\x " + "".join(f"{x:>4}" for x in range(x0, x1 + 1)))
            for z in range(z0, z1 + 1):
                row = []
                for x in range(x0, x1 + 1):
                    state = canvas.b.get((x, y, z))
                    if state is None:
                        v = light.get((x, y, z), 0)
                        row.append(f"{v:>4}" if v else "   .")
                    elif AB.name_of(state) == B.LIGHT:
                        row.append(f"  *{light.get((x, y, z), 0):x}")
                    else:
                        n = AB.name_of(state)
                        states.setdefault(n, set()).add(state.partition("[")[2].rstrip("]"))
                        row.append("  " + code_of(n, codes))
                text.append(f"{z:>5} " + "".join(row))
        text.append("")
        text.append("blocks:")
        for n, c in sorted(codes.items(), key=lambda kv: kv[1]):
            props = sorted(p for p in states[n] if p)
            text.append(f"  {c}  {n}" + (f"   [{' | '.join(props[:6])}{' ...' if len(props) > 6 else ''}]" if props else ""))
        text.append("")
        text.append(f"light sources within {REACH // 2} cells of the box (cell, level, who):")
        near = REACH // 2
        for cell, state in sorted(canvas.b.items()):
            if not (x0 - near <= cell[0] <= x1 + near and y0 - near <= cell[1] <= y1 + near
                    and z0 - near <= cell[2] <= z1 + near):
                continue
            if AB.name_of(state) != B.LIGHT:
                continue
            who = placed.get(cell)
            text.append(f"  {cell}  {light.get(cell, 0):>2}  {who[1] if who else 'not of sky/lights'}")
        text.append("")
        text.append("display entities in the box and a cell round it (x, y, z, model):")
        for x, y, z, nbt in sorted(canvas.entities, key=lambda e: (e[1], e[0], e[2])):
            if x0 - 1 <= x <= x1 + 2 and y0 - 1 <= y <= y1 + 2 and z0 - 1 <= z <= z1 + 2:
                item = nbt.get("item", {}) if isinstance(nbt, dict) else {}
                model = item.get("components", {}).get("minecraft:item_model") or nbt.get("id", "?")
                text.append(f"  {x:>8.3f} {y:>7.3f} {z:>8.3f}  {model}")
        body = "\n".join(text) + "\n"
        if out_dir:
            with open(os.path.join(out_dir, f"{name}.txt"), "w") as f:
                f.write(body)
        print(f"{name}: {len(text)} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
