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
from scenes.obs.main import _plan as P

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
    from above; the way over the roofs as one walks it from the dome room's south door to the small
    dome; both wings' roofs from above."""
    cx = (S.SMALL_DOME_X[0] + S.SMALL_DOME_X[1]) / 2.0 + 0.5        # the dome's axis, a point
    cz = (S.SMALL_DOME_Z[0] + S.SMALL_DOME_Z[1]) / 2.0 + 0.5
    spring = S.SMALL_DRUM_BASE + 3.0
    ridge = (S.WALL_W + S.WALL_E + 1) / 2.0                         # the wings' ridge line
    eye = S.ROOF_STAND + S.EYE                                      # the eye of a person on a terrace
    gable, end_gable = P.GABLE_Z                                    # the gables at a wing's two ends
    door_x, door_z = S.DOME_ROOM_DOORS["cells"][0]                  # the dome room's south door
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
    # the way (main/roof): from the corner terrace back at the door; on the landing behind the inner
    # gable, up the treads; on the ridge, along the grating; where the way comes onto the end terrace
    shot("door", (S.WALL_E - 0.4, eye, gable - 0.5), (door_x + 0.5, S.ROOF_STAND + 1.0, door_z + 0.5))
    shot("treads", (S.WALL_E - 1.5, eye, gable + 1.5), (ridge, P.ROOF_RIDGE_TOP + 0.3, gable + 2.0))
    shot("walk", (ridge, P.ROOF_RIDGE_TOP + S.EYE, gable + 2.5), (cx - 2.0, spring - 0.5, cz))
    shot("terrace", (S.WALL_W + 2.5, eye, end_gable + 1.5), (cx - 3.0, S.ROOF_STAND + 1.0, cz))
    # the same on the north end terrace, where the way ends at the clock tower's door (c223's
    # interface: the leaves in the west face at (10, 18..19, -30), the plate before them)
    shot("terrace_north", (S.WALL_W + 2.5, eye, -end_gable - 1.5), (cx - 3.0, S.ROOF_STAND + 1.0, -cz))
    shot("roofs", (cx + 6.0, spring + 22.0, cz + 26.0), (ridge, S.ROOF_STAND, 14.0))
    mirror = 2 * S.AXIS_Z                                           # the same over the north wing
    shot("roofs_north", (cx + 6.0, spring + 22.0, mirror - (cz + 26.0)), (ridge, S.ROOF_STAND, mirror - 14.0))
    shot("aerial", (cx + 14.0, spring + 24.0, cz + 18.0), (cx, spring - 2.0, cz))
    return out
