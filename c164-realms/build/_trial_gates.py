"""TRIAL ONLY: what stands in the entrance's planes once props/ironwork has dressed the building."""
import collections
import scenes.obs_main_facade as scene
from scenes.obs.main import facade

c = scene.build()
b = c.b if hasattr(c, "b") else c.blocks
def name(s):
    return "air" if s is None else s.split("[")[0].split(":")[-1]
for d in facade.doors(facade.ENTRANCE):
    (y0, y1) = d["y"]
    ix, iz = d["inward"]
    print(d["front"], "bay", d["bay"], d["kind"], "wall line cells", d["cells"], "y", d["y"])
    for step, label in ((0, "wall line"), (1, "one step in (the iron's plane)"), (2, "two steps in")):
        got = collections.Counter(name(b.get((x + ix * step, y, z + iz * step))) for x, z in d["cells"] for y in range(y0, y1 + 1))
        print("   ", label, dict(got))
ents = collections.Counter()
near = []
for e in c.entities:
    x, y, z, nbt = e
    model = str(nbt.get("item", {}).get("components", {}).get("minecraft:item_model", nbt.get("id")))
    ents[model.split(":")[-1].split("/")[-1]] += 1
    if 14 <= x <= 24 and -8 <= z <= 9 and y <= 9:
        near.append((round(x, 2), round(y, 2), round(z, 2), model.split(":")[-1].split("/")[-1]))
print("entities:", len(c.entities), dict(ents))
for n in sorted(near):
    print("   near the entrance:", n)
