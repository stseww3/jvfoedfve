"""Where every display entity of a scene stands: its model, anchor, the way it looks, the block
behind a wall piece and the cell it hangs in. No pictures; for a scene that was never drawn."""
import math, sys, importlib
scene = importlib.import_module("scenes." + sys.argv[1])
c = scene.build()
OUT = {0: ("south", (0, 0, 1)), 90: ("west", (-1, 0, 0)), 180: ("north", (0, 0, -1)), 270: ("east", (1, 0, 0))}
rows = []
for x, y, z, nbt in c.entities:
    name = nbt["item"]["components"]["minecraft:item_model"].split(":")[1]
    yaw = (float(nbt["Rotation"][0]) - 180.0) % 360.0
    sc = [float(v) for v in nbt["transformation"]["scale"]]
    k = int(round(yaw / 90.0)) % 4 * 90 if abs(yaw / 90.0 - round(yaw / 90.0)) < 1e-6 else None
    here = (math.floor(x), math.floor(y), math.floor(z))
    note = ""
    if k is not None:
        facing, d = OUT[k]
        behind = (math.floor(x - d[0] * 0.5), math.floor(y), math.floor(z - d[2] * 0.5))
        note = f"{facing:5} behind {c.get(*behind) or 'AIR':28.28} here {c.get(*here) or 'air'}"
    else:
        note = f"yaw {yaw:.1f} here {c.get(*here) or 'air'}"
    br = nbt.get("brightness")
    rows.append(f"{name:26} ({x:7.2f},{y:6.2f},{z:7.2f}) scale {sc[0]:.2f},{sc[1]:.2f},{sc[2]:.2f} {note}" + (f" bright {br}" if br else ""))
print("\n".join(rows))
print(len(rows), "entities")
