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

    a  the drawn rough/fine ashlar of the card's pixel rules -- the default
    b  another rhythm: rock-faced rustication with a chamfered joint, and broken-coursed dressed
       walling with a droved emblem and a raised panel
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


def _fine_a(seed):
    """ASHLAR_FINE side: dressed walling, two courses of eight pixels in running bond. A one-pixel
    A0 bed joint at rows 7 and 15; one-pixel A1 head joints, the upper course offset half a stone
    from the lower (so no head joint runs the full height); each course its own tone around A3, lit
    one step along its top."""
    rng = np.random.default_rng(seed)
    t_top = int(np.clip(3 + int(rng.integers(-1, 2)), 2, 4))
    t_bot = int(np.clip(3 + int(rng.integers(-1, 2)), 2, 4))
    px = _fill(3)
    px[0:8, :, :3] = _a(t_top)
    px[8:16, :, :3] = _a(t_bot)
    px[0, :, :3] = _a(min(5, t_top + 1))         # the lit top of each course
    px[8, :, :3] = _a(min(5, t_bot + 1))
    for y0, cols in ((0, (7, 15)), (8, (3, 11))):  # head joints, the courses offset by half
        for c in cols:
            px[y0:y0 + 7, c, :3] = _a(1)
    px[7, :, :3] = _a(0)                          # bed joints
    px[15, :, :3] = _a(0)
    return px


def _fine_top_a(seed):
    """ASHLAR_FINE end (and the panel/emblem ends): flat dressed stone, base A3 with a faint
    tooling fleck and no joint at all -- a tread or a coping carries no seam."""
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
    one-pixel A1 shadow thrown down and to the right."""
    rng = np.random.default_rng(seed)
    px = _fine_top_a(seed)                        # the dressed ground
    body, star = _emblem_figure()
    if seed % 2:                                  # the second variant wears the star on the left
        body = [(14 - x, y) for x, y in body]
        star = [(14 - x, y) for x, y in star]
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


def _fine_b(seed):
    """ASHLAR_FINE side, broken-coursed: the same two eight-pixel courses and A0 bed joints as a,
    but with one or two head joints per course at loose positions, so the wall reads as the same
    stone laid to a livelier, less regular rhythm. Across the four variants no column repeats."""
    rng = np.random.default_rng(seed)
    t_top = int(np.clip(3 + int(rng.integers(-1, 2)), 2, 4))
    t_bot = int(np.clip(3 + int(rng.integers(-1, 2)), 2, 4))
    px = _fill(3)
    px[0:8, :, :3] = _a(t_top)
    px[8:16, :, :3] = _a(t_bot)
    px[0, :, :3] = _a(min(5, t_top + 1))
    px[8, :, :3] = _a(min(5, t_bot + 1))
    for y0 in (0, 8):
        cols = sorted({int(rng.integers(2, 14)) for _ in range(int(rng.integers(1, 3)))})
        for c in cols:
            px[y0:y0 + 7, c, :3] = _a(1)
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
    lip where the groove catches the light, the opposite of a's raised figure."""
    px = _fine_top_b(seed)
    body, star = _emblem_figure()
    if seed % 2:
        body = [(14 - x, y) for x, y in body]
        star = [(14 - x, y) for x, y in star]
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
            "ashlar_fine": [_fine_a(s) for s in (21, 22, 23, 24)],
            "ashlar_fine_top": _fine_top_a(30),
            "ashlar_panel": [_panel_a(0), _panel_a(1)],
            "ashlar_emblem": [_emblem_a(0), _emblem_a(1)],
        }
    if version == "b":
        return {
            "ashlar_rough": [_rough_b(s) for s in (1, 2, 3)],
            "ashlar_rough_top": _rough_top_b(10),
            "ashlar_fine": [_fine_b(s) for s in (21, 22, 23, 24)],
            "ashlar_fine_top": _fine_top_b(30),
            "ashlar_panel": [_panel_b(0), _panel_b(1)],
            "ashlar_emblem": [_emblem_b(0), _emblem_b(1)],
        }
    raise ValueError(f"ashlar has no version {version!r}; there are {', '.join(VERSIONS)}")


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
    for name, pictures in textures(version).items():
        K.paint(pack_dir, name, pictures)
    out = []
    for role, mapping in _maps():
        for block in K.blocks(role):
            out.append(K.redirect(pack_dir, block, mapping))
    return out
