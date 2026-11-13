"""Stand-in materials for every repainted block that no package of this folder has painted yet.

Each such block is redirected, so it is already told apart from the blocks it shares files with
(cast iron from verdigris, each stone from the others), and shows its vanilla pictures re-toned into
the ramp of its material: the shapes and cut-outs are the game's, the colours are the palette's. The
lit windows are plain lit panes, and the instrument panels get one plain cased dial, upright on the
side the block faces.

This is scaffolding (written into the pack by respack_redirect.py). It lets the other lines build and
render against roughly the right colours from the first day, and it runs redirect_block over every
block-state file of the occupancy table. A package that paints a family for real lists its blocks in
BLOCKS and they drop out of here; when the last one has, nothing is left to stand in for. The stand-in
pictures all start with "ph_", and none may be left in the finished map (left() says what still is one).
"""
import math

import numpy as np

from artkit import respack

from ..common import assembly
from ..common import blocks as B
from ..common import palette as P
from . import _kit as K

PREFIX = "ph_"
# Categories whose packages may paint blocks, and so take them out of the stand-ins by listing them
# in BLOCKS: this one, and the sky line for the blocks of the cloud sea (it tunes their colours
# together with the light of the sky; it paints through _kit.paint and _kit.redirect like everyone).
PAINTERS = ("materials", "sky")
# A lit window is the brightest thing on a wall (sky line): it shows the colours of its picture
# exactly, whatever way it faces. So it is drawn at full emission, without the game's shading by
# direction (a face to the east or west would show at 0.6) and without the darkening of corners, and
# it is not see-through (the game's stained glass is one flat colour at 40 to 64 percent).
LIT = {"emit": 15, "shade": False, "ao": False}
BULB_LIT = 8                # light_emission of the caged lamp when it is on (its own light level is only 4)
# A block of the cloud sea is one flat tone: a bank is modelled by which tone stands where, and a
# block of it must not show its edges.
FLAT = {"shade": False, "ao": False}


def _pane(name, **how):
    """A lit pane straight from the palette: brightest in the middle, a darker rim."""
    return lambda: P.mat(name, **how).paint(K.TILE, K.TILE, seed=1)


def _flat(name, step):
    return lambda: P.mat(name, base=step).paint(K.TILE, K.TILE)


# roles of the occupancy table -> the ramp their stand-in is toned into, and what else it needs
_ROLES = [
    ((B.ASHLAR_ROUGH, B.ASHLAR_FINE, B.ASHLAR_PANEL, B.ASHLAR_EMBLEM), "ashlar", {}),
    ((B.IRON_PLATE, B.IRON_RIVETED, B.IRON_CAST, B.IRON_GRATE, B.IRON_DOOR, B.IRON_HATCH, B.IRON_BARS,
      B.IRON_PIPE, B.IRON_ROD), "iron", {}),
    ((B.IRON_BULB,), "iron", {"lamp": True, "emit": lambda ref: BULB_LIT if "_lit" in ref else 0}),
    ((B.IRON_LANTERN,), "iron", {"lamp": True}),
    ((B.WINDOW_LIT,), "glow", dict(LIT, picture=("window_lit", _pane("glow")))),
    ((B.WINDOW_CURTAIN,), "glow", dict(LIT, picture=("window_curtain", _pane("glow", base=1)))),
    ((B.WINDOW_FROSTED,), "opal", dict(LIT, picture=("window_frosted", _pane("opal")))),
    ((B.WINDOW_DARK, B.WINDOW_BLIND, B.SKYLIGHT), "night_glass", {}),
    ((B.BRASS_PLATE, B.BRASS_PATTERN, B.BRASS_COLUMN, B.BRASS_RAIL, B.BRASS_GATE, B.BRASS_DOOR, B.BRASS_HATCH,
      B.BRASS_BUTTON, B.BRASS_SHELF, B.BRASS_INLAY, B.BRASS_SIGN), "brass", {}),
    ((B.OLD_COPPER, B.OLD_COPPER_CUT), "old_copper", {}),
    ((B.WAINSCOT,), "dark_wood", {}),
    ((B.ENAMEL_SIGN,), "enamel", {}),
] + [((block,), "cloud", dict(FLAT, picture=(f"cloud_{i}", _flat("cloud", i))))      # dark to light
     for i, block in enumerate(getattr(B, "CLOUD", ()))]
_PANELS = list(B.PANELS.values())


def claimed():
    """The blocks the real packages paint: what the BLOCKS lists of their modules name."""
    out = {}
    scene = __package__.rpartition(".")[0]
    for line in PAINTERS:
        for module in assembly.category(f"{scene}.{line}").parts():
            for block in getattr(module, "BLOCKS", ()):
                if block in out:
                    raise ValueError(f"{block} is painted by two packages: {out[block]} and {module.__name__}")
                out[block] = module.__name__
    return out


def left():
    """The blocks that still wear a stand-in: [(block, ramp, extras)], the panels as (block, None, {})."""
    taken = claimed()
    out = [(block, ramp, extra) for roles, ramp, extra in _ROLES for block in K.blocks(*roles) if block not in taken]
    out += [(block, None, {}) for block in _PANELS if block not in taken]
    missing = set(B.ids(B.REPAINTED)) - set(taken) - {b for b, _, _ in out}
    if missing:
        raise ValueError("the occupancy table lists repainted blocks that neither a package nor the stand-ins "
                         "know: " + ", ".join(sorted(missing)))
    return out


def tone(pixels, ramp, lamp=False):
    """A picture of the game in the colours of one ramp: its darker and lighter pixels land on darker
    and lighter steps around the step the material is usually painted in; transparency is kept.
    lamp=True sends its light (a lit filament, a flame: warm bright pixels, and whatever is brighter
    than oxidized copper ever gets, since the copper lantern burns green) to the glow ramp instead."""
    a = np.asarray(pixels).astype(np.float64)
    out = np.array(pixels, dtype=np.uint8)
    lum = a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114
    seen = a[..., 3] > 0
    out[~seen] = 0
    if not seen.any():
        return out
    lo, mid, hi = np.percentile(lum[seen], (5, 50, 95))
    step = max(9.0, (hi - lo) / 3.0)        # the picture's own contrast spans about three steps
    colours = np.array([P.colour(ramp, i) for i in range(len(P.RAMPS[ramp]))], dtype=np.uint8)
    index = np.clip(np.rint(P.mat(ramp).base + (lum - mid) / step), 0, len(colours) - 1).astype(int)
    out[..., :3] = np.where(seen[..., None], colours[index], 0)
    if lamp:
        hot = seen & (((a[..., 0] > 1.25 * a[..., 2]) & (lum > 150.0)) | (lum > 185.0))
        glow = np.array([P.colour("glow", i) for i in range(len(P.RAMPS["glow"]))], dtype=np.uint8)
        level = np.clip(np.rint(2 + (lum - 190.0) / 25.0), 1, len(glow) - 1).astype(int)
        out[..., :3][hot] = glow[level][hot]
    return out


def panel_case():
    return P.mat("iron_dark").paint(K.TILE, K.TILE, seed=7)


def panel_face():
    """One plain instrument: a porcelain dial in a brass ring on the casing plate."""
    px = panel_case()
    for y in range(K.TILE):
        for x in range(K.TILE):
            d = math.hypot(x - 7.5, y - 7.5)
            if d <= 4.6:
                px[y, x, :3] = P.colour("porcelain", 3)
            elif d <= 5.7:
                px[y, x, :3] = P.colour("brass", 2)
    for x, y in ((7, 8), (8, 7), (9, 6), (10, 5)):      # the needle
        px[y, x, :3] = P.colour("iron", 0)
    return px


def upright(ref, flat):
    """Glazed terracotta turns its picture differently on every side to make the swirl; an instrument
    stands upright, so the turns go."""
    for el in flat["elements"]:
        for face in el["faces"].values():
            face.pop("rotation", None)
    return flat


def pack(pack_dir):
    out, painted, skipped, by_ramp = [], set(), [], {}
    for block, ramp, extra in left():
        if ramp is None:                                # an instrument panel: the dial on the side it faces
            for name, picture in (("panel_case", panel_case), ("panel_face", panel_face)):
                if name not in painted:
                    K.paint(pack_dir, PREFIX + name, picture())
                    painted.add(name)
            # in the model the south side is the one the block state turns to `facing`
            K.redirect(pack_dir, block, {ref: {"south": PREFIX + "panel_face", "*": PREFIX + "panel_case"}
                                         for ref in respack.block_pictures(K.game(), block)}, edit=upright)
            by_ramp.setdefault("panels", []).append(block)
            continue
        if K.drawn_by_code(block):                      # signs: their look is not in a block model
            skipped.append(block)
            continue
        mapping = {}
        for ref in respack.block_pictures(K.game(), block):
            if "picture" in extra:                      # one painted picture on every face
                name, picture = PREFIX + extra["picture"][0], extra["picture"][1]
                if name not in painted:
                    K.paint(pack_dir, name, picture())
            else:                                       # the game's picture in our colours
                name = f"{PREFIX}{ramp}_{ref.rpartition('/')[2]}"
                if name not in painted:
                    pixels, meta = K.vanilla_picture(ref)
                    K.paint(pack_dir, name, tone(pixels, ramp, extra.get("lamp", False)), meta=meta)
            painted.add(name)
            mapping[ref] = name
        K.redirect(pack_dir, block, mapping, emit=extra.get("emit", 0), shade=extra.get("shade", True),
                   ao=extra.get("ao"))
        by_ramp.setdefault(ramp, []).append(block)
    for ramp, names in by_ramp.items():
        out.append(f"stand-in {ramp}: {len(names)} blocks ({', '.join(names)})")
    if skipped:
        out.append(f"stand-in: {len(skipped)} blocks drawn by the game's code, left as they are ({', '.join(skipped)})")
    return out
