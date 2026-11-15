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

A few short moments in the morning hold trials: one value changed, to be compared with its look by
changing the time (TRIALS). tick("deep"), tick("pink") give the times.

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
# sun_angle only says on which side the afterglow lies (west while its sine is positive): the sun's
# own picture is painted out. The concept is the hour after sunset, so nothing in the west may read
# as a sun's disc.
#
# The three have to be told apart at the size of a stamp, so they differ in everything at once:
#   blue  the plan's values: cool blue-grey walls under a deep blue sky, a rose band in the west
#   deep  the walls sink to dark navy and the lamps carry the picture; near-black sky, every star,
#         the brightest comet, only an ember left in the west
#   glow  the walls take a mauve light and stand brighter than the lamps' wash; violet sky that
#         burns orange in the west, hardly a star, a faint comet
LOOKS = {
    "blue": dict(tick=14000, zenith="#0d1433", horizon="#383a74", sky_fog_end=96.0,
                 glow="#e97c4c", glow_alpha=0.45, sun_angle=92.0, moon_phase="full_moon", stars=0.60,
                 sky_light="#7f93d8", sky_factor=0.40, ambient="#161a2c", cloud="#565c8c"),
    "deep": dict(tick=18000, zenith="#05081a", horizon="#191c40", sky_fog_end=128.0,
                 glow="#c8553a", glow_alpha=0.15, sun_angle=97.0, moon_phase="waning_gibbous", stars=1.0,
                 sky_light="#6a80d8", sky_factor=0.14, ambient="#141829", cloud="#2c3160"),
    "glow": dict(tick=12900, zenith="#1c1e50", horizon="#5a4a86", sky_fog_end=80.0,
                 glow="#f0864f", glow_alpha=0.85, sun_angle=90.0, moon_phase="third_quarter", stars=0.15,
                 sky_light="#a89ad2", sky_factor=0.58, ambient="#1c1b31", cloud="#7d6f9c"),
}
DEFAULT = "blue"

# (tick, look): plateaus with short ramps between them; wraps round to the first entry
KEYS = [(0, "blue"), (12000, "blue"), (12600, "glow"), (13200, "glow"), (13600, "blue"),
        (15000, "blue"), (16000, "deep"), (21000, "deep"), (22000, "blue")]
# values that cannot be blended (the moon phase picture) switch in the middle of each ramp
STEPS = [(0, "blue"), (12300, "glow"), (13400, "blue"), (15500, "deep"), (21500, "blue")]

# Trials: a look with a few values changed, held for 200 ticks in the morning, which the map never
# shows. Changing the time puts a trial next to the look it varies, on the same blocks and without
# a restart. Noon stays the blue hour: the drivers take a shot without a time at noon.
#   card  the moon's slot shows a test card (sky/comet.py paints it into the new moon's picture):
#         which way up the game draws the picture is read off it
#   pink  the afterglow in the plan's second colour
#   near, far  the fog ending sooner and later, to read off the row of posts on the light board
TRIALS = {
    "card": dict(of="blue", tick=3100, moon_phase="new_moon"),
    "pink": dict(of="blue", tick=4100, glow="#e9706a"),
    "near": dict(of="blue", tick=5100, fog_end=144.0),
    "far": dict(of="blue", tick=7100, fog_end=256.0),
}
TRIAL_HOLD, TRIAL_RAMP = 100, 50     # held from tick - 100 to tick + 100, blended over 50 ticks each side


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


def look(name=DEFAULT):
    """A look's table of what is seen; a trial's is its look's with the trial's changes."""
    if name in LOOKS:
        return LOOKS[name]
    trial = TRIALS[name]
    return dict(LOOKS[trial["of"]], **{k: v for k, v in trial.items() if k != "of"})


def tick(name=DEFAULT):
    """The time that shows a look or a trial."""
    return look(name)["tick"]


def values(name=DEFAULT):
    """The attribute values of a look or a trial, keyed by the name after "minecraft:visual/"."""
    v = look(name)
    sky, fog = derive(v["zenith"], v["horizon"], v["sky_fog_end"])
    return {
        "sky_color": sky, "fog_color": fog, "sky_fog_end_distance": v["sky_fog_end"],
        "sunrise_sunset_color": _argb(v["glow"], v["glow_alpha"]),
        "sun_angle": v["sun_angle"], "moon_angle": MOON_ANGLE, "star_angle": STAR_ANGLE,
        "moon_phase": v["moon_phase"], "star_brightness": v["stars"],
        "sky_light_color": v["sky_light"], "sky_light_factor": v["sky_factor"],
        "ambient_light_color": v["ambient"], "cloud_color": _argb(v["cloud"], CLOUD_ALPHA),
        "block_light_tint": LAMP,
        "fog_start_distance": v.get("fog_start", FOG_START), "fog_end_distance": v.get("fog_end", FOG_END),
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


def _plateau(at):
    """The look whose plateau holds a tick."""
    before = [name for t, name in KEYS if t <= at][-1]
    after = ([name for t, name in KEYS if t > at] or [KEYS[0][1]])[0]
    if before != after:
        raise ValueError(f"tick {at} lies on a ramp between {before} and {after}")
    return before


def _keys():
    """(blended, stepped): KEYS and STEPS with the trials' plateaus cut into them."""
    blended, stepped = list(KEYS), list(STEPS)
    for name, trial in TRIALS.items():
        at, base = trial["tick"], _plateau(trial["tick"])
        blended += [(at - TRIAL_HOLD - TRIAL_RAMP, base), (at - TRIAL_HOLD, name),
                    (at + TRIAL_HOLD, name), (at + TRIAL_HOLD + TRIAL_RAMP, base)]
        stepped += [(at - TRIAL_HOLD, name), (at + TRIAL_HOLD, base)]
    return sorted(blended), sorted(stepped)


def _thin(points, steps):
    """Drop the keyframes that change nothing."""
    out = []
    for i, (at, value) in enumerate(points):
        before = points[i - 1][1]
        after = points[(i + 1) % len(points)][1]
        if i and value == before and (steps or value == after):
            continue
        out.append((at, value))
    return out


def _timeline():
    blended, stepped = _keys()
    names = list(LOOKS) + list(TRIALS)
    per = {name: values(name) for name in names}
    tracks = {}
    for key, first in per[DEFAULT].items():
        if all(per[name][key] == first for name in names):
            tracks[key] = M.track([(0, first)])
            continue
        steps = isinstance(first, str) and not first.startswith("#")
        tracks[key] = M.track(_thin([(at, per[name][key]) for at, name in (stepped if steps else blended)], steps))
    return M.timeline(tracks)


BIOMES = {"obs_blue": _biome()}
TIMELINES = {"obs_looks": _timeline()}
