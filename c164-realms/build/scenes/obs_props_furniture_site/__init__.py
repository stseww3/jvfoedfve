"""Test scene of props/furniture for the site: the master scene as it stands in this tree, with the
furniture of the site switched on (furniture.dress), whatever the switch furniture.DRESS says.

Every line is built whole, in the master scene's order, so the pictures keep up with the site as
its packages are merged. A piece is only placed where its floor stands (furniture.site): in a tree
without site/cablecar the station has no bench and no luggage, without site/outbuildings the
lookout has no bench (furniture.floor_in_tree), and the cameras of a group are only written while
its package is in the tree (shots.json is written again when one of them is merged). What was left out is listed by
python -m scenes.obs_props_furniture_site --report  (a node's job: it builds the master scene).
Where the lamps of the site and the building's own lights can be asked for they are, so that the
benches are judged in the light they will stand in.

What the pictures are for:
  sunset    four benches on the sunset terrace, their backs to the building: do they follow the
            curve of the rail, do they stand on the bands of the paving, is the walk from the west
            door left free, does a pier of the rail stand in front of a sitter
  station   the door of the waiting room between a bench and somebody's luggage, the bench under
            the gable window, and what the arrival view (V1) keeps of them
  lookout   the bench before the east rail, and V11, which must not show it
The luggage itself is judged near by on the stage of obs_props_furniture.
"""
import importlib

from artkit.canvas import Canvas

from scenes import obs
from scenes.obs.common import skeleton as S
from scenes.obs.props import furniture, lamps

try:
    from scenes.obs.sky import _lightkit as L
except ImportError:         # the sky line's light tool is not in this tree
    L = None

BIOME = obs.BIOME
BIOME_MARGIN = obs.BIOME_MARGIN
BIOME_MARGIN_Y = obs.BIOME_MARGIN_Y

build_models = obs.build_models
write_pack = obs.write_pack

FLOORS = furniture.FLOORS
in_tree = furniture.floor_in_tree       # is the package that lays a group's floor in this tree?


def build():
    c = Canvas()
    furniture.dress(c)
    if hasattr(lamps, "dress"):
        lamps.dress(c)
    if L is not None:
        L.dress(c)
    counts = {}
    for name in obs.LINES:
        line = importlib.import_module(f"scenes.obs.{name}")
        counts[name] = int(line.build(c, obs.ORIGIN) or 0)
    c.entity_counts = counts
    return c


# ---- the cameras ---------------------------------------------------------------------------------
BLUE, SUNSET = 14000, 12900     # light version A (the default) and C
EYE = S.EYE


def _points(group):
    """The benches of a group and the first piece of its luggage, as [(kind, point)]."""
    return [(kind, p) for g, kind, p, _, foot in furniture.site_pieces() if g == group and p == foot]


def shots():
    out = []

    def shot(name, pos, look_at, time=BLUE):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": time})

    # the sunset terrace. Its benches stand in two pairs, mirrored in the axis of the west door.
    cx, cz = S.mid(S.SUNSET_PLATFORM["centre"][0]), S.mid(S.SUNSET_PLATFORM["centre"][1])
    r = S.SUNSET_PLATFORM["radius"]
    ground = float(S.GROUND)
    (inner_w, inner_off), (outer_w, outer_off) = furniture.SUNSET_BENCHES
    inner = (cx - inner_w, ground, cz + inner_off)          # the south bench of the pair at the walk
    outer = (cx - outer_w, ground, cz + outer_off)          # the south bench of the outer pair
    door = (cx - 2.0, ground + EYE, cz)                     # just out of the west door
    # out of the door: the walk between the two inner benches, the rail, the west beyond it
    shot("sunset_door", door, (cx - r, ground + 0.8, cz))
    shot("sunset_door_c", door, (cx - r, ground + 0.8, cz), SUNSET)
    # from the air west of the terrace, the stamp view: the row behind the rail, the west front behind the row
    shot("sunset_west", (cx - r - 9.0, ground + 6.0, cz), (cx - 6.0, ground + 2.0, cz))
    # along the row from its south end: do the four follow the curve
    shot("sunset_row", (outer[0] + 3.5, ground + EYE, outer[2] + 5.0), (inner[0] - 0.5, ground + 0.5, cz))
    # one bench near by, from the walk: slats and casting on the paving, the building behind
    # (clear of the tripod telescope that props/instruments stands on the axis between the inner pair)
    shot("sunset_bench", (inner[0] - 2.6, ground + 1.5, cz + 2.1), (inner[0], ground + 0.5, inner[2]))
    # what the sitter of an inner bench sees, and of an outer one: the rail and its piers
    shot("sunset_seat", (inner[0] - 0.3, ground + 1.15, inner[2]), (inner[0] - 12.0, ground + 0.6, inner[2]))
    shot("sunset_seat_outer", (outer[0] - 0.3, ground + 1.15, outer[2]), (outer[0] - 10.0, ground + 0.6, outer[2]))
    # from above: where the benches stand on the bands of the paving
    shot("sunset_plan", (cx - r - 3.0, ground + 17.0, cz), (cx - r + 9.0, ground, cz))

    if in_tree("station"):
        feet = float(S.STATION_GROUND)
        pieces = dict(_points("station"))
        benches = [p for kind, p in _points("station") if kind == "bench"]
        gable = min(benches, key=lambda p: p[2])            # the bench under the gable window, the northern one
        front = max(benches, key=lambda p: p[2])
        trunk = pieces["trunk"]
        mid_x = (front[0] + trunk[0]) / 2.0
        # the arrival view: what it keeps of the bench at the foot of the front
        shot("station_v1", S.V1["pos"], S.V1["look_at"])
        # the front of the waiting room: its door between the bench and the luggage
        shot("station_front", (mid_x + 1.5, feet + EYE, front[2] + 5.0), (mid_x, feet + 0.9, front[2]))
        shot("station_luggage", (trunk[0] + 1.7, feet + 1.5, trunk[2] + 2.1), (trunk[0] + 0.1, feet + 0.5, trunk[2]))
        shot("station_gable", (gable[0] - 3.2, feet + EYE, gable[2] + 2.6), (gable[0], feet + 0.5, gable[2]))

    if in_tree("lookout"):
        feet = float(S.SOUTH_LOOKOUT["feet"])
        bench = _points("lookout")[0][1]
        # from the walk in the middle of the lookout: the bench before the east rail
        shot("lookout_bench", (bench[0] - 3.9, feet + EYE, bench[2] - 1.2), (bench[0], feet + 0.5, bench[2]))
        # V11 is taken from here and looks north-west: the bench must stay behind its right edge
        shot("lookout_v11", S.V11["pos"], S.V11["look_at"])
    return out
