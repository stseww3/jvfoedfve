"""Test scene materials/ashlar version b, the default: the same board and shots as obs_mat_ashlar,
the pack built with ashlar version b (the rough stone banded: a channel along every course and no
upright joint; the fine stone, the panel and the emblem as in a). The three-way compare the card
asks for -- see obs_mat_ashlar for the stations.

    python -m scenes.obs_mat_ashlar_b      writes shots.json (the same as obs_mat_ashlar)
"""
from scenes.obs_mat_ashlar import BIOME, Z, TIME, build, build_models, layout, shots  # noqa: F401
from scenes.obs.materials import _kit as K

CATEGORY = "materials"
VERSION = "b"


def write_pack(pack_dir):
    return K.pack_with(pack_dir, ashlar=VERSION)
