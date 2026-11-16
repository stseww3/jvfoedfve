"""The switchboard of the battery room and the copper bars that come to it (card
plan/packages/interiors/batteryroom.md; what the room needs to know is on the page
plan/packages/machines/batteryboard.md). The room is interiors/batteryroom's: that module places
the board with place() and runs the bars with run(). This module has no build() of its own.

What it is. A board of the family of the power house's (machines/board.py): the same slate slabs
in an iron frame, the same meters, knife switches and pointers. Three slabs on four iron legs
before the room's north wall, their faces to the aisle. The middle slab is the battery's: its
ammeter, whose pointer swings slowly to either side of the middle of its scale, and under it the
change-over switch for charging and discharging, two blades hinged in the middle and thrown up, the
lower jaws empty. Each wing is one pole's: a meter (the voltmeter on the west), the clamp where a
pair of copper bars from the racks lands (BUS_IN), and under it that pole's knife switch. Over the
head run two bus bars on porcelain posts, and behind them two conduits rise through the ceiling
to the time room (RISERS).

Where it stands. Under the time room, before the middle of the north wall, as wide as five cells:

    x  the board is 5 blocks wide about the room's axis (AXIS_X); the middle slab is as wide as
       the aisle
    y  the floor is S.GROUND; the slabs reach from one block to four above it, the bars over the
       head to four and five eighths, the conduits to the ceiling
    z  the wall's face is WALL_Z; the slabs' face is the plane z = FACE_Z, ten texels before it

How it is lit. The pieces are drawn looking east in the kit's leaning frame and placed with a
quarter turn, so that what looks into the room is shown at its full tone. All of them stand in
one cell, STAND, in the air before the middle slab, and take its light: the room hangs its lamp
so that this cell is lit. The meters' ticks glow by themselves.

Every model is drawn in texels in the board's own frame: x from the slabs' face into the room,
y up from the floor, z along the board from its east end.
"""
import functools

from ..common import skeleton as S
from ..main import shell
from ..motion import _kit as MK
from . import _powerkit as K
from . import board as PB

PREFIX = "mach_bboard_"

# --- where it stands (scene coordinates, blocks) ------------------------------------------------------
_BOX = shell.ROOMS.get("battery room", shell.ROOMS["time room"])["box"]     # the room lies under the time room
FLOOR = float(S.GROUND)                 # 0.0
AXIS_X = (_BOX[0] + _BOX[2] + 1) / 2.0  # 8.0: the middle of the aisle
WALL_Z = float(_BOX[1])                 # -25.0: the face of the north wall
FACING = "south"
YAW = 90.0                              # what is drawn looking east looks south
_T = 4                                  # the slabs are 4 texels of slate
_GAP = 6                                # ... and stand 6 texels off the wall
FACE_Z = WALL_Z + (_GAP + _T) / 16.0    # -24.375: the slabs' face
X = (AXIS_X - 2.5, AXIS_X + 2.5)        # 5.5 .. 10.5
SLAB_Y = (1.0, 4.0)
CEILING = 6.0                           # the underside of the time room's floor, above FLOOR
BEAM = 5.0                              # the underside of the room's iron beams, above FLOOR

# --- the board (its own frame, texels) ----------------------------------------------------------------
_Y0, _Y1 = 16, 64                       # the slabs
_SLABS = {"east": (0, 24), "main": (24, 56), "west": (56, 80)}
_STAND = (8, 56, 40)                    # where every piece's entity stands: before the middle slab
_METER_Y = 54
_METERS = {"east": (12, "A", 18.0, 2.0, 110), "main": (40, "A", 6.0, 15.0, 260), "west": (68, "V", -28.0, 1.5, 150)}
#           middle along the board, letter, where the pointer rests (degrees, negative is to the right of
#           whoever reads it), how far it swings to either side, in how many ticks there and back
_KNIFE_Y = (21, 38)                     # a wing's knife switch, foot to head
_OVER_Y = (17, 29, 45)                  # the change-over switch: foot of the lower pad, of the hinge pad, head
_BUS_Y = (40, 44)                       # the bars from the racks: 4 texels high
_BUS_Z = (-2, 2)                        # ... a pair, their middle lines either side of the wing's middle
_BUS_X = 6                              # how far their ends stand out of the face
_RAIL = (64, 66)                        # the head rail
_BAR_F = (-2, 68)                       # the front bus bar over the head: its south face and its underside
_BAR_R = (-6, 72)                       # the rear one
_RISERS = (16, 64)                      # the two conduits, along the board
_RISER_X = -8                           # ... their middle line, behind the face
_RISER_Y = (58, int(CEILING * 16))


def _w(x, y, z):
    """A point of the board's own frame (texels) in the scene (blocks)."""
    return (X[1] - z / 16.0, FLOOR + y / 16.0, FACE_Z + x / 16.0)


# --- for the others (scene coordinates, blocks) -------------------------------------------------------
# The point all pieces stand at and take their light from: its cell wants level 6 to 8.
STAND = _w(*_STAND)
# Where the bars from the racks end, per wing: the middle lines of a pair of bars, west one first.
# A bar is 2 texels wide and 4 high. run() lays them from here.
BUS_IN = {side: tuple(_w(_BUS_X, (_BUS_Y[0] + _BUS_Y[1]) / 2.0, _METERS[side][0] + s) for s in sorted(_BUS_Z, reverse=True))
          for side in ("west", "east")}
BUS_Y = FLOOR + (_BUS_Y[0] + _BUS_Y[1]) / 32.0      # 2.625: the height of the bars' middle line
# Where the two conduits go through the ceiling, to the time room's cabinet.
RISERS = tuple(_w(_RISER_X, _RISER_Y[1], z) for z in sorted(_RISERS, reverse=True))
# Where the cable from the power house ends: it comes along the north wall from the west and goes in
# behind the west wing, between slab and wall.
FEED_IN = _w(-_T - _GAP / 2.0, 34, _SLABS["west"][1])
# The pivot of the battery ammeter's pointer, the piece that moves.
NEEDLE = _w(3.75, _METER_Y, _METERS["main"][0])
KEEP_CLEAR = ((X[0] - 0.25, FLOOR, WALL_Z, X[1] + 0.25, FLOOR + 4.75, FACE_Z + 0.5),                # the board
              (X[0] + 0.5, FLOOR + 2.375, FACE_Z, X[0] + 1.0, FLOOR + 2.875, FACE_Z + _BUS_X / 16.0),   # the bars' ends
              (X[1] - 1.0, FLOOR + 2.375, FACE_Z, X[1] - 0.5, FLOOR + 2.875, FACE_Z + _BUS_X / 16.0),
              ) + tuple((x - 0.25, FLOOR + 4.0, WALL_Z, x + 0.25, FLOOR + CEILING, WALL_Z + 0.375) for x, _, _ in RISERS)

BRASS_3 = K.flat("brass", 3)
BAR = dict(seed=0, faces={"u": K.flat("brass", 4), "e": K.flat("brass", 4), "d": K.flat("brass", 1)})


# ---- the models -----------------------------------------------------------------------------------------
def _panel(name):
    z0, z1 = _SLABS[name]
    w = z1 - z0
    d = K.Draw(PREFIX + "panel_" + name, at=_STAND, scale=2.0, frame=K.LEAN_EAST, step=K.TEXEL)

    def u(z):                                           # a place along the board, in the slab's picture
        return z1 - z

    mz, letter = _METERS[name][0], _METERS[name][1]
    if name == "main":
        labels = [(u(mz + 15), 31, 5), (u(mz - 10), 31, 5)]         # either side of the hinge
    else:
        labels = [(u(mz) - 4, 44, 8)]                               # under the knife switch
    face = PB.slab_picture("battery " + name, w, labels).sprite(PREFIX + "slab_" + name)
    d.box((-_T, _Y0, z0), (0, _Y1, z1), K.flat("slate", 2), skip="d", seed=0, faces={"e": face})

    # the frame: head rail, a post behind each joint that goes down to the floor as a leg, the cover
    # strip before it, a bracket to the wall, a stretcher between the legs
    d.box((-7, _RAIL[0], z0), (1, _RAIL[1], z1), PB.IRON_L)
    strip = PB.strip_picture(_Y1 - _Y0 + 2).sprite(PREFIX + "strip")
    joints = {"east": (1.5,), "main": (z0, z1), "west": (z1 - 1.5,)}[name]
    for zj in joints:
        d.box((-7, 0, zj - 1.5), (-_T, _Y1, zj + 1.5), PB.IRON)
        d.box((0, _Y0, zj - 1.5), (1, _RAIL[1], zj + 1.5), K.flat("iron", 2), seed=0, faces={"e": strip})
        d.box((-9, 0, zj - 2.5), (-2, 1.5, zj + 2.5), PB.IRON_D)
        d.box((-_T - _GAP, _RAIL[0] - 2, zj - 1), (-7, _RAIL[0], zj + 1), PB.IRON)
    d.box((-6.5, 5, z0), (-5, 7, z1), PB.IRON_D)

    # the bus bars over the head, each on its porcelain posts; the rear bar stands higher
    for (x, y), posts in ((_BAR_F, (8, 28, 52, 72)), (_BAR_R, (12, 40, 68))):
        d.box((x, y, max(z0, 2)), (x + 1, y + 2, min(z1, 78)), BRASS_3, **BAR)
        for zp in posts:
            if z0 <= zp < z1:
                d.box((x - 1, _RAIL[1], zp - 1), (x + 2, y, zp + 1), PB.PORCELAIN)

    PB.meter(d, _METER_Y, mz, letter)

    if name == "main":                                  # the change-over switch, thrown up
        y0, ym, y1 = _OVER_Y
        PB.knife(d, mz, ym, y1, 8, (-5, 5))
        d.box((0, y0, mz - 8), (1, y0 + 4, mz + 8), PB.PORCELAIN)
        d.box((1, y0 + 1, mz - 7), (3.5, y0 + 2.5, mz + 7), PB.BRASS)               # the lower jaws, empty
    else:
        PB.knife(d, mz, _KNIFE_Y[0], _KNIFE_Y[1], 6, (-3, 3))
        # where the pair of bars from the racks lands: a brass plate on the slab, the bars' ends, the
        # strap bolted over them
        d.box((0, _BUS_Y[0] - 1.5, mz - 5), (1, _BUS_Y[1] + 1.5, mz + 5), PB.BRASS)
        for s in _BUS_Z:
            d.box((1, _BUS_Y[0], mz + s - 1), (_BUS_X, _BUS_Y[1], mz + s + 1), BRASS_3, **BAR)
        d.box((2, _BUS_Y[0] - 1, mz - 4.5), (3.5, _BUS_Y[1] + 1, mz + 4.5), K.flat("brass", 2), seed=0,
              faces={"e": BRASS_3, "u": BRASS_3})
        for s in (-4, 0, 4):
            d.box((3.5, _BUS_Y[0] + 1.5, mz + s - 0.5), (4, _BUS_Y[1] - 1.5, mz + s + 0.5), K.flat("iron", 1), seed=0)
    return d


def _riser():
    """A conduit from behind the head to the ceiling: its union over the head, a clip to the wall,
    the collar under the ceiling."""
    d = K.Draw(PREFIX + "riser", at=(_STAND[0], _STAND[1], 0), scale=2.0, frame=K.LEAN_EAST, step=K.TEXEL)
    d.tube("y", (_RISER_X, 0), _RISER_Y[0], _RISER_Y[1], 1.25, PB.IRON, sides=12)
    d.tube("y", (_RISER_X, 0), _RAIL[1] + 1, _RAIL[1] + 3.5, 2.0, PB.BRASS, sides=12)
    d.box((-_T - _GAP, 80, -2.5), (_RISER_X + 0.5, 81.5, 2.5), PB.IRON_D)
    d.tube("y", (_RISER_X, 0), _RISER_Y[1] - 2, _RISER_Y[1], 2.25, PB.IRON_D, sides=12)
    return d


# The bars of the racks and what they hang from, drawn in the scene's own frame: a bar runs north
# and south and shows one side to the aisle.
_LEAN = {"east": K.LEAN_EAST, "west": K.LEAN_WEST}
_DROP = (BEAM - BUS_Y + FLOOR) * 16.0   # 38 texels from the bars' middle line up to the beam


def _bar(show):
    """One block of a bar. It is shown stretched to the length it is to have (plain copper: nothing
    on it that a stretch would spoil)."""
    lit, dim = ("e", "w") if show == "east" else ("w", "e")
    d = K.Draw(PREFIX + "bar_" + show, at=(0, 0, 8), scale=2.0, frame=_LEAN[show], step=K.TEXEL)
    d.box((-1, -2, 0), (1, 2, 16), BRASS_3, seed=0,
          faces={"u": K.flat("brass", 4), lit: K.flat("brass", 4), dim: K.flat("brass", 1), "d": K.flat("brass", 1)})
    return d


def _hanger(show):
    """What a pair of bars hangs from under a beam: a saddle and a strap round the pair, a porcelain
    insulator, an iron rod up to a plate under the beam."""
    d = K.Draw(PREFIX + "hanger_" + show, scale=2.0, frame=_LEAN[show], step=K.TEXEL)
    d.box((-4, -3, -1.5), (4, -2, 1.5), PB.BRASS)
    d.box((-4, 2, -1.5), (4, 3, 1.5), PB.BRASS)
    for x in (-4, 3):
        d.box((x, -2, -1), (x + 1, 2, 1), K.flat("iron", 1), seed=0)
    d.tube("y", (0, 0), 3, 5, 1.25, PB.PORCELAIN, sides=12)
    d.tube("y", (0, 0), 5, 7.5, 2.5, PB.PORCELAIN, sides=12)
    d.tube("y", (0, 0), 7.5, 9, 1.25, PB.PORCELAIN, sides=12)
    d.tube("y", (0, 0), 9, 11, 2.0, PB.PORCELAIN, sides=12)
    d.box((-0.5, 11, -0.5), (0.5, _DROP - 1, 0.5), PB.IRON)
    d.box((-2.5, _DROP - 1, -2.5), (2.5, _DROP, 2.5), PB.IRON_D)
    return d


@functools.lru_cache(maxsize=None)
def _drawn():
    built = [_panel(name) for name in _SLABS] + [_riser()]
    built += [f(show) for f in (_bar, _hanger) for show in _LEAN]
    return {d.m.name[len(PREFIX):]: d for d in built}


def models():
    return {d.m.name: d.m for d in _drawn().values()}


# ---- placing --------------------------------------------------------------------------------------------
def place(canvas, origin=(0, 0, 0)):
    """The board before the north wall: three slabs, their pointers, the two conduits. Returns the
    number of display entities (8). The battery ammeter's pointer swings."""
    drawn = _drawn()
    n = 0
    for name in _SLABS:
        n += K.place(canvas, drawn["panel_" + name], STAND, origin, yaw=YAW)
        mz, _, rest, sway, period = _METERS[name]
        n += K.place(canvas, PB.piece("needle"), _w(3.75, _METER_Y, mz), origin, yaw=YAW, turns=(("x", rest),))
        MK.swing(canvas, "x", sway, period, name="bboard_needle_" + name)
    for z in _RISERS:
        n += K.place(canvas, drawn["riser"], _w(_STAND[0], _STAND[1], z), origin, yaw=YAW)
    return n


def _show(x):
    return "east" if x < AXIS_X else "west"


def bus(canvas, a, b, origin=(0, 0, 0), show=None):
    """One copper bar from a to b, the ends of its middle line, which runs north and south. show:
    the side that is seen, "east" or "west"; left out, the side towards the room's axis. Returns 1."""
    if abs(a[0] - b[0]) > 1e-6 or abs(a[1] - b[1]) > 1e-6 or abs(a[2] - b[2]) < 1e-6:
        raise ValueError(f"a bar runs north and south: {a} to {b} does not")
    mid = (a[0], a[1], (a[2] + b[2]) / 2.0)
    return K.place(canvas, _drawn()["bar_" + (show or _show(a[0]))], mid, origin, stretch=(1.0, 1.0, abs(b[2] - a[2])))


def hanger(canvas, pos, origin=(0, 0, 0), show=None):
    """A hanger under a beam for a pair of bars. pos: the middle between the two bars' middle lines;
    the beam's underside is BEAM. Returns 1."""
    return K.place(canvas, _drawn()["hanger_" + (show or _show(pos[0]))], pos, origin)


def run(canvas, side, south, hangers=(), origin=(0, 0, 0)):
    """The pair of bars of one wing ("west" or "east") from the board's clamp straight south to
    z = south, with a hanger at each z of `hangers`. The bars are laid in lengths that end at the
    hangers, so that each length takes the light of where it hangs. Returns the number of display
    entities."""
    pair = BUS_IN[side]
    stops = sorted({pair[0][2], float(south)} | {float(z) for z in hangers if pair[0][2] < z < south})
    n = 0
    for x, y, _ in pair:
        for z0, z1 in zip(stops, stops[1:]):
            n += bus(canvas, (x, y, z0), (x, y, z1), origin)
    middle = (pair[0][0] + pair[1][0]) / 2.0
    for z in hangers:
        n += hanger(canvas, (middle, pair[0][1], float(z)), origin)
    return n
