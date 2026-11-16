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

  the furnace window (A0's ruling, group g2 #37112; the two boiler bays of the power house only):
    WINDOW_FURNACE   the glow of the fires behind dirty glass: no curtain, no flame. Three blocks,
                     one to a row from the sill up, painted as one sheet: about 0.38 along the
                     sill, 0.29 in the second row, 0.18 in the third, whose head is near a dark
                     window (whole window ~0.28; the median pixel is a brown of 0.27 to 0.32)

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

The lining (A0's ruling, group g2 #32717). A lit window glows on every face of its blocks, so from
inside a room it would be a light box in the wall, while what it tells is a lamp in the room, seen
from outside. Its room side is therefore covered by a thin model that gives no light:

    WINDOW_LIT       night glass in the net of the dark windows: the same window as the dark one
                     beside it
    WINDOW_CURTAIN   the drawn curtain in its own colour by lamp light, warm and dark: cloth in
                     folds under its rail, with a hem (a), or the slats of a blind (b)
    WINDOW_FROSTED   the obscured glass with no light behind it: the pale, cold grey of milk glass
                     under the lamps of the room, no sky in it. In a room panelled in dark wood
                     (PANELLED: the two wing rooms) the same glass two steps deeper, level with
                     the panelling: there the pale one is the lightest plane of the room
    WINDOW_FURNACE   night glass, as WINDOW_LIT: the fires burn in the room

Only where somebody can stand behind the window: the star hall, the stair hall, the two wing rooms,
the dome room; main/shell.py's room_at() says which; the boiler bays of the power house; and the
lights of the cable car's winch house that site/cablecar.py's windows() marks lined. The
blocks of a window are not touched, so a front shows what it showed without the linings; LINING
switches them off, to prove that with two pictures. A lining is lit by the room, and a window's
lining as one sheet: all its pieces take the light of the room's cell before the middle of the
window (scenes/obs_mat_windows_in/placement.py holds line() to that, and to covering the glass).

    build(canvas, origin)                         the master scene: the lit windows of the main
                                                  building that have a room behind them, the
                                                  fire windows of the power house and the lined
                                                  lights of the station. The linings are this
                                                  line's entities, and it alone hangs them there
    line(canvas, cells, inward, glass, origin)    one window, for the test scene of a room or of
                                                  a house; returns the entities placed. Not for a
                                                  work package's build(): see line(). The box of
                                                  a panelled room says panelled=True
    models()                                      the lining models, names "mat_window_lining_..."
"""
import contextlib
import copy
import functools
import importlib

import numpy as np

from artkit import models as M
from artkit import respack

from ..common import blocks as B
from ..common import palette as P
from . import _kit as K

TILE = K.TILE                           # 16: one block face

FURNACE = tuple(B.WINDOW_FURNACE)       # the furnace window's three roles, the sill row first
FURNACE_ROWS = len(FURNACE)             # 3

# The blocks this package paints; while it does, the stand-ins drop them (materials/_standin.py).
BLOCKS = K.blocks(B.WINDOW_LIT, B.WINDOW_CURTAIN, B.WINDOW_FROSTED, B.WINDOW_DARK, B.WINDOW_BLIND, B.SKYLIGHT,
                  *FURNACE)

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


# ---- the furnace window: the fires of the boilers behind dirty glass ---------------------------------
# From the fire up into the soot: the two deepest ambers, the dark wood, the darkest iron (A0, g2
# #37112: no new colour, no signal red). A pixel stands between two neighbours of this ladder, and
# the dither decides which of the two it shows.
_HEAT = (("glow", 1), ("glow", 0), ("dark_wood", 4), ("dark_wood", 3), ("dark_wood", 2), ("dark_wood", 1),
         ("dark_wood", 0), ("iron", 0))
# Where a row of pixels stands on the ladder, by its height in pixels above the sill, 0 to 47.
# The first block is the fire's own band: the paler amber, plain in the lights that stand on the
# sill, with points of the deeper amber from its upper half on. Through the lower half of the
# second block the paler amber thins out into the deeper one; brown points come into that from
# the middle of the block and have all but taken it at its head. The third block is brown
# sinking into soot; its last row is all but the darkest iron, next to the dark glass that stands
# over it. A tone gives way to the next slowly at both ends and quickly between them, where the
# two are even and a dither is nothing but its own grain (c219, g2 #567).
# The levels are cr2's and a1's, read off the board's V6 (#78188, #78449). With the deeper amber
# along the sill and brown from the first block's upper half on, the window was a brown sheet
# with a dull foot there, 36 pixels of it over 0.5: the glass of the sill row is to stand at 0.60
# to 0.64 (Rec.709), that of the second row a quarter lighter than it was, the third as it was.
# The paler amber is all an orange of this hue has; the next step up is the yellow of a lamp, and
# a fire does not go there.
_RISE = ((0, 0.0), (7, 0.0), (11, 0.15), (15, 0.4), (19, 0.85), (21, 1.0), (23, 1.15), (27, 1.6), (31, 2.0),
         (39, 4.0), (47, 7.0))
# The order in which the pixels of a light turn to the darker of two tones: the sum of a rank for
# the column and a rank for the row, each a shuffle of 0 to 6 (c235's pre-review, g2 #571; A0
# #574). A row of a light holds each of the seven ranks once and a column holds them equally
# often, so a tone thins out evenly, with no fold down the glass and no slat across it.
# Which shuffles, the pictures decided. Two plain counts lay the points on a lattice: gauze. Two
# free shuffles (c235's 0361425 and 0526314 were the first tried) put pixels of one rank corner to
# corner: the points of a thin scatter line up into strokes, and with one pair for all lights the
# glass is hatched like a woven thing. So one of the two counts by three, forth or back, and the
# other goes by ones and twos and turns on its way: no two pixels of a rank touch, the lattice is
# broken where the shuffle turns, and where neighbouring ranks meet it is two points side by side,
# as dust lies. Every light takes another of these, starts its count elsewhere, and has the
# shuffle that turns across its columns or down its rows: each pane has its own stains.
_TURNING = ((0, 1, 6, 4, 2, 3, 5), (0, 2, 4, 5, 3, 1, 6), (0, 2, 4, 6, 5, 3, 1),
            (0, 2, 3, 1, 6, 4, 5), (0, 5, 4, 6, 1, 3, 2), (0, 6, 1, 3, 5, 4, 2))
_BY_THREE = ((0, 3, 6, 2, 5, 1, 4), (0, 4, 1, 5, 2, 6, 3))
# Dirty glass: a light now and then stands this much further up the ladder than its height says,
# half of it at its foot and half as much again under its head: the soot hangs from the bar, and
# a tall light is not one even scatter from foot to head. Along the sill that is where the fire is
# low: a light with points of the deeper amber among lights of the plain paler one, as a fire is
# strong in one place and low in the next (A0 #574). No two pictures of the sill row have it in
# the same lights, so a bay does not show one foot three times; and nothing there has a shape,
# least of all that of a flame. For each row of blocks from the sill up its pictures, and for each
# picture its lights in the order of _LIGHTS.
_SOOT = {
    "a": (((0.0, 0.2, 0.0, 0.0), (0.15, 0.0, 0.0, 0.1), (0.0, 0.0, 0.2, 0.0), (0.0, 0.15, 0.0, 0.1)),
          ((0.0, 0.0, 0.35, 0.0), (0.0, 0.4, 0.0, 0.0)),
          ((0.5, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.5))),
    "b": (((0.0, 0.15), (0.2, 0.0), (0.1, 0.0), (0.0, 0.1)),
          ((0.3, 0.0), (0.0, 0.35)),
          ((0.0, 0.5), (0.5, 0.0))),
}
_GRIME = 1.0                            # the corners of a light, where the soot sits: a whole step further up


def _heat(height, soot=0.0):
    """Where a pixel `height` pixels above the sill stands on _HEAT: (the step, how many sevenths
    of the way to the next)."""
    v = float(np.interp(height, [h for h, _ in _RISE], [v for _, v in _RISE])) + soot
    v = min(v, len(_HEAT) - 1.0)
    return int(v), int(round((v - int(v)) * 7))


def _ranks(serial, width, height):
    """The rank, 0 to 6, of every pixel of the light with this serial number: [row][column]. No two
    lights of a window are alike. The plain count turns back after seven pixels, so a tall light
    does not show one scatter twice."""
    turning = _TURNING[serial % len(_TURNING)]
    plain = [_BY_THREE[(serial // 2 + n // 7) % 2][n % 7] for n in range(max(width, height))]
    across, down = (turning, plain) if bin(serial).count("1") % 2 else (plain, turning)
    return [[(across[x % len(across)] + down[y % len(down)] + 3 * serial) % 7 for x in range(width)]
            for y in range(height)]


def _furnace(version, row, variant):
    """One picture of the furnace window: the block `row` rows above the sill, in its `variant`.
    Its tones hang on the height above the sill and on nothing else, so the three rows join into one
    sheet and the pictures of a row stand side by side without a seam."""
    px = _glass(BAR)
    for n, (x0, y0, x1, y1) in enumerate(_LIGHTS[version]):
        soot = _SOOT[version][row][variant][n]
        rank = _ranks((4 * row + variant) * len(_LIGHTS[version]) + n, x1 - x0 + 1, y1 - y0 + 1)
        for y in range(y0, y1 + 1):
            hung = soot * (0.5 + (y1 - y) / float(y1 - y0))
            for x in range(x0, x1 + 1):
                grime = _GRIME if x in (x0, x1) and y in (y0, y1) else 0.0
                step, sevenths = _heat(TILE * (row + 1) - 1 - y, hung + grime)
                px[y, x, :3] = P.colour(*_HEAT[min(step + (rank[y - y0][x - x0] < sevenths), len(_HEAT) - 1)])
    return _bars(px, version)


def furnace_face(version="a"):
    """WINDOW_FURNACE: the pictures of its three blocks, [row][picture], the sill row first. A row
    has several pictures (the sill row four, the others two), which the game mixes by position so
    that the three columns of a bay are not one stamp.

    The fires are low, behind the glass, and the glass is sooted: a band of the paler amber along
    the sill, deepening through the second row, thinning into brown and sinking into soot towards
    the head, where the third row meets the dark glass of the same bay. The three rows are one
    sheet (A0, g2 #37112): a tone hangs on the height above the sill, so no row repeats the row
    under it, which would show as three stripes. The soot is dither between neighbouring tones, a
    corner pixel in every light, and a light here and there that is dirtier than its height; along
    the sill such a light is where the fire is low. The net is that of the other windows. No
    curtain, no slat, no shape of a flame."""
    return [[_furnace(version, row, variant) for variant in range(len(_SOOT[version][row]))]
            for row in range(FURNACE_ROWS)]


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
FURNACE_NAMES = ("window_furnace_low", "window_furnace_mid", "window_furnace_high")
NAMES.update(zip(FURNACE, FURNACE_NAMES))
CAME = "window_came"


def faces(version=None):
    """{role: (the picture or the pictures mixed by position, how it is redirected)} for a version;
    the furnace window's three roles each with the pictures of their row."""
    v = _version(version)
    out = {
        B.WINDOW_LIT: (lit_face(v), LIT),
        B.WINDOW_FROSTED: (frosted_face(v), LIT),
        B.WINDOW_CURTAIN: (curtain_face(v), LIT),
        B.WINDOW_DARK: (dark_face(v), DARK),
        B.WINDOW_BLIND: (blind_face(v), DARK),
        B.SKYLIGHT: (skylight_face(v), DARK),
    }
    out.update((role, (pictures, LIT)) for role, pictures in zip(FURNACE, furnace_face(v)))
    return out


def pack(pack_dir, version=None):
    """Paint the windows and redirect their block and their pane to them (parts/materials.md 5):
    the face picture on every glass face, the came on the edge of a pane. Lit windows and the
    furnace window at emission 15 with the game's shading and corner darkening off; dark windows as
    the game draws a block."""
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


# ---- the lining: a lit window as the room behind it sees it ----------------------------------------
LINING = True                           # A0 #32717: on by default; unlined() builds without it
THICK = 0.5                             # how far a lining stands in front of the glass, in pixels
PIECE = 48 // TILE                      # a model reaches 48 pixels: a lining is cut into pieces of 3 blocks
# Blocks. The entity stands this far inside the room's cell, which lights it; the model is held
# back by as much, so its back lies on the glass itself. With a gap between the two, a line of
# sight along the wall passes behind the lining's edge and shows a hair of the lit glass: at the
# first rendering that was a bright line down the side of every lined window.
NUDGE = 0.01
MODEL = "mat_window_lining_"            # the category's prefix, and what the models are

# what a lit window is lined with, and in how many arrangements its pictures come
KINDS = {B.WINDOW_LIT: "lit", B.WINDOW_FROSTED: "frosted", B.WINDOW_CURTAIN: "curtain"}
# The furnace window is lined with night glass as well: the fires burn in the room, and from the
# room its three rows are the dark window they stand under.
KINDS.update((role, "lit") for role in FURNACE)
DEEP = "frosted_deep"                   # the lining of WINDOW_FROSTED in a panelled room: line(panelled=True)
# The pieces of a kind, by what is added to the model's name. Night glass comes in two arrangements
# of its pictures, so that the two halves of a tall window differ. A curtain's pieces differ by
# where they hang: the piece at the foot of a window carries the hem, the one at its head the
# rail, a window of one piece both, a piece between them neither.
PIECES = {"lit": ("", "_alt"), "frosted": ("",), DEEP: ("",), "curtain": ("", "_foot", "_head", "_whole")}
VARIANTS = {kind: len(names) for kind, names in PIECES.items()}

# Obscured glass with no light behind it, by the lamps of the room: the palest cold grey there is,
# and the soft edge the bars throw on it. Cold: beside the stone of the piers a neutral or a warm
# grey reads as slabs of that stone set in a grid, a cold one as glass with the night behind it.
UNLIT = ("snow", 4)
UNLIT_SOFT = ("snow", 2)
# The same glass in a room panelled in dark wood. A wall of dark wood shows a third of what the
# stone shows, and beside it the pale grey is the lightest large plane of the room: it takes the
# eye from what the room is there to show (m2's reading of the time room in the real building,
# #65185: the lining 0.097 where the panelling shows 0.067 and the wall of instruments 0.086). Two
# steps down the cold ramp the glass shows what the panelling and the night glass beside it show,
# and its hue alone says that it is glass. Which rooms: PANELLED, by main/shell.py's names.
UNLIT_DEEP = ("iron", 4)
UNLIT_DEEP_SOFT = ("iron", 3)
PANELLED = ("time room", "chart room")
# The curtain of version a by lamp light, from the hollow of a fold to its ridge: the cloth that
# shows deep orange with the lamp behind it is a faded red brown in front of it.
CLOTH = (("dark_wood", 2), ("old_copper", 0), ("old_copper", 1), ("old_copper", 2))
# The folds across it, each from its hollow over its ridge to the side turned away, as steps of
# CLOTH. Round, not grooved: no fold has more than two pixels of one step side by side. Uneven,
# and 48 pixels in all: the widest piece shows no fold twice.
_FOLDS = ("0123221", "012321", "0122321", "01321", "013221", "012321", "01231", "012321")
RAIL = (("brass", 1), ("brass", 3))     # what the curtain hangs from, and a ring on it
# The blind of version b, a wooden slat from its face down: the face twice, where it turns under,
# the shadow it throws on the next one. Dark wood: in brass the blind was the one saturated thing
# on the wall and read as if the lamp behind it still came through.
SLAT = (("dark_wood", 4), ("dark_wood", 4), ("dark_wood", 3), ("dark_wood", 1))
TAPE = 3                                # the two tapes a blind hangs in: so far in from its sides
_EDGE = {"lit": BAR, "frosted": BAR, DEEP: BAR, "curtain": CLOTH[0]}    # the half pixel a lining is thick


def unlit_face(version="a", deep=False):
    """The room side of WINDOW_FROSTED: the obscured glass as the room sees it at night, with no
    light behind it: the pale, cold grey of milk glass that only the lamps of the room fall on.
    Lighter than the night glass of a dark window by far, no sky in it, and still under the stone
    of the wall it stands in. Flat; under and beside the bars the same soft edge as on the lit
    side. One picture: the broken surface of version b shows by the light that falls through it,
    and none does. deep: the glass as it stands in a room panelled in dark wood (UNLIT_DEEP)."""
    glass, soft = (UNLIT_DEEP, UNLIT_DEEP_SOFT) if deep else (UNLIT, UNLIT_SOFT)
    px = _glass(glass)
    for x0, y0, x1, y1 in _LIGHTS[version]:
        _fill(px, x0, y0, x1, y0, soft)
        if version != "b":
            _fill(px, x0, y0, x0, y1, soft)
    return _bars(px, version)


def _folds(width):
    """The curtain across `width` pixels: for every column (the step of CLOTH it shows, 0 the
    hollow of a fold to 3 its ridge; which fold it belongs to; whether the fold is at its widest
    there or wider: the place where the cloth may hang a pixel fuller for a stretch)."""
    out, k = [], 0
    while len(out) < width:
        fold = [int(c) for c in _FOLDS[k % len(_FOLDS)]]
        ridge = fold.index(3)
        out += [(step, k, i == ridge + 1 and step == 2) for i, step in enumerate(fold)]
        k += 1
    return out[:width]


def _cloth(w, h, foot, head):
    """A curtain w by h blocks, drawn as one sheet: no fold comes twice and none is cut at a block.
    Cloth and not boards: a fold is round, from its hollow over the ridge that takes the light to
    the side turned away, and hangs a pixel fuller here and there; the foot piece ends in a hem
    that hangs in scallops just clear of the sill, the head piece is gathered under its rail."""
    wide, high = TILE * w, TILE * h
    px = np.zeros((high, wide, 4), np.uint8)
    px[..., 3] = 255
    stand = np.zeros((high, wide), int)
    cols = _folds(wide)
    for x, (step, k, fuller) in enumerate(cols):
        stand[:, x] = step
        if fuller:                                                 # the ridge two pixels wide for a stretch
            first = 5 + (7 + 11 * k + (17 if head else 0)) % max(high - 18, 1)
            stand[first:min(first + 6 + 3 * k % 5, high - 5), x] = 3
    if head:
        stand[2:4] = np.maximum(stand[2:4] - 1, 0)                 # gathered, in the shadow of the rail
    if foot:
        stand[high - 4] = np.maximum(stand[high - 4] - 1, 0)       # the seam of the hem
        steps = np.array([step for step, _, _ in cols])
        stand[high - 2] = np.where(steps >= 1, stand[high - 2], -1)    # the hem follows the folds:
        stand[high - 1] = np.where(steps >= 2, stand[high - 1], -1)    # it hangs lowest where they stand out
    for tone, colour in enumerate(CLOTH):
        px[stand == tone, :3] = P.colour(*colour)
    px[stand < 0, :3] = P.colour(*BAR)                             # under the hem: the foot of the window
    if head:
        px[0, :, :3] = P.colour(*CLOTH[0])
        px[1, :, :3] = P.colour(*RAIL[0])
        px[1, [x for x, (step, _, _) in enumerate(cols) if step == 3], :3] = P.colour(*RAIL[1])
    return px


def _blind(w, h, foot, head):
    """A venetian blind w by h blocks, let down and closed: wooden slats of four pixels, each with
    the shadow it throws on the next, and the two tapes it hangs in. The head piece begins with the
    head rail, the foot piece ends in the bottom rail, just clear of the sill. A window wider than
    a piece takes blinds side by side, each in its own tapes."""
    wide, high = TILE * w, TILE * h
    px = np.zeros((high, wide, 4), np.uint8)
    px[..., 3] = 255
    for y in range(high):
        px[y, :, :3] = P.colour(*SLAT[y % len(SLAT)])
    for x in (TAPE, wide - 1 - TAPE):
        for y in range(high):
            px[y, x, :3] = P.colour(*SLAT[min(y % len(SLAT) + 2, len(SLAT) - 1)])
    if head:
        px[0:3, :, :3] = P.colour(*SLAT[2])                        # the head rail, in its own shadow
        px[3, :, :3] = P.colour(*SLAT[3])
    if foot:
        px[high - 1, :, :3] = P.colour(*BAR)                       # under the bottom rail: the foot of the window
    return px


def lining_tiles(kind, version="a"):
    """The pictures a lining of glass is laid out of, one block face each. The lining of WINDOW_LIT
    is the dark window itself, its four pictures: night glass in the same net. A curtain is not
    laid out of blocks: see lining_picture()."""
    if kind == "lit":
        return dark_face(version)
    if kind in ("frosted", DEEP):
        return [unlit_face(version, deep=kind == DEEP)]
    raise ValueError(f"windows: no lining of glass {kind!r}; there are lit, frosted and {DEEP}")


# Which of a kind's pictures stands on which block of a piece: rows from the top, columns from the
# left as the room sees them. Two arrangements, so that the two halves of a tall window differ.
_MIX = (((0, 2, 1), (3, 1, 0), (2, 0, 3)),
        ((1, 3, 2), (2, 0, 1), (0, 2, 3)))


def lining_picture(kind, w, h, variant=0, version="a"):
    """The face of a piece w blocks wide and h high. Glass: the kind's pictures block by block,
    each the way a block's face shows it, so the net runs on into the windows beside the lined
    one. A curtain: one sheet with no glazing bars, the cloth hangs in front of them; a: cloth in
    folds, b: the slats of a blind. `variant` is the piece's place in PIECES."""
    if kind == "curtain":
        ends = PIECES[kind][variant]
        draw = _blind if version == "b" else _cloth
        return draw(w, h, foot=ends in ("_foot", "_whole"), head=ends in ("_head", "_whole"))
    tiles = lining_tiles(kind, version)
    px = np.zeros((TILE * h, TILE * w, 4), np.uint8)
    for j in range(h):
        for i in range(w):
            px[TILE * j:TILE * (j + 1), TILE * i:TILE * (i + 1)] = tiles[_MIX[variant][j][i] % len(tiles)]
    return px


class _Shown:
    """A painted picture as a material of artkit.models: the face it is given shows it as it is."""

    def __init__(self, name, pixels):
        self.name, self.pixels = name, pixels

    def paint(self, w, h, grain="u", seed=0):
        if self.pixels.shape[:2] != (h, w):
            raise ValueError(f"{self.name}: a picture of {self.pixels.shape[1]}x{self.pixels.shape[0]} "
                             f"on a face of {w}x{h}")
        return self.pixels.copy()


def lining_name(kind, w, h, variant=0):
    return f"{MODEL}{kind}_{w}x{h}{PIECES[kind][variant]}"


def _lining(kind, w, h, variant, version):
    """One piece, w by h blocks: a slab THICK deep that lies with its back on the glass. The anchor
    is the middle of the foot of its back. The picture is on the face that looks into the room,
    the model's +z; +x is the right hand of whoever looks at it. The back has no face."""
    name = lining_name(kind, w, h, variant)
    ramp, step = _EDGE[kind]
    m = M.Model(name)
    m.box((-TILE * w / 2.0, 0.0, 0.0), (TILE * w / 2.0, float(TILE * h), THICK),
          P.mat(ramp, kind="flat", base=step, bevel=0), skip="n",
          faces={"s": _Shown(f"{name}_face", lining_picture(kind, w, h, variant, version))})
    return m


@functools.lru_cache(maxsize=None)
def _linings(version):
    out = {}
    for kind, variants in VARIANTS.items():
        for variant in range(variants):
            for w in range(1, PIECE + 1):
                for h in range(1, PIECE + 1):
                    m = _lining(kind, w, h, variant, version)
                    out[m.name] = m
    return out


def models(version=None):
    """The lining models, {name: Model}: every piece of every kind (PIECES) in every size from 1 by
    1 to 3 by 3 blocks, 72 in all, so that a window of any size can be lined and the pack does not
    depend on which windows are lit. Their net follows the version of the windows; names and
    shapes are the same in both."""
    return dict(_linings(_version(version)))


def lining_of(glass):
    """The lining a glass takes ("lit", "frosted" or "curtain"); None for a glass that is not a lit
    window. `glass` is a role of the occupancy table or a block name, with or without namespace and
    state; the furnace window may be given as its three roles together or as any one of them.
    Whole blocks only: a pane stands in the middle of its cell, a lining lies on a face."""
    if isinstance(glass, (tuple, list)):
        glass = glass[0] if glass else None
    if isinstance(glass, B.Family):
        glass = glass.block
    name = str(glass or "").split(":", 1)[-1].partition("[")[0]
    for role, kind in KINDS.items():
        if name == role.block:
            return kind
    return None


def _first(n):
    """How many blocks the first piece takes of n in a row: as few pieces as PIECE allows, as even
    as they come (6 -> 3 + 3, 4 -> 2 + 2, 5 -> 3 + 2)."""
    pieces = -(-n // PIECE)
    return -(-n // pieces)


# the step from the glass into the room -> the yaw that points a model's +z that way
_YAW = {(0, 1): 0.0, (-1, 0): 90.0, (0, -1): 180.0, (1, 0): -90.0}


def _windows(cells):
    """The cells of a call split into windows: those of one plane that touch along an edge. Each
    is sorted, and they come in order, so that a build is the same every time."""
    left, out = set(cells), []
    while left:
        start = min(left)
        left.discard(start)
        window, edge = [start], [start]
        while edge:
            p, a, y = edge.pop()
            for near in ((p, a - 1, y), (p, a + 1, y), (p, a, y - 1), (p, a, y + 1)):
                if near in left:
                    left.discard(near)
                    window.append(near)
                    edge.append(near)
        out.append(sorted(window))
    return out


def _lamp_cell(window):
    """The cell of a window before which its lining takes its light: the one nearest to the middle
    of the window; of two that are as near the upper one, then the one further along the wall. A
    great window of 3 by 6 takes the fourth row of its middle column."""
    cols, rows = [a for _, a, _ in window], [y for _, _, y in window]
    ma, my = min(cols) + max(cols), min(rows) + max(rows)       # the middle, twice
    return min(window, key=lambda c: (abs(2 * c[1] - ma) + abs(2 * c[2] - my), -c[2], -c[1]))


def _held_at(model, anchor):
    """`model` held at another point of itself: M.display() puts a model's anchor on its entity, and
    reads the anchor, the name and the extent of the model, which a copy shares."""
    if tuple(anchor) == tuple(model.anchor):
        return model
    held = copy.copy(model)
    held.anchor = tuple(anchor)
    return held


def _hung(canvas):
    """The glass of a canvas that has its lining, {(x, y, z, dx, dz)}: the cell in the world and the
    step into the room on whose side the lining hangs. Kept on the canvas, so that a window is
    lined once however often it is asked for."""
    try:
        return canvas.__dict__.setdefault("_window_linings", set())
    except AttributeError:
        return set()            # a canvas that keeps nothing: every call lines


def line(canvas, cells, inward, glass, origin=(0, 0, 0), panelled=False):
    """Line the room side of one window. Returns the number of display entities placed: 0 for a
    window that is not lit, for one that has its lining already, and for every window while LINING
    is off.

    For a scene that builds a room or a house by itself: its test scene. A work package does not
    call this from its build(). In the master scene build() below lines every house, from the
    houses' tables; and a scene that builds the package without the materials line has no model
    for a lining to show (check.py fails it).

    cells     the glass of the window, [(x, y, z)]: whole blocks standing in one plane
    inward    the step from the glass into the room, (dx, dz): one block along x or along z
    glass     what the glass is: a role of the occupancy table (B.WINDOW_LIT, ...) or a block name,
              as main/facade.py's windows() gives it
    panelled  the room is panelled in dark wood: obscured glass takes its deep lining there
              (UNLIT_DEEP). build() says it for the rooms of PANELLED; the box of such a room
              says it here

    The window is cut into pieces of at most 3 by 3 blocks; a great window of 3 by 6 takes two.
    A display entity is lit by the cell it stands in, as a whole. So all the pieces of a window
    stand at one point, in the room's cell before the middle of the window, and each is held out
    from there to its place: the lining of a window is lit as one sheet, with no step of light
    where two pieces meet (c219's reading, g2 #38437). Cells that do not touch are windows of
    their own, each with its own light.

    The models are those of models(): a scene that calls this adds them to its build_models().
    """
    kind = lining_of(glass)
    if not LINING or kind is None:
        return 0
    if kind == "frosted" and panelled:
        kind = DEEP
    step = (int(inward[0]), int(inward[1]))
    if step not in _YAW:
        raise ValueError(f"windows.line: inward is one step along x or z, not {inward!r}")
    dx, dz = step
    ox, oy, oz = origin
    # every cell as (plane, along the wall, row): the wall runs along z where the room lies east or
    # west of the glass, along x where it lies north or south
    todo = {(int(x), int(z), int(y)) if dx else (int(z), int(x), int(y)) for x, y, z in cells}
    # glass that has its lining on this side takes no second one: whoever asks again places nothing
    hung = _hung(canvas)
    sides = {(p, a, y): (ox + (p if dx else a), oy + y, oz + (a if dx else p)) + step for p, a, y in todo}
    todo = {cell for cell, side in sides.items() if side not in hung}
    hung.update(sides[cell] for cell in todo)
    low = {}
    for p, a, y in todo:
        a0, y0 = low.get(p, (a, y))
        low[p] = (min(a0, a), min(y0, y))
    # A model's +x is the right hand of whoever looks at the lining from the room: up the wall's
    # axis where the room lies south or west of the glass, down it where it lies north or east.
    right = dz - dx
    pieces = _linings(_version(None))
    n = 0
    for window in _windows(todo):
        p, lamp_a, lamp_y = _lamp_cell(window)
        face = p + (1 if dx + dz > 0 else 0) + NUDGE * (dx + dz)    # the inner face of the glass
        along, height = lamp_a + 0.5, lamp_y + 0.5                  # the middle of that cell
        x, z = (face, along) if dx else (along, face)
        left, glazed = set(window), set(window)
        while left:
            _, a0, y0 = min(left, key=lambda c: (c[2], c[1]))       # the lowest row first, along it
            run = 1
            while (p, a0 + run, y0) in left:
                run += 1
            w = _first(run)
            rise = 1
            while all((p, a0 + i, y0 + rise) in left for i in range(w)):
                rise += 1
            h = _first(rise)
            left -= {(p, a0 + i, y0 + j) for i in range(w) for j in range(h)}
            if kind == "curtain":
                # which end of the window this piece is: nothing of the window under it, or over it
                foot = not any((p, a0 + i, y0 - 1) in glazed for i in range(w))
                head = not any((p, a0 + i, y0 + h) in glazed for i in range(w))
                variant = PIECES[kind].index(("", "_foot", "_head", "_whole")[foot + 2 * head])
            else:
                # which piece this is, counted along the wall and upwards: neighbours take different
                # arrangements of the pictures, like the squares of a chess board
                across, up = -((low[p][0] - a0) // PIECE), -((low[p][1] - y0) // PIECE)
                variant = (across + up) % VARIANTS[kind]
            model = pieces[lining_name(kind, w, h, variant)]
            # where the entity stands, in the piece's own measures: from the middle of its foot,
            # and NUDGE before its back
            held = (right * (along - (a0 + w / 2.0)) * TILE, (height - y0) * TILE, NUDGE * TILE)
            canvas.add_entity(ox + x, oy + height, oz + z, M.display(_held_at(model, held), yaw=_YAW[step]))
            n += 1
    return n


@contextlib.contextmanager
def unlined():
    """`with windows.unlined():` builds without the linings. For the twin of a scene that proves
    that a front looks the same with them and without."""
    global LINING
    was, LINING = LINING, False
    try:
        yield
    finally:
        LINING = was


# Where somebody can stand behind a window of the main building, while main/shell.py is not in the
# tree to be asked: {(front, storey): bays}, c231's reading of the shell (g2 #35461). The two wing
# rooms and the star hall behind the east front, the wing rooms behind the west front, the stair
# hall in the apse, the dome room behind the drum. Closed, and not lined: the end pavilions, the
# gables, the ground floor of the wings.
ROOM_BAYS = {("east", "main"): tuple(range(3, 16)), ("east", "base"): (8, 10),
             ("west", "main"): (3, 4, 5, 13, 14, 15), ("apse", "main"): (-1, 0, 1),
             ("drum", "drum"): tuple(range(20))}


def _package(line, name):
    """A work package of another line ("main", "facade"); None while it is not in the tree."""
    full = f"{__package__.rpartition('.')[0]}.{line}.{name}"
    try:
        return importlib.import_module(full)
    except ModuleNotFoundError as e:
        if e.name != full:
            raise               # it is there and fails to import something: say so
        return None


def _main(name):
    """A module of the main line; None while it is not in the tree."""
    return _package("main", name)


def _room(window):
    """The room somebody can stand in behind a window of the main building, by its name in
    main/shell.py's ROOMS; None where nobody can. What shell.room_at() says of the cell one step
    inside the glass, asked for the middle column (a column at a corner may stand against a wall:
    c231, g2 #35461) and the middle row. While the shell is not in the tree: "" for a room of
    ROOM_BAYS, which has no name there."""
    room_at = getattr(_main("shell"), "room_at", None)
    if room_at is None:
        return "" if window["bay"] in ROOM_BAYS.get((window["front"], window["storey"]), ()) else None
    cells, (dx, dz), (y0, y1) = window["cells"], window["inward"], window["y"]
    x, z = cells[len(cells) // 2]
    return room_at(x + dx, (y0 + y1) // 2, z + dz)


def _fire_windows():
    """The fire windows of the power house, as lined() gives a window: site/powerhouse.py's
    windows() of the storey "furnace", the three glowing rows of a boiler bay. The stokers stand
    behind them. Their lining is the fire window's, night glass, whichever glass stands in the
    bay: the house puts the curtain glass there until it switches to the fire window."""
    table = getattr(_package("site", "powerhouse"), "windows", None)
    if table is None:
        return []
    return [dict(w, glass=FURNACE[0]) for w in table() if w["storey"] == "furnace"]


def _station_windows():
    """The lights of the cable car's station whose room side is seen, as lined() gives a window:
    those of site/cablecar.py's windows() that it marks lined (the two tall lights of the winch
    house, seen from the platform through the house's open side)."""
    table = getattr(_package("site", "cablecar"), "windows", None)
    if table is None:
        return []
    return [w for w in table() if w.get("lined") and lining_of(w["glass"])]


def lined():
    """The windows that build() lines, [dict(front, bay, storey, cells, inward, y, glass, room)]:
    those of main/facade.py's windows() that are lit and have a room behind them (room: its name),
    the fire windows of the power house and the lined lights of the cable car's station (room: "")."""
    if not LINING:
        return []
    table = getattr(_main("facade"), "windows", None)
    main = []
    for w in table() if table else ():
        room = _room(w) if lining_of(w["glass"]) else None
        if room is not None:
            main.append(dict(w, room=room))
    return main + [dict(w, room="") for w in _fire_windows() + _station_windows()]


def build(canvas, origin=(0, 0, 0)):
    """The master scene: line the lit windows that have a room behind them, of the main building,
    of the power house and of the cable car's station (lined()). Returns the display entities
    placed. The materials are the first line to build, before any wall stands, so the windows are
    read from the houses' tables and not off the canvas: a house of another line gives its windows
    in a table and does not line them in its own build(), which runs in scenes that have no model
    of a lining (line()). The obscured glass of a room of PANELLED takes its deep lining."""
    n = 0
    for w in lined():
        y0, y1 = w["y"]
        n += line(canvas, [(x, y, z) for x, z in w["cells"] for y in range(y0, y1 + 1)],
                  w["inward"], w["glass"], origin, panelled=w["room"] in PANELLED)
    return n
