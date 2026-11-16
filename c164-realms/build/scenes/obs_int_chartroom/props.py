"""The models the test scene of the chart room shows: the room's own, the lamps of props/lamps, the
pieces of the props line that are in the tree, and the window linings of materials/windows."""
from scenes.obs.interiors import chartroom
from scenes.obs.materials import windows
from scenes.obs.props import lamps

PEERS = ("furniture", "paper", "instruments")
SCALE = dict(lamps.SCALE)


def build_models():
    out = dict(lamps.models())
    for name in PEERS:
        peer = chartroom._peer(name)
        if peer is not None:
            out.update(peer.models())
    if hasattr(windows, "models"):
        out.update(windows.models())
    out.update(chartroom.models())
    return out
