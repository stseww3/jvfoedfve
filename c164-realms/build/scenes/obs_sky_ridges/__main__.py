"""python -m scenes.obs_sky_ridges (in build/): writes this scene's shots.json, then prints where the
ridges stand and how high they read from the terrace.

The last part is a check, not a report: each entity's picture has to land on its own bearing at
DISTANCE, which is the one thing about a pushed-out display entity that is easy to get wrong (the
translation is in the model's own frame, and Rotation is 180 + the yaw the model faces).
"""
import json
import math
import os
import sys

import numpy as np

from artkit.gameassets import rot
from scenes.obs.common import skeleton as S
from scenes.obs.sky import ridges

from . import build, shots

CENTRE = (S.WALL_E + 0.0, S.AXIS_Z)


def _landing(canvas):
    """(silhouette, bearing it lands on, how far out) for every entity, the way the game reads it:
    the picture stands at anchor + rot_y(-Rotation) @ translation."""
    out = []
    for x, y, z, nbt in canvas.entities:
        R = float(nbt["Rotation"][0])
        tr = np.array([float(v) for v in nbt["transformation"]["translation"]])
        centre = np.array([x, y, z]) + rot("y", -R) @ tr
        bearing = math.degrees(math.atan2(centre[0] - CENTRE[0], centre[2] - CENTRE[1])) % 360.0
        out.append((nbt["item"]["components"]["minecraft:item_model"].split(":")[-1], bearing,
                    math.hypot(centre[0] - CENTRE[0], centre[2] - CENTRE[1])))
    return out


def _render_extents(assets, cells, entities):
    """The renderer's own world bounds of each entity: [(centre x, centre z)], so the check reads the
    picture the way it will actually be drawn rather than trusting the arithmetic twice."""
    out = []
    seen = []
    original = GS.Scene._entity

    def collect(self, x, y, z, nbt):
        boxes = original(self, x, y, z, nbt)
        if boxes:
            lo = np.array([b["lo_w"] for b in boxes])
            hi = np.array([b["hi_w"] for b in boxes])
            seen.append(((lo[:, 0].min() + hi[:, 0].max()) / 2.0,
                         (lo[:, 2].min() + hi[:, 2].max()) / 2.0))
        return boxes

    GS.Scene._entity = collect
    try:
        for ent in entities:
            GS.Scene(assets, dict(cells), [ent], {}, place=(0, 200, 0))
    finally:
        GS.Scene._entity = original
    return seen

def main():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("[\n" + ",\n".join(" " + json.dumps(shot) for shot in shots()) + "\n]\n")
    print(f"{len(shots())} shots -> {path}\n")

    canvas = build()
    print(f"ridges: {len(canvas.entities)} display entities, DISTANCE {ridges.DISTANCE:.0f} cells")
    print(f"(ceiling {ridges.MAX_ANGLE} degrees from the terrace)")
    for key, bearing, tall, elev in ridges.peaks():
        print(f"  {key}: bearing {bearing:5.1f}, tallest {tall:5.1f} cells, elevation {elev:4.2f} degrees")

    problems = []
    landing = _landing(canvas)
    for (key, bearing, dist), (_, want, _, _) in zip(landing, ridges.peaks()):
        if abs(((bearing - want + 180.0) % 360.0) - 180.0) > 2.0:
            problems.append(f"{key}: lands on bearing {bearing:.1f}, wanted {want:.1f}")
        if abs(dist - ridges.DISTANCE) > 8.0:
            problems.append(f"{key}: lands {dist:.0f} cells out, wanted {ridges.DISTANCE:.0f}")
    covered = sorted(round(b) for _, b, _ in landing)
    west_open = all(abs(b - 270.0) > 20.0 for b in covered)
    print(f"  bearings with hills: {covered}; the west (270) is open: {west_open}")
    if not west_open:
        problems.append("a panel stands in the west, where the afterglow has to be clear")
    for key, _, tall, elev in ridges.peaks():
        if elev > ridges.MAX_ANGLE:
            problems.append(f"{key}: {elev:.2f} degrees, over the {ridges.MAX_ANGLE} ceiling")
    if not 3 <= len(canvas.entities) <= 6:
        problems.append(f"{len(canvas.entities)} panels, the card asks for 3 to 6")

    for p in problems:
        print(f"PROBLEM: {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
