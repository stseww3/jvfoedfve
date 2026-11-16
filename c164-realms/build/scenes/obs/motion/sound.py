"""motion/sound.py -- the sounds of the place: the table of our sound events and the spots they are heard at.

Card plan/packages/motion/sound.md; detail plan/parts/motion.md section 8; ART-PLAN 9 and 12.6.

No sound is added to the game. The resource pack gets one file, assets/c164/sounds.json, in which
every event of ours points at a sound event the game ships (a sound of "type": "event") and says
how loud and how high it is played: the table EVENTS below. A sound is tuned there, in one place,
and the data pack never changes with it. An event of ours has no subtitle.

The data pack plays our events at fixed spots, to the players near enough to hear them, through
the motion loop: every spot is one line of MK.sound and motion/_kit writes the functions. A sound
that goes with a moving part has the part's period, so the two are on one chain and stay in step:
a clock ticks as its pendulum passes the plumb line, the engine beats as its crank passes the dead
centre.

    from scenes.obs.motion import sound
    sound.place(canvas, "tick", pos, reach=8.0)      # one spot of a kind, for whoever places a clock
    sound.build(canvas, origin)                       # every spot of the master scene
    sound.pack(pack_dir)                              # assets/c164/sounds.json
    sound.spots(canvas)                               # what is registered: python -m scenes.obs_mot_sound spots

What is heard where (build()):
    tick        the master clock in the star hall, and every regulator clock that stands on the canvas
    engine      the steam engine's cylinder, once a turn of the flywheel
    hum         the dynamo
    fire        the fire door of the boiler that has just been fired
    hiss        that boiler's safety valve: VALVE says when it blows, for the steam of motion/smoke
    telegraph   the sounder in the time room, once machines/rec has put it there
    wind        the head of the grand stair, the lookout of the clock tower, the south lookout

A spot is registered only when the package that owns the thing is in the tree; its position is
read from that package's own numbers.

The second round (plan/round2.md: everything moves). A thing that moves on a time of its own
says itself when it is heard, in one line beside the line that makes it move:

    sound.place(canvas, "strike", pos, reach=96.0, cycle=6000, at=(0, 60, 120))

The kinds for that are in KINDS below the first round's, with what each is meant for; the time a
kind has there is only what the test scene plays it on. The train's sounds go with the train
(TRAIN: when its exhaust beats, its whistle blows, its steam is let off and the station's bell
rings, for motion/smoke as well). Three things play a tune, each in one line:

    sound.chimes(canvas, bells, 2, cycle, at=tick)       # the tower clock chimes the half hour
    sound.strikes(canvas, bells, 7, cycle, at=tick)      # ... and strikes seven
    sound.gramophone(canvas, horn, reach=6.0)             # a waltz, once a minute

How far a sound carries. The game fades a sound evenly to nothing over the distance its own event
is given (16 blocks unless the game says otherwise: a piston 8, a beacon 7), times the volume it is
played at when that is more than 1. A sound of ours inherits the distance of the game's sound it
points at. So a sound that has to fill a room larger than that distance is played with a volume
above 1 (CARRY): it then carries CARRY times as far, and is at its full loudness at the spot. The
others are played with volume 1 and are as loud at the spot as the table says. A sound in stereo
(the wind) is not placed in space by the game at all: whoever is sent it hears it at the table's
volume, wherever he stands.

0 display entities, 0 blocks.
"""
import json
import os
import re
import struct
import zipfile

from . import _kit as MK

NS = MK.NS                      # "c164": the namespace of our events
GAME = "minecraft"

# ---- the table: our event -> (the game's event it plays, volume, pitch) ----------------------------
# Volume and pitch multiply what the game's own event has. First guesses on the candidates of
# plan/parts/motion.md 8, to be set by ear on the real machine (card: "listened to, then settled").
EVENTS = {
    "tick": ("block.note_block.hat", 0.30, 1.20),           # the pendulum passes the plumb line going one way
    "tock": ("block.note_block.hat", 0.30, 1.00),           # ... and coming back: the same click, a tone lower
    "engine": ("block.piston.extend", 1.00, 0.60),          # the steam engine's stroke
    "hum": ("block.beacon.ambient", 1.00, 0.50),            # the dynamo: the beacon's drone an octave down
    "fire": ("block.blastfurnace.fire_crackle", 0.60, 1.00),    # the boiler's fire
    "hiss": ("block.fire.extinguish", 0.35, 0.70),          # the safety valve blows
    "telegraph": ("block.stone_button.click_on", 1.50, 2.00),       # the sounder's armature comes down
    "telegraph_up": ("block.stone_button.click_off", 1.50, 2.00),   # ... and goes back up
    "wind": ("item.elytra.flying", 0.25, 0.85),             # the wind over the hill's open edges
    # ---- the second round. The game's bell is twelve times as loud as its number says (its own
    # table gives it the volume 12, and the client cuts what is above 1): 0.083 here is its full
    # loudness when it is played with the volume 1
    "whistle": ("block.note_block.flute", 1.00, 0.84),      # the engine's whistle: the lower of its two notes
    "whistle_hi": ("block.note_block.flute", 0.90, 1.00),   # ... and the upper, a minor third over it
    "chuff": ("block.piston.extend", 1.00, 0.90),           # one beat of the engine's exhaust
    "rail": ("entity.minecart.riding", 0.60, 0.90),         # wheels on rails: the train, a coal tub
    "bell": ("block.bell.use", 0.07, 1.50),                 # the station's bell, one stroke
    "strike": ("block.bell.use", 0.083, 0.55),              # the tower clock's hour bell, one stroke
    "chime": ("block.bell.use", 0.07, 0.80),                # its quarter bell, one stroke
    "clank": ("block.heavy_core.place", 1.00, 0.80),        # iron comes down on iron: the time ball, a signal's arm
    "creak": ("block.copper_door.open", 0.60, 0.70),        # a vane, a wind pump, a shutter turns on its pin
    "thump": ("block.barrel.close", 1.00, 0.70),            # a carrier of the pneumatic post arrives
    "spark": ("entity.firework_rocket.twinkle", 0.35, 1.60),    # the spark gap
    "drip": ("block.pointed_dripstone.drip_water_into_cauldron", 1.00, 1.00),   # a tap drips into a sink
    "scratch": ("ui.cartography_table.take_result", 0.60, 1.00),    # a pen on paper: the engraving machine, a recorder
    "rumble": ("entity.minecart.riding", 0.50, 0.60),       # something heavy rolls slowly: the dome on its rollers
    "grind": ("block.grindstone.use", 1.00, 0.50),          # gears under load: a winch, the dome's drive
    "water": ("block.water.ambient", 0.50, 1.00),           # running water: a fountain
    "bubble": ("block.bubble_column.upwards_ambient", 0.50, 1.20),  # the cells of the battery gas
    # the gramophone (gramophone() below): its three voices, each note at its own pitch, and the needle
    "gram": ("block.note_block.harp", 0.35, 1.00),          # the voice that goes up the chord; F sharp 3 to F sharp 5
    "gram_hi": ("block.note_block.flute", 0.28, 1.00),      # the voice that answers; F sharp 4 to F sharp 6
    "gram_low": ("block.note_block.bass", 0.40, 1.00),      # the bass; F sharp 1 to F sharp 3
    "needle": ("block.campfire.crackle", 0.12, 1.30),       # the needle in the groove
}

# ---- the other choices: what the test scene obs_mot_sound lets one hear beside the table ------------
# kind -> two more sets (the same events, another sound of the game), each with its CARRY. They are
# written into the test scene's own pack under the names <event>_b and <event>_c, never into the
# map's. Whoever has listened moves the set he likes into EVENTS.
OTHERS = {
    "tick": (
        ({"tick": ("block.wooden_button.click_on", 1.50, 2.00), "tock": ("block.wooden_button.click_off", 1.50, 2.00)}, 1.0),
        ({"tick": ("block.copper_bulb.turn_on", 0.60, 1.00), "tock": ("block.copper_bulb.turn_off", 0.60, 1.00)}, 1.0),
    ),
    "engine": (
        ({"engine": ("block.note_block.snare", 0.60, 0.50)}, 1.0),
        ({"engine": ("block.note_block.basedrum", 0.80, 0.50)}, 1.0),
    ),
    "hum": (
        ({"hum": ("block.conduit.ambient", 1.00, 0.50)}, 2.0),
        ({"hum": ("entity.bee.loop", 1.00, 0.50)}, 2.7),
    ),
    "fire": (
        ({"fire": ("block.smoker.smoke", 0.80, 0.80)}, 1.0),
        ({"fire": ("block.campfire.crackle", 0.60, 0.70)}, 1.0),
    ),
    "hiss": (
        ({"hiss": ("block.lava.extinguish", 0.30, 1.20)}, 1.0),
        ({"hiss": ("entity.puffer_fish.blow_out", 0.60, 0.50)}, 1.0),
    ),
    "telegraph": (
        ({"telegraph": ("block.copper_bulb.turn_on", 0.80, 1.60), "telegraph_up": ("block.copper_bulb.turn_off", 0.80, 1.60)}, 1.0),
        ({"telegraph": ("block.dispenser.fail", 0.50, 1.50), "telegraph_up": ("block.dispenser.dispense", 0.50, 1.50)}, 1.0),
    ),
    "wind": (
        ({"wind": ("block.dry_grass.ambient", 0.40, 1.00)}, 1.0),
        ({"wind": ("block.sand.idle", 0.10, 1.00)}, 1.0),
    ),
    # the train: a shrill single note and a deep hooter beside the two flutes; a soft heavy puff
    # and an airy one beside the piston; the click of the rail joints and a grinding beside the
    # rumble; a small glockenspiel bell and a struck plate beside the bell
    "whistle": (
        ({"whistle": ("block.note_block.bit", 0.50, 0.75)}, 4.0),
        ({"whistle": ("block.note_block.didgeridoo", 1.00, 0.84)}, 4.0),
    ),
    "chuff": (
        ({"chuff": ("entity.ender_dragon.flap", 0.50, 1.60)}, 1.5),
        ({"chuff": ("entity.horse.breathe", 1.00, 0.60)}, 1.5),
    ),
    "rail": (
        ({"rail": ("entity.iron_golem.step", 0.50, 1.20)}, 1.5),
        ({"rail": ("block.grindstone.use", 0.80, 0.80)}, 1.5),
    ),
    "bell": (
        ({"bell": ("block.note_block.bell", 1.00, 1.40)}, 2.0),
        ({"bell": ("block.anvil.land", 0.60, 1.80)}, 2.0),
    ),
    # the tower's quarter bells: two sets that are in tune, tubular bells two octaves up and
    # metal bars at the pitch of the real ones (keynote E4)
    "chime": (
        ({"chime": ("block.note_block.chime", 1.00, 0.75)}, 5.0),
        ({"chime": ("block.note_block.iron_xylophone", 1.00, 0.891)}, 5.0),
    ),
}
LETTERS = "abc"                 # a choice is named by its letter: a is the table's, b and c are OTHERS

# ---- when: a kind of sound is one or more events on one cycle ---------------------------------------
# The valve: the safety valve of the boiler that has just been fired lifts once in VALVE["cycle"]
# ticks, at tick VALVE["at"] of that cycle, and blows for VALVE["blow"] ticks. The hiss starts on
# that tick; the steam of motion/smoke is to come on the same cycle and ticks (one chain, in step).
VALVE = dict(cycle=160, at=80, blow=30)
HUM_LOOP = 160                  # the beacon's drone lasts 5.8 s and the game plays it every 80 ticks; an octave down, both double
FIRE_LOOP = 100                 # the furnace's crackle is 5.0 to 6.1 s long
WIND_LOOP = 240                 # the flying wind is a loop of 10.2 s: 12.0 s at the pitch 0.85, played end to end


def _morse(text, unit, start=0):
    """The ticks on which a sounder's armature comes down and goes up when `text` is sent in Morse
    code with a dot of `unit` ticks: (downs, ups, the tick after the last)."""
    code = {"E": ".", "I": "..", "M": "--", "T": "-", "A": ".-", "N": "-.", "S": "...", "O": "---"}
    downs, ups, t = [], [], int(start)
    for letter in text:
        if letter == " ":
            t += 4 * unit                           # a word's gap is seven units: three are there already
            continue
        for mark in code[letter]:
            downs.append(t)
            t += unit if mark == "." else 3 * unit
            ups.append(t)
            t += unit
        t += 2 * unit                               # a letter's gap is three units
    return tuple(downs), tuple(ups), t


BLAST = 9                       # ticks from one sounding of the whistle to the next while it is held (a note lasts 0.7 s)
STROKE = 16                     # ticks from one stroke of the station's bell to the next
TELEGRAPH_LOOP = 300            # the sounder taps its word once in 15 s
TELEGRAPH_WORD = "TIME"         # what it taps: a dash, two dots, two dashes, a dot
_DOWN, _UP, _END = _morse(TELEGRAPH_WORD, 2)

# kind -> ((event, cycle, the ticks of the cycle it sounds on), ...). The tick goes with the
# pendulums: MK.PENDULUM ticks are one swing there and back, the pendulum hangs plumb at 0 and at
# half of it (plan/parts/motion.md 4: a second clock's pendulum may start half a cycle off; it
# passes the plumb line on the same ticks). The engine's crank is at its dead centre at tick 0 of
# MK.ENGINE_REV (machines/engine: the rest pose).
KINDS = {
    "tick": (("tick", MK.PENDULUM, (0,)), ("tock", MK.PENDULUM, (MK.PENDULUM // 2,))),
    "engine": (("engine", MK.ENGINE_REV, (0,)),),
    "hum": (("hum", HUM_LOOP, (0,)),),
    "fire": (("fire", FIRE_LOOP, (0,)),),
    "hiss": (("hiss", VALVE["cycle"], (VALVE["at"],)),),
    "telegraph": (("telegraph", TELEGRAPH_LOOP, _DOWN), ("telegraph_up", TELEGRAPH_LOOP, _UP)),
    "wind": (("wind", WIND_LOOP, (0,)),),
    # ---- the second round: the time is the caller's, place(..., cycle=, at=). What stands here is
    # what the test scene plays the kind on, and what a caller gets who names no time.
    "whistle": (("whistle", 200, (0, BLAST, 2 * BLAST, 60)),        # a long blast and a short one
                ("whistle_hi", 200, (0, BLAST, 2 * BLAST, 60))),
    "chuff": (("chuff", 5, (0,)),),                                 # four beats a second
    "rail": (("rail", 40, (0,)),),                                  # the rumble lasts 2.1 s: end to end
    "bell": (("bell", 200, tuple(range(0, 5 * STROKE, STROKE))),),  # five strokes
    "strike": (("strike", 400, (0, 60, 120)),),                     # three o'clock
    "chime": (("chime", 400, (0, 30, 60, 90)),),                    # the four quarters
    "clank": (("clank", 200, (0,)),),
    "creak": (("creak", 120, (0,)),),
    "thump": (("thump", 200, (0,)),),
    "spark": (("spark", 100, (0, 30)),),
    "drip": (("drip", 50, (0,)),),
    "scratch": (("scratch", 60, (0, 20)),),
    "rumble": (("rumble", 60, (0,)),),                              # 3.2 s at this pitch: end to end
    "grind": (("grind", 30, (0,)),),
    "water": (("water", 50, (0,)),),                                # 2.6 s: end to end
    "bubble": (("bubble", 60, (0,)),),
}
FIRST_ROUND = ("tick", "engine", "hum", "fire", "hiss", "telegraph", "wind")     # the kinds build() places itself

# ---- how far (see the head of the file) ---------------------------------------------------------------
# The volume a kind is played with when its sound has to carry further than the game's own does:
# the piston's 8 blocks and the beacon's 7 become 16, across the power house from the far corner.
CARRY = {"engine": 2.0, "hum": 2.3,
         # the second round: a whistle is heard 64 blocks off, the exhaust 24 (the piston's 8 times
         # 3), the rails 24, the station's bell 32, the tower's bells over the whole hilltop
         "whistle": 4.0, "chuff": 3.0, "rail": 1.5, "bell": 2.0, "strike": 6.0, "chime": 5.0, "rumble": 1.5}
SOURCE = {"wind": "ambient"}    # the player's volume slider a kind is under; the others are "block"


def far(kind, choice=0):
    """Blocks a kind is heard over when it is played as place() plays it: the reach to give a
    spot that is to be heard as far as the sound carries."""
    sets = choices(kind)
    held, carry = sets[choice]
    near = min(_FADE.get(target, 16.0) for target, _volume, _pitch in held.values())
    return near * max(1.0, carry)


# what the game's own table gives a sound to fade over where that is not 16 blocks (26.3)
_FADE = {"block.piston.extend": 8.0, "block.piston.contract": 8.0, "block.beacon.ambient": 7.0,
         "block.copper_bulb.turn_on": 6.0, "block.copper_bulb.turn_off": 6.0}


# ---- the train (card motion/train) ---------------------------------------------------------------------
def train_times(cycle, leave, arrive, depart, home, beat=5):
    """When the train is heard, in the ticks of one round of its timetable: for its sounds here
    and for its steam (motion/smoke reads the same table, so a puff and its beat are on one tick).

    cycle     the ticks of one round, from one start out of the cloud to the next
    leave     the tick the train starts up out of the cloud; arrive: it stands at the platform;
              depart: it starts back down; home: it stands in the cloud again
    beat      ticks from one beat of the exhaust to the next at full speed (a quarter of a turn
              of the driving wheels)

    Returns a dict:
    chuffs    ((first, last, every), ...): a beat on `first` and on every `every`-th tick after it
              that is before `last`. The engine works uphill only: it starts slowly, runs, and
              shuts off before the platform; downhill it holds the train back and is silent
    whistles  ((tick, ticks it is held), ...): out of the cloud, before the platform, before it leaves
    release   (tick, ticks): the engine lets off steam at the platform
    bell      ((tick, ticks), ...): the station's bell, while the train comes in and before it leaves
    """
    cycle, leave, arrive, depart, home, beat = (int(v) for v in (cycle, leave, arrive, depart, home, beat))
    if not 0 <= leave < arrive <= depart < home <= cycle:
        raise ValueError(f"motion/sound: a round goes 0 <= leave < arrive <= depart < home <= cycle, "
                         f"not {leave}, {arrive}, {depart}, {home}, {cycle}")
    if beat < 2:
        raise ValueError(f"motion/sound: a beat every {beat} ticks is no beat")
    climb, halt = arrive - leave, depart - arrive
    slow = min(40, climb // 4)
    chuffs = [(leave, leave + slow, 2 * beat), (leave + slow, arrive - slow, beat),
              (arrive - slow, arrive - min(10, slow // 2), 2 * beat)]
    chuffs = tuple((a, b, every) for a, b, every in chuffs if b > a)
    long_, short = 3 * BLAST, BLAST
    whistles = [(leave + min(20, climb // 8), long_)]
    if climb >= 300:
        whistles += [(arrive - 140, long_), (arrive - 100, short)]
    if halt >= 60:
        whistles += [(depart - 30, short), (depart - 12, short)]
    bell = [(max(leave, arrive - 120), min(120, climb))]
    if halt >= 100:
        bell.append((depart - 60, 60))
    release = (arrive + 6, max(10, min(60, halt - 12)))
    return dict(cycle=cycle, leave=leave, arrive=arrive, depart=depart, home=home, beat=beat, chuffs=chuffs,
                whistles=tuple(whistles), release=release, bell=tuple(bell))


def beats(times):
    """The ticks of a round on which the exhaust beats."""
    return tuple(t for a, b, every in times["chuffs"] for t in range(a, b, every))


def blasts(times):
    """The ticks of a round on which the whistle sounds: a blast that is held sounds every BLAST ticks."""
    return tuple(sorted({t for tick, held in times["whistles"] for t in range(tick, tick + held, BLAST)}))


def strokes(times):
    """The ticks of a round on which the station's bell is struck."""
    return tuple(sorted({t for tick, held in times["bell"] for t in range(tick, tick + held, STROKE)}))


# The timetable is its owner's (whoever calls the motion kit's travel for the train): until that
# is in the tree this stands in for it, so that the steam and the sounds can be written against
# the keys. A round of 150 s: 45 s up, 30 s at the platform, 40 s down.
TRAIN_STAND_IN = dict(cycle=3000, leave=0, arrive=900, depart=1500, home=2300)
TRAIN = train_times(**TRAIN_STAND_IN)

# Only players within the reach of a spot are sent its sound (blocks from the spot), which is what
# keeps a room's sound in the room.
REACH_STAR_HALL = 10.0          # the master clock stands at the pier; the hall's side walls are 6.5 away
REACH_CLOCK = 8.0               # a regulator clock on its wall
REACH_POWER_HOUSE = 16.0        # the engine and the dynamo: the room is 19 blocks square
REACH_BOILERS = 12.0            # the fire and the valve: the firing floor and the door
REACH_TELEGRAPH = 6.0           # the console of the time room
REACH_WIND = 16.0               # an open edge
REACH_TOWER = 6.0               # the lookout of the clock tower and no further down


def _events_of_the_game():
    """The names of the sound events of the game, read off the client jar (the string constants of
    net/minecraft/sounds/SoundEvents), or None when there is no jar to read (MC_JAR, or MC_ROOT)."""
    path = os.environ.get("MC_JAR") or os.path.join(os.environ.get("MC_ROOT", "/agent/realms-study"),
                                                     "client26", "versions", "26.3", "26.3.jar")
    if not os.path.isfile(path):
        return None
    with zipfile.ZipFile(path) as jar:
        try:
            data = jar.read("net/minecraft/sounds/SoundEvents.class")
        except KeyError:
            return None
    # the constant pool of a class file (JVMS 4.4): entry 1 .. count-1, a long or a double takes two
    count = struct.unpack(">H", data[8:10])[0]
    pos, i, utf8, strings = 10, 1, {}, []
    wide = {3: 4, 4: 4, 5: 8, 6: 8, 7: 2, 9: 4, 10: 4, 11: 4, 12: 4, 15: 3, 16: 2, 17: 4, 18: 4, 19: 2, 20: 2}
    while i < count:
        tag = data[pos]
        if tag == 1:
            size = struct.unpack(">H", data[pos + 1:pos + 3])[0]
            utf8[i] = data[pos + 3:pos + 3 + size].decode("utf-8", "replace")
            pos += 3 + size
        elif tag == 8:
            strings.append(struct.unpack(">H", data[pos + 1:pos + 3])[0])
            pos += 3
        elif tag in wide:
            pos += 1 + wide[tag]
            if tag in (5, 6):
                i += 1
        else:
            return None
        i += 1
    return {utf8[s] for s in strings if s in utf8}


def choices(kind):
    """The sets of a kind, the table's first: [({event: (the game's event, volume, pitch)}, carry), ...]."""
    if kind not in KINDS:
        raise ValueError(f"motion/sound: no kind of sound {kind!r}; there are {', '.join(sorted(KINDS))}")
    own = {event: EVENTS[event] for event, _cycle, _at in KINDS[kind]}
    return [(own, CARRY.get(kind, 1.0))] + [(dict(events), carry) for events, carry in OTHERS.get(kind, ())]


def _named(event, choice):
    return event if choice == 0 else f"{event}_{LETTERS[choice]}"


def events(others=False):
    """Every event that is written: the table's, and with others=True the other choices' as well."""
    out = dict(EVENTS)
    if others:
        for kind in KINDS:
            for n, (events_of, _carry) in enumerate(choices(kind)):
                for event, row in events_of.items():
                    out[_named(event, n)] = row
    return out


def table(rows=None):
    """What goes into assets/c164/sounds.json: {our event: {"sounds": [one sound of type "event"]}}."""
    out = {}
    for name, (target, volume, pitch) in sorted((rows or EVENTS).items()):
        out[name] = {"sounds": [{"name": f"{GAME}:{target}", "type": "event",
                                 "volume": float(volume), "pitch": float(pitch)}]}
    return out


def pack(pack_dir, others=False):
    """Write assets/c164/sounds.json: our events, each pointing at one of the game's. No audio file.
    others=True is the test scene's: the other choices are written beside the table."""
    rows = events(others)
    known = _events_of_the_game()
    if known is not None:
        missing = sorted({target for target, _v, _p in rows.values() if target not in known})
        if missing:
            raise ValueError(f"motion/sound: the game (26.3) has no sound event {', '.join(missing)}")
    path = os.path.join(pack_dir, "assets", NS, "sounds.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(table(rows), fh, indent=1, sort_keys=True)
        fh.write("\n")
    checked = "each checked against the game's own" if known is not None else "not checked: no client jar here"
    return [f"motion/sound: assets/{NS}/sounds.json, {len(rows)} events pointing at the game's sounds ({checked})"]


def place(canvas, kind, pos, reach, origin=(0, 0, 0), phase=0, choice=0, cycle=None, at=None, pitch=1.0):
    """One spot of a kind of sound ("tick", ...) at pos (scene coordinates, plus origin), heard by
    the players within `reach` blocks. choice 1 or 2 plays one of the OTHERS (the test scene).

    cycle, at   the caller's own time: the kind sounds on the ticks `at` of every `cycle` ticks
                (a thing that moves takes its own period, and is then in step with its sound).
                Without them the kind has the time KINDS gives it.
    pitch       0.5 to 2.0, times the table's: a second bell a tone lower is the same kind again

    Returns 0: a sound is no entity."""
    sets = choices(kind)
    if not 0 <= choice < len(sets):
        raise ValueError(f"motion/sound: {kind} has the choices 0 .. {len(sets) - 1}, not {choice}")
    if (cycle is None) != (at is None):
        raise ValueError("motion/sound: cycle= and at= are given together")
    if cycle is not None and len({ticks for _event, _cycle, ticks in KINDS[kind]}) > 1:
        raise ValueError(f"motion/sound: the events of {kind} sound on ticks of their own; it takes no time of the caller's")
    held, carry = sets[choice]
    for event, own_cycle, own_at in KINDS[kind]:
        if event in held:
            MK.sound(canvas, pos, _named(event, choice), own_cycle if cycle is None else cycle,
                     at=own_at if at is None else at, volume=carry, pitch=pitch, reach=reach,
                     source=SOURCE.get(kind, "block"), origin=origin, phase=phase)
    return 0


# ---- the gramophone -----------------------------------------------------------------------------------
# A short tune of note-block sounds for the gramophone of the cable station's duty room (the
# director, group message 86565): the opening of the waltz "An der schoenen blauen Donau" (Johann
# Strauss the younger, 1866: out of copyright everywhere), sixteen bars of it and a close of our own.
# One voice goes up the chord, a higher one answers twice, in thirds; a bass note on the first beat
# of a bar and two light notes after it. Then the record runs on in its last groove, the needle
# crackling, and the tune starts again.
GRAM_BEAT = 7                   # ticks to a crotchet (171 to the minute), three crotchets to a bar
GRAM_LEAD = 20                  # ticks the needle is heard before the first note
GRAM_LOOP = 1200                # one playing and the pause after it: a minute
NEEDLE_LOOP = 50                # the crackle is 1.7 to 3 s long
_STEPS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_LOWEST = {"gram": "F#3", "gram_hi": "F#4", "gram_low": "F#1"}     # the note an instrument of the game plays at the pitch 0.5
_UP = (("D4", "D4", "F#4", "A4", "A4"), ("D4", "D4", "F#4", "A4", "A4"),        # the voice that goes up the chord: four
       ("C#4", "C#4", "E4", "B4", "B4"), ("C#4", "C#4", "E4", "B4", "B4"))      # phrases, each from the bar's upbeat
_ANSWER = ((("A5", "F#5"), ("F#5", "D5")), (("A5", "F#5"), ("G5", "E5")),       # what answers each phrase: two pairs
           (("B5", "G5"), ("G5", "E5")), (("B5", "G5"), ("F#5", "D5")))         # of notes, each pair played twice
_CLOSE = ("D4", "D4", "F#4", "A4")                                               # the close: up the chord once more
_LAST = ("D4", "F#4", "A4", "D5")                                               # ... to the chord it ends on
_CHORD_OF = lambda q: "A" if 21 <= q <= 44 else "D"                             # noqa: E731  the harmony of a crotchet
_BASS = {"D": "D2", "A": "A2"}
_AFTER = {"D": ("F#3", "A3"), "A": ("G3", "C#4")}                               # the light notes on the second and third beat


def _key(note):
    """The number of a note's key ("F#4" is 66, middle C 60)."""
    name, octave = note[:-1], int(note[-1])
    return 12 * (octave + 1) + _STEPS[name[0]] + (1 if name.endswith("#") else 0)


def _pitch(event, note):
    """The pitch an instrument's event is played at to sound `note`."""
    steps = _key(note) - _key(_LOWEST[event])
    if not 0 <= steps <= 24:
        raise ValueError(f"motion/sound: {note} is outside the two octaves of {event}")
    return round(0.5 * 2.0 ** (steps / 12.0), 4)


def tune():
    """The gramophone's tune: [(tick of GRAM_LOOP, event, pitch, volume)], in the order of time.
    Crotchet 0 is the upbeat; a phrase is twelve crotchets, and bar n begins on crotchet 3 n - 2."""
    notes = []
    for phrase, (up, answer) in enumerate(zip(_UP, _ANSWER)):
        q = 12 * phrase
        notes += [(q + i, "gram", note, 1.0) for i, note in enumerate(up)]
        for pair, at in zip(answer, ((6, 7), (9, 10))):
            notes += [(q + i, "gram_hi", note, 1.0) for i in at for note in pair]
    notes += [(48 + i, "gram", note, 1.0) for i, note in enumerate(_CLOSE)]
    notes += [(52, "gram", note, 1.0) for note in _LAST]
    for bar in range(1, 19):
        q = 3 * bar - 2
        notes.append((q, "gram_low", _BASS[_CHORD_OF(q)], 1.0))
        if bar < 18:
            notes += [(q + i, "gram", _AFTER[_CHORD_OF(q + i)][i - 1], 0.5) for i in (1, 2)]
    out = [(GRAM_LEAD + q * GRAM_BEAT, event, _pitch(event, note), volume) for q, event, note, volume in notes]
    out += [(t, "needle", 1.0, 1.0) for t in range(0, GRAM_LOOP, NEEDLE_LOOP)]
    return sorted(out)


def gramophone(canvas, pos, reach=6.0, origin=(0, 0, 0), phase=0):
    """The gramophone plays at `pos`, its horn (scene coordinates, plus origin), to the players
    within `reach` blocks: its tune once a minute, the needle's crackle all the time. One line
    beside the line that turns the record. Returns 0: a sound is no entity."""
    voices = {}
    for tick, event, pitch, volume in tune():
        voices.setdefault((event, pitch, volume), []).append(tick)
    for (event, pitch, volume), ticks in sorted(voices.items()):
        MK.sound(canvas, pos, event, GRAM_LOOP, at=ticks, volume=volume, pitch=pitch, reach=reach,
                 origin=origin, phase=phase)
    return 0


# ---- the tower clock's bells ---------------------------------------------------------------------------
# The quarters are the Cambridge chimes (St Mary the Great, 1793; the Westminster quarters): five
# phrases of four notes on four bells, one phrase at the first quarter, two at the half, three at
# the third, four before the hour is struck. The bells are a major third, a tone and the keynote,
# and the fourth below it; the hour bell is the kind "strike". The game's bell is a little out of
# tune from stroke to stroke (its own table plays it 2 % up or down at random), as old bells are.
CHIME_BEAT = 20                 # ticks from note to note
CHIME_REST = 2                  # beats the last note of a phrase rings before the next phrase
STRIKE_BEAT = 60                # ticks from one stroke of the hour to the next
_BELLS = {"g": 2.0 ** (4 / 12.0), "f": 2.0 ** (2 / 12.0), "e": 1.0, "b": 2.0 ** (-5 / 12.0)}    # times the keynote's pitch
_PHRASES = ("gfeb", "egfb", "efge", "gefb", "bfge")
_QUARTERS = {1: (0,), 2: (1, 2), 3: (3, 4, 0), 4: (1, 2, 3, 4)}


def chime_ticks(quarter):
    """How long the chime of a quarter lasts, in ticks, its last note rung out: 100, 200, 300, 400."""
    return len(_QUARTERS[quarter]) * (4 + CHIME_REST - 1) * CHIME_BEAT


def chimes(canvas, pos, quarter, cycle, at=0, reach=None, origin=(0, 0, 0), phase=0, choice=0):
    """The tower clock chimes a quarter (1, 2, 3, or 4 for the full hour) from tick `at` of every
    `cycle` ticks, at `pos`, its bells. The hour itself is strikes(), from at + chime_ticks(4) on.
    reach: the players within so many blocks hear it; None is as far as the bells carry.
    Returns 0."""
    if quarter not in _QUARTERS:
        raise ValueError(f"motion/sound: a clock chimes the quarters 1 to 4, not {quarter}")
    reach = far("chime", choice) if reach is None else reach
    ticks = {}
    for n, phrase in enumerate(_QUARTERS[quarter]):
        for i, bell in enumerate(_PHRASES[phrase]):
            ticks.setdefault(bell, []).append(int(at) + (n * (4 + CHIME_REST - 1) + i) * CHIME_BEAT)
    for bell, when in sorted(ticks.items()):
        place(canvas, "chime", pos, reach, origin=origin, phase=phase, choice=choice, cycle=cycle, at=when,
              pitch=round(_BELLS[bell], 4))
    return 0


def strikes(canvas, pos, count, cycle, at=0, reach=None, origin=(0, 0, 0), phase=0, choice=0):
    """The hour bell strikes `count` times from tick `at` of every `cycle` ticks, at `pos`. Returns 0."""
    if int(count) < 1:
        raise ValueError("motion/sound: a clock strikes once or more")
    reach = far("strike", choice) if reach is None else reach
    return place(canvas, "strike", pos, reach, origin=origin, phase=phase, choice=choice, cycle=cycle,
                 at=[int(at) + i * STRIKE_BEAT for i in range(int(count))])


# ---- the spots of the master scene ---------------------------------------------------------------------
def _package(line, name):
    """A package of another line, or None while it is not in the tree."""
    try:
        return __import__(f"scenes.obs.{line}.{name}", fromlist=[name])
    except ImportError:
        return None


def _clocks(canvas, origin):
    """The master clock ticks at its pendulum's pivot, in step with the pendulum; so does every
    regulator clock that stands on the canvas (props/instruments tags its pendulum, which stands
    on the pivot). All the clocks of the house are driven by the master clock and beat together."""
    clock, kit = _package("machines", "clock"), _package("props", "_kit")
    if clock is not None and kit is not None:
        out = kit.turn(kit.FACING[clock.MASTER_FACING], tuple(v / 16.0 for v in clock.MASTER_PIVOT))
        place(canvas, "tick", tuple(clock.MASTER_AT[i] + out[i] for i in range(3)), REACH_STAR_HALL, origin)
    instruments = _package("props", "instruments")
    if instruments is not None:
        tag = instruments.PENDULUM["tag"]
        for x, y, z, nbt in list(canvas.entities):
            if tag in nbt.get("Tags", ()):
                place(canvas, "tick", (x, y, z), REACH_CLOCK)        # where it stands: the origin is in it


def _power_house(canvas, origin):
    """The engine's stroke at its cylinder and the dynamo's hum (machines/engine says where); the
    fire and the safety valve of boiler No. 2, the one that has just been fired (machines/boiler)."""
    engine = _package("machines", "engine")
    if engine is not None:
        place(canvas, "engine", engine.STROKE_AT, REACH_POWER_HOUSE, origin)
        place(canvas, "hum", engine.HUM_AT, REACH_POWER_HOUSE, origin)
    boiler = _package("machines", "boiler")
    if boiler is not None:
        place(canvas, "fire", boiler.FIRE_DOORS[-1], REACH_BOILERS, origin)
        place(canvas, "hiss", boiler.SAFETY_VALVES[-1], REACH_BOILERS, origin)


def _telegraph(canvas, origin):
    """The sounder taps where the time room keeps the telegraph's place, once machines/rec is in
    the tree to stand it there."""
    room = _package("interiors", "timeroom")
    if _package("machines", "rec") is None or room is None or "telegraph" not in getattr(room, "SLOTS", {}):
        return
    x, y, z = room.SLOTS["telegraph"]["pos"]
    place(canvas, "telegraph", (x, y + 0.5, z), REACH_TELEGRAPH, origin)


def _wind(canvas, origin):
    """The wind is heard at three open places (plan/parts/motion.md 8): the east edge of the court
    at the head of the grand stair, the lookout of the clock tower, the south lookout."""
    S = _package("common", "skeleton")
    place(canvas, "wind", (S.EAST_EDGE_X + 0.5, S.GROUND + 1.5, S.AXIS_Z), REACH_WIND, origin)
    x0, z0, x1, z1 = S.SOUTH_LOOKOUT["box"]
    place(canvas, "wind", ((x0 + x1 + 1) / 2.0, S.SOUTH_LOOKOUT["feet"] + 1.5, (z0 + z1 + 1) / 2.0), REACH_WIND, origin)
    tower = _package("main", "tower")
    if tower is not None:
        place(canvas, "wind", (tower.AXIS[0], tower.LOOKOUT[0] + 1.5, tower.AXIS[1]), REACH_TOWER, origin)


def build(canvas, origin=(0, 0, 0)):
    """Register every sound spot of the master scene. Returns 0 (no display entity is placed)."""
    _clocks(canvas, origin)
    _power_house(canvas, origin)
    _telegraph(canvas, origin)
    _wind(canvas, origin)
    return 0


def spots(canvas):
    """The spots our events are played at as they stand on the canvas, for the card's table and its
    budget: [(event, (x, y, z), cycle, the ticks of the cycle it sounds on, reach)]. Read off the
    book motion/_kit keeps on the canvas; nothing that builds or packs depends on this."""
    book = getattr(canvas, "motion", None)
    out = []
    for p in (book.points if book is not None else ()):
        if p.kind != "sound" or not p.what.startswith(NS + ":"):
            continue
        reach = re.search(r"distance=\.\.([0-9.]+)", p.text)
        out.append((p.what.split(":", 1)[1], tuple(p.pos), p.cycle, tuple(p.ticks),
                    float(reach.group(1)) if reach else None))
    return out
