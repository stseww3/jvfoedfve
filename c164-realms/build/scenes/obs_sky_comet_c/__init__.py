"""Version c of the comet (the wide fan) over the white model of obs_sky_comet: the same blocks, the
same shots.

The moon's slot holds one picture per light, so the versions cannot hang in one sky. They are
compared picture by picture: every shot of this scene has its twins of the same name in
obs_sky_comet (version a) and in the scene of the third version.

    python -m scenes.obs_sky_comet_c      writes shots.json, prints where the comet stands
"""
from scenes.obs.sky import comet
from scenes.obs_sky_comet import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, build, shots, tell, where  # noqa: F401

STYLE = "c"


def write_pack(pack_dir):
    return comet.pack(pack_dir, STYLE)
