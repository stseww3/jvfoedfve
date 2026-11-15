"""The material board with version a of the grey-white stone: the rough stone jointed all round, a
stone to a block. The master board (obs_mat_board) shows version b, the default: the rough stone in
long horizontal channels with no upright joint.

A redirected block shows one picture in one resource pack, so two versions of a stone cannot stand
side by side on one board. They are compared picture by picture: every shot of this scene has its
twin of the same name in obs_mat_board (the whole board in its three lights, and the stone tier).

    python -m scenes.obs_mat_board_ashlar_a      writes shots.json
"""
from scenes.obs_mat_board import BIOME, TIME, build, build_models, compare, pack  # noqa: F401

VERSIONS = {"ashlar": "a"}


def write_pack(pack_dir):
    return pack(pack_dir, **VERSIONS)


def shots():
    return compare("stone")
