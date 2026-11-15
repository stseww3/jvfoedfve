"""Test scene of the work package machines/switchboard-boiler (plan/packages/machines/switchboard-boiler.md).

The power house's box with the boiler against the north wall -- its fire door on the axis of the bay
that glows in the house's own window table (north bay 4, x 81..83, y -3..-1) -- and the marble
switchboard on the west wall. The room is x 67..89, z 20..42, feet at y -6, walls ten high.

  fire_door       the boiler's fire door from inside the room, straight on
  fire_slant      the same from an angle, so the drum, its hoops and the mouth read together
  fire_far        the mouth from the far side of the room, the way V6 sees it through the window
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
BOARD_LIGHT = 6                     # rank 3, the figure starhall's board light uses


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
    # the east fire window: glass in the wall (the sky line lights it; site/powerhouse owns it)
    for z in range(SB.FIRE_WINDOWS["east"]["cells"][0], SB.FIRE_WINDOWS["east"]["cells"][1] + 1):
        for y in range(SB.FIRE_WINDOWS["east"]["y"][0], SB.FIRE_WINDOWS["east"]["y"][1] + 1):
            c.set(X1, y, z, B.WINDOW_FURNACE[0].block if hasattr(B.WINDOW_FURNACE[0], "block") else B.WINDOW_CURTAIN.block)
    # the door on the south wall, for the room view
    c.carve(int(SB.BOILER_C[0]) - 1, FEET, Z1, int(SB.BOILER_C[0]) + 1, FEET + 2, Z1)
    c.set(int(SB.BOILER_C[0]) - 2, CEIL - 1, int(SB.BOILER_C[2]), f"{B.LIGHT}[level={WORK_LIGHT}]")
    # a light in front of the switchboard's face, so the board's phosphor and pilot lamps can be seen
    # (cr3: the board had no bright point at all)
    c.set(int(SB.BOARD_AT[0]) + 2, CEIL - 2, int(SB.BOARD_AT[2]), f"{B.LIGHT}[level={BOARD_LIGHT}]")
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

    bx_, bz = SB.BOILER_C[0], SB.BOILER_C[2]
    eye = FEET + 1.62
    shot("fire_door", (bx_ - 5.0, eye, bz), (bx_, FEET + 1.5, bz))
    shot("fire_slant", (bx_ - 4.6, FEET + 2.0, bz + 3.0), (bx_, FEET + 1.5, bz))
    shot("fire_far", (bx_ - 8.0, FEET + 1.7, bz - 1.2), (bx_, FEET + 1.4, bz))
    bx, _, bz2 = SB.BOARD_AT
    shot("board", (bx + 3.4, FEET + 1.9, bz2), (bx, FEET + 1.8, bz2))
    shot("board_slant", (bx + 4.6, FEET + 2.1, bz2 + 3.4), (bx, FEET + 1.8, bz2))
    shot("room", (bx_ - 2.0, eye, Z1 - 2.6), (bx + 1.0, FEET + 1.7, bz))
    return out
