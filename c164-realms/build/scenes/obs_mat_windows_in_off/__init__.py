"""obs_mat_windows_in built without the linings (windows.LINING off): the same room, the same shots.

The proof A0 asked for (group g2 #32717): a lining lies behind glass that is not seen through, so a
front has to look the same with it and without. Every out_* picture of this scene is held against
its twin of the same name in obs_mat_windows_in with sky/_tones.py --diff; not one pixel may
differ. The in_* pictures show the room as it was before: the lit windows as boxes of light.

    python -m scenes.obs_mat_windows_in_off     writes shots.json (a copy of the other scene's)
"""
from scenes import obs_mat_windows_in as _lined
from scenes.obs.materials import windows as W
from scenes.obs_mat_windows_in import BIOME, TIME, build_models, shots, write_pack  # noqa: F401


def build():
    with W.unlined():
        return _lined.build()
