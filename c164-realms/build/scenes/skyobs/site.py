"""Everything between the buildings: stair, paths, pond and waterfall, dock, airship, small props."""
import math

from artkit import arch as A
from artkit import blocks as B
from artkit import pixelart as P
from artkit import respack
from artkit import trees as T
from artkit.canvas import Mix, hash3

from . import props

STEP = Mix({"stone_bricks": 64, "mossy_stone_bricks": 14, "cobblestone": 12, "andesite": 10}, seed=61)
MASON = Mix({"cobblestone": 34, "stone_bricks": 30, "andesite": 14, "mossy_cobblestone": 12, "stone": 10}, seed=62)
PATH = Mix({"dirt_path": 56, "gravel": 18, "coarse_dirt": 12, "cobblestone": 8, "mossy_cobblestone": 4,
            "rooted_dirt": 2}, seed=63)
BED = Mix({"gravel": 40, "clay": 20, "sand": 15, "stone": 15, "mud": 10}, seed=64)
SHORE = Mix({"grass_block": 40, "moss_block": 14, "mossy_cobblestone": 16, "gravel": 12, "stone": 10,
             "coarse_dirt": 8}, seed=65)
ROCK = Mix({"stone": 44, "andesite": 20, "cobblestone": 18, "mossy_cobblestone": 8, "tuff": 10}, seed=66)
WATER = "water[level=0]"


def lamp(c, land, x, z, toward=None):
    """Timber lamp post (custom model) on a stone stub; its arm reaches towards the point `toward`."""
    y = land.y(x, z)
    if y is None:
        return
    for h in range(1, 6):
        c.clear(x, y + h, z)
    c.set(x, y + 1, z, "andesite_wall")
    yaw = 0.0
    if toward is not None:
        yaw = math.degrees(math.atan2(toward[1] - (z + 0.5), toward[0] - (x + 0.5)))
    props.place(c, "lamp_post", x + 0.5, y + 2, z + 0.5, yaw=yaw)
    reach = 9.0 / 16.0
    lx = int(math.floor(x + 0.5 + reach * math.cos(math.radians(yaw))))
    lz = int(math.floor(z + 0.5 + reach * math.sin(math.radians(yaw))))
    c.set(lx, y + 4, lz, "light[level=14]", keep=True)
    land.kind[(x, z)] = "built"


def reserve(c, land, x, z, height=3):
    """Keep a ground cell free of plants for something that will stand on it."""
    y = land.y(x, z)
    if y is not None:
        for h in range(1, height + 1):
            c.clear(x, y + h, z)
        land.kind[(x, z)] = "built"
    return y


def nearest_on(pts, x, z):
    """Closest point to (x, z) on the polyline pts."""
    best = None
    for (xa, za), (xb, zb) in zip(pts, pts[1:]):
        dx, dz = xb - xa, zb - za
        t = max(0.0, min(1.0, ((x - xa) * dx + (z - za) * dz) / (dx * dx + dz * dz)))
        q = (xa + dx * t, za + dz * t)
        d = math.hypot(q[0] - x, q[1] - z)
        if best is None or d < best[0]:
            best = (d, q)
    return best[1]


def garland(c, a, b, sag=0.5):
    """Bunting from point a to point b, hanging in a shallow curve."""
    dx, dy, dz = (b[i] - a[i] for i in range(3))
    n = max(1, int(round(math.hypot(dx, dz))))
    yaw = math.degrees(math.atan2(dz, dx))
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append((a[0] + dx * t, a[1] + dy * t - sag * 4 * t * (1 - t), a[2] + dz * t))
    for q, r in zip(pts, pts[1:]):
        run, rise = math.hypot(r[0] - q[0], r[2] - q[2]), r[1] - q[1]
        props.place(c, "bunting", q[0], q[1], q[2], yaw=yaw, turns=(("z", math.degrees(math.atan2(rise, run))),),
                    scale=(math.hypot(run, rise), 1.0, 1.0))


def pedestal(c, land, x, z):
    """Stone plinth for the armillary sphere: a slab step around a chiselled block. Returns the top y."""
    y = land.y(x, z)
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            for h in range(1, 7):
                c.clear(x + dx, y + h, z + dz)
            A.fill_down(c, x + dx, y, z + dz, MASON(x + dx, y, z + dz), limit=3)
            c.set(x + dx, y, z + dz, MASON)
            if (dx, dz) != (0, 0):
                c.set(x + dx, y + 1, z + dz, B.slab(STEP(x + dx, y + 1, z + dz)))
            land.kind[(x + dx, z + dz)] = "built"
            land.top[(x + dx, z + dz)] = y
    c.set(x, y + 1, z, "chiseled_stone_bricks")
    c.set(x, y + 2, z, "stone_brick_wall")
    return y + 3


def grand_stair(c, land, x0, x1, z_top, y_top, y_ground, landing_after=4, landing_len=3):
    """Stair running south from a plateau edge. Returns the z of the first ground cell after it."""
    profile = []
    z, y = z_top, y_top
    for z_flat in (z_top - 2, z_top - 1):
        profile.append((z_flat, y_top, "flat"))
    steps = 0
    while y > y_ground:
        profile.append((z, y, "step"))
        z += 1
        y -= 1
        steps += 1
        if steps == landing_after:
            for _ in range(landing_len):
                profile.append((z, y, "flat"))
                z += 1
    for zz, yy, kind in profile:
        for x in range(x0 - 1, x1 + 2):
            cheek = x in (x0 - 1, x1 + 1)
            for h in range(1, 7):
                c.clear(x, yy + h, zz)
            if kind == "step":
                c.set(x, yy, zz, MASON if cheek else B.stairs(STEP(x, yy, zz), "north"))
            else:
                c.set(x, yy, zz, MASON)
            if cheek:
                top = STEP(x, yy + 1, zz)
                c.set(x, yy + 1, zz, B.stairs(top, "north") if kind == "step" else B.slab(top))
            A.fill_down(c, x, yy - 1, zz, MASON(x, yy - 1, zz), limit=14)
            if (x, zz) in land.top:
                land.kind[(x, zz)] = "built"
                land.top[(x, zz)] = yy
    # lantern posts on the cheeks: top, landing, foot
    flats = [p for p in profile if p[2] == "flat"]
    marks = [flats[1], flats[2 + landing_len // 2] if len(flats) > 2 else None, (z, y_ground, "foot")]
    for m in marks:
        if not m:
            continue
        zz, yy, kind = m
        for x in (x0 - 1, x1 + 1):
            base = yy + 1
            if kind == "foot":
                c.set(x, base, zz, "stone_bricks")
                A.fill_down(c, x, base - 1, zz, "cobblestone", limit=3)
                land.kind[(x, zz)] = "built"
            else:
                c.set(x, base, zz, "stone_bricks")
            c.set(x, base + 1, zz, "stone_brick_wall")
            c.set(x, base + 2, zz, "lantern[hanging=false]")
    return z


def path(c, land, pts, width=2.6, seed=0):
    cells = set()
    for (xa, za), (xb, zb) in zip(pts, pts[1:]):
        n = int(max(abs(xb - xa), abs(zb - za)) * 2) + 1
        for i in range(n + 1):
            t = i / n
            px, pz = xa + (xb - xa) * t, za + (zb - za) * t
            w = width / 2 + 0.6 * (hash3(int(px) // 3, 0, int(pz) // 3, seed) - 0.5)
            for x in range(int(px - w) - 1, int(px + w) + 2):
                for z in range(int(pz - w) - 1, int(pz + w) + 2):
                    if math.hypot(x + 0.5 - px, z + 0.5 - pz) <= w:
                        cells.add((x, z))
    for x, z in cells:
        if land.kind.get((x, z)) in ("grass", "moss", "rock", "duff"):
            y = land.top[(x, z)]
            c.set(x, y, z, PATH)
            land.kind[(x, z)] = "path"


def pond(c, land, cx, cz, rx, rz, level, outlet):
    """Pond with a short stream that leaves the island at the last outlet point (a waterfall)."""
    wet = set()
    for x in range(int(cx - rx) - 3, int(cx + rx) + 4):
        for z in range(int(cz - rz) - 3, int(cz + rz) + 4):
            if (x, z) not in land.top:
                continue
            d = ((x + 0.5 - cx) / rx) ** 2 + ((z + 0.5 - cz) / rz) ** 2 + 0.3 * (hash3(x // 2, 3, z // 2, 67) - 0.5)
            if d <= 1.0:
                wet.add((x, z, 2 if d < 0.5 else 1))
    end = outlet[-1]
    done = False
    for (xa, za), (xb, zb) in zip(outlet, outlet[1:]):
        n = int(max(abs(xb - xa), abs(zb - za)) * 2) + 1
        for i in range(n + 1):
            t = i / n
            px, pz = xa + (xb - xa) * t, za + (zb - za) * t
            if (int(math.floor(px)), int(math.floor(pz))) not in land.top:
                end = (px, pz)  # the stream leaves the island here
                done = True
                break
            for x in range(int(px) - 2, int(px) + 3):
                for z in range(int(pz) - 2, int(pz) + 3):
                    if math.hypot(x + 0.5 - px, z + 0.5 - pz) <= 1.05 and (x, z) in land.top:
                        if not any(w[0] == x and w[1] == z for w in wet):
                            wet.add((x, z, 1))
        if done:
            break
    cells = {(x, z) for x, z, _ in wet}
    for x, z, depth in wet:
        for y in range(level + 1, level + 7):
            c.clear(x, y, z)
        for y in range(level - depth + 1, level + 1):
            c.set(x, y, z, WATER)
        c.set(x, level - depth, z, BED)
        A.fill_down(c, x, level - depth - 1, z, ROCK(x, level - depth - 1, z), limit=6)
        land.kind[(x, z)] = "water"
        land.top[(x, z)] = level
    # banks: nothing next to the water may be lower than the water, except at the outlet
    for x, z in cells:
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, z + dz)
            if n in cells:
                continue
            if math.hypot(n[0] + 0.5 - end[0], n[1] + 0.5 - end[1]) <= 2.3:
                continue
            ty = land.top.get(n)
            if ty is None or ty < level:
                for y in range(level, level - 3, -1):
                    c.set(n[0], y, n[1], ROCK, keep=True)
                land.top[n] = level
                land.kind[n] = "rock"
            elif ty == level and land.kind.get(n) in ("grass", "moss"):
                c.set(n[0], ty, n[1], SHORE)
                if c.name(n[0], ty, n[1]) not in ("grass_block", "moss_block"):
                    land.kind[n] = "rock"
    # lily pads and reeds
    for x, z, depth in wet:
        h = hash3(x, 9, z, 68)
        if depth == 2 and h < 0.14:
            c.set(x, level + 1, z, "lily_pad")
        elif depth == 1 and h < 0.10:
            c.set(x, level - 0, z, "seagrass")
    for x, z in cells:
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, z + dz)
            if n in cells or land.kind.get(n) not in ("grass", "moss"):
                continue
            if hash3(n[0], 10, n[1], 69) < 0.16 and not c.has(n[0], level + 1, n[1]):
                for h in range(1, 2 + int(hash3(n[0], 11, n[1], 69) * 3)):
                    c.set(n[0], level + h, n[1], "sugar_cane")
                land.kind[n] = "built"
    # reed clumps (custom model) standing in the shallows along the bank
    for x, z, depth in sorted(wet):
        if depth != 1 or c.has(x, level + 1, z) or math.hypot(x + 0.5 - end[0], z + 0.5 - end[1]) < 5:
            continue
        on_bank = any((x + dx, z + dz) not in cells for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if on_bank and hash3(x, 12, z, 70) < 0.3:
            props.place(c, "cattail", x + 0.3 + 0.4 * hash3(x, 14, z, 70), level, z + 0.3 + 0.4 * hash3(x, 15, z, 70),
                        yaw=360.0 * hash3(x, 13, z, 70))


def dock(c, land, x_in, x_out, z0, half_w, y):
    """Timber landing stage running west from x_in (on land) to x_out (over the void)."""
    for x in range(x_out, x_in + 1):
        over = (x, z0) not in land.top or land.top[(x, z0)] < y - 1
        for z in range(z0 - half_w, z0 + half_w + 1):
            edge = abs(z - z0) == half_w
            for h in range(1, 6):
                c.clear(x, y + h, z)
            if edge:
                c.set(x, y, z, "spruce_log[axis=x]")
            elif (x, z) in land.top and land.top[(x, z)] >= y:
                c.set(x, y, z, "spruce_planks")
            else:
                c.set(x, y, z, "spruce_slab[type=top]" if hash3(x, 0, z, 71) > 0.08 else "spruce_planks")
            if (x, z) in land.top:
                land.kind[(x, z)] = "built"
                if land.top[(x, z)] > y:
                    for yy in range(y + 1, land.top[(x, z)] + 1):
                        c.clear(x, yy, z)
                    land.top[(x, z)] = y
        if over and (x - x_out) % 3 == 0:
            for z in range(z0 - half_w + 1, z0 + half_w):
                c.set(x, y - 1, z, "spruce_log[axis=z]", keep=True)
            for z in (z0 - half_w, z0 + half_w):
                n = 0
                for yy in range(y - 1, y - 9, -1):
                    if c.has(x, yy, z):
                        break
                    c.set(x, yy, z, "spruce_log[axis=y]" if n < 4 else "spruce_fence")
                    n += 1
    for x in range(x_out + 1, x_in + 1):
        for z in (z0 - half_w, z0 + half_w):
            if x < x_in - 1:
                c.set(x, y + 1, z, "spruce_fence")
    for z in (z0 - half_w, z0 + half_w):
        for x in (x_out, x_in - 1):
            c.set(x, y + 1, z, "spruce_fence")
            c.set(x, y + 2, z, "spruce_fence")
            c.set(x, y + 3, z, "lantern[hanging=false]")
    # cargo
    c.set(x_out + 3, y + 1, z0 + half_w - 1, "barrel[facing=up]")
    c.set(x_out + 4, y + 1, z0 + half_w - 1, "barrel[facing=up]")
    c.set(x_out + 4, y + 2, z0 + half_w - 1, "barrel[facing=east]")
    c.set(x_out + 7, y + 1, z0 - half_w + 1, "barrel[facing=up]")
    zn, zs = z0 - half_w + 1.5, z0 + half_w - 0.5
    props.place(c, "crate", x_out + 6.5, y + 1, zn - 0.05, yaw=8.0)
    props.place(c, "crate", x_out + 5.45, y + 1, zn + 0.05, yaw=-6.0)
    props.place(c, "crate", x_out + 6.0, y + 1.75, zn, yaw=27.0)
    props.place(c, "trunk", x_out + 9.6, y + 1, zn - 0.1, yaw=4.0)
    props.place(c, "trunk", x_out + 9.55, y + 1 + 9.25 / 16, zn - 0.12, yaw=-9.0)
    props.place(c, "trunk", x_out + 6.6, y + 1, zs, yaw=84.0)
    props.place(c, "crate", x_out + 11.5, y + 1, zs - 0.02, yaw=-14.0)
    # a garland ties the two landward lanterns together, high enough to walk under
    garland(c, (x_in - 0.5, y + 3.7, z0 - half_w + 0.5), (x_in - 0.5, y + 3.7, z0 + half_w + 0.5), sag=0.3)


# the envelope is made of blocks the resource pack repaints as canvas (see scenes/skyobs/__init__.py)
CANVAS = {"cream": "white_glazed_terracotta", "shade": "yellow_glazed_terracotta",
          "red": "red_glazed_terracotta", "dark": "orange_glazed_terracotta"}
CANVAS_TONES = {
    "cream": ["#d9cba6", "#e4d7b4", "#ece1c2", "#f3ead0"],
    "shade": ["#bfae86", "#cbbb94", "#d5c7a2", "#ddd0ae"],
    "red": ["#8f2c25", "#a2352b", "#b24032", "#bf4c3b"],
    "dark": ["#6c1f1c", "#7b2520", "#8a2c25", "#96342b"],
}


def write_pack(pack_dir):
    """The canvas of the airship: four plain weaves painted over blocks the scene does not use otherwise."""
    out = []
    for n, (key, block) in enumerate(CANVAS.items()):
        mat = P.Mat("canvas_" + key, CANVAS_TONES[key], noise=0.5, bevel=0, base=2)
        out.append(respack.cube(pack_dir, block, mat.paint(16, 16, "u", 400 + n), name="canvas_" + key))
    return out


def airship(c, cx, gy, cz, half_len=17.0, radius=6.2, bow=1):
    """Moored airship, nose to the east (bow=1) or west (bow=-1). gy is the floor of the car; the
    envelope hangs above it with its greatest girth over the car and a long taper aft. Its canvas
    is cream, sewn from eight gores with red seams; nose cap, tail and fins are red.
    Returns the point of the nose, for a mooring line."""
    cream, shade, red, dark = (CANVAS[k] for k in ("cream", "shade", "red", "dark"))
    cx, gy, cz = int(cx), int(gy), int(cz)
    cy = gy + int(radius) + 7
    mid = -0.2 * half_len   # the envelope's middle lies aft of the car's by this much
    nose_u, tail_u = mid + 0.8 * half_len, mid - 1.2 * half_len
    turn = 180.0 if bow > 0 else 0.0   # the models were drawn for a nose to the west

    def at(u, v):  # u runs towards the nose, v sideways
        return cx + bow * u, cz + v

    def r_at(u):
        t = (u - mid) / half_len
        if t >= 0.2:
            k = (t - 0.2) / 0.6
            return radius * math.sqrt(1 - k * k) if k < 1 else 0.0
        k = (0.2 - t) / 1.4
        return radius * (1 - k * k) ** 0.8 if k < 1 else 0.0

    n = int(radius) + 2
    for u in range(math.floor(tail_u), math.ceil(nose_u) + 1):
        r = r_at(u)
        if r < 0.6:
            continue
        t = (u - mid) / half_len
        for v in range(-n, n + 1):
            for w in range(-n, n + 1):
                d = math.hypot(v, w)
                if d > r + 0.3 or d < r - 1.15:
                    continue
                ang = math.degrees(math.atan2(w, v)) % 360.0
                off = abs((ang + 22.5) % 45.0 - 22.5)          # degrees to the nearest of eight seams
                seam = math.radians(off) * d < 0.55
                if t > 0.64 or t < -0.96:
                    state = dark if seam and r > 2.5 else red
                elif seam:
                    state = red
                else:
                    state = shade if w < -0.45 * r and hash3(u, v, w, 77) < 0.75 else cream
                x, z = at(u, v)
                c.set(x, cy + w, z, state)
    # a copper spike on the nose
    x, z = at(math.floor(nose_u) + 1, 0)
    c.set(x, cy, z, f"lightning_rod[facing={'east' if bow > 0 else 'west'}]", keep=True)
    nose = (x + 0.5, cy + 0.5, z + 0.5)
    # four swept fins around the tail
    rise = (1.4, 2.4, 3.2, 3.7, 3.8, 3.4, 2.6, 1.6, 0.8)
    for k, h in enumerate(rise):
        u = math.floor(tail_u) + 1 + k
        r = max(r_at(u), 0.5)
        for j in range(int(r), int(math.ceil(r + h)) + 1):
            if j > r + h:
                continue
            tip = j > r + h - 1.0 or k == len(rise) - 1
            for v, w in ((0, j), (0, -j), (j, 0), (-j, 0)):
                x, z = at(u, v)
                c.set(x, cy + w, z, dark if tip else red, keep=j <= r - 0.5)
    # keel under the belly, where the car hangs from; lanterns under it fore and aft of the car
    for u in range(-7, 8):
        x, z = at(u, 0)
        w = -int(math.floor(r_at(u) + 0.3))
        while w < 0 and not c.has(x, cy + w, z):
            w += 1
        c.set(x, cy + w, z, "dark_oak_planks" if abs(u) % 3 else "dark_oak_log[axis=x]")
        if abs(u) == 6:
            c.set(x, cy + w - 1, z, "waxed_copper_chain[axis=y]")
            c.set(x, cy + w - 2, z, "lantern[hanging=true]")
    for du, v in ((3, 1), (3, -1), (-3, 1), (-3, -1)):
        x, z = at(du, v)
        for y in range(gy + 3, cy):
            if c.has(x, y, z):
                break
            c.set(x, y, z, "dark_oak_fence")

    # gondola
    for du in range(-4, 5):
        hw = 2 if abs(du) <= 2 else 1 if abs(du) == 3 else 0
        for v in range(-hw, hw + 1):
            x, z = at(du, v)
            side = abs(v) == hw or abs(du) >= 3
            if hw > 0 and abs(v) == hw:
                c.set(x, gy, z, B.stairs("spruce_planks", "south" if v < 0 else "north", "top"))
            else:
                c.set(x, gy, z, "spruce_planks")
            if side:
                c.set(x, gy + 1, z, "spruce_planks" if abs(du) < 4 else "dark_oak_log")
                if abs(du) < 4:
                    c.set(x, gy + 2, z, "spruce_fence")
    # keel
    for du in range(-3, 4):
        x, z = at(du, 0)
        c.set(x, gy - 1, z, "dark_oak_slab[type=top]")
    for du in (-4, 4):
        x, z = at(du, 0)
        c.set(x, gy + 2, z, "dark_oak_log")
        c.set(x, gy + 3, z, "dark_oak_fence")
        c.set(x, gy + 4, z, "lantern[hanging=false]")
    # rigging: ropes from the rail up to the envelope, splayed fore and aft
    def hull(u, deg):
        """Point just inside the envelope skin at station u, `deg` around from straight down."""
        r = r_at(u) - 0.45
        x, z = at(u, 0)
        return x + 0.5, cy + 0.5 - r * math.cos(math.radians(deg)), z + 0.5 + r * math.sin(math.radians(deg))

    for du, v, ue, deg in ((2, 2, 5, 40), (2, -2, 5, -40), (-2, 2, -6, 40), (-2, -2, -6, -40),
                           (3, 1, 9, 26), (3, -1, 9, -26), (-3, 1, -11, 26), (-3, -1, -11, -26),
                           (0, 2, 0, 50), (0, -2, 0, -50)):
        x, z = at(du, v)
        props.stretch(c, "rope", (x + 0.5, gy + 3.0, z + 0.5), hull(ue, deg), thick=1.5)
    # outboard engines on the after part of the car, propellers astern
    x, _ = at(-2, 0)
    south, north = ("engine_pod_n", "engine_pod_s") if bow > 0 else ("engine_pod_s", "engine_pod_n")
    props.place(c, south, x + 0.5, gy + 1.5, cz + 3.02, yaw=turn)
    props.place(c, north, x + 0.5, gy + 1.5, cz - 2.02, yaw=turn)
    # helm at the forward end, cargo aft
    x, z = at(2, 0)
    props.place(c, "ship_wheel", x + 0.5, gy + 1, z + 0.5, yaw=turn)
    x, z = at(-1, 1)
    c.set(x, gy + 1, z, "barrel[facing=up]")
    x, z = at(-2, -1)
    props.place(c, "trunk", x + 0.5, gy + 1, z + 0.6, yaw=90.0)
    return nose


def boulders(c, land, seed=0, spacing=8.0):
    """Weathered rocks: a loose string near the rim and a few further in."""
    picked = []
    for (x, z) in sorted(land.edge):
        e = land.edge[(x, z)]
        if not 0.035 < e < 0.30 or land.kind.get((x, z)) not in ("grass", "moss"):
            continue
        if hash3(x, 51, z, seed) > (0.02 if e < 0.14 else 0.004):
            continue
        if any(math.hypot(x - a, z - b) < spacing for a, b in picked):
            continue
        picked.append((x, z))
    for (x0, z0) in picked:
        r = 1.3 + 1.9 * hash3(x0, 52, z0, seed)
        hmax = 0.9 + 0.85 * r * (0.6 + 0.4 * hash3(x0, 53, z0, seed))
        sx = 0.75 + 0.5 * hash3(x0, 54, z0, seed)
        n = int(r / min(sx, 1.0)) + 2
        cells = []
        for dx in range(-n, n + 1):
            for dz in range(-n, n + 1):
                cell = (x0 + dx, z0 + dz)
                if cell not in land.top or land.kind.get(cell) not in ("grass", "moss", "rock"):
                    continue
                d = math.hypot(dx / sx, dz * sx) / r + 0.35 * (hash3(cell[0], 55, cell[1], seed) - 0.5)
                if d >= 1:
                    continue
                cells.append((cell, hmax * math.sqrt(1 - d * d)))
        base = min((land.top[cell] for cell, _ in cells), default=None)
        if base is None:
            continue
        for cell, h in cells:
            x, z = cell
            ty = land.top[cell]
            top = base + h          # the rock's crown is level, the ground may slope under it
            full = int(math.floor(top + 0.25))
            if full < ty:
                continue
            c.set(x, ty, z, ROCK)
            for y in range(ty + 1, full + 1):
                c.set(x, y, z, ROCK if hash3(x, y, z, seed + 56) > 0.16 else "moss_block")
            land.top[cell] = max(ty, full)
            land.kind[cell] = "rock"
            if top - full >= 0.3 and not c.has(x, full + 1, z):
                name = c.name(x, full, z)
                sl = B.variant(name, "slab") if name != "moss_block" else None
                if sl:
                    c.set(x, full + 1, z, f"{sl}[type=bottom]")
                    land.kind[cell] = "built"


def garden(c, land, x0, z0, x1, z1, y):
    """Fenced kitchen garden; y is the ground block level."""
    crops = ["wheat[age=7]", "carrots[age=7]", "wheat[age=6]", "beetroots[age=3]", "potatoes[age=7]", "wheat[age=7]"]
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            for h in range(1, 6):
                c.clear(x, y + h, z)
            A.fill_down(c, x, y - 1, z, "dirt", limit=4)
            land.kind[(x, z)] = "built"
            land.top[(x, z)] = y
            edge = x in (x0, x1) or z in (z0, z1)
            if edge:
                c.set(x, y, z, "coarse_dirt" if hash3(x, 0, z, 73) < 0.5 else "grass_block")
                c.set(x, y + 1, z, "spruce_fence")
            else:
                c.set(x, y, z, "farmland[moisture=7]")
                if hash3(x, 1, z, 73) < 0.9:
                    c.set(x, y + 1, z, crops[(x - x0) % len(crops)])
    gz = z1
    gx = (x0 + x1) // 2
    c.set(gx, y + 1, gz, "spruce_fence_gate[facing=south,open=false]")
    c.set(gx, y, gz, "dirt_path")
    # scarecrow
    sx, sz = x0 + 2, (z0 + z1) // 2
    c.set(sx, y, sz, "coarse_dirt")
    c.set(sx, y + 1, sz, "spruce_fence")
    c.set(sx, y + 2, sz, "hay_block")
    c.set(sx - 1, y + 2, sz, "spruce_fence")
    c.set(sx + 1, y + 2, sz, "spruce_fence")
    c.set(sx, y + 3, sz, "carved_pumpkin[facing=south]")
    for x in (x0, x1):
        for z in (z0, z1):
            c.set(x, y + 2, z, "spruce_fence")
    c.set(x1, y + 3, z1, "lantern[hanging=false]")


def woodpile(c, x, y, z, length=3, face_axis="z"):
    for i in range(length):
        for h in range(2):
            if h == 1 and i == length - 1:
                continue
            c.set(x + (i if face_axis == "x" else 0), y + h, z + (i if face_axis == "z" else 0),
                  f"spruce_log[axis={'z' if face_axis == 'x' else 'x'}]")


def bench(c, x, y, z, n=3, facing="north"):
    """Seat made of stairs; `facing` is where the backrest is."""
    for i in range(n):
        c.set(x + i, y, z, B.stairs("spruce_planks", facing))
    side = "east" if facing in ("north", "south") else "south"
    c.set(x - 1, y, z, f"spruce_trapdoor[facing={A.OPP[side]},open=true]")
    c.set(x + n, y, z, f"spruce_trapdoor[facing={side},open=true]")


def islet(c, cx, cy, cz, r, depth, seed, tree=None):
    """Small floating rock with a grassy cap."""
    tops = {}
    for x in range(int(cx - r) - 2, int(cx + r) + 3):
        for z in range(int(cz - r) - 2, int(cz + r) + 3):
            wob = 0.35 * (hash3(x // 2, 1, z // 2, seed) - 0.5) + 0.2 * (hash3(x, 2, z, seed) - 0.5)
            dn = math.hypot(x - cx, z - cz) / r + wob
            if dn >= 1.0:
                continue
            e = 1.0 - dn
            top = cy + (1 if e > 0.55 and hash3(x // 3, 3, z // 3, seed) < 0.5 else 0) - (1 if e < 0.12 else 0)
            bot = cy - 1 - int(depth * e ** 0.8 * (0.75 + 0.5 * hash3(x // 2, 4, z // 2, seed)))
            for y in range(bot, top + 1):
                d = top - y
                if d == 0:
                    state = "grass_block" if hash3(x, 5, z, seed) < 0.85 else "moss_block"
                elif d <= 2 and e > 0.1:
                    state = "dirt"
                else:
                    t = (cy - y) / max(depth, 1)
                    h = hash3(x, y, z, seed)
                    state = ("deepslate" if h < 0.5 else "tuff") if t > 0.75 else ROCK(x, y, z) if t < 0.45 else \
                        ("tuff" if h < 0.45 else "stone" if h < 0.8 else "andesite")
                c.set(x, y, z, state)
            tops[(x, z)] = top
    for (x, z), top in tops.items():
        h = hash3(x, 6, z, seed)
        if c.has(x, top + 1, z):
            continue
        if h < 0.35:
            c.set(x, top + 1, z, "short_grass")
        elif h < 0.42:
            c.set(x, top + 1, z, "fern")
        elif h < 0.47:
            c.set(x, top + 1, z, "oxeye_daisy" if h < 0.445 else "poppy")
        elif h < 0.50:
            T.bush(c, x, top + 1, z, seed + x, T.leaf("azalea_leaves"))
    if tree:
        kind, height = tree
        ty = tops.get((int(cx), int(cz)), cy) + 1
        if kind == "spruce":
            T.spruce(c, int(cx), ty, int(cz), height, seed + 5)
        else:
            T.broadleaf(c, int(cx), ty, int(cz), height, max(3, height // 2), seed + 5, log="birch_log",
                        leaves=T.leaf_mix("birch_leaves"), squash=0.7, lift=(0.5, 1.0), clumps=0.85)
    # vines off the rim
    for (x, z), top in tops.items():
        for face, dx, dz in (("north", 0, 1), ("south", 0, -1), ("west", 1, 0), ("east", -1, 0)):
            n = (x + dx, z + dz)
            if n in tops or hash3(n[0], 7, n[1], seed) > 0.22:
                continue
            for i in range(1 + int(hash3(n[0], 8, n[1], seed) * 5)):
                if c.has(n[0], top - i, n[1]) or (i == 0 and not c.has(x, top, z)):
                    break
                c.set(n[0], top - i, n[1], f"vine[{face}=true]")
    return tops
