"""obs_mach_recorders: the test scene of machines/recorders.

The machines stand where they will stand: in the time-service room, on its console and on the pier
south of its message desk. The room is the real one, dressed in the stand-in of its shell that the
room's own test scene keeps (scenes.obs_int_timeroom.box), so the pictures show the machines under
the room's lamps and against its instrument wall.

Who places the machines: the room, once it says PLACES_RECORDERS (it then calls rec.place() for
each of its SLOTS). The room that is in the tree before that leaves a brass slab where the drum
goes; here that slab is taken away and the three are placed at the room's slots, the drum moved
on to the console as the room has agreed to move its slot. The scene is the same either way.
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.interiors import timeroom
from scenes.obs.machines import rec
from scenes.obs_int_timeroom import box

BIOME = "obs_blue"
PX = 1 / 16.0


def slots():
    """kind -> (pos, facing): the room's slots; the drum a pixel inside the east end of the console."""
    out = {}
    for kind in rec.KINDS:
        slot = timeroom.SLOTS[kind]
        x, y, z = slot["pos"]
        if kind == "drum":
            x = min(x, timeroom.CONSOLE_X[1] + 1.0 - rec.BASE[0] / 2.0 * PX - PX)
        out[kind] = ((x, y, z), slot["facing"])
    return out


def build():
    c = Canvas()
    sources = box.build(c)
    timeroom.build_timeroom(c)
    n = 0
    if not getattr(timeroom, "PLACES_RECORDERS", False):
        c.clear(timeroom.DRUM_X, timeroom.SILL, timeroom.CONSOLE_Z)     # the room's stand-in for the drum
        for kind, (pos, facing) in slots().items():
            n += rec.place(c, kind, pos, facing=facing)
    box.light(c, sources)
    sky.build(c)
    c.entity_counts = {"machines": n}
    return c


def write_pack(pack_dir):
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])
