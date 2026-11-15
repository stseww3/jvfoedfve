"""Test scene of the work package machines/mast (card machines/radiomast): the radio mast where it
stands in the map, with stand-ins for what it stands on and is seen beside and behind.

This scene shows version a, the default: foot and shaft are display models. Its twin
obs_mach_radiomast_b shows version b (legs and belts of the thin iron pipe block, the models carry
the diagonals) from the same cameras, so the two sets of pictures can be laid side by side shot by
shot; the pairs that decide are v1, skyline, aerial and far70.

Stand-ins, each only as far as the mast needs it:
  - the stone foot, the four guy anchors and the lead-in post are site/mastbase's. When that
    module is in the tree it is built as it is; until then the same blocks are put down here from
    the numbers the mast reads;
  - the pad and a strip of the terrace south of it, one flat course;
  - the clock tower (main/tower) as a banded shaft on the skeleton's footprint, with its lowest
    cornice and a rod for the time-ball mast: V1, V2 and V5 see the mast beside it;
  - the meridian hut as a low box: V2 sees the mast rise from behind it.

The shots are written from the numbers below:  python -m scenes.obs_mach_radiomast
"""
import math

from artkit.blocks import st
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.machines import mast

try:
    from scenes.obs.site import mastbase
except ImportError:
    mastbase = None

BIOME = "obs_blue"
BIOME_MARGIN = 120              # the look has to reach the far cameras: V1 stands 50 east of the blocks,
BIOME_MARGIN_Y = 96             # V11 80 south of them, V12 over 100 south and 30 above
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)
VERSION = "a"

PAVING = B.SLATE_SMOOTH.block
PLINTH = B.SLATE_BRICK.block
COPE = st(B.ASHLAR_PANEL.slab, type="bottom")
SEAT = B.IRON_RIVETED.block
BOLT = st(B.IRON_ROD, facing="up")
TOWER = (B.ASHLAR_FINE.block, B.ASHLAR_ROUGH.block)     # in bands three courses high: no face is flat over 5 x 5
CORNICE = st(B.ASHLAR_FINE.slab, type="top")
CORNICE_Y = 31                  # the tower's lowest cornice: one cell out all round at this y
HUT_WALL = B.ASHLAR_ROUGH.block
HUT_ROOF = st(B.SLATE_TILE.slab, type="bottom")
HUT_EAVES = 3                   # the hut: three courses of wall, the roof on them

# the cameras of the board that have the mast in them; the skeleton's own where it has them. V5 and
# V12 are not in the skeleton yet: until they are, the render station's proposals stand here, worked
# out from the skeleton the way tools/boardshots.py does
V1 = S.V1
V2 = getattr(S, "V2", dict(pos=(58.5, 1.7, 0.5), look_at=(17, 19, 0.5)))
V11 = S.V11
_TOWER = (S.mid(*S.CLOCK_SHAFT_X), S.mid(*S.CLOCK_SHAFT_Z))
V5 = getattr(S, "V5", dict(pos=(_TOWER[0] + 15.0, S.GROUND + S.EYE, _TOWER[1] + 15.0),
                           look_at=(_TOWER[0], S.CLOCK_SHAFT_TOP - 3.0, _TOWER[1])))
V12 = getattr(S, "V12", dict(pos=(S.EAST_EDGE_X + 20.0, 90.0, S.Z_SOUTH + 46.0),
                             look_at=(S.MERIDIAN_X, S.GROUND, S.AXIS_Z - 5.5)))


def _foot(c):
    """The stone foot of the mast from the numbers the mast reads: the step and its coping, the
    iron seat, the four anchors with their eye bolts, the lead-in post."""
    fx, fz, g = mast.FX, mast.FZ, int(mast.G)
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            c.set(fx + dx, g, fz + dz, PLINTH)
            c.set(fx + dx, g + 1, fz + dz, COPE if max(abs(dx), abs(dz)) > 1 else SEAT)
    for ax, _, az in mast.GUY_ANCHORS:
        x, z = int(math.floor(ax)), int(math.floor(az))
        c.set(x, g, z, SEAT)
        c.set(x, g + 1, z, BOLT)
    px, _, pz = (int(math.floor(v)) for v in mast.LEAD_POST)
    c.set(px, g + 1, pz, SEAT)
    c.set(px, g + 2, pz, BOLT)
    c.set(px, g + 3, pz, BOLT)


def _tower(c):
    """The clock tower as far as the mast is seen beside it: the shaft, its lowest cornice and the
    time-ball mast."""
    x0, x1 = S.CLOCK_SHAFT_X
    z0, z1 = S.CLOCK_SHAFT_Z
    for y in range(0, S.CLOCK_TOP + 1):
        c.box(x0, y, z0, x1, y, z1, TOWER[(y // 3) % 2])
    for x in range(x0 - 1, x1 + 2):
        for z in range(z0 - 1, z1 + 2):
            if not (x0 <= x <= x1 and z0 <= z <= z1):
                c.set(x, CORNICE_Y, z, CORNICE)
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    c.box(cx, S.CLOCK_TOP + 1, cz, cx, S.CLOCK_BALL_MAST - 1, cz, BOLT)


def _hut(c):
    """The meridian hut as a box of its size."""
    cx, cz = S.MERIDIAN_HUT["centre"]
    h = S.MERIDIAN_HUT["size"] // 2
    c.box(cx - h, 0, cz - h, cx + h, HUT_EAVES - 1, cz + h, HUT_WALL)
    c.box(cx - h, HUT_EAVES, cz - h, cx + h, HUT_EAVES, cz + h, HUT_ROOF)


def stage(version):
    """The scene with the mast built in the given version."""
    c = Canvas()
    x0, z0, x1, z1 = S.MAST_PAD["box"]
    hut_east = S.MERIDIAN_HUT["centre"][0] + S.MERIDIAN_HUT["size"] // 2
    c.box(S.CLOCK_SHAFT_X[0] - 2, -1, z0, max(x1, hut_east) + 2, -1, S.CLOCK_SHAFT_Z[1] + 2, PAVING)
    if mastbase is not None:
        mastbase.build(c, (0, 0, 0))
    else:
        _foot(c)
    _tower(c)
    _hut(c)
    n = mast.build(c, (0, 0, 0), version=version)
    sky.build(c, (0, 0, 0))             # A2's light sources go in last, when everything stands
    c.entity_counts = {"machines": n}
    return c


def build():
    return stage(VERSION)


def build_models():
    return mast.models()


def write_pack(pack_dir):
    """The sky's pictures, for the comet the lamp is seen beside, and the repainted iron and stone the
    mast is judged against."""
    return list(sky.pack(pack_dir) or []) + list(materials.pack(pack_dir) or [])


def shots():
    """The cameras. From far: the board's V1, V2, V5, V11 (skyline) and V12 (aerial), and the whole
    mast from 70 blocks under the three lights. From near: the lattice where the guys meet it, the
    look up from the pad, the foot on the seat, the same from above, one anchor with its guy, the
    head and its lamp."""
    out = []

    def shot(name, pos, look_at, time=TIME):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": time})

    ax, az = mast.AX, mast.AZ
    shot("v1", V1["pos"], V1["look_at"])
    shot("v2", V2["pos"], V2["look_at"])
    shot("v5", V5["pos"], V5["look_at"])
    shot("skyline", V11["pos"], V11["look_at"])
    shot("aerial", V12["pos"], V12["look_at"])
    far = (ax + 21.6, mast.G + S.EYE, az + 66.6)                # 70 blocks from the axis, a standing eye, 18 degrees
    shot("far70", far, (ax, 30.0, az))                          # off square: the line passes west of the hut
    shot("far70_deep", far, (ax, 30.0, az), 18000)
    shot("far70_glow", far, (ax, 30.0, az), 12900)
    shot("near", (ax + 6.0, 21.5, az + 2.5), (ax, 22.0, az))
    shot("below", (ax + 3.3, mast.G + S.EYE, az + 0.4), (ax, 14.0, az))        # from the apron, 75 degrees up
    shot("foot", (ax + 0.8, 3.4, az + 5.4), (ax, 4.6, az))                      # from between the two south anchors
    # the seat from above, down its diagonal and 45 degrees steep, as a window high in the clock tower
    # has it from the other side: what is pale on the seat must not make a sign from there
    shot("seat", (ax + 12.0, mast.BASE_Y + 17.0, az + 12.0), (ax, mast.BASE_Y + 0.5, az))
    sx, sy, sz = max(mast.GUY_ANCHORS, key=lambda p: (p[0], p[2]))              # the south-east anchor,
    shot("stay", (sx + 1.9, sy + 0.8, sz - 1.9), (sx - 0.1, sy + 1.0, sz - 0.1))        # its guy seen from the side
    shot("head", (ax + 4.5, mast.TOP_Y + 4.0, az + 5.5), (ax - 0.3, mast.TOP_Y + 2.1, az + 0.2))
    return out
