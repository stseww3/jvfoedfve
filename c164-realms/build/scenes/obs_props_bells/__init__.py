"""Test scene of props/bells: the entrance's bell and its push on a stretch of the main front.

A wall looks south, in the courses of the main front as far up as the string course, with two
pilasters four cells apart. On the west one hangs the bell as it hangs at the entrance: over a
bracket lamp of props/lamps, its back just under the string course. On the east one the push, at
the height of a hand in the plinth's upper course.

The hammer strikes its call once in bells.LOOP ticks (the motion line writes the loop; the pictures
show it at rest).

The shots are written from the numbers below:  python -m scenes.obs_props_bells
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.props import bells, lamps

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32
TIME = 14000

WALL_X = (-5, 9)
PIERS = {"bell": 0, "push": 4}      # the cells of the two pilasters
LAMP_Y = 4.0                        # where props/lamps hangs the pair at the entrance
FACE = 1.0                          # the plane of the pilasters' fronts
BELL = (PIERS["bell"] + 0.5, S.STRING - bells.BELL_DOWN - bells.BACK[1] * bells.PX, FACE)
PUSH = (PIERS["push"] + 0.5, S.PLINTH[0] + 1.0 + bells.PUSH_UP, FACE)


def _course(y):
    if y <= S.PLINTH[1]:
        return B.SLATE_BRICK.block
    return B.ASHLAR_ROUGH.block if y <= S.BASE[1] else B.ASHLAR_FINE.block


def build():
    c = Canvas()
    c.box(WALL_X[0] - 2, -1, -1, WALL_X[1] + 2, -1, 14, B.TUFF_SMOOTH.block)
    for y in range(S.STRING + 3):
        c.box(WALL_X[0], y, -1, WALL_X[1], y, -1, _course(y))
        for x in PIERS.values():
            c.set(x, y, 0, _course(y))
    c.box(WALL_X[0], S.STRING, 0, WALL_X[1], S.STRING, 0, B.ASHLAR_FINE.block)      # the string course, a cell proud
    for x in PIERS.values():
        c.set(x, S.STRING, 1, B.ASHLAR_FINE.block)                                  # and round the pilasters
    n = lamps.place(c, "bracket", (PIERS["bell"] + 0.5, LAMP_Y, FACE))
    n += bells.bell(c, BELL, facing="south")
    n += bells.push(c, PUSH, facing="south")
    sky.build(c, (0, 0, 0))
    c.entity_counts = {"props": n}
    return c


def write_pack(pack_dir):
    """The repainted stone the bell hangs on, and the pictures of the map's sky."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots():
    bx, by, _ = BELL
    px, py, _ = PUSH
    return [
        {"name": "bell_near", "pos": [bx + 0.9, by - 0.5, FACE + 2.2], "look_at": [bx, by - 0.1, FACE], "time": TIME},
        {"name": "bell_side", "pos": [bx + 2.6, by - 0.2, FACE + 1.2], "look_at": [bx, by, FACE + 0.1], "time": TIME},
        {"name": "push_near", "pos": [px + 0.5, S.EYE, FACE + 1.6], "look_at": [px, py + 0.1, FACE], "time": TIME},
        {"name": "court", "pos": [bx + 3.0, S.EYE, FACE + 8.5], "look_at": [bx + 1.5, 4.0, FACE], "time": TIME},
    ]
