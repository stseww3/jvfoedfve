"""site/powerhouse: the shell of the power house on the lower platform, its chimney and the pipe
bridge that carries the steam main up to the upper terrace (plan/ART-PLAN.md 4, 5.3; card
plan/packages/site/powerhouse.md). The inside (engine, dynamo, boilers, switchboard) is
interiors/powerhouse: here stands an empty shell, and windows() says where its glass is.

The house fills the skeleton's box (S.POWER_HOUSE): 23 by 23 cells, walls ten courses high from the
lower platform's paving. It is the works building of the hill and speaks the main building's
grammar in the lower platform's stone: a pier of one cell and a window of three (S.BAY), tuff brick
between polished courses.

  walls     Two planes. The pier plane is the edge of the box: a polished plinth course with a
            weathering, brick piers with a polished impost, a round arch over every bay (the main
            building's: main/_order.arch), a polished cornice, an iron gutter. One cell behind it
            stands the glass, six rows of it over a polished sill: every bay is a recess a block
            deep. The corners are piers two cells square. The clear floor inside is ROOM.
  windows   Iron-framed and dark. Only the two bays beside the chimney, where the boilers stand,
            glow in their lower three rows: the fire window, a block of its own for each row,
            brightest at the sill (B.WINDOW_FURNACE; the curtain glass stands in while the switch
            FIRE is off). The sky line gives them their light (sky/_lightkit.glazed): a source in
            the room's first cell behind the glass, which the inside therefore leaves free. The
            materials line lines their room side: in the master scene it reads windows() and
            does so itself (materials/windows.build); a scene that builds the house without that
            line calls lining().
  door      The second bay of the north front, from the yard: a riveted gate with a wicket. The
            wicket is the way into the house and stands open (A0, g2 #37124: a door that is to be
            walked through is not left for the visitor to open). A caged lamp on the gate's lintel
            marks it (DOOR_LAMP, LAMP_AT): the props line's model, placed here.
  chimney   In the north-east corner, wholly inside the box and outside the arrival view. Its foot
            is a tower six cells square, the corner pier, a bay and the next pier built solid, with
            a blind arch on each outer face; three courses above the eaves it steps in under a
            weathering to a square shaft four cells across, banded with iron every fourth course,
            with a polished necking under the head. The head is a corbel course under a weathered
            coping, six across and mitred at the corners like the weathering below; over it the
            mouth is as narrow as the shaft again and rimmed with iron, at y 23 (S.POWER_HOUSE).
            The shaft was a round once, a cross of twelve cells, and each of its four corners a
            notch one cell deep: on the diagonal, which is how V6 sees it, that was a black groove
            from the shoulder to the head and the shaft two posts side by side (review cr2-#7).
            A block cannot round a corner at this size, so the shaft is square and its faces whole.
  roof      Two versions (VERSION), and they differ in nothing else. Both show their profile to
            the yard in the north, where V6 stands, and their flank to the court.
            "a"  Five saw teeth, one to the bay of the north front, their ridges north-south: a
                 light of two rows of glass that looks west over an iron girder, a slate slope of
                 45 degrees behind it. The north and south walls close the saw with brick gables
                 under a stone verge. (A north light it is not: the profile went to V6.)
            "b"  An iron barrel vault over the hall, its axis north-south, rising five over a
                 span of 17 (x 68..84): its middle is the middle pier of the four bays the yard
                 sees beside the chimney. Its ends are iron screens with a three-light window; a
                 glazed monitor rides the crown. East of it, behind the chimney, the boiler
                 house lies under a flat of plates.
  bridge    The steam main leaves the west front through the pier in row PIPE_Z, a course under
            the cornice, and runs west in that one row: over the alley on a girder that a portal
            of two iron posts carries, over the terrace's railing without touching it (the girder's
            underside is half a block above the bars), to the bridge head two cells inside the
            railing, where it turns down into the ground: a riveted elbow, a length of plate, a
            riveted foot on a stone plinth three cells square and half a block high, the terrace's
            dressing stone. A knee on the down pipe carries the girder's end, so that one sees
            between the pipe and the railing; two cover plates in the paving west of the plinth
            say which way the main goes on under the court. A cable runs over it. The row is south
            of the court and never crosses the axis.
  run       RUN lays the main on along the ground of the upper terrace to the foot of the main
            building. Off by default: the master scene shows the main going into the ground at the
            bridge head and nothing more of it up there.
  fittings  What hangs on the shell and is the props line's to make and to place (props/pipes):
            FITTINGS, the valve head and the straps on the main; DRAINS, the gutter's two
            rainwater pipes.

  vents     Roof "a": a rotary ventilator at each end of the four whole ridges (VENTS), turning.

The shell is blocks. The display entities build() places are the lamp over the wicket, which it
asks the props line for, and the roof's ventilators, its own model (models()).
"""
import functools
import importlib

from artkit import models as M

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from ..motion import _kit as MK
from . import _kit as K

ORDER = 70      # after the lower platform (20), the retaining wall (25) and the court (60)

VERSION = "a"   # the roof that build() makes when it is not told: "a" the saw teeth, "b" the vault
RUN = False     # the main's run along the ground of the upper terrace (see above)
FIRE = True     # the boiler bays glow through the fire window; off, the curtain glass stands in its place.
#                 On since the role is in the assembly, materials/windows paints it and the sky line's
#                 kit knows it (review cr2, #74016)

# --- where it stands --------------------------------------------------------------------------------
X0, Z0, X1, Z1 = S.POWER_HOUSE["box"]               # x 67..89, z 20..42: the pier plane
FEET = S.POWER_HOUSE["base_y"]                      # -6, the first course
EAVES = FEET + S.POWER_HOUSE["wall_h"] - 1          # 3, the cornice course
TOP = FEET + S.POWER_HOUSE["chimney_h"] - 1         # 23, the chimney's rim
SPAN = X1 - X0 + 1                                  # 23 cells, both ways
BAY = S.BAY                                         # 4: a pier and three cells of window
CORNER = 2                                          # a corner pier is two cells square
N_BAYS = (SPAN - 2 * CORNER + 1) // BAY             # 5

# the courses of a front
PLINTH_Y = FEET                                     # -6
TABLE_Y = FEET + 1                                  # -5, the plinth's weathering
SILL_Y = FEET + 2                                   # -4
GLASS_Y = (FEET + 3, EAVES - 1)                     # -3..2, six rows of glass
ARCH_Y = EAVES - 1                                  # 2, the arch hangs in the top row of the opening
IMPOST_Y = ARCH_Y - 1                               # 1, the polished course of a pier the arches spring from
FURNACE_Y = (GLASS_Y[0], GLASS_Y[0] + 2)            # -3..-1, the rows that glow in a boiler bay
# The light behind a fire window, as sky/_lightkit counts it (windows(): level): the top of the
# second rank, what the lit windows of the main building have behind them and no window may pass
# (c331 #59302). It leaves 9 on the jambs and the sill, and 9 is where stone begins to turn warm.
FURNACE_LEVEL = 12
# The fire's light on the ground before a boiler bay. The sky line's source stands in the recess
# before the glass, three rows over the paving, and what reaches the paving the night swallows:
# the bay glowed over black ground (reviews cr2-#7, 1 and #74016, 1). So the shell offers that line
# one more source to a fire window (pools()): before the pier plane in the window's middle column,
# two rows under the glass, which is as low as that line lets a source stand from what glows. As
# bright as what the window has behind it and no brighter: the paving under it gets 11, the cells
# round that 10 and 9, three cells out from the wall (in the picture 0.22 where 0.16 was; the
# ground before the door has 0.23). With 10, what the recess has, the pool was there by numbers
# and not in the picture: the yard at dusk is as bright as 9 by itself.
POOL_LEVEL = FURNACE_LEVEL
POOL_WHY = "site/powerhouse:fire window"
GATE_ROWS = 4                                       # the door bay: a gate this high, a lintel, glass
FURNACE_LIGHT = 5                                   # the source before a boiler bay's glow while the sky line's kit
#                                                     is not in the tree (its figure for a low curtain window)

# the inside, for interiors/powerhouse and the machines
ROOM = (X0 + CORNER, Z0 + CORNER, X1 - CORNER, Z1 - CORNER)     # x 69..87, z 22..40: the clear floor
ROOM_Y = (FEET, EAVES)                              # feet at -6; the roof's lowest member is above EAVES

# the chimney: its foot is the corner pier, the fifth bay of the north front and the pier before it
TX0, TZ0, TX1, TZ1 = X1 - CORNER - BAY + 1, Z0, X1, Z0 + CORNER + BAY - 1      # x 84..89, z 20..25
TOWER = (TX0, TZ0, TX1, TZ1)
PED_TOP = EAVES + 3                                 # 6, the cornice of the square foot
HOOP_STEP = 4                                       # an iron hoop every fourth course of the shaft
FLUE_DEPTH = 6                                      # the courses the flue is open, from the rim down
SHAFT = [(x, z) for x in range(TX0 + 1, TX1) for z in range(TZ0 + 1, TZ1)]     # a square of four: 16 cells
FLUE = [(x, z) for x in (TX0 + 2, TX0 + 3) for z in (TZ0 + 2, TZ0 + 3)]
SMOKE = (TX0 + 3.0, TOP + 1.0, TZ0 + 3.0)           # the middle of the flue's mouth, for the motion line's smoke

# the roofs stand on the plane of the glass, one cell inside the box
RX0, RZ0, RX1, RZ1 = X0 + 1, Z0 + 1, X1 - 1, Z1 - 1     # x 68..88, z 21..41
VX0, VX1 = RX0, TX0                                 # x 68..84, version b: the vault over the hall. Its middle is
#                                                     the middle pier of the four bays the yard sees; east of
#                                                     it, behind the chimney, is the boiler house's flat
# The vault's top above the eaves course, in half blocks, from its foot (0) to the crown (8): a
# segment of a circle of radius 9.7 that rises 5 over the span of 17.
VAULT = (1.0, 2.0, 3.0, 3.5, 4.0, 4.5, 5.0, 5.0, 5.0)
LIGHT_MULLION = 3                                   # the end screen's two mullions stand this far from the middle

# the pipe bridge
PIPE_Z = Z0 + CORNER + 3 * BAY - 1                  # 33, the third pier of the west front. props/lamps reads
#                                                     it: no lamp on the lip's piers next to this row
PIPE_Y = EAVES - 1                                  # 2, the main; the girder is one below, the cable one above
PIPE_OUT = (X0, PIPE_Y, PIPE_Z)                     # the pier cell the main leaves the house through
PIPE_IN = (X0 + CORNER, PIPE_Y, PIPE_Z)             # the first cell of the room behind the sleeve: the main starts here
HEAD_X = S.EAST_EDGE_X - 2                          # 58, where the main goes down into the upper terrace
POSTS_X = (X0 - 5, X0 - 2)                          # 62 and 65, the portal in the alley
JOINT_STEP = 3                                      # a riveted collar on the main every third cell
RUN_X = (K.FOOT_STRIP_X + 2, HEAD_X - 1)            # x 22..57, the main on the terrace's ground when RUN is on
COVERS_X = (HEAD_X - 3, HEAD_X - 2)                 # 55 and 56: cover plates in the paving west of the head's plinth
CROSSING = (43, 47)                                 # there the path to the south lookout crosses it (the site
#                                                     lead's figures): the main dips under five cover plates
# What the props line hangs on the main, as props/pipes.mount() takes it: (kind, point, keywords).
# The shell places none of it (it has no display entity); props/pipes reads the table when it
# dresses the site, and this package's test scenes mount it themselves. A valve head with the
# bridge's one red handwheel on the west face of the down pipe, towards the court; a strap over
# the joint in the middle of each plain length of the main, between two riveted collars.
FITTINGS = ([("bonnet", (float(HEAD_X), S.GROUND + 1.5, PIPE_Z + 0.5), dict(out="west"))]
            + [("band", (float(x), PIPE_Y + 1.0, PIPE_Z + 0.5), dict(out="up", up="east"))
               for x in range(HEAD_X + 2, X0, JOINT_STEP)])
# Where the gutter's rainwater pipes come down, as props/pipes.drain() takes them (c241, g2 #37478):
# `at` is the point of the wall face behind the pipe, right under a slab of the gutter; `top` is
# the gutter's row, `bottom` the ground the pipe goes into. Two on the north front, the one the
# yard looks at: on the corner pier and on the last pier before the boiler bay. East of that the
# gutter runs on over the glowing window to the chimney's foot, where nothing can hang.
DRAINS = [dict(at=(x + 0.5, float(Z0)), facing="north", top=EAVES + 1, bottom=FEET)
          for x in (X0, X0 + CORNER + 3 * BAY - 1)]

# --- the ventilators on the saw roof (the shell's own display model; they turn) ----------------------
# A rotary ventilator at each end of the four whole ridges: a drum of slanted vanes between a
# throat plate and a crown, on a spigot that stands on the ridge roll, in the middle of the end
# bay of the light. Whatever wind there is turns it, always the same way. One display entity
# each, and the whole of it turns: the spigot is round and plain, so that is not seen. From the
# yard (V6) the three at the north ends of the inner ridges show between the gables' teeth; from
# the upper terrace the two on the west light. Roof "a" only: the vault has its monitor.
#
# How far the shell's display entities are drawn (VIEW, which the assembly applies to all a module
# places: here the ventilators and the lamp over the wicket): the near band, 32 blocks. Machines
# out of doors would have the middle one, but the arrival view (V1) looks this way from 58 blocks
# off and is over its count of entities; from the yard, the stair and the terrace's lip they are
# all within 32.
VIEW = M.NEAR
# Where the shell's own display models are placed (DRESS; build(dress=) overrides it): None, in
# the master scene only (canvas.master). Several test scenes of other packages borrow this shell
# with build() and pack their own models, not the shell's: a ventilator there would show a model
# their pack does not have. This package's own test scenes set it True. The lamp over the wicket
# is the props line's model and is placed everywhere.
DRESS = None
MODEL_VENT = "site_power_vent"
VENT_REV = 60                                       # ticks a turn: a vane passes every 7.5 ticks. Eight of them
#                                                     at four steps a turn are half a command a tick
VENT_BEHIND = 7                                     # ticks the south row is behind the north one, so that the
#                                                     eight do not all ask for their step in one tick
VENT_R = 10.0                                       # pixels: the drum's radius, a block and a quarter across
VENT_VANES = 8
VENT_SLANT = 35.0                                   # degrees a vane is turned out of the drum's round
VENT_TOP = 24.0                                     # pixels from the ridge roll to the nut on the crown: y 9.0
VENTS = [(x + 0.5, EAVES + 4.5, z)                  # the middle of the ridge roll's top: y 7.5
         for x in range(RX0, RX0 + 4 * BAY, BAY) for z in (RZ0 + 2.5, RZ1 - 1.5)]

# --- materials (the occupancy table's roles) --------------------------------------------------------
BODY = B.TUFF_BRICK.block
BRICK_STAIRS = B.TUFF_BRICK.stairs
COURSE = B.TUFF_SMOOTH.block                        # plinth, sill, cornice
TABLE = B.TUFF_SMOOTH.stairs
IRON = B.IRON_RIVETED.block
IRON_STAIRS = B.IRON_RIVETED.stairs
IRON_TOP = B.IRON_RIVETED.slab + "[type=top]"
IRON_LOW = B.IRON_RIVETED.slab + "[type=bottom]"
PLATE = B.IRON_PLATE
DARK = B.WINDOW_DARK.block
GLOW = B.WINDOW_CURTAIN.block                       # stands in for the fire window: _glow()
ROOF_GLASS = B.SKYLIGHT.block
SLATE = B.SLATE_TILE.stairs
VERGE_CAP = B.TUFF_SMOOTH.slab + "[type=bottom]"    # the stone on the point of a saw tooth's gable
PLINTH = B.TUFF_SMOOTH.slab + "[type=bottom]"       # the bridge head's plinth on the upper terrace

# --- the fronts -------------------------------------------------------------------------------------
STEP = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
OPPOSITE = {"north": "south", "south": "north", "west": "east", "east": "west"}
WINDOW, FURNACE, DOOR = "window", "furnace", "door"


class Front:
    """One of the four fronts. t counts the cells along it from 0, towards `along`; d counts the
    cells into the house: 0 is the pier plane, 1 the plane of the glass."""

    def __init__(self, name, along):
        self.name, self.along = name, along
        self.back = OPPOSITE[along]
        self.inward = OPPOSITE[name]

    def at(self, t, d=0):
        if self.name == "north":
            return X0 + t, Z0 + d
        if self.name == "south":
            return X0 + t, Z1 - d
        if self.name == "west":
            return X0 + d, Z0 + t
        return X1 - d, Z0 + t


FRONTS = {f.name: f for f in (Front("north", "east"), Front("east", "south"), Front("south", "east"),
                              Front("west", "south"))}
# What fills a bay. The bays of a front are counted from 1 along it: from the west on the north and
# south fronts, from the north on the east and west fronts. The chimney's foot takes the fifth bay
# of the north front and the first of the east; the boilers stand behind the two bays next to it.
FILL = {
    "north": {1: WINDOW, 2: DOOR, 3: WINDOW, 4: FURNACE},
    "east": {2: FURNACE, 3: WINDOW, 4: WINDOW, 5: WINDOW},
    "south": {1: WINDOW, 2: WINDOW, 3: WINDOW, 4: WINDOW, 5: WINDOW},
    "west": {1: WINDOW, 2: WINDOW, 3: WINDOW, 4: WINDOW, 5: WINDOW},
}
# The wicket: the cell of its leaf and the rows of the opening. It stands open; the way in is
# through this cell, so the room's cell behind it is to stay clear.
DOOR_AT = dict(front="north", bay=2, cell=FRONTS["north"].at(CORNER + BAY + 1, 1), y=(FEET, FEET + 1))
# The lamp over the wicket: the props line's caged wall lamp on the outer face of the gate's lintel,
# in its middle, low enough for its conduit to turn into the lintel and not into the glass over
# it. The lamp offers its own light source to the sky line, at the level that line gave the lamp
# (7). It is the one lamp of the front and stays at that level: beside the fire window it is a
# small warm point that says where the door is.
DOOR_LAMP = True
LAMP_AT = dict(kind="cage", version="a", facing="north",
               pos=(DOOR_AT["cell"][0] + 0.5, FEET + GATE_ROWS + 0.3125, float(DOOR_AT["cell"][1])))


def _bay(t):
    """(bay, i) for a cell t along a front that lies in a bay: the bay's number from 1 and the
    cell's place in it, 0 to 2. None for the cells of the piers."""
    k, i = divmod(t - CORNER, BAY)
    if t >= CORNER and k < N_BAYS and i < BAY - 1:
        return k + 1, i
    return None


def _in_tower(x, z):
    return TX0 <= x <= TX1 and TZ0 <= z <= TZ1


def _inside(x, z):
    """Whether a column lies behind the pier plane of all four fronts."""
    return X0 < x < X1 and Z0 < z < Z1


def _other(path):
    """A module of another line ("sky._lightkit"); None while it is not in the tree."""
    full = f"{__package__.rpartition('.')[0]}.{path}"
    try:
        return importlib.import_module(full)
    except ModuleNotFoundError as e:
        if not e.name or not f"{full}.".startswith(f"{e.name}."):
            raise               # it is there and cannot import something of its own: say so
        return None


def _glow(row):
    """The glass of a glowing row of a boiler bay, `row` counted up from the sill: the fire window
    (B.WINDOW_FURNACE, a role for each of the three rows, the sill's first) when FIRE is on and the
    occupancy table has it, the curtain glass otherwise."""
    fire = getattr(B, "WINDOW_FURNACE", None) if FIRE else None
    return GLOW if fire is None else fire[row].block


def windows(version=None):
    """The glass of the shell, as records sky/_lightkit.glazed() takes and interiors can read:
    front ("power.north", ...), bay, storey, cells (the glass columns (x, z)), inward (the step
    from the glass into the house) and y (the bottom and top row of the glass).

    storey "main" is dark glass; "furnace" is the lower three rows of a boiler bay, which glow
    (the dark rows over them are that bay's "main"); "gable" is the middle light of the screen at
    either end of version b's vault, on the north and the south front (bay 0). Offsets are the
    skeleton's: add the origin the house is built at.

    A "furnace" record asks for its light by number (level, FURNACE_LEVEL): the fire window is the
    one warm place of the works, and the tuff round it takes half the light ashlar does, so the
    level a dim window gets leaves its bay black round the glass (review cr2-#7, 1)."""
    out = []
    for front in FRONTS.values():
        name = f"power.{front.name}"
        for bay, kind in sorted(FILL[front.name].items()):
            t0 = CORNER + BAY * (bay - 1)
            common = dict(front=name, bay=bay, cells=[front.at(t0 + i, 1) for i in range(BAY - 1)],
                          inward=STEP[front.inward])
            if kind == FURNACE:
                out.append(dict(common, storey="furnace", y=FURNACE_Y, level=FURNACE_LEVEL))
                out.append(dict(common, storey="main", y=(FURNACE_Y[1] + 1, GLASS_Y[1])))
            elif kind == DOOR:
                out.append(dict(common, storey="main", y=(FEET + GATE_ROWS + 1, GLASS_Y[1])))
            else:
                out.append(dict(common, storey="main", y=GLASS_Y))
    if (version or VERSION) == "b":
        mid = (VX0 + VX1) // 2
        for front in (FRONTS["north"], FRONTS["south"]):
            z = front.at(0, 1)[1]
            out.append(dict(front=f"power.{front.name}", bay=0, storey="gable",
                            cells=[(x, z) for x in range(mid - LIGHT_MULLION + 1, mid + LIGHT_MULLION)],
                            inward=STEP[front.inward], y=(EAVES + 2, EAVES + 4)))
    return out


def pools(version=None):
    """Where the fire's light falls on the ground before a boiler bay: [(x, y, z)], the cell of the
    source the shell offers the sky line for each "furnace" record of windows() (POOL_LEVEL).
    Offsets are the skeleton's."""
    out = []
    for w in windows(version):
        if w["storey"] == "furnace":
            x, z = w["cells"][len(w["cells"]) // 2]
            dx, dz = w["inward"]
            out.append((x - 2 * dx, w["y"][0] - 2, z - 2 * dz))
    return out


class _Pen:
    """Sets the house's blocks where it is built."""

    def __init__(self, canvas, origin):
        self.c = canvas
        self.o = tuple(int(v) for v in origin)

    def put(self, x, y, z, state):
        self.c.set(self.o[0] + x, self.o[1] + y, self.o[2] + z, state)

    def clear(self, x, y, z):
        self.c.clear(self.o[0] + x, self.o[1] + y, self.o[2] + z)


# --- the walls ----------------------------------------------------------------------------------------
def _pier(p, x0, z0, x1, z1):
    # The plinth of a pier is a whole block. The lower platform's railing counts on it: it ends
    # against the two south corners, at (X0, FEET, Z1) and (X1, FEET, Z1) (site/lowerplatform).
    p.put(x0, PLINTH_Y, z0, COURSE)
    for y in range(TABLE_Y, EAVES):
        p.put(x0, y, z0, COURSE if y == IMPOST_Y else BODY)
    p.put(x0, EAVES, z0, COURSE)
    if _inside(x1, z1):
        for y in range(PLINTH_Y, EAVES + 1):
            p.put(x1, y, z1, BODY)


def _recess(p, front, x, z, first, last, plinth=True):
    """One column of a bay in the pier plane: the plinth and its weathering, the opening, the arch,
    the cornice. The arch is the main building's (main/_order.arch): a stair hung from the cornice
    at either end of the opening, its solid quarter towards the jamb, and nothing between them, so
    that the head steps in by half a block twice: over three cells that is a half circle."""
    if plinth:
        p.put(x, PLINTH_Y, z, COURSE)
        p.put(x, TABLE_Y, z, f"{TABLE}[facing={front.inward},half=bottom]")
    if first or last:
        p.put(x, ARCH_Y, z, f"{BRICK_STAIRS}[facing={front.back if first else front.along},half=top]")
    p.put(x, EAVES, z, COURSE)


def _gate(p, front, x, z, middle):
    """One column of the door bay in the plane of the glass: a riveted gate with a wicket in its
    middle column, a lintel beam, glass over it. The wicket stands open: its leaf has swung into
    the house and stands across its cell, against the gate on the left of whoever goes in."""
    if middle:
        for y, half in ((FEET, "lower"), (FEET + 1, "upper")):
            p.put(x, y, z, f"{B.IRON_DOOR}[facing={front.inward},half={half},hinge=left,open=true]")
        for y in range(FEET + 2, FEET + GATE_ROWS):
            p.put(x, y, z, PLATE)
    else:
        for y in range(FEET, FEET + GATE_ROWS):
            p.put(x, y, z, IRON)
    p.put(x, FEET + GATE_ROWS, z, IRON)
    for y in range(FEET + GATE_ROWS + 1, EAVES):
        p.put(x, y, z, DARK)


def _walls(p):
    for front in FRONTS.values():
        fill = FILL[front.name]
        for t in range(SPAN):
            x0, z0 = front.at(t, 0)
            x1, z1 = front.at(t, 1)
            if _in_tower(x0, z0):
                continue
            where = _bay(t)
            if where is None or where[0] not in fill:
                _pier(p, x0, z0, x1, z1)
                continue
            bay, i = where
            kind = fill[bay]
            _recess(p, front, x0, z0, i == 0, i == BAY - 2, plinth=kind != DOOR)
            if kind == DOOR:
                _gate(p, front, x1, z1, i == 1)
            else:
                p.put(x1, PLINTH_Y, z1, BODY)
                p.put(x1, TABLE_Y, z1, BODY)
                p.put(x1, SILL_Y, z1, COURSE)
                for y in range(GLASS_Y[0], GLASS_Y[1] + 1):
                    glows = kind == FURNACE and y <= FURNACE_Y[1]
                    p.put(x1, y, z1, _glow(y - FURNACE_Y[0]) if glows else DARK)
            p.put(x1, EAVES, z1, BODY)
        for t in range(SPAN):
            x, z = front.at(t, 0)
            if not _in_tower(x, z):
                p.put(x, EAVES + 1, z, IRON_LOW)        # the gutter on the cornice


# --- the chimney ------------------------------------------------------------------------------------
def _ring_facing(x, z):
    """Which way a cell of the tower's outline looks inwards, None for a cell inside it."""
    if z == TZ0:
        return "south"
    if z == TZ1:
        return "north"
    if x == TX0:
        return "east"
    if x == TX1:
        return "west"
    return None


def _tower(p):
    # the foot: solid, as high as the walls and three courses more, a polished course at the
    # plinth, at the eaves and at its own top
    for x in range(TX0, TX1 + 1):
        for z in range(TZ0, TZ1 + 1):
            for y in range(FEET, PED_TOP + 1):
                p.put(x, y, z, COURSE if y in (FEET, EAVES, PED_TOP) else BODY)
    # a blind arch on each outer face, as wide as the foot allows between two piers of one cell
    width = TX1 - TX0 + 1
    for front, t0 in ((FRONTS["north"], SPAN - width), (FRONTS["east"], 0)):
        for s in range(1, width - 1):
            x, z = front.at(t0 + s, 0)
            for y in range(SILL_Y, ARCH_Y + 1):
                p.clear(x, y, z)
            _recess(p, front, x, z, s == 1, s == width - 2)
            bx, bz = front.at(t0 + s, 1)
            p.put(bx, SILL_Y, bz, COURSE)
        for s in (0, width - 1):
            x, z = front.at(t0 + s, 0)
            p.put(x, IMPOST_Y, z, COURSE)
    # the soot door in the north arch: a cast plate two cells square
    for x in (TX0 + 2, TX0 + 3):
        for y in (SILL_Y + 1, SILL_Y + 2):
            p.put(x, y, TZ0 + 1, B.IRON_CAST)
    # the shoulder: a weathering all round, from the square foot in to the shaft
    y = PED_TOP + 1
    for x in range(TX0, TX1 + 1):
        for z in range(TZ0, TZ1 + 1):
            facing = _ring_facing(x, z)
            p.put(x, y, z, BODY if facing is None else f"{BRICK_STAIRS}[facing={facing},half=bottom]")
    # the shaft: square, banded, the flue open in its top courses; under the head a polished necking
    for y in range(PED_TOP + 2, TOP - 2):
        hoop = (y - PED_TOP) % HOOP_STEP == 0
        necking = y == TOP - 3
        for x, z in SHAFT:
            if y > TOP - FLUE_DEPTH and (x, z) in FLUE:
                continue
            p.put(x, y, z, IRON if hoop else COURSE if necking else BODY)
    # the head: a bead six across, a corbel course under a weathered coping (a stair hung under a
    # stair), and over it the iron rim on the mouth of the shaft alone. The stairs of the four
    # corners turn the corner of themselves, as those of the shoulder do: the corbel and the coping
    # are mitred there. As wide as the foot for three courses it made the chimney a dumbbell (cr2,
    # g2 #36637), and a course and a half of whole blocks still read as a lid in the pictures: now
    # the full width is one course, half of the corbel and half of the coping.
    for x in range(TX0, TX1 + 1):
        for z in range(TZ0, TZ1 + 1):
            if (x, z) in FLUE:
                continue
            facing = _ring_facing(x, z)
            if facing is None:
                p.put(x, TOP - 2, z, BODY)
                p.put(x, TOP - 1, z, COURSE)
                p.put(x, TOP, z, IRON)
            else:
                p.put(x, TOP - 2, z, f"{BRICK_STAIRS}[facing={facing},half=top]")
                p.put(x, TOP - 1, z, f"{TABLE}[facing={facing},half=bottom]")


# --- the roofs ----------------------------------------------------------------------------------------
# Both roofs show their profile to the yard. V6 and the three other standpoints it may be given all
# look at the north front, and a roof that turns its profile east and west is a level line from
# there, the saw as much as the vault (the first pictures, b5078551): so the saw's ridges and the
# vault's axis run north-south, and the court looks at their flank.
def _roof_a(p):
    """The saw teeth. A tooth is one bay of the north front: on its pier line the light, which
    looks west over the court (a girder, two rows of glass between iron mullions on the west
    front's pier lines, a ridge roll), and east of it three courses of slate that fall into the
    valley before the next light. The north and south walls close the profile, each tooth a gable
    of brick under a verge of polished stone; the last row is the east wall's coping."""
    y = EAVES + 1
    for x0 in range(RX0, RX1, BAY):
        for z in range(RZ0, RZ1 + 1):
            gable = z in (RZ0, RZ1)
            if not _in_tower(x0, z):
                p.put(x0, y, z, BODY if gable else IRON)
                for h in (1, 2):
                    p.put(x0, y + h, z, BODY if gable else IRON if (z - RZ0) % BAY == 0 else ROOF_GLASS)
                p.put(x0, y + 3, z, VERGE_CAP if gable else IRON_LOW)
            for i in (1, 2, 3):
                if _in_tower(x0 + i, z):
                    continue
                top = y + 3 - i
                p.put(x0 + i, top, z, f"{TABLE if gable else SLATE}[facing=west,half=bottom]")
                if gable:
                    for fill in range(y, top):
                        p.put(x0 + i, fill, z, BODY)
    for z in range(RZ0, RZ1 + 1):
        if not _in_tower(RX1, z):
            p.put(RX1, y, z, COURSE)


def _lunette(h, d):
    """The screen under the vault's end, h rows above its tie beam and d cells from the middle: a
    window of three lights, the middle one five cells wide, between two iron mullions."""
    return IRON if h == 0 or d == LIGHT_MULLION else DARK


def _roof_b(p):
    """The barrel vault over the hall: riveted plates, a whole block under the top of every column,
    so that a column closes against the next. Where the curve climbs a whole course from one
    column to the next (the three columns at either foot) the plate is a stair, and the curve comes
    out of the gutter in half steps; above them it rises by half a block at a time. A rib half a
    block proud of the plates lies on every pier line of the long sides. An end is an iron screen,
    glazed, under the vault's own last row. The monitor rides the crown between the second pier
    line from either end, glazed, open to the house below. East of the vault, behind the chimney,
    the boiler house has a flat of plates under the same ribs."""
    base = EAVES + 1
    mid = (VX0 + VX1) // 2
    m0, m1 = RZ0 + BAY, RZ1 - BAY
    for x in range(VX0, VX1 + 1):
        d = min(x - VX0, VX1 - x)
        rise = VAULT[d]
        k = int(rise)
        top = base + k - 1
        steep = rise - (VAULT[d - 1] if d else 0.0) >= 1.0
        plate = f"{IRON_STAIRS}[facing={'east' if x < mid else 'west'},half=bottom]" if steep else IRON
        for z in range(RZ0, RZ1 + 1):
            if _in_tower(x, z):
                continue
            rib = RZ0 < z < RZ1 and (z - RZ0) % BAY == 0 and not (abs(x - mid) <= 1 and m0 <= z <= m1)
            if not (x == mid and m0 < z < m1):
                p.put(x, top, z, IRON if rib else plate)
            if rise > k:
                p.put(x, top + 1, z, IRON if rib else IRON_LOW)
            elif rib and not steep:
                p.put(x, top + 1, z, IRON_LOW)
            if z in (RZ0, RZ1):
                for y in range(base, top):
                    p.put(x, y, z, _lunette(y - base, abs(x - mid)))
    # the monitor: a lantern along the crown, glazed on its long sides between iron posts on the
    # pier lines, under a lid of plates. From the court it is the one line of glass on the flank.
    y = base + int(VAULT[-1])
    for z in range(m0, m1 + 1):
        for x in (mid - 1, mid, mid + 1):
            if z in (m0, m1):
                p.put(x, y, z, IRON)
            elif x != mid:
                p.put(x, y, z, IRON if (z - RZ0) % BAY == 0 else ROOF_GLASS)
            p.put(x, y + 1, z, IRON_LOW)
    for x in range(VX1 + 1, RX1 + 1):
        for z in range(RZ0, RZ1 + 1):
            if not _in_tower(x, z):
                p.put(x, base, z, IRON if RZ0 < z and (z - RZ0) % BAY == 0 else IRON_LOW)


ROOFS = {"a": _roof_a, "b": _roof_b}


# --- the pipe bridge ----------------------------------------------------------------------------------
def _bridge(p, run):
    z = PIPE_Z
    for x in (X0, X0 + 1):
        p.put(x, PIPE_Y, z, IRON)                               # the sleeve through the pier the main comes out of
    for x in range(HEAD_X, X0):
        p.put(x, PIPE_Y, z, IRON if (X0 - x) % JOINT_STEP == 0 else PLATE)
    # the girder under the main: half a block deep where it spans (its underside clears the
    # terrace's railing by half a block), a whole block over the shoe and from post to post of the
    # portal, a haunch on either side of the portal
    for x in range(HEAD_X + 1, X0):
        if x == HEAD_X + 1:
            girder = f"{IRON_STAIRS}[facing=west,half=top]"     # the knee on the down pipe
        elif POSTS_X[0] <= x <= POSTS_X[1]:
            girder = IRON
        elif x == POSTS_X[0] - 1:
            girder = f"{IRON_STAIRS}[facing=east,half=top]"
        elif x == POSTS_X[1] + 1:
            girder = f"{IRON_STAIRS}[facing=west,half=top]"
        else:
            girder = IRON_TOP
        p.put(x, PIPE_Y - 1, z, girder)
        p.put(x, PIPE_Y + 1, z, f"{B.IRON_PIPE}[axis=x]")       # the cable
    p.put(HEAD_X, PIPE_Y + 1, z, IRON_LOW)                      # the cable's box on the elbow
    # the portal in the alley: two posts on stone feet, a lattice of bars under its head beam
    for x in POSTS_X:
        p.put(x, FEET, z, COURSE)
        for y in range(FEET + 1, PIPE_Y - 1):
            p.put(x, y, z, IRON)
    for x in range(POSTS_X[0] + 1, POSTS_X[1]):
        for y in (PIPE_Y - 3, PIPE_Y - 2):
            p.put(x, y, z, B.IRON_BARS)
    # the bridge head on the upper terrace: the main turns down and goes into the ground through a
    # riveted foot on a stone plinth; nothing stands between the down pipe and the terrace's railing
    for x in range(HEAD_X - 1, HEAD_X + 2):
        for row in range(z - 1, z + 2):
            p.put(x, S.GROUND, row, PLINTH)
    p.put(HEAD_X, S.GROUND, z, IRON)
    for y in range(S.GROUND + 1, PIPE_Y):
        p.put(HEAD_X, y, z, PLATE)
    if not run:
        p.put(HEAD_X, S.PAVING_Y, z, IRON)                      # the sleeve where it enters the ground
        for x in COVERS_X:
            p.put(x, S.PAVING_Y, z, IRON)                       # the trench's cover plates, level with the paving
        return
    for x in range(RUN_X[0], RUN_X[1] + 1):
        if CROSSING[0] <= x <= CROSSING[1]:
            p.put(x, S.PAVING_Y, z, IRON)                       # a cover plate, level with the paving
        else:
            p.put(x, S.GROUND, z, IRON if (HEAD_X - x) % (JOINT_STEP + 1) == 0 else PLATE)
    p.put(RUN_X[0] - 1, S.PAVING_Y, z, IRON)                    # and the sleeve before the wall-foot strip


# --- light --------------------------------------------------------------------------------------------
def _light(canvas, origin, version):
    """Hand the windows to the sky line, which gives the glowing ones their light, and offer it the
    source that lays the fire's light on the ground before each of them (pools()). While its kit is
    not in the tree a dim source stands in for it here, as the sky line places its own: in the
    recess before the middle of the glowing rows, never over a block."""
    table = windows(version)
    kit = _other("sky._lightkit")
    glazed = getattr(kit, "glazed", None)
    if glazed is not None:
        glazed(canvas, table, origin, group="power")
        suggest = getattr(kit, "suggest", None)
        for x, y, z in pools(version) if suggest is not None else ():
            suggest(canvas, (origin[0] + x, origin[1] + y, origin[2] + z), POOL_LEVEL, POOL_WHY, rank=2)
        return
    for w in table:
        if w["storey"] != "furnace":
            continue
        x, z = w["cells"][len(w["cells"]) // 2]
        dx, dz = w["inward"]
        y = w["y"][0] + (w["y"][1] - w["y"][0]) // 2
        canvas.set(origin[0] + x - dx, origin[1] + y, origin[2] + z - dz,
                   f"{B.LIGHT}[level={FURNACE_LIGHT}]", keep=True)


def lining(canvas, origin=(0, 0, 0), version=None):
    """The room side of the glowing glass. Lit glass glows on every face, and somebody can stand
    behind these windows; the materials line covers the room side of such a window with a sheet,
    the one that goes with its glass (materials/windows.line: for the fire window night glass, the
    fire is in the room and the window looks out at the night). The sheets are display entities.
    Returns how many were placed: none while that module has no line().

    build() does not call this. In the master scene the materials line lines the two windows
    itself, from windows() (materials/windows.build), and a scene that builds the site line
    without the materials line's models has nothing to show a sheet with (c350, #58341). It is for
    a scene that shows the house by itself and packs those models: this package's test scenes."""
    line = getattr(_other("materials.windows"), "line", None)
    if line is None:
        return 0
    n = 0
    for w in windows(version):
        if w["storey"] == "furnace":
            cells = [(x, y, z) for x, z in w["cells"] for y in range(w["y"][0], w["y"][1] + 1)]
            n += line(canvas, cells, w["inward"], _glow(0), origin=origin)
    return n


def _lamp(canvas, origin):
    """The lamp over the wicket (LAMP_AT), while DOOR_LAMP is on and the props line has its lamps.
    Returns the number of display entities placed."""
    place = getattr(_other("props.lamps"), "place", None) if DOOR_LAMP else None
    if place is None:
        return 0
    return int(place(canvas, LAMP_AT["kind"], LAMP_AT["pos"], facing=LAMP_AT["facing"], origin=origin,
                     version=LAMP_AT["version"]) or 0)


# --- the ventilators ----------------------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def _vent_model():
    """The rotary ventilator, in pixels from the middle of the ridge roll's top; its axis is y."""
    dark, iron, zinc = P.mat("iron_dark"), P.mat("iron", base=4), P.mat("iron", base=5)
    on = (0.0, 0.0)
    m = M.Model(MODEL_VENT)
    m.tube("y", on, 0.0, 1.0, 6.0, dark, sides=12)                      # the flashing on the ridge roll
    m.tube("y", on, 1.0, 6.0, 4.0, dark, sides=12)                      # the spigot
    m.tube("y", on, 6.0, 7.5, VENT_R, iron, sides=12)                   # the drum's throat plate
    m.tube("y", on, 7.5, 18.5, 1.0, dark, sides=4)                      # its spindle
    for k in range(VENT_VANES):                                         # the vanes: sheet zinc
        with m.turned(("y", k * 360.0 / VENT_VANES)):
            m.box((8.0, 7.5, -2.5), (8.5, 18.5, 2.5), zinc, grain="y", seed=7100,
                  rot=("y", VENT_SLANT, (8.25, 13.0, 0.0)))
    m.tube("y", on, 18.5, 20.0, VENT_R, iron, sides=12)                 # the crown, stepped
    m.tube("y", on, 20.0, 21.25, 7.0, iron, sides=12)
    m.tube("y", on, 21.25, 22.25, 3.5, dark)
    m.tube("y", on, 22.25, VENT_TOP, 1.0, dark, sides=4)                # the spindle's nut
    return m


def models():
    """The shell's own display models: the roof's ventilator."""
    return {MODEL_VENT: _vent_model()}


def _vents(canvas, origin, version):
    """The ventilators on the saw roof's ridges (VENTS), each a display entity that turns. Returns
    their number: none on the vault."""
    if version != "a":
        return 0
    model = _vent_model()
    for i, (x, y, z) in enumerate(VENTS):
        canvas.add_entity(origin[0] + x, origin[1] + y, origin[2] + z, M.display(model, view=VIEW))
        MK.spin(canvas, "y", VENT_REV, phase=VENT_BEHIND * (i % 2))     # the south row steps on other ticks
    return len(VENTS)


def build(canvas, origin=(0, 0, 0), version=None, run=None, dress=None):
    """Build the shell at `origin`. version: the roof, "a" or "b" (VERSION when not given);
    run: lay the main along the upper terrace (RUN when not given); dress: place the shell's own
    display models, the roof's ventilators (DRESS when not given: in the master scene only; a
    scene that asks for them packs models()). Returns the number of display entities placed: the
    lamp over the wicket and the ventilators. (The linings of the fire windows are the materials
    line's to place, see lining().)"""
    version = version or VERSION
    if version not in ROOFS:
        raise ValueError(f"no roof version {version!r}; there are {', '.join(sorted(ROOFS))}")
    p = _Pen(canvas, origin)
    canvas.carve(p.o[0] + X0, p.o[1] + FEET, p.o[2] + Z0, p.o[0] + X1, p.o[1] + EAVES + 8, p.o[2] + Z1)
    _walls(p)
    ROOFS[version](p)
    _tower(p)
    _bridge(p, RUN if run is None else run)
    _light(canvas, p.o, version)
    if dress is None:
        dress = DRESS
    if dress is None:
        dress = bool(getattr(canvas, "master", False))
    return _lamp(canvas, p.o) + (_vents(canvas, p.o, version) if dress else 0)
