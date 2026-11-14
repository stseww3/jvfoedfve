"""site/cablecar: the cable station on the north-east corner of the lower platform and the iron
trestle that carries its track down into the cloud (plan/ART-PLAN.md 4, 5.3; card
plan/packages/site/cablecar.md; A0 #171, #19629). The player arrives here: the spawn and the
arrival view (S.V1) are on the station platform, at the head of the track.

  platform   The station's footprint (S.CABLE_STATION) raised two blocks above the lower platform.
             Its west and south sides are two steps down to the lower platform, all the way along:
             the arrival view looks out over them to the west and south-west, so nothing stands on
             those edges, no rail and no post.
  track      One row (AXIS) on the arrival view's own line. In the station the two rails lie flush
             in the paving, the cable slot between them under a grating; a pair of buffer stops
             ends them. The car (machines/cablecar-winch) stands on the last three cells, east of
             the spawn cell, which is kept empty.
  house      Along the north edge, where it stays out of the arrival view: the winch house (east,
             tall, its whole south side open to the track so the winch is seen) and the waiting
             room (west, low). Tuff brick on a polished course, slate roofs.
  canopy     Iron ribs and glass, level with the winch house's eaves, over the car and the head of
             the track. It hangs on the winch house and on two thin columns south of the camera;
             its west and south-west stay open. Seen from S.V1 it lies wholly above the picture.
  trestle    East of the platform the track runs level for a few cells and then falls one in two,
             on iron bents that stand on the ridge the mountain keeps for it (site/_kit.py:
             cable_ridge), a third of a cell north for every cell east. The ridge falls faster than
             the track, so the bents grow; the last ones stand in the cloud and the track ends below
             its top.

What the other lines hang on (cells unless called a point): CAR, WINCH_ROOM, SLOT, SIGN, SPAWN,
track_axis(x), rail_top(x). Blocks only: no display entities, no models, no light sources.
"""
from ..common import blocks as B
from ..common import skeleton as S
from . import _kit as K

ORDER = 55      # after the terrain (10), the lower platform's floor (20) and the stair (25)

X0, Z0, X1, Z1 = S.CABLE_STATION        # x 75..91, z -40..-26
LOW = S.LOWER_GROUND                    # -6: feet on the lower platform; the lower of the two courses
FEET = S.STATION_GROUND                 # -4: feet on the station platform
TOP = FEET - 1                          # -5: the platform's paving course

# --- the track ------------------------------------------------------------------------------------
AXIS = K.CABLE_RIDGE_Z                  # -33: the row of the track's axis; S.V1 stands in it
HEAD = int(S.V1["pos"][0])              # 88: the last cell of the track, the spawn cell
CAR = dict(box=(HEAD + 1, AXIS - 1, X1, AXIS + 1), floor=FEET)      # x 89..91, z -34..-32
SPAWN = (HEAD + 0.5, float(FEET), AXIS + 0.5)                       # a point: (88.5, -4, -32.5)
SLOT = dict(cells=[(x, AXIS) for x in range(HEAD, X1 + 1)], y=TOP)  # the grating over the cable
LEVEL = 4                               # cells of level track east of the platform
GRADE = 0.5                             # then half a block down with every cell
BENT_FIRST, BENT_STEP = X1 + 7, 6       # x 98, 104 ..: the middle cell of every second straight run
SINK = K.ROCK_FLOOR + 2                 # -27: the track ends when its rails are this low, under the cloud


def track_axis(x):
    """The row of the track's axis in column x: AXIS in the station, then the ridge's own line
    (K.cable_ridge), carried on past the ridge's end."""
    if x <= X1:
        return AXIS
    return int(round(AXIS - (x - K.CABLE_RIDGE_X[0]) / 3.0))


def rail_top(x):
    """y of the upper face of the rails in column x (a point coordinate, in half blocks)."""
    return FEET - GRADE * max(0, x - X1 - LEVEL)


END = next(x for x in range(X1 + 1, X1 + 200) if rail_top(x) <= SINK)      # 141: the last column
BENTS = list(range(BENT_FIRST, END, BENT_STEP))

# --- the house --------------------------------------------------------------------------------------
HZ0 = Z0                                # -40: the north wall of both rooms
WINCH = (X1 - 6, HZ0, X1, HZ0 + 4)      # x 85..91, z -40..-36: the winch house, walls included
WINCH_TOP = FEET + 6                    # 2: its top wall course; the eaves and the canopy are at 3
WAIT = (WINCH[0] - 6, HZ0, WINCH[0] - 1, HZ0 + 3)   # x 79..84, z -40..-37: the waiting room
WAIT_TOP = FEET + 3                     # -1: its top wall course; the eaves are at 0
WINCH_ROOM = dict(box=(WINCH[0] + 1, WINCH[1] + 1, WINCH[2] - 1, WINCH[3] - 1), floor=FEET,
                  ceiling=WINCH_TOP, opening=dict(x=(WINCH[0] + 1, WINCH[2] - 1), z=WINCH[3],
                                                  y=(FEET, FEET + 4)))

# --- the canopy -------------------------------------------------------------------------------------
CANOPY_Y = WINCH_TOP + 1                # 3: the cells of the canopy; its underside is 7 above the platform
CANOPY = (WINCH[0], WINCH[3] + 1, X1, AXIS + 3)     # x 85..91, z -35..-30
RIBS_X = (CANOPY[0], (CANOPY[0] + CANOPY[2]) // 2, CANOPY[2])       # 85, 88, 91
RIBS_Z = (AXIS, CANOPY[3])              # -33 over the track's axis, -30 the south edge
COLUMNS = [(RIBS_X[1], CANOPY[3]), (RIBS_X[2], CANOPY[3])]          # (88, -30), (91, -30)
# where the station's name board hangs: under the canopy's west rib, over the way to the car
SIGN = dict(point=(CANOPY[0] + 0.5, float(CANOPY_Y), AXIS + 0.5), facing="west")

# --- the occupancy table's roles ----------------------------------------------------------------------
BODY = B.TUFF_BRICK.block
PAVE = B.TUFF_BRICK.block
KERB = B.TUFF_SMOOTH.block
STEP = B.TUFF_SMOOTH.stairs
WALL = B.TUFF_BRICK.block
COURSE = B.TUFF_SMOOTH.block            # the plinth course, the course under the eaves, the angle piers
ARCH = B.TUFF_BRICK.stairs
ROOF = B.SLATE_TILE.stairs
ROOF_FLAT = B.SLATE_TILE.slab + "[type=bottom]"
RIDGE = B.VERDIGRIS_CUT.slab + "[type=bottom]"
IRON = B.IRON_RIVETED.block
IRON_SLAB = B.IRON_RIVETED.slab
IRON_STAIR = B.IRON_RIVETED.stairs
GLASS = B.SKYLIGHT.block
GRATE = B.IRON_GRATE
BARS = B.IRON_BARS
PIPE = B.IRON_PIPE + "[axis=y]"
TIE = B.IRON_HATCH + "[half=top]"
DOOR = B.IRON_DOOR
LIT = B.WINDOW_FROSTED.pane
WARM = B.WINDOW_CURTAIN.pane
DARK = B.WINDOW_DARK.pane
FOOTING = B.TUFF_BRICK.block


class _Pen:
    """The canvas with the origin added."""

    def __init__(self, canvas, origin):
        self.c, self.o = canvas, origin

    def set(self, x, y, z, state):
        self.c.set(self.o[0] + x, self.o[1] + y, self.o[2] + z, state)

    def clear(self, x, y, z):
        self.c.clear(self.o[0] + x, self.o[1] + y, self.o[2] + z)


def _platform(p):
    """Two courses over the whole footprint, the upper one paved; two steps down along the west and
    the south side; the east face down to the rock."""
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            p.set(x, LOW, z, BODY)
            p.set(x, TOP, z, PAVE)
    for z in range(Z0, Z1 + 1):                 # the east face stands one course deeper: the rock
        p.set(X1, S.LOWER_PAVING_Y, z, BODY)    # east of it is a block below the lower paving
    bay = X1 - 4                                # the south-east corner stays level: a bay over the trestle
    for z in range(Z0, Z1 + 1):                 # west: the lower step, then the upper
        p.set(X0, LOW, z, STEP + "[facing=east]")
        p.clear(X0, TOP, z)
        p.set(X0 + 1, TOP, z, STEP + "[facing=east]")
    for x in range(X0 + 1, bay):                # south
        p.set(x, LOW, Z1, STEP + "[facing=north]")
        p.clear(x, TOP, Z1)
        if x > X0 + 1:
            p.set(x, TOP, Z1 - 1, STEP + "[facing=north]")
    p.clear(X0 + 1, TOP, Z1)
    for z in range(Z0, Z1 - 1):                 # a kerb line behind the head of each flight
        p.set(X0 + 2, TOP, z, KERB)
    for x in range(X0 + 2, bay):
        p.set(x, TOP, Z1 - 2, KERB)
    # the bay's rail and the east edge south of the track; the two cells north of the track
    edge = [(x, Z1) for x in range(bay, X1)] + [(X1, z) for z in range(Z1, AXIS + 1, -1)]
    K.rail(p.c, p.o, edge, [(bay, Z1), (X1, Z1), (X1, AXIS + 2)], y=FEET, kerb=False)
    K.rail(p.c, p.o, [(X1, AXIS - 2)], [], y=FEET, kerb=False)
    K.rail(p.c, p.o, [(x, Z0) for x in range(X0 + 2, WAIT[0])], [], y=FEET, kerb=False)


def _track(p):
    """The rails in the paving, the grating over the cable between them, the buffer stops."""
    for x in range(HEAD, X1 + 1):
        p.set(x, TOP, AXIS - 1, IRON)
        p.set(x, TOP, AXIS + 1, IRON)
        p.set(x, TOP, AXIS, GRATE)
    for z in (AXIS - 1, AXIS + 1):
        p.set(HEAD - 1, FEET, z, IRON_STAIR + "[facing=west]")


def _shell(p, box, y0, y1):
    """Four walls: a polished course at the foot and at the top, polished angle piers, brick between."""
    x0, z0, x1, z1 = box
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if x not in (x0, x1) and z not in (z0, z1):
                continue
            corner = x in (x0, x1) and z in (z0, z1)
            for y in range(y0, y1 + 1):
                p.set(x, y, z, COURSE if corner or y in (y0, y1) else WALL)


def _gable_roof(p, box, y, ridge):
    """A roof of two pitches over a box, the ridge east-west; the eaves course is y. The gable
    walls are filled under it."""
    x0, z0, x1, z1 = box
    half = (z1 - z0) // 2
    for x in range(x0, x1 + 1):
        for i in range(half):
            p.set(x, y + i, z0 + i, ROOF + "[facing=south]")
            p.set(x, y + i, z1 - i, ROOF + "[facing=north]")
            if x in (x0, x1):
                for z in range(z0 + i + 1, z1 - i):
                    p.set(x, y + i, z, WALL)
        for z in range(z0 + half, z1 - half + 1):
            p.set(x, y + half, z, ridge)


def _window(p, cells, y0, y1, glass):
    for x, z in cells:
        for y in range(y0, y1 + 1):
            p.set(x, y, z, glass)


def _winch_house(p):
    x0, z0, x1, z1 = WINCH
    _shell(p, WINCH, FEET, WINCH_TOP)
    # the south side is one opening between the angle piers, under an iron girder: the winch shows
    ox0, ox1 = WINCH_ROOM["opening"]["x"]
    oy0, oy1 = WINCH_ROOM["opening"]["y"]
    for x in range(ox0, ox1 + 1):
        for y in range(oy0, oy1 + 1):
            p.clear(x, y, z1)
        p.set(x, oy1 + 1, z1, IRON)
    p.set(ox0, oy1, z1, ARCH + "[half=top,facing=west]")
    p.set(ox1, oy1, z1, ARCH + "[half=top,facing=east]")
    # two tall lights in the east wall, two in the north wall, one in the west gable over the waiting room
    _window(p, [(x1, z0 + 1), (x1, z1 - 1)], FEET + 1, FEET + 4, DARK)
    _window(p, [(x0 + 2, z0), (x1 - 2, z0)], FEET + 2, FEET + 4, DARK)
    _gable_roof(p, WINCH, WINCH_TOP + 1, RIDGE)
    _window(p, [(x0, (z0 + z1) // 2)], WINCH_TOP + 1, WINCH_TOP + 1, DARK)


def _waiting_room(p):
    """Built before the winch house, whose west wall closes its east end."""
    x0, z0, x1, z1 = WAIT
    _shell(p, (x0, z0, x1 + 1, z1), FEET, WAIT_TOP)
    # the platform front: window, double door under a fanlight, window
    mid = (x0 + x1) // 2
    for x, hinge in ((mid, "left"), (mid + 1, "right")):
        p.set(x, FEET, z1, DOOR + f"[half=lower,facing=north,hinge={hinge}]")
        p.set(x, FEET + 1, z1, DOOR + f"[half=upper,facing=north,hinge={hinge}]")
        p.set(x, FEET + 2, z1, LIT)
    _window(p, [(mid - 1, z1), (mid + 2, z1)], FEET + 1, FEET + 2, LIT)
    _window(p, [(x0, z0 + 1), (x0, z1 - 1)], FEET + 1, FEET + 2, WARM)      # the west end
    _window(p, [(mid - 1, z0), (mid + 2, z0)], FEET + 1, FEET + 2, DARK)    # the back
    _gable_roof(p, WAIT, WAIT_TOP + 1, ROOF_FLAT)


def _canopy(p):
    """A square grid of iron ribs with glass in it, at the eaves of the winch house; brackets under
    the ribs at the wall, two thin columns with brackets under the south edge."""
    x0, z0, x1, z1 = CANOPY
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            rib = x in RIBS_X or z in RIBS_Z
            p.set(x, CANOPY_Y, z, IRON_SLAB + "[type=bottom]" if rib else GLASS)
    for x in RIBS_X:
        p.set(x, CANOPY_Y - 1, z0, IRON_STAIR + "[half=top,facing=north]")
    for x, z in COLUMNS:
        p.set(x, FEET, z, B.TUFF_SMOOTH.wall)
        for y in range(FEET + 1, CANOPY_Y):
            p.set(x, y, z, PIPE)
        for dx, facing in ((-1, "east"), (1, "west")):
            if x0 <= x + dx <= x1:
                p.set(x + dx, CANOPY_Y - 1, z, IRON_STAIR + f"[half=top,facing={facing}]")


def _slab(h):
    """The cell and the half of it whose upper face is at height h."""
    if h == int(h):
        return int(h) - 1, "top"
    return int(h // 1), "bottom"


def _trestle(p):
    """Two rails of riveted slabs with a tie in every second cell, on bents: a cap girder across,
    two legs on footings on the ridge (or down into the cloud), bars and struts between the legs."""
    for x in range(X1 + 1, END + 1):
        z = track_axis(x)
        y, half = _slab(rail_top(x))
        for dz in (-1, 1):
            p.set(x, y, z + dz, IRON_SLAB + f"[type={half}]")
        if half == "top":
            p.set(x, y, z, TIE)
    for x in BENTS:
        z = track_axis(x)
        y, half = _slab(rail_top(x))
        cap = y - 1 if half == "bottom" else y
        ridge = K.cable_ridge(x)
        foot = ridge[1] + 1 if ridge else K.ROCK_FLOOR
        for dz in (-1, 0, 1):
            p.set(x, cap, z + dz, IRON)
        for yy in range(cap - 1, foot - 1, -1):
            for dz in (-1, 1):
                p.set(x, yy, z + dz, FOOTING if ridge and yy == foot else IRON)
            if yy > foot:
                strut = (cap - yy) % 3 == 0
                p.set(x, yy, z, IRON_SLAB + "[type=top]" if strut else BARS)


def build(canvas, origin=(0, 0, 0)):
    p = _Pen(canvas, origin)
    _platform(p)
    _track(p)
    _waiting_room(p)
    _winch_house(p)
    _canopy(p)
    _trestle(p)
    for y in (FEET, FEET + 1):          # the spawn cell stays empty
        p.clear(HEAD, y, AXIS)
    return 0
