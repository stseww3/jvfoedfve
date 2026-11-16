"""Test scene of the work package props/signals: the home signal of the rack railway by itself.

A paved pad stands for the rock beside the trestle, and the rails are thought RAIL over it, as
far as they are over the rock where the signal stands in the master scene (site/_rail, s 7.5). Two
signals stand on it, both facing east as for a train that comes from there: the one in front
(lower z) at "stop" with its wire, which runs back to a stub of wall that stands for the winch
house's corner, and a second one at "clear", placed so by signals.signal(clear=True) for the
picture: in the map the arm is moved by the train's trip. Every model of the family is held to
_kit.settle here.

The shots are written from the numbers below:  python -m scenes.obs_props_signals
The near shots stand two to three blocks from what they show (plan/fine.md: the near layer).
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.props import _kit as K
from scenes.obs.props import signals

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B)
TIME_DEEP = 18000

PAD = (0, 0, 11, 13)            # x0, z0, x1, z1 of the pad
TOP = 0                         # its paving course
FEET = TOP + 1
RAIL = FEET + 7.0               # the level of the rails: so far over the rock in the master scene
STOP = (6.0, RAIL, 4.5)         # the signal at "stop": the point on its post at the level of the rails
CLEAR = (6.0, RAIL, 10.0)       # the one at "clear"
WALL = dict(x=2, z=(3, 5), y=(FEET, FEET + 10))         # the stub of wall the wire goes into
WIRE = ((WALL["x"] + 1.0, RAIL + signals.WIRE_LEVEL, STOP[2] - signals.WIRE_OFF), "east")

PAVE = B.TUFF_BRICK.block
KERB = B.TUFF_SMOOTH.block


def build():
    c = Canvas()
    x0, z0, x1, z1 = PAD
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            c.set(x, TOP - 1, z, PAVE)
            c.set(x, TOP, z, KERB if x in (x0, x1) or z in (z0, z1) else PAVE)
    for z in range(WALL["z"][0], WALL["z"][1] + 1):
        for y in range(WALL["y"][0], WALL["y"][1] + 1):
            c.set(WALL["x"], y, z, PAVE)
    for name, model in signals.models().items():
        faults = K.unsettled(model)
        if faults:
            raise ValueError(f"{name}: {len(faults)} faces stand between two axes; run it through _kit.settle")
    n = signals.signal(c, STOP, facing="east", wire_to=WIRE)
    n += signals.signal(c, CLEAR, facing="east", clear=True)
    lit = sky.build(c, (0, 0, 0))   # A2's light sources go in last, when everything that glows is in place
    c.entity_counts = {"props": n, "sky": lit or 0}
    return c


def build_models():
    return dict(signals.models())


def write_pack(pack_dir):
    """The repainted stone and the pictures of the map's sky (the stage stands in the map's hour,
    mood.py)."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


# ---- the cameras ------------------------------------------------------------------------------------------
def shots():
    """Both signals as the train sees them, ten blocks off, in the default light and in the deep
    night; the two from below, as from the incline; the signal at "stop" from the station's
    side; then the near shots, two to three blocks from what they show: its head from the front
    and from behind, the gear from the front and from behind, the foot, where the wire goes into
    the wall, and the head of the one at "clear"."""
    out = []

    def shot(name, pos, look_at, time=TIME):
        out.append({"name": name, "pos": [round(float(v), 2) for v in pos],
                    "look_at": [round(float(v), 2) for v in look_at], "time": time})

    x, y, z = STOP
    spindle, gear = y + signals.HEIGHT, y + signals.GEAR_UP
    mid = (z + CLEAR[2]) / 2.0
    shot("front", (x + 10.0, y + 1.6, mid), (x, y + 3.0, mid - 0.5))
    shot("front_deep", (x + 10.0, y + 1.6, mid), (x, y + 3.0, mid - 0.5), TIME_DEEP)
    shot("whole", (x + 12.0, FEET + 3.0, CLEAR[2] + 5.0), (x, y - 1.0, mid - 1.0))
    shot("back", (x - 5.0, y + 1.6, z + 3.5), (x, spindle - 0.7, z + 0.1))
    shot("head_near", (x + 2.5, spindle - 0.3, z + 1.8), (x, spindle, z - 0.2))
    shot("head_near_deep", (x + 2.5, spindle - 0.3, z + 1.8), (x, spindle, z - 0.2), TIME_DEEP)
    shot("head_back_near", (x - 2.5, spindle - 0.5, z + 1.4), (x, spindle, z - 0.1))
    shot("gear_near", (x + 2.3, gear + 0.6, z - 1.5), (x + 0.1, gear + 0.4, z - 0.15))
    shot("gear_back_near", (x - 2.2, gear + 0.7, z - 1.3), (x, gear + 0.3, z - 0.2))
    shot("foot_near", (x + 2.2, FEET + 1.4, z + 1.7), (x, FEET + 1.3, z))
    shot("wire_near", (WIRE[0][0] + 1.7, WIRE[0][1] + 0.5, WIRE[0][2] - 1.5), (WIRE[0][0] + 0.1, WIRE[0][1], WIRE[0][2]))
    shot("clear_near", (x + 2.5, spindle - 0.3, CLEAR[2] + 1.8), (x, spindle - 0.2, CLEAR[2] - 0.3))
    return out
