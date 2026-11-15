"""Writes shots.json of this test scene, of its twin and of the slit's scene:  python -m scenes.obs_main_dome"""
import json
import os

from scenes import obs_main_dome_slit

from . import shots

if __name__ == "__main__":
    here = os.path.dirname(__file__)
    for folder, listed in ((here, shots()), (here + "_b", shots()), (here + "_slit", obs_main_dome_slit.shots())):
        path = os.path.join(folder, "shots.json")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in listed) + "\n]\n")
        print(f"{len(listed)} shots -> {path}")
