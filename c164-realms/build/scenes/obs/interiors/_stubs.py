"""Stand-ins for what the other lines deliver (skipped by the category auto-discovery).

The machines (the orrery c236, the mother clock c238) and the props (the switchboard, furniture,
charts, globes, lamps: A5/c179/c220) arrive as display-entity models. Until they do, the hall is
dressed with these plain block stand-ins, so its layout, its light and its sight lines can be judged.
Each takes put(x, y, z, state) in the room's coordinates, places blocks only, and names in its
docstring which delivery replaces it. None places a display entity (the room stays at budget 0 until
the real models move in).
"""
import math

from ..common import blocks as B
from ..common import skeleton as S

OPP = {"north": "south", "south": "north", "west": "east", "east": "west"}
OUT = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}


def panel(block, wall):
    """A thin panel (a trapdoor) laid flat against the wall on the `wall` side of its cell."""
    return f"{block}[facing={OPP[wall]},half=bottom,open=true]"


def orrery(put, cx, cz, ring_y, hang_y):
    """c236 machines/orrery. A brass orbit about five across round a lit opal sun, three planets on
    it, four arms, a rod up to the ceiling boss. (cx, cz) is the cell under ORRERY_CENTRE; ring_y the
    orbit course, hang_y the ceiling block it hangs from. The real orrery is a ring of display
    entities; this is only the block mass that stands in for it in the box."""
    put(cx, ring_y, cz, B.WINDOW_FROSTED.block)                     # the sun (a lamp in the real one)
    for side, (dx, dz) in OUT.items():
        put(cx + dx, ring_y, cz + dz, f"{B.IRON_ROD}[facing={side}]")   # the four arms
    ring = [(dx, dz) for dx in range(-2, 3) for dz in range(-2, 3)
            if round(math.hypot(dx, dz)) == 2]
    for dx, dz in ring:
        put(cx + dx, ring_y, cz + dz, B.BRASS_RAIL)                 # the orbit
    for (dx, dz), block in zip(((2, 0), (-1, -2), (-2, 1)),
                               (B.VERDIGRIS, B.OLD_COPPER, B.ASHLAR_EMBLEM)):
        put(cx + dx, ring_y, cz + dz, block)                        # three planets
    for y in range(ring_y + 1, hang_y):                             # the rod up to the ceiling boss
        put(cx, y, cz, f"{B.IRON_PIPE}[axis=y]")


def mother_clock(put, x, z, y0, y1):
    """c238 machines/clock. A tall regulator in a dark case against the pier's east face (x = back_x,
    on the axis), its dial facing east; a stone dais at its foot (the plinth A0 #207 asked the hall to
    leave). The real clock is a display entity on the pier face; this is the dais and a block stand-in."""
    for dz in (-1, 0, 1):                                           # the dais at the foot
        put(x, S.GROUND, z + dz, B.ASHLAR_FINE.slab + "[type=bottom]")
    for y in range(y0, y1):
        put(x, y, z, B.DARK_WOOD.block)
    put(x, y0 + 2, z, f"{B.PANELS['dial']}[facing=east]")           # the dial
    put(x, y1, z, B.DARK_WOOD.stairs + "[facing=east,half=top]")    # the pediment


def switchboard(put, cells, y, facing, rows):
    """A5/props switchboard: a marble backboard on an iron cabinet carrying rows of instrument panels
    and brass knife switches. cells: the plan cells left to right along a wall; rows: one tuple of
    panel names per course, the bottom course first."""
    for i, (x, z) in enumerate(cells):
        put(x, y, z, B.IRON_PLATE)                                  # the cabinet base
        for j, row in enumerate(rows):
            name = row[i % len(row)]
            put(x, y + 1 + j, z, f"{B.PANELS[name]}[facing={facing}]")
        put(x, y + 1 + len(rows), z, B.ASHLAR_FINE.slab + "[type=top]")   # the marble cornice


def bench(put, cells, wall):
    """c179 props/furniture: a bench, its back to the wall on the `wall` side."""
    for x, z in cells:
        put(x, S.GROUND, z, f"{B.DARK_WOOD.stairs}[facing={OPP[wall]},half=bottom]")


def charts(put, cells, y, wall, rows=2):
    """c179 props/paper: framed star charts hung flat on a wall, as brass plaques."""
    for x, z in cells:
        for j in range(rows):
            put(x, y + j, z, panel(B.BRASS_HATCH, wall))


def case(put, x, z, wall):
    """c179 props/furniture: a low display case, a glass top on a dark-wood base."""
    put(x, S.GROUND, z, B.DARK_WOOD.slab + "[type=bottom]")
    put(x, S.GROUND + 1, z, B.WINDOW_DARK.block)


def globe(put, x, z, block):
    """c179 props/instruments: a floor globe on a brass stand."""
    put(x, S.GROUND, z, f"{B.BRASS_COLUMN}[axis=y]")
    put(x, S.GROUND + 1, z, block)


def wall_lamp(put, x, y, z):
    """c220/c179 props/lamps: a caged bulb let into the stand-in wall. In the real shell this is a
    lamp model on the wall and a light block beside it."""
    put(x, y, z, f"{B.IRON_BULB}[lit=true]")
