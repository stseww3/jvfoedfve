"""Test scene of the work package site/mastbase (plan/packages/site/mastbase.md).

The foot of the radio mast as it stands in the master scene: the terrace and the mast pad under it, the
main building behind them (the white model, until the main line's shell is merged), the props line on
the ground, and the sky line's light sources last. The lines are built whole, in the master scene's
order, so the picture keeps up with them as their packages are merged.

shots.json is written from shots():  python -m scenes.obs_site_mastbase  (in build/).
"""
from artkit.canvas import Canvas

from scenes.obs import main, materials, props, site, sky
from scenes.obs.common import skeleton as S

BIOME = "obs_blue"
BIOME_MARGIN = 80
BIOME_MARGIN_Y = 140
LINES = (site, main, props, sky)
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)


def build():
    c = Canvas()
    for line in LINES:
        line.build(c, (0, 0, 0))
    return c


def build_models():
    out = {}
    for line in LINES:
        out.update(line.models() or {})
    return out


def write_pack(pack_dir):
    """The mast foot paints nothing itself; it stands on the repainted blocks as the
    materials line has them today (ashlar, slate, cast iron)."""
    return materials.pack(pack_dir)


def shots():
    """The cameras, hung on the mast's foot (S.RADIO_MAST["foot"]): the foot from the terrace, with
    the clock tower its aerial runs to, from the court, from straight above (the seat, the coping
    and the four anchors as a plan), the arrival (V1, read from the skeleton) and from the air."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [float(round(v, 2)) for v in pos],
                    "look_at": [float(round(v, 2)) for v in look_at], "time": TIME})

    fx, fz = S.RADIO_MAST["foot"]                       # (23, -40)
    eye = S.MAST_PAD["feet"] + 1.7                      # a person standing on the pad or the terrace
    shot("base_near", (fx + 7.5, eye, fz + 6.5), (fx + 0.5, 1.2, fz))
    shot("base_tower", (fx + 11.0, eye + 0.5, fz - 9.0), (fx - 8.0, 12.0, fz + 8.0))
    # from the court, through the gap between the north end of the front and the meridian hut
    shot("base_court", (fx + 4.5, eye, fz + 21.5), (fx + 0.5, 3.0, fz))
    shot("base_top", (fx + 0.5, 13.0, fz + 6.0), (fx + 0.5, 0.0, fz - 0.5))
    shot("v1_arrival", S.V1["pos"], S.V1["look_at"])
    shot("aerial", (fx + 29.0, 40.0, fz - 32.0), (fx - 3.0, 2.0, fz + 4.0))
    return out
