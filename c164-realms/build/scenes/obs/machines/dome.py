"""machines/dome: the gear of the great dome (plan ART-PLAN 5.2 and 7.2; parts/A5-machines.md 2.2;
card packages/machines/domegear.md). What turns the dome and what opens its slit, seen from the
dome room (view V8, in one picture with the great refractor).

Two trains, each to be read from the hand to the load.

  Turning the dome. A rail lies on the ledge of the drum. Under every seam of the dome's twenty
  gores a truck with one flanged wheel carries the dome's base ring over it, and the trucks hold
  a toothed ring, teeth inwards. In the north-west corner of the room a hand wheel turns a short
  shaft; its pinion drives a crown wheel on an upright shaft, which climbs the wall through two
  bearings to a pinion in the toothed ring: 280 teeth to 10, twenty-eight turns of the upright
  shaft to one of the dome.

  Opening the slit (main/dome version a: two leaves that part sideways). Each leaf has an arm at
  its foot, bent over the sill into the room. An endless chain runs across the slit's foot over
  two corner wheels; the north arm holds its upper strand, the south arm its lower one, so the
  leaves can only move together and opposite ways. Each arm also hangs on a chain that turns
  round a sheave and runs up a rail under the beam beside the slit, over a second sheave and back
  down to a weight on wheels: the weights run down their rails and draw the leaves apart.
  Hauling the hand chain turns the sprocket in the middle of the endless chain, draws the leaves
  together and lifts the weights again.

What is fixed to the building stays below the underside of the dome's base ring (y 25); what is
above it rides round with the dome (the hand chain is hitched up before the dome is turned). The
shell, its ribs, the base ring and the beams beside the slit are main's and interiors'; this
package places display entities and nothing else.

Moving pieces are models of their own, for the motion category (plan 7.1):
  seg          all twenty turn about TURN_AXIS with the dome, and so does every piece of the slit gear
  riser        turns about the vertical through riser_at()
  handwheel    turns about the line along x through its entity, HAND_GEAR turns to one of the riser
  drive        turns about the line along x through its entity
  arm_n, arm_s slide along z towards the dome's meridian, TRAVEL blocks, as the leaves shut
  weight       runs up its rail, TRAVEL blocks at RUN_DEG from the level, as the leaves shut
Tonight the slit is open: the arms stand in its two lower corners and the weights at the foot of
their rails. Version b of the shell (a curtain drawn up from the slit's foot) gets its own gear
once the shell's version is chosen; until then nothing is placed at the slit for it.

Sizes inside the models are in sixteenths of a block (px) whatever scale a model is shown at.
"""
import functools
import importlib
import math

from artkit import models as M

from ..common import palette as P
from ..common import skeleton as S

PREFIX = "mach_dome_"
MOVED_IN = False            # the master scene gets the gear once the dome and its room stand in the assembly

IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
COPPER = P.mat("old_copper")
BRASS = P.mat("brass")
BRASS_D = P.mat("brass_dark")

# Every piece takes the light of the cell its entity stands in, like the blocks round it, and
# pieces that touch stand in one cell or in two next to each other. The ring's twenty segments
# cannot: by hand, in the sky light that falls through the slit, two neighbours differ by a fifth
# at most. Should the joints show all the same, this gives all twenty one light, (sky, block)
RING_LIGHT = None

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
RING_Y = LEDGE_Y + 1.0                  # 25.0: the underside of the dome's base ring (interiors/domeroom)
GORES = 20                              # main/dome: a truck under every seam between two gores
SEG_DEG = 360.0 / GORES
SEG_SCALE = 2
RING_SIDES = 3 * GORES                  # the ring is a polygon of sixty sides, three to a segment
RAIL_R = S.DOME_ROOM_DIAM / 2.0 + 0.25  # 11.25: the rail's centre line; a circle that lies on the ledge all the way round
RACK_TEETH = 14 * GORES                 # 280
RACK_R = RAIL_R - 0.5                   # 10.75: the toothed ring's pitch circle; a tooth and a gap are 3.86 px
PINION_TEETH = 10
PINION_R = RACK_R * PINION_TEETH / RACK_TEETH
RISER_R = RACK_R - PINION_R             # the upright shaft, from the dome's axis
# degrees round the dome (0 = east, 90 = south): the middle of a gap of the toothed ring, in the
# corner of the wall that interiors/domeroom keeps clear from the floor to the ledge (GEAR_SHAFT
# (-1, -9)). Two things want this angle and they cannot both have it: the hand wheel is 0.91 blocks
# across (rim 12.5 px plus a spoke) and a cell is 1.0, so the wheel's own rim must straddle a cell
# wall wherever the shaft stands on the pitch circle -- the widest disc that stays inside (-1, -9)
# at any meshing gap is 0.384 blocks, and the shaft at 240.43 already uses 0.375 of that for its
# pinion. Kept at 240.43, where the shaft is where domeroom's GEAR_SLIT/GEAR_STAND were laid out for
# it (g2 #38152, c290's own reading); the wheel reaches 0.03 blocks into the cell north of the
# shaft's own. Reported to c290 and S2 rather than moved here: it is domeroom's table that has to
# say which cells the hand wheel and the one turning it need.
RISER_DEG = (13 * 14 + 5) * 360.0 / RACK_TEETH
RISER_TOP = (RING_Y - FLOOR_Y) * PX     # 112 px over the floor
CROWN_PEGS = 8                          # the crown wheel on the upright shaft
CROWN_R = 4.5                           # px: its pitch circle
PEG_Y = (13.0, 15.0)                    # px over the floor: its pegs
HAND_TEETH = 6                          # the pinion on the hand shaft
HAND_R = CROWN_R * HAND_TEETH / CROWN_PEGS      # 3.375 px: the same pitch
HAND_H = (PEG_Y[0] + PEG_Y[1]) / 2.0 + HAND_R   # 17.375 px over the floor: the hand shaft
HAND_GEAR = CROWN_PEGS / HAND_TEETH     # turns of the hand wheel to one of the upright shaft

# ---- opening the slit (version a): in the dome's frame, x and z from its axis ------------------------
JAMB_Z = S.SLIT_W / 2.0                 # 2.5: the slit's two edges
RUN_Z = JAMB_Z + 0.5                    # 3.0: the plane of a weight's run, the middle of the beam beside the slit
SILL_Y = RING_Y + 1.0                   # 26.0: the top of the sill, which is the base ring's top
# the base ring's face towards the room beside the slit (columns z 2 and 3 on either side; on the
# meridian the raster circle lies a block further out)
FACE_X = -(S.DOME_ROOM_DIAM / 2.0 - 0.5)
LOOP_X = FACE_X + 0.25                  # the endless chain's plane
F0 = (LOOP_X, RING_Y + 0.5, 0.0)        # the middle of the foot gear: the drive's axis on the dome's meridian
STILE_X = FACE_X - 2.5                  # where an arm takes hold of its leaf: the stile over the sill's outer column
TRAVEL = JAMB_Z - 2.0 / PX              # 2.375 blocks: the leaves meet arm to arm on the meridian
# a weight's run. interiors/domeroom hangs the beam beside the slit two rows under the skin, and
# under main/dome's plates its underside steps one column in and two rows up three times running:
# the corners (-9.5, 28), (-8.5, 30), (-7.5, 32) lie on one line with the base ring's corner
RUN_FOOT = (FACE_X, SILL_Y)
RUN_STEP = (1.0, 2.0)
RUN_C1 = (RUN_FOOT[0] + RUN_STEP[0], RUN_FOOT[1] + RUN_STEP[1])
RUN_DEG = math.degrees(math.atan2(RUN_STEP[1], RUN_STEP[0]))        # 63.43
RUN_ANCHOR = (FACE_X + 0.5, SILL_Y + 0.5)       # the cell a run takes its light from
HANDCHAIN_Y = FLOOR_Y + 1.75            # the middle of the hand chain's bight: its lowest link hangs 1.3 over the floor

# px from F0
FACE = (FACE_X - F0[0]) * PX            # -4: the base ring's face beside the slit
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
RAIL = (-32.0, 71.0)                    # the rail's web: from over the base ring to the third corner
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


def seam_angles():
    return [(k + 0.5) * SEG_DEG for k in range(GORES)]


def riser_at():
    """(x, z) of the upright shaft, from the dome's axis."""
    r = math.radians(RISER_DEG)
    return RISER_R * math.cos(r), RISER_R * math.sin(r)


RISER_CELL = (int(math.floor(AX + riser_at()[0])), int(math.floor(AZ + riser_at()[1])))     # the column it stands in: (-1, -9)


def _run_units():
    r = math.radians(RUN_DEG)
    return (math.cos(r), math.sin(r)), (math.sin(r), -math.cos(r))


def on_run(s, d=0.0):
    """(x, y) in the dome's frame of the point s px up the line under the beam's corners and d px
    below it, away from the beam."""
    (ux, uy), (nx, ny) = _run_units()
    return RUN_C1[0] + (s * ux + d * nx) / PX, RUN_C1[1] + (s * uy + d * ny) / PX


def _eye():
    """Where the weight's chain leaves an arm, level across the slit's foot: (s along the run, x
    from F0), both in px. The chain meets the run's up-going strand there."""
    (_ux, uy), (_nx, ny) = _run_units()
    s = ((F0[1] + LUG / PX - RUN_C1[1]) * PX - UP_D * ny) / uy
    return s, (on_run(s, UP_D)[0] - F0[0]) * PX


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
def _segment():
    """One gore's share of the ring: a length of rail, the truck under the seam, a length of the
    toothed ring. The origin is on the ledge under the wheel; +x points outwards, the dome's axis
    is RAIL_R behind it."""
    d = _Draw("seg", SEG_SCALE)
    axis = (-RAIL_R * PX, 0.0, 0.0)
    arc = (-SEG_DEG / 2.0, SEG_DEG / 2.0)

    def at(deg):
        return ("y", -deg, axis)

    d.ring("y", (axis[0], 1.0, 0.0), RAIL_R * PX, 6.0, 2.0, IRON_D, sides=RING_SIDES, arc=arc, seed=101)   # the rail's foot
    d.ring("y", (axis[0], 3.0, 0.0), RAIL_R * PX, 2.0, 2.0, IRON, sides=RING_SIDES, arc=arc, seed=102)     # and its head
    for deg in (-7.5, -4.5, 4.5, 7.5):                                  # the chairs that hold it down
        for x in (-2.0, 2.0):
            d.box((x - 1.0, 2.0, -1.5), (x + 1.0, 3.0, 1.5), IRON, rot=at(deg), seed=103)

    hub = 8.5                                                           # the axle over the ledge: the tread stands on the rail's head
    d.tube("x", (hub, 0.0), -2.5, 1.0, 4.5, IRON, sides=12)             # the wheel's tread
    d.tube("x", (hub, 0.0), 1.0, 2.0, 5.25, IRON_D, sides=12)           # its flange, on the wall's side of the rail
    d.tube("x", (hub, 0.0), -5.5, 4.75, 1.0, IRON_D, sides=8)           # the axle
    for x0 in (-5.5, 4.25):
        d.tube("x", (hub, 0.0), x0, x0 + 0.5, 1.5, IRON, sides=8, seed=104)     # its nuts
    for x0 in (-5.0, 2.25):
        d.box((x0, 6.5, -2.0), (x0 + 2.0, 14.0, 2.0), IRON_D, seed=105)        # the truck's two cheeks
    d.box((-5.0, 14.0, -7.0), (4.25, 16.0, 7.0), IRON)                  # its saddle, under the base ring

    pitch = RACK_R * PX
    d.ring("y", (axis[0], 13.375, 0.0), pitch + 2.0, 2.0, 5.25, IRON_D, sides=RING_SIDES, arc=arc, seed=106)   # the toothed ring's back,
    x = pitch + axis[0]                                                 # bolted to the trucks' inner cheeks
    for j in range(RACK_TEETH // GORES):
        deg = (j + 0.5) * 360.0 / RACK_TEETH - SEG_DEG / 2.0
        d.box((x - 1.0, 11.0, -1.0), (x + 1.5, 15.75, 1.0), IRON, rot=at(deg), seed=107)
    return d


# ---- the hand gear: its pieces share one origin, on the floor on the upright shaft's axis, and the world's axes ----
def _riser():
    """The upright shaft: the crown wheel at its foot, a collar under and over each bearing, the
    pinion in the toothed ring at its top. Turns about its own axis."""
    d = _Draw("riser", 3, anchor=(0.0, HAND_H, 0.0))
    d.tube("y", (0.0, 0.0), 5.0, RISER_TOP, 1.5, IRON, sides=8)
    d.tube("y", (0.0, 0.0), 9.0, 11.0, 2.5, IRON_D, sides=8)                    # the crown wheel: its hub,
    d.tube("y", (0.0, 0.0), 11.0, PEG_Y[0], 5.5, IRON, sides=16)                # its disc
    for i in range(CROWN_PEGS):                                                 # and its pegs; a gap looks east
        a = math.radians((i + 0.5) * 360.0 / CROWN_PEGS)
        d.tube("y", (CROWN_R * math.cos(a), CROWN_R * math.sin(a)), PEG_Y[0], PEG_Y[1], 0.75, IRON_D, sides=8, seed=111)
    for y0 in (50.0, 60.0, 86.0, 96.0):
        d.tube("y", (0.0, 0.0), y0, y0 + 2.0, 2.5, IRON_D, sides=8, seed=112)
    y0 = RISER_TOP - 5.0
    d.tube("y", (0.0, 0.0), y0, RISER_TOP, PINION_R * PX - 1.2, IRON_D, sides=12)
    for i in range(PINION_TEETH):                                               # the first tooth points away from the dome's axis, into the gap
        deg = RISER_DEG + i * 360.0 / PINION_TEETH
        d.box((PINION_R * PX - 1.35, y0 + 0.25, -0.875), (PINION_R * PX + 0.8, RISER_TOP - 0.25, 0.875), IRON,
              rot=("y", -deg, (0.0, 0.0, 0.0)), seed=113)
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
        d.box((CROWN_R - 0.625, HAND_H - HAND_R - 0.875, -0.875), (CROWN_R + 0.625, HAND_H - HAND_R + 1.2, 0.875), IRON,
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
    """What is fixed to the dome at the slit's foot: the bracket out from the base ring with the
    drive's bearing, the two corner wheels on their studs, the endless chain."""
    d = _Draw("foot", 3)
    d.box((BACK, UNDER + 0.5, -3.0), (BACK + 1.0, 0.0, 3.0), IRON_D)                    # the plate on the base ring
    d.box((BACK + 1.0, UNDER + 1.0, -1.5), (5.0, UNDER + 3.0, 1.5), IRON_D, grain="x")  # the bracket
    d.box((2.0, UNDER + 3.0, -1.5), (5.0, 1.5, 1.5), IRON)                              # the bearing, between sprocket and hand-chain wheel
    for side in (-1, 1):
        z = side * IDLER_Z
        d.box((FACE, -2.0, z - 2.0), (FACE + 1.0, 2.0, z + 2.0), IRON_D, seed=401)
        d.tube("x", (0.0, z), FACE + 1.0, 1.5, PIN, IRON_D, sides=8, seed=402)
        d.tube("x", (0.0, z), -0.75, 0.75, SPROCKET_R, IRON, sides=8, seed=403)
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
    d.tube("x", (0.0, 0.0), -0.75, 0.75, SPROCKET_R, IRON, sides=8)
    d.ring("x", (WHEEL_X, 0.0, 0.0), WHEEL_R - 1.25, 2.0, 2.0, IRON, sides=16)  # the rim, under the hand chain
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
    the sill's top into the room, down the base ring's face to the strand it holds, and the lug
    its weight's chain is made fast to. Slides along z."""
    d = _Draw("arm_s" if side > 0 else "arm_n", 2)
    grip = -STRAND if side > 0 else STRAND          # the south arm holds the lower strand, the north arm the upper
    _eye_s, eye_x = _eye()

    def box(x0, y0, in0, x1, y1, in1, mat, **kw):   # in0, in1: px into the slit from the jamb
        d.box((x0, y0, side * (JAMB - in0)), (x1, y1, side * (JAMB - in1)), mat, **kw)

    stile = (STILE_X - F0[0]) * PX
    box(stile, SILL + 2.0, 0.0, stile + 8.0, SILL + 8.0, BAR, IRON_D)                   # the plate on the leaf's stile
    box(stile, SILL, 0.0, FACE, SILL + 2.0, BAR, IRON, grain="x")                       # along the sill
    box(FACE, grip - 1.0, 0.0, FACE + 2.0, SILL + 2.0, BAR, IRON)                       # down the base ring's face
    box(FACE, grip - 1.0, -CLAMP[1], FACE + 2.0, grip + 1.0, 0.0, IRON)                 # back under the jamb
    box(FACE + 2.0, grip - 1.75, -CLAMP[1], 1.75, grip + 1.75, -CLAMP[0], IRON_D)       # the clamp on the strand
    box(FACE + 2.0, LUG - 1.0, 0.0, eye_x + 1.5, LUG + 1.0, BAR, IRON, grain="x")       # the lug for the weight's chain
    d.box((eye_x - 1.0, LUG - 1.5, side * JAMB), (eye_x + 1.0, LUG + 1.5, side * (RUN - FOOT_R)), IRON_D, grain="z")   # its first link
    return d


# ---- the weights' runs --------------------------------------------------------------------------------
def _run(side):
    """The run of one weight (side 1: south, -1: north), fixed under the beam beside the slit: the
    rail, its cleats on the beam's corners and its foot on the jamb, the sheave at the foot that
    turns the chain out of the slit's foot, the sheave at the top, the chain. The origin is the
    beam's first corner (RUN_C1) in the run's plane; the axes are the dome's."""
    d = _Draw("run_s" if side > 0 else "run_n", 3,
              anchor=((RUN_ANCHOR[0] - RUN_C1[0]) * PX, (RUN_ANCHOR[1] - RUN_C1[1]) * PX, 0.0))
    foot_s = _eye()[0] + FOOT_R
    knee_d, knee_r = (UP_D + DOWN_D) / 2.0, (DOWN_D - UP_D) / 2.0
    zs = -side * FOOT_R                             # the sheave at the foot stands on the slit's side of the run
    with d.turned(("z", RUN_DEG)):                  # x up the run, y towards the beam
        d.box((RAIL[0], -WEB_D, -1.0), (RAIL[1], 0.0, 1.0), IRON_D, grain="x")
        d.box((FLANGE[0], -FLANGE_D[1], -3.0), (FLANGE[1], -FLANGE_D[0], 3.0), IRON, grain="x")
        for s0 in (STOP - 3.0, FLANGE[1] - 3.0):                                # a stop at either end, on both sides of the web
            for z0 in (-3.0, 1.0):
                d.box((s0, -FLANGE_D[0], z0), (s0 + 3.0, 2.0 - FLANGE_D[0], z0 + 2.0), IRON_D, seed=201)
        d.tube("y", (foot_s, zs), -UP_D - 0.75, -UP_D + 0.75, FOOT_R - 0.5, IRON, sides=12)
        d.tube("y", (foot_s, zs), -UP_D - 1.5, -1.0, PIN, IRON_D, sides=8)      # its pin, up into the foot
        d.ring("y", (foot_s, -UP_D, zs), FOOT_R, BAND, WRAP, IRON_D, sides=8,
               arc=(180.0, 270.0) if side > 0 else (90.0, 180.0), seed=202)
        _chain(d, "x", (-UP_D, 0.0), foot_s, KNEE_S, 210)
        d.box((KNEE_S - 4.0, -WEB_D - 0.5, -3.25), (KNEE_S + 4.0, -1.0, 3.25), IRON)    # the hanger of the top sheave, clamped on the web
        for z0 in (-3.25, 1.75):
            d.box((KNEE_S - 3.0, -knee_d - 4.0, z0), (KNEE_S + 3.0, -WEB_D - 0.5, z0 + 1.5), IRON_D, seed=203)
        d.tube("z", (KNEE_S, -knee_d), -0.75, 0.75, knee_r - 0.5, IRON, sides=12)
        d.tube("z", (KNEE_S, -knee_d), -3.75, 3.75, PIN, IRON_D, sides=8)
        d.ring("z", (KNEE_S, -knee_d, 0.0), knee_r, BAND, WRAP, IRON_D, sides=12, arc=(-90.0, 90.0), seed=204)
        _chain(d, "x", (-DOWN_D, 0.0), WEIGHT_S0 + W_HALF + 2.0, KNEE_S, 212)
    for i in range(3):                              # a cleat round each of the beam's three corners
        cx, cy = i * RUN_STEP[0] * PX, i * RUN_STEP[1] * PX
        d.box((cx - 4.0, cy - 1.0, -2.0), (cx, cy, 2.0), IRON, seed=205)
        d.box((cx, cy - 1.0, -2.0), (cx + 1.0, cy + 4.0, 2.0), IRON, seed=206)
    fx, fy = -RUN_STEP[0] * PX, -RUN_STEP[1] * PX   # where the line starts: the base ring's corner under the jamb
    z0, z1 = sorted((-side * 4.5, side * 2.0))
    d.box((fx, fy + 1.0, z0), (fx + 4.5, fy + 7.0, z1), IRON)                   # the foot: holds the web's end and the sheave's pin
    return d


def _weight():
    """A weight on its carriage: four wheels on the rail's flange, two hangers, old-copper slabs
    between iron end plates. The model lies along its rail (x up the run, y towards the beam) and
    is shown turned RUN_DEG about z; its origin is the carriage's middle on the line of the beam's
    corners."""
    d = _Draw("weight", 1)
    axle = W_WHEEL_R - FLANGE_D[0]
    for x in (-W_WHEEL, W_WHEEL):
        for z0 in (-2.75, 1.25):
            d.tube("z", (x, axle), z0, z0 + 1.5, W_WHEEL_R, IRON, sides=8, seed=301)
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


@functools.lru_cache(maxsize=None)
def _drawn():
    pieces = (_segment(), _riser(), _pedestal(), _handwheel(), _brackets(), _foot(), _drive(), _handchain(),
              _arm(-1), _arm(1), _run(-1), _run(1), _weight())
    return {d.m.name[len(PREFIX):]: d for d in pieces}


def models():
    return {d.m.name: d.m for d in _drawn().values()}


# ---- placing ----------------------------------------------------------------------------------------------
def layout(version=None):
    """[(piece, place, yaw, turns)] of the whole gear; a place is (x from the dome's axis, y, z from
    the dome's axis). version: main/dome's, read from that package when left out."""
    version = shell_version() if version is None else version
    out = []
    for deg in seam_angles():
        r = math.radians(deg)
        out.append(("seg", (RAIL_R * math.cos(r), LEDGE_Y, RAIL_R * math.sin(r)), deg, ()))
    rx, rz = riser_at()
    for name in ("riser", "pedestal", "handwheel", "brackets"):
        out.append((name, (rx, FLOOR_Y + HAND_H / PX, rz), 0.0, ()))
    if version == "a":
        for name in ("foot", "drive", "handchain", "arm_n", "arm_s"):
            out.append((name, F0, 0.0, ()))
        wx, wy = on_run(WEIGHT_S0)
        for side, name in ((-1, "run_n"), (1, "run_s")):
            out.append((name, (RUN_ANCHOR[0], RUN_ANCHOR[1], side * RUN_Z), 0.0, ()))
            out.append(("weight", (wx, wy, side * RUN_Z), 0.0, (("z", RUN_DEG),)))
    return out


def place(canvas, origin=(0, 0, 0), version=None):
    """The whole gear round DOME_AXIS. Returns the number of display entities."""
    ox, oy, oz = origin
    n = 0
    for name, (x, y, z), yaw, turns in layout(version):
        d = _drawn()[name]
        light = RING_LIGHT if name == "seg" else None
        canvas.add_entity(ox + AX + x, oy + y, oz + AZ + z,
                          M.display(d.m, yaw=yaw, scale=d.scale, turns=turns, brightness=light))
        n += 1
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
    out = []
    for name, (x, y, z), yaw, turns in layout(version):
        at = (ox + AX + x, oy + y, oz + AZ + z)
        seen = set()
        for p in _spots(_drawn()[name], yaw, turns):
            cell = tuple(int(math.floor(at[i] + p[i])) for i in range(3))
            if cell in seen:
                continue
            seen.add(cell)
            block = canvas.get(*cell)
            if block is not None and block.partition("[")[0].rpartition(":")[2] not in ignore:
                out.append((name, cell, block))
    return out


def build(canvas, origin=(0, 0, 0)):
    return place(canvas, origin) if MOVED_IN else 0
