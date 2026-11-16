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

  globe         the celestial globe of the south aisle turns in its stand, once in GLOBE_TURN
                ticks, the way the sky turns over the hill: about its polar axis, which leans to
                true north. The globe is props/instruments' and one model, stand and ball; what
                turns is a second ball, the same sky drawn by the same code a quarter of a
                pixel larger, on the same centre: it hides the ball in the stand and nothing
                else, and where instruments no longer offers what draws it the stand's own
                ball is seen as before and stands still. (A ball of its own in instruments,
                shown apart from the stand, would save the second set of pictures: asked of
                m1, 11-16.)

The flag is a tone under the palette's lightest cream: under the aisle's lamps a full cream is a
white dot from the door (the recorders' paper, machines/rec), and nothing new in the hall is to
be lighter than the pier's face (cr3: under 0.20).
"""
import functools
import math

from artkit import models as M

from ..common import palette as P
from ..main import shell
from ..props import _kit as K
from ..props import instruments

try:
    from ..motion import _kit as MK
except ImportError:                     # the motion line is not in the tree: everything stands still
    MK = None

PREFIX = "int_starhall_"
ROOM = shell.ROOMS["star hall"]
X0, Z0, X1, Z1 = ROOM["box"]                    # 2, -5, 15, 5
FEET = ROOM["feet"]                             # 0

HANG_Y = FEET + 3.0             # the middle of the case: on the shaft, which is the third and fourth block
CASE = (4.5, -8.0, 5.0, 2.5)    # the case: half its width, its foot and its top about the anchor, its depth. With
#                                 its mouldings it is ten pixels wide and no more: the shaft it hangs on is the
#                                 lightest stone of the first look's lower right, and keeps a margin either side (cr3)
WINDOW = (1.5, 1.25)            # half the width and half the height of a window
WINDOWS = tuple((x, y) for y in (2.0, -1.5, -5.0) for x in (-2.0, 2.0))
# the windows in use and their cycles: (the window, ticks its flag is up, ticks it is down)
CALLS = ((0, 190, 70), (3, 270, 70), (4, 350, 70))

GLOBE_SHELL = 0.25      # pixels the turning ball's poles stand over those of the ball in the stand
GLOBE_TURN = -900       # ticks to a turn; the minus: seen from over its north pole a star globe turns clockwise
GLOBE_NEEDS = ("_ball", "_stars", "_leaned", "SKY", "GLOBE_R", "GLOBE_Y", "GLOBE_TILT", "GLOBE_YAW")

WOOD = P.mat("dark_wood")
WOOD_D = P.mat("dark_wood", base=1)
GROUND = K.flat("iron", 1)
FLAG = K.flat("cream", 2)


def _annunciator():
    """The case, 9 px wide and 13 tall, the bell 6 px across on its top. Anchor: on the wall,
    8 px over the case's foot. The bell is dark brass: a gong of full brass, looking into the
    hall under the aisle's lamps, would be lighter than the pier's face."""
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
    m.tube("z", (0.0, top + 3.5), 1.0, 2.5, 3.0, K.BRASS_D, sides=12)               # the gong
    m.tube("z", (0.0, top + 3.5), 2.5, 3.0, 1.0, K.flat("brass", 1), sides=8)       # its nut
    m.box((3.0, top, 1.25), (4.0, top + 2.5, 2.25), K.IRON)                         # the hammer beside it
    m.box((1.5, top, 0.5), (4.5, top + 1.0, 2.5), K.IRON_D)                         # and its coils
    return m


def _flag(name, mat):
    """What a window in use shows: `up`, its dark ground, or `down`, the flag that has dropped
    into it. Anchor: on the wall behind the window's middle."""
    m = M.Model(PREFIX + "flag_" + name)
    d = CASE[3]
    m.box((-WINDOW[0] + 0.25, -WINDOW[1] + 0.25, d + 0.25), (WINDOW[0] - 0.25, WINDOW[1] - 0.25, d + 0.5), mat)
    return m


def _sky_ball():
    """The celestial globe's ball by itself, as instruments draws it in the stand (the same facets,
    the same sky, leaning the same way) and GLOBE_SHELL larger. Anchor: its centre. None when
    instruments has changed what draws it.

    instruments names the pictures of a ball after its own prefix, and a picture with the props'
    prefix written by a room lies in the props' area (tools/check.py, conflicts): the ball is
    drawn with this package's prefix in that place."""
    I = instruments
    if not all(hasattr(I, name) for name in GLOBE_NEEDS + ("PREFIX",)):
        return None
    m = M.Model(PREFIX + "sky_ball")
    theirs, I.PREFIX = I.PREFIX, PREFIX
    try:
        I._ball(m, "sky", (0.0, 0.0, 0.0), I.GLOBE_R + GLOBE_SHELL, I.SKY, 16, 8,
                I._stars(I._leaned(I.GLOBE_TILT, I.GLOBE_YAW)), swing=11.25, crown=True)
    finally:
        I.PREFIX = theirs
    return m


@functools.lru_cache(maxsize=None)
def _models():
    made = [_annunciator(), _flag("up", GROUND), _flag("down", FLAG), _sky_ball()]
    return {m.name: m for m in made if m is not None}


def models():
    return dict(_models())


def pilaster():
    """(x, z of the face, the way it looks) of the pilaster the annunciator hangs on: the middle
    one of the north aisle, on the face that looks across the hall."""
    from . import starhall
    xs = starhall.beam_xs()
    return xs[len(xs) // 2] + 0.5, Z0 + 1.0, "south"


def _globe(canvas, origin):
    """The turning ball of the celestial globe, where interiors/starhall stands the globe."""
    from . import starhall
    ball = _models().get(PREFIX + "sky_ball")
    if ball is None or MK is None:
        return 0
    I = instruments
    (x, z), facing = starhall.globe_at()
    yaw = K.FACING[facing]
    n = K.put(canvas, ball, (x, FEET + I.GLOBE_Y / 16.0, z), facing=facing, origin=origin)
    tilt = math.radians(I.GLOBE_TILT)
    with_yaw = math.radians(I.GLOBE_YAW)
    pole = (math.sin(tilt) * math.cos(with_yaw), math.cos(tilt), -math.sin(tilt) * math.sin(with_yaw))
    MK.spin(canvas, K.turn(yaw, pole), GLOBE_TURN)
    return n


def dress(canvas, origin=(0, 0, 0), version="a"):
    """Hang the annunciator and its three flags, set the globe turning; returns the display
    entities placed."""
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
    return n + _globe(canvas, origin)
