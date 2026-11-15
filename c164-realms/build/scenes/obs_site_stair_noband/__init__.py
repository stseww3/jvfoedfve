"""obs_site_stair without the walk's band on the stair's treads (site/stair, the switch BAND off):
the treads are one dark stone from cheek to cheek. A0 chose between the two on the pictures
(#28839; 11-16: the band stays) and the scene is kept as the other half of that comparison; every
shot here has its twin of the same name in obs_site_stair.

    python -m scenes.obs_site_stair      writes this scene's shots.json too
"""
from scenes import obs_site_stair as whole
from scenes.obs_site_stair import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, build_models, write_pack  # noqa: F401


def build():
    return whole.build(band=False)


def shots():
    return whole.shots(whole.JUDGED)
