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
"""
import math

from artkit import models as M

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
def glass_ball(m, centre, radius, bands, sides=8, squash=1.0, emit=15):
    """A glass ball drawn as bands of flat tone: bands = [(from, to, layers, material)] with from/to
    as in Model.ball (-1 the bottom, 1 the top). Every face of a band has the one tone, so the ball
    looks the same from all sides. Lit (the default) it is full bright with no face shading: the
    light and dark of it is what is painted (A2: emission 15, shading in the texture). emit=0 is
    the same glass switched off."""
    for t0, t1, layers, mat in bands:
        m.ball(centre, radius, mat, sides=sides, layers=layers, squash=squash, part=(t0, t1),
               faces={"n": mat, "s": mat, "u": mat, "d": mat}, emit=emit, shade=not emit)
    return m


def glass_prism(m, axis, c, a0, a1, radius, mat, sides=8, cap=None, emit=15):
    """A glass prism along `axis` in one flat tone (Model.tube would shade its sides)."""
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
