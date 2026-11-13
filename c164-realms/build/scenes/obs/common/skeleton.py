"""The scene skeleton: where every mass sits and how tall it is (plan/reviews/R1-first-designs.md, 0.3).

This is the one source of truth for coordinates, bay module and storey heights. The builders
(main, site, machines, interiors) read the constants and the small functions here instead of
writing numbers into their own code, so a wall, the floor behind it and the lamp on it all land on
the same grid. Materials (palette) and the occupancy table (blocks) are the other two shared files;
all three are kept by S2 (assembly) and a change is asked for in the group and approved by A0.

Axes (plan 0.3): x east, z south, y up. y = 0 is the first layer of air above the upper-terrace
paving; the paving block is at y = -1. Scene coordinates are canvas coordinates: the master scene
builds every line at ORIGIN = (0, 0, 0).

Numbers marked LOCKED come from A0's first review (R1 0.3) and do not move without A0. Numbers
marked PROVISIONAL are the plan's section-4 figures for masses the review did not pin down yet;
the site line (A4) proposes exact values through A0, and they are updated here.
"""
import math

# --- ground plane -------------------------------------------------------------------------------
GROUND = 0          # LOCKED. y of the first air above the upper-terrace paving
PAVING_Y = -1       # the paving block sits here
LOWER_DROP = 9      # PROVISIONAL. the lower platform is this many blocks below GROUND (plan 4)

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
# the telescope pier is an independent column on the dome centre, from the ground to the dome room
PIER_CENTRE = DOME_CENTRE
PIER_R = 3              # PROVISIONAL (A3/A5 refine): radius of the stone pier


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

# --- site masses, PROVISIONAL (plan 4; A4 proposes exact coordinates through A0) -----------------
# Each is (x0, z0, x1, z1) on the upper terrace unless a y is given. East (+x) is the arrival side.
FRONT_COURT = (WALL_E + 1, -30, WALL_E + 45, 30)     # ~30 x 60 east of the main building
SUNSET_PLATFORM = dict(centre=(WALL_W - 9, 0), radius=20)   # west half-circle off the rotunda
GRAND_STAIR = dict(x=WALL_E + 45, z0=-8, z1=8, width=16, drop=LOWER_DROP)   # front-court east edge
LOWER_PLATFORM = (WALL_E + 46, -42, WALL_E + 76, 43)  # ~30 x 85, LOWER_DROP below GROUND
CABLE_STATION = (WALL_E + 50, -40, WALL_E + 66, -26)  # lower platform, north half; the spawn
POWER_HOUSE = dict(box=(WALL_E + 52, 20, WALL_E + 74, 42), wall_h=10, chimney_h=30)
RADIO_MAST = dict(foot=(WALL_E + 8, -40), height=62)   # north-east stone pad
MERIDIAN_HUT = dict(centre=(WALL_E + 20, -30), size=9)  # north end of the meridian line
MERIDIAN_X = WALL_E + 20        # PROVISIONAL. the brass meridian runs north-south through the court at this x

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
    x0 = int(SUNSET_PLATFORM["centre"][0] - SUNSET_PLATFORM["radius"])
    x1 = LOWER_PLATFORM[2]
    z0 = min(Z_NORTH, LOWER_PLATFORM[1], RADIO_MAST["foot"][1])
    z1 = max(Z_SOUTH, LOWER_PLATFORM[3])
    return (x0, PAVING_Y - LOWER_DROP, z0, x1, CLOCK_BALL_MAST, z1)
