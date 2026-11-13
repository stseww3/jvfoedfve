"""Work package materials/iron (plan ART-PLAN 6.2, materials.md section 4): cast iron.

Every oxidized_* copper block without a waxed_ twin is redirected away from verdigris to cast iron:
a blue-black ramp (I0..I6), rivets hugging the edges so neighbouring plates read as one bolted run,
a cast emblem, an open grating, a riveted door with a brass porthole, and the two lamps that glow.
The waxed_oxidized_* twins stay verdigris (common/blocks.py; _kit.PROTECT guards them).

The painted faces are designed here; the thin and shaped pieces (bars, chain, rod, grating, bulb,
lantern) keep the game model's own cut-out and are repainted over it, so their UVs still line up.
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


def _diamond(px, cx, cy, r, hi, lo):
    for y in range(TILE):
        for x in range(TILE):
            if abs(abs(x - cx) + abs(y - cy) - r) <= 0.6:
                _put(px, x, y, hi if (x - cx) + (y - cy) < 0 else lo)


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


def _cast(seed, motif):
    """IRON_CAST: a riveted plate with a raised cast motif -- the station emblem, or a lozenge."""
    px = _plate(seed, base=2, noise=0.10)
    _panel_frame(px)
    _rivets(px, _CORNERS)
    cx = cy = 7.5
    if motif == "emblem":                                   # ring + meridian + a star at upper right
        _ring(px, cx, cy, 4.3, _i(5), _i(1))
        for y in range(3, 13):                              # the meridian line, lit left, shadow right
            _put(px, 7, y, _i(5))
            _put(px, 8, y, _i(2))
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):   # the star
            _put(px, 11 + dx, 4 + dy, _i(6))
    else:                                                   # a raised lozenge with a boss
        _diamond(px, cx, cy, 5.5, _i(5), _i(1))
        _diamond(px, cx, cy, 2.6, _i(5), _i(1))
        _put(px, 7, 7, _i(6))
    return px


def _hatch_lid(seed):
    """IRON_HATCH variant 0: a riveted lid with a raised centre seam."""
    px = _plate(seed, base=3, noise=0.11)
    _panel_frame(px)
    _rivets(px, _CORNERS + [(8, 1), (8, 14)])
    for y in range(3, 13):                                  # a central lifting rib
        _put(px, 7, y, _i(5))
        _put(px, 8, y, _i(1))
    return px


def _hatch_louvre(seed):
    """IRON_HATCH variant 1: horizontal louvre slats in a riveted frame."""
    px = _plate(seed, base=2, noise=0.08)
    _panel_frame(px)
    _rivets(px, _CORNERS)
    for y in range(2, 14):
        band = (y - 2) % 3
        colour = _i(4) if band == 0 else _i(2) if band == 1 else _i(1)
        for x in range(2, 14):
            _put(px, x, y, colour)
    return px


def _door_bottom():
    """IRON_DOOR lower half: a riveted leaf with a brass porthole (its glow is M2's to light)."""
    px = _plate(5, base=3, noise=0.10)
    _panel_frame(px)
    _rivets(px, [(1, 1), (14, 1), (1, 7), (14, 7), (1, 14), (14, 14)])
    cx = cy = 7.5
    _disc(px, cx, cy, 3.4, _glow(3), _glow(1))              # the lit glass seen through the port
    _ring(px, cx, cy, 4.3, _brass(4), _brass(1), width=1.6)  # the brass rim
    for a in range(0, 360, 90):                             # four bolts around the rim
        _put(px, int(round(cx + 4.3 * math.cos(math.radians(a + 45)))),
             int(round(cy + 4.3 * math.sin(math.radians(a + 45)))), _i(6))
    return px


def _door_top():
    """IRON_DOOR upper half: a riveted leaf with a louvred transom."""
    px = _plate(6, base=3, noise=0.10)
    _panel_frame(px)
    _rivets(px, [(1, 1), (14, 1), (1, 9), (14, 9), (1, 14), (14, 14)])
    for y in range(3, 9):                                   # the transom vent
        colour = _i(4) if (y - 3) % 2 == 0 else _i(1)
        for x in range(3, 13):
            _put(px, x, y, colour)
    for x in (3, 12):                                       # its side stiles
        for y in range(3, 9):
            _put(px, x, y, _i(5))
    return px


# ---- the shaped and thin pieces (the game's cut-out, repainted) --------------------------------------
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


def _grate(seed):
    """IRON_GRATE: the game's grating, its bars in iron and its crossings caught by the light."""
    px, _ = _recolour("block/oxidized_copper_grate")
    seen = px[..., 3] > 0
    r = P.mat("iron", base=3, noise=0.0)                    # a steady base so the mesh does not shimmer
    flat = r.paint(TILE, TILE, seed=seed)
    for y in range(TILE):
        for x in range(TILE):
            if seen[y, x]:
                cross = seen[max(0, y - 1), x] and seen[min(TILE - 1, y + 1), x] \
                    and seen[y, max(0, x - 1)] and seen[y, min(TILE - 1, x + 1)]
                px[y, x, :3] = _i(5) if cross else flat[y, x, :3]
    return px


def _bars():
    """IRON_BARS: the game's bars in iron with one lit rail across them."""
    px, _ = _recolour("block/oxidized_copper_bars")
    seen = px[..., 3] > 0
    for y in (7, 8):                                        # the horizontal rail
        for x in range(TILE):
            if seen[y, x]:
                px[y, x, :3] = _i(4)
    return px


def _chain():
    """IRON_PIPE (the chain block): a thin cable with a flange ring every few pixels."""
    px, _ = _recolour("block/oxidized_copper_chain")
    seen = px[..., 3] > 0
    for y in range(TILE):
        if y % 4 == 0:                                      # the flange rings
            for x in range(TILE):
                if seen[y, x]:
                    px[y, x, :3] = _i(5)
    return px


def _rod():
    """IRON_ROD: the lightning-rod shape as a plain iron rod, bright down its centre."""
    px, _ = _recolour("block/oxidized_lightning_rod")
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
    K.paint(pack_dir, "iron_cast", [_cast(1, "emblem"), _cast(2, "lozenge")])
    K.paint(pack_dir, "iron_grate", [_grate(1), _grate(2)])
    K.paint(pack_dir, "iron_hatch", [_hatch_lid(1), _hatch_louvre(2)])
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
                       (B.IRON_HATCH, "iron_hatch"), (B.IRON_BARS, "iron_bars"),
                       (B.IRON_PIPE, "iron_chain"), (B.IRON_ROD, "iron_rod")):
        for block in K.blocks(role):
            out.append(K.redirect(pack_dir, block, _map(block, name)))
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
