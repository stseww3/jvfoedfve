"""Test scene of props/signals in its place: the master scene as it stands in this tree, and the
cameras at the home signal beside the brow of the incline.

Every line is built whole, in the master scene's order, so the pictures keep up with the station,
the trestle and the rock as their packages are merged. What the pictures are for: the signal as
the platform sees it and as whoever rides up sees it (the far and the middle layer of
plan/fine.md), whole from the north with the trestle behind it, and from two to three blocks its
head, its gear and where its wire goes into the winch house (the near layer).

The shots are written from the line's numbers:  python -m scenes.obs_props_signals_site
which also says where the signal stands and what it stands on.
"""
from scenes import obs
from scenes.obs.common import skeleton as S
from scenes.obs.props import signals
from scenes.obs.site import _rail

BIOME = obs.BIOME
BIOME_MARGIN = obs.BIOME_MARGIN
BIOME_MARGIN_Y = obs.BIOME_MARGIN_Y
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B)
TIME_DEEP = 18000

build = obs.build
build_models = obs.build_models
write_pack = obs.write_pack

EYE = S.EYE


def seat():
    """Where the home signal stands: (x, y, z) on its post at the level of the rails."""
    return signals._home()["at"]


# ---- the cameras ------------------------------------------------------------------------------------------
def shots():
    """From the platform's east edge; from the train on the incline, in both lights, and from the
    incline's foot; whole from the north; then the near shots: the head from the front and from
    behind, the gear, the wire's way into the winch house."""
    out = []

    def shot(name, pos, look_at, time=TIME):
        out.append({"name": name, "pos": [round(float(v), 2) for v in pos],
                    "look_at": [round(float(v), 2) for v in look_at], "time": time})

    x, y, z = seat()
    spindle, gear = y + signals.HEIGHT, y + signals.GEAR_UP
    wire = signals._home()["wire_to"][0]

    def rider(s):
        """The eye of somebody who rides up, at s."""
        p = _rail.at(s)
        return p.x, p.y + 0.5 + EYE, p.z

    shot("platform", (_rail.EDGE - 0.5, _rail.FEET + EYE, _rail.Z - 1.0), (x, spindle - 1.5, z))
    shot("train", rider(14.0), (x, spindle - 2.0, z))
    shot("train_deep", rider(14.0), (x, spindle - 2.0, z), TIME_DEEP)
    shot("train_far", rider(_rail.S_FOOT), (x, spindle - 2.0, z))
    shot("north", (x + 0.5, y - 2.0, z - 10.5), (x, y - 1.0, z))
    shot("head_near", (x + 2.5, spindle - 0.3, z + 1.8), (x, spindle, z - 0.2))
    shot("head_back_near", (x - 2.5, spindle - 0.5, z + 1.4), (x, spindle, z - 0.1))
    shot("gear_near", (x + 2.3, gear + 0.6, z - 1.5), (x + 0.1, gear + 0.4, z - 0.15))
    shot("wire_near", (wire[0] + 1.7, wire[1] + 0.5, wire[2] - 1.5), (wire[0] + 0.1, wire[1], wire[2]))
    return out
