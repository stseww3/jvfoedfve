"""The look of the test scene: the blue hour, the look the map is finished in (A0 #43929)."""
from scenes.obs.sky.mood import BIOMES, TIMELINES  # noqa: F401
from scenes.obs.sky import mood as look

LOOK = look.DEFAULT
TIME = look.tick(LOOK)
