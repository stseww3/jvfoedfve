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

The rough face (a deep two-pixel joint where two stones meet) and the fine face (a one-pixel joint)
are the same stone in two finishes, not two stones (c190 pre-review point 2): both take the one
ashlar ramp off the one base lightness, and a facade covers their meeting with its string course.

Three versions are offered for the manager to choose (ART-PLAN 15, the stone fallback):

    a  the drawn rough/fine ashlar, to the pixel rules of materials.md section 3 -- the default:
       a pitch-faced rusticated stone, flat dressed walling a block long and half a block high in
       running bond, a sunk panel, the emblem carved proud
    b  another rhythm and another tooling: rock-faced rustication with a chamfered joint,
       broken-coursed dressed walling with a drafted joint, a raised panel, the emblem incised
    c  the vanilla sandstone, used as the game draws it -- the fallback, for the side-by-side

Each version is a whole set; they cannot share one pack. The test scene renders one per scene
(obs_mat_ashlar for a, obs_mat_ashlar_b, obs_mat_ashlar_c), the shots the same.
"""
import math

import numpy as np

from ..common import blocks as B
from ..common import palette as P
from . import _kit as K

TILE = K.TILE

# the blocks this package paints; nobody else may (families expand to stairs, slab, wall)
BLOCKS = K.blocks(B.ASHLAR_ROUGH, B.ASHLAR_FINE, B.ASHLAR_PANEL, B.ASHLAR_EMBLEM)

DEFAULT = "a"
VERSIONS = ("a", "b", "c")


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
    """The station emblem as the plan words it: a one-pixel ring, the meridian down it, a star on
    its upper-right shoulder. Returns (ring+meridian cells, star cells)."""
    ring = _cells(lambda dx, dy: 4.2 <= math.hypot(dx, dy) <= 4.9)
    meridian = [(7, y) for y in range(3, 13)]
    star = [(11, 4), (10, 4), (12, 4), (11, 3), (11, 5)]
    return ring + meridian, star


# ============================================================ version a: the card's pixel rules ===
def _rough_a(seed):
    """ASHLAR_ROUGH side: a pitch-faced rusticated stone. Base A2; a chamfer lit A3 top-left and
    shadowed A1 bottom-right; about a dozen short tool furrows (a lit lip over a dark groove); a
    one-pixel A0 joint all round, so two stones meet in a two-pixel groove."""
    rng = np.random.default_rng(seed)
    px = _fill(2)
    px[1, 1:15, :3] = _a(3)                       # the chamfer: top and left lit
    px[1:15, 1, :3] = _a(3)
    px[14, 1:15, :3] = _a(1)                      # bottom and right shadowed
    px[1:15, 14, :3] = _a(1)
    for _ in range(12):                           # pitch-faced tooling
        length = int(rng.integers(2, 4))
        x = int(rng.integers(3, 13 - length))
        y = int(rng.integers(4, 13))
        px[y, x:x + length, :3] = _a(1)           # the groove
        px[y - 1, x:x + length, :3] = _a(3)       # its lit lip
    px[0, :, :3] = _a(0)                          # the deep joint, one pixel all round
    px[15, :, :3] = _a(0)
    px[:, 0, :3] = _a(0)
    px[:, 15, :3] = _a(0)
    return px


def _rough_top_a(seed):
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


def _fine_a(tone):
    """ASHLAR_FINE side, to the pixel of materials.md section 3: two courses of eight pixels, a
    one-pixel A0 bed joint under each (rows 7 and 15), and one one-pixel A1 head joint to a course
    -- at x=15 in the upper course and x=7 in the lower -- so a stone is a block long and the
    courses break joint by half a block. The faces are flat: dressed stone, base A3.

    `tone` is the step of the ramp the upper course takes (A3 or one to either side). Its stone
    ends on the block's own edge, so every variant can give it a tone of its own. The stones of the
    lower course lie across two blocks, and two blocks choose their variants apart: a tone of its
    own there would step in the middle of a stone at every block edge, one step above the other all
    the way up a wall -- a stripe. The lower course is the base A3 in every variant."""
    px = _fill(3)
    px[0:7, :, :3] = _a(tone)
    px[0:7, 15, :3] = _a(1)                       # head joints: the upper course, then the lower
    px[8:15, 7, :3] = _a(1)
    px[7, :, :3] = _a(0)                          # bed joints
    px[15, :, :3] = _a(0)
    return px


def _fine_top_a(seed):
    """ASHLAR_FINE end (and the panel/emblem ends): flat dressed stone, base A3 with a faint
    tooling fleck and no joint at all -- a tread, a coping or a soffit carries no seam.

    materials.md section 3 words this picture "flat, base A3, a shallow joint". The joint is left
    out on purpose: the card and c190's point 1 forbid a joint on a tread, and stairs keep the
    attitude of their pictures when they are turned (uvlock), so a joint drawn along one edge of
    this picture would lie along the nosing of a flight that climbs north and across the tread of
    one that climbs east."""
    rng = np.random.default_rng(seed)
    px = _fill(3)
    m = rng.random((TILE, TILE))
    px[m < 0.10, :3] = _a(2)
    px[m > 0.90, :3] = _a(4)
    return px


def _panel_a(seed):
    """ASHLAR_PANEL side: a centred sunk square. The surround is bevelled, lit A4 top-left and
    shadowed A1 bottom-right; the sunk floor is A2, deepest (A0) along its foot."""
    px = _fill(3)
    px[0, :, :3] = _a(4)
    px[:, 0, :3] = _a(4)
    px[15, :, :3] = _a(1)
    px[:, 15, :3] = _a(1)
    m = 3 if seed % 2 else 4                      # two variants: a wider or a narrower panel
    y0, y1, x0, x1 = m, TILE - m, m, TILE - m
    px[y0:y1, x0:x1, :3] = _a(2)                  # the sunk floor
    px[y0, x0:x1, :3] = _a(1)                     # the drop: top and left walls in shadow
    px[y0:y1, x0, :3] = _a(1)
    px[y0:y1, x1 - 1, :3] = _a(4)                 # right wall catches the light
    px[y1 - 1, x0:x1, :3] = _a(0)                 # the foot of the recess, deepest
    return px


def _emblem_a(seed):
    """ASHLAR_EMBLEM side: the emblem carved proud of a dressed ground -- the figure lit A5 with a
    one-pixel A1 shadow thrown down and to the right. The figure is the same in every variant (a
    badge is not mirrored: the star stays on the upper right); the variants differ in the ground."""
    px = _fine_top_a(seed)                        # the dressed ground
    body, star = _emblem_figure()
    figure = set(body) | set(star)
    for x, y in figure:                          # the cast shadow
        if (x + 1, y + 1) not in figure and 0 <= x + 1 < TILE and 0 <= y + 1 < TILE:
            px[y + 1, x + 1, :3] = _a(1)
    for x, y in figure:                          # the raised figure
        px[y, x, :3] = _a(5)
    return px


# ============================================== version b: another seam rhythm / chiselled face ===
def _rough_b(seed):
    """ASHLAR_ROUGH side, rock-faced: a bumpy field of blobby tones with a chamfered joint (a
    one-pixel A1 chamfer inside the one-pixel A0 joint). A different rhythm from a's flat pitching."""
    rng = np.random.default_rng(seed)
    px = _fill(2)
    cell = rng.integers(0, 5, size=(TILE // 2 + 1, TILE // 2 + 1))
    tone = {0: 1, 1: 2, 2: 2, 3: 3, 4: 1}
    for y in range(2, 14):
        for x in range(2, 14):
            px[y, x, :3] = _a(tone[int(cell[y // 2, x // 2])])
    m = rng.random((TILE, TILE))
    hi = (m > 0.95)
    lo = (m < 0.05)
    hi[:2] = hi[-2:] = lo[:2] = lo[-2:] = False
    hi[:, :2] = hi[:, -2:] = lo[:, :2] = lo[:, -2:] = False
    px[hi, :3] = _a(4)                            # catchlights
    px[lo, :3] = _a(0)                            # pits
    px[1, 1:15, :3] = _a(1)                       # the chamfer
    px[1:15, 1, :3] = _a(1)
    px[14, 1:15, :3] = _a(1)
    px[1:15, 14, :3] = _a(1)
    px[0, :, :3] = _a(0)
    px[15, :, :3] = _a(0)
    px[:, 0, :3] = _a(0)
    px[:, 15, :3] = _a(0)
    return px


def _rough_top_b(seed):
    """ASHLAR_ROUGH end, rock-faced: a blotchy bed, no lines."""
    rng = np.random.default_rng(seed)
    px = _fill(2)
    cell = rng.integers(0, 5, size=(TILE // 2 + 1, TILE // 2 + 1))
    tone = {0: 1, 1: 2, 2: 2, 3: 3, 4: 3}
    for y in range(TILE):
        for x in range(TILE):
            px[y, x, :3] = _a(tone[int(cell[y // 2, x // 2])])
    return px


# per variant: the stones of the upper course as (the x of the head joint that ends it, its tone),
# and the x of the lower course's one head joint. No lower joint stands within two pixels of an
# upper one (of this block or of a neighbour's edge), so no joint runs on from course to course.
_FINE_B = (
    (((15, 3),), 3),
    (((7, 4), (15, 3)), 11),
    (((15, 2),), 12),
    (((7, 3), (15, 4)), 4),
)


def _fine_b(variant):
    """ASHLAR_FINE side, broken-coursed with a drafted joint: the same two eight-pixel courses and
    A0 bed joints as a, but every stone lit one step along its top arris, and the head joints at
    loose places -- the upper course ends on the block's edge and is broken once more in half the
    variants, the lower course is broken once, anywhere -- so the stones run from seven pixels to
    twenty-five long. The same stone as a, laid to a livelier rhythm.

    Tones as in a: only a stone that ends on the block's own edge takes a tone of its own."""
    upper, lower = _FINE_B[variant]
    px = _fill(3)
    px[8, :, :3] = _a(4)                          # the lower course: the base, its arris lit
    px[8:15, lower, :3] = _a(1)
    x0 = 0
    for cut, tone in upper:                       # the upper course, stone by stone
        px[0:7, x0:cut, :3] = _a(tone)
        px[0, x0:cut, :3] = _a(tone + 1)
        px[0:7, cut, :3] = _a(1)
        x0 = cut + 1
    px[7, :, :3] = _a(0)
    px[15, :, :3] = _a(0)
    return px


def _fine_top_b(seed):
    """ASHLAR_FINE end for version b: flat dressed stone, a touch lighter, no seam."""
    rng = np.random.default_rng(seed)
    px = _fill(3)
    m = rng.random((TILE, TILE))
    px[m < 0.10, :3] = _a(2)
    px[m > 0.80, :3] = _a(4)
    return px


def _panel_b(seed):
    """ASHLAR_PANEL side for version b: a raised (bolection) panel -- the field recessed and the
    centre proud, the opposite relief to a's sunk panel."""
    px = _fill(3)
    px[0, :, :3] = _a(1)
    px[:, 0, :3] = _a(1)
    px[15, :, :3] = _a(1)
    px[:, 15, :3] = _a(1)
    m = 3 if seed % 2 else 4
    y0, y1, x0, x1 = m, TILE - m, m, TILE - m
    px[y0:y1, x0:x1, :3] = _a(4)                  # the raised face
    px[y0, x0:x1, :3] = _a(5)                     # its lit top and left
    px[y0:y1, x0, :3] = _a(5)
    px[y1 - 1, x0:x1, :3] = _a(2)                 # its shadowed bottom and right
    px[y0:y1, x1 - 1, :3] = _a(2)
    return px


def _emblem_b(seed):
    """ASHLAR_EMBLEM side for version b: the emblem incised into the ground -- cut A1 with a lit A5
    lip where the groove catches the light, the opposite of a's raised figure. One figure in every
    variant, as in a; the variants differ in the ground."""
    px = _fine_top_b(seed)
    body, star = _emblem_figure()
    figure = set(body) | set(star)
    for x, y in figure:
        if (x + 1, y + 1) not in figure and 0 <= x + 1 < TILE and 0 <= y + 1 < TILE:
            px[y + 1, x + 1, :3] = _a(5)
    for x, y in figure:
        px[y, x, :3] = _a(1)
    return px


# ---- the textures of a version, by name ------------------------------------------------------------
def textures(version=DEFAULT):
    """{picture name: an array or a list of variant arrays} for a version. The names are the same in
    every version, so the redirect is the same; only the pixels change."""
    if version == "a":
        return {
            "ashlar_rough": [_rough_a(s) for s in (1, 2, 3)],
            "ashlar_rough_top": _rough_top_a(10),
            "ashlar_fine": [_fine_a(t) for t in (3, 4, 3, 2)],      # the base twice: half the stones are A3
            "ashlar_fine_top": _fine_top_a(30),
            "ashlar_panel": [_panel_a(0), _panel_a(1)],
            "ashlar_emblem": [_emblem_a(0), _emblem_a(1)],
        }
    if version == "b":
        return {
            "ashlar_rough": [_rough_b(s) for s in (1, 2, 3)],
            "ashlar_rough_top": _rough_top_b(10),
            "ashlar_fine": [_fine_b(v) for v in range(len(_FINE_B))],
            "ashlar_fine_top": _fine_top_b(30),
            "ashlar_panel": [_panel_b(0), _panel_b(1)],
            "ashlar_emblem": [_emblem_b(0), _emblem_b(1)],
        }
    raise ValueError(f"ashlar has no version {version!r}; there are {', '.join(VERSIONS)}")


# ---- the rules of the masonry, checked on the pixels -------------------------------------------------
def _steps(px):
    """A picture as steps of the ashlar ramp (0..5); -1 where a colour is not of the ramp."""
    out = np.full(px.shape[:2], -1)
    for n in range(6):
        out[(px[..., :3] == _a(n)).all(axis=-1)] = n
    return out


def faults(pictures):
    """What is wrong with a version's pictures as masonry: a list of lines, empty when nothing is.
    These are the rules of materials.md section 3 and of the card that hold for every drawn
    version, checked for every way two variants can come to lie beside or above one another (a
    wall takes its variants by position, so every pairing happens somewhere):

      - rough side   the one-pixel A0 joint runs all round (two stones meet in two pixels);
      - fine side    A0 bed joints along rows 7 and 15; no head joint runs on into the course above
                     or below it, in a block or from the block above -- that is what stripes a
                     wall; a stone is one tone from joint to joint, across the block's edge too;
      - the ends     no joint on the fine end, and no joint from side to side of the rough one: a
                     tread, a coping, a soffit carry none (c190's point 1).

    A0 and A1 are joint tones here: the face of a fine stone never takes them."""
    def many(name):
        got = pictures[name]
        return [_steps(p) for p in (got if isinstance(got, list) else [got])]

    out = []
    for i, s in enumerate(many("ashlar_rough")):
        if not all((edge == 0).all() for edge in (s[0], s[-1], s[:, 0], s[:, -1])):
            out.append(f"ashlar_rough{i}: the A0 joint does not run all round")

    fine = many("ashlar_fine")
    heads = []                                    # per variant: the head joints of its upper course, of its lower
    for i, s in enumerate(fine):
        if not ((s[7] == 0).all() and (s[15] == 0).all()):
            out.append(f"ashlar_fine{i}: no A0 bed joint along rows 7 and 15")
        upper, lower = ({x for x in range(TILE) if (s[y0:y0 + 7, x] <= 1).all()} for y0 in (0, 8))
        heads.append((upper, lower))
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
            off = (a > 1) & (b > 1) & (a != b)
            off[[7, 15]] = False
            if off.any():
                y, x = (int(v) for v in np.argwhere(off)[0])
                out.append(f"ashlar_fine{i} beside ashlar_fine{j}: a stone changes tone with no joint "
                           f"(row {y}, x={x % TILE})")

    for i, s in enumerate(many("ashlar_fine_top")):
        if (s <= 1).any():
            out.append(f"ashlar_fine_top{i}: a joint tone on the end of the fine stone")
    for i, s in enumerate(many("ashlar_rough_top")):
        if (s <= 1).all(axis=1).any() or (s <= 1).all(axis=0).any():
            out.append(f"ashlar_rough_top{i}: a joint from side to side on the end of the rough stone")
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
    wrong = faults(drawn)
    if wrong:
        raise AssertionError(f"ashlar version {version} breaks the rules of its masonry:\n  " + "\n  ".join(wrong))
    for name, pictures in drawn.items():
        K.paint(pack_dir, name, pictures)
    out = []
    for role, mapping in _maps():
        for block in K.blocks(role):
            out.append(K.redirect(pack_dir, block, mapping))
    return out
