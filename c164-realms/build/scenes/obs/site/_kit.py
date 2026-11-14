"""What the site packages share. Kept by the site lead: ask for what is missing instead of editing
it on your own branch (plan/roles/INTERFACE.md 2, plan/parts/A4-site.md 7).

Three things live here:
  - the floor of the upper terrace: its three stones, so that the court and the paving round the
    building are one floor;
  - the one way an edge is finished everywhere on the hill: a kerb stone in the paving course, low
    stone piers, iron bars between them. A0 #171: nothing solid on an edge the building is seen
    over -- every block of solid height on the east lip hides about three blocks of the front from
    the arrival platform -- so a pier is one block wide and a block and a half high, the piers stand
    BEAT apart or wider, and the only continuous line is the kerb, which adds no height;
  - the line of the ridge that carries the cable track down into the cloud.

The level ground itself (the terraces, the four shelves, the fixed views) is in the skeleton.
"""
from ..common import blocks as B
from ..common import skeleton as S

# --- the floor of the upper terrace -------------------------------------------------------------
# Darker and cooler than the walls, so that the pale building sits on it (plan/packages/site/court.md).
FIELD = B.SLATE_SMOOTH.block    # the ground, one stone laid whole
EDGE = B.SLATE_BRICK.block      # a course of small stones: either side of a strip, inside a kerb
STRIP = B.TUFF_SMOOTH.block     # the middle tone: strips and walks
FOOT_STRIP_X = S.FRONT_COURT[0] + 4     # 20: the strip along the foot of the entrance front

# --- the edge of a terrace ----------------------------------------------------------------------
KERB = B.ASHLAR_ROUGH.block     # the darker of the two ashlars, in the paving course: a pale coping line
PIER = B.ASHLAR_ROUGH.wall      # between two runs of bars and under its cap the game draws a wall as a
PIER_CAP = B.ASHLAR_ROUGH.slab  # slab of stone six pixels thick; the cap oversails it by five each side
BARS = B.IRON_BARS
BEAT = S.EAST_POST_SPACING      # 4: the piers stand on the building's pilaster lines, or wider


def beat(a, b, anchor=S.Z_NORTH):
    """The positions from a to b (both included) that lie BEAT apart counted from `anchor`. With the
    default anchor these are the z of the pilaster lines of the long fronts, carried on past the
    ends of the building."""
    return [p for p in range(min(a, b), max(a, b) + 1) if (p - anchor) % BEAT == 0]


def spaced(fixed):
    """Positions for piers along a line: the `fixed` ones and, between each two neighbours, as many
    more as fit evenly without any two standing closer than BEAT."""
    fixed = sorted(set(fixed))
    out = list(fixed)
    for a, b in zip(fixed, fixed[1:]):
        n = max(1, (b - a) // BEAT)
        out += [a + int(round((b - a) * i / float(n))) for i in range(1, n)]
    return sorted(set(out))


def outline(cells):
    """The cells of a set that touch what is outside it, corners included: an outline whose cells
    touch face to face, as bars and walls need (artkit.arch.outline does this for a disc)."""
    inside = set(cells)
    return [(x, z) for x, z in inside
            if any((x + dx, z + dz) not in inside for dx in (-1, 0, 1) for dz in (-1, 0, 1))]


def rail(c, o, cells, piers, y=S.GROUND, kerb=True):
    """A railing over `cells`, a list of (x, z) that touch face to face (bars only join across a
    face): a pier on every cell that is in `piers`, bars on the rest. With `kerb` the paving block
    under every cell becomes a kerb stone. `y` is where the railing stands, the first air above the
    paving (S.GROUND on the upper terrace, S.LOWER_GROUND on the lower platform)."""
    ox, oy, oz = o
    piers = set(piers)
    for x, z in cells:
        if kerb:
            c.set(ox + x, oy + y - 1, oz + z, KERB)
        if (x, z) in piers:
            c.set(ox + x, oy + y, oz + z, PIER)
            c.set(ox + x, oy + y + 1, oz + z, PIER_CAP)
        else:
            c.set(ox + x, oy + y, oz + z, BARS)


# --- the ridge under the cable track --------------------------------------------------------------
# East of the station the mountain keeps one ridge for the trestle to stand on (site/cablecar): it
# leaves the lower platform's east edge in row z -33 and runs east by north, one cell north for
# every three east, falling slowly at first and then fast, and is under the cloud from x 118.
CABLE_RIDGE_X = (S.LOWER_PLATFORM[2] + 1, S.LOWER_PLATFORM[2] + 30)     # x 92..121
CABLE_RIDGE_Z = -33
ROCK_FLOOR = -29                # the mountain is carried down to here everywhere; the cloud's top is y -26


def cable_ridge(x):
    """(z, y) of the ridge in column x: the row of its axis and the y of its topmost rock. The rock
    is exactly that high on the axis and one row either side of it. None where there is no ridge."""
    x0, x1 = CABLE_RIDGE_X
    if not x0 <= x <= x1:
        return None
    d = x - x0 + 1
    z = int(round(CABLE_RIDGE_Z - (x - x0) / 3.0))
    y = max(ROCK_FLOOR, int(round(S.LOWER_PAVING_Y - 1 - 0.30 * d - 0.014 * d * d)))
    return z, y
