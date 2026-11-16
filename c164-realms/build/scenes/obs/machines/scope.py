"""The great refractor of the dome room (plan/ART-PLAN.md 7.2; parts/A5-machines.md 2.1; card
plan/packages/machines/refractor.md). The star of view V8.

A riveted iron tube fifteen blocks long on an equatorial mount, standing on the cap of the pier
under the middle of the great dome and looking due west through the slit at the head of the comet.
Two mounts were drawn. The director picked a (11-16): build() and models() bring a alone; b
stays in this file and in the test scene, to be looked at beside it:

  a  German equatorial   one cast-iron pier in bolted sections; the polar axis lies in a sleeve
                         on its head, the declination axis crosses its upper end; the tube rides
                         on one end of that, a stack of counterweights on the other
  b  English yoke        the polar axis is a riveted frame, widest in the middle, that swings
                         between a pedestal in the south and a trestle in the north; the tube
                         hangs in the middle of the frame, on the axis of the dome

What the other lines read (scene coordinates; give the origin to have it added):

    scope.eyepiece()    the middle of the eyepiece's end face
    scope.objective()   the middle of the objective's end face
    scope.observer()    where the observer's feet stand; the eye is then on the tube's axis
    scope.sweep()       (centre, radius) of the ball no part of the instrument leaves, however
                        it is pointed: the dome's gear, its lamps and the room keep out of it
    scope.EYEPIECE, OBJECTIVE, OBSERVER, SWEEP      the same numbers by version, {"a": ..., "b": ...}
    scope.v8()          (position, look_at) of the camera of view V8: a standing eye at the east
                        edge of the observing floor, on the side the mount shows best from
    scope.V8            the same by version
    scope.ELEVATION     degrees the tube looks up, due west: the comet's head (sky/comet)
    scope.BRIGHTNESS    the light every piece is shown in, whatever cell it hangs in
    scope.solid()       the cells build() fills with a barrier: the inside of the pier's iron

    scope.FOLLOW, FOLLOW_PERIOD     degrees the mount turns to either side of where it was set,
                        and the ticks one turn there and back takes
    scope.followed(p, degrees)      where a point the mount carries (the eyepiece, a rung of the
                        observer's ladder beside it) is when the mount has turned so far

Every function takes version= ("a" or "b"; VERSION, the one that was picked, when left out).

What moves (plan/round2.md; motion/_kit does the moving). The driving clock turns the polar axis
after the comet, and the observer brings it back: the axis piece (a) or the yoke (b), the tube and
the lamp on its tail swing together about the polar axis, FOLLOW degrees to either side of where
the tube was set, slowly, for ever. The governor on the clock spins about its spindle. The motion
line turns a display entity about the spot it stands on, so the three that swing stand on the
crossing of the axes, which is on the polar axis, and hold their models out from there. What is
placed is the middle of the swing, and every number above is taken there. The tube does not turn
about the declination axis: nothing here drives that.

Light: the room is kept dark for observing. The one lamp is the small red one beside the
eyepiece, hooded, its glass turned west on the tailpiece and away from the floor; the light it
throws is offered to the sky line at LAMP_LEVEL. In the hood's back, towards the floor and the
camera of V8, is a ruby peep-hole: a point of red, no light. The lamp is the only red in the room
(A0): the governor's collar, which the card would have signal red, is old copper.

    python -m scenes.obs.machines.scope      the numbers above and the rules they are held to
"""
import copy
import functools
import math

import numpy as np

from artkit import models as M
from artkit.pixelart import Mat

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..props import _kit as K

try:
    from ..motion import _kit as MK
except ImportError:                     # the motion line is not in the tree: everything stands still
    MK = None

PREFIX = "mach_scope_"
VERSION = "a"                   # the version build() places: the director's pick (11-16)
VERSIONS = ("a", "b")
BRIGHTNESS = (10, 7)            # (sky, block): agreed with the light line for the dark dome room
LAMP_LEVEL = 4                  # the red lamp's light source (A0: not over 4)


# ---- directions and points (blocks, scene coordinates) ---------------------------------------------
def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _mul(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a):
    n = math.sqrt(_dot(a, a))
    return (a[0] / n, a[1] / n, a[2] / n)


def _neg(a):
    return (-a[0], -a[1], -a[2])


def _elevation():
    """Degrees up of the comet's head, due west: the sky line's number once its card is in."""
    try:
        from ..sky import comet
    except ImportError:
        return 41.05
    return float(getattr(comet, "HEAD_ELEVATION", 41.05))


ELEVATION = _elevation()
LATITUDE = S.LATITUDE
# How far from the upright the castings of a still model lean that carry the polar axis: a tenth of
# a degree more than the pole itself. The game lights a face of a model as if it looked along the
# axis of the model nearest its normal. Cast true to a latitude of 45 degrees, every face of them
# would stand exactly between two axes, and which of the two it is filed under comes out of the last
# bit of a float, face by face (props/_kit.settle). Leant a hair more, what lies on top of the slope
# is lit as a top and what lies under it as an underside, the two ends as upright faces: in every
# copy of the game as in the pictures.
LEAN = 90.0 - LATITUDE + K.SETTLE
AXIS = S.DOME_AXIS              # (4.5, 0.5): the middle of the pier's cap, what the dome turns about
CAP_Y = S.PIER_TOP_Y            # 18.0: the top of the cap; the foot stands on it
FLOOR_Y = float(S.ROOF_STAND)   # the observing floor
EAST, UP, SOUTH = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)
WORLD = (EAST, UP, SOUTH)

_E, _L = math.radians(ELEVATION), math.radians(LATITUDE)
SIGHT = (-math.cos(_E), math.sin(_E), 0.0)              # the way the tube looks: west and up
POLE = (0.0, math.sin(_L), -math.cos(_L))               # the polar axis: north and up
DEC = _unit(_cross(POLE, SIGHT))                        # the declination axis: east, up and south
NORMAL = _cross(POLE, DEC)                              # square to both axes: east and down
OVER = (math.sin(_E), math.cos(_E), 0.0)                # square to the tube in the vertical plane, upwards
DIURNAL = _neg(POLE)                                    # the sky turns about this, right-handed: in the west it sinks, northwards

# The mount follows the comet and comes back (plan/round2.md): it swings about the polar axis, the
# way the sky goes first. 2 degrees take the eyepiece 0.2 blocks to either side, 0.14 of them up
# and down; much further and the tail would come down into the face of somebody who stands on the
# observing floor (report() measures both ends of the swing).
FOLLOW = 2.0                    # degrees to either side of where the tube was set
FOLLOW_PERIOD = 480             # ticks there and back: 24 seconds. Slow enough for cast iron; from the camera of
#                                 V8 the tail is seen to creep, some eight pixels a second where it is quickest

TUBE_LEN = 15.0
TUBE_R = 0.75                   # the body; the objective's cell is CELL_R
CELL_R = 15.0 / 16.0
# rise: the height of the axes' crossing over the cap. off: how far the tube's axis is from the
# crossing, along the declination axis. back: from the declination axis to the eyepiece's end.
# show: the side the version shows the camera of V8, 1 the south, -1 the north: the mount of a is
# north of its tube (which is off the axis, in the plane z = 1.40), the pedestal of b south of
# its tube. The red lamp hangs on that side, the seams of the tube's plates run down it.
# finder, weights, seam: where the finder, the weights that balance it and the seams ride, in
# degrees round the tube from north over the top. The finder is seen over the tube's far edge
# from the camera of V8; b's can only be square to the trunnions. Every ring of the tube is two
# plates: its other seam is straight across. rods: the two clamp rods, in degrees round the tube
# from the upper end of the declination axis.
_SPEC = {
    "a": dict(rise=5.0, off=0.9 / DEC[2], back=6.39, show=-1.0,
              finder=90.0, weights=235.0, seam=(0.0, 30.0), rods=(158.0, 202.0)),
    "b": dict(rise=5.4, off=0.0, back=5.5, show=1.0,
              finder=37.0, weights=217.0, seam=(180.0, 150.0), rods=(-22.0, 22.0)),
}
V8_STAND = (12.7, 2.1)          # the camera of V8: x, and how far it stands from the tube's plane, to the side shown
OBSERVING = (S.PIER_ENVELOPE[2] + 1, S.DOME_CENTRE[1] - 1, S.PIER_ENVELOPE[2] + 5, S.DOME_CENTRE[1] + 3)
#                                 the observing floor (A0, plan/STATUS.md domeroom): columns x 8..12, z -1..3
V8_LOOK = (0.0, 25.2, 0.9)      # what it looks at: up the slit, under the comet's head


def _version(version):
    version = VERSION if version is None else version
    if version not in _SPEC:
        raise ValueError(f"no version {version!r} of the refractor; there are {', '.join(VERSIONS)}")
    return version


def crossing(version=None, origin=(0, 0, 0)):
    """Where the polar and the declination axis cross."""
    spec = _SPEC[_version(version)]
    return _add((AXIS[0], CAP_Y + spec["rise"], AXIS[1]), origin)


def pivot(version=None, origin=(0, 0, 0)):
    """Where the declination axis meets the tube's axis: what the tube turns about."""
    return _add(crossing(version, origin), _mul(DEC, _SPEC[_version(version)]["off"]))


def eyepiece(version=None, origin=(0, 0, 0)):
    return _add(pivot(version, origin), _mul(SIGHT, -_SPEC[_version(version)]["back"]))


def objective(version=None, origin=(0, 0, 0)):
    return _add(pivot(version, origin), _mul(SIGHT, TUBE_LEN - _SPEC[_version(version)]["back"]))


def observer(version=None, origin=(0, 0, 0)):
    """The observer's feet: behind the eyepiece, where a standing eye is on the tube's axis."""
    e = eyepiece(version)
    k = (e[1] - (FLOOR_Y + S.EYE)) / SIGHT[1]
    x, _y, z = _add(e, _mul(SIGHT, -k))
    return _add((x, FLOOR_Y, z), origin)


def sweep(version=None, origin=(0, 0, 0)):
    """(centre, radius): the ball about the crossing that the rim of the objective's cell
    describes; nothing of the instrument reaches further, however it is pointed."""
    spec = _SPEC[_version(version)]
    far = math.hypot(TUBE_LEN - spec["back"], spec["off"] + CELL_R)
    return crossing(version, origin), math.ceil(far * 10.0) / 10.0


def _turned(v, axis, degrees):
    """A direction turned about a unit axis, right-handed."""
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    return _add(_add(_mul(v, c), _mul(_cross(axis, v), s)), _mul(axis, _dot(axis, v) * (1.0 - c)))


def followed(p, degrees, version=None, origin=(0, 0, 0)):
    """Where a point that turns with the polar axis is when the mount has turned `degrees` the
    way the sky goes from where it was set; the other way when negative. p is given as the mount
    stands when placed, in the coordinates the origin puts it in. The mount swings between
    FOLLOW and -FOLLOW: FOLLOW * sin(2 pi t / FOLLOW_PERIOD), t ticks after the loop starts."""
    c = crossing(version, origin)
    return _add(c, _turned(_sub(p, c), DIURNAL, degrees))


def v8(version=None, origin=(0, 0, 0)):
    """(position, look_at) of the camera of view V8."""
    spec = _SPEC[_version(version)]
    at = (V8_STAND[0], FLOOR_Y + S.EYE, pivot(version)[2] + spec["show"] * V8_STAND[1])
    return _add(at, origin), _add(V8_LOOK, origin)


def _rounded(p):
    return tuple(round(v, 3) for v in p)


EYEPIECE = {v: _rounded(eyepiece(v)) for v in VERSIONS}
OBJECTIVE = {v: _rounded(objective(v)) for v in VERSIONS}
OBSERVER = {v: _rounded(observer(v)) for v in VERSIONS}
SWEEP = {v: (_rounded(sweep(v)[0]), sweep(v)[1]) for v in VERSIONS}
V8 = {v: tuple(_rounded(p) for p in v8(v)) for v in VERSIONS}

# the frames the moving pieces are drawn in: the world's directions of a model's x, y and z. Each
# is chosen so that the light painted into round shapes (artkit.models.LIGHT) falls from above.
TUBE_FRAME = (_neg(SOUTH), OVER, _neg(SIGHT))           # z runs down the tube to the eyepiece
AXIS_FRAME = (_neg(NORMAL), POLE, _neg(DEC))            # a: z runs out to the counterweight
YOKE_FRAME = (NORMAL, DEC, _neg(POLE))                  # b: z runs down the frame to the south

TUBE_SCALE, MOUNT_SCALE, YOKE_SCALE = 5.0, 2.0, 3.0


# ---- materials -------------------------------------------------------------------------------------
class Studded(Mat):
    """Plate with a row of rivet heads along the middle of a narrow face: a head is one light
    texel with a dark one in its shadow, `pitch` texels from the next (materials/iron)."""
    pitch = 3
    widest = 6          # a face wider than this is a plate's field, not its seam

    def levels(self, w, h, grain, seed):
        lv = super().levels(w, h, grain, seed)
        if min(w, h) > self.widest or max(w, h) < 3:
            return lv
        if w >= h:
            row = (h - 1) // 2
            for x in range(self.pitch // 2, w, self.pitch):
                lv[row, x] = self.base + 2
                if row + 1 < h:
                    lv[row + 1, x] = self.base - 2
        else:
            col = (w - 1) // 2
            for y in range(self.pitch // 2, h - 1, self.pitch):
                lv[y, col] = self.base + 2
                lv[y + 1, col] = self.base - 2
        return lv


class Ticked(Mat):
    """The band of a setting circle or the rim of a toothed wheel: every other texel along the
    band is a division, every `long`-th division a deeper one."""
    long = 4

    def levels(self, w, h, grain, seed):
        lv = super().levels(w, h, grain, seed)
        if grain == "cap":
            return lv
        jj, ii = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        along = ii if grain == "u" else jj
        lv = lv - (along % 2 == 1)
        if self.long:
            lv = lv - (along % (2 * self.long) == 1)
        return lv


def _as(cls, mat, tag, **more):
    """`mat` painted the way of `cls`: the same ramp, tone and bevel."""
    m = copy.copy(mat)
    m.__class__ = cls
    m.name = f"{mat.name}~{tag}"
    m._variants = {}
    m.__dict__.update(more)
    return m


def _flat(name, step):
    return P.mat(name, kind="flat", base=step, bevel=0)


IRON, IRON_D = P.mat("iron"), P.mat("iron_dark")
BRASS, BRASS_D = P.mat("brass"), P.mat("brass_dark")
COPPER = P.mat("old_copper")
TUBE = P.mat("iron", base=4)                            # the tube's plates: a step lighter than the castings
STEEL = P.mat("iron", base=5)                           # bright shafts and journals
WOOD = P.mat("dark_wood")                               # grips
IRON_STUD = _as(Studded, IRON, "stud")
IRON_D_STUD = _as(Studded, IRON_D, "stud")
IRON_SEAM = _as(Studded, IRON, "seam", pitch=4)
TUBE_STUD = _as(Studded, TUBE, "stud")
TUBE_SEAM = _as(Studded, TUBE, "seam", pitch=4)
BRASS_STUD = _as(Studded, BRASS_D, "stud")
BRASS_TICK = _as(Ticked, P.mat("brass", bevel=0), "tick")
IRON_TOOTH = _as(Ticked, P.mat("iron_dark", bevel=0), "tooth", long=0)
GLASS = _flat("night_glass", 2)
GLASS_D = _flat("night_glass", 0)
RED_LENS = _flat("signal_glow", 2)                      # the lamp alone is red (A0): its glass and its peep-hole
RED_HOT = _flat("signal_glow", 3)
HOOD = _flat("iron", 0)
DIAL = _flat("cream", 2)
HOOP_SEED, STRAP_SEED, CONE_SEED = 9001, 9002, 9005


class _Px:
    """Draws on a model in texels, sixteen to the block, whatever the model's scale is."""

    def __init__(self, name, scale):
        self.m = M.Model(name, px=float(scale))
        self.k = 1.0 / float(scale)

    def p(self, v):
        return tuple(x * self.k for x in v)

    def box(self, lo, hi, mat, rot=None, **kw):
        if rot is not None:
            rot = (rot[0], rot[1], self.p(rot[2]))
        self.m.box(self.p(lo), self.p(hi), mat, rot=rot, **kw)

    def tube(self, axis, c, a0, a1, radius, mat, **kw):
        kw.setdefault("sides", 12 if radius >= 7.0 else 8)
        self.m.tube(axis, self.p(c), a0 * self.k, a1 * self.k, radius * self.k, mat, **kw)

    def taper(self, axis, c, a0, a1, r0, r1, mat, **kw):
        self.m.taper(axis, self.p(c), a0 * self.k, a1 * self.k, r0 * self.k, r1 * self.k, mat, **kw)

    def ring(self, axis, centre, radius, thick, width, mat, **kw):
        self.m.ring(axis, self.p(centre), radius * self.k, thick * self.k, width * self.k, mat, **kw)

    def ball(self, centre, radius, mat, **kw):
        self.m.ball(self.p(centre), radius * self.k, mat, **kw)

    def rod(self, a, b, radius, mat, **kw):
        self.m.rod(self.p(a), self.p(b), radius * self.k, mat, **kw)

    def bar(self, a, b, across, deep, mat, **kw):
        """A square-edged bar from a to b whose long side stays the model's upright: `across`
        is its size along x where it stands upright, `deep` along z."""
        kw.setdefault("grain", "y")
        with self.m.aimed(self.p(a), self.p(b), "y") as length:
            self.m.box((-across * self.k / 2.0, 0.0, -deep * self.k / 2.0),
                       (across * self.k / 2.0, length, deep * self.k / 2.0), mat, **kw)

    def beam(self, a, b, width, height, mat, **kw):
        self.m.beam(self.p(a), self.p(b), width * self.k, height * self.k, mat, **kw)

    def turned(self, *turns, about=(0.0, 0.0, 0.0)):
        return self.m.turned(*turns, about=self.p(about))


def _spokes(d, axis, centre, r0, r1, n, mat, wide=1.5, thick=1.0, start=0.0):
    """n flat spokes about `axis` through `centre`, from radius r0 to r1."""
    k = M.AXES.index(axis)
    o1, o2 = [i for i in range(3) if i != k]
    lo, hi = list(centre), list(centre)
    lo[k], hi[k] = centre[k] - thick / 2.0, centre[k] + thick / 2.0
    lo[o1], hi[o1] = centre[o1] + r0, centre[o1] + r1
    lo[o2], hi[o2] = centre[o2] - wide / 2.0, centre[o2] + wide / 2.0
    for i in range(n):
        d.box(lo, hi, mat, rot=(axis, start + 360.0 * i / n, tuple(centre)), grain=M.AXES[o1])


def _circle(d, axis, centre, radius, n=4, band=3.0, thick=1.5, hub=3.0):
    """A setting circle: a graduated brass band on spokes, about `axis` through `centre`."""
    d.ring(axis, centre, radius - band / 2.0, band, thick, BRASS_TICK, sides=16)
    _spokes(d, axis, centre, hub - 0.5, radius - band + 0.5, n, BRASS_D, thick=thick * 0.6, start=45.0)
    k = M.AXES.index(axis)
    c = [v for i, v in enumerate(centre) if i != k]
    d.tube(axis, c, centre[k] - thick * 0.6, centre[k] + thick * 0.6, hub, BRASS_D, sides=8)


# ---- the tube ----------------------------------------------------------------------------------------
BODY_R, HOOP_R = 12.0, 13.0             # texels
HOOPS = tuple(41.5 + 23.0 * i for i in range(9))        # their middles, texels from the eyepiece's end
FINDER_OFF, FINDER_R = 17.5, 3.0
FINDER = (16.0, 80.0)                   # the finder's tube: from, to (texels from the eyepiece's end)
TAIL_PLATE = (19.0, 23.0, 9.0)          # from, to (texels from the eyepiece's end) and radius
HAND_RING = (15.0, 10.0)                # the ring the observer swings the tube by: where, radius
SKIRT = 35.0                            # degrees from the tube's line: under 45, or the game files a skirt under the shoulder's way


def _dec_angle():
    """The declination axis in the tube's own frame, degrees from the model's x towards its y."""
    return math.degrees(math.atan2(_dot(DEC, TUBE_FRAME[1]), _dot(DEC, TUBE_FRAME[0])))


def _tube(version):
    spec = _SPEC[version]
    d = _Px(f"{PREFIX}tube_{version}", TUBE_SCALE)
    back = spec["back"] * 16.0
    phi = _dec_angle()

    def z(s):
        """Model z of a point s texels up the tube from the eyepiece's end face."""
        return back - s

    def seg(s0, s1, radius, mat, sides=12, **kw):
        d.tube("z", (0.0, 0.0), z(s1), z(s0), radius, mat, sides=sides, **kw)

    def side(angle):
        """A frame whose y points out of the tube at `angle` degrees round it (0 north, 90 over)."""
        return d.turned(("z", angle - 90.0))

    # the tail: eyepiece, draw tube, the focusing sleeve with its pinion and two milled heads
    seg(0.25, 3, 2.0, BRASS_D, sides=8)
    seg(0, 0.25, 1.25, GLASS_D, sides=8, cap=GLASS_D)
    seg(3, 9, 2.75, BRASS)
    seg(9, 19, 4.25, BRASS_D)
    seg(9, 10.5, 5.0, BRASS)
    with side(spec["finder"] + 180.0):
        d.box((-1.25, 3.5, z(17.0)), (1.25, 6.0, z(12.0)), BRASS_D)
        d.tube("x", (5.0, z(14.5)), -7.0, 7.0, 0.75, STEEL, sides=4)
        for a, b in ((-7.5, -5.5), (5.5, 7.5)):
            d.tube("x", (5.0, z(14.5)), a, b, 2.25, BRASS, sides=8)
    s0, s1, plate_r = TAIL_PLATE
    seg(s0, s1, plate_r, IRON_D)
    seg(s0 + 1.0, s1 - 1.0, plate_r + 0.75, IRON_D_STUD)
    # the hand ring, on three stays from the tail plate
    ring_s, ring_r = HAND_RING
    d.ring("z", (0.0, 0.0, z(ring_s)), ring_r, 1.25, 1.25, BRASS, sides=16)
    for i in range(3):
        with side(spec["finder"] + 60.0 + 120.0 * i):
            d.rod((0.0, plate_r - 1.5, z(s0)), (0.0, ring_r, z(ring_s)), 0.6, BRASS_D, sides=4)
    def plates(a, b, radius):
        """A ring of the cone's plate from a to b: no line painted at its two ends, the skirt that
        follows it is its edge."""
        half = radius * math.tan(math.pi / 12.0)
        middle = (0.0, 0.0, (z(a) + z(b)) / 2.0)
        for i in range(6):
            d.box((-half, -radius, z(b)), (half, radius, z(a)), TUBE, rot=("z", 30.0 * i, middle) if i else None,
                  skip="we", grain="z", lit={"n": "cap", "s": "cap", "u": "plain", "d": "plain"}, seed=CONE_SEED)

    def skirt(s, r0, r1, mat=TUBE):
        """Where the tube steps out from r0 to r1 at s, going up it: twelve sloping plates over the
        shoulder. A shoulder looks down the tube at the observer and the game gives it four tenths
        of the light, a black gap under every ring; a plate that slopes SKIRT degrees is filed
        under the way its facet of the tube looks and is lit with it, and it is painted one step
        under that facet."""
        run = (r1 - r0) / math.tan(math.radians(SKIRT))
        long = math.hypot(run, r1 - r0)
        half = r1 * math.tan(math.pi / 12.0)
        y, zz = (r0 + r1) / 2.0, z(s) + run / 2.0
        for i in range(12):
            turn = math.radians(30.0 * i)
            light = _dot((-math.sin(turn), math.cos(turn), 0.0), M.LIGHT)
            tone = (1 if light > 0.45 else -1 if light < -0.45 else 0) - 1
            with d.turned(("z", 30.0 * i)):
                d.box((-half, y - 0.25, zz - long / 2.0), (half, y, zz + long / 2.0), mat, rot=("x", SKIRT, (0.0, y, zz)),
                      skip="dnswe", grain="z", faces={"u": mat.variant(tone, 0)}, seed=CONE_SEED + 1)

    # cone and body: rings of plate, each lapped and riveted to the next under a hoop, the seams
    # of neighbouring rings a facet apart; a brass hoop where the cone ends
    rings = [(s1 + (40.0 - s1) * i / 4.0, s1 + (40.0 - s1) * (i + 1) / 4.0,
              plate_r - 0.5 + (BODY_R - plate_r + 0.5) * (i + 0.5) / 4.0) for i in range(4)]
    for i, (a, b, radius) in enumerate(rings):
        plates(a, b, radius)
        if i:
            skirt(a, rings[i - 1][2], radius)
    seg(40, 228, BODY_R, TUBE)
    for i, s in enumerate(HOOPS):
        seg(s - 1.5, s + 1.5, HOOP_R, TUBE_STUD if i else BRASS_STUD, seed=HOOP_SEED)
        if i:
            skirt(s - 1.5, BODY_R, HOOP_R)
        else:
            skirt(s - 1.5, rings[-1][2], HOOP_R, BRASS_D)     # the brass hoop flares down over the cone's last ring
    for i, (a, b) in enumerate(zip(HOOPS, HOOPS[1:] + (228.0,))):
        for across in (0.0, 180.0):
            with side(spec["seam"][i % 2] + across):
                d.box((-1.5, BODY_R - 1.0, z(b)), (1.5, BODY_R + 0.5, z(a)), TUBE_SEAM, grain="z",
                      seed=HOOP_SEED + 3)
    # the objective: an iron flange, the brass cell, the dark glass inside the lip of the dew cap
    seg(227, 230, 13.75, IRON_D_STUD)
    seg(230, 238, 15.0, BRASS)
    seg(232, 234, 15.2, BRASS_STUD, seed=HOOP_SEED + 1)
    d.tube("z", (0.0, 0.0), z(238.75), z(238.0), 13.25, GLASS, sides=12, cap=GLASS)
    d.tube("z", (0.0, 0.0), z(238.9), z(238.75), 6.0, GLASS_D, sides=8, cap=GLASS_D)
    d.ring("z", (0.0, 0.0, z(239.0)), 14.0, 2.0, 2.0, BRASS_D, sides=16)

    # the finder rides where neither the saddle nor the yoke ever comes
    f0, f1 = FINDER
    with side(spec["finder"]):
        c = (0.0, FINDER_OFF)
        d.tube("z", c, z(f1), z(f0), FINDER_R, BRASS_D, sides=8)
        d.tube("z", c, z(f1 + 2.0), z(f1 - 3.0), FINDER_R + 0.75, BRASS, sides=8)
        d.tube("z", c, z(f1 + 2.5), z(f1 + 2.0), FINDER_R - 0.5, GLASS, sides=8, cap=GLASS)
        d.tube("z", c, z(f0 + 1.5), z(f0), FINDER_R + 0.5, BRASS, sides=8)
        d.tube("z", c, z(f0), z(f0 - 5.0), 2.0, BRASS_D, sides=8)
        d.tube("z", c, z(f0 - 5.0), z(f0 - 7.5), 1.25, BRASS, sides=8)
        for s in (f0 + 11.0, f1 - 14.0):
            d.tube("z", c, z(s + 1.5), z(s - 1.5), FINDER_R + 1.25, IRON_D, sides=8)
            d.box((-2.0, BODY_R - 2.0, z(s + 1.5)), (2.0, FINDER_OFF - FINDER_R, z(s - 1.5)), IRON_D)
    # two sliding weights on a rod balance it
    with side(spec["weights"]):
        d.tube("z", (0.0, 16.0), z(64.0), z(27.0), 0.75, STEEL, sides=4)
        for s in (30.0, 61.0):
            d.box((-1.0, BODY_R - 2.0, z(s + 1.0)), (1.0, 16.5, z(s - 1.0)), IRON_D)
        for s in (40.0, 46.5):
            d.tube("z", (0.0, 16.0), z(s + 2.5), z(s - 2.5), 3.0, BRASS_D, sides=8)

    # the clamp and the slow motion: two rods from the declination axis down to a handwheel each,
    # either side of the tail plate
    reach = 104.0 if version == "a" else 78.0
    for swing in spec["rods"]:
        with side(phi + swing):
            d.tube("z", (0.0, 15.5), z(reach), z(18.0), 0.6, BRASS, sides=4)
            d.tube("z", (0.0, 15.5), z(19.5), z(18.0), 3.0, BRASS, sides=8)
            d.tube("z", (0.0, 15.5), z(18.0), z(17.0), 1.25, BRASS_D, sides=8)
            for s in (30.0, 58.0, reach - 2.0):
                d.box((-0.75, BODY_R - 2.5 if s < 40 else BODY_R - 0.5, z(s + 0.75)), (0.75, 16.5, z(s - 0.75)), IRON_D)

    if version == "b":
        # the band the two trunnions are cast on; they run into the yoke's bearings
        seg(back - 7.0, back + 7.0, 13.5, IRON_D)
        for s in (back - 7.5, back + 7.5):
            seg(s - 1.0, s + 1.0, 14.25, IRON_STUD, seed=HOOP_SEED + 2)
        with side(phi):
            for a, b in ((-16.5, -12.5), (12.5, 16.5)):
                d.tube("y", (0.0, 0.0), a, b, 5.5, IRON_D, sides=8)
                for zz in (-4.0, 4.0):
                    lo, hi = sorted((math.copysign(12.0, a), math.copysign(15.0, a)))
                    d.box((-1.0, lo, zz - 0.75), (1.0, hi, zz + 0.75), IRON_STUD)
    else:
        # the saddle on the end of the declination axis and the two straps that hold the tube in it
        with side(phi):
            d.box((-9.0, -16.0, -21.0), (9.0, -11.0, 21.0), IRON_D)
            d.box((-11.0, -14.5, -19.0), (11.0, -9.5, -11.0), IRON_D)
            d.box((-11.0, -14.5, 11.0), (11.0, -9.5, 19.0), IRON_D)
            d.box((-10.0, -16.75, -22.0), (10.0, -15.5, 22.0), IRON_D_STUD)
            for zz in (-15.0, 15.0):
                d.tube("z", (0.0, 0.0), zz - 2.0, zz + 2.0, 13.4, IRON_STUD, seed=HOOP_SEED + 2)
                for sgn in (-1.0, 1.0):
                    a, b = sorted((sgn * 12.5, sgn * 15.5))
                    d.box((a, -9.0, zz - 1.5), (b, -6.0, zz + 1.5), IRON_D)
                    d.tube("y", (sgn * 14.0, zz), -10.5, -4.5, 0.75, BRASS, sides=4)
    return d.m


# ---- what both mounts are made of --------------------------------------------------------------------
def _east(mat, steps):
    """The face of a box that looks east, painted `steps` lighter than the rest of it. A model
    takes no light from a lamp: what a lamp throws on it has to be painted on it."""
    return {"e": mat.variant(steps)} if steps else {}


def _corner_irons(d, x, z, y0, y1, mat=None, about=(0.0, 0.0), east=0):
    """Angle irons riveted up the four corners of a box column of half sizes x and z that stands
    on the point `about` = (x, z)."""
    mat = mat or IRON_STUD
    ox, oz = about
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            a, b = sorted((ox + sx * x, ox + sx * (x + 0.5)))
            c, e = sorted((oz + sz * (z - 2.5), oz + sz * (z + 0.5)))
            d.box((a, y0, c), (b, y1, e), mat, grain="y", seed=STRAP_SEED, faces=_east(mat, east))
            a, b = sorted((ox + sx * (x - 2.5), ox + sx * (x + 0.5)))
            c, e = sorted((oz + sz * z, oz + sz * (z + 0.5)))
            d.box((a, y0, c), (b, y1, e), mat, grain="y", seed=STRAP_SEED, faces=_east(mat, east))


def _section(d, y0, y1, hx, hz, about=(0.0, 0.0), flange=1.5, mat=None, east=0):
    """One cast section of a box column: the shaft with its corner irons, a bolted flange on top.
    east: steps of light painted on what looks east."""
    ox, oz = about
    mat = mat or IRON
    d.box((ox - hx, y0, oz - hz), (ox + hx, y1, oz + hz), mat, grain="y", faces=_east(mat, east))
    _corner_irons(d, hx, hz, y0, y1, about=about, east=east)
    if flange:
        d.box((ox - hx - flange, y1, oz - hz - flange), (ox + hx + flange, y1 + 2.0, oz + hz + flange), IRON_D_STUD,
              faces=_east(IRON_D_STUD, east))


def _clock(d, at):
    """The driving clock on an east face: a brass case on a bracket, a dial behind glass, the
    winding square. `at` is the middle of the foot of its back. Returns two points on its top,
    the northern and the southern: the governor stands on one, the shaft to the worm leaves the
    case at the other."""
    x, y, z = at
    d.box((x, y - 2.0, z - 4.0), (x + 5.0, y, z + 4.0), IRON_D)
    d.box((x, y, z - 5.0), (x + 6.0, y + 13.0, z + 5.0), BRASS)
    d.box((x, y + 12.0, z - 5.5), (x + 6.5, y + 13.5, z + 5.5), BRASS_D)
    d.box((x, y, z - 5.5), (x + 6.5, y + 1.0, z + 5.5), BRASS_D)
    d.box((x + 6.0, y + 2.0, z - 3.5), (x + 6.5, y + 11.0, z + 3.5), GLASS_D)
    d.tube("x", (y + 7.5, z), x + 6.5, x + 6.9, 2.5, DIAL, sides=8, cap=DIAL)
    d.box((x + 6.9, y + 7.0, z - 0.5), (x + 7.2, y + 9.5, z + 0.5), HOOD)
    d.tube("x", (y + 3.5, z), x + 6.5, x + 7.5, 0.75, BRASS_D, sides=4)
    return (x + 3.0, y + 13.5, z - 2.5), (x + 3.0, y + 13.5, z + 2.5)


def _bearing(d, at, half=4.0, wide=7.5, low=-10.0):
    """A plummer block cast to the latitude about the point `at` of the polar axis."""
    x, y, z = at
    with d.turned(("x", -LEAN), about=at):
        d.box((x - wide, y - half, z + low), (x + wide, y + half, z + 4.0), IRON_D)
        d.box((x - wide, y - half + 1.0, z + 4.0), (x + wide, y + half - 1.0, z + 6.0), IRON)
        for sgn in (-1.0, 1.0):
            d.tube("z", (x + sgn * (wide - 2.0), y), z + 5.5, z + 7.5, 1.0, STEEL, sides=4)
        d.tube("y", (x, z), y - half - 0.75, y + half + 0.75, 4.75, BRASS_D, sides=8)


def _shaft(d, a, b):
    """The clock's shaft: a thin brass rod with a coupling at either end."""
    d.rod(a, b, 0.6, BRASS, sides=4)
    for p, q in ((a, b), (b, a)):
        n = math.dist(p, q)
        if n > 3.0:
            e = tuple(p[i] + (q[i] - p[i]) * 1.5 / n for i in range(3))
            d.rod(p, e, 1.25, BRASS_D, sides=8)


# ---- a: the German mount ---------------------------------------------------------------------------
A_SLEEVE = (-38.0, -10.5, 10.0)         # the polar sleeve: from, to (texels along the axis from the crossing), radius
A_CHEEK = -14.5                         # where the head's cheeks end: the declination circle passes over them
A_COLUMN = [                            # the pier's sections: y0, y1, half size along x and along z (texels)
    (6.0, 22.0, 24.0, 27.0),
    (24.0, 36.0, 24.0, 24.0),           # no narrower than A_SOLID's cells below y 32: they stand inside it
    (38.0, 44.0, 18.0, 17.5),
]
A_SOLID = (1, 2)                        # the barrier in the column: cells either side of the axis' own, and how many high
A_LAMPLIGHT = (2, 1, 0)                 # steps of light painted on what looks east, section by section (the foot as the lowest):
#                                         the room's lamp hangs at the east edge of the pier's well, under the cap (sky/lights)
A_WEIGHTS = (25.0, 38.0, 9.0)           # the counterweights: from, to (texels from the crossing), radius
A_CLOCK = (24.0, 26.0, 16.25)           # the driving clock on the pier's east face, its shaft under the mitre box


def _pier_a():
    d = _Px(PREFIX + "pier_a", MOUNT_SCALE)
    # the foot: a bed plate bolted to the cap, stepped up to the column
    low = A_LAMPLIGHT[0]
    d.box((-36.0, 0.0, -38.5), (36.0, 2.0, 38.5), IRON_D, faces=_east(IRON_D, low))
    d.box((-32.0, 2.0, -35.0), (32.0, 4.0, 35.0), IRON, faces=_east(IRON, low))
    d.box((-28.0, 4.0, -31.0), (28.0, 6.0, 31.0), IRON_D, faces=_east(IRON_D, low))
    for x in (-34.0, -12.0, 12.0, 34.0):
        for zz in (-36.75, -13.0, 13.0, 36.75):
            if abs(x) > 32.0 or abs(zz) > 35.0:
                d.box((x - 1.0, 2.0, zz - 1.0), (x + 1.0, 3.5, zz + 1.0), STEEL)
    # the column: three cast sections bolted flange to flange, angle irons up the corners
    for i, (y0, y1, hx, hz) in enumerate(A_COLUMN):
        _section(d, y0, y1, hx, hz, flange=1.5, east=A_LAMPLIGHT[i])
    y_top = A_COLUMN[-1][1] + 2.0
    hx, hz = A_COLUMN[0][2], A_COLUMN[0][3]
    # the door to the clock's weight in the lowest section, and a plate where a maker would sign
    d.box((hx, 8.0, -8.0), (hx + 0.75, 19.5, 2.0), IRON_D, faces=_east(IRON_D, low))
    d.box((hx + 0.75, 8.5, -7.5), (hx + 1.0, 19.0, -6.5), IRON_STUD, faces=_east(IRON_STUD, low))
    d.box((hx + 0.75, 13.0, 0.0), (hx + 1.75, 14.5, 1.0), BRASS)
    d.box((-5.0, 11.0, hz), (5.0, 16.0, hz + 0.5), BRASS_D)
    d.box((-4.0, 12.0, hz + 0.5), (4.0, 15.0, hz + 0.75), BRASS_STUD)

    # the head: two cheeks and a web, cast to the angle of the latitude, cradle the polar sleeve
    cy = _SPEC["a"]["rise"] * 16.0
    s0, s1, r = A_SLEEVE
    d.box((-13.5, y_top, -13.0), (13.5, y_top + 5.0, -5.0), IRON_D)
    with d.turned(("x", -LEAN), about=(0.0, cy, 0.0)):
        for sgn in (-1.0, 1.0):
            a, b = sorted((sgn * r, sgn * (r + 3.5)))
            d.box((a, cy + s0 + 2.0, -30.0), (b, cy + A_CHEEK, 2.5), IRON_D)
            a, b = sorted((sgn * (r + 3.5), sgn * (r + 4.25)))
            d.box((a, cy + s0 + 3.0, -1.0), (b, cy + A_CHEEK - 1.0, 2.0), IRON_STUD, grain="y", seed=STRAP_SEED + 1)
            d.box((a, cy + s0 + 3.0, -29.0), (b, cy + s0 + 6.0, -2.0), IRON_STUD, grain="z", seed=STRAP_SEED + 2)
        d.box((-r, cy + s0 + 4.0, -28.0), (r, cy + A_CHEEK, -5.0), IRON)
        d.tube("y", (0.0, 0.0), cy + s0, cy + s1, r, IRON)
        for s in (s0 + 1.5, s1 - 1.5):
            d.tube("y", (0.0, 0.0), cy + s - 1.5, cy + s + 1.5, r + 1.25, IRON_STUD, seed=HOOP_SEED)
        # the hour circle and the worm wheel on the lower end of the polar axis
        d.tube("y", (0.0, 0.0), cy + s0 - 6.0, cy + s0, 3.0, STEEL, sides=8)
        d.tube("y", (0.0, 0.0), cy + s0 - 2.0, cy + s0 - 0.5, 12.0, IRON_TOOTH, sides=12)
        _circle(d, "y", (0.0, cy + s0 - 3.5, 0.0), 14.0, n=6)
        d.tube("y", (0.0, 0.0), cy + s0 - 7.0, cy + s0 - 6.0, 4.0, BRASS, sides=8)
    # the drive: the clock on the east face, a shaft up to the mitre box on the corner of the head,
    # a shaft along the edge to the worm under the wheel
    governor, leaves = _clock(d, A_CLOCK)
    worm_y, worm_z = y_top + 1.25, A_COLUMN[-1][3] + 1.25
    d.box((-5.0, y_top - 2.0, worm_z - 2.25), (5.0, y_top + 2.0, worm_z + 1.75), BRASS_D)
    d.box((-3.0, y_top + 2.0, worm_z - 1.25), (3.0, y_top + 2.75, worm_z + 0.75), BRASS)
    box = (leaves[0], worm_y, worm_z)
    d.box((box[0] - 2.25, worm_y - 2.5, worm_z - 2.5), (box[0] + 2.25, worm_y + 2.0, worm_z + 2.5), BRASS_D)
    d.box((A_COLUMN[-1][2] + 1.5, worm_y - 3.25, worm_z - 2.0), (box[0] - 2.25, worm_y - 1.5, worm_z + 2.0), IRON_D)
    _shaft(d, (5.0, worm_y, worm_z), (box[0] - 2.25, worm_y, worm_z))
    _shaft(d, leaves, (box[0], worm_y - 2.5, leaves[2]))
    d.governor = governor
    return d


def _axis_a():
    d = _Px(PREFIX + "axis_a", MOUNT_SCALE)
    # the head of the polar axis and the declination housing cast across it
    d.tube("y", (0.0, 0.0), -9.5, 9.5, 10.5, IRON)
    d.tube("y", (0.0, 0.0), -10.25, -9.5, 5.0, STEEL, sides=8)
    d.tube("y", (0.0, 0.0), 9.5, 11.0, 8.0, IRON_D)
    d.tube("y", (0.0, 0.0), 11.0, 12.5, 2.5, BRASS_D, sides=8)
    d.tube("z", (0.0, 0.0), -7.9, -5.5, 10.0, IRON_D_STUD)
    d.tube("z", (0.0, 0.0), -5.5, 15.0, 8.5, IRON)
    d.tube("z", (0.0, 0.0), 13.0, 15.0, 10.0, IRON_STUD, seed=HOOP_SEED)
    # the declination circle, read from the floor on the counterweight's side
    d.tube("z", (0.0, 0.0), 15.0, 16.0, 10.0, IRON_TOOTH, sides=12)
    _circle(d, "z", (0.0, 0.0, 17.5), 13.0, n=6)
    d.box((-1.0, 11.0, 15.5), (1.0, 15.5, 19.0), BRASS_D)                            # the reader's index
    d.tube("x", (9.0, 14.0), -1.5, 1.5, 1.25, BRASS, sides=8)                        # and its lens
    # the clamp: a lever with a wooden grip on the housing's upper side
    d.box((-1.0, 7.5, 3.0), (1.0, 10.5, 5.0), IRON_D)
    d.rod((0.0, 10.0, 4.0), (0.0, 15.0, 9.0), 0.6, STEEL, sides=4)
    d.rod((0.0, 14.0, 8.0), (0.0, 16.5, 10.5), 1.1, WOOD, sides=8)
    # the counterweight: two iron cheeses on a steel shaft, a copper washer between, a brass nut
    w0, w1, wr = A_WEIGHTS
    mid = (w0 + w1) / 2.0
    d.tube("z", (0.0, 0.0), 15.0, w1 + 2.5, 2.25, STEEL, sides=8)
    d.tube("z", (0.0, 0.0), w0 - 2.5, w0, 4.0, BRASS_D, sides=8)
    d.tube("z", (0.0, 0.0), w0, mid - 0.5, wr, IRON_D)
    d.tube("z", (0.0, 0.0), mid - 0.5, mid + 0.5, wr - 1.5, COPPER)
    d.tube("z", (0.0, 0.0), mid + 0.5, w1, wr, IRON_D)
    for s in (w0 + 1.5, w1 - 1.5):
        d.tube("z", (0.0, 0.0), s - 0.5, s + 0.5, wr + 0.5, IRON)
    d.tube("z", (0.0, 0.0), w1, w1 + 2.0, 3.5, BRASS, sides=8)
    return d.m


# ---- b: the English yoke -------------------------------------------------------------------------------
B_SOUTH, B_NORTH = -44.5, 42.0          # the two bearings, texels along the polar axis from the crossing
B_GIRDER = (16.0, 21.0, 15.2, 6.0)      # the frame's long sides: inner and outer face (from the axis), half length, half depth
B_HUB = dict(south=(-36.0, -32.0), north=(31.0, 35.0))     # the end bosses, along the axis
B_HUB_R = 9.0
B_WHEEL = -39.0                         # the worm wheel, along the axis; the hour circle lies over it
B_TRESTLE_Z = -35.5                     # the plane of the north trestle, texels south of the cap's middle
B_LEG = ((34.0, 5.0), (6.0, 112.0))     # a leg of the trestle: its foot and its head, (x, y)
B_PEDESTAL = [                          # the south pedestal's sections: y0, y1, half size along x, z from, z to
    (3.0, 22.0, 15.0, 18.5, 38.5),
    (24.0, 48.0, 12.0, 21.0, 37.5),
]
B_CLOCK = (12.0, 26.0, 29.0)            # the driving clock on the pedestal's east face


def _yoke_b():
    d = _Px(PREFIX + "yoke_b", YOKE_SCALE)
    inner, outer, half, deep = B_GIRDER
    mid = (inner + outer) / 2.0
    ends = {"south": -B_HUB["south"][1], "north": -B_HUB["north"][0]}      # model z of each boss's inner face
    for sgn in (-1.0, 1.0):
        a, b = sorted((sgn * inner, sgn * outer))
        d.box((-deep, a, -half), (deep, b, half), IRON_SEAM, grain="z")
        # riveted flanges along both edges of the outer face, stiffeners between
        o0, o1 = sorted((sgn * outer, sgn * (outer + 0.5)))
        for x in (-deep, deep - 2.0):
            d.box((x, o0, -half), (x + 2.0, o1, half), IRON_SEAM, grain="z", seed=STRAP_SEED)
        for zz in (-10.5, 10.5):
            d.box((-deep + 2.0, o0, zz - 1.0), (deep - 2.0, o1, zz + 1.0), IRON_D)
        # the bearing of the tube's trunnion
        t0, t1 = sorted((sgn * outer, sgn * (outer + 3.0)))
        d.tube("y", (0.0, 0.0), t0, t1, 7.0, IRON_D, sides=8)
        t0, t1 = sorted((sgn * (outer + 3.0), sgn * (outer + 4.5)))
        d.tube("y", (0.0, 0.0), t0, t1, 3.0, BRASS_D, sides=8)
        # the arms that run in to the pivots
        for zz in ends.values():
            near = math.copysign(half - 1.0, zz)
            d.beam((0.0, sgn * mid, near), (0.0, sgn * 5.0, zz), 2.0 * deep, outer - inner, IRON_SEAM,
                   seed=STRAP_SEED + 1)
    # the end bosses are round: the trestle's legs stand close by the northern one
    for s0, s1 in B_HUB.values():
        z0, z1 = sorted((-s0, -s1))
        d.tube("z", (0.0, 0.0), z0, z1, B_HUB_R, IRON_D)
        d.tube("z", (0.0, 0.0), z0 + 1.0, z1 - 1.0, B_HUB_R + 0.5, IRON_D_STUD, seed=HOOP_SEED)
    # the journals: the south one carries the hour circle and, next the bearing, the worm wheel
    south, north, wheel = -B_HUB["south"][0], -B_HUB["north"][1], -B_WHEEL
    d.tube("z", (0.0, 0.0), south, -B_SOUTH + 4.5, 3.5, STEEL, sides=8)
    _circle(d, "z", (0.0, 0.0, south + 1.25), 14.5, n=6)
    d.tube("z", (0.0, 0.0), south + 2.0, wheel - 0.5, 5.0, IRON_D, sides=8)
    d.tube("z", (0.0, 0.0), wheel - 0.5, wheel + 0.5, 12.0, IRON_TOOTH, sides=12)
    d.tube("z", (0.0, 0.0), -B_NORTH - 4.5, north, 3.5, STEEL, sides=8)
    d.tube("z", (0.0, 0.0), north - 1.0, north, 6.0, IRON_D, sides=8)
    # the declination circle on the upper side of the frame, where the floor sees it
    _circle(d, "y", (0.0, outer + 3.75, 0.0), 13.0, n=6)
    d.box((-1.0, outer + 0.5, 11.0), (1.0, outer + 5.0, 15.5), BRASS_D)
    return d.m


def _piers_b():
    d = _Px(PREFIX + "piers_b", YOKE_SCALE)
    cy = _SPEC["b"]["rise"] * 16.0
    sq = math.sqrt(0.5)
    south = (0.0, cy + B_SOUTH * sq, -B_SOUTH * sq)
    north = (0.0, cy + B_NORTH * sq, -B_NORTH * sq)
    tz = B_TRESTLE_Z
    foot, head = B_LEG

    def leg_x(y):
        return foot[0] + (head[0] - foot[0]) * (y - foot[1]) / (head[1] - foot[1])

    # the bed: a frame of two riveted girders bolted to the cap, a sleeper and the pedestal's
    # plate across them
    for x in (-36.0, 31.0):
        d.box((x, 0.0, -40.0), (x + 5.0, 3.0, 40.0), IRON_D, grain="z")
        d.box((x - 0.5, 3.0, -40.0), (x + 5.5, 3.75, 40.0), IRON_SEAM, grain="z", seed=STRAP_SEED)
    d.box((-31.0, 0.0, -13.5), (31.0, 3.0, -7.5), IRON_D, grain="x")
    d.box((-31.0, 0.0, 17.0), (31.0, 3.0, 40.0), IRON_D)
    for x in (-27.0, 27.0):
        for zz in (20.0, 37.0):
            d.box((x - 1.0, 3.0, zz - 1.0), (x + 1.0, 4.5, zz + 1.0), STEEL)
    # the south pedestal: two cast sections and a cap plate, the thrust bearing on its head
    for y0, y1, hx, z0, z1 in B_PEDESTAL:
        _section(d, y0, y1, hx, (z1 - z0) / 2.0, about=(0.0, (z0 + z1) / 2.0), flange=1.5 if y1 < 40.0 else 0.0)
    y1, hx, z0, z1 = B_PEDESTAL[-1][1:]
    d.box((-hx - 1.5, y1, z0), (hx + 1.5, y1 + 2.0, z1 + 1.5), IRON_D_STUD)
    d.box((-4.0, 30.0, z1), (4.0, 35.0, z1 + 0.5), BRASS_D)
    d.box((-3.0, 31.0, z1 + 0.5), (3.0, 34.0, z1 + 0.75), BRASS_STUD)
    _bearing(d, south)
    with d.turned(("x", -LEAN), about=south):
        d.box((-6.0, south[1] - 6.5, south[2] - 5.0), (6.0, south[1] - 4.0, south[2] + 5.0), IRON)
    # the north trestle: two legs on the cap's north edge, their heads cast into one block, tied
    # twice and open between the ties (the tube is seen through it), each braced back to the sleeper
    for sgn in (-1.0, 1.0):
        a, b = sorted((sgn * (foot[0] - 6.0), sgn * (foot[0] + 6.0)))
        d.box((a, 3.0, tz - 4.5), (b, foot[1] + 1.0, tz + 4.5), IRON_D_STUD)
        d.bar((sgn * foot[0], foot[1], tz), (sgn * head[0], head[1], tz), 8.0, 7.0, IRON_SEAM, seed=STRAP_SEED + 3)
        x = leg_x(56.0)
        d.bar((sgn * x, 56.0, tz + 2.0), (sgn * x, 3.0, tz + 25.0), 4.5, 5.5, IRON_D)
        d.box((sgn * x - 4.0, 3.0, tz + 22.0), (sgn * x + 4.0, 4.5, tz + 28.0), IRON_D_STUD)
    for y in (32.0, 82.0):
        x = leg_x(y) + 1.0
        d.box((-x, y - 2.5, tz - 3.0), (x, y + 2.5, tz + 3.0), IRON_SEAM, grain="x", seed=STRAP_SEED + 4)
        for sgn in (-1.0, 1.0):
            a, b = sorted((sgn * (x - 6.0), sgn * (x + 3.0)))
            d.box((a, y - 4.0, tz - 4.0), (b, y + 4.0, tz + 4.0), IRON_D_STUD)
    d.box((-11.0, 106.0, tz - 3.5), (11.0, 122.0, tz + 3.5), IRON_D)
    d.box((-12.0, 108.0, tz - 4.25), (12.0, 110.0, tz + 4.25), IRON_D_STUD)
    d.box((-7.0, 122.0, tz - 3.0), (7.0, 124.0, tz + 3.0), IRON)
    _bearing(d, north, low=-7.0, wide=7.0)
    # the drive: the worm's box on the cheek of the south bearing, at the rim of the wheel; the
    # clock on the pedestal's east face under it, a shaft straight up
    leaves, governor = _clock(d, B_CLOCK)
    with d.turned(("x", -LEAN), about=(0.0, cy, 0.0)):
        d.box((12.25, cy + B_WHEEL - 1.0, -3.5), (16.0, cy + B_WHEEL + 0.5, 3.5), BRASS_D)
        d.box((7.5, cy + B_WHEEL - 2.5, -2.0), (12.25, cy + B_WHEEL - 1.0, 2.0), IRON_D)
    worm = (14.0, cy + (B_WHEEL - 0.25) * sq - 3.5 * sq, -(B_WHEEL - 0.25) * sq - 3.5 * sq)
    _shaft(d, leaves, worm)
    d.governor = governor
    return d


# ---- the small pieces --------------------------------------------------------------------------------
def _governor():
    """The clock's flyball governor. Anchor: the foot of its spindle; it spins about y."""
    d = _Px(PREFIX + "governor", 1.0)
    d.tube("y", (0.0, 0.0), 0.0, 1.0, 1.5, BRASS_D, sides=8)
    d.tube("y", (0.0, 0.0), 1.0, 8.0, 0.5, STEEL, sides=4)
    d.tube("y", (0.0, 0.0), 3.0, 4.0, 1.0, COPPER, sides=8)
    d.tube("y", (0.0, 0.0), 7.5, 8.5, 1.0, BRASS_D, sides=8)
    for side in (-1.0, 1.0):
        d.rod((0.0, 7.75, 0.0), (side * 3.0, 4.5, 0.0), 0.3, BRASS_D, sides=4)
        d.rod((0.0, 3.5, 0.0), (side * 3.0, 4.5, 0.0), 0.3, BRASS_D, sides=4)
        d.ball((side * 3.25, 4.25, 0.0), 1.25, BRASS, sides=8, layers=4)
    return d.m


LAMP_OFF = (-0.25, 0.32, 0.62)          # the lamp's glass from the eyepiece: blocks east, up, to the side shown
# The peep-hole in the hood's back (A0: a point in V8, not a patch) is a ruby set in the hood's
# east facet, cut with one facet that leans out and down. The game lights a piece of a model by
# the way it is filed as looking: up in full, north or south by three quarters, east or west by
# half, and a face that glows is lit no other way. A ruby upright in the hood's back would be a
# dull point; the facet is filed as looking up (it is nearer that than any other way) and is the
# full signal red, here and in the game.
PEEP = (0.2, 0.32)                      # the facet: texels across, and down its slope
PEEP_AT = (2.0, -0.5, 0.0)              # the middle of its upper edge, texels from the lamp's: on the hood's east facet
PEEP_LEAN = (45.0, 30.0)                # degrees it looks down from straight up, and round from the east to the side
#                                         shown: at the camera of V8
POINT = 3.0                             # screen pixels a point stays under, across and down, on a picture 720 high
GAME_FOV = 70.0                         # degrees, top to bottom: a visitor's on foot. The pictures are taken a
#                                         tenth wider (a flying camera's), the point is smaller in them


def _lamp_at(version):
    """Where the red lamp hangs, and where its arm is clamped on the rim of the tail plate."""
    e = eyepiece(version)
    side = _SPEC[_version(version)]["show"]
    s0, s1, r = TAIL_PLATE
    rim = _add(_add(e, _mul(SIGHT, (s0 + s1) / 32.0)), (0.0, 0.0, side * r / 16.0))
    return _add(e, (LAMP_OFF[0], LAMP_OFF[1], side * LAMP_OFF[2])), rim


def _lamp(version):
    """The red lamp: a blackened hood on an arm from the tail plate, the ruby glass sunk in its
    west face under a shade. Anchor: the middle of the lamp's body; the model is level. The
    drawer comes back with .peep, the number of the box whose top is the ruby's facet."""
    d = _Px(f"{PREFIX}lamp_{version}", 1.0)
    at, rim = _lamp_at(version)
    shown = _SPEC[version]["show"]
    arm = tuple((rim[i] - at[i]) * 16.0 for i in range(3))
    d.tube("y", (0.0, 0.0), -3.0, 2.0, 2.0, HOOD, sides=8)
    d.tube("y", (0.0, 0.0), 2.0, 3.0, 2.5, IRON_D, sides=8)
    d.tube("y", (0.0, 0.0), 3.0, 4.0, 1.25, HOOD, sides=8)
    d.tube("y", (0.0, 0.0), -3.5, -3.0, 2.25, IRON_D, sides=8)
    # the shade round the glass: a roof, two cheeks and a sill, let into the hood as far as its
    # north and south facets, so that the glass is seen from the west and from nowhere else
    back = -2.0 * math.tan(math.pi / 8.0)
    d.box((-4.0, 1.25, -2.0), (back, 1.75, 2.0), HOOD)
    for side in (-1.0, 1.0):
        a, b = sorted((side * 1.5, side * 2.0))
        d.box((-4.0, -2.25, a), (back, 1.25, b), HOOD)
    d.box((-2.75, -2.25, -1.5), (back, -1.75, 1.5), HOOD)
    d.box((-2.25, -1.75, -1.25), (-1.9, 0.75, 1.25), RED_LENS, emit=15, shade=False)
    d.box((-2.3, -1.0, -0.5), (-2.25, 0.0, 0.5), RED_HOT, emit=15, shade=False)
    # the peep-hole in the back: the floor sees that the lamp burns. Only the facet is drawn
    x, y, z = PEEP_AT
    across, down = PEEP
    lean, turn = PEEP_LEAN
    with d.turned(("z", -lean), ("y", -shown * turn), about=PEEP_AT):
        d.box((x, y - 0.05, z - across / 2.0), (x + down, y, z + across / 2.0), RED_LENS,
              skip="dnsew", emit=15, shade=False)
    d.peep = len(d.m.parts) - 1
    # the arm: up from the hood's cap and over to its clamp on the tail plate
    knee = (0.0, 6.0, 0.0)
    d.rod((0.0, 4.0, 0.0), knee, 0.5, BRASS_D, sides=4)
    d.rod(knee, arm, 0.5, BRASS_D, sides=4)
    d.ball(knee, 0.9, BRASS, sides=8, layers=3)
    return d


@functools.lru_cache(maxsize=None)
def _built():
    pier_a, piers_b = _pier_a(), _piers_b()
    lamps = {v: _lamp(v) for v in VERSIONS}
    # settle: the flats of the eight-sided pieces stand between two axes too; each piece is turned off the fence
    out = {m.name: K.settle(m) for m in (
        _tube("a"), _tube("b"), pier_a.m, _axis_a(), piers_b.m, _yoke_b(), _governor(), lamps["a"].m, lamps["b"].m)}
    stands = {"a": tuple(v / 16.0 for v in pier_a.governor), "b": tuple(v / 16.0 for v in piers_b.governor)}
    return out, stands, {v: lamps[v].peep for v in VERSIONS}


def models(version=None):
    """The models of one version: what build() places."""
    built = _built()[0]
    return {name: built[name] for name, _at, _frame, _scale in placed(version)}


# ---- placing ---------------------------------------------------------------------------------------------
def _pose(frame):
    """Yaw and turns for artkit.models.display that carry a model's x, y and z to the three
    directions of `frame`: the model is turned about z, then about x, then about the upright."""
    x, y, z = frame
    tilt = -math.asin(max(-1.0, min(1.0, z[1])))
    swing = math.atan2(z[0], z[2])
    roll = math.atan2(x[1], y[1])
    return -math.degrees(swing), (("z", math.degrees(roll)), ("x", math.degrees(tilt)))


def _put(canvas, model, at, frame, scale, origin, stand=None):
    """Place a model with its anchor at `at`. stand: the spot the entity itself stands on, for a
    piece that turns about an axis its anchor is not on: the entity is put on the axis and holds
    its model out from there, so that a turn of the entity is a turn about the axis."""
    yaw, turns = _pose(frame)
    nbt = M.display(model, yaw=yaw, turns=turns, scale=scale, brightness=BRIGHTNESS)
    if stand is not None:
        out = _sub(at, stand)
        a = math.radians(float(nbt["Rotation"][0]))
        c, s = math.cos(a), math.sin(a)
        held = (out[0] * c + out[2] * s, out[1], -out[0] * s + out[2] * c)      # in the entity's own frame
        tr = nbt["transformation"]
        tr["translation"] = [M.Float(float(v) + h) for v, h in zip(tr["translation"], held)]
        at = stand
    x, y, z = _add(at, origin)
    canvas.add_entity(x, y, z, nbt)
    return 1


def turning(version=None):
    """The models that turn with the polar axis: the axis piece or the yoke, the tube, and the
    lamp that is clamped on the tube's tail."""
    version = _version(version)
    return tuple(PREFIX + name for name in ("axis_a" if version == "a" else "yoke_b", f"tube_{version}", f"lamp_{version}"))


def placed(version=None):
    """What build() places: [(model name, anchor in scene coordinates, frame, scale)]."""
    version = _version(version)
    foot = (AXIS[0], CAP_Y, AXIS[1])
    stand = _add(foot, _built()[1][version])
    lamp = _lamp_at(version)[0]
    if version == "a":
        mount = [("pier_a", foot, WORLD, MOUNT_SCALE), ("axis_a", crossing("a"), AXIS_FRAME, MOUNT_SCALE)]
    else:
        mount = [("piers_b", foot, WORLD, YOKE_SCALE), ("yoke_b", crossing("b"), YOKE_FRAME, YOKE_SCALE)]
    return [(PREFIX + name, at, frame, scale) for name, at, frame, scale in mount + [
        (f"tube_{version}", pivot(version), TUBE_FRAME, TUBE_SCALE),
        ("governor", stand, WORLD, 1.0),
        (f"lamp_{version}", lamp, WORLD, 1.0),
    ]]


def solid(version=None, origin=(0, 0, 0)):
    """The cells nobody can walk into: [(x, y, z)], scene coordinates. They lie inside the two
    lower sections of the pier of a, which are solid iron to the eye, so what stops a visitor is
    what he sees (INTERFACE, the fifth supplement: a barrier stands inside a solid model, nowhere
    out of its outline, two cells high at the most). The piers of b are not built in the map and
    have none."""
    if _version(version) != "a":
        return []
    reach, high = A_SOLID
    x, y, z = (int(math.floor(v + o)) for v, o in zip((AXIS[0], CAP_Y, AXIS[1]), origin))
    return [(x + i, y + j, z + k) for i in range(-reach, reach + 1) for j in range(high)
            for k in range(-reach, reach + 1)]


def build(canvas, origin=(0, 0, 0), version=None, lamp=True):
    """Stand the refractor on the pier's cap. Returns the number of display entities placed.

    lamp=False leaves the red lamp's light source out (the lamp itself stays): a test scene that
    wants the room without it.

    What moves is registered with the motion line as it is placed (the module's head): the pieces
    the polar axis carries swing about it together, the governor spins. The lamp's light source
    stays where the lamp hangs in the middle of the swing.
    """
    version = _version(version)
    built = _built()[0]
    swung = turning(version) if MK is not None else ()
    n = 0
    for name, at, frame, scale in placed(version):
        if name in swung:
            n += _put(canvas, built[name], at, frame, scale, origin, stand=crossing(version))
            MK.swing(canvas, DIURNAL, FOLLOW, FOLLOW_PERIOD)
            continue
        n += _put(canvas, built[name], at, frame, scale, origin)
        if MK is not None and name == PREFIX + "governor":
            MK.spin(canvas, "y", MK.SCOPE_GOVERNOR_REV)
    for x, y, z in solid(version, origin):
        canvas.set(x, y, z, B.BARRIER)
    if lamp:
        try:
            from ..sky import _lightkit as L
        except ImportError:
            L = None
        if L is not None:
            cell = _add(_lamp_at(version)[0], origin)
            L.suggest(canvas, cell, LAMP_LEVEL, "machines/scope:lamp", rank=3)
    return n


# ---- the rules the numbers are held to -------------------------------------------------------------------
def _spot(model, part, where, at, frame, scale):
    """A point of one box of a placed model, in scene coordinates. `where` runs from -1 to 1
    across the box along each of its own axes."""
    k = scale / 16.0
    c = [(part["lo"][i] + part["hi"][i]) / 2.0 for i in range(3)]
    h = [(part["hi"][i] - part["lo"][i]) / 2.0 for i in range(3)]
    v = M._qrot(part["rot"][0] if part["rot"] else M.IDENT, tuple(where[i] * h[i] for i in range(3)))
    p = at
    for i in range(3):
        p = _add(p, _mul(frame[i], (c[i] + v[i] - model.anchor[i]) * k))
    return p


def _corners(model, at, frame, scale):
    """The corners of every box of a placed model, in scene coordinates."""
    for part in model.parts:
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    yield _spot(model, part, (sx, sy, sz), at, frame, scale)


def _box(part):
    """A box of a model, in the model's units: (its middle, its half sizes, its own three axes)."""
    c = np.array([(part["lo"][i] + part["hi"][i]) / 2.0 for i in range(3)])
    h = np.array([(part["hi"][i] - part["lo"][i]) / 2.0 for i in range(3)])
    q = part["rot"][0] if part["rot"] else M.IDENT
    return c, h, np.array([M._qrot(q, e) for e in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))])


def _within(model, at, frame, scale, points, slack=1e-6):
    """Which of `points` (scene coordinates) lie in a box of a placed model."""
    q = (np.asarray(points, dtype=float) - np.array(at)) @ np.array(frame).T * (16.0 / scale) + np.array(model.anchor)
    inside = np.zeros(len(q), dtype=bool)
    for part in model.parts:
        c, h, own = _box(part)
        inside |= (np.abs((q - c) @ own.T) <= h + slack).all(axis=1)
    return inside


def _first(version, eye, target):
    """What a look from `eye` at `target` meets first of the version's pieces: (model name,
    number of the box, how far along the way to the target: 1 is the target itself)."""
    built = _built()[0]
    best = (None, None, math.inf)
    for name, at, frame, scale in placed(version):
        model = built[name]
        k, f = scale / 16.0, np.array(frame, dtype=float)
        anchor = np.array(model.anchor, dtype=float)
        a = ((np.array(eye, dtype=float) - np.array(at)) @ f.T) / k + anchor
        b = ((np.array(target, dtype=float) - np.array(at)) @ f.T) / k + anchor
        for n, part in enumerate(model.parts):
            c, h, turn = _box(part)
            o, way = (a - c) @ turn.T, (b - a) @ turn.T
            t0, t1 = 0.0, best[2]
            for i in range(3):
                if abs(way[i]) < 1e-12:
                    if abs(o[i]) > h[i]:
                        t1 = -1.0
                    continue
                near, far = sorted(((-h[i] - o[i]) / way[i], (h[i] - o[i]) / way[i]))
                t0, t1 = max(t0, near), min(t1, far)
            if t0 < t1:
                best = (name, n, t0)
    return best


def _facet(version):
    """The facet of the lamp's ruby as it is placed: (its four corners, its middle, the way it
    looks), in scene coordinates."""
    version = _version(version)
    models_, _stands, peeps = _built()
    model = models_[f"{PREFIX}lamp_{version}"]
    part, at = model.parts[peeps[version]], _lamp_at(version)[0]
    corners = [_spot(model, part, (sx, 1, sz), at, WORLD, 1.0) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    middle = _spot(model, part, (0, 1, 0), at, WORLD, 1.0)
    return corners, middle, _unit(_cross(_sub(corners[3], corners[0]), _sub(corners[1], corners[0])))


def peep(version=None):
    """(across, down): the screen pixels the ruby's facet takes up from the camera of V8, on a
    picture 720 high at a visitor's field of view."""
    eye, look = v8(version)
    ahead = _unit(_sub(look, eye))
    right = _unit(_cross(ahead, UP))
    over = _cross(right, ahead)
    focal = 360.0 / math.tan(math.radians(GAME_FOV) / 2.0)
    seen = []
    for corner in _facet(version)[0]:
        way = _sub(corner, eye)
        seen.append((focal * _dot(way, right) / _dot(way, ahead), focal * _dot(way, over) / _dot(way, ahead)))
    return tuple(max(p[i] for p in seen) - min(p[i] for p in seen) for i in range(2))


LEAK_POINTS = 0.25                      # texels between the points leaks() takes on the glass
LEAK_WAYS = (5.0, 10.0)                 # degrees between the ways it looks from: round, and up


def leaks(version=None):
    """The ways the lamp's glass is seen from that are not west of it: [(degrees round from the
    east to the south, degrees up)], empty when the shade is whole. The ruby's facet is there to
    be seen and is left out. Only the lamp's own boxes are asked, as solid ones: what else stands
    in the way is no part of the shade."""
    version = _version(version)
    models_, _stands, peeps = _built()
    model, facet = models_[f"{PREFIX}lamp_{version}"], peeps[version]
    a, e = np.meshgrid(np.radians(np.arange(-90.0, 90.0 + 1e-6, LEAK_WAYS[0])),
                       np.radians(np.arange(-90.0, 90.0 + 1e-6, LEAK_WAYS[1])), indexing="ij")
    a, e = a.reshape(-1), e.reshape(-1)
    ways = np.stack([np.cos(e) * np.cos(a), np.sin(e), np.cos(e) * np.sin(a)], axis=-1)
    seen = np.zeros(len(ways), dtype=bool)
    boxes = [_box(part) for part in model.parts]
    for own, part in enumerate(model.parts):
        if not part["emit"] or own == facet:
            continue
        c, h, turn = boxes[own]
        # the nearest boxes first: they are the shade, and a look they stop is not asked about again
        others = sorted((n for n in range(len(boxes)) if n not in (own, facet)),
                        key=lambda n: float(np.linalg.norm(boxes[n][0] - c)))
        ticks = [np.linspace(-h[i], h[i], max(2, int(math.ceil(2.0 * h[i] / LEAK_POINTS)) + 1)) for i in range(3)]
        for i in range(3):
            j, l = [k for k in range(3) if k != i]
            u, v = np.meshgrid(ticks[j], ticks[l], indexing="ij")
            for side in (-1.0, 1.0):
                front = np.nonzero(ways @ (side * turn[i]) > 1e-6)[0]
                if not len(front):
                    continue
                local = np.zeros(u.shape + (3,))
                local[..., i], local[..., j], local[..., l] = side * h[i], u, v
                points = local.reshape(-1, 3) @ turn + c
                way = np.tile(ways[front], (len(points), 1))
                start = np.repeat(points, len(front), axis=0) + way * 1e-4
                which = np.tile(front, len(points))
                for n in others:
                    if not len(which):
                        break
                    bc, bh, bturn = boxes[n]
                    o, w = (start - bc) @ bturn.T, way @ bturn.T
                    still = np.abs(w) < 1e-12
                    w = np.where(still, 1.0, w)
                    t0, t1 = (-bh - o) / w, (bh - o) / w
                    near = np.where(still, np.where(np.abs(o) <= bh, -np.inf, np.inf), np.minimum(t0, t1))
                    far = np.where(still, np.inf, np.maximum(t0, t1))
                    free = np.maximum(near.max(axis=1), 0.0) >= far.min(axis=1)
                    start, way, which = start[free], way[free], which[free]
                seen[which] = True
    return [(round(math.degrees(float(a[n])), 1), round(math.degrees(float(e[n])), 1)) for n in np.nonzero(seen)[0]]


def _surface(model, at, frame, scale, step=0.5):
    """For every box of a placed model: (its middle and half sizes in model units, its turn,
    points on its faces at most `step` texels apart, in scene coordinates)."""
    k = scale / 16.0
    for part in model.parts:
        c, h, turn = _box(part)
        ticks = [np.linspace(-h[i], h[i], max(2, int(math.ceil(2.0 * h[i] * scale / step)) + 1)) for i in range(3)]
        faces = []
        for i in range(3):
            j, l = [a for a in range(3) if a != i]
            u, v = np.meshgrid(ticks[j], ticks[l], indexing="ij")
            for face in (-h[i], h[i]):
                local = np.zeros(u.shape + (3,))
                local[..., i], local[..., j], local[..., l] = face, u, v
                faces.append(local.reshape(-1, 3) @ turn + c)
        points = (np.concatenate(faces) - np.array(model.anchor, dtype=float)) * k
        yield c, h, turn, np.array(at, dtype=float) + points @ np.array(frame, dtype=float)


FINE = 4                                # cells to the texel where fouling() keeps count
JOURNAL = 5.5                           # what turns no further than this from the axis is a journal


def fouling(version=None):
    """Where what stands still is inside what the mount sweeps as it turns about the polar axis:
    a list of (texels along the axis from the crossing, texels from the axis), empty when all is
    clear. Half a texel of overlap is let pass (a worm bites its wheel), and so are the journals,
    which run in their bearings. The tube is left out: where it can be pointed is the observer's
    care."""
    version = _version(version)
    built = _built()[0]
    where = {name: (at, frame, scale) for name, at, frame, scale in placed(version)}
    still, turning = ("pier_a", "axis_a") if version == "a" else ("piers_b", "yoke_b")
    centre, pole = np.array(crossing(version)), np.array(POLE)

    def polar(points):
        rel = points - centre
        along = rel @ pole
        return along * 16.0, np.linalg.norm(rel - np.outer(along, pole), axis=1) * 16.0

    # what the turning piece sweeps: for every slice across the axis, each box takes up a ring
    model, (at, frame, scale) = built[PREFIX + turning], where[PREFIX + turning]
    k, f = scale / 16.0, np.array(frame, dtype=float)
    rings = []
    for c, h, turn, points in _surface(model, at, frame, scale, step=1.0 / (FINE + 1)):
        along, out = polar(points)
        cell = np.floor(along * FINE).astype(int)
        first = cell.min()
        near, far = np.full(cell.max() - first + 1, np.inf), np.zeros(cell.max() - first + 1)
        np.minimum.at(near, cell - first, out)
        np.maximum.at(far, cell - first, out)
        # a slice the axis itself passes through the box in is swept from the axis outwards
        mid = (np.arange(len(near)) + first + 0.5) / FINE / 16.0
        on_axis = ((centre + np.outer(mid, pole) - np.array(at)) @ f.T) / k + np.array(model.anchor, dtype=float)
        near[(np.abs((on_axis - c) @ turn.T) <= h + 1e-9).all(axis=1)] = 0.0
        rings.append((first, near, far))
    lo = min(first for first, _near, _far in rings)
    hi = max(first + len(near) for first, near, _far in rings)
    top = int(max(far.max() for _first, _near, far in rings) * FINE) + 2
    swept = np.zeros((hi - lo, top), dtype=bool)
    for first, near, far in rings:
        for i in range(len(near)):
            a = 0 if near[i] == 0.0 else int(math.ceil((near[i] + 0.5) * FINE))
            b = int(math.floor((far[i] - 0.5) * FINE))
            if b >= a and np.isfinite(near[i]) and far[i] > JOURNAL:
                swept[first - lo + i, a:b + 1] = True
    swept[1:-1] &= swept[:-2] & swept[2:]
    swept[0] = swept[-1] = False
    found = []
    for _c, _h, _turn, points in _surface(built[PREFIX + still], *where[PREFIX + still]):
        along, out = polar(points)
        i, j = np.floor(along * FINE).astype(int) - lo, np.floor(out * FINE).astype(int)
        ok = (i >= 0) & (i < swept.shape[0]) & (j < swept.shape[1])
        hit = np.zeros(len(i), dtype=bool)
        hit[ok] = swept[i[ok], j[ok]]
        found.extend(zip(along[hit].round(2).tolist(), out[hit].round(2).tolist()))
    return found


def report(version=None):
    """(lines, problems): the numbers of one version and the rules it breaks (A0's rulings in
    plan/STATUS.md, the neighbours' in g2). Corners of boxes are measured, so a round part counts
    a little larger than it is."""
    version = _version(version)
    built = _built()[0]
    spec = _SPEC[version]
    points = {name: list(_corners(built[name], at, frame, scale)) for name, at, frame, scale in placed(version)}
    everything = [p for ps in points.values() for p in ps]
    # the two ends of the swing about the polar axis: the way the sky goes first, then the other
    swung = turning(version)

    def ends(ps):
        return [[followed(p, way * FOLLOW, version) for p in ps] for way in (1.0, -1.0)]

    still = [p for name, ps in points.items() if name not in swung for p in ps]
    swings = [still + ps for ps in ends([p for name in swung for p in points[name]])]
    centre, radius = sweep(version)
    lines = [
        f"version {version}: the axes cross at {_rounded(crossing(version))}, the tube {spec['off']:.3f} off the "
        f"polar axis, looking {ELEVATION:.2f} degrees up due west",
        f"  eyepiece {EYEPIECE[version]}  objective {OBJECTIVE[version]}  observer {OBSERVER[version]}",
        f"  sweep: centre {SWEEP[version][0]}, radius {radius}; V8 from {V8[version][0]} at {V8[version][1]}",
        f"  lamp at {_rounded(_lamp_at(version)[0])}, light source of level {LAMP_LEVEL}, its peep-hole "
        f"{peep(version)[0]:.1f} by {peep(version)[1]:.1f} screen pixels in V8 (720 high)",
        f"  {len(points)} display entities, {sum(len(built[n].parts) for n in points)} boxes",
    ]
    problems = []
    fence = {name: len(K.unsettled(built[name])) for name in points}
    if any(fence.values()):
        problems.append("faces stand between two axes of their model, the game lights them one way or the other: "
                        + ", ".join(f"{k} of {name}" for name, k in fence.items() if k))
    else:
        lines.append("  no face stands between two axes of its model: the game lights each the same way every time")
    if abs(ELEVATION - 41.0) > 0.5:
        problems.append(f"the tube looks {ELEVATION:.2f} degrees up, the comet's head is 41 up")
    if version == "b" and abs(spec["off"]) > 1e-9:
        problems.append("b: the tube is not on the dome's axis")
    if version == "a" and spec["off"] > 1.5:
        problems.append(f"a: the tube is {spec['off']:.3f} off the polar axis, over 1.5")
    if LAMP_LEVEL > 4:
        problems.append(f"the lamp's light source is of level {LAMP_LEVEL}, over 4")
    if max(peep(version)) >= POINT:
        problems.append(f"the lamp's peep-hole is {peep(version)[0]:.1f} by {peep(version)[1]:.1f} screen pixels "
                        f"in V8, a patch: a point stays under {POINT}")
    _four, middle, looks = _facet(version)
    if looks[1] < max(abs(looks[0]), abs(looks[2])) + 0.05:
        problems.append("the peep-hole's facet does not look up more than any other way: the game lights it "
                        "by half or three quarters, a dull point")
    if _dot(looks, _unit(_sub(V8[version][0], middle))) < 0.3:
        problems.append("the peep-hole's facet looks away from the camera of V8")
    name, box, _far = _first(version, v8(version)[0], middle)
    if (name, box) != (f"{PREFIX}lamp_{version}", _built()[2][version]):
        problems.append(f"the peep-hole is hidden from the camera of V8 behind box {box} of {name}")
    seen = leaks(version)
    if seen:
        problems.append(f"the lamp's shade leaks: its glass is seen from {len(seen)} ways that are not west of it, "
                        f"the first {seen[0][0]:.0f} degrees round from the east to the south and {seen[0][1]:.0f} up")
    else:
        lines.append("  the lamp's glass is seen from the west and from nowhere else")
    far = max(math.dist(p, centre) for p in everything)
    lines.append(f"  furthest corner {far:.2f} from the crossing")
    if far > radius + 0.05:
        problems.append(f"a corner is {far:.2f} from the crossing, outside the sweep of {radius}")
    low = min(p[1] for pose in [everything] + swings for p in pose)
    if low < CAP_Y - 1e-6:
        problems.append(f"a corner is at y {low:.2f}, below the cap")
    x0, z0, x1, z1 = S.PIER_CAP
    for name in ("pier_a", "piers_b"):
        ps = points.get(PREFIX + name)
        if ps:
            lo = [min(p[i] for p in ps) for i in range(3)]
            hi = [max(p[i] for p in ps) for i in range(3)]
            lines.append(f"  {name}: x {lo[0]:.2f}..{hi[0]:.2f}, y {lo[1]:.2f}..{hi[1]:.2f}, z {lo[2]:.2f}..{hi[2]:.2f}")
            if lo[0] < x0 - 1e-6 or hi[0] > x1 + 1 + 1e-6 or lo[2] < z0 - 1e-6 or hi[2] > z1 + 1 + 1e-6:
                problems.append(f"{name} stands over the edge of the cap (x {x0}..{x1 + 1}, z {z0}..{z1 + 1})")
    cells = solid(version)
    if cells:
        name, at, frame, scale = placed(version)[0]
        grid = np.linspace(0.0, 1.0, 9)
        inner = np.array([(x + i, y + j, z + k) for x, y, z in cells for i in grid for j in grid for k in grid])
        out = inner[~_within(built[name], at, frame, scale, inner)]
        lo = [min(c[i] for c in cells) for i in range(3)]
        hi = [max(c[i] for c in cells) for i in range(3)]
        lines.append(f"  {len(cells)} barrier cells inside the pier's iron: x {lo[0]}..{hi[0]}, y {lo[1]}..{hi[1]}, "
                     f"z {lo[2]}..{hi[2]}")
        if len(out):
            problems.append(f"a barrier reaches out of the pier's iron at {len(out)} of {len(inner)} points taken in "
                            f"its cells, the first {tuple(round(float(v), 3) for v in out[0])}")
        if hi[1] - lo[1] > 1:
            problems.append(f"the barrier in the pier stands {hi[1] - lo[1] + 1} cells high, over 2")
    if version == "a":
        ps = [p for p in points[PREFIX + "axis_a"] if _dot(_sub(p, crossing("a")), DEC) < -A_WEIGHTS[0] / 16.0 + 0.01]
        lo = [min(p[i] for p in ps) for i in range(3)]
        hi = [max(p[i] for p in ps) for i in range(3)]
        down = min(p[1] for end in ends(ps) for p in end)
        lines.append(f"  counterweight: x {lo[0]:.2f}..{hi[0]:.2f}, y from {lo[1]:.2f} (from {down:.2f} at the low end "
                     f"of the swing), z {lo[2]:.2f}..{hi[2]:.2f}")
        if min(lo[1], down) < 21.0:
            problems.append(f"a: the counterweight comes down to y {min(lo[1], down):.2f}, below 21")
    fouled = fouling(version)
    if fouled:
        problems.append(f"turning about the polar axis the mount fouls what stands still at {len(fouled)} points, "
                        f"the first {fouled[0][0]} texels along the axis and {fouled[0][1]} from it")
    else:
        lines.append("  turning about the polar axis the mount clears all that stands still")
    # where people stand: east of the railing on the observing floor, and the ring stair's exit
    rail = S.PIER_ENVELOPE[2] + 1.5
    over = [[p[1] for p in pose if p[0] > rail] for pose in [everything] + swings]
    if any(over):
        low, down = min(over[0], default=math.inf), min(y for ys in over for y in ys)
        lines.append(f"  lowest corner east of the railing: y {low:.2f}, {down:.2f} at the low end of the swing "
                     f"(a standing eye is at {FLOOR_Y + S.EYE:.2f})")
        if down < FLOOR_Y + S.EYE - 0.15:
            problems.append(f"a corner over the observing floor is at y {down:.2f}, in a standing person's face")
    ex, ez = S.DOME_CENTRE[0], S.PIER_ENVELOPE[1] - 1
    if any(ex <= p[0] <= ex + 1 and ez <= p[2] <= ez + 1 and p[1] < FLOOR_Y + 3 for pose in [everything] + swings for p in pose):
        problems.append("a corner is in the three cells over the ring stair's exit")
    half = S.SLIT_W / 2.0
    stand = V8[version][0]
    x0, z0, x1, z1 = OBSERVING
    if not (x0 + 0.3 <= stand[0] <= x1 + 0.7 and z0 + 0.3 <= stand[2] <= z1 + 0.7):
        problems.append(f"the camera of V8 at {stand} is not on the observing floor (x {x0}..{x1 + 1}, z {z0}..{z1 + 1})")
    if abs(stand[2] - AXIS[1]) > half - 0.3:
        problems.append(f"the camera of V8 at z {stand[2]} does not see the comet's head through the slit")
    tube = points[f"{PREFIX}tube_{version}"]
    wide = [p for pose in [tube] + ends(tube) for p in pose if abs(p[2] - AXIS[1]) > half]
    if wide:
        problems.append(f"the tube is wider than the slit: z {max(abs(p[2] - AXIS[1]) for p in wide):.2f} from the axis")
    # the swing: how far the eyepiece goes, and that the tube and the lamp stay out of what stands still
    e = eyepiece(version)
    go = _sub(followed(e, FOLLOW, version), e)
    lines.append(f"  the mount swings {FOLLOW} degrees to either side in {FOLLOW_PERIOD} ticks: the eyepiece goes "
                 f"{math.hypot(go[0], go[2]):.3f} blocks across the floor (east {go[0]:+.3f}, south {go[2]:+.3f}) and "
                 f"{go[1]:+.3f} up the way the sky goes, and as far the other way; the tube stays "
                 f"{half - max(abs(p[2] - AXIS[1]) for pose in [tube] + ends(tube) for p in pose):.2f} inside the slit's edge")
    name, at, frame, scale = placed(version)[0]
    carried = [p for n in swung[1:] for p in points[n]]
    for pose in ends(carried):
        inside = int(_within(built[name], at, frame, scale, np.array(pose)).sum())
        if inside > int(_within(built[name], at, frame, scale, np.array(carried)).sum()):
            problems.append(f"at an end of the swing {inside} corners of the tube and the lamp are inside {name}")
    return lines, problems


if __name__ == "__main__":
    bad = 0
    for v in VERSIONS:
        text, wrong = report(v)
        print("\n".join(text))
        for w in wrong:
            print(f"  BROKEN: {w}")
        bad += len(wrong)
    print(f"the version placed: {VERSION}; brightness (sky, block) {BRIGHTNESS}")
    raise SystemExit(1 if bad else 0)
