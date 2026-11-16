"""site/terrain: the mountain the observatory stands on, the floor and the edge of the upper terrace
round the building, and the sunset terrace on the west (plan/ART-PLAN.md 4, card
plan/packages/site/terrain.md). Blocks only.

The mountain is an outline and a base, never a subject: nothing of it rises above the terrace
(y -1), and it stays a big step darker than the building. What gives it a shape (review 4):

  - form. Not an even slope: bands of cliff with shelves between them. The rock lies in beds that
    undulate and dip a little; the hard beds stand as cliffs four to eight blocks high, the shelves
    at their feet are a few blocks wide where the mountain is steep and wide on the ridges. Ridges
    run out from the terraces and gullies cut in between them, so no two sides have the same
    outline: long spurs to the north and south, the lower platform cut into the east side
    with one ridge beyond it for the cable track, and on the west, under the sunset terrace, a
    prow with benches of its own (review cr2-#2): no two of them run round it together. A wide
    bench close under the wall on the south-west, a sheer face down to a wide bench on the
    north-west, a keel running out west by north.
  - rock. Natural faces only (deepslate, cobbled deepslate, tuff, a little stone and andesite), laid
    in the same beds that make the cliffs, one to three blocks thick, so no face is flat and the
    lines of the beds follow the shelves. What is built -- the terrace's rim wall, its buttresses --
    is slate brick, and the eye can tell it from the mountain. The wall stands on the rock: along
    each bay between two buttresses the rock at its foot is level, and from bay to bay it steps,
    so the wall is two courses high where a ridge leaves the terrace and five at the head of a
    gully.
  - snow. Lies in ragged drifts against the feet of the cliffs, along about a third of their
    length (a fifth of the shelves' area): one layer thin at its edge, thicker towards the cliff,
    none on the brink of a drop or on a knob of rock. It draws the shelves; it must not outshine the building (its colour is
    materials/snow's). SNOW_ON switches it off for the pictures without it.

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

The foot stands in sky/cloudsea's sea (blocks; its face is y -28, the surf against the rock
reaches y -24). The rock has no top lower than K.ROCK_LOWEST (-28): what would lie lower is left
out, and the outermost columns go straight down to K.ROCK_SKIRT (-34) as a wall under the sea, so
there is no shelf and no floor of rock under the cloud for anybody to stand on (agreed with outb for
common/export's way home, #62548). The first draft's stand-in ring of cloud went when the sea came
(11-16).
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
LOWEST = K.ROCK_LOWEST          # -28: the lowest top the rock has; a column that would end lower is no rock at all
SKIRT = K.ROCK_SKIRT            # -34: the outermost columns are carried straight down to here, under the sea
NEEDLE = -24                    # a column no higher than this (where the surf reaches) with rock on one side at the
#                                 most is left out too: it would stand in the cloud as a post

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
    dict(start=(-29, -4), heading=(-1, -0.20), y0=-6.5, a=0.85, b=0.020, side=2.2),     # west by north, the keel of the prow under the sunset terrace
)
# A gully: where it starts under the terrace's edge, its heading, how deep it cuts, its half-width
# at the start and how fast it widens.
WEST_GULLIES = (
    dict(start=(-12, -23), heading=(-1, -0.25), depth=7.0, width=3.0, grow=0.10),       # either side of the sunset
    dict(start=(-12, 23), heading=(-1, 0.45), depth=5.0, width=2.5, grow=0.07),         # terrace: it stands on a prow
)
GULLIES = WEST_GULLIES + (
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

# --- the foot of the mountain, at the cloud ------------------------------------------------------------
# The beds dip to the west and south, and there the lowest shelf of BANDS would lie within two blocks
# of the cloud: a ledge a block or three wide running round the foot like the rim of a tray (review
# cr2-#5). So a shelf that would lie that low does not stay where the beds put it. Along half of the
# foot it is sunk under the cloud, and the cliff above it falls straight into the sea; along the
# other half it is lifted clear and stands as a bench of its own. Which, a slow noise says.
FOOT_NEAR = (-22.5, -23.5)      # the lowest shelf is left alone above the first of these, wholly treated below the second
FOOT_CLEAR = (-20.5, -22.5)     # lifted, it lies between these levels (by a second slow noise)
FOOT_SUNK = -31.0               # sunk, here: lower than the lowest top the rock has, so no shelf is left at all
FOOT_SCALE = 0.03               # the scale of the noise: benches and plunges fifteen to thirty blocks long
FOOT_SHARE = 0.0                # the noise is above this where the bench stands: on about half of the foot

# --- the prow under the sunset terrace ----------------------------------------------------------------
# Between the two west gullies the rock does not follow the bands above. It has three benches of
# its own, and the level and the width of each change with the bearing from the terrace's middle
# (degrees: 0 due west, + to the south), so the benches do not run round the prow as three rings:
# where one is wide the next is a ledge, and the cliffs between them are four blocks high here,
# eight and more there. Levels are in the mountain's own heights, as BANDS (on the west the rock
# itself stands about 1.7 lower); widths are in blocks.
PROW_DEG = (-90, -60, -30, 0, 15, 30, 45, 60, 75, 90)
PROW_BENCHES = (
    # close under the wall and on the south-west only: four blocks below the wall's foot
    dict(level=(-5.5, -5.5, -5.5, -5.5, -6.0, -6.7, -7.0, -7.0, -7.0, -7.0),
         width=(0.0, 0.0, 0.0, 0.0, 1.2, 3.5, 6.5, 6.0, 3.5, 1.5)),
    # the middle one: wide on the north-west, at the foot of a sheer face; a ledge on the south-west
    dict(level=(-12.5, -13.0, -13.8, -14.5, -15.2, -16.0, -16.5, -16.5, -16.5, -16.5),
         width=(3.0, 5.5, 5.0, 3.0, 2.2, 1.6, 1.5, 1.5, 2.0, 2.5)),
    # the lowest: not a ledge round the whole foot, just above the cloud, like the rim of a tray
    # (review cr2-#5), but one bench on the west, where the two above it are narrow, four blocks
    # clear of the cloud; everywhere else the cliff falls straight into the sea
    dict(deg=(-90, -12, -4, 20, 28, 90),
         level=(-22.0, -22.0, -21.0, -21.0, -22.0, -22.0),
         width=(0.0, 0.0, 4.5, 4.5, 0.0, 0.0)),
)
PROW_JOG = 1.6                  # each bench's cliff steps a block in or out every five or six along it (a noise of this
PROW_JOG_SCALE = 0.09           # weight and this scale, its own for each bench): no cliff runs on as a ruled line
PROW_CLIFF = 0.8                # the run of the cliff above a bench, in blocks: all but sheer
PROW_SHELF = (0.13, 0.10, 0.10) # the share of its band's height that each bench keeps, as SHELF
PROW_START = 0.9                # the first cliff starts this far out from the terrace
PROW_PLUNGE = 3.0               # below the lowest bench the rock is down at BANDS[-1] within this many blocks
PROW_FADE = 6.0                 # coming up to a gully's line the prow gives way to the bands over this distance

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

# --- snow ---------------------------------------------------------------------------------------------
# Review cr2-#2 and A0 #330: less of it (the second draft had it on a quarter of the shelves' area, in
# slabs), ragged edges, one layer at the edge and thicker towards the cliff, none on a knob of rock.
# How light it is belongs to materials/snow.
SNOW_ON = True                  # False: no snow at all (the pictures taken with and without it)
SNOW_BELOW = -7                 # none on the rock just under the terraces: it starts below the rim wall's foot
SNOW_ABOVE = -24                # ... and none where the sea's surf reaches (sky/cloudsea heaps cloud against the rock up
#                                 to here): the sea's edge is the cloud's own light line
SNOW_DRIFT = -0.3               # it lies in drifts: where a slow noise is above this. With the rules below that leaves a
#                                 drift at the foot of a third of the cliffs' length, on a fifth of the shelves' area: 716
#                                 columns in 23 patches (at 0.10, the first guess, it was eight puddles on the whole
#                                 mountain; at -0.15 the shorter straight edges of SNOW_RUN = 2 ate it down to 503)
SNOW_FRAY = 0.25                # ... with this much of a fine noise on top, so that a drift has no smooth outline
SNOW_REACH = 0.62               # out from the cliff's foot it covers this much of a shelf's width
SNOW_SWING = 0.9                # ... more here and less there, by a noise of this weight
SNOW_RUN = 2                    # no edge of it runs straight for more blocks than this (review cr2-#5: at 4 a drift
#                                 still read as a sheet laid on the rock)
SNOW_NOTCH = 0.35               # the share of the notches cut into a straight edge that go two blocks deep
SNOW_PASSES = 12                # how often the straight edges are looked for again after breaking them
SNOW_PATCH = 12                 # no patch of fewer blocks than this
SNOW_OPEN = 40                  # a patch of this many blocks or more has rock showing through it in two places,
SNOW_OPEN_MORE = 70             # ... of this many in three,
SNOW_OPEN_APART = 4             # ... no nearer to each other than this
SNOW_DEEP = 4                   # layers (eighths of a block) at the most; one layer at an edge

# --- what is built on the rim -------------------------------------------------------------------------
RIM = B.SLATE_BRICK.block       # the terrace's rim wall under the kerb, down to the rock
RIM_LOW, RIM_HIGH = -7, -4      # the rock at its foot lies between these: five courses of the wall show, or two
RIM_BASE = -5.0                 # ... about here on the straight edges,
RIM_NOISE = 2.0                 # higher and lower by a slow noise of this weight,
RIM_GULLY = 2.6                 # lower by this where a gully heads under the wall
RIM_GULLY_NEAR = 6.0            # (within about this distance of where it starts)
RIM_RIDGE = 1.4                 # and higher by this where a ridge leaves it
RIM_RIDGE_NEAR = 5.0
# round the sunset terrace by the bearing, as PROW_DEG: the wall is tallest on the nose and at the two
# gullies, lowest over the wide bench on the south-west
RIM_ARC_DEG = (-90, -70, -45, -20, 0, 15, 35, 55, 72, 90)
RIM_ARC = (-7.0, -6.0, -5.0, -6.0, -7.0, -6.4, -5.0, -4.0, -5.0, -7.0)
RIM_RISE = 1.5                  # going out from the wall's foot the rock rises no faster than this per block
RIM_REACH = 5                   # ... which matters no further out than this
BUTTRESS = B.SLATE_BRICK        # one under every pier, a block proud of the wall, weathered at the top
WALK_HALF = 2                   # the walk from the west door is the door bay with its two pilasters: 5 across
ARC_BAYS = 11                   # the bays of the railing round the sunset terrace's arc, an odd count: the axis runs
#                                 out through an open bay as wide as the walk from the west door, a pier either side

# --- the first draft's ring of cloud is gone (sky/cloudsea lays the sea) ------------------------------
# Its two levels stay for the one reader they have left, site/cablecar's test scene, which lays a
# stand-in sheet of its own by them; they go when that sheet does.
CLOUD_TOP = -26
CLOUD_BOTTOM = -28


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


def _beds(y, levels=BANDS, cliff=CLIFF, shelf=SHELF, lie=None):
    """What the beds make of a smooth height (the mountain's own heights, an array): the height
    itself above the first band and below the last; inside a band a cliff, then a shelf. Returns
    the new height and, for a cell on a shelf, how far out on it the cell lies (0 at the cliff's
    foot .. 1 at the shelf's edge; -1 elsewhere). The three tables may hold arrays in y's shape
    instead of numbers: every cell then has its own bands (the prow under the sunset terrace).
    `lie`: the levels the bands come to lie at, where that is not `levels` themselves -- a band
    still takes the ground between its two levels, but its cliff falls and its shelf lies between
    the two of `lie` (the foot of the mountain: FOOT_*). The first and the last are the same in both."""
    lie = levels if lie is None else lie
    out = y.copy()
    where = np.full(y.shape, -1.0)
    for k in range(len(levels) - 1):
        top, bot = levels[k], levels[k + 1]
        height = top - bot
        steep, flat = cliff[k], shelf[k]
        m = (y <= top) & (y > bot)
        u = (top - y) / height
        on_cliff = u < steep
        along = (u - steep) / np.maximum(1 - steep, 1e-6)       # 0..1 across the shelf
        fall = np.where(on_cliff, u / np.maximum(steep, 1e-6) * (1 - flat), (1 - flat) + along * flat)
        out = np.where(m, lie[k] - fall * (lie[k] - lie[k + 1]), out)
        where = np.where(m, np.where(on_cliff, -1.0, along), where)
    return out, where


def _foot(X, Z, dip):
    """The level the lowest shelf of BANDS comes to lie at, in the mountain's own heights, for every
    cell (FOOT_*): BANDS' own where that is clear of the cloud, and where it is not, either lifted
    clear or sunk under the cloud."""
    own = float(BANDS[3])
    near = N.smoothstep(FOOT_NEAR[0], FOOT_NEAR[1], own + dip)
    stands = N.smoothstep(FOOT_SHARE - 0.03, FOOT_SHARE + 0.03, N.fbm2(X * FOOT_SCALE, Z * FOOT_SCALE, SEED + 91, octaves=2))
    high = np.clip(0.5 + N.fbm2(X * 0.05, Z * 0.05, SEED + 92, octaves=2), 0.0, 1.0)
    clear = FOOT_CLEAR[0] + (FOOT_CLEAR[1] - FOOT_CLEAR[0]) * high
    level = stands * clear + (1 - stands) * FOOT_SUNK
    return own + near * (level - dip - own)


def _bearing(X, Z):
    """Degrees round the middle of the sunset terrace: 0 due west, + to the south."""
    return np.degrees(np.arctan2(Z - SUN_CZ, -(X - SUN_CX)))


def _by_bearing(deg, table, values):
    """`values` (given at the bearings in `table`) at every bearing of the array `deg`."""
    return np.interp(deg.ravel(), table, values).reshape(deg.shape)


def _prow(X, Z, s_up):
    """The rock under the sunset terrace, between the two west gullies (PROW_BENCHES). Returns how
    far each cell belongs to it (0..1), its smooth height there in the mountain's own heights, and
    the three tables _beds wants for it: the levels (the terrace, the three benches, BANDS'
    floor), the cliff's share of each band's run, the share of its height that each bench keeps."""
    inside = (X < TX0).astype(float)
    mx, mz = SUN_CX - SUN_R - 5.0, float(SUN_CZ)        # a point on the prow, between the gullies
    for g in WEST_GULLIES:
        _, lat = _along(X, Z, g["start"], g["heading"])
        _, mid = _along(mx, mz, g["start"], g["heading"])
        inside = inside * N.smoothstep(0.0, PROW_FADE, lat if mid > 0 else -lat)
    deg = _bearing(X, Z)
    s = np.maximum(s_up - PROW_START, 0.0)
    base = np.full(X.shape, float(TOP))
    at = np.zeros(X.shape)                              # how far out the band begins
    levels, cliff, keep = [np.full(X.shape, float(TOP))], [], []
    for k, (bench, share) in enumerate(zip(PROW_BENCHES, PROW_SHELF)):
        table = bench.get("deg", PROW_DEG)
        level = _by_bearing(deg, table, bench["level"])
        width = _by_bearing(deg, table, bench["width"])
        there = np.clip(width, 0.0, 1.0)                # under a block wide a bench fades out: all cliff
        run_cliff = PROW_CLIFF * (0.5 + 0.5 * there)
        run = run_cliff + width
        jog = PROW_JOG * N.perlin2(X * PROW_JOG_SCALE + 31.7 * k, Z * PROW_JOG_SCALE, SEED + 93 + k) * np.clip(s / 3.0, 0.0, 1.0)
        base = base - (levels[-1] - level) * np.clip((s + jog - at) / run, 0.0, 1.0)
        at = at + run
        levels.append(level)
        cliff.append(run_cliff / run)
        keep.append(share * there)
    floor = float(BANDS[-1])
    base = base - (levels[-1] - floor) * np.maximum(s - at, 0.0) / PROW_PLUNGE
    levels.append(np.full(X.shape, floor))
    cliff.append(np.ones(X.shape))
    keep.append(np.zeros(X.shape))
    return inside, base, levels, cliff, keep


def _mountain():
    """Every column of the mountain: dict(xs, zs, H, valid, upper, kept, shelf, dip, foot), arrays
    over the worked area. H is the y of the topmost block, valid says where there is rock at all;
    foot is the level given to the rock at the rim wall's foot (inf where it has none)."""
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
    # the beds undulate and dip to the west; cliffs and shelves follow them
    dip = 2.3 * N.fbm2(X * 0.016, Z * 0.016, SEED + 31, octaves=3) + 0.03 * (X - 25.0) - 0.012 * Z
    # under the sunset terrace the prow's own slope takes the place of the even one
    prow, base, levels, cliff, keep = _prow(X, Z, s_up)
    smooth = smooth + prow * (base + dip - smooth)
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

    # the beds: everywhere BANDS, on the prow its own benches, one going over into the other; and
    # the lowest shelf of BANDS, where it would lie at the cloud, lifted or sunk (_foot)
    lie = [float(b) for b in BANDS]
    lie[3] = _foot(X, Z, dip)
    lie = [lie[k] + prow * (levels[k] - lie[k]) for k in range(len(BANDS))]
    levels = [BANDS[k] + prow * (levels[k] - BANDS[k]) for k in range(len(BANDS))]
    cliff = [CLIFF[k] + prow * (cliff[k] - CLIFF[k]) for k in range(len(CLIFF))]
    keep = [SHELF[k] + prow * (keep[k] - SHELF[k]) for k in range(len(SHELF))]
    h, shelf = _beds(smooth - dip, levels, cliff, keep, lie)
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

    # the rock at the rim wall's foot: level along each bay of the wall, stepping from bay to bay;
    # going out from there it may rise again, but not as a second wall in front of the first
    cells = {(int(xs[i]), int(zs[k])) for i, k in zip(*np.nonzero(upper))}
    steps = neck_steps()
    foot = np.full(h.shape, np.inf)
    for (x, z), y in _footing(cells, N.fbm2(X * 0.06, Z * 0.06, SEED + 81, octaves=2)).items():
        if not kept[x - GX0, z - GZ0] and (x, z) not in steps:
            foot[x - GX0, z - GZ0] = y
    at_foot = np.isfinite(foot)
    cap = np.full(h.shape, np.inf)
    for dx in range(-RIM_REACH, RIM_REACH + 1):
        for dz in range(-RIM_REACH, RIM_REACH + 1):
            rise = RIM_RISE * max(math.hypot(dx, dz) - 0.5, 0.0)
            cap = np.minimum(cap, np.roll(foot, (dx, dz), axis=(0, 1)) + rise)
    capped = ~kept & ~at_foot & (cap < h)
    h = np.where(capped, cap, h)
    h = np.where(at_foot, foot, h)
    shelf = np.where(capped | at_foot, -1.0, shelf)
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
    valid = H >= LOWEST
    for _ in range(2):                  # no needle of rock alone in the surf: rock on one side of it at the most
        beside = sum(n.astype(int) for n in _neighbours(valid))
        valid &= kept | (beside >= 2) | (H > NEEDLE)
    return dict(xs=xs, zs=zs, H=H, valid=valid, upper=upper, kept=kept, shelf=shelf, dip=np.rint(dip).astype(int),
                foot=foot)


def _rim_want(x, z, noise):
    """The level the rock would have at the wall's foot beside the outline cell (x, z), before it
    is made level along a bay. `noise` is a slow noise over the worked area."""
    if x < TX0:                                         # round the sunset terrace: by the bearing
        deg = math.degrees(math.atan2(z - SUN_CZ, -(x - SUN_CX)))
        return float(np.interp(deg, RIM_ARC_DEG, RIM_ARC))
    y = RIM_BASE + RIM_NOISE * float(noise[x - GX0, z - GZ0])
    for g in GULLIES:
        y -= RIM_GULLY * math.exp(-(math.dist((x, z), g["start"]) / RIM_GULLY_NEAR) ** 2)
    for rg in RIDGES:
        y += RIM_RIDGE * math.exp(-(math.dist((x, z), rg["start"]) / RIM_RIDGE_NEAR) ** 2)
    return y


def _rim_level(y):
    return int(min(max(math.floor(y + 0.5), RIM_LOW), RIM_HIGH))


def _footing(cells, noise):
    """{(x, z): y}: the level of the rock in every cell outside the upper level (`cells`) that
    touches its rim wall, corners included.

    The wall is cut into bays by the piers, and a buttress stands under each pier. Along a bay the
    rock at the wall's foot is level; from bay to bay it steps, and the step is at the buttress,
    which stands on the lower of the two. So the wall reads as built on the mountain (review
    cr2-#2): short where the rock is high, tall where a gully heads under it. Not under the east
    lip (site/stair's wall goes down to the lower platform) nor where a path leaves the terrace."""
    ring = set(K.outline(cells))
    piers = rail_piers(ring)
    gaps = {p for run in GAPS.values() for p in run}
    walled = {p for p in ring if not (p[0] == TX1 and TZ0 < p[1] < TZ1)} - gaps
    level = {}
    left = walled - piers
    while left:                                         # the bays: the runs of the wall between two piers
        bay, todo = [], [left.pop()]
        while todo:
            x, z = todo.pop()
            bay.append((x, z))
            for q in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
                if q in left:
                    left.discard(q)
                    todo.append(q)
        y = _rim_level(sum(_rim_want(x, z, noise) for x, z in bay) / len(bay))
        level.update((p, y) for p in bay)
    for x, z in sorted(walled & piers):                 # a pier: the lower of the bays it stands between
        beside = [level[q] for q in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)) if q in level and q not in piers]
        level[(x, z)] = min(beside) if beside else _rim_level(_rim_want(x, z, noise))
    foot = {}
    for x, z in level:
        for ox in (x - 1, x, x + 1):
            for oz in (z - 1, z, z + 1):
                if (ox, oz) in cells or (ox, oz) in foot:
                    continue
                square = [q for q in ((ox + 1, oz), (ox - 1, oz), (ox, oz + 1), (ox, oz - 1)) if q in level]
                wall = [level[q] for q in square if q not in piers]
                if wall:                                # beside a bay (two, in an inner corner: the lower)
                    foot[(ox, oz)] = min(wall)
                elif square:                            # beside a pier only: where its buttress stands
                    foot[(ox, oz)] = min(level[q] for q in square)
                else:                                   # off an outer corner
                    foot[(ox, oz)] = min(level[q] for q in ((ox + 1, oz + 1), (ox + 1, oz - 1),
                                                            (ox - 1, oz + 1), (ox - 1, oz - 1)) if q in level)
    return foot


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


def _snow(m):
    """How many layers of snow lie on every column (eighths of a block; 0 where there is none).

    It lies on the shelves, from the foot of the cliff outwards, in drifts with bare rock between
    them. Not on the brink of a drop, not on a knob or a point of rock that stands proud of the
    ground round it, not as specks or lines. Its outline is ragged: no edge of it runs straight
    for more than SNOW_RUN blocks. And it is thin where it ends: one layer at an edge, a layer more
    with every block in from there, so that it reads as lying on the rock and not as a slab."""
    H, valid = m["H"], m["valid"]
    hi = np.where(valid, H, SKIRT)
    brink = np.zeros(H.shape, dtype=bool)               # a drop of two or more beside it
    lower = np.zeros(H.shape, dtype=int)                # how many of the four neighbours lie lower
    for n in _neighbours(hi):
        brink |= (hi - n) >= 2
        lower += (n < hi)
    around = lower.copy()                               # ... and of all eight
    for step in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        around += (np.roll(hi, step, axis=(0, 1)) < hi)
    proud = (lower >= 3) | (around >= 5)
    X, Z = np.meshgrid(m["xs"].astype(float), m["zs"].astype(float), indexing="ij")
    drift = (N.fbm2(X * 0.035, Z * 0.035, SEED + 61, octaves=3)
             + SNOW_FRAY * N.fbm2(X * 0.19, Z * 0.19, SEED + 62, octaves=2))
    reach = np.clip(SNOW_REACH + SNOW_SWING * N.fbm2(X * 0.07, Z * 0.07, SEED + 63, octaves=2), 0.3, 0.95)
    snow = (valid & ~m["kept"] & (m["shelf"] >= 0) & (m["shelf"] <= reach)
            & (H <= SNOW_BELOW) & (H >= SNOW_ABOVE) & ~brink & ~proud & (drift > SNOW_DRIFT))
    snow = _whole(snow)
    for _ in range(SNOW_PASSES):
        cut = _straight(snow, hi)
        if not cut.any():
            break
        snow = _tidy(snow & ~cut)
    snow = _patches(snow)
    snow &= ~_showing(snow, _layers(snow, hi), N.fbm2(X * 0.23, Z * 0.23, SEED + 66, octaves=2))
    return _layers(snow, hi)


def _whole(snow):
    """The cells of it that lie in a square of four: no specks, no lines one block wide."""
    square = snow & np.roll(snow, -1, axis=0) & np.roll(snow, -1, axis=1) & np.roll(snow, (-1, -1), axis=(0, 1))
    return square | np.roll(square, 1, axis=0) | np.roll(square, 1, axis=1) | np.roll(square, (1, 1), axis=(0, 1))


def _tidy(snow):
    """Without the cells that hang on to it by one side only (twice: a spike two long goes too)."""
    for _ in range(2):
        snow = snow & (sum(n.astype(int) for n in _neighbours(snow)) >= 2)
    return snow


def _notches(n, a, b, side):
    """Which cells of a straight edge n long are taken out, counted from its start: after every two
    that stay (or three, where SNOW_RUN allows it), one or two -- by the cell, not in a rhythm. A
    tooth is never a single cell, which _tidy would take off and the edge would only move back; so
    a notch that would leave one cell at the end takes that too."""
    out = []
    i = 0
    while n - i > SNOW_RUN:
        left = n - i
        stay = 3 if SNOW_RUN >= 3 and left >= 6 and hash3(a, b + i, side, SEED + 64) < 0.5 else 2
        take = 2 if left - stay >= 4 and hash3(a, b + i, side, SEED + 65) < 0.4 else 1
        if left - stay - take == 1:
            take += 1
        out += range(i + stay, min(i + stay + take, n))
        i += stay + take
    return out


def _straight(snow, hi):
    """The cells to take out of the snow so that none of its edges runs straight for more than
    SNOW_RUN blocks. An edge is where bare rock no higher than the snow lies beside it; against
    the foot of a cliff the snow may run as straight as the cliff does."""
    cut = np.zeros(snow.shape, dtype=bool)
    for side, (axis, step) in enumerate(((0, 1), (0, -1), (1, 1), (1, -1))):
        edge = snow & ~np.roll(snow, step, axis=axis) & (np.roll(hi, step, axis=axis) <= hi)
        rows = edge if axis == 0 else edge.T            # an edge that faces along x runs along z, and the other way round
        for a in np.flatnonzero(rows.any(axis=1)):
            on = np.flatnonzero(rows[a])
            ends = np.flatnonzero(np.diff(on) > 1)      # the last cell of every run but the last run
            for first, last in zip(np.concatenate(([0], ends + 1)), np.concatenate((ends, [len(on) - 1]))):
                b = int(on[first])
                for j in _notches(int(last - first + 1), int(a), b, side):
                    i, k = (int(a), b + j) if axis == 0 else (b + j, int(a))
                    cut[i, k] = True
                    if hash3(int(a), b + j, side, SEED + 67) < SNOW_NOTCH:      # ... and the cell behind it
                        cut[(i + step, k) if axis == 0 else (i, k + step)] = True
    return cut & snow


def _patches(snow):
    """Without the patches of fewer than SNOW_PATCH blocks (blocks that touch face to face)."""
    out = snow.copy()
    seen = np.zeros(snow.shape, dtype=bool)
    for i, k in zip(*np.nonzero(snow)):
        if seen[i, k]:
            continue
        seen[i, k] = True
        patch, todo = [], [(int(i), int(k))]
        while todo:
            a, b = todo.pop()
            patch.append((a, b))
            for p, q in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                if 0 <= p < snow.shape[0] and 0 <= q < snow.shape[1] and snow[p, q] and not seen[p, q]:
                    seen[p, q] = True
                    todo.append((p, q))
        if len(patch) < SNOW_PATCH:
            for a, b in patch:
                out[a, b] = False
    return out


def _showing(snow, deep, noise):
    """Rock showing through the big patches: the cells to take out of the snow. In a patch of
    SNOW_OPEN blocks or more two places, in one of SNOW_OPEN_MORE three, each one or two blocks,
    inside it (snow on all eight sides) and apart from each other; where the snow lies three
    layers deep before where it lies two, and among those where a fine noise says. The snow thins
    to one layer round them (_layers)."""
    out = np.zeros(snow.shape, dtype=bool)
    inside = snow.copy()
    for step in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        inside &= np.roll(snow, step, axis=(0, 1))
    seen = np.zeros(snow.shape, dtype=bool)
    for i, k in zip(*np.nonzero(snow)):
        if seen[i, k]:
            continue
        seen[i, k] = True
        patch, todo = [], [(int(i), int(k))]
        while todo:
            a, b = todo.pop()
            patch.append((a, b))
            for p, q in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                if 0 <= p < snow.shape[0] and 0 <= q < snow.shape[1] and snow[p, q] and not seen[p, q]:
                    seen[p, q] = True
                    todo.append((p, q))
        if len(patch) < SNOW_OPEN:
            continue
        want = 3 if len(patch) >= SNOW_OPEN_MORE else 2
        places = []
        for a, b in sorted((p for p in patch if inside[p]), key=lambda p: (-min(int(deep[p]), 3), -noise[p])):
            if all(max(abs(a - p), abs(b - q)) >= SNOW_OPEN_APART for p, q in places):
                places.append((a, b))
                out[a, b] = True
                beside = [(p, q) for p, q in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)) if inside[p, q]]
                if beside and hash3(a, 0, b, SEED + 68) < 0.5:
                    out[max(beside, key=lambda p: noise[p])] = True
            if len(places) == want:
                break
    return out


def _layers(snow, hi):
    """How deep the snow lies, in layers: one where it ends -- beside bare rock on its own level, or
    at a step down -- and a layer more with every block in from there, SNOW_DEEP at the most."""
    thin = np.zeros(snow.shape, dtype=bool)
    for n_hi, n_snow in zip(_neighbours(hi), _neighbours(snow)):
        thin |= (n_hi < hi) | ((n_hi == hi) & ~n_snow)
    deep = np.where(snow, np.where(thin, 1, SNOW_DEEP), 0)
    for _ in range(SNOW_DEEP - 1):
        near = deep.copy()
        for n_deep, n_snow in zip(_neighbours(deep), _neighbours(snow)):
            near = np.minimum(near, np.where(n_snow, n_deep + 1, SNOW_DEEP))
        deep = np.where(snow, near, 0)
    return deep


def _lay_mountain(c, o, m):
    """A watertight crust: every column from its top down as far as its lowest neighbour, the
    outermost columns down to the skirt's foot (SKIRT). Hollow inside; it is never seen."""
    ox, oy, oz = o
    H, valid, dip = m["H"], m["valid"], m["dip"]
    snow = _snow(m) if SNOW_ON else np.zeros(H.shape, dtype=int)
    low = H.copy()
    for axis, step in ((0, 1), (0, -1), (1, 1), (1, -1)):
        n = np.where(np.roll(valid, step, axis=axis), np.roll(H, step, axis=axis), SKIRT)
        low = np.minimum(low, n)
    low[0, :] = low[-1, :] = low[:, 0] = low[:, -1] = SKIRT
    low = np.maximum(low, SKIRT)
    X, Z = np.meshgrid(m["xs"].astype(float), m["zs"].astype(float), indexing="ij")
    lens_a = N.fbm2(X * 0.06, Z * 0.06, SEED + 71, octaves=2)
    lens_b = N.fbm2(X * 0.06, Z * 0.06, SEED + 72, octaves=2)
    for i, k in zip(*np.nonzero(valid)):
        x, z = int(m["xs"][i]), int(m["zs"][k])
        y1, y0, dp = int(H[i, k]), int(low[i, k]), int(dip[i, k])
        la, lb = float(lens_a[i, k]), float(lens_b[i, k])
        for y in range(y1, y0 - 1, -1):
            c.set(ox + x, oy + y, oz + z, _rock(x, y, z, dp, la, lb))
        if snow[i, k]:
            c.set(ox + x, oy + y1 + 1, oz + z, f"{SNOW}[layers={int(snow[i, k])}]")


# ---- the upper terrace: floor, rim, railing -------------------------------------------------------------
def upper_cells():
    m = mountain()
    return {(int(m["xs"][i]), int(m["zs"][k])) for i, k in zip(*np.nonzero(m["upper"]))}


def rail_piers(ring):
    """The cells of the outline that carry a pier. On the straight edges: the corners, either side
    of every gap, and between those as many as fit BEAT apart (the west edge keeps the pilaster
    lines of the west front). On the arc of the sunset terrace: ARC_BAYS even bays, none of the
    piers on the axis."""
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
    # the arc: ARC_BAYS even bays from one end of the straight edge round to the other, the middle
    # one astride the axis (who walks out along it looks at the sea, not at a pier); the piers
    # stand in pairs either side of it
    arc = sorted(p for p in ring if p[0] < TX0 and p[1] <= SUN_CZ)
    for k in range(ARC_BAYS // 2):
        a = math.radians(180 - (k + 0.5) * 180 / ARC_BAYS)
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

    # the rim wall under the kerb, from the kerb down to the rock at its foot (_footing), with a
    # buttress under every pier; not on the east lip (site/stair's wall)
    H, valid = m["H"], m["valid"]
    piers = rail_piers(ring)

    def rock(x, z):
        return int(H[x - GX0, z - GZ0]) if valid[x - GX0, z - GZ0] else SKIRT

    for x, z in ring:
        if x == TX1 and TZ0 < z < TZ1:
            continue
        sides = _outward((x, z), cells)
        if not sides:
            continue
        foot = min(rock(x + dx, z + dz) for dx, dz in sides)
        for y in range(TOP - 1, max(foot, RIM_LOW), -1):
            c.set(ox + x, oy + y, oz + z, RIM)
        if (x, z) not in piers or x == TX1:
            continue
        for out in sides:
            bx, bz = x + out[0], z + out[1]
            foot = rock(bx, bz)
            facing = {(1, 0): "west", (-1, 0): "east", (0, 1): "north", (0, -1): "south"}[out]
            for y in range(TOP - 2, max(foot, RIM_LOW) - 1, -1):
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


def build(canvas, origin=(0, 0, 0)):
    m = mountain()
    _lay_mountain(canvas, origin, m)
    _lay_terrace(canvas, origin, m)
    return 0
