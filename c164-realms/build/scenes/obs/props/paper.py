"""The paper family (plan ART-PLAN 7.3; parts/A6-props.md 2.7; card packages/props/paper.md).

What lies on the desks and hangs on the walls of a working observatory: star charts, blueprints,
a blackboard with tonight's orbit on it, a map of the Moon, log books, glass negatives. One
vocabulary for all of them: cream paper; the chart blue of the enamel signs with the drawing left
in cream; brass for whatever holds a sheet (a bead round it, a screw, a pin); an edge that curls
where a sheet hangs free; and one heading wherever a sheet has one, a strip of the chart blue
with its stars. The drawings are figures, lines and dots; nothing is written out, and no figure
is a cross.

Every face is drawn here, texel by texel, on the common palette, 16 texels to the block.

For the other lines:

    from scenes.obs.props import paper
    n += paper.place(canvas, "star_chart", (x, y, z), facing="east", origin=origin)   # on a wall
    n += paper.place(canvas, "logbook", (x, y, z), yaw=20.0, origin=origin)           # on a desk
    n += paper.place(canvas, "blueprint", (x, y, z), lie=True, origin=origin)         # a sheet laid flat

place() returns the number of display entities it placed (one). KINDS lists what there is.
"""
import functools
import math

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import palette as P
from . import _kit as K

PREFIX = "prop_paper_"

EN, CR, BR, IR, SL, GL = (P.RAMPS[k] for k in ("enamel", "cream", "brass", "iron", "slate", "glow"))

BRASS = K.BRASS
SCREW = K.flat("brass", 5)                                      # screw heads and pins catch the light
PAPER = K.CREAM                                                 # a sheet seen edge on, a rolled sheet
PLATE = K.flat("enamel", 0)                                     # the edge of an enamelled plate
WOOD = P.mat("dark_wood")
LEATHER = P.mat("dark_wood", kind="plain", noise=0.12, base=1)  # bindings (R1: leather is dark wood)
SLATE = P.mat("slate", noise=0.16, bevel=0)
CHALK = K.flat("cream", 3)
FELT = K.flat("cream", 1)
GLASS = K.flat("glow", 1)                                       # the edge of a glass negative
PENCIL = K.flat("brass", 3)
RIBBON = K.flat("enamel", 2)                                    # a book's marker

# the colours of a star chart: ground, Milky Way, graduation, figure lines, ecliptic, stars, faint stars
SKY = {"e": EN[1], "m": EN[2], "g": EN[3], "l": EN[3], "c": BR[3], "s": CR[3], "f": CR[0]}


# ---- drawing a face -----------------------------------------------------------------------------------
class _Grid:
    """A face drawn by hand: a grid of characters, one to a texel, y running down as in a picture."""

    def __init__(self, w, h, fill=" "):
        self.w, self.h = w, h
        self.rows = [[fill] * w for _ in range(h)]

    def put(self, x, y, ch):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.rows[y][x] = ch

    def dots(self, points, ch):
        for x, y in points:
            self.put(x, y, ch)

    def fill(self, x0, y0, x1, y1, ch):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, y, ch)

    def frame(self, x0, y0, x1, y1, ch):
        for x in range(x0, x1 + 1):
            self.put(x, y0, ch)
            self.put(x, y1, ch)
        for y in range(y0, y1 + 1):
            self.put(x0, y, ch)
            self.put(x1, y, ch)

    def line(self, p, q, ch, dash=None):
        """A one-texel line from p to q. dash = (on, off) breaks it."""
        self.dots(_dashed(_line(p, q), dash), ch)

    def text(self):
        return ["".join(row) for row in self.rows]

    def sprite(self, name, colours, back=None):
        return Sprite(name, self.text(), colours, back)


def _line(p, q):
    (x0, y0), (x1, y1) = p, q
    n = max(abs(x1 - x0), abs(y1 - y0))
    return [(round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n)) for i in range(n + 1)] if n else [p]


def _thin(points):
    """Drop the texels that only fill a corner, so a drawn curve is one texel thick everywhere."""
    have = set(points)
    out = []
    for x, y in points:
        corner = any((x + dx, y) in have and (x, y + dy) in have for dx in (-1, 1) for dy in (-1, 1))
        if corner:
            have.discard((x, y))
        else:
            out.append((x, y))
    return out


def _dashed(points, dash):
    if not dash:
        return points
    on, off = dash
    return [p for i, p in enumerate(points) if i % (on + off) < on]


def _ellipse(cx, cy, a, b):
    """The texels of an ellipse, one texel thick and alike in its four quarters. The centre lies
    on a texel or between two (cx, cy whole or half numbers)."""
    quarter, n = [], 64 * int(a + b)
    for k in range(n + 1):
        t = 0.5 * math.pi * k / n
        p = (int(math.floor(cx + a * math.cos(t) + 0.5)), int(math.floor(cy - b * math.sin(t) + 0.5)))
        if p not in quarter:
            quarter.append(p)
    mx, my = int(round(2 * cx)), int(round(2 * cy))
    out = []
    for x, y in _thin(quarter):
        for q in ((x, y), (mx - x, y), (x, my - y), (mx - x, my - y)):
            if q not in out:
                out.append(q)
    return out


def _graduate(g):
    """The graduated edge of a chart: two texels on and two off, all the way round, the corners
    left plain."""
    for x in range(g.w):
        for y in (0, g.h - 1):
            g.put(x, y, "g" if (x // 2) % 2 else "e")
    for y in range(g.h):
        for x in (0, g.w - 1):
            g.put(x, y, "g" if (y // 2) % 2 else "e")


def _blocks(corners):
    """The four texels of each first-magnitude star, from the upper left one."""
    return [(x + i, y + j) for x, y in corners for i in (0, 1) for j in (0, 1)]


# ---- the faces ----------------------------------------------------------------------------------------
def _chart_face():
    """The enamel star chart, 30 x 14: a graduated edge as on a map, and inside it four figures of
    the northern sky drawn star to star (the Dipper, the W, the Crown, the Arrow), a small cluster
    and loose stars of three magnitudes. A bright star is a block of four texels and a faint one a
    grey dot; none is drawn as a cross, no two lines cross, and a clear texel runs inside the
    edge."""
    g = _Grid(30, 14, "e")
    dipper = [(2, 5), (5, 4), (8, 4), (10, 6), (14, 5), (14, 8), (11, 9), (10, 6)]
    zigzag = [(17, 3), (19, 6), (22, 4), (25, 7), (27, 4)]
    crown = [(2, 8), (3, 10), (5, 11), (7, 10), (8, 8)]
    arrow = [(16, 10), (20, 9), (22, 8)]
    barb = [(20, 9), (22, 11)]
    for figure in (dipper, zigzag, crown, arrow, barb):
        for a, b in zip(figure, figure[1:]):
            g.line(a, b, "l")
    g.dots([(8, 2), (12, 2), (20, 2), (25, 2), (17, 7), (9, 11)], "f")
    g.dots(dipper + zigzag + crown + arrow + barb, "s")
    g.dots([(24, 10), (25, 9), (26, 10), (27, 9), (26, 11)], "s")               # the cluster
    g.dots([(15, 2), (5, 7), (13, 11)], "s")
    g.dots(_blocks([(14, 5), (22, 3)]), "s")                                    # first magnitude
    _graduate(g)
    return g.sprite("paper_chart_face", SKY)


def _sky_face(name, band, arch, figures, bright, stars, faint):
    """One half of the sky on an enamelled plate, 46 x 30, drawn like the small chart and with two
    things more: the Milky Way as a lighter stream (band: its first and last texel in each row from
    row 1 down), and the ecliptic as a dashed line of brass (arch: its row for a column). The
    ecliptic stops short of every star and figure it meets, as on an engraved chart, so nothing on
    the plate crosses anything."""
    g = _Grid(46, 30, "e")
    for y, (x0, x1) in enumerate(band, 1):
        g.fill(x0, y, x1, y, "m")
    ground = [row[:] for row in g.rows]
    g.dots(_dashed([(x, int(math.floor(arch(x) + 0.5))) for x in range(1, 45)], (2, 1)), "c")
    lines = [p for figure in figures for a, b in zip(figure, figure[1:]) for p in _line(a, b)]
    marks = list(stars) + _blocks(bright)
    g.dots(lines, "l")
    g.dots(faint, "f")
    g.dots(marks, "s")
    for x, y in lines + marks + list(faint):
        for i in (x - 1, x, x + 1):
            for j in (y - 1, y, y + 1):
                if 0 <= i < g.w and 0 <= j < g.h and g.rows[j][i] == "c":
                    g.rows[j][i] = ground[j][i]
    _graduate(g)
    return g.sprite(name, SKY)


# The winter half of the sky, east on the left as on any chart: the Hunter in the middle with his
# belt of three, the Twins, the Charioteer, the Bull with the horn that reaches up to him and the
# Seven Sisters beyond, the two Dogs, the River winding off to the south-west. The ecliptic arches
# over the Hunter, between the Bull's eye and the Sisters.
WINTER = dict(
    band=[(22, 26), (22, 26), (21, 26), (21, 25), (20, 25), (20, 24), (19, 24), (19, 23), (18, 23), (18, 22),
          (17, 22), (17, 22), (16, 21), (16, 21), (15, 20), (15, 20), (14, 19), (14, 19), (13, 19), (13, 18),
          (12, 18), (12, 17), (11, 17), (11, 16), (10, 16), (10, 15), (9, 15), (9, 14)],
    arch=lambda x: 16.0 - 5.0 * math.sin(math.pi * (x - 2) / 41.0),
    figures=[
        [(9, 4), (12, 7), (15, 10)], [(6, 7), (9, 10), (12, 13)],                       # the Twins
        [(28, 3), (31, 4), (31, 8), (27, 9), (25, 6), (27, 3)],                         # the Charioteer
        [(20, 14), (21, 18), (20, 22)], [(25, 14), (23, 16), (25, 21)],                 # the Hunter
        [(35, 18), (37, 18), (34, 14), (31, 8)],                                        # the Bull
        [(15, 24), (12, 26), (10, 27)], [(16, 24), (17, 27)],                           # the Great Dog
        [(8, 16), (10, 15)],                                                            # the Little Dog
        [(28, 23), (31, 22), (34, 24), (37, 23), (41, 25), (38, 27), (34, 26)],         # the River
    ],
    bright=[(5, 6), (27, 2), (19, 13), (25, 21), (33, 17), (15, 23), (7, 16)],
    stars=[(9, 4), (12, 7), (15, 10), (9, 10), (12, 13),
           (31, 4), (31, 8), (27, 9), (25, 6),
           (25, 14), (21, 18), (22, 17), (23, 16), (20, 22),
           (37, 18), (34, 14),
           (12, 26), (10, 27), (17, 27), (10, 15),
           (28, 23), (31, 22), (34, 24), (37, 23), (41, 25), (38, 27), (34, 26),
           (38, 7), (39, 8), (41, 7), (40, 9), (42, 8),                                 # the Seven Sisters
           (36, 3), (4, 21), (22, 25), (4, 10)],
    faint=[(13, 2), (18, 5), (41, 3), (34, 5), (3, 13), (7, 24), (3, 26), (42, 12), (43, 19), (30, 26), (29, 15),
           (23, 4), (21, 9), (18, 16), (16, 19), (17, 21), (13, 22), (14, 27)],
)

# The summer half: the three bright stars of the summer triangle, the Milky Way running down
# through it to the Scorpion with his bright heart and hooked tail; the Keystone, the Crown, the
# lone bright star in the west, the Great Square rising in the east and the lone star of autumn
# under it. Here the ecliptic sags, through the Scorpion's brow: three stars in a bow, left
# unjoined, because a line through them would stand across the end of the body.
SUMMER = dict(
    band=[(15, 19), (15, 19), (15, 20), (16, 20), (16, 20), (16, 21), (16, 21), (17, 21), (17, 22), (17, 22),
          (17, 22), (18, 23), (18, 23), (18, 23), (18, 24), (19, 24), (19, 25), (19, 25), (19, 26), (20, 26),
          (20, 27), (20, 27), (20, 28), (21, 28), (21, 29), (21, 29), (21, 30), (22, 30)],
    arch=lambda x: 13.0 + 5.0 * math.sin(math.pi * (x - 2) / 41.0),
    figures=[
        [(18, 4), (23, 4)], [(24, 6), (20, 12)], [(17, 5), (19, 12)],                   # the summer triangle
        [(28, 4), (32, 5), (31, 9), (28, 8), (28, 4)],                                  # the Keystone
        [(35, 3), (36, 6), (38, 7), (40, 6), (41, 3)],                                  # the Crown
        [(3, 4), (8, 3), (9, 8), (4, 9), (3, 4)],                                       # the Great Square
        [(36, 18), (33, 19)],                                                           # the Scorpion
        [(30, 21), (29, 23), (28, 25), (26, 27), (23, 27), (21, 25), (22, 23)],
    ],
    bright=[(16, 3), (24, 4), (19, 13), (31, 19), (41, 10), (5, 23)],
    stars=[(28, 4), (32, 5), (31, 9), (28, 8),
           (35, 3), (36, 6), (38, 7), (40, 6), (41, 3),
           (3, 4), (8, 3), (9, 8), (4, 9),
           (36, 15), (37, 18), (36, 21), (29, 23), (28, 25), (26, 27), (23, 27), (21, 25), (22, 23),
           (13, 10), (10, 20), (16, 26), (39, 24), (28, 13), (23, 21)],
    faint=[(11, 7), (4, 18), (14, 23), (12, 26), (37, 12), (42, 25), (43, 19), (33, 12), (26, 10), (30, 2),
           (19, 2), (20, 8), (21, 16), (25, 22), (26, 24), (24, 25)],
)


def _blueprint_face():
    """The blueprint, 24 x 14 above the rolled foot: the great dome cut through with its slit
    open, the refractor on its pier looking out of it (the pier a solid mass standing on the
    ground: no floor is drawn across it, a line through a post is a cross); the same dome in plan
    with the pier in the middle; the title block in the corner."""
    rows = ["bbbbbbbbbbbbbbbbbbbbbbbb",
            "bbbbbbbbbbbbbbbbbwwwbbbb",
            "bbbbbwwwwbbbbbbbwbbbwbbb",
            "bbbwwbbbbbbwbbbwbbbbbwbb",
            "bbbwbbbbwbbwbbbwbbwbbwbb",
            "bbwbbbbwbbbbwbbwbbbbbwbb",
            "bbwbbbwbbbbbwbbbwbbbwbbb",
            "bbwbbwmmbbbbwbbbbwwwbbbb",
            "bbwbwbmmbbbbwbbbbbbbbbbb",
            "bbwbbbmmbbbbwbbmmmmmmmmb",
            "bbwbbbmmbbbbwbbmbwwwbbmb",
            "bwwwwwwwwwwwwwbmbbbbbbmb",
            "bbbbbbbbbbbbbbbmmmmmmmmb",
            "bbbbbbbbbbbbbbbbbbbbbbbb"]
    return Sprite("paper_blueprint_face", rows, {"b": EN[2], "m": CR[0], "w": CR[3]})


def _board_face():
    """The blackboard, 28 x 20: tonight's orbit in chalk. The comet's long ellipse with the Sun in
    one focus, the line of apsides ruled faint, the comet on its way out with its tail away from
    the Sun and the radius drawn to it; beside the figure the reckoning in short lines, the result
    underlined; a heading above, and a wiped patch in the corner where an older figure stood."""
    g = _Grid(28, 20)
    centre, a, c = (10.0, 9.5), 8.0, 5.5
    for x, y in ((1, 16), (2, 16), (3, 16), (2, 17), (3, 17), (4, 17), (5, 17), (4, 18), (5, 18), (6, 18)):
        g.put(x, y, "u")                                                        # where it was wiped
    g.line((7, 10), (17, 10), "u", dash=(1, 1))                                 # line of apsides
    g.line((6, 9), (14, 6), "d")                                                # the radius vector
    orbit = _ellipse(centre[0], centre[1], a, math.sqrt(a * a - c * c))
    g.dots([p for p in orbit if p not in ((14, 4), (17, 7))], "c")              # room round the comet
    g.fill(4, 9, 5, 10, "c")                                                    # the Sun
    g.fill(15, 5, 16, 6, "c")                                                   # the comet
    g.dots([(17, 5), (18, 4), (19, 4)], "d")                                    # and its tail
    g.dots([(2, 1), (3, 1), (4, 1), (6, 1), (7, 1)], "d")                       # the heading
    for y, runs in ((7, ((21, 23), (25, 26))), (9, ((21, 22), (24, 26))), (11, ((21, 24), (26, 26)))):
        for x0, x1 in runs:                                                     # the reckoning
            g.line((x0, y), (x1, y), "d")
    g.line((21, 13), (26, 13), "d")
    g.line((21, 14), (26, 14), "c")                                             # the result, underlined
    return g.sprite("paper_board_face", {"u": SL[5], "d": CR[0], "c": CR[3]}, back=SLATE)


# The full Moon, 16 texels across, north up: h highland, s and k the seas, t the bright crater.
MOON = [".....hhhhhh.....",
        "...hhhsshhhhh...",
        "..hhsskkshsshh..",
        ".hhskkkksskkshh.",
        ".hskkkkkskkkshh.",
        "hhskkkkshskkhskh",
        "hskksksshhsskkkh",
        "hskkthsshhskkkhh",
        "hskkshhhhhhskkhh",
        "hhskshhhhhhhkkhh",
        "hhsskkshhhhkshhh",
        ".hhkkkshhhhhhhh.",
        ".hhhsshhhhhhhhh.",
        "..hhhhhtthhhhh..",
        "...hhhhtthhhh...",
        ".....hhhhhh....."]
MOON_INK = {"p": CR[3], "e": EN[1], "w": CR[3], "o": CR[0], "i": CR[0],
            "h": CR[2], "t": CR[3], "s": CR[1], "k": CR[0]}


def _moon_sheet():
    """The map of the Moon as it is printed, 24 x 24, as rows of characters: the heading (a strip
    of chart blue with its stars) across the head of the sheet, the disc engraved in greys inside
    its outline, a line of caption under it."""
    g = _Grid(24, 24, "p")
    g.fill(0, 0, 23, 1, "e")
    g.dots([(4, 1), (6, 0), (10, 1), (13, 0), (20, 1)] + _blocks([(16, 0)]), "w")
    inside = {(x, y) for x in range(18) for y in range(18) if (x - 8.5) ** 2 + (y - 8.5) ** 2 <= 81.0}
    for x, y in inside:
        if any(q not in inside for q in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))):
            g.put(3 + x, 3 + y, "o")
    for j, row in enumerate(MOON):
        for i, ch in enumerate(row):
            if ch != ".":
                g.put(4 + i, 4 + j, ch)
    g.line((8, 22), (10, 22), "i")
    g.line((12, 22), (15, 22), "i")
    return g.text()


def _cut(name, rows, x0, y0, x1, y1, colours):
    """The part of a drawn sheet from texel (x0, y0) up to but not including (x1, y1)."""
    return Sprite(name, [row[x0:x1] for row in rows[y0:y1]], colours)


def _page_face(name, lines):
    """One page of the open log, 4 x 6: the printed heading in chart blue, entries ruled under it."""
    g = _Grid(4, 6, "p")
    g.fill(0, 0, 3, 0, "e")
    for y, x0, x1 in lines:
        g.line((x0, y), (x1, y), "i")
    return g.sprite(name, {"p": CR[3], "e": EN[1], "i": CR[0]})


def _cover_face():
    """The cover of the shut log, 6 x 8: a pasted label with the same heading."""
    g = _Grid(6, 8)
    g.fill(1, 1, 4, 3, "p")
    g.fill(1, 1, 4, 1, "e")
    g.line((2, 2), (3, 2), "i")
    return g.sprite("paper_cover_face", {"p": CR[2], "e": EN[1], "i": CR[0]}, back=LEATHER)


def _plate_face(name, w, d, draw):
    """A glass negative on the light table, seen from above: what the sky left dark is clear and
    shows the lamp's amber, the stars are black specks. One texel of denser glass round the edge."""
    g = _Grid(w, d, "c")
    g.frame(0, 0, w - 1, d - 1, "r")
    draw(g)
    return g.sprite(name, {"c": GL[3], "r": GL[1], "1": IR[1], "2": IR[3], "3": IR[5], "4": GL[2]})


def _comet_plate(g):
    g.fill(2, 4, 3, 5, "1")
    g.dots([(4, 3)], "2")
    g.dots([(5, 2)], "3")
    g.dots([(6, 1)], "4")
    g.dots([(1, 2), (5, 5), (3, 1), (6, 6)], "2")


def _cluster_plate(g):
    g.fill(3, 3, 4, 4, "1")
    g.dots([(5, 2), (2, 5), (5, 5)], "2")
    g.dots([(1, 2), (6, 3), (3, 6), (2, 1)], "3")


def _spectrum_plate(g):
    g.fill(1, 1, 6, 2, "2")
    g.dots([(2, 1), (2, 2), (5, 1), (5, 2)], "c")
    g.dots([(3, 1), (3, 2)], "1")


# ---- the models ---------------------------------------------------------------------------------------
def _bead_frame(m, hw, hh, depth, wide=1.0):
    """A brass bead round a plate 2 hw by 2 hh about the origin, `depth` proud of the wall, a screw
    in each corner."""
    for y in (-hh, hh - wide):
        m.box((-hw, y, 0), (hw, y + wide, depth), BRASS, grain="x", skip="n")
    for x in (-hw, hw - wide):
        m.box((x, -hh + wide, 0), (x + wide, hh - wide, depth), BRASS, grain="y", skip="n")
    for x in (-hw + wide / 2.0, hw - wide / 2.0):
        for y in (-hh + wide / 2.0, hh - wide / 2.0):
            K.rivet(m, (x, y, depth), mat=SCREW)


def _star_chart():
    """The enamel star chart, two blocks by one: the plate screwed to the wall in a brass bead.
    Anchor: on the wall, the middle of the plate."""
    m = M.Model(PREFIX + "star_chart")
    m.box((-15, -7, 0), (15, 7, 1), PLATE, faces={"s": _chart_face()}, skip="n")
    _bead_frame(m, 16, 8, 1.5)
    return m


def _sky_map(name, sky):
    """One of the pair of great charts, three blocks by two: half the sky on an enamelled plate in
    the same brass bead as the small chart. Anchor: on the wall, the middle of the plate."""
    m = M.Model(PREFIX + name)
    m.box((-23, -15, 0), (23, 15, 1), PLATE, faces={"s": _sky_face("paper_" + name + "_face", **sky)}, skip="n")
    _bead_frame(m, 24, 16, 2.0)
    return m


def _blueprint():
    """A blueprint, a block and a half by one: pinned by its upper corners, its foot rolled up the
    way it came off the roll, the cream back of the sheet outside. Anchor: on the wall, the middle
    of the sheet."""
    m = M.Model(PREFIX + "blueprint")
    m.box((-12, -6, 0), (12, 8, 0.5), PAPER, faces={"s": _blueprint_face()}, skip="n")
    m.tube("x", (-7.0, 1.0), -12.0, 12.0, 1.0, PAPER)
    for x in (-10.5, 10.5):
        K.rivet(m, (x, 6.5, 0.5), mat=SCREW)
    return m


def _blackboard():
    """The blackboard, two blocks by one and a half: slate in a dark wood frame, a ledge with two
    chalks and the felt. Anchor: on the wall, the middle of the board."""
    m = M.Model(PREFIX + "blackboard")
    m.box((-14, -10, 0), (14, 10, 1), SLATE, faces={"s": _board_face()}, skip="n")
    for y in (-12, 10):
        m.box((-16, y, 0), (16, y + 2, 2), WOOD, grain="x", skip="n")
    for x in (-16, 14):
        m.box((x, -10, 0), (x + 2, 10, 2), WOOD, grain="y", skip="n")
    m.box((-15, -11, 2), (15, -10, 4.5), WOOD, grain="x")                       # the ledge
    m.box((-9, -10, 3), (-6, -9.25, 3.75), CHALK, grain="x")
    m.box((1, -10, 2.5), (3, -9.25, 3.25), CHALK, grain="x")
    m.box((7, -10, 2.25), (11, -9.25, 4.25), FELT, grain="x")                   # the felt and its back
    m.box((7, -9.25, 2.25), (11, -8.5, 4.25), WOOD, grain="x")
    return m


def _moon_map():
    """The map of the Moon, a block and a half square: a printed sheet pinned by three corners,
    the fourth standing off the wall. Anchor: on the wall, the middle of the sheet."""
    m = M.Model(PREFIX + "moon_map")
    rows = _moon_sheet()
    m.box((-12, -8, 0), (12, 12, 0.5), PAPER, faces={"s": _cut("paper_moon_head", rows, 0, 0, 24, 20, MOON_INK)},
          skip="n")
    m.box((-12, -12, 0), (8, -8, 0.5), PAPER, faces={"s": _cut("paper_moon_foot", rows, 0, 20, 20, 24, MOON_INK)},
          skip="nu")
    m.box((8, -12, 0), (12, -8, 0.5), PAPER, faces={"s": _cut("paper_moon_corner", rows, 20, 20, 24, 24, MOON_INK)},
          rot=("y", -25.0, (8.0, -10.0, 0.0)))
    for x, y in ((-10.5, 10.5), (10.5, 10.5), (-10.5, -10.5)):
        K.rivet(m, (x, y, 0.5), mat=SCREW)
    return m


def _logbook():
    """The observing log lying open, the left page full and the right one begun, the pencil across
    it and the marker ribbon down the gutter. Anchor: the middle of its underside."""
    m = M.Model(PREFIX + "logbook")
    m.box((-5, 0, -3.5), (5, 0.5, 3.5), LEATHER, skip="d")
    left = _page_face("paper_page_left", [(2, 0, 3), (4, 0, 2)])
    right = _page_face("paper_page_right", [(2, 0, 1)])
    m.box((-4.5, 0.5, -3), (-0.5, 1.25, 3), PAPER, faces={"u": left}, skip="d")
    m.box((0.5, 0.5, -3), (4.5, 1.25, 3), PAPER, faces={"u": right}, skip="d")
    m.box((-0.5, 0.5, 1.5), (0.5, 0.75, 3.75), RIBBON, skip="d")
    m.box((-0.5, 0, 3.5), (0.5, 0.5, 3.75), RIBBON, skip="dun")
    m.beam((1.25, 1.5, 2.25), (4.25, 1.5, -0.75), 0.5, 0.5, PENCIL)
    return m


def _logbook_shut():
    """A log book shut: leather boards, the edge of the pages between them, a pasted label, the
    end of the marker hanging out at the foot. Anchor: the middle of its underside; the spine is on
    its west side."""
    m = M.Model(PREFIX + "logbook_shut")
    m.box((-3, 0, -4), (3, 0.5, 4), LEATHER, skip="d")
    m.box((-3, 0.5, -4), (-2.5, 1.5, 4), LEATHER, skip="du")
    m.box((-2.5, 0.5, -3.5), (2.5, 1.5, 3.5), PAPER, skip="duw")
    m.box((-3, 1.5, -4), (3, 2, 4), LEATHER, faces={"u": _cover_face()}, skip="d")
    m.box((0.5, 1.0, 3.5), (1.5, 1.25, 4.25), RIBBON, skip="n")
    m.box((0.5, 0, 4), (1.5, 1.0, 4.25), RIBBON, skip="dun")
    return m


def _photo_plate(name, w, d, draw):
    """A glass negative lying on the light table, lit from below. Anchor: the middle of its
    underside."""
    m = M.Model(PREFIX + name)
    m.box((-w / 2.0, 0, -d / 2.0), (w / 2.0, 0.5, d / 2.0), GLASS, faces={"u": _plate_face("paper_" + name, w, d, draw)},
          skip="d", emit=15, shade=False)
    return m


# name -> how it is made and how it is mounted
SPEC = {
    "star_chart": dict(build=_star_chart, mount="wall"),
    "sky_map": dict(build=lambda: _sky_map("sky_map", WINTER), mount="wall"),
    "sky_map_b": dict(build=lambda: _sky_map("sky_map_b", SUMMER), mount="wall"),
    "blueprint": dict(build=_blueprint, mount="wall"),
    "blackboard": dict(build=_blackboard, mount="wall"),
    "moon_map": dict(build=_moon_map, mount="wall"),
    "logbook": dict(build=_logbook, mount="floor"),
    "logbook_shut": dict(build=_logbook_shut, mount="floor"),
    "photo_plate": dict(build=lambda: _photo_plate("photo_plate", 8, 8, _comet_plate), mount="floor"),
    "photo_plate_b": dict(build=lambda: _photo_plate("photo_plate_b", 8, 8, _cluster_plate), mount="floor"),
    "photo_plate_c": dict(build=lambda: _photo_plate("photo_plate_c", 8, 4, _spectrum_plate), mount="floor"),
}
KINDS = tuple(SPEC)
SCALE = {PREFIX + name: 1.0 for name in SPEC}


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + name: spec["build"]() for name, spec in SPEC.items()}


def models():
    return dict(_models())


# ---- placing ------------------------------------------------------------------------------------------
def place(canvas, kind, pos, facing="south", origin=(0, 0, 0), yaw=None, lie=False, **opts):
    """Put one piece into the scene; returns the number of display entities (1).

    kind     one of KINDS.
    pos      scene coordinates. A wall piece (star_chart, sky_map, sky_map_b, blueprint, blackboard,
             moon_map): the point on the wall face where its middle goes, `facing` the way that
             face looks; put it on a sixteenth of a block and its texels lie on the wall's. A desk
             piece (logbook, logbook_shut, photo_plate*): the middle of its underside on the desk
             top; `yaw` turns it.
    lie      lay a wall piece flat instead, face up, its head to the north (then turned by `yaw`):
             pos is the middle of its back on the desk top.
    opts     go to artkit.models.display (brightness, view).

    Sizes in texels, wide by high (by proud of the wall): star_chart 32 x 16 (2), sky_map and
    sky_map_b 48 x 32 (2.5), blueprint 24 x 16 (2), blackboard 32 x 24 (4.5), moon_map 24 x 24 (2);
    logbook 10 x 7 on the desk, logbook_shut 6 x 8, the plates 8 x 8, 8 x 8 and 8 x 4.
    """
    spec = SPEC[kind]
    mount = spec["mount"]
    if lie and mount == "wall":
        mount = "floor"
        opts["turns"] = (("x", -90.0),) + tuple(opts.get("turns", ()))
    if yaw is None:
        yaw = K.FACING[facing] if mount == "wall" else 0.0
    return K.put(canvas, _models()[PREFIX + kind], pos, mount=mount, yaw=yaw, origin=origin, **opts)


def build(canvas, origin=(0, 0, 0)):
    """Nothing of this family is dressed onto the building by itself: the rooms hang and lay out
    their papers with place()."""
    return 0
