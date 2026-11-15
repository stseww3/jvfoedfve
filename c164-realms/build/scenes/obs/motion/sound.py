"""motion/sound -- where the observatory's sounds sit, and the table that gives them their voices.

Card plan/packages/motion/sound.md; detail plan/parts/motion.md 4 and 9; ART-PLAN 9.

NO SOUND FILES ARE ADDED (card, and the plan's red line 6: no third-party assets; the checker bans
binaries anyway). Our events are written into `assets/c164/sounds.json` and each one POINTS AT A
SOUND THE GAME ALREADY HAS (`{"name": ..., "type": "event"}`), with its volume and pitch in the
command. That is the director's ruling (A0 #505.2), and it is what materials/brass-oldcopper-small
already does for the brass footfalls.

The seven events and what they stand for:

  c164:tick        the master clock's pendulum escaping        -> block.copper.step    (a small tap)
  c164:engine      the steam engine under load                 -> block.copper.break   (low, slow)
  c164:hum         the dynamo turning                          -> block.beacon.ambient  (a held hum)
  c164:fire        the boiler's draught                        -> block.fire.ambient    (a low roar)
  c164:hiss        the safety valve lifting                    -> block.fire.extinguish (a short hiss)
  c164:telegraph   the sounder clacking                        -> block.note_block.hat  (a dry knock)
  c164:wind        the wind over the mountain                  -> ambient.cave          (a wide, low bed)

WHY EACH ONE. Nothing here is a new sound: every target is a vanilla event, so the game plays its own
audio. Where a family had no good fit the choice is written beside it in VOICES rather than left
implicit -- the card wants two or three candidates per sound heard before one is picked, so VOICES
lists the alternates too and `pick()` switches between them by name.

REACH: a room's sound must not leave the room, so the indoor events are given the room's own size as
their reach (the time room is 12 x 19, the power house 23 x 23; a reach of 14-16 keeps them inside),
and the wind, which belongs to the whole mountain, is capped at the card's 24 blocks.

LOOPS. The wind and the dynamo's hum are loops: they are re-sent on a period rather than played once,
and the period is picked so the tail of one overlaps the head of the next and the join cannot be
heard (the card's "the join of a loop must not be audible"). `_KIT.sound` takes the period and the
ticks of the cycle, and `motion/loop` writes the function files.

WHAT IS NOT DONE: the hour bell (the map's clocks stop at 7:55, A0 #505.1), and any sound that would
need a new audio file.

    from scenes.obs.motion import sound
    n = sound.build(canvas, origin)     # register the points; 0 entities, 0 blocks
    sound.pack(pack_dir)                # write assets/c164/sounds.json
"""
import json
import os

from scenes.obs.motion import _kit as MK

NAME = "motion/sound"
NS = "c164"

# --- the events, each with the vanilla sounds it may be voiced with -----------------------------
# (event: [(vanilla event, volume, pitch), ...]); the first entry is the default voice.
VOICES = {
    "tick": [("block.copper.step", 0.45, 1.85),          # a small brass tap, quick and high
             ("block.copper_trapdoor.toggle", 0.30, 2.00),
             ("block.metal.step", 0.35, 1.95)],
    "engine": [("block.copper.break", 0.55, 0.62),        # heavy, slow, low
               ("block.copper.step", 0.60, 0.55),
               ("block.metal.break", 0.45, 0.60)],
    "hum": [("block.beacon.ambient", 0.32, 0.70),         # a held tone that sits under everything
            ("block.conduit.ambient", 0.28, 0.62),
            ("ambient.cave", 0.22, 0.85)],
    "fire": [("block.fire.ambient", 0.55, 0.90),          # a low roar, never a crackle
             ("block.fire.crackle", 0.35, 0.75),
             ("block.lava.ambient", 0.40, 0.80)],
    "hiss": [("block.fire.extinguish", 0.55, 1.05),       # a short breath of steam
             ("block.lava.extinguish", 0.50, 1.10),
             ("block.powder_snow.break", 0.45, 1.00)],
    "telegraph": [("block.note_block.hat", 0.35, 1.60),   # a dry click of the armature
                  ("block.stone_button.click_on", 0.30, 1.50),
                  ("block.copper_bulb.turn_on", 0.30, 1.80)],
    "wind": [("ambient.cave", 0.22, 0.55),                # a wide low bed, not a whistle
             ("ambient.basalt_deltas.loop", 0.25, 0.60),
             ("weather.rain.above", 0.15, 0.50)],
}

DEFAULT_VOICE = {event: voices[0] for event, voices in VOICES.items()}

# --- the periods, in ticks -----------------------------------------------------------------------
# the pendulum escapes twice a second (a 2-tick swing is the clock's own beat: see machines/clocks)
PENDULUM = 20                      # one beat of the master clock
ENGINE_STROKE = 24                 # one revolution of the flywheel, slow
HUM_LOOP = 100                     # the dynamo's held tone, re-sent before its tail dies
FIRE_LOOP = 160
WIND_LOOP = 240


def voices(choice=None):
    """The voice table actually written: {event: (vanilla event, volume, pitch)}. `choice` overrides
    single events by name, e.g. {"wind": 1} for the second candidate."""
    choice = choice or {}
    out = {}
    for event, cands in VOICES.items():
        i = int(choice.get(event, 0))
        if not 0 <= i < len(cands):
            raise ValueError(f"{event}: candidate {i} does not exist")
        out[event] = cands[i]
    return out


def table(choice=None):
    """The resource pack's sounds.json: {event: [{"name": vanilla, "type": "event"}]}."""
    return {event: [{"name": name, "type": "event"}] for event, (name, _v, _p) in voices(choice).items()}


def pack(pack_dir, choice=None):
    """Write assets/c164/sounds.json. Returns the one line the log shows."""
    path = os.path.join(pack_dir, "assets", NS, "sounds.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {}
    if os.path.isfile(path):
        with open(path) as fh:
            data = json.load(fh)
    data.update(table(choice))
    with open(path, "w") as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
    return [f"sounds.json: {len(table(choice))} events of ours point at the game's own sounds"]


# --- where the sounds sit ------------------------------------------------------------------------
def _point(canvas, pos, event, cycle, at, origin, choice, reach, scale=1.0):
    """One sound point, voiced from the table. A missing source (its package not in the tree) is
    simply not registered -- the card's rule."""
    name, volume, pitch = voices(choice)[event]
    try:
        MK.sound(canvas, pos, event, cycle, at=at, volume=volume * scale, pitch=pitch,
                 reach=reach, origin=origin)
    except (ValueError, TypeError):
        return 0
    return 0


def _sources():
    """The points, read from the packages that own them: {name: (pos, ...)}. A package that is not in
    the tree contributes nothing, which is what the card asks for."""
    out = {}
    try:
        from scenes.obs.machines import clock as CL
        mc = CL.S.MOTHER_CLOCK
        out["master clock"] = (mc["back_x"] + 0.5, CL.S.GROUND + 3.4, mc["z"])
    except Exception:
        pass
    try:
        from scenes.obs.machines import engine_dynamo as ED
        out["engine"] = (ED.CX + ED.CYL_X, ED.FEET + 1.2, ED.CZ)
        out["dynamo"] = (ED.CX + ED.DYNAMO_X, ED.FEET + 1.4, ED.CZ)
    except Exception:
        pass
    try:
        from scenes.obs.machines import switchboard_boiler as SB
        out["boiler"] = (SB.BOILER_C[0], SB.FEET + 1.2, SB.BOILER_C[2])
        out["safety valve"] = (SB.BOILER_C[0], SB.FEET + 2.2, SB.BOILER_C[2] - 1.4)
    except Exception:
        pass
    try:
        from scenes.obs.machines import recorders as RC
        slot = RC.DEFAULT_SLOTS["telegraph"]
        out["telegraph"] = (slot["pos"][0], slot["pos"][1] + 0.5, slot["pos"][2])
    except Exception:
        pass
    return out


def build(canvas, origin=(0, 0, 0), choice=None):
    """Register the sound points of every package in the tree. 0 display entities, 0 blocks -- sounds
    are commands, not things (the card's budget line). Returns 0."""
    where = _sources()
    if "master clock" in where:                        # the pendulum's tick, once a beat
        _point(canvas, where["master clock"], "tick", PENDULUM, (0, 10), origin, choice,
               reach=12.0)
    if "engine" in where:                              # the stroke, once a revolution
        _point(canvas, where["engine"], "engine", ENGINE_STROKE, (0,), origin, choice, reach=16.0)
    if "dynamo" in where:                              # the held hum, re-sent on a loop
        _point(canvas, where["dynamo"], "hum", HUM_LOOP, (0,), origin, choice, reach=16.0)
    if "boiler" in where:                              # the draught, a slow low loop
        _point(canvas, where["boiler"], "fire", FIRE_LOOP, (0,), origin, choice, reach=16.0)
    if "safety valve" in where:                        # the valve lifts now and then
        _point(canvas, where["safety valve"], "hiss", FIRE_LOOP, (FIRE_LOOP - 24,), origin, choice,
               reach=14.0)
    if "telegraph" in where:                           # a burst of clicks, then a rest
        _point(canvas, where["telegraph"], "telegraph", 40, (2, 6, 9, 14, 20), origin, choice,
               reach=12.0)
    _point(canvas, (0.0, 0.0, 0.0), "wind", WIND_LOOP, (0,), origin, choice, reach=24.0)
    return 0
