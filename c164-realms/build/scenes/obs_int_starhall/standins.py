"""Plain stand-ins for the two machines the star hall is the room of, used by the hall's test
scenes only while machines/orrery and machines/clock are not in the tree: the orrery as its
envelope (the sun as machines/orrery makes it, its size and its bands of glass; flat orbits
five blocks across at the ring's height, the shaft up to the boss) and the mother clock as
machines/clock builds it (a dark case on the hall's plinth; the
dial a piece of its own with a fixed light, a step over what the case gets; the hands at the
skeleton's time). They offer the two lights the real machines offer, at the cells and levels the
director set.
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
CLOCK_DIAL = (0, 14)      # (sky, block) the dial is shown at: machines/clock's MASTER_DIAL_LIGHT (78b4c91b).
#                           A0, 11-16: in V7 the dial reads 0.35 or more and is the first thing seen. A display
#                           entity's face that looks east is drawn at half, whatever its `shade` says
DIAL_Y = 25.5             # eighths of a block over the case's foot: where machines/clock has its dial
SUN_R = 3.36              # eighths of a block: machines/orrery's SUN_R, 0.42 of a block
# the sun's glass from its foot to its crown, as machines/orrery paints it: the hot belt low, where
# the door and the floor look at it
SUN_BANDS = ((-1.0, -0.8, 1, 2), (-0.8, -0.2, 3, 3), (-0.2, 0.4, 3, 2), (0.4, 0.8, 2, 1), (0.8, 1.0, 1, 0))
WOOD_D = P.mat("dark_wood", base=1)
# orbit radius (eighths of a block), where the planet stands on it (degrees), its radius, its material
PLANETS = ((5.0, 40.0, 0.6, K.IRON), (8.0, 200.0, 0.9, K.CREAM), (11.0, 110.0, 1.0, K.ENAMEL),
           (14.0, 310.0, 0.8, K.COPPER), (17.0, 160.0, 1.6, K.BRASS), (20.0, 250.0, 1.3, K.CREAM))
SHAFT_TOP = 28.0            # the model's shaft ends here; iron pipe carries on to the boss


def _orrery():
    """Shown at scale 2 (units are eighths of a block). Anchor: the middle of the sun."""
    m = M.Model(PREFIX + "orrery", px=2.0)
    K.glass_ball(m, (0, 0, 0), SUN_R, [(a, b, layers, K.flat("glow", step)) for a, b, layers, step in SUN_BANDS],
                 sides=12)
    m.tube("y", (0, 0), SUN_R - 0.5, SHAFT_TOP, 0.6, K.BRASS_D)
    for r, deg, size, mat in PLANETS:
        a = math.radians(deg)
        x, z = r * math.cos(a), r * math.sin(a)
        m.ring("y", (0, 0, 0), r, 0.5, 0.5, K.BRASS_D, sides=24)
        m.beam((SUN_R * math.cos(a), 0, SUN_R * math.sin(a)), (x, 0, z), 0.5, 0.5, K.BRASS)
        m.ball((x, 0, z), size, mat, sides=8, layers=4)
    return m


def _clock():
    """Shown at scale 2. A case a block and a half wide, three quarters deep and four high; its
    front looks along +z. Anchor: the middle of its foot."""
    m = M.Model(PREFIX + "clock", px=2.0)
    m.box((-6, 0, -3), (6, 30, 3), P.mat("dark_wood"), grain="y")
    m.box((-6.5, 0, -3.5), (6.5, 2, 3.5), WOOD_D, grain="x")
    m.box((-6.5, 30, -3.5), (6.5, 32, 3.5), WOOD_D, grain="x")
    m.box((-2.5, 4, 3), (2.5, 15, 3.25), P.mat("night_glass", base=1))
    m.tube("z", (0, 7.0), 3.25, 3.5, 1.5, K.BRASS, sides=8)
    return m


def _clock_dial():
    """The dial, its bezel and its two hands at the skeleton's time. Shown at scale 2. Anchor: the
    middle of its back."""
    m = M.Model(PREFIX + "clock_dial", px=2.0)
    hour, minute = S.CLOCK
    ink = K.flat("iron", 1)
    # a prism in one flat tone: a tube's end is drawn a step darker, and machines/clock's plate is the lightest cream
    K.glass_prism(m, "z", (0, 0), 0.0, 0.25, 4.5, K.flat("cream", 3), sides=16, emit=0)
    m.ring("z", (0, 0, 0.375), 4.75, 0.5, 0.75, K.BRASS, sides=16)
    m.box((-0.5, -0.5, 0.25), (0.5, 2.75, 0.5), ink, rot=("z", -((hour % 12) + minute / 60.0) * 30.0, (0, 0, 0.25)))
    m.box((-0.375, -0.75, 0.5), (0.375, 3.75, 0.75), ink, rot=("z", -minute * 6.0, (0, 0, 0.5)))
    return m


@functools.lru_cache(maxsize=None)
def models():
    return {m.name: m for m in (_orrery(), _clock(), _clock_dial())}


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
    facing = S.MOTHER_CLOCK["facing"]
    # the case gets what the cell beside the lamp gets, as machines/clock's does
    n = K.put(canvas, models()[PREFIX + "clock"], (back + 0.375, y0, z), facing=facing, scale=2.0, origin=origin,
              brightness=(0, CLOCK_LEVEL - 1))
    n += K.put(canvas, models()[PREFIX + "clock_dial"], (back + 0.75 + K.NUDGE, y0 + DIAL_Y / 8.0, z), facing=facing,
               scale=2.0, origin=origin, brightness=CLOCK_DIAL)
    L.suggest(canvas, (ox + int(back) + 1, oy + int(y0) + 2, oz + int(math.floor(z))), CLOCK_LEVEL,
              "machines/clock:master", rank=2)
    return n
