"""Test scene of the card sky/ridges: the far hills seen from the terrace.

A plain place to stand on -- the terrace with the sunset platform at its west edge, the south
lookout where V11 stands, and nothing else: the hills are the whole subject and the main building
would only hide them. The sky is the blue look's, since that is the look the map is finished in
(director, A0 #43929). The panels are the ones `sky/ridges.build()` puts down.

    python -m scenes.obs_sky_ridges        writes shots.json; prints the elevations of the peaks
                                           and which bearings come out empty (the west, on purpose)
"""
import math

from artkit.canvas import Canvas

from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.sky import mood as look
from scenes.obs.sky import ridges

BIOME = "obs_blue"
BIOME_MARGIN = 480          # the look (and its fog) has to reach every camera position
BIOME_MARGIN_Y = 120

GROUND = B.TUFF_SMOOTH.block
PLINTH = B.SLATE_BRICK.block
CENTRE = (S.WALL_E + 0.0, S.AXIS_Z)         # what the eyes below stand around and look across


def _terrace(c):
    """The terrace: the upper paving with its edge, and the lower platform beyond it, so the eye
    stands where the map puts a visitor. No wall, no lamps: nothing but the ground."""
    x0, z0, x1, z1 = S.UPPER_TERRACE
    c.box(x0, S.PAVING_Y, z0, x1, S.PAVING_Y, z1, GROUND)
    c.box(x1, S.LOWER_PAVING_Y, z0, x1, S.PAVING_Y - 1, z1, PLINTH)
    c.box(x1 + 1, S.LOWER_PAVING_Y, z0, x1 + 39, S.LOWER_PAVING_Y, z1, GROUND)
    cx, r = S.SUNSET_PLATFORM["centre"]
    for dx in range(-r, r + 1):
        for dz in range(-r, r + 1):
            if dx * dx + dz * dz <= r * r:
                c.set(cx + dx, S.PAVING_Y, dz, GROUND)
    bx0, bz0, bx1, bz1 = S.SOUTH_LOOKOUT["box"]
    c.box(bx0, S.SOUTH_LOOKOUT["feet"] - 1, bz0, bx1, S.SOUTH_LOOKOUT["feet"] - 1, bz1, GROUND)


def build():
    c = Canvas()
    _terrace(c)
    c.entity_counts = ridges.build(c)
    return c


# ---- the shots -------------------------------------------------------------------------------------------
EYE = S.EYE


def eye(bearing, dist, y=None):
    """An eye on the terrace `dist` cells from its centre on compass bearing `bearing`."""
    b = math.radians(bearing)
    return (CENTRE[0] + math.sin(b) * dist,
            (S.GROUND + EYE) if y is None else y,
            CENTRE[1] + math.cos(b) * dist)


def look_along(bearing, dist, rise=0.0):
    """What an eye at `bearing` sees: the horizon `dist` cells on in the same bearing, lifted by
    `rise`. A flat look, so the hills stand on the horizon line where they belong."""
    b = math.radians(bearing)
    y = S.GROUND + EYE + rise
    return (CENTRE[0] + math.sin(b) * dist, y, CENTRE[1] + math.cos(b) * dist)


def shots():
    out = []
    for name, place, bearing, rise in (
        ("west", 270.0, 270.0, 2.0),        # due west: open horizon, the afterglow, no hills
        ("west_nw", 300.0, 305.0, 2.0),     # the north-west group
        ("west_sw", 240.0, 233.0, 2.0),     # the south-west group
        ("east", 90.0, 270.0, 2.0),         # looking west from the far side: the same hills, far off
        ("east_back", 90.0, 90.0, 2.0),     # due east: must be empty of hills
        ("far_west", 285.0, 305.0, 2.0),    # a walk to the far side, then the north-west group
        ("v11", None, None, None),          # the look back from the south lookout (the card's view)
    ):
        if name == "v11":
            pos, target = S.V11["pos"], S.V11["look_at"]
        else:
            pos = eye(place, 20.0)
            target = look_along(bearing, 120.0, rise)
        out.append({"name": name, "pos": [round(v, 2) for v in pos],
                    "look_at": [round(v, 2) for v in target], "time": look.tick("blue")})
    return out
