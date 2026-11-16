"""The opening's functions played through without the game (from build/):

    python -m scenes.obs.motion._arrival_test

Not a work package (the name starts with "_"). A stand-in train keeps a2's interface
(plan/packages/motion/travel.md, section 3) with a plain timetable on a4's line, and a small
game runs the lines of arrival.py and guide_title.py the way this file understands the few
commands they are made of: marks, counts, who sits on what, what is scheduled. It answers what can
be answered without a client: that every way through the opening ends on the platform, with the
title shown once and no mark left behind. What the game itself does with the functions is the
export's verification and the look on a node (the card, plan/packages/motion/arrival.md).
"""
import re

from ..site import _rail as RAIL
from . import arrival as A
from . import guide_title as T

NS = "c164art"
SEATS = 12


class Train:
    """The kit's train as the opening reads it."""
    step, cycle = 20, 3000

    def __init__(self, up=940, stop=400):
        self.up, self.stop = up, stop
        self.stops = [(up, up + stop, RAIL.STOP), (2 * up + stop, self.cycle, RAIL.START)]
        self.hung = {}

    def at(self, tick):
        def ease(u):
            return u * u * (3.0 - 2.0 * u)
        if tick <= self.up:
            return RAIL.START + (RAIL.STOP - RAIL.START) * ease(tick / self.up)
        if tick <= self.up + self.stop:
            return RAIL.STOP
        if tick <= 2 * self.up + self.stop:
            return RAIL.STOP + (RAIL.START - RAIL.STOP) * ease((tick - self.up - self.stop) / self.up)
        return RAIL.START

    def tick(self, s, nth=0):
        hits = [t for t in range(1, self.cycle)
                if self.at(t - 1) != self.at(t) and (self.at(t - 1) - s) * (self.at(t) - s) <= 0]
        return hits[nth]

    def heading(self, tick, car=None):
        pose = RAIL.pose(self.at(tick), 2.0)
        return (pose.yaw + 180.0) % 360.0, -pose.pitch

    def run(self, command, at=(0,), pos=None, car=None):
        for tick in at:
            assert 0 <= tick <= self.stops[-1][0], f"{command!r} hangs outside the trip, at {tick}"
            self.hung.setdefault(int(tick), []).append(command.replace("{ns}", NS))


class Player:
    def __init__(self, name):
        self.name, self.tags, self.online, self.seat = name, set(), True, None
        self.where, self.titles, self.turned, self.faced = "nowhere", [], 0.0, []


class Game:
    """A server with the opening's functions, the train's three and the map's `back`."""

    def __init__(self, train=None, runs=True):
        self.train = train or Train()
        self.trip = A.Trip(self.train)
        for command, ticks in A.hung(self.trip):
            self.train.run(command, at=list(ticks))
        opening = {"first": A.first(), "join": A.join()}
        self.functions = {f"{NS}:{name}": [ln.replace("{ns}", NS) for ln in lines if not ln.startswith("#")]
                          for name, lines in {**T.functions(opening=opening), **A.functions()}.items()}
        self.players, self.scores, self.schedule = {}, {}, {}
        self.seats = [None] * SEATS             # who sits on each
        self.now, self.runs = 0, runs           # runs: False, a train that never leaves the line's end
        self.at = None                          # the trip's tick, None while the train rests
        self.calls = []

    # ---- the train's and the map's functions --------------------------------------------------------
    def state(self):
        if self.at is None:
            return 0
        return 1 if self.at < self.trip.arrive else 2 if self.at < self.trip.leave else 3

    def depart(self):
        if self.runs:
            self.at = -1                        # its tick 0 is run with the next tick of the game
            self.scores[(A.STATE, A.STATES)] = 1

    def builtin(self, name, player):
        self.calls.append((self.now, name, player.name if player else None))
        if name == f"{NS}:train/go":
            if self.at is None:
                self.depart()
        elif name == f"{NS}:train/restart":
            self.depart()
        elif name == f"{NS}:train/board":
            if player.seat is None and None in self.seats:
                player.seat = self.seats.index(None)
                self.seats[player.seat] = player.name
                player.where = "seat"
        elif name == "c164map:back":
            assert player.seat is None, "the map's tp would throw a rider off: dismount first"
            player.where = "spot"
        else:
            raise AssertionError(f"no function {name}")

    # ---- the commands --------------------------------------------------------------------------------
    def select(self, selector, me):
        if selector == "@s":
            return [me] if me is not None and me.online else []
        m = re.fullmatch(r"@([as])(?:\[(.*)\])?", selector)
        assert m, selector
        pool = [p for p in self.players.values() if p.online] if m.group(1) == "a" else ([me] if me else [])
        for key, value in re.findall(r"(\w+)=(\{[^}]*\}|[^,\]]+)", m.group(2) or ""):
            if key == "tag":
                pool = [p for p in pool if (value[1:] not in p.tags) if value.startswith("!")] if value.startswith("!") \
                    else [p for p in pool if value in p.tags]
            elif key == "scores":
                objective, span = value.strip("{}").split("=")
                pool = [p for p in pool if self.within(self.scores.get((p.name, objective)), span)]
            else:
                raise AssertionError(f"{selector}: {key}")
        return pool

    @staticmethod
    def within(value, span):
        if value is None:
            return False
        lo, _, hi = span.partition("..") if ".." in span else (span, "", span)
        return (lo == "" or value >= int(lo)) and (hi == "" or value <= int(hi))

    def run(self, line, me=None):
        words = line.split()
        if words[0] == "execute":
            return self.execute(words[1:], [me])
        if words[0] == "function":
            return self.call(words[1], me)
        if words[0] == "schedule":
            assert words[1] == "function" and words[3].endswith("t")
            self.schedule[words[2]] = self.now + int(words[3][:-1])        # the game's "replace"
            return 1
        if words[0] == "tag":
            for p in self.select(words[1], me):
                (p.tags.add if words[2] == "add" else p.tags.discard)(words[3])
            return 1
        if words[0] == "scoreboard":
            if words[1] == "objectives":
                return 1
            who = [p.name for p in self.select(words[3], me)] if words[3].startswith("@") else [words[3]]
            if words[2] == "get":
                value = self.scores.get((who[0], words[4]))
                return 0 if value is None else value
            for name in who:
                old = self.scores.get((name, words[4]), 0)
                self.scores[(name, words[4])] = int(words[5]) + (old if words[2] == "add" else 0)
            return 1
        if words[0] == "ride":
            assert words[1:] == ["@s", "dismount"]
            if me.seat is not None:
                self.seats[me.seat], me.seat, me.where = None, None, "beside the car"
            return 1
        if words[0] == "kill":
            assert words[1] == "@s" and isinstance(me, int)            # a seat
            return 1
        if words[0] == "rotate":
            assert words[1] == "@s"
            if words[2].startswith("~"):
                me.turned += float(words[2][1:] or 0)
            else:
                me.faced.append((self.now, float(words[2])))
                me.turned = 0.0
            return 1
        if words[0] == "title":
            for p in self.select(words[1], me):
                if words[2] == "title":
                    p.titles.append((self.now, p.where, self.at))
            return 1
        raise AssertionError(f"not a command this file knows: {line}")

    def execute(self, words, who):
        """`who`: the executors so far; a player, or a seat's number after `on vehicle`."""
        store = None
        while words[0] != "run":
            if words[0] == "as":
                who = [p for me in who for p in self.select(words[1], me)]
                words = words[2:]
            elif words[0] in ("if", "unless") and words[1] == "entity":
                want = words[0] == "if"
                who = [me for me in who if bool(self.select(words[2], me)) == want]
                words = words[3:]
            elif words[0] in ("if", "unless") and words[1] == "score":
                assert words[4] == "matches"
                ok = self.within(self.scores.get((words[2], words[3])), words[5])
                who = who if ok == (words[0] == "if") else []
                words = words[6:]
            elif words[:2] == ["on", "vehicle"]:
                who = [me.seat for me in who if me.seat is not None]
                words = words[2:]
            elif words[:2] == ["on", "passengers"]:
                who = [self.players[self.seats[seat]] for seat in who if self.seats[seat] is not None]
                words = words[2:]
            elif words[:3] == ["store", "result", "score"]:
                store, words = (words[3], words[4]), words[5:]
            else:
                raise AssertionError(f"execute {' '.join(words)}")
        line, out = " ".join(words[1:]), 0
        for me in who:
            if line == "kill @s" and isinstance(me, int):
                rider = self.players[self.seats[me]]                    # the seat goes, and its rider stands
                self.seats[me], rider.seat, rider.where = None, None, "beside the car"
                out = 1
            else:
                out = self.run(line, me)
        if store is not None:
            self.scores[store] = int(out or 0)
        return out

    def call(self, name, me=None):
        if name not in self.functions:
            self.builtin(name, me)
            return 1
        self.calls.append((self.now, name, getattr(me, "name", None)))
        for line in self.functions[name]:
            self.run(line, me)
        return 1

    # ---- time, and what a player does ---------------------------------------------------------------
    def tick(self, n=1):
        for _ in range(n):
            self.now += 1
            due = sorted(name for name, when in self.schedule.items() if when <= self.now)
            for name in due:
                del self.schedule[name]
                self.call(name)
            if self.at is not None:
                self.at += 1
                self.scores[(A.STATE, A.STATES)] = self.state()
                for command in self.train.hung.get(self.at, ()):
                    self.run(command)
                if self.at >= self.trip.home:
                    self.at = None
                    self.scores[(A.STATE, A.STATES)] = 0

    def new(self, name):
        """The map's `first`: its own mark, the spot, its `join` and then the hook."""
        p = self.players[name] = Player(name)
        p.tags.add(A.SEEN)
        p.where = "spot"
        self.call(f"{NS}:{T.JOIN}", p)
        self.call(f"{NS}:{T.FIRST}", p)
        return p

    def old(self, name):
        p = self.players[name] = Player(name)
        p.tags.add(A.SEEN)
        p.where = "spot"
        return p

    def sneak(self, p):
        self.seats[p.seat], p.seat, p.where = None, None, "beside the car"

    def leave(self, p):
        p.online = False                       # his seat goes into his file with him

    def back(self, p):
        p.online = True
        self.call(f"{NS}:{T.JOIN}", p)

    def done(self, p, titles=1):
        ours = {T.MARK, T.RIDE, A.ON, A.FWD}
        assert p.where == "spot" and p.seat is None, (p.name, p.where)
        assert not p.tags & ours, (p.name, p.tags)
        assert len(p.titles) == titles, (p.name, p.titles)


def test_trip():
    trip = A.Trip(Train())
    assert (trip.arrive, trip.leave, trip.home) == (940, 1340, 2280)
    assert trip.facing == 180.0 and abs(trip.turned + 90.0) < 0.011             # a quarter turn to the left
    assert trip.ahead[0] == 0 and trip.ahead[-1] < min(min(t) for t in trip.turns.values())
    assert trip.out + T.FADE_IN + T.STAY + T.FADE_OUT <= min(min(t) for t in trip.turns.values()) + 40
    assert trip.longest() <= T.RIDE_MOST
    for command, ticks in A.hung(trip):
        assert ticks == sorted(set(ticks)) and 0 <= ticks[0] and ticks[-1] <= trip.home, command


def test_alone_train_at_rest():
    g = Game()
    p = g.new("a")
    assert p.seat == 0 and A.ON in p.tags
    g.tick(g.trip.out + 1)
    assert p.faced == [(1, 180.0)] and A.FWD in p.tags                  # turned to look up the line as it leaves
    assert [t[1:] for t in p.titles] == [("seat", g.trip.out)]          # the title, over the cloud, in his seat
    g.tick(g.trip.arrive + A.AFTER - g.trip.out)
    assert abs(p.turned + 90.0) < 0.011                                 # turned with the car, a quarter turn
    g.done(p)
    assert g.now == g.trip.arrive + A.AFTER + 1 <= 960
    g.tick(3000)
    g.done(p)                                                           # and nothing more is said, ever
    assert not g.schedule                                               # nor does anything run for nobody


def test_alone_train_away():
    g = Game()
    g.depart()
    g.tick(1500)                                                        # an empty train on its way down
    assert g.state() == 3
    p = g.new("a")
    assert (g.now, f"{NS}:train/restart", "a") in g.calls
    g.tick(g.trip.arrive + A.AFTER + 1)
    g.done(p)
    assert [t[1:] for t in p.titles] == [("seat", g.trip.out)]


def test_a_second_one_comes_alone_after_him():
    g = Game()
    p = g.new("a")
    g.tick(300)
    q = g.new("b")                                                      # the train is not fetched from under a rider
    assert not [c for c in g.calls if c[1].endswith("restart")] and q.seat == 1
    assert q.faced == [] and A.FWD not in q.tags
    g.tick(20)
    assert q.faced == [(301, 180.0)] and A.FWD in q.tags                # on the straight still: he looks ahead too
    g.tick(g.trip.arrive + A.AFTER - g.at)
    g.done(p)
    g.done(q)
    assert abs(q.turned + 90.0) < 0.011 and q.titles[0][1] == "seat"


def test_others_looking_on():
    g = Game()
    g.old("o")
    g.depart()
    g.tick(1000)                                                        # the train stands in the station
    assert g.state() == 2
    p = g.new("a")
    assert not [c for c in g.calls if c[1].endswith("restart")] and p.seat == 0
    g.tick(g.trip.home - g.at + A.GAP + 2)                              # down with it, and off again at once
    assert g.at is not None and g.at <= 2 and p.seat == 0
    g.tick(g.trip.arrive + A.AFTER)
    g.done(p)
    assert [t[1:] for t in p.titles] == [("seat", g.trip.out)]
    assert g.now - 1000 <= T.RIDE_MOST


def test_gets_in_on_the_way_up():
    g = Game()
    g.old("o")
    g.depart()
    g.tick(500)                                                         # on the curve
    p = g.new("a")
    g.tick(100)
    assert p.faced == [] and p.turned == 0.0 and A.FWD not in p.tags    # he keeps the way the platform gave him
    assert len(p.titles) == 1 and p.titles[0][1] == "seat" and 540 <= p.titles[0][2] <= 560
    g.tick(g.trip.arrive + A.AFTER - g.at)
    g.done(p)
    q = g.new("b")                                                      # the car has just stopped: no title in time
    g.tick(60)
    assert q.seat is not None and not q.titles


def test_gets_in_too_late_for_the_title():
    g = Game()
    g.old("o")
    g.depart()
    g.tick(g.trip.last)
    p = g.new("a")
    g.tick(g.trip.arrive + A.AFTER - g.at)
    assert p.where == "spot" and not p.titles and T.MARK in p.tags
    g.tick(T.WAIT)
    g.done(p)
    assert p.titles[0][1] == "spot"


def test_sneaks_off():
    g = Game()
    p = g.new("a")
    g.tick(100)
    g.sneak(p)
    g.tick(A.POLL)
    assert p.where == "spot" and T.RIDE not in p.tags
    g.tick(T.WAIT)
    g.done(p)
    assert p.titles[0][1] == "spot"
    q = g.new("b")                                                      # the train goes on without him; another gets in
    assert q.seat == 0
    g.tick(g.trip.arrive + A.AFTER - g.at)
    g.done(q)


def test_leaves_and_comes_back():
    for when, where in ((100, "spot"), (400, "seat")):                  # before his title, and after it
        g = Game()
        p = g.new("a")
        g.tick(when)
        g.leave(p)
        g.tick(60)
        assert f"{NS}:{A.WATCH}" not in g.schedule                      # nobody in the opening: nothing runs
        g.back(p)
        assert p.where == "spot" and p.seat is None and g.seats[0] is None
        g.tick(T.WAIT + 1)
        g.done(p)
        assert p.titles[0][1] == where


def test_thirteen_at_once():
    g = Game()
    ps = [g.new(f"p{i}") for i in range(13)]
    assert [p.seat for p in ps] == list(range(12)) + [None]             # the first to come sit in front
    assert len([c for c in g.calls if "train/go" in c[1] or "restart" in c[1]]) == 1 and g.at == -1
    g.tick(A.TRIES * A.POLL + A.POLL)
    assert ps[12].where == "spot" and T.RIDE not in ps[12].tags
    g.tick(g.trip.arrive + A.AFTER)
    for p in ps:
        g.done(p)
    assert ps[12].titles[0][1] == "spot" and all(p.titles[0][1] == "seat" for p in ps[:12])


def test_train_that_never_comes():
    g = Game(runs=False)
    p = g.new("a")
    assert p.seat == 0
    g.tick(T.RIDE_MOST - T.WAIT)
    assert p.where == "spot"
    g.tick(T.WAIT)
    g.done(p)


def test_without_the_opening():
    lines = T.functions()
    assert lines[T.FIRST][1:] == [f"tag @s add {T.MARK}", f"schedule function {{ns}}:{T.SHOW} {T.WAIT}t"]
    assert not any("arrival" in ln or "train" in ln for fn in lines.values() for ln in fn if not ln.startswith("#"))


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("ok", test.__name__)
    print(f"{len(tests)} tests passed")
