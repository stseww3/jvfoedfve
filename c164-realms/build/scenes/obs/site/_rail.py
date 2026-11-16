"""site/_rail: the railway's line. One set of numbers, read by the masonry, the ironwork, the cloud
and everything that moves along the line (A0 #85320, 11-16; plan/round2.md, card site/railway;
the plan is drawn in plan/packages/site/railway.md). This module places nothing.

The train comes up out of the cloud to the summit station, where the cable car stood. Going out
from the station (the way the distance s is counted, in blocks along the line in plan):

  the station   level and due east from the buffers (x 88) over the platform's edge (x 92) and
                four columns on; the rails lie in the paving, their upper face at the level feet
                stand on (-4). The car stands here, square to the platform.
  the incline   straight on, due east: from x 96 half a block down with every column to the foot
                at x 112. The rack and the cable work here. No bend between the buffers and the
                foot: the tower and the comet stand dead ahead of whoever comes up.
  the viaduct   stone, from the foot: a curve to the right, of RADIUS, as far as due south, then
                straight on down the column FAR. One block down in nine of line, a block to every
                arch, all the way: the first arches stand sixteen blocks over the cloud and the
                last ones drown in it, and the line ends under the sea's face, where the train
                waits unseen.

The cable's track as it was built left the station's axis at x 92.5, a row north with every three
columns east. The train's car is five blocks long and stands across that place, and block rails
that step sideways under a straight engine do not bear looking at from the platform: so the line
is straight from the buffers to the foot, and the ridge under it (site/_kit.cable_ridge, the
terrain) and the ironwork (site/cablecar, machines/cable) follow it (cable #90197).

Nothing of it stands west of x 112, so the arrival view is as it was; the whole sweep lies in the
open sector that the grand stair and the lower platform look out on to the east, between the
station and the power house, and the train passes the mountain broadside before it turns in.

Who builds what: the iron columns x 92..111 stay cable's (site/cablecar; its END follows FOOT);
the masonry from the foot on is site/viaduct, one pier at each of piers(), an arch between; what
stands lower than CLOUD is the cloud's, and so is the sea over the line's end. Everybody takes
the cells from deck() and the levels from tread(), and nobody draws the line a second time.

What must stay clear (GAUGE): over the track's three rows nothing but the track from the rails'
level to five blocks above it; in the row outside them on either side nothing higher than a block
over the rails (a parapet); poles, signals and posts stand in that row or further out, and on the
left of one going out (the side away from the mountain, the curve's outer side): left(s).

Walkers do not get on to the line. The station's track is paving and is walked on; the line's
mouth is the three cells MOUTH in the first column east of the platform. While the train is away
they are shut two blocks high (a gate that is seen, with barriers for its collision), and while it
stands in the station the car stands in them. East of the mouth nothing is ground for a walker:
no walk starts there and the walk-through counts any place it reaches there as a way out.
"""
import functools
import math
from collections import namedtuple

from ..common import skeleton as S
from . import _kit as K

# --- the numbers ----------------------------------------------------------------------------------------
ROW = K.CABLE_RIDGE_Z                       # -33: the row of the track's axis in the station
FEET = float(S.STATION_GROUND)              # -4.0: the upper face of the rails in the station
HEAD = float(int(S.V1["pos"][0]))           # 88.0: the rails' west end, at the buffers
EDGE = S.CABLE_STATION[2] + 1.0             # 92.0: the platform's east edge
LEVEL = 4                                   # columns of level track east of the platform (x 92..95)
BROW = EDGE + LEVEL                         # 96.0: the level track ends,
STEEP = 0.5                                 # ... and every column east of it is half a block lower: the incline
FOOT = 112.0                                # the incline's foot; the last iron column is x 111
FAR = 175                                   # the column of the far straight, which runs due south
PITCH = 9.0                                 # from pier to pier of the viaduct, along the line
PIER = 2.0                                  # a pier's length along the line: an arch spans PITCH - PIER
SPANS = 17                                  # the viaduct's arches
EASY = 1.0 / PITCH                          # down with every block of line from the foot outwards: a block an arch
CLOUD = K.ROCK_FLOOR + 5                    # -24: no cloud lies higher beside what stands in the sea (cablecar.CLOUD)

Z = ROW + 0.5                               # -32.5: the centre line from the buffers to the foot
RADIUS = FAR + 0.5 - FOOT                   # 63.5
CENTRE = (FOOT, Z + RADIUS)                 # (112.0, 31.0), x and z: the curve is a quarter of a circle

S_EDGE = EDGE - HEAD                        # 4.0
S_BROW = BROW - HEAD                        # 8.0
S_FOOT = FOOT - HEAD                        # 24.0
S_CURVE = S_FOOT + RADIUS * math.pi / 2.0   # 123.75: the curve's end, at (175.5, 31.0)
LENGTH = S_FOOT + SPANS * PITCH + PIER      # 179.0: the line's end, at (175.5, 86.25), the rails at -29.2
FOOT_LEVEL = FEET - STEEP * (FOOT - BROW)   # -12.0

# The train: one car, which leads uphill, and the engine that pushes it at the downhill end (A0
# #89927). The numbers are the car's middle, s of travel(). STOP: the car's west door where the cable
# car's was (x 90) and its body out over the level track east of the platform, so that it stands in
# the mouth; the engine east of it on the brow and the head of the incline. START: both under the
# cloud at the line's end.
CAR = 5.0                                   # the car's length; it is three wide, the track's three rows
ENGINE = 3.5                                # the engine's
DOOR = S.CABLE_STATION[2] - 1.0             # 90.0: the car's west end when it stands in the station
STOP = DOOR + CAR / 2.0 - HEAD              # 4.5: the car on x 90..95
START = LENGTH - 6.5                        # 172.5: the engine's far end half a block short of the line's end
SPEED = dict(station=1.5, incline=2.5, viaduct=4.0)     # blocks a second, proposed: START to STOP in about 46 s

GAUGE = dict(half=1.5, height=5.0, parapet=1.0)
MOUTH = dict(cells=[(int(EDGE), ROW + d) for d in (-1, 0, 1)], y=(int(FEET), int(FEET) + 1))


class Point(namedtuple("Point", "s x y z hx hz slope")):
    """A place on the line: s, the point on the centre line at the level of the rails' upper face,
    the unit heading in plan of one going out, and the rise for each block of line going out
    (negative: the line goes down)."""
    __slots__ = ()

    @property
    def yaw(self):
        """Minecraft's yaw of one who looks out along the line; coming in it is this and 180."""
        return math.degrees(math.atan2(-self.hx, self.hz))

    @property
    def pitch(self):
        """Degrees above the level, going out (Minecraft's pitch has the other sign)."""
        return math.degrees(math.atan(self.slope))

    def off(self, right=0.0, up=0.0):
        """(x, y, z) of the point so far to the right of one going out, and so far above the rails."""
        return self.x - self.hz * right, self.y + up, self.z + self.hx * right


def level(s):
    """y of the rails' upper face at s: the line the wheels run on. On the incline the rails are
    slabs, each column's half a block under the last, and this is the line through their outer
    edges: no wheel that keeps to it sinks into a slab."""
    if s <= S_BROW:
        return FEET
    if s <= S_FOOT:
        return FEET - STEEP * (s - S_BROW)
    return FOOT_LEVEL - EASY * (s - S_FOOT)


def at(s):
    """The Point at s. Before 0 and past LENGTH the line is carried straight on, so that a vehicle
    whose middle is near an end has both its axles somewhere."""
    s = float(s)
    if s <= S_FOOT:
        x, z, hx, hz = HEAD + s, Z, 1.0, 0.0
    elif s <= S_CURVE:
        a = (s - S_FOOT) / RADIUS
        x, z, hx, hz = CENTRE[0] + RADIUS * math.sin(a), CENTRE[1] - RADIUS * math.cos(a), math.cos(a), math.sin(a)
    else:
        x, z, hx, hz = FAR + 0.5, CENTRE[1] + (s - S_CURVE), 0.0, 1.0
    slope = 0.0 if s <= S_BROW else -STEEP if s <= S_FOOT else -EASY
    return Point(s, x, level(s), z, hx, hz, slope)


def pose(s, base=0.0):
    """How a vehicle lies whose two axles stand on the line ``base`` apart with its middle at s: a
    Point half way between the axles, heading and slope along the line through both. This is what
    takes a car smoothly over the brow and the foot and round the curve."""
    if base <= 0.0:
        return at(s)
    a, b = at(s - base / 2.0), at(s + base / 2.0)
    dx, dy, dz = b.x - a.x, b.y - a.y, b.z - a.z
    run = math.hypot(dx, dz)
    return Point(float(s), (a.x + b.x) / 2.0, (a.y + b.y) / 2.0, (a.z + b.z) / 2.0, dx / run, dz / run, dy / run)


def left(s, out=2.0, up=0.0):
    """(x, y, z) beside the line on the side where poles and signals stand, ``out`` from the centre."""
    return at(s).off(-out, up)


def s_of_level(y):
    """Where on the viaduct the rails are at y (the cloud asks where the train comes out of it)."""
    return S_FOOT + (FOOT_LEVEL - y) / EASY


def project(x, z):
    """(s, right): the place on the line nearest to the point (x, z) and how far the point lies to
    the right of one going out there; None where the point is abreast of no part of the line."""
    best = None
    for s0, s1, find in _PARTS:
        s, right = find(x, z)
        if s0 - 1e-9 <= s <= s1 + 1e-9 and (best is None or abs(right) < abs(best[1])):
            best = (s, right)
    return best


def _on_arc(x, z):
    dx, dz = x - CENTRE[0], z - CENTRE[1]
    return S_FOOT + math.atan2(dx, -dz) * RADIUS, RADIUS - math.hypot(dx, dz)


_PARTS = (
    (0.0, S_FOOT, lambda x, z: (x - HEAD, z - Z)),
    (S_FOOT, S_CURVE, _on_arc),
    (S_CURVE, LENGTH, lambda x, z: (S_CURVE + z - CENTRE[1], FAR + 0.5 - x)),
)


def row(x):
    """The row of the track's axis in a column of the station or the incline: one row, ROW."""
    return ROW


def tread(s=None, x=None):
    """y of the upper face of the rails as they are built, in half blocks: in a column x of the
    station or the incline as the cable's track has it (cablecar.rail_top: x 96 is the first that
    is lower), on the viaduct the half block nearest to level(s)."""
    if x is not None:
        return FEET - STEEP * max(0.0, x + 1.0 - BROW)
    return round(2.0 * level(s)) / 2.0


def slab(top):
    """The cell and the half of it whose upper face is at ``top`` (a multiple of a half)."""
    if top == int(top):
        return int(top) - 1, "top"
    return int(math.floor(top)), "bottom"


Cell = namedtuple("Cell", "s right top")


@functools.lru_cache(maxsize=None)
def deck(half=1.5):
    """{(x, z): Cell}: the columns of blocks within ``half`` of the centre line, with where each
    lies (s along the line, how far right of one going out) and ``top``, the upper face of the
    rails at its place in half blocks (slab() gives the block). abs(right) below 0.5 is the row
    between the rails, 0.5 to 1.5 the rails, 1.5 to 2.5 the row outside them. West of FOOT the
    columns are the iron track's, with its levels; from FOOT on they are found from the line."""
    cells = {}
    wide = int(math.ceil(half - 0.5))
    for x in range(int(HEAD), int(FOOT)):
        for d in range(-wide, wide + 1):
            cells[(x, row(x) + d)] = Cell(x + 0.5 - HEAD, float(d), tread(x=x))
    for x in range(int(FOOT), FAR + wide + 2):
        for z in range(int(Z) - wide - 2, int(at(LENGTH).z) + 1):
            found = project(x + 0.5, z + 0.5)
            if found and found[0] >= S_FOOT and abs(found[1]) <= half:
                cells[(x, z)] = Cell(found[0], found[1], tread(found[0]))
    return cells


def piers():
    """The viaduct's piers, a Point at the middle of each: the first against the last iron column,
    the last at the line's end under the cloud. A pier is PIER long and stands square to the line."""
    return [at(S_FOOT + PIER / 2.0 + PITCH * k) for k in range(SPANS + 1)]


def sketch(scale=3):
    """The plan as text, a character to ``scale`` blocks, north at the top: # the station and the
    incline, o the viaduct, P a pier, S the spawn."""
    marks = {}
    for (x, z), cell in deck(1.5).items():
        marks[(x // scale, z // scale)] = "#" if cell.s < S_FOOT else "o"
    for p in piers():
        marks[(int(p.x) // scale, int(p.z) // scale)] = "P"
    marks[(int(HEAD) // scale, ROW // scale)] = "S"
    xs, zs = [k[0] for k in marks], [k[1] for k in marks]
    return "\n".join("".join(marks.get((x, z), ".") for x in range(min(xs) - 9, max(xs) + 2))
                     for z in range(min(zs) - 1, max(zs) + 2))
