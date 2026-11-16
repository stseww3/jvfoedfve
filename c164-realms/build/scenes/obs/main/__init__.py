"""A3 main building category (plan ART-PLAN 5, skeleton R1 0.3). The elevation grammar and the
shells: the long main building, the rotunda and great dome, the clock tower, the small dome; floors,
stairs and door openings; empty room shells for the interiors category.

Work packages are modules in this folder (auto-discovered); each may define build/models/pack:
  build(canvas, origin) -> int   lays the blocks of the shells and returns the display entities it
                                  placed. In the first round that was 0 for a shell, which was
                                  blocks only (the door, window frames and dressing are props/
                                  machines/interiors), with one exception: the clock tower's mast,
                                  its wind cups and its vane, three models of main/tower (A0,
                                  11-15 20:47; the vane a model of its own since round two): too
                                  thin for blocks, and part of the skyline. Since round two
                                  (plan/round2.md, plan/fine.md) a shell's own moving parts and
                                  its own fine parts, the mid and the near layer, are the shell
                                  package's display entities: the ventilators of main/roofworks,
                                  the windows where somebody is at work of main/facade, the
                                  dome's seams and rivets of main/dome. What hangs on a shell
                                  and is another line's stays that line's.
  models()/pack()                the models of those parts, named bld_<package>_...; the shells
                                  themselves use only occupancy-table blocks.

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
