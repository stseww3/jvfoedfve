"""The swell of the sea of clouds (card sky/cloudsea, round 2: what stood still moves).

The block sea cannot move. A few heads of cloud do. Each is one item display: a stepped dome in
the sea's own five tones, a block to the voxel as the block sea is, lit as the sea's upper faces
are. A head rests under the face of level sea, where nothing of it is seen; it rises slowly out
of the sea, stands, and sinks back. The heads further down the wind rise later, so that a swell
is seen to roll over the sea with the wind. Nothing travels, a head only goes up and down
(motion/_kit's slide): there is no way back to hide and nothing that comes near a rail or a pier.

Where: on level sea only. Every column under a head is the sea's and no higher than a low heap;
nothing built and no land within KEEP blocks of its rim, so the cloud at the foot of the cliffs
and round the trestle stays as it was laid; no nearer than NEAR to where people stand and no
further than FAR, where the fog has taken the sea.

With the loop stopped, or with no data pack at all, every head lies under the face: the sea is
the still one it was.
"""
import functools
import math

import numpy as np

from artkit import models as M
from artkit.nbtw import Float

from ..common import palette as P
from ..motion import _kit as MK

# Off since 11-16 13:15 (cr2): on the real client the heads' sides are darker than the sea (an item's
# faces are shaded by the way they face, 0.74 north and south, 0.5 east and west, whatever the
# model says; the block sea's are not), so a head reads as a stone stair. Until its shape is one
# of faces that look up, no head is placed.
ON = False                      # False: no head is placed
PREFIX = "sky_cloudsea_swell_"

VOXEL = 4.0                     # texels to a voxel of the model
SCALE = 4.0                     # ... shown at four times the size: a block to the voxel
SIDE = 11                       # columns across (48 texels are the most a model spans: 12)
TALL = 6                        # courses; the lowest never come out of the sea
# every shape: domes (east, south, radius, height) in columns from the middle, the highest wins
SHAPES = (
    ((0.0, 0.0, 5.4, 6.0),),
    ((-0.8, 0.4, 4.6, 6.0), (1.9, -1.0, 3.3, 4.4)),
    ((0.6, -0.9, 4.4, 6.0), (-1.8, 1.4, 3.4, 4.8)),
    ((0.0, 0.8, 4.8, 5.6), (0.4, -2.2, 3.0, 5.0)),
)
OFF = (0.37, 0.41)              # blocks a head stands off the grid: none of its faces lies in a block's
UNDER = 0.35                    # its crown rests this far under the lowest face over it
STAND = 2.6                     # ... and stands this far over the highest at the top of the swell

# One swell: up in three paces that slacken, a stand, down in three that quicken, and a rest under
# the face. Every pace sets off on a multiple of BEAT, and so does every head's place in the roll,
# so the whole swell costs the loop one function every two seconds.
BEAT = 40
CYCLE = 1600                    # ticks from one swell to the next at a place: 80 seconds
PACES = ((0, 0.55), (160, 0.87), (320, 1.0), (640, 0.87), (800, 0.55), (960, 0.0))   # (tick, share of the rise)
PACE = 160                      # ticks a pace takes
ROLL = 16                       # ticks the crest takes over one block down the wind: 100 blocks a swell
BEND = 9.0                      # blocks a crest bends back and forth across the wind
BEND_OVER = 23.0                # ... over this many blocks (times 2 pi)
AT_ONCE = 10                    # no more than this many heads set off on one beat

PITCH = 26                      # one head to a square of this side, at most
TRIES = 48                      # places tried in a square
KEEP = 12                       # blocks between a head's rim and the land or anything built
NEAR, FAR = 22.0, 112.0         # how far from where people stand a head may be
SEED = 4127
VIEW = M.FAR                    # seen across the whole site, as the sea is; the fog takes a head long before
ROOM = 0.5                      # blocks of room round a head in the box the game culls it by


def _heights(shape):
    """The height of every column of a head, 0..TALL voxels."""
    c = (SIDE - 1) / 2.0
    X, Z = np.meshgrid(np.arange(SIDE) - c, np.arange(SIDE) - c, indexing="ij")
    top = np.zeros((SIDE, SIDE))
    for px, pz, rad, rise in shape:
        d2 = ((X - px) ** 2 + (Z - pz) ** 2) / (rad * rad)
        top = np.maximum(top, np.where(d2 < 1.0, rise * np.sqrt(np.maximum(1.0 - d2, 0.0)), 0.0))
    return np.clip(np.rint(top), 0, TALL).astype(int)


def _tones(top):
    """{(i, j, k): (tone, faces not drawn)} for every voxel of a head that can be seen, shaded as
    sky/cloudsea shades the block sea: by its column's top, lighter where the head faces west and
    darker where it faces east; a voxel seen from the side only takes its column's light, more of
    it facing west, less facing east, and less the further down the side it lies."""
    last = len(P.RAMPS["cloud"]) - 1
    h = np.pad(top, 1)
    out = {}
    for i in range(SIDE):
        for k in range(SIDE):
            n = int(top[i, k])
            if not n:
                continue
            west, east, north, south = (int(h[i, k + 1]), int(h[i + 2, k + 1]), int(h[i + 1, k]), int(h[i + 1, k + 2]))
            light = 0.75 + min(max(0.30 * math.tanh(1.3 * (east - west) * 0.5), -0.34), 0.30)
            for j in range(n):
                skip = "d"
                skip += "" if j == n - 1 else "u"
                skip += "" if west <= j else "w"
                skip += "" if east <= j else "e"
                skip += "" if north <= j else "n"
                skip += "" if south <= j else "s"
                if len(skip) == 6:
                    continue
                if j == n - 1:
                    v = light
                else:
                    turn = 0.10 if west <= j else -0.06 if (north <= j or south <= j) else -0.16
                    v = light + turn - 0.05 * (n - 1 - j)
                out[(i, j, k)] = (int(min(max(round(last * v), 0), last)), skip)
    return out


def _model(name, shape):
    """A head: the anchor is the middle of its foot, so that the entity stands under all of it and
    the box the game culls it by (the entity's width and height) holds it at rest and risen."""
    m = M.Model(name, anchor=(SIDE * VOXEL / 2.0, 0.0, SIDE * VOXEL / 2.0))
    for (i, j, k), (tone, skip) in sorted(_tones(_heights(shape)).items()):
        m.box((i * VOXEL, j * VOXEL, k * VOXEL), ((i + 1) * VOXEL, (j + 1) * VOXEL, (k + 1) * VOXEL),
              P.mat("cloud", kind="flat", base=tone, bevel=0), skip=skip, seed=tone + 1, shade=False)
    return m


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + "abcdefgh"[n]: _model(PREFIX + "abcdefgh"[n], shape) for n, shape in enumerate(SHAPES)}


def models():
    return dict(_models()) if ON else {}


def sites(corner, top, sea, shore, hull, low, high, seed=SEED):
    """Where the heads go: [(x, z, lowest block top under it, highest)] in the grid's columns.

    corner   (x, z) of the grid's first column
    top      y of the highest block of cloud in every column
    sea      the columns that are sea and nothing else: cloud, and nothing built in them
    shore    how far every column lies from the nearest that is not such sea
    hull     how far every column lies from where people stand
    low, high   the block tops a head may have under it: level sea and its low heaps
    """
    nx, nz = top.shape
    r = SIDE // 2
    rng = np.random.default_rng(seed)
    out = []
    for a in range(0, nx - PITCH + 1, PITCH):
        for b in range(0, nz - PITCH + 1, PITCH):
            for _ in range(TRIES):
                i = a + int(rng.integers(r + 1, PITCH - r - 1))
                k = b + int(rng.integers(r + 1, PITCH - r - 1))
                if not (NEAR <= hull[i, k] <= FAR) or shore[i, k] < KEEP + r * math.sqrt(2.0):
                    continue
                patch = top[i - r:i + r + 1, k - r:k + r + 1]
                if not sea[i - r:i + r + 1, k - r:k + r + 1].all() or patch.min() < low or patch.max() > high:
                    continue
                out.append((corner[0] + i, corner[1] + k, int(patch.min()), int(patch.max())))
                break
    return out


def _beats(places, wind):
    """The beat of the cycle on which each head sets off: later down the wind, the crests bent a
    little; where more than AT_ONCE would set off together the last comers take the next beat."""
    n = CYCLE // BEAT
    load = [0] * n
    out = []
    for x, z, _, _ in places:
        along, across = x * wind[0] + z * wind[1], x * wind[1] - z * wind[0]
        beat = int(round((along + BEND * math.sin(across / BEND_OVER)) * ROLL / BEAT)) % n
        while load[beat] >= AT_ONCE:
            beat = (beat + 1) % n
        load[beat] += 1
        out.append(beat)
    return out


def place(canvas, origin, places, wind):
    """Put a head on every one of sites()' places and register its swell. Returns how many."""
    if not ON:
        return 0
    kit = list(_models().values())
    for n, ((x, z, lo, hi), beat) in enumerate(zip(places, _beats(places, wind))):
        rest = lo + 1 - UNDER                       # the upper face of the lowest block, less UNDER
        rise = hi + 1 + STAND - rest
        model = kit[(x * 7 + z * 13 + n) % len(kit)]
        nbt = M.display(model, scale=SCALE, brightness=(15, 0), view=VIEW)
        nbt["width"], nbt["height"] = Float(SIDE + 2 * ROOM), Float(TALL + rise + ROOM)
        canvas.add_entity(origin[0] + x + 0.5 + OFF[0], origin[1] + rest - TALL, origin[2] + z + 0.5 + OFF[1], nbt)
        MK.slide(canvas, (0.0, 1.0, 0.0), [(t, share * rise, PACE) for t, share in PACES], CYCLE, phase=beat * BEAT)
    return len(places)
