"""obs_int_astrodrive: a look at the astrograph's driving clock (interiors/_astrodrive) in the small
dome, before the room it belongs to (interiors/astroroom, c336) is in the tree. Not for the
assembly: it lives on the try branch only.

The dome is main/smalldome's on a stand-in of the pavilion's deck, the astrograph machines/astro's,
as in the test scene of that machine.
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.interiors import _astrodrive
from scenes.obs.machines import astro
from scenes.obs.main import smalldome

BIOME = "obs_blue"
DECK_Y = S.ROOF_FLOOR
DECK = (0, S.SMALL_DOME_Z[0] - 2, S.SMALL_DOME_X[1] + 1, S.SMALL_DOME_Z[1] + 2)


def build():
    c = Canvas()
    x0, z0, x1, z1 = DECK
    c.box(x0, DECK_Y, z0, x1, DECK_Y, z1, B.SLATE_SMOOTH.block)
    smalldome.build(c, (0, 0, 0))
    n = astro.build(c)
    n += _astrodrive.place(c)
    sky.build(c, (0, 0, 0))
    c.entity_counts = {"interiors": n}
    return c


def write_pack(pack_dir):
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
