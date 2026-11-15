"""site/cablecar: the cable station on the north-east corner of the lower platform and the iron
trestle that carries its track down into the cloud (plan/ART-PLAN.md 4, 5.3; card
plan/packages/site/cablecar.md; A0 #171, #304, #442). The player arrives here: the spawn and the
arrival view (S.V1) are on the station platform, at the head of the track.

The arrival view decides the plan (skeleton: V1, V1_CLEAR, V1_COMET). Seen from its eye, between
the two ends of the main building nothing of the station stands above the level of the eye, and
nothing where the comet hangs; the top of the picture and its middle are open sky, and the station
is the picture's edge. So the houses stand in a row along the north edge, the low one west of the
tall one; the glass roof is short, over the car alone, and west of it the platform lies open.

  platform   The station's footprint (S.CABLE_STATION) raised two blocks above the lower platform.
             Its west side and its south side as far as the bay are two steps down to the lower
             platform, so no rail stands on them. A line of polished stone carries the track's axis
             on to the west steps: from the spawn it points at the clock tower and at the comet.
  track      One row (AXIS), the arrival view's own line. The two rails lie flush in the paving,
             the cable slot between them under a grating; a pair of buffer stops ends them. The car
             (machines/cablecar-winch) stands on the last three cells, east of the spawn cell,
             which is kept empty.
  house      The winch house in the north-east corner, tall, its whole south side one opening
             under an iron girder so that the winch is seen from the car; nothing of it comes into
             the arrival view. West of it the waiting room, low and set back a row: it is the right
             edge of the arrival view, its eaves and its ridge running to the foot of the clock
             tower, and it is kept dark on that side (the blinds are down). Its light is in the
             gable, which looks at the observatory. Tuff brick on a polished course, slate roofs.
  glass roof Over the car and the spawn cell only: two iron frames with a glazed screen in each,
             glass between them in two pitches, an iron ridge. It lies between two girders, the
             winch house's and one on two thin columns south of the car; the columns stand east of
             the camera and the girder's end oversails the western one. Its underside is
             S.CANOPY_CLEAR above the platform; seen from S.V1 it lies wholly above the picture.
  bay        The south-east corner stays level, railed, over the head of the trestle.
  trestle    East of the platform the track runs level for a few cells and then falls one in two,
             on iron bents that stand on the ridge the mountain keeps for it (site/_kit.py:
             cable_ridge), a third of a cell north for every cell east. The ridge falls faster than
             the track, so the bents grow; the last ones stand in the cloud and the track ends below
             its top.

What the other lines hang on (cells unless called a point): CAR, WINCH_ROOM, SLOT, SPAWN,
track_axis(x), rail_top(x) for the car and the winch; SIGN, BENCHES, LUGGAGE, WAIT_ROOM for the
props; LAMP_POINTS for the lamps; STEPS for the paths that meet the platform. Blocks only: no
display entities, no models, no light sources.
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
CLOUD = K.ROCK_FLOOR + 5                # -24: the cloud is laid round the legs up to here (sky/cloudsea)


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

# --- the houses along the north edge ------------------------------------------------------------------
# How far west the tall house may come is the arrival view's right edge: a wall whose south face is
# 2.5 north of the eye is out of the picture, at any height, as long as it stays east of x 86.
WINCH = (HEAD - 2, Z0, X1, AXIS - 3)    # x 86..91, z -40..-36: the winch house, walls included
WINCH_TOP = FEET + 6                    # 2: its top wall course; its eaves are at 3, its ridge at 5
WAIT = (WINCH[0] - 6, Z0, WINCH[0] - 1, Z0 + 3)     # x 80..85, z -40..-37: the waiting room; its east
#                                                     wall is the winch house's west wall
WAIT_TOP = FEET + 3                     # -1: its top wall course; its eaves are at 0, its roof's top at 1.5
WINCH_ROOM = dict(box=(WINCH[0] + 1, WINCH[1] + 1, WINCH[2] - 1, WINCH[3] - 1), floor=FEET,
                  ceiling=WINCH_TOP, opening=dict(x=(WINCH[0] + 1, WINCH[2] - 1), z=WINCH[3],
                                                  y=(FEET, FEET + 4)))
WAIT_ROOM = dict(box=(WAIT[0] + 1, WAIT[1] + 1, WAIT[2], WAIT[3] - 1), floor=FEET, ceiling=WAIT_TOP,
                 door=((WAIT[0] + WAIT[2] + 1) // 2, WAIT[3]))      # x 81..85, z -39..-38; the door (83, -37)

# --- the glass roof over the car ------------------------------------------------------------------------
EAVES = FEET + S.CANOPY_CLEAR           # 1: its lowest course, level with the winch house's girder
CANOPY = (HEAD, AXIS - 2, X1, AXIS + 2)             # x 88..91, z -35..-31: the frames and the glass
FRAMES_X = (CANOPY[0], CANOPY[2])       # 88, 91
GIRDER_Z = CANOPY[3] + 1                # -30: the south girder's row
COLUMNS = [(CANOPY[0] + 1, GIRDER_Z), (CANOPY[2], GIRDER_Z)]        # (89, -30), (91, -30): east of the eye
BAY = HEAD - 1                          # 87: from here east the south side is the railed bay

# --- what the props and the lamps hang on (points) --------------------------------------------------------
# the station's name board: on the waiting room's gable, the course over its lit window
SIGN = dict(point=(float(WAIT[0]), WAIT_TOP + 0.5, (WAIT[1] + WAIT[3]) / 2.0 + 0.5), facing="west", width=2)
# benches against the waiting room: under the lit window, where who sits looks at the observatory,
# and at the foot of the front, west of the door (that one is in the corner of the arrival view)
BENCHES = {
    "gable": dict(point=(WAIT[0] - 0.45, float(FEET), (WAIT[1] + WAIT[3]) / 2.0 + 0.5), facing="west"),
    "front": dict(point=(WAIT[0] + 1.5, float(FEET), WAIT[3] + 1.45), facing="south"),
}
# luggage set down by the door, on its east side (out of the arrival view)
LUGGAGE = dict(point=(WAIT[2] - 0.5, float(FEET), WAIT[3] + 1.5))
# Where a lamp hangs (the hanging point, on the underside of the glass roof's ridge): over the west
# end of the car, its door. props/lamps hangs a pendant there (its group "station"); the two cells
# under the point are kept empty for it. It is not in the arrival view, and at level 12 it leaves
# the paving that is in it at 0, the waiting room's front at 1 and the end of its eaves, at the
# picture's edge, at 3. The winch house has no point: the winch brings its own wall lamp
# (machines/cable), on the north wall between the windows.
LAMP_POINTS = {
    "car": (CANOPY[0] + 1.5, float(EAVES + 2), AXIS + 0.5),
}
# the two flights down to the lower platform: the cells of their treads (both rows of each)
STEPS = dict(west=dict(x=(X0, X0 + 1), z=(Z0, Z1)), south=dict(x=(X0 + 1, BAY - 1), z=(Z1 - 1, Z1)))

# --- the occupancy table's roles ----------------------------------------------------------------------
BODY = B.TUFF_BRICK.block
PAVE = B.TUFF_BRICK.block
KERB = B.TUFF_SMOOTH.block              # kerb lines, the axis line, the edge stones beside the car
STEP = B.TUFF_SMOOTH.stairs
WALL = B.TUFF_BRICK.block
COURSE = B.TUFF_SMOOTH.block            # the plinth course, the course under the eaves, the angle piers
CORBEL = B.TUFF_SMOOTH.stairs
ROOF = B.SLATE_TILE.stairs
ROOF_FLAT = B.SLATE_TILE.slab + "[type=bottom]"
IRON = B.IRON_RIVETED.block
IRON_SLAB = B.IRON_RIVETED.slab
IRON_STAIR = B.IRON_RIVETED.stairs
GLASS = B.SKYLIGHT.block
SCREEN = B.SKYLIGHT.pane
GRATE = B.IRON_GRATE
BARS = B.IRON_BARS
PIPE = B.IRON_PIPE + "[axis=y]"
POST = B.TUFF_SMOOTH.wall
FINIAL = B.IRON_ROD + "[facing=up]"
TIE = B.IRON_HATCH + "[half=top]"
DOOR = B.IRON_DOOR
LIT = B.WINDOW_FROSTED.pane
WARM = B.WINDOW_CURTAIN.pane
DARK = B.WINDOW_DARK.pane
SHUT = B.WINDOW_BLIND.pane
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
    """Two courses over the whole footprint, the upper one paved; two steps down along the west
    side and along the south side as far as the bay; the east face down to the rock."""
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            p.set(x, LOW, z, BODY)
            p.set(x, TOP, z, PAVE)
    for z in range(Z0, Z1 + 1):                 # the east face stands one course deeper: the rock
        p.set(X1, S.LOWER_PAVING_Y, z, BODY)    # east of it is a block below the lower paving
    for z in range(Z0, Z1 + 1):                 # west: the lower step, then the upper
        p.set(X0, LOW, z, STEP + "[facing=east]")
        p.clear(X0, TOP, z)
        p.set(X0 + 1, TOP, z, STEP + "[facing=east]")
    for x in range(X0 + 1, BAY):                # south
        p.set(x, LOW, Z1, STEP + "[facing=north]")
        p.clear(x, TOP, Z1)
        if x > X0 + 1:
            p.set(x, TOP, Z1 - 1, STEP + "[facing=north]")
    for z in range(Z0, Z1 - 1):                 # a kerb line behind the head of each flight
        p.set(X0 + 2, TOP, z, KERB)
    for x in range(X0 + 2, BAY):
        p.set(x, TOP, Z1 - 2, KERB)
    for x in range(X0 + 3, HEAD):               # the track's axis, carried on to the west steps
        p.set(x, TOP, AXIS, KERB)
    for x in range(HEAD, X1 + 1):               # an edge stone along either side of the car
        for z in (CANOPY[1], CANOPY[3]):
            p.set(x, TOP, z, KERB)
    # the hill's railing: the north edge west of the waiting room; the bay's south side and its east
    # side as far as the column; the east edge either side of the track
    north = [(x, Z0) for x in range(X0 + 2, WAIT[0])]
    K.rail(p.c, p.o, north, north[:1], y=FEET, kerb=False)
    bay = [(x, Z1) for x in range(BAY, X1)] + [(X1, z) for z in range(Z1, GIRDER_Z, -1)]
    K.rail(p.c, p.o, bay, [(BAY, Z1), (X1, Z1)], y=FEET, kerb=False)
    for z in (CANOPY[1], CANOPY[3]):
        K.rail(p.c, p.o, [(X1, z)], [], y=FEET, kerb=False)


def _track(p):
    """The rails in the paving, the grating over the cable between them, the buffer stops."""
    for x in range(HEAD, X1 + 1):
        p.set(x, TOP, AXIS - 1, IRON)
        p.set(x, TOP, AXIS + 1, IRON)
        p.set(x, TOP, AXIS, GRATE)
    for z in (AXIS - 1, AXIS + 1):      # upright towards the car, braced behind
        p.set(HEAD - 1, FEET, z, IRON_STAIR + "[facing=east]")


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


def _gable_roof(p, box, y, gables=None):
    """A slate roof of two pitches over a box, the ridge east-west; the eaves course is y. The gable
    walls (at the x of `gables`, both ends by default) are filled under it."""
    x0, z0, x1, z1 = box
    half = (z1 - z0) // 2
    gables = (x0, x1) if gables is None else gables
    for x in range(x0, x1 + 1):
        for i in range(half):
            p.set(x, y + i, z0 + i, ROOF + "[facing=south]")
            p.set(x, y + i, z1 - i, ROOF + "[facing=north]")
            if x in gables:
                for z in range(z0 + i + 1, z1 - i):
                    p.set(x, y + i, z, WALL)
        for z in range(z0 + half, z1 - half + 1):
            p.set(x, y + half, z, ROOF_FLAT)


def _window(p, cells, y0, y1, glass):
    for x, z in cells:
        for y in range(y0, y1 + 1):
            p.set(x, y, z, glass)


def _winch_house(p):
    x0, z0, x1, z1 = WINCH
    mid = (z0 + z1) // 2
    _shell(p, WINCH, FEET, WINCH_TOP)
    # the south side is one opening between the angle piers, under an iron girder on two corbels:
    # the winch shows
    ox0, ox1 = WINCH_ROOM["opening"]["x"]
    oy0, oy1 = WINCH_ROOM["opening"]["y"]
    for x in range(ox0, ox1 + 1):
        for y in range(oy0, oy1 + 1):
            p.clear(x, y, z1)
        p.set(x, oy1 + 1, z1, IRON)
    p.set(ox0, oy1, z1, CORBEL + "[half=top,facing=west]")
    p.set(ox1, oy1, z1, CORBEL + "[half=top,facing=east]")
    # two tall lit lights in the east wall, over the cliff; two dark ones in the north wall, either
    # side of the two columns of brick the winch's wall lamp hangs on (machines/cable)
    _window(p, [(x1, z0 + 1), (x1, z1 - 1)], FEET + 1, FEET + 4, LIT)
    _window(p, [(x0 + 1, z0), (x1 - 1, z0)], FEET + 2, FEET + 4, DARK)
    _gable_roof(p, WINCH, WINCH_TOP + 1)
    # the west gable shows over the waiting room's roof: a lit light in it, an apex stone and a rod
    _window(p, [(x0, mid)], WINCH_TOP + 1, WINCH_TOP + 1, WARM)
    p.set(x0, WINCH_TOP + 3, mid, COURSE)
    p.set(x0, WINCH_TOP + 4, mid, FINIAL)


def _waiting_room(p):
    """Built before the winch house, whose west wall closes its east end."""
    x0, z0, x1, z1 = WAIT
    door = WAIT_ROOM["door"][0]
    _shell(p, (x0, z0, x1 + 1, z1), FEET, WAIT_TOP)
    # the front, which the arrival view sees: a door set back between two piers under a dark
    # fanlight, a window either side with its blind down, all three heads under the top course.
    # Nothing lit.
    p.set(door, FEET, z1, DOOR + "[half=lower,facing=south,hinge=left]")
    p.set(door, FEET + 1, z1, DOOR + "[half=upper,facing=south,hinge=left]")
    p.set(door, FEET + 2, z1, DARK)
    _window(p, [(door - 2, z1), (door + 2, z1)], FEET + 1, FEET + 2, SHUT)
    # the gable, which looks at the observatory: the lit window, under the name board's course
    _window(p, [(x0, z) for z in range(z0 + 1, z1)], FEET + 1, FEET + 2, LIT)
    _window(p, [(door - 1, z0), (door + 1, z0)], FEET + 1, FEET + 2, DARK)      # the back
    _gable_roof(p, WAIT, WAIT_TOP + 1, gables=(x0,))


def _glass_roof(p):
    """Two iron frames (the stepped rafters of a gable, a glazed screen under them), glass in two
    pitches between them, an iron ridge: each pitch is one light with iron all round it, the frames
    at its ends, the ridge above and a girder at its foot. The north girder is the winch house's;
    the south one lies on two thin columns and tapers where it oversails the western one."""
    x0, z0, x1, z1 = CANOPY
    half = (z1 - z0) // 2
    for x in range(x0, x1 + 1):
        frame = x in FRAMES_X
        for i in range(half):
            p.set(x, EAVES + i, z0 + i, IRON_STAIR + "[facing=south]" if frame else GLASS)
            p.set(x, EAVES + i, z1 - i, IRON_STAIR + "[facing=north]" if frame else GLASS)
            if frame:
                for z in range(z0 + i + 1, z1 - i):
                    p.set(x, EAVES + i, z, SCREEN)
        p.set(x, EAVES + half, z0 + half, IRON_SLAB + "[type=bottom]")
        p.set(x, EAVES, GIRDER_Z, IRON if x > x0 else IRON_STAIR + "[half=top,facing=east]")
    for x, z in COLUMNS:
        p.set(x, FEET, z, POST)
        for y in range(FEET + 1, EAVES):
            p.set(x, y, z, PIPE)


def _slab(h):
    """The cell and the half of it whose upper face is at height h."""
    if h == int(h):
        return int(h) - 1, "top"
    return int(h // 1), "bottom"


def _trestle(p):
    """Two rails of riveted slabs with a tie in every second cell, on bents: a cap girder across,
    two legs on footings on the ridge (or down into the cloud), bars and struts between the legs.
    In the cloud the legs stand bare but for the struts: bars would reach out into it."""
    for x in range(X1 + 1, END + 1):
        z = track_axis(x)
        y, half = _slab(rail_top(x))
        for dz in (-1, 1):
            p.set(x, y, z + dz, IRON_SLAB + f"[type={half}]")
        if half == "top":
            p.set(x, y, z, TIE)
    x = X1 + 1                                  # the abutment: masonry from the rock to the rails
    for y in range(K.cable_ridge(x)[1] + 1, TOP):
        for dz in (-1, 0, 1):
            p.set(x, y, track_axis(x) + dz, FOOTING)
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
                if (cap - yy) % 3 == 0:
                    p.set(x, yy, z, IRON_SLAB + "[type=top]")
                elif yy > CLOUD:
                    p.set(x, yy, z, BARS)


def build(canvas, origin=(0, 0, 0)):
    p = _Pen(canvas, origin)
    _platform(p)
    _track(p)
    _waiting_room(p)
    _winch_house(p)
    _glass_roof(p)
    _trestle(p)
    for y in (FEET, FEET + 1):          # the spawn cell stays empty
        p.clear(HEAD, y, AXIS)
    return 0
