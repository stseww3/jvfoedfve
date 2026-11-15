"""Work package materials/ashlar (plan ART-PLAN 6.2, materials.md section 3): grey-white ashlar.

The sandstone family is redirected to warm grey-white stone in four roles:

    ASHLAR_ROUGH   sandstone + stairs/slab/wall   rusticated base storey, stair cheeks
    ASHLAR_FINE    smooth_sandstone + stairs/slab  dressed coursed walling, the main walls
    ASHLAR_PANEL   cut_sandstone + slab            a sunk panel, under windows and in friezes
    ASHLAR_EMBLEM  chiseled_sandstone              the emblem block, lintels and over capitals

No vanilla picture is swapped: each block shows a copy of its own model with our pictures on it
(_kit.redirect / artkit.respack.redirect_block), so the files the sandstone family shares never move
and nothing of the game's is replaced. Every picture is script-made, 16 px, in the ashlar ramp
A0..A5 only (palette.py), and every one is checked by strays() before it is written.

Faces are mapped so that a tread or a coping never carries a bed joint (materials.md section 3,
c190 pre-review point 1): the fine stone shows ``ashlar_fine`` on its four sides and the seamless
``ashlar_fine_top`` on its up and down faces; the panel and the emblem take ``ashlar_fine_top`` on
their ends too. The rough stone shows ``ashlar_rough`` on its sides and ``ashlar_rough_top`` on its
ends, including the top of the low wall.

The rough face and the fine face are the same stone in two finishes, not two stones (c190
pre-review point 2): both take the one ashlar ramp, the rough a step darker over all (its base is
A2, the fine's A3), and a facade covers their meeting with its string course.

Three versions (ART-PLAN 15, the stone fallback). The pictures of the first round settled
everything but the rough face (the director's rulings of 2026-11-14 on c219's pre-review of the
three versions), so a and b are now the same set but for the jointing of the rough stone:

    a  the rough stone jointed all round, a stone to a block, as materials.md section 3 first
       had it -- kept for the side-by-side: a wall of it reads as tiles
    b  the rough stone banded: a channel along the foot of every course and no upright joint, so
       a base storey reads as courses, round its pilasters and corners too -- the default
    c  the vanilla sandstone, used as the game draws it -- the fallback, for the side-by-side

What a and b share: dressed walling in two courses to a block, lightly jointed, its stones of
loose lengths and lit along the top arris; a sunk panel of one size; the emblem incised; ends with
no joint. Each version is a whole set; they cannot share one pack. The test scene renders one per
scene (obs_mat_ashlar for a, obs_mat_ashlar_b, obs_mat_ashlar_c), the shots the same.
"""
import math

import numpy as np

from ..common import blocks as B
from ..common import palette as P
from . import _kit as K

TILE = K.TILE

# the blocks this package paints; nobody else may (families expand to stairs, slab, wall)
BLOCKS = K.blocks(B.ASHLAR_ROUGH, B.ASHLAR_FINE, B.ASHLAR_PANEL, B.ASHLAR_EMBLEM)

DEFAULT = "b"
VERSIONS = ("a", "b", "c")
JOINT = 2           # the lightest step of the ramp that is a joint on the fine face; its stones are lighter
STONE = 3           # the tone of a stone of the fine face, every one of them; its arris is a step lighter
GROOVES = (2, 5, 8, 11)     # the rows of the rough stone's tool marks: a groove, its lit lip the row below
ENDS = 3            # the variants of a stone's end; the game mixes them by position
FLECKS = (8, 20)    # the flecks on an end: so many of the rarer tone, so many of the commoner
CHOICE = 4          # the places drawn for a fleck; it takes the freest of them
RING = (5.9, 6.8)   # the emblem's ring: the pixels this far from the middle of the tile -- fourteen across
STAR = (10, 5)      # the emblem's star, a dot of two pixels by two: its upper left pixel


def _a(n):
    """One step of the ashlar ramp as (r, g, b); A0 dark .. A5 light."""
    return P.colour("ashlar", n)


def _fill(idx):
    px = np.empty((TILE, TILE, 4), dtype=np.uint8)
    px[..., :3] = _a(idx)
    px[..., 3] = 255
    return px


def _cells(inside):
    """Pixels (x, y) for which inside(dx, dy) holds, dx/dy measured from the tile centre."""
    c = (TILE - 1) / 2.0
    return [(x, y) for y in range(TILE) for x in range(TILE) if inside(x - c, y - c)]


def _emblem_figure():
    """The station's emblem, one figure for this block, the paving of the court and the models (the
    director's ruling of 2026-11-14 in g2, on #286/#288): a star about to cross the meridian in the
    eyepiece of a transit instrument -- the trade of an observatory that keeps the time. A
    one-pixel ring; the meridian down through it and out of it at both ends; a star inside the
    ring, right of its middle and above it, touching neither the ring nor the line. Returns
    (ring+meridian cells, star cells).

    On sixteen pixels the ring is the circle fourteen across (6.5 from the middle of the tile to
    the middle of its pixels): a smaller one leaves no room inside it for a star that stands
    clear. So the meridian runs the height of the tile, a pixel out of the ring at either end. The
    first drawings had a ring ten across with the star outside it, on its shoulder and then off it.

    The star is a dot of two pixels by two. A star with arms is, on this grid, a cross of five
    pixels, and from close by that read as a plus sign or a small cross and not as a star (c219's
    second look, g2 #313); from twenty blocks either is a dot. The ruling puts the star 0.4 of the
    radius right of the ring's middle and as far above it. Of the dots about that place the nearest
    stands with a corner on the ring and the one left of it against the lit lip of the meridian, a
    flag on a staff; this one, a row lower, has a plain pixel between it and both: 0.46 of the
    radius right of the middle and 0.31 above.

    The station's standard drawing (props/signs, c242) has the star a column to the left, at x
    9..10: flat figures -- enamel, cast iron -- have no lip, and there that is the dot a pixel
    clear of the ring and of the line. The rule is one, a pixel of the ground between the star
    and the ring and the line; cut into stone the lit lip is as plain to see as the cut and
    counts as line, so the stone's star stands a column further right (c242's ruling of
    2026-11-15 in g2, on the two drawings)."""
    lo, hi = RING
    ring = _cells(lambda dx, dy: lo <= math.hypot(dx, dy) <= hi)
    meridian = [(7, y) for y in range(TILE)]
    x, y = STAR
    star = [(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)]
    return ring + meridian, star


# ====================================================================== the rough stone ===
def _places(x0, x1):
    """The places of the rough stone's tool marks over the columns x0..x1, as (row, place, y, x,
    room): four rows (GROOVES), a place of four pixels to a mark, every other row two pixels
    along; a mark has `room` pixels from x, three, or two where the last place of a row is cut
    short by x1."""
    for i, y in enumerate(GROOVES):
        for k, x in enumerate(range(x0 + 2 * (i % 2), x1, 4)):
            yield i, k, y, x, min(3, x1 + 1 - x)


def _marks(px, rng, x0, x1, bare=()):
    """The tooling of the rough stone over the columns x0..x1: rows of short marks, each a dark
    groove (A1) over its lit lip (A3), two or three pixels long. Nothing but A1 and A3 on the
    base: no pits, no glints.

    A mark is a cut: its upper side is in shadow and the lower one catches the light, as on the
    channel of the banded stone and on the emblem. The first two rounds had the lip above the
    groove, and with a mark in every place the face read as raised bars in a net, a tread plate
    and nothing a chisel leaves (c219's review, g2 #310).

    The rows and the places are the same in every variant; a variant chooses where in its place a
    mark sits and how long it is, and which places (`bare`, as (row, place)) it leaves untooled.
    So across a wall the rows run on from block to block, and no stone carries a figure of its
    own -- thrown down anywhere, a dozen marks gathered in the middle of the block and read as a
    sign carved on it, a different sign on every stone."""
    for i, k, y, x, room in _places(x0, x1):
        at = int(rng.integers(0, room - 1))
        length = int(rng.integers(2, room - at + 1))
        if (i, k) not in bare:
            px[y, x + at:x + at + length, :3] = _a(1)
            px[y + 1, x + at:x + at + length, :3] = _a(3)


# per variant of the banded stone, the places it leaves untooled, as (row, place): one in each
# row, four of the sixteen, so that the marks are no net with a mark in every mesh.
#
# Two bare places that touch -- side by side in a row, or corner to corner in rows that follow
# one another -- are a bare patch, a figure on the wall. So none touch within a variant, and none
# across the edge of a block either, whichever two variants lie side by side there: where one
# leaves the last place of a row bare, none leaves bare the first place of that row, nor of the
# row above or below where that place reaches under it. And no place is bare in two variants, or
# that spot would be thin all over the wall.
#
# Twelve places are bare in one variant each; the four that never are lie at the right end of the
# two upper rows and at the left end of the two lower. Of three variants with four places each
# there are eight such tables, all of them with the middle variant here, a zigzag; this is the
# one whose other two variants are no zigzag.
_BARE = (
    ((0, 0), (1, 1), (2, 3), (3, 1)),
    ((0, 1), (1, 2), (2, 1), (3, 2)),
    ((0, 2), (1, 0), (2, 2), (3, 3)),
)


def _rough_ring(variant):
    """ASHLAR_ROUGH side for version a: a stone to a block, jointed all round as materials.md
    section 3 first had it -- a one-pixel A0 joint on every edge, so two stones meet in a two-pixel
    groove; inside it a chamfer, lit A3 along the top and the left, shadowed A1 along the bottom
    and the right; the face, base A2, tooled in rows (twelve marks, one in every place: inside a
    frame of joints a few bare places would be a figure on each stone again).

    Kept to be set beside b. Every block's joints stand where its neighbours' do, above and below
    as well, so a wall of it is a net of squares: facing tiles, not masonry (c219's pre-review)."""
    px = _fill(2)
    _marks(px, np.random.default_rng(variant + 1), 2, 13)
    px[1, 1:15, :3] = _a(3)
    px[1:15, 1, :3] = _a(3)
    px[14, 1:15, :3] = _a(1)
    px[1:15, 14, :3] = _a(1)
    px[0, :, :3] = _a(0)
    px[15, :, :3] = _a(0)
    px[:, 0, :3] = _a(0)
    px[:, 15, :3] = _a(0)
    return px


def _rough_band(variant):
    """ASHLAR_ROUGH side for version b, the default: banded rustication, the ground storey of a
    public building of the last century but one. A channel runs along the foot of every course --
    A0 on row 15, the stone above it shadowed A1 on row 14, the arris of the course below lit A3
    on row 0 -- and there is no upright joint at all. A base storey reads as one band of courses
    that can carry the pilasters over it; round a pilaster or a corner the courses run on as
    rings, and at a window they die into the opening.

    The face, base A2, is tooled in rows from edge to edge: sixteen places, of which a variant
    leaves four untooled (_BARE). No margin is left plain: a plain margin would draw the outline
    of the block again."""
    px = _fill(2)
    _marks(px, np.random.default_rng(variant + 1), 0, TILE - 1, _BARE[variant])
    px[0, :, :3] = _a(3)
    px[14, :, :3] = _a(1)
    px[15, :, :3] = _a(0)
    return px


def _touching(a, b=None, dx=0, dy=0):
    """Does a fleck of the end `a` touch one of `b`, corners counted? `a` and `b` are the flecks of
    two ends, True where one is; `b` lies dx blocks to the right of `a` and dy below it (1 or 0).
    With no `b`: do two flecks of `a` itself touch?"""
    if b is None:
        return bool((a[:, :-1] & a[:, 1:]).any() or (a[:-1] & a[1:]).any()
                    or (a[:-1, :-1] & a[1:, 1:]).any() or (a[:-1, 1:] & a[1:, :-1]).any())
    ya, xa = np.nonzero(a)
    yb, xb = np.nonzero(b)
    xb, yb = xb + dx * TILE, yb + dy * TILE
    return bool(((abs(xa[:, None] - xb[None, :]) <= 1) & (abs(ya[:, None] - yb[None, :]) <= 1)).any())


def _ends(seed, base, most):
    """The ENDS variants of the end of a stone -- its bed and its top: a tread, a coping, a kerb, a
    flag of a terrace, a soffit. Flat, the tone `base`, with single pixels a step from it: twenty of
    the tone `most` to a block and eight of the tone on the other side of the base. No joint at all.

    No fleck touches another, corners counted -- in a block, or across its edge or its corner into
    the next, whichever variants meet there: two that touch are a blot from close by, and a row of
    them is a seam. Each goes to the freest of a few places drawn by chance, so they spread over
    the block without standing in rows; and an end has variants, as a side has, so that the same
    few flecks do not come round at every block of a terrace.

    The first drawing gave either stone one picture. Laid as a field (the board's paved station;
    the site paves its terrace and lines its kerbs with these blocks), the fine end showed its one
    streak of flecks at every block, a lattice from above; the rough end, a third of it fleck with
    two broken bedding seams, read as stained, and its seams came round as a weave."""
    rng = np.random.default_rng(seed)
    rim = np.zeros((TILE, TILE), dtype=bool)      # the flecks of all the variants that lie on an edge
    at = np.arange(TILE)

    def far(flecks, x, y):
        """The square of the distance from (x, y) to the nearest fleck, round the block's edges."""
        ys, xs = np.nonzero(flecks)
        if not len(xs):
            return 4 * TILE * TILE
        dx, dy = abs(xs - x), abs(ys - y)
        return int((np.minimum(dx, TILE - dx) ** 2 + np.minimum(dy, TILE - dy) ** 2).min())

    def clear(flecks, x, y):
        """No fleck at (x, y) or beside it, round the block's edges."""
        return not flecks[np.ix_(at[[y - 1, y, (y + 1) % TILE]], at[[x - 1, x, (x + 1) % TILE]])].any()

    out = []
    for _ in range(ENDS):
        px, own = _fill(base), np.zeros((TILE, TILE), dtype=bool)
        for tone, count in zip((2 * base - most, most), FLECKS):
            for _ in range(count):
                found = []
                for _ in range(TILE ** 3):
                    x, y = (int(v) for v in rng.integers(0, TILE, 2))
                    edge = x in (0, TILE - 1) or y in (0, TILE - 1)
                    if clear(own, x, y) and (not edge or clear(rim, x, y)):
                        found.append((far(own, x, y), x, y))
                        if len(found) == CHOICE:
                            break
                if not found:
                    raise AssertionError("no room left on an end for a fleck that touches no other")
                _, x, y = max(found)
                own[y, x] = True
                rim[y, x] = x in (0, TILE - 1) or y in (0, TILE - 1)
                px[y, x, :3] = _a(tone)
        out.append(px)
    return out


# ============================================================ the fine stone and its ends ===
# per variant its two courses, the upper one first, each drawn in sixteen characters:
#     .  stone, the base tone A3      |  a head joint, A2
#
# Every course of every variant is broken once. The head joints stand at x 7, 8 or 15 in the upper
# course and at 3, 4 or 11 in the lower, two variants to each place: whichever variants come to lie
# on or beside one another, a joint is three pixels or more from every joint of the course above
# or below it (four or more inside a block), and none runs on from course to course. A stone runs
# from the joint of one block to the joint of the next, so along a wall the stones are 7 or 8
# pixels long, or 14 to 16, or 22 or 23: two in nine short, two in nine long, in both courses.
#
# Two blocks in three do not break the upper course on the block's edge. The first four variants
# all did: every second course of a wall had a joint on every line of the grid of the blocks, and
# a string course, which shows the upper course alone, read as a row of equal short stones (c219's
# review, g2 #310).
#
# Every stone is of the one tone. The first four variants had lighter stones in the upper course,
# nearly half of it: rows of light bars from twenty blocks (the same review). The six that
# followed kept two, in one course in twelve each. A stone that reaches the block's edge runs on
# into the next block, which chooses its variant by itself, so only a stone between two joints of
# one block can be lighter, and that is a short one, about as long as it is high. On the pictures
# (walls_far, walls_v2, coursed_course, lit_front at 06a6fd50) those read as pale squares strewn
# over the wall, as dots from thirty-seven blocks, and they pied a pilaster and a string course;
# so they went, as the reviewer had ruled for that case (c219, g2 #453), and with them the two
# courses broken twice that carried them, which had made three stones in seven short ones.
_FINE = (
    ("...............|", "....|..........."),
    (".......|........", "...........|...."),
    ("........|.......", "...|............"),
    (".......|........", "...|............"),
    ("...............|", "...........|...."),
    ("........|.......", "....|..........."),
)
SLIVER = 6          # a stone of the fine face is this many pixels long at the least
SHORT = 9           # a stone under this is a short one: about as long as its course is high


def _fine(variant):
    """ASHLAR_FINE side: dressed walling in two courses of eight pixels, broken-coursed and
    lightly jointed. A bed joint under each course (rows 7 and 15), one step lighter than the
    drawing first had it (A1; the A0 is kept for the channel of the rough stone), head joints
    lighter again (A2), every stone lit one step along its top arris, and the head joints at
    loose places (_FINE), so that along a wall the stones run from seven pixels to twenty-three.

    The first drawing, to the pixel of materials.md section 3 (a stone a block long in every
    course, half a block of break, A0 bed joints), read as a wall of enlarged grey brick from
    fourteen blocks; this one was chosen over it on the first round's pictures."""
    px = _fill(STONE)
    for y0, course in zip((0, 8), _FINE[variant]):
        for x, what in enumerate(course):
            if what == "|":
                px[y0:y0 + 7, x, :3] = _a(JOINT)
            else:
                px[y0, x, :3] = _a(STONE + 1)     # the arris of the stone, lit
    px[7, :, :3] = _a(1)
    px[15, :, :3] = _a(1)
    return px


def _fine_top():
    """ASHLAR_FINE end (and the panel/emblem ends): flat dressed stone, base A3 with a faint fleck
    of tooling and no joint at all -- a tread, a coping or a soffit carries no seam. Twenty pixels
    of a block are a step lighter and eight a step darker: with a fifth of it lighter a coping read
    as pitted from close by (c219's pre-review).

    materials.md section 3 first worded this picture "flat, base A3, a shallow joint". The joint
    is left out on purpose: the card and c190's point 1 forbid a joint on a tread, and stairs keep
    the attitude of their pictures when they are turned (uvlock), so a joint drawn along one edge
    of this picture would lie along the nosing of a flight that climbs north and across the tread
    of one that climbs east."""
    return _ends(30, 3, 4)


def _rough_top():
    """ASHLAR_ROUGH end: the bed of the rough stone, the same stone a step darker, base A2, and
    the fine end's fleck the other way round: twenty pixels of a block a step darker, pits, and
    eight a step lighter. The top of a kerb or a pier, the tread of a stair cheek, the soffit of
    an arch stone."""
    return _ends(10, 2, 1)


def _panel():
    """ASHLAR_PANEL side: a centred sunk square of ten pixels. The surround is bevelled, lit A4
    top-left and shadowed A1 bottom-right; the sunk floor is A2, deepest (A0) along its foot.

    One picture, no variants. The first drawing had two, a field of ten pixels and one of eight,
    and mixed by position they made the three panels under one window come out unequal (c219's
    pre-review); and a fleck on a field this small is a blemish, not a variety."""
    px = _fill(3)
    px[0, :, :3] = _a(4)
    px[:, 0, :3] = _a(4)
    px[15, :, :3] = _a(1)
    px[:, 15, :3] = _a(1)
    lo, hi = 3, TILE - 3
    px[lo:hi, lo:hi, :3] = _a(2)                  # the sunk floor
    px[lo, lo:hi, :3] = _a(1)                     # the drop: top and left walls in shadow
    px[lo:hi, lo, :3] = _a(1)
    px[lo:hi, hi - 1, :3] = _a(4)                 # right wall catches the light
    px[hi - 1, lo:hi, :3] = _a(0)                 # the foot of the recess, deepest
    return px


def _emblem():
    """ASHLAR_EMBLEM side: the emblem incised into a dressed ground -- cut A1, with a lit A5 lip
    where the far side of the cut catches the light (below it and to its right) -- and the ground
    plain A3, the face of a dressed stone.

    One picture, no variants: a badge is not mirrored (the star stays on the upper right), and
    there is nothing else to vary. While the ring was ten pixels across the ground round it took
    the fleck of the fine end, two ways; the ring of fourteen left five specks of that in the
    corners, and they read as dirt on a badge (c219's review, g2 #310)."""
    px = _fill(3)
    body, star = _emblem_figure()
    figure = set(body) | set(star)
    lip = {(x + 1, y + 1) for x, y in figure if x + 1 < TILE and y + 1 < TILE} - figure
    for x, y in lip:
        px[y, x, :3] = _a(5)
    for x, y in figure:
        px[y, x, :3] = _a(1)
    return px


# ---- the textures of a version, by name ------------------------------------------------------------
def textures(version=DEFAULT):
    """{picture name: an array or a list of variant arrays} for a version. The names are the same in
    every version, so the redirect is the same; only the pixels of the rough side change."""
    if version not in ("a", "b"):
        raise ValueError(f"ashlar draws no version {version!r}; it draws a and b (c is the vanilla stone)")
    rough = _rough_ring if version == "a" else _rough_band
    return {
        "ashlar_rough": [rough(v) for v in range(len(_BARE))],
        "ashlar_rough_top": _rough_top(),
        "ashlar_fine": [_fine(v) for v in range(len(_FINE))],
        "ashlar_fine_top": _fine_top(),
        "ashlar_panel": _panel(),
        "ashlar_emblem": _emblem(),
    }


# ---- the rules of the masonry, checked on the pixels -------------------------------------------------
def _steps(px):
    """A picture as steps of the ashlar ramp (0..5); -1 where a colour is not of the ramp."""
    out = np.full(px.shape[:2], -1)
    for n in range(6):
        out[(px[..., :3] == _a(n)).all(axis=-1)] = n
    return out


def _runs(row):
    """The runs of one tone along a row: (tone, length)."""
    out, start = [], 0
    for x in range(1, len(row) + 1):
        if x == len(row) or row[x] != row[start]:
            out.append((int(row[start]), x - start))
            start = x
    return out


def _course(s, y0):
    """A course of the fine side read back from a picture's steps, y0 its top row: per column
    JOINT where a head joint stands (joint tones from top to bottom), the tone of the stone where
    one does (one tone, lighter than a joint, under an arris a step lighter), and -1 where the
    column is neither."""
    out = []
    for x in range(TILE):
        column = [int(tone) for tone in s[y0:y0 + 7, x]]
        if 0 <= min(column) and max(column) <= JOINT:
            out.append(JOINT)
        elif min(column[1:]) == max(column[1:]) > JOINT and column[0] == column[1] + 1:
            out.append(column[1])
        else:
            out.append(-1)
    return out


def _groups(cells):
    """Cells (x, y) sorted into groups that touch, corners counted."""
    left, out = set(cells), []
    while left:
        group, edge = set(), [left.pop()]
        while edge:
            x, y = edge.pop()
            group.add((x, y))
            near = {(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)} & left
            left -= near
            edge += near
        out.append(group)
    return out


def _outside(cut):
    """The cells (x, y) that are reached from the edge of the tile without crossing a cell of
    `cut`, going along rows and columns only: what a closed ring keeps out of itself."""
    todo = [(x, y) for x in range(TILE) for y in range(TILE) if x in (0, TILE - 1) or y in (0, TILE - 1)]
    seen = set()
    while todo:
        x, y = todo.pop()
        if (x, y) in seen or (x, y) in cut or not (0 <= x < TILE and 0 <= y < TILE):
            continue
        seen.add((x, y))
        todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return seen


def faults(pictures, version=DEFAULT):
    """What is wrong with a version's pictures as masonry: a list of lines, empty when nothing is.
    These are the rules of the card, of materials.md section 3 and of the rulings on the first
    round's pictures, checked for every way two variants can come to lie beside or above one
    another (a wall takes its variants by position, so every pairing happens somewhere):

      - rough side   a: the one-pixel A0 joint runs all round (two stones meet in two pixels), and
                     every place of the face is tooled;
                     b: the channel runs from side to side (row 14 A1, row 15 A0, row 0 A3), no
                     upright joint, and no margin of the face is left plain; about four of the
                     sixteen places are left untooled, no two of them touching -- side by side in
                     a row, or corner to corner in rows that follow one another -- within the
                     block or across its edge, whichever variants meet there; and no place is
                     bare in two variants.
                     Both: the face is A2; a mark is a groove of A1, two or three pixels long, on
                     a row of GROOVES, over its lit lip of A3, and the face carries nothing else;
      - fine side    a bed joint, one joint tone unbroken, along rows 7 and 15, the same in every
                     variant; every course has a head joint, but none at a column where every
                     variant has one -- those stand in a row on the grid of the blocks; a head
                     joint is three pixels or more from every joint of the course above or below
                     it -- nearer, it runs on from course to course, and that stripes a wall; no
                     stone is shorter than SLIVER, and no more than a third of the stones of a
                     course are short ones (under SHORT); every stone is of the one tone STONE
                     from joint to joint and lit a step along its arris -- a stone of another
                     tone can only be a short one, and those are dots on a wall;
      - the ends     no joint on the fine end, and no joint from side to side of the rough one: a
                     tread, a coping, a soffit carry none (c190's point 1); the lighter fleck of the
                     fine end is no more than a tenth of it; either end is its base tone with single
                     pixels a step from it, an eighth of it at the most, and no two of them touch --
                     in a block, or across its edge or its corner, whichever variants meet there;
                     and an end has variants, or a field of it shows the same flecks at every block;
      - the panel    one size of sunk field: were it given variants, their bevels and the walls of
                     the field would stand at the same pixels;
      - the emblem   the star is a dot of two pixels by two of its own (no cross: red line 8), inside
                     the ring, with a plain pixel between it and the ring, the meridian and the lit
                     lip of either; the meridian runs out of the ring at both ends.

    The steps of the ramp up to JOINT are the joint tones of the fine side: the face of a fine
    stone never takes them. On the ends A0 and A1 are."""
    def many(name):
        got = pictures[name]
        return [_steps(p) for p in (got if isinstance(got, list) else [got])]

    out = []
    top, x0, x1 = (2, 2, 13) if version == "a" else (1, 0, TILE - 1)     # where the tooled face lies
    spans = {(r, k): x for r, k, _, x, _ in _places(x0, x1)}
    bare = []                                     # per variant: the places it leaves untooled
    for i, s in enumerate(many("ashlar_rough")):
        if version == "a":
            face = s[2:14, 2:14]
            if not all((edge == 0).all() for edge in (s[0], s[-1], s[:, 0], s[:, -1])):
                out.append(f"ashlar_rough{i}: the A0 joint does not run all round")
        else:
            face = s[1:14]
            if not ((s[14] == 1).all() and (s[15] == 0).all() and (s[0] == 3).all()):
                out.append(f"ashlar_rough{i}: no channel from side to side (row 14 A1, row 15 A0, row 0 A3)")
            if (face != 2).all(axis=0).any():
                out.append(f"ashlar_rough{i}: an upright joint; the courses are banded")
            if (face[:, :2] == 2).all() or (face[:, -2:] == 2).all():
                out.append(f"ashlar_rough{i}: a margin of the face is left plain")
        if ((face < 1) | (face > 3)).any():
            out.append(f"ashlar_rough{i}: a tone on the face that is not A1, A2 or A3")
        marks = [n for row in face for tone, n in _runs(row) if tone != 2]
        if not marks or min(marks) < 2 or max(marks) > 3:
            out.append(f"ashlar_rough{i}: a tool mark that is not two or three pixels long")
        grooves = np.zeros(face.shape, dtype=bool)
        rows = [y - top for y in GROOVES]
        grooves[rows] = face[rows] == 1
        if ((face == 1) != grooves).any() or ((face == 3) != np.roll(grooves, 1, axis=0)).any():
            out.append(f"ashlar_rough{i}: a tool mark that is not a groove (A1) on a row of GROOVES over its lit "
                       "lip (A3): a cut is dark above and lit below")
        bare.append({(r, k) for r, k, y, x, room in _places(x0, x1) if not (s[y, x:x + room] == 1).any()})
    last = max(k for _, k in spans)

    def corners(b, c, apart=0):
        """Do a place of b and a place of c, `apart` pixels to its right, touch corner to corner?"""
        return any(abs(p[0] - q[0]) == 1 and abs(spans[p] - spans[q] - apart) < 4 for p in b for q in c)

    for i, b in enumerate(bare):
        if version == "a":
            if b:
                out.append(f"ashlar_rough{i}: {len(b)} places untooled inside the joints: a figure on the stone")
            continue
        if not 3 <= len(b) <= 5:
            out.append(f"ashlar_rough{i}: {len(b)} of the {len(spans)} places untooled; about four are")
        if any((r, k + 1) in b for r, k in b):
            out.append(f"ashlar_rough{i}: two untooled places side by side in a row")
        if corners(b, b):
            out.append(f"ashlar_rough{i}: two untooled places corner to corner: a bare patch")
        for j, c in enumerate(bare):
            if j > i and b & c:
                out.append(f"ashlar_rough{i} and ashlar_rough{j}: both leave the places {sorted(b & c)} untooled")
            if any(k == last and (r, 0) in c for r, k in b) or corners(b, c, TILE):
                out.append(f"ashlar_rough{i} with ashlar_rough{j} on its right: two untooled places touch across "
                           "the block's edge")

    fine = many("ashlar_fine")
    courses = []                                  # per variant: its upper course and its lower, column by column
    beds = {(int(s[7, 0]), int(s[15, 0])) for s in fine}
    if len(beds) > 1:
        out.append(f"ashlar_fine: the variants do not agree on the tone of the bed joints ({sorted(beds)})")
    for i, s in enumerate(fine):
        if not all((s[y] == s[y, 0]).all() and 0 <= s[y, 0] <= JOINT for y in (7, 15)):
            out.append(f"ashlar_fine{i}: no unbroken bed joint (A0..A{JOINT}) along rows 7 and 15")
        courses.append([_course(s, y0) for y0 in (0, 8)])
        for name, course in zip(("upper", "lower"), courses[-1]):
            if -1 in course:
                out.append(f"ashlar_fine{i}: at x={course.index(-1)} the {name} course is neither a head joint nor "
                           "a stone of one tone under an arris a step lighter")
            if JOINT not in course:
                out.append(f"ashlar_fine{i}: a course without a head joint")
            odd = sorted({tone for tone in course if tone > JOINT and tone != STONE})
            if odd:
                out.append(f"ashlar_fine{i}: a stone of the {name} course is A{odd[0]}; every stone is A{STONE} -- "
                           "one of another tone can only be a short one, a dot on the wall from afar")
    for k, name in enumerate(("upper", "lower")):
        every = [x for x in range(TILE) if all(c[k][x] == JOINT for c in courses)]
        if every and len(courses) > 1:
            out.append(f"ashlar_fine: every variant breaks the {name} course at x={every}; along a wall those "
                       "joints stand in a row on the grid of the blocks")
        lengths = []                              # of the stones that begin in the left block of a pairing
        for i, left in enumerate(courses):
            for j, right in enumerate(courses):
                at = [x for x, tone in enumerate(left[k] + right[k]) if tone == JOINT]
                stones = [(a, b - a - 1) for a, b in zip(at, at[1:])]
                short = sorted({n for _, n in stones if n < SLIVER})
                if short:
                    out.append(f"ashlar_fine{i} beside ashlar_fine{j}: stones of {short} pixels in the {name} "
                               f"course; a stone is {SLIVER} long or more")
                lengths += [n for a, n in stones if a < TILE]
        squat = sum(n < SHORT for n in lengths)
        if squat * 3 > len(lengths):
            out.append(f"ashlar_fine: {squat} in {len(lengths)} stones of the {name} course are short ones (under "
                       f"{SHORT} pixels), more than a third: a course broken twice in a block makes them")
    for i, (upper, _) in enumerate(courses):
        for j, (_, lower) in enumerate(courses):
            near = sorted((u, v) for u in range(TILE) for v in range(TILE)
                          if upper[u] == lower[v] == JOINT and min((u - v) % TILE, (v - u) % TILE) < 3)
            if near:
                out.append(f"ashlar_fine{i} and ashlar_fine{j}: a head joint of the upper course of the one stands "
                           f"within two pixels of one of the lower course of the other (x={near[0][0]} and "
                           f"x={near[0][1]}); where the two meet, the joint runs on from course to course")
    for i, left in enumerate(fine):
        for j, right in enumerate(fine):
            pair = np.concatenate([left, right], axis=1)
            a, b = pair[:, :-1], pair[:, 1:]
            off = (a > JOINT) & (b > JOINT) & (a != b)
            off[[7, 15]] = False
            if off.any():
                y, x = (int(v) for v in np.argwhere(off)[0])
                out.append(f"ashlar_fine{i} beside ashlar_fine{j}: a stone changes tone with no joint "
                           f"(row {y}, x={x % TILE})")

    for i, s in enumerate(many("ashlar_fine_top")):
        if (s <= 1).any():
            out.append(f"ashlar_fine_top{i}: a joint tone on the end of the fine stone")
        if (s >= 4).mean() > 0.10:
            out.append(f"ashlar_fine_top{i}: more than a tenth of the end of the fine stone is lighter fleck")
    for i, s in enumerate(many("ashlar_rough_top")):
        if (s <= 1).all(axis=1).any() or (s <= 1).all(axis=0).any():
            out.append(f"ashlar_rough_top{i}: a joint from side to side on the end of the rough stone")
    for name, base in (("ashlar_fine_top", 3), ("ashlar_rough_top", 2)):
        ends = many(name)
        flecks = [s != base for s in ends]
        if len(ends) < 2:
            out.append(f"{name}: one picture; laid as a field its flecks come round at every block")
        for i, (s, f) in enumerate(zip(ends, flecks)):
            if (abs(s - base) > 1).any():
                out.append(f"{name}{i}: a tone more than a step from A{base}")
            if f.mean() > 0.125:
                out.append(f"{name}{i}: more than an eighth of the end is fleck ({f.sum()} pixels)")
            if _touching(f):
                out.append(f"{name}{i}: two flecks touch: a blot from close by")
            for j, g in enumerate(flecks):
                if any(_touching(f, g, dx, dy) for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1))):
                    out.append(f"{name}{i} and {name}{j} laid together: two flecks touch across the block's edge")

    panels = many("ashlar_panel")
    for i, s in enumerate(panels[1:], 1):
        if any(((s == n) != (panels[0] == n)).any() for n in (0, 1, 4)):
            out.append(f"ashlar_panel{i}: its bevels or the walls of its sunk field are not where ashlar_panel0 has them")

    for i, s in enumerate(many("ashlar_emblem")):
        cut = _groups((int(x), int(y)) for y, x in np.argwhere(s == 1))
        star = min(cut, key=len) if cut else set()
        x0, y0 = min(star) if star else (0, 0)
        if len(cut) != 2 or star != {(x0, y0), (x0 + 1, y0), (x0, y0 + 1), (x0 + 1, y0 + 1)}:
            out.append(f"ashlar_emblem{i}: the star is not a dot of two pixels by two of its own, apart from the "
                       f"ring and the meridian (the cut is in groups of {sorted(len(g) for g in cut)})")
            continue
        outside = _outside(max(cut, key=len))
        if any((x + dx, y + dy) in outside for x, y in star for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            out.append(f"ashlar_emblem{i}: the star is not inside the ring")
        own_lip = {(x + 1, y + 1) for x, y in star}
        about = {(x + dx, y + dy) for x, y in star for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - star - own_lip
        if any(s[y, x] != 3 for x, y in about if 0 <= x < TILE and 0 <= y < TILE):
            out.append(f"ashlar_emblem{i}: the star stands against the ring, the meridian or the lit lip of one of "
                       "them; a plain pixel lies between")
        if not ((s[0] == 1).any() and (s[-1] == 1).any()):
            out.append(f"ashlar_emblem{i}: the meridian does not run out of the ring at both ends")
    return out


# ---- how each family's faces are mapped (the same for every painted version) ------------------------
def _maps():
    """(role, {vanilla texture ref: name | {face: name}}). Confirmed against the 26.3 jar: the
    sandstone cube/stairs/slab carry sandstone on the sides and sandstone_top/bottom on the ends;
    the wall carries sandstone on every face; smooth_sandstone is cube_all on sandstone_top; cut and
    chiseled carry their own side picture and sandstone_top on the ends."""
    rough_side = {"side": "ashlar_rough", "end": "ashlar_rough_top"}
    fine_side = {"side": "ashlar_fine", "end": "ashlar_fine_top"}
    return [
        (B.ASHLAR_ROUGH, {"minecraft:block/sandstone": rough_side,
                          "minecraft:block/sandstone_top": "ashlar_rough_top",
                          "minecraft:block/sandstone_bottom": "ashlar_rough_top"}),
        (B.ASHLAR_FINE, {"minecraft:block/sandstone_top": fine_side}),
        (B.ASHLAR_PANEL, {"minecraft:block/cut_sandstone": "ashlar_panel",
                          "minecraft:block/sandstone_top": "ashlar_fine_top"}),
        (B.ASHLAR_EMBLEM, {"minecraft:block/chiseled_sandstone": "ashlar_emblem",
                           "minecraft:block/sandstone_top": "ashlar_fine_top"}),
    ]


def pack(pack_dir, version=DEFAULT):
    """Write the ashlar part of the resource pack for one version.

    a, b  paint the six pictures and redirect each sandstone-family block onto them.
    c     write nothing: the four families are claimed in BLOCKS, so the stand-ins leave them alone,
          and with no redirect they stay the vanilla sandstone -- the stone fallback, for compare.
    """
    if version == "c":
        return ["ashlar version c: the vanilla sandstone, left as the game draws it "
                "(claimed in BLOCKS, so no stand-in and no redirect touch it)"]
    drawn = textures(version)
    wrong = faults(drawn, version)
    if wrong:
        raise AssertionError(f"ashlar version {version} breaks the rules of its masonry:\n  " + "\n  ".join(wrong))
    for name, pictures in drawn.items():
        K.paint(pack_dir, name, pictures)
    out = []
    for role, mapping in _maps():
        for block in K.blocks(role):
            out.append(K.redirect(pack_dir, block, mapping))
    return out
