"""Test scene of the work package common/export (plan/packages/common/export.md): the trial saves.

A world with our look in it is marked as using experimental settings, and Realms says it does not
take such worlds (plan/reviews/export/realms-rules.md). Before the whole map is exported the admin
uploads two small saves made from this scene with tools/export.py, and what he sees answers three
things: does the upload go through, is the sky ours, are the repainted blocks and the models there.

The scene is a 9 x 9 platform and everything is in the first view of who arrives. He stands at the
east edge and looks west and up: two iron pillars with a dial on each, between them a pole with the
weather station's vane and cup wheel on it (site/outbuildings' two models, the cups turning), and
over the pole the comet. Every block of it is a repainted one, so a client without the pack shows
green copper, yellow sandstone, a white-and-blue tile where the dials are and a black-and-purple
cube on the pole.

    T1, with the look:      this scene, at tick 14000 (look A): the timeline holds the comet due west.
    T2, without the look:   the same blocks under the vanilla sky. The game's own moon stands where
                            our look keeps it (48 degrees up, due west) at tick 20370, and it wears
                            the comet's picture from the pack; scenes/obs_export_probe_plain is that
                            scene, for its pictures.

SPAWN is where the export puts the world's spawn (tools/export.py reads it, as it reads the
skeleton's V1 for the whole map): the eye and what it looks at, in scene coordinates.

shots.json is written from shots():  python -m scenes.obs_export_probe  (in build/).
"""
import math

from artkit import models as M
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.motion import _kit as MK
from scenes.obs.site import outbuildings

BIOME = "obs_blue"
BIOME_MARGIN = 48               # the look is sampled where the viewer stands: the platform and some air
BIOME_MARGIN_Y = 64
TIME = 14000                    # light version A
TIME_PLAIN = 20370              # the vanilla sky with its moon where the look's moon_angle (42) keeps ours

HALF = 4                        # the platform: x and z from -4 to 4, its floor blocks at y 0
FEET = 1.0                      # where feet stand on it
PILLAR_Z = (-3, 3)              # the two pillars, on the west edge
PILLAR_TOP = 5
DIAL_Y = 3
POLE = (-HALF, 0)               # the pole between them, (x, z)
POLE_RODS = 3
LIGHTS = ((-3, 3, -3), (-3, 3, 3), (-3, 4, 0), (0, 3, 0), (3, 3, 0))   # invisible lamps: it is night

YAW, PITCH = 90.0, -25.0        # west, and up far enough to hold the comet (37 to 59 degrees up)
_EYE = (HALF - 0.5, FEET + S.EYE, 0.5)
_AIM = (-math.sin(math.radians(YAW)) * math.cos(math.radians(PITCH)), -math.sin(math.radians(PITCH)),
        math.cos(math.radians(YAW)) * math.cos(math.radians(PITCH)))
SPAWN = dict(pos=_EYE, look_at=tuple(round(e + 16.0 * a, 4) for e, a in zip(_EYE, _AIM)))

_HEAD = (POLE[0] + 0.5, FEET + POLE_RODS, POLE[1] + 0.5)        # the top of the pole


def build():
    c = Canvas()
    for x in range(-HALF, HALF + 1):
        for z in range(-HALF, HALF + 1):
            rim = max(abs(x), abs(z)) == HALF
            line = z == 0 and not rim
            c.set(x, 0, z, B.IRON_RIVETED.block if rim else B.BRASS_PLATE.block if line else B.ASHLAR_FINE.block)
    for z in PILLAR_Z:
        for y in range(1, PILLAR_TOP + 1):
            c.set(-HALF, y, z, B.PANELS["dial"] + "[facing=east]" if y == DIAL_Y else B.IRON_RIVETED.block)
        c.set(-HALF, PILLAR_TOP + 1, z, B.ASHLAR_FINE.slab + "[type=bottom]")
    for y in range(1, POLE_RODS + 1):
        c.set(POLE[0], y, POLE[1], B.IRON_ROD + "[facing=up]")
    for x, y, z in LIGHTS:
        c.set(x, y, z, B.LIGHT + "[level=15]")

    kit = outbuildings.models()
    c.add_entity(*_HEAD, M.display(kit[outbuildings.MODEL_HEAD]))
    c.add_entity(_HEAD[0] - outbuildings.CUPS_ARM / 16.0, _HEAD[1] + outbuildings.CUPS_UP / 16.0, _HEAD[2],
                 M.display(kit[outbuildings.MODEL_CUPS]))
    MK.spin(c, "y", MK.ANEMOMETER_REV)                  # the cups go round: the loop runs in the save
    return c


def build_models():
    kit = outbuildings.models()
    return {name: kit[name] for name in (outbuildings.MODEL_HEAD, outbuildings.MODEL_CUPS)}


def write_pack(pack_dir):
    """The repainted blocks and the comet's pictures (with the blanked sun), as the map carries them."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots(time=TIME):
    """arrive: what who joins sees before he moves (the spawn's eye and aim). floor: the same eye
    looking down along the brass line. back: from behind the pole, back at the spawn."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [float(round(v, 2)) for v in pos],
                    "look_at": [float(round(v, 2)) for v in look_at], "time": time})

    shot("arrive", SPAWN["pos"], SPAWN["look_at"])
    shot("floor", SPAWN["pos"], (-HALF + 0.5, 1.2, 0.5))
    shot("back", (-HALF - 5.5, FEET + 4.0, 3.5), (HALF - 0.5, FEET + 1.0, 0.5))
    return out
