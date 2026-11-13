"""Stand-ins for what the other lines deliver (skipped by the category auto-discovery).

The machines (A5) and the props (A6) arrive as display-entity models. Until they do, a room is dressed
with these plain block stand-ins, so its layout, its light and its sight lines can be judged. Each
takes put(x, y, z, state) in the room's coordinates, places blocks only, and says in its docstring
which delivery replaces it. None places a display entity.
"""
from ..common import blocks as B

OUT = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
OPP = {"north": "south", "south": "north", "west": "east", "east": "west"}


def panel(block, wall):
    """A thin panel (a trapdoor) standing against the wall on the `wall` side of its cell."""
    return f"{block}[facing={OPP[wall]},half=bottom,open=true]"


def orrery(put, x, y, z, planets=((2, 1, B.VERDIGRIS), (-1, -2, B.OLD_COPPER), (-2, 1, B.ASHLAR_EMBLEM))):
    """A5 machines/orrery. A brass orbit five across round a lit opal globe (the sun is a lamp), three
    planets on the orbit, four arms, hung from (x, z) by a rod. y is the orbit's level."""
    put(x, y, z, B.WINDOW_FROSTED.block)
    for side, (dx, dz) in OUT.items():
        put(x + dx, y, z + dz, f"{B.IRON_ROD}[facing={side}]")
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            if max(abs(dx), abs(dz)) == 2 and abs(dx) != abs(dz):
                put(x + dx, y, z + dz, B.BRASS_RAIL)
    for dx, dz, block in planets:
        put(x + dx, y, z + dz, block)
    put(x, y + 1, z, f"{B.BRASS_COLUMN}[axis=y]")


def hanger(put, x, y0, y1, z):
    """The rod a hung machine hangs by, y0..y1."""
    for y in range(y0, y1 + 1):
        put(x, y, z, f"{B.IRON_PIPE}[axis=y]")


def mother_clock(put, x, y, z, facing):
    """A5/A6 master clock: a tall regulator in a dark case, its dial two blocks up."""
    put(x, y, z, B.DARK_WOOD.block)
    put(x, y + 1, z, B.DARK_WOOD.block)
    put(x, y + 2, z, f"{B.PANELS['dial']}[facing={facing}]")
    put(x, y + 3, z, B.DARK_WOOD.slab + "[type=bottom]")


def switchboard(put, cells, y, facing, rows):
    """A6 props/electrics on A1's panel blocks: a cabinet base and rows of instrument panels.
    cells: the plan cells left to right; rows: one list of panel names per row, bottom row first."""
    for i, (x, z) in enumerate(cells):
        put(x, y, z, B.IRON_PLATE)
        for j, row in enumerate(rows):
            put(x, y + 1 + j, z, f"{B.PANELS[row[i % len(row)]]}[facing={facing}]")


def charts(put, cells, y, wall, rows=2):
    """A6 props/paper: framed star charts on a wall, as brass plaques."""
    for x, z in cells:
        for j in range(rows):
            put(x, y + j, z, panel(B.BRASS_HATCH, wall))


def bench(put, cells, y, wall):
    """A6 props/furniture: a bench with its back to the wall on the `wall` side."""
    for x, z in cells:
        put(x, y, z, f"{B.DARK_WOOD.stairs}[facing={wall},half=bottom]")


def globe(put, x, y, z, block):
    """A6 props/instruments: a floor globe on a brass stand."""
    put(x, y, z, f"{B.BRASS_COLUMN}[axis=y]")
    put(x, y + 1, z, block)


def wall_lamp(put, x, y, z):
    """A6 props/lamps bracket lamp: a caged bulb let into the stand-in wall at (x, y, z). Third-rank
    light (level 4). In the real shell this is a lamp model on the wall and a light block beside it."""
    put(x, y, z, f"{B.IRON_BULB}[lit=true]")
