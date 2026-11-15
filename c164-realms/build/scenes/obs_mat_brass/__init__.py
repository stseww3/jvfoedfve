"""Test scene of the work package materials/brass-oldcopper-small
(plan/packages/materials/brass-oldcopper-small.md).

What it is for:
  brass   the whole brass family and the small pieces side by side under the sample lamps: plate,
          chequer plate, pipe, railing, gate, the half-glazed door, hatch, button, shelf, the brass
          plaque and the enamel nameplate (on a wall, on a post, on chains), the panelling, and a
          run of whole cells of brass plate in the floor. Does the brass read as one set?
  plates  the split: old copper (waxed exposed) beside the unwaxed exposed copper it shares its files
          with, which must stay the game's; the cast iron and verdigris pairs are in the same row.
  emblem  the thin brass line let into the paving, close and under lamps: a small emblem (ring,
          meridian, star), its west half on polished tuff and its east half on slate tiles, the
          lightest and the darkest paving it will lie in; three whole cells of brass plate beside it.
  court   a piece of the front court laid the way site/court lays it -- slate paving, the meridian
          between its two flanks, the ring and the star of the emblem on the dark disc -- with no lamp
          near: the line under the night sky alone, where it has to be a dark metal in the stone
          and not a yellow band.
  roof    a curved sheet of copper the way the roofs are built (blocks, stairs, slabs): half of it old
          copper, half the verdigris of the domes, on a stone cornice with the old copper gutter the
          main building has all round. Sky light only.
  walls   eight by eight of the brass plate, the chequer plate, old copper and its cut plate, to be
          read close and from twenty blocks for stripes.

How a line is laid (line() and ring() below can be copied): a cell of BRASS_LINE joins two of its
sides and its shape names them -- north_south, east_west, or one of the four corners. A corner is
drawn as a diagonal from the middle of one side to the middle of the next, so a path that steps
sideways every cell, as a circle of blocks does, is one straight slant. Where two lines cross lies
a BRASS_CROSS, and the star is one cell of BRASS_STAR. In the game they are rails, so (S2, 11-14):
  - the cell under a line is a whole solid block: a rail drops off a slab or a stair;
  - a cell of line has line in exactly the two neighbours its shape names. The game turns a rail
    towards the rails beside it when it is put down: two lines never lie in cells side by side,
    and the star keeps a cell clear of any line;
  - which way a crossing or a star lies is the game's choice, so their pictures are the same
    turned a quarter.

    python -m scenes.obs_mat_brass        writes shots.json from the layout below
"""
import math

from artkit.blocks import st
from artkit.canvas import Canvas, Mix

from scenes.obs import materials
from scenes.obs.common import blocks as B
from scenes.obs.materials import _board

BIOME = "obs_blue"
Z = 0
TIME = 14000        # the default light version (sky line)

# the court, as site/court.py has it
FIELD = Mix({B.SLATE_SMOOTH.block: 12, B.SLATE_BRICK.block: 3, B.SLATE_TILE.block: 1}, seed=41)
STRIP = B.TUFF_SMOOTH.block
DISC = B.SLATE_TILE.block
RING = 7
STAR = (3, -3)
COURT_W = 2 * RING + 5          # the ring, a clear cell and a margin either side
COURT_N, COURT_S = 14, 8        # how far the court piece reaches north and south of the station's z
ROUNDEL = -3                    # z of the ring's middle from the station's z

# the small emblem under the lamps: the star 0.4 of the radius right and up of the middle (A0, 11-14)
EMBLEM = 5
EMBLEM_STAR = (2, -2)
EMBLEM_W = 2 * EMBLEM + 5       # the ring, a clear cell and a margin either side
EMBLEM_D = 2 * EMBLEM + 5       # and as deep: the meridian runs two cells out of the ring
DARK = 14                       # clear ground east of its lamps, so none of their light reaches the court

# the roof: (blocks under the cap, the cap) of each column, from the eave northwards
HAUNCH = ((2, "stairs"), (3, "stairs"), (4, "slab"), (4, "slab"), (5, None), (5, None))
ROOF_W = 12
WALL_H = 2                      # the stone wall the roof sits on


SIDES = {(0, -1): "north", (0, 1): "south", (-1, 0): "west", (1, 0): "east"}
ACROSS = {"north": "south", "south": "north", "west": "east", "east": "west"}
SHAPES = {frozenset(pair): "_".join(pair) for pair in (("north", "south"), ("east", "west"), ("south", "east"),
                                                         ("south", "west"), ("north", "west"), ("north", "east"))}


def line(cells, closed=False):
    """The thin brass line along `cells`, a path of (x, z) in which every cell touches the next by a
    side: {(x, z): block state}. The end of an open path runs straight out of its cell."""
    out = {}
    for i, (x, z) in enumerate(cells):
        sides = set()
        for j in (i - 1, i + 1):
            if closed or 0 <= j < len(cells):
                other = cells[j % len(cells)]
                sides.add(SIDES[(other[0] - x, other[1] - z)])
        if len(sides) == 1:
            sides.add(ACROSS[min(sides)])
        out[(x, z)] = st(B.BRASS_LINE, shape=SHAPES[frozenset(sides)])
    return out


def ring(r):
    """A circle of radius r about (0, 0) as a closed path of cells that touch by their sides: where
    the circle of blocks steps diagonally, the path goes round by the outer of the two cells."""
    cells = []
    count = 16 * r
    for k in range(count + 1):
        a = 2 * math.pi * k / count
        cell = (round(r * math.cos(a)), round(r * math.sin(a)))
        if cells and cell == cells[-1]:
            continue
        if cells and abs(cell[0] - cells[-1][0]) + abs(cell[1] - cells[-1][1]) == 2:
            cells.append(max((cell[0], cells[-1][1]), (cells[-1][0], cell[1]), key=lambda at: math.hypot(*at)))
        cells.append(cell)
    return cells[:-1]               # the last is the first again


def emblem_lines(c, mx, az, r, star, z0, z1):
    """The emblem as site/court draws it, in thin line: the meridian at x = mx from z0 to z1, the
    ring of radius r about (mx, az) with a crossing where the meridian passes through it, the star.
    The middle cell stays empty (the armillary stands there)."""
    for z in range(z0, z1 + 1):
        if z != az:
            c.set(mx, 0, z, st(B.BRASS_LINE, shape="north_south"))
    for (dx, dz), state in line(ring(r), closed=True).items():
        c.set(mx + dx, 0, az + dz, st(B.BRASS_CROSS, shape="north_south") if dx == 0 else state)
    c.set(mx + star[0], 0, az + star[1], st(B.BRASS_STAR, shape="north_south"))


def emblem(c, x, z):
    """The line close and lit: a small emblem, its west half on polished tuff and its east half on
    slate tiles, so the line is seen on the lightest and on the darkest paving. Lamps overhead."""
    x1, z1 = x + EMBLEM_W - 1, z + EMBLEM_D - 1
    mx, az = x + EMBLEM_W // 2, z + EMBLEM_D // 2
    c.box(x - 1, -1, z - 1, x1 + 1, -1, z1 + 1, _board.FLOOR)
    c.box(x - 1, 0, z - 1, x1 + 1, 2, z - 1, _board.BACK)
    c.box(mx + 1, -1, z, x1 + 1, -1, z1 + 1, DISC)
    emblem_lines(c, mx, az, EMBLEM, EMBLEM_STAR, z, z1)
    c.box(x1, 0, az - 1, x1, 0, az + 1, B.BRASS_INLAY)             # whole cells of plate, to compare
    for lx in range(x + 1, x1 + 1, 4):
        for lz in range(z + 2, z1 + 1, 4):
            c.set(lx, 2, lz, st(B.LIGHT, level=15))
    return x1 + DARK


def court(c, x, z):
    """Slate paving with the meridian and the emblem, no lamps."""
    mx = x + COURT_W // 2
    for px in range(x, x + COURT_W):
        for pz in range(z - COURT_N, z + COURT_S + 1):
            c.set(px, -1, pz, FIELD)
    for pz in range(z - COURT_N, z + COURT_S + 1):       # the two flanks of the meridian
        for px in (mx - 1, mx, mx + 1):
            c.set(px, -1, pz, STRIP)
    az = z + ROUNDEL
    for dx in range(-RING, RING + 1):
        for dz in range(-RING, RING + 1):
            if math.hypot(dx, dz) < RING + 0.5:
                c.set(mx + dx, -1, az + dz, DISC)
    emblem_lines(c, mx, az, RING, STAR, z - COURT_N, z + COURT_S)
    return x + COURT_W + 1


def roof(c, x, z):
    """A curved sheet rising to the north off a stone wall: old copper on the left half, verdigris
    on the right, a plain old copper capping along the top, and along the eave the stone cornice
    carrying the old copper gutter (main/facade: a stair upside down, the cut slab on it)."""
    c.box(x - 1, -1, z - len(HAUNCH) - 1, x + ROOF_W, -1, z + 7, _board.FLOOR)
    for i in range(ROOF_W):
        skin = B.OLD_COPPER_CUT if i < ROOF_W // 2 else B.VERDIGRIS_CUT
        px = x + i
        for d, (full, cap) in enumerate(HAUNCH):
            pz = z - d
            c.box(px, 0, pz, px, WALL_H - 1, pz, B.ASHLAR_FINE.block if d == 0 else _board.BACK)
            top = B.OLD_COPPER if d == len(HAUNCH) - 1 else skin.block
            c.box(px, WALL_H, pz, px, WALL_H + full - 1, pz, top)
            if cap == "stairs":
                c.set(px, WALL_H + full, pz, st(skin.stairs, facing="north"))
            elif cap == "slab":
                c.set(px, WALL_H + full, pz, st(skin.slab, type="bottom"))
        c.set(px, WALL_H - 1, z + 1, st(B.ASHLAR_FINE.stairs, facing="north", half="top"))
        c.set(px, WALL_H, z + 1, st(B.OLD_COPPER_CUT.slab, type="bottom"))
    return x + ROOF_W + 1


WALLS = (("plate", B.BRASS_PLATE), ("tread", B.BRASS_PATTERN), ("copper", B.OLD_COPPER), ("cut", B.OLD_COPPER_CUT))


def walls(c, x, z):
    """Four eight-by-eight walls for the stripe check, the shaped blocks of each family at its foot."""
    for i, (_, what) in enumerate(WALLS):
        _board.wall(c, what, x + 10 * i, 0, z)
    end = x + 10 * (len(WALLS) - 1) + 7
    _board.stage(c, x, end, z, height=9)
    return end + 2


STATIONS = [("brass", _board.brass), ("plates", _board.twins_plates), ("emblem", emblem), ("court", court),
            ("roof", roof), ("walls", walls)]


def layout(c=None):
    """Where each station stands: {name: (first x, x after it)}. Builds into `c` when given one."""
    c = c or Canvas()
    spans, x = {}, 0
    for name, station in STATIONS:
        end = station(c, x, Z)
        spans[name] = (x, end)
        x = end + 2
    return spans


def build():
    c = Canvas()
    layout(c)
    return c


def build_models():
    return {}           # blocks only


def write_pack(pack_dir):
    return materials.pack(pack_dir)


def shots():
    """Camera positions from the layout: the brass row in halves and its small pieces close, the
    old copper split, the thin line close under the lamps, the court from above, from a walker's
    height and straight down, the roof and its gutter, each wall close and the walls from twenty
    blocks."""
    spans = layout()
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 1) for v in pos], "look_at": [round(v, 1) for v in look_at],
                    "time": TIME})

    def front(name, x0, x1, y=1.6):
        """Looking north at x0..x1 from as near as shows all of it."""
        d = max(5.0, (x1 - x0 + 2) / 2.6)
        shot(name, ((x0 + x1) / 2.0, y + 1.2, Z + 1 + d), ((x0 + x1) / 2.0, y, Z))

    xb = spans["brass"][0]
    front("brass_a", xb, xb + 16)                       # plate, chequer plate, pipe, rail, gate, door, hatch
    front("brass_b", xb + 17, xb + 30)                  # button, shelf, plaques, panelling, signs
    front("brass_door", xb + 11.5, xb + 17, y=1.0)
    front("brass_wall", xb + 18, xb + 25, y=1.0)
    front("brass_signs", xb + 25.5, xb + 30.5, y=1.0)
    shot("brass_line", (xb + 10.5, 3.0, Z + 6.0), (xb + 10.5, 0.0, Z + 1.5))
    xp = spans["plates"][0]
    front("plates_a", xp, xp + 14)
    front("plates_b", xp + 15, xp + 31)
    front("copper_twins", xp + 19.5, xp + 29.5)         # old copper | exposed copper, the cut family likewise
    xe, ze = spans["emblem"][0] + EMBLEM_W / 2.0, Z + EMBLEM_D / 2.0
    shot("emblem", (xe, 11.0, ze + 11.0), (xe, 0.0, ze + 0.5))
    shot("emblem_down", (xe, 16.0, ze + 0.6), (xe, 0.0, ze))
    shot("emblem_walk", (xe + 3.0, 1.7, ze + EMBLEM + 3.5), (xe - 0.5, 0.0, ze))
    shot("emblem_close", (xe + 1.5, 2.2, ze + EMBLEM + 2.5), (xe + 0.2, 0.0, ze + EMBLEM - 0.5))
    xc = spans["court"][0] + COURT_W / 2.0
    az = Z + ROUNDEL + 0.5
    shot("court", (xc, 9.0, Z + COURT_S + 6.0), (xc, 0.0, az))
    shot("court_walk", (xc + 3.0, 1.7, Z + COURT_S), (xc - 0.5, 0.0, az - 2.0))
    shot("court_down", (xc, 19.0, az + 1.5), (xc, 0.0, az))
    xr = spans["roof"][0] + ROOF_W / 2.0
    shot("roof", (xr, 5.0, Z + 11.0), (xr, 4.5, Z - 2.0))
    shot("roof_gutter", (xr + 2.5, 3.6, Z + 4.5), (xr - 0.5, 2.6, Z + 0.5))
    xw = spans["walls"][0]
    for i, (name, _) in enumerate(WALLS):
        shot(f"wall_{name}", (xw + 10 * i + 4.0, 4.6, Z + 8.5), (xw + 10 * i + 4.0, 4.0, Z))
    shot("walls_far_brass", (xw + 9.0, 5.0, Z + 20.0), (xw + 9.0, 4.0, Z))
    shot("walls_far_copper", (xw + 29.0, 5.0, Z + 20.0), (xw + 29.0, 4.0, Z))
    shot("wall_treads", (xw + 9.0, 4.2, Z + 4.6), (xw + 9.0, 0.2, Z + 1.0))
    return out
