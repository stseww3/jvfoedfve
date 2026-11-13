"""The look of the sky observatory scene: one biome for the still values, one timeline for the day.

Run by build/place.py, which writes these into the world's data pack. They are registry entries,
so a change needs a server restart and a client reconnect, not just /reload.

The vanilla sunset is switched off: it is a tilted disc around the camera, and with nothing but air
below an island the camera sees its far side as a flat stain over the lower half of the picture,
in a colour the fog on distant things does not share. The timeline paints dawn and dusk itself
through sky colour (overhead), fog colour (horizon, everything below it, and distant things) and the
colour of the light from the sky.
"""
from artkit import mood as M

NO_CLOUDS = "#00ffffff"   # the vanilla cloud layer is a flat sheet; sky.py places real clouds instead
DAY_SKY, DAY_FOG = "#3d8fe8", "#b2d6f8"


def _look(**kw):
    """The scene's look with single values changed, for trying variants side by side."""
    base = dict(
        sky=DAY_SKY, fog=DAY_FOG, water="#42b8dc", cloud=NO_CLOUDS, lamp="#ffc278",
        grass="#9fcf5e", foliage="#86bd50",
        dry_foliage="#d9a441",   # fallen leaves: the gold of the tree on the lookout
        # haze: the island stays crisp from the usual viewpoints, the far cloud banks fade out
        fog_start=70.0, fog_end=480.0,
        # fill light: with open sky on every side nothing is black; shadows on the clouds and the
        # underside of the island turn blue-grey instead
        ambient="#33426a",
    )
    base.update(kw)
    return M.biome(**base)


# Variants for comparison go in here too, e.g. "skyobs_clear": _look(fog_start=110.0, fog_end=900.0),
# and are swapped in with place.py --biome-only --biome <name>. Refill the scene's own biome before
# taking a variant out again, or the chunks still filled with it fall back to the default biome.
BIOMES = {
    "skyobs": _look(),
}

# One body in the sky at a time (see artkit.mood.one_body_sky): which moon phase texture stands for
# what. sky.py paints them.
PHASES = {
    "sun": "waxing_gibbous", "sun_warm": "waning_crescent", "sun_half": "first_quarter",
    "sun_faint": "waxing_crescent", "blank": "new_moon", "moon_faint": "third_quarter",
    "moon_half": "waning_gibbous", "moon": "full_moon",
}
# The sun crosses the horizon near ticks 12780 and 23215. It warms on the way down, sinks in plain
# view (there is no ground to hide it) and fades out once it is some 12 degrees below; then the
# moon fades in, already 15 degrees up in the east. Dawn mirrors that.
BODY = M.one_body_sky(
    dusk=13600, dawn=22400,
    day=[(t, PHASES[p]) for t, p in (
        (22450, "sun_faint"), (22550, "sun_half"), (22700, "sun_warm"), (800, "sun"), (11200, "sun_warm"),
        (13400, "sun_half"), (13480, "sun_faint"), (13550, "blank"))],
    night=[(t, PHASES[p]) for t, p in (
        (13650, "moon_faint"), (13750, "moon_half"), (13900, "moon"), (22150, "moon_half"),
        (22250, "moon_faint"), (22350, "blank"))],
)

TIMELINES = {
    "skyobs_day": M.timeline({
        "sunrise_sunset_color": M.track([(0, "#00000000")]),
        "moon_angle": BODY["moon_angle"],
        "moon_phase": BODY["moon_phase"],
        "sky_color": M.track([
            (200, "#4a7fd8"), (1300, DAY_SKY), (10700, DAY_SKY), (11700, "#4384dc"), (12300, "#4a5fb4"),
            (12800, "#34387f"), (13300, "#161d55"), (13700, "#0b1238"), (22300, "#0b1238"), (23000, "#1b2460"),
            (23500, "#33479a"),
        ]),
        "fog_color": M.track([
            (400, "#f6e2cc"), (1300, DAY_FOG), (10700, DAY_FOG), (11500, "#d6e2f2"), (11900, "#f0e4da"),
            (12150, "#ffd2a6"), (12400, "#ffb27a"), (12750, "#f28a66"), (13100, "#a05f86"), (13400, "#3f3470"),
            (13700, "#151a40"), (22300, "#151a40"), (22900, "#4b3f78"), (23350, "#e08a72"), (23800, "#ffc39a"),
        ]),
        "sky_light_color": M.track([
            (100, "#ffe2c0"), (700, "#fff4e4"), (1400, "#ffffff"), (10800, "#ffffff"), (11600, "#fff0d8"),
            (12100, "#ffdcae"), (12500, "#ffc49a"), (12900, "#c9a0c0"), (13300, "#8f8fe8"), (13700, "#7a7aff"),
            (22300, "#7a7aff"), (22800, "#9a8fe0"), (23200, "#e0a8b0"), (23600, "#ffc8a0"),
        ]),
        # the fill light from the open sky all around goes down with the sun
        "ambient_light_color": M.track([
            (300, "#ffffff"), (11900, "#ffffff"), (13400, "#3c3c3c"), (22500, "#3c3c3c"), (23700, "#ffffff"),
        ], modifier="multiply"),
        # holds the daylight a little longer into the dusk than vanilla, and lifts the night slightly
        "sky_light_factor": M.track([
            (500, 1.0), (11800, 1.0), (12300, 0.85), (12800, 0.6), (13300, 0.38), (13700, 0.27),
            (22300, 0.27), (22900, 0.4), (23500, 0.7),
        ], modifier="maximum"),
        "star_brightness": M.track([
            (11900, 0.0), (12500, 0.35), (13200, 1.0), (22600, 1.0), (23300, 0.3), (23800, 0.0),
        ], modifier="maximum"),
    }),
}
