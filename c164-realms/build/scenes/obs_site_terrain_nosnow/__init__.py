"""obs_site_terrain without the mountain's snow (site/terrain, the switch SNOW_ON off).

Every shot here has its twin of the same name in obs_site_terrain. The snow is measured on the
difference between the two pictures of a view (c235 #32498: where the snow is, and how light it
is against the building's stone).
"""
from scenes import obs_site_terrain as whole
from scenes.obs_site_terrain import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, build_models, write_pack  # noqa: F401


def build():
    return whole.build(snow=False)
