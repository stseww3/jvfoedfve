"""The time room's door: a part of interiors/timeroom, written beside it (timeroom.PARTS).

The doorway in the cross wall towards the hall's gallery is main/shell's, an opening two cells wide
and three rows high. On the room's side it gets a door case of the wainscot's wood and two panelled
leaves standing open into the room, hinged on the casings: _doorcase.py, the kit the wing rooms'
doors are made with. The case lies on the wainscot (timeroom.PANEL_S), its cap ends under the bell
over the door, and the leaves stand before the wainscot either side of the opening: the cells
SWEPT names are theirs. No light source; five display entities.
"""
from ..main import shell
from . import _doorcase as D
from . import timeroom as T

DOOR = next(d for d in shell.doors() if d["room"] == "time room")
FACE = T.WAINSCOT_T * 16.0          # 3 px: the case lies on the wainscot
SWING = 100.0                       # degrees from shut: past the square, so that from the instrument wall a leaf shows its face
SWEPT = D.swept(DOOR, FACE, SWING)  # what the leaves stand over on the floor: (x0, z0, x1, z1) each


def models():
    return D.models(T.PREFIX, DOOR, FACE, SWING)


def dress(canvas, origin=(0, 0, 0)):
    """Hang the door. Returns the display entities placed."""
    return D.place(canvas, T.PREFIX, DOOR, FACE, SWING, origin)
