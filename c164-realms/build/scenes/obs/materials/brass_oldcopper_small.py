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

from artkit import respack

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
def _plate(seed):
    """BRASS_PLATE: a polished sheet with the shallow raised edge of the iron plates, so a wall of
    them reads as butted sheets. Three versions, the brushing only."""
    px = _brushed("brass", seed, noise=0.14)
    _raised(px, 0, 0, TILE, TILE, R[4], R[1])
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


def _door_top():
    """BRASS_DOOR, upper half: a brass frame round one pane of frosted opal glass, the lock rail at
    its foot and the pull on the stile at a hand's height (a block and a little above the floor)."""
    px = _brushed("brass", 11, noise=0.10)
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
    px = _brushed("brass", 12, noise=0.10)
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
    px = _brushed("brass", 21, w, h, noise=0.08)
    _raised(px, 0, 0, w, h, R[4], R[1])
    _screws(px, [(2, 2), (w - 3, 2), (2, h - 4), (w - 3, h - 4)], R[5], R[1])
    return px


# ---- old copper ----------------------------------------------------------------------------------------
def _copper(seed):
    """OLD_COPPER: one dull brown sheet with a shallow raised edge. Three versions, the brushing."""
    px = _brushed("old_copper", seed, noise=0.16)
    _raised(px, 0, 0, TILE, TILE, C[3], C[1])
    return px


def _copper_cut(seed):
    """OLD_COPPER_CUT: the game's cut copper, four sheets of eight pixels to the block, each with
    its lit and its shadowed edge. The seams between blocks are the seams within one, so a gutter,
    a ring round a drum or a roof of it is one even grid whichever way it runs, and half a block
    (a slab) is a row of whole sheets."""
    px = _brushed("old_copper", seed, noise=0.12)
    for y in (0, 8):
        for x in (0, 8):
            _raised(px, x, y, x + 8, y + 8, C[3], C[1])
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
    """BRASS_INLAY: the brass let into the paving. Dark, the low end of the ramp, brushed along the
    line and with no edge of its own: under the night sky it is a dark metal a little warmer and
    lighter than the slate, a line and a ring of it are unbroken, and it does not shout."""
    return _brushed("brass_dark", seed, grain="v", noise=0.08)


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
             "edges": ((0, 0, 24, 2), (0, 28, 24, 30), (24, 2, 26, 14), (24, 16, 26, 28))}
_HANGING = {"faces": ((2, 16, 16, 26), (18, 16, 32, 26)),
            "edges": ((2, 14, 16, 16), (2, 26, 16, 28), (0, 16, 2, 26), (16, 16, 18, 26))}


def _sheet(ref, layout, face, edge, hardware, base, spread=3.0):
    """A sign's sheet: the game's cut-out, the board's two faces drawn by face(w, h), its edges in
    `edge`, and all the rest of it (post, bracket, chains) toned into the ramp `hardware`."""
    src = _vanilla(ref)
    px = _tone(src, hardware, base, spread)
    for x0, y0, x1, y1 in layout["faces"] + layout["edges"]:
        if not (src[y0:y1, x0:x1, 3] > 0).all():
            raise ValueError(f"{ref}: the board is not where this package draws it ({x0}, {y0}, {x1}, {y1})")
    for x0, y0, x1, y1 in layout["edges"]:
        _fill(px, x0, y0, x1, y1, edge)
    for x0, y0, x1, y1 in layout["faces"]:
        px[y0:y1, x0:x1] = face(x1 - x0, y1 - y0)
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
    for name, ref in (("brass_rail", "block/bamboo_fence"), ("brass_gate", "block/bamboo_fence_gate"),
                      ("brass_hatch", "block/bamboo_trapdoor"), ("brass_shelf", "block/bamboo_shelf")):
        paint(name, _tone(_vanilla(ref), "brass", 3, spread=_BAMBOO))
    paint("brass_door_top", _door_top())
    paint("brass_door_bottom", _door_bottom())
    paint("brass_sign", _sheet("block/bamboo_sign", _STANDING, _plaque, R[2], "brass", 1, spread=_BAMBOO))
    paint("brass_hanging_sign", _sheet("block/bamboo_hanging_sign", _HANGING, _plaque, R[2], "iron", 3))
    # old copper
    paint("old_copper", [_copper(s) for s in (1, 2, 3)])
    paint("old_copper_cut", [_copper_cut(s) for s in (1, 2)])
    # the small pieces
    paint("wainscot", _wainscot())
    paint("brass_inlay", [_inlay(s) for s in (1, 2, 3)])
    paint("enamel_plate", _brushed("enamel", 32, noise=0.04))
    paint("enamel_sign", _sheet("block/oak_sign", _STANDING, _nameplate, E[0], "iron", 3))
    paint("enamel_hanging_sign", _sheet("block/oak_hanging_sign", _HANGING, _nameplate, E[0], "iron", 3))

    out = []
    for block in BLOCKS:
        shows = {ref: SHOWS[ref.rpartition("/")[2]] for ref in respack.block_pictures(K.game(), block)}
        # a block is mixed in as many versions as the least varied of its pictures has
        out.append(K.redirect(pack_dir, block, shows, variants=min(versions[name] for name in shows.values())))
    out.append(K.sounds(pack_dir, {event: [{"name": to, "type": "event"}] for event, to in SOUNDS.items()}))
    return out
