"""site/stair: the grand stair from the upper terrace down to the lower platform, and the retaining
wall under the terrace's east edge (plan/ART-PLAN.md 4, 5.3; card plan/packages/site/stair.md). The
floor of the lower platform, its railing and its outer wall are the sibling module
site/lowerplatform.py.

Both stand in the middle of the arrival view (S.V1): the wall is the dark band the building stands
on, the stair comes down out of it on the left. Nothing here rises above the terrace floor except
the cap slabs of the two pedestals at the stair's head, half a block: every block of solid height
on that edge hides about three of the front (A0 #171; site/_kit; c235 #21906).

  wall       Column x 60, from under the kerb course of the terrace (y -1, site/court's) down to
             the lower paving: slate brick between a polished plinth course and a polished band
             under the kerb. A buttress stands under every second pier of the railing above -- the
             piers are on the building's pilaster lines -- in two stages, each weathered back with
             a stair block; in the bay between two buttresses, under the pier between them, an iron
             grating drains the terrace fill onto a splash stone.
  stair      17 wide (rows z -8..8), x 61..72, half a block down per column (S.stair_top): polished
             slate treads -- the stone of the court floor -- on slate brick. The twelfth riser
             lands on the platform's paving.
  cheeks     A wall on each side, outside the 17 (rows z -9 and 9, in line with the end piers of
             the terrace railing): slate brick like the retaining wall it grows out of, and on it
             an ashlar parapet that rakes with the stair, one block above the treads.
  pedestals  Where a cheek ends: plinth, panelled die, cap. At the head (x 61) one block square, the
             cheek's own top end. At the foot two blocks square, beyond the last riser (x 72..73)
             and standing out from the cheek away from the stair, so the 17 stay clear. They are
             the lamp bases: LAMP_POINTS names the middle of the top of each for the props line
             (the lamp) and the sky line (its light). No block is set above them.

Blocks only, no display entities.
"""
import math

from ..common import blocks as B
from ..common import skeleton as S
from . import _kit as K

ORDER = 25      # after the terrain (10) and the lower platform's floor (20); before the court (60)

G = S.GRAND_STAIR
EDGE_X = S.EAST_EDGE_X                              # 60: the wall's column
WZ0, WZ1 = S.UPPER_TERRACE[1], S.UPPER_TERRACE[3]   # z -38..38: the wall's run
TOP = S.PAVING_Y - 1                                # -2: the wall's top course, under the kerb course
FOOT = S.LOWER_PAVING_Y                             # -7: its lowest course, beside the lower paving
FEET = S.LOWER_GROUND                               # -6: the first course that is seen
CHEEK_Z = (G["z0"] - 1, G["z1"] + 1)                # rows -9 and 9
HEAD_X, FOOT_X = G["x0"], G["x1"]                   # 61 and 72: the pedestals' columns
PARAPET = 1.0                                       # the cheek's top above the tread beside it

BRICK = B.SLATE_BRICK.block
SMOOTH = B.SLATE_SMOOTH.block
SPLASH = B.SLATE_SMOOTH.slab + "[type=bottom]"
WEATHERING = B.SLATE_BRICK.stairs + "[facing=west,half=bottom]"     # the high side against the wall
TREAD = B.SLATE_SMOOTH.block
TREAD_SLAB = B.SLATE_SMOOTH.slab + "[type=bottom]"
ASHLAR = B.ASHLAR_ROUGH.block
ASHLAR_SLAB = B.ASHLAR_ROUGH.slab + "[type=bottom]"
DIE = B.ASHLAR_PANEL.block
GRATE = B.IRON_GRATE

# The piers of the terrace railing stand on the pilaster lines (K.beat). The first line clear of a
# cheek carries a buttress, and from there outwards every second one; the lines between carry a drain.
_CLEAR = min(z for z in K.beat(0, WZ1) if z > CHEEK_Z[1] + 1)                               # 14
BUTTRESS_Z = [z for z in K.beat(WZ0, WZ1) if abs(z) >= _CLEAR and (abs(z) - _CLEAR) % (2 * K.BEAT) == 0]
DRAIN_Z = [z for z in K.beat(WZ0, WZ1) if abs(z) > _CLEAR and (abs(z) - _CLEAR) % (2 * K.BEAT) == K.BEAT]

HEAD_TOP = S.GROUND + 0.5           # the cap of a head pedestal: its slab alone stands above the terrace floor
FOOT_TOP = FEET + 2.5               # the cap of a foot pedestal: a block above the cheek's low end
FOOT_SIZE = 2                       # a foot pedestal is this many blocks square


def _away(z):
    """The step from a cheek's row away from the stair."""
    return -1 if z < G["z0"] else 1


def _pedestal_cells(x, z, size):
    """The cells of the pedestal that ends the cheek in row z: from column x eastwards, from the
    cheek's row away from the stair."""
    return [(x + i, z + _away(z) * j) for i in range(size) for j in range(size)]


def _middle(cells):
    xs, zs = [x for x, _ in cells], [z for _, z in cells]
    return (min(xs) + max(xs) + 1) / 2.0, (min(zs) + max(zs) + 1) / 2.0


HEAD_PEDESTALS = [_pedestal_cells(HEAD_X, z, 1) for z in CHEEK_Z]
FOOT_PEDESTALS = [_pedestal_cells(FOOT_X, z, FOOT_SIZE) for z in CHEEK_Z]
LAMP_POINTS = [(_middle(cells)[0], top, _middle(cells)[1])
               for group, top in ((HEAD_PEDESTALS, HEAD_TOP), (FOOT_PEDESTALS, FOOT_TOP)) for cells in group]
# The paving under the stair's foot is one apron (site/lowerplatform): as wide as the foot pedestals stand.
APRON_Z = (CHEEK_Z[0] - (FOOT_SIZE - 1), CHEEK_Z[1] + (FOOT_SIZE - 1))
APRON_X = FOOT_X + FOOT_SIZE        # 74: one column beyond the pedestals


def _put(c, o, x, y, z, state):
    c.set(o[0] + x, o[1] + y, o[2] + z, state)


# --- the retaining wall ---------------------------------------------------------------------------
def _wall(c, o):
    """The whole run, the stair's mouth included: there it is the back of the stair."""
    for z in range(WZ0, WZ1 + 1):
        for y in range(FOOT, TOP + 1):
            _put(c, o, EDGE_X, y, z, SMOOTH if y in (FEET, TOP) else BRICK)


def _buttress(c, o, z):
    """Two stages against the wall: the lower two blocks out and two high, the upper one block out
    and up to the band under the kerb. Each ends in a weathering; the plinth course runs round."""
    x = EDGE_X + 1
    for y in range(FEET, TOP):
        _put(c, o, x, y, z, SMOOTH if y == FEET else BRICK)
    _put(c, o, x, TOP, z, WEATHERING)
    for y in range(FEET, FEET + 2):
        _put(c, o, x + 1, y, z, SMOOTH if y == FEET else BRICK)
    _put(c, o, x + 1, FEET + 2, z, WEATHERING)


def _drain(c, o, z):
    _put(c, o, EDGE_X, FEET + 1, z, GRATE)
    _put(c, o, EDGE_X + 1, FEET, z, SPLASH)


# --- the stair ------------------------------------------------------------------------------------
def _levels(top):
    """(k, half) of a height that is a multiple of one half: whole blocks fill up to y k - 1, and
    a bottom slab lies in y k when the height ends in a half."""
    k = int(math.floor(top))
    return k, top > k


def _tread(c, o, x, z):
    k, half = _levels(S.stair_top(x))
    for y in range(FEET, k):
        _put(c, o, x, y, z, BRICK if half or y < k - 1 else TREAD)
    if half:
        _put(c, o, x, k, z, TREAD_SLAB)


def _cheek(c, o, x, z):
    """Slate brick up to the parapet; the parapet is the top whole block, and the slab on it where
    the rake ends in a half."""
    k, half = _levels(S.stair_top(x) + PARAPET)
    for y in range(FEET, k):
        _put(c, o, x, y, z, BRICK if y < k - 1 else ASHLAR)
    if half:
        _put(c, o, x, k, z, ASHLAR_SLAB)


def _pedestal(c, o, cells, top):
    """Plinth, die and cap over `cells`, the cap's top at `top`; slate brick under the plinth down
    to the paving."""
    cap = int(math.floor(top))
    for x, z in cells:
        for y in range(FEET, cap - 2):
            _put(c, o, x, y, z, BRICK)
        _put(c, o, x, cap - 2, z, ASHLAR)
        _put(c, o, x, cap - 1, z, DIE)
        _put(c, o, x, cap, z, ASHLAR_SLAB)


def build(canvas, origin=(0, 0, 0)):
    c, o = canvas, origin
    _wall(c, o)
    for z in BUTTRESS_Z:
        _buttress(c, o, z)
    for z in DRAIN_Z:
        _drain(c, o, z)
    for x in range(G["x0"], G["x1"] + 1):
        for z in range(G["z0"], G["z1"] + 1):
            _tread(c, o, x, z)
        for z in CHEEK_Z:
            _cheek(c, o, x, z)
    for cells in HEAD_PEDESTALS:
        _pedestal(c, o, cells, HEAD_TOP)
    for cells in FOOT_PEDESTALS:
        _pedestal(c, o, cells, FOOT_TOP)
    return 0
