"""interiors/_starhall_ways -- the light on the ways of the star hall where its lamps leave less
than the line asks. A part of interiors/starhall (its PARTS), which calls dress() at the end of
its own and adds models() to its models; the underscore keeps the file out of the category's
auto-discovery. It adds lamps and light sources and nothing else (A0, 11-16 10:43).

The line: a place a person stands at has 5 or more, read as tools/darkfloor.py reads it (the
better of the cell of the feet and the cell of the head; the tops of the galleries' railings are
such places, reached with a hop). The list of the assembly 9fbb2e0c names sixteen places of the
hall at 3 and 4:

  the south gallery between its first two lamps     (5..6, 7, 5) and the railing's top (8, 8, 4)
  the north gallery between the wing room's doors   (8, 7, -5)
  the east end of both galleries                    (14..15, 7, -5 and 5), the railing's top beside it
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

    env PYTHONPATH=build python -m scenes.obs.interiors._starhall_ways     (from c164-realms/, on a worker node)

builds the master scene and tells what sky/lights made of every source asked for here.
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
FILL = 5                                        # in the cell of the head of the place it is for, and no further

# (the cell, its level, what it lights): building coordinates
SOURCES = (
    ((6, DECK + HEAD, Z1 - 1), RAIL_LEVEL, "south gallery"),
    ((8, DECK + HEAD, Z0), FILL, "north gallery"),
    ((int(END_LAMP_X), DECK + HEAD, Z0), END_LEVEL, "north gallery end"),
    ((int(END_LAMP_X), DECK + HEAD, Z1), END_LEVEL, "south gallery end"),
    ((X0, FEET + HEAD, Z0), FILL, "north aisle corner"),
    ((X0, FEET + HEAD, Z1), FILL, "south aisle corner"),
    ((9, FEET + HEAD, -3), FILL, "roundel north"),
    ((9, FEET + HEAD, 3), FILL, "roundel south"),
)


def models():
    return {}


def dress(canvas, origin=(0, 0, 0), version="a"):
    """Hang the two lamps and ask the light line for the sources; returns the display entities placed."""
    ox, oy, oz = origin
    n = 0
    for z, facing in ((float(Z0), "south"), (Z1 + 1.0, "north")):
        n += lamps.place(canvas, "cage", (END_LAMP_X, LAMP_Y, z), facing=facing, origin=origin, version=version,
                         light=False)
    for (x, y, z), level, what in SOURCES:
        L.suggest(canvas, (ox + x, oy + y, oz + z), level, f"{WHY}:way {what}", rank=3)
    return n


def main():
    from .. import build
    from ..sky import lights
    r = lights.report(build())
    odd = 0
    for cell, level, what in SOURCES:
        why = f"{WHY}:way {what}"
        got = r["placed"].get(cell)
        said = f"placed at {got[0]} ({got[1]})" if got else "not placed"
        odd += got is None or got[0] != level or got[1] != why
        for key in ("rejected", "capped", "merged", "moved"):
            for entry in r[key]:
                if entry[0] == cell:
                    said += f"; {key}: {entry}"
                    odd += 1
        print(f"{cell} {level} {what}: {said}")
    print("ways: " + ("PASS" if not odd else "FAIL"))


if __name__ == "__main__":
    main()
