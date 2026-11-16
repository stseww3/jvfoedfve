"""Test scene of the work package props/signals: the home signal of the rack railway by itself.

A paved pad, nine cells by seven, stands for the corner of the station platform the signal has in
the master scene (site/cablecar's railed bay): the signal in its middle, facing east as it does
there, and a post lamp of props/lamps north-west of it, where the station's pendant hangs from
the signal. The signal is stood by signals.signal(), the call signals.build() makes for the real
platform; every model of the family is held to _kit.settle here.

The shots are written from the numbers below:  python -m scenes.obs_props_signals
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.props import _kit as K
from scenes.obs.props import lamps, signals

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B)
TIME_DEEP = 18000

PAD = (0, 0, 8, 6)              # x0, z0, x1, z1 of the pad
TOP = 0                         # its paving course
FEET = TOP + 1
FOOT = (4.5, float(FEET), 3.5)  # the signal's foot: the middle of the pad
FACING = "east"
LAMP = (2.5, float(FEET), 1.5)  # the post lamp's foot

PAVE = B.TUFF_BRICK.block
KERB = B.TUFF_SMOOTH.block


def build():
    c = Canvas()
    x0, z0, x1, z1 = PAD
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            c.set(x, TOP - 1, z, PAVE)
            c.set(x, TOP, z, KERB if x in (x0, x1) or z in (z0, z1) else PAVE)
    for name, model in signals.models().items():
        faults = K.unsettled(model)
        if faults:
            raise ValueError(f"{name}: {len(faults)} faces stand between two axes; run it through _kit.settle")
    n = signals.signal(c, FOOT, facing=FACING)
    n += lamps.place(c, "post", LAMP)
    lit = sky.build(c, (0, 0, 0))   # A2's light sources go in last, when everything that glows is in place
    c.entity_counts = {"props": n, "sky": lit or 0}
    return c


def build_models():
    """The family's models and the post lamp's."""
    out = dict(lamps.models())
    out.update(signals.models())
    return out


def write_pack(pack_dir):
    """The repainted stone and the pictures of the map's sky (the stage stands in the map's hour,
    mood.py)."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


# ---- the cameras ------------------------------------------------------------------------------------------
def shots():
    """The front as the train sees it, in the default light and in the deep night; the back as
    the platform sees it; the whole signal from the south-east; the lamp and the spectacle from
    close by."""
    out = []

    def shot(name, pos, look_at, time=TIME):
        out.append({"name": name, "pos": [round(float(v), 2) for v in pos],
                    "look_at": [round(float(v), 2) for v in look_at], "time": time})

    x, y, z = FOOT
    spindle = y + signals.HEIGHT
    eye = FEET + S.EYE
    shot("front", (x + 8.0, eye, z), (x, spindle - 0.5, z + 0.5))
    shot("front_deep", (x + 8.0, eye, z), (x, spindle - 0.5, z + 0.5), TIME_DEEP)
    shot("back", (x - 4.0, eye, z - 0.5), (x, spindle - 0.2, z + 0.7))
    shot("whole", (x + 6.0, eye, z + 5.0), (x, y + 2.6, z + 0.3))
    shot("head_near", (x + 2.5, spindle - 0.8, z - 1.9), (x, spindle, z - 0.2))
    return out
