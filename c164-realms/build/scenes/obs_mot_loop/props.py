"""The sample parts of the beat board (card motion/loop). They are this scene's own: no work
package places them and none of them is meant for the map. Each is drawn the way a maker would
draw a part that moves: one model for what moves, its anchor on the axis, +z towards whoever
looks at it.

A model's box is what artkit.models.Model.bounds() makes of it: the boxes as they are before
they are turned into place. Where the middle of that box lies off the axis, the part has to turn
in small steps (plan/parts/motion.md section 2); the notes say where it lies for each part.

The parts of the crank are drawn at two pixels to the unit and placed at scale 2: a rod of four
blocks would not fit a model otherwise. Where two parts meet, a quarter of a unit is left between
their faces, so that no two faces lie in one plane.
"""
import functools

from artkit import models as M

from scenes.obs.common import palette as P

PREFIX = "mot_"
IRON = P.mat("iron")
IRON_D = P.mat("iron_dark")
IRON_FLAT = P.mat("iron_flat")
BRASS = P.mat("brass")
BRASS_D = P.mat("brass_dark")
BRASS_FLAT = P.mat("brass_flat")
GLASS_LIT = P.mat("glow", kind="flat", base=3, bevel=0)
GLASS_DARK = P.mat("brass", kind="flat", base=0, bevel=0)


def _wheel():
    """A spoked wheel about z, 2.4 blocks across. The anchor is its centre and the middle of its
    box, so it turns a quarter of a turn in one step. One spoke is brass, to see it go round."""
    m = M.Model(PREFIX + "wheel")
    m.ring("z", (0.0, 0.0, 0.0), 18.0, 3.0, 3.0, IRON, sides=16)
    m.tube("z", (0.0, 0.0), -2.0, 2.0, 3.0, IRON_D)
    for k in range(6):
        m.box((-1.0, 3.0, -1.0), (1.0, 16.5, 1.0), BRASS if k == 0 else IRON,
              rot=("z", 60.0 * k, (0.0, 0.0, 0.0)) if k else None, grain="y")
    return m


def _arm():
    """An arm that turns about one end, as an orrery's does: 3.5 blocks long. The anchor is the
    eye at its end; the middle of its box lies 1.6 blocks from there."""
    m = M.Model(PREFIX + "arm", px=2.0)
    m.ring("z", (0.0, 0.0, 0.0), 2.0, 1.0, 1.0, IRON_D, sides=8)
    m.box((2.5, -0.75, -0.5), (26.0, 0.75, 0.5), IRON, grain="x")
    m.tube("z", (27.0, 0.0), -0.75, 0.75, 1.5, BRASS)
    return m


def _pin():
    """A pin in the wall for the eye of an arm, a pixel of air round it. It stands still, so where
    the arm leaves its arc the eye is seen to move on the pin. The anchor is on its axis, a
    quarter of a block off the wall."""
    m = M.Model(PREFIX + "pin")
    m.tube("z", (0.0, 0.0), -3.75, 2.0, 2.0, BRASS)
    return m


def _pendulum():
    """A pendulum two blocks long. The anchor is the pivot at its top; the middle of its box lies
    a block below."""
    m = M.Model(PREFIX + "pendulum")
    m.tube("z", (0.0, 0.0), -1.0, 1.0, 1.5, BRASS_D)
    m.box((-0.5, -25.0, -0.5), (0.5, -1.0, 0.5), IRON, grain="y")
    m.tube("z", (0.0, -28.0), -1.0, 1.0, 4.0, BRASS, sides=12)
    return m


def _disc():
    """A crank disc about z, 2.5 blocks across. The crank pin stands a block from the centre on
    +x; the stud opposite it keeps the middle of the box on the axis."""
    m = M.Model(PREFIX + "disc", px=2.0)
    m.tube("z", (0.0, 0.0), -0.5, 0.5, 10.0, IRON, sides=16)
    m.tube("z", (0.0, 0.0), 0.5, 1.0, 1.5, IRON_D)
    m.tube("z", (8.0, 0.0), 0.5, 2.75, 1.0, BRASS)
    m.tube("z", (-8.0, 0.0), 0.5, 1.0, 1.0, IRON_D)
    return m


def _rod():
    """A connecting rod, four blocks from pin to pin. The anchor is the crosshead pin; the rod
    lies along -x to the crank pin. The middle of its box lies two blocks from the anchor."""
    m = M.Model(PREFIX + "rod", px=2.0)
    m.box((-30.5, -0.75, -0.5), (-1.5, 0.75, 0.5), IRON, grain="x")
    for x in (0.0, -32.0):
        m.ring("z", (x, 0.0, 0.0), 1.75, 1.0, 1.0, BRASS_D, sides=8)
    return m


def _crosshead():
    """A crosshead and its piston rod. The anchor is the crosshead pin, in the plane of the
    connecting rod; the block rides behind that plane and the piston rod runs on along +x into
    the cylinder."""
    m = M.Model(PREFIX + "crosshead", px=2.0)
    m.box((-2.0, -1.75, -2.25), (2.0, 1.75, -0.75), BRASS)
    m.tube("z", (0.0, 0.0), -1.5, 0.75, 1.0, BRASS_D)
    m.box((2.0, -0.5, -2.0), (30.0, 0.5, -1.0), IRON, grain="x")
    return m


def _guide():
    """The two slide bars the crosshead runs between, long enough for a stroke of two blocks.
    They stand still; the anchor is where the crosshead pin rests."""
    m = M.Model(PREFIX + "guide", px=2.0)
    for y in (-2.5, 2.0):
        m.box((-18.5, y, -2.25), (2.5, y + 0.5, -0.75), IRON_D, grain="x")
    return m


def _rail():
    """The bar a slider runs on, with a stop at either end. It stands still; the anchor is where
    the slider rests."""
    m = M.Model(PREFIX + "rail")
    m.box((-5.0, -1.0, -1.0), (29.0, 1.0, 1.0), IRON_D, grain="x")
    for x in (-6.0, 29.0):
        m.box((x, -2.5, -1.5), (x + 1.0, 2.5, 1.5), IRON)
    return m


def _slider():
    m = M.Model(PREFIX + "slider")
    m.box((-3.0, -3.0, -3.0), (3.0, 3.0, 3.0), BRASS)
    return m


def _lamp(lit):
    """A round lamp on a wall plate, lit or dark: the two models a blinking part changes between.
    The anchor is on the wall."""
    m = M.Model(PREFIX + ("lamp" if lit else "lamp_dark"))
    m.tube("z", (0.0, 0.0), 0.0, 1.0, 4.0, IRON_D)
    m.tube("z", (0.0, 0.0), 1.0, 2.0, 3.0, BRASS_D)
    glass = GLASS_LIT if lit else GLASS_DARK
    m.ball((0.0, 0.0, 4.5), 3.0, glass, sides=8, layers=4, faces={"n": glass, "s": glass, "u": glass, "d": glass},
           emit=15 if lit else 0, shade=not lit)
    return m


def _bar():
    """A bar that runs 48 units along +z from its anchor, to be drawn out between two points
    (artkit.models.between). Flat tones, which a stretch does not smear; the far end is a brass
    block, on which a skew would show."""
    m = M.Model(PREFIX + "bar")
    m.box((-1.0, -1.0, 0.0), (1.0, 1.0, 42.0), IRON_FLAT, grain="z")
    m.box((-1.5, -1.5, 42.0), (1.5, 1.5, 48.0), BRASS_FLAT, grain="z")
    return m


@functools.lru_cache(maxsize=None)
def _models():
    built = (_wheel(), _arm(), _pin(), _pendulum(), _disc(), _rod(), _crosshead(), _guide(), _rail(), _slider(),
             _lamp(True), _lamp(False), _bar())
    return {m.name: m for m in built}


def model(name):
    return _models()[PREFIX + name]


def build_models():
    return dict(_models())
