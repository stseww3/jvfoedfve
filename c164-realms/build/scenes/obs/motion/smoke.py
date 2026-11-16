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
    what     campfire_signal_smoke, the game's tall campfire smoke: a grey puff 0.6 to 1.2 blocks
             across that lives 14 to 16 seconds, keeps the speed it is sent with and fades in its
             last three seconds. One particle to the command (count 0), sent with the velocity
             MK.downwind(lean) * rise: it rises and leans south with the north wind, WIND_LEAN
             degrees off the upright on average. Sent "force", or nobody further than 32 blocks
             off would be sent it, and the chimney is looked at from 30 to 110 blocks.
    how      Four lanes (LANES), one puff each in turn. A single spot and a single velocity draw
             a string of beads; the lanes start at four spots inside the flue's mouth, half a
             block down so that a puff is seen to come out of it, and differ a little in lean and
             in speed, so the column is a block and a half wide at the mouth, opens to three at
             its head 17 to 25 blocks up, and its beads never line up twice the same way.
    when     the pendulums' period (MK.PENDULUM), so the puffs ride on the ticks of a chain the
             place has anyway: DENSITY puffs a second cost DENSITY commands a second and nothing
             for the scheduling.

DENSITY is the card's parameter to be judged on the real machine (1, 2 or 4 puffs a second); 2 is
the default: a wisp, not a cloud.
"""
import importlib

from . import _kit as MK

SMOKE_PARTICLE = "campfire_signal_smoke"
BEAT = MK.PENDULUM              # 40 ticks: the chain the puffs ride on
DENSITY = 2                     # puffs a second from the chimney: 1, 2 or 4
RISE = 0.07                     # blocks a tick: what a campfire gives its own smoke
# The lanes of the chimney's smoke: (east, up, south) of powerhouse.SMOKE in blocks, the lean in
# degrees, the rise as a share of RISE. The flue is two blocks square and a puff collides as a
# quarter-block box: every start is at least a quarter of a block clear of the flue's walls, and
# north of the middle on average, because the puff drifts south as it climbs out.
LANES = (
    ((-0.35, -0.45, -0.40), 9.0, 1.00),
    ((0.40, -0.20, -0.15), 11.0, 0.92),
    ((-0.10, -0.60, 0.10), 8.0, 1.08),
    ((0.15, -0.30, -0.50), 12.0, 0.96),
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
        (dx, dy, dz), lean, share = LANES[k % len(LANES)]
        if not is_open:
            dy = ABOVE
        MK.puff(canvas, (spot[0] + dx, spot[1] + dy, spot[2] + dz), SMOKE_PARTICLE, BEAT, at=(tick,),
                count=0, spread=MK.downwind(lean), speed=RISE * share, far=True, origin=origin)
    return len(beats)


def build(canvas, origin=(0, 0, 0)):
    chimney(canvas, origin)
    return 0
