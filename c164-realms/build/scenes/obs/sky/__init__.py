"""A2 light, sky and distance category (plan ART-PLAN 3.2). Owns the sky/fog/light colours, the
comet, the cloud sea, the stars, the invisible light-source placement rules and the three light
versions.

Work packages are modules in this folder (auto-discovered); each may define build/models/pack:
  build(canvas, origin) -> int   places the invisible `light` source blocks (plan 3.2, three ranks).
  models()              -> {}    no display entities.
  pack(pack_dir)        -> [str] environment textures ONLY (the comet/phase pictures under
                                  assets/minecraft/textures/environment/*, the denser cloud sheet).

The look itself (biomes, timelines) lives in mood.py -- not a work package, skipped by the
auto-discovery -- and is re-exported by scenes/obs/mood.py for the drivers. No package yet.
"""
from ..common import assembly

CATEGORY = "sky"
NS = "minecraft"               # environment textures replace vanilla ones
PREFIX = "sky_"

_cat = assembly.category(__name__)


def build(canvas, origin=(0, 0, 0)):
    return _cat.build(canvas, origin)


def models():
    return _cat.models()


def pack(pack_dir):
    return _cat.pack(pack_dir)
