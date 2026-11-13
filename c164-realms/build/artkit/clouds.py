"""Clouds made of blocks: a sea of cumulus tops to float an island over, and single towering clouds.

Shapes are unions of squashed spheres with a flat base, which is what gives cumulus its look: round
puffs piled on a level underside. They are modelled as one solid volume (`Field`); only its skin is
written, so even a wide sea stays cheap.

The skin is shaded here, not by the game. Stepped surfaces of one white block show a contour line on
every step, because the engine lights the top of a block brighter than its sides. So the resource
pack repaints five look-alike blocks as flat cloud tones without that face shading (`write_pack`),
and `Field.write` picks the tone per block from how far the surface faces up and how exposed it is.
"""
import math

import numpy as np

from . import blocks as B
from . import noise as N
from . import respack

# bright to shadow
TONES = ("dead_tube_coral_block", "dead_brain_coral_block", "dead_bubble_coral_block",
         "dead_fire_coral_block", "dead_horn_coral_block")
COLOURS = ("#ffffff", "#f1f6fc", "#dde7f5", "#c5d4ec", "#a9bcdc")


def _hash3(x, y, z, seed):
    h = (x * 374761393 + y * 668265263 + z * 2147483647 + int(seed) * 1274126177) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF) / float(1 << 24)


def _box(a, r, axis):
    """Mean over 2r+1 cells along one axis (zero outside the array)."""
    n = a.shape[axis]
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    acc = np.cumsum(np.pad(a, pad), axis=axis, dtype=np.float32)
    hi = np.take(acc, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(acc, np.arange(0, n), axis=axis)
    hi -= lo
    hi /= float(2 * r + 1)
    return hi


def _blur(a, r, passes=2):
    for _ in range(passes):
        for axis in range(a.ndim):
            a = _box(a, r, axis)
    return a


def _stamp(top, px, pz, cy, rad, squash):
    """Raise the height field `top` to a squashed hemisphere centred on (px, pz)."""
    nx, nz = top.shape
    x0, x1 = max(0, int(math.floor(px - rad))), min(nx - 1, int(math.ceil(px + rad)))
    z0, z1 = max(0, int(math.floor(pz - rad))), min(nz - 1, int(math.ceil(pz + rad)))
    if x0 > x1 or z0 > z1:
        return
    xs = np.arange(x0, x1 + 1)[:, None] + 0.5 - px
    zs = np.arange(z0, z1 + 1)[None, :] + 0.5 - pz
    d2 = xs * xs + zs * zs
    inside = d2 < rad * rad
    h = cy + squash * np.sqrt(np.maximum(rad * rad - d2, 0.0))
    view = top[x0:x1 + 1, z0:z1 + 1]
    view[inside] = np.maximum(view[inside], h[inside])


class Field:
    """A box of sky, x0..x1 / y0..y1 / z0..z1, in which clouds are piled up before they are written."""

    def __init__(self, x0, y0, z0, x1, y1, z1):
        self.lo = (x0, y0, z0)
        self.solid = np.zeros((x1 - x0 + 1, y1 - y0 + 1, z1 - z0 + 1), dtype=bool)

    def sea(self, base_y, seed=1, cover=0.5, scale=90.0, cell=11, radius=(5.0, 12.0), lift=7.0, squash=0.7,
            keep_out=None):
        """Lay a field of cumulus over the whole box with its flat underside near base_y.

        cover     share of the area under cloud (roughly)
        scale     size of the cloud banks in blocks
        cell      spacing of the big puffs; radius = their size at the edge and in the core of a bank
        lift      how much higher the puffs sit in the core of a bank
        keep_out  optional function (x, z) -> 0..1 that thins the field, e.g. under a build; columns
                  where it reaches 1 stay empty whatever the puffs around them do
        """
        x0, y0, z0 = self.lo
        nx, ny, nz = self.solid.shape
        X, Z = np.meshgrid(np.arange(nx) + x0, np.arange(nz) + z0, indexing="ij")
        field = (N.fbm2(X / scale, Z / scale, seed, octaves=3)
                 + 0.35 * N.fbm2(X / (scale * 0.33), Z / (scale * 0.33), seed + 7, octaves=2))
        thr = float(np.quantile(field, 1.0 - cover))
        dens = N.smoothstep(thr - 0.02, thr + 0.45, field)
        barred = np.zeros((nx, nz), dtype=bool)
        if keep_out is not None:
            k = np.clip(keep_out(X, Z), 0.0, 1.0)
            dens = dens * (1.0 - k)
            barred = k >= 0.999
        rng = np.random.default_rng(seed)
        top = np.full((nx, nz), -1e9)

        for gx in range(0, nx, cell):
            for gz in range(0, nz, cell):
                px, pz = gx + rng.uniform(0, cell), gz + rng.uniform(0, cell)
                ix, iz = min(nx - 1, int(px)), min(nz - 1, int(pz))
                d = dens[ix, iz]
                if d < 0.04:
                    continue
                rad = (radius[0] + (radius[1] - radius[0]) * d) * rng.uniform(0.75, 1.25)
                cy = base_y + lift * d * rng.uniform(0.55, 1.1) - 0.25 * rad
                _stamp(top, px, pz, cy, rad, squash)
        # a second, finer layer of puffs riding on the first
        fine = max(4, cell // 2)
        for gx in range(0, nx, fine):
            for gz in range(0, nz, fine):
                px, pz = gx + rng.uniform(0, fine), gz + rng.uniform(0, fine)
                ix, iz = min(nx - 1, int(px)), min(nz - 1, int(pz))
                if top[ix, iz] < -1e8 or rng.uniform() < 0.35:
                    continue
                rad = rng.uniform(2.2, 4.4)
                _stamp(top, px, pz, top[ix, iz] - 0.55 * rad, rad, 0.85)

        has = (top > -1e8) & ~barred
        bot = np.where(has, np.floor(base_y - 0.5 - 1.6 * dens), 0).astype(int) - y0
        tp = np.where(has, np.floor(top), -10**6).astype(int) - y0
        has &= tp >= bot
        if not has.any():
            return
        ya, yb = max(0, int(bot[has].min())), min(ny - 1, int(tp[has].max()))
        ys = np.arange(ya, yb + 1)[None, :, None]
        self.solid[:, ya:yb + 1, :] |= has[:, None, :] & (ys >= bot[:, None, :]) & (ys <= tp[:, None, :])

    def cumulus(self, cx, cy, cz, length, width, height, seed=1, heading=0.0, puffs=None):
        """One towering cloud with a flat base at cy, its long side along `heading` (degrees from +x).

        Built as a pile of spheres that shrink and gather towards the top.
        """
        rng = np.random.default_rng(seed)
        ca, sa = math.cos(math.radians(heading)), math.sin(math.radians(heading))
        x0, y0, z0 = self.lo
        nx, ny, nz = self.solid.shape
        n = puffs or int(10 + length * width / 60.0)
        for _ in range(n):
            u = rng.uniform(-1, 1)
            v = rng.uniform(-1, 1)
            if u * u + v * v > 1:
                continue
            # the higher a puff sits, the closer it stays to the middle
            t = rng.uniform(0, 1) ** 1.6
            spread = 1.0 - 0.75 * t
            lx, lz = u * length / 2.0 * spread, v * width / 2.0 * spread
            r = max(3.0, (0.22 * width + 0.05 * length) * (1.0 - 0.45 * t) * rng.uniform(0.7, 1.25))
            by = cy + t * height * (1.0 - 0.5 * (u * u + v * v)) + 0.35 * r
            bx, bz = cx + lx * ca - lz * sa, cz + lx * sa + lz * ca
            ia, ib = max(0, int(bx - r) - x0), min(nx - 1, int(bx + r) + 1 - x0)
            ja, jb = max(0, int(cy) - y0), min(ny - 1, int(by + r) + 1 - y0)
            ka, kb = max(0, int(bz - r) - z0), min(nz - 1, int(bz + r) + 1 - z0)
            if ia > ib or ja > jb or ka > kb:
                continue
            xs = np.arange(ia, ib + 1)[:, None, None] + x0 + 0.5 - bx
            ys = (np.arange(ja, jb + 1)[None, :, None] + y0 + 0.5 - by) / 0.8
            zs = np.arange(ka, kb + 1)[None, None, :] + z0 + 0.5 - bz
            self.solid[ia:ib + 1, ja:jb + 1, ka:kb + 1] |= xs * xs + ys * ys + zs * zs < r * r

    def well(self, x, z, radius):
        """Open a vertical shaft through everything, e.g. for a waterfall to vanish into."""
        x0, _, z0 = self.lo
        nx, _, nz = self.solid.shape
        xs = np.arange(nx)[:, None] + x0 + 0.5 - x
        zs = np.arange(nz)[None, :] + z0 + 0.5 - z
        ix, iz = np.nonzero(xs * xs + zs * zs < radius * radius)
        self.solid[ix, :, iz] = False

    def write(self, c, seed=0, dither=0.9):
        """Write the skin of the volume to canvas `c` in shaded tones. Returns the number of blocks."""
        s = self.solid
        p = np.pad(s, 1)
        inner = (p[:-2, 1:-1, 1:-1] & p[2:, 1:-1, 1:-1] & p[1:-1, :-2, 1:-1] & p[1:-1, 2:, 1:-1]
                 & p[1:-1, 1:-1, :-2] & p[1:-1, 1:-1, 2:])
        ii, jj, kk = np.nonzero(s & ~inner)
        del p, inner
        if not len(ii):
            return 0
        near = _blur(s.astype(np.float32), 2)      # where the surface faces
        wide = _blur(near, 4, passes=1)            # how buried a spot is: bumps low, creases high
        g = np.pad(near, 1, mode="edge")
        nx = g[ii, jj + 1, kk + 1] - g[ii + 2, jj + 1, kk + 1]
        ny = g[ii + 1, jj, kk + 1] - g[ii + 1, jj + 2, kk + 1]
        nz = g[ii + 1, jj + 1, kk] - g[ii + 1, jj + 1, kk + 2]
        up = ny / (np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-6)
        # a level top reads about 0.35 here, the crown of a puff 1, the crease between two puffs 0
        exposed = np.clip((0.62 - wide[ii, jj, kk]) / 0.34, 0.0, 1.0)
        light = N.smoothstep(0.15, 0.95, 0.45 * (0.5 + 0.5 * up) + 0.55 * exposed)
        x0, y0, z0 = self.lo
        xs, ys, zs = ii + x0, jj + y0, kk + z0
        last = len(TONES) - 1
        tone = last * (1.0 - light) + (_hash3(xs, ys, zs, seed) - 0.5) * dither
        idx = np.clip(np.rint(tone), 0, last).astype(int)
        names = [B.canon(t) for t in TONES]
        for x, y, z, t in zip(xs.tolist(), ys.tolist(), zs.tolist(), idx.tolist()):
            c.b[(x, y, z)] = names[t]
        return len(ii)


def write_pack(pack_dir, seed=7):
    """Repaint the tone blocks in a resource pack: flat colour with a breath of grain, no shading."""
    out = []
    jj, ii = np.meshgrid(np.arange(16), np.arange(16), indexing="ij")
    for n, (block, colour) in enumerate(zip(TONES, COLOURS)):
        rgb = np.array([int(colour[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)
        grain = (_hash3(ii, jj, 0 * ii, seed + n) - 0.5) * 5.0
        px = np.clip(rgb[None, None, :] + grain[..., None], 0, 255).astype(np.uint8)
        out.append(respack.cube(pack_dir, block, px, name=f"cloud{n}", shade=False, ao=False))
    return out
