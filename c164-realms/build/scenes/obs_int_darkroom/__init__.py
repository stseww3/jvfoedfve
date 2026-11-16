"""obs_int_darkroom: a try-out box for the darkroom kit (scenes.obs.interiors._darkroom). Not a
test scene of any card: it lives on the kit's try branch only. A stone box on the skeleton's
coordinates of the plate vault's darkroom (x 2..13, z 23..25, feet at 0) behind its wall with the
arch, a piece of the vault before it, the lift in a corner of that piece.
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.interiors import _darkroom as kit

BIOME = "obs_blue"
CATEGORY = "interiors"

X = (2, 13)
Z = (17, 25)            # the box: a piece of the vault (z 17..21), the wall (z 22), the darkroom (z 23..25)
WALL_Z = 22
ARCH_X = (6, 8)
CEIL = 6
LIFT = (2, 0, 18)
RED = 7                 # the light asked for before the red lamp
FILL = 9                # and before the lift


def build():
    c = Canvas()
    wall, floor = B.TUFF_BRICK.block, B.TUFF_SMOOTH.block
    for x in range(X[0] - 1, X[1] + 2):
        for z in range(Z[0] - 1, Z[1] + 2):
            c.set(x, -1, z, floor)
            c.set(x, CEIL, z, floor)
            edge = x in (X[0] - 1, X[1] + 1) or z in (Z[0] - 1, Z[1] + 1)
            for y in range(0, CEIL):
                if edge or (z == WALL_Z and not (ARCH_X[0] <= x <= ARCH_X[1] and y <= 2)):
                    c.set(x, y, z, wall)
    n = kit.dress(c)
    n += kit.lift(c, LIFT, facing="east")
    x, y, z = kit.lamp_cell()
    c.set(x, y, z, f"{B.LIGHT}[level={RED}]")
    c.set(LIFT[0] + 2, 2, LIFT[2] + 1, f"{B.LIGHT}[level={FILL}]")
    c.entity_counts = {"interiors": n}
    return c


def build_models():
    return kit.models()


def write_pack(pack_dir):
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
