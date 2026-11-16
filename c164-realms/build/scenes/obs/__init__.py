"""obs: the master scene of the observatory. S2 assembles the categories of work packages here.

Each category is a subpackage under this folder (materials, site, main, machines, interiors,
props, motion, sky) and offers the same three functions (plan/roles/INTERFACE.md):

    build(canvas, origin) -> int      place blocks and display entities; return the entity count
    models()              -> {name: artkit.models.Model}   custom models, names prefixed per line
    pack(pack_dir)        -> [str]     write the line's own resource-pack files

This package ties them together for the drivers:
    build()            -> Canvas      build every line at ORIGIN
    build_models()     -> {...}       every line's models merged (makepack.py / render.py read this)
    write_pack(dir)    -> [str]       every line's pack() (plus, from the drivers, the item models)
The look (biomes, timelines) is A2's, in sky/mood.py, re-exported by mood.py.
"""
import importlib

from artkit.canvas import Canvas

# the categories, in the order they lay the scene: materials places no blocks; site lays the ground,
# then the shells, the machines, the rooms, the props and what moves; sky comes last, because its
# light sources are placed against the walls, windows and lamps that stand by then and its block
# clouds keep clear of the mountain
LINES = ["materials", "site", "main", "machines", "interiors", "props", "motion", "sky"]

ORIGIN = (0, 0, 0)          # the master scene builds every line at the skeleton origin
BIOME = "obs_blue"          # the default light version; one of sky.mood.BIOMES
BIOME_MARGIN = 80           # the look has to reach the far camera positions, not only the blocks
BIOME_MARGIN_Y = 160
# The guide (card motion/guide): the arrival title and the credit plaque, the plaques, the star
# charts. Their packages and tools/export.py read these two switches from here.
GUIDE = True                # False: no part of the guide is built (export: --no-guide)
GUIDE_CHARTS = True         # False: the star charts alone are left out
# The opening (card motion/arrival): who comes for the first time rides up in the train.
ARRIVAL = True              # False: he stands on the platform as in A8, the train keeps its timetable (export: --no-arrival)


def _line(name):
    return importlib.import_module(f"{__name__}.{name}")


def build():
    c = Canvas()
    c.master = True     # only this canvas says so: a package that shows something in the master scene alone
    #                     (sky/ridges, sky/cloudsea) asks getattr(canvas, "master", False); a test scene's has none
    counts = {}
    for name in LINES:
        n = _line(name).build(c, ORIGIN)
        counts[name] = int(n or 0)
    c.entity_counts = counts
    return c


def build_models():
    """Every line's custom models, merged. Names are prefixed per line, so a clash is a bug that
    check.py catches; here a clash raises at once rather than silently dropping a model."""
    out = {}
    for name in LINES:
        for key, model in (_line(name).models() or {}).items():
            if key in out:
                raise ValueError(f"model name {key!r} is used by two lines (prefix per line)")
            out[key] = model
    return out


def write_pack(pack_dir):
    out = []
    for name in LINES:
        out += list(_line(name).pack(pack_dir) or [])
    return out
