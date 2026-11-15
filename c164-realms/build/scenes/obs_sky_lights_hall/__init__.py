"""Trial only, never delivered: the blue building with main/shell in it, the stand-in wall gone,
and the open hall lit by sky/lights with different numbers; one building for each try, 200 apart.

    python -m scenes.obs_sky_lights_hall     writes shots.json and prints what each try places
"""
import contextlib

from artkit.canvas import Canvas

from scenes import obs_sky_lights as base
from scenes.obs_sky_lights import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, write_pack  # noqa: F401
from scenes.obs_sky_lights.props import build_models  # noqa: F401
from scenes.obs.props import lamps
from scenes.obs.sky import _lightkit as L
from scenes.obs.sky import lights
from scenes.obs.sky import mood as look

# name: (the numbers of sky/lights it is lit by, sources laid by hand on top: ((x, y, z), level))
TRIES = {
    "k1": (dict(), ()),
    "k2": (dict(DOOR_LEVEL=12), ()),
    "k3": (dict(), (((9, 4, -4), 11), ((9, 4, 4), 11))),
    "k4": (dict(DOOR_LEVEL=12, FLIGHT_LEVEL=12), (((9, 4, -4), 11), ((9, 4, 4), 11), ((6, 8, 0), 11))),
}
VIEWS = ("axis", "door", "v7", "front")


def origin(i):
    return (-base.SPACING * i, 0, 0)


@contextlib.contextmanager
def numbers(**values):
    kept = {name: getattr(lights, name) for name in values}
    for name, value in values.items():
        setattr(lights, name, value)
    try:
        yield
    finally:
        for name, value in kept.items():
            setattr(lights, name, value)


def build(only=None):
    c = Canvas()
    L.dress(c)
    lamps.dress(c, False)
    for i, (name, (values, more)) in enumerate(TRIES.items()):
        if only is not None and name not in only:
            continue
        o = origin(i)
        with numbers(**values):
            base._station(c, "blue", o)
        for (x, y, z), level in more:
            c.set(x + o[0], y + o[1], z + o[2], L.light(level))
    return c


def shots():
    out = []
    for i, name in enumerate(TRIES):
        o = origin(i)
        for view in VIEWS:
            eye, target = base.VIEWS[view]
            out.append({"name": f"{name}_{view}", "pos": [round(eye[k] + o[k], 2) for k in range(3)],
                        "look_at": [round(target[k] + o[k], 2) for k in range(3)], "time": look.tick("blue")})
    return out
