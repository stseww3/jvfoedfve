"""machines/scope: the great refractor telescope (plan ART-PLAN 7.2; parts/A5-machines.md 2.1;
card packages/machines/refractor.md). The star of the great dome room (view V8): a riveted iron
tube with brass end hoops on an equatorial mount, standing on the pier cap, pointing due west and
up through the observing slit at the comet.

Two versions are kept side by side until the review picks one (INTERFACE 2):
  a  German equatorial  long tube offset on the declination axis, a counterweight on the far side,
                        classic observatory style.
  b  English / cradle   the tube centred in a fork cradle, heavier graduated rings, industrial.

The tube, the finder, the counterweight and the governor flyball are their own display entities and
carry a marked axis, so the motion category can later swing the tube about the two equatorial axes
and spin the governor (plan 7.1; the pose here is static). All coordinates come from the skeleton;
the only numbers written here are the mount's own proportions and the placeholder tube elevation,
which c230 settles from the comet (41..57 deg; the tube takes 45..50).

For the master scene build() places one version on the pier; the test scene obs_mach_refractor
places both in box domes with a west slit.
"""
import functools
import math

from artkit import models as M

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S

PREFIX = "mach_scope_"
VERSION = "a"                       # the version build() places until the review picks one

# ---- materials (plan 3.1 ramps through the one palette) -----------------------------------------
IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
IRON_F = P.mat("iron_flat")
BRASS = P.mat("brass")
BRASS_D = P.mat("brass_dark")
BRASS_F = P.mat("brass_flat")
COPPER = P.mat("old_copper")
SLATE = P.mat("slate")


def _flat(name, step):
    return P.mat(name, kind="flat", base=step, bevel=0)


RED = _flat("signal", 2)           # red paint: the governor's warning dab
RED_LENS = _flat("signal_glow", 2)  # the one small red lamp by the eyepiece
DARK_GLASS = _flat("night_glass", 1)  # the objective seen end-on: a dark disc, not a lamp

# ---- geometry: from the skeleton, plus the mount's own proportions ------------------------------
AX, AZ = S.DOME_AXIS               # (4.5, 0.5): the dome/pier axis, a point
TOP_Y = S.PIER_TOP_Y              # 18.0: the pier cap top; the equatorial foot stands here

ELEV = 47.0       # tube elevation above the horizon, due west. In the slit and on the comet
#                   (c230: comet 41..57; the card: the tube takes 45..50). One number to retune.
LAT = 45.0        # polar-axis tilt placeholder (mid latitude); the axis points at the pole
TUBE_LEN = 15.0   # the optical tube, blocks (card)
BACK = 5.0        # pivot (declination axis) to the eyepiece end
FRONT = TUBE_LEN - BACK   # pivot to the objective end
MOUNT_H = 5.5     # the declination axis stands this high above the pier cap; the eyepiece then
#                   clears the floor (the rising floor meets the observer) and the objective clears
#                   the dome shell with room to spare (checked against the 11-block inner radius)
PED_H = 2.0       # pedestal, blocks above the cap
POLAR_LEN = 3.0   # the polar-axis housing
CW_LEN = 4.0      # the counterweight shaft (version a)

TUBE_SCALE = 5    # 15 blocks -> scale 5 (48 drawing units), density 16 px / block (A5 1.2)
TUBE_R = 0.75     # tube radius, blocks (diameter 1.5)
MOUNT_SCALE = 2
CAP_SCALE = 3     # the wide cap would not fit the element range at scale 2
CW_SCALE = 2
FINDER_SCALE = 2  # the 4-block finder would exceed the element range at scale 1


def _dir():
    """Unit vector from the eyepiece towards the objective: due west and up at ELEV."""
    e = math.radians(ELEV)
    return (-math.cos(e), math.sin(e), 0.0)


def _polar_dir():
    """Unit vector up the polar axis, towards the celestial pole: due north and up at the latitude."""
    t = math.radians(90.0 - LAT)
    return (0.0, math.cos(t), -math.sin(t))


def _polar_top():
    """The top of the polar axis (the declination bearing), as (dx, dy, dz) blocks from the cap."""
    pd = _polar_dir()
    return (0.0, PED_H + POLAR_LEN * pd[1], POLAR_LEN * pd[2])


# ---- combination helpers (A5 5.2 asks for these; kept in the module, no machines/_kit.py) -------
def riveted_tube(m, c, a0, a1, r, courses=5, hoop=BRASS, hub=BRASS_D):
    """A riveted iron tube along +z from a0 to a1, centre line c=(x, y): the iron barrel, raised
    iron courses with a row of rivets, a wide hoop at each end and a row of rivets along the top.
    The end hoops are the brass the comet view catches through the slit."""
    m.tube("z", c, a0, a1, r, IRON, sides=8)
    span = a1 - a0
    for i in range(1, courses + 1):
        z = a0 + span * i / (courses + 1)
        m.tube("z", c, z - 0.3, z + 0.3, r + 0.25, IRON_D, sides=8)
        for k in range(6):                                   # rivets around the course
            ang = math.pi * 2 * k / 6
            m.box((c[0] + (r + 0.1) * math.cos(ang) - 0.2, c[1] + (r + 0.1) * math.sin(ang) - 0.2, z - 0.2),
                  (c[0] + (r + 0.45) * math.cos(ang) + 0.2, c[1] + (r + 0.45) * math.sin(ang) + 0.2, z + 0.2),
                  IRON, seed=701)
    m.tube("z", c, a0, a0 + 1.4, r + 0.45, hoop, sides=8)     # eyepiece hoop (small)
    m.tube("z", c, a1 - 2.2, a1 - 0.8, r + 0.7, hoop, sides=8)  # objective hoop (big)
    m.taper("z", c, a1 - 0.8, a1, r + 0.4, r - 0.1, hub, sides=8, steps=2)


def grad_circle(m, axis, centre, r, width, ticks=36, ring=BRASS_D, rim=BRASS):
    """A graduated setting circle: a thick ring, a bright rim and a ring of ticks. `width` is its
    thickness along the axis; `ticks` divisions. Used on both mounts (heavier on version b)."""
    m.ring(axis, centre, r, 0.9, width, ring, sides=max(16, ticks))
    m.ring(axis, centre, r + 0.6, 0.35, width * 0.6, rim, sides=max(16, ticks))
    o1, o2 = [i for i in range(3) if i != M.AXES.index(axis)]
    for k in range(ticks):
        ang = 2 * math.pi * k / ticks
        p = [centre[0], centre[1], centre[2]]
        long = 0.55 if k % (ticks // 12) == 0 else 0.3
        p[o1] = centre[o1] + (r + 0.3) * math.cos(ang)
        p[o2] = centre[o2] + (r + 0.3) * math.sin(ang)
        d = [0.18, 0.18, 0.18]
        d[M.AXES.index(axis)] = width * 0.4
        d[o1] = long if abs(math.cos(ang)) > abs(math.sin(ang)) else 0.18
        d[o2] = long if abs(math.sin(ang)) >= abs(math.cos(ang)) else 0.18
        m.box((p[0] - d[0], p[1] - d[1], p[2] - d[2]), (p[0] + d[0], p[1] + d[1], p[2] + d[2]), rim, seed=702)


def governor(m, top, drop, ball_r=1.1):
    """The governor of the driving clock: a vertical spindle and two arms with a weighted ball on
    each, a dab of warning red on the collar. Spins about the vertical axis (its axis, for A8).
    `top` is the point of the spindle; it hangs `drop` below. Returns nothing."""
    x, y, z = top
    m.tube("y", (x, z), y - drop, y, 0.45, BRASS, sides=8)          # spindle
    m.tube("y", (x, z), y - drop, y - drop + 0.6, 0.9, RED, sides=8)  # red collar
    for s in (-1, 1):
        a = (x, y - 0.4, z)
        b = (x + s * 2.0, y - drop + 1.2, z)
        m.rod(a, b, 0.3, BRASS_D, sides=6)                         # arm
        m.ball((x + s * 2.0, y - drop + 1.2, z), ball_r, COPPER, sides=8, layers=5)  # fly-ball


def fork_mount(m, base_top, span):
    """A fork cradle (version b): two riveted arms straddling the tube `span` apart along x, rising
    from the polar top to the declination axis, braced across. Industrial, heavier than the German
    head. Drawn in the model's own units; `base_top` is the top of the polar axis (units)."""
    bx, by, bz = base_top
    for s in (-1, 1):
        m.beam((bx, by, bz), (bx + s * span, by + 1.0, bz), 2.4, 2.4, IRON)          # splay
        m.beam((bx + s * span, by + 1.0, bz), (bx + s * span, by + 12.0, bz + 4.0), 2.6, 3.4, IRON_D)  # arm
        for k in range(3):                                                           # rivets on the arm
            m.box((bx + s * span - 1.2, by + 2.0 + 3.0 * k, bz + 0.6),
                  (bx + s * span + 1.2, by + 2.4 + 3.0 * k, bz + 1.0), IRON, seed=703)


# ---- models ------------------------------------------------------------------------------------
def _tube():
    """The optical tube assembly: one continuous riveted iron barrel, brass hoops at both ends,
    objective cell at +z, eyepiece drawtube at -z. Anchor at the eyepiece end; runs +z to the
    objective. Shown stretched between the two ends (models.between), so no texture is drawn out."""
    m = M.Model(PREFIX + "tube", px=TUBE_SCALE, anchor=(0.0, 0.0, 0.0))
    L = TUBE_LEN * 16.0 / TUBE_SCALE                 # 48 units
    r = TUBE_R * 16.0 / TUBE_SCALE                   # 2.4 units
    riveted_tube(m, (0.0, 0.0), 2.0, L - 0.5, r, courses=5)
    m.tube("z", (0.0, 0.0), 0.0, 2.0, r * 0.55, BRASS_D, sides=8)     # eyepiece drawtube
    m.tube("z", (0.0, 0.0), 0.5, 1.1, r * 0.8, BRASS, sides=8)        # eyepiece collar
    m.box((r * 0.55 - 0.1, -0.9, 0.4), (r * 0.55 + 1.2, 0.9, 1.6), BRASS_D)   # focuser knob
    import artkit.models as _m  # dark objective disc, seen end-on from outside the slit
    m.tube("z", (0.0, 0.0), L - 0.5, L, r - 0.2, DARK_GLASS, sides=8, cap=DARK_GLASS)
    return m


def _finder():
    """The finder scope: a small brass tube on brackets, lying along the main tube. Anchor at its
    back end; runs +z. Shown stretched between its two ends."""
    m = M.Model(PREFIX + "finder", px=FINDER_SCALE, anchor=(0.0, 0.0, 0.0))
    L = 4.0 * 16.0 / FINDER_SCALE                    # 32 units
    r = 0.25 * 16.0 / FINDER_SCALE                   # 2 units
    m.tube("z", (0.0, 0.0), 0.0, L, r, BRASS, sides=8)
    m.tube("z", (0.0, 0.0), L - 2.0, L, r + 0.6, BRASS_D, sides=8)    # objective ring
    m.tube("z", (0.0, 0.0), 0.0, 1.5, r + 0.5, BRASS_D, sides=8)      # eyepiece ring
    for z in (L * 0.3, L * 0.7):                                      # brackets down to the tube
        m.box((-0.6, -r - 2.5, z - 0.6), (0.6, -r, z + 0.6), IRON_D)
    return m


def _cap():
    """The iron cap over the stone pier cap: a plate, a raised hub for the mount foot and a ring of
    brass foot bolts. Anchor at the centre of its underside; sits on the cap top (y 18)."""
    m = M.Model(PREFIX + "cap", px=CAP_SCALE)
    U = 16.0 / CAP_SCALE
    r = 2.7 * U
    m.tube("y", (0.0, 0.0), 0.0, 0.7 * U, r, IRON, sides=16)
    m.tube("y", (0.0, 0.0), 0.0, 0.3 * U, r + 0.4, IRON_D, sides=16)   # a lip round the rim
    m.tube("y", (0.0, 0.0), 0.7 * U, 1.2 * U, 1.7 * U, IRON_D, sides=12)  # hub
    nb = 12
    for i in range(nb):
        a = 2 * math.pi * i / nb
        bx, bz = (r - 1.0 * U) * math.cos(a), (r - 1.0 * U) * math.sin(a)
        m.box((bx - 0.6, 0.6 * U, bz - 0.6), (bx + 0.6, 0.95 * U, bz + 0.6), BRASS, seed=704)
    return m


def _mount_a():
    """The German equatorial head (static): pedestal, a polar-axis housing leaning north at the
    latitude, a declination arm reaching the tube's pivot, and the two setting circles. The tube
    and the counterweight are placed separately. Anchor at the centre of the cap top; built in
    world-aligned units at scale 2 so build() places it with yaw 0."""
    m = M.Model(PREFIX + "mount_a", px=MOUNT_SCALE)
    U = 16.0 / MOUNT_SCALE                            # 8 units / block
    pt = _polar_top()                                 # blocks
    ptu = (pt[0] * U, pt[1] * U, pt[2] * U)           # units
    mu = (0.0, MOUNT_H * U, 0.0)                      # the pivot, units
    m.tube("y", (0.0, 0.0), 0.0, PED_H * U, 1.4 * U, IRON, sides=12)       # pedestal
    m.tube("y", (0.0, 0.0), PED_H * U - 0.4 * U, PED_H * U + 0.3 * U, 1.7 * U, IRON_D, sides=12)
    grad_circle(m, "y", (0.0, PED_H * U, 0.0), 1.9 * U, 0.7 * U, ticks=36)  # RA circle
    m.rod((0.0, PED_H * U, 0.0), ptu, 1.0 * U, IRON, sides=10)             # polar-axis housing
    m.rod(ptu, mu, 0.7 * U, IRON, sides=8)                                 # declination arm to the pivot
    m.ball(ptu, 1.2 * U, IRON_D, sides=10, layers=6)                       # the bearing knuckle
    grad_circle(m, "z", (0.0, MOUNT_H * U, 0.0), 1.6 * U, 0.6 * U, ticks=36)  # dec circle, faces the room
    m.tube("z", (0.0, MOUNT_H * U), -0.7 * U, 0.7 * U, 0.9 * U, IRON_D, sides=10)  # the saddle
    return m


def _mount_b():
    """The English / cradle head (static): pedestal, a polar-axis housing, a riveted fork cradle
    straddling the tube with a heavy graduated ring on each arm. The tube sits centred between the
    arms; no counterweight. Anchor at the centre of the cap top; world-aligned units at scale 2."""
    m = M.Model(PREFIX + "mount_b", px=MOUNT_SCALE)
    U = 16.0 / MOUNT_SCALE
    pt = _polar_top()
    ptu = (pt[0] * U, pt[1] * U, pt[2] * U)
    m.tube("y", (0.0, 0.0), 0.0, PED_H * U, 1.6 * U, IRON, sides=12)       # heavier pedestal
    m.tube("y", (0.0, 0.0), PED_H * U - 0.4 * U, PED_H * U + 0.3 * U, 1.9 * U, IRON_D, sides=12)
    grad_circle(m, "y", (0.0, PED_H * U, 0.0), 2.1 * U, 0.8 * U, ticks=48)  # heavier RA circle
    m.rod((0.0, PED_H * U, 0.0), ptu, 1.2 * U, IRON, sides=10)             # polar-axis housing
    fork_mount(m, ptu, 1.3 * U)                                            # the cradle arms
    for s in (-1, 1):                                                      # heavy dec rings on the arms
        grad_circle(m, "x", (s * 1.3 * U, MOUNT_H * U, 0.0), 1.9 * U, 0.7 * U, ticks=48)
    return m


def _cw():
    """The counterweight (version a): a riveted iron shaft with an old-copper weight at the end.
    Anchor at the shaft root (the declination bearing); runs +z to the weight. Moves with the tube
    about the declination axis (its axis, for A8)."""
    m = M.Model(PREFIX + "cw", px=CW_SCALE, anchor=(0.0, 0.0, 0.0))
    L = CW_LEN * 16.0 / CW_SCALE                      # 32 units
    m.tube("z", (0.0, 0.0), 0.0, L - 3.0, 0.8, IRON, sides=8)
    m.tube("z", (0.0, 0.0), L - 3.2, L - 0.4, 2.6, COPPER, sides=12)       # the weight
    m.tube("z", (0.0, 0.0), L - 3.2, L - 0.4, 2.9, COPPER, sides=12, cap=COPPER)
    m.tube("z", (0.0, 0.0), L - 0.4, L, 1.0, IRON_D, sides=8)              # end nut
    return m


def _drive():
    """The driving clock (转仪钟): a brass box with an old-copper weight drum hanging below, fixed
    to the mount by the polar axis. The governor is a separate model. Anchor at the top centre; the
    drum hangs down."""
    m = M.Model(PREFIX + "drive", px=1)
    m.box((-1.6, -1.0, -1.1), (1.6, 1.0, 1.1), BRASS)                      # the clock case
    m.box((-1.7, 0.6, -1.2), (1.7, 1.0, 1.2), BRASS_D)
    m.tube("y", (0.0, 0.0), -5.5, -1.0, 1.0, COPPER, sides=12)            # weight drum, hanging
    m.tube("y", (0.0, 0.0), -5.5, -5.0, 1.3, COPPER, sides=12, cap=COPPER)
    m.box((-0.3, -1.0, 0.9), (0.3, 0.6, 1.3), BRASS_D)                     # winding arbor
    return m


def _lamp():
    """The one small red lamp by the eyepiece (night observing; the only light). A small iron
    housing and a red lens that glows; A2 is handed the light source. Anchor at the fixing point."""
    m = M.Model(PREFIX + "lamp", px=1)
    m.box((-1.0, -1.0, -1.0), (1.0, 1.0, 0.2), IRON_D)
    m.tube("z", (0.0, 0.0), 0.0, 1.0, 1.3, IRON, sides=8)                  # bezel
    m.box((-0.8, -0.8, 1.0), (0.8, 0.8, 1.25), RED_LENS, emit=15, shade=False)  # the red lens
    return m


def _piston():
    """One hydraulic column of the rising observation floor: a steel ram in a cylinder with a
    flange, half extended (static). A5 does only the exposed columns; the floor is A3/A4's, the
    rise interface is A8's. Anchor at the foot on the dome-room floor."""
    m = M.Model(PREFIX + "piston", px=1)
    m.tube("y", (0.0, 0.0), 0.0, 1.0, 2.2, IRON_D, sides=12)               # base flange
    m.tube("y", (0.0, 0.0), 1.0, 5.0, 1.6, IRON, sides=12)                 # cylinder
    m.tube("y", (0.0, 0.0), 5.0, 8.5, 1.0, BRASS_D, sides=8)               # the ram, drawn out
    m.tube("y", (0.0, 0.0), 8.5, 9.0, 1.4, IRON_D, sides=8)                # ram head under the floor
    return m


@functools.lru_cache(maxsize=None)
def _models():
    return {m.name: m for m in (_tube(), _finder(), _cap(), _mount_a(), _mount_b(),
                                _cw(), _drive(), _lamp(), _piston())}


def models():
    return dict(_models())


SCALE = {PREFIX + "tube": TUBE_SCALE, PREFIX + "finder": FINDER_SCALE, PREFIX + "cap": CAP_SCALE,
         PREFIX + "mount_a": MOUNT_SCALE, PREFIX + "mount_b": MOUNT_SCALE, PREFIX + "cw": CW_SCALE,
         PREFIX + "drive": 1.0, PREFIX + "lamp": 1.0, PREFIX + "piston": 1.0}

# the four hydraulic columns of the rising floor, round the pier envelope corners, clear of the
# ring-stair exit on the east/south side (card; skeleton PIER_ENVELOPE x 1..7, z -3..3)
_PISTONS = [(2.0, 3.0), (6.0, 3.0), (2.0, -2.0), (6.0, -2.0)]


# ---- placing -----------------------------------------------------------------------------------
def _put(canvas, model, pos, scale, yaw=0.0, turns=(), **kw):
    canvas.add_entity(pos[0], pos[1], pos[2], M.display(model, yaw=yaw, scale=scale, turns=turns, **kw))
    return 1


def _span(canvas, model, a, b, thick, length, **kw):
    canvas.add_entity(a[0], a[1], a[2], M.between(model, a, b, thick=thick, length=length, **kw))
    return 1


def _offer_lights(canvas, lights, why):
    """Hand light sources [((x, y, z), level)] (cells, scene coords) to A2; place a block ourselves
    until A2's tool is in the tree (same contract as props/_kit.offer_lights)."""
    try:
        from ..sky import _lightkit
        take = getattr(_lightkit, "take", None)
    except ImportError:
        take = None
    if take is not None:
        take(canvas, lights, why)
        return
    for (x, y, z), lvl in lights:
        canvas.set(int(x), int(y), int(z), f"{B.LIGHT}[level={int(lvl)}]", keep=True)


def build(canvas, origin=(0, 0, 0), version=VERSION, light=True):
    """Place one telescope on the pier (the default version, or the one asked for). Returns the
    number of display entities. The pier, floor and dome shell are other packages'."""
    ox, oy, oz = origin
    base = (ox + AX, oy + TOP_Y, oz + AZ)             # cap top centre
    piv = (ox + AX, oy + TOP_Y + MOUNT_H, oz + AZ)    # declination axis (tube pivot)
    d = _dir()
    eye = tuple(piv[i] - BACK * d[i] for i in range(3))
    obj = tuple(piv[i] + FRONT * d[i] for i in range(3))
    mdl = _models()
    n = 0
    n += _put(canvas, mdl[PREFIX + "cap"], base, CAP_SCALE)
    n += _put(canvas, mdl[PREFIX + "mount_" + version], base, MOUNT_SCALE)
    n += _span(canvas, mdl[PREFIX + "tube"], eye, obj, TUBE_SCALE, TUBE_LEN * 16.0 / TUBE_SCALE)
    # the finder lies along the upper side of the tube, near the eyepiece
    perp = (math.sin(math.radians(ELEV)), math.cos(math.radians(ELEV)), 0.0)
    fa = tuple(piv[i] - 1.0 * d[i] + (TUBE_R + 0.6) * perp[i] for i in range(3))
    fb = tuple(fa[i] + 4.0 * d[i] for i in range(3))
    n += _span(canvas, mdl[PREFIX + "finder"], fa, fb, FINDER_SCALE, 4.0 * 16.0 / FINDER_SCALE)
    if version == "a":
        pt = _polar_top()
        pworld = (base[0] + pt[0], base[1] + pt[1], base[2] + pt[2])
        away = (pt[0] - 0.0, pt[1] - MOUNT_H, pt[2] - 0.0)           # from the pivot towards the bearing
        mag = math.sqrt(sum(v * v for v in away)) or 1.0
        u = tuple(v / mag for v in away)
        cw_end = tuple(pworld[i] + CW_LEN * u[i] for i in range(3))
        n += _span(canvas, mdl[PREFIX + "cw"], pworld, cw_end, CW_SCALE, CW_LEN * 16.0 / CW_SCALE)
    # the driving clock sits on the south face of the pedestal; the governor spins on top of it
    drive = (base[0] + 0.0, base[1] + PED_H + 0.4, base[2] + 2.0)
    n += _put(canvas, mdl[PREFIX + "drive"], drive)
    gov = M.Model(PREFIX + "gov_tmp")  # the governor is drawn here so its spin axis is world-vertical
    governor(gov, (0.0, 0.0, 0.0), 2.4)
    canvas.add_entity(drive[0], drive[1] + 1.0, drive[2], M.display(gov, scale=1.0))
    n += 1
    # the four hydraulic columns of the rising floor
    for px, pz in _PISTONS:
        n += _put(canvas, mdl[PREFIX + "piston"], (ox + px + 0.5, oy + TOP_Y, oz + pz + 0.5), 1.0)
    # the one small red lamp by the eyepiece, and its light source for A2
    lamp = tuple(eye[i] + (-0.6 * d[i]) for i in range(3))
    lamp = (lamp[0] + 0.8, lamp[1] + 0.2, lamp[2] + 0.8)
    n += _put(canvas, mdl[PREFIX + "lamp"], lamp, 1.0, yaw=-90.0)
    if light:
        _offer_lights(canvas, [((int(lamp[0]), int(lamp[1]), int(lamp[2])), 6)], "machines/scope:eyepiece lamp")
    return n
