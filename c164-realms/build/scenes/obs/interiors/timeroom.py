"""Work package interiors/timeroom: the time-service room (plan ART-PLAN 8, view V10).
Card: plan/packages/interiors/timeroom.md.

The room is the north wing's main floor: 12 wide (x 2..13), 19 long (z -25..-7), 7 high (feet at 7,
the ceiling block on 14). The door is in the south wall on the room's long axis (x 7..8), so what
is seen first from it is the far end wall. That is where the one star piece stands, the instrument
wall; everything else keeps to the long walls and leaves the way to it open.

What stands where (plan cells; north is -z, the camera of V10 looks north):

  instrument wall   a rack of panel blocks against the north wall (z -25), x 3..12, six rows high
                    under an iron cornice and a hood. It is laid like a small front: four piers of
                    louvres on a foot of drawers, a bank of valves glowing at the head of each, and
                    between them three bays two panels wide. The flank bays hold the line gear
                    (relays, pilot lamps and a dial, switches, fuses and a jack field), each in
                    its own order: the piers are the wall's symmetry, the bays are not mirror
                    images. The middle bay holds what there is one of (the nameplate and the
                    bell, the gauges and the register, the oscilloscope and the recorder). A
                    frieze of louvres runs under the cornice, and along the floor the bays stand
                    on louvres too: the drawers, with their brass pulls and labels, are the feet
                    of the piers only (a course of them from wall to wall was as busy with amber
                    as the instruments above it; review cr3-P4). rack_faults() says which rules
                    the wall is laid by.
  standard clocks   the rack stops one cell short of each long wall, which leaves a recess one cell
                    wide and one deep at each of its ends (x 2 and x 13). The back of each is
                    lined with a board of dark wood from the floor to the head course (the room's
                    own model): the stone of the end wall is the lightest thing the room has, and
                    beside the rack it would be looked at before the rack. A regulator clock
                    hangs on each board, its foot on the sill line, a shaded lamp over it: the two
                    clocks the service keeps. From the door both dials are in full view (the
                    rack's end hides a pixel and a half of each case), and the pendulums move on
                    either side of the rack; from the middle of the room the rack's ends hide half
                    of each clock, until one stands before a recess.
  console           a wooden shelf in front of the middle bay and the two piers beside it: the drum
                    recorder, the telegraph and its key stand on it, the operator sits in front of
                    it. Two drop lights hang over its two ends from the lip of the hood, each in
                    front of a pier, a block and a half over the shelf: the main light of the
                    room, on the faces at the height of the hand and on the shelf. The two jack
                    fields of the rack are the panels beside its ends; patch cords hang from them,
                    and the operator's mug stands by the key (the room's own models).
  message desk      under bay 6 of the east wall, a drop light on a long cord over the writer's
                    left hand; the telephone on the pier north of it, the pneumatic tube on the
                    pier south of it. The log lies under the lamp; on the right half of the top
                    the pad of message forms with a message begun, a written form waiting for
                    the tube, the spike with the day's slips (the room's own model).
  rating bench      under bay 5 of the west wall, a drop light over the left hand again, which is
                    where two box chronometers stand open, sent in to be rated against the
                    standard clocks (the room's own model); the log lies on the right, the
                    barometer hangs on the pier south of the bench.
  world clocks      five slave dials in a row on a dark board, on the blind stretch of the west wall
                    (the rotunda is behind it), over a low cabinet of drawers, a lamp over the
                    middle one. Their dials are level with the regulators'. They show the one time
                    every clock of the map is stopped at (the skeleton's CLOCK) in five places: the
                    hours differ, the minutes do not. These are the room's own models.
  south wall        card cabinets under a drawing west of the door, a coat stand east of it
  panelling         dark panels on every solid stretch of wall, from the floor to the ceiling: the
                    piers between the windows, the blind stretch of the west wall, the south wall
                    round the door; under the windows the one course below the sills. A corner
                    cell holds one panel and two walls want one: the south-west corner is a cased
                    riser (the lines to the building's slave dials go up in it), in the south-east
                    one the panel of the south wall stands edge on to the glass.
  cable ducts       in the floor: a grating along the foot of the rack from wall to wall, and a
                    line of riveted cover plates from under each end of the console down the
                    room, turning off to its desk. They are the two lines the floor has, they
                    run to the console, and where a line turns a desk stands: nowhere do two of
                    them cross. Under the grating lies an iron bed, one row down (y 5): the
                    cable trough the battery room below has under its ceiling along its north
                    wall, where its two risers come up at x 6 and x 9 (interiors/batteryroom,
                    c337); nothing else of the room reaches below its floor.
  ceiling           riveted beams across the room on the pilaster rows; each end sits in an iron
                    shoe at the head of its pier, the capital of the panelled pilaster

The sill line (y 8) is the line the room hangs on: the rack's foot course runs under it, the
console top, the top of the world clocks' cabinet and the feet of the two regulators are on it,
the desks stay below it.

Light: the room is dark and is lit by its lamps where somebody works, and by nothing else. The
lightmap takes little off a pale thing in the dark (a pale stone without a lamp is still lighter
than dark wood under one), so what is to sink is made dark and what is to be seen is light, and
only then lit: that is what the panelling and the boards in the recesses are for. Every lamp is a
shaded one (LAMPS) and hangs low over what it is for. A shade throws its light down, so the source
of a lamp is not offered at its bulb but under it, at the height of what it lights: over the shelf
of the console, in the cell a desk stands in, at the dial of a clock. The light lies in pools on
the floor and on the lower half of the walls; the heads of the windows stay out of it, and the
linings of the lit ones have what their own sources give them. The rack gets the most (12 on the faces at the height of the hand, 9 on its
frieze), a desk 8 and its chair 7, a clock 8 to 9. The lightmap is flat (a floor at 6 is hardly
darker than one at 10), so the pools are kept small and far apart: the floor rises from nothing at
the door to 3 between the desks and to 9 before the console, and leads to the rack. And the floor
is relaid in dark boards: in the shell's pale ones it was the lightest large thing of the room,
lit or not. The ceiling gets what the pools throw back and no more (BOUNCE): 3 to 5 over the
middle of the room, less towards the door and before the rack's own light, enough for its beams
and boards to be seen and not to be a black lid.
A window is not a light of the room: the ones the light line lights (sky/lights; bays 3 and 6
east, 3 and 5 west under the blue look) are lined on the room side by materials/windows and are
unlit glass from inside. The light line's sources of a lit window stand outside its glass, in the
opening of the stone leaf (10 there; c331): what comes through is 8 in the first cell behind the
glass and 3 on the room's long axis, no more than the lamp of the room that stands at that window
gives. For each of them has a lamp of the room within two cells, so that a lit window is a lamp
seen from outside: the lamps over the two regulators for the end windows, the drop lights over the
two desks for the others. Every source is offered to the light line
(sky/_lightkit); nothing is placed for good here. No block of the room stands in the first cell
behind the glass of a window (clear_cells()): the lining of a lit one lies on the glass there. The
two recesses are such cells; what hangs in them is display entities. The one block that does is
the last panel of the south wall (CORNER), edge on to the glass of east bay 7, which no look lights.

The room dresses the shell main/shell.py (c231) leaves: it lays no wall and no ceiling, and of the
floor only the boards anew, in the shell's own row. What other packages make is placed through
them when they are in the tree (PIECES: the furniture, the regulators and the barometer, the key
and the telephone, the books and the drawing) and is left out, or stood in for by a block, until
then. SLOTS says where the machines of machines/recorders go.

build() is what the master scene calls; it places nothing until MOVED_IN is set (the shell in the
master scene and the room past review). Until then the room lives in its box test scene,
build/scenes/obs_int_timeroom.
"""
import functools
import importlib
import math

from artkit import models as M
from artkit.blocks import st
from artkit.pixelart import Sprite

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..main import _plan as MP
from ..materials import panels
from ..props import _kit as K
from ..props import lamps

MOVED_IN = False
NAME = "interiors/timeroom"
PREFIX = "int_timeroom_"
PX = 1 / 16.0

# ---- the room (main/shell.ROOMS["time room"], c231; written from the skeleton until the shell is in the tree)
X0, X1 = S.ROOM_X                                   # 2..13
Z0, Z1 = S.pilaster_z(2) + 1, S.STAR_HALL_Z[0] - 1  # -25..-7
FEET = S.STAND                                      # 7
TOP = S.STAR_HALL_CEIL - 1                          # 13: the last clear row
FLOOR_Y = FEET - 1                                  # 6: the floor block
CEIL_Y = S.STAR_HALL_CEIL                           # 14: the ceiling block
SILL = S.WINDOW[0]                                  # 8: the sill line
DOOR_X = (7, 8)                                     # the door, in the wall on z -6
AXIS_X = S.mid(*DOOR_X)                             # 8.0: the long axis, between two cells
PIER_Z = tuple(z for z in range(Z0, Z1 + 1) if MP.on_pilaster(z))               # -22, -18, -14, -10
EAST_BAYS = tuple(b for b in range(1, S.N_BAYS + 1) if set(MP.window_rows(b)) <= set(range(Z0, Z1 + 1)))
WEST_BAYS = tuple(b for b in EAST_BAYS if all(abs(z - S.DOME_CENTRE[1]) > MP.WEST_BLIND_Z for z in MP.window_rows(b)))
BLIND_Z = (S.pilaster_z(max(WEST_BAYS)) + 1, Z1)    # -13..-7: the west wall with the rotunda behind it
NORTH, SOUTH, WEST, EAST = float(Z0), Z1 + 1.0, float(X0), X1 + 1.0     # the four wall faces: -25, -6, 2, 14

# ---- the instrument wall: top row first
RACK_Z = Z0                                         # -25
RACK_X = (X0 + 1, X1 - 1)                           # 3..12
PIER = ("tubes", "louvre", "louvre", "louvre", "drawers", "drawers")    # a pier: valves at its head, drawers at its foot
# The two flank bays hold the same line gear, and neither is the other's mirror image: where one
# has its dial the other has its lamps, a row higher or lower. A pair of the same face either side
# of the middle is a pair of eyes, and two faces that move would move as one (review c332, #54623).
# What shows light, the dial and the lamps, stands in the outer column of each; the inner columns
# are dark faces, and the drop lights of the console hang in front of them from where one stands.
FLANK_W = (                                         # the west flank bay: its outer column, its inner one
    ("louvre", "louvre"),
    ("dial", "relays"),
    ("bus_switch", "knife_switch"),
    ("pilot_lamps", "relays"),
    ("fuses", "patch_panel"),
    ("louvre", "louvre"),
)
FLANK_E = (                                         # the east flank bay: its inner column, its outer one
    ("louvre", "louvre"),
    ("bus_switch", "pilot_lamps"),
    ("relays", "knife_switch"),
    ("fuses", "dial"),
    ("patch_panel", "relays"),
    ("louvre", "louvre"),
)
MIDDLE = (                                          # the middle bay: what there is one of
    ("louvre", "louvre"),
    ("nameplate", "bell"),
    ("gauges", "counter"),
    ("scope", "recorder"),
    ("louvre", "louvre"),
    ("louvre", "louvre"),
)
# pier, west flank bay, pier, middle bay, pier, east flank bay, pier
RACK = [(p,) + w + (p,) + m + (p,) + e + (p,) for p, w, m, e in zip(PIER, FLANK_W, MIDDLE, FLANK_E)]
QUIET = ("louvre", "drawers")                       # faces with nothing to read on them: where the eye rests
PAIRED = QUIET + ("tubes", "patch_panel")           # what may stand as a pair either side of the middle: the quiet faces, the valves
#                                                     at the heads of the piers, the two jack fields at the ends of the console
REACH = 2                                           # an instrument has a quiet face within so many steps along its row
RACK_Y = FEET                                       # 7: the lowest row of panels stands on the floor
CORNICE_Y = RACK_Y + len(RACK)                      # 13
CONSOLE_X = (RACK_X[0] + 1 + len(FLANK_W[0]), RACK_X[1] - 1 - len(FLANK_E[0]))  # 6..9: the middle bay and the piers beside it
CONSOLE_Z = RACK_Z + 1                              # -24
KEY_X = CONSOLE_X[0] + 1                            # 7: the telegraph key's cell; the operator sits in front of it
DRUM_X = CONSOLE_X[1]                               # 9: the drum recorder's

# ---- the standard clocks, in the recesses the rack leaves at its two ends
REGULATOR_X = (S.mid(X0), S.mid(X1))                # 2.5 and 13.5
REGULATOR_FOOT = float(SILL)                        # 8.0; the clock is two blocks tall
REGULATOR_TOP = REGULATOR_FOOT + 2.0
REGULATOR_DIAL = 24.5                               # px: the middle of a regulator's dial above its foot (props/instruments' CLOCK_DIAL_Y)
DIAL_Y = REGULATOR_FOOT + REGULATOR_DIAL * PX       # 9.53: the middle of a regulator's dial, and of every dial of the room
BACK_T = 1.5 * PX                                   # the board at the back of a recess, off the wall: a pixel of board, half a pixel of frame
BACK = (3, 3, 1)                                    # blocks: the lengths that board is made of, from the floor to the ceiling: the panel the clock
#                                                     hangs on, the panel its lamp hangs on, the frieze beside the rack's cornice
BACK_HELD = DIAL_Y                                  # the height all the lengths of a board are held from: one cell lights the whole board
NICHE = NORTH + BACK_T                              # the face a regulator and its lamp hang on

# ---- along the long walls
DESK_BAY, BENCH_BAY = 6, 5                          # the message desk's window (east), the rating bench's (west)
WAINSCOT_T = 3 * PX                                 # a panel of the wainscot, off its wall
PANEL_TOP = TOP                                     # 13: the panelling runs up to the ceiling; at a beam's end its last row is the beam's shoe
PANEL_E, PANEL_W, PANEL_S = EAST - WAINSCOT_T, WEST + WAINSCOT_T, SOUTH - WAINSCOT_T      # the faces of the panelling: what hangs on a panelled wall hangs on these
DOOR_TOP = FEET + 2                                 # 9: the last row of the doorway
RISER = (X0, Z1)                                    # the south-west corner cell: the cased riser
CORNER = (X1, Z1)                                   # the south-east corner cell: the south wall's panel, not the east wall's
DESK_DEEP = 14 * PX                                 # props/furniture's writing desk, back to front
DESK_X = PANEL_E - DESK_DEEP / 2                    # 13.375: its back against the wainscot
BENCH_X = PANEL_W + DESK_DEEP / 2                   # 2.625
DESK_Z = S.mid(MP.window_rows(DESK_BAY)[0], MP.window_rows(DESK_BAY)[-1])       # -11.5: under the middle of its window
BENCH_Z = S.mid(MP.window_rows(BENCH_BAY)[0], MP.window_rows(BENCH_BAY)[-1])    # -15.5
SEAT = 1.075                                        # from the middle of a desk to the middle of its chair
CABINET_Z = SOUTH - 0.6                             # -6.6: where a cabinet stands with its back to the south wall
DUCT_X = (CONSOLE_X[0], CONSOLE_X[1])               # 6 and 9: the two lines of the floor, under the two ends of the console and in line with the two piers
DUCTS = (                                           # runs of duct in the floor, cell to cell; the two lines turn off to their desks at (6, -16) and (9, -12)
    ((X0, CONSOLE_Z), (X1, CONSOLE_Z)),                                         # along the foot of the rack, wall to wall
    ((DUCT_X[0], CONSOLE_Z), (DUCT_X[0], MP.window_rows(BENCH_BAY)[1])),        # from the west end of the console down the room
    ((DUCT_X[0], MP.window_rows(BENCH_BAY)[1]), (X0, MP.window_rows(BENCH_BAY)[1])),    # ... and west to under the rating bench
    ((DUCT_X[1], CONSOLE_Z), (DUCT_X[1], MP.window_rows(DESK_BAY)[1])),         # from the east end of the console down the room
    ((DUCT_X[1], MP.window_rows(DESK_BAY)[1]), (X1, MP.window_rows(DESK_BAY)[1])),      # ... and east to under the message desk
)

# ---- the world clocks: a row of slave dials on one board, on the blind stretch of the west wall, one to a cell
CLOCK = getattr(S, "CLOCK", (7, 55))                # the time every clock of the map is stopped at (A0, g2 #34136)
CLOCK_Z = (BLIND_Z[0] + 1, BLIND_Z[1] - 1)          # -12..-8
WORLD = (5, 2, 0, -3, -5)                           # hours off the station's time, from the north end of the row: seen from the room the west is on the left
CASE_R = 6.0                                        # px: the radius of a world clock's case
BOARD = (16.0, 9.0, 11.0)                           # px: the length of board behind one dial: as wide as a cell, so far above the dial's middle, so far below it
INK = P.RAMPS["iron"][1]
MARK = P.RAMPS["iron"][5]                           # what is printed on a dial, as props/instruments prints its regulator's: lighter than
#                                                     the hands, so that the hands are what is read
DIAL = (                                            # nine pixels across: twelve marks and the hub; the face of
    "..kckck..",                                    # props/instruments' regulator without its luminous quarters
    ".ccccccc.",
    "kccccccck",
    "ccccccccc",
    "kcccbccck",
    "ccccccccc",
    "kccccccck",
    ".dcccccd.",
    "..kdkdk..",
)
DIAL_COLOURS = dict(c=P.RAMPS["porcelain"][3], d=P.RAMPS["porcelain"][2], k=MARK, h=P.RAMPS["iron"][0], b=P.RAMPS["brass"][3])

# ---- the patch cords: at the jack fields of the rack, which are the panels beside the two ends of the console
JACK_FIELDS = tuple((RACK_X[0] + i, CORNICE_Y - 1 - j)                              # (5, 8) and (10, 8): the cells, x and y
                    for j, row in enumerate(RACK) for i, name in enumerate(row) if name == "patch_panel")
JACKS = (-4.0, 0.0, 4.0)                            # px: a field's three columns of jacks, and its three rows, about the middle of its face (materials/panels)
CORDS = {                                           # for a field: the two jacks a cord is looped between and how far it sags, the jack a cord hangs from and how long it is (px)
    "w": dict(loop=(JACKS[0], JACKS[1], 7.0), drop=(JACKS[2], 13.0)),
    "e": dict(loop=(JACKS[2], JACKS[1], 5.0), drop=(JACKS[0], 9.0)),
}
CORD_R = 0.5                                        # px: half the thickness of a cord
PLUG = 2.0                                          # px: how far a plug stands out of its jack

# ---- the chronometers on the rating bench, sent in to be rated against the standard clocks
CHRONOMETERS = ((-11.5, 0.5, 4.0), (-5.5, 0.5, -3.0))       # px along the bench from its middle (the sitter's left is minus), px towards the sitter, degrees turned
CHRONO_BOX = (5.0, 3.0)                             # px: a chronometer's box, square, and its height
CHRONO_DIAL = ("wbbbw", "bcccb", "bckcb", "bcccb", "wbbbw")     # looked into from above: the dial in its brass bowl
CHRONO_LID = ("wwwww", "wlllw", "wlllw", "wlllw", "wwwww")      # the inside of the open lid: the rating certificate
CHRONO_COLOURS = dict(w=P.RAMPS["dark_wood"][3], b=P.RAMPS["brass"][3], c=P.RAMPS["porcelain"][3], k=INK, l=P.RAMPS["cream"][2])
BOARD_TOP = 1.0                                     # blocks above the floor: the top of the board that stands in for a desk

# ---- the operator's mug on the console, east of the key: the hand that does not key reaches it
MUG = (S.mid(KEY_X) + 0.72, CONSOLE_Z + 0.66, 35.0) # x, z, degrees its handle is turned off the east

# ---- the paper of the message desk, on the right half of its top (the log book lies on the left, under the lamp);
# px from the middle of the desk top: to the sitter's right, towards the sitter
FORM = (4.0, 6.0)                                   # a message form, across and from its head to its foot
PAD = (4.5, 2.5, 6.0)                               # the pad of forms before the writing hand, and the degrees it is turned
SHEET = (9.8, 3.2, -14.0)                           # the form that is written and waits for the tube
SPIKE = (13.2, -1.5)                                # the spike the day's slips are on, before the desk's right stationery drawer
SLIPS = (10.0, -35.0, 50.0, -10.0, 25.0)            # degrees each slip on the spike is turned, the lowest first
INKWELL = (5.0, -4.5)                               # at the back, between the two stationery drawers
PAPER_COLOURS = dict(p=P.RAMPS["cream"][3], e=P.RAMPS["enamel"][1], i=P.RAMPS["cream"][0])  # props/paper's page: the printed
#                                                     heading in chart blue, what is written a soft line

# ---- light: what the room asks of the light line (level, rank); the lamps are props/lamps models
LAMPS = "b"                 # every lamp of the room is the shaded one (props/lamps' version B, the enamel cone), whatever the
#                             map's default: a shade keeps a lamp's glow to what is under it, and the opal globe of version A
#                             is itself the lightest thing in a dark room, six times over
CONSOLE_LAMP = (12, 2)      # the two drop lights over the ends of the console: the main light, on the instrument wall
DESK_LAMP = (8, 3)          # the drop lights over the message desk and the rating bench: 8 on the desk, 7 at its chair, and five
#                             cells on, on the room's long axis, 3 (at 10 the whole floor was lit, as light as the rack)
REGULATOR_LAMP = (9, 2)     # the bracket lamps over the two standard clocks
CLOCK_LAMP = (9, 2)         # the bracket lamp over the world clocks: 8 on the middle dial, 6 on the end ones
OVER = 20 * PX              # a bracket's arm above the top of what it hangs over: the shade ends half a block over it, a lamp
#                             over a clock and not a hat on it (at 12 px the pale inside of the shade sat on the dial's rim)
CONSOLE_HANG = FEET + 3.5   # 10.5: where the drop lights of the console end and their lamps hang; the shades end at 9.56, a block
#                             and a half over the shelf and a block over the eye: from the room one looks at the blue of the shade,
#                             not into its lit inside
DESK_HANG = FEET + 3.25     # 10.25: the same over a desk; the shade ends at 9.3, a block and a half over the desk top
LEFT = 0.5                  # a desk's drop light hangs this far left of the middle, as the sitter sees it: over the hand that does not write
LIP = 1 * PX                # the drop lights of the console hang this far inside the lip of the hood
CORD = lamps.PREFIX + "wire"                        # the cord of a drop light: props/lamps' cable, stretched from where it is fixed
# where the source of each lamp is offered (the room's cells): under the shade, at what the lamp is for
CONSOLE_LIGHT = tuple((x, SILL + 1, CONSOLE_Z) for x in DUCT_X)                     # (6, 9, -24), (9, 9, -24): over the shelf, at the height of the hand
REGULATOR_LIGHT = tuple((int(math.floor(x)), SILL, Z0) for x in REGULATOR_X)        # (2, 8, -25), (13, 8, -25): the cell the clock hangs in
DESK_LIGHT = (int(math.floor(DESK_X)), FEET, int(math.floor(DESK_Z)))               # (13, 7, -12): the cell the desk stands in, against its wall and
BENCH_LIGHT = (int(math.floor(BENCH_X)), FEET, int(math.floor(BENCH_Z)))            # (2, 7, -16)    as far from the middle of the room as a cell is
#                                                                                     (while a board stands in for a desk that cell is
#                                                                                     taken, and the light line puts the source at the chair)
CLOCK_LIGHT = (X0 + 1, int(math.floor(DIAL_Y)), int(math.floor(S.mid(*CLOCK_Z))))   # (3, 9, -10): before the middle dial (a panel stands in the dial's own cell)
# What a lit desk and a lit clock board throw back at the ceiling: a weak source in the row under the ceiling, two
# cells out from the wall the lamp is at. With every source low the boards and the beams over the middle of the
# room were dead black (under 0.03 on four tenths of the ceiling of V10; review cr3-P4); these leave the ceiling
# dark and its beams to be seen: along the room's axis 3 to 5 between the two desks, 1 to 2 at the next beam
# towards the rack, 7 at the rack with the console's own light. The two desks stand in neighbouring bays, one
# at each long wall, and their two sources stand either side of the beam between those bays: the beam over the
# middle of the room, the one V10 has overhead, is lit from the west on its north side and from the east on its
# south side. Each is 3 cells or more from the lining of a lit window, which they leave at what its own sources
# give it.
BOUNCE = (8, 3)             # over the message desk and over the rating bench
CLOCK_BOUNCE = (7, 3)       # over the world clocks
assert DESK_BAY == BENCH_BAY + 1, "the two desks stand in neighbouring bays"
MID_BEAM = S.pilaster_z(BENCH_BAY)                                                  # -14: the beam between the two desks' bays
DESK_BOUNCE = (X1 - 2, TOP, MID_BEAM + 1)                                           # (11, 13, -13)
BENCH_BOUNCE = (X0 + 2, TOP, MID_BEAM - 1)                                          # (4, 13, -15)
CLOCKS_BOUNCE = (X0 + 2, TOP, int(math.floor(S.mid(*CLOCK_Z))) + 1)                 # (4, 13, -9)
assert not {cell[2] for cell in (DESK_BOUNCE, BENCH_BOUNCE, CLOCKS_BOUNCE)} & set(PIER_Z), "a beam lies in a pier's row"


def rack_faults(rows=None):
    """What a wall of panels breaks of the rules the instrument wall is laid by: sentences, none
    when it keeps them. `rows` is the wall, top row first; left out, the rack.

    The rules are the ones the review of the panels' own test wall left (materials/panels keeps
    them for its bay in obs_mat_panels.faults):
      - every kind of panel is on the wall, the nameplate once;
      - a quiet face, a louvre or a drawer front, at most REACH steps from every instrument along
        its row, so no row is one unbroken run of instruments;
      - no instrument beside or above another of its kind: two white rounds side by side are a
        pair of eyes;
      - of the light faces (dial, gauges, recorder) no two beside or above each other, and of the
        lit ones (valves, oscilloscope, pilot lamps) none beside or above another lit face;
      - no instrument at the mirror image of another of its kind in its row (PAIRED says which
        faces may: the quiet ones, the valves of the piers, the two jack fields)."""
    rows = RACK if rows is None else rows
    light, lit = panels.RANKS["light"], panels.RANKS["lit"]
    wrong = [f"no {name} on the wall" for name in sorted(set(B.PANELS) - {name for row in rows for name in row})]
    plates = sum(row.count("nameplate") for row in rows)
    if plates != 1:
        wrong.append(f"{plates} nameplates on the wall")
    for j, row in enumerate(rows):
        for i, name in enumerate(row[:len(row) // 2]):
            if name not in PAIRED and row[-1 - i] == name:
                wrong.append(f"row {j}, columns {i} and {len(row) - 1 - i}: a {name} and its mirror image")
        for i, name in enumerate(row):
            if name in QUIET:
                continue
            if not any(near in QUIET for near in row[max(0, i - REACH):i + REACH + 1]):
                wrong.append(f"row {j}, column {i}: no quiet face within {REACH} steps of the {name}")
            beside = [(row[i + 1], "beside")] if i + 1 < len(row) else []
            under = [(rows[j + 1][i], "above")] if j + 1 < len(rows) else []
            for other, how in beside + under:
                if name == other or (name in light and other in light) or (name in lit and other in lit):
                    wrong.append(f"row {j}, column {i}: {name} {how} {other}")
    return wrong


assert not rack_faults(), "the instrument wall breaks the rules it is laid by:\n  " + "\n  ".join(rack_faults())
assert len(WORLD) == CLOCK_Z[1] - CLOCK_Z[0] + 1, "one world clock to a cell"


def pier(bay, end):
    """The middle, along z, of the pier at the north (end -1) or the south (end 1) of a bay."""
    return S.mid(S.pilaster_z(bay - 1 if end < 0 else bay))


def piece(package, kind, where, on=None, **how):
    """One thing of another package: scenes.obs.props.<package>.place(canvas, kind, where, **how).
    `on` names (package, kind) of the piece it stands on: it is placed only with that one, and the
    height of that one's top (its package's TOP) is added to where."""
    return dict(package=package, kind=kind, where=where, on=on, how=how)


# ---- what the room takes from other packages. `where` is what their place() asks for: the middle of
# the foot of a standing piece, the point on the wall face behind the foot of a hanging one, the
# middle of a picture; facing is the way the piece's front, or the wall face it hangs on, looks.
ON_DESK = ("furniture", "writing_desk")
PIECES = (
    # props/furniture (c179)
    piece("furniture", "stool", (S.mid(KEY_X), FEET, CONSOLE_Z + 1.5), facing="north"),
    piece("furniture", "writing_desk", (DESK_X, FEET, DESK_Z), facing="west"),
    piece("furniture", "swivel_chair", (DESK_X - SEAT, FEET, DESK_Z), yaw=K.FACING["east"] + 25.0),   # pushed back, half turned
    piece("furniture", "writing_desk", (BENCH_X, FEET, BENCH_Z), facing="east"),
    piece("furniture", "swivel_chair", (BENCH_X + SEAT, FEET, BENCH_Z), facing="west"),
    piece("furniture", "card_cabinet", (X0 + 2.5, FEET, CABINET_Z), facing="north"),
    piece("furniture", "card_cabinet", (X0 + 3.5, FEET, CABINET_Z), facing="north"),
    piece("furniture", "coat_stand", (DOOR_X[1] + 1.6, FEET, CABINET_Z), facing="north"),
    # props/instruments (c199)
    piece("instruments", "regulator_clock", (REGULATOR_X[0], REGULATOR_FOOT, NICHE), facing="south"),
    piece("instruments", "regulator_clock", (REGULATOR_X[1], REGULATOR_FOOT, NICHE), facing="south"),
    piece("instruments", "barometer", (PANEL_W, SILL + 0.25, pier(BENCH_BAY, 1)), facing="east"),
    # props/electrics (c242)
    piece("electrics", "telegraph_key", (S.mid(KEY_X), float(SILL), CONSOLE_Z + 0.65), facing="south"),
    piece("electrics", "wall_phone", (PANEL_E, SILL + 0.2, pier(DESK_BAY, -1)), facing="west"),   # on the pier north of the desk
    # props/paper (c197)
    piece("paper", "logbook", (BENCH_X + 0.125, FEET, BENCH_Z - 0.2), on=ON_DESK, yaw=K.FACING["east"] + 8.0),
    piece("paper", "logbook_shut", (DESK_X - 0.09375, FEET, DESK_Z - 0.2), on=ON_DESK, yaw=K.FACING["west"] - 15.0),
    piece("paper", "blueprint", (X0 + 3.0, FEET + 2.625, PANEL_S), facing="north"),               # pinned over the card cabinets
)

# ---- where the machines of machines/recorders go (scene coordinates; facing is the way the thing looks)
SLOTS = {
    "drum": dict(pos=(S.mid(DRUM_X), float(SILL), S.mid(CONSOLE_Z)), facing="south",
                 note="the drum recorder, on the console's east end; its drum turns"),
    "telegraph": dict(pos=(S.mid(CONSOLE_X[0]), float(SILL), S.mid(CONSOLE_Z)), facing="south",
                      note="sounder and tape reel, on the console west of the key; the tape runs east, to the drum"),
    "tube": dict(pos=(PANEL_E, float(SILL), pier(DESK_BAY, 1)), facing="west",
                 note="the pneumatic tube: down the pier south of the message desk, from the ceiling to a terminal"),
}


# ---- the room's own models: the world clocks ----------------------------------------------------------
def hands(rows, hour, minute):
    """A dial with its hands drawn in from the middle, the way props/instruments draws its clock's:
    the hour hand two pixels long, the minute hand three, a pixel to each step along the way the
    hand leans most."""
    grid = [list(row) for row in rows]
    mid = len(rows) // 2
    for turn, length in (((hour % 12 + minute / 60.0) / 12.0, 2), (minute / 60.0, 3)):
        dx, dy = math.sin(2.0 * math.pi * turn), -math.cos(2.0 * math.pi * turn)
        for i in range(1, length + 1):
            if abs(dx) > abs(dy):
                x, y = mid + (i if dx > 0 else -i), int(round(mid + i * dy / abs(dx)))
            else:
                x, y = int(round(mid + i * dx / abs(dy))), mid + (i if dy > 0 else -i)
            grid[y][x] = "h"
    return ["".join(row) for row in grid]


def clock_name(offset):
    """The model of the world clock that is `offset` hours off the station's time: ahead of it to
    the east, behind it to the west."""
    return PREFIX + ("clock_home" if not offset else f"clock_{'e' if offset > 0 else 'w'}{abs(offset)}")


def _world_clock(offset):
    """A world clock: a round slave dial on its length of the clock board. The dial is made like the
    head of props/instruments' barometer (a turned wooden case, a brass bezel, the nine-pixel
    dial). The board is as wide as a cell, so the clocks of a row stand on one board: a plain dark
    band across the panelling, which makes the five dials one row and not five things on a wall.
    Under the dial a brass label for the place whose time it keeps. The hands stand at the map's
    one time, `offset` hours on. Anchor: the point on the wall behind the middle of the dial."""
    name = clock_name(offset)
    wide, up, down = BOARD
    m = M.Model(name)
    m.box((-wide / 2.0, -down, 0.0), (wide / 2.0, up, 1.0), P.mat("dark_wood", base=1), skip="n", grain="x")   # the board
    m.tube("z", (0, 0), 0.0, 3.0, CASE_R, P.mat("dark_wood"), sides=16, cap=K.flat("dark_wood", 3))            # the case
    m.ring("z", (0, 0, 3.5), 5.0, 1.5, 1.0, K.BRASS, sides=16)                                                # the bezel
    half = len(DIAL) / 2.0
    face = Sprite(name + "_dial", hands(DIAL, CLOCK[0] + offset, CLOCK[1]), DIAL_COLOURS)
    m.box((-half, -half, 3.25), (half, half, 3.5), K.flat("porcelain", 3), skip="nudew", faces={"s": face})
    m.box((-2.5, -CASE_R - 3.5, 1.0), (2.5, -CASE_R - 1.5, 1.5), K.BRASS_D, grain="x")                        # the label
    return m


def cords_name(side):
    return PREFIX + "cords_" + side


def _cords(side):
    """The patch cords of one jack field, for the face of its panel: in the field's lowest row a
    cord looped from one jack to the next, and a cord hanging from the third jack with its free
    plug at its end, on the side of the console. They are the cream of the cord painted on the
    panel. Anchor: the middle of the panel's face."""
    (xa, xb, sag), (xd, length) = CORDS[side]["loop"], CORDS[side]["drop"]
    cord, sleeve = K.flat("cream", 1), K.flat("cream", 3)
    row, z = JACKS[0], PLUG + CORD_R
    top = row - 1.5                                 # where a cord has turned down out of its plug
    m = M.Model(cords_name(side))
    for x in (xa, xb, xd):
        m.box((x - 1.0, row - 1.0, 0.0), (x + 1.0, row + 1.0, PLUG), sleeve)                        # a plug in its jack
    mid, half = (xa + xb) / 2.0, (xb - xa) / 2.0
    loop = [(mid + half * math.sin(math.radians(a)), top - sag * math.cos(math.radians(a)), z) for a in range(-90, 91, 30)]
    m.hose([(xa, row, PLUG)] + loop + [(xb, row, PLUG)], CORD_R, cord, sides=4)
    lean = 0.4 if xd > 0 else -0.4                  # the hanging cord leans a little out of the field, towards the console
    foot = row - length
    m.hose([(xd, row, PLUG), (xd + lean / 2.0, top, z), (xd + lean, (row + foot) / 2.0, z), (xd + lean, foot, z)], CORD_R, cord, sides=4)
    m.tube("y", (xd + lean, z), foot - 3.0, foot, 1.0, sleeve)                                      # its free plug
    m.tube("y", (xd + lean, z), foot - 4.5, foot - 3.0, 0.5, K.BRASS)                               # the plug's tip
    return m


def _chronometer():
    """A box chronometer standing open on the bench: a square wooden box, in it the dial in its
    brass bowl, looking up; the lid stands open at the back with the rating certificate inside it.
    Anchor: the middle of its foot; its front is the side the lid opens to."""
    name = PREFIX + "chronometer"
    side, high = CHRONO_BOX
    half = side / 2.0
    wood = P.mat("dark_wood", base=3)
    m = M.Model(name)
    m.box((-half, 0.0, -half), (half, high, half), wood, faces={"u": Sprite(name + "_dial", CHRONO_DIAL, CHRONO_COLOURS)})
    m.box((-half, high, -half - 0.5), (half, high + side, -half), wood,
          faces={"s": Sprite(name + "_lid", CHRONO_LID, CHRONO_COLOURS)})                           # the lid
    return m


def _mug():
    """An enamel mug: the blue of the lamps' shades with their pale rolled rim, what is left in it
    dark. It is the one thing in the room that is nobody's instrument: somebody is on watch here.
    Dark on purpose: a white one is a white dot on the console from the door. Anchor: the middle
    of its foot; the handle is on its +x side."""
    m = M.Model(PREFIX + "mug")
    m.tube("y", (0.0, 0.0), 0.0, 3.0, 1.5, K.ENAMEL, sides=8, cap=K.flat("dark_wood", 0))
    m.ring("y", (0.0, 2.9, 0.0), 1.45, 0.3, 0.3, K.flat("cream", 2), sides=8)               # the rim
    m.ring("z", (1.9, 1.5, 0.0), 0.8, 0.4, 0.5, K.ENAMEL, sides=8, arc=(-90.0, 90.0))       # the handle
    return m


def _forms():
    """What lies on the message desk besides the log: a pad of message forms with the pencil across
    it (a message begun), a written form beside it, the spike with the day's slips, an inkwell. The
    forms are props/paper's page, cream with a heading in chart blue. They are the light things
    under the desk's lamp: the lamp is seen to light something. Anchor: the middle of the desk top;
    +x is the sitter's right, +z towards the sitter."""
    name = PREFIX + "forms"
    wide, deep = FORM[0] / 2.0, FORM[1] / 2.0
    edge, top = K.CREAM, K.flat("cream", 3)

    def face(tag, rows):
        return Sprite(f"{name}_{tag}", rows, PAPER_COLOURS)

    m = M.Model(name)
    x, z, turn = PAD
    m.box((x - wide, 0.0, z - deep), (x + wide, 1.0, z + deep), edge, rot=("y", turn, (x, 0.0, z)), skip="d",
          faces={"u": face("pad", ["eeee", "pppp", "iiip", "pppp", "iipp", "pppp"])})
    m.beam((x - 1.6, 1.25, z + 2.2), (x + 2.6, 1.25, z - 1.2), 0.5, 0.5, K.flat("brass", 3))        # the pencil
    x, z, turn = SHEET
    m.box((x - wide, 0.0, z - deep), (x + wide, 0.15, z + deep), top, rot=("y", turn, (x, 0.0, z)), skip="d",
          faces={"u": face("sheet", ["eeee", "pppp", "iiii", "iiip", "pppp", "ppii"])})
    x, z = SPIKE
    m.tube("y", (x, z), 0.0, 0.5, 1.25, K.IRON_D, sides=8)
    m.tube("y", (x, z), 0.5, 7.0, 0.25, K.IRON, sides=4)
    for i, turn in enumerate(SLIPS):
        y = 0.6 + 0.45 * i
        last = i == len(SLIPS) - 1
        m.box((x - 1.5, y, z - 1.0), (x + 1.5, y + 0.2, z + 1.0), K.flat("cream", 3 if i % 2 == 0 else 2),
              rot=("y", turn, (x, y, z)), faces={"u": face("slip", ["eee", "iip"])} if last else None)
    x, z = INKWELL
    m.box((x - 1.0, 0.0, z - 1.0), (x + 1.0, 1.5, z + 1.0), K.flat("enamel", 0), skip="d")
    m.tube("y", (x, z), 1.5, 2.0, 0.5, K.BRASS, sides=4)
    return m


def back_name(i):
    return f"{PREFIX}back_{i}"


def _back(i):
    """One length of the board that lines the back of a recess, the i-th from the floor: a board of
    dark wood as wide as the recess in a frame of stiles and rails, a panel of the wainscot as tall
    as BACK says. All the lengths of a board are held from one point, the point on the wall behind
    the middle of the regulator's dial: one cell lights the board from the floor to the ceiling,
    and no step of light shows where two lengths meet. Anchor: that point."""
    foot = (FEET + sum(BACK[:i]) - BACK_HELD) * 16.0
    top = foot + BACK[i] * 16.0
    board, frame = P.mat("dark_wood", base=1), P.mat("dark_wood", base=2)
    m = M.Model(back_name(i))
    m.box((-8.0, foot, 0.0), (8.0, top, 1.0), board, skip="n", grain="y")
    for x in (-8.0, 6.0):
        m.box((x, foot, 1.0), (x + 2.0, top, 1.5), frame, grain="y")            # the stiles
    for y in (foot, top - 2.0):
        m.box((-6.0, y, 1.0), (6.0, y + 2.0, 1.5), frame, grain="x")            # the rails
    return m


@functools.lru_cache(maxsize=None)
def _models():
    out = {clock_name(offset): _world_clock(offset) for offset in WORLD}
    out.update({cords_name(side): _cords(side) for side in CORDS})
    out.update({back_name(i): _back(i) for i in range(len(BACK))})
    out[PREFIX + "chronometer"] = _chronometer()
    out[PREFIX + "mug"] = _mug()
    out[PREFIX + "forms"] = _forms()
    return out


def models():
    """The room's own models: the five world clocks, the patch cords of the two jack fields, the
    boards at the backs of the two recesses, the chronometer of the rating bench, the mug on the
    console and the paper of the message desk. Its lamps are props/lamps', its machines
    machines/recorders', the rest the packages' named in PIECES."""
    return dict(_models())


# ---- the other lines' pieces --------------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def theirs(package):
    """The package scenes.obs.props.<package> of another line, or None while it is not in the tree."""
    full = f"{__package__.rsplit('.', 1)[0]}.props.{package}"
    try:
        return importlib.import_module(full)
    except ModuleNotFoundError as missing:
        if missing.name != full:
            raise
        return None


def their_models():
    """The models of the pieces of other packages the room places: what a test scene packs besides
    the lamps and the room's own (the master scene collects every package's models itself)."""
    out = {}
    for package in sorted({p["package"] for p in PIECES}):
        module = theirs(package)
        if module is not None:
            out.update(module.models())
    return out


def cells(run):
    """The cells of a straight run of the plan, both ends included."""
    (xa, za), (xb, zb) = run
    return [(x, z) for x in range(min(xa, xb), max(xa, xb) + 1) for z in range(min(za, zb), max(za, zb) + 1)]


def duct_cells():
    return sorted({c for run in DUCTS for c in cells(run)})


def grated(cell):
    """Is a cell of the ducts an open grating? The run at the foot of the rack is, where the cables
    come up into it; the rest lies under riveted cover plates. (The two bends were gratings too,
    each with a block of iron bed under it: two lone blocks under the ceiling of the battery room,
    over its racks, which read as nothing from below -- c337, 11-16.)"""
    return cell[1] == CONSOLE_Z


def clear_cells():
    """The cells no block of the room stands in: the first cell behind the glass of every window of
    the long walls, [(x, y, z)]. The lining of a lit window lies on its glass there."""
    out = []
    for bays, x in ((EAST_BAYS, X1), (WEST_BAYS, X0)):
        for bay in bays:
            out += [(x, y, z) for z in MP.window_rows(bay) for y in range(S.WINDOW[0], S.WINDOW[1] + 1)]
    return out


def panel(side):
    """A panel of the wainscot standing on that side of its cell."""
    back = {"north": "south", "south": "north", "west": "east", "east": "west"}[side]
    return st(B.WAINSCOT, facing=back, half="bottom", open="true")     # it stands on the side it turns its back to


def build_timeroom(c, origin=(0, 0, 0), roles=B):
    """Dress the room standing at `origin`. Returns dict(entities=<display entities placed>,
    lights=[((x, y, z), level, why)]): the light sources it has offered to the light line."""
    ox, oy, oz = origin
    lights, n = [], 0

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    def lamp(kind, pos, ask, why, at, **how):
        """A lamp of props/lamps. Its light is offered in the cell `at` (the room's own cells):
        under its shade, not at its bulb."""
        level, rank = ask
        cell = (ox + at[0], oy + at[1], oz + at[2])
        lights.append((cell, level, f"{NAME}:{why}"))
        _offer(c, cell, level, f"{NAME}:{why}", rank)
        return lamps.place(c, kind, pos, origin=origin, light=False, version=LAMPS, **how)

    def drop(x, z, top, hang, ask, why, at):
        """A drop light: a cord from where it is fixed, at the height `top`, down to `hang`, and a
        pendant on its end."""
        a, b = (ox + x, oy + top - K.NUDGE, oz + z), (ox + x, oy + hang, oz + z)
        c.add_entity(*a, M.between(lamps.models()[CORD], a, b))
        return 1 + lamp("pendant", (x, hang, z), ask, why, at)

    def bounce(at, ask, why):
        """What a lamp's pool throws back at the ceiling: a source and no lamp."""
        level, rank = ask
        cell = (ox + at[0], oy + at[1], oz + at[2])
        lights.append((cell, level, f"{NAME}:{why}"))
        _offer(c, cell, level, f"{NAME}:{why}", rank)

    # ---- the floor: dark boards over the pale ones of the shell. The floor is a quarter of what one
    # sees from the door; in the shell's boards it was the lightest large thing of the room, lighter
    # than the rack, lit or not (review cr3-P4)
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            put(x, FLOOR_Y, z, roles.DARK_WOOD.block)

    # ---- the instrument wall: six rows of panels, the cornice, the hood over the faces
    for j, row in enumerate(RACK[::-1]):
        for i, name in enumerate(row):
            put(RACK_X[0] + i, RACK_Y + j, RACK_Z, st(roles.PANELS[name], facing="south"))
    for x in range(RACK_X[0], RACK_X[1] + 1):
        put(x, CORNICE_Y, RACK_Z, roles.IRON_RIVETED.block)
        put(x, CORNICE_Y, CONSOLE_Z, st(roles.IRON_RIVETED.slab, type="top"))

    # ---- the console, and what stands on it until machines/recorders and props/electrics bring the real
    # things; its two drop lights hang from the lip of the hood
    for x in range(CONSOLE_X[0], CONSOLE_X[1] + 1):
        put(x, FEET, CONSOLE_Z, st(roles.DARK_WOOD.slab, type="top"))
    put(DRUM_X, SILL, CONSOLE_Z, st(roles.BRASS_PLATE.slab, type="bottom"))                 # the drum
    if theirs("electrics") is None:
        put(KEY_X, SILL, CONSOLE_Z, st(roles.BRASS_BUTTON, face="floor", facing="north"))   # the key
    for x, side, at in zip(DUCT_X, ("west", "east"), CONSOLE_LIGHT):
        n += drop(S.mid(x), CONSOLE_Z + 1.0 - LIP, CORNICE_Y + 0.5, CONSOLE_HANG, CONSOLE_LAMP, f"console {side}", at)

    # ---- the patch cords, on the faces of the two jack fields; the operator's mug by the key
    own = _models()
    for x, y in JACK_FIELDS:
        side = "w" if x < AXIS_X else "e"
        n += K.put(c, own[cords_name(side)], (S.mid(x), y + 0.5, RACK_Z + 1.0), mount="wall", facing="south", origin=origin)
    n += K.put(c, own[PREFIX + "mug"], (MUG[0], float(SILL), MUG[1]), yaw=MUG[2], origin=origin)

    # ---- the two recesses: the board at the back of each, the lamp over its standard clock
    assert getattr(theirs("instruments"), "CLOCK_DIAL_Y", REGULATOR_DIAL) == REGULATOR_DIAL, \
        "props/instruments has moved its regulator's dial: the dials of the room hang at its height (REGULATOR_DIAL)"
    for x, side, at in zip(REGULATOR_X, ("west", "east"), REGULATOR_LIGHT):
        for i in range(len(BACK)):
            n += K.put(c, own[back_name(i)], (x, BACK_HELD, NORTH), mount="wall", facing="south", origin=origin)
        n += lamp("bracket", (x, REGULATOR_TOP + OVER, NICHE), REGULATOR_LAMP, f"clock {side}", at, facing="south")

    # ---- the cable ducts: a cover plate in the floor, or a grating with an iron bed under it
    for x, z in duct_cells():
        if grated((x, z)):
            put(x, FLOOR_Y, z, roles.IRON_GRATE)
            put(x, FLOOR_Y - 1, z, roles.IRON_PLATE)
        else:
            put(x, FLOOR_Y, z, roles.IRON_RIVETED.block)

    # ---- beams on the pilaster rows, each end in a shoe at the head of its pier
    for z in PIER_Z:
        for x in range(X0 + 1, X1):
            put(x, TOP, z, st(roles.IRON_RIVETED.slab, type="top"))
        put(X0, TOP, z, st(roles.IRON_RIVETED.stairs, facing="west", half="top"))
        put(X1, TOP, z, st(roles.IRON_RIVETED.stairs, facing="east", half="top"))

    # ---- the message desk and the rating bench: a drop light from the ceiling over the sitter's left hand
    # (who sits at the desk looks east, at the bench west); a board under the window stands in for the
    # desk while props/furniture is not in the tree
    if theirs("furniture") is None:
        for x, bay in ((X1, DESK_BAY), (X0, BENCH_BAY)):
            for z in MP.window_rows(bay):
                put(x, FEET, z, st(roles.DARK_WOOD.slab, type="top"))
    n += drop(DESK_X, DESK_Z - LEFT, CEIL_Y, DESK_HANG, DESK_LAMP, "message desk", DESK_LIGHT)
    n += drop(BENCH_X, BENCH_Z + LEFT, CEIL_Y, DESK_HANG, DESK_LAMP, "rating bench", BENCH_LIGHT)
    bounce(DESK_BOUNCE, BOUNCE, "ceiling over the message desk")
    bounce(BENCH_BOUNCE, BOUNCE, "ceiling over the rating bench")

    # ---- what lies on the two desks, or on the boards that stand in for them: the chronometers on the
    # rating bench, the paper on the message desk
    bench_yaw = K.FACING["east"]
    desk_top = FEET + (BOARD_TOP if theirs("furniture") is None else theirs("furniture").TOP["writing_desk"])
    for along, out, twist in CHRONOMETERS:
        dx, _, dz = K.turn(bench_yaw, (along * PX, 0.0, out * PX))
        n += K.put(c, own[PREFIX + "chronometer"], (BENCH_X + dx, desk_top, BENCH_Z + dz), yaw=bench_yaw + twist, origin=origin)
    n += K.put(c, own[PREFIX + "forms"], (DESK_X, desk_top, DESK_Z), facing="west", origin=origin)

    # ---- the world clocks on their board over a cabinet of drawers, and the lamp over the middle one
    for z, offset in zip(range(CLOCK_Z[0], CLOCK_Z[1] + 1), WORLD):
        put(X0, FEET, z, st(roles.PANELS["drawers"], facing="east"))
        n += K.put(c, own[clock_name(offset)], (PANEL_W, DIAL_Y, S.mid(z)), mount="wall", facing="east", origin=origin)
    n += lamp("bracket", (PANEL_W, DIAL_Y + BOARD[1] * PX + OVER, S.mid(*CLOCK_Z)), CLOCK_LAMP, "world clocks", CLOCK_LIGHT, facing="east")
    bounce(CLOCKS_BOUNCE, CLOCK_BOUNCE, "ceiling over the world clocks")

    # ---- the panelling: every solid stretch of wall where no block of the room stands, from the floor
    # to the ceiling; before a window only the course under its sill
    clear = set(clear_cells())

    def free(x, y, z):
        return not c.has(ox + x, oy + y, oz + z)

    for y in range(FEET, PANEL_TOP + 1):
        put(RISER[0], y, RISER[1], roles.DARK_WOOD.block)
        for z in range(Z0, Z1 + 1):
            for x, side in ((X1, "east"), (X0, "west")):
                if (x, z) != CORNER and (x, y, z) not in clear and free(x, y, z):
                    put(x, y, z, panel(side))
        for x in range(X0 + 1, X1 + 1):
            if not (DOOR_X[0] <= x <= DOOR_X[1] and y <= DOOR_TOP) and free(x, y, Z1):
                put(x, y, Z1, panel("south"))

    # ---- the pieces of the other packages that are in the tree
    for p in PIECES:
        module = theirs(p["package"])
        if module is None:
            continue
        x, y, z = p["where"]
        if p["on"] is not None:
            under = theirs(p["on"][0])
            if under is None:
                continue
            y += under.TOP[p["on"][1]]
        n += module.place(c, p["kind"], (x, y, z), origin=origin, **p["how"])
    return {"entities": n, "lights": lights}


def _offer(canvas, cell, level, why, rank):
    """Register a light source with the light line (sky/_lightkit). While that kit is not in the
    tree the block is put down here, never over a block that is there, so a test scene is lit."""
    try:
        from ..sky import _lightkit
    except ImportError:
        canvas.set(*cell, st(B.LIGHT, level=level), keep=True)
    else:
        _lightkit.suggest(canvas, cell, level, why, rank=rank)


def build(canvas, origin=(0, 0, 0)):
    """The master scene's call: nothing until the room has moved in."""
    if not MOVED_IN:
        return 0
    return build_timeroom(canvas, origin)["entities"]
