"""The material board with version b of the lit windows: tall lights, two to a block, the light
pooling at the head of each pane; frosted glass with a broken surface; a venetian blind for the
curtain. The master board (obs_mat_board) shows version a, the default: small square lights.

A redirected block shows one picture in one resource pack, so two versions of a window cannot stand
side by side on one board. They are compared picture by picture: every shot of this scene has its
twin of the same name in obs_mat_board (the whole board in its three lights, and the glass tier).

    python -m scenes.obs_mat_board_windows_b      writes shots.json
"""
from scenes.obs_mat_board import BIOME, TIME, build, build_models, compare, pack  # noqa: F401

VERSIONS = {"windows": "b"}


def write_pack(pack_dir):
    return pack(pack_dir, **VERSIONS)


def shots():
    return compare("glass")
