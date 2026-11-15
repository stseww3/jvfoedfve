"""The models of the props/paper test scene: the paper family, the lamps that light the corner, and
the stand-in light table the glass negatives lie on."""
import functools

from artkit import models as M

from scenes.obs.common import palette as P
from scenes.obs.props import lamps, paper

TABLE = "prop_paper_stage_table"
SCALE = {**lamps.SCALE, **paper.SCALE, TABLE: 1.0}


@functools.lru_cache(maxsize=None)
def table():
    """A stand-in for the chart room's light table, three blocks by one and a half and a block
    high: a dark wood case on four legs, its top a pane of opal glass lit from inside, drawn in the
    material the real pane has. Anchor: the middle of its foot."""
    wood, pane = P.mat("dark_wood"), P.mat("opal")
    m = M.Model(TABLE)
    w, d, h, rim = 24.0, 12.0, 16.0, 1.5
    for x in (-w, w - 2.0):
        for z in (-d, d - 2.0):
            m.box((x, 0, z), (x + 2.0, h - 6.0, z + 2.0), wood, grain="y", skip="du")
    m.box((-w, h - 6.0, -d), (w, h - 0.5, d), wood, grain="x")
    for z in (-d, d - rim):
        m.box((-w, h - 0.5, z), (w, h, z + rim), wood, grain="x", skip="d")
    for x in (-w, w - rim):
        m.box((x, h - 0.5, -d + rim), (x + rim, h, d - rim), wood, grain="y", skip="d")
    m.box((-w + rim, h - 0.5, -d + rim), (w - rim, h, d - rim), pane, skip="d", emit=15, shade=False)
    return m


def build_models():
    return {**lamps.models(), **paper.models(), TABLE: table()}
