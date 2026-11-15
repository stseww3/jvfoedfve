"""Version "b" of the sea of clouds on the hilltop of obs_sky_cloudsea: the block sea alone, the
vanilla cloud layer blanked, the far distance left to the fog. The same hilltop, the same shots;
every picture has its twin of the same name in obs_sky_cloudsea ("c") and obs_sky_cloudsea_a ("a").

The offline renderer does not draw the vanilla layer, so offline this is the same picture as "c".
It is judged on the real client, where it is also what "c" becomes when the player switches the
clouds off.

    python -m scenes.obs_sky_cloudsea_b     # rewrites shots.json (a copy of the other scene's)
"""
from scenes import obs_sky_cloudsea as _base
from scenes.obs_sky_cloudsea import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, shots  # noqa: F401

VERSION = "b"


def build():
    return _base.build(VERSION)


def write_pack(pack_dir):
    return _base.write_pack(pack_dir, VERSION)
