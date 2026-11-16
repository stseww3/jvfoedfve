"""Trial tree only (never delivered): the places over the roofs that sound's list of dark cells
(renders/_wip/light/dark.md of his branch) gives to dome and the lights line. For each window and
each row a plan, one letter a block, and beside it the block light of the same cells (a hex digit;
'#' a whole block), then the sources of light and the lamps there.

    cd build && python _trial_roofdark.py
"""
import collections

from artkit import blockfacts as F
from artkit import blocks as AB
from scenes import obs
from scenes.obs.sky import _lightkit as L
from scenes.obs.sky import lights

c = obs.build()
r = lights.report(c)
TABLE = (("barrier", "B"), ("trapdoor", "t"), ("door", "D"), ("slab", "_"), ("stairs", "/"),
         ("grate", "="), ("bars", "|"), ("pane", "p"), ("glass", "g"), ("lantern", "l"), ("bulb", "b"), ("chain", "!"),
         ("wall", "m"), ("waxed_oxidized", "v"), ("waxed_weathered", "v"), ("oxidized", "i"), ("sandstone", "s"),
         ("deepslate", "d"), ("tuff", "f"), ("copper", "c"), ("spruce", "w"), ("dark_oak", "w"), ("snow", "*"))
names = collections.defaultdict(collections.Counter)


def kind(name):
    if name is None:
        return "."
    n = name.rpartition(":")[2].split("[")[0]
    if n == "light":
        return "L"
    for key, ch in TABLE:
        if key in n:
            names[ch][n] += 1
            return ch
    names["?"][n] += 1
    return "?"


WINDOWS = (("south: the dome room's door, the corner terrace, the inner gable, the steps up", (-2, 17), (4, 19)),
           ("north: the dome room's door, the corner terrace, the inner gable, the steps up", (-2, 17), (-19, -4)))
ROWS = range(16, 23)
for title, (x0, x1), (z0, z1) in WINDOWS:
    lv = L.levels(c, (x0 - 16, ROWS[0] - 8, z0 - 16), (x1 + 16, ROWS[-1] + 8, z1 + 16))
    print(f"== {title}: x {x0}..{x1}, z {z0}..{z1}; left the blocks, right the block light")
    for y in ROWS:
        head = "".join(str(x % 10) for x in range(x0, x1 + 1))
        print(f" y {y}      {head}   {head}")
        for z in range(z0, z1 + 1):
            plan = "".join(kind(c.name(x, y, z)) for x in range(x0, x1 + 1))
            light = ""
            for x in range(x0, x1 + 1):
                got = lv.get((x, y, z))
                light += f"{got:x}" if got is not None else "#" if c.has(x, y, z) else "0"
            print(f"   z {z:4d} {plan}   {light}")
    print("-- the sources of light there (cell, level, whose)")
    for cell, state in sorted(c.b.items()):
        if not (x0 - 3 <= cell[0] <= x1 + 3 and ROWS[0] - 1 <= cell[1] <= ROWS[-1] + 3 and z0 - 3 <= cell[2] <= z1 + 3):
            continue
        e = F.emission(*AB.parse(state))
        if e > 0:
            whose = r["placed"].get(cell, (None, state.rpartition(":")[2]))[1]
            print(f"   {cell}  {e:2d}  {whose}")
    print("-- the lamps there (x, y, z, model)")
    for x, y, z, nbt in c.entities:
        if x0 - 3 <= x <= x1 + 4 and ROWS[0] - 1 <= y <= ROWS[-1] + 3 and z0 - 3 <= z <= z1 + 4:
            item = nbt.get("item", {})
            model = item.get("components", {}).get("minecraft:item_model", "") if isinstance(item, dict) else ""
            if "lamp" in model or "lantern" in model or "light" in model:
                print(f"   {x:7.2f} {y:6.2f} {z:7.2f}  {model}")
print("== the letters")
for ch in sorted(names):
    print(f"  {ch}  " + ", ".join(f"{n} x{k}" for n, k in names[ch].most_common(8)))
