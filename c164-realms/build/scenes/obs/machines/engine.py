"""machines/engine-dynamo: the steam engine of the power house, its flywheel, the belt and the dynamo
(plan/ART-PLAN.md 5.3, 7.2, 8; plan/parts/A5-machines.md 2.5; card
plan/packages/machines/engine-dynamo.md).

What it is. A horizontal mill engine with one cylinder, as a works of the 1890s would have bought
it: the cylinder lies in the east, next to the boilers; its piston rod drives a crosshead between
four slide bars, the connecting rod turns an overhung crank, and on the crankshaft, between two
bearings, runs a flywheel five blocks across whose lower third turns in a pit. The flywheel is the
belt wheel as well: a flat leather belt runs west from its rim to the small pulley of a dynamo, one
turn of the engine to three of the armature. A flyball governor stands on the frame beside the
crank. Steam comes in at the top of the valve chest (STEAM_IN) and leaves into the floor; the
current leaves at the two terminals on top of the dynamo (POWER_OUT). The pipe and the cables are
the props line's.

Where it stands. In the south half of the power house (site/powerhouse.ROOM), the engine's line
east-west: boilers in the north-east, engine in the south-east, dynamo in the south-west, where the
cable leaves the house. From the wicket in the north front the flywheel is seen full face, the
crank and the rods before it, the belt running off to the right.

    x  the engine's line runs along x at z = LINE_Z; the crankshaft crosses it at x = SHAFT_X
    y  the floor is S.LOWER_GROUND; the shaft lies SHAFT_H above it
    z  the flywheel turns in the plane z = WHEEL_Z, over the pit (PIT)

Every model is drawn in the engine's own frame, in blocks: x from the shaft towards the cylinder,
y up from the floor, z from the engine's line towards the flywheel. Big pieces are shown at scale 2
and small ones at scale 1, each with as many texels to its unit (px = scale): 16 px to the block.

What moves (scenes/obs/motion/_kit.py; nothing runs every tick):
    flywheel   with the shaft and the crank, once in MK.ENGINE_REV, its top going away from the cylinder
    rod        the connecting rod: slides with the crosshead and tilts to stay on the crank pin
    crosshead  with the piston rod: slides
    governor   about its spindle, once in MK.GOVERNOR_REV
    armature   with commutator and pulley, once in MK.DYNAMO_REV, the way the belt takes it
The rest pose is the dead centre, the crank pin towards the cylinder, as the motion kit wants it.
A part that turns is painted with no light of its own from above: its tones depend on how a face
stands to the axis only, so no painted highlight goes round with the wheel.

The pit is the one thing here that is blocks: build() digs it (PIT, a slot one cell wide for the
flywheel and the belt's lower run) and lines it, because the machines are placed before the rooms
and the wheel cannot turn in a floor. The room's floor, the gratings and the rails round the pit
are interiors/powerhouse's, which reads PIT and KEEP_CLEAR.
"""
import contextlib
import functools
import math

from artkit import models as M

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..motion import _kit as MK

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
HUB_R = 0.44
SHAFT_R = 0.1875                        # a shaft of 6 px
CRANK = 1.0                             # shaft to crank pin: the stroke is twice this (the motion line's
ROD = 4.0                               # test station has the same crank and the same rod)
PIN = CRANK + ROD                       # 5.0: the crosshead pin at the dead centre, the rest pose
CYL = (5.75, 8.35)                      # the cylinder's barrel along x; its covers lie outside
CYL_R = 0.625                           # the lagged barrel: 20 px across
CHEST_Z = (-1.0625, -0.5625)            # the valve chest on the side the door sees
BED = (2.8, 8.7)                        # the bed under the slide bars and the cylinder, along x
BED_HALF = 0.75                         # half its width
BED_TOP = 0.625
MAIN = (0.5, 1.0)                       # the main bearing along z: between the crank and the pit
OUTER = (2.125, 2.625)                  # the outboard bearing: beyond the pit
GOVERNOR_AT = (2.25, 0.75)              # (x, z) of the governor's spindle, on the frame
GOVERNOR_Y = 2.0                        # where its turning part begins

# --- the dynamo (same frame) ---------------------------------------------------------------------------
DYN_X = -5.5                            # its shaft, parallel to the engine's
DYN_H = 1.25
DYN_Z = 0.25                            # the middle of its ring of poles
PULLEY_R = WHEEL_R * MK.DYNAMO_REV / MK.ENGINE_REV      # 0.833: the belt's one to three
YOKE_R = 1.0625                         # the ring's outside
POLES = 6                               # never four

# --- the belt --------------------------------------------------------------------------------------------
BELT_W = 0.375                          # 6 px of leather on a face of 8
BELT_T = PX
LEAN = math.degrees(math.asin((WHEEL_R - PULLEY_R) / abs(DYN_X)))      # 17.6: how the two runs lean

# --- the pit (cells, scene coordinates): {(x, z): how many blocks deep} ----------------------------------
# One cell wide. The flywheel needs two blocks under its middle and one at its ends; the belt's
# lower run leaves the wheel below the floor and comes up to the pulley, so the slot runs on west.
PIT = {(x, int(WHEEL_Z)): (2 if 76 <= x <= 78 else 1) for x in range(72, 80)}
PIT_LINING = B.TUFF_BRICK.block

# --- for the others ----------------------------------------------------------------------------------------
# Scene coordinates, the engine at origin (0, 0, 0).
STEAM_IN = (SHAFT_X + 7.05, FLOOR + H + 0.875, LINE_Z - 0.8125)     # the middle of the inlet flange, which looks up
EXHAUST = (SHAFT_X + 7.05, FLOOR, LINE_Z - 0.8125)                  # where the exhaust goes into the floor
POWER_OUT = ((SHAFT_X + DYN_X - 0.25, FLOOR + DYN_H + YOKE_R + 0.3125, LINE_Z + DYN_Z),
             (SHAFT_X + DYN_X + 0.25, FLOOR + DYN_H + YOKE_R + 0.3125, LINE_Z + DYN_Z))    # the two terminals' tops
# Boxes (x0, y0, z0, x1, y1, z1) in which something of the set stands or moves: nothing else goes there.
KEEP_CLEAR = (
    (SHAFT_X + 2.7, FLOOR, LINE_Z - 1.2, SHAFT_X + 8.9, FLOOR + 2.6, LINE_Z + 0.9),             # bed and cylinder
    (SHAFT_X - 1.4, FLOOR, LINE_Z - 0.4, SHAFT_X + 2.8, FLOOR + 3.2, LINE_Z + 1.0),             # crank, governor
    (SHAFT_X - 2.7, FLOOR - 2.0, LINE_Z + 1.0, SHAFT_X + 2.7, FLOOR + 4.0, LINE_Z + 2.75),      # flywheel, bearings
    (SHAFT_X - 6.5, FLOOR - 1.0, LINE_Z + 1.0, SHAFT_X - 2.7, FLOOR + 4.0, LINE_Z + 2.0),       # the belt
    (SHAFT_X - 6.9, FLOOR, LINE_Z - 1.1, SHAFT_X - 4.1, FLOOR + 2.8, LINE_Z + 2.0),             # the dynamo
)

# --- materials (the palette's, and nothing else) -----------------------------------------------------------
IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
IRON_L = P.mat("iron", base=4)                  # planed faces
STEEL = P.mat("iron", base=5, noise=0.10)       # bright steel: rods, shaft, slide bars
BRASS = P.mat("brass")
BRASS_D = P.mat("brass_dark")
COPPER = P.mat("old_copper")
WOUND = P.mat("old_copper", kind="wood", bevel=0)       # windings: the wire runs with the grain
PORCELAIN = P.mat("porcelain")
RED = P.mat("signal")
LEATHER = P.mat("dark_wood", kind="plain", noise=0.10, bevel=0, base=2)
LEATHER_EDGE = P.mat("dark_wood", kind="flat", bevel=0, base=1)
STUD = P.mat("iron", kind="flat", bevel=0, base=5)
STUD_BRASS = P.mat("brass", kind="flat", bevel=0, base=4)


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
    """A model drawn in blocks, in the engine's frame, round the point `at`, where its entity stands.
    artkit's unit is 1/16 block of a model shown at scale 1; a model shown at scale s is drawn s
    times smaller with s texels to the unit."""

    def __init__(self, name, at, scale=2.0):
        self.at = tuple(float(v) for v in at)
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

    def ball(self, centre, radius, mat, **kw):
        self.m.ball(self.p(centre), radius * self.u, mat, **kw)

    def rod(self, a, b, radius, mat, **kw):
        self.m.rod(self.p(a), self.p(b), radius * self.u, mat, **kw)

    def beam(self, a, b, width, height, mat, **kw):
        self.m.beam(self.p(a), self.p(b), width * self.u, height * self.u, mat, **kw)

    def turned(self, *turns, about=(0.0, 0.0, 0.0)):
        return self.m.turned(*turns, about=self.p(about))

    def stud(self, p, out="y", mat=STUD, size=PX):
        """A bolt head: `size` square, half of it proud. p is the middle of its foot; `out` the way
        the face it sits on looks ("x", "-x", "y", ...)."""
        k = M.AXES.index(out[-1])
        lo, hi = [v - size / 2.0 for v in p], [v + size / 2.0 for v in p]
        lo[k], hi[k] = sorted((p[k], p[k] + (-size / 2.0 if out.startswith("-") else size / 2.0)))
        self.box(lo, hi, mat)


# --- the shaft and what turns with it ------------------------------------------------------------------------
def _flywheel():
    """Flywheel, shaft and crank: one piece, its entity on the axis in the wheel's plane. The crank
    pin points at the cylinder: the dead centre."""
    d = _Draw("flywheel", (0.0, H, WZ))
    c = (0.0, H, WZ)
    with _lit_along((0.0, 0.0, -1.0)):
        d.ring("z", c, WHEEL_R - RIM_T / 2.0, RIM_T, RIM_W, IRON, sides=32)
        d.ring("z", c, WHEEL_R - RIM_T - PX, 2 * PX, 0.25, IRON_D, sides=32)           # the rib inside the rim
        for i in range(SPOKES):
            a = 30.0 + 360.0 * i / SPOKES
            # an arm in two lengths, stouter at the hub
            d.box((HUB_R - PX, H - 0.1875, WZ - 0.125), (1.25, H + 0.1875, WZ + 0.125), IRON, rot=("z", a, c), grain="x")
            d.box((1.25, H - 0.125, WZ - 0.0625), (WHEEL_R - RIM_T - PX, H + 0.125, WZ + 0.0625), IRON,
                  rot=("z", a, c), grain="x")
        d.tube("z", (0.0, H), WZ - 0.375, WZ + 0.375, HUB_R, IRON, sides=12)
        d.tube("z", (0.0, H), WZ - 0.4375, WZ + 0.4375, 0.28, IRON_L, sides=12)       # the boss, keyed on
        d.tube("z", (0.0, H), 0.1875, OUTER[1] + 0.125, SHAFT_R, STEEL, sides=8)
        # the crank: a web from the shaft to the pin, a balance weight behind the shaft
        z0, z1 = 0.1875, 0.4375
        d.box((0.0, H - 0.25, z0), (CRANK, H + 0.25, z1), IRON, grain="x")
        d.tube("z", (0.0, H), z0, z1, 0.34, IRON, sides=12)
        d.tube("z", (CRANK, H), z0, z1, 0.25, IRON, sides=12)
        d.box((-0.75, H - 0.4375, z0), (-0.25, H + 0.4375, z1), IRON_D, grain="y")
        d.tube("z", (CRANK, H), -0.1875, z0, 0.125, STEEL, sides=8)                   # the pin
        d.tube("z", (CRANK, H), -0.25, -0.1875, 0.1875, BRASS, sides=8)               # its collar
    return d


def _rod():
    """The connecting rod, from the crosshead pin (where its entity stands) to the crank pin."""
    d = _Draw("rod", (PIN, H, 0.0))
    t = 0.09375                                                                       # half its thickness: 3 px in all
    # the big end: a strap round two brasses
    d.box((CRANK - 0.3125, H - 0.25, -t), (CRANK + 0.3125, H + 0.25, t), IRON_L)
    d.box((CRANK - 0.1875, H - 0.1875, -t - PX / 2), (CRANK + 0.1875, H + 0.1875, t + PX / 2), BRASS)
    # the shank swells towards the crank
    d.box((CRANK + 0.3125, H - 0.125, -t + PX / 2), (2.75, H + 0.125, t - PX / 2), STEEL, grain="x")
    d.box((2.75, H - 0.09375, -t + PX / 2), (PIN - 0.1875, H + 0.09375, t - PX / 2), STEEL, grain="x")
    # the small end
    d.box((PIN - 0.1875, H - 0.1875, -t), (PIN + 0.1875, H + 0.1875, t), IRON_L)
    d.box((PIN - 0.09375, H - 0.09375, -t - PX / 2), (PIN + 0.09375, H + 0.09375, t + PX / 2), BRASS)
    return d


def _crosshead():
    """Crosshead and piston rod; the entity stands on the crosshead pin."""
    d = _Draw("crosshead", (PIN, H, 0.0))
    d.box((PIN - 0.28, H - 0.25, -0.1875), (PIN + 0.28, H + 0.25, 0.1875), IRON)
    for s in (-1.0, 1.0):                                                             # the slippers between the bars
        d.box((PIN - 0.3125, H - 0.25, s * 0.1875), (PIN + 0.3125, H + 0.25, s * 0.4375), IRON_L)
        d.tube("z", (PIN, H), *sorted((s * 0.4375, s * 0.5)), 0.09375, BRASS, sides=8)    # the pin's ends
    d.tube("x", (H, 0.0), PIN + 0.28, PIN + 2.7, 0.09375, STEEL, sides=8)             # the piston rod
    return d


def _governor():
    """What turns of the governor: spindle, arms, the two balls and the sleeve they lift."""
    x, z = GOVERNOR_AT
    y = GOVERNOR_Y
    d = _Draw("governor", (x, y, z), scale=1.0)
    with _lit_along((0.0, 1.0, 0.0)):
        d.tube("y", (x, z), y, y + 0.875, 0.03125, STEEL, sides=4)
        d.tube("y", (x, z), y + 0.8125, y + 0.9375, 0.0625, BRASS, sides=8)           # the head the arms hang from
        d.tube("y", (x, z), y + 0.9375, y + 1.0, 0.03125, BRASS, sides=4)
        d.tube("y", (x, z), y + 0.25, y + 0.375, 0.0625, BRASS, sides=8)              # the sleeve
        for s in (-1.0, 1.0):
            ball = (x + s * 0.375, y + 0.4375, z)
            d.rod((x + s * 0.03125, y + 0.875, z), ball, 0.02, STEEL, sides=4)
            d.rod((x + s * 0.0625, y + 0.3125, z), (x + s * 0.3, y + 0.42, z), 0.02, STEEL, sides=4)
            d.ball(ball, 0.15625, RED, sides=8, layers=4)
    return d


def _armature():
    """What turns of the dynamo: shaft, commutator, armature and the belt pulley."""
    d = _Draw("armature", (DYN_X, DYN_H, DYN_Z))
    c = (DYN_X, DYN_H)
    with _lit_along((0.0, 0.0, -1.0)):
        d.tube("z", c, -1.0, WZ + RIM_W / 2.0 + PX, 0.09375, STEEL, sides=8)
        d.tube("z", c, DYN_Z - 0.4375, DYN_Z + 0.4375, 0.5, WOUND, sides=12, grain="z")       # the wound drum
        for z in (DYN_Z - 0.4375, DYN_Z + 0.375):
            d.tube("z", c, z, z + 0.0625, 0.5 + PX / 2, IRON_D, sides=12)                     # its binding bands
        d.tube("z", c, DYN_Z - 0.8125, DYN_Z - 0.4375, 0.28, COPPER, sides=12, grain="z")     # the commutator
        d.tube("z", c, DYN_Z - 0.875, DYN_Z - 0.8125, 0.3125, BRASS_D, sides=12)
        # the pulley: a crowned face on a web
        d.ring("z", (DYN_X, DYN_H, WZ), PULLEY_R - 0.0625, 0.125, RIM_W, IRON, sides=20)
        d.tube("z", c, WZ - 0.0625, WZ + 0.0625, PULLEY_R - 0.125, IRON_D, sides=20)
        d.tube("z", c, WZ - 0.25, WZ + 0.25, 0.21875, IRON, sides=8)
    return d


# --- what stands still ---------------------------------------------------------------------------------------
def _bed():
    """The bed: a box of cast iron under the cylinder and the slide bars, which it carries."""
    d = _Draw("bed", ((BED[0] + BED[1]) / 2.0, 0.0, 0.0))
    x0, x1 = BED
    w = BED_HALF
    d.box((x0, 0.0, -w), (x1, 0.125, w), IRON_D)                                      # the sole
    d.box((x0 + PX, 0.125, -w + 0.125), (x1 - PX, BED_TOP - 0.125, w - 0.125), IRON)
    d.box((x0, BED_TOP - 0.125, -w), (x1, BED_TOP, w), IRON_L)                        # the planed top
    n = 6
    for i in range(n + 1):                                                            # ribs, and a bolt at the foot of each
        x = x0 + 0.125 + (x1 - x0 - 0.25) * i / n
        for s in (-1.0, 1.0):
            d.box((x - PX, 0.125, s * (w - 0.125)), (x + PX, BED_TOP - 0.125, s * (w - PX)), IRON)
            d.stud((x, 0.125, s * (w - PX)), "y", STUD, size=2 * PX)
    # the four slide bars and the yoke that holds their crank end
    gx = (BED[0] + 0.0625, CYL[0] - 0.125)
    for s in (-1.0, 1.0):
        za, zb = sorted((s * 0.21875, s * 0.46875))
        for y0, y1 in ((H + 0.25, H + 0.375), (H - 0.375, H - 0.25)):
            d.box((gx[0], y0, za), (gx[1], y1, zb), STEEL, grain="x")
        d.box((gx[0] - 0.0625, BED_TOP, za), (gx[0] + 0.125, H + 0.4375, zb), IRON)   # a post of the yoke
        d.box((gx[1] - 0.25, BED_TOP, za), (gx[1], H - 0.375, zb), IRON)              # a block under the cylinder end
    d.box((gx[0] - 0.0625, H + 0.4375, -0.46875), (gx[0] + 0.125, H + 0.5625, 0.46875), IRON)     # the yoke's head
    return d


def _plummer(d, z0, z1):
    """A bearing pedestal on the shaft, between z0 and z1."""
    zm = (z0 + z1) / 2.0
    d.box((-0.625, 0.0, z0 - PX), (0.625, 0.125, z1 + PX), IRON_D)
    d.box((-0.5, 0.125, z0), (0.5, 0.5, z1), IRON)
    d.box((-0.375, 0.5, z0), (0.375, H - 0.125, z1), IRON)
    d.tube("z", (0.0, H), z0, z1, 0.375, IRON, sides=12)                              # the housing
    d.tube("z", (0.0, H), z0 - PX, z1 + PX, 0.28, BRASS, sides=12)                    # the brasses show at its ends
    d.box((-0.3125, H + 0.3125, z0 + PX), (0.3125, H + 0.4375, z1 - PX), IRON_L)      # the cap
    for sx in (-0.21875, 0.21875):
        for sz in (z0 + 0.125, z1 - 0.125):
            d.stud((sx, H + 0.4375, sz), "y", STUD, size=2 * PX)
    d.tube("y", (0.0, zm), H + 0.4375, H + 0.5625, 0.0625, BRASS, sides=8)            # the oil cup
    d.tube("y", (0.0, zm), H + 0.5625, H + 0.625, 0.09375, BRASS, sides=8)


def _frame():
    """The two bearings of the shaft, the girder that ties the main bearing to the bed, and the
    governor's column on it."""
    d = _Draw("frame", (1.125, 0.0, 1.5))
    _plummer(d, *MAIN)
    _plummer(d, *OUTER)
    z0, z1 = MAIN[0] + PX, MAIN[1] - PX
    d.box((0.5, 0.0, MAIN[0] - PX), (BED[0] + 0.0625, 0.125, MAIN[1] + PX), IRON_D)
    d.box((0.5, 0.125, z0), (BED[0] + 0.0625, 0.75, z1), IRON)
    d.box((0.5, 0.75, z0 - PX), (BED[0] + 0.0625, 0.875, z1 + PX), IRON_L)
    # the governor's stand: a foot, a column, the bracket under the spindle
    x, z = GOVERNOR_AT
    d.tube("y", (x, z), 0.875, 1.0, 0.1875, IRON, sides=8)
    d.taper("y", (x, z), 1.0, GOVERNOR_Y - 0.125, 0.125, 0.078125, IRON, sides=8, steps=3)
    d.tube("y", (x, z), GOVERNOR_Y - 0.125, GOVERNOR_Y, 0.125, BRASS_D, sides=8)
    return d


def _cylinder():
    """The cylinder with its covers, the valve chest on the door's side, the steam inlet on top of
    the chest and the exhaust below it."""
    d = _Draw("cylinder", (7.0, 0.0, -0.1875))
    x0, x1 = CYL
    c = (H, 0.0)
    d.tube("x", c, x0, x1, CYL_R, IRON_D, sides=16)                                   # the lagging
    for x in (x0 + 0.3125, (x0 + x1) / 2.0, x1 - 0.3125):
        d.tube("x", c, x - 0.0625, x + 0.0625, CYL_R + PX / 2, BRASS, sides=16)       # its bands
    for a, b in ((x0 - 0.125, x0), (x1, x1 + 0.125)):
        d.tube("x", c, a, b, CYL_R + 0.0625, IRON, sides=16)                          # the covers' flanges
    d.tube("x", c, x1 + 0.125, x1 + 0.1875, 0.4375, IRON_L, sides=12)                 # the back cover, dished
    d.tube("x", c, x1 + 0.1875, x1 + 0.25, 0.1875, BRASS, sides=8)
    d.tube("x", c, x0 - 0.3125, x0 - 0.125, 0.1875, BRASS, sides=8)                   # the gland
    for x in (x0 + 0.375, x1 - 0.375):                                                # the feet
        d.box((x - 0.1875, BED_TOP, -0.5625), (x + 0.1875, H - 0.4375, 0.5625), IRON)
    # the valve chest
    za, zb = CHEST_Z
    cx0, cx1 = x0 + 0.25, x1 - 0.25
    d.box((cx0, H - 0.3125, za), (cx1, H + 0.3125, zb + 0.0625), IRON)
    d.box((cx0 - PX, H - 0.375, za - PX), (cx1 + PX, H + 0.375, za), IRON_L)          # its cover, bolted on
    for x in (cx0 + 0.0625, (cx0 + cx1) / 2.0, cx1 - 0.0625):
        for y in (H - 0.3125, H + 0.3125):
            d.stud((x, y, za - PX), "-z", STUD_BRASS, size=2 * PX)
    zc = (za + zb) / 2.0
    d.tube("x", (H, zc), cx0 - 0.25, cx0, 0.09375, BRASS, sides=8)                    # the valve rod's gland
    # steam in: a neck and a flange that looks up
    sx = STEAM_IN[0] - SHAFT_X
    d.tube("y", (sx, zc), H + 0.3125, H + 0.8125, 0.15625, IRON, sides=8)
    d.tube("y", (sx, zc), H + 0.8125, H + 0.875, 0.25, IRON_L, sides=8)
    # exhaust: down into the floor
    d.tube("y", (sx, zc), 0.0625, H - 0.3125, 0.1875, IRON_D, sides=8)
    d.tube("y", (sx, zc), 0.0, 0.0625, 0.28, IRON, sides=8)
    # the oiler on the barrel
    d.tube("y", (x0 + 1.3, 0.0), H + CYL_R, H + CYL_R + 0.125, 0.03125, BRASS, sides=4)
    d.tube("y", (x0 + 1.3, 0.0), H + CYL_R + 0.125, H + CYL_R + 0.3125, 0.09375, BRASS, sides=8)
    return d


def _tangent(sign):
    """The two ends of a straight run of the belt: on the flywheel and on the pulley. sign 1 is the
    upper run, -1 the lower."""
    a = math.radians(90.0 + LEAN)
    n = (math.cos(a), sign * math.sin(a))
    r1, r2 = WHEEL_R + BELT_T / 2.0, PULLEY_R + BELT_T / 2.0
    return (r1 * n[0], H + r1 * n[1]), (DYN_X + r2 * n[0], DYN_H + r2 * n[1])


def _belt():
    """The belt's two runs and its lap round the dynamo's pulley."""
    (ax, ay), (bx, by) = _tangent(1)
    d = _Draw("belt", ((ax + DYN_X - PULLEY_R) / 2.0, (H + DYN_H) / 2.0, WZ))
    for sign in (1, -1):
        (ax, ay), (bx, by) = _tangent(sign)
        d.beam((ax, ay, WZ), (bx, by, WZ), BELT_W, BELT_T, LEATHER)
    d.ring("z", (DYN_X, DYN_H, WZ), PULLEY_R + BELT_T / 2.0, BELT_T, BELT_W, LEATHER, sides=20,
           arc=(90.0 + LEAN, 270.0 - LEAN))
    return d


def _lap():
    """The belt's lap round the flywheel: it lies on the rim's far side and stands still while the
    wheel turns under it."""
    d = _Draw("lap", (0.0, H, WZ))
    d.ring("z", (0.0, H, WZ), WHEEL_R + BELT_T / 2.0, BELT_T, BELT_W, LEATHER, sides=32,
           arc=(-90.0 - LEAN, 90.0 + LEAN))
    return d


def _dynamo():
    """The dynamo's standing part: slide rails, the ring of poles with their coils, two bearings,
    the brush ring and the terminals."""
    d = _Draw("dynamo", (DYN_X, 0.0, DYN_Z + 0.25))
    c = (DYN_X, DYN_H, DYN_Z)
    for z in (DYN_Z - 0.5, DYN_Z + 0.5):                                              # the rails it is drawn up on
        d.box((DYN_X - 1.3125, 0.0, z - 0.125), (DYN_X + 1.3125, 0.125, z + 0.125), IRON_D)
    d.ring("z", c, YOKE_R - 0.125, 0.25, 0.75, IRON, sides=24)                        # the yoke
    for s in (-1.0, 1.0):                                                             # its feet
        xa, xb = sorted((DYN_X + s * 0.5, DYN_X + s * 1.125))
        d.box((xa, 0.125, DYN_Z - 0.4375), (xb, 0.375, DYN_Z + 0.4375), IRON)
    for i in range(POLES):                                                            # poles and field coils
        a = 30.0 + 360.0 * i / POLES
        d.box((0.5625 + DYN_X, DYN_H - 0.125, DYN_Z - 0.3125), (0.8125 + DYN_X, DYN_H + 0.125, DYN_Z + 0.3125), IRON_D,
              rot=("z", a, c))
        d.box((0.625 + DYN_X, DYN_H - 0.21875, DYN_Z - 0.4375), (0.8125 + DYN_X, DYN_H + 0.21875, DYN_Z + 0.4375),
              WOUND, rot=("z", a, c), grain="y")
    for z0, z1 in ((DYN_Z - 1.1875, DYN_Z - 0.9375), (DYN_Z + 0.5625, DYN_Z + 0.8125)):       # the bearings
        d.box((DYN_X - 0.4375, 0.0, z0), (DYN_X + 0.4375, 0.125, z1), IRON_D)
        d.box((DYN_X - 0.25, 0.125, z0), (DYN_X + 0.25, DYN_H - 0.125, z1), IRON)
        d.tube("z", (DYN_X, DYN_H), z0, z1, 0.21875, IRON, sides=8)
        d.tube("z", (DYN_X, DYN_H), z0 - PX, z1 + PX, 0.15625, BRASS, sides=8)
        d.tube("y", (DYN_X, (z0 + z1) / 2.0), DYN_H + 0.21875, DYN_H + 0.375, 0.0625, BRASS, sides=8)
    # the brush ring round the commutator, two brush holders
    d.ring("z", (DYN_X, DYN_H, DYN_Z - 0.625), 0.40625, 0.0625, 0.0625, BRASS_D, sides=16)
    for a in (35.0, 215.0):
        d.box((DYN_X + 0.28, DYN_H - 0.0625, DYN_Z - 0.75), (DYN_X + 0.5, DYN_H + 0.0625, DYN_Z - 0.5), BRASS,
              rot=("z", a, (DYN_X, DYN_H, DYN_Z - 0.625)))
    # the terminal board on top
    top = DYN_H + YOKE_R
    d.box((DYN_X - 0.4375, top, DYN_Z - 0.1875), (DYN_X + 0.4375, top + 0.125, DYN_Z + 0.1875), IRON_D)
    for s in (-1.0, 1.0):
        d.tube("y", (DYN_X + s * 0.25, DYN_Z), top + 0.125, top + 0.25, 0.09375, PORCELAIN, sides=8)
        d.tube("y", (DYN_X + s * 0.25, DYN_Z), top + 0.25, top + 0.3125, 0.046875, BRASS, sides=4)
    return d


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


# name: (what draws it, what registers its motion)
PARTS = {
    "bed": (_bed, None),
    "frame": (_frame, None),
    "cylinder": (_cylinder, None),
    "crosshead": (_crosshead, _move_crosshead),
    "rod": (_rod, _move_rod),
    "flywheel": (_flywheel, _move_flywheel),
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


def _scene(p, origin=(0, 0, 0)):
    """A point of the engine's frame in scene coordinates."""
    return (SHAFT_X + p[0] + origin[0], FLOOR + p[1] + origin[1], LINE_Z + p[2] + origin[2])


def pit(canvas, origin=(0, 0, 0)):
    """Dig the pit and line it: brick under it and beside it below the floor's own course."""
    ox, oy, oz = (int(v) for v in origin)
    top = int(FLOOR) - 1
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
    """Dig the pit, place the set and say what moves. Returns the number of display entities."""
    pit(canvas, origin)
    n = 0
    for name, d in _drawn().items():
        x, y, z = _scene(d.at, origin)
        canvas.add_entity(x, y, z, M.display(d.m, scale=d.scale))
        n += 1
        move = PARTS[name][1]
        if move is not None:
            n += move(canvas)
    return n


def _report():
    for name, d in _drawn().items():
        lo, hi = d.m.bounds()
        print(f"{d.m.name:24s} scale {d.scale:g}  {len(d.m.parts):4d} boxes  "
              f"span {' '.join(f'{(hi[i] - lo[i]) / d.u:5.2f}' for i in range(3))} blocks")
    print(f"{len(PARTS)} entities; lean of the belt {LEAN:.2f} degrees; pulley radius {PULLEY_R:.3f}")


if __name__ == "__main__":
    _report()
