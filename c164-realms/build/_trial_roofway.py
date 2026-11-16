"""Trial tree only (never delivered): plans of the roof's ways, for the lamps along the
walk-through's stretches J and K. A plan for each row of each window, one letter a block, and the
names behind the letters.

    cd build && python _trial_roofway.py
"""
import collections

from scenes import obs

c = obs.build()
TABLE = (("light", "L"), ("barrier", "B"), ("trapdoor", "t"), ("door", "D"), ("slab", "_"), ("stairs", "/"),
         ("grate", "#"), ("bars", "|"), ("glass", "g"), ("lantern", "l"), ("bulb", "b"), ("chain", "!"),
         ("waxed_oxidized", "v"), ("waxed_weathered", "v"), ("oxidized", "i"), ("sandstone", "s"),
         ("deepslate", "d"), ("tuff", "f"), ("copper", "c"), ("spruce", "w"), ("dark_oak", "w"))
names = collections.defaultdict(collections.Counter)


def kind(name):
    if name is None:
        return "."
    n = name.rpartition(":")[2].split("[")[0]
    for key, ch in TABLE:
        if key in n:
            names[ch][n] += 1
            return ch
    names["?"][n] += 1
    return "?"


WINDOWS = (("south: the dome room's door, the corner terrace, the inner gable, the steps up", (4, 17), (4, 19)),
           ("south: the way down, the end terrace, the small dome", (-1, 17), (22, 35)),
           ("north: the dome room's door, the corner terrace, the inner gable, the steps up", (4, 17), (-18, -3)),
           ("north: the way down, the end terrace, the clock tower's foot", (-1, 17), (-34, -21)))
for title, (x0, x1), (z0, z1) in WINDOWS:
    print(f"== {title}: x {x0}..{x1}, z {z0}..{z1}")
    for y in range(17, 23):
        print(f" y {y}      " + "".join(str(x % 10) for x in range(x0, x1 + 1)))
        for z in range(z0, z1 + 1):
            print(f"   z {z:4d} " + "".join(kind(c.name(x, y, z)) for x in range(x0, x1 + 1)))
print("== the letters")
for ch in sorted(names):
    print(f"  {ch}  " + ", ".join(f"{n} x{k}" for n, k in names[ch].most_common(8)))
print("== display entities in the windows (x, y, z, model)")
for x, y, z, nbt in c.entities:
    if 17 <= y <= 23 and any(x0 <= x <= x1 + 1 and z0 <= z <= z1 + 1 for _t, (x0, x1), (z0, z1) in WINDOWS):
        item = nbt.get("item", {})
        model = item.get("components", {}).get("minecraft:item_model", "") if isinstance(item, dict) else ""
        print(f"  {x:7.2f} {y:6.2f} {z:7.2f}  {nbt.get('id', '')} {model}")
