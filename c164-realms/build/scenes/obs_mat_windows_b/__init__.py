"""Version b of the lit windows on the board of obs_mat_windows: the same walls, the same shots.

A redirected block shows one picture in one resource pack, so two versions of a window cannot stand
side by side in one scene. They are compared picture by picture instead: every shot of this scene
has its twin of the same name in obs_mat_windows.

    python -m scenes.obs_mat_windows_b      writes shots.json (a copy of the other scene's)
"""
from scenes.obs.materials import _kit as K
from scenes.obs_mat_windows import BIOME, TIME, build, build_models, layout, shots  # noqa: F401

VERSIONS = {"windows": "b"}


def write_pack(pack_dir):
    return K.pack_with(pack_dir, **VERSIONS)
