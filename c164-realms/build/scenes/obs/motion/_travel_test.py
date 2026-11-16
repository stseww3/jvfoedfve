"""What travels, against itself and without the game (from build/):

    python -m scenes.obs.motion._travel_test

Not a work package. It answers what can be answered without a client about _kit.travel(): the
timetable is smooth and stops where it says, an entity that is given to a car is still shown
where its maker placed it, and the written functions, played back tick by tick the way this file
understands the game, keep a train on its line, its riders on their seats and its wheels on the
rails. What a client does with a teleport is the card's section 1 (plan/packages/motion/travel.md):
a display entity goes from where it is shown to where it was sent in teleport_duration ticks, in
a straight line, and its heading with it, the short way round.
"""
import math
import os
import re
import shutil
import tempfile

from . import _kit as MK
from ._kit_test import _Canvas, _close, _display

AT = (100, 64, -200)
CYCLE = 1000
TABLE = [(0, 80.0), (400, 5.0), (500, 5.0), (900, 80.0)]      # down the line to the halt, a stand, back
BASE = "c164art:t-motion/"
OWN = "c164art:trial/"


def _line():
    """Level, over a brow down an incline, a foot, a quarter circle of 20 blocks, straight on."""
    pts = [(0.0, 0.0, 0.0), (20.0, 0.0, 0.0), (32.0, -6.0, 0.0), (41.0, -7.0, 0.0)]
    for k in range(1, 31):
        a = math.radians(3.0 * k)
        pts.append((41.0 + 20.0 * math.sin(a), -7.0, 20.0 - 20.0 * math.cos(a)))
    return pts + [(61.0, -7.0, 40.0)]


LINE = _line()


def _turned(yaw, pitch, v):
    """v of an entity's own frame in the world's axes, written out: about x by the pitch, then
    about y by minus the yaw (the game's rotationYXZ(-yaw, pitch, 0))."""
    p, y = math.radians(pitch), math.radians(-yaw)
    x0, y0, z0 = v[0], v[1] * math.cos(p) - v[2] * math.sin(p), v[1] * math.sin(p) + v[2] * math.cos(p)
    return (x0 * math.cos(y) + z0 * math.sin(y), y0, -x0 * math.sin(y) + z0 * math.cos(y))


def _shown(pos, nbt, m):
    """Where the game shows the point m of the model of an item display with this NBT, standing on pos."""
    tr = nbt["transformation"]
    left, right = tuple(float(v) for v in tr["left_rotation"]), tuple(float(v) for v in tr["right_rotation"])
    scale, shift = [float(v) for v in tr["scale"]], [float(v) for v in tr["translation"]]
    v = MK._qrot(right, (-m[0], m[1], -m[2]))
    v = MK._qrot(left, tuple(v[i] * scale[i] for i in range(3)))
    w = _turned(float(nbt["Rotation"][0]), float(nbt["Rotation"][1]), tuple(shift[i] + v[i] for i in range(3)))
    return tuple(pos[i] + w[i] for i in range(3))


def _frame(line, s, at, axles):
    """A car's middle and the unit vectors of its own axes in the world, from the line alone."""
    a, b = line.at(s + at + axles[0]), line.at(s + at + axles[1])
    f = MK._unit(tuple(b[i] - a[i] for i in range(3)))
    yaw, pitch = math.degrees(math.atan2(-f[0], f[2])), -math.degrees(math.asin(f[1]))
    return tuple((a[i] + b[i]) / 2.0 for i in range(3)), [_turned(yaw, pitch, e) for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]


def _train(call=True, table=TABLE, cycle=CYCLE, wheel=0.5, axle=(0, 0, 1)):
    """A coach of two parts, a wheel and two seats, and an engine of one part, placed as they stand
    at the halt (distance 5)."""
    c = _Canvas()
    train = MK.travel(c, "trial", LINE, table, cycle, home=5.0, call=call)
    coach = train.car("coach", at=0.0, axles=(-1.0, 1.0))
    loco = train.car("loco", at=4.0, axles=(-1.0, 1.0))
    c.add_entity(5.0, 1.0, 0.0, _display("car_body", yaw=90.0))
    coach.carry(c)
    c.add_entity(5.0, 2.5, 0.25, _display("car_roof", yaw=37.0, turn=((0.0, 1.0, 0.0), 20.0), anchor=(0.5, 0.0, 0.25)))
    coach.carry(c)
    c.add_entity(4.0, wheel, 0.0, _display("car_wheels"))
    coach.roll(c, axle, wheel)
    coach.seat((5.5, 1.2, 0.4))
    coach.seat((4.5, 1.2, -0.4))
    c.add_entity(9.0, 1.5, 0.0, _display("loco_body"))
    loco.carry(c)
    return c, train, coach, loco


def _refused(*calls):
    for call in calls:
        try:
            call()
        except ValueError:
            continue
        raise AssertionError("what should be refused was taken")


def test_route():
    corners = [(0.0, 0.0, 0.0), (20.0, 0.0, 0.0), (40.0, -10.0, 0.0), (40.0, -10.0, 30.0)]
    line = MK.route(corners)
    assert abs(line.length - (20.0 + math.hypot(20.0, 10.0) + 30.0)) < 1e-9
    assert _close(line.at(10.0), (10.0, 0.0, 0.0)) and _close(line.at(line.length), (40.0, -10.0, 30.0))
    assert _close(line.at(20.0 + math.hypot(20.0, 10.0) / 2.0), (30.0, -5.0, 0.0))
    assert _close(line.at(-3.0), (-3.0, 0.0, 0.0)) and _close(line.at(line.length + 2.0), (40.0, -10.0, 32.0))
    ring = MK.route([(0, 0, 0), (4, 0, 0), (4, 0, 4), (0, 0, 4)], closed=True)
    assert abs(ring.length - 16.0) < 1e-9 and _close(ring.at(17.0), (1.0, 0.0, 0.0)) and _close(ring.at(-1.0), (0.0, 0.0, 1.0))

    class P:
        def __init__(self, s):
            self.x, self.y, self.z = 2.0 * s, 1.0, 0.0

    asked = MK.route(P, 0.0, 10.0)
    assert _close(asked.at(3.0), (6.0, 1.0, 0.0)) and _close(asked.at(12.0), (24.0, 1.0, 0.0))
    _refused(lambda: MK.route(P), lambda: MK.route([(0, 0, 0)]), lambda: MK.route([(0, 0, 0), (0, 0, 0)]))


def test_timetable():
    line = MK.route(LINE)
    s, rows = MK._timetable("t", TABLE, CYCLE, line)
    assert len(s) == CYCLE + 1 and rows == TABLE
    for t, d in TABLE:
        assert abs(s[t] - d) < 1e-9
    assert all(s[t + 1] < s[t] for t in range(0, 400)) and all(s[t] == 5.0 for t in range(400, 501))
    assert all(s[t + 1] > s[t] for t in range(500, 900)) and all(s[t] == 80.0 for t in range(900, CYCLE + 1))
    # it sets off and comes to rest gently: the first and the last tick of a move are far below its speed
    mean = 75.0 / 400.0
    assert abs(s[1] - s[0]) < mean / 20.0 and abs(s[400] - s[399]) < mean / 20.0
    assert max(abs(s[t + 1] - s[t]) for t in range(400)) < 1.6 * mean
    # more rows give a stretch its own speed, and nothing runs back between them
    s, _rows = MK._timetable("t", [(0, 80.0), (100, 60.0), (300, 50.0), (360, 5.0), (460, 5.0), (800, 80.0)], CYCLE, line)
    assert all(s[t + 1] < s[t] for t in range(0, 360))
    assert abs(s[50] - s[49]) > 2.0 * abs(s[200] - s[199])
    _refused(*[lambda bad=bad: MK._timetable("t", bad, CYCLE, line) for bad in (
        [(5, 80.0), (300, 80.0)], [(0, 80.0), (300, 5.0)], [(0, 80.0), (300, 5.0), (200, 80.0)],
        [(0, 80.0), (300, 5.0), (CYCLE + 1, 80.0)], [(0, 80.0)])])
    # round a ring the end runs into the start, at speed
    ring = MK.route([(0, 0, 0), (40, 0, 0), (40, 0, 40), (0, 0, 40)], closed=True)
    s, _rows = MK._timetable("t", [(0, 0.0), (400, 160.0)], 400, ring)
    assert abs((s[1] - s[0]) - 0.4) < 1e-6 and abs((s[400] - s[399]) - 0.4) < 1e-6


def test_take():
    """An entity given to a car is shown, with the train at home, where its maker placed it, and
    goes with the car's frame from there."""
    c = _Canvas()
    marks = ((0.0, 0.0, 0.0), (0.3, 0.2, -0.4), (-0.5, 0.1, 0.25))
    placed = []
    for pos, nbt in (((5.0, 1.0, 0.0), _display("a", yaw=90.0)),
                     ((5.3, 2.5, 0.25), _display("b", yaw=37.0, turn=((0.0, 1.0, 0.0), 20.0), anchor=(0.5, 0.0, 0.25))),
                     ((28.0, -3.0, 0.5), _display("c", yaw=200.0, scale=(2.0, 1.0, 0.5), anchor=(0.0, 0.25, 0.0)))):
        placed.append([_shown(pos, nbt, m) for m in marks])
        c.add_entity(pos[0], pos[1], pos[2], nbt)
    line = MK.route(LINE)
    for k, home in ((0, 5.0), (1, 5.0), (2, 26.0)):     # the third is placed on the incline
        train = MK.travel(c, f"t{k}", line, TABLE, CYCLE, home=home)
        car = train.car("car", at=1.5, axles=(-1.0, 1.0))
        car.carry(c, entity=c.entities[k])
        x, y, z, nbt = c.entities[k]
        assert nbt["teleport_duration"] == MK.TRAVEL_STEP + MK.TRAVEL_LEAD and {f"t.t{k}", f"t.t{k}.car"} <= set(nbt["Tags"])
        o_home, axes_home = _frame(line, home, 1.5, (-1.0, 1.0))
        # on the canvas it stays where the train is at home, and is shown as it was placed
        assert _close((x, y, z), o_home)
        for m, w in zip(marks, placed[k]):
            assert _close(_shown((x, y, z), nbt, m), w, 1e-5), (k, m)
        for tick in (0, 150, 240, 300, 400, 620, CYCLE):
            mid, yaw, pitch, _q = car.pose(tick)
            o, axes = _frame(line, train.s[tick], 1.5, (-1.0, 1.0))
            assert _close(mid, o)
            moved = dict(nbt, Rotation=[yaw, pitch])
            for m, w in zip(marks, placed[k]):
                own = [sum((w[i] - o_home[i]) * axes_home[j][i] for i in range(3)) for j in range(3)]
                want = tuple(o[i] + sum(own[j] * axes[j][i] for j in range(3)) for i in range(3))
                assert _close(_shown(mid, moved, m), want, 1e-5), (k, tick, m)
    _refused(lambda: MK.spin(c, "y", 40, entity=c.entities[0]),
             lambda: train.car("car"), lambda: car.carry(c, entity=c.entities[2]),
             lambda: MK.travel(c, "t0", line, TABLE, CYCLE), lambda: MK.travel(c, "start", line, TABLE, CYCLE),
             lambda: MK.travel(c, "Up", line, TABLE, CYCLE), lambda: MK.travel(c, "obs", line, TABLE, CYCLE),
             lambda: MK.travel(c, "x", line, TABLE, CYCLE, step=59),
             lambda: MK.travel(c, "y", line, [(0, 80.0), (300, 5.0), (CYCLE, 80.0)], CYCLE, call=True))
    assert set(MK.trains(c)) == {"t0", "t1", "t2"} and MK.trains(_Canvas()) == {}


def test_sends():
    """From teleport to teleport the car is shown within TRAVEL_FIT of its line; the teleports are
    far apart where the line is straight and the speed even, and close where it is not."""
    c, train, coach, loco = _train()
    for car in (coach, loco):
        sends = car.sends()
        assert [t for t, goal, _p, _y, _x in sends if goal == t] == [400, 900]      # where it comes to stand
        gaps = [goal - t for t, goal, _p, _y, _x in sends if goal > t]
        assert 12 <= max(gaps) <= MK.TRAVEL_STEP and min(gaps) >= 1 and 60 < len(sends) < 400, (len(sends), max(gaps))
        assert all(a[1] == b[0] for a, b in zip(sends, sends[1:]) if a[1] > a[0])   # each is aimed at the next
        assert all(-90.0 <= pitch <= 90.0 for _t, _g, _p, _yaw, pitch in sends)
    assert train.off() <= 2.0 * MK.TRAVEL_FIT, train.off()
    assert _close(coach.held(0), coach.sends()[0][2]) and _close(coach.held(450), coach.pose(400)[0])


# ---- the functions played back ------------------------------------------------------------------
_SEL = r"@e\[tag=([^,\]]+)(?:,tag=([^,\]]+))?(?:,x=(\S+?),y=(\S+?),z=(\S+?),distance=\.\.(\S+?))?(?:,limit=1)?\]"
_KINDS = [(kind, re.compile(rx + r"\Z")) for kind, rx in (
    ("schedule", r"schedule function (\S+) (\d+)t replace"),
    ("clear", r"schedule clear (\S+)"),
    ("function", r"function (\S+)"),
    ("set", r"scoreboard players set (\S+) (\S+) (-?\d+)"),
    ("guard", r"execute unless score (\S+) (\S+) matches (-?\d+) run return run function (\S+)"),
    ("idle", r"execute unless score (\S+) (\S+) matches (-?\d+) run return 0"),
    ("tp", r"tp " + _SEL + r" (\S+) (\S+) (\S+)(?: (\S+) (\S+))?"),
    ("mend", r"execute unless entity " + _SEL + r" run summon (\S+) (\S+) (\S+) (\S+) (\{.*\})"),
    ("merge", r"data merge entity " + _SEL + r" \{start_interpolation:0,interpolation_duration:(\d+),transformation:"
              r"\{left_rotation:\[(.*?)\],right_rotation:\[(.*?)\],scale:\[(.*?)\],translation:\[(.*?)\]\}\}"),
    ("free", r"tag " + _SEL + r" add (\S+)"),
    ("taken", r"execute as " + _SEL + r" on passengers on vehicle run tag @s remove (\S+)"),
    ("mount", r"execute if entity " + _SEL + r" run return run ride @s mount " + _SEL),
)]


class _Thing:
    """An entity of the played world: where the game has it and where a client shows it."""

    def __init__(self, pos, nbt):
        self.tags, self.pos = set(nbt.get("Tags", ())), tuple(float(v) for v in pos)
        self.rot = tuple(float(v) for v in nbt.get("Rotation", (0.0, 0.0)))
        self.takes = int(nbt.get("teleport_duration", 0))
        self.way = (float("-inf"), self.pos, self.rot, self.pos, self.rot)      # since, from, to
        self.poses = []         # (tick, ticks, left rotation, translation) merged into it
        self.rider = None

    def shown(self, time):
        since, p0, r0, p1, r1 = self.way
        u = 1.0 if self.takes <= 0 else min(1.0, (time - since) / float(self.takes))
        rot = (r0[0] + ((r1[0] - r0[0] + 180.0) % 360.0 - 180.0) * u, r0[1] + (r1[1] - r0[1]) * u)
        return tuple(p0[i] + (p1[i] - p0[i]) * u for i in range(3)), rot

    def sent(self, time, pos, rot):
        p, r = self.shown(time)
        self.way = (time, p, r, pos, self.rot if rot is None else rot)
        self.pos, self.rot = pos, self.way[4]


class _World:
    def __init__(self, pack, canvas, at, namespace="c164art"):
        self.root = os.path.join(pack, "data", namespace, "function")
        self.things = [_Thing((x + at[0], y + at[1], z + at[2]), nbt) for x, y, z, nbt in canvas.entities]
        self.files, self.tick, self.queue, self.order = {}, 0, {}, 0
        self.scores, self.calls, self.missed, self.said, self.ran = {}, [], [], [], {}

    def find(self, g):
        tag, also, x, y, z, reach = g[:6]
        out = [e for e in self.things if tag in e.tags and (also is None or also in e.tags)]
        if x is not None:
            out = [e for e in out if math.dist(e.pos, (float(x), float(y), float(z))) <= float(reach)]
        return out

    def call(self, name, who=None):
        if name not in self.files:
            path = os.path.join(self.root, *name.split(":", 1)[1].split("/")) + ".mcfunction"
            assert os.path.exists(path), f"{name} is called and is not in the pack"
            with open(path, encoding="utf-8") as fh:
                self.files[name] = fh.read().splitlines()
        self.calls.append((self.tick, name))
        for line in self.files[name]:
            self.ran[self.tick] = self.ran.get(self.tick, 0) + 1
            if self.line(line, who):
                return

    def run(self, ticks):
        for _ in range(ticks):
            self.tick += 1
            for name in sorted((n for n, due in self.queue.items() if due[0] <= self.tick), key=self.queue.get):
                if name in self.queue:
                    del self.queue[name]
                    self.call(name)

    def line(self, line, who):
        """Runs one line; True when its function ends with it."""
        for kind, rx in _KINDS:
            m = rx.match(line)
            if m:
                break
        else:
            self.said.append((self.tick, line))
            return False
        g = m.groups()
        if kind == "schedule":
            self.order += 1
            self.queue[g[0]] = (self.tick + int(g[1]), self.order)
        elif kind == "clear":
            self.queue.pop(g[0], None)
        elif kind == "function":
            self.call(g[0], who)
        elif kind == "set":
            self.scores[(g[0], g[1])] = int(g[2])
        elif kind == "guard":
            if self.scores.get((g[0], g[1])) != int(g[2]):
                self.call(g[3])
                return True
        elif kind == "idle":
            if self.scores.get((g[0], g[1])) != int(g[2]):
                return True
        elif kind == "tp":
            found = self.find(g)
            if not found:
                self.missed.append((self.tick, line))
            rot = None if g[9] is None else (float(g[9]), float(g[10]))
            for e in found:
                e.sent(self.tick, (float(g[6]), float(g[7]), float(g[8])), rot)
        elif kind == "mend":
            if not self.find(g):
                tags = re.search(r"Tags:\[(.*?)\]", g[10]).group(1).replace('"', "").split(",")
                takes = int(re.search(r"teleport_duration:(\d+)", g[10]).group(1))
                self.things.append(_Thing((float(g[7]), float(g[8]), float(g[9])), {"Tags": tags, "teleport_duration": takes}))
        elif kind == "merge":
            found = self.find(g)
            assert len(found) <= 1, line
            if not found:
                self.missed.append((self.tick, line))
            else:
                left, shift = (tuple(float(v.rstrip("f")) for v in g[k].split(",")) for k in (7, 10))
                assert abs(math.sqrt(sum(v * v for v in left)) - 1.0) < 1e-5, line
                found[0].poses.append((self.tick, int(g[6]), left, shift))
        elif kind == "free":
            for e in self.find(g):
                e.tags.add(g[6])
        elif kind == "taken":
            for e in self.find(g):
                if e.rider is not None:
                    e.tags.discard(g[6])
        elif kind == "mount":
            if self.find(g):
                seat = self.find(g[6:])
                assert len(seat) == 1 and who is not None, line
                if seat[0].rider is None and all(e.rider != who for e in self.things):
                    seat[0].rider = who
                return True
        return False


def _played(call=True, **more):
    c, train, coach, loco = _train(call, **more)
    tmp = tempfile.mkdtemp(prefix="c164-travel-play-")
    assert MK.write(c, tmp, "t", at=AT) == ["function c164art:t-motion/start"]
    return c, train, coach, loco, _World(tmp, c, AT), tmp


def _plus(p):
    return tuple(p[i] + AT[i] for i in range(3))


def _starts(world):
    return [tick for tick, name in world.calls if name == BASE + "trial/0"]


def test_play_trip():
    """A trip played back: every teleport finds its car, the cars keep to the timetable and stand
    in the station on the tick, the riders' seats keep their places in the coach."""
    c, train, coach, loco, world, tmp = _played()
    try:
        body = [e for e in world.things if "t.trial.coach" in e.tags]
        seats = [next(e for e in world.things if f"t.trial.s{k}" in e.tags) for k in range(2)]
        engine = [e for e in world.things if "t.trial.loco" in e.tags]
        assert len(body) == 3 and len(engine) == 1 and all(e.takes == 23 for e in body + seats + engine)
        assert all(_close(e.pos, _plus(coach.frame(5.0)[0])) for e in body)     # placed as the train is at home
        world.call(BASE + "start")
        began = world.tick
        world.run(40)           # the chains are started within a second
        first = _starts(world)[0]
        assert world.scores[("#t.trial", "c164m")] == 1
        # the first trip after start takes the train from where it was placed; the second is the rule
        world.run(first + CYCLE - world.tick)
        assert _starts(world) == [first, first + CYCLE] and not world.missed, world.missed[:3]
        fit = max(train.off(), MK.TRAVEL_FIT) + 0.005
        worst = worst_seat = 0.0
        for t in range(1, CYCLE):
            world.run(1)
            for car, things in ((coach, body), (loco, engine)):
                mid, yaw, pitch, _q = car.pose(t)
                true = car._ends(_plus(mid), yaw, pitch)
                for e in things:
                    at, rot = e.shown(world.tick)
                    ends = car._ends(at, rot[0], rot[1])
                    worst = max(worst, math.dist(ends[0], true[0]), math.dist(ends[1], true[1]))
            mid, rot = body[0].shown(world.tick)
            for k, seat in enumerate(seats):
                rides = tuple(mid[i] + _turned(rot[0], rot[1], train.seats[k][1])[i] for i in range(3))
                worst_seat = max(worst_seat, math.dist(seat.shown(world.tick)[0], rides))
            if 400 <= t < 500:          # it stands in the station, to the tick and to the spot
                assert all(math.dist(e.shown(world.tick)[0], _plus(coach.pose(400)[0])) < 1e-3 for e in body), t
            assert world.scores[("#t.trial", "c164m")] == (1 if t < 400 else 2 if t < 500 else 3 if t < 900 else 0), t
        assert not world.missed, world.missed[:3]
        assert worst < fit, (worst, fit)
        assert worst_seat < 0.03, worst_seat
        assert train.stops == [(400, 500, 5.0)]
        assert all(_close(e.pos, _plus(coach.pose(0)[0]), 1e-3) for e in body)
        # the wheel: no pose is further round from the one before than the client turns the right
        # way, and it ends the trip as it began
        wheel = next(e for e in world.things if "t.trial.r0" in e.tags)
        assert len(wheel.poses) > 100
        rest = last = MK._four(c.entities[2][3]["transformation"]["left_rotation"])
        for _tick, _ticks, left, _shift in wheel.poses:
            dot = abs(sum(left[i] * last[i] for i in range(4)))
            assert 2.0 * math.degrees(math.acos(min(1.0, dot))) <= MK.MAX_TURN + 0.5
            last = left
        assert abs(abs(sum(last[i] * rest[i] for i in range(4))) - 1.0) < 1e-6
        # the budget: what check() counts is what ran
        plan = MK._plan(c, "t", AT, "c164art")
        assert max(n for tick, n in world.ran.items() if tick > began) <= plan.peak, plan.peak
        status, summary, notes = MK.check(c)
        assert status == "PASS" and "1 that travel" in summary, (status, summary, notes)
        assert any(n.startswith("trial: 2 cars of 4 parts, 2 seats, 1 wheels") for n in notes), notes
        assert any(n.startswith("functions of the packages' own: trial/board") for n in notes), notes
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_play_go_and_board():
    """go sends the train off while it stands at its start and not otherwise; park and restart
    take it back from anywhere; board seats players in the order of the seats; a seat that went
    away with its rider is made anew."""
    c, train, coach, loco, world, tmp = _played()
    try:
        score = lambda: world.scores[("#t.trial", "c164m")]     # noqa: E731
        ours = lambda: [n for n in world.queue if n.startswith(BASE + "trial/")]    # noqa: E731
        world.call(BASE + "start")
        world.run(40)
        first = _starts(world)[0]
        world.run(200)
        world.call(OWN + "go")              # on its way: nothing
        assert _starts(world) == [first]
        world.run(first + train.end + 50 - world.tick)
        assert score() == 0
        world.call(OWN + "go")              # at rest: off at once, and the trip that was due is not run as well
        again = world.tick
        assert _starts(world) == [first, again] and score() == 1
        world.run(CYCLE - 1)
        assert _starts(world) == [first, again]
        world.run(1)
        assert _starts(world) == [first, again, again + CYCLE]
        # park: from anywhere back to the start, and there it stays until go
        world.run(300)
        world.call(OWN + "park")
        assert score() == 0 and not ours()
        assert all(_close(e.pos, _plus(coach.pose(0)[0]), 1e-3) for e in world.things if "t.trial.coach" in e.tags)
        world.run(3 * CYCLE)
        assert len(_starts(world)) == 3 and score() == 0
        world.call(OWN + "go")
        assert len(_starts(world)) == 4 and score() == 1 and len(ours()) == 1
        # restart: from anywhere, off at once
        world.run(520)
        assert score() == 3
        world.call(OWN + "restart")
        assert _starts(world)[-1] == world.tick and len(_starts(world)) == 5 and score() == 1 and len(ours()) == 1
        world.run(CYCLE + 100)
        assert len(_starts(world)) == 6 and not world.missed, world.missed[:3]
        # boarding
        seats = [next(e for e in world.things if f"t.trial.s{k}" in e.tags) for k in range(2)]
        world.call(OWN + "board", who="ann")
        world.call(OWN + "board", who="bob")
        world.call(OWN + "board", who="cy")         # no seat left
        world.call(OWN + "board", who="ann")        # she sits already
        assert [s.rider for s in seats] == ["ann", "bob"]
        # ann leaves the game and her seat goes with her; the next trip has the seat again
        world.things.remove(seats[0])
        world.run(CYCLE)
        fresh = [e for e in world.things if "t.trial.s0" in e.tags]
        assert len(fresh) == 1 and fresh[0].rider is None and fresh[0].takes == 23
        assert {"c164art", "t.trial", "t.trial.seat"} <= fresh[0].tags
        world.call(OWN + "board", who="cy")
        assert fresh[0].rider == "cy"
        # stop puts everything back where the trip starts
        world.run(150)
        world.call(BASE + "stop")
        assert all(_close(e.pos, _plus(coach.pose(0)[0]), 1e-3) for e in world.things if "t.trial.coach" in e.tags)
        assert score() == 0 and not world.queue
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_shared_chain():
    """Without call= the trip is on the chain of its cycle, with whatever else has that cycle."""
    c, train, coach, loco = _train(call=False)
    c.add_entity(60.0, 3.0, 0.0, _display("mot_wheel"))
    MK.spin(c, (0, 0, 1), CYCLE)
    plan = MK._plan(c, "t", AT, "c164art")
    assert [chain.folder for chain in plan.chains] == [f"c{CYCLE}"]
    assert set(plan.own) == {"trial/board"}
    assert not any("#t.trial" in line for lines in plan.files.values() for line in lines)


def test_wheel_rolls():
    """A wheel rolls the way the car goes, whichever way round its axle was named: the point of
    its rim on the rail does not slide."""
    for axle in ((0, 0, 1), (0, 0, -1), "z"):
        c, train, coach, loco = _train(axle=axle, wheel=1.0)     # big enough never to be held
        roll = train.rolls[0]
        turns, far = train._turns(roll), coach.far()
        for t in (30, 200, 380, 520, 700):
            ds = far[t + 1] - far[t]
            q = MK._about(roll.axis, turns[t + 1] - turns[t])
            down = (0.0, -abs(roll.radius), 0.0)
            there = MK._qrot(q, down)
            slid = math.dist((there[0], there[1], there[2] + ds), down)
            assert abs(ds) > 1e-4 and slid < 0.2 * abs(ds), (axle, t, ds, slid)


def test_wheel_held():
    """A wheel too small for the train's speed is held while the train is fast and loses whole
    turns: at the halt it stands as true rolling leaves it."""
    c, train, coach, loco = _train(wheel=0.05)
    roll = train.rolls[0]
    turns, far = train._turns(roll), coach.far()
    true = [far[t] * 180.0 / (math.pi * roll.radius) for t in range(CYCLE + 1)]
    steps = [abs(turns[t + 1] - turns[t]) for t in range(CYCLE)]
    assert max(abs(true[t + 1] - true[t]) for t in range(CYCLE)) > 2.0 * MK.ROLL_MOST      # it is too fast, by far
    assert max(steps) <= MK.ROLL_MOST + 1e-9
    lost = (true[400] - turns[400]) / 360.0
    assert abs(lost - round(lost)) < 1e-6 and round(lost) != 0, lost
    assert abs(turns[CYCLE] / 360.0 - round(turns[CYCLE] / 360.0)) < 1e-6
    # where the train is slow the wheel rolls true
    slow = [t for t in range(400) if abs(true[t + 1] - true[t]) < 0.5 * MK.ROLL_MOST]
    assert slow and all(abs((turns[t + 1] - turns[t]) - (true[t + 1] - true[t])) < 1e-9 for t in slow)
    status, _summary, notes = MK.check(c)
    assert status == "PASS" and any("is held to" in n for n in notes), (status, notes)


def test_times_and_places():
    c, train, coach, loco = _train()
    assert train.tick(5.0) == 400 and train.tick(30.0) < 400 < train.tick(30.0, nth=1)
    assert abs(train.at(train.tick(30.0)) - 30.0) < 0.3 and train.at(450) == 5.0
    # a point given as it lies at home is there again whenever the train is at home
    assert _close(train.where(400, (5.5, 1.2, 0.4), car="coach"), (5.5, 1.2, 0.4))
    assert _close(train.where(450, (9.0, 3.0, 0.0), car="loco"), (9.0, 3.0, 0.0))
    assert _close(train.where(0), MK.route(LINE).at(80.0))
    assert _close(train.heading(450, car="coach"), (-90.0, 0.0)) and _close(train.heading(0), (0.0, 0.0))
    beats = train.beats(0.5, per_turn=2)
    assert abs(len(beats) - 2 * 2 * 75.0 / (math.pi * 1.0)) <= 4, len(beats)       # there and back, two a turn
    assert all(0 < t <= 900 for t in beats) and not any(400 < t <= 500 for t in beats)
    train.run("particle minecraft:cloud {x} {y} {z} 0.0 0.0 0.0 0.0 1 force", at=beats[:5], pos=(9.0, 3.0, 0.0), car="loco")
    train.run("say {ns} arrived", at=(400,))
    plan = MK._plan(c, "t", AT, "c164art")
    lines = [line for lines in plan.files.values() for line in lines]
    assert "say c164art arrived" in lines
    puffs = [line for line in lines if line.startswith("particle")]
    assert len(puffs) == 5
    assert puffs[0].split()[2:5] == [MK._num(v) for v in _plus(train.where(beats[0], (9.0, 3.0, 0.0), car="loco"))]
    _refused(lambda: train.run("say late", at=(950,)), lambda: train.run("/say x"), lambda: train.tick(500.0),
             lambda: train.where(0, (0, 0, 0), car="tender"))


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("ok", test.__name__)
    print(f"{len(tests)} tests passed")
