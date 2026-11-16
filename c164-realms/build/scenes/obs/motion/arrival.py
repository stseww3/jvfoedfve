"""motion/arrival: the opening. Whoever comes to the map for the first time rides up out of the
cloud in the train and gets off at the summit station (plan/round2.md, "甲 火车是开场"; card
plan/packages/motion/arrival.md). Importing the module builds nothing.

What a newcomer gets
    the ride     He is seated in the car the moment he joins, the first to come in the front row
                 (the train's own board: machines/train numbers the seats from the uphill end).
                 Where the train is then decides what follows:
                   it rests at the line's end, under the cloud: it leaves at once;
                   it is away, nobody sits in it and nobody else is in the map who could see it
                   go: it is fetched back to the line's end (the kit's restart) and leaves at once.
                   So who comes alone always has the whole ride, and never waits;
                   it is away and somebody rides in it or looks on: he is seated in it where it
                   is. Going up he has the rest of the ride. Standing in the station or going
                   down he stays in it, down into the cloud, and it leaves again the moment it is
                   home (a train with somebody in it does not rest). Nobody ever sits and waits
                   in the cloud for a train to come.
    the look     Who sits in the car when it leaves the line's end, or gets in while it runs up the
                 straight, is turned to look ahead, level; from then on he is turned with the car
                 round the curve, a fifth of a degree a tick, as much as the car's body turns.
                 The turning is added to where he looks, so his mouse stays his own. Who gets in
                 further up keeps the way the platform gave him, west: the mountain.
    the title    Once, as his eye comes up over the highest cloud top (OUT): the map's name over
                 cloud and sky, gone before the line turns in towards the mountain. He must have
                 sat for two seconds by then, his game showing its "loading terrain" until then;
                 who has not is shown it at the next of the train's steps, and nobody later than
                 LAST, when it could not go out again before the station. On the platform nothing
                 is said: the arrival view is clean (the director, 11-16 13:17).
    the end      AFTER ticks after the car has come to rest in the station: off the seat and on
                 to the map's spot, facing the main building (c164map:back, the map's own: the
                 package writes no coordinates of a player's).

What else may happen
    he gets off  Sneaking leaves a seat, as it does everywhere in the game. Within POLL ticks he
                 stands on the spot; that is the way to pass the opening by.
    he leaves    Who leaves the game in the middle of it takes his seat with him (the game keeps a
                 lone rider's mount in his file). When he comes back he is put on the spot and the
                 seat he brought is removed: the kit makes the train's seats whole again before
                 its next departure, and two of one number must not be.
    no seat      The car has twelve. A thirteenth at once, or a train that is not there: after
                 TRIES tries he stands on the spot.
    the train stops  Nothing a train does keeps a man off the map: T.RIDE_MOST ticks after he
                 joined at the latest he stands on the spot, whatever the train does.
    the title, then  Who comes to the spot in one of these ways without having been shown the
                 title is shown it there two seconds later, as it was before there was a train
                 (guide/title).
    again        Who has been here before does not ride, nor does who falls off the mountain and
                 is put back: the map's function tag `first` runs once for a player.

How
    Functions in the data pack, registered with the motion kit (MK.function):
        guide/first    as who is new, once: marks him, sends for the train, seats him
        guide/join     as whoever joins: who comes back in the middle of the opening
                       (both are motion/guide-title's names, which the map's function tags call;
                       with the opening on their lines are first() and join() here)
        arrival/fetch  as the newcomer: the train's go, or its restart, or neither
        arrival/board  as one who is to ride: the train's board; seated, he is marked ON
        arrival/watch  every POLL ticks for as long as somebody is in the opening, and at no
                       other time: who has left his seat, who has no seat yet, who rides too long
        arrival/end    as one whose ride is over, however it ended
        arrival/again  as one who comes back in the middle of it
        arrival/title  the title, to those in the car who are owed it
        arrival/next   the train's go: it is home with somebody in it
    and commands hung on the train's trip (train.run), which keep the train's time whatever it
    does: who looks ahead (the steps of the straight), the turning (the ticks of the curve), the
    title (OUT and the steps after it), the end (the stop and AFTER), and at home, with somebody
    in it, arrival/next.
    Marks on a player: T.MARK, owed the title; T.RIDE, in the opening; ON, has been seated; FWD,
    is turned with the car; UP, found on a seat by this watch. CLOCK, a scoreboard objective of
    the package's own (made by guide/first; a data pack has no other place for it), counts a
    player's watches: his tries until he is seated, then how long he has sat.
    Whether a player is on a seat is asked of the game itself (execute on vehicle on passengers),
    not of a mark.

What it costs (agreed with the loop's keeper, a2, 11-16 13:11)
    With nobody in the opening: the commands on the train's trip, which find nobody. One a tick
    through the curve (about five hundred ticks of the three thousand), two at each of the
    straight's steps, one at each step the title may come on. With somebody in it: arrival/watch,
    eight commands every POLL ticks. Fetching the train back clears its pending functions, some
    two thousand commands in one tick, once, and only when nobody is there to feel it.

The switches are the main scene's: GUIDE off and there is no hook, ARRIVAL off (tools/export.py
--no-arrival) and who is new stands on the platform and is shown the title there, as in A8, while
the train keeps its timetable. In a tree or a scene without the train it is the same.
"""
from ..site import _rail as RAIL
from . import _kit as MK
from . import guide_title as T

TRAIN = "train"                 # the train's name with the motion kit (machines/train)
ON = "c164.on"                  # has been seated in the car
FWD = "c164.fwd"                # is turned with the car
UP = "c164.up"                  # found on a seat by this watch
SEEN = "c164.in"                # the map's own mark of who has been greeted (tools/export.py: IN_TAG)
CLOCK = "c164a"                 # scoreboard objective: a player's watches
STATE = f"#t.{TRAIN}"           # the kit's score of the train: 0 while it rests at the line's end
STATES = "c164m"                # ... and its objective

EYE = 1.93                      # blocks from the rails to a rider's eye on the level and the viaduct: the bench's
#                                 top 14.5 pixels over the rails and 1.02 from there (cable #92328)
OUT = RAIL.s_of_level(RAIL.CLOUD - EYE)     # 149.4: where the car's middle is when that eye is level with the
#                                             highest cloud top beside the line
POLL = 2                        # ticks from watch to watch
TRIES = 30                      # watches a newcomer is tried to be seated: three seconds
SAT = T.WAIT // POLL            # watches he has sat before a title is sent him: his game has loaded by then
AFTER = 10                      # ticks the car has stood in the station when its riders get off
GAP = 2                         # ticks from the train's coming home to its going again with somebody in it
FINE = 0.01                     # degrees: the turning is written in hundredths

FETCH, BOARD, WATCH, END = "arrival/fetch", "arrival/board", "arrival/watch", "arrival/end"
AGAIN, TITLE, NEXT = "arrival/again", "arrival/title", "arrival/next"


def on():
    """The main scene's switches, as they stand now: the guide's and the opening's."""
    return T.guide() and bool(getattr(T._of(""), "ARRIVAL", False))


def train(canvas):
    """The train on the canvas, when the opening is on and the kit has one of that name; or None."""
    trains = getattr(MK, "trains", None)
    return trains(canvas).get(TRAIN) if on() and trains is not None else None


def _turn(a):
    """An angle brought to -180 .. 180."""
    return (a + 180.0) % 360.0 - 180.0


def _angle(a):
    text = f"{a:.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


class Trip:
    """What the opening reads off the train's timetable. Ticks of the trip, 0 its departure from
    the line's end:
        arrive, leave   it stands in the station from the one to the other
        home            it is at the line's end again
        out             the car's middle passes OUT on the way up
        last            the last tick a title may be sent on: it has gone out before the station
        ahead           the steps on which the car still heads as it did at the line's end
        turns           {hundredths of a degree: [ticks]}: what the car's body has turned by that
                        tick since the tick before, on the way up, the game's yaw
        facing          the game's yaw of one who looks up the line at its end
    """

    def __init__(self, train_):
        stops = sorted(tuple(stop) for stop in train_.stops)
        station = [stop for stop in stops if abs(stop[2] - RAIL.STOP) < 0.01]
        if not station:
            raise ValueError("motion/arrival: the train's timetable has no stop at the station (site/_rail.STOP)")
        self.step = int(train_.step)
        self.arrive, self.leave = int(station[0][0]), int(station[0][1])
        self.home = next((int(stop[0]) for stop in stops if stop[0] > self.leave and abs(stop[2] - RAIL.START) < 0.01),
                         None)
        if self.home is None:
            self.home = int(train_.tick(RAIL.START, nth=1))
        self.out = int(train_.tick(OUT))
        self.last = self.arrive - (T.FADE_IN + T.STAY + T.FADE_OUT)
        if not 0 < self.out <= self.last:
            raise ValueError(f"motion/arrival: the car is over the cloud at tick {self.out} and in the station at "
                             f"{self.arrive}: the title of {self.arrive - self.last} ticks has no room on the way")
        yaws = [train_.heading(tick)[0] for tick in range(self.arrive + 1)]
        self.ahead = []
        for tick in range(0, self.arrive, self.step):
            if abs(_turn(yaws[tick] - yaws[0])) >= FINE:
                break
            self.ahead.append(tick)
        self.turns, turned, written = {}, 0.0, 0
        for tick in range(1, self.arrive + 1):
            turned += _turn(yaws[tick] - yaws[tick - 1])
            now = int(round(turned / FINE))
            if now != written:
                self.turns.setdefault(now - written, []).append(tick)
                written = now
        self.turned = written * FINE
        self.facing = -_turn(-RAIL.at(RAIL.START).yaw - 180.0)       # north is 180, not -180

    def longest(self):
        """Ticks from a newcomer's joining to his standing on the platform at the most, when the
        train keeps its timetable: seated at the last try, just as the car has come to rest in the
        station with others looking on; down with it, up again, and off."""
        return TRIES * POLL + (self.home - self.arrive) + GAP + self.arrive + AFTER


def limit():
    """Watches a player may sit in the car: after them he is put on the spot whatever the train does."""
    return (T.RIDE_MOST - TRIES * POLL) // POLL - 1


def hung(trip):
    """[(command, ticks)]: what hangs on the train's trip, in the order it is registered (the kit
    runs the commands of one tick in that order, after the train's own)."""
    late = f"@a[tag={ON},tag=!{FWD}]"
    owed = f"@a[tag={ON},tag={T.MARK},scores={{{CLOCK}={SAT}..}}]"
    out = [
        # who sits in the car as it leaves, and who gets in on the straight: he looks up the line
        (f"execute as {late} run rotate @s {_angle(trip.facing)} 0", trip.ahead),
        (f"tag {late} add {FWD}", trip.ahead),
    ]
    # ... and is turned with the car
    for by in sorted(trip.turns, key=lambda by: -len(trip.turns[by])):
        out.append((f"execute as @a[tag={FWD}] run rotate @s ~{_angle(by * FINE)} ~", trip.turns[by]))
    out += [
        # the title, over the cloud; who has only just sat down at one of the steps after it
        (f"execute if entity {owed} run function {{ns}}:{TITLE}",
         [trip.out] + [tick for tick in range(0, trip.last + 1, trip.step) if tick > trip.out]),
        # the car stands in the station
        (f"execute as @a[tag={ON}] run function {{ns}}:{END}", [trip.arrive + AFTER]),
        # home with somebody in it: no rest
        (f"execute if entity @a[tag={ON}] run schedule function {{ns}}:{NEXT} {GAP}t", [trip.home]),
    ]
    return out


def first():
    """The lines of guide/first after the newcomer has been marked."""
    return [
        f"tag @s add {T.RIDE}",
        f"scoreboard objectives add {CLOCK} dummy",
        f"scoreboard players set @s {CLOCK} 0",
        f"function {{ns}}:{FETCH}",
        f"function {{ns}}:{BOARD}",
        f"schedule function {{ns}}:{WATCH} {POLL}t",
    ]


def join():
    """The lines of guide/join that are the opening's."""
    return [f"execute if entity @s[tag={T.RIDE}] run function {{ns}}:{AGAIN}"]


def functions(name=None):
    """{name: [lines]} of the opening's own functions, as MK.function() takes them."""
    riders = f"@a[tag={T.RIDE}]"
    seated = f"@a[tag={ON},tag={T.MARK},scores={{{CLOCK}={SAT}..}}]"
    unseated = f"tag={T.RIDE},tag=!{ON}"
    was = "#arrival"
    return {
        FETCH: [
            "# as the newcomer, before he is seated: the train is sent off, or fetched, or left to run",
            f"execute store result score {was} {CLOCK} run scoreboard players get {STATE} {STATES}",
            "# it rests at the line's end: off it goes",
            f"execute if score {was} {CLOCK} matches 0 run function {{ns}}:{TRAIN}/go",
            "# it is away, nobody sits in it and nobody else is here to see it go: back to the line's end, and off",
            f"execute unless score {was} {CLOCK} matches 0 unless entity @a[tag={ON}] "
            f"unless entity @a[tag={SEEN},tag=!{T.RIDE}] run function {{ns}}:{TRAIN}/restart",
        ],
        BOARD: [
            "# as one who is to ride and has no seat: the first free seat; seated, the count starts anew",
            f"function {{ns}}:{TRAIN}/board",
            f"execute on vehicle on passengers run tag @s add {ON}",
            f"execute if entity @s[tag={ON}] run scoreboard players set @s {CLOCK} 0",
        ],
        WATCH: [
            f"# every {POLL} ticks while somebody is in the opening",
            f"tag @a[tag={UP}] remove {UP}",
            f"execute as {riders} on vehicle on passengers run tag @s add {UP}",
            f"scoreboard players add {riders} {CLOCK} 1",
            "# he has left his seat, or has sat longer than any ride lasts",
            f"execute as @a[tag={ON},tag=!{UP}] run function {{ns}}:{END}",
            f"execute as @a[tag={ON},scores={{{CLOCK}={limit()}..}}] run function {{ns}}:{END}",
            "# no seat yet: once more; after the last try, the platform",
            f"execute as @a[{unseated},scores={{{CLOCK}=..{TRIES}}}] run function {{ns}}:{BOARD}",
            f"execute as @a[{unseated},scores={{{CLOCK}={TRIES + 1}..}}] run function {{ns}}:{END}",
            f"execute if entity {riders} run schedule function {{ns}}:{WATCH} {POLL}t",
        ],
        END: [
            "# as one whose ride is over: the car stands in the station, or he got off, or there was no seat",
            "ride @s dismount",
            f"tag @s remove {ON}",
            f"tag @s remove {FWD}",
            f"tag @s remove {T.RIDE}",
            "function c164map:back",
            "# not shown the title on the way: on the platform, as before there was a train",
            f"execute if entity @s[tag={T.MARK}] run schedule function {{ns}}:{T.SHOW} {T.WAIT}t",
        ],
        AGAIN: [
            "# as one who comes back in the middle of the opening: the seat he left on came back with him",
            "execute on vehicle run kill @s",
            f"function {{ns}}:{END}",
        ],
        TITLE: ["# the map's name, once, to those in the car who have not been shown it"] + T.show(seated, name),
        NEXT: [
            "# the train is home with somebody in it: off again",
            f"function {{ns}}:{TRAIN}/go",
        ],
    }


def build(canvas, origin=(0, 0, 0)):
    """Register the opening on the canvas: its functions, and what hangs on the train's trip."""
    train_ = train(canvas)
    if train_ is None:
        return 0
    trip = Trip(train_)
    if trip.longest() > T.RIDE_MOST:
        raise ValueError(f"motion/arrival: by the train's timetable a newcomer may be {trip.longest()} ticks on "
                         f"the way, and guide_title.RIDE_MOST promises {T.RIDE_MOST}")
    for name, lines in functions().items():
        MK.function(canvas, name, lines)
    for command, ticks in hung(trip):
        train_.run(command, at=list(ticks))
    return 0
