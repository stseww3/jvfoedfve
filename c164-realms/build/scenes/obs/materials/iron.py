"""Work package materials/iron (plan ART-PLAN 6.2, materials.md section 4): cast iron.

Every oxidized_* copper block without a waxed_ twin is redirected away from verdigris to cast iron:
a blue-black ramp (I0..I6), rivets hugging the edges so neighbouring plates read as one bolted run,
a cast lozenge, an open grating, a riveted door with a brass porthole, and the two lamps that glow.
The waxed_oxidized_* twins stay verdigris (common/blocks.py; _kit.PROTECT guards them).

Every picture but the two lamps' is drawn here from nothing. The thin pieces (bars, pipe, rod,
grating) are drawn onto the pixels the game's own models read -- which columns and rows those are
is noted at each -- so the models stay the game's; the bulb and the lantern keep the game's picture,
taken over step for step into the iron ramp, their filament and slits into the glow ramp. One model
is touched: the thin edges of the game's trapdoor read the bottom rows of its picture upside down,
and the hatch's copies of its models show the picture's lit top rows there instead (_lips).
"""
import math

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


def _ring(px, cx, cy, r, hi, lo, width=1.0):
    for y in range(TILE):
        for x in range(TILE):
            if abs(math.hypot(x - cx, y - cy) - r) <= width / 2 + 0.25:
                _put(px, x, y, hi if (x - cx) + (y - cy) < 0 else lo)


def _cells(inside):
    """The pixels of the tile for which inside(dx, dy) holds, dx and dy measured from the tile centre."""
    c = (TILE - 1) / 2
    return [(x, y) for y in range(TILE) for x in range(TILE) if inside(x - c, y - c)]


def _relief(px, cells, shade=(), bright=()):
    """A cast figure standing proud of the plate: I5 all the way round, so a ring stays a closed ring
    instead of losing its far half in the plate and reading as a letter; I4 on the few cells turned
    from the light, I6 on the bright points, and a one-pixel I1 shadow thrown down and right of it."""
    figure = set(cells) | set(shade) | set(bright)
    for x, y in cells:
        _put(px, x, y, _i(5))
    for x, y in shade:
        _put(px, x, y, _i(4))
    for x, y in bright:
        _put(px, x, y, _i(6))
    for x, y in figure:
        if (x + 1, y + 1) not in figure:
            _put(px, x + 1, y + 1, _i(1))


def _disc(px, cx, cy, r, inner, edge):
    """A filled round boss: bright core, darker toward the rim."""
    for y in range(TILE):
        for x in range(TILE):
            d = math.hypot(x - cx, y - cy)
            if d <= r:
                _put(px, x, y, inner if d <= r - 1.3 else edge)


# ---- the flat plates (designed) ----------------------------------------------------------------------
def _plain(seed):
    """IRON_PLATE: a plain plate for casings and tanks -- brushed, no rivets, a shallow bevel so a
    wall of them reads as butted plates instead of going flat. Three variants, the brushing only."""
    px = _plate(seed, base=3, noise=0.14)
    _bevel(px)
    return px


def _riveted(seed):
    """IRON_RIVETED: a bolted plate, the bevel and eight rivets fixed, only the brushing varies."""
    px = _plate(seed, base=3, noise=0.11)
    _panel_frame(px)
    _rivets(px)
    return px


def _cast():
    """IRON_CAST: a riveted plate with a raised cast lozenge (one pixel thick, ten across) round a
    domed boss, the one picture of the block. Its field is smooth (a casting, not a rolled plate),
    so no brushing streak cuts across the motif.

    The block used to have a second picture, the station's emblem, mixed in by position: half the
    axle boxes round a dome came out with the emblem on them. A whole block has no state to tell
    two pictures apart, and the emblem stands only where someone puts it on purpose: on iron that
    is the props' brass roundel, hung where it is wanted (props/signs, which also keeps the framed
    sixteen-pixel figure that was drawn here)."""
    px = _plate(2, base=2, noise=0.0)
    _panel_frame(px)
    _rivets(px, _CORNERS)
    edge = _cells(lambda dx, dy: abs(dx) + abs(dy) == 5.0)
    boss = _cells(lambda dx, dy: abs(dx) + abs(dy) <= 2.0)
    lee = [(x, y) for x, y in boss if x + y >= TILE - 1]            # the half of the dome turned away
    _relief(px, edge + [cell for cell in boss if cell not in lee], shade=lee, bright=[(7, 7)])
    return px


def _hatch():
    """IRON_HATCH: a riveted lid with a raised rib down its middle, the one picture of the block.

    On edge it is a balustrade panel, lying it is a lid, a tie between rails, the blade of a
    louvre, and a run of them has to be one thing. The block used to have a second picture, a
    louvre, mixed in by position: half the panels of a balustrade came out louvred. It cannot go to
    the lying states either: the game does not turn a lying trapdoor with its facing, so the slats
    would run east-west on every wall of a belfry, along two of them and into the other two. A
    louvre on a wall is the panels' (B.PANELS["louvre"]) or the lower half of the door."""
    px = _plate(1, base=3, noise=0.11)
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


def _door_top():
    """IRON_DOOR upper half: a riveted plate with a brass porthole at eye height (its glow is M2's
    to light) and a brass lever under it on the latch side.

    The porthole's centre sits one pixel above the middle of the picture: a player's eye (1.62
    blocks up) is 62 % of the way up the upper block, a pixel higher still, well inside the glass.
    The game hinges the leaf on the picture's column 0, so the lever goes to the right. The plate
    under so much fitting is left unbrushed (a seed whose streaks all fall under the porthole)."""
    px = _plate(11, base=3, noise=0.10)
    _panel_frame(px)
    _rivets(px, _DOOR_RIVETS)
    cx, cy = 7.5, 6.5
    _disc(px, cx, cy, 3.4, _glow(3), _glow(1))              # the lit glass seen through the port
    _ring(px, cx, cy, 4.3, _brass(4), _brass(1), width=1.6)  # the brass rim
    for a in range(45, 360, 90):                            # four bolts around the rim
        _put(px, int(round(cx + 4.3 * math.cos(math.radians(a)))),
             int(round(cy + 4.3 * math.sin(math.radians(a)))), _i(6))
    for x, tone in ((10, 4), (11, 4), (12, 5)):             # the lever, its boss toward the latch edge
        _put(px, x, 13, _brass(tone))
        _put(px, x, 14, _i(1))
    return px


def _door_bottom():
    """IRON_DOOR lower half: the lower plate with a louvred vent (three slats) between two stiles,
    and a kick strip under it. The brushing's seed is one whose only streak
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
    on the side that takes the light, I2 on the other), the lit corner of every crossing I5, the
    holes clear. The plan's "4px mesh" is read as the pitch: the bars sit astride the tile's edges
    (one pixel on each tile) and its middle lines, so a floor of gratings is one unbroken mesh,
    a single grating set in a wall is closed all round by a one-pixel bar, and the holes are placed
    alike seen from either side, so the eye goes straight through. Variant 1 has lost the glint on
    four of its crossings, which keeps a floor of them from being one even field of dots."""
    px = np.zeros((TILE, TILE, 4), dtype=np.uint8)
    for y in range(TILE):
        for x in range(TILE):
            u, v = x % _MESH, y % _MESH
            across, down = v in (0, 3), u in (0, 3)         # on a bar running across, on one running down
            if across and down:
                tone = 5 if (u, v) == (3, 3) else 2 if (u, v) == (0, 0) else 3
            elif across:
                tone = 3 if v == 3 else 2
            elif down:
                tone = 3 if u == 3 else 2
            else:
                continue                                    # the hole
            _put(px, x, y, _i(tone))
    if variant:
        for x, y in _WORN:
            _put(px, x, y, _i(4))
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


_FLANGE = 4     # a flange ring every four pixels down the thin pipe


def _chain():
    """IRON_PIPE (the chain block): a thin pipe, no links -- I4 down its middle, I2 on the side that
    takes the light and I1 on the other, a flange ring of I5 across it every four pixels, so the
    rings carry on evenly from one block into the next. The game's chain is two crossed strips,
    each three pixels wide and the full height (columns 0 to 2 for one, 3 to 5 for the other);
    both get the same solid strip, so the pipe is the same from every side."""
    px = np.zeros((TILE, TILE, 4), dtype=np.uint8)
    for y in range(TILE):
        tones = (5, 5, 5) if y % _FLANGE == 0 else (2, 4, 1)
        for strip in (0, 3):
            for k, tone in enumerate(tones):
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


def _bulb(lit):
    """IRON_BULB: a caged bulb; lit sends the filament to the amber glow ramp."""
    ref = "block/oxidized_copper_bulb_lit" if lit else "block/oxidized_copper_bulb"
    px, _ = _recolour(ref, lamp=lit)
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
    K.paint(pack_dir, "iron_plate", [_plain(s) for s in (1, 2, 3)])
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
