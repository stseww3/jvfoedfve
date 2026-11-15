"""Test scene of machines/orrery: the two versions, each hung in a box the size of the star hall.

Each box is the clear star hall of the skeleton (x 2..15, z -6..6, the ceiling block at y 14) with
the things that frame the orrery in the views it has to hold (A0 #207): the thin telescope pier at
the west end, the side galleries (feet at y 7, the rail on the edge of the well), the entrance on
the east (three wide, y 0..5) with the great windows over it, and a strip of the front court outside
the door. Version a (planar, open gears) hangs in the south box; version b (the armillary bowl) in
the north box, built at a z offset, so the two are framed alike and can be compared blind.

    python -m scenes.obs_mach_orrery        # writes shots.json from the numbers below
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.machines import orrery

BIOME = "obs_blue"
BIOME_MARGIN = 24
BIOME_MARGIN_Y = 24

IX = (S.ROOM_X[0], S.east_wall_x(9) - 2)   # 2..15: the clear hall in x, up to the glass of the centre bays
IZ = S.STAR_HALL_Z                         # -6..6
WX = (IX[0] - 1, IX[1] + 1)                # the walls: x 1 and 16
WZ = (IZ[0] - 1, IZ[1] + 1)                # z -7 and 7
PAVE_Y = S.PAVING_Y                        # -1, the floor block; feet at y 0
CEIL_Y = S.STAR_HALL_CEIL                  # 14, the ceiling block (its lower face is the hang point)
WALL_TOP = CEIL_Y - 1                      # 13
DOOR_Y = (0, 5)                            # the entrance, three wide (A0: the three arches are y 0..5)
COURT_X = (WX[1] + 1, WX[1] + 8)           # a strip of the front court outside the door
VERSIONS = {"a": 0, "b": 22}               # version -> the z offset of its box

LIGHT_STONE = B.ASHLAR_FINE.block
DARK_STONE = B.SLATE_SMOOTH.block
WALL = B.ASHLAR_FINE.block
PILASTER = B.ASHLAR_ROUGH.block
COURSE = B.ASHLAR_PANEL.block
CEIL = B.ASHLAR_PANEL.block
PIER = B.ASHLAR_FINE.block
PIER_FOOT = B.ASHLAR_ROUGH.block
GALLERY = B.IRON_RIVETED.block
RAIL = B.IRON_BARS + "[east=true,west=true]"
GLASS = B.WINDOW_FROSTED.block
INLAY = B.BRASS_INLAY
WINDOW_LIGHT = 9                           # behind each great window; the sun of the orrery is the warm core
TIME = 14000                               # light version A, the default

CX, CZ = orrery.CX, orrery.CZ              # the hung centre (11.5, 0.5)
RING_Y = orrery.RING_Y                     # 8.5


def _wall(a, y):
    """One wall cell: a pilaster strip every fourth column (so no face runs flat over 5x5), a string
    course at the gallery floor, plain ashlar between."""
    if a % 4 == 0:
        return PILASTER
    return COURSE if y == S.STRING else WALL


def _box(c, dz, version):
    x0, x1 = IX
    z0, z1 = IZ[0] + dz, IZ[1] + dz
    wx0, wx1 = WX
    wz0, wz1 = WZ[0] + dz, WZ[1] + dz

    # floor: a black-and-white stone chequer (plan 8), the brass meridian inlaid along the axis
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            c.set(x, PAVE_Y, z, LIGHT_STONE if (x + z) % 2 == 0 else DARK_STONE)
    for x in range(S.PIER_SHAFT[2] + 1, x1 + 1):
        c.set(x, 0, dz, INLAY)
    c.box(COURT_X[0], PAVE_Y, dz - 3, COURT_X[1], PAVE_Y, dz + 3, DARK_STONE)

    c.box(wx0, CEIL_Y, wz0, wx1, CEIL_Y, wz1, CEIL)
    for y in range(0, WALL_TOP + 1):
        for x in range(wx0, wx1 + 1):
            c.set(x, y, wz0, _wall(x, y))
            c.set(x, y, wz1, _wall(x, y))
        for z in range(wz0, wz1 + 1):
            c.set(wx0, y, z, _wall(z - dz, y))
            c.set(wx1, y, z, _wall(z - dz, y))

    # the east front: the entrance on the axis and the three great windows over it (bays 8, 9, 10)
    c.carve(wx1, DOOR_Y[0], dz - 1, wx1, DOOR_Y[1], dz + 1)
    for zc in (dz - 4, dz, dz + 4):
        for y in range(S.WINDOW[0], S.WINDOW[1] + 1):
            for d in (-1, 0, 1):
                c.set(wx1, y, zc + d, GLASS)
        c.set(wx1 - 1, 10, zc, f"{B.LIGHT}[level={WINDOW_LIGHT}]", keep=True)

    # the telescope pier at the west end (plain stone context: 3x3, up through the hall)
    px0, pz0, px1, pz1 = S.PIER_SHAFT
    c.box(px0, 0, pz0 + dz, px1, WALL_TOP, pz1 + dz, PIER)
    c.box(px0, 0, pz0 + dz, px1, 1, pz1 + dz, PIER_FOOT)

    # the side galleries (x 2..13), the rail on the edge of the well at the ring's eye level
    for gz0, gz1, railz in ((z0, dz - 4, dz - 4), (dz + 4, z1, dz + 4)):
        c.box(x0, S.STRING, gz0, S.ROOM_X[1], S.STRING, gz1, GALLERY)
        for x in range(x0, S.ROOM_X[1] + 1):
            c.set(x, S.STAND, railz, RAIL)

    return orrery.build(c, (0, 0, dz), version=version)


def build():
    c = Canvas()
    n = 0
    for version, dz in VERSIONS.items():
        n += _box(c, dz, version)
    sky.build(c, (0, 0, 0))         # A2's light sources go in last
    c.entity_counts = {"machines": n}
    return c


def write_pack(pack_dir):
    """The repainted stone, iron, glass and brass the orrery is judged against."""
    return materials.pack(pack_dir)


def shots():
    """The cameras, the same five for each version: through the front door looking up at the sun;
    straight below, looking up; level from the side gallery; from the ring stair's first flight, a
    little above the ring; and close, about three blocks from the planets."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": TIME})

    for v, dz in VERSIONS.items():
        z = CZ + dz
        shot(f"door_{v}", (WX[1] + 3.5, S.EYE, z), (CX, RING_Y, z))
        shot(f"under_{v}", (CX, S.EYE, z), (CX, RING_Y, z))
        shot(f"gallery_{v}", (CX, S.STAND + S.EYE, z + 5.0), (CX, RING_Y + 0.2, z))
        shot(f"stair_{v}", (5.5, 8.5 + S.EYE, z + 3.0), (CX, RING_Y + 0.4, z))
        shot(f"near_{v}", (CX + 1.9, RING_Y + 0.5, z + 3.1), (CX + 0.4, RING_Y + 0.1, z + 0.5))
    return out
