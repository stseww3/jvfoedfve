"""A4 site and outbuildings category (plan ART-PLAN 4, 5.3). The hilltop and cloud line, the terrace
paving, meridian, balustrades, the grand stair, retaining walls and the lower platform; the shells
of the power house, cable-car station and footbridge, meridian hut, water tower, weather station,
lookout; a little high-alpine planting and snow.

Work packages are modules in this folder (auto-discovered); each may define build/models/pack:
  build(canvas, origin) -> int   lays the ground and the outbuilding shells; returns the number of
                                  display entities placed (terrace lamps, meridian markers).
  models()              -> {}    outbuilding-only models, names prefixed "site_".
  pack(pack_dir)        -> []    uses only occupancy-table blocks.

Framework demo so far: ground.py lays the two terraces so the masses have a floor. The terrain,
cloud line and outbuildings are A4's real work (no category lead yet -- the card is in the pool).
"""
from ..common import assembly

CATEGORY = "site"
NS = "c164"
PREFIX = "site_"

_cat = assembly.category(__name__)


def build(canvas, origin=(0, 0, 0)):
    return _cat.build(canvas, origin)


def models():
    return _cat.models()


def pack(pack_dir):
    return _cat.pack(pack_dir)
