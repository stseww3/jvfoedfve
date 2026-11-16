"""Trial tree only (never delivered): the walls under the upper terrace, for a wash from below at
the feet of their buttresses (the lights line, #75708; cr2 on the real pictures, #74079).

    cd build && python _trial_basewall.py survey
        plans of the east wall's foot on the lower platform and of the rock at the south wall's
        foot, with what stands there
    cd build && python _trial_basewall.py light
        the block light before the faces of the buttresses and of the wall between them
    cd build && python _trial_basewall.py luma <v1|v11> <picture> [<picture> ...]
        how light those faces are in a picture taken from that view (Rec. 709 luma of the sRGB
        values, 0 to 1, as tools/walk.py takes it), face by face; no scene is built
"""
import collections
import math
import sys

from scenes.obs.common import skeleton as S

FOV = 77.0                      # degrees, the height of the picture (tools/boardshots.py)
VIEWS = {"v1": S.V1, "v11": S.V11}
EAST_X = S.EAST_EDGE_X          # 60: the east wall's column
EAST_Z = (-38, -30, -22, -14, 14, 22, 30, 38)       # site/stair.BUTTRESS_Z
SOUTH_Z = S.UPPER_TERRACE[3]    # 38: the south wall's row
SOUTH_X = (-10, -6, -2, 2, 6, 10, 14, 19, 23, 27, 31, 35, 39, 43, 47, 51, 56)   # site/terrain.rail_piers
LOW = -14                       # the lowest foot looked for under the south wall

TABLE = (("snow", "*"), ("deepslate_brick", "B"), ("polished_deepslate", "P"), ("cobbled_deepslate", "c"),
         ("deepslate", "d"), ("polished_tuff", "T"), ("tuff", "t"), ("andesite", "a"), ("sandstone", "S"),
         ("stone", "s"), ("bars", "|"), ("grate", "#"), ("slab", "_"), ("stairs", "/"))
names = collections.defaultdict(collections.Counter)


def plain(name):
    return None if name is None else name.rpartition(":")[2].split("[")[0]


def kind(name):
    n = plain(name)
    if n is None:
        return "."
    if n == "light":
        return "L"
    for key, ch in TABLE:
        if key in n:
            names[ch][n] += 1
            return ch
    names["?"][n] += 1
    return "?"


def top(c, x, z, high=-1, low=-34):
    """The highest row from `high` down that holds a block (a light source is none), or None."""
    for y in range(high, low - 1, -1):
        n = plain(c.name(x, y, z))
        if n is not None and n != "light":
            return y
    return None


def depth(y):
    """A row as one letter: how far it lies under the terrace's paving (0 the paving, a = 10)."""
    if y is None:
        return " "
    d = -1 - y
    return str(d) if d < 10 else chr(ord("a") + d - 10) if d < 36 else "+"


def survey():
    from scenes import obs
    c = obs.build()
    x0, x1, z0, z1 = EAST_X - 1, EAST_X + 10, -44, 44
    print(f"== the east wall and the lower platform before it: x {x0}..{x1} (down the page), z {z0}..{z1}")
    for y in range(-7, 1):
        print(f" y {y}")
        print("          " + "".join(str(abs(z) // 10) if z % 10 == 0 else " " for z in range(z0, z1 + 1)))
        for x in range(x1, x0 - 1, -1):
            print(f"   x {x:4d} " + "".join(kind(c.name(x, y, z)) for z in range(z0, z1 + 1)))
    x0, x1, z0, z1 = -14, 58, SOUTH_Z - 1, SOUTH_Z + 9
    print(f"== the south wall and the rock at its foot: z {z0}..{z1} (down the page), x {x0}..{x1}")
    print("   the top block of each column at y -1 or lower, as its depth under the paving (0 = y -1, a = 10)")
    print("          " + "".join(str(abs(x) // 10) if x % 10 == 0 else " " for x in range(x0, x1 + 1)))
    print("          " + "".join(str(abs(x) % 10) for x in range(x0, x1 + 1)))
    for z in range(z0, z1 + 1):
        print(f"   z {z:4d} " + "".join(depth(top(c, x, z)) for x in range(x0, x1 + 1)))
    print("   what that block is")
    for z in range(z0, z1 + 1):
        print(f"   z {z:4d} " + "".join(kind(c.name(x, top(c, x, z), z)) if top(c, x, z) is not None else " "
                                        for x in range(x0, x1 + 1)))
    print("== the buttresses of the south wall: x, the rows of the buttress, the top row of the rock 1, 2, 3 and 4"
          " cells south of it and what lies there")
    for x in SOUTH_X:
        rows = [y for y in range(-2, LOW - 1, -1) if "deepslate_brick" in (plain(c.name(x, y, SOUTH_Z + 1)) or "")]
        out = []
        for dz in (2, 3, 4, 5):
            y = top(c, x, SOUTH_Z + dz)
            out.append(f"{y} {plain(c.name(x, y, SOUTH_Z + dz)) if y is not None else '-'}")
        print(f"   x {x:4d}  buttress rows {min(rows) if rows else '-'}..{max(rows) if rows else '-'}   " + "; ".join(out))
    print("== the letters")
    for ch in sorted(names):
        print(f"  {ch}  " + ", ".join(f"{n} x{k}" for n, k in names[ch].most_common(8)))
    print("== display entities at the east wall's foot and under the south wall (x, y, z, model)")
    for x, y, z, nbt in c.entities:
        east = EAST_X - 1 <= x <= EAST_X + 11 and -8 <= y <= 1
        south = SOUTH_Z - 1 <= z <= SOUTH_Z + 10 and LOW - 2 <= y <= 1 and x <= 58
        if east or south:
            item = nbt.get("item", {})
            model = item.get("components", {}).get("minecraft:item_model", "") if isinstance(item, dict) else ""
            print(f"  {x:7.2f} {y:6.2f} {z:7.2f}  {nbt.get('id', '')} {model}")


# ---- the faces that are measured ---------------------------------------------------------------------------
def faces(view):
    """[(name, the four corners of a rectangle in the scene)]: for V1 the east wall north of the
    stair, for V11 the south wall west of the way down to the lookout."""
    out = []
    if view == "v1":
        for z in (-14, -22, -30, -38):
            out.append((f"buttress z {z}, lower stage", [(EAST_X + 3, y, zz) for y in (-6, -4) for zz in (z, z + 1)]))
            out.append((f"buttress z {z}, upper stage", [(EAST_X + 2, y, zz) for y in (-3, -2) for zz in (z, z + 1)]))
        for z in (-18, -26, -34):
            out.append((f"wall, the bay round z {z}", [(EAST_X + 1, y, zz) for y in (-5, -2) for zz in (z - 2, z + 3)]))
    else:
        for x in (43, 39, 35, 31, 27, 23, 19, 14, 10):
            out.append((f"buttress x {x}, rows -4 and -3", [(xx, y, SOUTH_Z + 2) for y in (-4, -2) for xx in (x, x + 1)]))
        for x in (39, 23, 19):
            out.append((f"buttress x {x}, row -5", [(xx, y, SOUTH_Z + 2) for y in (-5, -4) for xx in (x, x + 1)]))
        for x in (41, 37, 33, 29, 25, 21):
            out.append((f"wall, the bay round x {x}", [(xx, y, SOUTH_Z + 1) for y in (-4, -2) for xx in (x - 1, x + 2)]))
    return out


def crop(view, path, out, scale=3):
    """The part of a picture the faces of a view lie in, with a margin, `scale` times as large."""
    from PIL import Image
    img = Image.open(path).convert("RGB")
    w, h = img.size
    pts = [project(view, (w, h), p) for _name, corners in faces(view) for p in corners]
    pts = [p for p in pts if p is not None]
    c0, c1 = max(0, int(min(p[0] for p in pts)) - w // 20), min(w, int(max(p[0] for p in pts)) + w // 20)
    r0, r1 = max(0, int(min(p[1] for p in pts)) - h // 8), min(h, int(max(p[1] for p in pts)) + h // 10)
    part = img.crop((c0, r0, c1, r1))
    part = part.resize((part.size[0] * scale, part.size[1] * scale), Image.NEAREST)
    part.save(out)
    print(f"{out}: columns {c0}..{c1}, rows {r0}..{r1} of {path}, x{scale}")


def project(view, size, p):
    """Where a point of the scene falls in a picture of `size` taken from a view: (column, row),
    or None when it lies behind the eye."""
    eye, at = VIEWS[view]["pos"], VIEWS[view]["look_at"]
    f = [at[i] - eye[i] for i in range(3)]
    n = math.sqrt(sum(v * v for v in f))
    f = [v / n for v in f]
    r = [-f[2], 0.0, f[0]]                              # f x up: looking west, north is on the right
    n = math.hypot(r[0], r[2])
    r = [v / n for v in r]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    d = [p[i] - eye[i] for i in range(3)]
    zc = sum(d[i] * f[i] for i in range(3))
    if zc <= 0.1:
        return None
    xc, yc = sum(d[i] * r[i] for i in range(3)), sum(d[i] * u[i] for i in range(3))
    w, h = size
    t = math.tan(math.radians(FOV / 2.0))
    return w / 2.0 + xc / zc / (t * w / h) * w / 2.0, h / 2.0 - yc / zc / t * h / 2.0


def luma(view, paths):
    from PIL import Image
    for path in paths:
        img = Image.open(path).convert("RGB")
        w, h = img.size
        px = img.load()
        print(f"== {path} ({w}x{h}), view {view}: the luma of each face, its middle 60% (columns, rows, pixels)")
        for name, corners in faces(view):
            pts = [project(view, (w, h), p) for p in corners]
            if any(p is None for p in pts):
                print(f"   {name}: behind the eye")
                continue
            cols, rows = sorted(p[0] for p in pts), sorted(p[1] for p in pts)
            # the inner box: between the second and the third of the four, drawn in by a fifth
            c0, c1, r0, r1 = cols[1], cols[2], rows[1], rows[2]
            if c1 - c0 < 1.0:
                c0, c1 = cols[0], cols[3]
            c0, c1 = c0 + 0.2 * (c1 - c0), c1 - 0.2 * (c1 - c0)
            r0, r1 = r0 + 0.2 * (r1 - r0), r1 - 0.2 * (r1 - r0)
            box = [(i, k) for i in range(int(math.floor(c0)), int(math.ceil(c1)) + 1)
                   for k in range(int(math.floor(r0)), int(math.ceil(r1)) + 1) if 0 <= i < w and 0 <= k < h]
            if not box:
                print(f"   {name}: outside the picture ({c0:.0f}..{c1:.0f}, {r0:.0f}..{r1:.0f})")
                continue
            total = 0.0
            for i, k in box:
                red, green, blue = px[i, k]
                total += (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255.0
            print(f"   {name}: {total / len(box):.3f}   ({c0:.0f}..{c1:.0f}, {r0:.0f}..{r1:.0f}, {len(box)} px)")


def light():
    from scenes import obs
    from scenes.obs.sky import _lightkit as L
    from scenes.obs.sky import lights
    c = obs.build()
    r = lights.report(c)
    print("== the projectors at the walls' feet: " + (", ".join(str(cell) for cell in r.get("base", [])) or "none"))
    for note in r["notes"]:
        if "projector" in note:
            print(f"   note: {note}")
    lv = L.levels(c, (EAST_X - 2, -9, -46), (EAST_X + 12, 3, 46))
    print("== the east wall: block light before the buttresses' faces, rows -6 (the foot) to -2")
    for z in EAST_Z:
        low = [lv.get((EAST_X + 3, y, z), 0) for y in (-6, -5)]
        up = [lv.get((EAST_X + 2, y, z), 0) for y in (-4, -3, -2)]
        side = [lv.get((EAST_X + 1, y, z + 1), 0) for y in (-6, -5, -4, -3, -2)]
        bay = [lv.get((EAST_X + 1, y, z + 4), 0) for y in (-6, -5, -4, -3, -2)]
        print(f"   z {z:4d}  lower stage {low}  upper stage {up}  the wall beside it {side}  the middle of the bay {bay}")
    lv = L.levels(c, (-16, LOW - 4, SOUTH_Z - 2), (60, 3, SOUTH_Z + 12))
    print("== the south wall: block light before the buttresses' faces, from the foot up to row -2")
    for x in SOUTH_X:
        rows = [y for y in range(-2, LOW - 1, -1) if "deepslate_brick" in (plain(c.name(x, y, SOUTH_Z + 1)) or "")]
        if not rows:
            continue
        face = [lv.get((x, y, SOUTH_Z + 2), 0) for y in range(min(rows), -1)]
        side = [lv.get((x + 1, y, SOUTH_Z + 1), 0) for y in range(min(rows), -1)]
        bay = [lv.get((x + 2, y, SOUTH_Z + 1), 0) for y in range(min(rows), -1)]
        print(f"   x {x:4d}  rows {min(rows)}..-2  face {face}  the wall beside it {side}  two cells on {bay}")
    print("== sky/lights")
    for line in lights.summary(c):
        if not line.startswith(("rejected", "moved", "merged", "capped")):
            print("   " + line)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    if what == "survey":
        survey()
    elif what == "light":
        light()
    elif what == "luma" and len(sys.argv) > 3 and sys.argv[2] in VIEWS:
        luma(sys.argv[2], sys.argv[3:])
    elif what == "crop" and len(sys.argv) == 5 and sys.argv[2] in VIEWS:
        crop(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print(__doc__)
        sys.exit(2)
