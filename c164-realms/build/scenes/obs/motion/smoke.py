"""motion/smoke: what the place breathes out (plan/packages/motion/smoke.md; plan/parts/motion.md 9).

The power house's chimney smokes: the one sign in the whole picture that somebody is on watch
tonight. Inside, the safety valve of the boiler that has just been fired lifts every few seconds
and the engine's steam flange leaks a little; a spark leaves the fire door that stands ajar now
and then; the dynamo's brushes and the open knife switch flash. Each is registered only where its
chimney or its machine stands on the canvas.

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

The safety valve
    where    the top of the last boiler's valve (machines/boiler.SAFETY_VALVES[-1]: No. 2, the
             one that has just been fired), when that boiler stands on the canvas. No. 1 is
             banked and does not blow.
    what     cloud, the game's white puff: a quad of 0.4 to 0.75 blocks that lives one to three
             seconds, loses a twenty-fifth of its speed every tick and so comes to rest 25 times
             its first tick's way off. It does not collide. (The game draws one down to the feet
             of a player within two blocks of it; the valve is four blocks over the floor.)
    how      STEAM_PUFFS wisps to a blow (the card's "size of the puff"), STEAM_STEP ticks
             apart, each slower than the one before: the valve lifts with a spurt and settles.
             They rise one to two blocks and lean with the wind as the smoke does (the room has
             the same wind: plan/parts/motion.md 9).
    when     the hiss is motion/sound's, and the two are on one chain: every VALVE["cycle"]
             ticks, from tick VALVE["at"], for VALVE["blow"] ticks. The numbers are sound.VALVE's
             when that module is in the tree (agreed with c361, 11-16); the ones here are the
             same, for a tree without it.

The rest of the room rides on one slow chain of BREATH ticks, the length of the valve's cycle, so
that nothing in it comes round sooner than every eight seconds.

The steam flange   one wisp of the same cloud in a BREATH from the rim of the engine's steam
             flange (machines/engine.STEAM_IN), slow: it rises half a block.
The fire door   small_flame, the game's small flame: a bright quad of 0.1 to 0.2 blocks that
             lives half a second to two, slows as the cloud does, shrinks to half and does not
             collide. Seven in a BREATH, one at a time, from the gap of the door that stands ajar
             (machines/boiler.FIRE_DOORS[-1]): out, up and away, half a block to a block.
The brushes and the open switch   electric_spark, which lives two or three ticks: a flicker.
             Two to the flash, scattered a few hundredths of a block; six flashes in a BREATH
             where the dynamo's two brushes touch the commutator, two at the jaws of the switch
             that stands open (machines/board.OPEN_SWITCH). Bright particles: never more than
             two of them in a tick at one place.
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

STEAM_PARTICLE = "cloud"
VALVE = dict(cycle=160, at=80, blow=30)     # ticks: motion/sound's VALVE says the same, and is read first
STEAM_PUFFS = 3                 # wisps to a blow
STEAM_STEP = 8                  # ticks from one wisp to the next
# The wisps of a blow, in turn: blocks a tick it leaves the valve with, its lean with the wind and
# its drift across it in degrees.
STEAM = ((0.09, 10.0, -4.0), (0.075, 7.0, 5.0), (0.06, 13.0, 0.0))
STEAM_ABOVE = 0.05              # blocks over the valve's top a wisp starts
NEAR = 4.0                      # blocks: a machine stands at a spot when one of its pieces is this near it

BREATH = 160                    # ticks: the chain the rest of the room rides on
# The leak of the engine's steam flange: (east, up, south) of engine.STEAM_IN where the wisp starts
# (the rim on the door's side: the pipe stands on the middle), then per wisp the tick of the
# BREATH, blocks a tick, the lean and the drift in degrees.
LEAK_AT = (0.0, 0.03, -0.18)
LEAK = ((20, 0.035, 10.0, 3.0),)

SPARK_PARTICLE = "small_flame"
# The leaf of the last boiler's fire door hangs on the south jamb and stands a third open: the gap
# between its free edge and the frame looks north-west, at whoever comes in by the wicket. A spark
# starts in that gap, (east, up, south) of boiler.FIRE_DOORS[-1].
FIRE_GAP = (-0.05, 0.0, -0.30)
# The sparks of a BREATH: the tick, the way it leaves by (east, up, south), blocks a tick along
# that way's upright. Out of the door is west; two of them come as a pair, a tick apart.
SPARKS = (
    (12, (-0.6, 1.0, -0.6), 0.040),
    (13, (-1.6, 1.0, -0.4), 0.022),
    (47, (-0.5, 1.0, -0.8), 0.045),
    (71, (-1.3, 1.0, -0.7), 0.030),
    (109, (-0.4, 1.0, -0.6), 0.040),
    (110, (-1.0, 1.0, -0.1), 0.035),
    (139, (-1.0, 1.0, -1.3), 0.027),
)

FLASH_PARTICLE = "electric_spark"
FLASH = 2                       # sparks to a flash
FLASH_SPEED = 0.2               # the game quarters it: a spark strays 0.05 blocks a tick or so
BRUSH_R = 0.25                  # the commutator's radius, where a brush touches it (machines/engine draws it so)
# The flashes of a BREATH at the brushes: the tick and the brush (1 the upper, -1 the lower). They
# fall on ticks the chain runs on anyway (the leak's, the sparks', the valve's): what happens at
# the same moment ten blocks apart is not seen to, and a tick of its own costs the loop a command.
BRUSH_FLASHES = ((20, 1), (71, -1), (88, 1), (109, -1), (110, -1), (139, 1))
BRUSH_SCATTER = (0.03, 0.01, 0.06)          # blocks: along the commutator more than across it
SWITCH_FLASHES = (13, 110)                  # ... and at the jaws of the open switch
SWITCH_SCATTER = (0.01, 0.03, 0.02)


def _package(line, name):
    """The package `name` of a line of the scene, or None while it is not in the tree."""
    full = f"scenes.obs.{line}.{name}"
    try:
        return importlib.import_module(full)
    except ModuleNotFoundError as e:
        if e.name and (full == e.name or full.startswith(e.name + ".")):
            return None
        raise


def _stands(canvas, prefix, spot, origin=(0, 0, 0)):
    """Does a piece of the machine whose models are named `prefix`... stand on the canvas within
    NEAR blocks of `spot` (scene coordinates, plus origin)?"""
    if not prefix:
        return False
    here = tuple(spot[i] + origin[i] for i in range(3))
    for x, y, z, nbt in getattr(canvas, "entities", ()):
        try:
            model = nbt["item"]["components"]["minecraft:item_model"]
        except (KeyError, TypeError):
            continue
        if model.split(":", 1)[-1].startswith(prefix) and math.dist((x, y, z), here) <= NEAR:
            return True
    return False


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
    house = _package("site", "powerhouse")
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


def valve_beat():
    """(cycle, at, blow) of the safety valve in ticks: motion/sound's VALVE when that module is in
    the tree and has one, VALVE here otherwise."""
    beat = dict(VALVE)
    sound = _package("motion", "sound")
    theirs = getattr(sound, "VALVE", None)
    if isinstance(theirs, dict):
        beat.update({k: theirs[k] for k in beat if k in theirs})
    cycle, at, blow = (int(beat[k]) for k in ("cycle", "at", "blow"))
    if cycle < 1 or not 0 <= at < cycle or blow < 0:
        raise ValueError(f"the safety valve's beat {beat} is no beat: at lies in the cycle, blow is 0 or more")
    return cycle, at, blow


def blowing_valve(canvas, origin=(0, 0, 0)):
    """The top of the safety valve that blows, in scene coordinates, or None when its boiler does
    not stand on the canvas."""
    boiler = _package("machines", "boiler")
    valves = getattr(boiler, "SAFETY_VALVES", None)
    if not valves or not _stands(canvas, getattr(boiler, "PREFIX", ""), valves[-1], origin):
        return None
    return tuple(float(v) for v in valves[-1])


def safety_valve(canvas, origin=(0, 0, 0), puffs=None):
    """Register the steam of the safety valve. Returns the number of wisps in a blow, 0 without
    the boiler."""
    top = blowing_valve(canvas, origin)
    if top is None:
        return 0
    cycle, at, blow = valve_beat()
    n = max(1, min(STEAM_PUFFS if puffs is None else int(puffs), len(STEAM), blow // STEAM_STEP + 1))
    for k in range(n):
        speed, lean, drift = STEAM[k]
        MK.puff(canvas, (top[0], top[1] + STEAM_ABOVE, top[2]), STEAM_PARTICLE, cycle,
                at=((at + k * STEAM_STEP) % cycle,), count=0, spread=way(lean, drift), speed=speed, origin=origin)
    return n


def steam_flange(canvas, origin=(0, 0, 0)):
    """The engine's steam flange in scene coordinates, or None when the engine does not stand on
    the canvas."""
    engine = _package("machines", "engine")
    spot = getattr(engine, "STEAM_IN", None)
    if not spot or not _stands(canvas, getattr(engine, "PREFIX", ""), spot, origin):
        return None
    return tuple(float(v) for v in spot)


def leak(canvas, origin=(0, 0, 0)):
    """Register the leak of the engine's steam flange. Returns the number of wisps in a BREATH."""
    flange = steam_flange(canvas, origin)
    if flange is None:
        return 0
    start = tuple(flange[i] + LEAK_AT[i] for i in range(3))
    for tick, speed, lean, drift in LEAK:
        MK.puff(canvas, start, STEAM_PARTICLE, BREATH, at=(tick,), count=0, spread=way(lean, drift), speed=speed,
                origin=origin)
    return len(LEAK)


def open_fire_door(canvas, origin=(0, 0, 0)):
    """The middle of the fire door that stands ajar, in scene coordinates, or None when its boiler
    does not stand on the canvas."""
    boiler = _package("machines", "boiler")
    doors = getattr(boiler, "FIRE_DOORS", None)
    if not doors or not _stands(canvas, getattr(boiler, "PREFIX", ""), doors[-1], origin):
        return None
    return tuple(float(v) for v in doors[-1])


def sparks(canvas, origin=(0, 0, 0)):
    """Register the sparks of the fire door that stands ajar. Returns their number in a BREATH."""
    door = open_fire_door(canvas, origin)
    if door is None:
        return 0
    start = tuple(door[i] + FIRE_GAP[i] for i in range(3))
    for tick, out, speed in SPARKS:
        MK.puff(canvas, start, SPARK_PARTICLE, BREATH, at=(tick,), count=0, spread=out, speed=speed, origin=origin)
    return len(SPARKS)


def brush_tips(canvas, origin=(0, 0, 0)):
    """Where the dynamo's two brushes touch the commutator, the upper first, in scene coordinates;
    None when the engine and its dynamo do not stand on the canvas."""
    engine = _package("machines", "engine")
    try:
        x = engine.SHAFT_X + engine.DYN_X
        y = engine.FLOOR + engine.DYN_H
        z = engine.LINE_Z + (engine.COMM[0] + engine.COMM[1]) / 2.0
    except AttributeError:
        return None
    if not _stands(canvas, getattr(engine, "PREFIX", ""), (x, y, z), origin):
        return None
    return (x, y + BRUSH_R, z), (x, y - BRUSH_R, z)


def open_switch(canvas, origin=(0, 0, 0)):
    """The jaws of the knife switch that stands open, in scene coordinates, or None when the
    switchboard does not stand on the canvas."""
    board = _package("machines", "board")
    spot = getattr(board, "OPEN_SWITCH", None)
    if not spot or not _stands(canvas, getattr(board, "PREFIX", ""), spot, origin):
        return None
    return tuple(float(v) for v in spot)


def flashes(canvas, origin=(0, 0, 0)):
    """Register the flashes at the dynamo's brushes and at the open switch. Returns their number in
    a BREATH."""
    n = 0
    tips = brush_tips(canvas, origin)
    if tips is not None:
        for tick, brush in BRUSH_FLASHES:
            MK.puff(canvas, tips[0 if brush > 0 else 1], FLASH_PARTICLE, BREATH, at=(tick,), count=FLASH,
                    spread=BRUSH_SCATTER, speed=FLASH_SPEED, origin=origin)
        n += len(BRUSH_FLASHES)
    jaws = open_switch(canvas, origin)
    if jaws is not None:
        MK.puff(canvas, jaws, FLASH_PARTICLE, BREATH, at=SWITCH_FLASHES, count=FLASH, spread=SWITCH_SCATTER,
                speed=FLASH_SPEED, origin=origin)
        n += len(SWITCH_FLASHES)
    return n


def build(canvas, origin=(0, 0, 0)):
    chimney(canvas, origin)
    safety_valve(canvas, origin)
    leak(canvas, origin)
    sparks(canvas, origin)
    flashes(canvas, origin)
    return 0
