"""The material board with version c of the grey-white stone: the four families left as the
sandstone the game draws. This is the stone fallback of ART-PLAN 15, laid beside the painted stone
so that it can be seen what repainting the stone buys. The master board (obs_mat_board) shows
version b, the default.

A redirected block shows one picture in one resource pack, so two versions of a stone cannot stand
side by side on one board. They are compared picture by picture: every shot of this scene has its
twin of the same name in obs_mat_board (the whole board in its three lights, and the stone tier).

    python -m scenes.obs_mat_board_ashlar_c      writes shots.json
"""
from scenes.obs_mat_board import BIOME, TIME, build, build_models, compare, pack  # noqa: F401

VERSIONS = {"ashlar": "c"}


def write_pack(pack_dir):
    return pack(pack_dir, **VERSIONS)


def shots():
    return compare("stone")
