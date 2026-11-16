"""interiors/_starhall_wiring -- the star hall's surface wiring (one of starhall.PARTS: the hall
calls dress() at the end of its own and adds models() to its own; the underscore keeps the
category's discovery from taking this file for a package).

Two services, both drawn the way the lamps of props/lamps draw theirs: a conduit a texel and a
half thick whose axis is one texel off the wall, and which never just stops.

  lamps   The circuit of the aisles' wall lamps. It leaves the switchboard's east end, runs east
          along the north wall one texel over the dado's top (a: the wainscot's ledge, b: the joint
          over the slate course) and sends a riser up to the wall plate of every lamp it passes
          under. It goes through the pilasters, with a collar on either side, and ends in the
          riser of the last lamp. The lamp over the board is fed straight up from the board's top.
          The south aisle has no board. Its feed crosses under the floor and comes out of the wall
          under the lamp between the two charts, across from the board's middle: a riser between
          the charts to that lamp, and the same run east along the dado.
            a  "academy"   brass tube, turned collars and bands, a tee under each lamp
            b  "workshop"  iron pipe in riveted straps, a cast junction box under each lamp
  time    One cable from the mother clock to the board: the line that carries its beat to the
          dials of the house. It is under the floor, in the gap round the pier that the grating
          covers, and shows at its two ends: down the north steps of the clock's plinth into the
          grating, and up out of the floor at the foot of the board's east end into a terminal.

No source of light, no emblem. Twelve display entities. Nothing lies on the hall's axis, and the
tube is a tone under the pier's face in the first look (S.V7).

The doors of the battery room and of the plate vault (starhall.aisle_doors(): x 7 in the north and
in the south wall, two blocks high) open under the runs, between the board's end or the charts and
the first pilaster: a run passes one texel over their heads, on the wall, and what holds it is
fixed over the pipe.
"""
import functools

from artkit import models as M

from ..common import palette as P
from ..main import shell
from ..props import _kit as K

PREFIX = "int_starhall_"
VERSIONS = ("a", "b")

R = 0.75                    # the conduit's radius, texels: props/lamps' conduits (K.wall_entry)
OFF = 1.0                   # its axis off the wall
OVER = 1.0                  # and over the dado's top
DADO = 2                    # blocks: the wainscot (a) and the slate course (b) are that high
PLATE_FOOT = 11.0           # texels from a bracket's anchor down to the foot of its wall plate (lamps._bracket_b)
BOARD_TOP = 3.5             # blocks over the floor: three rows of panels under a slab's lower half
SPAN = 40.0                 # texels: the longest run one piece carries; a longer one is cut 32 from its far end
CASE_HALF = 0.75            # blocks: half the width of the mother clock's case (machines/clock)
CASE_DEPTH = 0.75           # and the case's depth before the pier's face
LEAD_OUT = 16.0             # texels from the case's side to the time line's foot on the grating

# One tone each, without grain: a facet of the tube is a texel wide, and grain broke it into dashes.
# Model.tube takes a tone up on the facets that look up and one down on those that look out and down.
# a: the brass is old lacquer, the tone of the bead on the board's end (K.BRASS_D). Two tones up, the
# facets that look into the hall read 0.33 from inside the doorway and the pier's face 0.23; one tone
# up they read 0.26; at this tone 0.20 (hall: nothing of the wiring lighter than the pier's face).
PAINT = {
    "a": dict(tube=K.flat("brass", 1), fit=K.flat("brass", 0), box=None),
    "b": dict(tube=K.flat("iron", 4), fit=K.flat("iron", 3), box=P.mat("iron", base=4)),
}
CABLE = K.flat("old_copper", 1)     # the lamps' cable (props/lamps.CABLE)


def _band(m, axis, at, paint, c=(0.0, OFF), long=1.0):
    """A collar round the conduit: a texel long from `at` on, half a texel proud all round."""
    lo, hi = sorted((at, at + long))
    m.tube(axis, c, lo, hi, R + 0.5, paint["fit"], sides=8)


def _strap(m, axis, at, paint):
    """What holds the conduit to the wall every block or so. a: a band. b: a strap riveted to the
    wall: on a riser an ear on either side, on a run one ear, over the pipe. A run passes a texel
    over the head of a door two blocks high (the plate vault's, the battery room's), and an ear
    under the pipe hung before the opening with nothing behind it."""
    _band(m, axis, at - 0.5, paint)
    if paint["box"] is None:
        return
    if axis == "x":
        m.box((at - 0.5, R + 0.5, 0.0), (at + 0.5, R + 2.0, 0.5), paint["fit"])
        K.rivet(m, (at, R + 1.25, 0.5))
        return
    for s in (-1.0, 1.0):
        m.box((s * (R + 0.5), at - 0.5, 0.0), (s * (R + 2.0), at + 0.5, 0.5), paint["fit"])
        K.rivet(m, (s * (R + 1.25), at, 0.5))


def _joint(m, paint, left, right, entry):
    """Where the riser leaves the run. a: a tee, an elbow where the run ends, and a rose on the wall
    where the feed comes out of it. b: a cast box with a riveted lid; the feed comes into its back."""
    if paint["box"] is not None:
        top = OFF + R + 0.5
        m.box((-2.5, -2.5, 0.0), (2.5, 2.5, top), paint["box"])
        m.box((-1.5, -1.5, top), (1.5, 1.5, top + 0.5), paint["fit"])
        K.rivet(m, (-1.0, 1.0, top + 0.5), proud=0.25)
        K.rivet(m, (1.0, -1.0, top + 0.5), proud=0.25)
        _band(m, "y", 2.5, paint)
        for side, there in ((-1.0, left), (1.0, right)):
            if there:
                _band(m, "x", side * 2.5, paint, long=side)
        return
    if entry:
        m.tube("z", (0.0, 0.0), 0.0, 0.5, R + 1.75, paint["fit"], sides=8)
    if entry or not (left and right):
        m.tube("z", (0.0, 0.0), 0.5 if entry else OFF - R - 0.25, OFF + R + 0.25, R + 0.5, paint["fit"], sides=8)
        return
    m.tube("x", (0.0, OFF), -2.0, 2.0, R + 0.5, paint["fit"], sides=8)
    m.tube("y", (0.0, OFF), 0.0, 2.0, R + 0.5, paint["fit"], sides=8)


def _name(version, left, right, rise, entry=False):
    return f"{PREFIX}wire_{version}_{int(left)}_{int(right)}_{int(rise)}" + ("_in" if entry else "")


def _piece(version, left, right, rise, entry=False):
    """One length of conduit on a wall. The wall is the plane z = 0 and the model stands out along
    +z; the run's axis is y = 0. `left` and `right` are the texels of run to either side of x = 0,
    `rise` those of a riser at x = 0 up to a lamp's plate. A run ends in a collar: against a
    pilaster, a casing or the next piece. A riser alone stands on a flange (the board's top) and
    its anchor is its head, under the lamp's plate."""
    paint = PAINT[version]
    alone = rise and not (left or right or entry)
    m = M.Model(_name(version, left, right, rise, entry), anchor=(0.0, rise if alone else 0.0, 0.0))
    if left or right:
        m.tube("x", (0.0, OFF), -left if left else -R, right if right else R, R, paint["tube"], sides=8)
    for side, there in ((-1.0, left), (1.0, right)):
        if there:
            _band(m, "x", side * there, paint, long=-side)
            for at in range(8, int(there) - 3, 16):
                _strap(m, "x", side * at, paint)
    if rise:
        m.tube("y", (0.0, OFF), 0.0 if alone else -R, rise, R, paint["tube"], sides=8)
        _band(m, "y", rise, paint, long=-1.0)
        for at in range(14, int(rise) - 3, 16):
            _strap(m, "y", float(at), paint)
        if alone:
            m.tube("y", (0.0, OFF), 0.0, 1.0, R + 1.0, paint["fit"], sides=8)
        else:
            _joint(m, paint, left, right, entry)
    return m


def _lead_clock(version):
    """The time line where it leaves the clock. The model's axes are the scene's and its anchor is
    the cable's foot on the grating, north of the plinth's lower step: z counts back south from
    there to the case's north side, LEAD_OUT texels away. The cable comes out of the case's
    skirting, crosses the ledge beside it, and goes down the two steps of the plinth, on the stone
    all the way, into a flange on the grating."""
    paint = PAINT[version]
    m = M.Model(f"{PREFIX}lead_{version}_clock")
    low, high = LEAD_OUT - 12.0, LEAD_OUT - 4.0     # the faces of the lower and of the upper step
    for lo, hi in (((-0.5, 16.0, high - 1.0), (0.5, 17.0, LEAD_OUT + 0.5)),     # on the plinth's top, into the case
                   ((-0.5, 9.0, high - 1.0), (0.5, 16.0, high)),                # down the upper step
                   ((-0.5, 8.0, low - 1.0), (0.5, 9.0, high)),                  # on the lower step
                   ((-0.5, 1.0, low - 1.0), (0.5, 8.0, low)),                   # down it
                   ((-0.5, 0.0, 0.0), (0.5, 1.0, low))):                        # on the grating
        m.box(lo, hi, CABLE)
    m.tube("y", (0.0, -0.5), 0.0, 0.5, R + 1.0, paint["tube"], sides=8)
    m.tube("y", (0.0, -0.5), 0.5, 1.5, R + 0.25, paint["fit"], sides=8)
    return m


def _lead_board(version):
    """The time line where it reaches the board: wall-mounted on the plate that closes the board's
    east end (half a texel thick), its anchor at the plate's foot, in the middle. A shoe on the
    floor, the cable up the plate, a terminal box under the first joint of the board's rows."""
    paint = PAINT[version]
    m = M.Model(f"{PREFIX}lead_{version}_board")
    m.box((-1.5, 0.0, 0.5), (1.5, 0.75, 2.5), paint["fit"])
    m.box((-0.5, 0.75, 0.5), (0.5, 10.0, 1.5), CABLE)
    m.box((-1.5, 10.0, 0.5), (1.5, 14.0, 2.5), paint["box"] or paint["tube"])
    K.rivet(m, (0.0, 12.0, 2.5), mat=paint["fit"] if paint["box"] is None else K.RIVET, proud=0.25)
    return m


# ---- where the pieces go ----------------------------------------------------------------------------
def _hall():
    from . import starhall
    return starhall


def _runs(version):
    """The pieces of the lamp circuit: [(key of _piece, (x, y) on the wall, wall)], wall "north" or
    "south". Lengths are measured along the wall from west to east; a piece on the south wall is
    seen from the other side, so its left is the east."""
    hall = _hall()
    xs = hall.aisle_lamp_xs()
    posts = hall.beam_xs()
    run_y = hall.FEET + DADO + OVER / 16.0
    board = hall.STYLE[version]["board"]
    board_end = hall.BOARD_MID_X - len(board[0]) // 2 + len(board[0])
    out = []

    def piece(wall, x, west, east, rise=0.0, entry=False, y=run_y):
        left, right = (west, east) if wall == "north" else (east, west)
        out.append(((version, left, right, rise, entry), (x, y), wall))

    def run(wall, a, b):
        """A plain run from a to b, in one piece or two."""
        if b - a <= 0:
            return
        if (b - a) * 16.0 > SPAN:
            run(wall, a, b - 2.0)
            a = b - 2.0
        half = (b - a) * 8.0
        piece(wall, (a + b) / 2.0, half, half)

    def rise(y):
        return (y - PLATE_FOOT / 16.0 - run_y) * 16.0

    for wall in ("north", "south"):
        if wall == "north":
            head = (hall.BOARD_LAMP_Y - PLATE_FOOT / 16.0 - (hall.FEET + BOARD_TOP)) * 16.0
            piece(wall, xs[0], 0.0, 0.0, head, y=hall.BOARD_LAMP_Y - PLATE_FOOT / 16.0)
            run(wall, float(board_end), float(posts[0]))
        else:
            first = float(posts[0]) - xs[0]             # blocks from the feed to the first pilaster
            if first * 16.0 > SPAN:
                first -= 2.0
            piece(wall, xs[0], 0.0, first * 16.0, rise(hall.BOARD_LAMP_Y), entry=True)
            run(wall, xs[0] + first, float(posts[0]))
        for x in xs[1:]:
            west = max(p + 1.0 for p in posts if p + 1.0 <= x)
            east = min((float(p) for p in posts if p >= x), default=x)
            piece(wall, x, (x - west) * 16.0, (east - x) * 16.0, rise(hall.AISLE_LAMP_Y))
    return out


def _leads(version):
    """The two ends of the time line: [(model, position, placing)]."""
    hall = _hall()
    seat = sorted(shell.layout().seat)
    mx, mz = seat[len(seat) // 2]
    board = hall.STYLE[version]["board"]
    board_end = hall.BOARD_MID_X - len(board[0]) // 2 + len(board[0])
    side = mz + 0.5 - CASE_HALF                 # the case's north side
    return [(f"{PREFIX}lead_{version}_clock", (mx + CASE_DEPTH / 2.0, hall.FEET, side - LEAD_OUT / 16.0), dict()),
            (f"{PREFIX}lead_{version}_board", (float(board_end), hall.FEET, hall.Z0 + 0.5),
             dict(mount="wall", facing="east"))]


@functools.lru_cache(maxsize=None)
def _models():
    # A conduit is an eight-sided tube: its slanting flats stand exactly between two axes, and the
    # game lit such a flat as the one or the other by the last bit of a float, so that of two lengths
    # of one run one could show a light flat and the next a dark one. K.settle (the kit's, 11-16)
    # turns every tube a tenth of a degree: every length is lit the same way.
    out = {}
    for version in VERSIONS:
        for key, _at, _wall in _runs(version):
            m = K.settle(_piece(*key))
            out[m.name] = m
        for m in (_lead_clock(version), _lead_board(version)):
            out[m.name] = K.settle(m)
    return out


def models():
    return dict(_models())


def dress(canvas, origin=(0, 0, 0), version="a"):
    """Wire the hall that stands at `origin`; returns the display entities placed."""
    hall = _hall()
    made = _models()
    n = 0
    for key, (x, y), wall in _runs(version):
        face, facing = (float(hall.Z0), "south") if wall == "north" else (hall.Z1 + 1.0, "north")
        n += K.put(canvas, made[_name(*key)], (x, y, face), mount="wall", facing=facing, origin=origin)
    for name, pos, how in _leads(version):
        n += K.put(canvas, made[name], pos, origin=origin, **how)
    return n
