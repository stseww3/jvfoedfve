"""The lamps of the ways over the south roofs that the list of dark cells still asked for (sound's
dark.md on the assembly 01c7ab6e: "dome, lights: the roofs"). The rows are those of
lights.ROOF_WAYS and sky/lights hangs them with the others: the block a caged lamp is fixed to,
the way its face looks, the level of its source, what it lights. The north half is dome's
(sky/_ways_roofs.py); this one is its mirror across the building's axis, surveyed by cable (c338).
"""
from . import _lightkit as L

LAMPS = [
    # The pocket between the pier east of the dome room's south door and the drum's stepped corner
    # (three cells at 0) and the slab one steps up from to it (3): the lamp hangs on the pier's
    # east face, a course over the pocket's floor -- one course higher it leaves the slab at 4.
    ((14, 19, 9), "east", L.WAY, "the pocket east of the dome room's south door and the step before it"),
    # The ledge behind the top of the south gable, under the cornice (two cells at 3): over the
    # head of the window niche, in the last course under the cornice.
    ((8, 21, 12), "south", L.WAY - 2, "the ledge behind the top of the south gable"),
]
