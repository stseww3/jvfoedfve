"""The light and air of a moment, worked out the way the game does.

Since 1.21.11 the sky, the fog and the colours of light are environment attributes: the dimension
gives a value, the biome changes it, and the timelines of the dimension change it again tick by
tick (EnvironmentAttributeSystem). look() runs those layers for one tick of the day and then does
what the client does with the result: the fog colour drawn towards the sky colour
(AtmosphericFogEnvironment), the table that turns sky and block light levels into a colour
(lightmap.fsh).
"""
import math

import numpy as np

VISUAL = "minecraft:visual/"
DEFAULTS = {
    "sky_color": "#000000", "fog_color": "#000000", "fog_start_distance": 0.0, "fog_end_distance": 1024.0,
    "sky_fog_end_distance": 512.0, "sky_light_color": "#ffffff", "sky_light_factor": 1.0,
    "ambient_light_color": "#000000", "block_light_tint": "#ffd88c", "star_brightness": 0.0,
    "sun_angle": 0.0, "moon_angle": 0.0, "star_angle": 0.0, "moon_phase": "full_moon",
    "sunrise_sunset_color": "#00000000",
}
ANGLES = ("sun_angle", "moon_angle", "star_angle")
BLOCK_FACTOR = 1.4            # LightmapRenderStateExtractor: the flicker swings a little around this
SUN_SIZE, MOON_SIZE = 30.0, 20.0


def colour(text):
    """"#rrggbb" or "#aarrggbb" -> floats 0..1 (r, g, b) or (r, g, b, a)."""
    h = text.lstrip("#")
    v = [int(h[i:i + 2], 16) / 255.0 for i in range(0, len(h), 2)]
    return np.array(v[1:] + v[:1] if len(v) == 4 else v)


def _value(x):
    return colour(x) if isinstance(x, str) and x.startswith("#") else x


def _bezier(x1, y1, x2, y2, p):
    lo, hi = 0.0, 1.0
    for _ in range(40):
        s = (lo + hi) / 2.0
        if 3 * (1 - s) ** 2 * s * x1 + 3 * (1 - s) * s * s * x2 + s ** 3 < p:
            lo = s
        else:
            hi = s
    s = (lo + hi) / 2.0
    return 3 * (1 - s) ** 2 * s * y1 + 3 * (1 - s) * s * s * y2 + s ** 3


def _sample(track, tick, period, angle=False):
    """KeyframeTrackSampler: the track's value at a tick, wrapping round the period."""
    keys = [(k["ticks"], _value(k["value"])) for k in track["keyframes"]]
    if len(keys) == 1:
        return keys[0][1]
    t = tick % period
    segs = [(keys[-1][0] - period, keys[-1][1], keys[0][0], keys[0][1])]
    segs += [(keys[i][0], keys[i][1], keys[i + 1][0], keys[i + 1][1]) for i in range(len(keys) - 1)]
    segs += [(keys[-1][0], keys[-1][1], keys[0][0] + period, keys[0][1])]
    seg = next((s for s in segs if t < s[2]), segs[-1])
    t0, a, t1, b = seg
    if t <= t0:
        return a
    if t >= t1:
        return b
    alpha = (t - t0) / float(t1 - t0)
    ease = track.get("ease", "linear")
    if ease == "constant":
        return a
    if isinstance(ease, dict) and "cubic_bezier" in ease:
        alpha = _bezier(*ease["cubic_bezier"], alpha)
    if isinstance(a, str):
        return b if alpha >= 1.0 else a
    if angle:
        delta = (b - a + 180.0) % 360.0 - 180.0
        return b if abs(delta) >= 90.0 else a + alpha * delta
    return a + alpha * (b - a)


def _apply(base, modifier, arg):
    if modifier in (None, "override"):
        return arg
    if modifier == "multiply":
        return base * arg
    if modifier == "add":
        return np.minimum(base + arg, 1.0) if isinstance(base, np.ndarray) else base + arg
    if modifier == "subtract":
        return np.maximum(base - arg, 0.0) if isinstance(base, np.ndarray) else base - arg
    if modifier == "maximum":
        return max(base, arg)
    if modifier == "minimum":
        return min(base, arg)
    if modifier == "alpha_blend":
        return base[:3] + (arg[:3] - base[:3]) * arg[3]
    raise ValueError(f"attribute modifier {modifier!r} is not handled")


def attributes(tick, dimension, biome, timelines):
    """Every visual attribute at a tick. dimension, biome: {"attributes": ...} as in the data
    files; timelines: the dimension's timelines in the order of its tag."""
    out = {k: _value(v) for k, v in DEFAULTS.items()}
    for layer in (dimension.get("attributes", {}), biome.get("attributes", {})):
        for key, v in layer.items():
            if key.startswith(VISUAL) and key[len(VISUAL):] in out:
                name = key[len(VISUAL):]
                if isinstance(v, dict) and "argument" in v:
                    out[name] = _apply(out[name], v.get("modifier"), _value(v["argument"]))
                elif not isinstance(v, (dict, list)):
                    out[name] = _value(v)
    for tl in timelines:
        for key, track in tl.get("tracks", {}).items():
            if key.startswith(VISUAL) and key[len(VISUAL):] in out:
                name = key[len(VISUAL):]
                arg = _sample(track, tick, tl.get("period_ticks", 24000), angle=name in ANGLES)
                out[name] = _apply(out[name], track.get("modifier"), arg)
    return out


def _brightness(level):
    return level / (4.0 - 3.0 * level)


def lightmap(a, gamma=0.5):
    """lightmap.fsh: table[sky level][block level] -> colour the texture is multiplied with."""
    table = np.zeros((16, 16, 3))
    tint, sky_colour, ambient = a["block_light_tint"][:3], a["sky_light_color"][:3], a["ambient_light_color"][:3]
    for s in range(16):
        for b in range(16):
            bl, sl = b / 15.0, s / 15.0
            c = ambient + sky_colour * (_brightness(sl) * a["sky_light_factor"])
            lamp = tint + (1.0 - tint) * (0.9 * (2.0 * bl - 1.0) ** 2)
            c = np.clip(c + lamp * (_brightness(bl) * BLOCK_FACTOR), 0.0, 1.0)
            top = c.max()
            if top > 0.0:
                lifted = c * ((1.0 - (1.0 - top) ** 4) / top)
                c = c + (lifted - c) * gamma
            table[s, b] = c
    return table


class Look:
    """What render.py needs to know about one moment."""

    def __init__(self, tick, dimension, biome, timelines, render_chunks=14, gamma=0.5):
        a = self.attrs = attributes(tick, dimension, biome, timelines)
        self.tick = tick
        self.sky = a["sky_color"][:3]
        fog = a["fog_color"][:3]
        sun = a["sunrise_sunset_color"]
        self.sunset = sun if len(sun) == 4 and sun[3] > 0.0 else None
        sky_end = min(a["sky_fog_end_distance"] / 16.0, float(render_chunks))
        mix = 1.0 - (0.25 + 0.75 * min(1.0, max(0.0, sky_end / 32.0))) ** 0.25
        self.fog = fog + (self.sky - fog) * mix
        self.fog_start, self.fog_end = float(a["fog_start_distance"]), float(a["fog_end_distance"])
        far = render_chunks * 16.0
        self.far_start, self.far_end = far - min(64.0, max(4.0, far / 10.0)), far
        self.sky_end = min(far, float(a["sky_fog_end_distance"]))
        self.lightmap = lightmap(a, gamma)
        self.stars = float(a["star_brightness"])
        self.sun_angle, self.moon_angle, self.star_angle = (float(a[k]) for k in ANGLES)
        self.moon_phase = a["moon_phase"]
        effects = biome.get("effects", {})
        self.grass = colour(effects.get("grass_color", "#91bd59"))
        self.foliage = colour(effects.get("foliage_color", "#77ab2f"))
        self.dry_foliage = colour(effects.get("dry_foliage_color", "#a0763a"))
        self.water = colour(effects.get("water_color", "#3f76e4"))

    @staticmethod
    def body(angle):
        """Direction of the sun or moon for its angle: overhead at 0, on the western horizon at 90."""
        r = math.radians(angle)
        return np.array([-math.sin(r), math.cos(r), 0.0])
