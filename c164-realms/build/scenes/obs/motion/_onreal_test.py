"""The real-machine scripts against _kit_test's game, without the game (from build/):

    python -m scenes.obs.motion._onreal_test

Not a work package (the name starts with "_"). _kit_test.py plays the written functions back the
way it understands the game; this file puts a console in front of that game. The commands
_onreal.py types are answered in the words of the game's language file (26.3, en_us.json), time
goes on while a script waits, a /reload takes a few ticks and runs the load functions, and the
scene's entities are let go when nobody is near and nothing is force-loaded.

It answers one thing: do the checks pass on a loop that works as _kit_test understands it, and do
they fail on a world that is broken on purpose. What the game does is for the real machine to say.
"""
import argparse
import contextlib
import importlib
import io
import json
import math
import os
import re
import shutil
import struct
import tempfile

from . import _kit as MK
from . import _kit_test as T
from . import _onreal as R

_SELECTOR = re.compile(r"@e\[type=([a-z_:]+),x=(-?\d+\.\d+),y=(-?\d+\.\d+),z=(-?\d+\.\d+),distance=\.\.(\d+\.\d+),"
                       r"tag=([A-Za-z0-9_.+\-]+),limit=1\]\Z")
_WORLD = "minecraft:overworld"


def _f32(v):
    return struct.unpack("f", struct.pack("f", float(v)))[0]


def _java(v):
    """A 32-bit number as the game prints it: the shortest text that reads back the same, with an
    exponent below a thousandth."""
    v = _f32(v)
    if v == 0.0:
        return "0.0"
    for digits in range(1, 10):
        x = float(f"{v:.{digits}g}")
        if _f32(x) == v:
            break
    if 1e-3 <= abs(x) < 1e7:
        return repr(x)
    m, _, e = f"{x:.8e}".partition("e")
    m = m.rstrip("0")
    return f"{m + '0' if m.endswith('.') else m}E{int(e)}"


def _floats(values):
    return "[" + ", ".join(_java(v) + "f" for v in values) + "]"


def _unit(q):
    n = math.sqrt(sum(c * c for c in q))
    return tuple(c / n for c in q)


class _World(T._Game):
    """_kit_test's game with a console, a clock and chunks."""

    TICK = 0.05                 # seconds a tick at the game's normal pace
    TYPING = 0.0004             # seconds a command takes to come and be answered
    BASE, EACH = 0.4, 0.02      # milliseconds a tick costs, and each command run in it
    RELOADS = 1.3               # seconds a /reload holds the server: no tick, and no answer, until it is through

    def __init__(self, pack, breaks=()):
        super().__init__(pack)
        self.pack, self.breaks = pack, set(breaks)
        self.clock = 0.0            # seconds since this world's script began
        self.next = self.TICK       # when the next tick comes
        self.due = self.TICK        # when it was due: a game that is behind runs its ticks one upon the other
        self.sprint = 0             # ticks left of a sprint
        self.reloading = None       # the tick before which the load functions run
        self.players = {"C164Cam": [0.0, 0.0, 0.0, 0.0, 0.0]}
        self.modes = {}             # a player's game mode when he is not a spectator
        self.frozen = False         # tick freeze
        self.forced = set()
        self.home = None            # the chunks the placed entities stand in
        self.held = []              # the entities, while their chunks are let go
        self.apart = 0              # ticks since the chunks were last wanted
        self.costs = []
        self.index = {}
        self.typed = []
        self.uuid = 7

    # ---- time ----
    def sleep(self, seconds):
        self.clock += seconds
        while self.clock >= self.next:
            self._tick()
            cost = (self.BASE + self.EACH * self.ran.get(self.tick, 0)) / 1000.0
            self.costs = (self.costs + [cost * 1000.0])[-100:]
            if self.sprint:
                self.sprint -= 1
                self.next += cost
                self.due = self.next
            else:
                self.due += self.TICK
                self.next = max(self.next + cost, self.due)

    def now(self):
        return self.clock

    def wall(self):
        return 1.79e9 + self.clock

    def down(self, seconds):
        """The server is down for so long: no tick, the world as it was saved."""
        self.clock += seconds
        self.next = self.due = self.clock + self.TICK

    def _tick(self):
        if self.reloading is not None and self.tick + 1 >= self.reloading:
            self.reloading = None
            if "reload loses the queue" in self.breaks:
                self.queue.clear()
            path = os.path.join(self.pack, "data", "minecraft", "tags", "function", "load.json")
            with open(path, encoding="utf-8") as fh:
                for value in json.load(fh)["values"]:
                    if "load is not run" not in self.breaks:
                        self.call(value["id"])  # before this tick's game time is counted up
        self.run(1)
        self._chunks()

    # ---- chunks ----
    def place(self, canvas, at):
        """The scene stands, its chunks are force-loaded and the camera is before it, as the
        driver and the shots leave them."""
        shown = super().place(canvas, at)
        self.home = {(int(e.pos[0]) >> 4, int(e.pos[2]) >> 4) for e in self.shown}
        self.forced |= self.home
        x, y, z = (sum(e.pos[i] for e in shown) / len(shown) for i in range(3))
        for spot in self.players.values():
            spot[:3] = [x, y, z + 6.0]
        self._index()
        return shown

    def _index(self):
        self.index = {}
        for e in self.shown:
            for tag in e.tags:
                self.index.setdefault((tag,) + tuple(round(v, 2) for v in e.pos), []).append(e)

    def _chunks(self):
        if self.home is None:
            return
        near = any(abs(spot[0] - (16 * x + 8)) < 200 and abs(spot[2] - (16 * z + 8)) < 200
                   for spot in self.players.values() for x, z in self.home)
        wanted = near or bool(self.home & self.forced) or "chunks stay" in self.breaks
        self.apart = 0 if wanted else self.apart + 1
        if self.apart > 8 and self.shown:
            self.held, self.shown = self.shown, []
            self._index()
        elif wanted and self.held:
            self.shown, self.held = self.held, []
            self._index()

    def _find(self, kind, spot, reach, tag):
        found = [e for e in self.index.get((tag,) + tuple(round(v, 2) for v in spot), ())
                 if e.type == kind and math.dist(e.pos, spot) <= reach]
        assert len(found) <= 1, f"the selector finds {len(found)} entities"
        return found[0] if found else None

    def _run(self, line):
        kind, g = self._read(line)
        if kind == "guard" and "the guard lets everything by" in self.breaks:
            return False
        if kind != "merge":
            return super()._run(line)
        kind_of, spot, reach, tag, what = g
        e = self._find(kind_of, spot, reach, tag)
        if e is None:
            self.missed.append(line)
        elif "a step is lost" in self.breaks and tag == "m.mot_disc" and self.tick % 7 == 0:
            pass
        elif isinstance(what, str):
            e.models.append((self.tick, what))
        else:
            e.given(self.tick + self.late(self.tick), what[0], what[1])
        return False

    # ---- the console ----
    def command(self, text):
        self.sleep(self.TYPING)
        self.typed.append(text)
        words = text.split(" ")
        if text == "time query gametime":
            return f"The game time is {self.tick} tick(s)"
        if text == "list":
            return f"There are {len(self.players)} of a max of 20 players online: {', '.join(self.players)}"
        if text == "reload":            # the server thread waits for the reload: the answer comes when it is through
            self.clock += self.RELOADS
            self.next = max(self.next, self.clock)
            self.reloading = self.tick + 1
            return "Reloading!"
        if words[:2] == ["tick", "query"]:
            mean = sum(self.costs) / max(1, len(self.costs))
            ranked = sorted(self.costs) or [0.0]
            per = " ".join(f"P{p}: {ranked[min(len(ranked) - 1, len(ranked) * p // 100)]:.1f}ms" for p in (50, 95, 99))
            if self.frozen:
                return ("The game is frozenTarget tick rate: 20.0 per second.\n"
                        f"Average time per tick: {mean:.1f}ms (Target: 50.0ms)Percentiles: {per}. Sample: {len(self.costs)}")
            if self.sprint:
                return ("The game is sprintingTarget tick rate: 20.0 per second (ignored, reference only).\n"
                        f"Average time per tick: {mean:.1f}msPercentiles: {per}. Sample: {len(self.costs)}")
            return ("The game is running normallyTarget tick rate: 20.0 per second.\n"
                    f"Average time per tick: {mean:.1f}ms (Target: 50.0ms)Percentiles: {per}. Sample: {len(self.costs)}")
        if words[:2] == ["tick", "sprint"]:
            if "no sprint" in self.breaks:
                return "Unknown or incomplete command, see below for error"
            self.sprint = int(words[2])
            self.next = self.clock
            return "The game is sprinting"
        if words[:3] == ["scoreboard", "objectives", "add"]:
            if words[3] in self.objectives:
                return "An objective already exists by that name"
            self.objectives.add(words[3])
            return f"Created new objective [{words[3]}]"
        if words[:3] == ["scoreboard", "players", "get"]:
            holder, objective = words[3], words[4]
            if objective not in self.objectives:
                return f"Unknown scoreboard objective '{objective}'"
            if (holder, objective) not in self.scores:
                return f"Can't get value of {objective} for {holder}; none is set"
            return f"{holder} has {self.scores[(holder, objective)]} [{objective}]"
        if words[:3] == ["scoreboard", "players", "set"]:
            holder, objective, value = words[3], words[4], int(words[5])
            if objective not in self.objectives:
                return f"Unknown scoreboard objective '{objective}'"
            self.scores[(holder, objective)] = value
            return f"Set [{objective}] for {holder} to {value}"
        if words[0] == "function":
            before = sum(self.ran.values())
            self.call(words[1])
            return f"Executed {sum(self.ran.values()) - before} command(s) from function '{words[1]}'"
        if words[:2] == ["schedule", "clear"]:
            if self.queue.pop(words[2], None) is None:
                return f"No schedules with ID {words[2]}"
            return f"Removed 1 schedule(s) with ID {words[2]}"
        if words[:2] == ["forceload", "query"]:
            chunks = ", ".join(f"[{x}, {z}]" for x, z in sorted(self.forced))
            if not self.forced:
                return f"No force loaded chunks were found in {_WORLD}"
            if len(self.forced) == 1:
                return f"A force loaded chunk was found in {_WORLD} at: {chunks}"
            return f"{len(self.forced)} force loaded chunks were found in {_WORLD} at: {chunks}"
        if words[0] == "forceload" and words[1] in ("add", "remove"):
            x0, z0, x1, z1 = (int(v) >> 4 for v in (words[2:6] if len(words) > 4 else words[2:4] * 2))
            chunks = {(x, z) for x in range(min(x0, x1), max(x0, x1) + 1) for z in range(min(z0, z1), max(z0, z1) + 1)}
            changed = chunks - self.forced if words[1] == "add" else chunks & self.forced
            if not changed:
                return ("No chunks were marked for force loading" if words[1] == "add"
                        else "No chunks were removed from force loading")
            self.forced = self.forced | chunks if words[1] == "add" else self.forced - chunks
            return (f"Marked {len(changed)} chunks in {_WORLD} from [{x0}, {z0}] to [{x1}, {z1}] to be force loaded"
                    if words[1] == "add" else
                    f"Unmarked {len(changed)} chunks in {_WORLD} from [{x0}, {z0}] to [{x1}, {z1}] for force loading")
        if words[0] == "tp":
            spot = self.players[words[1]]
            spot[:len(words) - 2] = [float(v) for v in words[2:]]
            return f"Teleported {words[1]} to {', '.join(words[2:5])}"
        if words[:3] == ["data", "get", "entity"]:
            return self._data(words[3], " ".join(words[4:]))
        raise AssertionError(f"a command this test's console does not know: {text}")

    def _data(self, target, path):
        if target in self.players:
            spot = self.players[target]
            if path == "Pos":
                return f"{target} has the following entity data: [" + ", ".join(f"{v!r}d" for v in spot[:3]) + "]"
            if path == "Rotation":
                return f"{target} has the following entity data: {_floats(spot[3:])}"
            if path == "playerGameType":
                return f"{target} has the following entity data: {self.modes.get(target, 3)}"
            raise AssertionError(f"a path of a player this test's console does not know: {path}")
        m = _SELECTOR.match(target)
        assert m, f"a selector this test's console does not know: {target}"
        e = self._find(m.group(1), tuple(float(m.group(k)) for k in (2, 3, 4)), float(m.group(5)), m.group(6))
        if e is None:
            return "No entity was found"
        said = "Item Display has the following entity data: "
        if path == "transformation":
            left, right, scale, shift = e.ways[-1][1]
            return said + (f"{{left_rotation: {_floats(_unit(left))}, right_rotation: {_floats(_unit(right))}, "
                           f"scale: {_floats(scale)}, translation: {_floats(shift)}}}")
        if path == 'item.components."minecraft:item_model"':
            return said + f'"{e.models[-1][1]}"'
        if path == "UUID":
            return said + f"[I; {self.uuid}, -2, 3, {self.shown.index(e)}]"
        raise AssertionError(f"a path this test's console does not know: {path}")


def _bench(breaks=(), canvas=None, name="t", seconds=270.0):
    """A world in which _kit_test's small board stands and runs, and the bench to check it with.
    Returns (bench, world, what the bench printed, the folder to remove afterwards)."""
    c, _parts = T._board() if canvas is None else canvas
    tmp = tempfile.mkdtemp(prefix="c164-motion-real-")
    assert MK.write(c, tmp, name, at=T.AT) == [f"function c164art:{name}-motion/start"]
    world = _World(tmp, breaks)
    world.place(c, T.AT)
    world.call(f"c164art:{name}-motion/start")
    world.sleep(7.3)
    said = []
    bench = R.Bench(R.Server(world, world.sleep, world.now, world.wall), c, name, T.AT, seconds=seconds, out=said.append)
    return bench, world, said, tmp


def _all(bench):
    return [("ready", bench.ready, 5), ("record", bench.kept, 12), ("alive", bench.alive, 22),
            ("steps", bench.every_step, 20), ("reload", bench.reload_alive, 25), ("broken", bench.broken, 30),
            ("takeover", bench.takeover, 15), ("unload", bench.unloaded, 60), ("stop", bench.stopped, 30),
            ("start", bench.started, 12)]


def _status(bench):
    return {check: status for check, status, _text in bench.rows}


def test_numbers():
    """Numbers as the game prints them are read back as they were written."""
    assert _java(0.0) == "0.0" and _java(1.0) == "1.0" and _java(-0.5) == "-0.5"
    assert _java(0.70710678) == "0.70710677" and _java(0.0001) == "1.0E-4" and _java(-0.00025) == "-2.5E-4"
    assert R._numbers("0.0f, 1.0E-4f, -2.5E-4f, 0.70710677f") == (0.0, 1.0e-4, -2.5e-4, 0.70710677)
    assert R._numbers("100.5d, 70.0d, -190.0d") == (100.5, 70.0, -190.0)


def test_reader():
    """Which steps a reading can be, and for how long each step is due."""
    c, parts = T._board()
    plan = MK._plan(c, "t", T.AT, "c164art")
    wheel = R.Reader(plan, parts["wheel"], "wheel")
    assert wheel.due == [list(range(0, 12)), list(range(12, 24)), list(range(24, 36)), list(range(36, 48))]
    assert wheel.longest == 12 and wheel.first == 0
    late = R.Reader(plan, parts["pendulum_b"], "pendulum_b")       # half a swing late: its steps wrap round
    assert late.first == 0 and sorted(d for due in late.due for d in due) == list(range(40))
    slider = R.Reader(plan, parts["slider"], "slider")
    assert slider.due == [list(range(0, 60)), list(range(60, 120))] and slider.longest == 60
    left, shift = parts["slider"].pose(0.0, 0.0)
    right, scale = parts["slider"].right, parts["slider"].scale
    assert slider.steps((left, right, scale, shift)) == {1, R.REST}        # its second step ends where it was placed
    assert slider.steps((tuple(-v for v in left), right, scale, shift)) == {1, R.REST}      # q and -q are one turn
    assert slider.steps((left, right, scale, (9.0, 9.0, 9.0))) == set()
    assert slider.placed((left, right, scale, shift)) and not slider.placed((left, right, (2.0, 1.0, 1.0), shift))
    lamp = R.Reader(plan, parts["lamp"], "lamp")
    assert lamp.steps("c164:mot_lamp") == {0, R.REST} and lamp.steps("c164:mot_lamp_dark") == {1}


def test_clock():
    """A chain's clock closes in on the tick its first function ran on, and a reading that cannot
    be runs it empty."""
    c, parts = T._board()
    plan = MK._plan(c, "t", T.AT, "c164art")
    wheel = R.Reader(plan, parts["wheel"], "wheel")
    clock = R.Clock(next(ch for ch in plan.chains if ch.cycle == 48))
    assert clock.see(wheel, {0}, 1000, 1000) and len(clock.ticks) == 12
    assert clock.see(wheel, {0}, 1003, 1003) and len(clock.ticks) == 9
    assert clock.see(wheel, {1}, 1004, 1004) and clock.ticks == {(1004 - 12) % 48}
    assert not clock.see(wheel, {3}, 1005, 1005) and clock.ticks == {(1004 - 12) % 48}
    assert not clock.agrees(wheel, {R.REST}, 1006, 1006) and not clock.agrees(wheel, set(), 1006, 1006)
    # a start: the first function is due 1 + offset ticks later, a tick to either side let by
    clock.started(2000, 2001)
    assert clock.ticks == {(g + 1 + clock.offset) % 48 for g in (1999, 2000, 2001, 2002)}
    assert clock.agrees(wheel, {R.REST}, 2001 + clock.offset, 2001 + clock.offset)     # not set off yet
    assert not clock.agrees(wheel, {R.REST}, 2010 + clock.offset, 2010 + clock.offset)
    assert clock.see(wheel, {R.REST}, 2000 + clock.offset, 2000 + clock.offset) and len(clock.ticks) == 4
    assert clock.see(wheel, {0}, 2001 + clock.offset, 2001 + clock.offset) and len(clock.ticks) == 2
    assert clock.see(wheel, {0}, 2012 + clock.offset, 2012 + clock.offset)      # still its first step, 11 ticks on
    assert clock.ticks == {(2001 + clock.offset) % 48}
    assert clock.set_off() == [clock.offset, 1 + clock.offset]      # the start itself was known to two ticks
    clock.started(3000, 3000)
    assert clock.see(wheel, {0}, 3001 + clock.offset, 3001 + clock.offset)
    assert clock.see(wheel, {0}, 3012 + clock.offset, 3012 + clock.offset) and clock.set_off() == [1 + clock.offset]
    clock.started(4000, 4000)                                       # a chain that sets off a tick late is told
    assert clock.see(wheel, {R.REST}, 4001 + clock.offset, 4001 + clock.offset)
    assert clock.see(wheel, {0}, 4013 + clock.offset, 4013 + clock.offset) and clock.set_off() == [2 + clock.offset]


def test_real_passes():
    """On a loop that works every check passes, and the world is left as it was found."""
    bench, world, said, tmp = _bench()
    try:
        forced, spots = set(world.forced), {k: list(v) for k, v in world.players.items()}
        code = bench.run(_all(bench))
        status = _status(bench)
        assert code == 0 and said[-1].startswith("result: PASS; 9 checks passed"), "\n".join(said)
        assert status.pop("record") == "-" and set(status.values()) == {"PASS"}, status
        assert world.forced == forced and world.shown and not world.held
        assert all(abs(a - b) < 1e-3 for name in spots for a, b in zip(world.players[name], spots[name]))
        assert world.scores[("#run", MK.OBJECTIVE)] == bench.number and not world.sprint
        assert sum(1 for n in world.queue if "/c" in n) == len(bench.plan.chains)
        assert not world.lost and world.clock < 200.0, world.clock
        assert any(t.startswith("tp C164Cam ") for t in world.typed) and "reload" in world.typed
        # a second run in the same world, after the server was down: the loop went on where it was
        world.down(900.0)
        world.sleep(33.3)
        said.clear()
        again = R.Bench(bench.server, T._board()[0], "t", T.AT, out=said.append)
        assert again.run(_all(again)) == 0 and _status(again)["record"] == "PASS", "\n".join(said)
        assert "the server was down" in "\n".join(said)
        # ... and after the loop was started anew behind the script's back, the record does not fit
        world.sleep(1.15)
        world.call("c164art:t-motion/start")
        world.sleep(20.0)
        said.clear()
        third = R.Bench(bench.server, T._board()[0], "t", T.AT, out=said.append)
        assert third.run(_all(third)) == 1 and _status(third)["record"] == "FAIL", "\n".join(said)
        assert [c for c, s in _status(third).items() if s == "FAIL"] == ["record"], _status(third)
        # ... and a scene that was placed anew has no record to be held to
        world.uuid = 8
        said.clear()
        fourth = R.Bench(bench.server, T._board()[0], "t", T.AT, out=said.append)
        fourth.ready()
        fourth.kept()
        assert _status(fourth) == {"ready": "PASS", "record": "-"}, "\n".join(said)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_real_reload_on_a_beat():
    """Load that runs on the very tick of a heartbeat is hidden from the script: it types /reload
    once more, half a beat off, and does not take the loop for broken."""
    twice = 0
    for shift in range(10):                 # the board's quickest chain beats every 10 ticks
        bench, world, said, tmp = _bench()
        try:
            bench.ready()
            bench.alive(60)
            world.sleep(shift * world.TICK)
            bench.reload_alive()
            assert _status(bench)["reload"] == "PASS", (shift, "\n".join(said))
            twice += bench.retyped
            assert bench.retyped == ("typed again" in "\n".join(said))
            assert bench.patience < R.RELOAD
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    assert 1 <= twice <= 2, twice
    # ... and a pack whose load function is not run at all is told, by three checks
    code, status, said = _fails(["load is not run"], (["reload", "broken", "stop"], "FAIL"))
    assert code == 1 and [c for c, s in status.items() if s == "FAIL"] == ["reload", "broken", "stop"], status
    assert "typed again" in "\n".join(said)


def test_real_reload_after_a_beat():
    """With the quickest chain's clock known, /reload is typed just after a beat: load is seen at
    the first go whenever the check begins, and most of a cycle before the next beat."""
    from scenes.obs_mot_loop import build
    for shift in (0, 7, 13, 21, 29, 36, 39):        # the beat board's quickest chain beats every 40 ticks
        bench, world, said, tmp = _bench(canvas=(build(), None), name="obs_mot_loop")
        try:
            bench.ready()
            bench.alive(100)
            assert len(bench.clocks[40].ticks) == 1, bench.clock_widths()
            world.sleep(shift * world.TICK)
            bench.reload_alive()
            text = "\n".join(said)
            assert _status(bench)["reload"] == "PASS" and not bench.retyped, (shift, text)
            assert world.typed.count("reload") == 1 and abs(bench.held - world.RELOADS) < 0.01
            m = re.search(r"the heartbeat was back (\d+) to (\d+) ticks after that", text)
            assert m and int(m.group(1)) >= 20, (shift, text)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def test_real_nobody_falls():
    """A player who is not a spectator is not sent out over the void: the unloading is left
    undone and nothing is changed."""
    bench, world, said, tmp = _bench()
    try:
        bench.ready()
        world.modes["C164Cam"] = 1
        before, forced, spot = len(world.typed), set(world.forced), list(world.players["C164Cam"])
        bench.unloaded()
        assert _status(bench)["unload"] == "not done" and "not a spectator" in "\n".join(said)
        assert not any(t.startswith(("tp ", "forceload add", "forceload remove")) for t in world.typed[before:])
        assert world.forced == forced and world.players["C164Cam"] == spot and not bench.undo
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _fails(breaks, wanted, checks=None):
    bench, world, said, tmp = _bench(breaks)
    try:
        code = bench.run([c for c in _all(bench) if checks is None or c[0] in checks])
        status = _status(bench)
        assert {c for c, s in status.items() if s == wanted[1]} >= set(wanted[0]), (breaks, status, "\n".join(said))
        assert world.scores[("#run", MK.OBJECTIVE)] == bench.number, "the loop was not left running"
        return code, status, said
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_real_fails():
    """Worlds that are broken on purpose: the check that looks at what is broken fails."""
    code, status, _ = _fails(["reload loses the queue"], (["reload"], "FAIL"), ("ready", "alive", "reload"))
    assert code == 1 and status["alive"] == "PASS", status
    code, status, _ = _fails(["the guard lets everything by"], (["takeover"], "FAIL"))
    assert code == 1 and status["alive"] == "PASS", status
    code, status, said = _fails(["a step is lost"], (["alive"], "FAIL"), ("ready", "alive"))
    assert code == 1 and "mot_disc" in "\n".join(said), said
    code, status, _ = _fails(["chunks stay"], (["unload"], "not done"), ("ready", "alive", "unload"))
    assert code == 0, status


def test_real_not_running():
    """A loop that is not the world's when the script begins is a failure, and the script goes on."""
    bench, world, said, tmp = _bench()
    try:
        world.command("function c164art:t-motion/stop")
        code = bench.run(_all(bench)[:3])
        assert code == 1 and _status(bench) == {"ready": "FAIL", "record": "-", "alive": "PASS"}, "\n".join(said)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_real_cannot_begin():
    """A game that is frozen, a scene that does not stand where the script was told: the script
    says so and stops; it types nothing that changes the world, and starts no loop."""
    harmless = ("time query gametime", "tick query", "list")
    for case in ("frozen", "elsewhere", "elsewhere and stopped"):
        bench, world, said, tmp = _bench()
        try:
            if case == "frozen":
                world.frozen = True
            else:
                bench = R.Bench(bench.server, T._board()[0], "t", (T.AT[0] + 64, T.AT[1], T.AT[2]), out=said.append)
            if case == "elsewhere and stopped":
                world.command("function c164art:t-motion/stop")
            before = len(world.typed)
            code = bench.run(_all(bench))
            text = "\n".join(said)
            assert code == 1 and _status(bench) == {"ready": "FAIL"}, (case, text)
            assert ("the game is frozen" if case == "frozen" else "are not found") in text, (case, text)
            assert "result: FAIL (ready); 0 checks passed" in said[-1], said[-1]
            typed = [t for t in world.typed[before:] if t not in harmless]
            assert all(t.startswith(("data get entity ", "scoreboard players get ")) for t in typed), (case, typed)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def test_real_out_of_time():
    """A script that runs out of its time says what it did not do and puts things back."""
    bench, world, said, tmp = _bench(seconds=45.0)
    try:
        code = bench.run(_all(bench))
        status = _status(bench)
        assert code == 0 and "not done" in status.values() and "FAIL" not in status.values(), status
        assert world.clock < 7.3 + 45.0 and world.scores[("#run", MK.OBJECTIVE)] == bench.number
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_real_cost():
    """The cost of a loop is read off sprints: the test's world charges 0.02 ms a command."""
    bench, world, said, tmp = _bench()
    try:
        bench.ready()
        bench.cost(rounds=2, seconds=0.5)
        text = "\n".join(said)
        each = re.search(r"([\d.]+) microseconds a command", text)
        assert _status(bench)["cost"] == "PASS" and each and abs(float(each.group(1)) - 20.0) < 0.5, text
        assert world.scores[("#run", MK.OBJECTIVE)] == bench.number
        world.breaks.add("no sprint")
        bench.cost(rounds=1, seconds=0.5)
        assert bench.rows[-1][1] == "not done", bench.rows[-1]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_real_ended():
    """A second scene's start ends the first scene's loop: the second scene's script sees it."""
    bench, world, said, tmp = _bench()
    try:
        other = T._board()
        assert MK.write(other[0], tmp, "u", at=T.AT) == ["function c164art:u-motion/start"]
        second = R.Bench(bench.server, other[0], "u", T.AT, out=said.append)
        world.command("function c164art:u-motion/start")
        world.sleep(5.0)
        second.ended("t", T._board()[0])
        assert second.rows[-1][1] == "PASS", second.rows
        second.ended("never", T._board()[0])
        assert second.rows[-1][1] == "-", second.rows
        world.command("function c164art:t-motion/start")        # t's loop is the world's again and runs
        world.sleep(5.0)
        second.ended("t", T._board()[0])
        assert second.rows[-1][1] == "FAIL", second.rows
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _script(world, scene, at):
    """Run a scene's own script against the world, as the trip does. Returns (exit code, what it printed)."""
    script = importlib.import_module(f"scenes.{scene}.onreal")
    args = argparse.Namespace(origin=list(at), seconds=270.0)
    connect, R.connect = R.connect, lambda argv=None, what="": (args, R.Server(world, world.sleep, world.now, world.wall))
    said = io.StringIO()
    try:
        with contextlib.redirect_stdout(said):
            code = script.main([])
    finally:
        R.connect = connect
    return code, said.getvalue()


def test_scene_scripts(show=False):
    """The two scenes' own scripts, on the scenes as they are built, one after the other in one
    world as a trip with --apart has them: the beat board first, then the load scene, whose start
    takes the world over."""
    tmp = tempfile.mkdtemp(prefix="c164-motion-real-")
    rounds, R.ROUNDS, sprint, R.SPRINT = R.ROUNDS, 1, R.SPRINT, 0.3
    try:
        world = _World(tmp)
        for scene, at in (("obs_mot_loop", (22000, 200, 0)), ("obs_mot_load", (23000, 200, 0))):
            canvas = importlib.import_module(f"scenes.{scene}").build()
            assert MK.write(canvas, tmp, scene, at=at) == [f"function c164art:{scene}-motion/start"]
            world.forced = set()                # the trip lets go what the scene before it kept loaded
            world.place(canvas, at)
            world.command(f"function c164art:{scene}-motion/start")
            world.sleep(31.7)
            code, said = _script(world, scene, at)
            if show:
                print(said)
            assert code == 0 and "\nresult: PASS" in said and " FAIL " not in said, said
            assert " not done " not in said and not world.lost, said
        assert "ended     PASS" in said and "cost      PASS" in said, said
    finally:
        R.ROUNDS, R.SPRINT = rounds, sprint
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["--show"]:              # what the two scripts print, on this file's world
        test_scene_scripts(show=True)
        sys.exit(0)
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("ok", test.__name__)
    print(f"{len(tests)} tests passed")
