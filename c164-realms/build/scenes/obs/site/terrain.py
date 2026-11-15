"""site/terrain: the hilltop the observatory stands on, read as an outline (plan/ART-PLAN.md 4,
card plan/packages/site/terrain.md). Three things, all in blocks:

  - the mountain: a crust of dark rock that caps the upper terrace at y = -1 and falls away on the
    west, north and south into the cloud, so the pale building reads as a silhouette on a dark base
    (V1), a three-quarter mass with the afterglow on its west flank (V11) and a tidy plateau from
    above (V12). It is an OUTLINE and never rises above the terrace, so it cannot steal the front
    (the red line, plan 1): every column is at y = -1 or below.
  - the cloud sea: a flat sheet of the five cloud tones that laps round the mountain where the rock
    has fallen below the cloud line, lighter on the west rim where the afterglow catches it. A
    stand-in for A2's cloudsea (card: aligned with it when it lands), so the picture reads with the
    vanilla clouds switched off as well as on.
  - the sunset terrace: the half-round platform off the rotunda's west side (V11), ashlar paving on
    a slate plinth with an open ashlar-and-iron rail, kept clear of the rotunda's own circle.

The east slope, the grand stair and the lower platform are A0's to pin down (the drop is under
review); the mountain stops at the terrace's east lip until then, so nothing here is built on a
figure that is about to move. Blocks only, no display entities.
"""
import math

import numpy as np

from artkit import noise as N
from artkit.canvas import Mix

from ..common import blocks as B
from ..common import skeleton as S

ORDER = 10      # the ground goes down first, before the paving (court, 60) and the shells

# --- the cloud line (A2's sky/mood: the vanilla layer tops at scene y -28, the block sheet at -26) -
CLOUD_TOP = -26                 # the top face of the block cloud sheet
CLOUD_BOTTOM = -28              # two courses of cloud; the mountain plunges past it
CLOUD_SINK = CLOUD_BOTTOM - 1   # a rim column is carried this low so it reads as sunk in the sea
CLOUD_RADIUS = 86               # how far the sea is drawn before the fog takes it

# --- where the hilltop sits -----------------------------------------------------------------------
MESA_TOP = S.PAVING_Y           # -1, the rock cap under the terrace paving
EAST_LIP = S.FRONT_COURT[2] + 1  # 61, the court's east edge; the mountain stops here (east slope TBD)
CLOUD_CENTRE = (13.0, 0.0)      # the middle of the hilltop footprint; the sea is drawn round it
SLOPE = 0.72                    # blocks of fall per block out from the terrace edge
SEED = 164

# the flat top: the building and court rectangle, kept level with the terrace
PLATEAU = (S.WALL_W - 10, S.Z_NORTH - 4, EAST_LIP, S.Z_SOUTH + 4)   # x -10..61, z -38..38

# the sunset terrace (skeleton SUNSET_PLATFORM): a west half-circle off the rotunda
SUN_CX, SUN_CZ = S.SUNSET_PLATFORM["centre"]    # (-9, 0)
SUN_R = S.SUNSET_PLATFORM["radius"]             # 20

# --- materials (occupancy table only) -------------------------------------------------------------
# dark craggy rock, tuff over the deepslate families; a mix so no face reads flat (plan 6 flatwall)
ROCK_HIGH = Mix({B.TUFF.block: 11, B.TUFF_SMOOTH.block: 3, B.SLATE_SMOOTH.block: 4,
                 B.TUFF_BRICK.block: 2, B.SLATE_TILE.block: 1}, seed=SEED + 1)
ROCK_LOW = Mix({B.SLATE_SMOOTH.block: 9, B.TUFF.block: 4, B.SLATE_TILE.block: 3,
                B.SLATE_BRICK.block: 2}, seed=SEED + 2)
ROCK_SPLIT = -11                # above this the high mix, below it the low mix

PAVE = Mix({B.ASHLAR_FINE.block: 11, B.ASHLAR_ROUGH.block: 3, B.ASHLAR_PANEL.block: 2}, seed=SEED + 3)
PLINTH = Mix({B.SLATE_BRICK.block: 9, B.SLATE_TILE.block: 3, B.SLATE_SMOOTH.block: 2}, seed=SEED + 4)
POST = B.ASHLAR_ROUGH.block
CAP = B.ASHLAR_PANEL.slab
RAIL = B.IRON_BARS
BUTTRESS = B.SLATE_BRICK.block

# the five cloud tones (blocks.CLOUD, dark to light); a stand-in until A2's cloudsea lands
CLOUD = B.CLOUD


def _rock(x, y, z):
    return ROCK_HIGH(x, y, z) if y > ROCK_SPLIT else ROCK_LOW(x, y, z)


def _dist_to_plateau(x, z):
    """Distance from a column to the flat top (0 inside it), measured to the building/court
    rectangle and to the sunset half-circle, whichever is nearer."""
    x0, z0, x1, z1 = PLATEAU
    dx = max(x0 - x, x - x1, 0.0)
    dz = max(z0 - z, z - z1, 0.0)
    d_rect = math.hypot(dx, dz)
    d_sun = max(0.0, math.hypot(x - SUN_CX, z - SUN_CZ) - SUN_R) if x <= SUN_CX else d_rect
    return min(d_rect, d_sun)


def _surface(x, z):
    """The rock surface height of a column, or None where it has fallen too far to be worth drawing.
    The plateau is flat at MESA_TOP; outside it the ground falls away with some crag, reaching the
    cloud line and sinking past it at the rim."""
    d = _dist_to_plateau(x, z)
    if d <= 0.0:
        return MESA_TOP
    rugged = 0.0
    if d > 1.0:
        big = N.fbm2(np.array(x * 0.035), np.array(z * 0.035), SEED + 10, octaves=3)
        fine = N.fbm2(np.array(x * 0.12), np.array(z * 0.12), SEED + 11, octaves=2)
        amp = min(1.0, (d - 1.0) / 6.0)
        rugged = amp * (4.2 * float(big) + 1.6 * float(fine))
    y = MESA_TOP - SLOPE * d + rugged
    if y < CLOUD_SINK - 5:
        return None
    return int(round(y))


def _heightfield():
    """{(x, z): surface y} for every column of the mountain (nothing east of the lip)."""
    x0 = int(SUN_CX - SUN_R - 8)
    x1 = EAST_LIP
    z0 = int(S.Z_NORTH - 42)
    z1 = int(S.Z_SOUTH + 42)
    field = {}
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            y = _surface(x, z)
            if y is not None:
                field[(x, z)] = y
    return field


def _mountain(c, o):
    """A watertight height-map crust: each column is filled from its surface down only as far as it
    takes to close the step to its lowest neighbour, and columns on the rim are carried into the
    cloud. The inside stays hollow (it is never seen under the terrace), so the block count is small."""
    ox, oy, oz = o
    field = _heightfield()
    for (x, z), top in field.items():
        floor = top
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = field.get((x + dx, z + dz))
            floor = min(floor, CLOUD_SINK if n is None else n)
        for y in range(top, floor - 1, -1):
            c.set(ox + x, oy + y, oz + z, _rock(x, y, z))
    return field


def _cloud_sea(c, o, field):
    """A flat sheet of cloud round the mountain, where the rock is below the cloud line or absent.
    Lighter towards the west, where the afterglow catches the sea (c190's review); it keeps clear of
    the rock (the land pokes through), a stand-in for A2's cloudsea."""
    ox, oy, oz = o
    cx, cz = CLOUD_CENTRE
    r = CLOUD_RADIUS
    for x in range(int(cx - r), int(cx + r) + 1):
        for z in range(int(cz - r), int(cz + r) + 1):
            if math.hypot(x - cx, z - cz) > r:
                continue
            top = field.get((x, z))
            if top is not None and top >= CLOUD_TOP:
                continue                    # the mountain stands above the sea here
            west = (cx - x) / float(r)      # 1 at the west rim, negative to the east
            lift = 0.55 + 0.5 * max(0.0, west)
            tone = _cloud_tone(x, z, lift)
            for y in range(CLOUD_TOP, CLOUD_BOTTOM - 1, -1):
                c.set(ox + x, oy + y, oz + z, tone, keep=True)


def _cloud_tone(x, z, lift):
    """One of the five cloud tones; `lift` biases towards the light end (the west, the open sea)."""
    n = N.fbm2(np.array(x * 0.08), np.array(z * 0.08), SEED + 20, octaves=2)
    v = 0.5 + 0.5 * float(n) + 0.6 * (lift - 0.75)
    i = int(round(max(0.0, min(1.0, v)) * (len(CLOUD) - 1)))
    return CLOUD[i]


def _sunset_platform(c, o):
    """The half-round terrace off the rotunda's west side: ashlar paving on a slate plinth with an
    open rail, kept out of the rotunda's circle (centre DOME_CENTRE, radius DOME_R)."""
    ox, oy, oz = o
    cx, cz = int(SUN_CX), int(SUN_CZ)
    r = SUN_R
    dcx, dcz = S.DOME_CENTRE
    paved = set()
    for x in range(cx - r, cx + 1):             # the west half only
        for z in range(cz - r, cz + r + 1):
            if math.hypot(x - cx, z - cz) > r - 0.5:
                continue
            if math.hypot(x - dcx, z - dcz) <= S.DOME_R + 0.5:
                continue                        # do not enter the rotunda's circle
            c.set(ox + x, oy + S.PAVING_Y, oz + z, PAVE)
            paved.add((x, z))
    # the plinth that retains the rim, with a buttress every few blocks so no face reads flat
    rim = [(x, z) for (x, z) in paved
           if any((x + dx, z + dz) not in paved for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    for x, z in rim:
        deep = 6 if ((x * 7 + z) % 5 == 0) else 4       # the buttresses reach a little lower
        for y in range(S.PAVING_Y, S.PAVING_Y - deep - 1, -1):
            c.set(ox + x, oy + y, oz + z, PLINTH)
    # an open rail round the arc: a stone post every ~18 degrees, iron bars between, on the rim
    post_cells = set()
    for deg in range(90, 271, 18):
        a = math.radians(deg)
        x = int(round(cx + (r - 0.5) * math.cos(a)))
        z = int(round(cz + (r - 0.5) * math.sin(a)))
        post_cells.add((x, z))
    for x, z in rim:
        if (x, z) in post_cells:
            c.set(ox + x, oy + S.GROUND, oz + z, POST)
            c.set(ox + x, oy + S.GROUND + 1, oz + z, POST)
            c.set(ox + x, oy + S.GROUND + 2, oz + z, CAP)
        else:
            c.set(ox + x, oy + S.GROUND, oz + z, RAIL)


def build(canvas, origin=(0, 0, 0)):
    field = _mountain(canvas, origin)
    _cloud_sea(canvas, origin, field)
    _sunset_platform(canvas, origin)
    return 0
