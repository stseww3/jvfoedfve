"""site/terrain: the mountain the observatory stands on, the floor and the edge of the upper terrace
round the building, and the sunset terrace on the west (plan/ART-PLAN.md 4, card
plan/packages/site/terrain.md). Blocks only.

The mountain is an outline and a base, never a subject: nothing of it rises above the terrace
(y -1), and it stays a big step darker than the building. What gives it a shape (review 4):

  - form. Not an even slope: bands of cliff with shelves between them. The rock lies in beds that
    undulate and dip a little; the hard beds stand as cliffs four to eight blocks high, the shelves
    at their feet are a few blocks wide where the mountain is steep and wide on the ridges. Six
    ridges run out from the terraces and six gullies cut in between them, so no two sides have the
    same outline: sheer on the west under the sunset terrace, long spurs to the north and south,
    the lower platform cut into the east side with one ridge beyond it for the cable track.
  - rock. Natural faces only (deepslate, cobbled deepslate, tuff, a little stone and andesite), laid
    in the same beds that make the cliffs, one to three blocks thick, so no face is flat and the
    lines of the beds follow the shelves. What is built -- the terrace's rim wall, its buttresses --
    is slate brick, and the eye can tell it from the mountain.
  - snow. Lies on the shelves, in from their outer edge: the only cold light thing on the mountain
    at night, and it draws the shelves.

The upper terrace outside the front court is paved here with the court's own three stones (the
court, ORDER 60, lays its pattern over its part): the field, a kerb on the whole outline, a course
of brick inside it, the foot strip carried on to both ends. The sunset terrace is the same floor
(A0 #171): dark slate, the walk from the west door and a strip on the line of each outer pilaster
of the apse, ashlar only in the kerb and the piers. The railing (site/_kit.py) runs round the whole
outline except the east lip, which is the court's, and three gaps where a path leaves the terrace.

Level ground kept for others (plan/parts/A4-site.md 7): the lower platform (rock at
S.LOWER_PAVING_Y, paved by site/stair), the mast pad (part of the terrace), the three shelves of
the outbuildings with a neck of rock leading to each, and the ridge of the cable track
(K.cable_ridge). `top(x, z)` gives the rock surface of any column.

The ring of cloud at the foot is the first draft's stand-in, kept as it was until sky/cloudsea
takes over (A0 #171); only its middle and radius follow the mountain.
"""
import math

import numpy as np

from artkit import noise as N
from artkit.canvas import hash3

from ..common import blocks as B
from ..common import skeleton as S
from . import _kit as K

ORDER = 10      # the ground goes down first, before the stair (20-30), the court (60) and the shells

SEED = 164
TOP = S.PAVING_Y                # -1: the terrace's paving course; the mountain's highest block
LOWER = S.LOWER_PAVING_Y        # -7: the rock under the lower platform's paving
FLOOR = K.ROCK_FLOOR            # -29: the rock is carried down to here, under the cloud

# the area the mountain is worked out on: wide enough for the longest ridge to reach the floor
GX0, GX1 = -84, 134
GZ0, GZ1 = -104, 108

# --- the upper level: the terrace, the sunset half-circle, the mast pad -----------------------------
TX0, TZ0, TX1, TZ1 = S.UPPER_TERRACE
SUN_CX, SUN_CZ = S.SUNSET_PLATFORM["centre"]            # the cell (-9, 0)
SUN_R = S.SUNSET_PLATFORM["radius"] - 0.5               # cells whose middle lies within this of that cell's
PAD = S.MAST_PAD["box"]

# where a path leaves the terrace: the railing is left open over these cells, a pier either side
GAPS = {
    "south lookout": [(x, TZ1) for x in (44, 45, 46)],
    "weather station": [(x, TZ0) for x in (2, 3, 4)],
    "water tower": [(TX0, z) for z in (-33, -32, -31)],
}

# --- the shelves of the outbuildings: (box, the y of the rock) and the neck that leads to each ------
SHELVES = {
    "weather station": (S.WEATHER_STATION["box"], S.WEATHER_STATION["feet"] - 1),
    "water tower": (S.WATER_TOWER["box"], S.WATER_TOWER["feet"] - 1),
    "south lookout": (S.SOUTH_LOOKOUT["box"], S.SOUTH_LOOKOUT["feet"] - 1),
}
# start on the terrace's edge, heading, the fall per block down to the shelf's level, the length of
# the level run across the shelf. The crest is three cells wide and takes no roughness: a path.
NECKS = (
    dict(start=(45, TZ1), heading=(0, 1), fall=0.5, level=SHELVES["south lookout"][1], run=8),
    dict(start=(3, TZ0), heading=(0, -1), fall=1.0, level=SHELVES["weather station"][1], run=7),
    dict(start=(TX0, -32), heading=(-1, 0), fall=1.0, level=SHELVES["water tower"][1], run=9),
)

# --- ridges and gullies -----------------------------------------------------------------------------
# A ridge: where its crest leaves level ground, its heading, the crest's height there, and how the
# crest falls with the distance t along it (y0 - a t - b t^2); `side` is the fall per block away
# from the crest. These go through the beds like the rest of the mountain, so a ridge comes down in
# steps with long shelves on it.
RIDGES = (
    dict(start=(23, -46), heading=(0.30, -1), y0=-1.5, a=0.42, b=0.011, side=1.7),      # north, from the mast pad
    dict(start=(3, -49), heading=(-0.30, -1), y0=-5.5, a=0.60, b=0.020, side=1.9),      # north, below the weather station
    dict(start=(-21, -31), heading=(-1, -0.50), y0=-3.5, a=0.50, b=0.014, side=1.8),    # north-west, the water tower's shoulder
    dict(start=(-10, 31), heading=(-0.80, 1), y0=-2.0, a=0.55, b=0.012, side=1.8),      # south-west
    dict(start=(45, 56), heading=(0.30, 1), y0=-6.5, a=0.42, b=0.014, side=1.6),        # south, beyond the lookout
    dict(start=(80, 43), heading=(0.35, 1), y0=-8.0, a=0.65, b=0.020, side=1.9),        # south-east, below the power house
    dict(start=(91, 13), heading=(1, 0.30), y0=-8.5, a=0.55, b=0.016, side=1.8),        # east, below the lower platform
    dict(start=(-29, 5), heading=(-1, 0.55), y0=-4.5, a=0.85, b=0.020, side=2.2),       # west, the keel under the sunset terrace
)
# A gully: where it starts under the terrace's edge, its heading, how deep it cuts, its half-width
# at the start and how fast it widens.
GULLIES = (
    dict(start=(-12, -23), heading=(-1, -0.25), depth=7.0, width=3.0, grow=0.10),       # either side of the sunset
    dict(start=(-12, 23), heading=(-1, 0.45), depth=5.0, width=2.5, grow=0.07),         # terrace: it stands on a prow
    dict(start=(11, -40), heading=(0.10, -1), depth=5.0, width=2.5, grow=0.07),         # between weather station and mast pad
    dict(start=(44, -40), heading=(0.45, -1), depth=5.0, width=3.0, grow=0.08),         # north-east
    dict(start=(12, 40), heading=(-0.15, 1), depth=6.0, width=3.0, grow=0.08),          # south
    dict(start=(53, 40), heading=(0.05, 1), depth=4.0, width=2.0, grow=0.06),           # between the lookout's ridge and the lower platform
    dict(start=(93, -9), heading=(1, -0.15), depth=5.0, width=2.5, grow=0.08),          # east, between the cable ridge and the east spur
    dict(start=(93, 31), heading=(1, 0.20), depth=5.0, width=2.5, grow=0.08),           # east, between the two spurs
)

# --- the beds: where the cliffs stand ---------------------------------------------------------------
# In the mountain's own heights (before the beds' undulation is added back): the terrace's level and
# the level of each shelf below it. Of each band the top CLIFF part of the fall is taken in one cliff
# and only SHELF of its height is left for the shelf at its foot.
BANDS = (TOP, -8.0, -15.5, -23.5, -33.0)
CLIFF = (0.24, 0.20, 0.20, 0.35)        # the share of a band's run that is cliff
SHELF = (0.13, 0.12, 0.10, 0.50)        # the share of a band's height that the shelf keeps; the last band is under the cloud

# --- rock, in beds -----------------------------------------------------------------------------------
DEEP, COBBLED, TUFF = B.ROCK_DEEPSLATE, B.ROCK_COBBLED.block, B.TUFF.block
STONE, ANDESITE = B.ROCK_STONE.block, B.ROCK_ANDESITE.block
SNOW = B.SNOW_LAYER
# (rock, thickness), from the top down, repeated. No bed is thicker than three, and no two
# neighbours are the same, so no cliff shows a flat face of one block. Dark on the whole: deepslate
# a little over half, stone and andesite only as thin light seams.
BEDS = ((DEEP, 3), (TUFF, 1), (DEEP, 2), (COBBLED, 1), (TUFF, 2), (DEEP, 3), (STONE, 1), (DEEP, 2),
        (COBBLED, 2), (TUFF, 1), (DEEP, 3), (ANDESITE, 1), (DEEP, 2), (TUFF, 2), (COBBLED, 1))
# a few blocks of a kindred rock in a bed, as weathering: {bed rock: (the other rock, its share)}
FLECKS = {DEEP: (COBBLED, 0.10), COBBLED: (DEEP, 0.15), TUFF: (COBBLED, 0.08), STONE: (ANDESITE, 0.20),
          ANDESITE: (STONE, 0.20)}
LIGHT = (TUFF, STONE, ANDESITE)     # the beds that read as light lines on a cliff
SEAM = COBBLED                  # what stands in a light bed's place where the bed has thinned out
LENS_OUT = -0.02                # ... which is where the bed's own slow noise is below this: a little under half of it
SNOW_BELOW = -5                 # no snow on the rock just under the terraces
SNOW_IN = 0.9                   # snow lies on a shelf from the cliff's foot outwards; the very edge stays dark
SNOW_DRIFT = -0.12              # ... in drifts: where a slow noise is above this, about two thirds of the shelves
SNOW_DEPTH = ((0.25, 4), (0.6, 3), (1.0, 2))    # (how far out on the shelf, layers): it lies on the rock, it is not a block of it

# --- what is built on the rim -------------------------------------------------------------------------
RIM = B.SLATE_BRICK.block       # the terrace's rim wall under the kerb
RIM_DEPTH = 3                   # courses of it; the cliff shows below
RIM_SHOWS = 2                   # at least this many of them stand clear of the rock, everywhere
RIM_CLEAR = 1.5                 # ... within this distance of the terrace
BASTION_DEPTH = 5               # under the sunset terrace
BUTTRESS = B.SLATE_BRICK        # one under every pier, a block proud of the wall, weathered at the top
BUTTRESS_DEPTH = 6
WALK_HALF = 2                   # the walk from the west door is the door bay with its two pilasters: 5 across
ARC_STEP = 15                   # degrees between the piers on the sunset terrace's arc: about five blocks

# --- the first draft's ring of cloud (a stand-in; sky/cloudsea takes over) ---------------------------
CLOUD_TOP = -26                 # the top face of the block cloud sheet
CLOUD_BOTTOM = -28              # three courses of cloud; the mountain plunges past it
CLOUD_MARGIN = 11               # how far the ring reaches beyond the mountain's foot
CLOUD = B.CLOUD


# ---- the height of every column ------------------------------------------------------------------------
def _unit(v):
    n = math.hypot(v[0], v[1])
    return v[0] / n, v[1] / n


def _d_box(X, Z, box):
    """Distance from each cell to a box of cells (0 inside)."""
    x0, z0, x1, z1 = box
    dx = np.maximum(np.maximum(x0 - X, X - x1), 0.0)
    dz = np.maximum(np.maximum(z0 - Z, Z - z1), 0.0)
    return np.hypot(dx, dz)


def _in_box(X, Z, box):
    x0, z0, x1, z1 = box
    return (X >= x0) & (X <= x1) & (Z >= z0) & (Z <= z1)


def _along(X, Z, start, heading):
    """(t, lat): how far along a line each cell lies and how far to its side."""
    ux, uz = _unit(heading)
    px, pz = start
    t = (X - px) * ux + (Z - pz) * uz
    lat = (Z - pz) * ux - (X - px) * uz
    return t, lat


def _beds(y):
    """What the beds make of a smooth height (the mountain's own heights, an array): the height
    itself above the first band and below the last; inside a band a cliff, then a shelf. Returns
    the new height and, for a cell on a shelf, how far out on it the cell lies (0 at the cliff's
    foot .. 1 at the shelf's edge; -1 elsewhere)."""
    out = y.copy()
    where = np.full(y.shape, -1.0)
    for k in range(len(BANDS) - 1):
        top, bot = BANDS[k], BANDS[k + 1]
        height = top - bot
        cliff, shelf = CLIFF[k], SHELF[k]
        m = (y <= top) & (y > bot)
        u = (top - y[m]) / height
        on_cliff = u < cliff
        fall = np.where(on_cliff, u / cliff * (1 - shelf), (1 - shelf) + (u - cliff) / (1 - cliff) * shelf)
        out[m] = top - fall * height
        where[m] = np.where(on_cliff, -1.0, (u - cliff) / (1 - cliff))
    return out, where


def _mountain():
    """Every column of the mountain: dict(xs, zs, H, valid, upper, kept, shelf, dip), arrays over
    the worked area. H is the y of the topmost block, valid says where there is rock at all."""
    xs = np.arange(GX0, GX1 + 1)
    zs = np.arange(GZ0, GZ1 + 1)
    X, Z = np.meshgrid(xs.astype(float), zs.astype(float), indexing="ij")

    # the upper level and the distance to it
    disc = np.hypot(X - SUN_CX, Z - SUN_CZ)
    upper = _in_box(X, Z, S.UPPER_TERRACE) | ((X < TX0) & (disc <= SUN_R)) | _in_box(X, Z, PAD)
    d_up = np.minimum(np.minimum(_d_box(X, Z, S.UPPER_TERRACE), np.maximum(disc - SUN_R, 0.0)), _d_box(X, Z, PAD))
    d_low = _d_box(X, Z, S.LOWER_PLATFORM)

    # the smooth mountain: it falls away from the level ground, faster on the west, and the
    # distance is stretched and shifted by slow noise so the cliffs wander
    slow = N.fbm2(X * 0.021, Z * 0.021, SEED + 11, octaves=3)
    wander = N.fbm2(X * 0.05, Z * 0.05, SEED + 12, octaves=3)
    r = np.hypot(X - 25.0, Z) + 1e-6
    west = np.clip(-(X - 25.0) / r, 0.0, 1.0)
    south = np.clip(Z / r, 0.0, 1.0)
    uneven = N.fbm2(X * 0.045, Z * 0.045, SEED + 17, octaves=2)
    steep = 1.15 + (0.85 + 0.9 * uneven) * west ** 2 + 0.10 * south ** 2 + 0.15 * slow
    s_up = np.maximum(d_up * (1 + 0.22 * slow) + np.clip(d_up / 4.0, 0, 1) * 3.2 * wander, 0.45 * d_up)
    smooth = TOP - steep * s_up
    wander2 = N.fbm2(X * 0.05, Z * 0.05, SEED + 13, octaves=3)
    s_low = np.maximum(d_low * (1 + 0.22 * slow) + np.clip(d_low / 4.0, 0, 1) * 2.6 * wander2, 0.45 * d_low)
    smooth = np.maximum(smooth, LOWER - (1.45 + 0.2 * slow) * s_low)
    for i, rg in enumerate(RIDGES):
        t, lat = _along(X, Z, rg["start"], rg["heading"])
        lat = lat + 2.2 * N.perlin2(t * 0.06, np.full(t.shape, 7.3 + i), SEED + 14)
        tt = np.maximum(t, 0.0)
        off = np.where(t < 0, np.hypot(lat, t), np.abs(lat))
        smooth = np.maximum(smooth, rg["y0"] - rg["a"] * tt - rg["b"] * tt * tt - rg["side"] * off)
    for g in GULLIES:
        t, lat = _along(X, Z, g["start"], g["heading"])
        w = g["width"] + g["grow"] * np.maximum(t, 0.0)
        smooth = smooth - g["depth"] * np.exp(-(lat / w) ** 2) * N.smoothstep(0.0, 6.0, t)

    # the beds: they undulate and dip to the west; cliffs and shelves follow them
    dip = 2.3 * N.fbm2(X * 0.016, Z * 0.016, SEED + 31, octaves=3) + 0.03 * (X - 25.0) - 0.012 * Z
    h, shelf = _beds(smooth - dip)
    h = h + dip

    # what is not left to the beds: the necks to the shelves, the ridge of the cable track
    kept = upper.copy()                 # cells whose height is given: no roughness, no snow
    for nk in NECKS:
        t, lat = _along(X, Z, nk["start"], nk["heading"])
        down = (TOP - nk["level"]) / nk["fall"]         # the length of the fall to the shelf's level
        crest = np.where(t <= down, TOP - np.ceil(nk["fall"] * np.maximum(t, 0.0)),
                         np.where(t <= down + nk["run"], nk["level"], nk["level"] - 2.0 * (t - down - nk["run"])))
        neck = crest - 1.8 * np.maximum(np.abs(lat) - 1.5, 0.0)
        on = (neck > h) & (t >= 0)
        h = np.where(on, neck, h)
        shelf = np.where(on, -1.0, shelf)
        kept |= on & (np.abs(lat) <= 1.5) & (t <= down + nk["run"])
    cx0, cx1 = K.CABLE_RIDGE_X
    d = np.clip(X - cx0 + 1, 1.0, cx1 - cx0 + 1.0)
    axis = K.CABLE_RIDGE_Z - (np.clip(X, cx0, cx1) - cx0) / 3.0
    crest = LOWER - 1 - 0.30 * d - 0.014 * d * d - 2.5 * np.maximum(X - cx1, 0.0)
    ridge = np.where(X >= cx0, crest - 2.0 * np.maximum(np.abs(Z - axis) - 1.5, 0.0), -99.0)
    on = ridge > h
    h = np.where(on, ridge, h)
    shelf = np.where(on, -1.0, shelf)

    # level ground cut into the slope or built out from it: flat inside, a bank above, a fall below
    # its foot is uneven: here the rock falls from the very edge, there it runs out a little first
    pads = [(S.LOWER_PLATFORM, LOWER)] + [SHELVES[k] for k in sorted(SHELVES)]
    apron = 1.2 + 2.6 * N.fbm2(X * 0.11, Z * 0.11, SEED + 15, octaves=2)
    fall = 2.4 + 1.2 * N.fbm2(X * 0.09, Z * 0.09, SEED + 16, octaves=2)
    for box, level in pads:
        dist = _d_box(X, Z, box)
        near = (dist > 0) & (dist <= 10)
        foot = level - 0.5 - fall * np.maximum(dist - np.maximum(apron, 0.0), 0.0)
        h = np.where(near, np.clip(h, foot, level + 0.5 + 1.8 * dist), h)
        h = np.where(dist == 0, float(level), h)
        kept |= dist == 0
        shelf = np.where(dist <= 1, -1.0, shelf)

    rough = 0.45 * N.fbm2(X * 0.31, Z * 0.31, SEED + 41, octaves=2)
    h = np.where(kept, h, h + np.where(shelf >= 0, 0.35, 1.0) * rough)     # the shelves are smoother than the cliffs
    h = np.where(d_up <= RIM_CLEAR, np.minimum(h, TOP - RIM_SHOWS - 1), h)     # the rim wall is never buried
    h = np.where(upper, float(TOP), np.minimum(h, TOP))
    H = np.rint(h).astype(int)
    for x in range(cx0, cx1 + 1):       # the bed of the cable track: exact, three cells wide
        z, y = K.cable_ridge(x)
        for dz in (-1, 0, 1):
            H[x - GX0, z + dz - GZ0] = y
            kept[x - GX0, z + dz - GZ0] = True
            shelf[x - GX0, z + dz - GZ0] = -1.0
    for (x, z), y in neck_steps().items():      # the ground under the steps of each neck: exact
        H[x - GX0, z - GZ0] = y
        kept[x - GX0, z - GZ0] = True
    valid = H >= FLOOR
    return dict(xs=xs, zs=zs, H=H, valid=valid, upper=upper, kept=kept, shelf=shelf, dip=np.rint(dip).astype(int))


def neck_steps():
    """{(x, z): y of the rock} on the crest of each neck, from the terrace's edge down to the
    shelf: the ground the steps of site/outbuildings stand on. It goes down a whole block at a
    time, one block in every 1 / fall along the neck."""
    out = {}
    for nk in NECKS:
        (px, pz), (ux, uz) = nk["start"], nk["heading"]
        for t in range(1, int(math.ceil((TOP - nk["level"]) / nk["fall"])) + 1):
            y = TOP - int(math.ceil(nk["fall"] * t))
            for side in (-1, 0, 1):
                out[(px + ux * t - uz * side, pz + uz * t + ux * side)] = y
    return out


_cache = {}


def mountain():
    if "m" not in _cache:
        _cache["m"] = _mountain()
    return _cache["m"]


def top(x, z):
    """The y of the topmost rock in column (x, z), or None where the mountain has gone under the
    cloud. For the packages that stand on the mountain (steps, footings, trestle legs)."""
    m = mountain()
    i, k = x - GX0, z - GZ0
    if not (0 <= i < m["H"].shape[0] and 0 <= k < m["H"].shape[1]) or not m["valid"][i, k]:
        return None
    return int(m["H"][i, k])


# ---- rock and snow ---------------------------------------------------------------------------------------
def _bed_table():
    rows = []
    for rock, thick in BEDS:
        rows += [rock] * thick
    return rows


_BED_ROWS = _bed_table()


def _rock(x, y, z, dip, lens_a, lens_b):
    """The rock of a block: its bed, by its height in the beds' own levels, with a few flecks.
    A light bed is not a stripe round the whole mountain: it comes and goes in lenses, a different
    pattern for each bed, and where it is out the dark seam rock takes its place."""
    row = (dip - y + (1 if hash3(x, 0, z, SEED + 51) < 0.12 else 0)) % len(_BED_ROWS)
    rock = _BED_ROWS[row]
    if rock in LIGHT and math.cos(row * 2.4) * lens_a + math.sin(row * 2.4) * lens_b < LENS_OUT:
        rock = SEAM
    other, share = FLECKS[rock]
    return other if hash3(x, y, z, SEED + 52) < share else rock


def _neighbours(a):
    """The four neighbours' values of every cell, as four arrays."""
    return [np.roll(a, step, axis=axis) for axis, step in ((0, 1), (0, -1), (1, 1), (1, -1))]


def _snowy(m):
    """Where snow lies: on the shelves, in from their outer edge, where the ground is nearly level.
    In wide drifts with bare rock between them, not a line along the foot of every cliff; and never
    a single block of it standing proud of the ground."""
    H, valid = m["H"], m["valid"]
    level = np.ones(H.shape, dtype=bool)
    for n in _neighbours(H):
        level &= np.abs(n - H) <= 1
    X, Z = np.meshgrid(m["xs"].astype(float), m["zs"].astype(float), indexing="ij")
    drift = N.fbm2(X * 0.035, Z * 0.035, SEED + 61, octaves=3)
    snow = (valid & level & ~m["kept"] & (m["shelf"] >= 0) & (m["shelf"] <= SNOW_IN)
            & (H <= SNOW_BELOW) & (drift > SNOW_DRIFT))
    for _ in range(2):                                          # no specks: a cell needs two snowy neighbours
        snow &= sum(n.astype(int) for n in _neighbours(snow)) >= 2
    return snow


def _snow_depth(where):
    """How many layers of snow (eighths of a block) lie on a cell that far out on its shelf: a
    drift against the foot of the cliff, thinning towards the shelf's edge."""
    for limit, layers in SNOW_DEPTH:
        if where <= limit:
            return layers
    return SNOW_DEPTH[-1][1]


def _lay_mountain(c, o, m):
    """A watertight crust: every column from its top down as far as its lowest neighbour, the
    columns at the foot down to the floor. Hollow inside; it is never seen."""
    ox, oy, oz = o
    H, valid, dip = m["H"], m["valid"], m["dip"]
    snowy = _snowy(m)
    low = H.copy()
    for axis, step in ((0, 1), (0, -1), (1, 1), (1, -1)):
        n = np.where(np.roll(valid, step, axis=axis), np.roll(H, step, axis=axis), FLOOR)
        low = np.minimum(low, n)
    low[0, :] = low[-1, :] = low[:, 0] = low[:, -1] = FLOOR
    low = np.maximum(low, FLOOR)
    X, Z = np.meshgrid(m["xs"].astype(float), m["zs"].astype(float), indexing="ij")
    lens_a = N.fbm2(X * 0.06, Z * 0.06, SEED + 71, octaves=2)
    lens_b = N.fbm2(X * 0.06, Z * 0.06, SEED + 72, octaves=2)
    for i, k in zip(*np.nonzero(valid)):
        x, z = int(m["xs"][i]), int(m["zs"][k])
        y1, y0, dp = int(H[i, k]), int(low[i, k]), int(dip[i, k])
        la, lb = float(lens_a[i, k]), float(lens_b[i, k])
        for y in range(y1, y0 - 1, -1):
            c.set(ox + x, oy + y, oz + z, _rock(x, y, z, dp, la, lb))
        if snowy[i, k]:
            c.set(ox + x, oy + y1 + 1, oz + z, f"{SNOW}[layers={_snow_depth(float(m['shelf'][i, k]))}]")


# ---- the upper terrace: floor, rim, railing -------------------------------------------------------------
def upper_cells():
    m = mountain()
    return {(int(m["xs"][i]), int(m["zs"][k])) for i, k in zip(*np.nonzero(m["upper"]))}


def rail_piers(ring):
    """The cells of the outline that carry a pier. On the straight edges: the corners, either side
    of every gap, and between those as many as fit BEAT apart (the west edge keeps the pilaster
    lines of the west front). On the arc of the sunset terrace: every ARC_STEP degrees."""
    ring = set(ring)
    px0, pz0, px1, pz1 = PAD
    gate = {name: (cells[0], cells[-1]) for name, cells in GAPS.items()}
    piers = set()
    # north edge, west to east, with the mast pad's three sides in it
    gx0, gx1 = gate["weather station"][0][0] - 1, gate["weather station"][1][0] + 1
    piers |= {(x, TZ0) for x in K.spaced([TX0, gx0]) + K.spaced([gx1, px0]) + K.spaced([px1, TX1])}
    piers |= {(px0, z) for z in K.spaced([pz0, TZ0])} | {(px1, z) for z in K.spaced([pz0, TZ0])}
    piers |= {(x, pz0) for x in K.spaced([px0, px1])}
    # south edge
    gx0, gx1 = gate["south lookout"][0][0] - 1, gate["south lookout"][1][0] + 1
    piers |= {(x, TZ1) for x in K.spaced([TX0, gx0]) + K.spaced([gx1, TX1])}
    # west edge: the pilaster lines, down to where the arc takes over
    arc_z = max(z for x, z in ring if x == TX0 - 1) + 1         # the last row of the straight edge
    lines = [z for z in K.beat(TZ0, TZ1) if abs(z) >= arc_z + K.BEAT]
    piers |= {(TX0, z) for z in lines} | {(TX0, -arc_z), (TX0, arc_z)}
    # the arc: one on the axis, the rest in pairs either side of it
    arc = sorted(p for p in ring if p[0] < TX0 and p[1] <= SUN_CZ)
    for deg in range(180, 90, -ARC_STEP):
        a = math.radians(deg)
        ax, az = SUN_CX + SUN_R * math.cos(a), SUN_CZ - SUN_R * math.sin(a)
        x, z = min(arc, key=lambda p: (p[0] - ax) ** 2 + (p[1] - az) ** 2)
        piers |= {(x, z), (x, 2 * SUN_CZ - z)}
    return piers & ring


def _outward(cell, cells):
    """The sides of an outline cell that face out, as [(dx, dz)]: two at a corner, none at an
    inner corner."""
    x, z = cell
    return [(dx, dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (x + dx, z + dz) not in cells]


def _lay_terrace(c, o, m):
    ox, oy, oz = o
    cells = upper_cells()
    ring = set(K.outline(cells))
    inner = {p for p in K.outline(cells - ring)}
    for x, z in cells:                                  # the floor
        c.set(ox + x, oy + TOP, oz + z, K.KERB if (x, z) in ring else K.EDGE if (x, z) in inner else K.FIELD)
    plain = cells - ring - inner
    for x in range(PAD[0] + 1, PAD[2]):                 # the mast pad is an annex: the terrace's course runs on across its mouth
        if (x, TZ0 + 1) in plain:
            c.set(ox + x, oy + TOP, oz + TZ0 + 1, K.EDGE)
    fx = K.FOOT_STRIP_X                                 # the foot strip of the entrance front, end to end
    for z in range(TZ0 + 2, TZ1 - 1):
        for x, stone in ((fx - 1, K.EDGE), (fx + 1, K.EDGE), (fx, K.STRIP)):
            if (x, z) in plain:
                c.set(ox + x, oy + TOP, oz + z, stone)
    near = min(abs(z - S.ARMILLARY[1]) for z in _apse_lines())
    for x in range(GX0, TX0 + 1):                       # the sunset terrace: the forecourt's middle, again
        for z in range(-near - 1, near + 2):
            if (x, z) not in plain:
                continue
            walk = abs(z) <= WALK_HALF or abs(z) == near
            c.set(ox + x, oy + TOP, oz + z, K.STRIP if walk else K.EDGE)

    # the rim wall under the kerb, with a buttress under every pier; not on the east lip (site/stair's wall)
    H, valid = m["H"], m["valid"]
    piers = rail_piers(ring)
    for x, z in ring:
        if x == TX1 and TZ0 < z < TZ1:
            continue
        depth = BASTION_DEPTH if x < TX0 else RIM_DEPTH
        for y in range(TOP - 1, TOP - depth - 1, -1):
            if c.has(ox + x, oy + y, oz + z):
                c.set(ox + x, oy + y, oz + z, RIM)
        if (x, z) not in piers or x == TX1:
            continue
        for out in _outward((x, z), cells):
            bx, bz = x + out[0], z + out[1]
            i, k = bx - GX0, bz - GZ0
            foot = int(H[i, k]) if valid[i, k] else FLOOR
            facing = {(1, 0): "west", (-1, 0): "east", (0, 1): "north", (0, -1): "south"}[out]
            for y in range(TOP - 2, max(foot, TOP - BUTTRESS_DEPTH) - 1, -1):
                c.set(ox + bx, oy + y, oz + bz, BUTTRESS.block)
            if foot < TOP - 1:
                c.set(ox + bx, oy + TOP - 1, oz + bz, f"{BUTTRESS.stairs}[facing={facing},half=bottom]")

    # the railing: everything but the east lip (site/court's) and the gaps
    gaps = {p for cells_ in GAPS.values() for p in cells_}
    run = [p for p in ring if p[0] != TX1 and p not in gaps]
    K.rail(c, o, run, piers, kerb=False)


def _apse_lines():
    """z of the pilaster lines of the centre pavilion, as on the entrance front: the west door's bay
    and the apse's outer pilasters stand on them (main/facade, c206 #20473)."""
    first, last = S.CENTRE_BAYS[0], S.CENTRE_BAYS[-1]
    return [S.pilaster_z(first - 1), S.pilaster_z(last)]


# ---- the ring of cloud: the first draft's, kept until sky/cloudsea lands ---------------------------------
def _cloud_sea(c, o, m):
    """A flat sheet of cloud round the mountain, where the rock is below the cloud line or absent.
    Lighter towards the west, where the afterglow catches the sea."""
    ox, oy, oz = o
    H, valid = m["H"], m["valid"]
    above = valid & (H >= CLOUD_TOP)        # where the mountain stands out of the sea
    X, Z = np.meshgrid(m["xs"].astype(float), m["zs"].astype(float), indexing="ij")
    cx = round((X[above].min() + X[above].max()) / 2.0)
    cz = round((Z[above].min() + Z[above].max()) / 2.0)
    r = int(math.ceil(float(np.hypot(X[above] - cx, Z[above] - cz).max()))) + CLOUD_MARGIN
    xs = np.arange(cx - r, cx + r + 1)
    zs = np.arange(cz - r, cz + r + 1)
    CX, CZ = np.meshgrid(xs.astype(float), zs.astype(float), indexing="ij")
    tone = _cloud_tone(CX, CZ, 0.55 + 0.5 * np.maximum(0.0, (cx - CX) / r))    # lighter to the west
    inside = np.hypot(CX - cx, CZ - cz) <= r
    for i, k in zip(*np.nonzero(inside)):
        x, z = int(xs[i]), int(zs[k])
        gi, gk = x - GX0, z - GZ0
        if 0 <= gi < H.shape[0] and 0 <= gk < H.shape[1] and above[gi, gk]:
            continue
        for y in range(CLOUD_TOP, CLOUD_BOTTOM - 1, -1):
            c.set(ox + x, oy + y, oz + z, CLOUD[tone[i, k]], keep=True)


def _cloud_tone(x, z, lift):
    """Which of the five cloud tones (arrays); `lift` biases towards the light end."""
    n = N.fbm2(x * 0.08, z * 0.08, SEED + 20, octaves=2)
    v = np.clip(0.5 + 0.5 * n + 0.6 * (lift - 0.75), 0.0, 1.0)
    return np.rint(v * (len(CLOUD) - 1)).astype(int)


def build(canvas, origin=(0, 0, 0)):
    m = mountain()
    _lay_mountain(canvas, origin, m)
    _lay_terrace(canvas, origin, m)
    _cloud_sea(canvas, origin, m)
    return 0
