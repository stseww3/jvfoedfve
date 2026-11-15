"""The small instruments (plan ART-PLAN 7.3; parts/A6-props.md 2.5; card packages/props/instruments.md).

One vocabulary for every piece: a graduated brass ring or arc, a knurled knob, a steady foot of dark
wood or cast iron. Nothing glows except a dial.

    tripod_scope       a brass telescope on a wooden tripod, two blocks tall; it looks along `facing`
    celestial_globe    a celestial globe a block and a half across in a floor stand

For the other lines:

    from scenes.obs.props import instruments
    n += instruments.place(canvas, "tripod_scope", (x, y, z), facing="west", origin=origin)   # foot centre

place() returns the number of display entities it placed. build() puts nothing into the master
scene: the terraces and the rooms place their own instruments.
"""
import functools
import math

import numpy as np

from artkit import models as M
from artkit import pixelart

from ..common import palette as P
from . import _kit as K

PREFIX = "prop_inst_"

IRON, IRON_D, BRASS, BRASS_D = K.IRON, K.IRON_D, K.BRASS, K.BRASS_D
WOOD = P.mat("dark_wood")
LENS = K.flat("night_glass", 2)         # the glass of an objective: dark, it holds the sky and does not glow
EYECUP = K.flat("iron", 1)
KNOB = K.flat("brass", 4)               # the bright end of a knurled knob


class _Stars(pixelart.Mat):
    """The painted sky of a celestial globe: enamel blue with single-pixel stars of the cream ramp,
    one pixel in `rare`, a fifth of them the brightest cream."""
    rare = 16

    def paint(self, w, h, grain="u", seed=0):
        out = super().paint(w, h, grain, seed)
        jj, ii = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        r = pixelart._hash(ii * 3 + 1, jj * 5 + 2, seed * 13 + 7)
        out[r < 1.0 / self.rare, :3] = P.colour("cream", 1)
        out[r < 0.2 / self.rare, :3] = P.colour("cream", 3)
        return out


SKY = _Stars("enamel_stars", P.RAMPS["enamel"], kind="plain", noise=0.0, bevel=0, base=1)


# ---- the models --------------------------------------------------------------------------------------
SCOPE_TILT = 20.0       # degrees above the horizon
SCOPE_PIVOT = 27.5      # height of the altitude axis


def _tripod_scope():
    """A brass telescope on a wooden tripod, two blocks tall. It looks along +z and up by SCOPE_TILT;
    one leg stands forward and the observer steps between the other two. Anchor: the floor under the
    middle of the tripod."""
    m = M.Model(PREFIX + "tripod_scope")
    hub = 21.0
    for deg in (90.0, 210.0, 330.0):
        c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        with m.aimed((8.0 * c, 0.0, 8.0 * s), (1.5 * c, hub, 1.5 * s), "y") as length:
            m.tube("y", (0, 0), 0.0, 2.0, 0.5, IRON_D, sides=4)                 # shoe
            m.tube("y", (0, 0), 2.0, length, 0.75, WOOD, sides=4)               # leg
            m.tube("y", (0, 0), 11.0, 12.5, 1.0, BRASS_D, sides=4)              # the clamp of the slide
    m.tube("y", (0, 0), hub - 1.5, hub + 0.5, 2.5, BRASS_D)                     # tripod head
    m.box((-3.0, hub + 0.5, -1.5), (3.0, hub + 1.5, 1.5), IRON)                 # yoke: foot and cheeks
    for x in (-3.0, 2.0):
        m.box((x, hub + 1.5, -1.0), (x + 1.0, SCOPE_PIVOT + 1.0, 1.0), IRON, grain="y")
    m.tube("x", (SCOPE_PIVOT, 0), 3.0, 4.5, 1.25, BRASS_D, cap=KNOB)                 # clamp knob
    with m.turned(("x", -SCOPE_TILT), about=(0, SCOPE_PIVOT, 0)):
        c = (0, SCOPE_PIVOT)
        m.ring("x", (0, SCOPE_PIVOT, 0), 4.5, 1.0, 1.0, BRASS, sides=16, arc=(100, 260))   # altitude arc
        m.tube("z", c, -8.0, 13.0, 1.5, BRASS, sides=12)                        # main tube
        m.tube("z", c, -1.5, 1.5, 2.0, BRASS_D, sides=12)                       # cradle band
        m.tube("z", c, 7.0, 8.0, 1.75, BRASS_D, sides=12)
        m.tube("z", c, 13.0, 16.0, 2.0, BRASS_D, sides=12, cap=LENS)            # objective cell
        m.tube("z", c, -13.0, -8.0, 1.0, BRASS_D)                               # draw tube
        m.tube("z", c, -15.0, -13.0, 1.25, BRASS, cap=EYECUP)                   # eyepiece
        m.tube("x", (SCOPE_PIVOT, -9.0), 1.0, 2.5, 0.75, BRASS_D, cap=KNOB)                # focus knob
        m.tube("z", (0, SCOPE_PIVOT + 2.75), 1.0, 9.0, 0.5, BRASS_D, sides=4, cap=LENS)     # finder
        for z in (2.0, 7.0):
            m.box((-0.5, SCOPE_PIVOT + 1.5, z), (0.5, SCOPE_PIVOT + 2.25, z + 1.0), IRON_D)
    return m


GLOBE_R = 10.0          # the sphere: 20 px across
GLOBE_Y = 19.0          # height of its centre and of the horizon ring
GLOBE_TILT = 38.0       # the polar axis leans this far from the vertical, towards +z


def _celestial_globe():
    """A celestial globe in a floor stand: four wooden legs carry a brass horizon ring, a brass
    meridian ring stands in it and holds the sphere by its poles. 26 px across the horizon ring,
    30 px tall. Anchor: the floor under its middle."""
    m = M.Model(PREFIX + "celestial_globe")
    for deg in (45.0, 135.0, 225.0, 315.0):
        c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        m.tube("y", (8.5 * c, 8.5 * s), 0.0, 1.0, 1.5, IRON_D)                  # foot pad
        m.rod((8.5 * c, 1.0, 8.5 * s), (11.5 * c, GLOBE_Y - 0.5, 11.5 * s), 1.0, WOOD)
    for deg in (45.0, 135.0):                                                   # stretchers
        c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        m.beam((-9.2 * c, 5.0, -9.2 * s), (9.2 * c, 5.0, 9.2 * s), 1.5, 1.5, WOOD)
    m.tube("y", (0, 0), 4.0, 7.0, 2.0, BRASS_D)                                 # boss under the meridian ring
    m.tube("y", (0, 0), 7.0, GLOBE_Y - GLOBE_R - 1.5, 0.75, BRASS)
    m.ring("y", (0, GLOBE_Y, 0), 12.0, 2.0, 1.0, BRASS, sides=24)               # horizon ring
    m.ring("x", (0, GLOBE_Y, 0), GLOBE_R + 1.0, 1.0, 1.0, BRASS_D, sides=24)    # meridian ring
    with m.turned(("x", GLOBE_TILT), about=(0, GLOBE_Y, 0)):
        m.ball((0, GLOBE_Y, 0), GLOBE_R, SKY, sides=12, layers=10, patchy=True)
        for y0, y1 in ((GLOBE_Y - GLOBE_R - 1.5, GLOBE_Y - GLOBE_R), (GLOBE_Y + GLOBE_R, GLOBE_Y + GLOBE_R + 1.5)):
            m.tube("y", (0, 0), y0, y1, 0.75, BRASS)                            # the pins at the poles
    return m


# name -> how it is mounted and its scale
SPEC = {
    "tripod_scope": dict(build=_tripod_scope, mount="floor"),
    "celestial_globe": dict(build=_celestial_globe, mount="floor"),
}
SCALE = {PREFIX + name: spec.get("scale", 1.0) for name, spec in SPEC.items()}


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + name: spec["build"]() for name, spec in SPEC.items()}


def models():
    return dict(_models())


# ---- placing -------------------------------------------------------------------------------------------
def place(canvas, kind, pos, facing="south", origin=(0, 0, 0), yaw=None, **opts):
    """Put one instrument into the scene; returns the number of display entities (1).

    kind     "tripod_scope", "celestial_globe".
    pos      scene coordinates: the centre of its foot on the floor (or on the table top).
    facing   the way it looks: the telescope's objective points there. yaw overrides it.
    opts     go to artkit.models.display (brightness, view).
    """
    spec = SPEC[kind]
    return K.put(canvas, _models()[PREFIX + kind], pos, mount=spec["mount"], facing=facing, yaw=yaw,
                 scale=spec.get("scale", 1.0), origin=origin, **opts)


def build(canvas, origin=(0, 0, 0)):
    """Nothing of its own in the master scene: the lines that build the terraces and the rooms place
    their instruments with place()."""
    return 0
