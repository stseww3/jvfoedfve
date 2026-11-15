"""The great orrery (plan ART-PLAN 7.2 / 8; parts/A5-machines.md 2.3; card packages/machines/orrery.md).

The star of the star hall and of V7, the first look through the front door: a brass solar system hung
in the well on the entrance axis, between the telescope pier and the east wall, over the heads of
the people who walk in. Everything of it is seen from below first, so the sun and the planets are
the lowest things it has and nothing hangs in front of them; the arms, the works and the shaft
stand above them against the dark ceiling.

Coordinates are the skeleton's (the card's old centre (7.5, 0) and diameter 7 are void):

    ORRERY_CENTRE = (11.5, 0.5)   the hung centre (x, z)
    ORRERY_R      = 2.5           outer radius; nothing of the machine reaches past it
    ORRERY_HANG_Y = 14.0          the ceiling's lower face: the hub seats on interiors' hang point
    ORRERY_RING_Y = 7.5           the plane of the sun and the orbits (A0 #30150): a block below the eye
                                  of a person on the gallery, who looks down on the orbits
    ORRERY_BODY_Y = (6.5, 14.0)   the machine fills this; the floor below (y 0..6.5) stays walkable

How it is built, top to bottom (the same in both versions):

    hub      on the ceiling: the rose, three iron struts, the motor and its closed gear box
    column   a fixed iron tube down to the works; the hollow drive shaft turns inside it and the
             stay rod of the sun hangs down the middle of that
    works    six sleeves, one inside the other, each with a wheel at its upper end and an arm at
             its lower end. The innermost is the drive shaft itself and carries Mercury; its wheel
             turns a lay shaft beside the column, and the lay shaft's five other wheels turn the
             five other sleeves. An outer sleeve is a shorter one: Saturn's arm is the highest and
             its wheel the lowest, so a longer arm always passes over the shorter ones
    arms     flat brass bars in a stack; each planet hangs from the end of its arm on a rod
    sun      an opal lamp globe on the stay rod, the lowest and brightest thing of the machine;
             its glass, and the undersides of the planets, are drawn so that the engine lights them
             in full from below as well (see "faces lit as if they looked up")

Two versions stand side by side until the review picks one (card; A0 #30150):

  a  planar   the orbits lie flat in the ring plane inside a graduated zodiac band, which hangs
              on three iron rods from a spider under the works. Mercury, the Earth, Jupiter and
              Saturn hang just under the plane, Venus and Mars ride just over it; the Earth and
              Jupiter each carry the hoop of their orbit. The works are open: two stepped cones
              of wheels between brass plates
  b  tiered   the planets climb outward from the sun into a bowl; an equator ring and a tilted
              ecliptic band hang round them (armillary) from the same spider, on three straps;
              the works are shut in a brass drum

WHY THE PLANETS STAND WHERE THEY STAND. They turn at six rates, so sooner or later every planet
passes every other at every angle: what one sweeps as it goes round must stay clear of what the
others sweep. A rod sweeps a cylinder, a ball a ring. Balls large enough to be told apart from the
door do not fit side by side inside ORRERY_R, so in version a they pass over and under one another
(two levels, the rods of the lower ones going up between the upper ones), and in version b each
stands higher than the one inside it. clearances() measures it; `python -m scenes.obs.machines.orrery`
prints it and fails when two parts come closer than a third of a texel.

WHAT TURNS (the motion line's, plan/parts/motion.md): the six arms, each one model with its anchor
on the vertical axis through the centre, and in version a the lay shaft, anchored on its own axis.
moving() lists them with the ticks each takes for a turn. Those follow from the teeth of the
wheels, so wheels that are seen meshing stay in mesh: build() places the rest pose, in which every
sleeve wheel has a tooth in a gap of its lay wheel.

The sun throws no light of its own: build() offers one warm source in its cell to the light line
(A0: one lamp, cell (11, 7, 0), level 12; interiors offers the same cell, sky/lights merges them).

gear() and grad_circle() are the combined pieces the card asked for; another machine imports them
from this module (machines/_kit.py is not to be made yet).

    from scenes.obs.machines import orrery
    n += orrery.build(canvas, origin, version="a")     # places one orrery; returns the entity count
"""
import contextlib
import functools
import math

import numpy as np

from artkit import models as M

from ..common import palette as P
from ..common import skeleton as S
from ..motion import _kit as MK
from ..props import _kit as K

PREFIX = "mach_orrery_"
VERSION = "a"                    # the version build() places until the review picks one
PX = 1.0 / 16.0                  # a texel, in blocks: every length below is in blocks

# --- materials (palette only) -------------------------------------------------------------------
BRASS = P.mat("brass")
BRASS_L = P.mat("brass", base=4)                 # polished: pillars, lips
BRASS_D = P.mat("brass_dark")
COPPER = P.mat("old_copper")
IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
STEEL = P.mat("iron", base=5)                    # pinions
ENAMEL = P.mat("enamel")
GLOW = [K.flat("glow", i) for i in range(len(P.RAMPS["glow"]))]      # dark to light
SCALE_LIGHT, SCALE_DARK = K.flat("cream", 2), K.flat("brass", 0)     # the two tones of a graduated scale
STUD = K.flat("iron", 5)

# --- where it hangs (all from the skeleton) -----------------------------------------------------
CX, CZ = S.ORRERY_CENTRE                 # (11.5, 0.5)
R = S.ORRERY_R                           # 2.5
HANG_Y = S.ORRERY_HANG_Y                 # 14.0
RING_Y = S.ORRERY_RING_Y                 # 7.5: heights below are measured from this plane
FLOOR_Y = S.ORRERY_BODY_Y[0]             # 6.5: nothing the machine draws goes below this

SUN_R = 0.42                             # a lamp globe: large enough to be the sun from the door, ten
#                                          blocks off, small enough to leave the planets their room
SUN_LIGHT = 12                           # the one warm source build() offers the light line, in the
#                                          sun's cell (11, 7, 0). A0's figure: the sun is the hall's
#                                          brightest point, the cell before the mother clock is set
#                                          one below it, at 11

# --- the planets ----------------------------------------------------------------------------------
PLANETS = ("mercury", "venus", "earth", "mars", "jupiter", "saturn")          # inner to outer
# radius of the ball. Six worlds told apart by size and by stuff (cr2-M1, A0 #30150): steel grey,
# porcelain white, verdigris with white caps and a moon, old copper, belted brass, cream in rings
BALL = dict(mercury=0.11, venus=0.14, earth=0.18, mars=0.13, jupiter=0.27, saturn=0.18)
SATURN_RING = (0.21, 0.27)               # inner and outer edge
MOON = 0.06                              # radius of the Earth's moon

# --- the works --------------------------------------------------------------------------------------
TOOTH = 4 * PX                           # the pitch of every wheel: a tooth of 2 px and a gap of 2 px
#                                          (cr2-M1), so that teeth read as teeth and not as a rough rim
# teeth of (the wheel on the planet's sleeve, the wheel on the lay shaft that turns it). Every pair
# adds up to 20 teeth: one distance between the two shafts for all six pairs
TEETH = dict(mercury=(5, 15), venus=(7, 13), earth=(8, 12), mars=(9, 11), jupiter=(13, 7), saturn=(15, 5))
LAY_TURN = 3003                          # ticks the lay shaft takes for a turn (3 x 7 x 11 x 13, so that
#                                          every planet's turn is a whole number of ticks too)
PERIOD = {k: LAY_TURN * a // b for k, (a, b) in TEETH.items()}       # 1001, 1617, 2002, 2457, 5577, 9009:
#                                          Mercury in 50 seconds, Saturn in seven and a half minutes
assert all(PERIOD[k] * b == LAY_TURN * a for k, (a, b) in TEETH.items())
SPIN = {k: PERIOD["mercury"] / PERIOD[k] for k in PLANETS}           # rate against Mercury's: 1 .. 0.11
SLEEVE = dict(mercury=0.0625, venus=0.08, earth=0.10, mars=0.12, jupiter=0.14, saturn=0.16)   # radius

# the rest pose: where each arm points, in degrees from east towards south (the yaw of its display).
# Chosen on V7's picture, which looks west and up: the far side (about 180) is where a planet shows
# the door its lit face under the sun; nothing stands before the sun or the works; no two long arms
# make a line through the centre
POSE = dict(mercury=265.0, venus=78.0, earth=196.0, mars=318.0, jupiter=228.0, saturn=150.0)

ROD = PX                                 # radius of the rods the planets hang on: 2 px across
ARM_T = 2 * PX                           # an arm is a bar 2 px thick; the arms are stacked 3 px apart
ARM = {k: 0.625 + 3 * PX * i for i, k in enumerate(PLANETS)}         # the underside of each arm
# Radius of each orbit. Version a: Mercury, the Earth, Jupiter and Saturn pass one another in the
# lower level, with Venus and Mars in the upper level between their rods. Version b: every rod
# clears the ball outside it, and what the balls still overlap is made up in height
ORBIT = {
    "a": dict(mercury=0.555, venus=0.7975, earth=1.04, mars=1.285, jupiter=1.53, saturn=2.13),
    "b": dict(mercury=0.59, venus=0.845, earth=1.14, mars=1.385, jupiter=1.77, saturn=2.14),
}
HANG, RIDE = -0.14, 0.14                 # version a: the top of a ball that hangs under the plane, the
#                                          underside of one that rides over it
LEVEL = {                                # the middle of each planet over the ring plane
    "a": dict(mercury=HANG - BALL["mercury"], venus=RIDE + BALL["venus"], earth=HANG - BALL["earth"],
              mars=RIDE + BALL["mars"], jupiter=HANG - BALL["jupiter"], saturn=HANG - 0.03 - BALL["saturn"]),
    "b": dict(mercury=-0.27, venus=-0.07, earth=0.20, mars=0.51, jupiter=0.80, saturn=1.21),
}
HOOPS = ("earth", "jupiter")             # version a: the planets that carry the hoop of their orbit.
#                                          Six hoops a quarter of a block apart close up into one
#                                          disc from the door; two, and the band, stay three rings
HOOP = 2 * PX                            # the section of a hoop, 2 px square
BAND = (2.245, 2.495)                    # version a: the zodiac band, inner and outer radius (the
#                                          corners of its 72 sides come to ORRERY_R)
STAYS = (60.0, 180.0, 300.0)             # the three hangers of either version: never four
STAY_R = 2.37                            # version a: the hangers stand on the middle of the band
SPIDER_Y = 1.875                         # version a: underside of the iron spider the band hangs from
MOVE_Y0 = 2.0                            # underside of the works
WHEEL_Y = {k: MOVE_Y0 + 3 * PX * (i + 1) for i, k in enumerate(reversed(PLANETS))}   # underside of each pair
MOVE_Y1 = 3.4375                         # top of the works: the column stands on it
LAY_YAW = 60.0                           # where the lay shaft stands, seen from the centre
EQUATOR = (2.37, 2.495)                  # version b: the level ring
ECLIPTIC = dict(radius=2.36, thick=2 * PX, width=4 * PX, tilt=20.0)    # version b: the tilted band

HUB_DROP = 0.95                          # the hub hangs this far below the ceiling
COLUMN_AT = 11.6                         # the column's anchor: it takes the light of its own height


def pitch_radius(teeth):
    """Pitch radius in blocks of a wheel with `teeth` teeth on the pitch TOOTH."""
    return teeth * TOOTH / (2.0 * math.pi)


LAY_A = pitch_radius(sum(TEETH["mercury"]))      # 0.796: from the centre to the lay shaft


# --- painting -------------------------------------------------------------------------------------
@contextlib.contextmanager
def _lit_from_below():
    """artkit paints the tone steps of rings, tubes and balls for a light from above (models.LIGHT),
    and the game shades a face that looks down to four tenths. This machine hangs over its own lamp
    and over the people who look at it: with both, its undersides, which is what the door sees,
    would be the darkest brass in the hall. So its models are painted for a light from below."""
    keep = M.LIGHT
    M.LIGHT = (0.0, -1.0, 0.0)
    try:
        yield
    finally:
        M.LIGHT = keep


def _tone(mat, normal, toward):
    """`mat` one step lighter where a face looks at the sun, one step darker where it looks away."""
    d = sum(n * t for n, t in zip(normal, toward))
    return mat.variant(1 if d > 0.3 else -1 if d < -0.4 else 0, 0)


# --- faces lit as if they looked up -----------------------------------------------------------------
# The engine shades every face of an item display by the axis of the model the face looks along
# most nearly, carried through the display's matrix (26.3: BakedQuad.direction, and
# PoseStack.Pose.transformNormal in VertexConsumer.putBakedQuad): in full under an axis that ends up
# looking up, at 0.5 to 0.74 under one that looks sideways, at 0.4 under one that looks down. An
# element's light emission and its shade direction do not change that for an item. The door looks
# up at this machine at 36 degrees, so more than half of what it sees of a ball is the ball's
# underside: the opal sun came out at four tenths of its tone, duller than the windows behind it.
#
# Which axis a face is filed under is the model's affair; where that axis ends up is the display's.
# So a face can stand where it belongs and be lit as if it looked up: it is drawn in a model that
# is turned or leant over, as the top of a thin box that has no other face, and the display's
# matrix sets it back in its place.
#
#   _corner()   a model stood on one corner: its three axes come out 35 degrees over the level, a
#               third of a turn apart. An upright face that looks within 30 degrees of one of them
#               is filed under it and lit at 0.96; two such frames, a sixth of a turn apart, take
#               every upright face there is. Plain turns: nothing is stretched.
#   _leant()    a model leant over: a level plane of the scene is a tipped plane of the model,
#               unstretched (a texel stays a texel), and the model's y axis comes out 42 degrees
#               over the level. A face that looks straight down is filed under it and lit in full,
#               and stays so while the display turns about the vertical: the planets' undersides
#               go round lit. The price is a matrix that is no turn (tools/check.py reads its scale
#               as a stretch; no face is stretched).
LAMPS = tuple(np.array(v) / np.linalg.norm(v) for v in ((0.2, 1.0, -0.7), (-0.2, 1.0, 0.7)))   # the engine's two
FILED = np.array([(0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0)], dtype=float)   # its order
LIT = 0.95                               # the share of its tone a face drawn this way must keep
SURE = 0.1                               # by this much the axis a face is filed under must win
LAP = PX / 50.0                          # faces run this far past their edges, so no seam opens
SKIN = PX / 10.0                         # how thick the boxes behind them are


def _corner(azimuth):
    """The frame of a model stood on a corner: its x axis comes out at `azimuth` (from east towards
    south), y and z a third of a turn on either side of it, all three 35.26 degrees over the level."""
    c, s = math.sqrt(2.0 / 3.0), math.sqrt(1.0 / 3.0)
    g = np.array([(c * math.cos(math.radians(azimuth + k)), s, c * math.sin(math.radians(azimuth + k)))
                  for k in (0.0, 120.0, 240.0)]).T
    return g if np.linalg.det(g) > 0.0 else g[:, [0, 2, 1]]


def _leant(tip=40.0, rise=42.0):
    """The frame of a model leant over, for faces that look straight down. The plane of the model
    that is tipped `tip` degrees about x goes to the level plane of the scene as it is; the model's
    y axis, under which those faces are filed, is lit like a face that looks `rise` degrees over
    the level (in full from 38.2 degrees on, whichever way the display is turned about the
    vertical). Of all matrices that do this it is the least lopsided one."""
    b, e = math.radians(tip), math.radians(rise)
    sink = math.cos(e) / math.sin(b)
    lean = sink * math.tan(e) + 1.0 / math.tan(b)
    model = np.array([(1.0, 0.0, 0.0), (0.0, math.cos(b), math.sin(b)), (0.0, -math.sin(b), math.cos(b))])
    scene = np.array([(1.0, 0.0, 0.0), (0.0, -sink, lean), (0.0, 0.0, -1.0)])
    return scene.T @ model               # each row of `model` goes to the same row of `scene`


def _filed(g, normal):
    """The axis of the model that the engine files a face under which looks along `normal` in the
    scene, the model being shown through g; and by how much that axis wins over the next."""
    v = g.T @ np.asarray(normal, dtype=float)
    along = FILED @ (v / np.linalg.norm(v))
    k = int(np.argmax(along))            # the first of equals, as in the engine
    return FILED[k], float(along[k] - np.sort(along)[-2])


def brightness(g, normal, spins=False):
    """The share of its tone the engine leaves a face that looks along `normal` in the scene, in a
    model shown through g; for a display that spins about the vertical, the least of a whole turn."""
    axis, _sure = _filed(g, normal)
    s = np.linalg.solve(g.T, axis)
    s = s / np.linalg.norm(s)
    least = 1.0
    for turn in (range(0, 360, 5) if spins else (0,)):
        a = math.radians(turn)
        t = np.array([s[0] * math.cos(a) - s[2] * math.sin(a), s[1], s[0] * math.sin(a) + s[2] * math.cos(a)])
        least = min(least, 0.4 + 0.6 * sum(max(0.0, float(t @ lamp)) for lamp in LAMPS))
    return least


def _quat_of(r):
    """The quaternion (x, y, z, w) of a turn given as a matrix."""
    t = r[0, 0] + r[1, 1] + r[2, 2]
    if t > 0.0:
        s = 2.0 * math.sqrt(t + 1.0)
        q = ((r[2, 1] - r[1, 2]) / s, (r[0, 2] - r[2, 0]) / s, (r[1, 0] - r[0, 1]) / s, s / 4.0)
    elif r[0, 0] > r[1, 1] and r[0, 0] > r[2, 2]:
        s = 2.0 * math.sqrt(1.0 + r[0, 0] - r[1, 1] - r[2, 2])
        q = (s / 4.0, (r[0, 1] + r[1, 0]) / s, (r[0, 2] + r[2, 0]) / s, (r[2, 1] - r[1, 2]) / s)
    elif r[1, 1] > r[2, 2]:
        s = 2.0 * math.sqrt(1.0 + r[1, 1] - r[0, 0] - r[2, 2])
        q = ((r[0, 1] + r[1, 0]) / s, s / 4.0, (r[1, 2] + r[2, 1]) / s, (r[0, 2] - r[2, 0]) / s)
    else:
        s = 2.0 * math.sqrt(1.0 + r[2, 2] - r[0, 0] - r[1, 1])
        q = ((r[0, 2] + r[2, 0]) / s, (r[1, 2] + r[2, 1]) / s, s / 4.0, (r[1, 0] - r[0, 1]) / s)
    return tuple(float(v) for v in q)


HALF_TURN = np.diag([-1.0, 1.0, -1.0])   # the item renderer shows a model turned half a turn about y


def _display(model, g, scale, yaw=0.0):
    """The item display that shows `model` through the frame g at `scale`, its anchor on the entity
    and the whole turned by `yaw`: what artkit.models.display gives for a plain turn, for any
    matrix. The matrix is taken apart into a turn, a scale along three axes and a second turn, as
    the engine takes one apart; a plain turn stays one turn and one scale."""
    nbt = M.display(model, yaw=yaw, scale=scale)
    a = np.asarray(g, dtype=float) * (scale / 16.0)                 # the model's units to blocks
    u, s, vt = np.linalg.svd(HALF_TURN @ (a * 16.0) @ HALF_TURN)
    if s[0] - s[2] < 1e-9:
        u, vt = u @ vt, np.eye(3)
    elif np.linalg.det(u) < 0.0:
        u[:, 2], vt[2, :] = -u[:, 2], -vt[2, :]
    off = np.array(model.anchor) + np.array(model.shift()) - 8.0
    t = HALF_TURN @ (a @ off)
    tr = nbt["transformation"]
    kind = type(tr["scale"][0])
    tr["left_rotation"] = [kind(v) for v in _quat_of(u)]
    tr["right_rotation"] = [kind(v) for v in _quat_of(vt)]
    tr["scale"] = [kind(v) for v in s]
    tr["translation"] = [kind(-v) for v in t]
    return nbt


def _shown(nbt):
    """A display's NBT read back the way the engine reads it (DisplayRenderer and the item renderer;
    artkit.gamescene does the same): the matrix that takes the coordinates of the exported model to
    blocks in the scene, and where the exported model's origin lands, from the entity."""
    tr = nbt["transformation"]
    yaw = math.radians(float(nbt["Rotation"][0]))
    turn = np.array([[math.cos(yaw), 0.0, -math.sin(yaw)], [0.0, 1.0, 0.0], [math.sin(yaw), 0.0, math.cos(yaw)]])
    a = turn @ _matrix(tr["left_rotation"]) @ np.diag([float(v) for v in tr["scale"]]) \
        @ _matrix(tr["right_rotation"]) @ HALF_TURN / 16.0
    return a, turn @ np.array([float(v) for v in tr["translation"]]) - a @ np.full(3, 8.0)


class _Draw:
    """A model drawn in blocks. artkit's unit is 1/16 block of a model shown at scale 1; a model
    shown at scale s is drawn s times smaller with s texels to the unit, 16 px to the block.

    With a `frame` the model is one of those that are shown turned or leant over: it is made of
    face() calls alone, and `lit` keeps the share of its tone each face is left with."""

    def __init__(self, name, scale=1.0, frame=None, spins=False):
        self.scale = float(scale)
        self.u = 16.0 / self.scale
        self.m = M.Model(PREFIX + name, px=self.scale)
        self.g = None if frame is None else np.asarray(frame, dtype=float)
        self.spins = spins
        self.lit = []

    def display(self, yaw=0.0):
        if self.g is None:
            return M.display(self.m, yaw=yaw, scale=self.scale)
        return _display(self.m, self.g, self.scale, yaw)

    def points(self, step):
        """Points over the model's faces, `step` apart, in blocks from the anchor along the axes of
        a plain model of the same part (the display's yaw is still to come)."""
        if self.g is None:
            return _surface(self.m, self.scale, step)
        stretch = float(np.linalg.svd(self.g, compute_uv=False)[0])
        return _surface(self.m, self.scale, step / stretch) @ self.g.T

    def face(self, centre, normal, across, w, h, mat, lap=LAP, **kw):
        """One face and nothing behind it: a rectangle `w` along `across` and `h` the other way,
        its middle at `centre`, looking along `normal`; all as it is to stand in the scene, in
        blocks from the anchor. In a frame it is drawn where the frame's display takes it from."""
        g = np.eye(3) if self.g is None else self.g
        n = np.asarray(normal, dtype=float)
        ax = np.asarray(across, dtype=float)
        n, ax = n / np.linalg.norm(n), ax / np.linalg.norm(ax)
        au, av = np.linalg.solve(g, ax), np.linalg.solve(g, np.cross(n, ax))
        lu, lv = float(np.linalg.norm(au)), float(np.linalg.norm(av))
        if abs(float(au @ av)) > 1e-9 * lu * lv:
            raise ValueError(f"{self.m.name}: this frame skews a face that looks along {tuple(normal)}")
        y = g.T @ n
        y = y / np.linalg.norm(y)
        x = au / lu
        r = np.column_stack([x, y, np.cross(x, y)])                 # the box's own axes in the model
        if abs(r[2, 0]) > 1.0 - 1e-9:
            turn = (math.atan2(-r[1, 2], r[1, 1]), -math.copysign(math.pi / 2.0, r[2, 0]), 0.0)
        else:
            turn = (math.atan2(r[2, 1], r[2, 2]), -math.asin(r[2, 0]), math.atan2(r[1, 0], r[0, 0]))
        c = np.linalg.solve(g, np.asarray(centre, dtype=float)) * self.u
        half = np.array([(w / 2.0 + lap) * lu, 0.0, (h / 2.0 + lap) * lv]) * self.u
        self.m.box(tuple(c - half - (0.0, SKIN * self.u, 0.0)), tuple(c + half), mat,
                   rot=("xyz", tuple(math.degrees(v) for v in turn), tuple(c)), skip="nsewd", **kw)
        self.lit.append((brightness(g, n, self.spins), _filed(g, n)[1]))

    def _v(self, p):
        return tuple(v * self.u for v in p)

    def box(self, a, b, mat, rot=None, **kw):
        if rot is not None:
            rot = (rot[0], rot[1], self._v(rot[2]))
        self.m.box(self._v(a), self._v(b), mat, rot=rot, **kw)

    def tube(self, axis, c, a0, a1, radius, mat, **kw):
        self.m.tube(axis, self._v(c), a0 * self.u, a1 * self.u, radius * self.u, mat, **kw)

    def taper(self, axis, c, a0, a1, r0, r1, mat, **kw):
        self.m.taper(axis, self._v(c), a0 * self.u, a1 * self.u, r0 * self.u, r1 * self.u, mat, **kw)

    def ring(self, axis, centre, radius, thick, width, mat, **kw):
        self.m.ring(axis, self._v(centre), radius * self.u, thick * self.u, width * self.u, mat, **kw)

    def beam(self, a, b, width, height, mat, **kw):
        self.m.beam(self._v(a), self._v(b), width * self.u, height * self.u, mat, **kw)

    def turned(self, *turns, about=(0.0, 0.0, 0.0)):
        return self.m.turned(*turns, about=self._v(about))

    def spoke(self, angle, r0, r1, y0, y1, width, mat, **kw):
        """A bar from radius r0 to r1 about the model's axis, at `angle` from +x towards +z."""
        kw.setdefault("grain", "x")
        self.box((r0, y0, -width / 2.0), (r1, y1, width / 2.0), mat, rot=("y", -angle, (0.0, 0.0, 0.0)), **kw)

    def stud(self, p, out="y", mat=STUD):
        """A screw head: one texel square, half a texel proud. p is the middle of its foot."""
        k = M.AXES.index(out[-1])
        lo, hi = [v - PX / 2.0 for v in p], [v + PX / 2.0 for v in p]
        lo[k], hi[k] = sorted((p[k], p[k] + (-PX / 2.0 if out.startswith("-") else PX / 2.0)))
        self.box(lo, hi, mat)

    def gear(self, c, y0, y1, teeth, body, **kw):
        if "bore" in kw:
            kw["bore"] *= self.u
        return gear(self.m, (c[0] * self.u, c[1] * self.u), y0 * self.u, y1 * self.u, teeth, body, unit=self.u, **kw)

    def orb(self, centre, radius, bands, sides=10, toward=None, under=None):
        """A ball in bands of flat tone, bands = [(from, to, layers, material)] as in Model.ball. It
        is lit by the sun and by nothing else: the half that looks at `toward` (left out, the
        model's origin, where the sun is) is a step lighter, the half that looks away a step darker.
        A planet on the far side of the sun shows the door its day, one on the near side its night.
        With `under`, a model in the frame _leant(), the ledges that look down are drawn there, and
        the ledges no eye can reach are left out."""
        c = self._v(centre)
        r = radius * self.u
        toward = toward or tuple(-v for v in centre)
        size = math.sqrt(sum(v * v for v in toward)) or 1.0
        toward = tuple(v / size for v in toward)
        hw = math.tan(math.pi / sides)
        for t0, t1, layers, mat in bands:
            self.m._n += 1
            seed = self.m._n
            for i in range(layers):
                a0 = t0 + (t1 - t0) * i / layers
                a1 = t0 + (t1 - t0) * (i + 1) / layers
                tm = (a0 + a1) / 2.0
                slope = math.sqrt(max(0.0, 1.0 - tm * tm))
                if r * slope < 1e-6:
                    continue
                lo = (c[0] - r * slope * hw, c[1] + r * a0, c[2] - r * slope)
                hi = (c[0] + r * slope * hw, c[1] + r * a1, c[2] + r * slope)
                # the ball widens towards its middle: below it a layer's underside shows and its top
                # is inside the next layer, above it the other way round
                skip = "ew" if under is None else "ewd" if tm < 1e-9 else "ew"
                if under is not None and abs(tm) > 1e-9:
                    skip += "u" if tm < 0.0 else "d"
                for s in range(sides // 2):
                    ang = math.radians(360.0 * s / sides)
                    faces = {"u": _tone(mat, (0.0, 1.0, 0.0), toward), "d": _tone(mat, (0.0, -1.0, 0.0), toward)}
                    for letter, nz in (("n", -slope), ("s", slope)):
                        faces[letter] = _tone(mat, (nz * math.sin(ang), tm, nz * math.cos(ang)), toward)
                    self.m.box(lo, hi, mat, rot=("y", math.degrees(ang), c) if s else None, skip=skip,
                               faces=faces, seed=seed, grain="x")
                    if under is not None and tm < 1e-9:
                        under.face((centre[0], centre[1] + radius * a0, centre[2]), (0.0, -1.0, 0.0),
                                   (math.cos(ang), 0.0, -math.sin(ang)), 2.0 * radius * slope * hw,
                                   2.0 * radius * slope, faces["d"], seed=1, grain="x")


# --- the combined pieces (gear, graduated circle): written here, imported by other machines -------
def gear(m, c, y0, y1, teeth, body, tooth=None, unit=16.0, phase=0.0, spokes=0, bore=0.0, collet=None):
    """A spur wheel about the vertical axis through c = (x, z), from y0 to y1, with `teeth` teeth.

    Lengths are in the model's units, `unit` of them to the block. The teeth stand on the pitch TOOTH
    (2 px of tooth, 2 px of gap) whatever the size of the wheel, so two wheels mesh when the distance
    between their axes is the sum of their pitch_radius(); `phase` is the angle of the middle of one
    tooth, from +x towards +z. spokes > 0 crosses the wheel out: a rim, that many spokes (not four:
    four make a cross) and a collet of radius `bore`. A wheel belongs where there is real drive
    (plan 2). Returns the pitch radius in units."""
    if spokes == 4:
        raise ValueError(f"{m.name}: a wheel with four spokes reads as a cross")
    cx, cz = c
    px = unit / 16.0
    rp = pitch_radius(teeth) * unit
    root = rp - px
    ym = (y0 + y1) / 2.0
    m._n += 1
    seed = m._n
    for i in range(teeth):
        m.box((cx + root - 0.2 * px, y0, cz - 0.875 * px), (cx + rp + 0.9 * px, y1, cz + 0.875 * px), tooth or body,
              rot=("y", -(phase + 360.0 * i / teeth), (cx, ym, cz)), seed=seed, grain="x")
    if spokes:
        m.ring("y", (cx, ym, cz), root - px, 2.0 * px, y1 - y0, body, sides=max(16, 2 * teeth))
        for i in range(spokes):
            m.box((cx + bore * 0.7, y0, cz - px), (cx + root - 1.9 * px, y1, cz + px), body,
                  rot=("y", -(phase + 360.0 * (i + 0.5) / spokes), (cx, ym, cz)), grain="x")
    else:
        m.tube("y", c, y0, y1, root, body, sides=min(16, 2 * teeth))
    if bore > 0.0:
        m.tube("y", c, y0 - 0.5 * px, y1 + 0.5 * px, bore, collet or body, sides=8)
    return rp


def grad_circle(m, axis, centre, radius, thick, width, body, marks=60, light=SCALE_LIGHT, dark=SCALE_DARK,
                signs=0, sign_mat=ENAMEL, proud=0.0, arc=(0.0, 360.0)):
    """A graduated circle: a ring round `axis` (as Model.ring: radius to the middle of its section,
    thick across it, width along the axis) laid out as a scale of `marks` light marks with dark ones
    between -- a silvered scale with its divisions, drawn as stuff and not as a rough edge (cr2-M1:
    a mark wants 2 px, which is 36 marks and 12 signs, or 60 marks, on a radius of 2.4 blocks).
    signs > 0 sets that many plaques of `sign_mat` into it, evenly, each as long as three marks and
    `proud` proud of the scale on every side (the twelve signs of a zodiac band). marks=0 leaves a
    plain ring of `body`."""
    a0, a1 = arc
    if not marks:
        m.ring(axis, centre, radius, thick, width, body, sides=72, arc=arc)
        return m
    m._n += 3
    seeds = (m._n - 2, m._n - 1, m._n)
    sectors = signs or 1
    span = (a1 - a0) / sectors
    per = max(1, int(round(marks / sectors)))               # light marks to a sector
    pieces = 2 * per + 1 if signs else 2 * per              # between two plaques: dark, light, ..., dark
    step = span / (pieces + 3.0) if signs else span / pieces
    plaque = 3.0 * step if signs else 0.0
    for s in range(sectors):
        start = a0 + span * s
        if signs:
            m.ring(axis, centre, radius, thick + 2.0 * proud, width + 2.0 * proud, sign_mat,
                   sides=int(round(360.0 / plaque)), arc=(start - plaque / 2.0, start + plaque / 2.0), seed=seeds[2])
        for i in range(pieces):
            a = start + plaque / 2.0 + step * i
            m.ring(axis, centre, radius, thick, width, dark if i % 2 == 0 else light,
                   sides=int(round(360.0 / step)), arc=(a, a + step), seed=seeds[i % 2])
    return m


# --- the shared models (both versions) ----------------------------------------------------------
def _hub():
    """The seat on the ceiling: a stepped brass rose, three iron struts to the gear box the column
    hangs from, the motor beside it and its conduit into the ceiling. The wheels are shut in the
    box: nothing up here is seen to turn, so nothing up here shows teeth. Anchor: the hang point
    on the ceiling (interiors carries it); the model hangs down. Shown at scale 1."""
    d = _Draw("hub", 1.0)
    d.tube("y", (0, 0), -1 * PX, 0.0, 0.95, BRASS_D, sides=16)                 # the rose, flush to the ceiling
    d.tube("y", (0, 0), -3 * PX, -1 * PX, 0.80, BRASS, sides=16)
    d.tube("y", (0, 0), -4 * PX, -3 * PX, 0.42, BRASS_D, sides=12)
    for a in (90.0, 210.0, 330.0):                                             # three struts, never four
        dx, dz = math.cos(math.radians(a)), math.sin(math.radians(a))
        d.beam((0.70 * dx, -3 * PX, 0.70 * dz), (0.30 * dx, -0.78, 0.30 * dz), 2 * PX, 2.5 * PX, IRON)
        d.stud((0.70 * dx, -3 * PX, 0.70 * dz), "-y")
    d.tube("y", (0, 0), -0.92, -0.50, 0.30, IRON, sides=12)                    # the gear box
    d.tube("y", (0, 0), -0.50, -0.50 + PX, 0.33, IRON_D, sides=12)             # its lid
    d.tube("y", (0, 0), -HUB_DROP, -0.92 + PX, 0.22, BRASS, sides=10)          # the bearing the shaft leaves by
    for a in (30.0, 150.0, 270.0):
        d.stud((0.26 * math.cos(math.radians(a)), -0.92, 0.26 * math.sin(math.radians(a))), "-y")
    # the motor: an iron drum on its side, east of the box, brass end bells, a neck into the box
    d.tube("z", (0.56, -0.50), -0.26, 0.26, 0.19, IRON_D, sides=10)
    for z0, z1 in ((-0.31, -0.26), (0.26, 0.31)):
        d.tube("z", (0.56, -0.50), z0, z1, 0.16, BRASS, sides=10)
    for z in (-0.13, 0.0, 0.13):
        d.ring("z", (0.56, -0.50, z), 0.19, PX, PX, IRON, sides=10)            # cooling ribs
    d.box((0.28, -0.58, -0.09), (0.40, -0.42, 0.09), IRON)
    d.box((0.50, -0.31, -0.08), (0.62, -0.25, 0.08), BRASS_D)                  # the terminal box
    d.tube("y", (0.56, 0.0), -0.25, -3 * PX, PX, IRON, sides=6)                # the conduit into the ceiling
    return d


def _column():
    """The fixed tube from the gear box down to the works: iron, with brass collars where its
    lengths are joined and a brass foot on the works. Anchor: on the axis at COLUMN_AT, so that it
    takes the light of its own height and the metal fades towards the ceiling. Shown at scale 1."""
    d = _Draw("column", 1.0)
    y0, y1 = RING_Y + MOVE_Y1 - COLUMN_AT, HANG_Y - HUB_DROP - COLUMN_AT
    d.tube("y", (0, 0), y0, y0 + 2 * PX, 0.28, BRASS, sides=12)                # the foot
    d.taper("y", (0, 0), y0 + 2 * PX, y0 + 5 * PX, 0.23, 0.16, BRASS_D, sides=10, steps=3)
    d.tube("y", (0, 0), y0 + 5 * PX, y1, 0.13, IRON, sides=10)
    for t in (0.36, 0.70):
        y = y0 + (y1 - y0) * t
        d.tube("y", (0, 0), y - 1.5 * PX, y + 1.5 * PX, 0.17, BRASS_D, sides=10)
        d.tube("y", (0, 0), y - 0.5 * PX, y + 0.5 * PX, 0.20, BRASS, sides=10)
    d.taper("y", (0, 0), y1 - 3 * PX, y1, 0.15, 0.21, BRASS_D, sides=10, steps=3)
    return d


SUN_SIDES = 12
# the globe's layers from the lowest up, as steps of the glow ramp: the hot belt lies low, where the
# door looks at the globe from 36 degrees under it, the foot and the shoulders are amber, the crown
# goes dim into its holder
SUN_TONES = (2, 3, 4, 4, 4, 3, 3, 3, 2, 2, 2, 1, 1, 0)


def _sun():
    """The sun: an opal lamp globe hung on the stay rod. Only the glass glows, and it glows the
    same from every side and from below: its sides are drawn in two models stood on a corner, its
    ledges that look down in a model leant over, so the engine leaves each face its whole tone, and
    the light and dark of the globe is what is painted, in bands. The light it casts is the source
    build() offers. A brass holder grips its crown, a small finial closes it below. Anchor: the
    centre of the globe. Shown at scale 1. Returns the four models: the fittings with the ledges
    that look up, the two of the sides, the one of the underside."""
    d = _Draw("sun", 1.0)
    sides = [_Draw(f"sun_side{i}", 1.0, frame=_corner(15.0 + 60.0 * i)) for i in (0, 1)]
    under = _Draw("sun_under", 1.0, frame=_leant())
    r, n = SUN_R, len(SUN_TONES)
    hw = math.tan(math.pi / SUN_SIDES)
    for i, tone in enumerate(SUN_TONES):
        t0, t1 = -1.0 + 2.0 * i / n, -1.0 + 2.0 * (i + 1) / n
        rr = r * math.sqrt(1.0 - ((t0 + t1) / 2.0) ** 2)
        look = dict(emit=15, seed=1, grain="x")
        for k in range(SUN_SIDES):
            a = math.radians(360.0 * k / SUN_SIDES)
            out = (math.cos(a), 0.0, math.sin(a))
            best = max(sides, key=lambda f: brightness(f.g, out))
            best.face((rr * out[0], r * (t0 + t1) / 2.0, rr * out[2]), out, (-out[2], 0.0, out[0]),
                      2.0 * rr * hw, r * (t1 - t0), GLOW[tone], **look)
        for k in range(SUN_SIDES // 2):                 # the ledge to the next layer: strips that cross
            a = math.radians(360.0 * k / SUN_SIDES)
            across = (math.cos(a), 0.0, math.sin(a))
            if t0 + t1 < 0.0:
                under.face((0.0, r * t0, 0.0), (0.0, -1.0, 0.0), across, 2.0 * rr * hw, 2.0 * rr, GLOW[tone], **look)
            else:
                d.face((0.0, r * t1, 0.0), (0.0, 1.0, 0.0), across, 2.0 * rr * hw, 2.0 * rr, GLOW[tone], **look)
    d.tube("y", (0, 0), 0.70 * r, 0.70 * r + 0.08, 0.74 * r, BRASS_D, sides=12)        # the holder's rim
    d.taper("y", (0, 0), 0.70 * r + 0.08, r + 0.10, 0.62 * r, 0.13, BRASS, sides=12, steps=3)
    d.tube("y", (0, 0), r + 0.10, ARM["mercury"], 0.09, BRASS_D, sides=8)              # up to Mercury's collet
    d.tube("y", (0, 0), -r - 0.07, -r + 0.02, 0.10, BRASS_D, sides=8)                  # the finial
    d.tube("y", (0, 0), -r - 0.14, -r - 0.07, 0.0625, BRASS, sides=6)
    return [d] + sides + [under]


# --- the arms (both versions) ---------------------------------------------------------------------
def _flat(name, step):
    return K.flat(name, step)


def _planet(d, key, at, under):
    """The ball of one planet at `at`, and what marks it out; its underside goes to `under`."""
    r = BALL[key]
    if key == "mercury":
        d.orb(at, r, [(-1.0, 1.0, 3, _flat("iron", 6))], under=under)
    elif key == "venus":
        d.orb(at, r, [(-1.0, 1.0, 4, _flat("porcelain", 3))], under=under)
    elif key == "earth":
        d.orb(at, r, [(-1.0, -0.84, 1, _flat("porcelain", 3)), (-0.84, 0.84, 4, _flat("verdigris", 2)),
                      (0.84, 1.0, 1, _flat("porcelain", 3))], sides=10, under=under)
    elif key == "mars":
        d.orb(at, r, [(-1.0, 0.5, 3, _flat("old_copper", 2)), (0.5, 1.0, 1, _flat("porcelain", 3))], under=under)
    elif key == "jupiter":
        belt, zone = _flat("old_copper", 1), _flat("brass", 4)
        d.orb(at, r, [(-1.0, -0.75, 1, belt), (-0.75, -0.5, 1, _flat("brass", 3)), (-0.5, -0.25, 1, belt),
                      (-0.25, 0.25, 2, zone), (0.25, 0.5, 1, belt), (0.5, 0.75, 1, _flat("brass", 3)),
                      (0.75, 1.0, 1, belt)], sides=12, under=under)
    elif key == "saturn":
        d.orb(at, r, [(-1.0, -0.2, 2, _flat("cream", 2)), (-0.2, 0.2, 1, _flat("cream", 1)),
                      (0.2, 1.0, 2, _flat("cream", 2))], sides=10, under=under)
        r0, r1 = SATURN_RING
        with d.turned(("x", 22.0), ("z", 6.0), about=at):                      # the ring, tilted
            d.ring("y", at, (r0 + r1) / 2.0, r1 - r0, PX, BRASS_L, sides=18)


def _moon(d, version, r, level, under):
    """The Earth's moon. Where the Earth carries its hoop the moon hangs from the hoop a little way
    on; where it does not, on a wire from the Earth's seat."""
    earth = BALL["earth"]
    if version == "a":
        a = math.radians(16.0)
        x, z = r * math.cos(a), r * math.sin(a)
        d.orb((x, HANG - MOON, z), MOON, [(-1.0, 1.0, 2, _flat("porcelain", 2))], sides=6, toward=(-x, 0.25, -z), under=under)
        d.tube("y", (x, z), HANG - 0.01, -HOOP / 2.0, PX / 2.0, BRASS_D, sides=4)
    else:
        off, y = 0.30, level + 0.05
        top = level + earth + 0.04
        d.orb((r, y, off), MOON, [(-1.0, 1.0, 2, _flat("porcelain", 2))], sides=6, toward=(-r, -level, 0.0), under=under)
        d.box((r - PX / 2, top, 0.0), (r + PX / 2, top + PX, off + PX / 2), BRASS_D)
        d.box((r - PX / 2, y + MOON - 0.01, off - PX / 2), (r + PX / 2, top + PX, off + PX / 2), BRASS_D)


def _level_ring(d, under, radius, thick, width, mat, sides, y=0.0):
    """A level ring about the model's axis, as d.ring draws it, with its underside in `under`."""
    first = len(d.m.parts)
    d.ring("y", (0.0, y, 0.0), radius, thick, width, mat, sides=sides)
    for part in d.m.parts[first:]:
        part["skip"].add("d")
    tone = M._shade(mat, (0.0, -1.0, 0.0), "along")
    half = (radius + thick / 2.0) * math.tan(math.pi / sides)
    for s in range(sides):
        a = math.radians(360.0 * s / sides)
        out = (math.cos(a), 0.0, -math.sin(a))
        under.face((radius * out[0], y - width / 2.0, radius * out[2]), (0.0, -1.0, 0.0), out, thick, 2.0 * half,
                   tone, seed=2, grain="z")


def _arm(version, key):
    """One planet and all that turns with it, as one model: the sleeve with its wheel (version a;
    in b the wheel is inside the drum), the arm at the sleeve's lower end, the rod the planet hangs
    on, the planet, and in version a the hoop of its orbit if it carries one. The anchor is the
    centre, in the ring plane; the arm runs out along +x. Shown at scale 2. With it comes a second
    model that stands on the same spot and turns with it: the undersides of the planet and of the
    hoop, leant over so that they are lit (see _leant)."""
    d = _Draw(f"{version}_arm_{key}", 2.0)
    under = _Draw(f"{version}_under_{key}", 2.0, frame=_leant(), spins=True)
    r, level, ya, rs, ball = ORBIT[version][key], LEVEL[version][key], ARM[key], SLEEVE[key], BALL[key]
    collet = rs + 1.5 * PX
    top = level + ball

    # the sleeve, up to its wheel (a) or into the drum (b)
    if version == "a":
        yw = WHEEL_Y[key]
        teeth = TEETH[key][0]
        d.tube("y", (0, 0), ya + ARM_T, yw + ARM_T, rs, BRASS_D, sides=8)
        tone = STEEL if key == "mercury" else (BRASS, BRASS_D)[PLANETS.index(key) % 2]
        d.gear((0, 0), yw, yw + ARM_T, teeth, tone, phase=LAY_YAW - POSE[key],
               spokes=(0 if teeth < 12 else 5 if teeth < 15 else 6), bore=collet, collet=BRASS_D)
    else:
        d.tube("y", (0, 0), ya + ARM_T, MOVE_Y0 + PX, rs, BRASS_D, sides=8)

    # the arm: a collet on the sleeve, a flat bar that narrows outward, an eye where the rod hangs
    d.tube("y", (0, 0), ya, ya + ARM_T, collet, BRASS_D, sides=8)
    d.stud((-collet, ya + ARM_T / 2.0, 0.0), "-x")                             # the set screw
    mid = max(collet + 0.14, r * 0.42)
    d.box((collet - 0.01, ya, -1.5 * PX), (mid, ya + ARM_T, 1.5 * PX), BRASS, grain="x")
    d.box((mid, ya, -PX), (r + ROD, ya + ARM_T, PX), BRASS, grain="x")
    d.tube("y", (r, 0), ya - PX, ya, ROD + PX / 4.0, BRASS_D, sides=8)

    # the rod and the planet's seat
    d.tube("y", (r, 0), top - 0.02, ya - PX, ROD, BRASS, sides=8)
    d.tube("y", (r, 0), top - 0.03, top + 0.035, min(0.09, ball * 0.72), BRASS_D, sides=8)
    _planet(d, key, (r, level, 0.0), under)
    if key == "earth":
        _moon(d, version, r, level, under)

    # the hoop of its orbit, in the ring plane, clamped to the rod
    if version == "a" and key in HOOPS:
        _level_ring(d, under, r, HOOP, HOOP, COPPER, 2 * int(round(math.pi * r / 0.2)))
        d.box((r - 1.25 * PX, -1.5 * PX, -1.5 * PX), (r + 1.25 * PX, 1.5 * PX, 1.5 * PX), BRASS_D)
    return [d, under]


# --- what the fixed ring of either version hangs from ------------------------------------------------
def _hangers(d, radius, flat=False):
    """An iron spider under the works, over everything that turns, and three hangers down from the
    ends of its arms to a ring at `radius` (three, never four). Round rods with a brass foot on the
    ring; `flat` makes them straps, thin across and two texels wide along the ring, for a ring that
    has a planet passing close inside it."""
    d.tube("y", (0, 0), SPIDER_Y, MOVE_Y0, 0.30, IRON, sides=12)               # the spider's middle
    for a in STAYS:
        x, z = radius * math.cos(math.radians(a)), radius * math.sin(math.radians(a))
        if flat:
            d.spoke(a, 0.24, radius + STRAP / 2.0, SPIDER_Y, MOVE_Y0, 2.5 * PX, IRON)
            d.spoke(a, radius - STRAP / 2.0, radius + STRAP / 2.0, 1.5 * PX, SPIDER_Y, 2 * PX, IRON, grain="y")
            continue
        d.spoke(a, 0.24, radius + 0.07, SPIDER_Y, MOVE_Y0, 2.5 * PX, IRON)
        d.tube("y", (x, z), 1.5 * PX, MOVE_Y0 + PX, ROD, IRON, sides=6)
        d.tube("y", (x, z), 1.5 * PX, 3.5 * PX, 0.10, BRASS_D, sides=8)        # the foot on the band
        d.tube("y", (x, z), SPIDER_Y - PX, SPIDER_Y, 0.10, IRON_D, sides=8)


# --- version a: planar, the works open ------------------------------------------------------------
def _band_a():
    """The zodiac band: a channel of brass in the ring plane with a silvered scale between its two
    lips, twelve enamel plaques for the signs. It is the one fixed ring: it hangs on three iron rods
    from a spider under the works, outside everything that turns above the plane. Anchor: the
    centre, in the ring plane. Shown at scale 2."""
    d = _Draw("a_band", 2.0)
    r0, r1 = BAND
    d.ring("y", (0, 0, 0), r0 + PX / 2.0, PX, 3 * PX, BRASS_L, sides=72)       # the inner lip, towards the sun
    d.ring("y", (0, 0, 0), r1 - PX / 2.0, PX, 3 * PX, BRASS, sides=72)
    grad_circle(d.m, "y", (0, 0, 0), (r0 + r1) / 2.0 * d.u, (r1 - r0 - 2 * PX) * d.u, 2 * PX * d.u, BRASS,
                marks=36, signs=12, proud=0.75 * PX * d.u)
    _hangers(d, STAY_R)
    return d


def _pillars():
    return [(1.60, 0.0)] + [(0.84 * math.cos(math.radians(a)), 0.84 * math.sin(math.radians(a))) for a in (120.0, 240.0)]


def _plate(d, y0, y1, down):
    """One plate of the works: three arms from the middle, the long one over the lay shaft."""
    d.spoke(0.0, 0.0, 1.60, y0, y1, 4 * PX, BRASS)
    for a in (120.0, 240.0):
        d.spoke(a, 0.0, 0.84, y0, y1, 3 * PX, BRASS)
    d.tube("y", (0, 0), y0 - PX / 2.0, y1 + PX / 2.0, 0.27, BRASS_D, sides=12)
    d.tube("y", (LAY_A, 0), y0 - PX / 2.0, y1 + PX / 2.0, 0.15, BRASS_D, sides=8)
    side = "-y" if down else "y"
    for x, z in _pillars():
        d.tube("y", (x, z), y0 - PX / 4.0, y1 + PX / 4.0, 0.125, BRASS_L, sides=8)
        d.stud((x, y0 - PX / 4.0 if down else y1 + PX / 4.0, z), side)
    d.stud((LAY_A, y0 - PX / 2.0 if down else y1 + PX / 2.0, 0.0), side, mat=K.flat("brass", 5))


def _cage_a():
    """The frame of the works: two brass plates and three turned pillars. The lower plate carries the
    spider, the upper one the column; the lay shaft runs between them. Anchor: the centre, in the
    ring plane; +x points at the lay shaft. Shown at scale 2."""
    d = _Draw("a_cage", 2.0)
    y0, y1 = MOVE_Y0, MOVE_Y1 - 2 * PX
    _plate(d, y0, y0 + 2 * PX, True)
    _plate(d, y1, y1 + 2 * PX, False)
    lo, hi = y0 + 2 * PX, y1
    for x, z in _pillars():
        d.tube("y", (x, z), lo, hi, ROD, BRASS_L, sides=6)
        for a, b in ((lo, lo + PX), (hi - PX, hi)):
            d.tube("y", (x, z), a, b, 0.10, BRASS_D, sides=8)
        d.tube("y", (x, z), (lo + hi) / 2.0 - PX, (lo + hi) / 2.0 + PX, 0.09, BRASS_D, sides=8)
    return d


def _lay_a():
    """The lay shaft: a steel arbor with six wheels, each in mesh with the wheel of one sleeve. The
    two stacks are stepped cones, one the other way up from the other, and every pair shares the
    one distance between the shafts. Anchor: on its own axis, at the height of the ring plane (it
    takes the light of the planets' level, like the wheels it turns). Shown at scale 1."""
    d = _Draw("a_lay", 1.0)
    d.tube("y", (0, 0), MOVE_Y0 + PX, MOVE_Y1 - PX, ROD, IRON, sides=6)
    for i, key in enumerate(PLANETS):
        teeth = TEETH[key][1]
        y = WHEEL_Y[key]
        tone = STEEL if key == "saturn" else (BRASS_D, BRASS)[i % 2]
        # the main axis is LAY_YAW + 180 from here: a gap of this wheel looks at it
        d.gear((0, 0), y, y + ARM_T, teeth, tone, phase=LAY_YAW + 180.0 + 180.0 / teeth,
               spokes=(0 if teeth < 11 else 5 if teeth < 15 else 6), bore=0.14, collet=BRASS_D if teeth > 5 else STEEL)
    return d


# --- version b: tiered, armillary, the works shut ----------------------------------------------------
STRAP = 0.8 * PX                         # the hangers of version b are straps this thin
STRAP_R = R - STRAP / 2.0 - 0.004        # and stand on the outer lip of the equator ring, inside ORRERY_R


def _rings_b():
    """The two rings of the armillary and what they hang from: the level equator ring, its scale
    a row of short marks between two lips, the broad ecliptic band with its twelve signs, tilted
    twenty degrees and pinned to the equator at the two nodes, and the spider and three straps of
    _hangers(). Nothing stands under the sun or the planets: three stays from a boss under the sun,
    brass or iron, read from below as a three-pointed star in a ring (cr3 #63115). Anchor: the
    centre, in the ring plane. Shown at scale 2."""
    d = _Draw("b_rings", 2.0)
    e0, e1 = EQUATOR
    d.ring("y", (0, 0, 0), e0 + PX / 2.0, PX, 3 * PX, BRASS_L, sides=72)
    for y in (-PX, PX):
        d.ring("y", (0, y, 0), e1 - PX / 2.0, PX, PX, BRASS, sides=72)
    grad_circle(d.m, "y", (0, 0, 0), (e1 - PX / 2.0) * d.u, PX * d.u, PX * d.u, BRASS, marks=60)
    ec = ECLIPTIC
    with d.turned(("x", ec["tilt"]), about=(0, 0, 0)):                          # the north side up
        d.ring("y", (0, 0, 0), ec["radius"], ec["thick"], ec["width"], BRASS, sides=72)
        for i in range(12):
            a = 15.0 + 30.0 * i
            d.ring("y", (0, 0, 0), ec["radius"], ec["thick"] + 0.5 * PX, 2 * PX, ENAMEL, sides=60, arc=(a - 3.0, a + 3.0))
        for y in (-ec["width"] / 2.0 + PX / 4.0, ec["width"] / 2.0 - PX / 4.0):
            d.ring("y", (0, y, 0), ec["radius"], ec["thick"] + 0.5 * PX, PX / 2.0, BRASS_L, sides=72)
    for s in (-1.0, 1.0):                                                       # the pins at the nodes
        d.tube("x", (0.0, 0.0), *sorted((s * (ec["radius"] - 0.10), s * e1)), 0.09, BRASS_D, sides=8)
    _hangers(d, STRAP_R, flat=True)
    return d


def _drum_b():
    """The works shut away: a brass drum under the column, a band of enamel with twelve studs round
    its waist, a stepped lid. The sleeves of the arms go up into it. Anchor: the centre, in the ring
    plane. Shown at scale 1."""
    d = _Draw("b_drum", 1.0)
    y0 = MOVE_Y0
    d.tube("y", (0, 0), y0, y0 + PX, 0.52, BRASS_D, sides=12)
    d.tube("y", (0, 0), y0 + PX, y0 + 15 * PX, 0.47, BRASS, sides=12)
    d.tube("y", (0, 0), y0 + 6 * PX, y0 + 10 * PX, 0.485, ENAMEL, sides=12)
    for i in range(12):
        d.box((0.485 - 0.01, y0 + 7.5 * PX, -PX / 2.0), (0.485 + PX / 2.0, y0 + 8.5 * PX, PX / 2.0), K.flat("cream", 3),
              rot=("y", 30.0 * i, (0.0, 0.0, 0.0)))
    d.tube("y", (0, 0), y0 + 15 * PX, y0 + 16 * PX, 0.52, BRASS_D, sides=12)
    d.taper("y", (0, 0), y0 + 16 * PX, MOVE_Y1 - PX, 0.45, 0.27, BRASS, sides=12, steps=4)
    d.tube("y", (0, 0), MOVE_Y1 - PX, MOVE_Y1, 0.30, BRASS_D, sides=12)
    return d


# --- the model set -------------------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def _drawn():
    out = {}
    with _lit_from_below():
        made = [_hub(), _column(), *_sun(), _band_a(), _cage_a(), _lay_a(), _rings_b(), _drum_b()]
        for v in ("a", "b"):
            for key in PLANETS:
                made += _arm(v, key)
        for d in made:
            out[d.m.name] = d
    return out


def models():
    return {name: d.m for name, d in _drawn().items()}


def models_for(version):
    """The names build() places for one version, for a gallery or a count."""
    return [name for name, _pos, _yaw in placing(version)]


# --- placing -------------------------------------------------------------------------------------
def _lay_at():
    a = math.radians(LAY_YAW)
    return (CX + LAY_A * math.cos(a), RING_Y, CZ + LAY_A * math.sin(a))


def placing(version=VERSION):
    """Where every model of one version stands: [(model name, (x, y, z), yaw)], scene coordinates
    without an origin. The first six are the same in both versions: the hub, the column and the
    four models of the sun. Each arm is followed by the model of its undersides, on the same spot."""
    v, at = version, (CX, RING_Y, CZ)
    out = [("hub", (CX, HANG_Y - K.NUDGE, CZ), 0.0),             # in the air cell under the ceiling
           ("column", (CX, COLUMN_AT, CZ), 0.0)]
    out += [(name, at, 0.0) for name in ("sun", "sun_side0", "sun_side1", "sun_under")]
    if v == "a":
        out += [("a_band", at, 0.0), ("a_cage", at, LAY_YAW), ("a_lay", _lay_at(), 0.0)]
    else:
        out += [("b_rings", at, 0.0), ("b_drum", at, 0.0)]
    for key in PLANETS:
        out += [(f"{v}_arm_{key}", at, POSE[key]), (f"{v}_under_{key}", at, POSE[key])]
    return [(PREFIX + name, pos, yaw) for name, pos, yaw in out]


def moving(version=VERSION):
    """What turns, for the motion line: [dict(model, at, period, sense)]. `at` is the entity's place
    (scene coordinates without an origin), which is on the part's vertical axis; period is the ticks
    for one turn; sense is +1 for the way the planets go round (seen from above against the clock:
    the yaw of the display falls) and -1 for the lay shaft, which the wheels turn the other way.
    An arm and the model of its undersides are two entities on one spot that turn as one."""
    at = (CX, RING_Y, CZ)
    out = [dict(model=PREFIX + f"{version}_{part}_{key}", at=at, period=PERIOD[key], sense=1)
           for key in PLANETS for part in ("arm", "under")]
    if version == "a":
        out.append(dict(model=PREFIX + "a_lay", at=_lay_at(), period=LAY_TURN, sense=-1))
    return out


def build(canvas, origin=(0, 0, 0), version=VERSION):
    """Hang one orrery in the star hall and return the number of display entities. version "a" is
    planar, "b" the armillary bowl; the test scene builds both side by side, the review picks one."""
    drawn = _drawn()
    turns = {t["model"]: t["sense"] * t["period"] for t in moving(version)}
    n = 0
    for name, pos, yaw in placing(version):
        x, y, z = (pos[i] + origin[i] for i in range(3))
        canvas.add_entity(x, y, z, drawn[name].display(yaw))
        if name in turns:
            MK.spin(canvas, (0.0, 1.0, 0.0), turns[name])       # about the vertical, whatever the model's frame
        n += 1
    cell = (int(CX + origin[0]), int(RING_Y + origin[1]), int(CZ + origin[2]))
    K.offer_lights(canvas, [(cell, SUN_LIGHT)], f"machines/orrery:{version}")
    return n


# --- do the turning parts clear one another? ---------------------------------------------------------
CELL = PX / 8.0                          # the grid the sweeps are drawn on
REACH = 10                               # cells: gaps are measured up to this far
HUB_ZONE = 0.34                          # inside this radius the sleeves run one inside the other by design
TIGHT = PX / 3.0                         # two parts that pass closer than this are reported


def _matrix(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def _surface(model, scale, step=CELL):
    """Points over the faces of every box of a model, in blocks from its anchor, `step` apart."""
    k = scale / 16.0
    out = []
    for p in model.parts:
        lo, hi = np.array(p["lo"]), np.array(p["hi"])
        c, h = (lo + hi) / 2.0, (hi - lo) / 2.0
        axes = [np.linspace(-h[i], h[i], max(2, int(math.ceil(2.0 * h[i] * k / step)) + 1)) for i in range(3)]
        pts = []
        for i in range(3):
            j, l = [a for a in range(3) if a != i]
            g = np.stack(np.meshgrid(axes[j], axes[l], indexing="ij"), -1).reshape(-1, 2)
            for side in (-h[i], h[i]):
                f = np.zeros((len(g), 3))
                f[:, i], f[:, j], f[:, l] = side, g[:, 0], g[:, 1]
                pts.append(f)
        pts = np.concatenate(pts)
        if p["rot"]:
            pts = pts @ _matrix(p["rot"][0]).T
        out.append((pts + c) * k)
    return np.concatenate(out)


GRID = (int(math.ceil((R + 0.3) / CELL)), int(math.ceil((MOVE_Y0 + 1.2) / CELL)))    # rho 0..2.8, y -1.2..2.0


def sweep(name, pos, moves):
    """What a model standing at `pos` sweeps as it turns about the machine's axis, below the works:
    a grid of cells (rho from the axis, y from 1.2 under the ring plane), true where it touches.
    For a part that turns only what lies outside the nest of sleeves is kept."""
    pts = _drawn()[name].points(CELL)
    rho = np.hypot(pts[:, 0] + pos[0] - CX, pts[:, 2] + pos[2] - CZ)
    y = pts[:, 1] + pos[1] - RING_Y
    keep = (y < MOVE_Y0) & (y > -1.2) & (rho < R + 0.3)
    if moves:
        keep &= rho > HUB_ZONE
    grid = np.zeros(GRID, dtype=bool)
    grid[(rho[keep] / CELL).astype(int), ((y[keep] + 1.2) / CELL).astype(int)] = True
    return grid


def _near(grid):
    """For every cell, how many cells it is from the nearest true cell of `grid`, up to REACH + 1."""
    n = REACH
    wide = np.pad(grid, n)
    dist = np.where(grid, 0, n + 1)
    for k in range(1, n + 1):
        ring = np.zeros_like(grid)
        for dx in range(-k, k + 1):
            for dy in range(-k, k + 1):
                if (k - 1) ** 2 < dx * dx + dy * dy <= k * k:
                    ring |= wide[n + dx:n + dx + grid.shape[0], n + dy:n + dy + grid.shape[1]]
        dist = np.where(ring & (dist > k), k, dist)
    return dist


def clearances(version=VERSION):
    """The least distance in blocks between what one turning part sweeps and what every other part
    sweeps or stands in, below the works and outside the nest of sleeves: [(gap, part, other)],
    the tightest first, gaps measured up to REACH cells. Two parts that turn at different rates
    meet sooner or later at every angle, so a gap of nothing here is a planet going through a rod.
    The models of the sun count as one part, and so do an arm and the model of its undersides."""
    grids = {}
    for name, pos, _yaw in placing(version):
        short = name[len(PREFIX):]
        if short in ("hub", "column", "a_cage", "a_lay", "b_drum"):
            continue
        whole = "sun" if short.startswith("sun_") else short.replace("_under_", "_arm_")
        grid = sweep(name, pos, "arm_" in whole)
        grids[whole] = grids[whole] | grid if whole in grids else grid
    near = {short: _near(grid) for short, grid in grids.items() if "arm_" in short}
    out = []
    names = sorted(grids)
    for a in sorted(near):
        for b in names:
            if b == a or (b in near and b < a):
                continue
            k = int(near[a][grids[b]].min()) if grids[b].any() else REACH + 1
            out.append((max(0, k - 1) * CELL, a, b))
    return sorted(out)


def lowest(version=VERSION):
    """The lowest point of a version, as a height in the scene."""
    low = 1e9
    for name, pos, _yaw in placing(version):
        low = min(low, float(_drawn()[name].points(PX)[:, 1].min()) + pos[1])
    return low


def widest(version=VERSION):
    """The farthest any part of a version reaches from the axis, in blocks."""
    far = 0.0
    for name, pos, yaw in placing(version):
        pts = _drawn()[name].points(PX)
        off = K.turn(yaw, (1.0, 0.0, 0.0))
        x = pts[:, 0] * off[0] - pts[:, 2] * off[2] + pos[0] - CX
        z = pts[:, 0] * off[2] + pts[:, 2] * off[0] + pos[2] - CZ
        far = max(far, float(np.hypot(x, z).max()))
    return far


def _display_error(d, yaw):
    """How far a model's display is from what it is meant to show, in blocks: its matrix, read back
    as the engine reads it, against the frame (over a block of the model), and where the anchor
    lands against the entity."""
    a, off = _shown(d.display(yaw))
    r = math.radians(yaw)
    turn = np.array([[math.cos(r), 0.0, -math.sin(r)], [0.0, 1.0, 0.0], [math.sin(r), 0.0, math.cos(r)]])
    want = turn @ (np.eye(3) if d.g is None else d.g) * (d.scale / 16.0)
    anchor = off + a @ (np.array(d.m.anchor) + np.array(d.m.shift()))
    return max(float(np.abs(a - want).max()) * 16.0 / d.scale, float(np.abs(anchor).max()))


def _report():
    ok = True
    drawn = _drawn()
    framed = [d for d in drawn.values() if d.lit]
    dull = min(b for d in framed for b, _sure in d.lit)
    sure = min(s for d in framed for _b, s in d.lit)
    off = max(_display_error(drawn[name], yaw) for v in ("a", "b") for name, _pos, yaw in placing(v))
    ok = dull >= LIT and sure >= SURE and off < 1e-6
    print(f"faces lit as if they looked up: {sum(len(d.lit) for d in framed)} in {len(framed)} models; the dullest keeps "
          f"{dull:.3f} of its tone (limit {LIT}), the axis a face is filed under wins by {sure:.2f} at least "
          f"(limit {SURE}); the displays are off by {off:.1e} blocks at most")
    for v in ("a", "b"):
        gaps = clearances(v)
        low, far = lowest(v), widest(v)
        tight = [g for g in gaps if g[0] < TIGHT]
        ok = ok and not tight and low >= FLOOR_Y and far <= R + 1e-6
        print(f"version {v}: lowest point y {low:.3f} (limit {FLOOR_Y}), widest {far:.3f} (limit {R}); "
              f"{len(gaps)} pairs, {len(tight)} closer than {TIGHT:.3f}")
        for gap, a, b in gaps[:10]:
            print(f"    {gap:6.3f}  {a} / {b}")
    print("teeth and turns: " + ", ".join(f"{k} {TEETH[k][0]}:{TEETH[k][1]} {PERIOD[k]}" for k in PLANETS)
          + f"; lay shaft {LAY_TURN} the other way")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if _report() else 1)
