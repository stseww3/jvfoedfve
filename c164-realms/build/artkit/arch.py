"""Building helpers: round plans, curved shells from height functions, openings."""
import math

from . import blocks as B

DIRS = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
OPP = {"north": "south", "south": "north", "west": "east", "east": "west"}
LEFT = {"north": "west", "west": "south", "south": "east", "east": "north"}
RIGHT = {v: k for k, v in LEFT.items()}


def outward(dx, dz):
    """Cardinal direction closest to the vector (dx, dz)."""
    if abs(dx) >= abs(dz):
        return "east" if dx > 0 else "west"
    return "south" if dz > 0 else "north"


def dist(x, z, cx, cz):
    return math.hypot(x + 0.5 - cx, z + 0.5 - cz)


def disc(cx, cz, r):
    """Block columns whose centre lies within r of (cx, cz); the centre may sit on a block corner."""
    n = int(math.ceil(r)) + 1
    return [(x, z) for x in range(math.floor(cx) - n, math.floor(cx) + n + 1)
            for z in range(math.floor(cz) - n, math.floor(cz) + n + 1) if dist(x, z, cx, cz) <= r]


def ring(cx, cz, r_in, r_out):
    return [(x, z) for x, z in disc(cx, cz, r_out) if dist(x, z, cx, cz) > r_in]


def outline(cx, cz, r):
    """Edge-connected outline of a disc (good for fences and walls, which only join across faces)."""
    inside = set(disc(cx, cz, r))
    out = []
    for x, z in inside:
        if any((x + dx, z + dz) not in inside for dx in (-1, 0, 1) for dz in (-1, 0, 1)):
            out.append((x, z))
    return out


def shell(c, heights, base, y_min, thick=1, keep=False):
    """Lay a curved skin over columns.

    heights: {(x, z): surface height as a float}; base(x, y, z) -> full block name. Whole blocks
    are used up to the surface and the last step is a slab or a stair turned uphill, so domes and
    roofs read as curves instead of terraces. Returns {(x, z): y of the top cell}.
    """
    tops = {}
    for (x, z), h in heights.items():
        fl = math.floor(h)
        frac = h - fl
        if frac < 0.25:
            tops[(x, z)] = (fl - 1, "full")
        elif frac < 0.75:
            tops[(x, z)] = (fl, "half")
        else:
            tops[(x, z)] = (fl, "full")
    for (x, z), (ytop, kind) in tops.items():
        lows = [tops[(x + dx, z + dz)][0] if (x + dx, z + dz) in tops else y_min - 1 for dx, dz in DIRS.values()]
        ylow = max(y_min, min(ytop, min(lows) + 1) - (thick - 1))
        for y in range(ylow, ytop):
            c.set(x, y, z, base(x, y, z), keep)
        name = base(x, ytop, z)
        if ytop < y_min:
            continue
        if kind == "full":
            c.set(x, ytop, z, name, keep)
            continue
        h = heights[(x, z)]
        best, gain = None, 0.0
        for d, (dx, dz) in DIRS.items():
            n = heights.get((x + dx, z + dz))
            if n is not None and n - h > gain:
                best, gain = d, n - h
        if best and gain >= 0.45:
            c.set(x, ytop, z, B.stairs(name, best), keep)
        else:
            c.set(x, ytop, z, B.slab(name), keep)
    return {k: v[0] for k, v in tops.items()}


def fill_down(c, x, y, z, state, limit=12):
    """Extend a foundation from y downwards until it meets something."""
    n = 0
    while n < limit and not c.has(x, y, z):
        c.set(x, y, z, state)
        y -= 1
        n += 1
