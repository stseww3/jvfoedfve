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
                 it is deep: the field again, a step darker along the foot. The lowest row is the
                 only place where the darkest step of the ramp is used: the rim of thin snow, where
                 it thins out on the rock.

The lightest step of the ramp is kept back (A0): it comes in only if the pictures show the snow too
dull. Each picture has three versions, and every version has the same number of pixels of each
step, so a field of them has no lighter and no darker cells.

What was tried and dropped, on flat sheets of ten by ten tiles (the card has it): anything larger
than a mark. A soft drift to a tile reads as a grid of glyphs, thin wisps on one diagonal as rain,
swells with hollows beside them as hammered metal.
"""
import os

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
SIDE_MARKS = ((SWELL, 2), (SWELL, 1), (HOLLOW, 1), (HOLLOW, 1))     # the side has ten rows to put them in
PAIRS = ((1, 0), (1, -1))   # the second pixel of a mark of two: beside the first, or up to the right of it
APART = 4           # pixels from one mark to the next, at the least (over the tile's edge too)
FOOT = 2            # the lowest rows of the side: what one layer shows
CLEAN = 4           # rows of the side above the foot that carry no mark: the edge of thin snow is plain
FOOT_RIM = 11       # pixels of the lowest row that take the darkest step, in runs
FOOT_FIELD = 5      # pixels of the row above it that stay the field's step, in runs


def _wrapped(d):
    """A distance along one side of the tile, the short way round its edge."""
    return abs((d + TILE // 2) % TILE - TILE // 2)


def _set_down(rng, rows, marks):
    """One try at a field: the marks set down one after another, each where it keeps APART from
    those before it. None when one of them finds no room."""
    lv = np.full((rows, TILE), FIELD, dtype=np.int32)
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


def _field(rng, rows=TILE, marks=MARKS):
    """The steps of the field. On a whole tile the distance between two marks counts over the edge,
    so they keep apart from tile to tile as well; on the first `rows` rows only (the side) nothing
    joins top to foot."""
    for _ in range(200):
        lv = _set_down(rng, rows, marks)
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
    """The steps of the side picture: the field, and along the foot the rim of thin snow -- the
    lowest row the darkest step for most of its length, the row above it a hollow's step, both
    broken, so the rim is not a ruled line."""
    lv = np.full((TILE, TILE), FIELD, dtype=np.int32)
    marked = TILE - FOOT - CLEAN
    lv[:marked] = _field(rng, marked, SIDE_MARKS)
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
    pictures: [] when nothing does."""
    wrong = []
    counts = {name: [np.bincount(lv.ravel(), minlength=5) for lv in versions] for name, versions in drawn.items()}
    for name, versions in drawn.items():
        for v, lv in enumerate(versions):
            body = lv if name == "snow" else lv[:TILE - FOOT]       # the side's foot has its own rule
            if (lv == KEPT_BACK).any():
                wrong.append(f"{name}{v}: the lightest step is kept back, and it is used")
            if (body == RIM).any() or (lv[:TILE - 1] == RIM).any():
                wrong.append(f"{name}{v}: the darkest step outside the lowest row of the side")
            if (body == FIELD).sum() < 0.95 * body.size:
                wrong.append(f"{name}{v}: only {(body == FIELD).sum()} of {body.size} pixels are the field's step")
            if any((counts[name][v] != other).any() for other in counts[name]):
                wrong.append(f"{name}{v}: not as many pixels of each step as the other versions")
    return wrong


# TRIAL (not for delivery): how the sides of the layers are lit, picked by the environment so that one
# commit draws every candidate.  "" as the game does; a: sides lit like the top, corners darkened;
# b1: sides lit like the top, no darkening of corners; b3: sides lit like a north face, no darkening
_TRY = os.environ.get("C164_SNOW_TRY", "")
SIDE_SHADE = {"a": "up", "b1": "up", "b3": "north"}.get(_TRY)
CORNERS = False if _TRY in ("b1", "b3") else None
SIDES = ("north", "south", "east", "west")


def _layer_sides(ref, model):
    """The sides of the models of the layers show snow_side, whatever the game's model shows there,
    and stand in a box of their own, so that they can be lit otherwise than the game lights a side."""
    boxes = []
    for el in model["elements"] or []:
        sides = {name: face for name, face in el["faces"].items() if name in SIDES}
        if not sides:
            boxes.append(el)
            continue
        for face in sides.values():
            face["texture"] = f"{K.NS}:block/snow_side"
        rest = {name: face for name, face in el["faces"].items() if name not in SIDES}
        if rest:
            boxes.append(dict(el, faces=rest))
        side = dict(el, faces=sides)
        if SIDE_SHADE:
            side["shade_direction_override"] = SIDE_SHADE
        boxes.append(side)
    model["elements"] = boxes
    return model


def pack(pack_dir):
    drawn = levels()
    wrong = faults(drawn)
    if wrong:
        raise AssertionError("snow breaks its own rules:\n  " + "\n  ".join(wrong))
    for name, versions in drawn.items():
        K.paint(pack_dir, name, [_picture(lv) for lv in versions])
    return [K.redirect(pack_dir, B.SNOW, {"block/snow": "snow"}, ao=CORNERS),
            K.redirect(pack_dir, B.SNOW_LAYER, {"block/snow": "snow"}, edit=_layer_sides, ao=CORNERS)]
