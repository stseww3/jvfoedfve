"""The lamp family (plan ART-PLAN 7.3; parts/A6-props.md 2.1; card packages/props/lamps.md).

One vocabulary for every lamp: a cast-iron stand or bracket, a glass shade, a brass holder. The
light is filament amber; only the green desk lamp glows green. A lamp model only glows itself: the
light it throws is an invisible light block, offered to A2's tool by the placing functions.

Two versions of the shade-and-bracket motif are kept side by side until the review picks one:
  A  classical   opal globe, quadrant brace with a ring in the spandrel
  B  industrial  enamel cone shade with a bare bulb, square arm with a strut, riveted plates
The bracket, the caged wall lamp and the pendant exist in both; the other lamps are shared.

For the other lines:

    from scenes.obs.props import lamps
    n += lamps.place(canvas, "bracket", (x, y, z), facing="east", origin=origin)   # on a wall face
    n += lamps.place(canvas, "street", (x, y, z), origin=origin)                   # foot centre
    n += lamps.place(canvas, "pendant", (x, y, z), origin=origin)                  # hanging point
    n += lamps.festoon(canvas, a, b, origin=origin)                                # cable and bulbs

Both return the number of display entities they placed.
"""
import functools
import math

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import palette as P
from ..common import skeleton as S
from . import _kit as K

PREFIX = "prop_lamp_"
VERSION = "a"           # the version that "bracket", "cage" and "pendant" stand for until the review

IRON, IRON_D, BRASS, BRASS_D, COPPER, ENAMEL = K.IRON, K.IRON_D, K.BRASS, K.BRASS_D, K.COPPER, K.ENAMEL
OPAL = [K.flat("opal", i) for i in range(len(P.RAMPS["opal"]))]          # dark to light
GLOW = [K.flat("glow", i) for i in range(len(P.RAMPS["glow"]))]
RED = [K.flat("signal_glow", i) for i in range(len(P.RAMPS["signal"]))]
RIVET = K.flat("iron", 5)
RIM = K.flat("cream", 2)
CABLE = K.flat("old_copper", 1)
GREEN = P.mat("phosphor", kind="plain", noise=0.10, bevel=1, base=1)     # cased green glass
GREEN_LIT = K.flat("phosphor", 3)

# the glass of the box lamp, seen from the front: the bulb behind it is the bright spot
_g = P.RAMPS["glow"]
BULB_FACE = Sprite("lamp_bulb_face",
                   ["aaaa", "abba", "abba", "bccb", "bccb", "abba", "abba", "aaaa"],
                   {"a": _g[1], "b": _g[2], "c": _g[3]})


def _opal_globe(m, centre, radius, sides=8, squash=1.0, fine=False):
    """An opal glass globe lit from within. The hot belt round the middle is under a third of what
    is seen of it; towards the poles the glass goes darker step by step, the lower half a step
    more than the upper."""
    if fine:
        bands = [(-1.0, -0.75, 1, OPAL[0]), (-0.75, -0.5, 1, OPAL[1]), (-0.5, -0.25, 1, OPAL[2]),
                 (-0.25, 0.25, 1, OPAL[4]),
                 (0.25, 0.5, 1, OPAL[3]), (0.5, 0.75, 1, OPAL[2]), (0.75, 1.0, 1, OPAL[1])]
    else:
        bands = [(-1.0, -0.65, 1, OPAL[0]), (-0.65, -0.25, 1, OPAL[2]),
                 (-0.25, 0.25, 1, OPAL[4]),
                 (0.25, 0.65, 1, OPAL[3]), (0.65, 1.0, 1, OPAL[1])]
    return K.glass_ball(m, centre, radius, bands, sides=sides, squash=squash)


def _cone_shade(m, c, top, bottom, r_top, r_bottom, steps):
    """An enamel cone shade about the vertical line c = (x, z): blue outside, a pale rolled rim,
    and the white inside lit by the bulb. Returns the y of the underside."""
    m.taper("y", c, top, bottom, r_top, r_bottom, ENAMEL, steps=steps)
    m.tube("y", c, bottom - 1.0, bottom, r_bottom, RIM)
    K.glass_prism(m, "y", c, bottom - 1.1, bottom - 1.0, r_bottom - 0.75, OPAL[1])
    K.glass_prism(m, "y", c, bottom - 1.2, bottom - 1.1, r_bottom * 0.5, OPAL[3])
    return bottom - 1.0


def _rose(m):
    """The ceiling rose every pendant hangs from. Anchor: the hanging point."""
    m.tube("y", (0, 0), -1.0, 0.0, 2.5, BRASS_D)
    m.tube("y", (0, 0), -2.0, -1.0, 1.5, BRASS)


# ---- the models --------------------------------------------------------------------------------------
def _street():
    """Cast-iron street lamp with an opal globe, five blocks tall. It is shown at scale 2, so the
    units here are eighths of a block and px=2 keeps 16 texels to the block. Anchor: foot centre."""
    m = M.Model(PREFIX + "street", px=2.0)
    m.tube("y", (0, 0), 0.0, 1.5, 3.0, IRON_D)                          # plinth
    m.taper("y", (0, 0), 1.5, 6.0, 2.5, 1.25, IRON, steps=3)            # swelling foot
    m.tube("y", (0, 0), 6.0, 7.0, 1.75, IRON_D)
    m.tube("y", (0, 0), 7.0, 29.0, 0.75, IRON)                          # shaft
    m.tube("y", (0, 0), 17.0, 18.0, 1.25, IRON_D)
    m.box((-3.5, 26.5, -0.25), (3.5, 27.0, 0.25), IRON, grain="x")      # the ladder bar
    for x in (-3.5, 3.5):
        m.box((x - 0.5, 26.25, -0.5), (x + 0.5, 27.25, 0.5), IRON_D)
    m.taper("y", (0, 0), 29.0, 31.0, 1.0, 2.0, IRON, steps=2)           # capital
    m.tube("y", (0, 0), 31.0, 31.75, 2.5, BRASS)                        # gallery
    _opal_globe(m, (0, 35.0, 0), 3.5, sides=12, fine=True)
    m.tube("y", (0, 0), 38.25, 39.0, 1.5, IRON_D)
    m.box((-0.5, 39.0, -0.5), (0.5, 40.5, 0.5), BRASS)                  # finial
    return m


def _bracket_a():
    """Version A wall lamp: an upright opal globe on a cast bracket, a quadrant brace under the arm
    with a ring in the spandrel. Anchor: on the wall, at the arm."""
    m = M.Model(PREFIX + "bracket_a")
    m.box((-2, -10, 0), (2, 5, 1), IRON, grain="y")                     # wall plate
    m.box((-1, 5, 0), (1, 6, 1), IRON)
    m.box((-1, -11, 0), (1, -10, 1), IRON)
    m.box((-1, -1, 1), (1, 1, 12.5), IRON, grain="z")                   # arm
    m.ring("x", (0, -1, 1), 8.0, 1.0, 2.0, IRON, sides=24, arc=(90, 180))
    m.ring("x", (0, -4.1, 4.1), 2.6, 1.0, 2.0, IRON_D, sides=12)
    m.tube("y", (0, 11), 1.0, 2.5, 1.5, BRASS)                          # cup
    m.tube("y", (0, 11), 2.5, 3.25, 3.0, BRASS_D)                       # gallery
    _opal_globe(m, (0, 7.5, 11), 4.5)
    return m


def _bracket_b():
    """Version B wall lamp: an enamel cone shade and a bare bulb under a square arm with a strut,
    on a riveted plate. Anchor: on the wall, at the underside of the arm."""
    m = M.Model(PREFIX + "bracket_b")
    m.box((-3, -9, 0), (3, 4, 1), IRON, grain="y")                      # riveted wall plate
    for x in (-2, 2):
        for y in (-8, 3):
            m.box((x - 0.5, y - 0.5, 1), (x + 0.5, y + 0.5, 1.5), RIVET)
    m.box((-1, 0, 1), (1, 2, 12.5), IRON, grain="z")                    # square arm
    m.beam((0, -7.5, 1.0), (0, 0.5, 9.0), 1.0, 1.0, IRON_D)             # strut
    m.box((-1.5, -1, 9.0), (1.5, 3, 12.5), IRON_D)                      # junction box
    c = (0, 10.75)
    m.tube("y", c, -2.5, -1.0, 1.25, BRASS)                             # lampholder
    _cone_shade(m, c, -2.0, -6.0, 1.75, 6.25, 4)
    K.bulb(m, (0, -2.5, 10.75), glass=3.5)
    return m


def _cage_a():
    """Version A caged wall lamp: a round glass on a round base under two crossed hoops. Anchor: on
    the wall, centre of the base."""
    m = M.Model(PREFIX + "cage_a")
    m.tube("z", (0, 0), 0.0, 1.5, 5.0, IRON)                            # base
    m.tube("z", (0, 0), 1.5, 2.5, 4.0, IRON_D)                          # glass seat
    m.tube("y", (0, 1.0), 4.5, 9.0, 0.75, IRON_D)                       # conduit
    with m.turned(("x", 90), about=(0, 0, 2.5)):                        # the dome looks out of the wall
        K.glass_ball(m, (0, 0, 2.5), 3.5,
                     [(0.0, 0.4, 1, GLOW[1]), (0.4, 0.75, 1, GLOW[2]), (0.75, 1.0, 1, GLOW[3])])
    m.ring("x", (0, 0, 2.5), 4.25, 1.0, 1.0, IRON, sides=16, arc=(0, 180))
    m.ring("y", (0, 0, 2.5), 4.25, 1.0, 1.0, IRON, sides=16, arc=(180, 360))
    m.box((-1, -1, 6.5), (1, 1, 7.5), IRON_D)                           # where the hoops cross
    return m


def _cage_b():
    """Version B caged wall lamp: a glass block behind a guard of flat bars on a riveted plate.
    Anchor: on the wall, centre of the plate."""
    m = M.Model(PREFIX + "cage_b")
    m.box((-4, -6, 0), (4, 6, 1), IRON, grain="y")
    for x in (-3, 3):
        for y in (-5, 5):
            m.box((x - 0.5, y - 0.5, 1), (x + 0.5, y + 0.5, 1.5), RIVET)
    m.box((-3, -5, 1), (3, 5, 2), IRON_D)                               # body
    m.tube("y", (0, 1.0), 6.0, 9.0, 0.75, IRON_D)                       # conduit
    m.box((-2, -4, 2), (2, 4, 5), GLOW[1], faces={"s": BULB_FACE}, emit=15, shade=False)
    for x in (-3, 2):
        m.box((x, -5, 5.5), (x + 1, 5, 6.5), IRON, grain="y")           # guard: uprights
        for y in (-5, 4):
            m.box((x, y, 2), (x + 1, y + 1, 5.5), IRON_D, grain="z")    # and their returns
    for y in (-5, -2, 1, 4):
        m.box((-2, y, 5.5), (2, y + 1, 6.5), IRON, grain="x")           # bars
    return m


def _pendant_a():
    """Version A pendant: an opal globe in a brass gallery on a rod. Anchor: the hanging point."""
    m = M.Model(PREFIX + "pendant_a")
    _rose(m)
    m.tube("y", (0, 0), -12.0, -2.0, 0.5, BRASS_D, sides=4)             # rod
    m.tube("y", (0, 0), -14.0, -12.0, 2.0, BRASS)                       # holder
    m.tube("y", (0, 0), -15.0, -14.0, 3.5, BRASS_D)                     # gallery
    _opal_globe(m, (0, -19.25, 0), 5.5, sides=12, squash=0.82)
    m.tube("y", (0, 0), -24.5, -23.75, 1.0, BRASS)
    return m


def _pendant_b():
    """Version B pendant: an enamel cone shade and a bare bulb on a rod. Anchor: the hanging point."""
    m = M.Model(PREFIX + "pendant_b")
    _rose(m)
    m.tube("y", (0, 0), -9.0, -2.0, 0.5, BRASS_D, sides=4)
    m.tube("y", (0, 0), -12.0, -9.0, 1.25, BRASS)                       # lampholder
    _cone_shade(m, (0, 0), -10.0, -15.0, 2.0, 8.0, 5)
    K.bulb(m, (0, -12.0, 0), glass=3.0)
    return m


def _desk_green():
    """The green desk lamp: a brass foot and stem, a long hood of cased green glass over a tube
    bulb. The one lamp that glows green. Anchor: centre of the foot."""
    m = M.Model(PREFIX + "desk_green")
    m.tube("y", (0, 0), 0.0, 1.0, 3.0, BRASS)
    m.tube("y", (0, 0), 1.0, 2.0, 1.5, BRASS_D)
    m.tube("y", (0, 0), 2.0, 7.5, 0.5, BRASS, sides=4)
    m.box((-4.5, 7.5, -0.5), (4.5, 8.5, 0.5), BRASS_D, grain="x")       # cross bar
    lit = dict(emit=15, shade=False)
    for x in (-4.5, 3.5):
        m.box((x, 8.5, -2), (x + 1, 10.5, 2), GREEN, **lit)             # ends of the hood
    m.box((-4.5, 10.0, -1.0), (4.5, 11.0, 1.0), GREEN, grain="x", **lit)
    m.box((-4.5, 10.0, 1.0), (4.5, 11.0, 4.0), GREEN, rot=("x", 35.0, (0, 11.0, 1.0)), grain="x", **lit)
    m.box((-4.5, 10.0, -4.0), (4.5, 11.0, -1.0), GREEN, rot=("x", -35.0, (0, 11.0, -1.0)), grain="x", **lit)
    m.box((-3.5, 9.8, -0.9), (3.5, 10.0, 0.9), GREEN_LIT, **lit)        # the lit inside of the hood
    K.glass_prism(m, "x", (9.0, 0), -2.5, 2.5, 0.75, GLOW[3], cap=GLOW[2])
    return m


def _signal(name, lit):
    """Signal lamp: a red lens under a hood on a small iron housing. Two models, lit and dark; the
    blinking is A8's (swap the item model of the entities tagged c164_signal). Anchor: on the wall,
    centre of the plate."""
    m = M.Model(PREFIX + name)
    m.box((-3.5, -3.5, 0), (3.5, 3.5, 1), IRON, grain="y")
    m.tube("y", (0, 1.0), -7.5, -3.5, 0.75, IRON_D)                     # conduit
    m.tube("z", (0, 0), 1.0, 4.0, 3.0, IRON_D)                          # housing
    m.tube("z", (0, 0), 4.0, 4.75, 3.25, BRASS_D)                       # bezel
    tones = (RED[1], RED[2], RED[3]) if lit else (RED[0], RED[0], RED[1])
    with m.turned(("x", 90), about=(0, 0, 4.5)):
        K.glass_ball(m, (0, 0, 4.5), 2.5,
                     [(0.0, 0.4, 1, tones[0]), (0.4, 0.75, 1, tones[1]), (0.75, 1.0, 1, tones[2])],
                     emit=15 if lit else 0)
    m.ring("z", (0, 0, 5.5), 3.5, 1.0, 3.0, IRON, sides=16, arc=(0, 180))   # hood
    return m


def _uplight():
    """A small ground projector that washes the wall above it (A2: two blocks out from the plinth).
    The lens looks along +z and up. Anchor: centre of the foot."""
    m = M.Model(PREFIX + "uplight")
    m.box((-3, 0, -3), (3, 1, 3), IRON_D)
    for x in (-3, 2):
        m.box((x, 1, -1), (x + 1, 5.5, 1), IRON, grain="y")             # yoke
    with m.turned(("x", -40.0), about=(0, 4.5, 0)):
        m.tube("z", (0, 4.5), -2.25, 2.0, 2.0, IRON)                    # drum
        m.tube("z", (0, 4.5), -3.0, -2.25, 1.25, IRON_D)
        m.tube("z", (0, 4.5), 2.0, 3.0, 2.5, BRASS_D)                   # bezel
        K.glass_prism(m, "z", (0, 4.5), 3.0, 3.1, 1.75, GLOW[1])
        K.glass_prism(m, "z", (0, 4.5), 3.1, 3.2, 0.9, GLOW[3])
    return m


def _wire():
    """The cable of a festoon: runs along +z from the anchor, 48 long, and is stretched between two
    points. One flat tone, so stretching smears nothing."""
    m = M.Model(PREFIX + "wire")
    m.box((-0.5, -0.5, 0), (0.5, 0.5, 48), CABLE, grain="z")
    return m


def _bulb():
    """One bulb of a festoon, its holder clipped on the cable. Anchor: on the cable's axis."""
    m = M.Model(PREFIX + "bulb")
    m.box((-1, -1, -1), (1, 0.5, 1), IRON_D)
    K.bulb(m, (0, -1, 0), glass=3.0, cap=1.0)
    return m


# name -> how it is mounted, its scale, where its glowing part is (blocks, in the model's frame) and
# the light level A2 asked for (None: throws no light)
SPEC = {
    "street": dict(build=_street, mount="floor", scale=2.0, light=(0.0, 4.375, 0.0), level=14),
    "bracket_a": dict(build=_bracket_a, mount="wall", light=(0.0, 0.47, 0.69), level=12),
    "bracket_b": dict(build=_bracket_b, mount="wall", light=(0.0, -0.4, 0.67), level=12),
    "cage_a": dict(build=_cage_a, mount="wall", light=(0.0, 0.0, 0.3), level=7),
    "cage_b": dict(build=_cage_b, mount="wall", light=(0.0, 0.0, 0.3), level=7),
    "pendant_a": dict(build=_pendant_a, mount="ceiling", light=(0.0, -1.2, 0.0), level=8),
    "pendant_b": dict(build=_pendant_b, mount="ceiling", light=(0.0, -0.95, 0.0), level=8),
    "desk_green": dict(build=_desk_green, mount="floor", light=(0.0, 0.55, 0.0), level=6),
    "signal": dict(build=lambda: _signal("signal", True), mount="wall", light=None),
    "signal_off": dict(build=lambda: _signal("signal_off", False), mount="wall", light=None),
    "uplight": dict(build=_uplight, mount="floor", light=(0.0, 0.4, 0.15), level=8),
    "wire": dict(build=_wire, mount="floor", light=None),
    "bulb": dict(build=_bulb, mount="floor", light=(0.0, -0.25, 0.0), level=12),
}
SCALE = {PREFIX + name: spec.get("scale", 1.0) for name, spec in SPEC.items()}
VERSIONED = ("bracket", "cage", "pendant")
STREET_CLEARANCE = 8    # A2: a street lamp stands at least this far from a main wall face


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + name: spec["build"]() for name, spec in SPEC.items()}


def models():
    return dict(_models())


# ---- placing -------------------------------------------------------------------------------------------
def place(canvas, kind, pos, facing="south", origin=(0, 0, 0), version=None, light=True, level=None,
          yaw=None, **opts):
    """Put one lamp into the scene; returns the number of display entities (1).

    kind     "street", "bracket", "cage", "pendant", "desk_green", "signal", "signal_off", "uplight".
             "bracket", "cage" and "pendant" come in two versions: `version` "a" or "b" picks one,
             left out it is VERSION.
    pos      scene coordinates. A wall lamp: the point on the wall face where it is fixed, `facing`
             the way that face looks. A standing lamp: the centre of its foot on the floor (`facing`
             turns it; the uplight looks that way). A pendant: the point on the ceiling it hangs from.
    light    offer the lamp's light source to A2's tool at the level A2 gave for this lamp, or at
             `level`. A line that registers its own lights passes light=False.
    opts     go to artkit.models.display (brightness, view).
    Street lamps stand at least STREET_CLEARANCE blocks from a main wall face (A2).
    """
    name = f"{kind}_{version or VERSION}" if kind in VERSIONED else kind
    spec = SPEC[name]
    yaw = K.FACING[facing] if yaw is None else yaw
    n = K.put(canvas, _models()[PREFIX + name], pos, mount=spec["mount"], yaw=yaw,
              scale=spec.get("scale", 1.0), origin=origin, **opts)
    if name.startswith("signal"):
        canvas.entities[-1][3]["Tags"].append("c164_signal")
    if light and spec["light"] is not None:
        cell = K.light_cell(pos, yaw, spec["light"], origin)
        K.offer_lights(canvas, [(cell, spec["level"] if level is None else level)], f"props/lamps:{name}")
    return n


def festoon(canvas, a, b, spacing=1.0, origin=(0, 0, 0), light=True, level=None):
    """A string of bare bulbs on a cable from a to b (scene coordinates, both in the air): one
    stretched cable and a bulb every `spacing` blocks, half a spacing in from each end. Every third
    bulb offers a light source. Returns the number of display entities (1 + the bulbs)."""
    a = tuple(a[i] + origin[i] for i in range(3))
    b = tuple(b[i] + origin[i] for i in range(3))
    built = _models()
    canvas.add_entity(a[0], a[1], a[2], M.between(built[PREFIX + "wire"], a, b))
    length = math.dist(a, b)
    count = max(1, int(round(length / spacing)))
    yaw = math.degrees(math.atan2(-(b[0] - a[0]), b[2] - a[2]))
    spec = SPEC["bulb"]
    lights = []
    for i in range(count):
        t = (i + 0.5) / count
        p = tuple(a[k] + (b[k] - a[k]) * t for k in range(3))
        K.put(canvas, built[PREFIX + "bulb"], p, yaw=yaw)
        if i % 3 == 1 or count < 3 and i == 0:
            lights.append((K.light_cell(p, yaw, spec["light"]), spec["level"] if level is None else level))
    if light:
        K.offer_lights(canvas, lights, "props/lamps:festoon")
    return 1 + count


def build(canvas, origin=(0, 0, 0), version=VERSION):
    """What this package places in the master scene itself: the pair of bracket lamps beside the
    entrance, on whatever front the main line has built there, and two street lamps on the court.
    Lamps elsewhere are placed by the line that builds the wall or the room, with place()."""
    n = 0
    front = S.east_wall_x(9)
    for k in (8, 9):                                    # the pilasters either side of the door
        z = S.pilaster_z(k)
        x = K.east_face(canvas, 4, z, S.WALL_E, front + S.DEPTH_CORNICE, origin)
        if x is not None:
            n += place(canvas, "bracket", (x, 4.0, z + 0.5), facing="east", origin=origin, version=version)
    for z in (-5.5, 6.5):                               # either side of the axis, clear of the front
        n += place(canvas, "street", (front + 1 + STREET_CLEARANCE + 0.5, S.GROUND, z), origin=origin)
    return n
