"""props/electrics -- the exposed electrics of the observatory (plan ART-PLAN 2, 7.3; part A6-props
2.4; card plan/packages/props/electrics-signs.md).

One motif for the family (A6-props 2.4): porcelain-white insulators + a cast-iron bracket or box +
brass terminals and blades, with an enamel-blue plate for a touch. They are held together by the
insulator's stacked skirts, the iron carcase and the brass contacts. Examples: a cross-arm is an
iron bar with a row of insulators; a knife switch is a brass blade on a slate base; a junction box
is an iron box with the conduit entering it.

Everything is placed through _kit (mounting, materials, rivets). The family's own helpers -- the
insulator skirt, the cable run that never dead-ends -- live here (not in _kit.py, which is shared).

Eight pieces, all 16 texels to the block (px = scale):
    insulator     a pin insulator on a wall bracket, a saddle on top for the line.
    crossarm      an iron cross-arm carrying a row of insulators (2 x 0.5).
    junction_box  a cast-iron junction box with a bolted lid and a conduit entry (1 x 1).
    knife_switch  a brass knife switch on a slate base (1 x 1); the blade is a separate part (A8).
    fuse_box      a small iron box with a row of porcelain fuse carriers (1 x 1).
    bell          a brass gong bell with a striker (diameter 1).
    wall_phone    a dark-wood wall telephone, brass bells and a handset (1 x 1.5).
    telegraph_key a brass telegraph key on a wood base (0.5 x 0.5), the lever a separate part (A8).

For the other lines, the line that builds the wall or the room places the pieces and runs the cable:

    from scenes.obs.props import electrics as E
    n += E.place(canvas, "junction_box", (x, y, z), facing="east", origin=origin)
    n += E.run(canvas, (x, y, z), (x, y, z2), facing="east", origin=origin)   # insulators + cable

The cable run has a start and an end (A6-props 2.4, plan 2: no dead-ends): it is strung between its
two endpoints -- junction boxes, a cross-arm, or the point where it turns into the wall.
"""
import functools
import math

from artkit import models as M

from ..common import blocks as B
from ..common import palette as P
from ..common import skeleton as S
from . import _kit as K

PREFIX = "prop_elec_"
DRESS = False                   # build() dresses the master scene only when on (A0 #211)

IRON, IRON_D = K.IRON, K.IRON_D
BRASS, BRASS_D = K.BRASS, K.BRASS_D
PORC = P.mat("porcelain")
PORC_D = P.mat("porcelain", base=1)
SLATE = P.mat("slate")
WOOD = P.mat("dark_wood")
ENAMEL = K.ENAMEL
CABLE = K.flat("old_copper", 1)
RIVET = K.RIVET

OUT = 0.42                      # how far a wall insulator's saddle stands off the wall, in blocks
PITCH = 4.0                     # the bays' module: one insulator every this many blocks on a run


# ---- the family's own helpers --------------------------------------------------------------------
def _skirts(m, cx, cz, z0, z1, r0, r1, ribs=2, mat=PORC):
    """A porcelain pin-insulator body stacked along +z from z0 to z1, widening to r0 at the foot and
    tapering to r1 at the head, in `ribs` bells (each bell a flare)."""
    step = (z1 - z0) / ribs
    for i in range(ribs):
        a0 = z0 + step * i
        rr = r0 + (r1 - r0) * i / ribs
        m.taper("z", (cx, cz), a0, a0 + step * 0.85, rr, rr * 0.62, mat, steps=2, sides=8)
        m.tube("z", (cx, cz), a0 + step * 0.85, a0 + step, rr * 0.9, mat, sides=8)


def _insulator():
    """A pin insulator on a wall bracket: an iron bracket foot, a porcelain body standing off the
    wall, and an iron saddle on top for the line. Anchor: on the wall, the bracket foot."""
    m = M.Model(PREFIX + "insulator", px=1.0)
    cx = 4.0
    m.box((cx - 1.5, 1.0, 0.0), (cx + 1.5, 6.0, 1.0), IRON, grain="y")      # bracket plate
    m.tube("z", (cx, 3.5), 1.0, 2.0, 1.0, IRON)                             # pin stub
    _skirts(m, cx, 3.5, 2.0, 6.5, 2.6, 1.3)                                 # porcelain bells
    m.tube("z", (cx, 3.5), 6.5, 7.0, 1.5, PORC, sides=8)                    # head
    m.box((cx - 2.0, 3.0, 7.0), (cx + 2.0, 4.0, 7.8), IRON)                 # the line saddle (along x)
    return m


def _crossarm():
    """An iron cross-arm with a row of three insulators on top (2 x 0.5). Anchor: on the wall, the
    arm's foot centre; the arm runs along x."""
    m = M.Model(PREFIX + "crossarm", px=1.0)
    m.box((0.0, 2.0, 0.0), (32.0, 5.0, 3.0), IRON, grain="x")               # the arm
    m.beam((4.0, 2.0, 1.5), (4.0, -4.0, 1.5), 2.0, 2.0, IRON_D)             # a brace down to the wall
    m.beam((28.0, 2.0, 1.5), (28.0, -4.0, 1.5), 2.0, 2.0, IRON_D)
    for cx in (6.0, 16.0, 26.0):
        m.tube("y", (cx, 1.5), 5.0, 6.0, 1.0, IRON)                         # pin
        _skirts_y(m, cx, 1.5, 6.0, 10.0, 2.4, 1.2)
        m.tube("y", (cx, 1.5), 10.0, 10.5, 1.4, PORC, sides=8)
    return m


def _skirts_y(m, cx, cz, y0, y1, r0, r1, ribs=2, mat=PORC):
    """Insulator bells stacked up the +y axis (for a cross-arm, where the pin stands up)."""
    step = (y1 - y0) / ribs
    for i in range(ribs):
        a0 = y0 + step * i
        rr = r0 + (r1 - r0) * i / ribs
        m.taper("y", (cx, cz), a0, a0 + step * 0.85, rr, rr * 0.62, mat, steps=2, sides=8)
        m.tube("y", (cx, cz), a0 + step * 0.85, a0 + step, rr * 0.9, mat, sides=8)


def _junction_box():
    """A cast-iron junction box: a bolted lid, a brass gland and a conduit that turns down into the
    wall so the run never just stops. Anchor: on the wall, the box's foot centre."""
    m = M.Model(PREFIX + "junction_box", px=1.0)
    m.box((3.0, 3.0, 0.0), (13.0, 13.0, 4.0), IRON, grain="y")              # body
    m.box((3.5, 3.5, 4.0), (12.5, 12.5, 5.0), IRON_D, grain="y")           # lid, standing a little proud
    for x in (4.5, 11.5):
        for y in (4.5, 11.5):
            K.rivet(m, (x, y, 5.0))                                         # lid bolts
    m.tube("y", (8.0, 2.5), -3.0, 3.0, 1.0, IRON_D)                         # conduit down into the wall
    K.wall_entry(m, 8.0, -3.0)
    m.tube("y", (8.0, 2.5), 13.0, 16.0, 1.0, IRON_D)                        # and up out of the lid
    K.wall_entry(m, 8.0, 16.0)
    m.tube("z", (8.0, 8.0), 5.0, 6.0, 1.5, BRASS)                           # a brass gland on the face
    return m


def _knife_switch():
    """A knife switch on a slate base: two brass jaws, the blade between them and a wood handle. The
    blade is a separate part so A8 can throw it. Anchor: on the wall, the base's foot centre."""
    m = M.Model(PREFIX + "knife_switch", px=1.0)
    m.box((3.0, 2.0, 0.0), (13.0, 14.0, 1.5), SLATE, grain="y")            # slate base
    for y in (4.0, 11.0):
        m.box((4.0, y - 0.5, 1.5), (6.0, y + 0.5, 3.0), BRASS)             # lower / upper jaw block
        m.box((10.0, y - 0.5, 1.5), (12.0, y + 0.5, 3.0), BRASS)
    m.box((5.0, 4.0, 2.4), (6.5, 12.0, 3.0), BRASS_D, grain="y")            # the blade (A8's part)
    m.box((6.0, 11.0, 2.4), (11.0, 12.5, 2.9), BRASS_D, grain="x")          # the blade's cross-bar
    m.tube("z", (11.0, 12.0), 2.9, 4.5, 1.0, WOOD)                          # the handle knob
    return m


def _fuse_box():
    """A small iron box with a row of three porcelain fuse carriers behind a half-open lid. Anchor:
    on the wall, the box's foot centre."""
    m = M.Model(PREFIX + "fuse_box", px=1.0)
    m.box((3.0, 3.0, 0.0), (13.0, 13.0, 2.5), IRON, grain="y")             # body
    m.box((3.0, 2.0, 2.5), (13.0, 13.0, 3.0), IRON_D, grain="x")           # a back board
    for cx in (5.0, 8.0, 11.0):
        m.tube("z", (cx, 7.0), 3.0, 5.0, 1.1, PORC, sides=8)              # porcelain carrier
        m.tube("z", (cx, 7.0), 5.0, 5.5, 0.6, BRASS, sides=8)             # brass cap
    m.box((2.5, 12.0, 3.0), (13.5, 13.0, 6.5), IRON_D, grain="x",
          rot=("x", -70.0, (8.0, 12.5, 3.0)))                              # the lid, hinged open
    return m


def _bell():
    """A brass gong bell with its striker and a small iron coil box (diameter 1). Anchor: on the
    wall, the back-plate centre."""
    m = M.Model(PREFIX + "bell", px=1.0)
    m.box((5.0, 2.0, 0.0), (11.0, 8.0, 1.5), IRON, grain="y")              # coil box on the wall
    m.tube("z", (8.0, 10.0), 0.0, 1.5, 1.0, IRON_D)                         # the gong's stem up
    with m.turned(("x", 90), about=(8.0, 11.0, 1.5)):                       # the dome looks down
        m.ball((8.0, 11.0, 1.5), 4.0, BRASS, sides=12, part=(0.0, 1.0), squash=0.8)
    m.tube("z", (8.0, 11.0), 1.5, 2.0, 0.6, BRASS_D)                        # the hub
    m.rod((7.0, 6.0, 2.5), (6.0, 9.5, 4.0), 0.6, IRON_D)                    # the striker arm
    m.tube("z", (6.0, 9.8), 4.0, 4.8, 1.0, IRON)                           # the striker head
    return m


def _wall_phone():
    """A dark-wood wall telephone: the box, two brass bell domes, a mouthpiece, a crank and a handset
    hung on a hook (1 x 1.5). Anchor: on the wall, the box's foot centre."""
    m = M.Model(PREFIX + "wall_phone", px=1.0)
    m.box((3.0, 2.0, 0.0), (13.0, 22.0, 4.0), WOOD, grain="y")             # the box
    m.box((3.5, 2.5, 4.0), (12.5, 21.5, 4.6), WOOD, grain="y")             # a raised front panel
    for cx in (6.0, 10.0):
        with m.turned(("x", 90), about=(cx, 20.0, 4.0)):
            m.ball((cx, 20.0, 4.0), 2.3, BRASS, sides=10, part=(0.0, 1.0), squash=0.8)  # bell dome
    m.tube("z", (8.0, 13.0), 4.0, 7.0, 2.0, BRASS, sides=10)               # the mouthpiece
    m.tube("z", (8.0, 13.0), 7.0, 7.5, 2.4, BRASS_D, sides=10)
    m.tube("x", (6.0, 5.0), 12.5, 14.5, 1.0, BRASS)                        # the crank spindle
    m.rod((14.5, 6.0, 5.0), (15.5, 4.0, 5.0), 0.7, BRASS_D)                # the crank handle
    m.rod((1.5, 6.0, 4.0), (1.5, 11.0, 4.0), 1.2, IRON_D)                  # the handset, on its hook
    m.tube("x", (6.0, 4.0), 0.5, 2.5, 1.4, WOOD)                           # the ear-piece
    return m


def _telegraph_key():
    """A telegraph key on a wood base: a brass lever on a trunnion, a knob, the contacts and the
    terminals. The lever is a separate part (A8). Anchor: the base's foot centre; it stands on a
    table."""
    m = M.Model(PREFIX + "telegraph_key", px=1.0)
    m.box((0.5, 0.0, 0.5), (7.5, 1.5, 7.5), WOOD, grain="x")               # base
    m.box((3.0, 1.5, 3.0), (5.0, 3.5, 5.0), BRASS_D)                        # trunnion
    m.box((1.0, 3.0, 3.7), (6.5, 4.0, 4.3), BRASS, grain="x")               # the lever (A8's part)
    m.tube("y", (2.0, 4.0), 4.0, 5.2, 1.3, BRASS, sides=10)                # the knob
    for cx in (1.5, 6.5):
        m.tube("y", (cx, 4.0), 1.5, 2.6, 0.6, BRASS)                        # terminal posts
    return m


def _cable():
    """The line: a thin wire running along +z from the anchor, 48 units long, one flat tone so that
    stretching it between two insulators smears nothing (as lamps._wire)."""
    m = M.Model(PREFIX + "cable", px=1.0)
    m.box((-0.5, -0.5, 0.0), (0.5, 0.5, 48.0), CABLE, grain="z")
    return m


# ---- models, placing and the cable run -----------------------------------------------------------
SPEC = {
    "insulator": dict(build=_insulator, mount="wall", scale=1.0),
    "crossarm": dict(build=_crossarm, mount="wall", scale=1.0),
    "junction_box": dict(build=_junction_box, mount="wall", scale=1.0),
    "knife_switch": dict(build=_knife_switch, mount="wall", scale=1.0),
    "fuse_box": dict(build=_fuse_box, mount="wall", scale=1.0),
    "bell": dict(build=_bell, mount="wall", scale=1.0),
    "wall_phone": dict(build=_wall_phone, mount="wall", scale=1.0),
    "telegraph_key": dict(build=_telegraph_key, mount="floor", scale=1.0),
    "cable": dict(build=_cable, mount="wall", scale=1.0),
}
SCALE = {PREFIX + name: spec["scale"] for name, spec in SPEC.items()}


@functools.lru_cache(maxsize=None)
def _models():
    return {PREFIX + name: spec["build"]() for name, spec in SPEC.items()}


def models():
    return dict(_models())


def place(canvas, kind, pos, facing="south", origin=(0, 0, 0), yaw=None, **opts):
    """Place one fitting. Returns the entity count (1)."""
    spec = SPEC[kind]
    yaw = K.FACING[facing] if yaw is None else yaw
    return K.put(canvas, _models()[PREFIX + kind], pos, mount=spec["mount"], yaw=yaw,
                 scale=spec["scale"], origin=origin, **opts)


def run(canvas, a, b, facing="east", origin=(0, 0, 0), pitch=PITCH, ends=True):
    """A cable run along a wall from a to b (points on the wall face, scene coordinates): an insulator
    every `pitch` blocks and the line strung from one to the next, standing OUT off the wall. With
    ends=True a junction box closes each end, so the line has a start and an end and never dead-ends
    (A6-props 2.4, plan 2). Returns the entity count.

    a and b lie in the same wall face; the run goes straight between them.
    """
    yaw = K.FACING[facing]
    out = K.turn(yaw, (0.0, 0.0, OUT))                  # the saddle stands this far off the wall
    saddle_y = 0.78                                     # the line sits this high above the anchor
    length = math.dist(a, b)
    count = max(2, int(round(length / pitch)) + 1)
    pts = [tuple(a[k] + (b[k] - a[k]) * i / (count - 1) for k in range(3)) for i in range(count)]
    n = 0
    for p in pts:
        n += place(canvas, "insulator", p, facing=facing, origin=origin)
    saddles = [tuple(p[k] + out[k] + origin[k] + (saddle_y if k == 1 else 0.0) for k in range(3))
               for p in pts]
    built = _models()
    for p0, p1 in zip(saddles, saddles[1:]):
        canvas.add_entity(p0[0], p0[1], p0[2], M.between(built[PREFIX + "cable"], p0, p1))
        n += 1
    if ends:
        for p in (a, b):
            n += place(canvas, "junction_box", (p[0], p[1] - 0.5, p[2]), facing=facing, origin=origin)
    return n


def build(canvas, origin=(0, 0, 0)):
    """Nothing in the master scene until DRESS is on and A3's fronts are there to carry the run
    (A0 #211). Off, so the master scene always generates."""
    if not DRESS:
        return 0
    return 0
