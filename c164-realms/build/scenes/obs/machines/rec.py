"""Work package machines/recorders: the recording instruments of the time-service room (plan
ART-PLAN 7.2 and 8, view V10; card plan/packages/machines/recorders.md, draft plan/parts/A5-machines.md 2.10).

The instrument wall of that room is panel blocks and the room's own (interiors/timeroom). This
package makes what stands in front of it and is a machine: it is seen to record and to report.

  drum        the drum chronograph on the console. A wooden base, two brass standards, between them
              the drum with its sheet of paper; a clockwork case at its east end with a seconds
              dial and a fly-ball governor; in front of the drum a rail with the pen carriage.
              Three display entities: the frame, the drum (it turns about its axle, once in
              MK.DRUM_REV), the pen on its rail (a part of its own, so that the motion line can
              move it). The trace on the sheet is drawn as it lies on a real one: a line round
              the drum for every turn, a jog in it for every second, from the west end up to
              where the pen stands.
  telegraph   the register on the console west of the key. A wooden base, the pair of coils and
              the armature lever over them, a reel of paper tape on two brackets, the tape down
              through the printing head and out to the front. Two entities: the machine, and the
              tape that hangs over the edge of the shelf and curls at its end (left out with
              tape=False where the register stands on something else). Lying on the shelf the
              tape would be a line from the door: the eye is little higher than the shelf.
  tube        the pneumatic tube on a wall, no more than five and a half pixels off it. Two
              entities: the terminal (a board on the wall, the brass tube down it, its bell mouth
              at the height of the hand, under the mouth a tray with a carrier in it) and the run
              above it, which ends in a copper elbow into the wall, just under whatever stands
              at the head of the pier (HEAD above the foot).

The world clocks of the card (mach_rec_clockwall) are not made here: the room has its own row of
five stopped slave dials (interiors/timeroom, STATUS "recorders"), and a second set would be the
same thing twice on one wall.

Placing. The room places them: place(canvas, kind, pos, facing=, origin=) is what it calls for
each of its slots (interiors/timeroom.SLOTS; agreed with that room, 11-16). pos is the middle of
the foot of a standing piece (drum, telegraph) or the point on the wall face behind the foot of
the terminal (tube), as the props line has it. The machines line runs before the rooms are
dressed, so build(), the master scene's call, places nothing.

Nothing here gives light: the console's lamps are the room's.
"""
import functools
import math

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import palette as P
from ..props import _kit as K

try:
    from ..motion import _kit as MK
except ImportError:                     # the motion line is not in the tree: everything stands still
    MK = None

NAME = "machines/rec"
PREFIX = "mach_rec_"
PX = 1 / 16.0
KINDS = ("drum", "telegraph", "tube")

WOOD = P.mat("dark_wood")
WOOD_LIGHT = P.mat("dark_wood", base=3)
BRASS, BRASS_D = K.BRASS, K.BRASS_D
IRON, IRON_D = K.IRON, K.IRON_D
COPPER = K.COPPER
PAPER = K.flat("cream", 2)              # paper under a lamp: a tone under the lightest, or it is a white dot from the door
PAPER_EDGE = K.flat("cream", 1)
INK = P.RAMPS["enamel"][1]              # what a pen and a printing wheel leave: the blue of the paper line's headings

# ---- the drum chronograph (pixels; x runs along the drum, the front is +z, 0 the middle of the foot)
BASE = (22.0, 12.0, 2.0)                # the wooden base: wide, deep, high
AXLE = (9.0, -1.0)                      # the drum's axis: above the foot, and its z
DRUM_R = 2.0 / math.tan(math.pi / 8.0)  # 4.83: eight faces of four pixels each
SHEET = (-7.5, 2.5)                     # the paper, along x
FLANGE = (1.0, 5.6)                     # the brass cheek at each end of the drum: its width, its radius
STANDARDS = (-9.5, 4.5)                 # the middles of the two bearing standards, along x
CASE = ((5.0, -4.0), (10.0, 4.0), 10.0) # the clockwork case: (x, z) of two corners, its top
RAIL = (9.5, 5.0)                       # the pen's rail: above the foot, and its z
PEN_X = -1.0                            # where the pen stands on its rail: at the end of the trace
DRUM_X = (SHEET[0] + SHEET[1]) / 2.0    # -2.5: the middle of the drum
TRACE = (                               # the sheet, one face of the drum: a line round the drum for each turn,
    ".i.i.i....",                       # a jog in every line where a second fell
    ".i.i.i....",
    "..i.i.i...",
    ".i.i.i....",
)
SECONDS_DIAL = (                        # the clockwork's seconds dial; the hand stands at 60, as at 7:55 sharp
    ".chc.",
    "cchcc",
    "ccbcc",
    "ccccc",
    ".ccc.",
)
DIAL_COLOURS = dict(c=P.RAMPS["porcelain"][3], h=P.RAMPS["iron"][0], b=P.RAMPS["brass"][3])

# ---- the telegraph register
T_BASE = (14.0, 12.0, 2.0)
LANE = (-4.5, -1.5)                     # the tape's lane along x: the reel, the printing head and the hanging tape are in it
REEL = (12.0, -3.0, 3.0)                # the reel's axis (above the foot, z) and the radius of the roll on it
HEAD = (8.0, 0.0)                       # where the tape turns forward under the printing head: above the foot, z
SHELF = 8.0                             # z of the front edge of the shelf: a shelf 16 deep, the register in its middle
EDGE = SHELF + 0.5                      # z of the front of the tape that hangs over that edge
HANG = 19.0                             # pixels the tape hangs below that roller before it curls
TAPE_T = 0.25                           # the thickness of the tape
MARKS = "ii.i.i.ii.i.ii.i.i.i.ii.ii.i.i.ii.i.i.ii.i."    # what the wheel has printed, along the tape

# ---- the pneumatic tube (x along the wall, z out of it, 0 the point of the wall behind the foot)
TUBE_R = 1.5                            # the tube is three pixels thick
TUBE_OFF = 2.75                         # its axis off the wall
BOARD = (5.0, 3.0, 27.0)                # the board on the wall: half its width, its foot and its top above pos
MOUTH = 11.0                            # the lip of the bell mouth above pos: at the height of the hand
TRAY = 4.0                              # the floor of the tray under it
TERMINAL = 36.0                         # where the terminal's model ends and the run's begins
HEAD = 79.5                             # the top of the run, the flange of its elbow on the wall: just under 5 blocks above pos


def _marks(n, start=0):
    return [MARKS[(start + i) % len(MARKS)] for i in range(n)]


def _tape_face(name, n, across=3, start=0):
    """The printed face of a run of tape n pixels long, the marks down its middle; as rows from
    the far end to the near one (a face that is looked at from the front or from above)."""
    return Sprite(name, ["." * (across // 2) + ch + "." * (across - across // 2 - 1) for ch in _marks(n, start)],
                  dict(i=INK), back=PAPER)


def _prism(m, a0, a1, c, radius, mat, cap, sides=8, faces=None, seed=None):
    """A prism along x in one tone all round, for a part that turns: Model.tube paints a highlight
    on the side that looks at the light and the game shades a face by where it looks at rest, and a
    wheel would carry both round with it."""
    hw = radius * math.tan(math.pi / sides)
    lo, hi = (a0, c[0] - hw, c[1] - radius), (a1, c[0] + hw, c[1] + radius)
    side = mat.variant(0, "ends") if hasattr(mat, "variant") else mat
    look = dict({"w": cap, "e": cap, "n": side, "s": side}, **(faces or {}))
    m._n += 1
    seed = m._n if seed is None else seed
    for i in range(sides // 2):
        angle = 360.0 * i / sides
        m.box(lo, hi, mat, rot=("x", angle, ((a0 + a1) / 2.0, c[0], c[1])) if angle else None, skip="du",
              faces=look, seed=seed, grain="x", shade=False)
    return m


def _drum_frame():
    """What stands still of the drum chronograph. Anchor: the middle of its foot."""
    name = PREFIX + "drum_frame"
    m = M.Model(name)
    w, d, h = BASE
    ay, az = AXLE
    m.box((-w / 2.0, 0.0, -d / 2.0), (w / 2.0, h, d / 2.0), WOOD, grain="x")
    for x in STANDARDS:
        m.box((x - 1.0, h, az - 4.0), (x + 1.0, h + 0.5, az + 4.0), BRASS_D)                    # its foot
        for s in (-1.0, 1.0):
            m.beam((x, h + 0.5, az + s * 3.0), (x, ay, az), 1.0, 1.5, BRASS)                    # its two legs
        m.tube("x", (ay, az), x - 0.5, x + 0.5, 1.5, BRASS)                                     # the bearing
        m.box((x - 0.5, RAIL[0] - 0.5, az + 1.5), (x + 0.5, RAIL[0] + 0.5, RAIL[1] + 0.5), BRASS_D)   # the arm that holds the rail
    m.box((STANDARDS[0] - 0.5, RAIL[0] - 0.5, RAIL[1] - 0.5), (STANDARDS[1] + 0.5, RAIL[0] + 0.5, RAIL[1] + 0.5),
          IRON, grain="x")                                                                      # the rail
    (x0, z0), (x1, z1), top = CASE
    dial = Sprite(name + "_dial", list(SECONDS_DIAL), DIAL_COLOURS, back=BRASS)
    m.box((x0, h, z0), (x1, top, z1), BRASS, faces={"s": dial})                                 # the clockwork case
    m.box((x0 - 0.25, top, z0 - 0.25), (x1 + 0.25, top + 0.5, z1 + 0.25), BRASS_D)
    gx = (x0 + x1) / 2.0                                                                        # the governor on it
    m.tube("y", (gx, 0.0), top + 0.5, top + 5.0, 0.5, IRON, sides=4)
    for s in (-1.0, 1.0):
        m.rod((gx, top + 4.5, 0.0), (gx + s * 2.5, top + 2.5, 0.0), 0.3, IRON, sides=4)
        m.ball((gx + s * 2.5, top + 2.0, 0.0), 1.1, BRASS, sides=8, layers=3)
    return m


def _drum():
    """The drum with its sheet: what turns. Anchor: the middle of its axle; the axle runs along x."""
    name = PREFIX + "drum"
    half = (SHEET[1] - SHEET[0]) / 2.0
    width, radius = FLANGE
    trace = Sprite(name + "_trace", list(TRACE), dict(i=INK), back=PAPER)
    m = M.Model(name)
    _prism(m, -half, half, (0.0, 0.0), DRUM_R, PAPER, PAPER_EDGE, faces={"s": trace, "n": trace.mirrored()})
    for s in (-1.0, 1.0):
        a, b = sorted((s * half, s * (half + width)))
        _prism(m, a, b, (0.0, 0.0), radius, BRASS, K.flat("brass", 2))
    reach = STANDARDS[1] + 0.5 - DRUM_X                                 # to the outer face of a standard
    _prism(m, -reach, reach, (0.0, 0.0), 0.75, IRON, K.flat("iron", 4), sides=4)
    # the bar that clamps the sheet: it lies along the drum and shows that the drum turns
    m.box((-half, DRUM_R, -0.5), (half, DRUM_R + 0.5, 0.5), K.flat("brass", 3), rot=("x", 45.0, (0.0, 0.0, 0.0)),
          shade=False)
    return m


def _pen():
    """The pen carriage. Anchor: on the rail's axis, in the middle of the carriage."""
    m = M.Model(PREFIX + "pen")
    m.box((-1.0, -1.0, -0.75), (1.0, 1.0, 0.75), BRASS)
    m.box((-0.5, 1.0, -0.5), (0.5, 2.0, 0.5), K.flat("enamel", 1))                              # the ink well
    reach = DRUM_R * math.sqrt(0.5)                                     # the pen meets the sheet half way up its front
    tip = (0.0, AXLE[0] + reach - RAIL[0], AXLE[1] + reach - RAIL[1])
    m.beam((0.0, 1.0, -0.5), tip, 0.5, 0.5, IRON_D)
    return m


def _telegraph():
    """The register. Anchor: the middle of its foot; the tape leaves it at the front, in its lane."""
    name = PREFIX + "telegraph"
    m = M.Model(name)
    w, d, h = T_BASE
    x0, x1 = LANE
    ry, rz, rr = REEL
    hy, hz = HEAD
    m.box((-w / 2.0, 0.0, -d / 2.0), (w / 2.0, h, d / 2.0), WOOD, grain="x")
    # the reel on its two brackets
    for x in (x0 - 1.5, x1 + 0.5):
        m.box((x, h, rz - 1.0), (x + 1.0, ry + 1.0, rz + 1.0), BRASS, grain="y")
    m.tube("x", (ry, rz), x0, x1, rr, P.mat("cream", base=2), sides=8, cap=PAPER_EDGE)
    for x in (x0 - 0.5, x1):
        m.tube("x", (ry, rz), x, x + 0.5, rr + 0.6, BRASS, sides=8)
    m.tube("x", (ry, rz), x0 - 1.75, x1 + 1.75, 0.5, IRON, sides=4)
    # the tape: down from the front of the roll, under the printing head, forward to the roller at the edge
    front = rz + rr
    m.box((x0, hy, front - TAPE_T), (x1, ry, front), PAPER, faces={"s": _tape_face(name + "_down", int(round(ry - hy)))})
    m.box((x0, hy, front), (x1, hy + TAPE_T, SHELF), PAPER,
          faces={"u": _tape_face(name + "_out", int(round(SHELF - front)), start=5)})
    m.box((x0, hy, SHELF), (x1, hy + TAPE_T, EDGE), PAPER)
    m.box((x0 + 0.25, h, hz), (x1 - 0.25, hy - 2.0, hz + 1.5), BRASS_D)                         # the head's pedestal
    m.box((x0 - 0.5, hy - 2.0, hz - 0.5), (x1 + 0.5, hy, hz + 2.0), BRASS)                      # the head: the tape runs over it
    for x in (x0 - 0.75, x1 + 0.25):
        m.box((x, hy - 1.25, hz + 2.0), (x + 0.5, hy - 0.25, EDGE), BRASS_D, grain="z")         # the two arms out to the roller
    m.tube("x", (hy - 0.5, EDGE - 0.5), x0 - 0.25, x1 + 0.25, 0.5, BRASS, sides=4)              # the roller
    # the pair of coils, the armature over them, the lever that carries the printing wheel
    for x in (2.0, 5.0):
        m.tube("y", (x, -2.5), h, h + 0.5, 1.6, BRASS_D, sides=8)
        m.tube("y", (x, -2.5), h + 0.5, 6.5, 1.25, COPPER, sides=8)
        m.tube("y", (x, -2.5), 6.5, 7.0, 1.6, BRASS_D, sides=8)
    m.box((1.0, 7.25, -3.5), (6.0, 7.75, 0.9), IRON)
    m.box((x0 + 1.25, hy + 0.5, hz + 0.1), (6.5, hy + 1.1, hz + 0.9), BRASS, grain="x")
    m.box((x0 + 1.1, hy + TAPE_T, hz + 0.2), (x0 + 1.9, hy + 0.5, hz + 0.8), IRON_D)            # the wheel on the tape
    m.box((5.75, h, hz), (6.75, hy + 1.5, hz + 1.0), BRASS, grain="y")                          # the lever's post
    m.tube("y", (6.25, hz + 0.5), hy + 1.5, hy + 2.5, 0.4, IRON, sides=4)
    for x in (2.5, 5.0):                                                                        # the line's two binding posts
        m.tube("y", (x, 4.5), h, h + 2.0, 0.5, BRASS, sides=4)
        m.tube("y", (x, 4.5), h + 2.0, h + 2.75, 0.9, BRASS_D, sides=8)
    return m


def _tape():
    """The tape that hangs from the register's roller over the edge of the shelf and curls at its
    end. Anchor: the register's (the middle of its foot), so both are placed on one point."""
    name = PREFIX + "tape"
    x0, x1 = LANE
    top = HEAD[0] + TAPE_T
    foot = top - HANG
    m = M.Model(name)
    m.box((x0, foot, EDGE - TAPE_T), (x1, top, EDGE), PAPER,
          faces={"s": _tape_face(name + "_hang", int(round(HANG)), start=11)})
    m.ring("x", ((x0 + x1) / 2.0, foot, EDGE + 1.5 - TAPE_T / 2.0), 1.5, TAPE_T, x1 - x0, PAPER, sides=8, arc=(-45.0, 270.0))
    return m


def _terminal():
    """The terminal of the pneumatic tube. Anchor: the point on the wall behind the middle of its
    foot; the wall is the plane z = 0 and the terminal stands out along +z."""
    m = M.Model(PREFIX + "tube")
    z = TUBE_OFF
    half, foot, top = BOARD
    m.box((-half, foot, 0.0), (half, top, 1.0), WOOD_LIGHT, skip="n", grain="y")                # the board on the wall
    m.tube("y", (0.0, z), MOUTH + 3.0, TERMINAL, TUBE_R, BRASS)
    m.taper("y", (0.0, z), MOUTH, MOUTH + 3.0, TUBE_R + 1.0, TUBE_R + 0.25, BRASS_D, steps=2)   # the bell mouth
    m.box((-2.5, top - 4.0, 1.0), (2.5, top - 3.0, z + TUBE_R + 0.5), IRON_D)                   # the clip that holds it to the board
    lip = z + TUBE_R + 1.25                                                                     # 5.5: the tray's front
    m.box((-4.5, TRAY, 1.0), (4.5, TRAY + 0.75, lip), IRON_D)                                   # the tray under the mouth
    m.box((-4.5, TRAY + 0.75, lip - 0.75), (4.5, TRAY + 2.5, lip), IRON, grain="x")
    for x in (-4.5, 3.75):
        m.box((x, TRAY + 0.75, 1.0), (x + 0.75, TRAY + 3.5, lip - 0.75), IRON, grain="z")
    m.tube("x", (TRAY + 2.0, z + 0.25), -3.0, 3.0, 1.25, COPPER)                                # a carrier in the tray
    for x in (-3.5, 3.0):
        m.tube("x", (TRAY + 2.0, z + 0.25), x, x + 0.5, 1.0, K.flat("cream", 1), sides=8)       # its two felts
    return m


def _run():
    """The run of the tube over the terminal: the tube, a coupling at its foot, a clip, and at its
    head the copper elbow into the wall with its flange. Anchor: the point on the wall behind its
    foot (TERMINAL above the terminal's)."""
    m = M.Model(PREFIX + "tube_run")
    z = TUBE_OFF
    top = HEAD - TERMINAL                               # the top of the flange
    turn = top - 2.25                                   # the height of the elbow's leg into the wall
    m.tube("y", (0.0, z), 0.0, turn - 2.5, TUBE_R, BRASS)
    m.tube("y", (0.0, z), 0.0, 2.0, TUBE_R + 0.5, BRASS_D)
    m.box((-2.5, turn - 16.0, 0.0), (2.5, turn - 15.0, z + TUBE_R + 0.5), IRON_D)
    m.hose([(0.0, turn - 3.0, z), (0.0, turn - 1.0, z), (0.0, turn, z - 1.25), (0.0, turn, 0.5)], TUBE_R + 0.25, COPPER)
    m.box((-2.25, turn - 2.25, 0.0), (2.25, top, 0.5), BRASS_D, skip="n")
    return m


@functools.lru_cache(maxsize=None)
def _models():
    made = (_drum_frame(), _drum(), _pen(), _telegraph(), _tape(), _terminal(), _run())
    return {m.name: m for m in made}


def models():
    return dict(_models())


# ---- placing ---------------------------------------------------------------------------------------
def _at(pos, yaw, pixels):
    """The point `pixels` (in a model's own frame, from its anchor) of a piece placed at pos."""
    d = K.turn(yaw, tuple(v * PX for v in pixels))
    return tuple(pos[i] + d[i] for i in range(3))


def _drum_at(canvas, pos, yaw, origin):
    own = _models()
    n = K.put(canvas, own[PREFIX + "drum_frame"], pos, yaw=yaw, origin=origin)
    n += K.put(canvas, own[PREFIX + "drum"], _at(pos, yaw, (DRUM_X, AXLE[0], AXLE[1])), yaw=yaw, origin=origin)
    if MK is not None:
        MK.spin(canvas, "x", MK.DRUM_REV)               # the top of the drum comes forward, to the pen
    n += K.put(canvas, own[PREFIX + "pen"], _at(pos, yaw, (PEN_X, RAIL[0], RAIL[1])), yaw=yaw, origin=origin)
    return n


def _telegraph_at(canvas, pos, yaw, origin, tape=True):
    own = _models()
    n = K.put(canvas, own[PREFIX + "telegraph"], pos, yaw=yaw, origin=origin)
    if tape:
        n += K.put(canvas, own[PREFIX + "tape"], pos, yaw=yaw, origin=origin)
    return n


def _tube_at(canvas, pos, facing, origin):
    own = _models()
    n = K.put(canvas, own[PREFIX + "tube"], pos, mount="wall", facing=facing, origin=origin)
    n += K.put(canvas, own[PREFIX + "tube_run"], (pos[0], pos[1] + TERMINAL * PX, pos[2]), mount="wall", facing=facing,
               origin=origin)
    return n


def place(canvas, kind, pos, facing="south", origin=(0, 0, 0), yaw=None, **how):
    """Place one of KINDS; returns the number of display entities.

    drum, telegraph   pos is the middle of the foot; the front looks `facing` (or is turned yaw).
                      telegraph: the tape hangs over the front edge of the shelf, which is 8 pixels
                      in front of pos; tape=False leaves it out, where the register stands on
                      something else.
    tube              pos is the point on the wall face behind the middle of the terminal's foot,
                      `facing` the way that face looks. The mouth is 11 pixels above pos, the run
                      ends just under 5 blocks above it.
    """
    if kind == "tube":
        return _tube_at(canvas, pos, facing, origin, **how)
    turn = K.FACING[facing] if yaw is None else yaw
    if kind == "drum":
        return _drum_at(canvas, pos, turn, origin, **how)
    if kind == "telegraph":
        return _telegraph_at(canvas, pos, turn, origin, **how)
    raise KeyError(f"machines/rec makes {', '.join(KINDS)}; not {kind!r}")


def build(canvas, origin=(0, 0, 0)):
    """The master scene's call. Nothing: the time room places the machines at its slots when it is
    dressed (interiors/timeroom, PLACES_RECORDERS), which is after the machines line has run."""
    return 0
