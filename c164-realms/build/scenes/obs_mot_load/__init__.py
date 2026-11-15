"""Load scene of the work package motion/loop: what the loop costs the server.

A wall of 200 small wheels, a block apart, each turning once in 24 ticks in four steps. They are
put out of step along the diagonals, so every tick moves about 34 of them: an even load of some
35 commands a tick, three and a half times what the whole map is allowed on average
(plan/parts/motion.md section 7). On the real machine the tick time is read with the loop
running and with it stopped; the difference is what 35 commands a tick cost, and section 7's
limits are set by it.

The scene raises its own limits (MK.limits), so the check's item "motion" is WARN for it, by
design. It is a measuring rig: it never goes into the master scene.

The shots are written from the numbers below:  python -m scenes.obs_mot_load
"""
from artkit import models as M
from artkit.canvas import Canvas

from scenes.obs import materials
from scenes.obs.common import blocks as B
from scenes.obs.motion import _kit as MK

from . import props

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32

STONE, PAVING = B.ASHLAR_FINE.block, B.TUFF_SMOOTH.block
COLS, ROWS = 20, 10
OUT = 0.25                      # blocks the wheels stand off the wall's face
SOUTH = (0, 0, 1)
REV = 24                        # ticks a turn: four steps of six ticks
SPREAD = 6                      # the wheels start this many ticks apart, diagonal by diagonal
LAMP_LEVEL = 11
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)


def light(level):
    return f"{B.LIGHT}[level={level}]"


def build():
    c = Canvas()
    c.box(-3, -1, -1, COLS + 2, -1, 14, PAVING)
    c.box(-1, 0, -1, COLS, ROWS, -1, STONE)
    cog = props.model("load_cog")
    n = 0
    for col in range(COLS):
        for row in range(ROWS):
            c.add_entity(col + 0.5, row + 0.5, OUT, M.display(cog))
            MK.spin(c, SOUTH, REV, phase=(col + row) % SPREAD)
            n += 1
    MK.limits(c, peak=60, mean=40.0)
    for x in range(1, COLS, 3):
        for y in (2, 7):
            c.set(x, y, 1, light(LAMP_LEVEL), keep=True)
    c.entity_counts = {"motion": n}
    return c


def write_pack(pack_dir):
    """The repainted stone the wheels are seen against."""
    return materials.pack(pack_dir)


def shots():
    """The whole wall and a near look, each twice (see scenes.obs_mot_loop)."""
    x, y = COLS / 2.0, ROWS / 2.0
    views = [("far", (x, y, 9.0), (x, y, 0.0)), ("near", (x, y, 3.0), (x, y, 0.0))]
    out = []
    for again in ("", "_again"):
        for name, pos, look_at in views:
            out.append({"name": name + again, "pos": [round(float(v), 2) for v in pos],
                        "look_at": [round(float(v), 2) for v in look_at], "time": TIME})
    return out
