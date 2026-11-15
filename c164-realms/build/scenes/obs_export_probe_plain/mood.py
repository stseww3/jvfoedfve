"""What the offline renderer reads to draw this scene under the game's own sky. The scene is only
drawn, never placed: the trial save without the look (T2) is made from scenes.obs_export_probe with
tools/export.py --look off, which writes no biome and no timeline.

BIOMES: the game's void biome, copied from the 26.3 jar (data/minecraft/worldgen/biome/the_void.json,
without what only matters to mobs).

TIMELINES: where the game's day timeline has the moon, the sun and the stars at tick 20370. The
renderer does not follow that timeline's angle tracks (two keyframes on one tick, a full turn
between them, which it reads as no turn at all), so the three angles are written out here. They
come from the track's easing, cubic_bezier(0.362, 0.241, 0.638, 0.759) over the day from tick 6000:
moon 180 + 360 e, sun and stars 360 e. At tick 20370 that is 42 degrees for the moon, the angle our
look holds it at, so the comet's picture stands 48 degrees up, due west, in both trial saves.
"""

BIOMES = {
    "the_void": {
        "attributes": {"minecraft:visual/sky_color": "#7ba4ff"},
        "carvers": [],
        "downfall": 0.5,
        "effects": {"water_color": "#3f76e4"},
        "features": [],
        "has_precipitation": False,
        "temperature": 0.5,
    },
}

TIMELINES = {
    "probe_plain_angles": {
        "clock": "minecraft:overworld",
        "period_ticks": 24000,
        "tracks": {
            "minecraft:visual/moon_angle": {"keyframes": [{"ticks": 0, "value": 42.0}]},
            "minecraft:visual/sun_angle": {"keyframes": [{"ticks": 0, "value": 222.0}]},
            "minecraft:visual/star_angle": {"keyframes": [{"ticks": 0, "value": 222.0}]},
        },
    },
}
