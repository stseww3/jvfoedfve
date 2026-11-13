"""Test scene of the work package materials/respack-redirect (plan/packages/materials/).

What it is for: to see that redirecting a block changes that block and nothing else. Every repainted
copper block stands beside the vanilla block it shares its model and texture files with -- cast iron
beside waxed verdigris, old copper beside unwaxed exposed copper -- in every shape the family has.
The other stations are a catalogue of all repainted roles as the material packages stand today
(stand-ins until a family is painted for real): the four stones, the six windows, the sixteen
instrument panels, the brass family and the small pieces, the five tones of the cloud sea.

    python -m scenes.obs_mat_redirect        writes shots.json from the layout below
"""
from artkit.canvas import Canvas

from scenes.obs import materials
from scenes.obs.materials import _board

BIOME = "obs_blue"
Z = 0
STATIONS = [("plates", _board.twins_plates), ("shapes", _board.twins_shapes), ("stone", _board.stone),
            ("windows", _board.windows), ("panels", _board.panels), ("brass", _board.brass),
            ("clouds", _board.clouds)]
TIME = 14000        # the default light version (sky line)


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
    """Camera positions from the layout: each station whole and in halves at reading distance, the
    treads from above, the lit windows and the panels from the side."""
    spans = layout()
    out = []

    def front(name, x0, x1, y=1.6):
        """Looking north at x0..x1 from as near as shows all of it."""
        d = max(5.0, (x1 - x0 + 2) / 2.6)
        out.append({"name": name, "pos": [(x0 + x1) / 2.0, y + 1.2, round(Z + 1 + d, 1)], "look_at": [(x0 + x1) / 2.0, y, Z], "time": TIME})

    for name, (x0, x1) in spans.items():
        x1 -= 2                                         # the station's own last x, without the gap
        if x1 - x0 > 18:
            mid = (x0 + x1) // 2
            front(f"{name}_a", x0, mid)
            front(f"{name}_b", mid, x1)
        else:
            front(name, x0, x1)
    x0 = spans["plates"][0]
    out.append({"name": "plates_treads", "pos": [x0 + 7.0, 4.2, Z + 4.6], "look_at": [x0 + 7.0, 0.2, Z + 0.7], "time": TIME})
    x0 = spans["stone"][0]
    out.append({"name": "stone_treads", "pos": [x0 + 6.0, 4.2, Z + 4.6], "look_at": [x0 + 6.0, 0.2, Z + 0.7], "time": TIME})
    x0 = spans["panels"][0]
    out.append({"name": "panels_side", "pos": [x0 + 4.5, 1.8, Z + 4.5], "look_at": [x0 + 10.5, 0.5, Z + 0.5], "time": TIME})
    x0 = spans["windows"][0]
    out.append({"name": "windows_side", "pos": [x0 - 3.5, 2.4, Z + 3.5], "look_at": [x0 + 9.0, 1.4, Z + 0.5], "time": TIME})
    return out

