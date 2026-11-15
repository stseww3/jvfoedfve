"""Test scene of the work package props/ironwork: the whole family on one stage.

A long dressed-stone wall looks south and the cameras stand south of it. From west to east: the great
arched window frame in version A over a glazed opening, the same opening in version B (so the two
heads can be compared blind), a base-storey grille, then the entrance -- the open door, the fanlight
and the glazed canopy. An inspection ladder climbs the wall at the east end. On the paving in front
stand a run of balustrade scroll panels, a roof vent cowl and a floor grating.

The shots are written from the numbers below:  python -m scenes.obs_props_ironwork
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.props import ironwork

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32

STONE = B.ASHLAR_FINE.block
PANEL = B.ASHLAR_PANEL.block
EMBLEM = B.ASHLAR_EMBLEM
GLASS = B.WINDOW_LIT.block
PAVING = B.TUFF_SMOOTH.block
WALL_Z = -1
FACE = WALL_Z + 1               # the air cell in front of the wall; a wall prop's anchor sits on the face
WALL_H = 12
ARCH = {"a": 3, "b": 11}        # the two arch windows, one to a version
STRAIGHT = 4                    # the straight light below the springing, in blocks
GRILLE_X = 19
DOOR_X = 28
LADDER_X = 38
WALL_W0, WALL_W1 = -3, 44
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)


def _window(c, cx, y0, w, h, lit=GLASS):
    """A glazed opening w wide (odd), h tall, centred on cx with its foot at y0, in the wall face."""
    c.box(cx - (w - 1) // 2, y0, WALL_Z, cx + (w - 1) // 2, y0 + h - 1, WALL_Z, lit)


def _arches(c):
    """Each version's frame over a matching 3-wide arched opening: the straight light up to the
    springing, a glass lunette under the crown and stone spandrels in the corners, so the iron head
    caps the glass instead of floating over a flat-topped rectangle. The frame sits on the wall FACE,
    pressing on the glazed pane and its painted 8 px muntins (card: check for a double grid). Both
    openings are framed alike so the two heads can be compared blind; version B leaves the crown for
    A3's keystone."""
    n = 0
    for version, cx in ARCH.items():
        c.box(cx - 1, 3, WALL_Z, cx + 1, 3 + STRAIGHT - 1, WALL_Z, GLASS)   # straight light, 3 wide
        c.box(cx, 3 + STRAIGHT, WALL_Z, cx, 3 + STRAIGHT, WALL_Z, GLASS)     # the lunette under the crown
        c.box(cx - 1, 2, WALL_Z, cx + 1, 2, WALL_Z, PANEL)                   # the sunk sill course
        # the frame centres on the three-cell opening (cells cx-1..cx+1), whose middle point is cx+0.5
        n += ironwork.place(c, "window_arch", (cx + 0.5, 3.0, FACE), facing="south", version=version)
        if version == "b":
            c.box(cx, 3 + STRAIGHT + 1, WALL_Z, cx, 3 + STRAIGHT + 1, WALL_Z, EMBLEM)  # A3's keystone
    return n


def _entrance(c):
    """The door hung open, the fanlight above and the canopy over it. The three-wide opening (door
    y0-5, fanlight y5-6) is left out of the wall in build(), so a player walks through. The assembly
    sits on the wall FACE: the open leaves lie proud of the solid wall beside the opening (anchored
    on the wall itself they would be buried in it, as build() already anchors on the face)."""
    return ironwork.entrance(c, (DOOR_X + 0.5, 0.0, FACE), facing="south")


def _floor(c):
    """The pieces that stand on the paving in front of the wall (each on the middle of its cell)."""
    n = 0
    for cx in (4, 7, 10):                                              # a balustrade run (2-wide, on integer points)
        n += ironwork.place(c, "railing_panel", (cx, 0.0, 7.5), facing="south")
    n += ironwork.place(c, "vent_cowl", (LADDER_X - 3.5, 0.0, 6.5))
    n += ironwork.place(c, "grate_hatch", (DOOR_X + 4.5, 0.0, 8.5))
    return n


def build():
    c = Canvas()
    c.box(WALL_W0 - 1, -1, -1, WALL_W1 + 4, -1, 14, PAVING)
    # the wall, with the three-wide entrance (x DOOR_X-1..+1, y 0..6) left out so a player walks through
    c.box(WALL_W0, 0, WALL_Z, DOOR_X - 2, WALL_H - 1, WALL_Z, STONE)
    c.box(DOOR_X + 2, 0, WALL_Z, WALL_W1, WALL_H - 1, WALL_Z, STONE)
    c.box(DOOR_X - 1, 7, WALL_Z, DOOR_X + 1, WALL_H - 1, WALL_Z, STONE)
    c.box(DOOR_X - 2, 7, WALL_Z, DOOR_X + 2, 7, WALL_Z, EMBLEM)             # the lintel over the opening
    n = _arches(c)
    _window(c, GRILLE_X, 3, 3, 2)
    n += ironwork.place(c, "window_grille", (GRILLE_X + 0.5, 3.0, FACE), facing="south")
    n += _entrance(c)
    n += ironwork.place(c, "ladder", (LADDER_X + 0.5, 1.0, FACE), facing="south")
    n += _floor(c)
    sky.build(c, (0, 0, 0))             # A2's light sources go in last, when every piece is in place
    c.entity_counts = {"props": n}
    return c


def write_pack(pack_dir):
    """The repainted stone and glass the ironwork is judged against."""
    return materials.pack(pack_dir)


def shots():
    """The cameras: the whole stage, the two arch heads framed alike for a blind comparison, and each
    piece from about three blocks."""
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos],
                    "look_at": [round(v, 2) for v in look_at], "time": TIME})

    ac = {v: cx + 0.5 for v, cx in ARCH.items()}    # the centre point of each arch opening
    gx, dx, lx = GRILLE_X + 0.5, DOOR_X + 0.5, LADDER_X + 0.5
    shot("far", (dx - 8.0, 6.0, 34.0), (dx - 8.0, 5.0, -1.0))
    for v, cx in ac.items():
        shot(f"arch_{v}", (cx, 6.0, 9.0), (cx, 6.0, -1.0))
        shot(f"arch_{v}_head", (cx, 8.5, 6.0), (cx, 8.0, -1.0))
    shot("grille", (gx, 4.0, 6.0), (gx, 4.0, -1.0))
    shot("entrance", (dx, 4.5, 12.0), (dx, 4.0, -1.0))
    shot("door_near", (dx + 4.0, 3.4, 5.5), (dx + 0.75, 3.2, -0.5))   # 3/4 view of the east leaf's porthole
    shot("fanlight_near", (dx, 6.0, 4.5), (dx, 5.6, -1.0))
    shot("canopy_near", (dx - 3.5, 5.0, 5.0), (dx, 6.6, 1.0))
    shot("ladder_near", (lx + 2.0, 3.0, 4.5), (lx, 3.0, -1.0))
    shot("railing", (7.0, 1.6, 11.5), (7.0, 0.8, 7.5))
    shot("vent", (lx - 4.0, 1.6, 10.0), (lx - 4.0, 1.0, 6.5))
    shot("grate", (dx + 4.0, 2.4, 11.0), (dx + 4.0, 0.2, 8.5))
    return out
