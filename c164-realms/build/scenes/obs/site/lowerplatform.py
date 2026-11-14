"""site/lowerplatform: the floor of the lower platform, its railing and its outer wall
(plan/ART-PLAN.md 4, 5.3; card plan/packages/site/stair.md). The grand stair and the retaining wall
under the upper terrace are the sibling module site/stair.py.

The lower platform is the arrival level and the works yard: the cable station in its north-east
corner, the power house in its south-east, the grand stair in the middle of its west side. Feet
stand at S.LOWER_GROUND; the paving course is S.LOWER_PAVING_Y.

  floor   Tuff, the middle tone under the dark slate of the upper terrace. The field is tuff brick
          laid whole. The bands are polished tuff, the stone of the strips and walks of the upper
          court (site/_kit STRIP), and they draw the building's grid on the yard: a band on every
          pilaster line that carries a buttress of the retaining wall; a course along the foot of
          that wall and one inside the kerb; an apron at the stair's foot as wide as the stair and
          its cheeks, and from it a walk on the main axis to the east edge. Under the cable station
          and the power house the field is left plain: they build on it.
  edge    North, east and south the platform ends over the mountain. The edge is finished as every
          terrace edge is (site/_kit.rail): kerb, piers, bars. On the east edge the piers stand on
          the pilaster lines. The cable station closes its own stretch of the east edge.
  wall    Under the kerb a slate wall goes down the face of the mountain. It only fills air: it
          shows where the rock (site/terrain) falls away from the platform and is lost in it
          elsewhere.

The platform's air is cut clear first: the terrain's east lip stood in it before the platform had
its numbers.
"""
from ..common import blocks as B
from ..common import skeleton as S
from . import _kit as K
from .stair import BUTTRESS_Z

ORDER = 20      # after the terrain (10); before the stair (25), the court (60) and what stands on the platform

X0, Z0, X1, Z1 = S.LOWER_PLATFORM       # x 61..91, z -42..43
PY = S.LOWER_PAVING_Y                   # -7
FEET = S.LOWER_GROUND                   # -6
G = S.GRAND_STAIR
APRON = 2                               # the apron reaches this far east of the stair's foot
WALK = 1                                # the axis walk: this many rows either side of row z 0

FIELD = B.TUFF_BRICK.block
BAND = B.TUFF_SMOOTH.block
WALL = B.SLATE_BRICK.block
WALL_BAND = B.SLATE_SMOOTH.block
WALL_DEPTH = 7                          # courses of the outer wall under the kerb
WALL_BANDS = (1, 5)                     # which of them are polished, counted down from the kerb


def _in(x, z, box):
    x0, z0, x1, z1 = box
    return x0 <= x <= x1 and z0 <= z <= z1


def _stone(x, z):
    """The stone of the paving course at (x, z)."""
    if _in(x, z, S.CABLE_STATION) or _in(x, z, S.POWER_HOUSE["box"]):
        return FIELD
    if x == X0 or x == X1 - 1 or z == Z0 + 1 or z == Z1 - 1:
        return BAND                     # along the retaining wall's foot, and inside the kerb
    if z in BUTTRESS_Z:
        return BAND
    if G["z0"] - 1 <= z <= G["z1"] + 1 and x <= G["x1"] + APRON:
        return BAND                     # the apron (west of the foot it lies under the stair)
    if abs(z) <= WALK:
        return BAND
    return FIELD


def _rim():
    """The cells of the north, east and south edges in one run, from the north-west corner round
    to the south-west one."""
    north = [(x, Z0) for x in range(X0, X1 + 1)]
    east = [(X1, z) for z in range(Z0 + 1, Z1)]
    south = [(x, Z1) for x in range(X1, X0 - 1, -1)]
    return north + east + south


def _piers():
    """North and south the piers are spaced evenly from corner to corner; east they stand on the
    pilaster lines, and the last line gives way to the corner pier (no two closer than K.BEAT)."""
    xs = K.spaced([X0, X1])
    zs = [z for z in K.beat(Z0, Z1) if Z1 - z >= K.BEAT] + [Z1]
    return {(x, z) for x in xs for z in (Z0, Z1)} | {(X1, z) for z in zs}


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
    K.rail(c, o, [p for p in _rim() if not _in(p[0], p[1], S.CABLE_STATION)], _piers(), y=FEET, kerb=True)
    return 0
