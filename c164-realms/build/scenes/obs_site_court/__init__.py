"""Test scene for site/court (plan ART-PLAN 4): the front court paving, brass meridian and emblem,
read against the main building's east facade so the V2 front axis composes. The main building is the
A3 white-model demo (context only). sky.build() runs last for the light sources (none merged yet;
the biome lights the scene for now), per INTERFACE section 5."""
from artkit.canvas import Canvas

from scenes.obs import main, site, sky

BIOME = "obs_blue"
BIOME_MARGIN = 80
BIOME_MARGIN_Y = 140


def build():
    c = Canvas()
    site.build(c, (0, 0, 0))     # ground.py terraces + plaza.py (the court itself)
    main.build(c, (0, 0, 0))     # context: the main building massing, for the V2 framing
    sky.build(c, (0, 0, 0))      # light sources last (no sky package merged yet: a no-op for now)
    return c
