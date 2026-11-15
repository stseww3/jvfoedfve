"""Test scene of the work package interiors/domeroom (plan/packages/interiors/domeroom.md).

The dome room in a box: the drum and the dome as the assembly has them today (main/_dome), and
stand-ins for what other packages bring -- the floor, the opening round the pier and its railing
(main/shell, c231), the two doors to the roof terraces (main/dome, c222), the telescope
(machines/refractor, c237). The stand-ins use the skeleton's numbers and are dropped one by one as
those packages are merged.

    python -m scenes.obs_int_domeroom      the room as text (three sections, seven plans) and its checks
"""
import math

from artkit.canvas import Canvas

from scenes.obs import materials, sky
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
# where the ring stair comes out, until main/shell is in the tree (c231, g2 #32860)
EXIT = domeroom.stair_exit() or (S.DOME_CENTRE[0], S.PIER_ENVELOPE[1] - 1)
# the stand-in tube (c237, g2 #33181): its elevation, and how far the eyepiece end and the objective
# are from where the axes cross
TUBE_ELEVATION, TUBE_BACK, TUBE_FRONT = 41.05, 5.5, 9.5


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
    elev = math.radians(TUBE_ELEVATION)
    cross = (ex - TUBE_BACK * math.cos(elev), ey + TUBE_BACK * math.sin(elev), ez)
    front = (cross[0] - TUBE_FRONT * math.cos(elev), cross[1] + TUBE_FRONT * math.sin(elev), ez)

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


def dressed():
    """The box with the room in it, before the light line has been over it, and the number of
    display entities the room placed: what the checks of __main__ compare with shell()."""
    c = shell()
    return c, domeroom.dress(c)


def build():
    c, n = dressed()
    sky.build(c, (0, 0, 0))         # the light line's sources go in last, when every piece is in place
    c.entity_counts = {"interiors": n}
    return c


def build_models():
    """The room's own models, and those of the shared pieces it places when they are in the tree."""
    out = dict(domeroom.models())
    for name in ("furniture", "paper", "instruments"):
        module = domeroom._other("props", name)
        if module is not None:
            out.update(module.models())
    return out


def write_pack(pack_dir):
    """The room paints nothing itself: the comet in the slit is the sky line's picture, the blocks
    are repainted as the materials line has them today."""
    return list(sky.pack(pack_dir) or []) + list(materials.pack(pack_dir) or [])
