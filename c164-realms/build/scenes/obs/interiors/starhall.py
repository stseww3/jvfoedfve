"""Work package interiors/starhall: the entrance hall ("star hall"), plan ART-PLAN 8.

The star piece is the great orrery hung in the full-height central well. Round it: the stone floor
with its brass meridian and the roundel under the orrery, the mother clock on the telescope pier,
the switchboard, star charts, the gallery with its iron rail, a coffered ceiling. The hall is written
in the skeleton's scene coordinates (A0 g2 #207, #220): it dresses whatever shell stands there, laying
the floor and ceiling finish and filling the wall faces, and never builds the shell, the pier, the
gallery deck, the stairs or the machines (those are c231, c236, c238).

Two versions for the director to choose between (card packages/interiors/starhall.md, as A0 re-set it
in g2 #207 -- the layout is now locked, so the two differ in dress, not in plan):
  a  "academic"  symmetric and formal: a black-and-white chequer floor, ashlar pilasters on the bay
                 beat, a coffered dark-wood ceiling with a ring of brass stars.
  b  "workshop"  a working hall: cast iron and wood, a warm/cool two-tone stone floor with an iron
                 walk on the meridian, iron pilasters and an iron-panelled ceiling, tools on the wall.

Light (plan 3.2; the hall is warm and dark, a notch under the entrance): the orrery's sun is the
focus, the main light falls over the mother clock and from the gallery brackets, every other lamp is a
caged bulb. The placing offers these to A2/A8 (c220/c177) as (cell, level); in the box it drops the
light blocks itself so the scene renders.

Stand-ins until the deliveries arrive (see _stubs): the orrery and the clock (c236/c238), the
switchboard, benches, charts, globes, lamps (A5/c179/c220). The room places no display entity yet, so
it returns 0 against the indoor budget.

build() is what the master scene calls; it places nothing until MOVED_IN is set (c231's shell in the
master scene and a version chosen). Until then the hall lives in its box test scene
(build/scenes/obs_int_starhall), which calls build_box().
"""
import math

from ..common import blocks as B
from ..common import skeleton as S
from . import _shell as H
from . import _stubs as T

MOVED_IN = False            # set once c231's shell is in the master scene and a version is chosen
VERSION = "a"

# --- where the dress gathers (cells / courses) --------------------------------------------------
ORRERY = (int(S.ORRERY_CENTRE[0] - 0.5), int(S.ORRERY_CENTRE[1] - 0.5))   # (11, 0), the cell under it
ORRERY_RING_Y = int(S.ORRERY_RING_Y)            # 8, the orbit course the stand-in orrery sits on
ROUNDEL_R = S.ORRERY_R                           # 2.5, the brass roundel in the floor matches the orbit
MERIDIAN_Z = int(S.AXIS_Z - 0.5)                # 0, the central cell the brass meridian runs along
CLOCK_X = int(S.MOTHER_CLOCK["back_x"])         # 6, the pier's east face: the clock and the west end
#                                                 of the meridian
CLOCK_Y = (int(S.MOTHER_CLOCK["y"][0]), int(S.MOTHER_CLOCK["y"][1]))      # 1..5

BAY = S.BAY                                      # 4: the pilasters fall on this beat in x, as in z
PIL_X = tuple(range(H.X0, H.X1 + 1, BAY))        # 2, 6, 10: the depth bays of the hall
PIL_Z = (H.Z0, H.Z1)                            # the pilasters also stand on the north and south walls
CORNICE_Y = S.FRIEZE - 2                         # 12, a string course high on the wall breaks the ashlar
FRIEZE_Y = S.STRING                              # 6, the gallery course doubles as the low string course

# --- light (cell, level); the hall is a notch under the entrance's 13..14 (plan 3.2) -------------
SUN = 12                    # the orrery's sun, the one focus
CLOCK_GLOW = 10            # the pool over the mother clock, the main light of the west end
BRACKET = 7               # the gallery and wall brackets, third rank
DIAL = 6                  # the switchboard's pilot lamps and the clock dial

# bottom course first; the switchboard's instrument panels (c164 blocks.PANELS)
BOARD_A = (("knife_switch", "dial", "gauges", "dial", "knife_switch"),
           ("pilot_lamps", "relays", "nameplate", "relays", "pilot_lamps"))
BOARD_B = (("knife_switch", "fuses", "bus_switch", "fuses", "gauges", "knife_switch"),
           ("dial", "gauges", "patch_panel", "counter", "dial", "pilot_lamps"),
           ("pilot_lamps", "relays", "nameplate", "relays", "pilot_lamps", "bell"))

STYLE = {
    "a": dict(
        pale=B.ASHLAR_FINE.block, dark=B.SLATE_SMOOTH.block, chequer=True, walk=None,
        pilaster=B.ASHLAR_FINE.block, capital=B.ASHLAR_EMBLEM, base=B.ASHLAR_PANEL.block,
        coffer=B.DARK_WOOD.block, beam=B.IRON_RIVETED.block, star=B.BRASS_PLATE.block,
        board=dict(x=(6, 10), rows=BOARD_A),
        benches=[("north", range(8, 12)), ("south", range(8, 12))],
        charts=[("north", (7, 9, 11), 9), ("south", (7, 9, 11), 9)],
        cases=[(9, H.Z0 + 2, B.VERDIGRIS), (9, H.Z1 - 2, B.IRON_CAST)],
        brackets=[("north", 6), ("north", 10), ("south", 6), ("south", 10)],
    ),
    "b": dict(
        pale=B.TUFF_BRICK.block, dark=B.SLATE_SMOOTH.block, chequer=False, walk=B.IRON_GRATE,
        pilaster=B.IRON_RIVETED.block, capital=B.IRON_PLATE, base=B.IRON_PLATE,
        coffer=B.IRON_PLATE, beam=B.IRON_RIVETED.block, star=None,
        board=dict(x=(3, 8), rows=BOARD_B),
        benches=[("south", range(8, 13))],
        charts=[("north", (10, 11, 12), 9), ("north", (10, 11, 12), 11), ("south", (8, 10), 9)],
        cases=[(10, H.Z1 - 2, B.VERDIGRIS)],
        brackets=[("north", 4), ("north", 8), ("north", 12), ("south", 8), ("south", 12)],
    ),
}


def dress(c, origin=(0, 0, 0), version="a", standin=False):
    """Dress the hall standing at `origin`. standin: let the wall brackets sit in the stand-in walls,
    which is right only in the box; in the real shell they are lamp models and a light beside each.
    Returns dict(entities=<display entities placed>, lights=[(x, y, z, level), ...])."""
    st = STYLE[version]
    ox, oy, oz = origin
    pier = H.pier_cells()
    deck, rail = H.gallery_cells(), H.rail_cells()
    lights = []

    def put(x, y, z, state):
        c.set(ox + x, oy + y, oz + z, state)

    def free(x, y, z):
        return not c.has(ox + x, oy + y, oz + z)

    def light(x, y, z, level):
        lights.append((x, y, z, level))
        if free(x, y, z):
            put(x, y, z, f"{B.LIGHT}[level={level}]")

    _floor(put, st)
    _ceiling(put, st, pier)
    _walls(put, free, st, pier, deck)
    _gallery(put, deck, rail)

    # the star piece and the clock, both stand-ins until c236/c238 arrive
    T.orrery(put, ORRERY[0], ORRERY[1], ORRERY_RING_Y, H.CEIL)
    T.mother_clock(put, CLOCK_X, MERIDIAN_Z, CLOCK_Y[0], CLOCK_Y[1])

    # the three layers of small pieces: wall (switchboard, charts), surface (benches, cases), floor
    bx0, bx1 = st["board"]["x"]
    T.switchboard(put, [(x, H.Z0) for x in range(bx0, bx1 + 1)], S.GROUND, "south", st["board"]["rows"])
    for wall, xs in st["benches"]:
        T.bench(put, [(x, H.Z0 if wall == "north" else H.Z1) for x in xs], wall)
    for wall, xs, y in st["charts"]:
        T.charts(put, [(x, H.Z0 if wall == "north" else H.Z1) for x in xs], y, wall)
    for x, z, block in st["cases"]:
        T.case(put, x, z, "north" if z < 0 else "south")
        T.globe(put, x + 1, z, block)

    # light: the sun is the focus, the clock pool the main light, a bracket on the gallery beats
    light(ORRERY[0], ORRERY_RING_Y - 1, ORRERY[1], SUN)
    light(CLOCK_X + 1, CLOCK_Y[1] + 1, MERIDIAN_Z, CLOCK_GLOW)
    light((bx0 + bx1) // 2, S.GROUND + 2, H.Z0 + 1, DIAL)
    for wall, x in st["brackets"]:
        wz = (H.Z0, 1) if wall == "north" else (H.Z1, -1)
        if standin:
            T.wall_lamp(put, x, S.STAND + 1, wz[0])
        light(x, S.STAND + 1, wz[0] + wz[1], BRACKET)
    return {"entities": 0, "lights": lights}


def _floor(put, st):
    """The stone floor: a chequer or a two-tone band, the brass meridian down the axis from the door
    to the pier, and the brass roundel under the orrery."""
    pier = H.pier_cells()
    for x in range(H.X0, H.X1 + 1):
        for z in range(H.Z0, H.Z1 + 1):
            if (x, z) in pier:
                continue
            if st["chequer"]:
                pale = (x + z) % 2 == 0
            else:
                pale = (x // 2) % 2 == 0                 # broad bands, so iron walks read against them
            put(x, H.FLOOR, z, st["pale"] if pale else st["dark"])
    # the brass roundel under the orrery (a star-map disc with a bright rim), matching the orbit
    for dx in range(-3, 4):
        for dz in range(-3, 4):
            r = round(math.hypot(dx, dz))
            x, z = ORRERY[0] + dx, ORRERY[1] + dz
            if r <= 2 and (x, z) not in pier and H.X0 <= x <= H.X1 and H.Z0 <= z <= H.Z1:
                put(x, H.FLOOR, z, B.BRASS_PLATE.block if r == 2 else B.BRASS_PATTERN.block)
    # the brass meridian, a carpet on the floor from the pier's east foot to the east threshold
    for x in range(CLOCK_X, H.EAST_FACE + 1):
        if (x, MERIDIAN_Z) not in pier:
            put(x, S.GROUND, MERIDIAN_Z, B.BRASS_INLAY)
    # an iron walk laid on the meridian in the workshop version
    if st["walk"]:
        for x in range(CLOCK_X + 1, H.X1 + 1):
            if (x, MERIDIAN_Z) not in pier:
                put(x, H.FLOOR, MERIDIAN_Z, st["walk"])


def _ceiling(put, st, pier):
    """A beamed and coffered ceiling: cast-iron beams on the bay beat, coffers of dark wood (academic)
    or iron (workshop), a brass boss where the orrery hangs, and a few brass stars (academic)."""
    for x in range(H.X0, H.X1 + 1):
        for z in range(H.Z0, H.Z1 + 1):
            if (x, z) in pier:
                continue
            beam = x in PIL_X or z in (H.Z0, H.Z1) or z == MERIDIAN_Z or x == H.EAST_GLASS - 1
            put(x, H.CEIL, z, st["beam"] if beam else st["coffer"])
    put(ORRERY[0], H.CEIL, ORRERY[1], B.BRASS_PATTERN.block)                 # the boss the orrery hangs from
    for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        put(ORRERY[0] + dx, H.CEIL, ORRERY[1] + dz, B.BRASS_PLATE.block)     # a small rose round it
    if st["star"]:
        for x in range(H.X0 + 1, H.X1, 2):
            for z in (H.Z0 + 2, H.Z1 - 2):
                if (x, z) not in pier and (x, z) != ORRERY:
                    put(x, H.CEIL, z, st["star"])


def _walls(put, free, st, pier, deck):
    """A dark dado round the hall, pilasters on the bay beat with a capital and a base, and a high
    string course, so no ashlar face runs flat over 5x5."""
    def dado(x, z, wall, y0):
        for y in (y0, y0 + 1):
            if (x, z) not in pier and free(x, y, z):
                put(x, y, z, T.panel(B.WAINSCOT, wall))

    # the dado at the ground and again at the gallery, on the north, south and west faces
    for base in (S.GROUND, S.STAND):
        for x in range(H.X0, H.X1 + 1):
            dado(x, H.Z0, "north", base)
            dado(x, H.Z1, "south", base)
        for z in range(H.Z0, H.Z1 + 1):
            dado(H.X0, z, "west", base)

    # pilasters on the north and south walls, on the depth beat; a capital and a base
    for x in PIL_X:
        for z in PIL_Z:
            for y in range(S.GROUND, CORNICE_Y):
                if (x, z) not in pier:
                    put(x, y, z, st["pilaster"])
            put(x, S.GROUND, z, st["base"])
            put(x, CORNICE_Y, z, st["capital"])

    # a string course high on each wall, and one at the gallery, to break the flat ashlar
    for y in (FRIEZE_Y, CORNICE_Y):
        for x in range(H.X0, H.X1 + 1):
            for z in (H.Z0, H.Z1):
                if (x, z) not in pier and x not in PIL_X:
                    put(x, y, z, st["capital"] if y == CORNICE_Y else B.ASHLAR_FINE.slab + "[type=top]")


def _gallery(put, deck, rail):
    """Dress the gallery the shell deck carries: a brass top rail over the iron bars and an iron
    corbel under each rail cell, so the balcony reads from the floor."""
    for x, z in rail:
        put(x, S.STAND, z, B.IRON_BARS)
        put(x, H.DECK - 1, z, B.IRON_RIVETED.slab + "[type=top]")        # the corbel under the deck


def build_box(c, origin=(0, 0, 0), version="a"):
    """The box test scene's room: the stand-in shell, dressed."""
    H.star_hall(c, origin)
    return dress(c, origin, version, standin=True)


def build(canvas, origin=(0, 0, 0)):
    if not MOVED_IN:
        return 0
    return dress(canvas, origin, VERSION)["entities"]
