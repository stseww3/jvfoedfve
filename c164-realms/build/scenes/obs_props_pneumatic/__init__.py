"""obs_props_pneumatic: the test scene of props/pneumatic.

The line stands where it will stand: A 1, in the time-service room, from the station on the pier
north of the rating bench up into the beam's shoe and along the beam across the ceiling. The room
is the real one, dressed in the stand-in of its shell that the room's own test scene keeps
(scenes.obs_int_timeroom.box), so the pictures show the glass and the brass under the room's lamps
and against its panelling.

A carrier at rest is out of sight, and a picture drawn offline shows the rest pose. STILL places
two more that stand still in the glass, one in the riser and one under the beam: in this scene
only, so that a picture shows what a carrier in the tube looks like. In the game they are the
two that do not move.
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.interiors import timeroom
from scenes.obs.props import pneumatic
from scenes.obs_int_timeroom import box

BIOME = "obs_blue"
STILL = ((1.6, "up"), (4.2, "east"))    # blocks along the riser and along the run under the beam, the way it lies


def build():
    c = Canvas()
    sources = box.build(c)
    timeroom.build_timeroom(c)
    n = pneumatic.line(c, "time_room")
    spec = pneumatic.LINES["time_room"]()
    for run, (along, way) in zip(spec["runs"], STILL):
        d = pneumatic.DIRS[way]
        n += pneumatic.carrier(c, tuple(run["a"][i] + d[i] * along for i in range(3)), way)
    box.light(c, sources)
    sky.build(c)
    c.entity_counts = {"props": n}
    return c


def write_pack(pack_dir):
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
