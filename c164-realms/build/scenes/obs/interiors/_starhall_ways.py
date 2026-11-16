"""interiors/_starhall_ways -- the light on the ways of the star hall where its lamps leave less
than the line asks. A part of interiors/starhall (its PARTS), which calls dress() at the end of
its own and adds models() to its models; the underscore keeps the file out of the category's
auto-discovery. It adds lamps and light sources and nothing else (A0, 11-16 10:43).

The line: a place a person stands at has 5 or more, read as tools/darkfloor.py reads it (the
better of the cell of the feet and the cell of the head; the tops of the galleries' railings are
such places, reached with a hop). The list of the assembly 9fbb2e0c names sixteen places of the
hall at 3 and 4, and the hall gave the west end of both galleries with them (c348, 10:58):

  the south gallery between its first two lamps     (5..6, 7, 5) and the railing's top (8, 8, 4)
  the north gallery between the wing room's doors   (8, 7, -5)
  the east end of both galleries                    (14..15, 7, -5 and 5), the railing's top beside it
  the west end of both galleries                    (2..3, 7, -5 and 5), the south railing's top beside it
  the west corners of the two aisles                (2, 0, -5 and 5)
  the floor beside the roundel                      (9, 0, -3 and 3)

What the hall keeps (c348, 11-16): its lamps stay at 6 to 8 and no source here is over 8; each is
as low as leaves 5 in the places it is for. The orrery's sun stays the hall's one warm core: the
sources of the floor stand in the row of a walker's head, so the floor under them is no lighter
than it was. The windows of the east wall are to look dark from inside: the two new lamps hang on
the cross walls, a cell clear of the east wall. The floor before the door (x 12 and further east)
gets nothing.

A source stands in the row of a walker's head: a lamp three rows over a head has lost three levels
by the time it is down there. Two caged lamps are new, the fourth of each gallery wall, as high as
the other three and as far from the third as that is from the second; every other source stands
within reach of a lamp the hall has hung already.

The first look through the open door (A0 #83714, review #83800 and #85249, cr3 #87129). The board's
picture from the forecourt (V4) sees into the hall through the half of the doorway its iron gate
leaves free, x 602..640 of 1280: the north flight behind its side arch, the wall over it, and the
floor from the door to the arcade. That half is to read 0.22 and warm; on the save of 12:00 it was
at 0.188, the flight at 0.21 and the floor at 0.156 and grey. What the hall's own picture (V7)
asks of the same things: the pier's face beside the mother clock at 0.255 to 0.26, the two flights
alike and under it (0.235 at most), the dark linings of the doorway under 0.12, no new lamp to be
seen. So:

  the floor       two pairs of sources in the row of a walker's head, either side of the meridian
                  and clear of the roundel's middle, which keeps the sun's pool and no more (A0:
                  the floor's middle stays darker than the clock's dial). The east pair is the
                  lower: it is the nearer to the doorway's linings
  the stair foot  the hall raises its two lamps by one (starhall.STAIR_FOOT_LEVEL); the corner
                  sources before the first step go with them, one under the lamp: the first riser
                  was two levels under the four over it and is now one over them
  the pier        two sources beside the clock's dial on either side, in the row of the clock's
                  own lamp and two rows over it: the face's two outer columns go up by one level
                  and by two at their head, the dial has its own light

What that comes to, read by obs_int_starhall/doorway.py in the hall's test scene (traced without
the game; the hall of the 12:00 save reads 0.183 there where the game showed 0.188, the pier's
face 0.231 for 0.232, the flights 0.209 for 0.213, the linings 0.071 for 0.088):

                        the 12:00 save    now
  V4, the half          0.183 (+0.039)    0.216 (+0.082)
  V7, the pier's face   0.233, 0.229      0.254, 0.251
  V7, the two flights   0.211, 0.207      0.232, 0.228
  V7, the linings       0.071             0.091, 0.087

One level less anywhere is 0.004 to 0.005 less in the half; one more on the pier is 0.267, over
its line. The half's girder, the crown of the arch under it and the slate before the flight
(a quarter of the half between them) stay under 0.19 whatever the lamps.

The limits this part kept before (no source over 8, nothing before the door) were the hall's for
the hall's own picture; the director's order for the board's goes before them, and the three
sources that are over 8 now are asked for in the second rank.

    env PYTHONPATH=build python -m scenes.obs.interiors._starhall_ways [<folder>]     (from c164-realms/, on a worker node)

builds the master scene and tells what sky/lights made of every source asked for here and what
light the places they are for have; PASS or FAIL in the last line.
"""
from ..main import shell
from ..props import lamps
from ..sky import _lightkit as L

WHY = "interiors/starhall"
ROOM = shell.ROOMS["star hall"]
X0, Z0, X1, Z1 = ROOM["box"]                    # 2, -5, 15, 5
FEET = ROOM["feet"]                             # 0
DECK = shell.DECK_Y + 1                         # 7: where one stands on a gallery
HEAD = 1                                        # the row of a walker's head over the row of his feet

LAMP_Y = 10.5                                   # the galleries' caged lamps (interiors/starhall.GALLERY_LAMP_Y)
END_LAMP_X = 14.5                               # the fourth lamp of a gallery wall
END_LEVEL = 7                                   # under it: 6 beside it on the walk, 5 on the railing's top at the wall
RAIL_LEVEL = 7                                  # over the south railing, between the lamps at 4.5 and 8: 5 two cells off
WEST_LEVEL = 6                                  # beside the first lamp's foot: 5 in the gallery's last cell
CORNER_UNDER = 1                                # an aisle's corner cell holds the dado's panel: the source stands in the
#                                                 row before it, which is the cell before the flight's first step. It is
#                                                 this far under the stair foot's lamp: the first two risers then have one
#                                                 level more than the lamp gives the three over them (the 6 it had left 5
#                                                 at the head of who stands in the corner, and the first riser at 6 of 8)
FILL = 5                                        # in the cell of the head of the place it is for, and no further

# the first look through the door (the head of this file)
DOOR_EAST = (12, 1)                             # the floor's east pair: x, and the rows off the meridian's cell (z 0)
DOOR_EAST_LEVEL = 10                            # 9 under it, 8 beside; 6 and 5 by the time it is at the doorway's linings
DOOR_WEST = (9, 2)                              # the west pair: on the roundel's ring, towards the arcade
DOOR_WEST_LEVEL = 11
PIER_SIDE = (7, 3, 1)                           # beside the dial: x (the cell before the pier's face), y, rows off the axis
PIER_SIDE_LEVEL = 11                            # the clock's lamp between them has 11 too: the outer columns get what the
#                                                 middle one has
PIER_UPPER = 5                                  # a second row of the same, two rows higher: the head of the rough courses
PIER_UPPER_LEVEL = 11

def corner_level():
    """The level of the two sources before the flights' first steps: it follows the stair foot's lamps."""
    from . import starhall
    return max(FILL, starhall.STAIR_FOOT_LEVEL - CORNER_UNDER)


def sources():
    """(the cell, its level, what it lights): building coordinates. Read when the hall is dressed,
    so that a comparison may set the levels above first."""
    corner = corner_level()
    out = [
        ((6, DECK + HEAD, Z1 - 1), RAIL_LEVEL, "south gallery"),
        ((8, DECK + HEAD, Z0), FILL, "north gallery"),
        ((int(END_LAMP_X), DECK + HEAD, Z0), END_LEVEL, "north gallery end"),
        ((int(END_LAMP_X), DECK + HEAD, Z1), END_LEVEL, "south gallery end"),
        ((X0 + 1, DECK + HEAD, Z0), WEST_LEVEL, "north gallery west"),
        ((X0 + 1, DECK + HEAD, Z1), WEST_LEVEL, "south gallery west"),
        ((X0, DECK + HEAD, Z1 - 1), FILL, "south railing west"),
        ((X0, FEET + HEAD, Z0 + 1), corner, "north aisle corner"),
        ((X0, FEET + HEAD, Z1 - 1), corner, "south aisle corner"),
        ((9, FEET + HEAD, -3), FILL, "roundel north"),
        ((9, FEET + HEAD, 3), FILL, "roundel south"),
    ]
    for side, sign in (("north", -1), ("south", 1)):
        if DOOR_EAST_LEVEL:
            out.append(((DOOR_EAST[0], FEET + HEAD, sign * DOOR_EAST[1]), DOOR_EAST_LEVEL, f"door floor east {side}"))
        if DOOR_WEST_LEVEL:
            out.append(((DOOR_WEST[0], FEET + HEAD, sign * DOOR_WEST[1]), DOOR_WEST_LEVEL, f"door floor west {side}"))
        if PIER_SIDE_LEVEL:
            out.append(((PIER_SIDE[0], FEET + PIER_SIDE[1], sign * PIER_SIDE[2]), PIER_SIDE_LEVEL, f"pier face {side}"))
        if PIER_UPPER_LEVEL:
            out.append(((PIER_SIDE[0], FEET + PIER_UPPER, sign * PIER_SIDE[2]), PIER_UPPER_LEVEL, f"pier face upper {side}"))
    return tuple(out)


LINE = 5
# the places the sources are for, by the cell of the feet: the sixteen of the list and the galleries' west end
PLACES = (
    (5, 7, 5), (6, 7, 5), (8, 8, 4), (8, 7, -5),
    (14, 7, -5), (15, 7, -5), (14, 8, -4), (15, 8, -4), (14, 7, 5), (15, 7, 5), (14, 8, 4), (15, 8, 4),
    (2, 7, -5), (3, 7, -5), (2, 7, 5), (3, 7, 5),
    (2, 0, -5), (2, 0, 5), (9, 0, -3), (9, 0, 3),
)
# the tops of the south railing beside them, which the list gives to the light line and these sources reach
BESIDE = ((2, 8, 4), (3, 8, 4), (5, 8, 4), (6, 8, 4), (7, 8, 4))


def models():
    return {}


def dress(canvas, origin=(0, 0, 0), version="a"):
    """Hang the two lamps and ask the light line for the sources; returns the display entities placed."""
    ox, oy, oz = origin
    n = 0
    for z, facing in ((float(Z0), "south"), (Z1 + 1.0, "north")):
        n += lamps.place(canvas, "cage", (END_LAMP_X, LAMP_Y, z), facing=facing, origin=origin, version=version,
                         light=False)
    for (x, y, z), level, what in sources():
        L.suggest(canvas, (ox + x, oy + y, oz + z), level, f"{WHY}:way {what}", rank=L.rank(level))
    return n


def main(folder=None):
    """Build the master scene; say what sky/lights made of every source asked for here and what
    light the places they are for have now. With a folder, the same goes into
    obs-starhall-ways.txt there."""
    import os

    from .. import build
    from ..sky import lights
    canvas = build()
    r = lights.report(canvas)
    out, odd = [], 0
    for cell, level, what in sources():
        why = f"{WHY}:way {what}"
        got = r["placed"].get(cell)
        said = f"placed at {got[0]} ({got[1]})" if got else "not placed"
        odd += got is None or got[0] != level or got[1] != why
        for key in ("rejected", "capped", "merged", "moved"):
            for entry in r[key]:
                if entry[0] == cell:
                    said += f"; {key}: {entry}"
                    odd += 1
        out.append(f"{cell} {level} {what}: {said}")
    light = L.levels(canvas, (X0 - 14, FEET - 3, Z0 - 7), (X1 + 7, ROOM["ceiling"] + 6, Z1 + 7))
    low = 0
    for name, cells in (("the hall's", PLACES), ("the light line's beside them", BESIDE)):
        got = {c: max(light.get(c, 0), light.get((c[0], c[1] + 1, c[2]), 0)) for c in cells}
        low += sum(v < LINE for v in got.values())
        out.append(f"{name}: " + " ".join(f"({x},{y},{z})={v}" for (x, y, z), v in sorted(got.items())))
    out.append(f"sources odd: {odd}; places under {LINE}: {low}")
    out.append("ways: " + ("PASS" if not odd and not low else "FAIL"))
    print("\n".join(out))
    if folder:
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "obs-starhall-ways.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(out) + "\n")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else None)
