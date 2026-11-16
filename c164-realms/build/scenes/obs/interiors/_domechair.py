"""The observing ladder of the great dome room and the track it rolls on (a helper of
interiors/domeroom; the auto-discovery skips modules that start with "_").

    the track    two rings of flat iron about the dome's axis, let into the boards so that no more
                 than a texel of them stands proud. Each ring is laid in lengths of about a block
                 that butt end to end, a screw near either end of every length; the wheels have
                 worn the top bright. The rings pass outside the corners of the curb round the
                 pier's opening and inside everything that stands against the lining.
    the ladder   a step ladder on four wheels with a seat on top, for the nights when the
                 telescope points low and its eyepiece rides high. The family's make (props/
                 furniture): dark wood carried on cast iron, brass where a hand goes. Two sole
                 bars, one over each ring, a wheel under either end of them; two iron stringers
                 that rise from the inner sole bar, away from the pier, with the treads between
                 them; on top a boarded seat with a cloth pad between four posts; a wooden rail
                 round three sides of the seat and down either side of the steps, a brass knuckle
                 wherever it turns. One climbs towards the wall and sits down facing the pier: as
                 the tube comes down its eyepiece rises and moves outwards, and so does whoever
                 climbs.

The ladder is parked north-west of the pier (PARKED), between the stair's exit and the hand wheel of
the dome's gear, and may be rolled all the way round: band() is what it passes over, and the room
keeps that clear of everything that stands. The track is one display entity and the ladder another.

It does not stand still (round 2: whatever can move does). Its carriage is geared to the drive that
makes the telescope follow the sky, so that the seat keeps its place by the eyepiece: while the tube
swings to either side the ladder rolls ROLL blocks along the track and back in the same beat
(machines/scope.FOLLOW_PERIOD). It is slid along the tangent of the track where it is parked; over
so short a way it leaves the arc by less than a fifth of a texel.

The telescope. machines/scope.sweep() is the ball that holds every part of the telescope wherever
it points. Its radius is the reach of the objective, which is never below the level of the
crossing of the axes when the tube looks out of the slit; the floor itself lies inside that ball
within seven and a half blocks of the axis, so nothing that rolls on this track can stay out of
it. What does come down to the ladder is the tube's lower end, and that reaches no further from
the crossing than the eyepiece does. The ladder stays out of that smaller ball wherever it stands
on the track (the crossing is on the axis the track goes round), and below the crossing: report()
says by how much.

Frames. The track is drawn about the dome's axis with the world's directions, y = 0 the top of the
boards. The ladder is drawn with its origin on the boards half way between the rings, x along the
track and +z towards the dome's axis; shown with yaw = azimuth + 90 it looks at the axis from
`azimuth` degrees round it (0 = east, 90 = south). The ladder's lengths are texels.

    python -m scenes.obs.interiors._domechair      the numbers the room needs, a plan, the checks
"""
import copy
import functools
import importlib
import math
import tempfile

from artkit import models as M
from artkit.pixelart import Mat

from ..common import palette as P
from ..common import skeleton as S
from ..props import _kit as K

PREFIX = "int_domeroom_"
TEXEL = 0.0625
AXIS = S.DOME_AXIS                      # (x, z) of what the dome turns about, and the track goes round
FLOOR = float(S.ROOF_STAND)             # the top of the boards

# --- the track ------------------------------------------------------------------------------------
RAILS = (6.75, 8.25)                    # the middle lines of the two rings, in blocks from the axis
RAIL_WIDE = 2.0 * TEXEL
RAIL_PROUD = TEXEL                      # what stands above the boards: no more than a texel
LENGTHS = 48                            # lengths of flat iron to a ring
SCREW = 2                               # a screw this many texels from either end of a length
RAIL_SCALE = 6                          # both rings are one model: 18 blocks across, 16 texels to the block

# --- the ladder -----------------------------------------------------------------------------------
PARKED = 240.0                          # where it stands, in degrees round the axis: north-west of the pier, on
#                                         the floor V8 had empty in its right half (review cr3, #86316), clear of
#                                         the hand wheel of the dome's gear beyond it. Till round 2 it stood at
#                                         144.5, south-west, where the pier hid it from V8
ROLL = 0.35                             # blocks it rolls along the track to either side of there
FOLLOW_PERIOD = 480                     # ticks there and back, while machines/scope is not in the tree
WHEEL_AT = 8.0                          # the wheels, either side of the ladder's middle along the track
WHEEL_R, WHEEL_WIDE = 2.5, 1.5          # (to a flat of their eight, across the tread)
SOLE = (4.5, 6.5)                       # the sole bars: their underside and their top
SOLE_HALF = 11.0                        # and how far they run either side of the middle
FRAME = 8.75                            # the middle of an end frame, from the ladder's middle line
BOARD = 9.75                            # the footboard and the seat run this far: over the frames
RISE, GOING = 5.0, 4.0                  # from one tread to the next: up, and away from the pier
TREADS = 4                              # between the footboard and the seat
TREAD_DEEP = 5.0
NOSE = 2.0                              # the footboard's front edge, in front of the inner sole bar's middle
RAIL_TOP = 45.0                         # the middle of the rail round the seat
BAR = 1.5                               # the posts: square
WOODEN = 1.75                           # the rail on them: square, and a little stouter
KNUCKLE = 2.25                          # the brass where the rail turns: a cube

LIGHT = (9, 0)                          # (sky, block) both pieces are shown in: the room is dark
CLEAR = 2.0 * TEXEL                     # the least kept between the rolling ladder and what stands by the track
TAIL_SPARE = 0.25                       # what the tube's lower end carries beyond its eyepiece, and room to spare
# the telescope while machines/scope is not in the tree: the crossing of its axes above the boards,
# and how far its eyepiece is from there (version a, the director's pick)
CROSSING, TAIL = 5.0, 6.562
MOST = 30                               # display entities the room allows the two together


# --- materials ------------------------------------------------------------------------------------
class Strip(Mat):
    """A length of flat iron let into a floor: the last texel of its length is the dark of the
    joint with the next. Seen from above (`screws`) a screw head near either end: a light texel
    and a dark one in its shadow."""
    screws = False

    def levels(self, w, h, grain, seed):
        lv = super().levels(w, h, grain, seed)
        rows = lv if h >= w else lv.T               # a view: one row to every texel of the length
        n = rows.shape[0]
        if n < 4 * SCREW + 4:
            return lv
        if self.screws and rows.shape[1] >= 2:
            for at in (SCREW, n - 2 - SCREW):
                rows[at, 0] = self.base + 1
                rows[at, -1] = self.base - 2
        rows[-1, :] = self.base - 4 if self.screws else 0
        return lv


def _as(cls, mat, tag, **more):
    """`mat` painted the way of `cls`: the same ramp, tone and bevel."""
    m = copy.copy(mat)
    m.__class__ = cls
    m.name = f"{mat.name}~{tag}"
    m._variants = {}
    m.__dict__.update(more)
    return m


WORN = _as(Strip, P.mat("iron", base=5, bevel=0, noise=0.1), "worn", screws=True)   # where the wheels run
EDGE = _as(Strip, K.flat("iron", 2), "edge")                                       # the texel that stands proud
CAST = P.mat("iron", bevel="along")             # the frame's bars: light and dark edge along them only
CAST_D = K.IRON_D                               # the sole bars and the wheels
STEEL = K.flat("iron", 5)                       # an axle's end
TREAD = P.mat("dark_wood", base=3)              # the boards one steps and sits on: the lighter wood
RAIL = P.mat("dark_wood")                       # the rail a hand slides along
CLOTH = P.mat("enamel_cloth")
BRASS = K.BRASS


def _other(line, name):
    """Another package's module when it is in the tree, else None."""
    try:
        return importlib.import_module(f"..{line}.{name}", __package__)
    except ModuleNotFoundError as e:
        if e.name != f"{__package__.rsplit('.', 1)[0]}.{line}.{name}":
            raise                               # the module is there and fails to import something
        return None


# --- the models -----------------------------------------------------------------------------------
def _track():
    """Both rings. A length is a straight bar: its ends stand as far outside its ring's circle as
    its middle lies inside it, and it is as much longer as closes the joint on the outside of the
    bend."""
    m = M.Model(PREFIX + "rail", px=RAIL_SCALE)
    unit = 16.0 / RAIL_SCALE
    half = math.pi / LENGTHS
    for ring, radius in enumerate(RAILS):
        corner = 2.0 * radius / (1.0 + math.cos(half))
        middle = corner * math.cos(half)
        length = 2.0 * corner * math.sin(half) + RAIL_WIDE * math.tan(half)
        for i in range(LENGTHS):
            with m.turned(("y", -(i + 0.5) * 360.0 / LENGTHS)):
                m.box(((middle - RAIL_WIDE / 2.0) * unit, 0.0, -length / 2.0 * unit),
                      ((middle + RAIL_WIDE / 2.0) * unit, RAIL_PROUD * unit, length / 2.0 * unit),
                      EDGE, faces={"u": WORN}, skip="nsd", grain="z", seed=10 * ring + i % 3 + 1)
    return m


def _over(ring, x):
    """z of the middle line of ring 0 (the inner) or 1 at x off the ladder's middle, in the ladder's
    frame and in texels."""
    return (sum(RAILS) / 2.0 - math.sqrt(RAILS[ring] ** 2 - (x * TEXEL) ** 2)) / TEXEL


def _ladder():
    m = M.Model(PREFIX + "chair")
    zi, zo = _over(0, WHEEL_AT), _over(1, WHEEL_AT)     # the sole bars: the chords over the wheels
    low, top = SOLE
    axle = RAIL_PROUD / TEXEL + WHEEL_R
    for z in (zi, zo):
        for x in (-WHEEL_AT, WHEEL_AT):
            m.tube("z", (x, axle), z - WHEEL_WIDE / 2.0, z + WHEEL_WIDE / 2.0, WHEEL_R, CAST_D)
            m.tube("z", (x, axle), z - WHEEL_WIDE / 2.0 - 0.5, z + WHEEL_WIDE / 2.0 + 0.5, 0.5, STEEL, sides=4)
        m.box((-SOLE_HALF, low, z - 1.0), (SOLE_HALF, top, z + 1.0), CAST_D, grain="x")

    # the steps: the footboard lies on the inner sole bar, the seat is the last of them
    front = zi + NOSE                                   # the footboard's front edge

    def step(k):                                        # (the top of step k, its front edge)
        return top + 1.0 + RISE * k, front - GOING * k

    seat, seat_front = step(TREADS + 1)
    m.box((-BOARD, top, front - TREAD_DEEP), (BOARD, top + 1.0, front), TREAD, grain="x")
    for k in range(1, TREADS + 1):
        y, z = step(k)
        m.box((-FRAME + 0.5, y - 1.0, z - TREAD_DEEP), (FRAME - 0.5, y, z), TREAD, grain="x")
    m.box((-BOARD, seat - 1.0, zo - 1.0), (BOARD, seat, seat_front), TREAD, grain="x")
    m.box((-7.0, seat, zo + 1.0), (7.0, seat + 1.0, seat_front - 0.75), CLOTH, grain="x")

    # the rail: up from the newels on the footboard to the knees over the seat's front, level from
    # there to the back posts and across between them
    knee = seat_front - 0.25 - BAR / 2.0                # the posts on the seat's front corners
    newel = front - 0.25 - BAR / 2.0                    # and on the footboard's
    hand = RAIL_TOP - (newel - knee) * RISE / GOING     # the rail over the newel: it runs with the steps

    def along(y):                                       # z of the line through the middles of the treads
        return front - TREAD_DEEP / 2.0 - (y - top - 0.5) * GOING / RISE

    tie = (top + seat) / 2.0                            # the bars half way up
    for side in (-1.0, 1.0):
        x = side * FRAME
        a, b = sorted((side * (FRAME - 0.75), side * (FRAME + 0.75)))
        m.box((a, low, zo + 1.0), (b, top, zi - 1.0), CAST_D, grain="z")                     # the end of the frame
        m.beam((x, top - 0.5, along(top - 0.5)), (x, seat - 1.5, along(seat - 1.5)), 1.25, 3.5, CAST)   # the stringer
        m.box((a, top, zo - BAR / 2.0), (b, RAIL_TOP - BAR / 2.0, zo + BAR / 2.0), CAST, grain="y")      # the back post
        m.box((a, seat, knee - BAR / 2.0), (b, RAIL_TOP - BAR / 2.0, knee + BAR / 2.0), CAST, grain="y")
        m.box((a, top + 1.0, newel - BAR / 2.0), (b, hand - BAR / 2.0, newel + BAR / 2.0), CAST, grain="y")
        m.box((x - 0.5, tie - 0.75, zo + 0.5), (x + 0.5, tie + 0.75, along(tie)), CAST, grain="z")
        m.box((x - WOODEN / 2.0, RAIL_TOP - WOODEN / 2.0, zo), (x + WOODEN / 2.0, RAIL_TOP + WOODEN / 2.0, knee), RAIL, grain="z")
        m.beam((x, hand, newel), (x, RAIL_TOP, knee), WOODEN, WOODEN, RAIL)
        for y, z in ((RAIL_TOP, zo), (RAIL_TOP, knee), (hand, newel)):
            m.box((x - KNUCKLE / 2.0, y - KNUCKLE / 2.0, z - KNUCKLE / 2.0),
                  (x + KNUCKLE / 2.0, y + KNUCKLE / 2.0, z + KNUCKLE / 2.0), BRASS)
    m.box((-FRAME, RAIL_TOP - WOODEN / 2.0, zo - WOODEN / 2.0), (FRAME, RAIL_TOP + WOODEN / 2.0, zo + WOODEN / 2.0), RAIL,
          grain="x")
    m.box((-FRAME + 0.5, tie - 0.75, zo - 0.5), (FRAME - 0.5, tie + 0.75, zo + 0.5), CAST, grain="x")
    return m


@functools.lru_cache(maxsize=None)
def _models():
    return {m.name: m for m in (_ladder(), _track())}


def models():
    return dict(_models())


# --- where they are -------------------------------------------------------------------------------
def at(degrees):
    """((x, y, z), yaw): where the ladder's origin is when it stands `degrees` round the axis, and
    how it is turned there, in scene coordinates without the origin."""
    a, r = math.radians(degrees), sum(RAILS) / 2.0
    return (AXIS[0] + r * math.cos(a), FLOOR, AXIS[1] + r * math.sin(a)), (degrees + 270.0) % 360.0 - 180.0


def parked():
    return at(PARKED)


def place(canvas, origin=(0, 0, 0)):
    """Lay the track, park the ladder on it and set it rolling; returns the number of display
    entities."""
    got = models()
    n = K.put(canvas, got[PREFIX + "rail"], (AXIS[0], FLOOR, AXIS[1]), yaw=0.0, scale=RAIL_SCALE, origin=origin,
              brightness=LIGHT)
    pos, yaw = parked()
    n += K.put(canvas, got[PREFIX + "chair"], pos, yaw=yaw, origin=origin, brightness=LIGHT)
    _roll(canvas)
    return n


def _roll(canvas):
    """Register the ladder, the piece placed last, with the motion line: it slides along the track's
    tangent, ROLL blocks the way the degrees count while the telescope's eyepiece goes that way
    (the first quarter of the beat), back through where it is parked to as far on the other side,
    and home. While motion is not in the tree it stands parked, as it does in every offline picture."""
    MK = _other("motion", "_kit")
    if MK is None:
        return
    period = int(getattr(_other("machines", "scope"), "FOLLOW_PERIOD", FOLLOW_PERIOD))
    a, quarter = math.radians(PARKED), period // 4
    MK.slide(canvas, (-math.sin(a), 0.0, math.cos(a)),
             [(0, ROLL, quarter), (quarter, -ROLL, 2 * quarter), (3 * quarter, 0.0, period - 3 * quarter)], period)


# --- what the room is told ------------------------------------------------------------------------
def _boxes(model):
    """(middle, half sizes, turn) of every box, in the model's units."""
    for p in model.parts:
        yield (tuple((p["lo"][i] + p["hi"][i]) / 2.0 for i in range(3)),
               tuple((p["hi"][i] - p["lo"][i]) / 2.0 for i in range(3)), p["rot"][0] if p["rot"] else M.IDENT)


def _corners(box):
    mid, half, q = box
    out = []
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            for sz in (-1.0, 1.0):
                v = M._qrot(q, (sx * half[0], sy * half[1], sz * half[2]))
                out.append(tuple(mid[i] + v[i] for i in range(3)))
    return out


def _to_line(p, a, b):
    """How far the point p is from the stretch a..b (in the plane)."""
    dx, dz = b[0] - a[0], b[1] - a[1]
    span = dx * dx + dz * dz
    t = 0.0 if span < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / span))
    return math.hypot(a[0] + dx * t - p[0], a[1] + dz * t - p[1])


def _plan_gap(points, p):
    """How near the plan of a box (its corners, as (x, z)) comes to the point p outside it."""
    return min(_to_line(p, a, b) for i, a in enumerate(points) for b in points[i:])


def _to_box(box, p):
    """How far the point p is from a box."""
    mid, half, q = box
    own = M._qrot((-q[0], -q[1], -q[2], q[3]), tuple(p[i] - mid[i] for i in range(3)))
    return math.sqrt(sum(max(abs(own[i]) - half[i], 0.0) ** 2 for i in range(3)))


def band():
    """(inner, outer), in blocks from the dome's axis: what the ladder passes over as it is rolled
    round, from the nearest it comes to the axis to the furthest. Nothing may stand there."""
    axis = (0.0, sum(RAILS) / 2.0 / TEXEL)
    plans = [[(c[0], c[2]) for c in _corners(box)] for box in _boxes(_models()[PREFIX + "chair"])]
    inner = min(_plan_gap(plan, axis) for plan in plans)
    outer = max(math.hypot(x - axis[0], z - axis[1]) for plan in plans for x, z in plan)
    return inner * TEXEL, outer * TEXEL


def height():
    """How high the ladder stands above the boards, in blocks."""
    return max(c[1] for box in _boxes(_models()[PREFIX + "chair"]) for c in _corners(box)) * TEXEL


def nearest(above):
    """How near the ladder comes, wherever it stands on the track, to the point of the dome's axis
    that is `above` the boards (blocks)."""
    p = (0.0, above / TEXEL, sum(RAILS) / 2.0 / TEXEL)
    return min(_to_box(box, p) for box in _boxes(_models()[PREFIX + "chair"])) * TEXEL


def columns(degrees=None):
    """{(x, z)}: the columns the ladder stands in when it is `degrees` round the axis (where it is
    parked, if not said)."""
    pos, yaw = at(PARKED if degrees is None else degrees)
    out = set()
    for box in _boxes(_models()[PREFIX + "chair"]):
        plan = [(c[0], c[2]) for c in _corners(box)]
        (x0, x1), (z0, z1) = ((min(p[i] for p in plan), max(p[i] for p in plan)) for i in range(2))
        nx, nz = int(math.ceil(x1 - x0)) + 1, int(math.ceil(z1 - z0)) + 1
        for i in range(nx + 1):
            for j in range(nz + 1):
                dx, _, dz = K.turn(yaw, ((x0 + (x1 - x0) * i / nx) * TEXEL, 0.0, (z0 + (z1 - z0) * j / nz) * TEXEL))
                out.add((int(math.floor(pos[0] + dx)), int(math.floor(pos[2] + dz))))
    return out


def telescope():
    """(how high the crossing of the telescope's axes is above the boards, how far its lower end
    reaches from there): from machines/scope when it is in the tree."""
    scope = _other("machines", "scope")
    if scope is None:
        return CROSSING, TAIL + TAIL_SPARE
    centre, _ball = scope.sweep()
    return centre[1] - FLOOR, math.dist(scope.eyepiece(), centre) + TAIL_SPARE


# --- the checks -----------------------------------------------------------------------------------
def _to_cell(cell, far=False):
    """How near the column `cell` comes to the dome's axis (or how far its furthest corner is)."""
    if far:
        return max(math.hypot(x - AXIS[0], z - AXIS[1]) for x in (cell[0], cell[0] + 1) for z in (cell[1], cell[1] + 1))
    return math.hypot(max(cell[0] - AXIS[0], AXIS[0] - cell[0] - 1, 0.0), max(cell[1] - AXIS[1], AXIS[1] - cell[1] - 1, 0.0))


def _rings():
    """[(inner edge, outer edge)] of the two rings as they are drawn, in blocks from the axis."""
    unit, out = 16.0 / RAIL_SCALE, []
    boxes = list(_boxes(_models()[PREFIX + "rail"]))
    for ring in range(len(RAILS)):
        plans = [[(c[0], c[2]) for c in _corners(box)] for box in boxes[ring * LENGTHS:(ring + 1) * LENGTHS]]
        out.append((min(_plan_gap(plan, (0.0, 0.0)) for plan in plans) / unit,
                    max(math.hypot(x, z) for plan in plans for x, z in plan) / unit))
    return out


def _in_the_way(inner, outer):
    """[(kind, nearest, furthest)]: the room's furniture that stands in the band as the room has it
    now, when the room and props/furniture are in the tree."""
    room, furniture = _other("interiors", "domeroom"), _other("props", "furniture")
    if room is None or furniture is None:
        return []
    out = []
    for kind, (x, z), facing in getattr(room, "FURNITURE", ()):
        model = furniture.models().get(furniture.PREFIX + kind)
        if model is None:
            continue
        spots = []
        for box in _boxes(model):
            plan = []
            for c in _corners(box):
                dx, _, dz = K.turn(K.FACING[facing], (c[0] * TEXEL, 0.0, c[2] * TEXEL))
                plan.append((x + dx, z + dz))
            spots.append(plan)
        near = min(_plan_gap(plan, AXIS) for plan in spots)
        far = max(math.hypot(px - AXIS[0], pz - AXIS[1]) for plan in spots for px, pz in plan)
        if near < outer + CLEAR and far > inner - CLEAR:
            out.append((kind, near, far))
    return out


def report():
    """Print the numbers the room needs and a plan, then check the two pieces against the room;
    returns the number of checks that fail."""
    from ..main import _order as O
    from . import domeroom as D
    from artkit.canvas import Canvas

    got = models()
    ladder, track = got[PREFIX + "chair"], got[PREFIX + "rail"]
    inner, outer = band()
    pos, yaw = parked()
    stands = columns()
    rings = _rings()
    crossing, reach = telescope()
    room, wall, hole = D.room(), D.lined(), D.envelope()
    floor = room - wall - hole
    doors = set(D.doorways())
    out = D.stair_exit() or (S.DOME_CENTRE[0], S.PIER_ENVELOPE[1] - 1)
    step = (out[0], out[1] - 1)                     # the first cell of the boards north of the stair's exit

    print(f"the track: two rings about ({AXIS[0]}, {AXIS[1]}), middle lines {RAILS[0]} and {RAILS[1]} blocks out, "
          f"{RAIL_WIDE / TEXEL:g} texels wide, {RAIL_PROUD / TEXEL:g} proud of the boards, {LENGTHS} lengths each")
    for name, (a, b) in zip(("inner", "outer"), rings):
        print(f"  the {name} ring as drawn: {a:.3f} .. {b:.3f} from the axis")
    print(f"the ladder: parked {PARKED:g} degrees round the axis, origin ({pos[0]:.3f}, {pos[1]:g}, {pos[2]:.3f}), "
          f"yaw {yaw:g}; {height() / TEXEL:g} texels high")
    print(f"  as it rolls round it passes over {inner:.3f} .. {outer:.3f} blocks from the axis (band())")
    print(f"  parked it stands in the columns {sorted(stands)}")
    for m in (ladder, track):
        with tempfile.TemporaryDirectory() as tmp:
            told = m.export(tmp)
        print(f"  {m.name}: {told['elements']} boxes, a sheet of {told['texture']} with {told['rects']} pictures")

    marks = {}
    for cell in room:
        marks[cell] = "w" if cell in wall else "x" if cell in hole else "."
    for cell in D.observing_floor() - hole:
        marks[cell] = "o"
    for cell in doors:
        marks[cell] = "d"
    marks[out] = "e"
    for k in range(720):
        a = math.radians(k / 2.0)
        for r in RAILS:
            cell = (int(math.floor(AXIS[0] + r * math.cos(a))), int(math.floor(AXIS[1] + r * math.sin(a))))
            if marks.get(cell) in (".", "o"):
                marks[cell] = "=" if marks[cell] == "." else "0"
    for cell in stands:
        marks[cell] = "L"
    xs, zs = [c[0] for c in room], [c[1] for c in room]
    print("\nplan (north up; w lining, x the pier's opening and its curb, e the stair's exit, d a doorway, "
          "o the observing floor, = a ring passes, 0 a ring on the observing floor, L the ladder):")
    for z in range(min(zs), max(zs) + 1):
        print("  " + "".join(marks.get((x, z), " ") for x in range(min(xs), max(xs) + 1)))
    print()

    bad = []

    def check(what, wrong):
        wrong = [w for w in wrong] if not isinstance(wrong, bool) else ([what] if wrong else [])
        print(("ok    " if not wrong else "FAIL  ") + what)
        for w in wrong[:6]:
            print("        " + str(w))
        if wrong:
            bad.append(what)

    c = Canvas()
    n = place(c)
    check(f"place() returns the display entities it adds: {n}, not over {MOST}",
          n != len(c.entities) or n > MOST)
    names = [nbt["item"]["components"]["minecraft:item_model"].split(":", 1)[1] for _x, _y, _z, nbt in c.entities]
    check("every model's name begins with int_domeroom_chair or int_domeroom_rail, and every one shown is in models()",
          [name for name in list(got) + names
           if name not in got or not name.startswith((PREFIX + "chair", PREFIX + "rail"))])
    check(f"the rings stand no more than a texel proud of the boards ({RAIL_PROUD / TEXEL:g})",
          RAIL_PROUD > TEXEL + 1e-9 or max(corner[1] for box in _boxes(track) for corner in _corners(box))
          > RAIL_PROUD * 16.0 / RAIL_SCALE + 1e-9)
    check("each ring keeps within a quarter of a texel of its circle",
          [f"ring {i}: {a:.4f} .. {b:.4f}" for i, (a, b) in enumerate(rings)
           if a < RAILS[i] - RAIL_WIDE / 2.0 - TEXEL / 4.0 or b > RAILS[i] + RAIL_WIDE / 2.0 + TEXEL / 4.0])
    on_boards = [(r, k / 2.0) for r, (a, b) in zip(RAILS, rings) for k in range(720) for edge in (a, b)
                 if (int(math.floor(AXIS[0] + edge * math.cos(math.radians(k / 2.0)))),
                     int(math.floor(AXIS[1] + edge * math.sin(math.radians(k / 2.0))))) not in floor]
    check("both rings lie on the boards all the way round: clear of the pier's opening, its curb and the lining",
          [f"the ring at {r} leaves the boards {deg:g} degrees round" for r, deg in on_boards])
    curb = max(_to_cell(cell, far=True) for cell in hole)
    lining = min(_to_cell(cell) for cell in wall)
    check(f"the rolling ladder clears the curb's corners ({curb:.3f}) and the lining ({lining:.3f}) by {CLEAR / TEXEL:g} texels: "
          f"it passes over {inner:.3f} .. {outer:.3f}", inner < curb + CLEAR or outer > lining - CLEAR)
    wheels = []
    for ring in range(len(RAILS)):
        for x in (-WHEEL_AT, WHEEL_AT):
            off = math.hypot(x, sum(RAILS) / 2.0 / TEXEL - _over(ring, WHEEL_AT)) * TEXEL - RAILS[ring]
            if abs(off) > (RAIL_WIDE - WHEEL_WIDE * TEXEL) / 2.0 + 1e-9:
                wheels.append(f"a wheel of ring {ring} stands {off / TEXEL:.2f} texels off its middle line")
    low = min(corner[1] for box in _boxes(ladder) for corner in _corners(box))
    if abs(low - RAIL_PROUD / TEXEL) > 1e-6:
        wheels.append(f"the ladder's lowest point is {low:g} texels above the boards, the rings' top is {RAIL_PROUD / TEXEL:g}")
    check("the four wheels stand on the rings, and nothing of the ladder is lower than they are", wheels)
    kept = {"the observing floor": D.observing_floor(), "the pier's opening and its curb": hole, "the lining": wall,
            "the stair's exit and the cells round it": {(out[0] + dx, out[1] + dz) for dx, dz in O.SQUARE},
            "a doorway or a cell round it": {(x + dx, z + dz) for x, z in doors for dx, dz in O.SQUARE}}
    check("the parked ladder stands on the boards only: off the observing floor, the stair's exit and the doorways",
          [f"{sorted(stands & cells)} in {what}" for what, cells in kept.items() if stands & cells]
          + [f"{sorted(stands - room)} outside the room" for _ in (0,) if stands - room])
    ground = floor | doors

    def walk(blocked):
        reached, edge = set(), [step]
        while edge:
            cell = edge.pop()
            if cell in reached or cell in blocked or cell not in ground:
                continue
            reached.add(cell)
            edge.extend(O.step(cell, d) for d in O.SIDES)
        return reached

    check("the parked ladder cuts nothing off: every cell walked to from the stair's exit without it is walked to round it",
          sorted(walk(set()) - walk(stands) - stands))
    near = nearest(crossing)
    check(f"wherever it stands the ladder keeps {near:.3f} from the crossing of the telescope's axes: out of the reach of "
          f"the tube's lower end ({reach:.3f} with {TAIL_SPARE:g} to spare), and its top is {crossing - height():.3f} "
          f"below the crossing", near < reach or height() >= crossing)

    for kind, a, b in _in_the_way(inner, outer):
        print(f"note  in the band as the room stands now, for the room to move: {kind} at {a:.2f} .. {b:.2f} from the axis")
    print(f"\n{len(bad)} of the checks fail" if bad else "\nall checks pass")
    return len(bad)


if __name__ == "__main__":
    raise SystemExit(1 if report() else 0)
