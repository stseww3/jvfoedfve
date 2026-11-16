"""Shared helpers of the props category (the auto-discovery skips modules that start with "_").

Mounting conventions, the same for every family, so a builder can place any prop without reading
its model:

  floor    the anchor is the centre of the foot; the entity stands on the floor.
  wall     the anchor is on the wall face and the model sticks out along its own +z. `facing` is
           the way the wall face looks ("east" for the entrance front).
  ceiling  the anchor is the hanging point on the underside of the ceiling; the model hangs down.

A display entity is lit by the cell it stands in, so `put()` moves wall and ceiling props a hair off
the surface: the anchor is then in the air cell and not in the wall.

Light: a lamp model only glows itself. The light it throws is an invisible light block, and those
are A2's (sky/_lightkit). `offer_lights()` hands them over; until that tool is in the tree it puts
the blocks down itself so that a test scene is lit.

A face that glows is still lit by the way it looks. The game lights every face of an item by two
lamps fixed in the world, whatever the face emits (the item shader's minecraft_mix_light; the
offline renderer draws the same): a face that looks up shows its tone as painted, one that looks
north or south 0.74 of it, east or west 0.50, down 0.40. shade=False is read for blocks only. A
face is lit as if it looked along the axis of its model nearest to its normal, and that axis turns
with the display: so a glowing piece that must show its tones to one side is drawn in a frame
tilted towards that side and turned back by its display (c342 read it off the 26.3 client and
wrote the frame: ironwork.TILT; between 38.2 and 45 degrees the face that looks out is lit 1.00).
"""
import math

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import blocks as B
from ..common import palette as P

# the way a wall face looks -> the yaw that points a model's +z that way
FACING = {"south": 0.0, "west": 90.0, "north": 180.0, "east": -90.0}
NUDGE = 0.01            # blocks; keeps an anchor that lies on a surface inside the air cell

IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
BRASS = P.mat("brass")
BRASS_D = P.mat("brass_dark")
COPPER = P.mat("old_copper")
# The old copper of the outdoor rain pipes, level with the copper block's plate, which went down a
# step (A0, review #8). The small copper of lamps, ironwork and furniture keeps COPPER.
COPPER_D = P.mat("old_copper", base=1)
ENAMEL = P.mat("enamel")
CREAM = P.mat("cream")


def flat(name, step):
    """One flat tone of a ramp: glass and other smooth surfaces, where the shading is drawn as
    bands of tone instead of noise."""
    return P.mat(name, kind="flat", base=step, bevel=0)


def turn(yaw, v):
    """An offset in a model's own frame as a world offset, for a display placed with `yaw`."""
    r = math.radians(yaw)
    c, s = math.cos(r), math.sin(r)
    return (v[0] * c - v[2] * s, v[1], v[0] * s + v[2] * c)


def put(canvas, model, pos, mount="floor", facing="south", yaw=None, scale=1.0, origin=(0, 0, 0), **opts):
    """Place one display entity; returns 1 (the entity count). pos is in scene coordinates.

    yaw overrides facing (floor and ceiling props turn freely). opts go to artkit.models.display
    (turns, brightness, view).
    """
    if yaw is None:
        yaw = FACING[facing]
    x, y, z = (pos[i] + origin[i] for i in range(3))
    if mount == "wall":
        dx, _, dz = turn(yaw, (0.0, 0.0, NUDGE))
        x, z = x + dx, z + dz
    elif mount == "ceiling":
        y -= NUDGE
    canvas.add_entity(x, y, z, M.display(model, yaw=yaw, scale=scale, **opts))
    return 1


def light_cell(pos, yaw, offset, origin=(0, 0, 0)):
    """The cell that holds a prop's glowing part: the anchor plus an offset given in blocks in the
    model's own frame."""
    d = turn(yaw, offset)
    return tuple(int(math.floor(pos[i] + origin[i] + d[i])) for i in range(3))


def offer_lights(canvas, lights, why):
    """Hand light sources [((x, y, z), level), ...] (cells, scene coordinates) to A2's tool.

    A2 decides where the invisible light blocks really go (sky/_lightkit.take). While that tool is
    not in the tree the blocks are put down here, never over a block that is already there.
    """
    lights = [((int(x), int(y), int(z)), int(level)) for (x, y, z), level in lights]
    if not lights:
        return
    try:
        from ..sky import _lightkit
        take = getattr(_lightkit, "take", None)
    except ImportError:
        take = None
    if take is not None:
        take(canvas, lights, why)
        return
    for (x, y, z), level in lights:
        canvas.set(x, y, z, f"{B.LIGHT}[level={level}]", keep=True)


def east_face(canvas, y, z, x_lo, x_hi, origin=(0, 0, 0)):
    """x of the east face of the outermost block in the row (y, z) between x_lo and x_hi, or None
    when the row is empty: where a wall prop goes on a front that another line has built."""
    ox, oy, oz = origin
    for x in range(x_hi, x_lo - 1, -1):
        if canvas.has(ox + x, oy + y, oz + z):
            return x + 1.0
    return None


# ---- shapes that more than one family uses --------------------------------------------------------
RIVET = flat("iron", 5)


def rivet(m, p, out="z", mat=RIVET, proud=0.5):
    """A rivet head: one texel square, half a texel proud of the face it sits on (or `proud`). p is
    the middle of its foot on that face; `out` is the way the face looks: "x", "-x", "y", "-y", "z"
    or "-z"."""
    k = M.AXES.index(out[-1])
    lo, hi = [v - 0.5 for v in p], [v + 0.5 for v in p]
    lo[k], hi[k] = sorted((p[k], p[k] + (-proud if out.startswith("-") else proud)))
    m.box(tuple(lo), tuple(hi), mat)
    return m


# ---- faces that stand between two axes ------------------------------------------------------------
SETTLE = 0.1            # degrees: how far settle() turns a round piece, to take its faces off the fence
_FENCE = math.sqrt(2.0) * math.sin(math.radians(SETTLE / 2.0))


def _between(normal):
    """The two model axes a face's normal stands between (within half of SETTLE of the plane that
    divides them), or None. A face is asked by its normal, whatever shape it is a side of."""
    order = sorted(range(3), key=lambda i: -abs(normal[i]))
    if abs(normal[order[0]]) - abs(normal[order[1]]) >= _FENCE:
        return None
    return tuple(sorted(order[:2]))


def _drawn(part):
    """(box axis, the normal of its + face) for the pairs of sides of a part that have a face drawn."""
    q = part["rot"][0] if part["rot"] else M.IDENT
    for k in range(3):
        if any(letter not in part["skip"] for letter in M.SIDE[k]):
            yield k, M._qrot(q, M.NORMAL[M.SIDE[k][1]])


def unsettled(model):
    """The drawn faces of a model that stand between two axes: [(part's index, face letters, normal)].
    Empty once settle() has been over the model; a family's test scene may hold its models to that."""
    return [(i, "".join(M.SIDE[k]), normal) for i, part in enumerate(model.parts)
            for k, normal in _drawn(part) if _between(normal)]


def settle(m):
    """Makes the light on a model the same in every copy of the game and in the offline pictures.
    A family runs every model through it once, where it builds them: {name: K.settle(build())}.

    A face of an item is lit as if it looked along the model axis nearest to its normal (the note at
    the head of this file). The slanting flats of an eight-sided tube, ring or ball stand exactly
    between two axes, and which of the two such a face is filed under comes out of the last bit of
    a float: of two pieces of one kind one had its upper flats lit as "up" (1.00) and the other as
    a side (0.50), and a change anywhere in a model could change it again (c342 saw it on the pipes
    in the 26.3 client; this is what he wrote for them, for every family).

    Every round shape that has such faces is turned SETTLE degrees as one piece (the boxes that one
    call of tube(), ring(), ball(), glass_prism() made share a seed; a box of its own is a piece by
    itself): about its own middle, about the model axis the two axes stand across, and always the
    same way round, right-handed about that axis' positive end. The shape stays what it was and
    its boxes meet in the same lines. Its flats then fall to the four directions two and two, the
    same in every piece: of a tube along y, seen from above and counted clockwise from the north,
    two flats are lit as north, two as east, two as south, two as west. A tenth of a degree moves
    the rim of the widest piece a hundredth of a texel. Faces that are meant to stand in a frame
    of their own (machines/_relit) are not for this: settle the rest of the model before they are
    put in."""
    groups = {}
    for part in m.parts:
        groups.setdefault(part["seed"], []).append(part)
    for parts in groups.values():
        for _ in range(4):
            pair = next((pair for part in parts for _, normal in _drawn(part)
                         for pair in [_between(normal)] if pair), None)
            if pair is None:
                break
            turn_ = M.quat(M.AXES[3 - pair[0] - pair[1]], SETTLE)
            centres = [[(part["lo"][i] + part["hi"][i]) / 2.0 for i in range(3)] for part in parts]
            pivot = [sum(c[i] for c in centres) / len(centres) for i in range(3)]
            for part, c in zip(parts, centres):
                d = M._qrot(turn_, [c[i] - pivot[i] for i in range(3)])
                to = [pivot[i] + d[i] for i in range(3)]
                half = [(part["hi"][i] - part["lo"][i]) / 2.0 for i in range(3)]
                q = part["rot"][0] if part["rot"] else M.IDENT
                part["lo"] = tuple(to[i] - half[i] for i in range(3))
                part["hi"] = tuple(to[i] + half[i] for i in range(3))
                part["rot"] = (M._qmul(turn_, q), tuple(to))
        else:
            raise ValueError(f"{m.name}: faces stay between two axes however the piece is turned")
    return m


# Clear glass holds a little of the sky, as the roof lights do (materials/windows: their reflection is
# night glass 4). A white stroke was the brightest thing in a room after the lamps and read as paper
# stuck in the air; this tone shows on dark wood and on a pale lining alike and outshines neither.
SHEEN = P.RAMPS["night_glass"][4]
# On a narrow pane with dark wood close behind it the stroke is the one cold thing on the piece and
# read as a blue ribbon stuck on the door (cr4-#2): there it is a step lower.
SHEEN_DIM = P.RAMPS["night_glass"][3]
_PANE_AXES = {"u": (0, 2), "n": (0, 1), "s": (0, 1), "e": (2, 1), "w": (2, 1)}   # across and down a face


def sheen_texels(w, h, n=None):
    """The texels of the reflection on a pane w by h texels, as (across, down) from its upper left
    corner: a glancing stroke two texels wide that climbs n steps to the right (the block windows'
    stroke, materials/windows), and a shorter one beside it, or under it where the pane is narrow.
    Two texels wide, so the steps share edges and the stroke is a band, not a row of dots. n is a
    third of the pane's shorter side unless given, 2 to 4."""
    if n is None:
        n = max(2, min(4, int(round(min(w, h) / 3.0))))
    left = 1 if w >= n + 3 else 0
    out = [(left + i + d, n - i) for i in range(n) for d in (0, 1)]
    x0, y0 = (left + 3, n + 2) if w >= n + 6 else (left + 1, n + 3)
    out += [(x0 + i + d, y0 - i) for i in range(n - 1) for d in (0, 1)]
    return [(x, y) for x, y in out if 0 <= x < w and 0 <= y < h]


def pane(m, lo, hi, face, sheen=True, dim=False):
    """A pane of clear glass on the face `face` ("n", "s", "e", "w" or "u") of the thin box lo..hi.

    The glass itself is left out. What says it is there is its reflection (sheen_texels) in the
    pane's upper corner as one looks at it (the far left corner of a pane that lies flat), cut out
    of nothing, so whatever is behind the pane shows. Every family draws clear glass this way.
    sheen=False leaves a pane bare: in a row of panes not every one has a reflection, as with the
    block windows; a number is the length of the long stroke. dim=True is for a pane with dark
    wood close behind it (SHEEN_DIM). The pane is at least five texels each way, and sits a
    quarter of a texel behind its frame."""
    if not sheen:
        return m
    across, down = _PANE_AXES[face]
    w, h = (max(1, int(round(abs(hi[i] - lo[i]) * m.px))) for i in (across, down))   # as Model.faces() sizes it
    n = None if sheen is True else int(sheen)
    rows = [["."] * w for _ in range(h)]
    for i, j in sheen_texels(w, h, n):
        rows[j][i] = "g"
    name = f"prop_sheen_{w}x{h}" + ("" if n is None else f"_{n}") + ("_dim" if dim else "")
    picture = Sprite(name, ["".join(row) for row in rows], {"g": SHEEN_DIM if dim else SHEEN})
    m.box(lo, hi, BRASS, skip="".join(f for f in "nsewud" if f != face), faces={face: picture})
    return m


def wall_entry(m, x, y, radius=0.75):
    """Where a conduit that runs up or down a wall turns into it, so that it never just stops. For a
    wall-mounted model (the wall is its plane z = 0): a round flange on the wall and the knuckle of
    the bend, about the point (x, y) where the conduit's axis ends. The conduit itself is a tube of
    this radius whose axis is one texel off the wall."""
    m.tube("z", (x, y), 0.0, 1.0, radius + 1.0, IRON)
    m.tube("z", (x, y), 1.0, radius + 1.25, radius, IRON_D)
    return m


def switch_key(m, at, side=1.0):
    """The turn key of a brass lampholder: a stem and a flat grip, out along x from `at`, a point
    on the holder's surface. side=-1 points it the other way."""
    x, y, z = at
    a, b = sorted((x, x + side))
    m.box((a, y - 0.5, z - 0.5), (b, y + 0.5, z + 0.5), BRASS_D)
    a, b = sorted((x + side, x + 2.0 * side))
    m.box((a, y - 1.0, z - 0.5), (b, y + 1.0, z + 0.5), BRASS)
    return m


def glass_ball(m, centre, radius, bands, sides=8, squash=1.0, emit=15):
    """A glass ball drawn as bands of flat tone: bands = [(from, to, layers, material)] with from/to
    as in Model.ball (-1 the bottom, 1 the top). Every face of a band has the one tone. Lit (the
    default) every face emits (A2: emission 15, the light and dark painted as bands), so the cell's
    own light does not count; the way a face looks still does (the note at the head of this file):
    the faces that look east or west show half their tone. emit=0 is the same glass switched off."""
    for t0, t1, layers, mat in bands:
        m.ball(centre, radius, mat, sides=sides, layers=layers, squash=squash, part=(t0, t1),
               faces={"n": mat, "s": mat, "u": mat, "d": mat}, emit=emit, shade=not emit)
    return m


def glass_prism(m, axis, c, a0, a1, radius, mat, sides=8, cap=None, emit=15):
    """A glass prism along `axis` in one flat tone (Model.tube would shade its sides in the picture;
    the game still lights each side by the way it looks, see the note at the head of this file)."""
    k = M.AXES.index(axis)
    o1, o2 = [i for i in range(3) if i != k]
    origin = [0.0, 0.0, 0.0]
    origin[k], origin[o1], origin[o2] = (a0 + a1) / 2.0, c[0], c[1]
    hw = radius * math.tan(math.pi / sides)
    lo, hi = [0.0] * 3, [0.0] * 3
    lo[k], hi[k] = a0, a1
    lo[o1], hi[o1] = c[0] - hw, c[0] + hw
    lo[o2], hi[o2] = c[1] - radius, c[1] + radius
    cap = cap or mat
    faces = {M.SIDE[k][0]: cap, M.SIDE[k][1]: cap, M.SIDE[o2][0]: mat, M.SIDE[o2][1]: mat}
    m._n += 1
    seed = m._n
    for i in range(sides // 2):
        angle = 360.0 * i / sides
        m.box(lo, hi, mat, rot=(axis, angle, tuple(origin)) if angle else None, skip="".join(M.SIDE[o1]),
              faces=faces, seed=seed, grain=axis, emit=emit, shade=not emit)
    return m


GLOW_DIM, GLOW_MID, GLOW_HOT = flat("glow", 1), flat("glow", 2), flat("glow", 3)


def bulb(m, top, glass=3.0, cap=1.5):
    """A bare incandescent bulb hanging from `top`: a brass cap and a small pear of amber glass, the
    hot spot in the middle of it. The glass is the only thing that glows."""
    x, y, z = top
    m.tube("y", (x, z), y - cap, y, 1.0, BRASS_D, sides=4)
    y -= cap
    glass_prism(m, "y", (x, z), y - 1.0, y, 1.0, GLOW_DIM, cap=GLOW_DIM)
    glass_prism(m, "y", (x, z), y - glass, y - 1.0, 1.5, GLOW_HOT, cap=GLOW_MID)
    glass_prism(m, "y", (x, z), y - glass - 0.75, y - glass, 0.75, GLOW_MID, sides=4, cap=GLOW_MID)
    return y - glass - 0.75
