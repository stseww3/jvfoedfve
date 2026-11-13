"""The look of the observatory: sky, fog, the colours of light, the afterglow (ART-PLAN 3.2;
plan/parts/sky.md sections 1 and 2; card plan/packages/sky/look.md).

One biome, `obs_blue`, and one timeline, `obs_looks`. The plan asks for three light versions on one
timeline, switched by changing the time. They are three moments of the day here, each held over a
plateau, so a stopped clock always rests on a complete set of values, and a shot picks its version
with "time" in shots.json:

    14000  blue   the blue hour, the plan's values. The whole first half of the day shows it as
                  well, so a shot without a time (the drivers default to noon) gets it.
    18000  deep   a deeper night
    12900  glow   a stronger afterglow

The vanilla day timeline darkens sky, fog and clouds at night and turns sun, moon and stars. Ours
comes after it in the dimension's tag and overrides every visual track it touches, so the day cycle
no longer shows. A timeline belongs to the dimension, not to a biome: with everything on the
timeline the look does not depend on where the biome fill ends. The biome carries the blue hour
once more as a fallback.

A look states what is seen: the colour overhead and the colour of the horizon band. The game mixes
sky colour and fog colour into each other on the way to the screen, so sky_color and fog_color are
solved from the two seen colours (derive(); the formulas are in plan/parts/sky-notes.md 3).

Biomes and timelines are registry files: after a change here the server restarts and the client
reconnects (place.py says so). Other sky packages and the checks read LOOKS and values().
"""
from artkit import mood as M

GROUND_Y = 200              # world y of the scene origin (place.py --at); every plot uses it
CLOUD_TOP = -28             # scene y of the top of the vanilla cloud layer; the block clouds of
CLOUD_THICKNESS = 4         # sky/cloudsea lie on it with their sheet top at -26
CLOUD_ALPHA = 0.94
CLOUD_FOG_END = 768.0       # the layer fades to nothing at this distance
LAMP = "#ffb45e"            # the one lamp colour (tint of block light)
FOG_START, FOG_END = 60.0, 192.0   # crisp nearby; from 60 blocks on things melt into the horizon colour
MOON_ANGLE = 42.0           # the comet sits in the moon's slot: sprite centre 48 degrees up in the west
STAR_ANGLE = 0.0
WATER = "#1f3a6e"

# What is seen in each version. zenith/horizon: the sky overhead and the band at the horizon when
# not facing west. glow: the afterglow fan in the west and how strongly it stains the fog there.
# sun_angle places the afterglow's hot core (the sun's slot), 90 = on the western horizon.
LOOKS = {
    "blue": dict(tick=14000, zenith="#0d1433", horizon="#383a74", sky_fog_end=96.0,
                 glow="#e97c4c", glow_alpha=0.45, sun_angle=92.0, moon_phase="full_moon", stars=0.60,
                 sky_light="#7f93d8", sky_factor=0.40, ambient="#161a2c", cloud="#565c8c"),
    "deep": dict(tick=18000, zenith="#080c22", horizon="#24274f", sky_fog_end=128.0,
                 glow="#c8553a", glow_alpha=0.25, sun_angle=97.0, moon_phase="waning_gibbous", stars=0.95,
                 sky_light="#7388d8", sky_factor=0.26, ambient="#141829", cloud="#3b4170"),
    "glow": dict(tick=12900, zenith="#141a44", horizon="#4a4484", sky_fog_end=80.0,
                 glow="#f0864f", glow_alpha=0.85, sun_angle=90.0, moon_phase="third_quarter", stars=0.30,
                 sky_light="#8a96d8", sky_factor=0.48, ambient="#191c31", cloud="#6a6a9a"),
}
DEFAULT = "blue"

# (tick, look): plateaus with short ramps between them; wraps round to the first entry
KEYS = [(0, "blue"), (12000, "blue"), (12600, "glow"), (13200, "glow"), (13600, "blue"),
        (15000, "blue"), (16000, "deep"), (21000, "deep"), (22000, "blue")]
# values that cannot be blended (the moon phase picture) switch in the middle of each ramp
STEPS = [(0, "blue"), (12300, "glow"), (13400, "blue"), (15500, "deep"), (21500, "blue")]
# The eight moon phase pictures are eight slots. Three hold the comet for the three looks; for a few
# ticks in the morning the timeline shows a fourth, which sky/comet.py paints as a test card to
# check which way up the game draws the pictures. Everything else at that moment is the blue hour.
TEST_TICKS, TEST_PHASE = (3000, 3200), "new_moon"


def _rgb(text):
    h = text.lstrip("#")
    return [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]


def _hex(rgb):
    return "#" + "".join(f"{max(0, min(255, int(round(c * 255.0)))):02x}" for c in rgb)


def _argb(text, alpha):
    return f"#{max(0, min(255, int(round(alpha * 255.0)))):02x}" + text.lstrip("#")


def mix_share(sky_fog_end, render_chunks=32):
    """AtmosphericFogEnvironment: how far the fog colour is drawn towards the sky colour."""
    e = min(sky_fog_end / 16.0, float(render_chunks))
    return 1.0 - (0.25 + 0.75 * min(1.0, e / 32.0)) ** 0.25


def derive(zenith, horizon, sky_fog_end):
    """(sky_color, fog_color) to write so that the zenith and the horizon show the wanted colours.

    The sky dome is a plane 16 blocks overhead that takes fog by distance: straight up it shows the
    fog colour to a share of 16 / sky_fog_end. The fog colour on screen is the attribute drawn
    towards the sky colour by mix_share(). Both are undone here.
    """
    z = 16.0 / sky_fog_end
    m = mix_share(sky_fog_end)
    seen_sky, seen_fog = _rgb(zenith), _rgb(horizon)
    sky = [min(1.0, max(0.0, (a - z * b) / (1.0 - z))) for a, b in zip(seen_sky, seen_fog)]
    fog = [min(1.0, max(0.0, (b - m * s) / (1.0 - m))) for b, s in zip(seen_fog, sky)]
    return _hex(sky), _hex(fog)


def values(look=DEFAULT):
    """The attribute values of one look, keyed by the name after "minecraft:visual/"."""
    v = LOOKS[look]
    sky, fog = derive(v["zenith"], v["horizon"], v["sky_fog_end"])
    return {
        "sky_color": sky, "fog_color": fog, "sky_fog_end_distance": v["sky_fog_end"],
        "sunrise_sunset_color": _argb(v["glow"], v["glow_alpha"]),
        "sun_angle": v["sun_angle"], "moon_angle": MOON_ANGLE, "star_angle": STAR_ANGLE,
        "moon_phase": v["moon_phase"], "star_brightness": v["stars"],
        "sky_light_color": v["sky_light"], "sky_light_factor": v["sky_factor"],
        "ambient_light_color": v["ambient"], "cloud_color": _argb(v["cloud"], CLOUD_ALPHA),
        "block_light_tint": LAMP, "fog_start_distance": FOG_START, "fog_end_distance": FOG_END,
        "cloud_height": float(GROUND_Y + CLOUD_TOP - CLOUD_THICKNESS),
        "cloud_fog_end_distance": CLOUD_FOG_END,
    }


def _biome():
    a = values(DEFAULT)
    named = dict(sky="sky_color", fog="fog_color", cloud="cloud_color", sun="sky_light_color",
                 lamp="block_light_tint", ambient="ambient_light_color", fog_start="fog_start_distance",
                 fog_end="fog_end_distance", sky_fog_end="sky_fog_end_distance", cloud_height="cloud_height")
    rest = {M.VISUAL + k: v for k, v in a.items() if k not in named.values()}
    return M.biome(water=WATER, extra=rest, **{arg: a[key] for arg, key in named.items()})


def _timeline():
    per_look = {name: values(name) for name in LOOKS}
    tracks = {}
    for key, first in per_look[DEFAULT].items():
        if all(per_look[name][key] == first for name in LOOKS):
            tracks[key] = M.track([(0, first)])
        elif isinstance(first, str) and not first.startswith("#"):
            tracks[key] = M.track([(t, per_look[name][key]) for t, name in STEPS])
        else:
            tracks[key] = M.track([(t, per_look[name][key]) for t, name in KEYS])
    phase = [(t, per_look[name]["moon_phase"]) for t, name in STEPS]
    phase += [(TEST_TICKS[0], TEST_PHASE), (TEST_TICKS[1], per_look[DEFAULT]["moon_phase"])]
    tracks["moon_phase"] = M.track(sorted(phase))
    out = M.timeline(tracks)
    out["time_markers"] = {f"c164art:{name}": {"show_in_commands": True, "ticks": v["tick"]}
                           for name, v in LOOKS.items()}
    return out


BIOMES = {"obs_blue": _biome()}
TIMELINES = {"obs_looks": _timeline()}
