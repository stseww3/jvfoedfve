"""Work package interiors/domeroom: the great dome room (plan ART-PLAN 8, view V8).

The star piece is the great refractor on its pier, pointing through the slit at the comet. The room
dresses the shell that stands on the canvas and never builds it: the drum and the dome's skin are
main/dome (c222), the floor, the opening round the pier and its railing are main/shell (c231), the
telescope is machines/refractor (c237), the track, rollers, chains and winch are machines/domegear
(c196). Where the skin is and where it is open is read off the canvas, so the room follows the dome
when its slit is changed.

What the room adds, from the floor up (rows; radii from the centre of column (4, 0)):

    17       the floor's finish: a dark border along the wall, the observing floor at the eyepiece
             (a rising floor at rest, level with the boards: an iron rim round dark boards)
    18..22   an iron wall post under six ribs and under the two beams of the slit; an iron console
             under the ring beam where the other ribs come down
    23       the ring beam: iron corbelled out from the wall's top, fixed to the stone (10.5..11.5)
    24       the ledge on the inner leaf, left empty: the track and its rollers (machines/domegear)
    25       the dome's base ring over that ledge (11.5..12.5): what turns, and what the ribs stand on
    26..     twenty iron ribs under the skin, one under each rib outside, up to a collar ring; a
             heavier beam along either side of the slit and a lighter one across its head

and what stands in the room: the switchboard of the dome's drive in the east niche, the instrument
cabinet in the north niche, the sidereal clock in the south niche, the record desk with the small
red lamp against the railing south of the pier, the observing chair. The observer, the recorder and
the camera of V8 keep to the south of the tube: the comet's tail leans north, so only from there is
all of it seen through the slit (sky/comet, c230).

Light (plan 3.2): the sky in the slit is the cold base and the brightest thing; the warm points are
the red lamp on the desk, the pilot lamps of the switchboard and the clock's dial, all third rank.

Still stand-ins, in blocks: the desk, the chairs, the clock (props/furniture, props/instruments).
The room places no display entity yet and returns 0 against the indoor budget.

build() is what the master scene calls; it places nothing until MOVED_IN is set (c231's shell and
c222's dome in the master scene, the room reviewed). Until then the room lives in its box test
scene (build/scenes/obs_int_domeroom), which calls dress().
"""
import math

from ..common import blocks as B
from ..common import skeleton as S
from ..main import _order as O
from ..props import _kit as K

ORDER = 80                  # after the shell and the dome (60)
MOVED_IN = False

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
COLLAR = (5.0, 6.0)                             # the ring the ribs run into, as outside
POSTS = (27.0, 63.0, 117.0)                     # the ribs that come down on a wall post, and their
#                                                 mirror images in the axis; the others get a console
JAMB_DEPTH = 2                                  # rows the beams beside the slit hang below the skin
HEAD_DEPTH = 1                                  # the beam across its head: no lower, the comet's tail
#                                                 passes just under it (sky/comet)

IRON = B.IRON_RIVETED
WOOD = B.DARK_WOOD

# --- what stands in the room (cells) ---------------------------------------------------------------
DESK = ((1, 5), (2, 5), (3, 5))                 # the record desk, against the railing south of the pier
DESK_SEAT = (2, 6)                              # the recorder sits south of it and looks at the telescope
RED_LAMP_ON = (1, 5)                            # the desk's west end
CHAIR = ((10, -3), (11, -3))                    # the observing chair, pushed aside north-east of the eyepiece
# bottom course first; the instrument panels of the dome's drive (blocks.PANELS)
BOARD = (("knife_switch", "bus_switch", "knife_switch"),
         ("dial", "pilot_lamps", "gauges"))

# --- light: (level, rank); sky/lights decides where the invisible blocks really go -----------------
RED_LAMP = (6, 3)
PILOT_LAMPS = (5, 3)
CLOCK_DIAL = (4, 3)


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


def stair_exit():
    """The cell one steps onto from the ring stair (main/shell.EXIT)."""
    return (S.PIER_ENVELOPE[2] + 1, CZ)


def niches():
    """The four flat recesses of the round wall on the axes, each three columns wide:
    {"east": [cells from low to high], ...}."""
    cells = room()
    xs, zs = [c[0] for c in cells], [c[1] for c in cells]
    ends = {"east": max(xs), "west": min(xs), "south": max(zs), "north": min(zs)}
    return {side: sorted(c for c in cells if c[side in ("south", "north")] == at) for side, at in ends.items()}


def doorways():
    """The room's end of the two doors to the roof terraces: for each, the first column of the room
    behind the skeleton's door column, going straight in."""
    inside, out = room(), []
    for cell in S.DOME_ROOM_DOORS["cells"]:
        step = (0, -1 if cell[1] > CZ else 1)
        while cell not in inside:
            cell = O.step(cell, step)
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
    """Where the telescope's eyepiece is (x, y, z in blocks). Read from machines/refractor once its
    module says it; until then worked out from the numbers the director gave (elevation 41 degrees,
    the axes cross 5 above the pier's top, the tube runs 5 back from there, on the axis)."""
    try:
        from ..machines import scope
        for name in ("eyepiece", "EYEPIECE"):
            got = getattr(scope, name, None)
            if got is not None:
                return tuple(got() if callable(got) else got)
    except ImportError:
        pass
    ax, az = S.DOME_AXIS
    elev, back, cross = math.radians(41.0), 5.0, S.PIER_TOP_Y + 5.0
    return (ax + back * math.cos(elev), cross - back * math.sin(elev), az)


def observing_floor():
    """The columns of the observing floor, the rising floor at rest: four by four, east of the stair's
    exit, from the tube's line southwards (where the comet is seen from). machines/refractor stands
    its rams under the four corners."""
    ex, _ey, ez = eyepiece()
    x0, z0 = max(int(math.floor(ex)) + 1, stair_exit()[0] + 1), int(math.floor(ez)) - 1
    return O.box(x0, z0, x0 + 3, z0 + 3) & (room() - envelope())


class Shell:
    """The shell as it stands on the canvas, read before the room adds anything."""

    def __init__(self, c, origin=(0, 0, 0)):
        ox, oy, oz = origin
        self.inside, self.ledge = room(), leaf()
        self.edge = self.inside - O.shrink(self.inside)
        self.reach = self.inside | self.ledge
        self.soffit = {}                # column -> the row under the dome's skin; None where the sky is open
        for x, z in self.reach:
            self.soffit[(x, z)] = None
            for y in range(SKIN_FROM, S.DOME_APEX + 4):
                if c.has(ox + x, oy + y, oz + z):
                    self.soffit[(x, z)] = y - 1
                    break
        roofed = any(y is not None for y in self.soffit.values())
        self.gap = {col for col, y in self.soffit.items() if y is None} if roofed else set()
        self.frame = (O.ring(self.gap) & self.reach) - self.gap

    def touches_wall(self, col):
        return any(O.step(col, d) in self.ledge for d in O.SIDES)

    def at_angle(self, angle):
        """The column along the wall that a rib at `angle` comes down on."""
        cells = [e for e in self.edge if self.touches_wall(e)]
        return min(cells, key=lambda e: (round(_apart(_polar(*e)[1], angle), 3), abs(e[1] - CZ), abs(e[0] - CX), e))

    def posts(self):
        """The columns of the wall posts: under the POSTS ribs on either side of the axis, and where
        the beams beside the slit meet the wall."""
        out = {self.at_angle(a) for angle in POSTS for a in (angle, 360.0 - angle)}
        return out | {col for col in self.frame & self.edge if self.touches_wall(col)}

    def consoles(self):
        """The columns where a rib comes down on the ring beam alone."""
        taken = self.posts()
        out = set()
        for a in rib_angles():
            col = self.at_angle(a)
            if col not in taken and not any(_on_meridian(g[0], g[1], a) for g in self.gap & self.edge):
                out.add(col)
        return out


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
    _furniture(put, shell)
    _offer(c, origin, lights())
    return 0


def _vault(put, shell):
    """The dome's base ring, the beams round the slit, the ribs, the collar."""
    soffit, gap, frame = shell.soffit, shell.gap, shell.frame
    if not any(y is not None for y in soffit.values()):
        return
    for x, z in shell.ledge:
        put(x, BASE_RING_Y, z, IRON.block)

    def foot(col):
        return BASE_RING_Y + 1 if col in shell.ledge else SKIN_FROM

    for col in frame:
        top = soffit[col]
        beside = any(O.step(col, d) in gap for d in (O.NORTH, O.SOUTH))
        at_head = any(O.step(col, d) in gap for d in (O.EAST, O.WEST))
        depth = HEAD_DEPTH if at_head and not beside else JAMB_DEPTH
        near = [soffit[n] for n in (O.step(col, d) for d in O.SIDES) if n in frame]
        low = max(foot(col), min([top - depth + 1] + [y + 1 for y in near]))
        for y in range(low, top + 1):
            put(col[0], y, col[1], IRON.block)

    def run(cols):
        """A rib under the skin along `cols` (ordered from the wall inwards): each column is filled up
        to the skin from where the one before it stopped, so the rib is one unbroken line."""
        last = None
        for col in cols:
            top = soffit[col]
            low = foot(col) if last is None else max(foot(col), min(top, last + 1))
            for y in range(low, top + 1):
                put(col[0], y, col[1], IRON.block)
            last = top

    free = shell.reach - gap - frame
    for a in rib_angles():
        cols = [col for col in free if _on_meridian(col[0], col[1], a) and _polar(*col)[0] >= COLLAR[1]]
        run(sorted(cols, key=lambda col: -_polar(*col)[0]))
    for col in free:
        if COLLAR[0] <= _polar(*col)[0] < COLLAR[1]:
            put(col[0], soffit[col], col[1], IRON.block)


def _wall(c, origin, put, shell):
    """The ring beam under the wall's top, the posts, the consoles."""
    lay = O.Laying(c, None, origin, None)
    lay.mould(shell.ledge, WALL_TOP, IRON.stairs, "top", only=shell.edge)
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
        rim = any(O.step((x, z), d) not in cells for d in O.SIDES)
        put(x, FLOOR_Y, z, IRON.block if rim else WOOD.block)


def _furniture(put, shell):
    """What stands in the room. The switchboard and the cabinet are built into the niches, flush with
    the wall, and keep below the window; the rest are stand-ins in blocks."""
    n = niches()
    for i, (x, z) in enumerate(n["east"]):
        for row, names in enumerate(BOARD):
            put(x, FEET + row, z, B.PANELS[names[i]] + "[facing=west]")
    for x, z in n["north"]:
        for y in (FEET, FEET + 1):
            put(x, y, z, B.PANELS["drawers"] + "[facing=south]")
    kx, kz = n["south"][1]
    put(kx, FEET, kz, WOOD.block)
    put(kx, FEET + 1, kz, B.PANELS["dial"] + "[facing=north]")
    for x, z in DESK:
        put(x, FEET, z, f"{WOOD.slab}[type=top]")
    put(DESK_SEAT[0], FEET, DESK_SEAT[1], f"{WOOD.stairs}[facing=south,half=bottom]")
    (ax, az), (bx, bz) = CHAIR
    put(ax, FEET, az, f"{WOOD.stairs}[facing=east,half=bottom]")
    put(bx, FEET, bz, WOOD.block)
    put(bx, FEET + 1, bz, f"{WOOD.stairs}[facing=east,half=bottom]")


def lights():
    """[((x, y, z), level, rank, name)] the light sources the room asks for, in scene cells without
    the origin: each sits in the cell of something that is seen to glow."""
    n = niches()
    bx, bz = n["east"][1]
    kx, kz = n["south"][1]
    return [((RED_LAMP_ON[0], FEET + 1, RED_LAMP_ON[1]), *RED_LAMP, "red_lamp"),
            ((bx - 1, FEET + 1, bz), *PILOT_LAMPS, "pilot_lamps"),
            ((kx, FEET + 1, kz - 1), *CLOCK_DIAL, "clock_dial")]


def _offer(c, origin, wanted):
    """Hand the room's light sources to the light line: sky/_lightkit.suggest when it is in the tree,
    else the props kit's stand-in, which drops the blocks itself."""
    ox, oy, oz = origin
    try:
        from ..sky import _lightkit
        suggest = getattr(_lightkit, "suggest", None)
    except ImportError:
        suggest = None
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
