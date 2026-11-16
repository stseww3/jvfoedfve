#!/usr/bin/env python
"""A paper study, not a rendering: the one-page sketch of the battery room (card
plan/packages/interiors/batteryroom.md) -- the plan, the hero piece, what the three views see --
drawn from the one table of positions below, before anything is built.

No block is set and the game's renderer is not used. The three views are flat boxes behind a depth
buffer, coloured with the palette's ramps and lit with the map's own lightmap at the levels the
three lamps would give: they show where things stand and where the light falls, not textures.

    python plan/parts/figs/int_batteryroom_sketch.py        (from c164-realms/)

writes int-batteryroom-sketch.png beside this file, or into the folder named. Positions are the
skeleton's; the room's box is the time room's of main/shell, a floor lower.
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "build")))

from artkit import gamelook                         # noqa: E402
from scenes.obs.common import palette as P          # noqa: E402
from scenes.obs.common import skeleton as S         # noqa: E402
from scenes.obs.main import _plan as MP             # noqa: E402
from scenes.obs.main import shell                   # noqa: E402
from scenes.obs.sky import mood                     # noqa: E402

FONT = os.environ.get("PLAN_FONT", "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc")
PX = 1.0 / 16.0

# ---- the table: where everything stands (blocks, skeleton coordinates; px = sixteenths) ---------------
X0, Z0, X1, Z1 = shell.ROOMS["time room"]["box"]            # 2, -25, 13, -7: the cells of the clear box
FEET = S.GROUND                                             # 0
TOP = S.STRING - 1                                          # 5: the last clear row; the deck is the block above
AXIS = (X0 + X1 + 1) / 2.0                                  # 8.0: the long axis, between two cells
DOOR = (7, Z1 + 1)                                          # the cell of the south wall the door stands in
DOOR_H = 2
BEAMS = tuple(z for z in range(Z0, Z1 + 1) if MP.on_pilaster(z))                    # -22, -18, -14, -10
TRAY_Z = Z0 + 1                                             # -24: the time room's cable tray under its grating (m2)
EAST_BAYS = tuple(b for b in range(1, S.N_BAYS + 1) if set(MP.window_rows(b)) <= set(range(Z0, Z1 + 1)))
WEST_BAYS = tuple(b for b in EAST_BAYS if all(abs(z - S.DOME_CENTRE[1]) > MP.WEST_BLIND_Z for z in MP.window_rows(b)))
WINDOW_Y = MP.BASE_WINDOW                                   # 3..4
AISLE = (7, 8)
BANKS = ((5, 6), (9, 10))                                   # a bank: two rows of jars, back to back
ROWS = tuple(x for bank in BANKS for x in bank)
BANK_Z = (BEAMS[0], BEAMS[-1])                              # -22..-10: thirteen cells, from the first beam to the last
JAR = (7, 9, 11)                                            # px: along the row, high, across it
JAR_Z = (4, 12)                                             # px from the north edge of a cell: the middles of its two jars
TIERS = (5, 20)                                             # px above the floor: where the jars of the two tiers stand
POSTS = tuple(z + 0.5 for z in range(BANK_Z[0], BANK_Z[1] + 1, 2))                  # -21.5 .. -9.5: every other cell
GANTRIES = tuple(z + 0.5 for z in BEAMS)                    # the posts under the beams run up and carry the bars
LINTEL = 37                                                 # px: the top of a gantry's lintel
BAR = (40, 44)                                              # px: a bus bar, on three pixels of porcelain
BAR_X = tuple(b + s * 0.25 for _a, b in BANKS for s in (-1, 1))                     # 5.75, 6.25, 9.75, 10.25: a pair to a bank
BAR_Z = (Z0 + 6 * PX, BANK_Z[1] + 1 - 2 * PX)               # from the face of the board to the last jar
RISE_Z = BANK_Z[1] + JAR_Z[1] * PX                          # -9.25: over the last jar of a row, where its link goes up
PANELS = ((5.5, 7.0), (7.0, 9.0), (9.0, 10.5))              # the board: three slabs; the middle one as wide as the aisle
BOARD_Y = (0.75, 3.0)
BOARD_Z = Z0 + 6 * PX                                       # the face of the slabs: they stand six pixels off the wall
METERS = ((7.5, "V"), (8.5, "A"))
METER_Y = 2.45
FEEDS = (6.5, 9.5)                                          # the two thin lines up: under the time room's piers x 6 and x 9
CABLE_Y = 2.125                                             # the supply: on the top of the dado
GLAND = (5.5, 1.5)                                          # where it comes through the south wall: behind the hall's board
# the three caged lamps: where the lamp is, the cell its light is in, the level asked for
LAMPS = (
    ("hang", (AXIS, 3.0, BEAMS[-1] + 0.5), (7, 2, BEAMS[-1]), 8),   # under the first beam: the ends of the banks, the way in
    ("hang", (AXIS, 3.0, BEAMS[1] + 0.5), (8, 2, BEAMS[1]), 7),     # under the third: the far half
    ("wall", (AXIS, 3.6, Z0), (8, 3, Z0), 8),                       # on the north wall over the board
)
VIEWS = (
    ("int_door", "进门第一眼", (7.5, 1.62, Z1 + 0.7), (AXIS, 1.7, Z0)),
    ("int_aisle", "顺着走道", (AXIS, 1.62, -15.2), (AXIS, 1.8, Z0)),
    ("int_board", "配电板近看", (AXIS, 1.62, -21.2), (AXIS, 1.95, Z0)),
)
FOV = 77.0                                                  # render.py's: the game's 70, a tenth wider
NEAR = 0.08


def c(name, step):
    return tuple(int(v) for v in P.colour(name, step))


INK = c("iron", 0)
PAPER = (236, 232, 222)
NOTE = (60, 64, 72)
RED = (176, 40, 30)
AIR = (50, 54, 68)                                          # the inside of the room in the flat drawings
MARBLE, VEIN = c("porcelain", 3), c("porcelain", 2)
WOOD, WOOD_L, WOOD_D = c("dark_wood", 2), c("dark_wood", 4), c("dark_wood", 0)
LEAD, COPPER, COPPER_L, COPPER_D = c("iron", 5), c("old_copper", 3), c("old_copper", 4), c("old_copper", 1)
IRON, IRON_D, IRON_L = c("iron", 2), c("iron", 1), c("iron", 4)
CHINA = c("porcelain", 4)


# ---- the model of the views: boxes, and one-cell squares of floor, wall and ceiling ---------------------
SIDES = {
    "w": ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0), (-1, 0, 0)),
    "e": ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1), (1, 0, 0)),
    "d": ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1), (0, -1, 0)),
    "u": ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0), (0, 1, 0)),
    "n": ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, -1)),
    "s": ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1), (0, 0, 1)),
}
SHADE = {(0, 1, 0): 1.0, (0, -1, 0): 0.5, (0, 0, 1): 0.8, (0, 0, -1): 0.8, (1, 0, 0): 0.6, (-1, 0, 0): 0.6}


class Model:
    def __init__(self):
        self.corners, self.normals, self.colours, self.glows = [], [], [], []

    def box(self, lo, hi, colour, glow=False, only="wedusn"):
        span = (lo, hi)
        for key in only:
            *quad, normal = SIDES[key]
            self.corners.append([[span[k][i] for i, k in enumerate(corner)] for corner in quad])
            self.normals.append(normal)
            self.colours.append(colour)
            self.glows.append(glow)

    def run(self, a, b, half, colour, glow=False):
        """A bar from a to b along one axis, `half` thick either side of it; cut cell by cell, so
        that every length takes the light of its own cell."""
        axis = max(range(3), key=lambda i: abs(b[i] - a[i]))
        lo, hi = min(a[axis], b[axis]), max(a[axis], b[axis])
        cuts = [lo] + [float(v) for v in range(int(math.floor(lo)) + 1, int(math.ceil(hi)))] + [hi]
        for s, e in zip(cuts, cuts[1:]):
            p0, p1 = list(a), list(a)
            p0[axis], p1[axis] = s, e
            for i in range(3):
                if i != axis:
                    p0[i], p1[i] = a[i] - half[i], a[i] + half[i]
            self.box(p0, p1, colour, glow)

    def round(self, x, y, z, radius, deep, colour, glow=False):
        """A disc on a wall that looks south, its middle at (x, y), its back at z: three boxes."""
        for wide, high in ((1.0, 0.45), (0.8, 0.8), (0.45, 1.0)):
            self.box((x - radius * wide, y - radius * high, z), (x + radius * wide, y + radius * high, z + deep),
                     colour, glow, only="wedus")


def jar(m, x, y, z):
    """One cell of the battery, its middle at (x, z), standing at y: glass with a bright rim and
    corners, the acid and its level, the plates edge on to the aisle, flat on to the ends."""
    w, d = JAR[0] * PX / 2, JAR[2] * PX / 2
    m.box((x - d, y, z - w), (x + d, y + 6 * PX, z + w), c("night_glass", 1))
    m.box((x - d, y + 6 * PX, z - w), (x + d, y + 7 * PX, z + w), c("night_glass", 4), only="wesn")     # the level
    m.box((x - d, y + 7 * PX, z - w), (x + d, y + 8 * PX, z + w), c("night_glass", 0), only="wesn")
    m.box((x - d, y + 8 * PX, z - w), (x + d, y + 9 * PX, z + w), CHINA, only="wesnu")                   # the rim
    for sx in (-1, 1):
        for sz in (-1, 1):                                                                              # the corners
            px, pz = x + sx * d, z + sz * w
            m.box((px - 0.4 * PX, y, pz - 0.4 * PX), (px + 0.4 * PX, y + 8 * PX, pz + 0.4 * PX), c("porcelain", 2),
                  only="wesn")
        for dz, tone in ((-2, LEAD), (0, c("old_copper", 0)), (2, LEAD)):                               # the plates
            px = x + sx * (d + 0.003)
            m.box((px, y + PX, z + (dz - 0.5) * PX), (px, y + 6 * PX, z + (dz + 0.5) * PX), tone, only="e" if sx > 0 else "w")
    for sz in (-1, 1):
        pz = z + sz * (w + 0.003)
        m.box((x - 3.5 * PX, y + PX, pz), (x + 3.5 * PX, y + 6 * PX, pz), c("old_copper", 0), only="s" if sz > 0 else "n")
    m.box((x - PX, y + 9 * PX, z - w), (x + PX, y + 10 * PX, z + w + PX), LEAD, only="wesnu")           # lugs and link


def build():
    m = Model()
    slate, plate, grate = c("slate", 4), c("iron", 3), c("iron", 1)
    dado, stone, planks = c("slate", 3), c("ashlar", 2), c("dark_wood", 3)

    # the floor: slate; a sheet of lead-coloured plate under each bank; a drain in the aisle at two beams
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            under = x in ROWS and BANK_Z[0] <= z <= BANK_Z[1]
            drain = x in AISLE and z in BEAMS[1:3]
            m.box((x, -1, z), (x + 1, 0, z + 1), grate if drain else plate if under else slate, only="u")
    # the walls as they stand: two courses of the plinth's slate, the base storey's rough stone above
    for y in range(FEET, TOP + 1):
        tone = dado if y < S.BASE[0] else stone
        for z in range(Z0, Z1 + 1):
            m.box((X0 - 1, y, z), (X0, y + 1, z + 1), tone, only="e")
            m.box((X1 + 1, y, z), (X1 + 2, y + 1, z + 1), tone, only="w")
        for x in range(X0, X1 + 1):
            m.box((x, y, Z0 - 1), (x + 1, y + 1, Z0), tone, only="s")
            if not (x == DOOR[0] and y < DOOR_H):
                m.box((x, y, Z1 + 1), (x + 1, y + 1, Z1 + 2), tone, only="n")
    # the ceiling: the time room's boards; four iron beams on the pilaster lines; the time room's tray
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            if z in BEAMS or z == TRAY_Z:
                m.box((x, TOP, z), (x + 1, TOP + 1, z + 1), IRON if z in BEAMS else c("iron", 3), only="dns")
            else:
                m.box((x, TOP + 1, z), (x + 1, TOP + 2, z + 1), planks, only="d")
    # the iron cases before the windows: a back plate with a sill and a hood (two rows of stairs)
    for bays, back, front in ((EAST_BAYS, X1 + 0.5, X1), (WEST_BAYS, X0, X0 + 0.5)):
        for bay in bays:
            for z in MP.window_rows(bay):
                m.box((back, WINDOW_Y[0], z), (back + 0.5, WINDOW_Y[1] + 1, z + 1), IRON)
                m.box((front, WINDOW_Y[0], z), (front + 0.5, WINDOW_Y[0] + 0.5, z + 1), IRON)
                m.box((front, WINDOW_Y[1] + 0.5, z), (front + 0.5, WINDOW_Y[1] + 1, z + 1), IRON)

    # the banks: shelves of dark wood, the jars two to a cell and two tiers
    for a, b in BANKS:
        for x in (a, b):
            for z in range(BANK_Z[0], BANK_Z[1] + 1):
                for tier in TIERS:
                    y = tier * PX
                    m.box((x + PX, y - PX, z), (x + 1 - PX, y, z + 1), WOOD_L)
                    for rail in (x + PX, x + 1 - 3 * PX):
                        m.box((rail, y - 3 * PX, z), (rail + 2 * PX, y - PX, z + 1), WOOD)
                    for jz in JAR_Z:
                        jar(m, x + 0.5, y, z + jz * PX)
        # posts on porcelain feet under every other cell; under the beams they run up into a gantry
        for z in POSTS:
            tall = z in GANTRIES
            for px in (a + PX, b + 1 - 3 * PX):
                m.box((px, 2 * PX, z - PX), (px + 2 * PX, (LINTEL - 2 if tall else TIERS[1] - 1) * PX, z + PX), WOOD)
                m.box((px - PX, 0, z - 2 * PX), (px + 3 * PX, 2 * PX, z + 2 * PX), c("porcelain", 3))
            if tall:
                m.box((a + PX, (LINTEL - 2) * PX, z - PX), (b + 1 - PX, LINTEL * PX, z + PX), WOOD)
                for x in (b - 0.25, b + 0.25):
                    m.box((x - 1.5 * PX, LINTEL * PX, z - 1.5 * PX), (x + 1.5 * PX, BAR[0] * PX, z + 1.5 * PX), CHINA)

    # the bus bars: a pair over each bank, from the last jars to the board; at the door end a link
    # goes up to each bar from the last jar of its row
    mid = (BAR[0] + BAR[1]) / 2.0 * PX
    for x in BAR_X:
        m.run((x, mid, BAR_Z[0]), (x, mid, BAR_Z[1]), (PX, 2 * PX, 0), COPPER)
        m.run((x, (TIERS[1] + JAR[1]) * PX, RISE_Z), (x, BAR[0] * PX, RISE_Z), (0.75 * PX, 0, 0.75 * PX), COPPER_D)
        m.box((x - 2.5 * PX, mid - 3.5 * PX, BOARD_Z), (x + 2.5 * PX, mid + 3.5 * PX, BOARD_Z + PX), c("brass", 3))

    # the board: three slabs of marble in an iron frame on legs, off the wall
    by0, by1 = BOARD_Y
    for x0, x1 in PANELS:
        m.box((x0, by0, BOARD_Z - 2 * PX), (x1, by1, BOARD_Z), IRON)
        m.box((x0 + PX, by0 + PX, BOARD_Z), (x1 - PX, by1 - PX, BOARD_Z + 0.004), MARBLE, only="s")
        for x in (x0, x1 - 2 * PX):
            m.box((x, 0, BOARD_Z - 4 * PX), (x + 2 * PX, by0, BOARD_Z - 2 * PX), IRON)
    for x, _mark in METERS:
        m.round(x, METER_Y, BOARD_Z, 6.5 * PX, PX, c("brass", 3))
        m.round(x, METER_Y, BOARD_Z + PX, 5.5 * PX, 0.2 * PX, c("phosphor", 2), glow=True)
    for x in (AXIS - 5 * PX, AXIS, AXIS + 5 * PX):                                      # the change-over switch
        m.box((x - PX, 1.2, BOARD_Z), (x + PX, 1.85, BOARD_Z + 2 * PX), c("brass", 4))
    m.box((AXIS - 8 * PX, 1.72, BOARD_Z + 2 * PX), (AXIS + 8 * PX, 1.85, BOARD_Z + 4 * PX), WOOD_D)
    for x0, x1 in (PANELS[0], PANELS[2]):                                               # a knife switch, two fuses
        for x in ((x0 + x1) / 2 - 3 * PX, (x0 + x1) / 2 + 3 * PX):
            m.box((x - PX, 1.8, BOARD_Z), (x + PX, 2.35, BOARD_Z + 2 * PX), c("brass", 4))
            m.box((x - 2 * PX, 1.0, BOARD_Z), (x + 2 * PX, 1.5, BOARD_Z + 2 * PX), CHINA)
        m.box(((x0 + x1) / 2 - 6 * PX, 2.25, BOARD_Z + 2 * PX), ((x0 + x1) / 2 + 6 * PX, 2.37, BOARD_Z + 4 * PX), WOOD_D)
    for x in FEEDS:                                                                     # the two lines up
        m.run((x, by1, Z0 + 1.5 * PX), (x, TOP + 1, Z0 + 1.5 * PX), (PX, 0, PX), c("iron", 3))

    # the supply: out of the south wall behind the hall's board, round by the west wall on the top
    # of the dado, in behind the board
    half, off = 1.5 * PX, 3 * PX
    south, west, north = Z1 + 1 - off, X0 + off, Z0 + off
    m.box((GLAND[0] - 4 * PX, GLAND[1] - 4 * PX, Z1 + 1 - 2 * PX), (GLAND[0] + 4 * PX, GLAND[1] + 4 * PX, Z1 + 1), c("iron", 3))
    m.run((GLAND[0], GLAND[1], south), (GLAND[0], CABLE_Y, south), (half, 0, half), IRON_D)
    m.run((west, CABLE_Y, south), (GLAND[0], CABLE_Y, south), (0, half, half), IRON_D)
    m.run((west, CABLE_Y, north), (west, CABLE_Y, south), (half, half, 0), IRON_D)
    m.run((west, CABLE_Y, north), (PANELS[0][0], CABLE_Y, north), (0, half, half), IRON_D)

    # the lamps: a caged glass on a drop from a beam over the aisle; one on the wall over the board
    for kind, (x, y, z), _cell, _level in LAMPS:
        if kind == "hang":
            m.run((x, y, z), (x, TOP, z), (0.75 * PX, 0, 0.75 * PX), IRON)
            m.box((x - 3.5 * PX, y - 2 * PX, z - 3.5 * PX), (x + 3.5 * PX, y, z + 3.5 * PX), IRON)
            m.box((x - 2.5 * PX, y - 8 * PX, z - 2.5 * PX), (x + 2.5 * PX, y - 2 * PX, z + 2.5 * PX), c("glow", 3), glow=True)
        else:
            m.box((x - 4 * PX, y - 6 * PX, z), (x + 4 * PX, y + 6 * PX, z + PX), IRON)
            m.box((x - 2 * PX, y - 4 * PX, z + PX), (x + 2 * PX, y + 4 * PX, z + 5 * PX), c("glow", 3), glow=True)

    # small pieces. On the ends of the banks, where the first lamp is: the enamel plate (no naked
    # flame) and the record board; two carboys of distilled water by the east wall
    ze = BANK_Z[1] + 1 + 0.01
    m.box((5.75, 1.3, ze), (6.25, 1.8, ze + PX), c("cream", 3))
    m.box((5.86, 1.38, ze + PX), (6.14, 1.72, ze + 1.2 * PX), c("signal", 2), only="s")
    m.box((9.72, 1.1, ze), (10.28, 1.85, ze + PX), c("dark_wood", 1))
    m.box((9.78, 1.15, ze + PX), (10.22, 1.7, ze + 1.2 * PX), c("cream", 2), only="s")
    for x, z in ((11.7, Z1 - 0.5), (12.55, Z1 - 0.1)):
        m.box((x - 5 * PX, 0, z - 5 * PX), (x + 5 * PX, 6 * PX, z + 5 * PX), c("dark_wood", 3))
        m.box((x - 4 * PX, 6 * PX, z - 4 * PX), (x + 4 * PX, 13 * PX, z + 4 * PX), c("night_glass", 3))
        m.box((x - 1.5 * PX, 13 * PX, z - 1.5 * PX), (x + 1.5 * PX, 16 * PX, z + 1.5 * PX), c("porcelain", 3))
    # beside the board: a bench with the hydrometers and the measuring glasses, apron and gloves on hooks
    m.box((11.0, 0.82, Z0), (12.8, 0.9, Z0 + 0.6), c("dark_wood", 3))
    for x in (11.05, 12.65):
        m.box((x, 0, Z0 + 0.05), (x + 0.1, 0.82, Z0 + 0.55), WOOD)
    for x, h, tone in ((11.25, 8, CHINA), (11.4, 8, CHINA), (11.55, 8, CHINA), (11.95, 4, c("porcelain", 3)),
                       (12.15, 4, c("porcelain", 3)), (12.5, 5, c("cream", 3))):
        m.box((x, 0.9, Z0 + 0.25), (x + (1 if h == 8 else 2) * PX, 0.9 + h * PX, Z0 + 0.25 + 2 * PX), tone)
    m.box((3.85, 0.95, Z0), (4.35, 1.85, Z0 + PX), IRON_D)
    for x in (3.2, 3.45):
        m.box((x, 1.45, Z0), (x + 3 * PX, 1.85, Z0 + PX), INK)
    return m


# ---- light: the levels the lamps give, through the map's own lightmap ---------------------------------
def lightmap():
    a = {k: gamelook.colour(v) if isinstance(v, str) and v.startswith("#") else v
         for k, v in mood.values(mood.DEFAULT).items()}
    return gamelook.lightmap(a)[0]                  # indoors: no sky light


def levels(cells):
    best = np.zeros(len(cells), dtype=int)
    for _kind, _pos, at, lv in LAMPS:
        best = np.maximum(best, lv - np.abs(cells - np.array(at)).sum(axis=1))
    return best


def picture(model, eye, look_at, size, table, ss=2):
    """The model from a camera of the game: flat faces behind a depth buffer."""
    w, h = size[0] * ss, size[1] * ss
    eye = np.array(eye, dtype=float)
    f = np.array(look_at, dtype=float) - eye
    f /= np.linalg.norm(f)
    r = np.cross(f, (0.0, 1.0, 0.0))
    r /= np.linalg.norm(r)
    rot = np.stack([r, np.cross(r, f), f])
    ty = math.tan(math.radians(FOV) / 2.0)
    tx = ty * w / h
    corners = np.array(model.corners, dtype=float)
    normals = np.array(model.normals, dtype=float)
    colours = np.array(model.colours, dtype=float)
    glows = np.array(model.glows, dtype=bool)
    centres = corners.mean(axis=1)
    cam = (corners - eye) @ rot.T
    seen = (np.einsum("ij,ij->i", eye - centres, normals) > 1e-9) & (cam[:, :, 2].max(axis=1) > NEAR)
    shade = np.array([SHADE[tuple(int(v) for v in n)] for n in normals])
    lit = colours * table[levels(np.floor(centres + 0.3 * normals).astype(int))] * shade[:, None]
    rgb = np.where(glows[:, None], colours, np.minimum(255.0, lit)).astype(np.uint8)
    ncam = normals @ rot.T
    dist = np.einsum("ij,ij->i", corners[:, 0] - eye, normals)
    depth = np.full((h, w), np.inf)
    out = np.empty((h, w, 3), dtype=np.uint8)
    out[:] = (8, 9, 14)
    for i in np.nonzero(seen)[0]:
        p = cam[i]
        if p[:, 2].min() <= NEAR:                   # clip against the near plane
            cut = []
            for k in range(len(p)):
                a, b = p[k], p[(k + 1) % len(p)]
                if a[2] > NEAR:
                    cut.append(a)
                if (a[2] > NEAR) != (b[2] > NEAR):
                    cut.append(a + (NEAR - a[2]) / (b[2] - a[2]) * (b - a))
            if len(cut) < 3:
                continue
            p = np.array(cut)
        sx = w / 2.0 + p[:, 0] / p[:, 2] / tx * (w / 2.0)
        sy = h / 2.0 - p[:, 1] / p[:, 2] / ty * (h / 2.0)
        x0, x1 = max(0, int(math.floor(sx.min()))), min(w, int(math.ceil(sx.max())))
        y0, y1 = max(0, int(math.floor(sy.min()))), min(h, int(math.ceil(sy.max())))
        if x0 >= x1 or y0 >= y1:
            continue
        xs = np.arange(x0, x1) + 0.5
        ys = (np.arange(y0, y1) + 0.5)[:, None]
        bx, by = np.roll(sx, -1), np.roll(sy, -1)
        turn = 1.0 if float((sx * by - bx * sy).sum()) > 0.0 else -1.0
        inside = np.ones((y1 - y0, x1 - x0), dtype=bool)
        for k in range(len(sx)):
            inside &= turn * ((bx[k] - sx[k]) * (ys - sy[k]) - (by[k] - sy[k]) * (xs - sx[k])) >= 0.0
        if not inside.any():
            continue
        qx = (xs - w / 2.0) / (w / 2.0) * tx
        qy = -(ys - h / 2.0) / (h / 2.0) * ty
        inv = (ncam[i, 0] * qx + ncam[i, 1] * qy + ncam[i, 2]) / dist[i]
        z = np.where(inv > 1e-9, 1.0 / np.maximum(inv, 1e-9), np.inf)
        patch = depth[y0:y1, x0:x1]
        hit = inside & (z < patch)
        patch[hit] = z[hit]
        out[y0:y1, x0:x1][hit] = rgb[i]
    return Image.fromarray(out).resize(size, Image.LANCZOS)


# ---- flat drawings in the models' own pixels -----------------------------------------------------------
class Pixels:
    """A drawing in sixteenths of a block; (0, 0) is its lower left corner."""

    def __init__(self, w, h, ground):
        self.a = np.zeros((h, w, 3), dtype=np.uint8)
        self.a[:] = ground
        self.h = h

    def rect(self, x0, y0, x1, y1, colour):
        x0, y0, x1, y1 = (int(round(v)) for v in (x0, y0, x1, y1))
        self.a[max(0, self.h - y1):max(0, self.h - y0), max(0, x0):max(0, x1)] = colour

    def dot(self, x, y, colour):
        self.rect(x, y, x + 1, y + 1, colour)

    def disc(self, cx, cy, radius, colour):
        for y in range(int(cy - radius) - 1, int(cy + radius) + 2):
            for x in range(int(cx - radius) - 1, int(cx + radius) + 2):
                if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= radius ** 2:
                    self.dot(x, y, colour)

    def stamp(self, rows, x, y, colours):
        """A sprite with its lower left corner at (x, y); the first row is the top one."""
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch != ".":
                    self.dot(x + i, y + len(rows) - 1 - j, colours[ch])

    def image(self, scale):
        return Image.fromarray(self.a).resize((self.a.shape[1] * scale, self.a.shape[0] * scale), Image.NEAREST)


JAR_FACE = (                    # the side of a jar that looks at the aisle: seven by nine
    "RRRRRRR",
    "haaaaae",
    "hLLLLLe",
    "hnwpwne",
    "hnwpwne",
    "enwpwne",
    "enwpwne",
    "ewwwwwe",
    "ebbbbbe",
)
JAR_END = (                     # its end, across the row: the flat of the last plate
    "RRRRRRRRRRR",
    "haaaaaaaaae",
    "hLLLLLLLLLe",
    "hwpppppppwe",
    "hwpppppppwe",
    "ewpppppppwe",
    "ewpppppppwe",
    "ewwwwwwwwwe",
    "ebbbbbbbbbe",
)
JAR_COLOURS = dict(R=CHINA, h=c("porcelain", 2), e=c("night_glass", 3), a=c("night_glass", 0), L=c("night_glass", 4),
                   w=c("night_glass", 1), p=c("old_copper", 0), n=LEAD, b=c("night_glass", 2))
MAN = ("..hh..", "..hh..", ".bbbb.", "bbbbbb", "bbbbbb", "b.bb.b", "..bb..", ".b..b.", ".b..b.", ".b..b.")


def man(p, x, y, colour=(150, 146, 138)):
    """Somebody 1.8 tall, feet at (x, y): what the heights are measured against."""
    for x0, y0, x1, y1 in ((1, 0, 3, 13), (4, 0, 6, 13), (0, 13, 7, 24), (2, 24, 5, 29)):
        p.rect(x + x0, y + y0, x + x1, y + y1, colour)


def lamp(p, x, top, glow=True):
    """A caged lamp hanging from (x, top)."""
    p.rect(x - 3, top - 2, x + 4, top, IRON_L)
    p.rect(x - 2, top - 8, x + 3, top - 2, c("glow", 3))
    p.rect(x - 1, top - 7, x + 2, top - 3, c("glow", 4))
    for dx in (-3, 3):
        p.rect(x + dx, top - 9, x + dx + 1, top - 2, IRON_L)
    p.rect(x - 3, top - 9, x + 4, top - 8, IRON_L)


def hero():
    """The south end of a bank from the aisle, from the floor to the bars: z -12.5 .. -8.25."""
    w, h, base = 68, 50, 2
    p = Pixels(w, h, AIR)

    def zx(z):
        return int(round((z + 12.5) * 16))

    end = zx(BANK_Z[1] + 1)
    p.rect(0, 0, w, base, c("slate", 4))
    p.rect(0, 0, end, base, c("iron", 3))
    for tier in TIERS:
        y = tier + base
        p.rect(0, y - 3, end, y - 1, WOOD)
        p.rect(0, y - 1, end, y, WOOD_L)
        for cell in range(-13, BANK_Z[1] + 1):
            for jz in JAR_Z:
                left = zx(cell) + jz - 3
                p.stamp(JAR_FACE, left, y, JAR_COLOURS)
                p.dot(left + 1, y + 9, LEAD)                                # the lugs
                p.dot(left + 5, y + 9, LEAD)
                if left + 9 < end:
                    p.rect(left + 5, y + 10, left + 10, y + 11, LEAD)       # the link to the next jar
    for z in POSTS:
        if zx(z) < 0:
            continue
        tall = z in GANTRIES
        p.rect(zx(z) - 1, base + 2, zx(z) + 1, base + (LINTEL if tall else TIERS[1] - 1), c("dark_wood", 3))
        p.rect(zx(z) - 2, base, zx(z) + 2, base + 2, c("porcelain", 3))
        if tall:
            p.rect(zx(z) - 2, base + LINTEL, zx(z) + 2, base + BAR[0], CHINA)
            p.rect(zx(z) - 2, base + LINTEL + 1, zx(z) + 2, base + LINTEL + 2, c("porcelain", 2))
    bar = zx(BAR_Z[1])
    p.rect(0, base + BAR[0], bar, base + BAR[1], COPPER)
    p.rect(0, base + BAR[1] - 1, bar, base + BAR[1], COPPER_L)
    p.rect(0, base + BAR[0], bar, base + BAR[0] + 1, COPPER_D)
    rise = zx(RISE_Z)
    p.rect(rise - 1, base + TIERS[1] + JAR[1] + 1, rise + 1, base + BAR[0], COPPER_D)
    p.rect(end, base + 18, end + 1, base + 30, c("cream", 2))               # the record board on the end, edge on
    man(p, end + 2, base)
    return p


def section():
    """The room cut across under a beam, looking north: x 1.5 .. 14.5, y -0.5 .. 6.5."""
    w, h, left, base = 13 * 16, 7 * 16, 1.5, 8
    p = Pixels(w, h, AIR)

    def r(x0, y0, x1, y1, colour):
        p.rect(x0 - left * 16, y0 + base, x1 - left * 16, y1 + base, colour)

    r(0, -8, 16 * 16, 0, c("slate", 2))                                     # under the floor
    r(16 * X0, -2, 16 * (X1 + 1), 0, c("slate", 5))
    for a, b in BANKS:
        r(16 * a, -2, 16 * (b + 1), 0, c("iron", 4))
    for x, glass in ((X0 - 1, True), (X1 + 1, True)):                       # the inner leaves, a window in each
        r(16 * x, 0, 16 * x + 16, 32, c("slate", 3))
        r(16 * x, 32, 16 * x + 16, 96, c("ashlar", 2))
        r(16 * x, 16 * WINDOW_Y[0], 16 * x + 16, 16 * (WINDOW_Y[1] + 1), c("night_glass", 2))
    r(16 * (X0 - 1), 96, 16 * (X1 + 2), 112, c("dark_wood", 3))             # the time room's floor
    r(16 * X0, 80, 16 * (X1 + 1), 96, IRON)                                 # a beam
    for x in range(16 * X0 + 4, 16 * (X1 + 1), 8):
        p.dot(x - left * 16, 83 + base, IRON_L)
        p.dot(x - left * 16, 92 + base, IRON_L)
    for back, front in ((16 * X1 + 8, 16 * X1), (16 * X0, 16 * X0 + 8)):    # the cases before the windows
        r(back, 48, back + 8, 80, c("iron", 3))
        r(front, 48, front + 8, 56, c("iron", 3))
        r(front, 72, front + 8, 80, c("iron", 3))
    for a, b in BANKS:
        for x in (a, b):                                                    # the rows, end on
            for tier in TIERS:
                r(16 * x + 1, tier - 1, 16 * x + 15, tier, WOOD_L)
                for rail in (16 * x + 1, 16 * x + 13):
                    r(rail, tier - 3, rail + 2, tier - 1, WOOD)
                p.stamp(JAR_END, 16 * x + 3 - int(left * 16), tier + base, JAR_COLOURS)
                r(16 * x + 7, tier + 9, 16 * x + 9, tier + 10, LEAD)
        for post in (16 * a + 1, 16 * b + 13):                              # the gantry
            r(post, 2, post + 2, LINTEL - 2, c("dark_wood", 3))
            r(post - 1, 0, post + 3, 2, c("porcelain", 3))
        r(16 * a + 1, LINTEL - 2, 16 * b + 15, LINTEL, c("dark_wood", 3))
        for x in (16 * b - 4, 16 * b + 4):
            r(x - 2, LINTEL, x + 2, BAR[0], CHINA)
            r(x - 1, BAR[0], x + 1, BAR[1], COPPER_L)
    x = int(AXIS * 16 - left * 16)                                          # the lamp over the aisle
    p.rect(x, 48 + base, x + 1, 80 + base, IRON_L)
    lamp(p, x, 48 + base)
    r(16 * X0 + 2, 16 * CABLE_Y - 1, 16 * X0 + 5, 16 * CABLE_Y + 2, c("iron", 6))      # the supply on the west wall
    man(p, int(7.3 * 16 - left * 16), base)
    return p


def board():
    """The north wall from the aisle: x 2.6 .. 13.4, y 0 .. 4.3."""
    left, w, h = 2.6, 173, 69
    p = Pixels(w, h, c("ashlar", 1))

    def x_of(x):
        return int(round((x - left) * 16))

    p.rect(0, 0, w, 32, c("slate", 3))                                      # the plinth's slate under the rough stone
    y0, y1 = int(BOARD_Y[0] * 16), int(BOARD_Y[1] * 16)
    cable = int(round(CABLE_Y * 16))
    p.rect(0, cable - 1, x_of(PANELS[0][0]) + 1, cable + 2, IRON_D)         # the supply comes in from the west
    for x in (0.9, 1.9, 2.7):
        p.rect(x_of(left + x), cable - 2, x_of(left + x) + 1, cable + 3, IRON_L)
    for x in FEEDS:                                                         # the two lines up
        p.rect(x_of(x) - 1, y1, x_of(x) + 1, h, c("iron", 3))
    for x0, x1 in PANELS:
        a, b = x_of(x0), x_of(x1)
        for leg in (a, b - 2):
            p.rect(leg, 0, leg + 2, y0, IRON)
        p.rect(a, y0, b, y1, IRON)                                          # the frame, the marble
        p.rect(a + 1, y0 + 1, b - 1, y1 - 1, MARBLE)
        for i in range(a + 3, b - 5, 6):                                    # veins
            v = y0 + 3 + (i * 7) % 29
            p.rect(i, v, i + 3, v + 1, VEIN)
            p.rect(i + 2, v + 1, i + 5, v + 2, VEIN)
    for x, mark in METERS:                                                  # the two meters
        mx, my = x_of(x), int(METER_Y * 16)
        p.disc(mx, my, 6.6, c("brass", 3))
        p.disc(mx, my, 5.6, c("phosphor", 1))
        for k in range(-3, 4):
            ang = math.radians(90 + 22 * k)
            p.dot(int(mx + 4.4 * math.cos(ang)), int(my - 1 + 4.4 * math.sin(ang)), c("phosphor", 3))
        tip = math.radians(62 if mark == "V" else 112)
        for s in range(0, 5):
            p.dot(int(mx + s * math.cos(tip)), int(my - 2 + s * math.sin(tip)), c("phosphor", 4))
        p.rect(mx - 2, my - 10, mx + 2, my - 8, c("enamel", 2))
    cx = x_of(AXIS)                                                         # the change-over switch: up is charging
    for x in (cx - 5, cx, cx + 5):
        for y in (y0 + 4, y0 + 10, y0 + 16):
            p.rect(x - 1, y, x + 1, y + 2, COPPER)
        p.rect(x - 1, y0 + 11, x + 1, y0 + 17, c("brass", 4))
    p.rect(cx - 8, y0 + 14, cx + 8, y0 + 16, WOOD_D)
    for x0, x1 in (PANELS[0], PANELS[2]):                                   # a knife switch and two fuses to a bank
        mid = x_of((x0 + x1) / 2.0)
        for x in (mid - 4, mid + 2):
            p.rect(x, y0 + 16, x + 2, y0 + 18, COPPER)
            p.rect(x, y0 + 18, x + 2, y0 + 25, c("brass", 4))
            p.rect(x - 1, y0 + 4, x + 3, y0 + 12, CHINA)
            p.rect(x - 1, y0 + 4, x + 3, y0 + 5, c("brass", 3))
            p.rect(x - 1, y0 + 11, x + 3, y0 + 12, c("brass", 3))
        p.rect(mid - 6, y0 + 23, mid + 6, y0 + 25, WOOD_D)
    for x in BAR_X:                                                         # the bars come in on the wings, end on
        p.rect(x_of(x) - 3, BAR[0] - 2, x_of(x) + 3, BAR[1] + 2, c("brass", 3))
        p.rect(x_of(x) - 1, BAR[0], x_of(x) + 1, BAR[1], COPPER_L)
    lx, ly = x_of(AXIS), int(3.6 * 16)                                      # the lamp over it
    p.rect(lx - 1, ly + 6, lx + 1, h, IRON)
    p.rect(lx - 4, ly - 6, lx + 4, ly + 6, IRON)
    p.rect(lx - 2, ly - 4, lx + 2, ly + 4, c("glow", 3))
    p.rect(lx - 1, ly - 3, lx + 1, ly + 3, c("glow", 4))
    for y in (ly - 4, ly - 1, ly + 2):
        p.rect(lx - 3, y, lx + 3, y + 1, IRON_D)
    bx0, bx1 = x_of(11.0), x_of(12.8)                                       # the bench with the glassware
    p.rect(bx0, 13, bx1, 15, c("dark_wood", 3))
    for x in (bx0 + 1, bx1 - 3):
        p.rect(x, 0, x + 2, 13, WOOD)
    p.rect(x_of(11.2), 15, x_of(11.7), 17, WOOD)
    for x in (11.25, 11.4, 11.55):
        p.rect(x_of(x), 17, x_of(x) + 1, 24, CHINA)
    for x in (11.95, 12.15):
        p.rect(x_of(x), 15, x_of(x) + 2, 19, c("porcelain", 3))
    p.rect(x_of(12.5), 15, x_of(12.5) + 3, 20, c("cream", 3))
    p.rect(x_of(3.1), 30, x_of(4.5), 31, IRON_L)                            # the apron and the gloves on a rail of hooks
    p.rect(x_of(3.85), 15, x_of(4.35), 30, IRON_D)
    for x in (3.2, 3.45):
        p.rect(x_of(x), 23, x_of(x) + 3, 30, INK)
    man(p, x_of(4.9), 0, (120, 118, 114))
    return p


# ---- the plan -------------------------------------------------------------------------------------------
def plan(scale, fonts):
    xa, xb, za, zb = S.WALL_W, S.WALL_E + 1, Z0 - 2, Z1 + 4            # what the drawing shows: cells x 0..15, z -27..-4
    pad_l, pad_t = 160, 14
    w, h = (xb - xa) * scale + pad_l + 176, (zb - za) * scale + pad_t + 30
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img, "RGBA")
    small, tiny = fonts["small"], fonts["tiny"]

    def X(x):
        return pad_l + (x - xa) * scale

    def Z(z):
        return pad_t + (z - za) * scale

    def cell(x, z, fill, outline=None):
        d.rectangle([X(x), Z(z), X(x + 1), Z(z + 1)], fill=fill, outline=outline)

    stone, line = c("ashlar", 0), (120, 116, 108)
    for x in range(xa, xb):
        for z in range(za, zb):
            if X0 <= x <= X1 and Z0 <= z <= Z1:
                under = x in ROWS and BANK_Z[0] <= z <= BANK_Z[1]
                drain = x in AISLE and z in BEAMS[1:3]
                cell(x, z, c("iron", 3) if drain else c("iron", 5) if under else c("slate", 6), (92, 92, 98))
            elif X0 <= x <= X1 and (z > Z1 + 1 or z < Z0 - 1):
                cell(x, z, (214, 208, 196), (202, 196, 184))                # the hall to the south, the pavilion to the north
            else:
                cell(x, z, c("ashlar", 3) if x in (S.WALL_W, S.WALL_E) else stone, line)
    for bays, gx, ox, sx in ((EAST_BAYS, S.GLASS_E, S.WALL_E, X1), (WEST_BAYS, S.GLASS_W, S.WALL_W, X0)):
        for bay in bays:
            for z in MP.window_rows(bay):
                cell(gx, z, c("night_glass", 2), line)
                cell(ox, z, (176, 186, 214), line)
                d.rectangle([X(sx), Z(z), X(sx + 1), Z(z + 1)], outline=IRON_D, width=2)    # the iron case, overhead
                d.line([X(sx), Z(z), X(sx + 1), Z(z + 1)], fill=IRON_D, width=1)
                d.line([X(sx + 1), Z(z), X(sx), Z(z + 1)], fill=IRON_D, width=1)
    cell(DOOR[0], DOOR[1], (222, 214, 196), IRON_D)                     # the door, open into the room
    d.line([X(DOOR[0]), Z(DOOR[1] + 0.9), X(DOOR[0]), Z(DOOR[1] - 0.1)], fill=IRON_D, width=4)
    d.arc([X(DOOR[0] - 1), Z(DOOR[1] - 0.1), X(DOOR[0] + 1), Z(DOOR[1] + 1.9)], 270, 360, fill=IRON_D, width=1)
    d.rectangle([X(2.0), Z(Z1 + 2), X(7.0), Z(Z1 + 2.3)], outline=IRON_D, width=1)
    for z in BEAMS + (TRAY_Z,):                                         # the beams and the tray, overhead
        tone, wide = ((44, 50, 60), 3) if z in BEAMS else ((112, 120, 132), 7)
        for k in range(X0 * 4, (X1 + 1) * 4, 2):
            d.line([X(k / 4.0), Z(z + 0.5), X(k / 4.0 + 0.25), Z(z + 0.5)], fill=tone, width=wide)
    for x in ROWS:                                                      # the jars
        for z in range(BANK_Z[0], BANK_Z[1] + 1):
            for jz in JAR_Z:
                zc = z + jz * PX
                d.rectangle([X(x + 0.5 - 5.5 * PX), Z(zc - 3.5 * PX), X(x + 0.5 + 5.5 * PX), Z(zc + 3.5 * PX)],
                            fill=c("night_glass", 2), outline=CHINA)
    for a, b in BANKS:
        d.rectangle([X(a), Z(BANK_Z[0]), X(b + 1), Z(BANK_Z[1] + 1)], outline=WOOD, width=2)
        for z in GANTRIES:                                              # the gantries
            d.line([X(a + PX), Z(z), X(b + 1 - PX), Z(z)], fill=c("dark_wood", 3), width=4)
    for x in BAR_X:                                                     # the bus bars, the links up to them
        d.line([X(x), Z(BAR_Z[0]), X(x), Z(BAR_Z[1])], fill=COPPER, width=3)
        d.ellipse([X(x) - 3, Z(RISE_Z) - 3, X(x) + 3, Z(RISE_Z) + 3], fill=COPPER_D)
    off = 3 * PX
    cable = [(GLAND[0], Z1 + 1 - off), (X0 + off, Z1 + 1 - off), (X0 + off, Z0 + off), (PANELS[0][0], Z0 + off)]
    d.line([(X(x), Z(z)) for x, z in cable], fill=c("signal", 1), width=4, joint="curve")
    d.ellipse([X(GLAND[0]) - 6, Z(Z1 + 1) - 9, X(GLAND[0]) + 6, Z(Z1 + 1) + 3], fill=c("signal", 1), outline=INK)
    for x0, x1 in PANELS:
        d.rectangle([X(x0), Z(Z0 + 4 * PX), X(x1), Z(BOARD_Z)], fill=CHINA, outline=INK)
    for x, _mark in METERS:
        d.ellipse([X(x) - 5, Z(BOARD_Z) - 2, X(x) + 5, Z(BOARD_Z) + 8], fill=c("phosphor", 2), outline=INK)
    for x in FEEDS:
        d.ellipse([X(x) - 5, Z(Z0 + 0.09) - 5, X(x) + 5, Z(Z0 + 0.09) + 5], fill=c("enamel", 3), outline=INK)
    for _kind, (x, _y, z), _cell, lv in LAMPS:                          # the lamps and how far their light goes
        z = max(z, Z0 + 0.3)
        reach = (lv - 3) * scale
        d.ellipse([X(x) - reach, Z(z) - reach, X(x) + reach, Z(z) + reach], fill=(255, 198, 90, 30))
        d.ellipse([X(x) - 9, Z(z) - 9, X(x) + 9, Z(z) + 9], fill=c("glow", 2), outline=INK)
        d.text((X(x), Z(z)), str(lv), font=tiny, fill=INK, anchor="mm")
    ze = BANK_Z[1] + 1                                                  # small pieces
    d.rectangle([X(5.75), Z(ze), X(6.25), Z(ze + 0.14)], fill=c("signal", 2), outline=INK)
    d.rectangle([X(9.72), Z(ze), X(10.28), Z(ze + 0.14)], fill=c("cream", 3), outline=INK)
    for x, z in ((11.7, Z1 - 0.5), (12.55, Z1 - 0.1)):
        d.ellipse([X(x - 0.3), Z(z - 0.3), X(x + 0.3), Z(z + 0.3)], fill=c("night_glass", 4), outline=INK)
    d.rectangle([X(11.0), Z(Z0), X(12.8), Z(Z0 + 0.6)], fill=WOOD_L, outline=INK)
    d.rectangle([X(3.2), Z(Z0), X(4.35), Z(Z0 + 0.15)], fill=IRON_D)

    for x in range(X0, X1 + 1):                                         # the grid's numbers
        d.text((X(x + 0.5), Z(zb) + 4), str(x), font=tiny, fill=NOTE, anchor="ma")
    for z in range(Z0, Z1 + 1, 2):
        d.text((X(xa) - 6, Z(z + 0.5)), str(z), font=tiny, fill=NOTE, anchor="rm")
    d.text((X(xa) - 6, Z(zb) + 4), "z＼x", font=tiny, fill=NOTE, anchor="ra")
    d.text((X(xa + 1), Z(za + 0.5)), "北 ↑", font=small, fill=PAPER, anchor="mm")

    half = math.atan(math.tan(math.radians(FOV) / 2.0) * 16.0 / 9.0)   # the cameras
    for name, _what, eye, at in VIEWS:
        ex, ez = X(eye[0]), Z(eye[2])
        ang = math.atan2(at[2] - eye[2], at[0] - eye[0])
        for s in (-1, 1):
            d.line([ex, ez, ex + 1.9 * scale * math.cos(ang + s * half), ez + 1.9 * scale * math.sin(ang + s * half)],
                   fill=RED + (210,), width=2)
        d.ellipse([ex - 6, ez - 6, ex + 6, ez + 6], fill=RED, outline=INK)
        d.text((ex + 9, ez + 9), name[4:], font=tiny, fill=RED, anchor="la")
    ex, ez = X(xb) + 122, Z(-16.0)                                      # ext_base, from the forecourt
    d.ellipse([ex - 6, ez - 6, ex + 6, ez + 6], fill=RED, outline=INK)
    d.line([ex - 8, ez, X(xb) + 4, ez], fill=RED, width=2)
    d.text((ex, ez + 9), "ext_base", font=tiny, fill=RED, anchor="ma")
    d.text((ex, ez + 25), "（在前庭）", font=tiny, fill=RED, anchor="ma")

    def note(z, text, to, side="r"):
        x = xb + 0.2 if side == "r" else xa - 1.25
        d.line([X(x), Z(z), X(to[0]), Z(to[1])], fill=NOTE, width=1)
        d.text((X(x) + (3 if side == "r" else -3), Z(z)), text, font=small, fill=NOTE, anchor="lm" if side == "r" else "rm")

    note(Z0 - 0.6, "大理石配电板，三块", (PANELS[2][1], Z0 + 0.3))
    note(Z0 + 0.3, "细管上楼 ×2", (FEEDS[1], Z0 + 0.09))
    note(Z0 + 1.2, "比重计、量杯台", (12.8, Z0 + 0.3))
    note(TRAY_Z + 1.6, "授时室缆槽的底", (X1 + 1, TRAY_Z + 0.5))
    note(-21.4, "铁梁，四道，y 5", (X1 + 1, BEAMS[0] + 0.5))
    note(-19.8, "铁窗罩 y 3..4", (X1 + 0.5, -19.8))
    note(-14.4, "木门架，托铜排", (BANKS[1][1] + 1, GANTRIES[2]))
    note(-12.6, "铜排，一组一对", (BAR_X[3], -12.6))
    note(-11.3, "玻璃缸，两层", (ROWS[3] + 0.9, -11.3))
    note(ze - 0.2, "记录板", (10.28, ze + 0.07))
    note(Z1 - 0.3, "蒸馏水瓶", (12.85, Z1 - 0.2))
    note(Z0 + 0.1, "胶裙、手套", (3.2, Z0 + 0.08), "l")
    note(-17.5, "粗缆", (X0 + off, -17.5), "l")
    note(-13.5, "排水箅", (AISLE[0], BEAMS[2] + 0.5), "l")
    note(ze + 0.07, "禁火牌", (5.75, ze + 0.07), "l")
    note(Z1 + 0.4, "粗缆穿墙", (GLAND[0], Z1 + 0.9), "l")
    note(Z1 + 1.5, "铁门", (DOOR[0], Z1 + 1.5), "l")
    note(Z1 + 2.6, "星厅的配电盘", (2.0, Z1 + 2.2), "l")
    d.text((X(10.5), Z(Z1 + 3)), "星厅 北侧廊下", font=small, fill=NOTE, anchor="mm")
    return img


# ---- the sheet --------------------------------------------------------------------------------------------
def wrap(d, x, y, text, font, width, step, fill=NOTE):
    """Text set in lines no wider than `width`; returns the y under it."""
    row = ""
    for ch in text:
        if ch == "\n" or d.textlength(row + ch, font=font) > width:
            d.text((x, y), row, font=font, fill=fill)
            y += step
            row = "" if ch == "\n" else ch
        else:
            row += ch
    if row:
        d.text((x, y), row, font=font, fill=fill)
        y += step
    return y


def sheet(out):
    fonts = dict(title=ImageFont.truetype(FONT, 34), head=ImageFont.truetype(FONT, 22),
                 small=ImageFont.truetype(FONT, 17), tiny=ImageFont.truetype(FONT, 14))
    small = fonts["small"]
    model, table = build(), lightmap()
    w, h = 2366, 1600
    page = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(page)
    d.text((28, 14), "蓄电池室 · 草图一页", font=fonts["title"], fill=INK)
    d.text((372, 27), "interiors/batteryroom　北翼底层：x 2..13，z −25..−7，脚 y 0，净高 6 格　　stair c337，11-16　　"
           "纸上的研究，不是渲染。草稿：没交总监，卡已交回，留给接手的人", font=small, fill=NOTE)

    def head(x, y, text):
        d.text((x, y), text, font=fonts["head"], fill=INK)

    # one: the plan
    head(28, 68, "一　平面")
    drawing = plan(34, fonts)
    page.paste(drawing, (14, 100))
    y = 100 + drawing.size[1] + 8
    for text in (
        "红点是机位，黄圈是铁笼灯和它的光级，虚线是头顶的铁梁，打叉的格是铁窗罩。",
        "来电：粗缆从星厅配电盘背后穿南墙进来，贴着墙裙顶，沿西墙、北墙走进配电板背后。",
        "存电：两组架子四排缸，缸顶铅条一只连一只；每排在门口这头引上去，接到头顶的一对铜排。",
        "去电：铜排顺着架子直接进配电板两翼；板顶两根细管贴北墙上楼，对着授时室机柜的两根墩脚。",
        "窗：八个窗里侧各一只铁窗罩（两层铁楼梯块，实面朝玻璃），屋里的光到不了玻璃；"
        "ext_base 带屋、不带屋两张并排核，基座层一格不许变亮。",
        "数：实体约 100（上限 250）：架段 52、门架 8、铜排 4、引上条 4、板 3、指针 1、灯 3、吊杆 2、粗缆 6、"
        "细管 2、小件十来件。光三盏，8、7、8 级；夜光绿只在两只表盘上。在动：电流表指针慢摆。",
        "对口谈过的：门在 (7, 0..1, −6)，hall 两版都空着这一格，门我摆，过审以后 shell 开洞；"
        "m2 的缆槽底留在 z −24，两根细管对 (6, −25)、(9, −25)；空腔 y −1..5 里地面和四道梁归我铺。",
    ):
        y = wrap(d, 28, y, text, small, 770, 24) + 5

    # two: the hero
    x = 896
    head(x, 68, "二　主角：成排的玻璃缸，顶上一对铜排")
    a = hero().image(6)
    page.paste(a, (x, 104))
    under = wrap(d, x + a.size[0] + 16, 104,
                 "从走道看东边一组的南头。一格两只缸，上下两层；一组两排背靠背，每排 13 格，两组共 208 只。\n"
                 "模型一格一段（四只缸连架子），摆 52 次，三个变体错开放。\n"
                 "缸 7×9×11 像素：亮的缸沿和一条亮边，液面一条浅线，极板侧着朝走道，灰、棕、灰；缸顶铅条一只连一只。\n"
                 "深色木架，白瓷垫脚。上层缸沿在 1.8，液面线正在眼高。\n"
                 "梁下的立柱升上去成门架，白瓷瓶托着一对铜排（y 2.5..2.75）；南头每排引上一根。",
                 small, 700 - a.size[0] - 16, 23)
    y = max(104 + a.size[1], under) + 12
    b = section().image(3)
    page.paste(b, (x, y))
    y = wrap(d, x, y + b.size[1] + 6, "横剖，朝北看，切在一道梁下：两组架子夹着两格宽的走道，铁笼灯吊在走道正中，"
             "灯底 2.5。两边窗前是铁窗罩；西墙墙裙顶上那一点是粗缆。", small, 700, 23) + 10
    e = board().image(4)
    page.paste(e, (x, y))
    asks = wrap(d, x, y + e.size[1] + 6, "北墙。配电板 x 5.5..10.5，离墙六像素，立在铁腿上：中间一块正对走道，电压表、电流表"
                "（夜光绿表盘）和充电、放电换向闸刀；两翼各管一组，铜排从上面接进来，下面闸刀和瓷保险。"
                "板顶一盏壁装铁笼灯；两根细管上楼；粗缆从左边进；右边比重计台，左边胶裙和手套。", small, 700, 23) + 16

    # three: the views
    x, y = 1616, 68
    head(x, y, "三　三个机位各看到什么（盒子加光级，不是贴图）")
    y += 36
    says = {
        "int_door": "两组玻璃缸夹着走道退到底，头顶两对铜排收向尽头亮着的配电板和两只绿表盘。近处是两组架子的南头："
                    "缸的端面、禁火牌、记录板，引上条接到铜排；第一盏灯就在头顶前面。",
        "int_aisle": "缸在两肘边，看得见缸沿、液面线和极板；铜排和门架在头顶两侧；前面第二盏灯，尽头是板。",
        "int_board": "三块大理石板、两只绿表盘、换向闸刀；两对铜排从两边头顶接进两翼；细管上楼，粗缆从左边来。",
    }
    for name, what, eye, at in VIEWS:
        shot = picture(model, eye, at, (736, 414), table)
        page.paste(shot, (x, y))
        d.text((x, y + 420), f"{name}（{what}）", font=small, fill=INK)
        y = wrap(d, x, y + 444, says[name], fonts["tiny"], 736, 20, NOTE) + 12

    # four: what is still open
    x, y = 896, asks
    head(x, y, "四　没定的，要问总监")
    y += 34
    for text in (
        "1　走道上两盏要吊着的铁笼灯。lamps 家族里铁笼灯只有壁装的（cage），吊的只有敞口罩（pendant）。"
        "请 lamps 加一只吊式的，还是我把壁装的装在梁下的挂板上？",
        "2　铁窗罩（见平面第五条）这个办法行不行。",
        "3　过审以前，星厅北墙上要不要先立一扇关着的铁门？现在那面墙上没有门，护墙板是连着的。",
        "4　架子是模型，没有碰撞，人能穿过去（屏障的规矩不许这样用）。和别的屋的家具一样不管，行不行？",
        "5　文字：禁火牌用图形（划掉的火焰），表上只有 V、A，不写中文。",
        "6　这一稿自己看出来的毛病：板正中两只绿表加下面一根横把手，int_board、int_aisle 里远看是一张脸。"
        "表要错开（一大一小，或者三只），把手不要横在两只表的正下方。",
    ):
        y = wrap(d, x, y, text, small, 700, 23) + 6
    page.save(out)
    return out


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else HERE
    print(sheet(os.path.join(folder, "int-batteryroom-sketch.png")))
