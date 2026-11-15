"""Test scene of the linings of materials/windows (plan/packages/materials/windows.md): the lit
windows as the room behind them sees them.

One room of the main storey behind five bays of the entrance front, cut as the skeleton cuts it and
as this package's other scene builds its facade (obs_mat_windows): the wall face at x 0 looks east,
the glass stands one block in, the room lies behind it. The five great windows, from the north:

    lit    dark    frosted    curtain    blind

so each of the three linings stands beside a window that needs none, and the lining of the lit
window beside the dark window it is to be read as.

The room is a wing room's in height (feet at y 7, clear to 13) and eight deep, with two lamps under
its ceiling. In the opening of each lit window, outside the glass, stand the sources of the light
line (c220, g2 #33341: 10 before a lit window, 8 frosted, 6 curtain): the stone round the window is
warm, and the first cell of the room takes what comes through the glass.

Shots: in_* from inside the room, out_* the front from outside. The twin obs_mat_windows_in_off is
this scene built without the linings. Its out_* pictures have to be the same as these, pixel for
pixel (sky/_tones.py --diff); its in_* pictures show what the linings are for. obs_mat_windows_in_b
is the same room with version b of the windows.

    python -m scenes.obs_mat_windows_in              writes shots.json from the layout below
    python -m scenes.obs_mat_windows_in.placement    holds windows.line() to covering the glass and to
                                                     one light for a window, without a picture
"""
from artkit.blocks import st
from artkit.canvas import Canvas

from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.materials import _kit as K
from scenes.obs.materials import windows as W

BIOME = "obs_blue"
TIME = 14000                    # light version A; 18000 is B and 12900 is C
VERSIONS = {}                   # material package -> version; every package's default when empty

FINE, ROUGH = B.ASHLAR_FINE, B.ASHLAR_ROUGH
KIND = {"L": B.WINDOW_LIT, "F": B.WINDOW_FROSTED, "C": B.WINDOW_CURTAIN, "D": B.WINDOW_DARK, "B": B.WINDOW_BLIND}
MAIN = "LDFCB"                  # the great windows, north to south
# The light line's sources in the opening of a lit window, outside the glass. They stand in for
# sky/lights, which puts them there itself once it is in the tree.
SOURCE = {"L": 10, "F": 8, "C": 6}
ROOM_LAMP = 12                  # the two lamps of the room

WALL = S.DEPTH_WALL             # 0: the wall face
GLASS = S.DEPTH_GLASS           # -1: the glass, in the inner leaf of the wall
INWARD = (-1, 0)                # the room lies west of the glass
Z1 = S.BAY * len(MAIN)          # 20: the last pilaster; the room is clear from z 1 to z 19
DEEP = 8
X0 = GLASS - DEEP               # -9: the room is clear from here to x -2
FEET, CEIL = S.STAND, S.STAR_HALL_CEIL          # 7 and 14, as in the wing rooms


def window_z(k):
    """The first of the three columns of window k, 0 the north-most."""
    return S.BAY * k + 1


def window_mid(k):
    return S.mid(window_z(k), window_z(k) + 2)


def room(c):
    """The body with the room in it, the front as the skeleton cuts it, the five windows with their
    sources, and the linings."""
    out, eaves = WALL + S.DEPTH_PILASTER, WALL + S.DEPTH_CORNICE
    y0, y1 = S.WINDOW
    c.box(X0 - 1, S.PLINTH[0], 0, WALL, S.CORNICE, Z1, FINE.block)
    for (a, b), block in ((S.PLINTH, B.SLATE_BRICK.block), (S.BASE, ROUGH.block)):
        c.box(GLASS, a, 0, WALL, b, Z1, block)
    c.box(WALL, S.PARAPET[0], 0, WALL, S.PARAPET[1], Z1, FINE.block)
    c.box(out, S.PLINTH[0], 0, out, S.PLINTH[1], Z1, B.SLATE_BRICK.block)
    c.box(out, S.STRING, 0, out, S.STRING, Z1, st(FINE.slab, type="top"))
    c.box(out, S.CORNICE, 0, out, S.CORNICE, Z1, FINE.block)
    c.box(eaves, S.CORNICE, 0, eaves, S.CORNICE, Z1, st(FINE.slab, type="top"))
    for k in range(len(MAIN) + 1):
        pz = S.BAY * k
        c.box(out, S.BASE[0], pz, out, S.BASE[1], pz, ROUGH.block)
        c.box(out, S.STRING, pz, out, y1, pz, FINE.block)
        c.set(out, S.FRIEZE, pz, B.ASHLAR_EMBLEM)

    c.carve(X0, FEET, 1, GLASS - 1, CEIL - 1, Z1 - 1)
    c.box(X0, FEET - 1, 1, GLASS - 1, FEET - 1, Z1 - 1, B.FLOOR_WOOD.block)
    c.box(X0, CEIL, 1, GLASS - 1, CEIL, Z1 - 1, B.DARK_WOOD.block)
    for k in (1, 3):                                    # under the ceiling, before the dark and the curtain
        c.set(X0 + 3, CEIL - 2, window_z(k) + 1, st(B.LIGHT, level=ROOM_LAMP))

    n = 0
    for k, kind in enumerate(MAIN):
        w = window_z(k)
        c.box(WALL, S.PANEL, w, WALL, S.PANEL, w + 2, B.ASHLAR_PANEL.block)
        c.set(WALL, S.FRIEZE, w + 1, B.ASHLAR_EMBLEM)   # the keystone
        c.carve(WALL, y0, w, WALL, y1, w + 2)
        c.box(GLASS, y0, w, GLASS, y1, w + 2, KIND[kind].block)
        c.set(WALL, y1, w, st(FINE.stairs, half="top", facing="north"))
        c.set(WALL, y1, w + 2, st(FINE.stairs, half="top", facing="south"))
        if kind in SOURCE:
            for y in (y0 + 1, y1 - 1):
                c.set(WALL, y, w + 1, st(B.LIGHT, level=SOURCE[kind]))
        n += W.line(c, [(GLASS, y, z) for z in range(w, w + 3) for y in range(y0, y1 + 1)], INWARD, KIND[kind])
    c.box(X0 - 4, -1, -4, 14, -1, Z1 + 4, B.SLATE_SMOOTH.block)
    return n


def build():
    c = Canvas()
    room(c)
    return c


def build_models():
    return W.models(VERSIONS.get("windows"))


def write_pack(pack_dir):
    return K.pack_with(pack_dir, **VERSIONS)


def shots():
    """From inside: the whole window wall in the three light versions, each lining with the windows
    beside it, the wall from near and along its face. From outside: the front square on, along its
    face and from near, the three pictures the twin scene has to repeat."""
    out = []

    def shot(name, pos, look_at, time=TIME):
        out.append({"name": name, "pos": [round(float(v), 2) for v in pos],
                    "look_at": [round(float(v), 2) for v in look_at], "time": time})

    mid, eye = S.mid(0, Z1), FEET + 1.62
    lit_dark = S.mid(window_z(0), window_z(1) + 2)      # the pier between the lit and the dark window
    curtain_blind = S.mid(window_z(3), window_z(4) + 2)
    for name, time in (("in_wall", TIME), ("in_wall_b", 18000), ("in_wall_c", 12900)):
        shot(name, (X0 + 0.5, eye, mid), (GLASS, 10.0, mid), time)
    shot("in_lit", (-6.0, 9.5, lit_dark), (GLASS, 10.5, lit_dark))
    shot("in_frosted", (-5.5, 9.5, window_mid(2)), (GLASS, 10.5, window_mid(2)))
    shot("in_curtain", (-5.5, 9.5, curtain_blind), (GLASS, 10.5, curtain_blind))
    shot("in_near", (-3.5, 10.5, lit_dark - 1.0), (GLASS, 10.5, lit_dark - 1.0))
    shot("in_slant", (-2.6, 9.0, 1.4), (GLASS, 10.5, 11.0))
    shot("out_front", (17.0, 8.5, mid), (WALL, 8.5, mid))
    shot("out_slant", (9.0, 9.0, -4.0), (WALL, 10.5, 9.0))
    shot("out_near", (7.0, 10.5, lit_dark), (WALL, 10.5, lit_dark))
    return out
