"""machines/cable: the cable car, its winch and the haul rope at the cable station (plan ART-PLAN
7.2, 5.3; parts/A5-machines.md 2.7; card packages/machines/cablecar-winch.md).

The station is the spawn and the arrival view (skeleton S.V1): the player comes into the map at
the head of the track, looking away from all of this at the building. Nothing here stands in that
picture (A0 #304: no rope and no wheel between the eye and the building): every piece is east of
the spawn cell or in the winch house north of it. It is what the player finds on turning round:
the car at his back, its door towards him, and the winch in its house on his right.

How it works, so that it can be read off the pieces:

  motor -> belt -> drum   An electric motor on the threshold of the winch house drives the west
                          wheel of the drum by a flat belt. The drum is a wide barrel between two
                          spoked wheels three blocks across, the rope wound on it turn beside turn;
                          it fills the room from wall to wall.
  drum -> lead sheave     The rope leaves the top of the barrel, comes forward and down over a
                          sheave one block across that stands on the threshold, and goes into
                          the floor through a collar.
  under the paving        Cover plates in the paving show the way of the duct to the track. It
                          crosses below the north rail and ends under the cast cover between the
                          rails at the head of the track, which is also the step to the car's door.
  along the track         Out of that cover the rope runs just above the grating, under the car
                          (the car's grip is closed on it), off the platform, round a level roller
                          on the first tie on to the line of the trestle, over a roller at the brow
                          and down the trestle from roller to roller into the cloud.

The models (all "mach_cable_"):

  car      the car, the train's coach (plan/round2.md, card machines/train): dark-wood boards in
           a riveted iron frame, lit windows, a clerestory roof with a lamp at each end. It is a
           solid thing and stops the player like one: barriers in the cells its body fills
           (CAR_CELLS), none outside its outline (A0 11-16 09:11). It fills the track's way out
           of the platform from one piece of the edge's rail to the other.
  axle     ROLLS. A wheelset of the car, two of them (CAR_AXLES): an axle and two spoked wheels,
           anchored on the axle's line (its own z), in the car's axle boxes.
  drum     MOVES. Barrel, rope and the two wheels: turns about its own x axis through the anchor.
  frame    the two bearing pedestals of the drum, and the belt where it lies on the west wheel.
  motor    the motor on its bed, its belt pulley with the belt on it, its conduit into the floor.
  belt     one straight run of the belt, drawn out between the two wheels (M.between).
  sheave   MOVES. The lead sheave's wheel: turns about its own x axis through the anchor.
  stand    the lead sheave's stand, with the rope where it lies in the groove and goes down.
  duct     the cover plates of the rope duct, one cell of them.
  hood     the cast cover at the head of the track, the step to the car.
  turn     the level roller that turns the rope on to the trestle's line.
  roller   a track roller on its tie, that carries the rope: at the brow and down the slope.
  rope     the haul rope, drawn out between two points (M.between).

What moves (MOVING below): the drum and the sheave are models of their own, anchored on their
axes; build() registers their turn with the motion line (motion/_kit), a turn of the drum in
DRUM_REV ticks and the sheave as fast as the rope makes it. Turning them the positive way about x
pays the rope out (the car goes down); as placed, the winch hauls. The small rollers are plain
cylinders, a turn would not show, so they are not split.

Scale (A5 1.2: px = scale keeps 16 texels to the block): drum and frame 2, the rest 1 -- the
car is two blocks long and three wide over its eaves, as much as a model drawn texel for texel
may span. 28 display entities, one of them the lamp family's wall lamp in the winch house
(WORK_LAMP). The car, the drum and the rope with its rollers are seen from across the site; the
small pieces are drawn within 64 blocks (VIEW, VIEW_KEEP).

Blocks: the models stop nobody, so the package sets what does. Barriers inside the two solid
things, the car's body (CAR_CELLS) and the drum's barrel (SOLID), two high and nowhere beyond
what is seen. And the winch's own guard (GUARD): a low rail of iron bars before the winch house's
opening, from its west pier to the pier of the platform's edge beside the car, so that nobody
walks in among the wheels, the belt and the motor. Over the rail barriers two high (GUARD_OVER),
by the director's ruling: its top was a step to the car's roof.

Light: the car is lit within, a source of the second rank in the car that is offered to the sky
line, which places it. The winch house has no lamp of the site's: the winch brings its own, a
bracket lamp on the pier between the two windows of the back wall, over the barrel and between
the wheels, where it is seen from the platform; the lamp reports its own source. Neither reaches
the paving that the arrival view sees.
"""
import functools
import math

import numpy as np

from artkit import models as M
from artkit.pixelart import Mat, Sprite

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..motion import _kit as MK         # read only: the turn of the drum and the sheave is registered there
from ..props import _kit as PK          # read only: flat tones, rivets, the hand-over of light sources
from ..props import lamps               # the lamp in the winch house is one of the lamp family
from ..site import _kit as SK           # read only: the line of the ridge under the trestle
from ..site import cablecar as SHELL    # read only: the station's shell, whose numbers all of this hangs on

PREFIX = "mach_cable_"
PX = 1.0 / 16.0                         # one texel, in blocks
# How far off the pieces are drawn (artkit.models, the four bands; plan/INTERFACE.md 7: what stands
# out of doors and counts in the outline, the vehicles and the pieces along the line, is drawn from
# across the whole site). So the car, the drum with its pedestals, and the rope with its rollers
# keep the far band; the small things one walks up to are drawn within 64 blocks.
VIEW = M.MID
VIEW_KEEP = tuple(PREFIX + name for name in ("car", "axle", "drum", "frame", "rope", "roller", "turn"))

# --- materials (palette only) ---------------------------------------------------------------------
IRON, IRON_D, BRASS, BRASS_D = PK.IRON, PK.IRON_D, PK.BRASS, PK.BRASS_D
WOOD = P.mat("dark_wood")
WOOD_D = P.mat("dark_wood", base=1)                     # the sunk panel of the door
GLOW = [PK.flat("glow", i) for i in range(len(P.RAMPS["glow"]))]
ROPE, ROPE_TOP, ROPE_UNDER = PK.flat("iron", 4), PK.flat("iron", 5), PK.flat("iron", 2)
BELT, BELT_EDGE = PK.flat("old_copper", 1), PK.flat("old_copper", 0)        # a leather belt


class _Wound(Mat):
    """Rope wound on a barrel, turn beside turn: a light and a dark texel by turns along the
    barrel, so that every turn is two texels wide like the rope itself."""

    def levels(self, w, h, grain, seed):
        jj, ii = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        if grain == "cap":
            return np.full((h, w), self.base, dtype=np.int32)
        return self.base - ((ii if grain == "u" else jj) % 2)


COIL = _Wound(PREFIX + "coil", P.RAMPS["iron"], kind="flat", bevel=0, base=5)

_G = P.RAMPS["glow"]
_LIT = {"0": _G[0], "1": _G[1], "2": _G[2]}
# A lit window of the car, seen from outside: the lamp under the roof is the bright spot at the
# top, the light falls off towards the seats. The fourth row lies behind the glazing bar.
WIN6 = Sprite(PREFIX + "win6", ["112211", "122221", "112211", "000000", "111111", "011110", "011110", "001100",
                                "001100", "000000", "000000"], _LIT)
WIN5 = Sprite(PREFIX + "win5", ["12221", "12221", "11211", "00000", "11111", "01110", "01110", "00100",
                                "00100", "00000", "00000"], _LIT)
_I = P.RAMPS["iron"]
# One chequer plate of the duct's cover: a rim, raised lozenges, a slot to lift it by.
PLATE = Sprite(PREFIX + "plate", ["22222222", "24334332", "23343342", "23433432", "24334332", "23343342",
                                  "23300332", "22222222"], {"0": _I[0], "2": _I[2], "3": _I[3], "4": _I[4]})


# --- where it stands ------------------------------------------------------------------------------
# Everything hangs on the station's shell (site/cablecar): the car's cells, the winch room, the
# rule of the track. Points are in blocks, x east, y up, z south.
X0, Z0, X1, Z1 = S.CABLE_STATION                        # x 75..91, z -40..-26
FEET = float(S.STATION_GROUND)                          # -4: the platform's floor, and the rails' top in it
AXIS = SHELL.AXIS                                       # -33: the row of the track's axis
TRACK_Z = AXIS + 0.5                                    # the track's centre line in the station
CAR_BOX = SHELL.CAR["box"]                              # x 89..91, z -34..-32: the cells the shell keeps for the car
ROOM = SHELL.WINCH_ROOM["box"]                          # x 87..90, z -39..-37
LEVEL = SHELL.LEVEL                                     # 4: cells of level track east of the platform
GRADE = SHELL.GRADE                                     # 0.5: then the rails fall this much with every cell
track_axis = SHELL.track_axis                           # the row of the track's axis in column x
rail_top = SHELL.rail_top                               # y of the upper face of the rails in column x
TRACK_END = SHELL.END                                   # 141: the track's last column, under the cloud

# The car stands on the last two cells of the platform, as wide as the track is between its kerbs:
# its ends and its sides lie on cell lines (x 90 and 92, z -34 and -31), its east end flush with
# the platform's edge, so that it fills the gap the railing leaves for the track. A model stops
# nobody; the cells of the car's body hold barriers two high, so that the car is as solid as it
# looks and nobody walks through it and out on to the trestle (A0, 11-16 09:11: barriers stand
# inside a solid model one sees, and nowhere beyond its outline). Anchor: the middle of its foot
# on the rails. The cell west of it is left for the step to its door; the spawn cell is the next.
CAR_HALF = (16, 24)                                     # half its length and half its width, in texels
CAR = (CAR_BOX[2] + 1.0 - CAR_HALF[0] * PX, FEET, TRACK_Z)      # (91.0, -4, -32.5)
# Its two wheelsets, models of their own that roll: how far along the car from its middle they
# stand, the wheels' radius over the tyre (they stand on the rails) and the wheels' plane, the
# middle of a rail, all in texels.
CAR_AXLES = (-10.0, 10.0)
CAR_WHEEL = 4.0
RAIL_MID = 16.0
CAR_CELLS = [(x, y, z) for x in range(CAR_BOX[2] - 1, CAR_BOX[2] + 1) for y in (int(FEET), int(FEET) + 1)
             for z in range(CAR_BOX[1], CAR_BOX[3] + 1)]        # x 90..91, y -4..-3, z -34..-32: the barriers
CAR_LIGHT = (CAR_BOX[2], int(FEET) + 2, AXIS)           # a cell, over the barriers: the light of its windows
CAR_LIGHT_LEVEL = 9                                     # a lit window is a second-rank light (A5 1.3)

# The cast cover at the head of the track lies between the rails right under the car's door, in
# the east half of the cell before the car. The rope's duct lies in that same strip of x all the
# way north.
X_ROPE = CAR[0] - CAR_HALF[0] * PX - 0.25               # 89.75
HOOD = (X_ROPE, FEET, TRACK_Z)
DUCT_ROWS = list(range(ROOM[3] + 2, AXIS - 1))          # the paving between the house and the north rail: z -35

# The winch fills the room, which is four blocks wide and three deep: the drum's axle runs
# east-west through the middle of it, the feet of its bearings against the side walls, the wheels
# two texels clear of the floor and of the north wall. The threshold is the row of the south wall,
# which is one opening: the motor stands in its west half, the lead sheave over the rope's duct,
# the east third is free.
WHEEL_R = 1.5                                           # the big wheels: three blocks across
AXLE = (S.mid(ROOM[0], ROOM[2]), FEET + WHEEL_R + 2 * PX, ROOM[1] + WHEEL_R + 2 * PX)   # (89, -2.375, -37.375)
DRUM_HALF = 16.0                                        # half the drum's length over its bearings, in its units: 2 blocks
THRESHOLD_Z = ROOM[3] + 1.5
DRUM_ROPE_R = 1.0                                       # from the axle to the middle of the rope on the barrel
SHEAVE = (X_ROPE, FEET + 9 * PX, THRESHOLD_Z - 2 * PX)  # the lead sheave: one block across, a texel off the floor
SHEAVE_ROPE_R = 7 * PX
WHEEL_X = 10.25                                         # the wheels' middle planes, in the drum's units from its middle
BELT_X = AXLE[0] - WHEEL_X * 2 * PX                     # the west wheel's, in blocks
PULLEY = (BELT_X, FEET + 8 * PX, THRESHOLD_Z)           # the motor's belt pulley
WHEEL_BELT_R, PULLEY_BELT_R = WHEEL_R + 0.5 * PX, 4.5 * PX      # to the middle of the belt's thickness

# A model stops nobody, and the winch stands at the elbow of who comes into the map: left open, it
# is walked into and through (the walk-in count of 11-16, plan/reviews/walkin). Two things shut it.
# The barrel is as solid as it looks: barriers two high in the two columns that it fills, under the
# axle (SOLID). No other cell is filled by a wheel, the belt or the motor, and a barrier stands
# inside a solid model that is seen and nowhere beyond its outline (A0, 11-16 09:11). The rest is
# shut the way such a machine was, by a low iron rail of its own (GUARD): on the first row of the
# paving the winch leaves free, the one before the opening, from the opening's west pier, which it
# turns in to, to the pier of the platform's edge beside the car. It is a block high like the
# engine's, north of the north rail and clear of the way from the car's door to the steps. Nothing
# beside it is walked on to: the buffer stop south of it is a whole block up on every side
# (site/cablecar), so its top, level with the rail's, takes a jump like the rail itself.
SOLID = [(x, y, math.floor(AXLE[2])) for x in (int(AXLE[0]) - 1, int(AXLE[0])) for y in (int(FEET), int(FEET) + 1)]
#   (88..89, -4..-3, -38)
GUARD_Z = ROOM[3] + 2                                   # -35: the row before the opening, the duct's cover in it
GUARD = [(x, GUARD_Z) for x in range(ROOM[0] - 1, ROOM[2] + 1)]         # x 86..90; (91, -35) is the edge's pier
GUARD_RAIL = B.IRON_BARS
# The rail's top proved a step (the outdoor walk of candidate A7, plan/reviews/walk/1a0f1af, the
# second part, 1): one jump up on to it, then half a block at a time on to the cap of the edge's
# pier and on to the car's roof, and from there down on to the trestle, with no way back. The
# director had it shut with barriers and the look left as it is (11-16, 11:50): two high over
# every cell of the rail. One row would not do: the north buffer stop's top is level with the
# rail's and beside it, and a single row is jumped on to from there. With two the top is two
# blocks over the stop's and three over the paving. These are the only barriers of the package
# that do not stand inside a model.
GUARD_OVER = [(x, int(FEET) + up, z) for x, z in GUARD for up in (1, 2)]        # (86..90, -3..-2, -35)

# The winch's lamp: one of the lamp family, on the pier between the two windows of the back wall
# (site/cablecar keeps those two columns of brick for it), its lantern out over the barrel between
# the wheels. From the platform it is seen under the opening's girder, over the barrel.
LAMP = (AXLE[0], FEET + 3.5, float(ROOM[1]))            # a point on the north wall's face: (89, -0.5, -39)
LAMP_KIND = "bracket"
LAMP_LEVEL = None                                       # None: the lamp's own (12: the drum's cell gets 9, the sheave's 6)
WORK_LAMP = True                                        # False if the winch house is ever lit by a lamp of the site's


def _runs(c1, r1, c2, r2):
    """The two straight runs of a rope or belt that goes round two wheels the same way, in the
    wheels' plane. Centres are (z, y). Each run is given by its unit normal n, also (z, y): the
    run touches the wheels at c1 + r1 * n and c2 + r2 * n. The upper run comes first."""
    dz, dy = c2[0] - c1[0], c2[1] - c1[1]
    dist = math.hypot(dz, dy)
    u = (dz / dist, dy / dist)
    v = (-u[1], u[0])
    s = (r1 - r2) / dist
    c = math.sqrt(1.0 - s * s)
    out = [(s * u[0] + k * c * v[0], s * u[1] + k * c * v[1]) for k in (1.0, -1.0)]
    return sorted(out, key=lambda n: -n[1])


def _angle(n):
    """Where a normal (z, y) points, as M.Model.ring counts angles about x: 0 up, 90 south."""
    return math.degrees(math.atan2(n[0], n[1])) % 360.0


def _on(centre, r, n, x):
    """The point where a run with normal n touches the wheel about `centre`, in the plane x."""
    return (x, centre[1] + r * n[1], centre[2] + r * n[0])


def _sides(span, about):
    """How many sides to give a ring of which `span` degrees are wanted: M.Model.ring draws whole
    sides only, and a belt has to end where its straight run begins. The count near `about` whose
    sides fit the span best."""
    def miss(n):
        return abs(round(span * n / 360.0) * 360.0 / n - span)
    return min(range(about - about // 4, about + about // 2 + 1), key=lambda n: (round(miss(n), 2), abs(n - about)))


_LEAD = _runs((AXLE[2], AXLE[1]), DRUM_ROPE_R, (SHEAVE[2], SHEAVE[1]), SHEAVE_ROPE_R)[0]
LEAD_WRAP = _angle(_LEAD)                               # from here to 90 the rope lies on the sheave
_BELT = _runs((AXLE[2], AXLE[1]), WHEEL_BELT_R, (PULLEY[2], PULLEY[1]), PULLEY_BELT_R)
BELT_UP, BELT_LOW = _angle(_BELT[0]), _angle(_BELT[1])  # the belt is on the pulley between these two

# The rope along the track. In the station it runs level, three texels over the rails. East of
# the platform it follows the middle line of the trestle (a third of a block north for every block
# east): it climbs a little to the roller at the brow and then lies on the rollers of the slope,
# which stand on the middle of every sixth tie, RISE above the line of the steps' noses.
X_TURN = SK.CABLE_RIDGE_X[0] + 0.5                      # 92.5: where the centre line turns on to the ridge's
X_GRADE = X1 + LEVEL + 1.0                              # 96: the nose of the last level cell
_HX, _HZ = 3.0 / math.sqrt(10.0), -1.0 / math.sqrt(10.0)        # level and along the trestle
BEND = math.atan2(-_HZ, _HX)                            # the turn at X_TURN, 18 degrees to the north
THETA = math.atan(GRADE * _HX)                          # how steep the rope lies on the slope
TRACK_YAW = math.degrees(math.atan2(-_HX, _HZ))         # turns a model's +z down the trestle
TURN_R = 4 * PX                                         # from the level roller's axis to the middle of the rope
ROLL_R = 3 * PX                                         # the same for a track roller
ROLL_UP = 5 * PX                                        # a track roller's axis above its tie
RISE = ROLL_UP - GRADE / 2.0 + ROLL_R / math.cos(THETA)
BROW_TIE = X1 + LEVEL                                   # 95: the last level column
ROLLER_TIES = [t for t in range(BROW_TIE, TRACK_END - 6, 6) if rail_top(t) == int(rail_top(t))]   # 95, 101 .. 131


def _line_z(x):
    return TRACK_Z - max(0.0, x - X_TURN) / 3.0


def _slope(x):
    """The point of the rope at x, on the slope."""
    return (x, FEET - GRADE * (x - X_GRADE) + RISE, _line_z(x))


def _roller_at(tie):
    """The centre of the roller on the tie of column `tie`."""
    return (tie + 0.5, rail_top(tie) + ROLL_UP, _line_z(tie + 0.5))


TURN = (X_TURN - TURN_R * math.tan(BEND / 2.0), FEET + 4 * PX, TRACK_Z - TURN_R)
_Y_BROW = rail_top(BROW_TIE) + ROLL_UP + ROLL_R         # the rope on top of the brow roller
_X_BROW = X_GRADE - (_Y_BROW - FEET - RISE) / GRADE     # where the slope's line comes up to that
ROPE_LINE = ([(X_ROPE + 0.25 - 2 * PX, FEET + 3 * PX, TRACK_Z),        # two texels inside the hood
              (X_TURN, TURN[1], TRACK_Z),
              (_X_BROW, _Y_BROW, _line_z(_X_BROW))]
             + [_slope(t + 0.5) for t in ROLLER_TIES[2::2]]             # a new piece at every other roller
             + [_slope(TRACK_END + 1.0)])                               # the end of the track, under the cloud

_WHEEL, _POST, _SPOKE, _LEG = 700, 710, 720, 730        # pieces that share one picture


# --- the car --------------------------------------------------------------------------------------
def _car():
    """The car, drawn texel for texel (scale 1). x is the way of the track, the door at -x (west).
    Anchor: the middle of its foot, on the top of the rails.

    A broad car for a broad track: two blocks long and, over its eaves, three wide, its wheels on
    the middle of the rails. From the rails up: wheels 8 across under an iron frame (y 6..9), the
    floor at 9, boards to the waist rail (22..24), windows 24..35, the letter board to the eaves
    at 38, then the roof with its clerestory to 45. The walls lie in three planes: the iron
    frame, the boards one texel behind it, the glass one behind that."""
    m = M.Model(PREFIX + "car")
    L, W = CAR_HALF[0], CAR_HALF[1] - 2                 # half the body: 16 along the track, 22 across it
    FLOOR, WAIST, SILL, HEAD, EAVE = 9, 22, 24, 35, 38
    BAR = 31                                            # the glazing bar, before the windows' fourth row
    side_piers = ((-14, -12), (-6, -3), (3, 6), (12, 14))               # a long side: three windows six wide
    side_lights = (-12, -3, 6)
    end_piers = ((-20, -18), (-12, -8), (-2, 2), (8, 12), (18, 20))     # the valley end: four
    end_lights = (-18, -8, 2, 12)
    door_piers = ((6, 7), (12, 14), (19, 20))           # the door end: two narrow windows either side of the door
    door_lights = ((7, 12), (14, 19))

    # the underframe and the running gear
    for s in (-1.0, 1.0):
        m.box((-L + 2, 6, (W - 2) * s), (L - 2, FLOOR, W * s), IRON, grain="x")    # sole bar
        m.box(((L - 2) * s, 6, -W), (L * s, FLOOR, W), IRON, grain="z")            # head stock
        for t in (-10.5, -3.5, 3.5, 10.5):
            PK.rivet(m, (t, 7.5, W * s), "z" if s > 0 else "-z")
        for t in (-16.5, -5.5, 5.5, 16.5):
            PK.rivet(m, (L * s, 7.5, t), "x" if s > 0 else "-x")
    m.box((-L + 2, 8, -W + 2), (L - 2, FLOOR, W - 2), IRON_D)                      # the floor, seen from below
    for wx in CAR_AXLES:                    # the axle boxes under the sole bars: the wheelsets (_axle) run in them
        for s in (-1.0, 1.0):
            a, b = sorted((19.0 * s, 21.5 * s))
            m.box((wx - 2, 2, a), (wx + 2, 6, b), IRON_D, seed=_WHEEL + 4)
            a, b = sorted((21.5 * s, 22.0 * s))
            m.box((wx - 1, 3, a), (wx + 1, 5, b), BRASS_D, seed=_WHEEL + 2)        # the box's brass cover
    m.box((-2, 5, -1), (2, 8, 1), IRON_D)                                          # the grip's shank
    m.box((-3, 2, -2), (3, 5, 2), IRON_D, grain="x")                               # its jaws, closed on the rope

    # the body: four iron corner posts
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            m.box(((L - 2) * sx, FLOOR, (W - 2) * sz), (L * sx, EAVE, W * sz), IRON, grain="y", seed=_POST)
            for y in (12.5, 19.5, 27.5, 33.5):
                PK.rivet(m, ((L - 1.5) * sx, y, W * sz), "z" if sz > 0 else "-z")
                PK.rivet(m, (L * sx, y, (W - 1.5) * sz), "x" if sx > 0 else "-x")

    # the two long sides
    for s in (-1.0, 1.0):
        out = "s" if s > 0 else "n"
        m.box((-L + 2, FLOOR, (W - 2) * s), (L - 2, WAIST, (W - 1) * s), WOOD, grain="y")      # boards
        m.box((-L + 2, WAIST, (W - 2) * s), (L - 2, SILL, W * s), IRON, grain="x")             # waist rail
        for a, b in side_piers:
            m.box((a, SILL, (W - 2) * s), (b, HEAD, (W - 1) * s), WOOD, grain="y")
        m.box((-L + 2, HEAD, (W - 2) * s), (L - 2, EAVE, (W - 1) * s), WOOD, grain="x")        # letter board
        for a in side_lights:
            m.box((a, SILL, (W - 3) * s), (a + 6, HEAD, (W - 2) * s), GLOW[0], faces={out: WIN6}, emit=15,
                  shade=False)
            m.box((a, BAR, (W - 2) * s), (a + 6, BAR + 1, (W - 1) * s), IRON_D, grain="x")     # glazing bar
        m.box((-3, 13, (W - 1) * s), (3, 17, (W - 0.5) * s), BRASS, grain="x")                 # the maker's plate

    # the east end, towards the valley: four windows like the sides'
    m.box((L - 2, FLOOR, -W + 2), (L - 1, WAIST, W - 2), WOOD, grain="y")
    m.box((L - 2, WAIST, -W + 2), (L, SILL, W - 2), IRON, grain="z")
    for a, b in end_piers:
        m.box((L - 2, SILL, a), (L - 1, HEAD, b), WOOD, grain="y")
    m.box((L - 2, HEAD, -W + 2), (L - 1, EAVE, W - 2), WOOD, grain="z")
    for a in end_lights:
        m.box((L - 3, SILL, a), (L - 2, HEAD, a + 6), GLOW[0], faces={"e": WIN6}, emit=15, shade=False)
        m.box((L - 2, BAR, a), (L - 1, BAR + 1, a + 6), IRON_D, grain="z")

    # the west end, towards the platform: the door between two pairs of narrow windows
    for s in (-1.0, 1.0):
        a, b = sorted((6 * s, (W - 2) * s))
        m.box((-L + 1, FLOOR, a), (-L + 2, WAIST, b), WOOD, grain="y")
        m.box((-L, WAIST, a), (-L + 2, SILL, b), IRON, grain="z")
        m.box((-L + 1, HEAD, a), (-L + 2, EAVE, b), WOOD, grain="z")
        for a, b in door_piers:
            a, b = sorted((a * s, b * s))
            m.box((-L + 1, SILL, a), (-L + 2, HEAD, b), WOOD, grain="y")
        for a, b in door_lights:
            a, b = sorted((a * s, b * s))
            m.box((-L + 2, SILL, a), (-L + 3, HEAD, b), GLOW[0], faces={"w": WIN5}, emit=15, shade=False)
            m.box((-L + 1, BAR, a), (-L + 2, BAR + 1, b), IRON_D, grain="z")
        a, b = sorted((5 * s, 6 * s))
        m.box((-L, FLOOR, a), (-L + 2, EAVE, b), IRON, grain="y")                  # door jamb
        m.box((-L - 2, 15, a), (-L - 1, 31, b), BRASS, grain="y")                  # grab rail, a texel off the jamb
        for y in (15, 30):
            m.box((-L - 1, y, a), (-L, y + 1, b), BRASS)
        a, b = sorted((3 * s, 5 * s))
        m.box((-L + 1, FLOOR, a), (-L + 3, 37, b), WOOD, grain="y")                # the door's stiles
    m.box((-L, 37, -5), (-L + 2, EAVE, 5), IRON, grain="z")                        # door head
    for a, b in ((FLOOR, 12), (WAIST, SILL), (HEAD, 37)):
        m.box((-L + 1, a, -3), (-L + 3, b, 3), WOOD, grain="z")                    # bottom, lock and top rail
    m.box((-L + 2, 12, -3), (-L + 3, WAIST, 3), WOOD_D, grain="y")                 # the sunk panel
    m.box((-L + 2, SILL, -3), (-L + 3, HEAD, 3), GLOW[0], faces={"w": WIN6}, emit=15, shade=False)
    m.box((-L + 1, BAR, -3), (-L + 2, BAR + 1, 3), IRON_D, grain="z")
    m.box((-L, 19, 3), (-L + 1, 21, 5), BRASS)                                     # the handle

    # the roof: eaves board, deck, a clerestory with a row of small lights, a lamp at each end
    C = W - 9                                           # half the clerestory's width
    m.box((-L - 2, EAVE, -W - 2), (L + 2, EAVE + 1, W + 2), IRON, grain="x")
    m.box((-L - 1, 39, -W - 1), (L + 1, 41, W + 1), IRON_D, grain="x")
    m.box((-13, 41, -C), (13, 44, C), IRON_D, grain="x")
    for s in (-1.0, 1.0):
        m.box((-13, 41, C * s), (13, 42, (C + 1) * s), IRON, grain="x")            # the lights' sill
        for a in (-13, -8, -3, 2, 7, 12):
            m.box((a, 42, C * s), (a + 1, 44, (C + 1) * s), IRON, seed=_POST + 1)  # the bars between them
        for a in (-12, -7, -2, 3, 8):
            m.box((a, 42, C * s), (a + 4, 44, (C + 1) * s), GLOW[1], emit=15, shade=False, seed=_POST + 2)
        a, b = sorted((13 * s, 16 * s))                                            # s is the end from here on
        m.box((a, 41, -2), (b, 44, 2), BRASS_D)                                    # lamp housing
        a, b = sorted((16 * s, 17 * s))
        m.box((a, 42, -1), (b, 43, 1), GLOW[2], emit=15, shade=False)              # its lens
    m.box((-14, 44, -C - 2), (14, 45, C + 2), IRON, grain="x")
    return m


def _axle():
    """A wheelset of the car: an axle with a spoked wheel on the middle of either rail, its
    journals in the car's axle boxes. Anchor: the middle of the axle, the line it rolls about
    (the model's z)."""
    m = M.Model(PREFIX + "axle")
    G = RAIL_MID
    m.tube("z", (0.0, 0.0), -G - 3.5, G + 3.5, 1.0, IRON_D)
    for s in (-1.0, 1.0):
        m.ring("z", (0.0, 0.0, G * s), CAR_WHEEL - 0.5, 1.0, 3.0, IRON, sides=8, seed=_WHEEL)          # tyre
        a, b = sorted(((G - 0.5) * s, (G + 0.5) * s))
        for k in range(3):                                                         # six spokes: three bars through the hub
            m.box((-3.0, -0.5, a), (3.0, 0.5, b), IRON_D, rot=("z", 60.0 * k, (0.0, 0.0, 0.0)) if k else None,
                  seed=_WHEEL + 1)
        a, b = sorted(((G - 1.0) * s, (G + 1.5) * s))
        m.tube("z", (0.0, 0.0), a, b, 1.5, IRON, seed=_WHEEL + 3)                  # hub
    return m


# --- the winch ------------------------------------------------------------------------------------
def _drum():
    """The winch drum: a wide barrel with the rope wound on it between two spoked wheels three
    blocks across. Shown at scale 2: a unit is two texels. Anchor: the middle of the axle, which
    is the model's x axis. MOVES: the whole model turns about that axis.

    The rope leaves the barrel in the plane of X_ROPE; the wound turns end there."""
    m = M.Model(PREFIX + "drum", px=2.0)
    live = (X_ROPE - AXLE[0]) * 8.0
    barrel = DRUM_ROPE_R * 8.0 - 0.5
    m.tube("x", (0, 0), -DRUM_HALF, DRUM_HALF, 1.0, IRON_D)                        # the shaft, from wall to wall
    m.tube("x", (0, 0), -9.0, 9.0, barrel, IRON, sides=16)
    m.tube("x", (0, 0), -8.0, live + 0.5, barrel + 1.0, COIL, sides=16)            # the rope on it
    for s in (-1.0, 1.0):
        x = WHEEL_X * s
        m.ring("x", (x, 0, 0), WHEEL_R * 8.0 - 1.0, 2.0, 2.5, IRON, sides=24)      # rim
        for a in range(0, 360, 45):
            m.box((x - 0.5, 2.0, -0.75), (x + 0.5, 10.25, 0.75), IRON_D,
                  rot=("x", a + (22.5 if s > 0 else 0.0), (x, 0, 0)), grain="y", seed=_SPOKE)
        m.tube("x", (0, 0), x - 1.25, x + 1.25, 2.5, IRON_D)                       # hub
    return m


def _frame():
    """What carries the drum: a bearing pedestal outside each wheel, bolted to the floor, its
    foot plate out to DRUM_HALF, where the wall is; and the belt where it lies on the west wheel.
    Scale 2. Anchor: the middle of the drum's axle, so that drum and frame stand on one point and
    take the same light."""
    m = M.Model(PREFIX + "frame", px=2.0)
    floor = (FEET - AXLE[1]) * 8.0
    for s in (-1.0, 1.0):
        a, b = sorted(((DRUM_HALF - 3.5) * s, (DRUM_HALF - 0.5) * s))
        x = (a + b) / 2.0
        m.box((a - 0.5, floor, -8.0), (b + 0.5, floor + 1.0, 8.0), IRON_D, grain="z")          # foot plate
        for t in (-1.0, 1.0):
            m.box((x - 0.5, floor + 1.0, 7.0 * t - 0.5), (x + 0.5, floor + 1.5, 7.0 * t + 0.5), PK.RIVET,
                  seed=_LEG + 1)                                                               # holding-down bolt
            m.beam((x, floor + 1.0, 5.5 * t), (x, -2.0, 1.5 * t), 2.0, 2.0, IRON, seed=_LEG)   # leg
        m.box((a, -2.5, -2.5), (b, 2.0, 2.5), IRON, grain="z")                     # bearing
        m.box((a, 2.0, -1.5), (b, 3.0, 1.5), IRON_D, grain="z")                    # its cap
        m.box((x - 0.5, 3.0, -0.5), (x + 0.5, 4.0, 0.5), BRASS)                    # oil cup
    span = BELT_UP + 360.0 - BELT_LOW
    m.ring("x", (-WHEEL_X, 0, 0), WHEEL_BELT_R * 8.0, 0.5, 1.5, BELT, sides=_sides(span, 32),
           arc=(BELT_LOW, BELT_LOW + span))
    return m


def _motor():
    """The electric motor that drives the drum: a short ribbed body between two end bells on a
    bed, the belt pulley on its west end, a terminal box with the maker's plate on top, the
    conduit back from it and down into the floor behind the motor. It is a short one: it shares
    the threshold with the lead sheave, a block and a quarter east of its pulley.
    Anchor: the middle of the pulley; the shaft is the model's x axis, the body at +x."""
    m = M.Model(PREFIX + "motor")
    m.tube("x", (0, 0), -2.5, 2.5, 4.0, IRON, sides=12)                            # belt pulley
    m.tube("x", (0, 0), -3.0, 4.0, 1.0, IRON_D)                                    # shaft
    m.tube("x", (0, 0), 4.0, 6.0, 5.0, IRON_D, sides=12)                           # end bell
    m.tube("x", (0, 0), 6.0, 13.0, 6.0, IRON, sides=12)                            # body
    for x in (7.0, 9.0, 11.0):
        m.tube("x", (0, 0), x, x + 1.0, 7.0, IRON_D, sides=12, seed=_SPOKE + 1)    # cooling ribs
    m.tube("x", (0, 0), 13.0, 15.0, 5.0, IRON_D, sides=12)
    m.box((5.0, -8.0, -7.0), (14.0, -6.0, 7.0), IRON_D, grain="x")                 # bed
    m.box((7.0, 5.0, -3.0), (12.0, 9.0, 3.0), IRON_D, grain="x")                   # terminal box
    m.box((8.0, 6.0, 3.0), (11.0, 8.0, 3.5), BRASS, grain="x")                     # maker's plate, to the platform
    m.hose([(9.5, 7.0, -3.0), (9.5, 7.0, -9.0), (9.5, -8.0, -9.0)], 0.75, IRON_D)  # conduit
    m.tube("y", (9.5, -9.0), -8.0, -7.0, 2.0, IRON)                                # where it goes into the floor
    span = BELT_LOW - BELT_UP
    m.ring("x", (0, 0, 0), PULLEY_BELT_R * 16.0, 1.0, 3.0, BELT, sides=_sides(span, 12), arc=(BELT_UP, BELT_LOW))
    return m


def _belt():
    """A straight run of the belt: three texels wide, one thick, along +z from the anchor, 48
    long. Flat tones only, so M.between can draw it out."""
    m = M.Model(PREFIX + "belt")
    m.box((-1.5, -0.5, 0), (1.5, 0.5, 48), BELT, grain="z", faces={"e": BELT_EDGE, "w": BELT_EDGE})
    return m


def _sheave():
    """The lead sheave's wheel, one block across: two flanges with the groove between them, six
    spokes, a hub. Anchor: its middle; the axle is the model's x axis. MOVES: turns about it."""
    m = M.Model(PREFIX + "sheave")
    for x in (-1.5, 1.5):
        m.ring("x", (x, 0, 0), 6.5, 3.0, 1.0, IRON, sides=12, seed=_SPOKE + 2)     # flanges
    m.ring("x", (0, 0, 0), 5.5, 1.0, 2.0, IRON_D, sides=12)                        # the groove's bottom
    for a in range(0, 360, 60):
        m.box((-0.5, 2.0, -1.0), (0.5, 5.25, 1.0), IRON_D, rot=("x", a, (0, 0, 0)), grain="y", seed=_SPOKE + 3)
    m.tube("x", (0, 0), -2.0, 2.0, 2.5, IRON)                                      # hub
    return m


def _stand():
    """The lead sheave's stand on the threshold: a bed plate, an A-frame either side of the
    wheel, the pin, and the rope where it lies in the groove and drops through a collar into
    the floor. Anchor: the middle of the wheel; the floor is 9 below it."""
    m = M.Model(PREFIX + "stand")
    r = SHEAVE_ROPE_R * 16.0
    south = (THRESHOLD_Z + 0.5 - SHEAVE[2]) * 16.0                                 # the threshold's south edge
    m.box((-5, -9, -8), (5, -8, south), IRON_D, grain="z")                         # bed plate
    for s in (-1.0, 1.0):
        for t in (-1.0, 1.0):
            m.beam((3.5 * s, -8.0, 6.0 * t), (3.5 * s, 0.0, 1.0 * t), 1.0, 2.0, IRON, seed=_LEG + 2)
        a, b = sorted((3.0 * s, 5.0 * s))
        m.tube("x", (0, 0), a, b, 1.5, IRON_D)                                     # axle boss
    m.tube("x", (0, 0), -3.0, 3.0, 1.0, IRON_D)                                    # the pin the wheel turns on
    span = 90.0 - LEAD_WRAP
    m.ring("x", (0, 0, 0), r, 2.0, 2.0, ROPE, sides=_sides(span, 16), arc=(LEAD_WRAP, 90.0))   # the rope in the groove
    m.box((-1, -8, r - 1), (1, 0, r + 1), ROPE, grain="y")                         # and down
    m.box((-2, -8, r - 2), (2, -7, r + 2), IRON, grain="x")                        # the collar it goes through
    return m


# --- along the track ------------------------------------------------------------------------------
def _duct():
    """Two chequer plates over the rope duct, a texel proud of the paving, half a block wide and
    a block long, along z. Anchor: the middle of the foot."""
    m = M.Model(PREFIX + "duct")
    for z in (-8, 0):
        m.box((-4, 0, z), (4, 1, z + 8), IRON_D, faces={"u": PLATE})
    return m


def _hood():
    """The cast cover over the rope's way up at the head of the track, between the rails: five
    texels high, with a lower toe to the west, so that it is the step to the car's door. The rope
    comes out of its east face, under the car. Anchor: the middle of the foot."""
    m = M.Model(PREFIX + "hood")
    m.box((-4, 0, -8), (-2, 3, 8), IRON_D, grain="z")                              # the toe
    m.box((-2, 0, -8), (4, 5, 8), IRON, grain="z")                                 # the tread
    for x in (-0.5, 2.5):
        for z in (-6.5, 6.5):
            PK.rivet(m, (x, 5, z), "y")
    return m


def _turn():
    """The level roller on the first tie, that turns the rope on to the trestle's line: a
    grooved wheel ten across on an upright spindle. Anchor: the middle of the groove, on the
    spindle's axis; the tie's top is 4 below."""
    m = M.Model(PREFIX + "turn")
    m.tube("y", (0, 0), -4.0, -3.0, 3.0, IRON_D)                                   # foot
    m.tube("y", (0, 0), -3.0, 3.0, 1.0, IRON_D)                                    # spindle
    m.tube("y", (0, 0), -2.0, -1.0, 5.0, IRON, sides=12)                           # lower flange
    m.tube("y", (0, 0), -1.0, 1.0, TURN_R * 16.0 - 1.0, IRON_D, sides=12)          # the groove's bottom
    m.tube("y", (0, 0), 1.0, 2.0, 5.0, IRON, sides=12)                             # upper flange
    m.tube("y", (0, 0), 3.0, 4.0, 1.5, BRASS_D)                                    # grease cap
    return m


def _roller():
    """A track roller: a plain roller between two flanges, in two bearing blocks that stand on
    a tie. The axle is the model's x axis, the rope runs over it along z. Anchor: the middle of
    the roller; the tie's top is 5 below."""
    m = M.Model(PREFIX + "roller")
    foot = -ROLL_UP * 16.0
    m.tube("x", (0, 0), -3.0, 3.0, ROLL_R * 16.0 - 1.0, IRON)
    for s in (-1.0, 1.0):
        a, b = sorted((3.0 * s, 4.0 * s))
        m.tube("x", (0, 0), a, b, 3.0, IRON_D, seed=_SPOKE + 4)                    # flange
        a, b = sorted((4.0 * s, 6.0 * s))
        m.box((a, foot, -2.0), (b, 1.0, 2.0), IRON_D, grain="y", seed=_SPOKE + 5)  # bearing block
    return m


def _rope():
    """The haul rope: a bar two texels square along +z from the anchor, 48 long, lighter on top
    and dark below. Flat tones only, so M.between can draw it out."""
    m = M.Model(PREFIX + "rope")
    m.box((-1, -1, 0), (1, 1, 48), ROPE, grain="z", faces={"u": ROPE_TOP, "d": ROPE_UNDER})
    return m


BUILDERS = {"car": _car, "axle": _axle, "drum": _drum, "frame": _frame, "motor": _motor, "belt": _belt,
            "sheave": _sheave, "stand": _stand, "duct": _duct, "hood": _hood, "turn": _turn, "roller": _roller,
            "rope": _rope}
SCALE = {PREFIX + name: 2.0 if name in ("drum", "frame") else 1.0 for name in BUILDERS}
# What turns: about which axis of its own model (through the anchor), the tag its entities carry,
# how fast against the drum (the rope runs as fast on both) and the ticks a turn takes. The drum
# sets the pace: a turn in DRUM_REV ticks is two blocks of rope a second, the pace of a car on the
# track. A positive time pays the rope out; the winch is placed hauling.
DRUM_REV = 64
SHEAVE_REV = DRUM_REV * 7 // 16                         # 28: by the two radii, a whole number of ticks
if SHEAVE_REV * DRUM_ROPE_R != DRUM_REV * SHEAVE_ROPE_R:
    raise ValueError("the sheave's turn is not a whole number of ticks")
MOVING = {
    PREFIX + "drum": dict(tag="c164_cable_drum", axis="x", ratio=1.0, ticks=-DRUM_REV),
    PREFIX + "sheave": dict(tag="c164_cable_sheave", axis="x", ratio=DRUM_ROPE_R / SHEAVE_ROPE_R, ticks=-SHEAVE_REV),
}


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + name: make() for name, make in BUILDERS.items()}


def models():
    return dict(_models())


# --- placing --------------------------------------------------------------------------------------
def build(canvas, origin=(0, 0, 0)):
    """Place the car, the winch and the rope at the station. Returns the display entities placed."""
    built = _models()
    ox, oy, oz = origin

    def put(name, p, yaw=0.0):
        name = PREFIX + name
        nbt = M.display(built[name], yaw=yaw, scale=SCALE[name])
        if name in MOVING:
            nbt["Tags"].append(MOVING[name]["tag"])
        canvas.add_entity(p[0] + ox, p[1] + oy, p[2] + oz, nbt)
        if name in MOVING:
            MK.spin(canvas, MOVING[name]["axis"], MOVING[name]["ticks"])
        return 1

    def run(name, a, b):
        a = (a[0] + ox, a[1] + oy, a[2] + oz)
        b = (b[0] + ox, b[1] + oy, b[2] + oz)
        canvas.add_entity(a[0], a[1], a[2], M.between(built[PREFIX + name], a, b))
        return 1

    for x, y, z in CAR_CELLS + SOLID:       # the car and the barrel are solid: who walks into them is stopped
        canvas.set(x + ox, y + oy, z + oz, B.BARRIER)
    for x, z in GUARD:                      # the winch's rail
        canvas.set(x + ox, int(FEET) + oy, z + oz, GUARD_RAIL)
    for x, y, z in GUARD_OVER:              # and nobody gets up on it
        canvas.set(x + ox, y + oy, z + oz, B.BARRIER)
    n = put("car", CAR) + put("hood", HOOD)
    for along in CAR_AXLES:
        n += put("axle", (CAR[0] + along * PX, CAR[1] + CAR_WHEEL * PX, CAR[2]))
    for row in DUCT_ROWS:
        n += put("duct", (X_ROPE, FEET, row + 0.5))

    # A display entity takes the light of the cell it stands in. The belt's runs start at the
    # pulley and the rope's at the sheave, so each is lit like the piece it runs from.
    n += put("drum", AXLE) + put("frame", AXLE) + put("motor", PULLEY)
    for normal in _BELT:
        n += run("belt", _on(PULLEY, PULLEY_BELT_R, normal, BELT_X), _on(AXLE, WHEEL_BELT_R, normal, BELT_X))
    n += put("sheave", SHEAVE) + put("stand", SHEAVE)
    n += run("rope", _on(SHEAVE, SHEAVE_ROPE_R, _LEAD, X_ROPE), _on(AXLE, DRUM_ROPE_R, _LEAD, X_ROPE))

    n += put("turn", TURN)
    for tie in ROLLER_TIES:
        n += put("roller", _roller_at(tie), yaw=TRACK_YAW)
    for a, b in zip(ROPE_LINE, ROPE_LINE[1:]):
        n += run("rope", a, b)

    # The car is lit within: its source is offered to the sky line, which places it (PK.offer_lights
    # hands it to sky/_lightkit, and puts it down itself in a tree without that). The winch's lamp
    # reports its own.
    x, y, z = CAR_LIGHT
    PK.offer_lights(canvas, [((x + ox, y + oy, z + oz), CAR_LIGHT_LEVEL)], "machines/cable:car_windows")
    if WORK_LAMP:
        n += lamps.place(canvas, LAMP_KIND, LAMP, facing="south", origin=origin, level=LAMP_LEVEL)
    return n
