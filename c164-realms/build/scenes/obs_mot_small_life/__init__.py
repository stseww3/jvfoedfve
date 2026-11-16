"""Test scene of the work package motion/small-life: the steam at the boiler house's door and the
moths at the lamps.

The power house stands where it does in the master scene, on a slab of the lower platform, with the
four street lamps that carry moths on their own feet (two of them on stand-ins for the pedestals at
the grand stair's foot). So motion/small_life finds the door and the lamps and registers what it
registers in the master scene, and the two locked views that are to show it stand right here.

Particles are not drawn offline: the offline pictures show the bare stage, and what stirs is for
the real machine to say. Every camera is in the shot list twice, the second time as <name>_again,
so that a difference of the pair shows what has moved in between. The game must not be frozen
while the pictures are taken, and the pair should be taken a second or two apart, not a whole
number of ROUNDs (8 seconds).

The cameras
    v1       the skeleton's locked arrival view: three of the lamps on its left, 17 to 28 blocks off
    v6       the skeleton's locked view of the power house: the door 17 blocks off, the fourth
             lamp eight blocks before the eye
    lamp     three blocks from the globe of the nearest lamp of the arrival view: a moth is a
             dot of one texel, and darker than the glass
    door     from the yard, five blocks before the wicket: the wisps climb the gate and pass the lamp
    door_side  along the front: how far the wisps stand off the wall

    python -m scenes.obs_mot_small_life      (in build/) writes shots.json
"""
import math

from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.motion import small_life
from scenes.obs.props import lamps
from scenes.obs.site import powerhouse

BIOME = "obs_blue"
BIOME_MARGIN = 100
BIOME_MARGIN_Y = 150

PAVING = B.TUFF_SMOOTH.block
ROCK = B.TUFF.block
TIME = 14000                    # light version A, the default
EYE = S.EYE


def _views():
    (lx, ly, lz), _view, _n = small_life.MOTH_LAMPS[0]
    gx, gy, gz = (v + d for v, d in zip((lx, ly, lz), lamps.GLOBES["street"]["at"]))
    (dx, dz), top = powerhouse.DOOR_AT["cell"], max(powerhouse.DOOR_AT["y"]) + 1
    feet = S.LOWER_GROUND + EYE
    return [
        ("v1", S.V1["pos"], S.V1["look_at"]),
        ("v6", S.V6["pos"], S.V6["look_at"]),
        ("lamp", (gx + 1.6, gy - 0.9, gz - 2.4), (gx, gy, gz)),
        ("door", (dx + 1.3, feet, dz - 5.0), (dx + 0.5, top + 0.9, dz)),
        ("door_side", (dx - 4.0, feet + 0.6, dz - 0.9), (dx + 0.5, top + 0.9, dz - 0.3)),
    ]


def shots():
    out = []
    for again in ("", "_again"):
        for name, pos, look_at in _views():
            out.append({"name": name + again, "pos": [round(float(v), 2) for v in pos],
                        "look_at": [round(float(v), 2) for v in look_at], "time": TIME})
    return out


def stage():
    """The lower platform's paving, the power house and the four lamps: the canvas before
    motion/small_life and the sky line come to it."""
    c = Canvas()
    x0, z0, x1, z1 = S.LOWER_PLATFORM
    c.box(x0, S.LOWER_PAVING_Y - 2, z0, x1, S.LOWER_PAVING_Y - 1, z1, ROCK)
    c.box(x0, S.LOWER_PAVING_Y, z0, x1, S.LOWER_PAVING_Y, z1, PAVING)
    shell = powerhouse.build(c, (0, 0, 0))          # its own entities: the lamp over the wicket
    for (x, y, z), _view, _n in small_life.MOTH_LAMPS:
        for under in range(S.LOWER_GROUND, math.ceil(y)):   # a pedestal, where the foot stands over the paving
            c.set(math.floor(x), under, math.floor(z), PAVING)
    n = lamps.site(c, (0, 0, 0), groups=("way",))
    c.entity_counts = {"props": int(n or 0), "site": int(shell or 0), "motion": 0}
    return c


def build():
    c = stage()
    small_life.build(c, (0, 0, 0))
    sky.build(c, (0, 0, 0))                         # the sky line's light sources go in last
    return c


def build_models():
    return dict(lamps.models() or {})


def write_pack(pack_dir):
    """The repainted tuff, iron and glass of the house, and the map's sky: the moths are judged
    against it."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
