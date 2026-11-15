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
    """The repainted blocks, and the sky line's sun: the game's own is a white and yellow square
    wherever a shot looks west over the open horizon."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots():
    """V11 from the south lookout (the distance view), V1 and V2 (the two views whose skyline the
    dome ends on the south), the dome from the court, from the roofs and from above; the way over
    the roofs as one walks it from the dome room's south door to the small dome; both wings' roofs
    from above, the north one from the height of the tower's lookout as well; and the whole site from
    above, the one view of the board that sees the roofs."""
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
    shot("v1", S.V1["pos"], S.V1["look_at"])                        # the skyline's south end as one arrives
    shot("v2", S.V2["pos"], S.V2["look_at"])                        # and from the court's axis
    shot("v11_dome", (cx + 22.0, 4.0, cz + 15.0), (cx, spring, cz))
    shot("court", (cx + 26.0, 1.7, cz - 6.0), (cx, spring - 1.0, cz))
    shot("corner", (cx + 12.0, spring + 4.0, cz + 12.0), (cx, spring, cz))
    shot("slit", (S.WALL_W + 2.5, S.ROOF_STAND + 1.7, cz + 3.0), (cx - 2.0, spring + 0.5, cz))
    shot("west_high", (cx - 16.0, spring + 12.0, cz), (cx, spring, cz))
    # the way (main/roof): from the inner gable's top back at the door; the four treads against the
    # gable, from over the eaves; on the ridge, along the grating; where the way comes onto the end terrace
    shot("door", (door_x + 1.5, eye, gable + 0.5), (door_x + 0.5, S.ROOF_STAND + 1.0, door_z + 0.5))
    shot("treads", (S.WALL_E - 2.0, eye + 0.6, gable + 4.0), (ridge + 2.0, S.ROOF_STAND + 1.0, gable + 1.5))
    shot("walk", (ridge, P.ROOF_RIDGE_TOP + S.EYE, gable + 2.5), (cx - 2.0, spring - 0.5, cz))
    shot("terrace", (S.WALL_W + 2.5, eye, end_gable + 3.5), (cx - 3.0, S.ROOF_STAND + 2.6, cz))
    shot("roofs", (cx + 6.0, spring + 22.0, cz + 26.0), (ridge, S.ROOF_STAND, 14.0))
    # the north wing: from the west, where the tower does not stand in the way (the end terrace, the
    # treads down the west slope, the tower's door); then from the height of the tower's lookout, the
    # eye of a person in its south arch and in its west one (floor y 32, main/tower.py)
    mirror = 2 * S.AXIS_Z
    tower_x = (S.CLOCK_SHAFT_X[0] + S.CLOCK_SHAFT_X[1] + 1) / 2.0
    tower_z = (S.CLOCK_SHAFT_Z[0] + S.CLOCK_SHAFT_Z[1] + 1) / 2.0
    lookout = S.CLOCK_SHAFT_TOP + 1 + S.EYE
    shot("roofs_north", (ridge - 26.0, spring + 22.0, mirror - (cz + 6.0)), (ridge, S.ROOF_STAND, mirror - (cz - 8.0)))
    shot("lookout", (tower_x, lookout, S.CLOCK_SHAFT_Z[1] + 1.1), (ridge, S.ROOF_STAND + 1.0, mirror - 12.0))
    shot("lookout_west", (S.CLOCK_SHAFT_X[0] - 0.4, lookout, tower_z), (S.WALL_W + 4.5, S.ROOF_STAND - 0.5, tower_z + 1.0))
    shot("aerial", (cx + 14.0, spring + 24.0, cz + 18.0), (cx, spring - 2.0, cz))
    # V12, the board's view of the whole site from above: the skeleton does not lock it yet, so the
    # numbers are the proposal of tools/boardshots.py, written out the same way
    v12 = getattr(S, "V12", None) or dict(pos=(S.EAST_EDGE_X + 20.0, 90.0, S.Z_SOUTH + 46.0),
                                          look_at=(S.MERIDIAN_X, S.GROUND, S.AXIS_Z - 5.5))
    shot("v12", v12["pos"], v12["look_at"])
    return out
