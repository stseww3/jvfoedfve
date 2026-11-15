"""The stand-in of the shell the time room is dressed in. Nothing here goes into the master scene.

It stands on the skeleton's coordinates, so the dressing is written once, in the coordinates it
will have in the building. Every block of it was read off the real walls (main/facade and
main/shell of c231's branch 4b9d320b, built and read cell by cell). Whose every part is:

  main/shell (c231)    the floor and the ceiling of the room, the cross wall on z -6 with the door
                       to the gallery, the wall towards the end pavilion on z -26, the stretch of
                       the west wall the rotunda stands behind (z -10..-7)
  main/facade (c206)   the two long walls: glass in the inner leaf (x 14, x 1), the stone leaf
                       outside it (x 15, x 0) with the cornice over it; bays 3..7 are windows on the
                       east, 3..5 on the west
  sky/lights (c220)    which windows are lit and the two sources of each lit one: under the blue
                       look bays 3 and 6 of the east front and 3 and 5 of the west one, opal glass.
                       The sources stand outside the glass, in the window opening, level 8, one row
                       above the sill and one row below the head (c220, g2 #33335); the first cell
                       of the room behind the glass gets 6 of it
  materials/windows    a lit window is lined on the room side and is unlit glass from inside (A0,
    (c205)             g2 #32711). Until that lining is in the tree the box glazes the lit windows
                       with the dark glass, which is what the room sees; nobody looks at the box
                       from outside
"""
from artkit.blocks import st

from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.interiors import timeroom as T
from scenes.obs.main import _plan as MP

LIT = {"east": (3, 6), "west": (3, 5)}      # the lit windows of the room under the blue look (sky/lights)
OUTSIDE = 8                                 # the level of the sources of a lit opal window, in its opening
ROOM_SIDE = B.WINDOW_DARK                   # what a lit window is from the room, until its lining is in the tree
DOOR_Y = (T.FEET, T.FEET + 2)
GALLERY_Z = (T.Z1 + 2, T.Z1 + 3)            # -5..-4: the deck of the hall's side gallery, the rail on its edge
CORNICE_Y = S.CORNICE                       # 15: the course over the windows; it reaches two blocks out
REACH = 2


def wall_block(y):
    """The stone of an inside wall as main/shell lays it: a sunk course at the foot and the head."""
    return B.ASHLAR_PANEL.block if y in (S.PANEL, S.WINDOW[1]) else B.ASHLAR_FINE.block


def lit(front, bay):
    """Is a window of the room lit? The light line's table when it is in the tree, else LIT."""
    try:
        from scenes.obs.sky import _lightkit
    except ImportError:
        return bay in LIT[front]
    return _lightkit.window_lit(front, bay, "main")[0] >= _lightkit.LIT


def build(c, origin=(0, 0, 0)):
    """The shell; returns the light sources of the lit windows, [((x, y, z), level)], which the
    scene puts down itself: the light line reads the real fronts, and the box has none."""
    ox, oy, oz = origin
    sources = []

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    def cut(x, y, z):
        c.clear(ox + x, oy + y, oz + z)

    xw, xe = S.WALL_W, S.WALL_E                     # 0, 15: the stone leaves
    gw, ge = S.GLASS_W, S.GLASS_E                   # 1, 14: the glass planes
    zn, zs = T.Z0 - 1, T.Z1 + 1                     # -26, -6

    # floor and ceiling; the cornice over the long walls keeps the sky off the windows as it will
    for x in range(xw, xe + 1):
        for z in range(zn, zs + 1):
            inside = T.X0 <= x <= T.X1 and T.Z0 <= z <= T.Z1
            put(x, T.FLOOR_Y, z, B.FLOOR_WOOD.block if inside else B.ASHLAR_FINE.block)
            put(x, T.CEIL_Y, z, B.DARK_WOOD.block if inside else B.ASHLAR_FINE.block)
    for z in range(zn, zs + 1):
        for x in list(range(xw - REACH, gw + 1)) + list(range(ge, xe + REACH + 1)):
            put(x, CORNICE_Y, z, B.ASHLAR_FINE.block)

    # the four walls, both leaves of the long ones; the long walls have a plain course at the foot
    for y in range(T.FEET, T.TOP + 1):
        for x in range(xw, xe + 1):
            put(x, y, zn, wall_block(y))
            put(x, y, zs, wall_block(y))
        for z in range(zn, zs + 1):
            for x in (xw, gw, ge, xe):
                shell = x == gw and z >= T.PIER_Z[-1]       # the shell's own stretch of the west wall
                put(x, y, z, wall_block(y) if shell else B.ASHLAR_FINE.block)

    # the windows: glass in the inner leaf, the stone leaf open in front of it; the sources of a lit
    # one stand in that opening
    for front, bays, glass_x, face_x in (("east", T.EAST_BAYS, ge, xe), ("west", T.WEST_BAYS, gw, xw)):
        for bay in bays:
            rows = MP.window_rows(bay)
            glass = (ROOM_SIDE if lit(front, bay) else B.WINDOW_DARK).block
            for z in rows:
                for y in range(S.WINDOW[0], S.WINDOW[1] + 1):
                    put(glass_x, y, z, glass)
                    cut(face_x, y, z)
            if lit(front, bay):
                middle = rows[len(rows) // 2]
                sources += [((face_x, y, middle), OUTSIDE) for y in (S.WINDOW[0] + 1, S.WINDOW[1] - 1)]

    # the door, and a piece of the gallery beyond it
    for x in range(T.DOOR_X[0], T.DOOR_X[1] + 1):
        for y in range(DOOR_Y[0], DOOR_Y[1] + 1):
            cut(x, y, zs)
    for x in range(T.X0, T.X1 + 1):
        for z in range(GALLERY_Z[0], GALLERY_Z[1] + 1):
            put(x, T.FLOOR_Y, z, B.ASHLAR_FINE.block)
        put(x, T.FEET, GALLERY_Z[1], B.IRON_BARS)
    return [((ox + x, oy + y, oz + z), level) for (x, y, z), level in sources]


def light(c, sources):
    """Put down the sources of the lit windows, never over a block that is there."""
    for (x, y, z), level in sources:
        c.set(x, y, z, st(B.LIGHT, level=level), keep=True)
