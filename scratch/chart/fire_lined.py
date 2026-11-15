"""Who lines the fire windows of the power house, and that nobody lines them twice."""
from collections import Counter

from artkit.canvas import Canvas
from scenes.obs.materials import windows as W
from scenes.obs.site import powerhouse as PH


def names(canvas):
    out = Counter()
    for _, _, _, nbt in canvas.entities:
        s = str(nbt)
        i = s.find("mat_window_lining_")
        out[s[i:].split('"')[0].split("'")[0].split(",")[0].split("}")[0] if i >= 0 else "?"] += 1
    return dict(out)


fire = W._fire_windows()
print("fire windows:", [(w["front"], w["bay"], w["storey"], w["y"], w["inward"], len(w["cells"])) for w in fire])
print("lined():", len(W.lined()), "of which the power house's", len(fire))

c = Canvas()
n = W.build(c, (0, 0, 0))
print("windows.build:", n, "entities;", len(c.entities), "on the canvas")
before = len(c.entities)
m = PH._lining(c, (0, 0, 0), None)
print("then powerhouse._lining:", m, "entities;", len(c.entities) - before, "more on the canvas")
k = W.build(c, (0, 0, 0))
print("then windows.build again:", k)

c2 = Canvas()
m2 = PH._lining(c2, (0, 0, 0), None)
print("a canvas of its own, powerhouse._lining first:", m2, names(c2))
n2 = W.build(c2, (0, 0, 0))
print("then windows.build:", n2, "entities;", len(c2.entities), "on the canvas")

c3 = Canvas()
with W.unlined():
    print("unlined: build", W.build(c3, (0, 0, 0)), "powerhouse", PH._lining(c3, (0, 0, 0), None), len(c3.entities))

# the same window at another origin is another window
c4 = Canvas()
a = W.build(c4, (0, 0, 0))
b = W.build(c4, (200, 0, 0))
print("two origins on one canvas:", a, b)
fire_only = [e for e in c.entities if "lit_3x3" in str(e[3])]
print("names on the master-like canvas:", names(c))
