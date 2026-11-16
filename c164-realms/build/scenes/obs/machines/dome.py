"""machines/dome: the gear of the great dome (plan ART-PLAN 5.2 and 7.2; parts/A5-machines.md 2.2;
card packages/machines/domegear.md). What turns the dome and what opens its slit, seen from the
dome room (view V8, in one picture with the great refractor).

Two trains, each to be read from the hand to the load.

  Turning the dome. A rail lies on the ledge of the drum. Under every seam of the dome's twenty
  gores a truck with one flanged wheel carries the dome's ring girder over it, and the trucks hold
  a toothed ring, teeth inwards. In the north-west corner of the room a hand wheel turns a short
  shaft; its pinion drives a crown wheel on an upright shaft, which climbs the wall through two
  bearings to a pinion in the toothed ring: 160 teeth to 10, sixteen turns of the upright shaft
  to one of the dome. The ring's teeth are coarse, upright bars not half a block apart, and its
  pinion is a block and a half across: from the floor, seven blocks below, that is the part of
  the train that must be read.

  Opening the slit (main/dome version b, the one the map is built with: a curtain of slats
  between two rails, drawn up from the slit's foot). With the slit open the curtain lies wound on
  a roller across the slit's foot, its iron bar just above the roll. From either end of the bar a
  chain runs up the rail, over a sheave at the slit's head and back down under the rail, on
  rollers hung from it, then straight down to a drum of the winch: a shaft across the slit's foot,
  in front of the ring girder. Hauling the hand chain on the winch's wheel winds both chains and
  draws the bar up the rails; a pawl holds it. Two weights balance the curtain: each hangs on a
  wire rope from an end of the winch's shaft, over a sheave at the top of a rail under the arch
  girder beside the slit, and runs down that rail as the curtain goes up (the rope leaves the
  shaft on the side that pays it out while the chains wind on). Let go, the curtain comes down
  by its own weight and the roller takes it up again, turned by two small weights on cords round
  its shaft ends, in the pockets behind the rails' feet. A weight's rail is riveted under the
  lower chord of its arch girder, whose underside is the rail's line (riveted()); in a room that
  has no such girders yet, two straps hang it from the curb.

  Version a of the shell (two leaves that part sideways) keeps its gear. Each leaf has an arm at
  its foot, bent over the sill into the room. An endless chain runs across the slit's foot over
  two corner wheels; the north arm holds its upper strand, the south arm its lower one, so the
  leaves can only move together and opposite ways. Each arm also hangs on a chain that turns
  round a sheave and runs up a rail hung under the arch girder beside the slit, over a second
  sheave and back down to a weight on wheels: the weights run down their rails and draw the leaves apart.
  Hauling the hand chain turns the sprocket in the middle of the endless chain, draws the leaves
  together and lifts the weights again.

What is fixed to the building stays below the underside of the dome's ring girder (y 25); what is
above it rides round with the dome (the hand chain is hitched up before the dome is turned). The
shell and the curtain's rails are main's; the ring beam on the wall, the ring girder, the arch
girders beside the slit and the room's lining are interiors'; this package places display entities
and one barrier, in the foot of the upright shaft's corner, where the crown wheel and its bearing
fill the cell (barrier_cells()).

Moving pieces are models of their own, and place() sets them going with motion/_kit (plan 7.1):
  trucks       the twenty trucks and the toothed ring, in five lengths: they swing about TURN_AXIS as the
               dome is turned to and fro to keep the comet in its slit (turning(): main/_dome's numbers);
               the rail under them (rail) is the drum's and lies still
  riser        turns about the vertical through riser_at(), sixteen times the ring's angle
  handwheel    turns about the line along x through its entity, HAND_GEAR turns to one of the riser
  version b: the slit is shut and opened again once in CURTAIN_CYCLE ticks (curtain_moves())
  bar          goes up the curtain's path from BAR_DEG to SHUT_DEG, HAUL blocks: it turns about the line
               along z through CURTAIN_C, which keeps it on the path to a quarter pixel
  laths0..2    the curtain behind the bar, in PANELS lengths that turn about the same line; with the
               slit open they are parked in the wall under its foot
  roll         turns about the line along z through its entity as the curtain comes off it
  winch        turns about the line along z through its entity, WINCH_TURNS turns from open to shut
  weight       runs down its rail, WEIGHT_RUN blocks at RUN_DEG from the level, as the curtain goes up
  pull         sways about the line along z through its entity, its wheel's axis (PULL_SWAY)
  version a:
  drive        turns about the line along x through its entity
  arm_n, arm_s slide along z towards the dome's meridian, TRAVEL blocks, as the leaves shut
  weight       runs up its rail, TRAVEL blocks at RUN_DEG from the level, as the leaves shut
Tonight the slit is open. Version b: the curtain is on its roll, the bar at the rails' foot, the
weights at the top of their rails. Version a: the arms stand in the slit's two lower corners and
the weights at the foot of their rails.

Sizes inside the models are in sixteenths of a block (px) whatever scale a model is shown at.
"""
import functools
import importlib
import math
import os

from artkit import models as M

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..motion import _kit as MK
from ..props import _kit as K

PREFIX = "mach_dome_"
MOVED_IN = True             # in the master scene since 11-16 (the director's fast lane): the dome stands there, and
#                             what the gear takes from interiors/domeroom (the ring girder, the curb) follows with that package
# How far the pieces are drawn (the four bands of 11-16, artkit.models): the gear is seen from the
# dome room. What the curtain is made of is seen through the slit from across the site
VIEW = M.NEAR
VIEW_KEEP = (PREFIX + "roll", PREFIX + "bar", PREFIX + "laths?")

IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
IRON_B = P.mat("iron", base=4)          # bright: where iron runs on iron (a tread, the rail's head, a peg, a sheave)
TOOTH_IRON = P.mat("iron", base=4, bevel="ends")    # a tooth of the ring or its pinion: a bar with a lit top, no frame
ROOT_IRON = P.mat("iron_dark", base=1)              # what the teeth stand on: the gaps between them are to read as gaps
COPPER = P.mat("old_copper", base=1)    # the weights' slabs: the tone of the old-copper blocks' faces
SLAT = P.mat("verdigris", bevel="along")             # a slat of the curtain: the dome's plates, its long edges drawn
SLAT_D = P.mat("verdigris", base=1, bevel="along")   # every third one, the darker copper
SEAM = P.mat("verdigris", base=0, bevel=0)           # what shows between two slats on the roll
BRASS = P.mat("brass")
BRASS_D = P.mat("brass_dark")

# The sky's light a piece is shown in: (far from the slit, beside it); no lamp's. Left alone a piece
# takes the light of the cell its entity stands in: round the ring that falls off to nothing with
# the distance from the slit (in the pictures of 11-16 the far half of the ring could not be told
# from the dark of its slot), and a piece ten blocks long gets the light of one end. So every piece
# is told its light (night()): the open sky's above the slit less one level for every column away
# from it, never under the first number, so that the far half of the ring still reads, and never
# over the second, so that the iron stays under the sky. The numbers and the rule are those
# interiors/domeroom shows the dome's skeleton by (a3, 11-16): the gear and the girders it hangs on
# have one light. The sky's light follows the hour and the light version as the blocks' does; a
# lamp's does not, and it turns the iron brown ((10, 7), the telescope's light, made a rope of the
# toothed ring)
IRON_LIGHT = (10, 13)

PX = 16.0                   # px to a block
LINK = 4.0                  # px: a chain link; links are 3 x 2 px, every other one turned a quarter
BAND = 2.0                  # px: how thick a chain is drawn where it lies round a wheel,
WRAP = 2.75                 # and how wide: a hair inside its links, so that no two faces lie in one plane
PIN = 1.0                   # px: the radius of the small shafts and pins

# ---- turning the dome: all from the skeleton --------------------------------------------------------
AX, AZ = S.DOME_AXIS                    # the point the dome turns about
TURN_AXIS = (AX, AZ)                    # vertical, through this point
FLOOR_Y = float(S.ROOF_STAND)           # 18.0: feet on the dome-room floor
LEDGE_Y = float(S.DOME_SPRING)          # 24.0: the top of the drum's last course; the rail lies on it
RING_Y = LEDGE_Y + 1.0                  # 25.0: the underside of the dome's ring girder (interiors/domeroom)
GORES = 20                              # main/dome: a truck under every seam between two gores
SEG_DEG = 360.0 / GORES
# The ring is placed in five lengths of four gores: five display entities are the rail, five more
# what rides on it, and one command a step moves a length (twenty would move twenty trucks). A
# length is fourteen blocks from end to end and three deep, which a model shown at five holds
LENGTHS = 5
LENGTH_GORES = GORES // LENGTHS         # 4
LENGTH_DEG = 360.0 / LENGTHS            # 72
LENGTH_AT = 180.0                       # the first length's middle: astride the slit's meridian, so the slit's light is one length's
LENGTH_SCALE = 5
RING_SIDES = 3 * GORES                  # the ring is a polygon of sixty sides, three to a gore
# The dome's slow turn to and fro, by which it keeps the comet in its slit: main/_dome names it
# (TURN_DEG to either side, there and back in TURN_PERIOD ticks, in TURN_KEYS poses, TURN_SIGN 1
# setting off counter-clockwise seen from above), and what rides with the dome swings by it. These
# are its numbers of 11-16, used while that file has none (turning())
TURN = (3.0, 600, 8, 1)
RAIL_R = S.DOME_ROOM_DIAM / 2.0 + 0.25  # 11.25: the rail's centre line; a circle that lies on the ledge all the way round
CHEEK_IN = 5.0                          # px from the rail's centre line to the inner faces of a truck's cheeks
RACK_TEETH = 8 * GORES                  # 160: eight teeth to a segment
RACK_BACK = 2.0                         # px: the ring the teeth stand on, against the trucks' inner cheeks
RACK_Y = (10.0, 16.0)                   # px over the ledge: the toothed ring, up to the ring girder's underside
TOOTH = 3.0                             # px: how wide a tooth is, the ring's and its pinion's: an upright bar, twice as high
ADDENDUM, DEDENDUM = 1.75, 2.25         # px: a tooth stands this far past the pitch circle and is rooted this far behind it
# 10.67: the toothed ring's pitch circle; a tooth and a gap are 6.7 px
RACK_R = RAIL_R - (CHEEK_IN + RACK_BACK + DEDENDUM) / PX
PINION_TEETH = 10
PINION_R = RACK_R * PINION_TEETH / RACK_TEETH   # 0.67: a wheel of a block and a half, to be seen from the floor
RISER_R = RACK_R - PINION_R             # the upright shaft, from the dome's axis
# degrees round the dome (0 = east, 90 = south): the middle of a gap of the toothed ring, in the
# corner of the wall that interiors/domeroom keeps clear from the floor to the ledge (GEAR_SHAFT)
RISER_DEG = 107 * 360.0 / RACK_TEETH
RISER_TOP = (RING_Y - FLOOR_Y) * PX     # 112 px over the floor
CROWN_PEGS = 8                          # the crown wheel on the upright shaft
CROWN_R = 4.5                           # px: its pitch circle
PEG_Y = (13.0, 15.0)                    # px over the floor: its pegs
HAND_TEETH = 6                          # the pinion on the hand shaft
HAND_R = CROWN_R * HAND_TEETH / CROWN_PEGS      # 3.375 px: the same pitch
HAND_H = (PEG_Y[0] + PEG_Y[1]) / 2.0 + HAND_R   # 17.375 px over the floor: the hand shaft
HAND_GEAR = CROWN_PEGS / HAND_TEETH     # turns of the hand wheel to one of the upright shaft
HAND_PIECES = ("riser", "pedestal", "handwheel", "brackets")
# A model has no collision, and what one can walk into is given that of what is seen there
# (INTERFACE, the director's fifth supplement of 11-16: a barrier only inside a solid model that is
# seen, not a cell past its outline, never more than two high). In the corner of the wall that is
# kept clear for the upright shaft, the crown wheel, the footstep bearing and the base plate fill
# the first row and stand out of it to the east and to the south, the two sides one comes from:
# that one cell. The row over the crown wheel holds only the shaft, and the hand wheel is a thing
# one stands at (interiors/domeroom GEAR_STAND): no barrier there
BARRIER_ROWS = 1

# ---- opening the slit (version a): in the dome's frame, x and z from its axis ------------------------
JAMB_Z = S.SLIT_W / 2.0                 # 2.5: the slit's two edges
RUN_Z = JAMB_Z + 0.5                    # 3.0: the plane of a weight's run, the middle of the arch girder beside the slit
SILL_Y = RING_Y + 1.0                   # 26.0: the top of the sill: under the slit the ring girder is one row high
# the ring girder's face towards the room beside the slit (columns z 2 and 3 on either side; on the
# meridian the raster circle lies a block further out)
FACE_X = -(S.DOME_ROOM_DIAM / 2.0 - 0.5)
LOOP_X = FACE_X + 0.25                  # the endless chain's plane
F0 = (LOOP_X, RING_Y + 0.5, 0.0)        # the middle of the foot gear: the drive's axis on the dome's meridian
STILE_X = FACE_X - 2.5                  # where an arm takes hold of its leaf: the stile over the sill's outer column
TRAVEL = JAMB_Z - 2.0 / PX              # 2.375 blocks: the leaves meet arm to arm on the meridian
# a weight's run: a line from the ring girder's face beside the slit, one column in and two rows up
# three times running, through (-9.5, 28), (-8.5, 30) and (-7.5, 32). These are the lower corners of
# the vault's lining in the next column (interiors/domeroom: boards under every plate), so the rail
# runs along the lining's edge. What carries it is the iron curb interiors/domeroom lays under the
# skin beside the slit, the flange of an arch girder: under main/dome's open leaf, whose stile lies
# half a block over the plates, the curb is higher than the lining, and the rail hangs from it
RUN_FOOT = (FACE_X, SILL_Y)
RUN_STEP = (1.0, 2.0)
RUN_C1 = (RUN_FOOT[0] + RUN_STEP[0], RUN_FOOT[1] + RUN_STEP[1])
RUN_HANG = (2.0, 2.0, 1.0)              # blocks from the line's three corners up to the curb, just west of each
RUN_DEG = math.degrees(math.atan2(RUN_STEP[1], RUN_STEP[0]))        # 63.43
RUN_ANCHOR = (FACE_X + 0.5, SILL_Y + 0.5)       # the cell a run takes its light from
HANDCHAIN_Y = FLOOR_Y + 1.75            # the middle of the hand chain's bight: its lowest link hangs 1.3 over the floor
PULL_SWAY = (1.2, 100)                  # degrees to either side of the plumb line, ticks there and back: two pixels at the bight

# px from F0
FACE = (FACE_X - F0[0]) * PX            # -4: the ring girder's face beside the slit
BACK = FACE - PX                        # -20: its face on the meridian
SILL = (SILL_Y - F0[1]) * PX            # 8
UNDER = (RING_Y - F0[1]) * PX           # -8
JAMB = JAMB_Z * PX                      # 40
RUN = RUN_Z * PX                        # 48
SPROCKET_R = 2.0                        # the three wheels of the endless chain
STRAND = SPROCKET_R + 0.5               # its strands, over and under the wheels' axis
IDLER_Z = RUN - 1.0                     # the two corner wheels
WHEEL_X = 8.0                           # the hand-chain wheel's plane: its chain clears the arms' lugs when the leaves are shut
WHEEL_R = 6.25                          # the hand chain on it
BAR = 2.0                               # an arm is a flat bar this thick, on its leaf's meeting face
CLAMP = (2.5, 4.5)                      # where it grips its strand: behind the jamb, clear of the drive when shut
LUG = 5.5                               # where the weight's chain leaves it: over the upper strand, under the sill

# px along a run from its first corner (s) and below the line of the corners (d)
RAIL = (-32.0, 71.0)                    # the rail's web: from over the sill's level to the third corner
FLANGE = (-30.0, 53.0)                  # its foot, which the wheels run on
WEB_D = 6.0
FLANGE_D = (5.0, 7.0)
UP_D = 8.75                             # the chain on its way up: between the flange and the weight
DOWN_D = 14.5                           # and on its way back down, to the middle of the weight
KNEE_S = 62.0                           # the sheave at the top
FOOT_R = 3.0                            # the chain's turn round the sheave at the foot
STOP = -27.0                            # the lower stop's upper face
W_HALF = 9.0                            # half a weight's length
W_WHEEL = 5.0                           # its wheels, either way from its middle
W_WHEEL_R = 1.5
WEIGHT_S0 = STOP + W_WHEEL_R + W_WHEEL  # the weight's middle with the slit open: its lower wheels on the stop

# ---- opening the slit (version b): in the dome's frame -------------------------------------------------
# main/dome draws the slit's meridian as half an ellipse, SHELL_A wide at the ring beam's foot and
# SHELL_B high on the axis, and its shell is one block thick under that line; the curtain's slats
# are cells of the shell between the two rails. The gear lays the curtain's path in the middle of
# the shell's thickness. A point of the path is named by the angle main/dome counts its slats in
# (_elevation, DRAWN): 0 at the foot, 90 over the axis
SHELL_A = S.DOME_R + 0.5                # 13.5
SHELL_B = S.DOME_APEX + 1.0 - LEDGE_Y   # 14.0
MID = 8.0                               # px from the plates' face in to the curtain's path
HEAD_X = -1.5                           # the slit's head: the west face of the crown's nine columns
LATHS = 18                              # the roll's girth in slats
LATH = 4.0                              # px: a slat's width
LATH_T = 1.5                            # px: its thickness
ROLL_R = LATH / (2.0 * math.tan(math.pi / LATHS)) - LATH_T / 2.0       # 10.6 px: the middle of the roll's outermost slats
ROLL_HALF = JAMB - 2.5                  # px: half the curtain's width, a little play between the rails
ROD = 3.0                               # px: the curtain's bar is square
BAR_DEG = 16.5                          # where the bar rests with the slit open
TAIL = 2                                # slats between the bar and the roll
HAUL_Z = JAMB - 3.5                     # px: the plane of a hauling chain, just inside the rail's face
GAP = 7.0                               # px: a hauling chain's way back lies this far inside its way up
HANGERS = (22.0, 31.0, 40.0, 49.0, 58.0, 67.0, 76.0)       # where a rail carries rollers for its chain
LEAVE_DEG = HANGERS[1]                  # down to here the way back keeps to the rail; from here it drops to the winch
DRUM_R = 6.25                           # px: the chain on a drum of the winch
DRUM_W = 20.0                           # px: a drum's length: the six turns it takes up lie side by side
WHEEL_RB = 5.5                          # px: the hand chain on the winch's wheel
SHAFT = 1.5                             # px: the winch's shaft
ROPE = 0.5                              # px: half a weight's wire rope
ROPE_R = 1.125                          # px: the rope on the shaft's end, which is turned down to carry it
WINCH_X = FACE_X + 0.53                 # the winch's shaft: its drums turn a pixel off the ring girder's face, and its
                                        # hand chain hangs in the first column of the room
WINCH_D = UP_D - ROPE_R                 # px below a run's line: the rope leaves the shaft's far side straight up the
                                        # run, so that hauling the curtain up pays it out and lets the weight down
WINCH_HALF = RUN + 2.0                  # px: half the shaft
# a weight's run in version b: the rail ends where the underside of interiors/domeroom's arch
# girder leaves the line (x -3.66 in the scene); the sheave at its top is as far below the rail's
# end as in version a
RAIL_B = (RAIL[0], 47.0)
FLANGE_B = (FLANGE[0], 32.0)
KNEE_SB = 41.0
RUN_HANG_B = RUN_HANG[:2]
CLEATS = (-28.0, -14.0, 9.0, 22.0)      # where a rail is riveted to the arch girder over it
WEIGHT_S1 = FLANGE_B[1] - 3.0 - W_WHEEL_R - W_WHEEL    # the weight's middle with the slit open: its upper wheels under the stop
CORD_R = 0.875                          # px: the cord of a take-up weight on the roller's shaft end


def neighbour(line, name):
    """Another package's module when it is in the tree, else None: the gear is built and judged
    before its neighbours are merged."""
    package = f"{__package__.rsplit('.', 1)[0]}.{line}"
    try:
        return importlib.import_module(f"{package}.{name}")
    except ModuleNotFoundError as e:
        if e.name not in (package, f"{package}.{name}"):
            raise                               # the module is there and fails to import something
        return None


def shell_version():
    """The version of main/dome that stands: its VERSION once that package is in the tree, else "a"."""
    return getattr(neighbour("main", "dome"), "VERSION", "a")


def night(x, z):
    """The sky's light a piece is shown in, by the column its entity is in (x, z from the dome's
    axis): what falls through the open slit, one level less for every column away from it, kept
    within IRON_LIGHT."""
    col = int(math.floor(AX + x)), int(math.floor(AZ + z))
    half = S.SLIT_W // 2
    first = (S.DOME_CENTRE[0] - S.DOME_R, S.DOME_CENTRE[1] - half)          # the slit's columns: from the dome's edge
    last = (S.DOME_CENTRE[0] - half, S.DOME_CENTRE[1] + half)               # to its head
    away = sum(max(first[i] - col[i], col[i] - last[i], 0) for i in range(2))
    return max(IRON_LIGHT[0], min(IRON_LIGHT[1], 15 - away))


def riveted():
    """True once interiors/domeroom draws the dome's arch girders (its frame()): the weights' rails
    of version b are then riveted under their lower chords, whose underside is the rails' line.
    Until then two straps hang each rail from the curb beside the slit."""
    return hasattr(neighbour("interiors", "domeroom"), "frame")


def seam_angles():
    return [(k + 0.5) * SEG_DEG for k in range(GORES)]


def length_angles():
    """Degrees round the dome of the middles of the ring's lengths."""
    return [(LENGTH_AT + k * LENGTH_DEG) % 360.0 for k in range(LENGTHS)]


def on_rail(deg):
    """(x, z) of the rail's centre line at `deg` round the dome, from the dome's axis."""
    r = math.radians(deg)
    return RAIL_R * math.cos(r), RAIL_R * math.sin(r)


def turning():
    """(degrees to either side, ticks there and back, poses, sign) of the dome's turn to and fro:
    main/_dome's TURN_DEG, TURN_PERIOD, TURN_KEYS and TURN_SIGN once that file names them, else TURN."""
    shell = neighbour("main", "_dome")
    if getattr(shell, "TURN_DEG", None) is None or getattr(shell, "TURN_PERIOD", None) is None:
        return TURN
    return (float(shell.TURN_DEG), int(shell.TURN_PERIOD), int(getattr(shell, "TURN_KEYS", TURN[2])),
            1 if getattr(shell, "TURN_SIGN", 1) >= 0 else -1)


def riser_at():
    """(x, z) of the upright shaft, from the dome's axis."""
    r = math.radians(RISER_DEG)
    return RISER_R * math.cos(r), RISER_R * math.sin(r)


RISER_CELL = (int(math.floor(AX + riser_at()[0])), int(math.floor(AZ + riser_at()[1])))     # the column it stands in: (-1, -9)


def _run_units():
    r = math.radians(RUN_DEG)
    return (math.cos(r), math.sin(r)), (math.sin(r), -math.cos(r))


def on_run(s, d=0.0):
    """(x, y) in the dome's frame of the point s px up a run's line (RUN_FOOT, RUN_STEP) and d px
    below it, away from the vault."""
    (ux, uy), (nx, ny) = _run_units()
    return RUN_C1[0] + (s * ux + d * nx) / PX, RUN_C1[1] + (s * uy + d * ny) / PX


def _eye():
    """Where the weight's chain leaves an arm, level across the slit's foot: (s along the run, x
    from F0), both in px. The chain meets the run's up-going strand there."""
    (_ux, uy), (_nx, ny) = _run_units()
    s = ((F0[1] + LUG / PX - RUN_C1[1]) * PX - UP_D * ny) / uy
    return s, (on_run(s, UP_D)[0] - F0[0]) * PX


def _axes(inside=0.0):
    return SHELL_A - (MID + inside) / PX, SHELL_B - (MID + inside) / PX


def on_curve(deg, inside=0.0):
    """(x, y) in the dome's frame of the point of the curtain's path `deg` degrees up the slit's
    meridian, or of the line `inside` px further into the room."""
    a, b = _axes(inside)
    r = math.radians(deg)
    return -a * math.cos(r), LEDGE_Y + b * math.sin(r)


def slope(deg, inside=0.0):
    """Which way the path runs there, going up: degrees from east towards the zenith."""
    a, b = _axes(inside)
    r = math.radians(deg)
    return math.degrees(math.atan2(b * math.cos(r), a * math.sin(r)))


def _lengths(deg0, deg1, inside, steps=2000):
    """[(degrees, blocks from deg0 along the path)] in small steps."""
    out, far, last = [], 0.0, None
    for i in range(steps + 1):
        deg = deg0 + (deg1 - deg0) * i / steps
        at = on_curve(deg, inside)
        if last is not None:
            far += math.hypot(at[0] - last[0], at[1] - last[1])
        out.append((deg, far))
        last = at
    return out


def along(deg0, deg1, inside=0.0):
    """Blocks along the path between two angles."""
    return _lengths(deg0, deg1, inside)[-1][1]


def _stations(deg0, deg1, inside=0.0, pitch=LINK):
    """[(x, y, slope)] of the middles of the links of a chain that lies on the path from deg0 to
    deg1: a whole number of them fills it. Returns them with the length of one, in px."""
    table = _lengths(deg0, deg1, inside)
    n = max(1, int(round(table[-1][1] * PX / pitch)))
    step, out, j = table[-1][1] / n, [], 0
    for k in range(n):
        want = (k + 0.5) * step
        while table[j + 1][1] < want:
            j += 1
        (d0, f0), (d1, f1) = table[j], table[j + 1]
        deg = d0 + (d1 - d0) * (want - f0) / (f1 - f0)
        out.append(on_curve(deg, inside) + (slope(deg, inside) + (0.0 if deg1 > deg0 else 180.0),))
    return out, step * PX


def _unit(deg):
    r = math.radians(deg)
    return math.cos(r), math.sin(r)


def roll_at():
    """(x, y) of the roller's axis in the dome's frame: the curtain comes down from the bar, TAIL
    slats straight on, and lies on the roll's west side."""
    (bx, by), (tx, ty) = on_curve(BAR_DEG), _unit(slope(BAR_DEG))
    down = (ROD / 2.0 + TAIL * LATH) / PX
    return bx - down * tx + ROLL_R / PX * ty, by - down * ty - ROLL_R / PX * tx


def winch_at():
    """(x, y) of the winch's shaft in the dome's frame: at WINCH_X, where a weight's rope leaves
    it straight up its run."""
    (ux, uy), (nx, ny) = _run_units()
    s = ((WINCH_X - RUN_C1[0]) * PX - WINCH_D * nx) / ux
    return on_run(s, WINCH_D)


WINCH_S = ((WINCH_X - RUN_C1[0]) * PX - WINCH_D * _run_units()[1][0]) / _run_units()[0][0]      # px up a run's line: where the rope starts


def _head_deg():
    """Where a hauling chain turns back at the slit's head: its sheave lies between the chain's
    two ways, and the chain round it stops a pixel short of the head."""
    lo, hi = 60.0, 90.0
    for _ in range(40):
        mid = (lo + hi) / 2.0
        if on_curve(mid, GAP / 2.0)[0] + (GAP / 2.0 + 1.0) / PX < HEAD_X - 1.0 / PX:
            lo = mid
        else:
            hi = mid
    return lo


HEAD_DEG = _head_deg()                  # 81.7
SHUT_DEG = HEAD_DEG - 3.0               # the bar with the slit shut, under the head sheaves
HAUL = along(BAR_DEG, SHUT_DEG)         # 14.4 blocks: how far the bar is drawn
WINCH_TURNS = HAUL * PX / (2.0 * math.pi * DRUM_R)      # 5.9
WEIGHT_RUN = WINCH_TURNS * 2.0 * math.pi * ROPE_R / PX  # 2.6 blocks: to just over the lower stop


# ---- the curtain drawn (round two): the slit is shut and opened again ---------------------------------
# The curtain's path is half an ellipse. One turn about a line along z takes the bar from where it
# rests to where it stands with the slit shut, pose for pose, and keeps it within a quarter pixel
# of the path on the way (_pivot() finds the point the line passes through; off_path() says how
# far off the bar gets). So the bar and the curtain behind it are display entities that stand on
# that line and turn about it (motion/_kit's turn()): the client carries them round the curve.
def _pivot():
    (x0, y0), (x1, y1) = on_curve(BAR_DEG), on_curve(SHUT_DEG)
    phi = math.radians(slope(SHUT_DEG) - slope(BAR_DEG))
    c, s = math.cos(phi), math.sin(phi)
    bx, by = x1 - (c * x0 - s * y0), y1 - (s * x0 + c * y0)
    det = (1.0 - c) ** 2 + s ** 2
    return ((1.0 - c) * bx - s * by) / det, (s * bx + (1.0 - c) * by) / det


CURTAIN_C = _pivot()                    # (0.26, 24.34) in the dome's frame
CURTAIN_R = math.hypot(on_curve(BAR_DEG)[0] - CURTAIN_C[0], on_curve(BAR_DEG)[1] - CURTAIN_C[1])        # 13.2 blocks
# 164.7: where the bar rests, seen from CURTAIN_C (degrees from east towards the zenith)
CURTAIN_POLAR = math.degrees(math.atan2(on_curve(BAR_DEG)[1] - CURTAIN_C[1], on_curve(BAR_DEG)[0] - CURTAIN_C[0]))
CURTAIN_TURN = slope(BAR_DEG) - slope(SHUT_DEG)         # 62.4 degrees: the bar's way from open to shut
CURTAIN_AXIS = (0.0, 0.0, -1.0)         # right-handed about this the bar goes up the slit
CURTAIN_LIGHT = 14                      # the sky's light on the curtain: a level under the plates outside, one over the iron in the room
LATH_DEG = math.degrees(LATH / PX / CURTAIN_R)          # 1.09: a slat's share of that circle
TAIL_DEG = math.degrees((ROD / 2.0 + TAIL * LATH) / PX / CURTAIN_R)     # 2.58: the bar's own slats end this far below its middle
# Behind the bar the curtain comes in PANELS lengths of PANEL_LATHS slats, four blocks each. With
# the slit open they lie one in the other inside the wall under the slit's foot, where the same
# circle runs down through the sill, the ring beam and three rows of the drum (whole blocks; the
# test scene tells if a parked length shows: shown()). Shutting, the first comes up through the
# sill's top until it meets the bar's own slats, the bar sets off with it, and each of the others
# sets off when the one before it has gone its own length: one curtain from the bar down into the
# sill. They go back the same way, and each stops where it was parked.
PANELS = 4
PANEL_LATHS = 16
PANEL_DEG = PANEL_LATHS * LATH_DEG      # 17.4
# 8.1: the sill's top, in degrees of that circle below the bar at rest
SILL_DEG = 180.0 - math.degrees(math.asin((SILL_Y - CURTAIN_C[1]) / CURTAIN_R)) - CURTAIN_POLAR
PARK_DEG = SILL_DEG + 1.4               # a parked length's upper edge: a third of a block under the sill's top
CURTAIN_LEAD = PARK_DEG - TAIL_DEG      # 6.9: what the first length rises before the bar sets off
CURTAIN_CYCLE = 2400                    # ticks: once in two minutes
CURTAIN_AT = 1700                       # the tick the curtain sets off: for a minute and a half the comet stands in the open slit
CURTAIN_TICKS = 277                     # from there to shut: the bar goes a block in a little under a second
CURTAIN_HOLD = 120                      # ticks the slit stays shut


def _still():
    """For a still picture of the curtain drawn (the offline renderer shows every piece where it was
    placed, so the slit open): the share of its way, 0 to 1, that the environment's C164_CURTAIN
    names. place() then puts the bar and the curtain's lengths where they are by that time and
    does not set them going. 0 when it is not set: the map is always built so."""
    try:
        return max(0.0, min(1.0, float(os.environ.get("C164_CURTAIN", "0") or 0.0)))
    except ValueError:
        return 0.0


def off_path(steps=200):
    """The furthest the bar's middle gets from the curtain's path on its way round CURTAIN_C, in px."""
    a, b = _axes()
    worst = 0.0
    for i in range(steps + 1):
        r = math.radians(CURTAIN_POLAR - CURTAIN_TURN * i / steps)
        x, y = CURTAIN_C[0] + CURTAIN_R * math.cos(r), CURTAIN_C[1] + CURTAIN_R * math.sin(r) - LEDGE_Y
        worst = max(worst, abs((x / a) ** 2 + (y / b) ** 2 - 1.0) / math.hypot(2.0 * x / a ** 2, 2.0 * y / b ** 2))
    return worst * PX


def curtain_moves():
    """When the curtain's parts move in a cycle of CURTAIN_CYCLE ticks, as motion/_kit's turn() and
    slide() take it: {part: [(tick it sets off, how far from its rest it goes, ticks it takes), ...]}.
    "bar", ("laths", k), "roll" and "winch" in degrees, "weight" in blocks down its rail."""
    first = CURTAIN_TURN + CURTAIN_LEAD                 # the first length's whole way
    speed = first / CURTAIN_TICKS
    back = CURTAIN_AT + CURTAIN_TICKS + CURTAIN_HOLD

    def both(start, far):
        return [(CURTAIN_AT + start, far, CURTAIN_TICKS - start), (back, 0.0, CURTAIN_TICKS - start)]

    # whole ticks: the bar a tick early and a length a tick late rather than the other way, so that
    # on the way there is a hair's gap between two pieces and never two slats in one place
    bar = int(math.floor(CURTAIN_LEAD / speed))
    out = {"bar": both(bar, CURTAIN_TURN)}
    for k in range(PANELS):
        out["laths", k] = both(int(math.ceil(k * PANEL_DEG / speed)), first - k * PANEL_DEG)
    out["roll"] = both(0, first * CURTAIN_R * PX / (ROLL_R + LATH_T / 2.0))     # the curtain comes off it as fast as it goes
    out["winch"] = both(bar, 360.0 * WINCH_TURNS)
    out["weight"] = both(bar, WEIGHT_RUN)
    return out


def _drop():
    """A hauling chain between the last roller of its way back and its drum: (the point it leaves
    the rail's line at, the point it meets the drum at), both (x, y) in the dome's frame. It comes
    down on the drum's west side."""
    (lx, ly), (wx, wy) = on_curve(LEAVE_DEG, GAP), winch_at()
    reach = math.hypot(lx - wx, ly - wy)
    turn = math.atan2(ly - wy, lx - wx) + math.acos(DRUM_R / PX / reach)
    return (lx, ly), (wx + DRUM_R / PX * math.cos(turn), wy + DRUM_R / PX * math.sin(turn))


# ---- drawing ------------------------------------------------------------------------------------------
class _Draw:
    """A model drawn in px whatever scale it is shown at: every length is divided by the scale on
    its way to the model, so a part is as many pixels as its numbers say and the model keeps
    sixteen pixels to a block (px = scale)."""

    def __init__(self, name, scale, anchor=(0.0, 0.0, 0.0)):
        self.scale = scale
        self.m = M.Model(PREFIX + name, px=scale, anchor=self._p(anchor))

    def _p(self, v):
        return tuple(c / self.scale for c in v)

    def box(self, a, b, mat, rot=None, **kw):
        if rot is not None:
            rot = (rot[0], rot[1], self._p(rot[2]))
        self.m.box(self._p(a), self._p(b), mat, rot=rot, **kw)

    def tube(self, axis, c, a0, a1, radius, mat, **kw):
        s = self.scale
        self.m.tube(axis, (c[0] / s, c[1] / s), a0 / s, a1 / s, radius / s, mat, **kw)

    def ring(self, axis, centre, radius, thick, width, mat, **kw):
        s = self.scale
        self.m.ring(axis, self._p(centre), radius / s, thick / s, width / s, mat, **kw)

    def turned(self, *turns, about=(0.0, 0.0, 0.0)):
        return self.m.turned(*turns, about=self._p(about))


def _chain(d, axis, c, a0, a1, seed):
    """A straight run of chain along `axis` from a0 to a1; c = the two other coordinates of its
    centre line, as Model.tube takes them. A whole number of links fills the run."""
    k = M.AXES.index(axis)
    o1, o2 = [i for i in range(3) if i != k]
    n = max(1, int(round(abs(a1 - a0) / LINK)))
    step = (a1 - a0) / n
    for i in range(n):
        w1, w2 = (1.5, 1.0) if i % 2 == 0 else (1.0, 1.5)
        lo, hi = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
        lo[k], hi[k] = a0 + step * i, a0 + step * (i + 1)
        lo[o1], hi[o1] = c[0] - w1, c[0] + w1
        lo[o2], hi[o2] = c[1] - w2, c[1] + w2
        d.box(lo, hi, IRON if i % 2 == 0 else IRON_D, grain=axis, seed=seed + i % 2)


# ---- the ring -------------------------------------------------------------------------------------------
def _seams():
    """Where the seams of one length of the ring lie, in degrees from its middle: -27, -9, 9, 27."""
    return [(k - (LENGTH_GORES - 1) / 2.0) * SEG_DEG for k in range(LENGTH_GORES)]


def _rail():
    """One length of the rail on the ledge, LENGTH_DEG of it, with the chairs that hold it down:
    it is fixed to the drum. The origin is on the ledge under the length's middle; +x points
    outwards, the dome's axis is RAIL_R behind it."""
    d = _Draw("rail", LENGTH_SCALE)
    axis = (-RAIL_R * PX, 0.0, 0.0)
    arc = (-LENGTH_DEG / 2.0, LENGTH_DEG / 2.0)
    d.ring("y", (axis[0], 1.0, 0.0), RAIL_R * PX, 6.0, 2.0, IRON_D, sides=RING_SIDES, arc=arc, seed=101)   # the rail's foot
    d.ring("y", (axis[0], 3.0, 0.0), RAIL_R * PX, 2.0, 2.0, IRON_B, sides=RING_SIDES, arc=arc, seed=102)   # and its head
    for seam in _seams():
        for deg in (-7.5, -4.5, 4.5, 7.5):                              # the chairs, four to a gore
            for x in (-2.0, 2.0):
                d.box((x - 1.0, 2.0, -1.5), (x + 1.0, 3.0, 1.5), IRON, rot=("y", -(seam + deg), axis), seed=103)
    return d


def _trucks():
    """What rides round with the dome over one length of the rail: under each seam a truck with one
    flanged wheel, and the toothed ring the trucks hold. It turns about the dome's axis, and the
    model's anchor lies on it: +x points outwards from there, the length's middle is RAIL_R out."""
    d = _Draw("trucks", LENGTH_SCALE, anchor=(-RAIL_R * PX, 0.0, 0.0))
    axis = (-RAIL_R * PX, 0.0, 0.0)
    arc = (-LENGTH_DEG / 2.0, LENGTH_DEG / 2.0)
    hub = 8.5                                                           # the axle over the ledge: the tread stands on the rail's head
    for seam in _seams():
        with d.turned(("y", -seam), about=axis):
            d.tube("x", (hub, 0.0), -2.5, 1.0, 4.5, IRON_B, sides=12, seed=109)         # the wheel's tread
            d.tube("x", (hub, 0.0), 1.0, 2.0, 5.25, IRON, sides=12, seed=110)           # its flange, on the wall's side of the rail
            d.tube("x", (hub, 0.0), -5.5, 4.75, 1.0, IRON_D, sides=8, seed=115)         # the axle
            for x0 in (-5.5, 4.25):
                d.tube("x", (hub, 0.0), x0, x0 + 0.5, 1.5, IRON, sides=8, seed=104)     # its nuts
            d.tube("x", (hub, 0.0), -6.5, -5.5, 1.0, BRASS_D, sides=8, seed=116)        # the oil cup on its end, towards the room
            for x0 in (-CHEEK_IN, 2.25):
                d.box((x0, 6.5, -2.0), (x0 + 2.0, 14.0, 2.0), IRON_D, seed=105)        # the truck's two cheeks
            d.box((-CHEEK_IN, 14.0, -7.0), (4.25, 16.0, 7.0), IRON, seed=108)   # its saddle, under the ring girder

    pitch = RACK_R * PX
    y0, y1 = RACK_Y
    d.ring("y", (axis[0], (y0 + y1) / 2.0, 0.0), pitch + DEDENDUM + RACK_BACK / 2.0, RACK_BACK, y1 - y0 - 1.0, ROOT_IRON,
           sides=RING_SIDES, arc=arc, seed=106)                         # the toothed ring's back, bolted to the trucks' inner cheeks
    x = pitch + axis[0]
    for j in range(RACK_TEETH // LENGTHS):                              # its teeth, towards the dome's axis: a gap at either end
        deg = (j + 0.5) * 360.0 / RACK_TEETH - LENGTH_DEG / 2.0
        d.box((x - ADDENDUM, y0, -TOOTH / 2.0), (x + DEDENDUM + 0.25, y1, TOOTH / 2.0), TOOTH_IRON, rot=("y", -deg, axis),
              grain="y", seed=107)
    return d


# ---- the hand gear: its pieces share one origin, on the floor on the upright shaft's axis, and the world's axes ----
def _riser():
    """The upright shaft: the crown wheel at its foot, a collar under and over each bearing, the
    pinion in the toothed ring at its top. Turns about its own axis."""
    d = _Draw("riser", 3, anchor=(0.0, HAND_H, 0.0))
    d.tube("y", (0.0, 0.0), 5.0, RISER_TOP - 1.0, 1.5, IRON, sides=8)
    d.tube("y", (0.0, 0.0), 9.0, 11.0, 2.5, IRON_D, sides=8)                    # the crown wheel: its hub,
    d.tube("y", (0.0, 0.0), 11.0, PEG_Y[0], 5.5, IRON, sides=16)                # its disc
    for i in range(CROWN_PEGS):                                                 # and its pegs; a gap looks east
        a = math.radians((i + 0.5) * 360.0 / CROWN_PEGS)
        d.tube("y", (CROWN_R * math.cos(a), CROWN_R * math.sin(a)), PEG_Y[0], PEG_Y[1], 0.75, IRON_B, sides=8, seed=111)
    for y0 in (50.0, 60.0, 86.0, 96.0):
        d.tube("y", (0.0, 0.0), y0, y0 + 2.0, 2.5, IRON_D, sides=8, seed=112)
    y0, y1 = (RISER_TOP - RACK_Y[1] + y for y in RACK_Y)                        # the pinion, as high as the toothed ring
    y1 -= 0.5                                                                   # but for the air under the ring girder, which turns over it
    root = PINION_R * PX - DEDENDUM
    d.tube("y", (0.0, 0.0), y0 + 0.5, y1, root, ROOT_IRON, sides=20)
    d.tube("y", (0.0, 0.0), y0 - 1.0, y0 + 0.5, 3.0, IRON, sides=8, seed=114)   # its boss
    for i in range(PINION_TEETH):                                               # the first tooth points away from the dome's axis, into the gap
        deg = RISER_DEG + i * 360.0 / PINION_TEETH
        d.box((root - 0.25, y0, -TOOTH / 2.0), (PINION_R * PX + ADDENDUM, y1 - 0.25, TOOTH / 2.0), TOOTH_IRON,
              rot=("y", -deg, (0.0, 0.0, 0.0)), grain="y", seed=113)
    return d


def _pedestal():
    """What stands on the floor: the base plate, the footstep bearing of the upright shaft, the
    standard that carries the hand shaft east of the crown wheel."""
    d = _Draw("pedestal", 1, anchor=(0.0, HAND_H, 0.0))
    d.box((-5.5, 0.0, -4.5), (10.5, 1.5, 4.5), IRON_D)
    for x in (-4.5, 9.5):
        for z in (-3.5, 3.5):
            d.box((x - 0.5, 1.5, z - 0.5), (x + 0.5, 2.0, z + 0.5), IRON, seed=121)     # holding-down bolts
    d.box((-2.5, 1.5, -2.5), (2.5, 5.5, 2.5), IRON)
    d.box((6.5, 1.5, -2.0), (9.0, HAND_H - 2.875, 2.0), IRON)
    d.box((6.25, HAND_H - 2.875, -2.75), (9.25, HAND_H + 2.875, 2.75), IRON_D)
    return d


def _handwheel():
    """The hand shaft with its pinion over the crown wheel, the hand wheel and its crank handle.
    Turns about the shaft, which runs along x."""
    d = _Draw("handwheel", 1, anchor=(0.0, HAND_H, 0.0))
    d.tube("x", (HAND_H, 0.0), 3.25, 13.0, 1.0, IRON_D, sides=8)
    d.tube("x", (HAND_H, 0.0), CROWN_R - 0.75, CROWN_R + 0.75, HAND_R - 1.0, IRON, sides=12)
    for i in range(HAND_TEETH):                                                 # one tooth straight down, between two pegs
        d.box((CROWN_R - 0.625, HAND_H - HAND_R - 0.875, -0.875), (CROWN_R + 0.625, HAND_H - HAND_R + 1.2, 0.875), IRON_B,
              rot=("x", i * 360.0 / HAND_TEETH, (CROWN_R, HAND_H, 0.0)), seed=131)
    rim = 10.75
    d.ring("x", (rim, HAND_H, 0.0), 6.25, 2.0, 2.0, BRASS, sides=16)
    for i in range(3):                                                          # three bars: six spokes
        d.box((rim - 0.5, HAND_H - 5.75, -1.0), (rim + 0.5, HAND_H + 5.75, 1.0), IRON_D,
              rot=("x", 60.0 * i, (rim, HAND_H, 0.0)), seed=132)
    d.tube("x", (HAND_H, 0.0), rim - 1.25, rim + 1.25, 1.75, BRASS_D, sides=8)
    d.tube("x", (HAND_H + 6.25, 0.0), rim + 1.0, rim + 5.0, 1.0, BRASS, sides=8)    # the handle, on the rim
    return d


def _brackets():
    """What holds the upright shaft to the wall: a plummer block half way up, on an arm from the
    west wall, and the plate that fills the gap in the ring beam, flush with the ledge."""
    d = _Draw("brackets", 1, anchor=(0.0, HAND_H, 0.0))
    rx, rz = riser_at()
    x0, z0 = (RISER_CELL[0] - AX - rx) * PX, (RISER_CELL[1] - AZ - rz) * PX     # the column's west and north faces
    d.box((x0, 50.0, -4.0), (x0 + 1.0, 62.0, 4.0), IRON_D)
    d.box((x0 + 1.0, 54.0, -1.5), (-2.75, 58.0, 1.5), IRON_D, grain="x")
    d.box((-2.75, 52.0, -2.75), (2.75, 60.0, 2.75), IRON)
    d.box((x0, 88.0, z0), (x0 + PX, 96.0, z0 + PX), IRON_D)
    return d


# ---- the slit's foot: these pieces share the origin F0 and the dome's axes --------------------------------
def _foot():
    """What is fixed to the dome at the slit's foot: the bracket out from the ring girder with the
    drive's bearing, the two corner wheels on their studs, the endless chain."""
    d = _Draw("foot", 3)
    d.box((BACK, UNDER + 0.5, -3.0), (BACK + 1.0, 0.0, 3.0), IRON_D)                    # the plate on the ring girder
    d.box((BACK + 1.0, UNDER + 1.0, -1.5), (5.0, UNDER + 3.0, 1.5), IRON_D, grain="x")  # the bracket
    d.box((2.0, UNDER + 3.0, -1.5), (5.0, 1.5, 1.5), IRON)                              # the bearing, between sprocket and hand-chain wheel
    for side in (-1, 1):
        z = side * IDLER_Z
        d.box((FACE, -2.0, z - 2.0), (FACE + 1.0, 2.0, z + 2.0), IRON_D, seed=401)
        d.tube("x", (0.0, z), FACE + 1.0, 1.5, PIN, IRON_D, sides=8, seed=402)
        d.tube("x", (0.0, z), -0.75, 0.75, SPROCKET_R, IRON_B, sides=8, seed=403)
        d.ring("x", (0.0, 0.0, z), STRAND, BAND, WRAP, IRON_D, sides=8,
               arc=(0.0, 180.0) if side > 0 else (180.0, 360.0), seed=404)
    for y in (STRAND, -STRAND):
        _chain(d, "z", (0.0, y), -IDLER_Z, IDLER_Z, 410)
    return d


def _drive():
    """The drive: a short shaft with the sprocket in the endless chain and the hand-chain wheel.
    Turns about the shaft, which runs along x."""
    d = _Draw("drive", 1)
    d.tube("x", (0.0, 0.0), -1.5, WHEEL_X + 1.75, PIN, IRON_D, sides=8)
    d.tube("x", (0.0, 0.0), -0.75, 0.75, SPROCKET_R, IRON_B, sides=8)
    d.ring("x", (WHEEL_X, 0.0, 0.0), WHEEL_R - 1.25, 2.0, 2.0, IRON_B, sides=16)    # the rim, under the hand chain
    for i in range(3):                                                          # three spokes
        d.box((WHEEL_X - 0.5, 0.0, -1.0), (WHEEL_X + 0.5, WHEEL_R - 2.0, 1.0), IRON_D,
              rot=("x", 30.0 + 120.0 * i, (WHEEL_X, 0.0, 0.0)), seed=421)
    d.tube("x", (0.0, 0.0), WHEEL_X - 1.25, WHEEL_X + 1.25, 1.5, IRON_D, sides=8)
    return d


def _handchain():
    """The hand chain: an endless loop over the hand-chain wheel, down to where a hand reaches it."""
    d = _Draw("handchain", 3)
    low = (HANDCHAIN_Y - F0[1]) * PX
    d.ring("x", (WHEEL_X, 0.0, 0.0), WHEEL_R, BAND, WRAP, IRON_D, sides=12, arc=(-90.0, 90.0), seed=431)
    d.ring("x", (WHEEL_X, low, 0.0), WHEEL_R, BAND, WRAP, IRON_D, sides=12, arc=(90.0, 270.0), seed=431)
    for z in (-WHEEL_R, WHEEL_R):
        _chain(d, "y", (WHEEL_X, z), low, 0.0, 432)
    return d


def _arm(side):
    """The arm of one leaf (side 1: south, -1: north): a flat bar on the leaf's meeting face, along
    the sill's top into the room, down the ring girder's face to the strand it holds, and the lug
    its weight's chain is made fast to. Slides along z."""
    d = _Draw("arm_s" if side > 0 else "arm_n", 2)
    grip = -STRAND if side > 0 else STRAND          # the south arm holds the lower strand, the north arm the upper
    _eye_s, eye_x = _eye()

    def box(x0, y0, in0, x1, y1, in1, mat, **kw):   # in0, in1: px into the slit from the jamb
        d.box((x0, y0, side * (JAMB - in0)), (x1, y1, side * (JAMB - in1)), mat, **kw)

    stile = (STILE_X - F0[0]) * PX
    box(stile, SILL + 2.0, 0.0, stile + 8.0, SILL + 8.0, BAR, IRON_D)                   # the plate on the leaf's stile
    box(stile, SILL, 0.0, FACE, SILL + 2.0, BAR, IRON, grain="x")                       # along the sill
    box(FACE, grip - 1.0, 0.0, FACE + 2.0, SILL + 2.0, BAR, IRON)                       # down the ring girder's face
    box(FACE, grip - 1.0, -CLAMP[1], FACE + 2.0, grip + 1.0, 0.0, IRON)                 # back under the jamb
    box(FACE + 2.0, grip - 1.75, -CLAMP[1], 1.75, grip + 1.75, -CLAMP[0], IRON_D)       # the clamp on the strand
    box(FACE + 2.0, LUG - 1.0, 0.0, eye_x + 1.5, LUG + 1.0, BAR, IRON, grain="x")       # the lug for the weight's chain
    d.box((eye_x - 1.0, LUG - 1.5, side * JAMB), (eye_x + 1.0, LUG + 1.5, side * (RUN - FOOT_R)), IRON_D, grain="z")   # its first link
    return d


# ---- the weights' runs --------------------------------------------------------------------------------
def _run(side, version="a"):
    """The run of one weight (side 1: south, -1: north), hung under the curb beside the slit: the
    rail, its hangers and its foot on the ring girder, the sheave at the top and what the weight
    hangs on. Version a: a chain from the leaf's arm, turned out of the slit's foot by a sheave
    there. Version b: a wire rope from the end of the winch's shaft. The origin is the line's
    first corner (RUN_C1) in the run's plane; the axes are the dome's."""
    b = version == "b"
    d = _Draw(("runb_" if b else "run_") + ("s" if side > 0 else "n"), 3,
              anchor=((RUN_ANCHOR[0] - RUN_C1[0]) * PX, (RUN_ANCHOR[1] - RUN_C1[1]) * PX, 0.0))
    rail, flange, knee_s, hangs = (RAIL_B, FLANGE_B, KNEE_SB, RUN_HANG_B) if b else (RAIL, FLANGE, KNEE_S, RUN_HANG)
    foot_s = WINCH_S if b else _eye()[0] + FOOT_R
    knee_d, knee_r = (UP_D + DOWN_D) / 2.0, (DOWN_D - UP_D) / 2.0
    zs = -side * FOOT_R                             # version a: the sheave at the foot stands on the slit's side of the run
    top = -0.25 if b else 0.0                       # version b: a hair under the line, where the arch girder's chord lies
    with d.turned(("z", RUN_DEG)):                  # x up the run, y towards the vault
        d.box((rail[0], -WEB_D, -1.0), (rail[1], top, 1.0), IRON_D, grain="x")
        d.box((flange[0], -FLANGE_D[1], -3.0), (flange[1], -FLANGE_D[0], 3.0), IRON, grain="x")
        for s0 in (STOP - 3.0, flange[1] - 3.0):                                # a stop at either end, on both sides of the web
            for z0 in (-3.0, 1.0):
                d.box((s0, -FLANGE_D[0], z0), (s0 + 3.0, 2.0 - FLANGE_D[0], z0 + 2.0), IRON_D, seed=201)
        if b:
            for s0 in CLEATS:                                                   # a pair of cleats, riveted to web and chord
                for z0 in (-2.5, 1.0):
                    d.box((s0, -2.25, z0), (s0 + 3.0, top, z0 + 1.5), IRON, seed=207)
            d.box((foot_s, -UP_D - ROPE, -ROPE), (knee_s, -UP_D + ROPE, ROPE), IRON_B, grain="x", seed=210)
            d.box((WEIGHT_S1 + W_HALF + 2.0, -DOWN_D - ROPE, -ROPE), (knee_s, -DOWN_D + ROPE, ROPE), IRON_B, grain="x", seed=212)
        else:
            d.tube("y", (foot_s, zs), -UP_D - 0.75, -UP_D + 0.75, FOOT_R - 0.5, IRON_B, sides=12)
            d.tube("y", (foot_s, zs), -UP_D - 1.5, -1.0, PIN, IRON_D, sides=8)      # its pin, up into the foot
            d.ring("y", (foot_s, -UP_D, zs), FOOT_R, BAND, WRAP, IRON_D, sides=8,
                   arc=(180.0, 270.0) if side > 0 else (90.0, 180.0), seed=202)
            _chain(d, "x", (-UP_D, 0.0), foot_s, knee_s, 210)
            _chain(d, "x", (-DOWN_D, 0.0), WEIGHT_S0 + W_HALF + 2.0, knee_s, 212)
        d.box((knee_s - 4.0, -WEB_D - 0.5, -3.25), (knee_s + 4.0, -1.0, 3.25), IRON)    # the hanger of the top sheave, clamped on the web
        for z0 in (-3.25, 1.75):
            d.box((knee_s - 3.0, -knee_d - 4.0, z0), (knee_s + 3.0, -WEB_D - 0.5, z0 + 1.5), IRON_D, seed=203)
        d.tube("z", (knee_s, -knee_d), -0.75, 0.75, knee_r - 0.5, IRON_B, sides=12)
        d.tube("z", (knee_s, -knee_d), -3.75, 3.75, PIN, IRON_D, sides=8)
        if b:
            d.ring("z", (knee_s, -knee_d, 0.0), knee_r, 2.0 * ROPE, 2.0 * ROPE, IRON_B, sides=12, arc=(-90.0, 90.0), seed=204)
        else:
            d.ring("z", (knee_s, -knee_d, 0.0), knee_r, BAND, WRAP, IRON_D, sides=12, arc=(-90.0, 90.0), seed=204)
    if not b:
        _hangers(d, side, hangs)
    return d


def _hangers(d, side, hangs):
    """What hangs a run's rail from the curb: a strap at each of the line's corners and the foot on
    the ring girder. Drawn from the line's first corner, as the run is."""
    for i, hang in enumerate(hangs):                # a hanger at the line's corners: a strap that
        cx, cy = i * RUN_STEP[0] * PX, i * RUN_STEP[1] * PX         # clasps the web, up to a plate under the curb
        top = cy + hang * PX
        d.box((cx - 3.0, cy - 7.0, -2.0), (cx - 1.0, top - 1.0, 2.0), IRON_D, grain="y", seed=205)
        d.box((cx - 5.0, top - 1.0, -3.0), (cx, top, 3.0), IRON, seed=206)
    fx, fy = -RUN_STEP[0] * PX, -RUN_STEP[1] * PX   # where the line starts: the ring girder's corner under the jamb
    z0, z1 = sorted((-side * 4.5, side * 2.0))
    d.box((fx, fy + 1.0, z0), (fx + 4.5, fy + 7.0, z1), IRON)                   # the foot: holds the web's end (and, in a, the sheave's pin)


def _hang(side):
    """The straps and the foot of a rail of version b, for a room that has no arch girders yet."""
    d = _Draw("hang_s" if side > 0 else "hang_n", 3,
              anchor=((RUN_ANCHOR[0] - RUN_C1[0]) * PX, (RUN_ANCHOR[1] - RUN_C1[1]) * PX, 0.0))
    _hangers(d, side, RUN_HANG_B)
    return d


def _weight():
    """A weight on its carriage: four wheels on the rail's flange, two hangers, old-copper slabs
    between iron end plates. The model lies along its rail (x up the run, y towards the vault) and
    is shown turned RUN_DEG about z; its origin is the carriage's middle on the run's line."""
    d = _Draw("weight", 1)
    axle = W_WHEEL_R - FLANGE_D[0]
    for x in (-W_WHEEL, W_WHEEL):
        for z0 in (-2.75, 1.25):
            d.tube("z", (x, axle), z0, z0 + 1.5, W_WHEEL_R, IRON_B, sides=8, seed=301)
        for z0 in (-4.25, 1.25):
            d.tube("z", (x, axle), z0, z0 + 3.0, 0.5, IRON_D, sides=4, seed=302)
    for z0 in (-4.25, 3.25):
        d.box((-7.0, -12.5, z0), (7.0, -1.5, z0 + 1.0), IRON_D, seed=303)
    for i in range(4):                                                          # four slabs, every other one a little smaller
        x0, g = -8.0 + 4.0 * i, 0.5 * (i % 2)
        d.box((x0, g - 18.0, g - 3.25), (x0 + 4.0, -11.0 - g, 3.25 - g), COPPER, seed=304 + i % 2)
    for x0 in (-W_HALF, W_HALF - 1.0):
        d.box((x0, -18.5, -3.75), (x0 + 1.0, -10.5, 3.75), IRON_D, seed=306)
    d.box((W_HALF, -DOWN_D - 1.0, -1.0), (W_HALF + 2.0, 1.0 - DOWN_D, 1.0), IRON)       # the eye the chain is made fast to
    return d


# ---- the curtain's roller (version b): these pieces share the origin roll_at() on the dome's meridian ----
def _roll():
    """The curtain on its roller: LATHS slats to a turn, every third of the darker copper, between
    two iron cheeks on a shaft that runs on into the pockets behind the rails' feet. Turns about
    its shaft, which runs along z."""
    d = _Draw("roll", 3)
    leaves = slope(BAR_DEG) + 90.0                  # where the curtain leaves the roll, from its axis
    out = ROLL_R + LATH_T / 2.0
    for k in range(LATHS):                          # the outermost turn: every slat stands a little off the next
        d.box((out - LATH_T, 0.375 - LATH / 2.0, -ROLL_HALF), (out, LATH / 2.0 - 0.375, ROLL_HALF), SLAT_D if k % 3 == 2 else SLAT,
              rot=("z", leaves + (k + 0.5) * 360.0 / LATHS, (0.0, 0.0, 0.0)), grain="z", seed=601 + k % 3)
    d.tube("z", (0.0, 0.0), -ROLL_HALF, ROLL_HALF, out - 0.75, SEAM, sides=LATHS, seed=606)     # the turns under it
    for side in (-1, 1):
        z0, z1 = sorted((side * ROLL_HALF, side * (ROLL_HALF + 1.5)))
        d.tube("z", (0.0, 0.0), z0, z1, out + 1.0, IRON_D, sides=LATHS, seed=604)       # a cheek
    d.tube("z", (0.0, 0.0), -RUN - 2.0, RUN + 2.0, 1.5, IRON, sides=8)
    for side in (-1, 1):                            # the ends, turned down: a take-up weight's cord lies on each
        z0, z1 = sorted((side * (RUN + 2.0), side * (RUN + 6.0)))
        d.tube("z", (0.0, 0.0), z0, z1, CORD_R - 0.375, IRON_D, sides=8, seed=605)
    return d


def _rollseat():
    """What carries the roller: at either end a bearing on a bracket from the rail's foot, and
    under it the small weight that keeps the roll wound, on a cord round the shaft's end. The cord
    leaves the shaft on the curtain's side: drawing the curtain winds it up."""
    d = _Draw("rollseat", 3)
    cx, cy = roll_at()
    face = (-(SHELL_A - 1.0) - cx) * PX             # the rail's face towards the room: the plates are one block thick
    low = (RING_Y - cy) * PX + 1.0                  # the weight hangs in the ring girder's row and no lower: it rides round with the dome
    for side in (-1, 1):
        def box(x0, y0, z0, x1, y1, z1, mat, **kw):
            d.box((x0, y0, side * z0), (x1, y1, side * z1), mat, **kw)

        box(face, -6.0, RUN - 5.0, face + 1.0, 6.0, RUN + 2.0, IRON_D, seed=611)        # the plate on the rail
        box(face + 1.0, -2.0, RUN - 3.0, -2.5, 2.0, RUN + 1.0, IRON_D, grain="x", seed=612)
        box(-3.0, -3.0, RUN - 3.5, 3.0, 3.0, RUN + 1.5, IRON, seed=613)                 # the bearing
        box(-CORD_R - 0.5, low + 7.0, RUN + 3.5, -CORD_R + 0.5, 0.0, RUN + 4.5, IRON_B, grain="y", seed=614)    # the cord
        box(-3.5, low, RUN + 1.75, 2.0, low + 7.0, RUN + 6.25, IRON, seed=615)          # its weight
        # the lining of the pocket the weight hangs in: an iron plate on the pocket's outer side,
        # which is the back of the dome's copper skin and would show green into the room (dome
        # #70004); three rows high, the plate's own rivets at its corners
        wall = RUN + PX / 2.0
        box(face, low - 1.0, wall - 0.5, face + PX, low - 1.0 + 3.0 * PX, wall, IRON_D, seed=616)
        for x in (face + 1.5, face + PX - 2.5):
            for y in (low + 0.5, low + PX, low + 2.0 * PX, low + 3.0 * PX - 3.5):
                box(x, y, wall - 1.0, x + 1.0, y + 1.0, wall - 0.5, IRON_B, seed=617)
    return d


def _bar():
    """The curtain's bar with the slats between it and the roll, and an eye for a hauling chain at
    either end. The origin is the bar's middle (on_curve(BAR_DEG)) on the dome's meridian; the
    piece lies along the curtain's path there, and runs up it: it turns about the line along z
    through CURTAIN_C, and the model's anchor lies on that line."""
    bx, by = on_curve(BAR_DEG)
    d = _Draw("bar", 3, anchor=((CURTAIN_C[0] - bx) * PX, (CURTAIN_C[1] - by) * PX, 0.0))
    with d.turned(("z", slope(BAR_DEG))):           # x up the path, y out through the dome's skin
        d.box((-ROD / 2.0, -ROD / 2.0, -ROLL_HALF - 1.5), (ROD / 2.0, ROD / 2.0, ROLL_HALF + 1.5), IRON, grain="z")
        for i in range(TAIL):
            x1 = -ROD / 2.0 - i * LATH
            d.box((x1 - LATH, -LATH_T / 2.0, -ROLL_HALF), (x1, LATH_T / 2.0, ROLL_HALF), SLAT_D if i % 3 == 1 else SLAT,
                  grain="z", seed=621 + i % 3)
        for side in (-1, 1):
            z0, z1 = sorted((side * (HAUL_Z - 1.0), side * (HAUL_Z + 1.0)))
            d.box((ROD / 2.0, -1.5, z0), (ROD / 2.0 + 2.0, 1.5, z1), IRON_D, seed=624)
    return d


def _lath_phase(k):
    """Which of the three models the curtain's k-th length is: every third slat is of the darker
    copper, counted on from the bar's own slats."""
    return (TAIL + k * PANEL_LATHS) % 3


def _laths(phase):
    """One length of the curtain behind the bar, PANEL_LATHS slats on the circle about CURTAIN_C,
    as it lies parked in the wall under the slit's foot: its upper edge PARK_DEG below the bar at
    rest. The origin is CURTAIN_C, the axes are the dome's; it turns about the line along z
    through the origin. phase: the first slat's place in the run of three (_lath_phase())."""
    d = _Draw(f"laths{phase}", 3)
    r = CURTAIN_R * PX
    for j in range(PANEL_LATHS):
        with d.turned(("z", CURTAIN_POLAR + PARK_DEG + (j + 0.5) * LATH_DEG)):      # x out through the dome's skin, y down the path
            d.box((r - LATH_T / 2.0, -LATH / 2.0, -ROLL_HALF), (r + LATH_T / 2.0, LATH / 2.0, ROLL_HALF),
                  SLAT_D if (phase + j) % 3 == 1 else SLAT, grain="z", seed=681 + (phase + j) % 3)
    return d


# ---- the winch (version b): these pieces share the origin winch_at() on the dome's meridian ----------------
def _winch():
    """The winch: a shaft across the slit's foot with the hand-chain wheel in its middle, a ratchet
    wheel beside that, a grooved drum for each hauling chain and, on its turned-down ends, the
    weights' ropes. Turns about the shaft, which runs along z."""
    d = _Draw("winch", 3)
    d.tube("z", (0.0, 0.0), -RUN + 3.0, RUN - 3.0, SHAFT, IRON_D, sides=8)
    d.ring("z", (0.0, 0.0, 0.0), WHEEL_RB - 1.25, 2.0, 2.0, IRON_B, sides=16)           # the wheel's rim, under the hand chain
    for i in range(3):                                                          # three bars: six spokes
        d.box((-WHEEL_RB + 2.0, -1.0, -0.5), (WHEEL_RB - 2.0, 1.0, 0.5), IRON_D, rot=("z", 30.0 + 60.0 * i, (0.0, 0.0, 0.0)),
              grain="x", seed=631)
    d.tube("z", (0.0, 0.0), -1.5, 1.5, 2.0, IRON_D, sides=8)
    d.tube("z", (0.0, 0.0), 9.5, 11.5, 3.0, IRON, sides=8)                      # the ratchet wheel, south of the wheel's bearing
    for i in range(8):
        d.box((2.5, -0.75, 9.5), (4.5, 0.75, 11.5), IRON_B, rot=("z", 45.0 * i + 22.5, (0.0, 0.0, 10.5)), seed=632)
    for side in (-1, 1):
        z0, z1 = sorted((side * (HAUL_Z + 3.0 - DRUM_W), side * (HAUL_Z + 3.0)))
        d.tube("z", (0.0, 0.0), z0, z1, DRUM_R - 1.0, IRON, sides=12, seed=633)         # a drum's barrel,
        for z in (HAUL_Z + 2.5 - DRUM_W, HAUL_Z + 3.0):
            f0, f1 = sorted((side * z, side * (z + 0.5)))
            d.tube("z", (0.0, 0.0), f0, f1, DRUM_R + 1.25, IRON_D, sides=12, seed=634)  # its flanges,
        for k in range(1, int(DRUM_W / 3.0) - 1):                               # the groove the chain beds in
            d.ring("z", (0.0, 0.0, side * (HAUL_Z + 3.0 - DRUM_W + 3.0 * k)), DRUM_R - 0.875, 0.5, 0.75, IRON_D, sides=12, seed=638)
        for z in (HAUL_Z - 1.5, HAUL_Z + 1.5):                                  # and the two turns that stay on it: the chain
            d.ring("z", (0.0, 0.0, side * z), DRUM_R, BAND, WRAP, IRON_B, sides=12, seed=635)   # winds on from the rail's end
        e0, e1 = sorted((side * (RUN - 3.0), side * (RUN + 2.0)))
        d.tube("z", (0.0, 0.0), e0, e1, ROPE_R - ROPE, IRON_D, sides=8, seed=636)       # the end, turned down
        d.ring("z", (0.0, 0.0, side * RUN), ROPE_R, 2.0 * ROPE, 3.0, IRON_B, sides=8, seed=637)        # the rope on it
    return d


def _winchseat():
    """What carries the winch: a forked bracket out from the ring girder on the dome's meridian,
    a bearing either side of the hand-chain wheel; a bracket with a bearing from the foot of the
    arch girder beside the slit, outside either drum; the pawl on the fork, in the ratchet wheel."""
    d = _Draw("winchseat", 3)
    wx, wy = winch_at()
    back = (FACE_X - 1.0 - wx) * PX                 # the ring girder's face on the meridian,
    face = (FACE_X - wx) * PX                       # and beside the slit
    low, high = (RING_Y - wy) * PX + 0.5, (SILL_Y - wy) * PX - 0.5
    d.box((back, low, -8.0), (back + 1.0, high, 8.0), IRON_D)                           # the plate on the ring girder
    for z in (-6.0, 6.0):
        d.box((back + 1.0, -4.5, z - 1.0), (7.5 if z > 0 else 2.5, -2.5, z + 1.0), IRON_D, grain="x", seed=641)    # an arm of the fork
        d.box((-2.5, -2.5, z - 1.5), (2.5, 2.5, z + 1.5), IRON, seed=642)                # its bearing
    d.box((back + 1.0, -4.5, -5.0), (back + 3.0, -2.5, 5.0), IRON_D, grain="z", seed=643)       # the fork's root
    # the pawl: on a post at the south arm's end, its nose in the ratchet wheel from the room's
    # side, so that the wheel cannot run back (the chains come down on the drums' far side)
    d.box((5.5, -2.5, 5.0), (7.5, 6.0, 7.0), IRON_D, grain="y", seed=644)
    d.tube("z", (6.5, 5.0), 7.0, 11.5, 0.75, IRON_D, sides=8, seed=645)
    d.box((2.5, 4.4, 9.9), (7.0, 5.6, 11.1), IRON_B, rot=("z", 26.0, (6.5, 5.0, 10.5)), grain="x", seed=646)
    for side in (-1, 1):
        z0, z1 = sorted((side * (HAUL_Z + 4.75), side * (HAUL_Z + 7.25)))
        d.box((face, -4.5, z0 - 1.0), (face + 1.0, 4.5, z1 + 1.0), IRON_D, seed=647)     # the plate on the arch girder's foot
        d.box((face + 1.0, -2.5, z0), (2.5, 2.5, z1), IRON, grain="x", seed=648)         # the bracket and its bearing
    return d


def _pull():
    """The winch's hand chain: an endless loop over its wheel, down to where a hand reaches it."""
    d = _Draw("pull", 3)
    low = (HANDCHAIN_Y - winch_at()[1]) * PX
    d.ring("z", (0.0, 0.0, 0.0), WHEEL_RB, BAND, WRAP, IRON_D, sides=12, arc=(0.0, 180.0), seed=651)
    d.ring("z", (0.0, low, 0.0), WHEEL_RB, BAND, WRAP, IRON_D, sides=12, arc=(180.0, 360.0), seed=651)
    for x in (-WHEEL_RB, WHEEL_RB):
        _chain(d, "y", (x, 0.0), low, 0.0, 652)
    return d


# ---- the hauling chains (version b) ---------------------------------------------------------------------------
def _links(d, stations, length, z, seed):
    """Chain links, seen from the side, with their middles at stations [(x, y, slope)] (px)."""
    for i, (x, y, way) in enumerate(stations):
        across, wide = (1.5, 1.0) if i % 2 == 0 else (1.0, 1.5)
        d.box((x - length / 2.0, y - across, z - wide), (x + length / 2.0, y + across, z + wide),
              IRON_B if i % 2 == 0 else IRON, rot=("z", way, (x, y, z)), grain="x", seed=seed + i % 2)


def _haul(side):
    """One hauling chain (side 1: south, -1: north) and what the rail carries for it: up the
    curtain's path from the bar to the sheave at the slit's head, back under it to LEAVE_DEG and
    straight down to its drum on the winch; at every one of HANGERS a plate on the rail's face
    with a roller under each way of the chain (the curtain's edge runs on the upper ones). The
    origin is the bar's end of the chain; x and y are the dome's, px from its axis and the ledge."""
    bx, by = on_curve(BAR_DEG)
    z = side * HAUL_Z

    def px(at):
        return at[0] * PX, (at[1] - LEDGE_Y) * PX

    d = _Draw("haul_s" if side > 0 else "haul_n", 4, anchor=px((bx, by)) + (z,))
    eye = BAR_DEG + (ROD / 2.0 + 2.0) / PX / along(BAR_DEG, BAR_DEG + 1.0)     # the chain starts at the bar's eye
    up, length = _stations(eye, HEAD_DEG)
    _links(d, [px(at) + (at[2],) for at in up], length, z, 661)
    back, length = _stations(HEAD_DEG, LEAVE_DEG, GAP)
    _links(d, [px(at) + (at[2],) for at in back], length, z, 663)
    (lx, ly), (tx, ty) = (px(at) for at in _drop())
    fall = math.hypot(tx - lx, ty - ly)
    n = max(1, int(round(fall / LINK)))
    way = math.degrees(math.atan2(ty - ly, tx - lx))
    _links(d, [(lx + (tx - lx) * (k + 0.5) / n, ly + (ty - ly) * (k + 0.5) / n, way) for k in range(n)], fall / n, z, 665)

    hx, hy = px(on_curve(HEAD_DEG, GAP / 2.0))      # the sheave at the head, on a pin from the rail
    turn = slope(HEAD_DEG, GAP / 2.0)
    z0, z1 = sorted((side * (HAUL_Z - 2.5), side * (JAMB - 1.0)))
    d.tube("z", (hx, hy), z - 0.75, z + 0.75, GAP / 2.0 - 0.5, IRON_B, sides=12)
    d.tube("z", (hx, hy), z0, z1, PIN, IRON_D, sides=8)
    d.ring("z", (hx, hy, z), GAP / 2.0, BAND, WRAP, IRON, sides=12, arc=(turn - 90.0, turn + 90.0), seed=667)
    with d.turned(("z", turn), about=(hx, hy, 0.0)):
        d.box((hx - 4.0, hy - 5.0, side * (JAMB - 1.0)), (hx + 4.0, hy + 4.0, side * JAMB), IRON_D, seed=668)
    for deg in HANGERS:
        x, y = px(on_curve(deg))
        both = deg >= LEAVE_DEG
        with d.turned(("z", slope(deg)), about=(x, y, 0.0)):        # x up the path, y out through the skin
            d.box((x - 2.0, y - (GAP + 5.0 if both else 5.0), side * (JAMB - 1.0)), (x + 2.0, y + 1.5, side * JAMB), IRON_D,
                  grain="y", seed=669)
            for inside in ((0.0, GAP) if both else (0.0,)):
                d.tube("z", (x, y - inside - 2.5), z0, z1, 1.0, IRON_B, sides=8, seed=670)
    return d


_PIECES = {
    "rail": _rail, "trucks": _trucks, "riser": _riser, "pedestal": _pedestal, "handwheel": _handwheel, "brackets": _brackets,
    "foot": _foot, "drive": _drive, "handchain": _handchain, "weight": _weight,
    "arm_n": lambda: _arm(-1), "arm_s": lambda: _arm(1), "run_n": lambda: _run(-1), "run_s": lambda: _run(1),
    "roll": _roll, "rollseat": _rollseat, "bar": _bar, "winch": _winch, "winchseat": _winchseat, "pull": _pull,
    "haul_n": lambda: _haul(-1), "haul_s": lambda: _haul(1),
    "laths0": lambda: _laths(0), "laths1": lambda: _laths(1), "laths2": lambda: _laths(2),
    "runb_n": lambda: _run(-1, "b"), "runb_s": lambda: _run(1, "b"), "hang_n": lambda: _hang(-1), "hang_s": lambda: _hang(1),
}


@functools.lru_cache(maxsize=None)
def _piece(name):
    d = _PIECES[name]()
    if d.m.name != PREFIX + name:
        raise ValueError(f"the piece {name} draws the model {d.m.name}")
    # The shafts, wheels, sheaves and drums are tubes and rings of eight, twelve and sixteen sides,
    # and a flat of such a piece that stands exactly between two axes is lit by the game as the one
    # or the other by the last bit of a float: of two wheels of one kind one came out light and one
    # dark (cr3 counted 96 such faces on the models with K.unsettled, 11-16). K.settle turns each such piece a
    # tenth of a degree about its own middle, so every copy of the game lights it one way
    K.settle(d.m)
    return d


def unsettled():
    """The drawn faces that still stand between two axes, of every piece of both versions:
    [(piece, part's index, face letters)]."""
    return [(name, i, letters) for name in sorted(_PIECES) for i, letters, _normal in K.unsettled(_piece(name).m)]


def models(version=None):
    """The models of the pieces that stand: of the version of main/dome that is in the tree, or of
    the one named."""
    return {_piece(name).m.name: _piece(name).m for name in sorted({item[0] for item in layout(version)})}


# ---- placing ----------------------------------------------------------------------------------------------
def layout(version=None):
    """[(piece, place, yaw, turns)] of the whole gear; a place is (x from the dome's axis, y, z from
    the dome's axis). version: main/dome's, read from that package when left out."""
    version = shell_version() if version is None else version
    out = []
    for deg in length_angles():
        x, z = on_rail(deg)
        out.append(("rail", (x, LEDGE_Y, z), deg, ()))
        out.append(("trucks", (0.0, LEDGE_Y, 0.0), deg, ()))        # its entity stands on the dome's axis: it turns about it
    rx, rz = riser_at()
    for name in HAND_PIECES:
        out.append((name, (rx, FLOOR_Y + HAND_H / PX, rz), 0.0, ()))
    if version == "a":
        for name in ("foot", "drive", "handchain", "arm_n", "arm_s"):
            out.append((name, F0, 0.0, ()))
        wx, wy = on_run(WEIGHT_S0)
        for side, name in ((-1, "run_n"), (1, "run_s")):
            out.append((name, (RUN_ANCHOR[0], RUN_ANCHOR[1], side * RUN_Z), 0.0, ()))
            out.append(("weight", (wx, wy, side * RUN_Z), 0.0, (("z", RUN_DEG),)))
    elif version == "b":
        for name in ("roll", "rollseat"):
            out.append((name, roll_at() + (0.0,), 0.0, ()))
        out.append(("bar", CURTAIN_C + (0.0,), 0.0, ()))            # the bar and the curtain's lengths stand on the line they turn about
        for k in range(PANELS):
            out.append((f"laths{_lath_phase(k)}", CURTAIN_C + (0.0,), 0.0, ()))
        for name in ("winch", "winchseat", "pull"):
            out.append((name, winch_at() + (0.0,), 0.0, ()))
        wx, wy = on_run(WEIGHT_S1)
        for side, tag in ((-1, "n"), (1, "s")):
            out.append(("haul_" + tag, on_curve(BAR_DEG) + (side * HAUL_Z / PX,), 0.0, ()))
            for name in ("runb_",) if riveted() else ("runb_", "hang_"):
                out.append((name + tag, (RUN_ANCHOR[0], RUN_ANCHOR[1], side * RUN_Z), 0.0, ()))
            out.append(("weight", (wx, wy, side * RUN_Z), 0.0, (("z", RUN_DEG),)))
    return out


def barrier_cells(origin=(0, 0, 0)):
    """The cells that are given a barrier: the foot of the upright shaft's column of the wall."""
    return tuple((origin[0] + RISER_CELL[0], origin[1] + int(FLOOR_Y) + row, origin[2] + RISER_CELL[1])
                 for row in range(BARRIER_ROWS))


def place(canvas, origin=(0, 0, 0), version=None):
    """The whole gear round DOME_AXIS, and its barrier where nothing stands yet. Returns the number
    of display entities."""
    ox, oy, oz = origin
    version = shell_version() if version is None else version
    for cell in barrier_cells(origin):
        canvas.set(*cell, B.BARRIER, keep=True)
    n = 0
    deg, period, keys, sign = turning()
    moves, panel, still = curtain_moves(), 0, _still()
    for name, (x, y, z), yaw, turns in layout(version):
        d = _piece(name)
        part = "bar" if name == "bar" else ("laths", panel) if name.startswith("laths") else None
        if part is not None:                                        # the curtain is out under the sky
            sky = CURTAIN_LIGHT
            if still:                                               # a still picture of the curtain on its way: where it is by then
                start, far, ticks = moves[part][0]
                turns = turns + (("z", -far * max(0.0, min(1.0, (still * CURTAIN_TICKS - (start - CURTAIN_AT)) / ticks))),)
        else:
            sky = night(*(on_rail(yaw) if name == "trucks" else (x, z)))    # a length's light is that of its place on the ledge
        canvas.add_entity(ox + AX + x, oy + y, oz + AZ + z,
                          M.display(d.m, yaw=yaw, scale=d.scale, turns=turns, brightness=(sky, 0)))
        n += 1
        panel += name.startswith("laths")
        if part is not None and still:                              # shown on its way, it stays there
            continue
        # What moves is set going as it is placed (motion/_kit). The ring, its pinion's shaft and the
        # hand wheel swing in one period, so they are one chain and stay in mesh: sixteen turns of
        # the upright shaft to one of the ring, the same way round (the ring's teeth look inwards),
        # and HAND_GEAR of the hand wheel to one of the shaft
        if name == "trucks":
            MK.swing(canvas, (0.0, 1.0, 0.0), deg, sign * period, keys=keys, name=f"{PREFIX}trucks.{int(round(yaw))}")
        elif name == "riser":
            MK.swing(canvas, (0.0, 1.0, 0.0), deg * RACK_TEETH / PINION_TEETH, sign * period, keys=keys)
        elif name == "handwheel":
            MK.swing(canvas, (1.0, 0.0, 0.0), deg * RACK_TEETH / PINION_TEETH * HAND_GEAR, sign * period, keys=keys)
        elif name == "pull":                            # the hand chain hangs in the slit's draught
            MK.swing(canvas, (0.0, 0.0, 1.0), *PULL_SWAY)
        # The slit is shut and opened once in CURTAIN_CYCLE ticks (curtain_moves()): the bar and the
        # curtain's lengths turn about the line through CURTAIN_C, the roll pays the curtain out, the
        # winch winds the hauling chains the other way round and lets the weights down their rails
        elif name == "bar":
            MK.turn(canvas, CURTAIN_AXIS, moves[part], CURTAIN_CYCLE)
        elif name.startswith("laths"):
            MK.turn(canvas, CURTAIN_AXIS, moves[part], CURTAIN_CYCLE, name=f"{PREFIX}curtain.{part[1]}")
        elif name == "roll":
            MK.turn(canvas, CURTAIN_AXIS, moves["roll"], CURTAIN_CYCLE)
        elif name == "winch":
            MK.turn(canvas, (0.0, 0.0, 1.0), moves["winch"], CURTAIN_CYCLE)
        elif name == "weight" and version == "b":
            down = math.radians(RUN_DEG + 180.0)
            MK.slide(canvas, (math.cos(down), math.sin(down), 0.0), moves["weight"], CURTAIN_CYCLE,
                     name=f"{PREFIX}weight.{'n' if z < 0 else 's'}")
    return n


def _turn(q, v):
    """The vector v turned by the unit quaternion q = (x, y, z, w)."""
    x, y, z, w = q
    tx, ty, tz = 2.0 * (y * v[2] - z * v[1]), 2.0 * (z * v[0] - x * v[2]), 2.0 * (x * v[1] - y * v[0])
    return (v[0] + w * tx + y * tz - z * ty, v[1] + w * ty + z * tx - x * tz, v[2] + w * tz + x * ty - y * tx)


def _spots(d, yaw, turns):
    """Points of a piece as it stands, in blocks from its entity: the middle of every part and its
    corners, drawn in by a tenth so that a face lying against a block does not count."""
    m, k = d.m, d.scale / PX
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    signs = [(0, 0, 0)] + [(a, b, e) for a in (-1, 1) for b in (-1, 1) for e in (-1, 1)]
    for p in m.parts:
        mid = [(p["lo"][i] + p["hi"][i]) / 2.0 for i in range(3)]
        half = [(p["hi"][i] - p["lo"][i]) * 0.45 for i in range(3)]
        q = p["rot"][0] if p["rot"] else M.IDENT
        for sign in signs:
            v = _turn(q, [sign[i] * half[i] for i in range(3)])
            v = [mid[i] + v[i] - m.anchor[i] for i in range(3)]
            for axis, deg in turns:
                v = _turn(M.quat(axis, deg), v)
            yield ((v[0] * c - v[2] * s) * k, v[1] * k, (v[0] * s + v[2] * c) * k)


def clash(canvas, origin=(0, 0, 0), version=None, ignore=("light",)):
    """Where the gear stands in something: [(piece, cell, block)] for every cell that holds a block
    and one of a piece's points (see _spots). For the test scene, to be read with the plan in
    hand: a stair or a slab that a part only lies against is listed too."""
    ox, oy, oz = origin
    own = set(barrier_cells(origin))
    out = []
    for name, (x, y, z), yaw, turns, drawn in _poses(version):
        at = (ox + AX + x, oy + y, oz + AZ + z)
        seen = set()
        for p in _spots(_piece(name), yaw, turns):
            if drawn and at[1] + p[1] < oy + SILL_Y:    # the curtain under the sill's top: in the wall, as it is meant to be (shown())
                continue
            cell = tuple(int(math.floor(at[i] + p[i])) for i in range(3))
            if cell in seen:
                continue
            seen.add(cell)
            block = canvas.get(*cell)
            if block is None or _kind(block) in ignore or (cell in own and _kind(block) == B.BARRIER):
                continue
            out.append((name, cell, block))
    return out


def _poses(version=None):
    """layout() with what moves in the poses it is to be tried in as well: [(piece, place, yaw,
    turns, drawn)]. The ring's lengths at both ends of the dome's swing; the bar and the curtain's
    lengths every two degrees of their way up the slit, and drawn is True for those."""
    swing = turning()[0]
    moves, panel = curtain_moves(), 0
    out = []
    for name, at, yaw, turns in layout(version):
        if name == "trucks":
            out += [(name, at, way, turns, False) for way in (yaw - swing, yaw, yaw + swing)]
        elif name == "bar" or name.startswith("laths"):
            far = moves["bar"][0][1] if name == "bar" else moves["laths", panel][0][1]
            panel += name != "bar"
            n = int(math.ceil(far / 2.0))
            out += [(name, at, yaw, turns + (("z", -far * i / n),), True) for i in range(n + 1)]
        else:
            out.append((name, at, yaw, turns, False))
    return out


def shown(canvas, origin=(0, 0, 0), version=None):
    """Where the curtain that is not drawn could be seen: [(piece, cell, block)] for every cell
    that holds a point of a parked length and is not a whole block one cannot see through. Empty
    when the wall under the slit's foot hides them. With clash(), for the test scene."""
    ox, oy, oz = origin
    out = []
    for name, (x, y, z), yaw, turns in layout(version):
        if not name.startswith("laths"):
            continue
        at = (ox + AX + x, oy + y, oz + AZ + z)
        seen = set()
        for p in _spots(_piece(name), yaw, turns):
            cell = tuple(int(math.floor(at[i] + p[i])) for i in range(3))
            if cell in seen:
                continue
            seen.add(cell)
            block = canvas.get(*cell)
            if block is None or any(word in _kind(block) for word in SEEN_THROUGH):
                out.append((name, cell, block))
    return out


def _kind(block):
    return block.partition("[")[0].rpartition(":")[2]


# kinds of block that do not hide what stands inside them: not a whole cube, or one that is seen through
SEEN_THROUGH = ("glass", "slab", "stairs", "door", "fence", "wall", "pane", "bars", "chain", "carpet", "light", "barrier",
                "leaves", "button", "lever", "rod", "torch", "lantern", "ladder", "rail", "sign", "banner", "air")


def barred(canvas, origin=(0, 0, 0), version=None, ignore=("light",)):
    """Where the barrier is not inside the gear: [(what, cell)]. A barrier's cell must hold the
    barrier and a part of the hand gear, and on every side that is open to the room the gear must
    stand out past the cell's face, so that one meets what is seen before what is not. Empty when
    the collision is the gear's own. With clash() and unheld(), for the test scene."""
    ox, oy, oz = origin
    held = set()                                        # the cells the hand gear has a point in
    for name, (x, y, z), yaw, turns in layout(version):
        if name in HAND_PIECES:
            at = (ox + AX + x, oy + y, oz + AZ + z)
            held |= {tuple(int(math.floor(at[i] + p[i])) for i in range(3)) for p in _spots(_piece(name), yaw, turns)}
    out = []
    for cell in barrier_cells(origin):
        block = canvas.get(*cell)
        if block is None or _kind(block) != B.BARRIER:
            out.append((f"no barrier: the cell holds {block}", cell))
        if cell not in held:
            out.append(("no part of the hand gear in the cell", cell))
        for dx, dz, side in ((1, 0, "east"), (-1, 0, "west"), (0, 1, "south"), (0, -1, "north")):
            beside = (cell[0] + dx, cell[1], cell[2] + dz)
            block = canvas.get(*beside)
            if (block is None or _kind(block) in ignore) and beside not in held:
                out.append((f"open to the {side}, and the gear does not stand out past that face", cell))
    return out


def _held(version):
    """[(piece, (x, y, z) from the dome's axis)]: a point in every cell the gear is fixed to."""
    out = []
    for deg in seam_angles():
        x, z = RAIL_R * math.cos(math.radians(deg)), RAIL_R * math.sin(math.radians(deg))
        out += [("rail: the ledge under it", (x, LEDGE_Y - 0.5, z)), ("trucks: the ring girder on a truck", (x, RING_Y + 0.5, z))]
    rx, rz = riser_at()
    cx, cz = RISER_CELL[0] - AX, RISER_CELL[1] - AZ
    out += [("pedestal: the floor", (rx, FLOOR_Y - 0.5, rz)), ("brackets: the wall west of the shaft", (cx - 0.5, FLOOR_Y + 3.5, cz + 0.5))]
    if version == "a":
        out.append(("foot: the ring girder on the meridian", (F0[0] + (BACK - 8.0) / PX, F0[1], 0.0)))
        for side in (-1, 1):
            z = side * RUN_Z
            out += [("foot: the ring girder behind a corner wheel", (FACE_X - 0.5, F0[1], side * IDLER_Z / PX)),
                    ("arm: the leaf's stile", (STILE_X, SILL_Y + 0.5, z)),
                    ("run: the ring girder at its foot", (FACE_X - 0.5, SILL_Y + 0.5, z))]
            for i, hang in enumerate(RUN_HANG):
                out.append(("run: the curb over a hanger", (RUN_C1[0] + i * RUN_STEP[0] - 0.125, RUN_C1[1] + i * RUN_STEP[1] + hang + 0.5, z)))
    elif version == "b":
        out.append(("winchseat: the ring girder on the meridian", (FACE_X - 1.5, RING_Y + 0.5, 0.0)))
        hx, hy = on_curve(HEAD_DEG, GAP / 2.0)
        for side in (-1, 1):
            z = side * RUN_Z
            rail = side * (JAMB + 4.0) / PX
            out += [("rollseat: the rail's foot beside the roller", (-(SHELL_A - 0.5), roll_at()[1], rail)),
                    ("winchseat: the arch girder's foot beside a drum", (FACE_X - 0.5, winch_at()[1], side * (HAUL_Z + 6.0) / PX)),
                    ("haul: the rail beside the head sheave", (hx, hy, rail))]
            for deg in HANGERS:
                out.append((f"haul: the rail behind the rollers at {deg:g}", on_curve(deg) + (rail,)))
            if not riveted():
                out.append(("hang: the ring girder at the rail's foot", (FACE_X - 0.5, SILL_Y + 0.5, z)))
                for i, hang in enumerate(RUN_HANG_B):
                    out.append(("hang: the curb over a strap", (RUN_C1[0] + i * RUN_STEP[0] - 0.125, RUN_C1[1] + i * RUN_STEP[1] + hang + 0.5, z)))
    return out


def unheld(canvas, origin=(0, 0, 0), version=None):
    """What the gear would hang on and finds empty: [(what, cell)]. With clash(), for the test
    scene: both lists are empty when the gear fits the shell and the room that stand on the canvas."""
    version = shell_version() if version is None else version
    ox, oy, oz = origin
    out = []
    for what, (x, y, z) in _held(version):
        cell = (int(math.floor(ox + AX + x)), int(math.floor(oy + y)), int(math.floor(oz + AZ + z)))
        if canvas.get(*cell) is None:
            out.append((what, cell))
    if version == "b" and riveted():
        out += _off_the_girders(origin)
    return out


def _off_the_girders(origin=(0, 0, 0)):
    """Where a rail of version b leaves the underside of interiors/domeroom's arch girders:
    [(what, cell)], empty when the rail lies under their straight springing from end to end."""
    frame = neighbour("interiors", "domeroom").frame()
    ends = [on_run(s) for s in RAIL_B]
    cells = [(int(math.floor(origin[0] + AX + x)), int(math.floor(origin[1] + y)), int(math.floor(origin[2] + AZ + RUN_Z))) for x, y in ends]
    if frame is None:
        return [("run: the room has no arch girders", cells[0])]
    (d0, y0), (d1, y1) = frame.run()                # (distance from the axis along the slit, height): at the pier, where the line ends
    out = []
    for (x, y), cell in zip(ends, cells):
        line = y0 + (y1 - y0) * (d0 + x) / (d0 - d1)
        if not d1 - 1e-6 <= -x <= d0 + 1e-6:
            out.append(("run: the rail runs past the straight underside of the arch girder", cell))
        elif abs(line - y) > 0.5 / PX:
            out.append((f"run: the rail lies {(y - line) * PX:+.2f} px off the arch girder's underside", cell))
    return out


def build(canvas, origin=(0, 0, 0)):
    return place(canvas, origin) if MOVED_IN else 0
