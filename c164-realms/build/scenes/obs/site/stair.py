"""site/stair: the grand stair from the upper terrace down to the lower platform, and the retaining
wall under the terrace's east edge (plan/ART-PLAN.md 4, 5.3; card plan/packages/site/stair.md). The
floor of the lower platform, its railing and its outer wall are the sibling module
site/lowerplatform.py.

Both stand in the middle of the arrival view (S.V1): the wall is the dark band the building stands
on, the stair comes down out of it on the left. Two rules of that view shape them.
Nothing here rises above the terrace floor except the cap slabs of the two pedestals at the stair's
head, half a block: every block of solid height on that edge hides about three of the front (A0
#171; site/_kit; c235 #21906).
And nothing here is as bright as the front: only the building is (A0 #268, #28839). The faces S.V1
sees of the stair look north and up, and the game shades those less than the front, which looks
east; the same pale stone would show a third brighter here than on the building. So the stair is
slate, dressed with the middle tone of the site's floors, polished tuff, and has no pale stone at
all: a pedestal's cap of the railings' ashlar, right under its lamp, showed in S.V1 at twice the
front's brightness (the card has the numbers).

  wall       Column x 60, from under the kerb course of the terrace (y -1, site/court's) down to
             the lower paving: slate brick between a polished plinth course and a polished band
             under the kerb. It is an arcade on the building's own beat (a4, 11-16, for the second
             round: the wall is the middle of the arrival view). Under every pier of the railing
             above -- the piers are on the building's pilaster lines -- stands a pier of the wall:
             under every second one a buttress in two stages, each weathered back with a stair
             block; under the ones between a lesser buttress, one stage; beside a cheek a pier in
             the wall's own face. Between two piers the wall's face is set back one block under a
             stepped head: a blind arch, three wide, from the plinth course up to the band, with
             an iron weep hole at the foot of its panel that drains the terrace's fill. piers()
             and bays() tell the numbers: site/eastwall opens some of the arches into rooms and
             hangs the wall's ironwork; the steam main (props) runs in the band's course, so no
             buttress reaches into it.
             The lower platform is longer than the terrace, four rows in the north and five in
             the south. There the wall runs on to the platform's corners three courses high --
             the plinth course, one of brick, a polished coping -- over the rock that comes down
             to the paving (a4, 11-16: the walk of that day found raw rock against the paving in
             the north-west corner, and in the south-west a way out onto the mountain).
  stair      17 wide (rows z -8..8), x 61..72, half a block down per column (S.stair_top): polished
             slate treads -- the stone of the court floor -- on slate brick. The twelfth riser
             lands on the platform's paving.
  band       The walk of the court above comes down the middle of the treads in its own stone and
             goes on across the lower platform (site/lowerplatform): the door bay with its two
             pilasters, rows z -2..2, one line from the yard's east edge to the door. A switch
             (A0 #28839): BAND, or build(band=...). On: the director kept the band on the pictures
             (11-16). With it that line is unbroken; from the yard it is a paler runner up the
             middle of the treads and does not cut the stair in three.
  cheeks     A wall on each side, outside the 17 (rows z -9 and 9, in line with the end piers of
             the terrace railing): slate brick like the retaining wall it grows out of and on the
             same plinth course, under one course of coping that rakes with the stair, one block
             above the treads.
  pedestals  Where a cheek ends, in the coping's stone, so that the coping's line ends in them: a
             die and a cap on the plinth course. At the head (x 61) one block square, the cheek's
             own top end under a slab. At the foot two blocks square, beyond the last riser
             (x 72..73) and standing out from the cheek away from the stair, so the 17 stay clear
             and the outer rows (z -10 and 10) are pilaster lines; the cap there is four stair
             blocks laid as a hip: a slab as large as the pedestal, and in its middle a socle one
             block square, the size of a lamp's foot. They are the lamp bases: LAMP_POINTS names
             the middle of the top of each for the props line (the lamp) and the sky line (its
             light). No block is set above them. A lamp at the head stands on the lip, before the
             front for the arrival view: props/lamps gives a point above S.GROUND the lip's low
             lamp, not a pole.

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
WING_TOP = FEET + 2                                 # -4: the top course of the low wall past either end of the terrace
WING_Z = (list(range(S.LOWER_PLATFORM[1], WZ0))     # z -42..-39 and 39..43: from the terrace's ends
          + list(range(WZ1 + 1, S.LOWER_PLATFORM[3] + 1)))      # to the lower platform's corners
CHEEK_Z = (G["z0"] - 1, G["z1"] + 1)                # rows -9 and 9
HEAD_X, FOOT_X = G["x0"], G["x1"]                   # 61 and 72: the pedestals' columns
PARAPET = 1.0                                       # the cheek's top above the tread beside it

BRICK = B.SLATE_BRICK.block
SMOOTH = B.SLATE_SMOOTH.block
WEATHERING = B.SLATE_BRICK.stairs + "[facing=west,half=bottom]"     # the high side against the wall
HAUNCH = B.SLATE_BRICK.stairs       # upside down in an arch's two upper corners, its back to the pier
PANEL = B.SLATE_TILE.block          # the back of a blind arch: a step darker than the wall and in a smaller bond,
#                                     so the arch reads from across the yard (a4, 11-16)
TREAD = B.SLATE_SMOOTH.block
TREAD_SLAB = B.SLATE_SMOOTH.slab + "[type=bottom]"
DRESSING = B.TUFF_SMOOTH            # the middle tone (site/_kit.STRIP is its block): band, coping, pedestals
BAND_TREAD = DRESSING.block
BAND_SLAB = DRESSING.slab + "[type=bottom]"
COPING = DRESSING.block
COPING_SLAB = DRESSING.slab + "[type=bottom]"
DIE = DRESSING.block
CAP_SLAB = DRESSING.slab + "[type=bottom]"
CAP_STAIRS = DRESSING.stairs
GRATE = B.IRON_GRATE

# The court's walk (site/court) is the door bay with its two pilasters. The band on the treads and
# the walk across the lower platform (site/lowerplatform) keep its rows.
BAND = True                         # the switch (A0 #28839; kept on the pictures, 11-16): the walk's band lies on the treads
WALK_Z = (S.pilaster_z(S.CENTRE_BAYS[1] - 1), S.pilaster_z(S.CENTRE_BAYS[1]))       # rows -2..2

# The piers of the terrace railing stand on the pilaster lines (K.beat), and under each the wall has
# a pier of its own. The first line clear of a cheek carries a buttress, and from there outwards
# every second one; the lines between carry a lesser buttress; the line beside a cheek a pier that
# does not stand out.
_CLEAR = min(z for z in K.beat(0, WZ1) if z > CHEEK_Z[1] + 1)                               # 14
BUTTRESS_Z = [z for z in K.beat(WZ0, WZ1) if abs(z) >= _CLEAR and (abs(z) - _CLEAR) % (2 * K.BEAT) == 0]
MINOR_Z = [z for z in K.beat(WZ0, WZ1) if abs(z) > _CLEAR and (abs(z) - _CLEAR) % (2 * K.BEAT) == K.BEAT]
FLUSH_Z = [z for z in K.beat(WZ0, WZ1) if CHEEK_Z[1] < abs(z) < _CLEAR]                     # -10 and 10
DRAIN_Z = MINOR_Z                   # the lines the drains were on until the arcade: for who still reads the name
# No buttress stands in the band's course: the steam main runs there along the whole wall, its axis
# a third of a block off the face (props, m3 and a4, 11-16), and passes over every buttress's top.
BUTTRESS_TOP = TOP - 1              # -3: the course of a buttress's upper weathering
BUTTRESS_OUT = 2                    # a buttress's foot stands this far out; its upper stage and a lesser buttress, one
# Between two piers a blind arch. The goods lift's shaft stands against the wall in one bay of the
# south half (x 61..63, z 23..25; astro and sdome, 11-16): there the wall's face stays whole.
ARCH_HALF = (K.BEAT - 2) // 2       # 1: an arch fills the bay between two piers, three wide
ARCH_Y = (FEET + 1, TOP - 1)        # -5..-3: from the plinth course up to the band
BACK_X = EDGE_X - 1                 # 59: the panel at the back of an arch
LIFT_BAY = 24
_LINES = sorted(BUTTRESS_Z + MINOR_Z + FLUSH_Z)
ARCH_Z = [(a + b) // 2 for a, b in zip(_LINES, _LINES[1:]) if b - a == K.BEAT and (a + b) // 2 != LIFT_BAY]


def piers():
    """Every pier of the wall, north to south: dict(z, kind, out, top). kind is "buttress", "lesser"
    or "flush"; out is how many blocks it stands out from the wall's face at its foot (x EDGE_X + 1
    ..EDGE_X + out); top is the highest course it reaches there, the weathering's (TOP for a flush
    pier: the wall itself). A buttress's upper stage is a lesser buttress."""
    kinds = ([(z, "buttress", BUTTRESS_OUT, BUTTRESS_TOP) for z in BUTTRESS_Z]
             + [(z, "lesser", 1, BUTTRESS_TOP) for z in MINOR_Z] + [(z, "flush", 0, TOP) for z in FLUSH_Z])
    return [dict(z=z, kind=kind, out=out, top=top) for z, kind, out, top in sorted(kinds)]


def bays():
    """Every blind arch of the wall, north to south: dict(z, z0, z1, y0, y1, x, back). z is the
    middle row, z0..z1 the three rows of the recess, y0..y1 its courses (the two upper corners hold
    the stepped head), x the wall's column, cut away, and back the column of the panel behind it.
    Who opens an arch into a room (site/eastwall) overwrites these cells; a door that comes down to
    the paving also takes the plinth course under it, (x, FEET, z0..z1)."""
    return [dict(z=z, z0=z - ARCH_HALF, z1=z + ARCH_HALF, y0=ARCH_Y[0], y1=ARCH_Y[1], x=EDGE_X, back=BACK_X)
            for z in ARCH_Z]


HEAD_TOP = S.GROUND + 0.5           # the cap of a head pedestal: its slab alone stands above the terrace floor
FOOT_TOP = FEET + 3.0               # the socle on a foot pedestal's cap: a block and a half above the cheek's low end
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
    """The whole run, the stair's mouth included: there it is the back of the stair. And the low
    wall past either end of it."""
    for z in range(WZ0, WZ1 + 1):
        for y in range(FOOT, TOP + 1):
            _put(c, o, EDGE_X, y, z, SMOOTH if y in (FEET, TOP) else BRICK)
    for z in WING_Z:
        for y in range(FOOT, WING_TOP + 1):
            _put(c, o, EDGE_X, y, z, SMOOTH if y in (FEET, WING_TOP) else BRICK)


def _lesser(c, o, z):
    """One stage against the wall, one block out, up to under the band's course, where it ends in a
    weathering; the plinth course runs round it."""
    x = EDGE_X + 1
    for y in range(FEET, BUTTRESS_TOP):
        _put(c, o, x, y, z, SMOOTH if y == FEET else BRICK)
    _put(c, o, x, BUTTRESS_TOP, z, WEATHERING)


def _buttress(c, o, z):
    """Two stages against the wall: the upper one a lesser buttress, the lower one a second block
    out and two high under a weathering of its own. The two weatherings are one rake."""
    _lesser(c, o, z)
    x = EDGE_X + BUTTRESS_OUT
    for y in range(FEET, FEET + 2):
        _put(c, o, x, y, z, SMOOTH if y == FEET else BRICK)
    _put(c, o, x, FEET + 2, z, WEATHERING)


def _arch(c, o, bay):
    """A blind arch: the wall's face cut away between the plinth course and the band, a panel of
    slate tiles one block behind it, and in the two upper corners a stair block upside down with
    its back to the pier, which steps the head in. At the foot of the panel, in its middle, an
    iron grating: the weep hole of the terrace's fill, with stone behind it and under it (the hill
    is hollow there)."""
    x, back, z0, z1 = bay["x"], bay["back"], bay["z0"], bay["z1"]
    for z in range(z0, z1 + 1):
        for y in range(bay["y0"], bay["y1"] + 1):
            c.clear(o[0] + x, o[1] + y, o[2] + z)
            _put(c, o, back, y, z, PANEL)
    _put(c, o, x, bay["y1"], z0, f"{HAUNCH}[facing=north,half=top]")
    _put(c, o, x, bay["y1"], z1, f"{HAUNCH}[facing=south,half=top]")
    _put(c, o, back, bay["y0"], bay["z"], GRATE)
    _put(c, o, back - 1, bay["y0"], bay["z"], SMOOTH)
    _put(c, o, back, bay["y0"] - 1, bay["z"], BRICK)


# --- the stair ------------------------------------------------------------------------------------
def _levels(top):
    """(k, half) of a height that is a multiple of one half: whole blocks fill up to y k - 1, and
    a bottom slab lies in y k when the height ends in a half."""
    k = int(math.floor(top))
    return k, top > k


def _tread(c, o, x, z, walk):
    """Slate brick under one course of tread: the top whole block, or the slab alone where the
    height ends in a half. `walk`: the tread is of the walk's stone."""
    k, half = _levels(S.stair_top(x))
    for y in range(FEET, k):
        _put(c, o, x, y, z, BRICK if half or y < k - 1 else BAND_TREAD if walk else TREAD)
    if half:
        _put(c, o, x, k, z, BAND_SLAB if walk else TREAD_SLAB)


def _cheek(c, o, x, z):
    """The wall's plinth course and slate brick under one course of coping: the top whole block, or
    the slab alone where the rake ends in a half."""
    k, half = _levels(S.stair_top(x) + PARAPET)
    for y in range(FEET, k):
        _put(c, o, x, y, z, COPING if not half and y == k - 1 else SMOOTH if y == FEET else BRICK)
    if half:
        _put(c, o, x, k, z, COPING_SLAB)


def _hip(cells):
    """{cell: facing} for four stair blocks over a square of four cells, laid as a pinwheel: each
    has the next one before it, so the game gives every one of them its outer corner, the high
    quarter at the square's middle. Together: a slab the size of the square under a socle one
    block square."""
    x, z = min(x for x, _ in cells), min(z for _, z in cells)
    return {(x, z): "east", (x + 1, z): "south", (x + 1, z + 1): "west", (x, z + 1): "north"}


def _pedestal(c, o, cells, top):
    """The wall's plinth course, the die and the cap over `cells`, the cap's top at `top`. One cell
    is capped with a slab; four with a hip of stair blocks, whose socle carries the lamp."""
    cap = int(math.ceil(top)) - 1
    hip = _hip(cells) if len(cells) == 4 else None
    for x, z in cells:
        for y in range(FEET, cap):
            _put(c, o, x, y, z, SMOOTH if y == FEET else DIE if y == cap - 1 else BRICK)
        _put(c, o, x, cap, z, f"{CAP_STAIRS}[facing={hip[x, z]},half=bottom]" if hip else CAP_SLAB)


def build(canvas, origin=(0, 0, 0), band=None):
    """band: whether the walk's band lies on the treads; None is the switch BAND."""
    c, o = canvas, origin
    band = BAND if band is None else band
    _wall(c, o)
    for bay in bays():
        _arch(c, o, bay)
    for z in BUTTRESS_Z:
        _buttress(c, o, z)
    for z in MINOR_Z:
        _lesser(c, o, z)
    for x in range(G["x0"], G["x1"] + 1):
        for z in range(G["z0"], G["z1"] + 1):
            _tread(c, o, x, z, band and WALK_Z[0] <= z <= WALK_Z[1])
        for z in CHEEK_Z:
            _cheek(c, o, x, z)
    for cells in HEAD_PEDESTALS:
        _pedestal(c, o, cells, HEAD_TOP)
    for cells in FOOT_PEDESTALS:
        _pedestal(c, o, cells, FOOT_TOP)
    return 0
