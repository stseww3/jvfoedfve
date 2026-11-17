"""interiors/_domefittings -- what hangs and lies about the great dome room: the small things of the
night's work. Part of the package interiors/domeroom (card plan/packages/interiors/domeroom.md);
domeroom.py calls it. Made for plan/fine.md: every piece is one this room uses tonight, each in its
place by the thing it serves, and each drawn down to what is seen from two blocks away.

    the eyepiece rack    on the lining west of the recorder's bay, beside the clock: two shelves of
                         brass eyepieces standing in their holes, a ticket under each. One hole is
                         empty: that eyepiece is in the telescope
    the speaking tube    on the north wall between the cabinets and the hand wheel: a brass pipe up
                         from the time room below, its mouthpiece at the height of a mouth, the
                         whistle hanging beside it on its chain; next to it the push of the bell
    the greatcoat, cap   on the coat stand inside the north door: whoever observes has come in
                         from the terrace. The coat hangs by its loop and sways a little: the slit
                         is open, and the night's air comes down through it
    the desk's things    on the record desk beside the open book, at the writer's right hand: a
                         slide rule and half a cup of tea that still steams; at his left the
                         ephemeris, shut (props/paper's book)
    the barometer        props/instruments' banjo barometer with its thermometer, on the cheek of
                         the recorder's bay: both are read into the record with every observation

Nothing of it is lit (the barometer's marks glow as the family's do), nothing is red, and nothing
has a letter on it: a ticket's figure is a mark of ink.

    models()                -> {name: Model}
    place(canvas, origin, stand, desk_top)   -> the number of display entities
"""
import functools
import importlib
import math

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import palette as P
from ..common import skeleton as S
from ..props import _kit as K

PREFIX = "int_domeroom_"
FEET = float(S.ROOF_STAND)                      # the top of the boards
CX, CZ = S.DOME_CENTRE
SMALL = getattr(M, "SMALL", 0.25)               # the band of view range of what lies on a desk

# --- where they are (scene coordinates, blocks) -----------------------------------------------------
# the rack: on the north face of the lining's columns (1..2, 10), its foot at the height of a chest
RACK = ((CX - 2.0, FEET + 1.9375, CZ + 10.0), "north")
# the speaking tube: on the south face of the lining's column (2, -10), from the boards up
TUBE = ((CX - 1.5, FEET, CZ - 9.0), "south")
# the barometer: on the west cheek of the recorder's bay, the east face of the column (2, 10)
BAROMETER = ((CX - 1.0, FEET + 1.3125, CZ + 10.5), "east")
# the desk's things: the middle of the desk's top is (4.5, 10.5625), the open book lies on it (10
# texels wide, from 5.5 north of the middle to 1.5 south of it); the stationery drawers stand on
# the back corners from 3 south of the middle on
DESK_THINGS = (CX + 0.5, CZ + 10.5625)
CUP = (-10.5, -0.5)                             # the cup, (x, z) from there in texels: at the right hand
EPHEMERIS = (10.25, -1.5, 188.0)                # the shut book: (x, z) likewise and its yaw
# the coat stand's hooks (props/furniture: five, 72 degrees apart from 36 on, their eyes 4.9 texels
# from the post and 29.1 above the floor; a hook at a degrees points (cos a, -sin a) in (x, z)): the
# coat on the one that looks into the room, the cap on the next, which looks along the wall
STAND_HOOK = (4.9, 29.1)
COAT_HOOK, CAP_HOOK = 252.0, 180.0
COAT_SWAY = (1.5, 150)                          # degrees to either side, ticks there and back
STEAM = ("white_smoke", 46, 0.012)              # the particle, ticks from wisp to wisp, blocks a tick upwards
STEAM_OVER = 0.19                               # blocks over the desk's top a wisp starts: the cup's rim

WOOD = P.mat("dark_wood")
WOOD_D = P.mat("dark_wood", base=1)
WOOD_L = P.mat("dark_wood", base=3)
CLOTH = P.mat("enamel_cloth", base=1)           # the greatcoat: the station's dark blue
CLOTH_D = P.mat("enamel_cloth", base=0)
CHINA = P.mat("porcelain")
LENS = K.flat("iron", 1)                        # the eye lens of an eyepiece, dark in its cell
TICKET = dict(c=P.RAMPS["cream"][2], k=P.RAMPS["iron"][1])
RULE = dict(c=P.RAMPS["cream"][3], d=P.RAMPS["cream"][1], k=P.RAMPS["iron"][1])


def _other(line, name):
    """Another package's module when it is in the tree, else None."""
    try:
        return importlib.import_module(f"..{line}.{name}", __package__)
    except ModuleNotFoundError as e:
        if e.name != f"{__package__.rsplit('.', 1)[0]}.{line}.{name}":
            raise
        return None


def _sprite(name, rows, colours):
    return Sprite(PREFIX + name, rows, colours)


# --- the models -------------------------------------------------------------------------------------
# an eyepiece: (x on the shelf, the barrel's radius, its height): the long thin ones are the high powers
UPPER = ((-10.5, 1.25, 5.5), (-6.0, 1.25, 5.0), (-1.5, 1.5, 4.5), (3.0, 1.5, 4.0), (7.5, 1.75, 4.0), (11.5, 1.0, 3.0))
LOWER = ((-9.5, 2.25, 6.0), (-3.5, 2.25, 5.5), (2.5, 2.5, 5.0))
EMPTY = 9.0                                     # the hole of the eyepiece that is in the telescope


def _eyepiece(m, x, foot, radius, tall):
    """A brass eyepiece standing in its hole, the eye lens up: the barrel, a knurled collar a third
    of the way up, the dark cup of the eye lens."""
    z = 3.25
    m.tube("y", (x, z), foot, foot + tall, radius, K.BRASS, sides=8, cap=K.flat("brass", 2))
    m.tube("y", (x, z), foot + tall * 0.3, foot + tall * 0.3 + 1.0, radius + 0.5, K.BRASS_D, sides=8,
           cap=K.flat("brass", 4))
    m.tube("y", (x, z), foot + tall, foot + tall + 0.25, radius - 0.5, LENS, sides=8, cap=LENS)


def _rack():
    """The eyepiece rack. 31 px wide, 21.5 px tall, 6 px off the wall. Anchor: the point of the wall
    behind the middle of its foot."""
    m = M.Model(PREFIX + "eyepieces")
    m.box((-15.0, 0.0, 0.0), (15.0, 21.0, 1.0), WOOD_D, skip="n", grain="x")                  # the back board
    for x in (-15.0, 14.0):
        m.box((x, 0.0, 1.0), (x + 1.0, 21.0, 5.5), WOOD, grain="y")                           # the cheeks
    m.box((-15.5, 20.0, 0.0), (15.5, 21.5, 6.0), WOOD, grain="x")                             # the top
    for y in (1.0, 11.0):                                                                     # two shelves
        m.box((-14.0, y, 1.0), (14.0, y + 1.0, 5.5), WOOD_L, grain="x")
        m.box((-14.0, y - 1.0, 5.0), (14.0, y, 5.5), WOOD, grain="x")                         # its front lip
    for x, radius, tall in UPPER:
        _eyepiece(m, x, 12.0, radius, tall)
    for x, radius, tall in LOWER:
        _eyepiece(m, x, 2.0, radius, tall)
    m.ring("y", (EMPTY, 2.125, 3.25), 2.25, 0.75, 0.25, K.BRASS_D, sides=8)                   # the empty hole's rim
    m.tube("y", (EMPTY, 3.25), 2.0, 2.05, 1.75, LENS, sides=8, cap=LENS)                      # and its dark
    # a ticket under every hole, on the lip: the focal length, a figure one reads from a hand away
    for x in [e[0] for e in UPPER]:
        m.box((x - 1.0, 10.0, 5.5), (x + 1.0, 11.0, 5.625), K.flat("cream", 2), skip="nudew",
              faces={"s": _sprite("ticket", ["kc"], TICKET)})
    for x in [e[0] for e in LOWER] + [EMPTY]:
        m.box((x - 1.5, 0.0, 5.5), (x + 1.5, 1.0, 5.625), K.flat("cream", 2), skip="nudew",
              faces={"s": _sprite("ticket_wide", ["kck"], TICKET)})
    for x in (-13.0, 13.0):                                                                   # the screws that hold it
        m.box((x - 0.5, 18.0, 1.0), (x + 0.5, 19.0, 1.25), K.flat("brass", 4))
    return m


def _tube():
    """The speaking tube and the bell push. The pipe stands 26 px tall, 1.75 px off the wall on two
    clips; its mouthpiece reaches 8 px into the room. The whistle hangs on the side the cabinets
    are on (+x), the push is on the other. Anchor: the point of the wall behind the pipe, at the
    floor."""
    m = M.Model(PREFIX + "voicepipe")
    z = 1.75
    m.tube("y", (0.0, z), 0.0, 0.75, 2.5, K.BRASS_D, sides=8, cap=K.flat("brass", 2))         # the floor flange
    m.tube("y", (0.0, z), 0.75, 25.0, 1.25, K.BRASS, sides=8)                                 # the pipe
    for y in (7.0, 19.0):                                                                     # the clips, a screw in each ear
        m.box((-2.5, y, 0.0), (2.5, y + 1.0, z + 1.5), K.IRON_D)
        for x in (-2.0, 2.0):
            m.box((x - 0.25, y + 0.25, z + 1.5), (x + 0.25, y + 0.75, z + 1.625), K.flat("iron", 5))
    m.ball((0.0, 25.0, z), 1.5, K.BRASS, sides=8, layers=4)                                   # the elbow
    m.tube("z", (0.0, 25.0), z, 5.0, 1.25, K.BRASS, sides=8)                                  # out into the room
    for a, b, radius in ((5.0, 6.0, 1.75), (6.0, 7.0, 2.5), (7.0, 7.75, 3.25)):               # the mouthpiece's flare
        m.tube("z", (0.0, 25.0), a, b, radius, K.BRASS, sides=8, cap=K.flat("brass", 4))
    m.tube("z", (0.0, 25.0), 7.75, 7.875, 2.5, LENS, sides=8, cap=LENS)                       # its dark mouth
    # the whistle, out of the mouth and hanging by its chain from the upper clip
    m.box((3.0, 14.0, z + 0.5), (3.25, 19.5, z + 0.75), K.flat("iron", 3))                    # the chain
    m.tube("y", (3.125, z + 0.625), 12.0, 14.0, 0.75, K.flat("cream", 2), sides=8, cap=K.flat("cream", 3))
    m.tube("y", (3.125, z + 0.625), 11.5, 12.0, 1.0, K.BRASS_D, sides=8, cap=K.flat("brass", 3))
    # the bell push: a turned rose of wood, a brass ring, the bone button; its wire goes up the wall
    bx, by = -7.0, 22.0
    m.tube("z", (bx, by), 0.0, 1.0, 2.5, WOOD, sides=8, cap=K.flat("dark_wood", 3))
    m.ring("z", (bx, by, 1.25), 1.5, 0.75, 0.5, K.BRASS, sides=8)
    m.tube("z", (bx, by), 1.0, 2.0, 0.75, K.flat("cream", 3), sides=8, cap=K.flat("cream", 3))
    m.box((bx - 0.25, by + 2.5, 0.0), (bx + 0.25, 32.0, 0.5), K.flat("iron", 1), grain="y")
    for y in (26.0, 30.0):                                                                    # its staples
        m.box((bx - 0.75, y, 0.0), (bx + 0.75, y + 0.5, 0.75), K.flat("iron", 4))
    return m


def _coat():
    """The greatcoat on its hook: dark blue cloth, the collar turned down, two rows of brass
    buttons, the sleeves hanging straight. It hangs 25 px long and 12 wide. Anchor: the eye of the
    hook, which its loop is on; the model's z looks out of the coat's front."""
    m = M.Model(PREFIX + "greatcoat")
    m.box((-0.25, -1.5, -0.25), (0.25, 0.0, 0.25), CLOTH_D)                                   # the loop
    m.box((-3.0, -3.5, -1.5), (3.0, -1.5, 1.5), CLOTH_D, grain="x")                           # the collar
    m.box((-4.5, -10.0, -1.5), (4.5, -3.5, 1.5), CLOTH, grain="y")                            # the shoulders
    m.box((-5.0, -25.0, -1.75), (5.0, -10.0, 1.75), CLOTH, grain="y")                         # the skirt, a little fuller
    for side in (-1.0, 1.0):
        a, b = sorted((side * 4.5, side * 6.0))
        m.box((a, -18.0, -1.25), (b, -4.0, 1.25), CLOTH, grain="y")                           # a sleeve
        m.box((a - 0.125, -18.5, -1.375), (b + 0.125, -16.5, 1.375), CLOTH_D)                 # its cuff
        for y in (-7.0, -11.0, -15.0):                                                        # a row of buttons
            m.box((side * 1.75 - 0.5, y - 0.5, 1.75), (side * 1.75 + 0.5, y + 0.5, 2.0), K.flat("brass", 4))
    m.box((-0.125, -25.0, 1.75), (0.125, -3.5, 1.8125), CLOTH_D)                              # where the fronts meet
    m.box((-5.0, -25.0, -1.8125), (5.0, -24.0, 1.8125), CLOTH_D, grain="x")                   # the hem
    return m


def _cap():
    """The cap on the next hook: dark blue cloth, a patent peak, a brass badge on its band. Anchor:
    the eye of the hook, inside the crown; the peak looks along the model's z."""
    m = M.Model(PREFIX + "cap")
    m.tube("y", (0.0, 0.0), -1.5, 0.0, 3.0, CLOTH_D, sides=8, cap=K.flat("enamel", 0))        # the band
    m.tube("y", (0.0, 0.0), 0.0, 1.5, 3.75, CLOTH, sides=8, cap=K.flat("enamel", 1))          # the crown, wider
    m.box((-2.5, -1.75, 2.5), (2.5, -1.25, 4.75), K.flat("iron", 1))                          # the peak
    m.box((-0.75, -1.25, 3.0), (0.75, 0.0, 3.125), K.flat("brass", 4))                        # the badge
    return m


def _desk_things():
    """What lies on the record desk at the writer's right hand: a slide rule with its cursor, and
    a cup of tea on its saucer. Anchor: the middle of the desk's top; the model lies with the
    world's directions (x east, z south), so the writer, who looks south, has -x at his right."""
    m = M.Model(PREFIX + "desk_things")
    # the slide rule: boxwood faced with white, graduated along both edges, the brass cursor on it
    scale = _sprite("rule", ["kckckkck", "dddddddd"], RULE)
    with m.turned(("y", -9.0), about=(-10.0, 0.0, -5.0)):
        m.box((-14.0, 0.0, -5.75), (-6.0, 0.5, -4.25), K.flat("cream", 2), faces={"u": scale}, grain="x")
        m.box((-11.0, 0.0, -6.0), (-10.0, 0.75, -4.0), K.flat("brass", 3))                    # the cursor
    # the cup: a saucer, the cup's wall, the tea half way down it, the handle
    x, z = CUP
    m.tube("y", (x, z), 0.0, 0.25, 2.5, CHINA, sides=8, cap=K.flat("porcelain", 3))
    m.ring("y", (x, 1.5, z), 1.25, 0.5, 2.5, CHINA, sides=8)
    m.tube("y", (x, z), 0.25, 1.5, 1.0, K.flat("dark_wood", 2), sides=8, cap=K.flat("old_copper", 1))
    m.box((x - 2.25, 0.75, z - 0.25), (x - 1.5, 2.25, z + 0.25), CHINA)
    return m


@functools.lru_cache(maxsize=None)
def _models():
    return {m.name: K.settle(m) for m in (_rack(), _tube(), _coat(), _cap(), _desk_things())}


def models():
    """{name: Model} what the room's fittings are made of."""
    return dict(_models())


# --- where they go ----------------------------------------------------------------------------------
def hook(stand, degrees):
    """The eye of one of the coat stand's hooks, in scene coordinates: `stand` is (x, z) of the
    stand's foot, which the room places looking south."""
    reach, up = STAND_HOOK
    a = math.radians(degrees)
    return (stand[0] + reach * math.cos(a) / 16.0, FEET + up / 16.0, stand[1] - reach * math.sin(a) / 16.0)


def cup_rim(desk_top):
    """Where the tea's steam starts: over the middle of the cup, in scene coordinates."""
    return (DESK_THINGS[0] + CUP[0] / 16.0, FEET + desk_top + STEAM_OVER, DESK_THINGS[1] + CUP[1] / 16.0)


def place(canvas, origin=(0, 0, 0), stand=None, desk_top=None):
    """Hang and lay the fittings. `stand` is (x, z) of the coat stand's foot and `desk_top` the
    height of the record desk's top above the boards; a piece whose furniture the room has not got
    is left out. Returns the number of display entities."""
    got = _models()
    MK = _other("motion", "_kit")
    n = 0
    for name, (pos, facing) in (("eyepieces", RACK), ("voicepipe", TUBE)):
        n += K.put(canvas, got[PREFIX + name], pos, mount="wall", facing=facing, origin=origin)
    instruments = _other("props", "instruments")
    if instruments is not None and "barometer" in getattr(instruments, "SPEC", {}):
        n += instruments.place(canvas, "barometer", BAROMETER[0], facing=BAROMETER[1], origin=origin)
    if stand is not None:
        # a piece's front looks the way its hook points: yaw 0 is south, 90 west
        n += K.put(canvas, got[PREFIX + "greatcoat"], hook(stand, COAT_HOOK), yaw=270.0 - COAT_HOOK, origin=origin)
        if MK is not None:
            MK.swing(canvas, "z", *COAT_SWAY)
        x, y, z = hook(stand, CAP_HOOK)
        n += K.put(canvas, got[PREFIX + "cap"], (x, y + 0.03125, z), yaw=270.0 - CAP_HOOK, origin=origin)
    if desk_top is not None:
        top = FEET + desk_top
        n += K.put(canvas, got[PREFIX + "desk_things"], (DESK_THINGS[0], top, DESK_THINGS[1]), yaw=0.0, origin=origin,
                   view=SMALL)
        paper = _other("props", "paper")
        if paper is not None and "logbook_shut" in getattr(paper, "KINDS", ("logbook_shut",)):
            x, z, yaw = EPHEMERIS
            n += paper.place(canvas, "logbook_shut", (DESK_THINGS[0] + x / 16.0, top, DESK_THINGS[1] + z / 16.0), yaw=yaw,
                             origin=origin, view=SMALL)
        if MK is not None:
            particle, every, speed = STEAM
            MK.puff(canvas, cup_rim(desk_top), particle, every, count=0, spread=(0.0, 1.0, 0.0), speed=speed,
                    origin=origin)
    return n
