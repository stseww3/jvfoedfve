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
a fixed light (MASTER_DIAL_LIGHT), the top of the light table and well above what the case gets:
it is the white spot of the clock and of the hall. Looking in from the court along the axis (V7),
the dial and the east face of the pier are what is seen first, the orrery's sun is the warmest
point and the floor comes third (A0, 11-16). Case and pendulum take the light of the cell they
stand in, at the height of the trunk's top. The light source that goes with the clock is one
hidden light in front of the trunk (MASTER_LAMP), handed to sky/_lightkit, which places it. It is
a strong one, of the second rank: what is lit at the far end of the hall is the master clock on
its pier, with no lamp to be seen (A0, 11-15).

The tower clock (time tower). Four equal dials, one in the middle of each face of the shaft, centre
at y 27.5, 2.75 blocks across: white enamel, a thin brass rim, a mark at every hour (no numerals:
at 44 pixels they do not fit) and two heavy dark hands. Nothing glows and no light source goes with
it (A0, 11-14: a dial may not be brighter than the frosted windows of the front). The white of the
dial at night is the fixed light its entities are given (DIAL_LIGHT: the light of the sky, which
the wall round it has as well, and block light on top of it until the blue is out of the enamel;
set for each facing so that the four dials are alike). main/tower leaves a dark recess, three
blocks wide, for each dial. tower() reads the canvas: the dial sits DIAL_INSET inside the mouth of
the recess as it is built, never behind its back, and on a flush wall it is fixed to the surface.
The dial is smaller than the recess, so a dark ring stays round it. A drum behind the dial carries
it from the back of the recess; in a flush wall the drum is buried and not seen.

The time ball. A ball 2.5 blocks across, threaded on the mast of the tower (the mast, a display
model 7 pixels thick, and the cups and the vane above y 51 are main/tower's), with an iron sleeve
at each pole and under the lower pole the collar it is caught by: half as wide as the ball and as
thick as it is proud, a step in the foot of the ball and never a bar across the mast (a cross is a
red line). Nothing runs round the waist. The ball is turned about the mast (BALL_TURN) so that
the game's two lamps light its four sides alike, and its roundness is painted on it: five tones
round the place the moon lights it from, low in the east. It is of old copper (BALL): A0 chose it
on the V1 pictures (11-16), where it stands out of the sky by its lightness and is of one family
with the verdigris roof under it, and the one red thing in that sky stays the lamp of the radio
mast. The dark red ball is kept as a switch (tower(colour="red"), scene obs_mach_clocks_b). Where
no mast stands yet (the white model) the ball lies at the foot of the mast.

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
same. The pose placed here is where a loop starts: the pendulum hangs plumb.
  the pendulum   is registered with the motion line where it is placed (master(), one line:
        MK.swing(canvas, "z", PENDULUM_SWING, MK.PENDULUM); plan/parts/motion.md 4). It swings about
        the model's z axis through its anchor, PENDULUM_SWING degrees each way, there and back in
        two seconds; motion/_kit tags it (m.mach_clock_pendulum) and writes the functions.
        transformation("pendulum", degrees) is the same pose, for whoever wants one by hand.
The pieces that stand still in this version keep a tag of their own, for the day they move:
  c164_clock_hand_h, c164_clock_hand_m   all five hour hands and all five minute hands. A hand
        turns about the model's z axis through its anchor, clockwise as the dial is looked at:
        transformation(name, -degrees) with degrees from hand_angles(hour, minute).
  c164_clock_ball       slides along the mast, y only: BALL_HALF_Y (the pose now), BALL_UP_Y at
        the top of the mast, BALL_REST_Y after the drop. It keeps its turn about the mast:
        transformation("ball") has it.
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
TIME = tuple(S.CLOCK)

TAG_HOUR, TAG_MINUTE = "c164_clock_hand_h", "c164_clock_hand_m"
TAG_BALL = "c164_clock_ball"

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
# (sky, block) for the dial and its hands. A0, 11-16: in V7 the dial comes first and reads 0.35 or
# more. A face that looks east is drawn at half the light it is given, so the white enamel read
# 0.32 at (0, 11) and would read 0.40 at 13, the whole dial with its marks and hands a sixth less.
# 14 is the top of the light table, white light: the enamel reads 0.46 and its warmth is its own.
# The lamp in front of the trunk stays at 11. scenes/obs_mach_clocks/measure.py reads the dial.
MASTER_DIAL_LIGHT = (0, 14)
# the hidden light in front of the trunk: the cell, the level and the rank (A0, 11-15: (7, 3, 0), 11,
# second rank; the case, in the cell behind it, gets 10)
MASTER_LAMP = ((int(MASTER_AT[0]) + 1, int(MASTER_AT[1]) + 2, int(math.floor(MASTER_AT[2]))), 11)
MASTER_LAMP_RANK = 2
# The case is solid to the eye and a model stops nobody: who jumped on the stone under it stood in
# the trunk. Barriers fill the cell the case stands in, as high as a walker is (INTERFACE, the fifth
# supplement of 11-16: inside a solid model, not a cell outside its outline, never more than two
# high). The cell is the middle block of the stone: to the east its face is the stone's own, which
# stops a walker in that plane already; to the north and the south the case's foot is four pixels
# wider than the cell, as far as a model may stand out from what stops the eye (props/ironwork: EYE
# - NEAR). The case and the pendulum are lit by the cell over the two.
MASTER_SOLID = 2
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
# (sky, block) for the dial and its hands. The east and west faces of a display entity are drawn at
# 0.50 of the light it is given, the north and south faces at 0.74, and block light alone is orange:
# at (0, 11) the enamel came out tan (#634f3d on the pictures of 11-16), a lit parchment and not a
# white dial. The dial takes the sky's light as the wall round it does and block light on top until
# the blue is gone: (15, 9) on an east face and (8, 6) on a south face are the same warm white
# (#645858, 0.36 of full white) to within a hundredth, between the stone of the wall (0.22) and
# the lit frosted window (0.54). scenes/obs_mach_clocks/measure.py reads all of it off the pictures.
DIAL_LIGHT = {"east": (15, 9), "west": (15, 9), "south": (8, 6), "north": (8, 6)}
FAR = 4.0                        # view_range of everything on the tower: seen from the far platforms

# --- the time ball ------------------------------------------------------------------------------
BALL = "copper"                  # the colour tower() hangs (A0, 11-16); "red" is the other one made
BALL_AXIS = (S.mid(*S.CLOCK_SHAFT_X), S.mid(*S.CLOCK_SHAFT_Z))     # (13.5, -29.5): the mast
MAST_MODEL = "bld_tower_mast"    # the model main/tower's mast is shown with: a rod 7 pixels thick, y 42.6..51
BALL_R = 20.0                    # pixels: 2.5 blocks across (A0, 11-14)
BALL_SIDES = 16
# One half of the ball from the waist to the pole, in pixels above the centre: the layers it is
# stacked of, thick at the waist and thin towards the pole, so that the outline steps by one or two
# pixels like a circle drawn by hand. The last pixel of the pole is inside the sleeve.
BALL_LAYERS = (0.0, 4.0, 8.0, 11.0, 13.0, 15.0, 17.0, 19.0)
BALL_SLEEVE = 6.0                # the radius of the iron sleeve at each pole (the mast's is 3.5)
BALL_PLATE = 10.0                # the collar under the lower pole: half the ball's radius (cr2: under eight tenths)
BALL_FOOT = BALL_R + 3.5         # from the ball's centre down to the foot of its lower sleeve
# The game lights a display entity from two lamps fixed in the world and takes every face for the
# nearest axis of its model: sides that look east or west are drawn at 0.50, north or south at
# 0.74. On a round thing that is a hard line from pole to pole, and with anything round the waist
# a cross (the pictures of 11-16). Turned by this angle about the mast, the four sides of the
# model look where both lamps light them alike (0.65 each) and the line is gone.
BALL_TURN = math.degrees(math.atan2(0.7, 0.2)) - 45.0      # 29.05
# The roundness is painted instead. Where the light comes from, in the scene (east, up, south): the
# moon, low in the east at this hour, a little to the south so that from the cable station (V1 looks
# west) the light side is the upper left. BALL_SKY is what the sky adds from above. A face takes
# its tone from the cosine between the ball's surface there and the light: BALL_ZONES are the four
# values at which one tone ends and the next begins, from the far side to the highlight.
BALL_MOON = (0.80, 0.42, 0.42)
BALL_SKY = 0.12
BALL_ZONES = (-0.15, 0.25, 0.60, 0.92)
MAST_FOOT_Y = S.CLOCK_TOP + 1.0                      # 42.0: the tip of the roof, where the mast starts
BALL_HALF_Y = S.CLOCK_BALL_MAST - 4.5                # 47.5: half-way up, five minutes before the hour
BALL_UP_Y = S.CLOCK_BALL_MAST - 2.75                 # 49.25: at the top, 1.5 blocks of mast above it
BALL_REST_Y = MAST_FOOT_Y + BALL_FOOT / 16.0         # 43.46875: dropped, on the foot of the mast
# (sky, block): block light only, which is warm, so that copper stays copper and red stays red
# against the blue of the sky. cr2: the ball is to stand lighter than the sky behind it.
BALL_LIGHT = (0, 12)

# --- materials (palette only) -------------------------------------------------------------------
WOOD = P.mat("dark_wood")
# the panels that face the room are one step lighter: a face that looks east is drawn at half light
WOOD_FRONT = P.mat("dark_wood", base=3)
WOOD_DEEP = P.mat("dark_wood", base=1)       # the inside of the trunk
BRASS = P.mat("brass")
BRASS_DARK = P.mat("brass_dark")
# rims and bosses that look at the viewer: Model.ring and Model.tube paint such a face one step down
BRASS_LIGHT = P.mat("brass", base=4)
BRASS_LINE = K.flat("brass", 3)              # a line one pixel wide: one tone, or it breaks into dashes
# the rim of the movement's great wheel, piece by piece: flat tones, the second a step under the first
WHEEL_TEETH = 12
BRASS_TOOTH = (K.flat("brass", 5), K.flat("brass", 4))
IRON_DARK = P.mat("iron_dark")
STEEL = P.mat("iron", base=5)
COPPER = P.mat("old_copper")
CREAM = P.mat("cream")

# the iron of the ball's sleeves and collar, and of their undersides: a face that looks down is
# drawn at four tenths of the light, and the dark iron went dead black there (cr3, 11-16)
BALL_IRON = P.mat("iron", base=4)
BALL_IRON_UNDER = K.flat("iron", 5)

INK = P.colour("iron", 1)
# the hands of the small dial: blued steel in one tone, two steps lighter than the ink of the marks,
# so that the tip of the minute hand and the mark it points at stay two things (cr3, 11-16)
HAND_FLAT = K.flat("iron", 3)
ENAMEL = [P.colour("cream", i) for i in range(len(P.RAMPS["cream"]))]      # dark to light
# The paint of the ball: the model's name, the ramp and its steps for the five zones from the far
# side to the highlight. The middle zone is the paint as it is (the step its material starts
# from), shade below it and light above. Dark red stays in the three dark steps of its ramp: the
# fourth is the pink of a lamp.
BALL_TONES = {
    "copper": ("ball", ("old_copper", (0, 1, 2, 3, 4))),
    "red": ("ball_red", ("signal", (0, 0, 1, 2, 2))),
}
# What the game draws the faces of the turned ball at: its sides, and the ledges between the layers
# that look up and down. A ledge is painted in the step that comes out nearest to the side next to it.
BALL_SIDE_SHADE = 0.65
BALL_LEDGE_SHADE = {"u": 1.0, "d": 0.4}
# The ledges that look down are most of what the ball shows to the ground, and at four tenths no
# step of the ramp is light enough for them beside a light side: they lay round the lower half as
# dark hoops (the pictures of 11-16). They are elements of their own that take the top of the light
# table (BALL_UNDER_EMIT), which at the map's hour is BALL_UNDER_GAIN times what BALL_LIGHT gives,
# and they are painted for that.
# The table is at its top from 14 on (white at 14 as at 15), and 14 it has to be. The map's item
# shader (sky/_shaders.py, core/item.vsh) takes a face at block light 15 for a thing that glows of
# itself and does not shade it by the way it looks: at 15 the ledges were drawn at the whole of
# that light and not at four tenths of it, hoops of 0.61 to 0.68 round a ball of 0.23, lighter
# than the lit window under the dial (the saves A5 and A6 and the board of 11:00, in the real
# client; the offline pictures shade every face and never showed it).
BALL_UNDER_EMIT = 14
BALL_UNDER_GAIN = 1.28
# what a piece is turned by where it stands, before any turn of its own
_STANDING = {name: (("y", BALL_TURN),) for name, _paint in BALL_TONES.values()}

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


def _marks(px, quarter, other=None):
    """Hour marks in ink. quarter and other are (from, to, half width) in pixels, measured out from
    the centre and across the mark: the marks at twelve, three, six and nine, and the rest (left
    out without `other`)."""
    size = px.shape[0]
    c = size / 2.0
    for hour in range(12):
        if hour % 3 and other is None:
            continue
        s, k = math.sin(math.radians(30.0 * hour)), math.cos(math.radians(30.0 * hour))
        lo, hi, half = other if hour % 3 else quarter
        for j in range(size):
            for i in range(size):
                x, y = i + 0.5 - c, c - (j + 0.5)
                if lo - 1e-6 <= x * s + y * k <= hi + 1e-6 and abs(x * k - y * s) < half + 1e-6:
                    px[j, i, :3] = INK
                    px[j, i, 3] = 255


# The eight marks between the quarters of the tower dial are placed by hand: a square of two
# pixels a side against the inside of the minute track. Turned by 30 and 60 degrees and put on
# the grid, such a square came out a small plus lying on the track (cr3, 11-16). TOWER_MARK is the
# lower left pixel of the one at one o'clock, counted from the centre in whole pixels (to the right,
# upwards): it hangs from the track by its upper right pixel, 29.7 degrees past twelve. The mark at
# two o'clock is its mirror in the diagonal, the other six are these two in the other quadrants.
TOWER_MARK = (7, 13)


def _squares(px, corner):
    """A square of two pixels a side with its lower left pixel at `corner`, its mirror in the
    diagonal, and both again in each of the other three quadrants."""
    c = px.shape[0] // 2
    for a in (0, 1):
        for b in (0, 1):
            for right, up in ((corner[0] + a, corner[1] + b), (corner[1] + b, corner[0] + a)):
                for i in (c + right, c - 1 - right):
                    for j in (c - 1 - up, c + up):
                        px[j, i, :3] = INK
                        px[j, i, 3] = 255


def _tower_dial():
    """The tower dial, 40 pixels across inside its rim. From the rim in: a line all round (the
    minute track), a bar of two pixels by four hanging from it at each quarter and a square of two
    by two at each of the other hours. The disc is drawn a little under the rim so that no gap
    shows at the corners of the many-sided ring."""
    size, c = 40, 20.0
    px = _disc(size, 20.7, 18.6)
    for j in range(size):
        for i in range(size):
            if 17.5 < math.hypot(i + 0.5 - c, c - (j + 0.5)) <= 18.5:
                px[j, i, :3] = INK
    _marks(px, (13.5, 17.5, 1.0))
    _squares(px, TOWER_MARK)
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
    # A line of brass round the head of the skirting and round the foot of the cap. From the door
    # the plinth stands in front of the slate at the pier's foot, which is as dark as its wood:
    # the two lines are what draws it there (cr3, 11-16). A line is three strips a quarter of a
    # pixel proud of the wood, closed above and below: the eye of someone standing looks down on them.
    for y in (1, 8):
        box((-12.25, y, 12), (12.25, y + 1, 12.25), BRASS_LINE, skip="n")
        box((-12.25, y, 0), (-12, y + 1, 12), BRASS_LINE, skip="nse")
        box((12, y, 0), (12.25, y + 1, 12), BRASS_LINE, skip="nsw")

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
    # The glass of the door is clear and nothing is drawn for it. A glint has to be lighter than what
    # it lies on: it read as dirt on the brass of the movement, and as a stain on the beat scale when
    # it was moved to the corner over the dark back board (cr3, 11-16, twice).

    # inside, from the bottom: the beat scale, the coils and their yoke, the movement
    scale = Sprite("clock_beat_scale", ["#.#.##.#.#", "....##...."], {"#": P.RAMPS["iron"][1]}, back=CREAM)
    box((-5, 13, 2), (5, 15, 2.5), CREAM, skip="n", faces={"s": scale})
    # a coil is wound wire: rings of two tones between two iron cheeks (the upper cheek is the yoke)
    wire = Sprite("clock_coil", ["aa", "bb", "aa", "bb"], {"a": P.RAMPS["old_copper"][3], "b": P.RAMPS["old_copper"][1]},
                  back=COPPER)
    # They stand clear of everything that swings (PENDULUM_SWING to either side): the bob passes
    # under the lower cheeks, the armature between the coils, the rod in front of the yoke.
    for x in (-4.5, 4.5):
        tube("y", (x, 4.0), 25, 29, 2.0, wire, sides=8, cap=K.flat("iron", 1))
        tube("y", (x, 4.0), 24, 25, 2.5, IRON_DARK, sides=8)
    box((-6.5, 29, 1.5), (6.5, 30, 5.5), IRON_DARK, grain="x")
    box((-5, 30, 2), (5, 36, 3), BRASS_DARK, skip="n", grain="x")
    # the great wheel: a light rim round a darker web, the arbor in the middle; the small wheel beside it.
    # The rim is its teeth: twelve pieces, light and a step darker by turns. No spokes: the wheel is
    # six pixels across (cr3, 11-16).
    tube("z", (-1.5, 33.0), 3, 3.5, 2.0, BRASS, sides=12)
    for k in range(WHEEL_TEETH):
        m.ring("z", (-0.75, 16.5, 1.875), 1.25, 0.5, 0.75, BRASS_TOOTH[k % 2], sides=WHEEL_TEETH,
               arc=(360.0 * k / WHEEL_TEETH, 360.0 * (k + 1) / WHEEL_TEETH))
    tube("z", (2.5, 33.5), 3, 4.5, 1.5, BRASS_LIGHT, sides=8)
    box((-2, 32.5, 3.5), (-1, 33.5, 4.5), IRON_DARK)
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
        # a spear: three wide at the boss, two, and a point of one
        m.box((-1.5, -1.0, 0.75), (1.5, 2.5, 1.25), HAND_FLAT)
        m.box((-1.0, 2.5, 0.75), (1.0, 4.0, 1.25), HAND_FLAT, skip="d")
        m.box((-0.5, 4.0, 0.75), (0.5, 5.5, 1.25), HAND_FLAT, skip="d")
    else:
        # two wide as far as the hour hand reaches, one from there to the marks
        m.box((-1.0, -1.5, 1.5), (1.0, 4.5, 2.0), HAND_FLAT)
        m.box((-0.5, 4.5, 1.5), (0.5, 7.5, 2.0), HAND_FLAT, skip="d")
        m.tube("z", (0.0, 0.0), 1.5, 2.5, 1.25, BRASS_LIGHT, sides=8)
    return m


def _pendulum():
    """The pendulum, hanging from its anchor: suspension block, steel rod, the iron armature that
    swings between the coils, the brass bob with its rating nut, the pointer over the beat scale."""
    m = M.Model(PREFIX + "pendulum", px=1.0)
    m.box((-1.5, -1.0, -1.0), (1.5, 1.0, 1.0), IRON_DARK)
    m.box((-1.0, -13.5, -0.5), (1.0, -1.0, 0.5), STEEL, grain="y")
    m.box((-1.5, -11.0, -1.0), (1.5, -9.0, 1.0), IRON_DARK)
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
def _ball_zone(normal):
    """Which of the five tones the ball has where its surface looks along `normal` (in the scene)."""
    size = math.sqrt(sum(v * v for v in BALL_MOON))
    light = sum(n * v for n, v in zip(normal, BALL_MOON)) / size + BALL_SKY * normal[1]
    return sum(1 for edge in BALL_ZONES if light >= edge)


def _ball_tone(zone, column, row):
    """The zone a pixel of the ball is painted in. zone(dx, dy) is the zone of the place dx pixels
    to the right of it and dy pixels up. Where two tones meet, the first row of the lighter one
    takes the darker tone on every other pixel, so that they part in a row of checks: a hard line
    between two tones reads as a stripe from close by (cr3, 11-16). The checks are counted along
    the line: by the column where the darker tone lies above or below, else by the row."""
    here = zone(0, 0)
    if zone(0, 1) < here or zone(0, -1) < here:
        return here - 1 if column % 2 else here
    if zone(1, 0) < here or zone(-1, 0) < here:
        return here - 1 if row % 2 else here
    return here


def _ball_side(label, colours, r, y0, y1, turn, back):
    """One side of a layer, painted pixel by pixel: each pixel takes the tone of the place on the
    ball it covers, so the tones meet along curves a pixel fine and not along the edges of the
    sides. The side is r from the axis, y0..y1 high, on the box turned `turn` degrees about the
    mast; `back` is its far side (the box's north face), which is seen from the other way."""
    width = 2.0 * r * math.tan(math.pi / BALL_SIDES)
    w, h = max(1, int(round(width))), max(1, int(round(y1 - y0)))
    # the columns are counted on round the layer, so that the checks keep step from side to side
    first = (int(turn / 360.0 * BALL_SIDES) + (BALL_SIDES // 2 if back else 0)) * w
    px = np.zeros((h, w, 4), dtype=np.uint8)

    def zone(i, j):
        y = y1 - (j + 0.5) * (y1 - y0) / h
        up = max(-1.0, min(1.0, y / BALL_R))
        flat = math.sqrt(1.0 - up * up)
        across = ((i + 0.5) / w - 0.5) * width
        x, z = (-across, -r) if back else (across, r)
        at = math.atan2(x, z) + math.radians(turn + BALL_TURN)
        return _ball_zone((flat * math.sin(at), up, flat * math.cos(at)))

    for j in range(h):
        for i in range(w):
            px[j, i, :3] = colours[_ball_tone(lambda dx, dy: zone(i + dx, j - dy), first + i, int(y1) - j)]
            px[j, i, 3] = 255
    return _Picture(label, px)


def _luma(colour):
    return (0.299 * colour[0] + 0.587 * colour[1] + 0.114 * colour[2]) / 255.0


def _ball_ledge(label, colours, r, y, turn, letter):
    """The ledge of a layer, r from the axis at the height y, looking up ("u") or down ("d"): each
    pixel in the tone of the ball's side at that place (colours are the ledge's own, by zone). The
    picture lies as the game lays it on such a face: its top row at the north end of an upward
    face and at the south end of a downward one."""
    width = 2.0 * r * math.tan(math.pi / BALL_SIDES)
    w, h = max(1, int(round(width))), max(1, int(round(2.0 * r)))
    up = max(-1.0, min(1.0, y / BALL_R))
    flat = math.sqrt(1.0 - up * up)
    px = np.zeros((h, w, 4), dtype=np.uint8)

    def zone(i, j):
        z = ((j + 0.5) / h - 0.5) * 2.0 * r * (1.0 if letter == "u" else -1.0)
        x = ((i + 0.5) / w - 0.5) * width
        at = math.atan2(x, z) + math.radians(turn + BALL_TURN)
        return _ball_zone((flat * math.sin(at), up, flat * math.cos(at)))

    for j in range(h):
        for i in range(w):
            px[j, i, :3] = colours[_ball_tone(lambda dx, dy: zone(i + dx, j - dy), i, j)]
            px[j, i, 3] = 255
    return _Picture(label, px)


def _ball(name, paint):
    """The ball about its anchor. Each layer is a prism of BALL_SIDES sides, half a side off the
    model's axes so that no side is in doubt about the axis it is lit by. Sides and ledges are
    painted for where the ball looks once the entity is turned BALL_TURN: the tones run round the
    light in rings and cut across the layers, which is what makes a ball of a stack. An iron sleeve
    at each pole where the mast goes through and the collar under the lower one, their undersides
    a light iron: the ball is looked at from below."""
    ramp, zones = paint
    tones = [P.colour(ramp, step) for step in range(max(zones) + 1)]
    colours = [tones[step] for step in zones]
    drawn = {"u": BALL_LEDGE_SHADE["u"], "d": BALL_LEDGE_SHADE["d"] * BALL_UNDER_GAIN}
    ledges = {letter: [min(tones, key=lambda c: abs(_luma(c) * shade - _luma(side) * BALL_SIDE_SHADE)) for side in colours]
              for letter, shade in drawn.items()}
    m = M.Model(PREFIX + name, px=1.0)
    half = math.tan(math.pi / BALL_SIDES)
    for sign in (1.0, -1.0):
        ledge = "u" if sign > 0 else "d"
        for layer, (a0, a1) in enumerate(zip(BALL_LAYERS, BALL_LAYERS[1:])):
            y0, y1 = min(sign * a0, sign * a1), max(sign * a0, sign * a1)
            mid = (y0 + y1) / 2.0
            r = math.sqrt(BALL_R * BALL_R - mid * mid)
            for side in range(BALL_SIDES // 2):
                turn = 360.0 * (side + 0.5) / BALL_SIDES
                label = f"clock_{name}_{ledge}{layer}_{side}"
                face = {ledge: _ball_ledge(label, ledges[ledge], r, sign * a1, turn, ledge)}
                sides = {"s": _ball_side(label + "s", colours, r, y0, y1, turn, False),
                         "n": _ball_side(label + "n", colours, r, y0, y1, turn, True)}
                box = dict(rot=("y", turn, (0.0, 0.0, 0.0)), seed=1)
                lo, hi, paint = (-r * half, y0, -r), (r * half, y1, r), K.flat(ramp, zones[2])
                if sign > 0:
                    m.box(lo, hi, paint, skip="ewd", faces={**face, **sides}, **box)
                else:
                    m.box(lo, hi, paint, skip="ewud", faces=sides, **box)
                    m.box(lo, hi, paint, skip="ewsnu", faces=face, emit=BALL_UNDER_EMIT, **box)
    top = BALL_LAYERS[-1]
    m.tube("y", (0.0, 0.0), top - 0.5, BALL_R + 2.5, BALL_SLEEVE, BALL_IRON, sides=12)
    m.tube("y", (0.0, 0.0), -top - 2.0, -top, BALL_PLATE, BALL_IRON, sides=16, cap=BALL_IRON_UNDER)
    m.tube("y", (0.0, 0.0), -BALL_FOOT, -top - 2.0, BALL_SLEEVE, BALL_IRON, sides=12, cap=BALL_IRON_UNDER)
    return m


# --- the model set ------------------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def _models():
    out = {}
    made = [(_master(), 2.0), (_master_dial_model(), 1.0), (_master_hand("h"), 1.0), (_master_hand("m"), 1.0),
            (_pendulum(), 1.0), (_face(), 2.0), (_hand("h"), 1.0), (_hand("m"), 1.0)]
    made += [(_ball(name, paint), 1.0) for name, paint in BALL_TONES.values()]
    # The tubes and rings of eight, sixteen and twenty-four sides (weights, arbors, bezels, the drum
    # behind a dial, the plate under the ball) have flats exactly between two axes, and the game lights
    # such a flat as the one or the other by the last bit of a float: K.settle turns each such piece a
    # tenth of a degree, so that every copy of the game and the offline pictures light it one way. The
    # ball's own facets stand 11.25 degrees off the fence and are not touched.
    for model, scale in made:
        out[model.name] = K.settle(model)
        SCALE[model.name] = scale
    return out


def models():
    return dict(_models())


def transformation(name, turn=0.0):
    """The "transformation" of the display entity that shows the piece `name` ("hand_m",
    "master_hand_h", "pendulum", ...) turned `turn` degrees about its model's z axis: positive is
    anticlockwise as the dial is looked at, so a hand at `a` degrees past twelve is turn = -a."""
    model = _models()[PREFIX + name]
    turns = _STANDING.get(name, ()) + (("z", turn),)
    return M.display(model, scale=SCALE[model.name], turns=turns)["transformation"]


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
        suggest(canvas, cell, level, "machines/clock:master", rank=MASTER_LAMP_RANK)
    else:
        canvas.set(cell[0], cell[1], cell[2], f"{B.LIGHT}[level={level}]", keep=True)


def _collide(canvas, origin):
    """The case's collision (MASTER_SOLID): barriers in the cell it stands in, never over a block."""
    x, y, z = int(MASTER_AT[0]), int(MASTER_AT[1]), int(math.floor(MASTER_AT[2]))
    for k in range(MASTER_SOLID):
        canvas.set(x + int(origin[0]), y + k + int(origin[1]), z + int(origin[2]), B.BARRIER, keep=True)


def _swing(canvas):
    """Register the pendulum, the piece placed last, with the motion line (plan/parts/motion.md 4):
    it swings about its model's z axis through its anchor, the pivot, PENDULUM_SWING degrees to
    either side of where it hangs, there and back in the beat of every pendulum on the hill. The
    loop's functions are motion/_kit's to write; while that is not in the tree the pendulum hangs
    still, as it does in every offline picture."""
    try:
        from ..motion import _kit as MK
    except ImportError:
        return
    MK.swing(canvas, "z", PENDULUM_SWING, MK.PENDULUM)


def master(canvas, origin=(0, 0, 0), time=None):
    """The master clock on the pier: case, dial, two hands and pendulum, the case's collision and
    its lamp; returns the entity count."""
    hour, minute = hand_angles(*(time or TIME))
    face = MASTER_FACING
    n = _put(canvas, "master", _out(MASTER_AT, face, (0.0, MASTER_HOLD, 0.0)), origin, face)
    n += _put(canvas, "pendulum", _out(MASTER_AT, face, MASTER_PIVOT), origin, face,
              turns=(("z", PENDULUM_POSE),))
    _swing(canvas)
    centre = _out(MASTER_AT, face, MASTER_DIAL)
    lit = dict(brightness=MASTER_DIAL_LIGHT)
    n += _put(canvas, "master_dial", centre, origin, face, **lit)
    n += _put(canvas, "master_hand_h", centre, origin, face, tag=TAG_HOUR, turns=(("z", -hour),), **lit)
    n += _put(canvas, "master_hand_m", centre, origin, face, tag=TAG_MINUTE, turns=(("z", -minute),), **lit)
    _collide(canvas, origin)
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


def _shown(nbt):
    """The name of the model a display entity shows, without its namespace ("" for anything else)."""
    ref = ((nbt.get("item") or {}).get("components") or {}).get("minecraft:item_model") or ""
    return ref.rpartition(":")[2]


def mast_stands(canvas, origin=(0, 0, 0)):
    """Whether the mast of the tower is on the canvas. main/tower's mast is a display model and
    leaves no block on the axis (c223, 11-15): it is known by the model its entity shows,
    tower.MAST_MODEL (MAST_MODEL while main/tower is not in the tree). A stand-in mast of blocks on
    the axis where the ball hangs counts as well."""
    try:
        from ..main import tower
        name = getattr(tower, "MAST_MODEL", MAST_MODEL)
    except ImportError:
        name = MAST_MODEL
    name = str(getattr(name, "name", name)).rpartition(":")[2]
    if any(_shown(e[3]) == name for e in canvas.entities):
        return True
    x, z = (int(math.floor(v)) for v in BALL_AXIS)
    ox, oy, oz = (int(v) for v in origin)
    return any(_solid(canvas, x + ox, y + oy, z + oz)
               for y in range(int(math.floor(MAST_FOOT_Y)) + 1, int(math.floor(BALL_UP_Y)) + 1))


def ball(canvas, pos, colour=None, origin=(0, 0, 0)):
    """One time ball with its centre at pos; colour is "copper" or "red" (BALL when left out)."""
    name, _paint = BALL_TONES[colour or BALL]
    return _put(canvas, name, pos, origin, tag=TAG_BALL, brightness=BALL_LIGHT, view=FAR, turns=_STANDING[name])


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
