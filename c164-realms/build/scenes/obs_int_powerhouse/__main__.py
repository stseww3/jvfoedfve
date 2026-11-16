"""python -m scenes.obs_int_powerhouse: write shots.json from the scene's VIEWS."""
import json
import os

from . import shots


def main():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots.json")
    with open(path, "w") as fh:
        fh.write("[\n" + ",\n".join(" " + json.dumps(row) for row in shots()) + "\n]\n")
    print(f"{path}: {len(shots())} shots")


if __name__ == "__main__":
    main()
