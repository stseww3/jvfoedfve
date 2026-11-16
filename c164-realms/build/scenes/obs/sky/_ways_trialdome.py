"""Trial tree only (dome; never delivered): lamps to fall back on for the dome room's door passage
and the recesses under its north windows, should those cells not be left dark with the room
(the director, #442). C164_TRIAL_FALLBACK=1 hangs them.
"""
import os

from . import _lightkit as L

LAMPS = [
    # in the opening over the door's leaves, on the east jamb: lights the passage behind the door
    ((13, 20, -10), "west", L.WAY, "the passage behind the dome room's north door"),
    # the pier at the west end of the gable, its west face: into the recess under the window at x 0
    ((2, 19, -14), "west", L.WAY, "the recess under the dome room's north-west window"),
    # the riser of the gable's first step: into the recess under the window at x 4
    ((5, 19, -14), "west", L.WAY - 2, "the recess under the dome room's north window"),
] if os.environ.get("C164_TRIAL_FALLBACK") == "1" else []
