"""Work package interiors/domeroom: the great dome room (plan ART-PLAN 8, view V8).

The star piece is the great refractor on its pier, pointing through the slit at the comet. The room
dresses the shell that stands on the canvas and never builds it: the drum and the dome's skin are
main/dome (c222), the floor, the opening round the pier and its railing are main/shell (c231), the
telescope is machines/refractor (c237), the track, rollers, chains and hand gear are
machines/domegear (c196). Where the skin is and where it is open is read off the canvas, so the
room follows the dome when its slit is changed.

The plan (director, g2 #31564): the axis belongs to the telescope. East of the pier, on the axis, is
the observing floor, where one ends up standing behind the eyepiece and looks along the tube; the
ring stair comes up on the north side of the pier (c231, g2 #32860); the south side is kept for
those who look at the comet past the tube (its tail leans north, so only from the south is all of it
seen through the slit: sky/comet, c230), and the record desk stands there.

What the room adds, from the floor up (rows; radii from the centre of column (4, 0)):

    17       the floor's finish: a dark border along the wall; the observing floor east of the pier,
             level with the boards: dark boards, an iron plate at each corner
    18..22   an iron wall post under every second rib and under the two beams of the slit; an iron
             console under the ring beam where the other ribs come down
    23       the ring beam: iron corbelled out from the wall's top, fixed to the stone (10.5..11.5)
    24       the ledge on the inner leaf and the row over the ring beam, left empty: the track, the
             rollers and the toothed ring (machines/domegear)
    25       the dome's base ring over that ledge (11.5..12.5): what turns, and what the ribs stand on
    26..     twenty iron ribs under the skin, one under each rib outside, up to a collar ring; a
             heavier beam along either side of the slit and a lighter one across its head

and what stands in the room: the switchboard of the dome's drive built into the east niche, the
sidereal clock in the south niche, three cabinets in the north niche, the record desk south-west of
the pier, the observing chair parked beyond it, boxes by the south wall.

Light (plan 3.2): the sky in the slit is the cold base and the brightest thing. The room's own warm
points are the pilot lamps of the switchboard and the clock's dial, both third rank. The one red
lamp of the room is the telescope's, by the eyepiece (director, g2 #33812): the desk has none.

The shared pieces come from props/furniture, props/paper and props/instruments (the clock); while
those are not in the tree they stand in as blocks. The observing chair is the room's own model.

build() is what the master scene calls; it places nothing until MOVED_IN is set (c231's shell and
c222's dome in the master scene, the room reviewed). Until then the room lives in its box test
scene (build/scenes/obs_int_domeroom), which calls dress().
"""
import functools
import importlib
import math

from artkit import models as M

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..main import _order as O
from ..props import _kit as K

ORDER = 80                  # after the shell and the dome (60)
MOVED_IN = False
PREFIX = "int_domeroom_"

CX, CZ = S.DOME_CENTRE
FLOOR_Y = S.ROOF_FLOOR                          # 17: the row of the floor's boards
FEET = S.ROOF_STAND                             # 18: the row one stands in
WALL_TOP = S.DRUM[1]                            # 23: the last row of the drum's stone
LEDGE_Y = S.DOME_SPRING                         # 24: the row on top of the inner leaf (machines/domegear)
BASE_RING_Y = LEDGE_Y + 1                       # 25
SKIN_FROM = LEDGE_Y + 2                         # 26: a block from here up is the dome's skin; what stands
#                                                 lower in a column of the slit is its sill
RIBS = 20                                       # one under each rib of the dome outside
RIB_DEG = 360.0 / RIBS
COLLAR = (5.0, 6.0)                             # the ring the ribs run into
POSTS = (27.0, 63.0, 99.0, 135.0)               # the ribs that come down on a wall post (every second
#                                                 one), and their mirror images in the axis; the others
#                                                 get a console
# columns of the wall kept clear from the floor to the ledge for machines/domegear (c196, g2 #31714,
# #34943): the upright shaft of the hand gear that turns the dome, and its bearing in the row of the
# ring beam. His shaft across the slit's foot runs in the row of the base ring, east of it:
# (-6, 25, -4..4); in the room's columns that row is his
GEAR_SHAFT = ((-1, -9),)
GEAR_STAND = ((0, -9), (1, -9))                 # the hand wheel and the one who turns it: nothing here
JAMB_DEPTH = 2                                  # rows the beams beside the slit hang below the skin
HEAD_DEPTH = 1                                  # the beam across its head: no lower, the comet's tail
#                                                 passes just under it (sky/comet)

IRON = B.IRON_RIVETED
WOOD = B.DARK_WOOD
# what the dome's skin is made of: the copper families, and riveted iron along the slit (the stiles
# of its door or the rails of its shutter: c222, g2 #34576). Only these count when the room looks
# for the skin, and it looks from above: the machines are on the canvas before the room (the
# telescope's tube in the slit, chains and counterweights under the skin) and are not the dome
SKIN = frozenset([B.VERDIGRIS, B.VERDIGRIS_CAST, *B.VERDIGRIS_CUT.all(), *B.VERDIGRIS_STREAK.all(),
                  B.OLD_COPPER, *B.OLD_COPPER_CUT.all(), *B.IRON_RIVETED.all()])

# --- what stands in the room ----------------------------------------------------------------------
# the observing floor (director, g2 #31564): east of the pier from its curb on, under the eyepiece of
# either version of the telescope. Nothing of the room stands on it
OBSERVING = (S.PIER_ENVELOPE[2] + 1, CZ - 1, S.PIER_ENVELOPE[2] + 5, CZ + 3)       # x 8..12, z -1..3
# the eyepiece end of the telescope while machines/refractor is not in the tree: its version on the
# axis (c237, g2 #33181)
EYEPIECE = (8.65, 19.79, 0.5)
# bottom course first, from north to south; the instrument panels of the dome's drive (blocks.PANELS)
BOARD = (("knife_switch", "bus_switch", "knife_switch"),
         ("dial", "pilot_lamps", "gauges"))
# the shared furniture (props/furniture): (kind, the middle of its foot (x, z), the way it looks: a
# desk or a cabinet its front, a seat the way the one who sits on it looks)
FURNITURE = (
    ("writing_desk", (2.5, 6.5), "south"),          # the record desk; the recorder sits south of it
    ("swivel_chair", (2.5, 7.5), "north"),          # and looks at the telescope
    ("instrument_cabinet", (3.5, -10.5), "south"),  # the north niche: three abreast, below its window
    ("card_cabinet", (4.5, -10.5), "south"),
    ("instrument_cabinet", (5.5, -10.5), "south"),
    ("stool", (13.5, 1.5), "east"),                 # at the switchboard
    ("coat_stand", (10.5, -7.5), "south"),          # inside the north door
    ("crate", (7.5, 10.5), "south"),                # plate boxes by the south wall
    ("crate", (8.5, 10.5), "west"),
)
DESK = FURNITURE[0]
LOGBOOK = (3.0, 6.5)                            # (x, z) on the desk: the night's record (props/paper)
CHAIR = (-2.5, 5.5)                             # the observing chair, parked south-west of the pier
CHAIR_YAW = 180.0                               # the side one climbs looks north, at the slit's foot
CLOCK_LIFT = 0.5                                # the regulator clock (props/instruments) hangs on the back
#                                                 wall of the south niche, its foot this far above the floor

# --- light: (level, rank); sky/lights decides where the invisible blocks really go -----------------
PILOT_LAMPS = (5, 3)
CLOCK_DIAL = (4, 3)

OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}


# --- where things are ---------------------------------------------------------------------------
def room():
    """The columns of the room: inside both leaves of the drum (c231's floor and the pier's opening)."""
    return O.shrink(O.shrink(O.disc(CX, CZ, S.DOME_R)))


def leaf():
    """The columns of the drum's inner leaf: its top is the ledge the dome's base ring runs over."""
    return O.shrink(O.disc(CX, CZ, S.DOME_R)) - room()


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
    EXIT once that module is in the tree, else None. It is on the north side, (4, -4) (c231, g2
    #32860); that cell and the three above it are kept free."""
    shell = _other("main", "shell")
    got = getattr(shell, "EXIT", None)
    return tuple(got) if got else None


def niches():
    """The four flat recesses of the round wall on the axes, each three columns wide:
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
    """Degrees round the dome's centre (0 = east, 90 = south): a gore, not a rib, lies on each axis."""
    return [(k + 0.5) * RIB_DEG for k in range(RIBS)]


def _polar(x, z):
    return math.hypot(x - CX, z - CZ), math.degrees(math.atan2(z - CZ, x - CX)) % 360.0


def _apart(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _on_meridian(x, z, angle):
    dx, dz = x - CX, z - CZ
    ux, uz = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    return dx * ux + dz * uz > 0 and abs(dx * uz - dz * ux) <= 0.5


def eyepiece():
    """Where the middle of the telescope's eyepiece end is (x, y, z in blocks): what
    machines/refractor says once its module is in the tree, else EYEPIECE."""
    scope = _other("machines", "scope")
    got = getattr(scope, "eyepiece", None)
    return tuple(got()) if got is not None else EYEPIECE


def observing_floor():
    """The columns of the observing floor."""
    return O.box(*OBSERVING) & (room() - O.box(*S.PIER_ENVELOPE))


class Shell:
    """The shell as it stands on the canvas, read before the room adds anything."""

    def __init__(self, c, origin=(0, 0, 0)):
        ox, oy, oz = origin

        def skin(x, y, z):
            name = c.name(ox + x, oy + y, oz + z)
            return name is not None and name.rpartition(":")[2] in SKIN

        self.inside, self.ledge = room(), leaf()
        self.edge = self.inside - O.shrink(self.inside)
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

    def touches_wall(self, col):
        return any(O.step(col, d) in self.ledge for d in O.SIDES)

    def at_angle(self, angle):
        """The column along the wall that a rib at `angle` comes down on."""
        cells = [e for e in self.edge if self.touches_wall(e)]
        return min(cells, key=lambda e: (round(_apart(_polar(*e)[1], angle), 3), abs(e[1] - CZ), abs(e[0] - CX), e))

    def in_slit(self, angle):
        """Does the rib at `angle` come down where the slit is?"""
        return any(_on_meridian(g[0], g[1], angle) for g in self.gap & self.edge)

    def posts(self):
        """The columns of the wall posts: under the POSTS ribs on either side of the axis, and where
        the beams beside the slit meet the wall."""
        out = {self.at_angle(a) for angle in POSTS for a in (angle, 360.0 - angle)}
        out |= {col for col in self.frame & self.edge if self.touches_wall(col)}
        return out - set(GEAR_SHAFT)

    def consoles(self):
        """The columns where a rib comes down on the ring beam alone."""
        out = {self.at_angle(a) for a in rib_angles() if not self.in_slit(a)}
        return out - self.posts() - set(GEAR_SHAFT)


# --- the room's own models --------------------------------------------------------------------------
def _chair():
    """The observing chair: a steep step ladder with a seat, for the nights when the telescope
    points low and its eyepiece rides high. Cast-iron side frames on four small wheels, wooden
    treads and seat with a cloth pad, a grab rail on top. Anchor: the middle of its foot on the
    floor; +z is the side one climbs."""
    m = M.Model(PREFIX + "chair")
    wood, cloth = P.mat("dark_wood"), P.mat("enamel_cloth")
    foot, top, seat = 1.0, 34.0, 21.0

    def front(y):                                   # z of the rail one climbs along, at height y
        return 9.0 - 12.0 * (y - foot) / (top - foot)

    for x in (-6.25, 6.25):
        m.beam((x, foot, 9.0), (x, top, -3.0), 1.5, 2.0, K.IRON)                         # the climbing rail
        m.beam((x, foot, -9.0), (x, top - 3.0, -3.5), 1.5, 1.5, K.IRON_D)                # the strut behind it
        m.box((x - 0.75, foot, -9.0), (x + 0.75, foot + 1.5, 9.0), K.IRON_D, grain="z")  # the sill
        for z in (-9.0, 9.0):
            m.tube("x", (foot, z), x - 0.6, x + 0.6, 1.0, K.IRON_D)                      # a wheel
    m.box((-5.5, foot, -9.5), (5.5, foot + 1.5, -8.5), K.IRON_D, grain="x")
    for y in (6.0, 11.0, 16.0):
        m.box((-5.5, y, front(y) - 1.5), (5.5, y + 1.0, front(y) + 2.5), wood, grain="x")    # the treads
    m.box((-5.5, seat, -5.5), (5.5, seat + 1.5, front(seat) + 1.0), wood, grain="x")         # the seat
    m.box((-4.5, seat + 1.5, -4.5), (4.5, seat + 2.25, front(seat)), cloth)                  # and its pad
    m.box((-7.0, top - 0.75, -3.75), (7.0, top + 0.75, -2.25), wood, grain="x")              # the grab rail
    for a, b in ((-7.5, -7.0), (7.0, 7.5)):
        m.box((a, top - 1.0, -4.0), (b, top + 1.0, -2.0), K.BRASS)
    return m


@functools.lru_cache(maxsize=None)
def _models():
    return {m.name: m for m in (_chair(),)}


def models():
    return dict(_models())


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
    _fittings(put)
    n = _furniture(c, origin, put)
    _offer(c, origin, lights())
    return n


def _vault(put, shell):
    """The dome's base ring, the beams round the slit, the ribs, the collar."""
    soffit, gap, frame = shell.soffit, shell.gap, shell.frame
    if not shell.roofed:
        return
    for x, z in shell.ledge:
        put(x, BASE_RING_Y, z, IRON.block)

    def foot(col):
        return BASE_RING_Y + 1 if col in shell.ledge else SKIN_FROM

    def fill(col, low):
        for y in range(max(low, foot(col)), soffit[col] + 1):
            put(col[0], y, col[1], IRON.block)

    for col in frame:
        top = soffit[col]
        beside = any(O.step(col, d) in gap for d in (O.NORTH, O.SOUTH))
        at_head = any(O.step(col, d) in gap for d in (O.EAST, O.WEST))
        if at_head and not beside:
            fill(col, top - HEAD_DEPTH + 1)
        elif col in shell.ledge:
            fill(col, foot(col))                    # at the wall the beam stands on the base ring
        else:
            near = [soffit[n] for n in (O.step(col, d) for d in O.SIDES) if n in frame]
            fill(col, min([top - JAMB_DEPTH + 1] + near))

    free = shell.reach - gap - frame
    for a in rib_angles():
        cols = [col for col in free if _on_meridian(col[0], col[1], a) and _polar(*col)[0] >= COLLAR[1]]
        last = None
        for col in sorted(cols, key=lambda col: -_polar(*col)[0]):      # from the wall inwards
            top = soffit[col]
            if last is None:
                fill(col, foot(col) if col in shell.ledge else top)
            else:
                fill(col, min(top, last + 1))       # from where the column before stopped: one unbroken line
            last = top
    for col in free:
        if COLLAR[0] <= _polar(*col)[0] < COLLAR[1]:
            put(col[0], soffit[col], col[1], IRON.block)


def _wall(c, origin, put, shell):
    """The ring beam under the wall's top, the consoles, the posts."""
    lay = O.Laying(c, None, origin, None)
    lay.mould(shell.ledge, WALL_TOP, IRON.stairs, "top", only=shell.edge - set(GEAR_SHAFT))
    lay.mould(shell.ledge, WALL_TOP - 1, IRON.stairs, "top", only=shell.consoles())
    for x, z in shell.posts():
        for y in range(FEET, WALL_TOP):
            put(x, y, z, IRON.block)


def _floor(put, shell):
    """The floor's finish, in the row of the boards main/shell lays."""
    for x, z in shell.edge:
        put(x, FLOOR_Y, z, WOOD.block)
    cells = observing_floor()
    for x, z in cells:
        open_sides = [d for d in O.SIDES if O.step((x, z), d) not in cells]
        corner = len(open_sides) == 2 and open_sides[0][0] != open_sides[1][0] and open_sides[0][1] != open_sides[1][1]
        put(x, FLOOR_Y, z, IRON.block if corner else WOOD.block)


def _fittings(put):
    """What is built into the wall, flush with it and below the windows: the switchboard of the
    dome's drive in the east niche."""
    for i, (x, z) in enumerate(niches()["east"]):
        for row, names in enumerate(BOARD):
            put(x, FEET + row, z, B.PANELS[names[i]] + "[facing=west]")


def _clock(c, origin, put):
    """The sidereal clock in the south niche: the regulator of props/instruments on the niche's back
    wall. While that is not in the tree, a dial in a wooden case that fills the niche. Returns the
    number of display entities."""
    cells = niches()["south"]
    x, z = cells[len(cells) // 2]
    instruments = _other("props", "instruments")
    if instruments is not None:
        return instruments.place(c, "regulator_clock", (x + 0.5, FEET + CLOCK_LIFT, z + 1.0), facing="north",
                                 origin=origin)
    for cell in cells:
        for y in (FEET, FEET + 1):
            put(cell[0], y, cell[1], WOOD.block)
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
    if furniture is not None and paper is not None:
        top = FEET + furniture.TOP[DESK[0]]
        n += paper.place(c, "logbook", (LOGBOOK[0], top, LOGBOOK[1]), facing=DESK[2], origin=origin)
    n += K.put(c, _models()[PREFIX + "chair"], (CHAIR[0], FEET, CHAIR[1]), yaw=CHAIR_YAW, origin=origin)
    return n


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
    if _other("props", "instruments") is None:
        kz -= 1                                 # the stand-in clock fills the niche: the cell in front of it
    return [((bx - 1, FEET + 1, bz), *PILOT_LAMPS, "pilot_lamps"),
            ((kx, FEET + 1, kz), *CLOCK_DIAL, "clock_dial")]


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
