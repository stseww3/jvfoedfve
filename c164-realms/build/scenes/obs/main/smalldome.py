"""main/smalldome -- the small dome on the south end pavilion, above the parapet. A verdigris dome
a size down from the great dome: a short stone drum with a corbelled head, an iron skirt where the
track sits, copper plates, and an observing slit that looks west with its shutter slid aside. The
astrograph (machines) stands inside.

Card: plan/packages/main/smalldome.md. Design: plan/ART-PLAN.md 5.2 and 6.3, plan/parts/main.md 6.3.

Where it sits (skeleton SMALL_*): the pavilion is bays 16-17 (z 26..34), its east wall face x 16;
the dome is x 8..16, z 26..34, nine across, centred on cell (12, 30). It stands on the pavilion's
flat roof (deck y 17, feet y 18). Its east and south sides come out to the pavilion's wall faces,
so nothing of it may reach past x 16 or z 34, and nothing above the apex row y 26.

Rows, bottom to top:
    y 18..19  the stone body, seven across and one block thick: it stands one block inside the
              dome's foot, so the dome reads as the larger of the two. A small dark window over a
              sunk panel on the east, south and north axes; an iron door on the west, onto the
              pavilion's terrace, its leaf set back to the wall's inner face.
    y 20      the head of the drum: a stone corbel (stairs hung upside down) that widens the body
              to the nine of the dome. Its lip is flush with the pavilion's wall faces.
    y 21      the iron skirt, the ring the dome turns on: riveted plate with a cast axle box on each
              axis and each diagonal, two plates between every two (the great dome's ring beam has
              one under every seam).
    y 22..26  the dome: copper plates only, in level courses, one to a ring of the raster circle
              as on the great dome: two rows upright over the skirt (the edge ring, its top a
              level line at 24), then 25.5, then the cap at 26.5 and one cast block on the axis.

What a dome nine blocks across can carry (c219 #23263, A0 #23752): no ribs -- eight ribs took half
its surface and read as patches, four would draw a cross on its top from above; the top row is one
cast block on the axis, the plates fall away from it by half blocks; a slit one block wide, from
the skirt up to the apex block, and beside it the shutter leaf slid open to the south, riveted
iron. The skin is plain: the darker copper speaks of structure alone, the great dome's ribs and
their collar, and this dome has neither (A0 #57905, 11-16; three darker plates lay scattered in
the first row over the skirt until then). The apex is row 26 (A0 #57140, 11-16): at 25 the
copper stood less than twice as high as the iron skirt in V11 and the dome read as a flat lid.

The leaf lies in the plates' own face. It lay half a block proud of them until the first pictures
(11-16): one block wide on a dome of nine it stood there as a black chimney from the terrace and
as a black speck beside the apex from the court's side. Flush, the slit and its leaf read as one
dark slot from the skirt to the apex and the outline stays round. (In the darker copper, proud, it
read as a tan rib, and the slit beside it as a crease: the room is too small to be dark inside.)

Not here: the pavilion walls and the deck under the drum (main/facade.py, c206); the astrograph
(machines, A5); the terrace's gutters, the iron plate before the door, the roof light and the
ridge walkway that leads here (main/roof.py, same card).

    python -m scenes.obs.main.smalldome          # text sections and a self-check
    python -m scenes.obs.main.smalldome check    # the self-check alone (exit code 1 on a finding)
"""
import math
import sys

from artkit.canvas import Canvas

from ..common import blocks as B
from ..common import skeleton as S
from . import _order as O

ORDER = 50

CX = (S.SMALL_DOME_X[0] + S.SMALL_DOME_X[1]) // 2        # 12
CZ = (S.SMALL_DOME_Z[0] + S.SMALL_DOME_Z[1]) // 2        # 30
R = S.SMALL_DOME_R                                       # 4.5

BODY_Y = (S.SMALL_DRUM_BASE, S.SMALL_DRUM_BASE + 1)      # 18..19: the stone body
WINDOW_Y = BODY_Y[1]                                     # 19
DOOR_Y = BODY_Y                                          # 18..19: the door onto the terrace
HEAD_Y = BODY_Y[1] + 1                                   # 20: the corbel
SKIRT_Y = HEAD_Y + 1                                     # 21: the iron skirt; the dome's curve starts at its foot
APEX = S.SMALL_DOME_APEX                                 # 26: the last row anything stands in
FOOT = R + 0.25                                          # the half-ellipse the plates follow: this wide at
RISE = APEX + 0.8 - SKIRT_Y                              # the skirt's foot, this high on the axis -- the
#                                                          apex block alone reaches the top of row 26
SLIT_X = (S.SMALL_DOME_X[0], CX - 1)                     # the slit: the west axis row, up to the apex block
LEAF_Z = CZ + 1                                          # the shutter leaf: the row south of the slit
BOX_WAYS = O.SIDES + ((1, 1), (-1, 1), (-1, -1), (1, -1))        # where the skirt's axle boxes sit

PLATE, CAST = B.VERDIGRIS_CUT, B.VERDIGRIS_CAST
STONE, PANEL = B.ASHLAR_FINE, B.ASHLAR_PANEL
IRON = B.IRON_RIVETED                                    # the skirt's plates and the shutter leaf
SKIRT = IRON.block
AXLE_BOX = B.IRON_CAST                                   # as in the great dome's ring beam
GLASS = B.WINDOW_DARK.pane                               # a pane: the glass stands back in a wall one block thick
FRONT = "sdome"                                          # the front's name in windows()
AXES = (O.EAST, O.SOUTH, O.WEST, O.NORTH)                # bay 0, 1, 2, 3
DOOR_BAY = AXES.index(O.WEST)

DOME = frozenset(O.disc(CX, CZ, R))                      # nine across: the foot of the dome
BODY = frozenset(O.disc(CX, CZ, R - 1))                  # seven across: the stone body
WALL = frozenset(c for c in BODY if any(O.step(c, d) not in BODY for d in O.SIDES))
ROOM = BODY - WALL                                       # the floor inside: five across
RING = frozenset(O.ring(BODY))                           # the columns of the corbel and the skirt


# --- the drum ---------------------------------------------------------------------------------------
def _axis_cell(d):
    """The body's wall column on an axis: the middle of that side's straight run."""
    n = max(k for k in range(int(R) + 2) if (CX + d[0] * k, CZ + d[1] * k) in BODY)
    return (CX + d[0] * n, CZ + d[1] * n)


def door_cells():
    """[(x, y, z)] of the door leaf: the wall column on the west axis, two rows."""
    x, z = _axis_cell(O.WEST)
    return [(x, y, z) for y in range(DOOR_Y[0], DOOR_Y[1] + 1)]


def windows():
    """Every window of the drum, in the form _order.build returns them, for whoever lights them.
    The front is "sdome", the bays 0 east, 1 south, 3 north; the glass is dark (an observing room)."""
    return [dict(front=FRONT, bay=bay, storey="drum", cells=[_axis_cell(d)], inward=(-d[0], -d[1]),
                 y=(WINDOW_Y, WINDOW_Y), blind=False, glass=GLASS)
            for bay, d in enumerate(AXES) if bay != DOOR_BAY]


def axle_boxes():
    """The eight columns of the skirt that hold an axle box: the outermost one on each axis and on
    each diagonal. Round the ring two plates lie between every two of them."""
    out = set()
    for dx, dz in BOX_WAYS:
        n = max(k for k in range(int(R) + 2) if (CX + dx * k, CZ + dz * k) in RING)
        out.add((CX + dx * n, CZ + dz * n))
    return out


def drum(canvas, origin=(0, 0, 0), glass=None):
    """The stone body with its three small windows and the iron door, the corbel and the skirt;
    returns the windows. glass(front, bay, storey) may name another window role for a bay."""
    ox, oy, oz = origin

    def put(x, y, z, state):
        canvas.set(ox + x, oy + y, oz + z, state)

    for x, z in WALL:
        for y in range(BODY_Y[0], BODY_Y[1] + 1):
            put(x, y, z, STONE.block)
    out = windows()
    for w in out:
        role = glass(w["front"], w["bay"], w["storey"]) if glass else None
        if role is not None:
            w["glass"] = role.pane if isinstance(role, B.Family) else role
        (x, z), = w["cells"]
        put(x, WINDOW_Y, z, w["glass"])
        put(x, WINDOW_Y - 1, z, PANEL.block)
    for (x, y, z), half in zip(door_cells(), ("lower", "upper")):         # on the cell's inner edge
        put(x, y, z, f"{B.IRON_DOOR}[facing=west,half={half},hinge=left,open=false]")
    O.Laying(canvas, None, origin, None).mould(BODY, HEAD_Y, STONE.stairs, "top")
    boxes = axle_boxes()
    for x, z in RING:
        put(x, SKIRT_Y, z, AXLE_BOX if (x, z) in boxes else SKIRT)
    return out


# --- the dome ---------------------------------------------------------------------------------------
def _in_slit(x, z):
    return z == CZ and SLIT_X[0] <= x <= SLIT_X[1]


def _is_leaf(x, z):
    return z == LEAF_Z and SLIT_X[0] <= x <= SLIT_X[1]


def _ring(x, z):
    """The ring of the raster circle a column lies in: its distance from the axis column, rounded.
    The great dome counts its rings the same way (main/_dome.py); ring 4 is this dome's edge."""
    return int(math.hypot(x - CX, z - CZ) + 0.5)


def course(ring):
    """The top face of the plates of a ring, in half blocks: a half-ellipse FOOT wide at the
    skirt's foot and RISE high, taken where the ring's middle is and rounded to the nearer half."""
    top = SKIRT_Y + RISE * math.sqrt(max(0.0, 1.0 - (ring / FOOT) ** 2))
    return max(math.floor(2.0 * top + 0.5) / 2.0, SKIRT_Y + 1.5)


def _skin():
    """{column: top face} of the dome. The plates lie in courses, one to a ring and level all the
    way round, the way the great dome's do, so the two read as one make: every course ends in one
    clean line and the dome's foot is a level one. (Taken column by column from its own distance,
    as it was until the two domes were looked at side by side, the edge ring had four different
    heights: a bundle of pipes from the roofs.) The shutter leaf lies in this face too."""
    return {(x, z): course(_ring(x, z)) for x, z in DOME}


def _foot(skin, col):
    """The lowest row a column of the shell must fill so that no gap opens under it: down to the
    top face of its lowest neighbour, and to the skirt where it stands on the dome's edge. The
    slit is no neighbour: its sides show the thickness of the shell."""
    low = APEX
    for d in O.SIDES:
        n = O.step(col, d)
        if n not in DOME:
            low = SKIRT_Y + 1
        elif n in skin:
            low = min(low, math.floor(skin[n]))
    return max(low, SKIRT_Y + 1)


def dome(canvas, origin=(0, 0, 0)):
    """The dome's shell, one block thick: plates, the cast block at the apex, the slit left open
    from the skirt to the apex block, and the shutter leaf beside it."""
    ox, oy, oz = origin
    skin = {c: top for c, top in _skin().items() if not _in_slit(*c)}
    for (x, z), top in skin.items():
        ytop = math.ceil(top) - 1                       # the cell the top face lies in
        whole = top == ytop + 1
        metal = IRON if _is_leaf(x, z) else PLATE
        for y in range(min(ytop, _foot(skin, (x, z))), ytop + 1):
            if (x, z) == (CX, CZ):
                state = CAST
            elif y == ytop and not whole:
                state = f"{metal.slab}[type=bottom]"
            else:
                state = metal.block
            canvas.set(ox + x, oy + y, oz + z, state)


# --- the package --------------------------------------------------------------------------------------
def build(canvas, origin=(0, 0, 0), glass=None):
    """The drum and the dome. No display entities (the astrograph is A5's)."""
    drum(canvas, origin, glass)
    dome(canvas, origin)
    return 0


# --- self-check and drawings ----------------------------------------------------------------------------
def check():
    """What can be told without a picture; returns the findings as lines (none is good)."""
    out = []
    c = Canvas()
    build(c)
    name = lambda x, y, z: (c.get(x, y, z) or "air").partition("[")[0]
    (x0, y0, z0), (x1, y1, z1) = c.bounds()
    skin = _skin()

    # 1. nothing leaves the footprint or stands above the apex row (the east and south sides come
    #    out to the pavilion's wall faces)
    if (x0, z0, x1, z1) != (S.SMALL_DOME_X[0], S.SMALL_DOME_Z[0], S.SMALL_DOME_X[1], S.SMALL_DOME_Z[1]):
        out.append(f"footprint: the blocks span x {x0}..{x1}, z {z0}..{z1}, not the skeleton's nine by nine")
    if (y0, y1) != (BODY_Y[0], APEX):
        out.append(f"rows: the blocks span y {y0}..{y1}, not {BODY_Y[0]}..{APEX}")
    if not RING <= DOME:
        out.append("drum: the corbel's ring is not inside the dome's foot")
    # 2. the top: one block on the axis, nothing else as high
    high = [col for col, top in skin.items() if top > APEX + 0.5 and not _in_slit(*col)]
    if high != [(CX, CZ)] or name(CX, APEX, CZ) != CAST:
        out.append(f"apex: the columns that reach the top of row {APEX} are {sorted(high)}, not the cast block alone")
    # 3. the slit is open from the skirt to the apex block, and the skirt runs on under it; the leaf
    #    beside it is riveted iron over the slit's whole length and lies in the plates' face: as
    #    high as the plates across the slit, column for column
    for x in range(SLIT_X[0], SLIT_X[1] + 1):
        if any(c.has(x, y, CZ) for y in range(SKIRT_Y + 1, APEX + 1)):
            out.append(f"slit: something stands in the slit at x {x}")
        leaf, across = _top(c, x, LEAF_Z), _top(c, x, 2 * CZ - LEAF_Z)
        if leaf is None or leaf[1] not in (IRON.block, IRON.slab):
            out.append(f"leaf: no riveted iron beside the slit at x {x}")
        elif across is None or leaf[0] != across[0]:
            out.append(f"leaf: at x {x} its face is at {leaf[0]}, the plates' across the slit at "
                       f"{across[0] if across else 'nothing'}")
    # 4. the shell is closed everywhere else: seen from above no column is missing, and no step
    #    between two neighbours is higher than the blocks that stand under the upper one
    for col, top in skin.items():
        if _in_slit(*col):
            continue
        cells = [y for y in range(SKIRT_Y + 1, APEX + 1) if c.has(col[0], y, col[1])]
        if not cells or cells != list(range(cells[0], cells[-1] + 1)):
            out.append(f"shell: column {col} is missing or broken")
            continue
        for d in O.SIDES:
            n = O.step(col, d)
            if n not in DOME and cells[0] != SKIRT_Y + 1:
                out.append(f"shell: a gap between the skirt and column {col} on the dome's edge")
            if n in skin and not _in_slit(*n) and cells[0] > skin[n]:
                out.append(f"shell: a gap under column {col} over its neighbour {n}")
    # 5. the room is clear from the floor to under the plates
    for x, z in ROOM:
        for y in range(BODY_Y[0], SKIRT_Y + 1):
            if c.has(x, y, z):
                out.append(f"room: something stands inside at ({x}, {y}, {z})")
    for y in range(BODY_Y[0], APEX - 1):
        if c.has(CX, y, CZ):
            out.append(f"room: something stands on the axis at y {y}")
    # 6. the skirt is a closed iron ring: riveted plate, an axle box on each axis and each diagonal
    #    and two plates between every two of them along the dome's edge; the corbel a closed stone one
    ring = {col: name(col[0], SKIRT_Y, col[1]) for col in RING}
    if any(what not in (SKIRT, AXLE_BOX) for what in ring.values()):
        out.append(f"skirt: the ring at y {SKIRT_Y} is not iron all round")
    boxes = {col for col, what in ring.items() if what == AXLE_BOX}
    if boxes != axle_boxes() or len(boxes) != len(BOX_WAYS):
        out.append(f"skirt: {len(boxes)} axle boxes, not one on each axis and each diagonal")
    edge = sorted((col for col in RING if any(O.step(col, d) not in DOME for d in O.SIDES)),
                  key=lambda col: math.atan2(col[1] - CZ, col[0] - CX))
    at = [k for k, col in enumerate(edge) if col in boxes]
    if len(at) != len(boxes) or any((b - a) % len(edge) != 3 for a, b in zip(at, at[1:] + at[:1])):
        out.append("skirt: the axle boxes do not stand at every third column of the dome's edge")
    if any(name(x, HEAD_Y, z) != STONE.stairs for x, z in RING):
        out.append(f"corbel: the ring at y {HEAD_Y} is not stone stairs all round")
    # 7. three dark windows and the door
    for w in windows():
        (x, z), = w["cells"]
        if name(x, WINDOW_Y, z) != GLASS:
            out.append(f"drum: no window in bay {w['bay']}")
    if any(name(*cell) != B.IRON_DOOR for cell in door_cells()):
        out.append("drum: no door leaf on the west axis")
    return out


def _top(c, x, z):
    """(the top face, the block it is the face of) of a column of the dome over the skirt; None
    where nothing stands (the open slit)."""
    top = max((y for y in range(SKIRT_Y + 1, APEX + 1) if c.has(x, y, z)), default=None)
    if top is None:
        return None
    state = c.get(x, top, z)
    return top + (0.5 if "slab" in state else 1.0), state.partition("[")[0]


def _heights(c):
    """The dome from above: the top face of every column, in half blocks (. the open slit)."""
    lines = []
    for z in range(S.SMALL_DOME_Z[0], S.SMALL_DOME_Z[1] + 1):
        row = []
        for x in range(S.SMALL_DOME_X[0], S.SMALL_DOME_X[1] + 1):
            top = _top(c, x, z)
            if top is None:
                row.append("  .  " if (x, z) in DOME else "     ")
                continue
            row.append(f"{top[0]:4.1f}{O.mark(top[1])}")
        lines.append(f"z {z}  " + " ".join(row))
    return "\n".join(lines)


def _plan(c, y):
    """One row of the drum from above (north up)."""
    lines = []
    for z in range(S.SMALL_DOME_Z[0], S.SMALL_DOME_Z[1] + 1):
        lines.append(f"z {z}  " + " ".join(O.mark(c.get(x, y, z)) if c.has(x, y, z) else "."
                                         for x in range(S.SMALL_DOME_X[0], S.SMALL_DOME_X[1] + 1)))
    return "\n".join(lines)


def _drawings():
    O.MARKS.setdefault(CAST, "A")
    O.MARKS.setdefault(B.IRON_DOOR, "J")
    O.MARKS.setdefault(AXLE_BOX, "B")
    c = Canvas()
    build(c)
    xs = (S.SMALL_DOME_X[0] - 2, S.SMALL_DOME_X[1] + 2)
    zs = (S.SMALL_DOME_Z[0] - 2, S.SMALL_DOME_Z[1] + 2)
    ys = (BODY_Y[0] - 1, APEX + 1)
    for y, what in ((WINDOW_Y, "the body at the windows"), (HEAD_Y, "the corbel"), (SKIRT_Y, "the skirt")):
        print(f"PLAN at y {y}, {what} (north up, x {S.SMALL_DOME_X[0]}..{S.SMALL_DOME_X[1]}):\n")
        print(_plan(c, y))
        print()
    print("FROM ABOVE: top face and material of every column of the dome\n")
    print(_heights(c))
    print(f"\nSECTION through the slit (z = {CZ}, west on the left):\n")
    print(O.section(c, "z", CZ, xs, ys))
    print(f"\nSECTION across the slit (x = {CX - 2}, north on the left):\n")
    print(O.section(c, "x", CX - 2, zs, ys))
    print("\nEAST ELEVATION, from the court (south on the left):\n")
    print(O.elevation(c, "east", zs, ys, xs[1], xs[0]))
    print("\nSOUTH ELEVATION (west on the left):\n")
    print(O.elevation(c, "south", xs, ys, zs[1], zs[0]))
    print("\nWEST ELEVATION, the slit and the door (north on the left):\n")
    print(O.elevation(c, "west", zs, ys, xs[0], xs[1]))
    print("\nLetters: F dressed ashlar, P sunk panel, D dark window, J iron door, I riveted iron, B axle box,")
    print("V verdigris plate, A cast block. Small letters are slabs and stairs.")


if __name__ == "__main__":
    if "check" not in sys.argv[1:]:
        _drawings()
        print()
    found = check()
    print("\n".join(found) if found else
          "self-check: footprint, apex, slit and leaf, shell, room, skirt and corbel, windows and door -- all good")
    sys.exit(1 if found else 0)
