"""Materials, the traces: water marks, rust, soot, damp, oil, coal dust, cracks, chalk marks, wear.

The near layer of plan/fine.md asks for traces, and a trace has to lie where its cause is: under a
sill, below a bracket, over a flame. The random variants of a material cannot do that, and forty
people who each draw their own water mark draw forty. So the shapes are drawn here, once, and
there are three ways to put them on (plan/parts/materials.md, section 2 F):

    from scenes.obs.materials import traces as T

  A  on the face of a block (a wall, a floor, a roof): a decal, one thin plate shown by a display
     entity, a dark or a light ink with some of the face showing through.

         n += T.decal(canvas, (x, y, z), "south", "water", origin=origin)

     (x, y, z) is the point of the face the trace hangs on, "south" the way the face looks (north,
     south, east, west, up, down). Water and rust hang down from the point, soot and damp rise
     from it, the rest lie about it. look=0..3 picks one of the four drawings of a kind; left out,
     the place picks. On a floor or a ceiling turn= turns the plate about the upright. Returns 1.
     The models are models(): a test scene that places decals adds them to its build_models(),

         models.update(T.models())

  B  on a face of one's own model (a machine, a pipe, a piece of furniture): the material is
     wrapped, and the trace is worked into what it paints. No entity, no command.

         m.box(a, b, T.stain(IRON, "rust"))                  every face of the box
         m.box(a, b, IRON, faces={"s": T.stain(IRON, "soot", part=(0, 0, 1, 0.5))})
         m.tube("y", c, 0, 12, 3, T.worn(BRASS))             edges rubbed bright
         T.worn(WOOD, "middle")                              a seat, a tread, a grip

     part=(x0, y0, x1, y1) keeps the trace to a part of the face, in shares of its width and its
     height from the upper left corner. A trace moves a pixel along its own ramp, one step for the
     light part of the shape and two for its heart (wear: one step up), so the picture stays in
     the palette; rust takes the brown of old copper that is as light as the pixel was, coal dust
     and chalk are specks of iron black and of cream.

  C  for the wide views: stained siblings of the large materials, which the assembly puts in by
     rule (under sills, at the foot of walls, over flue mouths). Their pictures are made with
     apply() from the materials' own; that part is not in this file yet.

KINDS: water, rust, soot, damp, oil, coal, crack, chalk, worn. The rules that come with them are in
the plan: light (a step or two), with a cause in sight, and nobody draws a water mark of his own.
"""
import copy
import functools
import math

import numpy as np

from artkit import models as M
from artkit import pixelart as PX

from ..common import palette as P

PREFIX = "mat_trace_"
KINDS = ("water", "rust", "soot", "damp", "oil", "coal", "crack", "chalk", "worn")
LOOKS = 4                               # drawings of each kind
SIZE = {"water": (16, 24), "rust": (8, 20), "soot": (16, 24), "damp": (16, 10), "oil": (12, 12),
        "coal": (16, 16), "crack": (14, 14), "chalk": (8, 8), "worn": (16, 16)}     # a decal, pixels across and up
HOLD = {"water": "top", "rust": "top", "soot": "bottom", "damp": "bottom"}         # the rest are held by the middle
VIEW = M.NEAR                           # a trace is for the near view: drawn within 32 blocks
OFF = 0.02                              # blocks a decal stands off its face, inside the air cell
FACING = {"south": 0.0, "west": 90.0, "north": 180.0, "east": -90.0}
_OUT = {"south": (0, 0, 1), "north": (0, 0, -1), "east": (1, 0, 0), "west": (-1, 0, 0), "up": (0, 1, 0),
        "down": (0, -1, 0)}

# A decal's ink: (ramp, its step, how much of the face it hides out of 255) for the light part of
# the shape and for its heart. Dark inks hide a fifth to a half, so a wall shows a step or two
# darker whatever it is made of; coal and chalk are specks and strokes and hide nearly all.
_INK = {
    "water": (("iron", 1, 46), ("iron", 1, 82)),
    "damp": (("iron", 1, 42), ("iron", 1, 76)),
    "soot": (("iron", 0, 64), ("iron", 0, 120)),
    "rust": (("old_copper", 1, 70), ("old_copper", 0, 120)),
    "oil": (("iron", 0, 90), ("iron", 0, 150)),
    "coal": (("iron", 1, 200), ("iron", 0, 255)),
    "crack": (("iron", 0, 70), ("iron", 0, 150)),
    "chalk": (("cream", 2, 150), ("cream", 3, 225)),
    "worn": (("ashlar", 5, 26), ("ashlar", 5, 44)),
}
# Worked into a picture: steps along the pixel's own ramp for the light part and for the heart ...
_STEPS = {"water": (-1, -2), "damp": (-1, -2), "soot": (-1, -2), "oil": (-1, -2), "crack": (-1, -2), "worn": (1, 1)}
# ... or another colour altogether
_SPECK = {"coal": (("iron", 1), ("iron", 0)), "chalk": (("cream", 1), ("cream", 2))}
_RUST = "old_copper"


def _h(*key):
    """A number from 0 to 1 that hangs on the key and on nothing else."""
    x = 0x9E3779B1
    for k in key:
        x = ((x ^ (int(k) & 0xFFFFFFFF)) * 0x85EBCA6B) & 0xFFFFFFFF
        x ^= x >> 13
        x = (x * 0xC2B2AE35) & 0xFFFFFFFF
        x ^= x >> 16
    return x / 4294967296.0


def _rgb(ramp, step):
    return tuple(int(v) for v in PX.hx(P.RAMPS[ramp][step]))


# ---- the shapes: 0 nothing, 1 the light part, 2 the heart ------------------------------------------
def _water(w, h, look, seed):
    """Streaks that hang from the upper edge, under what sheds the water."""
    lv = np.zeros((h, w), dtype=np.int8)
    for x in range(w):                                  # the wet line under the sill
        if _h(seed, look, x, 9) < 0.6:
            lv[0, x] = 1
    taken = []
    for k in range(2 + look % 3):
        x = 1 + int(_h(seed, look, k, 1) * max(w - 2, 1))
        if any(abs(x - t) < 2 for t in taken):
            x = (x + 3) % max(w - 2, 1) + 1
            if any(abs(x - t) < 2 for t in taken):
                continue
        x = min(w - 1, x)
        taken.append(x)
        length = min(h, max(3, int(h * (0.45 + 0.55 * _h(seed, look, k, 2)))))
        head = max(2, length // 4)
        for r in range(length):
            if r >= length - 2 and (r + x) % 2:         # the end thins out
                continue
            lv[r, x] = 2 if r < head else 1
        if _h(seed, look, k, 3) > 0.55 and x + 1 < w - 1 and all(abs(x + 1 - t) >= 2 for t in taken if t != x):
            for r in range(int(length * 0.6)):
                lv[r, x + 1] = max(lv[r, x + 1], 1)
    return lv


def _rust(w, h, look, seed):
    """One run of rust water from a point of the upper edge, where the iron sits on the stone."""
    lv = np.zeros((h, w), dtype=np.int8)
    cx = min(max(w - 2, 0), max(1 if w > 2 else 0, w // 2 + (look % 3) - 1))
    for x in range(max(0, cx - 1), min(w, cx + 3)):
        lv[0, x] = 1
        if h > 1 and cx <= x <= cx + 1:
            lv[1, x] = 1

    def run(x, length, strong):
        for r in range(min(h, length)):
            if r and r % 5 == 0:
                x = min(w - 1, max(0, x + int(_h(seed, look, x, r, 4) * 3) - 1))
            if r >= length - 2 and (r + x) % 2:
                continue
            lv[r, x] = 2 if r < strong else max(lv[r, x], 1)

    length = max(4, int(h * (0.6 + 0.4 * _h(seed, look, 1))))
    run(cx, length, max(2, length // 3))
    if look >= 2:
        side = cx + 2 if _h(seed, look, 2) > 0.5 else cx - 2
        if 0 <= side < w:
            run(side, max(3, length // 2), 1)
    return lv


def _soot(w, h, look, seed):
    """Soot over a flame or a flue: thick at the foot, wider and thinner as it rises."""
    lv = np.zeros((h, w), dtype=np.int8)
    lean = (look % 3) - 1
    for r in range(h):
        t = (h - 1 - r) / float(max(h - 1, 1))          # 0 at the foot, 1 at the top
        half = max(0.6, (0.16 + 0.34 * t) * w)
        cx = (w - 1) / 2.0 + lean * t * w * 0.12
        dense = (1.0 - t) ** 1.2
        for x in range(w):
            f = 1.0 - ((x - cx) / half) ** 2
            if f <= 0.0:
                continue
            p = dense * (0.35 + 0.65 * f)
            if p > 0.62:
                lv[r, x] = 2
            elif p > 0.08 + 0.9 * _h(seed, look, x, r):
                lv[r, x] = 1
    return lv


def _damp(w, h, look, seed):
    """Damp that has risen from the ground: a band along the lower edge with a ragged line. Its two
    ends stand at one height in every drawing, so decals side by side join."""
    lv = np.zeros((h, w), dtype=np.int8)
    p1, p2 = _h(seed, look, 1) * w, _h(seed, look, 2) * w
    for x in range(w):
        window = math.sin(math.pi * (x + 0.5) / w)
        rise = 0.45 + window * (0.22 * math.sin(2.0 * math.pi * (x + p1) / w) + 0.12 * math.sin(4.0 * math.pi * (x + p2) / w))
        top = h - int(round(h * rise)) + (1 if _h(seed, look, x // 2, 3) > 0.7 else 0)
        top = min(max(h - 2, 0), max(1 if h > 2 else 0, top))
        lv[top:, x] = 1
        if _h(seed, look, x, 4) < 0.5:                  # the line is ragged
            lv[top, x] = 0
        for r in range(max(top + 1, h - 2), h):         # the wet line along the ground
            if _h(seed, look, x, r, 5) < 0.8:
                lv[r, x] = 2
    return lv


def _blot(w, h, look, seed, rx, ry, heart):
    lv = np.zeros((h, w), dtype=np.int8)
    cx = (w - 1) / 2.0 + (_h(seed, look, 1) - 0.5) * w * 0.2
    cy = (h - 1) / 2.0 + (_h(seed, look, 2) - 0.5) * h * 0.2
    a, b = _h(seed, look, 3) * 6.28, _h(seed, look, 4) * 6.28
    for y in range(h):
        for x in range(w):
            dx, dy = (x - cx) / rx, (y - cy) / ry
            ang = math.atan2(dy, dx)
            d = math.hypot(dx, dy) / (1.0 + 0.25 * math.sin(3.0 * ang + a) + 0.15 * math.sin(5.0 * ang + b))
            if d < heart:
                lv[y, x] = 2
            elif d < 1.0:
                lv[y, x] = 1
    return lv, cx, cy


def _oil(w, h, look, seed):
    """A blot of oil with a few drops beside it."""
    rx = max(1.0, min(w * (0.22 + 0.08 * _h(seed, look, 5)), 5.0))
    ry = max(1.0, min(h * (0.18 + 0.08 * _h(seed, look, 6)), 4.0))
    lv, cx, cy = _blot(w, h, look, seed, rx, ry, 0.6)
    for k in range(2 + look % 3):
        ang = _h(seed, look, k, 7) * 6.28
        far = 1.5 + 0.9 * _h(seed, look, k, 8)
        x, y = int(round(cx + math.cos(ang) * rx * far)), int(round(cy + math.sin(ang) * ry * far))
        if 0 <= x < w and 0 <= y < h and not lv[y, x]:
            lv[y, x] = 2 if k == 0 else 1
    return lv


def _coal(w, h, look, seed):
    """Coal dust: specks, thick where the coal was shovelled and thin away from it."""
    lv = np.zeros((h, w), dtype=np.int8)
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    if look % 4 == 1:
        cx, cy = w * 0.3, h * 0.65
    elif look % 4 == 2:
        cx, cy = w * 0.7, h * 0.35
    elif look % 4 == 3:
        cy = h * 0.8
    reach = max(1.5, 0.38 * w)
    for y in range(h):
        for x in range(w):
            p = 0.6 * math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / reach ** 2)
            if _h(seed, look, x, y, 1) < p:
                lv[y, x] = 2 if _h(seed, look, x, y, 2) < 0.6 else 1
    return lv


def _crack(w, h, look, seed):
    """A hair crack that wanders from an edge, with one short branch."""
    across = look % 4 == 2 and w == h
    lv = np.zeros((h, w), dtype=np.int8)
    drift = 1 if look % 2 == 0 else -1
    x = min(w - 1, int(w * (0.15 if drift > 0 else 0.8)))
    length = max(2, min(h, int(h * (0.55 if look % 4 == 3 else 0.75 + 0.25 * _h(seed, look, 1)))))
    fork = int(length * 0.4)
    for r in range(length):
        lv[r, x] = 2
        if r == fork:
            bx = x
            for k in range(1, 3 + int(_h(seed, look, 3) * 3)):
                bx = min(w - 1, max(0, bx - drift))
                if r + k < h and not lv[r + k, bx]:
                    lv[r + k, bx] = 1
        roll = _h(seed, look, r, 2)
        x = min(w - 1, max(0, x + (drift if roll < 0.45 else -drift if roll > 0.9 else 0)))
    return lv.T.copy() if across else lv


_MARKS = (
    ("........", ".......#", "......#.", ".....#..", "#...#...", ".#.#....", "..#.....", "........"),     # a tick
    ("........", ".#....#.", "..#..#..", "...##...", "...##...", "..#..#..", ".#....#.", "........"),     # a cross
    ("..####..", ".#....#.", "#......#", "#......#", "#......#", "#.......", ".#....#.", "..###..."),     # a ring
    ("........", ".#.#.#..", ".#.#.#..", ".#.#.#..", ".#.#.#..", ".#.#.#..", ".#.#.#..", "........"),     # a tally of three
)


def _chalk(w, h, look, seed):
    """A fitter's chalk mark, eight pixels square: a tick, a cross, a ring, a tally. No letters:
    writing takes the station's typeface (props/_kit.letters)."""
    lv = np.zeros((h, w), dtype=np.int8)
    rows = _MARKS[look % len(_MARKS)]
    x0 = int((w - 8) * _h(seed, look, 1)) if w > 8 else 0
    y0 = int((h - 8) * _h(seed, look, 2)) if h > 8 else 0
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == "#" and y0 + j < h and x0 + i < w:
                lv[y0 + j, x0 + i] = 1 if _h(seed, look, i, j, 3) < 0.15 else 2
    return lv


def _worn(w, h, look, seed):
    """Where hands and feet have been: a soft patch about the middle."""
    lv, _, _ = _blot(w, h, look, seed, max(1.0, min(w * 0.42, 7.0)), max(1.0, min(h * 0.36, 6.0)), 0.45)
    for y in range(h):
        for x in range(w):
            if lv[y, x] == 1 and _h(seed, look, x, y, 9) < 0.35:
                lv[y, x] = 0
    return lv


def _edges(w, h, look, seed):
    """Wear along the rim of a face: most of each edge, the corners always."""
    lv = np.zeros((h, w), dtype=np.int8)
    for x in range(w):
        for y in (0, h - 1):
            if _h(seed, look, x // 3, y, 1) < 0.75:
                lv[y, x] = 1
    for y in range(h):
        for x in (0, w - 1):
            if _h(seed, look, x, y // 3, 2) < 0.75:
                lv[y, x] = 1
    for y in (0, h - 1):
        for x in (0, w - 1):
            lv[y, x] = 2
    return lv


_SHAPES = {"water": _water, "rust": _rust, "soot": _soot, "damp": _damp, "oil": _oil, "coal": _coal,
           "crack": _crack, "chalk": _chalk, "worn": _worn, "edges": _edges}


def shape(kind, w, h, look=0, seed=0):
    """The drawing `look` of a kind on a field of w by h pixels: an array [row][column] of 0
    (nothing), 1 (the light part) and 2 (the heart). The same for the same arguments."""
    if kind not in _SHAPES:
        raise KeyError(f"no trace is called {kind!r}; there are {', '.join(KINDS)}")
    if w < 1 or h < 1:
        return np.zeros((max(h, 0), max(w, 0)), dtype=np.int8)
    return _SHAPES[kind](int(w), int(h), int(look), int(seed))


# ---- B: worked into a picture ----------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def _places():
    """{colour: (ramp, step)} for every colour of the palette; one that two ramps share goes to the first."""
    out = {}
    for name in P.RAMPS:
        for i in range(len(P.RAMPS[name])):
            out.setdefault(_rgb(name, i), (name, i))
    return out


def _luma(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def _moved(colour, kind, level):
    """What a pixel of `colour` becomes under the light part (1) or the heart (2) of a trace; None
    for a colour of no ramp (a picture of the game's own), which is left as it is."""
    if kind == _RUST or kind == "rust":
        want = _luma(colour) * (0.92 if level == 1 else 0.8)
        return min((_rgb(_RUST, i) for i in range(len(P.RAMPS[_RUST]))), key=lambda c: abs(_luma(c) - want))
    if kind in _SPECK:
        return _rgb(*_SPECK[kind][level - 1])
    place = _places().get(colour)
    if place is None:
        return None
    name, i = place
    return _rgb(name, min(len(P.RAMPS[name]) - 1, max(0, i + _STEPS[kind][level - 1])))


def apply(pixels, kind, levels):
    """A picture (h, w, 4) with a trace worked into it: where `levels` (shape()) is 1 or 2, a pixel
    goes a step or two along its own ramp (see the head of this file). Clear pixels stay clear.
    Returns a new array; every colour it adds is of the palette."""
    kind = "worn" if kind == "edges" else kind
    px = np.array(pixels, dtype=np.uint8, copy=True)
    was = px.copy()
    for level in (1, 2):
        mask = (levels == level) & (was[..., 3] > 0)
        if not mask.any():
            continue
        for colour in {tuple(int(v) for v in c) for c in was[mask][:, :3]}:
            new = _moved(colour, kind, level)
            if new is None or new == colour:
                continue
            hit = mask & (was[..., 0] == colour[0]) & (was[..., 1] == colour[1]) & (was[..., 2] == colour[2])
            px[hit, :3] = new
    return px


def _work(px, kind, look, part, seed):
    h, w = px.shape[:2]
    x0, y0, x1, y1 = 0, 0, w, h
    if part is not None:
        x0, y0 = int(round(part[0] * w)), int(round(part[1] * h))
        x1, y1 = int(round(part[2] * w)), int(round(part[3] * h))
        x0, x1 = max(0, min(x0, x1)), min(w, max(x0, x1))
        y0, y1 = max(0, min(y0, y1)), min(h, max(y0, y1))
    if x1 <= x0 or y1 <= y0:
        return px
    which = int(_h(seed, w, h, 11) * LOOKS) if look is None else int(look)
    levels = np.zeros((h, w), dtype=np.int8)
    levels[y0:y1, x0:x1] = shape(kind, x1 - x0, y1 - y0, which, seed)
    return apply(px, kind, levels)


def _label(kind, look, part):
    words = [kind]
    if look is not None:
        words.append(str(int(look)))
    if part is not None:
        words.append("p" + "_".join(str(int(round(v * 100))) for v in part))
    return "~" + "".join(words)


class _Traced:
    """A material that is no pixelart.Mat (a Sprite, a Picture, a kit's own) with a trace on it."""

    def __init__(self, mat, kind, look, part):
        self.mat, self.kind, self.look, self.part = mat, kind, look, part
        self.name = mat.name + _label(kind, look, part)

    def variant(self, shift=0, bevel=None):
        inner = self.mat.variant(shift, bevel) if hasattr(self.mat, "variant") else self.mat
        return self if inner is self.mat else _Traced(inner, self.kind, self.look, self.part)

    def paint(self, w, h, grain="u", seed=0):
        return _work(np.asarray(self.mat.paint(w, h, grain, seed)), self.kind, self.look, self.part, seed)


def _traced(mat, kind, look, part):
    if part is not None and len(part) != 4:
        raise ValueError(f"part={part!r}: (x0, y0, x1, y1) in shares of the face, from its upper left corner")
    if isinstance(mat, PX.Frames):                      # a moving picture: every frame takes the trace
        return PX.Frames(mat.name + _label(kind, look, part), [_traced(m, kind, look, part) for m in mat.mats],
                         mat.frametime, mat.interpolate)
    if not isinstance(mat, PX.Mat):
        return _Traced(mat, kind, look, part)
    base = type(mat)        # a Mat stays a Mat (artkit.models shades a round shape's sides by that), of a class of its own

    def paint(self, w, h, grain="u", seed=0):
        return _work(np.asarray(base.paint(self, w, h, grain, seed)), kind, look, part, seed)

    m = copy.copy(mat)
    m.__class__ = type("Traced" + base.__name__, (base,), {"paint": paint})
    m.name = mat.name + _label(kind, look, part)
    m._variants = {}
    return m


def stain(mat, kind, look=None, part=None):
    """`mat` with a trace of `kind` worked into every face it paints (see the head of this file).
    look=0..3 picks the drawing; left out, each face gets its own. part=(x0, y0, x1, y1) keeps the
    trace to that part of a face."""
    if kind not in KINDS:
        raise KeyError(f"no trace is called {kind!r}; there are {', '.join(KINDS)}")
    return _traced(mat, kind, look, part)


def worn(mat, where="edges", look=None, part=None):
    """`mat` rubbed bright: a step up its ramp along the edges of a face ("edges": casings, lids,
    handwheels) or about its middle ("middle": seats, treads, grips)."""
    if where not in ("edges", "middle"):
        raise ValueError(f"where={where!r}: edges or middle")
    return _traced(mat, "edges" if where == "edges" else "worn", look, part)


# ---- A: decals --------------------------------------------------------------------------------------
def picture(kind, look):
    """The decal of a kind as pixels (h, w, 4): the ink where the shape is, clear elsewhere."""
    w, h = SIZE[kind]
    levels = shape(kind, w, h, look, KINDS.index(kind) + 1)
    px = np.zeros((h, w, 4), dtype=np.uint8)
    for level, (ramp, step, hides) in zip((1, 2), _INK[kind]):
        px[levels == level, :3] = _rgb(ramp, step)
        px[levels == level, 3] = hides
    return px


@functools.lru_cache(maxsize=None)
def _models():
    out = {}
    back = P.mat("iron")                                # the plate's other faces are left out
    for kind in KINDS:
        w, h = SIZE[kind]
        y0 = {"top": -float(h), "bottom": 0.0}.get(HOLD.get(kind), -h / 2.0)
        for look in range(LOOKS):
            name = f"{PREFIX}{kind}_{look}"
            m = M.Model(name)
            face = PX.Picture(name + "_ink", picture(kind, look))
            m.box((-w / 2.0, y0, 0.0), (w / 2.0, y0 + h, 0.0), back, faces={"s": face}, skip="nudew", shade=False)
            out[name] = m
    return out


def models():
    """The decals, {name: Model}: mat_trace_<kind>_<look>."""
    return dict(_models())


def decal(canvas, pos, facing, kind, look=None, turn=0.0, origin=(0, 0, 0), **opts):
    """Put a trace on the face of a block (see the head of this file). pos is the point of the face
    the trace hangs on, in scene coordinates; facing the way the face looks. opts go to
    artkit.models.display (view=, brightness=). Returns 1, the entity it adds."""
    if kind not in KINDS:
        raise KeyError(f"no trace is called {kind!r}; there are {', '.join(KINDS)}")
    if facing not in _OUT:
        raise KeyError(f"facing={facing!r}: one of {', '.join(_OUT)}")
    x, y, z = (float(pos[i]) + origin[i] for i in range(3))
    if look is None:
        look = int(_h(round(x * 16), round(y * 16), round(z * 16), KINDS.index(kind)) * LOOKS)
    model = _models()[f"{PREFIX}{kind}_{int(look) % LOOKS}"]
    out = _OUT[facing]
    opts.setdefault("view", VIEW)
    if facing in FACING:
        nbt = M.display(model, yaw=FACING[facing], **opts)
    else:
        nbt = M.display(model, yaw=turn, turns=(("x", -90.0 if facing == "up" else 90.0),), **opts)
    canvas.add_entity(x + out[0] * OFF, y + out[1] * OFF, z + out[2] * OFF, nbt)
    return 1
