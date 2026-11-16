"""obs_props_steam: what the pictures cannot be trusted to show.

    python -m scenes.obs_props_steam.fit            (in build/)

Every model of the package is held to the kit's K.settle (no face stands between two axes: the game
and the offline pictures then light it alike), and the heating main of the east front is measured
against the stones it runs along: nothing of it in the door's bays, nothing in the two corners the
rainwater pipes stand in, the bend round the pilaster clear of the heads of those who walk under it.
"""
import sys

from scenes import obs_props_steam as scene
from scenes.obs.common import skeleton as S
from scenes.obs.main import _plan as P
from scenes.obs.props import _kit as K
from scenes.obs.props import pipes, steam

DOOR_Z = (-3.0, 4.0)        # the door's bays (review c332): no pipe between these
CORNER = 0.5                # a rainwater pipe's corner: no piece of the main nearer to the return wall than this
HEAD = 2.0                  # what stands over the paving is at least this far over it


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
        name = str(nbt.get("item", {}).get("components", {}).get("minecraft:item_model", ""))
        if steam.PREFIX in name or (pipes.PREFIX in name and abs(y - steam.front_line()[1]) < 0.5):
            mine.append((name.split(":")[-1], x, y, z))
    if not mine:
        found.append("the heating main is not in the scene: steam.east_front() placed nothing")
    reach = (pipes.BORE[steam.SIZE] + 2.0) / 16.0           # a flange's radius: the widest piece on the axis
    south, north = P.PAVILION_Z[1] - CORNER, P.CROSS_Z[1] + 1.0 + CORNER
    face = S.WALL_E + 1.0 + S.DEPTH_PILASTER                # the plane of the pilasters' faces: the plinth ends there
    for name, x, y, z in mine:
        if DOOR_Z[0] - reach < z < DOOR_Z[1] + reach:
            found.append(f"{name} at ({x:.2f}, {y:.2f}, {z:.2f}) stands in the door's bays")
        if z + reach > south or z - reach < north:
            found.append(f"{name} at ({x:.2f}, {y:.2f}, {z:.2f}) stands in a rainwater pipe's corner")
        if x > face and y - reach < S.GROUND + HEAD - 1e-6:
            found.append(f"{name} at ({x:.2f}, {y:.2f}, {z:.2f}) hangs over the paving lower than {HEAD} blocks")
    zs = [z for _, _, _, z in mine] or [0.0]
    print(f"{len(models)} models, {sum(len(m.parts) for m in models.values())} parts; the heating main: {len(mine)} pieces "
          f"from z {max(zs):.2f} to z {min(zs):.2f}: " + ("nothing found" if not found else f"{len(found)} found"))
    for line in found:
        print("  " + line)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
