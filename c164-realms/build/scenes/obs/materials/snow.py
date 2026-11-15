"""Work package materials/snow (plan/packages/materials/snow.md): the snow on the mountain.

The game's snow is white, and under the night sky a white surface is the brightest thing in the
picture: brighter than the building's own stone (0.59 against 0.38 in V11). So the snow is painted as
it lies in the shade at the blue hour, in the ramp "snow" of the palette (A0, 2026-11-15): a cold
blue-grey that stays below the stone of the front and above the rock. Two blocks, one set of pictures:

    SNOW         snow_block             the whole block
    SNOW_LAYER   snow[layers=1..8]      what lies on the mountain's shelves, an eighth of a block a layer

    snow         every face that is looked down on, and all six of the whole block: the ramp's
                 middle step, flat, with a very few marks on it -- a pixel or two a step lighter,
                 a single pixel a step darker, each well clear of the next. No grain and no edge:
                 a drift is one surface from cell to cell.
    snow_side    the four sides of a layer. A layer shows the lowest two rows of it for every eighth
                 it is deep. Above the foot it is the step below the field's, as flat as the field
                 and with fewer marks: the shade of a side is painted, not left to the game (below).
                 The foot, the lowest two rows, is the rim of thin snow, where it thins out on the
                 rock: the lowest row is the only place where the darkest step of the ramp is used.

The lightest step of the ramp is kept back (A0): it comes in only if the pictures show the snow too
dull. Each picture has three versions, and every version has the same number of pixels of each
step, so a field of them has no lighter and no darker cells.

How a layer is lit. The game lights the side of a layer as it lights the side of any block: 0.8 of
the top to north and south, 0.6 to east and west, and darker again towards the foot, where the corner
against the ground is darkened. A drift that rises a layer a block then shows a step two pixels high
at every block, half as bright as the snow around it and as dark as the rock: a pile of blue slabs
with dark joints. Snow in the shade has no such steps -- light from the whole sky, thrown back by the
snow all round, leaves a drift nearly one surface. With no step at all, though, a drift seen from
above is a flat patch of the sky's own colour, and reads as a hole in the rock. So the layers
(1 to 8) are lit by this package and not by the game:

    the top       as the game lights it, without the darkening of corners.
    the sides     lit like the top, on all four sides alike, and painted one step of the ramp darker:
                  0.92 of the top on the screen. A step between two layers is a faint line, a pile
                  that stands free still shows which face is its top.
    the foot      the lowest two pixels of every side, where the snow lies on the rock, are lit like
                  a north face (0.8): the rim is in the shade of the drift, about as dark as the rock
                  it thins out on.

The whole block stays as the game lights a block: it is for walls and masses, not for drifts.

What was tried and dropped. On flat sheets of ten by ten tiles: anything larger than a mark -- a
soft drift to a tile reads as a grid of glyphs, thin wisps on one diagonal as rain, swells with
hollows beside them as hammered metal. In pictures of the test scene and of the mountain: sides lit
like the top and painted like it (the hole in the rock), every side lit like a north face (the
steps read as stacked plates again), the game's light with the corners left dark (the slabs).
The card has the numbers.
"""
import numpy as np

from ..common import blocks as B
from ..common import palette as P
from . import _kit as K

TILE = K.TILE

# the blocks this package paints; nobody else may
BLOCKS = K.blocks(B.SNOW, B.SNOW_LAYER)

VERSIONS = 3
RIM, HOLLOW, FIELD, SWELL, KEPT_BACK = range(5)     # the steps of the ramp, dark to light
# the marks of one picture, (step, pixels): nine pixels in 256
MARKS = ((SWELL, 2), (SWELL, 2), (SWELL, 1), (SWELL, 1), (HOLLOW, 1), (HOLLOW, 1), (HOLLOW, 1))
SIDE = HOLLOW       # the step of the side above its foot
SIDE_MARKS = ((FIELD, 2), (FIELD, 1), (FIELD, 1))   # the side has ten rows to put them in: a step lighter only
PAIRS = ((1, 0), (1, -1))   # the second pixel of a mark of two: beside the first, or up to the right of it
APART = 4           # pixels from one mark to the next, at the least (over the tile's edge too)
FOOT = 2            # the lowest rows of the side: what one layer shows
CLEAN = 4           # rows of the side above the foot that carry no mark: the edge of thin snow is plain
FOOT_RIM = 11       # pixels of the lowest row that take the darkest step, in runs
FOOT_FIELD = 5      # pixels of the row above it that take the field's step, in runs

SIDES = ("north", "south", "east", "west")
SIDE_LIT = "up"     # the sides above the foot are lit like this face of a block, all four alike
FOOT_LIT = "north"  # ... and the foot like this one


def _wrapped(d):
    """A distance along one side of the tile, the short way round its edge."""
    return abs((d + TILE // 2) % TILE - TILE // 2)


def _set_down(rng, rows, marks, base):
    """One try at a field: the marks set down one after another, each where it keeps APART from
    those before it. None when one of them finds no room."""
    lv = np.full((rows, TILE), base, dtype=np.int32)
    taken = []
    for step, pixels in marks:
        for _ in range(200):
            x, y = int(rng.integers(TILE)), int(rng.integers(rows))
            cells = [(x, y)]
            if pixels == 2:
                dx, dy = PAIRS[int(rng.integers(len(PAIRS)))]
                cells.append(((x + dx) % TILE, (y + dy) % TILE if rows == TILE else y + dy))
            if all(0 <= cy < rows for _, cy in cells) and all(
                    max(_wrapped(cx - tx), _wrapped(cy - ty) if rows == TILE else abs(cy - ty)) >= APART
                    for cx, cy in cells for tx, ty in taken):
                break
        else:
            return None
        for cx, cy in cells:
            lv[cy, cx] = step
        taken += cells
    return lv


def _field(rng, rows=TILE, marks=MARKS, base=FIELD):
    """The steps of a field of `base` with its marks. On a whole tile the distance between two marks
    counts over the edge, so they keep apart from tile to tile as well; on the first `rows` rows
    only (the side) nothing joins top to foot."""
    for _ in range(200):
        lv = _set_down(rng, rows, marks, base)
        if lv is not None:
            return lv
    raise AssertionError(f"snow: {len(marks)} marks do not fit {rows} rows {APART} apart")


def _runs(rng, count):
    """`count` pixels of a row picked in runs: where a slow wave along the row stands highest."""
    x = np.arange(TILE)
    wave = sum(h * np.cos(2 * np.pi * turns * x / TILE + rng.uniform(0, 2 * np.pi))
               for turns, h in ((1, 1.0), (2, 0.8), (3, 0.6)))
    picked = np.zeros(TILE, dtype=bool)
    picked[np.argsort(wave, kind="stable")[-count:]] = True
    return picked


def _side(rng):
    """The steps of the side picture: the side's own step, a few marks high up on it, and along the
    foot the rim of thin snow -- the lowest row the darkest step for most of its length, the row
    above it broken by the field's step, so the rim is not a ruled line."""
    lv = np.full((TILE, TILE), SIDE, dtype=np.int32)
    marked = TILE - FOOT - CLEAN
    lv[:marked] = _field(rng, marked, SIDE_MARKS, SIDE)
    lv[TILE - FOOT:] = HOLLOW
    lv[TILE - 1, _runs(rng, FOOT_RIM)] = RIM
    lv[TILE - 2, _runs(rng, FOOT_FIELD)] = FIELD
    return lv


def _picture(lv):
    px = np.empty(lv.shape + (4,), dtype=np.uint8)
    px[..., :3] = np.array([P.colour("snow", i) for i in range(len(P.RAMPS["snow"]))], dtype=np.uint8)[lv]
    px[..., 3] = 255
    return px


def levels():
    """{picture name: [the steps of each version]}."""
    return {"snow": [_field(np.random.default_rng(164 + v)) for v in range(VERSIONS)],
            "snow_side": [_side(np.random.default_rng(1640 + v)) for v in range(VERSIONS)]}


def textures():
    """{picture name: [versions]}, as K.paint takes them."""
    return {name: [_picture(lv) for lv in versions] for name, versions in levels().items()}


def faults(drawn):
    """What breaks the rules the director set for the snow (A0 #29065), read off the steps of the
    pictures: [] when nothing does. The side is held to them a step lower: its shade is painted."""
    wrong = []
    counts = {name: [np.bincount(lv.ravel(), minlength=5) for lv in versions] for name, versions in drawn.items()}
    for name, versions in drawn.items():
        for v, lv in enumerate(versions):
            # the side's foot has its own rule
            body, base = (lv, FIELD) if name == "snow" else (lv[:TILE - FOOT], SIDE)
            if (lv == KEPT_BACK).any():
                wrong.append(f"{name}{v}: the lightest step is kept back, and it is used")
            if (body == RIM).any() or (lv[:TILE - 1] == RIM).any():
                wrong.append(f"{name}{v}: the darkest step outside the lowest row of the side")
            if (body == base).sum() < 0.95 * body.size:
                wrong.append(f"{name}{v}: only {(body == base).sum()} of {body.size} pixels are its own step")
            if any((counts[name][v] != other).any() for other in counts[name]):
                wrong.append(f"{name}{v}: not as many pixels of each step as the other versions")
    return wrong


def _layer_sides(ref, model):
    """A model of the layers as this package lights it. Its sides show snow_side, whatever the game's
    model shows there, and stand in two boxes of their own: the foot, lit as FOOT_LIT says, and what
    rises above it, lit as SIDE_LIT says. No corner of the model is darkened. The game's own second
    box of the thinnest layer (the underside, seen from within) is left as it is."""
    boxes = []
    for el in model["elements"] or []:
        sides = {name: dict(face, texture=f"{K.NS}:block/snow_side")
                 for name, face in el["faces"].items() if name in SIDES}
        if not sides:
            boxes.append(el)
            continue
        (x0, y0, z0), (x1, y1, z1) = el["from"], el["to"]
        if (x0, y0, z0, x1, z1) != (0, 0, 0, TILE, TILE) or not FOOT <= y1 <= TILE or len(sides) != len(SIDES):
            raise AssertionError(f"snow: {ref} is not a layer from the ground up over the whole cell ({el['from']} to {el['to']})")
        boxes.append(dict(el, faces={name: face for name, face in el["faces"].items() if name not in SIDES}))
        foot = {name: dict(face, uv=[0, TILE - FOOT, TILE, TILE]) for name, face in sides.items()}
        boxes.append(dict(el, to=[x1, FOOT, z1], faces=foot, shade_direction_override=FOOT_LIT))
        if y1 > FOOT:
            above = {name: dict(face, uv=[0, TILE - y1, TILE, TILE - FOOT]) for name, face in sides.items()}
            boxes.append(dict(el, **{"from": [x0, FOOT, z0]}, faces=above, shade_direction_override=SIDE_LIT))
    model["elements"] = boxes
    model["ambientocclusion"] = False
    return model


def pack(pack_dir):
    drawn = levels()
    wrong = faults(drawn)
    if wrong:
        raise AssertionError("snow breaks its own rules:\n  " + "\n  ".join(wrong))
    for name, versions in drawn.items():
        K.paint(pack_dir, name, [_picture(lv) for lv in versions])
    return [K.redirect(pack_dir, B.SNOW, {"block/snow": "snow"}),
            K.redirect(pack_dir, B.SNOW_LAYER, {"block/snow": "snow"}, edit=_layer_sides)]
