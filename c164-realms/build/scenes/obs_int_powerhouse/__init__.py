"""obs_int_powerhouse: the test scene of the power house's inside (work package interiors/powerhouse).

The room stands in its real shell: the site line builds the lower platform and the power house
(site/powerhouse, the fire windows glowing, as the card wants the house judged), the machines line
what it has, then the room is dressed by scenes.obs.interiors.powerhouse, the call the master scene
makes, then the props and the sky line follow as in the master scene. A machine of the room whose
module is not in the tree yet has a plain stand-in (standins.py), so the room is judged with
something where the engine, the boilers and the switchboard will stand.

The cameras are in VIEWS; `python -m scenes.obs_int_powerhouse` writes shots.json from them.
"""
import contextlib

from artkit.canvas import Canvas

from scenes.obs import machines, main, materials, props, site, sky
from scenes.obs.common import skeleton as S
from scenes.obs.interiors import powerhouse as room
from scenes.obs.site import powerhouse as shell

from . import standins

BIOME = "obs_blue"
CATEGORY = "interiors"
LINES = (site, main, machines, props, sky)
TIME = 14000
EYE = room.FEET + S.EYE                 # -4.38: the eye of somebody on the room's floor

# name, the eye, what it looks at
VIEWS = [
    ("int_power", (74.5, EYE, 22.7), (78.3, -4.3, 33.0)),               # in at the wicket: the engine ahead, the fires left
    ("int_switchboard", (76.5, EYE, 29.5), (70.5, -3.4, 29.5)),         # the board, full face
    ("int_walkway", (86.5, EYE, 32.5), (74.0, -4.6, 33.4)),             # along the gangway from its east end
    ("door_in", (74.5, EYE, 24.5), (74.5, -4.0, 36.0)),                 # two steps in, straight down the walk
    ("fires", (75.5, EYE, 30.5), (80.5, -4.4, 25.5)),                   # the stoker's place and the two fire doors
    ("engine_east", (86.5, EYE, 38.5), (78.0, -4.4, 35.8)),             # the engine from its far end
    ("belt", (74.6, EYE, 39.3), (76.0, -4.6, 35.5)),                    # the belt, the wheel and the crank from the south-west
    ("dynamo", (74.4, EYE, 33.6), (71.6, -4.2, 37.6)),                  # the dynamo, its terminals and the cables
    ("desk", (72.6, EYE, 25.4), (69.4, -5.0, 22.8)),                    # the engineer's corner
    ("deck_down", (78.5, EYE, 31.3), (80.5, -8.2, 32.9)),               # down through the grating into the trench
    ("roof_up", (78.5, EYE, 30.5), (79.5, 4.0, 33.5)),                  # up: the main, its hangers, the girders, the dark roof
    ("south_west", (69.7, EYE, 39.6), (80.0, -3.6, 28.0)),              # the whole works from the far corner
    ("v6_wicket", S.V6["pos"], S.V6["look_at"]),                        # the locked view: what the open wicket shows
    ("court_roof", (58.5, S.GROUND + S.EYE, 12.5), (80.0, 5.0, 30.0)),  # from the court's lip: the roof lights stay dark
    ("from_above", (70.2, 2.6, 23.2), (81.0, -6.0, 34.0)),              # from under the eaves in the north-west corner: the plan
]


def shots():
    return [{"name": name, "pos": [round(float(v), 2) for v in pos],
             "look_at": [round(float(v), 2) for v in look_at], "time": TIME}
            for name, pos, look_at in VIEWS]


@contextlib.contextmanager
def _lit_fires():
    was = shell.FIRE
    shell.FIRE = True
    try:
        yield
    finally:
        shell.FIRE = was


def build():
    c = Canvas()
    with _lit_fires():
        for line in LINES:
            if line is props:           # the rooms come after the machines and before the props
                standins.build(c)
                room.build_powerhouse(c, machines=standins.ALL)
            if line is sky:             # the materials line is not built here: the fire windows' room side
                shell.lining(c)
            line.build(c, (0, 0, 0))
    return c


def build_models():
    out = {}
    for line in LINES:
        out.update(line.models() or {})
    out.update(room.models())
    out.update(room.their_models())
    out.update(standins.models())
    try:
        from scenes.obs.materials import windows
    except ImportError:
        windows = None
    if getattr(windows, "line", None) is not None:
        out.update(windows.models())    # the linings of the fire windows (site/powerhouse.lining)
    return out


def write_pack(pack_dir):
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
