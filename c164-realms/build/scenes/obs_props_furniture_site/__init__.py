"""Test scene of the work package props/furniture's outdoor half (card section 13, plan A4-site
section 6: the packages of the site are blocks only, so the benches and the luggage are placed here).

The site is built whole, then furniture.site() asks for the furniture of the site on it, then the
sky's light sources. Nothing is added by hand: the picture shows what site() places on the ground as
the tree has it, and what it leaves out is written under the scene's own name in the run's note:

  python -m scenes.obs_props_furniture_site     writes shots.json, then read the note it prints

A package whose ground is not in the tree yet (the cable-car station, the south lookout) has its
pieces named in canvas.furniture_left_out rather than floating in the air, so this scene has fewer
pieces than the nine of the finished site until those packages are merged.
"""
from artkit.canvas import Canvas

from scenes.obs import site, sky
from scenes.obs.props import furniture

BIOME = "obs_blue"
BIOME_MARGIN = 80
BIOME_MARGIN_Y = 140
TIME = 14000                    # light version A, the default


def build():
    c = Canvas()
    site.build(c, (0, 0, 0))
    n = furniture.site(c)       # the switch DRESS stays off; the site is asked for here
    sky.build(c, (0, 0, 0))     # the light sources go in last, as in the master scene
    c.entity_counts = {"props": n}
    return c


def build_models():
    """The benches and the luggage are the props line's models, taken as the line has them."""
    return furniture.models()


def write_pack(pack_dir):
    """The site's paving is repainted by the materials line; the furniture is a model, not a block."""
    from scenes.obs import materials
    return materials.pack(pack_dir)


def shots():
    """The sunset terrace, where four benches stand: the way a sitter looks, the row along the rail,
    and the backs the building sees."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos],
                    "look_at": [round(v, 2) for v in look_at], "time": TIME})

    # the benches stand at x -23.0 (z +-4.5, from the pair by the walk) and x -20.0 (z +-10.5)
    shot("terrace_row", (-8.0, 6.0, 0.5), (-22.0, 0.5, 0.5))          # the row, from the building
    shot("terrace_west", (-30.0, 3.0, 0.5), (-22.0, 0.6, 0.5))        # the row, from over the rail
    shot("bench_walk", (-19.5, 1.7, 4.5), (-23.5, 0.6, 4.5))          # a sitter's view, afterglow west
    shot("bench_inner", (-16.8, 2.2, 4.5), (-23.0, 0.5, 4.5))         # the walk's pair, from in front
    shot("bench_back", (-26.5, 1.7, 4.5), (-20.0, 0.6, 4.5))          # the back, from behind the rail
    shot("bench_end", (-22.4, 1.4, 1.4), (-23.5, 0.6, 4.2))           # end-on: the cast end frame
    shot("bench_outer", (-17.5, 2.0, 10.5), (-20.5, 0.6, 10.5))       # the outer pair, on the slate
    shot("walk_south", (-24.0, 2.4, 12.0), (-23.0, 0.6, 2.0))         # along the walk, both pairs
    shot("terrace_aerial", (-16.0, 12.0, 16.0), (-22.0, 0.0, 2.0))    # where the rail runs
    return out
