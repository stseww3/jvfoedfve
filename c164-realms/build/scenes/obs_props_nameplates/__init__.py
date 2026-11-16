"""Test scene of props/nameplates: the station's machine plate, on iron and on stone.

A wall looks south: three cells of riveted iron plate and three of dressed stone. On each stretch
hang plates a block apart at the height of the eye, and one low on the iron as a plate hangs on
a machine's bed. The cameras stand one, two and three blocks before the wall: two blocks is where
the writing is to be read (plan/fine.md: the near layer).

The shots are written from the numbers below:  python -m scenes.obs_props_nameplates
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.props import _kit as K
from scenes.obs.props import nameplates

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32
TIME = 14000

IRON_X, STONE_X = (0, 2), (3, 5)
EYE_ROW = 1.5
LOW = 0.4
SHOWN = ((0.5, EYE_ROW, 1), (1.5, EYE_ROW, 13), (2.5, EYE_ROW, 31), (1.5, LOW, 14),
         (3.5, EYE_ROW, 41), (4.5, EYE_ROW, 61), (5.5, EYE_ROW, 73))
LIGHT_LEVEL = 9                 # a lamp's light on the wall, three blocks before it


def build():
    c = Canvas()
    c.box(IRON_X[0] - 3, -1, -1, STONE_X[1] + 3, -1, 7, B.TUFF_SMOOTH.block)
    c.box(IRON_X[0], 0, -1, IRON_X[1], 2, -1, B.IRON_PLATE)
    c.box(STONE_X[0], 0, -1, STONE_X[1], 2, -1, B.ASHLAR_FINE.block)
    n = 0
    for x, y, number in SHOWN:
        n += nameplates.plate(c, number, (x, y, 0.0), facing="south")
    K.offer_lights(c, [((x, 1, 3), LIGHT_LEVEL) for x in (1, 4)], "props/nameplates")
    sky.build(c, (0, 0, 0))
    c.entity_counts = {"props": n}
    return c


def write_pack(pack_dir):
    """The repainted iron and stone the plates hang on, and the pictures of the map's sky."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots():
    return [
        {"name": "one", "pos": [1.7, S.EYE, 1.0], "look_at": [1.5, EYE_ROW, 0.0], "time": TIME},
        {"name": "two", "pos": [1.8, S.EYE, 2.0], "look_at": [1.5, EYE_ROW - 0.2, 0.0], "time": TIME},
        {"name": "three", "pos": [3.0, S.EYE, 3.0], "look_at": [3.0, EYE_ROW - 0.2, 0.0], "time": TIME},
        {"name": "stone_two", "pos": [4.3, S.EYE, 2.0], "look_at": [4.5, EYE_ROW, 0.0], "time": TIME},
    ]
