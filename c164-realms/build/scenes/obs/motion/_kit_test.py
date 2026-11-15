"""The arithmetic of _kit.py against itself, without the game (from build/):

    python -m scenes.obs.motion._kit_test

Not a work package (the name starts with "_"). It answers what can be answered without a client:
a turned part keeps its anchor on the entity and turns the right way round, a connecting rod
stays on its crank pin, the steps are the ones the parts file promises, and the files written are
the files the functions name.

The second half plays the written functions back (the tests named test_play_*): it runs the files
of a small beat board tick by tick, the way this file understands the game, and looks at what a
client would show in between the steps. That is still this file's understanding and not the game:
what the client does with the functions is plan/parts/motion.md section 10.
"""
import bisect
import json
import math
import os
import re
import shutil
import tempfile

from . import _kit as MK


class _Canvas:
    def __init__(self):
        self.entities = []

    def add_entity(self, x, y, z, nbt):
        self.entities.append((x, y, z, nbt))


def _display(name, yaw=0.0, turn=None, scale=(1.0, 1.0, 1.0), anchor=(0.0, 0.0, 0.0)):
    """NBT as artkit.models.display writes it, for a model whose anchor lies `anchor` blocks from
    the middle of its box; turn is (model axis as a vector, degrees)."""
    q = MK._IDENT if turn is None else MK._about(turn[0], turn[1])
    q = (-q[0], q[1], -q[2], q[3])
    flipped = (-anchor[0] * scale[0], anchor[1] * scale[1], -anchor[2] * scale[2])
    t = MK._qrot(q, flipped)
    return {"id": "minecraft:item_display",
            "item": {"id": "minecraft:stick", "count": 1, "components": {"minecraft:item_model": f"c164:{name}"}},
            "transformation": {"left_rotation": list(q), "right_rotation": [0.0, 0.0, 0.0, 1.0],
                               "scale": list(scale), "translation": [-t[0], -t[1], -t[2]]},
            "Rotation": [(180.0 + yaw) % 360.0, 0.0], "Tags": ["c164art"]}


def _world(part, left, shift, m):
    """Where the game shows the model's point m (blocks from the middle of its box), as an offset
    from the entity, in world axes."""
    v = (-m[0] * part.scale[0], m[1] * part.scale[1], -m[2] * part.scale[2])
    p = MK._qrot(left, v)
    x, y, z = (shift[i] + p[i] for i in range(3))
    a = math.radians(-part.yaw)
    c, s = math.cos(a), math.sin(a)
    return (x * c + z * s, y, -x * s + z * c)


def _close(a, b, eps=1e-6):
    return all(abs(a[i] - b[i]) <= eps for i in range(len(a)))


def _last(canvas):
    return canvas.motion.parts[-1]


def test_ticks():
    assert MK._ticks(48, 4) == [0, 12, 24, 36, 48]
    assert MK._ticks(40, 8) == [0, 5, 10, 15, 20, 25, 30, 35, 40]
    assert MK._ticks(10, 3) == [0, 3, 7, 10]
    assert MK._num(87) == "87.0" and MK._num(79.5) == "79.5" and MK._num(-0.00001) == "0.0"
    assert MK._floats((0.0, -0.5, 1.0)) == "[0.0f,-0.5f,1.0f]"


def test_anchor_stays():
    """Whatever the yaw, the turns and the scale: the anchor stays on the entity and a point on the
    axis does not move."""
    c = _Canvas()
    anchor = (0.3, -0.2, 0.5)
    c.add_entity(4.5, 70.0, -2.5, _display("mot_a", yaw=37.0, turn=((0.6, 0.0, 0.8), 25.0), scale=(1.0, 2.0, 0.5),
                                           anchor=anchor))
    MK.spin(c, "y", 240)
    part = _last(c)
    on_axis = (anchor[0], anchor[1] + 1.0, anchor[2])
    rest = _world(part, part.left, part.shift, on_axis)
    assert _close(_world(part, part.left, part.shift, anchor), (0.0, 0.0, 0.0))
    for _tick, _ticks, turn, slide in part.steps:
        left, shift = part.pose(turn, slide)
        assert _close(_world(part, left, shift, anchor), (0.0, 0.0, 0.0)), turn
        assert _close(_world(part, left, shift, on_axis), rest), turn


def test_right_handed():
    """Placed with yaw 0 and no turns, the model's axes are the world's: a quarter turn about "y"
    takes what points east to the north (counter-clockwise seen from above)."""
    c = _Canvas()
    c.add_entity(0.5, 64.0, 0.5, _display("mot_b"))
    MK.spin(c, "y", 48)
    part = _last(c)
    left, shift = part.pose(90.0, 0.0)
    assert _close(_world(part, left, shift, (1.0, 0.0, 0.0)), (0.0, 0.0, -1.0))
    assert _close(part.local("x"), part.local((1, 0, 0)))
    c.add_entity(2.5, 64.0, 0.5, _display("mot_c", yaw=90.0))
    MK.spin(c, "x", 48)
    part = _last(c)
    assert _close(part.local("x"), part.local((0, 0, 1)))      # yaw 90 points the model's +x south
    left, shift = part.pose(90.0, 0.0)
    assert _close(_world(part, left, shift, (0.0, 0.0, -1.0)), (0.0, 1.0, 0.0))    # east goes up


def test_steps():
    c = _Canvas()
    c.add_entity(0.5, 64.0, 0.5, _display("mot_wheel", yaw=90.0, scale=(2.0, 2.0, 2.0)))
    MK.spin(c, "x", MK.ENGINE_REV)
    part = _last(c)
    assert [(t, d, round(a, 6)) for t, d, a, _s in part.steps] == [(0, 14, 105.0), (12, 14, 195.0),
                                                                   (24, 14, 285.0), (36, 14, 375.0)]
    assert part.lead == MK.LEAD and part.stray == 0.0
    # a long arm that turns slowly: many small steps, still aimed ahead, within a quarter pixel
    c.add_entity(3.5, 64.0, 0.5, _display("mot_arm", anchor=(1.75, 0.0, 0.0)))
    MK.spin(c, "y", MK.ORRERY["mercury"])
    part = _last(c)
    assert abs(part.arm() - 1.75) < 1e-9
    assert 20 <= len(part.steps) <= 30 and part.lead == MK.LEAD and part.stray <= MK.WOBBLE, len(part.steps)
    # a crank arm that is not a disc, at the engine's speed: 16 steps, not aimed ahead
    c.add_entity(6.5, 64.0, 0.5, _display("mot_crank", anchor=(0.5, 0.0, 0.0)))
    MK.spin(c, "z", MK.ENGINE_REV)
    part = _last(c)
    assert len(part.steps) == 16 and part.lead == 0 and part.stray <= MK.WOBBLE, (len(part.steps), part.lead)
    # too fast for an arm: refused, with the reason
    c.add_entity(9.5, 64.0, 0.5, _display("mot_fast", anchor=(1.75, 0.0, 0.0)))
    try:
        MK.spin(c, "y", 24)
    except ValueError as e:
        assert "too fast" in str(e)
    else:
        raise AssertionError("an arm of 1.75 blocks that turns in 24 ticks was not refused")
    # a pendulum: 8 poses there and back, back in the middle at the end
    c.add_entity(12.5, 64.0, 0.5, _display("mot_pendulum", anchor=(0.0, 0.5, 0.0)))
    MK.swing(c, "z", 5.0, MK.PENDULUM)
    part = _last(c)
    assert len(part.steps) == 8 and part.lead == MK.LEAD
    assert abs(part.steps[1][2] - 5.0 * (math.sin(math.pi / 4) + (1.0 - math.sin(math.pi / 4)) * 7.0 / 5.0)) < 1e-9


def test_rod_on_pin():
    """A rod 4 long on a crank of 1: at every pose its far end is on the crank pin."""
    c = _Canvas()
    c.add_entity(0.5, 64.0, 0.5, _display("mot_rod", anchor=(2.0, 0.0, 0.0)))
    MK.crank(c, (0, 0, 1), (1, 0, 0), 1.0, 4.0, MK.ENGINE_REV, lead=0)
    part = _last(c)
    assert len(part.steps) == 12
    for tick, ticks, tilt, slide in part.steps:
        a = 2.0 * math.pi * (tick + ticks) / MK.ENGINE_REV
        left, shift = part.pose(tilt, slide)
        assert _close(_world(part, left, shift, (-2.0, 0.0, 0.0)), (-5.0 + math.cos(a), math.sin(a), 0.0)), tick
        assert abs(_world(part, left, shift, (2.0, 0.0, 0.0))[1]) < 1e-9          # the crosshead pin keeps to its line
    c.add_entity(0.5, 64.0, 0.5, _display("mot_crosshead"))
    MK.crank(c, (0, 0, 1), (1, 0, 0), 1.0, 4.0, MK.ENGINE_REV, turn=False, lead=0)
    head = _last(c)
    assert [round(s[3], 9) for s in head.steps] == [round(s[3], 9) for s in part.steps]
    assert all(s[2] == 0.0 for s in head.steps) and abs(min(s[3] for s in head.steps) + 2.0) < 1e-9


def test_slide():
    c = _Canvas()
    c.add_entity(0.5, 64.0, 0.5, _display("mot_pen"))
    MK.slide(c, "x", [(0, 0.5, 1200), (1200, 0.0, 1200)], MK.DRUM_REV)
    part = _last(c)
    assert len(part.steps) == 12
    assert part.steps[5] == (1000, 200, 0.0, 0.5) and part.steps[11] == (2200, 200, 0.0, 0.0)
    assert part.steps[0][1] == 202 and abs(part.steps[0][3] - 0.5 / 6.0 * 1.01) < 1e-9
    try:
        MK.slide(c, "x", [(0, 0.5, 10)], 40, model="mot_pen", name="again")
    except ValueError as e:
        assert "registered already" in str(e)
    else:
        raise AssertionError("one entity was registered twice")
    # a move to where the part is already would be the same pose twice: refused, nothing registered
    c.add_entity(2.5, 64.0, 0.5, _display("mot_pen"))
    try:
        MK.slide(c, "x", [(0, 0.5, 10), (20, 0.5, 10), (40, 0.0, 10)], 60)
    except ValueError as e:
        assert "goes nowhere" in str(e)
    else:
        raise AssertionError("a move that goes nowhere was not refused")
    assert MK.registered(c) == (1, 0) and "m.mot_pen" not in c.entities[-1][3]["Tags"]


def test_write():
    c = _Canvas()
    c.add_entity(0.5, 64.0, 0.5, _display("mot_wheel", yaw=90.0))
    MK.spin(c, "x", MK.ENGINE_REV)
    c.add_entity(3.5, 65.0, 0.5, _display("mot_pendulum", anchor=(0.0, 0.5, 0.0)))
    MK.swing(c, "z", 5.0, MK.PENDULUM)
    c.add_entity(6.5, 64.0, 0.5, _display("mot_lamp"))
    MK.blink(c, "mot_lamp_dark", *MK.BLINK)
    MK.sound(c, (3.5, 65.0, 0.5), "minecraft:block.note_block.hat", MK.PENDULUM, at=(10, 30), volume=0.3)
    MK.puff(c, (9.0, 70.0, 0.0), "campfire_signal_smoke", 10, count=0, spread=MK.downwind(), speed=0.07, far=True)
    assert MK.registered(c) == (3, 2)
    assert "m.mot_wheel" in c.entities[0][3]["Tags"]
    status, summary, details = MK.check(c)
    assert status == "PASS", (status, summary, details)
    tmp = tempfile.mkdtemp(prefix="c164-motion-test-")
    try:
        assert MK.write(c, tmp, "t", at=(10, 64, -3)) == ["function c164art:t-motion/start"]
        root = os.path.join(tmp, "data", "c164art", "function", "t-motion")
        have = set()
        for d, _dirs, names in os.walk(root):
            for n in names:
                have.add(os.path.relpath(os.path.join(d, n), root).replace(os.sep, "/")[:-len(".mcfunction")])
        assert {"start", "stop", "rest", "halt", "load", "watch", "c10/0", "c40/0", "c48/0", "c60/0"} <= have, have

        def lines(rel):
            with open(os.path.join(root, *rel.split("/")) + ".mcfunction", encoding="utf-8") as fh:
                return fh.read().splitlines()

        named = set()
        for rel in have:
            for line in lines(rel):
                for word in line.split():
                    if word.startswith("c164art:t-motion/"):
                        named.add(word.split("/", 1)[1])
        assert named <= have, named - have                     # every function a line names is written
        assert have - named == {"stop", "load"}, have - named   # and all but the two entries are named
        first = lines("c10/0")
        assert first[0].startswith("execute unless score #run c164m matches ") and first[0].endswith("t-motion/halt")
        assert first[1] == "schedule function c164art:t-motion/c10/0 10t replace"
        assert first[2] == "scoreboard players set #t c164m 1"
        assert first[3] == "particle minecraft:campfire_signal_smoke 19.0 134.0 -3.0 0.0 1.0 0.1763 0.07 0 force"
        assert any("x=10.5,y=128.0,z=-2.5,distance=..0.05,tag=m.mot_wheel,limit=1]" in ln for ln in lines("c48/0"))
        assert any(ln.startswith("playsound minecraft:block.note_block.hat block @a[x=13.5,y=129.0,z=-2.5,"
                                 "distance=..16.0] 13.5 129.0 -2.5 0.3 1.0") for ln in lines("c40/2"))
        assert sum(1 for ln in lines("rest") if ln.startswith("data merge entity ")) == 3
        with open(os.path.join(tmp, "data", "minecraft", "tags", "function", "load.json"), encoding="utf-8") as fh:
            assert json.load(fh) == {"values": [{"id": "c164art:t-motion/load", "required": False}]}
        assert MK.write(_Canvas(), tmp, "t") == []
        assert not os.path.exists(root)
        assert not os.path.exists(os.path.join(tmp, "data", "minecraft", "tags", "function", "load.json"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_downwind():
    """The wind blows south: a puff that rises leans towards +z, ten degrees off the upright."""
    x, y, z = MK.downwind()
    assert x == 0.0 and y == 1.0 and abs(math.degrees(math.atan2(z, y)) - MK.WIND_LEAN) < 1e-9
    assert _close(MK.downwind(45.0, 2.0), (0.0, 2.0, 2.0))
    assert MK.downwind(0.0) == (0.0, 1.0, 0.0)


def test_same_spot():
    c = _Canvas()
    for _ in range(2):
        c.add_entity(0.5, 64.0, 0.5, _display("mot_wheel"))
        MK.spin(c, "y", 48)
    status, _summary, details = MK.check(c)
    assert status == "FAIL" and "one spot" in details[0], details
    c = _Canvas()
    c.add_entity(0.5, 64.0, 0.5, _display("mot_wheel"))
    MK.spin(c, "y", 48)
    c.add_entity(0.5, 64.0, 0.5, _display("mot_wheel"))
    MK.spin(c, "y", -48, name="mot_wheel.b")
    assert MK.check(c)[0] == "PASS"


# ---- the written functions, played back ---------------------------------------------------------
# As much of the game as the loop leans on, the way this file understands it:
#   - a scheduled function is kept under its name, a later call replaces the earlier, and it runs
#     on the tick it is due, in the order it was queued;
#   - a display entity holds the pose it was given last; a client shows it on the way there from
#     what it showed when the pose arrived, for as many ticks as the pose says: the two turns along
#     their arcs the short way round, shift and scale along straight lines.
# The files are read as they were written, and a line that is none of the kinds below fails the
# test: so this also pins down every kind of line the kit writes.
_ID = r"([a-z0-9_.\-]+:[a-z0-9_.\-/]+)"
_SCORE = r"(#[A-Za-z0-9_.+\-]+) (\w+)"
_LINES = [(kind, re.compile(text + r"\Z")) for kind, text in (
    ("schedule", r"schedule function " + _ID + r" (\d+)t replace"),
    ("clear", r"schedule clear " + _ID),
    ("function", r"function " + _ID),
    ("objective", r"scoreboard objectives add (\w+) dummy"),
    ("set", r"scoreboard players set " + _SCORE + r" (-?\d+)"),
    ("guard", r"execute unless score " + _SCORE + r" matches (-?\d+) run return run function " + _ID),
    ("watch", r"execute if score " + _SCORE + r" matches (-?\d+) unless score " + _SCORE
              + r" matches (-?\d+) run function " + _ID),
    ("let_go", r"execute if score " + _SCORE + r" matches (-?\d+) run scoreboard players set " + _SCORE
               + r" (-?\d+)"),
    ("merge", r"data merge entity @e\[type=([a-z_:]+),x=(-?\d+\.\d+),y=(-?\d+\.\d+),z=(-?\d+\.\d+),"
              r"distance=\.\.(\d+\.\d+),tag=([A-Za-z0-9_.+\-]+),limit=1\] (\{.*\})"),
    ("sound", r"playsound [a-z0-9_.:\-/]+ [a-z]+ @a\[x=-?\d+\.\d+,y=-?\d+\.\d+,z=-?\d+\.\d+,"
              r"distance=\.\.\d+\.\d+\]( -?\d+\.\d+){3} \d+\.\d+ \d+\.\d+"),
    ("puff", r"particle [a-z0-9_.:\-/]+( -?\d+\.\d+){3}( -?\d+\.\d+){3} \d+\.\d+ \d+ (force|normal)"),
)]
_F = r"\[((?:-?\d+\.\d+f,?){%d})\]"
_POSE = re.compile(r"\{start_interpolation:0,interpolation_duration:(\d+),transformation:\{left_rotation:" + _F % 4
                   + r",right_rotation:" + _F % 4 + r",scale:" + _F % 3 + r",translation:" + _F % 3 + r"\}\}\Z")
_SWAP = re.compile(r'\{item:\{components:\{"minecraft:item_model":"([a-z0-9_.\-]+:[a-z0-9_.\-/]+)"\}\}\}\Z')


def _slerp(a, b, u):
    """From the turn a to the turn b the short way round, as the client's library does it."""
    cosom = sum(a[i] * b[i] for i in range(4))
    if 1.0 - abs(cosom) > 1e-9:
        omega = math.acos(abs(cosom))
        s0, s1 = math.sin((1.0 - u) * omega) / math.sin(omega), math.sin(u * omega) / math.sin(omega)
    else:
        s0, s1 = 1.0 - u, u
    if cosom < 0.0:
        s1 = -s1
    return tuple(s0 * a[i] + s1 * b[i] for i in range(4))


def _lerp(a, b, u):
    return tuple(a[i] + (b[i] - a[i]) * u for i in range(len(a)))


class _Shown:
    """A display entity, and what a client shows or showed of it at any moment."""

    def __init__(self, pos, nbt):
        tr = nbt["transformation"]
        self.pos, self.type, self.tags = pos, nbt["id"], set(nbt.get("Tags", ()))
        self.yaw = float(nbt["Rotation"][0])
        self.models = [(float("-inf"), nbt["item"]["components"]["minecraft:item_model"])]
        self.rest = tuple(tuple(float(v) for v in tr[k])
                          for k in ("left_rotation", "right_rotation", "scale", "translation"))
        self.since = [float("-inf")]                # when each pose arrived
        self.ways = [(self.rest, self.rest, 0)]     # (what it showed then, the pose, ticks to get there)

    def model(self, time):
        return [name for since, name in self.models if since <= time][-1]

    def pose(self, time):
        k = bisect.bisect_right(self.since, time) - 1
        was, goal, takes = self.ways[k]
        if takes <= 0 or time >= self.since[k] + takes:
            return goal
        u = (time - self.since[k]) / takes
        return (_slerp(was[0], goal[0], u), _slerp(was[1], goal[1], u),
                _lerp(was[2], goal[2], u), _lerp(was[3], goal[3], u))

    def given(self, time, goal, takes):
        assert time >= self.since[-1], "a pose arrives before the one before it"
        self.ways.append((self.pose(time), goal, takes))
        self.since.append(time)

    def point(self, time, m=(0.0, 0.0, 0.0)):
        """Where the model's point m (blocks from the middle of its box) is shown, in the world."""
        left, right, scale, shift = self.pose(time)
        v = (-m[0], m[1], -m[2]) if self.type == "minecraft:item_display" else m
        v = MK._qrot(right, v)
        v = MK._qrot(left, tuple(v[i] * scale[i] for i in range(3)))
        x, y, z = (shift[i] + v[i] for i in range(3))
        a = math.radians(-self.yaw)
        c, s = math.cos(a), math.sin(a)
        return (self.pos[0] + x * c + z * s, self.pos[1] + y, self.pos[2] - x * s + z * c)


class _Game:
    """The queue, the scoreboard and the display entities of a world with one data pack."""

    def __init__(self, pack, namespace="c164art"):
        self.root = os.path.join(pack, "data", namespace, "function")
        self.files = {}         # function -> its lines, once read
        self.read = {}          # line -> (its kind, its words)
        self.tick = 0
        self.queue = {}         # function -> (the tick it is due, the order it was queued in)
        self.queued = 0
        self.objectives = set()
        self.scores = {}
        self.shown = []
        self.ran = {}           # tick -> commands run in it
        self.calls = []         # (tick, function) of every function run
        self.said = []          # (tick, line) of every sound and puff
        self.lost = []          # functions that were due and are not in the pack
        self.missed = []        # lines whose selector found no entity
        self.late = lambda tick: 0.0    # ticks a client learns of this tick's poses after the tick

    def place(self, canvas, at):
        for x, y, z, nbt in canvas.entities:
            self.shown.append(_Shown((x + at[0], y + at[1], z + at[2]), nbt))
        return self.shown[-len(canvas.entities):]

    def call(self, name):
        if name not in self.files:
            path = os.path.join(self.root, *name.split(":", 1)[1].split("/")) + ".mcfunction"
            if not os.path.exists(path):
                self.lost.append(name)
                return
            with open(path, encoding="utf-8") as fh:
                self.files[name] = fh.read().splitlines()
        self.calls.append((self.tick, name))
        for line in self.files[name]:
            self.ran[self.tick] = self.ran.get(self.tick, 0) + 1
            if self._run(line):
                return

    def run(self, ticks):
        for _ in range(ticks):
            self.tick += 1
            for name in sorted((n for n, due in self.queue.items() if due[0] <= self.tick), key=self.queue.get):
                if name in self.queue:          # not cleared by one that ran before it in this tick
                    del self.queue[name]
                    self.call(name)

    def score(self, holder, objective):
        assert objective in self.objectives, f"the objective {objective} is not there"
        return self.scores.get((holder, objective))

    def _read(self, line):
        """(the kind of line, its words); a line is taken apart once."""
        if line not in self.read:
            for kind, rx in _LINES:
                m = rx.match(line)
                if m:
                    break
            else:
                raise AssertionError(f"a line of a kind this test does not know: {line}")
            g = list(m.groups())
            if kind == "merge":
                pose, swap = _POSE.match(g[6]), _SWAP.match(g[6])
                if pose:
                    goal = tuple(tuple(float(v.rstrip("f")) for v in pose.group(k).split(",")) for k in (2, 3, 4, 5))
                    assert all(abs(math.sqrt(sum(c * c for c in q)) - 1.0) < 1e-5 for q in goal[:2]), line
                    g[6] = (goal, int(pose.group(1)))
                elif swap:
                    g[6] = swap.group(1)
                else:
                    raise AssertionError(f"what is merged is neither a pose nor a model: {line}")
                g[1:5] = [tuple(float(v) for v in g[1:4]), float(g[4])]
            self.read[line] = (kind, g)
        return self.read[line]

    def _run(self, line):
        """Runs one line. True when the function it stands in ends with it."""
        kind, g = self._read(line)
        if kind == "schedule":
            assert int(g[1]) >= 1, line
            self.queued += 1
            self.queue[g[0]] = (self.tick + int(g[1]), self.queued)
        elif kind == "clear":
            self.queue.pop(g[0], None)
        elif kind == "function":
            self.call(g[0])
        elif kind == "objective":
            self.objectives.add(g[0])
        elif kind == "set":
            self.score(g[0], g[1])
            self.scores[(g[0], g[1])] = int(g[2])
        elif kind == "guard":
            if self.score(g[0], g[1]) != int(g[2]):
                self.call(g[3])
                return True
        elif kind == "watch":
            if self.score(g[0], g[1]) == int(g[2]) and self.score(g[3], g[4]) != int(g[5]):
                self.call(g[6])
        elif kind == "let_go":
            if self.score(g[0], g[1]) == int(g[2]):
                self.scores[(g[3], g[4])] = int(g[5])
        elif kind == "merge":
            kind_of, spot, reach, tag, what = g
            found = [e for e in self.shown if e.type == kind_of and tag in e.tags and math.dist(e.pos, spot) <= reach]
            assert len(found) <= 1, f"the selector finds {len(found)} entities: {line}"
            if not found:
                self.missed.append(line)
            elif isinstance(what, str):
                found[0].models.append((self.tick, what))
            else:
                found[0].given(self.tick + self.late(self.tick), what[0], what[1])
        else:
            self.said.append((self.tick, line))
        return False


AT = (100, 64, -200)
SHAFT = (20.5, 4.5, 0.25)


def _board():
    """A small beat board on a wall that looks south: the stations of obs_mot_loop, with models
    that are only their names. Returns the canvas and its parts by name."""
    c = _Canvas()
    south, east = (0, 0, 1), (1, 0, 0)
    c.add_entity(2.5, 3.5, 0.25, _display("mot_wheel"))
    MK.spin(c, south, MK.ENGINE_REV)
    c.add_entity(6.5, 3.5, 0.25, _display("mot_wheel"))
    MK.spin(c, south, MK.ENGINE_REV, lead=0)
    c.add_entity(12.5, 4.5, 0.25, _display("mot_arm", anchor=(-1.75, 0.0, 0.0)))
    MK.spin(c, south, MK.ORRERY["mercury"])
    c.add_entity(15.5, 5.5, 0.25, _display("mot_pendulum", anchor=(0.0, 0.5, 0.0)))
    MK.swing(c, south, 5.0, MK.PENDULUM)
    c.add_entity(17.5, 5.5, 0.25, _display("mot_pendulum", anchor=(0.0, 0.5, 0.0)))
    MK.swing(c, south, 5.0, MK.PENDULUM, phase=MK.PENDULUM // 2)
    x, y, z = SHAFT
    c.add_entity(x, y, z, _display("mot_disc"))
    MK.spin(c, south, MK.ENGINE_REV)
    c.add_entity(x + 5.0, y, z, _display("mot_crosshead"))
    MK.crank(c, south, east, 1.0, 4.0, MK.ENGINE_REV, turn=False)
    c.add_entity(x + 5.0, y, z, _display("mot_rod", anchor=(2.0, 0.0, 0.0)))
    MK.crank(c, south, east, 1.0, 4.0, MK.ENGINE_REV)
    c.add_entity(30.5, 3.5, 0.25, _display("mot_slider"))
    MK.slide(c, east, [(0, 1.5, 30), (60, 0.0, 30)], 120)
    c.add_entity(34.5, 3.5, 0.25, _display("mot_lamp"))
    MK.blink(c, "mot_lamp_dark", *MK.BLINK)
    MK.sound(c, (15.5, 5.5, 0.25), "minecraft:block.note_block.hat", MK.PENDULUM, at=(10, 30), volume=0.3)
    MK.puff(c, (40.0, 9.0, 0.0), "campfire_signal_smoke", 10, count=0, spread=MK.downwind(), speed=0.07, far=True)
    names = ("wheel", "wheel_late", "arm", "pendulum", "pendulum_b", "disc", "crosshead", "rod", "slider", "lamp")
    return c, dict(zip(names, c.motion.parts))


def _played(name="t", at=AT, canvas=None):
    """A world in which the board stands and its functions are written. Returns (game, entities by
    name, parts by name, the folder to remove afterwards)."""
    c, parts = _board() if canvas is None else canvas
    tmp = tempfile.mkdtemp(prefix="c164-motion-play-")
    assert MK.write(c, tmp, name, at=at) == [f"function c164art:{name}-motion/start"]
    game = _Game(tmp)
    shown = game.place(c, at)
    by_entity = {id(e): s for e, s in zip(c.entities, shown)}
    return game, {k: by_entity[id(p.entity)] for k, p in parts.items()}, parts, tmp


def _first(game, chain):
    """The tick the chain's first function ran on: the tick its parts set off."""
    return next(tick for tick, name in game.calls if name.endswith(f"-motion/c{chain}/0"))


def _spans(start, ticks, per_tick=4):
    return [start + k / float(per_tick) for k in range(int(ticks * per_tick) + 1)]


def _angle(p, about):
    """Degrees of the point p round `about`, seen from the south: 0 is east, 90 is up."""
    return math.degrees(math.atan2(p[1] - about[1], p[0] - about[0]))


def _turned(a, b):
    """Degrees from a to b, between -180 and 180."""
    return (b - a + 180.0) % 360.0 - 180.0


def test_play_turns():
    """Wheels turn evenly and never stand, an arm keeps its eye on its pin, pendulums pass through
    the poses they were given on the ticks they were given for."""
    game, shown, parts, tmp = _played()
    try:
        game.call("c164art:t-motion/start")
        game.run(1300)
        assert not game.lost and not game.missed, (game.lost[:3], game.missed[:3])
        # a wheel: the rim point that starts in the east goes up (counter-clockwise for the cameras)
        # and is where an even turn has it, at every quarter of a tick
        t0 = _first(game, MK.ENGINE_REV)
        for key in ("wheel", "wheel_late", "disc"):
            e = shown[key]
            for t in _spans(t0, 3 * MK.ENGINE_REV):
                want = 360.0 * (t - t0) / MK.ENGINE_REV
                assert abs(_turned(want, _angle(e.point(t, (1.0, 0.0, 0.0)), e.pos))) < 1e-3, (key, t)
                assert math.dist(e.point(t), e.pos) < 1e-6, (key, t)
        # an arm that turns about one end: the eye stays on the pin within what the kit says it
        # strays, the tip goes round evenly, 3.5 blocks out
        e, part = shown["arm"], parts["arm"]
        t0 = _first(game, MK.ORRERY["mercury"])
        off = 0.0
        for t in _spans(t0, MK.ORRERY["mercury"], 2):
            off = max(off, math.dist(e.point(t, (-1.75, 0.0, 0.0)), e.pos))
            tip = e.point(t, (1.75, 0.0, 0.0))
            want = 360.0 * (t - t0) / MK.ORRERY["mercury"]
            assert abs(_turned(want, _angle(tip, e.pos))) < math.degrees(MK.WOBBLE / 3.5) + 1e-3, t
            assert abs(math.dist(tip, e.pos) - 3.5) < MK.WOBBLE + 1e-6, t
        assert 0.25 * part.stray < off <= part.stray + 1e-6 and part.stray <= MK.WOBBLE, (off, part.stray)
        # pendulums: on the ticks of their poses they are where the sine has them; the second one,
        # half a swing late, is the first one's mirror from the start
        t0 = _first(game, MK.PENDULUM)
        a, b = shown["pendulum"], shown["pendulum_b"]

        def lean(e, t):
            bob = e.point(t, (0.0, -0.5, 0.0))
            return math.degrees(math.atan2(bob[0] - e.pos[0], e.pos[1] - bob[1]))

        for k in range(3 * 8 + 1):
            t = t0 + 5 * k
            assert abs(lean(a, t) - 5.0 * math.sin(2.0 * math.pi * 5 * k / MK.PENDULUM)) < 1e-3, k
        for t in _spans(t0, 3 * MK.PENDULUM):
            assert abs(lean(a, t) + lean(b, t)) < 1e-3, t
            assert abs(lean(a, t)) <= 5.0 + 1e-3, t
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_play_crank():
    """Crank disc, connecting rod and crosshead, each moved by its own steps: the rod's eye stays
    on the crank pin and its other end on the crosshead's pin, within a pixel and a half pixel."""
    game, shown, parts, tmp = _played()
    try:
        game.call("c164art:t-motion/start")
        game.run(4 * MK.ENGINE_REV)
        disc, rod, head = shown["disc"], shown["rod"], shown["crosshead"]
        t0 = _first(game, MK.ENGINE_REV)
        eye = pin = reach = 0.0
        for t in _spans(t0, 3 * MK.ENGINE_REV):
            eye = max(eye, math.dist(rod.point(t, (-2.0, 0.0, 0.0)), disc.point(t, (1.0, 0.0, 0.0))))
            pin = max(pin, math.dist(rod.point(t, (2.0, 0.0, 0.0)), head.point(t)))
            reach = max(reach, abs(head.point(t)[1] - head.pos[1]))
        for k in range(3 * 12 + 1):         # on the ticks of the rod's poses the eye is on the pin
            t = t0 + 4 * k
            assert math.dist(rod.point(t, (-2.0, 0.0, 0.0)), disc.point(t, (1.0, 0.0, 0.0))) < 0.5 / 16.0, k
        assert eye < 1.0 / 16.0 and pin < 0.5 / 16.0 and reach < 1e-6, (eye * 16.0, pin * 16.0, reach)
        # the crosshead goes 2 blocks: from the dead centre it was placed in to the other and back
        xs = [head.point(t)[0] - head.pos[0] for t in _spans(t0, MK.ENGINE_REV)]
        assert abs(max(xs)) < 1e-6 and abs(min(xs) + 2.0) < 1e-3, (max(xs), min(xs))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_play_stops_and_lamp():
    """What slides stops where it was told to, a lamp changes its model, a sound and a puff come
    on their ticks."""
    game, shown, parts, tmp = _played()
    try:
        game.call("c164art:t-motion/start")
        game.run(400)
        e = shown["slider"]
        t0 = _first(game, 120)
        for t, want in ((0, 0.0), (15, 0.75), (30, 1.5), (45, 1.5), (60, 1.5), (75, 0.75), (90, 0.0), (119, 0.0),
                        (120, 0.0), (135, 0.75)):
            assert _close(e.point(t0 + t), (e.pos[0] + want, e.pos[1], e.pos[2])), t
        lamp, (on, off) = shown["lamp"], MK.BLINK
        t0 = _first(game, on + off)
        seen = [lamp.model(t0 + t) for t in range(2 * (on + off))]
        assert seen == (["c164:mot_lamp"] * on + ["c164:mot_lamp_dark"] * off) * 2, seen
        t0 = _first(game, MK.PENDULUM)
        ticks = [tick - t0 for tick, line in game.said if line.startswith("playsound ")]
        assert ticks[:4] == [10, 30, 50, 70], ticks[:4]
        assert all(line.startswith("playsound minecraft:block.note_block.hat block @a[x=115.5,y=69.5,z=-199.75,"
                                   "distance=..16.0] 115.5 69.5 -199.75 0.3 1.0")
                   for _tick, line in game.said if line.startswith("playsound "))
        puffs = [tick for tick, line in game.said if line.startswith("particle ")]
        assert [b - a for a, b in zip(puffs, puffs[1:])][:5] == [10] * 5
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_play_late():
    """What the two ticks of lead are for: when a client learns of a step a tick and a half late,
    a wheel that is aimed ahead goes on turning, and one that is not stands until the step comes."""
    game, shown, parts, tmp = _played()
    try:
        game.late = lambda tick: 1.5 if (tick // 12) % 2 else 0.0
        game.call("c164art:t-motion/start")
        game.run(5 * MK.ENGINE_REV)
        t0 = _first(game, MK.ENGINE_REV) + MK.ENGINE_REV
        stood = {}
        for key in ("wheel", "wheel_late"):
            e, times = shown[key], _spans(t0, 3 * MK.ENGINE_REV)
            turns = [_turned(_angle(e.point(a, (1.0, 0.0, 0.0)), e.pos), _angle(e.point(b, (1.0, 0.0, 0.0)), e.pos))
                     for a, b in zip(times, times[1:])]
            assert min(turns) > -1e-6, (key, min(turns))            # never backwards
            stood[key] = sum(1 for d in turns if d < 1e-6) / 4.0    # ticks it stood
        assert stood["wheel"] == 0.0 and stood["wheel_late"] >= 4.0, stood
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_play_budget():
    """The commands that run in a tick are the ones check() counts."""
    game, shown, parts, tmp = _played()
    try:
        c = _board()[0]
        plan = MK._plan(c, "t", AT, "c164art")
        status, summary, _details = MK.check(c)
        assert status == "WARN" and f"{plan.peak} commands in the busiest tick" in summary, summary
        game.call("c164art:t-motion/start")
        once = game.ran.pop(0)          # start and what it calls, once: not the loop's load
        game.run(MK.HORIZON)
        assert once == len(parts) + 4 + len(plan.chains) + 1 + sum(len(ch.files) for ch in plan.chains), once
        assert max(game.ran.values()) == plan.peak, (max(game.ran.values()), plan.peak)
        mean = sum(game.ran.values()) / float(MK.HORIZON)
        assert abs(mean - plan.mean) < 0.02 * plan.mean, (mean, plan.mean)
        assert not game.lost and not game.missed
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_play_entries():
    """start, stop and load; and a second scene's start ends the first scene's loop."""
    game, shown, parts, tmp = _played()
    try:
        base, run = "c164art:t-motion/", ("#run", MK.OBJECTIVE)
        plan = MK._plan(_board()[0], "t", AT, "c164art")

        def starts():
            return sum(1 for _tick, name in game.calls if name == base + "start")

        def ours(name="t"):
            return sorted(n for n in game.queue if n.startswith(f"c164art:{name}-motion/c"))

        game.call(base + "start")
        game.run(200)
        assert game.scores[run] == plan.number and len(ours()) == len(plan.chains), ours()
        # load on a loop that is alive: watch looks and leaves it alone
        game.call(base + "load")
        assert game.scores[("#t", MK.OBJECTIVE)] == 0
        game.run(plan.watch + 1)
        assert starts() == 1 and game.scores[("#t", MK.OBJECTIVE)] == 1
        # the queue is lost (the pack was off for a while): watch starts the loop again
        for name in ours():
            del game.queue[name]
        game.call(base + "load")
        game.run(plan.watch + 1)
        assert starts() == 2 and len(ours()) == len(plan.chains)
        # start on a loop that runs: every part back in its rest pose, the chains once each
        game.run(77)
        game.call(base + "start")
        assert starts() == 3 and len(ours()) == len(plan.chains)
        assert all(_close(e.pose(game.tick)[k], e.rest[k]) for e in shown.values() for k in range(4))
        # stop: nothing queued, every part in its rest pose and its own model, and load leaves it stopped
        game.run(333)
        game.call(base + "stop")
        assert not ours() and game.scores[run] == 0
        assert all(_close(e.pose(game.tick)[k], e.rest[k]) for e in shown.values() for k in range(4))
        assert shown["lamp"].model(game.tick) == "c164:mot_lamp"
        game.call(base + "load")
        game.run(plan.watch + 200)
        assert starts() == 3 and not ours()
        # a second scene on the same spot: its start takes the world over, and the first scene's
        # chains end themselves within a cycle of its quickest chain
        other = _board()
        assert MK.write(other[0], tmp, "u", at=AT) == ["function c164art:u-motion/start"]
        with open(os.path.join(tmp, "data", "minecraft", "tags", "function", "load.json"), encoding="utf-8") as fh:
            assert [v["id"] for v in json.load(fh)["values"]] == ["c164art:t-motion/load", "c164art:u-motion/load"]
        game.call(base + "start")
        game.run(100)
        game.call("c164art:u-motion/start")
        assert game.scores[run] == MK._plan(other[0], "u", AT, "c164art").number != plan.number
        game.run(plan.chains[0].cycle + MK.STAGGER + 1)
        assert not ours() and len(ours("u")) == len(plan.chains), (ours(), ours("u"))
        halted = [tick for tick, name in game.calls if name == base + "halt"]
        game.run(2000)
        assert not ours() and [tick for tick, name in game.calls if name == base + "halt"] == halted
        assert not game.lost
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("ok", test.__name__)
    print(f"{len(tests)} tests passed")
