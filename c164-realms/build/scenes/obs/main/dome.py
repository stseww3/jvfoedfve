"""main/dome: the rotunda's drum and the great dome's shell, the centre of V1, V2 and V12
(plan/packages/main/dome.md; plan/ART-PLAN.md 5.2).

The geometry is main/_dome.py; this module is the package the category finds. It lays the drum
from the rotunda's cornice up (y 16), the gallery, the dome and what shuts the slit. One block
thick: the room inside is interiors', the track's rollers and the shutter's chains are machines',
the round frames of the windows and the door leaves are props'.

Two versions stand side by side in the test scene obs_main_dome:

    a   twenty fine ribs, two leaves that part sideways
    b   eight main ribs and flush seams, a slatted curtain that rolls up into a housing on the crown

The slit looks west and stands open in the scene (ART-PLAN 5.2: the light inside shows through it);
"half" and "closed" are there for whoever animates or photographs it.
"""
from artkit.canvas import Canvas

from . import _dome

ORDER = 60                  # after the shell and the roof terraces: the drum stands on them
VERSION = "a"
SLIT = "open"


def _glass(front, bay, storey):
    from . import facade                    # the lit windows are told in one place for the whole building
    return facade.glass(front, bay, storey)


def _strip(canvas, origin):
    """Take away the massing an older main/facade.py lays here itself: it does so until it has the
    switch that looks for this package (facade.crowned)."""
    from . import facade
    if hasattr(facade, "crowned"):
        return
    ox, oy, oz = origin
    old = Canvas()
    _dome.build(old, glass=_glass)
    for (x, y, z), state in old.b.items():
        if canvas.get(ox + x, oy + y, oz + z) == state:
            canvas.clear(ox + x, oy + y, oz + z)


def build(canvas, origin=(0, 0, 0), version=None, slit=None):
    _strip(canvas, origin)
    _dome.build(canvas, origin, glass=_glass, version=version or VERSION, slit=slit or SLIT)
    return 0
