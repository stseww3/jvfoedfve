"""Stand-in shells for the interior box test scenes (skipped by the category auto-discovery).

A room is dressed first inside a plain stand-in of the shell the main-building line (A3) will hand
over, then moved into the real one. The stand-in is built on the skeleton's scene coordinates, so the
dressing is written once in real coordinates and moving in means dropping the stand-in, nothing else.
Everything here is A3's to replace: walls, deck, stairs, the telescope pier, the openings.

The entrance hall ("star hall"), from the skeleton (R1 0.3):
  clear volume   x X0..X1, z Z0..Z1, y 0..13; floor block at y -1, ceiling block at y 14
  east wall      face x 17 (centre bays step out 2), glass plane x 16; the door z -1..1, y 0..6
                 (leaf 0..4, fanlight 5..6); great windows y 8..13 in bays 8, 9, 10
  deck           the main-storey floor block y 6 (feet at 7) carries on into the hall as a gallery
  pier           the telescope pier, an independent column on the dome centre (4, 0), ground to dome room
LOCKED: z, y, the door, the deck level, the pier's centre. PROVISIONAL (R1 does not pin them down, A3
decides): the east end X1, the pier radius, the deck's outline and where the stairs go.
"""
from ..common import blocks as B
from ..common import skeleton as S

# --- the entrance hall -------------------------------------------------------------------------
EAST_FACE = S.east_wall_x(S.CENTRE_BAYS[1])     # 17
EAST_GLASS = EAST_FACE + S.DEPTH_GLASS          # 16
X0, X1 = S.ROOM_X[0], EAST_GLASS - 1            # 2..15
Z0, Z1 = S.STAR_HALL_Z                          # -6..6
Y0, Y1 = S.GROUND, S.STAR_HALL_CEIL - 1         # 0..13
FLOOR = S.PAVING_Y                              # -1
CEIL = S.STAR_HALL_CEIL                         # 14
DECK = S.STRING                                 # 6
DOOR_Z = (S.bay_center_z(9) - 1, S.bay_center_z(9) + 1)
DOOR_Y = (0, 4)
FAN_Y = (5, 6)
PIER = S.PIER_CENTRE
PIER_R = S.PIER_R + 0.5

DECK_X = 9                  # the deck's front edge between the stairs; the open well is east of it
STAIR_X = (14, 8)           # seven treads, y 0..6, rising west; the last lies in the deck's layer
STAIR_ROWS = {"north": (Z0, Z0 + 1), "south": (Z1 - 1, Z1)}
CHEEK = {"north": Z0 + 2, "south": Z1 - 2}      # the row beside a stair that carries its balustrade
COURT = 8                   # paving laid outside the door, so the view through it has ground

SIDES = {"twin": ("north", "south"), "south": ("south",)}


def pier_cells():
    cx, cz = PIER
    r = int(PIER_R) + 1
    return {(x, z) for x in range(cx - r, cx + r + 1) for z in range(cz - r, cz + r + 1)
            if (x - cx) ** 2 + (z - cz) ** 2 <= PIER_R ** 2}


def stair_cells(stairs):
    """Plan cells under a flight and its cheek, for the sides the version has."""
    out = set()
    for side in SIDES[stairs]:
        for x in range(STAIR_X[1], STAIR_X[0] + 1):
            out |= {(x, z) for z in STAIR_ROWS[side]}
            if x > STAIR_X[1]:                      # the cheek stops short of the top tread
                out.add((x, CHEEK[side]))
    return out


def deck_cells(stairs):
    """Plan cells of the gallery deck: the west part of the hall round the pier, one cell further
    east between the stairs so there is a way past the pier's face."""
    pier, taken = pier_cells(), stair_cells(stairs)
    return {(x, z) for x in range(X0, DECK_X + 1) for z in range(Z0, Z1 + 1)
            if (x, z) not in pier and (x, z) not in taken}


def rail_cells(stairs):
    """Deck cells that look into the open well: the railing stands on them."""
    deck, pier, taken = deck_cells(stairs), pier_cells(), stair_cells(stairs)
    out = set()
    for x, z in deck:
        for n in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
            inside = X0 <= n[0] <= X1 and Z0 <= n[1] <= Z1
            if inside and n not in deck and n not in pier and n not in taken:
                out.add((x, z))
                break
    return out


def well(stairs):
    """(x0, z0, x1, z1) of the open, full-height floor between the deck, the stairs and the door."""
    z0 = CHEEK["north"] + 1 if "north" in SIDES[stairs] else Z0
    z1 = CHEEK["south"] - 1 if "south" in SIDES[stairs] else Z1
    return (DECK_X + 1, z0, X1, z1)


def tread_y(x):
    return STAIR_X[0] - x


def star_hall(c, origin=(0, 0, 0), stairs="twin"):
    """The stand-in shell of the entrance hall. stairs: "twin" (a stone flight along each side wall)
    or "south" (one iron flight along the south wall)."""
    ox, oy, oz = origin

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    def cut(x, y, z):
        c.clear(ox + x, oy + y, oz + z)

    wall, rough = B.ASHLAR_FINE.block, B.ASHLAR_ROUGH.block
    xs, zs = range(X0 - 1, EAST_FACE + 1), range(Z0 - 1, Z1 + 2)

    # floor slab, the court outside the door, ceiling slab
    for x in range(X0 - 1, EAST_FACE + COURT + 1):
        for z in zs:
            put(x, FLOOR, z, B.SLATE_SMOOTH.block if x > EAST_FACE else wall)
    for x in xs:
        for z in zs:
            put(x, CEIL, z, wall)

    # perimeter walls; the east wall is two deep (glass plane and face), as the centre bays are
    for y in range(Y0, Y1 + 1):
        for x in xs:
            put(x, y, Z0 - 1, wall)
            put(x, y, Z1 + 1, wall)
        for z in zs:
            put(X0 - 1, y, z, wall)
            put(EAST_GLASS, y, z, wall)
            put(EAST_FACE, y, z, wall)

    # the east wall's openings: the door and its fanlight, the great windows, the small base windows
    glass, dark = B.WINDOW_LIT.block, B.WINDOW_DARK.block
    for z in range(DOOR_Z[0], DOOR_Z[1] + 1):
        for y in range(DOOR_Y[0], DOOR_Y[1] + 1):
            cut(EAST_GLASS, y, z)
            cut(EAST_FACE, y, z)
        for y in range(FAN_Y[0], FAN_Y[1] + 1):
            put(EAST_GLASS, y, z, glass)
            cut(EAST_FACE, y, z)
    for bay in S.CENTRE_BAYS:
        zc = S.bay_center_z(bay)
        for z in (zc - 1, zc, zc + 1):
            top = S.WINDOW[1] if z == zc else S.WINDOW[1] - 1       # a stepped arch head
            for y in range(S.WINDOW[0], top + 1):
                put(EAST_GLASS, y, z, glass)
                cut(EAST_FACE, y, z)
            if bay != S.CENTRE_BAYS[1]:
                for y in (3, 4):
                    put(EAST_GLASS, y, z, dark)
                    cut(EAST_FACE, y, z)

    # the telescope pier, through the hall and its ceiling
    for x, z in pier_cells():
        for y in range(Y0, CEIL + 1):
            put(x, y, z, rough)

    # the deck, its railing, the posts under its front edge
    deck, rail = deck_cells(stairs), rail_cells(stairs)
    plank = B.DARK_WOOD.block if stairs == "twin" else B.IRON_GRATE
    for x, z in deck:
        put(x, DECK, z, B.IRON_RIVETED.block if (x, z) in rail else plank)
    for x, z in rail:
        put(x, DECK + 1, z, B.IRON_BARS)
    x0, z0, x1, z1 = well(stairs)
    for z in (z0, z1) if stairs == "twin" else (z0 + 1, z1):
        for y in range(Y0, DECK):
            put(DECK_X, y, z, B.IRON_BARS)

    # doorways from the deck into the wings
    for z in (Z0 - 1, Z1 + 1):
        for x in (4, 5):
            for y in range(S.STAND, S.STAND + 3):
                cut(x, y, z)

    # the stairs
    for side in SIDES[stairs]:
        rows, cheek = STAIR_ROWS[side], CHEEK[side]
        for x in range(STAIR_X[1], STAIR_X[0] + 1):
            t = tread_y(x)
            cheeked = x > STAIR_X[1]
            if stairs == "twin":                                     # stone, solid under the treads
                for z in rows:
                    for y in range(Y0, t):
                        put(x, y, z, rough)
                    put(x, t, z, B.ASHLAR_ROUGH.stairs + "[facing=west,half=bottom]")
                if cheeked:
                    for y in range(Y0, t + 1):
                        put(x, y, cheek, rough)
                    put(x, t + 1, cheek, B.ASHLAR_FINE.slab + "[type=bottom]")
            else:                                                    # iron, open under the treads
                for z in rows + ((cheek,) if cheeked else ()):
                    put(x, t, z, B.IRON_RIVETED.stairs + "[facing=west,half=bottom]")
                if cheeked:
                    put(x, t + 1, cheek, B.IRON_BARS)
    return {"deck": deck, "rail": rail, "well": (x0, z0, x1, z1)}
