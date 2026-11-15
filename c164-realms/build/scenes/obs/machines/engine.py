"""machines/engine-dynamo: the steam engine of the power house, its flywheel, the belt and the dynamo
(plan/ART-PLAN.md 5.3, 7.2, 8; plan/parts/A5-machines.md 2.5; card
plan/packages/machines/engine-dynamo.md).

What it is. A horizontal mill engine with one cylinder, as a works of the 1890s would have bought
it. The cylinder lies in the east, next to the boilers; its piston rod drives a crosshead between
four slide bars, the connecting rod turns an overhung crank, and on the crankshaft, between two
bearings, runs a flywheel five blocks across whose lower third turns in a pit. The flywheel is the
belt wheel as well: a flat leather belt runs west from its rim to the small pulley of the dynamo,
one turn of the engine to three of the armature. The dynamo is of the two-pole kind with its
armature low between the pole pieces and two tall wound limbs under a yoke. On the side away from
the door an eccentric on the shaft works the slide valve in its chest, and a flyball governor
stands on the throttle over the chest, driven from the shaft by a cord. Steam comes in at the
flange beside the governor (STEAM_IN), which looks up, and leaves into the floor; the current
leaves at the two terminals on the dynamo's yoke (POWER_OUT). The pipe and the cables are the
props line's and the room's.

Where it stands. In the south half of the power house (site/powerhouse.ROOM), the engine's line
east-west: boilers in the north-east, engine in the south-east, dynamo in the south-west, where the
cable leaves the house. From the wicket in the north front the flywheel is seen full face, the
crank and the rods before it, the belt running off to the right onto the dynamo's pulley.

    x  the engine's line runs along x at z = LINE_Z; the crankshaft crosses it at x = SHAFT_X
    y  the floor is S.LOWER_GROUND; the shaft lies H above it
    z  the flywheel and the belt turn in the plane z = WHEEL_Z, over the pit (PIT)

Every model is drawn in the engine's own frame, in blocks: x from the shaft towards the cylinder,
y up from the floor, z from the engine's line towards the flywheel (south). Big pieces are shown at
scale 2 and small ones at scale 1, each with as many texels to its unit (px = scale): 16 px to the
block.

What moves (scenes/obs/motion/_kit.py; nothing runs every tick):
    flywheel   with the shaft, the crank and the eccentric, once in MK.ENGINE_REV, its top going
               away from the cylinder
    rod        the connecting rod: slides with the crosshead and tilts to stay on the crank pin
    crosshead  with the piston rod: slides
    eccentric  the eccentric's strap and rod: a small crank a quarter turn before the main one
    valve      the valve spindle the eccentric rod pushes: slides, a quarter of a stroke ahead
    governor   about its spindle, once in MK.GOVERNOR_REV
    armature   with commutator and pulley, once in MK.DYNAMO_REV, the way the belt takes it
The rest pose is the dead centre, the crank pin towards the cylinder, as the motion kit wants it.
The belt itself stands still (the motion line's ruling for this version): it is painted in lines
along its run and carries no mark, so between two turning wheels it does not read as standing.
A part that turns is painted with no light from above: its tones depend on how a face stands to the
axis only, so no painted highlight goes round with the wheel.

What is blocks. The machines are placed before the rooms and a wheel cannot turn in a floor, so
build() makes the set's own foundation: the pit (PIT: a slot one cell wide for the flywheel and
the belt's lower run), lined, and the iron base plate the set stands on (BASE), level with the
floor. The floor round it, the gratings and the rails at the pit are interiors/powerhouse's, which
reads PIT, BASE, KEEP_CLEAR and LIT_BY: the four cells the thirteen pieces take their light from
(a display entity is lit by the cell its anchor is in), to be lit alike.
"""
import contextlib
import functools
import math

import numpy as np

from artkit import models as M
from artkit.pixelart import Mat

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..motion import _kit as MK
from ..props import _kit as K

PREFIX = "mach_engine_"
PX = 1.0 / 16.0                         # a texel, in blocks: every length below is in blocks

# --- where it stands (scene coordinates) -------------------------------------------------------------
FLOOR = float(S.LOWER_GROUND)           # -6.0: where feet stand in the power house
SHAFT_X = 77.5                          # the crankshaft, which lies along z
LINE_Z = 35.0                           # the engine's line: cylinder, piston rod, crosshead, connecting rod
WHEEL_Z = 36.5                          # the plane the flywheel and the belt turn in: the middle of cell z 36

# --- the engine (its own frame, blocks) ----------------------------------------------------------------
H = 1.375                               # the shaft and the cylinder's axis over the floor: 22 px
WZ = WHEEL_Z - LINE_Z                   # 1.5: the flywheel's plane
WHEEL_R = 2.5                           # the flywheel: five blocks across (the card)
RIM_W = 0.5                             # its face, which carries the belt
RIM_T = 0.25                            # the rim's depth
SPOKES = 6                              # never four: four arms are a cross
HUB_R = 0.4375
SHAFT_R = 0.1875                        # a shaft of 6 px
CRANK = 1.0                             # shaft to crank pin: the stroke is twice this (the motion line's
ROD = 4.0                               # test station has the same crank and the same rod)
PIN = CRANK + ROD                       # 5.0: the crosshead pin at the dead centre, the rest pose
# along the shaft, from the door's side: the crank pin, the web, the main bearing, the eccentric, the
# governor's cord, the flywheel in its pit, the outboard bearing
WEB = (0.1875, 0.4375)
MAIN = (0.5, 0.875)
ECC_Z = (0.9375, 1.125)
CORD_Z = 1.15625
OUTER = (2.125, 2.625)
CYL = (5.75, 8.35)                      # the cylinder's barrel along x; its covers lie outside
CYL_R = 0.625                           # the lagged barrel: 20 px across
BED = (2.8, 8.7)                        # the bed under the slide bars and the cylinder, along x
BED_HALF = 0.75                         # half its width
BED_TOP = 0.625
CHEST = (6.0625, 8.0375)                # the valve chest along x, on the side away from the door: from the
#                                         middle of one of the barrel's bands to the middle of the other
CHEST_Z = (0.5625, 1.1875)
VALVE_Z = (ECC_Z[0] + ECC_Z[1]) / 2.0   # 1.031: the plane of the eccentric rod and the valve spindle
ECC = 0.1875                            # the eccentric's throw
ECC_R = 0.3125                          # its sheave
ECC_LEAD = 90.0                         # degrees it stands before the crank
VALVE_PIN = 4.9                         # where the eccentric rod takes the valve spindle, at rest
ECC_ROD = math.hypot(VALVE_PIN, ECC)    # the eccentric rod, from the sheave's middle to that pin
GOV_X, GOV_Z = 7.05, 0.875              # the governor's spindle, over the middle of the chest
GOV_Y = H + 1.0                         # where its turning part begins
GOV_PULLEY = (GOV_X, H + 0.875)         # the cord's pulley on the governor's bracket
INLET = (7.9, H + 0.9375, GOV_Z)        # the middle of the steam flange, which looks up

# --- the dynamo (same frame) ---------------------------------------------------------------------------
DYN_X = -5.5                            # its shaft, parallel to the engine's
DYN_H = 1.0
PULLEY_R = WHEEL_R * MK.DYNAMO_REV / MK.ENGINE_REV      # 0.833: the belt's one to three
D_NEAR = (1.9375, 2.1875)               # its bearing between the pulley and the armature
ARM = (2.375, 3.125)                    # the armature, between the pole pieces
ARM_R = 0.4375
COMM = (3.125, 3.4375)                  # the commutator
D_FAR = (3.5625, 3.8125)                # the bearing at the commutator's end
DYN_Z = (ARM[0] + ARM[1]) / 2.0         # 2.75: the middle of the magnet
LIMB = 0.59375                          # the two limbs stand this far either side of the shaft
YOKE_Y = (2.5, 2.75)                    # the yoke that ties their heads

# --- the belt --------------------------------------------------------------------------------------------
BELT_W = 0.375                          # 6 px of leather on a face of 8
BELT_T = PX

# --- the foundation (cells, scene coordinates) ------------------------------------------------------------
# The pit: {(x, z): how many blocks deep}. One cell wide. The flywheel needs two blocks under its
# middle and one at its ends; the belt's lower run leaves the wheel below the floor and comes up
# only at the pulley, so the slot runs on west to it.
PIT = {(x, int(WHEEL_Z)): (2 if 76 <= x <= 78 else 1) for x in range(72, 80)}
PIT_LINING = B.TUFF_BRICK.block
# The base plate: the floor's own course under the engine and under the dynamo, in riveted iron.
BASE = sorted(({(x, z) for x in range(76, 87) for z in range(34, 38)}
               | {(x, z) for x in range(70, 74) for z in range(36, 39)}) - set(PIT))
BASE_PLATE = B.IRON_RIVETED.block
LAMP_LEVEL = 6                          # what the pilot lamp on the dynamo hands to the sky line


def _scene(p, origin=(0, 0, 0)):
    """A point of the engine's frame in scene coordinates."""
    return (SHAFT_X + p[0] + origin[0], FLOOR + p[1] + origin[1], LINE_Z + p[2] + origin[2])


# --- for the others (scene coordinates, the set at origin (0, 0, 0)) ----------------------------------------
STEAM_IN = _scene(INLET)                # (85.4, -3.6875, 35.875): the pipe comes down on it
EXHAUST = _scene((GOV_X, 0.0, GOV_Z))   # where the exhaust goes into the floor: nothing to connect
POWER_OUT = (_scene((DYN_X - LIMB, YOKE_Y[1] + 0.3125, DYN_Z)),
             _scene((DYN_X + LIMB, YOKE_Y[1] + 0.3125, DYN_Z)))         # the two terminals' tops
# for motion/sound: the stroke is heard at the cylinder, once a turn; the hum at the dynamo
STROKE_AT = _scene(((CYL[0] + CYL[1]) / 2.0, H, 0.0))
HUM_AT = _scene((DYN_X, DYN_H, DYN_Z))
# Boxes (x0, y0, z0, x1, y1, z1) in which something of the set stands or moves: nothing else goes there.
KEEP_CLEAR = (
    _scene((2.7, 0.0, -0.9)) + _scene((8.9, 2.6, 1.3)),             # bed, slide bars, cylinder, valve chest
    _scene((6.3, 2.0, 0.2)) + _scene((8.3, 3.6, 1.6)),              # the governor and the steam flange
    _scene((-1.4, 0.0, -0.4)) + _scene((2.8, 2.8, 1.0)),            # the crank's sweep
    _scene((-2.7, -2.0, 1.0)) + _scene((2.7, 4.0, 2.75)),           # flywheel and its bearings
    _scene((-6.5, -1.0, 1.0)) + _scene((-2.7, 4.0, 2.0)),           # the belt
    _scene((-6.9, 0.0, 1.0)) + _scene((-4.1, 3.3, 4.0)),            # the dynamo
)

# --- materials (the palette's, and nothing else) -----------------------------------------------------------
IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
IRON_L = P.mat("iron", base=4)                  # planed faces
STEEL = P.mat("iron", base=5, noise=0.10)       # bright steel: rods, shaft, slide bars
BRASS = P.mat("brass")
BRASS_D = P.mat("brass_dark")
COPPER = P.mat("old_copper")
PORCELAIN = P.mat("porcelain")
RED = P.mat("signal")


class _Belting(Mat):
    """Leather as a running belt shows it: its tones lie in lines along the run, the two edges worn
    light and the middle dark where the pulleys' crown rubs, and nothing across it. In this version
    the belt stands still while both its wheels turn (plan/parts/motion.md 12.4), so nothing on it
    may tell where along its run a point is: no joint, no lacing, no speck."""

    def levels(self, w, h, grain, seed):
        lv = np.full((h, w), self.base, dtype=np.int32)
        if grain == "cap":
            return lv
        n = h if grain == "u" else w
        across = np.zeros(n, dtype=np.int32)
        if n >= 5:
            across[0] = across[-1] = 1
            across[n // 2 - 1 + n % 2:n // 2 + 1] = -1
        return lv + (across[:, None] if grain == "u" else across[None, :])


class _Winding(Mat):
    """Wire wound close, turn beside turn: one texel a turn, light and dark by turns, the wire
    running with the grain. Nothing else on it: a coil is the same all the way round."""

    def levels(self, w, h, grain, seed):
        lv = np.full((h, w), self.base, dtype=np.int32)
        if grain == "cap":
            return lv
        turns = np.arange(h if grain == "u" else w, dtype=np.int32) % 2
        return lv + (turns[:, None] if grain == "u" else turns[None, :])


LEATHER = _Belting("dark_wood~belting", P.RAMPS["dark_wood"], bevel=0, base=2)
WOUND = _Winding("old_copper~wound", P.RAMPS["old_copper"], bevel=0, base=1)     # varnished coils
BARS = _Winding("old_copper~bars", P.RAMPS["old_copper"], bevel=0, base=3)       # the commutator, worn bright
CORD = P.mat("dark_wood", kind="flat", bevel=0, base=3)
STUD = P.mat("iron", kind="flat", bevel=0, base=5)
EDGE = P.mat("iron", kind="flat", bevel=0, base=5)       # an edge turned bright: a wheel's rim
STUD_BRASS = P.mat("brass", kind="flat", bevel=0, base=4)
GLOW = K.flat("glow", 3)
GLOW_DIM = K.flat("glow", 1)

# Where each piece's entity stands (the engine's frame); its model is drawn round this point. A
# display entity is lit as a whole, by the cell its entity stands in, so pieces that touch must
# stand in one cell or a step of light shows where they meet. A static piece may stand anywhere; a
# piece that turns stands on its axis, a rod on the axis of its sliding pin. That leaves four cells
# (LIT_BY): the engine's, at the crosshead; the governor's; the flywheel's, on the shaft; the
# dynamo's. The room lights those four alike and the set is one machine.
_ENGINE = (PIN, H, 0.5)
_WHEEL = (0.0, H, WZ)
_DYNAMO = (DYN_X, DYN_H, DYN_Z)
AT = {
    "bed": _ENGINE,
    "cylinder": _ENGINE,
    "crosshead": _ENGINE,
    "rod": _ENGINE,
    "eccentric": (VALVE_PIN, H, 0.5),
    "valve": (VALVE_PIN, H, 0.5),
    "governor": (GOV_X, H, GOV_Z),
    "frame": _WHEEL,
    "flywheel": _WHEEL,
    "lap": _WHEEL,
    "belt": _WHEEL,
    "dynamo": _DYNAMO,
    "armature": _DYNAMO,
}
ANCHORS = {name: _scene(p) for name, p in AT.items()}
# the cells the pieces take their light from: {cell: the pieces that stand in it}
LIT_BY = {}
for _name, _p in ANCHORS.items():
    LIT_BY.setdefault(tuple(int(math.floor(v)) for v in _p), []).append(_name)


@contextlib.contextmanager
def _lit_along(axis):
    """artkit paints the tone steps of tubes, rings and balls for a light from above (models.LIGHT).
    On a part that turns, that highlight would go round with it. Painted for a light along its axis,
    the part's tones are the same all the way round, and the game's own shading does the rest."""
    keep = M.LIGHT
    M.LIGHT = tuple(float(v) for v in axis)
    try:
        yield
    finally:
        M.LIGHT = keep


class _Draw:
    """A model drawn in blocks, in the engine's frame, round the point AT[name], where its entity
    stands. artkit's unit is 1/16 block of a model shown at scale 1; a model shown at scale s is
    drawn s times smaller with s texels to the unit."""

    def __init__(self, name, scale=2.0):
        self.at = tuple(float(v) for v in AT[name])
        self.scale = float(scale)
        self.u = 16.0 / self.scale
        self.m = M.Model(PREFIX + name, px=self.scale)

    def p(self, v):
        return tuple((v[i] - self.at[i]) * self.u for i in range(3))

    def _line(self, axis, c):
        k = M.AXES.index(axis)
        o1, o2 = [i for i in range(3) if i != k]
        return k, ((c[0] - self.at[o1]) * self.u, (c[1] - self.at[o2]) * self.u)

    def box(self, a, b, mat, rot=None, **kw):
        if rot is not None:
            rot = (rot[0], rot[1], self.p(rot[2]))
        self.m.box(self.p(a), self.p(b), mat, rot=rot, **kw)

    def tube(self, axis, c, a0, a1, radius, mat, **kw):
        """c: the two other coordinates of the centre line, in the order of the axes."""
        k, c = self._line(axis, c)
        self.m.tube(axis, c, (a0 - self.at[k]) * self.u, (a1 - self.at[k]) * self.u, radius * self.u, mat, **kw)

    def taper(self, axis, c, a0, a1, r0, r1, mat, **kw):
        k, c = self._line(axis, c)
        self.m.taper(axis, c, (a0 - self.at[k]) * self.u, (a1 - self.at[k]) * self.u, r0 * self.u, r1 * self.u,
                     mat, **kw)

    def ring(self, axis, centre, radius, thick, width, mat, **kw):
        self.m.ring(axis, self.p(centre), radius * self.u, thick * self.u, width * self.u, mat, **kw)

    def arc(self, centre, radius, thick, width, a0, a1, mat, steps=None, **kw):
        """Part of a ring about z, from a0 to a1 degrees (from +x towards +y), ending exactly there:
        Model.ring keeps to whole sides."""
        steps = steps or max(1, int(math.ceil((a1 - a0) / 11.25)))
        step = (a1 - a0) / steps
        half = (radius + thick / 2.0) * math.tan(math.radians(step) / 2.0)
        cx, cy, cz = centre
        self.m._n += 1
        seed = self.m._n
        for s in range(steps):
            self.box((cx + radius - thick / 2.0, cy - half, cz - width / 2.0),
                     (cx + radius + thick / 2.0, cy + half, cz + width / 2.0), mat,
                     rot=("z", a0 + step * (s + 0.5), centre), seed=seed, grain="y", **kw)

    def ball(self, centre, radius, mat, **kw):
        self.m.ball(self.p(centre), radius * self.u, mat, **kw)

    def rod(self, a, b, radius, mat, **kw):
        self.m.rod(self.p(a), self.p(b), radius * self.u, mat, **kw)

    def beam(self, a, b, width, height, mat, **kw):
        self.m.beam(self.p(a), self.p(b), width * self.u, height * self.u, mat, **kw)

    def stud(self, p, out="y", mat=STUD, size=2 * PX):
        """A bolt head: `size` square, half a texel proud. p is the middle of its foot; `out` the
        way the face it sits on looks ("x", "-x", "y", ...)."""
        k = M.AXES.index(out[-1])
        lo, hi = [v - size / 2.0 for v in p], [v + size / 2.0 for v in p]
        lo[k], hi[k] = sorted((p[k], p[k] + (-PX / 2.0 if out.startswith("-") else PX / 2.0)))
        self.box(lo, hi, mat)

    def oil_cup(self, x, y, z):
        """A brass oil cup that stands on (x, y, z)."""
        self.tube("y", (x, z), y, y + 0.125, 0.03125, BRASS, sides=4)
        self.tube("y", (x, z), y + 0.125, y + 0.25, 0.09375, BRASS, sides=8)


def _tangents(c1, r1, c2, r2):
    """The two straight runs of an open belt from the wheel at c1 to the wheel at c2 (points (x, y),
    r1 >= r2): [(its end on the first wheel, its end on the second, the angle both ends are seen at
    from their centres)]."""
    dx, dy = c2[0] - c1[0], c2[1] - c1[1]
    beta = math.degrees(math.atan2(dy, dx))
    phi = math.degrees(math.asin((r1 - r2) / math.hypot(dx, dy)))
    out = []
    for sign in (1.0, -1.0):
        a = beta - sign * (90.0 - phi)
        n = (math.cos(math.radians(a)), math.sin(math.radians(a)))
        out.append(((c1[0] + r1 * n[0], c1[1] + r1 * n[1]), (c2[0] + r2 * n[0], c2[1] + r2 * n[1]), a))
    return out


def _laps(runs):
    """Where the belt lies on the two wheels, as arcs (from, to) in degrees: on the first wheel
    round its far side, on the second round its far side."""
    (_a1, _b1, plus), (_a2, _b2, minus) = runs
    return (minus, plus + 360.0), (plus, minus)


BELT = _tangents((0.0, H), WHEEL_R + BELT_T / 2.0, (DYN_X, DYN_H), PULLEY_R + BELT_T / 2.0)
CORD_FROM = 0.25                        # the cord's pulley on the crankshaft
CORD_TO = 0.25                          # and the one on the governor: as big, so that the two runs are parallel
CORD_RUNS = _tangents((0.0, H), CORD_FROM + PX / 2.0, GOV_PULLEY, CORD_TO + PX / 2.0)


# --- the shaft and what turns with it ------------------------------------------------------------------------
def _flywheel():
    """Flywheel, shaft, crank and eccentric: one piece, its entity on the axis in the wheel's
    plane. The crank pin points at the cylinder: the dead centre."""
    d = _Draw("flywheel")
    c = (0.0, H, WZ)
    with _lit_along((0.0, 0.0, -1.0)):
        face = IRON_L.variant(0, "along")                                             # the belt keeps the rim's face bright
        side = IRON_L.variant(0, 0)
        d.ring("z", c, WHEEL_R - RIM_T / 2.0, RIM_T, RIM_W, IRON, sides=32, faces={"e": face, "n": side, "s": side})
        for s in (-1.0, 1.0):                                                         # the rim's edge, turned bright
            d.ring("z", (0.0, H, WZ + s * (RIM_W / 2.0 + PX / 4)), WHEEL_R - PX / 2, PX, PX / 2, EDGE, sides=32)
        d.ring("z", c, WHEEL_R - RIM_T - PX, 2 * PX, 0.25, IRON_D, sides=32)           # the rib inside the rim
        for i in range(SPOKES):
            a = 30.0 + 360.0 * i / SPOKES
            # an arm in two lengths, stouter at the hub
            d.box((HUB_R - PX, H - 0.1875, WZ - 0.125), (1.25, H + 0.1875, WZ + 0.125), IRON, rot=("z", a, c), grain="x")
            d.box((1.25, H - 0.125, WZ - 0.09375), (WHEEL_R - RIM_T - PX, H + 0.125, WZ + 0.09375), IRON,
                  rot=("z", a, c), grain="x")
        for a in (0.0, 180.0):                                                        # the wheel is cast in two halves:
            for s in (-1.0, 1.0):                                                     # their joints inside the rim
                za, zb = sorted((WZ + s * 0.125, WZ + s * 0.25))
                d.box((WHEEL_R - RIM_T - 0.3125, H - 0.1875, za), (WHEEL_R - RIM_T - PX, H + 0.1875, zb), IRON_L,
                      rot=("z", a, c))
                for y in (H - 0.09375, H + 0.09375):
                    d.box((WHEEL_R - RIM_T - 0.25, y - PX, zb if s > 0 else za - PX / 2),
                          (WHEEL_R - RIM_T - 0.125, y + PX, zb + PX / 2 if s > 0 else za), STUD, rot=("z", a, c))
        d.tube("z", (0.0, H), WZ - 0.25, WZ + 0.25, HUB_R, IRON, sides=12)
        d.tube("z", (0.0, H), WZ - 0.3125, WZ + 0.3125, 0.3125, IRON_L, sides=12)       # the boss, keyed on
        for i in range(SPOKES):
            a = math.radians(360.0 * i / SPOKES)
            d.stud((0.375 * math.cos(a), H + 0.375 * math.sin(a), WZ - 0.25), "-z", STUD)
        d.tube("z", (0.0, H), WEB[0] - PX / 2, OUTER[1] + 0.125, SHAFT_R, STEEL, sides=8)  # its end shows in the crank
        # the cord's pulley: its far cheek inside the wheel's boss, its near one short of the eccentric's strap
        d.tube("z", (0.0, H), CORD_Z - 0.75 * PX, CORD_Z + PX, CORD_FROM, IRON_L, sides=12)
        # the eccentric: a sheave that sits off the axis, before the crank
        a = math.radians(ECC_LEAD)
        d.tube("z", (ECC * math.cos(a), H + ECC * math.sin(a)), ECC_Z[0] + PX / 2, ECC_Z[1] - PX / 2, ECC_R, IRON_L,
               sides=12)
        # the crank: a web from the shaft to the pin, a balance weight behind the shaft. The two
        # bosses stand proud of the web and of the weight, and the weight's middle of its wings:
        # no two of their faces lie in one plane
        z0, z1 = WEB
        q = PX / 4
        d.box((0.0, H - 0.21875, z0 + q), (CRANK, H + 0.21875, z1 - q), IRON, grain="x")
        d.tube("z", (0.0, H), z0, z1, 0.34375, IRON, sides=12)
        d.tube("z", (CRANK, H), z0, z1, 0.25, IRON, sides=12)
        for turn, inset in ((-28.0, 2 * q), (0.0, q), (28.0, 3 * q)):                 # the weight: a fan of three
            d.box((-0.8125, H - 0.21875, z0 + inset), (-0.1875, H + 0.21875, z1 - inset), IRON_D,
                  rot=("z", turn, (0.0, H, 0.0)), grain="x")
        d.tube("z", (CRANK, H), -0.1875, z0, 0.125, STEEL, sides=8)                   # the pin
        d.tube("z", (CRANK, H), -0.25, -0.1875, 0.1875, BRASS, sides=8)               # its collar
    return d


def _rod():
    """The connecting rod, from the crosshead pin (where its entity stands) to the crank pin."""
    d = _Draw("rod")
    t = 0.09375                                                                       # half its thickness: 3 px in all
    # the big end: a strap round two brasses, its oil cup on top
    d.box((CRANK - 0.3125, H - 0.25, -t), (CRANK + 0.3125, H + 0.25, t), IRON_L)
    d.box((CRANK - 0.1875, H - 0.1875, -t - PX / 2), (CRANK + 0.1875, H + 0.1875, t + PX / 2), BRASS)
    d.box((CRANK + 0.3125, H - 0.1875, -t), (CRANK + 0.4375, H + 0.1875, t), IRON)
    d.tube("y", (CRANK, 0.0), H + 0.25, H + 0.375, 0.0625, BRASS, sides=4)
    # the shank swells towards the crank
    d.box((CRANK + 0.4375, H - 0.125, -t + PX / 2), (2.75, H + 0.125, t - PX / 2), STEEL, grain="x")
    d.box((2.75, H - 0.09375, -t + PX / 2), (PIN - 0.1875, H + 0.09375, t - PX / 2), STEEL, grain="x")
    # the small end
    d.box((PIN - 0.1875, H - 0.1875, -t), (PIN + 0.1875, H + 0.1875, t), IRON_L)
    d.box((PIN - 0.09375, H - 0.09375, -t - PX / 2), (PIN + 0.09375, H + 0.09375, t + PX / 2), BRASS)
    return d


def _crosshead():
    """Crosshead and piston rod; the entity stands on the crosshead pin."""
    d = _Draw("crosshead")
    d.box((PIN - 0.28125, H - 0.25, -0.1875), (PIN + 0.28125, H + 0.25, 0.1875), IRON)
    for s in (-1.0, 1.0):                                                             # the slippers between the bars
        za, zb = sorted((s * 0.1875, s * 0.4375))
        d.box((PIN - 0.3125, H - 0.25, za), (PIN + 0.3125, H + 0.25, zb), IRON_L)
        d.tube("z", (PIN, H), *sorted((s * 0.4375, s * 0.5)), 0.09375, BRASS, sides=8)    # the pin's ends
    d.oil_cup(PIN, H + 0.25, 0.0)                                                     # between the two upper bars
    d.tube("x", (H, 0.0), PIN + 0.28125, PIN + 2.7, 0.09375, STEEL, sides=8)          # the piston rod
    d.tube("x", (H, 0.0), PIN + 0.28125, PIN + 0.40625, 0.15625, IRON, sides=8)       # its boss on the crosshead
    return d


def _eccentric():
    """The eccentric's strap and its rod, drawn as they stand when the crank is at the dead centre:
    the sheave's middle straight over the shaft, the rod leaning down to the valve spindle's pin,
    where the entity stands."""
    d = _Draw("eccentric")
    a = math.radians(ECC_LEAD)
    ex, ey = ECC * math.cos(a), H + ECC * math.sin(a)                                 # the sheave's middle, at rest
    d.ring("z", (ex, ey, VALVE_Z), ECC_R + 0.625 * PX, 1.25 * PX, ECC_Z[1] - ECC_Z[0], BRASS, sides=16)
    tilt = math.degrees(math.atan2(H - ey, VALVE_PIN - ex))
    with d.m.turned(("z", tilt), about=d.p((ex, ey, VALVE_Z))):
        d.box((ex + ECC_R + PX, ey - 0.09375, VALVE_Z - 0.0625), (ex + ECC_R + 0.25, ey + 0.09375, VALVE_Z + 0.0625), IRON_L)
        d.box((ex + ECC_R + 0.25, ey - 0.0625, VALVE_Z - 0.03125), (ex + ECC_ROD - 0.09375, ey + 0.0625, VALVE_Z + 0.03125),
              STEEL, grain="x")
        d.box((ex + ECC_ROD - 0.09375, ey - 0.09375, VALVE_Z - 0.03125), (ex + ECC_ROD + 0.09375, ey + 0.09375, VALVE_Z + 0.03125),
              IRON_L)                                                                 # its eye on the pin
    return d


def _valve():
    """The valve spindle: from the pin the eccentric rod takes it by, through its guide, into the
    gland of the chest. The entity stands on the pin."""
    d = _Draw("valve")
    for s in (-1.0, 1.0):                                                             # the fork round the rod's eye
        za, zb = sorted((VALVE_Z + s * 0.03125, VALVE_Z + s * 0.09375))
        d.box((VALVE_PIN - 0.09375, H - 0.09375, za), (VALVE_PIN + 0.125, H + 0.09375, zb), BRASS)
    d.box((VALVE_PIN + 0.125, H - 0.09375, VALVE_Z - 0.09375), (VALVE_PIN + 0.21875, H + 0.09375, VALVE_Z + 0.09375), BRASS)
    d.tube("x", (H, VALVE_Z), VALVE_PIN + 0.21875, CHEST[0] + 0.4, 0.0625, STEEL, sides=4)
    return d


def _governor():
    """What turns of the governor: spindle, arms, the two balls and the sleeve they lift."""
    x, z, y = GOV_X, GOV_Z, GOV_Y
    d = _Draw("governor", scale=1.0)
    with _lit_along((0.0, 1.0, 0.0)):
        d.tube("y", (x, z), y, y + 0.875, 0.03125, STEEL, sides=4)
        d.tube("y", (x, z), y + 0.8125, y + 0.9375, 0.0625, BRASS, sides=8)           # the head the arms hang from
        d.tube("y", (x, z), y + 0.9375, y + 1.0, 0.03125, BRASS, sides=4)
        d.tube("y", (x, z), y + 0.1875, y + 0.3125, 0.0625, BRASS, sides=8)           # the sleeve
        for s in (-1.0, 1.0):
            ball = (x + s * 0.375, y + 0.4375, z)
            d.rod((x + s * 0.03125, y + 0.875, z), ball, 0.02, STEEL, sides=4)
            d.rod((x + s * 0.0625, y + 0.25, z), (x + s * 0.3, y + 0.4, z), 0.02, STEEL, sides=4)
            d.ball(ball, 0.15625, RED, sides=8, layers=4)
    return d


def _armature():
    """What turns of the dynamo: shaft, belt pulley, armature and commutator."""
    d = _Draw("armature")
    c = (DYN_X, DYN_H)
    with _lit_along((0.0, 0.0, -1.0)):
        d.tube("z", c, WZ - 0.3125, D_FAR[1] + 0.09375, 0.09375, STEEL, sides=8)
        d.tube("z", c, ARM[0] + PX, ARM[1] - PX, ARM_R, WOUND, sides=12, grain="z")   # the wound drum
        for z in (ARM[0] + 0.125, ARM[1] - 0.1875):
            d.tube("z", c, z, z + 0.0625, ARM_R + PX / 2, BRASS_D, sides=12)          # its binding bands
        d.tube("z", c, COMM[0], COMM[1], 0.25, BARS, sides=12, grain="z")             # the commutator's bars
        d.tube("z", c, COMM[1], COMM[1] + 0.0625, 0.28125, BRASS_D, sides=12)
        # the pulley: a crowned face on six arms
        face = IRON_L.variant(0, "along")
        side = IRON_L.variant(0, 0)
        d.ring("z", (DYN_X, DYN_H, WZ), PULLEY_R - 0.0625, 0.125, RIM_W, IRON, sides=20,
               faces={"e": face, "n": side, "s": side})
        for s in (-1.0, 1.0):
            d.ring("z", (DYN_X, DYN_H, WZ + s * (RIM_W / 2.0 + PX / 4)), PULLEY_R - PX / 2, PX, PX / 2, EDGE, sides=20)
        for i in range(SPOKES):
            d.box((DYN_X + 0.1875, DYN_H - 0.0625, WZ - 0.0625), (DYN_X + PULLEY_R - 0.125, DYN_H + 0.0625, WZ + 0.0625),
                  IRON, rot=("z", 360.0 * i / SPOKES, (DYN_X, DYN_H, WZ)), grain="x")
        d.tube("z", c, WZ - 0.25, WZ + 0.25, 0.21875, IRON, sides=8)
    return d


# --- what stands still ---------------------------------------------------------------------------------------
def _cord(d, x0, x1):
    """The governor's cord between x0 and x1: the two thin runs from the shaft's pulley to the
    governor's. It is drawn into the pieces it passes over."""
    for a, b, _angle in CORD_RUNS:
        t0 = (max(x0, a[0]) - a[0]) / (b[0] - a[0])
        t1 = (min(x1, b[0]) - a[0]) / (b[0] - a[0])
        if t1 <= t0:
            continue
        p = [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, CORD_Z) for t in (t0, t1)]
        d.beam(p[0], p[1], PX, PX, CORD)


def _bed():
    """The bed: a box of cast iron under the cylinder and the slide bars, which it carries."""
    d = _Draw("bed")
    x0, x1 = BED
    w = BED_HALF
    d.box((x0, 0.0, -w), (x1, 0.125, w), IRON_D)                                      # the sole
    d.box((x0 + PX, 0.125, -w + 0.125), (x1 - PX, BED_TOP - 0.125, w - 0.125), IRON)
    d.box((x0, BED_TOP - 0.125, -w), (x1, BED_TOP, w), IRON_L)                        # the planed top
    n = 6
    for i in range(n + 1):                                                            # ribs, and a bolt at the foot of each
        x = x0 + 0.125 + (x1 - x0 - 0.25) * i / n
        for s in (-1.0, 1.0):
            za, zb = sorted((s * (w - 0.125), s * (w - PX)))
            d.box((x - PX, 0.125, za), (x + PX, BED_TOP - 0.125, zb), IRON)
            za, zb = sorted((s * (w - PX), s * w))
            d.box((x - PX, 0.125, za), (x + PX, 0.125 + PX / 2, zb), STUD)            # the bolt at the rib's foot
    # the four slide bars and the yoke that holds their crank end
    gx = (BED[0] + 0.0625, CYL[0] - 0.125)
    for s in (-1.0, 1.0):
        za, zb = sorted((s * 0.21875, s * 0.46875))
        for y0, y1 in ((H + 0.25, H + 0.375), (H - 0.375, H - 0.25)):
            d.box((gx[0] + 0.125, y0, za), (gx[1], y1, zb), STEEL, grain="x")         # from the yoke's post
        d.box((gx[0] - 0.0625, BED_TOP, za), (gx[0] + 0.125, H + 0.4375, zb), IRON)   # a post of the yoke
        d.box((gx[1] - 0.25, BED_TOP, za), (gx[1], H - 0.375, zb), IRON)              # a block under the cylinder end
    d.box((gx[0] - 0.0625, H + 0.4375, -0.46875), (gx[0] + 0.125, H + 0.5625, 0.46875), IRON)     # the yoke's head
    # the guide of the valve spindle, on an arm from the bed's far side: beyond where the spindle's
    # fork comes to at the end of its travel (the pin goes ECC either way)
    gv = VALVE_PIN + 0.21875 + ECC + 0.09375
    d.box((gv, BED_TOP - 0.125, w), (gv + 0.1875, BED_TOP, VALVE_Z + 0.125), IRON)
    d.box((gv, BED_TOP, VALVE_Z - 0.125), (gv + 0.1875, H + 0.125, VALVE_Z + 0.125), IRON)
    d.tube("x", (H, VALVE_Z), gv - 0.03125, gv + 0.21875, 0.09375, BRASS, sides=8)
    _cord(d, BED[0] + 0.0625, 99.0)
    return d


def _plummer(d, z0, z1):
    """A bearing pedestal on the shaft, between z0 and z1."""
    zm = (z0 + z1) / 2.0
    d.box((-0.625, 0.0, z0 - PX), (0.625, 0.125, z1 + PX), IRON_D)
    d.box((-0.5, 0.125, z0), (0.5, 0.5, z1), IRON)
    d.box((-0.375, 0.5, z0), (0.375, H - 0.125, z1), IRON)
    d.tube("z", (0.0, H), z0 - PX / 2, z1 + PX / 2, 0.375, IRON, sides=12)            # the housing, proud of its foot
    d.tube("z", (0.0, H), z0 - PX, z1 + PX, 0.28125, BRASS, sides=12)                 # the brasses show at its ends
    d.box((-0.3125, H + 0.3125, z0 + PX), (0.3125, H + 0.4375, z1 - PX), IRON_L)      # the cap
    for sx in (-0.21875, 0.21875):
        d.stud((sx, H + 0.4375, zm), "y")
    d.oil_cup(0.0, H + 0.4375, zm)
    for sx in (-0.5625, 0.5625):
        d.stud((sx, 0.125, zm), "y")


def _frame():
    """The two bearings of the shaft and the girder that ties the main bearing to the bed."""
    d = _Draw("frame")
    _plummer(d, *MAIN)
    _plummer(d, *OUTER)
    z0, z1 = MAIN
    d.box((0.625, 0.0, z0 - PX), (BED[0], 0.125, z1 + PX), IRON_D)                    # between the two soles
    d.box((0.5, 0.125, z0 + PX), (BED[0] + 0.0625, 0.75, z1 - PX), IRON)
    d.box((0.5, 0.75, z0), (BED[0] + 0.0625, 0.875, z1), IRON_L)
    for x in (1.0, 1.6, 2.2):
        d.stud((x, 0.125, z0 - PX / 2), "y")
    # the cord round the shaft's pulley and as far as the bed
    lap, _far = _laps(CORD_RUNS)
    d.arc((0.0, H, CORD_Z), CORD_FROM + PX / 2, PX, PX, lap[0], lap[1], CORD)
    _cord(d, -99.0, BED[0] + 0.0625)
    return d


def _cylinder():
    """The cylinder with its covers; on the side away from the door the valve chest, on the chest
    the throttle with the steam flange and the governor's bracket; below the chest the exhaust."""
    d = _Draw("cylinder")
    x0, x1 = CYL
    c = (H, 0.0)
    d.tube("x", c, x0, x1, CYL_R, IRON_D, sides=16)                                   # the lagging
    for x in (x0 + 0.3125, (x0 + x1) / 2.0, x1 - 0.3125):
        d.tube("x", c, x - 0.0625, x + 0.0625, CYL_R + PX / 2, BRASS, sides=16)       # its bands
    for a, b in ((x0 - 0.125, x0), (x1, x1 + 0.125)):
        d.tube("x", c, a, b, CYL_R + 0.0625, IRON, sides=16)                          # the covers' flanges
    d.tube("x", c, x1 + 0.125, x1 + 0.1875, 0.4375, IRON_L, sides=12)                 # the back cover, dished
    d.tube("x", c, x1 + 0.1875, x1 + 0.25, 0.1875, BRASS, sides=8)
    for i in range(8):                                                                # its nuts
        a = math.radians(22.5 + 45.0 * i)
        d.stud((x1 + 0.125, H + 0.5625 * math.sin(a), 0.5625 * math.cos(a)), "x")
    d.tube("x", c, x0 - 0.3125, x0 - 0.125, 0.1875, BRASS, sides=8)                   # the gland
    for x in (x0 + 0.375, x1 - 0.375):                                                # the feet
        d.box((x - 0.1875, BED_TOP, -0.5625), (x + 0.1875, H - 0.4375, 0.5625), IRON)
    # towards the door: the maker's plate on the lagging, the two drain cocks and their pipe
    xm = (x0 + x1) / 2.0
    d.box((xm + 0.25, H - 0.125, -CYL_R - PX / 2), (xm + 0.875, H + 0.125, -CYL_R + PX), BRASS)
    d.box((xm + 0.3125, H - 0.0625, -CYL_R - PX), (xm + 0.8125, H + 0.0625, -CYL_R - PX / 2), BRASS_D)
    # under each end of the barrel a drain cock, its lever towards the door; their pipe lies along
    # the bed's edge and goes down its side into the floor
    zc, zp = -0.375, -BED_HALF + 0.09375
    ends = (x0 + 0.09375, x1 - 0.09375)
    for x in ends:
        d.tube("y", (x, zc), BED_TOP + 0.0625, H - 0.46875, 0.046875, BRASS, sides=4)
        d.box((x - 0.03125, BED_TOP + 0.15625, zc - 0.21875), (x + 0.03125, BED_TOP + 0.21875, zc - 0.046875), BRASS_D)
        d.box((x - 0.03125, BED_TOP, zp + 0.03125), (x + 0.03125, BED_TOP + 0.0625, zc + 0.046875), COPPER)
    d.box((ends[0] - 0.03125, BED_TOP, zp - 0.03125), (ends[1] + 0.03125, BED_TOP + 0.0625, zp + 0.03125), COPPER)
    d.box((ends[1] - 0.03125, BED_TOP, -BED_HALF - 0.0625), (ends[1] + 0.03125, BED_TOP + 0.0625, zp - 0.03125), COPPER)
    d.box((ends[1] - 0.03125, 0.0, -BED_HALF - 0.0625), (ends[1] + 0.03125, BED_TOP, -BED_HALF), COPPER)
    # the oiler on the barrel
    d.oil_cup(x0 + 0.65, H + CYL_R, 0.0)
    # the valve chest and its cover
    za, zb = CHEST_Z
    cx0, cx1 = CHEST
    d.box((cx0, H - 0.3125, za - 0.0625), (cx1, H + 0.3125, zb - PX), IRON)
    d.box((cx0 - PX, H - 0.375, zb - PX), (cx1 + PX, H + 0.375, zb), IRON_L)
    for x in (cx0 + 0.0625, cx0 + 0.7, cx1 - 0.7, cx1 - 0.0625):
        for y in (H - 0.3125, H + 0.3125):
            d.stud((x, y, zb), "z", STUD_BRASS)
    d.tube("x", (H, VALVE_Z), cx0 - 0.1875, cx0, 0.125, BRASS, sides=8)               # the valve spindle's gland
    # the exhaust: down into the floor
    d.tube("y", (GOV_X, GOV_Z), 0.0625, H - 0.3125, 0.1875, IRON_D, sides=8)
    d.tube("y", (GOV_X, GOV_Z), 0.0, 0.0625, 0.28125, IRON, sides=8)
    # the throttle on the chest, the branch to the steam flange, the governor's bracket and column
    d.tube("y", (GOV_X, GOV_Z), H + 0.3125, H + 0.8125, 0.1875, IRON, sides=8)
    d.tube("x", (H + 0.5625, GOV_Z), GOV_X, INLET[0] + 0.14, 0.140625, IRON, sides=8)
    d.tube("y", (INLET[0], GOV_Z), H + 0.6875, INLET[1] - 0.0625, 0.140625, IRON, sides=8)       # from the branch's top
    d.tube("y", (INLET[0], GOV_Z), INLET[1] - 0.0625, INLET[1], 0.25, IRON_L, sides=8)
    d.box((GOV_X - 0.1875, H + 0.8125, GOV_Z - 0.1875), (GOV_X + 0.1875, H + 0.9375, CORD_Z - 0.0625), IRON)
    d.tube("z", GOV_PULLEY, GOV_Z, CORD_Z + 0.09375, 0.046875, STEEL, sides=4)
    d.tube("z", GOV_PULLEY, CORD_Z - PX, CORD_Z + PX, CORD_TO, IRON_L, sides=12)
    d.tube("y", (GOV_X, GOV_Z), H + 0.9375, GOV_Y, 0.109375, BRASS_D, sides=8)
    _lap, far = _laps(CORD_RUNS)
    d.arc((GOV_PULLEY[0], GOV_PULLEY[1], CORD_Z), CORD_TO + PX / 2, PX, PX, far[0], far[1], CORD, steps=8)
    return d


def _belt():
    """The belt's two runs and its lap round the dynamo's pulley."""
    d = _Draw("belt")
    for a, b, _angle in BELT:
        d.beam((a[0], a[1], WZ), (b[0], b[1], WZ), BELT_W, BELT_T, LEATHER)
    _lap, far = _laps(BELT)
    d.arc((DYN_X, DYN_H, WZ), PULLEY_R + BELT_T / 2.0, BELT_T, BELT_W, far[0], far[1], LEATHER)
    return d


def _lap():
    """The belt's lap round the flywheel: it lies on the rim's far side and stands still while the
    wheel turns under it."""
    d = _Draw("lap")
    lap, _far = _laps(BELT)
    d.arc((0.0, H, WZ), WHEEL_R + BELT_T / 2.0, BELT_T, BELT_W, lap[0], lap[1], LEATHER)
    return d


def _wire(d, points, mat=COPPER):
    """A stiff lead through the points, every leg of it along an axis: square, a texel thick. A leg
    owns the corner it ends in and the next one begins beyond it, so no two legs share a face."""
    h = PX / 2
    for n, (a, b) in enumerate(zip(points, points[1:])):
        k = max(range(3), key=lambda i: abs(b[i] - a[i]))
        lo, hi = [min(a[i], b[i]) - h for i in range(3)], [max(a[i], b[i]) + h for i in range(3)]
        if n and b[k] > a[k]:
            lo[k] = a[k] + h
        elif n:
            hi[k] = a[k] - h
        d.box(lo, hi, mat)


def _pedestal(d, z0, z1, foot):
    """A bearing of the dynamo's shaft between z0 and z1, standing on `foot`."""
    zm = (z0 + z1) / 2.0
    d.box((DYN_X - 0.3125, foot, z0), (DYN_X + 0.3125, foot + 0.125, z1), IRON_D)
    d.box((DYN_X - 0.1875, foot + 0.125, z0), (DYN_X + 0.1875, DYN_H - 0.125, z1), IRON)
    d.tube("z", (DYN_X, DYN_H), z0 - PX / 2, z1 + PX / 2, 0.21875, IRON, sides=8)
    d.tube("z", (DYN_X, DYN_H), z0 - PX, z1 + PX, 0.15625, BRASS, sides=8)
    d.oil_cup(DYN_X, DYN_H + 0.21875, zm)


def _dynamo():
    """The dynamo's standing part: slide rails and bedplate, the two pole pieces on their brass
    footsteps, the wound limbs and the yoke over them, the bearings, the brushes, the terminals and
    the pilot lamp."""
    d = _Draw("dynamo")
    foot = 0.25
    for z in (D_NEAR[1] + 0.25, D_FAR[0] - 0.25):                                     # the rails it is drawn up on
        d.box((DYN_X - 1.3125, 0.0, z - 0.125), (DYN_X + 1.3125, 0.125, z + 0.125), IRON_D)
        for sx in (-1.21875, 1.21875):
            d.stud((DYN_X + sx, 0.125, z), "y")
    d.box((DYN_X - 1.125, 0.125, D_NEAR[0] - 0.0625), (DYN_X + 1.125, foot, D_FAR[1] + 0.0625), IRON)
    _pedestal(d, *D_NEAR, foot)
    _pedestal(d, *D_FAR, foot)
    for s in (-1.0, 1.0):
        xa, xb = sorted((DYN_X + s * 0.5, DYN_X + s * 1.0))
        d.box((xa, foot, ARM[0] + PX), (xb, foot + 0.1875, ARM[1] - PX), BRASS_D)     # the footstep
        d.box((xa, foot + 0.1875, ARM[0]), (xb, DYN_H + 0.5625, ARM[1]), IRON)        # the pole piece
        xa, xb = sorted((DYN_X + s * 0.3125, DYN_X + s * 0.5))
        for y0, y1 in ((DYN_H + 0.34375, DYN_H + 0.5625), (DYN_H - 0.5625, DYN_H - 0.34375)):
            d.box((xa, y0, ARM[0]), (xb, y1, ARM[1]), IRON)                           # its horns round the armature
        # the limb: an iron core in a coil between two cheeks
        lx = DYN_X + s * LIMB
        d.tube("y", (lx, DYN_Z), DYN_H + 0.5625, YOKE_Y[0], 0.21875, IRON_D, sides=8)
        d.tube("y", (lx, DYN_Z), DYN_H + 0.6875, YOKE_Y[0] - 0.125, 0.34375, WOUND, sides=12, grain="x")
        for y in (DYN_H + 0.625, YOKE_Y[0] - 0.125):
            d.tube("y", (lx, DYN_Z), y, y + 0.0625, 0.375, BRASS_D, sides=12)
    d.box((DYN_X - 0.9375, YOKE_Y[0], DYN_Z - 0.3125), (DYN_X + 0.9375, YOKE_Y[1], DYN_Z + 0.3125), IRON)      # the yoke
    # the brush rocker at the commutator: a ring, a holder above and one below, their leads to the terminals
    zb = (COMM[0] + COMM[1]) / 2.0
    d.ring("z", (DYN_X, DYN_H, zb), 0.375, 0.0625, 0.0625, BRASS_D, sides=16)
    for s in (-1.0, 1.0):
        ya, yb = sorted((DYN_H + s * 0.25, DYN_H + s * 0.5))
        d.box((DYN_X - 0.0625, ya, zb - 0.09375), (DYN_X + 0.0625, yb, zb + 0.09375), BRASS)
    # the two leads lie on the machine: from each brush along the back of a pole piece, up the back
    # of its limb's coil and over the yoke as far as the terminal board, under the post on that limb
    top = YOKE_Y[1]
    zr = ARM[1] + PX / 2
    for s, y in ((-1.0, DYN_H + 0.5 + PX / 2), (1.0, DYN_H - 0.5 - PX / 2)):
        _wire(d, [(DYN_X, y, zr), (DYN_X + s * LIMB, y, zr), (DYN_X + s * LIMB, top + PX / 2, zr),
                  (DYN_X + s * LIMB, top + PX / 2, DYN_Z + 0.1875 + PX / 2)])
    # the maker's plate, on the pole piece that looks at the engine
    xe = DYN_X + 1.0
    d.box((xe - PX, DYN_H - 0.0625, DYN_Z - 0.25), (xe + PX / 2, DYN_H + 0.1875, DYN_Z + 0.25), BRASS)
    d.box((xe + PX / 2, DYN_H, DYN_Z - 0.1875), (xe + PX, DYN_H + 0.125, DYN_Z + 0.1875), BRASS_D)
    # the terminal board on the yoke: a porcelain post over each limb, the pilot lamp between them
    d.box((DYN_X - 0.8125, top, DYN_Z - 0.1875), (DYN_X + 0.8125, top + 0.0625, DYN_Z + 0.1875), IRON_D)
    for s in (-1.0, 1.0):
        d.tube("y", (DYN_X + s * LIMB, DYN_Z), top + 0.0625, top + 0.25, 0.09375, PORCELAIN, sides=8)
        d.tube("y", (DYN_X + s * LIMB, DYN_Z), top + 0.25, top + 0.3125, 0.046875, BRASS, sides=4)
    d.tube("y", (DYN_X, DYN_Z), top + 0.0625, top + 0.1875, 0.0625, BRASS_D, sides=4)
    k, c = d._line("y", (DYN_X, DYN_Z))
    K.glass_prism(d.m, "y", c, (top + 0.1875 - d.at[k]) * d.u, (top + 0.25 - d.at[k]) * d.u, 0.0625 * d.u, GLOW_DIM,
                  sides=4)
    K.glass_prism(d.m, "y", c, (top + 0.25 - d.at[k]) * d.u, (top + 0.4375 - d.at[k]) * d.u, 0.09375 * d.u, GLOW)
    return d


LAMP = _scene((DYN_X, YOKE_Y[1] + 0.3125, DYN_Z))       # the pilot lamp's glass


# --- the set ---------------------------------------------------------------------------------------------------
SHAFT = (0.0, 0.0, 1.0)         # the way both shafts point. A turn is right-handed about it: the top of
#                                 the flywheel goes west, away from the cylinder, and the belt's slack
#                                 run is the upper one
STROKE = (1.0, 0.0, 0.0)        # from the shaft to the cylinder


def _move_flywheel(canvas):
    return MK.spin(canvas, SHAFT, MK.ENGINE_REV)


def _move_rod(canvas):
    return MK.crank(canvas, SHAFT, STROKE, CRANK, ROD, MK.ENGINE_REV)


def _move_crosshead(canvas):
    return MK.crank(canvas, SHAFT, STROKE, CRANK, ROD, MK.ENGINE_REV, turn=False)


def _move_governor(canvas):
    return MK.spin(canvas, (0.0, 1.0, 0.0), MK.GOVERNOR_REV)


def _move_armature(canvas):
    return MK.spin(canvas, SHAFT, MK.DYNAMO_REV)


# The eccentric is a crank of its own, ECC_LEAD before the engine's: its rod and the valve spindle
# are drawn as they stand with the main crank at the dead centre, and start= says so.
def _move_eccentric(canvas):
    return MK.crank(canvas, SHAFT, STROKE, ECC, ECC_ROD, MK.ENGINE_REV, start=ECC_LEAD)


def _move_valve(canvas):
    return MK.crank(canvas, SHAFT, STROKE, ECC, ECC_ROD, MK.ENGINE_REV, turn=False, start=ECC_LEAD)


# name: (what draws it, what registers its motion)
PARTS = {
    "bed": (_bed, None),
    "frame": (_frame, None),
    "cylinder": (_cylinder, None),
    "crosshead": (_crosshead, _move_crosshead),
    "rod": (_rod, _move_rod),
    "flywheel": (_flywheel, _move_flywheel),
    "eccentric": (_eccentric, _move_eccentric),
    "valve": (_valve, _move_valve),
    "governor": (_governor, _move_governor),
    "lap": (_lap, None),
    "belt": (_belt, None),
    "dynamo": (_dynamo, None),
    "armature": (_armature, _move_armature),
}


@functools.lru_cache(maxsize=None)
def _drawn():
    return {name: draw() for name, (draw, _move) in PARTS.items()}


def models():
    return {d.m.name: d.m for d in _drawn().values()}


def foundation(canvas, origin=(0, 0, 0)):
    """The blocks of the set: the base plate in the floor's own course, the pit dug through it and
    lined with brick below that course."""
    ox, oy, oz = (int(v) for v in origin)
    top = int(FLOOR) - 1
    for x, z in BASE:
        canvas.set(ox + x, oy + top, oz + z, BASE_PLATE)
    for (x, z), depth in PIT.items():
        canvas.carve(ox + x, oy + top - depth + 1, oz + z, ox + x, oy + top, oz + z)
    for (x, z), depth in PIT.items():
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            near = PIT.get((x + dx, z + dz), 0)
            for y in range(top - depth + 1, top - near + 1):
                if y < top:
                    canvas.set(ox + x + dx, oy + y, oz + z + dz, PIT_LINING)
        canvas.set(ox + x, oy + top - depth, oz + z, PIT_LINING)


def build(canvas, origin=(0, 0, 0)):
    """Lay the foundation, place the set, say what moves and offer the pilot lamp's light. Returns
    the number of display entities."""
    foundation(canvas, origin)
    n = 0
    for name, d in _drawn().items():
        x, y, z = _scene(d.at, origin)
        canvas.add_entity(x, y, z, M.display(d.m, scale=d.scale))
        n += 1
        move = PARTS[name][1]
        if move is not None:
            n += move(canvas)
    cell = tuple(int(math.floor(v)) for v in _scene((DYN_X, YOKE_Y[1] + 0.3125, DYN_Z), origin))
    K.offer_lights(canvas, [(cell, LAMP_LEVEL)], "machines/engine: the pilot lamp on the dynamo")
    return n


def _report():
    for name, d in _drawn().items():
        lo, hi = d.m.bounds()
        print(f"{d.m.name:24s} scale {d.scale:g}  {len(d.m.parts):4d} boxes  "
              f"span {' '.join(f'{(hi[i] - lo[i]) / d.u:5.2f}' for i in range(3))} blocks  "
              f"at {' '.join(f'{v:7.3f}' for v in ANCHORS[name])}")
    (a, b, _up), (c, e, _down) = BELT
    fall = [math.degrees(math.atan2(q[1] - p[1], abs(q[0] - p[0]))) for p, q in ((a, b), (c, e))]
    print(f"{len(PARTS)} entities; pulley radius {PULLEY_R:.3f}; towards the pulley the belt's upper run falls "
          f"{-fall[0]:.1f} degrees and its lower run rises {fall[1]:.1f}")
    print("the belt's lower run over the floor, cell by cell (x: height at the cell's west edge):")
    for x in sorted({x for x, _z in PIT}):
        t = ((x - SHAFT_X) - c[0]) / (e[0] - c[0])
        if 0.0 <= t <= 1.0:
            print(f"   x {x}: {c[1] + (e[1] - c[1]) * t - BELT_T:6.3f}   pit {PIT[(x, int(WHEEL_Z))]} deep")
    print("STEAM_IN", STEAM_IN, " POWER_OUT", POWER_OUT, " LAMP", LAMP)


if __name__ == "__main__":
    _report()
