"""The stand-in of the shell the battery room is dressed in. Nothing here goes into the master scene.

It is a slice of the real building, cut out round the cavity under the time room: main/facade and
main/shell are built on a canvas of their own and every block of theirs inside SLICE is taken as
it stands, so the walls, the plinth, the barred dark windows of the base storey and the deck over
the room are the building's own. What the slice lacks is put down here:

  the time room's floor   as the time room relays it (interiors/timeroom): dark boards, the cover
                          plates of its cable ducts, the grating along its rack with the iron bed
                          under it, which hangs in the battery room's last row along z -24
  the doorway             the one cell main/shell will cut in the south wall when the room has
                          passed its review (batteryroom.HALL_DOOR), cut here so that the room is
                          seen from where one comes in; behind it a dark lobby stands in for the
                          star hall's side aisle, which is indoors
  the court               a strip of paving east of the front, for the view from outside
  the bare twin           the same slice once more, further south, with nothing in its cavity:
                          from the court the base storey with the room stands beside the base
                          storey without it (shot ext_base: the room is on the right)
"""
from artkit.canvas import Canvas

from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.interiors import batteryroom as R
from scenes.obs.interiors import timeroom as T
from scenes.obs.main import facade, shell

SLICE_X = (S.WALL_W - 3, S.WALL_E + 3)          # -3..18: both long walls and what stands out of them
SLICE_Y = (R.FLOOR_Y - 1, S.STAND)              # -2..7: from under the floor to the course over the string
SLICE_Z = (R.Z0 - 3, R.Z1 + 1)                  # -28..-6: the two cross walls and a bay beyond the north one
COURT_X = (SLICE_X[1] + 1, SLICE_X[1] + 26)     # the paving east of the front
LOBBY_Z = R.HALL_DOOR[1] + 1                    # -5: the row behind the doorway
BARE_DZ = SLICE_Z[1] - SLICE_Z[0] + 4           # 26: how far south of the slice its bare twin stands


def _slice(c, full, dz):
    """The slice of the building, dz rows south of where it stands, with the time room's floor over it."""
    for (x, y, z), state in full.b.items():
        if SLICE_X[0] <= x <= SLICE_X[1] and SLICE_Y[0] <= y <= SLICE_Y[1] and SLICE_Z[0] <= z <= SLICE_Z[1]:
            c.set(x, y, z + dz, state)

    # the time room's floor, as that room relays it, and the bed of its cable trough
    for x in range(T.X0, T.X1 + 1):
        for z in range(T.Z0, T.Z1 + 1):
            c.set(x, T.FLOOR_Y, z + dz, B.DARK_WOOD.block)
    for x, z in T.duct_cells():
        if T.grated((x, z)):
            c.set(x, T.FLOOR_Y, z + dz, B.IRON_GRATE)
            c.set(x, T.FLOOR_Y - 1, z + dz, B.IRON_PLATE)
        else:
            c.set(x, T.FLOOR_Y, z + dz, B.IRON_RIVETED.block)
    # a lid over the slice: the storeys above are not in it, and the sky is not to stand in the time room
    for x in range(SLICE_X[0], SLICE_X[1] + 1):
        for z in range(SLICE_Z[0], SLICE_Z[1] + 1):
            c.set(x, SLICE_Y[1] + 1, z + dz, B.ASHLAR_FINE.block)


def build(c, room=True, twin=True):
    """The shell. With room=False the cavity is left as the building has it: closed, no doorway.
    twin: the same slice once more, BARE_DZ rows to the south, its cavity closed and empty, so
    that the base storey is seen from the court with the room and without it, side by side."""
    full = Canvas()
    facade.build(full)
    shell.build(full)
    _slice(c, full, 0)
    if twin:
        _slice(c, full, BARE_DZ)

    # the court's paving, and the ground under the walls
    for x in range(SLICE_X[0] - 2, COURT_X[1] + 1):
        for z in range(SLICE_Z[0] - 2, SLICE_Z[1] + 3 + (BARE_DZ if twin else 0)):
            c.set(x, S.PAVING_Y, z, B.ASHLAR_FINE.block, keep=True)

    if room:
        x, z = R.HALL_DOOR
        for y in range(R.DOOR_Y[0], R.DOOR_Y[1] + 1):
            c.clear(x, y, z)
        for lx in range(x - 1, x + 2):                      # the lobby: a floor, a lid and three walls
            for y in range(R.FLOOR_Y, R.DOOR_Y[1] + 2):
                for lz in (LOBBY_Z, LOBBY_Z + 1):
                    solid = y in (R.FLOOR_Y, R.DOOR_Y[1] + 1) or lx != x or lz != LOBBY_Z
                    if solid:
                        c.set(lx, y, lz, B.SLATE_SMOOTH.block)
                    else:
                        c.clear(lx, y, lz)
    return c
