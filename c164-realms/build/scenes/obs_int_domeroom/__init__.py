"""Test scene of the work package interiors/domeroom (plan/packages/interiors/domeroom.md).

The dome room in a box: the drum and the dome as the assembly has them today (main/_dome), and
stand-ins for what other packages bring -- the floor, the opening round the pier and its railing
(main/shell, c231), the two doors to the roof terraces (main/dome, c222), the telescope
(machines/refractor, c237). The stand-ins use the skeleton's numbers and are dropped one by one as
those packages are merged.

    python -m scenes.obs_int_domeroom      the room as text (two sections, four plans) and its checks
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
# where the ring stair comes out, until main/shell says (director, g2 #31564: on the north side)
EXIT = domeroom.stair_exit() or (S.DOME_CENTRE[0], S.PIER_ENVELOPE[1] - 1)
TUBE_FRONT = 10.0               # stand-in tube: this far from the axes' crossing to the objective


def _shell_standin(c):
    """What main/shell lays in the dome room: the floor, the pier's cap, the railing round the
    opening with a gap at the stair's exit. Under it the box is closed off in dark stone."""
    inside = domeroom.room()
    hole = O.box(*S.PIER_ENVELOPE)
    for x, z in inside - hole:
        c.set(x, FLOOR_Y, z, B.FLOOR_WOOD.block)
    for x, z in O.box(*S.PIER_CAP):
        for y in range(UNDER_Y + 1, FLOOR_Y + 1):
            c.set(x, y, z, B.ASHLAR_FINE.block)
    for x, z in O.ring(hole) - {EXIT}:
        c.set(x, FLOOR_Y + 1, z, B.IRON_BARS)
    whole = O.disc(S.DOME_CENTRE[0], S.DOME_CENTRE[1], S.DOME_R)
    for x, z in whole:
        c.set(x, UNDER_Y, z, B.SLATE_SMOOTH.block)
        if (x, z) not in inside:
            for y in range(UNDER_Y + 1, S.DRUM_BASE):
                c.set(x, y, z, B.SLATE_BRICK.block)


def _doors_standin(c):
    """The two doorways through the drum, cut all the way into the room."""
    inside = domeroom.room()
    y0, y1 = S.DOME_ROOM_DOORS["y"]
    for cell in S.DOME_ROOM_DOORS["cells"]:
        inward = (0, -1 if cell[1] > S.DOME_CENTRE[1] else 1)
        while cell not in inside:
            for y in range(y0, y1 + 1):
                c.clear(cell[0], y, cell[1])
            cell = O.step(cell, inward)


def _scope_standin(c):
    """A line of iron plate where the tube is, a column of it for the mount on the pier."""
    ex, ey, ez = domeroom.eyepiece()
    ax, az = S.DOME_AXIS
    elev = math.radians(41.0)
    cross = (ax, ey + (ex - ax) * math.tan(elev), az)
    front = (ax - TUBE_FRONT * math.cos(elev), cross[1] + TUBE_FRONT * math.sin(elev), az)

    def cell(p):
        return (int(math.floor(p[0])), int(math.floor(p[1])), int(math.floor(p[2])))

    c.line(cell((ex, ey, ez)), cell(front), B.IRON_PLATE)
    mx, my, mz = cell(cross)
    for y in range(int(S.PIER_TOP_Y), my + 1):
        c.set(mx, y, mz, B.IRON_PLATE)


def shell():
    """The box without the room: what the room is laid into."""
    c = Canvas()
    _dome.build(c)
    _shell_standin(c)
    _doors_standin(c)
    _scope_standin(c)
    return c


def build():
    c = shell()
    domeroom.dress(c)
    return c


def write_pack(pack_dir):
    """The room paints nothing itself; it stands on the repainted blocks as the materials line has
    them today."""
    return materials.pack(pack_dir)
