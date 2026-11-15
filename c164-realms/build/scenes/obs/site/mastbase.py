"""site/mastbase: the stone foot of the radio mast (plan/ART-PLAN.md 4, 5.3, card
plan/packages/site/mastbase.md). Blocks only, no display entities.

The mast itself, its guys, insulators and the aerial to the clock tower are the machines line's
(machines/radiomast); the bracket on the tower is the main line's. This card gives them what they
stand on and tie to, on the mast pad north of the court (S.MAST_PAD, level with the upper terrace;
its kerb and railing are the terrain card's):

  - a two-step podium of dark slate brick with a grey-white coping on each step, centred on the
    mast's foot (S.RADIO_MAST["foot"]), with a riveted iron shoe let into the top;
  - a paved apron round it in the terrace's middle stone;
  - four guy anchors on the diagonals: a riveted iron block on a slate footing with an eye bolt;
  - a lead-in post on the podium's south-west corner, the corner that faces the clock tower: the
    aerial's down-lead and halyard tie off here.

What the other cards read from this module (blocks they place later win over these):
  TOP           the first free y above the upper step: the mast's legs or pole start here
  SOCKET        the cell over the iron shoe, in the middle of the upper step
  LEGS          the four corner cells of the upper step, for a four-legged mast
  GUY_ANCHORS   the points (x, y, z) where a guy meets its eye bolt
  ANTENNA_HOOK  the point on top of the lead-in post
Everything here stays under y 4: the arrival view (V1) looks over the terrace edge and sees nothing
of the pad below about y 3, so the foot never draws the eye from the building.
"""
from . import _kit as K
from ..common import blocks as B
from ..common import skeleton as S

ORDER = 72      # after the terrain (10), the court (60) and the outbuildings (70)

PLINTH = B.SLATE_BRICK.block            # the podium: dark slate brick
COPE = B.ASHLAR_PANEL.slab              # grey-white coping
IRON = B.IRON_RIVETED.block            # riveted iron: the shoe, the anchors, the post
ROD = B.IRON_ROD                        # eye bolts and the post's head

FX, FZ = S.RADIO_MAST["foot"]           # (23, -40)
G = S.MAST_PAD["feet"]                  # 0: where feet stand on the pad; the paving block is one below
LOWER, UPPER = 2, 1                     # half-widths of the two steps: 5x5 under 3x3
APRON = LOWER + 1                       # the paved apron, one cell round the lower step
REACH = 4                               # the anchors stand this far out on each diagonal

TOP = G + 2
SOCKET = (FX, TOP, FZ)
LEGS = [(FX + sx * UPPER, TOP, FZ + sz * UPPER) for sx in (-1, 1) for sz in (-1, 1)]
_ANCHOR_CELLS = [(FX + sx * REACH, FZ + sz * REACH) for sx in (-1, 1) for sz in (-1, 1)]
GUY_ANCHORS = [(x + 0.5, G + 2.0, z + 0.5) for x, z in _ANCHOR_CELLS]
_HOOK_CELL = (FX - LOWER, FZ + LOWER)   # the south-west corner of the lower step, toward the clock tower
ANTENNA_HOOK = (_HOOK_CELL[0] + 0.5, G + 4.0, _HOOK_CELL[1] + 0.5)


def _put(c, o, x, y, z, state, keep=False):
    c.set(o[0] + x, o[1] + y, o[2] + z, state, keep=keep)


def build(canvas, origin=(0, 0, 0)):
    c, o = canvas, origin
    x0, z0, x1, z1 = S.MAST_PAD["box"]
    pave = G - 1

    # until the terrain card's pad is merged the pad is a flat slab of the terrace's stone, laid only
    # where there is nothing yet; under the podium a footing goes a little way into the rock
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            _put(c, o, x, pave, z, K.FIELD, keep=True)
            _put(c, o, x, pave - 1, z, K.EDGE, keep=True)
    for x in range(FX - APRON, FX + APRON + 1):
        for z in range(FZ - APRON, FZ + APRON + 1):
            _put(c, o, x, pave, z, K.STRIP)                 # the apron, in the terrace's middle stone
            for y in (pave - 1, pave - 2):
                _put(c, o, x, y, z, PLINTH, keep=True)

    # the podium: two steps of slate brick, a grey-white coping on each, the iron shoe in the top
    for dx in range(-LOWER, LOWER + 1):
        for dz in range(-LOWER, LOWER + 1):
            x, z = FX + dx, FZ + dz
            _put(c, o, x, G, z, PLINTH)
            if max(abs(dx), abs(dz)) == LOWER:
                _put(c, o, x, G + 1, z, COPE + "[type=bottom]")
            elif (dx, dz) != (0, 0):
                _put(c, o, x, G + 1, z, PLINTH)
                _put(c, o, x, G + 2, z, COPE + "[type=bottom]")
            else:
                _put(c, o, x, G + 1, z, IRON)               # the shoe; the socket above it stays open

    # four guy anchors on the diagonals: an iron block on a slate footing, an eye bolt on top
    for x, z in _ANCHOR_CELLS:
        _put(c, o, x, pave, z, PLINTH)
        _put(c, o, x, pave - 1, z, PLINTH, keep=True)
        _put(c, o, x, G, z, IRON)
        _put(c, o, x, G + 1, z, ROD + "[facing=up]")

    # the lead-in post on the corner that faces the clock tower
    hx, hz = _HOOK_CELL
    _put(c, o, hx, G + 1, hz, IRON)
    _put(c, o, hx, G + 2, hz, ROD + "[facing=up]")
    _put(c, o, hx, G + 3, hz, ROD + "[facing=up]")
    return 0
