"""Work package materials/windows (plan ART-PLAN 6.2 lit and dark windows, 6.3 emission;
parts/materials.md section 5; card plan/packages/materials/windows.md).

Six windows, each a full glass block and a glass pane:

  lit (self-lit, the brightest things on a wall; the three are the three levels of sky/lights):
    WINDOW_LIT       amber, the filament glow itself               (whole window ~0.65)
    WINDOW_FROSTED   warm white, obscured glass                    (~0.54)
    WINDOW_CURTAIN   deep orange, a curtain drawn across the lamp  (~0.40)
  dark (hold the sky, no light of their own):
    WINDOW_DARK      glass with the blue of the sky in it, a glancing reflection here and there
    WINDOW_BLIND     a lowered blind behind dark glass
    SKYLIGHT         the one glass that is seen through (half opaque), in the net of the other five

The numbers are the grey of the whole picture, glazing bars included, on a scale of 0 to 1: what a
lit window shows on the screen, since it is drawn at full emission (agreed with c177, group g2 #82,
#89, #90).

The glazing bars are painted into the picture, one pixel of iron, and meet across the four edges so
that blocks join into one net; a window three blocks wide shows six lights across. The iron frames
of a window (arch head, outer frame, a transom) are props laid over these lines, not a second grid
(R1, c179 #14821). That holds for the roof light too: its heavy iron frame is the curb round the
whole light, which the roof builds; the picture carries the fine net only (review #1, c219).

A lit window is drawn in its own colours whichever way it faces: emission 15, the game's shading by
direction off, the darkening of corners off, the picture opaque. The main front faces east, where
the game would shade a face to 0.6 (c177, sky.md section 6), so the light and dark of a lit window
is painted here and nothing is left to the engine. The light a window throws on the wall around it
is the invisible light source sky/lights puts behind the glass; the glass only lights itself.

Two versions of the lit windows are compared (version="a" / "b"):

  a  small square lights, eight pixels each way, in a net of one pixel. Amber glass, each light a
     line paler at its head and a line deeper at its foot; milky frosted glass on which the bars
     throw a soft edge; a cloth curtain in folds.
  b  tall lights, two to a block: slender uprights and a transom of two pixels between blocks. The
     light pools at the head of each pane and deepens at its foot; frosted glass with a broken
     surface; a venetian blind with the lamp behind it.

The dark windows are painted one way; their bars follow the version, so that lit and dark windows
of one front share a net. Both nets cover the same share of the glass (60 of 256 pixels), which
keeps the two versions on the same ladder of brightness.
"""
import numpy as np

from artkit import respack

from ..common import blocks as B
from ..common import palette as P
from . import _kit as K

TILE = K.TILE                           # 16: one block face

# The blocks this package paints; while it does, the stand-ins drop them (materials/_standin.py).
BLOCKS = K.blocks(B.WINDOW_LIT, B.WINDOW_CURTAIN, B.WINDOW_FROSTED, B.WINDOW_DARK, B.WINDOW_BLIND, B.SKYLIGHT)

VERSIONS = ("a", "b")
VERSION = "a"                           # what the master scene shows until the review picks one

# A lit window: full emission, no shading by direction, no darkening of corners.
LIT = dict(emit=15, shade=False, ao=False)
# A dark window is an ordinary block: the game shades it and the sky lights it (c177's figures for
# the east front assume exactly that), and it carries no light of its own.
DARK = dict(emit=0)

BAR = ("iron", 1)                       # the glazing bar
SKYLIGHT_ALPHA = 128                    # half opaque (c177, g2 #90)
SKYLIGHT_SHEEN_ALPHA = 176              # the reflection in it hides a little more of what is behind

# Where the bars run, and the glass rectangles (x0, y0, x1, y1, inclusive) they leave.
_BARS = {"a": dict(cols=(0, 8), rows=(0, 8)), "b": dict(cols=(0, 8), rows=(0, 15))}
_LIGHTS = {"a": [(x, y, x + 6, y + 6) for y in (1, 9) for x in (1, 9)],
           "b": [(1, 1, 7, 14), (9, 1, 15, 14)]}


def _version(version):
    v = (version or VERSION).lower()
    if v not in VERSIONS:
        raise ValueError(f"windows: no version {version!r}; there are {', '.join(VERSIONS)}")
    return v


# ---- the picture, pixel by pixel ----------------------------------------------------------------------
def _glass(tone, alpha=255):
    """A picture of one colour of the palette."""
    px = np.zeros((TILE, TILE, 4), np.uint8)
    px[..., :3] = P.colour(*tone)
    px[..., 3] = alpha
    return px


def _fill(px, x0, y0, x1, y1, tone):
    """Recolour a rectangle (inclusive); what is outside the picture is left out. Alpha is kept."""
    x0, y0 = max(x0, 0), max(y0, 0)
    if x0 <= x1 and y0 <= y1:
        px[y0:y1 + 1, x0:x1 + 1, :3] = P.colour(*tone)


def _bars(px, version):
    """The glazing bars over a painted glass: whole columns and rows, opaque."""
    c = P.colour(*BAR)
    for x in _BARS[version]["cols"]:
        px[:, x, :3], px[:, x, 3] = c, 255
    for y in _BARS[version]["rows"]:
        px[y, :, :3], px[y, :, 3] = c, 255
    return px


def _stroke(px, light, x, y, n, tone, alpha=None):
    """A glancing stroke inside one light: n steps up and to the right from (x, y), two pixels wide.
    It never leaves its light, so no line runs on from one pane into the next. With `alpha`, the
    stroke is that opaque; without, the glass keeps its own."""
    x0, y0, x1, y1 = light
    for i in range(n):
        for dx in (0, 1):
            if x0 <= x + i + dx <= x1 and y0 <= y - i <= y1:
                px[y - i, x + i + dx, :3] = P.colour(*tone)
                if alpha is not None:
                    px[y - i, x + i + dx, 3] = alpha


# ---- lit windows: amber, warm white, deep orange -----------------------------------------------------
def lit_face(version="a"):
    """WINDOW_LIT: the glass is the plan's window amber (glow 2). The step above it is kept to a line
    at the head of each light and the palest step is not used at all: the whole window stays amber,
    the lamp shades stay the only near-white things in a view (c177, g2 #90). The step below it is a
    line at the foot of each light, so a pane runs from pale to deep and reads as glass with a lamp
    behind it, not as a flat sheet of light (review #1, c219); in the small lights of version a both
    are one pixel, the lightest form of what version b does in its tall ones."""
    px = _glass(("glow", 2))
    for x0, y0, x1, y1 in _LIGHTS[version]:
        head = 2 if version == "b" else 1                          # b: the light pools under the transom
        _fill(px, x0, y0, x1, y0 + head - 1, ("glow", 3))          # paler under the bar
        _fill(px, x0, y1, x1, y1, ("glow", 1))                     # deeper at the foot of the pane
    return _bars(px, version)


def frosted_face(version="a"):
    """WINDOW_FROSTED: opal glass, the second level of light. a: flat and milky, the bars throw a soft
    edge below and beside them. b: four pictures mixed by position, a broken surface of short strokes
    a step lighter and a step greyer, and the soft edge under the transom."""
    soft = ("cream", 0)                                            # a greyer warm white: opal in shadow
    if version != "b":
        px = _glass(("opal", 0))
        for x0, y0, x1, y1 in _LIGHTS[version]:
            _fill(px, x0, y0, x1, y0, soft)
            _fill(px, x0, y0, x0, y1, soft)
        return _bars(px, version)
    out = []
    for k in range(4):
        rng = np.random.default_rng(1100 + k)
        px = _glass(("opal", 0))
        for light in _LIGHTS[version]:
            x0, y0, x1, y1 = light
            _fill(px, x0, y0, x1, y0, soft)
            for i in range(6):
                tone = ("opal", 1) if i == 5 else soft
                _stroke_thin(px, (x0, y0 + 1, x1, y1), int(rng.integers(x0, x1 - 1)), int(rng.integers(y0 + 3, y1 + 1)),
                             int(rng.integers(2, 5)), tone)
        out.append(_bars(px, version))
    return out


def _stroke_thin(px, light, x, y, n, tone):
    """As _stroke, one pixel wide."""
    x0, y0, x1, y1 = light
    for i in range(n):
        if x0 <= x + i <= x1 and y0 <= y - i <= y1:
            px[y - i, x + i, :3] = P.colour(*tone)


def curtain_face(version="a"):
    """WINDOW_CURTAIN: the lamp behind a drawn curtain, the lowest level of light. The cloth is the
    deepest amber (glow 0); the step above it only on the lit edge of a fold or a slat, a brown of the
    same hue in the shadow beside it (c177, g2 #90). One picture each, so that a fold runs unbroken down
    a window and a slat across it. a: cloth in folds of uneven width. b: a venetian blind."""
    px = _glass(("glow", 0))
    lit, shadow = ("glow", 1), ("dark_wood", 4)
    if version == "b":
        for y in range(2, 15, 3):
            _fill(px, 0, y, TILE - 1, y, lit)                      # the lip of a slat
            if y + 1 < 15:
                _fill(px, 0, y + 1, TILE - 1, y + 1, shadow)       # the gap under it
    else:
        for x, tone in ((2, lit), (3, shadow), (6, lit), (7, shadow),
                        (9, shadow), (11, lit), (12, shadow), (14, lit), (15, shadow)):
            _fill(px, x, 0, x, TILE - 1, tone)
    return _bars(px, version)


# ---- dark windows: holding the sky -------------------------------------------------------------------
# What each light of the four pictures shows: the tone of its glass (a step of night_glass) and, for
# some, a glancing stroke one step lighter as (x, y, length): it starts x, y pixels right of and below
# the light's upper left corner and climbs to the right. Mostly the second step from the top; the
# lower three steps of the ramp would show as a black hole on the east front, where the sky leaves a
# quarter to a half of a colour (c177, g2 #82).
_DARK = {
    "a": [[(3, (1, 5, 4)), (3, None), (3, None), (2, None)],
          [(3, None), (3, (2, 4, 3)), (3, (0, 6, 3)), (3, None)],
          [(3, None), (2, None), (3, None), (3, (1, 6, 5))],
          [(4, None), (3, None), (3, (3, 5, 3)), (3, None)]],
    "b": [[(3, (1, 9, 5)), (3, None)],
          [(3, None), (3, (0, 12, 4))],
          [(2, None), (3, (2, 6, 4))],
          [(3, (0, 4, 3)), (3, None)]],
}


def dark_face(version="a"):
    """WINDOW_DARK: four pictures mixed by position. Each light is one tone of the sky as old glass
    holds it, now and then a darker pane, rarely a lighter one, and a short reflection across some.
    Opaque and without light: on the east front it shows about 0.08, under the wall and level with
    the sky overhead."""
    out = []
    for panes in _DARK[version]:
        px = _glass(("night_glass", 3))
        for light, (step, stroke) in zip(_LIGHTS[version], panes):
            x0, y0, x1, y1 = light
            _fill(px, x0, y0, x1, y1, ("night_glass", step))
            if stroke:
                x, y, n = stroke
                _stroke(px, light, x0 + x, y0 + y, n, ("night_glass", step + 1))
        out.append(_bars(px, version))
    return out


def blind_face(version="a"):
    """WINDOW_BLIND: a lowered blind behind dark glass: slats that hold a little of the sky, a darker
    gap under each. The darkest window, and still not a black hole (see _DARK)."""
    px = _glass(("night_glass", 3))
    for x0, y0, x1, y1 in _LIGHTS[version]:
        for y in range(y0 + 2, y1 + 1, 3):
            _fill(px, x0, y, x1, y, ("night_glass", 2))
    return _bars(px, version)


# The roof light: which lights of its four pictures carry a reflection, as (x, y, length) from the
# light's upper left corner (see _stroke). Fewer than a dark window has: a roof of them is calm, and
# what shows through the glass is the thing to look at.
_SKY = {
    "a": [[(1, 5, 4), None, None, None],
          [None, None, None, (0, 6, 5)],
          [None, (2, 4, 3), (1, 5, 3), None],
          [None, None, None, None]],
    "b": [[(1, 9, 5), None],
          [None, (0, 12, 5)],
          [(2, 6, 4), None],
          [None, None]],
}


def skylight_face(version="a"):
    """SKYLIGHT: the one glass that is seen through, for the canopy of the cable station, the roof
    lights and the small lights of the drum. Half opaque, the sky in it, in the same net of one-pixel
    bars as the other windows, so that a roof light and the windows under it are one glazing (review
    #1, c219: a frame of two pixels round every block read as a second, heavier grid). The heavy
    frame of a roof light is not in the picture: it is the iron curb round the whole light. A single
    block shows four panes, as every window here does; a round light wants a round frame of props
    over it (c206's cross-reading of this package). Four pictures mixed by position: a reflection
    across one light or two, or none, so a roof of them is not one stamp."""
    out = []
    for panes in _SKY[version]:
        px = _glass(("night_glass", 3), alpha=SKYLIGHT_ALPHA)
        for light, stroke in zip(_LIGHTS[version], panes):
            if stroke:
                x, y, n = stroke
                _stroke(px, light, light[0] + x, light[1] + y, n, ("night_glass", 4), alpha=SKYLIGHT_SHEEN_ALPHA)
        out.append(_bars(px, version))
    return out


def came():
    """The edge of a pane (where the game shows *_stained_glass_pane_top): the iron came seen edge on.
    The game takes the two middle columns of this picture for the two pixels of a pane's thickness:
    one a step lighter, so the edge reads as a strip of metal. One picture serves all six windows."""
    px = _glass(BAR)
    _fill(px, 7, 0, 7, TILE - 1, ("iron", 2))
    return px


# ---- what each role shows ----------------------------------------------------------------------------
NAMES = {B.WINDOW_LIT: "window_lit", B.WINDOW_FROSTED: "window_frosted", B.WINDOW_CURTAIN: "window_curtain",
         B.WINDOW_DARK: "window_dark", B.WINDOW_BLIND: "window_blind", B.SKYLIGHT: "window_skylight"}
CAME = "window_came"


def faces(version=None):
    """{role: (the picture or the pictures mixed by position, how it is redirected)} for a version."""
    v = _version(version)
    return {
        B.WINDOW_LIT: (lit_face(v), LIT),
        B.WINDOW_FROSTED: (frosted_face(v), LIT),
        B.WINDOW_CURTAIN: (curtain_face(v), LIT),
        B.WINDOW_DARK: (dark_face(v), DARK),
        B.WINDOW_BLIND: (blind_face(v), DARK),
        B.SKYLIGHT: (skylight_face(v), DARK),
    }


def pack(pack_dir, version=None):
    """Paint the six windows and redirect their block and their pane to them (parts/materials.md 5):
    the face picture on every glass face, the came on the edge of a pane. Lit windows at emission 15
    with the game's shading and corner darkening off; dark windows as the game draws a block."""
    v = _version(version)
    out = [f"windows: version {v}"]
    K.paint(pack_dir, CAME, came())
    for role, (pictures, how) in faces(v).items():
        name = K.paint(pack_dir, NAMES[role], pictures)
        for block in role.all():                                   # the full glass block and the pane
            shown = {ref: CAME if ref.endswith("_pane_top") else name
                     for ref in respack.block_pictures(K.game(), block)}
            out.append(K.redirect(pack_dir, block, shown, **how))
    return out
