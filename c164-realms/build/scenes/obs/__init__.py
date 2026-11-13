"""obs: the master scene of the observatory. S2 assembles the seven production lines here.

Each line is a subpackage under this folder (materials, sky, main, props, site, machines,
interiors) and offers the same three functions (plan/roles/INTERFACE.md):

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

# the seven lines, in the order they lay the scene (materials and sky place no blocks; site lays the
# ground, then the shells, then the dressing and the interiors, then the props as display entities)
LINES = ["materials", "sky", "site", "main", "machines", "interiors", "props"]

ORIGIN = (0, 0, 0)          # the master scene builds every line at the skeleton origin
BIOME = "obs_blue"          # the default light version; one of sky.mood.BIOMES
BIOME_MARGIN = 80           # the look has to reach the far camera positions, not only the blocks
BIOME_MARGIN_Y = 160


def _line(name):
    return importlib.import_module(f"{__name__}.{name}")


def build():
    c = Canvas()
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
