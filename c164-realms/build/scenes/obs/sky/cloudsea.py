"""Work package sky/cloudsea: the sea of clouds the mountain stands in (plan 3.2, 10; card
plan/packages/sky/cloudsea.md; plan/parts/sky.md 4; c219's terrain review #163.1).

Three ways to make the sea, chosen by ``version`` and compared on the real client (the offline
renderer draws the fog but neither the vanilla cloud layer nor the afterglow, so it shows the block
clouds' shape and tones in fog; the card is settled on S1's real-game pictures, each camera shot
with the cloud setting off and fast as well):

    "a"  vanilla only   no block clouds; a denser, repainted clouds.png carries the whole sea. With
                        the player's clouds off nothing is left -- the weakness the comparison shows.
    "b"  blocks only    the block sea; the vanilla layer is blanked, the far distance left to the fog.
    "c"  both (default) the same block sea with the vanilla layer under and beyond it. What the
                        master scene builds (A0 #171: "block clouds near, the game's cloud layer and
                        fog far"); with the player's clouds switched off it is "b".

The block sea is a calm sheet with cumulus standing in it, not a plate on a dish (the review's
verdict on the stand-in). The sheet's top is y -26, y -27 in its hollows. Heads of cloud stand out of
it to y -23: steep round domes, the bigger ones with smaller ones crowded on them, packed side by
side in ranges that lie north-south, across the way to the afterglow, with lanes of calm sea
between; a few big piles reach y -20. Along the mountain the cloud heaps up against the rock, high
in the gullies and low on the capes, so the rock rises out of cloud all the way round and the line
where they meet is never level. The sea is closed out to the fill radius and thinned to single
heads and then nothing by the scatter radius, so its end is a ragged line of far heads in the fog
and never a circle; it reaches further towards the west, where the afterglow would show any end of
it.

Only empty cells are filled. The sea lies right against the bare rock and snow of the mountain
(ROCK), so no slit shows a level line round the mountain's foot; from everything else -- what is
built: iron, masonry, timber, rope -- it keeps CLEAR empty cells, so no bar or wall joins on to a
cloud, and a sunk floor of cloud lies under a gap that is left there, so the eye never drops
through.

The five tones are the occupancy roles B.CLOUD (dark to light, palette RAMPS["cloud"]). This package
paints them (A0's exception to "only materials paints blocks": the cloud colour is tuned with the
light of the sky), through materials/_kit like everyone else, so the stand-in steps aside the moment
BLOCKS names them. The pictures are flat tones named sky_cloud_0..4 and the game's own face shading
is turned off (shade=False, ao=False): which tone a block wears is baked here from the shape, lit
from the west where the afterglow is. The calm sea is the middle tone, its hollows one darker; on a
head the tone climbs with the height, the crown and the west side lightest, the lee side and the
foot darkest. There is no dither: the tones lie in clean bands, as pixel art shades a ball.
"""
import numpy as np

from artkit import noise as N
from artkit import respack
from artkit.clouds import _blur, _hash3

from ..common import blocks as B
from ..common import palette as P
from ..materials import _kit as K

# The blocks this package paints; nobody else may (the stand-in reads this and lets them go).
BLOCKS = K.blocks(B.CLOUD)

VERSIONS = ("a", "b", "c")
DEFAULT = "c"

CENTRE = (30.0, 0.0)            # the sea is drawn round this point (card)
FILL, SCATTER = 150.0, 215.0    # closed inside FILL, thinned to nothing by SCATTER (card)
WEST = 0.30                     # both radii grow by up to this share towards the west
SHEET_TOP = -26                 # scene y of the calm sea's top (the vanilla layer's top is at -28)
SHEET_BOTTOM = -28              # the flat underside
SEA = SHEET_TOP - 0.4           # the calm sea's mean height: blocks at y -26, y -27 in the hollows
HEAP = 3.3                      # a head of cloud stands this far out of the sea (to y -23, card)
PILE = 6.2                      # the few big piles (to y -20, card)
PILES = 16                      # how many of those in the whole sea
PEAK = -20                      # nothing is higher than this
FLOOR_Y = -31                   # the sunk floor under a gap beside something built
CLEAR = 1                       # empty cells kept between the sea and anything built
SEED = 41

# What the sea lies right against: the mountain's bare rock and snow, whole blocks that nothing
# joins on to. Every other block is something built and is given CLEAR cells of room.
ROCK = (B.ROCK_STONE.block, B.ROCK_ANDESITE.block, B.ROCK_DEEPSLATE, B.ROCK_COBBLED.block, B.TUFF.block, B.SNOW)

# The vanilla cloud sheet (clouds.png): 256x256, one pixel is a 12x12x4-block cell, the same colour
# everywhere; it tiles on all four edges. Repainted as an almost closed deck (vanilla covers 27.6%)
# cut by thin winding cracks that run north-south, so from the hilltop it reads as banks of cloud
# lying across the way to the afterglow. Blank for "b".
SHEET = dict(cover=0.90, cracks=(26, 110), holes=9, seed=SEED + 2)

GRAIN = 0.08                    # share of a tone's pixels nudged one step, within the cloud ramp


# --- the five flat tone pictures ---------------------------------------------------------------------
def _tone(i, seed=SEED):
    """A flat cloud tone with a breath of grain, every pixel a colour of RAMPS["cloud"]."""
    px = np.empty((K.TILE, K.TILE, 4), dtype=np.uint8)
    px[..., :3] = P.colour("cloud", i)
    px[..., 3] = 255
    jj, ii = np.meshgrid(np.arange(K.TILE), np.arange(K.TILE), indexing="ij")
    r = _hash3(ii, jj, 0 * ii, seed + i)
    px[r > 1.0 - GRAIN / 2, :3] = P.colour("cloud", min(i + 1, len(P.RAMPS["cloud"]) - 1))
    px[r < GRAIN / 2, :3] = P.colour("cloud", max(i - 1, 0))
    return px


# --- the vanilla sheet -------------------------------------------------------------------------------
def _clouds_sheet(blank=False):
    """A 256x256 cloud sheet for the vanilla layer: white where there is cloud (the game tints it by
    cloud_color), transparent where there is not. Seamless on every edge."""
    n = 256
    out = np.zeros((n, n, 4), dtype=np.uint8)
    out[..., :3] = 255
    if blank:
        return out                                  # the vanilla layer off (version "b")
    rng = np.random.default_rng(SHEET["seed"])
    gap = np.zeros((n, n), dtype=bool)              # [row = z, column = x]
    want = int(round((1.0 - SHEET["cover"]) * n * n))
    for _ in range(SHEET["holes"]):                 # a few small round holes
        cx, cz, rad = rng.uniform(0, n), rng.uniform(0, n), rng.uniform(1.2, 2.6)
        for dz in range(-3, 4):
            for dx in range(-3, 4):
                if dx * dx + dz * dz <= rad * rad:
                    gap[int(cz + dz) % n, int(cx + dx) % n] = True
    while gap.sum() < want:                         # cracks: walks southwards that wander east and west
        x, z = rng.uniform(0, n), int(rng.integers(0, n))
        drift, wide = 0.0, rng.uniform() < 0.18
        for _ in range(int(rng.integers(*SHEET["cracks"]))):
            drift = float(np.clip(0.82 * drift + rng.normal(0.0, 0.33), -1.0, 1.0))
            x += drift
            gap[z % n, int(x) % n] = True
            if wide and rng.uniform() < 0.5:
                gap[z % n, (int(x) + 1) % n] = True
            if rng.uniform() < 0.035:               # a short side crack
                for k in range(1, int(rng.integers(2, 6))):
                    gap[z % n, (int(x) + k) % n] = True
            z += 1
    out[..., 3] = np.where(gap, 0, 255)
    return out


# --- the block sea -----------------------------------------------------------------------------------
def _grid():
    """The columns the sea may use, (x0, z0, nx, nz): out to the scatter radius and a margin round
    CENTRE, wider to the west."""
    cx, cz = CENTRE
    x0, x1 = int(np.floor(cx - SCATTER * (1.0 + WEST) - 26.0)), int(np.ceil(cx + SCATTER + 26.0))
    z0, z1 = int(np.floor(cz - SCATTER - 26.0)), int(np.ceil(cz + SCATTER + 26.0))
    return x0, z0, x1 - x0 + 1, z1 - z0 + 1


def _stamp(top, px, pz, foot, rise, rad, bulge=0.5):
    """Raise the height field ``top`` to a dome on (px, pz): ``rise`` high in the middle, falling to
    ``foot`` at the rim. ``bulge`` 0.5 is half an ellipsoid, steep at the foot and flat on top, as a
    cumulus head is; towards 1 the dome grows pointed."""
    nx, nz = top.shape
    a0, a1 = max(0, int(np.floor(px - rad))), min(nx - 1, int(np.ceil(px + rad)))
    b0, b1 = max(0, int(np.floor(pz - rad))), min(nz - 1, int(np.ceil(pz + rad)))
    if a0 > a1 or b0 > b1:
        return
    xs = np.arange(a0, a1 + 1)[:, None] + 0.5 - px
    zs = np.arange(b0, b1 + 1)[None, :] + 0.5 - pz
    d2 = (xs * xs + zs * zs) / (rad * rad)
    inside = d2 < 1.0
    h = foot + rise * np.maximum(1.0 - d2, 0.0) ** bulge
    view = top[a0:a1 + 1, b0:b1 + 1]
    view[inside] = np.maximum(view[inside], h[inside])


def _grow(a, r):
    """Grow a boolean array by r cells along every axis (a box)."""
    out = a
    for ax in range(a.ndim):
        acc = out.copy()
        n = out.shape[ax]
        for d in range(1, r + 1):
            lo, hi = [slice(None)] * a.ndim, [slice(None)] * a.ndim
            lo[ax], hi[ax] = slice(0, n - d), slice(d, n)
            acc[tuple(hi)] |= out[tuple(lo)]
            acc[tuple(lo)] |= out[tuple(hi)]
        out = acc
    return out


def _reach(passable):
    """The cells of ``passable`` (2D) that are joined to the border through passable cells."""
    reach = np.zeros_like(passable)
    reach[0, :], reach[-1, :] = passable[0, :], passable[-1, :]
    reach[:, 0], reach[:, -1] = passable[:, 0], passable[:, -1]
    while True:
        before = int(reach.sum())
        for ax in (0, 1):                           # spread along the runs of passable cells
            p, r = np.moveaxis(passable, ax, 0), np.moveaxis(reach, ax, 0)
            start = np.ones(p.shape, dtype=np.int64)
            start[1:] = p[1:] != p[:-1]
            run = np.cumsum(start, axis=0) + (np.arange(p.shape[1]) * (p.shape[0] + 1))[None, :]
            hit = np.bincount(run[r], minlength=int(run.max()) + 1) > 0
            r |= p & hit[run]
        if int(reach.sum()) == before:
            return reach


def _others(canvas, origin, lo, shape, y0):
    """(occ, rock): the cells of the box that hold a block of somebody else, and which of those are
    the mountain's bare rock (box indices; the box starts at scene (lo[0], y0, lo[1]))."""
    ox, oy, oz = origin
    nx, ny, nz = shape
    x0, z0 = lo
    occ, rock = np.zeros(shape, dtype=bool), np.zeros(shape, dtype=bool)
    keys = np.array(list(canvas.b.keys()), dtype=np.int64).reshape(-1, 3)
    if len(keys):
        a, b, c = keys[:, 0] - ox - x0, keys[:, 1] - oy - y0, keys[:, 2] - oz - z0
        ok = (a >= 0) & (a < nx) & (b >= 0) & (b < ny) & (c >= 0) & (c < nz)
        occ[a[ok], b[ok], c[ok]] = True
        for key, i, j, k in zip(keys[ok].tolist(), a[ok].tolist(), b[ok].tolist(), c[ok].tolist()):
            if canvas.b[tuple(key)].partition("[")[0].split(":")[-1] in ROCK:
                rock[i, j, k] = True
    return occ, rock


def _field(seed, land):
    """The sea as a height field: (top, level, deck). ``top`` is the continuous height of the cloud
    top per column (-inf where there is none), ``level`` the calm sea's height there, ``deck`` says
    where the sea is closed (beyond it there are single heads only). ``land`` marks the columns where
    something stands in the cloud: the sea heaps up along it and keeps its big piles away from it."""
    x0, z0, nx, nz = _grid()
    cx, cz = CENTRE
    X, Z = np.meshgrid(np.arange(nx) + x0, np.arange(nz) + z0, indexing="ij")

    r = np.hypot(X - cx, Z - cz)
    west = np.clip((cx - X) / np.maximum(r, 1.0), 0.0, 1.0)            # 1 due west of the centre
    wobble = N.fbm2(X / 47.0, Z / 47.0, seed + 5, octaves=3) * 20.0    # the edge is not a circle
    density = N.smoothstep(SCATTER, FILL, (r - wobble) / (1.0 + WEST * west ** 1.5))
    # where the cloud piles up: ranges that lie north-south, bent a little; 1 in a range, 0 in a lane
    bend = N.fbm2(X / 90.0, Z / 90.0, seed + 7, octaves=2) * 26.0
    core = N.smoothstep(-0.02, 0.22, N.fbm2((X + bend) / 60.0, Z / 100.0, seed + 1, octaves=2))
    level = SEA + 0.6 * N.fbm2(X / 58.0, Z / 58.0, seed + 2, octaves=2)

    rng = np.random.default_rng(seed)
    top = np.full((nx, nz), -np.inf)

    def cell_of(px, pz):
        return min(nx - 1, max(0, int(px))), min(nz - 1, max(0, int(pz)))

    def dome(px, pz, rad, rise, bulge=None):
        ix, iz = cell_of(px, pz)                    # rooted a little under the sea where it stands
        _stamp(top, px, pz, level[ix, iz] - 0.25, rise + 0.25, rad, rng.uniform(0.5, 0.8) if bulge is None else bulge)

    def head(px, pz, rad, rise):
        """A head of cloud. A small one is one dome; a middling one carries smaller domes on its
        flanks; a big one is a low cushion with a crowd of domes on it, so no top is a table."""
        if rad < 4.5:
            kids, spread, size, high = int(rng.integers(0, 2)), (0.6, 1.0), (0.5, 0.75), (0.55, 0.9)
        elif rad < 6.5:
            kids, spread, size, high = int(rng.integers(1, 4)), (0.5, 1.0), (0.45, 0.75), (0.6, 1.0)
        else:
            kids, spread, size, high = int(rng.integers(5, 9)), (0.1, 0.9), (0.3, 0.5), (0.8, 1.0)
        dome(px, pz, rad, rise if rad < 6.5 else 0.66 * rise)
        for _ in range(kids):
            a, s = rng.uniform(0.0, 2.0 * np.pi), rng.uniform(*spread)
            dome(px + np.cos(a) * s * rad, pz + np.sin(a) * s * rad, rad * rng.uniform(*size), rise * rng.uniform(*high))

    # the heads: packed side by side in the ranges, a few standing alone in the lanes of calm sea
    cell = 8
    for gx in range(0, nx, cell):
        for gz in range(0, nz, cell):
            px, pz = gx + rng.uniform(0, cell), gz + rng.uniform(0, cell)
            u, v, w, t = rng.uniform(size=4)
            ix, iz = cell_of(px, pz)
            d, c = density[ix, iz], core[ix, iz]
            if d <= 0.0 or u > d ** 0.8 * (0.06 + 0.86 * c):
                continue                            # thinned out in the lanes and towards the edge
            rad = (2.8 + 4.2 * v ** 1.5) * (0.75 + 0.25 * d) * (0.85 + 0.3 * c)
            if c > 0.8 and t > 0.9:
                rad = 7.0 + 25.0 * (t - 0.9)        # the broad cushions in the heart of a range
            head(px, pz, rad, min(HEAP * (0.62 + 0.38 * w), rad * (0.5 + 0.3 * w)))

    # the few big piles, well apart, in the ranges, away from the mountain: broad shoulders, a
    # narrower tower standing out of them, smaller domes on its flanks
    far = ~_grow(land, 28)
    piles = []
    for _ in range(4000):
        if len(piles) == PILES:
            break
        px, pz = rng.uniform(0, nx), rng.uniform(0, nz)
        ix, iz = cell_of(px, pz)
        if density[ix, iz] < 0.85 or core[ix, iz] < 0.6 or not far[ix, iz]:
            continue
        if any(np.hypot(px - qx, pz - qz) < 60.0 for qx, qz in piles):
            continue
        piles.append((px, pz))
        for n, away, rad, rise, bulge in ((4, (2.0, 6.0), (6.0, 8.5), (3.2, 4.4), 0.6),
                                          (2, (0.0, 2.5), (4.0, 5.5), (0.86 * PILE, PILE), 0.75),
                                          (4, (2.5, 5.5), (2.4, 3.6), (4.0, 5.2), 0.7)):
            for _ in range(n):
                a, s = rng.uniform(0.0, 2.0 * np.pi), rng.uniform(*away)
                dome(px + np.cos(a) * s, pz + np.sin(a) * s, rng.uniform(*rad), rng.uniform(*rise), bulge)

    # the surf: cloud heaped against whatever stands in it, high where the land folds round it
    if land.any():
        zone = _grow(land, 6) & ~land
        fold = _blur(land.astype(np.float32), 6)    # over a half in a gully, a tenth off a cape
        surf = N.fbm2(X / 23.0, Z / 23.0, seed + 9, octaves=2)
        step = 6
        for gx in range(0, nx, step):
            for gz in range(0, nz, step):
                px, pz = gx + rng.uniform(0, step), gz + rng.uniform(0, step)
                u, v, w = rng.uniform(size=3)
                ix, iz = cell_of(px, pz)
                if not zone[ix, iz]:
                    continue
                a = float(np.clip(0.45 + surf[ix, iz] + 1.5 * (fold[ix, iz] - 0.28), 0.0, 1.0))
                if u > 0.45 + 0.55 * a:
                    continue
                rise = 1.3 + (HEAP - 1.3) * a * (0.75 + 0.25 * w)
                if a > 0.8 and w > 0.35:
                    rise += 1.9 * w * (a - 0.8) / 0.2                   # the highest, to about y -21
                head(px, pz, min(6.4, 3.3 + 2.8 * v + 1.2 * a), rise)

    deck = density > 0.7
    top = np.where(deck, np.maximum(top, level), top)                  # closed between the heads
    top = np.minimum(top, PEAK + 0.45)
    return top, level, deck


def _shade(top, has, level):
    """Light 0..1 per column from the continuous height field, lit from the west and from above: the
    calm sea in the middle, its hollows darker; on a head the light climbs with the height, more on
    the west side, less on the lee side and round the foot; a whole range is lighter on its west."""
    x0, _, nx, nz = _grid()
    h = np.where(has, top, level - 1.5).astype(np.float32)

    def westward(a):                                # rising eastwards = facing west
        p = np.pad(a, 1, mode="edge")
        return (p[2:, 1:-1] - p[:-2, 1:-1]) * 0.5

    crest = h - _blur(h, 3)                                            # over its surroundings or under
    alt = np.clip((h - SEA) / HEAP, -0.3, 1.4)
    west = np.clip((CENTRE[0] - (np.arange(nx) + x0)) / FILL, -1.0, 1.4)[:, None]
    return (0.40 + 0.36 * alt + 0.22 * np.tanh(1.1 * westward(h)) + 0.10 * np.tanh(2.5 * westward(_blur(h, 5)))
            + 0.13 * np.tanh(1.4 * crest) + 0.05 * west)


def build(canvas, origin=(0, 0, 0), version=DEFAULT, *, seed=SEED):
    """Lay the block cloud sea into the canvas. Places blocks only, so it returns 0 display entities.
    The master scene calls build(canvas, origin); a test scene passes version to compare the three."""
    if version not in VERSIONS:
        raise ValueError(f"cloudsea version is one of {VERSIONS}, not {version!r}")
    # The sea is laid once: a sheet of cloud tones put down earlier (site/terrain's stand-in for this
    # package) is taken up, whichever version is built.
    names = list(B.CLOUD)                           # dark..light, as the tone index runs
    for key in [k for k, state in canvas.b.items() if state.partition("[")[0].split(":")[-1] in names]:
        del canvas.b[key]
    if version == "a":                              # vanilla layer only: no blocks
        return 0

    x0, z0, nx, nz = _grid()
    y0, y1 = FLOOR_Y - 1, PEAK + 2
    ny = y1 - y0 + 1
    occ, rock = _others(canvas, origin, (x0, z0), (nx, ny, nz), y0)
    built = _grow(occ & ~rock, CLEAR)               # what is built, and the room it is given

    # The land: columns where somebody's block stands in the cloud band, and what those wall in (the
    # hollow of the mountain; what merely has a bridge over it is not walled in and keeps its cloud).
    band = occ[:, SHEET_BOTTOM - y0:, :].any(axis=1)
    inside = ~band & ~_reach(~band)
    top, level, deck = _field(seed, band | inside)
    has = np.isfinite(top) & ~inside
    tops = np.where(has, np.rint(top), y0 - 1).astype(np.int64)

    # only empty cells, clear of what is built, and not in the hollow under a crust of rock
    ys = np.arange(ny)[None, :, None] + y0
    solid = has[:, None, :] & (ys >= SHEET_BOTTOM) & (ys <= tops[:, None, :]) & ~occ & ~built
    solid &= ~np.flip(np.logical_or.accumulate(np.flip(rock, 1), axis=1), 1)

    # the sunk floor: where the sea was opened beside something built and nothing stands in the
    # column, the eye would drop through to the void; a dark course of cloud lies there, low in the gap
    floor = np.zeros_like(solid)
    floor[:, FLOOR_Y - y0, :] = deck & ~inside & ~solid.any(axis=1) & ~occ.any(axis=1)
    floor &= ~built

    # only what can be seen from above or from the side is placed: a cell with cloud or rock over it
    # and on all four sides is left out, and so is the unseen underside of the sea
    p = np.pad(solid | occ, 1)
    west_open, east_open = ~p[:-2, 1:-1, 1:-1], ~p[2:, 1:-1, 1:-1]
    side_open = ~p[1:-1, 1:-1, :-2] | ~p[1:-1, 1:-1, 2:]
    up_open = ~p[1:-1, 2:, 1:-1]
    skin = solid & (up_open | west_open | east_open | side_open)

    # a cell seen from the side only takes its column's light, more of it facing west, less facing
    # east, and less the further down the side it lies
    light = _shade(top, has, level)[:, None, :] + np.zeros((1, ny, 1), dtype=np.float32)
    turn = np.where(west_open, 0.10, np.where(side_open, -0.06, -0.16))
    light = np.where(up_open, light, light + turn - 0.05 * np.clip(tops[:, None, :] - ys, 0, 8))

    ox, oy, oz = origin
    last = len(names) - 1
    ii, jj, kk = np.nonzero(skin)
    idx = np.clip(np.rint(last * light[ii, jj, kk]), 0, last).astype(int)
    for x, y, z, t in zip((ii + x0 + ox).tolist(), (jj + y0 + oy).tolist(), (kk + z0 + oz).tolist(), idx.tolist()):
        canvas.set(x, y, z, names[t], keep=True)
    ii, jj, kk = np.nonzero(floor)
    for x, y, z in zip((ii + x0 + ox).tolist(), (jj + y0 + oy).tolist(), (kk + z0 + oz).tolist()):
        canvas.set(x, y, z, names[0], keep=True)
    return 0


# --- the resource pack: the five tone pictures, the five blocks, the vanilla sheet -------------------
def pack(pack_dir, version=DEFAULT):
    out = []
    for i in range(len(B.CLOUD)):
        K.paint(pack_dir, f"sky_cloud_{i}", _tone(i))
    for i, block in enumerate(B.CLOUD):
        mapping = {ref: f"sky_cloud_{i}" for ref in respack.block_pictures(K.game(), block)}
        out.append(K.redirect(pack_dir, block, mapping, shade=False, ao=False))
    blank = version == "b"
    sheet = _clouds_sheet(blank=blank)
    respack.texture(pack_dir, "environment/clouds", sheet)
    cover = float((sheet[..., 3] > 0).mean())
    out.append("clouds.png: " + ("blanked (block clouds only)" if blank
                                 else f"{cover * 100:.1f}% cover, thin north-south cracks"))
    return out
