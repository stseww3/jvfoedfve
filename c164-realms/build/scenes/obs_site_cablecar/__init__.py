"""Test scene of the work package site/cablecar (plan/packages/site/cablecar.md): the cable station
on the lower platform and the trestle that takes its track down into the cloud.

The hill as it stands in the master scene: the site line whole, the main building above it, the
machines (the car and the winch in the station are theirs), the props line and the sky line's light
last. The lines are built whole, in the master scene's order, so the pictures keep up with them as
their packages are merged. The station's lamp and its furniture belong to the props line, which
keeps what it sets out on the site switched off in the master scene for now; here they are asked
for (_dress).

Two stand-ins, in this scene only, for what is still on other branches: the east flank of the
mountain with the ridge the trestle stands on (site/terrain's second draft; the ridge by the figures
of site/_kit.py) and a sheet of cloud round its foot (sky/cloudsea). They fill empty cells only, and
go when the real ones are merged.

The views (shots(); python -m scenes.obs_site_cablecar writes them to shots.json): V1 as the
skeleton fixes it (the station keeps the building's part of it and the comet's clear, and only the
waiting room stands in it, as its right edge), the platform from its south-west corner and back
along the axis line, the station from the lower platform and from the head of the grand stair, the
glass roof's truss and its girder from below, the trestle from the lower platform's edge, from the
side and looking back up it, and two from above.
"""
import importlib

from artkit.canvas import Canvas, Mix

from scenes.obs import machines, main, materials, props, site, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.site import _kit as K

BIOME = "obs_blue"
BIOME_MARGIN = 100
BIOME_MARGIN_Y = 150
LINES = (site, main, machines, props, sky)

ROCK = Mix({B.TUFF.block: 5, B.ROCK_ANDESITE.block: 3, B.ROCK_COBBLED.block: 2, B.ROCK_DEEPSLATE: 3}, seed=226)
CLOUD = Mix({B.CLOUD[1]: 2, B.CLOUD[2]: 3, B.CLOUD[3]: 2}, seed=227)
CLOUD_Y = (-27, -26)            # the block cloud's two courses; its top face is at y -25
FLANK = (61, -62, 112, -18)     # where the stand-in mountain is drawn
SEA = (61, -96, 176, -10)       # where the stand-in cloud is drawn

TIME = 14000
# The arrival view is the skeleton's. It looks up at (8, 34, 0.5) since A0 #304; a tree whose
# skeleton does not carry that figure yet gets it here.
V1 = S.V1 if hasattr(S, "V1_CLEAR") else dict(pos=S.V1["pos"], look_at=(8, 34, 0.5))
EYE = S.EYE
STAIR_X = S.GRAND_STAIR["x0"]   # 61: the grand stair's top step
VIEWS = [
    ("v1", V1["pos"], V1["look_at"]),
    # the whole station from the corner where its two flights of steps meet, and back along the
    # axis line from the head of the west steps: who walks back to the car
    ("platform", (77.5, S.STATION_GROUND + EYE, -28.5), (88.5, -0.5, -35.5)),
    ("axis", (80.5, S.STATION_GROUND + EYE, -32.5), (92.0, 0.0, -33.5)),
    # from the lower platform, and from the head of the grand stair on the upper terrace: its top
    # step on the axis, clear of the newel posts on the stair's cheeks
    ("lower", (70.5, S.LOWER_GROUND + EYE, -20.5), (86.0, -1.0, -35.0)),
    ("stair_head", (STAIR_X + 0.5, S.stair_top(STAIR_X) + EYE, 0.5), (86.0, -2.0, -33.0)),
    # up into the glass roof: the west truss from the open platform, and the south girder on its
    # two columns from the bay
    ("canopy", (86.5, S.STATION_GROUND + EYE, -30.5), (90.0, 1.8, -33.0)),
    ("girder", (88.5, S.STATION_GROUND + EYE, -27.5), (89.5, 1.5, -33.0)),
    # the trestle: from the east edge of the lower platform, from the side over the cloud, and back
    # up it from the second tower
    ("trestle", (90.5, S.LOWER_GROUND + EYE, -14.5), (112.0, -13.0, -38.0)),
    ("trestle_side", (112.0, -6.0, -14.0), (112.0, -16.0, -40.0)),
    ("east", (104.5, -8.5 + EYE, -36.5), (91.0, -1.0, -34.0)),
    # from above: over the cloud to the south-east, and over the lower platform to the west
    ("aerial", (114.0, 26.0, -2.0), (94.0, -8.0, -36.0)),
    ("aerial_west", (64.0, 14.0, -12.0), (86.0, -4.0, -34.0)),
]


def shots(names=None):
    """The shot list, or the views of it that are named."""
    return [{"name": name, "pos": [round(float(v), 2) for v in pos],
             "look_at": [round(float(v), 2) for v in look_at], "time": TIME}
            for name, pos, look_at in VIEWS if names is None or name in names]


def _crust(c, x, z, top, thick=3):
    for y in range(top, max(top - thick, K.ROCK_FLOOR) - 1, -1):
        c.set(x, y, z, ROCK, keep=True)


def _standins(c):
    lx0, lz0, lx1, lz1 = S.LOWER_PLATFORM
    for x in range(FLANK[0], FLANK[2] + 1):             # the slope below the lower platform's edges
        for z in range(FLANK[1], FLANK[3] + 1):
            d = max(lx0 - x, x - lx1, lz0 - z, z - lz1)
            if d > 0:
                top = int(round(S.LOWER_PAVING_Y - 1 - 1.6 * (d - 1)))
                if top >= K.ROCK_FLOOR:
                    _crust(c, x, z, top)
    for x in range(K.CABLE_RIDGE_X[0], K.CABLE_RIDGE_X[1] + 1):     # the ridge, falling two in one each side
        z, y = K.cable_ridge(x)
        for k in range(0, 14):
            top = y - 2 * max(0, k - 1)
            if top < K.ROCK_FLOOR:
                break
            for zz in {z - k, z + k}:
                _crust(c, x, zz, top)
    for x in range(SEA[0], SEA[2] + 1):
        for z in range(SEA[1], SEA[3] + 1):
            for y in CLOUD_Y:
                c.set(x, y, z, CLOUD, keep=True)


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
    """What the props line sets out on the station, both under the group "station": the pendant
    under the glass roof (props/lamps, on site/cablecar.LAMP_POINTS), the two benches and the
    luggage against the waiting room (props/furniture, on BENCHES and LUGGAGE). Called after the
    props line and before the sky line, which lays the lamps' light. A tree whose props line does
    not set them out yet has none."""
    for name in ("lamps", "furniture"):
        set_out = getattr(_prop(name), "site", None)
        if set_out is not None:
            set_out(c, (0, 0, 0), groups=("station",))


def build():
    c = Canvas()
    for line in LINES:
        line.build(c, (0, 0, 0))
        if line is site:
            _standins(c)
        if line is props:
            _dress(c)
    return c


def build_models():
    """The models of the lines that are built here, and the materials line's: the sheets on the room
    side of the winch house's two lights are its models (materials/windows.line)."""
    out = {}
    for line in (materials,) + LINES:
        out.update(line.models() or {})
    return out


def write_pack(pack_dir):
    """The station paints nothing itself; it stands on the repainted blocks as the materials line
    has them today (cast iron, the roof light, the lit and dark windows)."""
    return materials.pack(pack_dir)
