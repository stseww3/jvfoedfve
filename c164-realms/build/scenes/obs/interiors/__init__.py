"""A7 interiors category (plan ART-PLAN 8). The five first-pass rooms: the star hall, the great dome
room, the chart room, the time room, the engine-house floor. Each: one star piece, three layers of
small pieces (wall, surface, floor), at least one thing moving, at least one thing glowing.

Work packages are modules in this folder (auto-discovered); each may define build/models/pack:
  build(canvas, origin) -> int   dresses the rooms inside the shells main/site leave; returns the
                                  number of display entities placed (budget: 1000 indoors, <=250/room).
  models()              -> {...} room-only models, names prefixed "int_"; shared furniture comes
                                  from the props category.
  pack(pack_dir)        -> []    nothing of its own.

Each room is first built in its own box test scene (build/scenes/obs_int_<room>/), then moved in once
the shell is up. No package yet.
"""
from ..common import assembly

CATEGORY = "interiors"
NS = "c164"
PREFIX = "int_"

_cat = assembly.category(__name__)


def build(canvas, origin=(0, 0, 0)):
    return _cat.build(canvas, origin)


def models():
    return _cat.models()


def pack(pack_dir):
    return _cat.pack(pack_dir)
