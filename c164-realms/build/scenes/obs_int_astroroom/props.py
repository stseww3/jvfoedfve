"""The models the test scene of the astrograph room shows: the room's own, the astrograph's, and
those of the props line the room places (lamps, furniture, paper)."""
from scenes.obs.interiors import astroroom
from scenes.obs.machines import astro
from scenes.obs.props import furniture, lamps, paper

SCALE = {**lamps.SCALE, **astro.SCALE}


def build_models():
    out = dict(lamps.models())
    for peer in (furniture, paper, astro):
        out.update(peer.models())
    out.update(astroroom.models())
    return out
