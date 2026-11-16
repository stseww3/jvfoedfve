"""Test scene for the card sky/ridges: the far ridges seen from where people stand.

    python -m scenes.obs_sky_ridges                 writes shots.json and prints what every shot holds
    python -m scenes.obs_sky_ridges.preview DIR     the sky with the ridges on it, by the shader's twin

The ridges are painted by the sky's shader (scenes.obs.sky.ridges hands it the layer). So this is
a world as a Realms map has it (card sky/safe-look, scene obs_sky_safe): no biome and no timeline
of ours (mood.py), the plot filled with one of the game's own biomes, the clock stopped at the
look's hour, and the look in the resource pack's core shaders.

A stand-in for the site in plain vanilla blocks, enough to stand on and to hide what the real site
hides: the upper terrace with the half-round sunset platform at its west end, the main building
as a plain block, the lower platform and the south lookout, each with walls that go down under
the cloud layer, since the real site is a mountain.

No offline picture is kept: the offline renderer does not run the game's shaders, so it shows
neither this sky nor the ridges on it. What the game draws is seen in the game. preview.py draws
the sky as the shader's twin gives it: a tool to shape the ridges with, not evidence.

A ridge stands at no distance: its line is the same for every eye. What a shot holds of it is
the part of the line that lies in the frame and that the stand-in does not hide (describe()).

The shots (the card's list):
  west, northwest, southwest   from the west rail of the sunset platform, where the view is open
  east                         from the court to the east: no ridge may show
  back_west                    from the east edge of the terrace, 87 blocks further back: the ridges
                               on either side of the main building, as high over the horizon as
                               in `west`
  v11                          the skeleton's V11, from the south lookout north-north-west, the
                               afterglow at its left edge
  v1, v2                       the skeleton's arrival view and axis view, the two pictures the map is
                               known by: in V1 a low hill of the north range shows in the strip of
                               horizon at the right edge, between the terrace's end and the station;
                               in V2 the ranges show low at the picture's edges, on either side of
                               the main building
"""
import functools
import json
import math
import os

import numpy as np

from artkit.canvas import Canvas
from scenes.obs import sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.sky import _shaders, mood, ridges

BIOME = "minecraft:the_void"        # as in obs_sky_safe: no weather, nothing spawns
BIOME_MARGIN = 120          # the biome has to reach past the cameras, not only over the blocks
BIOME_MARGIN_Y = 150

STONE = B.TUFF_SMOOTH.block          # the stand-in's walls
DARK = B.SLATE_SMOOTH.block          # its ground

SKIRT_Y = int(mood.CLOUD_TOP) - int(mood.CLOUD_THICKNESS) - 2       # how far down the stand-in's walls go

FOV = 77.0                  # what the pictures are taken at (render.py, tools/shoot.py)
ASPECT = 16.0 / 9.0

RAIL = (S.SUNSET_PLATFORM["centre"][0] - S.SUNSET_PLATFORM["radius"] + 1.5, S.GROUND + S.EYE, S.AXIS_Z)
BACK = (S.EAST_EDGE_X - 0.5, S.GROUND + S.EYE, S.AXIS_Z)
COURT = (S.MERIDIAN_X + 0.5, S.GROUND + S.EYE, S.AXIS_Z)


def _towards(pos, bearing, up, reach=100.0):
    """A point to look at: reach blocks from pos, bearing degrees north of due west, up degrees up."""
    a, e = math.radians(bearing), math.radians(up)
    return (round(pos[0] - reach * math.cos(e) * math.cos(a), 2), round(pos[1] + reach * math.sin(e), 2),
            round(pos[2] - reach * math.cos(e) * math.sin(a), 2))


# name: (eye, look_at)
CAMERAS = {
    "west": (RAIL, _towards(RAIL, 0.0, 6.0)),
    "northwest": (RAIL, _towards(RAIL, 45.0, 6.0)),
    "southwest": (RAIL, _towards(RAIL, -45.0, 6.0)),
    "east": (COURT, _towards(COURT, 180.0, 6.0)),
    "back_west": (BACK, _towards(BACK, 0.0, 6.0)),
    "v11": (S.V11["pos"], S.V11["look_at"]),
    "v1": (S.V1["pos"], S.V1["look_at"]),
    "v2": (S.V2["pos"], S.V2["look_at"]),
}


def write_pack(pack_dir):
    """The sky's pack (the sun painted out, the comet in the moon's slot) and the shaders that carry
    the look, the ridges' layer in them."""
    return list(sky.pack(pack_dir) or []) + _shaders.pack(pack_dir)


def shots():
    """Every camera at the hour the clock is stopped at."""
    return [dict(name=name, pos=[float(v) for v in pos], look_at=[float(v) for v in at], time=mood.LOCK_TICK)
            for name, (pos, at) in CAMERAS.items()]


def _rect(x0, z0, x1, z1):
    return {(x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)}


def _upper():
    """The cells of the upper terrace with the half-round sunset platform at its west end."""
    x0, z0, x1, z1 = S.UPPER_TERRACE
    cx, cz = S.SUNSET_PLATFORM["centre"]
    r = S.SUNSET_PLATFORM["radius"]
    return _rect(x0, z0, x1, z1) | {(x, z) for x in range(cx - r, x0) for z in range(cz - r, cz + r + 1)
                                    if math.hypot(x - cx, z - cz) <= r}


@functools.lru_cache(maxsize=None)
def masses():
    """The stand-in as solid shapes: (cells (x, z), lowest y, the y its top lies at). The pavings
    stand on walls that go down to SKIRT_Y, so from outside each is a solid mass."""
    lookout = S.SOUTH_LOOKOUT["box"]
    return [
        (_upper(), SKIRT_Y, S.PAVING_Y + 1),
        (_rect(S.WALL_W, S.Z_NORTH, S.WALL_E, S.Z_SOUTH), S.GROUND, S.CORNICE + 1),       # the main building
        (_rect(*S.LOWER_PLATFORM), SKIRT_Y, S.LOWER_PAVING_Y + 1),
        (_rect(*lookout), SKIRT_Y, S.SOUTH_LOOKOUT["feet"]),
    ]


def _skirt(c, cells, top):
    """Walls under the rim of a paving (a set of (x, z)), from under it down to SKIRT_Y: what the
    mountain under a terrace hides stays hidden."""
    for x, z in cells:
        if all((x + dx, z + dz) in cells for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            continue
        for y in range(SKIRT_Y, top):
            c.set(x, y, z, STONE)


def build():
    c = Canvas()
    (upper, _, _), (house, _, _), (lower, _, _), (lookout, _, _) = masses()
    for x, z in upper:
        c.set(x, S.PAVING_Y, z, DARK)
    _skirt(c, upper, S.PAVING_Y)
    # the main building: a plain block as high as the cornice, hollow
    for x, z in house:
        for y in range(S.GROUND, S.CORNICE + 1):
            if y == S.CORNICE or x in (S.WALL_W, S.WALL_E) or z in (S.Z_NORTH, S.Z_SOUTH):
                c.set(x, y, z, STONE)
    for x, z in lower:
        c.set(x, S.LOWER_PAVING_Y, z, DARK)
    _skirt(c, lower, S.LOWER_PAVING_Y)
    for x, z in lookout:
        c.set(x, S.SOUTH_LOOKOUT["feet"] - 1, z, DARK)
    _skirt(c, lookout, S.SOUTH_LOOKOUT["feet"] - 1)
    return c


# ---- what a camera holds -------------------------------------------------------------------------
def ridge_line():
    """The ridge line as the shader has it: (bearing north of due west, degrees up) for every
    column of the table in which a ridge stands."""
    up = ridges.baked() * ridges.STEP
    bearing = ridges.FROM + (np.arange(ridges.COLUMNS) + 0.5) * ridges.STEP
    return [(float(b), float(u)) for b, u in zip(bearing, up) if u > 0.0]


def _direction(bearing, up):
    a, e = math.radians(bearing), math.radians(up)
    return np.array([-math.cos(e) * math.cos(a), math.sin(e), -math.cos(e) * math.sin(a)])


def _frame(pos, at):
    f = np.array(at, dtype=float) - np.array(pos, dtype=float)
    f /= np.linalg.norm(f)
    right = np.cross(f, (0.0, 1.0, 0.0))
    right /= np.linalg.norm(right)
    return f, right, np.cross(right, f)


def _inside(pos, at, bearing, up):
    """Whether a direction (bearing north of due west, degrees up) lies in a shot's picture."""
    f, right, top = _frame(pos, at)
    d = _direction(bearing, up)
    along = d @ f
    if along <= 0.0:
        return False
    half = math.tan(math.radians(FOV / 2.0))
    return abs(d @ right / along) <= half * ASPECT and abs(d @ top / along) <= half


def hidden(pos, bearing, up, reach=160.0, step=0.25):
    """Whether the stand-in stands in the way of a direction from pos (bearing north of due west,
    degrees up): the sight line is walked in steps as far as the stand-in reaches."""
    d = _direction(bearing, up)
    p = np.array(pos, dtype=float)[None, :] + np.arange(step, reach, step)[:, None] * d[None, :]
    cells = list(zip(np.floor(p[:, 0]).astype(int).tolist(), np.floor(p[:, 2]).astype(int).tolist()))
    for mass, low, top in masses():
        inside = (p[:, 1] >= low) & (p[:, 1] < top)
        if any(ok and c in mass for ok, c in zip(inside.tolist(), cells)):
            return True
    return False


def describe():
    """What every shot shows of the ridges: the part of each range's line whose top lies in the
    frame and is not hidden by the stand-in."""
    lines = list(ridges.report())
    twin = _shaders.Twin(mood.DEFAULT)
    whole = ridge_line()
    for name, (pos, at) in CAMERAS.items():
        parts = []
        behind = False
        for side, sign in (("north", 1.0), ("south", -1.0)):
            line = [p for p in whole if p[0] * sign > 0.0 and _inside(pos, at, *p)]
            behind = behind or bool(line)
            line = [p for p in line if not hidden(pos, *p)]
            if not line:
                continue
            top = max(line, key=lambda p: p[1])
            glow = float(twin.fan(np.array([_direction(*p) for p in line])).max())
            parts.append(f"{side} {min(p[0] for p in line):.0f} to {max(p[0] for p in line):.0f}, "
                         f"up to {top[1]:.2f} degrees at {top[0]:.0f}, afterglow to {glow:.2f}")
        none = "no ridge in sight: what the frame holds of them is behind the stand-in" if behind else "no ridge in the frame"
        lines.append(f"{name:10s} " + ("; ".join(parts) if parts else none))
    return lines


def tell(folder):
    path = os.path.join(folder, "shots.json")
    with open(path, "w") as fh:
        fh.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n")
    print(f"{path}: {len(shots())} shots")
    print("\n".join(describe()))
