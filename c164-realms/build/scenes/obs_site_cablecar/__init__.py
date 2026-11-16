"""Test scene of the work package site/cablecar (plan/packages/site/cablecar.md): the cable station
on the lower platform and the trestle that takes its track down into the cloud.

The hill as it stands in the master scene: the site line whole, the main building above it, the
machines (the car and the winch in the station are theirs), the props line and the sky line's light
last. The lines are built whole, in the master scene's order, so the pictures keep up with them as
their packages are merged. The station's lamp and its furniture belong to the props line. The
lamp hangs in the master scene, with the other lamps of the site; the furniture, which the line
keeps switched off there for now, is asked for here (_dress). The sea of cloud the track goes
down into is the sky line's (sky/cloudsea); nothing in this scene stands in for anything.

The views (shots(); python -m scenes.obs_site_cablecar writes them to shots.json): V1 as the
skeleton fixes it (the station keeps the building's part of it and the comet's clear, and only the
waiting room stands in it, as its right edge), the platform from its south-west corner and back
along the axis line, the station from the lower platform and from the head of the grand stair, the
glass roof's truss and its girder from below, the trestle from the lower platform's edge, from the
side and looking back up it, and two from above.
"""
import importlib

from artkit.canvas import Canvas

from scenes.obs import machines, main, materials, props, site, sky
from scenes.obs.common import skeleton as S
from scenes.obs.site import cablecar

BIOME = "obs_blue"
BIOME_MARGIN = 100
BIOME_MARGIN_Y = 150
LINES = (site, main, machines, props, sky)

TIME = 14000
# The arrival view is the skeleton's. It looks up at (8, 34, 0.5) since A0 #304; a tree whose
# skeleton does not carry that figure yet gets it here.
V1 = S.V1 if hasattr(S, "V1_CLEAR") else dict(pos=S.V1["pos"], look_at=(8, 34, 0.5))
EYE = S.EYE
VIEWS = [
    ("v1", V1["pos"], V1["look_at"]),
    # the whole station from the corner where its two flights of steps meet, and back along the
    # axis line from the head of the west steps: who walks back to the car
    ("platform", (77.5, S.STATION_GROUND + EYE, -28.5), (88.5, -0.5, -35.5)),
    ("axis", (80.5, S.STATION_GROUND + EYE, -32.5), (92.0, 0.0, -33.5)),
    # from the lower platform, and from the head of the grand stair: on the upper terrace's lip, on
    # the axis, in the opening the railing leaves for the stair
    ("lower", (70.5, S.LOWER_GROUND + EYE, -20.5), (86.0, -1.0, -35.0)),
    ("stair_head", (S.EAST_EDGE_X + 0.5, S.GROUND + EYE, 0.5), (86.0, -2.0, -33.0)),
    # up into the glass roof: the west truss from the open platform, and the south girder on its
    # two columns from the bay
    ("canopy", (86.5, S.STATION_GROUND + EYE, -30.5), (90.0, 1.8, -33.0)),
    ("girder", (88.5, S.STATION_GROUND + EYE, -27.5), (89.5, 1.5, -33.0)),
    # the trestle: from the east edge of the lower platform, from the side over the cloud, and back
    # up it from the second tower. The first stands at the platform's railing, at the south end of a
    # bay: from there the bay's north pier hides the station's foot and the first cells of the track,
    # and the whole descent lies clear of it (from the middle of a bay the pier stands before the
    # track; from the station's own look-out the track runs straight away from the eye)
    ("trestle", (91.1, S.LOWER_GROUND + EYE, -18.3), (110.4, -8.6, -41.3)),
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
    """What the props line sets out on the station and keeps switched off in the master scene: the
    two benches and the luggage against the waiting room (props/furniture, its group "station", on
    BENCHES and LUGGAGE). Asked for here, after the props line; a piece that stands already is not
    set out twice, and a tree without the furniture has none. The pendant under the glass roof
    (props/lamps, on LAMP_POINTS) is one of the site's lamps: the props line hangs it itself."""
    set_out = getattr(_prop("furniture"), "site", None)
    if set_out is not None:
        set_out(c, (0, 0, 0), groups=("station",))


def build():
    c = Canvas()
    for line in LINES:
        line.build(c, (0, 0, 0))
        if line is site:
            cablecar.lining(c)      # the materials line is not built here: the room side of the winch
            #                         house's two lights (it places them in the master scene)
        if line is props:
            _dress(c)
    return c


def build_models():
    """The models of the lines that are built here, and the materials line's: the sheets on the room
    side of the winch house's two lights are its models (materials/windows.line), which this scene
    asks for with cablecar.lining()."""
    out = {}
    for line in (materials,) + LINES:
        out.update(line.models() or {})
    return out


def write_pack(pack_dir):
    """The station paints nothing itself; it stands on the repainted blocks as the materials line
    has them today (cast iron, the roof light, the lit and dark windows), under the map's sky: the
    scene keeps the map's hour (mood.py), and V1 looks west over an open horizon, where the game's
    own sun would lie without the sky's pictures."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
