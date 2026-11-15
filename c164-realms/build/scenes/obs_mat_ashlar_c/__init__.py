"""Test scene materials/ashlar version c: the same board and shots as obs_mat_ashlar, with the four
families left as the vanilla sandstone the game draws (ashlar version c writes nothing; the families
are claimed in BLOCKS so the stand-ins leave them alone too). This is the stone fallback the card
asks to lay beside a and b, so the manager can see why the observatory repaints the stone.

    python -m scenes.obs_mat_ashlar_c      writes shots.json (the same as obs_mat_ashlar)
"""
from scenes.obs_mat_ashlar import BIOME, Z, TIME, build, build_models, layout, shots  # noqa: F401
from scenes.obs.materials import _kit as K

CATEGORY = "materials"
VERSION = "c"


def write_pack(pack_dir):
    return K.pack_with(pack_dir, ashlar=VERSION)
