"""Test scene of the work package props/steam-mains: the steam main on the real wall.

The wall is not a stand-in. It is the south wing of the main building's east front, all five bays
of it, between the return of the middle pavilion (row 6) and the return of the south end pavilion
(row 26), laid by A3's elevation grammar (main/_order) with the main building's own order
(main/facade.order()) on the skeleton's own columns. Plan coordinates are scene coordinates, so
steam.dress() and pipes.dress(), the functions that dress the master scene, run here unchanged and
find the same stones: the rainwater pipes stand in the two corners the main has to keep clear of.

What it shows: the heating main of the south wing (props/steam_mains.east_front) from the pilaster it
leaves to the bend that takes it into the wall -- plates where it goes through a pilaster,
brackets, bolted joints, the red rings of its medium, the stop valve, the steam trap on the plinth's
step, the copper bend round the last pilaster: five pieces in all. What moves is not in a picture: the valve's gland weeps and the trap blows (the
motion line's particles; check.py counts them).

The door's bays north of row 6 are not in the scene. gallery.py lays the package's own models out
(props.GALLERY).

The shots are written from the numbers below:  python -m scenes.obs_props_steam_mains
"""
from artkit.blocks import st
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.main import _order as O
from scenes.obs.main import _plan as P
from scenes.obs.main import facade
from scenes.obs.props import pipes
from scenes.obs.props import steam_mains as steam
from scenes.obs.site import _kit as site

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)

# ---- the plan: the skeleton's own columns ----------------------------------------------------------
Z0, Z1 = P.CROSS_Z[1], P.PAVILION_Z[1]          # 6 and 26: the two returns the wing stands between
BACK = S.WALL_E - 7                             # 8: the stretch is cut this far behind the front
PAVING = (BACK - 3, Z0 - 5, S.WALL_E + 27, Z1 + 5)      # x0, z0, x1, z1 of the terrace laid before it
GLOW = {B.WINDOW_LIT.block: 10, B.WINDOW_FROSTED.block: 10, B.WINDOW_CURTAIN.block: 9}   # as materials/windows


def footprint():
    return {(x, z) for z in range(Z0, Z1 + 1) for x in range(BACK, P.east_face(z) + 1)}


def _classify(x, z, outs):
    """The east front as main/facade classifies it; the returns and the sides where the stretch is
    cut out of the building are plain wall."""
    if "east" in outs:
        if P.on_pilaster(z):
            return O.Pier(out=("east",))                # also where the front steps: the return stays plain
        return O.Bay("east", P.bays_at(z)[0])
    return None


def plan():
    return O.Plan(footprint(), _classify)


def _rooms(c, windows):
    """What stands behind the wall: a room to each bay, so a lit window lights its own reveal and
    not its neighbour's; a floor under the main storey and a deck over it. The lamps behind lit
    glass are the ones materials/windows sets."""
    fine, rough = B.ASHLAR_FINE.block, B.ASHLAR_ROUGH.block
    for z in range(Z0 + 1, Z1):
        for x in range(BACK + 1, P.east_face(z)):
            c.set(x, S.ROOF_FLOOR, z, facade.DECK)
    for z in range(Z0 + 1, Z1):
        cross = P.on_pilaster(z)
        for x in range(BACK + 1, P.east_face(z) - 1):
            c.set(x, S.STRING, z, fine)
            if cross:
                for y in range(S.GROUND, S.ROOF_FLOOR):
                    c.set(x, y, z, rough)
    for w in windows:
        level = GLOW.get(w["glass"])
        if level:
            x, z = w["cells"][len(w["cells"]) // 2]
            y0, y1 = w["y"]
            for y in ((y0 + 1, y1 - 1) if y1 - y0 > 2 else (y0,)):
                c.set(x + w["inward"][0], y, z + w["inward"][1], st(B.LIGHT, level=level))


def build():
    c = Canvas()
    x0, z0, x1, z1 = PAVING
    c.box(x0, S.GROUND - 1, z0, x1, S.GROUND - 1, z1, site.FIELD)
    c.box(site.FOOT_STRIP_X, S.GROUND - 1, z0, site.FOOT_STRIP_X, S.GROUND - 1, z1, site.STRIP)
    windows = O.build(c, plan(), facade.order(), glass=facade.glass)
    _rooms(c, windows)
    rain = pipes.dress(c)               # the rainwater pipes in the two corners, as the master scene has them
    n = steam.dress(c)
    sky.build(c, (0, 0, 0))             # A2's light sources go in last, when every piece is in place
    c.entity_counts = {"props": rain + n}
    return c


def write_pack(pack_dir):
    """The repainted stone, copper and glass the main is judged against, and the map's sky: the
    scene stands in the map's hour, and without the sky's pack the game's own sun stands in it."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


def shots():
    """The cameras. The first two stand where the board's V3 and V4 stand; the others walk along the
    foot of the wall."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(float(v), 2) for v in pos],
                    "look_at": [round(float(v), 2) for v in look_at], "time": TIME})

    x, y = steam.front_line()
    places = steam.front_places()
    start = float(S.pilaster_z(steam.FRONT_FROM))
    last = float(S.pilaster_z(steam.FRONT_BAYS[-1]))
    valve, trap, end = places["valve"][0], places["trap"][0], places["end"][0]
    turn = S.pilaster_z(steam.FRONT_ROUND) + 0.5        # the middle of the pilaster the bend goes round
    bend = x + steam.LOOP_OUT / 16.0                    # the bend's outer length
    joint = places["bay"][-1]                           # the bolted joint of the bay before the valve

    shot("board_v3", (24.5, S.EYE, 12.5), (16.5, 6.5, 6.5))
    shot("board_v4", (27.5, S.EYE, 3.5), (17.5, 4.5, 0.5))
    shot("front", (x + 14.0, S.EYE, (start + end) / 2.0), (x, 3.0, (start + end) / 2.0))
    shot("ten", (x + 10.0, S.EYE, trap), (x, y, trap))                  # the fine rule's two looks at one
    shot("two", (x + 2.0, S.EYE, trap + 0.4), (x, y - 0.1, trap + 0.4))     # place: from 10 blocks and from 2
    shot("along_north", (x + 1.6, S.EYE, start + 1.5), (x, y, turn))
    shot("along_south", (x + 1.9, S.EYE, end - 1.8), (x, y, last + 2.0))
    shot("walk", (x + 4.5, S.EYE, valve + 4.0), (x, y, trap))
    shot("valve", (x + 2.1, y + 0.5, valve + 1.5), (x, y, valve - 0.3))
    shot("trap", (x + 2.2, y + 0.25, trap - 0.9), (x + 0.35, y - 0.4, trap))
    shot("bend", (bend + 2.2, y + 1.5, turn + 1.9), (bend - 0.5, y, turn))
    shot("bend_under", (bend + 1.2, S.EYE - 0.5, turn - 2.2), (bend - 0.3, y, turn))
    shot("into_wall", (x + 1.7, y + 0.5, end - 1.6), (x, y, end))
    shot("joint", (x + 1.8, y + 0.4, joint + 0.9), (x, y, joint - 0.2))
    shot("start", (x + 2.4, y + 0.5, start - 2.6), (x, y, start))
    return out
