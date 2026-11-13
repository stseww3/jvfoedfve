"""Work package materials/windows (plan ART-PLAN 6.2 lit/dark windows + 6.3 emission;
parts/materials.md section 5; card plan/packages/materials/windows.md).

Six windows, each a full glass block and a glass pane:

  lit (self-lit, the brightest thing on a wall):
    WINDOW_LIT       amber, the filament-glow window                (whole-pane grey ~0.65)
    WINDOW_FROSTED   warm white, obscured/frosted glass             (~0.53)
    WINDOW_CURTAIN   deep orange, a drawn curtain, the dimmest lit  (~0.40)
  dark (hold the sky, no light of their own):
    WINDOW_DARK      a pane holding the blue of the sky, a glancing cold reflection
    WINDOW_BLIND     a lowered venetian blind, the darkest
    SKYLIGHT         the one see-through glass (alpha 0.5), a wide iron frame

The glazing bars are painted into the picture, 8 px to a light, one pixel of iron, the four edges
seamless so blocks join into one net (a three-wide arch shows six lights across). The model window
frames (arch head, outer frame, a transom) are A6's iron pieces, laid over these bars, not a second
grid (R1, c179 #14821). The light and dark of a lit window is painted in, not left to face shading:
the main front faces east, where the engine would shade a face to 0.6, so a lit window is drawn at
full emission with the shading and the corner darkening off and its picture opaque, and it then shows
its painted colours whichever way it faces (c177 sky.md section 6, #14980). The invisible world light
that washes the wall around a window is A2's (sky/lights); here the glass only lights itself.

Two versions of the lit windows are compared (card "version"): a is flat casement glazing with a
square grid and a cloth curtain; b is lamp-behind glazing (each light brighter at its centre) with a
venetian curtain. Both keep the same hues (amber / warm white / deep orange) and the same brightness
ladder. The dark windows have one version, shared by both.
"""
import numpy as np

from artkit import respack

from ..common import blocks as B
from ..common import palette as P
from . import _kit as K

TILE = K.TILE                           # 16: one block face

# The blocks this package paints; while it does, the stand-ins drop them (materials/_standin.py).
BLOCKS = K.blocks(B.WINDOW_LIT, B.WINDOW_CURTAIN, B.WINDOW_FROSTED, B.WINDOW_DARK, B.WINDOW_BLIND, B.SKYLIGHT)

VERSION = "a"                           # the default lit-window version; review picks it

# The light of a lit window: full emission, no face shading, no corner darkening, opaque picture.
LIT = dict(emit=15, shade=False, ao=False)
# A dark window is an ordinary block that holds the sky: the engine shades and dims it (c177's numbers
# for the east face already assume this), it carries no light of its own.
DARK = dict(emit=0)

MUNTIN = 1                              # P.colour("iron", 1): the glazing bar, a thin blue-black line
SKYLIGHT_ALPHA = 128                   # the one see-through glass (c177 #14983: 0.5)


# ---- the picture, pixel by pixel ----------------------------------------------------------------------
def _blank(step_ramp, alpha=255):
    px = np.zeros((TILE, TILE, 4), np.uint8)
    px[..., :3] = P.colour(*step_ramp)
    px[..., 3] = alpha
    return px


def _lines(px, cols=(), rows=(), ramp=("iron", MUNTIN), alpha=255):
    """Draw the glazing bars: full columns and rows of one colour. Columns at 0 and 8 (and rows the
    same) tile seamlessly into an eight-pixel net across neighbouring blocks."""
    c = P.colour(*ramp)
    for x in cols:
        px[:, x, :3] = c
        px[:, x, 3] = alpha
    for y in rows:
        px[y, :, :3] = c
        px[y, :, 3] = alpha


def _glass(px, mask, ramp):
    """Recolour the glass under a mask; the alpha already set by _blank is kept (the skylight is half
    transparent, the rest opaque)."""
    px[mask, :3] = P.colour(*ramp)


def _grid(version):
    """Where the glazing bars run. a: a square grid, two lights to a block. b: the same uprights with
    an extra rail between, horizontal factory-sash lights."""
    return dict(cols=(0, 8), rows=(0, 8))


def _yy_xx():
    yy, xx = np.mgrid[0:TILE, 0:TILE]
    return yy, xx


# ---- lit windows: amber, warm white, deep orange -----------------------------------------------------
def lit_face(version="a"):
    """WINDOW_LIT: amber filament glow. The glass is the plan's window amber (#ffc65a); the top row of
    each light lifts to the next step; the brightest step is kept out so it reads amber, not white.
    Whole-pane grey lands near 0.65 (c177 #15356: keep #ffc65a, the one near-white is the lamp shade)."""
    px = _blank(("glow", 2))                                   # #ffc65a
    yy, xx = _yy_xx()
    top = (yy % 8 == 1)                                        # the row under each bar
    if version == "b":
        centre = (np.abs((xx % 8) - 4) <= 1) & (np.abs((yy % 8) - 4) <= 1)   # a brighter heart, lamp behind
        _glass(px, centre, ("glow", 3))
    else:
        _glass(px, top, ("glow", 3))
    _lines(px, **_grid(version))
    return px


def frosted_face(version="a"):
    """WINDOW_FROSTED: warm white obscured glass, milkier and flatter than the amber window. opal with
    a scatter of frost specks that also pulls the grey down to ~0.53 (c177 #15356: 0.52-0.55)."""
    px = _blank(("opal", 0))                                   # #bfae8c
    yy, xx = _yy_xx()
    if version == "b":
        bloom = (np.abs((xx % 8) - 4) <= 1) & (np.abs((yy % 8) - 4) <= 1)
        _glass(px, bloom, ("opal", 1))
    # frost specks: a fixed scatter of the darkest iron, a few per light, to read as obscured glass
    spots = _speck_mask(seed=7, n_per_cell=4)
    _glass(px, spots, ("iron", 2))
    _lines(px, **_grid(version))
    return px


def curtain_face(version="a"):
    """WINDOW_CURTAIN: a drawn curtain behind the glass, the dimmest lit window, deep orange. Folds
    are glow[0] with a glow[1] highlight on their crests; whole-pane grey ~0.40 (c177 #15356: 0.38-0.42)."""
    px = _blank(("glow", 0))                                   # #c96a1c, deep orange cloth in shadow
    yy, xx = _yy_xx()
    if version == "b":
        crest = (yy % 8 == 4) & (xx % 3 == 1)                  # horizontal venetian slats catch the light
    else:
        crest = (xx % 8 == 4) & (yy % 3 == 1)                  # the bright edge of a vertical fold
    _glass(px, crest, ("glow", 1))                             # glow[1] only on the fold crests (c177 #15356)
    _lines(px, **_grid(version))
    return px


def _speck_mask(seed, n_per_cell):
    """A fixed scatter of pixels inside the glass of each eight-pixel light (never on a bar)."""
    rng = np.random.default_rng(seed)
    mask = np.zeros((TILE, TILE), bool)
    for cy in (0, 8):
        for cx in (0, 8):
            for _ in range(n_per_cell):
                x = cx + int(rng.integers(2, 8))
                y = cy + int(rng.integers(2, 8))
                mask[y, x] = True
    return mask


# ---- dark windows: holding the sky -------------------------------------------------------------------
def dark_face():
    """WINDOW_DARK: the sky caught in glass. night_glass top steps, a glancing diagonal reflection, a
    band pressed darker low down; opaque, no light of its own. On the east front it shows about 0.08
    (c177 #14983: times 0.25/0.29/0.44 for the east face)."""
    px = _blank(("night_glass", 3))                           # #3a4a80
    yy, xx = _yy_xx()
    _glass(px, (yy >= 11), ("night_glass", 2))               # pressed darker toward the sill
    _glass(px, (np.abs((xx + yy) - 13) <= 1), ("night_glass", 4))   # the diagonal reflection
    _lines(px, cols=(0, 8), rows=(0, 8))
    return px


def blind_face():
    """WINDOW_BLIND: a lowered venetian blind seen through dark glass, the darkest window. Horizontal
    slats of the lowest night_glass steps, a thin highlight on each slat lip."""
    px = _blank(("night_glass", 1))                          # #1c2548
    yy, _ = _yy_xx()
    _glass(px, (yy % 3 == 2), ("night_glass", 0))            # the shadow under each slat
    _glass(px, (yy % 3 == 0), ("night_glass", 2))            # the lip the sky just catches
    _lines(px, cols=(0, 8), rows=(0, 8))
    return px


def skylight_face():
    """SKYLIGHT: the one see-through glass, for the cable-car canopy, the drum's round lights and the
    roof lights. Half opaque, a wide iron frame (a 12-pixel light), the sky held in the glass."""
    px = _blank(("night_glass", 3), alpha=SKYLIGHT_ALPHA)
    yy, xx = _yy_xx()
    _glass(px, (np.abs((xx + yy) - 15) <= 1), ("night_glass", 4))   # a reflection streak
    px[..., 3][np.abs((xx + yy) - 15) <= 1] = 176                   # the reflection is less transparent
    frame = (xx < 2) | (xx >= TILE - 2) | (yy < 2) | (yy >= TILE - 2)   # a 2-pixel iron frame: a 12 px light
    _lines(px, cols=(), rows=())
    px[frame, :3] = P.colour("iron", 1)
    px[frame, 3] = 255
    return px


def came():
    """The edge of a pane (the vanilla *_stained_glass_pane_top): the iron came seen edge-on. One
    picture serves every window; a lit window's came shows its iron colour at full emission."""
    px = _blank(("iron", 1))
    yy, xx = _yy_xx()
    _glass(px, (xx == 0) | (yy == 0), ("iron", 2))           # a one-pixel highlight on two edges
    _glass(px, (xx == TILE - 1) | (yy == TILE - 1), ("iron", 0))
    return px


# ---- what each role shows ----------------------------------------------------------------------------
def _faces(version):
    """{role: (face picture, how to redirect it)}. The lit three change with the version; the dark
    three do not."""
    return {
        B.WINDOW_LIT: (lit_face(version), LIT),
        B.WINDOW_FROSTED: (frosted_face(version), LIT),
        B.WINDOW_CURTAIN: (curtain_face(version), LIT),
        B.WINDOW_DARK: (dark_face(), DARK),
        B.WINDOW_BLIND: (blind_face(), DARK),
        B.SKYLIGHT: (skylight_face(), DARK),
    }


def _name(role):
    return "window_" + {B.WINDOW_LIT: "lit", B.WINDOW_FROSTED: "frosted", B.WINDOW_CURTAIN: "curtain",
                        B.WINDOW_DARK: "dark", B.WINDOW_BLIND: "blind", B.SKYLIGHT: "skylight"}[role]


def pack(pack_dir, version=None):
    """Paint the six windows and redirect their block and pane to them (parts/materials.md 5):
    the face picture on every glass face, the came on a pane's edge. Lit windows at emission 15 with
    the engine's shading and corner darkening off; dark windows as the game draws them."""
    v = (version or VERSION).lower()
    if v not in ("a", "b"):
        raise ValueError(f"windows: no version {v!r} (a or b)")
    out = [f"windows: lit version {v}"]
    K.paint(pack_dir, "window_came", came())
    for role, (face, how) in _faces(v).items():
        name = _name(role)
        K.paint(pack_dir, name, face)
        for block in role.all():                             # the full glass block and the pane
            mapping = {}
            for ref in respack.block_pictures(K.game(), block):
                mapping[ref] = "window_came" if ref.rstrip("0123456789").endswith("_pane_top") else name
            out.append(K.redirect(pack_dir, block, mapping, **how))
    return out
