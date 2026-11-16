"""A door case and two panelled leaves standing open, for a doorway of main/shell in a panelled room.

The doorway is the shell's (shell.doors()): two cells wide, three rows high, in a wall one block
thick. On the room's side the kit gives it what a joiner would: boards lining the opening, a casing
on the wall either side standing on a plinth block, a frieze and a cap over the head, and the two
leaves, hinged on the casings and swung into the room. The gallery's side of the wall is not
touched. Nothing here is a light source, and brass is on the knobs and the hinges only.

Model space, 1/16 block: x across the opening from the middle of its foot, towards the right hand
of somebody who stands in the room and looks at the door; y up from the floor; z out of the wall
into the room, 0 on the wall's own face. `face` is how far the room's lining stands off that face
(the thickness of its wainscot): the case lies on the lining, the leaves hang in front of it.

Five display entities: the two jambs, the head, the two leaves. All five are held from one point,
the middle of the opening on the lining's face, so one cell lights the whole door and no step of
light shows where a jamb meets the head or a leaf its casing. The leaves' swing is drawn into
their models; whoever moves them later turns them about the pin (pin()).

    models(prefix, door, face, swing)  -> {name: Model}       names: prefix + "door_" + a piece of PIECES
    place(canvas, prefix, door, face, swing, origin) -> 5     the display entities placed
    swept(door, face, swing)           -> [(x0, z0, x1, z1)]  what the leaves stand over on the floor
"""
from artkit import models as M

from ..common import palette as P
from ..props import _kit as K

PIECES = ("jamb_l", "jamb_r", "head", "leaf_l", "leaf_r")
ROWS = 3                    # the height of the opening the kit is drawn for, in blocks
WALL = 16.0                 # the wall the opening is in: one block thick

FRAME = P.mat("dark_wood", base=2)      # stiles, rails, casings: the wainscot's wood
FIELD = P.mat("dark_wood", base=1)      # what lies deeper: a leaf's panels, the boards lining the opening
EDGE = P.mat("dark_wood", base=3)       # what stands proud and takes the light: beads, the cap
PLATE = K.BRASS_D                       # hinges and the plates behind the knobs
KNOB = K.flat("brass", 3)

LINING = 1.0                # the boards that line the opening
CASING = 5.0                # a jamb's casing on the wall: a board this wide,
PROUD = 1.0                 # this far off the lining,
BEAD = 1.5                  # a bead this wide along the opening and a fillet along its outer edge,
RAISED = 0.5                # which stand this much prouder
PLINTH = (6.0, 2.0, 0.5)    # the block a casing stands on: its height, how far it stands off the lining, how much wider it is
FRIEZE = 3.25               # the head: a board this high over the opening,
CAP = (1.25, 2.5, 1.0)      # and a cap on it: its height, how far it stands off the lining, how far it runs past the casings

LEAF = 2.0                  # a leaf's thickness
GAP = 0.5                   # the air under a leaf and over it
STILE = 3.0
RAILS = ((0.0, 5.5), (15.5, 19.5), (35.5, 38.5), (44.0, 47.0))    # from a leaf's foot: bottom, lock, frieze and top rail
SUNK = 0.5                  # a panel lies this deep in its frame, on both faces
KNOB_Y = 17.5               # the knob, on the lock rail, from the leaf's foot
HINGES = (6.0, 23.5, 41.0)  # the middles of the three hinges, from the leaf's foot

FACING = {(0, 1): "south", (0, -1): "north", (1, 0): "east", (-1, 0): "west"}


def _size(door):
    """(half the opening's width, its height) in model units."""
    cells, (y0, y1) = door["cells"], door["y"]
    rows = y1 - y0 + 1
    if rows != ROWS:
        raise ValueError(f"the door kit is drawn for an opening {ROWS} rows high, not {rows}")
    return len(cells) * 8.0, rows * 16.0


def _held(top, face):
    return (0.0, top / 2.0, face)


def pin(side, half, face):
    """Where a leaf's hinge pin stands, (x, z) in model space: at the opening's edge, on the front
    of the casing's bead, so that the leaf swings clear of the casing. side: -1 left, 1 right."""
    return (side * half, face + PROUD + RAISED)


def _jamb(name, side, half, top, face):
    """One side of the case: the board lining the opening's side from the gallery's face of the
    wall to the room's lining, and on the lining the casing on its plinth block."""
    m = M.Model(name, anchor=_held(top, face))
    edge = side * half
    hidden = "e" if side > 0 else "w"       # the face that lies against the wall's stone
    m.box((edge - side * LINING, 0.0, -WALL), (edge, top, face), FIELD, grain="y", skip=hidden + "ud")
    high, off, wider = PLINTH
    m.box((edge, 0.0, face), (edge + side * (CASING + wider), high, face + off), FRAME, grain="x", skip="nd")
    m.box((edge, high, face), (edge + side * CASING, top, face + PROUD), FRAME, grain="y", skip="nud")
    for a, b in ((0.0, BEAD), (CASING - 1.0, CASING)):
        m.box((edge + side * a, high, face + PROUD), (edge + side * b, top, face + PROUD + RAISED), EDGE,
              grain="y", skip="nud")
    return m


def _head(name, half, top, face):
    """The head of the case: the board lining the opening's soffit, the frieze over the opening
    with a bead along its foot, the cap."""
    m = M.Model(name, anchor=_held(top, face))
    m.box((-half + LINING, top - LINING, -WALL), (half - LINING, top, face), FIELD, grain="x", skip="ewu")
    wide = half + CASING
    m.box((-wide, top, face), (wide, top + FRIEZE, face + PROUD), FRAME, grain="x", skip="nu")
    m.box((-wide, top, face + PROUD), (wide, top + 0.75, face + PROUD + RAISED), EDGE, grain="x", skip="n")
    high, off, past = CAP
    m.box((-wide - past, top + FRIEZE, face), (wide + past, top + FRIEZE + high, face + off), EDGE, grain="x", skip="n")
    return m


def _leaf(name, side, half, top, face, swing):
    """One leaf, swung `swing` degrees into the room about its pin: two stiles, four rails, three
    panels sunk on both faces, a knob with its plate on either face of the meeting stile, three
    hinges. Drawn shut (from its jamb to the middle of the opening, its room face on the pin's
    line) and turned as one piece."""
    m = M.Model(name, anchor=_held(top, face))
    px, pz = pin(side, half, face)
    foot, tall = GAP, top - 2.0 * GAP
    near, far = sorted((px, 0.0))                   # the leaf shut: from its jamb to the middle of the opening
    back, front = pz - LEAF, pz
    with m.turned(("y", side * swing), about=(px, 0.0, pz)):
        for x in (near, far - STILE):
            m.box((x, foot, back), (x + STILE, foot + tall, front), FRAME, grain="y")
        for a, b in RAILS:
            m.box((near + STILE, foot + a, back), (far - STILE, foot + b, front), FRAME, grain="x", skip="ew")
        for (_, a), (b, _) in zip(RAILS, RAILS[1:]):
            m.box((near + STILE, foot + a, back + SUNK), (far - STILE, foot + b, front - SUNK), FIELD,
                  grain="y", skip="ewud")
        knob_x = side * STILE / 2.0                 # the middle of the meeting stile
        for z, out in ((front, 1.0), (back, -1.0)):
            m.box((knob_x - 0.75, foot + KNOB_Y - 2.5, z), (knob_x + 0.75, foot + KNOB_Y + 2.5, z + out * 0.25), PLATE,
                  grain="y", skip="n" if out > 0 else "s")
            m.tube("z", (knob_x, foot + KNOB_Y), z, z + out * 0.75, 0.4, PLATE, sides=4)
            m.ball((knob_x, foot + KNOB_Y, z + out * 1.4), 0.9, KNOB, sides=8, layers=4)
        for y in HINGES:
            m.tube("y", (px, pz), foot + y - 1.5, foot + y + 1.5, 0.6, PLATE, sides=8)
    return m


def _swings(swing):
    return tuple(swing) if isinstance(swing, (tuple, list)) else (swing, swing)


def models(prefix, door, face, swing=100.0):
    """The five models of the door of `door` (an entry of shell.doors()), named prefix + "door_" +
    a piece. face: how far the room's lining stands off the wall, in 1/16 block. swing: how far
    the leaves stand open, in degrees from shut; one number, or (left, right)."""
    half, top = _size(door)
    left, right = _swings(swing)
    name = lambda piece: f"{prefix}door_{piece}"
    out = [_jamb(name("jamb_l"), -1, half, top, face), _jamb(name("jamb_r"), 1, half, top, face),
           _head(name("head"), half, top, face),
           _leaf(name("leaf_l"), -1, half, top, face, left), _leaf(name("leaf_r"), 1, half, top, face, right)]
    return {m.name: m for m in out}


def held(door, face):
    """The point all five pieces are held from, in the shell's coordinates: the middle of the
    opening, on the face of the room's lining."""
    xs, zs = [x for x, _ in door["cells"]], [z for _, z in door["cells"]]
    dx, dz = door["inward"]
    off = 0.5 + face / 16.0
    return ((min(xs) + max(xs) + 1) / 2.0 + dx * off, (door["y"][0] + door["y"][1] + 1) / 2.0,
            (min(zs) + max(zs) + 1) / 2.0 + dz * off)


def place(canvas, prefix, door, face, swing=100.0, origin=(0, 0, 0)):
    """Hang the door of `door` on the room's side of its wall. Returns the display entities placed."""
    at = held(door, face)
    return sum(K.put(canvas, model, at, mount="wall", facing=FACING[tuple(door["inward"])], origin=origin)
               for model in models(prefix, door, face, swing).values())


def swept(door, face, swing=100.0):
    """What the two leaves stand over on the room's floor, as boxes (x0, z0, x1, z1) in the shell's
    coordinates: the room keeps these clear."""
    hx, _hy, hz = held(door, face)
    dx, dz = door["inward"]
    out = []
    for name, model in models("", door, face, swing).items():
        if "leaf" not in name:
            continue
        lo, hi = model.reach()
        across = [(v - model.anchor[0]) / 16.0 for v in (lo[0], hi[0])]
        into = [(v - model.anchor[2]) / 16.0 for v in (lo[2], hi[2])]
        # model x runs to the model's left: east when it faces south, north when it faces east
        if dz:
            xs, zs = [hx + dz * u for u in across], [hz + dz * w for w in into]
        else:
            xs, zs = [hx + dx * w for w in into], [hz - dx * u for u in across]
        out.append((round(min(xs), 4), round(min(zs), 4), round(max(xs), 4), round(max(zs), 4)))
    return out
