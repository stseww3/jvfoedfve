"""props/pipes -- the pipework family (plan/parts/A6-props.md 2.2, card plan/packages/props/pipes.md).

Pipes are what shows on the stone that this is a building of the electrical age: copper rainwater
pipes in the corners of the front, and where the power house's main comes in, a stop valve with a
red handwheel and a pressure gauge. Every pipe comes from somewhere and goes somewhere: a run ends
in a hopper, a sleeve, a plate on a wall or a grating, a bend or a fitting, never in the air.

Two materials, both the palette's:

    old copper   rainwater: the downpipe (3 px), its hopper head, clips and sleeves
    iron         steam and heating: the main in two bores, "l" (6 px) and "m" (4 px), with plates,
                 flanges, bends and stop valves; a valve's handwheel is the one red thing (signal),
                 the gauge is brass with a cream dial and three phosphor marks

How a line is put together:

    run(canvas, a, b, kind)             one straight length from point a to point b on the pipe's axis.
                                        It is ONE model drawn out along its axis, whatever the length;
                                        it is painted in flat tones that run with the axis, so the
                                        stretch smears nothing. Everything else is a piece of its own
                                        at 16 px to the block and is never stretched.
    place(canvas, kind, pos, along, out)   a fitting ON a run (flange, valve, bend, gauge): `pos` is a
                                        point of the axis, `along` the way the pipe runs through it,
                                        `out` the way its own second axis points (a valve's stem, a
                                        bend's other leg, a gauge's stalk). The run goes right through
                                        a flange; it ends inside the flanges of a valve or a bend.
    mount(canvas, kind, pos, out, up)   a piece ON a surface (plate, hopper, clip, sleeve, bonnet,
                                        band): `pos` is on that surface, `out` the way the surface looks.

    downpipe(canvas, corner, top, bottom, facing, side)   a whole rainwater pipe in a re-entrant corner
    inlet(canvas)                       where the power house's main enters the building
    dress(canvas)                       what the family puts on the main building: both of the above

Directions are names: "east", "west", "south", "north", "up", "down". All functions take scene
coordinates plus `origin` and return the number of display entities they placed.

build() places nothing while DRESS is off (A0, 11-14: whatever dresses the whole building carries
such a switch and is opened after its review). The test scene obs_props_pipes calls dress() itself.
"""
import functools
import math

from artkit import models as M

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from . import _kit as K

PREFIX = "prop_pipe_"
DRESS = False           # the family on the main building: off until the review has passed it

DIRS = {"east": (1, 0, 0), "west": (-1, 0, 0), "south": (0, 0, 1), "north": (0, 0, -1),
        "up": (0, 1, 0), "down": (0, -1, 0)}

RUN = 48.0              # a run's model is this long (three blocks at scale 1)
BORE = {"l": 3.0, "m": 2.0}             # the iron main's radius: 6 px and 4 px across
BEND = {"l": 5.0, "m": 4.0}             # a bend's radius on the axis
BOLTS = {"l": (8, 22.5), "m": (6, 30.0)}                # bolts round a flange, and where the first one sits
DOWN_R = 1.5            # the copper downpipe: 3 px across
GAP = 1.0               # it stands this far clear of the wall, and of the return wall beside it
CLIP_EVERY = 3.0        # a downpipe is clipped about this often, in blocks


def _tones(name):
    """The dark, the middle and the light tone of a material, flat, around the step it is painted at."""
    base = P.mat(name).base
    return tuple(K.flat(name, base + d) for d in (-1, 0, 1))


IRON3 = _tones("iron")
COPPER3 = _tones("old_copper")
RED = P.mat("signal")
MOUTH = K.flat("old_copper", 0)         # the dark inside of a hopper
DIAL = K.flat("cream", 3)
NEEDLE = K.flat("iron", 0)
MARK = K.flat("phosphor", 2)
PIN = K.flat("brass", 4)
ABOVE = (0.0, 1.0, 0.0)                 # where the light on a level pipe comes from


# ---- directions -----------------------------------------------------------------------------------
def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _name(v):
    """The name of the direction a vector points in, or None when it lies along no axis."""
    length = math.sqrt(sum(c * c for c in v))
    if length < 1e-9:
        return None
    for name, d in DIRS.items():
        if all(abs(v[i] / length - d[i]) < 1e-6 for i in range(3)):
            return name
    return None


def _turns(along, out):
    """The turns (for artkit.models.display) that carry a model's +z onto `along` and its +y onto
    `out`, two directions at right angles. Its +x then points to out x along."""
    z, y = DIRS[along], DIRS[out]
    if sum(a * b for a, b in zip(z, y)):
        raise ValueError(f"{along!r} and {out!r} are not at right angles")
    x = _cross(y, z)
    # the matrix with columns x, y, z, taken apart as a turn about x, then y, then z
    if abs(x[2]) > 1.0 - 1e-9:
        a, b, c = math.atan2(-z[1], y[1]), -math.copysign(math.pi / 2.0, x[2]), 0.0
    else:
        a, b, c = math.atan2(y[2], z[2]), -math.asin(x[2]), math.atan2(x[1], x[0])
    return (("x", math.degrees(a)), ("y", math.degrees(b)), ("z", math.degrees(c)))


def _stone(canvas, x, y, z):
    """Whether a cell holds something a pipe can stand on or must go through: any block but the
    light line's invisible source."""
    name = canvas.name(x, y, z)
    return name is not None and name != B.LIGHT


# ---- shapes ---------------------------------------------------------------------------------------
def _even(m, axis, c, a0, a1, radius, tones, sides=8, light=ABOVE):
    """A round bar like Model.tube, painted to be drawn out: every long face is one flat tone -- the
    light one where it looks towards `light`, the dark one where it looks away -- so a stretch along
    the axis smears nothing and the bar still reads round."""
    dark, mid, bright = tones
    k = M.AXES.index(axis)
    o1, o2 = [i for i in range(3) if i != k]
    origin = [0.0, 0.0, 0.0]
    origin[k], origin[o1], origin[o2] = (a0 + a1) / 2.0, c[0], c[1]
    hw = radius * math.tan(math.pi / sides)
    lo, hi = [0.0] * 3, [0.0] * 3
    lo[k], hi[k] = a0, a1
    lo[o1], hi[o1] = c[0] - hw, c[0] + hw
    lo[o2], hi[o2] = c[1] - radius, c[1] + radius
    m._n += 1
    seed = m._n
    for i in range(sides // 2):
        angle = 360.0 * i / sides
        q = M.quat(axis, angle)
        faces = {letter: dark for letter in M.SIDE[k]}
        for letter in M.SIDE[o2]:
            d = sum(n * l for n, l in zip(M._qrot(q, M.NORMAL[letter]), light))
            faces[letter] = bright if d > 0.5 else dark if d < -0.5 else mid
        m.box(lo, hi, mid, rot=(axis, angle, tuple(origin)) if angle else None, skip="".join(M.SIDE[o1]),
              faces=faces, seed=seed, grain=axis)
    return m


def _bolts(m, radius, count, z0, z1, first=0.0):
    """Bolts round the axis z: `count` of them on a circle, each one texel square, from z0 to z1."""
    for i in range(count):
        m.box((radius - 0.5, -0.5, z0), (radius + 0.5, 0.5, z1), K.RIVET,
              rot=("z", first + 360.0 * i / count, (0.0, 0.0, 0.0)))
    return m


def _pair(m, size, z):
    """Two flanges bolted together on the axis z, from z to z + 2: a fitting's own and the pipe's."""
    r = BORE[size]
    count, first = BOLTS[size]
    m.tube("z", (0, 0), z, z + 1.0, r + 2.0, K.IRON)
    m.tube("z", (0, 0), z + 1.0, z + 2.0, r + 2.0, K.IRON_D)
    return _bolts(m, r + 1.0, count, z - 0.75, z + 2.75, first)


def _port(m, size, start, end):
    """A flanged port of a valve on the axis z: a neck from `start`, and the pair of flanges that
    ends at `end`. A run stops inside the pair."""
    m.tube("z", (0, 0), start, end - 2.0, BORE[size] + 0.75, K.IRON_D)
    return _pair(m, size, end - 2.0)


def _works(m, size, y0, top=90.0):
    """A valve's works, out along +y from y0 on the axis y: the neck, the bonnet's flange, the gland,
    the brass stem and the red handwheel; the stem ends WORKS above y0.

    The wheel is 2 r + 4 across and has five spokes: three in a round rim read as a car's badge,
    four as a cross. One spoke stands at the angle `top`, counted as Model.ring counts (from +x,
    right-handed about +y): the caller says which way is up once the works are turned into place."""
    r = BORE[size]
    m.tube("y", (0, 0), y0, y0 + 2.0, r - 0.5, K.IRON_D)
    m.tube("y", (0, 0), y0 + 2.0, y0 + 3.0, r + 0.5, K.IRON)
    m.tube("y", (0, 0), y0 + 3.0, y0 + 5.0, 1.5, K.IRON_D)
    m.tube("y", (0, 0), y0 + 5.0, y0 + WORKS, 0.75, K.BRASS)
    wheel, rim = y0 + WORKS - 1.5, r + 1.5
    first = top % 36.0          # the rim has ten flats; every spoke ends on the middle of one
    m.ring("y", (0.0, wheel, 0.0), rim, 1.0, 1.0, RED, sides=10, arc=(first, first + 360.0))
    for i in range(5):
        m.box((0.75, wheel - 0.5, -0.5), (rim - 0.5, wheel + 0.5, 0.5), RED,
              rot=("y", (top + 72.0 * i) % 360.0, (0.0, wheel, 0.0)))
    m.tube("y", (0, 0), wheel - 0.75, wheel + 0.75, 1.25, RED)
    m.tube("y", (0, 0), wheel + 0.75, wheel + 1.25, 1.0, K.BRASS_D)
    return m


WORKS = 7.75            # a valve's works are this long, from the foot of the neck to the stem's end


# ---- rainwater: old copper ------------------------------------------------------------------------
def _down():
    """The downpipe: along +z from the anchor, RUN long, to be drawn out between two points."""
    m = M.Model(PREFIX + "down")
    _even(m, "z", (0, 0), 0.0, RUN, DOWN_R, COPPER3)
    return m


def _hopper(name, side):
    """The hopper head under the cornice, in a re-entrant corner. Wall-mounted: the anchor is on the
    wall face behind the downpipe's axis, half a block under the soffit (the middle of the cell, so
    the piece is lit by the air it hangs in). side 1: the return wall stands at the model's +x, to
    the right of someone who looks at the wall; -1: to the left. The head leans into the corner:
    its outlet is the downpipe's socket, GAP clear of both walls.

    Top to bottom: the collar where the gutter's outlet comes out of the cornice stone, the short
    outlet pipe, the rim, the box with a lozenge on its front, the funnel, the socket."""
    m = M.Model(PREFIX + name)
    a = GAP + DOWN_R

    def x(r):
        """r is counted from the return wall's face."""
        return side * (a - r)

    light, dark = K.COPPER.variant(1), K.COPPER.variant(-1)
    outlet = (x(4.5), 3.5)
    m.tube("y", outlet, 7.0, 8.0, 2.5, dark)
    _even(m, "y", outlet, 4.0, 7.0, DOWN_R, COPPER3, light=(-0.6 * side, 0.0, 0.8))
    m.box((x(0.0), 3.0, 0.0), (x(9.0), 5.0, 7.0), light, faces={"u": MOUTH})
    m.box((x(0.5), -2.0, 0.0), (x(8.5), 3.0, 6.5), K.COPPER)
    m.box((x(3.5), -0.5, 6.5), (x(5.5), 1.5, 7.0), light, rot=("z", 45.0, (x(4.5), 0.5, 6.75)))
    m.box((x(0.5), -4.0, 0.0), (x(6.5), -2.0, 5.0), dark)
    m.box((x(0.5), -6.5, 0.5), (x(4.5), -4.0, 4.5), K.COPPER)
    return m


HOPPER_SOCKET = (-6.5, -4.0)    # the socket's underside and top, in texels from the hopper's anchor


def _down_clip():
    """A joint of the downpipe and the clip that holds it: the socket of the length below, and under
    it an iron band bolted together in front. Wall-mounted, the anchor on the wall face behind the
    axis at the height of the joint; the axis stands GAP + DOWN_R out."""
    m = M.Model(PREFIX + "down_clip")
    a = GAP + DOWN_R
    m.tube("y", (0, a), 0.0, 2.0, a, K.COPPER.variant(1))
    m.tube("y", (0, a), -1.5, 0.0, a, K.IRON_D)
    m.box((-1.0, -1.5, 2.0 * a), (1.0, 0.0, 2.0 * a + 1.0), K.IRON)
    m.box((-0.5, -1.25, 2.0 * a + 1.0), (0.5, -0.25, 2.0 * a + 1.5), K.RIVET)
    return m


def _down_sleeve():
    """Where the downpipe goes through stone -- a string course, the plinth's coping: a collar on
    the stone's face (the model's plane z = 0) round the pipe, which leaves along +z."""
    m = M.Model(PREFIX + "down_sleeve")
    m.tube("z", (0, 0), 0.0, 1.5, GAP + DOWN_R, K.COPPER.variant(-1))
    return m


# ---- steam and heating: iron ----------------------------------------------------------------------
def _main(name, r):
    """A length of the iron main: along +z from the anchor, RUN long, to be drawn out."""
    m = M.Model(PREFIX + name)
    _even(m, "z", (0, 0), 0.0, RUN, r, IRON3)
    return m


def _flange(name, size):
    """Two lengths bolted together: a pair of flanges on the axis z, the anchor between them."""
    m = M.Model(PREFIX + name)
    _pair(m, size, -1.0)
    return m


def _plate(name, size):
    """Where a main goes into a wall, a floor or a grating: a flange bolted on that face (the
    model's plane z = 0) and the neck the pipe is welded into; the pipe leaves along +z. The neck
    ends PLATE_NECK out."""
    m = M.Model(PREFIX + name)
    r = BORE[size]
    count, first = BOLTS[size]
    m.tube("z", (0, 0), 0.0, 1.5, r + 2.0, K.IRON)
    m.tube("z", (0, 0), 1.5, PLATE_NECK, r + 0.5, K.IRON_D)
    _bolts(m, r + 1.25, count, 1.5, 2.25, first)
    return m


PLATE_NECK = 3.0


def _elbow(name, size):
    """A quarter bend. The anchor is the corner, where the two axes meet; one leg comes in along
    +z, the other leaves along +y, and each ends in a pair of flanges ELBOW[size] from the corner:
    a run stops inside it."""
    m = M.Model(PREFIX + name)
    r, rho = BORE[size], BEND[size]
    arc = [(0.0, rho * (1.0 - math.cos(math.radians(t))), rho * (1.0 - math.sin(math.radians(t))))
           for t in (0.0, 30.0, 60.0, 90.0)]
    m.hose(arc, r, K.IRON)
    _pair(m, size, rho)
    with m.turned(("x", -90.0)):
        _pair(m, size, rho)
    return m


ELBOW = {size: BEND[size] + 2.0 for size in BEND}       # from a bend's corner to the end of its flanges


def _valve(name, size):
    """The stop valve in a straight run: a globe on the axis z (the anchor is its middle), a flanged
    port either way that ends VALVE[size] from the middle, and the works -- bonnet, brass stem, red
    handwheel -- out along +y."""
    m = M.Model(PREFIX + name)
    g = BORE[size] + 1.5
    m.ball((0.0, 0.0, 0.0), g, K.IRON_D, sides=8, layers=3)
    _port(m, size, g - 1.0, VALVE[size])
    with m.turned(("y", 180.0)):
        _port(m, size, g - 1.0, VALVE[size])
    _works(m, size, g - 1.0)
    return m


VALVE = {size: BORE[size] + 4.0 for size in BORE}       # half the length of a straight valve


def _valve_angle(name, size):
    """The angle stop valve, where a main turns as it comes up out of a floor: a globe at the
    corner (the anchor, where the two axes meet), one flanged port out along +z and one down along
    -y, each ending ANGLE from the corner, and the works out along -z, in line with the first port:
    the handwheel looks back along the pipe, one spoke upright. With the axis ANGLE above a floor
    the lower flanges stand on it."""
    m = M.Model(PREFIX + name)
    g = BORE[size] + 1.5
    m.ball((0.0, 0.0, 0.0), g, K.IRON_D, sides=8, layers=3)
    _port(m, size, g - 1.0, ANGLE)
    with m.turned(("x", 90.0)):
        _port(m, size, g - 1.0, ANGLE)
    with m.turned(("x", -90.0)):
        _works(m, size, g - 1.0, top=270.0)
    return m


ANGLE = 8.0             # from an angle valve's corner to the end of either port: half a block


def _bonnet():
    """The works of a stop valve that is let into a lagged main (site/powerhouse lays its steam main
    in whole blocks): only the works show. Mounted on a face of the main, the anchor on that face,
    everything out along +z: a plate with four bolts, then the works of the big valve, one spoke
    of the wheel along +y."""
    m = M.Model(PREFIX + "bonnet")
    m.box((-4.0, -4.0, 0.0), (4.0, 4.0, 1.0), K.IRON_D)
    for x in (-3.0, 3.0):
        for y in (-3.0, 3.0):
            K.rivet(m, (x, y, 1.0))
    with m.turned(("x", 90.0)):
        _works(m, "l", 0.0, top=90.0)
    return m


def _band():
    """A strap round a lagged main laid in whole blocks, over the joint between two of them. Mounted
    on a face of the main: the anchor is the middle of that face on the joint, the model's +z looks
    out of the face and its +y runs with the main. The strap goes all the way round, one texel
    proud, and is bolted together on the face it is mounted on."""
    m = M.Model(PREFIX + "band")
    h = 8.0
    m.box((-h - 1.0, -1.0, 0.0), (h + 1.0, 1.0, 1.0), K.IRON)
    for s in (-1.0, 1.0):
        m.box((s * h, -1.0, -2.0 * h), (s * (h + 1.0), 1.0, 0.0), K.IRON)
    m.box((-h - 1.0, -1.0, -2.0 * h - 1.0), (h + 1.0, 1.0, -2.0 * h), K.IRON_D)
    m.box((-1.5, -1.5, 1.0), (1.5, 1.5, 2.0), K.IRON_D)
    K.rivet(m, (0.0, 0.0, 2.0))
    return m


def _gauge():
    """The pressure gauge. The anchor is the tapping, on the pipe's skin; the stalk stands out along
    +y and the dial looks along +x. From the pipe up: the boss, one turn of small pipe (the siphon
    that keeps steam out of the works), the brass case, the cream dial with three phosphor marks,
    the needle."""
    m = M.Model(PREFIX + "gauge")
    m.tube("y", (0, 0), -0.5, 1.5, 1.25, K.IRON_D)
    m.ring("x", (0.0, 3.0, 0.0), 1.0, 1.0, 1.0, K.BRASS_D, sides=8)
    m.tube("y", (0, 0), 4.5, 5.25, 0.75, K.BRASS_D)
    yc = GAUGE_DIAL
    m.tube("x", (yc, 0), -1.25, 1.0, 3.0, K.BRASS)
    m.tube("x", (yc, 0), 1.0, 1.25, 2.25, DIAL, cap=DIAL)
    m.box((1.25, yc - 0.5, -0.5), (1.5, yc + 2.0, 0.5), NEEDLE, rot=("x", -40.0, (1.25, yc, 0.0)))
    for y, z in ((yc + 1.5, 0.0), (yc, 1.5), (yc, -1.5)):
        m.box((1.25, y - 0.5, z - 0.5), (1.4, y + 0.5, z + 0.5), MARK, emit=10, shade=False)
    m.box((1.25, yc - 0.5, -0.5), (1.6, yc + 0.5, 0.5), PIN)
    return m


GAUGE_DIAL = 8.25       # the middle of the gauge's dial above the tapping, in texels


def _clip(name, size):
    """A bracket that holds a main along a wall. Wall-mounted: the anchor is on the wall face
    behind the pipe's axis; the pipe runs along x with its axis STANDOFF[size] out. A plate riveted
    to the wall, a stem, and a strap round the pipe."""
    m = M.Model(PREFIX + name)
    r, d = BORE[size], STANDOFF[size]
    m.box((-2.0, -r - 2.0, 0.0), (2.0, r + 2.0, 0.75), K.IRON_D)
    for y in (-r - 1.0, r + 1.0):
        K.rivet(m, (0.0, y, 0.75))
    m.box((-0.75, -1.0, 0.75), (0.75, 1.0, d - r), K.IRON)
    m.ring("x", (0.0, 0.0, d), r + 0.5, 1.0, 2.0, K.IRON_D, sides=8)
    return m


STANDOFF = {"l": 5.0, "m": 4.0}         # a main along a wall: its axis this far off the face, in texels

SPEC = {
    "down": dict(build=_down),
    "down_hopper_left": dict(build=lambda: _hopper("down_hopper_left", -1.0)),
    "down_hopper_right": dict(build=lambda: _hopper("down_hopper_right", 1.0)),
    "down_clip": dict(build=_down_clip),
    "down_sleeve": dict(build=_down_sleeve),
    "main_l": dict(build=lambda: _main("main_l", BORE["l"])),
    "main_m": dict(build=lambda: _main("main_m", BORE["m"])),
    "flange_l": dict(build=lambda: _flange("flange_l", "l")),
    "flange_m": dict(build=lambda: _flange("flange_m", "m")),
    "plate_l": dict(build=lambda: _plate("plate_l", "l")),
    "plate_m": dict(build=lambda: _plate("plate_m", "m")),
    "elbow_l": dict(build=lambda: _elbow("elbow_l", "l")),
    "elbow_m": dict(build=lambda: _elbow("elbow_m", "m")),
    "valve_l": dict(build=lambda: _valve("valve_l", "l")),
    "valve_m": dict(build=lambda: _valve("valve_m", "m")),
    "valve_angle_l": dict(build=lambda: _valve_angle("valve_angle_l", "l")),
    "valve_angle_m": dict(build=lambda: _valve_angle("valve_angle_m", "m")),
    "bonnet": dict(build=_bonnet),
    "band": dict(build=_band),
    "gauge": dict(build=_gauge),
    "clip_l": dict(build=lambda: _clip("clip_l", "l")),
    "clip_m": dict(build=lambda: _clip("clip_m", "m")),
}
SCALE = {PREFIX + name: 1.0 for name in SPEC}


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + name: spec["build"]() for name, spec in SPEC.items()}


def models():
    return dict(_models())


# ---- placing --------------------------------------------------------------------------------------
def place(canvas, kind, pos, along="south", out="up", origin=(0, 0, 0), **opts):
    """A fitting on a run; returns 1. pos is the point of the pipe's axis where the fitting's anchor
    goes (a gauge: the point on the pipe's skin), `along` the way the model's +z points and `out`
    the way its +y points:

        flange_*        along: the pipe; out: any direction across it
        valve_*         along: the pipe; out: the stem and the wheel
        valve_angle_*   along: the level port, and the pipe that leaves by it; out: "up" (the other
                        port goes down, the wheel looks back against `along`)
        elbow_*         along: one leg; out: the other
        gauge           out: the stalk; the dial looks to the LEFT of someone who looks along
                        `along` with `out` overhead (out x along)"""
    return K.put(canvas, _models()[PREFIX + kind], pos, yaw=0.0, turns=_turns(along, out), origin=origin, **opts)


def mount(canvas, kind, pos, out="east", up="up", origin=(0, 0, 0), **opts):
    """A piece on a surface; returns 1. pos is on the surface, `out` the way the surface looks (the
    model's +z), `up` the way the model's +y points: "up" on a wall, any level direction on a floor
    or under a soffit; for a band, the way the main runs. The anchor is moved a hair off the
    surface, into the air."""
    n = DIRS[out]
    pos = tuple(pos[i] + n[i] * K.NUDGE for i in range(3))
    return K.put(canvas, _models()[PREFIX + kind], pos, yaw=0.0, turns=_turns(out, up), origin=origin, **opts)


def run(canvas, a, b, kind="main_l", lit=None, origin=(0, 0, 0)):
    """One straight length of pipe from a to b, two points of its axis; returns 1. kind is "main_l",
    "main_m" or "down". The entity stands at a, which must be in the air (it is lit from there);
    b may lie inside a fitting or a stone.

    lit    the side the pipe's light tone looks to. Left out: up for a level run, north for an
           upright one. Only runs along an axis can say; a slanted run is lit from above."""
    a = tuple(a[i] + origin[i] for i in range(3))
    b = tuple(b[i] + origin[i] for i in range(3))
    model = _models()[PREFIX + kind]
    d = tuple(b[i] - a[i] for i in range(3))
    along = _name(d)
    if along is None:
        nbt = M.between(model, a, b, length=RUN)
    else:
        if lit is None:
            lit = "north" if along in ("up", "down") else "up"
        dist = math.sqrt(sum(v * v for v in d))
        nbt = M.display(model, scale=(1.0, 1.0, dist * 16.0 / RUN), turns=_turns(along, lit))
    canvas.add_entity(a[0], a[1], a[2], nbt)
    return 1


def downpipe(canvas, corner, top, bottom, facing="east", side=1, origin=(0, 0, 0)):
    """A rainwater pipe in a re-entrant corner, from the cornice down into the plinth.

    corner   (x, z): the point of the plan where the face of the wall the pipe stands in front of
             meets the face of the return wall beside it
    facing   the way that wall looks
    side     1: the return wall stands to the right of someone who looks at the wall, -1: to the left
    top      y of the soffit the hopper hangs under (the cornice's row)
    bottom   y of the top of the stone the pipe goes into (the plinth's coping)

    The hopper fills the cell under the soffit; the pipe stands GAP clear of both walls. Where a
    course of stone crosses its way (the string course) the pipe goes through it, with a sleeve on
    the stone above and below; it ends in a sleeve on the plinth. Clips hold it about every
    CLIP_EVERY blocks; they are fixed to the return wall, which is solid all the way up (the wall
    behind the pipe is a window's edge for most of its height). Nothing is placed where the canvas
    has no walls or the hopper's cell is full. Returns the number of display entities."""
    out = DIRS[facing]
    right = _cross(DIRS["up"], out)                             # to the right of someone who looks at the wall
    back = tuple(int(side) * v for v in right)                  # towards the return wall
    clear = _name(tuple(-v for v in back))                      # the way the return wall looks
    off = (GAP + DOWN_R) / 16.0 + K.NUDGE
    ax, az = corner[0] + (out[0] - back[0]) * off, corner[1] + (out[2] - back[2]) * off     # the axis
    wx, wz = ax - out[0] * off, az - out[2] * off               # on the wall, behind the axis
    rx, rz = ax + back[0] * off, az + back[2] * off             # on the return wall, beside it
    ox, oy, oz = origin
    cx, cz = int(math.floor(ax)), int(math.floor(az))

    def solid(y):
        return _stone(canvas, cx + ox, y + oy, cz + oz)

    def held(y):
        return _stone(canvas, cx + back[0] + ox, int(math.floor(y)) + oy, cz + back[2] + oz)

    if solid(top - 1) or not solid(bottom - 1) or not _stone(canvas, cx - out[0] + ox, bottom + oy, cz - out[2] + oz):
        return 0
    n = mount(canvas, "down_hopper_" + ("right" if side > 0 else "left"), (wx, top - 0.5, wz), out=facing,
              origin=origin)
    head = top - 0.5 + HOPPER_SOCKET[0] / 16.0                  # the underside of the hopper's socket
    n += run(canvas, (ax, head + 1.5 / 16.0, az), (ax, bottom + 1.0 / 32.0, az), "down", lit=clear, origin=origin)
    n += mount(canvas, "down_sleeve", (ax, bottom, az), out="up", up=facing, origin=origin)
    lengths, start = [], float(bottom)                          # the free lengths between the stones
    for y in range(bottom, top - 1):
        if not solid(y):
            continue
        if y > start:
            lengths.append((start, float(y)))
            n += mount(canvas, "down_sleeve", (ax, y, az), out="down", up=facing, origin=origin)
        if not solid(y + 1):
            n += mount(canvas, "down_sleeve", (ax, y + 1, az), out="up", up=facing, origin=origin)
        start = y + 1.0
    if head > start:
        lengths.append((start, head))
    for lo, hi in lengths:
        count = max(1, int(round((hi - lo) / CLIP_EVERY)))
        for i in range(count):
            y = round((lo + (hi - lo) * (i + 0.5) / count) * 4.0) / 4.0
            if held(y):
                n += mount(canvas, "down_clip", (rx, y, rz), out=clear, origin=origin)
    return n


def corners():
    """The re-entrant corners of the east front, where an end pavilion or the middle one stands
    forward of a wing: [((x, z), side)] as downpipe() takes them, north to south. The pipe stands
    in front of the wing's wall, beside the pavilion's return."""
    out = []
    for k in range(1, S.N_BAYS):
        north, south = S.east_wall_x(k), S.east_wall_x(k + 1)
        if north == south:
            continue
        x, z = min(north, south) + 1.0, S.pilaster_z(k)         # the wing's face; the return wall's row
        out.append(((x, z + 1.0), 1) if north > south else ((x, float(z)), -1))
    return out


# Where the power house's main enters the building: the grating main/facade sets into the foot of the
# south end pavilion's corner pier (c206: facade.PIPE_INLET, the same numbers; A0, 11-14: the pipe
# goes into the plinth there and no riser climbs the east front). The main comes under the paving
# from the pipe bridge (c228: nothing of site/powerhouse stands in the two cells east of the grating).
INLET = (S.east_wall_x(S.N_BAYS) + S.DEPTH_PILASTER, S.GROUND, S.Z_SOUTH - 1)
INLET_GAUGE = 5.0       # along the main from the grating's face, in texels: the gauge's tapping,
INLET_VALVE = 15.0      # and the corner of the angle valve the main comes up into


def inlet(canvas, origin=(0, 0, 0)):
    """The main's last block and a half before it goes into the building, east of the grating INLET
    and at the middle of its height: the main comes up out of its trench into an angle stop valve
    that stands on the paving, its red handwheel looking east at the court; from the valve a short
    length runs west into a plate on the grating, and carries the pressure gauge, its dial to the
    south.

    Nothing is placed unless the grating is there, the two cells east of it are free and paved.
    Returns the number of display entities."""
    x, y, z = INLET
    ox, oy, oz = origin
    if canvas.name(x + ox, y + oy, z + oz) != B.IRON_GRATE:
        return 0
    for dx in (1, 2):
        if _stone(canvas, x + dx + ox, y + oy, z + oz) or not _stone(canvas, x + dx + ox, y - 1 + oy, z + oz):
            return 0
    face, ay, az = x + 1.0, y + ANGLE / 16.0, z + 0.5
    corner = face + INLET_VALVE / 16.0
    n = mount(canvas, "plate_l", (face, ay, az), out="east", origin=origin)
    n += run(canvas, (face + (PLATE_NECK - 1.0) / 16.0, ay, az), (corner - (ANGLE - 1.0) / 16.0, ay, az), "main_l",
             origin=origin)
    n += place(canvas, "gauge", (face + INLET_GAUGE / 16.0, ay + BORE["l"] / 16.0, az), along="west", out="up",
               origin=origin)
    n += place(canvas, "valve_angle_l", (corner, ay, az), along="west", out="up", origin=origin)
    return n


def dress(canvas, origin=(0, 0, 0)):
    """The family on the main building, on whatever the main line has built there: a downpipe in
    each of the four re-entrant corners of the east front, and the main's inlet at the south end.
    Returns the number of display entities."""
    n = 0
    for corner, side in corners():
        n += downpipe(canvas, corner, S.CORNICE, S.PLINTH[1] + 1, facing="east", side=side, origin=origin)
    return n + inlet(canvas, origin)


def build(canvas, origin=(0, 0, 0)):
    """What this package places in the master scene: dress(), once DRESS is on."""
    return dress(canvas, origin) if DRESS else 0
