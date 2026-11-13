"""Test scene of the work package materials/iron (plan/packages/materials/iron.md).

What it is for: to see the cast iron of every oxidized_* copper block that has no waxed_ twin, and
to see that the waxed_oxidized_* twin beside it stays verdigris. The twin stations set each repainted
block next to the vanilla block it shares its model and texture files with -- cast iron beside
verdigris, old copper beside exposed copper -- in every shape the family has, so a glance confirms
the split, and the two lamps (the caged bulb, the lantern) show their glow. Two eight-by-eight walls,
the riveted plate (with its stairs and slabs at the foot) and the plain plate, are there to be read
close for the rivets and seams and from twenty blocks for stripes (c190's pre-review, point 3): a
bolted run must not tile into continuous diagonal lines or evenly spaced bars, and the plate face
must keep enough light and dark.

    python -m scenes.obs_mat_iron        writes shots.json from the layout below
"""
from artkit.canvas import Canvas

from scenes.obs import materials
from scenes.obs.common import blocks as B
from scenes.obs.materials import _board

BIOME = "obs_blue"
Z = 0
TIME = 14000        # the default light version (sky line)


def walls(c, x, z):
    """Two eight-by-eight walls for the stripe check: the riveted plate (with its stairs and slabs at
    the foot) and the plain plate, a gap between them."""
    _board.wall(c, B.IRON_RIVETED, x, 0, z)             # x..x+7, its stairs and slabs at z+1
    _board.wall(c, B.IRON_PLATE, x + 10, 0, z)          # x+10..x+17
    _board.stage(c, x, x + 17, z, height=9)
    return x + 19


STATIONS = [("plates", _board.twins_plates), ("shapes", _board.twins_shapes), ("walls", walls)]


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


def build_models():
    return {}           # blocks only


def write_pack(pack_dir):
    return materials.pack(pack_dir)


def shots():
    """Camera positions from the layout: the two twin rows in halves at reading distance (the split
    and the lamp glow), each eight-by-eight wall close (rivets, seams, brushing), the riveted treads
    from above, and both walls from twenty blocks (stripes)."""
    spans = layout()
    out = []

    def front(name, x0, x1, y=1.6):
        """Looking north at x0..x1 from as near as shows all of it."""
        d = max(5.0, (x1 - x0 + 2) / 2.6)
        out.append({"name": name, "pos": [(x0 + x1) / 2.0, y + 1.2, round(Z + 1 + d, 1)], "look_at": [(x0 + x1) / 2.0, y, Z], "time": TIME})

    for name in ("plates", "shapes"):                   # each row is wide: read it in halves
        x0, x1 = spans[name]
        x1 -= 2                                          # the station's own last x, without the gap
        mid = (x0 + x1) // 2
        front(f"{name}_a", x0, mid)
        front(f"{name}_b", mid, x1)
    xs = spans["shapes"][0]                              # the caged bulb (lit over unlit) and the lantern
    front("shapes_lamps", xs + 25, xs + 34)
    xw = spans["walls"][0]
    out.append({"name": "wall_riveted", "pos": [xw + 3.5, 4.6, Z + 8.5], "look_at": [xw + 3.5, 4.0, Z], "time": TIME})
    out.append({"name": "wall_plate", "pos": [xw + 13.5, 4.6, Z + 8.5], "look_at": [xw + 13.5, 4.0, Z], "time": TIME})
    out.append({"name": "wall_treads", "pos": [xw + 3.5, 4.2, Z + 4.6], "look_at": [xw + 3.5, 0.2, Z + 1.0], "time": TIME})
    out.append({"name": "walls_far", "pos": [xw + 8.5, 5.0, Z + 20.0], "look_at": [xw + 8.5, 4.0, Z], "time": TIME})
    return out
