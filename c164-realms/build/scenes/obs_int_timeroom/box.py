"""The stand-in of the shell the time room is dressed in. Nothing here goes into the master scene.

It stands on the skeleton's coordinates, so the dressing is written once, in the coordinates it
will have in the building. Whose every part is:

  main/shell (c231)    the floor and the ceiling of the room, the cross wall on z -6 with the door
                       to the gallery, the wall towards the end pavilion on z -26, the stretch of
                       the west wall the rotunda stands behind (z -14..-7)
  main/facade (c206)   the two long walls: glass in the inner leaf (x 14, x 1), the stone leaf
                       outside it (x 15, x 0); bays 3..7 are windows on the east, 3..5 on the west
  sky/lights (c220)    which windows are lit: of this room, bays 3 and 6 of the east front in the
                       blue hour (the table of its delivery 8972aa8)
"""
from artkit.blocks import st

from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.interiors import timeroom as T

EAST_BAYS = (3, 4, 5, 6, 7)
WEST_BAYS = (3, 4, 5)
LIT_BAYS = (3, 6)                       # of the east front
DOOR_Y = (T.FEET, T.FEET + 2)
GALLERY_Z = (T.Z1 + 2, T.Z1 + 3)        # -5..-4: the deck of the hall's side gallery, the rail on its edge


def wall_block(y):
    """The stone of an inside wall as main/shell lays it: a sunk course at the foot and the head."""
    return B.ASHLAR_PANEL.block if y in (S.PANEL, S.WINDOW[1]) else B.ASHLAR_FINE.block


def window_rows(bay):
    return range(S.pilaster_z(bay - 1) + 1, S.pilaster_z(bay))


def build(c, origin=(0, 0, 0)):
    ox, oy, oz = origin

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    def cut(x, y, z):
        c.clear(ox + x, oy + y, oz + z)

    xw, xe = S.WALL_W, S.WALL_E                     # 0, 15: the stone leaves
    gw, ge = S.GLASS_W, S.GLASS_E                   # 1, 14: the glass planes
    zn, zs = T.Z0 - 1, T.Z1 + 1                     # -26, -6

    # floor and ceiling
    for x in range(xw, xe + 1):
        for z in range(zn, zs + 1):
            inside = T.X0 <= x <= T.X1 and T.Z0 <= z <= T.Z1
            put(x, T.FLOOR_Y, z, B.FLOOR_WOOD.block if inside else B.ASHLAR_FINE.block)
            put(x, T.CEIL_Y, z, B.DARK_WOOD.block if inside else B.ASHLAR_FINE.block)

    # the four walls, both leaves of the long ones
    for y in range(T.FEET, T.TOP + 1):
        for x in range(xw, xe + 1):
            put(x, y, zn, wall_block(y))
            put(x, y, zs, wall_block(y))
        for z in range(zn, zs + 1):
            for x in (xw, gw, ge, xe):
                put(x, y, z, wall_block(y))

    # the windows: glass in the inner leaf, the stone leaf open in front of it
    for front, bays, glass_x, face_x in (("east", EAST_BAYS, ge, xe), ("west", WEST_BAYS, gw, xw)):
        for bay in bays:
            lit = front == "east" and bay in LIT_BAYS
            for z in window_rows(bay):
                for y in range(S.WINDOW[0], S.WINDOW[1] + 1):
                    put(glass_x, y, z, (B.WINDOW_LIT if lit else B.WINDOW_DARK).block)
                    cut(face_x, y, z)

    # the door, and a piece of the gallery beyond it
    for x in range(T.DOOR_X[0], T.DOOR_X[1] + 1):
        for y in range(DOOR_Y[0], DOOR_Y[1] + 1):
            cut(x, y, zs)
    for x in range(T.X0, T.X1 + 1):
        for z in range(GALLERY_Z[0], GALLERY_Z[1] + 1):
            put(x, T.FLOOR_Y, z, B.ASHLAR_FINE.block)
        put(x, T.FEET, GALLERY_Z[1], B.IRON_BARS)


def light(c, lights, origin=(0, 0, 0)):
    """Put down the lights the room offers, so that the box is lit the way the room will be."""
    ox, oy, oz = origin
    for x, y, z, level, _why in lights:
        c.set(ox + x, oy + y, oz + z, st(B.LIGHT, level=level))
