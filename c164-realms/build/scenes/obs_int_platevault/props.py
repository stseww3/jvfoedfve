"""The models the test scene of the plate vault shows: the room's own, and those of the props line
the room places (lamps, furniture, paper, signs)."""
from scenes.obs.interiors import platevault
from scenes.obs.props import furniture, lamps, paper, signs

SCALE = dict(lamps.SCALE)


def build_models():
    out = dict(lamps.models())
    for peer in (furniture, paper, signs):
        out.update(peer.models())
    out.update(platevault.models())
    return out
