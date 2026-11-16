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
                       chart room (chart, c350), the register desk beside it, the checking table
                       with its lit glass east of the door
  the stacks (z 9..20) a nave three wide on the axis (x 6..8) between two island stacks (x 5 and
                       x 9), a side aisle beyond each, and a stack on either long wall (x 2 and
                       x 13). Every stack rises to the ceiling: twelve shelves of plates in their
                       sleeves, edge-on. Iron beams cross the nave and the aisles on the pilaster
                       rows and carry the lamps
  cross aisle (z 21)   joins the aisles before the darkroom wall
  darkroom (z 23..25)  the last bay, lined with slate, behind a slate wall on the pilaster row z 22
                       with an arch three wide on the axis. Its one light is the safelight over the
                       sink on the south wall: the red point the nave ends on, seen from the door.
                       What stands in it, and the lift, are power's kit (interiors/_darkroom, c339)

The way of a plate reads from south to north: the sink and the trays under the red lamp, the
stacks, the register desk, the lift.

Light. The room is a way like the others (cr2, 11-16): wherever a person can stand the block light
is 5 or more, on the threshold 7; the lamps of the stacks give 7 to 8, and the darkroom end stays
the darkest place of the building, 5 to 6. The lamps: a shaded pendant under every beam of the nave
and of the two side aisles, a caged lamp over the door, one by the lift's winch and one on the
south end of each island stack (the cross aisle and the arch), the desk lamp, the checking table's
glass. A lamp's source stands under the lamp in the row of a walker's head: the shade
throws the light down, and the ceiling over it stays dark. In the darkroom the safelight's glow is
a source of 6 in every cell before the benches; the red lamp stays the one bright thing in it.
build/scenes/obs_int_platevault/ways.py reads the result as tools/darkfloor.py does. Nothing lights
a window of the base storey: the wall stacks and the darkroom's lining are whole blocks and stand
before every one of them, so the storey stays the dark band it is from outside.

A stack is a core of wood blocks (it stops who walks) with a face of shelves on each long side: a
model three blocks wide and high, two tiers of them. A face takes its light from the cell its
anchor stands in: the lower tier's from the row over a walker's head, the upper tier's from two
rows higher, which is two steps dimmer, so the shelves fade towards the ceiling as they do under a
shaded lamp.

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
from . import _darkroom as D

ORDER = 80              # a room that moves into the shell (INTERFACE 3)
MOVED_IN = True         # the master scene dresses the room (fast lane: a card's switch is turned on with its delivery)
NAME = "interiors/platevault"
PREFIX = "int_vault_"
PX = 1 / 16.0
VIEW = M.NEAR           # everything in the room is drawn within 32 blocks (s2, 11-16; the assembly lowers it after
#                         build()): no board view looks into the base storey, whose windows the stacks stand before

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

# ---- light: what the room asks of the light line ------------------------------------------------
# A source in the row of a walker's head lights the floor around it three cells far at 8 and one cell
# far at 6 (5 is the line); a source at the lamp itself, three rows higher, would have to be an 11.
LAMPS = "b"                         # the versions of props/lamps with a shade or a guard
LAMP_X = (float(X0 + 2), AXIS_X, X1 - 1.5)      # 4.0, 7.5, 11.5: the pendants of the west aisle, the nave, the east aisle
LAMP_Z = PIER_Z[:-1]                # 10, 14, 18: one under every beam
HEAD = FEET + 1                     # the row of a walker's head: where the sources stand
DOOR_LAMP_Y = 3.0                   # the caged lamp over the door: flat on the wall, and above what one sees coming in
CAGE_Y = 2.5                        # the other caged lamps
ASK_WAY = 8                         # under a pendant, inside the door, before the south end of an island
ASK_LIFT = 7                        # by the lift
ASK_CHECK = 7                       # the checking table's glass
ASK_DARK = 6                        # the darkroom: as low as a source can be that leaves 5 in the cell beside it
PANEL_T = 3 * PX                    # a panel of the wainscot, off its wall

DRIP = 50                           # ticks between two drops of the sink's tap

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
BRASS, BRASS_D = K.BRASS, K.BRASS_D
LIT = dict(emit=15, shade=False)
OPAL = P.mat("opal")                        # lit opal glass, as the chart room's light table has it
CLOTH = P.mat("enamel_cloth", base=0)       # the black-out curtain: the darkest of the cloth


def slate(y):
    """The slate of the darkroom's wall and lining, in three courses."""
    return SLATE_FOOT if y <= S.PLINTH[1] else SLATE_HEAD if y >= TOP else SLATE_WALL


def panel(side):
    """A panel of the wainscot standing on that side of its cell."""
    back = {"north": "south", "south": "north", "west": "east", "east": "west"}[side]
    return st(B.WAINSCOT, facing=back, half="bottom", open="true")      # it stands on the side it turns its back to


class _Sleeves:
    """The picture of a shelf of plates seen from the aisle: the edges of their paper sleeves, two
    texels each, batch by batch in the same paper, here and there a sleeve that stands lower and
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
LOW, HIGH = 40.0, 24.0      # where a face's anchor is, from its foot: the lower tier's in the row over a walker's
#                             head, the upper tier's in the middle of its height, two rows higher


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


# ---- the room's own models: the checking table, the curtain ---------------------------------------
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
    for m in (_checker(), _curtain()):
        out[m.name] = m
    return out


def models():
    """The room's own models and those of the darkroom kit, which is no package of its own."""
    return dict(D.models(), **_models())


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
    # The racks, the sink and the bench stand along the south wall on their legs, as models: a barrier
    # one high in each of their cells stops who would walk through them (INTERFACE: inside a model
    # that is seen, never beyond its outline). Over it the wall is panelled; behind the legs it is
    # the plinth's own slate.
    for x in range(DARK_X[0], DARK_X[1] + 1):
        put(x, FEET, BENCH_Z, B.BARRIER)
        for y in range(FEET + 1, TOP + 1):
            put(x, y, BENCH_Z, panel("south"))

    # the lift's shaft is air from the floor to the ceiling; the frame is a model, and a barrier two
    # high stands in it. The floor block of the chart room over it stays shut until the cased riser
    # stands on it up there (chart): an open cell in that floor would be a pit
    for y in (FEET, FEET + 1):
        put(LIFT[0], y, LIFT[1], B.BARRIER)

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

    # ---- the lamps: a model each, and its source under it in the row of a walker's head ---------------
    ways = []
    for x in LAMP_X:
        for z in LAMP_Z:
            n += lamps.place(canvas, "pendant", (x, float(TOP), S.mid(z)), origin=origin, version=LAMPS, light=False)
            ways.append((int(x), z))
    n += lamps.place(canvas, "cage", (AXIS_X, FEET + DOOR_LAMP_Y, float(Z0)), facing="south", origin=origin,
                     version=LAMPS, light=False)                 # over the door: the threshold
    ways.append((HALL_DOOR[0], Z0))
    for x in ISLAND_X:                                          # the cross aisle and the arch
        n += lamps.place(canvas, "cage", (S.mid(x), FEET + CAGE_Y, float(ISLAND_Z[1] + 1)), facing="south", origin=origin,
                         version=LAMPS, light=False)
        ways.append((x, ISLAND_Z[1] + 1))
    K.offer_lights(canvas, [((ox + x, oy + HEAD, oz + z), ASK_WAY) for x, z in ways], f"{NAME}:way")
    n += lamps.place(canvas, "cage", (float(X0), FEET + CAGE_Y, S.mid(LIFT[1] + 1)), facing="east", origin=origin,
                     version=LAMPS, light=False)                 # on the west wall, over the lift's crank
    K.offer_lights(canvas, [((ox + LIFT[0], oy + HEAD, oz + LIFT[1] + 1), ASK_LIFT)], f"{NAME}:lift")

    # ---- the darkroom's pieces and the lift: power's kit ---------------------------------------------
    south = Z1 + 1 - PANEL_T                            # the face of the south wall's panelling
    n += D.dress(canvas, origin, wall_z=south, feet=FEET)
    # the safelight's glow: the row before the benches, a source in every cell, which leaves 5 behind it
    # and 5 on the benches' tops (a person gets up there with a hop)
    K.offer_lights(canvas, [((ox + x, oy + HEAD, oz + BENCH_Z - 1), ASK_DARK) for x in range(DARK_X[0], DARK_X[1] + 1)],
                   f"{NAME}:safelight")
    tap = K.turn(K.FACING["north"], D.TAP)              # the mouth of the tap that drips, from the sink's anchor
    MK.puff(canvas, (AXIS_X + tap[0], FEET + tap[1], south + tap[2]), "dripping_water", DRIP, origin=origin)
    n += D.lift(canvas, (LIFT[0], FEET, LIFT[1]), "east", origin, top=CEIL_Y - FEET)

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
    K.offer_lights(canvas, [((ox + int(check[0]), oy + HEAD, oz + Z0), ASK_CHECK)], f"{NAME}:checker")
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
