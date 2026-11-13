"""Colour grading with data: biomes that carry environment attributes, and timelines that shift them.

Since 1.21.11 the sky, fog, cloud and light colours are "environment attributes" that a biome or a
dimension sets and a timeline modulates over the day, so a data pack alone can grade a scene: the
sky gradient, the haze, the tint of daylight and of lamp light, the stars.

Biomes and timelines are registry entries. They load when the server starts and are sent to the
client when it joins, so after these files change the server must be restarted and the client must
reconnect; `/reload` does not pick them up.
"""
import json
import os

VISUAL = "minecraft:visual/"


def biome(sky, fog, water="#3f76e4", water_fog=None, grass=None, foliage=None, dry_foliage=None,
          cloud=None, sun=None, lamp=None, ambient=None, fog_start=None, fog_end=None, sky_fog_end=None,
          cloud_height=None, stars=None, particles=None, extra=None):
    """Biome JSON (26.3) for a hand-placed scene: no features, no spawns, only the look.

    sky, fog      colour of the zenith and of the horizon haze, "#rrggbb"
    cloud         "#aarrggbb"
    sun, lamp     tint of sky light and of block light; ambient is the floor under both
    fog_start/end distances in blocks over which the haze builds up (vanilla: 0 and 1024)
    stars         star brightness added on top of the day/night curve (0..1)
    particles     list of (particle id, probability per block and tick) drifting around the viewer
    extra         further attributes, written as given
    """
    attrs = {VISUAL + "sky_color": sky, VISUAL + "fog_color": fog}
    for key, value in (("water_fog_color", water_fog or water), ("cloud_color", cloud), ("sky_light_color", sun),
                       ("block_light_tint", lamp), ("ambient_light_color", ambient),
                       ("fog_start_distance", fog_start), ("fog_end_distance", fog_end),
                       ("sky_fog_end_distance", sky_fog_end), ("cloud_height", cloud_height)):
        if value is not None:
            attrs[VISUAL + key] = value
    if stars is not None:
        attrs[VISUAL + "star_brightness"] = {"modifier": "maximum", "argument": stars}
    if particles:
        attrs[VISUAL + "ambient_particles"] = [{"particle": {"type": p}, "probability": prob} for p, prob in particles]
    attrs.update(extra or {})
    effects = {"water_color": water}
    for key, value in (("grass_color", grass), ("foliage_color", foliage), ("dry_foliage_color", dry_foliage)):
        if value is not None:
            effects[key] = value
    return {"attributes": attrs, "carvers": [], "features": [], "downfall": 0.5, "has_precipitation": False,
            "temperature": 0.7, "effects": effects}


def track(keyframes, modifier=None, ease=None):
    """One timeline track: keyframes = [(tick, value), ...] within the period."""
    out = {"keyframes": [{"ticks": int(t), "value": v} for t, v in keyframes]}
    if modifier:
        out["modifier"] = modifier
    if ease:
        out["ease"] = ease
    return out


def _vanilla_sun_angle(tick):
    """Where vanilla puts the sun: 0 overhead at noon (tick 6000), 90 on the western horizon,
    180 straight below, 270 on the eastern horizon. It runs a little slower around noon."""
    x1, y1, x2, y2 = 0.362, 0.241, 0.638, 0.759   # the cubic bezier ease of the vanilla day timeline
    p = ((tick - 6000) % 24000) / 24000.0
    lo, hi = 0.0, 1.0
    for _ in range(40):
        s = (lo + hi) / 2.0
        if 3 * (1 - s) ** 2 * s * x1 + 3 * (1 - s) * s * s * x2 + s ** 3 < p:
            lo = s
        else:
            hi = s
    s = (lo + hi) / 2.0
    return 360.0 * (3 * (1 - s) ** 2 * s * y1 + 3 * (1 - s) * s * s * y2 + s ** 3)


def one_body_sky(day, night, dusk=13050, dawn=22850, step=500):
    """Tracks that make the moon object play both sun and moon, so that only one body is ever drawn.

    Vanilla always draws both, opposite each other. On the ground the lower one is hidden; from a
    floating island it is in plain view below the horizon: a moon under the island at noon, a sun
    under it at midnight. Here the moon object follows the sun's path by day and its own by night,
    and its phase picks the picture; the resource pack paints the eight phase textures to match
    and blanks the sun texture.

    day, night  [(tick, phase), ...]: the picture from each tick on, within the day (dawn..dusk
                over midnight's far side) and within the night (dusk..dawn)
    dusk, dawn  ticks at which the object jumps across the sky; it should show a blank phase then
    Returns {"moon_angle": track, "moon_phase": track}.
    """
    def sun(t):                      # continuous through noon: -108 before sunrise .. +106 after sunset
        a = _vanilla_sun_angle(t)
        return a - 360.0 if a > 180.0 else a

    def moon(t):                     # the same for the night side, through midnight
        return _vanilla_sun_angle(t) - 180.0

    angle = [(t, sun(t)) for t in range(0, dusk, step)] + [(dusk, sun(dusk))]
    angle += [(t, moon(t)) for t in range(dusk + 1, dawn - 1, step)] + [(dawn - 1, moon(dawn - 1))]
    angle += [(t, sun(t)) for t in range(dawn, 24000, step)]
    phases = sorted(list(day) + list(night))
    return {"moon_angle": track([(t, round(a, 3)) for t, a in angle]),
            "moon_phase": track(phases)}


def timeline(tracks, clock="minecraft:overworld", period=24000):
    return {"clock": clock, "period_ticks": period,
            "tracks": {(k if ":" in k else VISUAL + k): v for k, v in tracks.items()}}


def _write(path, data):
    text = json.dumps(data, indent=1, sort_keys=True) + "\n"
    if os.path.exists(path):
        with open(path) as fh:
            if fh.read() == text:
                return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)
    return True


def write(pack_dir, namespace, biomes, timelines=None, dimension_tag="in_overworld"):
    """Write biomes {name: json} and timelines {name: json} into a data pack.

    Timelines are appended to the dimension's timeline tag, after the vanilla ones, so their
    modifiers apply on top of the vanilla day cycle. Returns the names of the files that changed:
    if the list is not empty the server has to be restarted.
    """
    changed = []
    for name, data in biomes.items():
        if _write(os.path.join(pack_dir, "data", namespace, "worldgen", "biome", name + ".json"), data):
            changed.append(f"biome {name}")
    timelines = timelines or {}
    for name, data in timelines.items():
        if _write(os.path.join(pack_dir, "data", namespace, "timeline", name + ".json"), data):
            changed.append(f"timeline {name}")
    tag = os.path.join(pack_dir, "data", "minecraft", "tags", "timeline", dimension_tag + ".json")
    if timelines:
        if _write(tag, {"replace": False, "values": [f"{namespace}:{n}" for n in sorted(timelines)]}):
            changed.append("timeline tag")
    elif os.path.exists(tag):
        os.remove(tag)
        changed.append("timeline tag")
    for kind in ("worldgen/biome", "timeline"):
        d = os.path.join(pack_dir, "data", namespace, kind)
        keep = biomes if kind == "worldgen/biome" else timelines
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith(".json") and f[:-5] not in keep:
                    os.remove(os.path.join(d, f))
                    changed.append(f"removed {kind} {f[:-5]}")
    return changed
