"""machines/switchboard-boiler, the boilers of the power house (plan/ART-PLAN.md 5.3, 7.2;
plan/parts/A5-machines.md 2.6; card plan/packages/machines/switchboard-boiler.md). The switchboard
is machines/board.py.

What it is. Two shell boilers of riveted iron plate, each three blocks across and four and a half
long, lying side by side on cast saddles. The fire is in a furnace tube that runs through the
water from end to end: its mouth is the round casting low in the front plate, with the fire door
in it and the ash pit's damper under the door. Above the furnace the front carries what the stoker
reads: two water gauges, the boiler's number, and the pressure gauge on its stem over the top of
the plate. On the shell: the lever safety valve near the front, its weight the one red thing of
the set; the steam dome with the stop valve, whose flange looks up and is where the steam pipe
starts; the manhole. The smoke leaves by a sheet-iron flue from the middle of the back plate into
the chimney's foot.

No. 1 (north) stands banked with its door shut: the fire shows in the ring between door and frame
and in the three air slots. No. 2 has just been fired: its door stands a third open.

Where they stand. In the north-east of the room (site/powerhouse.ROOM), west of the chimney's foot
and behind the two bays whose windows glow: their axes east-west, their fronts to the west, so
that whoever comes in by the wicket has the two fire doors on the left hand, the switchboard on
the right and the engine straight ahead.

    x  the front plates stand in the plane x = FRONT_X; the shells lie east of it
    y  the floor is S.LOWER_GROUND; the shells' axes lie AXIS_H above it
    z  the axes: AXES_Z

How it is lit. Every piece of a boiler stands (its entity) in the cell before that boiler's fire
door, where LIGHTS asks for the fire's light: the whole boiler takes the light of its own fire,
whatever the room does. The front and the fittings are drawn in the kit's leaning frame, so that
what looks at the firing floor is shown at its full tone.

Every model is drawn in texels in a boiler's own frame: x from the front plate towards the back,
y up from the floor, z from the axis (south is positive).
"""
import functools
import math

from ..common import palette as P
from ..common import skeleton as S
from . import _powerkit as K

PREFIX = "mach_boiler_"

# --- where they stand (scene coordinates, blocks) -----------------------------------------------------
FLOOR = float(S.LOWER_GROUND)           # -6.0
FRONT_X = 79.0                          # the plane of the front plates
AXES_Z = (24.5, 28.5)                   # No. 1 (on the middle of the chimney foot's west face), No. 2
CHIMNEY_WEST = 84.0                     # the west face of the chimney's foot (site/powerhouse.TOWER)
CHIMNEY_SOUTH = 26.0                    # ... and its south face
R = 1.5                                 # the shell: three blocks across (the card)
LEN = 4.5                               # ... and four and a half long
AXIS_H = 2.0                            # its axis over the floor: half a block of saddle under it
DOME_X = 2.5                            # the steam dome's axis, from the front plate
STAND = (-0.5, 1.5, 0.0)                # where a boiler's entities stand, in its own frame: before the fire door

# --- a boiler (its own frame, texels) -----------------------------------------------------------------
_R, _LEN, _AXIS = 24, 72, 32
_AT = tuple(v * 16.0 for v in STAND)
_SIDES = 16
_STEP = 360.0 / _SIDES
_HOOPS = ((0, 3), (19, 22), (50, 53), (69, 72))     # the two end rings and the two girth laps between them
_LAPS = {2: ((3, 19), (53, 69)), 3: ((22, 50),)}    # the lengthwise laps: flat -> stretches along x
_FURNACE = 22                           # the furnace mouth's middle over the floor
_MOUTH = 11                             # ... and its radius
_DOOR = (12, 9)                         # the fire door, wide and high
_DOOR_Y = _FURNACE + 1.5                # its middle
_AJAR = 30.0                            # how far No. 2's door stands open, degrees
_GLASS_Z = 13                           # the water gauges, either side of the middle
_DOME = int(DOME_X * 16)                # 40
_VALVE = 12                             # the safety valve's axis, from the front plate
_FLUE_R = 8
_TURN = (88, 96)                        # the south flue: straight to here, on its new line from here

# --- for the others (scene coordinates, blocks) -------------------------------------------------------
# Where the fire doors throw their light: the cell before each door (ART-PLAN 3.2, second grade).
LIGHTS = [((FRONT_X + STAND[0], FLOOR + STAND[1], z), 10) for z in AXES_Z]
# The stop valve's flange on each steam dome, looking up: the steam pipes start on it (interiors).
STEAM_OUT = [(FRONT_X + DOME_X, FLOOR + 5.0, z) for z in AXES_Z]
# For the motion line: the middle of each fire door (sparks, the fire's crackle) and the top of each
# safety valve (a wisp of steam).
FIRE_DOORS = [(FRONT_X - 0.25, FLOOR + _DOOR_Y / 16.0, z) for z in AXES_Z]
SAFETY_VALVES = [(FRONT_X + _VALVE / 16.0, FLOOR + 67.0 / 16.0, z) for z in AXES_Z]
# Boxes (x0, y0, z0, x1, y1, z1) in which something of the set stands: nothing else goes there.
KEEP_CLEAR = tuple((FRONT_X - 0.375, FLOOR, z - R - 0.125, FRONT_X + LEN + 0.0625, FLOOR + 5.0, z + R + 0.125)
                   for z in AXES_Z) + (
    (FRONT_X + LEN, FLOOR + AXIS_H - 0.625, AXES_Z[0] - 0.625, CHIMNEY_WEST, FLOOR + AXIS_H + 0.625, AXES_Z[0] + 0.625),
    (FRONT_X + LEN, FLOOR + AXIS_H - 0.625, CHIMNEY_SOUTH, FRONT_X + _TURN[1] / 16.0 + 0.625, FLOOR + AXIS_H + 0.625,
     AXES_Z[1] + 0.625),
)

# --- materials (the palette's, and nothing else) ------------------------------------------------------
IRON = P.mat("iron")                    # castings: base 3, a bevel round every face
IRON_L = P.mat("iron", base=4)
IRON_D = P.mat("iron", base=2)
BRASS = P.mat("brass")
RED = P.mat("signal")
PLATE = 3                               # the iron ramp's step of the shell's plates
# The painted tone of a flat of the shell, by its place from the crown (0) down to the keel (7), in
# steps from PLATE. The game shows the two flats next to the crown at full tone, the four of each
# flank a step darker and the two next to the keel three steps darker: with these the eight come out
# 1, 0, 0, -1, -1, -2, -2, -3: a round shell under a light from above, in five tones.
BAND = (1, 0, 1, 0, 0, -1, 1, 0)


def _i(step):
    return K.tone("iron", step)


def _fl(step):
    return K.flat("iron", step)


# ---- the pictures ---------------------------------------------------------------------------------------
def _plate_picture(j):
    """The strip of plate on one flat of the shell, from the front plate to the back."""
    t = PLATE + BAND[j]
    p = K.Pix(_LEN, 10, _i(t))
    p.streaks(_i(t), _i(t + 1), _i(t - 1), seed=40 + j, share=0.07)
    for x0, x1 in _LAPS.get(j, ()):
        p.rect(x0, 6, x1 - 1, 6, _i(t - 1))
        for x in range(x0 + 2, x1 - 1, 4):
            p.set(x, 3, _i(t + 2))
            p.set(x, 4, _i(t - 1))
    return p.sprite(f"{PREFIX}plate_{j}")


def _hoop_picture(j, up):
    """A hoop's outer face on one flat: lit on the edge towards the fire, two rivets to the flat."""
    t = PLATE + BAND[j]
    p = K.Pix(3, 10)
    p.rect(0, 0, 0, 9, _i(t + 1))
    p.rect(1, 0, 1, 9, _i(t))
    p.rect(2, 0, 2, 9, _i(t - 1))
    for y in (2, 7):
        p.set(1, y, _i(t + 2))
        p.set(1, y - 1 if up else y + 1, _i(t - 1))
    return p.sprite(f"{PREFIX}hoop_{j}{'u' if up else 'd'}")


def _rim(p, c, r, field):
    """The turned edge of an end plate, with its ring of rivets: lit from above."""
    p.disc(c, c, r, _i(field))
    p.band(c, c, r, r - 1.0, _i(field + 2), _i(field + 1), _i(field - 2))
    p.band(c, c, r - 3.0, r - 4.0, _i(field - 2), _i(field - 1), _i(field + 1))
    p.studs(c, c, r - 2.0, 28, _i(field + 2), _i(field - 2), start=360.0 / 56.0)


def _front_picture():
    """The front plate: 50 texels across."""
    p = K.Pix(50, 50)
    _rim(p, 25.0, 25.0, PLATE)
    # soot round the furnace mouth, thinning out
    my = 25.0 + (_AXIS - _FURNACE)
    for y in range(50):
        for x in range(50):
            if p.get(x, y) != _i(PLATE) or math.hypot(x + 0.5 - 25.0, y + 0.5 - 25.0) > 21.0:
                continue
            d = math.hypot(x + 0.5 - 25.0, y + 0.5 - my)
            if d <= _MOUTH + 2.0 or (d <= _MOUTH + 4.0 and (x + y) % 2 == 0):
                p.set(x, y, _i(PLATE - 1))
    p.streaks(_i(PLATE), _i(PLATE + 1), _i(PLATE - 1), seed=7, share=0.06)
    # the boards the two water gauges are screwed to
    for s in (-1, 1):
        x = 25 + s * _GLASS_Z
        p.rect(x - 2, 11, x + 1, 23, _i(PLATE - 2))
        p.frame(x - 2, 11, x + 1, 23, _i(PLATE - 1), _i(PLATE - 3))
    return p


def _back_picture():
    p = K.Pix(50, 50)
    _rim(p, 25.0, 25.0, PLATE - 1)
    p.streaks(_i(PLATE - 1), _i(PLATE), _i(PLATE - 2), seed=9, share=0.06)
    p.disc(25.0, 25.0, _FLUE_R + 3.0, _i(PLATE))
    p.band(25.0, 25.0, _FLUE_R + 3.0, _FLUE_R + 2.0, _i(PLATE + 1), _i(PLATE), _i(PLATE - 2))
    p.studs(25.0, 25.0, _FLUE_R + 1.5, 10, _i(PLATE + 2), _i(PLATE - 2), start=18.0)
    p.disc(25.0, 25.0, _FLUE_R, _i(0))
    return p


def _mouth_picture():
    """The furnace mouth: a round casting bolted to the front plate, 22 texels across."""
    c = float(_MOUTH)
    p = K.Pix(22, 22)
    p.disc(c, c, c, _i(4))
    p.band(c, c, c, c - 1.0, _i(6), _i(5), _i(2))
    p.studs(c, c, c - 2.0, 12, _i(6), _i(2), start=15.0)
    p.disc(c, c, c - 3.0, _i(2))
    p.band(c, c, c - 3.0, c - 4.0, _i(1), _i(1), _i(3))
    # the ash pit under the door: a low arch, its damper pulled a third open
    p.rect(6, 17, 15, 18, _i(0))
    p.rect(7, 19, 14, 19, _i(0))
    p.rect(6, 16, 15, 16, _i(4))
    p.rect(12, 17, 15, 18, _i(3))
    p.set(15, 18, _i(1))
    return p


_FIRE = (
    "uvuuvuuuuvuuvu",
    "uVVVVVVVVVVVVu",
    "uVuVVuVVuVVuVu",
    "uuVuuVuuVuuVuu",
    "uuuuuuuuuuuuuu",
    "uuuuuuuuuuuuuu",
    "uuuvuuuuuvuuuu",
    "uvuuuvuuvuuuvu",
    "uuvvuvvuvvuvvu",
    "uvvvvvvvvvvvvu",
    "uuvuuvuuuvuuvu",
)


def _fire_picture():
    """What stands behind the door: the dark of the crown, the glare, the bed of coal (the fire's
    two tones and soot, no flames: the director, #522). Its outermost ring is what shows round the
    shut door."""
    p = K.Pix(_DOOR[0] + 2, _DOOR[1] + 2)
    p.text(0, 0, _FIRE)
    return p


def _door_picture():
    w, h = _DOOR
    p = K.Pix(w, h, _i(3))
    p.frame(0, 0, w - 1, h - 1, _i(5), _i(1))
    p.frame(1, 1, w - 2, h - 2, _i(4), _i(2))
    p.set(2, 2, _i(6))
    p.set(w - 3, 2, _i(6))
    p.rect(2, 3, w - 3, 3, _i(2))                       # the lip over the air slots
    return p


def _slots_picture():
    """The three air slots of the fire door, glowing."""
    p = K.Pix(8, 5)
    for y in (0, 2, 4):
        p.rect(0, y, 7, y, "u")
    for x, y in ((1, 0), (5, 0), (3, 2), (6, 2), (2, 4), (4, 4)):
        p.set(x, y, "v")
    return p


def _lining_picture():
    """The inside of the open door, in the fire's light."""
    w, h = _DOOR
    p = K.Pix(w, h, "u")
    p.frame(0, 0, w - 1, h - 1, "V", "V")
    for x, y in ((3, 2), (8, 2), (5, 4), (2, 6), (9, 6), (6, 7)):
        p.set(x, y, "v")
    for y in (3, 5):
        p.rect(2, y, 9, y, "V")
    return p


_DIGITS = {1: (".0.", "00.", ".0.", ".0.", "000"), 2: ("00.", "..0", ".0.", "0..", "000")}


def _number_picture(n):
    """The boiler's number, a brass plate 7 texels square."""
    p = K.Pix(7, 7, "d")
    p.frame(0, 0, 6, 6, "e", "b")
    p.text(2, 1, _DIGITS[n], {"0": _i(0)})
    return p


def _gauge_picture():
    """The pressure gauge's face, 8 texels across."""
    p = K.Pix(8, 8)
    p.disc(4.0, 4.0, 4.0, "c")
    p.band(4.0, 4.0, 4.0, 3.0, "e", "d", "b")
    p.disc(4.0, 4.0, 3.0, "s")
    p.set(2, 5, "q")
    p.set(5, 5, "q")
    p.text(3, 2, ("..0", ".0.", "0.."), {"0": _i(0)})
    return p


def _wheel_picture():
    """The stop valve's handwheel, five spokes, 13 texels across."""
    p = K.Pix(13, 13)
    p.band(6.5, 6.5, 6.5, 5.3, _i(6), _i(5), _i(3))
    for k in range(5):
        a = math.radians(72.0 * k)
        p.line(6, 6, int(round(6 + 5.0 * math.sin(a))), int(round(6 - 5.0 * math.cos(a))), _i(4), only=".")
    p.rect(5, 5, 7, 7, "c")
    p.set(6, 6, "e")
    return p


# ---- the models -----------------------------------------------------------------------------------------
def _hoop(d, x0, x1, proud=1.0):
    """A band round the shell from x0 to x1, `proud` texels over the plate: one box to a flat."""
    hw = (_R + proud) * math.tan(math.pi / _SIDES)
    for k in range(_SIDES):
        j = k if k < _SIDES // 2 else _SIDES - 1 - k
        t = PLATE + BAND[j]
        d.box((x0, _AXIS + _R, -hw), (x1, _AXIS + _R + proud, hw), _fl(t), skip="nsd", seed=0,
              rot=("x", _STEP * (k + 0.5), ((x0 + x1) / 2.0, _AXIS, 0.0)),
              faces={"u": _hoop_picture(j, k >= _SIDES // 2), "w": _fl(t + 1), "e": _fl(t - 1)})


def _saddle(d, x0, x1):
    """A cast saddle: the web the shell lies in (the shell hides what of it is inside), its foot, two ribs."""
    xm = (x0 + x1) / 2.0
    d.box((x0, 1, -18), (x1, 15, 18), IRON)
    d.box((xm - 5.5, 0, -21), (xm + 5.5, 2, 21), IRON_L)
    for z in (-15, 15):
        d.box((xm - 4.5, 2, z - 1), (xm + 4.5, 14, z + 1), IRON)


def _body():
    d = K.Draw(PREFIX + "body", at=_AT, scale=2.0, step=K.TEXEL)
    hw = _R * math.tan(math.pi / _SIDES)
    plates = [_plate_picture(j) for j in range(8)]
    for i in range(_SIDES // 2):
        d.box((0, _AXIS - _R, -hw), (_LEN, _AXIS + _R, hw), _fl(PLATE), skip="nswe", seed=0,
              rot=("x", _STEP * (i + 0.5), (_LEN / 2.0, _AXIS, 0.0)), faces={"u": plates[i], "d": plates[7 - i]})
    for x0, x1 in _HOOPS:
        _hoop(d, x0, x1)
    _saddle(d, 58, 62)
    # the manhole on the crown of the last ring: seat, cover, the bar that holds it down and its nut
    top = _AXIS + _R
    d.tube("y", (61, 0), top - 1, top + 2, 5, IRON, sides=12)
    d.tube("y", (61, 0), top + 2, top + 3, 4, IRON_L, sides=12)
    d.box((55, top + 3, -1), (67, top + 4.5, 1), IRON_L)
    d.box((60, top + 4.5, -1), (62, top + 6, 1), BRASS)
    d.plate("e", (_LEN, _AXIS, 0), 50, 50, _back_picture().sprite(PREFIX + "back"), lift=0.25)
    return d


def _door(number):
    """The front of boiler `number`: the plate and all that is on it, the front saddle, the gauge."""
    d = K.Draw(PREFIX + f"door_{number}", at=_AT, scale=2.0, frame=K.LEAN_WEST, step=K.TEXEL)
    d.plate("w", (0, _AXIS, 0), 50, 50, _front_picture().sprite(PREFIX + "front"), lift=0.25)
    _saddle(d, 1, 5)

    # the furnace mouth, two texels proud of the plate
    d.tube("x", (_FURNACE, 0), -2, 1, _MOUTH, IRON_L, sides=16)
    d.plate("w", (-2, _FURNACE, 0), 22, 22, _mouth_picture().sprite(PREFIX + "mouth"), lift=0.25)
    w, h = _DOOR
    d.plate("w", (-2.25, _DOOR_Y, 0), w + 2, h + 2, _fire_picture().sprite(PREFIX + "fire"), lift=0.25, emit=15)
    d.plate("w", (-2.25, _FURNACE - 7.5, -1.5), 5, 1, K.Pix(5, 1, "u").sprite(PREFIX + "ash"), lift=0.25, emit=15)
    for y in (20, 25):                                  # the hinges, on the south jamb
        d.box((-4.5, y, w / 2.0), (-2, y + 2, w / 2.0 + 2), IRON_L)
    d.box((-3.5, _DOOR_Y - 1, -w / 2.0 - 2.5), (-2, _DOOR_Y + 1, -w / 2.0 - 1), IRON_L)      # the latch's keeper

    def leaf():
        d.box((-4, _DOOR_Y - h / 2.0, -w / 2.0), (-3, _DOOR_Y + h / 2.0, w / 2.0), _fl(2), seed=0,
              faces={"w": _door_picture().sprite(PREFIX + "leaf"), "u": _fl(4), "n": _fl(3), "s": _fl(3)})
        d.plate("w", (-4, _DOOR_Y - 1.5, 0), 8, 5, _slots_picture().sprite(PREFIX + "slots"), lift=0.25, emit=15)
        d.box((-5.5, _DOOR_Y - 2, -w / 2.0 + 1), (-4, _DOOR_Y + 2, -w / 2.0 + 2), IRON_L)    # the latch's grip

    if number == 2:
        with d.turned(("y", _AJAR), about=(-3, _DOOR_Y, w / 2.0)):
            leaf()
            d.plate("e", (-3, _DOOR_Y, 0), w, h, _lining_picture().sprite(PREFIX + "lining"), lift=0.25, emit=15)
    else:
        leaf()

    # the two water gauges: a cock above, a cock below, the glass between them with the water half up
    for s in (-1, 1):
        z = s * _GLASS_Z
        for y in (34, 43):
            d.box((-3, y, z - 1.5), (0, y + 2, z + 1.5), BRASS)
        d.box((-2.5, 36, z - 0.5), (-1.5, 40, z + 0.5), K.flat("porcelain", 1), seed=0)
        d.box((-2.5, 40, z - 0.5), (-1.5, 43, z + 0.5), K.flat("porcelain", 4), seed=0)
    # the number
    d.box((-1, 40, -3.5), (0, 47, 3.5), K.flat("brass", 1), seed=0,
          faces={"w": _number_picture(number).sprite(PREFIX + f"number_{number}")})
    # the blow-down under the plate: pipe, cock, its key
    d.box((-3, 2, -1), (-1, 9, 1), IRON)
    d.box((-4, 4, -2), (0, 7, 2), BRASS)
    d.box((-3, 5, 2), (-2, 6, 6), IRON_L)
    # the pressure gauge on its stem over the top of the plate
    top = _AXIS + _R
    d.box((-2, top, -1), (0, top + 5, 1), BRASS)
    d.tube("x", (top + 9, 0), -3, -1, 4, BRASS, sides=12)
    d.plate("w", (-3, top + 9, 0), 8, 8, _gauge_picture().sprite(PREFIX + "gauge"), lift=0.25)
    return d


def _dome():
    """What stands on the shell: the lever safety valve, the steam dome with the stop valve."""
    d = K.Draw(PREFIX + "dome", at=_AT, scale=2.0, frame=K.LEAN_WEST, step=K.TEXEL)
    top = _AXIS + _R                                    # 56: the crown
    # the steam dome
    d.tube("y", (_DOME, 0), top - 2, top + 12, 8, IRON, sides=12)
    d.ring("y", (_DOME, top + 1, 0), 8.75, 1.5, 2, IRON_L, sides=12)
    d.ring("y", (_DOME, top + 12, 0), 8.5, 1.0, 2, BRASS, sides=12)
    d.ball((_DOME, top + 12, 0), 8, IRON, sides=12, layers=3, squash=0.5, part=(0.0, 1.0))
    # the stop valve on it: body, the flange that looks up, bonnet and spindle to the south, the handwheel
    d.tube("y", (_DOME, 0), top + 15, top + 22, 3, IRON_L, sides=8)
    d.tube("y", (_DOME, 0), top + 22, top + 24, 5, IRON_L, sides=12)
    d.tube("z", (_DOME, top + 18.5), 2, 7, 2, BRASS, sides=8)
    d.tube("z", (_DOME, top + 18.5), 7, 11, 0.75, IRON_L, sides=4)
    d.ring("z", (_DOME, top + 18.5, 10.5), 6.0, 1.0, 1.0, IRON_L, sides=16)
    wheel = _wheel_picture().sprite(PREFIX + "wheel")
    d.plate("s", (_DOME, top + 18.5, 10.5), 13, 13, wheel)
    d.plate("n", (_DOME, top + 18.5, 10.5), 13, 13, wheel)
    # the safety valve: seat, column, the lever from its fulcrum over the valve to the weight
    d.tube("y", (_VALVE, 0), top - 1, top + 2, 3.5, IRON_L, sides=12)
    d.tube("y", (_VALVE, 0), top + 2, top + 10, 2, BRASS, sides=8)
    d.tube("y", (_VALVE, 0), top + 10, top + 11, 3, BRASS, sides=12)
    d.box((_VALVE - 0.5, top + 11, -0.5), (_VALVE + 0.5, top + 12, 0.5), IRON_L)
    d.box((_VALVE - 7, top - 1, -1), (_VALVE - 5, top + 13, 1), IRON)
    d.box((_VALVE - 7, top + 12, -0.5), (_VALVE + 15, top + 14, 0.5), IRON_L)
    d.box((_VALVE + 12.5, top + 10, -0.5), (_VALVE + 13.5, top + 12, 0.5), IRON)
    d.tube("y", (_VALVE + 13, 0), top + 5, top + 10, 2.5, RED, sides=12)
    return d


def _flue(name, turn):
    """The flue from the back plate: straight on into the chimney, or east and then north into it."""
    d = K.Draw(PREFIX + name, at=_AT, scale=2.0, step=K.TEXEL)
    sheet = IRON_D
    if not turn:
        end = (CHIMNEY_WEST - FRONT_X) * 16.0
        d.tube("x", (_AXIS, 0), _LEN, end, _FLUE_R, sheet, sides=12)
        d.ring("x", (_LEN + 1.5, _AXIS, 0), _FLUE_R + 0.75, 1.5, 2, IRON, sides=12)
        d.ring("x", (end - 1.0, _AXIS, 0), _FLUE_R + 0.75, 1.5, 2, IRON, sides=12)
        return d
    end = (CHIMNEY_SOUTH - AXES_Z[1]) * 16.0            # -40: the foot's south face
    a, b = _TURN
    d.hose([(_LEN, _AXIS, 0), (a, _AXIS, 0), (b, _AXIS, a - b), (b, _AXIS, end)], _FLUE_R, sheet, sides=12, lap=0.42)
    d.ring("x", (_LEN + 1.5, _AXIS, 0), _FLUE_R + 0.75, 1.5, 2, IRON, sides=12)
    d.ring("x", (a - 3.0, _AXIS, 0), _FLUE_R + 0.75, 1.5, 2, IRON, sides=12)
    d.ring("z", (b, _AXIS, a - b - 3.0), _FLUE_R + 0.75, 1.5, 2, IRON, sides=12)
    d.ring("z", (b, _AXIS, end + 1.0), _FLUE_R + 0.75, 1.5, 2, IRON, sides=12)
    return d


@functools.lru_cache(maxsize=None)
def _drawn():
    built = [_body(), _door(1), _door(2), _dome(), _flue("flue", False), _flue("flue_turn", True)]
    return {d.m.name[len(PREFIX):]: d for d in built}


def models():
    return {d.m.name: d.m for d in _drawn().values()}


def build(canvas, origin=(0, 0, 0)):
    """Place the two boilers; returns the number of display entities."""
    drawn = _drawn()
    n = 0
    for i, z in enumerate(AXES_Z):
        at = (FRONT_X + STAND[0], FLOOR + STAND[1], z + STAND[2])
        for name in ("body", f"door_{i + 1}", "dome", "flue_turn" if i else "flue"):
            n += K.place(canvas, drawn[name], at, origin)
    return n
