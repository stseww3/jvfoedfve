"""The plates of the seam test: one per material the props' models are painted in."""
from artkit import models as M

from scenes.obs.common import palette as P
from scenes.obs.props import _kit as K

PREFIX = "prop_swatch_"
MATS = {
    "iron": K.IRON, "iron_dark": K.IRON_D, "iron_riveted": K.IRON,
    "brass": K.BRASS, "brass_dark": K.BRASS_D,
    "old_copper": K.COPPER, "cable": K.flat("old_copper", 1),
    "ashlar": P.mat("ashlar"), "dark_wood": P.mat("dark_wood"),
}


def _plate(name, mat):
    """Ten texels square, one proud of the wall; anchor: its middle, on the wall."""
    m = M.Model(PREFIX + name)
    m.box((-5, -5, 0), (5, 5, 1), mat)
    if name.endswith("riveted"):
        for x in (-4, 4):
            for y in (-4, 4):
                K.rivet(m, (x, y, 1))
    return m


def build_models():
    return {PREFIX + name: _plate(name, mat) for name, mat in MATS.items()}
