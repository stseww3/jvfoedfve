"""Trial only (never delivered): the lamps of the site in the director's view of the power house,
S.V6, with the lip's low lamps as the table has them (LIP None) or with another list of piers.

The view was locked after the lamps were delivered (A0 #56796: where a lamp stands before the
bridge head, the lamp moves and the view stays). obs_trial_v6_drop and obs_trial_v6_22 are this
scene with the lamp of the pier at z 26 left out, and moved one pier towards the stair head.
"""
from scenes import obs_props_lamps_site as base
from scenes.obs.common import skeleton as S
from scenes.obs.props import lamps
from scenes.obs_props_lamps_site import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, build_models, write_pack  # noqa: F401

LIP = None
TIMES = {"v6": base.BLUE, "v6_deep": base.DEEP}


def build_with(lip):
    told = lamps._told

    def patched(module, name):
        if lip is not None and (module, name) == ("site.court", "lip_lamps"):
            return list(lip)
        return told(module, name)

    lamps._told = patched
    try:
        return base.build()
    finally:
        lamps._told = told


def build():
    return build_with(LIP)


def shots_for(times):
    return [{"name": name, "pos": [round(v, 2) for v in S.V6["pos"]],
             "look_at": [round(v, 2) for v in S.V6["look_at"]], "time": time} for name, time in times.items()]


def shots():
    return shots_for(TIMES)
