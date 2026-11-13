"""A1 materials category (plan ART-PLAN 6). Owns the look of every repainted block in the occupancy
table: stone, cast iron, windows, the 16 instrument panels, brass, old copper, small pieces,
animated textures and the footstep sounds.

Work packages are modules in this folder (auto-discovered, see common/assembly.py). Each may define:
  build(canvas, origin) -> int   materials paints blocks, it does not place them: returns 0.
  models()              -> {}    no display entities (animated panels are blocks).
  pack(pack_dir)        -> [str] writes this category's resource-pack files ONLY:
                                   assets/minecraft/blockstates/<block>.json   (redirects)
                                   assets/minecraft/models/block/<block>.json
                                   assets/<NS>/textures/block/*.png            (the paint)
                                   assets/minecraft/textures/block/*.png       (replaced vanilla)
                                 No other category writes under these paths.

Framework demo so far: stone.py repaints two blocks from the palette, jar-free. The real work --
reading each vanilla block-state/model file and redirecting it, the 16 panels, animation, sounds --
is A1's, one module per work package.
"""
from ..common import assembly

CATEGORY = "materials"
NS = "c164"                     # the custom namespace this category's block textures live under
PREFIX = "mat_"                 # model-name prefix, if a package ever needs a display entity

_cat = assembly.category(__name__)


def build(canvas, origin=(0, 0, 0)):
    return _cat.build(canvas, origin)


def models():
    return _cat.models()


def pack(pack_dir):
    return _cat.pack(pack_dir)
