"""Test scene of the work package motion/guide-title (plan/packages/motion/guide.md, part one): the
cable station as it stands in the master scene, with the three functions of the arrival title in
its data pack and the credit plate on the waiting room's front.

The hill is built as scenes/obs_site_cablecar builds it: the site line whole, the main building,
the machines, the props line (with the station's furniture, which that line keeps switched off in
the master scene for now) and the sky line's light, in the master scene's order; then this
package by itself, not the motion line whole. Nothing stands in for anything.

What the pictures can and cannot show. Neither the title nor the plate is in them: a title is
drawn on the player's screen, and the offline renderer leaves text displays out (it says how
many at its end). The pictures show the wall the plate hangs on, from where a visitor sees it,
and the arrival view, which is to stay as it was. What the title and the plate look like is seen
in the game: tools/export.py's verify counts the title's packets, and the render station walks
the save with a real client.

The views (shots(); python -m scenes.obs_mot_guide_title writes them to shots.json, and says where
the plate falls in the arrival view):
    v1         the arrival view, as the skeleton fixes it
    from_car   from the spawn, turned to the plate: what who steps out of the car has on his right
    plate      square on, from two and a half blocks: the pier between the door and the east window,
               the luggage at its foot
    front      the waiting room's whole front from the south-west, as who comes back to the car
               sees it
"""
import importlib
import math

from artkit.canvas import Canvas

from scenes.obs import machines, main, materials, props, site, sky
from scenes.obs.common import skeleton as S
from scenes.obs.motion import guide_title
from scenes.obs.site import cablecar

BIOME = "obs_blue"
BIOME_MARGIN = 100
BIOME_MARGIN_Y = 150
LINES = (site, main, machines, props, sky)

TIME = 14000
FOV, ASPECT = 77.0, 16.0 / 9.0  # the game's picture, as tools/boardshots.py has it
EYE = S.EYE
PLATE = guide_title.plate_at()[0]           # the middle of the plate, on the wall's face
VIEWS = [
    ("v1", S.V1["pos"], S.V1["look_at"]),
    ("from_car", (cablecar.SPAWN[0], cablecar.SPAWN[1] + EYE, cablecar.SPAWN[2]), PLATE),
    ("plate", (PLATE[0], S.STATION_GROUND + EYE, PLATE[2] + 2.5), PLATE),
    ("front", (79.5, S.STATION_GROUND + EYE, -31.5), (84.0, -2.2, -36.5)),
]


def shots(names=None):
    """The shot list, or the views of it that are named."""
    return [{"name": name, "pos": [round(float(v), 2) for v in pos],
             "look_at": [round(float(v), 2) for v in look_at], "time": TIME}
            for name, pos, look_at in VIEWS if names is None or name in names]


def where(view, point):
    """Where `point` falls in the picture of `view`: (x, y), each from -1 at the left or bottom
    edge to 1 at the right or top edge, or None when the point is behind the camera."""
    pos, to = view["pos"], view["look_at"]
    f = [to[i] - pos[i] for i in range(3)]
    n = math.sqrt(sum(v * v for v in f))
    f = [v / n for v in f]
    r = [-f[2], 0.0, f[0]]
    n = math.hypot(r[0], r[2])
    r = [v / n for v in r]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    d = [point[i] - pos[i] for i in range(3)]
    depth = sum(d[i] * f[i] for i in range(3))
    if depth <= 0.0:
        return None
    half = math.tan(math.radians(FOV / 2.0))
    return (sum(d[i] * r[i] for i in range(3)) / depth / (half * ASPECT),
            sum(d[i] * u[i] for i in range(3)) / depth / half)


def plate_corners():
    """The four corners of the plate (props/plaques.corners), or of a plate of the size the card
    gives in a tree without the props line's plaques."""
    full = f"{props.__name__}.plaques"
    try:
        return importlib.import_module(full).corners(PLATE, guide_title.plate_at()[1])
    except ModuleNotFoundError as e:
        if e.name != full:
            raise
    return [(PLATE[0] + dx, PLATE[1] + dy, PLATE[2] + 0.01) for dx, dy in
            ((-0.46, -0.135), (0.46, -0.135), (0.46, 0.135), (-0.46, 0.135))]


def _prop(name):
    """A package of the props line; None while it is not in the tree."""
    full = f"{props.__name__}.{name}"
    try:
        return importlib.import_module(full)
    except ModuleNotFoundError as e:
        if e.name != full:
            raise               # it is there and fails to import something: say so
        return None


def _dress(c):
    """The two benches and the luggage against the waiting room (props/furniture, its group
    "station"), which the props line keeps switched off in the master scene for now: the luggage
    stands at the foot of the plate's pier."""
    set_out = getattr(_prop("furniture"), "site", None)
    if set_out is not None:
        set_out(c, (0, 0, 0), groups=("station",))


def build():
    c = Canvas()
    counts = {}
    for line in LINES:
        if line is sky:         # the motion line's place in the master scene: before the sky
            counts["motion"] = int(guide_title.build(c, (0, 0, 0)) or 0)
        counts[line.__name__.rsplit(".", 1)[-1]] = int(line.build(c, (0, 0, 0)) or 0)
        if line is site:
            cablecar.lining(c)  # the materials line is not built here: the room side of the winch
            #                     house's two lights (it places them in the master scene)
        if line is props:
            _dress(c)
    c.entity_counts = counts
    return c


def build_models():
    """The models of the lines that are built here, and the materials line's (cablecar.lining()).
    The package has none of its own."""
    out = {}
    for line in (materials,) + LINES:
        out.update(line.models() or {})
    return out


def write_pack(pack_dir):
    """The package paints nothing: the scene stands on the repainted blocks, under the map's sky."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
