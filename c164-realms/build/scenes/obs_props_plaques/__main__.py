"""Writes shots.json of this test scene from the stage's numbers:  python -m scenes.obs_props_plaques
With --report it prints how every plaque is set: the name's size, the lines of the sentence and
their widths in font pixels, and the number of display entities."""
import json
import os
import sys

from scenes.obs.props import plaques

from . import CREDIT, build, shots

if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "shots.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n")
    print(f"{len(shots())} shots -> {path}")
    if "--report" in sys.argv[1:]:
        for key, (name, sentence) in list(plaques.TEXT.items()) + [("(credit)", CREDIT)]:
            rows = plaques.layout(name, sentence)
            print(f"  {key:16s} name {plaques.width(name):3d} px at {rows[0][1] / plaques.NAME_PX:.2f} of its size; "
                  + " | ".join(f"{words} ({plaques.width(words)})" for words, *_ in rows[1:]))
        print("display entities:", build().entity_counts)
