"""Test scene of the battery room's switchboard (machines/batteryboard.py; the room's card is
plan/packages/interiors/batteryroom.md, what the room needs to know of the board is on the page
plan/packages/machines/batteryboard.md): the board where the room will have it, in a box that
stands in for the room.

The box is the clear inside under the time room (main/shell.ROOMS), six rows high: two rows of
slate brick, rusticated ashlar above, the time room's floor over it, an iron beam under that on
each of the four pilaster lines. No windows, no door, no racks and no cells: those are the room's.
From each wing's clamp a pair of bars runs south under the beams, as the room may run them
(batteryboard.run()). The light stands in for the room's three caged lamps (third grade): one
over the board, two over the aisle; the sources are handed to the sky line.

    python -m scenes.obs_mach_batteryboard        # writes shots.json from the numbers below
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.machines import _powerkit as K
from scenes.obs.machines import batteryboard as board
from scenes.obs.machines import board as family
from scenes.obs.main import shell

BIOME = "obs_blue"
BIOME_MARGIN = 24
BIOME_MARGIN_Y = 24

X0, Z0, X1, Z1 = shell.ROOMS["time room"]["box"]                # the room lies under it: x 2..13, z -25..-7
FY = int(board.FLOOR)                                           # where feet stand
ROWS = 6                                                        # clear height
BEAMS_Z = tuple(z for z in range(Z0, Z1 + 1) if (z - Z0) % 4 == 3)      # -22, -18, -14, -10
FLOOR = B.SLATE_SMOOTH.block                                    # stands in for the room's acid-proof floor
DADO = B.SLATE_BRICK.block
WALL = B.ASHLAR_ROUGH.block
DECK = shell.ROOM_FLOOR                                         # the time room's floor, seen from below
BEAM = B.IRON_RIVETED.block
LAMPS = [((board.AXIS_X, FY + 4.5, Z0 + 1.5), 8),               # over the board: the cell over board.STAND
         ((board.AXIS_X - 0.5, FY + 4.5, BEAMS_Z[0] + 0.5), 8),     # under the first beam, over the aisle
         ((board.AXIS_X - 0.5, FY + 4.5, BEAMS_Z[2] + 0.5), 7)]     # under the third
TIME = 14000                                                    # light version A, the default

EYE = S.EYE


def build():
    c = Canvas()
    c.box(X0 - 1, FY - 1, Z0 - 1, X1 + 1, FY - 1, Z1 + 1, FLOOR)
    c.box(X0 - 1, FY + ROWS, Z0 - 1, X1 + 1, FY + ROWS, Z1 + 1, DECK)
    for y in range(FY, FY + ROWS):
        block = DADO if y < FY + 2 else WALL
        c.box(X0 - 1, y, Z0 - 1, X1 + 1, y, Z0 - 1, block)
        c.box(X0 - 1, y, Z1 + 1, X1 + 1, y, Z1 + 1, block)
        c.box(X0 - 1, y, Z0, X0 - 1, y, Z1, block)
        c.box(X1 + 1, y, Z0, X1 + 1, y, Z1, block)
    for z in BEAMS_Z:
        c.box(X0, FY + ROWS - 1, z, X1, FY + ROWS - 1, z, BEAM)
    n = board.place(c, (0, 0, 0))
    hang = tuple(z + 0.5 for z in BEAMS_Z)
    for side in ("west", "east"):
        n += board.run(c, side, hang[-1] + 0.5, hang, (0, 0, 0))
    K.light(c, LAMPS, (0, 0, 0), "machines/batteryboard:stand-in", rank=3)
    c.entity_counts = {"machines": n}
    sky.build(c, (0, 0, 0))                         # the sky line's light sources go in last
    return c


def build_models():
    out = dict(family.models())
    out.update(board.models())
    return out


def write_pack(pack_dir):
    """The repainted iron and ashlar of the box, and the sky's sun."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots():
    """The cameras: the board from the door's end of the aisle, from half way, face on and near,
    each wing with its bars, the head, and the bars overhead."""
    ax, fz, y = board.AXIS_X, board.FACE_Z, FY + EYE
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(float(v), 2) for v in pos],
                    "look_at": [round(float(v), 2) for v in look_at], "time": TIME})

    shot("aisle", (ax - 0.5, y, Z1 + 0.5), (ax, FY + 2.4, fz))                  # a step inside the door
    shot("mid", (ax, y, (Z0 + Z1) / 2.0), (ax, FY + 2.5, fz))                   # half way down the aisle
    shot("board", (ax, y, fz + 4.4), (ax, FY + 2.6, fz))                        # the board, face on
    shot("main", (ax + 0.5, y, fz + 1.9), (ax, FY + 2.7, fz))                   # the middle slab, near
    shot("west", (ax + 0.4, y, fz + 2.3), (board.X[0] + 0.8, FY + 2.7, fz))     # a wing and its bars' landing
    shot("east", (ax + 3.9, y, fz + 2.0), (ax + 0.6, FY + 2.6, fz))             # from the east, along the face
    shot("head", (ax, y, fz + 1.6), (ax, FY + 4.7, fz - 0.2))                   # the bus bars and the conduits
    shot("bars", (ax - 0.8, y, BEAMS_Z[1] + 1.0), (board.X[0] + 0.7, FY + 2.9, BEAMS_Z[0] + 0.5))    # overhead
    return out
