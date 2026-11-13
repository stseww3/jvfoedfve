"""A6 props library category (plan ART-PLAN 7.3). The eight families of small models -- lamps,
pipework, door and window ironwork, electrics and signs, small instruments, furniture, paper goods,
emblems -- and the functions that place them. First batch: lamps, door/window ironwork, pipework.

Work packages are modules in this folder (auto-discovered); each may define build/models/pack:
  build(canvas, origin) -> int   places this package's dressing; returns the display-entity count.
  models()              -> {...} the package's models, names prefixed "prop_" so no file clashes.
  pack(pack_dir)        -> []    the item models come from models(); nothing else of its own.

Framework demo so far: lamps.py ships one model (a terrace bollard) and places two, to exercise the
whole display-entity path end to end. The real families, each with a shared motif and a gallery test
scene, are A6's work, one module per family. Shared helpers can live in _kit.py (skipped by the
auto-discovery).
"""
from ..common import assembly

CATEGORY = "props"
NS = "c164"                     # artkit.models writes item models under this namespace
PREFIX = "prop_"

_cat = assembly.category(__name__)


def build(canvas, origin=(0, 0, 0)):
    return _cat.build(canvas, origin)


def models():
    return _cat.models()


def pack(pack_dir):
    return _cat.pack(pack_dir)
