"""sky/_ways_pier: the caged lamps round the telescope pier that sky/lights hangs with its own
(lights.way_lamps() takes in the LAMPS of every sky/_ways_*.py). What was still dark round the
pier after the lamps of sky/lights itself and of the grand stair hall (_ways_stairhall.py), on
sound's list of the cells one can stand in (tools/darkfloor.py of his branch: under 5 at the feet
and at the head).

A row is as in lights.ROOF_WAYS: the block of the wall the lamp is fixed to (x, y, z), the way its
face looks, the level of its source, what it lights; the source stands in the cell before the
lamp. None hangs on the pier's east face, which is the mother clock's and looks at the door.
"""

LAMPS = [
    # The last two steps of the ring stair, under the mouth of the well, had 4: the lamp in the
    # mouth is three cells off and is not raised, the dome room above it keeps dark (lights,
    # #79855). This one hangs inside the well on the north curb, under those steps and out of the
    # dome room's sight, as the lamp under the pier's corbel does beside it.
    ((6, 15, -4), "south", 8, "the ring stair's last two steps, from the well under them"),
]
