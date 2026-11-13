"""props/ironwork -- the door and window ironwork of the observatory (plan ART-PLAN 7.3, part A6,
card plan/packages/props/ironwork.md).

Nine pieces, all cast iron, all on the common palette, 16 texels to the block (px = scale):

    window_arch_a / _b   the great arched window's iron frame, two versions to compare. Iron only:
                         it is pressed on A1's glazed pane and its painted 8 px muntins show through,
                         so the frame starts no grid of its own -- jambs, a springing transom and the
                         arch head. a: a plain frame under a full semicircular head. b: a heavier
                         riveted frame under a flatter segmental head, the crown left open for A3's
                         stone keystone.
    window_grille        the base-storey small window's barred grille (frame + uprights + a mid rail).
    fanlight             the half-round fanlight over the door: a radiating iron fan and amber glass.
    door_leaf            one leaf of the entrance door: a riveted plate with a glazed porthole; two
                         are hung open so a player walks through (door()).
    canopy               the glazed entrance canopy on two brackets; its underside is left flat for
                         lamps.festoon to hang the bare bulbs (c179 #15697).
    railing_panel        a cast scroll panel for the terrace balustrade, between two posts.
    ladder               an inspection ladder with side rails, rungs and safety hoops.
    vent_cowl            a roof vent: a flanged pipe under a flared cowl.
    grate_hatch          a floor grating / louvre hatch with a ring pull.

Everything is placed through _kit (mounting, materials, rivets, glowing glass). The arch_frame /
grille / louvre helpers live here (c179 #15697: kept in this module until a second family needs one).

The look is judged on texture and on style, so the test scene is build/scenes/obs_props_ironwork.
"""
import functools
import math

from artkit import models as M

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from . import _kit as K

PREFIX = "prop_iron_"
VERSION = "a"                    # the default arch frame; the review picks one and only this changes

IRON, IRON_D = K.IRON, K.IRON_D
BRASS, BRASS_D = K.BRASS, K.BRASS_D
COPPER = K.COPPER
RIVET = K.RIVET
GLASS_HOT, GLASS_MID, GLASS_DIM = K.GLOW_HOT, K.GLOW_MID, K.GLOW_DIM     # amber glass that glows
GLASS_COOL = K.flat("opal", 3)                                          # frosted canopy glass, not lit


# ---- shared ironwork helpers (c179 #15697: these stay in ironwork.py) ------------------------------
def _rivet_line(m, a, b, n, out="z", mat=RIVET):
    """n rivet heads evenly from point a to point b (both ends), on a face that looks `out`."""
    for i in range(n):
        t = i / (n - 1) if n > 1 else 0.5
        K.rivet(m, tuple(a[k] + (b[k] - a[k]) * t for k in range(3)), out=out, mat=mat)


def arch_frame(m, half_w, spring, rise, thick, mat, *, depth=(0.0, 2.5), keystone_gap=0.0,
               sides=24, rivets=0, rivet_mat=RIVET):
    """An arch band in the model's x-y plane (z out of the wall), about x = 0. Its soffit passes
    through (+-half_w, spring) and the crown (0, spring + rise); rise = half_w is a semicircle, a
    smaller rise a segmental (flatter) arch. thick is the band's radial size, depth its size out of
    the wall. keystone_gap (degrees) leaves the crown open for A3's stone keystone. Returns the soffit
    radius and the y of the arc's centre, so a caller can line a transom or spandrel up with it."""
    r_soffit = (rise * rise + half_w * half_w) / (2.0 * rise)
    yc = spring + rise - r_soffit
    r_mid = r_soffit + thick / 2.0
    a0 = math.degrees(math.atan2(spring - yc, half_w))
    a1 = 180.0 - a0
    cz, width = (depth[0] + depth[1]) / 2.0, depth[1] - depth[0]
    arcs = [(a0, a1)] if keystone_gap <= 0.0 else [(a0, 90.0 - keystone_gap / 2.0),
                                                   (90.0 + keystone_gap / 2.0, a1)]
    for lo, hi in arcs:
        m.ring("z", (0.0, yc, cz), r_mid, thick, width, mat, sides=sides, arc=(lo, hi))
    for i in range(rivets):
        ang = a0 + (a1 - a0) * (i + 0.5) / rivets
        if keystone_gap > 0.0 and abs(ang - 90.0) < keystone_gap / 2.0:
            continue
        r = math.radians(ang)
        K.rivet(m, (r_mid * math.cos(r), yc + r_mid * math.sin(r), depth[1]), out="z", mat=rivet_mat)
    return r_soffit, yc


def grille(m, w, h, depth, mat, *, frame=1.5, pitch=4.0, bars="v", mid=False):
    """A barred grille filling w x h from the foot centre (x in [-w/2, w/2], y in [0, h]), in the
    x-y plane, `depth` out of the wall. A box frame, round uprights (bars='v') or rungs ('h') at
    about `pitch`, and an optional mid rail across the middle."""
    hw = w / 2.0
    m.box((-hw, 0.0, 0.0), (hw, frame, depth), mat, grain="x")
    m.box((-hw, h - frame, 0.0), (hw, h, depth), mat, grain="x")
    m.box((-hw, 0.0, 0.0), (-hw + frame, h, depth), mat, grain="y")
    m.box((hw - frame, 0.0, 0.0), (hw, h, depth), mat, grain="y")
    zc = depth / 2.0
    if mid:
        m.box((-hw, h / 2.0 - frame / 2.0, 0.0), (hw, h / 2.0 + frame / 2.0, depth), mat, grain="x")
    if bars == "v":
        n = max(1, int(round(w / pitch)) - 1)
        for i in range(n):
            x = -hw + w * (i + 1) / (n + 1)
            m.tube("y", (x, zc), frame, h - frame, 0.7, mat, sides=8)
    else:
        n = max(1, int(round(h / pitch)) - 1)
        for i in range(n):
            y = h * (i + 1) / (n + 1)
            m.tube("x", (y, zc), -hw + frame, hw - frame, 0.7, mat, sides=8)


def louvre(m, w, h, depth, n, mat, *, frame=1.5, tilt=32.0):
    """n fixed slats slanted `tilt` degrees, inside a box frame, filling w x h from the foot centre."""
    hw = w / 2.0
    m.box((-hw, 0.0, 0.0), (-hw + frame, h, depth), mat, grain="y")
    m.box((hw - frame, 0.0, 0.0), (hw, h, depth), mat, grain="y")
    inner = h - frame
    for i in range(n):
        y = frame + inner * (i + 0.5) / n
        m.box((-hw + frame, y - 0.8, -depth), (hw - frame, y + 0.8, depth), mat,
              rot=("x", tilt, (0.0, y, depth / 2.0)), grain="x")


# ---- the great arched window frame (two versions) -------------------------------------------------
def _window_arch(version, width=3):
    """Iron frame for a `width`-block, six-block arched window, at scale 2 (anchor: the foot centre
    of the opening, on the wall). A1 draws the glass and its muntins behind it."""
    heavy = version == "b"
    m = M.Model(PREFIX + "window_arch_" + version, px=2.0)
    ohw = width * 4.0                       # opening half-width in units (8 units = 1 block at px 2)
    dz = 2.5
    jamb = 3.0 if heavy else 2.0
    thick = 3.0 if heavy else 2.0
    spring = 36.0 if heavy else 32.0        # the segmental head is flatter, so its jambs run higher
    rise = 7.0 if heavy else ohw            # rise = ohw is a full semicircle; both crowns clear 48 u
    gap = 24.0 if heavy else 0.0
    xo = ohw + jamb / 2.0                   # the frame straddles the opening edge
    m.box((-xo, 0.0, 0.0), (-ohw + jamb / 2.0, spring, dz), IRON, grain="y")
    m.box((ohw - jamb / 2.0, 0.0, 0.0), (xo, spring, dz), IRON, grain="y")
    m.box((-xo, 0.0, 0.0), (xo, 2.0, dz), IRON, grain="x")                        # bottom rail
    m.box((-xo, spring - 1.0, 0.0), (xo, spring + 1.0, dz), IRON_D, grain="x")    # springing transom
    arch_frame(m, ohw, spring, rise, thick, IRON, depth=(0.0, dz), keystone_gap=gap,
               rivets=9 if heavy else 0)
    if heavy:
        for sx in (-1.0, 1.0):
            _rivet_line(m, (sx * ohw, 3.0, dz), (sx * ohw, spring - 3.0, dz), 5)
        _rivet_line(m, (-ohw, spring, dz), (ohw, spring, dz), 5)
    else:
        for sx in (-1.0, 1.0):
            K.rivet(m, (sx * ohw, 2.0, dz))
            K.rivet(m, (sx * ohw, spring - 1.0, dz))
    return m


# ---- the base-storey grille -----------------------------------------------------------------------
def _window_grille(width=3):
    """A barred grille for a `width` x 2 base-storey window, at scale 1 (anchor: the foot centre on
    the wall)."""
    m = M.Model(PREFIX + "window_grille", px=1.0)
    grille(m, width * 16.0, 32.0, 2.0, IRON, frame=2.0, pitch=4.0, bars="v", mid=True)
    for sx in (-1.0, 1.0):
        x = sx * (width * 8.0 - 1.5)
        K.rivet(m, (x, 2.0, 2.0))
        K.rivet(m, (x, 30.0, 2.0))
    return m


# ---- the fanlight over the door -------------------------------------------------------------------
def _fanlight(width=3):
    """A half-round fanlight: a radiating iron fan and amber glass, at scale 1 (anchor: the foot
    centre on the wall; the glass glows -- the only lit piece of the family)."""
    m = M.Model(PREFIX + "fanlight", px=1.0)
    hw = width * 8.0 - 2.0              # keeps the rim inside the 48-unit limit at scale 1
    rim, bars = 2.0, 6
    R = hw - 2.0                        # rim radius; the glass sits inside it
    base, rg = rim, hw - 2.0 * rim      # the springing line and the glass radius
    layers = 8
    for i in range(layers):            # amber glass as a stack of chords: a filled half-disc, glowing
        y0 = rg * i / layers
        cw = math.sqrt(max(0.0, rg * rg - y0 * y0))
        if cw < 0.5:
            continue
        m.box((-cw, base + y0, 0.0), (cw, base + rg * (i + 1) / layers, 0.6), GLASS_MID,
              emit=15, shade=False, grain="x")
    m.box((-hw, 0.0, 0.0), (hw, base, 1.0), IRON, grain="x")                      # springing bar
    arch_frame(m, R, base, R, rim, IRON, depth=(0.0, 1.0), sides=28)              # the semicircular rim
    for i in range(1, bars):                                                      # radiating muntins
        ang = math.radians(180.0 * i / bars)
        m.rod((0.0, base, 0.8), (rg * math.cos(ang), base + rg * math.sin(ang), 0.8), 0.6, IRON_D)
    K.rivet(m, (0.0, base + 1.0, 1.0))
    return m


# ---- the entrance door leaf -----------------------------------------------------------------------
def _door_leaf(width=1.5, height=5):
    """One riveted leaf with a glazed porthole, at scale 2 (anchor: the foot of the hinge edge; the
    leaf runs +x to the free edge and +z out). Riveted and glazed through, so a leaf reads the same
    hung from either jamb."""
    m = M.Model(PREFIX + "door_leaf", px=2.0)
    w, h, dz = width * 8.0, height * 8.0, 2.5
    m.box((0.0, 0.0, 0.0), (w, h, dz), IRON, grain="y")
    for y in (h * 0.36, h * 0.64):                                               # two ledge bands
        m.box((0.6, y - 0.8, 0.0), (w - 0.6, y + 0.8, dz + 0.4), IRON_D, grain="x")
    for z, out in ((dz, "z"), (0.0, "-z")):                                      # riveted both faces
        _rivet_line(m, (1.2, 1.5, z), (w - 1.2, 1.5, z), 4, out=out)
        _rivet_line(m, (1.2, h - 1.5, z), (w - 1.2, h - 1.5, z), 4, out=out)
        _rivet_line(m, (1.2, 1.5, z), (1.2, h - 1.5, z), 6, out=out)
        _rivet_line(m, (w - 1.2, 1.5, z), (w - 1.2, h - 1.5, z), 6, out=out)
    cx, cy, r = w / 2.0, h * 0.68, 3.4
    m.ring("z", (cx, cy, dz / 2.0), r, 1.2, dz + 0.6, BRASS, sides=16)            # porthole rim
    K.glass_prism(m, "z", (cx, cy), -0.3, dz + 0.3, r - 0.9, GLASS_MID, cap=GLASS_DIM, emit=15)
    m.tube("y", (0.4, dz / 2.0), -1.0, h + 1.0, 1.0, IRON_D, sides=8)            # hinge barrel
    for y in (h * 0.2, h * 0.8):                                                 # strap hinges
        m.box((0.0, y - 1.0, dz), (w * 0.45, y + 1.0, dz + 0.5), IRON_D, grain="x")
    m.box((w - 2.5, cy - 4.0, dz), (w - 1.5, cy + 4.0, dz + 1.2), BRASS_D)       # a pull by the edge
    return m


# ---- the glazed entrance canopy -------------------------------------------------------------------
def _canopy(width=5, depth=3):
    """A glazed canopy on two brackets, at scale 2 (anchor: the fixing on the wall, its foot centre).
    The underside middle is kept clear so lamps.festoon can hang the bare bulbs under it."""
    m = M.Model(PREFIX + "canopy", px=2.0)
    hw, out = width * 4.0, depth * 8.0
    m.box((-hw, 4.0, 0.0), (hw, 7.0, 2.5), IRON, grain="x")                       # fixing / back beam
    for sx in (-1.0, 1.0):
        x = sx * (hw - 2.0)
        m.beam((x, -6.0, 2.0), (x, 3.0, out - 2.0), 2.0, 3.0, IRON)              # bracket
        m.rod((x, 6.5, 2.0), (x, 4.0, out - 2.0), 0.8, IRON_D)                   # tie rod
    m.box((-hw, 5.0, 2.0), (hw, 5.8, out - 1.0), GLASS_COOL, rot=("x", -9.0, (0.0, 5.4, 2.0)),
          grain="z")                                                             # glass roof, sloped
    m.box((-hw, 2.0, out - 2.5), (hw, 4.5, out), IRON, grain="x")                # riveted front beam
    _rivet_line(m, (-hw + 3.0, 3.2, out), (hw - 3.0, 3.2, out), 7, out="z")
    return m


# ---- the terrace balustrade scroll panel ----------------------------------------------------------
def _railing_panel(width=2, height=1):
    """A cast scroll panel between two posts, at scale 1 (anchor: the foot centre, it stands on the
    floor)."""
    m = M.Model(PREFIX + "railing_panel", px=1.0)
    w, h, dz = width * 16.0, height * 16.0, 2.0
    hw = w / 2.0
    for sx in (-1.0, 1.0):                                                        # posts
        m.box((sx * hw - 1.5, 0.0, 0.0), (sx * hw + 1.5, h, dz), IRON, grain="y")
    m.box((-hw, h - 2.0, 0.0), (hw, h, dz), IRON, grain="x")                      # top rail
    m.box((-hw, 0.0, 0.0), (hw, 2.0, dz), IRON, grain="x")                        # bottom rail
    zc = dz / 2.0
    for sx in (-1.0, 1.0):                                                        # a pair of C-scrolls
        cx = sx * hw * 0.5
        m.ring("z", (cx, h * 0.5, zc), h * 0.28, 1.2, dz, IRON_D, sides=16, arc=(200.0, 520.0))
        m.ring("z", (sx * hw * 0.25, h * 0.42, zc), h * 0.14, 1.0, dz, IRON_D, sides=12, arc=(0.0, 300.0))
    K.rivet(m, (0.0, 2.0, dz))
    K.rivet(m, (0.0, h - 2.0, dz))
    return m


# ---- the inspection ladder ------------------------------------------------------------------------
def _ladder(width=0.5, height=3):
    """Side rails, rungs and three safety hoops, at scale 1 (anchor: the foot centre on the wall;
    the ladder stands off the wall on +z)."""
    m = M.Model(PREFIX + "ladder", px=1.0)
    h = height * 16.0
    rail, stand = width * 16.0 / 2.0, 4.0
    for sx in (-1.0, 1.0):
        m.box((sx * rail - 1.0, 0.0, stand - 1.0), (sx * rail + 1.0, h, stand + 1.0), IRON, grain="y")
    for i in range(int(h // 8)):
        y = 6.0 + 8.0 * i
        m.tube("x", (y, stand), -rail, rail, 0.8, IRON_D, sides=8)               # rung
    for y in (h * 0.4, h * 0.65, h * 0.9):                                       # safety hoops, gap at the wall
        m.ring("y", (0.0, y, stand + 1.0), 5.0, 1.0, 1.2, IRON, sides=16, arc=(300.0, 600.0))
    return m


# ---- the roof vent cowl ---------------------------------------------------------------------------
def _vent_cowl(width=1, height=1.5):
    """A flanged pipe under a flared cowl, at scale 1 (anchor: the foot centre, it stands on the
    roof)."""
    m = M.Model(PREFIX + "vent_cowl", px=1.0)
    h = height * 16.0
    r = width * 16.0 / 2.0 - 2.0
    m.tube("y", (0.0, 0.0), 0.0, 1.5, r + 1.5, IRON, sides=12)                   # base flange
    m.tube("y", (0.0, 0.0), 1.5, h - 7.0, r, IRON, sides=12)                     # pipe
    m.ring("y", (0.0, h - 6.5, 0.0), r + 0.5, 1.0, 1.0, IRON_D, sides=12)        # collar
    m.taper("y", (0.0, 0.0), h - 6.0, h - 1.0, r - 0.5, r + 2.0, IRON, sides=12)  # flared cowl
    m.tube("y", (0.0, 0.0), h - 1.0, h, r + 2.0, IRON_D, sides=12, cap=IRON_D)    # cap lip
    return m


# ---- the floor grating / louvre hatch -------------------------------------------------------------
def _grate_hatch(width=1):
    """A square floor grating with a ring pull, at scale 1 (anchor: the foot centre, it lies flat on
    the floor)."""
    m = M.Model(PREFIX + "grate_hatch", px=1.0)
    s = width * 16.0 / 2.0
    for sx in (-1.0, 1.0):
        m.box((sx * s - 1.5, 0.0, -s), (sx * s + 1.5, 2.0, s), IRON, grain="z")
        m.box((-s, 0.0, sx * s - 1.5), (s, 2.0, sx * s + 1.5), IRON, grain="x")
    for i in range(int(2 * s // 3) - 1):                                         # grating bars
        z = -s + 3.0 * (i + 1)
        m.tube("x", (1.0, z), -s + 1.5, s - 1.5, 0.6, IRON_D, sides=6)
    m.box((-s, 0.0, -s + 0.5), (-s + 1.5, 1.0, -s + 2.5), IRON_D)                # a hinge
    m.ring("y", (s - 3.0, 1.5, 0.0), 2.0, 0.8, 0.8, BRASS, sides=12)            # ring pull
    return m


# ---- the family's models, placement and dressing --------------------------------------------------
SPEC = {
    "window_arch_a": dict(build=lambda: _window_arch("a"), mount="wall", scale=2.0, light=None),
    "window_arch_b": dict(build=lambda: _window_arch("b"), mount="wall", scale=2.0, light=None),
    "window_grille": dict(build=_window_grille, mount="wall", scale=1.0, light=None),
    "fanlight": dict(build=_fanlight, mount="wall", scale=1.0, light=(0.0, 0.6, 0.4), level=9),
    "door_leaf": dict(build=_door_leaf, mount="wall", scale=2.0, light=None),
    "canopy": dict(build=_canopy, mount="wall", scale=2.0, light=None),
    "railing_panel": dict(build=_railing_panel, mount="floor", scale=1.0, light=None),
    "ladder": dict(build=_ladder, mount="wall", scale=1.0, light=None),
    "vent_cowl": dict(build=_vent_cowl, mount="floor", scale=1.0, light=None),
    "grate_hatch": dict(build=_grate_hatch, mount="floor", scale=1.0, light=None),
}
SCALE = {PREFIX + name: spec["scale"] for name, spec in SPEC.items()}
VERSIONED = ("window_arch",)


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + name: spec["build"]() for name, spec in SPEC.items()}


def models():
    return dict(_models())


def _resolve(kind, version):
    """The SPEC key and model name for a kind, adding the version where a kind is versioned."""
    if kind in VERSIONED:
        kind = f"{kind}_{version or VERSION}"
    return kind


def place(canvas, kind, pos, facing="south", origin=(0, 0, 0), version=None, light=True,
          level=None, yaw=None, **opts):
    """Place one piece and, if it is a lit one, offer its light to A2. Returns the entity count."""
    key = _resolve(kind, version)
    spec = SPEC[key]
    n = K.put(canvas, _models()[PREFIX + key], pos, mount=spec["mount"], facing=facing, yaw=yaw,
              scale=spec["scale"], origin=origin, **opts)
    if light and spec.get("light") is not None:
        y = yaw if yaw is not None else K.FACING[facing]
        cell = K.light_cell(pos, y, spec["light"], origin)
        K.offer_lights(canvas, [(cell, level if level is not None else spec.get("level", 9))],
                       f"props/ironwork:{key}")
    return n


def door(canvas, pos, facing="east", origin=(0, 0, 0)):
    """Both leaves of the entrance door, hung open flat against the facade so the opening stays clear
    (the door is kept open, a player walks through). pos is the foot centre of the three-wide opening
    on the wall. Returns the entity count."""
    leaf = _models()[PREFIX + "door_leaf"]
    base = K.FACING[facing]
    tan = K.turn(base, (1.0, 0.0, 0.0))             # along the wall, where a leaf's +x runs at `base`
    out = K.turn(base, (0.0, 0.0, K.NUDGE))         # a hair off the wall
    half = 1.5                                      # half the three-wide opening, in blocks
    n = 0
    for mult, dyaw in ((1.0, 0.0), (-1.0, 180.0)):  # one leaf at each jamb, swung flat and apart
        hinge = tuple(pos[k] + mult * half * tan[k] + out[k] + origin[k] for k in range(3))
        canvas.add_entity(hinge[0], hinge[1], hinge[2],
                          M.display(leaf, yaw=base + dyaw, scale=SPEC["door_leaf"]["scale"]))
        n += 1
    return n


def entrance(canvas, pos, facing="east", origin=(0, 0, 0), version=None):
    """The whole entrance dressing: the open door, the fanlight above it and the glazed canopy over
    that. pos is the foot centre of the door opening on the wall. lamps.build hangs the festoon and
    the door-side wall lamps. Returns the entity count."""
    n = door(canvas, pos, facing=facing, origin=origin)
    above = (pos[0], pos[1] + 5.0, pos[2])
    n += place(canvas, "fanlight", above, facing=facing, origin=origin, version=version)
    n += place(canvas, "canopy", (pos[0], pos[1] + 7.0, pos[2]), facing=facing, origin=origin)
    return n


def _windows():
    """A3's window table when it is in the tree, else None (props dress a wall that already exists)."""
    try:
        from ..main import _plan
    except ImportError:
        return None
    return getattr(_plan, "windows", lambda: [])()


def build(canvas, origin=(0, 0, 0), version=VERSION):
    """Dress the front A3 has built: an arch frame on every main-storey window, a grille on every
    base-storey one, and the entrance at the east middle bay. Places nothing until A3's wall and its
    window table are in the tree, so the master scene always generates."""
    n = 0
    table = _windows()
    if table is not None:
        for w in table:
            if w["front"] not in ("east", "west"):
                continue        # north/south end walls and the drum are dressed by their own cards
            xs = [c[0] for c in w["cells"]]
            zs = [c[1] for c in w["cells"]]
            y0 = w["y"][0]
            cz = (min(zs) + max(zs)) / 2.0
            # the frame sits on the wall face, one block out from the recessed glass column
            wall_x = (max(xs) + 1) if w["front"] == "east" else (min(xs) - 1)
            pos = (wall_x, float(y0), cz)
            if w["storey"] == "main":        # the two-wide end-pavilion windows get a narrow variant
                n += place(canvas, "window_arch", pos, facing=w["front"], origin=origin, version=version)
            elif w["storey"] == "base":
                n += place(canvas, "window_grille", pos, facing=w["front"], origin=origin)
        return n
    # fall back to the locked skeleton: only where A3's east front already stands
    for bay in range(1, S.N_BAYS + 1):
        cz = S.bay_center_z(bay)
        x = K.east_face(canvas, S.WINDOW[0], cz, S.WALL_E - 1, S.east_wall_x(bay) + 1, origin)
        if x is not None and bay != 9:
            n += place(canvas, "window_arch", (x, float(S.WINDOW[0]), cz), facing="east",
                       origin=origin, version=version)
        x = K.east_face(canvas, S.BASE[0] + 1, cz, S.WALL_E - 1, S.east_wall_x(bay) + 1, origin)
        if x is not None:
            n += place(canvas, "window_grille", (x, float(S.BASE[0] + 1), cz), facing="east",
                       origin=origin)
    x = K.east_face(canvas, S.GROUND, S.bay_center_z(9), S.WALL_E - 1, S.east_wall_x(9) + 1, origin)
    if x is not None:
        n += entrance(canvas, (x, float(S.GROUND), S.bay_center_z(9)), facing="east",
                      origin=origin, version=version)
    return n
