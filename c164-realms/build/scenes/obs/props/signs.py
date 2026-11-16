"""props/signs -- the station's emblem and the enamel signs (plan ART-PLAN 2, 5.1, 7.3; part
A6-props 2.8; card plan/packages/props/electrics-signs.md).

THE EMBLEM is the name of this observatory: a star about to cross the meridian in the eyepiece of a
transit instrument, the trade of an observatory that keeps the time (the director, g2 11-14). It is
seen over the entrance, in the paving of the court, on the iron gates and on the cable car, and it
has to read as one mark in all of them. This module holds the standard figure and is the one place
that draws it on a model:

    emblem_cells(16)    the figure on one block
    emblem_cells(16, framed=True)   the same on a tile that has a border of its own (the
                        nameplate of materials/panels)
    emblem_cells(48)    the figure on three blocks: the great piece over the entrance
    python -m scenes.obs.props.signs        prints them

  ring       its radius R is 6.5 sixteenths of the figure, measured to the middle of its line; the
             line is R / 6.5 thick (one pixel on 16, three on 48).
  meridian   upright through the ring's middle and out of the ring at both ends: it runs the whole
             height of the figure, 1.23 R above the middle and below it.
  star       inside the ring, right of its middle and above it by 0.4 R each way, touching neither
             the ring nor the line. On a small figure a dot of 2 x 2 (c219: a plus of five pixels
             reads as a small cross); on a large one a star of eight points round a solid middle,
             the same star as materials/brass paints for the floor. Never two bars crossing.
  never mirrored: the star is on the upper right for whoever looks at it, on both sides of a flag;
  in the paving north is up (site/court).
  cut in stone (materials/ashlar's emblem block): the ring and the meridian are these pixels; every
  cut has a lit lip a pixel to its right and below, as bright against the stone as the cut is dark,
  so the lip is part of the line and the star stands a column further right, x 10..11, to keep a
  plain pixel between itself and the meridian's lip. The same rule, not another figure.

The pieces (16 texels to the block, px = scale; a wall piece is hung by the middle of its back):

    emblem          the brass roundel, 1 x 1: lintels, gates, the cable car, indoors.
    great_emblem    the one great piece over the entrance, 3 x 3 (A0 #186), version A: the emblem
                    cast in brass, low relief, old brass, painted as the entrance lamps light it
                    from below.
    great_clock     the same seat, version B: a clock of the tower dials' family (machines/clock):
                    white enamel dial, black hands, a thin brass rim in a dark iron case; not lit
                    from inside.
                    Both are shown in the light of the entrance's lamps (SPEC, "shown"), which
                    the game does not carry that far up, and offer a wash for the stone round
                    them to the light line.
    plate_<label>   enamel plates: white figures on blue (numbers, arrows, N and S), black on white
                    with a red flash (voltage). Digits, signs and a letter or two, nothing else.
    station_board   the name board of the cable station, a block high and two and a half long, in
                    the plates' enamel: the emblem, which is the name, and the height of the place
                    in metres (HEIGHT), as the boards of mountain railways have it.
    flag, pole_*    the station's flag (blue, the emblem in cream) on a pole with a ball on top.

The great piece is hung by build() when DRESS is on, on the seat main/facade.emblem() gives,
version VERSION of it, the name board on the seat site/cablecar keeps for it (SIGN), and the
entrance's plate beside the main doorway (doorplate(): the plate "1", the house's number). For the
other lines:

    from scenes.obs.props import signs
    n += signs.great(canvas, seat, "emblem", origin)        # or "clock"; a seat as facade.emblem()'s
    n += signs.place(canvas, "emblem", (x, y, z), facing="east", origin=origin)
    n += signs.plate(canvas, "220V", (x, y, z), facing="east", origin=origin)
    n += signs.flagpole(canvas, (x, y, z), height=7, origin=origin)

A flag has no facing to choose: the map has one wind (the skeleton's WIND_TO) and every flag flies
with it. Mounting, materials and lights are _kit's. The test scene is build/scenes/obs_props_elecsign
(shared with props/electrics).
"""
import functools
import math

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import palette as P
from ..common import skeleton as S
from . import _kit as K

PREFIX = "prop_sign_"
DRESS = True                    # build() dresses the master scene: on from the merge (COMMON 0.10)
VERSION = "a"                   # the great piece over the entrance: the cast emblem (A0, g2 11-15, on the
                                # pictures of V2). The clock stays in the module as version b.
VERSIONS = {"a": "emblem", "b": "clock"}

BR = P.RAMPS["brass"]
CR = P.RAMPS["cream"]
EN = P.RAMPS["enamel"]
IR = P.RAMPS["iron"]
SG = P.RAMPS["signal"]

BRASS, BRASS_D = K.BRASS, K.BRASS_D
IRON, IRON_D = K.IRON, K.IRON_D
BLACK = K.flat("iron", 0)
CLOTH = P.mat("enamel_cloth")

# ---- the station emblem: one figure, two sizes -----------------------------------------------------
EMBLEM_R = 6.5                  # the ring's radius in sixteenths of the figure, to the middle of its line
EMBLEM_STAR = 0.4               # the star's middle: this share of R right of the ring's middle and above it
EMBLEM_SIZES = (16, 48)


def emblem_cells(n=16, framed=False):
    """The standard figure on n x n pixels, n 16 or 48, as dict(ring, meridian, star) of pixels
    (x, y), y running down as in a picture.

    16: the ring is the circle fourteen across (the pixels 5.9 to 6.8 from the middle of the
        tile), the meridian the column x = 7 over the whole height, the star the four pixels
        x 9..10, y 5..6: the one place where a dot of 2 x 2 stands as far to the right of the
        ring's middle as above it and a clear pixel off both the ring and the line.
    16, framed: for a tile that has a frame of its own, a border of one pixel with a rivet or a
        screw in each corner (materials/panels' nameplate; cast iron carries no emblem of its own
        any more, ironwork that wants one hangs the brass roundel of this module): the ring
        a pixel smaller all round, twelve across (5.1 to 5.9 from the middle), the meridian from
        frame to frame (rows 1 to 14), a pixel out of the ring at each end, the star the same four
        pixels.
    48: the same three times over: the ring three pixels thick (18 to 21 from the middle), the
        meridian the two middle columns x 23..24 (a line of three cannot stand in the middle of an
        even tile), the star of eight points nine across about the pixel (31, 16), which is
        (10, 5) of the small figure; two clear pixels to the ring and to the line."""
    if n not in EMBLEM_SIZES:
        raise ValueError(f"the emblem is drawn on {EMBLEM_SIZES} pixels, not on {n}")
    if framed and n != 16:
        raise ValueError("only the figure of 16 pixels has a framed form")
    k = n // 16
    c = (n - 1) / 2.0
    if framed:
        lo, hi = 5.1, 5.9
    elif k == 1:
        lo, hi = 5.9, 6.8
    else:
        lo, hi = (EMBLEM_R - 0.5) * k, (EMBLEM_R + 0.5) * k - 1e-9
    ring = [(x, y) for y in range(n) for x in range(n) if lo <= math.hypot(x - c, y - c) <= hi]
    if k == 1:
        meridian = [(7, y) for y in (range(1, n - 1) if framed else range(n))]
        star = [(x, y) for y in (5, 6) for x in (9, 10)]
    else:
        meridian = [(x, y) for y in range(n) for x in (n // 2 - 1, n // 2)]
        sx, sy = 31, 16
        star = [(sx + dx, sy + dy) for dy in range(-4, 5) for dx in range(-4, 5)
                if min(abs(dx), abs(dy)) == 0 or (abs(dx) == abs(dy) and abs(dx) <= 3)
                or max(abs(dx), abs(dy)) <= 1]
    return {"ring": ring, "meridian": meridian, "star": star}


def emblem_rows(n=16, framed=False):
    """The standard figure as lines of text: o the ring, | the meridian, * the star."""
    fig = emblem_cells(n, framed)
    grid = [["."] * n for _ in range(n)]
    for key, mark in (("ring", "o"), ("meridian", "|"), ("star", "*")):
        for x, y in fig[key]:
            grid[y][x] = mark
    return ["".join(row) for row in grid]


def emblem_faults(n=16, framed=False, cells=None, lip=False):
    """What is wrong with the figure as a drawing: a list of sentences, empty when it keeps the
    rules above. Run by the test scene, so a change to the figure that breaks them is noticed.
    cells: another drawing of the figure on n pixels to be held against the same rules, as
    dict(ring, meridian, star).
    lip: that drawing is cut with a lit lip a pixel to the right of every cut and below it (the
    stone of materials/ashlar). The lips of the ring and of the meridian then count as part of
    them, and the star may stand a pixel further right than up to stay clear of them."""
    fig = emblem_cells(n, framed) if cells is None else cells
    name = f"emblem {n}" + (" framed" if framed else "")
    out = []
    ring, line, star = set(fig["ring"]), set(fig["meridian"]), set(fig["star"])
    c = (n - 1) / 2.0
    k = n // 16
    if star & (ring | line):
        out.append(f"{name}: the star lies on the ring or on the meridian")
    drawn = ring | line
    if lip:
        drawn = drawn | {(x + 1, y + 1) for x, y in drawn}
    gap = min(max(abs(a - x), abs(b - y)) for a, b in star for x, y in drawn) - 1
    need = 1 if k == 1 else 2
    if gap < need:
        out.append(f"{name}: the star stands {gap} clear pixels off the ring or the line, less than {need}")
    if not all(math.hypot(x - c, y - c) < min(math.hypot(a - c, b - c) for a, b in ring) for x, y in star):
        out.append(f"{name}: the star is not inside the ring")
    mx = sum(x for x, _ in star) / len(star) - c
    my = c - sum(y for _, y in star) / len(star)
    if mx <= 0 or my <= 0 or not -0.01 <= mx - my <= (k if lip else 0) + 0.01:
        out.append(f"{name}: the star is not as far right of the middle as above it ({mx:g}, {my:g})")
    top, foot = min(y for _, y in ring), max(y for _, y in ring)
    if not {y for _, y in line} >= set(range(top - 1, foot + 2)):
        out.append(f"{name}: the meridian does not run out of the ring at both ends")
    if any(abs(x - c) > k for x, _ in line):
        out.append(f"{name}: the meridian does not run through the ring's middle")
    return out


# ---- painting by hand ------------------------------------------------------------------------------
def _dice(x, y, seed=0):
    """A number in [0, 1) for a pixel, the same every time."""
    h = (x * 73856093) ^ (y * 19349663) ^ ((seed + 1) * 83492791)
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0


def _picture(name, grid, back=None):
    """A Sprite from a grid of palette colours (hex), None for see-through."""
    chars, rows = {}, []
    for line in grid:
        row = ""
        for colour in line:
            if colour is None:
                row += " "
            else:
                if colour not in chars:
                    chars[colour] = "abcdefghijklmnopqrstuvwxyz"[len(chars)]
                row += chars[colour]
        rows.append(row)
    return Sprite(name, rows, {ch: colour for colour, ch in chars.items()}, back=back)


def _sheets(m, picture, half, z0, z1, count):
    """One picture on `count` thin sheets from z0 to z1, the last one at z1: what is drawn stands
    out of the ground like a casting, every pixel of it where the standard figure has it, and
    looked at from the side the sheets close up into its flank. half = half the sheet's size in
    model units; only the fronts are drawn, and all sheets share one piece of the texture."""
    for i in range(count):
        z = z1 if count == 1 else z0 + (z1 - z0) * i / (count - 1)
        m.box((-half, -half, z - 0.05), (half, half, z), BRASS_D, faces={"s": picture}, skip="newud", seed=1)
    return m


def _disc(n, radius):
    """Is the pixel (x, y) of an n x n picture within `radius` pixels of its middle?"""
    c = (n - 1) / 2.0
    return lambda x, y: math.hypot(x - c, y - c) <= radius


def _roundel_small():
    """The brass roundel on 16 pixels, lit from the upper left like the blocks: (ground, figure).
    The figure is the standard one, light on a dark ground, its shadow a pixel down and right."""
    n = 16
    fig = emblem_cells(n)
    body, star = set(fig["ring"]) | set(fig["meridian"]), set(fig["star"])
    raised = body | star
    inside = _disc(n, n / 2.0)
    ground = [[None] * n for _ in range(n)]
    figure = [[None] * n for _ in range(n)]
    for y in range(n):
        for x in range(n):
            if not inside(x, y):
                continue
            ground[y][x] = BR[0] if (x - 1, y - 1) in raised or (x, y) in raised else BR[1]
            if (x, y) in star:
                figure[y][x] = BR[5]
            elif (x, y) in body:
                figure[y][x] = BR[4]
    return ground, figure


def _roundel_great():
    """The great emblem on 48 pixels, painted as the entrance lamps light it from below: (ground,
    figure). Whatever stands out of the ground has a lit lip along its lower edges and a dark one
    along its upper edges, and throws its shadow up the ground."""
    n = 48
    fig = emblem_cells(n)
    body, star = set(fig["ring"]) | set(fig["meridian"]), set(fig["star"])
    raised = body | star
    inside, c = _disc(n, n / 2.0), (n - 1) / 2.0
    ground = [[None] * n for _ in range(n)]
    figure = [[None] * n for _ in range(n)]
    for y in range(n):
        for x in range(n):
            if not inside(x, y):
                continue
            roll = _dice(x, y, 48)
            if (x, y) in raised or (x, y + 1) in raised:
                ground[y][x] = BR[0]                                    # under the figure and in its shadow
            elif math.hypot(x - c, y - c) > n / 2.0 - 1.0:              # the edge of the casting: no second ring
                ground[y][x] = BR[0]
            else:                                                       # the ground: cast, a little pitted
                ground[y][x] = BR[0] if roll < 0.04 else BR[2] if roll > 0.98 else BR[1]
            if (x, y) in star:
                sx, sy = 31, 16
                figure[y][x] = BR[5] if max(abs(x - sx), abs(y - sy)) <= 2 else BR[4]
            elif (x, y) in body:
                if (x, y + 1) not in body:
                    figure[y][x] = BR[5]
                elif (x, y - 1) not in body:
                    figure[y][x] = BR[3]
                else:
                    figure[y][x] = BR[3] if roll > 0.93 else BR[4]
    return ground, figure


# ---- the emblem as a model ---------------------------------------------------------------------------
def _emblem():
    """The brass roundel, 1 x 1: a cast disc, the standard figure standing a pixel out of it.
    Anchor: the middle of its back, on the wall."""
    m = M.Model(PREFIX + "emblem", px=1.0)
    ground, figure = _roundel_small()
    m.tube("z", (0.0, 0.0), 0.0, 1.0, 7.5, BRASS_D, sides=16)
    _sheets(m, _picture("emblem_ground", ground), 8.0, 1.2, 1.2, 1)
    _sheets(m, _picture("emblem_figure", figure), 8.0, 1.6, 2.0, 2)
    return m


def _great_emblem():
    """Version A of the great piece over the entrance (A0 #186): the emblem cast in brass, three
    blocks across, in low relief (two pixels) on a dark pitted ground. Old brass, nothing glows:
    it is lit by the entrance lamps under it, and painted so. Drawn in sixteen units and shown at
    scale 3, so it has 48 texels across. Anchor: the middle of its back, on the wall."""
    m = M.Model(PREFIX + "great_emblem", px=3.0)
    ground, figure = _roundel_great()
    m.tube("z", (0.0, 0.0), 0.0, 0.6, 7.85, BRASS_D, sides=24)
    _sheets(m, _picture("great_ground", ground), 8.0, 0.7, 0.7, 1)
    _sheets(m, _picture("great_figure", figure), 8.0, 0.84, 1.4, 5)
    return m


# ---- the clock: version B of the great piece -----------------------------------------------------------
# Every clock of the map is stopped at one time (A0, g2 11-15): the skeleton's CLOCK, 7:55 while the
# skeleton in the tree does not have it yet.
CLOCK_TIME = tuple(getattr(S, "CLOCK", (7, 55)))
_ROMAN = {"I": ["1", "1", "1", "1", "1"], "V": ["101", "101", "101", "101", "010"],
          "X": ["101", "101", "010", "101", "101"]}
DIAL_R = 19.0                   # the dial's radius in pixels of the 48


def _glyphs(text, font):
    """The bitmap of a word: its glyphs side by side, a clear column between them."""
    rows = ["", "", "", "", ""]
    for i, ch in enumerate(text):
        for j in range(5):
            rows[j] += ("0" if i else "") + font[ch][j]
    return rows


def _dial():
    """The dial on 48 pixels, laid out as the small dials of machines/clock are: white enamel, a
    chapter ring a tone down, in it a square dot at each hour that has no figure, inside it the
    four quarters in Roman figures; a grey edge where the rim throws its shadow. The hands are not
    painted: they are the model's."""
    n = 48
    c = (n - 1) / 2.0
    inside = _disc(n, DIAL_R - 0.01)
    grid = [[None] * n for _ in range(n)]
    for y in range(n):
        for x in range(n):
            if inside(x, y):
                d = math.hypot(x - c, y - c)
                if d >= DIAL_R - 1.0:
                    grid[y][x] = CR[1] if y > c + 9 else CR[2]
                else:
                    grid[y][x] = CR[2] if 0.80 * DIAL_R <= d <= 0.90 * DIAL_R else CR[3]

    def stamp(rows, x0, y0):
        for j, row in enumerate(rows):
            for i, bit in enumerate(row):
                if bit == "1":
                    grid[y0 + j][x0 + i] = IR[0]

    # the figures stand 12.5 pixels from the middle, the dots in the middle of the chapter ring
    for text, at in (("XII", (20, 9)), ("III", (34, 21)), ("VI", (21, 34)), ("IX", (9, 21))):
        stamp(_glyphs(text, _ROMAN), *at)
    mark = 0.85 * DIAL_R
    for hour in range(1, 12):
        a = math.radians(30.0 * hour)
        if hour % 3:
            stamp(["11", "11"], int(round(c + mark * math.sin(a) - 0.5)), int(round(c - mark * math.cos(a) - 0.5)))
    return grid


def _great_clock():
    """Version B of the great piece over the entrance (A0 #186): a clock, three blocks across, of
    one family with the tower's dials (A0 #265, machines/clock): a white enamel dial, black hands,
    a thin brass rim, and round them a case of dark iron that does for the entrance what the dark
    recess does for a dial in the tower. Nothing glows; it shows CLOCK_TIME, as they do. Drawn in
    sixteen units, shown at scale 3. Anchor: the middle of its back, on the wall."""
    m = M.Model(PREFIX + "great_clock", px=3.0)
    m.tube("z", (0.0, 0.0), 0.0, 1.0, 7.9, IRON_D, sides=24)                    # the case
    _sheets(m, _picture("clock_dial", _dial()), 8.0, 1.1, 1.1, 1)
    m.ring("z", (0.0, 0.0, 1.25), 20.0 / 3.0, 2.0 / 3.0, 0.5, BRASS, sides=32)  # the rim, two pixels of brass
    hour, minute = CLOCK_TIME
    # the hands in pixels of the 48: (how far round, length, tail, width, how far off the wall).
    # Three pixels and two wide: from the court a pixel of the dial is less than one on the screen
    for angle, length, tail, wide, z in (((hour % 12 + minute / 60.0) * 30.0, 9.0, 2.5, 3.0, 1.2),
                                         (minute * 6.0, 14.0, 3.0, 2.0, 1.32)):
        m.box((-wide / 6.0, -tail / 3.0, z), (wide / 6.0, length / 3.0, z + 0.12), BLACK,
              rot=("z", -angle, (0.0, 0.0, z)))
    m.tube("z", (0.0, 0.0), 1.2, 1.6, 0.6, BRASS_D, sides=8)                    # the boss of the hands
    return m


# ---- enamel plates ------------------------------------------------------------------------------------
# Figures of three by five: digits, the few letters the plan allows, an arrow and the flash.
_FONT = {
    "0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"], "3": ["111", "001", "011", "001", "111"],
    "4": ["101", "101", "111", "001", "001"], "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"], "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"], "9": ["111", "101", "111", "001", "111"],
    "V": ["101", "101", "101", "101", "010"], "A": ["010", "101", "111", "101", "101"],
    "N": ["1001", "1101", "1011", "1001", "1001"], "S": ["011", "100", "010", "001", "110"],
    "M": ["10001", "11011", "10101", "10001", "10001"],
    ">": ["0000100", "0000010", "1111111", "0000010", "0000100"],
    "<": ["0010000", "0100000", "1111111", "0100000", "0010000"],
    "!": ["0011", "0110", "1111", "0110", "1100"],     # the flash of a voltage plate
}
# label -> (what is written, the plate's style). "!" is the flash, drawn in signal red on white.
PLATES = {str(i): (str(i), "blue") for i in range(1, 13)}
PLATES.update({"<": ("<", "blue"), ">": (">", "blue"), "N": ("N", "blue"), "S": ("S", "blue"),
               "220V": ("!220V", "white"), "110V": ("!110V", "white")})
_SLUG = {"<": "left", ">": "right"}
PLATE_H = 9                     # a plate is nine pixels high: its edge, a clear pixel, the figures of five


def plate_name(label):
    return "plate_" + _SLUG.get(label, label.lower())


def plate_size(label):
    """(width, height) of a plate in blocks."""
    text, _ = PLATES[label]
    return (sum(len(_FONT[ch][0]) for ch in text) + len(text) - 1 + 4) / 16.0, PLATE_H / 16.0


def _plate_face(text, style):
    """The face of an enamel plate: a fine line round its edge with the corners knocked off, the
    figures in the middle. Blue: cream on enamel blue, a short gloss along the top, the lower edge
    of the field a step darker. White: black on white enamel, the flash in red."""
    blue = style == "blue"
    edge, corner = (CR[2], EN[0]) if blue else (IR[1], CR[1])
    field, shade, gloss = (EN[2], EN[1], EN[3]) if blue else (CR[3], CR[2], CR[3])
    ink, flash = (CR[3], CR[3]) if blue else (IR[0], SG[2])
    tw = sum(len(_FONT[ch][0]) for ch in text) + len(text) - 1
    w, h = tw + 4, PLATE_H
    grid = [[field] * w for _ in range(h)]
    for x in range(w):
        grid[0][x] = grid[h - 1][x] = edge
    for y in range(h):
        grid[y][0] = grid[y][w - 1] = edge
    for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        grid[y][x] = corner
    for x in range(1, w - 1):
        grid[h - 2][x] = shade
        if x <= max(2, w // 4):
            grid[1][x] = gloss
    x = 2
    for ch in text:
        for j, row in enumerate(_FONT[ch]):
            for i, bit in enumerate(row):
                if bit == "1":
                    grid[2 + j][x + i] = flash if ch == "!" else ink
        x += len(_FONT[ch][0]) + 1
    return grid


def _plate(label):
    """An enamel plate: a thin sheet of pressed steel, the face drawn by hand. Anchor: the middle
    of its back, on the wall."""
    text, style = PLATES[label]
    grid = _plate_face(text, style)
    w, h = len(grid[0]), len(grid)
    m = M.Model(PREFIX + plate_name(label), px=1.0)
    side = K.flat("enamel", 0) if style == "blue" else K.flat("cream", 1)
    m.box((-w / 2.0, -h / 2.0, 0.0), (w / 2.0, h / 2.0, 0.5), side,
          faces={"s": _picture(plate_name(label) + "_face", grid)}, skip="n")
    return m


# ---- the station's name board ---------------------------------------------------------------------------
# What the board of a mountain railway's station says: the name of the place and how high it lies.
# The name of this place is the emblem; the height is the skeleton's once it says one, in metres
# above the sea. One board, for the cable station (site/cablecar's SIGN).
HEIGHT = int(getattr(S, "ALTITUDE", 2610))
BOARD_H = 16                    # a block high: the framed emblem from edge to edge
BOARD_GAP = 3                   # clear pixels between the emblem's ring and the figures


def board_text():
    """What stands after the emblem: the height and the letter of its measure."""
    return f"{HEIGHT}M"


def board_size():
    """(width, height) of the station's board in blocks."""
    text = board_text()
    figures = sum(len(_FONT[ch][0]) for ch in text) + len(text)     # a pixel between two, two before the M
    return (14 + BOARD_GAP + figures + 2) / 16.0, BOARD_H / 16.0


def _board_face():
    """The face of the station's board, in the enamel of the plates: their edge line with the
    corners knocked off, their gloss and their shaded foot. At its head the emblem in its framed
    form (the board has an edge of its own: the ring twelve across, a clear pixel off the edge, the
    meridian from edge to edge), then the height in the plates' figures, on the lower five of the
    ring's middle rows so that they sit rather than hang."""
    text = board_text()
    w, h = int(round(board_size()[0] * 16)), BOARD_H
    edge, corner, field, shade, gloss, ink = CR[2], EN[0], EN[2], EN[1], EN[3], CR[3]
    grid = [[field] * w for _ in range(h)]
    for x in range(w):
        grid[0][x] = grid[h - 1][x] = edge
    for y in range(h):
        grid[y][0] = grid[y][w - 1] = edge
    for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        grid[y][x] = corner
    for x in range(1, w - 1):
        grid[h - 2][x] = shade
        if x <= w // 4:
            grid[1][x] = gloss
    fig = emblem_cells(16, framed=True)
    for key in ("ring", "meridian", "star"):
        for x, y in fig[key]:
            grid[y][x] = ink
    x, top = 14 + BOARD_GAP, (h - 5) // 2 + 1
    for ch in text:
        if ch == "M":
            x += 1
        for j, row in enumerate(_FONT[ch]):
            for i, bit in enumerate(row):
                if bit == "1":
                    grid[top + j][x + i] = ink
        x += len(_FONT[ch][0]) + 1
    return grid


def _station_board():
    """The name board of the cable station: the emblem and the height of the place on a sheet of
    enamelled steel a block high, a pixel proud of the wall, a brass screw in each corner. Anchor:
    the middle of its back, on the wall."""
    grid = _board_face()
    w, h = len(grid[0]), len(grid)
    m = M.Model(PREFIX + "station_board", px=1.0)
    m.box((-w / 2.0, -h / 2.0, 0.0), (w / 2.0, h / 2.0, 1.0), K.flat("enamel", 0),
          faces={"s": _picture("station_board_face", grid)}, skip="n")
    for x in (-w / 2.0 + 2.5, w / 2.0 - 2.5):
        for y in (-h / 2.0 + 2.5, h / 2.0 - 2.5):
            K.rivet(m, (x, y, 1.0), out="z", mat=K.flat("brass", 4))
    return m


# ---- the flag and its pole ------------------------------------------------------------------------------
FLAG = (24, 16)                 # the cloth in pixels: a block and a half by a block
FLAG_WAVE = (16.0, -20.0, 14.0)     # how its three widths hang turned against each other, in degrees
# One wind for the whole map, a north wind (A0, g2 11-15): the skeleton's WIND_TO is the side every
# flag flies to, in the words used for facing; south while the skeleton in the tree does not say.
WIND_TO = getattr(S, "WIND_TO", "south")
POLE = K.flat("iron", 3)
POLE_R = 1.0                    # the pole is two pixels thick
POLE_FOOT, POLE_HEAD = 1.0, 0.75    # what the foot and the head take of a pole's height, in blocks


def _flag_face(hoist):
    """One side of the flag: enamel blue, the emblem in cream in the middle of it, the meridian
    from the upper edge to the lower, a cream tape down the hoist, which is the column `hoist`.
    None where the cloth's own weave shows."""
    w, h = FLAG
    grid = [[None] * w for _ in range(h)]
    fig = emblem_cells(16)
    for key in ("ring", "meridian", "star"):
        for x, y in fig[key]:
            grid[y][x + (w - 16) // 2] = CR[3] if key == "star" else CR[2]
    for y in range(h):
        grid[y][hoist] = CR[1]
    return grid


def _flag():
    """The flag, hanging in three widths turned a little against each other so that it is cloth
    and not a board; both sides show the emblem the right way round. The still flag: its flutter
    is A8's. Anchor: the upper corner of the hoist, on the pole's axis; the cloth hangs below it
    and flies along +x."""
    m = M.Model(PREFIX + "flag", px=1.0)
    w, h = FLAG
    part = w // 3

    def widths(side, grid):
        return [_picture(f"flag_{side}{i}", [row[i * part:(i + 1) * part] for row in grid], back=CLOTH)
                for i in range(3)]

    # seen from the front the hoist is on the left, from the back on the right: the back is a
    # picture of its own, not the front mirrored, so the star stays on the upper right
    front, back = widths("s", _flag_face(0)), widths("n", _flag_face(w - 1))
    x, z = POLE_R + 0.5, 0.0
    for i, angle in enumerate(FLAG_WAVE):
        with m.turned(("y", angle), about=(x, 0.0, z)):
            m.box((x, -h, z - 0.25), (x + part, 0.0, z + 0.25), CLOTH,
                  faces={"s": front[i], "n": back[2 - i]}, seed=10 + i)
        a = math.radians(angle)
        x, z = x + part * math.cos(a), z - part * math.sin(a)
    for y in (-1.5, -h + 1.5):                                          # the two rings it is bent on with
        m.tube("y", (0.0, 0.0), y - 0.5, y + 0.5, POLE_R + 0.5, BRASS_D, sides=8)
    return m


def _pole_foot():
    """The foot of the flagpole: a cast-iron shoe bolted to the paving, the pole standing in its
    socket. Anchor: the middle of its foot; it is one block high."""
    m = M.Model(PREFIX + "pole_foot", px=1.0)
    m.box((-3.0, 0.0, -3.0), (3.0, 1.5, 3.0), IRON, grain="x")
    for x in (-2.0, 2.0):
        for z in (-2.0, 2.0):
            K.rivet(m, (x, 1.5, z), out="y")
    m.taper("y", (0.0, 0.0), 1.5, 7.0, 2.4, 1.6, IRON_D, steps=3)
    m.tube("y", (0.0, 0.0), 7.0, 8.0, 2.0, IRON)
    m.tube("y", (0.0, 0.0), 8.0, 16.0, POLE_R, POLE)
    return m


def _pole():
    """The pole between foot and head: runs along +z from the anchor, 48 long, in flat tones, and
    is drawn out to the length wanted (models.between)."""
    m = M.Model(PREFIX + "pole", px=1.0)
    m.tube("z", (0.0, 0.0), 0.0, 48.0, POLE_R, POLE)
    return m


def _pole_head():
    """The head of the flagpole: the last of the pole and a brass ball on it. A ball and nothing
    else: no yard, no vane, nothing across the pole. Anchor: its lower end, on the pole's axis."""
    m = M.Model(PREFIX + "pole_head", px=1.0)
    top = POLE_HEAD * 16.0
    m.tube("y", (0.0, 0.0), 0.0, top - 3.0, POLE_R, POLE)
    m.tube("y", (0.0, 0.0), top - 3.0, top - 2.4, 1.4, BRASS_D)
    m.ball((0.0, top - 1.2, 0.0), 1.6, BRASS, sides=8, layers=4)
    return m


# ---- models and placing ---------------------------------------------------------------------------------
# kind -> how it is mounted and its scale. The great pieces hang ten blocks over the entrance's
# lamps, further than the game carries their light, so they say themselves how they are lit:
#   shown   the light the piece is shown in, (sky, block): that of the bracket lamps beside the
#           door (the light line's second rank, 12). A front that looks east shows at half of it,
#           so the dial stays under the frosted windows and the brass under the curtained ones.
#   light   a source registered with the light line for the stone round the piece: where (blocks,
#           in the model's frame: at the foot of the piece, in the air before the wall) and how
#           bright. The light line takes it (c220, g2 11-15): a wall wash, the third rank, under
#           the name WASH; no lamp is hung for it. It lifts the tablet's lowest row to 8 and 7,
#           one less for each row above.
GREAT_SHOWN = (15, 12)
WASH = ("props/signs:emblem", 3)        # what the wash is registered as, and its rank
SPEC = {
    "emblem": dict(build=_emblem, mount="wall", scale=1.0),
    "great_emblem": dict(build=_great_emblem, mount="wall", scale=3.0, shown=GREAT_SHOWN,
                         light=(0.0, -1.0, 0.3), level=8),
    "great_clock": dict(build=_great_clock, mount="wall", scale=3.0, shown=GREAT_SHOWN,
                        light=(0.0, -1.0, 0.3), level=8),
    "station_board": dict(build=_station_board, mount="wall", scale=1.0),
    "flag": dict(build=_flag, mount="floor", scale=1.0),
    "pole_foot": dict(build=_pole_foot, mount="floor", scale=1.0),
    "pole": dict(build=_pole, mount="floor", scale=1.0),
    "pole_head": dict(build=_pole_head, mount="floor", scale=1.0),
}
SPEC.update({plate_name(label): dict(build=functools.partial(_plate, label), mount="wall", scale=1.0)
             for label in PLATES})
SCALE = {PREFIX + kind: spec["scale"] for kind, spec in SPEC.items()}
GREAT = ("emblem", "clock")


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + kind: spec["build"]() for kind, spec in SPEC.items()}


def models():
    return dict(_models())


def _wash(canvas, cell, level):
    """Register the wash of a great piece with the light line (sky/_lightkit.suggest, with its
    rank). While that tool is not in the tree the kit puts the source down itself."""
    why, rank = WASH
    try:
        from ..sky import _lightkit
        suggest = getattr(_lightkit, "suggest", None)
    except ImportError:
        suggest = None
    if suggest is None:
        K.offer_lights(canvas, [(cell, level)], why)
    else:
        suggest(canvas, cell, level, why, rank=rank)


def place(canvas, kind, pos, facing="south", origin=(0, 0, 0), light=True, yaw=None, **opts):
    """Place one piece: a wall piece by the middle of its back at pos (a point of the wall's face),
    `facing` the way that face looks; a floor piece by the middle of its foot. A great piece is
    shown in the light of the entrance (brightness=None leaves it to the cell it hangs in) and
    registers a wash for the stone round it with the light line unless light=False. Returns the
    number of display entities."""
    spec = SPEC[kind]
    yaw = K.FACING[facing] if yaw is None else yaw
    if spec.get("shown") is not None:
        opts.setdefault("brightness", spec["shown"])
    n = K.put(canvas, _models()[PREFIX + kind], pos, mount=spec["mount"], yaw=yaw, scale=spec["scale"],
              origin=origin, **opts)
    if light and spec.get("light") is not None:
        _wash(canvas, K.light_cell(pos, yaw, spec["light"], origin), spec["level"])
    return n


def plate(canvas, label, pos, facing="south", origin=(0, 0, 0), **opts):
    """Hang the enamel plate that says `label` (one of PLATES) by the middle of its back."""
    if label not in PLATES:
        raise KeyError(f"no plate says {label!r}; add it to signs.PLATES (there are: {', '.join(PLATES)})")
    return place(canvas, plate_name(label), pos, facing=facing, origin=origin, **opts)


def great(canvas, seat, kind="emblem", origin=(0, 0, 0), light=True, **opts):
    """Hang the great piece on its seat over the entrance. seat is what main/facade.emblem() gives:
    dict(cells, out, face_x) -- the nine blocks of the tablet, the way it looks, the plane of its
    face. kind is "emblem" (version A) or "clock" (version B). The seat looks east or west; opts
    as for place()."""
    if kind not in GREAT:
        raise KeyError(f"the great piece is one of {GREAT}, not {kind!r}")
    if seat["out"] not in ("east", "west"):
        raise ValueError(f"the seat of the great piece looks east or west, not {seat['out']!r}")
    ys = [y for _, y, _ in seat["cells"]]
    zs = [z for _, _, z in seat["cells"]]
    pos = (seat["face_x"], (min(ys) + max(ys) + 1) / 2.0, (min(zs) + max(zs) + 1) / 2.0)
    return place(canvas, "great_" + kind, pos, facing=seat["out"], origin=origin, light=light, **opts)


def flagpole(canvas, foot, height=7.0, origin=(0, 0, 0), flag=True):
    """A flagpole standing on the ground at `foot` (the middle of its foot), `height` blocks to
    the top of its ball, the flag under the ball. The cloth flies with the map's one wind, to
    WIND_TO, a block and a half from the pole; nobody who puts up a pole chooses that. With the
    north wind the cloth lies north to south and shows a whole face to the east and to the west:
    from the east the hoist is on the right, from the west on the left, and the emblem reads
    the right way round from both. Returns the number of display entities (four: foot, pole,
    head, flag)."""
    yaw = K.FACING[WIND_TO] + 90.0          # the cloth flies along the model's +x: turn that to WIND_TO
    built = _models()
    x, y, z = (foot[i] + origin[i] for i in range(3))
    n = K.put(canvas, built[PREFIX + "pole_foot"], foot, yaw=yaw, origin=origin)
    lower, upper = y + POLE_FOOT, y + height - POLE_HEAD
    canvas.add_entity(x, lower, z, M.between(built[PREFIX + "pole"], (x, lower, z), (x, upper, z)))
    head = (foot[0], foot[1] + height - POLE_HEAD, foot[2])
    n += 1 + K.put(canvas, built[PREFIX + "pole_head"], head, yaw=yaw, origin=origin)
    if flag:
        hoist = (foot[0], foot[1] + height - 0.25, foot[2])
        n += K.put(canvas, built[PREFIX + "flag"], hoist, yaw=yaw, origin=origin)
    return n


def _seat():
    """The seat of the great piece as main/facade gives it, or None while the front in the tree
    has none (props dress a wall that already stands)."""
    try:
        from ..main import facade
    except ImportError:
        return None
    give = getattr(facade, "emblem", None)
    return give() if give is not None else None


def _station_seat():
    """Where the cable station wants its name board: site/cablecar's SIGN, dict(point, facing,
    width) -- a point of the wall's face, the middle of the board's back -- or None while that
    package is not in the tree."""
    try:
        from ..site import cablecar
    except ImportError:
        return None
    return getattr(cablecar, "SIGN", None)


def station(canvas, seat=None, origin=(0, 0, 0)):
    """Hang the station's name board on its seat (site/cablecar.SIGN when none is given). Nothing
    is hung where the wall behind the seat does not stand on the canvas or the cell before it is
    taken by anything but a light source. Returns the number of display entities."""
    seat = _station_seat() if seat is None else seat
    if seat is None:
        return 0
    out = K.turn(K.FACING[seat["facing"]], (0.0, 0.0, 1.0))
    wall, air = (tuple(math.floor(seat["point"][i] + origin[i] + side * out[i] + 1e-6) for i in range(3))
                 for side in (-0.5, 0.5))
    if not canvas.has(*wall) or canvas.name(*air) not in (None, "light"):
        return 0
    return place(canvas, "station_board", seat["point"], facing=seat["facing"], origin=origin)


# ---- the plate beside the entrance ------------------------------------------------------------------------
# The plan's list for the entrance (V4) is the iron gates, the canopy, the bracket lamps and a
# nameplate, and the board of 11-16 10:00 had no plate beside the door (review c332; c356 hangs it,
# 11-16). The name of the place is the emblem over the door, so the plate says what the plate beside
# a door of that time says, the house's number in white on blue enamel: the main building is 1. It
# is one of PLATES as it is, 7 by 9 pixels: small beside the lamps' back plates, a plate from ten
# blocks off, its figure read from three.
DOOR_PLATE = "1"
DOOR_PLATE_UP = 0.5             # its middle over the top of the plinth: in the first course of pale stone


def _door_seat():
    """Where the entrance's plate hangs: dict(point, facing) -- the middle of the plate's back, on
    the east face of the pier between the main doorway and the arch south of it, in the first
    course over the plinth -- read off main/facade (doors() for the doorway, emblem() for the plane
    of the two pilasters the piers are), or None while the front in the tree has no such doorway."""
    try:
        from ..main import facade
    except ImportError:
        return None
    doors, tablet = getattr(facade, "doors", None), getattr(facade, "emblem", None)
    if doors is None or tablet is None:
        return None
    ways = [d for d in doors() if d["front"] == "east" and d["kind"] == "door"]
    if not ways:
        return None
    pier = max(z for _, z in ways[0]["cells"]) + 1          # the column of cells south of the doorway
    return dict(point=(tablet()["face_x"], S.BASE[0] + DOOR_PLATE_UP, pier + 0.5), facing="east")


def doorplate(canvas, seat=None, origin=(0, 0, 0), **opts):
    """Hang the entrance's plate (DOOR_PLATE) on its seat: _door_seat() when none is given, or
    dict(point, facing) as the station's board has it. Nothing is hung where the stone behind the
    seat does not stand on the canvas or the cell before it is taken by anything but a light
    source. opts as for place(). Returns the number of display entities."""
    seat = _door_seat() if seat is None else seat
    if seat is None:
        return 0
    out = K.turn(K.FACING[seat["facing"]], (0.0, 0.0, 1.0))
    wall, air = (tuple(math.floor(seat["point"][i] + origin[i] + side * out[i] + 1e-6) for i in range(3))
                 for side in (-0.5, 0.5))
    if not canvas.has(*wall) or canvas.name(*air) not in (None, "light"):
        return 0
    return plate(canvas, DOOR_PLATE, seat["point"], facing=seat["facing"], origin=origin, **opts)


def build(canvas, origin=(0, 0, 0), version=None):
    """What signs place in the master scene: nothing while DRESS is off (A0 #211: what is hung over
    the whole building stays off until it has passed on the real wall), and then no other package's
    table is read at all. On: the great piece on its seat over the entrance, version `version` of
    it (VERSION when not given) -- the main line owns the seat and places no models, so the piece
    is hung from here (c206, g2 11-15) -- the name board on the cable station, which keeps a
    seat for it and has no models of its own either, and the plate beside the main doorway
    (doorplate()). Nothing is hung where the seat's stone does not stand."""
    if not DRESS:
        return 0
    n = 0
    seat = _seat()
    if seat is not None and all(canvas.has(x + origin[0], y + origin[1], z + origin[2]) for x, y, z in seat["cells"]):
        n += great(canvas, seat, VERSIONS[VERSION if version is None else version], origin)
    return n + station(canvas, origin=origin) + doorplate(canvas, origin=origin)


if __name__ == "__main__":
    for size, framed in ((16, False), (16, True), (48, False)):
        print(f"the station emblem on {size} pixels{', for a tile with a frame' if framed else ''} "
              "(o ring, | meridian, * star)")
        print("\n".join(emblem_rows(size, framed)))
        for fault in emblem_faults(size, framed):
            print("  FAULT:", fault)
        print()
