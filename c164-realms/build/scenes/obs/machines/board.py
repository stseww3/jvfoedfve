"""machines/switchboard-boiler, the switchboard of the power house (plan/ART-PLAN.md 5.3, 7.2;
plan/parts/A5-machines.md 2.6; card plan/packages/machines/switchboard-boiler.md). The boilers are
machines/boiler.py.

ROUGH SET: the volumes where they stand, so that the room can be laid out round them. The dials'
faces, the switches' poles and the bus bars come with the next commits.

What it is. A board of slate slabs in an iron frame, standing free before the west wall with its
face to the room: three slabs, three blocks high, over a base course of the materials line's
instrument panels (blocks). On the slabs the big pieces only: a round meter at the head of each
slab and a row of knife switches at the hand's height.

Where it stands. Before the west wall, north of the dynamo (interiors/powerhouse's place for it):
the base course in column X, cells Z[0]..Z[1], its faces to the east.

    x  the slabs' face is the plane x = FACE_X, two texels behind the faces of the base course
    y  the floor is S.LOWER_GROUND; the base course is one block, the slabs stand on it
    z  the board runs from Z[0] to Z[1] + 1

Every model is drawn in blocks in the board's own frame: x from the slabs' face into the room,
y up from the floor, z along the board from its north end.
"""
import functools

from artkit.blocks import st

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from . import _powerkit as K

PREFIX = "mach_board_"

# --- where it stands (scene coordinates) --------------------------------------------------------------
FLOOR = float(S.LOWER_GROUND)           # -6.0
X = 70                                  # the column of the base course
Z = (26, 32)                            # its cells: seven
FACING = "east"
FACE_X = X + 1.0 - 0.125                # 70.875: the slabs' face
BASE = ("louvre", "fuses", "bus_switch", "relays", "bus_switch", "fuses", "louvre")     # the base course, north to south

# --- the board (its own frame, blocks) ----------------------------------------------------------------
SLABS = (2.0, 3.0, 2.0)                 # the slabs' widths, north to south
SLAB_Y = (1.0, 4.0)                     # they stand on the base course and are three blocks high
SLAB_T = 0.25                           # 4 texels of slate
FRAME = 0.125                           # the frame's bars: 2 texels
METER_Y = 3.25                          # the meters' middles
METER_R = 0.5                           # a meter is a block across (the card)
SWITCH_Y = 1.875                        # the knife switches' middles
SWITCH = (0.5, 1.0)                     # a switch: half a block wide, one high (the card)

# --- for the others (scene coordinates) ---------------------------------------------------------------
# The dials glow faintly: a source before the middle slab, for the sky line to set.
LIGHTS = [((X + 2.5, FLOOR + METER_Y, (Z[0] + Z[1] + 1) / 2.0), 6)]
KEEP_CLEAR = ((X - 0.5, FLOOR, float(Z[0]), X + 1.5, FLOOR + SLAB_Y[1] + 0.75, Z[1] + 1.0),)

# --- materials (the palette's, and nothing else) ------------------------------------------------------
SLATE = P.mat("slate")
IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
BRASS = P.mat("brass")
PORCELAIN = P.mat("porcelain")
CREAM = P.mat("cream")
WOOD = P.mat("dark_wood")


def _slab(name, width):
    """One slab and its frame, drawn from its north end."""
    d = K.Draw(PREFIX + name, scale=2.0)
    d.box((-SLAB_T, SLAB_Y[0], 0.0), (0.0, SLAB_Y[1], width), SLATE)
    for z in (0.0, width):                                                          # the uprights
        d.box((-SLAB_T - FRAME, 0.0, z - FRAME / 2.0), (0.0625, SLAB_Y[1] + FRAME, z + FRAME / 2.0), IRON_D)
    d.box((-SLAB_T, SLAB_Y[1], 0.0), (0.0625, SLAB_Y[1] + FRAME, width), BRASS)        # the head rail
    return d


def _meter():
    d = K.Draw(PREFIX + "meter", scale=1.0)
    d.tube("x", (0.0, 0.0), 0.0, 0.125, METER_R, BRASS, sides=16)
    d.tube("x", (0.0, 0.0), 0.125, 0.1875, METER_R - 0.0625, CREAM, sides=16)
    d.box((0.1875, -0.03125, -0.03125), (0.25, 0.34, 0.03125), IRON_D, rot=("x", 25.0, (0.1875, 0.0, 0.0)))
    return d


def _switch():
    d = K.Draw(PREFIX + "switch", scale=1.0)
    w, h = SWITCH[0] / 2.0, SWITCH[1] / 2.0
    d.box((0.0, -h, -w), (0.0625, h, w), PORCELAIN)
    for z in (-0.125, 0.125):
        d.box((0.0625, -h + 0.125, z - 0.03125), (0.25, h - 0.125, z + 0.03125), BRASS)
    d.box((0.25, h - 0.25, -0.1875), (0.375, h - 0.125, 0.1875), WOOD)
    return d


@functools.lru_cache(maxsize=None)
def _drawn():
    built = [_slab("slab_2", 2.0), _slab("slab_3", 3.0), _meter(), _switch()]
    return {d.m.name[len(PREFIX):]: d for d in built}


def models():
    return {d.m.name: d.m for d in _drawn().values()}


def build(canvas, origin=(0, 0, 0)):
    """Lay the base course and place the board; returns the number of display entities."""
    drawn = _drawn()
    ox, oy, oz = (int(v) for v in origin)
    for i, name in enumerate(BASE):
        canvas.set(ox + X, oy + int(FLOOR), oz + Z[0] + i, st(B.PANELS[name], facing=FACING))
    n = 0
    z = float(Z[0])
    # the board's frame is turned a quarter: its x looks east already, its z runs south
    for width in SLABS:
        n += K.place(canvas, drawn[f"slab_{int(width)}"], (FACE_X, FLOOR, z), origin)
        mid = z + width / 2.0
        n += K.place(canvas, drawn["meter"], (FACE_X, FLOOR + METER_Y, mid), origin)
        for k in range(int(width)):
            n += K.place(canvas, drawn["switch"], (FACE_X, FLOOR + SWITCH_Y, z + k + 0.5), origin)
        z += width
    return n
