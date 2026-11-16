"""The sea along the railway (site/_rail; card site/railway, a4's assignment of 11-16): what of the
line stands lower than the cloud is the cloud's.

  the piers' feet   the viaduct's masonry is site/viaduct's down to y -24. From -25 down through
                    the sea a pier is built here, of the same stone, so that no pier ends in the
                    air where the sea lies low beside it.
  the room          no cloud where the train runs: over the track's three rows and the row outside
                    them on either side, from the rails' level to HEAD blocks above it, the whole
                    line. A rider whose head enters a block of cloud is smothered and sees nothing
                    but the block's picture (outb, 11-16): the sea is blocks.
  the bank          over the line's end, from MOUTH on, the sea is heaped into a long bank with
                    the track in a cleft through it: the train waits in the cleft unseen and comes
                    out of the bank at MOUTH. The cleft leans shut over the track and leaves a rift
                    one block wide, here and there bridged, so that the sky's light falls into it
                    and the cloud inside is as light as the cloud outside.

Nothing is done in a scene where the line is not built (built()).
"""
import math

import numpy as np

from artkit import noise as N

from ..common import blocks as B
from ..site import _rail as R

STONE = B.TUFF_BRICK.block      # the viaduct's stone (site/viaduct: dark tuff brick)
PIER_TOP = R.CLOUD - 1          # -25: a pier is built here from this block down
PIER_FOOT = -31                 # ... to this one, through the sea (the trestle's legs went as far)
ROOM = 2.5                      # blocks either side of the centre line that are kept free
HEAD = 5                        # ... and blocks over the rails (the line's gauge)
BUILT = 24                      # so many of the viaduct's cells built, and the line is there

MOUTH = 180.0                   # s where the train comes out of the bank: the rails are at the sea's face
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
    for (x, z), c in R.deck(1.5).items():
        if c.s < R.S_FOOT + 1.0:
            continue
        y = R.slab(c.top)[0]
        state = canvas.b.get((x + ox, y + oy, z + oz)) or canvas.b.get((x + ox, y - 1 + oy, z + oz))
        if state is not None and _name(state) not in cloud:
            n += 1
            if n >= BUILT:
                return True
    return False


def feet(canvas, origin):
    """Build the piers' feet: every column of a pier from PIER_TOP, or from under the deck where the
    deck is lower, down to PIER_FOOT or to what stands there already. Returns the blocks placed."""
    ox, oy, oz = origin
    cells = R.deck(ROOM)
    n = 0
    for p in R.piers():
        for (x, z), c in cells.items():
            if abs(c.s - p.s) > R.PIER / 2.0:
                continue
            for y in range(min(PIER_TOP, R.slab(c.top)[0] - 1), PIER_FOOT - 1, -1):
                if (x + ox, y + oy, z + oz) in canvas.b:
                    break
                canvas.set(x + ox, y + oy, z + oz, STONE)
                n += 1
    return n


def _far(X, Z):
    """(s, r) of the columns beside the far straight: the way along the line, carried on past its
    end, and how many columns the column lies from the track's middle one."""
    return R.S_CURVE + (Z + 0.5 - R.CENTRE[1]), np.abs(X - R.FAR)


def _first(s):
    """The lowest block that may hold cloud over the track at s."""
    return int(math.ceil(R.level(min(float(s), R.LENGTH)) + HEAD))


def bank(X, Z):
    """The height of the bank's top in every column (-inf where the bank is not): its crest CREST
    over the cleft, kept as far as BROAD from the centre line and falling away beyond in a round
    shoulder, lower over the mouth's lip and past the line's end, never a ruled ridge."""
    s, r = _far(X, Z)
    first = np.vectorize(_first, otypes=[float])(s)
    top = first + CREST - 0.9 * np.maximum(r - BROAD, 0.0) ** 1.4
    top -= 1.2 * np.clip(1.0 - (s - MOUTH) / 3.0, 0.0, 1.0) ** 2            # the lip over the mouth
    top -= 0.5 * np.maximum(s - R.LENGTH - 1.0, 0.0) ** 1.6                 # the round end
    top += 1.3 * N.fbm2(X / 6.0, Z / 6.0, SEED, octaves=2) - 0.2
    return np.where((s >= MOUTH) & (s <= R.LENGTH + TAIL + 6.0), top, -np.inf)


def room(lo, shape, y0):
    """The cells of the sea's box (first cell at scene (lo[0], y0, lo[1])) that hold no cloud: the
    train's room along the whole line, and from MOUTH on the cleft's lean and the rift over it."""
    nx, ny, nz = shape
    out = np.zeros(shape, dtype=bool)

    def free(i, k, a, b):
        if 0 <= i < nx and 0 <= k < nz:
            out[i, min(max(a - y0, 0), ny):min(max(b - y0, 0), ny), k] = True

    for (x, z), c in R.deck(ROOM).items():
        free(x - lo[0], z - lo[1], int(math.floor(c.top)), int(math.ceil(c.top + HEAD)))
    # the cleft: closed behind the train (the room ends with the line), leaning in above the room
    z0, z1 = int(math.floor(R.at(MOUTH).z)), int(math.floor(R.at(R.LENGTH).z))
    for z in range(z0, z1 + 1):
        first = _first(R.S_CURVE + (z + 0.5 - R.CENTRE[1]))
        for d in (-1, 0, 1):
            free(R.FAR + d - lo[0], z - lo[1], first, first + 1)
        if (z - z0) % sum(RIFT) < RIFT[0]:
            free(R.FAR - lo[0], z - lo[1], first, y0 + ny)
    return out
