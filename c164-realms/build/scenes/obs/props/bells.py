"""Props, the bells: the electric bell of the entrance and the push that rings it.

    bell(canvas, pos, facing)   a gong under a pair of coils on an iron back; beside the gong hangs the
                                hammer, a piece of its own, which strikes it: the strokes of CODE, once
                                in LOOP ticks, each with the bell's note
    push(canvas, pos, facing)   a brass plate with a rose and a button; its wire goes up an iron tube
                                and into the wall

Both are wall props (props/_kit: the anchor on the wall's face, the model out along its own +z);
pos is the middle of the back, facing the way the wall looks. Bronze, brass and iron, nothing that
glows: on a front they stay under the globe lamps.

In the master scene (build): the bell hangs on the pier south of the entrance's south gate, over
the bracket lamp and under the string course, and the push on the pier south of the doorway, under
the door's plate, at the height of a hand. Both places are read off main/facade.

What moves: the hammer. It rests clear of the gong's rim and is thrown against it by the coils --
here it slides the GAP towards the gong and back, which from the court is what a hammer on a
spring does. motion/_kit drives it (slide) and plays the note (sound).
"""
import functools
import math

from artkit import models as M

from ..common import skeleton as S
from ..motion import _kit as MK
from . import _kit as K

PREFIX = "prop_bell_"
PX = 1.0 / 16.0
VIEW = M.MID                    # seen from the court: drawn up to 64 blocks away

BACK = (6.5, 7.25)              # half the width and the height of the bell's back, in texels
GONG = (-1.25, -3.0)            # the middle of the gong on the back
GONG_R = 4.0
BALL = 0.85                     # the hammer's ball
GAP = 1.5                       # texels from the ball to the gong's rim while it rests: more than a real
                                # bell's, so that the stroke is seen from the court
PIVOT = (GONG[0] + GONG_R + GAP + BALL, 5.5, 2.5)   # where the hammer's spring is held: its anchor
BRONZE = K.BRASS_D              # the gong: bell metal, darker than the brass of the terminals

# The call. A stroke throws the hammer in OUT ticks and lets it back in BACK_IN; the strokes of a
# group follow each other every BEAT ticks, the groups of CODE stand REST ticks apart, and the
# whole is given once in LOOP ticks: three and three, the way a block bell asks for the line.
CODE = (3, 3)
BEAT, REST, LOOP = 10, 30, 300
OUT, BACK_IN = 2, 4
NOTE = dict(event="minecraft:block.note_block.bell", volume=0.35, pitch=1.6, reach=12.0)

PUSH = (2.0, 2.75)              # half the width and the height of the push's plate
TUBE = 0.4                      # the radius of the iron tube a wire runs in
PUSH_UP = 0.45                  # the push's middle over the top of the plinth's lower course: 1.45 over the paving
BELL_DOWN = 0.05                # the bell's back ends this far under the string course


def _bell():
    """The bell without its hammer. From the back outwards: the iron back with four rivets; over the
    middle the case of the two coils, its two brass terminals on top and the tube of the wire going
    up from it; under it the gong on its post, a nut on its middle."""
    m = M.Model(PREFIX + "gong")
    w, h = BACK
    m.box((-w, -h, 0.0), (w, h, 0.75), K.IRON_D)
    for x in (-w + 1.0, w - 1.0):
        for y in (-h + 1.0, h - 1.0):
            K.rivet(m, (x, y, 0.75), out="z")
    m.box((-5.0, 2.5, 0.75), (3.0, 6.5, 4.0), K.IRON)                   # the coils' case
    m.box((-5.5, 2.0, 0.75), (3.5, 2.5, 4.25), K.IRON_D)                # its foot, the pole pieces under it
    for x in (-3.5, 1.5):
        m.tube("y", (x, 2.5), 6.5, 7.25, 0.5, K.BRASS, sides=6)
    m.tube("y", (-1.0, 1.25), 6.5, h + 1.0, TUBE, K.IRON_D, sides=6)    # the wire's tube, into the stone above
    gx, gy = GONG
    m.tube("z", (gx, gy), 0.75, 2.0, 1.0, K.IRON, sides=6)              # the post
    m.tube("z", (gx, gy), 2.0, 3.5, GONG_R, BRONZE, sides=12)           # the gong's rim
    m.tube("z", (gx, gy), 3.5, 4.25, GONG_R - 1.25, BRONZE, sides=12)   # its crown
    m.tube("z", (gx, gy), 4.25, 4.75, 1.0, K.BRASS, sides=6)            # the nut
    return m


def _hammer():
    """The hammer: the iron armature that the coils pull, the spring's foot over it, the arm and the
    ball. The anchor is where the spring is held (PIVOT, in the bell's frame); the ball hangs level
    with the gong's middle, GAP off its rim, and strikes along the model's -x."""
    m = M.Model(PREFIX + "hammer", anchor=PIVOT)
    px, py, pz = PIVOT
    m.box((px - 1.0, py - 0.5, pz - 1.0), (px + 1.0, py + 0.5, pz + 1.0), K.BRASS)      # the spring's foot
    m.box((px - 1.25, 2.25, pz - 1.0), (px - 0.25, py - 0.5, pz + 1.0), K.IRON)         # the armature, before the pole pieces
    m.tube("y", (px, pz), GONG[1] + BALL, py - 0.5, 0.35, K.IRON_D, sides=6)            # the arm
    m.ball((px, GONG[1], pz), BALL, K.BRASS, sides=8, layers=4)
    return m


def _push():
    """The push: a brass plate, a rose, the button; the wire's tube up from the plate and into the wall."""
    m = M.Model(PREFIX + "push")
    w, h = PUSH
    m.box((-w, -h, 0.0), (w, h, 0.5), K.BRASS_D)
    for y in (-h + 0.75, h - 0.75):
        K.rivet(m, (0.0, y, 0.5), out="z", mat=K.BRASS, proud=0.25)
    m.tube("z", (0.0, 0.0), 0.5, 1.25, 1.5, K.BRASS, sides=8)
    m.tube("z", (0.0, 0.0), 1.25, 1.75, 0.75, K.CREAM, sides=6)
    m.tube("y", (0.0, 0.5), h, h + 3.0, TUBE, K.IRON_D, sides=6)
    m.tube("z", (0.0, h + 3.0), 0.0, 0.5 + TUBE, TUBE, K.IRON_D, sides=6)
    return m


SPEC = {"gong": _bell, "hammer": _hammer, "push": _push}
SCALE = {PREFIX + name: 1.0 for name in SPEC}


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + name: K.settle(build()) for name, build in SPEC.items()}


def models():
    return dict(_models())


def strokes():
    """The ticks of LOOP on which the hammer sets off, one for every stroke of CODE."""
    out, t = [], 0
    for group in CODE:
        out += [t + i * BEAT for i in range(group)]
        t += (group - 1) * BEAT + REST
    return out


def bell(canvas, pos, facing="east", origin=(0, 0, 0), phase=0, **opts):
    """Hang a bell, the middle of its back at pos on a wall that looks `facing`, and have its hammer
    strike the call; opts as for K.put (brightness, view). Returns the number of display entities (2)."""
    yaw = K.FACING[facing]
    n = K.put(canvas, _models()[PREFIX + "gong"], pos, mount="wall", facing=facing, origin=origin, **opts)
    d = K.turn(yaw, tuple(v * PX for v in PIVOT))
    at = tuple(pos[i] + d[i] for i in range(3))
    n += K.put(canvas, _models()[PREFIX + "hammer"], at, mount="wall", facing=facing, origin=origin, **opts)
    moves = []
    for t in strokes():
        moves += [(t, GAP * PX, OUT), (t + OUT, 0.0, BACK_IN)]
    MK.slide(canvas, "-x", moves, LOOP, phase=phase)
    rim = K.turn(yaw, ((GONG[0] + GONG_R) * PX, GONG[1] * PX, 3.0 * PX))
    MK.sound(canvas, tuple(pos[i] + rim[i] for i in range(3)), NOTE["event"], LOOP,
             at=tuple(t + OUT for t in strokes()), volume=NOTE["volume"], pitch=NOTE["pitch"],
             reach=NOTE["reach"], origin=origin, phase=phase)
    return n


def push(canvas, pos, facing="east", origin=(0, 0, 0), **opts):
    """Fix a push, the middle of its plate's back at pos on a wall that looks `facing`. Returns 1."""
    return K.put(canvas, _models()[PREFIX + "push"], pos, mount="wall", facing=facing, origin=origin, **opts)


def seats():
    """Where the entrance's bell and its push hang: {"bell": dict(point, facing), "push": ...}, the
    middle of each back. Read off main/facade: the plane of the piers (emblem()), the doorway and
    the gates either side of it (doors()). Empty while the front in the tree has no such entrance."""
    try:
        from ..main import facade
    except ImportError:
        return {}
    doors, tablet = getattr(facade, "doors", None), getattr(facade, "emblem", None)
    if doors is None or tablet is None:
        return {}
    ways = [d for d in doors() if d["front"] == "east"]
    door = [d for d in ways if d["kind"] == "door"]
    gates = [d for d in ways if d["kind"] == "gate"]
    if not door or not gates:
        return {}
    face = tablet()["face_x"]
    door_pier = max(z for _, z in door[0]["cells"]) + 1             # the pier south of the doorway
    gate_pier = max(z for d in gates for _, z in d["cells"]) + 1    # the pier south of the south gate: the lamp's
    return {"bell": dict(point=(face, S.STRING - BELL_DOWN - BACK[1] * PX, gate_pier + 0.5), facing="east"),
            "push": dict(point=(face, S.PLINTH[0] + 1.0 + PUSH_UP, door_pier + 0.5), facing="east")}


def _hangs(canvas, seat, origin):
    """The stone behind a seat stands on the canvas and the cell before it is free (air or a light)."""
    out = K.turn(K.FACING[seat["facing"]], (0.0, 0.0, 1.0))
    wall, air = (tuple(math.floor(seat["point"][i] + origin[i] + side * out[i] + 1e-6) for i in range(3))
                 for side in (-0.5, 0.5))
    return canvas.has(*wall) and canvas.name(*air) in (None, "light")


def build(canvas, origin=(0, 0, 0)):
    """The entrance's bell and its push, each where its stone stands in the tree."""
    n, at = 0, seats()
    if "bell" in at and _hangs(canvas, at["bell"], origin):
        n += bell(canvas, at["bell"]["point"], at["bell"]["facing"], origin=origin)
    if "push" in at and _hangs(canvas, at["push"], origin):
        n += push(canvas, at["push"]["point"], at["push"]["facing"], origin=origin)
    return n
