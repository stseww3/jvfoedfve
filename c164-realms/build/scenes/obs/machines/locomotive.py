"""machines/locomotive: the rack locomotive that pushes the car up from the cloud (plan/round2.md,
"the train is the opening"; plan/packages/machines/locomotive.md).

A small tank engine for a rack line, three and a half blocks long: two axles, outside cylinders at
the uphill end, a cog wheel between the frames that climbs the rack, side tanks, an open-backed cab
at the downhill end. The boiler lies TILT degrees nose down on the frames, as a rack engine's does:
on the incline it comes level. The engine does not turn round: its chimney always leads uphill,
towards the car it pushes, and its front beam carries one sprung buffer in the middle that bears on
the car's end beam (no coupling: a rack engine pushes).

The engine's own frame, in which every number of this module is given (texels, 16 to the block):
    x   along the track, 0 in the middle of the engine's length; -x is uphill (the chimney, the car),
        +x downhill (the cab)
    y   up from the upper face of the rails
    z   across the track, 0 on its centre line; with yaw 0 the frame is the world's (x east, z south)

What it is made of (PARTS): one display entity for each, all of them standing on points of the
engine's middle plane, so that a pose is an offset (x, y) and a turn about z.
    body        everything that does not move                              (drawn at scale 2)
    fire        the glow of the firehole, on the cab floor and under the ashpan: a small model of
                its own whose picture flickers by itself (artkit.pixelart.shimmer)
    wheels      a pair of wheels on their axle, twice: they roll
    pinion      the cog wheel on its axle, with the two brake drums: it rolls on the rack's pitch line
    conrod      the two connecting rods, from the crossheads to the pins of the rear wheels
    crosshead   the two crossheads with their piston rods: they slide between the bars
    coupling    the two coupling rods from pin to pin: they go round with the pins and stay level
Left and right cranks stand alike (a real engine's are a quarter turn apart), so that the rods of
both sides are one model each.

pose(run) gives where every part lies when the engine has run so many blocks uphill; place() puts
the engine down in any pose and hands its parts to whatever moves it:
    car=    motion's travel (MK.travel(...).car("loco", ...)): the pieces are carried, the wheels and
            the cog roll with the way run. Until travel has rods (a2: the next step) the rods and
            the crossheads are left off a travelling engine, for a rod that stood still on a
            turning wheel would be seen at once
    stand=  the engine runs on the spot, wheels, cog, rods and crossheads driven by the loop
            (MK.spin, MK.crank): the test scene's proof of the running gear
    neither: it stands still, complete.

For the people who hang things on it (smoke, sound, lamps), in blocks in the engine's frame:
CHIMNEY, CYLINDERS, SAFETY_VALVE, WHISTLE, HEADLAMP, FIREHOLE, and REV, the blocks run for one turn
of the driving wheels (two beats of each cylinder: four puffs).
"""
import functools
import math

import numpy as np

from artkit import models as M
from artkit import pixelart as PA

from ..common import palette as P
from ..motion import _kit as MK
from ..props import _kit as K           # read only: tones, the hand-over of light sources, settle()
from ..props import signs               # read only: the station emblem's standard figure
from ..site import _rail as RAIL        # read only: the line
from . import _powerkit as PW           # the machines' drawing frame (a model drawn in texels at any scale)

PREFIX = "mach_loco_"
TEXEL = 1.0 / 16.0
TAG = "c164_loco"

# --- the numbers (texels in the engine's frame) -----------------------------------------------------
LENGTH = 56.0                           # over the buffer and the rear beam: 3.5 blocks
HALF = LENGTH / 2.0
NOSE = 6.0                              # the buffer stands so far before the front beam: on straight track
#                                         that is the gap to the car, and in the station's kink (18 degrees
#                                         between car and engine) the beam's inner corner still clears the car
FRONT = -HALF + NOSE                    # -22: the front beam's face
REAR = HALF                             # 28: the rear beam's face
WHEEL_R = 8.0                           # the wheels: a block across
AXLES = (-9.0, 15.0)                    # x of the two axles; the rear one is driven
AXLE_Y = WHEEL_R
GAUGE = 16.0                            # the wheels' middle planes: the middle of a rail (cable #86086)
CRANK_R = 4.0                           # from the axle to the crank pin
ROD = 19.5                              # the connecting rod, from pin to pin
CYL = (-20.0, -11.0)                    # the cylinders, from the front cover to the back one
CYL_Z = 19.75                           # their axis, and the middle plane of the connecting rods
CYL_R = 2.5
BARS = (CYL[1], 2.0)                    # the slide bars, from the back cover to the motion bracket
# The cog wheel: its teeth' tips reach 1.5 over the rails, down between the rungs of cable's ladder
# rack; RUNG is the rack's pitch, which the cog's pitch circle rolls on.
RUNG = 4.0
TEETH = 8
PITCH_R = TEETH * RUNG / (2.0 * math.pi)                # 5.09
TIP_R = 5.75
PINION = ((AXLES[0] + AXLES[1]) / 2.0, 1.5 + TIP_R)     # (3, 7.25): its axle, between the two others
PLATE_Y = 17.5                          # the running plate's upper face
BOILER = (-19.5, 27.5)                  # the middle of the smokebox's front: the boiler turns about it
TILT = 9.0                              # degrees the boiler lies nose down
TANK = (-7.0, 10.0)                     # the side tanks, x
CAB = (10.0, 26.0)                      # the cab, from the spectacle plate to the back sheet
SIDE = 21.0                             # half the width over tanks and cab
WAIST = 33.5                            # the cab's side sheets end here; open above, to the eaves
EAVES = 46.0
FIRE_X = 17.0                           # the firebox's back, in the cab
FIREHOLE_Y = 24.0


def _tilted(u, v, z=0.0):
    """A point of the boiler, given along it (u, from the smokebox's front) and square to it (v),
    as a point of the engine's frame."""
    a = math.radians(TILT)
    return (BOILER[0] + u * math.cos(a) - v * math.sin(a), BOILER[1] + u * math.sin(a) + v * math.cos(a), z)


def _blocks(p):
    return tuple(round(v * TEXEL, 4) for v in p)


# --- for smoke, sound and lamps: points in blocks in the engine's frame ------------------------------
CHIMNEY_U, CHIMNEY_TOP = 5.0, 23.25
CHIMNEY = _blocks(_tilted(CHIMNEY_U, CHIMNEY_TOP))              # the middle of the chimney's mouth
CHIMNEY_LEAN = TILT                                             # it leans so far forward on level track
CYLINDERS = tuple(_blocks((CYL[0] + 2.0, AXLE_Y - CYL_R - 1.0, CYL_Z * s)) for s in (-1.0, 1.0))   # the drain cocks
SAFETY_VALVE = _blocks(_tilted(27.0, 11.25))                    # the top of the valves
WHISTLE = _blocks(_tilted(29.0, 13.0, 4.0))                     # its mouth
HEADLAMP = _blocks(_tilted(-1.6, 11.1))                         # the middle of its lens
FIREHOLE = _blocks((FIRE_X, FIREHOLE_Y, 0.0))
REV = round(2.0 * math.pi * WHEEL_R * TEXEL, 4)                 # 3.1416 blocks for a turn of the wheels
COG_REV = round(TEETH * RUNG * TEXEL, 4)                        # 2.0 blocks for a turn of the cog

# The light the engine is shown in, (sky, block): given, not taken from the cell it stands in,
# because in the cloud that cell is a block and the engine would be black (motion/travel, a2
# #89123). The block light is what the car's lit windows give its own cell at the stop.
LIGHT = (15, 7)
CAB_LIGHT = 8                           # the fire's light in the cab, offered to the sky line (no more than 9)
STAND_REV = 64                          # ticks for a turn of the wheels of an engine that runs on the spot

# --- materials (palette only) -----------------------------------------------------------------------
IRON, IRON_D, BRASS, BRASS_D, COPPER = K.IRON, K.IRON_D, K.BRASS, K.BRASS_D, K.COPPER
BLACK = P.mat("iron", base=1)           # what the fire blackens: smokebox, chimney, cab roof
STEEL = P.mat("iron", base=5)           # bright steel: tyres, rods, bars, what hands and boots wear bright
PAINT = P.mat("enamel", base=1)         # the engine's paint: the station's enamel blue, dark
PAINT_L = P.mat("enamel", base=2)
BEAM = P.mat("signal", base=0)          # the buffer beams: warning red, as a railway's are
WOOD = P.mat("dark_wood")
COAL = P.mat("slate", base=1, noise=0.5)
SOOT = K.flat("iron", 0)
GLOW = [K.flat("glow", i) for i in range(len(P.RAMPS["glow"]))]
TAIL = P.mat("signal_glow")
CREAM = K.flat("cream", 3)
RIVET = K.flat("iron", 5)
RIVET_P = K.flat("enamel", 3)           # a rivet under the paint


class _Tread(PA.Mat):
    """Chequer plate: raised lozenges in staggered rows, a step lighter, the texel beside each a
    step darker."""

    def levels(self, w, h, grain, seed):
        jj, ii = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        a = (ii + 2 * (jj % 2)) % 4
        return self.base + (a == 0).astype(np.int32) - (a == 1).astype(np.int32)


TREAD = _Tread(PREFIX + "tread", P.RAMPS["iron"], kind="flat", bevel=0, base=2)

# One letter for every tone a hand-drawn face uses: the machines' own (PW.TONES) and the paint.
TONES = dict(PW.TONES)
TONES.update({c: P.RAMPS["enamel"][i] for i, c in enumerate("HINO")})

_RIVET, _SPOKE, _TOOTH, _LUMP, _BOLT = 900, 910, 920, 930, 940      # pieces that share one picture


def _sprite(name, pix):
    return PA.Sprite(PREFIX + name, pix.rows(), TONES)


def _sheet(w, h, seed):
    """A painted iron sheet: an edge that catches the light, a row of rivets along every edge."""
    p = PW.Pix(w, h, "I")
    p.specks("I", "N", "H", seed, share=0.05)
    p.frame(0, 0, w - 1, h - 1, "N", "H")
    for x in range(2, w - 2, 3):
        p.set(x, 1, "O")
        p.set(x, h - 2, "O")
    for y in range(4, h - 3, 3):
        p.set(1, y, "O")
        p.set(w - 2, y, "O")
    return p


def _cab_side():
    """The cab's side sheet, 16 x 16: the paint, lined out in brass, the station's emblem on it (the
    standard figure of sixteen pixels, props/signs), and the grime that the hand leaves below the
    opening's edge."""
    p = _sheet(16, 16, 3)
    cells = signs.emblem_cells(16)
    for x, y in cells["ring"]:
        p.set(x, y, "c")
    for x, y in cells["meridian"]:
        if 1 <= y <= 14:
            p.set(x, y, "c")
    for x, y in cells["star"]:
        p.set(x, y, "e")
    for x, y in cells["ring"]:                      # the ring is lit from above
        if y < 5:
            p.set(x, y, "d")
    return _sprite("cab_side", p)


def _tank_side():
    """A tank's side, 17 x 13: the paint lined out with a thin brass line, the oval of the engine's
    number plate in the middle (the plate itself is a piece of brass on it), and where the water
    ran down from the filler when the tank was last filled to the brim."""
    p = _sheet(17, 13, 5)
    for x in range(3, 14):
        p.set(x, 2, "b")
        p.set(x, 10, "b")
    for y in range(3, 10):
        p.set(2, y, "b")
        p.set(14, y, "b")
    for x, y0, y1 in ((11, 1, 6), (12, 1, 9), (5, 1, 3)):
        for y in range(y0, y1 + 1):
            p.set(x, y, "H", only="IN")
    return _sprite("tank_side", p)


def _number_plate():
    """The engine's number plate, 9 x 5: an oval of brass with a raised rim, the field sunk and
    dark. The emblem and the number go on it with the station's letters (a6's)."""
    return PA.Sprite(PREFIX + "number", [".ccdddcc.",
                                         "cd11111dc",
                                         "d1111111e",
                                         "cb11111dc",
                                         ".bbcccdc."], TONES)


def _backhead():
    """The firebox's back in the cab, 15 x 22: rows of stay heads, the firehole's door plate with
    the hole in it (the fire is a model of its own, before it), soot over the door, a shelf."""
    p = PW.Pix(15, 22, "1")
    p.specks("1", "2", "0", 9, share=0.08)
    p.frame(0, 0, 14, 21, "3", "0")
    for y in (2, 5, 8):
        for x in (2, 5, 9, 12):
            p.set(x, y, "4")
            p.set(x, y + 1, "0", only="1")
    p.rect(3, 12, 11, 18, "2")
    p.frame(3, 12, 11, 18, "4", "0")
    p.rect(5, 14, 9, 16, "0")
    for x in range(4, 11):
        p.set(x, 11, "0")
    for x in range(5, 10):
        p.set(x, 10, "0", only="12")
    p.set(7, 9, "0", only="12")
    p.set(3, 15, "5")                                # the door's hinge pins
    p.set(3, 16, "5")
    p.set(11, 15, "d")                               # its latch, brass, worn
    return _sprite("backhead", p)


def _beam_face(name):
    """A buffer beam's face, 42 x 8: red, two rows of rivets, the dirt of the road along its foot."""
    p = PW.Pix(42, 8, "J")
    p.specks("J", "K", "J", 11, share=0.06)
    p.frame(0, 0, 41, 7, "K", "J")
    for x in range(2, 41, 4):
        p.set(x, 1, "L")
        p.set(x, 6, "K")
    for x in range(1, 41):
        if (x * 7) % 5 < 2:
            p.set(x, 7, "1")
    return _sprite(name, p)


# --- drawing helpers ---------------------------------------------------------------------------------
def _draw(name, scale=1.0):
    return PW.Draw(PREFIX + name, scale=scale, step=TEXEL)


def _rivet(d, p, out, mat=RIVET, proud=0.5):
    """A rivet head a texel square on the face that looks along `out` ("x", "-x", ...), p the
    middle of its foot."""
    k = M.AXES.index(out[-1])
    lo, hi = [v - 0.5 for v in p], [v + 0.5 for v in p]
    lo[k], hi[k] = sorted((p[k], p[k] + (-proud if out.startswith("-") else proud)))
    d.box(tuple(lo), tuple(hi), mat, seed=_RIVET)


def _pair(z0, z1, s):
    """z0..z1 on the side s (1 south, -1 north), in rising order."""
    return tuple(sorted((z0 * s, z1 * s)))


# --- the body -----------------------------------------------------------------------------------------
def _frames(d):
    """The plate frames inside the wheels, the beams, the running plate."""
    for s in (-1.0, 1.0):
        a, b = _pair(10.5, 11.5, s)
        d.box((FRONT + 2, 9.5, a), (REAR - 2, PLATE_Y - 1.0, b), IRON_D, grain="x")
        for x in AXLES:
            for x0, x1 in ((x - 4.5, x - 1.75), (x + 1.75, x + 4.5)):          # the horns of an axle box
                d.box((x0, 3.0, a), (x1, 9.5, b), IRON_D, grain="y")
            d.box((x - 4.5, 2.5, a), (x + 4.5, 3.5, b), IRON, grain="x")       # the stay under them
            o, p = _pair(11.5, 12.5, s)
            d.box((x - 1.75, 6.0, o), (x + 1.75, 10.0, p), BRASS_D)            # the axle box
            d.box((x - 0.5, 10.0, o), (x + 0.5, 11.0, p), IRON)
            for i, half in enumerate((5.5, 4.25, 3.0)):                        # the leaf spring over it
                d.box((x - half, 11.0 + 0.75 * i, o), (x + half, 11.75 + 0.75 * i, p), STEEL, grain="x")
            for x0 in (x - 5.5, x + 4.75):
                d.box((x0, 11.0, o), (x0 + 0.75, PLATE_Y - 1.0, p), IRON_D)    # its hangers
        d.box((PINION[0] - 2.5, 4.0, a), (PINION[0] + 2.5, 9.5, b), IRON_D, grain="y")      # the cog axle's bearing
        d.box((PINION[0] - 1.25, 6.0, b if s > 0 else a - 0.75), (PINION[0] + 1.25, 8.5, b + 0.75 if s > 0 else a),
              BRASS_D)
    for x0, x1 in ((FRONT + 2, FRONT + 3), (-3.5, -2.5), (REAR - 4, REAR - 3)):  # stretchers between the frames
        d.box((x0, 10.0, -10.5), (x1, PLATE_Y - 1.0, 10.5), IRON_D, grain="z")

    # the beams: red, riveted, the front one with the buffer in its middle
    d.box((FRONT, 8.5, -SIDE), (FRONT + 2, PLATE_Y - 1.0, SIDE), BEAM, grain="z", faces={"w": _beam_face("beam_front")})
    d.box((REAR - 2, 8.5, -SIDE), (REAR, PLATE_Y - 1.0, SIDE), BEAM, grain="z", faces={"e": _beam_face("beam_rear")})
    d.box((FRONT - 0.5, 7.5, -3.5), (FRONT, 13.0, 3.5), IRON_D)                 # the buffer's seat
    for y in (8.25, 12.25):
        for z in (-2.75, 2.75):
            _rivet(d, (FRONT - 0.5, y, z), "-x", proud=0.4)
    d.tube("x", (10.25, 0.0), -HALF + 1.5, FRONT - 0.5, 1.5, STEEL, sides=8)    # its plunger
    d.tube("x", (10.25, 0.0), -HALF, -HALF + 1.5, 3.0, IRON, sides=12)          # its head
    d.box((REAR, 10.0, -1.5), (REAR + 0.5, 14.0, 1.5), IRON_D)                  # the draw hook's plate
    d.box((REAR + 0.5, 11.0, -0.5), (REAR + 1.5, 13.0, 0.5), STEEL)
    for z in (-13.0, 13.0):                                                     # lamp irons on the front beam
        d.box((FRONT - 0.5, 15.0, z - 0.5), (FRONT, 20.5, z + 0.5), IRON)

    # the running plate, chequered where one walks on it, and its valance
    d.box((FRONT, PLATE_Y - 1.0, -SIDE - 1.0), (REAR, PLATE_Y, SIDE + 1.0), IRON_D, grain="x", faces={"u": TREAD})
    for s in (-1.0, 1.0):
        a, b = _pair(SIDE + 0.25, SIDE + 1.0, s)
        d.box((FRONT, PLATE_Y - 2.25, a), (REAR, PLATE_Y - 1.0, b), IRON, grain="x")
        for x in range(int(FRONT) + 3, int(REAR) - 1, 4):
            _rivet(d, (x, PLATE_Y - 1.6, (SIDE + 1.0) * s), "z" if s > 0 else "-z", proud=0.3)


def _cylinders(d):
    """The two cylinders with their valve chests, the slide bars and what holds them, the steam pipes."""
    y = AXLE_Y
    for s in (-1.0, 1.0):
        z = CYL_Z * s
        out = "z" if s > 0 else "-z"
        d.tube("x", (y, z), CYL[0] + 0.75, CYL[1] - 0.75, CYL_R - 0.3, PAINT, sides=8)      # the lagging
        for x0 in (CYL[0], CYL[1] - 0.75):
            d.tube("x", (y, z), x0, x0 + 0.75, CYL_R, STEEL, sides=8)                      # the covers
        for x in (CYL[0] + 2.25, (CYL[0] + CYL[1]) / 2.0, CYL[1] - 2.25):                   # the lagging's bands
            d.ring("x", (x, y, z), CYL_R - 0.15, 0.3, 0.75, BRASS, sides=8)
        d.tube("x", (y, z), CYL[0] - 0.4, CYL[0], 0.9, BRASS, sides=8)                      # the front cover's boss
        d.tube("x", (y, z), CYL[1], CYL[1] + 1.0, 1.0, BRASS, sides=8)                      # the gland
        a, b = _pair(CYL_Z - 2.5, CYL_Z + 1.75, s)
        d.box((CYL[0] + 1.0, y + CYL_R - 0.25, a), (CYL[1] - 1.0, y + 4.75, b), IRON, grain="x")       # the valve chest
        a, b = _pair(CYL_Z - 1.75, CYL_Z + 1.0, s)
        d.box((CYL[0] + 2.0, y + 4.75, a), (CYL[1] - 2.0, y + 5.5, b), BRASS_D, grain="x")              # its cover
        for x in (CYL[0] + 2.75, CYL[1] - 2.75):
            _rivet(d, (x, y + 5.5, z - 0.4 * s), "y", proud=0.4)
        for x in (CYL[0] + 2.0, CYL[1] - 2.0):                                              # the drain cocks
            d.box((x - 0.5, y - CYL_R - 1.0, z - 0.5), (x + 0.5, y - CYL_R, z + 0.5), BRASS, seed=_BOLT)
        d.box((CYL[0] + 2.0, y - CYL_R - 0.75, z - 0.2), (CYL[1] - 2.0, y - CYL_R - 0.35, z + 0.2), STEEL)   # their pull rod
        a, b = _pair(11.5, CYL_Z - CYL_R + 0.25, s)
        d.box((CYL[0] + 1.0, y - 2.0, a), (CYL[1] - 1.0, y + 2.0, b), IRON_D, grain="z")    # the casting on the frame

        # the slide bars and the motion bracket: a hanger from the running plate outside the rods,
        # a stay over them to the frame
        a, b = _pair(CYL_Z - 0.5, CYL_Z + 0.75, s)
        d.box((BARS[0], y + 2.25, a), (BARS[1], y + 3.0, b), STEEL, grain="x")
        d.box((BARS[0], y - 3.0, a), (BARS[1], y - 2.25, b), STEEL, grain="x")
        a, b = _pair(CYL_Z + 0.75, CYL_Z + 1.75, s)
        d.box((BARS[1] - 1.0, y - 3.5, a), (BARS[1], PLATE_Y - 1.0, b), IRON_D, grain="y")
        for yy in (y - 2.6, y + 2.6, y + 6.5):
            _rivet(d, (BARS[1] - 0.5, yy, (CYL_Z + 1.75) * s), out, proud=0.3)
        a, b = _pair(11.5, CYL_Z + 0.75, s)
        d.box((BARS[1] - 1.0, y + 5.25, a), (BARS[1], y + 7.25, b), IRON_D, grain="z")
        d.box((BARS[1] - 1.6, y + 3.0, (CYL_Z + 0.1) * s - 0.3), (BARS[1] - 1.0, y + 3.6, (CYL_Z + 0.1) * s + 0.3),
              BRASS, seed=_BOLT)                                                            # an oil cup on the bar

        # the steam pipe: copper, out of the smokebox's side and down through the plate to the chest
        d.hose([_tilted(5.5, 0.5, 7.6 * s), (-14.5, 25.5, 13.0 * s), (-15.0, 20.5, (CYL_Z - 1.0) * s),
                (-15.5, y + 5.5, (CYL_Z - 0.4) * s)], 1.1, COPPER)
        d.tube("y", (-15.1, (CYL_Z - 0.85) * s), PLATE_Y, PLATE_Y + 0.75, 1.75, BRASS_D, sides=8)   # its flange on the plate


def _boiler(d):
    """Everything that lies at the boiler's tilt: smokebox and door, barrel, chimney, dome, safety
    valves, whistle, handrails, the headlamp. Drawn level about BOILER and turned as one piece."""
    fx, fy = BOILER
    with d.turned(("z", TILT), about=(fx, fy, 0.0)):
        # the smokebox, its front ring and the door: a dished plate on two strap hinges, the dart's
        # two handles in the middle, a ring of rivets round it
        d.tube("x", (fy, 0.0), fx, fx + 10.0, 8.0, BLACK, sides=12)
        d.ring("x", (fx + 0.5, fy, 0.0), 8.1, 0.5, 1.0, IRON_D, sides=12)
        d.ring("x", (fx + 9.5, fy, 0.0), 8.1, 0.5, 1.0, IRON_D, sides=12)
        d.tube("x", (fy, 0.0), fx - 0.75, fx, 6.5, BLACK, sides=12)
        d.tube("x", (fy, 0.0), fx - 1.25, fx - 0.75, 4.5, BLACK, sides=12)
        for k in range(12):
            d.box((fx - 0.4, fy + 6.9, -0.5), (fx, fy + 7.9, 0.5), RIVET, rot=("x", 30.0 * k + 15.0, (fx, fy, 0.0)),
                  seed=_RIVET + 1)
        for v in (-2.75, 2.75):
            d.box((fx - 1.1, fy + v - 0.5, -6.9), (fx - 0.75, fy + v + 0.5, 2.5), IRON, grain="z")     # hinge straps
            d.tube("y", (fx - 0.9, -6.9), fy + v - 1.0, fy + v + 1.0, 0.6, STEEL, sides=8)              # hinge pins
        d.tube("x", (fy, 0.0), fx - 1.9, fx - 1.25, 1.25, BRASS, sides=8)                               # the dart's boss
        d.box((fx - 2.4, fy - 0.4, -0.4), (fx - 1.9, fy + 3.25, 0.4), STEEL, rot=("x", -20.0, (fx - 2.0, fy, 0.0)))
        d.box((fx - 2.9, fy - 0.4, -0.4), (fx - 2.4, fy + 2.75, 0.4), STEEL, rot=("x", 100.0, (fx - 2.5, fy, 0.0)))
        d.plate("w", (fx - 1.25, fy + 3.0, 2.25), 5, 3, PA.Sprite(PREFIX + "door_plate", ["cdddc", "d111d", "cbbbc"], TONES),
                lift=0.25)

        # the barrel under its painted lagging, brass bands, the clack valves of the feed pipes
        d.tube("x", (fy, 0.0), fx + 10.0, fx + 31.0, 7.25, PAINT, sides=12)
        for u in (11.0, 17.5, 24.0, 30.0):
            d.ring("x", (fx + u, fy, 0.0), 7.45, 0.4, 1.0, BRASS, sides=12)
        for s in (-1.0, 1.0):
            a, b = _pair(7.0, 8.25, s)
            d.box((fx + 12.5, fy - 2.5, a), (fx + 14.5, fy - 0.5, b), BRASS, seed=_BOLT + 1)

        # the chimney: a foot on the smokebox, a stack that widens a little, a copper cap
        cx = fx + CHIMNEY_U
        d.tube("y", (cx, 0.0), fy + 7.4, fy + 8.6, 3.6, BLACK, sides=8)
        d.taper("y", (cx, 0.0), fy + 8.6, fy + 20.0, 2.4, 2.9, BLACK, sides=8, steps=3)
        d.taper("y", (cx, 0.0), fy + 20.0, fy + 22.5, 3.0, 3.9, COPPER, sides=8, steps=2)
        d.tube("y", (cx, 0.0), fy + 22.5, fy + CHIMNEY_TOP, 3.6, COPPER, sides=8)
        d.tube("y", (cx, 0.0), fy + CHIMNEY_TOP, fy + CHIMNEY_TOP + 0.05, 2.7, SOOT, sides=8)           # the mouth
        d.ring("y", (cx, fy + 19.6, 0.0), 3.0, 0.4, 0.8, BRASS, sides=8)

        # the dome: brass, on a foot
        dx = fx + 19.0
        d.tube("y", (dx, 0.0), fy + 6.6, fy + 7.4, 3.9, BRASS_D, sides=8)
        d.tube("y", (dx, 0.0), fy + 7.4, fy + 10.75, 3.25, BRASS, sides=8)
        d.ball((dx, fy + 10.75, 0.0), 3.25, BRASS, sides=8, layers=3, squash=0.85, part=(0.0, 1.0))
        d.tube("y", (dx, 0.0), fy + 13.4, fy + 14.1, 0.6, BRASS_D, sides=8)

        # two safety valves under one spring bridge, and the whistle
        sx = fx + 27.0
        d.box((sx - 1.5, fy + 6.9, -3.0), (sx + 1.5, fy + 7.6, 3.0), BRASS_D)
        for z in (-1.75, 1.75):
            d.tube("y", (sx, z), fy + 7.6, fy + 10.5, 0.8, BRASS, sides=8)
        d.box((sx - 0.9, fy + 10.5, -2.75), (sx + 0.9, fy + 11.25, 2.75), BRASS_D, grain="z")
        d.box((sx - 0.3, fy + 9.0, -0.3), (sx + 4.5, fy + 9.5, 0.3), STEEL, grain="x")                  # the easing lever, back to the cab
        d.tube("y", (fx + 29.0, 4.0), fy + 6.9, fy + 11.0, 0.5, BRASS, sides=8)
        d.tube("y", (fx + 29.0, 4.0), fy + 11.0, fy + 13.0, 1.0, BRASS, sides=8)
        d.tube("y", (fx + 29.0, 4.0), fy + 13.0, fy + 13.4, 0.4, BRASS_D, sides=8)

        # handrails along both sides, on stanchions
        for s in (-1.0, 1.0):
            d.rod((fx + 1.0, fy + 3.0, 8.7 * s), (fx + 30.5, fy + 3.0, 8.7 * s), 0.35, BRASS)
            for u in (2.0, 11.0, 20.5, 29.5):
                d.rod((fx + u, fy + 2.6, 7.0 * s), (fx + u, fy + 3.0, 8.7 * s), 0.3, BRASS_D)

        # the headlamp on the smokebox's brow: a brass case, a lit lens in a rim, a vent, a handle
        d.box((fx - 1.0, fy + 7.7, -1.5), (fx + 2.25, fy + 8.6, 1.5), IRON)
        d.box((fx - 1.25, fy + 8.6, -2.25), (fx + 2.25, fy + 13.6, 2.25), BRASS_D)
        d.ring("x", (fx - 1.45, fy + 11.1, 0.0), 1.9, 0.6, 0.4, BRASS, sides=8)
        d.tube("x", (fy + 11.1, 0.0), fx - 1.6, fx - 1.25, 1.6, GLOW[3], sides=8, emit=15, shade=False)
        d.tube("y", (fx + 0.5, 0.0), fy + 13.6, fy + 14.6, 1.0, BRASS_D, sides=8)
        d.box((fx + 0.1, fy + 14.6, -1.5), (fx + 0.9, fy + 15.1, 1.5), BRASS, grain="z")


def _firebox(d):
    """The firebox, level between the tanks and in the cab, with what stands on its back."""
    d.box((6.0, PLATE_Y, -7.5), (FIRE_X, 39.5, 7.5), PAINT, grain="y", faces={"e": _backhead()})
    d.box((FIRE_X, FIREHOLE_Y - 2.5, -3.75), (FIRE_X + 0.3, FIREHOLE_Y - 2.0, 3.75), IRON, grain="z")   # the door's sill
    d.box((FIRE_X, 28.0, -5.0), (FIRE_X + 1.5, 28.5, 5.0), IRON, grain="z")                              # the shelf over the door
    d.tube("y", (FIRE_X + 0.75, -3.5), 28.5, 30.0, 0.6, CREAM, sides=8)                                  # the fireman's tea can on it
    d.box((FIRE_X + 0.4, 28.5, 2.0), (FIRE_X + 1.4, 29.75, 3.25), BRASS, seed=_BOLT + 2)                 # and the oil can
    d.tube("x", (36.0, 4.5), FIRE_X, FIRE_X + 0.8, 1.75, BRASS, sides=8)                                 # the pressure gauge
    d.tube("x", (36.0, 4.5), FIRE_X + 0.8, FIRE_X + 0.9, 1.25, CREAM, sides=8)
    d.box((FIRE_X + 0.9, 35.9, 4.4), (FIRE_X + 1.0, 37.0, 4.6), SOOT)                                    # its hand
    d.box((FIRE_X, 30.5, -5.75), (FIRE_X + 0.75, 31.25, -4.5), BRASS, seed=_BOLT + 3)                    # the water gauge's cocks
    d.box((FIRE_X, 35.0, -5.75), (FIRE_X + 0.75, 35.75, -4.5), BRASS, seed=_BOLT + 3)
    d.box((FIRE_X + 0.2, 31.25, -5.4), (FIRE_X + 0.6, 35.0, -5.0), K.flat("porcelain", 3), emit=6, shade=False)   # its glass
    d.box((FIRE_X + 0.2, 31.25, -5.4), (FIRE_X + 0.61, 33.0, -5.0), K.flat("night_glass", 3))            # the water in it
    d.box((FIRE_X, 37.4, -1.0), (FIRE_X + 1.25, 38.4, 1.0), BRASS_D)                                     # the regulator's stuffing box
    d.box((FIRE_X + 1.25, 37.6, -0.4), (FIRE_X + 1.75, 38.2, 6.5), STEEL, grain="z")                     # its handle, across
    d.box((FIRE_X + 1.0, 37.4, 6.0), (FIRE_X + 2.0, 38.4, 7.0), BRASS, seed=_BOLT + 2)


def _tanks(d):
    """The side tanks: painted sheet lined out in brass, the number plate, fillers, the feed pipes."""
    side = _tank_side()
    for s in (-1.0, 1.0):
        out = "s" if s > 0 else "n"
        a, b = _pair(11.5, SIDE, s)
        d.box((TANK[0], PLATE_Y, a), (TANK[1], 30.5, b), PAINT, grain="x", faces={out: side})
        d.box((TANK[0] - 0.25, 30.25, a), (TANK[1], 30.75, b + 0.25 if s > 0 else b), BRASS, grain="x")  # the beading round the top
        d.plate(out, (1.5, 24.0, SIDE * s), 9, 5, _number_plate(), lift=0.3)
        d.tube("y", (-1.0, 16.25 * s), 30.75, 31.75, 2.25, BRASS_D, sides=8)                             # the filler's lid
        d.box((-1.4, 31.75, 16.25 * s - 1.5), (-0.6, 32.25, 16.25 * s + 1.5), BRASS, grain="z")
        d.tube("y", (7.5, 13.5 * s), 30.75, 33.5, 0.5, COPPER, sides=8)                                  # the vent pipe
        for x in (TANK[0] + 1.0, TANK[1] - 1.0):                                                         # lifting eyes
            d.box((x - 0.5, 30.75, 19.0 * s - 0.5), (x + 0.5, 31.75, 19.0 * s + 0.5), IRON, seed=_BOLT + 4)
        for y in (21.0, 27.0):                                                                           # the front's handrail
            d.box((TANK[0] - 0.75, y, 15.0 * s - 0.3), (TANK[0], y + 0.6, 15.0 * s + 0.3), BRASS_D, seed=_BOLT + 5)
        d.box((TANK[0] - 1.0, 20.5, 15.0 * s - 0.3), (TANK[0] - 0.5, 28.0, 15.0 * s + 0.3), BRASS, grain="y")
        # the feed pipe: copper, from under the cab along the tank's foot, round its front and up
        # to the clack valve on the barrel
        d.hose([(CAB[0] + 1.0, PLATE_Y + 1.1, (SIDE + 0.7) * s), (TANK[0] - 1.6, PLATE_Y + 1.1, (SIDE + 0.7) * s),
                (TANK[0] - 1.6, PLATE_Y + 1.1, 12.5 * s), _tilted(13.5, -1.5, 8.2 * s)], 0.6, COPPER)
        for x in (TANK[0] + 3.0, TANK[1] - 3.0):                                                         # its clips
            d.box((x - 0.4, PLATE_Y, SIDE * s), (x + 0.4, PLATE_Y + 2.0, (SIDE + 1.5) * s), BRASS_D, seed=_BOLT + 6)
    d.tube("z", (2.0, 19.5), -11.5, 11.5, 0.9, COPPER, sides=8)                                          # the balance pipe under the barrel


def _cab(d):
    """The cab: spectacle plate with two round windows, side sheets with the emblem, corner pillars,
    an arched roof; the bunker with its coal behind, open above it; the brake, the reverser."""
    x0, x1 = CAB
    side = _cab_side()
    d.box((x0, PLATE_Y, -SIDE), (x0 + 1.0, EAVES, SIDE), PAINT, grain="z")
    for s in (-1.0, 1.0):
        out = "s" if s > 0 else "n"
        zs = "z" if s > 0 else "-z"
        d.ring("x", (x0 - 0.2, 40.5, 14.0 * s), 2.9, 0.8, 0.6, BRASS, sides=12)                          # the spectacles
        d.tube("x", (40.5, 14.0 * s), x0 - 0.1, x0 + 1.1, 2.5, GLOW[0], sides=12, emit=10, shade=False)
        a, b = _pair(SIDE - 1.0, SIDE, s)
        d.box((x0, PLATE_Y, a), (x1, WAIST, b), PAINT, grain="x", faces={out: side})
        d.box((x0, WAIST, a), (x0 + 2.5, EAVES, b), PAINT, grain="y")
        d.box((x1 - 2.5, WAIST, a), (x1, EAVES, b), PAINT, grain="y")
        d.box((x0, EAVES - 1.5, a), (x1, EAVES, b), PAINT, grain="x")
        o, p = _pair(SIDE - 1.25, SIDE + 0.35, s)
        d.box((x0 + 2.5, WAIST - 0.4, o), (x1 - 2.5, WAIST + 0.4, p), STEEL, grain="x")                  # the sill, worn bright by sleeves
        d.box((x1 - 0.35, PLATE_Y + 2.0, (SIDE + 0.2) * s - 0.3), (x1 + 0.25, WAIST + 6.0, (SIDE + 0.2) * s + 0.3),
              BRASS, grain="y")                                                                          # the grab rail at the cab's back
        for y in (PLATE_Y + 2.0, WAIST + 5.4):
            _rivet(d, (x1 - 0.05, y + 0.3, SIDE * s), zs, mat=BRASS_D, proud=0.5)
        # the steps under the cab's back corner: a hanger, two treads worn bright
        a, b = _pair(SIDE, SIDE + 0.5, s)
        d.box((x1 - 2.0, 5.0, a), (x1 + 1.5, PLATE_Y - 1.0, b), IRON_D, grain="y")
        a, b = _pair(SIDE, SIDE + 2.0, s)
        for y in (5.0, 10.5):
            d.box((x1 - 2.5, y, a), (x1 + 2.0, y + 0.75, b), STEEL, grain="x", faces={"u": TREAD})

    # the back sheet and the bunker: coal heaped over its edge
    d.box((x1 - 1.0, PLATE_Y, -SIDE), (x1, WAIST + 1.0, SIDE), PAINT, grain="z", faces={"e": _sheet(42, 17, 7).sprite(PREFIX + "back_sheet")
                                                                                         if False else PAINT})
    d.box((x1 - 5.0, PLATE_Y, -SIDE + 1.0), (x1 - 4.25, WAIST - 2.0, SIDE - 1.0), IRON_D, grain="z")     # the bunker's front
    d.box((x1 - 4.25, WAIST - 4.0, -SIDE + 1.0), (x1 - 1.0, WAIST - 1.0, SIDE - 1.0), COAL, grain="z")
    lumps = ((-15.0, 0.0, 20.0), (-9.5, 0.8, -35.0), (-4.0, 0.2, 10.0), (1.5, 1.0, 50.0), (7.0, 0.3, -15.0),
             (12.5, 0.9, 30.0), (16.0, 0.0, -40.0), (-12.0, 1.4, 60.0), (4.0, 1.6, -60.0), (10.0, 1.5, 15.0))
    for z, up, turn in lumps:
        c = (x1 - 2.6, WAIST - 1.0 + up, z)
        d.box((c[0] - 1.25, c[1] - 1.0, c[2] - 1.5), (c[0] + 1.25, c[1] + 1.0, c[2] + 1.5), COAL,
              rot=("xyz", (turn * 0.3, turn, 12.0), c), seed=_LUMP)
    d.box((x1 - 5.75, PLATE_Y, -2.0), (x1 - 5.0, PLATE_Y + 3.0, 2.0), SOOT)                              # the coal hole
    d.box((x1 - 7.5, PLATE_Y, -1.75), (x1 - 5.0, PLATE_Y + 0.6, 1.75), COAL, seed=_LUMP + 1)             # and what spilled out of it
    d.beam((x1 - 5.4, PLATE_Y + 0.3, 8.0), (x1 - 5.6, PLATE_Y + 13.0, 10.5), 0.6, 0.6, WOOD)             # the shovel, stood in the corner
    d.box((x1 - 6.0, PLATE_Y, 6.75), (x1 - 5.4, PLATE_Y + 3.0, 9.25), STEEL, rot=("x", 11.0, (x1 - 5.7, PLATE_Y, 8.0)))

    # the floor's chequer plate, the brake's column with its red wheel, the reverser
    d.box((x0 + 1.0, PLATE_Y, -SIDE + 1.0), (x1 - 5.0, PLATE_Y + 0.25, SIDE - 1.0), IRON_D, grain="x", faces={"u": TREAD})
    bx, bz = x1 - 7.0, -15.5
    d.tube("y", (bx, bz), PLATE_Y, 31.0, 0.6, IRON, sides=8)
    d.ring("y", (bx, 31.4, bz), 2.1, 0.6, 0.6, P.mat("signal"), sides=8)
    for k in range(2):
        d.box((bx - 2.1, 31.1, bz - 0.25), (bx + 2.1, 31.7, bz + 0.25), P.mat("signal"), rot=("y", 90.0 * k + 22.5, (bx, 31.4, bz)),
              seed=_SPOKE + 5)
    d.tube("y", (bx, bz), 31.0, 32.2, 0.5, BRASS, sides=8)
    rz = 15.0
    d.box((x0 + 2.0, PLATE_Y, rz - 0.4), (x0 + 9.0, PLATE_Y + 6.5, rz + 0.4), IRON_D, grain="x")         # the reverser's stand
    d.ring("z", (x0 + 5.5, PLATE_Y + 6.0, rz), 4.5, 0.6, 0.9, STEEL, sides=16, arc=(40.0, 140.0))        # its notched quadrant
    d.box((x0 + 5.2, PLATE_Y + 2.0, rz + 0.4), (x0 + 5.8, PLATE_Y + 13.0, rz + 0.9), STEEL, rot=("z", -14.0, (x0 + 5.5, PLATE_Y + 2.0, rz)))
    d.box((x0 + 7.9, PLATE_Y + 12.2, rz + 0.3), (x0 + 8.9, PLATE_Y + 13.6, rz + 1.0), BRASS, seed=_BOLT + 7)

    # the roof: three steps of an arch, a rain strip, a ventilator; sooty
    d.box((x0 - 1.5, EAVES, -SIDE - 1.5), (x1 + 1.5, EAVES + 1.0, SIDE + 1.5), BLACK, grain="x")
    d.box((x0 - 1.5, EAVES + 1.0, -15.0), (x1 + 1.5, EAVES + 2.0, 15.0), BLACK, grain="x")
    d.box((x0 - 1.5, EAVES + 2.0, -8.0), (x1 + 1.5, EAVES + 2.75, 8.0), BLACK, grain="x")
    for s in (-1.0, 1.0):
        a, b = _pair(SIDE + 1.5, SIDE + 2.0, s)
        d.box((x0 - 1.5, EAVES - 0.25, a), (x1 + 1.5, EAVES + 1.0, b), IRON, grain="x")
    d.box((x0 + 4.0, EAVES + 2.75, -3.0), (x1 - 4.0, EAVES + 3.5, 3.0), IRON_D, grain="x")
    for x in (x0 + 5.0, x1 - 5.0):
        _rivet(d, (x, EAVES + 3.5, 0.0), "y")

    # the tail lamp on the plate's back corner: brass, a red lens to the rear
    d.box((x1 - 0.25, PLATE_Y, 13.0), (x1 + 2.0, PLATE_Y + 3.5, 15.5), BRASS_D)
    d.box((x1 + 2.0, PLATE_Y + 0.9, 13.5), (x1 + 2.2, PLATE_Y + 2.9, 15.0), TAIL, emit=15, shade=False)
    d.box((x1 + 0.4, PLATE_Y + 3.5, 13.75), (x1 + 1.35, PLATE_Y + 4.25, 14.75), BRASS)


def _front(d):
    """What stands on the plate beside the smokebox: its saddle, a tool box, a jack."""
    d.box((BOILER[0] + 0.5, PLATE_Y, -5.0), (BOILER[0] + 9.5, 22.5, 5.0), IRON_D, grain="x")            # the saddle
    for z in (-5.0, 5.0):
        for x in (BOILER[0] + 2.0, BOILER[0] + 5.0, BOILER[0] + 8.0):
            _rivet(d, (x, PLATE_Y + 1.0, z), "z" if z > 0 else "-z", proud=0.4)
    # north of the smokebox: the tool box, strapped, a brass hasp
    d.box((-13.0, PLATE_Y, -20.0), (-8.5, PLATE_Y + 4.0, -13.0), WOOD, grain="z")
    for z in (-18.5, -14.5):
        d.box((-13.2, PLATE_Y, z - 0.5), (-8.3, PLATE_Y + 4.2, z + 0.5), IRON, grain="y", seed=_BOLT + 8)
    d.box((-13.4, PLATE_Y + 2.0, -17.0), (-13.0, PLATE_Y + 3.25, -16.0), BRASS)
    # south of it: the jack that puts a wheel back on the rails, and a bucket
    d.box((-12.5, PLATE_Y, 14.5), (-9.5, PLATE_Y + 0.75, 18.5), IRON, grain="x")
    d.tube("y", (-11.0, 16.5), PLATE_Y + 0.75, PLATE_Y + 5.5, 1.25, IRON_D, sides=8)
    d.tube("y", (-11.0, 16.5), PLATE_Y + 5.5, PLATE_Y + 7.0, 0.6, STEEL, sides=8)
    d.box((-11.4, PLATE_Y + 7.0, 15.25), (-10.6, PLATE_Y + 7.6, 17.75), STEEL, grain="z")
    d.tube("y", (-17.5, 17.0), PLATE_Y, PLATE_Y + 3.0, 1.5, IRON, sides=8)
    d.tube("y", (-17.5, 17.0), PLATE_Y + 2.9, PLATE_Y + 3.0, 1.25, SOOT, sides=8)


def _body():
    d = _draw("body", scale=2.0)
    _frames(d)
    _cylinders(d)
    _front(d)
    _boiler(d)
    _firebox(d)
    _tanks(d)
    _cab(d)
    return d


# --- the fire -------------------------------------------------------------------------------------------
def _glowing(name, rows, seed):
    """A hand-drawn glow that flickers: the first frame is the drawing."""
    pix = PA.Sprite(PREFIX + name, rows, TONES).paint(len(rows[0]), len(rows))
    return PA.shimmer(PREFIX + name, pix, P.RAMPS["glow"], frames=6, frametime=4, share=0.4, seed=seed)


def _fire():
    """The fire's light: in the firehole, on the floor before it, in the ashpan's slot under the
    cab. A small model by itself, so that only its own small sheet is redrawn when it flickers.
    Anchor: the middle of the firehole on the firebox's back."""
    d = _draw("fire")
    hole = _glowing("fire_hole", ["vwxwv", "wxyxw", "uvwvu"], 1)
    d.box((0.05, -1.5, -2.5), (0.3, 1.5, 2.5), GLOW[1], faces={"e": hole}, emit=15, shade=False)
    floor = _glowing("fire_floor", [".u..", "uvu.", "vwvu", "vwvu", "uvu.", ".u.."], 2)
    y = PLATE_Y + 0.3 - FIREHOLE_Y
    d.box((0.5, y, -3.0), (4.5, y + 0.05, 3.0), GLOW[0], skip="nsewd", faces={"u": floor}, emit=12, shade=False)
    slot = _glowing("fire_ash", ["uvuuvvuu", "0u00u0u0"], 3)
    y = 12.0 - FIREHOLE_Y
    d.box((-8.5, y, -9.75), (-0.5, y + 2.0, 9.75), SOOT, faces={"n": slot, "s": slot}, emit=15, shade=False)
    return d


# --- the running gear ----------------------------------------------------------------------------------
def _wheels():
    """A pair of wheels on their axle: ten spokes, a steel tyre, the crank's boss and web towards -x
    (the rest pose) and the balance weight opposite. Anchor: the middle of the axle, which is the
    model's z axis. MOVES: turns about it."""
    d = _draw("wheels")
    d.tube("z", (0.0, 0.0), -GAUGE - 1.0, GAUGE + 1.0, 1.25, IRON_D, sides=8)
    for s in (-1.0, 1.0):
        zc = (GAUGE - 0.1) * s
        d.ring("z", (0.0, 0.0, zc), WHEEL_R - 0.75, 1.5, 2.75, STEEL, sides=16)                          # the tyre
        d.ring("z", (0.0, 0.0, zc), WHEEL_R - 1.9, 0.8, 1.75, IRON, sides=16)                            # the rim
        for k in range(5):
            d.box((-(WHEEL_R - 1.6), -0.55, zc - 0.5), (WHEEL_R - 1.6, 0.55, zc + 0.5), IRON,
                  rot=("z", 36.0 * k + 18.0, (0.0, 0.0, zc)), seed=_SPOKE)
        a, b = _pair(GAUGE - 1.5, GAUGE + 1.5, s)
        d.tube("z", (0.0, 0.0), a, b, 2.1, IRON, sides=8)                                                # the hub
        a, b = _pair(GAUGE + 1.5, GAUGE + 1.9, s)
        d.tube("z", (0.0, 0.0), a, b, 1.1, BRASS_D, sides=8)
        a, b = _pair(GAUGE - 0.75, GAUGE + 1.25, s)
        d.box((-CRANK_R, -1.3, a), (0.0, 1.3, b), IRON, grain="x")                                       # the crank's web
        a, b = _pair(GAUGE - 0.75, GAUGE + 1.75, s)
        d.tube("z", (-CRANK_R, 0.0), a, b, 1.7, IRON, sides=8)                                           # its boss
        d.ring("z", (0.0, 0.0, zc), WHEEL_R - 3.3, 2.2, 1.5, IRON_D, sides=16, arc=(-56.25, 56.25))      # the balance weight
    return d


def _pinion():
    """The cog wheel on its axle between the frames, a brake drum on either side of it. Anchor: the
    middle of the axle (the model's z axis). MOVES: turns about it, a turn for every TEETH rungs."""
    d = _draw("pinion")
    d.tube("z", (0.0, 0.0), -10.5, 10.5, 1.25, IRON_D, sides=8)
    d.tube("z", (0.0, 0.0), -3.0, 3.0, PITCH_R - 0.9, IRON, sides=16)
    for k in range(TEETH // 2):
        d.box((-TIP_R, -0.9, -2.75), (TIP_R, 0.9, 2.75), STEEL, rot=("z", 360.0 * k / TEETH, (0.0, 0.0, 0.0)),
              seed=_TOOTH)
    for s in (-1.0, 1.0):
        a, b = _pair(3.0, 3.6, s)
        d.tube("z", (0.0, 0.0), a, b, 2.25, IRON_D, sides=8)
        a, b = _pair(5.0, 8.5, s)
        d.tube("z", (0.0, 0.0), a, b, 4.25, IRON_D, sides=16)                                            # the brake drum
        for z in (5.4, 8.1):
            d.ring("z", (0.0, 0.0, z * s), 4.35, 0.5, 0.5, IRON, sides=16)                               # its flanges
        d.ring("z", (0.0, 0.0, 6.75 * s), 4.3, 0.3, 1.6, BRASS_D, sides=16, arc=(20.0, 340.0))           # the band's lining
    return d


def _conrod():
    """The two connecting rods. Anchor: the crosshead pin (the small end); the rod lies along +x,
    ROD long, to the crank pin. MOVES: slides with the crosshead and tilts about z."""
    d = _draw("conrod")
    for s in (-1.0, 1.0):
        a, b = _pair(CYL_Z - 0.5, CYL_Z + 0.5, s)
        d.box((0.0, -0.6, a), (ROD * 0.5, 0.6, b), STEEL, grain="x")
        d.box((ROD * 0.5, -0.8, a), (ROD, 0.8, b), STEEL, grain="x")
        d.tube("z", (0.0, 0.0), a, b, 1.3, STEEL, sides=8)                                               # the small end
        a, b = _pair(CYL_Z - 0.75, CYL_Z + 0.75, s)
        d.tube("z", (ROD, 0.0), a, b, 1.9, STEEL, sides=8)                                               # the big end
        d.box((ROD - 2.4, -1.5, a), (ROD - 1.6, 1.5, b), BRASS, seed=_BOLT)                              # its brasses' cotter
        a, b = _pair(CYL_Z + 0.75, CYL_Z + 1.25, s)
        d.tube("z", (ROD, 0.0), a, b, 1.0, BRASS, sides=8)                                               # the pin's nut
        d.box((ROD - 0.4, 1.9, CYL_Z * s - 0.4), (ROD + 0.4, 2.6, CYL_Z * s + 0.4), BRASS, seed=_BOLT + 1)   # the oil cup
    return d


def _crosshead():
    """The two crossheads with their slippers, and the piston rods. Anchor: the crosshead pin.
    MOVES: slides along x."""
    d = _draw("crosshead")
    for s in (-1.0, 1.0):
        a, b = _pair(CYL_Z - 0.75, CYL_Z + 1.0, s)
        d.box((-1.5, -1.75, a), (1.5, 1.75, b), IRON, grain="y")
        for y0 in (1.75, -2.25):
            d.box((-1.5, y0, a), (1.5, y0 + 0.5, b), BRASS_D, grain="x", seed=_BOLT)
        d.tube("x", (0.0, CYL_Z * s), -11.25, -1.5, 0.6, STEEL, sides=8)                                 # the piston rod
        a, b = _pair(CYL_Z + 1.0, CYL_Z + 1.4, s)
        d.tube("z", (0.0, 0.0), a, b, 0.8, BRASS, sides=8)                                               # the pin's head
    return d


def _coupling():
    """The two coupling rods, from the front wheels' pins to the rear ones'. Anchor: half way
    between the two pins. MOVES: goes round with the pins, CRANK_R from where the wheels' own
    middle line is, and stays level."""
    d = _draw("coupling")
    half = (AXLES[1] - AXLES[0]) / 2.0
    for s in (-1.0, 1.0):
        a, b = _pair(GAUGE + 2.0, GAUGE + 3.0, s)
        d.box((-half, -0.7, a), (half, 0.7, b), STEEL, grain="x")
        for x in (-half, half):
            d.tube("z", (x, 0.0), a, b, 1.6, STEEL, sides=8)
            d.box((x - 0.4, 1.6, (GAUGE + 2.5) * s - 0.4), (x + 0.4, 2.3, (GAUGE + 2.5) * s + 0.4), BRASS, seed=_BOLT)
        o, p = _pair(GAUGE + 3.0, GAUGE + 3.4, s)
        d.tube("z", (-half, 0.0), o, p, 0.9, BRASS, sides=8)                                             # the front pin's cap
    return d


BUILDERS = {"body": _body, "fire": _fire, "wheels": _wheels, "pinion": _pinion, "conrod": _conrod,
            "crosshead": _crosshead, "coupling": _coupling}

_MID = (AXLES[0] + AXLES[1]) / 2.0
# name, where its anchor lies in the rest pose (x, y), and how it moves:
#   carry                 with the engine
#   roll, radius          with the engine, turning about z as a wheel of that radius rolls
#   rod, shaft            the connecting rod: its anchor on the stroke's line, CRANK_R and ROD to the pin
#   slide, shaft          what the rod pushes: on the stroke's line, no turn
#   orbit, centre         level, its anchor CRANK_R from `centre`, going round as the pins do
PARTS = (
    dict(name="body", at=(0.0, 0.0), move="carry"),
    dict(name="fire", at=(FIRE_X, FIREHOLE_Y), move="carry"),
    dict(name="wheels", at=(AXLES[0], AXLE_Y), move="roll", radius=WHEEL_R),
    dict(name="wheels", at=(AXLES[1], AXLE_Y), move="roll", radius=WHEEL_R),
    dict(name="pinion", at=PINION, move="roll", radius=PITCH_R),
    dict(name="conrod", at=(AXLES[1] - CRANK_R - ROD, AXLE_Y), move="rod", shaft=(AXLES[1], AXLE_Y)),
    dict(name="crosshead", at=(AXLES[1] - CRANK_R - ROD, AXLE_Y), move="slide", shaft=(AXLES[1], AXLE_Y)),
    dict(name="coupling", at=(_MID - CRANK_R, AXLE_Y), move="orbit", centre=(_MID, AXLE_Y)),
)
MOVING = ("rod", "slide", "orbit")      # the moves travel does not have yet


@functools.lru_cache(maxsize=None)
def _drawn():
    return {PREFIX + name: make() for name, make in BUILDERS.items()}


@functools.lru_cache(maxsize=None)
def _models():
    return {name: K.settle(d.m) for name, d in _drawn().items()}


def models():
    return dict(_models())


# --- poses ----------------------------------------------------------------------------------------------
def pose(part, run=0.0):
    """((x, y), degrees about z) of a part of PARTS when the engine has run `run` blocks uphill
    (towards -x) from the rest pose, in which the crank pins point at the cylinders. A turn is
    right-handed about +z: seen from the south side (+z) the wheels of an engine going uphill, to
    the left, turn counter-clockwise."""
    move = part["move"]
    x, y = part["at"]
    if move == "carry":
        return (x, y), 0.0
    if move == "roll":
        return (x, y), math.degrees(run / (part["radius"] * TEXEL))
    phi = math.pi + run / (WHEEL_R * TEXEL)             # where the pins stand, from +x
    if move == "orbit":
        cx, cy = part["centre"]
        return (cx + CRANK_R * math.cos(phi), cy + CRANK_R * math.sin(phi)), 0.0
    sx, sy = part["shaft"]
    reach = math.sqrt(ROD * ROD - (CRANK_R * math.sin(phi)) ** 2)
    at = (sx + CRANK_R * math.cos(phi) - reach, sy)
    if move == "slide":
        return at, 0.0
    return at, math.degrees(math.atan2(CRANK_R * math.sin(phi), reach))


def home():
    """Where the engine stands at the stop, behind the car: (the point of its frame's origin, yaw,
    tilt), read off the line (site/_rail): its two axles stand on the line, its middle LENGTH / 2
    behind the car's end. yaw turns the frame's +x to the heading of one going out; tilt is the
    degrees +x points above the level (negative where the line goes down)."""
    s = RAIL.STOP + RAIL.CAR / 2.0 + LENGTH * TEXEL / 2.0
    lie = RAIL.pose(s + _MID * TEXEL, (AXLES[1] - AXLES[0]) * TEXEL)
    yaw = math.degrees(math.atan2(lie.hz, lie.hx))
    tilt = math.degrees(math.atan(lie.slope))
    dx, dy, dz = _offset((-_MID, 0.0), yaw, tilt)
    return (lie.x + dx, lie.y + dy, lie.z + dz), yaw, tilt


def _offset(xy, yaw, tilt):
    """A point (x, y) texels of the engine's middle plane as blocks in the world, from the origin."""
    a = math.radians(tilt)
    x, y = xy[0] * TEXEL, xy[1] * TEXEL
    return K.turn(yaw, (x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a), 0.0))


def point(p, at, yaw=0.0, tilt=0.0):
    """A point given in blocks in the engine's frame (CHIMNEY, WHISTLE, ...) as a point of the
    scene, for an engine placed at `at` with that yaw and tilt."""
    a = math.radians(tilt)
    dx, dy, dz = K.turn(yaw, (p[0] * math.cos(a) - p[1] * math.sin(a), p[0] * math.sin(a) + p[1] * math.cos(a), p[2]))
    return (at[0] + dx, at[1] + dy, at[2] + dz)


# --- placing --------------------------------------------------------------------------------------------
def place(canvas, at, yaw=0.0, tilt=0.0, run=0.0, origin=(0, 0, 0), car=None, stand=False, light=False,
          brightness=LIGHT, view=M.FAR):
    """Put the engine down with the origin of its frame on `at` (scene coordinates before origin).

    yaw, tilt   as home() gives them: yaw 0 looks along the world's axes, chimney to the west
    run         blocks it has run uphill from the rest pose: how its wheels and rods stand
    car         motion's travel car that carries it: every piece is handed to it, wheels and cog
                roll; the rods are left off until travel moves them (MOVING)
    stand       True: it runs on the spot, driven by the loop (MK.spin, MK.crank); the coupling
                rods, which the loop has no verb for, are left off
    light       True: the fire's light in the cab is offered to the sky line
    Returns the number of display entities placed; they carry TAG and are kept, with their parts,
    in canvas.locomotive = [(entity, part), ...]."""
    built, drawn = _models(), _drawn()
    kept = getattr(canvas, "locomotive", None)
    if kept is None:
        kept = canvas.locomotive = []
    n = 0
    for part in PARTS:
        move = part["move"]
        if move in MOVING and car is not None and not hasattr(car, "rod"):
            continue
        if move == "orbit" and (stand or car is not None):
            continue
        name = PREFIX + part["name"]
        xy, turn = pose(part, run)
        dx, dy, dz = _offset(xy, yaw, tilt)
        nbt = M.display(built[name], yaw=yaw, scale=drawn[name].scale, turns=(("z", turn + tilt),),
                        brightness=brightness, view=view)
        nbt["Tags"].append(TAG)
        canvas.add_entity(at[0] + dx + origin[0], at[1] + dy + origin[1], at[2] + dz + origin[2], nbt)
        kept.append((canvas.entities[-1], part))
        n += 1
        if car is not None:
            if move == "roll":
                car.roll(canvas, "z", part["radius"] * TEXEL)
            else:
                car.carry(canvas)
        elif stand:
            if move == "roll":
                MK.spin(canvas, "z", int(round(STAND_REV * part["radius"] / WHEEL_R)))
            elif move in ("rod", "slide"):
                MK.crank(canvas, "z", "-x", CRANK_R * TEXEL, ROD * TEXEL, STAND_REV, turn=move == "rod")
    if light:
        x, y, z = point((1.25, 1.7, 0.0), at, yaw, tilt)
        K.offer_lights(canvas, [((math.floor(x + origin[0]), math.floor(y + origin[1]), math.floor(z + origin[2])),
                                 CAB_LIGHT)], "machines/locomotive:cab_fire")
    return n


DRESS = True            # the engine stands at the stop in the master scene; a test scene may switch it
#                         off for its canvas with dress(canvas, False)


def dress(canvas, on=True):
    canvas.locomotive_dress = bool(on)


def build(canvas, origin=(0, 0, 0)):
    """The engine at the stop, behind the car, unless it stands already: who makes the train
    (machines/cable, with motion's travel) places it with place(canvas, *home(), car=...), and then
    this does nothing."""
    if not getattr(canvas, "locomotive_dress", DRESS) or getattr(canvas, "locomotive", None):
        return 0
    at, yaw, tilt = home()
    return place(canvas, at, yaw=yaw, tilt=tilt, origin=origin, light=True)
