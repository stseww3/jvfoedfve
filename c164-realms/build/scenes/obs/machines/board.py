"""machines/switchboard-boiler, the switchboard of the power house (plan/ART-PLAN.md 5.3, 7.2;
plan/parts/A5-machines.md 2.6; card plan/packages/machines/switchboard-boiler.md). The boilers are
machines/boiler.py.

What it is. A board of three slate slabs in an iron frame, standing free before the west wall with
its face to the room, stayed to the wall at its head: three blocks high over a base course of the
materials line's instrument panels (blocks). The middle slab is the dynamo's: its voltmeter between
two pilot lamps, the main switch, the two handwheels of the field rheostats. The slabs to either
side are the feeders': an ammeter and two knife switches each; the last switch of the south slab
stands open. Over the head run the two bus bars on porcelain posts, the rear one higher, and at
the south end stand the two lead-in insulators where the dynamo's leads arrive (LEAD_IN).

Where it stands. Before the west wall, north of the dynamo: the base course in column X, cells
Z[0]..Z[1], its faces to the east; behind it the alley between board and wall.

    x  the slabs' face is the plane x = FACE_X, two texels behind the faces of the base course
    y  the floor is S.LOWER_GROUND; the base course is one block, the slabs stand on it
    z  the board runs from Z[0] to Z[1] + 1

How it is lit. Each slab is one piece, drawn in the kit's leaning frame so that what looks into the
room is shown at its full tone; its entity stands in the air before it, in the light of the room's
two shaded lamps before the board, whose sources build() hands to the sky line (LIGHTS: the same
cells and level as interiors/powerhouse hangs its lamps at). The meters' ticks and the pilot lamps
glow by themselves. The three pointers are pieces of their own and tremble.

Every model is drawn in texels in the board's own frame: x from the slabs' face into the room,
y up from the floor, z along the board from its north end.
"""
import functools
import math

from artkit.blocks import st

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..motion import _kit as MK
from . import _powerkit as K

PREFIX = "mach_board_"

# --- where it stands (scene coordinates, blocks) ------------------------------------------------------
FLOOR = float(S.LOWER_GROUND)           # -6.0
X = 70                                  # the column of the base course
Z = (26, 32)                            # its cells: seven
FACING = "east"
FACE_X = X + 1.0 - 0.125                # 70.875: the slabs' face
WALL_X = 69.0                           # the room's west wall, where the stays end (site/powerhouse.ROOM)
BASE = ("louvre", "fuses", "bus_switch", "nameplate", "bus_switch", "fuses", "louvre")  # north to south
SLAB_Y = (1.0, 4.0)                     # the slabs stand on the base course and are three blocks high

# --- the board (its own frame, texels) ----------------------------------------------------------------
_Y0, _Y1 = 16, 64                       # the slabs
_T = 4                                  # ... are 4 texels of slate
_SLABS = {"north": (0, 32), "main": (32, 80), "south": (80, 112)}
_STAND = {"north": (10, 40, 24), "main": (10, 40, 56), "south": (10, 40, 104)}      # where each slab's entity stands
_METER_Y = 54
_METER_R = 8
_METERS = {"north": (16, "A", -22.0, 3.0, 90), "main": (56, "V", -34.0, 2.0, 130), "south": (96, "A", 12.0, 4.0, 170)}
#           middle along the board, letter, where the pointer rests (degrees, negative is to the right of
#           whoever reads it), how far it trembles to either side, in how many ticks there and back
_SWITCH_Y = (24, 43)                    # a knife switch, foot to head
_SWITCHES = {"north": ((9, False), (23, False)), "south": ((89, False), (103, True))}   # middle, standing open
_OPEN = 55.0                            # how far the open switch leans out of its jaws, degrees
_RAIL = (64, 66)                        # the head rail
_BAR_F = (-2, 68)                       # the front bus bar: its west face and its underside
_BAR_R = (-6, 72)                       # the rear one
_BELLS = ((-1.5, 105.0), (-5.5, 109.5)) # the two lead-in insulators: x, z
_BELL_TOP = 76

# --- for the others (scene coordinates, blocks) -------------------------------------------------------
# The light the board stands in: the sources of the room's two shaded lamps before it (third grade
# on the slabs, which stand a cell or two away). build() hands them to the sky line.
LIGHTS = [((X + 1.5, FLOOR + 2.5, 28.5), 10), ((X + 1.5, FLOOR + 2.5, 31.5), 10)]
# The tops of the two lead-in insulators at the south end: the dynamo's leads end here (interiors).
LEAD_IN = tuple((FACE_X + x / 16.0, FLOOR + _BELL_TOP / 16.0, Z[0] + z / 16.0) for x, z in _BELLS)
# For the motion line: the jaws of the switch that stands open (a spark now and then).
OPEN_SWITCH = (FACE_X + 3.0 / 16.0, FLOOR + (_SWITCH_Y[1] - 1.5) / 16.0, Z[0] + 103.0 / 16.0)
KEEP_CLEAR = ((X + 0.0, FLOOR, float(Z[0]), X + 1.5, FLOOR + _BELL_TOP / 16.0, Z[1] + 1.0),
              (WALL_X, FLOOR + 62.0 / 16.0, float(Z[0]), X + 0.5, FLOOR + 64.0 / 16.0, Z[1] + 1.0))     # the stays

# --- materials (the palette's, and nothing else) ------------------------------------------------------
IRON = P.mat("iron")
IRON_L = P.mat("iron", base=4)
IRON_D = P.mat("iron", base=2)
BRASS = P.mat("brass")
PORCELAIN = P.mat("porcelain")
WOOD = P.mat("dark_wood")


# ---- the pictures (drawn as whoever stands before the board sees them: left is south) -------------------
def _slab_picture(name, w, labels):
    """A slab's face: polished slate with a few pale veins, a chamfer, a screw in each corner, and
    the engraved brass labels under what is mounted on it (labels: left texel, top texel, width)."""
    seed = sum(ord(c) for c in name)
    p = K.Pix(w, _Y1 - _Y0, "D")
    p.specks("D", "E", "C", seed, share=0.08)
    for k in range(2 + w // 24):                        # veins: thin, wandering down to the right
        x = int(K.dice(k, 1, seed) * w)
        for y in range(1, 47):
            r = K.dice(k * 97 + y, 2, seed)
            x += 1 if r > 0.62 else -1 if r < 0.08 else 0
            if r > 0.9 or not 1 <= x < w - 1:
                continue
            p.set(x, y, "F" if r < 0.2 else "E")
    p.frame(0, 0, w - 1, _Y1 - _Y0 - 1, "F", "B")
    for x, y in ((2, 2), (w - 3, 2), (2, 44), (w - 3, 44)):
        p.set(x, y, "e")
        p.set(x, y + 1, "A")
    for x, y, n in labels:
        p.rect(x, y, x + n - 1, y + 2, "c")
        p.rect(x, y, x + n - 1, y, "d")
        p.rect(x, y + 2, x + n - 1, y + 2, "b")
        for i in range(1, n - 1, 2):
            p.set(x + i, y + 1, "0")
    return p


def _back_picture(name, w, risers):
    """A slab's back, as the alley sees it: bare slate, the copper straps that rise to the bars."""
    p = K.Pix(w, _Y1 - _Y0, "B")
    p.specks("B", "C", "A", sum(ord(c) for c in name) + 5, share=0.08)
    for x, y in risers:
        p.rect(x, 0, x + 1, y, "b")
        p.rect(x, 0, x, y, "c")
        p.rect(x - 1, y - 1, x + 2, y + 1, "d")
        p.set(x, y, "f")
    return p


def _dial_picture(letter):
    """A meter's face: the brass bezel, the cream dial with its letter."""
    c = float(_METER_R)
    p = K.Pix(16, 16)
    p.disc(c, c, c, "c")
    p.band(c, c, c, c - 1.0, "f", "d", "a")
    p.band(c, c, c - 1.0, c - 2.0, "b", "b", "d")
    p.disc(c, c, c - 2.0, "s")
    p.band(c, c, c - 2.0, c - 3.0, "q", "r", "s")
    glyph = {"V": ("0.0", "0.0", ".0."), "A": (".0.", "0.0", "000", "0.0")}[letter]
    p.text(7 - len(glyph[0]) // 2, 10, glyph, {"0": "1"})
    return p


def _ticks_picture():
    """The ticks of a meter's scale, which glow: eight, on the upper arc of the dial."""
    p = K.Pix(16, 16)
    for a in (-56.0, -40.0, -24.0, -8.0, 8.0, 24.0, 40.0, 56.0):
        r = math.radians(a)
        p.set(int(math.floor(8.0 + 4.7 * math.sin(r))), int(math.floor(8.0 - 4.7 * math.cos(r))), "j")
    return p


def _wheel_picture():
    """A rheostat's handwheel: five spokes, a brass boss, 11 texels across."""
    p = K.Pix(11, 11)
    p.band(5.5, 5.5, 5.5, 4.4, "5", "4", "2")
    for k in range(5):
        a = math.radians(72.0 * k)
        p.line(5, 5, int(round(5 + 4.0 * math.sin(a))), int(round(5 - 4.0 * math.cos(a))), "3", only=".")
    p.rect(4, 4, 6, 6, "c")
    p.set(5, 5, "e")
    return p


def _lens_picture():
    p = K.Pix(3, 3, "w")
    p.set(1, 1, "x")
    for x, y in ((0, 0), (2, 0), (0, 2), (2, 2)):
        p.set(x, y, "v")
    return p


def _strip_picture(n):
    """The cover strip over a joint of two slabs: a flat iron bar with a screw every half block."""
    p = K.Pix(3, n, "2")
    p.rect(0, 0, 0, n - 1, "3")
    p.rect(2, 0, 2, n - 1, "1")
    for y in range(3, n, 8):
        p.set(1, y, "5")
        p.set(1, y + 1, "0")
    return p


# ---- the models -----------------------------------------------------------------------------------------
def _knife(d, zc, y0, y1, half, blades, opened=False):
    """A knife switch on the slab: a porcelain pad at foot and head, brass hinge posts and jaws, the
    blades, and the wooden bar that joins the blades at their upper ends, with its grip. The bar
    lies over the blades' ends; nothing of a blade stands above it."""
    d.box((0, y0, zc - half), (1, y0 + 4, zc + half), PORCELAIN)
    d.box((0, y1 - 4, zc - half), (1, y1, zc + half), PORCELAIN)
    d.box((1, y1 - 2.5, zc - half + 1), (3.5, y1 - 1, zc + half - 1), BRASS)            # the jaws
    for s in blades:
        d.box((1, y0 + 1, zc + s - 1), (3.5, y0 + 3, zc + s + 1), BRASS)                # a hinge post

    def moving():
        for s in blades:
            d.box((2, y0 + 2, zc + s - 0.5), (3.5, y1 - 2.5, zc + s + 0.5), K.flat("brass", 4), seed=0,
                  faces={"n": K.flat("brass", 2), "s": K.flat("brass", 2)})
        d.box((2, y1 - 5, zc - half + 0.5), (4.5, y1 - 2.5, zc + half - 0.5), WOOD)
        d.box((4.5, y1 - 5, zc - 1), (7, y1 - 2.5, zc + 1), WOOD)

    if opened:
        with d.turned(("z", -_OPEN), about=(2.75, y0 + 2, zc)):
            moving()
    else:
        moving()


def _panel(name):
    z0, z1 = _SLABS[name]
    w = z1 - z0
    d = K.Draw(PREFIX + "panel_" + name, at=_STAND[name], scale=2.0, frame=K.LEAN_EAST, step=K.TEXEL)

    def u(z):                                           # a place along the board, in the slab's picture
        return z1 - z

    mz, letter = _METERS[name][0], _METERS[name][1]
    labels, risers = [], []
    if name == "main":
        labels = [(u(mz) - 5, 38, 10), (u(72) - 4, 38, 8), (u(40) - 4, 38, 8)]
        risers = [(mz - z0 - 6, 30), (mz - z0 + 5, 30)]
    else:
        for zc, _ in _SWITCHES[name]:
            labels.append((u(zc) - 3, 43, 6))
            risers += [(zc - z0 - 3, 12), (zc - z0 + 2, 12)]
    face = _slab_picture(name, w, labels).sprite(PREFIX + "slab_" + name)
    back = _back_picture(name, w, risers).sprite(PREFIX + "back_" + name)
    d.box((-_T, _Y0, z0), (0, _Y1, z1), K.flat("slate", 2), skip="d", seed=0, faces={"e": face, "w": back})

    # the frame: head rail, a post behind each joint with its cover strip before it, the stays to the wall
    d.box((-7, _RAIL[0], z0), (1, _RAIL[1], z1), IRON_L)
    strip = _strip_picture(_Y1 - _Y0 + 2).sprite(PREFIX + "strip")
    joints = {"north": (1.5,), "main": (z0, z1), "south": (z1 - 1.5,)}[name]
    for zj in joints:
        d.box((-7, _Y0, zj - 1.5), (-_T, _Y1, zj + 1.5), IRON)
        d.box((0, _Y0, zj - 1.5), (1, _RAIL[1], zj + 1.5), K.flat("iron", 2), seed=0, faces={"e": strip})
        d.box(((WALL_X - FACE_X) * 16.0, _RAIL[0] - 2, zj - 1), (-7, _RAIL[0], zj + 1), IRON)

    # the bus bars over the head, each on its porcelain posts; the rear bar stands higher
    ends = {"north": (6, z1), "main": (z0, z1), "south": (z0, None)}[name]
    for (x, y), posts, bell in ((_BAR_F, (8, 24, 40, 56, 72, 88), _BELLS[0]), (_BAR_R, (16, 48, 64, 96), _BELLS[1])):
        a, b = ends[0], ends[1] if ends[1] is not None else bell[1]
        d.box((x, y, a), (x + 1, y + 2, b), K.flat("brass", 3), seed=0, faces={"u": K.flat("brass", 4), "e": K.flat("brass", 4)})
        for zp in posts:
            if z0 <= zp < z1:
                d.box((x - 1, _RAIL[1], zp - 1), (x + 2, y, zp + 1), PORCELAIN)
    if name == "south":                                 # the lead-in insulators: skirt, neck, cap, stud
        for x, z in _BELLS:
            d.tube("y", (x, z), _RAIL[1], _RAIL[1] + 5, 2.5, PORCELAIN, sides=8)
            d.tube("y", (x, z), _RAIL[1] + 5, _RAIL[1] + 8, 1.5, PORCELAIN, sides=8)
            d.tube("y", (x, z), _RAIL[1] + 8, _RAIL[1] + 9, 2.0, PORCELAIN, sides=8)
            d.tube("y", (x, z), _RAIL[1] + 9, _BELL_TOP, 0.75, BRASS, sides=4)

    # the meter: a brass case three texels proud, its dial, the ticks that glow
    d.tube("x", (_METER_Y, mz), 0, 3, _METER_R, BRASS, sides=16)
    d.plate("e", (3, _METER_Y, mz), 16, 16, _dial_picture(letter).sprite(PREFIX + "dial_" + letter), lift=0.25)
    d.plate("e", (3.25, _METER_Y, mz), 16, 16, _ticks_picture().sprite(PREFIX + "ticks"), lift=0.25, emit=15)

    if name == "main":
        _knife(d, mz, _SWITCH_Y[0] - 2, _SWITCH_Y[1], 8, (-5, 5))                       # the main switch
        wheel = _wheel_picture().sprite(PREFIX + "wheel")
        lens = _lens_picture().sprite(PREFIX + "lens")
        for zc in (mz - 16, mz + 16):
            d.tube("x", (32, zc), 0, 3, 1.5, BRASS, sides=8)                            # a rheostat's handwheel
            d.ring("x", (3.5, 32, zc), 5.0, 1.0, 1.0, IRON_L, sides=16)
            d.plate("e", (3.5, 32, zc), 11, 11, wheel, lift=0.5)
            d.tube("x", (_METER_Y + 2, zc), 0, 2, 2.5, BRASS, sides=8)                  # a pilot lamp
            d.plate("e", (2, _METER_Y + 2, zc), 3, 3, lens, lift=0.25, emit=15)
    else:
        for zc, opened in _SWITCHES[name]:
            _knife(d, zc, _SWITCH_Y[0], _SWITCH_Y[1], 4, (-2, 2), opened)
    return d


def _needle():
    """A meter's pointer, standing upright on its pivot."""
    d = K.Draw(PREFIX + "needle", scale=1.0, step=K.TEXEL)
    d.box((0, -1.5, -0.5), (0.5, 5.5, 0.5), K.flat("iron", 0), seed=0)
    d.box((0, -1, -1), (0.75, 1, 1), K.flat("brass", 1), seed=0, faces={"e": K.flat("brass", 3)})
    return d


@functools.lru_cache(maxsize=None)
def _drawn():
    built = [_panel(name) for name in _SLABS] + [_needle()]
    return {d.m.name[len(PREFIX):]: d for d in built}


def models():
    return {d.m.name: d.m for d in _drawn().values()}


def build(canvas, origin=(0, 0, 0)):
    """Lay the base course, place the board and its light; returns the number of display entities."""
    drawn = _drawn()
    K.light(canvas, LIGHTS, origin, "machines/board:lamp")
    ox, oy, oz = (int(v) for v in origin)
    for i, name in enumerate(BASE):
        canvas.set(ox + X, oy + int(FLOOR), oz + Z[0] + i, st(B.PANELS[name], facing=FACING))
    n = 0
    for name in _SLABS:
        x, y, z = _STAND[name]
        n += K.place(canvas, drawn["panel_" + name], (FACE_X + x / 16.0, FLOOR + y / 16.0, Z[0] + z / 16.0), origin)
        mz, _, rest, tremble, period = _METERS[name]
        n += K.place(canvas, drawn["needle"], (FACE_X + 3.75 / 16.0, FLOOR + _METER_Y / 16.0, Z[0] + mz / 16.0), origin,
                     turns=(("x", rest),))
        MK.swing(canvas, "x", tremble, period, name="needle_" + name)
    return n
