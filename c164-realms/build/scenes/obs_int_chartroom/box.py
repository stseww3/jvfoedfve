"""The stand-in of the shell the chart room is dressed in. Nothing here goes into the master scene.

It stands on the skeleton's coordinates, so the dressing is written once, in the coordinates it
will have in the building. It is the mirror about the axis of the box of the time room
(scenes/obs_int_timeroom/box.py, c195), whose every block was read off the real walls. Whose every
part is:

  main/shell (c231)        the floor and the ceiling of the room, the cross wall on z 6 with the door
                           to the gallery, the wall towards the end pavilion on z 26, the stretch of
                           the west wall the rotunda stands behind (z 7..10)
  main/facade (c206)       the two long walls: glass in the inner leaf (x 14, x 1), the stone leaf
                           outside it (x 15, x 0) with the cornice over it; bays 11..15 are windows
                           on the east, 13..15 on the west
  sky/lights (c220)        which windows are lit and the two sources of each lit one: under the blue
                           look bays 12 and 14 of the east front and 13 and 15 of the west one, opal
                           glass; the sources stand outside the glass, in the window opening, one row
                           above the sill and one row below the head (c220 #33341: level 8 there)
  materials/windows (me)   the lining on the room side of the lit windows, when that is in the tree

Beyond the door the box has a piece of the hall's side gallery, shut in by a floor, a lid and three
walls, with one lamp of the hall on the cross wall beside the door (as the time room's box has it,
m2): the gallery is indoors, and what the room sees through its doorway is a dim hall, not the sky.
"""
from artkit.blocks import st

from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.interiors import chartroom as T
from scenes.obs.main import _plan as MP
from scenes.obs.materials import windows
from scenes.obs.props import lamps

LIT = {"east": (12, 14), "west": (13, 15)}      # the lit windows of the room under the blue look (sky/lights)
OUTSIDE = 10                                    # the level of the sources of a lit opal window, in its opening
DOOR_Y = (T.FEET, T.FEET + 2)
GALLERY_Z = (T.Z0 - 3, T.Z0 - 2)                # 4..5: the deck of the hall's side gallery, the rail on its edge
HALL_Z = T.Z0 - 5                               # 2: the wall that stands in for the hall beyond the gallery
HALL_LAMP = (T.DOOR_X[1] + 2.5, T.FEET + 3.5, 8)    # a lamp of the hall on the cross wall east of the door: x, y, its level
CORNICE_Y = S.CORNICE                           # 15: the course over the windows; it reaches two blocks out
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
    scene puts down while the light line is not in the tree."""
    ox, oy, oz = origin
    sources = []
    line = getattr(windows, "line", None)

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    def cut(x, y, z):
        c.clear(ox + x, oy + y, oz + z)

    xw, xe = S.WALL_W, S.WALL_E                     # 0, 15: the stone leaves
    gw, ge = S.GLASS_W, S.GLASS_E                   # 1, 14: the glass planes
    zn, zs = T.Z0 - 1, T.Z1 + 1                     # 6, 26

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
                shell = x == gw and z <= T.PIER_Z[0]        # the shell's own stretch of the west wall
                put(x, y, z, wall_block(y) if shell else B.ASHLAR_FINE.block)

    # the windows: glass in the inner leaf, the stone leaf open in front of it, the head of that
    # opening shut by a stair hung in each top corner and a slab between the two (facade.CROWN)
    for front, bays, glass_x, face_x, inward in (("east", T.EAST_BAYS, ge, xe, -1), ("west", T.WEST_BAYS, gw, xw, 1)):
        for bay in bays:
            rows = MP.window_rows(bay)
            glass = (B.WINDOW_FROSTED if lit(front, bay) else B.WINDOW_DARK).block
            for z in rows:
                for y in range(S.WINDOW[0], S.WINDOW[1] + 1):
                    put(glass_x, y, z, glass)
                    cut(face_x, y, z)
            put(face_x, S.WINDOW[1], rows[0], st(B.ASHLAR_FINE.stairs, facing="north", half="top"))
            put(face_x, S.WINDOW[1], rows[-1], st(B.ASHLAR_FINE.stairs, facing="south", half="top"))
            for z in rows[1:-1]:
                put(face_x, S.WINDOW[1], z, st(B.ASHLAR_FINE.slab, type="top"))
            if lit(front, bay):
                middle = rows[len(rows) // 2]
                sources += [((face_x, y, middle), OUTSIDE) for y in (S.WINDOW[0] + 1, S.WINDOW[1] - 1)]
                if line is not None:
                    cells = [(glass_x, y, z) for z in rows for y in range(S.WINDOW[0], S.WINDOW[1] + 1)]
                    line(c, cells, (inward, 0), glass, origin=origin, panelled=True)

    # the door, and a piece of the gallery beyond it: indoors, so a floor, a lid and three walls stand
    # in for the hall, and one of the hall's lamps hangs on the cross wall beside the door
    for x in range(T.DOOR_X[0], T.DOOR_X[1] + 1):
        for y in range(DOOR_Y[0], DOOR_Y[1] + 1):
            cut(x, y, zn)
    for z in range(HALL_Z, GALLERY_Z[1] + 1):
        for x in range(gw, ge + 1):
            put(x, T.FLOOR_Y, z, B.ASHLAR_FINE.block)
            put(x, T.CEIL_Y, z, B.ASHLAR_FINE.block)
            if z == HALL_Z or x in (gw, ge):
                for y in range(T.FEET, T.TOP + 1):
                    put(x, y, z, wall_block(y))
    for x in range(gw + 1, ge):
        put(x, T.FEET, GALLERY_Z[0], B.IRON_BARS)
    lamps.place(c, "bracket", (HALL_LAMP[0], HALL_LAMP[1], float(zn)), facing="north", origin=origin,
                version="b", level=HALL_LAMP[2])
    return [((ox + x, oy + y, oz + z), level) for (x, y, z), level in sources]


def light(c, sources):
    """Put down the sources of the lit windows, never over a block that is there."""
    for (x, y, z), level in sources:
        c.set(x, y, z, st(B.LIGHT, level=level), keep=True)
