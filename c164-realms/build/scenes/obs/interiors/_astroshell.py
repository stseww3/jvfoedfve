"""A part of interiors/astroroom: the inside of the small dome's shell (card
plan/packages/interiors/astroroom.md: "the part of the dome's inner shell one sees: iron ribs, the
hand crank that turns it and the toothed ring; one make with the great dome room's"; the room is
c336's, this file c328's, 11-16).

From the head of the wall up (y 20) the dome is a thing that turns. This is what it turns on and
what holds its plates:

  the ring      the dome's foot: a plate girder bent round the room (a web twelve pixels high, an
                angle along its top and one along its bottom, a stiffener at every joint), carried
                by eight rollers that stand on the head of the wall, one on each axis and each
                diagonal: where main/smalldome has the axle boxes in the skirt outside. A flat rail
                lies under the rollers. Inside the girder's foot the rack: a toothed ring
  the crank     on the wall south of the door, where the hand finds it coming in: a cast case with
                a crank and its wooden grip, an upright shaft to the head of the wall, and on it
                the pinion that stands in the rack. It stands still: nobody turns the dome tonight
  the arches    two T-irons beside the slit, from the ring over the crown to the ring on the far
                side: the slit is cut between them
  the ribs      T-irons on the other two axes and on the four diagonals, from the ring up to the
                arch they meet, all with one curve
  the ties      a ring of flat bar from rib to rib where the plates take their first step, cut at
                the arches where the slit is; a bar across between the arches at the crown and one
                east of it

Above the ring nothing is measured by hand: the two curves are found under the plates as
main/smalldome lays them, in interiors/_domeframe's own way (a line that bends one way only and
passes under every corner of the stepped plates), so the frame follows the dome when its courses
change. The sections are a size down from the great dome's lattice girders, as the dome is: plain
T-irons, the same iron in the same tones.

The ring is as wide as the room lets it be: the corbel's ring of blocks comes in to 2.9 from the
axis at eight corners, and the girder passes inside them. The arches stand far enough from the
slit to let the astrograph's tube by (its cell is 0.66 from the tube's axis).

Fourteen display entities (this file's share of the room's budget is 35). Nothing gives light and
no block is laid: the head of the pier in the floor is the room's own. All is shown in the
astrograph's light (machines/astro.BRIGHTNESS), one room and one iron.

    place(canvas, origin=(0, 0, 0)) -> the display entities placed
    models() -> {name: Model}
    check() -> the findings, as lines (none is good)

Where (scene coordinates): from y 20 up, inside the corbel's ring; and the crank, on the north
face (z 32.0) of the wall's south-west corner block: x 10.3..10.8, from y 18.9 up to the ring,
no more than 0.6 out of that face.

    python -m scenes.obs.interiors._astroshell          # the numbers and the self-check
    python -m scenes.obs.interiors._astroshell check    # the self-check alone (exit code 1 on a finding)
"""
import functools
import math
import sys

from artkit import models as M

from ..common import palette as P
from ..main import smalldome as SD
from ..props import _kit as K
from . import _domeframe as F

try:
    from ..machines import astro
except ImportError:                     # the astrograph is not in the tree: nothing to keep clear of
    astro = None
try:
    from ..machines.meridian import IRON_TOOTH
except ImportError:
    IRON_TOOTH = P.mat("iron_dark", bevel=0)

PREFIX = "int_astroroom_shell_"
BUDGET = 35                             # display entities (cr4: 120 for the room, 35 of them the shell's)
BRIGHTNESS = astro.BRIGHTNESS if astro is not None else (10, 7)
SCALE, UNIT, TEXEL = F.SCALE, F.UNIT, F.TEXEL

CAST = P.mat("iron_dark")               # castings: the rollers, the crank's case
STEEL = P.mat("iron", base=5)           # bright shafts
WOOD = P.mat("dark_wood")               # the crank's grip

AX, AZ = SD.CX + 0.5, SD.CZ + 0.5       # (12.5, 30.5): the dome's upright axis
LEDGE = float(SD.HEAD_Y)                # 20.0: the head of the wall, where the rollers stand

# ---- the ring (blocks) ------------------------------------------------------------------------------
RING_R = 2.78125                        # the middle of the girder's web, from the axis
WEB = TEXEL
RING_ROWS = (LEDGE + 0.4375, LEDGE + 1.1875)    # the girder's underside and its top
LEG = 0.125                             # how far the two angles stand in from the web
FLATS = 24                              # flats to the whole ring: fifteen degrees each
RAIL = (0.125, TEXEL)                   # the rail on the head of the wall: wide, high
WHEEL = (0.15625, 0.125)                # a roller: radius, width
ROLLERS = 8                             # one on each axis and each diagonal
RACK = (0.125, 0.125)                   # the rack inside the girder's foot: radial, upright; its teeth look inwards
RACK_R = RING_R - WEB / 2.0 - LEG - RACK[0] / 2.0       # 2.5625: its middle

# ---- the crank (blocks) -----------------------------------------------------------------------------
PINION_R = 0.085
MESH = 0.015                            # between the pinion and the rack's teeth
CRANK_Y = LEDGE - 0.8125                # 19.1875: the crank's axle, 1.19 over the floor, where a hand turns it
SHAFT_OUT = 0.09375                     # the upright shaft, out of the wall's face
CASE_OUT = 0.25                         # the case's front, out of the wall's face
ARM, ARM_ANGLE = 0.1875, 35.0           # the crank's arm, and how far it leans from upright
GRIP = 0.1875                           # the wooden grip's length
CRANK_REACH = 0.6                       # nothing of the crank is further out of the wall than this

# ---- the frame (blocks) -----------------------------------------------------------------------------
SIDE = 0.875                            # the arches' planes, from the axis: clear of the astrograph's tube
RIBS = (45.0, 90.0, 135.0, 225.0, 270.0, 315.0)         # degrees round the axis: 0 east, 90 south
FLANGE, STEM = (0.125, TEXEL), (TEXEL, 0.125)           # a rib's T-iron: (across, deep) of flange and stem
ARCH_FLANGE, ARCH_STEM = (0.1875, TEXEL), (TEXEL, 0.1875)
TIE = (TEXEL, 0.125)                    # the flat bar of the ties: level, upright
STEP = 0.25                             # a curve is drawn in bars of about this length
PURLIN_R = 2.0                          # where the ring of ties crosses the ribs, from the axis
TIES_Y = 24.0                           # the height of the ties' origin
CLEAR = 0.05                            # what the astrograph keeps from every bar


# ---- the lines under the plates ------------------------------------------------------------------------
def ceiling():
    """{column: the height of the underside of the plates over it} for every column inside the
    corbel's ring, None under the open slit: main/smalldome's own rule for the shell's thickness."""
    skin = {col: top for col, top in SD._skin().items() if not SD._in_slit(*col)}
    return {col: None if SD._in_slit(*col) else float(min(math.ceil(skin[col]) - 1, SD._foot(skin, col)))
            for col in SD.BODY}


def _round_axis(col):
    """How near a column comes to the dome's axis."""
    dx = max(col[0] - AX, AX - (col[0] + 1), 0.0)
    dz = max(col[1] - AZ, AZ - (col[1] + 1), 0.0)
    return math.hypot(dx, dz)


def _along(col):
    """How near a column under an arch comes to the axis, counted along the slit; None for a
    column no arch runs under (the arches run in the rows either side of the slit's)."""
    if abs(col[1] - SD.CZ) != 1:
        return None
    return max(col[0] - AX, AX - (col[0] + 1), 0.0)


# ---- pieces ----------------------------------------------------------------------------------------------
def _tee(piece, curve, s0, s1, flange, stem, seed):
    """A T-iron along the curve from length s0 to s1, its flange's back on the curve, its stem into
    the room; returns the line of its underside."""
    n = max(1, int(round((s1 - s0) / STEP)))
    marks = [s0 + (s1 - s0) * i / n for i in range(n + 1)]
    piece.chain([curve.at(s, flange[1] / 2.0) for s in marks], flange, F.CHORD, seed=seed)
    piece.chain([curve.at(s, flange[1] + stem[1] / 2.0) for s in marks], stem, F.BAR, seed=seed + 1)
    return [curve.at(s, flange[1] + stem[1]) for s in marks]


def _shoe(piece, curve, wide):
    """The plate a T-iron's foot stands on, on the girder's top angle."""
    z, y = curve.p[0]
    piece.box((z - LEG, y), (z + WEB / 2.0, y + 1.5 * TEXEL), -wide / 2.0 - TEXEL / 2.0, wide / 2.0 + TEXEL / 2.0,
              F.PLATE, seed=41)


def _rib(name, curve, end, arch_top):
    """A rib from the ring up to `end` from the axis, where it meets an arch whose back is at
    `arch_top` there: the plate on its end goes up to the arch."""
    last = curve.where(end)
    piece = F.Piece(name, curve.at(last * 0.5, 0.4))
    piece.soffit = _tee(piece, curve, 0.0, last, FLANGE, STEM, 11)
    (z, y), low = curve.at(last, 0.0), curve.at(last, FLANGE[1] + STEM[1])
    piece.bar(low, (z, max(y, arch_top)), (FLANGE[0], TEXEL), F.PLATE, seed=15)
    _shoe(piece, curve, FLANGE[0])
    return piece


def _arch(name, curve):
    """Half an arch, from the ring to the crown."""
    last = curve.length
    piece = F.Piece(name, curve.at(last * 0.5, 0.4))
    piece.soffit = _tee(piece, curve, 0.0, last, ARCH_FLANGE, ARCH_STEM, 21)
    _shoe(piece, curve, ARCH_FLANGE[0])
    return piece


def _ties(meridian, arch):
    """The ties, one model with its origin on the dome's axis at TIES_Y and its axes the world's:
    the ring of flat bar from rib to rib, cut where the slit is and hung from the arches at its
    four ends, and the bars across between the arches. Returns (model, the bars as lines)."""
    m = M.Model(PREFIX + "ties", px=SCALE)
    u, lines = UNIT, []

    def bar(a, b):
        m.beam(tuple(v * u for v in a), tuple(v * u for v in b), TIE[0] * u, TIE[1] * u, F.BAR, seed=91)
        lines.append(((AX + a[0], TIES_Y + a[1], AZ + a[2]), (AX + b[0], TIES_Y + b[1], AZ + b[2]), TIE[1] / 2.0))

    def post(x, z, y0, y1):
        h = TEXEL / 2.0
        m.box(((x - h) * u, y0 * u, (z - h) * u), ((x + h) * u, y1 * u, (z + h) * u), F.BAR, seed=92)
        lines.append(((AX + x, TIES_Y + y0, AZ + z), (AX + x, TIES_Y + y1, AZ + z), h))

    y = meridian.at(meridian.where(PURLIN_R))[1] - FLANGE[1] - TIE[1] / 2.0 - TIES_Y
    gap = math.degrees(math.asin(SIDE / PURLIN_R))          # where an arch crosses the ring of ties
    south = [gap, 45.0, 90.0, 135.0, 180.0 - gap]
    for chain in (south, [360.0 - a for a in south]):
        nodes = [(PURLIN_R * math.cos(math.radians(a)), y, PURLIN_R * math.sin(math.radians(a))) for a in chain]
        for a, b in zip(nodes, nodes[1:]):
            bar(a, b)
    x = PURLIN_R * math.cos(math.radians(gap))
    bar((x, y, -SIDE), (x, y, SIDE))
    hang = arch.at(arch.where(x), ARCH_FLANGE[1] + ARCH_STEM[1])[1] - TIES_Y
    for sx in (-x, x):
        for sz in (-SIDE, SIDE):
            post(sx, sz, min(y, hang), max(y, hang))
    for along in (0.0, 1.0):
        yy = arch.at(arch.where(along), ARCH_FLANGE[1])[1] - TIE[1] / 2.0 - TIES_Y
        bar((along, yy, -SIDE), (along, yy, SIDE))
    return m, lines


def _ring():
    """Half the ring, from its east end round by the north to its west end; it is shown twice, the
    second time turned half round. The rail, the girder, the rack, and four rollers, the first on
    the east axis. The model's origin is on the dome's axis, at the head of the wall."""
    m = M.Model(PREFIX + "ring", px=SCALE)
    u, t = UNIT, TEXEL * UNIT
    y0, y1 = (RING_ROWS[0] - LEDGE) * u, (RING_ROWS[1] - LEDGE) * u
    step = 360.0 / FLATS

    def hoop(radius, thick, lo, hi, mat, seed):
        m.ring("y", (0.0, (lo + hi) / 2.0, 0.0), radius * u, thick * u, hi - lo, mat, sides=FLATS, arc=(0.0, 180.0),
               seed=seed)

    legs = RING_R - WEB / 2.0 - LEG / 2.0
    hoop(RING_R, RAIL[0], 0.0, RAIL[1] * u, F.BAR, 71)
    hoop(RING_R, WEB, y0, y1, F.PLATE, 72)
    hoop(legs, LEG, y1 - t, y1, F.CHORD, 73)
    hoop(legs, LEG, y0, y0 + t, F.CHORD, 73)
    hoop(RACK_R, RACK[0], y0, y0 + RACK[1] * u, IRON_TOOTH, 74)
    inner = (RING_R - WEB / 2.0) * u                    # the web's inner face, in the middle of a flat
    for k in range(FLATS // 2):
        with m.turned(("y", k * step)):                 # a joint between two flats: the stiffener
            m.box((inner - LEG * u, y0 + t, -t / 2.0), (inner + 0.03 * u, y1 - t, t / 2.0), F.BAR, seed=75)
        with m.turned(("y", (k + 0.5) * step)):         # a flat: two rivets under the top angle, two over the bottom one
            for z in (-0.18 * u, 0.18 * u):
                for y in (y0 + 2.5 * t, y1 - 2.5 * t):
                    m.box((inner - t / 2.0, y - t / 2.0, z - t / 2.0), (inner, y + t / 2.0, z + t / 2.0), F.RIVET,
                          seed=99)
    radius, wide = WHEEL
    axle = (RAIL[1] + radius) * u                       # the rollers' axles, over the head of the wall
    fork = y0 - 0.05 * u                                # the underside of a roller's saddle
    r = RING_R * u
    for k in range(0, FLATS // 2, FLATS // ROLLERS):
        with m.turned(("y", k * step)):
            m.tube("x", (axle, 0.0), r - wide / 2.0 * u, r + wide / 2.0 * u, radius * u, CAST, sides=8, seed=76)
            m.tube("x", (axle, 0.0), r - 0.17 * u, r + 0.17 * u, 0.035 * u, STEEL, sides=4, seed=77)
            m.box((r - 0.14 * u, fork, -0.08 * u), (r + 0.14 * u, y0, 0.08 * u), CAST, seed=78)
            for side in (-1.0, 1.0):
                x = r + side * 0.105 * u
                m.box((x - t / 2.0, axle - 0.06 * u, -0.06 * u), (x + t / 2.0, fork, 0.06 * u), CAST, seed=79)
    return m


def crank_at():
    """The point of the wall the crank's case is bolted to, at the height of the crank's axle: on
    the north face of the wall's south-west corner block, where the upright shaft before that face
    stands under the rack."""
    face = SD.CZ + 2.0
    r = pinion_radius()
    dz = face - SHAFT_OUT - AZ
    return (AX - math.sqrt(r * r - dz * dz), CRANK_Y, face)


def pinion_radius():
    """How far the pinion's axis stands from the dome's: the pinion inside the rack, its teeth in the rack's."""
    return RACK_R - RACK[0] / 2.0 - PINION_R - MESH


def _crank():
    """The crank. The model's origin is crank_at(); its z points out of the wall, its x along the
    wall (shown turned half round: to the room's west), y up."""
    m = M.Model(PREFIX + "crank", px=SCALE)
    u, t = UNIT, TEXEL * UNIT
    foot = RING_ROWS[0] - CRANK_Y                       # the ring's underside over the crank's axle
    head = LEDGE - CRANK_Y                              # the head of the wall
    # the plate on the wall, its four bolts, the case of the bevel wheels
    m.box((-0.1875 * u, -0.25 * u, 0.0), (0.1875 * u, 0.25 * u, t), F.PLATE, seed=81)
    for x in (-0.125 * u, 0.125 * u):
        for y in (-0.1875 * u, 0.1875 * u):
            m.box((x - t / 2.0, y - t / 2.0, t), (x + t / 2.0, y + t / 2.0, 1.5 * t), F.RIVET, seed=99)
    m.box((-0.125 * u, -0.125 * u, t), (0.125 * u, 0.15625 * u, CASE_OUT * u), CAST, seed=82)
    # the crank's axle out of the case's front, its boss, the arm and the grip
    z0 = CASE_OUT * u
    m.tube("z", (0.0, 0.0), z0, z0 + 2.0 * t, 0.035 * u, STEEL, sides=8, seed=83)
    m.tube("z", (0.0, 0.0), z0 + t, z0 + 2.0 * t, 0.0625 * u, CAST, sides=8, seed=84)
    with m.turned(("z", ARM_ANGLE)):
        m.box((-t / 2.0, 0.0, z0 + t), (t / 2.0, ARM * u, z0 + 2.0 * t), CAST, seed=85)
        m.tube("z", (0.0, ARM * u), z0 + 2.0 * t, z0 + 2.0 * t + GRIP * u, 0.04 * u, WOOD, sides=8, seed=86)
    # the upright shaft, its bearing under the head of the wall, the pinion in the rack
    c = (0.0, SHAFT_OUT * u)
    m.tube("y", c, 0.15625 * u, (foot + RACK[1] + 0.03) * u, 0.03125 * u, STEEL, sides=8, seed=87)
    m.box((-0.075 * u, (head - 0.1875) * u, 0.0), (0.075 * u, (head - 0.0625) * u, (SHAFT_OUT + 0.0625) * u), F.PLATE,
          seed=88)
    m.tube("y", c, (foot - 0.06) * u, (foot - 0.02) * u, 0.055 * u, STEEL, sides=8, seed=89)
    m.ring("y", (0.0, (foot + RACK[1] / 2.0) * u, SHAFT_OUT * u), (PINION_R - 0.02) * u, 0.04 * u, (RACK[1] + 0.03) * u,
           IRON_TOOTH, sides=8, seed=90)
    return m


# ---- the frame ---------------------------------------------------------------------------------------------
class _Frame:
    """The lines, the pieces and where they go: meridian, arch_line (interiors/_domeframe.Curve),
    pieces {name: Piece}, placed [(name, position, yaw)], ties (a model), tie_lines."""


@functools.lru_cache(maxsize=None)
def frame():
    f = _Frame()
    ceil, top = ceiling(), RING_ROWS[1]
    f.meridian = F.under(ceil, _round_axis, RING_R, top)
    f.arch_line = F.under(ceil, _along, math.sqrt(RING_R ** 2 - SIDE ** 2), top)
    f.pieces, f.placed = {}, []
    name = PREFIX + "arch"
    f.pieces[name] = _arch(name, f.arch_line)
    z, y = f.pieces[name].anchor
    for side in (-SIDE, SIDE):
        f.placed.append((name, (AX + z, y, AZ + side), -90.0))
        f.placed.append((name, (AX - z, y, AZ + side), 90.0))
    edge = SIDE + ARCH_FLANGE[0] / 2.0                  # the arches' outer edges, from the axis
    for deg in RIBS:
        a = math.radians(deg)
        end = edge / abs(math.sin(a))
        name = PREFIX + f"rib_{int(round(end * 100)):03d}"
        if name not in f.pieces:
            where = f.arch_line.where(end * abs(math.cos(a)))
            f.pieces[name] = _rib(name, f.meridian, end, f.arch_line.at(where)[1])
        z, y = f.pieces[name].anchor
        f.placed.append((name, (AX + z * math.cos(a), y, AZ + z * math.sin(a)), deg - 90.0))
    f.ties, f.tie_lines = _ties(f.meridian, f.arch_line)
    return f


@functools.lru_cache(maxsize=None)
def _models():
    f = frame()
    out = {name: piece.m for name, piece in f.pieces.items()}
    out.update({m.name: m for m in (_ring(), f.ties, _crank())})
    return out


def models():
    return dict(_models())


def placed():
    """[(model name, position, yaw)] of every display entity, in scene coordinates."""
    ring = PREFIX + "ring"
    return ([(ring, (AX, LEDGE, AZ), 0.0), (ring, (AX, LEDGE, AZ), 180.0)] + list(frame().placed)
            + [(PREFIX + "ties", (AX, TIES_Y, AZ), 0.0), (PREFIX + "crank", crank_at(), 180.0)])


def place(canvas, origin=(0, 0, 0), brightness=BRIGHTNESS):
    """Hang the shell's iron in the dome; returns the number of display entities."""
    built = _models()
    return sum(K.put(canvas, built[name], pos, yaw=yaw, scale=SCALE, origin=origin, brightness=brightness)
               for name, pos, yaw in placed())


def lines():
    """Every bar of the ribs, the arches and the ties in scene coordinates: (a, b, half thickness)."""
    f = frame()
    out = list(f.tie_lines)
    for name, (x, y, z), yaw in f.placed:
        piece = f.pieces[name]
        fz, fy = piece.anchor
        r = math.radians(yaw)
        (zx, zz), (xx, xz) = (-math.sin(r), math.cos(r)), (math.cos(r), math.sin(r))
        for a, b, half in piece.lines:
            out.append(tuple((x + p[0] * xx + (p[1] - fz) * zx, y + p[2] - fy, z + p[0] * xz + (p[1] - fz) * zz)
                             for p in (a, b)) + (half,))
    return out


def crank_box():
    """The box the crank fills, in scene coordinates: (x0, y0, z0), (x1, y1, z1)."""
    x, y, z = crank_at()
    return (x - 0.25, y - 0.25, z - CRANK_REACH), (x + 0.25, RING_ROWS[0] + RACK[1] + 0.03, z)


# ---- self-check ----------------------------------------------------------------------------------------------
def _astro_points(low, turn=0.0):
    """Points all over the astrograph's boxes that stand higher than `low`, a fifth of a block apart;
    with `turn`, of the instrument that many degrees along its tracking."""
    out = []
    built = astro._built()
    for name, at, axes, scale in (astro.placed(turn) if turn else astro.placed()):
        m, k = built[name], scale / 16.0
        for part in m.parts:
            c = [(part["lo"][j] + part["hi"][j]) / 2.0 for j in range(3)]
            h = [(part["hi"][j] - part["lo"][j]) / 2.0 for j in range(3)]
            q = part["rot"][0] if part["rot"] else M.IDENT
            n = [max(1, int(math.ceil(2.0 * h[j] * k / 0.2))) for j in range(3)]
            for i0 in range(n[0] + 1):
                for i1 in range(n[1] + 1):
                    for i2 in range(n[2] + 1):
                        v = M._qrot(q, ((2.0 * i0 / n[0] - 1.0) * h[0], (2.0 * i1 / n[1] - 1.0) * h[1],
                                        (2.0 * i2 / n[2] - 1.0) * h[2]))
                        p = list(at)
                        for j in range(3):
                            off = (c[j] + v[j] - m.anchor[j]) * k
                            for i in range(3):
                                p[i] += axes[j][i] * off
                        if p[1] > low:
                            out.append(tuple(p))
    return out


def _gap(p, a, b):
    """From point p to the stretch a-b."""
    d = [b[i] - a[i] for i in range(3)]
    span = sum(v * v for v in d)
    k = 0.0 if span < 1e-12 else max(0.0, min(1.0, sum((p[i] - a[i]) * d[i] for i in range(3)) / span))
    return math.dist(p, [a[i] + d[i] * k for i in range(3)])


def check():
    """What can be told without a picture; returns the findings as lines (none is good)."""
    out = []
    # 1. the budget, and every model within what a display entity can show
    if len(placed()) > BUDGET:
        out.append(f"{len(placed())} display entities, the budget is {BUDGET}")
    for name, m in _models().items():
        if not name.startswith(PREFIX):
            out.append(f"{name}: not named {PREFIX}...")
        try:
            m.shift()
        except ValueError as e:
            out.append(str(e))
    # 2. the ring passes inside the corbel's blocks, every roller stands on the head of the wall
    #    and its axle ends before the blocks behind it
    near = min(_round_axis(col) for col in SD.RING)
    corner = (RING_R + WEB / 2.0) / math.cos(math.pi / FLATS)
    if corner > near - 0.03:
        out.append(f"ring: its corners are {corner:.3f} from the axis, the corbel's blocks come in to {near:.3f}")
    for k in range(ROLLERS):
        a = math.radians(360.0 * k / ROLLERS)
        for what, r, where in (("stands", RING_R, SD.WALL), ("ends", RING_R + 0.17, SD.BODY)):
            col = (int(math.floor(AX + r * math.cos(a))), int(math.floor(AZ + r * math.sin(a))))
            if col not in where:
                out.append(f"roller {k}: it {what} over column {col}, not inside the corbel's ring")
    # 3. every bar of the frame stays inside the corbel's ring, out of the slit and under the plates
    ceil = ceiling()
    for a, b, half in lines():
        n = max(1, int(math.ceil(math.dist(a, b) / 0.05)))
        for i in range(n + 1):
            p = [a[j] + (b[j] - a[j]) * i / n for j in range(3)]
            col = (int(math.floor(p[0])), int(math.floor(p[2])))
            if col not in ceil or ceil[col] is None:
                out.append(f"frame: a bar at ({p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f}) is "
                           f"{'in the slit' if col in ceil else 'outside the room'}")
                break
            if p[1] + half > ceil[col] + 1e-6:
                out.append(f"frame: a bar at ({p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f}) reaches {p[1] + half:.3f}, "
                           f"the plates over {col} start at {ceil[col]:g}")
                break
    # 4. the crank: on the corner block's face, the floor before it free, the pinion in the rack
    x, y, z = crank_at()
    block, before = (int(math.floor(x)), SD.CZ + 2), (int(math.floor(x)), SD.CZ + 1)
    if block not in SD.WALL or before not in SD.ROOM:
        out.append(f"crank: at x {x:.2f} the block behind it is {block}, the cell before it {before}")
    if abs(math.hypot(x - AX, z - SHAFT_OUT - AZ) + PINION_R + MESH - (RACK_R - RACK[0] / 2.0)) > 1e-6:
        out.append("crank: the pinion does not stand in the rack")
    if CASE_OUT + 2.0 * TEXEL + GRIP > CRANK_REACH:
        out.append(f"crank: the grip ends {CASE_OUT + 2.0 * TEXEL + GRIP:g} out of the wall, more than {CRANK_REACH:g}")
    # 5. the astrograph keeps clear of all of it, as it stands and at either end of its tracking
    if astro is not None:
        (bx0, by0, bz0), (bx1, by1, bz1) = crank_box()
        bars = lines()
        hits = set()
        track = float(getattr(astro, "TRACK", 0.0))
        for turn in ((0.0, -track, track) if track else (0.0,)):
            when = f", turned {turn:g} degrees" if turn else ""
            for p in _astro_points(by0 - CLEAR, turn):
                # the ring with its rollers fills a band from the head of the wall to the girder's top;
                # every bar of the frame stands on the girder
                if (LEDGE - CLEAR < p[1] < RING_ROWS[1] + CLEAR
                        and math.hypot(p[0] - AX, p[2] - AZ) > RACK_R - RACK[0] / 2.0 - CLEAR):
                    hits.add("the ring" + when)
                if p[1] > RING_ROWS[1] - CLEAR and any(_gap(p, a, b) < half + CLEAR for a, b, half in bars):
                    hits.add("a bar of the frame" + when)
                if bx0 - CLEAR < p[0] < bx1 + CLEAR and p[1] < by1 + CLEAR and bz0 - CLEAR < p[2] < bz1 + CLEAR:
                    hits.add("the crank" + when)
        out += [f"astrograph: it comes within {CLEAR:g} of {what}" for what in sorted(hits)]
    return out


def report():
    f = frame()
    x, y, z = crank_at()
    rows = [
        f"ring: web {RING_R:g} from the axis ({AX:g}, {AZ:g}), y {RING_ROWS[0]:g}..{RING_ROWS[1]:g}; "
        f"the corbel's blocks come in to {min(_round_axis(col) for col in SD.RING):.3f}",
        f"rack: {RACK_R - RACK[0] / 2.0:g}..{RACK_R + RACK[0] / 2.0:g} from the axis; pinion {pinion_radius():.3f} from the axis",
        f"crank: bolted on at ({x:.3f}, {y:g}, {z:g}), box {crank_box()}",
        "meridian: " + " ".join(f"({d:.2f}, {h:.2f})" for d, h in f.meridian.p[::4] + f.meridian.p[-1:]),
        "arch:     " + " ".join(f"({d:.2f}, {h:.2f})" for d, h in f.arch_line.p[::4] + f.arch_line.p[-1:]),
        f"{len(placed())} display entities",
    ]
    for name, m in sorted(_models().items()):
        lo, hi = m.reach()
        rows.append(f"  {name}: {len(m.parts)} boxes, " + " x ".join(f"{(hi[i] - lo[i]) / UNIT:.2f}" for i in range(3))
                    + " blocks")
    for name, pos, yaw in placed():
        rows.append(f"  {name[len(PREFIX):]:8s} at ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}), yaw {yaw:g}")
    return rows


if __name__ == "__main__":
    found = check()
    if len(sys.argv) < 2 or sys.argv[1] != "check":
        print("\n".join(report()))
    print("\n".join(found) if found else "self-check: the budget, the ring inside the corbel, the frame under the "
          "plates, the crank at the rack, the astrograph clear -- all good")
    sys.exit(1 if found else 0)
