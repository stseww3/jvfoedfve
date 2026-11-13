"""Motion and sound category (plan/PIPELINE.md 2.1 and 4.2): what turns, swings, puffs and hums --
the loop framework (interpolated transformations, timing), where sounds sit, smoke and steam.

Work packages are modules in this folder (auto-discovered); each may define build/models/pack:
  build(canvas, origin) -> int   places the entities that move (markers, displays); returns the
                                  display-entity count.
  models()              -> {...} models of its own, names prefixed "mot_".
  pack(pack_dir)        -> [str] sounds and particles ONLY: assets/c164/sounds/*, sounds.json,
                                  assets/c164/particles/*, assets/c164/textures/particle/*.

Animated block pictures are the materials category's (it owns the block pictures). The functions
that drive the loops are data-pack files; how a package hands those over is settled with the
category's parts file (plan/roles/INTERFACE.md 2). No package yet.
"""
from ..common import assembly

CATEGORY = "motion"
NS = "c164"
PREFIX = "mot_"

_cat = assembly.category(__name__)


def build(canvas, origin=(0, 0, 0)):
    return _cat.build(canvas, origin)


def models():
    return _cat.models()


def pack(pack_dir):
    return _cat.pack(pack_dir)
