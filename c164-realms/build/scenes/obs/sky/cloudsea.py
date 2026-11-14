"""Work package sky/cloudsea: the sea of clouds the observatory floats on (plan 3.2, 10; card
plan/packages/sky/cloudsea.md; c219's terrain review #163.1).

Three ways to make the sea, chosen by ``version`` and compared on the real client (the offline
renderer draws the fog but neither the vanilla cloud layer nor the afterglow, so it shows the block
clouds' shape and tones in fog; the card is settled on S1's real-game pictures, each camera shot
with the cloud setting off and fast as well):

    "a"  vanilla only   no block clouds; a denser, repainted clouds.png carries the whole sea. It
                        fails the "clouds off" test on purpose -- the weakness the comparison shows.
    "b"  blocks only    the block sea; the vanilla layer is blanked, the far distance left to the fog.
    "c"  both (default) the same block sea with the vanilla layer under and beyond it. What the
                        master scene builds (A0 #171: "block clouds near, the game's cloud layer and
                        fog far"); with the player's clouds switched off it is "b".

The block clouds are a churning carpet, not a plate on a dish (the review's verdict on the stand-in):
densely tiled near the middle with its top rolling one to three blocks, broken into clumps and then
scattered to nothing by the scatter radius, so no circular edge is ever seen -- what is left out
there is lost in the fog. The top sits at scene y -26, crowns pile to -23 and a few to -20. Only
empty cells are filled, two clear of any block, so the mountain and the platforms poke through by
themselves and the sea laps round them wherever they fall below the cloud line.

The five tones are the occupancy roles B.CLOUD (dark to light, palette RAMPS["cloud"]). This package
paints them (A0's exception to "only materials paints blocks": the cloud colour is tuned with the
light of the sky), through materials/_kit like everyone else, so the stand-in steps aside the moment
BLOCKS names them. The pictures are flat tones named sky_cloud_0..4; which tone a block of the sea
wears is baked here from how far its surface faces up and how exposed it stands (the shading of
artkit/clouds, reused), so a block face shows one flat colour and the game's own face shading is
turned off (shade=False, ao=False).
"""
import numpy as np

from artkit import respack
from artkit.clouds import _blur, _hash3            # reused: the sea's tone allocation (card)
from artkit import noise as N

from ..common import blocks as B
from ..common import palette as P
from ..materials import _kit as K

# The blocks this package paints; nobody else may (the stand-in reads this and lets them go).
BLOCKS = K.blocks(B.CLOUD)

VERSIONS = ("a", "b", "c")
DEFAULT = "c"

CENTRE = (30.0, 0.0)            # the sea is drawn round this point (card)
SHEET_TOP = -26                 # scene y of the carpet's top face (2 above the vanilla layer at -28)
SHEET_BOTTOM = -28              # the carpet's flat underside where it is thick
RISE = 6                        # crowns pile up to SHEET_TOP + RISE = -20 at the very most
SEED = 41

# How far the sea reaches (card): tiled solid inside ``fill``, scattered to nothing by ``scatter``.
# The same for "b" and "c": with the player's clouds off, "c" has to stand as "b" does.
REACH = dict(fill=150.0, scatter=215.0)
CLEAR = 1                       # empty cells kept between the sea and any other block

# The vanilla cloud sheet (clouds.png): 256x256, one pixel is a 12x12-block cloud; it tiles on all
# four edges. Repainted denser than vanilla (27.6%) with north-south lanes, so the far layer reads
# as a packed sea rather than scattered tufts. Blanked for "b" (no vanilla layer there).
CLOUDS_PNG = dict(coverage=0.88, lanes=(39, 112, 184), lane_w=2, blur=6, seed=SEED + 2)

GRAIN = 0.10                    # share of a tone's pixels nudged one step, within the cloud ramp


# --- the five flat tone pictures ---------------------------------------------------------------------
def _tone(i, seed=SEED):
    """A flat cloud tone with a breath of grain, every pixel a colour of RAMPS["cloud"]."""
    px = np.empty((K.TILE, K.TILE, 4), dtype=np.uint8)
    px[..., :3] = P.colour("cloud", i)
    px[..., 3] = 255
    jj, ii = np.meshgrid(np.arange(K.TILE), np.arange(K.TILE), indexing="ij")
    r = _hash3(ii, jj, 0 * ii, seed + i)
    px[r > 1.0 - GRAIN / 2, :3] = P.colour("cloud", min(i + 1, len(P.RAMPS["cloud"]) - 1))
    px[r < GRAIN / 2, :3] = P.colour("cloud", max(i - 1, 0))
    return px


def _clouds_sheet(blank=False):
    """A 256x256 cloud sheet for the vanilla layer: white where there is cloud (the game tints it by
    cloud_color), transparent where there is not. Seamless on every edge; denser than vanilla."""
    n = 256
    out = np.zeros((n, n, 4), dtype=np.uint8)
    out[..., :3] = 255
    if blank:
        return out                                  # the vanilla layer off (version "b")
    rng = np.random.default_rng(CLOUDS_PNG["seed"])
    field = rng.random((n, n)).astype(np.float32)
    r = CLOUDS_PNG["blur"]
    for _ in range(2):                              # a wrap-around box blur keeps the tiling seamless
        for ax in (0, 1):
            acc = np.zeros_like(field)
            for d in range(-r, r + 1):
                acc += np.roll(field, d, axis=ax)
            field = acc / (2 * r + 1)
    mask = field >= np.quantile(field, 1.0 - CLOUDS_PNG["coverage"])
    for x in CLOUDS_PNG["lanes"]:                   # north-south lanes (full columns tile cleanly)
        mask[:, x:x + CLOUDS_PNG["lane_w"]] = False
    out[..., 3] = np.where(mask, 255, 0)
    return out


# --- the block sea -----------------------------------------------------------------------------------
def _volume(reach, seed):
    """(solid, (x0, y0, z0)): a boolean box of the block sea in scene coordinates. A carpet whose top
    rolls between -26 and -20, densely tiled inside ``fill`` and scattering to nothing by ``scatter``
    so the edge dissolves instead of cutting a circle."""
    cx, cz = CENTRE
    fill, scatter = reach["fill"], reach["scatter"]
    x0, x1 = int(np.floor(cx - scatter)), int(np.ceil(cx + scatter))
    z0, z1 = int(np.floor(cz - scatter)), int(np.ceil(cz + scatter))
    y0, y1 = SHEET_BOTTOM - 5, SHEET_TOP + RISE + 1
    nx, nz = x1 - x0 + 1, z1 - z0 + 1

    X, Z = np.meshgrid(np.arange(nx) + x0, np.arange(nz) + z0, indexing="ij")
    r = np.hypot(X - cx, Z - cz)
    wobble = N.fbm2(X / 41.0, Z / 41.0, seed + 5, octaves=3) * 22.0    # the edge is not a circle
    density = N.smoothstep(scatter, fill, r - wobble)                  # 1 inside fill, 0 past scatter

    # present: a solid carpet where it is dense, breaking into clumps and then stray puffs as it thins
    clump = 0.5 + 0.5 * N.fbm2(X / 10.0, Z / 10.0, seed + 9, octaves=3)
    present = (density > 0.03) & (clump < np.minimum(1.1, 0.08 + density * 1.08))

    # the rolling top: mostly one to three blocks of relief, a few crowns higher
    roll = 0.5 + 0.5 * N.fbm2(X / 15.0, Z / 15.0, seed, octaves=3)
    fine = 0.5 + 0.5 * N.fbm2(X / 5.5, Z / 5.5, seed + 3, octaves=2)
    up = np.clip((0.7 * roll + 0.3 * fine - 0.33) * (RISE + 2.0), -1.0, float(RISE))
    up *= np.clip(0.4 + 0.6 * density, 0.0, 1.0)                       # flatter where it is thin
    top = np.rint(SHEET_TOP + up).astype(np.int64)
    bottom = np.rint(top - (1.5 + 4.0 * density)).astype(np.int64)     # thick when dense, thin when sparse
    bottom = np.minimum(bottom, SHEET_BOTTOM)

    ty = np.clip(top - y0, 0, y1 - y0)
    by = np.clip(bottom - y0, 0, y1 - y0)
    ys = np.arange(y1 - y0 + 1)[None, :, None] + y0
    solid = (present[:, None, :] & (ys >= bottom[:, None, :]) & (ys <= top[:, None, :])
             & (ty[:, None, :] >= by[:, None, :]))
    return solid, (x0, y0, z0)


def _dilate(a, r):
    """Grow a boolean box by r cells in every direction (Chebyshev), separably."""
    out = a
    for ax in range(a.ndim):
        acc = out.copy()
        for d in range(1, r + 1):
            acc |= np.roll(out, d, axis=ax)
            acc |= np.roll(out, -d, axis=ax)
        out = acc
    return out


def _clear_of_blocks(solid, lo, canvas, origin, clearance=CLEAR):
    """Drop cloud cells that overlap a block already on the canvas or leave fewer than ``clearance``
    empty cells to it, so the sea keeps clear of the mountain and the platforms (card: only empty
    cells, two away from the site's blocks) and no fence, wall or pane joins on to a cloud."""
    x0, y0, z0 = lo
    ox, oy, oz = origin
    nx, ny, nz = solid.shape
    occ = np.zeros_like(solid)
    ix, iy, iz = [], [], []
    for (x, y, z) in canvas.b:
        a, b, c = x - ox - x0, y - oy - y0, z - oz - z0
        if 0 <= a < nx and 0 <= b < ny and 0 <= c < nz:
            ix.append(a), iy.append(b), iz.append(c)
    if ix:
        occ[np.array(ix), np.array(iy), np.array(iz)] = True
        solid &= ~_dilate(occ, clearance)
    return solid


def _shade(solid):
    """Per cell a tone index 0..4 (dark to light) for the skin cells: bright on crowns and exposed
    faces, dark in the troughs between clumps. The allocation of artkit/clouds, reused."""
    near = _blur(solid.astype(np.float32), 2)       # where the surface faces
    wide = _blur(near, 4, passes=1)                 # how buried a spot is
    g = np.pad(near, 1, mode="edge")
    gx = g[:-2, 1:-1, 1:-1] - g[2:, 1:-1, 1:-1]
    gy = g[1:-1, :-2, 1:-1] - g[1:-1, 2:, 1:-1]
    gz = g[1:-1, 1:-1, :-2] - g[1:-1, 1:-1, 2:]
    up = gy / (np.sqrt(gx * gx + gy * gy + gz * gz) + 1e-6)
    exposed = np.clip((0.62 - wide) / 0.34, 0.0, 1.0)
    light = N.smoothstep(0.15, 0.95, 0.45 * (0.5 + 0.5 * up) + 0.55 * exposed)
    return light


def build(canvas, origin=(0, 0, 0), version=DEFAULT, *, seed=SEED):
    """Pile the block cloud sea into the canvas. Places blocks only, so it returns 0 display entities.
    The master scene calls build(canvas, origin); a test scene passes version to compare the three."""
    if version not in VERSIONS:
        raise ValueError(f"cloudsea version is one of {VERSIONS}, not {version!r}")
    # The sea is laid once: a sheet of cloud tones put down earlier (site/terrain's stand-in for this
    # package) is taken up, whichever version is built.
    names = list(B.CLOUD)                           # dark..light, as the tone index runs
    for key in [k for k, state in canvas.b.items() if state.partition("[")[0].split(":")[-1] in names]:
        del canvas.b[key]
    if version == "a":                              # vanilla layer only: no blocks
        return 0
    solid, lo = _volume(REACH, seed)
    solid = _clear_of_blocks(solid, lo, canvas, origin)

    # only what can be seen from above or from the side is placed: a cell with cloud over it and on
    # all four sides is left out, and so is the unseen underside of the carpet
    p = np.pad(solid, 1)
    inner = (p[1:-1, 2:, 1:-1] & p[:-2, 1:-1, 1:-1] & p[2:, 1:-1, 1:-1]
             & p[1:-1, 1:-1, :-2] & p[1:-1, 1:-1, 2:])
    ii, jj, kk = np.nonzero(solid & ~inner)
    if not len(ii):
        return 0
    light = _shade(solid)[ii, jj, kk]
    x0, y0, z0 = lo
    ox, oy, oz = origin
    xs, ys, zs = ii + x0, jj + y0, kk + z0
    last = len(B.CLOUD) - 1
    dither = (_hash3(xs, ys, zs, seed) - 0.5) * 0.9
    idx = np.clip(np.rint(last * light + dither), 0, last).astype(int)
    for x, y, z, t in zip((xs + ox).tolist(), (ys + oy).tolist(), (zs + oz).tolist(), idx.tolist()):
        canvas.set(x, y, z, names[t], keep=True)
    return 0


# --- the resource pack: the five tone pictures, the five blocks, the vanilla sheet -------------------
def pack(pack_dir, version=DEFAULT):
    out = []
    for i in range(len(B.CLOUD)):
        K.paint(pack_dir, f"sky_cloud_{i}", _tone(i))
    for i, block in enumerate(B.CLOUD):
        mapping = {ref: f"sky_cloud_{i}" for ref in respack.block_pictures(K.game(), block)}
        out.append(K.redirect(pack_dir, block, mapping, shade=False, ao=False))
    blank = version == "b"
    respack.texture(pack_dir, "environment/clouds", _clouds_sheet(blank=blank))
    out.append("clouds.png: " + ("blanked (block clouds only)" if blank
                                 else f"{int(CLOUDS_PNG['coverage'] * 100)}% cover, north-south lanes"))
    return out
