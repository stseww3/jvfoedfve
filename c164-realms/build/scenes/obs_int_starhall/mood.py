"""Stand-in blue-hour look for the star hall test scene (placeholder for A2 / c177).

Values are the plan's (ART-PLAN.md 3.2): deep-indigo zenith, blue-violet horizon, cool sky light,
warm block light, a dark-but-not-black floor. A single-keyframe timeline locks the blue hour so the
interior reads the warm/cool split regardless of the shot tick. A2 owns the real observatory biome
and timeline; S2 swaps this out when the room moves into the merged scene.
"""
from artkit import mood as M

BIOMES = {
    "obs_int": M.biome(
        sky="#0d1433", fog="#383a74", sun="#7f93d8", lamp="#ffb45e", ambient="#161a2c",
        water="#1f3a6e", cloud="#00ffffff", fog_start=24.0, fog_end=200.0, stars=0.6,
    ),
}

TIMELINES = {
    "obs_int_blue": M.timeline({
        "sky_color": M.track([(0, "#0d1433")]),
        "fog_color": M.track([(0, "#383a74")]),
        "sky_light_color": M.track([(0, "#7f93d8")]),
        "ambient_light_color": M.track([(0, "#2a2f40")], modifier="multiply"),
        "sky_light_factor": M.track([(0, 0.3)], modifier="maximum"),
        "star_brightness": M.track([(0, 0.6)], modifier="maximum"),
    }),
}
