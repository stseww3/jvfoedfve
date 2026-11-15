"""site/lowerplatform: the floor of the lower platform, its railing and its outer wall
(plan/ART-PLAN.md 4, 5.3; card plan/packages/site/stair.md). The grand stair and the retaining wall
under the upper terrace are the sibling module site/stair.py.

The lower platform is the arrival level and the works yard: the cable station in its north-east
corner, the power house in its south-east, the grand stair in the middle of its west side. Feet
stand at S.LOWER_GROUND; the paving course is S.LOWER_PAVING_Y.

  floor   Small slate setts laid whole, as dark as the court above: the yard is the foreground of
          the arrival view with the top of every stone turned to the sky, and only the building is
          to be bright there (A0 #22564). The bands are polished tuff, the stone of the court's
          strips and walks (site/_kit), and they draw two things on the yard.
          The way in: a walk from the middle of the cable station's south side down to the main
          axis; the walk on the axis from the east edge to the stair, in the rows of the court's
          walk above and of the band on the stair's treads (the door bay with its two pilasters),
          so the three are one line from this edge to the door; and before the stair a forecourt
          as wide as the stair's two foot pedestals stand, a band along each side of it and an
          apron at the stair's foot. Where the axis begins, on the east edge, the walk ends in a
          block like that apron (A0 #28839), from one pier of the railing to another: a place to
          stand on the axis and look up the stair at the front. Nothing stands on it.
          The way to the works: a walk like the one from the station, from the forecourt's south
          band to the power house's door and in between its piers; the wicket's own cell is its
          threshold. The door is the house's number (site/powerhouse.DOOR_AT), so the walk is laid
          when the house is in the tree.
          The building's grid: a band on every pilaster line that carries a buttress of the
          retaining wall, a course along the foot of that wall and one inside the kerb.
          Under the cable station and the power house the field is left plain: they build on it.
          (The house writes nothing in the paving course: the floor of its doorway is laid here.)
  lamps   LAMP_POINTS names where the lamps of the way in stand on the paving, in pairs: either
          side of the walk from the station, and where that walk comes into the forecourt. The
          lamps are the props line's to place; here each only has its pad of polished tuff.
  edge    North, east and south the platform ends over the mountain. The edge is finished as every
          terrace edge is (site/_kit.rail): kerb, piers, bars. On the east edge the piers stand on
          the pilaster lines. The cable station closes its own stretch of the east edge. The power
          house's south wall stands in the row next to the south edge and leaves no ground to rail
          off: under it the kerb runs on alone, and the railing ends on the cell past either
          corner of the house, where its last bar is let into the plinth of the corner pier.
  wall    Under the kerb a slate wall goes down the face of the mountain. It only fills air: it
          shows where the rock (site/terrain) falls away from the platform and is lost in it
          elsewhere.

The platform's air is cut clear first: the terrain's east lip stood in it before the platform had
its numbers.
"""
import functools
import importlib

from ..common import blocks as B
from ..common import skeleton as S
from . import _kit as K
from .stair import APRON_X, APRON_Z, BUTTRESS_Z, FOOT_X, WALK_Z

ORDER = 20      # after the terrain (10); before the stair (25), the court (60) and what stands on the platform

X0, Z0, X1, Z1 = S.LOWER_PLATFORM       # x 61..91, z -42..43
PY = S.LOWER_PAVING_Y                   # -7
FEET = S.LOWER_GROUND                   # -6
CX0, CZ0, CX1, CZ1 = S.CABLE_STATION    # x 75..91, z -40..-26
HX0, HZ0, HX1, HZ1 = S.POWER_HOUSE["box"]       # x 67..89, z 20..42

FIELD = K.EDGE                          # slate setts
BAND = K.STRIP                          # polished tuff
WALL = B.SLATE_BRICK.block
WALL_BAND = B.SLATE_SMOOTH.block
WALL_DEPTH = 7                          # courses of the outer wall under the kerb
WALL_BANDS = (1, 5)                     # which of them are polished, counted down from the kerb

# --- the way in -----------------------------------------------------------------------------------
# The walk on the axis is five wide: the rows of the stair's band (stair.WALK_Z, rows -2..2). It
# ends on the east edge in a block as deep as the apron shows beyond the stair's foot.
LINK = 1                                            # the walk from the station is three wide: 1 either side
_MID = (CX0 + CX1) // 2                             # 83: the middle column of the cable station
LINK_X = (_MID - LINK, _MID + LINK)                 # x 82..84: the walk from the station down to the axis
LINK_Z = (CZ1 + 1, WALK_Z[0] - 1)                   # z -25..-3: from the station's south side to the axis
COURT_Z = APRON_Z                                   # rows -10 and 10: the two bands of the forecourt
START_X = X1 - (APRON_X - FOOT_X + 1)               # 88: the block where the axis begins is x 88..90
LAMP_STEP = 2 * K.BEAT                              # 8: the lamps of the way stand this far apart, in pairs
_GATE_X = (_MID - LAMP_STEP // 2, _MID + LAMP_STEP // 2)        # 79 and 87: either side of where the link comes in
_LINK_LAMP_X = (LINK_X[0] - 2, LINK_X[1] + 2)                   # 80 and 86: a cell clear of the link
LAMP_CELLS = ([(x, z) for x in _GATE_X for z in COURT_Z]
              + [(x, COURT_Z[0] - LAMP_STEP) for x in _LINK_LAMP_X])
LAMP_POINTS = [(x + 0.5, FEET, z + 0.5) for x, z in LAMP_CELLS]     # the middle of a lamp's foot, on the paving

# --- the way to the works ---------------------------------------------------------------------------
# The power house's door is its own number, site/powerhouse.DOOR_AT: the front it is in and the cell
# of the wicket, which stands in the plane of the glass, a cell behind the piers. The walk lies on
# the wicket's line and is as wide as the walk from the station, which is the doorway's width. It
# runs from the forecourt's south band into the doorway and ends in the wicket's cell.
@functools.lru_cache(maxsize=None)
def door_walk():
    """The cells (x, z) of the walk to the power house's door. There are none while site/powerhouse
    is not in the tree, or has its door in another front than the one that looks at the yard."""
    name = f"{__package__}.powerhouse"
    try:
        door = getattr(importlib.import_module(name), "DOOR_AT", None)
    except ModuleNotFoundError as e:
        if e.name != name:
            raise               # the house is there and cannot import something of its own: say so
        door = None
    if not door or door["front"] != "north" or door["cell"][1] <= COURT_Z[1]:
        return frozenset()
    x, z = door["cell"]
    return frozenset({(i, k) for i in range(x - LINK, x + LINK + 1) for k in range(COURT_Z[1] + 1, z)}
                     | {(x, z)})


# --- the edge -------------------------------------------------------------------------------------
# The cells of the south edge that get no railing: the power house's wall stands against them (c228
# #35515). The cells past its two corners (HX0 and HX1) keep a bar, which joins the corner pier's
# plinth (site/powerhouse: a whole block of polished tuff at FEET in (HX0, HZ1) and (HX1, HZ1)).
BARE = [(x, Z1) for x in range(HX0 + 1, HX1)] if HZ1 == Z1 - 1 else []


def _in(x, z, box):
    x0, z0, x1, z1 = box
    return x0 <= x <= x1 and z0 <= z <= z1


def _stone(x, z):
    """The stone of the paving course at (x, z)."""
    if (x, z) in door_walk():
        return BAND                     # the walk to the power house's door, into its doorway
    if _in(x, z, S.CABLE_STATION) or _in(x, z, S.POWER_HOUSE["box"]):
        return FIELD
    if x == X0 or x == X1 - 1 or z == Z0 + 1 or z == Z1 - 1:
        return BAND                     # along the retaining wall's foot, and inside the kerb
    if z in BUTTRESS_Z or z in COURT_Z:
        return BAND
    if APRON_Z[0] <= z <= APRON_Z[1] and (x <= APRON_X or x >= START_X):
        return BAND                     # the apron (west of the foot it lies under the stair) and its like
    if WALK_Z[0] <= z <= WALK_Z[1]:
        return BAND                     # the walk on the axis
    if LINK_X[0] <= x <= LINK_X[1] and LINK_Z[0] <= z <= LINK_Z[1]:
        return BAND                     # the walk from the station
    if (x, z) in LAMP_CELLS:
        return BAND                     # a lamp's pad
    return FIELD


def _rim():
    """The cells of the north, east and south edges in one run, from the north-west corner round
    to the south-west one."""
    north = [(x, Z0) for x in range(X0, X1 + 1)]
    east = [(X1, z) for z in range(Z0 + 1, Z1)]
    south = [(x, Z1) for x in range(X1, X0 - 1, -1)]
    return north + east + south


def _south_piers():
    """The x of the piers on the south edge: spaced like the north edge's where the railing runs from
    corner to corner. Where the power house parts it in two, each run is spaced from its corner
    pier to the cell where it meets the house, and that cell keeps its bar."""
    if not BARE:
        return K.spaced([X0, X1])
    return K.spaced([X0, HX0])[:-1] + K.spaced([HX1, X1])[1:]


def _piers():
    """North the piers are spaced evenly from corner to corner; east they stand on the pilaster
    lines, and the last line gives way to the corner pier (no two closer than K.BEAT)."""
    zs = [z for z in K.beat(Z0, Z1) if Z1 - z >= K.BEAT] + [Z1]
    return ({(x, Z0) for x in K.spaced([X0, X1])} | {(x, Z1) for x in _south_piers()}
            | {(X1, z) for z in zs})


def _outer_wall(c, o):
    for x, z in _rim():
        for d in range(1, WALL_DEPTH + 1):
            c.set(o[0] + x, o[1] + PY - d, o[2] + z, WALL_BAND if d in WALL_BANDS else WALL, keep=True)


def build(canvas, origin=(0, 0, 0)):
    c, o = canvas, origin
    c.carve(o[0] + X0, o[1] + FEET, o[2] + Z0, o[0] + X1, o[1] + S.GROUND + 1, o[2] + Z1)
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            c.set(o[0] + x, o[1] + PY, o[2] + z, _stone(x, z))
    _outer_wall(c, o)
    railed = [p for p in _rim() if p not in BARE and not _in(p[0], p[1], S.CABLE_STATION)]
    K.rail(c, o, railed, _piers(), y=FEET, kerb=True)
    for x, z in BARE:
        c.set(o[0] + x, o[1] + PY, o[2] + z, K.KERB)
    return 0
