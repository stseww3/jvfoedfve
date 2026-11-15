"""A look only (preview branch): the box stand-in against the real building, cell by cell, and the
light the light line leaves in the room when the building is dressed.

    cd build && python -m scenes.obs_int_timeroom_in.report [level behind the lit windows]
"""
import sys

from artkit.canvas import Canvas

from scenes import obs_int_timeroom_in as inside
from scenes.obs import main
from scenes.obs.interiors import timeroom as T
from scenes.obs.main import shell
from scenes.obs.sky import _lightkit as L
from scenes.obs_int_timeroom import box

HEX = "0123456789abcdef"


def compare():
    real = Canvas()
    with shell.hall_open():
        main.build(real, (0, 0, 0))
    stand = Canvas()
    box.build(stand)
    diff = {}
    for x in range(0, 16):
        for y in range(4, 16):
            for z in range(T.Z0 - 1, T.Z1 + 2):
                a, b = real.b.get((x, y, z)), stand.b.get((x, y, z))
                if a != b:
                    diff.setdefault((str(a), str(b)), []).append((x, y, z))
    print("the box against the real building, x 0..15, y 4..15, z %d..%d:" % (T.Z0 - 1, T.Z1 + 1))
    if not diff:
        print("  no cell differs")
    for (a, b), cells in sorted(diff.items(), key=lambda kv: -len(kv[1])):
        print("  %4d  real %-44s box %-44s e.g. %s" % (len(cells), a, b, cells[:5]))
    print("the real building under the room, y 5, rows z -25, -24, -16, -12 (x 2..13):")
    for z in (-25, -24, -16, -12):
        print("  z%3d " % z + " | ".join(str(real.b.get((x, 5, z))).replace("minecraft:", "") for x in (2, 6, 9, 13)))
    print("... and y 4:")
    for z in (-25, -24):
        print("  z%3d " % z + " | ".join(str(real.b.get((x, 4, z))).replace("minecraft:", "") for x in (2, 6, 9, 13)))


def light(behind):
    c = inside.build(behind)
    r = c.light_report
    box_ = (T.X0 - 1, T.FLOOR_Y, T.Z0 - 1, T.X1 + 1, T.CEIL_Y, T.Z1 + 1)
    near = sorted((cell, v) for cell, v in r["placed"].items()
                  if box_[0] <= cell[0] <= box_[3] and box_[1] <= cell[1] <= box_[4] and box_[2] <= cell[2] <= box_[5])
    print("sources placed in and round the room (behind the lit windows: %s):" % (behind or "the light line's own"))
    for cell, v in near:
        print("  ", cell, v)
    for key in ("rejected", "moved", "capped", "merged", "problems", "notes"):
        rows = [row for row in r.get(key) or [] if "timeroom" in str(row)]
        if rows:
            print(key + ":", rows)
    lv = L.levels(c, (T.X0 - 2, T.FLOOR_Y, T.Z0 - 1), (T.X1 + 2, T.CEIL_Y, T.Z1 + 1))
    for y in (7, 9, 11, 13):
        print("plan at y %d, z from -25 (top) to -7, x 2..13:" % y)
        for z in range(T.Z0, T.Z1 + 1):
            print("  z%3d " % z + " ".join(HEX[lv.get((x, y, z), 0)] for x in range(T.X0, T.X1 + 1)))
    print("entities:", len(c.entities), "blocks:", len(c.b))


if __name__ == "__main__":
    compare()
    for arg in sys.argv[1:] or ["own"]:
        light(int(arg) if arg.isdigit() else None)
