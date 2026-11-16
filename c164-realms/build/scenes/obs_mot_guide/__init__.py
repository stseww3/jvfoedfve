"""Test scene of the work package motion/guide, part C: the bench.

A paved strip under the open sky with six stone posts in a row and one iron step. A post stands in
for a star chart, the step for the spot behind the eyepiece of the great refractor, and the air
over the step for the dome's slit. guide.quest() is told these places and nothing else: the
commands and the functions are the map's, word for word, and only the places differ (the lights
go up an arc of ARC_R blocks here, not the dome's 13).

What the real machine has to show, with the scene's loop started:

    1  Walk along the row on its south side. At each post, once: a soft chime and, over the
       hotbar, "Star chart 1 of 6", then 2, 3 ... in the order they are walked up to. A post that
       has been counted is silent the second time. A second player hears and reads nothing of
       the first one's. Walking along the north side, behind the posts, takes none: a post is
       taken from the spot before it (STAND), as a chart is not taken through a wall.
    2  Stand on the step with none: nothing. With some: "Star charts: 3 of 6" for as long as one
       stands there, gone three seconds after one has stepped off.
    3  Stand on the step with all six: the title THE COMET, IN FOCUS once, one bell, and for ten
       seconds points of light that climb, east of the step, from head height to eight blocks up.
       Stand on it again: nothing.
    4  Leave the server in the middle of the row and come back: the count goes on.

The map has no function that takes the charts away again (the card: no tool of the owner's is
left in it). To walk the bench a second time an operator takes his own tags off by hand:
    /tag @s remove c164.c1   ... c164.c6, c164.done

The camera shows the bench twice, as every scene of this line does; nothing in the picture moves
until a player has all six.

    python -m scenes.obs_mot_guide      (in build/) writes shots.json
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.motion import guide

BIOME = "obs_blue"
BIOME_MARGIN = 40
BIOME_MARGIN_Y = 60
TIME = 14000                    # light version A, the default

PAVING, POST, STEP = B.TUFF_SMOOTH.block, B.TUFF_BRICK.block, B.IRON_RIVETED.block
FLOOR = 0                       # y of the first air over the paving
STRIP = (0, 0, 20, 10)          # x0, z0, x1, z1
POSTS = tuple((2 + 3 * k, 2) for k in range(6))     # the posts' columns: three blocks apart, so no two are in reach at once
STEP_AT = (10, 7)               # the step's column
ARC_R = 6.0                     # the radius of the arc the lights climb
ARC_HALF = 1.75                 # ... and half its width, the dome's slit's

CHARTS = tuple((f"post{k + 1}", (x + 0.5, FLOOR + 1.0, z + 0.5), float(FLOOR)) for k, (x, z) in enumerate(POSTS))
STAND = tuple((x + 0.5, float(FLOOR), z + 1.5) for x, z in POSTS)      # before a post, on its south
OBSERVER = (STEP_AT[0] + 0.5, FLOOR + 1.0, STEP_AT[1] + 0.5)
DOME = ((OBSERVER[0] + ARC_R, FLOOR + 2.0, OBSERVER[2]), ARC_R, ARC_HALF, "west")


def shots():
    x0, z0, x1, z1 = STRIP
    mid = (x0 + x1 + 1) / 2.0
    view = dict(pos=[mid, FLOOR + 5.0, z1 + 7.0], look_at=[mid, FLOOR + 2.0, z0 + 4.0], time=TIME)
    return [dict(name="bench" + again, **view) for again in ("", "_again")]


def build():
    c = Canvas()
    x0, z0, x1, z1 = STRIP
    c.box(x0, FLOOR - 1, z0, x1, FLOOR - 1, z1, PAVING)
    for x, z in POSTS:
        c.set(x, FLOOR, z, POST)
    c.set(STEP_AT[0], FLOOR, STEP_AT[1], STEP)
    guide.quest(c, CHARTS, OBSERVER, DOME, (0, 0, 0), stands=STAND)
    c.entity_counts = {"motion": 0}
    return c


def write_pack(pack_dir):
    """The repainted stone and iron the bench is made of, and the map's sky."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
