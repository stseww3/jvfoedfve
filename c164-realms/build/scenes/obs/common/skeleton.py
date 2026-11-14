"""The scene skeleton: where every mass sits and how tall it is (plan/reviews/R1-first-designs.md, 0.3).

This is the one source of truth for coordinates, bay module and storey heights. The builders
(main, site, machines, interiors) read the constants and the small functions here instead of
writing numbers into their own code, so a wall, the floor behind it and the lamp on it all land on
the same grid. Materials (palette) and the occupancy table (blocks) are the other two shared files;
all three are kept by S2 (assembly) and a change is asked for in the group and approved by A0.

Axes (plan 0.3): x east, z south, y up. y = 0 is the first layer of air above the upper-terrace
paving; the paving block is at y = -1. Scene coordinates are canvas coordinates: the master scene
builds every line at ORIGIN = (0, 0, 0).

Numbers marked LOCKED come from A0 (the first review, R1 0.3, or the group message named beside
them) and do not move without A0. Numbers marked PROVISIONAL are the plan's section-4 figures for
masses the review did not pin down yet. Numbers marked PROPOSED are the site lead's, from
plan/parts/A4-site.md section 2. The other lines build on them; A0 may still move them on the
pictures.

Cells and points. A number that names a block (a wall face x, a pilaster z, a floor y) is a CELL:
the block column or layer with that integer coordinate, which fills the span k .. k + 1. A display
entity stands at a POINT, in real coordinates: the middle of cell k is k + 0.5, its lower side is
k. The main building is symmetric about the middle of the block row z = 0, so the axis of the
entrance, the star hall and the dome is the plane z = 0.5 and not z = 0: a model hung "at z = 0"
hangs half a block north of the axis. mid() turns a cell or a span of cells into its middle point.
"""
import math


def mid(a, b=None):
    """The middle, as a point coordinate, of cell a, or of the cells a .. b (both included)."""
    return (a + (a if b is None else b) + 1) / 2.0


# --- ground plane -------------------------------------------------------------------------------
GROUND = 0          # LOCKED. y of the first air above the upper-terrace paving
PAVING_Y = -1       # the paving block sits here
LOWER_DROP = 6      # LOCKED (A0 #171, 11-14; it was 9). the lower platform is this many blocks below GROUND
LOWER_GROUND = GROUND - LOWER_DROP      # -6, where feet stand on the lower platform
LOWER_PAVING_Y = PAVING_Y - LOWER_DROP  # -7, its paving block

# --- the bay grid of the main-building family (main building, clock tower, small dome, meridian hut) -
BAY = 4             # LOCKED. one bay = pilaster (1) + window (3)
N_BAYS = 17         # LOCKED. 18 pilasters enclose 17 bays
N_PILASTERS = N_BAYS + 1
PIL_Z0 = -34        # LOCKED. the north-most pilaster; the south-most is at +34


def pilaster_z(k):
    """z of pilaster k, k = 0 (north) .. 17 (south)."""
    return PIL_Z0 + BAY * k


def bay_center_z(j):
    """z of the centre of bay j, j = 1 (north) .. 17 (south); bay 9 is the middle at z = 0."""
    return PIL_Z0 + BAY * j - BAY // 2


Z_NORTH = pilaster_z(0)     # -34
Z_SOUTH = pilaster_z(N_BAYS)  # +34
LENGTH = Z_SOUTH - Z_NORTH + 1  # 69 blocks

# --- the three-depth section of a bay (offsets from a wall face, outwards positive) --------------
# LOCKED (R1 0.3): pilaster +1, wall 0, glass -1, cornice +2.
DEPTH_PILASTER = 1
DEPTH_WALL = 0
DEPTH_GLASS = -1
DEPTH_CORNICE = 2

# --- the main building's depth (west = rotunda side, east = entrance side) -----------------------
WALL_W = 0          # LOCKED. the west wall face
WALL_E = 15         # LOCKED. the east wall face; "depth 15" is this span
GLASS_W = WALL_W - DEPTH_GLASS   # 1, the inner (glass/wall) column on the west
GLASS_E = WALL_E + DEPTH_GLASS   # 14, the inner column on the east
ROOM_X = (GLASS_W + 1, GLASS_E - 1)   # 2..13, the clear interior, 12 deep (matches plan 8 rooms)

# five-part elevation on the ENTRANCE (east) front: end pavilion 2 + wing 5 + centre 3 + wing 5 +
# end pavilion 2 = 17 bays. The centre three bays step out 2, the two end pairs step out 1.
CENTRE_BAYS = (8, 9, 10)            # LOCKED. project +2 -> east wall face x = 17
END_BAYS = (1, 2, 16, 17)           # LOCKED. project +1 -> east wall face x = 16


def east_wall_x(bay):
    """The east (front) wall face of a bay, after the five-part projection."""
    if bay in CENTRE_BAYS:
        return WALL_E + 2
    if bay in END_BAYS:
        return WALL_E + 1
    return WALL_E


def projection(bay):
    """How far a bay steps out on the entrance front: 0, 1 or 2 blocks."""
    return east_wall_x(bay) - WALL_E


# --- storey heights of the main-building family (y), LOCKED (R1 0.3) -----------------------------
PLINTH = (0, 1)         # deepslate-brick plinth, air vents
BASE = (2, 5)           # rusticated base storey; small 3x2 barred windows
STRING = 6              # the string course; the main-storey floor block is also here
STAND = STRING + 1      # 7, feet of the main storey stand here
PANEL = 7               # the sunk panel under the window
WINDOW = (8, 13)        # the great arched window, 6 blocks of clear light
FRIEZE = 14             # frieze band (the keystone lives in this course)
CORNICE = 15            # cornice; a copper gutter runs on top
PARAPET = (16, 17)      # parapet; lightning rods stand above the pilasters
ROOF_FLOOR = 17         # the roof-terrace / dome-room floor block
ROOF_STAND = 18         # feet on the roof terrace and the dome-room floor stand here

AXIS_Z = mid(0)         # 0.5, a point: the east-west axis of symmetry runs through the middle of row z = 0

# the star hall (entrance hall): clear to y 0..13, ceiling at 14 -- NOT 12, which would cross the
# middle of the main-storey windows (R1 0.3).
STAR_HALL_Z = (-6, 6)
STAR_HALL_CEIL = 14

# --- rotunda and great dome, LOCKED (R1 0.3) ----------------------------------------------------
DOME_CENTRE = (4, 0)    # (x, z)
DOME_R = 13             # outer radius
DRUM = (18, 23)         # the stone drum, with small round windows
DOME_SPRING = 24        # the verdigris dome springs here
DOME_APEX = 37          # its top
DOME_ROOM_DIAM = 22     # the great dome-room interior diameter
SLIT_W = 5              # observing slit width, facing west, open from the drum top through the apex +2
SLIT_FACING = "west"
DOME_AXIS = (mid(DOME_CENTRE[0]), mid(DOME_CENTRE[1]))   # (4.5, 0.5), a point: what the dome turns about
# The telescope pier is an independent column on the dome centre, from the ground to the dome room.
# LOCKED by A0 (#20004, 11-14). The shaft is thin, 3 x 3, and runs straight up from y 0; its cap
# widens to 5 x 5 in the course of the dome-room floor to carry the equatorial foot (PIER_TOP_Y is
# the cap's top). The ring stair winds round the shaft inside the envelope, clockwise, from the
# gallery level (STAND, reached by a small bridge) up through the star-hall ceiling to the dome room,
# and comes out east or south of the cap, never under the tube, which points west. The ground floor
# of the star hall (y 0..6) carries no stair at all: it is kept for the orrery, the meridian and the
# mother clock. The dome-room floor leaves the envelope open for the stair and the pier.
PIER_CENTRE = DOME_CENTRE
PIER_SHAFT = (DOME_CENTRE[0] - 1, DOME_CENTRE[1] - 1, DOME_CENTRE[0] + 1, DOME_CENTRE[1] + 1)   # x 3..5, z -1..1
PIER_CAP = (DOME_CENTRE[0] - 2, DOME_CENTRE[1] - 2, DOME_CENTRE[0] + 2, DOME_CENTRE[1] + 2)     # x 2..6, z -2..2
PIER_R = 3              # the pier and ring-stair envelope: x 1..7, z -3..3
PIER_ENVELOPE = (DOME_CENTRE[0] - PIER_R, DOME_CENTRE[1] - PIER_R,
                 DOME_CENTRE[0] + PIER_R, DOME_CENTRE[1] + PIER_R)


def dome_profile(y):
    """Horizontal radius of the dome shell at height y (a half-ellipse from spring to apex), or
    None below the springing. For white-model massing and reach checks, not the final shell."""
    if y < DOME_SPRING:
        return None
    if y > DOME_APEX:
        return 0.0
    t = (y - DOME_SPRING) / float(DOME_APEX - DOME_SPRING)
    return DOME_R * math.sqrt(max(0.0, 1.0 - t * t))


# --- clock tower (north), LOCKED (R1 0.3): rises from the north end pavilion, not hidden inside ---
# base = north end pavilion (bays 1,2, z -34..-26, 9 wide), from the ground.
CLOCK_BASE_Z = (pilaster_z(0), pilaster_z(2))   # -34..-26
CLOCK_SHAFT_X = (10, 16)        # 7 columns; the east face (x=16) is flush with the end-pavilion wall face
CLOCK_SHAFT_Z = (-33, -27)      # 7 columns
CLOCK_SHAFT_TOP = 31
CLOCK_TOP = 41                  # the belfry / spire top
CLOCK_BALL_MAST = 52            # the time-ball mast

# --- small dome (south), LOCKED (R1 0.3): sits on the south end pavilion -------------------------
SMALL_PAVILION_Z = (pilaster_z(15), pilaster_z(17))   # 26..34, exactly 9 wide
SMALL_DOME_X = (8, 16)
SMALL_DOME_Z = (26, 34)
SMALL_DRUM_BASE = 18
SMALL_DOME_R = 4.5
SMALL_DOME_APEX = 25

# --- site masses ----------------------------------------------------------------------------------
# Cells. Each is (x0, z0, x1, z1) on the upper terrace unless a y is given. East (+x) is the arrival side.
# PROPOSED by A4 (plan/parts/A4-site.md 2; A0 may move them on the pictures):
SUNSET_PLATFORM = dict(centre=(WALL_W - 9, 0), radius=20)   # west half-circle off the rotunda
RADIO_MAST = dict(foot=(WALL_E + 8, -40), height=62)   # (23, -40), on MAST_PAD

# The upper terrace and the four shelves cut into the mountain round it. A4's figures (c221 #19040),
# approved by A0 (#19260.6). The terrain gives each shelf its flat rock and the ridge that leads to
# it; what stands on a shelf, the steps down to it and its railing are the shelf's own package.
# feet is where a person stands (the first air); the rock or paving block is one below.
UPPER_TERRACE = (WALL_W - 10, Z_NORTH - 4, WALL_E + 45, Z_SOUTH + 4)    # x -10..60, z -38..38; feet at GROUND
MAST_PAD = dict(box=(17, -46, 29, -39), feet=GROUND)            # north, level with the terrace
WEATHER_STATION = dict(box=(-2, -49, 8, -43), feet=-4)          # north slope, a flight of four down
WATER_TOWER = dict(box=(-21, -35, -13, -27), feet=-2)           # north-west shoulder; the tank top stays
#                                                                 below the cornice (CORNICE, y 15)
SOUTH_LOOKOUT = dict(box=(40, 48, 50, 56), feet=-5)             # on the south ridge; V11 stands here

# The east side, LOCKED by A0 (#171, 11-14) from the sight line of the arrival view. With the eye h
# below the upper terrace and a blocks east of its edge, the edge hides h x 44.5 / a of the front
# (44.5 is the court's depth). The first figures (a drop of 9, the station 12.5 from the edge) hid the
# front up to y 26, the whole row of lit windows; these hide it up to y 4.
FRONT_COURT = (WALL_E + 1, -30, WALL_E + 45, 30)     # x 16..60 east of the main building, 45 deep: the
#                                                       axial view needs the depth (the plan's 30 is void)
EAST_EDGE_X = FRONT_COURT[2]    # 60, the last column of the upper terrace
# Nothing solid may stand along the east edge: every block of solid height there hides about three
# more blocks of the front. An open iron railing only, with stone posts one block wide and at least
# EAST_POST_SPACING apart, centre to centre; a continuous coping line may run in the paving course
# only, with nothing of it above y = GROUND.
EAST_POST_SPACING = BAY         # 4: the posts stand on the pilaster lines or wider
# The grand stair runs east from the terrace edge and does not cut into the court. It is 17 wide
# (z -8..8; an even width cannot sit on an axis that runs through the middle of a row), so its cheek
# walls stand outside the 17, in rows z -9 and z 9, in line with the newel posts of the court's
# railing. Slope 1 in 2: half-block steps of one block going, twelve of them over x 61..72 for the
# six blocks of LOWER_DROP (stair_top below). A pair of lamp bases at the head and at the foot.
GRAND_STAIR = dict(x0=EAST_EDGE_X + 1, x1=EAST_EDGE_X + 2 * LOWER_DROP, z0=-8, z1=8, width=17,
                   run=2 * LOWER_DROP, drop=LOWER_DROP, rise=0.5)       # x 61..72
LOWER_PLATFORM = (WALL_E + 46, -42, WALL_E + 76, 43)  # x 61..91; feet at LOWER_GROUND, paving at LOWER_PAVING_Y
# The cable station fills the north-east corner of the lower platform. Its platform is STATION_RAISE
# above the lower platform, and the spawn is on it. The canopy faces west and is open to the west and
# the south-west on thin columns; its underside is at least CANOPY_CLEAR above the station platform.
CABLE_STATION = (WALL_E + 60, -40, WALL_E + 76, -26)  # x 75..91, z -40..-26
STATION_RAISE = 2
STATION_GROUND = LOWER_GROUND + STATION_RAISE         # -4, where feet stand on the station platform
CANOPY_CLEAR = 5                                      # so the canopy's underside is at y 1 or higher
# The power house stands on the lower platform: walls y -6..3, the chimney top at y 23.
POWER_HOUSE = dict(box=(WALL_E + 52, 20, WALL_E + 74, 42), base_y=LOWER_GROUND,
                   wall_h=10, chimney_h=30)           # x 67..89, z 20..42


def stair_top(x):
    """y of the top surface of the grand stair in column x (a point coordinate, in half blocks): 0 on
    the terrace (x <= 60), then half a block down with every column, -0.5 at x 61 .. -6 at x 72, where
    the last tread is level with the lower platform, and -6 east of it."""
    steps = min(max(int(x) - EAST_EDGE_X, 0), GRAND_STAIR["run"])
    return GROUND - steps * GRAND_STAIR["rise"]


# --- fixed camera positions, LOCKED by A0 (#171, 11-14). Points. -----------------------------------
EYE = 1.62          # the eye of a standing person, above where the feet stand
# V1, the arrival view: a person on the station platform looks west-south-west and up at the whole
# observatory in three-quarter view, the clock tower on the right and the great dome in the middle.
# Everything of the front from about y 4 up is in sight: the string course, the great windows, the
# cornice, the dome, the tower. Walking to the stair on the lower platform the front sinks behind the
# terrace edge and rises again on the stair; that is wanted.
V1 = dict(pos=(88.5, STATION_GROUND + EYE, -32.5), look_at=(8, 14, 0.5))    # the eye at y -2.38
# What V1 has to show (A0 #19629): the canopy of the cable station may come into the top of the
# picture as a frame, by no more than V1_FRAME of its height, and must not cut the top of the
# time-ball mast: the comet stands over it. tools/check.py tests the sight lines.
V1_FRAME = 1 / 8.0
# V11, the look back from the south lookout (A4's, approved by A0 #19260.6): the main building in
# three-quarter view fills the middle third, the afterglow is on the left.
V11 = dict(pos=(45.5, SOUTH_LOOKOUT["feet"] + EYE, 52.5), look_at=(6, 14, 0.5))     # the eye at y -3.38

# PROPOSED by A4 again:
MERIDIAN_X = WALL_E + 20        # 35. the brass meridian runs north-south through the court in this column
MERIDIAN_Z = (-30, 30)          # from the hut's middle to the court's south edge; the top of the inlay is y 0
# north end of the meridian line: x 31..39, z -34..-26; the door is in the south wall, on the line
MERIDIAN_HUT = dict(centre=(MERIDIAN_X, -30), size=9, door=(MERIDIAN_X, -26))
ARMILLARY = (MERIDIAN_X, 0)     # the cell where the meridian crosses the axis: the emblem roundel's
#                                 middle, kept free for the armillary sphere (machines), feet at y 0

# --- machine anchors (c193 #95, approved A0 #97) ------------------------------------------------
# Points, not cells. The great orrery hangs in the well of the star hall, on the entrance axis
# between the telescope pier and the east wall. The well is z -3..3 (gallery at z = +-5, its rail at
# z = +-4) and, under the thin pier (A0 #86.6), x 7..15; ORRERY_CENTRE is the middle of cell (11, 0).
ORRERY_CENTRE = (mid(11), AXIS_Z)       # (11.5, 0.5). the hung orrery's centre; the brass roundel in
#                                         the floor below is centred on the same cell (11, 0)
ORRERY_R = 2.5                          # outer radius; outer diameter 5, one clear cell each side of the well
ORRERY_HANG_Y = float(STAR_HALL_CEIL)   # 14.0, the ceiling block's lower face: beam, hangers, motor seat
ORRERY_RING_Y = 8.5                     # A0 #97: the ring of planets and the sun lamp sits here, at the
#                                         eye height of a person on the gallery (8.6); gears/motor above it
ORRERY_BODY_Y = (8.0, ORRERY_HANG_Y)    # the machine fills this height; the ground below (y 0..8) is walkable
# Telescope: the equatorial foot (diameter <= 5) sits on the pier cap, centred on DOME_AXIS (4.5, 0.5).
PIER_TOP_Y = float(ROOF_STAND)          # 18.0, the pier cap top; the foot stands on the cap, clear of the
#                                         joint between the pier and the dome-room floor
RING_STAIR = dict(y0=STAND, y1=ROOF_STAND, turn="clockwise")   # feet at 7 on the bridge, at 18 in the dome room
# Mother clock: wall-mounted on the pier's east face, on the axis (c193 #95, A0 #86.7, #20004): a box
# about 1.5 wide x 0.75 thick x 4 high, facing east. Its back is the east face of the shaft.
MOTHER_CLOCK = dict(back_x=float(PIER_SHAFT[2] + 1), z=AXIS_Z, y=(1.0, 5.0), facing="east")   # x 6.0, z 0.5

SITE_SPAN = 110                 # the hilltop is about 110 x 110 blocks (plan 4)


# --- entity budget (R1 0.4): placement functions return how many display entities they placed ----
ENTITY_TOTAL = 3000             # whole map
ENTITY_PER_VIEW = 600           # any one billboard view
BUDGET = {                      # by use
    "props_outdoor": 1100,
    "props_indoor": 1000,       # five rooms, <= 250 each
    "machines": 400,
    "assembly_reserve": 500,
}
BUDGET_PER_ROOM = 250
PROPS_PER_VIEW = 400            # props alone in any one view
SAMPLE_BAY_BUDGET = 120         # the M2 sample段 (5 bays), ~20 per bay


def mass_bounds():
    """A coarse (x0, y0, z0, x1, y1, z1) box around everything, for sanity and camera framing.
    Not authoritative geometry -- the masses above are."""
    shelves = [m["box"] for m in (MAST_PAD, WEATHER_STATION, WATER_TOWER, SOUTH_LOOKOUT)]
    x0 = min([int(SUNSET_PLATFORM["centre"][0] - SUNSET_PLATFORM["radius"])] + [b[0] for b in shelves])
    x1 = LOWER_PLATFORM[2]
    z0 = min([Z_NORTH, LOWER_PLATFORM[1], RADIO_MAST["foot"][1]] + [b[1] for b in shelves])
    z1 = max([Z_SOUTH, LOWER_PLATFORM[3]] + [b[3] for b in shelves])
    return (x0, PAVING_Y - LOWER_DROP, z0, x1, CLOCK_BALL_MAST, z1)
