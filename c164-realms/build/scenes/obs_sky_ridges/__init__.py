"""Test scene of the work package sky/ridges (plan/packages/sky/ridges.md).

The terrace as a flat shelf with the station's own sky above it, and the four ridge planes out at
380 blocks. The card asks for five views, and they are the whole test:

  west          due west from the sunset platform: the afterglow's side, where a ridge must NOT stand
  northwest     the north-west group, seen from the platform
  southwest     the south-west group
  east          due east: nothing there, and nothing should be
  far_walk      from the far end of the terrace, looking west again -- do the ridges slide against
                the cloud sea as you walk?

A ridge is only visible where there is afterglow behind it, and offline the sun's fan is not drawn at
all (plan/packages/common/offline-sky.md), so **these pictures show the planes' placement and shape,
not whether they read in the game**. That judgement is the real game's, and the card says so.

    python -m scenes.obs_sky_ridges        writes shots.json from the layout
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.sky import ridges

BIOME = "obs_blue"
CATEGORY = "sky"
TIME = 12900                      # the afterglow's own time: the ridges are for this hour

SHELF = 40                        # the platform's half-width, blocks
WALL = B.TUFF_BRICK.block


def _platform(c):
    """A flat shelf with a low parapet, so the camera stands at a known height on a known edge."""
    for x in range(-SHELF, SHELF + 1):
        for z in range(-SHELF, SHELF + 1):
            c.set(x, -1, z, WALL)
    for i in range(-SHELF, SHELF + 1):
        for (x, z) in ((i, -SHELF), (i, SHELF), (-SHELF, i), (SHELF, i)):
            c.set(x, 0, z, WALL)
    return c


def layout(c=None):
    c = c or Canvas()
    _platform(c)
    n = ridges.build(c, (0, 0, 0))
    return c, n


def build():
    c, _ = layout()
    return c


def build_models():
    return ridges.models()


def write_pack(pack_dir):
    out = materials.pack(pack_dir)
    out += ridges.pack(pack_dir)
    return out


def shots():
    out = []

    def shot(name, pos, look_at, time=TIME):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": time})

    eye = 1.62
    shot("west", (0.0, eye, 0.0), (-40.0, eye, 0.0))
    shot("northwest", (0.0, eye, 0.0), (-28.0, eye, -28.0))
    shot("southwest", (0.0, eye, 0.0), (-28.0, eye, 28.0))
    shot("east", (0.0, eye, 0.0), (40.0, eye, 0.0))
    shot("far_walk", (-30.0, eye, 30.0), (-60.0, eye, 10.0))
    return out
