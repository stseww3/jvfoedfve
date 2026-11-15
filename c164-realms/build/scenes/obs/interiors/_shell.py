"""Stand-in shell of the star hall for its box test scene (skipped by category auto-discovery).

The star hall is dressed first inside a plain stand-in of the shell the main-building line (c231)
will hand over, then moved into the real one. The stand-in is built on the skeleton's scene
coordinates, so the dressing is written once in real coordinates and moving in means dropping the
stand-in, nothing else. Everything here is c231's to replace: the walls, the floor and ceiling
slabs, the telescope pier, the gallery deck and its ring stair, the entrance arches and the west
openings into the rotunda.

Layout locked by A0 (skeleton R1 0.3, g2 #207, #220):
  clear volume   x 2..13 (ROOM_X), z -6..6 (STAR_HALL_Z), y 0..13; floor block y -1, ceiling y 14
  entrance       the east wall, three arches on bays 8, 9, 10 (z -5..-3, -1..1, 3..5), y 0..5 with a
                 round head to y 6; the centre arch is the open door, the two sides are iron grilles;
                 great dark windows y 8..13 over each arch
  pier           the telescope pier, a 3x3 stone shaft (x 3..5, z -1..1) straight up from the floor
                 through the ceiling to the dome room; the mother clock sits on its east face
  gallery        the main-storey floor carries into the hall as a gallery at y 6 (feet at 7) round
                 the north, south and west sides; its rail looks into the full-height central well
                 where the orrery hangs. The ground floor carries no stair (g2 #207): the gallery is
                 reached by the rotunda's grand stair, the dome room by the ring stair round the pier
  west           not sealed: the hall opens west into the rotunda; the pier blocks the axis sightline,
                 the rotunda's outer wall is solid stone with dark windows and a west door
"""
from ..common import blocks as B
from ..common import skeleton as S

X0, X1 = S.ROOM_X                       # 2, 13: the clear interior in x
Z0, Z1 = S.STAR_HALL_Z                  # -6, 6
Y0 = S.GROUND                           # 0, feet on the hall floor
Y1 = S.STAR_HALL_CEIL - 1               # 13, the top of the clear volume
FLOOR = S.PAVING_Y                      # -1, the floor block (its top is y 0)
CEIL = S.STAR_HALL_CEIL                 # 14, the ceiling block
DECK = S.STRING                         # 6, the gallery floor block
STAND = S.STAND                         # 7, feet on the gallery

WEST = X0 - 1                           # 1, the west wall column (the rotunda side)
EAST_GLASS = S.GLASS_E                  # 14, the inner (glass) column of the east wall
EAST_FACE = S.WALL_E                    # 15, the east wall face (the box keeps the centre bays plain)
COURT = 6                               # paving laid east of the door, so the way out has ground
NORTH = Z0 - 1                          # -7, the north wall column (the time-room wing beyond)
SOUTH = Z1 + 1                          # 7, the south wall column (the chart-room wing beyond)

PIER_X = (S.PIER_SHAFT[0], S.PIER_SHAFT[2])     # 3, 5
PIER_Z = (S.PIER_SHAFT[1], S.PIER_SHAFT[3])     # -1, 1
GALLERY_DEPTH = 2                       # the gallery is this many cells deep against a wall

DOOR_BAY = S.CENTRE_BAYS[1]            # 9, the middle bay: the open door
ARCH_Y = (0, 5)                        # the arch opening (c206/c218 #236/#242)
ARCH_HEAD = 6
WINDOW_Y = S.WINDOW                     # 8..13, the great windows over the arches
WEST_DOOR_Z = (-1, 1)
WEST_WINDOW_Y = (9, 12)


def pier_cells():
    """Plan cells the 3x3 telescope pier stands on."""
    return {(x, z) for x in range(PIER_X[0], PIER_X[1] + 1) for z in range(PIER_Z[0], PIER_Z[1] + 1)}


def arch_z(bay):
    """The three cells of the arch on `bay` (z, north to south)."""
    zc = S.bay_center_z(bay)
    return (zc - 1, zc, zc + 1)


def gallery_cells():
    """Plan cells of the gallery deck: a walk GALLERY_DEPTH deep against the north, south and west
    walls, clear of the pier. The centre and the east (entrance) side are the open well."""
    pier = pier_cells()
    out = set()
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            near = (z <= Z0 + GALLERY_DEPTH - 1 or z >= Z1 - GALLERY_DEPTH + 1
                    or x <= X0 + GALLERY_DEPTH - 1)
            if near and (x, z) not in pier:
                out.add((x, z))
    return out


def rail_cells():
    """Gallery cells that border the open well: the rail stands on them."""
    deck, pier = gallery_cells(), pier_cells()
    out = set()
    for x, z in deck:
        for nx, nz in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
            inside = X0 <= nx <= X1 and Z0 <= nz <= Z1
            if inside and (nx, nz) not in deck and (nx, nz) not in pier:
                out.add((x, z))
                break
    return out


def star_hall(c, origin=(0, 0, 0)):
    """Build the stand-in shell at `origin`. Everything here is c231's to replace."""
    ox, oy, oz = origin
    wall, rough = B.ASHLAR_FINE.block, B.ASHLAR_ROUGH.block
    grille, dark, lit = B.IRON_BARS, B.WINDOW_DARK.block, B.WINDOW_LIT.block

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    def cut(x, y, z):
        c.clear(ox + x, oy + y, oz + z)

    # floor and ceiling slabs over the whole box; the court outside the door is paved
    for x in range(WEST, EAST_FACE + COURT + 1):
        for z in range(NORTH, SOUTH + 1):
            put(x, FLOOR, z, B.SLATE_SMOOTH.block if x > EAST_FACE else wall)
    for x in range(WEST, EAST_FACE + 1):
        for z in range(NORTH, SOUTH + 1):
            put(x, CEIL, z, wall)

    # the four perimeter walls, floor to ceiling
    for y in range(Y0, Y1 + 1):
        for x in range(WEST, EAST_FACE + 1):
            put(x, y, NORTH, wall)
            put(x, y, SOUTH, wall)
        for z in range(NORTH, SOUTH + 1):
            put(WEST, y, z, wall)
            put(EAST_GLASS, y, z, wall)
            put(EAST_FACE, y, z, wall)

    # the east wall's openings: three arches, the centre a door, the sides iron grilles; great dark
    # windows over them
    for bay in S.CENTRE_BAYS:
        for z in arch_z(bay):
            for y in range(ARCH_Y[0], ARCH_Y[1] + 1):
                cut(EAST_GLASS, y, z)
                cut(EAST_FACE, y, z)
            head = ARCH_HEAD if z == S.bay_center_z(bay) else ARCH_HEAD - 1   # a stepped round head
            put(EAST_GLASS, head, z, wall)
            if bay != DOOR_BAY:                                               # side bays: iron grille
                for y in range(ARCH_Y[0], ARCH_Y[1] + 1):
                    put(EAST_GLASS, y, z, grille)
            for y in range(WINDOW_Y[0], WINDOW_Y[1] + 1):
                put(EAST_GLASS, y, z, dark)
                cut(EAST_FACE, y, z)

    # the west wall holds the rotunda back: dark windows and a west door on the axis
    for z in range(NORTH, SOUTH + 1):
        for y in range(WEST_WINDOW_Y[0], WEST_WINDOW_Y[1] + 1):
            put(WEST, y, z, dark)
    for z in range(WEST_DOOR_Z[0], WEST_DOOR_Z[1] + 1):
        for y in range(Y0, 3 + 1):
            put(WEST, y, z, grille if z == S.AXIS_Z - 0.5 else B.IRON_PLATE)

    # the telescope pier, floor to ceiling and one course above, on the dome centre
    for x, z in pier_cells():
        for y in range(FLOOR, CEIL + 2):
            put(x, y, z, rough)

    # the gallery deck round the well and its iron rail
    deck, rail = gallery_cells(), rail_cells()
    for x, z in deck:
        put(x, DECK, z, B.IRON_RIVETED.block if (x, z) in rail else B.DARK_WOOD.block)
    for x, z in rail:
        put(x, STAND, z, B.IRON_BARS)

    # small base windows beside the door, so the arrival view has a little warm light to the sides
    for z in (NORTH + 2, SOUTH - 2):
        put(EAST_GLASS, 3, z, lit)
    return {"deck": deck, "rail": rail, "pier": pier_cells()}
