"""Work package interiors/domeroom: the great dome room (plan ART-PLAN 8, view V8).

The star piece is the great refractor on its pier, pointing through the slit at the comet. The room
dresses the shell that stands on the canvas and never builds it: the drum and the dome's skin are
main/dome, the floor, the opening round the pier and its railing are main/shell, the telescope is
machines/scope, the track, rollers, chains and hand gear are machines/domegear. Where the skin is
and where it is open is read off the canvas, so the room follows the dome when its slit is changed.

The plan (director, g2 #31564): the axis belongs to the telescope. East of the pier, on the axis, is
the observing floor, where one ends up standing behind the eyepiece and looks along the tube; the
ring stair comes up on the north side of the pier; the south side is kept for those who look at the
comet past the tube (its tail leans north, so only from the south is all of it seen through the
slit: sky/comet), and the record desk stands there.

The room is dark and quiet so that the sky in the slit is the brightest thing in it: no stone and no
copper shows indoors. Wood lines the drum and the vault; iron is what carries and what turns.

What the room adds, from the floor up:

    17       the floor's finish: a dark border along the wall; the observing floor east of the pier,
             level with the boards: dark boards from the iron curb of the pier's opening on, an
             iron plate at each corner
    18..22   the drum's lining: boards in front of the stone all the way round, open at the two doors
             and in the column of the hand gear's shaft; in the reveal of every window the room
             sees a shutter of dark panelling stands shut
    23       the lining's cornice: a moulding of the same boards
    24       the ledge on the inner leaf and the row over the cornice, left empty: the track, the
             rollers and the toothed ring (machines/domegear)
    25..26   the dome's ring girder over that ledge: what turns, and what the skeleton stands on
             (under the open slit one row, level with its sill)
    27..     the vault: boards on the inside of every plate, an iron curb round the slit; under the
             boards the dome's skeleton as display models (interiors/_domeframe): the ring girder
             in front of its blocks, the two lattice arch girders beside the slit, a lattice rib
             on every seam, three rings of purlins; and on the skeleton's back the lining that is
             seen, as display models too: boards from seam to seam, a flat panel to every gore

and what stands in the room: the switchboard of the dome's drive on the east axis, the sidereal
clock on the south axis and the record desk under it, three cabinets on the north axis and a chart
table beside them, plate boxes by the south wall; round the pier the track of the observing ladder,
and the ladder parked on it south-west of the pier (interiors/_domechair). The ladder rolls all the
way round, so nothing else stands in the band it passes over.

Light (plan 3.2): the sky in the slit is the cold base and the brightest thing. The room has one
lamp, the telescope's red one by the eyepiece (director, g2 #33812); the desk has none. What else
is warm in it is the glow of its instruments, third rank and all of it below the cornice: the pilot
lamps of the switchboard in the east, the dial of the sidereal clock in the south, and in the north,
facing whoever comes up the stair, the opal face of the mean-time dial on the cabinets. Round the
room one walks from one of them to the next (sky/lights, c331 #73179).

The shared pieces come from props/furniture, props/paper and props/instruments (the clock); while
those are not in the tree they stand in as blocks. The switchboard (interiors/_domeboard), the
observing ladder and its track are the room's own models.

build() is what the master scene calls; it places nothing unless MOVED_IN is set. The room is
judged in its box test scene (build/scenes/obs_int_domeroom), which calls dress().
"""
import functools
import importlib
import math

from artkit import models as M
from artkit.canvas import Canvas
from artkit.pixelart import Sprite

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..main import _order as O
from ..props import _kit as K
from . import _domechair
from . import _domeframe as F

ORDER = 80                  # after the shell and the dome (60)
MOVED_IN = True             # the room is in the master scene (COMMON 0.10: switched on with the delivery)
PREFIX = "int_domeroom_"

CX, CZ = S.DOME_CENTRE
FLOOR_Y = S.ROOF_FLOOR                          # 17: the row of the floor's boards
FEET = S.ROOF_STAND                             # 18: the row one stands in
WALL_TOP = S.DRUM[1]                            # 23: the last row of the drum's stone
LEDGE_Y = S.DOME_SPRING                         # 24: the row on top of the inner leaf (machines/domegear)
BASE_RING = (LEDGE_Y + 1, LEDGE_Y + 2)          # 25..26: the dome's ring girder
SKIN_FROM = LEDGE_Y + 2                         # 26: a block from here up is the dome's skin; what stands
#                                                 lower in a column of the slit is its sill
RIBS = 20                                       # the seams of the dome outside
RIB_DEG = 360.0 / RIBS
# what is kept clear for machines/domegear. The hand gear that turns the dome (g2 #31714, #34943):
# the column of the wall its upright shaft stands in, from the floor to the ledge with its bearing in
# the row of the ring beam, and the floor in front of its hand wheel
GEAR_SHAFT = ((-1, -9),)
GEAR_STAND = ((0, -9), (1, -9))                 # the hand wheel and the one who turns it: nothing here
# the gear of the slit's curtain (machines/domegear, c352 #66647; laid out for main/dome's version b
# with the slit open), as (x, (first row, last row), (z, ...)). In the room's columns the base
# ring's row is his
GEAR_FOR = ("b", "open")
GEAR_SLIT = (
    (-6, (25, 26), (-3, -2, -1, 0, 1, 2, 3)),   # the winch across the slit's foot
    (-7, (25, 25), (0,)),                       # its bracket, out of the east face of the base ring
    (-6, (19, 24), (0,)),                       # the hand chain
    (-8, (26, 27), (-2, -1, 0, 1, 2)),          # the roll the curtain winds on
    (-7, (26, 27), (-2, -1, 0, 1, 2)),
    (-8, (25, 27), (-3, 3)),                    # the ends of its shaft and their weights
    (-7, (27, 30), (-2, 2)),                    # the two chains that draw the curtain
    (-6, (26, 27), (-2, 2)),
    (-6, (25, 27), (-3, 3)),                    # the two counterweight rails: hung under the girders beside
    (-5, (25, 29), (-3, 3)),                    # the slit, along the line of their undersides
    (-4, (28, 31), (-3, 3)),
    (-3, (29, 32), (-3, 3)),
)

IRON = B.IRON_RIVETED
SHUTTER = B.WAINSCOT                            # a framed panel of dark wood, three texels thick
WOOD = B.DARK_WOOD                              # the floor's border, what stands in for furniture
DEAL = B.FLOOR_WOOD                             # the boards of the vault and of the drum's lining: dark oak
#                                                 is dead black where no lamp is (0.02 from below, the sky's
#                                                 own light on it); these read as dark boards (0.04 to 0.08)
# what the dome's skin is made of: the copper families, and riveted iron along the slit (the stiles
# of its leaves or the rails of its shutter: main/dome). Only these count when the room looks for the
# skin, and it looks from above: the machines are on the canvas before the room (the telescope's tube
# in the slit, chains and counterweights under the skin) and are not the dome
SKIN = frozenset([B.VERDIGRIS, B.VERDIGRIS_CAST, *B.VERDIGRIS_CUT.all(), *B.VERDIGRIS_STREAK.all(),
                  B.OLD_COPPER, *B.OLD_COPPER_CUT.all(), *B.IRON_RIVETED.all()])
AROUND = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))

# --- what stands in the room ----------------------------------------------------------------------
# the observing floor (director, g2 #31564): east of the pier from its curb on, under the eyepiece of
# either version of the telescope. Nothing of the room stands on it
OBSERVING = (S.PIER_ENVELOPE[2] + 1, CZ - 1, S.PIER_ENVELOPE[2] + 5, CZ + 3)       # x 8..12, z -1..3
# the eyepiece end of the telescope while machines/scope is not in the tree: its version a (the
# director's pick, 11-16), whose tube rides south of the dome's axis, in the plane z = 1.4
EYEPIECE = (10.103, 19.703, 1.4)
# bottom course first, from north to south; the instrument panels of the dome's drive (blocks.PANELS)
BOARD = (("knife_switch", "bus_switch", "knife_switch"),
         ("dial", "pilot_lamps", "gauges"))
# the shared furniture (props/furniture): (kind, the middle of its foot (x, z), the way it looks: a
# desk or a cabinet its front, a seat the way the one who sits on it looks)
FURNITURE = (
    # the record desk in the bay of the south axis, its back against the lining, and the recorder's
    # chair before it: who writes down the time has the sidereal clock over the desk, in front of him
    ("writing_desk", (4.5, 10.5625), "north"),
    ("swivel_chair", (4.5, 9.5), "south"),
    ("instrument_cabinet", (3.5, -9.5), "south"),   # on the north axis: three abreast against the
    ("card_cabinet", (4.5, -9.5), "south"),         # lining, below the window
    ("instrument_cabinet", (5.5, -9.5), "south"),
    ("stool", (13.5, 1.5), "east"),                 # at the switchboard
    ("coat_stand", (10.5, -6.5), "south"),          # inside the north door
    ("drafting_table", (7.5, -8.5), "south"),       # the night's chart, under the window east of the cabinets
)
# the boxes the plates are carried in, by the south wall: (x, z, how many boxes it stands on, yaw).
# props/furniture's plate_box once it has one, else its packing case, which does not stack
PLATE_BOXES = ((7.5, 9.5, 0, 0.0), (8.5, 9.4, 0, 96.0), (7.56, 9.47, 1, 9.0))
DESK = FURNITURE[0]
LOGBOOK = (4.5, 10.4375)                        # (x, z) on the desk: the night's record (props/paper)
CLOCK_LIFT = 1.25                               # the regulator clock (props/instruments) hangs on the lining
#                                                 of the south axis, its foot this far above the floor: a
#                                                 hand's breadth over the gallery at the back of the desk
# the mean-time dial (the room's own model) stands on the cabinets of the north axis, before whoever
# comes out of the stair: on the western one, so that V8 has all of it inside its right edge as it
# has all of the sidereal clock inside its left one (review cr4, #74681: nothing that glows is cut
# by the frame). Every clock on the hill is stopped at one time (director, g2 #34140)
TIME_DIAL = FURNITURE[2]
CLOCK = getattr(S, "CLOCK", (7, 55))
DIAL_GLOW = 6                                   # the light its opal face is shown in, whatever the room's
DIAL_FACE = (                                   # c the lit glass, k the quarters, m the other hours
    "..mckcm..",
    ".ccccccc.",
    "mcccccccm",
    "ccccccccc",
    "kccccccck",
    "ccccccccc",
    "mcccccccm",
    ".ccccccc.",
    "..mckcm..",
)

# --- light: (level, rank); sky/lights decides where the invisible blocks really go -----------------
# Each is the glow of an instrument that is seen to glow, which is not a lamp (sky/lights, c331
# #73179, who set the levels): the room's one lamp stays the telescope's red one. All three sit
# under row 21, where they reach the floor one walks on and not the vault
PILOT_LAMPS = (6, 3)
CLOCK_DIAL = (5, 3)
TIME_DIAL_GLOW = (5, 3)
# the sky's light the skeleton's iron is shown in: (far from the slit, beside it). No lamp is added:
# the pieces are told how much of the night falls on them (_night). The floor keeps the iron out of
# dead black in the half of the room the slit does not light; the cap keeps it under the sky
IRON_LIGHT = (10, 13)
# and the same for the boards of the vault's lining. Every board is shown in the least light a model
# can have (interiors/_domeframe.boards), so with these the lining stays a step under the iron in
# front of it everywhere, and both under the sky in the slit. BOARD_WARMTH is the lamp light the
# boards are shown in besides: no lamp is there, it stands for what the room throws back up at its
# ceiling. It keeps the wood brown and out of dead black in the deepest hour of the night, when the
# sky's share is next to nothing; the iron has none of it and stays the colour of the night
BOARD_LIGHT = (11, 14)
BOARD_WARMTH = 3

OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}


# --- where things are ---------------------------------------------------------------------------
def room():
    """The columns of the room: inside both leaves of the drum (main/shell's floor and the pier's
    opening)."""
    return O.shrink(O.shrink(O.disc(CX, CZ, S.DOME_R)))


def leaf():
    """The columns of the drum's inner leaf: its top is the ledge the dome's ring girder runs over."""
    return O.shrink(O.disc(CX, CZ, S.DOME_R)) - room()


def lined():
    """The columns of the room that touch the stone by a side: where the wall's lining stands."""
    inner, stone = room(), leaf()
    return {col for col in inner if any(O.step(col, d) in stone for d in O.SIDES)}


def envelope():
    """The opening round the pier and the curb its railing stands on (main/shell)."""
    x0, z0, x1, z1 = S.PIER_ENVELOPE
    return O.box(x0 - 1, z0 - 1, x1 + 1, z1 + 1)


def _other(line, name):
    """Another package's module when it is in the tree, else None: the room is built and judged
    before its neighbours are merged."""
    try:
        return importlib.import_module(f"..{line}.{name}", __package__)
    except ModuleNotFoundError as e:
        if e.name != f"{__package__.rsplit('.', 1)[0]}.{line}.{name}":
            raise                               # the module is there and fails to import something
        return None


def stair_exit():
    """The cell one steps onto from the ring stair, on the curb of the pier's opening: main/shell's
    EXIT once that module is in the tree, else None. It is on the north side, (4, -4); that cell and
    the three above it are kept free."""
    shell = _other("main", "shell")
    got = getattr(shell, "EXIT", None)
    return tuple(got) if got else None


def niches():
    """The four flats of the round wall on the axes, each three columns wide and all of them lined:
    {"east": [cells from low to high], ...}."""
    cells = room()
    xs, zs = [c[0] for c in cells], [c[1] for c in cells]
    ends = {"east": (0, max(xs)), "west": (0, min(xs)), "south": (1, max(zs)), "north": (1, min(zs))}
    return {side: sorted(c for c in cells if c[i] == at) for side, (i, at) in ends.items()}


def doorways():
    """The room's end of the two doors to the roof terraces: for each, the first column of the room
    behind the skeleton's door column, going straight in."""
    inside, out = room(), []
    for cell in S.DOME_ROOM_DOORS["cells"]:
        inward = (0, -1 if cell[1] > CZ else 1)
        while cell not in inside:
            cell = O.step(cell, inward)
        out.append(cell)
    return out


def rib_angles():
    """Degrees round the dome's centre (0 = east, 90 = south) of the dome's seams: a gore, not a
    seam, lies on each axis."""
    return [(k + 0.5) * RIB_DEG for k in range(RIBS)]


def eyepiece():
    """Where the middle of the telescope's eyepiece end is (x, y, z in blocks): what machines/scope
    says once its module is in the tree, else EYEPIECE."""
    scope = _other("machines", "scope")
    got = getattr(scope, "eyepiece", None)
    return tuple(got()) if got is not None else EYEPIECE


def observing_floor():
    """The columns of the observing floor."""
    return O.box(*OBSERVING) & (room() - O.box(*S.PIER_ENVELOPE))


def gear_cells():
    """{(x, y, z)} the cells kept clear for the gear of the slit's leaves (GEAR_SLIT)."""
    return {(x, y, z) for x, (y0, y1), zs in GEAR_SLIT for z in zs for y in range(y0, y1 + 1)}


def _glass(name):
    return name is not None and "glass" in name


class Shell:
    """The shell as it stands on the canvas, read before the room adds anything."""

    def __init__(self, c, origin=(0, 0, 0)):
        ox, oy, oz = origin

        def name(x, y, z):
            return c.name(ox + x, oy + y, oz + z)

        def skin(x, y, z):
            got = name(x, y, z)
            return got is not None and got.rpartition(":")[2] in SKIN

        self.name, self.skin = name, skin
        self.inside, self.ledge = room(), leaf()
        self.wall = lined()
        self.reach = self.inside | self.ledge
        self.soffit = {}                # column -> the row under the dome's skin; None where the sky is open
        for x, z in self.reach:
            self.soffit[(x, z)] = None
            for y in range(S.DOME_APEX + 3, SKIN_FROM - 1, -1):     # from above: the skin's outside first,
                if skin(x, y, z):
                    while y > SKIN_FROM and skin(x, y - 1, z):      # then down through it to its underside
                        y -= 1
                    self.soffit[(x, z)] = y - 1
                    break
        self.roofed = any(y is not None for y in self.soffit.values())
        self.gap = {col for col, y in self.soffit.items() if y is None} if self.roofed else set()
        self.frame = (O.ring(self.gap) & self.reach) - self.gap
        # the slit runs along x: the columns beside it, and those across its head
        self.jambs = {col for col in self.frame if any(O.step(col, d) in self.gap for d in (O.NORTH, O.SOUTH))}
        self.head = self.frame - self.jambs
        lines = {z for _x, z in self.jambs}
        self.arches = {col for col in self.reach - self.gap if col[1] in lines}
        self.vault = {col: self._lining(col) for col in self.reach - self.gap}

    def _lining(self, col):
        """The rows of a roofed column that the vault fills: every free cell that touches the skin
        from inside; over the inner leaf every free cell between the ring girder and the skin."""
        top = self.soffit[col]
        if top is None:
            return []
        x, z = col
        if col in self.ledge:
            rows = range(BASE_RING[1] + 1, top + 1)
        else:
            rows = [y for y in range(SKIN_FROM, top + 1)
                    if any(self.skin(x + dx, y + dy, z + dz) for dx, dy, dz in AROUND)]
        return [y for y in rows if self.name(x, y, z) is None]

    def window(self, col, y):
        """The side on which the cell looks at a window of the drum (one of O.SIDES), else None."""
        for d in O.SIDES:
            x, z = O.step(col, d)
            if (x, z) in self.ledge and _glass(self.name(x, y, z)):
                return d
        return None

    def glazed(self, col, y):
        """Does the cell look at a window of the drum?"""
        return self.window(col, y) is not None


# --- the room's own models --------------------------------------------------------------------------
def _time_dial():
    """The mean-time dial: a slave of the mother clock, a drum of brass in a cradle on a wooden
    foot. Its face is opal glass with a bulb no bigger than a pea behind it, so the hour is read
    across the dark room without a lamp; the marks and the hands stand dark against it. Anchor:
    the middle of the foot's underside; the dial looks +z."""
    m = M.Model(PREFIX + "time_dial")
    cy, face = 8.0, 1.5                             # the middle of the dial; the plane of its glass
    m.box((-5.5, 0.0, -2.5), (5.5, 1.5, 2.5), P.mat("dark_wood", base=1), grain="x")    # the foot
    m.box((-3.0, 1.5, -2.0), (3.0, cy - 4.5, 2.0), K.BRASS_D)                           # the cradle
    m.tube("z", (0.0, cy), -2.0, face, 5.5, K.BRASS, sides=16)                          # the drum
    marks = dict(c=P.RAMPS["opal"][2], k=P.RAMPS["iron"][0], m=P.RAMPS["iron"][2])
    m.box((-4.5, cy - 4.5, face), (4.5, cy + 4.5, face + 0.25), K.flat("opal", 2), skip="nudew",
          faces={"s": Sprite(PREFIX + "time_dial_face", list(DIAL_FACE), marks)}, emit=DIAL_GLOW, shade=False)
    top = face + 0.25
    hour, minute = CLOCK
    for lean, length in (((hour % 12 + minute / 60.0) * 30.0, 2.5), (minute * 6.0, 3.75)):
        m.box((-0.5, cy, top), (0.5, cy + length, top + 0.2), K.flat("iron", 0), grain="y",
              rot=("z", -lean, (0.0, cy, top + 0.1)))                                   # a hand: one clean strip
        top += 0.2
    m.box((-0.5, cy - 0.5, top), (0.5, cy + 0.5, top + 0.15), K.flat("brass", 4))       # the boss on the pivot
    m.ring("z", (0.0, cy, face + 0.375), 5.0, 1.0, 0.75, K.BRASS, sides=16)             # the bezel
    return m


@functools.lru_cache(maxsize=None)
def _models():
    return {m.name: m for m in (_time_dial(),)}


def models():
    out = dict(_models())
    skeleton = frame()
    if skeleton is not None:
        out.update(skeleton.models)
    out.update(_domechair.models())
    board = _other("interiors", "_domeboard")
    if board is not None:
        out.update(board.models())
    return out


# --- the dome's skeleton ------------------------------------------------------------------------------
def ceilings(shell):
    """{column of the room: the height of the underside over it once the vault is boarded}, None
    under the open slit."""
    out = {}
    for col in shell.inside:
        top, rows = shell.soffit[col], shell.vault.get(col)
        out[col] = None if top is None else min(rows) if rows else top + 1
    return out


def _faces(shell):
    """How far from the axis the ring girder's web has its front, and how far along their planes
    the arch girders come up against their piers. The web is round and the inner leaf is not: it
    stands against the block of the leaf that comes nearest to the axis and clear of all others."""
    ax, az = S.DOME_AXIS

    def out_to_leaf(dx, z0):
        d = 0.0
        while (int(math.floor(ax + d * dx)), int(math.floor(az + z0))) not in shell.ledge:
            d += 0.03125
            if d > 2.0 * S.DOME_R:
                raise ValueError("no inner leaf on the way out from the dome's axis")
        return d

    nearest = min(math.hypot(max(x - ax, ax - (x + 1), 0.0), max(z - az, az - (z + 1), 0.0)) for x, z in shell.ledge)
    arches = min(out_to_leaf(dx, side) for dx in (1.0, -1.0) for side in _sides(shell))
    return nearest - F.WEB, arches


def _sides(shell):
    """Where the two arch planes stand, as z counted from the dome's axis: through the middle of
    the columns beside the slit."""
    return sorted({z + 0.5 - S.DOME_AXIS[1] for _x, z in shell.jambs})


def _sill(shell):
    """Where the ring girder stops for the slit's foot: (the side of the axis the slit comes down
    to the inner leaf on, -1 west or 1 east; how far the outer faces of the two piers beside it
    stand from the axis). None where the slit ends above the leaf."""
    foot = [x + 0.5 - S.DOME_AXIS[0] for x, _z in shell.gap & shell.ledge]
    if not foot:
        return None
    return math.copysign(1.0, sum(foot)), max(abs(side) for side in _sides(shell)) + 0.5


@functools.lru_cache(maxsize=1)
def _default_shell():
    """The dome as the tree builds it when nobody asks for anything else, on a canvas of its own:
    what the skeleton's models are drawn for when they are asked for before a room is dressed."""
    c = Canvas()
    dome = _other("main", "dome")
    if dome is None:
        from ..main import _dome as dome
    dome.build(c)
    return Shell(c)


_FRAMES = {}


def frame(shell=None):
    """The dome's skeleton (interiors/_domeframe.Frame) for the shell on the canvas, or without one
    for the dome that was dressed last, else for the dome as the tree builds it. None where the
    dome has no slit to build the two arch girders beside."""
    if shell is None:
        if "last" in _FRAMES:
            return _FRAMES["last"]
        shell = _default_shell()
    if not shell.roofed or len(_sides(shell)) != 2:
        return None
    ceiling = ceilings(shell)
    key = hash(frozenset(ceiling.items()))
    if key not in _FRAMES:
        _FRAMES[key] = F.Frame(PREFIX, ceiling, S.DOME_AXIS, _sides(shell), shell.arches & shell.inside,
                               _faces(shell), (BASE_RING[0], BASE_RING[1] + 1), rib_angles(), _sill(shell))
    _FRAMES["last"] = _FRAMES[key]
    return _FRAMES[key]


# --- the dress ------------------------------------------------------------------------------------
def dress(c, origin=(0, 0, 0)):
    """Dress the dome room inside the shell that stands on the canvas. Returns the number of display
    entities placed."""
    ox, oy, oz = origin
    shell = Shell(c, origin)

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    _vault(put, shell)
    _wall(c, origin, put, shell)
    _floor(put, shell)
    n = _fittings(c, origin, put) + _skeleton(c, origin, shell) + _furniture(c, origin, put)
    _offer(c, origin, lights())
    return n


def _vault(put, shell):
    """The blocks of the dome's ring girder over the inner leaf, and the inside of the skin: boards,
    and an iron curb round the slit (its reveal: the one place where the lining's edge is seen)."""
    if not shell.roofed:
        return
    for col in shell.ledge:
        for y in BASE_RING if shell.soffit[col] is not None else BASE_RING[:1]:
            if shell.name(col[0], y, col[1]) is None:
                put(col[0], y, col[1], IRON.block)
    iron = shell.frame
    for col, rows in shell.vault.items():
        for y in rows:
            put(col[0], y, col[1], IRON.block if col in iron else DEAL.block)


def _night(shell, pos, within=IRON_LIGHT):
    """The sky's light a piece of the skeleton is shown in. A display entity takes the light of the
    one cell its origin is in, and a rib is ten blocks long: its origin may sit in the full light
    under the slit or in the dark behind a girder. So every piece is given its light: what comes
    down through the slit, one level less for every column away from it, `within` (least, most)."""
    x, z = int(math.floor(pos[0])), int(math.floor(pos[2]))
    away = min((abs(x - gx) + abs(z - gz) for gx, gz in shell.gap), default=15)
    return max(within[0], min(within[1], 15 - away))


def _skeleton(c, origin, shell):
    """The iron skeleton under the vault and the boards on its back; returns the number of display
    entities."""
    skeleton = frame(shell)
    if skeleton is None:
        return 0
    n = sum(K.put(c, skeleton.models[name], pos, yaw=yaw, scale=F.SCALE, origin=origin,
                  brightness=(_night(shell, pos), 0))
            for name, pos, yaw in skeleton.placed)
    return n + sum(K.put(c, skeleton.models[name], pos, yaw=yaw, scale=F.SCALE, origin=origin, turns=F.LEAN,
                         brightness=(_night(shell, pos, BOARD_LIGHT), BOARD_WARMTH))
                   for name, pos, yaw in skeleton.lined)


def _wall(c, origin, put, shell):
    """The drum's lining, its cornice and the shutters of the windows.

    The cornice is the lining's own: a moulding of the same boards that widens upwards. Where a
    column of the lining has stone on two sides the moulding's hollow would open onto the second,
    so that column is a whole block. A window the room sees keeps its reveal, the depth of the
    lining, and in it a shutter of dark panelling stands shut, flush with the boards: the drum's
    windows are dark at night from both sides."""
    lay = O.Laying(c, None, origin, None)
    cols = shell.wall - set(GEAR_SHAFT)
    lay.mould(shell.ledge, WALL_TOP, DEAL.stairs, "top", only=cols)
    for col in cols:
        if sum(O.step(col, d) in shell.ledge for d in O.SIDES) > 1:
            put(col[0], WALL_TOP, col[1], DEAL.block)
    doors = set(doorways())
    y0, y1 = S.DOME_ROOM_DOORS["y"]
    for col in cols:
        for y in range(FEET, WALL_TOP):
            if col in doors and y0 <= y <= y1:
                continue
            out = shell.window(col, y)
            if out is None:
                put(col[0], y, col[1], DEAL.block)
            else:
                # an open trapdoor stands on the side of its cell its facing points away from
                put(col[0], y, col[1], f"{SHUTTER}[facing={O.NAME[out]},half=bottom,open=true]")


def _floor(put, shell):
    """The floor's finish, in the row of the boards main/shell lays. The iron curb round the pier's
    opening is main/shell's and stays whole: the observing floor's own boards start east of it."""
    open_floor = shell.inside - shell.wall
    for x, z in shell.wall | (open_floor - O.shrink(open_floor)):
        put(x, FLOOR_Y, z, WOOD.block)
    cells = observing_floor() - envelope()
    for x, z in cells:
        open_sides = [d for d in O.SIDES if O.step((x, z), d) not in cells]
        corner = len(open_sides) == 2 and open_sides[0][0] != open_sides[1][0] and open_sides[0][1] != open_sides[1][1]
        put(x, FLOOR_Y, z, IRON.block if corner else WOOD.block)


def _fittings(c, origin, put):
    """The switchboard of the dome's drive on the east axis, below the windows: the room's own model
    (interiors/_domeboard) on the lining once that is in the tree, else instrument panels let into
    the boards. Returns the number of display entities."""
    board = _other("interiors", "_domeboard")
    if board is not None:
        return board.place(c, origin)
    for i, (x, z) in enumerate(niches()["east"]):
        for row, names in enumerate(BOARD):
            put(x, FEET + row, z, B.PANELS[names[i]] + "[facing=west]")
    return 0


def _clock(c, origin, put):
    """The sidereal clock on the south axis: the regulator of props/instruments on the lining. While
    that is not in the tree, a dial let into the boards. Returns the number of display entities."""
    cells = niches()["south"]
    x, z = cells[len(cells) // 2]
    instruments = _other("props", "instruments")
    if instruments is not None:
        return instruments.place(c, "regulator_clock", (x + 0.5, FEET + CLOCK_LIFT, float(z)), facing="north",
                                 origin=origin)
    put(x, FEET + 1, z, B.PANELS["dial"] + "[facing=north]")
    return 0


def _furniture(c, origin, put):
    """What stands loose in the room; returns the number of display entities."""
    furniture, paper = _other("props", "furniture"), _other("props", "paper")
    n = _clock(c, origin, put)
    for kind, (x, z), facing in FURNITURE:
        if furniture is not None:
            n += furniture.place(c, kind, (x, FEET, z), facing=facing, origin=origin)
        else:
            _standin(put, kind, (int(math.floor(x)), int(math.floor(z))), facing)
    boxed = furniture is not None and "plate_box" in furniture.SPEC
    for x, z, tier, yaw in PLATE_BOXES:
        if boxed:
            lift = tier * (furniture.TOP["plate_box"] + getattr(furniture, "STRAP", 0.0))
            n += furniture.place(c, "plate_box", (x, FEET + lift, z), yaw=yaw, origin=origin)
        elif tier == 0 and furniture is not None:
            n += furniture.place(c, "crate", (x, FEET, z), yaw=yaw, origin=origin)
        elif tier == 0:
            _standin(put, "crate", (int(math.floor(x)), int(math.floor(z))), "south")
    if furniture is not None and paper is not None:
        top = FEET + furniture.TOP[DESK[0]]
        n += paper.place(c, "logbook", (LOGBOOK[0], top, LOGBOOK[1]), facing=DESK[2], origin=origin)
    n += K.put(c, _models()[PREFIX + "time_dial"], _time_dial_at(), facing=TIME_DIAL[2], origin=origin)
    # the track of the observing ladder round the pier, and the ladder parked on it
    return n + _domechair.place(c, origin)


def _time_dial_at():
    """(x, y, z) of the middle of the mean-time dial's foot: on top of the cabinet it stands on (the
    cabinet's stand-in is two blocks)."""
    kind, (x, z), _ = TIME_DIAL
    furniture = _other("props", "furniture")
    return x, FEET + (furniture.TOP[kind] if furniture is not None else 2.0), z


def _standin(put, kind, cell, facing):
    """A piece of the shared furniture as blocks, while props/furniture is not in the tree."""
    x, z = cell
    if kind == "writing_desk":
        along = O.EAST if facing in ("north", "south") else O.SOUTH
        for k in (-1, 0, 1):
            dx, dz = O.step(cell, along, k)
            put(dx, FEET, dz, f"{WOOD.slab}[type=top]")
    elif kind == "swivel_chair":
        put(x, FEET, z, f"{WOOD.stairs}[facing={OPPOSITE[facing]},half=bottom]")
    elif kind == "stool":
        put(x, FEET, z, f"{WOOD.slab}[type=bottom]")
    elif kind.endswith("_cabinet"):
        for y in (FEET, FEET + 1):
            put(x, y, z, B.PANELS["drawers"] + f"[facing={facing}]")
    elif kind == "coat_stand":
        for y in (FEET, FEET + 1):
            put(x, y, z, f"{B.IRON_ROD}[facing=up]")
    else:
        put(x, FEET, z, WOOD.block)


def lights():
    """[((x, y, z), level, rank, name)] the light sources the room asks for, in scene cells without
    the origin: each sits right in front of something that is seen to glow."""
    n = niches()
    bx, bz = n["east"][len(n["east"]) // 2]
    kx, kz = n["south"][len(n["south"]) // 2]
    instruments = _other("props", "instruments")
    dial = 1 if instruments is None else int(math.floor(CLOCK_LIFT + getattr(instruments, "CLOCK_DIAL_Y", 24.5) / 16.0))
    tx, ty, tz = _time_dial_at()
    return [((bx - 1, FEET + 1, bz), *PILOT_LAMPS, "pilot_lamps"),
            ((kx, FEET + dial, kz - 1), *CLOCK_DIAL, "clock_dial"),
            ((int(math.floor(tx)), int(math.floor(ty + 0.5)), int(math.floor(tz))), *TIME_DIAL_GLOW, "time_dial")]


def _offer(c, origin, wanted):
    """Hand the room's light sources to the light line: sky/_lightkit.suggest when it is in the tree,
    else the props kit's stand-in, which drops the blocks itself."""
    ox, oy, oz = origin
    suggest = getattr(_other("sky", "_lightkit"), "suggest", None)
    for (x, y, z), level, rank, name in wanted:
        cell, why = (ox + x, oy + y, oz + z), f"interiors/domeroom:{name}"
        if suggest is not None:
            suggest(c, cell, level, why, rank=rank)
        else:
            K.offer_lights(c, [(cell, level)], why)


def build(canvas, origin=(0, 0, 0)):
    if not MOVED_IN:
        return 0
    return dress(canvas, origin)
