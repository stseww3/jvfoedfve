"""Work package interiors/timeroom: the time-service room (plan ART-PLAN 8, view V10).
Card: plan/packages/interiors/timeroom.md.

The room is the north wing's main floor: 12 wide (x 2..13), 19 long (z -25..-7), 7 high (feet at 7,
the ceiling block on 14). Its door is in the south wall (x 7..8), on the room's long axis, so the
first thing seen from it is the far end wall: that is where the instrument wall stands.

What is where (plan cells; north is -z):

  instrument wall   a rack of panel blocks against the north wall (z -25), x 3..12, on a riveted
                    plinth and under an iron cornice. The columns x 2 and x 13 stay empty: they are
                    the cells behind the glass of the last windows, which the light line keeps free.
  recorder          the drum recorder on its stand, in front of the wall, east of the axis
  telegraph desk    against the east wall in bay 6, one of the two bays whose windows are lit from
                    outside (sky/lights), so the lamp on the desk is what lights that window
  clock wall        the world clocks: dials in a row on the blind stretch of the west wall
                    (z -13..-7, the rotunda is behind it)
  cable trench      an iron grating in the floor along the foot of the rack
  ceiling           riveted beams across the room on the pilaster rows, where the piers carry them

The room dresses the shell main/shell.py (c231) leaves: it lays nothing of the walls, the floor
slab or the ceiling slab. Machines (machines/recorders) and furniture (props) are stand-in boxes
until those packages exist.

build() is what the master scene calls; it places nothing until MOVED_IN is set (the shell in the
master scene and the room past review). Until then the room lives in its box test scene,
build/scenes/obs_int_timeroom.
"""
from artkit.blocks import st

from ..common import blocks as B
from ..common import skeleton as S

MOVED_IN = False

# the clear inside: main/shell.ROOMS["time room"] (c231), written out from the skeleton until the
# shell is in the tree
X0, X1 = S.ROOM_X                                   # 2..13
Z0, Z1 = S.pilaster_z(2) + 1, S.STAR_HALL_Z[0] - 1  # -25..-7
FEET = S.STAND                                      # 7
TOP = S.STAR_HALL_CEIL - 1                          # 13: the last clear row
FLOOR_Y = FEET - 1                                  # 6: the floor block
CEIL_Y = S.STAR_HALL_CEIL                           # 14: the ceiling block
DOOR_X = (7, 8)                                     # in the wall on z -6
BEAM_Z = tuple(z for z in range(Z0, Z1 + 1) if (z - S.PIL_Z0) % S.BAY == 0)     # -22, -18, -14, -10

# the instrument wall: top row first, west to east
RACK_X = (X0 + 1, X1 - 1)                           # 3..12
RACK_Z = Z0                                         # -25
RACK = [row.split() for row in (
    "louvre       louvre     nameplate   louvre      tubes    tubes    louvre      nameplate   louvre     louvre",
    "bell         gauges     dial        pilot_lamps dial     dial     pilot_lamps dial        gauges     bell",
    "louvre       relays     counter     dial        scope    scope    dial        counter     relays     louvre",
    "knife_switch bus_switch patch_panel patch_panel recorder recorder patch_panel patch_panel bus_switch knife_switch",
    "fuses        fuses      drawers     relays      drawers  drawers  relays      drawers     fuses      fuses",
)]
RACK_Y = FEET + 1                                   # 8: the foot of the lowest row of panels

# the world clocks on the blind stretch of the west wall: bottom row first
CLOCK_Z = (-12, -8)
CLOCKS = ("drawers", "counter", "dial")

DESK_LAMP = 12              # a second-rank light: the lamp on a desk
RACK_GLOW = 6               # a third-rank light: what the lit panels throw on the floor in front


def build_timeroom(c, origin=(0, 0, 0), roles=B, *, version="a"):
    """Dress the room standing at `origin`. Returns dict(entities=<display entities placed>,
    lights=[(x, y, z, level, why), ...]): the lights are offered, not placed."""
    ox, oy, oz = origin
    lights = []

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    # the instrument wall: plinth, five rows of panels, cornice
    for x in range(RACK_X[0], RACK_X[1] + 1):
        put(x, FEET, RACK_Z, roles.IRON_RIVETED.block)
        put(x, TOP, RACK_Z, roles.IRON_PLATE)
    for j, row in enumerate(RACK[::-1]):
        for i, name in enumerate(row):
            put(RACK_X[0] + i, RACK_Y + j, RACK_Z, st(roles.PANELS[name], facing="south"))

    # the cable trench at the foot of the rack
    for x in range(RACK_X[0], RACK_X[1] + 1):
        put(x, FLOOR_Y, RACK_Z + 1, roles.IRON_GRATE)

    # beams on the pilaster rows
    for z in BEAM_Z:
        for x in range(X0, X1 + 1):
            put(x, TOP, z, st(roles.IRON_RIVETED.slab, type="top"))

    # panelling under the windows of the long walls
    for z in range(Z0 + 1, Z1 + 1):
        put(X1, FEET, z, st(roles.WAINSCOT, facing="west", half="bottom", open="true"))
        if z < CLOCK_Z[0] - 1:
            put(X0, FEET, z, st(roles.WAINSCOT, facing="east", half="bottom", open="true"))

    # the world clocks
    for z in range(CLOCK_Z[0], CLOCK_Z[1] + 1):
        for j, name in enumerate(CLOCKS):
            put(X0, FEET + j, z, st(roles.PANELS[name], facing="east"))

    # stand-ins: the recorder on its stand, the telegraph desk
    put(10, FEET, -22, roles.DARK_WOOD.block)
    put(10, FEET + 1, -22, st(roles.BRASS_COLUMN, axis="x"))
    for z in (-13, -12, -11):
        for x in (X1 - 1, X1):
            put(x, FEET, z, st(roles.DARK_WOOD.slab, type="top"))
    lights.append((X1 - 1, FEET + 2, -12, DESK_LAMP, "the lamp on the telegraph desk"))
    lights.append((11, FEET + 2, -22, DESK_LAMP, "the lamp over the recorder"))
    return {"entities": 0, "lights": lights}


def build(canvas, origin=(0, 0, 0)):
    """The master scene's call: nothing until the room has moved in."""
    if not MOVED_IN:
        return 0
    return build_timeroom(canvas, origin)["entities"]
