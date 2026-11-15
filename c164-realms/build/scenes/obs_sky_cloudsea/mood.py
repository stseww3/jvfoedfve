"""The look of this test scene: the sky's own (scenes.obs.sky.mood, untouched) with the fog laws
under trial cut into the morning as further plateaus.

Why a law is tried (plan/roles/A0-director.md 4; the game's fog.glsl, clouds.fsh and
AtmosphericFogEnvironment, 26.3): a block is mixed towards the fog colour by
(distance - fog_start) / (fog_end - fog_start); the vanilla cloud layer takes no fog colour, its
opacity is multiplied by 1 - distance / cloud_fog_end and what lies behind it -- the fog colour,
below the horizon -- shows through. With fog_start = 0 and fog_end = cloud_fog_end = D a block and
the layer beside it sink into the horizon by the same law, d / D, and a block cloud of the layer's
colour is not told from the layer at any distance. The layer has to be opaque for that (alpha 1.0;
0.94 lets a sixteenth of the dark behind it through close by).

    LAWS    name -> the look it varies, its tick, and the four numbers
    b<D>    fog_start 0, fog_end = cloud_fog_end = D: the two laws are one
    s<D>    fog_start stays 60 (nothing nearer than 60 blocks changes in anybody's pictures),
            fog_end = 60 + 0.6 D: the block law crosses the layer's at 150 blocks and stays within
            60 / D of it nearer by

Each is held for 200 ticks like the sky's own trials (ticks ending in 600, the sky's end in 100),
so changing the time puts one law beside the other on the same blocks. The numbers the director
settles on go into sky/mood.py (A2 writes them); this file then goes back to one import line.
"""
import copy

from artkit import mood as M
from scenes.obs.sky import mood as sky

HOLD, RAMP = sky.TRIAL_HOLD, sky.TRIAL_RAMP


def _law(of, tick, fog_start, fog_end, cloud_fog_end, alpha=1.0):
    return dict(of=of, tick=tick, fog_start=float(fog_start), fog_end=float(fog_end),
                cloud_fog_end=float(cloud_fog_end), alpha=alpha)


LAWS = {}
for _i, _d in enumerate((384, 512, 768, 2048)):
    LAWS[f"b{_d}"] = _law("blue", 600 + 1000 * _i, 0.0, _d, _d)
    LAWS[f"s{_d}"] = _law("blue", 4600 + 1000 * _i, sky.FOG_START, sky.FOG_START + 0.6 * _d, _d)


def tick(name):
    """The time that shows a law, a look or one of the sky's trials."""
    return LAWS[name]["tick"] if name in LAWS else sky.tick(name)


def values(name):
    """The attribute values of a law (or of a look or trial of the sky's), keyed as sky.values()."""
    if name not in LAWS:
        return sky.values(name)
    law = LAWS[name]
    out = dict(sky.values(law["of"]))
    out["fog_start_distance"], out["fog_end_distance"] = law["fog_start"], law["fog_end"]
    out["cloud_fog_end_distance"] = law["cloud_fog_end"]
    alpha = max(0, min(255, int(round(law["alpha"] * 255.0))))
    out["cloud_color"] = f"#{alpha:02x}" + sky.look(law["of"])["cloud"].lstrip("#")
    return out


def _held(at):
    """The look the sky's timeline holds at a tick, None on a ramp between two."""
    before = [name for t, name in sky.KEYS if t <= at][-1]
    after = ([name for t, name in sky.KEYS if t > at] or [sky.KEYS[0][1]])[0]
    return before if before == after else None


def _timeline():
    """The sky's timeline with a plateau for every law: on each track whose value the law changes,
    the look's value, a ramp, the law's value held, a ramp back."""
    line = copy.deepcopy(sky.TIMELINES["obs_looks"])
    taken = sorted(t["tick"] for t in sky.TRIALS.values())
    for name, law in LAWS.items():
        at, lo, hi = law["tick"], law["tick"] - HOLD - RAMP, law["tick"] + HOLD + RAMP
        if _held(lo) != law["of"] or _held(hi) != law["of"]:
            raise ValueError(f"law {name}: ticks {lo}..{hi} do not lie on the plateau of {law['of']}")
        if any(abs(at - t) < 2 * (HOLD + RAMP) for t in taken):
            raise ValueError(f"law {name}: tick {at} runs into another trial")
        taken.append(at)
        base, mine = sky.values(law["of"]), values(name)
        for key, value in mine.items():
            if value == base[key]:
                continue
            track = line["tracks"][M.VISUAL + key]
            frames = [(k["ticks"], k["value"]) for k in track["keyframes"]]
            frames += [(lo, base[key]), (at - HOLD, value), (at + HOLD, value), (hi, base[key])]
            track["keyframes"] = [{"ticks": int(t), "value": v} for t, v in sorted(frames, key=lambda f: f[0])]
    return line


BIOMES = sky.BIOMES
TIMELINES = {"obs_looks": _timeline()}
