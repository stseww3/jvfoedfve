"""The small life of the place (card plan/packages/motion/small-life.md): what stirs where nothing
is a machine. The steam at the boiler house's door, the moths at the lamps.

Nothing is placed here, no block and no entity. Everything is a particle of the game's own, sent
by the loop (motion/_kit); who stands further off than 32 blocks is not sent any of it.

  steam    The wicket of the power house stands open and the house is warm: what the boilers lose
           creeps out under the top of the opening and climbs the gate's plates, past the lamp
           over the door, and is gone before the glass. A wisp every second or so
           (DOOR_WISPS), the game's cloud, as motion/smoke has it for the safety valve. The wind
           is from the north and stands on this front, so nothing blows away: a wisp leaves the
           wall by a quarter of what it rises. It starts over the opening and not in it: this
           particle of the game's sinks to the feet of a player who is nearer than two blocks,
           and the top of the opening is two blocks over the sill.
  moths    At the street lamps that the arrival view and the power house's view have before them
           (MOTH_LAMPS). A moth is one dot, a texel of this map's, that flies about the globe in
           short straight hops, bumps the glass now and then, and sits on it for a while and
           creeps (flight()). The game's trail: a particle that goes from where it is sent to a
           point it is given in the time it is given, without wind, weight or chance, so a hop
           is one command and the next hop starts where this one ends. It is drawn in the colour
           it is given whatever light stands there: MOTH_COLOUR is darker than the darkest glass
           of a globe (the game lightens or darkens every dot by up to an eighth; the brightest
           moth has 0.58 of white, the globe 0.69 to 0.89), so a moth before the sky is a pale
           dot and a moth before the globe a dark one. Two to a lamp at most.

Both ride on motion/smoke's BREATH (160 ticks), the moths on every eighth tick of it and the second
moth of a lamp on the ticks half-way between, where the steam's wisps are too: forty ticks of the
chain for all of it.
"""
import math
import random

from . import _kit as MK
from . import smoke

ROUND = smoke.BREATH            # 160 ticks: one round of everything here
VIEWERS = "normal"              # the game's word for: only who stands within 32 blocks

# ---- the steam at the boiler house's door ----------------------------------------------------------
WISP = smoke.STEAM_PARTICLE
DOOR_OUT = 0.12                 # blocks before the gate's face a wisp starts
DOOR_OVER = 0.1                 # ... and over the top of the opening
# The wisps of a ROUND: the tick, where along the lintel it starts (blocks from the opening's
# middle; the opening is one wide), blocks a tick it rises with, and what it goes out from the
# wall and along it for one block of rise. The game slows a wisp by a 25th every tick: one that
# starts with 0.06 climbs a block and a half, as high as the lamp.
DOOR_WISPS = (
    (4, -0.22, 0.062, 0.25, -0.06),
    (20, 0.18, 0.050, 0.18, 0.08),
    (28, -0.05, 0.045, 0.30, 0.02),
    (52, 0.27, 0.066, 0.22, -0.04),
    (68, -0.30, 0.048, 0.20, 0.10),
    (84, 0.06, 0.070, 0.28, -0.08),
    (92, -0.14, 0.046, 0.16, 0.05),
    (116, 0.22, 0.058, 0.26, 0.03),
    (132, -0.26, 0.064, 0.20, -0.02),
    (148, 0.10, 0.052, 0.24, 0.07),
)

# ---- the moths -------------------------------------------------------------------------------------
MOTH = "trail"
MOTH_COLOUR = 0x8F8468          # a dusty wing in lamp light
HOP = 8                         # ticks from one point of a flight to the next
HALF = HOP // 2                 # the second moth of a lamp flies on the ticks in between
TOUCH = 0.07                    # blocks off the glass: where a moth sits, and how near it comes when it bumps
SHELL = (0.2, 0.7)              # blocks off the glass: where a flight's other points lie
RISE = (-40.0, 35.0)            # degrees over the globe's middle: a flight keeps off the ironwork under it
CLEAR = 0.07                    # a hop passes the glass by this, or by what its nearer end has
HOP_TURN = 75.0                 # degrees round the globe one hop may go: further, and it would cut through
CREEP = 0.12                    # blocks a sitting moth creeps on the glass
# A moth of a lamp: (hops of its flight, which way round: 1 turns as the sun goes for who looks
# down on the lamp, times it bumps the glass). A flight goes once about the globe and turns back
# on the way once or twice. What is left of the ROUND the moth sits.
MOTHS = ((12, 1, 1), (14, -1, 2))
# The lamps: the foot as props/lamps.site_lamps() names it, the view it stands in (the moths sit
# on the side of the globe that view sees), how many moths.
MOTH_LAMPS = (
    ((80.5, -6.0, -17.5), "V1", 2),     # the three on the left of the arrival view: 17, 25 and
    ((79.5, -6.0, -9.5), "V1", 2),      # 28 blocks from that eye
    ((73.0, -3.0, -9.0), "V1", 1),
    ((73.0, -3.0, 10.0), "V6", 2),      # at the stair's foot, eight blocks before the eye of V6
)
STEP = 40                       # ticks from one lamp's round to the next lamp's: they do not sit in step
LAMP_NEAR = 0.1                 # blocks: a lamp stands on its foot when its model is this near it


# ---- the steam -------------------------------------------------------------------------------------
def door(canvas, origin=(0, 0, 0)):
    """((x, y, z) of the middle of the top edge of the open wicket, on the gate's outer face, in
    scene coordinates; the way out of the wall as (dx, dz)), or None when no gate stands on the
    canvas where site/powerhouse hangs it."""
    house = smoke._package("site", "powerhouse")
    at = getattr(house, "DOOR_AT", None)
    if not at:
        return None
    out = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}[at["front"]]
    (x, z), top = at["cell"], max(at["y"]) + 1
    ox, oy, oz = (int(v) for v in origin)
    plate = canvas.has(x + ox, top + oy, z + oz)                    # the gate over the opening
    air = not canvas.has(x + out[0] + ox, top + oy, z + out[1] + oz)
    if not plate or not air:
        return None
    # the face of the cell that looks out
    return (x + 0.5 + out[0] * 0.5, float(top), z + 0.5 + out[1] * 0.5), out


def door_steam(canvas, origin=(0, 0, 0), wisps=None):
    """Register the steam at the boiler house's door. Returns the number of wisps in a ROUND, 0
    without the door."""
    found = door(canvas, origin)
    if found is None:
        return 0
    (x, y, z), (ox, oz) = found
    wisps = DOOR_WISPS if wisps is None else tuple(wisps)
    for tick, along, speed, out, drift in wisps:
        # along the lintel is across the way out
        start = (x + ox * DOOR_OUT - oz * along, y + DOOR_OVER, z + oz * DOOR_OUT + ox * along)
        way = (ox * out - oz * drift, 1.0, oz * out + ox * drift)
        MK.puff(canvas, start, WISP, ROUND, at=(tick,), count=0, spread=way, speed=speed, origin=origin)
    return len(wisps)


# ---- the moths -------------------------------------------------------------------------------------
def _point(radius, turn, rise):
    """A point about the globe's middle: `turn` degrees from east towards south, `rise` over it."""
    a, e = math.radians(turn), math.radians(rise)
    return (radius * math.cos(e) * math.cos(a), radius * math.sin(e), radius * math.cos(e) * math.sin(a))


def _passes(a, b):
    """How near the hop from a to b comes to the globe's middle."""
    d = [b[i] - a[i] for i in range(3)]
    n = sum(v * v for v in d)
    t = 0.0 if n < 1e-12 else max(0.0, min(1.0, -sum(a[i] * d[i] for i in range(3)) / n))
    return math.sqrt(sum((a[i] + t * d[i]) ** 2 for i in range(3)))


def _tries(rng, hops, way, face, glass, bumps):
    """One draw of a flight (flight()), or None when one of its hops would pass through the globe."""
    sit = glass + TOUCH
    home = (face + rng.uniform(-35.0, 35.0), rng.uniform(-10.0, 25.0))      # degrees round, degrees up
    crept = (home[0] + way * math.degrees(CREEP / sit), home[1] + rng.uniform(-4.0, 4.0))
    # The points of the round: 0 where it takes off, 1 .. hops - 1 its flight, hops where it sits
    # down. At the glass are both ends and the bumps. A hop to the glass or from it goes straight in
    # or out, or nearly (a chord from the glass to a point further round would pass through the
    # globe): the way round is made on the other hops, and a few of those turn back.
    glassy = [True] + [False] * (hops - 1) + [True]
    for n in range(bumps):
        glassy[int(round((n + 1) * hops / (bumps + 1.0)))] = True
    travel = [k for k in range(hops) if not glassy[k] and not glassy[k + 1]]
    signs = [1] * len(travel)
    for i in rng.sample(range(1, len(travel) - 1), max(0, (len(travel) - 6) // 2)):
        signs[i] = -1
    sizes = [rng.uniform(0.7, 1.3) for _ in travel]
    net = sum(sign * size for sign, size in zip(signs, sizes))
    turns = {k: way * sign * size * 360.0 / net for k, sign, size in zip(travel, signs, sizes)}
    if max(abs(v) for v in turns.values()) > HOP_TURN:
        return None
    ways, points = [crept], [_point(sit, *crept)]
    for k in range(1, hops + 1):
        last = ways[-1]
        if k == hops:
            here = home
        elif k - 1 in turns:
            here = (last[0] + turns[k - 1], rng.uniform(*RISE))
        else:
            here = (last[0] + rng.uniform(-8.0, 8.0), max(RISE[0], min(RISE[1], last[1] + rng.uniform(-8.0, 8.0))))
        p = _point(sit if glassy[k] else glass + rng.uniform(*SHELL), *here)
        near = min(glass + CLEAR, math.sqrt(sum(v * v for v in points[-1])), math.sqrt(sum(v * v for v in p)))
        if _passes(points[-1], p) < near - 1e-9:
            return None
        ways.append(here)
        points.append(p)
    return [points[-1]] + points


def flight(seed, hops, way, face, glass, bumps=1):
    """One moth's round about a globe of radius `glass`, as points about the globe's middle:
    hops + 2 of them. The first is where it sits, the second where it has crept to when it takes
    off, the last is the first again; `bumps` of the points between are at the glass. `way` 1 or
    -1: which way round it flies; `face`: the side of the globe it sits on, in degrees from east
    towards south. The same seed gives the same flight."""
    rng = random.Random(seed)
    for _ in range(2000):
        points = _tries(rng, hops, way, face, glass, bumps)
        if points is not None:
            return points
    raise ValueError(f"seed {seed}: no flight of {hops} hops found that keeps out of the globe")


def _eye(view):
    S = smoke._package("common", "skeleton")
    return getattr(S, view, {}).get("pos") if S is not None else None


def moth_lamps(canvas, origin=(0, 0, 0)):
    """The lamps of MOTH_LAMPS that stand on the canvas: (the middle of the globe in scene
    coordinates, its radius, the side the view sees in degrees from east towards south, moths)."""
    lamps = smoke._package("props", "lamps")
    globe = getattr(lamps, "GLOBES", {}).get("street") if lamps is not None else None
    if not globe:
        return []
    name = lamps.PREFIX + "street"
    out = []
    for foot, view, moths in MOTH_LAMPS:
        here = tuple(foot[i] + origin[i] for i in range(3))
        stands = False
        for x, y, z, nbt in getattr(canvas, "entities", ()):
            try:
                model = nbt["item"]["components"]["minecraft:item_model"]
            except (KeyError, TypeError):
                continue
            if model.split(":", 1)[-1] == name and math.dist((x, y, z), here) <= LAMP_NEAR:
                stands = True
                break
        if not stands:
            continue
        middle = tuple(foot[i] + globe["at"][i] for i in range(3))
        eye = _eye(view)
        face = math.degrees(math.atan2(eye[2] - middle[2], eye[0] - middle[0])) if eye else 0.0
        out.append((middle, float(globe["radius"]), face, moths))
    return out


def moths(canvas, origin=(0, 0, 0)):
    """Register the moths. Returns their number."""
    n = 0
    for i, (middle, glass, face, count) in enumerate(moth_lamps(canvas, origin)):
        for j, (hops, way, bumps) in enumerate(MOTHS[:count]):
            rest = ROUND - hops * HOP
            if rest < HOP:
                raise ValueError(f"a flight of {hops} hops leaves a moth no time to sit in a round of {ROUND}")
            points = [tuple(middle[a] + p[a] for a in range(3)) for p in flight(1000 * (i + 1) + j, hops, way, face, glass, bumps)]
            tick = i * STEP + j * HALF
            for k in range(hops + 1):
                ticks = rest if k == 0 else HOP
                MK.run(canvas, {"": points[k], "to": points[k + 1]},
                       "particle minecraft:" + MOTH + "{target:[{to.x}d,{to.y}d,{to.z}d],color:" + str(MOTH_COLOUR)
                       + ",duration:" + str(ticks) + "} {x} {y} {z} 0 0 0 0 1 " + VIEWERS,
                       ROUND, at=(tick % ROUND,), origin=origin)
                tick += ticks
            n += 1
    return n


def build(canvas, origin=(0, 0, 0)):
    door_steam(canvas, origin)
    moths(canvas, origin)
    return 0
