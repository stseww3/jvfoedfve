"""Test scene of the work package site/yard (plan/packages/site/yard.md).

The works yard as it lies in the master scene: the site line whole (the lower platform, the stair,
the cable station and the power house it runs between), the main building over the wall, the props
line on the ground (the lamps the yard keeps clear of) and the sky line's light last. The lines are
built whole, in the master scene's order, so the pictures keep up with them as packages are merged.

The cameras: the three board views the yard shows in (the arrival V1, whose foreground it is; V6
before the power house; V12 from the air), then the yard as plan/fine.md asks to see it: from ten
blocks, where the parts are counted, and from two, where the marks are.

shots.json is written from shots():  python -m scenes.obs_site_yard  (in build/).
plan.py prints the platform's floor as a map:  python -m scenes.obs_site_yard.plan
"""
from artkit.canvas import Canvas

from scenes.obs import main, materials, props, site, sky
from scenes.obs.common import skeleton as S
from scenes.obs.site import yard

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
    """The yard paints nothing itself: its plate is the materials line's iron."""
    return materials.pack(pack_dir)


def shots():
    """The cameras. The board views are read from the skeleton; the others hang on the yard's own
    numbers, so they follow a line that is moved."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [float(round(v, 2)) for v in pos],
                    "look_at": [float(round(v, 2)) for v in look_at], "time": TIME})

    eye = yard.FEET + 1.62                              # a person standing on the lower platform
    mid = yard.ROW + 0.5                                # the middle of line A
    tx = yard.TABLE[0] + 0.5
    shot("v1_arrival", S.V1["pos"], S.V1["look_at"])
    shot("v6_powerhouse", S.V6["pos"], S.V6["look_at"])
    shot("v12_air", S.V12["pos"], S.V12["look_at"])
    # ten blocks off: the table, the rake by it and line A to the heap; line B across the stair's foot
    shot("yard_10", (tx + 6.0, eye, mid + 7.5), (tx - 3.0, yard.FEET + 0.3, mid))
    shot("lineb_10", (tx + 6.0, eye, 0.5), (tx - 1.0, yard.FEET + 0.4, 0.5))
    shot("wall_top", (S.EAST_EDGE_X - 0.5, S.GROUND + 1.62, mid + 3.0), (tx - 4.0, yard.FEET, mid))
    # two or three blocks off
    shot("table_2", (tx + 2.1, eye, mid + 2.2), (tx, yard.FEET + 0.35, mid))
    shot("rake_2", (yard.REST_X - 1.4, eye, mid + 2.3), (yard.REST_X - 0.2, yard.FEET + 0.7, mid))
    shot("stop_2", (yard.A_WEST[0] + 2.7, eye, mid - 2.0), (yard.A_WEST[0] + 0.7, yard.FEET + 0.4, mid + 0.2))
    shot("heap_2", (yard.HEAP[0] + 3.4, eye, yard.HEAP[1] + 2.8), (yard.HEAP[0] + 0.5, yard.FEET + 0.6, yard.HEAP[1] + 0.3))
    shot("stub_2", (yard.A_EAST[1] - 0.4, eye, mid + 2.4), (yard.A_EAST[1] - 0.6, yard.FEET + 0.5, mid))
    shot("door_3", (tx + 2.0, eye, yard.B_Z[1] - 4.0), (tx, yard.FEET + 0.2, yard.B_Z[1] + 0.5))
    shot("air_yard", (tx + 10.0, 12.0, mid - 18.0), (tx - 4.0, yard.FEET, mid + 8.0))
    return out
