"""Test scene of the work package interiors/domeroom (plan/packages/interiors/domeroom.md).

The dome room in a box: the drum and the dome (main/dome once it is in the tree, until then the
massing of main/_dome), and stand-ins for what other packages bring -- the floor, the opening
round the pier and its railing (main/shell), the two doorways to the roof terraces (main/dome),
the telescope (machines/scope: the real one as soon as its module is in the tree, with its red
lamp). The stand-ins use the skeleton's numbers and are dropped one by one as those packages are
merged.

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
# the stand-in tube (machines/scope, version a): its elevation, and how far the eyepiece end and the
# objective are from where the tube turns
TUBE_ELEVATION, TUBE_BACK, TUBE_FRONT = 41.05, 6.4, 8.6


def _shell_standin(c):
    """What main/shell lays in the dome room (c231, cursor/c164-shell-f063): the floor of boards,
    the iron curb round the pier's opening, the railing on it with a gap at the stair's exit, the
    pier's cap. Under it the box is closed off in dark stone."""
    inside = domeroom.room()
    hole = O.box(*S.PIER_ENVELOPE)
    curb = O.ring(hole)
    for x, z in inside - hole:
        c.set(x, FLOOR_Y, z, B.IRON_RIVETED.block if (x, z) in curb else B.FLOOR_WOOD.block)
    for x, z in O.box(*S.PIER_CAP):
        for y in range(UNDER_Y + 1, FLOOR_Y + 1):
            c.set(x, y, z, B.ASHLAR_FINE.block)
    for x, z in curb - {EXIT}:
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


def _scope(c):
    """The telescope: machines/scope once it is in the tree, else a line of iron plate where the
    tube is and a column of it for the mount on the pier. Returns the display entities placed."""
    scope = domeroom._other("machines", "scope")
    if scope is not None:
        return scope.build(c)
    ex, ey, ez = domeroom.eyepiece()
    elev = math.radians(TUBE_ELEVATION)
    cross = (ex - TUBE_BACK * math.cos(elev), ey + TUBE_BACK * math.sin(elev), ez)
    front = (cross[0] - TUBE_FRONT * math.cos(elev), cross[1] + TUBE_FRONT * math.sin(elev), ez)

    def cell(p):
        return (int(math.floor(p[0])), int(math.floor(p[1])), int(math.floor(p[2])))

    # the line starts above the head of the one who stands at the eyepiece: blocks would stand in
    # the observer's own column, which the real tube (display models) leaves free
    rise = (S.ROOF_STAND + 2 - ey) / math.sin(elev)
    low = (ex - rise * math.cos(elev), ey + rise * math.sin(elev) + 0.01, ez)
    c.line(cell(low), cell(front), B.IRON_PLATE)
    mx, my, mz = cell(cross)
    for y in range(int(S.PIER_TOP_Y), my + 1):
        c.set(mx, y, mz, B.IRON_PLATE)
    return 0


def _rotunda(c):
    """The drum and the dome: main/dome in its default version once that package is in the tree
    (c222), else the massing the master scene has today."""
    dome = domeroom._other("main", "dome")
    if dome is not None:
        dome.build(c)
    else:
        _dome.build(c)


def shell():
    """The box without the room: what the room is laid into."""
    c = Canvas()
    _rotunda(c)
    _shell_standin(c)
    _doors_standin(c)
    c.machines = _scope(c)
    return c


def dressed():
    """The box with the room in it, before the light line has been over it, and the number of
    display entities the room placed: what the checks of __main__ compare with shell()."""
    c = shell()
    return c, domeroom.dress(c)


def build():
    c, n = dressed()
    sky.build(c, (0, 0, 0))         # the light line's sources go in last, when every piece is in place
    c.entity_counts = {"interiors": n, "machines": c.machines}
    return c


def build_models():
    """The room's own models, and those of the shared pieces it places when they are in the tree."""
    out = dict(domeroom.models())
    for name in ("furniture", "paper", "instruments"):
        module = domeroom._other("props", name)
        if module is not None:
            out.update(module.models())
    scope = domeroom._other("machines", "scope")
    if scope is not None:
        out.update(scope.models())
    return out


def write_pack(pack_dir):
    """The room paints nothing itself: the comet in the slit is the sky line's picture, the blocks
    are repainted as the materials line has them today."""
    return list(sky.pack(pack_dir) or []) + list(materials.pack(pack_dir) or [])
