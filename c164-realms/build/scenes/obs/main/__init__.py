"""A3 main building category (plan ART-PLAN 5, skeleton R1 0.3). The elevation grammar and the
shells: the long main building, the rotunda and great dome, the clock tower, the small dome; floors,
stairs and door openings; empty room shells for the interiors category.

Work packages are modules in this folder (auto-discovered); each may define build/models/pack:
  build(canvas, origin) -> int   lays the blocks of the shells; returns 0 (no display entities here;
                                  the door, window frames and dressing are props/machines/interiors).
  models()/pack()                usually empty; the shells use only occupancy-table blocks.

Framework demo so far: massing.py is the M3 white-model massing on the skeleton grid. The elevation
grammar (order.py / wall engine), the three-depth section, windows and openings are A3's real work,
one module per work package.
"""
from ..common import assembly

CATEGORY = "main"
NS = "c164"
PREFIX = "bld_"

_cat = assembly.category(__name__)


def build(canvas, origin=(0, 0, 0)):
    return _cat.build(canvas, origin)


def models():
    return _cat.models()


def pack(pack_dir):
    return _cat.pack(pack_dir)
