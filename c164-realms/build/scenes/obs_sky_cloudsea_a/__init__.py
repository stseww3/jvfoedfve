"""Version "a" of the sea of clouds on the hilltop of obs_sky_cloudsea: the vanilla cloud layer
alone, repainted denser, no block clouds. The same hilltop, the same shots; every picture has its
twin of the same name in obs_sky_cloudsea ("c") and obs_sky_cloudsea_b ("b").

The offline renderer does not draw the vanilla layer, so offline this is the bare hilltop in fog --
which is also what this version leaves when the player switches the clouds off. It is judged on
the real client.

    python -m scenes.obs_sky_cloudsea_a     # rewrites shots.json (a copy of the other scene's)
"""
from scenes import obs_sky_cloudsea as _base
from scenes.obs_sky_cloudsea import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, shots  # noqa: F401

VERSION = "a"


def build():
    return _base.build(VERSION)


def write_pack(pack_dir):
    return _base.write_pack(pack_dir, VERSION)
