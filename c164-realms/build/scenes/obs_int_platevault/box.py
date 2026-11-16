"""The stand-in of the shell the plate vault is dressed in. Nothing here goes into the master scene.

It stands on the skeleton's coordinates, so the dressing is written once, in the coordinates it
will have in the building:

  main/facade      the east front of the south wing, bays 11..15, as facade.sample() builds it: the
                   plinth, the base storey with its small barred windows (glass in the inner leaf
                   x 14, the bars in the stone leaf x 15), and the main storey over it. The exterior
                   shot looks at this wall.
  main/shell       the cross wall on z 6 with the door to the star hall, one cell wide at
                   platevault.HALL_DOOR; the wall towards the end pavilion on z 26; the floor of
                   the chart room on y 6, which is this room's ceiling; the west wall, with the
                   small windows of bays 13..15 cut as the west front has them
  the hall         beyond the door a piece of the hall's aisle under the gallery, shut in by a
                   floor, a lid and walls, with the pier the gallery stands on before x 8 and one of
                   the hall's lamps beside the door: what the room sees through its doorway is a
                   dim hall, not the sky
"""
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.interiors import platevault as T
from scenes.obs.main import _plan as MP
from scenes.obs.main import facade, shell
from scenes.obs.props import lamps

HALL_Z = (T.Z0 - 5, T.Z0 - 2)       # 2..5: the piece of the hall's aisle
HALL_X = (T.HALL_DOOR[0] - 4, T.HALL_DOOR[0] + 4)
HALL_TOP = T.FEET + 3               # the aisle is four high under the gallery
PIER = (T.HALL_DOOR[0] + 1, T.Z0 - 2)       # (8, 5): a pier of the gallery (hall, c348)
HALL_LAMP = (T.HALL_DOOR[0] - 2.5, T.FEET + 2.5, 7)     # on the hall's side of the cross wall: x, y, level


def build(c, origin=(0, 0, 0)):
    ox, oy, oz = origin

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    def cut(x, y, z):
        c.clear(ox + x, oy + y, oz + z)

    zn, zs = T.Z0 - 1, T.Z1 + 1                     # 6, 26
    bays = (zs - zn) // S.BAY
    facade.sample(c, origin=(ox, oy, oz + zn), bays=bays, depth=S.WALL_E)

    # the sample is a building of its own with a leaf inside each end wall: the room is clear there
    for x in range(T.X0, T.X1 + 1):
        for y in range(T.FEET, S.WINDOW[1] + 1):
            cut(x, y, T.Z0)
            cut(x, y, T.Z1)
    # the cross wall and the pavilion's wall in the shell's courses, the shell's stretch of the west wall
    for y in range(T.FEET, T.TOP + 1):
        for x in range(T.X0, T.X1 + 1):
            put(x, y, zn, shell.wall_block(y))
            put(x, y, zs, shell.wall_block(y))
        for z in range(T.Z0, T.PIER_Z[0] + 1):
            put(S.GLASS_W, y, z, shell.wall_block(y))
    # floor and ceiling (the chart room's floor)
    for x in range(T.X0, T.X1 + 1):
        for z in range(T.Z0, T.Z1 + 1):
            put(x, T.FLOOR_Y, z, B.ASHLAR_FINE.block)
            put(x, T.CEIL_Y, z, B.FLOOR_WOOD.block)
    # the small windows of the west front
    for bay in T.WEST_BAYS:
        for z in MP.window_rows(bay):
            for y in range(T.WINDOW_Y[0], T.WINDOW_Y[1] + 1):
                put(S.GLASS_W, y, z, B.WINDOW_DARK.block)
                put(S.WALL_W, y, z, B.IRON_BARS)

    # the door, and the piece of the hall beyond it
    for y in range(T.DOOR_Y[0], T.DOOR_Y[1] + 1):
        cut(T.HALL_DOOR[0], y, zn)
    for z in range(HALL_Z[0], HALL_Z[1] + 1):
        for x in range(HALL_X[0], HALL_X[1] + 1):
            for y in range(T.FEET, HALL_TOP + 1):
                cut(x, y, z)                        # the sample's plinth steps out here: indoors it does not
            put(x, T.FLOOR_Y, z, B.TUFF_SMOOTH.block)
            put(x, HALL_TOP + 1, z, B.ASHLAR_FINE.block)
            if z == HALL_Z[0] or x in HALL_X:
                for y in range(T.FEET, HALL_TOP + 1):
                    put(x, y, z, shell.wall_block(y))
    for y in range(T.FEET, HALL_TOP + 1):
        put(PIER[0], y, PIER[1], shell.wall_block(y))
    lamps.place(c, "bracket", (HALL_LAMP[0], HALL_LAMP[1], float(zn)), facing="north", origin=origin,
                version="b", level=HALL_LAMP[2])
