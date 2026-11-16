"""The two engines on the chart room's light table (interiors/chartroom places them; these are only
the models, one display entity each):

  bridge()        "int_chart_bridge": the plate measuring engine. A bridge across the table that
                  rides on the two long sides of its brass frame, over the plate that is being
                  measured. From the hand to the plate: the crank on the divided drum turns the lead
                  screw that lies along the front of the bed; the screw draws the carriage along the
                  bed; the carriage carries the microscope, whose nose looks straight down at the
                  plate and whose tube leans out to the observer on the stool. Whole turns are read
                  on the scale let into the bed, parts of a turn on the drum under its index. The
                  lever at the other end clamps the bridge to the table.
  viewer(plate)   "int_chart_viewer": the plate viewer. A lamp house with a screen of lit opal
                  glass, hung in trunnions between two iron standards that stand on the table's
                  frame; it leans back and is clamped by the two hand wheels, a divided arc on its
                  cheek says how far. The plate stands on a brass ledge before the screen, two
                  clips hold its head, and a reading glass on a sliding stem stands over the part
                  that is being looked at. `plate` is the picture of the plate's face.

Both are drawn in texels about the same anchors as the stand-ins they replace (chartroom.py at
1939bfc3): the bridge LIFT over the middle of its foot on the table's frame, x across the table and
-z the side the door sees; the viewer LIFT over the middle of the foot of its face on the glass, its
face looking along +z.

What V9 asks of the bridge (chart, 11-16): within LOW of the room's axis nothing of it rises more
than LOW_TOP over the frame, or it would stand before the comet on the viewer; at the two sides it
may rise to SIDE_TOP. So the tall things, the microscope's tube and the drum, are at the observer's
end, and the middle is the bed, the screw and the scale, low over the lit glass. clearance() says
by how much the rule is kept; `python -m scenes.obs.interiors._chartengine` prints it.
"""
import math

import numpy as np

from artkit import models as M

from ..common import palette as P
from ..props import _kit as K

PREFIX = "int_chart_"
LIFT = 2.0                  # both anchors are held this far over the foot: in the row over the glass, where the table's
#                             sources are (chartroom.LIFT)

IRON, IRON_D, BRASS, BRASS_D = K.IRON, K.IRON_D, K.BRASS, K.BRASS_D
WOOD = P.mat("dark_wood")
WOOD_L = P.mat("dark_wood", base=3)
WOOD_D = P.mat("dark_wood", base=1)
OPAL = P.mat("opal")                    # lit opal glass, the room's one bright thing
PLATE_SIDE = K.flat("opal", 0)          # the edge of a glass negative
SLOT = K.flat("opal", 1)                # the lamps seen through a louvre
LIT = dict(emit=15, shade=False)


def _sheet(w, h, tone):
    out = np.empty((h, w, 4), dtype=np.uint8)
    out[..., :3] = tone
    out[..., 3] = 255
    return out


class _Thread:
    """The lead screw: bright brass with the thread cut into it, a turn to every two texels. It
    stands in for a material (artkit.models asks a material for its name and paint() only)."""

    name = "chart_thread"

    def paint(self, w, h, grain="u", seed=0):
        if grain == "cap":
            return _sheet(w, h, P.colour("brass", 2))
        out = _sheet(w, h, P.colour("brass", 4))
        if grain == "u":
            out[:, 1::2, :3] = P.colour("brass", 1)
        else:
            out[1::2, :, :3] = P.colour("brass", 1)
        return out


class _Rule:
    """A divided scale: a division on every other texel, every fifth of them a long one."""

    name = "chart_rule"

    def paint(self, w, h, grain="u", seed=0):
        out = _sheet(w, h, P.colour("brass", 4))
        if grain != "u":
            return out
        short = h - max(1, h // 2)
        for i, x in enumerate(range(1, w, 2)):
            out[(0 if i % 5 == 0 else short):, x, :3] = P.colour("brass", 0)
        return out


class _Drum:
    """The rim of a divided drum: the divisions are lines along it, one to every face of the prism,
    and stop short of the edge that is away from the index."""

    name = "chart_drum"

    def paint(self, w, h, grain="u", seed=0):
        if grain == "cap":
            return _sheet(w, h, P.colour("brass", 2))
        out = _sheet(w, h, P.colour("brass", 4))
        if grain == "u":
            out[0, max(0, w - max(2, w - 1)):, :3] = P.colour("brass", 0)
        else:
            out[max(0, h - max(2, h - 1)):, 0, :3] = P.colour("brass", 0)
        return out


THREAD, RULE, DRUM = _Thread(), _Rule(), _Drum()

# ---- the measuring bridge ------------------------------------------------------------------------
# x across the table (the observer's stool stands on -x, the west side), y from the top of the
# table's brass frame, -z towards the door. The frame's long sides are 13..15 from the middle and
# the glass lies a quarter of a texel under their top; a plate on it is half a texel thick.
LOW, LOW_TOP = 10.0, 5.0    # within LOW of the axis nothing rises more than LOW_TOP over the frame
SIDE_TOP = 14.0             # and nothing anywhere more than this
BED_Y = (0.75, 4.5)         # the bed: clear of the plates under it, and its top
BED_Z = (0.5, 3.5)
SCREW = (1.7, -0.75)        # the lead screw's axis (y, z): along the front of the bed
SCREW_R = 0.8
STANDARD = (13.0, 15.25)    # the two standards the bed is bolted between, on the frame's long sides
DRUM_X = (-19.25, -15.75)   # the divided drum on the observer's end of the screw
DRUM_R = 3.5
NOSE = (-9.75, -3.5)        # the microscope's nose (x, z): over the plate, clear of the bed and the screw
TUBE_FROM = (-11.0, 3.5)    # where the tube leaves the prism house (x, y) ...
TUBE_LEAN = 40.0            # ... leaning this far from the plumb line towards the observer
TUBE_LEN = 10.5


def bridge():
    """The plate measuring engine. Anchor: LIFT over the middle of its foot on the table's frame."""
    m = M.Model(PREFIX + "bridge", anchor=(0.0, LIFT, 0.0))
    y, z = SCREW
    # the two standards: a shoe on the frame's long side and an upright
    for s in (-1.0, 1.0):
        m.box((s * 12.5, 0.0, -4.0), (s * 15.5, BED_Y[0], 4.5), IRON_D, grain="z")
        m.box((s * STANDARD[0], BED_Y[0], -2.25), (s * STANDARD[1], BED_Y[1] + 0.25, 4.0), IRON, grain="z")
    # the bed between them, the scale let into its two faces and its top
    m.box((-STANDARD[0], BED_Y[0], BED_Z[0]), (STANDARD[0], BED_Y[1], BED_Z[1]), IRON_D, grain="x", skip="ew")
    for face, at in (("n", (BED_Z[0] - 0.2, BED_Z[0])), ("s", (BED_Z[1], BED_Z[1] + 0.2))):
        m.box((-12.5, 2.85, at[0]), (12.5, 4.35, at[1]), BRASS, grain="x", skip="ns".replace(face, ""), faces={face: RULE})
    m.box((-12.5, BED_Y[1], 1.25), (12.5, BED_Y[1] + 0.1, 2.75), BRASS, grain="x", skip="d", faces={"u": RULE})
    # the lead screw along the front of the bed, from the far standard through the near one to the drum
    m.tube("x", SCREW, DRUM_X[1], STANDARD[0], SCREW_R, THREAD)
    m.tube("x", SCREW, STANDARD[1], STANDARD[1] + 0.4, 1.2, BRASS_D)                # its end in the far standard
    # the divided drum, the index over it, the crank
    m.tube("x", SCREW, DRUM_X[0], DRUM_X[1], DRUM_R, DRUM, sides=12)
    m.tube("x", SCREW, DRUM_X[1], -STANDARD[1], 1.5, BRASS_D)
    m.box((-STANDARD[1], BED_Y[1] + 0.25, z - 0.5), (-13.5, y + DRUM_R + 0.6, z + 0.5), IRON_D, grain="x")
    m.box((DRUM_X[0] + 1.25, y + DRUM_R + 0.1, z - 0.5), (-STANDARD[1], y + DRUM_R + 0.6, z + 0.5), IRON_D, grain="x")
    m.tube("x", SCREW, DRUM_X[0] - 0.5, DRUM_X[0], 2.5, IRON, sides=12)
    m.tube("x", (y + 1.5, z), DRUM_X[0] - 2.25, DRUM_X[0] - 0.5, 0.7, WOOD_L)
    # the carriage: a saddle on the bed, and an apron down its front with the nut the screw runs in
    m.box((-12.75, BED_Y[1], -2.25), (-7.0, LOW_TOP, 3.75), IRON, grain="x")
    m.box((-12.25, 0.6, -2.25), (-7.5, BED_Y[1], BED_Z[0]), IRON, grain="x", skip="u")
    # the microscope: the nose over the plate, the prism house on the apron, the focusing head on the
    # side the door sees, and the tube leaning out to the observer: brass, a clamp ring, the draw
    # tube and the eyepiece
    m.tube("y", NOSE, 0.4, 2.0, 0.8, IRON_D)
    m.box((-12.0, 2.0, -4.75), (-8.75, LOW_TOP, -2.25), IRON, grain="x")
    m.tube("z", (NOSE[0], 3.5), -5.75, -4.75, 1.0, BRASS)
    lean = math.radians(TUBE_LEAN)
    a = (TUBE_FROM[0], TUBE_FROM[1], NOSE[1])
    b = (a[0] - TUBE_LEN * math.sin(lean), a[1] + TUBE_LEN * math.cos(lean), NOSE[1])
    with m.aimed(a, b, "y"):
        m.tube("y", (0.0, 0.0), 0.0, 7.0, 1.25, BRASS)
        m.tube("y", (0.0, 0.0), 3.0, 4.0, 1.5, IRON_D)
        m.tube("y", (0.0, 0.0), 7.0, 9.0, 1.0, BRASS_D)
        m.tube("y", (0.0, 0.0), 9.0, TUBE_LEN, 1.4, IRON_D)
    # the clamp at the far end: a lever on a boss on the standard, with a wooden grip
    m.tube("y", (14.1, 1.0), BED_Y[1] + 0.25, 6.5, 1.0, BRASS_D)
    m.box((13.6, 5.5, 0.5), (18.0, 6.25, 1.5), BRASS, grain="x")
    m.tube("x", (5.9, 1.0), 18.0, 19.0, 0.9, WOOD_L)
    return m


def clearance(model=None):
    """How far the bridge keeps under what V9 allows: (over the middle, at the sides), texels to
    spare; a negative number is a part that stands too high. Every box is tried at a lattice of its
    own points, turned into place."""
    model = model or bridge()
    spare = [1e9, 1e9]
    steps = [i / 6.0 for i in range(7)]
    for p in model.parts:
        c = [(p["lo"][i] + p["hi"][i]) / 2.0 for i in range(3)]
        h = [(p["hi"][i] - p["lo"][i]) / 2.0 for i in range(3)]
        q = p["rot"][0] if p["rot"] else M.IDENT
        for tx in steps:
            for ty in steps:
                for tz in steps:
                    v = M._qrot(q, tuple(h[i] * (2.0 * t - 1.0) for i, t in enumerate((tx, ty, tz))))
                    x, y = c[0] + v[0], c[1] + v[1]
                    if abs(x) <= LOW:
                        spare[0] = min(spare[0], LOW_TOP - y)
                    spare[1] = min(spare[1], SIDE_TOP - y)
    return tuple(round(v, 3) for v in spare)


# ---- the plate viewer ----------------------------------------------------------------------------
# x across the table, y from the top of the glass, +z the way the face looks. The lamp house is
# drawn upright in its own frame (its face in the plane z 0, its foot on y 0) and then leant back
# about the lower edge of its back, as the stand-in was; it hangs FOOT clear of the glass.
VIEW_W, VIEW_H = 26.0, 24.0     # the face, across and high
VIEW_TILT = -20.0               # it leans back by this
FOOT = 0.75
HINGE_Z = -2.0
DEPTH = 6.5                     # the lamp house behind the face
PLATE = ((-9.0, 3.0), (9.0, 21.0))      # the plate before the screen: 18 by 18 on the ledge
TRUNNION = (11.0, -4.0)         # the axis the house hangs on, in the house's frame (y, z): the middle of its cheek
STANDARD_X = 14.0               # the middle of a standard: on the long side of the table's frame
LOOK_AT = (-3.0, 9.0)           # what the reading glass stands over, on the face (x, y): the comet's head


def _leant(y, z):
    """A point (y, z) of the house's own frame, where it is once the house leans back."""
    a = math.radians(VIEW_TILT)
    dz = z - HINGE_Z
    return FOOT + y * math.cos(a) - dz * math.sin(a), HINGE_Z + y * math.sin(a) + dz * math.cos(a)


def viewer(plate, glass=True):
    """The plate viewer; `plate` is the picture on the plate's face. glass=False leaves the reading
    glass off. Anchor: LIFT over the middle of the foot of its face."""
    m = M.Model(PREFIX + "viewer", anchor=(0.0, LIFT, 0.0))
    hw = VIEW_W / 2.0
    with m.moved((0.0, FOOT, 0.0)), m.turned(("x", VIEW_TILT), about=(0.0, 0.0, HINGE_Z)):
        # the lamp house and the frame of its face, brass plates on the frame's corners
        m.box((-hw + 1, 1, -DEPTH), (hw - 1, VIEW_H - 1, -1.5), WOOD_D, grain="x", skip="s")
        for x in (-hw, hw - 2.0):
            m.box((x, 0, -2), (x + 2, VIEW_H, 0), WOOD, grain="y")
            for y in (0.0, VIEW_H - 2.0):
                m.box((x, y, 0), (x + 2, y + 2, 0.2), BRASS_D, skip="n")
        m.box((-hw + 2, 0, -2), (hw - 2, 2, 0), WOOD, grain="x", skip="ew")
        m.box((-hw + 2, VIEW_H - 2, -2), (hw - 2, VIEW_H, 0), WOOD, grain="x", skip="ew")
        # the screen, and the plate before it with the light behind it
        m.box((-hw + 2, 2, -1.5), (hw - 2, VIEW_H - 2, -1), OPAL, skip="nudew", **LIT)
        (x0, y0), (x1, y1) = PLATE
        m.box((x0, y0, -1), (x1, y1, -0.5), PLATE_SIDE, skip="n", faces={"s": plate}, **LIT)
        # the ledge the plate stands on, with a lip; the two clips that hold its head
        m.box((x0 - 1, y0 - 1, -1), (x1 + 1, y0, 0.75), BRASS_D, grain="x")
        m.box((x0 - 1, y0, 0.25), (x1 + 1, y0 + 0.5, 0.75), BRASS_D, grain="x", skip="d")
        for x in (-6.0, 6.0):
            m.box((x - 0.5, y1 - 0.5, -1), (x + 0.5, y1 + 1, -0.25), BRASS_D)
        if glass:
            # the reading glass: a slider on the ledge's lip, a stem, the ring of the lens
            gx, gy = LOOK_AT
            m.box((gx - 1.0, y0 - 0.75, 0.75), (gx + 1.0, y0 + 0.75, 1.5), BRASS, grain="x")
            m.rod((gx, y0 + 0.75, 1.1), (gx, gy - 3.4, 1.9), 0.4, BRASS_D, sides=4)
            m.ring("z", (gx, gy, 1.9), 3.0, 0.8, 0.8, BRASS, sides=12)
        # the cowl over the lamps and its lid; the louvres of the back; the cable's gland
        m.box((-7, VIEW_H - 1, -DEPTH + 0.5), (7, VIEW_H + 0.75, -2.5), IRON_D, grain="x", skip="d")
        m.box((-8, VIEW_H + 0.75, -DEPTH), (8, VIEW_H + 1.5, -2.0), IRON, grain="x")
        for x in (-6.0, 0.0, 6.0):
            for y in (15.0, 18.0):
                m.box((x - 2, y, -DEPTH - 0.25), (x + 2, y + 1, -DEPTH), SLOT, skip="s", **LIT)
        m.tube("z", (-8.0, 4.0), -DEPTH - 1.0, -DEPTH, 0.75, IRON_D)
    ty, tz = _leant(*TRUNNION)
    for s in (-1.0, 1.0):
        x = s * STANDARD_X
        # a standard: a foot along the table's frame, two legs up to the bearing
        m.box((x - 1.0, 0.25, tz - 7.0), (x + 1.0, 1.25, tz + 7.0), IRON_D, grain="z")
        for end in (-6.0, 6.0):
            m.beam((x, 1.0, tz + end), (x, ty, tz), 1.5, 1.5, IRON)
        m.tube("x", (ty, tz), s * 13.0, s * 15.25, 1.9, IRON, sides=12)
        # the trunnion, the divided arc on the house's cheek, the hand wheel that clamps it
        m.tube("x", (ty, tz), s * (hw - 1), s * 13.0, 1.0, IRON_D)
        m.ring("x", (s * 12.5, ty, tz), 5.5, 0.9, 0.5, BRASS_D, sides=24, arc=(125.0, 235.0))
        m.tube("x", (ty, tz), s * 15.25, s * 16.5, 2.25, DRUM, sides=12)
        m.tube("x", (ty, tz), s * 16.5, s * 17.0, 0.8, IRON_D)
    # the tie between the standards' feet behind the house
    m.rod((-STANDARD_X + 1.0, 0.75, tz - 6.5), (STANDARD_X - 1.0, 0.75, tz - 6.5), 0.5, IRON_D, sides=4)
    # the cable: from the gland over the east standard's foot and down the table's side to its lamp box
    gy, gz = _leant(4.0, -DEPTH - 1.0)
    m.hose([(-8.0, gy, gz), (-11.0, 1.2, gz - 2.0), (-15.7, 1.8, gz - 3.0), (-15.7, -4.0, gz - 3.0)], 0.45, IRON_D, sides=4)
    m.tube("x", (-4.0, gz - 3.0), -15.9, -15.0, 0.9, BRASS_D)
    return m


if __name__ == "__main__":
    over_axis, at_sides = clearance()
    print(f"bridge: {len(bridge().parts)} boxes; under V9's line by {over_axis} over the axis, {at_sides} at the sides")
