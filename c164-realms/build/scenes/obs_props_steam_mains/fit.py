"""obs_props_steam_mains: what the pictures cannot be trusted to show.

    python -m scenes.obs_props_steam_mains.fit            (in build/)

Every model of the package is held to the kit's K.settle (no face stands between two axes: the game
and the offline pictures then light it alike), and the heating main of the east front is measured
against the stones it runs along: nothing of it in the door's bays, nothing in the two corners the
rainwater pipes stand in, the bend round the pilaster clear of the heads of those who walk under it.
"""
import sys

from artkit import models as M
from scenes import obs_props_steam_mains as scene
from scenes.obs.common import skeleton as S
from scenes.obs.main import _plan as P
from scenes.obs.props import _kit as K
from scenes.obs.props import steam_mains as steam

DOOR_Z = (-3.0, 4.0)        # the door's bays (review c332): no pipe between these
CORNER = 0.5                # a rainwater pipe's corner: no piece of the main nearer to the return wall than this
HEAD = 2.0                  # what stands over the paving is at least this far over it
REACH = 3.0                 # blocks: no piece of the main is longer


def _over(model, x, y):
    """The corners of every part of a piece that stands at (x, y): (x, y) of each, in blocks."""
    for part in model.parts:
        c = [(part["lo"][i] + part["hi"][i]) / 2.0 for i in range(3)]
        h = [(part["hi"][i] - part["lo"][i]) / 2.0 for i in range(3)]
        q = part["rot"][0] if part["rot"] else M.IDENT
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    v = M._qrot(q, (sx * h[0], sy * h[1], sz * h[2]))
                    yield x + (c[0] + v[0]) / 16.0, y + (c[1] + v[1]) / 16.0


def main():
    found = []
    models = steam.models()
    for name, model in sorted(models.items()):
        for i, letters, normal in K.unsettled(model):
            found.append(f"{name}: part {i}, faces {letters} stand between two axes "
                         f"({normal[0]:.4f}, {normal[1]:.4f}, {normal[2]:.4f})")
    canvas = scene.build()
    mine = []
    for x, y, z, nbt in canvas.entities:
        name = str(nbt.get("item", {}).get("components", {}).get("minecraft:item_model", "")).split(":")[-1]
        if name in models:
            mine.append((name, x, y, z))
    if not mine:
        found.append("the heating main is not in the scene: steam.east_front() placed nothing")
    south, north = P.PAVILION_Z[1] - CORNER, P.CROSS_Z[1] + 1.0 + CORNER
    face = S.WALL_E + 1.0 + S.DEPTH_PILASTER                # the plane of the pilasters' faces: the plinth ends there
    for name, x, y, z in mine:
        lo, hi = models[name].reach()                       # the piece as it is seen, in texels from its anchor
        z0, z1 = z + lo[2] / 16.0, z + hi[2] / 16.0
        if z0 < DOOR_Z[1] and z1 > DOOR_Z[0]:
            found.append(f"{name} at ({x:.2f}, {y:.2f}, {z:.2f}) stands in the door's bays")
        if z1 > south or z0 < north:
            found.append(f"{name} at ({x:.2f}, {y:.2f}, {z:.2f}) stands in a rainwater pipe's corner")
        if z1 - z0 > REACH + 1e-6:
            found.append(f"{name} is {z1 - z0:.2f} blocks long")
        low = min((py for px, py in _over(models[name], x, y) if px > face + 1e-6), default=None)
        if low is not None and low < S.GROUND + HEAD - 1e-6:
            found.append(f"{name} at ({x:.2f}, {y:.2f}, {z:.2f}) hangs over the paving at y {low:.2f}, lower than "
                         f"{HEAD} blocks over it")
    zs = [z for _, _, _, z in mine] or [0.0]
    print(f"{len(models)} models, {sum(len(m.parts) for m in models.values())} parts; the heating main: {len(mine)} pieces, "
          f"anchors from z {max(zs):.2f} to z {min(zs):.2f}: " + ("nothing found" if not found else f"{len(found)} found"))
    for line in found:
        print("  " + line)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
