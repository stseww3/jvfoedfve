"""Test scene of the work package main/shell (plan/packages/main/shell.md).

The main line built whole (walls, drum and dome, the shell inside them) four times over:

  at z 0      as it stands, with a few invisible lights inside so the rooms can be seen (they are
              this scene's only; the light line lights the real rooms);
  at z 100    cut off above y 5: the ground floor from above -- the hall, the west arcade, the two
              flights, the way to the west door, the foot of the pier;
  at z 200    cut off above y 13: the main floor -- galleries, mezzanine, the well, the wing rooms,
              the first turn of the ring stair;
  at z 300    cut off above y 19: the dome-room floor, the opening round the pier, the stair's top.

A slab of paving lies under each so the cuts do not look into the void.
"""
from artkit.canvas import Canvas

from scenes.obs import main, materials
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S

BIOME = "obs_blue"
BIOME_MARGIN = 60
CUTS = {"ground": (100, 5), "main": (200, 13), "dome": (300, 19)}       # name: (z of the copy, last row kept)
GROUND = (S.WALL_W - 14, S.Z_NORTH - 6, S.WALL_E + 9, S.Z_SOUTH + 6)   # x -14..24, z -40..40
LIGHTS = [
    (9, 4, -3), (9, 4, 3), (13, 4, 0), (10, 11, 0), (13, 10, -3), (13, 10, 3),      # the hall
    (-3, 3, 0), (-4, 10, 0), (-3, 10, -4), (-3, 10, 4), (0, 9, 0),                  # the stair hall
    (7, 10, -11), (7, 10, -20), (7, 10, 11), (7, 10, 20),                           # the wing rooms
    (11, 20, 5), (11, 20, -5), (-3, 20, 5), (-3, 20, -5), (7, 15, 1),               # the dome room, the stair
]


def build():
    whole = Canvas()
    main.build(whole, (0, 0, 0))
    c = Canvas()
    x0, z0, x1, z1 = GROUND
    for dz in [0] + [z for z, _top in CUTS.values()]:
        c.box(x0, S.PAVING_Y, z0 + dz, x1, S.PAVING_Y, z1 + dz, B.SLATE_SMOOTH.block)
    for (x, y, z), state in whole.b.items():
        c.set(x, y, z, state)
        for dz, top in CUTS.values():
            if y <= top:
                c.set(x, y, z + dz, state)
    for x, y, z in LIGHTS:
        c.set(x, y, z, f"{B.LIGHT}[level=15]", keep=True)
    return c


def build_models():
    return main.models() or {}


def write_pack(pack_dir):
    """The shell paints nothing; it stands on the repainted blocks as the materials line has them."""
    return materials.pack(pack_dir)
