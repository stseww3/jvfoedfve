"""machines/clock.py -- the master clock, the tower clock and the time ball.

Card plan/packages/machines/clocks.md; detail plan/parts/A5-machines.md 2.4 and 3.3; ART-PLAN 5.3, 7.2.
One set of timekeeping told in three places. Every dial shows the same time, TIME (the skeleton's
CLOCK): five minutes to eight. The blue hour of the pictures is eight in the evening, so the whole
hill stands at the moment before the time signal: the dials say 7:55 and the ball has been hoisted
half-way up its mast, the sign that it is about to drop (A0, 11-15).

The master clock (star hall). A long-case regulator in dark wood and brass, the one source of time
for the hill. It stands on the slate step at the east foot of the telescope pier with its back on
the pier and faces the front door (skeleton MOTHER_CLOCK: back x 6.0, axis z 0.5, y 1.0..5.0; the
case is 1.5 wide, 0.75 deep and 4 high). The pier is the one mass in the building that the floors
do not shake, which is why the regulator is fixed to it. Behind the glazed door of the trunk are
the brass plate and the two wheels of the movement, two copper coils on an iron yoke with the
armature on the pendulum rod between them (the clock is driven and read electrically), the
pendulum, and the beat scale under its pointer. Nothing glows. The dial is a piece of its own with
a fixed light (MASTER_DIAL_LIGHT), a little above what the hall gives the case, so that it is the
light spot of the clock; case and pendulum take the light of the cell they stand in, the one in
front of the trunk. The light source that goes with the clock is one hidden light in front of the
dial (MASTER_LAMP); it is handed to sky/_lightkit, which places it.

The tower clock (time tower). Four equal dials, one in the middle of each face of the shaft, centre
at y 27.5, 2.75 blocks across: white enamel, a thin brass rim, a mark at every hour (no numerals:
at 44 pixels they do not fit) and two heavy dark hands. Nothing glows and no light source goes with
it (A0, 11-14: a dial may not be brighter than the frosted windows of the front). The warm tone of
the dial at night is the fixed light its entities are given (DIAL_LIGHT, block light only, set for
each facing so that the four dials are equally bright). main/tower leaves a dark recess, three
blocks wide, for each dial. tower() reads the canvas: the dial sits DIAL_INSET inside the mouth of
the recess as it is built, never behind its back, and on a flush wall it is fixed to the surface.
The dial is smaller than the recess, so a dark ring stays round it. A drum behind the dial carries
it from the back of the recess; in a flush wall the drum is buried and not seen.

The time ball. A ball 2.5 blocks across, threaded on the mast of the tower (the mast, the vane and
what else stands on it are main/tower's), with an iron sleeve at each pole and a catch plate tight
under it, narrower than the ball: the plate travels with the ball, so it never stands alone on the
mast as a bar (a cross is a red line). Two colours until A0 picks one on the pictures: old copper
(BALL, the default) and dark red. Where no mast stands yet (the white model) the ball lies at the
foot of the mast.

Models; px equals the scale each is shown at, so every texture is 16 pixels to the block:
  mach_clock_master          the case with its movement, coils and beat scale             scale 2
  mach_clock_master_dial     the master dial and its bezel; anchor = the middle of its back   1
  mach_clock_master_hand_h   its hour hand; anchor = the dial centre                           1
  mach_clock_master_hand_m   its minute hand                                                   1
  mach_clock_pendulum        rod, armature, bob and pointer; anchor = the pivot                1
  mach_clock_face            one tower dial; anchor = its centre on the back plane             2
  mach_clock_hand_h          a tower hour hand; anchor = the dial centre                       1
  mach_clock_hand_m          a tower minute hand                                               1
  mach_clock_ball            the time ball in old copper; anchor = its centre                  1
  mach_clock_ball_red        the same in dark red                                              1
18 display entities in all (master 5, tower 12, ball 1); the budget of this card is 40.

Moving pieces, for motion (A8). Only the pendulum moves in this version of the map (A0, 11-15: the
sky is locked at eight in the evening, so the hands stand at 7:55 and the ball waits at half mast; a
clock that ran would part from the sky). The hands and the ball are entities of their own all the
same. The pose placed here is where a loop starts: the pendulum hangs plumb. Each piece has a tag:
  c164_clock_pendulum   swings about the model's z axis through its anchor, PENDULUM_SWING degrees
        each way, there and back in two seconds: transformation("pendulum", degrees).
  c164_clock_hand_h, c164_clock_hand_m   all five hour hands and all five minute hands. A hand
        turns about the model's z axis through its anchor, clockwise as the dial is looked at:
        transformation(name, -degrees) with degrees from hand_angles(hour, minute).
  c164_clock_ball       slides along the mast, y only: BALL_HALF_Y (the pose now), BALL_UP_Y at
        the top of the mast, BALL_REST_Y after the drop.
transformation() gives the whole "transformation" of the entity for a turn, because the anchor of a
hand or of the pendulum is not the middle of its model and the translation changes with the turn.

    from scenes.obs.machines import clock
    n = clock.build(canvas, origin)      # both; or clock.master(...) and clock.tower(...) alone
"""
import functools
import math

import numpy as np

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..props import _kit as K

PREFIX = "mach_clock_"

# What every dial shows: the hour and the minute. S2 keeps the number in the skeleton (A0, 11-15).
TIME = tuple(getattr(S, "CLOCK", (7, 55)))

TAG_HOUR, TAG_MINUTE = "c164_clock_hand_h", "c164_clock_hand_m"
TAG_PENDULUM, TAG_BALL = "c164_clock_pendulum", "c164_clock_ball"

# --- the master clock ---------------------------------------------------------------------------
# Its pieces are measured in pixels (16 to the block) from the middle of the case's foot on the
# pier face: x across, y up, z out into the room.
MASTER_AT = (S.MOTHER_CLOCK["back_x"], S.MOTHER_CLOCK["y"][0], S.MOTHER_CLOCK["z"])    # (6.0, 1.0, 0.5)
MASTER_FACING = S.MOTHER_CLOCK["facing"]                                               # "east"
# A display entity takes the light of the cell it stands in. The case's entity stands at the height
# of the trunk's top, not at the foot, so that the case is lit like the wall behind the trunk and
# the dial, where the lamp is, and not like the floor.
MASTER_HOLD = 40.0
MASTER_PIVOT = (0.0, 37.0, 6.25)     # the pendulum's pivot
MASTER_DIAL = (0.0, 51.0, 10.5)      # the middle of the dial's back, on the front of the hood
MASTER_DIAL_LIGHT = (0, 9)           # (sky, block) for the dial and its hands (cr2 and lights, 11-15)
# the hidden light in front of the dial: the cell and the level (lights, 11-15: (7, 3, 0), level 8)
MASTER_LAMP = ((int(MASTER_AT[0]) + 1, int(MASTER_AT[1]) + 2, int(math.floor(MASTER_AT[2]))), 8)
PENDULUM_SWING = 5.0                 # degrees each way (A8)
PENDULUM_POSE = 0.0                  # the still pose is where the loop starts: plumb (motion, 11-15)

# --- the tower clock ----------------------------------------------------------------------------
SIDES = ("east", "south", "west", "north")
# facing -> (the step out of the wall in x and z, the outer face of the shaft as the skeleton has it)
_WALLS = {
    "east": ((1, 0), S.CLOCK_SHAFT_X[1] + 1.0),       # x 17.0
    "west": ((-1, 0), float(S.CLOCK_SHAFT_X[0])),     # x 10.0
    "south": ((0, 1), S.CLOCK_SHAFT_Z[1] + 1.0),      # z -26.0
    "north": ((0, -1), float(S.CLOCK_SHAFT_Z[0])),    # z -33.0
}
_SCAN = 5                        # cells looked through for the wall, from one proud of the shaft inwards
DIAL_Y = 27.5                    # the centre of every dial
DIAL_INSET = 0.25                # how far the dial's back plane sits inside the mouth of its recess
DIAL_DRUM = 0.75                 # the drum behind the dial, in blocks
# The east and west faces of a display entity are drawn at 0.50 of the light it is given, the north
# and south faces at 0.74. With these two values the white of the four dials comes out alike: by the
# light table about 0.32 of full white, between the stone of the walls (0.19) and the orange windows
# (0.42), far below the frosted windows (0.54). Start low; raise it on the pictures if the dial does
# not read (cr2). Block light 8 on an east face would be 0.25.
DIAL_LIGHT = {"east": (0, 11), "west": (0, 11), "south": (0, 7), "north": (0, 7)}
FAR = 4.0                        # view_range of everything on the tower: seen from the far platforms

# --- the time ball ------------------------------------------------------------------------------
BALL = "copper"                  # the colour tower() hangs: "copper" or "red"
BALL_AXIS = (S.mid(*S.CLOCK_SHAFT_X), S.mid(*S.CLOCK_SHAFT_Z))     # (13.5, -29.5): the mast
BALL_R = 20.0                    # pixels: 2.5 blocks across (A0, 11-14)
BALL_PLATE = 14.0                # the catch plate's radius: under eight tenths of the ball's (cr2)
BALL_FOOT = BALL_R + 3.5         # from the ball's centre down to the foot of its lower sleeve
MAST_FOOT_Y = S.CLOCK_TOP + 1.0                      # 42.0: the tip of the roof, where the mast starts
BALL_HALF_Y = S.CLOCK_BALL_MAST - 4.5                # 47.5: half-way up, five minutes before the hour
BALL_UP_Y = S.CLOCK_BALL_MAST - 2.75                 # 49.25: at the top, 1.5 blocks of mast above it
BALL_REST_Y = MAST_FOOT_Y + BALL_FOOT / 16.0         # 43.46875: dropped, on the foot of the mast
BALL_LIGHT = (0, 10)

# --- materials (palette only) -------------------------------------------------------------------
WOOD = P.mat("dark_wood")
# the panels that face the room are one step lighter: a face that looks east is drawn at half light
WOOD_FRONT = P.mat("dark_wood", base=3)
WOOD_DEEP = P.mat("dark_wood", base=1)       # the inside of the trunk
BRASS = P.mat("brass")
BRASS_DARK = P.mat("brass_dark")
# rims and bosses that look at the viewer: Model.ring and Model.tube paint such a face one step down
BRASS_LIGHT = P.mat("brass", base=4)
BRASS_BRIGHT = P.mat("brass", base=5)
BRASS_LINE = K.flat("brass", 3)              # a line one pixel wide: one tone, or it breaks into dashes
IRON_DARK = P.mat("iron_dark")
STEEL = P.mat("iron", base=5)
COPPER = P.mat("old_copper")
CREAM = P.mat("cream")

INK = P.colour("iron", 1)
ENAMEL = [P.colour("cream", i) for i in range(len(P.RAMPS["cream"]))]      # dark to light
# the paint of the ball, three flat tones from its underside to its crown
BALL_TONES = {
    "copper": ("ball", [K.flat("old_copper", i) for i in (1, 2, 3)]),
    "red": ("ball_red", [K.flat("signal", i) for i in (0, 1, 1)]),
}

SCALE = {}                       # model name -> the scale it is shown at (filled by _models())


class _Picture:
    """A face painted by hand: the pixels as they are, for the one face size they were drawn for."""

    def __init__(self, name, pixels):
        self.name = name
        self.pixels = pixels

    def paint(self, w, h, grain="u", seed=0):
        if (h, w) != self.pixels.shape[:2]:
            raise ValueError(f"{self.name} is drawn {self.pixels.shape[1]}x{self.pixels.shape[0]}, "
                             f"the face asks for {w}x{h}")
        return self.pixels.copy()


# --- the dials ----------------------------------------------------------------------------------
def hand_angles(hour, minute):
    """Degrees clockwise from twelve: (hour hand, minute hand)."""
    return ((hour % 12) + minute / 60.0) * 30.0, minute * 6.0


def _disc(size, radius, shade):
    """An enamel disc on a clear square: full white, a ring of shade under the rim (from the radius
    `shade` outwards), darker where the rim stands between the dial and the light (upper left)."""
    c = size / 2.0
    px = np.zeros((size, size, 4), dtype=np.uint8)
    for j in range(size):
        for i in range(size):
            x, y = i + 0.5 - c, c - (j + 0.5)
            r = math.hypot(x, y)
            if r > radius:
                continue
            tone = ENAMEL[3]
            if r > shade:
                tone = ENAMEL[1] if y - x > 0.85 * r else ENAMEL[2]
            px[j, i, :3] = tone
            px[j, i, 3] = 255
    return px


def _marks(px, quarter, other):
    """Twelve hour marks in ink. quarter and other are (from, to, half width) in pixels, measured
    out from the centre and across the mark: the marks at twelve, three, six and nine, and the rest."""
    size = px.shape[0]
    c = size / 2.0
    for hour in range(12):
        s, k = math.sin(math.radians(30.0 * hour)), math.cos(math.radians(30.0 * hour))
        lo, hi, half = other if hour % 3 else quarter
        for j in range(size):
            for i in range(size):
                x, y = i + 0.5 - c, c - (j + 0.5)
                if lo - 1e-6 <= x * s + y * k <= hi + 1e-6 and abs(x * k - y * s) < half + 1e-6:
                    px[j, i, :3] = INK
                    px[j, i, 3] = 255


def _tower_dial():
    """The tower dial, 40 pixels across inside its rim. From the rim in: a line all round and a bar
    hanging from it at every hour, two pixels wide, longer at the quarters. The disc is drawn a
    little under the rim so that no gap shows at the corners of the many-sided ring."""
    size, c = 40, 20.0
    px = _disc(size, 20.7, 18.6)
    for j in range(size):
        for i in range(size):
            if 17.5 < math.hypot(i + 0.5 - c, c - (j + 0.5)) <= 18.5:
                px[j, i, :3] = INK
    _marks(px, (13.5, 17.5, 1.0), (15.5, 17.5, 1.0))
    return _Picture("clock_tower_dial", px)


def _master_dial():
    """The master dial, 18 pixels across: a square of four pixels at each quarter, a dot at each of
    the other hours. Nothing else: the hands need the room."""
    px = _disc(18, 9.7, 8.1)
    _marks(px, (6.5, 7.5, 1.0), (6.9, 7.6, 0.5))
    return _Picture("clock_master_dial", px)


def _rows(w, h, marks):
    grid = [["."] * w for _ in range(h)]
    for ch, cells in marks.items():
        for i, j in cells:
            grid[j][i] = ch
    return ["".join(row) for row in grid]


# --- the master clock's models ------------------------------------------------------------------
def _master():
    """The case, drawn in pixels (two to a model unit): skirting 0..2, plinth 2..8, its cap 8..10,
    the trunk 10..38 (18 wide, the door's glass 12 x 22), the neck 38..40, the hood 40..62 with the
    dial on its front, the cornice 62..64. The anchor is MASTER_HOLD up the back."""
    m = M.Model(PREFIX + "master", px=2.0, anchor=(0.0, MASTER_HOLD / 2.0, 0.0))

    def box(a, b, mat, **kw):
        m.box(tuple(v / 2.0 for v in a), tuple(v / 2.0 for v in b), mat, **kw)

    def tube(axis, c, a0, a1, radius, mat, **kw):
        m.tube(axis, (c[0] / 2.0, c[1] / 2.0), a0 / 2.0, a1 / 2.0, radius / 2.0, mat, **kw)

    # the plinth: skirting, body with a raised field, cap
    box((-12, 0, 0), (12, 2, 12), WOOD, skip="n", grain="x")
    box((-11, 2, 0), (11, 8, 11), WOOD, skip="nud", grain="y", faces={"s": WOOD_FRONT})
    box((-8, 3, 11), (8, 7, 11.5), WOOD_FRONT, skip="n", grain="x")
    box((-12, 8, 0), (12, 10, 12), WOOD, skip="n", grain="x")

    # the trunk: back board, two sides, the door's rails, its brass bead and its knob
    box((-7, 10, 0), (7, 38, 2), WOOD_DEEP, skip="nweud", grain="y")
    box((-9, 10, 0), (-7, 38, 9), WOOD, skip="nud", grain="y", faces={"s": WOOD_FRONT, "e": WOOD_DEEP})
    box((7, 10, 0), (9, 38, 9), WOOD, skip="nud", grain="y", faces={"s": WOOD_FRONT, "w": WOOD_DEEP})
    box((-7, 10, 8), (7, 12, 9), WOOD_FRONT, skip="nwed", grain="x")
    box((-7, 36, 8), (7, 38, 9), WOOD_FRONT, skip="nweu", grain="x")
    box((-7, 12, 8.25), (-6, 36, 9.25), BRASS_LINE)
    box((6, 12, 8.25), (7, 36, 9.25), BRASS_LINE)
    box((-6, 12, 8.25), (6, 13, 9.25), BRASS_LINE, skip="we")
    box((-6, 35, 8.25), (6, 36, 9.25), BRASS_LINE, skip="we")
    box((7, 23, 9), (9, 25, 9.75), BRASS, skip="n")
    glass = Sprite("clock_glass", _rows(12, 22, {"a": [(8, 7), (7, 8), (6, 9), (5, 10), (4, 11)],
                                                 "b": [(9, 10), (8, 11), (7, 12)]}),
                   {"a": P.RAMPS["night_glass"][4], "b": P.RAMPS["night_glass"][3]})
    box((-6, 13, 8.4), (6, 35, 8.5), WOOD, skip="nweud", faces={"s": glass})    # a few glints; the rest is clear

    # inside, from the bottom: the beat scale, the coils and their yoke, the movement
    scale = Sprite("clock_beat_scale", ["#.#.##.#.#", "....##...."], {"#": P.RAMPS["iron"][1]}, back=CREAM)
    box((-5, 13, 2), (5, 15, 2.5), CREAM, skip="n", faces={"s": scale})
    for x in (-4.5, 4.5):
        tube("y", (x, 4.0), 24, 28, 1.5, COPPER, sides=8)
    box((-6, 28, 2.5), (6, 29, 5.5), IRON_DARK, grain="x")
    box((-5, 30, 2), (5, 36, 3), BRASS_DARK, skip="n", grain="x")
    tube("z", (-1.5, 32.5), 3, 4, 2.5, BRASS_LIGHT, sides=12)
    tube("z", (2.5, 33.5), 3, 4.5, 1.5, BRASS_BRIGHT, sides=8)
    box((-2, 32, 4), (-1, 33, 4.5), IRON_DARK)
    box((2, 33, 4.5), (3, 34, 5), IRON_DARK)

    # the hood: neck, the panel the dial hangs on, the cornice
    box((-12, 38, 0), (12, 40, 12), WOOD, skip="n", grain="x")
    box((-11, 40, 0), (11, 62, 10.5), WOOD, skip="nud", grain="y", faces={"s": WOOD_FRONT})
    box((-12, 62, 0), (12, 64, 12), WOOD, skip="n", grain="x")
    return m


def _master_dial_model():
    """The master dial: the enamel plate and the brass bezel round it, 20 pixels over all."""
    m = M.Model(PREFIX + "master_dial", px=1.0)
    m.box((-9.0, -9.0, 0.0), (9.0, 9.0, 0.5), CREAM, skip="nweud", faces={"s": _master_dial()})
    m.ring("z", (0.0, 0.0, 0.75), 9.5, 1.0, 1.5, BRASS_LIGHT, sides=16)
    return m


def _master_hand(kind):
    """A hand of the master dial, pointing up from its anchor, the middle of the dial's back: as
    heavy for its dial as the tower's hands, so that the clock still reads from the front door."""
    m = M.Model(PREFIX + "master_hand_" + kind, px=1.0)
    if kind == "h":
        m.box((-1.5, -1.0, 0.75), (1.5, 4.0, 1.25), IRON_DARK, grain="y")
        m.box((-0.5, 4.0, 0.75), (0.5, 5.0, 1.25), IRON_DARK, skip="d")
    else:
        m.box((-1.0, -1.5, 1.5), (1.0, 6.5, 2.0), IRON_DARK, grain="y")
        m.box((-0.5, 6.5, 1.5), (0.5, 7.5, 2.0), IRON_DARK, skip="d")
        m.tube("z", (0.0, 0.0), 1.5, 2.5, 1.25, BRASS_LIGHT, sides=8)
    return m


def _pendulum():
    """The pendulum, hanging from its anchor: suspension block, steel rod, the iron armature that
    swings between the coils, the brass bob with its rating nut, the pointer over the beat scale."""
    m = M.Model(PREFIX + "pendulum", px=1.0)
    m.box((-1.5, -1.0, -1.0), (1.5, 1.0, 1.0), IRON_DARK)
    m.box((-1.0, -13.5, -0.5), (1.0, -1.0, 0.5), STEEL, grain="y")
    m.box((-1.5, -12.0, -1.0), (1.5, -10.0, 1.0), IRON_DARK)
    m.tube("z", (0.0, -17.0), -1.0, 0.75, 4.0, BRASS_LIGHT, sides=12)
    tones = {str(i): c for i, c in enumerate(P.RAMPS["brass"])}
    bob = Sprite("clock_bob", ["..4443..", ".455443.", "45544432", "45444332", "44443332", "34433322",
                               ".333222.", "..3221.."], tones)
    m.box((-4.0, -21.0, 0.9), (4.0, -13.0, 1.0), BRASS_LIGHT, skip="nweud", faces={"s": bob})
    m.box((-1.0, -22.5, -0.5), (1.0, -21.0, 0.5), BRASS_DARK)
    m.box((-0.5, -23.5, -0.5), (0.5, -22.5, 0.5), STEEL)
    return m


# --- the tower clock's models -------------------------------------------------------------------
def _face():
    """One tower dial, in model units of two pixels: the drum behind the back plane, the enamel
    plate (40 pixels), the brass rim in front of it (44 pixels over all: 2.75 blocks)."""
    m = M.Model(PREFIX + "face", px=2.0)
    m.tube("z", (0.0, 0.0), -DIAL_DRUM * 8.0, 0.0, 10.75, IRON_DARK, sides=24)
    m.box((-10.0, -10.0, 0.0), (10.0, 10.0, 0.5), CREAM, skip="nweud", faces={"s": _tower_dial()})
    m.ring("z", (0.0, 0.0, 0.75), 10.5, 1.0, 1.5, BRASS_LIGHT, sides=24)
    return m


def _hand(kind):
    """A tower hand, pointing up from its anchor (the dial's centre on the back plane), close to
    the enamel. Heavy, so that it is still a hand from the cable station: the hour hand is 13
    pixels long and 6 wide, the minute hand 19 and 5; each steps down to its tip and has a tail of
    3, short enough that the two never draw a cross. The minute hand carries the brass boss."""
    m = M.Model(PREFIX + "hand_" + kind, px=1.0)
    if kind == "h":
        m.tube("z", (0.0, 0.0), 1.5, 2.75, 3.5, IRON_DARK, sides=12)
        m.box((-3.0, -3.0, 1.5), (3.0, 9.0, 2.5), IRON_DARK, grain="y")
        m.box((-2.0, 9.0, 1.5), (2.0, 11.0, 2.5), IRON_DARK, skip="d", grain="y")
        m.box((-1.0, 11.0, 1.5), (1.0, 13.0, 2.5), IRON_DARK, skip="d", grain="y")
    else:
        m.box((-2.5, -3.0, 3.0), (2.5, 15.0, 4.0), IRON_DARK, grain="y")
        m.box((-1.5, 15.0, 3.0), (1.5, 17.0, 4.0), IRON_DARK, skip="d", grain="y")
        m.box((-0.5, 17.0, 3.0), (0.5, 19.0, 4.0), IRON_DARK, skip="d", grain="y")
        m.tube("z", (0.0, 0.0), 3.0, 5.0, 2.0, BRASS_LIGHT, sides=8)
    return m


# --- the time ball's models ---------------------------------------------------------------------
def _ball(name, tones):
    """The ball about its anchor: thin layers at the poles and thick ones at the waist, so that the
    outline steps like a drawn circle, painted in three flat tones from the underside to the crown;
    a seam of dark brass round the waist; an iron sleeve at each pole where the mast goes through;
    the catch plate tight under the ball, between it and the lower sleeve."""
    low, mid, high = tones
    m = M.Model(PREFIX + name, px=1.0)
    for t0, t1, layers, mat in ((-1.0, -0.8, 2, low), (-0.8, -0.4, 2, low), (-0.4, 0.4, 4, mid),
                                (0.4, 0.8, 2, high), (0.8, 1.0, 2, high)):
        m.ball((0.0, 0.0, 0.0), BALL_R, mat, sides=16, layers=layers, part=(t0, t1),
               faces={"n": mat, "s": mat, "u": mat, "d": mat})
    m.tube("y", (0.0, 0.0), -1.0, 1.0, BALL_R + 0.4, BRASS_DARK, sides=16)
    m.tube("y", (0.0, 0.0), BALL_R - 1.5, BALL_R + 2.5, 6.0, IRON_DARK, sides=12)
    m.tube("y", (0.0, 0.0), -BALL_R - 1.5, -BALL_R, BALL_PLATE, IRON_DARK, sides=16)
    m.tube("y", (0.0, 0.0), -BALL_FOOT, -BALL_R - 1.5, 6.0, IRON_DARK, sides=12)
    return m


# --- the model set ------------------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def _models():
    out = {}
    made = [(_master(), 2.0), (_master_dial_model(), 1.0), (_master_hand("h"), 1.0), (_master_hand("m"), 1.0),
            (_pendulum(), 1.0), (_face(), 2.0), (_hand("h"), 1.0), (_hand("m"), 1.0)]
    made += [(_ball(name, tones), 1.0) for name, tones in BALL_TONES.values()]
    for model, scale in made:
        out[model.name] = model
        SCALE[model.name] = scale
    return out


def models():
    return dict(_models())


def transformation(name, turn=0.0):
    """The "transformation" of the display entity that shows the piece `name` ("hand_m",
    "master_hand_h", "pendulum", ...) turned `turn` degrees about its model's z axis: positive is
    anticlockwise as the dial is looked at, so a hand at `a` degrees past twelve is turn = -a."""
    model = _models()[PREFIX + name]
    return M.display(model, scale=SCALE[model.name], turns=(("z", turn),))["transformation"]


# --- placing ------------------------------------------------------------------------------------
def _put(canvas, name, pos, origin, facing=None, tag=None, **opts):
    model = _models()[PREFIX + name]
    if facing is None:
        x, y, z = (pos[i] + origin[i] for i in range(3))
        canvas.add_entity(x, y, z, M.display(model, scale=SCALE[model.name], **opts))
    else:
        K.put(canvas, model, pos, mount="wall", facing=facing, scale=SCALE[model.name], origin=origin, **opts)
    if tag:
        canvas.entities[-1][3]["Tags"].append(tag)
    return 1


def _out(at, facing, pixels):
    """The point `pixels` (x across, y up, z out; from the anchor of a piece on a wall) in the scene."""
    d = K.turn(K.FACING[facing], tuple(v / 16.0 for v in pixels))
    return tuple(at[i] + d[i] for i in range(3))


def _solid(canvas, x, y, z):
    """Whether the cell holds something that is seen: a hidden light source is not a wall."""
    name = canvas.name(x, y, z)
    return name is not None and name.split(":")[-1] != B.LIGHT


def _lamp(canvas, origin):
    """Hand the clock's one light source to the sky line (sky/_lightkit.suggest places it with the
    rest). While that tool is not in the tree the block is put down here, never over another."""
    (x, y, z), level = MASTER_LAMP
    cell = (x + int(origin[0]), y + int(origin[1]), z + int(origin[2]))
    try:
        from ..sky import _lightkit
        suggest = getattr(_lightkit, "suggest", None)
    except ImportError:
        suggest = None
    if suggest is not None:
        suggest(canvas, cell, level, "machines/clock:master", rank=3)
    else:
        canvas.set(cell[0], cell[1], cell[2], f"{B.LIGHT}[level={level}]", keep=True)


def master(canvas, origin=(0, 0, 0), time=None):
    """The master clock on the pier: case, dial, two hands and pendulum; returns the entity count."""
    hour, minute = hand_angles(*(time or TIME))
    face = MASTER_FACING
    n = _put(canvas, "master", _out(MASTER_AT, face, (0.0, MASTER_HOLD, 0.0)), origin, face)
    n += _put(canvas, "pendulum", _out(MASTER_AT, face, MASTER_PIVOT), origin, face, tag=TAG_PENDULUM,
              turns=(("z", PENDULUM_POSE),))
    centre = _out(MASTER_AT, face, MASTER_DIAL)
    lit = dict(brightness=MASTER_DIAL_LIGHT)
    n += _put(canvas, "master_dial", centre, origin, face, **lit)
    n += _put(canvas, "master_hand_h", centre, origin, face, tag=TAG_HOUR, turns=(("z", -hour),), **lit)
    n += _put(canvas, "master_hand_m", centre, origin, face, tag=TAG_MINUTE, turns=(("z", -minute),), **lit)
    _lamp(canvas, origin)
    return n


def _surface(canvas, facing, across, origin):
    """The outer face (its coordinate along the facing's axis) of the first block met going into
    the shaft through the cell `across` of the dial's row, or None when the way is open."""
    (dx, dz), _wall = _WALLS[facing]
    s = dx + dz
    lo, hi = S.CLOCK_SHAFT_X if dx else S.CLOCK_SHAFT_Z
    first = (hi if s > 0 else lo) + s
    y = int(math.floor(DIAL_Y))
    ox, oy, oz = (int(v) for v in origin)
    for k in range(_SCAN):
        c = first - s * k
        x, z = (c, across) if dx else (across, c)
        if _solid(canvas, x + ox, y + oy, z + oz):
            return float(c + 1 if s > 0 else c)
    return None


def dial_centre(canvas, facing, origin=(0, 0, 0)):
    """Where the dial of one face goes: the centre of its back plane, in the package's own
    coordinates (the origin is not added). `back` is the wall straight behind the dial, `mouth` the
    wall two cells to either side of it: the dial sits DIAL_INSET inside the mouth, but never
    behind the back. With no tower on the canvas it hangs where the skeleton has the wall."""
    (dx, dz), wall = _WALLS[facing]
    s = dx + dz
    axis = S.mid(*(S.CLOCK_SHAFT_Z if dx else S.CLOCK_SHAFT_X))
    mid = int(math.floor(axis))
    back = _surface(canvas, facing, mid, origin)
    sides = [p for p in (_surface(canvas, facing, mid + d, origin) for d in (-2, 2)) if p is not None]
    if back is None and not sides:
        plane = wall
    else:
        mouth = s * max(s * p for p in sides) if sides else back
        seat = mouth - s * DIAL_INSET
        plane = seat if back is None else s * max(s * back, s * seat)
    return (plane, DIAL_Y, axis) if dx else (axis, DIAL_Y, plane)


def mast_stands(canvas, origin=(0, 0, 0)):
    """Whether main/tower's mast is on the canvas: something on the axis where the ball hangs."""
    x, z = (int(math.floor(v)) for v in BALL_AXIS)
    ox, oy, oz = (int(v) for v in origin)
    return any(_solid(canvas, x + ox, y + oy, z + oz)
               for y in range(int(math.floor(MAST_FOOT_Y)) + 1, int(math.floor(BALL_UP_Y)) + 1))


def ball(canvas, pos, colour=None, origin=(0, 0, 0)):
    """One time ball with its centre at pos; colour is "copper" or "red" (BALL when left out)."""
    name, _tones = BALL_TONES[colour or BALL]
    return _put(canvas, name, pos, origin, tag=TAG_BALL, brightness=BALL_LIGHT, view=FAR)


def tower(canvas, origin=(0, 0, 0), time=None, sides=SIDES, colour=None):
    """The four dials of the tower with their hands, and the time ball; returns the entity count."""
    hour, minute = hand_angles(*(time or TIME))
    n = 0
    for facing in sides:
        pos = dial_centre(canvas, facing, origin)
        lit = dict(brightness=DIAL_LIGHT[facing], view=FAR)
        n += _put(canvas, "face", pos, origin, facing, **lit)
        n += _put(canvas, "hand_h", pos, origin, facing, tag=TAG_HOUR, turns=(("z", -hour),), **lit)
        n += _put(canvas, "hand_m", pos, origin, facing, tag=TAG_MINUTE, turns=(("z", -minute),), **lit)
    y = BALL_HALF_Y if mast_stands(canvas, origin) else BALL_REST_Y
    n += ball(canvas, (BALL_AXIS[0], y, BALL_AXIS[1]), colour, origin)
    return n


def build(canvas, origin=(0, 0, 0)):
    """The whole set at its places in the skeleton; returns the number of display entities."""
    return master(canvas, origin) + tower(canvas, origin)
