"""Framework demo work package: palette-painted variants for the dressed-stone and plate blocks,
jar-free, so the pipeline generates end to end before A1's real redirect lands. A1 replaces this
with the full redirect of every occupancy-table block (see the category docstring)."""
from artkit import respack

from ..common import blocks as B
from ..common import palette as P

NS = "c164"

_DEMO = [
    (B.ASHLAR_FINE.block, "ashlar", "ashlar_fine"),
    (B.IRON_PLATE, "iron", "iron_plate"),
]


def pack(pack_dir):
    out = []
    for block, mat_name, tex_name in _DEMO:
        variants = [(P.mat(mat_name).paint(16, 16, seed=s), 1) for s in (1, 2, 3)]
        out.append(respack.cube_variants(pack_dir, block, variants, name=tex_name, ns=NS))
    return out
