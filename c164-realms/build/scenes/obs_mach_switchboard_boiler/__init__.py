"""Test scene of machines/switchboard-boiler (plan/packages/machines/switchboard-boiler.md): the two
boilers and the switchboard where they stand in the master scene, in the shell of the power house
as site/powerhouse builds it.

Round the shell there is a slab of the lower platform and nothing else. The room is empty but for
the set: the engine and the dynamo, the gratings, the pipes, the coal and the lamps are other
packages'. The floor is a stand-in for the room's (interiors/powerhouse). The light is the room's
as it will be where the set stands, and nothing more: the two sources the boilers ask for before
their fire doors (boiler.LIGHTS), and the sources of the two shaded lamps the room hangs before
the board (BOARD_LAMPS: interiors/powerhouse's numbers, stood in for here).

The house's glass is painted opaque: the skeleton's V6 sees nothing of the set.

    python -m scenes.obs_mach_switchboard_boiler        # writes shots.json from the numbers below
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.machines import board, boiler
from scenes.obs.site import powerhouse

BIOME = "obs_blue"
BIOME_MARGIN = 24
BIOME_MARGIN_Y = 24

X0, Z0, X1, Z1 = S.POWER_HOUSE["box"]
SLAB = (X0 - 6, Z0 - 6, X1 + 3, Z1 + 3)         # the piece of the lower platform the house stands on
PAVING_Y = S.LOWER_PAVING_Y                     # -7
FLOOR = B.TUFF_SMOOTH.block                     # stands in for the room's floor and the yard's paving
ROCK = B.TUFF.block
FY = boiler.FLOOR
BOARD_LAMPS = [((71, -4, 28), 10), ((71, -4, 31), 10)]          # the room's two lamps before the board
TIME = 14000                                    # light version A, the default

EYE = S.EYE


def build():
    c = Canvas()
    c.box(SLAB[0], PAVING_Y - 3, SLAB[1], SLAB[2], PAVING_Y - 1, SLAB[3], ROCK)
    c.box(SLAB[0], PAVING_Y, SLAB[1], SLAB[2], PAVING_Y, SLAB[3], FLOOR)
    shell = powerhouse.build(c, (0, 0, 0))          # its own entities: the lamp over the wicket
    n = boiler.build(c, (0, 0, 0)) + board.build(c, (0, 0, 0))
    for (x, y, z), level in boiler.LIGHTS + board.LIGHTS + BOARD_LAMPS:
        c.set(int(x // 1), int(y // 1), int(z // 1), f"{B.LIGHT}[level={level}]", keep=True)
    c.entity_counts = {"machines": n, "site": int(shell or 0)}
    return c


def build_models():
    out = dict(boiler.models())
    out.update(board.models())
    try:
        from scenes.obs.props import lamps          # the shell hangs the props line's lamp over its wicket
    except ImportError:
        lamps = None
    if lamps is not None:
        out.update(lamps.models() or {})
    return out


def write_pack(pack_dir):
    """The repainted tuff, iron, glass and panels of the house the set stands in, and the sky's sun."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots():
    """The cameras: what whoever comes in by the wicket sees, then the boilers and the board each
    from the firing floor and from near."""
    fx, r, h = boiler.FRONT_X, boiler.R, FY + boiler.AXIS_H
    za, zb = boiler.AXES_Z
    bx, bz = board.FACE_X, (board.Z[0] + board.Z[1] + 1) / 2.0
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(float(v), 2) for v in pos],
                    "look_at": [round(float(v), 2) for v in look_at], "time": TIME})

    shot("door", (74.5, FY + EYE, 23.2), (77.5, FY + 1.4, 36.5))                # a step inside the wicket
    shot("hall", (74.5, FY + EYE, 39.5), (76.0, FY + 1.6, 27.0))                # from the south wall, back north
    shot("fronts", (fx - 5.0, FY + EYE, (za + zb) / 2.0), (fx, h - 0.4, (za + zb) / 2.0))
    shot("fire", (fx - 2.4, FY + EYE, zb + 0.9), (fx, FY + 1.25, zb))           # one fire door, near
    shot("flank", (fx - 1.5, FY + EYE, zb + r + 3.2), (fx + 2.2, h + 0.3, zb))  # the south boiler's side
    shot("dome", (fx + 0.6, FY + 4.6, zb + r + 2.6), (fx + boiler.DOME_X, h + r + 0.5, zb))
    shot("flues", (fx + 6.6, FY + EYE, zb + 2.6), (fx + 4.6, h + 0.6, zb - 1.0))    # behind the boilers
    shot("board", (bx + 5.0, FY + EYE, bz), (bx, FY + 2.4, bz))                 # the board, face on
    shot("board_near", (bx + 2.2, FY + EYE, bz + 1.6), (bx, FY + 2.6, bz))
    shot("board_side", (bx + 1.6, FY + EYE, board.Z[0] - 2.2), (bx, FY + 2.2, bz - 0.5))
    shot("above", (76.5, FY + 8.0, 31.5), (77.5, FY, 27.5))
    return out
