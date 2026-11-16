"""python -m scenes.obs_int_clockroom: write shots.json of the scene and of its twin without the
room from the scene's VIEWS, and count the light outside the tower with the room and without it."""
import json
import os

from scenes import obs_int_clockroom_bare as bare

from . import outside_light, shots


def write(folder, rows):
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), folder, "shots.json")
    with open(path, "w") as fh:
        fh.write("[\n" + ",\n".join(" " + json.dumps(row) for row in rows) + "\n]\n")
    print(f"{path}: {len(rows)} shots")


def main():
    write("obs_int_clockroom", shots())
    write("obs_int_clockroom_bare", bare.shots())
    changed = outside_light()
    if not changed:
        print("light outside the tower: the same in every cell with the room and without it")
    for cell, (without, with_room) in changed.items():
        print(f"light outside the tower: {cell} {without} without the room, {with_room} with it")


if __name__ == "__main__":
    main()
