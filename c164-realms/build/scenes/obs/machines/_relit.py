"""Faces of an item display that the engine lights in full, whichever way they look.

The engine shades every face of an item display by the axis of the model the face looks along most
nearly, carried through the display's matrix (26.3: BakedQuad.direction, and
PoseStack.Pose.transformNormal in VertexConsumer.putBakedQuad): in full under an axis that ends up
looking up, at 0.5 to 0.74 under one that looks sideways, at 0.4 under one that looks down. An
element's light emission and its shade direction do not change that for an item. So a lamp globe
seen from below, or the underside of anything that hangs, comes out at four tenths of its tone.

Which axis a face is filed under is the model's affair; where that axis ends up is the display's.
So a face can stand where it belongs and be lit as if it looked up: it is drawn in a model that is
turned or leant over, as the top of a thin box that has no other face, and the display's matrix
sets it back in its place. Plain vanilla: no shader, no resource the game does not read anyway.
Seen in the real client on the orrery's sun (s1, 11-16: the underside at full tone, no seam
between the faces, nothing parting while the displays turn).

    corner(azimuth)   a model stood on one corner: its three axes come out 35 degrees over the
                      level, a third of a turn apart. An upright face that looks within 30 degrees
                      of one of them is filed under it and lit at 0.96; two such frames, a sixth of
                      a turn apart, take every upright face there is. Plain turns: nothing is
                      stretched.
    leant()           a model leant over: a level plane of the scene is a tipped plane of the model,
                      unstretched (a texel stays a texel), and the model's y axis comes out 42
                      degrees over the level. A face that looks straight down is filed under it and
                      lit in full, and stays so while the display turns about the vertical. The
                      price is a matrix that is no turn.
    a face that looks up needs neither: a plain model lights it in full.

What they do not take is a face that slopes: one that looks neither up, nor level, nor straight
down. A round thing is drawn in steps, upright faces and ledges (Globe does that for a ball).

    from scenes.obs.machines import _relit as RL

    part = RL.Faces("props_lamp_shade_under", scale=1.0, frame=RL.frame((0, -1, 0)))
    part.face(centre, normal, across, w, h, mat, emit=15)     # in blocks from the anchor, as it stands in the scene
    canvas.add_entity(x, y, z, part.display(yaw))             # part.m is the model, for the package's models()

    globe = RL.Globe("props_lamp_globe", 0.25, [mat_low, ..., mat_top], emit=15)
    globe.models()                                            # {name: Model}
    globe.place(canvas, (x, y, z))                            # four entities on one spot

A model in a frame holds face() calls and nothing else. What does not glow, or looks up, or may be
dull, stays in a plain model on the same spot (Globe.plain is one: draw the fittings into it).
A display that turns about the vertical keeps its faces lit: say spins=True and brightness() gives
the least of a whole turn. Turn it with motion's MK.spin(canvas, (0, 1, 0), period): the world's
vertical, because a leant model has no axis of its own that stands upright.
"""
import math

import numpy as np

from artkit import models as M

LAMPS = tuple(np.array(v) / np.linalg.norm(v) for v in ((0.2, 1.0, -0.7), (-0.2, 1.0, 0.7)))   # the engine's two
FILED = np.array([(0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0)], dtype=float)   # its order
LIT = 0.95                               # the share of its tone a face drawn this way must keep
SURE = 0.1                               # by this much the axis a face is filed under must win
PX = 1.0 / 16.0
LAP = PX / 50.0                          # faces run this far past their edges, so no seam opens
SKIN = PX / 10.0                         # how thick the boxes behind them are


def corner(azimuth):
    """The frame of a model stood on a corner: its x axis comes out at `azimuth` (from east towards
    south), y and z a third of a turn on either side of it, all three 35.26 degrees over the level."""
    c, s = math.sqrt(2.0 / 3.0), math.sqrt(1.0 / 3.0)
    g = np.array([(c * math.cos(math.radians(azimuth + k)), s, c * math.sin(math.radians(azimuth + k)))
                  for k in (0.0, 120.0, 240.0)]).T
    return g if np.linalg.det(g) > 0.0 else g[:, [0, 2, 1]]


def leant(tip=40.0, rise=42.0):
    """The frame of a model leant over, for faces that look straight down. The plane of the model
    that is tipped `tip` degrees about x goes to the level plane of the scene as it is; the model's
    y axis, under which those faces are filed, is lit like a face that looks `rise` degrees over
    the level (in full from 38.2 degrees on, whichever way the display is turned about the
    vertical). Of all matrices that do this it is the least lopsided one."""
    b, e = math.radians(tip), math.radians(rise)
    sink = math.cos(e) / math.sin(b)
    lean = sink * math.tan(e) + 1.0 / math.tan(b)
    model = np.array([(1.0, 0.0, 0.0), (0.0, math.cos(b), math.sin(b)), (0.0, -math.sin(b), math.cos(b))])
    scene = np.array([(1.0, 0.0, 0.0), (0.0, -sink, lean), (0.0, 0.0, -1.0)])
    return scene.T @ model               # each row of `model` goes to the same row of `scene`


def filed(g, normal):
    """The axis of the model that the engine files a face under which looks along `normal` in the
    scene, the model being shown through g; and by how much that axis wins over the next."""
    v = g.T @ np.asarray(normal, dtype=float)
    along = FILED @ (v / np.linalg.norm(v))
    k = int(np.argmax(along))            # the first of equals, as in the engine
    return FILED[k], float(along[k] - np.sort(along)[-2])


def brightness(g, normal, spins=False):
    """The share of its tone the engine leaves a face that looks along `normal` in the scene, in a
    model shown through g (None: a plain model); for a display that spins about the vertical, the
    least of a whole turn."""
    g = np.eye(3) if g is None else np.asarray(g, dtype=float)
    axis, _sure = filed(g, normal)
    s = np.linalg.solve(g.T, axis)
    s = s / np.linalg.norm(s)
    least = 1.0
    for turn in (range(0, 360, 5) if spins else (0,)):
        a = math.radians(turn)
        t = np.array([s[0] * math.cos(a) - s[2] * math.sin(a), s[1], s[0] * math.sin(a) + s[2] * math.cos(a)])
        least = min(least, 0.4 + 0.6 * sum(max(0.0, float(t @ lamp)) for lamp in LAMPS))
    return least


def frame(normal, spins=False):
    """The frame for a face that looks along `normal` in the scene: None where a plain model lights
    it, leant() for one that looks straight down, corner() at its own azimuth for an upright one.
    Faces that share a frame share a model; corner(a) serves the upright faces within 30 degrees of
    a, a + 120 and a + 240."""
    n = np.asarray(normal, dtype=float)
    n = n / np.linalg.norm(n)
    if brightness(None, n, spins) >= LIT:
        return None
    if n[1] < -1.0 + 1e-9:
        return leant()
    if abs(n[1]) < 1e-9:
        return corner(math.degrees(math.atan2(n[2], n[0])))
    raise ValueError(f"no frame lights a face that looks along {tuple(normal)}: it slopes; draw it in steps")


def quat_of(r):
    """The quaternion (x, y, z, w) of a turn given as a matrix."""
    t = r[0, 0] + r[1, 1] + r[2, 2]
    if t > 0.0:
        s = 2.0 * math.sqrt(t + 1.0)
        q = ((r[2, 1] - r[1, 2]) / s, (r[0, 2] - r[2, 0]) / s, (r[1, 0] - r[0, 1]) / s, s / 4.0)
    elif r[0, 0] > r[1, 1] and r[0, 0] > r[2, 2]:
        s = 2.0 * math.sqrt(1.0 + r[0, 0] - r[1, 1] - r[2, 2])
        q = (s / 4.0, (r[0, 1] + r[1, 0]) / s, (r[0, 2] + r[2, 0]) / s, (r[2, 1] - r[1, 2]) / s)
    elif r[1, 1] > r[2, 2]:
        s = 2.0 * math.sqrt(1.0 + r[1, 1] - r[0, 0] - r[2, 2])
        q = ((r[0, 1] + r[1, 0]) / s, s / 4.0, (r[1, 2] + r[2, 1]) / s, (r[0, 2] - r[2, 0]) / s)
    else:
        s = 2.0 * math.sqrt(1.0 + r[2, 2] - r[0, 0] - r[1, 1])
        q = ((r[0, 2] + r[2, 0]) / s, (r[1, 2] + r[2, 1]) / s, s / 4.0, (r[1, 0] - r[0, 1]) / s)
    return tuple(float(v) for v in q)


def matrix_of(q):
    """The turn of a quaternion (x, y, z, w) as a matrix."""
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


HALF_TURN = np.diag([-1.0, 1.0, -1.0])   # the item renderer shows a model turned half a turn about y


def display(model, g, scale=1.0, yaw=0.0):
    """The item display that shows `model` through the frame g at `scale`, its anchor on the entity
    and the whole turned by `yaw`: what artkit.models.display gives for a plain turn, for any
    matrix. The matrix is taken apart into a turn, a scale along three axes and a second turn, as
    the engine takes one apart; a plain turn stays one turn and one scale."""
    nbt = M.display(model, yaw=yaw, scale=scale)
    if g is None:
        return nbt
    a = np.asarray(g, dtype=float) * (scale / 16.0)                 # the model's units to blocks
    u, s, vt = np.linalg.svd(HALF_TURN @ (a * 16.0) @ HALF_TURN)
    if s[0] - s[2] < 1e-9:
        u, vt = u @ vt, np.eye(3)
    elif np.linalg.det(u) < 0.0:
        u[:, 2], vt[2, :] = -u[:, 2], -vt[2, :]
    off = np.array(model.anchor) + np.array(model.shift()) - 8.0
    t = HALF_TURN @ (a @ off)
    tr = nbt["transformation"]
    kind = type(tr["scale"][0])
    tr["left_rotation"] = [kind(v) for v in quat_of(u)]
    tr["right_rotation"] = [kind(v) for v in quat_of(vt)]
    tr["scale"] = [kind(v) for v in s]
    tr["translation"] = [kind(-v) for v in t]
    return nbt


def shown(nbt):
    """A display's NBT read back the way the engine reads it (DisplayRenderer and the item renderer;
    artkit.gamescene does the same): the matrix that takes the coordinates of the exported model to
    blocks in the scene, and where the exported model's origin lands, from the entity."""
    tr = nbt["transformation"]
    yaw = math.radians(float(nbt["Rotation"][0]))
    turn = np.array([[math.cos(yaw), 0.0, -math.sin(yaw)], [0.0, 1.0, 0.0], [math.sin(yaw), 0.0, math.cos(yaw)]])
    a = turn @ matrix_of(tr["left_rotation"]) @ np.diag([float(v) for v in tr["scale"]]) \
        @ matrix_of(tr["right_rotation"]) @ HALF_TURN / 16.0
    return a, turn @ np.array([float(v) for v in tr["translation"]]) - a @ np.full(3, 8.0)


class Faces:
    """A model and the frame it is shown through. artkit's unit is 1/16 block of a model shown at
    scale 1; a model shown at scale s is drawn s times smaller with s texels to the unit, 16 px to
    the block. With a frame the model is made of face() calls alone; `lit` keeps, for each, the
    share of its tone the face is left with and by how much its axis wins."""

    def __init__(self, name, scale=1.0, frame=None, spins=False):
        self.scale = float(scale)
        self.u = 16.0 / self.scale
        self.m = M.Model(name, px=self.scale)
        self.g = None if frame is None else np.asarray(frame, dtype=float)
        self.spins = spins
        self.lit = []

    def display(self, yaw=0.0):
        return display(self.m, self.g, self.scale, yaw)

    def face(self, centre, normal, across, w, h, mat, lap=LAP, **kw):
        """One face and nothing behind it: a rectangle `w` along `across` and `h` the other way,
        its middle at `centre`, looking along `normal`; all as it is to stand in the scene, in
        blocks from the anchor. In a frame it is drawn where the frame's display takes it from.
        The other keywords go to Model.box (emit, seed, grain)."""
        g = np.eye(3) if self.g is None else self.g
        n = np.asarray(normal, dtype=float)
        ax = np.asarray(across, dtype=float)
        n, ax = n / np.linalg.norm(n), ax / np.linalg.norm(ax)
        au, av = np.linalg.solve(g, ax), np.linalg.solve(g, np.cross(n, ax))
        lu, lv = float(np.linalg.norm(au)), float(np.linalg.norm(av))
        if abs(float(au @ av)) > 1e-9 * lu * lv:
            raise ValueError(f"{self.m.name}: this frame skews a face that looks along {tuple(normal)}")
        y = g.T @ n
        y = y / np.linalg.norm(y)
        x = au / lu
        r = np.column_stack([x, y, np.cross(x, y)])                 # the box's own axes in the model
        if abs(r[2, 0]) > 1.0 - 1e-9:
            turn = (math.atan2(-r[1, 2], r[1, 1]), -math.copysign(math.pi / 2.0, r[2, 0]), 0.0)
        else:
            turn = (math.atan2(r[2, 1], r[2, 2]), -math.asin(r[2, 0]), math.atan2(r[1, 0], r[0, 0]))
        c = np.linalg.solve(g, np.asarray(centre, dtype=float)) * self.u
        half = np.array([(w / 2.0 + lap) * lu, 0.0, (h / 2.0 + lap) * lv]) * self.u
        self.m.box(tuple(c - half - (0.0, SKIN * self.u, 0.0)), tuple(c + half), mat,
                   rot=("xyz", tuple(math.degrees(v) for v in turn), tuple(c)), skip="nsewd", **kw)
        self.lit.append((brightness(g, n, self.spins), filed(g, n)[1]))

    def off(self, yaw=0.0):
        """How far, in blocks, the display is from what it is meant to show: its matrix, read back
        as the engine reads it, against the frame (over a block of the model), and where the anchor
        lands against the entity. Nothing, if display() is right."""
        a, at = shown(self.display(yaw))
        t = math.radians(yaw)
        turn = np.array([[math.cos(t), 0.0, -math.sin(t)], [0.0, 1.0, 0.0], [math.sin(t), 0.0, math.cos(t)]])
        want = turn @ (np.eye(3) if self.g is None else self.g) * (self.scale / 16.0)
        anchor = at + a @ (np.array(self.m.anchor) + np.array(self.m.shift()))
        return max(float(np.abs(a - want).max()) * 16.0 / self.scale, float(np.abs(anchor).max()))


def checked(parts, yaws=(0.0, 77.0)):
    """Do the faces these Faces drew with face() keep their tone, are they filed surely, do the
    displays put the models where they belong? (ok, a line to print)."""
    parts = list({p.m.name: p for p in parts}.values())
    lit = [v for p in parts for v in p.lit]
    if not lit:
        return True, "no face drawn with face()"
    dull, sure = min(v[0] for v in lit), min(v[1] for v in lit)
    off = max(p.off(yaw) for p in parts for yaw in yaws)
    line = (f"faces lit as if they looked up: {len(lit)} in {sum(1 for p in parts if p.lit)} models; the dullest "
            f"keeps {dull:.3f} of its tone (limit {LIT}), the axis a face is filed under wins by {sure:.2f} at "
            f"least (limit {SURE}); the displays are off by {off:.1e} blocks at most")
    return dull >= LIT and sure >= SURE and off < 1e-6, line


class Globe:
    """A ball that shows its tones in full from every side and from below: a lamp globe. `tones`
    are the materials of its layers from the lowest up (flat tones; the light and dark of the ball
    is what is painted, the engine adds none), each layer `sides` upright faces round and a ledge
    to the next. Four models on one spot: `plain` with the ledges that look up (and whatever
    fittings the caller draws into it), two stood on a corner for the upright faces, one leant
    over for the ledges that look down. The anchor is the middle of the ball. The other keywords
    go to every face (emit=15 for glass that glows). cls: the Faces to make the four of."""

    def __init__(self, name, radius, tones, sides=12, scale=1.0, spins=False, cls=None, **look):
        make = cls or Faces
        self.plain = make(name, scale, spins=spins)
        self.sides = [make(f"{name}_side{i}", scale, frame=corner(15.0 + 60.0 * i), spins=spins) for i in (0, 1)]
        self.under = make(f"{name}_under", scale, frame=leant(), spins=spins)
        look.setdefault("seed", 1)
        look.setdefault("grain", "x")
        r, n = radius, len(tones)
        hw = math.tan(math.pi / sides)
        for i, mat in enumerate(tones):
            t0, t1 = -1.0 + 2.0 * i / n, -1.0 + 2.0 * (i + 1) / n
            rr = r * math.sqrt(1.0 - ((t0 + t1) / 2.0) ** 2)
            for k in range(sides):
                a = math.radians(360.0 * k / sides)
                out = (math.cos(a), 0.0, math.sin(a))
                best = max(self.sides, key=lambda f: (brightness(f.g, out, spins), filed(f.g, out)[1]))
                best.face((rr * out[0], r * (t0 + t1) / 2.0, rr * out[2]), out, (-out[2], 0.0, out[0]),
                          2.0 * rr * hw, r * (t1 - t0), mat, **look)
            for k in range(sides // 2):                 # the ledge to the next layer: strips that cross
                a = math.radians(360.0 * k / sides)
                across = (math.cos(a), 0.0, math.sin(a))
                if t0 + t1 < 0.0:
                    self.under.face((0.0, r * t0, 0.0), (0.0, -1.0, 0.0), across, 2.0 * rr * hw, 2.0 * rr, mat, **look)
                else:
                    self.plain.face((0.0, r * t1, 0.0), (0.0, 1.0, 0.0), across, 2.0 * rr * hw, 2.0 * rr, mat, **look)

    def parts(self):
        return [self.plain] + self.sides + [self.under]

    def models(self):
        return {p.m.name: p.m for p in self.parts()}

    def place(self, canvas, pos, yaw=0.0):
        """Put the four displays on one spot; returns their number."""
        for p in self.parts():
            canvas.add_entity(pos[0], pos[1], pos[2], p.display(yaw))
        return len(self.parts())


def _report():
    """python -m scenes.obs.machines._relit: a globe and a face of each kind, checked; and a globe
    twice the size shown at scale 2, as a lamp that is placed at any yaw (spins: the least of a
    whole turn)."""
    from ..props import _kit as K
    tones = [K.flat("glow", i) for i in (2, 3, 4, 4, 3, 2, 1, 0)]
    globe = Globe("mach_relit_try", 0.25, tones, emit=15)
    one = Faces("mach_relit_try_down", frame=frame((0, -1, 0)), spins=True)
    one.face((0.3, -0.2, 0.1), (0, -1, 0), (1, 0, 0), 0.25, 0.125, K.flat("glow", 3))
    side = Faces("mach_relit_try_side", frame=frame((1, 0, 1)))
    side.face((0.3, 0.0, 0.3), (1, 0, 1), (0, 1, 0), 0.25, 0.125, K.flat("glow", 3))
    ok, line = checked(globe.parts() + [one, side])
    print(line)
    big = Globe("mach_relit_try_big", 0.5, tones, scale=2.0, spins=True, emit=15)
    fits, line = checked(big.parts(), yaws=(0.0, 33.0, 90.0, 211.0))
    print("at scale 2, turned any way:", line)
    ok = ok and fits
    try:
        frame((1, -1, 0))
    except ValueError as e:
        print("a face that slopes:", e)
    else:
        ok = False
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if _report() else 1)
