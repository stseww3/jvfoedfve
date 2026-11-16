"""The sea along the railway (site/_rail; card site/railway, a4's assignment of 11-16): what of the
line stands lower than the cloud is the cloud's.

  the piers' feet   the viaduct's masonry is site/viaduct's down to y -24. Below its lowest course
                    a pier is built here, of the same stone, down through the sea, so that no pier
                    ends in the air where the sea lies low beside it.
  the room          no cloud where the train runs: over the track's three rows and the row outside
                    them on either side, from the rails' level to HEAD blocks above it, the whole
                    line and two blocks past its end. A rider whose head enters a block of cloud is
                    smothered and sees nothing but the block's picture (outb, 11-16): the sea is
                    blocks, and a block's cell that only touches the car is in the way as well.
  the bank          over the line's end the sea is heaped into a long bank with the track in a
                    cleft through it, where the train waits unseen. From RAMP before MOUTH the
                    cloud rises beside the track, a cutting open to the sky; from MOUTH on the
                    cleft leans shut over the track and leaves a rift one block wide, here and
                    there bridged, so that the sky's light falls into it and the cloud inside is
                    nearly as light as the cloud outside. The train comes out from under the roof
                    at MOUTH and out of the cutting RAMP further up the line.

Nothing is done in a scene where the viaduct is not built (built()).
"""
import math

import numpy as np

from artkit import noise as N

from ..common import blocks as B
from ..site import _rail as R

STONE = B.TUFF_BRICK.block      # the viaduct's body (site/viaduct.BRICK)
PIER_TOP = R.CLOUD - 1          # -25: a pier's foot begins no higher than this block
PIER_FOOT = -31                 # ... and goes down to this one, through the sea (the trestle's legs went as far)
ROOM = R.GAUGE["half"] + 1.0    # 2.5: blocks either side of the centre line that are kept free
HEAD = int(R.GAUGE["height"])   # 5: ... and blocks over the rails
PAST = 2                        # the room goes on this many blocks past the line's end
BUILT = 24                      # so many of the viaduct's rail cells built, and the line is there

MOUTH = R.s_of_level(-26.0)     # 150: where the roof ends; further up the line no roof fits under the sea's peak
RAMP = 14.0                     # the cutting before the mouth: the cloud beside the track rises over this length
TAIL = 5.0                      # the bank goes on this far past the line's end
CREST = 2.0                     # blocks of cloud over the cleft's first course
BROAD = 4.0                     # blocks from the centre line the bank keeps its crest
RIFT = (3, 2)                   # the rift overhead: so many cells open, so many bridged
SEED = 5173


def _name(state):
    return state.partition("[")[0].split(":")[-1]


def built(canvas, origin, cloud):
    """Whether the viaduct stands on the canvas: something that is not cloud in the rails' cells."""
    ox, oy, oz = origin
    n = 0
    for (x, z), c in R.deck(R.GAUGE["half"]).items():
        if c.s < R.S_FOOT + 1.0:
            continue
        y = R.slab(c.top)[0]
        state = canvas.b.get((x + ox, y + oy, z + oz)) or canvas.b.get((x + ox, y - 1 + oy, z + oz))
        if state is not None and _name(state) not in cloud:
            n += 1
            if n >= BUILT:
                return True
    return False


def _piers():
    """[(x, z)]: the columns of the viaduct's piers. site/viaduct tells its own (with the pilasters);
    where that package is not there, the cells a4 named: the deck and the row outside it, a block
    either way of the pier's middle."""
    try:
        from ..site import viaduct
    except ImportError:
        cells = R.deck(ROOM)
        return sorted(k for k, c in cells.items() if any(abs(c.s - p.s) <= R.PIER / 2.0 for p in R.piers()))
    return sorted(k for _, cells in viaduct.piers_cells() for k in cells)


def _rock():
    try:
        from ..site import terrain
        return terrain.top
    except ImportError:
        return lambda x, z: None


def feet(canvas, origin, rock=None):
    """Build the piers' feet: in every column of a pier, from under the masonry that stands there
    (no higher than PIER_TOP) down to PIER_FOOT or to what stands there already. ``rock(x, z)``
    tells the y of the mountain's top block in a column, or None: a pier that stands on the rock has
    no foot (the rock is a crust, and nothing is built inside it). Returns the blocks placed."""
    ox, oy, oz = origin
    rock = rock or _rock()
    cells = R.deck(ROOM + 1.0)
    n = 0
    for x, z in _piers():
        c = cells.get((x, z))
        if c is None:
            continue
        y = int(math.floor(c.top)) + 1
        while y >= PIER_FOOT and (x + ox, y + oy, z + oz) not in canvas.b:
            y -= 1                                  # down to the masonry's top
        while y >= PIER_FOOT and (x + ox, y + oy, z + oz) in canvas.b:
            y -= 1                                  # ... and through it
        ground = rock(x, z)
        if ground is not None and ground >= y:
            continue                                # the pier stands on the rock here
        for yy in range(min(y, PIER_TOP), PIER_FOOT - 1, -1):
            if (x + ox, yy + oy, z + oz) in canvas.b:
                break
            canvas.set(x + ox, yy + oy, z + oz, STONE)
            n += 1
    return n


def _far(X, Z):
    """(s, r) of the columns beside the far straight: the way along the line, carried on past its
    end, and how many columns a column lies from the track's middle one."""
    return R.S_CURVE + (Z + 0.5 - R.CENTRE[1]), np.abs(X - R.FAR)


def _first(s):
    """The lowest block that may hold cloud over the track at s, on the far straight."""
    s = np.minimum(s, R.LENGTH)
    return np.ceil(R.FOOT_LEVEL - R.EASY * (s - R.S_FOOT) + HEAD)


def bank(X, Z, low):
    """The height of the bank's top in every column (-inf where the bank is not). ``low`` is the
    height the sea keeps beside what stands in it: the bank rises from it over RAMP before the
    mouth. From the mouth on its crest lies CREST over the cleft, kept as far as BROAD from the
    centre line and falling away beyond in a round shoulder; it sinks past the line's end. Never a
    ruled ridge."""
    s, r = _far(X, Z)
    first = _first(s)
    t = np.clip((s - (MOUTH - RAMP)) / RAMP, 0.0, 1.0)
    crest = low + (first + CREST - low) * (t * t * (3.0 - 2.0 * t))
    top = crest + 1.3 * N.fbm2(X / 6.0, Z / 6.0, SEED, octaves=2) - 0.2
    # the roof is a course thick at the least over the cleft, and its walls beside the room as high
    top = np.where((s >= MOUTH) & (r <= BROAD), np.maximum(top, first + 1.0), top)
    top = top - 0.9 * np.maximum(r - BROAD, 0.0) ** 1.4
    top = top - 0.5 * np.maximum(s - R.LENGTH - 1.0, 0.0) ** 1.6            # the round end
    return np.where((s >= MOUTH - RAMP) & (s <= R.LENGTH + TAIL + 6.0), top, -np.inf)


def room(lo, shape, y0):
    """The cells of the sea's box (first cell at scene (lo[0], y0, lo[1])) that hold no cloud: the
    train's room along the whole line, the cutting open to the sky before MOUTH, and from MOUTH on
    the cleft's lean and the rift over it."""
    nx, ny, nz = shape
    out = np.zeros(shape, dtype=bool)

    def free(x, z, a, b=None):
        i, k = x - lo[0], z - lo[1]
        if 0 <= i < nx and 0 <= k < nz:
            b = y0 + ny if b is None else b
            out[i, min(max(a - y0, 0), ny):min(max(b - y0, 0), ny), k] = True

    wide = int(math.ceil(ROOM - 0.5))
    z_mouth = int(math.floor(R.at(MOUTH).z))
    for (x, z), c in R.deck(ROOM).items():
        on_far = c.s > R.S_CURVE
        # up the line from the mouth nothing is over the track at all
        free(x, z, int(math.floor(c.top)), None if not on_far or z < z_mouth else int(math.ceil(c.top + HEAD)))
    z_end = int(math.floor(R.at(R.LENGTH).z))
    for z in range(z_mouth, z_end + PAST + 1):
        s = R.S_CURVE + (z + 0.5 - R.CENTRE[1])
        first = int(_first(s))
        if z > z_end - 1:                           # past the line's end: the room carried straight on
            floor = int(math.floor(R.level(R.LENGTH)))
            for d in range(-wide, wide + 1):
                free(R.FAR + d, z, floor, first)
        if z <= z_end:
            for d in (-1, 0, 1):
                free(R.FAR + d, z, first, first + 1)
            if (z - z_mouth) % sum(RIFT) < RIFT[0]:
                free(R.FAR, z, first)
    return out
