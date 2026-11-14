"""Test scene of the work package materials/ashlar (plan/packages/materials/ashlar.md).

What it is for: to see the grey-white stone of the sandstone family -- the rusticated base, the
dressed coursed walls, the sunk panel and the emblem block -- in every shape, and to check the
things the card and c190's pre-review call for:

  - stones     the four stones side by side (materials/_board.stone): each family with its stairs,
               slabs and (rough) wall, and the panel/emblem stacked over a fine wall;
  - walls      an eight-by-eight wall of rough and of fine with their shaped blocks at the foot, to
               read close for the joints and tooling and from twenty blocks for stripes;
  - coursed    a facade band: a slate plinth, a rusticated base storey, a projecting string course,
               then the dressed storey with sunk panels under the windows and emblem lintels -- the
               rough below and the fine above must read as one stone across the course (c190 #2);
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


def walls(c, x, z):
    """An eight-by-eight wall of rough and of fine, each with its shaped blocks at the foot, a gap
    between them: close for the joints, from twenty blocks for stripes."""
    _board.wall(c, B.ASHLAR_ROUGH, x, 0, z)             # x..x+7, stairs/slabs/wall at z+1
    _board.wall(c, B.ASHLAR_FINE, x + 10, 0, z)         # x+10..x+17
    _board.stage(c, x, x + 17, z, height=9)
    return x + 19


def coursed(c, x, z):
    """A facade band (ART-PLAN 5.1): a slate plinth, two courses of rusticated stone, a projecting
    string course of fine stone, then the dressed storey with sunk panels under the windows and
    emblem lintels over. Rough and fine stand in the one plane under the one light, so the band is a
    fair test that the two finishes read as one stone (c190 #2); only the course steps out."""
    w = 7
    c.box(x, 0, z, x + w - 1, 0, z, B.SLATE_BRICK.block)                 # plinth
    c.box(x, 1, z, x + w - 1, 4, z, B.ASHLAR_ROUGH.block)                # rusticated base storey
    for dx in range(w):                                                   # the string course, a projecting band
        c.set(x + dx, 5, z, st(B.ASHLAR_FINE.stairs, facing="south", half="top"))
    c.box(x, 6, z, x + w - 1, 12, z, B.ASHLAR_FINE.block)                # dressed storey, the one plane
    for dx in (1, 2, 4, 5):                                              # sunk panels under the windows
        c.set(x + dx, 8, z, B.ASHLAR_PANEL.block)
    for dx in (0, 3, 6):                                                 # emblem lintels over
        c.set(x + dx, 12, z, B.ASHLAR_EMBLEM)
    _board.stage(c, x, x + w - 1, z, height=14)
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
    eight-by-eight wall close and both from twenty blocks (stripes), the fine treads from above, the
    coursed band face-on (rough and fine as one stone) and close on the string course."""
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
    out.append({"name": "wall_rough", "pos": [xw + 3.5, 4.6, Z + 8.5], "look_at": [xw + 3.5, 4.0, Z], "time": TIME})
    out.append({"name": "wall_fine", "pos": [xw + 13.5, 4.6, Z + 8.5], "look_at": [xw + 13.5, 4.0, Z], "time": TIME})
    out.append({"name": "walls_far", "pos": [xw + 8.5, 5.0, Z + 20.0], "look_at": [xw + 8.5, 4.0, Z], "time": TIME})

    xc0, xc1 = spans["coursed"]
    xc1 -= 2
    xm = (xc0 + xc1) / 2.0
    out.append({"name": "coursed", "pos": [xm, 6.5, Z + 12.0], "look_at": [xm, 6.0, Z], "time": TIME})
    out.append({"name": "coursed_course", "pos": [xm, 5.6, Z + 6.0], "look_at": [xm, 5.0, Z], "time": TIME})

    xf = spans["flight"][0]
    out.append({"name": "flight_treads", "pos": [xf + 1.0, 7.5, Z + 3.0], "look_at": [xf + 1.0, 1.0, Z - 3.0], "time": TIME})
    out.append({"name": "flight_copings", "pos": [xf + 3.5, 6.5, Z + 2.5], "look_at": [xf + 3.5, 1.5, Z - 2.0], "time": TIME})
    return out
