"""A5 large machines category (plan ART-PLAN 7.2). The big movable pieces, each the star of one
view: the great refractor, the dome gear, the orrery, the master/tower clocks and time ball, the
engine and dynamo, the cable car and winch, the radio mast, the meridian circle and astrograph,
recorders.

Work packages are modules in this folder (auto-discovered); each may define build/models/pack:
  build(canvas, origin) -> int   summons the machines placed in the scene; returns how many display
                                  entities (the entity budget: machines get 400).
  models()              -> {...} machine models, names prefixed "mach_" so no file clashes.
  pack(pack_dir)        -> []    the item models come from models().

Movable parts are separate models with a marked axis (plan 7.1); the motion category spins them. No
package yet (no category lead -- the card is in the pool).
"""
from ..common import assembly

CATEGORY = "machines"
NS = "c164"
PREFIX = "mach_"

_cat = assembly.category(__name__)


def build(canvas, origin=(0, 0, 0)):
    return _cat.build(canvas, origin)


def models():
    return _cat.models()


def pack(pack_dir):
    return _cat.pack(pack_dir)
