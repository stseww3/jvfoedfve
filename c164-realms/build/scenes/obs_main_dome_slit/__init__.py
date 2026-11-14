"""Test scene of the work package main/dome: the slit of both versions shut, half open and open
(plan/packages/main/dome.md).

Six rotundas stand in a row from north to south, each from the rotunda's cornice up (the drum's
first course on the paving) and with its slit to the west, where the cameras stand: version a
shut, half open and open, then version b the same. In the master scene and in obs_main_dome and
obs_main_dome_b the slit is open.

The shots are written by python -m scenes.obs_main_dome.
"""
from artkit.canvas import Canvas

from scenes.obs import materials
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.main import _dome as D
from scenes.obs.main import _order as O
from scenes.obs.main import dome

BIOME = "obs_blue"
BIOME_MARGIN = 64
BIOME_MARGIN_Y = 96
PAVING = B.TUFF_SMOOTH.block
PITCH = 40                              # from one rotunda's centre to the next
STAGE = tuple((version, state) for version in D.VERSIONS for state in ("closed", "half", "open"))
LIFT = 1 - D.ATTIC                      # the attic course stands on the paving
TIME = 14000                            # light version A, the default (INTERFACE: 18000 is B, 12900 is C)


def origin(i):
    """Where the i-th rotunda's scene origin lies."""
    return 0, LIFT, (2 * i - len(STAGE) + 1) * PITCH // 2


def build():
    c = Canvas()
    cx, cz = S.DOME_CENTRE
    for i, (version, state) in enumerate(STAGE):
        ox, oy, oz = origin(i)
        for x, z in O.disc(cx, cz, D.R + 6):
            c.set(ox + x, 0, oz + z, PAVING)
        dome.build(c, (ox, oy, oz), version=version, slit=state)
    return c


def write_pack(pack_dir):
    """The repainted blocks the shell stands in, as the materials line has them today."""
    return materials.pack(pack_dir)


def shots():
    """Each rotunda's slit from where obs_main_dome's shot "slit" looks at it; each version's three
    in one picture, from the west and from above."""
    cx, cz = S.DOME_CENTRE
    out = []

    def shot(name, at, pos, look_at):
        out.append({"name": name, "pos": [round(a + v, 2) for a, v in zip(at, pos)],
                    "look_at": [round(a + v, 2) for a, v in zip(at, look_at)], "time": TIME})

    for i, (version, state) in enumerate(STAGE):
        shot(f"{version}_{state}", origin(i), (cx - 22.0, 33.0, cz + 7.0), (cx - 7.0, 30.0, cz))
    for version in D.VERSIONS:
        middle = origin(STAGE.index((version, "half")))
        shot(f"{version}_row", middle, (cx - 58.0, 30.0, cz + 0.5), (cx, 27.0, cz + 0.5))
        shot(f"{version}_top", middle, (cx - 30.0, 80.0, cz + 0.5), (cx - 2.0, 30.0, cz + 0.5))
    return out
