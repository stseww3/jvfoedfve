"""Test scene of the work package materials/ashlar (plan/packages/materials/ashlar.md).

What it is for: to see the grey-white stone of the sandstone family -- the rusticated base, the
dressed coursed walls, the sunk panel and the emblem block -- in every shape, and to check the
things the card and c190's pre-review call for:

  - stones     the four stones side by side (materials/_board.stone): each family with its stairs,
               slabs and (rough) wall, and the panel/emblem stacked over a fine wall;
  - walls      an eight-by-eight wall of each of the four, the families with their shaped blocks at
               the foot, to read close for the joints and tooling and from twenty blocks for stripes;
  - coursed    a facade band in the one wall plane: a slate plinth, a rusticated base storey, a
               string course standing proud, then the dressed storey with sunk panels and emblem
               blocks -- the rough below and the fine above must read as one stone across the course
               (c190 #2);
  - flight     a flight of fine stairs and a coping run, to be read from straight above: a tread and
               a coping carry no bed joint (c190 #1).

This scene renders version a (the drawn ashlar). obs_mat_ashlar_b and obs_mat_ashlar_c render the
other two versions over the same board and the same shots (the three-way compare the card asks for).

    python -m scenes.obs_mat_ashlar      writes shots.json from the layout below
"""
from artkit.blocks import st
from artkit.canvas import Canvas

from scenes.obs import materials  # noqa: F401  (kept so the scene reads like its siblings)
from scenes.obs.common import blocks as B
from scenes.obs.materials import _board
from scenes.obs.materials import _kit as K

BIOME = "obs_blue"
CATEGORY = "materials"
Z = 0
TIME = 14000        # the default light version (sky line)
VERSION = "a"       # the drawn ashlar; obs_mat_ashlar_b / _c compare b and c


WALLS = (("rough", B.ASHLAR_ROUGH), ("fine", B.ASHLAR_FINE), ("panel", B.ASHLAR_PANEL), ("emblem", B.ASHLAR_EMBLEM))
WALL, PITCH = 8, 10     # a wall is WALL by WALL; x from one wall to the next


def walls(c, x, z):
    """An eight-by-eight wall of each of the four stones, a gap between them, the families with
    their shaped blocks at the foot: close for the joints and the tooling, from twenty blocks for
    stripes. The panel and the emblem are accents on a facade, but a frieze sets them in a row, and
    a whole wall of each is where a repeat that stripes would show."""
    for i, (_, what) in enumerate(WALLS):
        _board.wall(c, what, x + PITCH * i, 0, z, n=WALL)       # its stairs/slabs/low wall at z + 1
    last = x + PITCH * (len(WALLS) - 1) + WALL - 1
    _board.stage(c, x, last, z, height=WALL + 1)
    return last + 2


def coursed(c, x, z):
    """A facade band as ART-PLAN 5.1 stacks it, base and main storey in the one wall plane: a slate
    plinth, a rusticated base storey, a string course standing one proud of the wall, then the
    dressed storey with sunk panels under the windows and emblem blocks at the top.

    The course is an upside-down fine stair -- a shelf over a half-deep fascia -- set exactly on the
    change from rough to fine, so it takes the jump from the two-pixel joint to the one-pixel joint
    and the two finishes read as one stone, split on purpose (c190 #2). The stage's lamps light the
    foot of the band, so the base storey and the first courses of the dressed one stand in the one
    light; higher up the stone is seen as the night sky lights it."""
    w, top = 7, 12
    c.box(x, 0, z, x + w - 1, 0, z, B.SLATE_BRICK.block)                 # plinth
    c.box(x, 1, z, x + w - 1, 4, z, B.ASHLAR_ROUGH.block)                # rusticated base storey
    c.box(x, 5, z, x + w - 1, top, z, B.ASHLAR_FINE.block)               # dressed storey, the same plane
    for dx in range(w):                                                   # the string course, one proud
        c.set(x + dx, 5, z + 1, st(B.ASHLAR_FINE.stairs, facing="north", half="top"))
    for dx in (1, 2, 4, 5):                                              # sunk panels under the windows
        c.set(x + dx, 8, z, B.ASHLAR_PANEL.block)
    for dx in (0, 3, 6):                                                 # emblem blocks at the top
        c.set(x + dx, top, z, B.ASHLAR_EMBLEM)
    _board.stage(c, x, x + w - 1, z, height=top + 2)
    return x + w + 2


def flight(c, x, z):
    """A flight of fine stairs climbing north and a coping run beside it, to be read from straight
    above: the treads (fine) and the copings (fine, and a rough one to compare) carry no bed joint."""
    for i in range(5):                                  # the flight, each step up and one north
        zz = z - i
        for dx in (0, 1):
            c.set(x + dx, i, zz, st(B.ASHLAR_FINE.stairs, facing="south"))
        if i:
            c.box(x, 0, zz, x + 1, i - 1, zz, B.ASHLAR_FINE.block)
    c.box(x + 3, 0, z - 4, x + 4, 1, z, B.ASHLAR_FINE.block)             # a low wall to cap
    for dz in range(5):                                                  # the copings
        c.set(x + 3, 2, z - dz, st(B.ASHLAR_FINE.slab, type="bottom"))
        c.set(x + 4, 2, z - dz, st(B.ASHLAR_ROUGH.slab, type="bottom"))
    _board.stage(c, x, x + 5, z, height=7)
    return x + 7


STATIONS = [("stones", _board.stone), ("walls", walls), ("coursed", coursed), ("flight", flight)]


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
    return K.pack_with(pack_dir, ashlar=VERSION)


def shots():
    """Camera positions from the layout: the four stones in halves (the split, the joints), each
    eight-by-eight wall close and the four from twenty blocks (stripes), the coursed band face-on
    (rough and fine as one stone) and its string course from the ground, the fine treads and the
    copings from above."""
    spans = layout()
    out = []

    def front(name, x0, x1, y=1.6, time=TIME):
        d = max(5.0, (x1 - x0 + 2) / 2.6)
        out.append({"name": name, "pos": [(x0 + x1) / 2.0, y + 1.2, round(Z + 1 + d, 1)],
                    "look_at": [(x0 + x1) / 2.0, y, Z], "time": time})

    x0, x1 = spans["stones"]
    x1 -= 2
    mid = (x0 + x1) // 2
    front("stones_a", x0, mid)                                  # the split and the shapes, read close
    front("stones_b", mid, x1)

    xw = spans["walls"][0]
    for i, (name, _) in enumerate(WALLS):                       # each wall face-on, close
        xc = xw + PITCH * i + WALL / 2.0
        out.append({"name": f"wall_{name}", "pos": [xc, 4.6, Z + 8.5], "look_at": [xc, 4.0, Z], "time": TIME})
    xc = xw + (PITCH * (len(WALLS) - 1) + WALL) / 2.0           # the four of them from twenty blocks
    out.append({"name": "walls_far", "pos": [xc, 5.0, Z + 20.0], "look_at": [xc, 4.0, Z], "time": TIME})

    xc0, xc1 = spans["coursed"]
    xc1 -= 2
    xm = (xc0 + xc1) / 2.0
    out.append({"name": "coursed", "pos": [xm, 6.5, Z + 12.0], "look_at": [xm, 6.0, Z], "time": TIME})
    # the string course as someone on the ground sees it: from below and a little to one side, so
    # its shelf, its fascia and its plain soffit all show, with the rough under it and the fine over
    out.append({"name": "coursed_course", "pos": [xm - 2.5, 2.6, Z + 6.5], "look_at": [xm + 0.5, 5.2, Z + 0.5],
                "time": TIME})

    xf = spans["flight"][0]
    out.append({"name": "flight_treads", "pos": [xf + 1.0, 7.5, Z + 3.0], "look_at": [xf + 1.0, 1.0, Z - 3.0],
                "time": TIME})
    out.append({"name": "flight_copings", "pos": [xf + 3.5, 6.5, Z + 2.5], "look_at": [xf + 3.5, 1.5, Z - 2.0],
                "time": TIME})
    return out
