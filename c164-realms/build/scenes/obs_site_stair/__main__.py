"""python -m scenes.obs_site_stair (in build/): writes shots.json from shots(), for this scene and
for the two that repeat its judged views, so that the arrival view follows the skeleton."""
import json
import os

from . import JUDGED, shots

HERE = os.path.dirname(os.path.abspath(__file__))
REPEATS = ("obs_site_stair_noband", "obs_site_stair_nolamps")


def write(folder, rows):
    path = os.path.join(folder, "shots.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("[\n" + ",\n".join(" " + json.dumps(row) for row in rows) + "\n]\n")
    print(f"{len(rows)} shots -> {path}")


def main():
    write(HERE, shots())
    for name in REPEATS:
        write(os.path.join(os.path.dirname(HERE), name), shots(JUDGED))


if __name__ == "__main__":
    main()
