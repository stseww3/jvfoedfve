"""Test scene of the work package materials/ashlar (plan/packages/materials/ashlar.md).

What it is for: to see the grey-white stone of the sandstone family -- the rusticated base, the
dressed coursed walls, the sunk panel and the emblem block -- in every shape, and to check the
things the card and c190's pre-review call for:

  - stones     the four stones side by side (materials/_board.stone): each family with its stairs,
               slabs and (rough) wall, and the panel/emblem stacked over a fine wall;
  - walls      an eight-by-eight wall of each of the four, the families with their shaped blocks at
               the foot, to read close for the joints and tooling and from twenty blocks for stripes;
  - coursed    a facade band in the one wall plane: a slate plinth, a rusticated base storey, a
               string course standing proud, then the dressed storey with sunk panels and emblem
               blocks -- the rough below and the fine above must read as one stone across the course
               (c190 #2);
  - flight     a flight of fine stairs and a coping run, to be read from straight above: a tread and
               a coping carry no bed joint (c190 #1);
  - lit        seven bays of the front, cut as the skeleton cuts it and built of the four stones,
               with the merged windows in them and one bracket lamp on a pilaster: the stone as the
               building will show it, cold under the night sky and warm where a lamp and a lit
               window reach it (c219's pre-review point 4). No stage lamp stands near it.

This scene renders version a (the drawn ashlar). obs_mat_ashlar_b and obs_mat_ashlar_c render the
other two versions over the same board and the same shots (the three-way compare the card asks for).

    python -m scenes.obs_mat_ashlar      writes shots.json from the layout below
"""
from artkit.blocks import st
from artkit.canvas import Canvas

from scenes.obs import materials  # noqa: F401  (kept so the scene reads like its siblings)
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.materials import _board
from scenes.obs.materials import _kit as K
from scenes.obs.props import lamps

BIOME = "obs_blue"
CATEGORY = "materials"
Z = 0
TIME = 14000        # the default light version (sky line)
DUSK = 12900        # light version C, the lightest of the three: the lit bays once more, the stone easier to read
VERSION = "a"       # the drawn ashlar; obs_mat_ashlar_b / _c compare b and c


WALLS = (("rough", B.ASHLAR_ROUGH), ("fine", B.ASHLAR_FINE), ("panel", B.ASHLAR_PANEL), ("emblem", B.ASHLAR_EMBLEM))
WALL, PITCH = 8, 10     # a wall is WALL by WALL; x from one wall to the next


def walls(c, x, z):
    """An eight-by-eight wall of each of the four stones, a gap between them, the families with
    their shaped blocks at the foot: close for the joints and the tooling, from twenty blocks for
    stripes. The panel and the emblem are accents on a facade, but a frieze sets them in a row, and
    a whole wall of each is where a repeat that stripes would show."""
    for i, (_, what) in enumerate(WALLS):
        _board.wall(c, what, x + PITCH * i, 0, z, n=WALL)       # its stairs/slabs/low wall at z + 1
    last = x + PITCH * (len(WALLS) - 1) + WALL - 1
    _board.stage(c, x, last, z, height=WALL + 1)
    return last + 2


def coursed(c, x, z):
    """A facade band as ART-PLAN 5.1 stacks it, base and main storey in the one wall plane: a slate
    plinth, a rusticated base storey, a string course standing one proud of the wall, then the
    dressed storey with sunk panels under the windows and emblem blocks at the top.

    The course is an upside-down fine stair -- a shelf over a half-deep fascia -- set exactly on the
    change from rough to fine, so it takes the jump from the two-pixel joint to the one-pixel joint
    and the two finishes read as one stone, split on purpose (c190 #2). The stage's lamps light the
    foot of the band, so the base storey and the first courses of the dressed one stand in the one
    light; higher up the stone is seen as the night sky lights it."""
    w, top = 7, 12
    c.box(x, 0, z, x + w - 1, 0, z, B.SLATE_BRICK.block)                 # plinth
    c.box(x, 1, z, x + w - 1, 4, z, B.ASHLAR_ROUGH.block)                # rusticated base storey
    c.box(x, 5, z, x + w - 1, top, z, B.ASHLAR_FINE.block)               # dressed storey, the same plane
    for dx in range(w):                                                   # the string course, one proud
        c.set(x + dx, 5, z + 1, st(B.ASHLAR_FINE.stairs, facing="north", half="top"))
    for dx in (1, 2, 4, 5):                                              # sunk panels under the windows
        c.set(x + dx, 8, z, B.ASHLAR_PANEL.block)
    for dx in (0, 3, 6):                                                 # emblem blocks at the top
        c.set(x + dx, top, z, B.ASHLAR_EMBLEM)
    _board.stage(c, x, x + w - 1, z, height=top + 2)
    return x + w + 2


def flight(c, x, z):
    """A flight of fine stairs climbing north and a coping run beside it, to be read from straight
    above: the treads (fine) and the copings (fine, and a rough one to compare) carry no bed joint."""
    for i in range(5):                                  # the flight, each step up and one north
        zz = z - i
        for dx in (0, 1):
            c.set(x + dx, i, zz, st(B.ASHLAR_FINE.stairs, facing="south"))
        if i:
            c.box(x, 0, zz, x + 1, i - 1, zz, B.ASHLAR_FINE.block)
    c.box(x + 3, 0, z - 4, x + 4, 1, z, B.ASHLAR_FINE.block)             # a low wall to cap
    for dz in range(5):                                                  # the copings
        c.set(x + 3, 2, z - dz, st(B.ASHLAR_FINE.slab, type="bottom"))
        c.set(x + 4, 2, z - dz, st(B.ASHLAR_ROUGH.slab, type="bottom"))
    _board.stage(c, x, x + 5, z, height=7)
    return x + 7


# ---- the lit bays: the stone with windows in it and a lamp on it -----------------------------------------
BAYS = 7                        # bays of the front; a bay is a pilaster and a window of three (S.BAY)
KIND = {"L": B.WINDOW_LIT, "F": B.WINDOW_FROSTED, "C": B.WINDOW_CURTAIN, "D": B.WINDOW_DARK}
MAIN = "FLDLCDF"                # the tall windows, west to east
BASE = "D..CLDF"                # the small windows of the base storey; "." is a bay left solid, so that
#                                 the lamp's light falls on two bays of rough stone and not on glass
GLOW = {"L": 10, "F": 10, "C": 9}   # the invisible light behind a lit window, as materials/windows sets
#                                     it (plan/parts/sky.md 6); a dark window has none
BASE_WINDOW = (3, 4)            # y of the small windows: three wide, two high
BRACKET = 2                     # the pilaster that carries the lamp, counted from the west
BRACKET_Y = 4.0                 # where props/lamps hangs its pair beside the entrance
LAMP_MODEL = lamps.PREFIX + "bracket_a"


def _window(c, kind, x, y0, y1, z, glow):
    """A window three wide in the solid wall: the opening, the glass one block in, the free cell
    behind it and, behind a lit window, the lights at the heights `glow`."""
    glass, room = z + S.DEPTH_GLASS, z + S.DEPTH_GLASS - 1
    c.carve(x, y0, z, x + 2, y1, z)
    c.box(x, y0, glass, x + 2, y1, glass, KIND[kind].block)
    c.carve(x, y0, room, x + 2, y1, room)
    if kind in GLOW:
        for y in glow:
            c.set(x + 1, y, room, st(B.LIGHT, level=GLOW[kind]))


def lit(c, x, z):
    """Seven bays of the front as the skeleton cuts it (and as materials/windows builds its ten),
    looking south like the rest of this board: a slate plinth, the rusticated base, the string
    course, a sunk panel under each tall window, a keystone and the pilasters' emblem blocks in the
    frieze, a cornice two blocks out, the parapet; pilasters one block out, glass one block in.

    One bracket lamp (version a of props/lamps) hangs on a pilaster of the base storey. Nothing else
    lights the front but the night sky and the windows themselves, so this is where the stone is
    seen cold and warm at once. Returns the x after it; sets the number of display entities."""
    fine, rough = B.ASHLAR_FINE, B.ASHLAR_ROUGH
    end = x + S.BAY * BAYS                              # the last pilaster
    out, eaves, back = z + S.DEPTH_PILASTER, z + S.DEPTH_CORNICE, z + S.DEPTH_GLASS - 2
    for (y0, y1), block in ((S.PLINTH, B.SLATE_BRICK.block), (S.BASE, rough.block),
                            ((S.STRING, S.CORNICE), fine.block)):
        c.box(x, y0, back, end, y1, z, block)           # solid: every window gets a room of its own
    c.box(x, S.PARAPET[0], z, end, S.PARAPET[1], z, fine.block)
    c.box(x, S.PLINTH[0], out, end, S.PLINTH[1], out, B.SLATE_BRICK.block)
    c.box(x, S.STRING, out, end, S.STRING, out, st(fine.stairs, facing="north", half="top"))
    c.box(x, S.CORNICE, out, end, S.CORNICE, out, fine.block)
    c.box(x, S.CORNICE, eaves, end, S.CORNICE, eaves, st(fine.slab, type="top"))
    for k in range(BAYS + 1):
        px = x + S.BAY * k
        c.box(px, S.BASE[0], out, px, S.BASE[1], out, rough.block)
        c.box(px, S.STRING, out, px, S.WINDOW[1], out, fine.block)
        c.set(px, S.FRIEZE, out, B.ASHLAR_EMBLEM)
    for k in range(BAYS):
        w = x + S.BAY * k + 1                           # the bay's windows are at w .. w + 2
        c.box(w, S.PANEL, z, w + 2, S.PANEL, z, B.ASHLAR_PANEL.block)
        c.set(w + 1, S.FRIEZE, z, B.ASHLAR_EMBLEM)      # the keystone
        _window(c, MAIN[k], w, S.WINDOW[0], S.WINDOW[1], z, glow=(S.WINDOW[0] + 1, S.WINDOW[1] - 1))
        c.set(w, S.WINDOW[1], z, st(fine.stairs, half="top", facing="west"))        # the hint of an arch
        c.set(w + 2, S.WINDOW[1], z, st(fine.stairs, half="top", facing="east"))
        if BASE[k] != ".":
            _window(c, BASE[k], w, BASE_WINDOW[0], BASE_WINDOW[1], z, glow=(BASE_WINDOW[0],))
    c.box(x - 2, -1, back, end + 14, -1, z + 16, _board.FLOOR)      # paving, on past the east end
    c.entity_counts = {"props": lamps.place(c, "bracket", lamp_at(x, z), facing="south", version="a")}
    return end + 1


def lamp_at(x, z):
    """Where the bracket lamp is fixed: the middle of the south face of its pilaster."""
    return (x + S.BAY * BRACKET + 0.5, BRACKET_Y, z + S.DEPTH_PILASTER + 1.0)


# name, how to build it, the free x before it. The lit bays stand sixteen blocks clear of the last
# station, whose stage lamps reach fourteen: nothing but their own lamp and windows lights them.
STATIONS = [("stones", _board.stone, 0), ("walls", walls, 2), ("coursed", coursed, 2), ("flight", flight, 2),
            ("lit", lit, 16)]


def layout(c=None):
    """Where each station stands: {name: (first x, x after it)}. Builds into `c` when given one."""
    c = c or Canvas()
    spans, x = {}, 0
    for name, station, gap in STATIONS:
        x += gap
        end = station(c, x, Z)
        spans[name] = (x, end)
        x = end
    return spans


def build():
    c = Canvas()
    layout(c)
    return c


def build_models():
    """The one model the board shows: the bracket lamp of props/lamps on the lit bays."""
    return {LAMP_MODEL: lamps.models()[LAMP_MODEL]}


def write_pack(pack_dir):
    return K.pack_with(pack_dir, ashlar=VERSION)


def shots():
    """Camera positions from the layout: the four stones in halves (the split, the joints), each
    eight-by-eight wall close, the four from twenty blocks and from thirty-six, the distance of the
    forecourt view (stripes, the lightness of the whole), and along their faces at a grazing angle
    (where joints run into streaks); the coursed band face-on (rough and fine as one stone) and its
    string course from the ground; the fine treads and the copings from above; the lit bays from the
    forecourt as someone walking up to them sees them, face-on, and close to the lamp."""
    spans = layout()
    out = []

    def front(name, x0, x1, y=1.6, time=TIME):
        d = max(5.0, (x1 - x0 + 2) / 2.6)
        out.append({"name": name, "pos": [(x0 + x1) / 2.0, y + 1.2, round(Z + 1 + d, 1)],
                    "look_at": [(x0 + x1) / 2.0, y, Z], "time": time})

    x0, x1 = spans["stones"]
    x1 -= 2
    mid = (x0 + x1) // 2
    front("stones_a", x0, mid)                                  # the split and the shapes, read close
    front("stones_b", mid, x1)

    xw = spans["walls"][0]
    for i, (name, _) in enumerate(WALLS):                       # each wall face-on, close
        xc = xw + PITCH * i + WALL / 2.0
        out.append({"name": f"wall_{name}", "pos": [xc, 4.6, Z + 8.5], "look_at": [xc, 4.0, Z], "time": TIME})
    xc = xw + (PITCH * (len(WALLS) - 1) + WALL) / 2.0           # the four of them from twenty blocks
    out.append({"name": "walls_far", "pos": [xc, 5.0, Z + 20.0], "look_at": [xc, 4.0, Z], "time": TIME})
    # from thirty-six blocks off their faces, where the forecourt view stands to the front (c219 #5)
    out.append({"name": "walls_v2", "pos": [xc, 5.0, Z + 37.0], "look_at": [xc, 4.0, Z], "time": TIME})
    # along the face of the fine wall from the gap before it: its far end is seen at thirteen
    # degrees to the face, the panel and the emblem walls beyond it at six and less (c219 #5)
    out.append({"name": "walls_graze", "pos": [xw + PITCH - 0.5, 3.0, Z + 2.6],
                "look_at": [xw + PITCH + WALL - 1.5, 4.0, Z + 1.0], "time": TIME})

    xc0, xc1 = spans["coursed"]
    xc1 -= 2
    xm = (xc0 + xc1) / 2.0
    out.append({"name": "coursed", "pos": [xm, 6.5, Z + 12.0], "look_at": [xm, 6.0, Z], "time": TIME})
    # the string course as someone on the ground sees it: from below and a little to one side, so
    # its shelf, its fascia and its plain soffit all show, with the rough under it and the fine over
    out.append({"name": "coursed_course", "pos": [xm - 2.5, 2.6, Z + 6.5], "look_at": [xm + 0.5, 5.2, Z + 0.5],
                "time": TIME})

    xf = spans["flight"][0]
    out.append({"name": "flight_treads", "pos": [xf + 1.0, 7.5, Z + 3.0], "look_at": [xf + 1.0, 1.0, Z - 3.0],
                "time": TIME})
    out.append({"name": "flight_copings", "pos": [xf + 3.5, 6.5, Z + 2.5], "look_at": [xf + 3.5, 1.5, Z - 2.0],
                "time": TIME})

    xl = spans["lit"][0]
    lx, ly, lz = lamp_at(xl, Z)
    # walking up to the front: eye height, the lamp left of the middle, the front running off to
    # the east and ending against the sky (nothing of the board stands that way)
    for name, time in (("coursed_lit", TIME), ("coursed_lit_dusk", DUSK)):
        out.append({"name": name, "pos": [lx - 0.5, 1.7, Z + 12.0], "look_at": [lx + 4.5, 6.5, Z + 1.0],
                    "time": time})
    xm = xl + S.BAY * BAYS / 2.0 + 0.5                          # the whole of it, face-on
    out.append({"name": "lit_front", "pos": [xm, 8.5, Z + 14.5], "look_at": [xm, 8.5, Z], "time": TIME})
    # the lamp and the stone it lights: the rough pilaster and base, the course, a panel, a sill
    out.append({"name": "lit_lamp", "pos": [lx - 3.0, 3.2, lz + 4.5], "look_at": [lx, ly + 0.6, lz - 0.5],
                "time": TIME})
    return out
