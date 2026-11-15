"""Stand-ins for what the other lines deliver (skipped by the category auto-discovery).

Blocks only, and only for the hall's own test scene (build/scenes/obs_int_starhall): the two machines
the star hall is the background of, and the props it places, for as long as their packages are not in
the tree. The master scene never gets a stand-in: there a piece whose package is missing is left out.

Each takes put(x, y, z, state), which sets a block in the room's coordinates, and names the delivery
that replaces it. None places a display entity.
"""
import math

from artkit import arch
from artkit.blocks import st

from ..common import blocks as B
from ..common import skeleton as S

OPP = {"north": "south", "south": "north", "west": "east", "east": "west"}


def panel(block, wall):
    """A thin panel (a trapdoor on edge) standing against the wall on the `wall` side of its cell: it
    stands on the side it turns its back to."""
    return st(block, facing=OPP[wall], half="bottom", open="true")


def orrery(put, level):
    """machines/orrery (c236). The envelope of the hung orrery: an orbit five across round a pale sun
    at the ring's height, a rod up to the beam it hangs from. The sun's light, `level`, goes into the
    free cell under the sun's block: the real one offers it in the sun's own cell."""
    cx, cz = S.ORRERY_CENTRE
    x, z, y = int(math.floor(cx)), int(math.floor(cz)), int(math.floor(S.ORRERY_RING_Y))
    for ox, oz in arch.outline(cx, cz, S.ORRERY_R):
        put(ox, y, oz, B.BRASS_RAIL)
    put(x, y, z, B.WINDOW_FROSTED.block)
    for yy in range(y + 1, S.STAR_HALL_CEIL):
        put(x, yy, z, st(B.IRON_PIPE, axis="y"))
    put(x, y - 1, z, st(B.LIGHT, level=level))


def mother_clock(put, level):
    """machines/clock (c238). A dark case with its dial before the pier's east face, standing on the
    hall's step (y 1 .. 5), and the hidden light before the dial, `level`."""
    x = int(S.MOTHER_CLOCK["back_x"])
    z = int(math.floor(S.MOTHER_CLOCK["z"]))
    y0, y1 = (int(v) for v in S.MOTHER_CLOCK["y"])
    for y in range(y0, y1):
        put(x, y, z, B.DARK_WOOD.block)
    put(x, y0 + 2, z, st(B.PANELS["dial"], facing=S.MOTHER_CLOCK["facing"]))
    put(x + 1, y0 + 2, z, st(B.LIGHT, level=level))


def bench(put, cells, y, wall):
    """props/furniture "bench" (c179): its back to the wall on the `wall` side."""
    for x, z in cells:
        put(x, y, z, st(B.DARK_WOOD.stairs, facing=wall, half="bottom"))


def table(put, cells, y):
    """props/furniture "display_table", "writing_desk" (c179): a top one block up, open below."""
    for x, z in cells:
        put(x, y, z, st(B.DARK_WOOD.slab, type="top"))


def box(put, cells, y):
    """props/furniture "trunk" (c179): half a block high."""
    for x, z in cells:
        put(x, y, z, st(B.DARK_WOOD.slab, type="bottom"))


def plate(put, x, y, wide, high, wall, row):
    """props/paper (c197): an enamel chart on a wall, `wide` by `high` blocks about the point (x, y),
    as brass panels in the cells of `row`, the row of cells along that wall."""
    x0 = int(round(x - wide / 2.0))
    y0 = int(math.floor(y - high / 2.0 + 0.5))
    for cx in range(x0, x0 + int(math.ceil(wide))):
        for cy in range(y0, y0 + int(math.ceil(high))):
            put(cx, cy, row, panel(B.BRASS_HATCH, wall))
