"""Test scene of the work package motion/smoke (plan/packages/motion/smoke.md).

Particles are not drawn offline, so no picture can show this package working: the card says so, and
the check for it is the real game. What this scene gives is the four places in place, so the puff
points land where they will land in the master scene and can be looked up on the real thing:

  a chimney mouth     the power house's flue at its own height (site/powerhouse.SMOKE)
  a valve on a pipe   the boiler's safety valve
  a fire door         the boiler's door, with its sparks
  a pair of brushes   the dynamo's brush gear, with its sparks

They are laid out on one flat shelf, so a camera at sixty blocks sees the chimney's smoke and a
camera a few blocks away sees the rest. `shots.json` carries both views -- they are not evidence the
smoke works, only a record of where the four places are.

    python -m scenes.obs_mot_smoke        writes shots.json from the layout
"""
from artkit.blocks import st
from artkit.canvas import Canvas

from scenes.obs import materials
from scenes.obs.common import blocks as B
from scenes.obs.motion import smoke

BIOME = "obs_blue"
CATEGORY = "motion"
TIME = 14000

WALL = B.TUFF_BRICK.block
SHELF_Y = 0


def _shelf(c, x0, z0, x1, z1):
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            c.set(x, SHELF_Y - 1, z, WALL)


def layout(c=None):
    c = c or Canvas()
    _shelf(c, -8, -8, 24, 8)
    # a chimney stub, so the smoke has a mouth to come out of
    for y in range(SHELF_Y, SHELF_Y + 14):
        for x in range(0, 4):
            for z in range(-2, 2):
                if x in (0, 3) or z in (-2, 1):
                    c.set(x, y, z, WALL)
    for x in range(0, 4):
        for z in range(-2, 2):
            c.set(x, SHELF_Y + 14, z, WALL)
    # a bench for the other three places
    for x in range(12, 22):
        c.set(x, SHELF_Y, 0, WALL)
    n = 0
    # the four places, at the scene coordinates smoke.build() already reads
    points = smoke._sources()
    if "valve" in points:
        vx, vy, vz = points["valve"]
        c.set(int(vx), SHELF_Y, int(vz), WALL)
        c.set(int(vx), SHELF_Y + 1, int(vz), WALL)
    if "brushes" in points:
        bx, by, bz = points["brushes"]
        for dx in (-1, 1):
            c.set(int(bx) + dx, SHELF_Y, int(bz), WALL)
            c.set(int(bx) + dx, SHELF_Y + 1, int(bz), WALL)
    n += smoke.build(c, (0, 0, 0))
    return c, n


def build():
    c, _ = layout()
    return c


def build_models():
    return {}


def write_pack(pack_dir):
    out = materials.pack(pack_dir)
    try:
        from scenes.obs.motion import sound
        out += sound.pack(pack_dir)
    except Exception:
        pass
    return out


def shots():
    """Two views: the chimney from sixty blocks, and the three places that are seen close."""
    pts = smoke._sources()
    cx = 2.0
    cy = float(SHELF_Y + 14)
    cz = 0.0
    if "chimney" in pts:
        cx, cy, cz = pts["chimney"]
    return [
        {"name": "chimney_60", "pos": [cx, cy + 4.0, cz + 60.0],
         "look_at": [cx, cy + 6.0, cz], "time": TIME},
        {"name": "close", "pos": [17.5, float(SHELF_Y + 2.6), 7.0],
         "look_at": [17.5, float(SHELF_Y + 1.0), 0.0], "time": TIME},
    ]
