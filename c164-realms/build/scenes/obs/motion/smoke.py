"""motion/smoke: what the place breathes out (plan/packages/motion/smoke.md; plan/parts/motion.md 9).

The power house's chimney smokes: the one sign in the whole picture that somebody is on watch
tonight. Later rounds add the steam of the safety valve and the pipe joints, the sparks at the
furnace mouth and at the dynamo's brushes; each is registered only where its machine stands.

Nothing is placed here, no block and no entity. Every puff is a particle of the game's own, sent
by the loop of motion/_kit.py (MK.puff). With the loop stopped, or without the data pack, there
is no smoke and the picture is whole all the same.

The chimney
    where    powerhouse.SMOKE, the middle of the flue's mouth (site/powerhouse), and only when the
             chimney stands on the canvas: a scene that builds the motion line without the site
             has no smoke hanging in the air.
    what     campfire_signal_smoke, the game's tall campfire smoke: a grey puff that lives 14 to
             16 seconds, keeps the speed it is sent with and fades in its last three seconds. Its
             quad is 0.6 to 1.2 blocks across; what is seen of it on the real machine is 0.3 to
             0.8. One particle to the command (count 0), sent with the velocity
             MK.downwind(lean) * rise: it rises and leans south with the north wind, WIND_LEAN
             degrees off the upright on average. Sent "force", or nobody further than 32 blocks
             off would be sent it, and the chimney is looked at from 30 to 110 blocks.
    how      Eight lanes (LANES), one puff each in turn. A single spot and a single velocity draw
             a string of beads; the lanes start at eight spots spread over the flue's mouth, a
             quarter to half a block down so that a puff is seen to come out of it, and differ a
             little in lean, in their drift across the wind and in speed. The column is a good
             block wide at the mouth and opens to three or four at its head, 17 to 25 blocks up.
    when     the pendulums' period (MK.PENDULUM), so the puffs ride on the ticks of a chain the
             place has anyway: DENSITY puffs a second cost DENSITY commands a second and nothing
             for the scheduling.

DENSITY was the card's parameter to be judged on the real machine (1, 2 or 4 puffs a second). The
first cut had 2, a puff every 0.7 blocks of the column: beads a block apart at the mouth, a dotted
line from 60 blocks off (s1's pictures of 60494273; cr2, message 71977). It is 4 now, a puff every
0.35 blocks, which is less than a puff is wide: one wisp.
"""
import importlib
import math

from . import _kit as MK

SMOKE_PARTICLE = "campfire_signal_smoke"
BEAT = MK.PENDULUM              # 40 ticks: the chain the puffs ride on
DENSITY = 4                     # puffs a second from the chimney: 1, 2 or 4
RISE = 0.07                     # blocks a tick: what a campfire gives its own smoke
# The lanes of the chimney's smoke: (east, up, south) of powerhouse.SMOKE in blocks, the lean with
# the wind and the drift across it in degrees, the rise as a share of RISE. The flue is two blocks
# square and a puff collides as a quarter-block box (one that touches a wall loses its drift for
# good): every start is at least a quarter of a block clear of the flue's walls, and north of the
# middle on average, because the puff drifts south as it climbs out. Neighbours in the list start
# on opposite sides of the mouth. The leans average WIND_LEAN, the drifts nothing, the shares one:
# over the first four lanes (which is all that DENSITY 1 and 2 use) nearly so.
LANES = (
    ((-0.45, -0.45, -0.35), 9.0, -2.0, 1.00),
    ((0.40, -0.20, 0.10), 11.0, 1.5, 0.93),
    ((-0.10, -0.60, -0.55), 8.0, 3.0, 1.07),
    ((0.15, -0.30, 0.30), 12.0, -1.0, 0.96),
    ((0.55, -0.50, -0.40), 10.5, 2.5, 1.04),
    ((-0.35, -0.25, 0.25), 9.5, -3.0, 0.91),
    ((0.05, -0.55, -0.15), 11.5, -1.0, 1.09),
    ((-0.60, -0.35, 0.05), 8.5, 0.0, 0.98),
)
ABOVE = 0.1                     # where a puff starts over a mouth that is not open: this far above it


def _site(name):
    """A package of the site line, or None while it is not in the tree."""
    try:
        return importlib.import_module(f"scenes.obs.site.{name}")
    except ImportError:
        return None


def _beats(density):
    """The ticks of a BEAT on which the chimney puffs, `density` to the second."""
    n = density * BEAT // MK.SECOND
    if n < 1 or density * BEAT % MK.SECOND or BEAT % n:
        raise ValueError(f"{density} puffs a second do not fall on whole ticks of a cycle of {BEAT}")
    return [k * (BEAT // n) for k in range(n)]


def way(lean=MK.WIND_LEAN, drift=0.0):
    """The way a puff goes that rises one block: MK.downwind(lean), which is where the wind is
    read, and `drift` degrees off the upright across the wind (to the left of one who looks
    where it blows) on top of it. In still air there is nothing to be across of."""
    x, y, z = MK.downwind(lean)
    level = math.hypot(MK.WIND[0], MK.WIND[2])
    if level < 1e-9 or not drift:
        return (x, y, z)
    over = math.tan(math.radians(drift)) * y / level
    return (x + MK.WIND[2] * over, y, z - MK.WIND[0] * over)


def chimney_mouth(canvas, origin=(0, 0, 0)):
    """(the smoke's spot in scene coordinates, is the flue open under it), or None when no
    chimney stands on the canvas where site/powerhouse puts it."""
    house = _site("powerhouse")
    if house is None or not hasattr(house, "SMOKE"):
        return None
    ox, oy, oz = (int(v) for v in origin)
    flue = set(getattr(house, "FLUE", ()))
    rim = [(x, z) for x, z in getattr(house, "SHAFT", ()) if (x, z) not in flue]
    top = getattr(house, "TOP", None)
    if top is None or not rim or not any(canvas.has(x + ox, top + oy, z + oz) for x, z in rim):
        return None
    is_open = bool(flue) and not any(canvas.has(x + ox, top + oy, z + oz) for x, z in flue)
    return tuple(float(v) for v in house.SMOKE), is_open


def chimney(canvas, origin=(0, 0, 0), density=None):
    """Register the chimney's smoke. Returns the number of puffs in a BEAT, 0 without a chimney."""
    mouth = chimney_mouth(canvas, origin)
    if mouth is None:
        return 0
    spot, is_open = mouth
    beats = _beats(DENSITY if density is None else density)
    for k, tick in enumerate(beats):
        (dx, dy, dz), lean, drift, share = LANES[k % len(LANES)]
        if not is_open:
            dy = ABOVE
        MK.puff(canvas, (spot[0] + dx, spot[1] + dy, spot[2] + dz), SMOKE_PARTICLE, BEAT, at=(tick,),
                count=0, spread=way(lean, drift), speed=RISE * share, far=True, origin=origin)
    return len(beats)


def build(canvas, origin=(0, 0, 0)):
    chimney(canvas, origin)
    return 0
