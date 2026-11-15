"""Work package materials/iron (plan ART-PLAN 6.2, materials.md section 4): cast iron.

Every oxidized_* copper block without a waxed_ twin is redirected away from verdigris to cast iron:
a blue-black ramp (I0..I6), rivets hugging the edges so neighbouring plates read as one bolted run,
a cast diamond point, an open grating, a riveted door with a brass porthole, and the two lamps that glow.
The waxed_oxidized_* twins stay verdigris (common/blocks.py; _kit.PROTECT guards them).

Every picture but the lantern's is drawn here from nothing. The thin pieces (bars, pipe, rod,
grating) are drawn onto the pixels the game's own models read -- which columns and rows those are
is noted at each -- so the models stay the game's; the lantern keeps the game's picture, taken
over step for step into the iron ramp, its slits into the glow ramp. One model is touched: the
thin edges of the game's trapdoor read the bottom rows of its picture upside down, and the hatch's
copies of its models show the picture's lit top rows there instead (_lips).
"""
import numpy as np

from artkit import respack

from ..common import blocks as B
from ..common import palette as P
from . import _kit as K

TILE = K.TILE

# the blocks this package paints; nobody else may (families expand to stairs, slab)
BLOCKS = K.blocks(B.IRON_PLATE, B.IRON_RIVETED, B.IRON_CAST, B.IRON_GRATE, B.IRON_DOOR, B.IRON_HATCH,
                  B.IRON_BARS, B.IRON_PIPE, B.IRON_ROD, B.IRON_BULB, B.IRON_LANTERN)

BULB_EMIT = 8        # the lit caged bulb renders at this level (its world light is the game's own 4)
LANTERN_EMIT = 15    # the iron lantern is a first-rank light


def _i(n):
    return P.colour("iron", n)


def _glow(n):
    return P.colour("glow", n)


def _brass(n):
    return P.colour("brass", n)


# ---- pixel helpers -----------------------------------------------------------------------------------
def _put(px, x, y, rgb):
    if 0 <= x < TILE and 0 <= y < TILE:
        px[y, x, :3] = rgb
        px[y, x, 3] = 255


def _plate(seed, base=3, noise=0.14):
    """A brushed cast-iron face from the palette: a few flat tones, one-pixel streaks, a shallow bevel."""
    return P.mat("iron", base=base, noise=noise).paint(TILE, TILE, seed=seed).copy()


def _panel_frame(px):
    """A raised-plate border: light along the top and left, dark along the bottom and right."""
    for t in range(TILE):
        _put(px, t, 0, _i(4))
        _put(px, 0, t, _i(4))
        _put(px, t, TILE - 1, _i(1))
        _put(px, TILE - 1, t, _i(1))
    _put(px, 0, TILE - 1, _i(2))        # the two corners where light meets dark
    _put(px, TILE - 1, 0, _i(2))


def _bevel(px):
    """A shallow raised edge for a plain plate: the top and left a step lighter, the bottom and right
    a step darker, the corners left at base -- gentler than the riveted frame, no rivets. It keeps a
    wall of plain plates from reading flat (card materials/iron: IRON_PLATE has a shallow bevel)."""
    for t in range(1, TILE - 1):
        _put(px, t, 0, _i(4))
        _put(px, 0, t, _i(4))
        _put(px, t, TILE - 1, _i(1))
        _put(px, TILE - 1, t, _i(1))


# rivets hug the edge (four corners, four edge mids) so that across a seam two plates' rivets pair up
_RIVETS = [(1, 1), (8, 1), (14, 1), (1, 8), (14, 8), (1, 14), (8, 14), (14, 14)]
_CORNERS = [(1, 1), (14, 1), (1, 14), (14, 14)]


def _rivets(px, points=_RIVETS):
    for x, y in points:
        _put(px, x, y, _i(6))           # the lit head
        _put(px, x, y + 1, _i(1))       # a one-pixel shadow under it


def _cells(inside):
    """The pixels of the tile for which inside(dx, dy) holds, dx and dy measured from the tile centre."""
    c = (TILE - 1) / 2
    return [(x, y) for y in range(TILE) for x in range(TILE) if inside(x - c, y - c)]


# ---- the flat plates (designed) ----------------------------------------------------------------------
# the plain plate's brushing, a variant to the row: (row, first column, length, a step lighter or darker)
_BRUSHED = (((3, 9, 4, 1), (8, 3, 5, -1), (12, 8, 3, 1)),
            ((5, 3, 3, -1), (10, 9, 4, 1)),
            ((2, 4, 5, -1), (6, 10, 3, -1), (10, 2, 4, 1), (13, 9, 3, -1)),
            ((4, 7, 4, 1), (9, 2, 3, 1), (13, 4, 4, -1)),
            (),
            ())


def _plain(variant):
    """IRON_PLATE: a plain plate for casings and tanks -- no rivets, a shallow bevel so a wall of
    them reads as butted plates instead of going flat, and a few short brush marks. Six variants,
    the brushing only: four carry two to four marks, each on a row of its own with at least two
    clear rows to the next and no two variants' in the same place, and two carry none.

    The marks used to be the palette's own (noise 0.14: nine to the plate, on its grid of five
    pixels), three variants of them: they came to lie over one another to the right of the middle
    on all three, and from eight blocks a wall of plates was a wall of squares each stamped with
    the same three short bars (review 12 of 11-16, wall_plate)."""
    px = _plate(1, base=3, noise=0.0)
    _bevel(px)
    for y, x0, n, step in _BRUSHED[variant]:
        for x in range(x0, x0 + n):
            _put(px, x, y, _i(3 + step))
    return px


def _riveted(seed):
    """IRON_RIVETED: a bolted plate, the bevel and eight rivets fixed, only the brushing varies."""
    px = _plate(seed, base=3, noise=0.11)
    _panel_frame(px)
    _rivets(px)
    return px


_POINT = 5.0        # half the diagonal of the cast plate's diamond point: ten pixels from tip to tip
# its four facets by (in the lower half, in the right half), lit from the top left
_FACETS = {(False, False): 5, (False, True): 4, (True, False): 3, (True, True): 1}


def _cast():
    """IRON_CAST: a riveted plate with a diamond point cast on it -- a low four-sided pyramid on a
    lozenge ten pixels across, each facet one flat tone (I5 on the one that faces the light, I4 and
    I3 on the two beside it, I1 on the one turned away), its shadow one pixel down and right of it;
    the one picture of the block. The field is smooth (a casting, not a rolled plate) and a step
    darker than the plates', so the whole picture stays under theirs.

    The lozenge used to be a thin ring round a domed boss with a glint on it, and a row of them over
    a door was a row of eyes (the pictures of 11-15). A solid point has neither ring nor pupil, and
    its four facets say where the light comes from for as far as the block can be told apart.

    The block used to have a second picture, the station's emblem, mixed in by position: half the
    axle boxes round a dome came out with the emblem on them. A whole block has no state to tell
    two pictures apart, and the emblem stands only where someone puts it on purpose: on iron that
    is the props' brass roundel, hung where it is wanted (props/signs, which also keeps the framed
    sixteen-pixel figure that was drawn here)."""
    px = _plate(2, base=2, noise=0.0)
    _panel_frame(px)
    _rivets(px, _CORNERS)
    for x, y in _cells(lambda dx, dy: abs(dx) + abs(dy) <= _POINT):
        _put(px, x, y, _i(_FACETS[(y > TILE // 2 - 1, x > TILE // 2 - 1)]))
    for x, y in _cells(lambda dx, dy: dx > 0 and dy > 0 and dx + dy == _POINT + 1):
        _put(px, x, y, _i(1))
    return px


def _hatch():
    """IRON_HATCH: a riveted lid with a raised rib down its middle, the one picture of the block.

    On edge it is a balustrade panel, lying it is a lid, a tie between rails, the blade of a
    louvre, and a run of them has to be one thing. The block used to have a second picture, a
    louvre, mixed in by position: half the panels of a balustrade came out louvred. It cannot go to
    the lying states either: the game does not turn a lying trapdoor with its facing, so the slats
    would run east-west on every wall of a belfry, along two of them and into the other two. A
    louvre on a wall is the panels' (B.PANELS["louvre"]) or the lower half of the door.

    The plate is left unbrushed: a balustrade shows the one picture panel after panel, and a streak
    that comes back at the same place on every panel reads as a slot cut in each."""
    px = _plate(1, base=3, noise=0.0)
    _panel_frame(px)
    _rivets(px, _CORNERS + [(8, 1), (8, 14)])
    for y in range(3, 13):                                  # the rib
        _put(px, 7, y, _i(5))
        _put(px, 8, y, _i(1))
    return px


def _lips(ref, flat):
    """What redirect does to the game's trapdoor models before it maps the picture (its `edit`).

    Where it counts the game shows the whole picture the right way up (uv 0,0,16,16 in the 26.3
    models): on both sides of a standing trapdoor and on the top of a lying one. A standing panel
    is therefore lit from the top and the left like the plate it stands on, and nothing is turned
    there. The thin edges are another matter: the four edges of a lying trapdoor and the top edge
    of a standing one read the picture's bottom three rows upside down (uv 0,16,16,13), which puts
    the frame's dark lower lip uppermost -- an edge lit from below, and the edge is all that a
    louvre of lying hatches shows. Those edges read the top three rows the right way up instead:
    the frame's lit lip, the rivets under it, their shadows."""
    turned = 0
    for box in flat["elements"] or []:
        for face in box["faces"].values():
            if face.get("uv") == [0, 16, 16, 13]:
                face["uv"] = [0, 0, 16, 3]
                turned += 1
    if not turned:
        raise ValueError(f"{ref}: no edge of this model reads the picture's bottom rows upside down any more; "
                         "look at the game's trapdoor models again before the hatch is redirected")
    return flat


# the door's two plates carry the same six rivets, so down each side they pair up across the seam
_DOOR_RIVETS = [(1, 1), (14, 1), (1, 7), (14, 7), (1, 14), (14, 14)]


# the porthole as it sits in the door's upper picture: R its brass rim, B a bolt on the rim, r the
# reveal inside the rim, g the glass. Ten pixels across, drawn cell by cell: a ring this small comes
# out lopsided when it is taken from a radius
_PORT = ("...RRRR...",
         ".BRrrrrRB.",
         ".RrggggrR.",
         "RrggggggrR",
         "RrggggggrR",
         "RrggggggrR",
         "RrggggggrR",
         ".RrggggrR.",
         ".BRrrrrRB.",
         "...RRRR...")
_PORT_AT = (3, 2)       # its top left corner; the centre comes to (7.5, 6.5)


def _hinge(px, y):
    """A strap hinge on the door's hinge edge (the picture's column 0): three pixels of strap, the
    bolt at its inner end, a one-pixel shadow under it."""
    for x, tone in ((0, 5), (1, 5), (2, 6)):
        _put(px, x, y, _i(tone))
        _put(px, x, y + 1, _i(1))


def _door_top():
    """IRON_DOOR upper half: a riveted plate with a brass porthole at eye height (its glow is M2's
    to light), a brass lever under it on the latch side and a strap hinge on the other.

    The porthole's centre sits one pixel above the middle of the picture: a player's eye (1.62
    blocks up) is 62 % of the way up the upper block, a pixel higher still, well inside the glass.
    The game hinges the leaf on the picture's column 0, so the lever goes to the right. The plate
    under so much fitting is left unbrushed (a seed whose streaks all fall under the porthole).

    The porthole is a window, not a lamp: a one-pixel rim of aged brass (lit above and to the left,
    dark below and to the right, a bolt at each quarter), inside it the rim's reveal lit the other
    way round, and glass that lies in the rim's shadow along its top and left and lightens toward
    the lower right. It carries no highlight and no figure; the first one had a pale core on a
    thick uneven ring, which read as a badge."""
    px = _plate(11, base=3, noise=0.10)
    _panel_frame(px)
    _rivets(px, _DOOR_RIVETS)
    x0, y0 = _PORT_AT
    cells = {(x0 + x, y0 + y): mark for y, row in enumerate(_PORT) for x, mark in enumerate(row) if mark != "."}
    glass = {cell for cell, mark in cells.items() if mark == "g"}

    def depth(x, y, dx, dy):                                # the glass between a pixel and the rim that way
        n = 0
        while (x + (n + 1) * dx, y + (n + 1) * dy) in glass:
            n += 1
        return n

    for (x, y), mark in cells.items():
        lit = x + y < x0 + y0 + len(_PORT) - 1              # up and left of the diagonal through the centre
        if mark == "g":
            rgb = _glow(min(2, depth(x, y, 0, -1), depth(x, y, -1, 0)))
        elif mark == "r":
            rgb = _brass(0 if lit else 2)
        elif mark == "B":
            rgb = _brass(4)
        else:
            rgb = _brass(3 if lit else 1)
        _put(px, x, y, rgb)
    for x, tone in ((10, 4), (11, 4), (12, 5)):             # the lever, its boss toward the latch edge
        _put(px, x, 13, _brass(tone))
        _put(px, x, 14, _i(1))
    _hinge(px, 3)
    return px


def _door_bottom():
    """IRON_DOOR lower half: the lower plate with a louvred vent (three slats) between two stiles,
    a kick strip under it and the second strap hinge, as far from the door's foot as the upper one
    is from its head. The brushing's seed is one whose only streak
    left in sight is a dark scuff along the kick strip: a streak beside the vent would run on
    from a slat's lip and read as a slat reaching the door's edge."""
    px = _plate(3, base=3, noise=0.10)
    _panel_frame(px)
    _rivets(px, _DOOR_RIVETS)
    for y in range(3, 12):
        tone = (4, 2, 1)[(y - 3) % 3]                       # each slat: a lit lip, its face, the gap
        for x in range(4, 12):
            _put(px, x, y, _i(tone))
        for x in (3, 12):                                   # the side stiles
            _put(px, x, y, _i(5))
    _hinge(px, TILE - 4)
    return px


# ---- the thin pieces (drawn onto the pixels the game's models read) and the two lamps ----------------
def _recolour(ref, lamp=False):
    """A game picture in cast iron: each opaque pixel to the iron step nearest its brightness, its
    cut-out kept. lamp=True sends the warm, bright pixels (a filament, a flame) to the glow ramp."""
    px, meta = K.vanilla_picture(ref)
    px = np.asarray(px, dtype=np.uint8).copy()
    rgb = px[..., :3].astype(np.float64)
    seen = px[..., 3] > 0
    out = px.copy()
    out[~seen] = 0
    if not seen.any():
        return out, meta
    lum = rgb @ np.array([0.299, 0.587, 0.114])
    lo, mid, hi = np.percentile(lum[seen], (5, 50, 95))
    step = max(9.0, (hi - lo) / 3.0)
    iron = np.array([_i(n) for n in range(7)], dtype=np.uint8)
    idx = np.clip(np.rint(3 + (lum - mid) / step), 0, 6).astype(int)
    out[..., :3] = np.where(seen[..., None], iron[idx], 0)
    if lamp:
        warm = seen & (((rgb[..., 0] > 1.15 * rgb[..., 2]) & (lum > 120.0)) | (lum > 170.0))
        glow = np.array([_glow(n) for n in range(5)], dtype=np.uint8)
        level = np.clip(np.rint(1 + (lum - 150.0) / 22.0), 0, 4).astype(int)
        out[..., :3][warm] = glow[level][warm]
    return out, meta


_MESH = 4                                   # the grating's pitch: a two-pixel bar, a two-pixel hole
_WORN = [(7, 3), (15, 7), (3, 11), (11, 15)]    # the crossings whose glint the second variant has lost


def _grate(variant):
    """IRON_GRATE: an open grating -- a square mesh on a four-pixel pitch, bars two pixels thick (I3
    on the side that takes the light, I2 on the other), the lit corner of every crossing I4, the
    holes clear. The plan's "4px mesh" is read as the pitch: the bars sit astride the tile's edges
    (one pixel on each tile) and its middle lines, so a floor of gratings is one unbroken mesh,
    a single grating set in a wall is closed all round by a one-pixel bar, and the holes are placed
    alike seen from either side, so the eye goes straight through. Variant 1 has lost the glint on
    four of its crossings, which keeps a floor of them from being one even field of dots.

    The glint was I5, two steps over the bar: the edge of a gallery floor, sixteen crossings to the
    block seen level, came out as a band of light dots (the pictures of 11-15, gallery_front)."""
    px = np.zeros((TILE, TILE, 4), dtype=np.uint8)
    for y in range(TILE):
        for x in range(TILE):
            u, v = x % _MESH, y % _MESH
            across, down = v in (0, 3), u in (0, 3)         # on a bar running across, on one running down
            if across and down:
                tone = 4 if (u, v) == (3, 3) else 2 if (u, v) == (0, 0) else 3
            elif across:
                tone = 3 if v == 3 else 2
            elif down:
                tone = 3 if u == 3 else 2
            else:
                continue                                    # the hole
            _put(px, x, y, _i(tone))
    if variant:
        for x, y in _WORN:
            _put(px, x, y, _i(3))
    return px


_UPRIGHTS = (2, 7, 12)      # where the game's bars stand: its post and its end caps read columns 7 and 8


def _bars():
    """IRON_BARS: a railing -- three thin uprights (I3 on the lit side, I2 on the other) under one
    handrail along the top, its upper edge catching the light (I5), and nothing else across them.
    The uprights stand where the game's own do, so the post, the caps and the two half panes of
    its model still find them. The rail runs the full width: a run of railing carries one unbroken
    handrail into its end posts, and bars set two high in a window opening get a middle bar and a
    top bar.

    Nothing crosses the uprights lower down, not even a collar on each: seen from far below (the
    arrival view looks up through the railing of the upper terrace at the entrance) whatever lies
    across a railing at half its height draws a line over what stands behind it, where the
    handrail at the top comes to lie along the building's string course (the second reviewer's
    reckoning, g2 11-15 18:50).

    Its tones average the plates' (2.8 against 2.9): the game's picture, taken over step for step,
    stood a whole step lighter than the plate beside it (the cross-reading of the placeholders)."""
    px = np.zeros((TILE, TILE, 4), dtype=np.uint8)
    for x in _UPRIGHTS:
        for y in range(TILE):
            _put(px, x, y, _i(3))
            _put(px, x + 1, y, _i(2))
    for x in range(TILE):
        _put(px, x, 0, _i(5))
        _put(px, x, 1, _i(2))
    return px


# the thin pipe across its three pixels: the shaft, and the two flanges of a joint (the one at the foot
# of a length, the one at the head of the next)
_SHAFT = (2, 4, 1)
_FLANGES = {TILE - 1: (5, 5, 5), 0: (4, 5, 2)}


def _chain():
    """IRON_PIPE (the chain block): a thin pipe, no links -- I4 down its middle, I2 on the side that
    takes the light and I1 on the other -- in lengths of one block, flanged at both ends: where two
    blocks meet, the last row of one and the first of the next make a joint two pixels deep, the
    upper flange I5 across, the lower one shaded like the shaft, only lighter. Nothing else crosses
    the pipe. It used to carry a ring every four pixels: four light bars to the block made a
    ladder of it close to and a dotted light line from the courtyard, lighter than the plates it
    ran along (3.0 against 2.9; now 2.6). The game's chain is two crossed strips, each three pixels
    wide and the full height (columns 0 to 2 for one, 3 to 5 for the other); both get the same
    solid strip, so the pipe is the same from every side."""
    px = np.zeros((TILE, TILE, 4), dtype=np.uint8)
    for y in range(TILE):
        for strip in (0, 3):
            for k, tone in enumerate(_FLANGES.get(y, _SHAFT)):
                _put(px, strip + k, y, _i(tone))
    return px


def _rod():
    """IRON_ROD (the lightning rod's shape): a plain rod, lit down one side (I5) and dark down the
    other (I1) -- its shaft is two pixels thick, so "bright down the middle, dark at the edge"
    comes to those two columns -- under a small square cap with a lit corner. The game's model
    reads the cap from the top-left four by four and the shaft from columns 0 and 1 below it."""
    px = np.zeros((TILE, TILE, 4), dtype=np.uint8)
    cap = ((4, 4, 4, 2),
           (4, 5, 4, 2),
           (4, 4, 3, 2),
           (2, 2, 2, 1))
    for y, row in enumerate(cap):
        for x, tone in enumerate(row):
            _put(px, x, y, _i(tone))
    for y in range(len(cap), TILE):
        _put(px, 0, y, _i(5))
        _put(px, 1, y, _i(1))
    return px


_CAGE = (5, 10)     # the bulb's guard: a bar across and a bar down at each, panes of three, four and three pixels


def _bulb(lit):
    """IRON_BULB: a caged lamp -- the cast plate's body (its raised border, its four corner rivets)
    round a glass of twelve pixels, and before the glass a guard of two bars across and two down,
    one pixel each: nine panes. Lit, the eight outer panes are one amber (G1), the middle one a
    step lighter with the filament in its heart (G4), the bars dark against them (I1). Unlit, the
    panes are dark glass that holds the night (night_glass, the middle one a step lighter, the
    dead bulb in it) and the bars take the body's tone.

    The picture used to be the game's, taken over into the iron ramp: its guard is one bar across
    and one down through the middle, and before the lit glass that was a dark plus on an orange
    square at any distance (review 12 of 11-16, red line 8). The outer panes share one tone, so
    that the lighter ones do not draw a plus of light round the middle either: at stamp size the
    lamp is an amber square with a light heart and a faint grid over it."""
    px = _plate(1, base=3, noise=0.0)
    _panel_frame(px)
    _rivets(px, _CORNERS)
    if lit:
        pane, middle, heart, bar = _glow(1), _glow(2), _glow(4), _i(1)
    else:
        pane, middle, heart = (P.colour("night_glass", n) for n in range(3))
        bar = _i(3)
    lo, hi = _CAGE
    for y in range(2, TILE - 2):
        for x in range(2, TILE - 2):
            if x in _CAGE or y in _CAGE:
                rgb = bar
            elif lo < x < hi and lo < y < hi:
                rgb = heart if lo + 1 < x < hi - 1 and lo + 1 < y < hi - 1 else middle
            else:
                rgb = pane
            _put(px, x, y, rgb)
    return px


def _lantern():
    """IRON_LANTERN: the copper lantern as iron sheet with glowing slits; its sheet is 16x48."""
    return _recolour("block/oxidized_copper_lantern", lamp=True)


# ---- assemble the pack -------------------------------------------------------------------------------
def _map(block, name):
    """Map every picture a block shows to one of ours (covers all faces, so redirect never complains)."""
    return {ref: name for ref in respack.block_pictures(K.game(), block)}


def pack(pack_dir):
    out = []
    K.paint(pack_dir, "iron_plate", [_plain(v) for v in range(len(_BRUSHED))])
    K.paint(pack_dir, "iron_riveted", [_riveted(s) for s in (1, 2, 3)])
    K.paint(pack_dir, "iron_cast", _cast())
    K.paint(pack_dir, "iron_grate", [_grate(0), _grate(1)])
    K.paint(pack_dir, "iron_hatch", _hatch())
    K.paint(pack_dir, "iron_door_bottom", _door_bottom())
    K.paint(pack_dir, "iron_door_top", _door_top())
    K.paint(pack_dir, "iron_bars", _bars())
    K.paint(pack_dir, "iron_chain", _chain())
    K.paint(pack_dir, "iron_rod", _rod())
    K.paint(pack_dir, "iron_bulb", _bulb(False))
    K.paint(pack_dir, "iron_bulb_lit", _bulb(True))
    lantern_px, lantern_meta = _lantern()
    K.paint(pack_dir, "iron_lantern", lantern_px, meta=lantern_meta)

    for role, name in ((B.IRON_PLATE, "iron_plate"), (B.IRON_RIVETED, "iron_riveted"),
                       (B.IRON_CAST, "iron_cast"), (B.IRON_GRATE, "iron_grate"),
                       (B.IRON_BARS, "iron_bars"), (B.IRON_PIPE, "iron_chain"), (B.IRON_ROD, "iron_rod")):
        for block in K.blocks(role):
            out.append(K.redirect(pack_dir, block, _map(block, name)))
    for block in K.blocks(B.IRON_HATCH):
        out.append(K.redirect(pack_dir, block, _map(block, "iron_hatch"), edit=_lips))
    for block in K.blocks(B.IRON_DOOR):
        out.append(K.redirect(pack_dir, block, {ref: ("iron_door_top" if ref.endswith("_top") else "iron_door_bottom")
                                                 for ref in respack.block_pictures(K.game(), block)}))
    for block in K.blocks(B.IRON_BULB):
        out.append(K.redirect(pack_dir, block, {ref: ("iron_bulb_lit" if "_lit" in ref else "iron_bulb")
                                                for ref in respack.block_pictures(K.game(), block)},
                              emit=lambda ref: BULB_EMIT if "_lit" in ref else 0))
    for block in K.blocks(B.IRON_LANTERN):
        out.append(K.redirect(pack_dir, block, _map(block, "iron_lantern"), emit=LANTERN_EMIT))
    return out
