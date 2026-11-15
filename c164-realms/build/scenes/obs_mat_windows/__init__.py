"""Test scene of the work package materials/windows (plan/packages/materials/windows.md).

The six windows where they will be used. Everything faces east, as the entrance front of the main
building does, and is looked at from the east. Along z, from the north:

    facade    ten bays of the entrance front, cut as the skeleton cuts it: plinth, rough base with
              small windows, string course, sunk panel, the tall window with the hint of an arch,
              frieze, a cornice two blocks out, parapet; pilasters one block out, glass one block
              in. Sixteen of its twenty windows are lit and four are dark, no two dark ones in
              neighbouring bays. The cell behind the glass is kept free for the sky line's invisible
              lights, and holds them here by the table of plan/parts/sky.md 6: two in a tall window,
              one in a small one, at level 9 or 10, so the stone round a lit window is warm.
              It stands alone, far enough from the rest to be looked at from the forecourt's distance.
    walls     each window as six by six glass blocks flush in a frame of fine stone: the three lit
              ones, then the three dark ones. No lamp anywhere near: a lit window shows its picture
              by itself, a dark one holds the sky. The roof light, the one window to see through,
              has a lamp-lit room behind it.
    panes     a wall with a window of panes for each of the six, and a free screen of frosted panes
              that turns a corner: the edges, the post, both faces of a pane.
    roof      the roof light where its name puts it: lying flat, six by six, over a lamp room.
    compass   a square lantern with the same four rows on every side (lit, frosted, curtain, dark):
              the place to measure that a lit window shows the colours of its picture whichever way
              it faces, and what the four ways do to a dark one.

    python -m scenes.obs_mat_windows        writes shots.json from the layout below

The second version of the lit windows is the scene obs_mat_windows_b: this board and these shots,
with windows="b" asked of the materials' pack.
"""
from artkit.blocks import st
from artkit.canvas import Canvas

from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.materials import _kit as K

BIOME = "obs_blue"
TIME = 14000                    # light version A; 18000 is B and 12900 is C
VERSIONS = {}                   # material package -> version; every package's default when empty

FLOOR = B.SLATE_SMOOTH.block
FINE, ROUGH = B.ASHLAR_FINE, B.ASHLAR_ROUGH
# one letter for each window, in the order they are shown
KIND = {"L": B.WINDOW_LIT, "F": B.WINDOW_FROSTED, "C": B.WINDOW_CURTAIN,
        "D": B.WINDOW_DARK, "B": B.WINDOW_BLIND, "S": B.SKYLIGHT}
NAME = {"L": "lit", "F": "frosted", "C": "curtain", "D": "dark", "B": "blind", "S": "skylight"}
# The invisible light in the first cell behind a lit window. These stand in for the sky line's own
# (plan/parts/sky.md 6: second rank, 9 to 10 behind a lit window, never 15); a dark window has none.
# They are set here and not through scenes.obs.sky.build(): the sky line has no light package yet,
# and when it has one these become its suggest() calls.
LAMP = {"L": 10, "F": 10, "C": 9}
ROOM_LAMP = 12                  # the lamp of a room that is looked into through the roof light

# ---- the facade: ten bays of the entrance front ---------------------------------------------------------
BAYS = 10
MAIN = "LCLDLLFLDL"             # the tall windows, north to south
BASE = "BLLLCDLCLF"             # the small windows of the base storey under them
BASE_WINDOW = (3, 4)            # y of the small windows: three wide, two high
WALL = S.DEPTH_WALL             # x of the wall face; the scene's x is the skeleton's depth from it
GLASS = S.DEPTH_GLASS
ROOM = GLASS - 1                # the cell behind the glass: the sky line's
BACK = ROOM - 1


def _light(c, x, y, z, kind):
    if kind in LAMP:
        c.set(x, y, z, st(B.LIGHT, level=LAMP[kind]))


def _recessed(c, kind, z, y0, y1, lamps):
    """A window three wide in the solid wall: the opening, the glass one block in, the free cell
    behind it, and in that the lights of a lit window at the heights given."""
    c.carve(WALL, y0, z, WALL, y1, z + 2)
    c.box(GLASS, y0, z, GLASS, y1, z + 2, KIND[kind].block)
    c.carve(ROOM, y0, z, ROOM, y1, z + 2)
    for y in lamps:
        _light(c, ROOM, y, z + 1, kind)


def facade(c, z):
    end = z + S.BAY * BAYS                              # the last pilaster
    out, eaves = WALL + S.DEPTH_PILASTER, WALL + S.DEPTH_CORNICE
    for (y0, y1), block in ((S.PLINTH, B.SLATE_BRICK.block), (S.BASE, ROUGH.block),
                            ((S.STRING, S.CORNICE), FINE.block)):
        c.box(BACK, y0, z, WALL, y1, end, block)        # solid: every window gets a room of its own
    c.box(WALL, S.PARAPET[0], z, WALL, S.PARAPET[1], end, FINE.block)
    c.box(out, S.PLINTH[0], z, out, S.PLINTH[1], end, B.SLATE_BRICK.block)
    c.box(out, S.STRING, z, out, S.STRING, end, st(FINE.slab, type="top"))
    c.box(out, S.CORNICE, z, out, S.CORNICE, end, FINE.block)
    c.box(eaves, S.CORNICE, z, eaves, S.CORNICE, end, st(FINE.slab, type="top"))
    for k in range(BAYS + 1):
        pz = z + S.BAY * k
        c.box(out, S.BASE[0], pz, out, S.BASE[1], pz, ROUGH.block)
        c.box(out, S.STRING, pz, out, S.WINDOW[1], pz, FINE.block)
        c.set(out, S.FRIEZE, pz, B.ASHLAR_EMBLEM)
    for k in range(BAYS):
        w = z + S.BAY * k + 1                           # the bay's windows are at w .. w + 2
        c.box(WALL, S.PANEL, w, WALL, S.PANEL, w + 2, B.ASHLAR_PANEL.block)
        c.set(WALL, S.FRIEZE, w + 1, B.ASHLAR_EMBLEM)   # the keystone
        _recessed(c, MAIN[k], w, S.WINDOW[0], S.WINDOW[1], lamps=(S.WINDOW[0] + 1, S.WINDOW[1] - 1))
        c.set(WALL, S.WINDOW[1], w, st(FINE.stairs, half="top", facing="north"))
        c.set(WALL, S.WINDOW[1], w + 2, st(FINE.stairs, half="top", facing="south"))
        _recessed(c, BASE[k], w, BASE_WINDOW[0], BASE_WINDOW[1], lamps=(BASE_WINDOW[0],))
    c.box(BACK, -1, z - 3, 14, -1, end + 3, FLOOR)
    return end + 1


def bay_mid(z, bay):
    """The middle, as a point, of bay 1 .. BAYS of a facade that starts at z."""
    return S.mid(z + S.BAY * (bay - 1) + 1, z + S.BAY * (bay - 1) + 3)


# ---- the six windows as walls of glass blocks ---------------------------------------------------------------
N = 8                           # a wall is N by N, its glass N - 2 by N - 2
PITCH = N + 2
ORDER = "LFCDBS"


def _room(c, z):
    """What is seen through the roof light when it stands in a wall: a wainscoted room, a row of
    instruments, a lamp."""
    c.box(-5, 0, z, -1, N - 1, z + N - 1, FINE.block)
    c.carve(-4, 1, z + 1, -1, N - 2, z + N - 2)
    c.box(-5, 1, z + 1, -5, 3, z + N - 2, B.DARK_WOOD.block)
    c.box(-5, 4, z + 1, -5, N - 2, z + N - 2, B.FLOOR_WOOD.block)
    for dz, name in ((2, "dial"), (3, "gauges"), (4, "pilot_lamps"), (5, "knife_switch")):
        c.set(-5, 4, z + dz, st(B.PANELS[name], facing="east"))
    c.box(-4, 0, z + 1, -1, 0, z + N - 2, B.FLOOR_WOOD.block)
    c.box(-3, 1, z + 3, -3, 1, z + 4, B.PALE_WOOD.block)
    c.set(-2, N - 3, z + 3, st(B.LIGHT, level=ROOM_LAMP))


def walls(c, z):
    for i, kind in enumerate(ORDER):
        w = z + PITCH * i
        c.box(WALL, 0, w, WALL, N - 1, w + N - 1, FINE.block)
        c.box(WALL, 1, w + 1, WALL, N - 2, w + N - 2, KIND[kind].block)
        if kind == "S":
            _room(c, w)
    end = z + PITCH * len(ORDER) - 2
    c.box(-6, -1, z - 2, 14, -1, end + 1, FLOOR, keep=True)
    return end


def wall_mid(z, kind):
    return z + PITCH * ORDER.index(kind) + N / 2.0


# ---- panes ----------------------------------------------------------------------------------------------------
PANE_H = (1, 4)                 # a window of panes is two wide and this high
PANE_PITCH = 3


def panes(c, z):
    """A window of panes for each of the six, set in the wall itself, and a free screen."""
    width = PANE_PITCH * len(ORDER) + 1
    c.box(BACK + 1, 0, z, WALL, PANE_H[1] + 1, z + width - 1, FINE.block)
    for i, kind in enumerate(ORDER):
        w = z + PANE_PITCH * i + 1
        c.box(WALL, PANE_H[0], w, WALL, PANE_H[1], w + 1, st(KIND[kind].pane, north="true", south="true"))
        c.carve(WALL - 1, PANE_H[0], w, WALL - 1, PANE_H[1], w + 1)
        _light(c, WALL - 1, PANE_H[0] + 1, w, kind)
    s = z + width + 2                                   # the free screen: four along z, then two to the east
    pane = B.WINDOW_FROSTED.pane
    for y in range(3):
        c.set(WALL, y, s, st(pane, south="true"))
        c.set(WALL, y, s + 1, st(pane, north="true", south="true"))
        c.set(WALL, y, s + 2, st(pane, north="true", south="true"))
        c.set(WALL, y, s + 3, st(pane, north="true", east="true"))
        c.set(WALL + 1, y, s + 3, st(pane, west="true", east="true"))
        c.set(WALL + 2, y, s + 3, st(pane, west="true"))
    c.box(-6, -1, z - 6, 14, -1, s + 9, FLOOR, keep=True)
    return s + 4


# ---- the roof light lying flat ----------------------------------------------------------------------------------
ROOF_X = -4                     # the lamp room is N by N, from here to the east
ROOF_Y = 3


def roof(c, z):
    x = ROOF_X
    c.box(x, 0, z, x + N - 1, ROOF_Y, z + N - 1, FINE.block)
    c.carve(x + 1, 0, z + 1, x + N - 2, ROOF_Y, z + N - 2)
    c.box(x + 1, ROOF_Y, z + 1, x + N - 2, ROOF_Y, z + N - 2, B.SKYLIGHT.block)
    c.box(x + 1, -1, z + 1, x + N - 2, -1, z + N - 2, B.FLOOR_WOOD.block)
    c.box(x + 3, 0, z + 3, x + 4, 0, z + 4, B.PALE_WOOD.block)
    c.set(x + 3, 1, z + 3, st(B.LIGHT, level=ROOM_LAMP))
    c.box(-6, -1, z - 6, 14, -1, z + N + 9, FLOOR, keep=True)
    return z + N


# ---- the lantern with four equal sides --------------------------------------------------------------------------
COMPASS_X = 4                   # five by five, from here to the east
ROWS = "DCFL"                   # from the foot up


def compass(c, z):
    x = COMPASS_X
    c.box(x, 0, z, x + 4, len(ROWS) + 1, z + 4, FINE.block)
    c.carve(x + 1, 1, z + 1, x + 3, len(ROWS), z + 3)
    for i, kind in enumerate(ROWS):
        block = KIND[kind].block
        c.box(x + 1, 1 + i, z, x + 3, 1 + i, z, block)              # north
        c.box(x + 1, 1 + i, z + 4, x + 3, 1 + i, z + 4, block)      # south
        c.box(x, 1 + i, z + 1, x, 1 + i, z + 3, block)              # west
        c.box(x + 4, 1 + i, z + 1, x + 4, 1 + i, z + 3, block)      # east
    c.box(-6, -1, z - 10, 14, -1, z + 14, FLOOR, keep=True)
    return z + 5


# name, how to build it, the free z before it. The facade is looked at from 46 blocks: at that
# distance a picture is 130 blocks wide, and nothing else is to stand in it.
STATIONS = [("facade", facade, 0), ("walls", walls, 46), ("panes", panes, 6), ("roof", roof, 6),
            ("compass", compass, 10)]


def layout(c=None):
    """Where each station stands: {name: (first z, z after it)}. Builds into `c` when given one."""
    c = c or Canvas()
    spans, z = {}, 0
    for name, station, gap in STATIONS:
        z += gap
        end = station(c, z)
        spans[name] = (z, end)
        z = end
    return spans


def build():
    c = Canvas()
    layout(c)
    return c


def build_models():
    return {}           # blocks only


def write_pack(pack_dir):
    return K.pack_with(pack_dir, **VERSIONS)


def shots():
    """The facade from the front in the three light versions, from the forecourt's distance, along
    its face and from near; the walls three at a time and one by one; the panes; the roof light from
    above; the lantern from its four sides at one distance."""
    spans, out = layout(), []

    def shot(name, pos, look_at, time=TIME):
        out.append({"name": name, "pos": [round(float(v), 2) for v in pos],
                    "look_at": [round(float(v), 2) for v in look_at], "time": time})

    z = spans["facade"][0]
    mid = S.mid(z, z + S.BAY * BAYS)
    for name, time in (("front", TIME), ("front_b", 18000), ("front_c", 12900)):
        shot(name, (17.0, 8.5, mid), (0, 8.5, mid), time)
    shot("far", (46.0, 1.7, mid + 11.5), (0, 8.0, mid))
    shot("slant", (11.0, 5.0, z - 3.0), (0, 9.5, z + 14.0))
    shot("near_main", (9.0, 10.5, bay_mid(z, 4)), (0, 10.5, bay_mid(z, 4)))        # lit, dark, lit
    shot("near_base", (7.0, 3.5, bay_mid(z, 6)), (0, 3.5, bay_mid(z, 6)))          # curtain, dark, lit

    z = spans["walls"][0]
    for name, kind in (("walls_lit", "F"), ("walls_dark", "B")):                   # the middle one of three
        shot(name, (11.5, N / 2.0, wall_mid(z, kind)), (0, N / 2.0, wall_mid(z, kind)))
    for kind in ORDER:
        shot(f"close_{NAME[kind]}", (5.2, N / 2.0, wall_mid(z, kind)), (0, N / 2.0, wall_mid(z, kind)))

    z = spans["panes"][0]
    width = PANE_PITCH * len(ORDER) + 1
    shot("panes", (8.5, 3.0, z + width / 2.0), (0, 2.8, z + width / 2.0))
    shot("pane_edges", (4.0, 3.6, z + width - 0.5), (0.8, 1.4, z + width + 4.5))

    z = spans["roof"][0]
    shot("roof", (ROOF_X + N + 5.5, ROOF_Y + 5.0, z + N / 2.0), (ROOF_X + N / 2.0 - 0.5, ROOF_Y, z + N / 2.0))

    z = spans["compass"][0]
    cx, cz, y, d = COMPASS_X + 2.5, z + 2.5, 1 + len(ROWS) / 2.0, 8.5
    for name, dx, dz in (("face_east", d, 0), ("face_west", -d, 0), ("face_south", 0, d), ("face_north", 0, -d)):
        shot(name, (cx + dx, y, cz + dz), (cx, y, cz))
    return out
