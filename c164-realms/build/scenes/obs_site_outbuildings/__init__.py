"""Test scene of the work package site/outbuildings (plan/packages/site/outbuildings.md).

The four small buildings as they stand in the master scene: the terraces and shelves under them, the
main building behind them (the white model, until the main line's shell is merged), the props line on
the ground, and the sky line's light sources last. The lines are built whole, in the master scene's
order, so the picture keeps up with them as their packages are merged.

shots.json is written from shots():  python -m scenes.obs_site_outbuildings  (in build/).
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
    """The outbuildings paint nothing themselves; they stand on the repainted blocks as the
    materials line has them today (ashlar, slate, cast iron)."""
    return materials.pack(pack_dir)


def _middle(box):
    x0, z0, x1, z1 = box
    return (x0 + x1) // 2, (z0 + z1) // 2


def shots():
    """The cameras. The two locked views this card answers to are read from the skeleton: the
    arrival (V1), which the hut stands in, and the look back (V11), which is taken from the lookout.
    Then each small building once from near and once from where it shows with the main building,
    and the whole hilltop from the air. The cameras hang on the skeleton's boxes, so they follow a
    shelf that moves."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [float(round(v, 2)) for v in pos],
                    "look_at": [float(round(v, 2)) for v in look_at], "time": TIME})

    eye = S.GROUND + 1.7                                # a person standing on the upper terrace
    north, south = S.UPPER_TERRACE[1], S.UPPER_TERRACE[3]       # the terrace's edges: z -38 and 38
    shot("v1_arrival", S.V1["pos"], S.V1["look_at"])
    shot("v11_lookback", S.V11["pos"], S.V11["look_at"])

    hx, hz = S.MERIDIAN_HUT["centre"]                   # (35, -30)
    shot("hut_near", (hx + 9.5, eye, hz + 12.5), (hx + 0.5, 3.0, hz))
    shot("hut_mid", (hx + 22.5, eye + 0.9, hz + 15.5), (hx - 11.0, 9.0, hz))
    shot("hut_slit", (hx + 0.5, eye, hz + 15.5), (hx + 0.5, 3.0, hz))       # on the meridian, looking north

    x0, z0, x1, z1 = S.SOUTH_LOOKOUT["box"]             # 40,48,50,56
    mx = _middle(S.SOUTH_LOOKOUT["box"])[0] + 0.5
    shot("lookout_near", (mx, eye, south - 1.5), (mx, S.SOUTH_LOOKOUT["feet"], z1 - 3.0))
    shot("lookout_mid", (x1 + 13.0, 0.0, z1 + 14.0), (x0 - 10.0, 3.0, z0 - 20.0))

    cx, cz = _middle(S.WATER_TOWER["box"])              # (-17, -31)
    feet = S.WATER_TOWER["feet"]
    shot("tower_near", (cx + 12.5, eye, cz + 8.5), (cx, feet + 7.0, cz))
    shot("tower_mid", (cx - 21.0, feet + 7.0, cz - 25.0), (cx + 9.0, feet + 9.0, cz + 7.0))

    wx, wz = _middle(S.WEATHER_STATION["box"])          # (3, -46)
    shot("weather_near", (wx + 8.5, eye, north + 0.5), (wx, S.WEATHER_STATION["feet"] + 1.0, wz))
    shot("weather_mid", (wx - 9.0, 0.0, wz - 22.0), (wx + 3.0, 6.0, wz + 12.0))

    shot("aerial", (70.0, 60.0, -70.0), (15.0, 0.0, -10.0))
    return out
