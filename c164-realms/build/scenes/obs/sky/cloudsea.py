"""Work package sky/cloudsea: the sea of clouds the mountain stands in (plan 3.2, 10; card
plan/packages/sky/cloudsea.md; plan/parts/sky.md 4; c219's terrain review #163.1; the director's
rulings of 11-16 in plan/roles/A0-director.md: the server sends blocks for ten chunks round a
player, and the map carries no registry files).

The sea is blocks and nothing else. The game's own cloud layer cannot be the sea's face: its height
is a registry value, which the map may not carry, and at its own height it would drift through the
lower platform. clouds.png is blanked, so no layer is drawn whatever the player's cloud setting is.
What lies beyond the blocks is the sky's, drawn by the resource pack's shaders (A2's). The join
agreed with A2 (11-16; his sky/mood holds the numbers): under the horizon the sky is painted as a
level sea at the height of FACE in the colour of level cloud, sunk into the colour of the horizon
by a long haze of its own (1 - exp(-distance / 800)); the blocks' fog runs from 60 to 150 blocks
from the eye and takes a block under the horizon into the far sea of its own direction, a block
above it into the sky's lowest ring. Level cloud is the far sea's colour already, so the blocks
need no rim and no fading of their own: where they end, nothing changes.

One surface, laid as far as REACH from where people stand, a single block thick wherever it is
level:

    the swell   the sea is not flat. Level cloud has its upper face at y -28 (FACE); broad hollows
                lie a block lower and broad crests a block higher, longer along the wind than
                across it, more of the hollows in the calm lanes and more of the crests under the
                banks. No patch of a level is narrower than BROAD: a narrow one is a floe.
    the heads   cumulus standing out of the swell to y -24: half balls, about as high as they are
                wide, the bigger ones with smaller ones crowded on their flanks and a knob or two
                on top (to y -23), packed side by side in banks with calm lanes between;
    the piles   a few towers in the banks, to y -20;
    the surf    cloud heaped against whatever stands in the sea: a lip all the way round, high in
                the gullies and low on the capes, higher where the wind comes from, so the line
                where rock and sea meet is cloud and never a level cut.

Only empty cells are filled. The sea lies right against whatever stands in it: the mountain's rock
and snow, and what is built -- the legs and girders of the cable trestle, piers, steps -- and it
goes on under what merely bridges it. Where something built ends low in the sea (its top within
two blocks over the face: the last cells of the cable track) the sea heaps a head over it, so the
track runs into cloud and is not seen to end on a level; near anything that stands in the sea no
cloud is higher than y -24 (LOW: the trestle's bars begin above that), the piles keep well away.
The one exception to lying against everything is what would grow a thick arm towards a cloud
beside it when the scene is placed (walls and fences, JOINS): from those the sea keeps CLEAR empty
cells, with a sunk floor of cloud under the gap.

The five tones are the occupancy roles B.CLOUD (dark to light, palette RAMPS["cloud"]). This package
paints them (A0's exception to "only materials paints blocks": the cloud colour is tuned with the
light of the sky), through materials/_kit like everyone else. The pictures are flat tones named
sky_cloud_0..4 and the game's own face shading is turned off (shade=False, ao=False): which tone a
block wears is baked here from the shape, lit from the west where the afterglow is. Level cloud
wears the second lightest tone, the top of a head as much as the calm sea (sky/mood's "cloud" is
that tone as the blue hour lights it: the colour of the far sea, so that the blocks end in their
own colour). What faces west is the lightest tone, what faces east the two below; the
foot of a head and the creases between two are darker again, the sea in the lee of a head lies in
its shadow, and the crowns of the piles catch the light. The swell is shaded as broadly as it is
shaped: its western slopes a tone lighter, its eastern slopes a tone darker, the steps themselves
inside those bands, so no step is outlined. There is no dither: the tones lie in clean bands, as
pixel art shades a ball. Light and dark keep the balance, so from far off the sea is the one tone.
"""
import numpy as np

from artkit import noise as N
from artkit import respack
from artkit.clouds import _blur, _hash3

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..materials import _kit as K

# The director's switch for what is laid over the whole site (COMMON 0.5; since 11-16 08:24 the
# author turns it on in the commit he delivers): off, build() places nothing and takes nothing up,
# and site/terrain's stand-in ring stays. On, the sea is laid on every canvas that has something
# standing in it (see build()); a test scene asks with dress=True whatever the switch says.
DRESS = True

# The blocks this package paints; nobody else may (the stand-in reads this and lets them go).
BLOCKS = K.blocks(B.CLOUD)

FACE = -28                      # scene y of the sea's face: the upper face of level cloud
MEAN = FACE - 1                 # -29: the top block of level cloud
TROUGH = MEAN - 1               # -30: ... of a hollow of the swell; the sea has no block lower than this
FOOT = FACE - 0.5               # a height field at or over this puts a block above the face
FLOOR_Y = TROUGH - 2            # -32: the sunk floor under a gap beside a wall or a fence
SWELL = 1.2                     # how far the long waves roll the surface about its level, in blocks
ROLL = (38.0, 64.0)             # ... and how long they are, across the wind and along it
PILLOW = 1.6                    # how high the low heaps the face is made of stand over the creases between them
HEAPS = 10                      # ... and how far apart they lie
BANK = 0.5                      # the banks ride this much higher than the calm lanes between them
BROAD = 4                       # no patch of a level of the swell is narrower than this many blocks
HEAP = 4.6                      # a head of cloud stands this far out of the face (to y -24)
KNOB = 5.6                      # ... and a knob on a big one a block higher (to y -23, the card's)
SMALLEST = 1.6                  # ... and never less than this: two blocks in its middle, or it is a floe
FOOTING = 2.5                   # a head's lowest step reaches this far round the step above it, no further
PILE = 8.0                      # the few big piles (to y -20, card)
PILES = 7                       # how many of those
PEAK = -20                      # nothing is higher than this
CLEAR = 1                       # empty cells kept between the sea and what would join on to it
SEED = 41

# What stands in the sea. A whole block of somebody else -- rock, snow, masonry, a girder -- hides
# the cloud behind it and under it. THIN (by the ending of the name, or the whole name) is what
# hides nothing: a slab, a step, a rail, a pipe, a layer of snow. JOINS are the thin things that
# grow a thick arm towards a whole block beside them when a scene is placed: the game shapes them
# from their neighbours. The sea keeps CLEAR cells away from those and lies right against
# everything else. Bars and panes join on as well, but with a thin arm at the cloud's own level
# that ends in the cloud's face; a well round every leg of the trestle would show far more.
THIN = ("_slab", "_stairs", "_wall", "_fence", "_fence_gate", "_bars", "_chain", "_rod", "_pane", "_glass", "_grate",
        "_trapdoor", "_door", "_carpet", "_button", "_sign", "_torch", "_lantern", "_rail", "_candle", "_head")
THIN_NAMES = (B.SNOW_LAYER, "chain", "lantern", "ladder", "rail", "glass", "torch", "lever", "scaffolding")
JOINS = ("_wall", "_fence")
# What is built and runs down into the sea -- a track, a stair -- is heaped over where its top comes
# this near the face: the cloud stands at least two blocks over it, and the track is lost in a head
# of cloud instead of ending on a level.
SUNK = (FACE - 1, FACE + 2)     # the block y of such a top: -29 .. -26 (lower, it is under the face anyway)
COVERED = 6.5                   # the head over it is this wide
LOW = FACE + 4                  # -24: no cloud is higher than this block within SHY of what stands in the sea
LEDGE = LOW - 1                 # a whole block that ends bare beside the sea no higher than this is lapped over
SHY = 28                        # ... the piles keep this far away from it (site/cablecar's bars begin at -23)

# How far the sea is laid. The server sends blocks for ten chunks round a player (Realms), so
# nobody is shown a block further off than 160 and the fog has to be whole before that. The sea
# reaches REACH from where people stand, which is as far as that fog lets anyone on a flat see it.
REACH = 150.0
THIN_OUT = (REACH - 56.0, REACH - 14.0)     # the banks thin out between these and the last of the sea is calm
WIND = {"north": (0.0, -1.0), "south": (0.0, 1.0), "west": (-1.0, 0.0), "east": (1.0, 0.0)}[S.WIND_FROM]

LIE = 9.0                      # the shading: how readily the lie of the swell turns a tone
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


def _no_clouds():
    """clouds.png, 256x256, one pixel a cell of the game's cloud layer: no cell holds cloud."""
    out = np.zeros((256, 256, 4), dtype=np.uint8)
    out[..., :3] = 255
    return out


# --- where people stand ------------------------------------------------------------------------------
def _flats():
    """(x0, z0, x1, z1, y of the feet) of the flats people stand on, from the skeleton. The sunset
    platform is the one round one and is taken apart."""
    shelves = (S.MAST_PAD, S.WEATHER_STATION, S.WATER_TOWER, S.SOUTH_LOOKOUT)
    return ([(*S.UPPER_TERRACE, S.GROUND), (*S.LOWER_PLATFORM, S.LOWER_GROUND), (*S.CABLE_STATION, S.STATION_GROUND)]
            + [(*s["box"], s["feet"]) for s in shelves])


def _off(box, X, Z):
    x0, z0, x1, z1 = box[:4]
    return np.hypot(np.maximum(np.maximum(x0 - X, X - x1), 0.0), np.maximum(np.maximum(z0 - Z, Z - z1), 0.0))


def _hull(X, Z):
    """How far a column is from the nearest place where somebody can stand."""
    (cx, cz), r = S.SUNSET_PLATFORM["centre"], S.SUNSET_PLATFORM["radius"]
    d = np.maximum(np.hypot(X - cx, Z - cz) - r, 0.0)
    for flat in _flats():
        d = np.minimum(d, _off(flat, X, Z))
    return d


def _grid():
    """The columns the sea may use, (x0, z0, nx, nz): REACH from where people stand, and a margin."""
    (cx, cz), r = S.SUNSET_PLATFORM["centre"], S.SUNSET_PLATFORM["radius"]
    flats = _flats()
    pad = int(REACH) + 26
    x0, x1 = min([cx - r] + [f[0] for f in flats]) - pad, max(f[2] for f in flats) + pad
    z0, z1 = min([cz - r] + [f[1] for f in flats]) - pad, max([cz + r] + [f[3] for f in flats]) + pad
    return x0, z0, x1 - x0 + 1, z1 - z0 + 1


# --- the block sea -----------------------------------------------------------------------------------
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


def _distance(mask, reach):
    """How many cells every cell of a 2D mask lies from the nearest set one, as the crow flies; no
    further than ``reach`` is told apart."""
    n, m = mask.shape
    along = np.where(mask, 0.0, reach + 1.0)        # along z first
    for k in range(1, m):
        along[:, k] = np.minimum(along[:, k], along[:, k - 1] + 1.0)
    for k in range(m - 2, -1, -1):
        along[:, k] = np.minimum(along[:, k], along[:, k + 1] + 1.0)
    along *= along
    out = along.copy()
    for d in range(1, reach + 1):                   # then the rows d away on either side
        out[d:, :] = np.minimum(out[d:, :], along[:-d, :] + d * d)
        out[:-d, :] = np.minimum(out[:-d, :], along[d:, :] + d * d)
    return np.minimum(np.sqrt(out), float(reach))


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


def _open(mask, n):
    """The cells of a 2D mask that lie in a square of n by n cells of it."""
    sq = mask.copy()                                # sq[i, j]: the square whose low corner is (i, j) is all set
    for ax in (0, 1):
        acc = sq.copy()
        size = sq.shape[ax]
        for d in range(1, n):
            lo, hi = [slice(None)] * 2, [slice(None)] * 2
            lo[ax], hi[ax] = slice(0, size - d), slice(d, size)
            acc[tuple(lo)] &= sq[tuple(hi)]
        tail = [slice(None)] * 2
        tail[ax] = slice(max(0, size - (n - 1)), size)
        acc[tuple(tail)] = False
        sq = acc
    out = sq
    for ax in (0, 1):
        acc = out.copy()
        size = out.shape[ax]
        for d in range(1, n):
            lo, hi = [slice(None)] * 2, [slice(None)] * 2
            lo[ax], hi[ax] = slice(0, size - d), slice(d, size)
            acc[tuple(hi)] |= out[tuple(lo)]
        out = acc
    return out


def _tidy(base, top, lip):
    """The surface as blocks show it, cleaned as a sprite is: (level, height). ``base`` is the swell
    and ``top`` what stands out of it, both as the continuous y of a column's top block (``top`` is
    -inf where nothing stands); ``lip`` marks the cells along the land, which stay as they are.

    The swell's levels are broad: no patch of a hollow or of a crest is narrower than BROAD. No step
    of a head is narrower than two cells (one block on a head is a pimple, a row of them a fence),
    and a head's lowest step is a foot and not a floe: it reaches FOOTING round the step above it
    and no further, and a patch one block high with nothing on it goes. A cell lower than all four
    beside it is a pit and is filled. ``level`` is the y of every column's top block, ``height``
    the smooth height the shading reads: within half a block of the level."""
    b = np.floor(np.clip(base, TROUGH, MEAN + 1.45) + 0.5).astype(np.int64)
    swell = np.where(_open(b <= TROUGH, BROAD), TROUGH, MEAN)
    for y in range(MEAN + 1, int(b.max()) + 1):
        swell[_open(b >= y, BROAD) & (swell == y - 1)] = y
    lvl = np.maximum(swell, np.where(np.isfinite(top), np.floor(top + 0.5), TROUGH).astype(np.int64))
    out = swell.copy()
    for y in range(TROUGH + 1, int(lvl.max()) + 1):
        there = lvl >= y
        out[there & (out == y - 1) & (_open(there, 2) | lip)] = y
    rise = out - swell
    floe = (rise == 1) & ~lip & (_distance(rise >= 2, 4) > FOOTING)
    out[floe] = swell[floe]
    p = np.pad(out, 1, mode="edge")
    out = np.maximum(out, np.minimum(np.minimum(p[:-2, 1:-1], p[2:, 1:-1]), np.minimum(p[1:-1, :-2], p[1:-1, 2:])))
    height = np.where(out > swell, np.minimum(np.maximum(top, out - 0.45), out + 0.45),
                      out + np.clip(base - out, -0.45, 0.45))
    return out, height


def _others(canvas, origin, lo, shape, y0):
    """(occ, whole, joins, high, roof): the cells of the box that hold a block of somebody else;
    which of those are whole blocks, hiding what is behind them; which hold something that would
    join on to a cloud (box indices; the box starts at scene (lo[0], y0, lo[1])); and per column
    the scene y of the highest block of somebody else and of the highest whole one, at any height
    (far below the box where there is none)."""
    ox, oy, oz = origin
    nx, ny, nz = shape
    x0, z0 = lo
    occ, whole, joins = (np.zeros(shape, dtype=bool) for _ in range(3))
    high = np.full((nx, nz), -10 ** 6, dtype=np.int64)
    roof = high.copy()
    keys = np.array(list(canvas.b.keys()), dtype=np.int64).reshape(-1, 3)
    if len(keys):
        kinds = {}                                  # per block state: 0 thin, 1 joins on, 2 whole

        def kind(state):
            name = state.partition("[")[0].split(":")[-1]
            return 1 if name.endswith(JOINS) else 0 if (name.endswith(THIN) or name in THIN_NAMES) else 2

        for state in set(canvas.b.values()):
            kinds[state] = kind(state)
        what = np.fromiter((kinds[state] for state in canvas.b.values()), dtype=np.int64, count=len(keys))
        a, b, c = keys[:, 0] - ox - x0, keys[:, 1] - oy - y0, keys[:, 2] - oz - z0
        col = (a >= 0) & (a < nx) & (c >= 0) & (c < nz)
        np.maximum.at(high, (a[col], c[col]), b[col] + y0)
        full = col & (what == 2)
        np.maximum.at(roof, (a[full], c[full]), b[full] + y0)
        ok = col & (b >= 0) & (b < ny)
        occ[a[ok], b[ok], c[ok]] = True
        whole[a[ok & (what == 2)], b[ok & (what == 2)], c[ok & (what == 2)]] = True
        joins[a[ok & (what == 1)], b[ok & (what == 1)], c[ok & (what == 1)]] = True
    return occ, whole, joins, high, roof


def _field(seed, land, sunk=()):
    """The sea's surface: (level, height, sea). ``level`` is the y of every column's top block,
    ``height`` the smooth height the shading reads, ``sea`` where the sea lies at all. ``land``
    marks the columns where something stands in the cloud: the sea heaps up along it and keeps its
    piles away from it. ``sunk`` lists what is built and ends low in the sea, as (column, column,
    y of its top block): the sea heaps over those."""
    x0, z0, nx, nz = _grid()
    X, Z = np.meshgrid(np.arange(nx) + x0, np.arange(nz) + z0, indexing="ij")

    out = _hull(X, Z) - 14.0 * N.fbm2(X / 47.0, Z / 47.0, seed + 5, octaves=3)     # no edge is a ruled line
    sea = out < REACH
    amount = N.smoothstep(THIN_OUT[1], THIN_OUT[0], out)
    # where the cloud piles up: banks, longer north-south than they are wide, about two thirds of
    # the sea that may carry any; 1 in a bank, 0 in the calm lanes that wind between them
    core, base = _face(X, Z, seed)
    # how hard it boils: the heads stand high here and lie low and woolly there
    vigour = N.smoothstep(-0.25, 0.25, N.fbm2(X / 44.0, Z / 44.0, seed + 3, octaves=2))

    top = np.full((nx, nz), -np.inf)

    def cell_of(px, pz):
        return min(nx - 1, max(0, int(px))), min(nz - 1, max(0, int(pz)))

    def dome(g, px, pz, rad, rise, bulge=None):     # rooted a little under the face
        _stamp(top, px, pz, FOOT - 0.25, rise + 0.25, rad, g.uniform(0.5, 0.62) if bulge is None else bulge)

    def head(g, px, pz, rad, rise):
        """A head of cloud, shaped by the random numbers of ``g``: half a ball, about as high as
        its foot is wide, so its side stands steep out of the face and its top is round. A small
        one is one dome; the bigger it is, the more smaller ones crowd on its flanks, each half a
        ball again and lower than the one it leans on, and a big one carries a knob or two on its
        top, so that no top is a table."""
        dome(g, px, pz, rad, rise)
        if rad < 3.4:
            kids = int(g.integers(0, 2))
        elif rad < 4.8:
            kids = int(g.integers(1, 4))
        elif rad < 6.0:
            kids = int(g.integers(2, 5))
        else:
            kids = int(g.integers(4, 8))
        for _ in range(kids):
            a, s = g.uniform(0.0, 2.0 * np.pi), g.uniform(0.55, 1.0)
            r = max(2.2, rad * g.uniform(0.42, 0.68))
            dome(g, px + np.cos(a) * s * rad, pz + np.sin(a) * s * rad, r,
                 min(rise * g.uniform(0.6, 0.95), r * g.uniform(0.8, 1.05)))
        if rad >= 4.4 and rise >= 3.4:
            for _ in range(int(g.integers(1, 3)) + (rad >= 6.4)):
                a, s = g.uniform(0.0, 2.0 * np.pi), g.uniform(0.0, 0.45)
                dome(g, px + np.cos(a) * s * rad, pz + np.sin(a) * s * rad, g.uniform(2.2, 3.0),
                     min(rise + g.uniform(0.7, 1.1), KNOB), 0.55)

    # Every head has random numbers of its own, by the cell of the grid it is drawn in (the piles by
    # their place in the list of sites tried): when somebody builds or digs at the shore the sea
    # changes there and stays as it was everywhere else.

    # the heads: packed side by side in the banks, so close that they lean on one another, and none
    # in the calm lanes between the banks. They do not look at the land, so they stand where they
    # stand whatever is built. Towards the end of the sea they grow few, small and low.
    cell = 7
    gxs, gzs = range(0, nx, cell), range(0, nz, cell)
    draws = np.random.default_rng((seed, 0)).uniform(size=(len(gxs), len(gzs), 6)).tolist()
    for i, gx in enumerate(gxs):
        for j, gz in enumerate(gzs):
            fx, fz, u, v, w, t = draws[i][j]
            px, pz = gx + fx * cell, gz + fz * cell
            ix, iz = cell_of(px, pz)
            d, c = amount[ix, iz], core[ix, iz]
            if d <= 0.0 or u > d ** 0.8 * 0.95 * c:
                continue
            rad = (3.0 + 3.2 * v ** 1.3) * (0.8 + 0.2 * d)
            if c > 0.7 and d > 0.6 and t > 0.82:
                rad = 6.2 + 9.0 * (t - 0.82)        # the big heads in the heart of a bank
            lift = (0.72 + 0.28 * vigour[ix, iz]) * (0.6 + 0.4 * d)
            head(np.random.default_rng((seed, 0, i, j)), px, pz, rad,
                 max(SMALLEST, min(HEAP, rad * (0.72 + 0.28 * w)) * lift))

    # the few big piles, well apart, in the banks, away from the mountain: broad shoulders, a
    # narrower tower standing out of them, smaller domes on its flanks
    away = ~_grow(land, SHY)
    sites = np.random.default_rng((seed, 1)).uniform(size=(4000, 2)) * (nx, nz)
    piles = []
    for i, (px, pz) in enumerate(sites.tolist()):
        if len(piles) == PILES:
            break
        ix, iz = cell_of(px, pz)
        if amount[ix, iz] < 0.85 or core[ix, iz] < 0.6 or not away[ix, iz]:
            continue
        if any(np.hypot(px - qx, pz - qz) < 60.0 for qx, qz in piles):
            continue
        piles.append((px, pz))
        g = np.random.default_rng((seed, 1, i))
        for n, off, rad, rise, bulge in ((4, (2.0, 6.0), (6.0, 8.5), (3.8, 5.2), 0.6),
                                         (2, (0.0, 2.5), (4.0, 5.5), (0.86 * PILE, PILE), 0.75),
                                         (4, (2.5, 5.5), (2.4, 3.6), (4.8, 6.4), 0.7)):
            for _ in range(n):
                a, s = g.uniform(0.0, 2.0 * np.pi), g.uniform(*off)
                dome(g, px + np.cos(a) * s, pz + np.sin(a) * s, g.uniform(*rad), g.uniform(*rise), bulge)

    # the surf: cloud heaped against whatever stands in the sea
    if land.any():
        shore = _distance(land, 14)                 # 0 on the land, how far out to sea
        coast = land & (_distance(~land, 3) <= 2.5)                     # the land's own last columns
        fold = _blur(land.astype(np.float32), 6)    # over a half in a gully, a tenth off a cape
        # 1 on a shore that faces the wind, -1 in the lee: the cloud is driven up the one and
        # sinks away from the other
        gx_, gz_ = np.gradient(_blur(land.astype(np.float32), 9))
        windward = -(gx_ * WIND[0] + gz_ * WIND[1]) / np.maximum(np.hypot(gx_, gz_), 1e-6)
        drive = 0.25 * np.maximum(windward, 0.0) - 0.12 * np.maximum(-windward, 0.0)
        surf = N.fbm2(X / 23.0, Z / 23.0, seed + 9, octaves=2)
        # the lip: at least one block of cloud over the face against the land all the way round, and
        # on the land's own last columns where they lie under it; no hollow of the swell comes near
        lip = coast | ((shore > 0.0) & (shore <= 1.5))
        top = np.where(lip, np.maximum(top, FOOT + 0.55), top)
        base = np.where(shore <= 6.0, np.maximum(base, MEAN), base)
        # small round lobes along it, so the lip is no ribbon
        step = 3
        gxs, gzs = range(0, nx, step), range(0, nz, step)
        draws = np.random.default_rng((seed, 3)).uniform(size=(len(gxs), len(gzs), 5)).tolist()
        for i, gx in enumerate(gxs):
            for j, gz in enumerate(gzs):
                fx, fz, u, v, w = draws[i][j]
                px, pz = gx + fx * step, gz + fz * step
                ix, iz = cell_of(px, pz)
                if land[ix, iz] or shore[ix, iz] > 3.2 or u > 0.72:
                    continue
                rad = 2.0 + 1.6 * v
                _stamp(top, px, pz, FOOT - 0.25, rad * (0.6 + 0.4 * w) + 0.25, rad, 0.55)
        # the heads of the surf, big where the land folds round them and small off a cape
        zone = (shore > 0.0) & (shore <= 6.5)
        step = 6
        gxs, gzs = range(0, nx, step), range(0, nz, step)
        draws = np.random.default_rng((seed, 2)).uniform(size=(len(gxs), len(gzs), 5)).tolist()
        for i, gx in enumerate(gxs):
            for j, gz in enumerate(gzs):
                fx, fz, u, v, w = draws[i][j]
                px, pz = gx + fx * step, gz + fz * step
                ix, iz = cell_of(px, pz)
                if not zone[ix, iz]:
                    continue
                a = float(np.clip(0.5 + surf[ix, iz] + 1.5 * (fold[ix, iz] - 0.28) + drive[ix, iz], 0.0, 1.0))
                if u > 0.6 + 0.4 * a:
                    continue
                rad = 2.8 + 1.4 * v + 2.2 * a
                head(np.random.default_rng((seed, 2, i, j)), px, pz, rad, min(HEAP, rad * (0.7 + 0.3 * w)))
        # where the surf stands high the cloud banks up further out as well: big heads with a
        # crowd of smaller ones on them, a few to a bay, and none where the sea is near its end
        bank = N.fbm2(X / 41.0, Z / 41.0, seed + 13, octaves=2)
        step = 12
        gxs, gzs = range(0, nx, step), range(0, nz, step)
        draws = np.random.default_rng((seed, 4)).uniform(size=(len(gxs), len(gzs), 5)).tolist()
        for i, gx in enumerate(gxs):
            for j, gz in enumerate(gzs):
                fx, fz, u, v, w = draws[i][j]
                px, pz = gx + fx * step, gz + fz * step
                ix, iz = cell_of(px, pz)
                if shore[ix, iz] < 2.5 or shore[ix, iz] > 13.0:
                    continue
                a = float(np.clip(0.5 + 1.9 * bank[ix, iz] + 1.2 * (fold[ix, iz] - 0.28) + 1.4 * drive[ix, iz], 0.0, 1.0))
                if u > a * a * amount[ix, iz]:
                    continue
                rad = 5.4 + 2.4 * v
                head(np.random.default_rng((seed, 4, i, j)), px, pz, rad,
                     min(HEAP, 0.75 * rad) * (0.8 + 0.2 * w) * (0.7 + 0.3 * a))

        # what is built and ends low in the sea is heaped over: a head on every such column, two
        # blocks over it or more, so a row of them is one long head
        for i, k, y in sunk:
            crest = min(y + 3, LOW) + 0.4
            _stamp(top, i + 0.5, k + 0.5, FOOT - 0.25, crest - (FOOT - 0.25), COVERED, 0.6)
        top = np.where(away, top, np.minimum(top, LOW + 0.45))
    else:
        lip = land

    level, height = _tidy(base, np.minimum(top, PEAK + 0.45), lip)
    return level, height, sea


_TURNS = np.array([(1.0, 1.0), (-1.0, 1.0), (1.0, -1.0), (-1.0, -1.0)]) / np.sqrt(2.0)
_TURNS = np.vstack([_TURNS, [(1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0)]])


def _wave(x, z, seed):
    """Gradient noise, roughly -1..1, one wave to a unit: artkit.noise's, but with the gradient of
    a lattice point taken from _hash3 and not from a shuffled table, so that the sky's shader can
    do the same sum (far_glsl(): c164_wave)."""
    x, z = np.asarray(x, dtype=float), np.asarray(z, dtype=float)
    xf, zf = np.floor(x), np.floor(z)
    i, k = xf.astype(np.int64), zf.astype(np.int64)
    dx, dz = x - xf, z - zf
    u, v = dx * dx * dx * (dx * (dx * 6.0 - 15.0) + 10.0), dz * dz * dz * (dz * (dz * 6.0 - 15.0) + 10.0)

    def corner(ii, kk, ddx, ddz):
        g = _TURNS[(8.0 * _hash3(ii, kk, 0 * ii, seed)).astype(np.int64)]
        return g[..., 0] * ddx + g[..., 1] * ddz

    a = corner(i, k, dx, dz)
    a = a + u * (corner(i + 1, k, dx - 1.0, dz) - a)
    b = corner(i, k + 1, dx, dz - 1.0)
    b = b + u * (corner(i + 1, k + 1, dx - 1.0, dz - 1.0) - b)
    return (a + v * (b - a)) * 1.6


def _waves(x, z, seed):
    """Two octaves of _wave."""
    x, z = np.asarray(x, dtype=float), np.asarray(z, dtype=float)
    return (_wave(x, z, seed) + 0.5 * _wave(2.0 * x, 2.0 * z, seed + 31)) / 1.5


def _face(X, Z, seed):
    """The open sea's face at the columns (X, Z): (core, base). ``core`` is 1 in a bank, where the
    cloud piles up, and 0 in the calm lanes that wind between the banks, which are longer
    north-south than they are wide and take about two thirds of the sea. ``base`` is the
    continuous y of a column's top block where no head stands: low heaps lying side by side on
    long low waves, the banks riding higher. Everything in it is a sum the sky's shader can do as
    well (far_glsl()), since the far sea is painted from it."""
    bend = _waves(X / 90.0, Z / 90.0, seed + 7) * 22.0
    core = N.smoothstep(-0.20, 0.04, _waves((X + bend) / 44.0, Z / 70.0, seed + 1))
    roll = _waves((X + bend) / ROLL[0], Z / ROLL[1], seed + 11)
    return core, MEAN + SWELL * roll + PILLOW * (_heaps(X + 0.5 * bend, Z, seed + 17) - 0.45) + BANK * (core - 0.5)


def _heaps(X, Z, seed):
    """The low heaps the face of the sea is made of: for every column how high the highest of the
    flat domes over it stands, 0 in a crease between two and 1 on the top of a full one. One dome
    to a cell of a grid HEAPS wide, each somewhere in its cell, wider than the cell so that it
    leans on its neighbours, longer along the wind than across it."""
    ci, ck = np.floor(X / HEAPS).astype(np.int64), np.floor(Z / (1.3 * HEAPS)).astype(np.int64)
    out = np.zeros(X.shape)
    for di in (-1, 0, 1):
        for dk in (-1, 0, 1):
            i, k = ci + di, ck + dk
            px = (i + 0.15 + 0.7 * _hash3(i, k, 1, seed)) * HEAPS
            pz = (k + 0.15 + 0.7 * _hash3(i, k, 2, seed)) * 1.3 * HEAPS
            rad = HEAPS * (0.55 + 0.30 * _hash3(i, k, 3, seed))
            full = 0.55 + 0.45 * _hash3(i, k, 4, seed)
            d2 = ((X - px) / rad) ** 2 + ((Z - pz) / (1.3 * rad)) ** 2
            out = np.maximum(out, full * np.sqrt(np.clip(1.0 - d2, 0.0, 1.0)))
    return out


def _shade(h):
    """Light 0..1 per column from the smooth height of its top, lit from the west, low. Level cloud
    takes 0.75 (the second lightest tone) whatever its height. What faces west takes more and what
    faces east less: the steep side of a head by its own slope; the low heaps of the face, whose
    slopes are slight, by the lie of the whole slope, so that a heap is light on its west third and
    dark on its east; the top of a head is level cloud again, so that seen from the west, with the
    light behind the eye, a head is a light side under a darker top and no pale plate. What lies
    lower than the cloud round it is darker: the foot of a head and a crease between two by a
    tone, the floor of a lane walled in by heads as well. What stands over the cloud round it has
    a breath more, and the crowns of the piles catch the light."""
    h = (h - MEAN).astype(np.float32)               # the blur reads zero outside the grid: level cloud

    def westward(a):                                # rising eastwards = facing west
        p = np.pad(a, 1, mode="edge")
        return (p[2:, 1:-1] - p[:-2, 1:-1]) * 0.5

    low = np.clip(1.6 - h, 0.0, 1.0)                # 1 on the face and its heaps, 0 on a head
    turn = np.clip(0.30 * np.tanh(1.3 * westward(h)) + 0.16 * low * np.tanh(LIE * westward(_blur(h, 2))), -0.34, 0.30)
    crease = np.clip((_blur(h, 1) - h - 0.35) / 0.75, 0.0, 1.0)
    walled = np.clip((_blur(h, 4) - h - 0.4) / 1.4, 0.0, 1.0)
    crest = np.clip(h - _blur(h, 3) - 0.5, 0.0, 1.0)
    crown = np.clip((h - (LOW - MEAN)) / 4.0, 0.0, 1.0)
    return 0.75 + turn - 0.22 * crease - 0.18 * walled + 0.10 * crest + 0.12 * crown


# --- the far sea: what is painted where the blocks have ended ----------------------------------------
# The sky's shaders (sky/_shaders.py) paint the sea on below the horizon, and the blocks go into
# that painting between sky/mood's FOG_START and FOG_END. A flat colour there would be a floor; the
# painted sea carries the open face's own shapes instead: far_tone() is the tone of the column
# (x, z) as build() would give it to the face with no head on it and no land near, from the same
# _face(), so that in a calm lane the painting is the blocks' own picture and the blocks end in it
# without a seam. Further out, where a pixel covers several blocks, the tones run together into
# their mean.
FAR_FOLD = 2.4                  # the crease read from the four columns beside one, for build()'s blur over 5 x 5
FAR_LIE = 1.0                   # the lie of the slope read from the two columns beside one, for build()'s blur over 9 x 9
FAR_PIXEL = 600.0               # pixels to a radian: how much sea a pixel covers at a distance
FAR_FINE = (3.0, 7.0)           # the tones are whole while a pixel covers this many blocks, run together from the second on
FAR_MEAN = (0.0, 0.03, 0.22, 0.61, 0.14)    # the share of each tone on the open face: what they run together into


def far_tone(x, z, seed=SEED):
    """The tone (0..4, an index into B.CLOUD) of the far sea's column (x, z): whole numbers or
    numpy arrays of them, scene coordinates."""
    x, z = np.asarray(x, dtype=float), np.asarray(z, dtype=float)

    def height(i, k):
        return np.clip(_face(i, k, seed)[1], TROUGH, MEAN + 1.45) - MEAN

    h, west, east = height(x, z), height(x - 1.0, z), height(x + 1.0, z)
    lie = 0.5 * (east - west)                       # rising eastwards = facing west
    fold = 0.25 * (west + east + height(x, z - 1.0) + height(x, z + 1.0)) - h
    low = np.clip(1.6 - h, 0.0, 1.0)
    turn = np.clip(0.30 * np.tanh(1.3 * lie) + 0.16 * low * np.tanh(LIE * FAR_LIE * lie), -0.34, 0.30)
    crease = np.clip((FAR_FOLD * fold - 0.35) / 0.75, 0.0, 1.0)
    last = len(B.CLOUD) - 1
    return np.clip(np.rint(last * (0.75 + turn - 0.22 * crease)), 0, last).astype(int)


def far_tints():
    """What a tone's colour is of level cloud's (the second lightest tone), per channel; and the
    last row what the far sea's tones come to where they run together."""
    ramp = np.array([P.colour("cloud", i) for i in range(len(B.CLOUD))], dtype=float)
    tints = ramp / ramp[len(B.CLOUD) - 2]
    return np.vstack([tints, np.array(FAR_MEAN) @ tints])


def far_colour(sea, x, z, reach, height, seed=SEED):
    """The far sea's colour before the fog: ``sea`` is level cloud's (sky/mood's "cloud"), (x, z)
    where the line of sight meets the sea's top (numpy arrays, scene coordinates), ``reach`` how
    far along it that is and ``height`` the eye over the sea's top."""
    x, z, reach = np.asarray(x, dtype=float), np.asarray(z, dtype=float), np.asarray(reach, dtype=float)
    tints = far_tints()
    spread = reach * reach / (max(float(height), 0.5) * FAR_PIXEL)     # blocks to a pixel along the line of sight
    t = np.clip((spread - FAR_FINE[0]) / (FAR_FINE[1] - FAR_FINE[0]), 0.0, 1.0)
    blur = t * t * (3.0 - 2.0 * t)
    out = np.empty(x.shape + (3,))
    out[...] = tints[-1]
    fine = blur < 1.0
    if fine.any():
        tone = far_tone(np.floor(x[fine]), np.floor(z[fine]), seed)
        out[fine] = tints[tone] * (1.0 - blur[fine, None]) + tints[-1] * blur[fine, None]
    return out * np.asarray(sea, dtype=float)


FAR_GLSL = """// The far sea's face (sky/cloudsea.py: far_colour(), the same sums in numpy). The tone of the
// column the line of sight meets the sea in, as the blocks of the open sea wear it.
uint c164_bits(int x, int y, int z, int seed) {
    uint h = uint(x) * 374761393u + uint(y) * 668265263u + uint(z) * 2147483647u + uint(seed) * 1274126177u;
    h = (h ^ (h >> 13)) * 1274126177u;
    return h ^ (h >> 16);
}

float c164_hash(int x, int y, int z, int seed) {
    return float(c164_bits(x, y, z, seed) & 0xFFFFFFu) / 16777216.0;
}

float c164_corner(int i, int k, vec2 d, int seed) {
    uint g = (c164_bits(i, k, 0, seed) >> 21) & 7u;
    vec2 turn = g < 4u ? vec2((g & 1u) == 0u ? 0.70710678 : -0.70710678, (g & 2u) == 0u ? 0.70710678 : -0.70710678)
                       : (g == 4u ? vec2(1.0, 0.0) : g == 5u ? vec2(-1.0, 0.0) : g == 6u ? vec2(0.0, 1.0) : vec2(0.0, -1.0));
    return dot(turn, d);
}

float c164_wave(vec2 p, int seed) {
    vec2 f = floor(p);
    ivec2 c = ivec2(f);
    vec2 d = p - f;
    vec2 u = d * d * d * (d * (d * 6.0 - 15.0) + 10.0);
    float a = mix(c164_corner(c.x, c.y, d, seed), c164_corner(c.x + 1, c.y, d - vec2(1.0, 0.0), seed), u.x);
    float b = mix(c164_corner(c.x, c.y + 1, d - vec2(0.0, 1.0), seed), c164_corner(c.x + 1, c.y + 1, d - vec2(1.0, 1.0), seed), u.x);
    return mix(a, b, u.y) * 1.6;
}

float c164_waves(vec2 p, int seed) {
    return (c164_wave(p, seed) + 0.5 * c164_wave(2.0 * p, seed + 31)) / 1.5;
}

float c164_heaps(vec2 p, int seed) {
    const vec2 cell = vec2({heaps}, {heaps_long});
    ivec2 c = ivec2(floor(p / cell));
    float best = 0.0;
    for (int di = -1; di <= 1; di++) {
        for (int dk = -1; dk <= 1; dk++) {
            int i = c.x + di;
            int k = c.y + dk;
            vec2 middle = (vec2(float(i), float(k)) + 0.15 + 0.7 * vec2(c164_hash(i, k, 1, seed), c164_hash(i, k, 2, seed))) * cell;
            float rad = {heaps} * (0.55 + 0.30 * c164_hash(i, k, 3, seed));
            vec2 q = (p - middle) / vec2(rad, 1.3 * rad);
            best = max(best, (0.55 + 0.45 * c164_hash(i, k, 4, seed)) * sqrt(clamp(1.0 - dot(q, q), 0.0, 1.0)));
        }
    }
    return best;
}

// the open face over its mean level at the column p
float c164_face(vec2 p) {
    float bend = c164_waves(p / 90.0, {seed} + 7) * 22.0;
    float t = clamp((c164_waves(vec2((p.x + bend) / 44.0, p.y / 70.0), {seed} + 1) + 0.20) / 0.24, 0.0, 1.0);
    float roll = c164_waves(vec2((p.x + bend) / {roll_x}, p.y / {roll_z}), {seed} + 11);
    float base = {swell} * roll + {pillow} * (c164_heaps(vec2(p.x + 0.5 * bend, p.y), {seed} + 17) - 0.45)
        + {bank} * (t * t * (3.0 - 2.0 * t) - 0.5);
    return clamp(base, {trough}, 1.45);
}

// sea: level cloud's colour; at: where the line of sight meets the sea's top, on the map; reach: how
// far along it that is; height: the eye over the sea's top
vec3 c164_far_sea(vec3 sea, vec2 at, float reach, float height) {
    float spread = reach * reach / (max(height, 0.5) * {pixel});
    float t = clamp((spread - {fine_0}) / ({fine_1} - {fine_0}), 0.0, 1.0);
    float blur = t * t * (3.0 - 2.0 * t);
    vec3 tint = {tint_mean};
    if (blur < 1.0) {
        vec2 p = floor(at - {origin});
        float h = c164_face(p);
        float west = c164_face(p - vec2(1.0, 0.0));
        float east = c164_face(p + vec2(1.0, 0.0));
        float lie = 0.5 * (east - west);
        float fold = 0.25 * (west + east + c164_face(p - vec2(0.0, 1.0)) + c164_face(p + vec2(0.0, 1.0))) - h;
        float turn = clamp(0.30 * tanh(1.3 * lie) + 0.16 * clamp(1.6 - h, 0.0, 1.0) * tanh({lie} * lie), -0.34, 0.30);
        float crease = clamp(({fold} * fold - 0.35) / 0.75, 0.0, 1.0);
        int tone = int(clamp(floor({last} * (0.75 + turn - 0.22 * crease) + 0.5), 0.0, {last}));
        vec3 own = {tints};
        tint = mix(own, tint, blur);
    }
    return sea * tint;
}
"""


def far_glsl(origin=(0.0, 0.0), seed=SEED):
    """The GLSL of the far sea for sky/_shaders.py: defines
    vec3 c164_far_sea(vec3 sea, vec2 at, float reach, float height), far_colour() in the shader's
    words. ``origin`` is where the scene's (0, 0) stands on the map."""
    def f(x):
        text = repr(round(float(x), 6))
        return text if ("." in text or "e" in text) else text + ".0"

    def vec3(c):
        return "vec3(" + ", ".join(f(v) for v in c) + ")"

    tints = far_tints()
    last = len(B.CLOUD) - 1
    own = "".join(f"tone == {i} ? {vec3(tints[i])} : " for i in range(last)) + vec3(tints[last])
    values = dict(heaps=f(HEAPS), heaps_long=f(1.3 * HEAPS), seed=str(int(seed)), roll_x=f(ROLL[0]), roll_z=f(ROLL[1]),
                  swell=f(SWELL), pillow=f(PILLOW), bank=f(BANK), trough=f(TROUGH - MEAN), pixel=f(FAR_PIXEL),
                  fine_0=f(FAR_FINE[0]), fine_1=f(FAR_FINE[1]), tint_mean=vec3(tints[-1]),
                  origin=f"vec2({f(origin[0])}, {f(origin[1])})", lie=f(LIE * FAR_LIE), fold=f(FAR_FOLD), last=f(last), tints=own)
    text = FAR_GLSL
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    return text


def build(canvas, origin=(0, 0, 0), *, seed=SEED, dress=None):
    """Lay the sea of clouds into the canvas. Places blocks only, so it returns 0 display entities."""
    if not (DRESS if dress is None else dress):
        return 0
    names = list(B.CLOUD)                           # dark..light, as the tone index runs
    mine = [k for k, state in canvas.b.items() if state.partition("[")[0].split(":")[-1] in names]
    # The sea is laid where something stands in it. Every category's test scene calls the sky's
    # build() for its light sources (INTERFACE 4); one that builds on the terraces alone, nothing
    # of it reaching down to the sea's face, is no mountain and is left as it is. A scene that
    # wants the sea all the same says dress=True.
    cloud = set(mine)
    if dress is None and not any(k[1] - origin[1] <= MEAN for k in canvas.b if k not in cloud):
        return 0
    # The sea is laid once: a sheet of cloud tones put down earlier (site/terrain's stand-in for this
    # package) is taken up.
    for key in mine:
        del canvas.b[key]

    x0, z0, nx, nz = _grid()
    y0, y1 = FLOOR_Y - 1, PEAK + 2
    ny = y1 - y0 + 1
    occ, whole, joins, high, roof = _others(canvas, origin, (x0, z0), (nx, ny, nz), y0)
    kept = _grow(joins, CLEAR)                      # the room given to what would join on to a cloud

    # The land: columns where somebody's block stands in the cloud, from level cloud up, and what
    # those wall in: the hollow of the mountain. What merely has a bridge over it is not walled in
    # and keeps its cloud, and so does a pocket less than five columns across (the slot between two
    # rails, a cleft in the shore): the hollow is what is left of the walled-in columns after two
    # are taken off every rim. Under the land the sea goes on for a few columns only: far enough in
    # to lie under a trestle or a landing stage, and no further under the mountain.
    band = occ[:, MEAN - y0:, :].any(axis=1)
    shut = ~band & ~_reach(~band)
    inside = shut & _grow(~_grow(~shut, 2), 2)
    land = band | inside
    dry = inside | (land & (_distance(~land, 6) > 4.5))
    # what is built and ends low in the sea: the columns whose highest block is a thin one near the face
    j = np.clip(high - y0, 0, ny - 1)
    thin = occ[np.arange(nx)[:, None], j, np.arange(nz)[None, :]] & ~whole[np.arange(nx)[:, None], j, np.arange(nz)[None, :]]
    sunk = thin & (high >= SUNK[0]) & (high <= SUNK[1]) & ~dry
    level, height, sea = _field(seed, land, [(i, k, int(high[i, k])) for i, k in zip(*np.nonzero(sunk))])
    here = sea & ~dry
    # A ledge of somebody's whole blocks that ends low and bare beside the sea -- the foot of the
    # rock, the head of a pier -- is lapped over: one block of cloud on it at least. Bare, with
    # heads standing two blocks over it on every side, it is a hole nobody climbs out of (the
    # walk-out found one at (-19, 30)); under cloud it is the sea, and whoever stands on the sea is
    # sent back (common/export). No cloud near the land is higher than LOW, so no bare block is
    # left more than a step under the cloud beside it.
    ledge = here & (roof == high) & (high >= TROUGH) & (high <= LEDGE)
    level = np.where(ledge, np.maximum(level, high + 1), level)
    height = np.where(ledge, np.maximum(height, high + 1.0), height)

    # Only empty cells, clear of what would join on. Where the sea's own level is open all the way
    # from outside (the open sea, and under a girder that bridges it) a column is cloud from the
    # hollows' level up to its top; elsewhere (on the rock's last columns, in a pocket of the shore)
    # there is none under a whole block of somebody else: the hollow of the mountain stays empty.
    ys = np.arange(ny)[None, :, None] + y0
    wet = _reach(~whole[:, MEAN - y0, :])
    under = ys < roof[:, None, :]
    solid = here[:, None, :] & (ys >= TROUGH) & (ys <= level[:, None, :]) & ~occ & ~kept
    solid &= wet[:, None, :] | ~under

    # the sunk floor: where the sea was opened beside a wall or a fence and nothing stands in the
    # column, the eye would drop through to the void; a dark course of cloud lies there, low in the gap
    floor = np.zeros_like(solid)
    floor[:, FLOOR_Y - y0, :] = here & ~solid.any(axis=1) & ~occ.any(axis=1)
    floor &= ~kept

    # only what can be seen from above or from the side is placed: a cell with cloud or whole rock
    # over it and on all four sides is left out. What is built hides nothing (a rail, a bar, a step
    # lets the eye past), nor does a thin layer of snow.
    p = np.pad(solid | whole, 1)
    west_open, east_open = ~p[:-2, 1:-1, 1:-1], ~p[2:, 1:-1, 1:-1]
    side_open = ~p[1:-1, 1:-1, :-2] | ~p[1:-1, 1:-1, 2:]
    up_open = ~p[1:-1, 2:, 1:-1]
    skin = solid & (up_open | west_open | east_open | side_open)

    # The light of a column is that of its top block; the land counts as a block over the face, as
    # the lip against it is, so the lip is lit by the side the sea lies on. A cell seen from the side
    # only takes its column's light, more of it facing west, less facing east, and less the further
    # down the side it lies.
    light = _shade(np.where(solid.any(axis=1), height, np.where(land, MEAN + 1.0, float(MEAN))))
    light = light[:, None, :] + np.zeros((1, ny, 1), dtype=np.float32)
    turn = np.where(west_open, 0.10, np.where(side_open, -0.06, -0.16))
    light = np.where(up_open, light, light + turn - 0.05 * np.clip(level[:, None, :] - ys, 0, 8))

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


# --- the resource pack: the five tone pictures, the five blocks, the cloud layer's picture -----------
def pack(pack_dir):
    out = []
    for i in range(len(B.CLOUD)):
        K.paint(pack_dir, f"sky_cloud_{i}", _tone(i))
    for i, block in enumerate(B.CLOUD):
        mapping = {ref: f"sky_cloud_{i}" for ref in respack.block_pictures(K.game(), block)}
        out.append(K.redirect(pack_dir, block, mapping, shade=False, ao=False))
    respack.texture(pack_dir, "environment/clouds", _no_clouds())
    out.append("clouds.png: blanked (the game draws no cloud layer; the sea is blocks)")
    return out
