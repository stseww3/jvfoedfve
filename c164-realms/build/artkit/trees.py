"""Hand-shaped trees: trunks that lean and fork, crowns made of several clumps."""
import math
import random

from .canvas import hash3


def leaf(name):
    return f"{name}[persistent=true]"


def leaf_mix(main, alt=None, share=0.0, seed=7):
    """Leaf picker: mostly `main`, with `share` of `alt` sprinkled in."""
    a, b = leaf(main), leaf(alt) if alt else None

    def pick(x, y, z):
        if b and hash3(x, y, z, seed) < share:
            return b
        return a
    return pick


def blob(c, cx, cy, cz, rx, ry, rz, leaves, seed, squash=0.6, core=0.55):
    """Leaf clump: an ellipsoid with a ragged skin, flatter underneath than on top."""
    for x in range(math.floor(cx - rx), math.ceil(cx + rx) + 1):
        for y in range(math.floor(cy - ry), math.ceil(cy + ry) + 1):
            for z in range(math.floor(cz - rz), math.ceil(cz + rz) + 1):
                dy = (y - cy) / (ry if y >= cy else ry * squash)
                d = ((x - cx) / rx) ** 2 + dy * dy + ((z - cz) / rz) ** 2
                if d > 1.0:
                    continue
                if d > core and hash3(x, y, z, seed) > (1.0 - d) / (1.0 - core):
                    continue
                c.set(x, y, z, leaves, keep=True)


def _roots(c, x, y, z, wood, rng, n, ground=None):
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    rng.shuffle(dirs)
    for dx, dz in dirs[:n]:
        yy = y
        c.set(x + dx, yy, z + dz, wood, keep=True)
        for _ in range(3):
            yy -= 1
            if c.has(x + dx, yy, z + dz):
                break
            c.set(x + dx, yy, z + dz, wood)


def spruce(c, x, y, z, height, seed, log="spruce_log", leaves="spruce_leaves", width=1.0):
    """Conifer with stacked skirts of branches. (x, y, z) is the lowest trunk block."""
    rng = random.Random(seed)
    L = leaf(leaves)
    wood = log.replace("_log", "_wood")
    bare = max(2, round(height * 0.17))
    top = y + height
    for yy in range(y, top - 3):
        c.set(x, yy, z, log)
    if height >= 15:
        _roots(c, x, y, z, wood, rng, 3 if height >= 21 else 2)
    for yy in range(top - 3, top + 1):
        c.set(x, yy, z, L)
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        c.set(x + dx, top - 2, z + dz, L, keep=True)
        c.set(x + dx, top - 3, z + dz, L, keep=True)
    span = height - bare - 1
    rmax = (1.25 + 0.185 * span) * width
    pattern = (0.5, 0.74, 1.0)
    for i in range(1, span + 1):
        yy = top - 1 - i
        t = i / span
        env = 0.95 + (rmax - 0.95) * t ** 0.8
        phase = pattern[(i - 1) % 3]
        r = env * phase
        ri = math.ceil(r + 0.5)
        for dx in range(-ri, ri + 1):
            for dz in range(-ri, ri + 1):
                d = math.hypot(dx, dz)
                if d == 0:
                    continue
                if d <= r - 0.2 + 0.55 * hash3(x + dx, yy, z + dz, seed):
                    c.set(x + dx, yy, z + dz, L, keep=True)
                    if phase == 1.0 and d > r - 1.3 and hash3(x + dx, yy - 1, z + dz, seed + 1) < 0.4:
                        c.set(x + dx, yy - 1, z + dz, L, keep=True)


def broadleaf(c, x, y, z, height, spread, seed, log="oak_log", leaves=None, squash=0.6, lift=(0.35, 0.8),
              thick=False, hang=0.0, clumps=1.0):
    """Deciduous tree: wandering trunk, a few rising boughs and a crown built from clumps."""
    rng = random.Random(seed)
    wood = log.replace("_log", "_wood")
    leaves = leaves or leaf_mix("oak_leaves")
    trunk_h = max(3, round(height * 0.5))
    tx, tz = x, z
    spine = []
    for i in range(trunk_h):
        if i >= 2 and rng.random() < 0.25:
            dx, dz = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
            if abs(tx + dx - x) <= 2 and abs(tz + dz - z) <= 2:
                c.set(tx + dx, y + i - 1, tz + dz, wood)
                tx, tz = tx + dx, tz + dz
        c.set(tx, y + i, tz, log)
        if thick and i < trunk_h * 0.6:
            for dx, dz in ((1, 0), (0, 1), (1, 1)):
                c.set(tx + dx, y + i, tz + dz, log)
        spine.append((tx, y + i, tz))
    _roots(c, x, y, z, wood, rng, 3 if height >= 9 else 2)
    if thick:
        _roots(c, x + 1, y, z + 1, wood, rng, 3)

    n = 3 if height < 9 else rng.randint(4, 5) if height < 14 else rng.randint(5, 7)
    a0 = rng.uniform(0, math.tau)
    ends = []
    for i in range(n):
        a = a0 + i * math.tau / n + rng.uniform(-0.35, 0.35)
        sx, sy, sz = spine[max(1, trunk_h - 1 - rng.randint(0, max(1, trunk_h // 3)))]
        length = spread * rng.uniform(0.55, 1.0)
        rise = length * rng.uniform(*lift)
        ex, ey, ez = sx + math.cos(a) * length, sy + rise, sz + math.sin(a) * length
        mx = (sx + ex) / 2 + rng.uniform(-0.8, 0.8)
        my = (sy + ey) / 2 + rng.uniform(0.0, 1.2)
        mz = (sz + ez) / 2 + rng.uniform(-0.8, 0.8)
        c.line((sx, sy, sz), (round(mx), round(my), round(mz)), wood, keep=True)
        c.line((round(mx), round(my), round(mz)), (round(ex), round(ey), round(ez)), wood, keep=True)
        ends.append((ex, ey, ez, length))
        if length > spread * 0.75:
            ends.append((mx, my + 0.5, mz, length * 0.6))

    crown_y = y + height - 2.6
    for yy in range(y + trunk_h, round(crown_y)):
        c.set(tx, yy, tz, log, keep=True)
    r_top = max(2.4, min(4.4, spread * 0.5)) * clumps
    blob(c, tx, crown_y, tz, r_top, r_top * 0.8, r_top, leaves, seed + 11, squash)
    for j, (ex, ey, ez, length) in enumerate(ends):
        r = rng.uniform(2.3, 3.4) * clumps * (0.85 + 0.25 * length / spread)
        blob(c, ex, ey + 0.8, ez, r, r * 0.72, r, leaves, seed + 20 + j, squash)

    if hang > 0:
        for (bx, by, bz), s in list(c.b.items()):
            if abs(bx - x) > spread + 6 or abs(bz - z) > spread + 6 or by < y + 2:
                continue
            if "leaves" in s and not c.has(bx, by - 1, bz) and hash3(bx, by, bz, seed + 3) < hang:
                c.set(bx, by - 1, bz, leaves, keep=True)
                if hash3(bx, by, bz, seed + 4) < 0.4:
                    c.set(bx, by - 2, bz, leaves, keep=True)


def bush(c, x, y, z, seed, leaves, size=1):
    """Low shrub made of a few leaf blocks; (x, y, z) is the first block above ground."""
    c.set(x, y, z, leaves, keep=True)
    for i, (dx, dz) in enumerate(((1, 0), (-1, 0), (0, 1), (0, -1))):
        if hash3(x + dx, y, z + dz, seed + i) < 0.28 + 0.2 * size and c.has(x + dx, y - 1, z + dz):
            c.set(x + dx, y, z + dz, leaves, keep=True)
    if size >= 2:
        blob(c, x, y + 0.4, z, 1.7 + 0.5 * (size - 2), 1.4, 1.7 + 0.5 * (size - 2), leaves, seed + 9, squash=1.0)
    elif hash3(x, y + 1, z, seed) < 0.35:
        c.set(x, y + 1, z, leaves, keep=True)
