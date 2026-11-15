"""A stand-in for site/cablecar while that package is not in the tree: the station's blocks by its
own rule, copied from its second draft (c226, cursor/c164-cable-a47d 246a2de5) so that the car and
the winch are tried in the shell they are made for and not in a box. Blocks only: no props, no
lamps, no light, and not the sheets that package lays on the room side of the winch house's two
lit lights (materials/windows.line): here their backs glow into the room. The cells the machines
hang on are taken from machines/cable, which carries the same figures for a tree without the shell.

This file goes when site/cablecar is merged: the scene then builds the real one.
"""
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.machines import cable
from scenes.obs.site import _kit as K

X0, Z0, X1, Z1 = S.CABLE_STATION        # x 75..91, z -40..-26
LOW = S.LOWER_GROUND                    # -6: the lower of the platform's two courses
FEET = S.STATION_GROUND                 # -4: feet on the station platform
TOP = FEET - 1                          # -5: the platform's paving course

AXIS = cable.AXIS                       # -33: the row of the track's axis
HEAD = cable.CAR_BOX[0] - 1             # 88: the last cell of the track, the spawn cell
END = cable.TRACK_END                   # 141: the last column of the track
BENTS = list(range(X1 + 7, END, 6))     # x 98, 104 ..
CLOUD = K.ROCK_FLOOR + 5                # -24: the cloud is laid round the legs up to here

ROOM = cable.ROOM                       # the winch room's cells: x 87..90, z -39..-37
WINCH = (ROOM[0] - 1, ROOM[1] - 1, ROOM[2] + 1, ROOM[3] + 1)       # the winch house, walls included
WINCH_TOP = FEET + 6                    # 2: its top wall course; its eaves are at 3, its ridge at 5
OPENING = dict(x=(ROOM[0], ROOM[2]), y=(FEET, FEET + 4))            # the whole south side, under a girder
WAIT = (WINCH[0] - 6, Z0, WINCH[0] - 1, Z0 + 3)                     # x 80..85, z -40..-37: the waiting room
WAIT_TOP = FEET + 3
WAIT_DOOR = (WAIT[0] + WAIT[2] + 1) // 2                            # 83

EAVES = FEET + S.CANOPY_CLEAR           # 1: the glass roof's lowest course
CANOPY = (HEAD, AXIS - 2, X1, AXIS + 2)             # x 88..91, z -35..-31
FRAMES_X = (CANOPY[0], CANOPY[2])
GIRDER_Z = CANOPY[3] + 1                # -30: the south girder's row
COLUMNS = [(CANOPY[0] + 1, GIRDER_Z), (CANOPY[2], GIRDER_Z)]        # (89, -30), (91, -30)
PEDESTAL = 2                            # courses of stone under a column's shaft; its head is one course
BAY = HEAD - 1                          # 87: from here east the south side is the railed bay
# where the site's lamp hangs: the underside of the glass roof's ridge, over the car's door
LAMP_POINTS = {"car": (CANOPY[0] + 1.5, float(EAVES + 2), AXIS + 0.5)}

BODY = PAVE = WALL = FOOTING = B.TUFF_BRICK.block
KERB = COURSE = B.TUFF_SMOOTH.block
STEP = CORBEL = B.TUFF_SMOOTH.stairs
ROOF = B.SLATE_TILE.stairs
ROOF_FLAT = B.SLATE_TILE.slab + "[type=bottom]"
IRON = B.IRON_RIVETED.block
IRON_SLAB = B.IRON_RIVETED.slab
IRON_STAIR = B.IRON_RIVETED.stairs
GLASS = B.SKYLIGHT.block
SCREEN = B.SKYLIGHT.pane
GRATE = B.IRON_GRATE
BARS = B.IRON_BARS
PIPE = B.IRON_PIPE + "[axis=y]"         # a column's shaft
POST = B.TUFF_SMOOTH.wall               # its pedestal
CAPITAL = B.IRON_CAST                   # its head
FINIAL = B.IRON_ROD + "[facing=up]"
TIE = B.IRON_HATCH + "[half=top]"
DOOR = B.IRON_DOOR
LIT = B.WINDOW_FROSTED.pane             # the lit glass of the waiting room's gable
LIT_FLUSH = B.WINDOW_FROSTED.block      # and of the winch house's east wall: whole blocks, flush with the wall
DARK = B.WINDOW_DARK.pane
SHUT = B.WINDOW_BLIND.pane


class _Pen:
    """The canvas with the origin added."""

    def __init__(self, canvas, origin):
        self.c, self.o = canvas, origin

    def set(self, x, y, z, state):
        self.c.set(self.o[0] + x, self.o[1] + y, self.o[2] + z, state)

    def clear(self, x, y, z):
        self.c.clear(self.o[0] + x, self.o[1] + y, self.o[2] + z)


def _platform(p):
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            p.set(x, LOW, z, BODY)
            p.set(x, TOP, z, PAVE)
    for z in range(Z0, Z1 + 1):                 # the east face stands one course deeper
        p.set(X1, S.LOWER_PAVING_Y, z, BODY)
    for z in range(Z0, Z1 + 1):                 # west: the lower step, then the upper
        p.set(X0, LOW, z, STEP + "[facing=east]")
        p.clear(X0, TOP, z)
        p.set(X0 + 1, TOP, z, STEP + "[facing=east]")
    for x in range(X0 + 1, BAY):                # south
        p.set(x, LOW, Z1, STEP + "[facing=north]")
        p.clear(x, TOP, Z1)
        if x > X0 + 1:
            p.set(x, TOP, Z1 - 1, STEP + "[facing=north]")
    for z in range(Z0, Z1 - 1):                 # a kerb line behind the head of each flight
        p.set(X0 + 2, TOP, z, KERB)
    for x in range(X0 + 2, BAY):
        p.set(x, TOP, Z1 - 2, KERB)
    for x in range(X0 + 3, HEAD):               # the track's axis, carried on to the west steps
        p.set(x, TOP, AXIS, KERB)
    for x in range(HEAD, X1 + 1):               # an edge stone along either side of the car
        for z in (CANOPY[1], CANOPY[3]):
            p.set(x, TOP, z, KERB)
    north = [(x, Z0) for x in range(X0 + 2, WAIT[0])]
    K.rail(p.c, p.o, north, north[:1], y=FEET, kerb=False)
    bay = [(x, Z1) for x in range(BAY, X1)] + [(X1, z) for z in range(Z1, GIRDER_Z, -1)]
    K.rail(p.c, p.o, bay, [(BAY, Z1), (X1, Z1)], y=FEET, kerb=False)
    for z in (CANOPY[1], CANOPY[3]):
        K.rail(p.c, p.o, [(X1, z)], [], y=FEET, kerb=False)


def _track(p):
    """The rails in the paving, the grating over the cable between them, the buffer stops."""
    for x in range(HEAD, X1 + 1):
        p.set(x, TOP, AXIS - 1, IRON)
        p.set(x, TOP, AXIS + 1, IRON)
        p.set(x, TOP, AXIS, GRATE)
    for z in (AXIS - 1, AXIS + 1):
        p.set(HEAD - 1, FEET, z, IRON_STAIR + "[facing=east]")


def _walls(p, box, y0, y1):
    """Four walls: a polished course at the foot and at the top, polished angle piers, brick between."""
    x0, z0, x1, z1 = box
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if x not in (x0, x1) and z not in (z0, z1):
                continue
            corner = x in (x0, x1) and z in (z0, z1)
            for y in range(y0, y1 + 1):
                p.set(x, y, z, COURSE if corner or y in (y0, y1) else WALL)


def _gable_roof(p, box, y, gables=None):
    """A slate roof of two pitches over a box, the ridge east-west; the eaves course is y."""
    x0, z0, x1, z1 = box
    half = (z1 - z0) // 2
    gables = (x0, x1) if gables is None else gables
    for x in range(x0, x1 + 1):
        for i in range(half):
            p.set(x, y + i, z0 + i, ROOF + "[facing=south]")
            p.set(x, y + i, z1 - i, ROOF + "[facing=north]")
            if x in gables:
                for z in range(z0 + i + 1, z1 - i):
                    p.set(x, y + i, z, WALL)
        for z in range(z0 + half, z1 - half + 1):
            p.set(x, y + half, z, ROOF_FLAT)


def _window(p, cells, y0, y1, glass):
    for x, z in cells:
        for y in range(y0, y1 + 1):
            p.set(x, y, z, glass)


def _winch_house(p):
    x0, z0, x1, z1 = WINCH
    mid = (z0 + z1) // 2
    _walls(p, WINCH, FEET, WINCH_TOP)
    ox0, ox1 = OPENING["x"]
    oy0, oy1 = OPENING["y"]
    for x in range(ox0, ox1 + 1):               # the south side is one opening under an iron girder
        for y in range(oy0, oy1 + 1):
            p.clear(x, y, z1)
        p.set(x, oy1 + 1, z1, IRON)
    p.set(ox0, oy1, z1, CORBEL + "[half=top,facing=west]")
    p.set(ox1, oy1, z1, CORBEL + "[half=top,facing=east]")
    # two tall lit lights in the east wall, a pier between them; two dark ones in the north wall,
    # either side of the two columns of brick the winch's wall lamp hangs on; a small dark one in
    # the west gable, under an apex stone and a rod
    _window(p, [(x1, z0 + 1), (x1, z1 - 1)], FEET + 1, FEET + 4, LIT_FLUSH)
    _window(p, [(x0 + 1, z0), (x1 - 1, z0)], FEET + 2, FEET + 4, DARK)
    _gable_roof(p, WINCH, WINCH_TOP + 1)
    _window(p, [(x0, mid)], WINCH_TOP + 1, WINCH_TOP + 1, DARK)
    p.set(x0, WINCH_TOP + 3, mid, COURSE)
    p.set(x0, WINCH_TOP + 4, mid, FINIAL)


def _waiting_room(p):
    """Built before the winch house, whose west wall closes its east end."""
    x0, z0, x1, z1 = WAIT
    _walls(p, (x0, z0, x1 + 1, z1), FEET, WAIT_TOP)
    p.set(WAIT_DOOR, FEET, z1, DOOR + "[half=lower,facing=south,hinge=left]")
    p.set(WAIT_DOOR, FEET + 1, z1, DOOR + "[half=upper,facing=south,hinge=left]")
    p.set(WAIT_DOOR, FEET + 2, z1, DARK)
    _window(p, [(WAIT_DOOR - 2, z1), (WAIT_DOOR + 2, z1)], FEET + 1, FEET + 2, SHUT)
    _window(p, [(x0, z) for z in range(z0 + 1, z1)], FEET + 1, FEET + 2, LIT)
    _window(p, [(WAIT_DOOR - 1, z0), (WAIT_DOOR + 1, z0)], FEET + 1, FEET + 2, DARK)
    _gable_roof(p, WAIT, WAIT_TOP + 1, gables=(x0,))


def _glass_roof(p):
    """Two iron frames with a glazed screen in each, glass in two pitches between them, an iron
    ridge; the south girder lies on two columns and tapers where it oversails the western one. A
    column is a stone pedestal of two courses, an iron shaft of two, a cast block under the girder."""
    x0, z0, x1, z1 = CANOPY
    half = (z1 - z0) // 2
    for x in range(x0, x1 + 1):
        frame = x in FRAMES_X
        for i in range(half):
            p.set(x, EAVES + i, z0 + i, IRON_STAIR + "[facing=south]" if frame else GLASS)
            p.set(x, EAVES + i, z1 - i, IRON_STAIR + "[facing=north]" if frame else GLASS)
            if frame:
                for z in range(z0 + i + 1, z1 - i):
                    p.set(x, EAVES + i, z, SCREEN)
        p.set(x, EAVES + half, z0 + half, IRON_SLAB + "[type=bottom]")
        p.set(x, EAVES, GIRDER_Z, IRON if x > x0 else IRON_STAIR + "[half=top,facing=east]")
    for x, z in COLUMNS:
        for y in range(FEET, EAVES):
            p.set(x, y, z, POST if y < FEET + PEDESTAL else CAPITAL if y == EAVES - 1 else PIPE)


def _slab(h):
    """The cell and the half of it whose upper face is at height h."""
    if h == int(h):
        return int(h) - 1, "top"
    return int(h // 1), "bottom"


def _trestle(p):
    """Two rails of riveted slabs with a tie in every second cell, on bents: a cap girder across,
    two legs on footings on the ridge (or down into the cloud), bars and struts between the legs."""
    for x in range(X1 + 1, END + 1):
        z = cable.track_axis(x)
        y, half = _slab(cable.rail_top(x))
        for dz in (-1, 1):
            p.set(x, y, z + dz, IRON_SLAB + f"[type={half}]")
        if half == "top":
            p.set(x, y, z, TIE)
    x = X1 + 1                                  # the abutment: masonry from the rock to the rails
    for y in range(K.cable_ridge(x)[1] + 1, TOP):
        for dz in (-1, 0, 1):
            p.set(x, y, cable.track_axis(x) + dz, FOOTING)
    for x in BENTS:
        z = cable.track_axis(x)
        y, half = _slab(cable.rail_top(x))
        cap = y - 1 if half == "bottom" else y
        ridge = K.cable_ridge(x)
        foot = ridge[1] + 1 if ridge else K.ROCK_FLOOR
        for dz in (-1, 0, 1):
            p.set(x, cap, z + dz, IRON)
        for yy in range(cap - 1, foot - 1, -1):
            for dz in (-1, 1):
                p.set(x, yy, z + dz, FOOTING if ridge and yy == foot else IRON)
            if yy > foot:
                if (cap - yy) % 3 == 0:
                    p.set(x, yy, z, IRON_SLAB + "[type=top]")
                elif yy > CLOUD:
                    p.set(x, yy, z, BARS)


def build(canvas, origin=(0, 0, 0)):
    p = _Pen(canvas, origin)
    _platform(p)
    _track(p)
    _waiting_room(p)
    _winch_house(p)
    _glass_roof(p)
    _trestle(p)
    for y in (FEET, FEET + 1):          # the spawn cell stays empty
        p.clear(HEAD, y, AXIS)
    return 0
