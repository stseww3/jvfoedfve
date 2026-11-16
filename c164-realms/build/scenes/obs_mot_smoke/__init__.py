"""Test scene of the work package motion/smoke: the chimney's mouth and what comes out of it.

A stand-in for the power house's chimney stands where the real one does, made from site/powerhouse's
own numbers (the foot, the shaft, the flue, the iron rim) on the lower platform's paving. So
motion/smoke finds its chimney and registers the smoke at powerhouse.SMOKE exactly as it does in
the master scene, and the cameras that are locked for the master scene stand right here too.

Particles are not drawn offline: the offline pictures of this scene show the bare stand-in, and
whether it smokes is for the real machine to say. On the real machine the driver runs the scene's
start function once the scene stands (build/place.py). Every camera is in the shot list twice, the
second time as <name>_again, so that sky/_tones.py --diff of the pair shows what has moved in
between: the footprint should be one streak over the mouth, leaning south. The game must not be
frozen (tick freeze) while the pictures are taken, and the pair should be taken a few seconds
apart, not a whole number of BEATs (2 seconds).

The cameras
    v6       the skeleton's locked view of the power house from the grand stair, 37 blocks off
    v12      the board's view of the whole island from the north-east, low (A0, 11-16): the
             chimney is 85 blocks off and the smoke stands against the sky
    arrival  a person on the station platform, two steps south of V1's eye, who has turned to
             the chimney: 60 blocks off. (V1 itself does not show it: the chimney stands outside
             that picture's left edge, and the smoke leans further out.)
    side     from the west, square to the wind: the lean
    mouth    close to the rim: does the smoke come out of the flue

    python -m scenes.obs_mot_smoke      (in build/) writes shots.json and says where the smoke
                                        falls in the pictures of V1, V6 and V12
"""
import math

from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.motion import _kit as MK
from scenes.obs.motion import smoke
from scenes.obs.site import powerhouse as H

BIOME = "obs_blue"
BIOME_MARGIN = 100
BIOME_MARGIN_Y = 150

BODY, COURSE, IRON = B.TUFF_BRICK.block, B.TUFF_SMOOTH.block, B.IRON_RIVETED.block
PAVING = B.TUFF_SMOOTH.block
TIME = 14000                    # light version A, the default
FOV, ASPECT = 77.0, 16.0 / 9.0  # the game's picture, as tools/boardshots.py has it
LIFE = (280, 330)               # ticks a puff of campfire_signal_smoke lives

# The board's twelfth view: the whole island from the north-east, low (A0's ruling of 11-16, g2
# #77204; it was a view from straight above, which showed roofs and no smoke). The skeleton's own
# S.V12 once it is written there, the ruling's numbers until then.
V12 = getattr(S, "V12", None) or dict(pos=(126.0, 44.0, -50.0), look_at=(22.0, 4.0, 0.0))


def plume(share=0.5):
    """A point of the smoke's middle line, `share` of the way from the mouth to where the puffs
    of the middle lane die."""
    x, y, z = H.SMOKE
    way = MK.downwind()
    reach = smoke.RISE * sum(LIFE) / 2.0 * share
    return (x + way[0] * reach, y + way[1] * reach, z + way[2] * reach)


def _views():
    x, y, z = H.SMOKE
    ax, ay, az = S.V1["pos"]
    return [
        ("v6", S.V6["pos"], S.V6["look_at"]),
        ("v12", V12["pos"], V12["look_at"]),
        ("arrival", (ax, ay, az + 2.0), plume(0.4)),
        ("side", (x - 30.0, y + 6.0, z + 2.0), plume(0.5)),
        ("mouth", (x - 6.0, y + 2.5, z - 5.0), (x, y + 1.5, z + 0.3)),
    ]


def shots():
    """The cameras, each twice (see scenes.obs_mot_loop)."""
    out = []
    for again in ("", "_again"):
        for name, pos, look_at in _views():
            out.append({"name": name + again, "pos": [round(float(v), 2) for v in pos],
                        "look_at": [round(float(v), 2) for v in look_at], "time": TIME})
    return out


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


def build():
    c = Canvas()
    x0, z0, x1, z1 = S.LOWER_PLATFORM
    c.box(x0, S.LOWER_PAVING_Y, z0, x1, S.LOWER_PAVING_Y, z1, PAVING)
    tx0, tz0, tx1, tz1 = H.TOWER
    c.box(tx0, H.FEET, tz0, tx1, H.PED_TOP, tz1, BODY)
    flue = set(H.FLUE)
    for y in range(H.PED_TOP + 1, H.TOP + 1):
        for x, z in H.SHAFT:
            if y > H.TOP - H.FLUE_DEPTH and (x, z) in flue:
                continue
            c.set(x, y, z, IRON if y == H.TOP else COURSE if y == H.TOP - 3 else BODY)
    smoke.build(c, (0, 0, 0))
    c.entity_counts = {"motion": 0}
    return c


def write_pack(pack_dir):
    """The repainted brick, stone and iron the stand-in is made of, and the map's sky: the smoke
    is judged against it."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
