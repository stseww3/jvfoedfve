"""python -m scenes.obs_int_domeroom: the room as text (no game, no picture)."""
from scenes.obs.common import skeleton as S
from scenes.obs.main import _order as O

from . import build

c = build()
cx, cz = S.DOME_CENTRE
print("section along the axis (z = %d), looking north" % cz)
print(O.section(c, "z", cz, (cx - 15, cx + 15), (S.DRUM_BASE, S.DOME_APEX + 2)))
print("section across (x = %d), looking west" % cx)
print(O.section(c, "x", cx, (cz - 15, cz + 15), (S.DRUM_BASE, S.DOME_APEX + 2)))
for y in (S.ROOF_STAND, S.DRUM[1], S.DOME_SPRING + 1, S.DOME_SPRING + 6):
    print("plan of row y = %d, north up" % y)
    for z in range(cz - 14, cz + 15):
        print("z %3d  %s" % (z, "".join(" " if c.get(x, y, z) is None else O.mark(c.get(x, y, z))
                                         for x in range(cx - 14, cx + 15)).rstrip()))
