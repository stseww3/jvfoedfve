"""The lesser islands: the lookout with the golden tree east of the tower, reached over a rope
bridge; the two basins that catch the waterfall on its way down to the clouds; the small rocks
adrift around the island. Every rock that floats has skystone growing under it.

Water is not placed as a fall anywhere: the game lets it run. A basin is a pool of still water
with a rim one block higher and a notch in the rim; the water runs out through the notch and
drops from the edge of the rock.
"""
import math
import random

from artkit import respack
from artkit import trees as T
from artkit.canvas import Mix, hash3

from . import props, site, skystone, terrain

ROCK = Mix({"stone": 44, "andesite": 20, "cobblestone": 18, "mossy_cobblestone": 8, "tuff": 10}, seed=71)
RIM = Mix({"mossy_cobblestone": 34, "cobblestone": 22, "stone": 20, "moss_block": 14, "andesite": 10}, seed=72)
BED = Mix({"gravel": 45, "stone": 25, "clay": 15, "mossy_cobblestone": 15}, seed=73)
GOLD_LEAVES = "pale_oak_leaves"   # repainted golden by the resource pack, as are the leaves it sheds
# three tones of the same foliage; the game picks one per block, which breaks up the crown
GOLDS = (
    (["#7a4a0e", "#a86c16", "#cf9224", "#ecb53a", "#ffd65c", "#fff0a0"], 5),
    (["#6a360a", "#93500f", "#bd7216", "#dc9426", "#f2b640", "#ffd872"], 3),
    (["#8a5c10", "#b98618", "#dfab2a", "#f6ca43", "#ffe46a", "#fff6b4"], 2),
)


# ---- the golden leaves ---------------------------------------------------------------------------
def _rgb(tone, tones=GOLDS[0][0]):
    s = tones[tone]
    return [int(s[i:i + 2], 16) for i in (1, 3, 5)] + [255]


def leaf_picture(tones, seed=11):
    """16x16 cut-out picture of golden foliage that tiles: small leaves, lighter towards their
    tips, over a dark ground with gaps to see through."""
    rng = random.Random(seed)
    tone = [[rng.choice((0, 0, 1)) for _ in range(16)] for _ in range(16)]
    leafy = [[False] * 16 for _ in range(16)]
    for _ in range(36):
        x, y = rng.randrange(16), rng.randrange(16)
        dx, dy = rng.choice(((1, 1), (1, -1), (-1, 1), (-1, -1), (1, 0), (0, -1)))
        base = rng.choice((1, 2, 2, 3))
        for i in range(rng.choice((2, 3, 3))):
            px, py = (x + dx * i) % 16, (y + dy * i) % 16
            tone[py][px] = min(5, base + i + (1 if i and rng.random() < 0.3 else 0))
            leafy[py][px] = True
    return [[[0, 0, 0, 0] if not leafy[y][x] and rng.random() < 0.6 else _rgb(tone[y][x], tones) for x in range(16)]
            for y in range(16)]


FALLING = (
    ("...34", "..23.", ".22..", "12...", "....."),
    (".....", ".234.", "1223.", ".12..", "....."),
    ("..4..", ".33..", ".23..", "..2..", "..1.."),
)


def falling_leaves():
    """The twelve little pictures of a leaf on its way down."""
    out = []
    for n in range(12):
        rows = [list(r) for r in FALLING[n % 3]]
        for _ in range(n // 3):
            rows = [list(r) for r in zip(*rows[::-1])]
        shift = (0, 1, 0, -1)[n % 4]
        out.append([[[0, 0, 0, 0] if ch == "." else _rgb(max(1, min(5, int(ch) + shift))) for ch in row] for row in rows])
    return out


def write_pack(pack_dir):
    meta = {"texture": {"mipmap_strategy": "dark_cutout"}}
    variants = [(leaf_picture(tones, seed=11 + n), weight) for n, (tones, weight) in enumerate(GOLDS)]
    info = respack.cube_variants(pack_dir, GOLD_LEAVES, variants, name="gold_leaves", parent="minecraft:block/leaves",
                                 meta=meta)
    for n, pixels in enumerate(falling_leaves()):
        respack.texture(pack_dir, f"particle/pale_oak_{n}", pixels)
    return info + ", 12 falling leaf pictures"


# ---- rock ----------------------------------------------------------------------------------------
def _smooth(x, z, seed, cell):
    """Value noise in 0..1 that varies over about `cell` blocks."""
    gx, gz = x / cell, z / cell
    x0, z0 = math.floor(gx), math.floor(gz)
    fx, fz = gx - x0, gz - z0
    fx, fz = fx * fx * (3 - 2 * fx), fz * fz * (3 - 2 * fz)
    a, b = hash3(x0, 0, z0, seed), hash3(x0 + 1, 0, z0, seed)
    d, e = hash3(x0, 0, z0 + 1, seed), hash3(x0 + 1, 0, z0 + 1, seed)
    return (a * (1 - fx) + b * fx) * (1 - fz) + (d * (1 - fx) + e * fx) * fz


def isle(c, cx, cy, cz, r, depth, seed, relief=1.0, basin=None):
    """A floating rock with a grown-over top and a ragged underside.

    basin = (x, z, radius, heading in degrees, width): a pool whose water stands one below cy,
    with a notch through the rim towards `heading` (0 = +x, 90 = +z).
    Returns a terrain.Land for planting and building on it, with .low = lowest block per column.
    """
    land = terrain.Land()
    land.low = {}
    if basin:
        bx, bz, br, heading, width = basin
        ux, uz = math.cos(math.radians(heading)), math.sin(math.radians(heading))
    n = int(r * 1.5) + 4
    for x in range(math.floor(cx) - n, math.floor(cx) + n + 1):
        for z in range(math.floor(cz) - n, math.floor(cz) + n + 1):
            dx, dz = x + 0.5 - cx, z + 0.5 - cz
            e = 1.0 - math.hypot(dx, dz) / r - 0.5 * (_smooth(x, z, seed, 6.0) - 0.5) - 0.12 * (hash3(x, 1, z, seed) - 0.5)
            top = cy + int(round(relief * 2.2 * (_smooth(x, z, seed + 1, 7.0) - 0.35)))
            kind = "grass"
            wet = False
            if basin:
                db = math.hypot(x + 0.5 - bx, z + 0.5 - bz)
                along = (x + 0.5 - bx) * ux + (z + 0.5 - bz) * uz
                across = abs(-(x + 0.5 - bx) * uz + (z + 0.5 - bz) * ux)
                if db <= br:
                    e, top, kind, wet = max(e, 0.3), cy - 1, "water", True
                elif along > 0 and across < width / 2.0 and e > -0.05:
                    e, top, kind = max(e, 0.06), cy - 2, "built"       # the floor of the notch
                elif db <= br + 1.7 or (along > 0 and across < width / 2.0 + 1.3 and e > -0.05):
                    e, top, kind = max(e, 0.12), cy, "rock"            # the rim, and the banks of the notch
            if e <= 0:
                continue
            if kind == "grass" and e < 0.08:
                top -= 1
            reach = 2.0 + depth * e ** 0.75 * (0.7 + 0.6 * _smooth(x, z, seed + 2, 4.0))
            reach += 5.0 * max(0.0, _smooth(x, z, seed + 3, 2.6) - 0.62) / 0.38 * min(1.0, e * 4.0)
            bot = top - int(reach)
            for y in range(bot, top + 1):
                d = top - y
                t = (cy - y) / max(depth, 1.0)
                h = hash3(x, y, z, seed)
                if wet and d == 0:
                    state = site.WATER
                elif wet and d == 1:
                    state = BED(x, y, z)
                elif kind in ("rock", "built") and d <= 1:
                    state = RIM(x, y, z)
                elif d == 0:
                    state = "grass_block" if h < 0.86 else "moss_block"
                elif d <= 2 and e > 0.1 and kind == "grass":
                    state = "dirt" if h < 0.8 else "coarse_dirt"
                elif t < 0.4:
                    state = ROCK(x, y, z)
                elif t < 0.75:
                    state = "tuff" if h < 0.45 else "stone" if h < 0.8 else "andesite"
                else:
                    state = "deepslate" if h < 0.6 else "tuff" if h < 0.85 else "cobbled_deepslate"
                c.set(x, y, z, state)
            land.top[(x, z)] = top
            land.kind[(x, z)] = kind
            land.edge[(x, z)] = e
            land.low[(x, z)] = bot
    return land


def dress(c, land, seed, flowers=("oxeye_daisy", "poppy", "azure_bluet"), roots=0.0):
    """Grass, ferns, a few flowers and bushes on the green parts; vines off the rim; roots = share
    of the columns where roots come out of the rock underneath."""
    for (x, z), low in land.low.items():
        if roots and hash3(x, 10, z, seed) < roots and c.has(x, low, z) and not c.has(x, low - 1, z):
            c.set(x, low - 1, z, "hanging_roots")
    for (x, z), kind in land.kind.items():
        top = land.top[(x, z)]
        if c.has(x, top + 1, z):
            continue
        h = hash3(x, 6, z, seed)
        if kind == "grass":
            if h < 0.34:
                c.set(x, top + 1, z, "short_grass")
            elif h < 0.42:
                c.set(x, top + 1, z, "fern")
            elif h < 0.48:
                c.set(x, top + 1, z, flowers[int(hash3(x, 7, z, seed) * len(flowers))])
            elif h < 0.51 and land.edge[(x, z)] < 0.3:
                T.bush(c, x, top + 1, z, seed + x, T.leaf("azalea_leaves"))
        elif kind == "rock" and h < 0.22:
            c.set(x, top + 1, z, "moss_carpet")
    for (x, z), top in land.top.items():
        if land.kind[(x, z)] != "grass":
            continue   # nothing may hang where water comes over the edge
        for face, dx, dz in (("north", 0, 1), ("south", 0, -1), ("west", 1, 0), ("east", -1, 0)):
            n = (x + dx, z + dz)
            if n in land.top or hash3(n[0], 8, n[1], seed) > 0.26:
                continue
            for i in range(1 + int(hash3(n[0], 9, n[1], seed) * 6)):
                if c.has(n[0], top - i, n[1]) or not c.has(x, top - i, z):
                    break
                c.set(n[0], top - i, n[1], f"vine[{face}=true]")


def skystone_under(c, land, kind, scale, seed):
    """The crystal that keeps a rock afloat: a cluster under its deepest part, with the light it gives."""
    def around(p):
        return sum(land.low.get((p[0] + dx, p[1] + dz), land.low[p] + 6) for dx in (-1, 0, 1) for dz in (-1, 0, 1))
    x, z = min(land.low, key=around)
    y = land.low[(x, z)]
    rng = random.Random(seed)
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            for dy in (0, 1):
                if c.has(x + dx, y + dy, z + dz) and hash3(x + dx, y + dy, z + dz, seed) < 0.7:
                    c.set(x + dx, y + dy, z + dz, "calcite")
    props.place(c, skystone.cluster_name(kind), x + 0.5, y + 0.05, z + 0.5, yaw=rng.uniform(0.0, 360.0), scale=scale,
                turns=(("z", rng.uniform(-10.0, 10.0)), ("x", rng.uniform(-10.0, 10.0))), brightness=15, view=6.0)
    if not c.has(x, y - 1, z):
        c.set(x, y - 1, z, "light[level=13]")


def flank(land, toward):
    """A point on the underside of an isle, a little in from the rim on the side facing `toward`
    (x, z): where a chain can take hold."""
    inner = [p for p in land.top if land.edge[p] >= 0.15]
    x, z = min(inner, key=lambda p: math.hypot(p[0] + 0.5 - toward[0], p[1] + 0.5 - toward[1]))
    return (x + 0.5, land.low[(x, z)] - 0.2, z + 0.5)


def small(c, x, y, z, r, depth, seed, tree=None):
    """One of the little rocks adrift around the island. tree = (kind, height) or None."""
    land = isle(c, x + 0.5, y, z + 0.5, r, depth, seed, relief=0.6)
    if tree:
        kind, height = tree
        ty = land.top.get((x, z), y) + 1
        if kind == "spruce":
            T.spruce(c, x, ty, z, height, seed + 5)
        else:
            T.broadleaf(c, x, ty, z, height, max(3, height // 2), seed + 5, log="birch_log",
                        leaves=T.leaf_mix("birch_leaves"), squash=0.7, lift=(0.5, 1.0), clumps=0.85)
    dress(c, land, seed + 1)
    skystone_under(c, land, "c", 1.2 + 0.2 * r, seed + 2)
    return land


# ---- the lookout ---------------------------------------------------------------------------------
def golden_tree(c, land, x, z, seed, height=17, spread=10):
    """The old tree on the lookout: dark trunk on spreading roots, golden crown, lanterns hung in
    it, its leaves on the grass. (x, z) is the north-west column of its two-by-two trunk."""
    y = land.top[(x, z)] + 1
    before = set(c.b)
    T.broadleaf(c, x, y, z, height, spread, seed, log="dark_oak_log", leaves=T.leaf_mix(GOLD_LEAVES),
                squash=0.85, lift=(0.45, 0.95), thick=True, hang=0.12, clumps=1.3)
    crown = sorted(p for p in c.b if p not in before and c.name(*p) == GOLD_LEAVES)
    rng = random.Random(seed)
    # roots run out over the ground from the foot of the trunk and sink into it
    trunk = {(x, z), (x + 1, z), (x, z + 1), (x + 1, z + 1)}
    for k in range(6):
        ang = k * math.tau / 6 + rng.uniform(-0.35, 0.35)
        length = rng.uniform(3.2, 6.2)
        t = 1.2
        while t < length:
            p = (math.floor(x + 1.0 + t * math.cos(ang)), math.floor(z + 1.0 + t * math.sin(ang)))
            t += 0.5
            if p in trunk:
                continue
            if land.kind.get(p) not in ("grass", "root"):
                break
            gy = land.top[p]
            if t < 3.0:
                c.set(p[0], gy + 1, p[1], "dark_oak_wood")
            else:
                c.set(p[0], gy, p[1], "dark_oak_wood", keep=c.name(p[0], gy, p[1]) == "dark_oak_wood")
            land.kind[p] = "root"
    rng.shuffle(crown)
    hung = []
    for px, py, pz in crown:
        if len(hung) >= 7:
            break
        d = math.hypot(px - x, pz - z)
        if not 2.5 <= d <= spread * 0.85 or any(c.has(px, py - i, pz) for i in (1, 2, 3)):
            continue
        if any(math.hypot(px - hx, pz - hz) < 3.5 for hx, hz in hung):
            continue
        c.set(px, py - 1, pz, "waxed_copper_chain[axis=y]")
        c.set(px, py - 2, pz, "lantern[hanging=true]")
        hung.append((px, pz))
    for (gx, gz), kind in land.kind.items():
        d = math.hypot(gx - x, gz - z)
        gy = land.top[(gx, gz)] + 1
        if kind == "grass" and d <= spread + 1 and hash3(gx, 3, gz, seed) < 0.6 * (1 - 0.7 * d / (spread + 1)):
            if not c.has(gx, gy, gz):
                amount = 1 + int(hash3(gx, 4, gz, seed) * 4)
                facing = ("north", "east", "south", "west")[int(hash3(gx, 5, gz, seed) * 4)]
                c.set(gx, gy, gz, f"leaf_litter[segment_amount={amount},facing={facing}]")


def rope_bridge(c, x0, x1, z, h0, h1, sag=1.2):
    """A hanging bridge two planks wide running along x, its walking surface at h0 at x0 and h1 at
    x1; z is the first of its two rows. Posts stand at x0 and x1; rope hand rails hang between them."""
    n = abs(x1 - x0)
    step = 1 if x1 > x0 else -1

    def surface(i):
        t = i / n
        return h0 + (h1 - h0) * t - sag * 4.0 * t * (1.0 - t)

    for i in range(1, n):
        x = x0 + step * i
        h = surface(i)
        base = math.floor(h + 1e-6)
        frac = h - base
        if frac < 0.25:
            y, kind = base - 1, "top"
        elif frac < 0.75:
            y, kind = base, "bottom"
        else:
            y, kind = base, "top"
        wood = "dark_oak_slab" if i % 4 == 0 else "spruce_slab"
        for dz in (0, 1):
            c.set(x, y, z + dz, f"{wood}[type={kind}]")
    for x, h in ((x0, h0), (x1, h1)):
        for pz in (z - 1, z + 2):
            c.set(x, int(h), pz, "dark_oak_log")
            c.set(x, int(h) + 1, pz, "dark_oak_fence")
            c.set(x, int(h) + 2, pz, "lantern[hanging=false]")
        for dz in (0, 1):
            c.clear(x, int(h), z + dz)
            c.clear(x, int(h) + 1, z + dz)
    pieces = max(4, n // 3)

    def rail(i, height):
        t = i / n
        return surface(i) + height - 0.3 * 4.0 * t * (1.0 - t)

    for side, edge in ((z - 0.5, z + 0.05), (z + 2.5, z + 1.95)):
        for height, thick in ((1.25, 1.6), (0.6, 1.2)):
            pts = [(x0 + step * (n * k / pieces) + 0.5, rail(n * k / pieces, height), side) for k in range(pieces + 1)]
            for a, b in zip(pts, pts[1:]):
                props.stretch(c, "rope", a, b, thick=thick, brightness=(15, 0))
        # hangers from the upper rail in to the edge of the deck
        for i in range(2, n - 1, 2):
            x = x0 + step * i + 0.5
            props.stretch(c, "rope", (x, rail(i, 1.25), side), (x, surface(i) - 0.2, edge), thick=0.9, brightness=(15, 0))


def lookout(c, cx, cy, cz, rows, seed=811):
    """The lookout east of the tower: the golden tree, a bench under it, skystone breaking the
    surface at the far end. rows = the four z rows the bridge from the west takes up with its
    posts. Returns its land; land.landing = (x, height of the ground) where the bridge arrives."""
    land = isle(c, cx, cy, cz, 11.5, 15.0, seed, relief=0.9)
    # a stone threshold at the western-most place where all four rows are firm ground
    x1 = min(x for (x, z) in land.top if all(land.edge.get((x, zz), 0.0) >= 0.1 for zz in rows))
    for x in (x1, x1 + 1):
        for z in rows:
            for y in range(cy - 1, land.top[(x, z)] + 3):
                if y <= cy:
                    c.set(x, y, z, RIM(x, y, z))
                else:
                    c.clear(x, y, z)
            land.top[(x, z)] = cy
            land.kind[(x, z)] = "built"
    land.landing = (x1, cy + 1)
    tx, tz = math.floor(cx) + 1, math.floor(cz) - 1
    golden_tree(c, land, tx, tz, seed + 1)
    # a bench looking out over the clouds
    bx, bz = math.floor(cx) + 6, math.floor(cz) + 1
    for k in range(3):
        p = (bx, bz + k)
        if p in land.top and not c.has(bx, land.top[p] + 1, bz + k):
            c.set(bx, land.top[p] + 1, bz + k, "spruce_stairs[facing=west,half=bottom]")
            land.kind[p] = "built"
    # skystone breaking the surface on the seaward tip
    tip = max((p for p in land.top if land.edge[p] > 0.14), key=lambda p: p[0] - abs(p[1] + 0.5 - cz) * 0.6)
    gy = land.top[tip]
    for dx, dz in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        p = (tip[0] + dx, tip[1] + dz)
        if p in land.top:
            c.set(p[0], land.top[p], p[1], "calcite" if (dx, dz) == (0, 0) or hash3(p[0], 1, p[1], seed) < 0.5 else "smooth_basalt")
            land.kind[p] = "rock"
    props.place(c, skystone.cluster_name("b", hanging=False), tip[0] + 0.5, gy + 0.9, tip[1] + 0.5, yaw=40.0,
                scale=2.2, brightness=15, view=6.0)
    land.kind[tip] = "built"
    c.set(tip[0], gy + 3, tip[1], "light[level=12]", keep=True)
    # a small telescope on the south rim, turned to where the water goes down
    spot = max((p for p in land.top if land.edge[p] > 0.22 and land.kind[p] == "grass" and p[0] < cx + 4),
               key=lambda p: p[1])
    props.place(c, "spyglass", spot[0] + 0.5, land.top[spot] + 1, spot[1] + 0.5, yaw=160.0)
    land.kind[spot] = "built"
    dress(c, land, seed + 2, flowers=("dandelion", "oxeye_daisy", "orange_tulip"), roots=0.14)
    skystone_under(c, land, "b", 2.6, seed + 3)
    return land


# ---- the waterfall -------------------------------------------------------------------------------
def _leaves_at(land, x, z, out, start):
    """Walk from (x, z) along `out` until the rock ends; the point just past it."""
    t = start
    while (math.floor(x + (t + 0.5) * out[0]), math.floor(z + (t + 0.5) * out[1])) in land.top:
        t += 0.5
    return (x + (t + 0.6) * out[0], z + (t + 0.6) * out[1])


def cascade(c, fall, out, seed=821):
    """Two basins under the waterfall. fall = (x, z) where the island's water comes down, out =
    unit vector away from the island. Returns ((x, z), unit vector) of the last fall, the one that
    reaches the clouds."""
    heading = math.degrees(math.atan2(out[1], out[0]))
    # upper basin: wide enough to catch every strand of the fall
    b1 = (fall[0] + 0.5, fall[1] + 0.5, 4.7, heading, 2.2)
    upper = isle(c, b1[0] - 0.8 * out[0], -30, b1[1] - 0.8 * out[1], 8.4, 11.0, seed, relief=0.5, basin=b1)
    dress(c, upper, seed + 1)
    p2 = _leaves_at(upper, b1[0], b1[1], out, b1[2])
    # lower basin, turned to one side so that the three falls do not stand in one line
    h2 = heading - 62.0
    o2 = (math.cos(math.radians(h2)), math.sin(math.radians(h2)))
    b2 = (p2[0] + 0.4 * out[0], p2[1] + 0.4 * out[1], 3.2, h2, 1.2)
    lower = isle(c, b2[0] - 0.5 * o2[0], -57, b2[1] - 0.5 * o2[1], 6.0, 8.0, seed + 5, relief=0.4, basin=b2)
    dress(c, lower, seed + 6)
    p3 = _leaves_at(lower, b2[0], b2[1], o2, b2[2])
    skystone_under(c, upper, "b", 2.4, seed + 8)
    skystone_under(c, lower, "c", 2.0, seed + 9)
    return p3, o2
