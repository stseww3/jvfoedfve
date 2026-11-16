"""python -m scenes.obs_int_clockroom: write shots.json from the scene's VIEWS, and count the light
outside the tower with the room and without it."""
import json
import os

from . import outside_light, shots


def main():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots.json")
    with open(path, "w") as fh:
        fh.write("[\n" + ",\n".join(" " + json.dumps(row) for row in shots()) + "\n]\n")
    print(f"{path}: {len(shots())} shots")
    changed = outside_light()
    if not changed:
        print("light outside the tower: the same in every cell with the room and without it")
    for cell, (without, with_room) in changed.items():
        print(f"light outside the tower: {cell} {without} without the room, {with_room} with it")


if __name__ == "__main__":
    main()
