"""Test scene of the work package motion/guide, part C: the close, in the dome room.

The dome room in a box, as the test scene of interiors/domeroom builds it: the drum and the dome
with its slit, the floor, the great refractor on its pier, the dome's gear, the sky with the comet
in the slit. In it the guide's close with the map's own places and nothing made up: guide.slit(),
scope.OBSERVER, guide.tube(scope), scope.EYE_TAG once machines/scope has one. The charts are the
map's too (motion/_guide_charts); their places lie outside this box, so nobody takes one here.

One thing in this scene is not the map's: the replay. Every REPLAY ticks a command of the scene's
own gives every player the ten seconds of light again (it sets the score the lights count down),
so that a camera which takes a picture every two seconds finds the shaft and the stream at every
stage, and somebody who walks about the room can watch them from wherever he likes. The map has
no such command: there the lights are for the player who has all six charts, once.

Particles are not drawn offline: the offline pictures show the room as it stands.

The cameras (a standing eye on the room's floor)
    back     four blocks behind the observer's spot, in the tube's plane, the eyes up the slit:
             where somebody stands who has stepped back from the eyepiece. The comet is in the
             slit south of its middle, the shaft north of it; the stream comes down the tube's
             lower flank on the left
    step     a block behind the spot, the eyes up the tube's underside: the stream runs towards
             the eye and turns up into the eyepiece's mouth
    side     from the south-east of the room: the tube's south flank with the stream along it,
             the slit beyond
    v8       the skeleton's locked view of the room

    python -m scenes.obs_mot_guide_dome      (in build/) writes shots.json
"""
from scenes import obs_int_domeroom as room
from scenes.obs.common import skeleton as S
from scenes.obs.machines import scope
from scenes.obs.motion import _kit as MK
from scenes.obs.motion import guide

BIOME = room.BIOME
BIOME_MARGIN = room.BIOME_MARGIN
BIOME_MARGIN_Y = room.BIOME_MARGIN_Y
TIME = 14000                    # light version A, the default
REPLAY = 320                    # ticks from one replay of the lights to the next: ten seconds of them, three of
#                                 the last motes going out, three of the dark room

OBSERVER = scope.OBSERVER[scope.VERSION]


def _charts():
    """The map's charts and the spots one reads them from; six spots under the box while
    motion/_guide_charts is not in the tree."""
    module = guide._package("motion", "_guide_charts")
    if module is not None:
        return module.CHARTS, getattr(module, "STAND", None)
    under = float(S.DRUM_BASE - 8)
    return tuple((f"post{k + 1}", (4.0 * k - 10.0, under + 1.0, 0.5), under) for k in range(6)), None


def shots():
    eye = S.ROOF_STAND + S.EYE
    ox, _oy, oz = OBSERVER
    start, rim, _mouth = guide.tube(scope)
    half = [round((a + b) / 2.0, 2) for a, b in zip(start, rim)]
    views = [
        ("back", (ox + 4.0, eye, oz), (-4.0, 33.0, 0.5)),
        ("step", (ox + 1.2, eye, oz), half),
        ("side", (10.0, eye, 6.0), (3.0, 25.5, 1.5)),
        ("v8", S.V8["pos"], S.V8["look_at"]),
    ]
    return [dict(name=name, pos=[round(v, 2) for v in pos], look_at=[round(v, 2) for v in at], time=TIME)
            for name, pos, at in views]


def build():
    c = room.build()
    charts, stands = _charts()
    guide.quest(c, charts, OBSERVER, guide.slit(), (0, 0, 0), stands=stands, tube=guide.tube(scope),
                eye=getattr(scope, "EYE_TAG", None))
    # the replay: this scene's own, not the map's
    MK.run(c, None, f"scoreboard objectives add {guide.GLOW} dummy", REPLAY, at=(0,))
    MK.run(c, None, f"scoreboard players set @a {guide.GLOW} {guide.LIGHT_BEATS}", REPLAY, at=(1,))
    return c


build_models = room.build_models
write_pack = room.write_pack
