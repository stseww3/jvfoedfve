"""The rotunda above the main cornice: the stone drum with its ring of small windows, the copper
gutter and the iron gallery, the verdigris dome in twenty gores, its crown, the observing slit and
what shuts it (plan/ART-PLAN.md 5.2; the skeleton's DOME_* numbers; the card is
plan/packages/main/dome.md).

This is the outer shell, laid with the elevation grammar where it is stone. The room inside, the
round frames of the windows, the door leaves and the true rollers are other cards'. The name starts
with an underscore: the category's auto-discovery does not take it; main/dome.py is the package
and main/facade.py reads the drum's windows from here.

Why twenty gores: at radius 13 a gore is then four blocks wide at the foot, one of seam and three
of plate -- the bay of the fronts below (a pilaster and three of window). Seen from the court the
seams come down at z = +-2, +-6 and +-10, the lines of the pilasters of the entrance front, and
the drum's own pilasters and windows fall on the same grid. A gore, not a seam, lies on each of
the four axes: the slit takes the west one.

Rows, from the main cornice (y 15) up:

    16       the attic course: a band of sunk panels, level with the parapet beside it
    17..21   the drum, dressed stone: a pilaster under every seam that meets a straight run of the
             round wall; in every gore a niche one block wide and one deep, the small window at
             its head (y 20) and a sunk panel under it (y 18..19); in two gores the niche is
             the door of the dome room instead (the skeleton's DOME_ROOM_DOORS). Indoors, the two
             blocks of the inner leaf that look into the corner where the hand gear's upright
             shaft climbs the wall are cased in iron plate up to the ledge (GEAR_SHAFT)
    22       a corbel course; it breaks forward over the pilasters
    23       the gallery: the top of the wall is the iron track, in front of it the copper gutter,
             sunk half a block, and outside that an iron cove whose top is the walkway. Nothing
             stands on it: the roofs of this house have no railings, and posts without a rail
             between them read as a ring of nails (POSTS)
    24       the ring beam of the dome, riveted iron, an axle box under every seam. Where the round
             wall steps it turns the corner on the inside as well (corners()): the shell is one
             block thick and passes those columns by, and from the dome room one looked through
             them, under the ring girder, at the back of the plates
    25..37   the dome's plates, whole blocks and slabs, in courses: one to a ring of the raster
             circle and level all the way round, as high as a half-ellipse is there, to the nearer
             half block. The first stands three rows upright over the ring beam (its first row is
             the sill of the slit) and ends in a level line at y 28; the next ones end at 30.5,
             32, 33.5, 34.5, 35.5 and then every half block up to 38. The slit, 5 wide, looks
             west and is open from the sill to the crown
    38       the crown: eight plates half a block over the top round one cast block on the axis,
             the only highest point of the dome (the slit stops west of it)

Nothing on the dome stands a whole block proud of the plates (A0, group #294; the first cut's
ribs made a saw-tooth of the outline). Two versions, one idea each for how close the seams stand
and how the slit is shut. The map is built with b (VERSION; the director's choice of 11-16: the
ribs follow the sphere up to the crown and tell the round when dome and sky are one brightness);
a is kept:

    a   twenty fine seams, one between every two gores, flush with the plates and of the same
        copper: a strip of the uncut sheet between the plates' joints, to be seen from close by
        (twenty lines of the darker copper would read as stripes: the pre-review of the second
        cut). What shows of them from afar is where the water runs off: the foot of every seam
        is stained with the darker copper, one course high and two under the main seams (RUNS).
        They die into a flush collar. The slit is shut by two leaves that part sideways, an iron
        stile and two columns of plate each, lying half a block over the plates; open they lie
        on the dome beside the slit.
    b   eight main ribs, the pair beside each of the four axes, of the darker copper; the twelve
        seams between them are not drawn. On the three steep courses of the foot they stand half
        a block over the plates, from there up they lie flush (PROUD_COURSES: proud, they would
        notch the top line of V1 and V2) and die into a flush collar. The slit is shut by a
        curtain of copper slats drawn up from its foot between two flush iron rails; its last
        slat is the iron bar the chains pull.
"""
import functools
import math

from ..common import blocks as B
from ..common import skeleton as S
from . import _order as O

CX, CZ = S.DOME_CENTRE
R = S.DOME_R
GORES = 20
GORE_DEG = 360.0 / GORES
ATTIC = S.PARAPET[0]                    # 16: the first row above the main cornice
DRUM_TOP = S.DRUM[1]                    # 23: the gallery's row
WINDOW_Y = (S.DRUM[0] + S.DRUM[1]) // 2                     # 20
NICHE_Y = (WINDOW_Y - 2, WINDOW_Y - 1)  # 18..19: the sunk panel under a window
NICHE_SUNK = True                       # False: the panel stands in the wall face, only the window is a recess
CORBEL_Y = DRUM_TOP - 1                 # 22
SKIRT_Y = S.DOME_SPRING                 # 24: the ring beam
SILL_Y = SKIRT_Y + 1                    # 25: the slit opens above this row
CROWN = S.DOME_APEX + 1.0               # 38.0: the plates' top face round the axis
FOOT_R = R + 0.5                        # 13.5: the plates' face at the foot (ring 13's outer face)
PILASTER_OFF = 4.5                      # a pilaster stands at most this many degrees off its seam
SLIT_HALF = S.SLIT_W // 2               # 2: the slit is z -2..2
SLIT_HEAD = CX - 2                      # 2: the last column of the slit; the crown starts east of it
DOORS = getattr(S, "DOME_ROOM_DOORS", dict(cells=((12, 10), (12, -10)), y=(18, 19)))
# The column of the room in which the upright shaft of the dome's hand gear climbs the wall, from the
# floor to its pinion in the toothed ring (machines/dome: riser_at(); interiors/domeroom leaves its
# lining open there, GEAR_SHAFT). What the room sees of the drum in that corner is the shaft's casing
# and not the wall: a column of white stone was the brightest thing in the right half of V8 (a3, 11-16)
GEAR_SHAFT = getattr(S, "DOME_GEAR_SHAFT", (-1, -9))
CASED_Y = S.DRUM                        # 18..23: from the room's floor to the ledge
CAP = frozenset(O.box(CX - 1, CZ - 1, CX + 1, CZ + 1))      # the crown's nine columns

PLATE = B.VERDIGRIS_CUT                 # the dome's plates
SHEET = B.VERDIGRIS                     # the same copper in one sheet, no joints: one block, no shapes
RIB = B.VERDIGRIS_STREAK                # the darker copper
SEAM = {"a": SHEET, "b": RIB}           # what a version draws its seams and their collar with
CAST = B.VERDIGRIS_CAST                 # the boss on the axis
SKIRT = B.IRON_RIVETED.block
AXLE_BOX = B.IRON_CAST
TRACK = B.IRON_PLATE
CASING = B.IRON_PLATE                   # behind the hand gear's upright shaft
GUTTER = B.OLD_COPPER_CUT
WALK = B.IRON_RIVETED                   # the gallery's cove
POST = B.IRON_ROD
LEAF = B.IRON_RIVETED                   # the stiles of the leaves, the curtain's rails and its bar

VERSIONS = ("a", "b")
VERSION = "b"                           # the one the map is built with (the director, 11-16); a is kept
STATES = ("open", "half", "closed")
MAIN_RIBS = tuple(k for k in range(GORES) if k % 5 in (1, 3))       # version b: 27, 63, 117, 153 ... degrees
COLLAR = {"a": 6, "b": 5}               # the ring the seams run into: its radius in blocks
RELIEF = {"a": 0.0, "b": 0.5}           # how far the seams stand over the plates
# ... and on how many courses, from the foot: on the three that stand steep (to y 32). Higher up a rib
# half a block proud shows over the dome's top line from where one stands below (3 to 4 pixels where
# the ribs at +-27 degrees cross the shoulder in V2, 2 to 3 in V1 and V11), and the outline is the
# dome's first task; there the ribs lie flush and are drawn by their copper alone.
PROUD_COURSES = {"a": 0, "b": 3}
COLLAR_RELIEF = {"a": 0.0, "b": 0.0}    # how far their collar does: it is the top line of V1
PROUD = 0.5                             # how far a leaf lies over the plates
LEAF_W = SLIT_HALF + 1                  # 3: a leaf is its stile and two columns of plate
PARTED = {"closed": 0, "half": 2, "open": SLIT_HALF + 1}            # version a: how far each leaf has slid
DRAWN = {"closed": 91.0, "half": 35.0, "open": 0.0}                 # version b: the curtain stands up to here (degrees)
SLAT_DEG = 5.0                          # a slat of the curtain, in degrees along the meridian
# Version a: how many courses, from the foot, the darker copper stains under seam k, by k % 5 --
# beside an axis, a main seam (where version b has a rib), a diagonal, a main seam, beside an axis.
# One course is the three rows over the ring beam, two reach y 30.5.
RUNS = {"a": (1, 2, 1, 2, 1), "b": None}
POSTS = 0                               # the gallery's posts: none (2 * GORES would be one over every seam and between)


def _polar(x, z):
    """Distance from the dome's centre column and the angle round it (0 = east, 90 = south)."""
    return math.hypot(x - CX, z - CZ), math.degrees(math.atan2(z - CZ, x - CX)) % 360.0


def _apart(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _nearest(cells, angle):
    """The column closest to an angle, and how far off it is; of two equally close, the one that is
    its mirror image on the other side of the building's axes gets the same answer."""
    best = min(cells, key=lambda c: (round(_apart(_polar(*c)[1], angle), 3), abs(c[1] - CZ), abs(c[0] - CX), c))
    return best, _apart(_polar(*best)[1], angle)


def rib_angles():
    """The twenty seams between the gores."""
    return [(k + 0.5) * GORE_DEG for k in range(GORES)]


def ribs(version="a"):
    """The seams a version draws on the dome: all twenty, flush (a); the eight main ribs (b)."""
    angles = rib_angles()
    return angles if version == "a" else [angles[k] for k in MAIN_RIBS]


# --- the drum ---------------------------------------------------------------------------------------
def window_cells():
    """{wall column: gore number} of the drum's windows: in the middle of each gore, the column of
    the wall line closest to it that looks one way only (a corner of the raster circle cannot take
    an opening). Gore 0 looks east; they count round by the south."""
    body = O.disc(CX, CZ, R)
    wall = body - O.shrink(body)
    flat = [c for c in wall if sum(O.step(c, d) not in body for d in O.SIDES) == 1]
    return {_nearest(flat, k * GORE_DEG)[0]: k for k in range(GORES)}


def pilaster_cells():
    """The columns of the pilaster plane that carry a pilaster: under each seam, where a column
    stands clear in front of one wall column (in a step of the raster circle a pilaster would only
    move the step). The four seams on the diagonals find none and come down on the corner itself."""
    body = O.disc(CX, CZ, R)
    clear = [c for c in O.ring(body) if sum(O.step(c, d) in body for d in O.SIDES) == 1]
    out = []
    for a in rib_angles():
        cell, off = _nearest(clear, a)
        if off <= PILASTER_OFF:
            out.append(cell)
    return sorted(set(out))


def plan():
    cells = window_cells()
    return O.Plan(O.disc(CX, CZ, R), lambda x, z, outs: O.Bay("drum", cells[(x, z)]) if (x, z) in cells else None,
                  pilasters=pilaster_cells())


def order():
    fine, panel = B.ASHLAR_FINE, B.ASHLAR_PANEL
    return [
        O.Storey((ATTIC, ATTIC), "attic", wall=panel, pier=fine),
        O.Storey((ATTIC + 1, CORBEL_Y - 1), "drum", wall=fine, pier=fine, window=O.Window((WINDOW_Y, WINDOW_Y))),
        O.Course(CORBEL_Y, fine, inner=panel),
        O.Storey((DRUM_TOP, DRUM_TOP), "track", wall=fine),
    ]


def doors(p):
    """[the columns of each doorway of the dome room, from the wall line inwards]: the wall column
    and all of the inner leaf behind it -- two columns where the round wall steps -- so the way is
    open as far as the first column of the room."""
    out = []
    for c in DOORS["cells"]:
        if len(p.outs.get(c, ())) != 1:
            continue
        inward = O.step((0, 0), p.outs[c][0], -1)
        run = [c]
        while O.step(run[-1], inward) not in p.core and len(run) < 4:
            run.append(O.step(run[-1], inward))
        out.append(run)
    return out


def niches(p):
    """[(wall column, the column of the inner leaf behind it)] of the sunk panels: under the window
    of every gore but the two whose niche is a door."""
    taken = {run[0] for run in doors(p)}
    return [(op.cells[0], op.behind()[0]) for op in p.openings if op.cells[0] not in taken]


def casing(p):
    """The columns of the inner leaf that look into the corner of the hand gear's shaft by a side."""
    return sorted(c for c in (O.step(GEAR_SHAFT, d) for d in O.SIDES) if c in p.leaf)


def posts(p):
    """The columns of the gallery's walkway that carry a post, POSTS of them at equal angles, each
    where the walkway touches the gutter by a whole side."""
    edge = [c for c in p.far if any(O.step(c, d) in p.front for d in O.SIDES)]
    return sorted({_nearest(edge, k * 360.0 / POSTS)[0] for k in range(POSTS)})


def drum(canvas, origin=(0, 0, 0), glass=None):
    """The drum and its gallery; returns the drum's windows (see _order.build)."""
    p = plan()
    windows = O.build(canvas, p, order(), origin, glass=glass)
    s = O.Laying(canvas, p, origin, glass)
    for front, back in niches(p):
        for y in O.rows(NICHE_Y):
            if NICHE_SUNK:
                s.clear(front, y)
                s.put(back, y, B.ASHLAR_PANEL.block)
            else:
                s.put(front, y, B.ASHLAR_PANEL.block)
    for run in doors(p):
        for y in O.rows(tuple(DOORS["y"])):
            for c in run:
                s.clear(c, y)
    for c in casing(p):
        for y in O.rows(CASED_Y):
            s.put(c, y, CASING)
    s.fill(p.wall, DRUM_TOP, TRACK)
    s.fill(p.front, DRUM_TOP, f"{GUTTER.slab}[type=bottom]")
    s.mould(p.body | p.front, DRUM_TOP, WALK.stairs, "top")
    for c in posts(p):
        s.put(c, DRUM_TOP + 1, f"{POST}[facing=up]")
    return windows


# --- the dome ---------------------------------------------------------------------------------------
def _half(h):
    """A height to the nearer half block."""
    return math.floor(2.0 * h + 0.5) / 2.0


def _ring(x, z):
    """The ring of the raster circle a column lies in: its distance from the centre column, rounded
    (O.disc counts the same way, so ring R is the dome's edge)."""
    return int(math.hypot(x - CX, z - CZ) + 0.5)


def course(ring):
    """The top face of the plates of a ring: a half-ellipse FOOT_R wide at the ring beam's foot and
    CROWN high on the axis, taken where the ring's middle is and rounded to the nearer half block."""
    return _half(SKIRT_Y + (CROWN - SKIRT_Y) * math.sqrt(max(0.0, 1.0 - (ring / FOOT_R) ** 2)))


def plates():
    """{column: top face} of the dome's plates, the slit's columns included. The plates lie in
    courses, one to a ring of the raster circle and level all the way round: 28 on the dome's edge
    (three rows of plates upright over the ring beam), then 30.5, 32, 33.5, 34.5, 35.5 and by half
    blocks up to 38 round the axis. Every level of the dome is then one of the round plans a ring
    wide apart, and each course ends in one clean line. (Taken column by column from its own
    distance, the ellipse gives the columns of one ring up to four different heights where it is
    steep: from the roofs the dome's lower half was a bundle of pipes, not courses.)"""
    return {(x, z): course(_ring(x, z)) for x, z in O.disc(CX, CZ, R)}


def _in_slit(x, z):
    return abs(z - CZ) <= SLIT_HALF and x <= SLIT_HEAD


def _railed(x, z, version):
    """Version b: the two columns beside the slit that are the curtain's rails."""
    return version == "b" and abs(z - CZ) == SLIT_HALF + 1 and x <= SLIT_HEAD


@functools.lru_cache(maxsize=None)
def meridians():
    """{column: the number of the seam it lies on}: a seam's meridian takes one column of every
    ring from the dome's edge up, the one closest to it of those that show a whole side to the
    ring below -- so it is one block wide on every course and never skips one (a straight line one
    block wide slips between the columns of a thin ring). On the dome's edge it is the column of
    the seam's axle box."""
    out = {}
    for ring in range(1, R + 1):
        body = O.disc(CX, CZ, ring)
        face = [c for c in body if _ring(*c) == ring and any(O.step(c, d) not in body for d in O.SIDES)]
        for k, a in enumerate(rib_angles()):
            out.setdefault(_nearest(face, a)[0], k)
    return out


def _seam(x, z, version):
    """The number of the seam the column lies on, of those the version draws; None for a column
    on none."""
    k = meridians().get((x, z))
    return None if k is None or (version == "b" and k not in MAIN_RIBS) else k


def _lined(x, z, version):
    """Is the column one of those the surface is drawn with: a seam or a rib below the collar, the
    collar itself? Not in the slit, on the rails or on the crown."""
    if (x, z) in CAP or _in_slit(x, z) or _railed(x, z, version):
        return False
    ring = _ring(x, z)
    return ring == COLLAR[version] or (ring > COLLAR[version] and _seam(x, z, version) is not None)


def _stained(x, z, version):
    """Is the column of a seam one of a run of the darker copper: the water that gathers along a
    seam runs down it and stains its lower end, over more courses under some seams than others."""
    reach = RUNS[version]
    ring = _ring(x, z)
    return reach is not None and ring != COLLAR[version] and ring > R - reach[_seam(x, z, version) % len(reach)]


def _relief(x, z, version):
    """How far the column stands over the plates: a rib's relief on the courses where it is proud,
    the collar's, else nothing."""
    if not _lined(x, z, version):
        return 0.0
    ring = _ring(x, z)
    if ring == COLLAR[version]:
        return COLLAR_RELIEF[version]
    return RELIEF[version] if ring > R - PROUD_COURSES[version] else 0.0


def surface(version="a"):
    """{column: top face} of the dome as a version builds it, the slit's columns as if it were shut
    flush: the plates, the ribs and their collar standing over them by their relief, the crown."""
    tops = plates()
    for (x, z) in tops:
        tops[(x, z)] += _relief(x, z, version)
    for c in CAP:
        tops[c] = CROWN + 0.5
    tops[(CX, CZ)] = CROWN + 1.0
    return tops


def _foot(tops, c):
    """The lowest row a column of a shell has to fill so that no gap opens under it: down to the
    top face of its lowest neighbour, and to the ring beam where it stands on the dome's edge."""
    low = None
    for d in O.SIDES:
        n = O.step(c, d)
        at = int(math.floor(tops[n])) if n in tops else SKIRT_Y
        low = at if low is None else min(low, at)
    return low


def _cells(tops, c, lowest=SKIRT_Y):
    """[(y, the cell is a slab)] of a column of a shell one block thick, bottom to top."""
    top = tops[c]
    ytop = int(math.ceil(top)) - 1                      # the cell the top face lies in
    foot = max(lowest, min(ytop, _foot(tops, c)))
    return [(y, y == ytop and top != ytop + 1) for y in range(foot, ytop + 1)]


def _state(role, slab):
    """The block of a cell of the shell: the role's whole block, or its lower slab where the cell
    is a half one. The uncut sheet is one block without shapes: its half cells are plates."""
    if not isinstance(role, B.Family):
        return f"{PLATE.slab}[type=bottom]" if slab else role
    return f"{role.slab}[type=bottom]" if slab else role.block


def _elevation(x, y):
    """Where a cell of the slit lies along its meridian, in degrees: 0 at the foot, 90 at the apex."""
    return math.degrees(math.atan2((y + 0.5 - SKIRT_Y) / (CROWN - SKIRT_Y), (CX - x) / FOOT_R))


def axle_boxes():
    """The columns of the ring beam that hold an axle box: on the dome's edge, the one closest to
    each seam (it lies on the seam, but for the four seams on the diagonals, which come down on a
    corner of the raster circle: there it is the column beside the corner)."""
    body = O.disc(CX, CZ, R)
    edge = [c for c in body if any(O.step(c, d) not in body for d in O.SIDES)]
    return {_nearest(edge, a)[0] for a in rib_angles()}


def corners():
    """The columns of the wall line that show no side to the open: where the raster circle steps,
    the one in the corner behind the two that do. The shell passes them by -- each holds one plate
    of the first course's top and nothing under it -- so they were pockets open to the room in the
    ring beam's row, and through them the room saw the plates of the foot from behind, verdigris
    under an iron ring girder. The ring beam fills them: from the room the wall line's top is iron
    all the way round."""
    body = O.disc(CX, CZ, R)
    return {c for c in body - O.shrink(body) if all(O.step(c, d) in body for d in O.SIDES)}


def dome(canvas, origin=(0, 0, 0), version="a"):
    """The dome's shell, one block thick, the slit left open above its sill; in version b the two
    rails of the curtain as well, from the sill's row up: they stand on the ring beam."""
    ox, oy, oz = origin
    tops = surface(version)
    boxes = axle_boxes()
    for (x, z) in sorted(corners()):
        canvas.set(ox + x, oy + SKIRT_Y, oz + z, SKIRT)
    for (x, z) in sorted(tops):
        slit = _in_slit(x, z)
        rail = _railed(x, z, version)
        lined = _lined(x, z, version)
        for y, slab in _cells(tops, (x, z)):
            if slit and y > SILL_Y:
                break
            if y == SKIRT_Y:
                state = AXLE_BOX if (x, z) in boxes else SKIRT
            elif (x, z) == (CX, CZ):
                state = CAST
            elif rail and y >= SILL_Y:
                state = _state(LEAF, slab)
            elif lined:
                state = _state(RIB if _stained(x, z, version) else SEAM[version], slab)
            else:
                state = _state(PLATE, slab)
            canvas.set(ox + x, oy + y, oz + z, state)


def _leaves(canvas, origin, state):
    """Version a: two leaves, each a stile of riveted iron and two columns of plate. Shut they meet
    on the axis; open they have slid apart along the ring beam and lie on the dome beside the slit.
    A leaf follows the plates half a block over them, one block thick like them."""
    ox, oy, oz = origin
    tops = surface("a")
    shift = PARTED[state]
    stile = {}
    for side in (-1, 1):
        for n in range(LEAF_W):
            z = CZ + side * (shift + n)
            for (x, zz) in tops:
                if zz == z and x <= SLIT_HEAD:
                    stile[(x, z)] = stile.get((x, z), False) or n == 0
    for c in stile:
        tops[c] += PROUD
    for (x, z), iron in sorted(stile.items()):
        for y, slab in _cells(tops, (x, z), SILL_Y + 1):
            canvas.set(ox + x, oy + y, oz + z, _state(LEAF if iron else PLATE, slab))


def _curtain(canvas, origin, state):
    """Version b: a curtain of copper slats in the plane of the plates, between the two rails. It
    is drawn up from the slit's foot (the roller is machines'), so it shuts the slit from the sill
    upwards; the slats run straight across, every third of the darker copper, and the last one up
    is the iron bar the chains pull."""
    ox, oy, oz = origin
    tops = surface("b")
    up = DRAWN[state]
    cells = []
    for (x, z) in sorted(tops):
        if not _in_slit(x, z):
            continue
        for y, slab in _cells(tops, (x, z), SILL_Y + 1):
            slat = int(_elevation(x, y) / SLAT_DEG)
            if slat * SLAT_DEG < up:
                cells.append((x, y, z, slab, slat))
    bar = max((cell[4] for cell in cells), default=None)
    for x, y, z, slab, slat in cells:
        family = LEAF if slat == bar else RIB if slat % 3 == 2 else PLATE
        canvas.set(ox + x, oy + y, oz + z, _state(family, slab))


def shutter(canvas, origin=(0, 0, 0), version="a", state="open"):
    """What shuts the slit, in one of STATES."""
    if state not in STATES:
        raise ValueError(f"the slit is one of {STATES}, not {state!r}")
    (_leaves if version == "a" else _curtain)(canvas, origin, state)


def build(canvas, origin=(0, 0, 0), glass=None, version=None, slit="open"):
    """The whole rotunda above the cornice, in the map's version when none is named. Returns the
    drum's windows."""
    version = version or VERSION
    if version not in VERSIONS:
        raise ValueError(f"the dome has versions {VERSIONS}, not {version!r}")
    windows = drum(canvas, origin, glass)
    dome(canvas, origin, version)
    shutter(canvas, origin, version, slit)
    return windows
