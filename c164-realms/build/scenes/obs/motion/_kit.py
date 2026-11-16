"""What moves, and the loop that moves it (plan/parts/motion.md, card motion/loop).

A package that places a display entity which turns, swings or slides says so in one line, right
after the line that places it:

    from scenes.obs.motion import _kit as MK

    canvas.add_entity(x, y, z, M.display(wheel, yaw=90.0, scale=2.0))
    MK.spin(canvas, "x", MK.ENGINE_REV)

The registration stays on the canvas. The drivers (build/place.py, tools/check.py) call write()
after the export, and this module alone writes the data-pack functions that move what is registered.

How a part moves. The client interpolates a display entity's transformation: the data pack gives
the next pose and how long to head for it, the client fills in the frames. A turn is interpolated
along the arc, a shift along a straight line, so

  - the entity stands on the axis: the model's anchor is on it;
  - a part whose model is centred on the axis may turn a quarter of a turn in one step;
  - a part that is not gets smaller steps, small enough that the straight shift stays within
    WOBBLE of the arc; a part too fast for that is refused, with the reason.

The pose a part is placed in is its rest pose and the start of its loop. With the loop stopped, or
with no data pack at all, every part stands as its maker placed it.

Timing. No function runs every tick. Parts of the same period share a chain of scheduled functions,
one function for every tick on which something is due, and each function schedules the next. Poses
are absolute, so a part that missed a step (its chunk was not loaded) is right again at the next.
The loop counts game ticks, not the time of day, and what is queued is saved with the world.

Per scene the data pack gets  <namespace>:<scene>-motion/  with
    start   stop every chain of the scene, put the parts in their rest poses, start the chains;
            from then on this scene's loop is the one that runs in the world
    stop    stop the chains and put the parts in their rest poses
    load    (in #minecraft:load) restarts a loop that should be running and is not
and the chains  c<period>/<n>. One loop runs in a world at a time: a chain of another scene ends
itself at the start of its next cycle, so two scenes placed on the same spot one after the other
do not both pull at the same entities.

What is not a part: a command of a package's own on some ticks of a cycle (run), and functions of
a package's own under a name of their own, <namespace>:<folder>/<name> (function): the guide's
walk-up checks and what they set off (card motion/guide). They are registered like a sound or a
puff and written by write() with the loop, so that the data pack still holds nothing that this
module did not write.

What the client does with a pose was read off the game's classes (26.3, world/entity/Display and
com/mojang/math/Transformation): every merge that changes the entity starts the way anew, from
what the client shows at that moment to the pose the entity now has; the two turns go along their
arcs the short way round, shift and scale along straight lines; a way of 0 ticks is a jump. A
merge that changes something else and leaves the pose alone starts the way anew all the same, so
the part is seen to go the last stretch once more: nothing but this module should merge into an
entity that is registered here, and no step repeats the pose of the step before it.

_kit_test.py plays the written functions back on that understanding. The real machine has borne
it out for the parts (plan/parts/motion.md section 10: the loop over a reload, a restart of the
server, a chunk unloaded and back, another scene's start; section 7: what a command costs).
"""
import json
import math
import os
import re
import shutil
import zlib

from ..common import skeleton as S

NS = "c164"                     # the namespace of the models and of our sound events
OBJECTIVE = "c164m"             # the one scoreboard objective: whose loop runs, each scene's heartbeat
RUN = "#run"                    # its holder of the running scene's number
DISPLAYS = ("minecraft:item_display", "minecraft:block_display", "minecraft:text_display")

# ---- the beat of the place (ticks; 20 ticks are one second) -------------------------------------
# One second is the beat: the master clock's pendulum swings once a second, the animated panels of
# materials/panels change once a second, and every other period is a simple ratio of it. First
# guesses, to be tuned on the real machine; packages name these, so a tuning is one line here.
SECOND = 20
PENDULUM = 40                   # a pendulum there and back: one swing a second
ENGINE_REV = 48                 # flywheel and crank of the steam engine: 25 turns a minute
GOVERNOR_REV = 24               # the engine's governor: twice the shaft
DYNAMO_REV = 16                 # the dynamo's armature: belted 1 to 3
SCOPE_GOVERNOR_REV = 32         # the governor of the telescope's driving clock
DRUM_REV = 2400                 # a recording drum: two minutes
# the beat board's arms (obs_mot_loop) and the self-test's. The orrery itself turns by its own gear
# ratios: machines/orrery.py's PERIOD
ORRERY = {"mercury": 1200, "venus": 1920, "earth": 2640, "mars": 3120, "jupiter": 7200, "saturn": 10800}
BLINK = (30, 30)                # a lamp that blinks: ticks lit, ticks dark (no part blinks in this version)
FLAG_SWAY = 120                 # a flag there and back
ANEMOMETER_REV = 24             # the wind cups

# ---- the wind -----------------------------------------------------------------------------------
# One wind for the whole place, from the north (the director, group message 39156): vanes point
# their tails south, flags fly south, smoke and steam lean south. The skeleton's WIND is one block
# of its way; a tree whose skeleton does not have it yet gets the same wind.
WIND = tuple(float(v) for v in getattr(S, "WIND", (0, 0, 1)))
WIND_LEAN = 10.0                # degrees a puff that rises leans with it

# ---- limits -------------------------------------------------------------------------------------
WOBBLE = 1.0 / 64.0             # blocks a model's middle may stray from its arc: a quarter pixel
WOBBLE_MOST = 1.0 / 32.0        # what a fast part is let off with when it cannot keep to WOBBLE
MIN_STEP = 3                    # ticks; a part that needs shorter steps is too fast to be driven so
MAX_STEP = 200                  # ticks; a player who arrives sees a part stand still until its next step
LEAD = 2                        # ticks a step is aimed beyond the next one, so a late step is not a halt
MAX_TURN = 150.0                # degrees one step may aim through; at 180 the short way round is the wrong way
PEAK = 120                      # commands in any one tick (round 2, plan/round2.md section 2; 40 before)
MEAN = 40.0                     # commands a tick on average (10 before)
FILES = 3000                    # function files of one scene
EVENTS = 720                    # functions of one chain

NEAR = 0.05                     # blocks: the selector's reach round the spot an entity stands on
APART = 0.1                     # two parts of one name stand at least this far apart
STAGGER = 20                    # ticks the chains may be started apart
HORIZON = 2400                  # ticks the busiest tick is looked for in
GRACE = 20                      # ticks load waits beyond one cycle before it calls a loop dead

_TIERS = ((LEAD, WOBBLE), (LEAD, WOBBLE_MOST), (0, WOBBLE), (0, WOBBLE_MOST))
_NAME = re.compile(r"[A-Za-z0-9_.+\-]+\Z")
_OWN = re.compile(r"[a-z0-9_.\-]+(/[a-z0-9_.\-]+)+\Z")      # a function of a package's own: folder/name
_SPOT = re.compile(r"\{(?:([a-z][a-z0-9_]*)\.)?([xyz])\}")   # {x}, {door.x}: a place in a command's text
_CALLS = re.compile(r"\b(?:function|clear) ([a-z0-9_.\-]+):([a-z0-9_.\-/]+)")
_SCENES = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
_IDENT = (0.0, 0.0, 0.0, 1.0)


# ---- rotations (quaternions are (x, y, z, w), as the game writes them) ---------------------------
def _qmul(a, b):
    """The turn b followed by the turn a."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def _qrot(q, v):
    x, y, z, w = q
    p = _qmul(_qmul(q, (v[0], v[1], v[2], 0.0)), (-x, -y, -z, w))
    return (p[0], p[1], p[2])


def _about(axis, degrees):
    h = math.radians(degrees) / 2.0
    s = math.sin(h)
    return (axis[0] * s, axis[1] * s, axis[2] * s, math.cos(h))


def _unit(v):
    v = tuple(float(c) for c in v)
    if len(v) != 3:
        raise ValueError(f"a direction has three numbers, not {len(v)}")
    n = math.sqrt(sum(c * c for c in v))
    if n < 1e-9:
        raise ValueError("a direction of no length")
    return tuple(c / n for c in v)


def _stray(arm, turn, share):
    """How far, in blocks, the middle of a model strays from its arc.

    arm    blocks from the axis to the middle of the model's box
    turn   degrees the part turns from one step to the next
    share  step / (step + lead): how much of the way to the pose it is aimed at the part has gone
           when the next step takes over

    The turn is interpolated along the arc and the shift along the chord. Aimed beyond the next
    step, the part leaves the chord early, a little off the arc, and starts the next chord from
    there; that settles at the chord's error at the hand-over divided by the share.
    """
    if arm <= 0.0 or turn == 0.0:
        return 0.0
    aim = math.radians(abs(turn)) / share

    def off(u):
        return math.hypot((1.0 - u) + u * math.cos(aim) - math.cos(u * aim), u * math.sin(aim) - math.sin(u * aim))

    worst = off(0.5) if share >= 0.5 else off(share)
    return arm * (worst + (off(share) / share if share < 1.0 else 0.0))


# ---- text ---------------------------------------------------------------------------------------
def _num(v, places=4):
    """A number as a command takes it. Always with a decimal point: a whole x or z in a position
    would be moved to the middle of the block."""
    s = f"{float(v):.{places}f}".rstrip("0")
    if s.endswith("."):
        s += "0"
    return "0.0" if s == "-0.0" else s


def _floats(v):
    return "[" + ",".join(_num(c, 6) + "f" for c in v) + "]"


def _four(v):
    v = tuple(float(c) for c in v)
    if len(v) != 4:
        raise ValueError(f"a rotation has four numbers, not {len(v)}")
    return v


# ---- what is registered --------------------------------------------------------------------------
class _Book:
    """A canvas's registrations. It hangs on the canvas as canvas.motion."""

    def __init__(self):
        self.parts = []
        self.points = []
        self.own = {}           # name -> (lines, places): the packages' own functions
        self.peak = PEAK
        self.mean = MEAN


def _book(canvas):
    book = getattr(canvas, "motion", None)
    if book is None:
        book = canvas.motion = _Book()
    return book


def _model_name(nbt):
    ref = ((nbt.get("item") or {}).get("components") or {}).get("minecraft:item_model")
    return None if ref is None else ref.split(":", 1)[-1]


class _Part:
    """One registered display entity: where it stands, its rest pose, and the steps of its loop."""

    def __init__(self, entity, name, kind, cycle, phase):
        x, y, z, nbt = entity
        self.entity, self.name, self.kind = entity, name, kind
        self.pos = (float(x), float(y), float(z))
        self.type = nbt["id"]
        self.cycle = cycle
        self.phase = int(phase) % cycle
        tr = nbt.get("transformation") or {}
        if not isinstance(tr, dict):
            raise ValueError(f"{name}: its transformation is a matrix; give rotations, scale and translation")
        self.left = _four(tr.get("left_rotation", _IDENT))
        self.right = _four(tr.get("right_rotation", _IDENT))
        self.scale = tuple(float(v) for v in tr.get("scale", (1.0, 1.0, 1.0)))
        self.shift = tuple(float(v) for v in tr.get("translation", (0.0, 0.0, 0.0)))
        rot = nbt.get("Rotation") or (0.0, 0.0)
        self.yaw, self.pitch = float(rot[0]), float(rot[1])
        self.axis = (0.0, 1.0, 0.0)     # what it turns about, in the entity's own frame
        self.way = (0.0, 0.0, 0.0)      # the way it slides, in the same frame
        self.steps = []                 # (tick, ticks to get there, degrees turned, blocks slid)
        self.swaps = []                 # (tick, model name): a lamp that blinks
        self.lead = 0
        self.turn = 0.0                 # the widest turn a step aims through, degrees
        self.stray = 0.0                # the furthest the model's middle leaves its arc, blocks
        self.forced = False             # the maker set the steps or the lead by hand
        self.in_step = None             # the cycle of the chain its own chain keeps in step with (turn())

    def local(self, spec):
        """A direction in the entity's own frame, the frame its transformation is given in.

        "x", "-y", ...  the model's own axis as the part lies now
        (dx, dy, dz)    a direction in the world (x east, y up, z south)
        """
        if isinstance(spec, str):
            s = spec.strip()
            sign = -1.0 if s.startswith("-") else 1.0
            s = s.lstrip("+-")
            if s not in ("x", "y", "z"):
                raise ValueError(f"{self.name}: an axis is \"x\", \"-x\", \"y\", ... or a direction (dx, dy, dz), "
                                 f"not {spec!r}")
            u = [0.0, 0.0, 0.0]
            u["xyz".index(s)] = sign
            if self.type == "minecraft:item_display":
                # the item renderer shows a model turned half a turn about y (artkit.models.display)
                u = [-u[0], u[1], -u[2]]
            return _unit(_qrot(self.left, u))
        if abs(self.pitch) > 1e-6:
            raise ValueError(f"{self.name}: the entity is pitched; give the axis as the model's own (\"x\", ...)")
        w = _unit(spec)
        a = math.radians(self.yaw)
        c, s = math.cos(a), math.sin(a)
        return (w[0] * c + w[2] * s, w[1], -w[0] * s + w[2] * c)

    def arm(self):
        """Blocks from the axis to the middle of the model's box: what wobbles when the part turns."""
        along = sum(self.shift[i] * self.axis[i] for i in range(3))
        return math.sqrt(sum((self.shift[i] - along * self.axis[i]) ** 2 for i in range(3)))

    def pose(self, turn, slide):
        """(left rotation, translation) of the part turned `turn` degrees about its axis from the
        rest pose and slid `slide` blocks along its way. The anchor stays on the entity (and goes
        with the slide); scale and right rotation are the rest pose's."""
        q = _about(self.axis, turn)
        t = _qrot(q, self.shift)
        return _qmul(q, self.left), tuple(t[i] + slide * self.way[i] for i in range(3))


class _Point:
    """A spot where a command is run on some ticks of a cycle: a sound, a puff of particles."""

    def __init__(self, kind, what, pos, cycle, ticks, phase, text, *, spots=None, weight=1):
        self.kind, self.what, self.pos = kind, what, tuple(float(v) for v in pos)
        self.cycle, self.ticks, self.phase, self.text = cycle, ticks, int(phase) % cycle, text
        self.spots = {"": self.pos} if spots is None else spots     # the places its text names
        self.weight = int(weight)                                   # commands it counts as


def _pick(canvas, entity, model):
    if entity is not None:
        for e in canvas.entities:
            if e is entity:
                return e
        raise ValueError("entity= is not one of canvas.entities")
    if model is not None:
        for e in reversed(canvas.entities):
            if _model_name(e[3]) == model:
                return e
        raise ValueError(f"no display entity on the canvas shows the model {model!r}")
    if not canvas.entities:
        raise ValueError("nothing has been placed on the canvas yet")
    return canvas.entities[-1]


def _register(canvas, kind, cycle, entity, model, name, phase):
    cycle = int(cycle)
    if cycle < 1:
        raise ValueError(f"a cycle of {cycle} ticks")
    e = _pick(canvas, entity, model)
    nbt = e[3]
    if nbt.get("id") not in DISPLAYS:
        raise ValueError(f"only display entities are moved, not {nbt.get('id')!r}")
    book = _book(canvas)
    for p in book.parts:
        if p.entity is e:
            raise ValueError(f"{p.name}: this display entity is registered already ({p.kind})")
    name = name or _model_name(nbt)
    if not name:
        raise ValueError("the entity shows no model to name it after: give name=")
    if not _NAME.match(name):
        raise ValueError(f"{name!r}: a name is made of letters, digits and _ . + -")
    return _Part(e, name, kind, cycle, phase)


def _enrol(canvas, part):
    """The part's loop is worked out: tag its entity and keep it. Returns 0, the verbs' result."""
    tags = part.entity[3].setdefault("Tags", [])
    if "m." + part.name not in tags:
        tags.append("m." + part.name)
    _book(canvas).parts.append(part)
    return 0


def _ticks(cycle, n):
    """n + 1 ticks from 0 to the cycle, as even as whole ticks allow."""
    return [(k * cycle + n // 2) // n for k in range(n + 1)]


def _strain(part, keys, lead):
    """The widest turn a step aims through (degrees) and the furthest the model's middle strays
    from its arc (blocks) when the part is driven through these poses with this lead."""
    arm, turn, stray = part.arm(), 0.0, 0.0
    for (t0, a0, _s0), (t1, a1, _s1) in zip(keys, keys[1:]):
        share = (t1 - t0) / float(t1 - t0 + lead)
        turn = max(turn, abs(a1 - a0) / share)
        stray = max(stray, _stray(arm, a1 - a0, share))
    return turn, stray


def _settle(part, keys, lead, forced):
    """Give the part its steps. keys are the poses it passes through, (tick, degrees, blocks), from
    tick 0 to the end of the cycle, where it is in its first pose again. Each step is aimed `lead`
    ticks beyond the next pose, so that the part passes through that pose still moving; the lead
    is dropped when it would take the model's middle off its arc."""
    forced = forced or lead is not None
    for (t0, _a0, _s0), (t1, _a1, _s1) in zip(keys, keys[1:]):
        if t1 - t0 < (1 if forced else MIN_STEP):
            raise ValueError(f"{part.name}: a step of {t1 - t0} ticks; the shortest is {MIN_STEP}. Fewer steps, "
                             f"or a longer period")
        if t1 - t0 > MAX_STEP:
            raise ValueError(f"{part.name}: a step of {t1 - t0} ticks; the longest is {MAX_STEP}. More steps")
    tiers = _TIERS if lead is None else ((lead, None),)
    for ld, limit in tiers:
        turn, stray = _strain(part, keys, ld)
        if turn > (179.0 if forced else MAX_TURN) + 1e-6:
            continue
        if limit is not None and not forced and stray > limit + 1e-9:
            continue
        part.lead, part.turn, part.stray, part.forced = ld, turn, stray, forced
        part.steps = []
        for (t0, a0, s0), (t1, a1, s1) in zip(keys, keys[1:]):
            k = (t1 - t0 + ld) / float(t1 - t0)
            part.steps.append((t0, t1 - t0 + ld, a0 + (a1 - a0) * k, s0 + (s1 - s0) * k))
        return
    turn, stray = _strain(part, keys, lead or 0)
    if turn > (179.0 if forced else MAX_TURN) + 1e-6:
        raise ValueError(f"{part.name}: a step would turn it {turn:.0f} degrees at once, and the client takes "
                         f"the short way round. Give it more steps")
    raise ValueError(f"{part.name}: the middle of its model lies {part.arm():.2f} blocks off the axis and would "
                     f"stray {stray * 16.0:.2f} pixels from its arc (a step turns up to {turn:.0f} degrees). "
                     f"Centre the model on the axis, give it more steps, or let it move slower")


def _spin_keys(part, cycle, lead):
    """How many steps one turn is cut into: as few as keep every step under MAX_TURN and MAX_STEP
    and the model's middle on its arc; a divisor of the period if one is near, so the steps are
    equal and fall on the ticks the other parts of the chain use."""
    if cycle < 4 * MIN_STEP:
        raise ValueError(f"{part.name}: one turn in {cycle} ticks; the quickest is {4 * MIN_STEP} "
                         f"(4 steps of {MIN_STEP} ticks)")
    arm = part.arm()
    least = max(4, -(-cycle // MAX_STEP))
    most = cycle // MIN_STEP
    tiers = _TIERS if lead is None else ((lead, WOBBLE), (lead, WOBBLE_MOST))
    for ld, limit in tiers:
        need = None
        for n in range(least, most + 1):
            short, long = cycle // n, -(-cycle // n)
            share = short / float(short + ld)
            turn = 360.0 * long / cycle
            if turn / share > MAX_TURN or _stray(arm, turn, share) > limit:
                continue
            if need is None:
                need = n
            if cycle % n == 0:
                return n
            if n >= 2 * need:
                break
        if need is not None:
            return need
    raise ValueError(f"{part.name}: one turn in {cycle} ticks is too fast for a model whose middle lies "
                     f"{arm:.2f} blocks off its axis. Centre the model on the axis (a wheel, a disc), or "
                     f"let it turn slower")


# ---- the verbs ----------------------------------------------------------------------------------
def spin(canvas, axis, period, *, entity=None, model=None, name=None, phase=0, keys=None, lead=None):
    """The part turns about `axis` for ever, once in `period` ticks.

    axis     "x", "-y", ... the model's own axis, or a direction in the world (dx, dy, dz). The
             turn is right-handed: counter-clockwise seen from the tip of the axis. A negative
             period turns the other way.
    entity   the tuple in canvas.entities; model= picks the last one placed that shows that model;
             neither: the one placed last
    name     the part's tag is "m." + name; by default the model's name. Two parts on one spot
             need different names
    phase    ticks the part is behind, to put two alike out of step: half the period for the
             second of two pendulums. start() puts every part in the pose it was placed in, so a
             part with a phase needs up to a cycle to fall into step, and a wheel may begin with
             a turn the wrong way; a part that only turns is better placed turned than given a phase
    keys, lead   the number of steps in a turn and the lead, set by hand: for test scenes that
             show what a coarse step looks like. The limits on the wobble are not applied then.

    Returns 0, so `n += MK.spin(...)` leaves an entity count alone.
    """
    period = int(period)
    if period == 0:
        raise ValueError("a period of 0 ticks")
    cycle = abs(period)
    part = _register(canvas, "spin", cycle, entity, model, name, phase)
    part.axis = part.local(axis)
    n = int(keys) if keys is not None else _spin_keys(part, cycle, lead)
    if n < 2:
        raise ValueError(f"{part.name}: a turn needs at least 2 steps")
    sign = 1.0 if period > 0 else -1.0
    _settle(part, [(t, sign * 360.0 * t / cycle, 0.0) for t in _ticks(cycle, n)], lead, keys is not None)
    return _enrol(canvas, part)


def swing(canvas, axis, degrees, period, *, keys=8, entity=None, model=None, name=None, phase=0, lead=None):
    """The part swings about `axis`, `degrees` to either side of the pose it was placed in, there
    and back in `period` ticks. It starts in the middle, towards the positive side (a negative
    period: towards the other). keys is the number of poses in one swing there and back: 8 slows
    it down at the ends, 4 is an even to and fro."""
    period = int(period)
    if period == 0:
        raise ValueError("a period of 0 ticks")
    cycle = abs(period)
    part = _register(canvas, "swing", cycle, entity, model, name, phase)
    part.axis = part.local(axis)
    n = max(int(keys), -(-cycle // MAX_STEP))
    amp = float(degrees) * (1.0 if period > 0 else -1.0)
    _settle(part, [(t, amp * math.sin(2.0 * math.pi * t / cycle), 0.0) for t in _ticks(cycle, n)], lead, False)
    return _enrol(canvas, part)


def crank(canvas, axis, along, radius, length, period, *, turn=True, keys=12, entity=None, model=None,
          name=None, phase=0, lead=None, start=0.0):
    """The part is the connecting rod of a crank, or what the rod pushes.

    axis     the shaft, as in spin(); the crank itself is registered with spin() about the same
             axis and with the same period
    along    the way from the shaft to the cylinder (the model's own axis or a world direction),
             square to the shaft
    radius   blocks from the shaft to the crank pin
    length   blocks from the crank pin to the pin of the crosshead
    turn     True: a connecting rod. Its anchor is the crosshead pin; it slides with the crosshead
             and tilts to keep its other end on the crank pin. False: the crosshead, the piston
             rod, the piston: they only slide.

    start    degrees: where the crank pin stands while the part is at rest, measured from `along`
             about the shaft, right-handed (the way spin() turns for a positive period, whatever
             the sign of this period). An eccentric that is a quarter turn ahead of a main crank
             turning with a positive period: start=90. The part is placed as it stands at that
             angle: a rod leaning, its anchor where the crosshead pin is then. `along` named as
             the model's own axis is then the rod's own line, and the lean is taken out of it.

    The rest pose with start=0 is the dead centre with the crank pin towards the cylinder: crank,
    rod and piston rod in one line, the crosshead as far from the shaft as it goes.
    """
    radius, length = float(radius), float(length)
    if not length > radius > 0.0:
        raise ValueError(f"a rod of {length} blocks on a crank of {radius}: the rod has to be the longer")
    period = int(period)
    if period == 0:
        raise ValueError("a period of 0 ticks")
    cycle = abs(period)

    def at(a):
        """(degrees the rod leans, blocks from the shaft to the crosshead pin) with the crank pin at a."""
        reach = radius * math.cos(a) + math.sqrt(length * length - (radius * math.sin(a)) ** 2)
        return (-math.degrees(math.asin(radius * math.sin(a) / length)) if turn else 0.0), reach

    a0 = math.radians(float(start))
    lean, far = at(a0) if a0 else (0.0, radius + length)
    part = _register(canvas, "crank", cycle, entity, model, name, phase)
    part.axis = part.local(axis)
    part.way = part.local(along)
    if isinstance(along, str) and lean:
        part.way = _unit(_qrot(_about(part.axis, -lean), part.way))
    if abs(sum(part.axis[i] * part.way[i] for i in range(3))) > 1e-3:
        raise ValueError(f"{part.name}: the line of the stroke is not square to the shaft")
    n = max(int(keys), -(-cycle // MAX_STEP))
    sign = 1.0 if period > 0 else -1.0
    track = []
    for t in _ticks(cycle, n):
        tilt, reach = at(a0 + sign * 2.0 * math.pi * t / cycle)
        track.append((t, tilt - lean, reach - far))
    _settle(part, track, lead, False)
    return _enrol(canvas, part)


def slide(canvas, axis, moves, cycle, *, entity=None, model=None, name=None, phase=0):
    """The part slides along `axis` and stops, as a list of moves tells it.

    moves    [(tick it sets off, blocks from the rest pose it goes to, ticks it takes), ...] in
             order; between two moves it stands still. The last move ends at 0.0: a loop comes
             back to where it starts.
    cycle    ticks after which the moves repeat

    A move longer than MAX_STEP ticks is cut into steps.
    """
    part = _register(canvas, "slide", cycle, entity, model, name, phase)
    part.way = part.local(axis)
    at, here = 0, 0.0
    for start, offset, travel in moves:
        start, travel, offset = int(start), int(travel), float(offset)
        if start < at:
            raise ValueError(f"{part.name}: the move at tick {start} sets off before the one before it has ended")
        if travel < 1:
            raise ValueError(f"{part.name}: a move takes at least one tick")
        if abs(offset - here) < 1e-6:
            # the same pose given twice makes the client show the way to it once more, from the start
            raise ValueError(f"{part.name}: the move at tick {start} goes nowhere (the part is at {here:g} "
                             f"already); a part stands still between two moves by itself")
        n = -(-travel // MAX_STEP)
        cuts = [start + (k * travel + n // 2) // n for k in range(n + 1)]
        for k in range(n):
            dt = cuts[k + 1] - cuts[k]
            a = here + (offset - here) * (cuts[k] - start) / float(travel)
            b = here + (offset - here) * (cuts[k + 1] - start) / float(travel)
            if k < n - 1:       # more of the move follows: aim beyond, as a turning part does
                part.steps.append((cuts[k], dt + LEAD, 0.0, a + (b - a) * (dt + LEAD) / float(dt)))
            else:
                part.steps.append((cuts[k], dt, 0.0, b))
        at, here = start + travel, offset
    if at > part.cycle:
        raise ValueError(f"{part.name}: the moves end at tick {at}, after the cycle of {part.cycle}")
    if abs(here) > 1e-9:
        raise ValueError(f"{part.name}: the last move has to end at 0.0, where the part was placed")
    part.lead = LEAD
    return _enrol(canvas, part)


def _turn_steps(arm, start, here, to, travel, lead, limit):
    """One move of turn() cut into steps: ([(tick, ticks to get there, degrees)], the widest turn
    a step aims through, the furthest the model's middle strays from its arc), or None when no
    cut keeps within MAX_TURN and `limit`. As few steps as do, as even as whole ticks allow; all
    but the last aim `lead` ticks beyond the next, the last ends on the move's own pose."""
    least = -(-travel // MAX_STEP)
    for n in range(least, max(least, travel // MIN_STEP) + 1):
        cuts = [start + (k * travel + n // 2) // n for k in range(n + 1)]
        kinds = {(cuts[k + 1] - cuts[k], lead if k < n - 1 else 0) for k in range(n)}
        turn_ = max(abs(to - here) * (dt + ahead) / float(travel) for dt, ahead in kinds)
        if turn_ > MAX_TURN + 1e-6:
            continue
        stray = max(_stray(arm, (to - here) * dt / float(travel), dt / float(dt + ahead)) for dt, ahead in kinds)
        if stray > limit + 1e-9:
            continue
        steps = []
        for k in range(n - 1):
            dt = cuts[k + 1] - cuts[k] + lead
            steps.append((cuts[k], dt, here + (to - here) * (cuts[k] - start + dt) / float(travel)))
        steps.append((cuts[n - 1], cuts[n] - cuts[n - 1], to))
        return steps, turn_, stray
    return None


def turn(canvas, axis, moves, cycle, *, entity=None, model=None, name=None, phase=0, in_step=None):
    """The part turns about `axis` and stops, as a list of moves tells it: what slide() is to a
    shift. An escape wheel that jumps half a tooth at every beat, the arm of a signal that drops
    and comes back, a fly that whirls while the clock strikes.

    axis     as in spin(): "x", "-y", ... the model's own axis, or a direction in the world. The
             turn is right-handed: counter-clockwise seen from the tip of the axis
    moves    [(tick it sets off, degrees from the rest pose it turns to, ticks it takes), ...] in
             order. The degrees count on from move to move: more than the move before turns the
             part on (360 and beyond for one that goes round), less turns it back. Between two
             moves it stands still. The last move ends at 0 or at whole turns, the pose the part
             was placed in: a loop comes back to where it starts.
    cycle    ticks after which the moves repeat
    in_step  another cycle of this scene, one that divides `cycle`: the moves' ticks are then ticks
             of that chain too. An escape wheel with a cycle of 1200 and in_step=80 is let go on
             tick 0 and tick 40 of the pendulum's 80. Left out, the chains of two cycles are
             started a few ticks apart (STAGGER), by a difference that stays the same

    A move is cut into steps where it takes longer than MAX_STEP ticks, turns further than
    MAX_TURN degrees, or would take a model whose middle lies off the axis from its arc (WOBBLE,
    as in spin()); the steps of one move run into each other, and its last one ends on the pose
    the move names. A move too fast for that is refused, with the reason.
    """
    part = _register(canvas, "turn", cycle, entity, model, name, phase)
    if in_step is not None:
        if int(in_step) != in_step or in_step < 1 or part.cycle % int(in_step):
            raise ValueError(f"{part.name}: in_step={in_step!r} is not a cycle that divides its own of {part.cycle} ticks")
        if int(in_step) != part.cycle:      # its own cycle: it is on that chain as it is
            part.in_step = int(in_step)
    part.axis = part.local(axis)
    track, at, here = [], 0, 0.0
    for start, to, travel in moves:
        start, travel, to = int(start), int(travel), float(to)
        if start < at:
            raise ValueError(f"{part.name}: the move at tick {start} sets off before the one before it has ended")
        if travel < 1:
            raise ValueError(f"{part.name}: a move takes at least one tick")
        if abs(to - here) < 1e-6:
            # the same pose given twice makes the client show the way to it once more, from the start
            raise ValueError(f"{part.name}: the move at tick {start} goes nowhere (the part is at {here:g} degrees "
                             f"already); a part stands still between two moves by itself")
        track.append((start, here, to, travel))
        at, here = start + travel, to
    if not track:
        raise ValueError(f"{part.name}: moves= names no move")
    if at > part.cycle:
        raise ValueError(f"{part.name}: the moves end at tick {at}, after the cycle of {part.cycle}")
    if abs(here - 360.0 * round(here / 360.0)) > 1e-6:
        raise ValueError(f"{part.name}: the last move has to end at 0 or at whole turns, the pose the part was "
                         f"placed in; it ends at {here:g} degrees")
    arm = part.arm()
    for lead, limit in _TIERS:
        cut = [_turn_steps(arm, start, a0, a1, travel, lead, limit) for start, a0, a1, travel in track]
        if None in cut:
            continue
        part.steps = [(tick, ticks, degrees, 0.0) for steps, _turn, _stray_ in cut for tick, ticks, degrees in steps]
        part.lead = lead
        part.turn = max(turn_ for _steps, turn_, _stray_ in cut)
        part.stray = max(stray for _steps, _turn, stray in cut)
        return _enrol(canvas, part)
    # the last of the tiers is the widest: a move it has no cut for is the one to name
    start, a0, a1, travel = next(move for move in track if _turn_steps(arm, *move, 0, WOBBLE_MOST) is None)
    if _turn_steps(0.0, start, a0, a1, travel, 0, WOBBLE_MOST) is None:
        raise ValueError(f"{part.name}: the move at tick {start} turns it {abs(a1 - a0):g} degrees in {travel} ticks; "
                         f"a step takes {MIN_STEP} ticks or more and turns {MAX_TURN:g} degrees at most. Give the "
                         f"move more ticks")
    raise ValueError(f"{part.name}: the middle of its model lies {arm:.2f} blocks off the axis, and the move at tick "
                     f"{start} ({abs(a1 - a0):g} degrees in {travel} ticks) would take it off its arc. Centre the "
                     f"model on the axis, or give the move more ticks")


def blink(canvas, other, on, off, *, entity=None, model=None, name=None, phase=0):
    """The part shows its own model for `on` ticks, then the model `other` for `off` ticks, and so
    on: a lamp with a lit and a dark model. Only the model changes; an invisible light source
    beside it stays as it is."""
    on, off = int(on), int(off)
    if on < 1 or off < 1:
        raise ValueError("a lamp is lit and dark for at least one tick each")
    part = _register(canvas, "blink", on + off, entity, model, name, phase)
    ref = ((part.entity[3].get("item") or {}).get("components") or {}).get("minecraft:item_model")
    if part.type != "minecraft:item_display" or ref is None:
        raise ValueError(f"{part.name}: only an item display that shows a model can change it")
    ns = ref.split(":", 1)[0] if ":" in ref else NS
    part.swaps = [(0, ref if ":" in ref else f"{ns}:{ref}"), (on, other if ":" in other else f"{ns}:{other}")]
    return _enrol(canvas, part)


def _at(ticks, cycle):
    out = sorted({int(t) for t in ticks})
    if not out:
        raise ValueError("at= names no tick")
    if out[0] < 0 or out[-1] >= cycle:
        raise ValueError(f"at= {out}: ticks of a cycle of {cycle} run from 0 to {cycle - 1}")
    return out


def sound(canvas, pos, event, cycle, at=(0,), *, volume=1.0, pitch=1.0, reach=16.0, source="block",
          origin=(0, 0, 0), phase=0):
    """A sound at `pos` (scene coordinates, plus origin) on the ticks `at` of every `cycle` ticks.

    event    a sound event; without a namespace it is one of ours (assets/c164/sounds.json, which
             points at the game's own sounds: motion/sound.py)
    reach    blocks: only players this near are sent the sound. A sound fades over 16 blocks
             whatever its volume (below 1), so the reach is what keeps a room's sound in the room.

    A sound that goes with a part (the tick of a pendulum) takes the part's period: it is then on
    the part's chain and stays in step with it.
    """
    cycle = int(cycle)
    if cycle < 1:
        raise ValueError(f"a cycle of {cycle} ticks")
    if not 0.5 <= pitch <= 2.0:
        raise ValueError(f"pitch {pitch}: the game plays 0.5 to 2.0")
    if not volume > 0.0 or not reach > 0.0:
        raise ValueError("volume and reach are above 0")
    event = event if ":" in event else f"{NS}:{event}"
    text = (f"playsound {event} {source} @a[x={{x}},y={{y}},z={{z}},distance=..{_num(reach)}] "
            f"{{x}} {{y}} {{z}} {_num(volume)} {_num(pitch)}")
    place = tuple(pos[i] + origin[i] for i in range(3))
    _book(canvas).points.append(_Point("sound", event, place, cycle, _at(at, cycle), phase, text))
    return 0


def downwind(lean=WIND_LEAN, rise=1.0):
    """The way a puff goes that rises and leans with the wind, `lean` degrees off the upright: the
    spread= of a puff of count 0, whose speed= is then how fast it rises (blocks a tick)."""
    if not 0.0 <= lean < 90.0:
        raise ValueError(f"a lean of {lean} degrees")
    level = math.hypot(WIND[0], WIND[2])
    over = math.tan(math.radians(lean)) * rise / level if level > 1e-9 else 0.0
    return (WIND[0] * over, float(rise), WIND[2] * over)


def puff(canvas, pos, particle, cycle, at=(0,), *, count=1, spread=(0.0, 0.0, 0.0), speed=0.0, far=False,
         origin=(0, 0, 0), phase=0):
    """Particles at `pos` (scene coordinates, plus origin) on the ticks `at` of every `cycle` ticks.

    count, spread, speed   as the game's particle command takes them. count 0 sends one particle
             with the velocity spread * speed: a puff that rises, and with spread=downwind() one
             that leans with the wind as it does.
    far      True: seen from afar too (the game's "force"), for the chimney's smoke
    """
    cycle = int(cycle)
    if cycle < 1:
        raise ValueError(f"a cycle of {cycle} ticks")
    if int(count) < 0:
        raise ValueError("count is 0 or more")
    particle = particle if ":" in particle else f"minecraft:{particle}"
    text = (f"particle {particle} {{x}} {{y}} {{z}} {_num(spread[0])} {_num(spread[1])} {_num(spread[2])} "
            f"{_num(speed)} {int(count)} {'force' if far else 'normal'}")
    place = tuple(pos[i] + origin[i] for i in range(3))
    _book(canvas).points.append(_Point("puff", particle, place, cycle, _at(at, cycle), phase, text))
    return 0


def _spots(pos, origin):
    """The places a text may name, {"": (x, y, z)} or {name: (x, y, z)}: scene coordinates plus origin."""
    if pos is None:
        return {}
    if not isinstance(pos, dict):
        pos = {"": pos}
    out = {}
    for key, p in pos.items():
        if key and not re.match(r"[a-z][a-z0-9_]*\Z", key):
            raise ValueError(f"{key!r}: a place is named in small letters, digits and _")
        if len(p) != 3:
            raise ValueError(f"a place has three numbers, not {len(p)}")
        out[key] = tuple(float(p[i]) + float(origin[i]) for i in range(3))
    return out


def _command(text, spots, comment=False):
    """One line of a function as a package gives it: one command, without the slash of the chat."""
    if not isinstance(text, str) or "\n" in text or "\r" in text:
        raise ValueError(f"a command is one line of text, not {text!r}")
    text = text.strip()
    if not text or text.startswith("/") or (text.startswith("#") and not comment):
        raise ValueError(f"{text!r} is not a command (a function's line has no slash)")
    for m in _SPOT.finditer(text):
        if (m.group(1) or "") not in spots:
            raise ValueError(f"{m.group(0)} in {text!r}: pos= gives no such place")
    return text


def _fill(text, spots, at, namespace):
    """The text with its places written out for the scene placed at `at`, and {ns} as the namespace."""
    for key, p in spots.items():
        for i, axis in enumerate("xyz"):
            text = text.replace("{" + (key + "." if key else "") + axis + "}", _num(p[i] + at[i]))
    return text.replace("{ns}", namespace)


def run(canvas, pos, command, cycle, at=(0,), *, origin=(0, 0, 0), phase=0, weight=1):
    """A command of a package's own on the ticks `at` of every `cycle` ticks: the guide's look for
    a player who has walked up to something.

    pos      the place the command is about (scene coordinates, plus origin): {x} {y} {z} in the
             command are written out as its coordinates in the world. A dict of places, {"door":
             (x, y, z), ...}, is written {door.x} {door.y} {door.z}; None when it names no place.
             Other braces stay as they are; {ns} is the data pack's namespace.
    weight   the commands it counts as in the budget. 1 for a command that finds nobody most of
             the time (execute as @a[x=..,distance=..2,tag=!seen] run function ...); what runs for
             every player every time is counted in full: 1 plus the lines of the function it calls.

    A selector measures to the player's feet. Like a sound, a command that shares a part's period
    is on that part's chain; commands of one cycle on one tick cost one function between them.
    """
    cycle = int(cycle)
    if cycle < 1:
        raise ValueError(f"a cycle of {cycle} ticks")
    if int(weight) < 1:
        raise ValueError("weight is 1 or more")
    spots = _spots(pos, origin)
    text = _command(command, spots)
    _book(canvas).points.append(_Point("run", text.split()[0], spots.get("", (0.0, 0.0, 0.0)), cycle,
                                       _at(at, cycle), phase, text, spots=spots, weight=weight))
    return 0


def function(canvas, name, lines, *, pos=None, origin=(0, 0, 0)):
    """A function of a package's own, <namespace>:<name>, written by write() with the loop's.

    name     folder/name ("guide/first"), in the small letters, digits and _ . - of the game's
             names. The folder is the package's: not a scene's name (build/place.py keeps its
             functions there) and not one that ends in -motion (the loops').
    lines    its commands, one a line, without the slash; a line that starts with # is a comment.
             {x} {y} {z}, {door.x} ... and {ns} as in run().

    It runs when something calls it: a command registered with run(), another function, a
    function tag of the map (tools/export.py), an operator. What it schedules itself is not in
    the budget check() counts: agree it with the loop's keeper and write it into the card.
    """
    if not isinstance(name, str) or not _OWN.match(name) or any(set(part) <= {"."} for part in name.split("/")):
        raise ValueError(f"{name!r}: a function of a package's own is named folder/name, in the game's letters")
    folder = name.split("/", 1)[0]
    if folder.endswith("-motion") or os.path.isdir(os.path.join(_SCENES, folder)):
        raise ValueError(f"{name!r}: the folder {folder!r} is a scene's or a loop's; take one of the package's own")
    book = _book(canvas)
    if name in book.own:
        raise ValueError(f"{name}: this function is registered already")
    if isinstance(lines, str):
        raise ValueError(f"{name}: lines= is a list of commands")
    spots = _spots(pos, origin)
    out = [_command(line, spots, comment=True) for line in lines]
    if not any(not line.startswith("#") for line in out):
        raise ValueError(f"{name}: a function without a command")
    book.own[name] = (out, spots)
    return 0


def limits(canvas, peak=None, mean=None):
    """Other limits for this canvas than PEAK and MEAN. For a load test only: check() says so."""
    book = _book(canvas)
    if peak is not None:
        book.peak = int(peak)
    if mean is not None:
        book.mean = float(mean)
    return 0


def registered(canvas):
    """(parts, points) registered on the canvas."""
    book = getattr(canvas, "motion", None)
    return (len(book.parts), len(book.points)) if book is not None else (0, 0)


# ---- from the registrations to the functions -------------------------------------------------------
class _Chain:
    """The parts and points of one period: the ticks of the cycle on which something is due."""

    def __init__(self, cycle):
        self.cycle = cycle
        self.events = {}        # tick -> [command]
        self.more = {}          # tick -> commands its lines count as beyond one each (run(weight=))
        self.files = []         # (tick, [lines]) in order, once the plan is drawn up
        self.offset = 0         # ticks after start() the chain's first function runs (plus one)
        self.follows = None     # the cycle of the chain it keeps in step with (turn(in_step=))

    def add(self, tick, command, weight=1):
        tick %= self.cycle
        self.events.setdefault(tick, []).append(command)
        if weight != 1:
            self.more[tick] = self.more.get(tick, 0) + weight - 1

    def load(self, tick, lines):
        """Commands the function of this tick counts as."""
        return len(lines) + self.more.get(tick, 0)

    def count(self):
        return sum(self.load(tick, lines) for tick, lines in self.files)


class _Plan:
    """Everything write() writes and check() counts, for one scene placed at `at`."""

    def __init__(self, canvas, name, at, namespace):
        book = canvas.motion
        self.book, self.name = book, name
        self.base = f"{namespace}:{name}-motion"
        self.number = (zlib.crc32(name.encode("utf-8")) & 0x7FFFFFFF) or 1
        self.at = tuple(float(v) for v in at)
        self._distinct(canvas)
        chains = {}
        self.rest = []
        for part in book.parts:
            sel = self._selector(part)
            chain = chains.setdefault(part.cycle, _Chain(part.cycle))
            for tick, duration, turn, slide_ in part.steps:
                chain.add(tick + part.phase, self._pose(sel, part, duration, turn, slide_))
            for tick, model in part.swaps:
                chain.add(tick + part.phase, self._swap(sel, model))
            if part.swaps:
                self.rest.append(self._swap(sel, part.swaps[0][1]))
            else:
                self.rest.append(self._pose(sel, part, 0, 0.0, 0.0))
        for point in book.points:
            text = _fill(point.text, point.spots, self.at, namespace)
            chain = chains.setdefault(point.cycle, _Chain(point.cycle))
            for tick in point.ticks:
                chain.add(tick + point.phase, text, point.weight)
        self.own = {own: [_fill(line, spots, self.at, namespace) for line in lines]
                    for own, (lines, spots) in book.own.items()}
        for part in book.parts:
            if part.in_step is None:
                continue
            chain = chains[part.cycle]
            if part.in_step not in chains:
                raise ValueError(f"{part.name}: in_step={part.in_step}, and nothing in this scene has a cycle of "
                                 f"{part.in_step} ticks")
            if chain.follows not in (None, part.in_step):
                raise ValueError(f"{part.name}: in_step={part.in_step}, and another part of its cycle of {part.cycle} "
                                 f"ticks has in_step={chain.follows}; a chain keeps in step with one other")
            chain.follows = part.in_step
        self.chains = [chains[c] for c in sorted(chains)]
        if not self.chains:     # functions of the packages' own and nothing that loops
            self.peak, self.mean, self.watch, self.files = 0, 0.0, 0, {}
            return
        holder = f"#{name}"
        guard = (f"execute unless score {RUN} {OBJECTIVE} matches {self.number} run "
                 f"return run function {self.base}/halt")
        for i, chain in enumerate(self.chains):
            ticks = sorted(chain.events)
            for k, tick in enumerate(ticks):
                gap = (ticks[(k + 1) % len(ticks)] - tick) % chain.cycle or chain.cycle
                lines = [f"schedule function {self.base}/c{chain.cycle}/{(k + 1) % len(ticks)} {gap}t replace"]
                if k == 0:
                    # a chain goes on only while its scene's loop is the one that runs in the world
                    lines.insert(0, guard)
                    if i == 0:      # the quickest chain says once a cycle that the loop is alive
                        lines.append(f"scoreboard players set {holder} {OBJECTIVE} 1")
                chain.files.append((tick, lines + chain.events[tick]))
        self.peak = self._stagger()
        self.mean = sum(chain.count() / float(chain.cycle) for chain in self.chains)
        self.watch = self.chains[0].cycle + GRACE
        self.files = self._files(holder)

    def _distinct(self, canvas):
        """A selector finds a part by the spot it stands on and by its name, so every registered
        entity is still on the canvas and no two of one name stand on one spot."""
        on_canvas = {id(e) for e in canvas.entities}
        seen = {}
        for part in self.book.parts:
            if id(part.entity) not in on_canvas:
                raise ValueError(f"{part.name}: the registered entity is no longer on the canvas")
            for other in seen.get(part.name, ()):
                if all(abs(part.pos[i] - other.pos[i]) < APART for i in range(3)):
                    raise ValueError(f"{part.name}: two registered parts of this name stand on one spot "
                                     f"{tuple(round(v, 3) for v in part.pos)}; give one of them name=")
            seen.setdefault(part.name, []).append(part)

    def _selector(self, part):
        x, y, z = (_num(part.pos[i] + self.at[i]) for i in range(3))
        return f"@e[type={part.type},x={x},y={y},z={z},distance=..{NEAR},tag=m.{part.name},limit=1]"

    @staticmethod
    def _pose(sel, part, duration, turn, slide_):
        left, shift = part.pose(turn, slide_)
        return (f"data merge entity {sel} {{start_interpolation:0,interpolation_duration:{int(duration)},"
                f"transformation:{{left_rotation:{_floats(left)},right_rotation:{_floats(part.right)},"
                f"scale:{_floats(part.scale)},translation:{_floats(shift)}}}}}")

    @staticmethod
    def _swap(sel, model):
        return f"data merge entity {sel} {{item:{{components:{{\"minecraft:item_model\":\"{model}\"}}}}}}"

    def _stagger(self):
        """Start the chains a few ticks apart, so that their busy ticks do not fall together: the
        heaviest chain first, each at the offset that keeps the busiest tick lowest. A chain that
        keeps in step with another (turn(in_step=)) goes with that one, at the offset that lets
        its tick 0 fall on a tick 0 of the other's; the two are weighed and placed as one. Returns
        the number of commands in the busiest tick."""
        load = [0] * HORIZON
        led = {}
        for chain in self.chains:
            if chain.follows is not None:
                led.setdefault(chain.follows, []).append(chain)

        def team(chain, offset):
            """[(chain, its offset)] of a chain started at `offset` and of those in step with it. A
            chain's tick t comes offset + t - (its first tick) ticks after the start."""
            out = [(chain, offset)]
            for other in led.get(chain.cycle, ()):
                out += team(other, (offset - chain.files[0][0] + other.files[0][0]) % chain.cycle)
            return out

        def due(chain, offset):
            """{tick after the start: commands} of the chain's team, within the horizon."""
            out = {}
            for member, off in team(chain, offset):
                first = member.files[0][0]
                for tick, lines in member.files:
                    for t in range(off + tick - first, HORIZON, member.cycle):
                        out[t] = out.get(t, 0) + member.load(tick, lines)
            return out

        def weight(chain):
            return sum(member.count() / float(member.cycle) for member, _off in team(chain, 0))

        for chain in sorted((c for c in self.chains if c.follows is None), key=lambda c: (-weight(c), c.cycle)):
            best = None
            for off in range(min(chain.cycle, STAGGER)):
                marks = due(chain, off)
                peak = max((load[t] + n for t, n in marks.items()), default=0)
                if best is None or peak < best[0]:
                    best = (peak, off, marks)
            for member, off in team(chain, best[1]):
                member.offset = off
            for t, n in best[2].items():
                load[t] += n
        return max(load)

    def _files(self, holder):
        """{path below the scene's function folder: [lines]}"""
        add = f"scoreboard objectives add {OBJECTIVE} dummy"
        out = {}
        halt = []
        for chain in self.chains:
            for k, (_tick, lines) in enumerate(chain.files):
                out[f"c{chain.cycle}/{k}"] = lines
                halt.append(f"schedule clear {self.base}/c{chain.cycle}/{k}")
        out["halt"] = halt
        out["rest"] = [f"function {self.base}/halt"] + self.rest
        out["start"] = ([add, f"function {self.base}/rest",
                         f"scoreboard players set {RUN} {OBJECTIVE} {self.number}",
                         f"scoreboard players set {holder} {OBJECTIVE} 1"]
                        + [f"schedule function {self.base}/c{chain.cycle}/0 {1 + chain.offset}t replace"
                           for chain in self.chains])
        out["stop"] = [add, f"execute if score {RUN} {OBJECTIVE} matches {self.number} run "
                            f"scoreboard players set {RUN} {OBJECTIVE} 0",
                       f"function {self.base}/rest"]
        out["load"] = [add, f"scoreboard players set {holder} {OBJECTIVE} 0",
                       f"schedule function {self.base}/watch {self.watch}t replace"]
        out["watch"] = [f"execute if score {RUN} {OBJECTIVE} matches {self.number} unless score {holder} "
                        f"{OBJECTIVE} matches 1 run function {self.base}/start"]
        return out


def _plan(canvas, name, at, namespace):
    book = getattr(canvas, "motion", None) if canvas is not None else None
    if book is None or not (book.parts or book.points or book.own):
        return None
    return _Plan(canvas, name, at, namespace)


def _load_tag(pack_dir, entry, wanted):
    """Put the scene's load function into #minecraft:load, or take it out. The other scenes' entries
    stay; every entry is optional, so a scene whose functions are gone does not break the tag."""
    path = os.path.join(pack_dir, "data", "minecraft", "tags", "function", "load.json")
    tag = {"values": []}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            tag = json.load(fh)
    elif not wanted:
        return
    values = [v for v in tag.get("values", []) if (v.get("id") if isinstance(v, dict) else v) != entry]
    if wanted:
        values.append({"id": entry, "required": False})
    if not values:
        os.remove(path)
        return
    tag["values"] = values
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(tag, fh, indent=1)
        fh.write("\n")


def _write_own(pack_dir, scene, namespace, own):
    """Write the packages' own functions ({name: [lines]}) and remove those this scene wrote the
    last time and has no more. What it wrote is noted in <pack>/<scene>.motion.json, a driver's
    note like build/place.py's <scene>.placed.json (tools/export.py takes both out of the map)."""
    root = os.path.join(pack_dir, "data", namespace, "function")
    note = os.path.join(pack_dir, f"{scene}.motion.json")
    before = []
    if os.path.exists(note):
        try:
            with open(note, encoding="utf-8") as fh:
                before = [n for n in json.load(fh).get("own", []) if isinstance(n, str) and _OWN.match(n)
                          and not any(set(part) <= {"."} for part in n.split("/"))]
        except (OSError, ValueError, AttributeError):
            before = []
    for name in before:
        if name in own:
            continue
        path = os.path.join(root, *name.split("/")) + ".mcfunction"
        if os.path.exists(path):
            os.remove(path)
        folder = os.path.dirname(path)
        while folder != root and os.path.isdir(folder) and not os.listdir(folder):
            os.rmdir(folder)
            folder = os.path.dirname(folder)
    for name, lines in own.items():
        path = os.path.join(root, *name.split("/")) + ".mcfunction"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
    if own:
        with open(note, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"own": sorted(own)}, fh, indent=1)
            fh.write("\n")
    elif os.path.exists(note):
        os.remove(note)


def write(canvas, pack_dir, name, at=(0, 200, 0), namespace="c164art"):
    """Write the scene's motion functions into the data pack, for the scene placed at `at` (the
    selectors and positions are in world coordinates, so a scene that is moved is written anew),
    and with them the functions of the packages' own (function()).

    Returns the commands the driver runs once the scene stands: ["function <ns>:<name>-motion/start"],
    or [] when nothing on the canvas loops. In that case the scene's motion folder and its entry
    in #minecraft:load are removed.
    """
    folder = os.path.join(pack_dir, "data", namespace, "function", f"{name}-motion")
    plan = _plan(canvas, name, at, namespace)
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    _load_tag(pack_dir, f"{namespace}:{name}-motion/load", plan is not None and bool(plan.files))
    _write_own(pack_dir, name, namespace, plan.own if plan is not None else {})
    if plan is None or not plan.files:
        return []
    for rel, lines in plan.files.items():
        path = os.path.join(folder, *rel.split("/")) + ".mcfunction"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
    return [f"function {plan.base}/start"]


def check(canvas, models=None, pack=None):
    """What tools/check.py reports as the item "motion": (status, one line, details).

    models   the scene's models ({name: Model}), to see that a lamp's other model is there
    pack     the generated resource pack, to see that our sound events are in its sounds.json
    """
    try:
        plan = _plan(canvas, "check", (0, 0, 0), "c164art")
    except ValueError as e:
        return "FAIL", "what is registered does not make a loop", [str(e)]
    if plan is None:
        return "PASS", "nothing moves", []
    book = plan.book
    fails, warns, notes = [], [], []
    if plan.peak > book.peak:
        fails.append(f"{plan.peak} commands in the busiest tick, the limit is {book.peak}")
    if plan.mean > book.mean:
        fails.append(f"{plan.mean:.1f} commands a tick on average, the limit is {book.mean:g}")
    if len(plan.files) + len(plan.own) > FILES:
        fails.append(f"{len(plan.files) + len(plan.own)} function files, the limit is {FILES}")
    # a function of our namespace that a package's command names is one that is registered (the
    # loops' own folders aside: start and stop are there for whoever wants them)
    theirs = [(f"the command on the chain of {p.cycle} ticks", [p.text]) for p in book.points if p.kind == "run"]
    theirs += [(f"the function {own}", lines) for own, lines in plan.own.items()]
    for where, lines in theirs:
        for line in lines:
            for space, path in _CALLS.findall(line.replace("{ns}", "c164art")):
                if space == "c164art" and not path.split("/", 1)[0].endswith("-motion") and path not in plan.own:
                    fails.append(f"{where} names the function c164art:{path}, which nobody has registered")
    if plan.own:
        notes.append("functions of the packages' own: " + ", ".join(
            f"{own} ({sum(1 for ln in lines if not ln.startswith('#'))} commands)" for own, lines in plan.own.items()))
    for chain in plan.chains:
        if len(chain.files) > EVENTS:
            fails.append(f"the chain of {chain.cycle} ticks has {len(chain.files)} functions, the limit is {EVENTS}")
        notes.append(f"chain of {chain.cycle} ticks: {len(chain.files)} functions, {chain.count()} commands a "
                     f"cycle, starts {1 + chain.offset} ticks after start")
    names = None if models is None else {getattr(m, "name", k) for k, m in dict(models).items()}
    for part in book.parts:
        for _tick, ref in part.swaps:
            if names is not None and ref.startswith(NS + ":") and ref.split(":", 1)[1] not in names:
                fails.append(f"{part.name}: blinks to the model {ref}, which the scene does not have")
        if part.kind in ("slide", "blink"):
            continue
        steps = f"{len(part.steps)} steps in {part.cycle} ticks"
        if part.forced:
            warns.append(f"{part.name}: {steps} set by hand (lead {part.lead}); its model strays "
                         f"{part.stray * 16.0:.2f} pixels from its arc")
        elif part.stray > WOBBLE + 1e-9:
            notes.append(f"{part.name}: {steps}; its model strays {part.stray * 16.0:.2f} pixels from its arc "
                         f"(its middle lies {part.arm():.2f} blocks off the axis), within the half pixel a "
                         f"fast part is let off with")
        elif part.lead == 0:
            notes.append(f"{part.name}: {steps}, not aimed ahead: its middle lies {part.arm():.2f} blocks off "
                         f"the axis")
        elif part.kind == "spin" and len(part.steps) > 4:
            notes.append(f"{part.name}: {steps}: its middle lies {part.arm():.2f} blocks off the axis")
    ours = sorted({p.what for p in book.points if p.kind == "sound" and p.what.startswith(NS + ":")})
    if ours:
        table = None
        path = os.path.join(pack, "assets", NS, "sounds.json") if pack else None
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                table = json.load(fh)
        for event in ours:
            if table is None:
                warns.append(f"{event}: the pack has no assets/{NS}/sounds.json, so nothing is heard")
            elif event.split(":", 1)[1] not in table:
                fails.append(f"{event} is not in assets/{NS}/sounds.json")
    if (book.peak, book.mean) != (PEAK, MEAN):
        warns.append(f"the scene sets its own limits ({book.peak} in a tick, {book.mean:g} on average, not "
                     f"{PEAK} and {MEAN:g}): a load test")
    own = f" and {len(plan.own)} of the packages' own" if plan.own else ""
    summary = (f"{len(book.parts)} parts and {len(book.points)} points on {len(plan.chains)} chains, "
               f"{len(plan.files)} function files{own}; {plan.peak} commands in the busiest tick (limit {book.peak}), "
               f"{plan.mean:.1f} a tick on average (limit {book.mean:g})")
    return ("FAIL" if fails else "WARN" if warns else "PASS"), summary, fails + warns + notes
