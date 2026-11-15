"""Test scene of the work package machines/engine-dynamo (plan/packages/machines/engine-dynamo.md).

The power house's box with the engine set standing on its bed plate: the room is x 67..89, z 20..42,
feet at y -6, walls ten high, so the floor slab is y -7 and the ceiling block y 4. Everything else in
the room -- the shell, the grille walkways, the boiler and switchboard (machines/switchboard-boiler),
the lamps and pipes (props) -- is a stand-in here: this scene is for the engine and the dynamo.

  set             the whole machine from the door and from the room's east end
  flywheel        the wheel from the side, where its rim, spokes and crank pin read
  cylinder        the cylinder, slide bars and crosshead close
  governor        the governor from the height of a standing person
  dynamo          the dynamo and its armature
  belt            the belt run from the wheel to the dynamo's pulley

The scene lays one work light over the machine (the room's own lamps are props/lamps' when they are in
the tree); without it a box room is black and no metal reads.

    python -m scenes.obs_mach_engine_dynamo        writes shots.json from the layout below
"""
from artkit.canvas import Canvas

from scenes.obs import materials
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.machines import engine_dynamo as engine

BIOME = "obs_blue"
CATEGORY = "machines"
TIME = 14000

PH = S.POWER_HOUSE
X0, Z0, X1, Z1 = PH["box"]          # 67, 20, 89, 42
FEET = PH["base_y"]                 # -6
CEIL = FEET + PH["wall_h"]          # 4
FLOOR = FEET - 1                    # -7
WALL = B.TUFF_BRICK.block
WORK_LIGHT = 14                     # the test scene's work light (never 15)

DOOR_H = 3                          # the way in, on the south wall, in front of the machine


def _room(c):
    """The box: floor, four walls, ceiling, and the door in the south wall."""
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            c.set(x, FLOOR, z, WALL)
            c.set(x, CEIL, z, WALL)
    for y in range(FEET, CEIL):
        for x in range(X0, X1 + 1):
            c.set(x, y, Z0, WALL)
            c.set(x, y, Z1, WALL)
        for z in range(Z0, Z1 + 1):
            c.set(X0, y, z, WALL)
            c.set(X1, y, z, WALL)
    dx = int(engine.CX)
    c.carve(dx - 1, FEET, Z1, dx + 1, FEET + DOOR_H - 1, Z1)
    # a work light over each end: the machine is 12 blocks long and one lamp left the dynamo end dark
    for lx in (int(engine.CX + engine.CYL_X), int(engine.CX + engine.DYNAMO_X)):
        c.set(lx, CEIL - 1, int(engine.CZ), f"{B.LIGHT}[level={WORK_LIGHT}]")
    return c


def layout(c=None):
    c = c or Canvas()
    _room(c)
    n = engine.build(c, (0, 0, 0))
    return c, n


def build():
    c, _ = layout()
    return c


def build_models():
    return engine.models()


def write_pack(pack_dir):
    return materials.pack(pack_dir)


def shots():
    out = []

    def shot(name, pos, look_at, time=TIME):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": time})

    cx, cz = engine.CX, engine.CZ
    eye = FEET + 1.62
    shot("set", (cx, eye, Z1 - 2.0), (cx, FEET + 1.6, cz - 1.0))
    shot("set_east", (X1 - 2.0, eye, cz + 6.0), (cx - 1.0, FEET + 1.6, cz))
    # the wheel: three-quarter from the room's south-west, where the spokes and crank pin read; the
    # side view looks along the room's long axis at the rim
    shot("flywheel", (cx + engine.WHEEL_X - 2.2, FEET + 3.0, cz + 5.6),
         (cx + engine.WHEEL_X, FEET + 2.5, cz))
    shot("flywheel_side", (cx + engine.WHEEL_X + 0.4, FEET + 2.5, cz - 4.6),
         (cx + engine.WHEEL_X, FEET + 2.4, cz))
    shot("cylinder", (cx + engine.CYL_X + 1.2, FEET + 2.3, cz + 3.8),
         (cx + engine.CYL_X, FEET + 1.6, cz))
    shot("governor", (cx + engine.GOV_X - 0.6, FEET + 1.20, cz + 2.6),
         (cx + engine.GOV_X, FEET + 1.95, cz + 0.95))
    shot("dynamo", (cx + engine.DYNAMO_X + 0.6, FEET + 2.0, cz + 3.6),
         (cx + engine.DYNAMO_X, FEET + 1.7, cz))
    shot("belt", (cx + engine.DYNAMO_X - 3.0, FEET + 2.7, cz + 4.6),
         (cx + engine.WHEEL_X + 0.5, FEET + 2.6, cz))
    return out
