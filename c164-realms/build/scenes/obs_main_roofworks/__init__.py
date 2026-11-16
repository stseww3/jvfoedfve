"""Test scene of the work package main/roofworks (plan/packages/main/roofworks.md): the main
building with what stands on its roofs, under the map's sky.

Only the main line and the sky are built: the roofs' outline against the blue hour is what the
package is judged by, and the kept pictures change with the building alone. The mountain, the
court and the machines are left out, so the house stands in the air; the eyes of the board's
views are where the skeleton has them.

The shots are written from the skeleton's numbers and the package's:  python -m scenes.obs_main_roofworks
"""
from artkit.canvas import Canvas

from scenes.obs import main, materials, sky
from scenes.obs.common import skeleton as S
from scenes.obs.main import roof, roofworks
from scenes.obs.props import lamps

BIOME = "obs_blue"
BIOME_MARGIN = 80
BIOME_MARGIN_Y = 160
LINES = (main, sky)
TIME = 14000                    # the blue hour, the default look
NOON = 6000                     # for the shots that are to show how a thing is made


def build():
    c = Canvas()
    for line in LINES:
        line.build(c, (0, 0, 0))
    return c


def build_models():
    out = dict(lamps.models() or {})        # the sky line hangs the props line's lamps on the building's ways
    for line in LINES:
        out.update(line.models() or {})
    return out


def write_pack(pack_dir):
    """The package paints no block: it stands in the repainted blocks as the materials line has them
    today, under the sky's own pictures. Its models come with build_models()."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots():
    def shot(name, pos, look_at, time=TIME):
        return {"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at], "time": time}

    big = {(k["cell"][1] > 0): k for k in roofworks.cowls() if not k["size"]}           # False: north, True: south
    small = {(k["cell"][1] > 0): k for k in roofworks.cowls() if k["size"]}
    nx, _ny, nz = big[False]["at"]
    sx, _sy, sz = big[True]["at"]
    head = big[False]["top"] - 0.5
    ridge = roof.RIDGE[1] + 0.5
    eye = roof.RIDGE_TOP + 1.62
    return [
        # the board's views the roofs are seen in: the court's axis, the tower's own view, the
        # arrival, the south lookout and the far one from the north-east
        shot("v2", S.V2["pos"], S.V2["look_at"]),
        shot("v5", S.V5["pos"], S.V5["look_at"]),
        shot("v1", S.V1["pos"], S.V1["look_at"]),
        shot("v11", S.V11["pos"], S.V11["look_at"]),
        shot("v12", S.V12["pos"], S.V12["look_at"]),
        # from the court, nearer and off the axis: the heads over each wing's parapet
        shot("court_north", (40.5, 1.62, -6.5), (nx, head, nz - 1.5)),
        shot("court_south", (40.5, 1.62, 7.5), (sx, head, sz + 1.5)),
        # from the ridge walk at eye height, as a visitor comes along it
        shot("walk_north", (ridge, eye, nz + 4.0), (nx, head - 0.6, nz - 1.0)),
        shot("walk_south", (ridge, eye, sz - 4.0), (sx, head - 0.6, sz + 1.0)),
        # how they are made: by day, close, from over the parapet and from the air
        shot("made", (nx + 3.2, head + 0.4, nz + 2.6), (nx, head - 1.2, nz), NOON),
        shot("made_small", (nx + 3.0, head, small[False]["at"][2] + 2.4), (nx, head - 1.2, small[False]["at"][2]), NOON),
        shot("air_north", (nx + 12.0, head + 7.0, nz + 9.0), (nx - 2.0, head - 2.0, nz - 2.0), NOON),
    ]
