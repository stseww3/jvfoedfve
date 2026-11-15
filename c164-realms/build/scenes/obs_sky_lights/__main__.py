"""python -m scenes.obs_sky_lights (in build/): writes this scene's shots.json, then prints what the
lights came to: the report of sky/lights, the lighting map of each look, and the block light that
reaches the stone round the windows of the levels board, round the entrance and at the wall wash."""
import json
import os

from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.sky import _lightkit as L
from scenes.obs.sky import lights

from . import BOARD, BOARD_LEVELS, STATIONS, WING_X, build, shots


def surround(canvas, o, wall, bay):
    """The block light on the stone round a bay's great window: the highest level and the least,
    for each kind of face. A face shows the light of the cell in front of it."""
    zc = S.bay_center_z(bay)
    y0, y1 = S.WINDOW
    lo = (o[0] + wall - 3, o[1] + S.PANEL - 2, o[2] + zc - 4)
    hi = (o[0] + wall + 4, o[1] + S.CORNICE + 1, o[2] + zc + 4)
    lv = L.levels(canvas, lo, hi)

    def span(cells):
        got = []
        for x, y, z in cells:
            cell = (o[0] + x, o[1] + y, o[2] + z)
            if not canvas.has(*cell) or canvas.name(*cell) == B.LIGHT:
                got.append(lv.get(cell, 0))
        return f"{max(got):>2} (least {min(got)})" if got else " -"

    rows = range(y0, y1 + 1)
    return {
        "jamb": span([(wall, y, zc - 1) for y in rows]),
        "sill": span([(wall, y0, z) for z in (zc - 1, zc, zc + 1)]),
        "pilaster side": span([(wall + 1, y, zc - 1) for y in rows]),
        "pilaster front": span([(wall + 2, y, z) for y in rows for z in (zc - 2, zc + 2)]),
        "panel under it": span([(wall + 1, S.PANEL, z) for z in (zc - 1, zc, zc + 1)]),
        "frieze over it": span([(wall + 1, S.FRIEZE, z) for z in (zc - 1, zc, zc + 1)]),
    }


def main():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("[\n" + ",\n".join(" " + json.dumps(shot) for shot in shots()) + "\n]\n")
    print(f"{len(shots())} shots -> {path}\n")

    canvas = build()
    print("\n".join(lights.summary(canvas)))
    table = L._main_keys() or ()
    for name in STATIONS:
        tiers = L.tiers(table, name)
        n = L.counts(tiers)
        print(f"\n{name}: dark {n[0]}, dim {n[1]}, lit {n[2]}, bright {n[3]} of {sum(n)} "
              f"({100.0 * n[0] / max(sum(n), 1):.0f}% dark); lit neighbours: {L.lit_neighbours(tiers) or 'none'}")
        print(L.chart(tiers))
    print("\nblock light on the stone round a great window (highest of its rows, and the least):")
    for bay, level in BOARD_LEVELS.items():
        print(f"  {level} behind the glass: "
              + "; ".join(f"{k} {v}" for k, v in surround(canvas, BOARD, WING_X, bay).items()))
    o = STATIONS["blue"]
    wall = S.east_wall_x(9)
    print("  blue, over the door:   " + "; ".join(f"{k} {v}" for k, v in surround(canvas, o, wall, 9).items()))
    lv = L.levels(canvas, (o[0] + wall - 9, o[1], o[2] - 8), (o[0] + wall + 12, o[1] + 8, o[2] + 8))
    row = [lv.get((o[0] + x, o[1], o[2]), 0) for x in range(wall - 8, wall + 12)]
    print(f"\nblue, on the ground along the axis, x {wall - 8}..{wall + 11} (the wall face is x {wall}): "
          + " ".join(str(v) for v in row))
    for x, what in ((wall + 1, "the door's jambs at the pilaster plane"), (wall - 5, "five cells behind the wall line")):
        print(f"blue, {what} (x {x}), rows y 6..0, z -6..6:")
        for y in range(6, -1, -1):
            print("   " + " ".join(f"{lv.get((o[0] + x, o[1] + y, o[2] + z), 0):>2}" for z in range(-6, 7)))
    bay = lights.WASH_BAYS[0]
    wall, zc = S.east_wall_x(bay), S.bay_center_z(bay)
    lv = L.levels(canvas, (o[0] + wall - 2, o[1] - 1, o[2] + zc - 6), (o[0] + wall + 6, o[1] + 9, o[2] + zc + 6))
    print(f"blue, the wall wash of bay {bay}, block light before the wall (x {wall + 1}), rows y 7..0, z {zc - 2}..{zc + 2} "
          f"(the pilasters' rows show the light before their fronts, x {wall + 2}):")
    for y in range(7, -1, -1):
        cells = [(wall + (2 if abs(dz) == 2 else 1), y, zc + dz) for dz in range(-2, 3)]
        print("   " + " ".join(f"{lv.get((o[0] + x, o[1] + yy, o[2] + z), 0):>2}" for x, yy, z in cells))


if __name__ == "__main__":
    main()
