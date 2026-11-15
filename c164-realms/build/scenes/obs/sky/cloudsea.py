"""Work package sky/cloudsea: the sea of clouds the mountain stands in (plan 3.2, 10; card
plan/packages/sky/cloudsea.md; plan/parts/sky.md 4; c219's terrain review #163.1; the ruling on the
seam in plan/roles/A0-director.md 4).

The face of the sea is the game's own cloud layer. clouds.png is painted shut, so the layer is one
closed sheet, flat and of one colour, with its upper face at scene y -28 (sky/mood.CLOUD_TOP) as far
as the game draws clouds. A sheet has no rim at the view distance and nothing to line up with, and
the game cuts it where rock or iron stands in it, so it lies against everything without a gap. That
sheet is the calm sea, out to the horizon. Blocks are only what the sheet cannot be:

    the surf    cloud heaped against whatever stands in the sea: a lip all the way round, high in
                the gullies and low on the capes, so the line where rock and sea meet is cloud and
                is never the sheet's level cut;
    the heads   cumulus standing out of the face to y -24: steep round domes, the bigger ones with
                smaller ones crowded on them, packed side by side in banks that lie north-south,
                across the way to the afterglow, with the calm sea between;
    the piles   a few towers in the banks, to y -20;
    the deck    one course of cloud under the face (its top a block lower, lower again in its
                hollows). Nobody sees it through the sheet. It is the sea for a player who has
                switched the game's clouds off, and it keeps the stars from showing through the
                sheet near the mountain.

Three versions, compared on the real client (the offline renderer draws the fog but neither the
cloud layer nor the afterglow; scenes/obs_sky_cloudsea/preview.py lays the layer into its picture
by the game's arithmetic, as a forecast; the card is settled on S1's pictures):

    "a"  the sheet alone   no blocks. Rock and track meet the sheet's level cut, and with the
                           player's clouds off nothing is left.
    "b"  blocks alone      the deck is the sea, its face a block lower; clouds.png is blanked and
                           the distance is left to the fog.
    "c"  both (default)    what the master scene builds. With the player's clouds off it is "b";
                           on "fast" the game draws the sheet four blocks lower, under the deck,
                           and the deck is the sea as far as it reaches.

Where the blocks may stand is ruled by the view distance (12 chunks: the board's). The game takes
blocks into the fog colour between 172.8 and 192 blocks whatever the fog is set to, and draws none
beyond the last loaded chunk; the sheet it goes on drawing. So a head must never stand where
somebody sees it from further than that:

  - from the ground (SEEN): for every column, how far away the farthest person stands who can see a
    head there, worked out from the skeleton's flats and a plain model of the slopes between them.
    The banks thin out where that passes 150 blocks and end by 166.
  - from the air (AERIAL): the board's camera V12 stands so far out that the far shore is at its
    wall of fog. A lane of calm sea lies where that camera loses the blocks (LOST), so that it sees
    no head darken there and none cut off at a chunk's edge; the banks beyond the lane it does not
    load, and the people on the west rail do.
  - the deck is laid REACH blocks out from where anyone can stand, so its end is behind the wall of
    fog from every flat; under the sheet it could end anywhere.

Only empty cells are filled. The sea lies right against whatever stands in it: the mountain's rock
and snow (ROCK, COVER), and what is built -- the legs and girders of the cable trestle, piers,
steps -- so a track that runs down into the cloud is lost in it. A track or a wall that is to be
lost in the sea has to be carried down to y -31, under the deck. The one exception is what would
grow a thick arm towards a cloud beside it when the scene is placed (walls and fences, JOINS): from
those the sea keeps CLEAR empty cells, with a sunk floor of cloud under the gap. A block whose top
would lie in the sheet's face (y -29: the mountain's sunk rim) gets a block of cloud on it, so the
two faces never flicker in each other.

The five tones are the occupancy roles B.CLOUD (dark to light, palette RAMPS["cloud"]). This package
paints them (A0's exception to "only materials paints blocks": the cloud colour is tuned with the
light of the sky), through materials/_kit like everyone else. The pictures are flat tones named
sky_cloud_0..4 and the game's own face shading is turned off (shade=False, ao=False): which tone a
block wears is baked here from the shape, lit from the west where the afterglow is. The sheet shows
the second lightest tone (sky/mood's cloud colour is that tone as the blue hour lights it), so that
is what low cloud wears and where a head's lit foot melts into the sea; the crown and the west side
of a head are the lightest, its lee side and its creases the two below. There is no dither: the
tones lie in clean bands, as pixel art shades a ball. The deck wears the sheet's tone near the
mountain and sinks to the tone nearest the fog's by its end.
"""
import math
from functools import lru_cache

import numpy as np

from artkit import noise as N
from artkit import respack
from artkit.clouds import _blur, _hash3

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..materials import _kit as K
from . import mood

# The blocks this package paints; nobody else may (the stand-in reads this and lets them go).
BLOCKS = K.blocks(B.CLOUD)

VERSIONS = ("a", "b", "c")
DEFAULT = "c"

FACE = mood.CLOUD_TOP           # -28: scene y of the sea's face, the upper face of the game's cloud layer
FOOT = FACE - 0.5               # a height field at or over this puts a block above the face
DECK_Y = FACE - 2               # the deck's blocks: their top is one block under the face
HOLLOW_Y = DECK_Y - 1           # ... and one lower in the deck's hollows
FLOOR_Y = DECK_Y - 2            # the sunk floor under a gap beside a wall or a fence
HEAP = 4.6                      # a head of cloud stands this far out of the face (to y -24)
PILE = 8.0                      # the few big piles (to y -20, card)
PILES = 7                       # how many of those
PEAK = -20                      # nothing is higher than this
CLEAR = 1                       # empty cells kept between the sea and what would join on to it
SEED = 41

# What stands in the sea. ROCK is the mountain's bare rock and snow: whole blocks, which hide the
# cloud that lies behind them. COVER lies on the rock in thin layers and hides nothing. JOINS (by the
# ending of the name) are the built things that grow a thick arm towards a whole block beside them
# when a scene is placed: the game shapes them from their neighbours. The sea keeps CLEAR cells away
# from those and lies right against everything else. Bars and panes join on as well, but with a thin
# arm at the cloud's own level that ends in the cloud's face; a well round every leg of the trestle
# would show far more.
ROCK = (B.ROCK_STONE.block, B.ROCK_ANDESITE.block, B.ROCK_DEEPSLATE, B.ROCK_COBBLED.block, B.TUFF.block, B.SNOW)
COVER = (B.SNOW_LAYER,)
JOINS = ("_wall", "_fence")

# The view distance the map is shown at and what follows from it (26.3: fog.glsl, FogRenderer,
# ChunkTrackingView). Blocks: the fog of the view distance runs from 90% of it to all of it, by the
# distance in plan; chunks are loaded at most a chunk further.
VIEW = 12 * 16.0                # 192
REACH = VIEW + 12.0             # the deck ends this far from where anyone can stand
SEEN = (150.0, 166.0)           # the banks thin out between these distances to their farthest onlooker
HEAD_Y = FACE + 6               # a head counts as seen when the eye reaches this height over its column
FALL = 0.72                     # the mountain's slopes in the sight model: blocks down per block out (site/terrain)
CRAG = 2.0                      # ... taken this much lower: gullies let the eye past
# The board's aerial camera (tools/boardshots.py; the skeleton's V12 once it holds one): where it
# stands in plan, and from where to where it loses the blocks (the wall of fog is whole at VIEW, the
# last loaded chunk ends at most 16 further; a head's own width on both sides).
AERIAL = tuple(float(v) for v in getattr(S, "V12", {}).get("pos", (S.EAST_EDGE_X + 20.0, 90.0, S.Z_SOUTH + 46.0)))[::2]
LOST = (VIEW - 6.0, VIEW + 22.0)
LOST_EDGE = 7.0                 # the lane's banks: the heads thin out over this much on either side

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


# --- the game's cloud layer --------------------------------------------------------------------------
def _clouds_sheet(blank=False):
    """clouds.png, 256x256, one pixel a cell of 12x4x12 blocks: every cell cloud (the game takes the
    colour from cloud_color and reads this picture for where cloud is), or none at all for "b"."""
    out = np.zeros((256, 256, 4), dtype=np.uint8)
    out[..., :3] = 255
    out[..., 3] = 0 if blank else 255
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


def _ground(X, Z):
    """The sight model's mountain: every flat, falling away at FALL on all sides, the main block
    standing on it up to its roof terrace. The slopes are taken lower than the real ones by CRAG,
    so the model hides a little less than the rock will."""
    (cx, cz), r = S.SUNSET_PLATFORM["centre"], S.SUNSET_PLATFORM["radius"]
    g = S.GROUND - FALL * np.maximum(np.hypot(X - cx, Z - cz) - r, 0.0)
    for flat in _flats():
        g = np.maximum(g, flat[4] - FALL * _off(flat, X, Z))
    g = g - CRAG * np.minimum(_hull(X, Z) / 3.0, 1.0)
    block = (X >= S.WALL_W) & (X <= S.WALL_E) & (Z >= S.Z_NORTH) & (Z <= S.Z_SOUTH)
    return np.where(block, float(S.ROOF_STAND), g)


def _eyes(step=6.0):
    """Eyes along the rim of every flat and of the roof terrace."""
    out = []
    for x0, z0, x1, z1, feet in _flats() + [(S.WALL_W, S.Z_NORTH, S.WALL_E, S.Z_SOUTH, S.ROOF_STAND)]:
        xs = np.linspace(x0 + 0.5, x1 + 0.5, max(2, int(round((x1 - x0) / step)) + 1))
        zs = np.linspace(z0 + 0.5, z1 + 0.5, max(2, int(round((z1 - z0) / step)) + 1))
        out += [(x, feet + S.EYE, z) for x in xs for z in (zs[0], zs[-1])]
        out += [(x, feet + S.EYE, z) for z in zs[1:-1] for x in (xs[0], xs[-1])]
    (cx, cz), r = S.SUNSET_PLATFORM["centre"], S.SUNSET_PLATFORM["radius"]
    for a in np.linspace(0.5 * np.pi, 1.5 * np.pi, 13):
        out.append((cx + (r - 1.0) * math.cos(a), S.GROUND + S.EYE, cz + (r - 1.0) * math.sin(a)))
    return out


def _grid():
    """The columns the sea may use, (x0, z0, nx, nz): out to the deck's end and a margin."""
    (cx, cz), r = S.SUNSET_PLATFORM["centre"], S.SUNSET_PLATFORM["radius"]
    flats = _flats()
    pad = int(REACH) + 14
    x0, x1 = min([cx - r] + [f[0] for f in flats]) - pad, max(f[2] for f in flats) + pad
    z0, z1 = min([cz - r] + [f[1] for f in flats]) - pad, max([cz + r] + [f[3] for f in flats]) + pad
    return x0, z0, x1 - x0 + 1, z1 - z0 + 1


@lru_cache(maxsize=None)
def _sight():
    """Per column: how far away the farthest person stands who sees a head of cloud there (0 where
    the mountain hides it from everybody, twice the view distance where it is too far out for
    anybody). Rays from every eye, a degree and a bit apart; a head is seen where the ground between
    does not rise over the line from the eye to HEAD_Y."""
    x0, z0, nx, nz = _grid()
    X, Z = np.meshgrid(np.arange(nx) + x0, np.arange(nz) + z0, indexing="ij")
    ground = _ground(X, Z)
    q = 6                                           # the rays are gathered in cells this wide
    far = np.zeros((nx // q + 1, nz // q + 1))
    turn = np.linspace(0.0, 2.0 * np.pi, 300, endpoint=False)
    out = np.arange(3.0, VIEW + 0.5, 3.0)
    for ex, ey, ez in _eyes():
        i = np.floor(ex + np.cos(turn)[:, None] * out).astype(int) - x0
        j = np.floor(ez + np.sin(turn)[:, None] * out).astype(int) - z0
        ok = (i >= 0) & (i < nx) & (j >= 0) & (j < nz)
        i, j = np.clip(i, 0, nx - 1), np.clip(j, 0, nz - 1)
        rise = (ground[i, j] - ey) / out            # how steeply the ground stands over the eye
        over = np.maximum.accumulate(rise, axis=1)
        over = np.concatenate([np.full((len(turn), 1), -np.inf), over[:, :-1]], axis=1)
        seen = ok & ((HEAD_Y - ey) / out > over)
        np.maximum.at(far, (i[seen] // q, j[seen] // q), np.broadcast_to(out, i.shape)[seen])
    mid = _hull(((np.arange(far.shape[0]) + 0.5) * q + x0)[:, None], ((np.arange(far.shape[1]) + 0.5) * q + z0)[None, :])
    far = np.where((far == 0.0) & (mid > 40.0), 2.0 * VIEW, far)
    p = np.pad(far, 1, mode="edge")                 # the rays are a sample: a cell takes its neighbours' too
    far = np.max([p[a:a + far.shape[0], b:b + far.shape[1]] for a in range(3) for b in range(3)], axis=0)
    fx, fz = (np.arange(nx) + 0.5) / q - 0.5, (np.arange(nz) + 0.5) / q - 0.5
    a, b = np.clip(np.floor(fx).astype(int), 0, far.shape[0] - 2), np.clip(np.floor(fz).astype(int), 0, far.shape[1] - 2)
    u, v = np.clip(fx - a, 0.0, 1.0)[:, None], np.clip(fz - b, 0.0, 1.0)[None, :]
    a, b = a[:, None], b[None, :]
    return ((far[a, b] * (1 - u) + far[a + 1, b] * u) * (1 - v) + (far[a, b + 1] * (1 - u) + far[a + 1, b + 1] * u) * v)


def _amount(X, Z):
    """How much of the banks a column may carry, 0..1: all of them where every onlooker is near,
    none where one of them would see a head beyond the wall of fog or in the board camera's lane."""
    lit = N.smoothstep(SEEN[1], SEEN[0], _sight())
    lost = np.hypot(X - AERIAL[0], Z - AERIAL[1])
    lane = N.smoothstep(LOST[0] - LOST_EDGE, LOST[0], lost) * N.smoothstep(LOST[1] + LOST_EDGE, LOST[1], lost)
    return lit * (1.0 - lane)


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


def _others(canvas, origin, lo, shape, y0):
    """(occ, rock, whole, joins): the cells of the box that hold a block of somebody else; which of
    those are the mountain's rock and snow; which of these are whole blocks, hiding what is behind
    them; and which cells hold something that would join on to a cloud (box indices; the box starts
    at scene (lo[0], y0, lo[1]))."""
    ox, oy, oz = origin
    nx, ny, nz = shape
    x0, z0 = lo
    occ, rock, whole, joins = (np.zeros(shape, dtype=bool) for _ in range(4))
    keys = np.array(list(canvas.b.keys()), dtype=np.int64).reshape(-1, 3)
    if len(keys):
        a, b, c = keys[:, 0] - ox - x0, keys[:, 1] - oy - y0, keys[:, 2] - oz - z0
        ok = (a >= 0) & (a < nx) & (b >= 0) & (b < ny) & (c >= 0) & (c < nz)
        occ[a[ok], b[ok], c[ok]] = True
        for key, i, j, k in zip(keys[ok].tolist(), a[ok].tolist(), b[ok].tolist(), c[ok].tolist()):
            name = canvas.b[tuple(key)].partition("[")[0].split(":")[-1]
            if name in ROCK:
                rock[i, j, k] = whole[i, j, k] = True
            elif name in COVER:
                rock[i, j, k] = True
            elif name.endswith(JOINS):
                joins[i, j, k] = True
    return occ, rock, whole, joins


def _field(seed, land):
    """The block sea as height fields: (top, hollow, deck, dusk). ``top`` is the continuous height
    of what stands out of the face per column (-inf where nothing does), ``hollow`` says where the
    deck lies a block lower, ``deck`` where there is deck at all, ``dusk`` how far the deck has sunk
    towards the fog's tone there (0 near the mountain, 1 at its end). ``land`` marks the columns
    where something stands in the cloud: the sea heaps up along it and keeps its piles away from it."""
    x0, z0, nx, nz = _grid()
    X, Z = np.meshgrid(np.arange(nx) + x0, np.arange(nz) + z0, indexing="ij")

    hull = _hull(X, Z)
    wobble = N.fbm2(X / 47.0, Z / 47.0, seed + 5, octaves=3)           # no edge is a ruled line
    deck = hull - 14.0 * wobble < REACH
    dusk = N.smoothstep(96.0, 168.0, hull - 22.0 * wobble)
    hollow = N.fbm2(X / 58.0, Z / 58.0, seed + 2, octaves=2) < -0.16
    amount = _amount(X, Z)
    # where the cloud piles up: banks that lie north-south, bent a little, about half of the sea;
    # 1 in a bank, 0 in the calm sea that winds between them
    bend = N.fbm2(X / 90.0, Z / 90.0, seed + 7, octaves=2) * 26.0
    core = N.smoothstep(-0.10, 0.08, N.fbm2((X + bend) / 60.0, Z / 100.0, seed + 1, octaves=2))
    # how hard it boils: the heads stand high here and lie low and woolly there
    vigour = N.smoothstep(-0.25, 0.25, N.fbm2(X / 44.0, Z / 44.0, seed + 3, octaves=2))

    top = np.full((nx, nz), -np.inf)

    def cell_of(px, pz):
        return min(nx - 1, max(0, int(px))), min(nz - 1, max(0, int(pz)))

    def dome(g, px, pz, rad, rise, bulge=None):     # rooted a little under the face
        _stamp(top, px, pz, FOOT - 0.25, rise + 0.25, rad, g.uniform(0.5, 0.8) if bulge is None else bulge)

    def head(g, px, pz, rad, rise):
        """A head of cloud, shaped by the random numbers of ``g``. A small one is one dome; a
        middling one carries smaller domes on its flanks; a big one is a low cushion with a crowd
        of domes on it, so no top is a table."""
        if rad < 4.5:
            kids, spread, size, high = int(g.integers(0, 2)), (0.6, 1.0), (0.5, 0.75), (0.55, 0.9)
        elif rad < 6.5:
            kids, spread, size, high = int(g.integers(1, 4)), (0.5, 1.0), (0.45, 0.75), (0.6, 1.0)
        else:
            kids, spread, size, high = int(g.integers(5, 9)), (0.1, 0.9), (0.3, 0.5), (0.8, 1.0)
        dome(g, px, pz, rad, rise if rad < 6.5 else 0.66 * rise)
        for _ in range(kids):
            a, s = g.uniform(0.0, 2.0 * np.pi), g.uniform(*spread)
            dome(g, px + np.cos(a) * s * rad, pz + np.sin(a) * s * rad, rad * g.uniform(*size), rise * g.uniform(*high))

    # Every head has random numbers of its own, by the cell of the grid it is drawn in (the piles by
    # their place in the list of sites tried): when somebody builds or digs at the shore, or the
    # board's camera moves, the sea changes there and stays as it was everywhere else.

    # the heads: packed side by side in the banks, a few standing alone in the calm sea. They do
    # not look at the land, so they stand where they stand whatever is built.
    cell = 8
    gxs, gzs = range(0, nx, cell), range(0, nz, cell)
    draws = np.random.default_rng((seed, 0)).uniform(size=(len(gxs), len(gzs), 6)).tolist()
    for i, gx in enumerate(gxs):
        for j, gz in enumerate(gzs):
            fx, fz, u, v, w, t = draws[i][j]
            px, pz = gx + fx * cell, gz + fz * cell
            ix, iz = cell_of(px, pz)
            d, c = amount[ix, iz], core[ix, iz]
            if d <= 0.0 or u > d ** 0.8 * (0.02 + 0.88 * c):
                continue                            # thinned out in the calm sea and towards the banks' end
            rad = (3.0 + 4.4 * v ** 1.5) * (0.8 + 0.2 * d) * (0.85 + 0.3 * c)
            if c > 0.8 and t > 0.88:
                rad = 8.0 + 28.0 * (t - 0.88)       # the broad cushions in the heart of a bank
            high = HEAP * (0.45 + 0.55 * vigour[ix, iz]) * (0.7 + 0.3 * w)
            head(np.random.default_rng((seed, 0, i, j)), px, pz, rad, min(high, rad * (0.55 + 0.35 * w)))

    # the few big piles, well apart, in the banks, away from the mountain: broad shoulders, a
    # narrower tower standing out of them, smaller domes on its flanks
    away = ~_grow(land, 28)
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
        surf = N.fbm2(X / 23.0, Z / 23.0, seed + 9, octaves=2)
        # the lip: at least one block of cloud against the land all the way round, and on the
        # land's own last columns where they lie under the face
        top = np.where(coast | ((shore > 0.0) & (shore <= 1.5)), np.maximum(top, FOOT + 0.55), top)
        # small lobes along it, so the lip is no ribbon
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
                _stamp(top, px, pz, FOOT - 0.25, 0.85 + 1.1 * w + 0.25, 1.7 + 1.7 * v, 0.55)
        # the heads of the surf, high where the land folds round them
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
                a = float(np.clip(0.5 + surf[ix, iz] + 1.5 * (fold[ix, iz] - 0.28), 0.0, 1.0))
                if u > 0.6 + 0.4 * a:
                    continue
                rise = 1.5 + (HEAP - 1.5) * a * (0.75 + 0.25 * w)
                if a > 0.8 and w > 0.35:
                    rise += 1.9 * w * (a - 0.8) / 0.2                   # the highest, to about y -22
                head(np.random.default_rng((seed, 2, i, j)), px, pz, min(6.4, 3.3 + 2.8 * v + 1.2 * a), rise)
        # where the surf stands high the cloud banks up further out as well: broad cushions with a
        # crowd of domes on them, a few to a bay, and none where a head may not stand
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
                a = float(np.clip(0.5 + 1.9 * bank[ix, iz] + 1.2 * (fold[ix, iz] - 0.28), 0.0, 1.0))
                if u > a * a * amount[ix, iz]:
                    continue
                head(np.random.default_rng((seed, 4, i, j)), px, pz, 7.0 + 4.5 * v, (2.6 + (HEAP - 2.6) * a) * (0.8 + 0.2 * w))

    top = np.minimum(top, PEAK + 0.45)
    return top, hollow, deck, dusk


def _shade(top, has):
    """Light 0..1 per column from the continuous height field, lit from the west and from above. Low
    cloud takes the face's own light (0.75: the tone the sheet shows); on a head the light climbs
    with the height, more on the west side, less on the lee side and in the creases."""
    h = np.where(has, top, FACE - 0.2).astype(np.float32)

    def westward(a):                                # rising eastwards = facing west
        p = np.pad(a, 1, mode="edge")
        return (p[2:, 1:-1] - p[:-2, 1:-1]) * 0.5

    crest = h - _blur(h, 3)                                            # over its surroundings or under
    alt = np.clip((h - FOOT) / HEAP, 0.0, 1.6)
    return (0.66 + 0.22 * alt + 0.30 * np.tanh(1.1 * westward(h)) + 0.12 * np.tanh(2.5 * westward(_blur(h, 5)))
            + 0.12 * np.tanh(1.4 * crest))


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
    if version == "a":                              # the sheet alone: no blocks
        return 0

    x0, z0, nx, nz = _grid()
    y0, y1 = FLOOR_Y - 1, PEAK + 2
    ny = y1 - y0 + 1
    occ, rock, whole, joins = _others(canvas, origin, (x0, z0), (nx, ny, nz), y0)
    kept = _grow(joins, CLEAR)                      # the room given to what would join on to a cloud

    # The land: columns where somebody's block stands in the cloud band, and what those wall in: the
    # hollow of the mountain. What merely has a bridge over it is not walled in and keeps its cloud,
    # and so does a pocket less than five columns across (the slot between two rails, a cleft in the
    # shore): the hollow is what is left of the walled-in columns after two are taken off every rim.
    band = occ[:, DECK_Y - y0:, :].any(axis=1)
    shut = ~band & ~_reach(~band)
    inside = shut & _grow(~_grow(~shut, 2), 2)
    top, hollow, deck, dusk = _field(seed, band | inside)
    has = (top >= FOOT) & ~inside
    tops = np.where(has, np.floor(top + 0.5), y0 - 1).astype(np.int64)
    floor_y = np.where(hollow, HOLLOW_Y, DECK_Y)
    deck = deck & ~inside

    # only empty cells, clear of what would join on, and not in the hollow under a crust of rock:
    # what stands out of the face, down to the deck's hollows, and the deck's one course
    ys = np.arange(ny)[None, :, None] + y0
    heap = has[:, None, :] & (ys >= HOLLOW_Y) & (ys <= tops[:, None, :])
    solid = (heap | (deck[:, None, :] & (ys == floor_y[:, None, :]))) & ~occ & ~kept
    solid &= ~np.flip(np.logical_or.accumulate(np.flip(rock, 1), axis=1), 1)
    # a block of somebody else whose top lies in the sheet's face is covered
    f = FACE - y0
    awash = occ[:, f - 1, :] & ~occ[:, f:, :].any(axis=1) & ~inside
    solid[:, f, :] |= awash & ~kept[:, f, :]

    # the sunk floor: where the deck was opened beside a wall or a fence and nothing stands in the
    # column, the eye would drop through to the void; a dark course of cloud lies there, low in the gap
    floor = np.zeros_like(solid)
    floor[:, FLOOR_Y - y0, :] = deck & ~solid.any(axis=1) & ~occ.any(axis=1)
    floor &= ~kept

    # only what can be seen from above or from the side is placed: a cell with cloud or whole rock
    # over it and on all four sides is left out. What is built hides nothing (a rail, a bar, a step
    # lets the eye past), nor does a thin layer of snow.
    p = np.pad(solid | whole, 1)
    west_open, east_open = ~p[:-2, 1:-1, 1:-1], ~p[2:, 1:-1, 1:-1]
    side_open = ~p[1:-1, 1:-1, :-2] | ~p[1:-1, 1:-1, 2:]
    up_open = ~p[1:-1, 2:, 1:-1]
    skin = solid & (up_open | west_open | east_open | side_open)

    # a cell seen from the side only takes its column's light, more of it facing west, less facing
    # east, and less the further down the side it lies. The deck: the face's light, a tone less in
    # its hollows, and both sinking to the fog's tone towards its end.
    light = _shade(top, has)[:, None, :] + np.zeros((1, ny, 1), dtype=np.float32)
    turn = np.where(west_open, 0.10, np.where(side_open, -0.06, -0.16))
    light = np.where(up_open, light, light + turn - 0.05 * np.clip(tops[:, None, :] - ys, 0, 8))
    calm = np.clip(0.75 - 0.25 * hollow - 0.5 * dusk, 0.25, 0.75)
    light = np.where(has[:, None, :] | (ys > floor_y[:, None, :]), light, calm[:, None, :])

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
def pack(pack_dir, version=DEFAULT):
    out = []
    for i in range(len(B.CLOUD)):
        K.paint(pack_dir, f"sky_cloud_{i}", _tone(i))
    for i, block in enumerate(B.CLOUD):
        mapping = {ref: f"sky_cloud_{i}" for ref in respack.block_pictures(K.game(), block)}
        out.append(K.redirect(pack_dir, block, mapping, shade=False, ao=False))
    blank = version == "b"
    respack.texture(pack_dir, "environment/clouds", _clouds_sheet(blank=blank))
    out.append("clouds.png: " + ("blanked (block clouds only)" if blank else "closed, one sheet (the sea's face)"))
    return out
