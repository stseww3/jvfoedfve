"""sky/_ways_doors: the lamps of the ways at the doors of the main building. A stretch of
sky/lights: lights.way_lamps() reads LAMPS of every sky/_ways_<stretch>.py and hangs a caged lamp
of props for each row, with its source in the cell before the wall.

The west door (the walk-through's stations C05 and C06; sound's table of 11-16 10:50, "the way to
the west door": three cells of threshold at 2 to 3, the three cells of floor behind them at 3 to
4). The doorway is three cells wide and goes through two layers of wall. Its glazed leaves stand
open along the reveals of the outer layer, from their hinges out to the west; the reveals of the
inner layer are bare stone. One lamp on either of those, in the third row over the floor, over
the head of who walks through: the two look at each other across the doorway, level with the
leaves' glass. At level 8 the thresholds get 6 at the sides and 5 in the middle, the floor behind
them 6 to 7, and who comes up from the sunset terrace sees the lamps through the open door.
"""
from . import _lightkit as L

ROW = 2                                 # the lamp's cell is the third over the floor (lights.WAY_ROW)
LOOKS = {(0, -1): "north", (0, 1): "south", (-1, 0): "west", (1, 0): "east"}


def _west_door():
    """The rows of the west door: the flat-headed doorway of the apse, as main's table of
    doorways gives it. Empty without main, or where that doorway is not three cells wide."""
    try:
        from ..main import _plan
    except ImportError:
        return []
    out = []
    for d in _plan.doors():
        if d["front"] != "apse" or d.get("kind", "door") != "door" or d.get("arch") or len(d["cells"]) != 3:
            continue
        ix, iz = d["inward"]
        ax, az = abs(iz), abs(ix)                                   # along the wall line, towards +x or +z
        cells = sorted(d["cells"])
        row = d["y"][0] + ROW
        for (x, z), step in ((cells[0], -1), (cells[-1], 1)):
            wall = (x + step * ax + ix, row, z + step * az + iz)    # beside the doorway, one layer in
            side = LOOKS[(step * ax, step * az)]
            out.append((wall, LOOKS[(-step * ax, -step * az)], L.WAY,
                        f"the west door, inside the leaves: the {side} reveal"))
    return out


LAMPS = _west_door()
