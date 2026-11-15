"""Work package materials/respack-redirect: the base the other material packages stand on.

The tool itself is artkit.respack.redirect_block (public). What this module adds to the pack:

  - a stand-in for every repainted block of the occupancy table that no package has painted yet
    (_standin.py), so the whole table is redirected from the first day;
  - the audit of everything the category has written (_kit.audit): block states only for repainted
    blocks, nothing of the game's replaced, no missing model or picture, palette colours only. A broken
    rule stops the pack from being made.

It runs after the packages that paint for real (ORDER), so the audit sees their files too.
"""
from . import _kit as K
from . import _standin

ORDER = 99

# vanilla pictures this category replaces outright, as paths under assets/minecraft/textures/. A block
# picture is only replaced when no block that keeps its vanilla look shows it; so far none is.
REPLACED = ()


def pack(pack_dir):
    return _standin.pack(pack_dir) + [K.audit(pack_dir, REPLACED)]
