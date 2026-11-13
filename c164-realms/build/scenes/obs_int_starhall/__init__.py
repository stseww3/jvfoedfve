"""Test scene for the star hall package: versions a and b side by side in stand-in box shells.

A placeholder scene: the box shell stands in for the main-building line's (c178) real shell, and
mood.py stands in for A2's observatory look. When S2 moves the room into the merged scene it drops
the box and uses A3's shell and A2's biome; build_starhall itself does not change.
"""
from artkit.canvas import Canvas

from scenes.obs.interiors import shell, starhall

BIOME = "obs_int"
GAP = 10                                  # air between the two boxes


def build():
    c = Canvas()
    room = shell.STARHALL
    a = starhall.build_starhall(c, (0, 0, 0), version="a")
    b = starhall.build_starhall(c, (room.w + GAP, 0, 0), version="b")
    # realise the suggested invisible light sources, but only in empty cells so lamp fixtures and
    # walls are left intact (A2 owns lighting in the master scene; here it is just for self-check)
    for x, y, z, level in a["lights"] + b["lights"]:
        if not c.has(x, y, z):
            c.set(x, y, z, f"light[level={level}]")
    return c


def write_pack(pack_dir):
    """No repainted blocks or custom sky of our own: the stand-in sky is in mood.py, the blocks are
    occupancy-table vanilla blocks that A1 repaints on its own branch."""
    return []
