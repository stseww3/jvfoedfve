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
GROOVES = (3, 6, 9, 12)     # the rows of the rough stone's tool marks: a groove, its lit lip the row above
STAR = (13, 2)      # the middle of the emblem's star


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
    """The station emblem as the plan words it: a one-pixel ring, the meridian down it, a star off
    its upper-right shoulder. Returns (ring+meridian cells, star cells).

    The star stands a pixel clear of the ring. On the shoulder itself two of its five pixels were
    pixels of the ring, and what was left read as a burr on it (c219's pre-review)."""
    ring = _cells(lambda dx, dy: 4.2 <= math.hypot(dx, dy) <= 4.9)
    meridian = [(7, y) for y in range(3, 13)]
    x, y = STAR
    star = [(x, y), (x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
    return ring + meridian, star


# ====================================================================== the rough stone ===
def _marks(px, rng, x0, x1):
    """The tooling of the rough stone over the columns x0..x1: rows of short marks, each a dark
    groove (A1) under a lit lip (A3), two or three pixels long, a place of four pixels to each,
    every other row two pixels along. Nothing but A1 and A3 on the base: no pits, no glints.

    The rows and the places are the same in every variant; a variant chooses where in its place a
    mark sits and how long it is. So across a wall the rows run on from block to block, and no
    stone carries a figure of its own -- thrown down anywhere, a dozen marks gathered in the middle
    of the block and read as a sign carved on it, a different sign on every stone."""
    for i, y in enumerate(GROOVES):
        for x in range(x0 + 2 * (i % 2), x1, 4):
            room = min(3, x1 + 1 - x)                   # the last place of a row may be two pixels
            at = int(rng.integers(0, room - 1))
            length = int(rng.integers(2, room - at + 1))
            px[y, x + at:x + at + length, :3] = _a(1)
            px[y - 1, x + at:x + at + length, :3] = _a(3)


def _rough_ring(seed):
    """ASHLAR_ROUGH side for version a: a stone to a block, jointed all round as materials.md
    section 3 first had it -- a one-pixel A0 joint on every edge, so two stones meet in a two-pixel
    groove; inside it a chamfer, lit A3 along the top and the left, shadowed A1 along the bottom
    and the right; the face, base A2, tooled in rows (twelve marks).

    Kept to be set beside b. Every block's joints stand where its neighbours' do, above and below
    as well, so a wall of it is a net of squares: facing tiles, not masonry (c219's pre-review)."""
    px = _fill(2)
    _marks(px, np.random.default_rng(seed), 2, 13)
    px[1, 1:15, :3] = _a(3)
    px[1:15, 1, :3] = _a(3)
    px[14, 1:15, :3] = _a(1)
    px[1:15, 14, :3] = _a(1)
    px[0, :, :3] = _a(0)
    px[15, :, :3] = _a(0)
    px[:, 0, :3] = _a(0)
    px[:, 15, :3] = _a(0)
    return px


def _rough_band(seed):
    """ASHLAR_ROUGH side for version b, the default: banded rustication, the ground storey of a
    public building of the last century but one. A channel runs along the foot of every course --
    A0 on row 15, the stone above it shadowed A1 on row 14, the arris of the course below lit A3
    on row 0 -- and there is no upright joint at all. A base storey reads as one band of courses
    that can carry the pilasters over it; round a pilaster or a corner the courses run on as
    rings, and at a window they die into the opening.

    The face, base A2, is tooled in rows from edge to edge (sixteen marks). No margin is left
    plain: a plain margin would draw the outline of the block again."""
    px = _fill(2)
    _marks(px, np.random.default_rng(seed), 0, TILE - 1)
    px[0, :, :3] = _a(3)
    px[14, :, :3] = _a(1)
    px[15, :, :3] = _a(0)
    return px


def _rough_top(seed):
    """ASHLAR_ROUGH end: the bed of the rough stone, a weak horizontal layering over base A2, with
    no hard joint ring so that a run of them does not grid."""
    rng = np.random.default_rng(seed)
    px = _fill(2)
    m = rng.random((TILE, TILE))
    px[m < 0.14, :3] = _a(1)
    px[m > 0.86, :3] = _a(3)
    for y in (5, 11):                             # two broken bedding seams
        for x in range(TILE):
            if rng.random() < 0.55:
                px[y, x, :3] = _a(1)
    return px


# ============================================================ the fine stone and its ends ===
# per variant: the stones of the upper course as (the x of the head joint that ends it, its tone),
# and the x of the lower course's one head joint. No lower joint stands within two pixels of an
# upper one (of this block or of a neighbour's edge), so no joint runs on from course to course.
# A stone is A3 or A4, never A2: A2 is the head joint.
_FINE = (
    (((15, 3),), 3),
    (((7, 4), (15, 3)), 11),
    (((15, 4),), 12),
    (((7, 3), (15, 4)), 4),
)


def _fine(variant):
    """ASHLAR_FINE side: dressed walling in two courses of eight pixels, broken-coursed and
    lightly jointed. A bed joint under each course (rows 7 and 15), one step lighter than the
    drawing first had it (A1; the A0 is kept for the channel of the rough stone), head joints
    lighter again (A2), every stone lit one step along its top arris, and the head joints at loose
    places -- the upper course ends on the block's edge and is broken once more in half the
    variants, the lower course is broken once, anywhere -- so the stones run from seven pixels to
    twenty-five long.

    The first drawing, to the pixel of materials.md section 3 (a stone a block long in every
    course, half a block of break, A0 bed joints), read as a wall of enlarged grey brick from
    fourteen blocks; this one was chosen over it on the first round's pictures.

    Only a stone that ends on the block's own edge takes a tone of its own. The stones of the
    lower course lie across two blocks, and two blocks choose their variants apart: a tone of its
    own there would step in the middle of a stone at every block edge, one step above the other
    all the way up a wall -- a stripe. The lower course is the base A3 in every variant."""
    upper, lower = _FINE[variant]
    px = _fill(3)
    px[8, :, :3] = _a(4)                          # the lower course: the base, its arris lit
    px[8:15, lower, :3] = _a(2)
    x0 = 0
    for cut, tone in upper:                       # the upper course, stone by stone
        px[0:7, x0:cut, :3] = _a(tone)
        px[0, x0:cut, :3] = _a(tone + 1)
        px[0:7, cut, :3] = _a(2)
        x0 = cut + 1
    px[7, :, :3] = _a(1)
    px[15, :, :3] = _a(1)
    return px


def _fine_top(seed):
    """ASHLAR_FINE end (and the panel/emblem ends, and the emblem's ground): flat dressed stone,
    base A3 with a faint fleck of tooling and no joint at all -- a tread, a coping or a soffit
    carries no seam. About one pixel in sixteen is a step lighter and one in twenty-five a step
    darker: with a fifth of it lighter a coping read as pitted from close by (c219's pre-review).

    materials.md section 3 first worded this picture "flat, base A3, a shallow joint". The joint
    is left out on purpose: the card and c190's point 1 forbid a joint on a tread, and stairs keep
    the attitude of their pictures when they are turned (uvlock), so a joint drawn along one edge
    of this picture would lie along the nosing of a flight that climbs north and across the tread
    of one that climbs east."""
    rng = np.random.default_rng(seed)
    px = _fill(3)
    m = rng.random((TILE, TILE))
    px[m < 0.04, :3] = _a(2)
    px[m > 0.94, :3] = _a(4)
    return px


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


def _emblem(seed):
    """ASHLAR_EMBLEM side: the emblem incised into a dressed ground -- cut A1, with a lit A5 lip
    where the far side of the cut catches the light (below it and to its right). One figure in
    every variant (a badge is not mirrored: the star stays on the upper right); the variants differ
    in the fleck of the ground, which is kept out of the ring and a pixel clear of the figure."""
    px = _fine_top(seed)
    body, star = _emblem_figure()
    figure = set(body) | set(star)
    lip = {(x + 1, y + 1) for x, y in figure if x + 1 < TILE and y + 1 < TILE} - figure
    for x, y in figure | lip | set(_cells(lambda dx, dy: math.hypot(dx, dy) < 4.2)):
        px[max(y - 1, 0):y + 2, max(x - 1, 0):x + 2, :3] = _a(3)
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
        "ashlar_rough": [rough(s) for s in (1, 2, 3)],
        "ashlar_rough_top": _rough_top(10),
        "ashlar_fine": [_fine(v) for v in range(len(_FINE))],
        "ashlar_fine_top": _fine_top(30),
        "ashlar_panel": _panel(),
        "ashlar_emblem": [_emblem(0), _emblem(1)],
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


def faults(pictures, version=DEFAULT):
    """What is wrong with a version's pictures as masonry: a list of lines, empty when nothing is.
    These are the rules of the card, of materials.md section 3 and of the rulings on the first
    round's pictures, checked for every way two variants can come to lie beside or above one
    another (a wall takes its variants by position, so every pairing happens somewhere):

      - rough side   a: the one-pixel A0 joint runs all round (two stones meet in two pixels);
                     b: the channel runs from side to side (row 14 A1, row 15 A0, row 0 A3), no
                     upright joint, and no margin of the face is left plain.
                     Both: the face is A2 with marks of A1 and A3 only, two or three pixels long;
      - fine side    a bed joint, one joint tone unbroken, along rows 7 and 15, the same in every
                     variant; every course has a head joint; no head joint runs on into the course
                     above or below it, in a block or from the block above -- that is what stripes
                     a wall; a stone is one tone from joint to joint, across the block's edge too;
      - the ends     no joint on the fine end, and no joint from side to side of the rough one: a
                     tread, a coping, a soffit carry none (c190's point 1); the lighter fleck of the
                     fine end is no more than a tenth of it;
      - the panel    one size of sunk field: were it given variants, their bevels and the walls of
                     the field would stand at the same pixels;
      - the emblem   the star is five pixels of its own, clear of the ring.

    The steps of the ramp up to JOINT are the joint tones of the fine side: the face of a fine
    stone never takes them. On the ends A0 and A1 are."""
    def many(name):
        got = pictures[name]
        return [_steps(p) for p in (got if isinstance(got, list) else [got])]

    out = []
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

    fine = many("ashlar_fine")
    heads = []                                    # per variant: the head joints of its upper course, of its lower
    beds = {(int(s[7, 0]), int(s[15, 0])) for s in fine}
    if len(beds) > 1:
        out.append(f"ashlar_fine: the variants do not agree on the tone of the bed joints ({sorted(beds)})")
    for i, s in enumerate(fine):
        if not all((s[y] == s[y, 0]).all() and 0 <= s[y, 0] <= JOINT for y in (7, 15)):
            out.append(f"ashlar_fine{i}: no unbroken bed joint (A0..A{JOINT}) along rows 7 and 15")
        upper, lower = ({x for x in range(TILE) if (s[y0:y0 + 7, x] <= JOINT).all()} for y0 in (0, 8))
        heads.append((upper, lower))
        if not (upper and lower):
            out.append(f"ashlar_fine{i}: a course without a head joint")
        if upper & lower:
            out.append(f"ashlar_fine{i}: a head joint runs through both courses at x={sorted(upper & lower)}")
    for i, (_, lower) in enumerate(heads):
        for j, (upper, _) in enumerate(heads):
            if lower & upper:
                out.append(f"ashlar_fine{i} over ashlar_fine{j}: a head joint runs on at x={sorted(lower & upper)}")
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

    panels = many("ashlar_panel")
    for i, s in enumerate(panels[1:], 1):
        if any(((s == n) != (panels[0] == n)).any() for n in (0, 1, 4)):
            out.append(f"ashlar_panel{i}: its bevels or the walls of its sunk field are not where ashlar_panel0 has them")

    for i, s in enumerate(many("ashlar_emblem")):
        cut = _groups((int(x), int(y)) for y, x in np.argwhere(s == 1))
        if sorted(len(g) for g in cut)[:1] != [5] or len(cut) != 2:
            out.append(f"ashlar_emblem{i}: the star is not five pixels of its own, clear of the ring "
                       f"(the cut is in groups of {sorted(len(g) for g in cut)})")
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
