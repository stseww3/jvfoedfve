"""Where do the display entities fall in a shot's frame? Run in build/ with PYTHONPATH=.:/tmp/c164_lamps

    python entframe.py <scene> <shot> [substring of the model's name]
"""
import importlib
import sys

from inframe import camera, W, H


def main():
    scene, shot_name = sys.argv[1], sys.argv[2]
    want = sys.argv[3] if len(sys.argv) > 3 else ""
    mod = importlib.import_module("scenes." + scene)
    canvas = mod.build()
    shot = next(s for s in mod.shots() if s["name"] == shot_name)
    px = camera(shot["pos"], shot["look_at"])
    print("shot", shot_name, "pos", shot["pos"], "look_at", shot["look_at"])
    for x, y, z, nbt in canvas.entities:
        name = nbt["item"]["components"]["minecraft:item_model"].split(":")[-1]
        if want not in name:
            continue
        p = px((x, y, z))
        if p is None:
            continue
        inside = 0 <= p[0] < W and 0 <= p[1] < H
        if inside or (-200 <= p[0] < W + 200 and -200 <= p[1] < H + 200):
            print(f"  {name:28s} ({x:6.2f}, {y:5.2f}, {z:6.2f}) -> px ({p[0]:5.0f}, {p[1]:5.0f}) {'in ' if inside else 'OUT'} {p[2]:.1f} off")


if __name__ == "__main__":
    main()
