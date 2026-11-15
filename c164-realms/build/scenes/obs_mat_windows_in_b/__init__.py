"""Version b of the windows in the room of obs_mat_windows_in: the same room, the same shots.

The linings follow the version of the windows: the net of tall lights on the lit and on the frosted
window, the slats of the blind in place of the curtain's folds. Every shot of this scene has its
twin of the same name in obs_mat_windows_in.

    python -m scenes.obs_mat_windows_in_b       writes shots.json (a copy of the other scene's)
"""
from scenes.obs.materials import _kit as K
from scenes.obs.materials import windows as W
from scenes.obs_mat_windows_in import BIOME, TIME, build, shots  # noqa: F401

VERSIONS = {"windows": "b"}


def build_models():
    return W.models(VERSIONS["windows"])


def write_pack(pack_dir):
    return K.pack_with(pack_dir, **VERSIONS)
