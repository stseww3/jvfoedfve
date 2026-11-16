"""What the boilers and the switchboard of the power house share (machines/switchboard-boiler):
drawing a model in blocks, lighting a piece that looks at a wall's side of the sky, painting a
face pixel by pixel, and placing a piece.

The name starts with an underscore: the category does not take it for a package.
"""
import math

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import palette as P

VIEW = 1.5          # view range of a piece: 96 blocks at the client's normal setting; the room is 19 across
TEXEL = 1.0 / 16.0

# ---- how a piece is lit --------------------------------------------------------------------------------
# The game lights a face of an item model by the one of the model's six axes its normal lies nearest
# to, that axis turned with the display entity, under two fixed lamps high in the north-east and the
# south-west: a face filed under "up" is full bright, north and south 0.74, east and west 0.5, down
# 0.4 (see machines/mast.py, the lamp). A boiler front looks west and the board looks east: drawn
# upright, all that counts on them would be shown at half its tone, and iron at half its tone under a
# lamp of level 10 is black.
#
# So such a piece is drawn in a frame that leans towards the side it looks at: the entity is turned
# about the north-south axis by LEAN, the model is drawn turned back and stands upright, and its
# front is filed under the model's "up", which now points LEAN off the zenith: full bright, as its
# tops are (filed under the axis that leans the other way). Faces that look north and south keep
# 0.74, undersides and backs get 0.4. It is the light of a lamp that hangs before the piece, which
# is where the fire and the room's lamps are. LEAN is a degree past 45 so that no face lies on the
# line between two axes.
LEAN = 46.0
LEAN_WEST = (("z", LEAN),)      # for a piece that looks west
LEAN_EAST = (("z", -LEAN),)     # for a piece that looks east


class Draw:
    """A model drawn round the point `at`, where its entity stands, and shown at `scale`.

    artkit's unit is 1/16 block of a model shown at scale 1. A model shown at scale s is drawn s
    times smaller and gets s texels to the unit (px = scale): 16 texels to the block whatever the
    scale. A model may span 48 units: three blocks at scale 1, six at scale 2.

    step   what the numbers given to this object count, in blocks: 1.0 for blocks, TEXEL for texels.
           Everything is given in it: `at`, corners, centres, radii, thicknesses
    frame  the turns the entity is given (LEAN_WEST, LEAN_EAST); everything is drawn turned back
    """

    def __init__(self, name, at=(0.0, 0.0, 0.0), scale=2.0, frame=(), step=1.0):
        self.scale = float(scale)
        self.step = float(step)
        self.k = self.step * 16.0 / self.scale          # one step, in artkit's units
        self.at = tuple(float(v) for v in at)
        self.m = M.Model(name, px=self.scale)
        self.frame = tuple(frame)
        if self.frame:
            self._upright = self.m.turned(*((axis, -deg) for axis, deg in reversed(self.frame)))
            self._upright.__enter__()

    def p(self, v):
        return tuple((v[i] - self.at[i]) * self.k for i in range(3))

    def _across(self, axis, c):
        k = M.AXES.index(axis)
        o1, o2 = [i for i in range(3) if i != k]
        return k, ((c[0] - self.at[o1]) * self.k, (c[1] - self.at[o2]) * self.k)

    def box(self, a, b, mat, rot=None, **kw):
        if rot is not None:
            rot = (rot[0], rot[1], self.p(rot[2]))
        self.m.box(self.p(a), self.p(b), mat, rot=rot, **kw)

    def tube(self, axis, c, a0, a1, radius, mat, **kw):
        """c: the two other coordinates of the centre line, in the order of the axes."""
        k, c = self._across(axis, c)
        self.m.tube(axis, c, (a0 - self.at[k]) * self.k, (a1 - self.at[k]) * self.k, radius * self.k, mat, **kw)

    def taper(self, axis, c, a0, a1, r0, r1, mat, **kw):
        k, c = self._across(axis, c)
        self.m.taper(axis, c, (a0 - self.at[k]) * self.k, (a1 - self.at[k]) * self.k, r0 * self.k, r1 * self.k,
                     mat, **kw)

    def ring(self, axis, centre, radius, thick, width, mat, **kw):
        self.m.ring(axis, self.p(centre), radius * self.k, thick * self.k, width * self.k, mat, **kw)

    def ball(self, centre, radius, mat, **kw):
        self.m.ball(self.p(centre), radius * self.k, mat, **kw)

    def rod(self, a, b, radius, mat, **kw):
        self.m.rod(self.p(a), self.p(b), radius * self.k, mat, **kw)

    def beam(self, a, b, width, height, mat, **kw):
        self.m.beam(self.p(a), self.p(b), width * self.k, height * self.k, mat, **kw)

    def hose(self, points, radius, mat, **kw):
        self.m.hose([self.p(v) for v in points], radius * self.k, mat, **kw)

    def turned(self, *turns, about=(0.0, 0.0, 0.0)):
        """`with d.turned(("z", 30), about=p):` turns what is drawn inside about the point p."""
        return self.m.turned(*turns, about=self.p(about))

    def plate(self, face, at, w, h, sprite, lift=0.0, **kw):
        """A picture standing by itself: a box as thin as paper that shows `sprite` on one face only.

        face   the letter of the face that carries it: "w" or "e" (the picture's plane is x = at[0]),
               "u" or "d" (y = at[1]), "n" or "s" (z = at[2])
        at     the middle of the picture; w, h its size in texels
        lift   how far the picture stands off that plane towards where it looks, in texels: a
               quarter keeps it clear of the face it lies on
        Pictures of one name share their place on the model's sheet.
        """
        k = {"w": 0, "e": 0, "u": 1, "d": 1, "n": 2, "s": 2}[face]
        out = 1.0 if face in "eus" else -1.0
        ua, va = M.FACE_AXES[face][1], M.FACE_AXES[face][2]
        t = TEXEL / self.step                           # a texel, in steps
        lo, hi = list(at), list(at)
        lo[ua], hi[ua] = at[ua] - w * t / 2.0, at[ua] + w * t / 2.0
        lo[va], hi[va] = at[va] - h * t / 2.0, at[va] + h * t / 2.0
        front = at[k] + out * lift * t
        lo[k], hi[k] = sorted((front, front - out * t / 4.0))
        kw.setdefault("seed", 0)
        self.box(lo, hi, sprite, skip="".join(f for f in "nsewud" if f != face), **kw)


def place(canvas, drawn, pos, origin, yaw=0.0, turns=(), brightness=None):
    """One drawn model with its point `at` on pos; returns 1, the entity it takes.
    turns: (axis, degrees) about the scene's axes, for a piece that rests turned (a pointer)."""
    x, y, z = (pos[i] + origin[i] for i in range(3))
    canvas.add_entity(x, y, z, M.display(drawn.m, yaw=yaw, scale=drawn.scale, turns=tuple(drawn.frame) + tuple(turns),
                                         brightness=brightness, view=VIEW))
    return 1


def light(canvas, lights, origin, why, rank=2):
    """Hand the sources a piece stands in, [((x, y, z), level)], to the sky line, which places them
    with the rest when everything stands (sky/_lightkit.suggest). While that tool is not in the tree
    the blocks are put down here, never over another."""
    try:
        from ..sky import _lightkit
        suggest = getattr(_lightkit, "suggest", None)
    except ImportError:
        suggest = None
    for (x, y, z), level in lights:
        cell = (int((origin[0] + x) // 1), int((origin[1] + y) // 1), int((origin[2] + z) // 1))
        if suggest is not None:
            suggest(canvas, cell, level, why, rank=rank)
        else:
            from ..common import blocks as B
            canvas.set(cell[0], cell[1], cell[2], f"{B.LIGHT}[level={int(level)}]", keep=True)


# ---- painting a face pixel by pixel ----------------------------------------------------------------------
# One letter for every tone of the ramps the set uses; "." is see-through.
LETTERS = {"iron": "0123456", "brass": "abcdef", "slate": "ABCDEFG", "cream": "pqrs", "porcelain": "PQRST",
           "glow": "uvwxy", "phosphor": "hijkl", "signal": "JKLM", "dark_wood": "VWXYZ"}
TONES = {c: P.RAMPS[ramp][i] for ramp, letters in LETTERS.items() for i, c in enumerate(letters)}


def tone(ramp, step):
    """The letter of a ramp's step, kept inside the ramp."""
    letters = LETTERS[ramp]
    return letters[int(min(len(letters) - 1, max(0, step)))]


def flat(ramp, step):
    """One flat tone of a ramp, as a material."""
    return P.mat(ramp, kind="flat", base=step, bevel=0)


def dice(i, j, seed):
    """A number from 0 to 1 for the texel (i, j): the same every time."""
    h = (i * 374761393 + j * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(1 << 24)


class Pix:
    """A small picture drawn in the letters of TONES; x runs right, y down, (0, 0) is the top left
    texel. Circles are measured from texel middles: disc(24, 24, 24, ...) fills the inscribed circle
    of a 48 x 48 picture."""

    def __init__(self, w, h, fill="."):
        self.w, self.h = int(w), int(h)
        self.g = [[fill] * self.w for _ in range(self.h)]

    def get(self, x, y):
        return self.g[y][x] if 0 <= x < self.w and 0 <= y < self.h else "."

    def set(self, x, y, ch, only=None):
        if 0 <= x < self.w and 0 <= y < self.h and (only is None or self.g[y][x] in only):
            self.g[y][x] = ch

    def rect(self, x0, y0, x1, y1, ch, only=None):
        """Both corners are filled."""
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, ch, only)

    def frame(self, x0, y0, x1, y1, light, dark=None, only=None):
        """The outline of a rectangle: its top and left in `light`, its bottom and right in `dark`."""
        dark = light if dark is None else dark
        for x in range(x0, x1 + 1):
            self.set(x, y1, dark, only)
        for y in range(y0, y1 + 1):
            self.set(x1, y, dark, only)
        for x in range(x0, x1):
            self.set(x, y0, light, only)
        for y in range(y0, y1):
            self.set(x0, y, light, only)

    def disc(self, cx, cy, r, ch, only=None, inner=None):
        """Texels whose middle lies within r of (cx, cy) and, with `inner`, further than that."""
        for y in range(self.h):
            for x in range(self.w):
                d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
                if d <= r and (inner is None or d > inner):
                    self.set(x, y, ch, only)

    def band(self, cx, cy, r, inner, top, side, bottom, only=None, lean=0.5):
        """A ring lit from above: the texels between `inner` and r, in three tones by where on the
        ring they lie."""
        for y in range(self.h):
            for x in range(self.w):
                dx, dy = x + 0.5 - cx, y + 0.5 - cy
                d = math.hypot(dx, dy)
                if inner < d <= r:
                    up = -dy / d
                    self.set(x, y, top if up > lean else bottom if up < -lean else side, only)

    def studs(self, cx, cy, r, n, ch, shade=None, start=0.0, only=None):
        """n texels on the circle of radius r, the first `start` degrees from the top, clockwise;
        the texel under each in `shade`."""
        for k in range(n):
            a = math.radians(start + 360.0 * k / n)
            x, y = int(math.floor(cx + r * math.sin(a))), int(math.floor(cy - r * math.cos(a)))
            if shade is not None:
                self.set(x, y + 1, shade, only)
        for k in range(n):
            a = math.radians(start + 360.0 * k / n)
            self.set(int(math.floor(cx + r * math.sin(a))), int(math.floor(cy - r * math.cos(a))), ch, only)

    def line(self, x0, y0, x1, y1, ch, only=None):
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        for k in range(n + 1):
            self.set(int(round(x0 + (x1 - x0) * k / n)), int(round(y0 + (y1 - y0) * k / n)), ch, only)

    def streaks(self, on, light, dark, seed, share=0.10, run=5):
        """Short brushed runs along x, one step up or down, on the texels that are `on`."""
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] != on:
                    continue
                r = dice(y, (x + (y * 3) % run) // run, seed)
                if r > 1.0 - share / 2.0:
                    self.g[y][x] = light
                elif r < share / 2.0:
                    self.g[y][x] = dark

    def specks(self, on, light, dark, seed, share=0.10):
        """Single texels one step up or down, on the texels that are `on`."""
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] != on:
                    continue
                r = dice(x, y, seed)
                if r > 1.0 - share / 2.0:
                    self.g[y][x] = light
                elif r < share / 2.0:
                    self.g[y][x] = dark

    def swap(self, old, new, where=None):
        """Every texel that is `old` becomes `new`; where(x, y) picks among them."""
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] == old and (where is None or where(x, y)):
                    self.g[y][x] = new

    def paste(self, other, x0, y0):
        for y in range(other.h):
            for x in range(other.w):
                if other.g[y][x] != ".":
                    self.set(x0 + x, y0 + y, other.g[y][x])

    def text(self, x0, y0, rows, key=None):
        """Rows of a small drawing laid on the picture: its letters are tones, or stand for the
        tones `key` gives; spaces and dots leave what is there."""
        for j, row in enumerate(rows):
            for i, c in enumerate(row):
                if c in " .":
                    continue
                self.set(x0 + i, y0 + j, key[c] if key else c)

    def mirrored(self):
        out = Pix(self.w, self.h)
        out.g = [row[::-1] for row in self.g]
        return out

    def rows(self):
        return ["".join(r) for r in self.g]

    def sprite(self, name):
        return Sprite(name, self.rows(), TONES)

    def save(self, path, k=8):
        """A picture file of it, k times enlarged: for looking at while drawing, never for the pack."""
        from PIL import Image
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        for y in range(self.h):
            for x in range(self.w):
                c = self.g[y][x]
                if c in TONES:
                    v = TONES[c].lstrip("#")
                    img.putpixel((x, y), (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16), 255))
        img.resize((self.w * k, self.h * k), Image.NEAREST).save(path)
