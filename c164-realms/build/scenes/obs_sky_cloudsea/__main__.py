"""Writes shots.json and trials.json of this test scene from the skeleton's cameras:
python -m scenes.obs_sky_cloudsea"""
import json
import os

from . import shots, trial_shots

if __name__ == "__main__":
    for name, rows in (("shots.json", shots()), ("trials.json", trial_shots())):
        path = os.path.join(os.path.dirname(__file__), name)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in rows) + "\n]\n")
        print(f"{len(rows)} shots -> {path}")
