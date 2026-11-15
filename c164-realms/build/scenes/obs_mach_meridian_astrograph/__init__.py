"""Test scene of the work package machines/meridian-astrograph.

Two boxes in one scene, 60 blocks apart: the meridian hut at (35, -30), 9 x 9 with a north-south slit
in its roof, and the small dome's drum at (12.5, 30.5) with its shutter. Both shells belong to other
lines (site/meridian hut, main/smalldome); what is here is a stand-in so the instruments can be seen
in the geometry they will live in.

  meridian_hut      the circle from the hut's door, and close on the tube and its graduated ring
  slit              looking up the tube at the roof's slit, which is what the instrument is for
  astro             the astrograph under the dome, from the drum's floor
  astro_up          the tube from below, up through the dome's opening
  both              the two instruments far apart, for the record

    python -m scenes.obs_mach_meridian_astrograph        writes shots.json from the layout
"""
from artkit.canvas import Canvas

from scenes.obs import materials
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.machines import meridian_astrograph as MA

BIOME = "obs_blue"
CATEGORY = "machines"
TIME = 14000

WORK_LIGHT = 14
WALL = B.TUFF_BRICK.block

# the hut: 9 x 9 round the centre, walls 6 high, a slit 2 wide in the roof running north-south
HUT_CX, HUT_CZ = MA.HUT_CX, MA.HUT_CZ
HUT_H = 6
SLIT_W = 2

# the small dome's drum: the floor at SMALL_DRUM_BASE, 8 high, the slit facing the platform
DX0, DX1 = S.SMALL_DOME_X
DZ0, DZ1 = S.SMALL_DOME_Z
DOME_FLOOR = S.SMALL_DRUM_BASE
DOME_H = 7


def _box(c, x0, z0, x1, z1, floor, height, wall=WALL, door=None):
    """A hollow box: floor, four walls, roof. `door` = (x0, x1, face) cuts a way in."""
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            c.set(x, floor, z, wall)
            c.set(x, floor + height + 1, z, wall)
    for y in range(floor + 1, floor + height + 1):
        for x in range(x0, x1 + 1):
            c.set(x, y, z0, wall)
            c.set(x, y, z1, wall)
        for z in range(z0, z1 + 1):
            c.set(x0, y, z, wall)
            c.set(x1, y, z, wall)
    if door:
        d0, d1, face = door
        for x in range(d0, d1 + 1):
            for y in range(floor + 1, floor + 4):
                c.carve(x, y, face, x, y, face)


def _hut(c):
    h = (HUT_H - 1) // 2
    x0, x1 = int(HUT_CX) - h, int(HUT_CX) + h
    z0, z1 = int(HUT_CZ) - h, int(HUT_CZ) + h
    _box(c, x0, z0, x1, z1, MA.HUT_FEET - 1, HUT_H, door=(int(HUT_CX) - 1, int(HUT_CX), z1))
    # the roof's slit: two cells wide, running the hut's whole length, north to south
    sx = int(HUT_CX)
    for z in range(z0, z1 + 1):
        for x in range(sx - SLIT_W // 2, sx - SLIT_W // 2 + SLIT_W):
            c.carve(x, MA.HUT_FEET + HUT_H + 1, z, x, MA.HUT_FEET + HUT_H + 1, z)
    c.set(sx, MA.HUT_FEET + HUT_H, int(HUT_CZ) + 2, f"{B.LIGHT}[level={WORK_LIGHT}]")
    return c


def _dome(c):
    _box(c, DX0, DZ0, DX1, DZ1, DOME_FLOOR - 1, DOME_H, door=(DX0 + 3, DX0 + 4, DZ1))
    # the shutter: a slot in the drum's south face and the roof above the instrument
    cx, cz = int(MA.DOME_CX), int(MA.DOME_CZ)
    c.carve(cx, DOME_FLOOR + DOME_H + 1, cz, cx, DOME_FLOOR + DOME_H + 1, cz)
    c.set(cx + 2, DOME_FLOOR + DOME_H, cz, f"{B.LIGHT}[level={WORK_LIGHT}]")
    return c


def layout(c=None):
    c = c or Canvas()
    _hut(c)
    _dome(c)
    n = MA.build(c, (0, 0, 0))
    return c, n


def build():
    c, _ = layout()
    return c


def build_models():
    return MA.models()


def write_pack(pack_dir):
    return materials.pack(pack_dir)


def shots():
    out = []

    def shot(name, pos, look_at, time=TIME):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": time})

    mx, mz = MA.HUT_CX, MA.HUT_CZ
    eye = MA.HUT_FEET + 1.62
    shot("meridian_hut", (mx - 0.5, eye, mz + 3.2), (mx + 0.3, MA.HUT_FEET + 1.5, mz - 0.3))
    shot("meridian_tube", (mx - 2.2, MA.HUT_FEET + 1.75, mz + 2.6), (mx + 0.6, MA.HUT_FEET + 1.55, mz))
    shot("slit", (mx + 0.2, MA.HUT_FEET + 1.75, mz + 2.4), (mx, MA.HUT_FEET + 4.6, mz - 2.2))
    ax, az = MA.DOME_CX, MA.DOME_CZ
    aeye = MA.DOME_FLOOR + 1.62
    shot("astro", (ax - 2.0, aeye, az + 2.6), (ax, MA.DOME_FLOOR + 2.4, az))
    shot("astro_up", (ax - 1.0, MA.DOME_FLOOR + 1.15, az + 2.2), (ax, MA.DOME_FLOOR + 5.2, az - 0.8))
    shot("both", (mx - 8.0, MA.HUT_FEET + 8.0, mz + 12.0), (mx + 2.0, MA.HUT_FEET + 1.0, mz - 4.0))
    return out
