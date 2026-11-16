"""The astrograph room (card plan/packages/interiors/astroroom.md): the inside of the small dome on
the south end pavilion. The star is the astrograph (machines/astro), which fills the middle of a
room five blocks across and looks out of the slit over the door; this module makes the room a place
somebody works in tonight.

The room (main/smalldome, c328): feet at 18; the floor is the five by five inside the stone body
less its four corners; the door is in the west wall on the axis (9, 30), a window in each of the
other three; the walls are two blocks high, their head a ledge all round at 20. The instrument
leaves eight cells clear from the floor up (the card has the numbers): the three behind the door
and the two niches, north and south, each three cells wide and one deep. So:

  south niche   where the work is done, and the one place the instrument leaves in full view of the
                door: the writing desk in the east two cells. At its east end the box of tonight's
                plates stands open, its lid up, under the red lamp on the niche's end wall: there
                the holders are loaded. Beside it the exposure log lies open under the desk lamp; a
                stool before it. The driving clock's governor (_astrodrive, c356) hangs on the wall
                in the west cell
  north niche   where the plates are kept: a low cabinet of plate drawers along the whole wall,
                under the window; on it a box of fresh plates and two plate holders. One sees it
                in glimpses, under the tube and past the counterweights
  east wall     south of the camera back the observing steps: three treads on wheels, a rail to
                hold on to, for the eye at the guiding telescope
  by the door   two plate boxes shut and stacked, to go down to the plate vault in the morning

The floor is relaid in boards, with the head of the instrument's pier flush in it under the column.

Light. Two lamps and no more (the card): the desk lamp and the red lamp, whose glass looks west
along the niche and stands behind the south window's jamb. Each offers a source of its own, and two
low ones without a fixture fill what the lamps leave: the north niche and the east wall (LIGHTS).
They are no brighter than it takes for a visitor to see where he puts his feet (5 where one can
stand), and at most 4 of it passes a window.

What is whose: the shell, the slit and the door are main/smalldome's; the astrograph is machines';
desk, stool and the shut plate boxes are props/furniture's, the lamp props/lamps', the log
props/paper's. The room's own models (names "int_astroroom_...") are the cabinet, the open plate
box (props/furniture's plate box with its lid up, the same wood and brass), the plate holder, the
red lamp and the steps. Two parts of the room are written by others, a file each, and called from
here: the driving clock on the south wall (_astrodrive, c356) and, from the head of the wall up,
the iron inside the shell with the crank that turns the dome (_astroshell, c328).

Coordinates are the skeleton's. build_astroroom() dresses the room where it stands in the building;
the test scene (build/scenes/obs_int_astroroom) stands the small dome on a stand-in of the roof.
build() is what the master scene calls; it places nothing while MOVED_IN is off.
"""
import functools

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..main import smalldome
from ..props import _kit as K
from ..props import furniture, lamps, paper
from . import _astrodrive, _astroshell

ORDER = 80              # a room that moves into the shell (INTERFACE 3)
MOVED_IN = True         # the master scene dresses the room (fast lane: a card's switch is turned on with its delivery)
NAME = "interiors/astroroom"
PREFIX = "int_astroroom_"
PX = 1 / 16.0
BUDGET = 70             # display entities of this module (cr4: 120 for the room, 35 the inner shell's, 15 the drive's)
ROOM_BUDGET = 120       # the card's

# ---- the room (cells) ---------------------------------------------------------------------------
FEET = S.SMALL_DRUM_BASE                # 18
FLOOR_Y = FEET - 1                      # 17: the floor block
CX, CZ = smalldome.CX, smalldome.CZ     # 12, 30: the column of the dome's axis
ROOM = smalldome.ROOM                   # the floor's 21 columns
PAD = frozenset((x, z) for x in (CX - 1, CX) for z in (CZ - 1, CZ))     # under the column's foot
NORTH, SOUTH, EAST = float(CZ - 2), float(CZ + 3), float(CX + 3)        # 28.0, 33.0, 15.0: wall faces
NICHE_X = (CX - 1, CX + 1)              # 11..13: the cells of either niche
NICHE_EAST = float(NICHE_X[1] + 1)      # 14.0: the face that ends a niche on the east

BOARDS, STONE = B.FLOOR_WOOD.block, B.ASHLAR_FINE.block

# ---- the plan (blocks) ----------------------------------------------------------------------------
CABINET = (S.mid(CX), NORTH)                            # (12.5, 28.0): the middle of the cabinet's back
DESK = (float(NICHE_X[1]), SOUTH - 0.5)                 # (13.0, 32.5): the middle of the desk's foot
DESK_YAW = K.FACING["north"]                            # one sits on its north side
DESK_CELLS = (NICHE_X[1] - 1, NICHE_X[1])               # 12, 13
STOOL = (DESK[0] - 0.5, DESK[1] - 0.78)                  # pushed in at the desk's west end, clear of the hour circle
STEPS = (EAST - 0.5, CZ + 1.56)                         # (14.5, 31.56): against the east wall, south of the camera
BOXES = (CX - 1.58, CZ - 0.6)                           # (10.42, 29.4): the shut boxes, left of the door
BOX_ON_DESK = (-8.5, 1.5)                               # the open plate box, in the desk's frame (on_desk)
RED = (NICHE_EAST, FEET + 1.62, SOUTH - 0.5 - 3.0 / 16.0)       # the red lamp: on the niche's end wall, over the box

# ---- light: what the room offers sky/lights. Every place one can get to wants 5 at the feet or the
#      head (the closing list of 11-16: the floor, the tops of desk and cabinet, the head of the wall);
#      each level is the lowest that does it. (what, the cell, the level)
LIGHTS = (
    ("desk lamp", (NICHE_X[1], FEET, CZ + 1), 7),           # (13, 18, 31): a cell north of the desk
    ("red lamp", (NICHE_X[1], FEET + 2, CZ + 2), 8),        # (13, 20, 32): the cell over the lamp's flue
    ("fill north", (CX, FEET + 2, CZ - 2), 7),              # (12, 20, 28): over the cabinet; no fixture
    ("fill east", (CX + 2, FEET + 2, CZ), 7),               # (14, 20, 30): over the camera's back; no fixture
)

# ---- materials: props/furniture's wood and brass, so the pieces are of one make -------------------
WOOD = P.mat("dark_wood")
WOOD_L = P.mat("dark_wood", base=3)
WOOD_D = P.mat("dark_wood", base=1)
SHADOW = K.flat("dark_wood", 0)
BRASS, BRASS_D, IRON, IRON_D = K.BRASS, K.BRASS_D, K.IRON, K.IRON_D
CARD = K.flat("cream", 1)                   # a drawer's label
SLEEVE, KRAFT = K.flat("cream", 2), K.flat("old_copper", 2)     # a plate in its paper sleeve, edge on
FELT = K.flat("enamel", 0)                  # the lining of a plate box's lid
RUBY = tuple(K.flat("signal", step) for step in (1, 2))         # the red lamp's glass, brighter in the middle
LIT = dict(emit=15, shade=False)

# ---- the room's own models ------------------------------------------------------------------------
CAB_W, CAB_D, CAB_H = 44.0, 12.0, 16.0      # the cabinet: along the wall, off it, high (its top is the window's sill)
BAYS = 3
DRAWER = (12.0, 5.0)                        # a drawer front: wide, high


def _cabinet():
    """The plate cabinet: a low chest of six drawers the whole length of the niche, each with its
    label over its pull. Anchor: on the wall at floor level, the middle of its back."""
    m = M.Model(PREFIX + "cabinet")
    hw = CAB_W / 2.0
    m.box((-hw + 1.0, 0.0, 0.0), (hw - 1.0, 2.0, CAB_D - 1.0), WOOD_D, grain="x", skip="n")
    m.box((-hw, 2.0, 0.0), (hw, CAB_H - 2.0, CAB_D), WOOD, grain="y", skip="n")
    m.box((-hw - 0.5, CAB_H - 2.0, 0.0), (hw + 0.5, CAB_H, CAB_D + 0.5), WOOD_D, grain="x", skip="n")
    w, h = DRAWER
    for bay in range(BAYS):
        x0 = -hw + 2.0 + (w + 2.0) * bay
        for y0 in (3.0, 9.0):
            m.box((x0, y0, CAB_D), (x0 + w, y0 + h, CAB_D + 0.5), WOOD_L, grain="x", skip="n")
            m.box((x0 + 5.0, y0 + 1.0, CAB_D + 0.5), (x0 + 7.0, y0 + 2.0, CAB_D + 1.25), BRASS_D, skip="n")
            m.box((x0 + 3.0, y0 + 3.0, CAB_D + 0.5), (x0 + 9.0, y0 + 4.0, CAB_D + 0.75), CARD, skip="n")
    return m


def _plate_box_open():
    """props/furniture's plate box with its lid up: the lid stands on its hinges behind the box,
    its lining towards the room; in the box the night's plates in their paper sleeves, on edge,
    and room for three more. Anchor: the middle of the box's underside; the lid is behind."""
    m = M.Model(PREFIX + "plate_box_open")
    m.box((-6.0, 0.0, -4.0), (6.0, 1.0, 4.0), WOOD, grain="x")
    for z0 in (-4.0, 3.0):
        m.box((-6.0, 1.0, z0), (6.0, 6.0, z0 + 1.0), WOOD, grain="x")
    for x0 in (-6.0, 5.0):
        m.box((x0, 1.0, -3.0), (x0 + 1.0, 6.0, 3.0), WOOD, grain="z")
    m.box((-5.0, 1.0, -3.0), (5.0, 1.5, 3.0), SHADOW, skip="d")
    for i, top in enumerate((6.5, 6.5, 6.0, 6.5, 6.5, 6.5, 5.5)):
        x = -4.25 + i
        m.box((x, 1.5, -2.5), (x + 0.5, top, 2.5), KRAFT if i in (2, 5) else SLEEVE, skip="d")
    for x0 in (-6.5, 5.0):                                          # dull brass on the corners, as on the shut box
        for z0 in (-4.5, 3.0):
            m.box((x0, 0.0, z0), (x0 + 1.5, 1.5, z0 + 1.5), BRASS_D)
        for y0 in (6.0, 13.25):
            m.box((x0, y0, -7.5), (x0 + 1.5, y0 + 1.5, -6.0), BRASS_D)
    m.box((-1.0, 3.5, 4.0), (1.0, 6.0, 4.5), BRASS, skip="n")       # the catch, hanging
    # the lid: a tray three texels deep, on end
    m.box((-6.25, 6.0, -7.25), (6.25, 14.5, -6.5), WOOD_D, grain="x")
    for x0 in (-6.25, 5.5):
        m.box((x0, 6.0, -6.5), (x0 + 0.75, 14.5, -4.25), WOOD_D, grain="y", skip="n")
    for y0 in (6.0, 13.75):
        m.box((-5.5, y0, -6.5), (5.5, y0 + 0.75, -4.25), WOOD_D, grain="x", skip="n")
    m.box((-5.5, 6.75, -6.5), (5.5, 13.75, -6.25), FELT, skip="n")
    return m


HOLDER_FACE = Sprite("astroroom_holder", ["b.....b"] + [".sssss."] * 7 + ["b.....b"],
                     {"b": P.RAMPS["brass"][2], "s": P.RAMPS["iron"][1]}, back=WOOD_D)


def _holder():
    """A plate holder lying flat: a thin frame of dark wood with brass corners, the dark slide
    shut in it, the slide's brass tab at one end. Anchor: the middle of its underside."""
    m = M.Model(PREFIX + "holder")
    m.box((-3.5, 0.0, -4.5), (3.5, 1.0, 4.5), WOOD_D, grain="z", skip="d", faces={"u": HOLDER_FACE})
    m.box((-1.5, 0.25, 4.5), (1.5, 0.75, 5.5), BRASS, skip="n")
    return m


def _safelight():
    """The red lamp: a small iron lamp house with a pane of ruby glass, a hood and a short flue; the
    plate vault's safelight a size down. It does not blink. Anchor: on the wall, the middle of its
    back."""
    m = M.Model(PREFIX + "safelight")
    m.box((-3.0, -2.5, 0.0), (3.0, 2.5, 3.0), IRON_D, skip="n")
    m.box((-3.5, 2.5, 0.0), (3.5, 3.5, 4.0), IRON, skip="n")
    m.box((-1.0, 3.5, 0.5), (1.0, 5.5, 2.5), IRON_D, skip="d")
    m.box((-2.0, -1.5, 3.0), (2.0, 1.5, 3.4), RUBY[0], skip="n", **LIT)
    m.box((-1.0, -0.5, 3.4), (1.0, 0.5, 3.6), RUBY[1], skip="n", **LIT)
    return m


TREADS = ((3.0, 7.0, 4.0), (-1.0, 3.0, 8.0), (-7.0, -1.0, 12.0))    # from, to, the top of each tread
RAIL_Y = 28.0


def _steps():
    """The observing steps: three treads between two stepped cheeks, on four iron wheels; at the
    back of the top tread two posts and a rail to hold on to. Anchor: the middle of its foot; the
    lowest tread is its front."""
    m = M.Model(PREFIX + "steps")
    for z0, z1, top in TREADS:
        for x0 in (-6.0, 5.0):
            m.box((x0, 1.0, z0), (x0 + 1.0, top - 1.0, z1), WOOD, grain="y")
        m.box((-6.5, top - 1.0, z0 - 0.5), (6.5, top, z1 + 0.5), WOOD_L, grain="x")
    m.box((-5.0, 8.0, -7.0), (5.0, 11.0, -6.0), WOOD_D, grain="x")          # the tie under the top tread
    m.box((-5.0, 1.0, 6.0), (5.0, 3.0, 7.0), WOOD_D, grain="x")             # and the one under the lowest
    for x0 in (-6.0, 5.0):
        m.box((x0, 12.0, -7.0), (x0 + 1.0, RAIL_Y - 1.0, -6.0), WOOD_D, grain="y", skip="d")
    m.box((-6.5, RAIL_Y - 1.0, -7.5), (6.5, RAIL_Y, -5.5), WOOD, grain="x")
    for x0 in (-7.0, 6.0):
        for z in (-5.0, 5.0):
            m.tube("x", (1.25, z), x0, x0 + 1.0, 1.25, IRON_D, sides=8)
    return m


@functools.lru_cache(maxsize=None)
def _models():
    return {m.name: m for m in (_cabinet(), _plate_box_open(), _holder(), _safelight(), _steps())}


def models():
    return {**_models(), **_astrodrive.models(), **_astroshell.models()}


# ---- building -----------------------------------------------------------------------------------
def on_desk(x, z):
    """A point on the desk top: texels from the desk's middle in the desk's own frame (x to the
    sitter's right, z towards the sitter)."""
    dx, _, dz = K.turn(DESK_YAW, (x * PX, 0.0, z * PX))
    return (DESK[0] + dx, FEET + furniture.TOP["writing_desk"], DESK[1] + dz)


def build_astroroom(canvas, origin=(0, 0, 0)):
    """Dress the room; returns the number of display entities placed."""
    ox, oy, oz = origin
    own = _models()
    n = 0

    def put(x, y, z, state):
        canvas.set(ox + x, oy + y, oz + z, state)

    def piece(name, pos, **how):
        return K.put(canvas, own[PREFIX + name], pos, origin=origin, **how)

    # the floor: boards, and the head of the pier flush in them under the column
    for x, z in ROOM:
        put(x, FLOOR_Y, z, STONE if (x, z) in PAD else BOARDS)

    # ---- the north niche: the cabinet, on it a box of fresh plates and two holders ------------------
    top = FEET + CAB_H * PX
    n += piece("cabinet", (CABINET[0], float(FEET), CABINET[1]), mount="wall", facing="south")
    for x in range(NICHE_X[0], NICHE_X[1] + 1):                     # a model stops nobody
        put(x, FEET, CZ - 2, B.BARRIER)
    n += furniture.place(canvas, "plate_box", (NICHE_EAST - 0.62, top, NORTH + 0.4), yaw=-6.0, origin=origin)
    n += piece("holder", (CABINET[0] - 0.15, top, NORTH + 0.42), yaw=4.0)
    n += piece("holder", (CABINET[0] - 0.1, top + PX, NORTH + 0.45), yaw=-12.0)

    # ---- the south niche: the desk; tonight's box open under the red lamp; the log under the desk
    #      lamp; the stool; the driving clock ---------------------------------------------------------
    n += furniture.place(canvas, "writing_desk", (DESK[0], float(FEET), DESK[1]), yaw=DESK_YAW, origin=origin)
    for x in DESK_CELLS:
        put(x, FEET, CZ + 2, B.BARRIER)
    n += furniture.place(canvas, "stool", (STOOL[0], float(FEET), STOOL[1]), origin=origin)
    n += piece("plate_box_open", on_desk(*BOX_ON_DESK), yaw=DESK_YAW)
    n += piece("safelight", RED, mount="wall", facing="west")
    n += lamps.place(canvas, "desk_green", on_desk(4.5, -3.25), yaw=DESK_YAW + 20.0, origin=origin, light=False)
    for what, (x, y, z), level in LIGHTS:
        K.offer_lights(canvas, [((ox + x, oy + y, oz + z), level)], f"{NAME}:{what}")
    n += paper.place(canvas, "logbook", on_desk(3.75, 3.4), yaw=DESK_YAW - 4.0, origin=origin)
    n += _astrodrive.place(canvas, origin)

    # ---- overhead: the ring the dome turns on, its rack and crank, the ribs under the plates --------
    n += _astroshell.place(canvas, origin)

    # ---- the observing steps by the camera, the boxes that go down in the morning -------------------
    n += piece("steps", (STEPS[0], float(FEET), STEPS[1]), facing="west")
    n += furniture.place(canvas, "plate_box", (BOXES[0], float(FEET), BOXES[1]), yaw=96.0, origin=origin)
    n += furniture.place(canvas, "plate_box", (BOXES[0] + 0.02, FEET + furniture.TOP["plate_box"] + furniture.STRAP,
                                               BOXES[1] - 0.02), yaw=84.0, origin=origin)
    return n


def check():
    """What can be told without a picture; returns the findings as lines (none is good)."""
    from artkit.canvas import Canvas

    out = []
    for name, m in _models().items():
        lo, hi = m.bounds()
        if any((hi[i] - lo[i]) * m.px > 48.0 for i in range(3)):
            out.append(f"{name}: wider than three blocks")
    c = Canvas()
    smalldome.build(c)
    whole = build_astroroom(c)
    n = whole - _astrodrive.place(Canvas()) - _astroshell.place(Canvas())
    if n > BUDGET:
        out.append(f"{n} display entities, the budget is {BUDGET}")
    if whole > ROOM_BUDGET:
        out.append(f"{whole} display entities in the room, the card allows {ROOM_BUDGET}")
    for x, z in ROOM:
        if not c.has(x, FLOOR_Y, z):
            out.append(f"floor: nothing at ({x}, {z})")
    return out


def build(canvas, origin=(0, 0, 0)):
    """What the master scene calls: the room, once it has moved in."""
    if not MOVED_IN:
        return 0
    return build_astroroom(canvas, origin)
