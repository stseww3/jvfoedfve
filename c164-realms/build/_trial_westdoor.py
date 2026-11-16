"""Trial tree only (never delivered): plans of the west door and the paving before it, for a lamp
beside or over the door (the lights line, #75708). A plan for each row, one letter a block, the
names behind the letters, the display entities there and the sources of light.

    cd build && python _trial_westdoor.py
"""
import collections

from scenes import obs

c = obs.build()
TABLE = (("barrier", "B"), ("trapdoor", "t"), ("door", "D"), ("slab", "_"), ("stairs", "/"),
         ("grate", "#"), ("bars", "|"), ("pane", "p"), ("glass", "g"), ("lantern", "l"), ("chain", "!"),
         ("wall", "w"), ("waxed_oxidized", "v"), ("waxed_weathered", "v"), ("oxidized", "i"), ("sandstone", "s"),
         ("polished_deepslate", "P"), ("deepslate", "d"), ("polished_tuff", "T"), ("tuff", "f"), ("copper", "c"),
         ("spruce", "o"), ("dark_oak", "o"), ("quartz", "q"), ("calcite", "q"))
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


X0, X1, Z0, Z1 = -18, 1, -8, 8
print(f"== the west door: x {X0}..{X1} (across), z {Z0}..{Z1} (down the page)")
for y in range(-1, 9):
    print(f" y {y}      " + "".join(str(abs(x) % 10) for x in range(X0, X1 + 1)))
    for z in range(Z0, Z1 + 1):
        print(f"   z {z:4d} " + "".join(kind(c.name(x, y, z)) for x in range(X0, X1 + 1)))
print("== the letters")
for ch in sorted(names):
    print(f"  {ch}  " + ", ".join(f"{n} x{k}" for n, k in names[ch].most_common(8)))
print("== the sources of light there (cell, state)")
found = [(cell, state) for cell, state in c.b.items()
         if X0 - 6 <= cell[0] <= X1 + 4 and -1 <= cell[1] <= 9 and Z0 - 2 <= cell[2] <= Z1 + 2
         and state.rpartition(":")[2].startswith("light[")]
for cell, state in sorted(found):
    print(f"  {cell} {state}")
print("== display entities there (x, y, z, model)")
for x, y, z, nbt in c.entities:
    if X0 - 6 <= x <= X1 + 2 and -1 <= y <= 9 and Z0 - 2 <= z <= Z1 + 3:
        item = nbt.get("item", {})
        model = item.get("components", {}).get("minecraft:item_model", "") if isinstance(item, dict) else ""
        print(f"  {x:7.2f} {y:6.2f} {z:7.2f}  {nbt.get('id', '')} {model}")
