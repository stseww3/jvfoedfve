"""Test scene of the work package main/smalldome (plan/packages/main/smalldome.md): the small dome
on the south end pavilion, and the roofs that lead to it.

The dome as it stands in the master scene: the terraces under the building, the whole main line
(the walls, the great dome, the roofs), the props on the court and the sky line's light sources
last. The lines are built whole, in the master scene's order, so the pictures keep up with them.

The shots are written from the skeleton's numbers:  python -m scenes.obs_main_smalldome
"""
from artkit.canvas import Canvas

from scenes.obs import main, materials, props, site, sky
from scenes.obs.common import skeleton as S

BIOME = "obs_blue"
BIOME_MARGIN = 80
BIOME_MARGIN_Y = 140
LINES = (site, main, props, sky)
TIME = 14000                    # light version A, the default


def build():
    c = Canvas()
    for line in LINES:
        line.build(c, (0, 0, 0))
    return c


def build_models():
    out = {}
    for line in LINES:
        out.update(line.models() or {})
    return out


def write_pack(pack_dir):
    return materials.pack(pack_dir)


def shots():
    """V11 from the south lookout (the distance view), the dome from the court, from the roofs and
    from above."""
    cx = (S.SMALL_DOME_X[0] + S.SMALL_DOME_X[1]) / 2.0 + 0.5        # the dome's axis, a point
    cz = (S.SMALL_DOME_Z[0] + S.SMALL_DOME_Z[1]) / 2.0 + 0.5
    spring = S.SMALL_DRUM_BASE + 3.0
    ridge = (S.WALL_W + S.WALL_E + 1) / 2.0                         # the wings' ridge line
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos],
                    "look_at": [round(v, 2) for v in look_at], "time": TIME})

    shot("v11", S.V11["pos"], S.V11["look_at"])
    shot("v11_dome", (cx + 22.0, 4.0, cz + 15.0), (cx, spring, cz))
    shot("court", (cx + 26.0, 1.7, cz - 6.0), (cx, spring - 1.0, cz))
    shot("corner", (cx + 12.0, spring + 4.0, cz + 12.0), (cx, spring, cz))
    shot("slit", (S.WALL_W + 2.5, S.ROOF_STAND + 1.7, cz + 3.0), (cx - 2.0, spring + 0.5, cz))
    shot("west_high", (cx - 16.0, spring + 12.0, cz), (cx, spring, cz))
    shot("ridge", (ridge, S.ROOF_STAND + 4.7, 14.5), (ridge + 2.0, spring - 1.0, cz))
    shot("roofs", (cx + 6.0, spring + 22.0, cz + 26.0), (ridge, S.ROOF_STAND, 14.0))
    shot("aerial", (cx + 14.0, spring + 24.0, cz + 18.0), (cx, spring - 2.0, cz))
    return out
