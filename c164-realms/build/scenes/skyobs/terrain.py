"""Floating island: outline, top relief, underside and rock/soil materials."""
from collections import deque

import numpy as np

from artkit import noise as N

SEED = 164
X0, X1 = -70, 70
Z0, Z1 = -58, 58
Y0, Y1 = -78, 14
AX, AZ = 52.0, 40.0
KNOLL = (20.0, -12.0)
KNOLL_H = 10

ROCK = ["stone", "andesite", "cobblestone", "mossy_cobblestone", "tuff", "deepslate", "cobbled_deepslate"]
STONE, ANDESITE, COBBLE, MOSSY, TUFF, DEEP, CDEEP = range(7)


class Land:
    """Result of the terrain pass: per-column top height and surface kind."""

    def __init__(self):
        self.top = {}      # (x, z) -> y of the highest terrain block
        self.kind = {}     # (x, z) -> "grass" | "moss" | "rock" | "path" | "water" | "built"
        self.edge = {}     # (x, z) -> 0 at the rim .. 1 in the middle
        self.spires = []   # (x, z, depth, radius) of the spires hanging from the underside

    def y(self, x, z):
        return self.top.get((x, z))


def _pads(T, Xg, Zg, pads):
    """Blend the relief towards flat pads: (x0, z0, x1, z1, height, margin)."""
    for x0, z0, x1, z1, h, margin in pads:
        dx = np.maximum(np.maximum(x0 - Xg, Xg - x1), 0)
        dz = np.maximum(np.maximum(z0 - Zg, Zg - z1), 0)
        w = 1 - N.smoothstep(0, margin, np.hypot(dx, dz))
        T = T * (1 - w) + h * w
    return T


GREAT_SPIRE = (14.0, -8.0, 52.0, 16.0)   # x, z, how far it hangs below the belly, radius at its root


def _spires(Xg, Zg, e):
    """Extra depth of the hanging spires and their plan [(x, z, depth, radius)]."""
    rng = np.random.default_rng(SEED + 40)
    plan = [GREAT_SPIRE]
    for _ in range(600):
        if len(plan) >= 10:
            break
        x, z = rng.uniform(X0 + 10, X1 - 10), rng.uniform(Z0 + 8, Z1 - 8)
        ei = float(e[int(round(x)) - X0, int(round(z)) - Z0])
        r = rng.uniform(5.5, 9.5)
        if ei < 0.2 or any(np.hypot(x - px, z - pz) < 0.8 * (r + pr) for px, pz, _, pr in plan):
            continue
        plan.append((x, z, rng.uniform(12.0, 34.0) * (0.55 + 0.9 * ei), r))
    out = np.zeros(Xg.shape)
    for i, (x, z, h, r) in enumerate(plan):
        ang = np.arctan2(Zg - z, Xg - x)
        rr = r * (1 + 0.28 * N.perlin2(np.cos(ang) * 1.4 + 0.37 * x, np.sin(ang) * 1.4 + 0.41 * z, SEED + 41 + i))
        t = np.clip(1 - np.hypot(Xg - x, Zg - z) / rr, 0, 1)
        out = np.maximum(out, h * t ** 1.45)
    return out, plan


def _teeth(Xg, Zg, cell=6):
    """Small stalactites all over the underside: one per jittered grid cell, some cells empty."""
    rng = np.random.default_rng(SEED + 42)
    out = np.zeros(Xg.shape)
    for gx in range(X0, X1, cell):
        for gz in range(Z0, Z1, cell):
            x, z = gx + rng.uniform(0, cell), gz + rng.uniform(0, cell)
            h, r = rng.uniform(3.0, 11.0), rng.uniform(1.6, 3.3)
            if rng.random() < 0.4:
                continue
            i0, i1 = max(0, int(x - r) - 1 - X0), min(Xg.shape[0], int(x + r) + 2 - X0)
            k0, k1 = max(0, int(z - r) - 1 - Z0), min(Xg.shape[1], int(z + r) + 2 - Z0)
            t = np.clip(1 - np.hypot(Xg[i0:i1, k0:k1] - x, Zg[i0:i1, k0:k1] - z) / r, 0, 1)
            out[i0:i1, k0:k1] = np.maximum(out[i0:i1, k0:k1], h * t ** 1.2)
    return out


def _largest_component(solid):
    """Drop loose specks: keep only the biggest 6-connected body."""
    seen = np.zeros(solid.shape, dtype=bool)
    best = None
    nx, ny, nz = solid.shape
    for start in zip(*np.nonzero(solid)):
        if seen[start]:
            continue
        comp = [start]
        seen[start] = True
        q = deque([start])
        while q:
            x, y, z = q.popleft()
            for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                a, b, c = x + dx, y + dy, z + dz
                if 0 <= a < nx and 0 <= b < ny and 0 <= c < nz and solid[a, b, c] and not seen[a, b, c]:
                    seen[a, b, c] = True
                    comp.append((a, b, c))
                    q.append((a, b, c))
        if best is None or len(comp) > len(best):
            best = comp
    out = np.zeros(solid.shape, dtype=bool)
    idx = np.array(best)
    out[idx[:, 0], idx[:, 1], idx[:, 2]] = True
    return out


def build(c, pads=()):
    xs = np.arange(X0, X1 + 1)
    zs = np.arange(Z0, Z1 + 1)
    ys = np.arange(Y0, Y1 + 1)
    Xg, Zg = np.meshgrid(xs, zs, indexing="ij")

    # --- outline: 0 at the rim, towards 1 in the middle --------------------------------------
    th = np.arctan2(Zg / AZ, Xg / AX)
    r = np.hypot(Xg / AX, Zg / AZ)
    rim = (1 + 0.20 * N.perlin2(np.cos(th) * 1.3 + 5.1, np.sin(th) * 1.3 + 2.7, SEED)
           + 0.07 * N.perlin2(np.cos(th) * 3.4 + 1.0, np.sin(th) * 3.4 + 9.0, SEED + 1))
    e = 1 - r / rim + 0.02 * N.perlin2(Xg * 0.16, Zg * 0.16, SEED + 20)

    # --- top relief ---------------------------------------------------------------------------
    base = 1.0 + 1.7 * N.fbm2(Xg * 0.032, Zg * 0.032, SEED + 2, octaves=3)
    dk = np.hypot(Xg - KNOLL[0], Zg - KNOLL[1]) + 2.0 * N.perlin2(Xg * 0.09, Zg * 0.09, SEED + 3)
    k = 1 - N.smoothstep(11.5, 17.5, dk)
    knoll = KNOLL_H * k
    knoll = 0.4 * knoll + 0.6 * np.round(knoll / 2.5) * 2.5
    T = base * (1 - k) + knoll
    T = _pads(T, Xg, Zg, pads)
    T = T - 3.2 * (1 - N.smoothstep(0.0, 0.11, e))

    # --- underside: a shallow belly from which spires hang, a great one under the knoll -------
    core = N.smoothstep(0.0, 0.92, e)
    depth = 3.5 + 21 * core ** 1.15 * (0.8 + 0.4 * N.perlin2(Xg * 0.045, Zg * 0.045, SEED + 5))
    ridge = 1 - np.abs(N.perlin2(Xg * 0.085, Zg * 0.085, SEED + 6))
    depth += 7 * N.smoothstep(0.70, 0.98, ridge) * core
    spires, plan = _spires(Xg, Zg, e)
    depth += spires + _teeth(Xg, Zg) * N.smoothstep(0.08, 0.35, core)
    bot = -depth

    X3, Y3, Z3 = np.meshgrid(xs, ys, zs, indexing="ij")
    T3 = T[:, None, :]
    below = T3 - Y3
    wobble = N.perlin3(X3 * 0.07, Y3 * 0.045, Z3 * 0.07, SEED + 7)
    lower = np.minimum(bot[:, None, :] + 5.0 * wobble, T3 - 2.2)
    e3 = e[:, None, :] + 0.05 * N.perlin3(X3 * 0.06, Y3 * 0.09, Z3 * 0.06, SEED + 8) * np.clip(below / 8.0, 0, 1)
    solid = (e3 > 0) & (Y3 <= T3) & (Y3 >= lower)
    solid = _largest_component(solid)

    # --- materials ----------------------------------------------------------------------------
    nx, ny, nz = solid.shape
    has = solid.any(axis=1)
    top_i = ny - 1 - np.argmax(solid[:, ::-1, :], axis=1)
    top_y = np.where(has, ys[top_i], -9999)

    rng = np.random.default_rng(SEED + 9)
    h1 = rng.random(solid.shape)
    h2 = rng.random(solid.shape)
    s = -Y3 + 3.0 * N.perlin2(Xg * 0.05, Zg * 0.05, SEED + 10)[:, None, :] + 6.0 * (h1 - 0.5)
    n1 = N.perlin3(X3 * 0.11, Y3 * 0.17, Z3 * 0.11, SEED + 11)
    rock = np.full(solid.shape, STONE, dtype=np.int8)
    upper = s < 10
    rock[upper & (n1 > 0.26)] = ANDESITE
    rock[upper & (n1 < -0.30)] = COBBLE
    rock[upper & (h2 < 0.05)] = MOSSY
    mid = (s >= 10) & (s < 25)
    rock[mid & (n1 > 0.22)] = TUFF
    rock[mid & (n1 < -0.30)] = ANDESITE
    rock[mid & (h2 < 0.07)] = COBBLE
    rock[mid & (h2 > 0.94)] = DEEP
    low = (s >= 25) & (s < 39)
    rock[low] = DEEP
    rock[low & (n1 > 0.05)] = TUFF
    rock[low & (h2 < 0.10)] = CDEEP
    rock[low & (h2 > 0.93)] = STONE
    deep = s >= 39
    rock[deep] = DEEP
    rock[deep & (n1 > 0.28)] = CDEEP
    rock[deep & (h2 < 0.06)] = TUFF
    seam = np.mod(Y3 + 2.5 * N.perlin2(Xg * 0.04, Zg * 0.04, SEED + 12)[:, None, :], 8.0) < 1.15
    rock[seam & upper] = ANDESITE
    rock[seam & mid] = TUFF

    pad = np.pad(solid, 1, constant_values=False)
    side_open = ~(pad[2:, 1:-1, 1:-1] & pad[:-2, 1:-1, 1:-1] & pad[1:-1, 1:-1, 2:] & pad[1:-1, 1:-1, :-2])
    under_open = ~pad[1:-1, :-2, 1:-1]

    # steepness of the top surface
    tp = np.pad(top_y.astype(float), 1, constant_values=-9999)
    nb = np.stack([tp[2:, 1:-1], tp[:-2, 1:-1], tp[1:-1, 2:], tp[1:-1, :-2]])
    nb = np.where(nb < -9000, top_y[None], nb)
    drop = top_y[None] - nb
    steep = (drop.max(axis=0) >= 2) | (drop.min(axis=0) <= -3)

    moss_n = N.fbm2(Xg * 0.07, Zg * 0.07, SEED + 13, octaves=3)
    grass_n = N.fbm2(Xg * 0.11, Zg * 0.11, SEED + 14, octaves=2)
    hcol = rng.random(top_y.shape)

    land = Land()
    land.spires = plan
    for i in range(nx):
        x = int(xs[i])
        for kz in range(nz):
            if not has[i, kz]:
                continue
            z = int(zs[kz])
            ty = int(top_y[i, kz])
            on_knoll = k[i, kz] > 0.04
            rocky = steep[i, kz] or (on_knoll and (grass_n[i, kz] < 0.12 or k[i, kz] < 0.97))
            if rocky and not steep[i, kz] and hcol[i, kz] < 0.25:
                rocky = False
            land.top[(x, z)] = ty
            land.edge[(x, z)] = float(e[i, kz])
            col = solid[i, :, kz]
            for j in np.nonzero(col)[0]:
                y = int(ys[j])
                d = ty - y
                rk = ROCK[rock[i, j, kz]]
                if d == 0:
                    if rocky:
                        state = rk
                        land.kind[(x, z)] = "rock"
                    elif moss_n[i, kz] > 0.36 and hcol[i, kz] < 0.8:
                        state = "moss_block"
                        land.kind[(x, z)] = "moss"
                    else:
                        state = "grass_block"
                        land.kind[(x, z)] = "grass"
                elif d <= 3 and not rocky:
                    if under_open[i, j, kz] and d >= 2:
                        state = rk
                    elif side_open[i, j, kz] and d >= 2:
                        state = rk if h2[i, j, kz] < 0.7 else "coarse_dirt"
                    elif side_open[i, j, kz]:
                        state = "dirt" if h2[i, j, kz] < 0.6 else ("coarse_dirt" if h2[i, j, kz] < 0.85 else "rooted_dirt")
                    else:
                        state = "dirt"
                else:
                    state = rk
                c.b[(x, y, z)] = state
    return land
