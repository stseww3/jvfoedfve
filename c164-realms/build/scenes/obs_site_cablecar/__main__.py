"""python -m scenes.obs_site_cablecar (in build/): writes shots.json from shots(), so that the
arrival view follows the skeleton."""
import json
import os

from . import shots

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    path = os.path.join(HERE, "shots.json")
    rows = shots()
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("[\n" + ",\n".join(" " + json.dumps(row) for row in rows) + "\n]\n")
    print(f"{len(rows)} shots -> {path}")


if __name__ == "__main__":
    main()
