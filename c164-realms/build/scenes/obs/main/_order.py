"""The elevation grammar: one set of rules that lays every stone front of the observatory
(plan/ART-PLAN.md 5.1 and 5.4, plan/parts/main.md 3 and 4, the three depths of the skeleton).

A front is said in two halves, and build() multiplies them:

  Plan    WHERE. The footprint -- the block columns a building fills up to its wall face -- and,
          for every column of the wall line, what it is: a pier with a pilaster in front of it, a
          column of a window bay, or plain wall. The rest follows from the footprint:

              far      two blocks in front of the wall line    the cornice plane   (+2)
              front    one block in front                      the pilaster plane  (+1)
              wall     the outermost columns of the footprint  the wall plane      ( 0)
              leaf     one block behind                        the glass plane     (-1)

          so the three depths of a bay are not drawn, they come out of the plan, and a front that
          steps, turns a corner or runs round a drum gets its returns and corner blocks for free.
  Order   WHAT. The bands of the elevation from the ground up -- Plinth, Storey, Course, Frieze,
          Cornice, Parapet -- each with its rows, its materials and its recipe. Bay width, storey
          heights, mouldings and window types are all arguments, so another building is another
          Order on another Plan and no new code.

    from scenes.obs.main import _order as O

    plan = O.Plan(O.box(0, 0, 21, 21), O.bays(O.box(0, 0, 21, 21), bay=5))   # 22 x 22, bays of five
    order = [O.Plinth((0, 1), B.TUFF_BRICK),
             O.Storey((2, 8), "hall", wall=B.TUFF_BRICK, pier=B.TUFF_BRICK,
                      window=O.Window((3, 8), head="arch")),
             O.Cornice(9, B.TUFF_BRICK, reach=1)]
    windows = O.build(canvas, plan, order, origin)

Materials are roles of the occupancy table (scenes.obs.common.blocks); what a role looks like is
the materials line's business. Mouldings are stairs turned towards the wall: the game works out
where they turn a corner from their neighbours when the structure is placed (StairBlock), and so
does the offline renderer (artkit.shapes), so no state here names a shape.

Coordinates are scene cells (x east, z south, y up). The name starts with an underscore: the
category's auto-discovery does not take it for a work package.
"""
from ..common import blocks as B

EAST, WEST, SOUTH, NORTH = (1, 0), (-1, 0), (0, 1), (0, -1)
SIDES = (EAST, WEST, SOUTH, NORTH)
NAME = {EAST: "east", WEST: "west", SOUTH: "south", NORTH: "north"}
STEP = {v: k for k, v in NAME.items()}
SQUARE = [(dx, dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1)]


# --- sets of block columns ------------------------------------------------------------------------
def step(c, d, n=1):
    return (c[0] + d[0] * n, c[1] + d[1] * n)


def grow(cells):
    """The columns and everything that touches them, corners included."""
    return {(x + dx, z + dz) for x, z in cells for dx, dz in SQUARE}


def shrink(cells):
    """The columns that have all eight neighbours in the set."""
    return {c for c in cells if all((c[0] + dx, c[1] + dz) in cells for dx, dz in SQUARE)}


def ring(cells):
    """The columns round a set: one block out, corner blocks included."""
    return grow(cells) - set(cells)


def box(x0, z0, x1, z1):
    """The columns of a rectangle, corners included."""
    return {(x, z) for x in range(min(x0, x1), max(x0, x1) + 1) for z in range(min(z0, z1), max(z0, z1) + 1)}


def disc(cx, cz, r):
    """The columns whose middle is within r + 0.5 of the middle of column (cx, cz): a round plan the
    way the skeleton counts its radius, from block centre to block centre."""
    n = int(r) + 1
    return {(x, z) for x in range(cx - n, cx + n + 1) for z in range(cz - n, cz + n + 1)
            if int(((x - cx) ** 2 + (z - cz) ** 2) ** 0.5 + 0.5) <= r}


# --- the plan ---------------------------------------------------------------------------------------
class Pier:
    """A column of the wall line with a pilaster in front of it.

    out     the sides the pilaster stands on, as names ("east", ...). Left out: every open side of
            the column, and on a corner the block between the two as well.
    crest   the pilaster is one of the order's own (it stands on a pilaster line): it carries the
            emblem block in the frieze and a post in the parapet. False for the extra width of a
            broad corner pier.
    """

    def __init__(self, out=None, crest=True):
        self.out, self.crest = out, crest


class Bay:
    """A column of the wall line that belongs to a window bay.

    front, bay   name the bay; all columns of one bay give the same two (they key the windows).
    out          the side the bay looks to; needed only where the column has two open sides.
    blind        the same recess, backed with stone instead of glass.
    """

    def __init__(self, front, bay, out=None, blind=False):
        self.front, self.bay, self.out, self.blind = front, bay, out, blind


class Opening:
    """A window bay of a plan: its columns of the wall line in order, and the side it looks to."""

    def __init__(self, front, bay, out, blind):
        self.front, self.bay, self.out, self.blind = front, bay, out, blind
        self.cells = []
        self.door = None        # (y0, y1, stone for the arched head or None) once Plan.door() is called

    @property
    def inward(self):
        return (-self.out[0], -self.out[1])

    def behind(self, n=1):
        """The columns n blocks behind the opening's: where its glass stands."""
        return [step(c, self.out, -n) for c in self.cells]

    def middle(self):
        """The middle column, or None when the opening has an even number of them."""
        return self.cells[len(self.cells) // 2] if len(self.cells) % 2 else None


class Plan:
    """Where a front stands. footprint: the columns filled up to the wall face. classify(x, z, outs)
    says what each column of the wall line is -- a Pier, a Bay or None for plain wall; outs are the
    names of the column's open sides."""

    def __init__(self, footprint, classify=None, piers=()):
        self.body = frozenset(footprint)
        core = shrink(self.body)
        self.wall = self.body - core
        self.leaf = core - shrink(core)
        self.core = shrink(core)                     # what lies inside both leaves
        self.front = ring(self.body)
        self.far = ring(self.body | self.front)
        self.outs = {c: tuple(d for d in SIDES if step(c, d) not in self.body) for c in self.wall}
        self.piers = set(piers)     # columns of the front ring that hold a pilaster
        self.crests = set()         # those of them that stand on a pilaster line
        self.posts = set()          # columns of the wall line behind a crest: the parapet's posts
        self.jambs = set()          # every column of the wall line behind a pilaster
        self.bays = {}              # (front, bay) -> Opening
        for c in sorted(self.wall):
            outs = self.outs[c]
            if not outs or classify is None:
                continue            # the inside of a re-entrant corner is plain wall
            what = classify(c[0], c[1], tuple(NAME[d] for d in outs))
            if isinstance(what, Pier):
                sides = outs if what.out is None else tuple(STEP[n] for n in what.out)
                cells = [step(c, d) for d in sides]
                if len(sides) == 2 and sides[0][0] != sides[1][0] and sides[0][1] != sides[1][1]:
                    cells.append((c[0] + sides[0][0] + sides[1][0], c[1] + sides[0][1] + sides[1][1]))
                self.piers.update(cells)
                self.jambs.add(c)
                if what.crest:
                    self.crests.update(cells[:len(sides)])
                    self.posts.add(c)
            elif isinstance(what, Bay):
                if what.out is None and len(outs) != 1:
                    raise ValueError(f"bay column {c} has {len(outs)} open sides: say which one it looks to")
                out = outs[0] if what.out is None else STEP[what.out]
                key = (what.front, what.bay)
                if key not in self.bays:
                    self.bays[key] = Opening(what.front, what.bay, out, what.blind)
                op = self.bays[key]
                if op.out != out:
                    raise ValueError(f"bay {key} looks two ways: {NAME[op.out]} and {NAME[out]}")
                op.cells.append(c)
        stray = self.piers - self.front
        if stray:
            raise ValueError(f"pilasters off the front ring: {sorted(stray)[:6]}")
        for op in self.bays.values():
            op.cells.sort(key=lambda c: c[1] if op.out[0] else c[0])
            run = [c[1] if op.out[0] else c[0] for c in op.cells]
            if run != list(range(run[0], run[0] + len(run))) or len({c[0] if op.out[0] else c[1] for c in op.cells}) != 1:
                raise ValueError(f"bay {(op.front, op.bay)} is not one straight run: {op.cells}")

    @property
    def openings(self):
        return [self.bays[k] for k in sorted(self.bays, key=lambda k: (str(k[0]), k[1]))]

    def door(self, front, bay, y0, y1, arch=None):
        """Turn a bay into a doorway from row y0 to y1, through both leaves; `arch` (a stone family)
        rounds the two top corners like a window head. The storeys leave their windows out of it."""
        self.bays[(front, bay)].door = (y0, y1, arch)

    def pier_fronts(self, wrap):
        """The columns of the far ring that a pilaster's own mouldings stand on: the one in front
        of it, with wrap the corner ones beside that as well. A corner pier always gets its corner."""
        if wrap:
            return ring(self.body | self.piers) & self.far
        fronts = {step(p, d) for p in self.piers for d in SIDES} & self.far
        for c in list(self.far - fronts):
            for dx in (-1, 1):
                for dz in (-1, 1):
                    if (c[0] + dx, c[1] + dz) in self.piers and (c[0] + dx, c[1]) in fronts and (c[0], c[1] + dz) in fronts:
                        fronts.add(c)
        return fronts


def bays(footprint, bay=4, pier=1, origin=(0, 0), fronts=None, corner=1):
    """A classify function for a plain rectangular footprint: pilasters every `bay` blocks along
    each side, counted from the side's low corner (shifted by origin), `pier` blocks wide, windows
    between them. corner: how many columns next to each corner stay solid besides the corner
    itself. fronts: the sides to treat (names); the others are plain wall."""
    xs = [c[0] for c in footprint]
    zs = [c[1] for c in footprint]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)

    def classify(x, z, outs):
        if len(outs) == 2:
            return Pier()
        side = outs[0]
        if fronts is not None and side not in fronts:
            return None
        along, lo, hi = (z, z0, z1) if side in ("east", "west") else (x, x0, x1)
        if along - lo < corner or hi - along < corner:
            return Pier(crest=False)
        k, rest = divmod(along - lo - origin[0 if side in ("north", "south") else 1], bay)
        if rest < pier:
            return Pier()
        return Bay(side, k + 1)

    return classify


# --- laying -----------------------------------------------------------------------------------------
class Laying:
    """One run of build(): the plan, the canvas and what the bands share."""

    def __init__(self, canvas, plan, origin, glass):
        self.c, self.plan, self.o = canvas, plan, origin
        self.glass_of = glass
        self.windows = []

    def put(self, cell, y, state):
        self.c.set(self.o[0] + cell[0], self.o[1] + y, self.o[2] + cell[1], state)

    def clear(self, cell, y):
        self.c.clear(self.o[0] + cell[0], self.o[1] + y, self.o[2] + cell[1])

    def fill(self, cells, y, state):
        for cell in cells:
            self.put(cell, y, state)

    def glass(self, op, storey, default):
        """The block state behind an opening: what the glass function says, else the default."""
        role = self.glass_of(op.front, op.bay, storey) if self.glass_of else None
        role = default if role is None else role
        return role.block if isinstance(role, B.Family) else role

    def mould(self, body, y, stairs, half, only=None):
        """A moulding round `body`: stairs on the columns that touch it, each turned towards it, so
        the profile widens upwards (half "top") or spreads at the foot ("bottom"). A column that
        touches the body by a corner only is turned so that the game makes it the outer corner.
        only: keep the moulding to these columns. Returns the columns it stands on."""
        cells = ring(body) if only is None else ring(body) & set(only)
        facing = {}
        for c in cells:
            near = [d for d in SIDES if step(c, d) in body]
            if near:
                facing[c] = near[0]
        for c in cells - set(facing):
            cands = [d for dx in (-1, 1) for dz in (-1, 1) if (c[0] + dx, c[1] + dz) in body
                     for d in ((dx, 0), (0, dz))]
            turned = [d for d in cands if step(c, d) in facing and (facing[step(c, d)][0] == 0) != (d[0] == 0)]
            facing[c] = (turned or cands)[0]
        for c, d in facing.items():
            self.put(c, y, f"{stairs}[facing={NAME[d]},half={half}]")
        return set(facing)


def rows(y):
    """Rows of a band: a number or a (first, last) pair."""
    return range(y, y + 1) if isinstance(y, int) else range(y[0], y[1] + 1)


class Plinth:
    """The foot of the building: solid to the pilaster plane, so the piers stand on it.

    mat     the plinth's family (deepslate brick for the main-building family)
    inner   the family of the inner leaf (what the rooms see); left out, the plinth's
    vent    a block set into the lowest row under the middle of the bays for which vents(opening)
            holds (an iron grating: the cellar's air)
    """

    def __init__(self, y, mat, inner=None, vent=None, vents=None):
        self.y, self.mat, self.inner = y, mat, inner or mat
        self.vent, self.vents = vent, vents or (lambda op: True)

    def lay(self, s):
        p = s.plan
        for y in rows(self.y):
            s.fill(p.leaf, y, self.inner.block)
            s.fill(p.wall | p.front, y, self.mat.block)
        if self.vent:
            for op in p.openings:
                mid = op.middle()
                if mid is not None and not op.door and self.vents(op):
                    s.put(step(mid, op.out), rows(self.y)[0], self.vent)


class Window:
    """A window type: how a storey opens a bay.

    y        rows of the opening
    head     "flat", or "arch": the two top corners are stairs hung from the lintel, so the head
             steps in by half a block twice (the glass behind stays whole)
    apron    a family for the row under the opening (the sunk panel under a great window)
    grille   a block that stands in the opening, in the wall plane (iron bars)
    recess   how far behind the wall plane the glass stands: 1, or 0 for glass flush with the wall
    dark     the glass where the glass function has nothing to say
    """

    def __init__(self, y, head="flat", apron=None, grille=None, recess=1, dark=B.WINDOW_DARK):
        self.y, self.head, self.apron, self.grille, self.recess, self.dark = y, head, apron, grille, recess, dark

    def cut(self, s, op, storey):
        y0, y1 = self.y
        if op.door and op.door[0] <= y1 and op.door[1] >= y0:
            return                                  # the doorway takes this storey's window
        glass = storey.inner.block if op.blind else s.glass(op, storey.name, self.dark)
        panes = op.behind(self.recess)
        for c, g in zip(op.cells, panes):
            for y in range(y0, y1 + 1):
                if self.recess:
                    if self.grille:
                        s.put(c, y, self.grille)
                    else:
                        s.clear(c, y)
                s.put(g, y, glass)
            if self.apron:
                s.put(c, y0 - 1, self.apron.block)
        if self.head == "arch" and self.recess:
            arch(s, op, y1, storey.wall)
        s.windows.append(dict(front=op.front, bay=op.bay, storey=storey.name, cells=panes,
                              inward=op.inward, y=(y0, y1), blind=op.blind, glass=glass))


def arch(s, op, y, stone):
    """Round the two top corners of an opening: a stair hung from the row above in the first and
    in the last column, its solid quarter towards the jamb."""
    cells = op.cells
    if len(cells) < 2:
        return
    for c, nxt in ((cells[0], cells[1]), (cells[-1], cells[-2])):
        d = (c[0] - nxt[0], c[1] - nxt[1])
        s.put(c, y, f"{stone.stairs}[facing={NAME[d]},half=top]")


class Storey:
    """A storey: wall, piers and one window to the bay.

    name     the storey's key in the windows that build() returns ("base", "main")
    wall     the family of the wall leaf;  inner  that of the inner leaf (left out, the wall's)
    pier     the family of the piers in the pilaster plane; None for a storey without them
    window   a Window, or None for a blind storey
    base, capital   the pilaster's own mouldings in the storey's first and last row: "front" for a
             foot and a head as wide as the pilaster, "wrap" for ones that run round it, None
    """

    def __init__(self, y, name, wall, pier=None, window=None, base=None, capital=None, inner=None):
        self.y, self.name, self.wall, self.pier, self.window = y, name, wall, pier, window
        self.base, self.capital, self.inner = base, capital, inner or wall

    def lay(self, s):
        p = s.plan
        y0, y1 = self.y
        for y in range(y0, y1 + 1):
            s.fill(p.leaf, y, self.inner.block)
            s.fill(p.wall, y, self.wall.block)
            if self.pier:
                s.fill(p.piers, y, self.pier.block)
        if self.pier:
            body = p.body | p.piers
            if self.base:
                s.mould(body, y0, self.pier.stairs, "bottom", only=p.pier_fronts(self.base == "wrap"))
            if self.capital:
                s.mould(body, y1, self.pier.stairs, "top", only=p.pier_fronts(self.capital == "wrap"))
        if self.window:
            for op in p.openings:
                self.window.cut(s, op, self)


class Course:
    """A string course: one row of the wall with a moulding hung along it, which breaks forward
    round every pilaster (wrap) or stops against it."""

    def __init__(self, y, mat, wrap=True, half="top", inner=None):
        self.y, self.mat, self.wrap, self.half, self.inner = y, mat, wrap, half, inner or mat

    def lay(self, s):
        p = s.plan
        s.fill(p.leaf, self.y, self.inner.block)
        s.fill(p.wall | p.piers, self.y, self.mat.block)
        only = None if self.wrap else (p.front - p.piers) | p.pier_fronts(False)
        s.mould(p.body | p.piers, self.y, self.mat.stairs, self.half, only=only)


class Frieze:
    """The band between the window heads and the cornice.

    mat      the family over the bays (sunk panels);  plain  the family over piers and plain wall
    crest    the block over each pilaster of the order (the emblem block), standing forward with it
    key      a family: a console hung under the cornice over the middle of each bay of odd width,
             the keystone of the arch below. None for no keystones
    """

    def __init__(self, y, mat, plain, crest=None, key=None, inner=None):
        self.y, self.mat, self.plain, self.crest, self.key, self.inner = y, mat, plain, crest, key, inner or plain

    def lay(self, s):
        p = s.plan
        s.fill(p.leaf, self.y, self.inner.block)
        s.fill(p.wall, self.y, self.plain.block)
        s.fill(p.piers, self.y, self.plain.block)
        if self.crest:
            s.fill(p.crests, self.y, self.crest)
        for op in p.openings:
            s.fill(op.cells, self.y, self.mat.block)
            mid = op.middle()
            if self.key and mid is not None and len(op.cells) >= 3:
                s.put(step(mid, op.out), self.y, f"{self.key.stairs}[facing={NAME[op.inward]},half=top]")


class Cornice:
    """The cornice: a bed of blocks in the pilaster plane and a moulding hung in front of it
    (reach 2, the main order), or the moulding alone round the wall and its pilasters (reach 1).

    gutter   a family: slabs lying on top of the cornice, in the row above (the copper gutter)
    """

    def __init__(self, y, mat, reach=2, gutter=None, inner=None):
        self.y, self.mat, self.reach, self.gutter, self.inner = y, mat, reach, gutter, inner or mat

    def lay(self, s):
        p = s.plan
        s.fill(p.leaf, self.y, self.inner.block)
        s.fill(p.wall, self.y, self.mat.block)
        if self.reach >= 2:
            s.fill(p.front, self.y, self.mat.block)
            top = p.front | s.mould(p.body | p.front, self.y, self.mat.stairs, "top")
        else:
            s.fill(p.piers, self.y, self.mat.block)
            top = p.piers | s.mould(p.body | p.piers, self.y, self.mat.stairs, "top")
        if self.gutter:
            s.fill(top, self.y + 1, f"{self.gutter.slab}[type=bottom]")


class Parapet:
    """The parapet on the wall line: whole blocks, a coping of slabs in the last row, and over each
    pilaster of the order a post half a block higher.

    rod      a block that stands on the posts for which rods(column) holds, `height` of them
             (the lightning rods); gutter  a family for the inner leaf in the first row: the floor
             of the gutter behind the parapet
    """

    def __init__(self, y, mat, rod=None, rods=None, height=2, gutter=None):
        self.y, self.mat, self.rod, self.rods, self.height, self.gutter = y, mat, rod, rods or (lambda c: True), height, gutter

    def lay(self, s):
        p = s.plan
        y0, y1 = self.y
        for y in range(y0, y1):
            s.fill(p.wall, y, self.mat.block)
        s.fill(p.wall - p.posts, y1, f"{self.mat.slab}[type=bottom]")
        s.fill(p.posts, y1, self.mat.block)
        if self.gutter:
            s.fill(p.leaf, y0, self.gutter.block)
        if self.rod:
            for c in p.posts:
                if self.rods(c):
                    for y in range(y1 + 1, y1 + 1 + self.height):
                        s.put(c, y, f"{self.rod}[facing=up]")


def doorway(s, op):
    """Cut a doorway through both leaves and everything that stands in front of them."""
    y0, y1, stone = op.door
    for c in op.cells:
        for n in (-1, 0, 1, 2):
            for y in range(y0, y1 + 1):
                s.clear(step(c, op.out, n), y)
    if stone is not None:
        arch(s, op, y1, stone)


def build(canvas, plan, order, origin=(0, 0, 0), glass=None):
    """Lay `order` (a list of bands, bottom to top) on `plan`.

    glass(front, bay, storey) -> a window role of the occupancy table (B.WINDOW_LIT, ...) or None
    for the window type's dark glass: which windows are lit is the light line's to say
    (sky/_lightkit.window_lit has this shape).

    Returns the windows glazed, for whoever lights or frames them:
    [dict(front, bay, storey, cells, inward, y, blind, glass)] -- cells are the glass columns (x, z)
    in scene coordinates without the origin, inward the step from the glass into the building, y the
    glass's (bottom, top) rows.
    """
    s = Laying(canvas, plan, origin, glass)
    for band in order:
        band.lay(s)
    for op in plan.openings:
        if op.door:
            doorway(s, op)
    return s.windows


# --- looking at a plan without the game ---------------------------------------------------------------
def drawing(plan, pad=3):
    """The plan as text, north up: # wall line, : inner leaf, P pilaster, w bay column, b blind bay
    column, D doorway, + the cornice's reach."""
    marks = {}
    for c in plan.far:
        marks[c] = "+"
    for c in plan.leaf:
        marks[c] = ":"
    for c in plan.wall:
        marks[c] = "#"
    for c in plan.piers:
        marks[c] = "P"
    for op in plan.openings:
        for c in op.cells:
            marks[c] = "D" if op.door else "b" if op.blind else "w"
    xs = [c[0] for c in marks]
    zs = [c[1] for c in marks]
    x0, x1 = min(xs) - pad + 2, max(xs) + pad - 2
    lines = ["       x " + "".join("%d" % (abs(x) % 10) for x in range(x0, x1 + 1))]
    for z in range(min(zs), max(zs) + 1):
        lines.append("z %4d  %s" % (z, "".join(marks.get((x, z), " ") for x in range(x0, x1 + 1)).rstrip()))
    return "\n".join(lines)
