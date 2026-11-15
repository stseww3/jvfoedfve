"""Test scene of the work package materials/snow (plan/packages/materials/snow.md).

What it is for:
  order   what the director asked for (A0 #29065): a short piece of the mountain -- its rocks in
          their beds, three shelves, snow on them one to three layers deep, thinning towards the
          edge -- and beside it a wall of the front's stone behind its kerb and a block of dark
          slate, all in one view under the sky alone. Rock darkest, snow between, the building's
          stone lightest: the order is measured here, on the faces that look up and on the
          faces that look at the viewer.
  layers  every depth of snow, one layer to eight, and the whole block, in a row at the foot of a
          rock face: the sides. The rim along the foot, the field above it.
  field   a sheet of one layer ten by ten on the rock and a wall of whole blocks eight by eight:
          the field close, straight from above and from twenty blocks, for stripes and repeats.

No lamp anywhere: the snow lies on the mountain, away from every lamp, and the sky lights it.

    python -m scenes.obs_mat_snow        writes shots.json from the layout below
"""
from artkit.blocks import st
from artkit.canvas import Canvas, hash3

from scenes.obs import materials
from scenes.obs.common import blocks as B
from scenes.obs.materials import _board

BIOME = "obs_blue"
CATEGORY = "materials"
Z = 0
TIME = 14000        # the default light version (sky line)
DUSK = 12900        # light version C, the lightest of the three: the order once more

# the mountain's rock as site/terrain lays it: beds from the top down, a few flecks of a kindred rock
DEEP, COBBLED, TUFF, STONE = B.ROCK_DEEPSLATE, B.ROCK_COBBLED.block, B.TUFF.block, B.ROCK_STONE.block
BEDS = ((DEEP, 3), (TUFF, 1), (DEEP, 2), (COBBLED, 1), (TUFF, 2), (DEEP, 3), (STONE, 1))
FLECKS = {DEEP: (COBBLED, 0.10), COBBLED: (DEEP, 0.15), TUFF: (COBBLED, 0.08), STONE: (COBBLED, 0.20)}
ROWS = [rock for rock, thick in BEDS for _ in range(thick)]
PHASE = 4           # which bed lies at y 0: set so that the floor and the three shelves are the dark rock
GROUND = -1         # y of the floor everything stands on

# the slope: three shelves, each (y of its rock, cells deep), from the front northwards, and the cliff behind
SLOPE_W = 14
SHELVES = ((0, 4), (2, 4), (6, 3))
CLIFF_TOP = 9
DEPTH = (3, 2, 1)   # layers of snow by how far a cell is from the foot of the cliff behind it; further out, bare

WALL_W, WALL_H = 6, 5       # the wall of the front's stone
SLATE_W, SLATE_H = 3, 2     # the block of slate

SHEET = 10          # the sheet of one layer
WALL = 8            # the wall of whole blocks


def rock(x, y, z):
    """The rock of a cell: its bed by its height, with a few flecks."""
    bed = ROWS[(PHASE - y) % len(ROWS)]
    other, share = FLECKS[bed]
    return other if hash3(x, y, z, 164) < share else bed


def ground(c, x0, x1, z0, z1):
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            c.set(x, GROUND, z, rock(x, GROUND, z), keep=True)


def column(c, x, top, z):
    for y in range(GROUND, top + 1):
        c.set(x, y, z, rock(x, y, z))


def slope(c, x, z):
    """A piece of the mountain rising to the north: shelves with cliffs between them, the line of
    each cliff stepping a cell in and out, and snow on the shelves as the terrain lays it -- deepest
    at the foot of the cliff, a layer less with every cell outwards, the outer edge bare, and here
    and there a gap of bare rock between two drifts."""
    for i in range(SLOPE_W):
        px, k = x + i, 0
        for n, (top, deep) in enumerate(SHELVES):
            deep += int(hash3(px // 2, n, 0, 7) < 0.45)                 # the cliff behind it a cell further back
            shift = int(hash3((px + 1) // 2, n, 2, 7) < 0.35)           # a drift a cell further out
            bare = hash3(px // 3, n, 3, 7) < 0.22                       # no drift here at all
            for j in range(deep):
                pz = z - k - j
                column(c, px, top, pz)
                out = deep - 1 - j - shift                              # cells from the cliff's foot
                if not bare and out < len(DEPTH):
                    c.set(px, top + 1, pz, st(B.SNOW_LAYER, layers=DEPTH[max(out, 0)]))
            k += deep
        for j in range(2):                                              # the cliff behind the last shelf
            column(c, px, CLIFF_TOP, z - k - j)
    return x + SLOPE_W


def stones(c, x, z):
    """Beside the slope: a wall of the front's dressed stone with a kerb of it in front (a face
    that looks at the viewer and one that looks up), and a block of the terraces' dark slate."""
    c.box(x, 0, z - 3, x + WALL_W - 1, WALL_H - 1, z - 3, B.ASHLAR_FINE.block)
    c.box(x, 0, z, x + WALL_W - 1, 0, z, B.ASHLAR_FINE.block)
    x += WALL_W + 2
    c.box(x, 0, z - 3, x + SLATE_W - 1, SLATE_H - 1, z - 1, B.SLATE_SMOOTH.block)
    return x + SLATE_W


def order(c, x, z):
    end = stones(c, slope(c, x, z) + 2, z)
    ground(c, x - 2, end + 1, z - 16, z + 5)
    return end + 3


def layers(c, x, z):
    """One to eight layers and the whole block, two cells of each with a cell of bare rock between,
    on a bench at the foot of a rock face."""
    end = x + 3 * 9 - 2
    for px in range(x - 1, end + 2):
        column(c, px, 3, z - 1)
        column(c, px, 0, z)
    for n in range(1, 10):
        for px in (x + 3 * (n - 1), x + 3 * (n - 1) + 1):
            c.set(px, 1, z, st(B.SNOW_LAYER, layers=n) if n <= 8 else B.SNOW)
    ground(c, x - 2, end + 2, z - 1, z + 6)
    return end + 4


def field(c, x, z):
    """A sheet of one layer on the rock, and behind its far end a wall of whole blocks."""
    ground(c, x - 1, x + SHEET + WALL + 3, z - SHEET - 1, z + 6)
    c.box(x, 0, z - SHEET + 1, x + SHEET - 1, 0, z, st(B.SNOW_LAYER, layers=1))
    _board.wall(c, B.SNOW, x + SHEET + 2, 0, z - 3, n=WALL)
    return x + SHEET + WALL + 5


STATIONS = [("order", order), ("layers", layers), ("field", field)]


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
    """Camera positions from the layout: the order from the front, at dusk and from above; the
    slope close, along a shelf and at the rim of thin snow; the row of depths; the sheet straight
    down, at a walker's height and with the wall from twenty blocks; the wall close."""
    spans = layout()
    out = []

    def shot(name, pos, look_at, time=TIME):
        out.append({"name": name, "pos": [round(v, 1) for v in pos], "look_at": [round(v, 1) for v in look_at],
                    "time": time})

    xo = spans["order"][0]
    mid = (xo + spans["order"][1] - 3) / 2.0                        # the middle of slope, wall and slate
    shot("order", (mid, 6.5, Z + 13.0), (mid, 2.0, Z - 4.0))
    shot("order_dusk", (mid, 6.5, Z + 13.0), (mid, 2.0, Z - 4.0), time=DUSK)
    shot("order_down", (mid, 24.0, Z + 3.0), (mid, 0.0, Z - 4.0))
    xs = xo + SLOPE_W / 2.0
    shot("slope", (xs, 9.0, Z + 8.0), (xs, 2.5, Z - 5.0))
    shot("slope_along", (xo + 0.5, 2.8, Z - 1.5), (xo + 9.0, 1.0, Z - 2.5))     # standing on the first shelf
    shot("rim", (xs - 1.0, 1.9, Z + 3.5), (xs - 1.0, 1.0, Z - 0.5))
    xl = spans["layers"][0]
    shot("layers", (xl + 12.5, 3.0, Z + 11.0), (xl + 12.5, 1.2, Z))
    shot("layers_thin", (xl + 5.0, 2.4, Z + 4.5), (xl + 5.0, 1.1, Z))            # one to four layers
    shot("layers_deep", (xl + 18.5, 2.6, Z + 5.5), (xl + 18.5, 1.4, Z))          # five to eight, the whole block
    xf = spans["field"][0]
    xm, zm = xf + SHEET / 2.0, Z - SHEET / 2.0 + 1.0
    shot("field_down", (xm, 13.0, zm + 0.6), (xm, 0.0, zm))
    shot("field_walk", (xf + 1.0, 1.8, Z + 2.5), (xf + 7.0, 0.0, Z - 6.0))
    xw = xf + SHEET + 2 + WALL / 2.0
    shot("wall_snow", (xw, 4.6, Z + 5.5), (xw, 4.0, Z - 3.0))
    shot("field_far", (xf + SHEET + 1.0, 5.0, Z + 17.0), (xf + SHEET + 1.0, 3.0, Z - 3.0))
    return out
