"""The plate vault and its darkroom (card plan/packages/interiors/platevault.md): the ground floor of
the south wing, right under the chart room. The glass plates the astrograph of the small dome takes
every night are developed and dried here, entered in the register, shelved in their paper sleeves,
and sent up to the light table of the chart room by a hand lift.

The room is 12 wide (x 2..13), 19 long (z 7..25) and 6 high (feet at 0, the ceiling block on 6 is
the chart room's floor). The door from the star hall is one cell wide and two high, in the cross
wall on z 6 at x 7 (hall, c348: the piers of the gallery stand before x 8; shell, c325: as high as
the door of the battery room across the hall), so the room's axis is the middle of that cell,
x 7.5. From north to south:

  entry (z 7..8)       the hand lift in the north-west corner (2, 7), under the cased riser of the
                       chart room (chart, c350), and the register desk beside it
  the stacks (z 9..20) a nave three wide on the axis (x 6..8) between two island stacks (x 5 and
                       x 9), a side aisle beyond each, and a stack on either long wall (x 2 and
                       x 13). Every stack rises to the ceiling: twelve shelves of plates in their
                       sleeves, edge-on. Iron beams cross the nave and the aisles on the pilaster
                       rows and carry the lamps
  cross aisle (z 21)   joins the aisles before the darkroom wall
  darkroom (z 23..25)  the last bay, lined with slate, behind a slate wall on the pilaster row z 22
                       with an arch three wide on the axis. Its one light is the safelight over the
                       sink on the south wall: the red point the nave ends on, seen from the door

The way of a plate reads from south to north: the sink and the trays under the red lamp, the
stacks, the register desk, the lift.

Light: three shaded pendants over the nave, dimmer towards the darkroom, one over each side aisle,
the desk lamp, and the safelight (the lowest step of the third rank). Nothing lights a window of
the base storey: the wall stacks and the darkroom's lining are whole blocks and stand before every
one of them, so the storey stays the dark band it is from outside.

A stack is a core of wood blocks (it stops who walks) with a face of shelves on each long side: a
model three blocks wide and high, two tiers of them. Both tiers take their light from the cells
people walk in (the lower from eye height, the upper from the floor, which is two steps dimmer),
so the shelves fade towards the ceiling as they do under a shaded lamp.

Coordinates are the skeleton's. build_platevault() dresses the room where it stands in the building;
the box test scene (build/scenes/obs_int_platevault) stands a stand-in of the shell around it.
build() is what the master scene calls; it places nothing while MOVED_IN is off.
"""
import functools
import random

import numpy as np

from artkit import models as M
from artkit.blocks import st

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..main import _plan as MP
from ..main import shell
from ..motion import _kit as MK
from ..props import _kit as K
from ..props import furniture, lamps, paper, signs

ORDER = 80              # a room that moves into the shell (INTERFACE 3)
MOVED_IN = False        # the master scene dresses the room; turned on with the delivery
NAME = "interiors/platevault"
PREFIX = "int_vault_"
PX = 1 / 16.0

# ---- the room (cells) ---------------------------------------------------------------------------
_ABOVE = shell.ROOMS["chart room"]
X0, Z0, X1, Z1 = _ABOVE["box"]      # 2, 7, 13, 25: the clear inside, the same columns as the chart room above
FEET = S.GROUND                     # 0
FLOOR_Y = FEET - 1                  # -1: the floor block
CEIL_Y = _ABOVE["feet"] - 1         # 6: the chart room's floor block is this room's ceiling
TOP = CEIL_Y - 1                    # 5: the highest clear row, and the row of the beams
HALL_DOOR = (7, Z0 - 1)             # (7, 6): the wall cell of the door to the star hall (hall reads this name)
DOOR_Y = (FEET, FEET + 1)           # the doorway's rows: two high, as the battery room's across the hall
AXIS_X = S.mid(HALL_DOOR[0])        # 7.5: the room's axis runs through the door
LIFT = (X0, Z0)                     # (2, 7): the hand lift's shaft, under the chart room's cased riser
PIER_Z = tuple(z for z in range(Z0, Z1 + 1) if MP.on_pilaster(z))      # 10, 14, 18, 22: the beams' rows
EAST_BAYS = tuple(b for b in range(1, S.N_BAYS + 1)
                  if set(MP.window_rows(b)) <= set(range(Z0, Z1 + 1)))                # 11..15
WEST_BAYS = tuple(b for b in EAST_BAYS
                  if all(abs(z - S.DOME_CENTRE[1]) > MP.WEST_BLIND_Z for z in MP.window_rows(b)))   # 13..15
WINDOW_Y = MP.BASE_WINDOW           # (3, 4): the small windows of the base storey

# ---- the plan (cells) ---------------------------------------------------------------------------
WALL_Z = PIER_Z[-1]                 # 22: the darkroom's wall, on the last pilaster row
DARK_Z = (WALL_Z + 1, Z1)           # 23..25: the darkroom, the last bay
DARK_X = (X0 + 1, X1 - 1)           # 3..12: its clear width inside the slate lining
ARCH_X = (HALL_DOOR[0] - 1, HALL_DOOR[0] + 1)      # 6..8: the arch in the darkroom's wall
ARCH_Y = FEET + 2                   # the row of the arch's head
NAVE_X = ARCH_X                     # 6..8: the nave, as wide as the arch
FACE_CELLS = 3                      # a face of shelves is three blocks wide and high
ISLAND_X = (NAVE_X[0] - 1, NAVE_X[1] + 1)           # 5 and 9: the two island stacks
ISLAND_Z = (Z0 + 2, WALL_Z - 2)     # 9..20
EAST_STACK_Z = (Z0, WALL_Z - 1)     # 7..21: the stack on the east wall, before the windows of bays 11..14
WEST_STACK_Z = (Z0 + 3, WALL_Z - 1)     # 10..21: the one on the west wall; the lift and the desk stand north of it
BENCH_Z = Z1                        # 25: the sink and the benches, on the south wall
SINK_X = ARCH_X                     # 6..8: the stone sink, on the axis

# ---- light: what the room asks of the light line ------------------------------------------------
LAMPS = "b"                         # the shaded lamp of props/lamps: its glow stays under it
NAVE_LAMPS = ((PIER_Z[0], 11), (PIER_Z[1], 10), (PIER_Z[2], 8))     # (the beam's row, level): dimmer towards the darkroom
AISLE_LAMPS = ((float(X0 + 2), PIER_Z[1], 9), (X1 - 1.5, PIER_Z[1], 9))     # (x, the beam's row, level)
ASK_CHECK = 7                       # the checking table's glass
ASK_DARK = 5                        # the safelight: the lowest step of the third rank (the card)
SAFELIGHT_Y = FEET + 2.3            # its middle: under the head of the arch as the door of the hall sees it
PANEL_T = 3 * PX                    # a panel of the wainscot, off its wall

# ---- the lift -------------------------------------------------------------------------------------
LIFT_REST = FEET + 1.0              # the car's floor when it stands at the hatch
LIFT_TRAVEL = float(CEIL_Y - LIFT_REST)     # up into the floor of the chart room
LIFT_MOVES = ((100, LIFT_TRAVEL, 100), (400, 0.0, 100))    # (tick it sets off, blocks from rest, ticks it takes)
LIFT_CYCLE = 600                    # half a minute: up, a wait at the top, down, a wait at the hatch
DRIP = 50                           # ticks between two drops of the tap

# ---- blocks ---------------------------------------------------------------------------------------
FLOOR = B.FLOOR_WOOD.block
WET_FLOOR = B.SLATE_SMOOTH.block
BEAM = B.IRON_RIVETED.block
CORE = B.DARK_WOOD.block
SLATE_FOOT, SLATE_WALL, SLATE_HEAD = B.SLATE_BRICK.block, B.SLATE_TILE.block, B.SLATE_SMOOTH.block

# ---- materials ------------------------------------------------------------------------------------
WOOD = P.mat("dark_wood")
WOOD_D = P.mat("dark_wood", base=1)
SHADOW = K.flat("dark_wood", 0)             # the inside of a stack
PAPER = K.flat("cream", 1)                  # a sleeve's top and side
LABEL = K.flat("cream", 3)
KRAFT = K.flat("old_copper", 2)
ROPE = K.flat("old_copper", 3)
PORCELAIN = P.mat("porcelain")
BATH = K.flat("iron", 1)                    # what stands in a tray: dark in this light
BOTTLE = K.flat("old_copper", 0)            # brown glass
BRASS, BRASS_D, IRON, IRON_D = K.BRASS, K.BRASS_D, K.IRON, K.IRON_D
LIT = dict(emit=15, shade=False)
OPAL = P.mat("opal")                        # lit opal glass, as the chart room's light table has it
CLOTH = P.mat("enamel_cloth")               # the black-out curtain
RUBY = tuple(K.flat("signal", step) for step in (1, 2, 3))     # the safelight's glass, brighter towards its middle


def slate(y):
    """The slate of the darkroom's wall and lining, in three courses."""
    return SLATE_FOOT if y <= S.PLINTH[1] else SLATE_HEAD if y >= TOP else SLATE_WALL


def panel(side):
    """A panel of the wainscot standing on that side of its cell."""
    back = {"north": "south", "south": "north", "west": "east", "east": "west"}[side]
    return st(B.WAINSCOT, facing=back, half="bottom", open="true")      # it stands on the side it turns its back to


class _Sleeves:
    """The picture of a shelf of plates seen from the aisle: the edges of their paper sleeves, a
    texel each, batch by batch in the same paper, here and there a sleeve that stands lower and
    the coloured tab of an index card. It stands in for a material on the front of one box
    (artkit.models asks a material only for its name and paint())."""

    PAPERS = (("cream", 3, 1), ("cream", 2, 0), ("cream", 3, 1), ("old_copper", 4, 2), ("old_copper", 3, 1))
    TABS = (("enamel", 3), ("signal", 1), ("brass", 4), ("verdigris", 2))

    def __init__(self, name):
        self.name = name

    def paint(self, w, h, grain="u", seed=0):
        rnd = random.Random(f"{self.name}:{w}:{h}:{seed}")
        out = np.empty((h, w, 4), dtype=np.uint8)
        out[..., :3] = P.colour("dark_wood", 0)
        out[..., 3] = 255
        x = 0
        while x < w:
            batch = 2 * rnd.randint(2, 5)               # sleeves of one batch: the same paper
            ramp, light, dark = rnd.choice(self.PAPERS)
            for i in range(x, min(w, x + batch)):
                edge = (i - x) % 2 == 0                 # a sleeve is two texels: its edge, and the side in shadow
                top = 0 if edge and rnd.random() < 0.85 else 1
                out[top:, i, :3] = P.colour(ramp, light if edge else dark)
            if rnd.random() < 0.45:                     # the batch's index card, its tab over the sleeves
                out[:, x, :3] = P.colour(*rnd.choice(self.TABS))
            x += batch
        return out


# ---- the room's own models: the faces of the stacks -----------------------------------------------
# A face is 48 texels wide and high and 3 deep: uprights on the lines of the cells, a board every
# half block, and in each pigeonhole (14 wide, 7 high) a run of sleeves. Its uprights at the two
# edges are half ones: with the next face's they make one.
FACE = 16.0 * FACE_CELLS
ROW = 8.0
DEPTH = 3.0
HOLES = ((-FACE / 2 + 1, -9.0), (-7.0, 7.0), (9.0, FACE / 2 - 1))
LOW, HIGH = 40.0, -40.0     # where a face's anchor is, from its foot: the lower tier's at eye height, the upper
#                             tier's as far below its foot, in the row of cells over the floor


def _face(name, seed, anchor_y):
    m = M.Model(PREFIX + name, anchor=(0.0, anchor_y, 0.0))
    rnd = random.Random(seed)
    sleeves = _Sleeves(f"vault_sleeves_{seed}")
    half = FACE / 2.0
    m.box((-half, 0, 0), (half, FACE, 0.5), SHADOW, skip="n")
    for a, b in ((-half, -half + 1), (-9.0, -7.0), (7.0, 9.0), (half - 1, half)):
        m.box((a, 0, 0.5), (b, FACE, DEPTH + 0.25), WOOD, grain="y", skip="n")
    i = 0
    for k in range(int(FACE / ROW)):
        y = k * ROW
        m.box((-half + 1, y, 0.5), (half - 1, y + 1, DEPTH), WOOD_D if k == 0 else WOOD, grain="x", skip="n")
        for x0, x1 in HOLES:
            i += 1
            roll = rnd.random()
            if roll < 0.06:
                continue                                        # an empty pigeonhole
            height = rnd.choice((5.0, 6.0, 6.0, 6.0))
            width = x1 - x0 if roll < 0.78 else float(rnd.randint(6, 11))
            a = x0 if rnd.random() < 0.7 else x1 - width
            m.box((a, y + 1, 0.5), (a + width, y + 1 + height, DEPTH - 0.5), PAPER, skip="nd",
                  faces={"s": sleeves}, seed=seed * 100 + i)
            if rnd.random() < 0.8:
                c = (x0 + x1) / 2.0
                m.box((c - 1.5, y, DEPTH), (c + 1.5, y + 1, DEPTH + 0.2), LABEL, skip="n")
    return m


FACES = (("face_a", 11), ("face_b", 23), ("face_c", 37))


# ---- the room's own models: the darkroom and the lift --------------------------------------------
def _safelight():
    """The darkroom's lamp: an iron lamp house with a pane of ruby glass, a hood and a short flue.
    Anchor: on the wall, the middle of its back."""
    m = M.Model(PREFIX + "safelight")
    m.box((-4, -3.5, 0), (4, 3.5, 4), IRON_D)
    m.box((-4.5, 3.5, 0), (4.5, 4.5, 5), IRON)
    m.box((-1, 4.5, 1), (1, 7, 3), IRON_D)
    m.box((-3, -2.5, 4), (3, 2.5, 4.5), RUBY[0], skip="n", **LIT)
    m.box((-2, -1.5, 4.5), (2, 1.5, 4.7), RUBY[1], skip="n", **LIT)
    m.box((-1, -0.5, 4.7), (1, 0.5, 4.9), RUBY[2], skip="n", **LIT)
    return m


def _tray():
    """A developing tray of porcelain with its bath. Anchor: the middle of its underside."""
    m = M.Model(PREFIX + "tray")
    m.box((-6, 0, -4.5), (6, 0.5, 4.5), PORCELAIN)
    m.box((-6, 0.5, -4.5), (6, 2, -3.5), PORCELAIN)
    m.box((-6, 0.5, 3.5), (6, 2, 4.5), PORCELAIN)
    m.box((-6, 0.5, -3.5), (-5, 2, 3.5), PORCELAIN)
    m.box((5, 0.5, -3.5), (6, 2, 3.5), PORCELAIN)
    m.box((-5, 0.5, -3.5), (5, 1.5, 3.5), BATH, skip="d")
    return m


def _bottles():
    """Four bottles of brown glass, labelled, side by side. Anchor: the middle of their foot."""
    m = M.Model(PREFIX + "bottles")
    for i, (x, tall) in enumerate(((-6.0, 7.0), (-2.0, 8.0), (2.0, 6.0), (6.0, 8.0))):
        m.box((x - 1.5, 0, -1.5), (x + 1.5, tall, 1.5), BOTTLE)
        m.box((x - 0.5, tall, -0.5), (x + 0.5, tall + 2, 0.5), BOTTLE)
        m.box((x - 1, tall + 2, -1), (x + 1, tall + 2.5, 1), KRAFT)
        m.box((x - 1.5, 2, -1.75), (x + 1.5, tall - 2, -1.5), LABEL, skip="s")
    return m


def _tap():
    """The sink's tap: a brass pipe out of the wall with a cross handle, its mouth turned down.
    Anchor: on the wall, the middle of its rose; the mouth is TAP_MOUTH from it."""
    m = M.Model(PREFIX + "tap")
    m.box((-1.5, -1.5, 0), (1.5, 1.5, 0.5), BRASS_D)
    m.box((-0.5, -0.5, 0.5), (0.5, 0.5, 6.5), BRASS, grain="z")
    m.box((-0.5, -3, 5.5), (0.5, -0.5, 6.5), BRASS, grain="y")
    m.box((-2, 0.5, 2.5), (2, 1, 3.5), BRASS_D)
    m.box((-0.5, 0.5, 1), (0.5, 1, 5), BRASS_D)
    return m


TAP_MOUTH = (0.0, -3.0 * PX, 6.0 * PX)


def _car():
    """The hand lift's car: an open box of wood on an iron bail, a batch of plates in their sleeves
    standing in it. Anchor: the middle of its underside."""
    m = M.Model(PREFIX + "lift_car")
    sleeves = _Sleeves("vault_sleeves_car")
    m.box((-6, 0, -6), (6, 1, 6), WOOD_D, grain="x")
    m.box((-6, 1, -6), (-5, 5, 6), WOOD, grain="z")
    m.box((5, 1, -6), (6, 5, 6), WOOD, grain="z")
    m.box((-5, 1, -6), (5, 5, -5), WOOD, grain="x")
    m.box((-5, 1, 5), (5, 3, 6), WOOD, grain="x")
    m.box((-4, 1, -4), (4, 7, 3), PAPER, skip="d", faces={"s": sleeves, "n": sleeves})
    m.box((-6.5, 3, -0.5), (-6, 12, 0.5), IRON_D)
    m.box((6, 3, -0.5), (6.5, 12, 0.5), IRON_D)
    m.box((-6.5, 12, -0.5), (6.5, 12.5, 0.5), IRON_D)
    return m


CAR_TOP = 12.5 * PX
ROPE_L = 48.0 * PX


def _rope():
    """A length of the lift's rope. Anchor: its lower end."""
    m = M.Model(PREFIX + "lift_rope")
    m.box((-0.5, 0, -0.5), (0.5, 48, 0.5), ROPE, grain="y")
    return m


def _guides():
    """A length of the two iron rods the car runs between. Anchor: the middle of its foot."""
    m = M.Model(PREFIX + "lift_guides")
    for x in (-7.5, 7.0):
        m.box((x, 0, -0.5), (x + 0.5, 48, 0.5), IRON, grain="y")
    return m


CHECK_TOP = 13.25 * PX


def _checker():
    """The checking table: a lamp box of dark wood on four legs with a pane of lit opal glass in its
    top, the small sister of the chart room's light table. Anchor: the middle of its foot."""
    m = M.Model(PREFIX + "checker")
    for x in (-11.0, 10.0):
        for z in (-6.0, 5.0):
            m.box((x, 0, z), (x + 1, 9, z + 1), WOOD_D, grain="y")
    m.box((-12, 9, -7), (12, 13, 7), WOOD, grain="x")
    m.box((-10, 12.5, -5), (10, 13.25, 5), OPAL, skip="d", **LIT)
    return m


def _curtain():
    """The darkroom's black-out curtain, drawn aside to one jamb of the arch, on its brass rail.
    Anchor: on the wall, under the middle of the rail at floor level."""
    m = M.Model(PREFIX + "curtain")
    m.box((-24, 46.5, 1), (24, 47.5, 2), BRASS, grain="x")
    for x in (-24.0, 23.0):
        m.box((x, 46, 0), (x + 1, 48, 2.5), BRASS_D)
    for x, deep in ((-23.0, 3.0), (-21.0, 4.0), (-19.0, 3.0), (-17.0, 4.0), (-15.0, 2.5)):
        m.box((x, 1, 0.5), (x + 2, 46.5, 0.5 + deep), CLOTH, grain="y")
    return m


@functools.lru_cache(maxsize=None)
def _models():
    out = {}
    for name, seed in FACES:
        for tag, anchor in (("", LOW), ("_up", HIGH)):
            m = _face(name + tag, seed + (500 if tag else 0), anchor)
            out[m.name] = m
    for m in (_safelight(), _tray(), _bottles(), _tap(), _car(), _rope(), _guides(), _checker(), _curtain()):
        out[m.name] = m
    return out


def models():
    return dict(_models())


# ---- building -----------------------------------------------------------------------------------
def stacks():
    """The stacks: [(x, (z0, z1), sides)]: the column of cells, its run, and the sides shelves face."""
    return [(ISLAND_X[0], ISLAND_Z, ("west", "east")), (ISLAND_X[1], ISLAND_Z, ("west", "east")),
            (X0, WEST_STACK_Z, ("east",)), (X1, EAST_STACK_Z, ("west",))]


def _faces(c, own, x, run, side, origin, salt):
    """Hang the faces of one side of a stack: three cells to a face, two tiers."""
    n = 0
    plane = float(x + 1) if side == "east" else float(x)
    for i in range((run[1] - run[0] + 1) // FACE_CELLS):
        z = run[0] + FACE_CELLS * i + FACE_CELLS / 2.0
        for tier, (tag, anchor) in enumerate((("", LOW), ("_up", HIGH))):
            name = FACES[(i + 2 * tier + salt) % len(FACES)][0] + tag
            y = FEET + FACE_CELLS * tier + anchor * PX
            n += K.put(c, own[PREFIX + name], (plane, y, z), mount="wall", facing=side, origin=origin)
    return n


def build_platevault(canvas, origin=(0, 0, 0)):
    """Dress the room; returns the number of display entities placed."""
    ox, oy, oz = origin
    own = _models()
    n = 0

    def put(x, y, z, state):
        canvas.set(ox + x, oy + y, oz + z, state)

    def cut(x, y, z):
        canvas.clear(ox + x, oy + y, oz + z)

    # the floor: boards in the vault, slate in the darkroom and under its wall, a drain before the sink
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            put(x, FLOOR_Y, z, SLATE_FOOT if z == WALL_Z else WET_FLOOR if z > WALL_Z else FLOOR)
    put(HALL_DOOR[0], FLOOR_Y, BENCH_Z - 1, B.IRON_GRATE)

    # the stacks' cores
    for x, (z0, z1), _ in stacks():
        for z in range(z0, z1 + 1):
            for y in range(FEET, TOP + 1):
                put(x, y, z, CORE)

    # the iron beams on the pilaster rows, between the stacks; the last one lies on the darkroom's wall
    for z in PIER_Z[:-1]:
        for x in range(X0, X1 + 1):
            if not canvas.has(ox + x, oy + TOP, oz + z):
                put(x, TOP, z, BEAM)

    # the darkroom: its wall with the arch, the lining of the two long walls, the panelling of the south wall
    for x in range(X0, X1 + 1):
        for y in range(FEET, TOP):
            put(x, y, WALL_Z, slate(y))
        put(x, TOP, WALL_Z, BEAM)
    for x in range(ARCH_X[0], ARCH_X[1] + 1):
        for y in range(FEET, ARCH_Y + 1):
            cut(x, y, WALL_Z)
    put(ARCH_X[0], ARCH_Y, WALL_Z, st(B.SLATE_BRICK.stairs, facing="west", half="top"))
    put(ARCH_X[1], ARCH_Y, WALL_Z, st(B.SLATE_BRICK.stairs, facing="east", half="top"))
    for x in range(ARCH_X[0] + 1, ARCH_X[1]):
        put(x, ARCH_Y, WALL_Z, st(B.SLATE_BRICK.slab, type="top"))
    for z in range(DARK_Z[0], DARK_Z[1] + 1):
        for y in range(FEET, TOP + 1):
            put(X0, y, z, slate(y))
            put(X1, y, z, slate(y))
    for x in range(DARK_X[0], DARK_X[1] + 1):
        sink = SINK_X[0] <= x <= SINK_X[1]
        put(x, FEET, BENCH_Z, st(B.ASHLAR_FINE.slab, type="bottom") if sink else SLATE_HEAD)
        for y in range(FEET + 1, TOP + 1):
            put(x, y, BENCH_Z, panel("south"))

    # the lift: its shaft through the chart room's floor, the base the car stands on
    cut(LIFT[0], CEIL_Y, LIFT[1])
    put(LIFT[0], FEET, LIFT[1], B.IRON_CAST)

    # ---- models: the faces of the stacks, their numbers --------------------------------------------
    for k, (x, run, sides) in enumerate(stacks()):
        for side in sides:
            n += _faces(canvas, own, x, run, side, origin, k + (side == "east"))
    for label, x in zip(("2", "1"), ISLAND_X):                    # 1 on the left as one comes in
        n += signs.plate(canvas, label, (S.mid(x), FEET + 1.75, float(ISLAND_Z[0])), facing="north", origin=origin)

    # the rolling ladder on the nave face of the west island (props/furniture: the rail's pieces run to
    # the right as one looks at the face, so from its south end)
    front = (ISLAND_X[0] + 1 + (DEPTH + 0.25) * PX, float(FEET))
    n += furniture.rail(canvas, (front[0], front[1], S.mid(ISLAND_Z[1])), ISLAND_Z[1] - ISLAND_Z[0] + 1,
                        facing="east", origin=origin)
    n += furniture.place(canvas, "library_ladder", (front[0], front[1], S.mid(PIER_Z[0] + 2)), facing="east", origin=origin)
    n += K.put(canvas, own[PREFIX + "curtain"], (AXIS_X, float(FEET), float(WALL_Z)), mount="wall", facing="north",
               origin=origin)

    # ---- the lamps -----------------------------------------------------------------------------------
    for z, level in NAVE_LAMPS:
        n += lamps.place(canvas, "pendant", (AXIS_X, float(TOP), S.mid(z)), origin=origin, version=LAMPS, level=level)
    for x, z, level in AISLE_LAMPS:
        n += lamps.place(canvas, "pendant", (x, float(TOP), S.mid(z)), origin=origin, version=LAMPS, level=level)

    # ---- the darkroom's pieces -----------------------------------------------------------------------
    south = Z1 + 1 - PANEL_T                            # the face of the south wall's panelling
    bench = FEET + 1.0
    n += K.put(canvas, own[PREFIX + "safelight"], (AXIS_X, SAFELIGHT_Y, south), mount="wall", facing="north", origin=origin)
    K.offer_lights(canvas, [((ox + HALL_DOOR[0], oy + FEET + 2, oz + BENCH_Z - 1), ASK_DARK)], f"{NAME}:safelight")
    tap = (AXIS_X, FEET + 1.75, south)
    n += K.put(canvas, own[PREFIX + "tap"], tap, mount="wall", facing="north", origin=origin)
    mouth = K.turn(K.FACING["north"], TAP_MOUTH)
    MK.puff(canvas, tuple(tap[i] + mouth[i] for i in range(3)), "dripping_water", DRIP, origin=origin)
    for i, x in enumerate(range(SINK_X[1] + 1, DARK_X[1])):
        n += K.put(canvas, own[PREFIX + "tray"], (S.mid(x), bench, BENCH_Z + 0.4), yaw=(-4.0, 3.0, 0.0)[i % 3], origin=origin)
    for x in (DARK_X[0] + 0.6, DARK_X[0] + 1.9, DARK_X[1] + 0.5):
        n += K.put(canvas, own[PREFIX + "bottles"], (x, bench, BENCH_Z + 0.55), origin=origin)

    # ---- the lift ------------------------------------------------------------------------------------
    shaft = (S.mid(LIFT[0]), S.mid(LIFT[1]))
    for y in (FEET + 1.0, FEET + 4.0):
        n += K.put(canvas, own[PREFIX + "lift_guides"], (shaft[0], y, shaft[1]), yaw=90.0, origin=origin)
    n += K.put(canvas, own[PREFIX + "lift_car"], (shaft[0], LIFT_REST, shaft[1]), yaw=-90.0, origin=origin)
    MK.slide(canvas, "y", LIFT_MOVES, LIFT_CYCLE)
    for k in range(2):
        n += K.put(canvas, own[PREFIX + "lift_rope"], (shaft[0], LIFT_REST + CAR_TOP + k * ROPE_L, shaft[1]), origin=origin)
        MK.slide(canvas, "y", LIFT_MOVES, LIFT_CYCLE)

    # ---- the register desk beside the lift, the day's cases by the door ------------------------------
    desk = (X0 + 2.5, float(FEET), Z0 + 0.5)
    top = FEET + furniture.TOP["writing_desk"]
    n += furniture.place(canvas, "writing_desk", desk, facing="south", origin=origin)
    n += furniture.place(canvas, "stool", (desk[0] + 0.1, float(FEET), desk[2] + 1.0), origin=origin)
    n += lamps.place(canvas, "desk_green", (desk[0] + 0.55, top, desk[2] - 0.1), origin=origin)
    n += paper.place(canvas, "logbook", (desk[0] - 0.15, top, desk[2] + 0.05), facing="south", origin=origin)
    check = (X1 - 2.5, float(FEET), Z0 + 0.6)           # the checking table, east of the door
    glass = FEET + CHECK_TOP
    n += K.put(canvas, own[PREFIX + "checker"], check, origin=origin)
    K.offer_lights(canvas, [((ox + int(check[0]), oy + FEET + 1, oz + Z0), ASK_CHECK)], f"{NAME}:checker")
    n += paper.place(canvas, "photo_plate", (check[0] - 0.3, glass, check[2]), yaw=8.0, origin=origin)
    n += paper.place(canvas, "photo_plate_b", (check[0] + 0.3, glass, check[2] - 0.05), yaw=-12.0, origin=origin)
    n += furniture.place(canvas, "crate", (X1 - 0.75, float(FEET), Z0 + 0.6), yaw=4.0, origin=origin)
    n += furniture.place(canvas, "crate_small", (X1 - 0.8, FEET + furniture.TOP["crate"], Z0 + 0.6), yaw=20.0, origin=origin)
    return n


def build(canvas, origin=(0, 0, 0)):
    """What the master scene calls: the room, once it has moved in."""
    if not MOVED_IN:
        return 0
    return build_platevault(canvas, origin)
