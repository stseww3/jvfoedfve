"""machines/meridian -- the transit circle of the meridian hut (plan/ART-PLAN.md 7.2;
plan/parts/A5-machines.md 2.9; card plan/packages/machines/meridian-astrograph.md).

A telescope that can do one thing: tip about a level axis that lies east and west, and so sweep the
meridian from the north horizon over the zenith to the south one. What crosses the brass line in
the floor crosses its wires; the two great circles on the axis say how high. It stands in the
middle of the hut (site/outbuildings), under the slot in the roof:

  the piers    two stone piers cased in riveted iron plate, either side of the meridian, a brass
               bearing on each head. From each head a forked arm carries two reading microscopes
               to the rim of the circle beside it; a thermometer hangs on the casing.
  the tube     a cast cube in the middle; two cones of riveted plate bolted to it, the object glass
               in a brass cell at one end and the micrometer eyepiece at the other; the two halves
               of the axis bolted to its sides, cast cones that end in steel pivots.
  the circles  one either side of the tube, two and three quarter blocks across, as large as the
               hut's low roof lets them turn: a graduated brass band on six spokes.
  the lamp     a small brass lantern on the west pier, level with the axis: it shines through the
               hollow pivot onto the wires. The one light in the hut.

It is set on the pole star: due north, as high as the place's latitude (the evening's first
reading, which says whether the axis still lies east and west). The tube is as long as the axis
is high, less two texels, so it passes the floor when it is turned over.

One set with the great refractor (machines/scope, c344): tube plates a step lighter than the
castings, a riveted hoop over every lap, flanges with a ring of bolts, brass cells and graduated
brass circles on six spokes, bright steel shafts.

What the other lines read (scene coordinates; give the origin to have it added):

    meridian.axis()        the middle of the instrument: where the axis crosses the meridian
    meridian.eyepiece()    the middle of the eyepiece's end face
    meridian.sweep()       (centre, radius) of the ball the tube and the circles never leave
    meridian.lamp_cell()   the cell the lamp's light is offered in (LAMP_LEVEL)
    meridian.ALTITUDE      degrees the tube looks up, due north
    meridian.BRIGHTNESS    the light every piece is shown in, whatever cell it stands in

The pieces that turn are models of their own, each anchored on the axis: the tube and the two
circles turn together about their model's x (plan 7.1). This round they stand still (plan/parts/
motion.md 1: nobody is at the eyepiece).

The drawing vocabulary of this card's two instruments is here too (Draw and what follows it);
machines/astro reads it from this module.

    python -m scenes.obs.machines.meridian      the numbers above and the rules they are held to
"""
import functools
import math
import sys

import numpy as np

from artkit import models as M
from artkit.pixelart import Mat

from ..common import palette as P
from ..common import skeleton as S

PREFIX = "mach_meridian_"
BRIGHTNESS = (10, 7)            # (sky, block): the same as the great refractor's, for a room kept dark
LAMP_LEVEL = 4                  # the lantern's light source, rank 3 (the refractor's lamp is 4 too)

EAST, UP, SOUTH = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)
WORLD = (EAST, UP, SOUTH)


# ---- the drawing vocabulary of the two instruments (machines/astro reads it from here) ------------
class Riveted(Mat):
    """Plate with a row of rivet heads down the middle of a narrow face: a head is one light texel
    with a dark one in its shadow, `pitch` texels from the next. The rule of the great refractor's
    hoops and seams, so the two read as one make."""
    pitch = 3
    widest = 6          # a wider face is the field of a plate, not a lap

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


class Graduated(Mat):
    """The band of a divided circle or the head of a micrometer: every other texel along the band
    is a division, and every `long`-th division is cut a step deeper."""
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


def painted(cls, mat, tag, **more):
    """The palette's material `mat` painted the way of `cls`: its ramp, tone and bevel are kept."""
    out = cls.__new__(cls)
    out.__dict__.update(mat.__dict__)
    out.name = f"{mat.name}~{tag}"
    out._variants = {}
    out.__dict__.update(more)
    return out


def flat(name, step):
    """One flat tone of a ramp: glass, a dial, the inside of a hood."""
    return P.mat(name, kind="flat", base=step, bevel=0)


IRON, IRON_D = P.mat("iron"), P.mat("iron_dark")        # castings
PLATE = P.mat("iron", base=4)                           # rolled plate: a step lighter than the castings
STEEL = P.mat("iron", base=5)                           # bright shafts and pivots
BRASS, BRASS_D = P.mat("brass"), P.mat("brass_dark")
WOOD = P.mat("dark_wood")
IRON_STUD = painted(Riveted, IRON, "stud")
IRON_D_STUD = painted(Riveted, IRON_D, "stud")
PLATE_STUD = painted(Riveted, PLATE, "stud")
PLATE_SEAM = painted(Riveted, PLATE, "seam", pitch=4)
BRASS_STUD = painted(Riveted, BRASS_D, "stud")
BRASS_TICK = painted(Graduated, P.mat("brass", bevel=0), "tick")
IRON_TOOTH = painted(Graduated, P.mat("iron_dark", bevel=0), "tooth", long=0)
GLASS, GLASS_D = flat("night_glass", 2), flat("night_glass", 0)
HOOD = flat("iron", 0)
DIAL = flat("cream", 2)
GLOW = [flat("glow", i) for i in range(len(P.RAMPS["glow"]))]       # dark to light
HOOP_SEED = 7301                # hoops of one tube share their picture


class Draw:
    """A model drawn in texels. A piece shown at scale n is built of model units n texels long, so
    there are sixteen texels to the block whatever the scale; every length here is in texels."""

    def __init__(self, name, scale, anchor=(0.0, 0.0, 0.0)):
        self.scale = float(scale)
        self.model = M.Model(name, px=self.scale, anchor=self.units(anchor))

    def units(self, v):
        return tuple(c / self.scale for c in v)

    def box(self, lo, hi, mat, rot=None, **kw):
        if rot is not None:
            rot = (rot[0], rot[1], self.units(rot[2]))
        self.model.box(self.units(lo), self.units(hi), mat, rot=rot, **kw)

    def tube(self, axis, c, a0, a1, radius, mat, **kw):
        self.model.tube(axis, self.units(c), a0 / self.scale, a1 / self.scale, radius / self.scale, mat, **kw)

    def taper(self, axis, c, a0, a1, r0, r1, mat, **kw):
        self.model.taper(axis, self.units(c), a0 / self.scale, a1 / self.scale, r0 / self.scale,
                         r1 / self.scale, mat, **kw)

    def ring(self, axis, centre, radius, thick, width, mat, **kw):
        self.model.ring(axis, self.units(centre), radius / self.scale, thick / self.scale,
                        width / self.scale, mat, **kw)

    def ball(self, centre, radius, mat, **kw):
        self.model.ball(self.units(centre), radius / self.scale, mat, **kw)

    def rod(self, a, b, radius, mat, **kw):
        self.model.rod(self.units(a), self.units(b), radius / self.scale, mat, **kw)

    def bar(self, a, b, across, deep, mat, **kw):
        """A flat bar from a to b: `across` is its size along x where it stands upright, `deep`
        its size along z."""
        kw.setdefault("grain", "y")
        with self.model.aimed(self.units(a), self.units(b), "y") as length:
            self.model.box((-across / self.scale / 2.0, 0.0, -deep / self.scale / 2.0),
                           (across / self.scale / 2.0, length, deep / self.scale / 2.0), mat, **kw)

    def turned(self, *turns, about=(0.0, 0.0, 0.0)):
        return self.model.turned(*turns, about=self.units(about))

    def along(self, a, b):
        """`with d.along(a, b) as length:` a frame whose origin is a and whose y runs to b; the
        length is in texels."""
        return _Along(self, a, b)


class _Along:
    def __init__(self, draw, a, b):
        self.draw, self.a, self.b = draw, a, b

    def __enter__(self):
        self.group = self.draw.model.aimed(self.draw.units(self.a), self.draw.units(self.b), "y")
        return self.group.__enter__() * self.draw.scale

    def __exit__(self, *exc):
        return self.group.__exit__(*exc)


def spokes(d, axis, centre, r0, r1, n, mat, wide=2.0, thick=1.0, start=0.0):
    """n flat spokes about `axis` through `centre`, from radius r0 out to r1."""
    k = M.AXES.index(axis)
    o1, o2 = [i for i in range(3) if i != k]
    lo, hi = list(centre), list(centre)
    lo[k], hi[k] = centre[k] - thick / 2.0, centre[k] + thick / 2.0
    lo[o1], hi[o1] = centre[o1] + r0, centre[o1] + r1
    lo[o2], hi[o2] = centre[o2] - wide / 2.0, centre[o2] + wide / 2.0
    for i in range(n):
        d.box(lo, hi, mat, rot=(axis, start + 360.0 * i / n, tuple(centre)), grain=M.AXES[o1])


def circle(d, axis, centre, radius, band=3.0, width=1.5, hub=3.0, n=6, sides=16, start=30.0, rim=0.0):
    """A divided circle about `axis` through `centre`: a graduated brass band of outer radius
    `radius` on n spokes and a hub. rim is the size of a plain stiffening ring inside the band."""
    d.ring(axis, centre, radius - band / 2.0, band, width, BRASS_TICK, sides=sides)
    inner = radius - band
    if rim:
        d.ring(axis, centre, inner - rim / 2.0 + 0.25, rim, width + 1.0, BRASS_D, sides=sides)
        inner -= rim - 0.25
    spokes(d, axis, centre, hub - 0.5, inner + 0.5, n, BRASS_D, wide=max(1.5, radius / 10.0),
           thick=width * 0.7, start=start)
    k = M.AXES.index(axis)
    c = [v for i, v in enumerate(centre) if i != k]
    d.tube(axis, c, centre[k] - width, centre[k] + width, hub, BRASS_D, sides=8 if hub < 4.0 else 12)


def corner_irons(d, half, y0, y1, about=(0.0, 0.0), mat=None, wide=2.0, proud=0.5):
    """An angle iron riveted up each corner of a square upright of half size `half` that stands on
    the point `about` = (x, z)."""
    mat = mat or IRON_STUD
    ox, oz = about
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            x0, x1 = sorted((ox + sx * (half + proud), ox + sx * (half + proud - wide)))
            z0, z1 = sorted((oz + sz * (half + proud), oz + sz * (half + proud - wide)))
            d.box((x0, y0, z0), (x1, y1, z1), mat, grain="y")


def upright(d, y0, y1, half, about=(0.0, 0.0), mat=None, band=1.5, irons=True):
    """One section of a square cast upright from y0 to y1, a bolted flange at its head `band`
    texels deep and half a texel proud, angle irons up its corners."""
    ox, oz = about
    d.box((ox - half, y0, oz - half), (ox + half, y1 - band, oz + half), mat or IRON, grain="y")
    if irons:
        corner_irons(d, half, y0, y1 - band, about)
    if band:
        d.box((ox - half - 0.5, y1 - band, oz - half - 0.5), (ox + half + 0.5, y1, oz + half + 0.5), IRON_STUD)


def pose(frame):
    """Yaw and turns for artkit.models.display that carry a model's x, y and z onto the three
    directions of `frame` (unit vectors, right-handed): the model is rolled about its z, tipped
    about x and then swung about the upright."""
    x, y, z = frame
    tip = -math.asin(max(-1.0, min(1.0, z[1])))
    swing = math.atan2(z[0], z[2])
    roll = math.atan2(x[1], y[1])
    return -math.degrees(swing), (("z", math.degrees(roll)), ("x", math.degrees(tip)))


def put(canvas, model, at, frame, scale, origin=(0, 0, 0), brightness=BRIGHTNESS):
    """Stand one piece with its anchor on `at`, its axes along `frame`. Returns 1, the entity."""
    yaw, turns = pose(frame)
    x, y, z = (at[i] + origin[i] for i in range(3))
    canvas.add_entity(x, y, z, M.display(model, yaw=yaw, turns=turns, scale=scale, brightness=brightness))
    return 1


def corners(model, at, frame, scale):
    """The corners of every box of a placed model, in scene coordinates: [(part index, point)]."""
    k = scale / 16.0
    for i, part in enumerate(model.parts):
        c = [(part["lo"][j] + part["hi"][j]) / 2.0 for j in range(3)]
        h = [(part["hi"][j] - part["lo"][j]) / 2.0 for j in range(3)]
        q = part["rot"][0] if part["rot"] else M.IDENT
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    v = M._qrot(q, (sx * h[0], sy * h[1], sz * h[2]))
                    p = list(at)
                    for j in range(3):
                        off = (c[j] + v[j] - model.anchor[j]) * k
                        for n in range(3):
                            p[n] += frame[j][n] * off
                    yield i, tuple(p)


def size_findings(models, scales):
    """16 texels to the block and no piece larger than its scale allows: the findings as lines."""
    out = []
    for name, model in models.items():
        scale = scales[name]
        if model.px != scale:
            out.append(f"{name}: drawn at {model.px:g} texels to the unit, shown at scale {scale:g}")
        lo, hi = model.bounds()
        span = max(hi[i] - lo[i] for i in range(3))
        if span > 48.0 + 1e-6:
            out.append(f"{name}: {span:g} units across, a model holds 48")
    return out


# ---- where it stands (blocks, scene coordinates) ----------------------------------------------------
AXIS_Y = 32.0                   # texels: the axis over the floor (two blocks, site/outbuildings HUT_AXIS)
PIER_OFF = 32.0                 # the piers' middles from the meridian (HUT_PIERS)
CIRCLE_OFF = 14.5               # the circles' planes from the meridian
CIRCLE_R = 22.0                 # two and three quarter blocks across: two texels under the hut's roof
HALF = 30.0                     # the tube from the axis to either end: it passes the floor
ALTITUDE = S.LATITUDE           # the pole star: due north, as high as the latitude
TUBE_SCALE = CIRCLE_SCALE = PIER_SCALE = 2.0
LAMP_SCALE = 1.0
LAMP_PIER = -1                  # the lantern hangs on the west pier
HUT_ROOF = 3.5                  # blocks: the underside of the hut's roof over the floor, off the meridian

_A = math.radians(ALTITUDE)
SIGHT = (0.0, math.sin(_A), -math.cos(_A))              # the way the tube looks: north and up
OVER = (0.0, math.cos(_A), math.sin(_A))                # square to it in the meridian, upwards
TUBE_FRAME = (EAST, OVER, tuple(-v for v in SIGHT))     # x the axis, z down the tube to the eyepiece
WEST_FRAME = WORLD                                      # the piers are drawn with their x towards the tube
EAST_FRAME = ((-1.0, 0.0, 0.0), UP, (0.0, 0.0, -1.0))


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def axis(origin=(0, 0, 0)):
    """The middle of the instrument: where its axis crosses the meridian, over the hut's middle."""
    cx, cz = S.MERIDIAN_HUT["centre"]
    return _add((cx + 0.5, S.GROUND + AXIS_Y / 16.0, cz + 0.5), origin)


def piers(origin=(0, 0, 0)):
    """The middle of each pier's foot on the floor: west, east."""
    x, _, z = axis(origin)
    return [(x + sgn * PIER_OFF / 16.0, origin[1] + float(S.GROUND), z) for sgn in (-1.0, 1.0)]


def eyepiece(origin=(0, 0, 0)):
    return _add(axis(origin), _mul(SIGHT, -HALF / 16.0))


def objective(origin=(0, 0, 0)):
    return _add(axis(origin), _mul(SIGHT, HALF / 16.0))


def sweep(origin=(0, 0, 0)):
    """(centre, radius) of the ball that holds the tube and the circles however they are turned."""
    return axis(origin), (max(HALF, CIRCLE_R) + 1.0) / 16.0


def lamp_cell(origin=(0, 0, 0)):
    """The cell the lantern's glass is in."""
    x, y, z = _add(piers()[0 if LAMP_PIER < 0 else 1], origin)
    return (int(math.floor(x + LAMP_PIER * LAMP_OUT / 16.0)), int(math.floor(y + AXIS_Y / 16.0)),
            int(math.floor(z)))


# ---- the tube -----------------------------------------------------------------------------------------
CUBE = 6.5                      # half the cast cube in the middle
CONE = (8.0, 24.0, 6.0, 4.75)   # each half of the tube: from, to (texels from the axis), radius at both
PIVOT = (21.0, 31.0, 1.5)       # each steel pivot: from, to (texels from the meridian), radius


def _tube():
    d = Draw(PREFIX + "tube", TUBE_SCALE)
    c0, c1, r0, r1 = CONE
    d.box((-CUBE, -CUBE, -CUBE), (CUBE, CUBE, CUBE), IRON_D)
    for sgn in (-1.0, 1.0):
        # a brass cover on the cube's two free faces (the lamp's mirror is behind one)
        d.tube("y", (0.0, 0.0), sgn * CUBE, sgn * (CUBE + 0.75), 4.0, BRASS, sides=8)
        d.tube("y", (0.0, 0.0), sgn * (CUBE + 0.75), sgn * (CUBE + 1.5), 1.5, BRASS_D, sides=8)
        # half of the axis: a bolted flange, a cast cone, a brass collar, the steel pivot
        d.tube("x", (0.0, 0.0), sgn * CUBE, sgn * c0, 6.25, IRON_D_STUD, sides=12, seed=HOOP_SEED + 1)
        d.taper("x", (0.0, 0.0), sgn * c0, sgn * PIVOT[0], 5.0, 3.0, IRON, sides=12, steps=4)
        d.tube("x", (0.0, 0.0), sgn * (PIVOT[0] - 0.5), sgn * (PIVOT[0] + 1.0), 3.5, BRASS_D, sides=8)
        d.tube("x", (0.0, 0.0), sgn * (PIVOT[0] + 1.0), sgn * PIVOT[1], PIVOT[2], STEEL, sides=8)
        # half of the tube: a bolted flange, a cone of plate, one riveted hoop over its lap
        d.tube("z", (0.0, 0.0), sgn * CUBE, sgn * c0, 7.25, IRON_D_STUD, sides=12, seed=HOOP_SEED + 1)
        d.taper("z", (0.0, 0.0), sgn * c0, sgn * c1, r0, r1, PLATE, sides=12, steps=4)
        d.tube("z", (0.0, 0.0), sgn * 14.5, sgn * 17.5, 6.25, PLATE_STUD, sides=12, seed=HOOP_SEED)
    # the object glass: a brass cell with a ring of screws, the dark glass inside its lip
    d.tube("z", (0.0, 0.0), -c1 - 5.0, -c1, 5.5, BRASS, sides=12)
    d.tube("z", (0.0, 0.0), -c1 - 3.5, -c1 - 1.5, 5.75, BRASS_STUD, sides=12, seed=HOOP_SEED + 2)
    d.tube("z", (0.0, 0.0), -c1 - 5.5, -c1 - 5.0, 4.5, GLASS, sides=12, cap=GLASS)
    d.tube("z", (0.0, 0.0), -c1 - 5.6, -c1 - 5.5, 2.0, GLASS_D, sides=8, cap=GLASS_D)
    d.ring("z", (0.0, 0.0, -c1 - 5.5), 5.0, 1.5, 1.0, BRASS_D, sides=16)
    # the eye end: a tail plate, the micrometer box with a divided head either side, the eyepiece
    d.tube("z", (0.0, 0.0), c1, c1 + 1.5, 5.5, IRON_D_STUD, sides=12, seed=HOOP_SEED + 2)
    d.box((-4.5, -3.5, c1 + 1.5), (4.5, 3.5, c1 + 4.0), BRASS_D)
    d.tube("x", (0.0, c1 + 2.75), -6.5, 6.5, 0.75, STEEL, sides=4)
    for sgn in (-1.0, 1.0):
        d.tube("x", (0.0, c1 + 2.75), sgn * 6.0, sgn * 8.0, 2.0, BRASS_TICK, sides=8)
    d.tube("z", (0.0, 0.0), c1 + 4.0, c1 + 5.5, 1.75, BRASS, sides=8)
    d.tube("z", (0.0, 0.0), c1 + 5.5, HALF, 2.25, BRASS_D, sides=8, cap=GLASS_D)
    # the two finding circles on the eye end, by which the tube is set to a star's height
    for sgn in (-1.0, 1.0):
        d.tube("x", (0.0, 20.0), sgn * 4.75, sgn * 5.75, 3.5, BRASS_TICK, sides=8)
        d.tube("x", (0.0, 20.0), sgn * 5.75, sgn * 6.5, 1.25, BRASS_D, sides=8)
    return d.model


def _circle():
    d = Draw(PREFIX + "circle", CIRCLE_SCALE)
    circle(d, "x", (0.0, 0.0, 0.0), CIRCLE_R, band=3.5, width=1.5, hub=4.75, n=6, sides=24, start=0.0, rim=1.5)
    d.tube("x", (0.0, 0.0), -2.5, 2.5, 3.5, BRASS, sides=8)
    return d.model


# ---- the piers ------------------------------------------------------------------------------------------
PIER = [                        # the casing's sections: y0, y1, half size (texels)
    (3.0, 13.5, 7.0),
    (13.5, 22.5, 6.5),
    (22.5, 27.0, 6.0),
]
PIER_CAP = (27.0, 28.5, 7.0)
SCOPE_AT = 20.0                 # the reading microscopes look at the band this far from the axis
SCOPE_ANGLE = 45.0              # ... and this many degrees either side of straight up
ARM_X = 5.0                     # the plane of the forked arm, texels from the pier's middle towards the tube


def _microscope(d, y, z):
    """A reading microscope along x at (y, z): the eye end at the pier, the glass at the circle."""
    d.tube("x", (y, z), ARM_X - 2.0, ARM_X + 8.5, 1.25, BRASS, sides=8)
    d.tube("x", (y, z), ARM_X + 8.5, ARM_X + 10.0, 0.9, BRASS_D, sides=8, cap=GLASS_D)
    d.tube("x", (y, z), ARM_X - 3.5, ARM_X - 2.0, 0.9, BRASS_D, sides=8, cap=GLASS_D)
    d.box((ARM_X + 2.0, y - 1.75, z - 1.75), (ARM_X + 4.5, y + 1.75, z + 1.75), BRASS_D)
    d.tube("y", (ARM_X + 3.25, z), y + 1.75, y + 3.25, 1.0, BRASS_TICK, sides=8)


def _pier():
    d = Draw(PREFIX + "pier", PIER_SCALE)
    # a cast foot, the casing in three bolted sections with angle irons up the corners, a cap
    d.box((-8.0, 0.0, -8.0), (8.0, 3.0, 8.0), IRON_D_STUD)
    for y0, y1, half in PIER:
        upright(d, y0, y1, half)
    # a thermometer on the casing (the air's warmth goes down beside every reading): a brass
    # plate, the dark tube up its middle, the bulb at the foot
    y0, y1, half = PIER[1]
    d.box((-1.5, y0 + 1.0, half), (1.5, y1 - 2.0, half + 0.5), BRASS, grain="y")
    d.box((-0.5, y0 + 2.5, half + 0.5), (0.5, y1 - 2.5, half + 0.75), GLASS_D)
    d.box((-1.0, y0 + 1.5, half + 0.5), (1.0, y0 + 3.0, half + 1.0), STEEL)
    y0, y1, half = PIER_CAP
    d.box((-half, y0, -half), (half, y1, half), IRON_D)
    # the bearing on the side of the tube: a brass block with two cheeks, the pivot lies between them
    rest = AXIS_Y - PIVOT[2] - 0.25
    d.box((0.5, y1, -3.5), (7.0, rest, 3.5), BRASS_D)
    for sgn in (-1.0, 1.0):
        a, b = sorted((sgn * (PIVOT[2] + 0.25), sgn * 3.5))
        d.box((0.5, rest, a), (7.0, AXIS_Y + 1.5, b), BRASS)
    # the forked arm: two flat bars from the cap to the rim of the circle, a microscope on each
    rise = SCOPE_AT * math.cos(math.radians(SCOPE_ANGLE))
    for sgn in (-1.0, 1.0):
        top = (ARM_X, AXIS_Y + rise, sgn * SCOPE_AT * math.sin(math.radians(SCOPE_ANGLE)))
        d.bar((ARM_X, y1 - 0.5, sgn * 5.0), top, 2.0, 3.0, IRON_D)
        d.box((ARM_X - 1.5, y1 - 0.5, sgn * 5.0 - 2.0), (ARM_X + 1.5, y1 + 1.5, sgn * 5.0 + 2.0), IRON_STUD)
        _microscope(d, top[1], top[2])
    return d.model


# ---- the lamp ---------------------------------------------------------------------------------------------
LAMP_OUT = 10.5                 # the lantern's middle, texels from the pier's middle, away from the tube


def _lamp():
    """The lantern that lights the wires: on a bracket outside the pier, level with the axis, its
    bull's eye turned to the hollow pivot. Drawn in the pier's frame and anchored on the pier's
    foot, so it stands wherever a pier does."""
    d = Draw(PREFIX + "lamp", LAMP_SCALE)
    x = -LAMP_OUT
    d.box((x - 1.0, 26.0, -1.5), (-6.0, 27.5, 1.5), IRON_D)
    d.tube("y", (x, 0.0), 27.5, 29.0, 2.75, BRASS_D, sides=8)
    d.tube("y", (x, 0.0), 29.0, 34.5, 2.25, BRASS, sides=8)
    d.taper("y", (x, 0.0), 34.5, 37.0, 2.75, 1.25, HOOD, sides=8, steps=2)
    d.tube("y", (x, 0.0), 37.0, 37.75, 1.75, IRON_D, sides=8)
    # the bull's eye towards the pivot, and a slit of glass towards the door
    d.tube("x", (AXIS_Y, 0.0), x + 2.0, x + 3.0, 2.0, BRASS_D, sides=8)
    d.tube("x", (AXIS_Y, 0.0), x + 3.0, x + 3.5, 1.5, GLOW[3], sides=8, cap=GLOW[4], emit=15, shade=False)
    d.box((x - 1.0, 30.25, 2.25), (x + 1.0, 33.75, 2.5), GLOW[2], emit=15, shade=False,
          faces={"s": GLOW[3]})
    return d.model


# ---- the package --------------------------------------------------------------------------------------------
SCALE = {PREFIX + "tube": TUBE_SCALE, PREFIX + "circle": CIRCLE_SCALE, PREFIX + "pier": PIER_SCALE,
         PREFIX + "lamp": LAMP_SCALE}


@functools.lru_cache(maxsize=None)
def _built():
    return {m.name: m for m in (_tube(), _circle(), _pier(), _lamp())}


def models():
    return dict(_built())


def placed():
    """What build() stands: [(model name, anchor in scene coordinates, frame, scale)]."""
    a = axis()
    west, east = piers()
    out = [("pier", west, WEST_FRAME, PIER_SCALE), ("pier", east, EAST_FRAME, PIER_SCALE),
           ("tube", a, TUBE_FRAME, TUBE_SCALE)]
    out += [("circle", _add(a, (sgn * CIRCLE_OFF / 16.0, 0.0, 0.0)), TUBE_FRAME, CIRCLE_SCALE) for sgn in (-1.0, 1.0)]
    out.append(("lamp", west if LAMP_PIER < 0 else east, WEST_FRAME if LAMP_PIER < 0 else EAST_FRAME, LAMP_SCALE))
    return [(PREFIX + name, at, frame, scale) for name, at, frame, scale in out]


def build(canvas, origin=(0, 0, 0), lamp=True, brightness=BRIGHTNESS):
    """Stand the transit circle in the meridian hut. Returns the number of display entities.

    lamp=False leaves the lantern's light source out (the lantern itself stays).
    """
    built = _built()
    n = 0
    for name, at, frame, scale in placed():
        n += put(canvas, built[name], at, frame, scale, origin, brightness)
    if lamp:
        try:
            from ..sky import _lightkit as L
        except ImportError:
            L = None
        if L is not None:
            L.suggest(canvas, lamp_cell(origin), LAMP_LEVEL, "machines/meridian:lamp", rank=3)
    return n


# ---- the rules the numbers are held to ---------------------------------------------------------------------
def _hut_clear(p):
    """Is a point inside the hut's room (site/outbuildings: clear from wall to wall, x 32..38 and
    z -33..-27, 3.5 high under the flat roof, open to the sky over the meridian's own column)?"""
    cx, cz = S.MERIDIAN_HUT["centre"]
    h = S.MERIDIAN_HUT["size"] // 2
    x, y, z = p
    if not (cx - h + 1 <= x <= cx + h and cz - h + 1 <= z <= cz + h and y >= S.GROUND):
        return False
    d = abs(int(math.floor(x)) - cx)
    return d == 0 or y <= S.GROUND + HUT_ROOF


def check():
    """What can be told without a picture; returns the findings as lines (none is good)."""
    out = size_findings(_built(), SCALE)
    built = _built()
    # 1. nothing of it stands in the hut's walls, floor or roof
    for name, at, frame, scale in placed():
        bad = [p for _, p in corners(built[name], at, frame, scale) if not _hut_clear(p)]
        if bad:
            worst = min(bad, key=lambda p: p[1])
            out.append(f"{name}: {len(bad)} corners outside the hut's room, e.g. "
                       f"({worst[0]:.2f}, {worst[1]:.2f}, {worst[2]:.2f})")
    # 2. the tube passes the floor and the piers when it is turned right over
    if HALF >= AXIS_Y:
        out.append(f"tube: {HALF:g} texels from the axis to its end, the axis is {AXIS_Y:g} over the floor")
    if CIRCLE_R >= AXIS_Y:
        out.append(f"circle: radius {CIRCLE_R:g} texels, the axis is {AXIS_Y:g} over the floor")
    inner = PIER_OFF - 8.0
    if CIRCLE_OFF + 1.5 >= inner or CIRCLE_OFF - 1.5 <= CONE[2] + 1.25:
        out.append("circle: it does not turn freely between the tube and the pier")
    if not PIER_OFF - 7.0 < PIVOT[1] < PIER_OFF:
        out.append(f"pivot: it ends {PIVOT[1]:g} texels from the meridian, the bearing is from "
                   f"{PIER_OFF - 7.0:g} to {PIER_OFF - 0.5:g}")
    # 3. the microscopes look at the graduated band, and stop short of it
    if not CIRCLE_R - 3.5 <= SCOPE_AT <= CIRCLE_R:
        out.append(f"microscopes: they look {SCOPE_AT:g} texels from the axis, the band is from "
                   f"{CIRCLE_R - 3.5:g} to {CIRCLE_R:g}")
    if PIER_OFF - (ARM_X + 10.0) <= CIRCLE_OFF + 1.25:
        out.append("microscopes: they reach into the circle")
    # 4. the tube looks out through the slot: the sight line leaves the hut over the meridian's column
    cx, _ = S.MERIDIAN_HUT["centre"]
    p = objective()
    while p[1] < S.GROUND + 6.0:
        p = _add(p, _mul(SIGHT, 0.25))
        if int(math.floor(p[0])) != cx:
            out.append(f"sight: the line leaves the meridian's column at ({p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f})")
            break
    # 5. the site line's numbers, when its outbuildings are in the tree
    try:
        from ..site import outbuildings
    except ImportError:
        outbuildings = None
    if outbuildings is not None:
        theirs = getattr(outbuildings, "HUT_AXIS", None)
        if theirs is not None and any(abs(a - b) > 1e-6 for a, b in zip(theirs, axis())):
            out.append(f"axis: site/outbuildings gives {theirs}, the instrument stands on {axis()}")
        cells = getattr(outbuildings, "HUT_PIERS", None)
        mine = [tuple(int(math.floor(v)) for v in p) for p in piers()]
        if cells is not None and [tuple(c) for c in cells] != mine:
            out.append(f"piers: site/outbuildings gives {cells}, the piers stand in {mine}")
    return out


def report():
    lines = [f"axis {axis()}, piers {piers()}",
             f"tube: looks north, {ALTITUDE:g} degrees up; objective {tuple(round(v, 2) for v in objective())}, "
             f"eyepiece {tuple(round(v, 2) for v in eyepiece())}",
             f"sweep: centre {sweep()[0]}, radius {sweep()[1]:.2f}",
             f"lamp: cell {lamp_cell()}, level {LAMP_LEVEL}",
             f"{len(placed())} display entities"]
    for name, model in _built().items():
        lo, hi = model.bounds()
        lines.append(f"  {name}: scale {SCALE[name]:g}, {len(model.parts)} boxes, "
                     + " x ".join(f"{(hi[i] - lo[i]) * model.px:.1f}" for i in range(3)) + " texels")
    return lines


if __name__ == "__main__":
    findings = check()
    if "check" not in sys.argv[1:]:
        print("\n".join(report()))
    print("self-check: " + ("; ".join(findings) if findings else
                            "sizes, the room, the turn over the floor, the circles, the microscopes, the slot -- all good"))
    sys.exit(1 if findings else 0)
