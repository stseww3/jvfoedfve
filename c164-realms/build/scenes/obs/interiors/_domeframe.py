"""The iron skeleton of the great dome, as display models (a helper of interiors/domeroom; the
auto-discovery skips modules that start with "_").

What turns with the dome and carries its boards and plates, from the ring girder up:

    two arch girders   lattice girders in the two upright planes beside the slit, from the ring
                       girder over the crown to the ring girder on the far side: the slit is cut
                       between them, and the leaves of the slit run on them
    the ribs           lattice ribs on the dome's seams, each from the ring girder up to the arch
                       girder it meets; they all have the one curve of the dome's meridian

Nothing here is measured by hand: the frame is drawn under the ceiling it is given (the underside
of the boards over every column, read off the canvas by interiors/domeroom), so it follows the dome
when its courses change. A curve that stays under every corner of the stepped boards is found once
for the ribs (round the axis) and once for the arch girders (along their planes).

Frames of reference. A piece is drawn in its own upright plane: z along the plane and away from
the dome's axis, y up, x across; lengths in blocks until they are handed to the model. A rib's
plane goes through the axis; an arch girder is drawn as a half, from the crown to its foot, and
set down four times.
"""
import math

import numpy as np

from artkit import models as M

from ..common import palette as P
from ..props import _kit as K

SCALE = 4                       # blocks to 16 model units: a model reaches 12 blocks, 16 texels to the block
UNIT = 16.0 / SCALE
TEXEL = 0.0625
MARGIN = TEXEL                  # between a chord's back and the lowest corner of the boards
SOLE = 0.125                    # the plate a foot stands on, on the bottom of the ring girder's upper row

# the sections, in blocks: (across the plane, in the plane)
RIB_CHORD = (0.25, 0.125)
RIB_DEPTH = 0.5                 # between the middles of a rib's two chords
RIB_PANEL = 0.75
RIB_LACE = (TEXEL, 0.125)
ARCH_CHORD = (0.3125, 0.1875)
ARCH_DEPTH = 0.875
ARCH_PANEL = 1.0
ARCH_LACE = (TEXEL, 0.125)

CHORD = P.mat("iron", base=4, bevel="along")    # the chord one sees from below
BACK = P.mat("iron", bevel="along")
LACE = P.mat("iron", bevel=0)
PLATE = P.mat("iron")
RIVET = K.RIVET


# --- the curve under the boards -------------------------------------------------------------------
def tips(ceiling, reach):
    """The corners a line has to pass under, from the outside in: [(distance, height)].

    ceiling: {column: the height of the underside over it, None where there is none};
    reach(column): how near the column comes to where the distance is counted from, or None for
    a column that does not count. Every height keeps the nearest column that has it, and a height
    only counts while it reaches further in than all the lower ones."""
    nearest = {}
    for col, y in ceiling.items():
        d = None if y is None else reach(col)
        if d is not None:
            nearest[y] = min(nearest.get(y, d), d)
    out = []
    for y in sorted(nearest):
        if not out or nearest[y] < out[-1][0]:
            out.append((nearest[y], float(y)))
    return out


def concave(points, step=TEXEL / 2.0, most=2.0):
    """The chain through points = [(x, y)], x rising, let down where it has to be so that it bends
    one way only (never upwards) and passes on or under every point; the first point keeps its
    height. Every point may be let down by a whole number of steps; of all the chains that bend
    the right way the one is kept whose gaps, squared, add up to the least: a few small gaps
    rather than one large one."""
    xs = np.array([p[0] for p in points], dtype=float)
    ys = np.array([p[1] for p in points], dtype=float)
    n = len(points)
    if n < 3:
        return list(points)
    drop = np.arange(int(round(most / step)) + 1) * step
    k = len(drop)
    huge = 1e18
    cost = np.full((k, k), huge)            # [how far point i - 1 is let down, how far point i]
    cost[0, :] = drop ** 2
    came = []
    for i in range(1, n - 1):
        before = ((ys[i] - drop)[None, :] - (ys[i - 1] - drop)[:, None]) / (xs[i] - xs[i - 1])
        after = ((ys[i + 1] - drop)[None, :] - (ys[i] - drop)[:, None]) / (xs[i + 1] - xs[i])
        allowed = before[:, :, None] >= after[None, :, :] - 1e-9
        via = np.where(allowed, cost[:, :, None], huge)
        came.append(via.argmin(axis=0))
        cost = via.min(axis=0) + (drop ** 2)[None, :]
    if cost.min() >= huge:
        raise ValueError("no chain that bends one way passes under these corners")
    b, c = np.unravel_index(cost.argmin(), cost.shape)
    drops = [c, b]
    for back in reversed(came):
        b, c = back[b, c], b
        drops.append(b)
    drops.reverse()
    return [(float(x), float(y - drop[d])) for x, y, d in zip(xs, ys, drops)]


def rounded(points, rounds=3):
    """The chain with its corners cut (each round takes every corner off at a quarter of its two
    sides): it stays on the hollow side of the chain and keeps its ends."""
    for _ in range(rounds):
        out = [points[0]]
        for a, b in zip(points, points[1:]):
            out.append((a[0] + (b[0] - a[0]) * 0.25, a[1] + (b[1] - a[1]) * 0.25))
            out.append((a[0] + (b[0] - a[0]) * 0.75, a[1] + (b[1] - a[1]) * 0.75))
        out.append(points[-1])
        points = out
    return points


class Curve:
    """A line in an upright plane, as (z, y) points from its foot at the ring girder inwards and
    up; lengths along it are counted from the foot."""

    def __init__(self, points):
        self.p = [(float(z), float(y)) for z, y in points]
        self.s = [0.0]
        for a, b in zip(self.p, self.p[1:]):
            self.s.append(self.s[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        self.length = self.s[-1]

    def at(self, s, inside=0.0):
        """The point at length s, moved `inside` towards the hollow of the curve."""
        s = min(max(s, 0.0), self.length)
        i = 0
        while i < len(self.s) - 2 and self.s[i + 1] < s:
            i += 1
        a, b = self.p[i], self.p[i + 1]
        span = self.s[i + 1] - self.s[i]
        t = (s - self.s[i]) / span
        tz, ty = (b[0] - a[0]) / span, (b[1] - a[1]) / span
        return (a[0] + (b[0] - a[0]) * t - ty * inside, a[1] + (b[1] - a[1]) * t + tz * inside)

    def where(self, z):
        """The length at which the curve is at distance z from the axis (it only goes inwards)."""
        for i, (a, b) in enumerate(zip(self.p, self.p[1:])):
            if (a[0] - z) * (b[0] - z) <= 0.0 and abs(a[0] - b[0]) > 1e-12:
                return self.s[i] + (self.s[i + 1] - self.s[i]) * (a[0] - z) / (a[0] - b[0])
        return self.length if z <= self.p[-1][0] else 0.0


def under(ceiling, reach, foot):
    """The line of a chord's back: from `foot` (distance, height) inwards, MARGIN under every
    corner of the boards."""
    chain = [(-foot[0], foot[1])] + [(-d, y - MARGIN) for d, y in tips(ceiling, reach) if d < foot[0] - 0.05]
    chain = [p for i, p in enumerate(chain) if i == 0 or p[0] > chain[i - 1][0] + 1e-6]
    return Curve([(-x, y) for x, y in rounded(concave(chain))])


# --- pieces ---------------------------------------------------------------------------------------
class Piece:
    """One model drawn in an upright plane, lengths in blocks: bars from point to point (z, y), with
    x across the plane. `lines` keeps what was drawn, for the checks: (a, b, half thickness)."""

    def __init__(self, name, anchor):
        self.name, self.anchor = name, anchor               # the anchor: (z, y) in the plane
        self.m = M.Model(name, px=SCALE)
        self.lines = []

    def _u(self, x, p):
        return (x * UNIT, (p[1] - self.anchor[1]) * UNIT, (p[0] - self.anchor[0]) * UNIT)

    def bar(self, a, b, section, mat, x=0.0, seed=None):
        across, deep = section
        self.m.beam(self._u(x, a), self._u(x, b), across * UNIT, deep * UNIT, mat, seed=seed)
        self.lines.append((a, b, deep / 2.0))

    def chain(self, points, section, mat, seed=None):
        for a, b in zip(points, points[1:]):
            if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-6:
                self.bar(a, b, section, mat, seed=seed)

    def box(self, lo, hi, across, mat, x=0.0, **kw):
        """A plate square to the frame: from (z, y) to (z, y), `across` wide about x."""
        a = self._u(x - across / 2.0, (min(lo[0], hi[0]), min(lo[1], hi[1])))
        b = self._u(x + across / 2.0, (max(lo[0], hi[0]), max(lo[1], hi[1])))
        self.m.box(a, b, mat, **kw)
        self.lines.append(((lo[0], lo[1]), (hi[0], hi[1]), 0.0))

    def rivet(self, p, x, towards):
        """A rivet head on a face square to the plane's z: one texel, half a texel proud."""
        z0, z1 = sorted((p[0], p[0] + towards * TEXEL / 2.0))
        self.m.box(self._u(x - TEXEL / 2.0, (z0, p[1] - TEXEL / 2.0)), self._u(x + TEXEL / 2.0, (z1, p[1] + TEXEL / 2.0)),
                   RIVET, seed=99)


def _stations(first, step, last):
    out, s = [], first
    while s < last - 1e-9:
        out.append(s)
        s += step
    return out


def _on_sole(curve, inside):
    """The length at which the line `inside` the curve has climbed onto the sole."""
    s = 0.0
    while curve.at(s, inside)[1] < curve.p[0][1] + TEXEL / 2.0 and s < curve.length:
        s += TEXEL / 2.0
    return s


def _shoe(piece, curve, belly, chord, wide):
    """The foot of a rib or of an arch girder on the ring girder: a plate against the girder's
    face with its rivets, and the sole both chords stand on."""
    z0, y0 = curve.p[0]
    base = y0 - SOLE
    piece.box((z0, base), (z0 + TEXEL, base + 0.875), wide, PLATE, seed=41)
    inner = curve.at(_on_sole(curve, belly), belly)[0] - chord[1]
    piece.box((inner, base), (z0, y0), wide, PLATE, seed=42)
    for x in (-wide / 2.0 + TEXEL * 1.5, wide / 2.0 - TEXEL * 1.5):
        for y in (0.3125, 0.6875):
            piece.rivet((z0, base + y), x, -1.0)


def rib(name, curve, end):
    """A lattice rib from the ring girder up to distance `end` from the axis, where it meets an
    arch girder: two chords, a zigzag of flat bars between them, a post where it ends."""
    across, deep = RIB_CHORD
    back, belly = deep / 2.0, deep / 2.0 + RIB_DEPTH
    last = curve.where(end)
    piece = Piece(name, curve.at(last * 0.55, belly + 0.4))
    tops = _stations(0.375, RIB_PANEL, last - 0.3)
    start = _on_sole(curve, belly)
    lows = [s + RIB_PANEL / 2.0 for s in tops if s + RIB_PANEL / 2.0 < last - 0.15]
    piece.chain([curve.at(s, back) for s in [0.0] + tops + [last]], RIB_CHORD, BACK, seed=11)
    piece.chain([curve.at(s, belly) for s in [start] + [s for s in lows if s > start + 0.1] + [last]],
                RIB_CHORD, CHORD, seed=12)
    for i, s in enumerate(tops):
        for low in (s - RIB_PANEL / 2.0, s + RIB_PANEL / 2.0):
            if start < low < last - 0.15:
                piece.bar(curve.at(s, back), curve.at(low, belly), RIB_LACE, LACE, seed=13 + i % 2)
    piece.bar(curve.at(last, 0.0), curve.at(last, belly + deep / 2.0), (across, 0.125), PLATE, seed=15)
    _shoe(piece, curve, belly, RIB_CHORD, 0.5)
    return piece


def arch(name, curve, posts):
    """Half an arch girder, from its foot on the ring girder to the crown: two chords, a lattice
    of crossing flat bars between them, an upright plate at the crown and wherever a rib comes in
    (posts: distances from the crown)."""
    across, deep = ARCH_CHORD
    back, belly = deep / 2.0, deep / 2.0 + ARCH_DEPTH
    last = curve.length
    piece = Piece(name, curve.at(last * 0.5, belly + 0.5))
    count = max(1, int(round((last - 0.5) / ARCH_PANEL)))
    step = (last - 0.5) / count
    marks = [0.5 + i * step for i in range(count + 1)]
    start = _on_sole(curve, belly)
    piece.chain([curve.at(s, back) for s in [0.0] + marks], ARCH_CHORD, BACK, seed=21)
    piece.chain([curve.at(s, belly) for s in [start] + [s for s in marks if s > start + 0.1]], ARCH_CHORD, CHORD, seed=22)
    for a, b in zip(marks, marks[1:]):
        if a > start:
            piece.bar(curve.at(a, belly), curve.at(b, back), ARCH_LACE, LACE, x=-0.046875, seed=24)
        piece.bar(curve.at(a, back), curve.at(b, belly), ARCH_LACE, LACE, x=0.046875, seed=23)
    for d in list(posts) + [TEXEL]:
        s = curve.where(d)
        piece.bar(curve.at(s, 0.0), curve.at(s, belly + deep / 2.0), (across, 0.125), PLATE, seed=25)
    _shoe(piece, curve, belly, ARCH_CHORD, 0.5625)
    return piece


# --- the frame ------------------------------------------------------------------------------------
class Frame:
    """The skeleton under one dome: its two curves, its models, and where every piece goes.

    ceiling   {column: the height of the underside over it, None under the open slit}
    axis      (x, z) of the dome's upright axis
    sides     where the two arch planes stand, as z counted from the axis
    arches    the columns the arch girders run under
    faces     (how far from the axis the ribs meet the ring girder's face, how far along their
              planes the arch girders do)
    base      the height of the bottom of the ring girder's upper row: the feet stand on it
    angles    the dome's seams, in degrees round the axis (0 = east, 90 = south)
    """

    def __init__(self, prefix, ceiling, axis, sides, arches, faces, base, angles):
        self.axis, self.sides = axis, tuple(sorted(sides))
        ax, az = axis
        foot_y = base + SOLE

        def round_axis(col):
            dx = max(col[0] - ax, ax - (col[0] + 1), 0.0)
            dz = max(col[1] - az, az - (col[1] + 1), 0.0)
            return math.hypot(dx, dz)

        def along(col):
            return max(col[0] - ax, ax - (col[0] + 1), 0.0) if col in arches else None

        self.meridian = under(ceiling, round_axis, (faces[0] - TEXEL, foot_y))
        self.arch_line = under(ceiling, along, (faces[1] - TEXEL, foot_y))
        reach = min(abs(s) for s in self.sides) - ARCH_CHORD[0] / 2.0
        self.models, self.pieces, self.placed = {}, {}, []
        posts = set()
        for deg in angles:
            a = math.radians(deg)
            if abs(math.sin(a)) * self.meridian.p[0][0] <= reach + 0.5:
                continue                                    # a seam between the two arch girders
            end = reach / abs(math.sin(a))
            name = f"{prefix}rib_{int(round(end * 100)):04d}"
            if name not in self.pieces:
                self.pieces[name] = rib(name, self.meridian, end)
            z, y = self.pieces[name].anchor
            self.placed.append((name, (ax + z * math.cos(a), y, az + z * math.sin(a)), deg - 90.0))
            posts.add(round(abs(end * math.cos(a)), 3))
        name = prefix + "arch"
        self.pieces[name] = arch(name, self.arch_line, sorted(posts))
        z, y = self.pieces[name].anchor
        for side in self.sides:
            self.placed.append((name, (ax + z, y, az + side), -90.0))
            self.placed.append((name, (ax - z, y, az + side), 90.0))
        self.models = {name: piece.m for name, piece in self.pieces.items()}

    def underside(self, along):
        """The height of the arch girders' underside at a distance from the axis along the slit."""
        s = self.arch_line.where(abs(along))
        return self.arch_line.at(s, ARCH_CHORD[1] + ARCH_DEPTH)[1]

    def lines(self):
        """Every bar of the frame in the scene's coordinates, as (a, b, half thickness)."""
        out = []
        for name, (x, y, z), yaw in self.placed:
            piece = self.pieces[name]
            az, ay = piece.anchor
            r = math.radians(yaw)
            dx, dz = -math.sin(r), math.cos(r)              # where the plane's z points
            for a, b, half in piece.lines:
                out.append(tuple((x + (p[0] - az) * dx, y + p[1] - ay, z + (p[0] - az) * dz) for p in (a, b)) + (half,))
        return out
