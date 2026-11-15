"""Test scene for the card sky/ridges: the far ridges seen from where people stand.

    python -m scenes.obs_sky_ridges             writes shots.json and prints what every shot holds
    python -m scenes.obs_sky_ridges.sheet DIR   a preview of the shots by the game's own arithmetic

A stand-in for the site in plain vanilla blocks, enough to stand on and to hide what the real site
hides: the upper terrace with the half-round sunset platform at its west end, the main building
as a plain block, the lower platform and the south lookout, each with walls that go down under
the cloud layer, since the real site is a mountain. The ridges themselves are the four
display entities of scenes.obs.sky.ridges, which stand in the middle of the terrace and are drawn
360 to 446 blocks out.

The offline pictures cannot show the ridges: the offline renderer follows a ray as far as the game
draws blocks (192 blocks at 12 chunks) and it has no afterglow. They show where the cameras
stand. Whether the game draws a sheet that far out, in which colour and without flicker, is only
seen in the game: the card's first question (sky-notes.md 10.5). Until the game has answered,
sheet.py draws what the game's arithmetic gives for the same cameras; it is a tool to shape the
ridges with, not evidence.

The shots (the card's list):
  west, northwest, southwest   from the west rail of the sunset platform, where the view is open
  west_glow, west_deep         the same view under the other two lights: under glow the afterglow
                               is strongest, so a ridge that is drawn at all shows there
  east                         from the court to the east: no ridge may show
  back_west                    from the east edge of the terrace, 87 blocks further back: the ridges
                               on either side of the main building; set against `west` it shows how
                               far the ridge line shifts against the horizon when a person walks
  v11                          the skeleton's V11: it looks north-north-west with the afterglow at its
                               left edge, and the strip of horizon it has left of the terrace is the
                               gap between the two ranges, moved north by the 52 blocks the lookout
                               lies south of the axis; no ridge shows there, and none should
  v1, v2                       the skeleton's arrival view and axis view, the two pictures the map is
                               known by: in V1 the north range stands in the strip of sky at the right
                               edge, north of the terrace; in V2 the outer peaks of both ranges stand
                               low at the picture's edges, on either side of the main building
"""
import json
import math
import os

import numpy as np

from artkit.canvas import Canvas
from scenes.obs import sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.sky import mood, ridges

BIOME = "obs_blue"
BIOME_MARGIN = 120          # the look has to reach past the cameras, not only over the blocks
BIOME_MARGIN_Y = 150

STONE = B.TUFF_SMOOTH.block          # the stand-in's walls
DARK = B.SLATE_SMOOTH.block          # its ground

SKIRT_Y = int(mood.CLOUD_TOP) - int(mood.CLOUD_THICKNESS) - 2       # how far down the stand-in's walls go

FOV = 77.0                  # what the pictures are taken at (render.py, tools/shoot.py)
ASPECT = 16.0 / 9.0

RAIL = (S.SUNSET_PLATFORM["centre"][0] - S.SUNSET_PLATFORM["radius"] + 1.5, S.GROUND + S.EYE, S.AXIS_Z)
BACK = (S.EAST_EDGE_X - 0.5, S.GROUND + S.EYE, S.AXIS_Z)


def _towards(pos, bearing, up, reach=100.0):
    """A point to look at: reach blocks from pos, bearing degrees north of due west, up degrees up."""
    a, e = math.radians(bearing), math.radians(up)
    return (round(pos[0] - reach * math.cos(e) * math.cos(a), 2), round(pos[1] + reach * math.sin(e), 2),
            round(pos[2] - reach * math.cos(e) * math.sin(a), 2))


# name: (eye, look_at, light)
CAMERAS = {
    "west": (RAIL, _towards(RAIL, 0.0, 6.0), "blue"),
    "northwest": (RAIL, _towards(RAIL, 45.0, 6.0), "blue"),
    "southwest": (RAIL, _towards(RAIL, -45.0, 6.0), "blue"),
    "west_glow": (RAIL, _towards(RAIL, 0.0, 6.0), "glow"),
    "west_deep": (RAIL, _towards(RAIL, 0.0, 6.0), "deep"),
    "east": ((S.MERIDIAN_X + 0.5, S.GROUND + S.EYE, S.AXIS_Z), _towards((S.MERIDIAN_X + 0.5, S.GROUND + S.EYE, S.AXIS_Z), 180.0, 6.0), "blue"),
    "back_west": (BACK, _towards(BACK, 0.0, 6.0), "blue"),
    "v11": (S.V11["pos"], S.V11["look_at"], "blue"),
    "v1": (S.V1["pos"], S.V1["look_at"], "blue"),
    "v2": (S.V2["pos"], S.V2["look_at"], "blue"),
}


def write_pack(pack_dir):
    """The sky's pack (the sun painted out, the comet in the moon's slot): the scene uses the map's hour."""
    return list(sky.pack(pack_dir) or [])


def shots():
    return [dict(name=name, pos=[float(v) for v in pos], look_at=[float(v) for v in at], time=mood.tick(look))
            for name, (pos, at, look) in CAMERAS.items()]


def _skirt(c, cells, top):
    """Walls under the rim of a paving (a set of (x, z)), from under it down to SKIRT_Y: what the
    mountain under a terrace hides stays hidden."""
    for x, z in cells:
        if all((x + dx, z + dz) in cells for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            continue
        for y in range(SKIRT_Y, top):
            c.set(x, y, z, STONE)


def _rect(x0, z0, x1, z1):
    return {(x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)}


def build():
    c = Canvas()
    x0, z0, x1, z1 = S.UPPER_TERRACE
    upper = _rect(x0, z0, x1, z1)
    cx, cz = S.SUNSET_PLATFORM["centre"]
    r = S.SUNSET_PLATFORM["radius"]
    upper |= {(x, z) for x in range(cx - r, x0) for z in range(cz - r, cz + r + 1) if math.hypot(x - cx, z - cz) <= r}
    for x, z in upper:
        c.set(x, S.PAVING_Y, z, DARK)
    _skirt(c, upper, S.PAVING_Y)
    # the main building: a plain block as high as the cornice, hollow
    for y in range(S.GROUND, S.CORNICE + 1):
        for x in range(S.WALL_W, S.WALL_E + 1):
            for z in range(S.Z_NORTH, S.Z_SOUTH + 1):
                if y == S.CORNICE or x in (S.WALL_W, S.WALL_E) or z in (S.Z_NORTH, S.Z_SOUTH):
                    c.set(x, y, z, STONE)
    x0, z0, x1, z1 = S.LOWER_PLATFORM
    c.box(x0, S.LOWER_PAVING_Y, z0, x1, S.LOWER_PAVING_Y, z1, DARK)
    _skirt(c, _rect(x0, z0, x1, z1), S.LOWER_PAVING_Y)
    x0, z0, x1, z1 = S.SOUTH_LOOKOUT["box"]
    c.box(x0, S.SOUTH_LOOKOUT["feet"] - 1, z0, x1, S.SOUTH_LOOKOUT["feet"] - 1, z1, DARK)
    _skirt(c, _rect(x0, z0, x1, z1), S.SOUTH_LOOKOUT["feet"] - 1)
    ridges.build(c)
    return c


# ---- what a camera holds -------------------------------------------------------------------------
def seen(pos, name):
    """A sheet's ridge line as a camera sees it: for each of its columns (bearing north of due west,
    degrees up, distance), only where the ridge stands out of the cloud layer."""
    ridge = ridges.crest(name)
    low_left, low_right = ridges.corners(name)[:2]
    out = []
    for i in range(ridges.WIDTH):
        p = low_left + (low_right - low_left) * ((i + 0.5) / ridges.WIDTH)
        if ridge[i] <= ridges.SEA:
            continue
        dx, dz = p[0] - pos[0], p[2] - pos[2]
        reach = math.hypot(dx, dz)
        out.append((math.degrees(math.atan2(-dz, -dx)), math.degrees(math.atan2(ridge[i] - pos[1], reach)), reach))
    return out


def _frame(pos, at):
    f = np.array(at, dtype=float) - np.array(pos, dtype=float)
    f /= np.linalg.norm(f)
    right = np.cross(f, (0.0, 1.0, 0.0))
    right /= np.linalg.norm(right)
    return f, right, np.cross(right, f)


def _inside(pos, at, bearing, up):
    """Whether a direction (bearing north of due west, degrees up) lies in a shot's picture."""
    f, right, top = _frame(pos, at)
    a, e = math.radians(bearing), math.radians(up)
    d = np.array([-math.cos(e) * math.cos(a), math.sin(e), -math.cos(e) * math.sin(a)])
    along = d @ f
    if along <= 0.0:
        return False
    half = math.tan(math.radians(FOV / 2.0))
    return abs(d @ right / along) <= half * ASPECT and abs(d @ top / along) <= half


def describe():
    """What the frame of every shot holds of the ridges; the stand-in's blocks in front are not counted."""
    lines = list(ridges.report())
    for name, (pos, at, look) in CAMERAS.items():
        alpha = mood.look(look)["glow_alpha"]
        parts = []
        for sheet in ridges.SHEETS:
            line = [p for p in seen(pos, sheet) if _inside(pos, at, p[0], p[1])]
            if not line:
                continue
            top = max(line, key=lambda p: p[1])
            fan = max(ridges.fan(abs(b), max(u, 0.0), alpha) for b, u, _ in line)
            parts.append(f"{sheet} {min(p[0] for p in line):.0f} to {max(p[0] for p in line):.0f}, "
                         f"up to {top[1]:.1f} degrees at {top[0]:.0f} ({top[2]:.0f} blocks), afterglow to {fan:.2f}")
        lines.append(f"{name:10s} ({look}) " + ("; ".join(parts) if parts else "no ridge in the frame"))
    return lines


def tell(folder):
    path = os.path.join(folder, "shots.json")
    with open(path, "w") as fh:
        fh.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n")
    print(f"{path}: {len(shots())} shots")
    print("\n".join(describe()))
