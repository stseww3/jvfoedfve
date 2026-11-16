"""python -m scenes.obs_site_powerhouse (in build/): writes shots.json from shots(), for this scene and
for its twin, so that the locked views follow the skeleton."""
import json
import os

from . import shots

HERE = os.path.dirname(os.path.abspath(__file__))
TWIN = "obs_site_powerhouse_b"


def write(folder, rows):
    path = os.path.join(folder, "shots.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("[\n" + ",\n".join(" " + json.dumps(row) for row in rows) + "\n]\n")
    print(f"{len(rows)} shots -> {path}")


def main():
    write(HERE, shots())
    write(os.path.join(os.path.dirname(HERE), TWIN), shots())


if __name__ == "__main__":
    main()
