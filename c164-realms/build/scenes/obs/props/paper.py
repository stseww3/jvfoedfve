"""The paper family (plan ART-PLAN 7.3; parts/A6-props.md 2.7; card packages/props/paper.md).

What lies on the desks and hangs on the walls of a working observatory: star charts, blueprints,
a blackboard with tonight's orbit on it, a map of the Moon, log books, glass negatives. One
vocabulary for all of them: cream paper; the chart blue of the enamel signs with the drawing left
in cream; brass for whatever holds a sheet (a bead round it, a screw, a pin); and an edge that
curls where a sheet hangs free. The drawings are figures, lines and dots; nothing is written out.

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

EN, CR, BR, IR, SL, OP = (P.RAMPS[k] for k in ("enamel", "cream", "brass", "iron", "slate", "opal"))

BRASS = K.BRASS
SCREW = K.flat("brass", 5)                                      # screw heads and pins catch the light
PAPER = K.CREAM                                                 # a sheet seen edge on, a rolled sheet
BOARD = K.flat("cream", 2)                                      # the edge of a mount
PLATE = K.flat("enamel", 0)                                     # the edge of an enamelled plate
WOOD = P.mat("dark_wood")
LEATHER = P.mat("dark_wood", kind="plain", noise=0.12, base=1)  # bindings (R1: leather is dark wood)
SLATE = P.mat("slate", noise=0.16, bevel=0)
CHALK = K.flat("cream", 3)
FELT = K.flat("cream", 1)
GLASS = K.flat("opal", 0)                                       # the edge of a glass negative
PENCIL = K.flat("brass", 3)


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

    def ring(self, cx, cy, r, ch, dash=None, arc=(0.0, 360.0)):
        """A one-texel circle about (cx, cy); the centre may lie between texels."""
        self.dots(_dashed(_thin(_circle(cx, cy, r, arc)), dash), ch)

    def disc(self, cx, cy, r, ch):
        for y in range(self.h):
            for x in range(self.w):
                if math.hypot(x - cx, y - cy) <= r:
                    self.put(x, y, ch)

    def sprite(self, name, colours, back=None):
        return Sprite(name, ["".join(row) for row in self.rows], colours, back)


def _line(p, q):
    (x0, y0), (x1, y1) = p, q
    n = max(abs(x1 - x0), abs(y1 - y0))
    return [(round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n)) for i in range(n + 1)] if n else [p]


def _circle(cx, cy, r, arc=(0.0, 360.0)):
    out = []
    steps = max(16, int(r * 16))
    for i in range(steps + 1):
        t = math.radians(arc[0] + (arc[1] - arc[0]) * i / steps)
        p = (int(math.floor(cx + r * math.cos(t) + 0.5)), int(math.floor(cy - r * math.sin(t) + 0.5)))
        if p not in out:
            out.append(p)
    return out


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


# ---- the faces ----------------------------------------------------------------------------------------
def _chart_face():
    """The enamel star chart, 30 x 14: a graduated border as on a map, and inside it four figures
    of the northern sky drawn star to star, a small cluster and loose stars of three magnitudes.
    A bright star is a block of four texels and a faint one a grey dot; none is drawn as a cross,
    and no two lines cross."""
    g = _Grid(30, 14, "e")
    for x in range(30):
        for y in (0, 13):
            g.put(x, y, "g" if (x // 2) % 2 else "e")
    for y in range(14):
        for x in (0, 29):
            g.put(x, y, "g" if (y // 2) % 2 else "e")
    dipper = [(2, 4), (5, 3), (8, 3), (10, 5), (14, 4), (14, 7), (11, 8), (10, 5)]
    zigzag = [(17, 2), (19, 5), (22, 3), (25, 6), (28, 3)]
    triangle = [(16, 9), (21, 8), (19, 12), (16, 9)]
    crown = [(2, 8), (3, 10), (5, 11), (7, 10), (8, 8)]
    for figure in (dipper, zigzag, triangle, crown):
        for a, b in zip(figure, figure[1:]):
            g.line(a, b, "l")
    g.dots(dipper + zigzag + triangle + crown, "s")
    g.dots([(24, 10), (25, 9), (26, 10), (27, 9), (26, 12), (28, 11)], "s")     # the cluster
    g.dots([(15, 1), (5, 6), (23, 12), (28, 7)], "s")
    g.dots([(8, 1), (11, 1), (25, 1), (16, 6), (22, 7), (1, 12), (14, 10), (7, 12), (20, 1)], "f")
    for x, y in ((14, 4), (22, 2), (11, 11)):                                   # first magnitude
        g.fill(x, y, x + 1, y + 1, "s")
    return g.sprite("paper_chart_face", {"e": EN[1], "g": EN[3], "l": EN[3], "s": CR[3], "f": CR[0]})


def _blueprint_face():
    """The blueprint, 24 x 14 above the rolled foot: the great dome cut through, the refractor on
    its pier under it and the observing floor; the same dome in plan with the pier in the middle;
    the title block in the corner."""
    rows = ["bbbbbbbbbbbbbbbbbbbbbbbb",
            "bbbbbbbbbbbbbbbbbwwwbbbb",
            "bbbbbwwwwwbbbbbbwbbbwbbb",
            "bbbwwbbbbbwwbbbwbbbbbwbb",
            "bbbwbbbbwbbwbbbwbbwbbwbb",
            "bbwbbbbwbbbbwbbwbbbbbwbb",
            "bbwbbbwmbbbbwbbbwbbbwbbb",
            "bbwbbwbmbbbbwbbbbwwwbbbb",
            "bbwmmmmmmmmmwbbbbbbbbbbb",
            "bbwbbbbmbbbbwbbmmmmmmmmb",
            "bbwbbbbmbbbbwbbmbwwwbbmb",
            "bwwwwwwwwwwwwwbmbbbbbbmb",
            "bbbbbbbbbbbbbbbmmmmmmmmb",
            "bbbbbbbbbbbbbbbbbbbbbbbb"]
    return Sprite("paper_blueprint_face", rows, {"b": EN[2], "m": CR[0], "w": CR[3]})


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


def _moon_face():
    """The Moon, 22 x 22: a print of the full Moon on a night-blue field inside a cream mount: the
    seas in two greys, the bright crater in the south."""
    g = _Grid(22, 22, "p")
    g.fill(2, 2, 19, 19, "n")
    for j, row in enumerate(MOON):
        for i, ch in enumerate(row):
            if ch != ".":
                g.put(3 + i, 3 + j, ch)
    return g.sprite("paper_moon_face", {"p": CR[3], "n": EN[0], "h": CR[2], "t": CR[3], "s": CR[1], "k": CR[0]})


def _page_face(name, lines):
    """One page of the open log, 4 x 6: ruled entries, the gutter side in shade."""
    g = _Grid(4, 6, "p")
    for y, x0, x1 in lines:
        g.line((x0, y), (x1, y), "i")
    return g.sprite(name, {"p": CR[3], "i": CR[0]})


def _cover_face():
    """The cover of the shut log, 6 x 8: a pasted label."""
    g = _Grid(6, 8)
    g.fill(1, 1, 4, 3, "p")
    g.line((2, 2), (3, 2), "i")
    return g.sprite("paper_cover_face", {"p": CR[2], "i": CR[0]}, back=LEATHER)


def _plate_face(name, w, d, draw):
    """A glass negative on the light table, seen from above: what the sky left dark shows clear,
    the stars are black specks. One texel of denser glass round the edge."""
    g = _Grid(w, d, "c")
    g.frame(0, 0, w - 1, d - 1, "r")
    draw(g)
    return g.sprite(name, {"c": OP[2], "r": OP[0], "1": IR[1], "2": IR[3], "3": IR[5], "4": OP[1]})


def _comet_plate(g):
    g.fill(2, 4, 3, 5, "1")
    g.dots([(4, 3)], "2")
    g.dots([(5, 2)], "3")
    g.dots([(6, 1)], "4")
    g.dots([(1, 2), (5, 5), (3, 1), (6, 6)], "2")


def _cluster_plate(g):
    g.fill(3, 3, 4, 4, "1")
    g.dots([(2, 4), (5, 3), (4, 2), (3, 5)], "2")
    g.dots([(1, 2), (6, 5), (5, 6), (2, 6), (6, 1)], "3")


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
    """The map of the Moon, a block and a half square: a print in a cream mount and a brass bead.
    Anchor: on the wall, the middle of the mount."""
    m = M.Model(PREFIX + "moon_map")
    m.box((-11, -11, 0), (11, 11, 1), BOARD, faces={"s": _moon_face()}, skip="n")
    _bead_frame(m, 12, 12, 1.5)
    return m


def _logbook():
    """The observing log lying open, the left page full and the right one half written, the pencil
    across it. Anchor: the middle of its underside."""
    m = M.Model(PREFIX + "logbook")
    m.box((-5, 0, -3.5), (5, 0.5, 3.5), LEATHER, skip="d")
    left = _page_face("paper_page_left", [(1, 0, 2), (2, 0, 3), (3, 0, 1), (4, 0, 3)])
    right = _page_face("paper_page_right", [(1, 0, 3), (2, 0, 1)])
    m.box((-4.5, 0.5, -3), (-0.5, 1.25, 3), PAPER, faces={"u": left}, skip="d")
    m.box((0.5, 0.5, -3), (4.5, 1.25, 3), PAPER, faces={"u": right}, skip="d")
    m.beam((1.25, 1.5, 2.25), (4.25, 1.5, -0.75), 0.5, 0.5, PENCIL)
    return m


def _logbook_shut():
    """A log book shut: leather boards, the edge of the pages between them, a pasted label.
    Anchor: the middle of its underside; the spine is on its west side."""
    m = M.Model(PREFIX + "logbook_shut")
    m.box((-3, 0, -4), (3, 0.5, 4), LEATHER, skip="d")
    m.box((-3, 0.5, -4), (-2.5, 1.5, 4), LEATHER, skip="du")
    m.box((-2.5, 0.5, -3.5), (2.5, 1.5, 3.5), PAPER, skip="duw")
    m.box((-3, 1.5, -4), (3, 2, 4), LEATHER, faces={"u": _cover_face()}, skip="d")
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
    pos      scene coordinates. A wall piece (star_chart, blueprint, blackboard, moon_map): the point
             on the wall face where its middle goes, `facing` the way that face looks; put it on a
             sixteenth of a block and its texels lie on the wall's. A desk piece (logbook,
             logbook_shut, photo_plate*): the middle of its underside on the desk top; `yaw` turns it.
    lie      lay a wall piece flat instead, face up, its head to the north (then turned by `yaw`):
             pos is the middle of its back on the desk top.
    opts     go to artkit.models.display (brightness, view).
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
