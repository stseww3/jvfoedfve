"""Test scene of the work package main/tower (plan/packages/main/tower.md): the clock tower as it
stands in the master scene, version a of its top (four arches under a four-sided copper roof).

The lines are built whole, in the master scene's order (the mountain and the court, the main
building with the tower on its north pavilion, the machines, the lamps, the sky's light), so the
pictures keep up with them as their packages are merged. Version b (the octagonal kiosk under a
dome) is the twin scene obs_main_tower_b: the same shots, picture by picture.

The dials, their hands and the time ball are machines/clock's: with the machines line built here
the tower carries them as in the master scene, the dials in its recesses and the ball on its mast,
and the radio mast stands north-east of it.

The shots are written from the skeleton's numbers:  python -m scenes.obs_main_tower
"""
from artkit.canvas import Canvas

from scenes.obs import machines, main, materials, props, site, sky
from scenes.obs.common import skeleton as S
from scenes.obs.main import tower

BIOME = "obs_blue"
BIOME_MARGIN = 80
BIOME_MARGIN_Y = 160
LINES = (site, main, machines, props, sky)
TOP = "a"
TIME = 14000                    # the blue hour, the default look


def build(top=None):
    was, tower.VERSION = tower.VERSION, top or TOP
    try:
        c = Canvas()
        for line in LINES:
            line.build(c, (0, 0, 0))
    finally:
        tower.VERSION = was
    return c


def build_models():
    out = {}
    for line in LINES:
        out.update(line.models() or {})
    return out


def write_pack(pack_dir):
    """The tower paints no block itself; it stands in the repainted blocks as the materials line has
    them today, under the sky's own pictures: the scene keeps the map's hour, and the sky's pack is
    what blanks the sun on the western horizon and hangs the comet. Its two models (the mast and the
    cup wheel) come with build_models()."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots():
    cx, cz = tower.AXIS                             # the tower's axis
    face = tower.X1 + 1.0                           # its east face
    dial = tower.DIAL_CENTRES["east"][1]
    foot = float(tower.FOOT)

    def shot(name, pos, look_at):
        return {"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at], "time": TIME}

    # V5 is not in the skeleton yet: until it is, the station the picture board proposes for it
    # (tools/boardshots.py: fifteen blocks east and south of the axis, looking up the corner)
    board = getattr(S, "V5", dict(pos=(cx + 15.0, S.GROUND + S.EYE, cz + 15.0), look_at=(cx, S.CLOCK_SHAFT_TOP - 3.0, cz)))
    return [
        # V5, the up-views from the court: dial, lookout, top, ball and mast in one line. v5_up and
        # v5_far see the east face nearly square on, from farther back than the board's station.
        # The comet is due west of every eye: v5_far stands south of the tower's own latitude, so
        # that the comet hangs clear of the top and not behind it
        shot("v5_board", board["pos"], board["look_at"]),
        shot("v5_up", (44.5, 1.7, -22.5), (cx, 33.0, cz)),
        shot("v5_far", (58.5, 1.7, -18.5), (cx, 30.0, cz)),
        # V1, the arrival view from the station platform, and V2, the court's axis: eye and look-at
        # are the skeleton's. The tower is the right-hand high point of both skylines
        shot("v1_stamp", S.V1["pos"], S.V1["look_at"]),
        shot("v2_axis", S.V2["pos"], S.V2["look_at"]),
        # close on a dial's recess, on the top from above and level with the lookout, and on where
        # the tower meets the building
        shot("dial_close", (face + 13.0, 22.0, cz + 6.0), (face, dial, cz)),
        shot("top_close", (face + 14.0, 45.0, cz + 11.0), (cx, tower.APEX - 1.0, cz)),
        shot("top_level", (face + 23.5, 34.0, cz + 15.0), (cx, 36.0, cz)),
        shot("junction", (face + 18.0, 24.0, cz + 18.0), (cx + 1.0, 18.0, cz + 3.0)),
        # the sides the court does not see: the door, from the roof walk at eye height, and the
        # north-west corner from the air
        shot("west_door", (cx - 9.0, foot + 1.62, cz), (float(tower.X0), foot + 1.0, cz)),
        shot("north_west", (cx - 22.0, 30.0, cz - 22.0), (cx, 31.0, cz)),
    ]
