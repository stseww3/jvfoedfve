"""Everything between the buildings: stair, paths, pond and waterfall, dock, airship, small props."""
import math

from artkit import arch as A
from artkit import blocks as B
from artkit import trees as T
from artkit.canvas import Mix, hash3

STEP = Mix({"stone_bricks": 64, "mossy_stone_bricks": 14, "cobblestone": 12, "andesite": 10}, seed=61)
MASON = Mix({"cobblestone": 34, "stone_bricks": 30, "andesite": 14, "mossy_cobblestone": 12, "stone": 10}, seed=62)
PATH = Mix({"dirt_path": 56, "gravel": 18, "coarse_dirt": 12, "cobblestone": 8, "mossy_cobblestone": 4,
            "rooted_dirt": 2}, seed=63)
BED = Mix({"gravel": 40, "clay": 20, "sand": 15, "stone": 15, "mud": 10}, seed=64)
SHORE = Mix({"grass_block": 40, "moss_block": 14, "mossy_cobblestone": 16, "gravel": 12, "stone": 10,
             "coarse_dirt": 8}, seed=65)
ROCK = Mix({"stone": 44, "andesite": 20, "cobblestone": 18, "mossy_cobblestone": 8, "tuff": 10}, seed=66)
WATER = "water[level=0]"


def lamp(c, land, x, z):
    y = land.y(x, z)
    if y is None:
        return
    for h in range(1, 6):
        c.clear(x, y + h, z)
    c.set(x, y + 1, z, "cobblestone_wall")
    c.set(x, y + 2, z, "spruce_fence")
    c.set(x, y + 3, z, "spruce_fence")
    c.set(x, y + 4, z, "lantern[hanging=false]")
    land.kind[(x, z)] = "built"


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
    c.set(x_out + 6, y + 1, z0 - half_w + 1, "composter")
    c.set(x_out + 7, y + 1, z0 - half_w + 1, "barrel[facing=up]")


def airship(c, cx, cy, cz, half_len=9.5, radius=4.4):
    """Small moored airship, nose to the west: striped teardrop envelope, open gondola beneath."""
    cream, red = "white_terracotta", "red_terracotta"
    cx, cy, cz = int(cx), int(cy), int(cz)

    def at(u, v):  # u runs towards the nose, v sideways
        return cx - u, cz + v

    def r_at(u):
        t = u / half_len
        if abs(t) >= 1:
            return 0.0
        return radius * math.sqrt(1 - t * t) * (0.85 + 0.15 * t)

    n = int(half_len) + 1
    for u in range(-n, n + 1):
        r = r_at(u)
        if r <= 0:
            continue
        for v in range(-int(radius) - 1, int(radius) + 2):
            for w in range(-int(radius) - 1, int(radius) + 2):
                d = math.hypot(v, w)
                if d > r or d < r - 1.6:
                    continue
                gore = int(math.floor((math.atan2(w, v) + math.pi + math.pi / 8) / (math.tau / 8))) % 8
                x, z = at(u, v)
                c.set(x, cy + w, z, red if (gore % 2 or abs(u) > half_len - 1.2) else cream)
    # cruciform tail
    for k, u in enumerate(range(-n + 1, -n + 6)):
        reach = 4.0 - 0.45 * k
        r = r_at(u)
        for j in range(int(r), int(math.ceil(reach)) + 1):
            if j < r - 0.5 or j > reach:
                continue
            for v, w in ((0, j), (0, -j), (j, 0), (-j, 0)):
                x, z = at(u, v)
                c.set(x, cy + w, z, red, keep=True)

    # gondola
    gy = cy - int(radius) - 6
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
    for du in (-4, 4):
        x, z = at(du, 0)
        c.set(x, gy + 2, z, "dark_oak_log")
        c.set(x, gy + 3, z, "dark_oak_fence")
        c.set(x, gy + 4, z, "lantern[hanging=false]")
    for du, v in ((-2, -2), (2, -2), (-2, 2), (2, 2), (-3, -1), (3, -1), (-3, 1), (3, 1)):
        x, z = at(du, v)
        y = gy + 3
        while not c.has(x, y, z) and y < cy:
            c.set(x, y, z, "iron_chain[axis=y]")
            y += 1
    x, z = at(1, -1)
    c.set(x, gy + 1, z, "barrel[facing=up]")
    x, z = at(-1, 1)
    c.set(x, gy + 1, z, "chest[facing=north]")
    return gy


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
