"""Test scene of the work package main/tower (plan/packages/main/tower.md): the clock tower as it
stands in the master scene, spire version a (the verdigris cupola).

The lines are built whole, in the master scene's order (the mountain and the court, the main
building with the tower on its north pavilion, the lamps, the sky's light), so the pictures keep up
with them as their packages are merged. Version b of the spire is the twin scene obs_main_tower_b:
the same shots, picture by picture.

The shots are written from the skeleton's numbers:  python -m scenes.obs_main_tower
"""
from artkit.canvas import Canvas

from scenes.obs import main, materials, props, site, sky
from scenes.obs.common import skeleton as S
from scenes.obs.main import tower

BIOME = "obs_blue"
BIOME_MARGIN = 80
BIOME_MARGIN_Y = 160
LINES = (site, main, props, sky)
SPIRE = "a"
TIME = 14000                    # the blue hour, the default look


def build(spire=None):
    was, tower.VERSION = tower.VERSION, spire or SPIRE
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
    """The tower paints nothing itself; it stands in the repainted blocks as the materials line has
    them today."""
    return materials.pack(pack_dir)


def shots():
    cx, cz = tower.CX + 0.5, tower.CZ + 0.5         # the tower's axis
    face = tower.X1 + 1.0                           # its east face
    dial = (tower.DIAL_Y[0] + tower.DIAL_Y[1] + 1) / 2.0
    v1 = S.V1

    def shot(name, pos, look_at):
        return {"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at], "time": TIME}

    return [
        # V5, the up-view from the court: clock face, belfry, spire, ball and mast in one line
        shot("v5_up", (44.5, 1.7, -22.5), (cx, 33.0, cz)),
        shot("v5_far", (58.5, 1.7, -30.5), (cx, 30.0, cz)),
        # V1, the arrival view from the station platform, as the skeleton fixes it; and the same
        # eye turned to the tower
        shot("v1_stamp", v1["pos"], v1["look_at"]),
        shot("v1_tower", v1["pos"], (cx, 26.0, cz)),
        # close on a clock face, on the top, and on where the tower meets the building
        shot("dial_close", (face + 13.0, 22.0, cz + 6.0), (face, dial, cz)),
        shot("top_close", (face + 14.0, 45.0, cz + 11.0), (cx, tower.SPIRE[1] - 1.0, cz)),
        shot("junction", (face + 18.0, 24.0, cz + 18.0), (cx + 1.0, 18.0, cz + 3.0)),
        # the sides the court does not see
        shot("north_west", (cx - 22.0, 30.0, cz - 22.0), (cx, 31.0, cz)),
    ]
