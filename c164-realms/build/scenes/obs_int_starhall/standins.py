"""Plain stand-ins for the two machines the star hall is the room of, used by the hall's test
scenes only while machines/orrery and machines/clock are not in the tree: the orrery as its
envelope (a small warm sun, flat orbits five blocks across at the ring's height, the shaft up to
the boss) and the mother clock as a dark case with a pale dial on the hall's plinth. They offer the
two lights the real machines offer, at the cells and levels the director set.
"""
import functools
import math

from artkit import models as M

from scenes.obs.common import blocks as B
from scenes.obs.common import palette as P
from scenes.obs.common import skeleton as S
from scenes.obs.props import _kit as K
from scenes.obs.sky import _lightkit as L

PREFIX = "int_starhall_standin_"
SUN_LEVEL, CLOCK_LEVEL = 12, 11
WOOD_D = P.mat("dark_wood", base=1)
# orbit radius (eighths of a block), where the planet stands on it (degrees), its radius, its material
PLANETS = ((5.0, 40.0, 0.6, K.IRON), (8.0, 200.0, 0.9, K.CREAM), (11.0, 110.0, 1.0, K.ENAMEL),
           (14.0, 310.0, 0.8, K.COPPER), (17.0, 160.0, 1.6, K.BRASS), (20.0, 250.0, 1.3, K.CREAM))
SHAFT_TOP = 28.0            # the model's shaft ends here; iron pipe carries on to the boss


def _orrery():
    """Shown at scale 2 (units are eighths of a block). Anchor: the middle of the sun."""
    m = M.Model(PREFIX + "orrery", px=2.0)
    K.glass_ball(m, (0, 0, 0), 3.5, [(-1.0, -0.6, 1, K.GLOW_DIM), (-0.6, -0.2, 1, K.GLOW_MID),
                                     (-0.2, 0.6, 2, K.GLOW_HOT), (0.6, 1.0, 1, K.GLOW_MID)], sides=12)
    m.tube("y", (0, 0), 3.0, SHAFT_TOP, 0.6, K.BRASS_D)
    for r, deg, size, mat in PLANETS:
        a = math.radians(deg)
        x, z = r * math.cos(a), r * math.sin(a)
        m.ring("y", (0, 0, 0), r, 0.5, 0.5, K.BRASS_D, sides=24)
        m.beam((3.5 * math.cos(a), 0, 3.5 * math.sin(a)), (x, 0, z), 0.5, 0.5, K.BRASS)
        m.ball((x, 0, z), size, mat, sides=8, layers=4)
    return m


def _clock():
    """Shown at scale 2. A case a block and a half wide, three quarters deep and four high; its
    front looks along +z. Anchor: the middle of its foot."""
    m = M.Model(PREFIX + "clock", px=2.0)
    m.box((-6, 0, -3), (6, 30, 3), P.mat("dark_wood"), grain="y")
    m.box((-6.5, 0, -3.5), (6.5, 2, 3.5), WOOD_D, grain="x")
    m.box((-6.5, 30, -3.5), (6.5, 32, 3.5), WOOD_D, grain="x")
    m.tube("z", (0, 23.0), 3.0, 3.5, 5.0, K.BRASS_D, sides=16)
    m.tube("z", (0, 23.0), 3.5, 3.75, 4.25, K.CREAM, sides=16)
    m.box((-0.25, 23.0, 3.75), (0.25, 26.5, 4.0), K.IRON_D, rot=("z", -25.0, (0, 23.0, 3.75)))
    m.box((-0.25, 23.0, 3.75), (0.25, 25.5, 4.0), K.IRON_D, rot=("z", 115.0, (0, 23.0, 3.75)))
    m.box((-2.5, 4, 3), (2.5, 15, 3.25), P.mat("night_glass", base=1))
    m.tube("z", (0, 7.0), 3.25, 3.5, 1.5, K.BRASS, sides=8)
    return m


@functools.lru_cache(maxsize=None)
def models():
    return {m.name: m for m in (_orrery(), _clock())}


def orrery(canvas, origin=(0, 0, 0)):
    ox, oy, oz = origin
    cx, cz = S.ORRERY_CENTRE
    n = K.put(canvas, models()[PREFIX + "orrery"], (cx, S.ORRERY_RING_Y, cz), scale=2.0, origin=origin)
    x, z = int(math.floor(cx)), int(math.floor(cz))
    for y in range(int(math.ceil(S.ORRERY_RING_Y + SHAFT_TOP / 8.0)), S.STAR_HALL_CEIL):
        canvas.set(ox + x, oy + y, oz + z, f"{B.IRON_PIPE}[axis=y]")
    L.suggest(canvas, (ox + x, oy + int(S.ORRERY_RING_Y), oz + z), SUN_LEVEL, "machines/orrery:sun", rank=2)
    return n


def clock(canvas, origin=(0, 0, 0)):
    ox, oy, oz = origin
    back, z, (y0, _) = S.MOTHER_CLOCK["back_x"], S.MOTHER_CLOCK["z"], S.MOTHER_CLOCK["y"]
    n = K.put(canvas, models()[PREFIX + "clock"], (back + 0.375, y0, z), facing=S.MOTHER_CLOCK["facing"],
              scale=2.0, origin=origin, brightness=(0, CLOCK_LEVEL))
    L.suggest(canvas, (ox + int(back) + 1, oy + int(y0) + 2, oz + int(math.floor(z))), CLOCK_LEVEL,
              "machines/clock:master", rank=2)
    return n
