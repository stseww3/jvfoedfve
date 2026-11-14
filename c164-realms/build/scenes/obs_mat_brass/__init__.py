"""Test scene of the work package materials/brass-oldcopper-small
(plan/packages/materials/brass-oldcopper-small.md).

What it is for:
  brass   the whole brass family and the small pieces side by side under the sample lamps: plate,
          chequer plate, pipe, railing, gate, the half-glazed door, hatch, button, shelf, the brass
          plaque and the enamel nameplate (on a wall, on a post, on chains), the panelling, and a
          run of the brass line in the floor. Does the brass read as one set?
  plates  the split: old copper (waxed exposed) beside the unwaxed exposed copper it shares its files
          with, which must stay the game's; the cast iron and verdigris pairs are in the same row.
  court   a piece of the front court laid the way site/court lays it -- slate paving, the meridian
          between its two flanks, the ring and the star of the emblem on the dark disc -- with no lamp
          near: the brass line under the night sky alone, where it has to be a dark metal.
  roof    a curved sheet of copper the way the roofs are built (blocks, stairs, slabs): half of it old
          copper, half the verdigris of the domes, on a stone cornice with the old copper gutter the
          main building has all round. Sky light only.
  walls   eight by eight of the brass plate, the chequer plate, old copper and its cut plate, to be
          read close and from twenty blocks for stripes.

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

# the roof: (blocks under the cap, the cap) of each column, from the eave northwards
HAUNCH = ((2, "stairs"), (3, "stairs"), (4, "slab"), (4, "slab"), (5, None), (5, None))
ROOF_W = 12
WALL_H = 2                      # the stone wall the roof sits on


def court(c, x, z):
    """Slate paving with the meridian and the emblem, no lamps."""
    mx = x + COURT_W // 2
    for px in range(x, x + COURT_W):
        for pz in range(z - COURT_N, z + COURT_S + 1):
            c.set(px, -1, pz, FIELD)
    for pz in range(z - COURT_N, z + COURT_S + 1):       # the line and its two flanks
        for px in (mx - 1, mx, mx + 1):
            c.set(px, -1, pz, STRIP)
        c.set(mx, 0, pz, B.BRASS_INLAY)
    az = z + ROUNDEL
    for dx in range(-RING, RING + 1):
        for dz in range(-RING, RING + 1):
            d = math.hypot(dx, dz)
            if d >= RING + 0.5:
                continue
            c.set(mx + dx, -1, az + dz, DISC)
            c.clear(mx + dx, 0, az + dz)
            if d >= RING - 0.5 or (dx == 0 and dz != 0):
                c.set(mx + dx, 0, az + dz, B.BRASS_INLAY)
    for dx, dz in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        c.set(mx + STAR[0] + dx, 0, az + STAR[1] + dz, B.BRASS_INLAY)
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


STATIONS = [("brass", _board.brass), ("plates", _board.twins_plates), ("court", court), ("roof", roof),
            ("walls", walls)]


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
    old copper split, the court from above, from a walker's height and straight down, the roof
    and its gutter, each wall close and the walls from twenty blocks."""
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
