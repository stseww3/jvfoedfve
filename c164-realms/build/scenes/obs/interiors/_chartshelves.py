"""interiors/_chartshelves -- the bookcase wall of the chart room (card
plan/packages/interiors/chartroom.md). The room is interiors/chartroom.py (chart, c350): it asks
this module for models() and calls place(); the name starts with an underscore, so the category's
auto-discovery does not take it for a room.

The whole south wall, floor to ceiling: twelve blocks by seven, six texels deep. It is a piece of
joinery with an order of its own, so that from the door (V9) it reads as a library and not as a
field of spines:

  five bays       four piers between them, a cheek at each end. The middle bay stands on the room's
                  axis, behind the plate viewer and the comet: it holds no books. Below, a cupboard
                  of two panelled doors; above, a plain sunk field for the room's wall clock
                  (CLOCK_AT, CLOCK_FIELD), and nothing in it that the eye could take for a light.
  two storeys     The first ends in the board that carries the ladder rail of props/furniture (its
                  middle 44.5 texels over the floor; the ladder's rollers ride on it and reach 46.8)
                  and in a cornice from 47. Below that cornice nothing stands proud of the front,
                  so the ladder runs the whole wall. The piers of the second storey stand a texel
                  proud, on the cornice, and their faces are bare from 72 to 88 texels (LAMP_Y):
                  the room fixes its bracket lamps there.
  entablature     a block high under the ceiling: an architrave, a frieze with the letter of each
                  bay on an enamel plate, a cornice of two steps. The piers run on through the
                  frieze as blocks.
  what is kept    The books stand in runs, a set of volumes in one binding and then the next, as
                  the yearly volumes of a library do: from far that is a few quiet masses of colour
                  to a shelf, not confetti. The two outer bays have a plan chest for the flat sheets
                  in their foot; the two bays beside the middle keep the great atlases lying in
                  piles in theirs and the rolled charts in a rack of pigeonholes at the height of
                  the eye of who stands on the ladder; the plates' pasteboard boxes are brown card,
                  not white, so that no shelf is lighter than the light table.

Drawn in the wall's own frame, texels: U from the east end of the wall (the left hand of who looks
at it), Y from the floor, Z from the wall into the room. Fifteen display entities: five strips,
each cut where a pier ends, three tiers to a strip; each is held on the wall at the middle of its
own tier, so the cell before it lights it.

    python -m scenes.obs.interiors._chartshelves      # the count of entities and of elements
"""
import functools
import random

import numpy as np

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import palette as P
from ..main import shell
from ..props import _kit as K

PREFIX = "int_chart_shelf_"
PX = 1 / 16.0

ROOM = shell.ROOMS["chart room"]
X0, Z0, X1, Z1 = ROOM["box"]                    # 2, 7, 13, 25
FEET = ROOM["feet"]                             # 7
EAST, SOUTH = float(X1 + 1), float(Z1 + 1)      # 14.0, 26.0: the east end of the wall, the wall's face
WIDE = (X1 + 1 - X0) * 16.0                     # 192
HIGH = (ROOM["ceiling"] - FEET) * 16.0          # 112

# ---- the order of the wall (texels) -----------------------------------------------------------------
FRONT = 6.0                                     # the face of the case
BAYS = ((4.0, 35.0), (41.0, 72.0), (78.0, 114.0), (120.0, 151.0), (157.0, 188.0))
PIERS = ((35.0, 41.0), (72.0, 78.0), (114.0, 120.0), (151.0, 157.0))
CHEEKS = ((0.0, 4.0), (188.0, 192.0))           # the panelling of the long walls hides three texels of each below the sill
STRIPS = ((0.0, 41.0), (41.0, 78.0), (78.0, 114.0), (114.0, 151.0), (151.0, 192.0))     # one model wide each
TIERS = ((0.0, 48.0), (48.0, 96.0), (96.0, HIGH))                                       # one model high each
MIDDLE = 2                                      # the bay on the axis
PLINTH = 4.0
RAIL = (43.0, 47.0)                             # the board the ladder rail is fixed on: flat from end to end
CORNICE = (47.0, 49.0)                          # the first storey's cornice, a texel proud: its upper half is the
#                                                 foot of the second tier
LOW_BOARDS = (15.0, 25.0, 34.0)                 # the undersides of the first storey's shelves
CHEST_TOP = (24.0, 26.0)                        # the top of a plan chest
HIGH_BOARDS = (60.0, 72.0, 84.0)                # of the second storey's
HEAD = (95.0, 96.0)                             # the board that closes the second storey
CAPITAL = 90.0                                  # where a pier's capital begins
ARCHITRAVE, FRIEZE, CROWN = (96.0, 98.0), (98.0, 107.0), (107.0, 109.0)
FIELD_U, FIELD_Y = (82.0, 110.0), (53.0, 91.0)  # the sunk field of the middle bay
FIELD_Z = 5.0                                   # its face

# ---- for the room (scene coordinates) ---------------------------------------------------------------
FRONT_Z = SOUTH - FRONT * PX                    # 25.625: the plane of the case's front, where the rail runs
PIER_X = tuple(EAST - (a + b) / 32.0 for a, b in PIERS)     # 11.625, 9.3125, 6.6875, 4.375: the piers' middles
PIER_FACE_Z = SOUTH - (FRONT + 1.0) * PX        # 25.5625: the face of a pier above the first cornice
LAMP_Y = (FEET + 4.5, FEET + 5.5)               # a pier's face is bare between these
CLOCK_AT = (EAST - 96.0 * PX, FEET + 4.5, SOUTH - FIELD_Z * PX)     # (8, 11.5, 25.6875): the middle of the field
CLOCK_FIELD = ((FIELD_U[1] - FIELD_U[0]) * PX, (FIELD_Y[1] - FIELD_Y[0]) * PX)      # 1.75 by 2.375 blocks, flat

# ---- materials ----------------------------------------------------------------------------------------
WOOD = P.mat("dark_wood")
WOOD_L = P.mat("dark_wood", base=3)
WOOD_D = P.mat("dark_wood", base=1)
SHADOW = K.flat("dark_wood", 0)                 # the inside of the case
BRASS, BRASS_D = K.BRASS, K.BRASS_D
CARD = P.mat("old_copper", kind="plain", noise=0.06, base=1, bevel=1)       # brown pasteboard
CARD_D = P.mat("old_copper", kind="plain", noise=0.06, base=0, bevel=1)
LABEL = K.flat("cream", 1)
CR, EN, BR, DW, OC = (P.RAMPS[k] for k in ("cream", "enamel", "brass", "dark_wood", "old_copper"))

# A rolled chart, end on: a ring of paper round its dark hollow. Old sheets are grey, the ones in a
# wrapper brown, and only the odd new one is pale: a rack of white rings on dark wood read as dice.
ROLLS = tuple((Sprite(f"chart_shelf_roll_{k}", ["aba", "bcb", "aba"], {"a": a, "b": b, "c": DW[0]}), body)
              for k, (a, b, body) in enumerate((
                  (OC[2], CR[0], P.mat("cream", base=0, bevel=0)),
                  (OC[1], OC[3], P.mat("old_copper", kind="plain", noise=0.06, base=2, bevel=0)),
                  (CR[0], CR[1], P.mat("cream", base=1, bevel=0)))))
CARD_LABEL = K.flat("cream", 0)                 # the card on a drawer's front
KEYHOLE = Sprite("chart_shelf_key", ["b", "k", "b"], {"b": BR[2], "k": DW[0]})

# the bays' letters, five high, and the enamel plate each stands on. The middle bay is an even number
# of texels wide, so its letter is too: every plate sits on the texel grid at the middle of its bay.
_LETTERS = {
    "A": (".#.", "#.#", "###", "#.#", "#.#"),
    "B": ("##.", "#.#", "##.", "#.#", "##."),
    "C": (".###", "#...", "#...", "#...", ".###"),
    "D": ("##.", "#.#", "#.#", "#.#", "##."),
    "E": ("###", "#..", "##.", "#..", "###"),
}


def _plate(letter):
    wide = len(_LETTERS[letter][0]) + 4
    rows = ["r" * wide] + ["rg" + "".join("w" if ch == "#" else "g" for ch in row) + "gr" for row in _LETTERS[letter]] + ["r" * wide]
    return Sprite(f"chart_shelf_plate_{letter.lower()}", rows, {"r": EN[3], "g": EN[1], "w": CR[2]})


# the bindings a bay's books are chosen from: (ramp, step); a binding named twice is chosen twice as often
BROWN = (("old_copper", 0), ("old_copper", 1), ("old_copper", 2), ("dark_wood", 3), ("dark_wood", 4))
BLUE = (("enamel", 0), ("enamel", 1), ("enamel", 2), ("enamel", 1))
GREY = (("iron", 3), ("iron", 4))
PALE = (("cream", 0),)
BINDINGS = (BROWN + BROWN + BLUE + GREY, BLUE + BLUE + GREY + PALE, (), BLUE + BROWN + BROWN + PALE, BROWN + GREY + GREY + BLUE)


class _Spines:
    """The picture of a shelf of books from the front. The books stand in runs: a set of volumes in
    one binding, as wide and as tall as one another, then the next set. A volume is one to three
    texels wide; its right edge is a step darker, so every spine can be counted. What is tooled on
    a spine is a title label in the upper third or a band at head and tail in the binding's own
    lighter tone: nothing that runs across a spine at its middle, so that no two strokes cross.
    It stands in for a material on one face (artkit.models asks a material for its name and paint())."""

    def __init__(self, name, bindings, full=0.94):
        self.name, self.bindings, self.full = name, bindings, full

    def paint(self, w, h, grain="u", seed=0):
        rnd = random.Random(f"{self.name}:{w}:{h}:{seed}")
        out = np.empty((h, w, 4), dtype=np.uint8)
        out[..., :3] = P.colour("dark_wood", 0)
        out[..., 3] = 255
        x = 0
        while x < w:
            ramp, step = rnd.choice(self.bindings)
            width = rnd.choice((1, 2, 2, 3, 3))
            top = rnd.choice((0, 1, 1, 2)) if h > 6 else rnd.choice((0, 1))
            tooling = rnd.choice(("label", "label", "bands", "plain")) if width == 3 else rnd.choice(("dot", "plain", "plain"))
            for _ in range(rnd.choice((2, 3, 4, 5, 6, 8)) if width > 1 else rnd.choice((2, 3, 4))):
                if x + width > w:
                    break
                self._volume(out, x, width, top, h, ramp, step, tooling)
                x += width
            if rnd.random() > self.full:
                x += rnd.choice((1, 2, 3))          # a gap where a volume is out
            if x + 1 >= w:
                break
        return out

    @staticmethod
    def _volume(out, x, width, top, h, ramp, step, tooling):
        steps = len(P.RAMPS[ramp])
        out[top:, x:x + width, :3] = P.colour(ramp, step)
        if width >= 2:
            out[top:, x + width - 1, :3] = P.colour(ramp, step - 1) if step else P.colour("dark_wood", 0)
        pale = ramp == "cream"
        if tooling == "label" and h - top >= 6:
            out[top + 1:top + 3, x:x + width - 1, :3] = P.colour("iron", 2) if pale else P.colour("cream", 0)
        elif tooling == "bands" and h - top >= 6:
            tone = P.colour(ramp, min(steps - 1, step + 1))
            out[top + 1, x:x + width - 1, :3] = tone
            out[h - 2, x:x + width - 1, :3] = tone
        elif tooling == "dot" and width == 2 and h - top >= 5:
            out[top + 2, x, :3] = P.colour("iron", 2) if pale else P.colour("brass", 2)


class _Pile:
    """The picture of a pile of great atlases lying flat, their spines to the room: each two or
    three texels thick, as long as the pile or a little shorter, a title label near one end."""

    def __init__(self, name, bindings):
        self.name, self.bindings = name, bindings

    def paint(self, w, h, grain="u", seed=0):
        rnd = random.Random(f"{self.name}:{w}:{h}:{seed}")
        out = np.zeros((h, w, 4), dtype=np.uint8)
        y = h
        while y > 0:
            thick = min(y, rnd.choice((2, 2, 3)))
            ramp, step = rnd.choice(self.bindings)
            a = rnd.choice((0, 0, 1))
            b = w - rnd.choice((0, 0, 1, 2))
            out[y - thick:y, a:b, :3] = P.colour(ramp, step)
            out[y - thick:y, a:b, 3] = 255
            if step:
                out[y - 1, a:b, :3] = P.colour(ramp, step - 1)
            if thick == 3 and ramp != "cream":
                out[y - 2, a + 2:a + 5, :3] = P.colour("cream", 0)
            y -= thick
        out[out[..., 3] == 0] = (*P.colour("dark_wood", 0), 255)
        return out


class _Piece:
    """One display entity of the wall: a strip of it, one tier high. What is drawn is given in the
    wall's frame and lands in the model's: x from the strip's middle, y from the tier's foot."""

    def __init__(self, strip, tier):
        self.strip, self.tier = strip, tier
        self.u0, self.u1 = STRIPS[strip]
        self.y0, self.y1 = TIERS[tier]
        self.mid = (self.u0 + self.u1) / 2.0
        self.m = M.Model(f"{PREFIX}{'abcde'[strip]}{tier + 1}", anchor=(0.0, (self.y1 - self.y0) / 2.0, 0.0))
        self.rnd = random.Random(1009 * strip + 31 * tier + 7)
        self.n = 0

    def at(self, u, y, z):
        return (u - self.mid, y - self.y0, z)

    def box(self, u, y, z, mat, rot=None, **kw):
        if rot is not None:
            axis, angle, about = rot
            rot = (axis, angle, self.at(*about))
        self.m.box(self.at(u[0], y[0], z[0]), self.at(u[1], y[1], z[1]), mat, rot=rot, **kw)

    def seed(self):
        self.n += 1
        return 100 * (10 * self.strip + self.tier) + self.n

    def bay(self):
        return next(((a, b) for a, b in BAYS if self.u0 <= a and b <= self.u1), None)

    def piers(self):
        return [(a, b) for a, b in PIERS if self.u0 <= a and b <= self.u1]

    def cheeks(self):
        return [(a, b) for a, b in CHEEKS if self.u0 <= a and b <= self.u1]


# ---- what stands on the shelves ---------------------------------------------------------------------
def _books(p, u, y, top, bindings, full=0.94):
    """A shelf of books between u[0] and u[1], standing on y, under a board whose underside is top."""
    height = (top - y) - p.rnd.choice((1, 1, 2))
    a, b = u
    if p.rnd.random() < 0.3:                    # the row stops short of one end, and its last book leans
        short = float(p.rnd.choice((5, 6, 8)))
        if p.rnd.random() < 0.5:
            _lean(p, (a + short - 3.0, a + short - 1.0), y, height - 1.0, bindings, -1.0)
            a += short
        else:
            _lean(p, (b - short + 1.0, b - short + 3.0), y, height - 1.0, bindings, 1.0)
            b -= short
    seed = p.seed()
    spines = _Spines(f"chart_shelf_spines_{p.strip}_{p.tier}_{seed}", bindings, full)
    p.box((a, b), (y, y + height), (1.0, 4.5), SHADOW, skip="nd", faces={"s": spines}, seed=seed)


def _lean(p, u, y, height, bindings, side):
    """One book leaning against the end of its row: side -1 when the row is on its right, 1 when it
    is on its left. It stands on the corner of its foot that is nearer the row, a hair behind the
    row's own spines."""
    ramp, step = p.rnd.choice(bindings)
    mat = P.mat(ramp, kind="plain", noise=0.05, base=step, bevel=0)
    foot = (u[1] if side < 0 else u[0], y, 2.5)
    p.box(u, (y, y + height), (1.5, 4.25), mat, rot=("z", 14.0 * side, foot), skip="n", grain="y")


def _boxes(p, u, y, top):
    """Pasteboard plate boxes side by side, a label on each: brown card, the odd one darker."""
    x = u[0] + p.rnd.choice((0.0, 1.0))
    while x + 6.0 <= u[1]:
        height = min(top - y - 1.0, float(p.rnd.choice((7, 8, 8))))
        mat = CARD_D if p.rnd.random() < 0.25 else CARD
        p.box((x, x + 6.0), (y, y + height), (1.0, 5.0), mat, skip="nd", grain="y")
        p.box((x + 1.5, x + 4.5), (y + height - 4.0, y + height - 2.0), (5.0, 5.25), LABEL, skip="n")
        x += 6.0 + p.rnd.choice((0.0, 1.0, 1.0))


def _piles(p, u, y, top, bindings):
    """Great atlases lying flat in two piles, a portfolio standing between them and the cheek."""
    a, b = u
    seed = p.seed()
    left = _Pile(f"chart_shelf_pile_{p.strip}_{seed}", bindings)
    right = _Pile(f"chart_shelf_pile_{p.strip}_{seed}b", bindings)
    high_l, high_r = float(p.rnd.choice((7, 8))), float(p.rnd.choice((5, 6)))
    p.box((a + 1.0, a + 14.0), (y, y + high_l), (1.0, 5.0), SHADOW, skip="nd", faces={"s": left}, seed=seed)
    p.box((b - 12.0, b - 1.0), (y, y + high_r), (1.0, 5.0), SHADOW, skip="nd", faces={"s": right}, seed=seed + 1)
    folio = P.mat("enamel", kind="plain", noise=0.05, base=1, bevel=0)
    p.box((a + 15.0, a + 17.0), (y, top - 2.0), (1.5, 5.0), folio, rot=("z", 10.0, (a + 15.0, y, 3.0)), skip="n", grain="y")
    p.box((a + 17.0, a + 18.0), (y, top - 3.0), (1.5, 5.0), CARD, rot=("z", 6.0, (a + 17.0, y, 3.0)), skip="n", grain="y")


def _pigeonholes(p, u, y, top):
    """A rack of pigeonholes for rolled charts: two groups of three columns either side of an upright,
    four rows; nearly every hole holds a roll, end on, some further out than others. A hole is four
    texels each way, a roll three."""
    a, b = u
    p.box((a, a + 1.0), (y, top), (1.0, 5.5), WOOD, grain="y")
    p.box((b - 1.0, b), (y, top), (1.0, 5.5), WOOD, grain="y")
    p.box((a + 15.0, b - 15.0), (y, top), (1.0, 5.5), WOOD, grain="y")
    floors = [y + 2.0 + 5.0 * i for i in range(4)]
    p.box((a + 1.0, b - 1.0), (y, y + 2.0), (1.0, 5.5), WOOD, grain="x")
    p.box((a + 1.0, b - 1.0), (floors[-1] + 4.0, top), (1.0, 5.5), WOOD, grain="x")
    for f in floors[1:]:
        p.box((a + 1.0, b - 1.0), (f - 1.0, f), (1.0, 5.25), WOOD, grain="x")
    columns = [a + 1.0 + 5.0 * i for i in range(3)] + [b - 15.0 + 5.0 * i for i in range(3)]
    for c in columns:
        if c not in (a + 1.0, b - 15.0):
            p.box((c - 1.0, c), (y + 2.0, floors[-1] + 4.0), (1.0, 5.25), WOOD, grain="y")
    for f in floors:
        for c in columns:
            if p.rnd.random() < 0.08:
                continue
            out = p.rnd.choice((4.5, 4.5, 5.0, 5.0, 5.0, 5.75))
            end, body = ROLLS[p.rnd.choice((0, 0, 0, 0, 0, 1, 1, 1, 2))]
            p.box((c + 0.5, c + 3.5), (f, f + 3.0), (1.0, out), body, skip="n", grain="z", faces={"s": end})


def _chest(p, u):
    """A plan chest in the foot of a bay: five shallow drawers for the flat sheets, each with a bar
    pull at either hand and a card at its middle."""
    a, b = u
    mid = (a + b) / 2.0
    p.box((a, b), (PLINTH, CHEST_TOP[0]), (1.0, 5.5), WOOD_D, skip="n", grain="x")
    for i in range(5):
        y = PLINTH + 1.0 + 4.0 * i              # three texels of front, one of the carcass between two
        p.box((a + 1.0, b - 1.0), (y, y + 3.0), (5.5, FRONT - 0.25), WOOD, skip="n", grain="x")
        for x in (a + 6.0, b - 9.0):
            p.box((x, x + 3.0), (y + 1.0, y + 2.0), (FRONT - 0.25, FRONT + 0.25), BRASS_D, skip="n")
        p.box((mid - 1.5, mid + 1.5), (y + 1.0, y + 2.0), (FRONT - 0.25, FRONT), CARD_LABEL, skip="n")
    p.box((a, b), CHEST_TOP, (1.0, FRONT), WOOD, skip="n", grain="x")


def _panelled(p, u, y, depth=FRONT, stile=3.0, rails=()):
    """A framed panel: stiles and rails at `depth`, the field between them a texel behind, darker.
    rails are the undersides of rails between the first and the last."""
    (a, b), (y0, y1) = u, y
    p.box((a + stile, b - stile), (y0 + stile, y1 - stile), (1.0, depth - 1.0), WOOD_D, skip="n", grain="y")
    for x in (a, b - stile):
        p.box((x, x + stile), (y0, y1), (1.0, depth), WOOD, skip="n", grain="y")
    for yy in (y0, y1 - stile) + tuple(rails):
        p.box((a + stile, b - stile), (yy, yy + stile), (1.0, depth), WOOD, skip="n", grain="x")


def _cupboard(p, u):
    """The foot of the middle bay: two panelled doors that meet on the axis, a knob on each meeting
    stile and a keyhole under the right one."""
    a, b = u
    mid = (a + b) / 2.0
    y0, y1 = PLINTH + 1.0, RAIL[0] - 1.0
    p.box((a, b), (PLINTH, y0), (1.0, FRONT), WOOD, skip="n", grain="x")
    p.box((a, b), (y1, RAIL[0]), (1.0, FRONT), WOOD, skip="n", grain="x")
    p.box((a, a + 1.0), (y0, y1), (1.0, FRONT), WOOD, skip="n", grain="y")
    p.box((b - 1.0, b), (y0, y1), (1.0, FRONT), WOOD, skip="n", grain="y")
    for x0, x1 in ((a + 1.0, mid), (mid, b - 1.0)):
        _panelled(p, (x0, x1), (y0, y1), depth=FRONT - 0.25, rails=(y0 + 15.0,))
    for x in (mid - 2.0, mid + 1.0):
        p.box((x, x + 1.0), (y0 + 19.0, y0 + 21.0), (FRONT - 0.25, FRONT + 0.5), BRASS_D, skip="n")
    p.box((mid + 1.0, mid + 2.0), (y0 + 13.0, y0 + 16.0), (FRONT - 0.25, FRONT), BRASS_D, skip="n", faces={"s": KEYHOLE})


# ---- the three tiers of a strip ---------------------------------------------------------------------
def _first(strip):
    """The first storey: plinth, shelves, the rail board, the cornice. Nothing is proud of the
    front below the cornice."""
    p = _Piece(strip, 0)
    u = (p.u0, p.u1)
    p.box(u, (0.0, 48.0), (0.0, 1.0), SHADOW, skip="nudew")
    p.box(u, (0.0, PLINTH), (1.0, FRONT), WOOD_D, skip="nd", grain="x")
    p.box(u, RAIL, (1.0, FRONT), WOOD, skip="n", grain="x")
    p.box(u, (CORNICE[0], p.y1), (0.0, FRONT + 1.0), WOOD_D, skip="n", grain="x")
    for a, b in p.cheeks():
        p.box((a, b), (PLINTH, RAIL[0]), (1.0, FRONT), WOOD, skip="n", grain="y")
    for a, b in p.piers():                      # a sunk panel in a fillet
        _panelled(p, (a, b), (PLINTH, RAIL[0]), stile=1.0)
    bay = p.bay()
    if strip == MIDDLE:
        _cupboard(p, bay)
        return p
    outer = strip in (0, len(STRIPS) - 1)
    a, b = bay
    if outer:
        _chest(p, bay)
        boards = LOW_BOARDS[2:]
        floors = (CHEST_TOP[1],) + tuple(y + 1.0 for y in boards)
    else:
        boards = LOW_BOARDS
        floors = (PLINTH,) + tuple(y + 1.0 for y in boards)
    for y in boards:
        p.box((a, b), (y, y + 1.0), (1.0, FRONT - 0.5), WOOD, skip="n", grain="x")
    tops = tuple(boards) + (RAIL[0],)
    for i, (y, top) in enumerate(zip(floors, tops)):
        if not outer and i == 0:
            _piles(p, bay, y, top, BINDINGS[strip])
        elif not outer and i == 2 and strip < MIDDLE:
            _boxes(p, (a, a + 15.0), y, top)
            _books(p, (a + 16.0, b), y, top, BINDINGS[strip])
        elif not outer and i == 2:
            _books(p, (a, b - 16.0), y, top, BINDINGS[strip])
            _boxes(p, (b - 15.0, b), y, top)
        else:
            _books(p, bay, y, top, BINDINGS[strip])
    return p


def _second(strip):
    """The second storey: the piers a texel proud with a capital, bare where the lamps hang."""
    p = _Piece(strip, 1)
    u = (p.u0, p.u1)
    p.box(u, (48.0, 96.0), (0.0, 1.0), SHADOW, skip="nudew")
    p.box(u, (p.y0, CORNICE[1]), (1.0, FRONT + 1.0), WOOD_D, skip="nd", grain="x")
    p.box(u, HEAD, (1.0, FRONT), WOOD, skip="nu", grain="x")
    foot = CORNICE[1]
    for a, b in p.cheeks():
        p.box((a, b), (foot, HEAD[0]), (1.0, FRONT), WOOD, skip="n", grain="y")
    for a, b in p.piers():                      # a shaft on a base, under a capital
        p.box((a, b), (foot, CAPITAL), (1.0, FRONT + 1.0), WOOD, skip="n", grain="y")
        p.box((a, b), (CAPITAL, HEAD[1]), (1.0, FRONT + 2.0), WOOD_D, skip="n", grain="x")
        p.box((a, b), (foot, foot + 2.0), (1.0, FRONT + 2.0), WOOD_D, skip="n", grain="x")
    bay = p.bay()
    a, b = bay
    if strip == MIDDLE:                         # the clock's field, a bead of lighter wood round it
        _panelled(p, bay, (CORNICE[1], HEAD[0]), stile=3.0)
        (fa, fb), (fy0, fy1) = FIELD_U, FIELD_Y
        for x in (fa - 1.0, fb):
            p.box((x, x + 1.0), (fy0 - 1.0, fy1 + 1.0), (1.0, FIELD_Z + 0.5), WOOD_L, skip="n", grain="y")
        for y in (fy0 - 1.0, fy1):
            p.box((fa, fb), (y, y + 1.0), (1.0, FIELD_Z + 0.5), WOOD_L, skip="n", grain="x")
        return p
    outer = strip in (0, len(STRIPS) - 1)
    boards = HIGH_BOARDS[1:] if not outer else HIGH_BOARDS
    for y in boards:
        p.box((a, b), (y, y + 1.0), (1.0, FRONT - 0.5), WOOD, skip="n", grain="x")
    floors = ((foot,) if outer else ()) + tuple(y + 1.0 for y in boards)
    tops = tuple(boards[(0 if outer else 1):]) + (HEAD[0],)
    if not outer:
        _pigeonholes(p, bay, foot, HIGH_BOARDS[1])
    for i, (y, top) in enumerate(zip(floors, tops)):
        if outer and i == 1:
            split = a + 13.0 if strip == 0 else b - 13.0
            if strip == 0:
                _boxes(p, (a, split - 1.0), y, top)
                _books(p, (split, b), y, top, BINDINGS[strip])
            else:
                _books(p, (a, split), y, top, BINDINGS[strip])
                _boxes(p, (split + 1.0, b), y, top)
        else:
            _books(p, bay, y, top, BINDINGS[strip], full=0.9 if i == len(floors) - 1 else 0.94)
    return p


def _third(strip):
    """The entablature: architrave, frieze, a cornice of two steps; a block over each pier, the
    bay's letter on an enamel plate over its middle."""
    p = _Piece(strip, 2)
    u = (p.u0, p.u1)
    p.box(u, ARCHITRAVE, (0.0, FRONT + 0.5), WOOD, skip="n", grain="x")
    p.box(u, FRIEZE, (0.0, FRONT), WOOD_D, skip="nud", grain="x")
    p.box(u, CROWN, (0.0, FRONT + 1.0), WOOD, skip="n", grain="x")
    p.box(u, (CROWN[1], HIGH), (0.0, FRONT + 2.0), WOOD_D, skip="nu", grain="x")
    for a, b in p.piers():
        p.box((a, b), FRIEZE, (FRONT, FRONT + 1.0), WOOD, skip="n", grain="y")
    a, b = p.bay()
    mid = (a + b) / 2.0
    plate = _plate("ABCDE"[strip])
    half = len(plate.rows[0]) / 2.0
    p.box((mid - half, mid + half), (FRIEZE[0] + 1.0, FRIEZE[0] + 8.0), (FRONT, FRONT + 0.5), K.flat("enamel", 3),
          skip="n", faces={"s": plate})
    return p


@functools.lru_cache(maxsize=None)
def _pieces():
    return {(s, t): make(s) for s in range(len(STRIPS)) for t, make in enumerate((_first, _second, _third))}


def models():
    return {p.m.name: p.m for p in _pieces().values()}


def place(canvas, origin=(0, 0, 0)):
    """Stand the wall in the room; returns the number of display entities (15)."""
    n = 0
    for p in _pieces().values():
        pos = (EAST - p.mid * PX, FEET + (p.y0 + p.y1) / 2.0 * PX, SOUTH)
        n += K.put(canvas, p.m, pos, mount="wall", facing="north", origin=origin)
    return n


if __name__ == "__main__":
    pieces = _pieces()
    print(f"{len(pieces)} display entities; elements: "
          + " ".join(f"{p.m.name[len(PREFIX):]}={len(p.m.parts)}" for p in pieces.values()))
