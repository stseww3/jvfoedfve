"""The iron skeleton of the great dome, as display models (a helper of interiors/domeroom; the
auto-discovery skips modules that start with "_").

What turns with the dome and carries its boards and plates, from the trucks up:

    the ring girder    a plate girder bent round the room, on the dome's trucks: a web two rows high
                       in front of the blocks over the ledge, an angle along its top and one along
                       its bottom, a stiffener every six degrees. It stops at the two piers beside
                       the slit's foot: between them is the sill and the gear that parts the leaves
                       (machines/domegear)
    two arch girders   lattice girders in the two upright planes beside the slit, from the pier at
                       the slit's foot over the crown to the pier on the far side: the slit is cut
                       between them. Where they spring they are straight, and their underside there
                       is the line the weights' rails of machines/domegear hang on
    the ribs           lattice ribs on the dome's seams, each from the ring girder up to the arch
                       girder it meets, all with the one curve of the dome's meridian. At its foot a
                       rib's two chords take hold of the ring girder's two angles
    the purlins        rings of bar from rib to rib; each ends on the arch girders, the upper ones
                       where a rib does
    the cross members  between the two arch girders where the slit is not: the girder across the
                       slit's head, and the purlins carried across

And what the iron carries on the inside, the lining of the vault: boards laid level from seam to
seam on the ribs' backs, a panel to a gore, and from cover plate to cover plate between the two
arch girders where the slit is not. They stand a texel in front of the stepped blocks of the skin,
so the vault is seen as twenty flat gores and not as a stair of blocks, and they are given the
night's light like the iron (a block of the vault far from the slit has none at all).

Nothing here is measured by hand: the frame is drawn under the ceiling it is given (the underside
of the boards over every column, read off the canvas by interiors/domeroom), so it follows the dome
when its courses change. A line that stays under every corner of the stepped boards is found once
for the ribs (round the axis) and once for the arch girders (along their planes).

Frames of reference. A piece is drawn in its own upright plane: z along the plane and away from
the dome's axis, y up, x across; lengths in blocks until they are handed to the model. A rib's
plane goes through the axis; an arch girder is drawn as a half, from its foot to the crown, and
set down four times. Shown with yaw = azimuth - 90, a piece's z points outwards at that azimuth
and its x the way the azimuth falls.
"""
import math

import numpy as np

from artkit import models as M

from ..common import palette as P

SCALE = 4                       # blocks to 16 model units: a model reaches 12 blocks, 16 texels to the block
UNIT = 16.0 / SCALE
TEXEL = 0.0625
MARGIN = TEXEL                  # between a chord's back and the lowest corner of the boards

# the sections, in blocks: (across the plane, in the plane)
RIB_CHORD = (0.25, 0.125)
RIB_DEEP = 0.625                # from a rib's back to its belly
RIB_PANEL = 0.75
ARCH_CHORD = (0.3125, 0.1875)
ARCH_DEEP = (0.75, 1.0)         # an arch girder's depth lies within these; the run under it says what it is
ARCH_PANEL = 1.0
LACE = (TEXEL, 0.125)           # the flat bars of a lattice
PURLIN = (0.125, 0.1875)        # (level, upright)
RUN_ROWS = 2.0                  # from the corners of the boards down to the line the weights' rails hang
#                                 on (machines/domegear: the lower corners of the lining one column on)
WEB = TEXEL                     # the ring girder's web plate
FLANGE = 0.25                   # how far its two angles stand out from the web, and how far they lap it
FACET = 6.0                     # degrees to one flat of the ring girder: three to a gore
PULL = 0.5                      # a length of the ring girder is shown from this far in front of its web
BAND = 0.5                      # an arch girder's cover plate reaches this far to either side of its plane
BOARD = 0.25                    # a board of the vault's lining: this wide, a texel thick
BOARD_TILT = 42.0               # degrees the frame of a panel of boards leans outwards (see boards())
LEAN = (("x", BOARD_TILT),)     # the turn a panel of boards is shown with, which sets it upright again
BAND_MOST = 7.0                 # the longest panel of the boards between the arch girders, along its line

# the skeleton is the lightest iron in the room: what is left of the night's light falls on it
CHORD = P.mat("iron", base=5, bevel="along")
BAR = P.mat("iron", base=4, bevel=0)
PLATE = P.mat("iron", base=4)
RIVET = P.mat("iron", kind="flat", base=6, bevel=0)
# the boards of the vault: the lightest of the dark wood (the lining of the drum is of the same tone),
# every board with a light edge and a dark one along it
LINING = P.mat("dark_wood", base=4, bevel="along")


# --- the line under the boards --------------------------------------------------------------------
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


def straight(points):
    """How many of the first points stand on one straight line (two at least, if there are two)."""
    n = min(2, len(points))
    while n < len(points):
        (x0, y0), (x1, y1), (x2, y2) = points[0], points[1], points[n]
        if abs((x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)) > 1e-6:
            break
        n += 1
    return n


def concave(points, hold=0, step=TEXEL / 2.0, most=4.0):
    """The chain through points = [(x, y)], x rising, let down where it has to be so that it bends
    one way only (never upwards) and passes on or under every point. The first point keeps its
    height, and so do the `hold` after it; every other may be let down by a whole number of steps.
    Of all the chains that bend the right way the one is kept whose gaps, squared, add up to the
    least: a few small gaps rather than one large one."""
    xs = np.array([p[0] for p in points], dtype=float)
    ys = np.array([p[1] for p in points], dtype=float)
    n = len(points)
    if n < 3:
        return list(points)
    drop = np.arange(int(round(most / step)) + 1) * step
    k = len(drop)
    huge = 1e18

    def price(i):
        return np.where(drop > 0.0, huge, 0.0) if i <= hold else drop ** 2

    cost = np.full((k, k), huge)            # [how far point i - 1 is let down, how far point i]
    cost[0, :] = price(1)
    came = []
    for i in range(1, n - 1):
        before = ((ys[i] - drop)[None, :] - (ys[i - 1] - drop)[:, None]) / (xs[i] - xs[i - 1])
        after = ((ys[i + 1] - drop)[None, :] - (ys[i] - drop)[:, None]) / (xs[i + 1] - xs[i])
        allowed = before[:, :, None] >= after[None, :, :] - 1e-9
        via = np.where(allowed, cost[:, :, None], huge)
        came.append(via.argmin(axis=0))
        cost = via.min(axis=0) + price(i + 1)[None, :]
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
    sides): it stays on the hollow side of the chain and keeps its first point. The chain is one
    half of a chain that is the same on both sides of x = 0, so the corner in the middle is cut
    like every other; what comes back ends on the middle."""
    whole = list(points) + [(-x, y) for x, y in reversed(points) if x < -1e-9]
    for _ in range(rounds):
        out = [whole[0]]
        for a, b in zip(whole, whole[1:]):
            out.append((a[0] + (b[0] - a[0]) * 0.25, a[1] + (b[1] - a[1]) * 0.25))
            out.append((a[0] + (b[0] - a[0]) * 0.75, a[1] + (b[1] - a[1]) * 0.75))
        out.append(whole[-1])
        whole = out
    half = [p for p in whole if p[0] < -1e-9]
    a, b = half[-1], whole[len(half)]
    t = (0.0 - a[0]) / (b[0] - a[0]) if b[0] - a[0] > 1e-12 else 0.0
    return half + [(0.0, a[1] + (b[1] - a[1]) * t)]


class Curve:
    """A line in an upright plane, as (z, y) points from its foot inwards and up; lengths along it
    are counted from the foot, and below nought the first stretch is carried on straight, into
    what the foot stands against."""

    def __init__(self, points):
        self.p = [(float(z), float(y)) for z, y in points]
        self.s = [0.0]
        for a, b in zip(self.p, self.p[1:]):
            self.s.append(self.s[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        self.length = self.s[-1]

    def _stretch(self, s):
        i = 0
        while i < len(self.s) - 2 and self.s[i + 1] < s:
            i += 1
        a, b = self.p[i], self.p[i + 1]
        span = self.s[i + 1] - self.s[i]
        return a, ((b[0] - a[0]) / span, (b[1] - a[1]) / span), s - self.s[i]

    def at(self, s, inside=0.0):
        """The point at length s, moved `inside` towards the hollow of the curve."""
        a, (tz, ty), along = self._stretch(min(s, self.length))
        return (a[0] + tz * along - ty * inside, a[1] + ty * along + tz * inside)

    def where(self, z):
        """The length at which the curve is at distance z from the axis (it only goes inwards)."""
        for i, (a, b) in enumerate(zip(self.p, self.p[1:])):
            if (a[0] - z) * (b[0] - z) <= 0.0 and abs(a[0] - b[0]) > 1e-12:
                return self.s[i] + (self.s[i + 1] - self.s[i]) * (a[0] - z) / (a[0] - b[0])
        return self.length if z <= self.p[-1][0] else 0.0

    def down(self, inside):
        """The length, below nought, at which the line `inside` the curve comes down on the upright
        face the curve starts from."""
        _a, (tz, ty), _along = self._stretch(0.0)
        return inside * ty / tz

    def slope(self):
        """How steeply the curve leaves its foot: rise over run."""
        _a, (tz, ty), _along = self._stretch(0.0)
        return ty / -tz

    def springing(self):
        """How far from its foot the curve runs straight."""
        (z0, y0), (z1, y1) = self.p[0], self.p[1]
        n = 1
        while n + 1 < len(self.p) and abs((z1 - z0) * (self.p[n + 1][1] - y0) - (y1 - y0) * (self.p[n + 1][0] - z0)) < 1e-9:
            n += 1
        return self.s[n]

    def level(self, inside, step=TEXEL):
        """The line `inside` the curve, from the face its foot stands against to its end:
        [(z, y)], z falling."""
        out, s = [], self.down(inside)
        while s < self.length:
            out.append(self.at(s, inside))
            s += step
        return out + [self.at(self.length, inside)]


def under(ceiling, reach, face, height=None):
    """The line of a chord's back: from the upright face at distance `face` inwards, MARGIN under
    every corner of the boards. It starts at `height`. Without one it springs straight: the line
    of the first corners, as many as stand on one line, is carried on down to the face."""
    corners = [(d, y - MARGIN) for d, y in tips(ceiling, reach) if d < face - 0.05]
    hold = 0
    if height is None:
        hold = straight(corners)
        (d0, y0), (d1, y1) = corners[0], corners[1]
        height = y0 - (y1 - y0) / (d0 - d1) * (face - d0)
    chain = [(-face, height)] + [(-d, y) for d, y in corners]
    return Curve([(-x, y) for x, y in rounded(concave(chain, hold=hold))])


def height_at(line, z):
    """The height of a line [(z, y)] (z falling) at distance z, None beyond its ends."""
    for a, b in zip(line, line[1:]):
        if b[0] - 1e-9 <= z <= a[0] + 1e-9 and a[0] - b[0] > 1e-12:
            return a[1] + (b[1] - a[1]) * (a[0] - z) / (a[0] - b[0])
    return None


# --- pieces ---------------------------------------------------------------------------------------
class Piece:
    """One model drawn in an upright plane, lengths in blocks: points are (z, y) in the plane with
    an x across it. `lines` keeps the bars that were drawn, for the checks: ((x, z, y), (x, z, y),
    half thickness)."""

    def __init__(self, name, anchor):
        self.name, self.anchor = name, anchor               # the anchor: (z, y) in the plane, at x = 0
        self.m = M.Model(name, px=SCALE)
        self.lines = []
        self.soffit = []                                    # the line of its underside, where it has one to tell

    def _u(self, x, p):
        return (x * UNIT, (p[1] - self.anchor[1]) * UNIT, (p[0] - self.anchor[0]) * UNIT)

    def rod(self, xa, a, xb, b, section, mat, seed=None):
        """A bar from (xa, a) to (xb, b); section: (its size sideways, its size in the upright plane
        through it). An upright bar has its first size across the piece's plane. A bar square to
        the frame is a plain box: it needs no turn, and a long one keeps the model's box small."""
        p, q = self._u(xa, a), self._u(xb, b)
        w, h = section[0] * UNIT, section[1] * UNIT
        runs = [abs(q[i] - p[i]) > 1e-6 for i in range(3)]
        if sum(runs) == 1:
            k = runs.index(True)
            half = ((0.0, h / 2.0, w / 2.0), (w / 2.0, 0.0, h / 2.0), (w / 2.0, h / 2.0, 0.0))[k]
            self.m.box([min(p[i], q[i]) - half[i] for i in range(3)], [max(p[i], q[i]) + half[i] for i in range(3)],
                       mat, grain="xyz"[k], seed=seed)
        else:
            self.m.beam(p, q, w, h, mat, seed=seed)
        self.lines.append(((xa, a[0], a[1]), (xb, b[0], b[1]), max(section) / 2.0))

    def bar(self, a, b, section, mat, x=0.0, seed=None):
        self.rod(x, a, x, b, section, mat, seed=seed)

    def chain(self, points, section, mat, seed=None):
        for a, b in zip(points, points[1:]):
            if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-6:
                self.bar(a, b, section, mat, seed=seed)

    def plate(self, points, width, mat, seed=None):
        """A plate a texel thick and `width` across the piece's plane, along the points. For the
        checks it is as thin as it is: what it is wide in is the plane of the boards above it."""
        for a, b in zip(points, points[1:]):
            if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-6:
                self.m.beam(self._u(0.0, a), self._u(0.0, b), width * UNIT, TEXEL * UNIT, mat, seed=seed)
                self.lines.append(((0.0, a[0], a[1]), (0.0, b[0], b[1]), TEXEL / 2.0))

    def box(self, lo, hi, x0, x1, mat, **kw):
        """A plate square to the frame: from (z, y) to (z, y), from x0 to x1 across."""
        self.m.box(self._u(min(x0, x1), (min(lo[0], hi[0]), min(lo[1], hi[1]))),
                   self._u(max(x0, x1), (max(lo[0], hi[0]), max(lo[1], hi[1]))), mat, **kw)

    def rivet(self, x, p, out):
        """A rivet head on a face that looks along `out` ("x", "-x", "z" or "-z" of the piece): one
        texel across, half a texel proud. (x, p) is the middle of its foot."""
        h, proud = TEXEL / 2.0, (-1.0 if out.startswith("-") else 1.0) * TEXEL / 2.0
        if out.endswith("z"):
            self.box((p[0], p[1] - h), (p[0] + proud, p[1] + h), x - h, x + h, RIVET, seed=99)
        else:
            self.box((p[0] - h, p[1] - h), (p[0] + h, p[1] + h), x, x + proud, RIVET, seed=99)


def _between(fixed, panel):
    """Stations from the first of `fixed` to the last, through every one of them, the stretches
    between them divided evenly into lengths of about `panel`."""
    out = []
    for a, b in zip(fixed, fixed[1:]):
        n = max(1, int(round((b - a) / panel)))
        out += [a + (b - a) * i / n for i in range(n)]
    return out + [fixed[-1]]


def _gusset(piece, face, y0, y1, half, rows):
    """A plate on the upright face a piece's foot stands against, with two rows of rivets."""
    piece.box((face - TEXEL, y0), (face, y1), -half, half, PLATE, seed=41)
    for x in (-half + TEXEL * 1.5, half - TEXEL * 1.5):
        for i in range(rows):
            piece.rivet(x, (face - TEXEL, y0 + (y1 - y0) * (i + 0.5) / rows), "-z")


def rib(name, curve, end, purlins, rows):
    """A lattice rib from the ring girder's web (its front is where the curve starts, its angles
    are at the heights `rows`) up to distance `end` from the axis, where it meets an arch girder:
    two chords, a zigzag of flat bars between them, a plate where it ends, a gusset on the web
    between the girder's two angles. The back chord leaves the web under the top angle, the belly
    chord stands on the bottom one: the rib is as deep as the girder where it starts.

    purlins: [(length along the curve, [(x, z) where a bar from that point of the rib ends, ...])];
    every such point is a point of the lattice."""
    across, deep = RIB_CHORD
    back, belly = deep / 2.0, RIB_DEEP - deep / 2.0
    last = curve.where(end)
    piece = Piece(name, curve.at(last * 0.5, RIB_DEEP + 0.75))
    tops = _between([0.0] + sorted(s for s, _ends in purlins if 0.3 < s < last - 0.3) + [last], RIB_PANEL)
    lows = [(a + b) / 2.0 for a, b in zip(tops, tops[1:])]
    face = curve.p[0][0]

    def into(a, b, by=0.1):                             # a chord's first point, carried on into the web
        k = by / math.hypot(a[0] - b[0], a[1] - b[1])
        return (a[0] + (a[0] - b[0]) * k, a[1] + (a[1] - b[1]) * k)

    line = [curve.at(s, back) for s in [curve.down(back)] + tops[1:]]
    piece.chain([into(line[0], line[1])] + line, RIB_CHORD, CHORD, seed=11)
    line = [(face, rows[0] + FLANGE)] + [curve.at(s, belly) for s in lows + [last]]
    piece.chain([into(line[0], line[1])] + line, RIB_CHORD, CHORD, seed=12)
    for i, s in enumerate(tops[1:-1]):
        piece.bar(curve.at(s, back), curve.at(lows[i], belly), LACE, BAR, seed=13)
        piece.bar(curve.at(s, back), curve.at(lows[i + 1], belly), LACE, BAR, seed=14)
    piece.bar(curve.at(last, 0.0), curve.at(last, RIB_DEEP), (across, 0.125), PLATE, seed=15)
    for s, ends in purlins:
        z, y = curve.at(s)
        for x1, z1 in ends:
            piece.rod(0.0, (z, y - PURLIN[1] / 2.0), x1, (z1, y - PURLIN[1] / 2.0), PURLIN, BAR, seed=16)
    _gusset(piece, face, rows[0] + FLANGE, rows[1] - FLANGE, 0.25, 4)
    piece.soffit = [(face, float(rows[0]))] + [curve.at(s, RIB_DEEP) for s in lows + [last]]
    return piece


def arch(name, curve, deep_all, posts):
    """Half an arch girder, from the pier at its foot to the crown: two chords, a lattice of
    crossing flat bars between them, a cover plate on its back as wide as the columns it runs
    under (the curb of the slit on one side of the crown, the edge of the boards everywhere), an
    upright plate at the crown and wherever something comes in from the side (posts: (distance
    from the crown, how far the plate stands over the girder's back)), a gusset on the pier. Where
    its straight springing ends is a point of the lattice, so the underside keeps to its line as
    far as the back does."""
    across, deep = ARCH_CHORD
    back, belly = deep / 2.0, deep_all - deep / 2.0
    last = curve.length
    piece = Piece(name, curve.at(last * 0.5, deep_all + 0.75))
    stops = sorted((curve.where(d), over) for d, over in posts)
    fixed = sorted({0.0, last, curve.springing()} | {s for s, _over in stops})
    fixed = [s for i, s in enumerate(fixed) if i == 0 or s == last or (s - fixed[0] > 0.4 and last - s > 0.4)]
    marks = _between(fixed, ARCH_PANEL)
    into = 0.1
    piece.chain([curve.at(s, back) for s in [curve.down(back) - into] + marks[1:]], ARCH_CHORD, CHORD, seed=21)
    piece.chain([curve.at(s, belly) for s in [curve.down(belly) - into] + marks], ARCH_CHORD, CHORD, seed=22)
    piece.plate([curve.at(s, -TEXEL / 2.0) for s in [curve.down(-TEXEL / 2.0) - into] + marks[1:]], 2.0 * BAND, PLATE,
                seed=26)
    for a, b in zip(marks, marks[1:]):
        piece.bar(curve.at(a, belly), curve.at(b, back), LACE, BAR, x=-0.046875, seed=24)
        piece.bar(curve.at(a, back), curve.at(b, belly), LACE, BAR, x=0.046875, seed=23)
    for s, over in stops + [(last - TEXEL, 0.0)]:
        piece.bar(curve.at(s, -over), curve.at(s, deep_all), (across, 0.125), PLATE, seed=25)
    face = curve.p[0][0]
    _gusset(piece, face, curve.at(curve.down(deep_all), deep_all)[1] + TEXEL, curve.p[0][1] + 0.1875, 0.28125, 4)
    piece.soffit = [curve.at(s, deep_all) for s in [curve.down(deep_all)] + marks]
    return piece


def cross(name, anchor, girder, ties, reach):
    """What goes across between the two arch girders, drawn in the upright plane along the slit:
    the girder across the slit's head (girder: (z, the height of its top, of its underside)), a
    lattice of the arch girders' make, and the purlins carried across (ties: [(z, top)])."""
    piece = Piece(name, anchor)
    z, top, low = girder
    across, deep = ARCH_CHORD
    hi, lo = top - deep / 2.0, low + deep / 2.0
    for y in (hi, lo):
        piece.rod(-reach, (z, y), reach, (z, y), (across, deep), CHORD, seed=51)
    count = max(2, 2 * int(round(reach / ARCH_PANEL)))
    marks = [-reach + 2.0 * reach * i / count for i in range(count + 1)]
    for a, b in zip(marks, marks[1:]):
        piece.rod(a, (z - 0.046875, lo), b, (z - 0.046875, hi), LACE, BAR, seed=52)
        piece.rod(a, (z + 0.046875, hi), b, (z + 0.046875, lo), LACE, BAR, seed=53)
    for x in (marks[0] + 0.0625, 0.0, marks[-1] - 0.0625):
        piece.rod(x, (z, low), x, (z, top), (0.125, across), PLATE, seed=54)
    for z1, top1 in ties:
        piece.rod(-reach, (z1, top1 - PURLIN[1] / 2.0), reach, (z1, top1 - PURLIN[1] / 2.0), PURLIN, BAR, seed=55)
    return piece


def ring(name, radius, rows, arc, cheek=None):
    """A length of the ring girder, `arc` degrees of it about the dome's axis in flats of about
    FACET degrees: each a web plate from rows[0] to rows[1] with its front `radius` from the axis,
    an angle along its top and one along its bottom; a stiffener on every joint between two flats.
    The model's origin is PULL in front of the web's middle, half way up.

    cheek: (side, swing, pier) for a length that ends at a pier of the slit, at its end on the side
    of +x (1) or of -x (-1): a plate from the girder's end straight back to the pier's face, which
    stands `pier` from the axis along the slit; the slit runs `swing` degrees off the radius
    through that end."""
    m = M.Model(name, px=SCALE)
    facets = max(1, int(round(arc / FACET)))
    each = arc / facets
    mid = (rows[0] + rows[1]) / 2.0
    y0, y1 = (rows[0] - mid) * UNIT, (rows[1] - mid) * UNIT
    t, f = TEXEL * UNIT, FLANGE * UNIT
    front = PULL * UNIT                                 # the web's front, from the model's origin
    axis = (0.0, 0.0, front - radius * UNIT)
    half = radius * math.tan(math.radians(each / 2.0)) * UNIT
    for i in range(facets):
        with m.turned(("y", (i - (facets - 1) / 2.0) * each), about=axis):
            m.box((-half, y0, front), (half, y1, front + WEB * UNIT), PLATE, grain="x", seed=61)
            for leg, lap in (((y1 - t, y1), (y1 - f, y1 - t)), ((y0, y0 + t), (y0 + t, y0 + f))):
                m.box((-half, leg[0], front - f), (half, leg[1], front), CHORD, grain="x", seed=62)
                m.box((-half, lap[0], front - t), (half, lap[1], front), CHORD, grain="x", seed=63)
                for k in range(4):
                    x, y = (k - 1.5) * half / 2.0, (lap[0] + lap[1]) / 2.0
                    m.box((x - t / 2.0, y - t / 2.0, front - 1.5 * t), (x + t / 2.0, y + t / 2.0, front - t), RIVET, seed=99)
    for i in range(1, facets):
        with m.turned(("y", (i - facets / 2.0) * each), about=axis):
            m.box((-t / 2.0, y0 + f, front - 0.1875 * UNIT), (t / 2.0, y1 - f, front), BAR, seed=64)
    if cheek is not None:
        side, swing, pier = cheek
        corner = radius / math.cos(math.radians(each / 2.0))            # the web's last corner, from the axis
        a, b = math.radians(arc / 2.0), math.radians(arc / 2.0 + swing)
        x, z = side * corner * math.sin(a) * UNIT, axis[2] + corner * math.cos(a) * UNIT
        dx, dz = side * math.sin(b), math.cos(b)
        length = (pier - corner * math.cos(math.radians(swing)) + TEXEL / 2.0) * UNIT
        m.beam((x - dx * f, 0.0, z - dz * f), (x + dx * length, 0.0, z + dz * length), t, y1 - y0, PLATE, seed=65)
    return m


def boards(name, line, span, start=0.0, stop=None, seed=0):
    """A panel of the vault's lining: boards BOARD wide laid edge to edge up `line` (a Curve in the
    panel's upright plane), whole boards from the length `start` along it to `stop`, each straight
    across that plane. span(z): how far the board whose lower edge is z from the axis reaches
    across, as (from, to), or None where there is none. Returns (the model, its anchor (z, y) in
    the plane, the boards as [((z, y) of the lower edge, (z, y) of the upper, (from, to) across)]),
    or None without a board.

    Only the face that looks into the room is drawn. How the game lights it (see machines/mast): a
    face is filed under the one of its model's six axes its normal lies nearest to, and that axis,
    turned with the display entity, is what the item renderer's two fixed lamps shine on. The
    boards of a gore look inwards and down, 16 degrees under the level at the springing and 80
    near the crown: drawn upright, the lower ones would be filed under a level axis and take the
    light of whatever side of the room they are on, the upper ones under "down". So a panel is
    drawn in a frame that leans outwards by BOARD_TILT, in which every board looks down more than
    anywhere else, and it is shown leaning back by as much (Frame.lined). The axis the boards are
    filed under then points inwards and well under the level, where neither lamp reaches: every
    board of every panel takes the same light, the least there is, on all sides of the room."""
    cells, s = [], start
    stop = line.length if stop is None else min(stop, line.length)
    while s + BOARD <= stop + 1e-9:
        a, b = line.at(s), line.at(s + BOARD)
        got = span(a[0])
        if got is not None and got[1] - got[0] >= 2.0 * TEXEL:
            cells.append((a, b, got))
        s += BOARD
    if not cells:
        return None
    anchor = ((cells[0][0][0] + cells[-1][1][0]) / 2.0, (cells[0][0][1] + cells[-1][1][1]) / 2.0)
    m = M.Model(name, px=SCALE)
    with m.turned(("x", -BOARD_TILT)):
        for i, (a, b, (x0, x1)) in enumerate(cells):
            mid, half = (x0 + x1) / 2.0 * UNIT, (x1 - x0) / 2.0 * UNIT
            p = (mid, (a[1] - anchor[1]) * UNIT, (a[0] - anchor[0]) * UNIT)
            q = (mid, (b[1] - anchor[1]) * UNIT, (b[0] - anchor[0]) * UNIT)
            # in the frame that looks from p at q, +y is the side of the dome's skin
            with m.aimed(p, q, "z") as length:
                m.box((-half, 0.0, 0.0), (half, TEXEL * UNIT, length), LINING, grain="x", seed=seed + i, skip="nsewu")
    return m, anchor, cells


# --- the frame ------------------------------------------------------------------------------------
class Frame:
    """The skeleton under one dome: its lines, its models, and where every piece goes.

    ceiling   {column: the height of the underside over it, None under the open slit}
    axis      (x, z) of the dome's upright axis
    sides     where the two arch planes stand, as z counted from the axis
    arches    the columns the arch girders run under
    faces     (how far from the axis the ring girder's web has its front, how far along their
              planes the arch girders come up against their piers)
    rows      the heights of the ring girder's underside and of its top
    angles    the dome's seams, in degrees round the axis (0 = east, 90 = south)
    sill      where the ring girder stops for the slit's foot: (-1 or 1: the side of the axis along
              the slit, how far the piers' outer faces stand from the axis across it), or None

    placed    [(model, the position of its origin, yaw)] for every piece of iron
    lined     the same for every panel of the boards; a panel is shown with the turn LEAN as well
    """

    def __init__(self, prefix, ceiling, axis, sides, arches, faces, rows, angles, sill=None):
        self.axis, self.sides, self.rows, self.faces = axis, tuple(sorted(sides)), rows, faces
        ax, az = axis

        def round_axis(col):
            dx = max(col[0] - ax, ax - (col[0] + 1), 0.0)
            dz = max(col[1] - az, az - (col[1] + 1), 0.0)
            return math.hypot(dx, dz)

        def along(col):
            return max(col[0] - ax, ax - (col[0] + 1), 0.0) if col in arches else None

        self.meridian = under(ceiling, round_axis, faces[0], rows[1])
        self.arch_line = under(ceiling, along, faces[1])
        tilt = math.atan(self.arch_line.slope())
        self.arch_deep = min(max((RUN_ROWS - MARGIN) * math.cos(tilt), ARCH_DEEP[0]), ARCH_DEEP[1])
        self.reach = reach = min(abs(s) for s in self.sides) - ARCH_CHORD[0] / 2.0
        self.models, self.pieces, self.placed = {}, {}, []

        # the ribs: every seam that is not between the two arch girders, up to the girder it meets
        def seam(deg):
            return round(deg % 360.0, 3) % 360.0

        ends = {}
        for deg in angles:
            lateral = abs(math.sin(math.radians(deg)))
            if lateral * faces[0] > reach + 0.5:
                ends[seam(deg)] = reach / lateral
        # the purlins: a ring through the top of every rib that ends low enough to leave a bay worth
        # spanning, and one half way up the lowest stretch
        tops = sorted({round(e, 3) for e in ends.values() if e > 3.5}, reverse=True)
        first = [self.meridian.at(self.meridian.where(tops[0]) / 2.0)[0]] if tops else []
        self.rings = [(d, self.meridian.at(self.meridian.where(d))[1]) for d in first + tops]
        step = 360.0 / len(angles)
        half_bay = math.radians(step) / 2.0
        junctions = {}
        for deg, end in sorted(ends.items()):
            a = math.radians(deg)
            from_slit = math.degrees(math.asin(abs(math.sin(a))))
            towards = 1.0 if math.sin(a) * math.cos(a) > 0.0 else -1.0     # the side of the rib the slit's axis is on
            purlins = []
            for d, _y in self.rings:
                if d < end - 2e-3:
                    continue
                bars = []
                for side in (1.0, -1.0):
                    other = ends.get(seam(deg - side * step))
                    if other is not None and other <= d + 2e-3:         # half way to the next rib
                        bars.append((side * d * math.sin(half_bay) * math.cos(half_bay), d * math.cos(half_bay) ** 2))
                    elif d - end > 2e-3 and side == towards:            # on to the arch girder
                        gap = math.radians(from_slit - math.degrees(math.asin(reach / d)))
                        bars.append((side * d * math.sin(gap), d * math.cos(gap)))
                        junctions.setdefault(round(math.sqrt(d * d - reach * reach), 3), 0.0)
                purlins.append((self.meridian.where(d), bars))
            lopsided = any(len(bars) != 2 or abs(bars[0][0] + bars[1][0]) > 1e-6 for _s, bars in purlins)
            name = f"{prefix}rib_{int(round(end * 100)):04d}" + (("p" if towards > 0.0 else "m") if lopsided else "")
            if name not in self.pieces:
                self.pieces[name] = rib(name, self.meridian, end, purlins, rows)
            z, y = self.pieces[name].anchor
            self.placed.append((name, (ax + z * math.cos(a), y, az + z * math.sin(a)), deg - 90.0))
            # the rib comes in over the arch girder's back by what the two lines differ there
            where = round(abs(end * math.cos(a)), 3)
            rib_top = self.meridian.at(self.meridian.where(end))[1]
            arch_top = self.arch_line.at(self.arch_line.where(where))[1]
            junctions[where] = max(junctions.get(where, 0.0), rib_top - arch_top, 0.0)

        name = prefix + "arch"
        self.pieces[name] = arch(name, self.arch_line, self.arch_deep, sorted(junctions.items()))
        z, y = self.pieces[name].anchor
        for side in self.sides:
            self.placed.append((name, (ax + z, y, az + side), -90.0))
            self.placed.append((name, (ax - z, y, az + side), 90.0))

        # between the arch girders: across the slit's head, in the first column that has boards, and
        # from there on away from the slit. Drawn with z along the slit and away from its foot
        self.head = None
        if sill is not None:
            row = int(math.floor(az))
            opens = [(col[0] + 0.5 - ax) * -sill[0] for col in arches if ceiling.get((col[0], row), 0) is None]
            if opens:
                at = max(opens) + 1.0
                s = self.arch_line.where(abs(at))
                top, low = self.arch_line.at(s)[1], self.arch_line.at(s, self.arch_deep)[1]
                ties = [(z, y) for z, y in ((math.sqrt(d * d - reach * reach), y) for d, y in self.rings if d > reach)
                        if z > at + 1.0]
                span = max([z for z, _y in ties] + [at])
                name = prefix + "cross"
                anchor = ((span + at) / 2.0, low - 1.0)
                self.pieces[name] = cross(name, anchor, (at, top, low), ties, reach)
                self.placed.append((name, (ax - sill[0] * anchor[0], anchor[1], az + sum(self.sides) / 2.0),
                                    -90.0 if sill[0] < 0.0 else 90.0))
                self.head = (-sill[0] * at, top, low)

        # the ring girder: one length to a gore. It is left out between the two piers of the slit's
        # foot, and the two lengths that end there go back to the piers with a cheek plate that lies
        # against a pier's outer face
        mid = (rows[0] + rows[1]) / 2.0
        name = prefix + "ring"
        if sill is not None:
            cut = math.degrees(math.asin((sill[1] + TEXEL * 0.75) / faces[0]))
            middle = 180.0 if sill[0] < 0.0 else 0.0
        gores = sorted(a % 360.0 for a in angles)
        for a0, a1 in zip(gores, gores[1:] + [gores[0] + 360.0]):
            length, at, arc, cheek = name, (a0 + a1) / 2.0, a1 - a0, None
            if sill is not None:
                off = (at - middle + 180.0) % 360.0 - 180.0         # the gore's middle, from the sill's
                lo, hi = abs(off) - arc / 2.0, abs(off) + arc / 2.0
                if hi <= cut + 1e-6:
                    continue
                if lo < cut:
                    side = math.copysign(1.0, off)                  # the pier is on the side the azimuth falls: +x
                    length, arc, cheek = name + ("_endp" if side > 0.0 else "_endm"), hi - cut, (side, cut, faces[1])
                    at = middle + side * (cut + hi) / 2.0
            if length not in self.models:
                self.models[length] = ring(length, faces[0], rows, arc, cheek)
            r = math.radians(at)
            self.placed.append((length, (ax + (faces[0] - PULL) * math.cos(r), mid, az + (faces[0] - PULL) * math.sin(r)),
                                at - 90.0))
        self.models.update({name: piece.m for name, piece in self.pieces.items()})

        # the boards between the iron: a panel to every gore outside the two arch girders, from the
        # ring girder up to the edge of their cover plates; the boards lie from seam to seam on the
        # line the ribs' backs keep to. A gore and the one across the dome are one model
        self.lined, self.panels = [], {}
        self.edge = edge = max(abs(s) for s in self.sides) + BAND
        for a0, a1 in zip(gores, gores[1:] + [gores[0] + 360.0]):
            if faces[0] * max(abs(math.sin(math.radians(a))) for a in (a0, a1)) <= edge:
                continue                                            # a gore between the two girders
            a, half = math.radians((a0 + a1) / 2.0), math.radians((a1 - a0) / 2.0)
            name = f"{prefix}boards_{int(round(math.degrees(a) % 180.0)):03d}"
            if name not in self.panels:
                # across the panel a point is x; its distance from the slit's axis is z * ks + x * kc
                ks, kc = abs(math.sin(a)), -math.copysign(1.0, math.sin(a)) * math.cos(a)

                def across(z, ks=ks, kc=kc, half=half):
                    lo, hi = -z * math.tan(half), z * math.tan(half)
                    if abs(kc) < 1e-9:
                        if z * ks < edge:
                            return None
                    elif kc > 0.0:
                        lo = max(lo, (edge - z * ks) / kc)
                    else:
                        hi = min(hi, (edge - z * ks) / kc)
                    return math.floor(lo / TEXEL) * TEXEL, math.ceil(hi / TEXEL) * TEXEL

                line = Curve([(z * math.cos(half), y) for z, y in self.meridian.p])
                got = boards(name, line, across, seed=100 * len(self.panels))
                if got is None:
                    continue
                self.models[name], self.panels[name] = got[0], got[1:]
            z, y = self.panels[name][0]
            self.lined.append((name, (ax + z * math.cos(a), y, az + z * math.sin(a)), math.degrees(a) - 90.0))
        # and between the two girders where the slit is not: from their far feet over the crown to
        # the girder across the slit's head (the last board ends on it), the boards across from
        # cover plate to cover plate, on the line the girders' backs keep to. Drawn like that
        # girder, z away from the slit's foot, in lengths a model can hold
        if self.head is not None:
            at, inner = -sill[0] * self.head[0], min(abs(s) for s in self.sides) - BAND
            whole = list(self.arch_line.p) + [(-z, y) for z, y in reversed(self.arch_line.p) if z > 1e-9]
            keep = [p for p in whole if p[0] > at - BOARD]
            if len(keep) < len(whole):
                (z0, y0), (z1, y1) = keep[-1], whole[len(keep)]
                keep.append((at - BOARD, y0 + (y1 - y0) * (z0 - (at - BOARD)) / (z0 - z1)))
            line = Curve(keep)
            count = int(math.ceil(line.length / BAND_MOST))
            each = math.ceil(line.length / BOARD / count) * BOARD
            for i in range(count):
                name = f"{prefix}boards_band_{i}"
                got = boards(name, line, lambda z: (-inner, inner), start=i * each, stop=(i + 1) * each,
                             seed=2000 + 100 * i)
                if got is not None:
                    self.models[name], self.panels[name] = got[0], got[1:]
                    z, y = got[1]
                    self.lined.append((name, (ax - sill[0] * z, y, az + sum(self.sides) / 2.0),
                                       -90.0 if sill[0] < 0.0 else 90.0))

    def run(self):
        """The straight line the arch girders' underside keeps to where they spring: ((distance
        from the axis along the slit, height) at the pier, (the same where the girder leaves the
        line and bends in under it)). The weights' rails of machines/domegear hang on it."""
        line = next(piece.soffit for name, piece in self.pieces.items() if name.endswith("arch"))
        (z0, y0), slope = line[0], self.arch_line.slope()
        last = line[0]
        for z, y in line[1:]:
            if abs((y0 + (z0 - z) * slope) - y) > 1e-6:
                break
            last = (z, y)
        return line[0], last

    def soffit(self, along):
        """The height of the arch girders' underside at a distance from the axis along the slit."""
        line = next(piece.soffit for name, piece in self.pieces.items() if name.endswith("arch"))
        return height_at(line, abs(along))

    def belly(self, distance):
        """The height of a rib's underside at a distance from the axis (None where no rib is)."""
        lines = [piece.soffit for name, piece in self.pieces.items() if "rib_" in name]
        return min((y for y in (height_at(line, distance) for line in lines) if y is not None), default=None)

    def lines(self):
        """Every bar of the pieces in the scene's coordinates, as (a, b, half thickness)."""
        out = []
        for name, (x, y, z), yaw in self.placed:
            piece = self.pieces.get(name)
            if piece is None:
                continue
            fz, fy = piece.anchor
            r = math.radians(yaw)
            (zx, zz), (xx, xz) = (-math.sin(r), math.cos(r)), (math.cos(r), math.sin(r))
            for a, b, half in piece.lines:
                out.append(tuple((x + p[0] * xx + (p[1] - fz) * zx, y + p[2] - fy, z + p[0] * xz + (p[1] - fz) * zz)
                                 for p in (a, b)) + (half,))
        return out

    def planks(self):
        """Every board of the lining in the scene's coordinates: the four corners of the face that
        looks into the room, the two of its lower edge first."""
        out = []
        for name, (x, y, z), yaw in self.lined:
            (fz, fy), cells = self.panels[name]
            r = math.radians(yaw)
            (zx, zz), (xx, xz) = (-math.sin(r), math.cos(r)), (math.cos(r), math.sin(r))
            for a, b, ends in cells:
                out.append(tuple((x + e * xx + (p[0] - fz) * zx, y + p[1] - fy, z + e * xz + (p[0] - fz) * zz)
                                 for p in (a, b) for e in ends))
        return out
