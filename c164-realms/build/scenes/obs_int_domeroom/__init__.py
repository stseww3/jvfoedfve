"""Test scene of the work package interiors/domeroom (plan/packages/interiors/domeroom.md).

The dome room in a box: the drum and the dome as the assembly has them today (main/_dome), and
stand-ins for what other packages bring -- the floor, the opening round the pier and its railing
(main/shell, c231), the telescope (machines/refractor, c237). The stand-ins use the skeleton's
numbers and are dropped one by one as those packages are merged.

    python -m scenes.obs_int_domeroom      the room as text: the plan at eye height and two sections
"""
import math

from artkit.canvas import Canvas

from scenes.obs import materials
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.interiors import domeroom
from scenes.obs.main import _dome
from scenes.obs.main import _order as O

BIOME = "obs_blue"
CATEGORY = "interiors"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32

FLOOR_Y = S.ROOF_FLOOR
UNDER_Y = S.DRUM_BASE - 4       # the box's bottom: the pier's opening looks down on it
TUBE_FRONT = 10.0               # stand-in tube: this far from the axes' crossing to the objective


def _shell_standin(c):
    """What main/shell lays in the dome room: the floor, the pier's cap, the railing round the
    opening with a gap at the stair's exit. Under it the box is closed off in dark stone."""
    inside = domeroom.room()
    x0, z0, x1, z1 = S.PIER_ENVELOPE
    hole = O.box(x0, z0, x1, z1)
    curb = O.ring(hole)
    exit_cell = (x1 + 1, S.DOME_CENTRE[1])
    for x, z in inside - hole:
        c.set(x, FLOOR_Y, z, B.FLOOR_WOOD.block)
    cx0, cz0, cx1, cz1 = S.PIER_CAP
    for x, z in O.box(cx0, cz0, cx1, cz1):
        for y in range(UNDER_Y + 1, FLOOR_Y + 1):
            c.set(x, y, z, B.ASHLAR_FINE.block)
    for x, z in curb - {exit_cell}:
        c.set(x, FLOOR_Y + 1, z, B.IRON_BARS)
    whole = O.disc(S.DOME_CENTRE[0], S.DOME_CENTRE[1], S.DOME_R)
    for x, z in whole:
        c.set(x, UNDER_Y, z, B.SLATE_SMOOTH.block)
        if (x, z) not in inside:
            for y in range(UNDER_Y + 1, S.DRUM_BASE):
                c.set(x, y, z, B.SLATE_BRICK.block)


def _scope_standin(c):
    """A line of iron plate where the tube is, a block of mount on the pier."""
    ex, ey, ez = domeroom.eyepiece()
    ax, az = S.DOME_AXIS
    cross = (ax, ey + (ex - ax) * math.tan(math.radians(41.0)), az)
    elev = math.atan2(cross[1] - ey, ex - ax)
    front = (ax - TUBE_FRONT * math.cos(elev), cross[1] + TUBE_FRONT * math.sin(elev), az)
    cell = lambda p: (int(math.floor(p[0])), int(math.floor(p[1])), int(math.floor(p[2])))
    c.line(cell((ex, ey, ez)), cell(front), B.IRON_PLATE)
    mx, my, mz = cell(cross)
    for y in range(int(S.PIER_TOP_Y), my + 1):
        c.set(mx, y, mz, B.IRON_PLATE)


def build():
    c = Canvas()
    _dome.build(c)
    _shell_standin(c)
    _scope_standin(c)
    domeroom.dress(c)
    return c


def write_pack(pack_dir):
    """The room paints nothing itself; it stands on the repainted blocks as the materials line has
    them today."""
    return materials.pack(pack_dir)
