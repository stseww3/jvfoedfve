"""The lamps of the ways over the south roofs that the list of dark cells still asked for (sound's
dark.md on the assembly 01c7ab6e: "dome, lights: the roofs"). The rows are those of
lights.ROOF_WAYS and sky/lights hangs them with the others: the block a caged lamp is fixed to,
the way its face looks, the level of its source, what it lights. The north half is dome's
(sky/_ways_roofs.py); this one is its mirror across the building's axis, surveyed by cable (c338).
"""
from . import _lightkit as L

LAMPS = [
    # The pocket between the pier east of the dome room's south door and the drum's stepped corner
    # (three cells at 0) and the slab one steps up from to it (3): the lamp hangs on the pier, a
    # course over the pocket's floor -- one course higher it leaves the slab at 4. On the pier's
    # south face, over the step: the cell before its east face is the parapet guard's (see the
    # north half).
    ((14, 19, 9), "south", L.WAY, "the pocket east of the dome room's south door and the step before it"),
    # The ledge behind the top of the south gable, under the cornice (two cells at 3): over the
    # head of the window niche, in the last course under the cornice.
    ((8, 21, 12), "south", L.WAY - 2, "the ledge behind the top of the south gable"),
    # The passage behind the dome room's south door (its last cell at 4) has no lamp of its own:
    # the lamp outside the door has 9 for it (lights.ROOF_WAYS).
    # The recess under the dome room's south-west window (two cells at 0): on the west face of
    # the pier at the west end of the gable, outside the recess, so that the dome room behind
    # the glass gets no more light than it had.
    ((2, 19, 14), "west", L.WAY, "the recess under the dome room's south-west window"),
    # The recess under the window at x 4 (one cell at 1): on the riser of the gable's first step.
    ((5, 19, 14), "west", L.WAY - 2, "the recess under the dome room's south window"),
]
