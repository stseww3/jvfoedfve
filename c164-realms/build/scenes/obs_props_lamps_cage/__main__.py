"""Writes shots.json of the cage-A comparison scene:
    python -m scenes.obs_props_lamps_cage"""
import json
import os

from . import CHOICES, build, build_models, shots

if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "shots.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n")
    print(f"{len(shots())} shots -> {path}")
    print("models:", ", ".join(sorted(build_models())))
    print("choices:", ", ".join(f"{name} = {choice}" for name, choice in CHOICES))
    c = build()
    print("display entities:", c.entity_counts)
