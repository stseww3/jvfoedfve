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
             tower, and it is kept dark on that side (the blinds are down, the door is shut: the
             room is a shell and nobody goes in). Tuff brick on a polished course, slate roofs; a
             chimney stands in the waiting room's back wall, out of the arrival view.
  windows    Three are lit, all of frosted glass and none of them towards the arrival view: the
             waiting room's gable window, which looks at the observatory, and two tall lights in
             the winch house's east wall, over the cliff. windows() lists the glass of both
             houses; the sky line gives the lit ones their light (sky/_lightkit.glazed). The two
             tall lights are whole blocks, flush with the wall: their room side is seen from the
             platform through the opening, and the materials line covers it with the sheet that
             shows frosted glass with the night behind it (materials/windows.line). The waiting
             room's front is walled up behind its blinds and its door, so that no light of the
             room gets out on the side the arrival view sees, wherever its source stands.
  glass roof Over the car and the spawn cell only: two iron trusses (stepped rafters and a tie
             rod, the gable open), glass between them in two pitches, an iron ridge. Who arrives
             walks out under the western truss. It lies between two girders, the winch house's
             and one on two slender columns south of the car: a stone base, a shaft, a cast
             bearing block in the girder. The columns stand east of the camera and the girder's
             end oversails the western one. Its underside is S.CANOPY_CLEAR above the platform;
             seen from S.V1 it lies wholly above the picture.
  bay        The south-east corner stays level, railed, over the head of the trestle.
  trestle    East of the platform the track runs level for a few cells and then falls one in two,
             a thin deck on lattice towers that stand on the ridge the mountain keeps for it
             (site/_kit.py: cable_ridge), a third of a cell north for every cell east. The ridge
             falls faster than the track, so the towers grow; the last ones stand in the cloud and
             the track ends below its top.

What the other lines hang on (cells unless called a point): CAR, WINCH_ROOM, SLOT, SPAWN,
track_axis(x), rail_top(x) for the car and the winch; SIGN, BENCHES, LUGGAGE for the props;
LAMP_POINTS for the lamps; windows() for the light; SMOKE for the motion line; STEPS for the paths
that meet the platform. The package sets blocks and has no models and no light sources of its
own. build() returns the display entities placed for it: the sheets on the room side of the
winch house's two lights.
"""
import importlib

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
TOWER_FIRST, TOWER_STEP = X1 + 7, 6     # x 98, 104 ..: a tower under the last two cells of every second
#                                         straight run, this column and the next
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


def _slab(h):
    """The cell and the half of it whose upper face is at height h."""
    if h == int(h):
        return int(h) - 1, "top"
    return int(h // 1), "bottom"


END = next(x for x in range(X1 + 1, X1 + 200) if rail_top(x) <= SINK)      # 141: the last column
# A tower stands where its bearers, the course under its first column's rails, are above the cloud:
# x 98 .. 128. Past the last one the deck goes down into the cloud alone.
TOWERS = [x for x in range(TOWER_FIRST, END, TOWER_STEP) if _slab(rail_top(x))[0] - 1 > CLOUD]

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
# the waiting room's chimney, in its back wall behind the door: the cell, its lowest and its highest
# course (the pot), and the middle of the pot's mouth (a point)
STACK = dict(cell=(WAIT_ROOM["door"][0], WAIT[1]), y=(WAIT_TOP + 1, WAIT_TOP + 4))      # (83, -40), y 0..3
SMOKE = (STACK["cell"][0] + 0.5, STACK["y"][1] + 1.0, STACK["cell"][1] + 0.5)           # (83.5, 4.0, -39.5)

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
GRATE = B.IRON_GRATE
BARS = B.IRON_BARS
PIPE = B.IRON_PIPE + "[axis=y]"         # a tower's legs in the cloud
# A column's shaft is a wall post of dark slate. The iron of the table is whole blocks, stairs and
# slabs, or bars, pipe and rod two and three pixels thick: four courses of those read as a wire, not
# as what carries a girder. The post is half a block thick and of the roofs' stone, dark as the iron.
SHAFT = B.SLATE_SMOOTH.wall
CAPITAL = B.IRON_CAST                   # the bearing block over a column, in the girder's course
ROD = B.IRON_ROD                        # a truss's tie
FINIAL = ROD + "[facing=up]"
POT = B.SLATE_SMOOTH.wall               # the chimney's pot
TIE = B.IRON_HATCH + "[half=top]"
DOOR = B.IRON_DOOR
LIT = B.WINDOW_FROSTED                  # the lit glass: panes in the waiting room's gable, whole blocks in
#                                         the winch house's east wall (a lining lies on a block's face)
DARK = B.WINDOW_DARK.pane
SHUT = B.WINDOW_BLIND.pane
FOOTING = B.TUFF_BRICK.block


def windows():
    """The glass of the two houses, as records sky/_lightkit.glazed() takes: front, bay (the cell
    the window stands in along its wall; the first one of a wider window), storey, cells (the glass
    columns (x, z)), inward (the step from the glass into the house), y (the bottom and the top row
    of the glass). Two keys more for this package: glass, what stands in the window, and lined,
    set where the room side of the glass is seen (the winch room is open to the platform) and
    takes a lining. None of the kit's own keys is set: no window asks for a level of its own.
    Where the source of a lit window stands, behind the glass or before it, is the kit's to say;
    the waiting room is built so that either way its light stays off the front the arrival view
    sees (_waiting_room).

    Lit are the waiting room's gable window and the two lights of the winch house's east wall, a
    pier between them. Everything on the front the arrival view sees is dark: two windows with
    their blinds down and the light over the door."""
    wx0, wz0, _, wz1 = WAIT
    hx0, hz0, hx1, hz1 = WINCH
    door = WAIT_ROOM["door"][0]
    mid = (hz0 + hz1) // 2
    low = (FEET + 1, FEET + 2)              # the waiting room's windows: two rows over the plinth course
    tall = (FEET + 1, FEET + 4)             # the lights of the winch house's east wall
    high = (FEET + 2, FEET + 4)             # the windows of its north wall
    over = (FEET + 2, FEET + 2)             # the light over the door
    apex = (WINCH_TOP + 1, WINCH_TOP + 1)

    def window(front, bay, cells, inward, y, glass, storey="main", **more):
        return dict(front=f"station.{front}", bay=bay, storey=storey, cells=cells, inward=inward, y=y,
                    glass=glass, **more)

    return [
        # the waiting room: the lit window in its gable; its front, all dark; its back
        window("west", wz0 + 1, [(wx0, z) for z in range(wz0 + 1, wz1)], (1, 0), low, LIT.pane),
        window("south", door - 2, [(door - 2, wz1)], (0, -1), low, SHUT),
        window("south", door, [(door, wz1)], (0, -1), over, DARK),
        window("south", door + 2, [(door + 2, wz1)], (0, -1), low, SHUT),
        window("north", door - 1, [(door - 1, wz0)], (0, 1), low, DARK),
        window("north", door + 1, [(door + 1, wz0)], (0, 1), low, DARK),
        # the winch house: the two lights of its east wall; the north wall's two windows, either
        # side of the two columns of brick the winch's wall lamp hangs on (machines/cable); a small
        # one in the west gable, which shows over the waiting room's roof
        window("east", hz0 + 1, [(hx1, hz0 + 1)], (-1, 0), tall, LIT.block, lined=True),
        window("east", hz1 - 1, [(hx1, hz1 - 1)], (-1, 0), tall, LIT.block, lined=True),
        window("north", hx0 + 1, [(hx0 + 1, hz0)], (0, 1), high, DARK),
        window("north", hx1 - 1, [(hx1 - 1, hz0)], (0, 1), high, DARK),
        window("west", mid, [(hx0, mid)], (1, 0), apex, DARK, storey="gable"),
    ]


def _other(path):
    """A module of another line ("sky._lightkit"); None while it is not in the tree."""
    full = f"{__package__.rpartition('.')[0]}.{path}"
    try:
        return importlib.import_module(full)
    except ModuleNotFoundError as e:
        if not e.name or not f"{full}.".startswith(f"{e.name}."):
            raise               # it is there and cannot import something of its own: say so
        return None


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


def _winch_house(p):
    """The glass of its windows is set by _glaze: two tall lights in the east wall, two dark
    windows in the north wall, a small dark one in the west gable."""
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
    _gable_roof(p, WINCH, WINCH_TOP + 1)
    # the west gable shows over the waiting room's roof: an apex stone and a rod
    p.set(x0, WINCH_TOP + 3, mid, COURSE)
    p.set(x0, WINCH_TOP + 4, mid, FINIAL)


def _waiting_room(p):
    """Built before the winch house, whose west wall closes its east end. The front, which the
    arrival view sees: a door set back between two piers under a dark light, a window either
    side with its blind down, all three heads under the top course; nothing lit. The door is
    shut: a wall with a door's face, and nobody goes in. The gable, which looks at the
    observatory, has the lit window under the name board's course (_glaze sets the glass).

    Glass panes and a door let light through. The row behind the front is therefore walled up
    where the front has an opening: behind the two blinds, behind the door and the light over
    it. Whatever lights the gable window from within, a source behind its glass or a lamp one
    day, none of it reaches the side the arrival view sees; the blinds and the door look the
    same, nothing shows through them.

    The chimney stands in the back wall, on the door's axis: two courses of brick through the
    eaves, a polished cap, a pot. From the arrival view it is out of the picture, north of the
    comet's part of the sky; from the upper terrace it tells the low roof apart as a house."""
    x0, z0, x1, z1 = WAIT
    door = WAIT_ROOM["door"][0]
    _shell(p, (x0, z0, x1 + 1, z1), FEET, WAIT_TOP)
    p.set(door, FEET, z1, DOOR + "[half=lower,facing=south,hinge=left]")
    p.set(door, FEET + 1, z1, DOOR + "[half=upper,facing=south,hinge=left]")
    for w in windows():
        if w["front"] == "station.south":       # the waiting room's: the winch house's south side is open
            dx, dz = w["inward"]
            for x, z in w["cells"]:
                for y in range(FEET if x == door else w["y"][0], w["y"][1] + 1):
                    p.set(x + dx, y, z + dz, WALL)
    _gable_roof(p, WAIT, WAIT_TOP + 1, gables=(x0,))
    sx, sz = STACK["cell"]
    low, top = STACK["y"]
    for y in range(low, top + 1):
        p.set(sx, y, sz, POT if y == top else COURSE if y == top - 1 else WALL)


def _glaze(p):
    """The glass of windows(), when the walls and the gables stand."""
    for w in windows():
        for x, z in w["cells"]:
            for y in range(w["y"][0], w["y"][1] + 1):
                p.set(x, y, z, w["glass"])


def _glass_roof(p):
    """Two iron frames, glass in two pitches between them, an iron ridge: each pitch is one light
    with iron all round it, the frames at its ends, the ridge above and a girder at its foot. A
    frame is a truss: the stepped rafters of a gable and a tie rod from foot to foot, at half the
    height of the eaves course (the girders' underside stays the lowest of the roof); the gable
    over the rod is open. The rod's three pieces turn their heads to the rafters' feet and to
    one joint between them: two shoes and a coupling. The north girder is the winch house's; the
    south one lies on two columns and tapers where it oversails the western one. A column is a
    base stone, a slender shaft, and in the girder's own course a cast block where it bears:
    the girder runs on over the columns and nothing hangs under it."""
    x0, z0, x1, z1 = CANOPY
    half = (z1 - z0) // 2
    for x in range(x0, x1 + 1):
        frame = x in FRAMES_X
        for i in range(half):
            p.set(x, EAVES + i, z0 + i, IRON_STAIR + "[facing=south]" if frame else GLASS)
            p.set(x, EAVES + i, z1 - i, IRON_STAIR + "[facing=north]" if frame else GLASS)
        if frame:
            for z in range(z0 + 1, z1):
                p.set(x, EAVES, z, f"{ROD}[facing={'north' if z <= z0 + half else 'south'}]")
        p.set(x, EAVES + half, z0 + half, IRON_SLAB + "[type=bottom]")
        p.set(x, EAVES, GIRDER_Z, CAPITAL if (x, GIRDER_Z) in COLUMNS else IRON if x > x0
              else IRON_STAIR + "[half=top,facing=east]")
    for x, z in COLUMNS:
        p.set(x, FEET, z, COURSE)
        for y in range(FEET + 1, EAVES):
            p.set(x, y, z, SHAFT)


def _trestle(p):
    """Two rails of riveted slabs with a tie in every second cell: a deck half a block thick, and
    under it, at every second straight run, a lattice tower. A tower is two cells along the
    track and three across: under the rails four bearers and a cross girder between the first
    pair (the second pair has the track's own tie between it), then iron bars in all six
    columns, which join into one lattice, down to a footing course on the ridge. The two columns
    of a tower stand in one straight run and its first is one whose rails are lower slabs, so
    the bearers lie in one course, under the rails of the first and level with those of the
    second. Past the ridge's end the towers stand in the cloud. Bars would reach out into the
    cloud that is laid beside them, so the lattice ends over it and its four corners go on down
    as pipes, which join nothing: the same thin legs whether the cloud covers them or not."""
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
    for x in TOWERS:
        z = track_axis(x)
        if _slab(rail_top(x))[1] != "bottom" or track_axis(x + 1) != z:
            raise ValueError(f"no tower at x {x}: its two columns are not in one run, or the first has upper slabs")
        cap = _slab(rail_top(x))[0] - 1
        p.set(x, cap, z, IRON_SLAB + "[type=top]")
        for xx in (x, x + 1):
            for dz in (-1, 1):
                p.set(xx, cap, z + dz, IRON)
            ridge = K.cable_ridge(xx)
            foot = ridge[1] + 1 if ridge else K.ROCK_FLOOR - 1
            for dz in (-1, 0, 1):
                if ridge:
                    p.set(xx, foot, z + dz, FOOTING)
                for y in range(cap - 1, foot, -1):
                    if y > CLOUD:
                        p.set(xx, y, z + dz, BARS)
                    elif dz:
                        p.set(xx, y, z + dz, PIPE)


def _light(canvas, origin):
    """Hand the windows to the sky line, which gives the lit ones their light: a source at the
    glass, on the side its kit puts it. While the kit is not in the tree they glow without it."""
    glazed = getattr(_other("sky._lightkit"), "glazed", None)
    if glazed is not None:
        glazed(canvas, windows(), origin, group="station")


def _lining(canvas, origin):
    """The room side of the lit glass that is seen from a room. Lit glass glows on every face, and
    from the platform one looks into the winch room at the back of its two lights; the materials
    line covers that side with the sheet that goes with the glass (materials/windows.line:
    frosted glass with the night behind it). The sheets are display entities. Returns how many
    were placed: none while that module has no line()."""
    line = getattr(_other("materials.windows"), "line", None)
    if line is None:
        return 0
    n = 0
    for w in windows():
        if w.get("lined"):
            cells = [(x, y, z) for x, z in w["cells"] for y in range(w["y"][0], w["y"][1] + 1)]
            n += line(canvas, cells, w["inward"], w["glass"], origin=origin)
    return n


def build(canvas, origin=(0, 0, 0)):
    """Returns the number of display entities placed: the sheets of _lining."""
    p = _Pen(canvas, origin)
    _platform(p)
    _track(p)
    _waiting_room(p)
    _winch_house(p)
    _glaze(p)
    _glass_roof(p)
    _trestle(p)
    for y in (FEET, FEET + 1):          # the spawn cell stays empty
        p.clear(HEAD, y, AXIS)
    _light(canvas, origin)
    return _lining(canvas, origin)
