"""What no picture shows of a loop on the real machine: the server is asked over RCON while the
scene stands (plan/parts/motion.md section 10, the list after the stations).

Not a work package (the name starts with "_"). Two scenes' own scripts use it:

    scenes/obs_mot_loop/onreal.py    the six things a picture cannot show, on the beat board
    scenes/obs_mot_load/onreal.py    what 35 commands a tick cost the server

The render post's trip runs such a script after the scene's shots, with the game still open
(tools/nodetrip.py --after <scene>=<script>), from build/ as

    <script> --pw-file <file> --port <n> --origin X Y Z

and keeps what it prints beside the scene's pictures. Exit code 0: every check that was made
passed; 1: one did not; 2: the script could not do its work. The server is left running, the loop
started, the players where they stood, the same chunks force-loaded as before.

How a part is read. The server holds the pose a part was given last (the client fills in the way
there), and  data get entity <selector> transformation  reads it back. A pose that is read is the
pose of one of the part's steps, and a step is due from its tick of the cycle to the next step's:
so every reading says where in its cycle the part's chain is, and the readings of all the parts
of one chain have to agree on it. A chain's clock is the set of ticks, modulo its cycle, on which
its first function can have run, given all that was read; a reading that leaves the clock empty
is a part that is not where its chain has it: it lost a step, or the loop was started anew.

What the game answers was read off its language file and classes (26.3: en_us.json,
server/commands, server/rcon); _onreal_test.py plays both scripts against _kit_test's game.
"""
import argparse
import os
import re
import sys
import time
import traceback

from . import _kit as MK

TOL = 2e-5                      # a number read back may differ this much from the one written
REST = -1                       # among a reading's steps: the pose the part was placed in
AWAY = 640                      # blocks north the players are sent for the unloading (plots lie
                                # along x, their galleries to the south: the north is empty)
NEARBY = 24                     # chunks round the plot whose force-loading the unloading lifts
RECORD = "c164t"                # the objective a run leaves its record in, for the next run
SPARE = 12.0                    # seconds kept for putting things back
RELOAD = 200                    # ticks a /reload is given before its load functions are given up
ROUNDS, SPRINT = 3, 2.5         # the cost of a loop: sprints with it running and stopped, seconds each

_DATA = re.compile(r" has the following entity data: (.*)\Z", re.S)
_CHUNK = re.compile(r"\[(-?\d+), (-?\d+)\]")


class Stuck(Exception):
    """The server does not do what the script waits for; the script cannot go on."""


def _numbers(text):
    return tuple(float(v.strip().rstrip("fdFD")) for v in text.split(",") if v.strip())


def _near(a, b, tol=TOL):
    return len(a) == len(b) and all(abs(x - y) <= tol for x, y in zip(a, b))


def _turn(a, b):
    """Two rotations as the game holds them are the same turn: q and -q are."""
    return _near(a, b) or _near(a, tuple(-v for v in b))


def _coord(v):
    return f"{float(v):.4f}"


def _span(a, b):
    """So many ticks, as far as it is known."""
    a, b = max(0, a), max(0, b)
    return f"{a} tick{'' if a == 1 else 's'}" if a == b else f"{a} to {b} ticks"


class Server:
    """The server's console over RCON, and the few things the checks read from it."""

    def __init__(self, console, sleep=time.sleep, now=time.monotonic, wall=time.time):
        self.console, self.sleep, self.now, self.wall = console, sleep, now, wall
        self.asked = 0
        self.said = ""

    def ask(self, command):
        self.asked += 1
        self.said = self.console.command(command)
        return self.said

    def time(self):
        m = re.search(r"game time is (-?\d+)", self.ask("time query gametime"))
        if not m:
            raise Stuck(f"time query gametime -> {self.said[:160]!r}")
        return int(m.group(1))

    def score(self, holder, objective=MK.OBJECTIVE):
        m = re.search(r" has (-?\d+) ", self.ask(f"scoreboard players get {holder} {objective}"))
        return int(m.group(1)) if m else None

    def put(self, holder, value, objective=MK.OBJECTIVE):
        self.ask(f"scoreboard players set {holder} {objective} {int(value)}")

    def data(self, target, path):
        """What  data get entity  says of the path; None when there is no such entity or no such tag."""
        m = _DATA.search(self.ask(f"data get entity {target} {path}"))
        return m.group(1).strip() if m else None

    def pose(self, selector):
        """(left rotation, right rotation, scale, shift) of a display entity; None when it is not found."""
        text = self.data(selector, "transformation")
        if text is None:
            return None
        out = []
        for key in ("left_rotation", "right_rotation", "scale", "translation"):
            m = re.search(key + r": \[([^\]]*)\]", text)
            if not m:
                raise Stuck(f"a transformation without {key}: {text[:200]!r}")
            out.append(_numbers(m.group(1)))
        return tuple(out)

    def model(self, selector):
        text = self.data(selector, 'item.components."minecraft:item_model"')
        return None if text is None else text.strip("\"'")

    def players(self):
        reply = self.ask("list")
        names = reply.split(":", 1)[1] if ":" in reply else ""
        return [n.strip() for n in names.split(",") if n.strip()]

    def pace(self):
        """(running | lagging | sprinting | frozen, average milliseconds a tick, P50, P95, P99) of
        the last hundred ticks, as  tick query  gives them; None for what it does not say."""
        reply = self.ask("tick query")
        state = ("frozen" if "frozen" in reply else "sprinting" if "sprinting" in reply
                 else "lagging" if "keep up" in reply else "running")
        avg = re.search(r"Average time per tick: ([\d.]+)ms", reply)
        per = re.search(r"P50: ([\d.]+)ms P95: ([\d.]+)ms P99: ([\d.]+)ms", reply)
        return (state, float(avg.group(1)) if avg else None) + tuple(float(per.group(k)) if per else None
                                                                     for k in (1, 2, 3))

    def forced(self):
        """The chunks marked for force loading in the overworld, as (x, z)."""
        reply = self.ask("forceload query")
        return [] if " at: " not in reply else [(int(x), int(z)) for x, z in _CHUNK.findall(reply.split(" at: ", 1)[1])]

    def wait(self, ticks):
        """Until the game is so many ticks further. Returns the game time then."""
        start = g = self.time()
        t0 = self.now()
        while g < start + ticks:
            if self.now() - t0 > 10.0 + 0.5 * ticks:
                raise Stuck(f"the game time went from {start} to {g} in {self.now() - t0:.0f} s: the game stands still")
            self.sleep(max(0.015, 0.04 * (start + ticks - g - 1)))
            g = self.time()
        return g

    def skip(self, ticks):
        """Let the game run so many ticks as fast as it can (tick sprint). Returns the game time
        then, and (ticks, seconds) of the stretch in the middle of the sprint that was timed."""
        start = self.time()
        self.ask(f"tick sprint {int(ticks)}")
        t0 = self.now()
        marks = [(t0, start)]
        while marks[-1][1] < start + ticks:
            if self.now() - t0 > 20.0 + 0.5 * ticks:
                raise Stuck(f"a sprint of {ticks} ticks is not over after {self.now() - t0:.0f} s")
            self.sleep(0.004)
            marks.append((self.now(), self.time()))
        inner = [(t, g) for t, g in marks if start + 0.1 * ticks <= g <= start + 0.9 * ticks]
        span = (inner[-1][1] - inner[0][1], inner[-1][0] - inner[0][0]) if len(inner) >= 2 else (0, 0.0)
        return marks[-1][1], span


class Reader:
    """One registered part as the server holds it: how it is read, and which of its steps a
    reading can be."""

    def __init__(self, plan, part, label):
        self.part, self.label, self.cycle = part, label, part.cycle
        self.selector = plan._selector(part)
        if part.swaps:
            events = [((tick + part.phase) % part.cycle, model) for tick, model in part.swaps]
            self.rest = part.swaps[0][1]
        else:
            events = [((tick + part.phase) % part.cycle, part.pose(turn, slide))
                      for tick, _ticks, turn, slide in part.steps]
            self.rest = part.pose(0.0, 0.0)
        events.sort(key=lambda e: e[0])
        ticks = [tick for tick, _pose in events]
        self.poses = [pose for _tick, pose in events]
        self.first = ticks[0]           # the tick of the cycle on which the part gets its first step after a start
        n = len(events)
        lasts = [(ticks[(k + 1) % n] - ticks[k] - 1) % self.cycle + 1 for k in range(n)]
        self.longest = max(lasts)       # ticks the longest of its steps is due
        self.due = [[(ticks[k] + d) % self.cycle for d in range(lasts[k])] for k in range(n)]

    def read(self, server):
        """The part's model (a lamp that blinks) or its pose; None when the entity is not found."""
        return server.model(self.selector) if self.part.swaps else server.pose(self.selector)

    def steps(self, value):
        """The steps this reading can be: REST among them when it is the part as it was placed.
        The empty set: a pose the plan does not have."""
        if self.part.swaps:
            out = {k for k, model in enumerate(self.poses) if model == value}
            return out | {REST} if value == self.rest else out
        left, _right, _scale, shift = value
        out = {k for k, (turn, slid) in enumerate(self.poses) if _turn(turn, left) and _near(slid, shift)}
        return out | {REST} if _turn(self.rest[0], left) and _near(self.rest[1], shift) else out

    def placed(self, value):
        """Is this reading the part as its maker placed it, scale and right rotation too."""
        if value is None:
            return False
        if self.part.swaps:
            return value == self.rest
        left, right, scale, shift = value
        return (_turn(self.rest[0], left) and _near(self.rest[1], shift) and _turn(self.part.right, right)
                and _near(self.part.scale, scale))


class Clock:
    """Where in its cycle a chain is: the ticks, modulo the cycle, on which its first function can
    have run."""

    def __init__(self, chain):
        self.cycle, self.offset = chain.cycle, chain.offset
        self.ticks = None           # None: nothing is known
        self.fresh = None           # after a start: the game time by which the chain has set off
        self.from_start = None      # after a start: the game times it can have run at

    def forget(self):
        self.ticks = self.fresh = self.from_start = None

    def started(self, g0, g1):
        """The loop's start ran at a game time from g0 to g1: the chain's first function is due
        one tick and its offset later. A tick to either side is let by (which tick the queue
        counts from is the game's affair); what is read afterwards closes in on the tick it was."""
        self.ticks = {(g + 1 + self.offset) % self.cycle for g in range(g0 - 1, g1 + 2)}
        self.fresh = g1 + 2 + self.offset
        self.from_start = g0, g1

    def set_off(self):
        """After a start: how many ticks after it the chain's first function ran, as the readings
        have it (the plan has 1 + offset); None when they do not say."""
        if not self.ticks or self.fresh is None:
            return None
        g0, g1 = self.from_start
        delays = {(tick - g) % self.cycle for tick in self.ticks for g in range(g0, g1 + 1)}
        delays = {d for d in delays if d <= self.offset + 3}
        return sorted(delays)

    def _fits(self, reader, steps, g0, g1):
        """The ticks the clock can stand on when the part shows one of these steps at a game time
        from g0 to g1. None: the reading says nothing (the part has not had a step since the start)."""
        if REST in steps and self.fresh is not None and g0 < self.fresh + reader.first:
            return None
        fits = {(g - d) % self.cycle for k in steps if k != REST for d in reader.due[k] for g in range(g0, g1 + 1)}
        return fits if self.ticks is None else fits & self.ticks

    def agrees(self, reader, steps, g0, g1):
        fits = self._fits(reader, steps, g0, g1)
        return fits is None or bool(fits)

    def see(self, reader, steps, g0, g1):
        """Take a reading in. False: it does not agree with what was read before, and the clock
        stays as it was."""
        fits = self._fits(reader, steps, g0, g1)
        if fits:
            self.ticks = fits
        return fits is None or bool(fits)

    def width(self):
        return "unknown" if self.ticks is None else f"{len(self.ticks)}"


class Seen:
    """What a stretch of readings showed."""

    def __init__(self):
        self.rounds = self.readings = 0
        self.steps = {}             # label -> every step the part was seen in
        self.kinds = {}             # label -> the different readings, to tell whether it moved
        self.lost = []              # (game time, label): the entity was not found
        self.odd = []               # (game time, label, the reading): a pose the plan does not have
        self.off = []               # (game time, game time, label, steps): not where its chain's clock has it

    def clean(self):
        return not (self.lost or self.odd or self.off)

    def moved(self):
        return {label for label, kinds in self.kinds.items() if len(kinds) > 1}

    def faults(self, most=4):
        out = [f"game time {g}: {label} is not found" for g, label in self.lost[:most]]
        out += [f"game time {g}: {label} is in a pose the plan does not have: {value}" for g, label, value in self.odd[:most]]
        out += [f"game time {a}..{b}: {label} shows step {', '.join(map(str, steps)) or '?'} "
                f"(-1 is the rest pose), which its chain is not at" for a, b, label, steps in self.off[:most]]
        more = len(self.lost) + len(self.odd) + len(self.off) - len(out)
        return out + ([f"... and {more} more"] if more > 0 else [])


class Bench:
    """A scene's loop under test: its plan, its parts as the server holds them, its chains' clocks,
    and the checks."""

    def __init__(self, server, canvas, scene, origin, namespace="c164art", seconds=270.0, out=print):
        self.server, self.scene, self.origin, self.out = server, scene, tuple(int(v) for v in origin), out
        self.plan = MK._plan(canvas, scene, self.origin, namespace)
        if self.plan is None:
            raise Stuck(f"nothing is registered on the canvas of {scene}")
        names = [part.name for part in self.plan.book.parts]
        count = {}
        self.readers = []
        for part in self.plan.book.parts:
            count[part.name] = count.get(part.name, 0) + 1
            label = part.name if names.count(part.name) == 1 else f"{part.name}.{count[part.name]}"
            self.readers.append(Reader(self.plan, part, label))
        self.clocks = {chain.cycle: Clock(chain) for chain in self.plan.chains}
        self.base, self.number, self.holder = self.plan.base, self.plan.number, f"#{scene}"
        self.quick = self.plan.chains[0].cycle          # the chain that carries the heartbeat
        self.patience, self.retyped, self.held = RELOAD, False, 0.0
        self.functions = [f"{self.base}/c{chain.cycle}/{k}" for chain in self.plan.chains
                          for k in range(len(chain.files))]
        self.until = server.now() + seconds
        self.began = server.now()
        self.rows = []              # (check, status, what was found)
        self.undo = []              # (what, how): things to put back, the last first
        self.leave = False          # the scene is not there to be checked: its loop is not to be started either

    # ---- the report ----
    def note(self, check, status, text, details=()):
        self.rows.append((check, status, text))
        self.out(f"{check:<9} {status:<8} {text}")
        for line in details:
            self.out(f"{'':<18} {line}")

    def left(self):
        return self.until - self.server.now()

    # ---- reading ----
    def look(self, readers=None):
        """Every part read once: (game time before, game time after, [(reader, reading)])."""
        g0 = self.server.time()
        values = [(r, r.read(self.server)) for r in (self.readers if readers is None else readers)]
        return g0, self.server.time(), values

    def take(self, seen, look, learn=True):
        g0, g1, values = look
        seen.rounds += 1
        for reader, value in values:
            seen.readings += 1
            if value is None:
                seen.lost.append((g0, reader.label))
                continue
            steps = reader.steps(value)
            seen.steps.setdefault(reader.label, set()).update(steps)
            seen.kinds.setdefault(reader.label, set()).add(frozenset(steps))
            if not steps:
                seen.odd.append((g0, reader.label, value))
                continue
            clock = self.clocks[reader.cycle]
            if not (clock.see(reader, steps, g0, g1) if learn else clock.agrees(reader, steps, g0, g1)):
                seen.off.append((g0, g1, reader.label, sorted(steps)))

    def watch(self, ticks, learn=True, readers=None, seen=None):
        """Read every part once a tick for so many ticks."""
        seen = Seen() if seen is None else seen
        g = start = self.server.time()
        t0 = self.server.now()
        while g < start + ticks:
            look = self.look(readers)
            self.take(seen, look, learn)
            g = look[1]
            while g == look[1]:
                if self.server.now() - t0 > 15.0 + 0.5 * ticks:
                    raise Stuck(f"the game time stands at {g}")
                self.server.sleep(0.015)
                g = self.server.time()
        return seen

    def beat(self, within=None):
        """Ticks until the loop says it is alive: the heartbeat's holder is set to 5, and the
        quickest chain sets it to 1 once a cycle. None: it did not within a cycle."""
        within = self.quick + 3 if within is None else within
        self.server.put(self.holder, 5)
        start = g = self.server.time()
        while g <= start + within:
            if self.server.score(self.holder) == 1:
                return g - start
            self.server.sleep(0.02)
            g = self.server.time()
        return None

    def queued(self):
        """How many of the scene's chain functions stood in the queue. They are taken out of it:
        this is asked when there should be none."""
        return sum(1 for name in self.functions if "Removed" in self.server.ask(f"schedule clear {name}"))

    def still(self, ticks):
        """Did no part change for so many ticks: the labels of those that did."""
        before = self.look()[2]
        self.server.wait(ticks)
        after = self.look()[2]
        return [r.label for (r, a), (_r, b) in zip(before, after) if a != b]

    def start(self):
        """Run the scene's start and set the clocks by it."""
        g0 = self.server.time()
        self.server.ask(f"function {self.base}/start")
        g1 = self.server.time()
        for clock in self.clocks.values():
            clock.started(g0, g1)
        return g0, g1

    def clock_widths(self):
        return ", ".join(f"c{cycle} {clock.width()}" for cycle, clock in sorted(self.clocks.items()))

    # ---- the checks ----
    def ready(self):
        """The scene stands, its loop is the one that runs, the game is not frozen."""
        s = self.server
        state, average = s.pace()[:2]
        g = s.time()
        plan = self.plan
        self.out(f"{self.scene} on the real machine, plot {' '.join(map(str, self.origin))}: {len(self.readers)} parts "
                 f"and {len(plan.book.points)} points on {len(plan.chains)} chains "
                 f"({', '.join(f'c{c.cycle} sets off {1 + c.offset} after start' for c in plan.chains)}), "
                 f"{len(plan.files)} functions, the loop's number {self.number}")
        self.out(f"game time {g}; the game is {state}, {average} ms a tick on average; "
                 f"players: {', '.join(s.players()) or 'none'}")
        if state == "frozen":
            self.leave = True
            self.note("ready", "FAIL", "the game is frozen (tick freeze): no loop runs, nothing can be checked")
            raise Stuck("the game is frozen")
        missing = [r.label for r, value in self.look()[2] if value is None]
        if missing:
            self.leave = True
            self.note("ready", "FAIL", f"{len(missing)} of {len(self.readers)} parts are not found where the plan "
                      f"has them: {', '.join(missing[:8])}", [f"the first selector: {self.readers[0].selector}"])
            raise Stuck("the scene's parts are not there")
        run = s.score(MK.RUN)
        if run != self.number:
            self.start()
            self.note("ready", "FAIL", f"{MK.RUN} was {run}, not this scene's {self.number}: its loop was not the one "
                      f"that runs. Started now, to go on with the checks")
            return
        self.note("ready", "PASS", f"all {len(self.readers)} parts are found, {MK.RUN} is this scene's number")

    def kept(self):
        """What an earlier run of this script left in the world: is the loop still in step with it."""
        s = self.server
        at = s.score("#at", RECORD)
        if at is None:
            self.note("record", "-", "no record of an earlier run in this world: nothing to compare (a second trip "
                      "with --no-place, after the server was down, shows whether the loop goes on where it was)")
            return
        if [s.score(f"#u{i}", RECORD) for i in range(4)] != self._uuid():
            self.note("record", "-", "the scene was placed anew since the record of an earlier run: nothing to compare")
            return
        ticks = (s.time() - at) % 2 ** 31
        seconds = int(s.wall()) - (s.score("#wall", RECORD) or 0)
        stood = seconds - ticks / 20.0
        age = (f"the record is {ticks} ticks of game time and {seconds} s old"
               + (f": the game stood still for {stood:.0f} s in between (the server was down)" if stood > 20 else ""))
        for cycle, clock in self.clocks.items():
            tick = s.score(f"#c{cycle}", RECORD)
            clock.forget()
            if tick is not None:
                clock.ticks = {(tick + d) % cycle for d in (-1, 0, 1)}
        took = self.beat()
        seen = self.watch(3 * self.quick)
        if took is not None and seen.clean():
            self.note("record", "PASS", f"{age}; the loop is alive and every part is where the record's clocks have "
                      f"it: no chain set off anew")
        else:
            self.note("record", "FAIL", f"{age}; "
                      + ("the loop is dead" if took is None else "the parts are not where the record's clocks have them"),
                      seen.faults())
            for clock in self.clocks.values():
                clock.forget()

    def alive(self, ticks=250, readers=None):
        """The loop beats, every part moves, and every pose that is read is one of the plan's, on
        the tick the plan has it."""
        took = self.beat()
        seen = self.watch(ticks, readers=readers)
        self.seen = seen
        readers = self.readers if readers is None else readers
        stood = [r.label for r in readers if r.label not in seen.moved()]
        text = (f"the heartbeat came back after {took} ticks; " if took is not None else "the heartbeat did not come back; ")
        text += (f"{seen.readings} readings of {len(readers)} parts in {ticks} ticks: "
                 + ("every one a pose of the plan and in step with its chain" if seen.clean() else "not all as planned")
                 + ("; every part moved" if not stood else f"; {len(stood)} did not move: {', '.join(stood[:6])}")
                 + f". Clocks, ticks wide: {self.clock_widths()}")
        self.note("alive", "PASS" if took is not None and seen.clean() and not stood else "FAIL", text, seen.faults())

    def every_step(self, piece=24):
        """The game sprints through the longest cycle in pieces, and after each piece the parts are
        read: every step of every part is to be seen once, where its chain's clock has it."""
        s = self.server
        seen = Seen()
        for label, steps in getattr(getattr(self, "seen", None), "steps", {}).items():
            seen.steps[label] = set(steps)
        longest = max(r.cycle for r in self.readers)
        pieces = -(-(longest + piece) // piece)
        t0 = s.now()
        for k in range(pieces):
            s.skip(piece)
            self.take(seen, self.look())
            if k == 0 and s.now() - t0 > 0.6:
                self.note("steps", "not done", f"the game does not sprint here (tick sprint {piece} took "
                          f"{s.now() - t0:.1f} s): a whole cycle of the slowest chain would take "
                          f"{longest / 20.0:.0f} s. The steps that were read are in the checks around this one")
                return
        took = s.now() - t0
        while s.pace()[0] == "sprinting":
            s.sleep(0.05)
        self.watch(10, seen=seen)
        missing = []
        steps = 0
        for r in self.readers:
            steps += len(r.poses)
            gone = sorted(set(range(len(r.poses))) - seen.steps.get(r.label, set()))
            if gone:
                missing.append(f"{r.label}: step {', '.join(map(str, gone))} of {len(r.poses)} was never read")
        text = (f"{pieces} sprints of {piece} ticks ({took:.1f} s): "
                + (f"all {steps} steps of the {len(self.readers)} parts were read back as the plan has them"
                   if not missing else f"{len(missing)} parts have steps that were never read")
                + ("; after the sprints every chain is where its clock had it" if seen.clean() else ""))
        self.note("steps", "PASS" if not missing and seen.clean() else "FAIL", text, missing[:6] + seen.faults())

    def _when(self, value, limit, since):
        """Wait until the heartbeat's holder reads `value`; `since` is a game time at which it read
        something else. Returns the earliest and the latest game time at which the change can have
        shown from here (what is done in a tick shows when the tick is over), or None when `limit`
        ticks went by without it."""
        s = self.server
        start, last = None, since       # last: the latest game time at which the holder still read something else
        while True:
            g0 = s.time()
            got = s.score(self.holder)
            g1 = s.time()
            start = g0 if start is None else start
            if got == value:
                return min(last + 1, g1), g1
            if g1 > start + limit:
                return None
            last = g0
            s.sleep(0.02)

    def _after_beat(self):
        """Wait for a tick just after a beat of the quickest chain, by its clock: the next beat is
        then most of a cycle away. False when the clock is not known well enough."""
        ticks = self.clocks[self.quick].ticks
        if not ticks or len(ticks) > self.quick // 4:
            return False
        s = self.server
        g = start = s.time()
        while g <= start + self.quick + 2:
            if all(1 <= (g - tick) % self.quick <= self.quick // 3 for tick in ticks):
                return True
            s.sleep(0.01)
            g = s.time()
        return False

    def _reload(self):
        s = self.server
        s.put(self.holder, 5)
        start = s.time()
        t0 = s.now()
        s.ask("reload")
        self.held = s.now() - t0
        return start, self._when(0, self.patience, start)

    def _reloaded(self, alive=False):
        """Type /reload and wait for the scene's load function, which sets the heartbeat's holder
        to 0. Returns (the game time of the command, the earliest and latest game time at which
        load can have shown); the last is None when it was not seen to run. self.held: the seconds
        the command held the server (the game answers when the reload is through; load runs at the
        beginning of the next tick, and the ticks that are due by then follow one upon the other).

        With the loop alive the holder reads 0 only until the next beat, and not at all when load
        runs on the very tick of a beat (load runs before the queue in a tick). So the command is
        typed just after a beat, by the quickest chain's clock; and when load was not seen though
        the loop beats, the command is typed a second time, half a beat off: self.retyped says so."""
        s = self.server
        self.retyped = False
        if alive:
            self._after_beat()
        start, when = self._reload()
        if when is None and s.score(self.holder) == 1:
            self.retyped = True
            s.wait((self.quick // 2 - (s.time() - start)) % self.quick)
            start, when = self._reload()
        if when is not None:        # the next /reload is given up sooner: this is how long one takes here
            self.patience = min(self.patience, 4 * (when[1] - start) + 60)
        return start, when

    def reload_alive(self):
        """/reload with the loop alive: the load function runs, finds the loop alive after its
        watch and leaves it alone; the parts go on from where they are."""
        patience = self.patience
        typed, load = self._reloaded(alive=True)
        twice = ("a first /reload did not show load running (it can run on the very tick of a heartbeat, which "
                 "hides it from here), so the command was typed again half a beat off. " if self.retyped else "")
        if load is None:
            self.note("reload", "FAIL", f"{twice}{patience} ticks after /reload the heartbeat's holder had not read "
                      f"0: the scene's load function was not seen to run (is it in #minecraft:load?)")
            return
        ran = f"/reload held the server for {self.held:.1f} s; load had run {_span(load[0] - typed, load[1] - typed)} later"
        beat = self._when(1, self.quick + 3, load[0])
        if beat is None:
            self.note("reload", "FAIL", f"{twice}{ran}, but the heartbeat did not come back within a cycle: the "
                      f"chains did not live through the reload")
            return
        seen = self.watch(max(20, self.plan.watch + 25 - (self.server.time() - load[1])))
        text = (f"{twice}{ran} (the heartbeat's holder read 0), the heartbeat was back "
                f"{_span(beat[0] - load[1], beat[1] - load[0])} after that; {self.server.time() - load[1]} ticks on, "
                f"past the watch of {self.plan.watch}, "
                + ("every part is where its chain's clock had it before the reload: nothing set off anew"
                   if seen.clean() else "the parts are not where their clocks had them: the loop set off anew"))
        self.note("reload", "PASS" if seen.clean() else "FAIL", text, seen.faults())
        if not seen.clean():
            self._learn()

    def _learn(self):
        """Read the clocks anew, after something put them wrong."""
        for clock in self.clocks.values():
            clock.forget()
        self.watch(2 * self.quick)

    def broken(self):
        """The queue is lost (halt clears it, as a pack that was off for a while would): nothing
        moves; after /reload the watch starts the loop again, all chains from one start."""
        s = self.server
        s.ask(f"function {self.base}/halt")
        s.put(self.holder, 5)
        moved = self.still(self.quick + 5)
        if moved or s.score(self.holder) != 5:
            self.start()
            self.note("broken", "FAIL", "after halt the loop still ran: "
                      + (f"{', '.join(moved[:6])} moved" if moved else "the heartbeat beat")
                      + ". Started anew, to go on with the checks")
            return
        patience = self.patience
        typed, load = self._reloaded()
        if load is None:
            self.start()
            self.note("broken", "FAIL", f"{patience} ticks after /reload the scene's load function was not seen to "
                      f"run. Started by hand, to go on with the checks")
            return
        ran = f"/reload held the server for {self.held:.1f} s; load had run {_span(load[0] - typed, load[1] - typed)} later"
        again = self._when(1, self.plan.watch + 2 * self.quick, load[0])
        if again is None:
            self.start()
            self.note("broken", "FAIL", f"{ran}, but {self.plan.watch + 2 * self.quick} ticks on the loop had not "
                      f"started again. Started by hand, to go on with the checks")
            return
        for clock in self.clocks.values():
            clock.started(*again)
        seen = self.watch(2 * self.quick)
        early, late = again[0] - load[1], again[1] - load[0]
        # load runs before its tick's game time is counted up: its 60 ticks read as 59 from here
        timely = early - 2 <= self.plan.watch <= late + 2
        text = (f"halt: nothing moved for {self.quick + 5} ticks and the heartbeat stayed away. {ran}, and "
                f"{_span(early, late)} after that the loop was started again (the watch is {self.plan.watch}); "
                + ("all chains set off from that one start and every part is where the plan has it since"
                   if seen.clean() else "but the parts are not where a start at that tick has them"))
        self.note("broken", "PASS" if seen.clean() and timely else "FAIL", text, seen.faults())
        if not seen.clean():
            self._learn()

    def takeover(self):
        """Another loop takes the world over (#run gets another number): at the next round of the
        quickest chain the guard calls halt, and the lines after the guard are not run."""
        s = self.server
        s.put(MK.RUN, 1 if self.number != 1 else 2)
        s.put(self.holder, 5)
        s.wait(self.quick + 2)
        moved = self.still(30)
        left = self.queued()
        beat = s.score(self.holder)
        ok = not moved and not left and beat == 5
        text = (f"{MK.RUN} given to another number: {self.quick + 2} ticks later (one round of the quickest chain) "
                + ("nothing moved for 30 ticks" if not moved else f"{', '.join(moved[:6])} still moved")
                + (", none of the scene's chain functions was queued" if not left
                   else f", {left} of the scene's {len(self.functions)} chain functions were still queued")
                + (", and the heartbeat's line after the guard was not run" if beat == 5
                   else f", but the heartbeat's holder read {beat}: the line after the guard was run"))
        self.start()
        seen = self.watch(self.quick)
        self.note("takeover", "PASS" if ok and seen.clean() else "FAIL", text + ". Started again"
                  + ("" if seen.clean() else ", but the parts are not where the plan has them"), seen.faults())

    def _uuid(self):
        text = self.server.data(self.readers[0].selector, "UUID")
        return None if text is None else [int(v) for v in re.findall(r"-?\d+", text.split(";", 1)[-1])]

    def _spot(self, name):
        pos, rot = self.server.data(name, "Pos"), self.server.data(name, "Rotation")
        if pos is None or rot is None:
            return None
        return _numbers(pos.strip("[]")) + _numbers(rot.strip("[]"))

    def _mark(self, chunks, word):
        """forceload add | remove for these chunks, a row of chunks to the command."""
        rows = {}
        for x, z in sorted(chunks):
            rows.setdefault(z, []).append(x)
        for z, xs in sorted(rows.items()):
            run = [xs[0]]
            for x in xs[1:] + [None]:
                if x is not None and x == run[-1] + 1:
                    run.append(x)
                    continue
                self.server.ask(f"forceload {word} {run[0] * 16} {z * 16} {run[-1] * 16} {z * 16}")
                run = [x]

    def unloaded(self, away=100):
        """Nobody near and nothing force-loaded: the scene's entities are let go and the chains run
        on without them. When somebody comes back, every part is right again at its next step."""
        s = self.server
        cx, cz = self.origin[0] >> 4, self.origin[2] >> 4
        mine = [(x, z) for x, z in s.forced() if abs(x - cx) <= NEARBY and abs(z - cz) <= NEARBY]
        spots = {name: self._spot(name) for name in s.players()}
        spots = {name: spot for name, spot in spots.items() if spot is not None}
        walkers = [name for name in spots if (s.data(name, "playerGameType") or "").strip() != "3"]
        if walkers:
            self.note("unload", "not done", f"{', '.join(walkers)} is online and not a spectator: sent away over "
                      f"the void he would fall, and while he stays the chunks stay. Nothing was changed")
            return

        def back():
            for name, spot in spots.items():
                s.ask(f"tp {name} " + " ".join(_coord(v) for v in spot))

        def marked():
            self._mark(mine, "add")

        self.undo += [("the force-loaded chunks", marked), ("the players", back)]
        self._mark(mine, "remove")
        for name in spots:
            s.ask(f"tp {name} {_coord(self.origin[0] + 0.5)} {_coord(self.origin[1] + 40)} "
                  f"{_coord(self.origin[2] - AWAY + 0.5)}")
        how = f"{len(mine)} chunks unmarked, {len(spots)} player(s) sent {AWAY} blocks north"
        start = g = s.time()
        while any(value is not None for _r, value in self.look()[2]):
            g = s.time()
            if g > start + 400:
                self.note("unload", "not done", f"{how}, but 400 ticks later the scene's entities were still found: "
                          f"the chunks were not let go, so there is nothing to see here")
                self._put_back()
                return
            s.sleep(0.05)
        gone = g - start
        took = self.beat()
        s.wait(max(0, away - (s.time() - start)))
        out = s.time() - start
        if spots:
            back()
            self.undo.remove(("the players", back))
        else:                       # nobody is online: marking the chunks again is what brings the scene back
            self._put_back()
        first = {}                  # label -> the game time it was found again
        right = {}                  # label -> ticks after that until it agreed with its chain's clock
        behind = set()
        start = s.time()
        limit = max(r.longest for r in self.readers) + 60
        while len(right) < len(self.readers) and s.time() <= start + limit:
            g0, g1, values = self.look()
            for reader, value in values:
                if value is None or reader.label in right:
                    continue
                first.setdefault(reader.label, g0)
                steps = reader.steps(value)
                if steps and self.clocks[reader.cycle].agrees(reader, steps, g0, g1):
                    right[reader.label] = g0 - first[reader.label]
                else:
                    behind.add(reader.label)
            while s.time() == g1:
                s.sleep(0.015)
        self._put_back()
        late = []
        for r in self.readers:
            if r.label not in right:
                late.append(f"{r.label}: not right again {limit} ticks after it was found (its longest step lasts "
                            f"{r.longest})" if r.label in first else f"{r.label}: not found again")
            elif right[r.label] > r.longest + 2:
                late.append(f"{r.label}: right again after {right[r.label]} ticks; its longest step lasts {r.longest}")
        seen = self.watch(self.quick)
        ok = took is not None and not late and seen.clean() and len(first) == len(self.readers)
        text = (f"{how}: the entities were gone after {gone} ticks; "
                + ("the heartbeat went on without them" if took is not None else "the heartbeat stopped without them")
                + (f". Back after {out} ticks away: " if spots else f". Marked again after {out} ticks: ")
                + (f"{len(first)} of {len(self.readers)} parts were found again" if len(first) < len(self.readers)
                   else f"{len(behind)} of {len(self.readers)} parts were behind when they were found again, and every "
                        f"part was right at its next step (the slowest after "
                        f"{max(right.values()) if right else '?'} ticks)" if not late
                   else f"{len(late)} parts were not right again within a step"))
        self.note("unload", "PASS" if ok else "FAIL", text, late[:6] + seen.faults())

    def _put_back(self):
        while self.undo:
            _what, how = self.undo.pop()
            how()

    def stopped(self):
        """stop: every part back as it was placed, nothing queued, and /reload does not start it."""
        s = self.server
        s.ask(f"function {self.base}/stop")
        run = s.score(MK.RUN)
        wrong = [r.label for r, value in self.look()[2] if not r.placed(value)]
        left = self.queued()
        typed, load = self._reloaded()
        s.wait(self.plan.watch + 10)
        again = [r.label for r, value in self.look()[2] if not r.placed(value)]
        ok = run == 0 and not wrong and not left and load is not None and not again and s.score(MK.RUN) == 0
        text = (f"stop: {MK.RUN} is {run}; "
                + ("every part is back as it was placed (pose, scale and right rotation; the lamp its own model)"
                   if not wrong else f"{len(wrong)} parts are not as they were placed: {', '.join(wrong[:6])}")
                + (", nothing of the scene is queued" if not left else f", {left} chain functions were still queued")
                + (f". /reload (load had run {_span(load[0] - typed, load[1] - typed)} later) and "
                   f"{self.plan.watch + 10} ticks more: "
                   if load is not None else ". /reload: the scene's load function was not seen to run, so this "
                                            "says nothing about a reload; ")
                + ("still stopped, every part as placed" if not again and s.score(MK.RUN) == 0
                   else f"it runs again: {', '.join(again[:6])} moved"))
        self.note("stop", "PASS" if ok else "FAIL", text)

    def started(self, ticks=100):
        """start: every chain sets off one tick and its offset after it, and every part is where
        the plan has it, tick for tick. The run's record is left in the world."""
        s = self.server
        self.start()
        run = s.score(MK.RUN)
        seen = self.watch(ticks)
        ok = run == self.number and seen.clean()
        whose = "this scene's" if run == self.number else str(run)
        text = (f"start: {MK.RUN} is {whose}; for {ticks} ticks every part was where its chain has it "
                f"({seen.readings} readings). Ticks after the start at which the chains set off, read / planned: "
                + ", ".join(f"c{cycle} {'-'.join(map(str, clock.set_off() or ['?']))}/{1 + clock.offset}"
                            for cycle, clock in sorted(self.clocks.items()))
                if seen.clean() else f"start: {MK.RUN} is {whose}; the parts were not where the plan has them")
        self.note("start", "PASS" if ok else "FAIL", text, seen.faults())
        if ok:
            self._record()

    def _record(self):
        s = self.server
        uuid = self._uuid()
        if uuid is None or len(uuid) != 4:
            return
        s.ask(f"scoreboard objectives add {RECORD} dummy")
        for i, v in enumerate(uuid):
            s.put(f"#u{i}", v, RECORD)
        for cycle, clock in self.clocks.items():
            if clock.ticks:
                s.put(f"#c{cycle}", sorted(clock.ticks)[len(clock.ticks) // 2], RECORD)
        s.put("#wall", int(s.wall()), RECORD)
        s.put("#at", s.time() % 2 ** 31, RECORD)
        self.out(f"{'':<18} the clocks are noted in the world (objective {RECORD}) for a later run to compare with")

    def cost(self, rounds=None, seconds=None):
        """What the loop costs the server. The game sprints (ticks as fast as they come) with the
        loop running and with it stopped, in turns, and the time a tick takes is read off each
        sprint; then the game's own figure at its normal pace, tick query's hundred ticks."""
        s = self.server
        rounds, seconds = ROUNDS if rounds is None else rounds, SPRINT if seconds is None else seconds
        _g, (ticks, took) = s.skip(400)
        if not ticks or took <= 0.0 or took / ticks > 0.04:
            self.note("cost", "not done", f"the game does not sprint here (tick sprint 400 -> {ticks} ticks timed in "
                      f"{took:.2f} s): the cost of a tick cannot be read this way")
            return
        n = int(min(20000, max(400, seconds * ticks / took)))
        times = {True: [], False: []}
        running = True
        for _ in range(2 * rounds):
            s.wait(3)
            _g, (ticks, took) = s.skip(n)
            if ticks:
                times[running].append(1000.0 * took / ticks)
            running = not running
            if running:
                self.start()
            else:
                s.ask(f"function {self.base}/stop")
        paces = {}
        for running in (True, False):       # the loop runs again after the last sprint
            if not running:
                s.ask(f"function {self.base}/stop")
            s.wait(110)
            paces[running] = s.pace()
        self.start()
        if not times[True] or not times[False]:
            self.note("cost", "not done", "the sprints were too short to be timed")
            return
        on, off = (sorted(times[k])[len(times[k]) // 2] for k in (True, False))
        each = 1000.0 * (on - off) / self.plan.mean         # microseconds a command
        book = self.plan.book

        def ms(values):
            return ", ".join(f"{v:.3f}" for v in values)

        def pace(p):
            return (f"{p[1]} ms a tick on average, P50 {p[2]}, P95 {p[3]}, P99 {p[4]}" if p[1] is not None
                    else "tick query gave no figure") + f" ({p[0]})"

        self.note("cost", "PASS", f"{len(self.readers)} parts, {self.plan.mean:.1f} commands a tick on average, "
                  f"{self.plan.peak} in the busiest. Sprints of {n} ticks, milliseconds a tick: loop running "
                  f"{ms(times[True])}; stopped {ms(times[False])}. The loop costs {on - off:.3f} ms a tick: "
                  f"{each:.1f} microseconds a command",
                  [f"at that price the map's limits come to: {MK.MEAN:g} commands a tick on average "
                   f"{MK.MEAN * each / 1000.0:.3f} ms, {MK.PEAK} in the busiest tick {MK.PEAK * each / 1000.0:.3f} ms "
                   f"(a tick has 50 ms)" + (f"; this scene's own limits are {book.mean:g} and {book.peak}"
                                             if (book.peak, book.mean) != (MK.PEAK, MK.MEAN) else ""),
                   f"at the game's normal pace, loop running: {pace(paces[True])}",
                   f"at the game's normal pace, loop stopped: {pace(paces[False])}"])

    def ended(self, other, canvas, namespace="c164art"):
        """Another scene's loop ran in this world before this scene's was started: it has ended
        itself, nothing of it is queued and its heartbeat does not beat."""
        s = self.server
        plan = MK._plan(canvas, other, (0, 0, 0), namespace)
        holder = f"#{other}"
        if plan is None or s.score(holder) is None:
            self.note("ended", "-", f"the loop of {other} never ran in this world: nothing to see")
            return
        s.put(holder, 5)
        s.wait(plan.chains[0].cycle + 3)
        beat = s.score(holder)
        names = [f"{plan.base}/c{chain.cycle}/{k}" for chain in plan.chains for k in range(len(chain.files))]
        left = sum(1 for name in names if "Removed" in s.ask(f"schedule clear {name}"))
        self.note("ended", "PASS" if beat == 5 and not left else "FAIL",
                  f"the loop of {other}, which ran in this world before this scene was started: "
                  + ("its heartbeat does not beat" if beat == 5 else "its heartbeat still beats")
                  + (f", none of its {len(names)} chain functions is queued" if not left
                     else f", {left} of its {len(names)} chain functions were still queued")
                  + f" ({MK.RUN} is {s.score(MK.RUN)}, this scene's is {self.number})")

    # ---- the run ----
    def run(self, checks):
        """checks: [(its name in the report, the check, seconds it may need)]. Returns the exit code."""
        code = 0
        try:
            for name, check, need in checks:
                if self.left() < need + SPARE:
                    self.note(name, "not done", f"{self.left():.0f} s of the script's time are left, "
                              f"this check may need {need}")
                    continue
                check()
        except Stuck as stuck:
            self.out(f"stopped: {stuck}")
            code = 2
        except (OSError, ConnectionError) as lost:
            self.out(f"stopped: the connection to the server: {lost}")
            return 2
        except Exception:
            self.out("stopped: the script itself failed\n" + traceback.format_exc())
            code = 2
        finally:
            try:
                self._put_back()
                if not self.leave and self.server.score(MK.RUN) != self.number:
                    self.start()
                    self.out(f"{'':<18} the loop is started again, as the script found it")
            except Exception as e:          # the report is worth more than a clean ending
                self.out(f"putting things back failed: {type(e).__name__}: {e}")
                code = code or 2
        failed = [check for check, status, _text in self.rows if status == "FAIL"]
        passed = sum(1 for _check, status, _text in self.rows if status == "PASS")
        undone = [check for check, status, _text in self.rows if status == "not done"]
        self.out(f"result: {'FAIL (' + ', '.join(failed) + ')' if failed else 'PASS' if code == 0 else 'NOT FINISHED'}; "
                 f"{passed} checks passed" + (f", not done: {', '.join(undone)}" if undone else "")
                 + f"; {self.server.asked} commands in {self.server.now() - self.began:.0f} s")
        return 1 if failed else code


def connect(argv=None, what=""):
    """The arguments the trip gives a scene's script, and the server they name."""
    ap = argparse.ArgumentParser(description=what, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pw-file", required=True, help="the file that holds the server's RCON password")
    ap.add_argument("--port", type=int, default=25598)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--origin", type=int, nargs=3, required=True, metavar=("X", "Y", "Z"),
                    help="where the scene stands")
    ap.add_argument("--seconds", type=float, default=270.0, help="what the script may take (the trip allows 300)")
    args = ap.parse_args(argv)
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.normpath(os.path.join(here, "..", "..", "..", "..", "tools")))
    from rcon import Rcon
    try:
        with open(args.pw_file) as fh:
            secret = fh.read().strip()
        return args, Server(Rcon(args.host, args.port, secret, timeout=60.0))
    except (OSError, ConnectionError) as e:     # PermissionError, a login that is turned down, is an OSError
        print(f"stopped: the server's console is not reached ({type(e).__name__}: {e})")
        print("result: NOT FINISHED; 0 checks passed; 0 commands in 0 s")
        raise SystemExit(2)
