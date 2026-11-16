"""site/viaduct: the stone viaduct that takes the railway from the foot of the incline round to the
south and down into the cloud (card plan/packages/site/viaduct.md; the line is site/_rail's, and
every cell and every level here is read from it: a4 #88816 and #91496, 11-16).

Eighteen piers and seventeen arches, every bay the same and a block lower than the one before: the
line falls a block in the nine of a bay. A pier is as long as _rail.PIER along the line and as
wide as the deck, with a pilaster a block deep on either face that carries a cap at the parapet;
an arch spans the seven blocks between two piers, a half block of straight and a half circle over
it (RISE). The masonry is level in every bay and steps down at the pier's cap, where the lower
parapet runs into the pilaster; only the rails follow the grade, in half blocks. The first arches
stand tall over the cloud, on the ridge and beyond it; round the curve they sink, on the far
straight only the parapet shows, and the last bays are under the sea's face.

From the top down, in every column of the deck (_rail.deck: three rows of track, a row outside
them on either side, and at the piers a row further out):

  the rails     two rows of riveted iron half blocks, as on the incline (site/cablecar), their
                upper face where _rail.tread() has it. Between them the bed lies half a block
                lower all the way, every second block of it a sleeper: there the rack stands on
                its seats (the cable line's models)
  the parapet   in the outer rows: a course of the body's stone beside the track and a coping of
                dressed stone on it, level over the bay: a block over the rails where they are
                lowest in it and nowhere more (_rail.GAUGE)
  the bed       ballast under the track, whole blocks: the rails lie on it or half a block over it
  the body      tuff brick, the stone of the station and the power house, down to the arch
  the ring      dressed tuff a block thick round every opening, standing on an impost of the same
                stone on the pier; over the crown a keystone goes up to the coping
  the pilaster  brick, a block proud of the face from the pier's foot to the parapet: a dressed
                band where the two arches spring and a dressed cap level with the higher coping,
                which the lower one runs into. Poles and lamps that want to stand on the viaduct
                stand on the caps: stand()

What is whose: the incline's last column is x 111 and nothing here stands west of x 112. This
package builds no lower than LOWEST (the level the cloud may be laid up to beside what stands in
it); the shafts of the piers below that are the cloud line's (sky/cloudsea), which reads the
piers' cells from piers_cells(). Only the track itself goes on under that level, bed, rails,
parapet and the piers' caps, to the line's end: the train comes up through the cloud on it. The
first piers stand on the ridge's rock where it reaches up to them (site/terrain.top), on a dressed
course.

The package sets blocks; its ironwork and marks (models "site_viaduct_...") come with the card's
next round.
"""
import functools
import math

from ..common import blocks as B
from . import _rail as R
from . import terrain

ORDER = 56              # after the cable station and its incline (55), which the first pier stands against

# --- stone, wood and iron ---------------------------------------------------------------------------------
BRICK = B.TUFF_BRICK.block                  # the body: the station's stone
DRESSED = B.TUFF_SMOOTH.block               # rings, imposts, keystones, the coping, the caps
DRESSED_SLAB = B.TUFF_SMOOTH.slab
BALLAST = B.ROCK_COBBLED.block              # the bed under the track
BALLAST_SLAB = B.ROCK_COBBLED.slab
SLEEPER = B.DARK_WOOD.block                 # the sleepers that show between the rails
SLEEPER_SLAB = B.DARK_WOOD.slab
RAIL = B.IRON_RIVETED.slab                  # the incline's rails (cablecar.IRON_SLAB)

# --- the numbers ------------------------------------------------------------------------------------------
TRACK = R.GAUGE["half"]                     # 1.5: the track's three rows
HALF = TRACK + 1.0                          # 2.5: with the parapet's row on either side
WIDE = HALF + 1.0                           # 3.5: with the pilasters' row, which is filled at the piers only
SPAN = R.PITCH - R.PIER                     # 7.0: an arch, from pier to pier
RADIUS = SPAN / 2.0                         # 3.5: its half circle
STILT = 0.5                                 # the straight under the half circle
RISE = STILT + RADIUS                       # 4.0: the opening's height at the crown, over the springing
CROWN = 3                                   # courses over the crown, to the coping's upper face: the ring's, the
#                                             parapet's body beside the bed, the coping
RING = 1.25                                 # how thick the ring of dressed stone is, measured from the half circle
KEY = 0.5                                   # the keystone: this far to either side of the crown
COLLAR = (CROWN + int(RISE) + 1, CROWN + int(RISE) + 2)     # 8, 9: the pilaster's band, so many courses under its
#                                             coping: the imposts of the two arches the pier carries
LOWEST = R.CLOUD                            # -24: the lowest course of the body; what is lower is the cloud line's


def bed(top):
    """The upper face of the ballast where the rails' upper face is at ``top``: a whole number, the
    rails' own half block lying on it (a lower slab) or half a block over it (an upper one)."""
    return int(math.ceil(top)) - 1


@functools.lru_cache(maxsize=None)
def coping(bay):
    """The upper face of the parapet in a bay (0 the first pier, k the arch k - 1 and the pier k
    it runs down to): level over the whole bay, a block over the rails where they are lowest in
    it, at its downhill end."""
    end = R.S_FOOT + R.PIER + R.PITCH * bay
    return int(math.floor(R.tread(end - 1e-6) + R.GAUGE["parapet"]))


def arch(k):
    """Arch k, between pier k and pier k + 1: (s of its uphill face, the level it springs from)."""
    return R.S_FOOT + R.PIER + R.PITCH * k, coping(k + 1) - CROWN - int(RISE)


def intrados(u):
    """How high the opening is, over the springing, ``u`` along the arch from its uphill face: in
    half blocks, which upper slabs make."""
    reach = RADIUS * RADIUS - (u - RADIUS) ** 2
    return round(2.0 * (STILT + math.sqrt(max(0.0, reach)))) / 2.0


def place(s):
    """Where s lies in the viaduct: (k, pier, side, u). k is the pier or the arch; pier says which
    of the two; side is the arch whose ring a stone here may belong to (for a pier's uphill half
    the arch before it, for its downhill half the one after) and u the place along that arch."""
    along = max(0.0, s - R.S_FOOT)
    k = min(int(along // R.PITCH), R.SPANS)
    t = along - R.PITCH * k
    pier = t <= R.PIER
    side = k if not pier or t >= R.PIER / 2.0 else k - 1
    side = min(max(side, 0), R.SPANS - 1)
    return k, pier, side, s - arch(side)[0]


def _track(cell, out):
    """The track's own blocks in a column of its three rows; returns the body's uppermost course."""
    top = cell.top
    b = bed(top)
    if abs(cell.right) >= 0.5:
        y, half = R.slab(top)
        out[y] = f"{RAIL}[type={half}]"
        out[b - 1] = BALLAST
    else:
        # between the rails the bed lies half a block under them everywhere (the rack's seats stand
        # on it, all of one height: cable #91195), and every second block of line is a sleeper
        tie = int(cell.s) % 2 == 1
        if top == int(top):
            out[b] = f"{SLEEPER_SLAB if tie else BALLAST_SLAB}[type=bottom]"
            out[b - 1] = BALLAST
        else:
            out[b - 1] = SLEEPER if tie else BALLAST
    return b - 2


def _column(x, z, cell):
    """One column of the deck or of a pilaster, {y: block state}."""
    k, pier, side, u = place(cell.s)
    off = abs(cell.right)
    out = {}
    if off > HALF and not pier:
        return out
    cope = coping(k if pier else k + 1)
    spring = arch(side)[1]
    if off < TRACK:
        upper = _track(cell, out)
    else:
        out[cope - 1] = DRESSED
        upper = cope - 2
    # the body: a pier down to the rock or to LOWEST, an arch down to its ring; under LOWEST only
    # what carries the track
    deep = min(LOWEST, cope - CROWN)
    rock = low = edge = None
    if pier:
        rock = terrain.top(x, z)
        if rock is not None and rock < deep:
            rock = None
        foot = deep if rock is None else rock + 1
    else:
        low = spring + intrados(u)
        edge = int(math.ceil(low))              # the lowest whole block over the opening
        foot = max(edge, deep)
    for y in range(upper, foot - 1, -1):
        out[y] = BRICK
    if low is not None and low != int(low) and deep <= int(math.floor(low)) <= upper:
        out[int(math.floor(low))] = f"{DRESSED_SLAB}[type=top]"
    # dressed stone
    centre = spring + STILT
    for y, state in list(out.items()):
        if state != BRICK:
            continue
        plinth = rock is not None and y == foot
        if off > HALF:
            dressed = plinth or cope - y in COLLAR
        else:
            mid = y + 0.5
            ring = mid >= centre - 1e-9 and math.hypot(u - RADIUS, mid - centre) < RADIUS + RING
            impost = pier and y == spring - 1
            key = off >= TRACK and not pier and abs(u - RADIUS) <= KEY and y == cope - 2
            dressed = plinth or ring or y == edge or impost or key
        if dressed:
            out[y] = DRESSED
    return out


@functools.lru_cache(maxsize=None)
def plan():
    """Every block of the viaduct, {(x, y, z): state}, in the skeleton's coordinates."""
    out = {}
    for (x, z), cell in R.deck(WIDE).items():
        if x < int(R.FOOT):
            continue                    # the station and the incline: the cable line's
        for y, state in _column(x, z, cell).items():
            out[(x, y, z)] = state
    return out


def piers_cells():
    """For the cloud line: [(pier number, [(x, z), ...])], the columns of each pier with its two
    pilasters, which this package fills down to LOWEST and no lower."""
    out = [(k, []) for k in range(R.SPANS + 1)]
    for (x, z), cell in sorted(R.deck(WIDE).items()):
        if x >= int(R.FOOT):
            k, pier, _, _ = place(cell.s)
            if pier:
                out[k][1].append((x, z))
    return out


def stand(k, right=False):
    """(x, y, z) of the middle of the upper face of pier k's cap on the left of one going out (the
    side poles stand on, _rail.left) or on the right: where a pole or a lamp may be stood."""
    p = R.piers()[k]
    x, _, z = p.off((WIDE + HALF) / 2.0 * (1.0 if right else -1.0))
    return x, float(coping(k)), z


def sketch(right=2.0, step=1.0):
    """The viaduct's face unrolled, as text: a column of characters for every ``step`` of line,
    read off the row ``right`` of the centre line (2 and -2 are the two faces, 3 and -3 the
    pilasters, 1 a rail, 0 the row between). # body, = dressed stone, - a dressed slab, o ballast,
    w a sleeper, r a rail, . nothing."""
    blocks = plan()
    marks = {BRICK: "#", DRESSED: "=", BALLAST: "o", SLEEPER: "w"}
    heads = ((RAIL, "r"), (SLEEPER_SLAB, "w"), (BALLAST_SLAB, "o"), (DRESSED_SLAB, "-"))
    cols = []
    s = R.S_FOOT + 0.5
    while s < R.LENGTH:
        x, _, z = R.at(s).off(right)
        cols.append((int(math.floor(x)), int(math.floor(z))))
        s += step
    ys = [y for (_, y, _) in blocks]
    rows = []
    for y in range(max(ys), min(ys) - 1, -1):
        row = []
        for x, z in cols:
            state = blocks.get((x, y, z))
            row.append("." if state is None else
                       marks.get(state) or next((m for head, m in heads if state.startswith(head)), "?"))
        rows.append(f"{y:4d} " + "".join(row))
    return "\n".join(rows)


def facts():
    """What the card quotes: the levels of every bay and how many blocks there are."""
    blocks = plan()
    lines = [f"{len(blocks)} blocks, x {min(k[0] for k in blocks)}..{max(k[0] for k in blocks)}, "
             f"y {min(k[1] for k in blocks)}..{max(k[1] for k in blocks)}, "
             f"z {min(k[2] for k in blocks)}..{max(k[2] for k in blocks)}"]
    for k in range(R.SPANS):
        s0, spring = arch(k)
        p = R.at(s0 + RADIUS)
        lines.append(f"arch {k:2d}: s {s0:6.2f}..{s0 + SPAN:6.2f}, crown at ({p.x:6.1f}, {p.z:6.1f}), rails "
                     f"{R.tread(s0):6.1f}..{R.tread(s0 + SPAN):6.1f}, coping {coping(k + 1)}, springs from {spring}, "
                     f"crown {spring + int(RISE)}")
    for k, cells in piers_cells():
        rocks = sorted({terrain.top(x, z) for x, z in cells if terrain.top(x, z) is not None})
        x, y, z = stand(k)
        lines.append(f"pier {k:2d}: {len(cells)} columns, coping {coping(k)}, rock under it {rocks or 'none'}, "
                     f"the left cap's face at ({x:.1f}, {y:.1f}, {z:.1f})")
    return lines


def check():
    """What can be told without a picture; returns the findings as lines (none is good)."""
    out = []
    blocks = plan()
    deck = R.deck(WIDE)
    highest = {}
    for (x, y, z), state in blocks.items():
        cell = deck[(x, z)]
        face = y + (0.5 if "type=bottom" in state else 1.0)
        highest[(x, z)] = max(face, highest.get((x, z), face))
        over = face - cell.top
        if abs(cell.right) < TRACK and over > 1e-9:
            out.append(f"({x}, {y}, {z}): {state} stands {over} over the rails, in the track's rows")
        elif abs(cell.right) <= HALF and over > R.GAUGE["parapet"] + 1e-9:
            out.append(f"({x}, {y}, {z}): {state} stands {over} over the rails, a parapet may stand {R.GAUGE['parapet']}")
        if x < int(R.FOOT):
            out.append(f"({x}, {y}, {z}): west of the incline's foot")
    for (x, z), cell in deck.items():
        if x < int(R.FOOT) or abs(cell.right) >= TRACK:
            continue
        if abs(cell.right) >= 0.5:
            y, half = R.slab(cell.top)
            if not blocks.get((x, y, z), "").startswith(RAIL):
                out.append(f"({x}, {z}): no rail at {cell.top}")
        elif highest.get((x, z)) != cell.top - 0.5:
            out.append(f"({x}, {z}): the bed between the rails is at {highest.get((x, z))}, the rails at {cell.top}")
    return out


def build(canvas, origin=(0, 0, 0)):
    """Sets the viaduct's blocks; returns the number of display entities placed (none yet)."""
    ox, oy, oz = origin
    for (x, y, z), state in plan().items():
        canvas.set(ox + x, oy + y, oz + z, state)
    return 0
