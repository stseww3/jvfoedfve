"""Third test scene of the work package motion/smoke: the bench.

The room of obs_mot_smoke_room, machine for machine, with the sparks, the flashes and the leak
coming every few ticks. A flash at a brush lives a tenth of a second and the room has six in
eight seconds: nine pictures in ten of the real machine have none, and nobody can say from them
where a flash sits, how big it is and whether it jumps out of the dark room as a white dot. Here
a picture has them.

The particles, the spots, the ways and the speeds are the room's: smoke.sparks(), smoke.flashes()
and smoke.leak() are called as smoke.build() calls them and are told nothing but when. HOW MANY
there are in a picture of this scene is not what the room has; for that, obs_mot_smoke_room.

    sparks   one every SPARK_STEP ticks, the room's first five in turn: three or four in the air
             at a time (the room: one, now and then)
    flashes  at each brush and at the open switch one every FLASH_CYCLE ticks, the two brushes
             in turn. A flash is out before the next at its spot is lit, so no spot has more of
             them than in the room: two sparks. Of the two brushes one is always alight; the
             switch is dark for a tick or two in four
    leak     a wisp a second: one or two in the air (the room: one in eight seconds)

The chimney and the safety valve are left out: obs_mot_smoke and obs_mot_smoke_room show them as
they are.

The cameras are the room's four that look at these spots. The brushes and the switch are in the
list twice, the second time as <name>_again. The game must not be frozen while the pictures are
taken.

    python -m scenes.obs_mot_smoke_bench      (in build/) writes shots.json
"""
from scenes import obs_mot_smoke_room as room
from scenes.obs import sky
from scenes.obs.motion import smoke

BIOME = room.BIOME
BIOME_MARGIN = room.BIOME_MARGIN
BIOME_MARGIN_Y = room.BIOME_MARGIN_Y
TIME = room.TIME

VIEWS = ("fire", "flange", "brushes", "switch")
TWICE = ("brushes", "switch")

SPARK_STEP = 8          # ticks from one spark to the next
SPARKS = 5              # ... and how many of the room's take their turn
FLASH_CYCLE = 4         # ticks from one flash at a spot to the next
LEAK_CYCLE = 20         # ticks from one wisp to the next


def shots():
    views = {name: (pos, look_at) for name, pos, look_at in room._views()}
    out = []
    for again in ("", "_again"):
        for name in (VIEWS if not again else TWICE):
            pos, look_at = views[name]
            out.append({"name": name + again, "pos": [round(float(v), 2) for v in pos],
                        "look_at": [round(float(v), 2) for v in look_at], "time": TIME})
    return out


def build():
    c = room.stage()
    smoke.sparks(c, (0, 0, 0), cycle=SPARK_STEP * SPARKS,
                 table=[(k * SPARK_STEP, out, speed) for k, (_, out, speed) in enumerate(smoke.SPARKS[:SPARKS])])
    half = FLASH_CYCLE // 2
    smoke.flashes(c, (0, 0, 0), cycle=FLASH_CYCLE, brush=((0, 1), (half, -1)), switch=(0,))
    smoke.leak(c, (0, 0, 0), cycle=LEAK_CYCLE, wisps=[(0,) + tuple(wisp[1:]) for wisp in smoke.LEAK[:1]])
    sky.build(c, (0, 0, 0))                         # the sky line's light sources go in last
    return c


build_models = room.build_models
write_pack = room.write_pack
