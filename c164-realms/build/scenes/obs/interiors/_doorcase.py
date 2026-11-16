"""The doors of the wing rooms: what hangs in a doorway of main/shell (shell.doors()), on the room's side.

Two kinds, one for each storey. Nothing here is a block, a barrier or a light source; a leaf stands
open and no cell a player walks in is taken.

A door case and two panelled leaves, for a room on the main floor (models(), place(), swept()).
The doorway is two cells wide, three rows high, in a wall one block thick. On the room's side the
kit gives it what a joiner would: boards lining the opening, a casing on the wall either side
standing on a plinth block, a frieze and a cap over the head, and the two leaves, hinged on the
casings and swung into the room. The gallery's side of the wall is not touched. Brass is on the
knobs and the hinges only.

An iron leaf, for a room on the ground floor (iron_models(), iron_place(), iron_swept()): the plate
vault's door keeps a fire out and the battery room's keeps its acid in, and wood does neither. The
doorway is one cell wide and two rows high, and its case is stone and the shell's own
(shell.door_cases()). The leaf is the building's blue iron, a plate with three ledges riveted on
either face, the kin of the entrance door's (props/ironwork): it lies on the room's face of the
wall, lapping over the opening's edges, hung on three knuckles beside one of them, and stands
folded back flat against the wall on that side. One display entity.

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

The iron leaf is drawn in the same space and held from the middle of the opening's top row. `hinge`
is the end of the wall its knuckles are on, as a compass word ("west", "east"; "north", "south" in
a wall that runs that way): open, the leaf lies against the wall on that side of the opening, and
that stretch of wall is kept bare, two rows high and IRON_REACH wide.

    iron_models(prefix, door, hinge, face, swing)  -> {name: Model}      one: prefix + "door_iron"
    iron_place(canvas, prefix, door, hinge, face, swing, origin) -> 1    the display entity placed
    iron_swept(door, hinge, face, swing)           -> [(x0, z0, x1, z1)] what the leaf stands over on the floor
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
KNOB = P.mat("brass", base=2)               # a turned knob, a step under the brass of the room's dials
KNOB_END = K.flat("brass", 2)

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


def _size(door, rows=ROWS, wide=None):
    """(half the opening's width, its height) in model units."""
    cells, (y0, y1) = door["cells"], door["y"]
    if y1 - y0 + 1 != rows:
        raise ValueError(f"the door kit is drawn for an opening {rows} rows high, not {y1 - y0 + 1}")
    if wide is not None and len(cells) != wide:
        raise ValueError(f"the door kit is drawn for an opening {wide} wide, not {len(cells)}")
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
            m.tube("z", (knob_x, foot + KNOB_Y), z, z + out * 0.75, 0.35, PLATE, sides=4)
            m.tube("z", (knob_x, foot + KNOB_Y), z + out * 0.75, z + out * 1.5, 0.75, KNOB, sides=8, cap=KNOB_END)
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
    return {m.name: K.settle(m) for m in out}


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


def _over(door, at, model):
    """What a model held at `at` on the wall of `door` stands over on the room's floor: (x0, z0, x1, z1)
    in the shell's coordinates."""
    hx, _hy, hz = at
    dx, dz = door["inward"]
    lo, hi = model.reach()
    across = [(v - model.anchor[0]) / 16.0 for v in (lo[0], hi[0])]
    into = [(v - model.anchor[2]) / 16.0 for v in (lo[2], hi[2])]
    # model x runs to the model's left: east when it faces south, north when it faces east
    if dz:
        xs, zs = [hx + dz * u for u in across], [hz + dz * w for w in into]
    else:
        xs, zs = [hx + dx * w for w in into], [hz - dx * u for u in across]
    return (round(min(xs), 4), round(min(zs), 4), round(max(xs), 4), round(max(zs), 4))


def swept(door, face, swing=100.0):
    """What the two leaves stand over on the room's floor, as boxes (x0, z0, x1, z1) in the shell's
    coordinates: the room keeps these clear."""
    at = held(door, face)
    return [_over(door, at, model) for name, model in models("", door, face, swing).items() if "leaf" in name]


# ---- the iron leaf of a ground-floor room ---------------------------------------------------------
IRON_ROWS = 2               # the opening the iron leaf is drawn for: one cell wide, this many rows high
IRON = K.IRON               # the plate
LEDGE = K.IRON_D            # what is riveted on it, and the knuckles
LATCH = K.flat("iron", 4)   # the latch bar: iron a hand has worn
SHEET = 1.5                 # the plate's thickness
LAP = 0.5                   # shut, the leaf laps this far over the wall either side of the opening and over its head,
FOOT = 0.5                  # and clears the floor by this much
AIR = 0.25                  # between the wall and what lies nearest to it, the leaf shut or folded back
PROUD_L = 0.5               # a ledge stands this proud of the plate, on both faces,
HEAD = 0.5                  # and a rivet's head as much again
LEDGES = ((0.0, 5.0), (14.0, 17.0), (28.0, 31.0))   # from the leaf's foot: the kick plate, the lock ledge, the top ledge
KNUCKLES = ((1.5, 4.5), (14.0, 17.0), (28.0, 31.0))     # a hinge at each ledge: the ledges are its straps
KNUCKLE = 1.0               # a knuckle's radius
PIN = 0.5                   # the pin stands this far outside the leaf's hinge edge: the knuckle ends on the opening's edge
ACROSS = (2.5, 6.5, 10.5, 14.5)                     # rivets across a ledge, from the hinge edge
ROWS_OF = (3.5, 15.5, 29.5)                         # the height of the row on each ledge,
CORNERS = 1.5                                       # of the two at the kick plate's lower corners,
UP = (7.5, 11.5, 19.5, 22.5, 25.5)                  # and of those up the plate's two edges between the ledges
PULL = (14.0, 13.5, 4.0, 1.5)   # the bar to pull the leaf shut by, on the face that looks at the hall when it is shut and
#                                 into the room when it stands open: from the hinge edge, from the foot, its length, how
#                                 far it stands off the ledge. It takes the place of the lock ledge's last rivet
IRON_REACH = (2.0 * PIN + LAP + 2.0 * (8.0 + LAP)) / 16.0   # blocks of wall the folded leaf covers, from the opening's edge


def _iron_held(top, face):
    return (0.0, top - 8.0, face)


def _side(door, hinge):
    """-1 or 1: the side of the model a leaf hangs on whose knuckles are on the `hinge` end of the wall."""
    right = {(0, 1): "east", (0, -1): "west", (1, 0): "north", (-1, 0): "south"}[tuple(door["inward"])]
    left = {"east": "west", "west": "east", "north": "south", "south": "north"}[right]
    if hinge not in (left, right):
        raise ValueError(f"a door in this wall hangs on its {left} or its {right} end, not {hinge!r}")
    return 1 if hinge == right else -1


def _iron_leaf(name, side, half, top, face, swing):
    """The iron leaf, swung `swing` degrees into the room about its pin; 180 lays it flat against
    the wall. Drawn shut, lying on the wall over the opening, and turned as one piece. Both faces
    carry the ledges and their rivets; the face that shows when the leaf is folded back has the
    pull, the one that then looks at the wall a latch bar that lies flat."""
    m = M.Model(name, anchor=_iron_held(top, face))
    wide, tall = 2.0 * (half + LAP), top + LAP - FOOT
    edge = side * (half + LAP)                          # the hinge edge of the shut leaf
    at = lambda u: edge - side * u                      # across the leaf, from its hinge edge
    back = face + AIR + PROUD_L                         # the plate: the face towards the wall when shut,
    front = back + SHEET                                # and the one towards the room
    # the pin: where the folded leaf's rivets clear the wall as the shut leaf's ledges do
    px, pz = side * (half + LAP + PIN), face + AIR + (PROUD_L + SHEET + PROUD_L + HEAD) / 2.0
    with m.turned(("y", side * swing), about=(px, 0.0, pz)):
        m.box((at(0.0), FOOT, back), (at(wide), FOOT + tall, front), IRON, grain="y")
        for a, b in LEDGES:
            m.box((at(0.0), FOOT + a, back - PROUD_L), (at(wide), FOOT + b, back), LEDGE, grain="x", skip="s")
            m.box((at(0.0), FOOT + a, front), (at(wide), FOOT + b, front + PROUD_L), LEDGE, grain="x", skip="n")
        pull_u, pull_v, pull_long, pull_off = PULL
        on_ledge = [(u, v) for v in ROWS_OF for u in ACROSS] + [(u, CORNERS) for u in (ACROSS[0], ACROSS[-1])]
        on_plate = [(u, v) for v in UP for u in (ACROSS[0], ACROSS[-1])]
        for spots, off in ((on_ledge, PROUD_L), (on_plate, 0.0)):
            for u, v in spots:
                K.rivet(m, (at(u), FOOT + v, front + off), out="z", proud=HEAD)
                if not (pull_u < u + 0.5 and u - 0.5 < pull_u + 1.0 and pull_v < v + 0.5 and v - 0.5 < pull_v + pull_long):
                    K.rivet(m, (at(u), FOOT + v, back - off), out="-z", proud=HEAD)
        out = back - PROUD_L - pull_off                 # the pull: two feet through the ledge, a brass bar on them
        for v in (pull_v, pull_v + pull_long - 1.0):
            m.box((at(pull_u), FOOT + v, out), (at(pull_u + 1.0), FOOT + v + 1.0, back), K.BRASS_D, skip="s")
        m.box((at(pull_u), FOOT + pull_v, out), (at(pull_u + 1.0), FOOT + pull_v + pull_long, out + 0.5), K.BRASS,
              grain="y")
        row = ROWS_OF[1]                                # the latch: a flat bar on the lock ledge, to the leaf's free edge
        m.box((at(ACROSS[-1] - 2.0), FOOT + row - 0.5, front + PROUD_L), (at(wide), FOOT + row + 0.5, front + PROUD_L + HEAD),
              LATCH, grain="x", skip="n")
        for a, b in KNUCKLES:
            m.tube("y", (px, pz), FOOT + a, FOOT + b, KNUCKLE, LEDGE, sides=8)
    return K.settle(m)


def iron_models(prefix, door, hinge, face=0.0, swing=180.0):
    """The model of the iron leaf of `door` (an entry of shell.doors(), one cell wide and two rows
    high), named prefix + "door_iron". hinge: the end of the wall its knuckles are on, a compass
    word. face: how far the room's lining stands off the wall, in 1/16 block. swing: how far the
    leaf stands open, in degrees from shut."""
    half, top = _size(door, IRON_ROWS, 1)
    m = _iron_leaf(f"{prefix}door_iron", _side(door, hinge), half, top, face, swing)
    return {m.name: m}


def iron_held(door, face=0.0):
    """The point the iron leaf is held from, in the shell's coordinates: the middle of the opening's
    top row, on the face of the room's lining. The cell before it lights the leaf."""
    x, _y, z = held(door, face)
    return (x, door["y"][1] + 0.5, z)


def iron_place(canvas, prefix, door, hinge, face=0.0, swing=180.0, origin=(0, 0, 0)):
    """Hang the iron leaf of `door` on the room's side of its wall. Returns the display entities placed."""
    at = iron_held(door, face)
    return sum(K.put(canvas, model, at, mount="wall", facing=FACING[tuple(door["inward"])], origin=origin)
               for model in iron_models(prefix, door, hinge, face, swing).values())


def iron_swept(door, hinge, face=0.0, swing=180.0):
    """What the iron leaf stands over on the room's floor, as boxes (x0, z0, x1, z1) in the shell's
    coordinates: the room keeps this clear, and the wall behind it bare."""
    at = iron_held(door, face)
    return [_over(door, at, model) for model in iron_models("", door, hinge, face, swing).values()]
