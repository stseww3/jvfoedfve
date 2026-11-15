"""obs_int_powerhouse: the box test scene of the power house (work package interiors/powerhouse).

The room stands in a stand-in of its shell on the skeleton's coordinates; the dressing is
scenes.obs.interiors.powerhouse, the same call the master scene will make once site/powerhouse is
in the tree. The resource pack is the materials line's.

The stand-in shell is by the shell package's own rule (site/powerhouse, c285): tuff brick walls two
cells thick with a pier of one and a window of three, a polished plinth and cornice, the wicket in
the second bay of the north front, and the two furnace bays where the boilers stand.

The machines come from their own packages when those are in the tree (machines/engine-dynamo is);
otherwise a stand-in of plain blocks marks the cells this room keeps clear for them.
"""
from artkit.canvas import Canvas

from scenes.obs import materials
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.interiors import powerhouse
from scenes.obs.machines import engine_dynamo as ENGINE

BIOME = "obs_blue"
CATEGORY = "interiors"
TIME = 14000

BOX = S.POWER_HOUSE["box"]
X0, Z0, X1, Z1 = BOX
FEET = S.POWER_HOUSE["base_y"]
WALL_H = S.POWER_HOUSE["wall_h"]
TOP = FEET + WALL_H                 # the roof's underside: one row over the cornice
BAY = S.BAY
PIER = powerhouse.PIER

WALL = B.TUFF_BRICK.block
PLINTH = B.TUFF_SMOOTH.block
CORNICE = B.TUFF_SMOOTH.block
IRON = B.IRON_RIVETED.block
GLASS = B.WINDOW_DARK.block


def shell(c):
    """The shell of the room: site/powerhouse's own when it is in the tree, else the stand-in by
    its rule."""
    real = _real_shell()
    if real is not None:
        return real
    return _stand_in_shell(c)


def _real_shell():
    """site/powerhouse's module, if the assembly has it."""
    try:
        from scenes.obs.site import powerhouse as SITE
    except ModuleNotFoundError:
        return None
    return SITE


def _stand_in_shell(c):
    """The stand-in, by the shell package's rule (site/powerhouse, c285)."""
    # the four walls: the pier plane at the box, the lining one cell in
    for d in (0, 1):
        for x in range(X0 + d, X1 - d + 1):
            for z in (Z0 + d, Z1 - d):
                for y in range(FEET, TOP):
                    c.set(x, y, z, WALL)
        for z in range(Z0 + d, Z1 - d + 1):
            for x in (X0 + d, X1 - d):
                for y in range(FEET, TOP):
                    c.set(x, y, z, WALL)
    # the plinth and the cornice
    for d in (0, 1):
        for x in range(X0 + d, X1 - d + 1):
            for z in (Z0 + d, Z1 - d):
                c.set(x, FEET, z, PLINTH)
                c.set(x, TOP - 1, z, CORNICE)
        for z in range(Z0 + d, Z1 - d + 1):
            for x in (X0 + d, X1 - d):
                c.set(x, FEET, z, PLINTH)
                c.set(x, TOP - 1, z, CORNICE)
    # the wicket: the second bay of the north front, four courses
    for x in powerhouse.DOOR_X:
        for y in range(powerhouse.DOOR_ROWS[0], powerhouse.DOOR_ROWS[0] + 4):
            c.clear(x, y, Z0)
            c.clear(x, y, Z0 + 1)
    # the furnace bays: the north front's fourth bay and the east front's second, the lowest three
    # rows glowing; the boiler's own light is the light line's, so here they are curtain glass
    for x in range(X0 + PIER + 3 * BAY, X0 + PIER + 3 * BAY + 3):
        for y in range(FEET + 3, FEET + 6):
            c.set(x, y, Z0 + 1, B.WINDOW_CURTAIN.block)
    for z in range(Z0 + PIER + BAY, Z0 + PIER + BAY + 3):
        for y in range(FEET + 3, FEET + 6):
            c.set(X1 - 1, y, z, B.WINDOW_CURTAIN.block)
    # the floor slab the room stands on, so the walls are not floating
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            c.set(x, FEET - 2, z, B.SLATE_BRICK.block)


def machines(c, origin=(0, 0, 0)):
    """The engine and the dynamo, from their own package; a stand-in if it is not in the tree."""
    if ENGINE is not None:
        return ENGINE.build(c, origin)
    n = 0
    for x, z in powerhouse.ENGINE_CELLS:
        c.set(x, FEET, z, B.IRON_PLATE)
    return n


def build():
    c = Canvas()
    modules = shell(c)
    if modules is not None:
        modules.build(c)
    powerhouse.build_powerhouse(c)
    machines(c)
    return c


def build_models():
    """The machines' own models: the models category is where they are made, and this scene shows
    them, so its pack needs them."""
    return ENGINE.models()


def write_pack(pack_dir):
    return materials.pack(pack_dir)
