"""Test scene of the work package site/cablecar (plan/packages/site/cablecar.md): the cable station
on the lower platform and the trestle that takes its track down into the cloud.

The hill as it stands in the master scene: the site line whole, the main building above it, the
machines (the car and the winch in the station are theirs), the props line and the sky line's light
last. The lines are built whole, in the master scene's order, so the pictures keep up with them as
their packages are merged. The station's lamp and its furniture belong to the props line. The
lamp hangs in the master scene, with the other lamps of the site; the furniture, which the line
keeps switched off there for now, is asked for here (_dress).

One stand-in, in this scene only, for what is still on another branch: the sea of cloud beyond the
ring that site/terrain lays round the mountain's foot (sky/cloudsea takes both over). The ring ends
at x 129 on the track's line and the track goes on down to x 141. The sheet fills empty cells
only, in the ring's courses and tones, and goes when the real sea is merged.

The views (shots(); python -m scenes.obs_site_cablecar writes them to shots.json): V1 as the
skeleton fixes it (the station keeps the building's part of it and the comet's clear, and only the
waiting room stands in it, as its right edge), the platform from its south-west corner and back
along the axis line, the station from the lower platform and from the head of the grand stair, the
glass roof's truss and its girder from below, the trestle from the lower platform's edge, from the
side and looking back up it, and two from above.
"""
import importlib

import numpy as np

from artkit import noise as N
from artkit.canvas import Canvas

from scenes.obs import machines, main, materials, props, site, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.site import terrain

BIOME = "obs_blue"
BIOME_MARGIN = 100
BIOME_MARGIN_Y = 150
LINES = (site, main, machines, props, sky)

SEA = (61, -120, 200, 24)       # where the stand-in sea is drawn: east and north of the lower platform
# the ring's own figures (site/terrain._cloud_sea, east of its middle), so that no seam shows where
# the sheet takes over from it
SEA_NOISE = dict(scale=0.08, seed=terrain.SEED + 20, octaves=2, lift=0.55)

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
    # up it from the second tower. The first stands at the platform's railing in the bay next to the
    # station's foot: from any bay further south the next pier of the railing hides the track.
    ("trestle", (91.1, S.LOWER_GROUND + EYE, -23.5), (112.0, -12.5, -39.7)),
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


def _standins(c):
    """The sheet of cloud over SEA, in the empty cells of the ring's three courses."""
    xs = np.arange(SEA[0], SEA[2] + 1)
    zs = np.arange(SEA[1], SEA[3] + 1)
    X, Z = np.meshgrid(xs.astype(float), zs.astype(float), indexing="ij")
    k = SEA_NOISE
    n = N.fbm2(X * k["scale"], Z * k["scale"], k["seed"], octaves=k["octaves"])
    tone = np.rint(np.clip(0.5 + 0.5 * n + 0.6 * (k["lift"] - 0.75), 0.0, 1.0) * (len(B.CLOUD) - 1)).astype(int)
    for i, x in enumerate(xs):
        for j, z in enumerate(zs):
            rock = terrain.top(int(x), int(z))
            if rock is None or rock < terrain.CLOUD_TOP:        # the ring's rule: not where the mountain stands out
                for y in range(terrain.CLOUD_TOP, terrain.CLOUD_BOTTOM - 1, -1):
                    c.set(int(x), y, int(z), B.CLOUD[tone[i, j]], keep=True)


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
    has them today (cast iron, the roof light, the lit and dark windows), under the map's sky: the
    scene keeps the map's hour (mood.py), and V1 looks west over an open horizon, where the game's
    own sun would lie without the sky's pictures."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
