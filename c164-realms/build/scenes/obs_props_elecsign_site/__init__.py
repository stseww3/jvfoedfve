"""Test scene of the work package props/electrics-signs for the whole site: the master scene as it
stands in this tree, every line built whole and in the master scene's order, looked at where the
package hangs something in it (signs.build, switch signs.DRESS):

  the great emblem   on the tablet main/facade keeps for it over the entrance;
  the name board     on the gable of the cable station's waiting room, on the seat site/cablecar
                     keeps for it (SIGN).

Nothing is placed here: what the pictures show is what the map has. A piece whose seat is not in
the tree is not hung, and the shot that looks for it is left out, so the scene keeps up with the
site as its packages are merged.  python -m scenes.obs_props_elecsign_site  lists what hangs and
writes shots.json.
"""
import importlib

from artkit.canvas import Canvas

from scenes import obs
from scenes.obs.common import skeleton as S
from scenes.obs.props import signs

try:
    from scenes.obs.sky import _lightkit as L
except ImportError:         # the sky line's light tool is not in the tree
    L = None

BIOME = obs.BIOME
BIOME_MARGIN = obs.BIOME_MARGIN
BIOME_MARGIN_Y = obs.BIOME_MARGIN_Y
BLUE, DEEP = 14000, 18000       # the blue hour (the default look) and deep night

build_models = obs.build_models
write_pack = obs.write_pack


def build():
    c = Canvas()
    if L is not None:
        L.dress(c)              # the building shows its own lights: the pieces are judged against the lit map
    counts = {}
    for name in obs.LINES:
        line = importlib.import_module(f"scenes.obs.{name}")
        counts[name] = int(line.build(c, obs.ORIGIN) or 0)
    c.entity_counts = counts
    return c


def hung(canvas):
    """The package's display entities on the canvas: [(model's name, (x, y, z)), ...]."""
    out = []
    for x, y, z, nbt in canvas.entities:
        name = nbt["item"]["components"]["minecraft:item_model"].split(":")[-1]
        if name.startswith(("prop_sign_", "prop_elec_")):
            out.append((name, (x, y, z)))
    return out


# ---- the cameras ---------------------------------------------------------------------------------
def shots():
    """The director's view of the front under both times and the emblem from the court below it;
    the station's gable from its own platform under both times, from an arm's length and from
    the lower platform, where the way to the stair leaves it."""
    out = []

    def shot(name, pos, look_at, time=BLUE):
        out.append({"name": name, "pos": [round(float(v), 2) for v in pos],
                    "look_at": [round(float(v), 2) for v in look_at], "time": time})

    seat = signs._seat()
    if seat is not None:
        v2 = S.V2
        ex, ey, ez = seat["face_x"], seat["cells"][-1][1] + 0.5, seat["cells"][-1][2] + 0.5
        eye = S.GROUND + S.EYE
        shot("v2", v2["pos"], v2["look_at"])
        shot("v2_deep", v2["pos"], v2["look_at"], DEEP)
        shot("emblem_court", (ex + 20.0, eye, ez), (ex, ey - 3.5, ez))
        shot("emblem_near", (ex + 7.0, eye, ez + 3.0), (ex, ey, ez))
    board = signs._station_seat()
    if board is not None and board["facing"] == "west":
        bx, by, bz = board["point"]
        feet, low = S.STATION_GROUND + S.EYE, S.LOWER_GROUND + S.EYE
        edge = S.CABLE_STATION[0] + 0.6
        shot("board_near", (bx - 2.5, feet, bz + 0.6), (bx, by - 0.1, bz))
        shot("board_gable", (edge, feet, bz + 1.6), (bx, by - 0.7, bz - 0.2))
        shot("board_gable_deep", (edge, feet, bz + 1.6), (bx, by - 0.7, bz - 0.2), DEEP)
        shot("board_way", (bx - 10.0, low, bz + 2.5), (bx, by - 0.9, bz + 0.3))
    return out
