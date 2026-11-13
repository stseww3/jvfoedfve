"""A2's look for the observatory (plan ART-PLAN 3.2): one frozen state, the blue hour after sunset.

Game time is locked (place.py runs `tick freeze`), so the whole scene lives at one light state. The
plan asks for three versions on one timeline, switched by changing the time; they are the three
biomes below. The default is the blue hour. A2 keeps this file; the values here are the plan's
numbers as a working starting point and A2 tunes them against the real renders. S2 re-exports
BIOMES/TIMELINES through scenes/obs/mood.py so the drivers (place.py, render.py) find them.
"""
from artkit import mood as M

# plan 3.2 ---------------------------------------------------------------------------------------
ZENITH = "#0d1433"          # the sky overhead: deep indigo
HORIZON = "#383a74"         # the haze at the horizon: blue-purple
AFTERGLOW = "#ffe97c4c"     # a fixed warm band in the west (aarrggbb); does not move with time
FILL = "#7f93d8"            # sky light (fill): cool, pressed to ~a third of day
LAMP = "#ffb45e"            # block light (the main light): warm
AMBIENT = "#161a2c"         # the floor under both; never dead black
CLOUD = "#e8545a86"         # the cloud sea: cool grey-purple (aarrggbb)
CLOUD_Y = 168               # PROVISIONAL: world y of the cloud sea at the mountainside; S2+A2 fix
                            # this against place.py --at (GROUND maps to that y)


def _look(**kw):
    """The still look with single values changed, for comparing versions side by side."""
    base = dict(
        sky=ZENITH, fog=HORIZON, water="#1f3a6e", cloud=CLOUD, sun=FILL, lamp=LAMP, ambient=AMBIENT,
        cloud_height=CLOUD_Y,
        # the hilltop stays crisp; past 60 blocks everything melts into the horizon colour (plan 3.2)
        fog_start=28.0, fog_end=160.0,
        stars=0.6,
    )
    base.update(kw)
    return M.biome(**base)


BIOMES = {
    "obs_blue": _look(),                                             # the blue hour (default)
    "obs_deep": _look(sky="#0a0f28", fog="#272a5a", sun="#6678c0",   # a deeper night
                      ambient="#10131f", stars=0.8),
    "obs_glow": _look(fog="#4a3a66", sun="#8a93c8"),                 # a stronger western afterglow
}

# One body in the sky at a time (artkit.mood.one_body_sky): the comet. Here it is frozen in the
# west above the dome, so a constant angle and a single phase whose texture A2 repaints as a comet.
# A2 replaces this with the tuned arc and the painted phases.
COMET_ANGLE = 118.0         # PROVISIONAL: degrees, low in the west; A2 tunes against the renders
COMET_PHASE = "waning_crescent"

TIMELINES = {
    "obs_dusk": M.timeline({
        # the western afterglow halo, held fixed (plan 3.2: "the halo does not move with time")
        "sunrise_sunset_color": M.track([(0, AFTERGLOW)]),
        # the one body, frozen as the comet
        "moon_angle": M.track([(0, COMET_ANGLE)]),
        "moon_phase": M.track([(0, COMET_PHASE)]),
        # hold the blue hour at every tick so a frozen scene reads the same whatever the shot time
        "sky_color": M.track([(0, ZENITH)]),
        "fog_color": M.track([(0, HORIZON)]),
        "sky_light_color": M.track([(0, FILL)]),
        # fill light pressed to a third of day; never to black (plan 3.2)
        "sky_light_factor": M.track([(0, 0.35)], modifier="maximum"),
        "star_brightness": M.track([(0, 0.6)], modifier="maximum"),
    }),
}
