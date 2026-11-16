"""Test scene of the work package machines/locomotive (plan/packages/machines/locomotive.md): the
rack engine by itself, on a level piece of track in a paved yard.

The track runs east and west; the cameras stand south of it and look north, so that west, where
the car stands in the train, is on the left. Three engines stand on it, nine blocks from one to
the next:

    still     the engine as it stands in the station: complete, nothing moves but the fire
    stand     the same engine running on the spot: wheels, cog, connecting rods and crossheads are
              driven by the loop (the proof of the running gear; in the train motion's travel turns
              them with the way run)
    quarter   the engine a quarter turn of its wheels further on, still: the pins up, the rods
              leaning, to read pose() off a picture

The shots are written from the numbers below:  python -m scenes.obs_mach_locomotive
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.machines import locomotive
from scenes.obs.props import _kit as K

BIOME = "obs_blue"
CATEGORY = "machines"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32
TIME = 14000                    # light version A, the default

PAVING = B.TUFF_SMOOTH.block
TRACK_Z = 0.5                   # the track's centre line: the rails are the rows z -1 and z 1
STILL = (0.0, 0.0, TRACK_Z)
STAND = (9.0, 0.0, TRACK_Z)
QUARTER = (18.0, 0.0, TRACK_Z)
YARD = (-9, -8, 27, 10)         # x0, z0, x1, z1

VIEWS = [
    # the still engine: its south side square on, the end the car sees, the cab from behind, close
    # on the motion, from above, the north side
    ("side", (0.0, 1.6, 7.0), (0.0, 1.35, TRACK_Z)),
    ("front", (-5.5, 1.9, TRACK_Z), (-1.5, 1.6, TRACK_Z)),
    ("front_near", (-3.6, 2.3, 2.2), (-1.3, 1.6, 0.4)),
    ("cab", (4.9, 2.3, 2.6), (1.4, 1.9, 0.4)),
    ("cab_in", (2.9, 2.6, TRACK_Z), (1.1, 1.9, TRACK_Z)),
    ("gear", (0.4, 0.9, 3.6), (0.2, 0.5, 1.7)),
    ("above", (-2.8, 4.8, 3.6), (-0.2, 1.6, 0.5)),
    ("north", (0.6, 1.6, -6.0), (0.0, 1.35, TRACK_Z)),
    # the engine on the stand, and the one a quarter turn on
    ("stand", (9.0, 1.6, 7.0), (9.0, 1.2, TRACK_Z)),
    ("stand_gear", (9.4, 0.9, 3.6), (9.2, 0.5, 1.7)),
    ("quarter", (18.0, 1.6, 7.0), (18.0, 1.2, TRACK_Z)),
    ("quarter_gear", (18.4, 0.9, 3.6), (18.2, 0.5, 1.7)),
    ("row", (9.0, 5.0, 15.5), (9.0, 1.0, TRACK_Z)),
]


def shots(names=None):
    """The shot list, or the views of it that are named."""
    return [{"name": name, "pos": [round(float(v), 2) for v in pos],
             "look_at": [round(float(v), 2) for v in look_at], "time": TIME}
            for name, pos, look_at in VIEWS if names is None or name in names]


def build():
    # no face may stand between two axes (props/_kit.settle sees to it where the models are built)
    loose = sorted(name for name, model in locomotive.models().items() if K.unsettled(model))
    assert not loose, f"faces between two axes, not settled: {loose}"
    c = Canvas()
    x0, z0, x1, z1 = YARD
    c.box(x0, -1, z0, x1, -1, z1, PAVING)
    c.box(x0, -1, -1, x1, -1, -1, B.IRON_RIVETED.block)
    c.box(x0, -1, 1, x1, -1, 1, B.IRON_RIVETED.block)
    c.box(x0, -1, 0, x1, -1, 0, B.IRON_GRATE)
    n = locomotive.place(c, STILL, light=True)
    n += locomotive.place(c, STAND, stand=True)
    n += locomotive.place(c, QUARTER, run=locomotive.REV / 4.0)
    sky.build(c, (0, 0, 0))         # the sky line's light sources go in last
    c.entity_counts = {"machines": n}
    return c


def build_models():
    return locomotive.models()


def write_pack(pack_dir):
    """The repainted blocks the engine stands on, and the map's sky (mood.py keeps the map's hour)."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
