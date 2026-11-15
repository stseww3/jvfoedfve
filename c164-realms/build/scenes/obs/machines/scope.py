"""The great refractor of the dome room (plan/ART-PLAN.md 7.2; parts/A5-machines.md 2.1; card
plan/packages/machines/refractor.md). The star of view V8.

A riveted iron tube fifteen blocks long on an equatorial mount, standing on the cap of the pier
under the middle of the great dome and looking due west through the slit at the head of the comet.
Two mounts are kept side by side until the review picks one:

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
    scope.ELEVATION     degrees the tube looks up, due west: the comet's head (sky/comet)
    scope.BRIGHTNESS    the light every piece is shown in, whatever cell it hangs in

Every function takes version= ("a" or "b"; VERSION when left out).

The pieces that move are models of their own, each anchored on the axis it turns about, so the
motion line can swing them (plan 7.1): the tube about the declination axis, the axis piece (a) or
the yoke (b) about the polar axis, the governor about its spindle. Here they stand still.

Light: the room is kept dark for observing. The one lamp is the small red one beside the
eyepiece, hooded, its glass turned west on the tailpiece and away from the floor; the light it
throws is offered to the sky line at LAMP_LEVEL. It is the only signal red in the room.

    python -m scenes.obs.machines.scope      the numbers above and the rules they are held to
"""
import copy
import functools
import math

import numpy as np

from artkit import models as M
from artkit.pixelart import Mat

from ..common import palette as P
from ..common import skeleton as S

PREFIX = "mach_scope_"
VERSION = "b"                   # the version build() places until the review picks one
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

TUBE_LEN = 15.0
TUBE_R = 0.75                   # the body; the objective's cell is CELL_R
CELL_R = 15.0 / 16.0
# rise: the height of the axes' crossing over the cap. off: how far the tube's axis is from the
# crossing, along the declination axis. back: from the declination axis to the eyepiece's end.
_SPEC = {
    "a": dict(rise=5.0, off=0.9 / DEC[2], back=6.39),   # the tube in the plane z = 1.40
    "b": dict(rise=5.4, off=0.0, back=5.5),
}


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


def _rounded(p):
    return tuple(round(v, 3) for v in p)


EYEPIECE = {v: _rounded(eyepiece(v)) for v in VERSIONS}
OBJECTIVE = {v: _rounded(objective(v)) for v in VERSIONS}
OBSERVER = {v: _rounded(observer(v)) for v in VERSIONS}
SWEEP = {v: (_rounded(sweep(v)[0]), sweep(v)[1]) for v in VERSIONS}

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
STEEL = P.mat("iron", base=4)                           # bright shafts and journals
IRON_STUD = _as(Studded, IRON, "stud")
IRON_D_STUD = _as(Studded, IRON_D, "stud")
IRON_SEAM = _as(Studded, IRON, "seam", pitch=4)
BRASS_STUD = _as(Studded, BRASS_D, "stud")
BRASS_TICK = _as(Ticked, P.mat("brass", bevel=0), "tick")
IRON_TOOTH = _as(Ticked, P.mat("iron_dark", bevel=0), "tooth", long=0)
GLASS = _flat("night_glass", 2)
GLASS_D = _flat("night_glass", 0)
RED = _flat("signal", 1)                                # red paint: the governor's collar
RED_LENS = _flat("signal_glow", 2)
RED_HOT = _flat("signal_glow", 3)
HOOD = _flat("iron", 0)
DIAL = _flat("cream", 2)
HOOP_SEED, STRAP_SEED = 9001, 9002


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
FINDER_OFF, FINDER_R = 19.0, 4.0
TAIL_PLATE = (20.0, 24.0, 8.5)          # from, to (texels from the eyepiece's end) and radius


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

    # the tail: eyepiece, draw tube, focusing tube with its two wheels, the plate they are bolted to
    seg(0, 4, 2.0, BRASS_D, sides=8)
    seg(4, 10, 3.0, BRASS, sides=8)
    seg(10, 20, 4.5, BRASS_D, sides=8)
    seg(11, 12.5, 5.25, BRASS, sides=8)
    seg(18.5, 20, 5.5, BRASS, sides=8)
    d.tube("x", (0.0, z(15.0)), -8.0, 8.0, 0.75, STEEL, sides=4)
    for side in (-1.0, 1.0):
        d.tube("x", (0.0, z(15.0)), side * 6.5, side * 8.5, 2.5, BRASS, sides=8)
    s0, s1, plate_r = TAIL_PLATE
    seg(s0, s1, plate_r, IRON_D)
    seg(s0 + 1.0, s1 - 1.0, plate_r + 0.75, IRON_D_STUD)
    # the wheel the observer turns the tailpiece by
    d.ring("z", (0.0, 0.0, z(17.0)), 10.5, 1.5, 1.5, BRASS, sides=16)
    _spokes(d, "z", (0.0, 0.0, z(17.0)), 5.0, 10.0, 4, BRASS_D, wide=1.5, thick=1.0, start=45.0)
    for i in range(8):
        with d.turned(("z", 45.0 * i + 22.5)):
            d.box((-0.75, 11.0, z(17.75)), (0.75, 13.5, z(16.25)), BRASS_D)
    # cone and body: nine riveted hoops, one seam of rivets down the south side
    d.taper("z", (0.0, 0.0), z(s1), z(40.0), plate_r - 0.5, BODY_R, IRON, sides=12, steps=4)
    seg(40, 228, BODY_R, IRON)
    for s in HOOPS:
        seg(s - 1.5, s + 1.5, HOOP_R, IRON_STUD, seed=HOOP_SEED)
    with d.turned(("z", 90.0)):
        d.box((-1.5, BODY_R - 1.0, z(226.0)), (1.5, BODY_R + 0.5, z(43.0)), IRON_SEAM, grain="z")
    # the objective: an iron flange, the brass cell, the dark glass inside the lip of the dew cap
    seg(227, 230, 13.75, IRON_D_STUD)
    seg(230, 238, 15.0, BRASS)
    seg(232, 234, 15.2, BRASS_STUD, seed=HOOP_SEED + 1)
    d.tube("z", (0.0, 0.0), z(238.75), z(238.0), 13.25, GLASS, sides=12, cap=GLASS)
    d.tube("z", (0.0, 0.0), z(238.9), z(238.75), 6.0, GLASS_D, sides=8, cap=GLASS_D)
    d.ring("z", (0.0, 0.0, z(239.0)), 14.0, 2.0, 2.0, BRASS_D, sides=16)

    # the finder, square to the declination axis on the south and lower side, where the yoke and
    # the saddle never come
    with d.turned(("z", phi)):
        c = (0.0, FINDER_OFF)
        d.tube("z", c, z(80.0), z(16.0), FINDER_R, BRASS, sides=8)
        d.tube("z", c, z(82.0), z(77.0), FINDER_R + 0.75, BRASS_D, sides=8)
        d.tube("z", c, z(82.5), z(82.0), FINDER_R - 0.5, GLASS, sides=8, cap=GLASS)
        d.tube("z", c, z(16.0), z(11.0), 2.5, BRASS_D, sides=8)
        d.tube("z", c, z(11.0), z(8.5), 1.5, BRASS, sides=8)
        for s in (27.0, 66.0):
            d.tube("z", c, z(s + 1.5), z(s - 1.5), FINDER_R + 1.25, IRON_D, sides=8)
            d.box((-2.0, 10.0, z(s + 1.5)), (2.0, FINDER_OFF - FINDER_R, z(s - 1.5)), IRON_D)
    # two sliding weights on a rod, opposite the finder: they balance it
    with d.turned(("z", phi + 180.0)):
        d.tube("z", (0.0, 16.0), z(64.0), z(27.0), 0.75, STEEL, sides=4)
        for s in (30.0, 61.0):
            d.box((-1.0, 10.0, z(s + 1.0)), (1.0, 16.5, z(s - 1.0)), IRON_D)
        for s in (40.0, 46.5):
            d.tube("z", (0.0, 16.0), z(s + 2.5), z(s - 2.5), 3.0, BRASS_D, sides=8)

    # the clamp and slow-motion rods run from the declination axis down to the observer's hand
    reach = 104.0 if version == "a" else 78.0
    for swing in ((158.0, 202.0) if version == "a" else (-22.0, 22.0)):
        with d.turned(("z", phi - 90.0 + swing)):
            d.tube("z", (0.0, 15.5), z(reach), z(21.0), 0.6, BRASS, sides=4)
            d.tube("z", (0.0, 15.5), z(21.0), z(17.5), 1.5, BRASS_D, sides=8)
            for s in (30.0, 58.0, reach - 2.0):
                d.box((-0.75, 9.5 if s < 40 else 11.5, z(s + 0.75)), (0.75, 16.5, z(s - 0.75)), IRON_D)

    if version == "b":
        # the band the two trunnions are cast on; they run into the yoke's bearings
        seg(back - 7.0, back + 7.0, 13.5, IRON_D)
        for s in (back - 7.5, back + 7.5):
            seg(s - 1.0, s + 1.0, 14.25, IRON_STUD, seed=HOOP_SEED + 2)
        with d.turned(("z", phi - 90.0)):
            for side in (-1.0, 1.0):
                d.tube("y", (0.0, 0.0), side * 12.5, side * 16.5, 5.5, IRON_D, sides=8)
                for zz in (-4.0, 4.0):
                    d.box((-1.0, side * 12.0, zz - 0.75), (1.0, side * 15.0, zz + 0.75), IRON_STUD)
    else:
        # the saddle on the end of the declination axis and the two straps that hold the tube in it
        with d.turned(("z", phi - 90.0)):
            d.box((-9.0, -16.0, -21.0), (9.0, -11.0, 21.0), IRON_D)
            d.box((-11.0, -14.5, -19.0), (11.0, -9.5, -11.0), IRON_D)
            d.box((-11.0, -14.5, 11.0), (11.0, -9.5, 19.0), IRON_D)
            d.box((-10.0, -16.75, -22.0), (10.0, -15.5, 22.0), IRON_D_STUD)
            for zz in (-15.0, 15.0):
                d.tube("z", (0.0, 0.0), zz - 2.0, zz + 2.0, 13.4, IRON_STUD, seed=HOOP_SEED + 2)
                for side in (-1.0, 1.0):
                    d.box((side * 12.5, -9.0, zz - 1.5), (side * 15.5, -6.0, zz + 1.5), IRON_D)
                    d.tube("y", (side * 14.0, zz), -10.5, -4.5, 0.75, BRASS, sides=4)
    return d.m


# ---- a: the German mount ---------------------------------------------------------------------------
A_SLEEVE = (-38.0, -10.5, 8.0)          # the polar sleeve: from, to (texels along the axis from the crossing), radius
A_COLUMN = [                            # the pier's sections: y0, y1, half size along x and along z (texels)
    (6.0, 20.0, 17.0, 21.0),
    (22.0, 34.0, 15.0, 19.0),
    (36.0, 43.0, 13.5, 17.0),
]
A_WEIGHTS = (25.0, 38.0, 9.0)           # the counterweights: from, to (texels from the crossing), radius
A_CLOCK = (15.0, 23.0, -4.0)            # the driving clock's case on the pier's east face: x, y, z of its low north corner


def _corner_irons(d, x, z, y0, y1, mat=None):
    """Angle irons riveted up the four corners of a box column of half sizes x and z."""
    mat = mat or IRON_STUD
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            a, b = sorted((sx * x, sx * (x + 0.5)))
            c, e = sorted((sz * (z - 2.5), sz * (z + 0.5)))
            d.box((a, y0, c), (b, y1, e), mat, grain="y", seed=STRAP_SEED)
            a, b = sorted((sx * (x - 2.5), sx * (x + 0.5)))
            c, e = sorted((sz * z, sz * (z + 0.5)))
            d.box((a, y0, c), (b, y1, e), mat, grain="y", seed=STRAP_SEED)


def _clock(d, x, y, z):
    """The driving clock: a brass case on a bracket, a dial behind glass, the winding square. Its
    low north-west corner is at (x, y, z); it looks east. Returns where the governor stands."""
    d.box((x, y - 2.0, z + 1.0), (x + 5.0, y, z + 9.0), IRON_D)                      # bracket
    d.box((x, y, z), (x + 6.0, y + 13.0, z + 10.0), BRASS)
    d.box((x - 0.5, y + 12.0, z - 0.5), (x + 6.5, y + 13.5, z + 10.5), BRASS_D)
    d.box((x + 6.0, y + 2.0, z + 1.5), (x + 6.5, y + 11.0, z + 8.5), GLASS_D)
    d.tube("x", (y + 7.5, z + 5.0), x + 6.5, x + 6.9, 2.5, DIAL, sides=8, cap=DIAL)
    d.box((x + 6.9, y + 7.0, z + 4.5), (x + 7.2, y + 9.5, z + 5.5), HOOD)             # the hand
    d.tube("x", (y + 3.5, z + 5.0), x + 6.5, x + 7.5, 0.75, BRASS_D, sides=4)
    return (x + 3.0, y + 13.5, z + 2.5)


def _pier_a():
    d = _Px(PREFIX + "pier_a", MOUNT_SCALE)
    # the foot: a bed plate bolted to the cap, stepped up to the column
    d.box((-28.0, 0.0, -32.0), (28.0, 2.0, 32.0), IRON_D)
    d.box((-24.0, 2.0, -28.0), (24.0, 4.0, 28.0), IRON)
    d.box((-20.0, 4.0, -24.0), (20.0, 6.0, 24.0), IRON_D)
    for x in (-26.0, 0.0, 26.0):
        for zz in (-30.0, 0.0, 30.0):
            if x or zz:
                d.box((x - 1.0, 2.0, zz - 1.0), (x + 1.0, 3.5, zz + 1.0), STEEL)
    # the column: three cast sections bolted flange to flange, angle irons up the corners
    for i, (y0, y1, hx, hz) in enumerate(A_COLUMN):
        d.box((-hx, y0, -hz), (hx, y1, hz), IRON, grain="y")
        _corner_irons(d, hx, hz, y0, y1)
        d.box((-hx - 1.5, y1, -hz - 1.5), (hx + 1.5, y1 + 2.0, hz + 1.5), IRON_D_STUD)
    y_top = A_COLUMN[-1][1] + 2.0
    # the door of the clock's weight, and a plate where a maker would sign
    d.box((17.0, 8.0, -7.0), (17.75, 19.0, 7.0), IRON_D)
    d.box((17.75, 8.5, -6.5), (18.0, 18.5, -5.5), IRON_STUD)
    d.box((17.75, 13.0, 4.5), (18.75, 14.5, 5.5), BRASS)
    d.box((-4.0, 26.0, 19.0), (4.0, 30.0, 19.5), BRASS_D)

    # the head: two cheeks and a web, cast to the angle of the latitude, cradle the polar sleeve
    cy = _SPEC["a"]["rise"] * 16.0
    s0, s1, r = A_SLEEVE
    d.box((-11.0, y_top, -13.0), (11.0, y_top + 6.0, -5.0), IRON_D)
    with d.turned(("x", -LATITUDE), about=(0.0, cy, 0.0)):
        for side in (-1.0, 1.0):
            a, b = sorted((side * r, side * (r + 3.0)))
            d.box((a, cy + s0 + 2.0, -30.0), (b, cy - 14.0, 2.0), IRON_D)
            a, b = sorted((side * (r + 3.0), side * (r + 3.75)))
            d.box((a, cy + s0 + 3.0, -1.0), (b, cy - 15.0, 1.5), IRON_STUD, grain="y", seed=STRAP_SEED + 1)
        d.box((-r, cy + s0 + 4.0, -28.0), (r, cy - 14.0, -5.0), IRON)
        d.tube("y", (0.0, 0.0), cy + s0, cy + s1, r, IRON)
        for s in (s0 + 1.5, s1 - 1.5):
            d.tube("y", (0.0, 0.0), cy + s - 1.5, cy + s + 1.5, r + 1.0, IRON_STUD, seed=HOOP_SEED)
        # the hour circle and the worm wheel on the lower end of the polar axis
        d.tube("y", (0.0, 0.0), cy + s0 - 6.0, cy + s0, 3.0, STEEL, sides=8)
        d.tube("y", (0.0, 0.0), cy + s0 - 2.0, cy + s0 - 0.5, 10.5, IRON_TOOTH)
        _circle(d, "y", (0.0, cy + s0 - 3.5, 0.0), 13.0)
        d.tube("y", (0.0, 0.0), cy + s0 - 7.0, cy + s0 - 6.0, 4.0, BRASS, sides=8)
        # the worm in its box on the east side, driven from the clock below
        d.box((10.0, cy + s0 - 3.5, -5.0), (15.0, cy + s0 + 1.0, 1.0), BRASS_D)
    sq = math.sqrt(0.5)
    worm = (12.5, cy + (s0 - 1.25) * sq - 2.0 * sq, -(s0 - 1.25) * sq - 2.0 * sq)
    cx, cyy, cz = A_CLOCK
    top = _clock(d, cx, cyy, cz)
    d.rod((cx + 3.0, cyy + 13.5, cz + 7.5), worm, 0.6, BRASS, sides=4)
    d.tube("y", (cx + 3.0, cz + 7.5), cyy + 13.5, cyy + 15.0, 1.25, BRASS_D, sides=8)
    d.governor = top
    return d


def _axis_a():
    d = _Px(PREFIX + "axis_a", MOUNT_SCALE)
    # the head of the polar axis and the declination housing cast across it
    d.tube("y", (0.0, 0.0), -9.0, 9.0, 9.0, IRON)
    d.tube("y", (0.0, 0.0), -10.25, -9.0, 5.0, STEEL, sides=8)
    d.tube("y", (0.0, 0.0), 9.0, 10.5, 7.0, IRON_D)
    d.tube("y", (0.0, 0.0), 10.5, 12.0, 2.5, BRASS_D, sides=8)
    d.tube("z", (0.0, 0.0), -7.9, -5.5, 10.0, IRON_D_STUD)
    d.tube("z", (0.0, 0.0), -5.5, 15.0, 7.5, IRON)
    d.tube("z", (0.0, 0.0), 13.0, 15.0, 9.0, IRON_STUD, seed=HOOP_SEED)
    # the declination circle, read from the floor on the counterweight's side
    d.tube("z", (0.0, 0.0), 15.0, 16.0, 10.0, IRON_TOOTH)
    _circle(d, "z", (0.0, 0.0, 17.5), 13.0)
    d.box((-1.0, 11.0, 15.5), (1.0, 15.5, 19.0), BRASS_D)                            # the reader's index
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
B_SOUTH, B_NORTH = -47.5, 42.0          # the two bearings, texels along the polar axis from the crossing
B_GIRDER = (16.0, 21.0, 15.2, 5.0)      # the frame's long sides: inner and outer face (from the axis), half length, half depth
B_HUB = dict(south=(-40.0, -36.0), north=(33.0, 37.0))     # the end blocks, along the axis
B_TRESTLE_Z = -36.0                     # the plane of the north trestle, texels south of the cap's middle
B_CLOCK = (11.0, 6.0, 26.0)


def _yoke_b():
    d = _Px(PREFIX + "yoke_b", YOKE_SCALE)
    inner, outer, half, deep = B_GIRDER
    mid = (inner + outer) / 2.0
    ends = {"south": -B_HUB["south"][1], "north": -B_HUB["north"][0]}      # model z of each hub's inner face
    for side in (-1.0, 1.0):
        a, b = sorted((side * inner, side * outer))
        d.box((-deep, a, -half), (deep, b, half), IRON, grain="z")
        # riveted flanges along both edges of the outer face, stiffeners between
        o0, o1 = sorted((side * outer, side * (outer + 0.5)))
        for x in (-deep, deep - 2.0):
            d.box((x, o0, -half), (x + 2.0, o1, half), IRON_SEAM, grain="z", seed=STRAP_SEED)
        for zz in (-10.0, 10.0):
            d.box((-deep + 2.0, o0, zz - 1.0), (deep - 2.0, o1, zz + 1.0), IRON_D)
        # the bearing of the tube's trunnion
        t0, t1 = sorted((side * outer, side * (outer + 3.0)))
        d.tube("y", (0.0, 0.0), t0, t1, 6.5, IRON_D, sides=8)
        t0, t1 = sorted((side * (outer + 3.0), side * (outer + 4.5)))
        d.tube("y", (0.0, 0.0), t0, t1, 3.0, BRASS_D, sides=8)
        # the arms that run in to the pivots
        for zz in ends.values():
            near = math.copysign(half - 1.0, zz)
            d.beam((0.0, side * mid, near), (0.0, side * 5.5, zz), 2.0 * deep, outer - inner, IRON)
            d.beam((deep - 1.0, side * (mid + 2.6), near), (deep - 1.0, side * 8.1, zz), 2.0, 0.5, IRON_SEAM,
                   seed=STRAP_SEED + 1)
            d.beam((-deep + 1.0, side * (mid + 2.6), near), (-deep + 1.0, side * 8.1, zz), 2.0, 0.5, IRON_SEAM,
                   seed=STRAP_SEED + 1)
    for name, (s0, s1) in B_HUB.items():
        z0, z1 = sorted((-s0, -s1))
        d.box((-deep - 1.0, -8.5, z0), (deep + 1.0, 8.5, z1), IRON_D)
        d.box((-deep - 1.5, -9.0, z0 + 1.0), (deep + 1.5, 9.0, z1 - 1.0), IRON_D_STUD)
    # the journals: the south one carries the worm wheel and the hour circle
    south, north = -B_HUB["south"][0], -B_HUB["north"][1]
    d.tube("z", (0.0, 0.0), south, -B_SOUTH + 4.5, 3.5, STEEL, sides=8)
    d.tube("z", (0.0, 0.0), south, south + 1.0, 6.0, IRON_D, sides=8)
    d.tube("z", (0.0, 0.0), south + 1.0, south + 2.0, 12.0, IRON_TOOTH)
    _circle(d, "z", (0.0, 0.0, south + 2.75), 14.5, n=6)
    d.tube("z", (0.0, 0.0), north, -B_NORTH - 4.5, 3.5, STEEL, sides=8)
    d.tube("z", (0.0, 0.0), north - 1.0, north, 6.0, IRON_D, sides=8)
    # the declination circle on the upper side of the frame, where the floor sees it
    _circle(d, "y", (0.0, outer + 3.75, 0.0), 13.0)
    d.box((-1.0, outer + 0.5, 11.0), (1.0, outer + 5.0, 15.5), BRASS_D)
    return d.m


def _bearing(d, at, half=4.0, wide=7.5, low=-10.0):
    """A plummer block cast to the latitude about the point `at` of the polar axis."""
    x, y, z = at
    with d.turned(("x", -LATITUDE), about=at):
        d.box((x - wide, y - half, z + low), (x + wide, y + half, z + 4.0), IRON_D)
        d.box((x - wide, y - half + 1.0, z + 4.0), (x + wide, y + half - 1.0, z + 6.0), IRON)
        for side in (-1.0, 1.0):
            d.tube("z", (x + side * (wide - 2.0), y), z + 5.5, z + 7.5, 1.0, STEEL, sides=4)
        d.tube("y", (x, z), y - half - 0.75, y + half + 0.75, 4.75, BRASS_D, sides=8)


def _piers_b():
    d = _Px(PREFIX + "piers_b", YOKE_SCALE)
    cy = _SPEC["b"]["rise"] * 16.0
    sq = math.sqrt(0.5)
    south = (0.0, cy + B_SOUTH * sq, -B_SOUTH * sq)
    north = (0.0, cy + B_NORTH * sq, -B_NORTH * sq)
    # the bed: two riveted girders from the trestle's feet to the pedestal, sleepers across
    for x in (-18.0, 14.0):
        d.box((x, 0.0, -40.0), (x + 4.0, 3.0, 24.0), IRON_D, grain="z")
        d.box((x - 0.5, 3.0, -40.0), (x + 4.5, 3.75, 24.0), IRON_SEAM, grain="z", seed=STRAP_SEED)
    for zz in (-38.5, -16.0, 6.0):
        d.box((-24.0, 0.0, zz), (24.0, 2.5, zz + 5.0), IRON_D, grain="x")
    # the south pedestal: two cast sections, the thrust bearing on its head
    d.box((-15.0, 0.0, 20.0), (15.0, 3.0, 40.0), IRON_D)
    d.box((-11.0, 3.0, 23.0), (11.0, 22.0, 39.0), IRON, grain="y")
    d.box((-12.5, 22.0, 21.5), (12.5, 24.0, 40.0), IRON_D_STUD)
    d.box((-9.0, 24.0, 25.0), (9.0, 44.0, 38.5), IRON, grain="y")
    for x in (-11.0, 9.0):
        d.box((x, 3.0, 23.0 - 0.5), (x + 2.0, 22.0, 23.0), IRON_STUD, grain="y", seed=STRAP_SEED + 2)
        d.box((x, 3.0, 39.0), (x + 2.0, 22.0, 39.5), IRON_STUD, grain="y", seed=STRAP_SEED + 2)
    _bearing(d, south)
    with d.turned(("x", -LATITUDE), about=south):
        d.box((-6.0, south[1] - 6.5, south[2] - 6.0), (6.0, south[1] - 4.0, south[2] + 6.0), IRON)
    # the north trestle: an A of two legs on the cap's north edge, tied twice, braced to the bed
    tz = B_TRESTLE_Z
    foot, head = (22.0, 3.0), (5.0, 110.0)

    def leg_x(y):
        return foot[0] + (head[0] - foot[0]) * (y - foot[1]) / (head[1] - foot[1])

    for side in (-1.0, 1.0):
        d.box((side * foot[0] - 5.0, 0.0, tz - 4.0), (side * foot[0] + 5.0, 3.0, tz + 4.0), IRON_D)
        d.bar((side * foot[0], foot[1], tz), (side * head[0], head[1], tz), 5.0, 6.0, IRON)
        d.bar((side * (foot[0] + 2.75), foot[1], tz), (side * (head[0] + 2.75), head[1], tz), 0.5, 2.0, IRON_SEAM,
              seed=STRAP_SEED + 3)
        d.bar((side * leg_x(52.0), 52.0, tz + 2.0), (side * leg_x(52.0), 3.0, tz + 22.0), 4.0, 4.0, IRON_D)
        d.box((side * leg_x(52.0) - 4.0, 0.0, tz + 19.0), (side * leg_x(52.0) + 4.0, 3.0, tz + 26.0), IRON_D)
    for y in (38.0, 80.0):
        x = leg_x(y) + 1.0
        d.box((-x, y - 2.0, tz - 2.5), (x, y + 2.0, tz + 2.5), IRON_D, grain="x")
        d.box((-x, y - 0.5, tz + 2.5), (x, y + 0.5, tz + 3.0), IRON_SEAM, grain="x", seed=STRAP_SEED + 4)
    d.box((-8.0, 106.0, tz - 3.5), (8.0, 121.0, tz + 3.5), IRON_D)
    d.box((-9.0, 108.0, tz - 4.0), (9.0, 110.0, tz + 4.0), IRON_D_STUD)
    d.box((-5.0, 121.0, tz - 2.5), (5.0, 123.0, tz + 2.5), IRON)
    _bearing(d, north, low=-7.0, wide=7.0)
    # the driving clock on the pedestal's east face, its shaft up to the worm under the hour circle
    cx, cyy, cz = B_CLOCK
    top = _clock(d, cx, cyy, cz)
    circle = -B_HUB["south"][0] + 2.0           # along the axis, towards the south from the crossing
    worm = (13.0, cy - circle * sq - 2.5, circle * sq - 2.5)
    d.box((worm[0] - 2.5, worm[1] - 2.5, worm[2] - 3.0), (worm[0] + 2.5, worm[1] + 2.5, worm[2] + 3.0), BRASS_D)
    d.bar((10.5, 40.0, worm[2]), (worm[0], worm[1] - 2.0, worm[2]), 2.0, 3.0, IRON_D)
    d.rod((cx + 3.0, cyy + 13.5, cz + 7.5), (worm[0], worm[1] - 2.5, worm[2]), 0.6, BRASS, sides=4)
    d.tube("y", (cx + 3.0, cz + 7.5), cyy + 13.5, cyy + 15.0, 1.25, BRASS_D, sides=8)
    d.governor = top
    return d


# ---- the small pieces --------------------------------------------------------------------------------
def _governor():
    """The clock's flyball governor. Anchor: the foot of its spindle; it spins about y."""
    d = _Px(PREFIX + "governor", 1.0)
    d.tube("y", (0.0, 0.0), 0.0, 1.0, 1.5, BRASS_D, sides=8)
    d.tube("y", (0.0, 0.0), 1.0, 8.0, 0.5, STEEL, sides=4)
    d.tube("y", (0.0, 0.0), 3.0, 4.0, 1.0, RED, sides=8)
    d.tube("y", (0.0, 0.0), 7.5, 8.5, 1.0, BRASS_D, sides=8)
    for side in (-1.0, 1.0):
        d.rod((0.0, 7.75, 0.0), (side * 3.0, 4.5, 0.0), 0.3, BRASS_D, sides=4)
        d.rod((0.0, 3.5, 0.0), (side * 3.0, 4.5, 0.0), 0.3, BRASS_D, sides=4)
        d.ball((side * 3.25, 4.25, 0.0), 1.25, BRASS, sides=8, layers=4)
    return d.m


LAMP_OFF = (-0.25, 0.32, 0.62)          # the lamp's glass from the eyepiece: blocks east, up, south


def _lamp_at(version):
    """Where the red lamp hangs, and where its arm is clamped on the rim of the tail plate."""
    e = eyepiece(version)
    s0, s1, r = TAIL_PLATE
    rim = _add(_add(e, _mul(SIGHT, (s0 + s1) / 32.0)), (0.0, 0.0, r / 16.0))
    return _add(e, LAMP_OFF), rim


def _lamp(version):
    """The red lamp: a blackened hood on an arm from the tail plate, the ruby glass sunk in its
    west face under a shade. Anchor: the middle of the lamp's body; the model is level."""
    d = _Px(f"{PREFIX}lamp_{version}", 1.0)
    at, rim = _lamp_at(version)
    arm = tuple((rim[i] - at[i]) * 16.0 for i in range(3))
    d.tube("y", (0.0, 0.0), -3.0, 2.0, 2.0, HOOD, sides=8)
    d.tube("y", (0.0, 0.0), 2.0, 3.0, 2.5, IRON_D, sides=8)
    d.tube("y", (0.0, 0.0), 3.0, 4.0, 1.25, HOOD, sides=8)
    d.tube("y", (0.0, 0.0), -3.5, -3.0, 2.25, IRON_D, sides=8)
    # the shade over the glass: a roof and two cheeks, open to the west only
    d.box((-4.0, 1.25, -2.0), (-1.5, 1.75, 2.0), HOOD)
    for side in (-1.0, 1.0):
        a, b = sorted((side * 1.5, side * 2.0))
        d.box((-4.0, -2.25, a), (-1.5, 1.25, b), HOOD)
    d.box((-2.25, -1.75, -1.25), (-1.9, 0.75, 1.25), RED_LENS, emit=15, shade=False)
    d.box((-2.3, -1.0, -0.5), (-2.25, 0.0, 0.5), RED_HOT, emit=15, shade=False)
    # the arm: up from the hood's cap and over to its clamp on the tail plate
    knee = (0.0, 6.0, 0.0)
    d.rod((0.0, 4.0, 0.0), knee, 0.5, BRASS_D, sides=4)
    d.rod(knee, arm, 0.5, BRASS_D, sides=4)
    d.ball(knee, 0.9, BRASS, sides=8, layers=3)
    return d.m


@functools.lru_cache(maxsize=None)
def _built():
    pier_a, piers_b = _pier_a(), _piers_b()
    out = {m.name: m for m in (
        _tube("a"), _tube("b"), pier_a.m, _axis_a(), piers_b.m, _yoke_b(), _governor(), _lamp("a"), _lamp("b"))}
    stands = {"a": tuple(v / 16.0 for v in pier_a.governor), "b": tuple(v / 16.0 for v in piers_b.governor)}
    return out, stands


def models():
    return dict(_built()[0])


# ---- placing ---------------------------------------------------------------------------------------------
def _pose(frame):
    """Yaw and turns for artkit.models.display that carry a model's x, y and z to the three
    directions of `frame`: the model is turned about z, then about x, then about the upright."""
    x, y, z = frame
    tilt = -math.asin(max(-1.0, min(1.0, z[1])))
    swing = math.atan2(z[0], z[2])
    roll = math.atan2(x[1], y[1])
    return -math.degrees(swing), (("z", math.degrees(roll)), ("x", math.degrees(tilt)))


def _put(canvas, model, at, frame, scale, origin):
    yaw, turns = _pose(frame)
    x, y, z = _add(at, origin)
    canvas.add_entity(x, y, z, M.display(model, yaw=yaw, turns=turns, scale=scale, brightness=BRIGHTNESS))
    return 1


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


def build(canvas, origin=(0, 0, 0), version=None, lamp=True):
    """Stand the refractor on the pier's cap. Returns the number of display entities placed.

    lamp=False leaves the red lamp's light source out (the lamp itself stays): a test scene that
    wants the room without it.
    """
    version = _version(version)
    built = _built()[0]
    n = 0
    for name, at, frame, scale in placed(version):
        n += _put(canvas, built[name], at, frame, scale, origin)
    if lamp:
        try:
            from ..sky import _lightkit as L
        except ImportError:
            L = None
        if L is not None:
            cell = _add(_lamp_at(version)[0], origin)
            L.suggest(canvas, cell, LAMP_LEVEL, "machines/scope:lamp", rank=3)
    return n
