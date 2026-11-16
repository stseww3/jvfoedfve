"""motion/sound.py -- the sounds of the place: the table of our sound events and the spots they are heard at.

Card plan/packages/motion/sound.md; detail plan/parts/motion.md section 8; ART-PLAN 9 and 12.6.

No sound is added to the game. The resource pack gets one file, assets/c164/sounds.json, in which
every event of ours points at a sound event the game ships (a sound of "type": "event") and says
how loud and how high it is played: the table EVENTS below. A sound is tuned there, in one place,
and the data pack never changes with it. An event of ours has no subtitle.

The data pack plays our events at fixed spots, to the players near enough to hear them, through
the motion loop: every spot is one line  MK.sound(canvas, pos, event, cycle, at=..., reach=...)
and motion/_kit writes the functions. A sound that goes with a moving part has the part's period,
so the two are on one chain and stay in step: the master clock ticks as its pendulum passes the
plumb line.

    from scenes.obs.motion import sound
    sound.place(canvas, "tick", pos, reach=10.0)     # one spot of a kind, for whoever places a clock
    sound.build(canvas, origin)                       # every spot of the master scene
    sound.pack(pack_dir)                              # assets/c164/sounds.json

A spot is registered only when the package that owns the thing is in the tree; its position is
read from that package's own numbers. There is no striking of the hour: the clocks stand at 7:55
(the director, group message 36340).

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
# Volume and pitch multiply what the game's own event has. A playsound of volume 1 or less is
# heard for 16 blocks and fades evenly over them, so the volume here is the loudness at the spot.
# First guesses, to be set by ear on the real machine (card: "listened to, then settled").
EVENTS = {
    "tick": ("block.note_block.hat", 0.30, 1.20),           # the pendulum passes the plumb line going one way
    "tock": ("block.note_block.hat", 0.30, 1.00),           # ... and coming back: the same click, a tone lower
    "engine": ("block.piston.extend", 0.35, 0.60),          # the steam engine's stroke, once a turn of the flywheel
    "hum": ("block.beacon.ambient", 0.50, 0.625),           # the dynamo and the switchboard
    "fire": ("block.blastfurnace.fire_crackle", 0.60, 1.00),    # the boiler's fire door
    "hiss": ("block.fire.extinguish", 0.35, 0.70),          # the safety valve, with its puff of steam
    "telegraph": ("block.stone_button.click_on", 0.40, 1.30),   # the sounder in the time room
    "wind": ("item.elytra.flying", 0.12, 0.80),             # the wind over the hill's open edges
}

# ---- how a kind of sound is played: (event, cycle, the ticks of the cycle it sounds on) ------------
# A kind is one or more events on one cycle. The tick goes with the pendulums: PENDULUM ticks are
# one swing there and back, the pendulum hangs plumb at 0 and at half of it (plan/parts/motion.md 4:
# a second clock's pendulum may start half a cycle off; it passes the plumb line on the same ticks).
KINDS = {
    "tick": (("tick", MK.PENDULUM, (0,)), ("tock", MK.PENDULUM, (MK.PENDULUM // 2,))),
}

# ---- where: the reach of a room -------------------------------------------------------------------
# Only players within the reach are sent a sound (blocks from the spot), which is what keeps a
# room's sound in the room.
REACH_STAR_HALL = 10.0          # the master clock stands at the pier; the hall's side walls are 6.5 away


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


def table(events=None):
    """What goes into assets/c164/sounds.json: {our event: {"sounds": [one sound of type "event"]}}."""
    out = {}
    for name, (target, volume, pitch) in sorted((events or EVENTS).items()):
        out[name] = {"sounds": [{"name": f"{GAME}:{target}", "type": "event",
                                 "volume": float(volume), "pitch": float(pitch)}]}
    return out


def pack(pack_dir, events=None):
    """Write assets/c164/sounds.json: our events, each pointing at one of the game's. No audio file."""
    events = dict(events or EVENTS)
    known = _events_of_the_game()
    if known is not None:
        missing = sorted({target for target, _v, _p in events.values() if target not in known})
        if missing:
            raise ValueError(f"motion/sound: the game (26.3) has no sound event {', '.join(missing)}")
    path = os.path.join(pack_dir, "assets", NS, "sounds.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(table(events), fh, indent=1, sort_keys=True)
        fh.write("\n")
    checked = "each checked against the game's own" if known is not None else "not checked: no client jar here"
    return [f"motion/sound: assets/{NS}/sounds.json, {len(events)} events pointing at the game's sounds ({checked})"]


def place(canvas, kind, pos, reach, origin=(0, 0, 0), phase=0, source="block"):
    """One spot of a kind of sound ("tick", ...) at pos (scene coordinates, plus origin), heard by
    the players within `reach` blocks. Returns 0: a sound is no entity."""
    if kind not in KINDS:
        raise ValueError(f"motion/sound: no kind of sound {kind!r}; there are {', '.join(sorted(KINDS))}")
    for event, cycle, at in KINDS[kind]:
        MK.sound(canvas, pos, event, cycle, at=at, reach=reach, source=source, origin=origin, phase=phase)
    return 0


def _master_clock(canvas, origin):
    """The master clock in the star hall ticks at its pendulum's pivot, in step with the pendulum."""
    try:
        from ..machines import clock
        from ..props import _kit as K
    except ImportError:
        return
    out = K.turn(K.FACING[clock.MASTER_FACING], tuple(v / 16.0 for v in clock.MASTER_PIVOT))
    pivot = tuple(clock.MASTER_AT[i] + out[i] for i in range(3))
    place(canvas, "tick", pivot, REACH_STAR_HALL, origin)


def build(canvas, origin=(0, 0, 0)):
    """Register every sound spot of the master scene. Returns 0 (no display entity is placed)."""
    _master_clock(canvas, origin)
    return 0
