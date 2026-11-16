"""Test scene of props/plaques for the site: the master scene as it stands in this tree, with the
plaques hung (plaques.dress) whatever the master scene's switch GUIDE says.

Every line is built whole, in the master scene's order. A plaque hangs only where the cell behind
its middle stands (plaques.site): what was left out is listed by
python -m scenes.obs_props_plaques_site --report  (a node's job: it builds the master scene),
with the plaques that hang in the open air before a camera of the board, nearer than the
distance they are drawn from.

One camera a plaque, 2.6 blocks before it at the height of the eye: where the real client's
picture of its words is taken from. The offline renderer draws no text display, so the kept
pictures show the wall the plaque hangs on and what stands round it.
"""
import importlib
import math

from artkit.canvas import Canvas

from scenes import obs
from scenes.obs.common import skeleton as S
from scenes.obs.props import _kit as K
from scenes.obs.props import plaques

BIOME = obs.BIOME
BIOME_MARGIN = obs.BIOME_MARGIN
BIOME_MARGIN_Y = obs.BIOME_MARGIN_Y

build_models = obs.build_models
write_pack = obs.write_pack

TIME = 14000
BEFORE = 2.6                    # blocks from a plaque to the camera that reads it
BOARD = [name for name in (f"V{i}" for i in range(1, 13)) if hasattr(S, name)]
REACH = plaques.VIEW * 64.0     # blocks a plaque is drawn from, at the game's own entity distance


def build():
    c = Canvas()
    plaques.dress(c)
    counts = {}
    for name in obs.LINES:
        line = importlib.import_module(f"scenes.obs.{name}")
        counts[name] = int(line.build(c, obs.ORIGIN) or 0)
    c.entity_counts = counts
    return c


def _yaw(spec):
    return K.FACING[spec.get("facing", "south")] if spec.get("yaw") is None else float(spec["yaw"])


def shots():
    """A camera before every plaque of the tables; the arrival view alone while there is none."""
    out = []
    for key, spec in plaques.site_plaques().items():
        x, y, z = spec["pos"]
        dx, _, dz = K.turn(_yaw(spec), (0.3, 0.0, BEFORE))
        out.append({"name": key, "pos": [round(x + dx, 2), round(y + 0.1, 2), round(z + dz, 2)],
                    "look_at": [round(float(x), 2), round(float(y), 2), round(float(z), 2)], "time": TIME})
    if not out:
        out.append({"name": "v1", "pos": list(S.V1["pos"]), "look_at": list(S.V1["look_at"]), "time": TIME})
    return out


def in_board():
    """The plaques a camera of the board could show: [(key, view, blocks from the camera)] for every
    plaque nearer to a locked camera than it is drawn from, on the side it is read from."""
    out = []
    for key, spec in plaques.site_plaques().items():
        reach = 64.0 * spec.get("view", plaques.VIEW)
        front = K.turn(_yaw(spec), (0.0, 0.0, 1.0))
        for view in BOARD:
            eye = getattr(S, view)["pos"]
            to = tuple(e - p for e, p in zip(eye, spec["pos"]))
            far = math.sqrt(sum(v * v for v in to))
            if far < reach and sum(a * b for a, b in zip(to, front)) > 0.0:
                out.append((key, view, far))
    return out
