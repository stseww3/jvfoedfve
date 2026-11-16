"""python -m scenes.obs_mot_guide_title (in build/): writes shots.json from shots(), and says what
the title's two lines measure and where the credit plate falls in the arrival view."""
import json
import os

from scenes.obs.common import skeleton as S
from scenes.obs.motion import guide_title as G

from . import plate_corners, shots, where

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    path = os.path.join(HERE, "shots.json")
    rows = shots()
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("[\n" + ",\n".join(" " + json.dumps(row) for row in rows) + "\n]\n")
    print(f"{len(rows)} shots -> {path}")
    for part, room in zip(G.MAP_TITLE, (G.TITLE_ROOM, G.SUB_ROOM)):
        print(f"  {part!r}: {G.width(part)} pixels of the font, room for {room}")
    for wrong in G.misfits():
        print("  NOT SHOWN WHOLE: " + wrong)
    marks = [where(S.V1, corner) for corner in plate_corners()]
    inside = [m for m in marks if m is not None and abs(m[0]) <= 1.0 and abs(m[1]) <= 1.0]
    print("  the plate's corners in the arrival view (x, y from -1 to 1; outside when beyond): "
          + "  ".join("behind" if m is None else f"({m[0]:+.2f}, {m[1]:+.2f})" for m in marks))
    print(f"  {len(inside)} of them in the picture")


if __name__ == "__main__":
    main()
