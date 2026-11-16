"""Test scene of the work package site/outbuildings (plan/packages/site/outbuildings.md).

The four small buildings as they stand in the master scene: the terraces and shelves under them, the
main building behind them (the white model, until the main line's shell is merged), the props line on
the ground, and the sky line's light sources last. The lines are built whole, in the master scene's
order, so the picture keeps up with them as their packages are merged.

The one lamp each small building may carry (outbuildings.LAMP_POINTS: the hut's door, the water
tower's foot). The package names the points; the props line hangs the lamps with the site's other
lamps. Where props/lamps has that table the scene asks for it (lamps.dress); what that leaves out
the scene hangs itself, so the pictures show the hut and the tower as they will stand at night.

The bench on the south lookout is the props line's too (props/furniture, its group "lookout", c179
#37389). The scene asks for that one group once that package is in the tree, so the lookout's
pictures show it and the look back (V11) shows that it keeps out of that picture.

shots.json is written from shots():  python -m scenes.obs_site_outbuildings  (in build/).
"""
import importlib.util
import math

from artkit.canvas import Canvas

from scenes.obs import main, materials, props, site, sky
from scenes.obs.common import skeleton as S
from scenes.obs.props import lamps
from scenes.obs.site import outbuildings

BIOME = "obs_blue"
BIOME_MARGIN = 80
BIOME_MARGIN_Y = 140
LINES = (site, main, props, sky)
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)


def _door_lamps(c):
    """Hang the lamps of the small buildings that nobody has hung yet (see the module's text). Both
    points lie on a face that looks south: the hut's south gable, the south face of a tower leg."""
    for p in outbuildings.LAMP_POINTS.values():
        if any(math.dist(p, e[:3]) < 0.5 for e in c.entities):
            continue
        lamps.place(c, "cage", p, facing="south")


def _lookout_bench(c):
    """Ask props/furniture for the lookout's bench (see the module's text). Nothing while that
    package, or its table of the site's furniture, is not in the tree; a piece it has placed
    already (its own switch on) is not placed twice."""
    name = props.__name__ + ".furniture"
    if importlib.util.find_spec(name) is None:
        return
    furniture = importlib.import_module(name)
    if hasattr(furniture, "site"):
        furniture.site(c, (0, 0, 0), groups=("lookout",))


def build():
    c = Canvas()
    if hasattr(lamps, "dress"):
        lamps.dress(c)
    for line in LINES:
        if line is sky:
            _door_lamps(c)          # before the sky line turns the offered lights into light
        line.build(c, (0, 0, 0))
        if line is props:
            _lookout_bench(c)       # on the lookout's floor, which the site line has laid by now
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
    shot("hut_inside", (hx + 0.5, eye, hz + 3.2), (hx + 0.5, 2.7, hz - 3.5))    # a step inside the door

    x0, z0, x1, z1 = S.SOUTH_LOOKOUT["box"]             # 40,48,50,56
    mx = _middle(S.SOUTH_LOOKOUT["box"])[0] + 0.5
    # a person half-way down the steps, on the east side of the walk
    shot("lookout_near", (mx + 0.8, S.SOUTH_LOOKOUT["feet"] + 4.4, z0 - 5.0), (mx, S.SOUTH_LOOKOUT["feet"], z1 - 2.5))
    shot("lookout_mid", (x1 + 13.0, 0.0, z1 + 14.0), (x0 - 10.0, 3.0, z0 - 20.0))

    cx, cz = _middle(S.WATER_TOWER["box"])              # (-17, -31)
    feet = S.WATER_TOWER["feet"]
    # from the terrace by the west front; the tower shows between two piers of the railing
    shot("tower_near", (cx + 13.4, eye, cz + 6.5), (cx, feet + 7.0, cz))
    shot("tower_mid", (cx - 21.0, feet + 7.0, cz - 25.0), (cx + 9.0, feet + 9.0, cz + 7.0))
    # the wind engine on the tower (plan/fine.md: a thing is looked at from ten blocks and from two):
    # the wheel from before it and the tail from its side, eight blocks off; the pump, its rod and
    # the guides under the deck from ten blocks; the pump from two, standing between the legs
    hub = outbuildings.WIND_WHEEL                       # (-16.5, 15.25, -31.25)
    shot("wind_wheel", (hub[0] + 5.0, hub[1] + 1.25, hub[2] - 5.75), (hub[0], hub[1] - 0.25, hub[2] + 0.45))
    shot("wind_tail", (hub[0] + 7.5, hub[1] + 0.25, hub[2] + 2.25), (hub[0], hub[1] - 0.05, hub[2] + 1.25))
    shot("wind_ten", (cx + 9.4, feet + 3.2, cz + 4.6), (cx + 0.5, feet + 3.0, cz + 0.2))
    shot("wind_two", (cx + 1.7, feet + S.EYE, cz - 1.6), (cx + 0.5, feet + 1.3, cz + 0.15))

    wx, wz = _middle(S.WEATHER_STATION["box"])          # (3, -46)
    # on the terrace, in the gap of its railing, at the head of the steps
    shot("weather_near", (wx + 0.5, eye + 0.2, north + 1.4), (wx + 0.8, S.GROUND, wz - 0.6))
    shot("weather_mid", (wx - 9.0, 0.0, wz - 22.0), (wx + 3.0, 6.0, wz + 12.0))
    ax, ay, az = outbuildings.MAST_HEAD                 # the head of the wind mast, from three blocks off
    shot("weather_head", (ax + 1.3, ay + 0.1, az + 2.7), (ax - 0.25, ay + 0.35, az))

    shot("aerial", (70.0, 60.0, -70.0), (15.0, 0.0, -10.0))
    return out
