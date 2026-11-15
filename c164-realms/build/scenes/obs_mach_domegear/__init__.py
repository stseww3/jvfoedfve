"""Test scene of the work package machines/domegear: the gear of the great dome in its room, at the
scene's true coordinates (plan/packages/machines/domegear.md).

The gear hangs on three other packages, and each is taken from the tree once it is there:

  main/dome            the drum and the dome's skin. Until its geometry is in main/_dome the drum is
                       the assembly's and the skin a stand-in laid by that package's own rule
                       (version a, the slit open): plates, ring beam and the two leaves, no seams
  interiors/domeroom   the room's lining and ironwork. Until then a stand-in by that package's rule
                       (its fifth draft): dark boards in front of the drum's stone with the fixed
                       ring beam on top of them, the dome's ring girder over the ledge, boards
                       under every plate, an iron curb round the slit carried on along the two
                       arch lines and down to the ring girder; no furniture
  machines/scope       the great refractor. Until then a bar of iron where its tube lies

The floor and the pier's cap are always this scene's own. It adds no light: the room is dark (its
one lamp is the telescope's, by the eyepiece), and the gear is to be seen as it will stand there,
in the sky light that falls through the slit.

The shots are written from the numbers below:  python -m scenes.obs_mach_domegear
"""
import math

from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.machines import dome
from scenes.obs.main import _dome as SHELL
from scenes.obs.main import _order as O

BIOME = "obs_blue"
BIOME_MARGIN = 48
BIOME_MARGIN_Y = 64
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)
GLOW = 12900                    # light version C: the most sky light the room ever gets

CX, CZ = S.DOME_CENTRE
AX, AZ = S.DOME_AXIS
FLOOR, STAND = S.ROOF_FLOOR, S.ROOF_STAND
WALL_TOP = S.DRUM[1]            # 23: the last course of the drum; the gear's ledge is its top
# the stand-in refractor, version b of machines/refractor (c237, g2 #427): its elevation, due west;
# where its axes cross; how far its eyepiece end and its objective are from there
TUBE_DEG = 41.05
TUBE_PIVOT = (AX, S.PIER_TOP_Y + 5.4, AZ)
TUBE_ENDS = (-5.5, 9.5)

# the stand-in skin: main/dome's numbers (c222, cursor/c164-dome-0dab)
SKIRT_Y = S.DOME_SPRING         # 24: the dome's ring beam
SILL_Y = SKIRT_Y + 1            # 25: the slit opens above this row
FOOT_ROWS = 3                   # rows of plates upright over the ring beam
CROWN = S.DOME_APEX + 1.0       # 38.0: the plates' top face round the axis
SLIT_HALF = S.SLIT_W // 2       # 2: the slit is z -2..2
SLIT_HEAD = CX - 2              # its last column
PROUD = 0.5                     # how far a leaf lies over the plates
# the stand-in room: interiors/domeroom's numbers (a3, cursor/c164-a3-domeroom-f3-f4f6)
SKIN_FROM = SKIRT_Y + 2         # 26: a block from here up is the dome's skin
GIRDER = (SKIRT_Y + 1, SKIRT_Y + 2)     # 25..26: the dome's ring girder, over the inner leaf
AROUND = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
SKIN = frozenset([B.VERDIGRIS, B.VERDIGRIS_CAST, *B.VERDIGRIS_CUT.all(), *B.VERDIGRIS_STREAK.all(),
                  *B.IRON_RIVETED.all()])


def rings():
    """The drum's plan in rings of columns: the wall, the inner leaf behind it, the room."""
    body = O.disc(CX, CZ, S.DOME_R)
    inner = O.shrink(body)
    room = O.shrink(inner)
    return body - inner, inner - room, room


# --- the shell ----------------------------------------------------------------------------------------
def _in_slit(x, z):
    return abs(z - CZ) <= SLIT_HALF and x <= SLIT_HEAD


def _cells(tops, col, lowest=SKIRT_Y):
    """[(y, the cell is a slab)] of a column of a shell one block thick, bottom to top: down to the
    top face of its lowest neighbour, so that no gap opens under it."""
    top = tops[col]
    ytop = int(math.ceil(top)) - 1
    low = min(int(math.floor(tops[n])) if n in tops else SKIRT_Y for n in (O.step(col, d) for d in O.SIDES))
    return [(y, y == ytop and top != ytop + 1) for y in range(max(lowest, min(ytop, low)), ytop + 1)]


def _skin(c):
    """The stand-in skin: a half-ellipse rounded to the nearer half block, upright for FOOT_ROWS
    rows over the ring beam, the slit open above its sill, the two leaves lying on the dome beside
    it, each an iron stile and two columns of plate."""
    plate, iron = B.VERDIGRIS_CUT, B.IRON_RIVETED
    tops = {}
    for x, z in O.disc(CX, CZ, S.DOME_R):
        d = math.hypot(x - CX, z - CZ)
        h = SKIRT_Y + (CROWN - SKIRT_Y) * math.sqrt(max(0.0, 1.0 - (d / (S.DOME_R + 0.5)) ** 2))
        tops[(x, z)] = max(math.floor(2.0 * h + 0.5) / 2.0, SKIRT_Y + 1.0 + FOOT_ROWS)
    for col in O.box(CX - 1, CZ - 1, CX + 1, CZ + 1):
        tops[col] = CROWN + 0.5
    tops[(CX, CZ)] = CROWN + 1.0

    def lay(col, cells, family):
        for y, slab in cells:
            c.set(col[0], y, col[1], f"{family.slab}[type=bottom]" if slab else family.block)

    for col in sorted(tops):
        cells = _cells(tops, col)
        if _in_slit(*col):
            cells = [cell for cell in cells if cell[0] <= SILL_Y]
        lay(col, [cell for cell in cells if cell[0] > SKIRT_Y], plate)
        if cells and cells[0][0] == SKIRT_Y:
            c.set(col[0], SKIRT_Y, col[1], iron.block)
    c.set(CX, int(CROWN), CZ, B.VERDIGRIS_CAST)

    leaves = {}                                         # column -> it is the leaf's stile
    for side in (-1, 1):
        for n in range(SLIT_HALF + 1):
            z = CZ + side * (SLIT_HALF + 1 + n)
            for x, zz in tops:
                if zz == z and x <= SLIT_HEAD:
                    leaves[(x, z)] = n == 0
    for col in leaves:
        tops[col] += PROUD
    for col, stile in sorted(leaves.items()):
        lay(col, _cells(tops, col, SILL_Y + 1), iron if stile else plate)


def _shell(c):
    if hasattr(SHELL, "plates"):                        # main/dome's geometry is in the tree
        SHELL.build(c, version=dome.shell_version(), slit="open")
    else:
        SHELL.drum(c)
        _skin(c)


# --- the room -----------------------------------------------------------------------------------------
def _floor(c):
    """The floor's boards with the hole of the pier envelope, and the pier's cap."""
    _wall, _leaf, room = rings()
    x0, z0, x1, z1 = S.PIER_ENVELOPE
    for x, z in room:
        if not (x0 <= x <= x1 and z0 <= z <= z1):
            c.set(x, FLOOR, z, B.FLOOR_WOOD.block)
    px0, pz0, px1, pz1 = S.PIER_CAP
    c.box(px0, FLOOR, pz0, px1, FLOOR, pz1, B.ASHLAR_FINE.block)


def _telescope(c):
    """The great refractor; returns the number of display entities."""
    scope = dome.neighbour("machines", "scope")
    if scope is not None:
        return scope.build(c)
    t = math.radians(TUBE_DEG)

    def cell(along):
        return (int(math.floor(TUBE_PIVOT[0] - along * math.cos(t))),
                int(math.floor(TUBE_PIVOT[1] + along * math.sin(t))), int(math.floor(TUBE_PIVOT[2])))

    c.line(cell(TUBE_ENDS[0]), cell(TUBE_ENDS[1]), B.IRON_PLATE)
    return 0


def _ironwork(c):
    """The stand-in room. Where the skin is and where it is open is read off the canvas, from above
    and before anything is added, as interiors/domeroom reads it."""
    _wall, leaf, room = rings()
    lined = {col for col in room if any(O.step(col, d) in leaf for d in O.SIDES)}
    reach = room | leaf
    iron, wood = B.IRON_RIVETED, B.DARK_WOOD

    def skin(x, y, z):
        name = c.name(x, y, z)
        return name is not None and name.rpartition(":")[2] in SKIN

    soffit = {}                                         # column -> the row under the skin; None: open sky
    for x, z in reach:
        soffit[(x, z)] = None
        for y in range(S.DOME_APEX + 3, SKIN_FROM - 1, -1):
            if skin(x, y, z):
                while y > SKIN_FROM and skin(x, y - 1, z):
                    y -= 1
                soffit[(x, z)] = y - 1
                break
    gap = {col for col, y in soffit.items() if y is None}
    frame = (O.ring(gap) & reach) - gap
    lines = {col[1] for col in frame if any(O.step(col, d) in gap for d in (O.NORTH, O.SOUTH))}
    girders = frame | {col for col in reach - gap if col[1] in lines}       # the curb round the slit, the two arch lines
    cells = {}
    for x, z in leaf:                                   # the dome's ring girder: one row under the open slit
        for y in GIRDER if soffit[(x, z)] is not None else GIRDER[:1]:
            cells[(x, y, z)] = iron.block
    for x, z in reach - gap:                            # the vault: what touches the skin from inside, and over
        top = soffit[(x, z)]                            # the inner leaf everything up to it
        if (x, z) in leaf:
            rows = range(GIRDER[1] + 1, top + 1)
        else:
            rows = [y for y in range(SKIN_FROM, top + 1) if any(skin(x + i, y + j, z + k) for i, j, k in AROUND)]
        for y in rows:
            cells[(x, y, z)] = iron.block if (x, z) in girders else wood.block
    for (x, y, z), state in cells.items():
        if c.name(x, y, z) is None:
            c.set(x, y, z, state)
    # the drum's lining and the fixed ring beam on top of it, but for the column the hand gear's
    # upright shaft climbs; no boards in front of a door or a window
    cols = lined - {dome.RISER_CELL}
    O.Laying(c, None, (0, 0, 0), None).mould(leaf, WALL_TOP, iron.stairs, "top", only=cols)
    for x, z in cols:
        behind = [n for n in (O.step((x, z), d) for d in O.SIDES) if n in leaf]
        for y in range(STAND, WALL_TOP):
            names = [c.name(bx, y, bz) for bx, bz in behind]
            if all(name is not None and "glass" not in name for name in names):
                c.set(x, y, z, wood.block)


def _room(c):
    """The room's lining and ironwork; returns the number of display entities."""
    room = dome.neighbour("interiors", "domeroom")
    if room is not None:
        return room.dress(c)
    _ironwork(c)
    return 0


def build():
    c = Canvas()
    _shell(c)
    _floor(c)
    n = _telescope(c)                                   # the master scene's order: machines before interiors
    n += dome.place(c)
    m = _room(c)
    sky.build(c, (0, 0, 0))                             # the light line's sources go in last
    c.entity_counts = {"machines": n, "interiors": m}
    return c


def write_pack(pack_dir):
    """The sky's pictures (the comet stands in the slit) and the repainted stone, copper and iron
    the gear is judged against."""
    return list(sky.pack(pack_dir) or []) + list(materials.pack(pack_dir) or [])


def shots():
    """V8 as the card asks (the gear in one picture with the tube), its twin north of the tube and
    V8 in the afterglow; then what a visitor sees from the floor (the room, the ring across it, the
    slit's foot from the hand chain, the weights, the hand gear); and close views from a ladder's
    height (the ring, the pinion in the toothed ring from below, the slit's foot, a weight), in
    the afterglow, the most light the room gets: these are for judging the parts. With main/dome's
    version b the slit's gear runs up the rails, and four more follow it: the chains from the
    floor, the curtain on its roller, the sheaves at the slit's head, the slit's foot from outside."""
    out = []

    def shot(name, pos, look_at, time=TIME):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": time})

    def spot(at, z=0.0):
        return (AX + at[0], at[1], AZ + z)

    eye = STAND + S.EYE
    b = dome.shell_version() == "b"
    foot = spot(dome.winch_at()) if b else spot(dome.F0)            # the middle of the slit's foot gear
    weight = spot(dome.on_run(dome.WEIGHT_S1 if b else dome.WEIGHT_S0, dome.DOWN_D), dome.RUN_Z)   # the south weight
    gx, gz = AX + dome.riser_at()[0], AZ + dome.riser_at()[1]       # the hand gear's upright shaft
    # the room's V8: interiors/domeroom's stand and aim until the skeleton has the view, so that the
    # pictures of the two packages can be laid side by side
    v8 = getattr(S, "V8", None) or dict(pos=(11.8, eye, 2.2), look_at=(0.0, 25.2, 0.9))
    shot("v8", v8["pos"], v8["look_at"])
    shot("v8_north", (v8["pos"][0], v8["pos"][1], v8["pos"][2] - 2.0), v8["look_at"])
    shot("v8_glow", v8["pos"], v8["look_at"], GLOW)
    shot("room", (AX + 6.0, eye, AZ - 7.0), (AX - 6.0, STAND + 5.0, AZ + 3.0))
    shot("ring_far", (AX + 8.0, eye, AZ + 3.0), (AX - 8.0, STAND + 6.5, AZ + 8.0))
    shot("slit_foot_up", (AX - 6.5, eye, AZ + 1.5), foot)
    shot("weights", (AX - 3.0, eye, AZ + 6.5), (weight[0], weight[1], AZ + 1.5) if b else (AX - 9.0, STAND + 10.5, AZ + 3.0))
    shot("hand_gear", (gx + 1.9, eye, gz + 2.1), (gx + 0.2, STAND + 1.3, gz))
    shot("hand_gear_up", (AX - 3.0, eye, AZ - 6.5), (gx, STAND + 4.5, gz))
    shot("ring_near", (AX - 4.0, STAND + 7.0, AZ + 6.0), (AX - 7.95, STAND + 6.4, AZ + 7.95), GLOW)
    shot("mesh", (gx + 2.2, dome.RING_Y - 2.4, gz + 2.6), (gx - 0.2, dome.RING_Y - 0.2, gz - 0.3), GLOW)
    shot("slit_foot", (AX - 6.0, STAND + 7.3, AZ + 2.5), foot, GLOW)
    shot("weight_near", (AX - 6.0, STAND + 8.5, AZ), weight if b else (AX - 9.5, STAND + 10.0, AZ + 3.0), GLOW)
    if b:
        north = -dome.HAUL_Z / dome.PX
        shot("chains", (AX + 3.0, eye, AZ + 4.0), spot(dome.on_curve(45.0), north))
        shot("curtain", (AX - 8.5, STAND + 10.0, AZ + 1.0), spot(dome.roll_at()), GLOW)
        shot("slit_head", (AX - 4.0, STAND + 16.0, AZ), spot(dome.on_curve(dome.HEAD_DEG, dome.GAP / 2.0), north), GLOW)
        shot("foot_outside", (AX - 18.0, STAND + 15.0, AZ + 5.0), spot(dome.roll_at()), GLOW)
    return out
