"""Test scene of the work package materials/panels (plan/packages/materials/panels.md).

What it is for: to see the sixteen instrument panels as what they are made for, a wall.

    wall        one bay of eight by four, every kind twice, under the lamp row: each face close, the
                bay from twenty blocks, and from the side for the casing
    room        the bay and its mirror image as the wall of a closed room of the timing room's size
                (16 long, 12 deep, 7 high), on a riveted plinth under plain plate, with no light but
                three weak lamps where desks would stand: the dark iron wall with a few things
                glowing on it that view V10 is about, and the casing beside cast iron
    turn        one block for each way a panel can face, free-standing: the instrument shows on the
                side it faces and nowhere else, and it stands upright there (a register, whose
                figures would show a mirrored picture, with an oscilloscope on top of it)
    animated    the four that move, side by side, to be watched in the game

The bay is this package's proposal for the timing room; where the panels finally stand is the
interiors line's to say. Its rows are sorted the way a switchboard bay is: at the top the louvres
and the valves that need them, with the nameplates; under them what is read from across the room
(dials, gauges, pilot lamps, the bell); at hand height the switches, the register, the
oscilloscope and the recorder; at the foot the fuses, relays, jack fields and drawers. Each row
reads the same from both ends, but for the oscilloscope and the recorder side by side in its
middle.

    python -m scenes.obs_mat_panels        writes shots.json from the layout below
"""
from artkit.blocks import st
from artkit.canvas import Canvas

from scenes.obs import materials
from scenes.obs.common import blocks as B
from scenes.obs.materials import _board

BIOME = "obs_blue"
Z = 0
TIME = 14000        # the default light version (sky line)

# one bay, top row first
BAY = [row.split() for row in (
    "louvre       louvre      nameplate tubes       tubes       nameplate louvre      louvre",
    "bell         pilot_lamps gauges    dial        dial        gauges    pilot_lamps bell",
    "knife_switch bus_switch  counter   scope       recorder    counter   bus_switch  knife_switch",
    "drawers      fuses       relays    patch_panel patch_panel relays    fuses       drawers",
)]
WIDE, HIGH = len(BAY[0]), len(BAY)
ROOM = (16, 12, 7)                  # the timing room: along the wall, deep, high (interiors, timeroom)
DESK_LAMP = 12                      # a second-rank light, three blocks from the wall
FACINGS = ("south", "east", "north", "west")
ANIMATED = ("tubes", "scope", "counter", "pilot_lamps")


def bay(c, x, y, z, mirrored=False):
    """One bay with its foot at y, facing south."""
    for j, row in enumerate(BAY):
        for i, name in enumerate(row[::-1] if mirrored else row):
            c.set(x + i, y + HIGH - 1 - j, z, st(B.PANELS[name], facing="south"))


def wall(c, x, z):
    bay(c, x, 0, z)
    _board.stage(c, x, x + WIDE - 1, z)
    return x + WIDE + 1


def room(c, x, z):
    """The wall at z facing into the room south of it; the room is closed, the camera stands in it."""
    long, deep, high = ROOM
    x1, z1 = x + long - 1, z + deep
    c.box(x - 1, -1, z, x1 + 1, -1, z1 + 1, B.FLOOR_WOOD.block)
    c.box(x - 1, high, z, x1 + 1, high, z1 + 1, B.DARK_WOOD.block)
    for wx in (x - 1, x1 + 1):
        c.box(wx, 0, z, wx, high - 1, z1 + 1, B.DARK_WOOD.block)
    c.box(x, 0, z1 + 1, x1, high - 1, z1 + 1, B.DARK_WOOD.block)
    c.box(x, 0, z, x1, 0, z, B.IRON_RIVETED.block)
    c.box(x, 1 + HIGH, z, x1, high - 1, z, B.IRON_PLATE)
    bay(c, x, 1, z)
    bay(c, x + WIDE, 1, z, mirrored=True)
    for dx in (2, 8, 13):
        c.set(x + dx, 2, z + 4, st(B.LIGHT, level=DESK_LAMP))
    return x1 + 3


def turn(c, x, z):
    """Four posts three apart, one for each facing; no backdrop, so that they are seen from both
    sides, and lamps on both sides."""
    c.box(x - 1, -1, z - 5, x + 11, -1, z + 5, _board.FLOOR)
    for i, facing in enumerate(FACINGS):
        px = x + 1 + 3 * i
        c.set(px, 0, z, _board.BASE)
        c.set(px, 1, z, st(B.PANELS["counter"], facing=facing))
        c.set(px, 2, z, st(B.PANELS["scope"], facing=facing))
        for dz in (-3, 3):
            c.set(px, 3, z + dz, st(B.LIGHT, level=15))
    return x + 13


def animated(c, x, z):
    n = len(ANIMATED)
    c.box(x, 0, z, x + n - 1, 0, z, B.IRON_RIVETED.block)
    for i, name in enumerate(ANIMATED):
        c.set(x + i, 1, z, st(B.PANELS[name], facing="south"))
    c.box(x, 2, z, x + n - 1, 2, z, B.IRON_PLATE)
    _board.stage(c, x, x + n - 1, z, height=5)
    return x + n + 1


STATIONS = [("wall", wall), ("room", room), ("turn", turn), ("animated", animated)]


def layout(c=None):
    """Where each station stands: {name: (first x, x after it)}. Builds into `c` when given one."""
    c = c or Canvas()
    spans, x = {}, 0
    for name, station in STATIONS:
        end = station(c, x, Z)
        spans[name] = (x, end)
        x = end + 2
    return spans


def build():
    c = Canvas()
    layout(c)
    return c


def write_pack(pack_dir):
    return materials.pack(pack_dir)


def shots():
    """Camera positions from the layout. The bay: whole, its two halves close enough to read every
    face (between them they hold all sixteen kinds), from twenty blocks, and from above its east
    end for the casing on its side and top. The room: the whole wall from the back of the room, and
    along the wall from near. The posts from the south-east and from the north-west. The four that
    move, close."""
    spans = layout()
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 1) for v in pos], "look_at": [round(v, 1) for v in look_at],
                    "time": TIME})

    x = spans["wall"][0]
    mid, eye = x + WIDE / 2.0, HIGH / 2.0
    shot("wall", (mid, eye + 0.6, Z + 6.5), (mid, eye, Z))
    shot("wall_left", (x + WIDE / 4.0, eye + 0.2, Z + 4.2), (x + WIDE / 4.0, eye, Z))
    shot("wall_right", (x + 3 * WIDE / 4.0, eye + 0.2, Z + 4.2), (x + 3 * WIDE / 4.0, eye, Z))
    shot("wall_far", (mid, eye + 1.0, Z + 21.0), (mid, eye, Z))
    shot("wall_side", (x + WIDE + 3.0, HIGH + 1.5, Z + 3.5), (x + WIDE - 2.0, eye + 0.5, Z + 0.5))

    x = spans["room"][0]
    long, deep, high = ROOM
    mid = x + long / 2.0
    shot("room", (mid, 3.2, Z + deep + 0.4), (mid, 2.8, Z))
    shot("room_near", (x + 2.5, 2.4, Z + 5.0), (x + 9.5, 2.8, Z))

    x = spans["turn"][0]
    mid = x + 6.0
    shot("turn_se", (x + 12.5, 3.8, Z + 4.6), (mid, 1.6, Z + 0.5))
    shot("turn_nw", (x - 0.5, 3.8, Z - 3.6), (mid, 1.6, Z + 0.5))

    x = spans["animated"][0]
    mid = x + len(ANIMATED) / 2.0
    shot("animated", (mid, 1.9, Z + 4.0), (mid, 1.5, Z))
    return out
