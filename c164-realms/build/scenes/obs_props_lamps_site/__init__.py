"""Test scene of props/lamps for the whole site: the master scene as it stands in this tree, with
the lamps of the site switched on (lamps.dress), whatever the switch lamps.DRESS says.

Every line is built whole, in the master scene's order, so the picture keeps up with the site as its
packages are merged: a lamp is only placed where its pedestal, pier or wall stands (lamps.site), and
the ones left out are listed by  python -m scenes.obs_props_lamps_site  (which also writes
shots.json). Where the sky line's light tool is in the tree the building is asked to show its own
lights as well (_lightkit.dress), because the lamps are judged against the lit front.

What the pictures are for (A0 #22559 three): the way in reads as a chain of pairs from the cable
station to the door; the pools of light do not run into one sheet; the lip's pier lamps are a rank
under the street lamps; the foreground of V1 stays darker than the building; everything else is
dark but for one lamp at a door.
"""
import importlib

from artkit.canvas import Canvas

from scenes import obs
from scenes.obs.common import skeleton as S
from scenes.obs.props import lamps

try:
    from scenes.obs.sky import _lightkit as L
except ImportError:         # the sky line's light tool is not merged yet
    L = None

BIOME = obs.BIOME
BIOME_MARGIN = obs.BIOME_MARGIN
BIOME_MARGIN_Y = obs.BIOME_MARGIN_Y

build_models = obs.build_models
write_pack = obs.write_pack


def build():
    c = Canvas()
    lamps.dress(c)
    if L is not None:
        L.dress(c)
    counts = {}
    for name in obs.LINES:
        line = importlib.import_module(f"scenes.obs.{name}")
        counts[name] = int(line.build(c, obs.ORIGIN) or 0)
    c.entity_counts = counts
    return c


# ---- the cameras ---------------------------------------------------------------------------------
BLUE, DEEP = 14000, 18000       # the blue hour (the default look) and deep night, when only lamps are left
EYE = S.EYE
UP, LOW = S.GROUND + EYE, S.LOWER_GROUND + EYE          # the eye of somebody on the court, on the lower platform
V1 = S.V1
V2 = getattr(S, "V2", dict(pos=(58.5, 1.7, 0.5), look_at=(17, 19, 0.5)))
V12 = getattr(S, "V12", dict(pos=(66.0, 72.0, 58.0), look_at=(8.0, -2.0, 0.0)))
AX, AZ = S.ARMILLARY
STATION_SOUTH = S.CABLE_STATION[3] + 1                  # the first row south of the cable station
STATION_MID = (S.CABLE_STATION[0] + S.CABLE_STATION[2]) // 2

BOARD = {"v1": V1, "v2": V2, "v12": V12}                # the director's three, under both times
VIEWS = {   # name: (eye, looks at)
    # out of the station's south side, down the walk to the stair's forecourt
    "way_link": ((STATION_MID + 0.5, LOW, STATION_SOUTH + 1.5), (74.0, -3.0, -2.0)),
    # on the axis at the east edge of the lower platform: every pair up to the door
    "way_axis": ((89.5, LOW, 0.5), (17.0, 14.0, 0.5)),
    # the stamp view from the east: the whole chain in elevation
    "east_high": ((104.0, 7.0, 0.5), (8.0, 15.0, 0.5)),
    # across the court to the lip: street lamps near, pier lamps behind them
    "court_side": ((30.5, UP, -20.5), (56.0, 1.5, 4.0)),
    # along the lip from its north end: three pier lamps and the stair head's lamp in a row
    "lip": ((58.5, UP, -38.5), (60.5, 1.6, -10.0)),
    "post_near": ((58.4, 2.3, -15.9), (60.5, 1.85, -17.5)),
    "feet": ((AX + 5.5, UP, AZ + 5.5), (AX + 0.5, 1.2, AZ + 0.5)),
    "hut_door": ((41.0, UP, -18.0), (37.5, 2.3, -25.0)),
    "tower_foot": ((-10.0, UP, -26.5), (-14.5, 1.0, -32.0)),
}


def shots():
    out = []

    def shot(name, pos, look_at, time):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": time})

    for name, v in BOARD.items():
        shot(name, v["pos"], v["look_at"], BLUE)
    for name, v in BOARD.items():
        shot(f"{name}_deep", v["pos"], v["look_at"], DEEP)
    for name, (pos, look_at) in VIEWS.items():
        shot(name, pos, look_at, BLUE)
    return out
