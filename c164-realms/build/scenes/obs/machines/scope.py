"""machines/scope: the great refractor of the dome room (plan ART-PLAN 7.2; parts/A5-machines.md 2.1;
card packages/machines/refractor.md). The star of view V8: a riveted iron tube with a brass hoop at
each end, riding an equatorial head on the telescope pier, pointed at the comet through the west
slit. Two mountings stand side by side for the review to choose between.

    a  German      a pedestal, the polar axle leaning north at the latitude, the declination axis
                   crossing it, the tube on the saddle 1.5 blocks out along that axis and a
                   counterweight on its far end: one long and one short slanted bar in outline
    b  English     an English cradle: the polar axle carried at both ends by brackets on the cap,
                   a fork straddling the tube, heavy graduated rings, the tube on the dome axis

THE NUMBERS (director #388.3 and #442.3; c237's figures in #427, kept)

    elevation   ELEV, the comet's head: due west, 41.05 deg (sky/comet). The tube looks straight at
                it, so what the room shows down the tube is what the map is about.
    pier cap    S.PIER_TOP_Y = 18.0, the cap's top face. The head's foot is the iron cap model on
                it, centred on the dome axis.
    axes        version a crosses at (4.5, 23.0, 0.5), version b at (4.5, 23.4, 0.5). Version b's
                is the higher by 0.4 because the room's east rail (c231) leaves a person standing
                at x 8.86, and at 23.4 a standing person's eye is on the tube's axis.
    tube        the tube's axis passes through SADDLE: for a, 1.5 blocks out from the axes along
                the declination axis -- the most the director allows, and still inside the slit's
                z -2..2 with its hoops (they reach z 2.35) -- and in the vertical plane z 1.40;
                for b, on the axes themselves, the plane z 0.5, as the director requires.
    counterweight  version a's hangs on the far end of the declination axis, north-west and down,
                its lowest point at y 21.1: above the north stair exit's floor, as required (no
                lower than y 21). Version b has none.
    sweep       the radius the objective's hoop sweeps round the axes: 9.0 (a), 9.6 (b). The dome
                gear's toothed ring is at 10.8 in y 24.5, so more than a block is left clear.
    brightness  (10, 7) for every piece, so no step shows where two meet: the slit's sky is 15, the
                eyepiece end seven blocks in is 8 to 9, and the room's one lamp is 4.
    scale       px = scale, so every piece keeps 16 pixels to the block: the tube 15 blocks at
                scale 5 (48 units), the head at scale 3, the cap at 2, small parts at 2 and 1.

READING THE POSE (interiors/domeroom and the reviewers read these; do not write the numbers out
again elsewhere): eyepiece(version), objective(version), observer(version), sweep(version), all in
scene coordinates, the version defaulting to VERSION.

WHAT MOVES (plan 7.1; the motion category drives it, this module only poses it): the tube and the
counterweight turn about the declination axis, the head about the polar axis; the governor spins
about its vertical spindle. axes() gives the point, the axis and the motion of each.

    from scenes.obs.machines import scope
    n = scope.build(canvas, origin, version="a")      # one telescope on the pier; the entity count
"""
import functools
import math

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S

PREFIX = "mach_scope_"
VERSION = "a"                   # the version build() places until the review picks one
VERSIONS = ("a", "b")

# ---- materials (the plan's ramps, through the one palette) ---------------------------------------
IRON = P.mat("iron")
IRON_D = P.mat("iron", base=1, kind="metal", noise=0.12)      # the darker course of a riveted barrel
BRASS = P.mat("brass")
BRASS_D = P.mat("brass", base=1, kind="metal", noise=0.12)    # its shaded side and its marks' backing
COPPER = P.mat("old_copper")
GLASS = P.mat("night_glass", kind="plain", noise=0.06, bevel=0)   # the objective, seen end-on: dark
RED = P.mat("signal", kind="metal", noise=0.10, base=1)           # painted red: the governor's collar
RED_GLASS = P.mat("signal_glow", kind="glow", bevel=0, base=2)    # the one lamp's red lens

# the setting circles' scale is painted into the ring's own picture, never cut into boxes: a box
# narrower than a pixel flickers at a distance (cr2-M2 2)
MARK = P.RAMPS["brass"][4]

# ---- geometry: the skeleton, then this machine's own figures -------------------------------------
AX, AZ = S.DOME_AXIS            # (4.5, 0.5): the dome and pier axis, a point
CAP_Y = S.PIER_TOP_Y            # 18.0: the pier cap's top face; the head's foot stands here
ELEV = 41.05                    # the tube's elevation: the comet's head, due west (sky/comet, c230)
LAT = getattr(S, "LATITUDE", 45.0)   # the polar axis rises this far above the northern horizon

TUBE_LEN = 15.0                 # the optical tube, blocks (card)
TUBE_R = 0.75                   # its radius: diameter 1.5 (card)
HOOP_R = 0.95                   # the objective's brass hoop: diameter 1.9 (c237 #427)
OFFSET = {"a": 1.5, "b": 0.0}   # the tube's axis off the axes, along the declination axis (#388.3)
BACK = {"a": 6.39, "b": 5.50}   # the saddle to the eyepiece end (c237 #427's two poses)
PIVOT_Y = {"a": 23.0, "b": 23.4}   # where the two axes cross (c237 #427)
SWEEP_R = {"a": 9.0, "b": 9.6}     # the objective hoop's radius about the axes (c237 #427)
CW_FLOOR = 21.0                 # the director's floor under version a's weight (no lower than 21)

BRIGHTNESS = (10, 7)            # every piece of the machine (c220, 11-15)

# 16 pixels to the block at every scale (px = scale), so a 48-unit drawing is 3 blocks at scale 1
# and 15 at scale 5. A piece takes the smallest scale that keeps it inside 48 units.
TUBE_SCALE = 5                  # 15 blocks -> 48 units
HEAD_SCALE = 3                  # the head stands 8 blocks tall: at 2 it would overflow 48 units
CAP_SCALE = 2                   # 5 blocks across -> 40 units
SMALL_SCALE = 2                 # the counterweight shaft, the finder
FIN_SCALE = 1                   # the driving clock, the governor, the lamp: under 3 blocks


def _dir():
    """Unit vector from the eyepiece towards the objective: due west, up at ELEV."""
    e = math.radians(ELEV)
    return (-math.cos(e), math.sin(e), 0.0)


def _up():
    """Unit vector square to the tube in its vertical plane, towards its sky side."""
    e = math.radians(ELEV)
    return (math.sin(e), math.cos(e), 0.0)


def _pole():
    """Unit vector up the polar axis, towards the celestial pole: due north, up at the latitude."""
    t = math.radians(LAT)
    return (0.0, math.sin(t), -math.cos(t))


def _dec():
    """Unit vector of the declination axis, from the axes' crossing towards the tube: square to both
    the polar axis and the tube's. A tube at ELEV due west, about a polar axis at LAT, is carried on
    this one axis whichever mount holds it, and it is what puts version a's saddle 1.5 out at
    (5.29, 23.90, 1.40) and its weight down at (3.5, 21.9, -0.5), as c237 reported."""
    p, d = _pole(), _dir()
    u = (p[1] * d[2] - p[2] * d[1], p[2] * d[0] - p[0] * d[2], p[0] * d[1] - p[1] * d[0])
    mag = math.sqrt(sum(v * v for v in u)) or 1.0
    return tuple(v / mag for v in u)


def pivot(version=None):
    """The point where the polar and declination axes cross, in scene coordinates."""
    return (AX, PIVOT_Y[version or VERSION], AZ)


def saddle(version=None):
    """The point where the tube's axis crosses the declination axis, in scene coordinates."""
    v = version or VERSION
    p, u = pivot(v), _dec()
    return tuple(p[i] + OFFSET[v] * u[i] for i in range(3))


def eyepiece(version=None):
    """The centre of the eyepiece end's face, in scene coordinates (c237 #427, kept)."""
    v = version or VERSION
    s, d = saddle(v), _dir()
    return tuple(s[i] - BACK[v] * d[i] for i in range(3))


def objective(version=None):
    """The centre of the objective end's face, in scene coordinates (c237 #427, kept)."""
    v = version or VERSION
    s, d = saddle(v), _dir()
    return tuple(s[i] + (TUBE_LEN - BACK[v]) * d[i] for i in range(3))


def observer(version=None):
    """Where a person stands to look through the eyepiece: east of the eyepiece end, feet on the
    dome-room floor, eye on the tube's axis. Version b's figures are the ones the east rail was
    set for (c231); version a's stand south of the tube's plane."""
    v = version or VERSION
    eye, d = eyepiece(v), _dir()
    return (eye[0] + 0.1 * -d[0], CAP_Y, eye[2])


def sweep(version=None):
    """The radius the objective's hoop sweeps round the axes, blocks (the dome gear is at 10.8)."""
    return SWEEP_R[version or VERSION]


# ---- pictures: the setting circles' scale is painted, not built ----------------------------------
def _mark(body, w, h, long):
    """The picture of one division of a setting circle: the ring's own picture with a mark across
    the middle. w, h: the face in pixels. The mark is centred both ways, so it reads the same
    whichever way round a face shows its picture."""
    length = max(2, (w - 2) // (2 if long else 3))
    lo = (w - length) // 2
    hi = lo + length
    rows = ["".join("t" if lo <= i < hi else "." for i in range(w))] * max(1, h)
    return Sprite(f"{PREFIX}mark_{w}x{h}{'l' if long else ''}", rows, {"t": MARK}, back=body)


def grad_circle(m, axis, centre, r_out, thick, width, ticks, seed=1):
    """A graduated setting circle about `axis` through `centre`: a ring of `ticks` segments whose
    two flat faces carry one painted mark to the division, every third one longer. The sides are
    the divisions, so no mark is ever narrower than a pixel."""
    k = M.AXES.index(axis)
    o1, o2 = [i for i in range(3) if i != k]
    half = r_out * math.tan(math.pi / ticks)
    lo, hi = [0.0] * 3, [0.0] * 3
    lo[k], hi[k] = centre[k] - width / 2.0, centre[k] + width / 2.0
    lo[o1], hi[o1] = centre[o1] + r_out - thick, centre[o1] + r_out
    lo[o2], hi[o2] = centre[o2] - half, centre[o2] + half
    outer, inner, flats = M.SIDE[o1][1], M.SIDE[o1][0], M.SIDE[k]
    lit = {outer: "along", inner: "inner", flats[0]: "along", flats[1]: "along"}
    _, ua, va = M.FACE_AXES[flats[0]]
    w, h = (max(1, int(round((hi[a] - lo[a]) * m.px))) for a in (ua, va))
    back = BRASS_D.variant(0, "along")
    marks = [_mark(back, w, h, False), _mark(back, w, h, True)]
    for i in range(ticks):
        theta = 360.0 * i / ticks
        m.box(tuple(lo), tuple(hi), BRASS_D, rot=(axis, theta, tuple(centre)) if theta else None,
              skip="".join(M.SIDE[o2]), grain=M.AXES[o2], seed=seed,
              faces=dict.fromkeys(flats, marks[0 if i % 3 else 1]), lit=lit)
    return m


def riveted_tube(m, c, a0, a1, r, courses, hoop_at=(), hoop_r=None):
    """The iron barrel of a tube from a0 to a1 along +z, its centre line at c = (x, y) in the
    model's own frame: a raised course every length with a row of rivets round it, one row along
    the top between courses, and a wide brass hoop at each end.

    Every rivet is 2 pixels across at every scale (a block is 16), so a 15-block barrel reads as the
    same bolted iron as an A1 plate, and its brass hoops are what the comet's light catches."""
    m.tube("z", c, a0, a1, r, IRON, sides=8)
    span = a1 - a0
    pitch = span / (courses + 1)
    for i in range(1, courses + 1):
        z = a0 + pitch * i
        m.tube("z", c, z - 0.3, z + 0.3, r + 0.25, IRON_D, sides=8)
        for k in range(8):                                  # a rivet every 45 degrees round it
            ang = math.pi * 2 * k / 8
            rx, ry = (r + 0.45) * math.cos(ang), (r + 0.45) * math.sin(ang)
            m.box((c[0] + rx - 0.22, c[1] + ry - 0.22, z - 0.22),
                  (c[0] + rx + 0.22, c[1] + ry + 0.22, z + 0.22), IRON_D, seed=700 + k)
    for i in range(courses + 1):                            # the top seam's rivets, along the length
        z = a0 + pitch * (i + 0.5)
        m.box((c[0] - 0.22, c[1] + r - 0.1, z - 0.22),
              (c[0] + 0.22, c[1] + r + 0.2, z + 0.22), IRON_D, seed=720 + i)
    hr = hoop_r if hoop_r is not None else r + 0.45
    for at, wide in hoop_at or ((a0, 0.9), (a1 - 1.6, 1.4)):
        m.tube("z", c, at, at + wide, hr, BRASS, sides=8)
        m.tube("z", c, at - 0.15, at, hr, BRASS_D, sides=8)      # a shadow line at its foot


# ---- models --------------------------------------------------------------------------------------
def _tube():
    """The optical tube: one continuous riveted iron barrel, 15 blocks long, a small brass hoop and
    the drawtube at the eyepiece end, a wide hoop round the objective, the dark objective glass
    behind it. One model, so the courses and the rivets run its whole length without a join. Anchor
    at the eyepiece end's face centre; runs +z towards the objective."""
    m = M.Model(PREFIX + "tube", px=TUBE_SCALE, anchor=(0.0, 0.0, 0.0))
    L = TUBE_LEN * 16.0 / TUBE_SCALE                     # 48 units
    r = TUBE_R * 16.0 / TUBE_SCALE                       # 2.4
    hr = HOOP_R * 16.0 / TUBE_SCALE                      # 3.04
    m.tube("z", (0.0, 0.0), 0.0, 2.2, r * 0.55, BRASS_D, sides=8)       # drawtube
    m.tube("z", (0.0, 0.0), 0.5, 1.2, r * 0.85, BRASS, sides=8)         # eyepiece collar
    m.box((r * 0.5, -1.0, 0.5), (r * 0.5 + 2.4, 1.0, 1.9), BRASS_D)     # the focuser
    m.tube("z", (0.0, 0.0), 1.9, 2.6, r + 0.45, BRASS, sides=8)         # the eyepiece hoop
    riveted_tube(m, (0.0, 0.0), 2.6, L - 2.2, r, courses=9, hoop_at=((L - 3.6, 2.0),))
    m.taper("z", (0.0, 0.0), L - 1.6, L - 0.2, hr, hr - 0.45, BRASS, sides=8, steps=2)
    m.tube("z", (0.0, 0.0), L - 0.2, L, r - 0.15, GLASS, sides=8, cap=GLASS)
    return m


def _finder():
    """The finder: a small brass tube on two iron brackets along the main tube's sky side. Anchor at
    its eyepiece end; runs +z."""
    m = M.Model(PREFIX + "finder", px=SMALL_SCALE, anchor=(0.0, 0.0, 0.0))
    L, r = 4.0 * 16.0 / SMALL_SCALE, 0.25 * 16.0 / SMALL_SCALE
    m.tube("z", (0.0, 0.0), 0.0, 1.4, r + 0.5, BRASS_D, sides=8)
    m.tube("z", (0.0, 0.0), 1.2, L - 2.0, r, BRASS, sides=8)
    m.tube("z", (0.0, 0.0), L - 2.4, L, r + 0.6, BRASS_D, sides=8)
    for z in (L * 0.25, L * 0.72):
        m.box((-0.5, -r - 2.6, z - 0.5), (0.5, -r, z + 0.5), IRON_D)
    return m


def _cap():
    """The iron cap bolted over the stone pier: a flat plate with a lip over the stone, a shallow
    hub, and a ring of brass bolts. Anchor at the centre of its underside, on the cap's top."""
    m = M.Model(PREFIX + "cap", px=CAP_SCALE)
    U = 16.0 / CAP_SCALE
    r = 2.5 * U
    m.tube("y", (0.0, 0.0), 0.0, 0.3 * U, r + 0.4, IRON_D, sides=16)    # the lip over the stone
    m.tube("y", (0.0, 0.0), 0.2 * U, 0.8 * U, r, IRON, sides=16)
    m.tube("y", (0.0, 0.0), 0.8 * U, 1.2 * U, 1.3 * U, IRON_D, sides=12)  # the hub
    for i in range(12):
        a = 2 * math.pi * i / 12
        bx, bz = (r - 0.9 * U) * math.cos(a), (r - 0.9 * U) * math.sin(a)
        m.box((bx - 0.45, 0.6 * U, bz - 0.45), (bx + 0.45, 0.9 * U, bz + 0.45), BRASS, seed=760)
    return m


# the models are drawn in the model's own frame: the anchor is the centre of the cap's top face, so
# a figure in blocks above the cap is (world y - CAP_Y) * 16 / scale units
def _local(y_block, z_block=0.0):
    """A point in HEAD_SCALE units from a block figure above the cap top, `z_block` south of it."""
    U = 16.0 / HEAD_SCALE
    return (0.0, (y_block - CAP_Y) * U, z_block * U)


def _mount_a():
    """The German head (static): the pedestal on the cap's centre, a yoke carrying the polar axle
    leaning north at the latitude, the declination bearing where it crosses, the saddle 1.5 blocks
    out along the declination axis, the two setting circles, and the weight's short shaft on the far
    side. The tube and the weight itself are placed separately by build(). Anchor at the cap top's
    centre; world-aligned units at HEAD_SCALE, so build() places it with no turn."""
    m = M.Model(PREFIX + "mount_a", px=HEAD_SCALE)
    U = 16.0 / HEAD_SCALE
    pv = _local(PIVOT_Y["a"])                                # the axes' crossing, units
    m.tube("y", (0.0, 0.0), 0.0, 1.7 * U, 1.5 * U, IRON, sides=12)              # the pedestal
    m.tube("y", (0.0, 0.0), 1.5 * U, 2.2 * U, 1.85 * U, IRON_D, sides=12)       # its collar
    grad_circle(m, "y", (0.0, 2.2 * U, 0.0), 2.0 * U, 0.45 * U, 0.4 * U, ticks=24, seed=11)
    m.beam((0.0, 2.2 * U, 0.0), pv, 1.5 * U, 1.2 * U, IRON)                     # the yoke
    u = _pole()
    a = tuple(pv[i] - 2.2 * U * u[i] for i in range(3))                          # the polar axle
    b = tuple(pv[i] + 2.0 * U * u[i] for i in range(3))
    m.rod(a, b, 0.8 * U, IRON, sides=10)
    m.ball(pv, 0.95 * U, IRON_D, sides=10, layers=6)                             # the knuckle
    d = _dec()
    s = tuple(pv[i] + OFFSET["a"] * U * d[i] for i in range(3))                  # the saddle
    m.rod(pv, s, 0.5 * U, IRON, sides=8)                                         # the dec stub
    m.tube("y", (0.0, s[1], s[2]), -0.9 * U, 0.9 * U, 1.0 * U, IRON_D, sides=8)  # the saddle ring
    m.tube("z", (0.0, s[1]), s[2] - 0.8 * U, s[2] + 0.8 * U, 0.95 * U, IRON_D, sides=8)
    grad_circle(m, "z", (0.0, pv[1], pv[2]), 1.7 * U, 0.4 * U, 0.3 * U, ticks=24, seed=12)
    return m


def _mount_b():
    """The English cradle head (static): a heavier pedestal, the polar axle carried by an A-frame at
    the cap's north edge (the tall one) and a bracket at its south edge (the short one), and a fork
    rising from the axle to straddle the tube, a heavy graduated ring on each arm. The tube sits on
    the axes between the arms, as the director requires; there is no counterweight. Anchor and units
    as version a."""
    m = M.Model(PREFIX + "mount_b", px=HEAD_SCALE)
    U = 16.0 / HEAD_SCALE
    pv = _local(PIVOT_Y["b"])
    m.tube("y", (0.0, 0.0), 0.0, 1.6 * U, 1.7 * U, IRON, sides=12)
    m.tube("y", (0.0, 0.0), 1.4 * U, 2.2 * U, 2.05 * U, IRON_D, sides=12)
    grad_circle(m, "y", (0.0, 2.2 * U, 0.0), 2.3 * U, 0.5 * U, 0.4 * U, ticks=36, seed=21)
    # the polar axle: leaning north at the latitude, its two ends over the cap's north and south
    # edges, the north one higher (an A-frame carries it there, a short bracket the south end)
    u = _pole()
    axle = [(tuple(pv[i] + t * U * u[i] for i in range(3))) for t in (-2.3, 2.1)]
    m.rod(axle[0], axle[1], 0.7 * U, IRON, sides=10)
    for end, legs in ((axle[0], 1.5), (axle[1], 2.0)):                # the north one is the A-frame
        for sx in (-1, 1):
            m.beam((sx * legs * 0.5 * U, 0.0, end[2]), (0.0, end[1] - 0.5 * U, end[2]),
                   0.55 * U, 0.6 * U, IRON)                           # a splayed leg
        m.box((-1.1 * U, end[1] - 0.6 * U, end[2] - 0.35 * U),
              (1.1 * U, end[1] - 0.3 * U, end[2] + 0.35 * U), IRON_D)   # its head
        m.box((-0.35 * U, end[1] - 0.9 * U, end[2] - 0.35 * U),
              (0.35 * U, end[1] - 0.5 * U, end[2] + 0.35 * U), BRASS_D)  # the bearing
    for s in (-1, 1):                                                  # the fork's two arms
        ear = (0.0, pv[1], pv[2] + s * 1.3 * U)
        root = (0.0, pv[1] - 1.3 * U, pv[2] + s * 0.55 * U)
        m.beam(root, ear, 0.8 * U, 0.9 * U, IRON)                       # the arm
        m.tube("z", (0.0, ear[1]), ear[2] - 0.4 * U, ear[2] + 0.4 * U, 0.6 * U, IRON_D, sides=8)
        grad_circle(m, "z", ear, 1.4 * U, 0.35 * U, 0.35 * U, ticks=36, seed=31 + s)
    m.beam((0.0, pv[1] - 1.4 * U, pv[2] - 1.3 * U), (0.0, pv[1] - 1.4 * U, pv[2] + 1.3 * U),
           0.5 * U, 0.6 * U, IRON)                                     # the brace between the arms
    return m


def _cw():
    """The counterweight (version a): a riveted shaft with an old-copper weight on its far end.
    Anchor at the shaft's root on the declination bearing; runs +z to the weight. It turns with the
    tube about the declination axis (the motion category's)."""
    m = M.Model(PREFIX + "cw", px=SMALL_SCALE, anchor=(0.0, 0.0, 0.0))
    L = 2.6 * 16.0 / SMALL_SCALE
    m.tube("z", (0.0, 0.0), 0.0, L - 1.4, 0.62, IRON, sides=8)
    m.tube("z", (0.0, 0.0), L - 1.6, L - 0.2, 2.0, COPPER, sides=12)
    m.tube("z", (0.0, 0.0), L - 1.6, L - 0.2, 2.3, COPPER, sides=12, cap=COPPER)
    m.tube("z", (0.0, 0.0), L - 0.2, L, 0.8, IRON_D, sides=8)
    return m


def _drive():
    """The driving clock (转仪钟): a brass case with its winding arbor, and the weight drum hanging
    on its barrel below. The governor is a model of its own. Anchor at the top centre; the drum
    hangs down. It hangs close against the pedestal's south face (cr2-M2 2)."""
    m = M.Model(PREFIX + "drive", px=FIN_SCALE)
    m.box((-2.6, -1.7, -1.8), (2.6, 1.7, 1.8), BRASS)                   # the case, about 1 block
    m.box((-2.8, 1.1, -2.0), (2.8, 1.7, 2.0), BRASS_D)                  # its lid
    m.box((-0.5, -1.7, 1.8), (0.5, -0.2, 2.6), BRASS_D)                 # the winding arbor
    m.tube("y", (0.0, 0.0), -12.0, -1.7, 1.5, COPPER, sides=12)         # the weight drum
    m.tube("y", (0.0, 0.0), -12.0, -11.0, 1.9, COPPER, sides=12, cap=COPPER)
    m.tube("y", (0.0, 0.0), -1.7, -1.0, 0.6, IRON_D, sides=8)           # its chain
    return m


def _gov():
    """The governor as its own model, so its spin axis is the vertical line through its entity: the
    spindle, two arms with a flyball each, the warning-red collar. Anchor at the spindle's top."""
    m = M.Model(PREFIX + "governor", px=FIN_SCALE)
    m.tube("y", (0.0, 0.0), -7.0, 0.0, 0.45, BRASS, sides=8)
    m.tube("y", (0.0, 0.0), -7.0, -6.5, 0.85, RED, sides=8)
    for s in (-1, 1):
        m.rod((0.0, -0.3, 0.0), (s * 2.6, -6.0, 0.0), 0.3, BRASS_D, sides=6)
        m.ball((s * 2.6, -6.0, 0.0), 1.3, COPPER, sides=8, layers=5)
    return m


def _lamp():
    """The room's one lamp, at the eyepiece (director #442.3): an iron housing under a deep shade,
    its red lens turned west onto the focuser and the setting circles, its back to the observer's
    floor. Anchor at the fixing point; build() gives it the turn that points the lens west."""
    m = M.Model(PREFIX + "lamp", px=FIN_SCALE)
    m.box((-1.4, -1.4, -1.4), (1.4, 1.4, 0.2), IRON_D)                  # the housing
    m.tube("z", (0.0, 0.0), -0.8, 0.5, 1.7, IRON, sides=8)              # its bezel
    m.box((-1.1, 1.0, -1.2), (1.1, 1.6, 1.9), IRON_D)                   # the shade over the lens
    m.box((-0.9, -0.9, 0.5), (0.9, 0.9, 0.8), RED_GLASS, emit=15, shade=False)   # the lens, west
    return m


@functools.lru_cache(maxsize=None)
def _models():
    return {m.name: m for m in (_tube(), _finder(), _cap(), _mount_a(), _mount_b(),
                                _cw(), _drive(), _gov(), _lamp())}


def models():
    return dict(_models())


def axes():
    """{model: (the point its entity stands on, the axis it turns about, the motion)}: what the
    motion category has to swing and spin, in scene coordinates for the default version."""
    p, d, u = pivot(), _dir(), _dec()
    return {
        PREFIX + "tube": (eyepiece(), d, "very slow tracking about the declination axis"),
        PREFIX + "cw": (p, d, "the same turn as the tube, about the declination axis"),
        PREFIX + "mount_a": (p, _pole(), "the head turns about the polar axis, under the tube"),
        PREFIX + "mount_b": (p, _pole(), "the head turns about the polar axis, under the tube"),
        PREFIX + "governor": ((p[0], p[1] + 3.2, p[2]), (0.0, 1.0, 0.0),
                              "spins about its vertical spindle, evenly and slowly"),
    }


# ---- placing -----------------------------------------------------------------------------------
def _put(canvas, model, pos, yaw=0.0, **kw):
    """A model at its own scale, so every piece keeps 16 pixels to the block (px = scale)."""
    canvas.add_entity(pos[0], pos[1], pos[2],
                      M.display(model, yaw=yaw, scale=model.px, brightness=BRIGHTNESS, **kw))
    return 1


def _stretch(canvas, model, a, b, length):
    """A model drawn along +z from its anchor and `length` units long, stretched from a to b at its
    own scale, so the picture is never drawn out (a stretched rivet becomes a streak)."""
    canvas.add_entity(a[0], a[1], a[2],
                      M.between(model, a, b, thick=model.px, length=length, brightness=BRIGHTNESS))
    return 1


def _aim(canvas, model, a, b):
    """A model of fixed length drawn along +z from its anchor, turned to point from a at b and
    standing at a: no stretch at all, so its rivets and its weight stay square."""
    dx, dy, dz = (b[i] - a[i] for i in range(3))
    yaw = math.degrees(math.atan2(-dx, dz))
    pitch = math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    canvas.add_entity(a[0], a[1], a[2],
                      M.display(model, yaw=yaw, scale=model.px, turns=(("x", -pitch),),
                                brightness=BRIGHTNESS))
    return 1


def _offer_lights(canvas, lights, why):
    """Hand light sources [((x, y, z), level)] in cells to A2 (sky/lights); put a block down
    ourselves until that tool is in the tree -- the contract props/_kit.offer_lights keeps."""
    try:
        from ..sky import _lightkit
        take = getattr(_lightkit, "take", None)
    except ImportError:
        take = None
    if take is not None:
        take(canvas, lights, why)
        return
    for (x, y, z), level in lights:
        canvas.set(int(x), int(y), int(z), f"{B.LIGHT}[level={int(level)}]", keep=True)


LIGHT = ((int(round(eyepiece()[0])) + 1, int(round(eyepiece()[1])), int(round(eyepiece()[2]))), 4)
"""The one lamp's light source: a cell (east of the eyepiece end, at its height) and the level 4 of
director #442.3. A2 reads this instead of writing the numbers out again."""


def build(canvas, origin=(0, 0, 0), version=VERSION, light=True):
    """One telescope standing on the pier: the cap, the head, the tube, the finder, the driving
    clock with its governor, version a's counterweight, and the room's one lamp. Returns the number
    of display entities placed."""
    v = version if version in VERSIONS else VERSION
    ox, oy, oz = origin
    base = (ox + AX, oy + CAP_Y, oz + AZ)
    d, u = _dir(), _up()
    mdl = _models()
    n = 0
    n += _put(canvas, mdl[PREFIX + "cap"], base)
    n += _put(canvas, mdl[PREFIX + "mount_" + v], base)
    eye = tuple(ox + p for p in eyepiece(v))
    obj = tuple(ox + p for p in objective(v))
    n += _stretch(canvas, mdl[PREFIX + "tube"], eye, obj, TUBE_LEN * 16.0 / TUBE_SCALE)
    # the finder lies along the tube's sky side, its eyepiece end three blocks back from the saddle,
    # drawn at its own length (4 blocks) rather than stretched
    s = tuple(ox + p for p in saddle(v))
    fa = tuple(s[i] - 3.0 * d[i] + (TUBE_R + 0.8) * u[i] for i in range(3))
    fb = tuple(fa[i] + 4.0 * d[i] for i in range(3))
    n += _aim(canvas, mdl[PREFIX + "finder"], fa, fb)
    pv = tuple(ox + p for p in pivot(v))
    if v == "a":
        # the weight on the far end of the declination axis: down and north-west from the axes, its
        # lowest point clear of the floor (director #388.3: no lower than y 21). Drawn at its own
        # length, so its weight stays a disc
        far = tuple(-t for t in _dec())
        root = tuple(pv[i] + 1.35 * far[i] for i in range(3))
        drop = min(2.6, (root[1] - CW_FLOOR) / max(0.1, -far[1]))
        end = tuple(root[i] + drop * far[i] for i in range(3))
        n += _aim(canvas, mdl[PREFIX + "cw"], root, end)
    # the driving clock and its governor on the pedestal's south face, above the cap
    drive = (pv[0], oy + CAP_Y + 1.35, pv[2] + 1.05)
    n += _put(canvas, mdl[PREFIX + "drive"], drive)
    n += _put(canvas, mdl[PREFIX + "governor"], (drive[0], drive[1] + 1.75, drive[2]))
    # the one lamp, its red lens turned west onto the focuser (director #442.3)
    lamp = (eye[0] + 0.7, eye[1] - 1.0, eye[2] + 0.15)
    n += _put(canvas, mdl[PREFIX + "lamp"], lamp, yaw=-90.0)
    if light:
        _offer_lights(canvas, [((LIGHT[0][0] + ox, LIGHT[0][1] + oy, LIGHT[0][2] + oz), LIGHT[1])],
                      "machines/scope: the one lamp by the eyepiece")
    return n
