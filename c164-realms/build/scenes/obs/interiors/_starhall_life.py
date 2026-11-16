"""interiors/_starhall_life -- what moves on the walls of the star hall (the second round, A0
11-16 12:12: every room shows at least two things that move, one of them in the first look from
the door; the orrery and the mother clock are the machines' and do not count). A part of
interiors/starhall (its PARTS), which calls dress() at the end of its own and adds models() to
its models; the underscore keeps the file out of the category's auto-discovery. No blocks, no
light sources.

Where. From the door (S.V7) the walls of the aisles are hidden behind the pilasters that stand
under the beams; what the first look shows of an aisle is the faces of those pilasters that look
across the hall, pale stone a block wide from the base to the capital (the review's empty places
of A8, cr3 #86304, 2). What hangs there hangs on the shaft of the middle pilaster, the one under
the meridian.

  annunciator   on the north pilaster, beside the switchboard: the bell indicator of the house, a
                shallow glazed case of dark wood with six windows and the bell on its top. A
                call from a room drops a pale flag into its window; it is set back by hand a
                while later. Three of the six windows are in use: each has a flag of its own, a
                display entity that shows the window's dark ground and, for a few seconds of
                every cycle, the flag (motion's blink: two commands a cycle). The three cycles
                differ in length, so the flags fall in no order one could learn.

The flag is a tone under the palette's lightest cream: under the aisle's lamps a full cream is a
white dot from the door (the recorders' paper, machines/rec), and nothing new in the hall is to
be lighter than the pier's face (cr3: under 0.20).
"""
import functools

from artkit import models as M

from ..common import palette as P
from ..main import shell
from ..props import _kit as K

try:
    from ..motion import _kit as MK
except ImportError:                     # the motion line is not in the tree: everything stands still
    MK = None

PREFIX = "int_starhall_"
ROOM = shell.ROOMS["star hall"]
X0, Z0, X1, Z1 = ROOM["box"]                    # 2, -5, 15, 5
FEET = ROOM["feet"]                             # 0

HANG_Y = FEET + 3.0             # the middle of the case: on the shaft, which is the third and fourth block
CASE = (7.0, -8.0, 5.0, 2.5)    # the case: half its width, its foot and its top about the anchor, its depth
WINDOW = (2.5, 1.5)             # half the width and half the height of a window
WINDOWS = tuple((x, y) for y in (1.75, -1.75, -5.25) for x in (-3.25, 3.25))
# the windows in use and their cycles: (the window, ticks its flag is up, ticks it is down)
CALLS = ((0, 190, 70), (3, 270, 70), (4, 350, 70))

WOOD = P.mat("dark_wood")
WOOD_D = P.mat("dark_wood", base=1)
GROUND = K.flat("iron", 1)
FLAG = K.flat("cream", 2)


def _annunciator():
    """The case, 14 px wide and 13 tall, the bell 6 px across on its top. Anchor: on the wall,
    8 px over the case's foot."""
    m = M.Model(PREFIX + "annunciator")
    w, y0, y1, d = CASE
    m.box((-w, y0, 0.0), (w, y1, d), WOOD_D, grain="y", skip="n")
    m.box((-w - 0.5, y1, 0.0), (w + 0.5, y1 + 1.0, d + 0.5), WOOD, grain="x")       # cornice
    m.box((-w - 0.5, y0 - 1.0, 0.0), (w + 0.5, y0, d + 0.5), WOOD, grain="x")       # foot moulding
    m.box((-w + 1.0, y0 + 1.0, d), (w - 1.0, y1 - 1.0, d + 0.25), GROUND)           # the ground behind the glass
    for x, y in WINDOWS:
        for s in (-1.0, 1.0):                                                       # a brass frame to each window
            m.box((x - WINDOW[0], y + s * WINDOW[1] - 0.25, d + 0.25), (x + WINDOW[0], y + s * WINDOW[1] + 0.25, d + 0.75),
                  K.BRASS_D, grain="x")
            m.box((x + s * WINDOW[0] - 0.25, y - WINDOW[1], d + 0.25), (x + s * WINDOW[0] + 0.25, y + WINDOW[1], d + 0.75),
                  K.BRASS_D, grain="y")
    top = y1 + 1.0
    m.box((-1.0, top, 0.5), (1.0, top + 1.0, 2.0), K.IRON_D)                        # the bell's bracket
    m.tube("z", (0.0, top + 3.5), 1.0, 2.5, 3.0, K.BRASS, sides=12)                 # the gong
    m.tube("z", (0.0, top + 3.5), 2.5, 3.0, 1.0, K.BRASS_D, sides=8)                # its nut
    m.box((3.25, top, 1.25), (4.25, top + 2.5, 2.25), K.IRON)                       # the hammer beside it
    m.box((2.0, top, 0.5), (5.5, top + 1.0, 2.5), K.IRON_D)                         # and its coils
    return m


def _flag(name, mat):
    """What a window in use shows: `up`, its dark ground, or `down`, the flag that has dropped
    into it. Anchor: on the wall behind the window's middle."""
    m = M.Model(PREFIX + "flag_" + name)
    d = CASE[3]
    m.box((-WINDOW[0] + 0.5, -WINDOW[1] + 0.5, d + 0.25), (WINDOW[0] - 0.5, WINDOW[1] - 0.5, d + 0.5), mat)
    return m


@functools.lru_cache(maxsize=None)
def _models():
    made = [_annunciator(), _flag("up", GROUND), _flag("down", FLAG)]
    return {m.name: m for m in made}


def models():
    return dict(_models())


def pilaster():
    """(x, z of the face, the way it looks) of the pilaster the annunciator hangs on: the middle
    one of the north aisle, on the face that looks across the hall."""
    from . import starhall
    xs = starhall.beam_xs()
    return xs[len(xs) // 2] + 0.5, Z0 + 1.0, "south"


def dress(canvas, origin=(0, 0, 0), version="a"):
    """Hang the annunciator and its three flags; returns the display entities placed."""
    models = _models()
    x, z, facing = pilaster()
    yaw = K.FACING[facing]
    n = K.put(canvas, models[PREFIX + "annunciator"], (x, HANG_Y, z), mount="wall", facing=facing, origin=origin)
    for window, up, down in CALLS:
        dx, dy, dz = K.turn(yaw, (WINDOWS[window][0] / 16.0, WINDOWS[window][1] / 16.0, 0.0))
        n += K.put(canvas, models[PREFIX + "flag_up"], (x + dx, HANG_Y + dy, z + dz), mount="wall", facing=facing,
                   origin=origin)
        if MK is not None:
            MK.blink(canvas, PREFIX + "flag_down", up, down, name=f"{PREFIX}flag_{window}")
    return n
