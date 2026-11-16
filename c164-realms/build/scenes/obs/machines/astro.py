"""machines/astro -- the astrograph of the small dome (plan/ART-PLAN.md 7.2;
plan/parts/A5-machines.md 2.9; card plan/packages/machines/meridian-astrograph.md).

The camera of the observatory: a short stout tube of riveted plate with a wide photographic
glass in a brass cell at one end and a wooden plate holder at the other, a slim brass guiding
telescope riding on its back. It stands in the small dome on the south end pavilion
(main/smalldome) and looks out of the slit due west, at the head of the comet, parallel to the
great refractor: tonight it takes the comet's plate.

  the mount   a small German equatorial, the great refractor's a size down: a cast column in two
              bolted sections, two cheek plates on its head that hold the polar sleeve at the
              latitude; the hour circle and the worm wheel on the lower end of the polar axis, the
              driving clock on the column's west face and its rod up to the worm.
  the axis    the declination sleeve across the head of the polar axis, its divided circle, the
              steel shaft that runs out to two cast counterweights.
  the tube    rings of plate under riveted hoops, a brass cell with the object glass inside the
              lip of a dew cap; the saddle and its two straps; the guiding telescope on two ring
              brackets, its eyepiece beside the plate holder; a slow-motion rod along the side
              with a handwheel at the observer's hand.
  the back    the camera: a wooden box with brass corners behind the tail flange, the plate
              holder in its frame, the dark slide half drawn.

The room decides its size (the card asks for a tube six blocks long): the drum is five blocks
across inside and seven under the dome, so the tube is 6.2 blocks from the dew cap to the plate
holder and 1.1 across. It is wider than the slit, so the dew cap stops between the plates that
flank the slit, two texels short of them: as far out as it can go, where the object glass shows
whole from the far end of the terrace and from the tower. The plate holder is at the height of
the observer's chest in the east half of the room.
The tube is on the east side of the pier and the counterweights hang to the west and north, the
way an equatorial of this kind stands when it looks west.

What the other lines read (scene coordinates; give the origin to have it added):

    astro.pivot()       where the tube's axis crosses the declination axis: on the dome's axis
    astro.head()        where the declination axis crosses the polar axis
    astro.objective()   the middle of the object glass
    astro.plate()       the middle of the plate holder's back
    astro.foot()        the middle of the column's foot on the floor
    astro.sweep()       (centre, radius) of the ball no part of the instrument leaves as it stands
    astro.ELEVATION     degrees the tube looks up, due west: the comet's head (sky/comet)
    astro.BRIGHTNESS    the light every piece is shown in, whatever cell it stands in

The pieces that turn are models of their own, and all three stand on the polar axis, at the head:
the axis piece (its model's y is the polar axis), the tube and the back (drawn about the tube's
pivot, anchored where the declination axis meets the polar one). The driving clock turns the
polar axis after the sky, a turn in a day, which no visit sees. So the instrument is shown at
work: it follows for TRACK degrees, is brought back and follows again, there and back in
TRACK_PERIOD ticks, the three pieces as one (the second round, plan/round2.md: what stands is to
move; registered with the motion line as they are placed, motion/_kit.swing). placed(turn) gives
the instrument at any turn, for whoever has to keep clear of it. No lamp: plates are changed in
the dark.

    python -m scenes.obs.machines.astro      the numbers above and the rules they are held to
"""
import functools
import math
import sys

from ..common import palette as P
from ..common import skeleton as S
from . import meridian as K

try:
    from ..motion import _kit as MK
except ImportError:                     # the motion line is not in the tree: the instrument stands still
    MK = None

PREFIX = "mach_astro_"
BRIGHTNESS = K.BRIGHTNESS

IRON, IRON_D, PLATE, STEEL, BRASS, BRASS_D, WOOD = K.IRON, K.IRON_D, K.PLATE, K.STEEL, K.BRASS, K.BRASS_D, K.WOOD
WOOD_D = P.mat("dark_wood", base=1)                   # the plate holder: a step darker than the box
EAST, UP, SOUTH, WORLD = K.EAST, K.UP, K.SOUTH, K.WORLD


# ---- directions and points (blocks, scene coordinates) -------------------------------------------------
def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _mul(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a):
    n = math.sqrt(_dot(a, a))
    return (a[0] / n, a[1] / n, a[2] / n)


def _elevation():
    """Degrees up of the comet's head, due west: the sky line's number, as the great refractor reads it."""
    try:
        from ..sky import comet
    except ImportError:
        return 41.05
    return float(getattr(comet, "HEAD_ELEVATION", 41.05))


ELEVATION = _elevation()
LATITUDE = S.LATITUDE
_E, _L = math.radians(ELEVATION), math.radians(LATITUDE)
SIGHT = (-math.cos(_E), math.sin(_E), 0.0)              # the way the tube looks: west and up
OVER = (math.sin(_E), math.cos(_E), 0.0)                # square to the tube in the slit's plane, upwards
POLE = (0.0, math.sin(_L), -math.cos(_L))               # the polar axis: north and up
DEC = _unit(_cross(POLE, SIGHT))                        # the declination axis towards the tube: east, up, south

TUBE_FRAME = ((0.0, 0.0, -1.0), OVER, _mul(SIGHT, -1.0))        # x north, y over, z down the tube to the plate
AXIS_FRAME = (_cross(POLE, _mul(DEC, -1.0)), POLE, _mul(DEC, -1.0))     # y the polar axis, z out to the weights

FLOOR = float(S.SMALL_DRUM_BASE)                        # 18: the dome room's floor, the pavilion's deck
DOME_AXIS = ((S.SMALL_DOME_X[0] + S.SMALL_DOME_X[1]) / 2.0 + 0.5,
             (S.SMALL_DOME_Z[0] + S.SMALL_DOME_Z[1]) / 2.0 + 0.5)       # (12.5, 30.5), a point
RISE = 40.0                     # texels: the tube's pivot over the floor
OFF = 18.0                      # from the polar axis to the tube's axis, along the declination axis
FRONT, TAIL, BACK = 66.0, 26.0, 33.5    # from the pivot: to the dew cap's lip, the tail flange, the plate holder's back
HOLD = 8.0                      # from the head down the polar axis to the bolt the cheeks hold the sleeve by
TUBE_SCALE, MOUNT_SCALE, AXIS_SCALE, BACK_SCALE = 2.0, 1.0, 1.0, 1.0
ON_POLE = tuple(-OFF * _dot(DEC, axis) for axis in TUBE_FRAME)     # the head, in the tube's texels from its pivot

# the tracking: to either side of the pose the instrument stands in, about the polar axis
TRACK = 2.5                     # degrees
TRACK_PERIOD = 400              # ticks there and back: twenty seconds
TRACK_KEYS = 8                  # poses in one swing: it slows down at the ends


def pivot(origin=(0, 0, 0)):
    return _add((DOME_AXIS[0], FLOOR + RISE / 16.0, DOME_AXIS[1]), origin)


def head(origin=(0, 0, 0)):
    return _add(pivot(origin), _mul(DEC, -OFF / 16.0))


def foot(origin=(0, 0, 0)):
    x, _, z = _add(head(), _mul(POLE, -HOLD / 16.0))
    return _add((x, FLOOR, z), origin)


def objective(origin=(0, 0, 0)):
    return _add(pivot(origin), _mul(SIGHT, (FRONT - 3.0) / 16.0))


def plate(origin=(0, 0, 0)):
    return _add(pivot(origin), _mul(SIGHT, -BACK / 16.0))


def sweep(origin=(0, 0, 0)):
    """(centre, radius) of the ball round the pivot that holds every piece, as it stands and at
    either end of its tracking."""
    built = _built()
    c = pivot()
    r = max(math.dist(c, p) for turn in (-TRACK, 0.0, TRACK) for name, at, frame, scale in placed(turn)
            for _, p in K.corners(built[name], at, frame, scale))
    return _add(c, origin), r


# ---- the tube -----------------------------------------------------------------------------------------
BODY_R, HOOP_R, CELL_R = 9.0, 10.0, 10.0
BODY = (-53.0, 16.0)            # the rings of plate: from, to (texels from the pivot; the plate is at +)
HOOPS = (-35.0, -17.0, 16.0)    # the hoops' middles; the last, where the tail cone starts, is brass
STRAPS = (-7.5, 7.5)            # the saddle's two straps
GUIDE_OFF, GUIDE_R = 13.25, 2.75
GUIDE = (-50.0, 21.5)           # the guiding telescope's tube: from, to
SEAMS = (215.0, 245.0)          # where the seams of rivets run: degrees round the tube (0 north, 90 over)
ROD = (175.0, 2.0, 22.0)        # the slow-motion rod: degrees round the tube, from, to


def _saddle_angle():
    """Where the declination axis leaves the tube, degrees round it from the model's x towards y."""
    d = _mul(DEC, -1.0)
    return math.degrees(math.atan2(_dot(d, TUBE_FRAME[1]), _dot(d, TUBE_FRAME[0])))


def _tube():
    d = K.Draw(PREFIX + "tube", TUBE_SCALE, anchor=ON_POLE)

    def seg(z0, z1, radius, mat, sides=12, **kw):
        d.tube("z", (0.0, 0.0), z0, z1, radius, mat, sides=sides, **kw)

    def side(angle):
        """A frame whose y points out of the tube at `angle` degrees round it (0 north, 90 over)."""
        return d.turned(("z", angle - 90.0))

    # the object glass inside the lip of the dew cap, the brass cell with its ring of screws
    d.ring("z", (0.0, 0.0, -FRONT + 2.0), CELL_R - 0.25, 1.5, 4.0, IRON_D, sides=16)
    seg(-FRONT + 3.0, -FRONT + 3.5, 8.75, K.GLASS, cap=K.GLASS)
    seg(-FRONT + 2.9, -FRONT + 3.0, 4.5, K.GLASS_D, sides=8, cap=K.GLASS_D)
    seg(-FRONT + 3.5, -FRONT + 11.0, CELL_R, BRASS)
    seg(-FRONT + 6.0, -FRONT + 8.0, CELL_R + 0.25, K.BRASS_STUD, seed=K.HOOP_SEED + 1)
    seg(-FRONT + 11.0, BODY[0], CELL_R + 0.5, K.IRON_D_STUD, seed=K.HOOP_SEED + 2)
    # the body: rings of two plates, each ring lapped and riveted to the next under a hoop, a
    # seam of rivets down either side of it, the seams of neighbouring rings a facet apart (the
    # great refractor's rule); the tail cone and its bolted flange
    seg(BODY[0], BODY[1], BODY_R, PLATE)
    for z in HOOPS:
        seg(z - 1.5, z + 1.5, HOOP_R, K.BRASS_STUD if z == HOOPS[-1] else K.PLATE_STUD, seed=K.HOOP_SEED)
    laps = (BODY[0],) + HOOPS
    for i, (a, b) in enumerate(zip(laps, laps[1:])):
        for opposite in (0.0, 180.0):
            with side(SEAMS[i % 2] + opposite):
                d.box((-1.5, BODY_R - 1.0, a + 1.5), (1.5, BODY_R + 0.5, b - 1.5), K.PLATE_SEAM, grain="z",
                      seed=K.HOOP_SEED + 3)
    d.taper("z", (0.0, 0.0), BODY[1], TAIL - 2.0, BODY_R, 8.0, PLATE, sides=12, steps=2)
    seg(TAIL - 2.0, TAIL, 9.25, K.IRON_D_STUD, seed=K.HOOP_SEED + 2)

    # the saddle on the end of the declination axis, and the two straps that hold the tube in it
    with side(_saddle_angle()):
        d.box((-7.0, BODY_R - 0.5, -11.0), (7.0, BODY_R + 2.5, 11.0), IRON_D)
        d.box((-8.0, BODY_R + 1.5, -12.0), (8.0, BODY_R + 2.75, 12.0), K.IRON_D_STUD)
        d.tube("y", (0.0, 0.0), BODY_R + 2.75, OFF - 3.0, 4.25, IRON_D, sides=12)
    for z in STRAPS:
        seg(z - 2.0, z + 2.0, HOOP_R + 0.4, K.IRON_STUD, seed=K.HOOP_SEED + 4)

    # the guiding telescope on the tube's back, on two ring brackets, its eyepiece past the tail
    g0, g1 = GUIDE
    with side(90.0):
        c = (0.0, GUIDE_OFF)
        d.tube("z", c, g0, g1, GUIDE_R, BRASS, sides=8)
        d.tube("z", c, g0 - 3.0, g0 + 1.0, GUIDE_R + 0.75, BRASS_D, sides=8)
        d.tube("z", c, g0 - 3.25, g0 - 3.0, GUIDE_R - 0.25, K.GLASS, sides=8, cap=K.GLASS)
        d.tube("z", c, g1, g1 + 5.0, 2.0, BRASS_D, sides=8)
        d.tube("z", c, g1 + 5.0, g1 + 8.0, 1.25, BRASS, sides=8, cap=K.GLASS_D)
        for z in (g0 + 9.0, g1 - 10.0):
            d.tube("z", c, z - 1.5, z + 1.5, GUIDE_R + 1.0, IRON_D, sides=8)
            d.box((-2.0, BODY_R - 1.0, z - 1.5), (2.0, GUIDE_OFF - GUIDE_R, z + 1.5), IRON_D)

    # the slow-motion rod: from the declination clamp down the side to a handwheel by the plate
    angle, r0, r1 = ROD
    with side(angle):
        d.tube("z", (0.0, BODY_R + 3.0), r0, r1, 0.6, BRASS, sides=4)
        d.tube("z", (0.0, BODY_R + 3.0), r1, r1 + 1.5, 3.0, BRASS, sides=8)
        d.tube("z", (0.0, BODY_R + 3.0), r1 + 1.5, r1 + 2.5, 1.25, BRASS_D, sides=8)
        for z in (r0 + 1.0, r1 - 4.0):
            d.box((-0.75, BODY_R - 1.0, z - 0.75), (0.75, BODY_R + 4.0, z + 0.75), IRON_D)
    return d.model


def _back():
    """The camera: drawn in the tube's frame and anchored as the tube is, so it turns with it."""
    d = K.Draw(PREFIX + "back", BACK_SCALE, anchor=ON_POLE)
    box0, box1 = TAIL, TAIL + 5.0
    d.box((-8.0, -8.0, box0), (8.0, 8.0, box1), WOOD, grain="x")
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):                          # brass corners
            a, b = sorted((sx * 8.25, sx * 5.5))
            c, e = sorted((sy * 8.25, sy * 5.5))
            d.box((a, c, box1 - 1.0), (b, e, box1 + 0.25), BRASS_D)
        d.tube("x", (0.0, box0 + 2.5), sx * 8.0, sx * 10.0, 1.5, BRASS, sides=8)    # the focusing screws
        d.tube("x", (0.0, box0 + 2.5), sx * 10.0, sx * 10.75, 2.25, K.BRASS_TICK, sides=8)
    # the plate holder in its frame, two brass turn-buttons, the dark slide half drawn to the north
    d.box((-7.0, -7.0, box1), (7.0, 7.0, BACK - 0.5), WOOD_D, grain="y")
    d.box((-5.0, -5.0, BACK - 0.5), (5.0, 5.0, BACK), WOOD, grain="x")
    for sy in (-1.0, 1.0):
        a, b = sorted((sy * 7.75, sy * 6.25))
        d.box((-1.5, a, BACK - 2.0), (1.5, b, BACK - 1.0), BRASS)
    d.box((2.0, -6.0, box1 + 0.75), (13.0, 6.0, box1 + 1.5), IRON_D, grain="x")
    d.box((13.0, -2.5, box1 + 0.5), (14.5, 2.5, box1 + 1.75), BRASS)
    return d.model


# ---- the axis piece -----------------------------------------------------------------------------------------
SLEEVE = (-3.0, 5.5, 4.25)      # the declination sleeve: from, to (texels from the head, towards the weights), radius
DEC_CIRCLE = (7.5, 7.5)         # the declination circle: where on the shaft, radius
WEIGHTS = ((10.0, 14.0), (14.5, 18.5))  # as far out as the room's north-west corner lets them hang
WEIGHT_R = 5.25
SHAFT_END = 20.5
POLAR_TOP = -5.0                # where the polar sleeve ends under the head, texels along the polar axis


def _axis():
    d = K.Draw(PREFIX + "axis", AXIS_SCALE)
    s0, s1, r = SLEEVE
    # the head of the polar axis and the sleeve across it, a bolted flange on either end
    d.tube("y", (0.0, 0.0), POLAR_TOP, 0.0, 3.5, IRON_D, sides=12)
    d.tube("y", (0.0, 0.0), POLAR_TOP, POLAR_TOP + 1.25, 4.5, K.BRASS_STUD, sides=12, seed=K.HOOP_SEED + 1)
    d.tube("z", (0.0, 0.0), s0, s1, r, IRON, sides=12)
    for a, b in ((s0, s0 + 1.5), (s1 - 1.5, s1)):
        d.tube("z", (0.0, 0.0), a, b, r + 0.75, K.IRON_D_STUD, sides=12, seed=K.HOOP_SEED + 2)
    d.tube("y", (0.0, 2.25), r - 0.5, r + 1.0, 1.5, BRASS, sides=8)          # the oil cup on the sleeve
    # the shaft, its divided circle, the two counterweights and the stop that keeps them on
    d.tube("z", (0.0, 0.0), s1, SHAFT_END, 1.5, STEEL, sides=8)
    K.circle(d, "z", (0.0, 0.0, DEC_CIRCLE[0]), DEC_CIRCLE[1], band=2.5, width=1.25, hub=2.75, n=6, sides=16)
    for a, b in WEIGHTS:
        d.tube("z", (0.0, 0.0), a, b, WEIGHT_R, IRON_D, sides=12)
        d.tube("z", (0.0, 0.0), a + 1.0, b - 1.0, WEIGHT_R + 0.25, IRON, sides=12)
        d.box((-1.0, WEIGHT_R - 0.5, (a + b) / 2.0 - 1.0), (1.0, WEIGHT_R + 1.5, (a + b) / 2.0 + 1.0), BRASS)
    d.tube("z", (0.0, 0.0), WEIGHTS[-1][1], WEIGHTS[-1][1] + 1.5, 2.5, BRASS_D, sides=8)
    return d.model


# ---- the mount ------------------------------------------------------------------------------------------------
FOOT = (9.0, 2.0)               # the cast foot: half size, height (texels)
COLUMN = [                      # the column's sections: y0, y1, half size, the depth of the flange at the head
    (2.0, 6.5, 7.0, 1.5),
    (6.5, 12.0, 5.5, 0.0),
]
HEAD_BLOCK = (7.25, 12.0, 13.5, -4.5, 4.5)      # the block the cheeks stand on: half size along x, y0, y1, z0, z1
CHEEK = (5.25, 6.75)            # the cheek plates: from, to along x, either side
CHEEK_HEAD = 4.0                # the round head of a cheek about its bolt: radius
POLAR = (-22.5, POLAR_TOP, 4.0)  # the polar sleeve: from, to (texels from the head along the axis), radius
HOUR_CIRCLE = (-24.75, 6.5)     # the hour circle: where on the axis, radius
WORM_WHEEL = (-26.5, 4.25)      # the worm wheel: where on the axis, radius to the middle of its teeth
POLAR_END = -28.5
CLOCK = (3.5, 4.25, 6.0)        # the driving clock on the column's west face: deep, high, wide


def _on_pole(k, x=0.0):
    """The point k texels from the head along the polar axis, in the mount's own frame (the
    origin on the foot, x east, y up, z south)."""
    hy = (head()[1] - FLOOR) * 16.0
    hz = (head()[2] - foot()[2]) * 16.0
    return (x, hy + k * POLE[1], hz + k * POLE[2])


def _mount():
    d = K.Draw(PREFIX + "mount", MOUNT_SCALE)
    # a cast foot, the column in two bolted sections, the block on its head
    half, high = FOOT
    d.box((-half, 0.0, -half), (half, high, half), K.IRON_D_STUD)
    for y0, y1, h, band in COLUMN:
        K.upright(d, y0, y1, h, band=band)
    bx, by0, by1, bz0, bz1 = HEAD_BLOCK
    d.box((-bx, by0, bz0), (bx, by1, bz1), K.IRON_STUD)
    # the two cheeks: each a plate that narrows to a round head about the bolt they hold the polar
    # sleeve by; under the bolt the screw that clamps the sleeve at the latitude
    x0, x1 = CHEEK
    hold = _on_pole(-HOLD)
    waist = (by1 + hold[1]) / 2.0
    for sgn in (-1.0, 1.0):
        a, b = sorted((sgn * x0, sgn * x1))
        d.box((a, by1, bz0), (b, waist, bz1), K.IRON_STUD, grain="y")
        d.box((a, waist, hold[2] - CHEEK_HEAD + 0.75), (b, hold[1], hold[2] + CHEEK_HEAD - 0.75), IRON, grain="y")
        a, b = sorted((sgn * (x0 - 0.125), sgn * (x1 + 0.25)))         # the head stands a little proud of the plate
        d.tube("x", (hold[1], hold[2]), a, b, CHEEK_HEAD, IRON, sides=12)
        a, b = sorted((sgn * (x1 + 0.25), sgn * (x1 + 1.5)))
        d.tube("x", (hold[1], hold[2]), a, b, 2.75, BRASS_D, sides=8)
        a, b = sorted((sgn * x1, sgn * (x1 + 0.75)))
        d.tube("x", (by1 + 3.0, bz0 + 2.5), a, b, 1.25, BRASS, sides=8)
    d.tube("x", (hold[1], hold[2]), -x1 - 2.25, x1 + 2.25, 1.25, STEEL, sides=8)
    # the polar sleeve between them, a bolted flange on either end; below it the steel axis with
    # the hour circle and the worm wheel
    p0, p1, r = POLAR
    with d.along(_on_pole(p0), _on_pole(p1)) as length:
        d.tube("y", (0.0, 0.0), 0.0, length, r, IRON, sides=12)
        for a, b in ((0.0, 1.5), (length - 1.5, length)):
            d.tube("y", (0.0, 0.0), a, b, r + 0.75, K.IRON_D_STUD, sides=12, seed=K.HOOP_SEED + 2)
        d.tube("y", (0.0, 0.0), POLAR_END - p0, 0.0, 1.75, STEEL, sides=8)
        K.circle(d, "y", (0.0, HOUR_CIRCLE[0] - p0, 0.0), HOUR_CIRCLE[1], band=2.5, width=1.25, hub=2.75, n=6,
                 sides=16)
        d.ring("y", (0.0, WORM_WHEEL[0] - p0, 0.0), WORM_WHEEL[1], 1.5, 1.5, K.IRON_TOOTH, sides=16)
        K.spokes(d, "y", (0.0, WORM_WHEEL[0] - p0, 0.0), 1.5, WORM_WHEEL[1] - 0.5, 4, IRON_D, wide=1.5, thick=1.0,
                 start=45.0)
        d.tube("y", (0.0, 0.0), POLAR_END - p0 - 0.75, POLAR_END - p0, 2.5, BRASS_D, sides=8)
    # the driving clock on the column's west face, where it shows from the door; its rod runs up to
    # the worm on the west side of the wheel
    deep, tall, wide = CLOCK
    face = -COLUMN[0][2]
    d.box((face - deep, high, -wide / 2.0), (face, high + tall, wide / 2.0), BRASS_D)
    d.box((face - deep - 0.25, high + 1.0, -wide / 2.0 + 1.0), (face - deep, high + tall - 1.0, wide / 2.0 - 1.0), K.DIAL)
    d.box((face - deep - 0.5, high + tall / 2.0, -0.5), (face - deep - 0.25, high + tall - 1.5, 0.5), K.HOOD)
    d.tube("z", (face - deep / 2.0, high + tall / 2.0), wide / 2.0, wide / 2.0 + 1.0, 1.0, BRASS, sides=8)
    reach = WORM_WHEEL[1] + 1.75
    worm = _on_pole(WORM_WHEEL[0], -reach)
    a = (worm[0], worm[1] + 1.5 * POLE[2], worm[2] - 1.5 * POLE[1])
    b = (worm[0], worm[1] - 1.5 * POLE[2], worm[2] + 1.5 * POLE[1])
    d.rod(a, b, 1.0, BRASS, sides=8)
    d.rod((face - deep / 2.0, high + tall, wide / 2.0 - 1.5), a, 0.5, STEEL, sides=4)
    return d.model


# ---- the package --------------------------------------------------------------------------------------------
SCALE = {PREFIX + "tube": TUBE_SCALE, PREFIX + "back": BACK_SCALE, PREFIX + "axis": AXIS_SCALE,
         PREFIX + "mount": MOUNT_SCALE}


@functools.lru_cache(maxsize=None)
def _built():
    return {m.name: m for m in (_tube(), _back(), _axis(), _mount())}


def models():
    return dict(_built())


TURNING = (PREFIX + "axis", PREFIX + "tube", PREFIX + "back")       # what the polar axis carries


def _turned(v, degrees):
    """A direction turned about the polar axis, right-handed: counter-clockwise seen from its tip."""
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    return _add(_add(_mul(v, c), _mul(_cross(POLE, v), s)), _mul(POLE, _dot(POLE, v) * (1.0 - c)))


def placed(turn=0.0):
    """What build() stands: [(model name, anchor in scene coordinates, frame, scale)]; with `turn`,
    the instrument that many degrees along its tracking (within -TRACK .. TRACK as it runs)."""
    out = [("mount", foot(), WORLD, MOUNT_SCALE), ("axis", head(), AXIS_FRAME, AXIS_SCALE),
           ("tube", head(), TUBE_FRAME, TUBE_SCALE), ("back", head(), TUBE_FRAME, BACK_SCALE)]
    out = [(PREFIX + name, at, frame, scale) for name, at, frame, scale in out]
    if turn:
        out = [(name, at, tuple(_turned(axis, turn) for axis in frame) if name in TURNING else frame, scale)
               for name, at, frame, scale in out]
    return out


def build(canvas, origin=(0, 0, 0), brightness=BRIGHTNESS):
    """Stand the astrograph in the small dome and set it tracking. Returns the number of display
    entities."""
    built = _built()
    n = 0
    for name, at, frame, scale in placed():
        n += K.put(canvas, built[name], at, frame, scale, origin, brightness)
        if MK is not None and name in TURNING:
            MK.swing(canvas, POLE, TRACK, -TRACK_PERIOD, keys=TRACK_KEYS)   # it sets off after the sky, westwards
    return n


# ---- the rules the numbers are held to ---------------------------------------------------------------------
def _room():
    """The small dome's shell as it is built, to hold the instrument against: a canvas, or None
    while main/smalldome is not in the tree."""
    try:
        from artkit.canvas import Canvas
        from ..main import smalldome
    except ImportError:
        return None
    c = Canvas()
    smalldome.build(c)
    return c


def check():
    """What can be told without a picture; returns the findings as lines (none is good)."""
    built = _built()
    out = K.size_findings(built, SCALE)
    room = _room()

    def cell(p):
        return tuple(int(math.floor(v)) for v in p)

    # 1. the frames are square and right-handed, and the tube's axis lies in the slit's plane
    for name, frame in (("tube", TUBE_FRAME), ("axis", AXIS_FRAME)):
        x, y, z = frame
        if abs(_dot(x, y)) + abs(_dot(y, z)) + abs(_dot(x, z)) > 1e-9 or math.dist(_cross(x, y), z) > 1e-9:
            out.append(f"{name}: its frame is not square and right-handed")
    if abs(pivot()[2] - DOME_AXIS[1]) > 1e-9 or abs(SIGHT[2]) > 1e-9:
        out.append("tube: its axis is not in the plane of the slit")
    # 2. nothing of it stands in the dome's shell or under the floor, as it stands and at either
    #    end of its tracking
    if room is not None:
        for turn in (0.0, -TRACK, TRACK):
            for name, at, frame, scale in placed(turn):
                bad = [p for _, p in K.corners(built[name], at, frame, scale) if p[1] < FLOOR or room.has(*cell(p))]
                if bad:
                    p = bad[0]
                    out.append(f"{name}{f', turned {turn:g} degrees' if turn else ''}: {len(bad)} corners in the "
                               f"dome's shell or under the floor, e.g. ({p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f})")
        # 3. the object glass looks out of the slit: nothing of the shell on the sight line
        p = objective()
        (x0, _, z0), (x1, y1, z1) = room.bounds()
        while x0 - 1 <= p[0] <= x1 + 1 and p[1] <= y1 + 1:
            if room.has(*cell(p)):
                out.append(f"sight: the shell stands on the line at {cell(p)}")
                break
            p = _add(p, _mul(SIGHT, 0.2))
    # 4. the plate holder is where a hand reaches it, the tube passes over a head at the door
    y = plate()[1] - FLOOR
    if not 0.9 <= y <= 1.6:
        out.append(f"plate: its middle is {y:.2f} over the floor, a hand wants 0.9 to 1.6")
    # 5. the tracking: the three pieces the polar axis carries stand on it, at the head; the tube
    #    and the back, anchored there, still have their own axis through pivot(); all three are
    #    registered with the motion line, and with nothing else
    for name, at, frame, scale in placed():
        if name not in TURNING:
            continue
        if math.dist(at, head()) > 1e-9:
            out.append(f"{name}: it does not stand on the polar axis at the head")
        if name == PREFIX + "axis":
            continue
        k = scale / 16.0
        origin = at
        for j in range(3):
            origin = _add(origin, _mul(frame[j], -built[name].anchor[j] * k))
        if math.dist(origin, pivot()) > 1e-9:
            out.append(f"{name}: its own axis stands {math.dist(origin, pivot()):.4f} off the pivot")
    if abs(_dot(_turned(DEC, 90.0), POLE)) > 1e-9 or math.dist(_turned(POLE, 37.0), POLE) > 1e-9:
        out.append("tracking: the turn is not about the polar axis")
    if MK is not None:
        from artkit.canvas import Canvas
        scratch = Canvas()
        build(scratch)
        if MK.registered(scratch) != (len(TURNING), 0):
            out.append(f"tracking: {MK.registered(scratch)} parts and points are registered, not {len(TURNING)} parts")
    return out


def report():
    c, r = sweep()
    lines = [f"tube: looks west, {ELEVATION:.2f} degrees up; pivot {tuple(round(v, 2) for v in pivot())}, "
             f"objective {tuple(round(v, 2) for v in objective())}, plate {tuple(round(v, 2) for v in plate())}",
             f"mount: head {tuple(round(v, 2) for v in head())}, foot {tuple(round(v, 2) for v in foot())}; "
             f"the saddle {_saddle_angle():.1f} degrees round the tube",
             f"sweep: centre {tuple(round(v, 2) for v in c)}, radius {r:.2f}",
             f"{len(placed())} display entities"]
    far = {}
    for what, p in (("the object glass", objective()), ("the plate", plate()),
                    ("the outer weight", _add(head(), _mul(DEC, -WEIGHTS[-1][1] / 16.0)))):
        v = _sub(p, head())
        far[what] = math.dist(_add(head(), _turned(v, TRACK)), p) * 16.0
    lines.append(f"tracking: {TRACK:g} degrees to either side about the polar axis, there and back in "
                 f"{TRACK_PERIOD} ticks" + ("" if MK is not None else " (no motion line in the tree: it stands)") + "; "
                 + ", ".join(f"{what} goes {px:.1f} texels either way" for what, px in far.items()))
    for name, model in _built().items():
        lo, hi = model.bounds()
        lines.append(f"  {name}: scale {SCALE[name]:g}, {len(model.parts)} boxes, "
                     + " x ".join(f"{(hi[i] - lo[i]) * model.px:.1f}" for i in range(3)) + " texels")
    return lines


if __name__ == "__main__":
    findings = check()
    if "check" not in sys.argv[1:]:
        print("\n".join(report()))
    print("self-check: " + ("; ".join(findings) if findings else
                            "sizes, the frames, the room, the slit, the plate holder, the tracking -- all good"))
    sys.exit(1 if findings else 0)
