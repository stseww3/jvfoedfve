"""obs_site_stair without the lamps of the way in: no lamp on the yard's pads nor on the stair's
pedestals, and the props line is not asked for the site's lamps. What the stone does alone in the
blue hour (c235's review of site/stair asks for the judged views with the lamps and without);
every shot here has its twin of the same name in obs_site_stair.

    python -m scenes.obs_site_stair      writes this scene's shots.json too
"""
from scenes import obs_site_stair as whole
from scenes.obs_site_stair import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, build_models, write_pack  # noqa: F401


def build():
    return whole.build(lit=False)


def shots():
    return whole.shots(whole.JUDGED)
