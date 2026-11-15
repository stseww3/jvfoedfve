"""Test scene of the work package machines/switchboard-boiler (plan/packages/machines/switchboard-boiler.md).

The power house's box with the boiler against the north wall -- its fire door on the axis of the bay
that glows in the house's own window table (north bay 4, x 81..83, y -3..-1) -- and the marble
switchboard on the west wall. The room is x 67..89, z 20..42, feet at y -6, walls ten high.

  fire_north      the boiler's fire door from inside the room, straight on
  fire_slant      the same from an angle, so the drum, its hoops and the mouth read together
  through_window  from outside the north wall's fire window, where V6 sees the glow: the point of the
                  whole piece (the wall is cut away here so the ray reaches the mouth)
  board           the switchboard face on the west wall
  board_slant     the board from the room's middle, with the boiler behind it
  room            both families in one view from the door

The scene lays one work light (the room's own lamps are props/lamps' when they are in the tree).

    python -m scenes.obs_mach_switchboard_boiler        writes shots.json from the layout below
"""
from artkit.canvas import Canvas

from scenes.obs import materials
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.machines import switchboard_boiler as SB

BIOME = "obs_blue"
CATEGORY = "machines"
TIME = 14000

PH = S.POWER_HOUSE
X0, Z0, X1, Z1 = PH["box"]
FEET = PH["base_y"]
CEIL = FEET + PH["wall_h"]
FLOOR = FEET - 1
WALL = B.TUFF_BRICK.block
WORK_LIGHT = 14


def _room(c):
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            c.set(x, FLOOR, z, WALL)
            c.set(x, CEIL, z, WALL)
    for y in range(FEET, CEIL):
        for x in range(X0, X1 + 1):
            c.set(x, y, Z0, WALL)
            c.set(x, y, Z1, WALL)
        for z in range(Z0, Z1 + 1):
            c.set(X0, y, z, WALL)
            c.set(X1, y, z, WALL)
    # the fire window in the north wall, cut open so the glow can be seen from outside
    for x in range(SB.FIRE_AXIS["x"][0], SB.FIRE_AXIS["x"][1] + 1):
        for y in range(SB.FIRE_AXIS["y"][0], SB.FIRE_AXIS["y"][1] + 1):
            c.carve(x, y, Z0, x, y, Z0)
    # the door on the south wall, for the room view
    c.carve(int(SB.FIRE_MID_X) - 1, FEET, Z1, int(SB.FIRE_MID_X) + 1, FEET + 2, Z1)
    c.set(int(SB.FIRE_MID_X), CEIL - 1, int(SB.BOILER_C[2]) + 2, f"{B.LIGHT}[level={WORK_LIGHT}]")
    return c


def layout(c=None):
    c = c or Canvas()
    _room(c)
    n = SB.build(c, (0, 0, 0))
    return c, n


def build():
    c, _ = layout()
    return c


def build_models():
    return SB.models()


def write_pack(pack_dir):
    return materials.pack(pack_dir)


def shots():
    out = []

    def shot(name, pos, look_at, time=TIME):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": time})

    fx = SB.FIRE_MID_X
    bz = SB.BOILER_C[2]
    eye = FEET + 1.62
    shot("fire_north", (fx, eye, bz + 4.6), (fx, FEET + 1.5, bz - 1.4))
    shot("fire_slant", (fx + 3.2, FEET + 2.2, bz + 4.4), (fx, FEET + 1.5, bz - 1.4))
    shot("through_window", (fx, FEET + 1.7, Z0 - 3.2), (fx, FEET + 1.7, bz))
    bx, _, bz2 = SB.BOARD_AT
    shot("board", (bx + 3.4, FEET + 1.9, bz2), (bx, FEET + 1.8, bz2))
    shot("board_slant", (bx + 4.6, FEET + 2.1, bz2 + 3.4), (bx, FEET + 1.8, bz2))
    shot("room", (fx - 1.0, eye, Z1 - 2.2), (bx + 1.0, FEET + 1.7, bz))
    return out
