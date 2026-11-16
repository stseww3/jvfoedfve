"""Test scene of props/plaques: the twelve plaques of the map on one wall, and one on a pier.

A wall of the pale stone, two rows of six plaques at two blocks from one to the next, their
middles 1.5 and 2.5 over the floor; east of it a pier one block wide with the credit plate of
motion/guide on it (a name wider than the plate holds, set smaller), to show how much stone a
plaque leaves either side of it on the narrowest thing it hangs on.

The plaques are text displays: the offline renderer draws none of them, so the kept pictures
show the bare wall and are only the place the real client's pictures are taken from (near: the
words of one plaque from 2.6 blocks; wall: the family from eight; pier).

The shots are written from the numbers below:  python -m scenes.obs_props_plaques
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.props import _kit as K
from scenes.obs.props import plaques

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32
TIME = 14000
PITCH = 2                       # blocks from the middle of one plaque to the next
ROWS = (2.5, 1.5)               # the middles of the two rows over the floor
PER_ROW = 6
PIER_X = PER_ROW * PITCH + 2    # the pier: one block wide, clear of the wall
LIGHT_LEVEL = 9                 # a lamp's light on the wall, three blocks before it
CREDIT = ("BLUE HOUR OBSERVATORY", "Built by c164")


def spots():
    """Where each plaque hangs: [(key or None for the credit plate, the middle of its plate)]."""
    out = []
    for i, key in enumerate(plaques.TEXT):
        out.append((key, (1.0 + (i % PER_ROW) * PITCH, ROWS[i // PER_ROW], 0.0)))
    out.append((None, (PIER_X + 0.5, 1.5, 0.0)))
    return out


def build():
    c = Canvas()
    c.box(-2, -1, -1, PIER_X + 2, -1, 7, B.TUFF_SMOOTH.block)
    c.box(-1, 0, -1, PER_ROW * PITCH, 3, -1, B.ASHLAR_FINE.block)
    c.box(PIER_X, 0, -1, PIER_X, 2, -1, B.ASHLAR_FINE.block)
    n = 0
    for key, at in spots():
        if key is None:
            n += plaques.sign(c, *CREDIT, at)
        else:
            n += plaques.place(c, key, at)
    K.offer_lights(c, [((x, 1, 3), LIGHT_LEVEL) for x in range(1, PIER_X + 1, 4)], "props/plaques")
    sky.build(c, (0, 0, 0))
    c.entity_counts = {"props": n}
    return c


def write_pack(pack_dir):
    """The repainted stone the plaques hang on, and the pictures of the map's sky."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots():
    near = dict(spots())["power_house"]         # the longest sentence
    wall_x = PER_ROW * PITCH / 2.0
    return [
        {"name": "near", "pos": [near[0] + 0.3, 1.62, 2.6], "look_at": [near[0], near[1], 0.0], "time": TIME},
        {"name": "wall", "pos": [wall_x, 1.9, 8.0], "look_at": [wall_x, 1.9, 0.0], "time": TIME},
        {"name": "pier", "pos": [PIER_X - 1.0, 1.62, 3.0], "look_at": [PIER_X + 0.5, 1.5, 0.0], "time": TIME},
    ]
