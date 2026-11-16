"""interiors/_starhall_gallery -- what stands on the two galleries of the star hall. A part of
interiors/starhall (its PARTS), which calls dress() at the end of its own and adds models() to its
models; the underscore keeps the file out of the category's auto-discovery.

A gallery is the walk along a cross wall at the height of the main floor (main/shell: feet 7, the
cell against the wall on z -5 and 5, the railing on the next cell). What the observatory keeps up
here stands against the wall:

  a "academy"    the record office. At the west end of the south gallery a run in dark wood: two
                 cabinets of record cards, one of instruments and, nearest the door, a glazed case
                 with a log book open in it; a table globe, two shut log books and a sextant on
                 the cabinets' tops. At the east end of the north gallery, beside the great chart,
                 a cabinet of instruments with the glass ball of a sunshine recorder on it.
  b "workshop"   the store. In the same places one instrument cabinet with its sextant, a packing
                 case with a smaller one on it and a travelling trunk as they came up from the
                 cable car, a log book left on the trunk's lid and a barometer hung on the wall
                 over it; beside the north chart a case with the globe unpacked on it.

Both runs are looked along more than they are looked at: the hall's two gallery pictures stand at
the far end of each walk. So the south run steps down toward the door (the low piece first, the
tall one behind it, the instrument on that turned to face down the walk), and what stands at the
end of the north walk carries a ball, which is the same outline from every side.

Kept clear (interiors/starhall, c348): the wing doors and a cell either side of them, the great
charts, the bridge onto the ring stair and the north walk west of it, the window niches. Nothing
reaches higher than TOP_Y, nothing is a light source, the emblem is not shown.

Every piece is one of props/furniture, props/instruments or props/paper, placed by that package's
place(); this file has no model of its own. A piece whose package is not in the tree is left out.
A display entity stops nobody: the pieces stand in the walk's own cell, and between a cabinet's
front and the railing's bars 9.5 px are left.
"""
import importlib

from ..common import skeleton as S
from ..main import shell
from ..props import _kit as K

ROOM = shell.ROOMS["star hall"]
X0, Z0, X1, Z1 = ROOM["box"]                    # 2, -5, 15, 5
FEET = shell.DECK_Y + 1                         # 7: where one stands on a gallery
TOP_Y = FEET + 3.0                              # nothing reaches higher: the caged lamps hang at 10.5
VERSIONS = ("a", "b")

PX = 1.0 / 16.0
GAP = 0.75 * PX                                 # between a piece's back and the wall: a case set down a little
#                                                 askew does not run its corner into the stone
WALL = {"north": float(Z0), "south": float(Z1 + 1)}     # the face of a gallery's wall
INTO = {"north": 1.0, "south": -1.0}            # from that face into the hall, along z
LOOKS = {"north": "south", "south": "north"}    # the way a piece against that wall looks

DOORS = tuple(shell.ROOM_DOOR_X)                # 7, 8: a gallery's door into its wing room
MERIDIAN = int(S.ORRERY_CENTRE[0])              # 11: the great charts hang over this cell and one either side
RUN = tuple(range(X0, DOORS[0] - 1))            # 2..5: the walk west of the door and of the cell kept free beside it
LAST = MERIDIAN + 2                             # 13: the walk's last cell, between a great chart and a window niche
BAROMETER_Y = FEET + 0.95                       # its foot: clear of the trunk under it, its head at TOP_Y less a pixel
DOWN_THE_WALK = 55.0                            # a flat instrument turned to show its face to the walk's east end

# A version's pieces: (package, kind, wall, x, what it stands on or None, turned by degrees).
# x is the middle of the piece along the wall. What stands on another piece is given the x of that
# piece and is put on its top (props/furniture.TOP); (dx, dz) moves it in the carrier's own frame.
SETS = {
    "a": (
        ("furniture", "card_cabinet", "south", RUN[0] + 0.5, None, 0.0),
        ("furniture", "card_cabinet", "south", RUN[1] + 0.5, None, 0.0),
        ("furniture", "instrument_cabinet", "south", RUN[2] + 0.5, None, 0.0),
        ("furniture", "display_case", "south", RUN[3] + 0.5, None, 0.0),
        ("instruments", "globe", "south", RUN[0] + 0.5, "card_cabinet", 25.0),
        ("paper", "logbook_shut", "south", RUN[1] + 0.5, "card_cabinet", 8.0),
        ("paper", "logbook_shut", "south", RUN[1] + 0.5, ("card_cabinet", 2.0 * PX), -14.0),
        ("instruments", "sextant", "south", RUN[2] + 0.5, "instrument_cabinet", DOWN_THE_WALK),
        ("paper", "logbook", "south", RUN[3] + 0.5, "display_case", 6.0),
        ("furniture", "instrument_cabinet", "north", LAST + 0.5, None, 0.0),
        ("instruments", "sunshine_recorder", "north", LAST + 0.5, "instrument_cabinet", 0.0),
    ),
    "b": (
        ("furniture", "instrument_cabinet", "south", RUN[0] + 0.5, None, 0.0),
        ("instruments", "sextant", "south", RUN[0] + 0.5, "instrument_cabinet", DOWN_THE_WALK),
        ("furniture", "crate", "south", RUN[1] + 0.5, None, 4.0),
        ("furniture", "crate_small", "south", RUN[1] + 0.5, "crate", -12.0),
        ("furniture", "trunk", "south", RUN[3], None, 0.0),
        ("paper", "logbook_shut", "south", RUN[3] - 5.0 * PX, ("trunk", 0.5 * PX), 20.0),      # on the straps
        ("instruments", "barometer", "south", RUN[3] + 5.5 * PX, None, 0.0),
        ("furniture", "crate", "north", LAST + 0.5, None, -5.0),
        ("instruments", "globe", "north", LAST + 0.5, "crate", 25.0),
    ),
}


def _package(name):
    """A package of the props line, or None while it is not in the tree."""
    try:
        return importlib.import_module(f"{__package__.rpartition('.')[0]}.props.{name}")
    except ImportError:
        return None


def _box(package, kind):
    """(lo, hi) of a piece's model in pixels, in its own frame: +z is its front."""
    return package.models()[package.PREFIX + kind].bounds()


def pieces(version):
    """Where everything goes: [(package, kind, (x, y, z), yaw)], scene coordinates at origin 0.
    A piece of a package that is not in the tree is left out, and what stands on it with it."""
    out = []
    for name, kind, wall, x, on, turn in SETS[version]:
        package, furniture = _package(name), _package("furniture")
        if package is None or kind not in package.SPEC:
            continue
        yaw = K.FACING[LOOKS[wall]] + turn
        if on is None and package.SPEC[kind]["mount"] == "wall":
            out.append((package, kind, (x, BAROMETER_Y, WALL[wall]), yaw))
            continue
        if on is None:
            lo, hi = _box(package, kind)
            y, back = float(FEET), -lo[2] * PX
        else:
            carrier, lift = on if isinstance(on, tuple) else (on, 0.0)
            if furniture is None or carrier not in furniture.SPEC:
                continue
            lo, hi = _box(furniture, carrier)
            # on the middle of the carrier's top, which is not over the middle of its foot
            y, back = FEET + furniture.TOP[carrier] + lift, -lo[2] * PX + (hi[2] + lo[2]) * PX / 2.0
        out.append((package, kind, (x, y, WALL[wall] + INTO[wall] * (back + GAP)), yaw))
    return out


def models():
    return {}


def dress(canvas, origin=(0, 0, 0), version="a"):
    """Furnish the two galleries of the hall that stands at `origin`; returns the display entities placed."""
    n = 0
    for package, kind, pos, yaw in pieces(version):
        n += package.place(canvas, kind, pos, origin=origin, yaw=yaw)
    return n
