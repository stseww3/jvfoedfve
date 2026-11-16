"""The great armillary sphere of the front court (card plan/packages/machines/armillary.md).

It stands where the brass meridian of the court (x = 35) crosses the entrance axis (z = 0), in the
middle of the emblem roundel that site/court lays there, and it is the foreground of the axis view
V2: from the head of the grand stair the lit entrance and the great dome are seen through its rings.

    centre cell      skeleton.ARMILLARY = (35, 0); the centre line of the sphere is (35.5, 0.5)
    stone base       blocks, x 34..36, z -1..1, y 0..1: a square of deepslate stairs (two half-block
                     steps) round a core, and one block of wall stone on it; 3 wide, 2 high
    sphere           its middle at y 4.75; the bore of the meridian ring is 4.5 blocks
    top              y 7.25: the crown of the meridian ring, a plain arc. Nothing stands on it; the
                     polar axis ends in a ball, below the crown.

The brass work is display entities, one model to the ring. Every model has its anchor in the middle
of the sphere and every entity stands on that one point, so they all take their light from the
same cell, LIGHT_CELL = (35, 4, 0): no step in brightness from ring to ring. The cell under it,
(35, 3, 0), stays empty: the props line (props/lamps) puts a hidden light there, with the four
ground lamps.

One version stands, a, the classic one: many thin rings -- meridian, equator, the two tropics, one
colure, the ecliptic band with its scale, the polar axis and a small earth. 8 entities. From every
side it is a ball of rings, and the gold windows and the gates show through it (director, 11-16).

From due east (V2) the meridian ring is a full circle; the polar axis and the equator are the two
diagonals in it, one rising to the right and one to the left; behind the circle are the lit
entrance and the gold window over it. From due north or south, along the brass meridian that leads
people that way, the meridian ring stands on edge: an upright through the ball of rings.

Two things the director ruled out on the pictures (11-16; the code is in the branch's history, the
card names the commit):
  a horizon ring   level across the meridian ring. Along the meridian it is seen on edge, a level
                   bar through the upright one: a cross in a circle (red line).
  version b        one great graduated meridian ring and a broad ecliptic band. Along the meridian
                   it is a thick hoop, and from the front it hides more of the windows: a porthole.

What does not turn (the frame), drawn the way it stands; +x east, +y up, +z south:
  stand      the iron saddle on the base that clamps the foot of the meridian ring
  meridian   upright, north-south, over the brass line in the paving; it carries the two bearings
             of the polar axis and the ball that ends it

What turns (the sphere proper), every piece ABOUT THE POLAR AXIS THROUGH THE ANCHOR. The axis lies
in the meridian plane and rises LATITUDE degrees above the northern horizon; as a unit vector
(east, up, south) it is POLE = (0, sin LATITUDE, -cos LATITUDE). These models are drawn in the
sphere's own frame, with +y along the polar axis, and each is placed with the two turns
(("y", hour), ("x", LATITUDE - 90)): the first spins it about its own axis, the second tips that
axis onto the pole. To move one, change `hour` only; pieces() gives the turns for any hour (the
southern tropic has a half turn about z in front). The sky's daily motion is the negative sense.
  axis       the rod and the earth on it
  equator    square to the axis
  tropic     the same model twice, OBLIQUITY degrees north and south of the equator
  ecliptic   the band, OBLIQUITY degrees off the equator, a mark every 10 degrees and a long one
             every 30 (the twelve signs)
  colure     the one ring through both poles that carries the others (the solstitial colure), with
             a bolt head where each of them crosses it. Only one: two would cross at the pole.
This round places a still pose, HOUR; the motion is the motion line's. Only the axis, the ecliptic
and the colure show that they turn: the equator and the tropics are plain rings about the axis.
The pose is chosen on the pictures: at -35 the colure stands open beside the band from due east and
from the entrance, two ovals in the ring, and along the meridian the band is close to a whole
circle. At -15 the band opens a little more towards V2, but the colure closes onto the axis, and
from the entrance all that is left in the ring is bars across the axis.

Brass: old and dark (the palette's brass_dark), one step lighter where a face looks up; only the
scale marks, the bolt heads and the ball on the axis go brighter. Nothing glows. At night the four
small ground lamps at the corners of the base light it; lamps and light sources are the props
line's (props/lamps), which reads LAMP_CELLS and LIGHT_CELL from here; lamp_feet() gives the same
four places as points, with the yaw towards the sphere.

    from scenes.obs.machines import armillary
    n = armillary.build(canvas, origin)      # base and brass; returns the entity count
"""
import functools
import math
import os

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S

PREFIX = "mach_armillary_"
VERSION = "a"                       # the one version (director, 11-16); the models keep its letter
VERSIONS = ("a",)

# --- where it stands (the skeleton's numbers) -----------------------------------------------------
CX, CZ = S.ARMILLARY                # the cell (35, 0)
# DRAFT ONLY (this scratch branch): the base to look at, by the environment
_BASE = os.environ.get("C164_ARM_BASE", "steps")        # steps | plate | wall | rail | cap
_RAISE = 0.5 if _BASE == "cap" else 0.0
BASE_TOP = S.GROUND + 2 + _RAISE    # the top of the stone base
CENTRE_Y = S.GROUND + 4.75 + _RAISE # the middle of the sphere
LIGHT_CELL = (CX, int(math.floor(CENTRE_Y)), CZ)    # the cell every brass piece takes its light from
# the four ground lamps: the cells diagonally off the corners of the base, on the court
LAMP_CELLS = tuple((CX + dx, CZ + dz) for dx in (-2, 2) for dz in (-2, 2))

# --- the instrument's own numbers -----------------------------------------------------------------
# the pole's height over the northern horizon: the skeleton's (director, 11-15: the telescope, the
# transit instrument and this sphere read one number)
LATITUDE = float(S.LATITUDE)
OBLIQUITY = 23.5                    # the ecliptic's tilt to the equator
HOUR = -35.0                        # the still pose: how far the sphere is turned about the polar axis
POLE = (0.0, math.sin(math.radians(LATITUDE)), -math.cos(math.radians(LATITUDE)))
BRIGHTNESS = None                   # None: the light of LIGHT_CELL (the props line lights it). Else (sky, block)

# The models are drawn 2 px to the unit and shown at twice their size: 16 px to the block, and a ring
# 5 blocks across stays inside the 48 units a model may span. So below 1 unit = 2 px = 1/8 block.
PX = 2.0
FOOT = (CENTRE_Y - BASE_TOP) * 16.0 / PX        # 22: the top of the base, in units below the anchor
R_BORE = 18.0                       # the bore of the meridian ring
R_CAGE = 17.5                       # what turns keeps inside this radius
# A ring is (outer radius, radial size, width along its own axis); the tropic has the radius of the
# sphere it lies on in the first place. studs: where on the colure the other rings cross it, in
# degrees from the equator (the model's +x) towards the north pole (+y).
SPEC = {
    "a": dict(
        parts=("stand", "meridian", "axis", "equator", "tropic", "ecliptic", "colure"),
        meridian=(20.0, 2.0, 2.0),
        equator=(16.75, 1.5, 2.0),
        tropic=(16.75, 1.5, 1.5),
        ecliptic=(17.0, 1.0, 3.0),
        colure=(16.5, 1.5, 1.5),
        studs=(0.0, OBLIQUITY, 180.0 - OBLIQUITY, 180.0, 180.0 + OBLIQUITY, -OBLIQUITY),
        rod=0.75, earth=2.5, boss=1.5, knob=1.75,
    ),
}
POLAR = ("axis", "equator", "tropic", "ecliptic", "colure")     # the pieces that turn about the pole

# --- materials (palette only) ---------------------------------------------------------------------
BRASS = P.mat("brass_dark")                 # the body of every ring
WORN = P.mat("brass", base=2)               # one step up: bolts, collars, the ball on the axis
HEAD = P.mat("brass_flat")                  # the end of a bolt: that step, flat
IRON = P.mat("iron")
EARTH = P.mat("verdigris")                  # the small globe in the middle: the dome's copper green
MARK = P.RAMPS["brass"][3]                  # the scale marks: two steps over the body, no brighter

STEP = B.SLATE_BRICK                        # the main building's plinth stone
DIE = B.ASHLAR_PANEL.block                  # wall stone with a sunk panel on each face


# --- rings ----------------------------------------------------------------------------------------
def _mark(body, w, h, upright, long):
    """The picture of one division of a scale: the body's own with a mark across its middle.

    w, h: the face in pixels; upright: the mark runs down the picture (else across it). The mark is
    centred both ways, so it reads the same whichever way round a face shows its picture."""
    across, along = (w, h) if upright else (h, w)
    n = 2 if across % 2 == 0 else 1
    length = along - 2 if long else max(2, (along - 2) // 2)
    rows = ["t" * n] * length if upright else ["t" * length] * n
    return Sprite(f"{PREFIX}mark_{body.name}_{w}x{h}_{'v' if upright else 'h'}{length}", rows, {"t": MARK},
                  back=body)


def _hoop(m, axis, r_out, thick, width, body, sides, scale=False, every=3, seed=1):
    """Model.ring() about the model's origin, with a scale on its outer face if wanted: one mark to
    the division (360 / sides degrees), across the rim, a long one every `every`-th; division 0 lies
    on the first of the two other axes."""
    k = M.AXES.index(axis)
    o1, o2 = [i for i in range(3) if i != k]
    half = r_out * math.tan(math.pi / sides)
    lo, hi = [0.0] * 3, [0.0] * 3
    lo[k], hi[k] = -width / 2.0, width / 2.0
    lo[o1], hi[o1] = r_out - thick, r_out
    lo[o2], hi[o2] = -half, half
    outer, inner, flats = M.SIDE[o1][1], M.SIDE[o1][0], M.SIDE[k]
    lit = {outer: "along", inner: "inner", flats[0]: "along", flats[1]: "along"}
    marks = None
    if scale:
        _, ua, va = M.FACE_AXES[outer]
        w, h = (max(1, int(round((hi[a] - lo[a]) * PX))) for a in (ua, va))
        back = body.variant(0, "along")
        marks = [_mark(back, w, h, va == k, long) for long in (False, True)]
    for i in range(sides):
        faces = {outer: marks[i % every == 0]} if marks else {}
        theta = 360.0 * i / sides
        m.box(tuple(lo), tuple(hi), body, rot=(axis, theta, (0.0, 0.0, 0.0)) if theta else None,
              skip="".join(M.SIDE[o2]), grain=M.AXES[o2], seed=seed, faces=faces, lit=lit)
    return m


# --- the models -----------------------------------------------------------------------------------
def _name(version, part):
    return f"{PREFIX}{version}_{part}"


def _new(version, part):
    return M.Model(_name(version, part), px=PX)


def _stand(version):
    """The saddle: an iron foot on the stone and two cheeks that clamp the lowest eighth of the
    meridian ring between them, bolted through. It lies in the meridian plane, so that from above
    nothing shows across the meridian line. The ring's foot is sunk in the iron."""
    r_out, _, w = SPEC[version]["meridian"]
    m = _new(version, "stand")
    m.box((-3.0, -FOOT, -4.0), (3.0, -FOOT + 2.5, 4.0), IRON)
    cheek = r_out + 0.5
    for side in (-1.0, 1.0):
        m.ring("x", (side * (w / 2.0 + 0.5), 0.0, 0.0), (R_BORE + cheek) / 2.0, cheek - R_BORE, 1.0, IRON,
               sides=32, arc=(157.5, 202.5))
    for a in (-15.0, 15.0):
        with m.turned(("x", a)):
            m.tube("x", (-(R_BORE + cheek) / 2.0, 0.0), -(w / 2.0 + 1.5), w / 2.0 + 1.5, 0.5, WORN, sides=4,
                   cap=HEAD)
    return m


def _meridian(version):
    """The meridian ring, upright in the north-south plane, with the two bearings of the polar axis.
    The northern one (the upper) ends in a ball; the crown of the ring stays the highest point."""
    s = SPEC[version]
    r_out, thick, w = s["meridian"]
    m = _new(version, "meridian")
    _hoop(m, "x", r_out, thick, w, BRASS, 36)
    with m.turned(("x", LATITUDE - 90.0)):              # +y now points at the pole
        for end in (-1.0, 1.0):
            m.tube("y", (0.0, 0.0), end * (R_BORE - 0.5), end * (r_out + 1.0), s["boss"], BRASS, sides=8)
        m.ball((0.0, r_out + 1.0 + s["knob"] * 0.75, 0.0), s["knob"], WORN, sides=8, layers=4)
        m.tube("y", (0.0, 0.0), -(r_out + 1.75), -(r_out + 1.0), s["boss"] + 0.5, WORN, sides=8)
    return m


def _axis(version):
    """The polar axis (along the model's y) with the earth on it. The rod ends inside the bearings
    of the meridian ring."""
    s = SPEC[version]
    m = _new(version, "axis")
    reach = R_BORE + 0.5
    m.tube("y", (0.0, 0.0), -reach, reach, s["rod"], BRASS, sides=8)
    m.ball((0.0, 0.0, 0.0), s["earth"], EARTH, sides=10, layers=5)
    for end in (-1.0, 1.0):
        m.tube("y", (0.0, 0.0), end * (s["earth"] - 0.25), end * (s["earth"] + 0.75), s["rod"] + 0.5, WORN, sides=8)
    return m


def _equator(version):
    r_out, thick, w = SPEC[version]["equator"]
    m = _new(version, "equator")
    m.ring("y", (0.0, 0.0, 0.0), r_out - thick / 2.0, thick, w, BRASS, sides=32)
    return m


def _tropic(version):
    """The northern tropic: the circle OBLIQUITY degrees north of the equator. Turned upside down it
    is the southern one."""
    r, thick, w = SPEC[version]["tropic"]
    e = math.radians(OBLIQUITY)
    m = _new(version, "tropic")
    m.ring("y", (0.0, r * math.sin(e), 0.0), r * math.cos(e) - thick / 2.0, thick, w, BRASS, sides=32)
    return m


def _ecliptic(version):
    """The ecliptic band: tipped OBLIQUITY degrees about the model's z, so its highest point lies
    over +x, where the colure and the northern tropic meet it. The scale is on its outer face."""
    r_out, thick, w = SPEC[version]["ecliptic"]
    m = _new(version, "ecliptic")
    with m.turned(("z", OBLIQUITY)):
        _hoop(m, "y", r_out, thick, w, BRASS, 36, scale=True)
    return m


def _colure(version):
    """The colure: the ring through both poles and the two highest points of the ecliptic (the
    model's x-y plane), with a hub at each pole where it turns on the rod, and a bolt through it
    where the equator, the tropics and the ecliptic cross it: the head shows outside them."""
    s = SPEC[version]
    r_out, thick, w = s["colure"]
    m = _new(version, "colure")
    m.ring("z", (0.0, 0.0, 0.0), r_out - thick / 2.0, thick, w, BRASS, sides=32)
    for end in (-1.0, 1.0):
        m.tube("y", (0.0, 0.0), end * (r_out - thick - 0.5), end * (r_out + 0.5), s["rod"] + 0.75, BRASS, sides=8)
    for a in s["studs"]:
        with m.turned(("z", a)):
            m.tube("x", (0.0, 0.0), r_out - thick - 0.5, R_CAGE, 0.5, WORN, sides=4, cap=HEAD)
    return m


BUILDERS = {"stand": _stand, "meridian": _meridian, "axis": _axis, "equator": _equator, "tropic": _tropic,
            "ecliptic": _ecliptic, "colure": _colure}


@functools.lru_cache(maxsize=None)
def _models():
    return {_name(version, part): BUILDERS[part](version) for version in SPEC for part in SPEC[version]["parts"]}


def models():
    return dict(_models())


# --- placing --------------------------------------------------------------------------------------
def pieces(version=VERSION, hour=HOUR):
    """[(part, turns)]: the entities of a version and the turns that set each one, for the sphere
    turned `hour` degrees about the polar axis. The frame takes no turns."""
    spin, tilt = ("y", float(hour)), ("x", LATITUDE - 90.0)
    out = []
    for part in SPEC[version]["parts"]:
        if part not in POLAR:
            out.append((part, ()))
            continue
        out.append((part, (spin, tilt)))
        if part == "tropic":
            out.append((part, (("z", 180.0), spin, tilt)))
    return out


def lamp_feet(origin=(0, 0, 0)):
    """[((x, y, z), yaw)]: where the four small ground lamps stand (the middle of each of LAMP_CELLS,
    on the court) and the yaw that turns a model's +z towards the axis of the sphere."""
    ox, oy, oz = origin
    return [((ox + S.mid(x), oy + S.GROUND, oz + S.mid(z)), math.degrees(math.atan2(x - CX, CZ - z)))
            for x, z in LAMP_CELLS]


def _base(canvas, origin):
    """The stone base: a square of deepslate stairs rising to the middle from all four sides (the
    game turns the corner ones), a core, and the die of wall stone on top."""
    x0, y0, z0 = origin[0] + CX, origin[1] + S.GROUND, origin[2] + CZ
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            if dx == 0 and dz == 0:
                canvas.set(x0, y0, z0, STEP.block)
                continue
            if _BASE == "plate":
                canvas.set(x0 + dx, y0, z0 + dz, f"{STEP.slab}[type=bottom]")
                continue
            if _BASE == "wall":
                canvas.set(x0 + dx, y0, z0 + dz, STEP.wall)
                continue
            # a stair faces the way it rises: towards the middle
            facing = ("west" if dx > 0 else "east") if dx else ("north" if dz > 0 else "south")
            canvas.set(x0 + dx, y0, z0 + dz, f"{STEP.stairs}[half=bottom,facing={facing}]")
    canvas.set(x0, y0 + 1, z0, DIE)
    if _BASE == "cap":
        canvas.set(x0, y0 + 2, z0, f"{B.ASHLAR_FINE.slab}[type=bottom]")
    if _BASE == "rail":
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                if max(abs(dx), abs(dz)) == 2 and (CX + dx, CZ + dz) not in LAMP_CELLS:
                    canvas.set(x0 + dx, y0, z0 + dz, B.IRON_BARS)


def build(canvas, origin=(0, 0, 0), version=VERSION):
    """Place the base and the brass of one version; returns the number of display entities."""
    _base(canvas, origin)
    built = _models()
    at = (origin[0] + S.mid(CX), origin[1] + CENTRE_Y, origin[2] + S.mid(CZ))
    opts = {} if BRIGHTNESS is None else {"brightness": BRIGHTNESS}
    n = 0
    for part, turns in pieces(version):
        nbt = M.display(built[_name(version, part)], scale=PX, turns=turns, **opts)
        nbt["Tags"] += ["c164_armillary", f"c164_armillary_{part}"]
        canvas.add_entity(at[0], at[1], at[2], nbt)
        n += 1
    return n
