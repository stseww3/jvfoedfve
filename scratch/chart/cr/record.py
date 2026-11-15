"""What build_chartroom() placed, left out and offered to the light line (run from build/)."""
import collections
import importlib

from artkit.canvas import Canvas

T = importlib.import_module("scenes.obs.interiors.chartroom")
c = Canvas()
r = T.build_chartroom(c)
print("entities", r["entities"], "on the canvas", len(c.entities))
print("missing", r["missing"])
for cell, level, why in r["lights"]:
    print("light", cell, level, why)
names = collections.Counter()
for e in c.entities:
    name = None
    if isinstance(e, dict):
        name = e.get("model") or e.get("name") or str(sorted(e))[:60]
    else:
        name = getattr(e, "model", None) or getattr(e, "name", None) or type(e).__name__
    names[str(name)] += 1
for name, n in sorted(names.items()):
    print(f"  {n:3d} {name}")
