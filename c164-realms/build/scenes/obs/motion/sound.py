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

What is heard where (build()):
    tick        the master clock in the star hall, and every regulator clock that stands on the canvas
    engine      the steam engine's cylinder, once a turn of the flywheel
    hum         the dynamo
    fire        the fire door of the boiler that has just been fired
    hiss        that boiler's safety valve: VALVE says when it blows, for the steam of motion/smoke
    telegraph   the sounder in the time room, once machines/rec has put it there
    wind        the head of the grand stair, the lookout of the clock tower, the south lookout

A spot is registered only when the package that owns the thing is in the tree; its position is
read from that package's own numbers. There is no striking of the hour: the clocks stand at 7:55
(the director, group message 36340).

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
}

# ---- how far (see the head of the file) ---------------------------------------------------------------
# The volume a kind is played with when its sound has to carry further than the game's own does:
# the piston's 8 blocks and the beacon's 7 become 16, across the power house from the far corner.
CARRY = {"engine": 2.0, "hum": 2.3}
SOURCE = {"wind": "ambient"}    # the player's volume slider a kind is under; the others are "block"

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


def place(canvas, kind, pos, reach, origin=(0, 0, 0), phase=0, choice=0):
    """One spot of a kind of sound ("tick", ...) at pos (scene coordinates, plus origin), heard by
    the players within `reach` blocks. choice 1 or 2 plays one of the OTHERS (the test scene).
    Returns 0: a sound is no entity."""
    sets = choices(kind)
    if not 0 <= choice < len(sets):
        raise ValueError(f"motion/sound: {kind} has the choices 0 .. {len(sets) - 1}, not {choice}")
    held, carry = sets[choice]
    for event, cycle, at in KINDS[kind]:
        if event in held:
            MK.sound(canvas, pos, _named(event, choice), cycle, at=at, volume=carry, reach=reach,
                     source=SOURCE.get(kind, "block"), origin=origin, phase=phase)
    return 0


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
