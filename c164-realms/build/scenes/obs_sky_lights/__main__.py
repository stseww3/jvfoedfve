"""python -m scenes.obs_sky_lights (in build/): writes this scene's shots.json, then prints what the
lights came to: the report of sky/lights, the lighting map of each look, and the block light that
reaches the stone round the windows of the levels board, round a lit window of a wing, round the
entrance, on the ground at the foot of a street lamp and on the washed pilasters (of the building,
and of the buildings that try another level)."""
import json
import os

from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.sky import _lightkit as L
from scenes.obs.sky import lights

from . import BOARD, BOARD_LEVELS, STATIONS, SURROUND_BAY, VARIANTS, WING_X, build, shots


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
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "shots.json")
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
    stood = [("blue", o)] + [(name, at) for name, (_, at, numbers, _) in VARIANTS.items() if "BEHIND" in numbers]
    for name, at in stood:
        print(f"  {name + ', bay ' + str(SURROUND_BAY) + ':':<22} "
              + "; ".join(f"{k} {v}" for k, v in surround(canvas, at, S.east_wall_x(SURROUND_BAY), SURROUND_BAY).items()))
    wall = S.east_wall_x(9)
    print("  blue, over the door:   " + "; ".join(f"{k} {v}" for k, v in surround(canvas, o, wall, 9).items()))
    beside = lights.ENTRANCE_BAYS[-1]       # its jamb and pilaster side of surround() are the ones towards the door
    print(f"  blue, beside the door (bay {beside}): "
          + "; ".join(f"{k} {v}" for k, v in surround(canvas, o, S.east_wall_x(beside), beside).items()))
    lv = L.levels(canvas, (o[0] + wall - 9, o[1], o[2] - 8), (o[0] + wall + 12, o[1] + 8, o[2] + 8))
    row = [lv.get((o[0] + x, o[1], o[2]), 0) for x in range(wall - 8, wall + 12)]
    print(f"\nblue, on the ground along the axis, x {wall - 8}..{wall + 11} (the wall face is x {wall}): "
          + " ".join(str(v) for v in row))
    r = lights.report(canvas)
    for foot in sorted(cell for cell in r["pools"] if cell[0] > o[0] - 100):
        lv = L.levels(canvas, (foot[0] - 8, foot[1], foot[2] - 1), (foot[0] + 8, foot[1] + 6, foot[2] + 1))
        row = [lv.get((foot[0] + d, foot[1], foot[2]), 0) for d in range(-7, 8)]
        print(f"blue, on the ground through the foot of the street lamp at {foot} (a pool of {L.POOL} there), "
              f"x {foot[0] - 7}..{foot[0] + 7}: " + " ".join(str(v) for v in row))
    for x, what in ((wall + 1, "the door's jambs at the pilaster plane"), (wall - 5, "five cells behind the wall line")):
        print(f"blue, {what} (x {x}), rows y 6..0, z -6..6:")
        for y in range(6, -1, -1):
            print("   " + " ".join(f"{lv.get((o[0] + x, o[1] + y, o[2] + z), 0):>2}" for z in range(-6, 7)))
    north = [S.pilaster_z(k) for k in lights.WASH_PILASTERS if k < lights.DOOR_BAY]
    z0, z1 = min(north) - 2, S.pilaster_z(lights.DOOR_BAY - 2)      # from the bay beyond the wash to the entrance's corner
    wall, top = S.east_wall_x(lights.WASH_PILASTERS[0]), S.WINDOW[0] + 3
    washed = [("blue", o, L.WASH)]
    washed += [(name, at, numbers["WASH"]) for name, (_, at, numbers, _) in VARIANTS.items() if "WASH" in numbers]
    for name, at, level in washed:
        lv = L.levels(canvas, (at[0] + wall - 2, at[1] - 1, at[2] + z0 - 6),
                      (at[0] + wall + 8, at[1] + top + 4, at[2] + z1 + 6))
        print(f"{name}, the wall wash of the north wing at {level}: the block light on the front's faces (the cell "
              f"before the outermost block of each line: stone, the bars of a small window, the glass of a great "
              f"one), rows y {top}..0, z {z0}..{z1}; pilasters at z "
              f"{', '.join(str(z) for z in range(z0, z1 + 1) if (z - S.PIL_Z0) % S.BAY == 0)}:")
        for y in range(top, -1, -1):
            row = []
            for z in range(z0, z1 + 1):
                line = [(at[0] + x, at[1] + y, at[2] + z) for x in range(wall + 6, wall - 3, -1)]
                face = next((i for i, cell in enumerate(line)
                             if canvas.has(*cell) and canvas.name(*cell) != B.LIGHT), None)
                row.append(" ." if not face else f"{lv.get(line[face - 1], 0):>2}")
            print(f"   y {y:>2}  " + " ".join(row))


if __name__ == "__main__":
    main()
