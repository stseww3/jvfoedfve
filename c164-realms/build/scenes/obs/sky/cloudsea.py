"""Work package sky/cloudsea: the sea of clouds the mountain stands in (plan 3.2, 10; card
plan/packages/sky/cloudsea.md; plan/parts/sky.md 4; c219's terrain review #163.1; the ruling on the
seam in plan/roles/A0-director.md 4).

The face of the sea is the game's own cloud layer. clouds.png is painted shut, so the layer is one
closed sheet, flat and of one colour, with its upper face at scene y -28 (sky/mood.CLOUD_TOP) as far
as the game draws clouds. A sheet has no rim at the view distance and nothing to line up with, and
the game cuts it where rock or iron stands in it, so it lies against everything without a gap. That
sheet is the calm sea, out to the horizon. Blocks are only what the sheet cannot be:

    the surf    cloud heaped against whatever stands in the sea: a lip all the way round, high in
                the gullies and low on the capes, higher where the wind comes from, so the line
                where rock and sea meet is cloud and is never the sheet's level cut;
    the heads   cumulus standing out of the face to y -24: steep round domes, the bigger ones with
                smaller ones crowded on them, packed side by side in banks with calm sea between;
    the piles   a few towers in the banks, to y -20;
    the bodies  what the heads stand on: under every bank a shelf of cloud whose top is one block
                under the face, stepping down at its rim;
    the deck    one course of cloud far below the face (its top five blocks under it, lower again
                in its hollows), out to DECK_REACH from where people stand.

Nobody sees bodies or deck through the sheet. They are the sea for the players who do not have the
sheet where it is drawn here:

    clouds "fast"   the game draws the layer as one flat face at its underside, y -32. The bodies
                    stand three blocks out of that face as low banks with the heads on them, and
                    the face still runs to the horizon over the deck.
    clouds off      the deck is the sea, five blocks lower, dark towards its end; the banks stand
                    on it.

No block of cloud ever has its top in one of the two faces (top blocks at y -29 and -33 are not
laid), and a block of somebody else that has is given a block of cloud on it, so nothing flickers.

Three versions, compared on the real client (the offline renderer draws the fog but neither the
cloud layer nor the afterglow; scenes/obs_sky_cloudsea/preview.py lays the layer into its picture
by the game's arithmetic, as a forecast; the card is settled on S1's pictures):

    "a"  the sheet alone   no blocks. Rock and track meet the sheet's level cut, and with the
                           player's clouds off nothing is left.
    "b"  blocks alone      clouds.png is blanked: what "c" is with the player's clouds off.
    "c"  both (default)    what the master scene builds.

Where a head may stand is ruled by the view distance (12 chunks: the board's). The game takes
blocks into the fog colour between 172.8 and 192 blocks whatever the fog is set to, and draws none
beyond the last loaded chunk; the sheet it goes on drawing, lighter than the fog. A head in that
wall is a dark blot on the sea, and a rim of them is a ring. So a head never stands where somebody
sees it from further than that:

  - from the ground (SEEN): for every column, how far away the farthest person stands who can see a
    head there, worked out from the skeleton's flats and a plain model of the slopes between them.
    The banks thin out where that passes 156 blocks and end by 170. That leaves the sea its banks
    for some forty to seventy blocks from the shore; beyond is the sheet alone, as a level deck of
    cloud lies beyond the heads a mountain raises in it.
  - from the air (AERIAL): the board's camera V12 stands so far out that the far shore is at its
    wall of fog. A lane of calm sea lies where that camera loses the blocks (LOST), so that it sees
    no head darken there and none cut off at a chunk's edge; the banks beyond the lane it does not
    load, and the people on the west rail do.

Only empty cells are filled, and none under a whole block of somebody else. The sea lies right
against whatever stands in it: the mountain's rock and snow, and what is built -- the legs and
girders of the cable trestle, piers, steps. Where something built ends low in the sea (its top
within two blocks over the face: the last cells of the cable track) the sea heaps a head over it,
so the track runs into cloud and is not seen to end on the sheet; near anything that stands in
the sea no cloud is higher than y -24 (LOW: the trestle's bars begin above that), the piles keep
well away. The one exception to lying against everything is what would grow a thick arm towards a
cloud beside it when the scene is placed (walls and fences, JOINS): from those the sea keeps CLEAR
empty cells, with a sunk floor of cloud under the gap.

The five tones are the occupancy roles B.CLOUD (dark to light, palette RAMPS["cloud"]). This package
paints them (A0's exception to "only materials paints blocks": the cloud colour is tuned with the
light of the sky), through materials/_kit like everyone else. The pictures are flat tones named
sky_cloud_0..4 and the game's own face shading is turned off (shade=False, ao=False): which tone a
block wears is baked here from the shape, lit from the west where the afterglow is. The sheet shows
the second lightest tone (sky/mood's cloud colour is that tone as the blue hour lights it), so that
is what level cloud wears, the top of a head as much as the deck. What faces west is the lightest
tone, what faces east the two below, the creases at a head's foot the darkest; the crowns of the
piles catch the light as well. There is no dither: the tones lie in clean bands, as pixel art
shades a ball. The deck sinks to the tone nearest the fog's by its end.
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
LOW_FACE = FACE - mood.CLOUD_THICKNESS      # -32: where the game draws the layer on "fast": its underside
FOOT = FACE - 0.5               # a height field at or over this puts a block above the face
BODY_Y = FACE - 2               # the top blocks of a bank's body: their top is one block under the face
DECK_Y = LOW_FACE - 2           # the deck's blocks: their top is one block under the fast face
HOLLOW_Y = DECK_Y - 1           # ... and one lower in the deck's hollows
FLOOR_Y = DECK_Y - 2            # the sunk floor under a gap beside a wall or a fence
RIM = ((1.5, BODY_Y), (2.5, BODY_Y - 1), (3.5, BODY_Y - 2))    # a body: this far round its heads, this high
HEAP = 4.6                      # a head of cloud stands this far out of the face (to y -24)
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
# of cloud instead of ending on the sheet.
SUNK = (FACE - 1, FACE + 2)     # the block y of such a top: -29 .. -26 (lower, it is under the face anyway)
COVERED = 6.5                   # the head over it is this wide
LOW = FACE + 4                  # -24: no cloud is higher than this block within SHY of what stands in the sea
SHY = 28                        # ... the piles keep this far away from it (site/cablecar's bars begin at -23)

# The view distance the map is shown at and what follows from it (26.3: fog.glsl, FogRenderer,
# ChunkTrackingView). Blocks: the fog of the view distance runs from 90% of it to all of it, by the
# distance in plan; chunks are loaded at most a chunk further.
VIEW = 12 * 16.0                # 192
DECK_REACH = 150.0              # the deck ends this far from where anyone can stand
SEEN = (156.0, 170.0)           # the banks thin out between these distances to their farthest onlooker
HEAD_Y = FACE + 6               # a head counts as seen when the eye reaches this height over its column
FALL = 0.72                     # the mountain's slopes in the sight model: blocks down per block out (site/terrain)
CRAG = 2.0                      # ... taken this much lower: gullies let the eye past
# The board's aerial camera (tools/boardshots.py; the skeleton's V12 once it holds one): where it
# stands in plan, and from where to where it loses the blocks (the wall of fog is whole at VIEW, the
# last loaded chunk ends at most 16 further; a head's own width on both sides).
AERIAL = tuple(float(v) for v in getattr(S, "V12", {}).get("pos", (S.EAST_EDGE_X + 20.0, 90.0, S.Z_SOUTH + 46.0)))[::2]
LOST = (VIEW - 6.0, VIEW + 22.0)
LOST_EDGE = 7.0                 # the lane's banks: the heads thin out over this much on either side
WIND = {"north": (0.0, -1.0), "south": (0.0, 1.0), "west": (-1.0, 0.0), "east": (1.0, 0.0)}[S.WIND_FROM]

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
    """The columns the sea may use, (x0, z0, nx, nz): as far as anybody sees a block, and a margin."""
    (cx, cz), r = S.SUNSET_PLATFORM["centre"], S.SUNSET_PLATFORM["radius"]
    flats = _flats()
    pad = int(VIEW) + 26
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


def _open2(mask):
    """The cells of a 2D mask that lie in a square of two by two cells of it."""
    sq = mask[:-1, :-1] & mask[1:, :-1] & mask[:-1, 1:] & mask[1:, 1:]
    out = np.zeros_like(mask)
    out[:-1, :-1] |= sq
    out[1:, :-1] |= sq
    out[:-1, 1:] |= sq
    out[1:, 1:] |= sq
    return out


def _tidy(top, lip):
    """The heads as blocks show them, cleaned as a sprite is: no step of a head is narrower than
    two cells (one block on a head is a pimple, a row of them a fence), and the lowest step is a
    foot and not a floe: it reaches FOOTING round the step above it and no further, and a patch
    one block high with nothing on it goes. The lip along the land (``lip``) stays as it is.
    Returns the height field with those cells lowered or taken out."""
    lvl = np.where(top >= FOOT, np.floor(top + 0.5), FACE - 1).astype(np.int64)
    out = np.full(top.shape, FACE - 1, dtype=np.int64)
    for y in range(FACE, int(lvl.max()) + 1):
        there = lvl >= y
        ok = (_open2(there) | (lip & there)) & (out == y - 1)
        out[ok] = y
    out[(out == FACE) & ~lip & (_distance(out > FACE, 4) > FOOTING)] = FACE - 1
    return np.where(out >= FACE, np.minimum(top, out + 0.45), -np.inf)


def _others(canvas, origin, lo, shape, y0):
    """(occ, whole, joins, high): the cells of the box that hold a block of somebody else; which of
    those are whole blocks, hiding what is behind them; which hold something that would join on to
    a cloud (box indices; the box starts at scene (lo[0], y0, lo[1])); and per column the scene y
    of the highest block of somebody else at any height (far below the box where there is none)."""
    ox, oy, oz = origin
    nx, ny, nz = shape
    x0, z0 = lo
    occ, whole, joins = (np.zeros(shape, dtype=bool) for _ in range(3))
    high = np.full((nx, nz), -10 ** 6, dtype=np.int64)
    keys = np.array(list(canvas.b.keys()), dtype=np.int64).reshape(-1, 3)
    if len(keys):
        a, b, c = keys[:, 0] - ox - x0, keys[:, 1] - oy - y0, keys[:, 2] - oz - z0
        col = (a >= 0) & (a < nx) & (c >= 0) & (c < nz)
        np.maximum.at(high, (a[col], c[col]), b[col] + y0)
        ok = col & (b >= 0) & (b < ny)
        occ[a[ok], b[ok], c[ok]] = True
        for key, i, j, k in zip(keys[ok].tolist(), a[ok].tolist(), b[ok].tolist(), c[ok].tolist()):
            name = canvas.b[tuple(key)].partition("[")[0].split(":")[-1]
            if name.endswith(JOINS):
                joins[i, j, k] = True
            elif not (name.endswith(THIN) or name in THIN_NAMES):
                whole[i, j, k] = True
    return occ, whole, joins, high


def _field(seed, land, sunk=()):
    """What stands out of the face, and the deck: (top, hollow, deck, dusk). ``top`` is the
    continuous height per column of the heads, the surf and the piles (-inf where the face is
    calm), ``hollow`` says where the deck lies a block lower, ``deck`` where there is deck at all,
    ``dusk`` how far the deck has sunk towards the fog's tone there (0 near the mountain, 1 at its
    end). ``land`` marks the columns where something stands in the cloud: the sea heaps up along it
    and keeps its piles away from it. ``sunk`` lists what is built and ends low in the sea, as
    (column, column, y of its top block): the sea heaps over those."""
    x0, z0, nx, nz = _grid()
    X, Z = np.meshgrid(np.arange(nx) + x0, np.arange(nz) + z0, indexing="ij")

    hull = _hull(X, Z)
    wobble = N.fbm2(X / 47.0, Z / 47.0, seed + 5, octaves=3)           # no edge is a ruled line
    deck = hull - 14.0 * wobble < DECK_REACH
    dusk = N.smoothstep(0.36 * DECK_REACH, 0.76 * DECK_REACH, hull - 22.0 * wobble)
    hollow = N.fbm2(X / 58.0, Z / 58.0, seed + 2, octaves=2) < -0.16
    amount = _amount(X, Z)
    # where the cloud piles up: banks, longer north-south than they are wide, about two thirds of
    # the sea that may carry any; 1 in a bank, 0 in the calm water that winds between them
    bend = N.fbm2(X / 90.0, Z / 90.0, seed + 7, octaves=2) * 22.0
    core = N.smoothstep(-0.20, 0.04, N.fbm2((X + bend) / 44.0, Z / 70.0, seed + 1, octaves=2))
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
        ball again and lower than the one it leans on."""
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

    # Every head has random numbers of its own, by the cell of the grid it is drawn in (the piles by
    # their place in the list of sites tried): when somebody builds or digs at the shore, or the
    # board's camera moves, the sea changes there and stays as it was everywhere else.

    # the heads: packed side by side in the banks, so close that they lean on one another, and none
    # in the calm water between the banks. They do not look at the land, so they stand where they
    # stand whatever is built. Towards the end of where a head may stand they grow few, small and low.
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
        swell = 0.25 * np.maximum(windward, 0.0) - 0.12 * np.maximum(-windward, 0.0)
        surf = N.fbm2(X / 23.0, Z / 23.0, seed + 9, octaves=2)
        # the lip: at least one block of cloud against the land all the way round, and on the
        # land's own last columns where they lie under the face
        lip = coast | ((shore > 0.0) & (shore <= 1.5))
        top = np.where(lip, np.maximum(top, FOOT + 0.55), top)
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
                a = float(np.clip(0.5 + surf[ix, iz] + 1.5 * (fold[ix, iz] - 0.28) + swell[ix, iz], 0.0, 1.0))
                if u > 0.6 + 0.4 * a:
                    continue
                rad = 2.8 + 1.4 * v + 2.2 * a
                head(np.random.default_rng((seed, 2, i, j)), px, pz, rad, min(HEAP, rad * (0.7 + 0.3 * w)))
        # where the surf stands high the cloud banks up further out as well: big heads with a
        # crowd of smaller ones on them, a few to a bay, and none where a head may not stand
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
                a = float(np.clip(0.5 + 1.9 * bank[ix, iz] + 1.2 * (fold[ix, iz] - 0.28) + 1.4 * swell[ix, iz], 0.0, 1.0))
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

    top = np.minimum(top, PEAK + 0.45)
    return _tidy(top, lip), hollow, deck, dusk


def _shade(h):
    """Light 0..1 per column from the height of its top block, lit from the west, low. Level cloud
    takes the face's own light (0.75: the tone the sheet shows), whatever its height; what faces
    west takes more, what faces east less, a little of that again for the lie of the whole bank;
    a crest has a breath more than a crease, and the crowns of the piles catch the light."""
    h = (h - DECK_Y).astype(np.float32)             # the blur reads zero outside the grid: the deck's level

    def westward(a):                                # rising eastwards = facing west
        p = np.pad(a, 1, mode="edge")
        return (p[2:, 1:-1] - p[:-2, 1:-1]) * 0.5

    crest = h - _blur(h, 3)                                             # over its surroundings or under
    crown = np.clip((h - (FACE - DECK_Y) - 3.0) / 5.0, 0.0, 1.0)
    return (0.75 + 0.30 * np.tanh(1.3 * westward(h)) + 0.10 * np.tanh(2.5 * westward(_blur(h, 5)))
            + 0.05 * np.tanh(1.2 * crest) + 0.12 * crown)


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
    occ, whole, joins, high = _others(canvas, origin, (x0, z0), (nx, ny, nz), y0)
    kept = _grow(joins, CLEAR)                      # the room given to what would join on to a cloud

    # The land: columns where somebody's block stands in the cloud, from the bodies' level up, and
    # what those wall in: the hollow of the mountain. What merely has a bridge over it is not walled
    # in and keeps its cloud, and so does a pocket less than five columns across (the slot between
    # two rails, a cleft in the shore): the hollow is what is left of the walled-in columns after
    # two are taken off every rim. Under the land the sea goes on for a few columns only: far
    # enough in to lie under a trestle or a landing stage, and no further under the mountain.
    band = occ[:, BODY_Y - y0:, :].any(axis=1)
    shut = ~band & ~_reach(~band)
    inside = shut & _grow(~_grow(~shut, 2), 2)
    land = band | inside
    dry = inside | (land & (_distance(~land, 6) > 4.5))
    # what is built and ends low in the sea: the columns whose highest block is a thin one near the face
    j = np.clip(high - y0, 0, ny - 1)
    thin = occ[np.arange(nx)[:, None], j, np.arange(nz)[None, :]] & ~whole[np.arange(nx)[:, None], j, np.arange(nz)[None, :]]
    sunk = thin & (high >= SUNK[0]) & (high <= SUNK[1]) & ~dry
    top, hollow, deck, dusk = _field(seed, land, [(i, k, int(high[i, k])) for i, k in zip(*np.nonzero(sunk))])

    # The top block of every column: a head where the field stands out of the face; round the heads
    # their body, stepping down; the deck everywhere else, and a strip of it round every body.
    cap = (top >= FOOT) & ~dry
    near = _distance(cap, 6)
    floor_y = np.where(hollow, HOLLOW_Y, DECK_Y)
    level = np.full((nx, nz), y0 - 1, dtype=np.int64)                   # nothing
    sea = (deck | (near <= 5.5)) & ~dry
    level[sea] = floor_y[sea]
    for reach, y in reversed(RIM):
        level[(near <= reach) & ~dry] = y
    level[cap] = np.floor(top[cap] + 0.5).astype(np.int64)

    # only empty cells, clear of what would join on, and none under a whole block of somebody else
    ys = np.arange(ny)[None, :, None] + y0
    solid = (ys >= floor_y[:, None, :]) & (ys <= level[:, None, :]) & ~occ & ~kept
    solid &= ~np.flip(np.logical_or.accumulate(np.flip(whole, 1), axis=1), 1)
    # nothing has its top in one of the game's two faces: a block of cloud that would is left out,
    # a block of somebody else that has is covered, under an overhang as well
    for face in (FACE, LOW_FACE):
        f = face - y0
        solid[:, f - 1, :] &= solid[:, f, :] | occ[:, f, :]
        awash = occ[:, f - 1, :] & ~occ[:, f, :] & ~dry
        solid[:, f, :] |= awash & ~kept[:, f, :]

    # the sunk floor: where the deck was opened beside a wall or a fence and nothing stands in the
    # column, the eye would drop through to the void; a dark course of cloud lies there, low in the gap
    floor = np.zeros_like(solid)
    floor[:, FLOOR_Y - y0, :] = sea & ~solid.any(axis=1) & ~occ.any(axis=1)
    floor &= ~kept

    # only what can be seen from above or from the side is placed: a cell with cloud or whole rock
    # over it and on all four sides is left out. What is built hides nothing (a rail, a bar, a step
    # lets the eye past), nor does a thin layer of snow.
    p = np.pad(solid | whole, 1)
    west_open, east_open = ~p[:-2, 1:-1, 1:-1], ~p[2:, 1:-1, 1:-1]
    side_open = ~p[1:-1, 1:-1, :-2] | ~p[1:-1, 1:-1, 2:]
    up_open = ~p[1:-1, 2:, 1:-1]
    skin = solid & (up_open | west_open | east_open | side_open)

    # The light of a column is that of its top block; the land counts as level with the face, so the
    # lip is lit by the side the sea lies on. The deck is a tone darker in its hollows and sinks to
    # the fog's tone towards its end. A cell seen from the side only takes its column's light, more
    # of it facing west, less facing east, and less the further down the side it lies.
    here = level > y0 - 1
    height = np.where(cap, top, np.where(land, FACE, np.where(here, level, DECK_Y)))
    light = _shade(height)
    low = here & (level <= DECK_Y)
    light = np.where(low, np.clip(light - 0.25 * (level == HOLLOW_Y) - 0.5 * dusk, 0.25, 1.0), light)
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
