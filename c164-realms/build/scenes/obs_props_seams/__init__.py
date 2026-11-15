"""Test scene of the props kit: do the props' materials meet the blocks' without a seam in colour?

The cross-looks between the materials line and the props line use it. One bay per repainted block,
from west to east: the cast irons, the brasses, the old coppers, the stones, the dark wood. A bay is
a wall of the block three wide and three high; on its middle course hang two plain plates painted
in the props' materials of that kind (props/_kit.py), the usual tone on the left, the dark one on
the right, and the block between them is left bare. A plate should read as the same material as the
wall it hangs on: a part of it, a little proud, not a patch of another colour.

The shots are written from the numbers below:  python -m scenes.obs_props_seams
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.props import _kit as K

from . import props

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32
TIME = 14000
PITCH = 4                       # a bay is three wide, then a gap of one
LIGHT_LEVEL = 12                # three blocks in front of the wall: a lamp's light on its middle course

# (name, the block, the plate on the left, the plate on the right or None)
BAYS = [
    ("iron_plate", B.IRON_PLATE, "iron", "iron_dark"),
    ("iron_riveted", B.IRON_RIVETED.block, "iron_riveted", "iron_dark"),
    ("iron_cast", B.IRON_CAST, "iron", "iron_dark"),
    ("brass_plate", B.BRASS_PLATE.block, "brass", "brass_dark"),
    ("brass_pattern", B.BRASS_PATTERN.block, "brass", "brass_dark"),
    ("old_copper", B.OLD_COPPER, "old_copper", "cable"),
    ("old_copper_cut", B.OLD_COPPER_CUT.block, "old_copper", None),
    ("ashlar_fine", B.ASHLAR_FINE.block, "ashlar", None),
    ("ashlar_rough", B.ASHLAR_ROUGH.block, "ashlar", None),
    ("dark_wood", B.DARK_WOOD.block, "dark_wood", None),
]


def build():
    c = Canvas()
    width = len(BAYS) * PITCH
    c.box(-2, -1, -1, width, -1, 7, B.TUFF_SMOOTH.block)
    n = 0
    built = props.build_models()
    for i, (_, block, left, right) in enumerate(BAYS):
        x0 = i * PITCH
        c.box(x0, 0, -1, x0 + 2, 2, -1, block)
        n += K.put(c, built[props.PREFIX + left], (x0 + 0.5, 1.5, 0.0), mount="wall")
        if right:
            n += K.put(c, built[props.PREFIX + right], (x0 + 2.5, 1.5, 0.0), mount="wall")
        K.offer_lights(c, [((x0 + 1, 1, 3), LIGHT_LEVEL)], "props/seams")
    sky.build(c, (0, 0, 0))
    c.entity_counts = {"props": n}
    return c


def write_pack(pack_dir):
    return materials.pack(pack_dir)


def shots():
    """Two bays to a picture from five blocks, and the whole row along the wall."""
    out = []
    for i in range(0, len(BAYS), 2):
        x = i * PITCH + PITCH - 0.5
        out.append({"name": f"{BAYS[i][0]}__{BAYS[i + 1][0]}", "pos": [x, 1.9, 5.0], "look_at": [x, 1.5, 0.0],
                    "time": TIME})
    out.append({"name": "row", "pos": [-1.5, 2.2, 3.0], "look_at": [10.0, 1.4, 0.0], "time": TIME})
    return out
