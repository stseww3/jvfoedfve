"""Test scene of the card sky/ridges: the far hills seen from the terrace.

A plain place to stand on -- the terrace with the sunset platform at its west edge, the south
lookout where V11 stands, and nothing else: the hills are the whole subject, and the main building
would only hide them. The sky is the blue look's, since that is the look the map is finished in
(director, A0 #43929). The panels are the ones `sky/ridges.build()` puts down.

    python -m scenes.obs_sky_ridges        writes shots.json; prints the elevations of the peaks
                                           and which bearings come out empty (the west, on purpose)
"""
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


def _terrace(c):
    """The terrace: the upper paving with its edge, and the lower platform beyond it, so the eye
    stands where the map puts a visitor. No wall, no lamps: nothing but the ground."""
    x0, z0, x1, z1 = S.UPPER_TERRACE
    c.box(x0, S.PAVING_Y, z0, x1, S.PAVING_Y, z1, GROUND)
    # the eastern edge of the upper terrace, and the lower platform six blocks under it
    c.box(x1, S.LOWER_PAVING_Y, z0, x1, S.PAVING_Y - 1, z1, PLINTH)
    c.box(x1 + 1, S.LOWER_PAVING_Y, z0, x1 + 39, S.LOWER_PAVING_Y, z1, GROUND)
    # the sunset platform at the west end: a half circle the eye can stand on
    cx, r = S.SUNSET_PLATFORM["centre"]
    for dx in range(-r, r + 1):
        for dz in range(-r, r + 1):
            if dx * dx + dz * dz <= r * r:
                c.set(cx + dx, S.PAVING_Y, dz, GROUND)
    # the south lookout: where V11 stands (a small deck, the way the site has it)
    bx0, bz0, bx1, bz1 = S.SOUTH_LOOKOUT["box"]
    c.box(bx0, S.SOUTH_LOOKOUT["feet"] - 1, bz0, bx1, S.SOUTH_LOOKOUT["feet"] - 1, bz1, GROUND)


def build():
    c = Canvas()
    _terrace(c)
    c.entity_counts = ridges.build(c)
    return c


# ---- the shots -------------------------------------------------------------------------------------------
EYE = S.EYE


def _eye_at(deg, dist, y=None):
    """An eye `dist` cells from the terrace centre on the compass bearing `deg`, looking back at the
    centre: the bearings the hills stand on, and the west left open."""
    import math
    b = math.radians(deg)
    cx = S.WALL_E + 0.0
    x = cx + math.sin(b) * dist
    z = math.cos(b) * dist
    return (x, (S.GROUND + EYE) if y is None else y, z), (cx, S.GROUND + EYE + max(0.0, dist * 0.02), 0.0)


WEST = (S.SUNSET_PLATFORM["centre"][0] - 18.5, S.GROUND + EYE, S.AXIS_Z)
WEST_LOOK = (WEST[0] - 40.0, S.GROUND + EYE + 3.0, S.AXIS_Z)


def shots():
    out = []
    for name, (pos, target) in (
        ("west", (WEST, WEST_LOOK)),                                     # due west: the open horizon
        ("west_nw", _eye_at(300.0, 30.0)),                               # the north-west group
        ("west_sw", _eye_at(240.0, 30.0)),                               # the south-west group
        ("east", (_eye_at(90.0, 30.0)[0], (S.WALL_E - 40.0, S.GROUND + EYE + 3.0, S.AXIS_Z))),  # must be empty
        ("far_west", _eye_at(270.0, 60.0)),                              # from the far side of the terrace
        ("v11", (S.V11["pos"], S.V11["look_at"])),                       # the look back, the card's view
    ):
        out.append({"name": name, "pos": [round(v, 2) for v in pos],
                    "look_at": [round(v, 2) for v in target], "time": look.tick("blue")})
    return out
