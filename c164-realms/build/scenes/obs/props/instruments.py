"""props/instruments -- the small instruments of the observatory (plan ART-PLAN 7.3, part A6 section
2.5, card plan/packages/props/instruments.md).

One family, one motif: a graduated brass ring or arc, a knurled brass knob, a steady foot of dark
wood, cast iron or stone. Phosphor green is on dials only and nothing else glows.

    tripod_scope       a brass telescope on a wooden tripod, two blocks tall (the south lookout)
    tripod_scope_comet the same telescope trained on the comet's head, 41 degrees up, with a star
                       diagonal to look into from above (the sunset terrace)
    celestial_globe    a star globe 20 px across in a three-legged floor stand (the star hall)
    globe              a table globe: a verdigris ball in a brass half meridian on a turned foot
    sextant            a sextant in its wooden cradle, for a table
    barometer          a banjo barometer for the wall, two blocks tall, the dial at the foot
    louvre_box         a white louvred thermometer screen on four legs and a stone slab
    regulator_clock    a precision pendulum clock in a long glazed case, two blocks tall; its
                       pendulum is the separate model regulator_pendulum (see PENDULUM)
    calc_machine       a hand-cranked calculating machine on a board, for a table
    sunshine_recorder  a glass ball before a brass bowl, for the stone pedestal of the weather station
                       (not on the card: site/outbuildings keeps a pedestal for it)

Every piece is one display entity at scale 1 (16 texels to the block), the clock two. For the other
lines:

    from scenes.obs.props import instruments
    n += instruments.place(canvas, "tripod_scope", (x, y, z), facing="west", origin=origin)

place() returns the number of display entities it placed. Nothing here is spread over the building:
the rooms and the outbuildings place what they need. build() places one piece, the telescope of the
sunset terrace, and that only once the switch DRESS is on (see site()).

No bar crosses another at right angles in any of these (RUBRIC red line 8): the celestial globe
has only the lower half of its meridian, a cradle that ends under the horizon ring, so that from
no side an upright bar stands across the level ring; the table globe's half meridian leans with its
axis; the barometer's dial is at the foot of its board.

The look is judged in the test scene build/scenes/obs_props_instruments.
"""
import functools
import math

import numpy as np

from artkit import models as M
from artkit import pixelart
from artkit.pixelart import Sprite

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from . import _kit as K

PREFIX = "prop_inst_"

IRON, IRON_D, BRASS, BRASS_D = K.IRON, K.IRON_D, K.BRASS, K.BRASS_D
WOOD = P.mat("dark_wood")
WOOD_L = P.mat("dark_wood", base=3)               # the lighter board: door frames, the clock's dial board
WOOD_D = P.mat("dark_wood", base=1)               # feet, plinths, cornices, the inside of a case
STONE = P.mat("ashlar")
WHITE = P.mat("cream", base=2, bevel=1)           # white paint on wood: the thermometer screen
WHITE_D = P.mat("cream", base=1, bevel=1)
LENS = K.flat("night_glass", 2)                   # the glass of an objective: dark, it holds the sky
EYECUP = K.flat("iron", 1)
KNOB = K.flat("brass", 4)                         # the bright end of a knurled knob
ROD = K.flat("brass", 3)                          # a rod one pixel thick: one clean line, no edges
INK = P.RAMPS["iron"][1]
LUME = P.RAMPS["phosphor"][2]


# ---- painted surfaces ----------------------------------------------------------------------------
class _Scale(pixelart.Mat):
    """A graduated limb seen face on. Lines are engraved across the grain every `pitch` pixels along
    it, `reach` pixels long from one edge of the picture (edge: "first" or "last" row or column), and
    where `long` = (pitch, phase) is given those lines are one pixel longer. The lines start from the
    limb's inner edge; the row along the other edge, its outline, is left whole and with `rim` it is
    the lit edge, one step up. A line that stood on the outline would be a notch in it against a dark
    sky, and the limb a cog."""
    pitch, phase, reach, edge, ink, rim, long = 2, 1, 1, "first", 1, True, None

    def paint(self, w, h, grain="u", seed=0):
        out = super().paint(w, h, grain, seed)
        jj, ii = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        along, across, size = (ii, jj, h) if grain == "u" else (jj, ii, w)
        depth = across if self.edge == "first" else size - 1 - across     # 0 on the edge the lines start from
        if self.rim and size >= 2:
            out[depth == size - 1, :3] = self.ramp[min(len(self.ramp) - 1, self.base + 1)]
        mark = (along % self.pitch == self.phase) & (depth < self.reach)
        if self.long:
            mark |= (along % self.long[0] == self.long[1]) & (depth < self.reach + 1)
        out[mark, :3] = self.ramp[self.ink]
        return out


def _scale(edge, pitch, phase, reach, ramp="brass", base=3, ink=1, rim=True, long=None):
    name = f"{ramp}_scale_{edge}_{pitch}_{phase}_{reach}_{ink}" + ("_rim" if rim else "") + \
        (f"_long_{long[0]}_{long[1]}" if long else "")
    s = _Scale(name, P.RAMPS[ramp], kind="flat", bevel=0, base=base)
    s.edge, s.pitch, s.phase, s.reach, s.ink, s.rim, s.long = edge, pitch, phase, reach, ink, rim, long
    return s


class _Slats(pixelart.Mat):
    """Louvres: a lit slat and the shadow under it, two pixels to the pair, level whatever the grain."""

    def paint(self, w, h, grain="u", seed=0):
        out = super().paint(w, h, grain, seed)
        out[1::2, :, :3] = self.ramp[0]
        return out


class _Ribs(pixelart.Mat):
    """Slots cut across the grain, every other pixel along it: the drum of the calculating machine."""

    def paint(self, w, h, grain="u", seed=0):
        out = super().paint(w, h, grain, seed)
        if grain == "u":
            out[:, 1::2, :3] = self.ramp[0]
        elif grain == "v":
            out[1::2, :, :3] = self.ramp[0]
        return out


SKY = P.mat("enamel", kind="flat", bevel=0, base=1)          # the ground of the celestial globe
SEA = P.mat("verdigris", kind="flat", bevel=0, base=1)       # and of the table globe
GLASS = P.mat("night_glass", kind="flat", bevel=0, base=3)   # a glass ball that is not lit from inside
SLATS = _Slats("cream_slats", P.RAMPS["cream"], kind="flat", bevel=0, base=3)
DRUM = _Ribs("iron_slots", P.RAMPS["iron"], kind="flat", bevel=0, base=3)


def _sprite(name, rows, **colours):
    return Sprite(PREFIX + name, rows, colours)


FACE, FACE_D = P.RAMPS["porcelain"][3], P.RAMPS["porcelain"][2]
MARK = P.RAMPS["iron"][5]       # what is printed on a dial; only what points is as dark as ink
DIAL_COLOURS = dict(c=FACE, d=FACE_D, k=INK, m=MARK, h=P.RAMPS["iron"][0], b=P.RAMPS["brass"][3], g=LUME)
# the barometer: a scale over the upper arc, three luminous marks; the hand is one straight line
# through the middle and points at "fair"
BARO_DIAL = [
    "..mcgcm..",
    ".mccccch.",
    "cccccchcc",
    "mcccchccm",
    "gcccbcccg",
    "mcchccccm",
    "ccccccccc",
    ".dcccccd.",
    "..ddddd..",
]
# the clock: twelve marks, the quarters luminous; the hands are drawn in by _hands()
CLOCK_DIAL = [
    "..mcgcm..",
    ".ccccccc.",
    "mcccccccm",
    "ccccccccc",
    "gcccbcccg",
    "ccccccccc",
    "mcccccccm",
    ".dcccccd.",
    "..mdgdm..",
]
# every clock on the hill is stopped at one time, five minutes before the time ball drops (director,
# g2 #34140): the skeleton's CLOCK once it has it
CLOCK = getattr(S, "CLOCK", (7, 55))


def _hands(rows, hour, minute):
    """A nine-pixel dial with its hands drawn in from the middle: the hour hand two pixels long, the
    minute hand three, one pixel to each step along the way the hand leans most."""
    grid = [list(row) for row in rows]
    mid = len(rows) // 2
    for turn, length in (((hour % 12 + minute / 60.0) / 12.0, 2), (minute / 60.0, 3)):
        dx, dy = math.sin(2.0 * math.pi * turn), -math.cos(2.0 * math.pi * turn)
        for i in range(1, length + 1):
            if abs(dx) > abs(dy):
                x, y = mid + (i if dx > 0 else -i), int(round(mid + i * dy / abs(dx)))
            else:
                x, y = int(round(mid + i * dx / abs(dy))), mid + (i if dy > 0 else -i)
            grid[y][x] = "h"
    return ["".join(row) for row in grid]


def _lume(rows):
    """Only the luminous marks of a dial, for the plate that glows in front of it."""
    return ["".join(ch if ch == "g" else "." for ch in row) for row in rows]


GLINT = P.RAMPS["porcelain"][4]         # the glint of a lens or of a glass ball: one pixel
# Clear glass as the furniture draws it (_kit.sheen_texels): the glass is left out and its reflection
# says it is there, a glancing stroke two pixels wide that climbs to the right and a shorter one
# under it, in the tone the roof lights hold the sky in; a white one was the brightest thing on the
# wall and read as paper. One column further left than the kit puts it: the clock's door is seven
# pixels wide and its middle column is the pendulum rod's, which a stroke would cut in two.
SHEEN = getattr(K, "SHEEN", P.RAMPS["night_glass"][4])
STROKES = ((1, 1), (2, 1), (0, 2), (1, 2), (1, 5), (2, 5))


def _pane(m, lo, hi):
    """A pane of clear glass that looks +z: nothing but its reflection in the upper left corner."""
    w, h = int(round(hi[0] - lo[0])), int(round(hi[1] - lo[1]))
    rows = [["."] * w for _ in range(h)]
    for i, j in STROKES:
        if i < w and j < h:
            rows[j][i] = "g"
    m.box(lo, hi, BRASS, skip="nudew", faces={"s": _sprite(f"sheen_{w}x{h}", ["".join(row) for row in rows], g=SHEEN)})


def _ball(m, name, centre, radius, mat, sides, bands, paint, swing=0.0, crown=False, depth=1.5):
    """A ball with a picture on it, as a solid of flat facets: `bands` level rings of `sides` facets,
    each a thin box that lies against the sphere and leans as the sphere does there, the top and
    bottom rings closing on the poles. `radius` is the height of the poles over the centre, the
    facets lie against a sphere a little smaller; `swing` turns the whole about the vertical. The
    rings stand level whichever way a globe's axis leans: it is the picture that is turned.

    Why not the stack of prisms of Model.ball: the game lights a face by the axis it looks along
    most, so every step of a stack is a bright ring over a dark riser and a ball of twenty pixels
    is a pile of plates. Here a ring that leans less than 45 degrees takes the light of a wall and
    one that leans more that of a floor, the same all the way round, and the ball has a lit crown,
    a girdle and a dark foot. For that no ring may lean by 45 degrees (bands is not 2, 6, 10...),
    and no facet may look half way between x and z (swing).

    A facet is as wide as the wider of its two edges, so towards a pole its corners run a little
    over its neighbours (under a sixth of a pixel proud of them) and cut a sliver out of the pixels
    beside the seam. paint(points, clear) is given the unit vectors from the centre to every pixel
    of the facets (the model's frame, an array n x 3) and which of them are seen whole; it returns
    for each pixel None (the ground, mat's own tone), a number (so many steps of mat's ramp above
    the ground) or a colour. A mark that has to stay one whole pixel, a star, goes on a clear pixel.
    The ground is one tone all over: nothing is painted lighter or darker for the light, it would
    be taken for the picture.

    The ring round a pole is all corners. With `crown` four square plates lie over it there like
    the sides of a low pyramid, a corner of each on the pole, and take its place in the picture:
    pixels seen whole on the top of the ball, where a globe on the floor is looked at most."""
    half = math.pi / (2.0 * bands)                      # half the angle a ring covers, pole to pole
    k = math.tan(math.pi / sides)
    inner = radius * math.cos(half)                     # the sphere the facets lie against
    reach = inner * math.tan(half)                      # half the height of a facet
    patches, points, clear = [], [], []

    def patch(x0, x1, y0, y1, z, spin, lean, yaw, whole):
        """A box whose face that looks +z, at z, is the rectangle x0..x1 by y0..y1 with the picture
        on it; it is turned `spin` degrees in its own plane about its middle, then leaned up by
        `lean` and swung round by `yaw`. whole(x, y, dx, dy) tells of a pixel, by its middle and
        half its size, whether it is seen whole."""
        w, h = max(1, int(round(x1 - x0))), max(1, int(round(y1 - y0)))
        dx, dy = (x1 - x0) / (2.0 * w), (y1 - y0) / (2.0 * h)
        q = M._qmul(M.quat("y", yaw), M.quat("x", -lean))
        sin, cos = math.sin(math.radians(spin)), math.cos(math.radians(spin))
        for row in range(h):
            for col in range(w):
                x, y = dx * (2.0 * col + 1.0 - w), dy * (h - 2.0 * row - 1.0)
                clear.append(whole(x + (x0 + x1) / 2.0, y + (y0 + y1) / 2.0, dx, dy))
                p = M._qrot(q, ((x0 + x1) / 2.0 + x * cos - y * sin, (y0 + y1) / 2.0 + x * sin + y * cos, z))
                size = math.sqrt(sum(v * v for v in p))
                points.append(tuple(v / size for v in p))
        patches.append((x0, x1, y0, y1, z, spin, lean, yaw, w, h))

    for i in range(bands):
        lean = (2 * i + 1) * half - math.pi / 2.0       # the latitude the ring lies against the sphere at
        foot, head = (inner * math.cos(lean) + s * reach * math.sin(lean) for s in (1.0, -1.0))
        wide = max(foot, head) * k                      # half the width of the box

        def whole(x, y, dx, dy, lean=lean, wide=wide):
            # the box runs `over` beyond the facet's own edge, most at the pixel's end nearer the pole;
            # the neighbour's corner lies over the strip from wide - 2 over to wide - over
            over = max(wide - (inner * math.cos(lean) - (y + s * dy) * math.sin(lean)) * k for s in (1.0, -1.0))
            a, b = max(0.0, abs(x) - dx), abs(x) + dx
            return wide > 2.0 * over and min(b, wide - over) - max(a, wide - 2.0 * over) <= 0.12

        polar = crown and i in (0, bands - 1)
        for s in range(sides):
            if polar:           # under the plates only the half next to the ring below is wanted
                patch(-wide, wide, min(0.0, math.copysign(reach, -lean)), max(0.0, math.copysign(reach, -lean)),
                      inner, 0.0, math.degrees(lean), swing + 360.0 * s / sides, lambda *_: False)
            else:
                patch(-wide, wide, -reach, reach, inner, 0.0, math.degrees(lean), swing + 360.0 * s / sides, whole)
        if polar:
            # the plates: square, a corner on the pole, the opposite one on the ring's far edge; a
            # hair proud of the ring, whose ridges would show through them otherwise
            apex = inner * math.cos(lean) / math.sin(lean)
            far = (inner * math.cos(lean) - max(foot, head)) / math.sin(lean)
            side = abs(apex - far) / math.sqrt(2.0)
            for s in range(4):
                patch(-side / 2.0, side / 2.0, (apex + far - side) / 2.0, (apex + far + side) / 2.0, inner + 0.08,
                      45.0, math.degrees(lean), 45.0 + 90.0 * s, lambda *_: True)
    marks = iter(paint(np.array(points), np.array(clear)))
    seed = m._seed({})
    for n, (x0, x1, y0, y1, z, spin, lean, yaw, w, h) in enumerate(patches):
        rows, chars = [], {}
        for _ in range(h):
            row = ""
            for _ in range(w):
                mark = next(marks)
                if not isinstance(mark, str):
                    mark = mat.ramp[int(min(len(mat.ramp) - 1, max(0, mat.base + (mark or 0))))]
                    mark = "#%02x%02x%02x" % tuple(int(v) for v in mark)
                row += chars.setdefault(mark, chr(ord("a") + len(chars)))
            rows.append(row)
        sprite = Sprite(f"{PREFIX}{name}_{n}", rows, {ch: c for c, ch in chars.items()})
        lo = (centre[0] + x0, centre[1] + y0, centre[2] + z - depth)
        hi = (centre[0] + x1, centre[1] + y1, centre[2] + z)
        with m.turned(("x", -lean), ("y", yaw), about=tuple(centre)):
            m.box(lo, hi, mat, rot=("z", spin, tuple((a + b) / 2.0 for a, b in zip(lo, hi))) if spin else None,
                  skip="n", seed=seed, faces={"s": sprite})


def _leaned(tilt, yaw=0.0):
    """The turn that leans a globe's polar axis `tilt` degrees from the vertical towards +x, then
    swings it `yaw` degrees about the vertical: what the pins and the rings are drawn in."""
    return M._qmul(M.quat("y", yaw), M.quat("z", -tilt))


# The brighter stars of the sky: (right ascension in hours, declination in degrees, class, warm).
# Class 1 is the dozen everybody knows, 2 the rest of the first magnitude, 3 the second-magnitude
# stars that make the figures; warm are the orange and red ones. A pixel of this globe is nearly six
# degrees, so a figure is a handful of pixels at most and no line is drawn between them.
STARS = (
    (6.75, -16.7, 1, 0), (6.40, -52.7, 1, 0), (14.66, -60.8, 1, 0), (14.26, 19.2, 1, 1), (18.62, 38.8, 1, 0),
    (5.28, 46.0, 1, 0), (5.24, -8.2, 1, 0), (7.65, 5.2, 1, 0), (1.63, -57.2, 1, 0), (5.92, 7.4, 1, 1),
    (14.06, -60.4, 1, 0), (19.85, 8.9, 1, 0), (12.44, -63.1, 1, 0),
    (4.60, 16.5, 2, 1), (16.49, -26.4, 2, 1), (13.42, -11.2, 2, 0), (7.76, 28.0, 2, 1), (22.96, -29.6, 2, 0),
    (20.69, 45.3, 2, 0), (12.80, -59.7, 2, 0), (10.14, 12.0, 2, 0), (6.98, -29.0, 2, 0), (7.58, 31.9, 2, 0),
    (12.52, -57.1, 2, 1), (17.56, -37.1, 2, 0), (5.42, 6.3, 2, 0), (5.44, 28.6, 2, 0), (9.22, -69.7, 2, 0),
    (5.60, -1.2, 2, 0),
    # the hunter and the dogs, the twins, the charioteer, the bull
    (5.68, -1.9, 3, 0), (5.53, -0.3, 3, 0), (5.80, -9.7, 3, 0), (6.38, -18.0, 3, 0), (7.14, -26.4, 3, 0),
    (6.63, 16.4, 3, 0), (5.99, 44.9, 3, 0), (3.79, 24.1, 3, 0), (5.13, -5.1, 3, 0), (5.55, -17.8, 3, 0),
    # the bears, the dragon, the queen, the king
    (11.06, 61.8, 3, 1), (11.03, 56.4, 3, 0), (11.90, 53.7, 3, 0), (12.26, 57.0, 3, 0), (12.90, 56.0, 3, 0),
    (13.40, 54.9, 3, 0), (13.79, 49.3, 3, 0), (2.53, 89.3, 3, 0), (14.85, 74.2, 3, 1), (17.94, 51.5, 3, 1),
    (0.15, 59.2, 3, 0), (0.68, 56.5, 3, 1), (0.95, 60.7, 3, 0), (1.43, 60.2, 3, 0), (21.31, 62.6, 3, 0),
    # the hero, the chained lady, the winged horse, the ram, the whale
    (3.41, 49.9, 3, 0), (3.14, 41.0, 3, 0), (2.06, 42.3, 3, 1), (1.16, 35.6, 3, 1), (0.14, 29.1, 3, 0),
    (23.06, 28.1, 3, 1), (23.08, 15.2, 3, 0), (0.22, 15.2, 3, 0), (21.74, 9.9, 3, 1), (2.12, 23.5, 3, 1),
    (0.73, -18.0, 3, 1), (3.04, 4.1, 3, 1),
    # the lion, the water snake, the maiden, the crow, the herdsman, the crown
    (10.33, 19.8, 3, 1), (11.82, 14.6, 3, 0), (11.24, 20.5, 3, 0), (9.46, -8.7, 3, 1), (12.69, -1.4, 3, 0),
    (13.04, 11.0, 3, 0), (12.26, -17.5, 3, 0), (15.58, 26.7, 3, 0), (14.75, 27.1, 3, 1),
    # the scorpion, the archer, the serpent bearer, the strong man, the scales
    (16.01, -22.6, 3, 0), (17.62, -43.0, 3, 0), (16.84, -34.3, 3, 1), (18.40, -34.4, 3, 0), (18.92, -26.3, 3, 0),
    (17.58, 12.6, 3, 0), (17.17, -15.7, 3, 0), (16.50, 21.5, 3, 0), (17.24, 14.4, 3, 1), (15.28, -9.4, 3, 0),
    # the swan, the lyre's neighbours, the eagle, the water bearer, the sea goat
    (20.37, 40.3, 3, 0), (19.51, 28.0, 3, 1), (19.77, 10.6, 3, 1), (22.10, -0.3, 3, 0), (21.53, -5.6, 3, 0),
    (21.78, -16.1, 3, 0),
    # the far south: the ship, the centaur, the crane, the peacock, the phoenix
    (8.38, -59.5, 3, 1), (9.13, -43.4, 3, 1), (8.16, -47.3, 3, 0), (8.06, -40.0, 3, 0), (8.75, -54.7, 3, 0),
    (14.11, -36.4, 3, 1), (13.66, -53.5, 3, 0), (16.81, -69.0, 3, 1), (22.14, -47.0, 3, 0), (20.43, -56.7, 3, 0),
    (0.44, -42.3, 3, 1), (5.66, -34.1, 3, 0),
)
STAR_TONES = {(1, 0): P.RAMPS["cream"][3], (1, 1): P.RAMPS["brass"][5], (2, 0): P.RAMPS["cream"][1],
              (2, 1): P.RAMPS["brass"][4], (3, 0): P.RAMPS["night_glass"][4], (3, 1): P.RAMPS["night_glass"][4]}
MILKY_WAY = (12.857, 27.13, 6.0)        # the pole of the band of the Milky Way, and half its width in degrees
GLOBE_HOUR = 9.0                        # the right ascension, in hours, that stands in front (+z) on the horizon ring:
                                        # the hunter and his dogs are up on the front of the globe, left of the pole


def _sky_point(hours, degrees, lean):
    """Where a point of the sky lies on the celestial globe, as a unit vector in the model's frame.
    The sky is seen from outside, so right ascension runs to the right for whoever faces the globe."""
    a, d = math.radians(15.0 * (hours - GLOBE_HOUR)), math.radians(degrees)
    return M._qrot(lean, (math.cos(d) * math.sin(a), math.sin(d), math.cos(d) * math.cos(a)))


def _stars(lean):
    """paint() for _ball: the sky of the celestial globe. Each star of STARS is one pixel, the pixel
    that lies nearest to it among those clear of the facets' corners; where two would stand side by
    side the fainter one is left out, so the figures stay figures of single points. The Milky Way
    is the ground one step lighter."""
    def paint(points, clear):
        marks = [None] * len(points)
        north = np.array(_sky_point(MILKY_WAY[0], MILKY_WAY[1], lean))
        for n in np.nonzero(np.abs(points @ north) < math.sin(math.radians(MILKY_WAY[2])))[0]:
            marks[n] = 1
        free = np.nonzero(clear)[0]
        taken = []
        for hours, degrees, rank, warm in sorted(STARS, key=lambda star: star[2]):
            at = np.array(_sky_point(hours, degrees, lean))
            n = int(free[np.argmax(points[free] @ at)])
            if float(points[n] @ at) < math.cos(math.radians(7.0)):
                continue                # no clear pixel near it: it lies right on a pole
            # a pixel is a little under 6 degrees: nearer than 1.3 pixels is side by side
            if all(float(points[n] @ points[other]) < math.cos(math.radians(7.4)) for other in taken):
                taken.append(n)
                marks[n] = STAR_TONES[rank, warm]
        return marks
    return paint


# The lands of the table globe: round patches (longitude, latitude, radius in degrees) that run into
# one another. It is the map of no country: three masses and two islands, so that every side of the
# ball shows a coast.
LANDS = (
    (20.0, 38.0, 30.0), (52.0, 24.0, 22.0), (74.0, 44.0, 20.0), (28.0, 2.0, 16.0), (34.0, -22.0, 13.0),
    (150.0, -20.0, 22.0), (172.0, 6.0, 15.0), (132.0, -42.0, 12.0),
    (265.0, 30.0, 24.0), (286.0, 4.0, 17.0), (292.0, -26.0, 14.0), (240.0, 52.0, 14.0),
    (110.0, 62.0, 9.0), (215.0, -8.0, 7.0),
)


def _lands(lean):
    """paint() for _ball: the map of the table globe, the lands three steps lighter than the seas (two
    are lost in the shade of the ball's own sides)."""
    def paint(points, clear):
        land = np.zeros(len(points), dtype=bool)
        for lon, lat, radius in LANDS:
            a, d = math.radians(lon), math.radians(lat)
            at = np.array(M._qrot(lean, (math.cos(d) * math.sin(a), math.sin(d), math.cos(d) * math.cos(a))))
            land |= points @ at > math.cos(math.radians(radius))
        return [3 if on else None for on in land]
    return paint


def _glass(tones, glint):
    """paint() for _ball: a ball of glass in level rings of tone, `tones` from the foot to the crown
    in steps from the ground, and its glint, one white pixel where the ball looks along `glint`."""
    def paint(points, clear):
        marks = [tones[min(len(tones) - 1, int((math.asin(max(-1.0, min(1.0, y))) / math.pi + 0.5) * len(tones)))]
                 for y in points[:, 1]]
        free = np.nonzero(clear)[0]
        marks[int(free[np.argmax(points[free] @ (np.array(glint) / np.linalg.norm(glint)))])] = GLINT
        return marks
    return paint


def _dial(m, name, rows, centre, z):
    """A round dial nine pixels across on a face that looks +z: the painted face, and in front of it
    a plate with only its luminous marks, which glows in the dark."""
    x, y = centre
    half = len(rows) / 2.0
    m.box((x - half, y - half, z - 0.25), (x + half, y + half, z), K.flat("porcelain", 3), skip="nudew",
          faces={"s": _sprite(name, rows, **DIAL_COLOURS)})
    m.box((x - half, y - half, z), (x + half, y + half, z + 0.1), K.flat("phosphor", 2), skip="nudew",
          faces={"s": _sprite(name + "_lume", _lume(rows), g=LUME)}, emit=15, shade=False)


# ---- the models ------------------------------------------------------------------------------------
SCOPE_TILT = 18.0       # degrees above the horizon: the telescope as it stands about
SCOPE_TILT_MAX = 46.0   # as far as the fork lets the tube rise: beyond, its underside meets the fork's foot
SCOPE_PIVOT = 26.5      # height of the altitude axis
SCOPE_HUB = 19.5        # height of the tripod head
COMET_TILT = 41.0       # where the director has the comet's head: due west, this far up (g2 #37928)


def comet_tilt():
    """Degrees above the horizon of the comet's head, which stands due west for every viewer. The
    sky's own number while it can be read (the comet is painted into the moon's slot; sky/comet
    works the head's elevation out for telescopes and cameras), else COMET_TILT; no higher than
    the fork allows."""
    try:
        from ..sky import comet, mood
        if hasattr(comet, "HEAD_ELEVATION"):
            tilt = float(comet.HEAD_ELEVATION)
        else:
            tilt = 90.0 - float(mood.MOON_ANGLE) - float(comet.HEAD_BELOW)
    except (ImportError, AttributeError, TypeError, ValueError):
        tilt = COMET_TILT
    return min(tilt, SCOPE_TILT_MAX)


def _scope(name, tilt, diagonal=False):
    """A brass refractor on a wooden tripod. It looks along +z and up by `tilt` degrees; one leg
    stands forward under the objective and the observer steps between the other two (the feet are
    8.5 px from the middle). On the right of the fork the graduated altitude sector, on the left
    the clamp. With `diagonal` the eyepiece stands up out of a prism housing on the end of the draw
    tube, to be looked into from above: how a refractor is used when it points high. Anchor: the
    floor under the middle of the tripod."""
    m = M.Model(PREFIX + name)
    hub = SCOPE_HUB
    for turn in (0.0, 120.0, 240.0):
        with m.turned(("y", turn)):
            with m.aimed((0.0, 0.0, 8.5), (0.0, hub - 0.5, 1.75), "y") as length:
                m.taper("y", (0, 0), 0.0, 2.5, 0.5, 1.0, IRON_D, sides=4, steps=2)      # pointed shoe
                m.tube("y", (0, 0), 2.5, length, 1.0, WOOD, sides=4)                    # leg
                m.tube("y", (0, 0), 10.0, 11.5, 1.25, BRASS_D, sides=4)                 # the clamp of the slide
    m.tube("y", (0, 0), hub - 1.5, hub + 0.5, 2.75, BRASS_D)                            # tripod head
    m.tube("y", (0, 0), hub + 0.5, hub + 1.5, 1.5, IRON)                                # azimuth bearing
    foot = hub + 1.5
    m.box((-4.0, foot, -1.5), (4.0, foot + 1.0, 1.5), IRON)                             # yoke: foot and cheeks
    for x in (-4.0, 3.0):
        m.box((x, foot + 1.0, -1.5), (x + 1.0, SCOPE_PIVOT + 1.5, 1.5), IRON, grain="y")
    m.tube("x", (SCOPE_PIVOT, 0), -5.5, -4.0, 1.5, BRASS_D, cap=KNOB)                   # clamp knob, on the left
    limb = _scale("last", 3, 1, 1)
    with m.turned(("x", -tilt), about=(0, SCOPE_PIVOT, 0)):
        c = (0, SCOPE_PIVOT)
        side, ends = 4.5, (101.25, 258.75)                                              # on the right the altitude
        m.ring("x", (side, SCOPE_PIVOT, 0), 5.5, 2.0, 0.75, BRASS, sides=16, arc=ends,
               faces={"w": limb, "e": limb})                                            # arc: a graduated sector
        for deg in ends:                                                                # hung from the axis
            a = math.radians(deg)
            m.beam((side, SCOPE_PIVOT, 0.0), (side, SCOPE_PIVOT + 4.75 * math.cos(a), 4.75 * math.sin(a)),
                   0.5, 1.0, BRASS_D)
        m.tube("x", (SCOPE_PIVOT, 0), 4.0, 5.25, 1.25, BRASS_D, cap=KNOB)               # its boss
        m.tube("z", c, -7.0, 12.0, 2.0, BRASS, sides=12)                                # main tube
        m.tube("z", c, -1.75, 1.75, 2.5, BRASS_D, sides=12)                             # cradle band
        m.tube("z", c, 6.5, 7.5, 2.25, BRASS_D, sides=12)
        m.tube("z", c, 12.0, 15.5, 2.5, BRASS_D, sides=12)                              # objective cell
        m.tube("z", c, 15.5, 15.75, 2.0, LENS, sides=12, cap=LENS)                      # the glass
        m.tube("z", c, -11.5, -7.0, 1.5, BRASS_D)                                       # draw tube
        if diagonal:
            m.box((-1.5, SCOPE_PIVOT - 1.5, -14.5), (1.5, SCOPE_PIVOT + 1.5, -11.5), BRASS_D)   # prism housing
            m.tube("y", (0, -13.0), SCOPE_PIVOT + 1.0, SCOPE_PIVOT + 4.5, 1.0, BRASS, cap=EYECUP)
        else:
            m.tube("z", c, -14.0, -11.5, 1.0, BRASS, cap=EYECUP)                        # eyepiece
        m.tube("x", (SCOPE_PIVOT - 0.5, -8.5), 1.25, 3.0, 1.0, BRASS_D, cap=KNOB)       # focus knob
        m.tube("z", (0, SCOPE_PIVOT + 3.25), 1.0, 9.5, 1.0, BRASS_D, cap=LENS)          # finder
        for z in (2.5, 7.0):
            m.box((-0.75, SCOPE_PIVOT + 1.75, z), (0.75, SCOPE_PIVOT + 2.5, z + 1.0), IRON_D)
    return m


def _tripod_scope():
    """The telescope as it stands about, SCOPE_TILT up: 34 px tall and 30 px long."""
    return _scope("tripod_scope", SCOPE_TILT)


def _tripod_scope_comet():
    """The same telescope trained on the comet's head, with a star diagonal: 39 px tall and 27 px
    long, the eyepiece 21 px above the floor and 13 px behind the middle."""
    return _scope("tripod_scope_comet", comet_tilt(), diagonal=True)


LATITUDE = getattr(S, "LATITUDE", 45.0)         # how high the pole of the sky stands (the skeleton's, once it has it)
GLOBE_R = 10.0          # the sphere: 20 px across
GLOBE_Y = 19.0          # height of its centre and of the horizon ring
GLOBE_TILT = 90.0 - LATITUDE    # the polar axis leans this far from the vertical: the globe is set for the hill
GLOBE_YAW = 0.0         # the plane of the meridian: the model's x-y plane, the pole leaning towards +x; its
                        # two ends meet the horizon ring as far from the one front leg as from the other


def _celestial_globe():
    """A star globe in a floor stand: three legs carry a wooden horizon ring with a brass scale let
    into its top; a graduated brass half meridian hangs in it, rests in a cradle on the stretchers
    and carries the sphere by its south pole. On the north pole sits the hour circle. Nothing of
    brass stands above the horizon ring but that: a whole meridian ring, seen in its own plane, is
    an upright bar across the level ring (red line 8). 28 px across the horizon ring, 29 px tall.
    The sky is the real one (STARS), seen from outside as on every star globe, and the globe is set
    for the hill's latitude: who stands in front of it (+z) has the pole up on his right, the
    model's +x. Anchor: the floor under its middle."""
    m = M.Model(PREFIX + "celestial_globe")
    cy, r = GLOBE_Y, GLOBE_R
    for turn in (60.0, 180.0, 300.0):                   # two legs in front, one behind
        with m.turned(("y", turn)):
            z = 12.0
            m.box((-1.5, 0.0, z - 1.5), (1.5, 1.5, z + 1.5), WOOD_D)                    # foot
            m.box((-1.0, 1.5, z - 1.0), (1.0, 4.5, z + 1.0), WOOD, grain="y")
            m.box((-1.25, 4.5, z - 1.25), (1.25, 7.0, z + 1.25), WOOD_D)                # the block the stretcher meets
            m.box((-1.0, 7.0, z - 1.0), (1.0, 15.0, z + 1.0), WOOD, grain="y")
            m.box((-1.25, 15.0, z - 1.25), (1.25, 16.0, z + 1.25), BRASS_D)             # collar
            m.box((-1.25, 16.0, z - 1.25), (1.25, cy - 1.0, z + 1.25), WOOD_D)
            m.box((-1.0, 5.0, 2.0), (1.0, 6.5, z - 1.25), WOOD, grain="z")              # stretcher
    m.tube("y", (0, 0), 4.5, 6.5, 2.75, WOOD_D)                                         # hub of the stretchers
    m.ring("y", (0, cy, 0), 12.5, 3.0, 2.0, WOOD, sides=24,
           faces={"u": _scale("first", 2, 1, 1, long=(4, 1))})                          # horizon ring
    lean = _leaned(GLOBE_TILT, GLOBE_YAW)
    _ball(m, "sky", (0, cy, 0), r, SKY, 16, 8, _stars(lean), swing=11.25, crown=True)
    with m.turned(("y", GLOBE_YAW)):
        for z in (-1.75, 0.75):                                                         # the cradle under the meridian
            m.box((-1.5, 6.5, z), (1.5, 8.75, z + 1.0), BRASS_D)
        m.ring("z", (0, cy, 0), r + 1.5, 2.0, 1.5, BRASS, sides=24, arc=(180.0, 360.0),
               faces={"s": _scale("first", 3, 1, 1), "n": _scale("last", 3, 1, 1)})     # half meridian, under the ring
    with m.turned(("z", -GLOBE_TILT), ("y", GLOBE_YAW), about=(0, cy, 0)):
        m.tube("y", (0, 0), cy + r - 1.0, cy + r + 0.5, 2.5, BRASS_D, cap=K.flat("brass", 3))   # hour circle
        m.tube("y", (0, 0), cy + r + 0.5, cy + r + 1.5, 1.0, BRASS_D, cap=KNOB)         # and its pointer's knob
        m.tube("y", (0, 0), cy - r - 3.25, cy - r + 1.0, 0.75, BRASS)                   # the pin at the south pole
        m.tube("y", (0, 0), cy - r - 3.5, cy - r - 2.5, 1.25, BRASS_D, cap=KNOB)        # and its nut
    return m


def _globe():
    """A table globe 18 px tall: a verdigris ball 10 px across with its lands a lighter green, its
    axis leaning 23.5 degrees, in a graduated brass half meridian on a turned wooden foot. Anchor:
    the table under its middle."""
    m = M.Model(PREFIX + "globe")
    cy, r, tilt = 11.0, 5.0, 23.5
    m.tube("y", (0, 0), 0.0, 1.0, 4.0, WOOD_D)                                          # foot
    m.tube("y", (0, 0), 1.0, 2.0, 3.0, WOOD)
    m.tube("y", (0, 0), 2.0, 4.0, 1.25, WOOD)                                           # stem
    m.tube("y", (0, 0), 3.75, 5.0, 1.75, BRASS_D)                                       # the socket of the meridian
    north = 90.0 - tilt
    m.ring("z", (0, cy, 0), r + 1.25, 1.5, 1.25, BRASS, sides=24, arc=(north - 187.5, north + 7.5),
           faces={"s": _scale("first", 2, 0, 1, ink=2), "n": _scale("last", 2, 0, 1, ink=2)})   # half meridian
    _ball(m, "earth", (0, cy, 0), r, SEA, 12, 8, _lands(_leaned(tilt)))
    with m.turned(("z", -tilt), about=(0, cy, 0)):
        for a0, a1 in ((cy - r - 2.25, cy - r + 1.0), (cy + r - 1.0, cy + r + 2.25)):
            m.tube("y", (0, 0), a0, a1, 0.75, BRASS_D, cap=KNOB)
    return m


def _sextant():
    """A sextant standing in a wooden cradle, the limb down: a brass sector of sixty degrees with a
    graduated arc, the index arm with its clamp, the two glasses, a short telescope and the wooden
    grip behind the right arm. 14 px wide, 17 px tall, 7 px deep. Anchor: the table under its middle."""
    m = M.Model(PREFIX + "sextant")
    top = (0.0, 14.5, 0.0)                              # the pivot of the index arm
    reach = 10.5                                        # radius of the limb's middle line

    def at(deg, radius, z=0.0):
        a = math.radians(deg)
        return (top[0] + radius * math.cos(a), top[1] + radius * math.sin(a), z)

    m.box((-6.5, 0.0, -3.5), (6.5, 2.0, 3.5), WOOD_D)                                   # the cradle
    for x in (-5.5, 3.5):
        m.box((x, 2.0, -1.5), (x + 2.0, 4.0, 1.5), WOOD)
    m.ring("z", top, reach, 2.0, 1.5, BRASS, sides=36, arc=(240.0, 300.0),
           faces={"s": _scale("first", 2, 0, 1, ink=2), "n": _scale("last", 2, 0, 1, ink=2)})   # the limb
    for deg in (240.0, 300.0):                                                          # the frame: no cross brace
        m.beam(top, at(deg, reach - 0.5), 1.25, 1.5, BRASS_D)
    m.tube("z", (top[0], top[1]), -0.75, 2.25, 1.5, BRASS, cap=KNOB)                    # pivot
    arm = 280.0                                         # the index arm: off the middle, clear of the cradle
    m.beam(at(arm, 0.5, 1.25), at(arm, reach + 0.5, 1.25), 1.0, 1.25, BRASS)
    c = at(arm, reach, 1.25)
    m.box((c[0] - 1.25, c[1] - 1.25, 0.75), (c[0] + 1.25, c[1] + 1.25, 2.0), BRASS_D)   # its clamp and vernier
    m.tube("z", (c[0], c[1]), 2.0, 3.0, 0.75, BRASS_D, cap=KNOB)
    m.box((-0.5, top[1] - 0.25, 2.25), (0.5, top[1] + 2.5, 3.5), LENS)                  # index glass
    g = at(240.0, 5.5)
    m.box((g[0] - 0.5, g[1] - 1.25, 0.75), (g[0] + 0.5, g[1] + 1.25, 3.0), LENS)        # horizon glass
    t = at(300.0, 5.5)
    m.tube("x", (t[1], 1.75), t[0] - 0.5, t[0] + 4.5, 1.0, BRASS, cap=LENS)             # telescope
    m.tube("x", (t[1], 1.75), t[0] + 0.5, t[0] + 1.5, 1.25, BRASS_D)                    # and its collar
    m.beam(at(300.0, 3.0, -2.75), at(300.0, 9.5, -2.75), 1.5, 2.0, WOOD)                # the grip, behind the right arm
    for radius in (4.0, 8.5):                                                           # on its two posts
        p = at(300.0, radius)
        m.box((p[0] - 0.5, p[1] - 0.5, -2.25), (p[0] + 0.5, p[1] + 0.5, -0.5), BRASS_D)
    return m


BARO_DIAL_Y = 7.0       # height of the dial's centre above the piece's foot


def _barometer():
    """A banjo barometer for the wall, two blocks tall: the round dial at the foot, a long neck with a
    thermometer above it. The dial's marks glow. 12 px wide, 32 px tall, 3.5 px off the wall. Anchor:
    the point on the wall behind the foot."""
    m = M.Model(PREFIX + "barometer")
    y = BARO_DIAL_Y
    m.box((-1.5, 0.0, 0.0), (1.5, 1.0, 2.0), WOOD_D)                                    # drop under the case
    m.tube("z", (0, y), 0.0, 2.0, 6.0, WOOD, sides=16, cap=K.flat("dark_wood", 3))      # the round case
    m.ring("z", (0, y, 2.5), 5.0, 1.5, 1.0, BRASS, sides=16)                            # bezel
    _dial(m, "baro_dial", BARO_DIAL, (0.0, y), 2.5)
    m.tube("z", (0, y - 5.0), 3.0, 3.5, 0.75, BRASS_D, cap=KNOB)                        # set-hand knob, on the bezel
    m.box((-2.5, y + 5.0, 0.0), (2.5, 29.0, 1.0), WOOD, grain="y")                      # neck
    m.box((-1.5, 15.0, 1.0), (1.5, 27.0, 1.25), K.flat("porcelain", 3), skip="nudew",
          faces={"s": _sprite("baro_thermo", ["ctc", "mtc"] * 4 + ["cqc", "mqc"] * 2, c=FACE, m=MARK,
                              t=P.RAMPS["porcelain"][4], q=P.RAMPS["iron"][2])})        # thermometer
    for ty in (14.0, 27.0):
        m.box((-1.5, ty, 1.0), (1.5, ty + 1.0, 2.0), BRASS_D)                           # its clips
    m.box((-3.5, 29.0, 0.0), (3.5, 30.0, 2.0), WOOD_D)                                  # cap
    m.box((-1.5, 30.0, 0.0), (1.5, 32.0, 2.0), BRASS_D, faces={"u": KNOB})              # the urn on it
    return m


CLOCK_DIAL_Y = 24.5     # height of the dial's centre above the case's foot
PENDULUM_PIVOT = (0.0, 24.5, 2.5)       # model units from the clock's anchor: behind the middle of the dial
PENDULUM_LENGTH = 17.0                  # pivot to the middle of the bob: a seconds pendulum, a block long


def _regulator_clock():
    """A precision pendulum clock in a long case, two blocks tall: the case 11 px wide, 13 px over the
    plinth and the cornice, 6 px off the wall. The dial fills the hood; under it a glazed door, and
    behind the glass the beat scale under the pendulum's tip. The pendulum is the model
    regulator_pendulum and hangs behind the dial board, the whole of its bob clear of the door's
    rails. Anchor: the point on the wall behind the middle of the case's foot.

    The case is an odd number of pixels wide, like the dial, so that all of it lies on one grid."""
    m = M.Model(PREFIX + "regulator_clock")
    m.box((-5.5, 2.0, 0.0), (5.5, 30.0, 1.0), WOOD_D)                                   # back board
    for x in (-5.5, 4.5):
        m.box((x, 2.0, 1.0), (x + 1.0, 30.0, 5.0), WOOD, grain="y")                     # sides
    m.box((-6.5, 0.0, 0.0), (6.5, 2.0, 6.0), WOOD_D)                                    # plinth
    m.box((-6.5, 30.0, 0.0), (6.5, 32.0, 6.0), WOOD_D)                                  # cornice
    m.box((-4.5, 19.0, 4.0), (4.5, 30.0, 5.0), WOOD_L)                                  # hood: the dial board
    _dial(m, "clock_dial", _hands(CLOCK_DIAL, *CLOCK), (0.0, CLOCK_DIAL_Y), 5.25)
    m.ring("z", (0, CLOCK_DIAL_Y, 5.375), 5.0, 1.0, 0.75, BRASS, sides=16)              # bezel
    for x in (-4.5, 3.5):                                                               # the door: stiles and rails
        m.box((x, 2.0, 4.0), (x + 1.0, 19.0, 5.0), WOOD_L, grain="y")
    for y in (2.0, 18.0):
        m.box((-3.5, y, 4.0), (3.5, y + 1.0, 5.0), WOOD_L, grain="x")
    _pane(m, (-3.5, 3.0, 4.65), (3.5, 18.0, 4.75))                                      # the door's glass
    m.box((-2.5, 3.0, 1.0), (2.5, 4.0, 1.25), K.flat("porcelain", 3), skip="nudew",
          faces={"s": _sprite("clock_beat", ["mcmcm"], c=FACE, m=MARK)})                # beat scale
    m.tube("z", (4.0, 11.0), 5.0, 6.0, 0.75, BRASS_D, cap=KNOB)                         # door knob
    return m


def _regulator_pendulum():
    """The pendulum of the regulator clock, hanging plumb: a rod and a brass bob with its rating nut.
    Anchor: the pivot it swings about; the swing is a turn about the model's z axis."""
    m = M.Model(PREFIX + "regulator_pendulum")
    m.box((-0.75, -0.75, -0.5), (0.75, 0.25, 0.5), BRASS_D)                             # suspension
    m.box((-0.5, -PENDULUM_LENGTH, -0.25), (0.5, -0.75, 0.25), ROD, grain="y")          # rod
    m.tube("z", (0, -PENDULUM_LENGTH), -0.6, 0.6, 2.5, BRASS, sides=12, cap=KNOB)       # bob
    m.tube("y", (0, 0), -PENDULUM_LENGTH - 3.5, -PENDULUM_LENGTH - 2.5, 0.75, BRASS_D)  # rating nut
    return m


def _louvre_box():
    """A thermometer screen: a white box louvred on all four sides under a pitched roof, on four legs
    bolted to a stone slab; the door is on the +z side. The slab 14 x 12 px, the roof 14 px long and
    15 px over the eaves, 31 px tall. Anchor: the ground under its middle."""
    m = M.Model(PREFIX + "louvre_box")
    m.box((-7.0, 0.0, -6.0), (7.0, 2.0, 6.0), STONE)                                    # slab
    for x in (-6.0, 4.0):
        for z in (-5.0, 3.0):
            m.box((x, 2.0, z), (x + 2.0, 3.0, z + 2.0), IRON_D)                         # iron shoes
            m.box((x, 3.0, z), (x + 2.0, 16.0, z + 2.0), WHITE_D, grain="y")            # legs
            m.box((x, 17.0, z), (x + 2.0, 26.0, z + 2.0), WHITE, grain="y")             # corner posts
    for x in (-6.0, 5.0):                                                               # rails between the legs
        m.box((x, 6.0, -3.0), (x + 1.0, 8.0, 3.0), WHITE_D, grain="z")
    m.box((-4.0, 6.0, -5.0), (4.0, 8.0, -4.0), WHITE_D, grain="x")
    m.box((-5.0, 17.0, -4.0), (5.0, 26.0, 4.0), SLATS)                                  # the louvred panels
    for y in (16.0, 26.0):
        m.box((-6.0, y, -5.0), (6.0, y + 1.0, 5.0), WHITE)                              # bottom and top frame
    m.box((-1.0, 17.0, 4.0), (1.0, 26.0, 5.0), WHITE, grain="y")                        # the meeting stile of the doors
    m.tube("z", (0.5, 21.5), 5.0, 6.0, 0.5, BRASS_D, sides=4, cap=KNOB)                 # door knob
    for half, y0, y1 in ((3.0, 27.0, 28.0), (1.0, 28.0, 29.0)):                         # gables, under the boards
        m.box((-6.0, y0, -half), (6.0, y1, half), WHITE)
    rise, run = 4.0, 7.5
    slope, pitch = math.hypot(rise, run), math.degrees(math.atan2(rise, run))
    for side in (1.0, -1.0):                                                            # the two roof boards: they
        with m.turned(("x", side * pitch), about=(0.0, 30.5, 0.0)):                     # rest on the gables' corners
            lo, hi = sorted((0.0, side * slope))
            m.box((-7.0, 29.5, lo), (7.0, 30.5, hi), WHITE_D, grain="x")
    m.box((-7.25, 30.0, -0.75), (7.25, 31.0, 0.75), IRON_D, grain="x")                  # ridge
    return m


def _calc_machine():
    """A hand-cranked calculating machine on a wooden board: the slotted drum between two iron side
    plates with a brass setting lever standing in each slot, the result register in the carriage in
    front, the crank on the right. 13 px wide, 15.5 px with the crank, 11 px deep, 9 px tall.
    Anchor: the table under the middle of the board."""
    m = M.Model(PREFIX + "calc_machine")
    m.box((-6.5, 0.0, -5.0), (6.5, 1.0, 6.0), WOOD_D)                                   # board
    m.box((-5.5, 1.0, 2.0), (5.5, 4.0, 5.0), IRON_D)                                    # carriage
    m.box((-4.5, 2.0, 5.0), (4.5, 3.0, 5.1), K.flat("porcelain", 3), skip="nudew",
          faces={"s": _sprite("calc_register", ["cbcbcbcbc"], c=FACE, b=P.RAMPS["brass"][2])})   # result windows in a brass strip
    m.box((-5.5, 1.0, -4.0), (5.5, 3.0, 2.0), IRON)                                     # body
    for x in (-5.5, 4.5):
        m.box((x, 3.0, -4.0), (x + 1.0, 8.0, 2.0), IRON, grain="y")                     # side plates
    axis = (5.0, -1.0)                                                                  # (y, z) of the drum's axis
    m.tube("x", axis, -4.5, 4.5, 3.0, DRUM, sides=12)                                   # the slotted drum
    for x, deg in ((-3.0, 20.0), (-1.0, 55.0), (1.0, 35.0), (3.0, 70.0)):               # a lever in each slot
        with m.turned(("x", deg), about=(0.0, axis[0], axis[1])):
            m.box((x - 0.5, axis[0] + 2.75, axis[1] - 0.5), (x + 0.5, axis[0] + 3.75, axis[1] + 0.5), KNOB)
    m.tube("x", axis, 5.5, 7.0, 0.75, BRASS_D)                                          # crank: axle, arm, grip
    m.beam((6.5, 5.0, -1.0), (6.5, 8.0, 1.0), 1.0, 1.0, BRASS)
    m.tube("x", (8.0, 1.0), 6.5, 9.0, 0.75, WOOD_D, cap=K.flat("dark_wood", 3))
    m.tube("x", (2.5, 3.5), -6.5, -5.5, 1.0, BRASS_D, cap=KNOB)                         # clearing knob on the carriage
    return m


def _sunshine_recorder():
    """A sunshine recorder for a stone pedestal: a glass ball on a brass pillar burns the sun's track
    into the card that lies in the brass bowl behind and below it, a half ring square to the polar
    axis. The ball is seen from the front (+z, the side of the sun). 10 px wide, 10 px tall, 9 px
    deep. Anchor: the pedestal top under its middle."""
    m = M.Model(PREFIX + "sunshine_recorder")
    cy, r = 7.0, 3.0
    m.box((-5.0, 0.0, -5.0), (5.0, 1.0, 4.0), IRON_D)                                   # base plate
    for x in (-4.0, 4.0):
        m.tube("y", (x, 3.0), 1.0, 2.0, 0.75, BRASS_D, cap=KNOB)                        # levelling screws
    m.tube("y", (0, 0), 1.0, 2.0, 2.0, BRASS_D)                                         # the foot of the pillar
    m.tube("y", (0, 0), 2.0, cy - r + 0.25, 1.0, BRASS)                                 # pillar: the ball sits on it
    m.box((-1.0, 2.0, -3.0), (1.0, 3.0, -0.5), BRASS_D)                                 # the arm that carries the bowl
    with m.turned(("x", -LATITUDE), about=(0.0, cy, 0.0)):                              # y is the polar axis in here
        m.ring("y", (0.0, cy, 0.0), r + 1.5, 1.0, 3.0, BRASS, sides=16, arc=(0.0, 180.0),
               faces={"w": _scale("last", 2, 0, 2, ramp="cream", ink=0, rim=False)})    # the bowl and the card in it
    # the glass ball, five rings of ten facets two pixels square. From the foot up: dark where it
    # rests, the light it gathers low down, dark where one looks through it, and the sky on its
    # crown; the game lights the crown and shades the foot besides. Its glint is one white pixel up
    # and to the left of the front
    _ball(m, "glass", (0.0, cy, 0.0), r + 0.15, GLASS, 10, 5, _glass((-1, 1, -1, 0, 0), (-0.5, 0.62, 0.6)))
    return m


# name -> how it is mounted; "table" pieces stand on a floor too
SPEC = {
    "tripod_scope": dict(build=_tripod_scope, mount="floor"),
    "tripod_scope_comet": dict(build=_tripod_scope_comet, mount="floor"),
    "celestial_globe": dict(build=_celestial_globe, mount="floor"),
    "globe": dict(build=_globe, mount="floor"),
    "sextant": dict(build=_sextant, mount="floor"),
    "barometer": dict(build=_barometer, mount="wall"),
    "louvre_box": dict(build=_louvre_box, mount="floor"),
    "regulator_clock": dict(build=_regulator_clock, mount="wall"),
    "regulator_pendulum": dict(build=_regulator_pendulum, mount="wall"),
    "calc_machine": dict(build=_calc_machine, mount="floor"),
    "sunshine_recorder": dict(build=_sunshine_recorder, mount="floor"),
}
SCALE = {PREFIX + name: 1.0 for name in SPEC}
# what motion needs to swing the pendulum: the entity carries the tag, stands on the pivot and turns
# about the axis the clock faces along (the model's z); a seconds pendulum, a block long
PENDULUM = dict(tag="c164_pendulum", pivot=tuple(v / 16.0 for v in PENDULUM_PIVOT), axis="z",
                swing=3.0, period_ticks=40)


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + name: spec["build"]() for name, spec in SPEC.items()}


def models():
    return dict(_models())


# ---- placing -----------------------------------------------------------------------------------------
def place(canvas, kind, pos, facing="south", origin=(0, 0, 0), yaw=None, **opts):
    """Put one instrument into the scene; returns the number of display entities (1; the clock 2).

    kind     a key of SPEC ("regulator_pendulum" comes with the clock).
    pos      scene coordinates. A standing piece: the middle of its foot on the floor or on the
             table top. "barometer" and "regulator_clock": the point on the wall face behind the
             middle of the piece's foot (both are 2 blocks tall from there).
    facing   the way the piece's front looks: the telescope's objective, the door of the louvre
             box, the dials; for the two wall pieces the way the wall face looks. yaw (degrees)
             turns a standing piece freely instead.
    opts     go to artkit.models.display (brightness, view).
    """
    spec = SPEC[kind]
    yaw = K.FACING[facing] if yaw is None else yaw
    n = K.put(canvas, _models()[PREFIX + kind], pos, mount=spec["mount"], yaw=yaw, origin=origin, **opts)
    if kind == "regulator_clock":
        dx, dy, dz = K.turn(yaw, PENDULUM["pivot"])
        n += K.put(canvas, _models()[PREFIX + "regulator_pendulum"], (pos[0] + dx, pos[1] + dy, pos[2] + dz),
                   mount="wall", yaw=yaw, origin=origin, **opts)
        canvas.entities[-1][3]["Tags"].append(PENDULUM["tag"])
    return n


# ---- the site --------------------------------------------------------------------------------------------
# The rooms and the outbuildings place their instruments themselves, with place(). One piece is left
# to this package, because site/terrain is blocks only: the telescope of the sunset terrace (plan
# ART-PLAN 4; director, g2 #37928). It stands on the axis at the west end of the walk from the west
# door, between the inner pair of benches that props/furniture sets either side of the walk, and is
# trained on the head of the comet, due west and 41 degrees up: who comes out of the west door walks
# straight up to its eyepiece and finds the comet in it. The two blocks between it and the rail
# stay free to walk in. The switch, dress() and site() work like those of props/furniture.
DRESS = False           # off in the master scene until the family has passed review; a test scene asks
                        # for the site's instruments with dress(canvas), or calls site()
SUNSET_SCOPE = 16.0     # blocks west of the middle of the terrace's half-circle, on the axis


def site_pieces():
    """The instruments of the site as (group, kind, point, yaw). point is the middle of the piece's
    foot in scene coordinates before the origin."""
    cx, cz = S.SUNSET_PLATFORM["centre"]
    point = (S.mid(cx) - SUNSET_SCOPE, float(S.GROUND), S.mid(cz))
    return [("sunset", "tripod_scope_comet", point, K.FACING["west"])]


def _stands(canvas, foot, origin=(0, 0, 0)):
    """True when the piece has a floor under the middle of its foot on the canvas as it is, and room
    to stand in: the cell below is taken and the cell above that is free (a light source in it
    does not count)."""
    x, z = math.floor(foot[0] + origin[0]), math.floor(foot[2] + origin[2])
    y = math.ceil(foot[1] + origin[1])
    return canvas.has(x, y - 1, z) and canvas.name(x, y, z) in (None, B.LIGHT)


def dress(canvas, on=True):
    """Ask for the instruments of the site on this canvas while the switch DRESS is off (a test
    scene). Call it before the lines are built."""
    canvas.instruments_dress = bool(on)


def site(canvas, origin=(0, 0, 0), groups=None):
    """Place the instruments of the site (site_pieces()), or of the groups named ("sunset"). A piece
    is only placed where its floor is on the canvas as it is, so a tree without the terrace has no
    telescope floating in the air; what was left out is kept in canvas.instruments_left_out as
    (group, kind, point). A piece is placed once: a second call adds what does not stand yet.
    Returns the number of display entities placed by this call."""
    origin = tuple(origin)
    placed = getattr(canvas, "instruments_placed", None)
    if placed is None:
        placed = canvas.instruments_placed = set()
    n, left = 0, list(getattr(canvas, "instruments_left_out", []))
    for group, kind, p, yaw in site_pieces():
        if (groups is not None and group not in groups) or (kind, p, origin) in placed:
            continue
        if _stands(canvas, p, origin):
            n += place(canvas, kind, p, yaw=yaw, origin=origin)
            placed.add((kind, p, origin))
        elif (group, kind, p) not in left:
            left.append((group, kind, p))
    canvas.instruments_left_out = [e for e in left if (e[1], e[2], origin) not in placed]
    return n


def build(canvas, origin=(0, 0, 0)):
    """What this package places in the master scene itself: the instruments of the site (site()),
    once the switch DRESS is on or a test scene has asked for it (dress()). Everything else is
    placed by the lines that build the rooms and the outbuildings, each piece where it is used,
    with place()."""
    if getattr(canvas, "instruments_dress", DRESS):
        return site(canvas, origin)
    return 0
