"""Framework demo work package: one terrace bollard lamp, placed twice at the entrance, to exercise
the model -> display-entity -> resource-pack path end to end. A6 replaces this with the real lamp
family (plan 7.3) and its gallery test scene."""
from artkit import models as M
from artkit import pixelart as _P

from ..common import palette as P
from ..common import skeleton as S

SCALE = {"prop_bollard": 1.0}

_IRON = _P.Mat("prop_iron", list(P.RAMPS["iron"]), kind="metal", noise=0.14, bevel=1, base=3)
_GLOW = _P.Mat("prop_glow", list(P.RAMPS["opal"]), kind="glow", bevel=0, base=2)


def _bollard():
    """A short cast-iron terrace bollard with an opal-glass lamp on top. Anchor: foot centre."""
    m = M.Model("prop_bollard")
    m.box((-2, 0, -2), (2, 2, 2), _IRON)
    m.box((-1.5, 2, -1.5), (1.5, 11, 1.5), _IRON, grain="y")
    m.box((-2.5, 11, -2.5), (2.5, 14, 2.5), _GLOW, emit=14, shade=False)
    m.box((-2.5, 14, -2.5), (2.5, 15, 2.5), _IRON)
    return m


def models():
    return {"prop_bollard": _bollard()}


def build(canvas, origin=(0, 0, 0)):
    ox, oy, oz = origin
    model = _bollard()
    n = 0
    for z in (-3, 3):
        canvas.add_entity(ox + S.east_wall_x(9) + 3, oy + S.GROUND, oz + z,
                          M.display(model, scale=SCALE["prop_bollard"], brightness=(0, 14)))
        n += 1
    return n
