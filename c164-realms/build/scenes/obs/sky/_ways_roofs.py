"""The lamps of the ways over the north roofs that the list of dark cells still asked for (sound's
dark.md on the assembly 01c7ab6e, "dome, lights: the roofs": ten cells north of the dome room,
all of them pockets beside the ways, under a cornice). Surveyed by dome (c326) on the master
scene, block light cell by cell: with these each of the ten has 5 at the feet or at the head.
The south half is cable's (sky/_ways_roofsouth.py), the mirror of this one.

Rows as lights.ROOF_WAYS: the block a caged lamp is fixed to, the way its face looks, the level
of its source (in the cell before that face), what it lights.
"""
from . import _lightkit as L

LAMPS = [
    # The pocket between the pier east of the dome room's north door and the drum's stepped corner
    # (three cells at 0) and the slab one steps up from beside it (3): on the pier's east face, a
    # course over the pocket's floor -- one course higher it leaves the slab at 4.
    ((14, 19, -9), "east", L.WAY, "the pocket east of the dome room's north door and the step before it"),
    # The ledge behind the top of the north gable (two cells at 3): over the head of the window
    # niche, in the last course under the cornice. 6 is the least that brings both to 5.
    ((8, 21, -12), "north", L.WAY - 2, "the ledge behind the top of the north gable"),
    # The passage behind the door (one cell at 4; the lamp outside the door leaves it one short):
    # in the opening over the door's leaves, on its east jamb. The dome room behind it gets one
    # level more in the mouth of the passage and nothing further in (the director, #442: the room
    # has its one red lamp and no other).
    ((13, 20, -10), "west", L.WAY, "the passage behind the dome room's north door"),
    # The recesses under the dome room's north windows (three cells at 0), from outside and from
    # the row under the windows, so that nothing more than now goes in through the glass: on the
    # west face of the pier that ends the gable, and knee-high on the riser of the gable's first
    # step (6: the least that brings the recess before it to 5).
    ((2, 19, -14), "west", L.WAY, "the recess under the dome room's north-west window"),
    ((5, 19, -14), "west", L.WAY - 2, "the recess under the dome room's north window"),
]
