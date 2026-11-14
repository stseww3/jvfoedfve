"""Work package materials/brass-oldcopper-small (plan ART-PLAN 6.2 second batch, materials.md
section 6): brass, old copper, the small pieces, and the sound of brass underfoot.

Brass is the bamboo family, which this map uses for nothing else: plate, chequer plate, a thick
pipe, railing and gate, a half-glazed door (brass frame, opal glass), a grille hatch, button, shelf
and a plaque on a post or on chains. One ramp (R0..R5), lit from the upper left like the iron.

Old copper is waxed exposed copper brought to the palette's own brown ramp, the ramp the models'
old copper is painted with, so a gutter of blocks meets a downpipe that is a model. Only
waxed_exposed_* is redirected: the unwaxed exposed copper beside it and the waxed_weathered_* and
waxed_oxidized_* twins stay as the game draws them (_kit.PROTECT guards the last two). The cut
plate keeps the game's two-by-two sheets, the grid the verdigris above it has.

The small pieces: wall panelling (the dark oak trapdoor, never used as a trapdoor), the brass line
in the floor (the yellow carpet: the meridian and the emblem of the court) and the enamel nameplate
(the oak signs).

The flat faces are designed here. The shaped pieces (railing, gate, hatch, shelf, the post and
chains of a sign) keep the game's own cut-out and are toned into our ramps over it, so their UVs
still line up; of a sign's sheet only the board is drawn.

A plaque is left blank for what is written on it in the world: digits, signs, a little English.
The brass plaque takes the game's dark lettering as it is; the enamel one needs white.
"""
import numpy as np

from artkit import noise, respack

from ..common import blocks as B
from ..common import palette as P
from . import _kit as K

TILE = K.TILE

# the blocks this package paints; nobody else may (families expand to stairs, slab)
BLOCKS = K.blocks(B.BRASS_PLATE, B.BRASS_PATTERN, B.BRASS_COLUMN, B.BRASS_RAIL, B.BRASS_GATE, B.BRASS_DOOR,
                  B.BRASS_HATCH, B.BRASS_BUTTON, B.BRASS_SIGN, B.BRASS_SHELF, B.OLD_COPPER, B.OLD_COPPER_CUT,
                  B.WAINSCOT, B.BRASS_INLAY, B.ENAMEL_SIGN)


def _steps(ramp):
    return [P.colour(ramp, n) for n in range(len(P.RAMPS[ramp]))]


R = _steps("brass")             # R0..R5
C = _steps("old_copper")        # C0..C4
W = _steps("dark_wood")         # W0..W4
E = _steps("enamel")            # E0..E3
M = _steps("cream")             # M0..M3
O = _steps("opal")              # O0..O4
I = _steps("iron")              # I0..I6: the post and the chains of a sign


# ---- pixel helpers -----------------------------------------------------------------------------------
def _put(px, x, y, rgb):
    if 0 <= y < px.shape[0] and 0 <= x < px.shape[1]:
        px[y, x, :3] = rgb
        px[y, x, 3] = 255


def _fill(px, x0, y0, x1, y1, rgb):
    """The cells x0..x1-1, y0..y1-1 in one colour."""
    px[y0:y1, x0:x1, :3] = rgb
    px[y0:y1, x0:x1, 3] = 255


def _brushed(mat, seed, w=TILE, h=TILE, grain="u", **how):
    """A face of a palette material, w by h, without the material's own bevel: the edges of a piece
    are drawn by whoever knows its shape."""
    how.setdefault("bevel", 0)
    return P.mat(mat, **how).paint(w, h, grain=grain, seed=seed).copy()


def _dice(x, y, seed):
    """A number in [0, 1) for every cell, the same on every machine (a hash of the cell)."""
    n = (np.asarray(x, dtype=np.int64) * 374761393 + np.asarray(y, dtype=np.int64) * 668265263
         + int(seed) * 2147483647) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFFFF) / float(1 << 24)


def _stains(w, h, seed, share, size=4.0, margin=1):
    """Where a face is stained: soft patches about `size` pixels across over `share` of it, none
    within `margin` of its edge, so that no patch is cut off where two blocks meet."""
    yy, xx = np.mgrid[0:h, 0:w]
    field = noise.perlin2(xx / size + 0.37, yy / size + 0.61, seed)
    inner = np.zeros((h, w), dtype=bool)
    inner[margin:h - margin, margin:w - margin] = True
    return inner & (field > np.quantile(field[inner], 1.0 - share))


def _worn(steps, body, seed, w=TILE, h=TILE, dark=0.0, light=0.0, pits=0.0, size=4.0):
    """A face of sheet metal without the palette's brushed streaks (short streaks on a warm colour
    read as the grain of a plank): the step `body` of the colours `steps`, stained a step darker
    in soft patches over the share `dark` of it, a share `pits` of single pixels a step darker and
    a share `light` of single pixels worn a step brighter."""
    px = np.zeros((h, w, 4), np.uint8)
    px[..., :3] = steps[body]
    px[..., 3] = 255
    lower, upper = steps[max(0, body - 1)], steps[min(len(steps) - 1, body + 1)]
    if dark:
        px[_stains(w, h, seed, dark, size)] = (*lower, 255)
    yy, xx = np.mgrid[0:h, 0:w]
    inner = (xx > 0) & (xx < w - 1) & (yy > 0) & (yy < h - 1)
    roll = _dice(xx, yy, seed)
    px[inner & (roll < pits)] = (*lower, 255)
    px[inner & (roll > 1.0 - light)] = (*upper, 255)
    return px


def _sheen(px, seed, x0, x1, rows, colours):
    """The long thin reflections of a polished sheet: in each of `rows` a line of one of `colours`
    (taken in turn) between x0 and x1, each of its own length and place."""
    for n, y in enumerate(rows):
        length = int((x1 - x0) * (0.55 + 0.4 * _dice(n, y, seed)))
        start = x0 + int((x1 - x0 - length) * _dice(y, n, seed + 1))
        for x in range(start, start + length):
            _put(px, x, y, colours[n % len(colours)])


def _raised(px, x0, y0, x1, y1, light, dark):
    """The rim of x0..x1-1, y0..y1-1 as a plate standing proud: light along its top and left, dark
    along its bottom and right. The two corners where light meets dark keep what is there. With the
    colours the other way round the same rim is a sunk panel."""
    for x in range(x0, x1 - 1):
        _put(px, x, y0, light)
    for y in range(y0, y1 - 1):
        _put(px, x0, y, light)
    for x in range(x0 + 1, x1):
        _put(px, x, y1 - 1, dark)
    for y in range(y0 + 1, y1):
        _put(px, x1 - 1, y, dark)


def _ring(px, x0, y0, x1, y1, rgb, corners=True):
    """The rim of x0..x1-1, y0..y1-1 in one colour; without its four corners it reads rounded."""
    for x in range(x0, x1):
        for y in range(y0, y1):
            on_x, on_y = x in (x0, x1 - 1), y in (y0, y1 - 1)
            if (on_x or on_y) and (corners or not (on_x and on_y)):
                _put(px, x, y, rgb)


def _screws(px, points, head, shadow):
    """One-pixel heads with a pixel of shadow under each: the screws of the instrument panels."""
    for x, y in points:
        _put(px, x, y, head)
        _put(px, x, y + 1, shadow)


def _vanilla(ref):
    return np.asarray(K.vanilla_picture(ref)[0], dtype=np.uint8)


_BAMBOO = 1.5       # the steps of the brass ramp the game's bamboo pictures are toned over (see _tone)


def _tone(src, ramp, base, spread=3.0):
    """A picture of the game in one of our ramps: every opaque pixel goes to the step nearest its
    brightness, the picture's middle brightness landing on `base` and its range of tones (5th to
    95th percentile) taking up `spread` steps; the cut-out is kept. Bamboo is drawn in a few close
    yellows: spread over the whole ramp they turn to speckle, over a step and a half they stay
    the quiet grain of a brushed metal."""
    seen = src[..., 3] > 0
    out = np.zeros_like(src)
    if not seen.any():
        return out
    lum = src[..., :3].astype(np.float64) @ np.array([0.299, 0.587, 0.114])
    lo, mid, hi = np.percentile(lum[seen], (5, 50, 95))
    step = max(9.0, (hi - lo) / spread)
    steps = np.array(_steps(ramp), dtype=np.uint8)
    idx = np.clip(np.rint(base + (lum - mid) / step), 0, len(steps) - 1).astype(int)
    out[seen, :3] = steps[idx][seen]
    out[seen, 3] = 255
    return out


# ---- brass: the flat faces (designed) ----------------------------------------------------------------
_SHEEN = {1: (4, 7, 11), 2: (5, 9, 12), 3: (4, 8, 10)}       # the rows a plate's reflections lie in, by version


def _plate(seed):
    """BRASS_PLATE: a polished sheet screwed on at its corners, with the shallow raised edge of the
    iron plates, so a wall of them reads as butted sheets. Its reflections are a few long thin
    lines, two light and one dark, that stop short of the edge: they differ from version to
    version (three), so a wall of plates does not line them up into stripes."""
    px = _worn(R, 3, seed)
    _sheen(px, seed, 3, TILE - 3, _SHEEN[seed], (R[4], R[2], R[4]))
    _raised(px, 0, 0, TILE, TILE, R[4], R[1])
    _put(px, 1, 1, R[5])                                                # the glint in the lit corner
    _screws(px, [(2, 2), (TILE - 3, 2), (2, TILE - 4), (TILE - 3, TILE - 4)], R[5], R[1])
    return px


def _tread():
    """BRASS_PATTERN: chequer plate, the patterned plate of machine platforms and stair treads.
    Raised lugs four pixels long lean one way and the other from cell to cell of eight pixels, each
    with its shadow under it, on a field left flat: the lugs are the texture. It has no edge of its
    own and one version only, so a floor of it is one rolled sheet."""
    px = _brushed("brass", 0, base=2, noise=0.0)
    for cy in (0, 1):
        for cx in (0, 1):
            rising = (cx + cy) % 2 == 0
            lug = [(cx * 8 + 2 + t, cy * 8 + (5 - t if rising else 2 + t)) for t in range(4)]
            for x, y in lug:
                _put(px, x, y + 1, R[1])
            for x, y in lug:
                _put(px, x, y, R[4])
            _put(px, *min(lug, key=lambda cell: cell[1]), R[5])       # the end that catches the light
    return px


_ROUND = (1, 2, 3, 4, 5, 4, 3, 3, 3, 2, 2, 2, 1, 1, 0, 0)        # a cylinder lit from the upper left


def _pipe():
    """BRASS_COLUMN, its side: a thick pipe turned round by its shading, a collar at each end of
    the block so that a run of them is flanged at every joint. Drawn clean: a turned part."""
    px = np.zeros((TILE, TILE, 4), np.uint8)
    for x, step in enumerate(_ROUND):
        _fill(px, x, 0, x + 1, TILE, R[step])
        for y in (0, 1, TILE - 2, TILE - 1):                        # the collars stand a step prouder
            _put(px, x, y, R[min(5, step + 1)])
        for y in (2, TILE - 3):                                     # and throw a line of shadow
            _put(px, x, y, R[max(0, step - 1)])
    return px


def _pipe_end():
    """BRASS_COLUMN, its end: the flange face with its bore and four bolts."""
    px = _brushed("brass", 7, base=2, noise=0.0)
    _raised(px, 0, 0, TILE, TILE, R[3], R[1])
    c = (TILE - 1) / 2
    for y in range(TILE):
        for x in range(TILE):
            d = np.hypot(x - c, y - c)
            if d <= 3.3:
                _put(px, x, y, R[0])
            elif d <= 4.6:                                          # the lip of the bore
                _put(px, x, y, R[4] if (x - c) + (y - c) < 0 else R[2])
            elif d <= 6.6:
                _put(px, x, y, R[3])
    _screws(px, [(1, 1), (TILE - 2, 1), (1, TILE - 3), (TILE - 2, TILE - 3)], R[5], R[1])
    return px


def _tube(px, x0, y0, x1, y1, along, shades):
    """The cells x0..x1-1, y0..y1-1 as a round bar running along "x" or "y": `shades` are the steps
    of the brass ramp across it, from its lit side (top, or left) to its far side."""
    for y in range(y0, y1):
        for x in range(x0, x1):
            across = (y - y0) if along == "x" else (x - x0)
            _put(px, x, y, R[shades[min(across, len(shades) - 1)]])


def _rail():
    """BRASS_RAIL: a railing of polished tube. The game's fence models read five patches of the
    sheet (26.3: bamboo_fence_post, bamboo_fence_side_*): the post's side (0,0)-(4,16) and top
    (4,0)-(8,4), a bar's side (4,4)-(13,7), end (13,4)-(15,7) and top (13,7)-(15,16). The post is a
    tube with a knob at its head and a collar at its foot; the bars are thinner tubes."""
    px = _brushed("brass", 0, noise=0.0)                           # what no face shows: plain brass
    _tube(px, 0, 0, 4, TILE, "y", (2, 4, 3, 1))                     # the post
    _tube(px, 0, 0, 4, 2, "y", (3, 5, 4, 2))                        # its knob
    _tube(px, 0, 2, 4, 3, "y", (1, 3, 2, 0))                        # the neck under it
    _tube(px, 0, TILE - 2, 4, TILE, "y", (3, 5, 4, 2))              # the collar at its foot
    _tube(px, 0, TILE - 3, 4, TILE - 2, "y", (1, 3, 2, 0))
    for y, row in enumerate(((3, 4, 4, 2), (4, 5, 4, 2), (4, 4, 3, 1), (2, 2, 1, 1))):   # the knob from above
        for x, step in enumerate(row):
            _put(px, 4 + x, y, R[step])
    _tube(px, 4, 4, 15, 7, "x", (4, 3, 1))                          # a bar's side and its end
    _tube(px, 13, 7, 15, TILE, "y", (4, 4))                         # a bar from above
    return px


def _gate():
    """BRASS_GATE: the sheet of the game's gate is the gate seen from the front (26.3:
    bamboo_fence_gate*): two hanging posts at its sides, two meeting stiles in the middle, two bars
    either side between them, and above and below each the patch its top and its underside read.
    Every member is a tube like the railing's; the latch is a bright knob where the stiles meet."""
    px = _brushed("brass", 0, noise=0.0)
    for x in (0, TILE - 2):                                         # the hanging posts
        _tube(px, x, 2, x + 2, 13, "y", (4, 2))
        _fill(px, x, 0, x + 2, 2, R[4])
        _fill(px, x, 13, x + 2, 15, R[1])
    for x in (2, 10):                                               # the bars: the upper pair and the lower
        for y in (3, 9):
            _tube(px, x, y, x + 4, y + 3, "x", (4, 3, 1))
        _fill(px, x, 1, x + 4, 3, R[4])
        _fill(px, x, 12, x + 4, 14, R[1])
    for x in (6, 8):                                                # the meeting stiles
        _tube(px, x, 3, x + 2, 12, "y", (4, 2))
        _fill(px, x, 1, x + 2, 3, R[4])
        _fill(px, x, 12, x + 2, 14, R[1])
    for x in (7, 8):                                                # the latch
        _put(px, x, 7, R[5])
        _put(px, x, 8, R[1])
    return px


def _hatch():
    """BRASS_HATCH: a brass lid: a frame with a screw in each corner, a groove, a fielded middle
    and a flush ring to lift it by. A trapdoor shows this sheet upside down when it stands open or
    is seen from above, and its top three rows are its edge all round: so light and shadow are the
    same above and below, and the top three rows are frame and groove."""
    px = _worn(R, 3, 13)
    _ring(px, 0, 0, TILE, TILE, R[4])
    _ring(px, 2, 2, TILE - 2, TILE - 2, R[1])
    _ring(px, 3, 3, TILE - 3, TILE - 3, R[4])
    for x, y in ((1, 1), (TILE - 2, 1), (1, TILE - 2), (TILE - 2, TILE - 2)):
        _put(px, x, y, R[5])
    _ring(px, 6, 6, 10, 10, R[1], corners=False)                    # the cup of the ring
    _fill(px, 7, 7, 9, 9, R[2])
    _put(px, 6, 6, R[2])
    _put(px, 9, 9, R[2])
    return px


def _door_top():
    """BRASS_DOOR, upper half: a brass frame round one pane of frosted opal glass, the lock rail at
    its foot and the pull on the stile at a hand's height (a block and a little above the floor)."""
    px = _worn(R, 3, 11)
    _fill(px, 3, 3, 13, 14, O[2])
    for x in range(3, 13):
        _put(px, x, 3, O[0])                                        # the frame's shadow on the glass
    for y in range(4, 14):
        _put(px, 3, y, O[1])
    for x, y in ((9, 5), (8, 6), (7, 7), (11, 6), (10, 7), (9, 8)):  # the sheen of frosted glass
        _put(px, x, y, O[3])
    _raised(px, 2, 2, 14, 15, R[1], R[4])                           # the glass sits behind the frame
    for y in range(TILE):                                           # the leaf's own edges
        _put(px, 0, y, R[4])
        _put(px, TILE - 1, y, R[1])
    for x in range(1, TILE - 1):
        _put(px, x, 0, R[4])
    for y in (11, 12, 13, 14):                                      # the pull
        _put(px, 14, y, R[5])
    _put(px, 14, 15, R[1])
    return px


def _door_bottom():
    """BRASS_DOOR, lower half: a sunk brass panel between the lock rail and a riveted kick plate."""
    px = _worn(R, 3, 12)
    _fill(px, 4, 3, 12, 11, R[2])
    _raised(px, 3, 2, 13, 12, R[1], R[4])
    for y in range(TILE):
        _put(px, 0, y, R[4])
        _put(px, TILE - 1, y, R[1])
    for x in range(1, TILE):
        _put(px, x, TILE - 1, R[1])
    for x in range(1, TILE - 1):                                    # the kick plate stands proud
        _put(px, x, 13, R[4])
    _screws(px, [(2, 14), (TILE - 3, 14)], R[5], R[1])
    return px


def _plaque(w, h):
    """The board of BRASS_SIGN: a brass plaque with a screw in each corner, its middle left clear
    for the dark lettering the game writes on a sign."""
    px = _worn(R, 3, 21, w, h)
    _sheen(px, 21, 5, w - 5, (h - 3,), (R[4],))
    _raised(px, 0, 0, w, h, R[4], R[1])
    _screws(px, [(2, 2), (w - 3, 2), (2, h - 4), (w - 3, h - 4)], R[5], R[1])
    return px


# ---- old copper ----------------------------------------------------------------------------------------
def _copper(seed):
    """OLD_COPPER: one dull brown sheet with a shallow raised edge, stained darker in soft patches
    and rubbed lighter in a few spots: copper that has stood outdoors, not polished. Three
    versions."""
    px = _worn(C, 2, seed, dark=0.18, light=0.02, size=5.0)
    _raised(px, 0, 0, TILE, TILE, C[3], C[1])
    return px


def _copper_cut(seed):
    """OLD_COPPER_CUT: the game's cut copper, four sheets of eight pixels to the block, each with
    its lit and its shadowed edge. The seams between blocks are the seams within one, so a gutter,
    a ring round a drum or a roof of it is one even grid whichever way it runs, and half a block
    (a slab) is a row of whole sheets. A sheet in four has weathered a step darker than the rest,
    as the sheets of an old roof do; which one differs from version to version (three)."""
    px = np.zeros((TILE, TILE, 4), np.uint8)
    for n, (x, y) in enumerate(((0, 0), (8, 0), (0, 8), (8, 8))):
        tone = 1 if n == seed % 4 else 2
        px[y:y + 8, x:x + 8] = _worn(C, tone, seed * 4 + n, 8, 8, dark=0.08, size=3.0)
        _raised(px, x, y, x + 8, y + 8, C[tone + 1], C[tone - 1])
    return px


# ---- the small pieces ----------------------------------------------------------------------------------
def _wainscot():
    """WAINSCOT: one framed panel of dark wood to the block: rails and stiles, a groove, a fielded
    middle with the grain upright. Light and shadow are the same all round, so the panel reads the
    same whichever way up the trapdoor it is drawn on is hung."""
    px = _brushed("dark_wood", 5, grain="v")
    rail = _brushed("dark_wood", 6)
    px[:2], px[-2:] = rail[:2], rail[-2:]
    _ring(px, 2, 2, TILE - 2, TILE - 2, W[0])
    _ring(px, 3, 3, TILE - 3, TILE - 3, W[3])
    return px


def _inlay(seed):
    """BRASS_INLAY: the brass let into the paving. The low end of the ramp, flat, with a few
    pixels pitted dark and a few worn bright where feet pass; no edge and no direction of its own,
    so a line and a ring of it are unbroken whichever way they run. Under the night sky it is a
    dark metal, warmer than the slate and between the slate and its tuff flanks in brightness."""
    return _worn(R, 1, seed, pits=0.05, light=0.025)


def _nameplate(w, h):
    """The board of ENAMEL_SIGN: blue enamel, a cream line just inside its dark edge with the
    corners rounded off, a screw at each end; the middle is clear for white lettering."""
    px = _brushed("enamel", 31, w, h, noise=0.04)
    _ring(px, 0, 0, w, h, E[0])
    _ring(px, 1, 1, w - 1, h - 1, M[2], corners=False)
    for x in range(3, 3 + w // 4):                                  # the gloss of the enamel
        _put(px, x, 2, E[3])
    for x in range(2, w - 2):
        _put(px, x, h - 3, E[1])
    _screws(px, [(3, h // 2 - 1), (w - 4, h // 2 - 1)], M[1], E[0])
    return px


# ---- signs: the game's sheet, the board drawn ----------------------------------------------------------
# Where a sign's board lies on its 32 x 32 sheet, as (x0, y0, x1, y1): its two faces and its four thin
# edges. Read from the game's models (template_sign*, template_*hanging_sign*, 26.3); _sheet() fails
# if a sheet of the game is not opaque there, so a changed layout is noticed and not mispainted.
_STANDING = {"faces": ((0, 2, 24, 14), (0, 16, 24, 28)),
             "edges": ((0, 0, 24, 2), (0, 28, 24, 30), (24, 2, 26, 14), (24, 16, 26, 28)),
             "post": ((28, 0, 30, 14), (30, 0, 32, 14), (28, 16, 30, 30), (30, 16, 32, 30), (28, 30, 30, 32))}
_HANGING = {"faces": ((2, 16, 16, 26), (18, 16, 32, 26)),
            "edges": ((2, 14, 16, 16), (2, 26, 16, 28), (0, 16, 2, 26), (16, 16, 18, 26)),
            "post": ()}


def _sheet(ref, layout, face, edge, hardware, base, post=None):
    """A sign's sheet: the game's cut-out, the board's two faces drawn by face(w, h), its edges in
    `edge`, its post a rod two pixels thick in the colours `post` (lit side, far side), and the
    rest of it (the bar and the chains of a hanging sign) toned into the ramp `hardware`."""
    src = _vanilla(ref)
    px = _tone(src, hardware, base)
    for x0, y0, x1, y1 in layout["faces"] + layout["edges"] + layout["post"]:
        if not (src[y0:y1, x0:x1, 3] > 0).all():
            raise ValueError(f"{ref}: the sign is not where this package draws it ({x0}, {y0}, {x1}, {y1})")
    for x0, y0, x1, y1 in layout["edges"]:
        _fill(px, x0, y0, x1, y1, edge)
    for x0, y0, x1, y1 in layout["faces"]:
        px[y0:y1, x0:x1] = face(x1 - x0, y1 - y0)
    for x0, y0, x1, y1 in layout["post"]:
        _fill(px, x0, y0, x0 + 1, y1, post[0])
        _fill(px, x0 + 1, y0, x1, y1, post[1])
    return px


# ---- the sound of brass --------------------------------------------------------------------------------
# materials.md, way E. Every sound of the bamboo wood set is pointed at the game's own sound event of
# the same act on copper, by the event's name and not by its files: what is heard is exactly what
# walking on, striking or working copper sounds like in this version of the game, whichever files
# and loudness the game gives it. No audio is carried.
_ACTS = ("step", "hit", "fall", "place", "break")
SOUNDS = {
    **{f"block.bamboo_wood.{act}": f"block.copper.{act}" for act in _ACTS},
    **{f"block.bamboo_wood_hanging_sign.{act}": f"block.copper.{act}" for act in _ACTS},
    **{f"block.bamboo_wood_door.{act}": f"block.copper_door.{act}" for act in ("open", "close")},
    **{f"block.bamboo_wood_trapdoor.{act}": f"block.copper_trapdoor.{act}" for act in ("open", "close")},
    **{f"block.bamboo_wood_fence_gate.{act}": f"block.copper_trapdoor.{act}" for act in ("open", "close")},
    **{f"block.bamboo_wood_button.{act}": f"block.stone_button.{act}" for act in ("click_on", "click_off")},
    **{f"block.bamboo_wood_pressure_plate.{act}": f"block.metal_pressure_plate.{act}"
       for act in ("click_on", "click_off")},
}


# ---- assemble the pack ---------------------------------------------------------------------------------
# the picture of the game (as the models name it, without "minecraft:block/") -> ours
SHOWS = {
    "bamboo_planks": "brass_plate", "bamboo_mosaic": "brass_tread",
    "bamboo_block": "brass_pipe", "bamboo_block_top": "brass_pipe_end",
    "bamboo_fence": "brass_rail", "bamboo_fence_particle": "brass_plate",
    "bamboo_fence_gate": "brass_gate", "bamboo_fence_gate_particle": "brass_plate",
    "bamboo_door_top": "brass_door_top", "bamboo_door_bottom": "brass_door_bottom",
    "bamboo_trapdoor": "brass_hatch", "bamboo_shelf": "brass_shelf", "stripped_bamboo_block": "brass_plate",
    "bamboo_sign": "brass_sign", "bamboo_hanging_sign": "brass_hanging_sign",
    "exposed_copper": "old_copper", "exposed_cut_copper": "old_copper_cut",
    "dark_oak_trapdoor": "wainscot", "yellow_wool": "brass_inlay",
    "oak_sign": "enamel_sign", "oak_hanging_sign": "enamel_hanging_sign",
    "oak_planks": "enamel_plate", "stripped_oak_log": "enamel_plate",
}


def pack(pack_dir):
    versions = {}

    def paint(name, pictures):
        K.paint(pack_dir, name, pictures)
        versions[name] = len(pictures) if isinstance(pictures, list) else 1

    # brass
    paint("brass_plate", [_plate(s) for s in (1, 2, 3)])
    paint("brass_tread", _tread())
    paint("brass_pipe", _pipe())
    paint("brass_pipe_end", _pipe_end())
    paint("brass_rail", _rail())
    paint("brass_gate", _gate())
    paint("brass_hatch", _hatch())
    paint("brass_shelf", _tone(_vanilla("block/bamboo_shelf"), "brass", 3, spread=_BAMBOO))
    paint("brass_door_top", _door_top())
    paint("brass_door_bottom", _door_bottom())
    paint("brass_sign", _sheet("block/bamboo_sign", _STANDING, _plaque, R[2], "brass", 1, post=(R[2], R[0])))
    paint("brass_hanging_sign", _sheet("block/bamboo_hanging_sign", _HANGING, _plaque, R[2], "iron", 3))
    # old copper
    paint("old_copper", [_copper(s) for s in (1, 2, 3)])
    paint("old_copper_cut", [_copper_cut(s) for s in (1, 2, 3)])
    # the small pieces
    paint("wainscot", _wainscot())
    paint("brass_inlay", [_inlay(s) for s in (1, 2, 3)])
    paint("enamel_plate", _brushed("enamel", 32, noise=0.04))
    paint("enamel_sign", _sheet("block/oak_sign", _STANDING, _nameplate, E[0], "iron", 3, post=(I[4], I[2])))
    paint("enamel_hanging_sign", _sheet("block/oak_hanging_sign", _HANGING, _nameplate, E[0], "iron", 3))

    out = []
    for block in BLOCKS:
        shows = {ref: SHOWS[ref.rpartition("/")[2]] for ref in respack.block_pictures(K.game(), block)}
        # a block is mixed in as many versions as the least varied of its pictures has
        out.append(K.redirect(pack_dir, block, shows, variants=min(versions[name] for name in shows.values())))
    out.append(K.sounds(pack_dir, {event: [{"name": to, "type": "event"}] for event, to in SOUNDS.items()}))
    return out
