"""Test scene of the work package motion/sound: a floor of small stands, one sound to a stand.

Nothing here is to be looked at: the scene is walked through on the real machine with the sound
on. Every stand plays one choice of one kind of sound, to whoever comes within REACH blocks of it;
the stands are STEP blocks apart, so between two of them nothing is heard, and that silence is
part of what is listened for (a sound stops at its reach).

    rows, from the north (z)     the kinds, in the order of ROWS: tick, engine, hum, fire, hiss,
                                 telegraph, wind; then the second round's (sound.KINDS, below
                                 the first round's): whistle, chuff, rail and bell of the train,
                                 strike and chime of the tower clock, clank, creak, thump, spark,
                                 drip, scratch, rumble, grind, water, bubble
    columns, from the west (x)   the choices: a, the table's (scenes/obs/motion/sound.EVENTS), on
                                 the stand one block high; b and c, the other two
                                 (sound.OTHERS), on the stands two and three blocks high. A
                                 kind without other choices has the one stand

The scene's pack has the map's sounds.json and the other choices beside them (sound.pack with
others=True); the map's own pack never has the others. Whoever has listened moves the choice he
likes into the table.

What to listen for at a stand: is it the thing (a clock, an engine, ...); is it too loud at the
stand; does it stop before the next stand; and for the ones that loop (hum, fire, wind): is the
seam heard, do two rounds pile up. The wind's choices a and b are in stereo: the game does not
place them in space, so they are as loud at the edge of the reach as at the stand, and a round
that has begun is heard to its end after one has walked away.

The second round's kinds sound here on the time KINDS gives them, which is only this scene's: in
the map the thing that moves says when (the train's exhaust beats with its wheels, the tower's bell
strikes the hour). The whistle blows long, then short, once in ten seconds; the exhaust beats four
times a second without an end, as it does on the climb; the station's bell is struck five times.
The tower's quarter bells play the chime of the half hour (two phrases of the Cambridge quarters),
its hour bell strikes three; both once in twenty seconds. What carries far in the map (the whistle
64 blocks, the tower's bells the whole hilltop) is cut off at the stand's reach here like
everything else. The last stand, south of the last row, is the gramophone: its tune once a
minute (sound.gramophone), the needle's crackle between.

The shot is written from the numbers below:  python -m scenes.obs_mot_sound
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.motion import _kit as MK
from scenes.obs.motion import sound

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32

STONE, PAVING = B.ASHLAR_FINE.block, B.TUFF_SMOOTH.block
ROWS = tuple(sound.KINDS)       # tick, engine, hum, fire, hiss, telegraph, wind, and the second round's
STEP = 14                       # blocks from stand to stand
REACH = 6.0                     # how far a stand is heard: two reaches are less than a step
EDGE = 8                        # the first stand's cell, from the floor's corner
LAMP_LEVEL = 12                 # the invisible light over each stand
BELLS = 400                     # ticks from one playing of the tower's bells to the next
TIME = 14000                    # light version A, the default


def light(level):
    return f"{B.LIGHT}[level={level}]"


def stand(row, column):
    """(x, z) of the cell of the stand for the kind ROWS[row] and the choice `column`."""
    return EDGE + STEP * column, EDGE + STEP * row


def size():
    """(x, z) of the floor's far corner: a row to a kind, and the gramophone's."""
    return 2 * EDGE + STEP * (len(sound.LETTERS) - 1), 2 * EDGE + STEP * len(ROWS)


def play(c, kind, pos, column):
    """What a stand plays: the kind on the time the table gives it; the tower's bells what they
    play in the map, the chime of the half hour and three strokes of the hour, once in BELLS ticks."""
    if kind == "chime":
        return sound.chimes(c, pos, 2, BELLS, reach=REACH, choice=column)
    if kind == "strike":
        return sound.strikes(c, pos, 3, BELLS, reach=REACH, choice=column)
    return sound.place(c, kind, pos, REACH, choice=column)


def build():
    c = Canvas()
    far_x, far_z = size()
    c.box(0, -1, 0, far_x, -1, far_z, PAVING)
    for row, kind in enumerate(ROWS):
        for column in range(len(sound.choices(kind))):
            x, z = stand(row, column)
            c.box(x, 0, z, x, column, z, STONE)
            c.set(x, column + 2, z, light(LAMP_LEVEL), keep=True)
            play(c, kind, (x + 0.5, column + 1.5, z + 0.5), column)
    x, z = stand(len(ROWS), 0)                      # the last stand: the gramophone
    c.box(x, 0, z, x, 0, z, STONE)
    c.set(x, 2, z, light(LAMP_LEVEL), keep=True)
    sound.gramophone(c, (x + 0.5, 1.5, z + 0.5), REACH)
    c.entity_counts = {"motion": 0}
    return c


def write_pack(pack_dir):
    """The stone of the stands, the map's sky (the scene stands in the map's hour), and the
    sounds: the table's and the other choices."""
    return (list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
            + list(sound.pack(pack_dir, others=True) or []))


def shots():
    """One camera: the floor from above its north-west corner. It looks at the first round's
    stands, as it did before the second round's rows were laid south of them: nothing here is
    judged by a picture."""
    far_x, _ = size()
    first_z = 2 * EDGE + STEP * (len(sound.FIRST_ROUND) - 1)
    return [{"name": "floor", "pos": [-12.0, 30.0, -16.0], "look_at": [far_x / 2.0, 0.0, first_z * 0.45], "time": TIME}]


assert 2 * REACH < STEP and MK.NS == sound.NS and ROWS[:len(sound.FIRST_ROUND)] == sound.FIRST_ROUND
