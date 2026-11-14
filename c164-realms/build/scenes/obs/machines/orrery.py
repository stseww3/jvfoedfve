"""The great orrery (plan ART-PLAN 7.2 / 8; parts/A5-machines.md 2.3; card packages/machines/orrery.md).

The star of the star hall: a brass solar system hung in the well on the entrance axis, between the
telescope pier at the west end and the east wall. It reads from three places the plan asks it to
hold (A0 #207): from the front door, looking west and up, the warm sun is the one note of light in
the doorway; straight below, looking up, the six arms wheel round the sun; and from the gallery and
the ring stair it stands at eye level.

Coordinates are the skeleton's (the card's old centre (7.5,0) and diameter 7 are void):

    ORRERY_CENTRE = (11.5, 0.5)   the hung centre (x, z)
    ORRERY_R      = 2.5           outer radius; the ring of planets keeps inside it
    ORRERY_HANG_Y = 14.0          the ceiling's lower face: the hub seats on interiors' hang point
    ORRERY_RING_Y = 8.5           the plane of the arms and the sun, at gallery eye height
    ORRERY_BODY_Y = (8.0, 14.0)   the machine fills this; the floor below (y 0..8) stays walkable

Two versions stand side by side until the review picks one (card: both six planets, both turn slow):
  a  planar      the six arms share one plane, the gear train is open above them
  b  tiered      the arms splay into a shallow bowl under a cage of brass meridian rings (armillary)

The motion is A8's; this round places a still pose. The six arms are separate models so A8 can turn
each on its own: EACH ARM'S ANCHOR IS THE CENTRE, AND ITS AXIS IS THE WORLD VERTICAL THROUGH THE
CENTRE -- turning the display entity about that point sweeps the planet round its orbit. SPIN below
gives a suggested rate per planet (six different, all slow); A8 settles the timing. The sun throws
no light of its own; build() offers one warm source at its cell to A2, kept low (the hall's one warm
core, bright area under a third).

The combined pieces the card asked for -- gear() and grad_circle() -- live here, not in a shared
machines/_kit.py (that file is not to be made yet); another machine imports them from this module.

    from scenes.obs.machines import orrery
    n += orrery.build(canvas, origin, version="a")     # places one orrery; returns the entity count
"""
import functools
import math

from artkit import models as M

from ..common import palette as P
from ..common import skeleton as S
from ..props import _kit as K

PREFIX = "mach_orrery_"
VERSION = "a"                    # the version build() places until the review picks one

# --- materials (palette only) -------------------------------------------------------------------
BRASS = P.mat("brass")
BRASS_D = P.mat("brass_dark")
IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
VERDIGRIS = P.mat("verdigris")
OLD_COPPER = P.mat("old_copper")
SUN = [P.mat("glow", kind="flat", base=i, bevel=0) for i in range(len(P.RAMPS["glow"]))]   # dark..light

# --- where it hangs (all from the skeleton) -----------------------------------------------------
CX, CZ = S.ORRERY_CENTRE                 # (11.5, 0.5)
R = S.ORRERY_R                           # 2.5
HANG_Y = S.ORRERY_HANG_Y                 # 14.0
RING_Y = S.ORRERY_RING_Y                 # 8.5
FLOOR_Y = S.ORRERY_BODY_Y[0]             # 8.0: nothing the machine draws goes below this

HUB_DROP = 0.95                          # the hub hangs this far below the ceiling
STEM_TOP = HANG_Y - HUB_DROP - RING_Y    # blocks from the ring plane up to where the stem meets the hub

SUN_R = 0.34                             # the sun's radius (a small warm core, not a dazzling globe)
SUN_LIGHT = 10                           # the one warm source build() offers A2 (kept low; A2 aligns)

# planets, inner to outer: (name, orbit radius, planet radius, material, banded, ringed). The colours
# set them apart with the palette's cast iron / brass / verdigris / old copper, and the sizes grow
# outward (Mars, like the real one, a touch smaller than Earth); Saturn carries its ring, Jupiter
# its band, so the six read as six worlds.  All radii keep the far edge inside R = 2.5.
PLANETS = [
    ("mercury", 0.72, 0.14, IRON_D, False, False),
    ("venus", 0.98, 0.17, BRASS, False, False),
    ("earth", 1.24, 0.20, VERDIGRIS, False, False),
    ("mars", 1.48, 0.16, OLD_COPPER, False, False),
    ("jupiter", 1.72, 0.30, BRASS_D, True, False),
    ("saturn", 1.95, 0.22, BRASS, False, True),
]
# the still pose: scattered orbital angles so the planets do not line up (a snapshot of the orbits)
POSE = (18.0, 84.0, 152.0, 212.0, 288.0, 338.0)
# version b lifts each arm by this, inner low to outer high, into a shallow bowl
BOWL = (0.0, 0.14, 0.30, 0.48, 0.68, 0.90)
# A8's to settle: a slow rate per planet, inner fastest, all gentle (degrees per in-game minute, say)
SPIN = {"mercury": 1.00, "venus": 0.62, "earth": 0.47, "mars": 0.38, "jupiter": 0.17, "saturn": 0.11}

CAGE = 2.35                              # version b: the brass meridian cage radius (inside R)

SCALE = {}                              # model name -> the scale it is shown at (its px matches it)


# --- the combined pieces (gear, graduated circle): written here, imported by other machines -------
def gear(m, c, y0, y1, pitch_r, teeth, body, tooth=None, hub_r=0.0, hub_mat=None, hub_ext=0.0,
         body_sides=12):
    """A spur gear about the vertical axis through c = (x, z), from y0 to y1 (model units), with
    `teeth` teeth round a pitch radius `pitch_r`. A gear belongs where there is real drive (plan 2);
    the teeth are boxes straddling the pitch circle so they read as teeth close up. hub_r > 0 adds a
    boss on the shaft, hub_ext long past each face."""
    cx, cz = c
    tooth = tooth or body
    ym = (y0 + y1) / 2.0
    depth = max(0.9, pitch_r * 0.18)
    tw = max(0.9, 2.0 * math.pi * pitch_r / teeth * 0.52)
    m.tube("y", c, y0, y1, pitch_r - depth * 0.5, body, sides=body_sides)
    for i in range(teeth):
        ang = 360.0 * i / teeth
        m.box((cx + pitch_r - depth - 0.1, y0 + 0.05, cz - tw / 2.0),
              (cx + pitch_r + depth * 0.5, y1 - 0.05, cz + tw / 2.0), tooth,
              rot=("y", ang, (cx, ym, cz)))
    if hub_r > 0.0:
        m.tube("y", c, y0 - hub_ext, y1 + hub_ext, hub_r, hub_mat or body, sides=8)
    return m


def grad_circle(m, axis, centre, radius, thick, width, body, ticks=0, tick_mat=None, tick_len=0.8,
                sides=32, arc=(0.0, 360.0)):
    """A graduated ring: a ring round `axis` (plan: the brass scale rings of the instruments), with
    `ticks` marks standing out from its rim. Shared with the telescope and meridian circles."""
    m.ring(axis, centre, radius, thick, width, body, sides=sides, arc=arc)
    if not ticks:
        return m
    k = M.AXES.index(axis)
    o1, o2 = [i for i in range(3) if i != k]
    tick_mat = tick_mat or body
    for i in range(ticks):
        ang = arc[0] + (arc[1] - arc[0]) * (i / ticks)
        lo, hi = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
        lo[k], hi[k] = centre[k] - width * 0.3, centre[k] + width * 0.3
        lo[o1], hi[o1] = centre[o1] + radius, centre[o1] + radius + tick_len
        lo[o2], hi[o2] = centre[o2] - 0.45, centre[o2] + 0.45
        m.box(tuple(lo), tuple(hi), tick_mat, rot=(axis, ang, tuple(centre)))
    return m


def _planet(m, c, r, mat, banded=False, ringed=False):
    """One planet: a ball of its material. A band (a proud belt of old copper) marks Jupiter; a
    tilted pair of brass rings marks Saturn, so each reads for what it is."""
    sides = 10 if r > 3.5 else 8
    m.ball(c, r, mat, sides=sides, layers=max(3, int(round(r / 1.3))))
    if banded:
        m.tube("y", (c[0], c[2]), c[1] - r * 0.22, c[1] + r * 0.22, r * 1.03, OLD_COPPER, sides=sides)
    if ringed:
        with m.turned(("z", 18.0), about=c):
            m.ring("y", c, r + 1.3, 0.9, 0.5, BRASS_D, sides=18)
            m.ring("y", c, r + 2.5, 0.7, 0.4, BRASS, sides=18)
    return m


# --- the shared models (both versions) ----------------------------------------------------------
def _hub():
    """The ceiling seat and the crown wheel it drives: brass canopy flush to the ceiling, four iron
    straps, the open crown wheel, the collar the stem turns in. Anchor: the hang point on the
    ceiling (interiors carries it); the model hangs down. Shown at scale 1."""
    u = 16.0
    m = M.Model(PREFIX + "hub", px=1.0)
    m.tube("y", (0, 0), -0.28 * u, -0.05 * u, 0.95 * u, BRASS_D, sides=16)     # canopy rim
    m.tube("y", (0, 0), -0.26 * u, 0.0, 0.80 * u, BRASS, sides=16)             # the boss on the ceiling
    for a in range(3):                                                         # three hangers, never four:
        m.box((0.52 * u, -0.64 * u, -0.07 * u), (0.80 * u, -0.08 * u, 0.07 * u), IRON,   # no cross from below
              rot=("y", 30.0 + 120.0 * a, (0, 0, 0)), grain="y")
    gear(m, (0, 0), -0.82 * u, -0.64 * u, 0.78 * u, 22, BRASS, tooth=BRASS_D,  # the crown wheel
         hub_r=0.17 * u, hub_mat=IRON_D, hub_ext=0.04 * u)
    m.tube("y", (0, 0), -0.98 * u, -0.82 * u, 0.24 * u, IRON_D, sides=12)      # the stem's bearing
    return m


def _sun():
    """The central sun: a small amber core. Only its own faces glow (emit, face kept small); the
    light it casts is an invisible source build() offers A2. Anchor: the centre. Shown at scale 1."""
    u = 16.0
    m = M.Model(PREFIX + "sun", px=1.0)
    r = SUN_R * u
    bands = [(-1.0, -0.45, 1, SUN[1]), (-0.45, 0.45, 1, SUN[3]), (0.45, 1.0, 1, SUN[1])]
    for t0, t1, layers, mat in bands:
        m.ball((0, 0, 0), r, mat, sides=10, layers=layers, part=(t0, t1),
               faces={"n": mat, "s": mat, "u": mat, "d": mat}, emit=15, shade=False)
    m.tube("y", (0, 0), r - 1.0, r + 1.6, 0.14 * u, BRASS, sides=8)            # the collar to the stem
    return m


# --- version a: planar, open gear train ---------------------------------------------------------
def _stem_a():
    """The hanging shaft and the open gear train that drives the flat system. Three crown wheels on
    the shaft and two idlers geared to them, teeth in the open (plan 2: gears where there is drive).
    Anchor: the centre, at the ring plane; the model rises to the hub. Shown at scale 2."""
    u = 8.0
    m = M.Model(PREFIX + "a_stem", px=2.0)
    top = STEM_TOP
    m.tube("y", (0, 0), 0.20 * u, 0.26 * u, 0.46 * u, BRASS_D, sides=12)       # boss over the arm clamps
    m.tube("y", (0, 0), 0.26 * u, 0.70 * u, 0.42 * u, BRASS, sides=12)
    m.tube("y", (0, 0), 0.55 * u, top * u, 0.13 * u, IRON, sides=8)            # the shaft
    gear(m, (0, 0), 0.92 * u, 1.14 * u, 0.52 * u, 18, BRASS, tooth=BRASS_D, hub_r=0.14 * u, hub_mat=IRON_D)
    gear(m, (0, 0), 1.36 * u, 1.56 * u, 0.40 * u, 14, BRASS_D, tooth=BRASS, hub_r=0.13 * u, hub_mat=IRON_D)
    gear(m, (0, 0), 1.80 * u, 1.98 * u, 0.30 * u, 12, BRASS, tooth=BRASS_D, hub_r=0.12 * u, hub_mat=IRON_D)
    for ang in (40.0, 220.0):
        ix, iz = math.cos(math.radians(ang)) * 0.60 * u, math.sin(math.radians(ang)) * 0.60 * u
        gear(m, (ix, iz), 1.02 * u, 1.46 * u, 0.26 * u, 10, BRASS_D, tooth=BRASS, hub_r=0.09 * u, hub_mat=IRON_D)
        m.rod((ix, 1.24 * u, iz), (0.0, 1.24 * u, 0.0), 0.05 * u, IRON_D)      # idler axle to the shaft
    m.tube("y", (0, 0), (top - 0.22) * u, top * u, 0.20 * u, BRASS_D, sides=12)
    return m


def _rings_a():
    """The flat concentric orbit tracks of the planar version, in the ring plane, with a graduated
    outer rim and three slim brass spiders. Anchor: the centre. Shown at scale 2."""
    u = 8.0
    m = M.Model(PREFIX + "a_rings", px=2.0)
    for r in (0.98, 1.48, 1.95):
        m.ring("y", (0, 0, 0), r * u, 0.08 * u, 0.09 * u, BRASS_D, sides=28)
    grad_circle(m, "y", (0, 0, 0), 2.18 * u, 0.12 * u, 0.13 * u, BRASS, ticks=24, tick_mat=BRASS_D,
                tick_len=0.55, sides=36)
    for ang in (30.0, 150.0, 270.0):
        dx, dz = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        m.rod((0.40 * u * dx, 0.0, 0.40 * u * dz), (2.18 * u * dx, 0.0, 2.18 * u * dz), 0.05 * u, BRASS_D)
    return m


# --- version b: tiered bowl under a cage of meridian rings (armillary) ---------------------------
def _stem_b():
    """The hanging shaft and a closed brass gear can -- the works are shut away, the ornament is the
    ring cage outside (plan: version b is the richer, armillary one). Anchor: the centre, at the
    ring plane. Shown at scale 2."""
    u = 8.0
    m = M.Model(PREFIX + "b_stem", px=2.0)
    top = STEM_TOP
    m.tube("y", (0, 0), 0.20 * u, 0.26 * u, 0.46 * u, BRASS_D, sides=12)
    m.tube("y", (0, 0), 0.26 * u, 0.74 * u, 0.42 * u, BRASS, sides=12)
    m.tube("y", (0, 0), 0.55 * u, top * u, 0.13 * u, IRON, sides=8)
    m.tube("y", (0, 0), 0.86 * u, 0.90 * u, 0.40 * u, BRASS_D, sides=12)       # the gear can
    m.tube("y", (0, 0), 0.90 * u, 1.74 * u, 0.36 * u, BRASS, sides=12)
    m.tube("y", (0, 0), 1.74 * u, 1.78 * u, 0.40 * u, BRASS_D, sides=12)
    gear(m, (0, 0), 1.78 * u, 1.96 * u, 0.30 * u, 12, BRASS, tooth=BRASS_D, hub_r=0.12 * u, hub_mat=IRON_D)
    m.tube("y", (0, 0), (top - 0.22) * u, top * u, 0.20 * u, BRASS_D, sides=12)
    return m


def _rings_b():
    """The brass cage: a graduated equator ring, a shallow tilted ecliptic ring, three upper meridian
    arcs that meet at the pole as six ribs (the lower halves left open, so nothing dips into the walk
    line), and the crown where they meet. Anchor: the centre. Shown at scale 2."""
    u = 8.0
    m = M.Model(PREFIX + "b_rings", px=2.0)
    grad_circle(m, "y", (0, 0, 0), CAGE * u, 0.12 * u, 0.16 * u, BRASS, ticks=24, tick_mat=BRASS_D,
                tick_len=0.55, sides=36)
    with m.turned(("x", 12.0), about=(0, 0, 0)):                               # the ecliptic ring
        m.ring("y", (0, 0, 0), 1.85 * u, 0.10 * u, 0.11 * u, BRASS_D, sides=32)
    for yaw in (0.0, 60.0, 120.0):                                             # three upper meridian arcs: six ribs
        #                                                                        (two would cross at the pole)
        with m.turned(("y", yaw), about=(0, 0, 0)):
            m.ring("x", (0, 0, 0), CAGE * u, 0.12 * u, 0.16 * u, BRASS, sides=36, arc=(-90.0, 90.0))
    m.tube("y", (0, 0), (CAGE - 0.14) * u, (CAGE + 0.10) * u, 0.20 * u, BRASS_D, sides=10)   # the crown
    return m


def _arm(version, key, orbit, prad, pmat, banded, ringed, rise):
    """One planet arm: a clamp collar at the axis, a slender brass bar, the planet at its end. The
    anchor is the axis; the beam runs out along +x (and up by `rise` in version b). Shown at scale 1."""
    u = 16.0
    m = M.Model(PREFIX + version + "_arm_" + key, px=1.0)
    end = (orbit * u, rise * u, 0.0)
    m.tube("y", (0, 0), -0.22 * u, 0.22 * u, 0.15 * u, BRASS_D, sides=8)       # the clamp on the hub
    m.box((-0.11 * u, -0.07 * u, -0.10 * u), (0.12 * u, 0.07 * u, 0.10 * u), BRASS)
    m.beam((0.0, 0.0, 0.0), end, 0.18 * u, 0.13 * u, BRASS)                    # the arm
    m.tube("y", (end[0], end[2]), end[1] - 0.14 * u, end[1] + 0.14 * u, 0.09 * u, BRASS_D, sides=6)  # the planet's seat
    _planet(m, end, prad * u, pmat, banded=banded, ringed=ringed)
    return m


# --- the model set -------------------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def _models():
    out = {}
    for name, model, scale in [("hub", _hub(), 1.0), ("sun", _sun(), 1.0),
                               ("a_stem", _stem_a(), 2.0), ("a_rings", _rings_a(), 2.0),
                               ("b_stem", _stem_b(), 2.0), ("b_rings", _rings_b(), 2.0)]:
        out[model.name] = model
        SCALE[model.name] = scale
    for version in ("a", "b"):
        for (key, orbit, prad, pmat, banded, ringed), rise in zip(PLANETS, BOWL):
            model = _arm(version, key, orbit, prad, pmat, banded, ringed, rise if version == "b" else 0.0)
            out[model.name] = model
            SCALE[model.name] = 1.0
    return out


def models():
    return dict(_models())


# --- placing -------------------------------------------------------------------------------------
def _place(canvas, name, pos, origin=(0, 0, 0), yaw=0.0, **opts):
    built = _models()
    x, y, z = (pos[i] + origin[i] for i in range(3))
    canvas.add_entity(x, y, z, M.display(built[name], yaw=yaw, scale=SCALE[name], **opts))
    return 1


def build(canvas, origin=(0, 0, 0), version=VERSION):
    """Hang one orrery in the star hall and return the number of display entities. version "a" is
    planar, "b" the armillary bowl; the test scene builds both side by side, the review picks one."""
    v = version
    n = _place(canvas, PREFIX + "hub", (CX, HANG_Y - K.NUDGE, CZ), origin)   # in the air cell under the ceiling
    n += _place(canvas, PREFIX + "sun", (CX, RING_Y, CZ), origin)
    n += _place(canvas, PREFIX + v + "_stem", (CX, RING_Y, CZ), origin)
    for (key, *_rest), yaw in zip(PLANETS, POSE):
        n += _place(canvas, PREFIX + v + "_arm_" + key, (CX, RING_Y, CZ), origin, yaw=yaw)
    n += _place(canvas, PREFIX + v + "_rings", (CX, RING_Y, CZ), origin)
    cell = (int(CX + origin[0]), int(RING_Y + origin[1]), int(CZ + origin[2]))
    K.offer_lights(canvas, [(cell, SUN_LIGHT)], f"machines/orrery:{v}")
    return n


def models_for(version):
    """The names build() places for one version, for a gallery or a count."""
    base = [PREFIX + "hub", PREFIX + "sun", PREFIX + version + "_stem", PREFIX + version + "_rings"]
    return base + [PREFIX + version + "_arm_" + p[0] for p in PLANETS]
