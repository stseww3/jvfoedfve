"""Under the island: skystone crystal growing out of the rock, the mooring chains that broke when
the island rose, loose rock adrift beside the spires.

The crystal is what lights the underside: every cluster carries light blocks, so by night the glow
on the rock has a source that can be seen.
"""
import math
import random

from artkit.canvas import hash3

from . import props, skystone

ROCK = ("stone", "andesite", "cobblestone", "mossy_cobblestone", "tuff", "deepslate", "cobbled_deepslate")
SOIL = ("dirt", "coarse_dirt", "rooted_dirt", "grass_block", "moss_block")
SEED = 1640


def lows(c, land):
    """Lowest rock or soil block of every column of the island."""
    out = {}
    for (x, y, z), state in c.b.items():
        if (x, z) in land.top and y <= land.top[(x, z)] and state.partition("[")[0] in ROCK + SOIL:
            if y < out.get((x, z), 10 ** 6):
                out[(x, z)] = y
    return out


def _cluster(c, low, x, z, kind, scale, rng, light=14):
    """Hang a crystal cluster from the underside of column (x, z): a pale rind in the rock around
    its root, light below it. Returns False when there is no rock there."""
    xi, zi = math.floor(x), math.floor(z)
    y = low.get((xi, zi))
    if y is None:
        return False
    for dx in range(-3, 4):
        for dy in range(-1, 4):
            for dz in range(-3, 4):
                p = (xi + dx, y + dy, zi + dz)
                if c.name(*p) not in ROCK:
                    continue
                d = math.sqrt(dx * dx + dy * dy + dz * dz)
                h = hash3(p[0], p[1], p[2], SEED)
                if d < 1.7 or (d < 2.4 and h < 0.5):
                    c.set(*p, "calcite")
                elif d < 3.3 and h < 0.55:
                    c.set(*p, "smooth_basalt")
    props.place(c, skystone.cluster_name(kind), xi + 0.5, y + 0.05, zi + 0.5, yaw=rng.uniform(0.0, 360.0),
                scale=scale, turns=(("z", rng.uniform(-12.0, 12.0)), ("x", rng.uniform(-12.0, 12.0))),
                brightness=15, view=6.0)
    reach = int(skystone.SHARDS[kind][0][2] * scale / 16.0)
    for k, dy in enumerate(range(1, reach + 1, 4)):
        if not c.has(xi, y - dy, zi):
            c.set(xi, y - dy, zi, f"light[level={light if k == 0 else light - 2}]")
    return True


def crystals(c, land, low):
    """Big clusters on the shoulders of the great spire, one near the tip of each lesser spire,
    small ones scattered over the belly."""
    rng = random.Random(SEED)
    done = []

    def put(x, z, kind, scale):
        if any(math.hypot(x - px, z - pz) < 5.0 for px, pz in done):
            return False
        if _cluster(c, low, x, z, kind, scale, rng):
            done.append((x, z))
            return True
        return False

    gx, gz, _, gr = land.spires[0]
    for k in range(4):
        ang = math.radians(90.0 * k + 35.0 + rng.uniform(-15.0, 15.0))
        d = gr * rng.uniform(0.42, 0.62)
        put(gx + d * math.cos(ang), gz + d * math.sin(ang), "a" if k % 2 == 0 else "b", rng.uniform(3.2, 4.0))
    for x, z, h, r in land.spires[1:]:
        ang, d = rng.uniform(0.0, math.tau), r * rng.uniform(0.25, 0.45)
        put(x + d * math.cos(ang), z + d * math.sin(ang), "b" if h > 20 else "c", rng.uniform(2.4, 3.2))
    cells = sorted(p for p, e in land.edge.items() if e > 0.22)
    small = 0
    while small < 8 and cells:
        x, z = cells[rng.randrange(len(cells))]
        if put(x + 0.5, z + 0.5, "c", rng.uniform(1.6, 2.4)):
            small += 1
    return done


def chunk(c, cx, cy, cz, r, depth, seed, green=True):
    """A loose rock adrift: flat on top, tapering to a point below. green: True = grass and moss on
    top, "moss" = some moss only (nothing else grows in the shade of the island), False = bare."""
    cells = []
    for x in range(math.floor(cx - r) - 1, math.ceil(cx + r) + 2):
        for z in range(math.floor(cz - r) - 1, math.ceil(cz + r) + 2):
            dn = math.hypot(x + 0.5 - cx, z + 0.5 - cz) / r + 0.3 * (hash3(x, 1, z, seed) - 0.5)
            if dn >= 1.0:
                continue
            top = cy + (1 if dn < 0.45 and hash3(x // 2, 2, z // 2, seed) < 0.5 else 0)
            reach = max(1, int(round(depth * (1.0 - dn) ** 0.85 * (0.7 + 0.6 * hash3(x, 3, z, seed)))))
            for y in range(top - reach + 1, top + 1):
                cells.append((x, y, z, top))
    if any(c.has(x, y, z) for x, y, z, _ in cells):
        return False
    for x, y, z, top in cells:
        t = (cy - y) / max(depth, 1.0)
        h = hash3(x, y, z, seed)
        if y == top and green is True and h < 0.6:
            state = "moss_block" if h < 0.35 else "grass_block"
        elif y == top and green == "moss" and h < 0.3:
            state = "moss_block"
        elif t < 0.3:
            state = "stone" if h < 0.5 else "andesite" if h < 0.8 else "cobblestone"
        elif t < 0.65:
            state = "tuff" if h < 0.5 else "stone" if h < 0.75 else "deepslate"
        else:
            state = "deepslate" if h < 0.7 else "cobbled_deepslate"
        c.set(x, y, z, state)
    return True


def debris(c, land, low):
    """Loose rocks beside the spires and below the rim."""
    rng = random.Random(SEED + 1)
    gx, gz, _, gr = land.spires[0]
    placed = []
    for _ in range(400):
        if len(placed) >= 14:
            break
        ang, d = rng.uniform(0.0, math.tau), rng.uniform(gr * 0.7, 46.0)
        x, z = gx + d * math.cos(ang) * 1.15, gz + d * math.sin(ang) * 0.9
        col = low.get((math.floor(x), math.floor(z)))
        under = col if col is not None else -6
        y = int(under - rng.uniform(7.0, 26.0))
        r = rng.uniform(1.4, 3.6)
        if any(math.dist((x, y, z), p) < 9.0 for p in placed):
            continue
        green = True if col is None else "moss" if rng.random() < 0.5 else False
        if chunk(c, x, y, z, r, r * rng.uniform(1.6, 2.8), rng.randrange(10 ** 6), green=green):
            placed.append((x, y, z))
            # below the island no daylight reaches it
            if col is not None and not c.has(math.floor(x), y + 3, math.floor(z)):
                c.set(math.floor(x), y + 3, math.floor(z), "light[level=11]")
    return placed


def broken_chains(c, land, low):
    """Mooring chains that tore when the island rose: they hang from the belly, one still holds
    the stone it was let into."""
    rng = random.Random(SEED + 2)
    out = []
    for x, z, length, stone in ((-24, 20, 26.0, True), (33, 9, 17.0, False), (-36, -8, 21.0, False), (6, 27, 13.0, False)):
        y = low.get((x, z))
        if y is None:
            continue
        for dx, dz in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            if c.name(x + dx, y, z + dz) in ROCK + SOIL:
                c.set(x + dx, y, z + dz, "polished_deepslate" if (dx, dz) == (0, 0) else "deepslate_bricks")
        a = (x + 0.5, y - 0.1, z + 0.5)
        b = (x + 0.5 + rng.uniform(-0.6, 0.6), y - length, z + 0.5 + rng.uniform(-0.6, 0.6))
        props.chain(c, a, b, brightness=(13, 0), view=6.0)
        if stone:
            chunk(c, b[0], int(b[1]) - 1, b[2], 2.3, 4.5, 77, green=False)
            c.set(math.floor(b[0]), int(b[1]) + 2, math.floor(b[2]) + 1, "light[level=10]", keep=True)
        out.append((a, b))
    return out


def rim_near(land, x, z):
    """Middle of the island column closest to (x, z): a point on the rim for anything outside."""
    rx, rz = min(land.top, key=lambda p: math.hypot(p[0] + 0.5 - x, p[1] + 0.5 - z))
    return (rx + 0.5, rz + 0.5)


def tether(c, land, low, to, sag=4.0):
    """A chain from the underside of the island, a little in from the rim, to the point `to`
    (x, y, z) on a rock adrift beside it."""
    rx, rz = rim_near(land, to[0], to[2])
    d = math.hypot(to[0] - rx, to[2] - rz)
    ux, uz = (rx - to[0]) / d, (rz - to[2]) / d
    sx, sz = math.floor(rx + 2.5 * ux), math.floor(rz + 2.5 * uz)
    y = low.get((sx, sz), land.top[(math.floor(rx), math.floor(rz))] - 3)
    return props.chain(c, (sx + 0.5, y - 0.2, sz + 0.5), to, sag=sag, brightness=(14, 0), view=6.0)


def dress(c, land):
    low = lows(c, land)
    crystals(c, land, low)
    broken_chains(c, land, low)
    debris(c, land, low)
    return low
