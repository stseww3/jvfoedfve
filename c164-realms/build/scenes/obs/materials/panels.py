"""Work package materials/panels (plan ART-PLAN 6.2, materials.md section 6): the sixteen instrument
panels, the blocks an instrument wall is stacked from (the timing room's wall V10, the switchboard
of the power house, the world-clock wall).

Each is a glazed-terracotta block redirected so that the instrument shows on the one side the block
faces and the other five sides are a plain iron casing. In the game's model the south face is the
one a block state turns to `facing`, and the pinwheel turn the game gives each face is dropped, so
the instrument stands upright whichever way the block looks (the stand-in already worked this way).

Sixteen different faces on one wall turn into a slot machine unless they are held together (the
pre-review of the designs, point 5), so they are built as one set and sorted into three ranks:

  - every face is the same module: a dark brushed plate with the raised edge of the riveted plates
    and a screw in each corner; where a face has a row of three parts (valves, fuses, switch
    poles, relays, lamps, jacks, knobs) they stand on the same three columns, so the parts line
    up along a wall; the light falls from the upper left on all of them;
  - dark (ten): brass, copper and iron on the plate; what is light on them is small (figures,
    labels, the emblem);
  - light (three): the dial and the gauges in porcelain, the recorder's paper;
  - lit (three): the valves, the oscilloscope's tube, the pilot lamps. Only the pixels that glow
    (GLOW) are drawn at full brightness: a second front lies over the first and shows those
    pixels alone (see glow and _mount), the way the game lays the coloured fringe over the side of
    its grass block. Everything else on a lit face, down to the black floor the lamps sit in and
    a pilot lamp while it is out (OUT), takes the light of the room like the faces beside it, so
    in a dim room there are filaments, lamps and a round green tube on a dark wall, and no
    glowing rectangles. Green and red are single lamps.

Four faces are animated, slowly, and on one beat, the second of the master clock (FRAMETIME): the
units wheel of the register steps once a second, the pilot lamps take turns every two, the trace
runs through a wave in two, the filaments breathe once in four. The game starts every animated
picture together, so what steps, steps on the same tick. The numbers are this package's until
motion (A8) sets a beat.
"""
import math

import numpy as np

from artkit import respack

from ..common import blocks as B
from ..common import palette as P
from . import _kit as K

TILE = K.TILE

# the blocks this package paints; nobody else may
BLOCKS = K.blocks(*B.PANELS.values())

FRAMETIME = {"tubes": 20, "scope": 5, "counter": 20, "pilot_lamps": 20}     # ticks a frame stays; 20 = one second
SMOOTH = ("tubes",)             # frames the game blends into one another: a glow that swells, no steps
LIT = 15                        # light_emission of what glows: its picture's own colours in any light
# the three ranks of the card: mostly dark, a few light, at most four lit
RANKS = {
    "lit": ("tubes", "scope", "pilot_lamps"),
    "light": ("dial", "gauges", "recorder"),
    "dark": ("knife_switch", "counter", "patch_panel", "fuses", "bell", "louvre", "drawers", "nameplate",
             "relays", "bus_switch"),
}

TRIO = (3, 7, 11)               # where a row of three parts stands: each part two pixels wide from here
CORNERS = ((1, 1), (14, 1), (1, 14), (14, 14))


def _ramp(name):
    return [P.colour(name, step) for step in range(len(P.RAMPS[name]))]


FE, BR, PC, GL, PH, SG, EN, CR, CU = (_ramp(n) for n in (
    "iron", "brass", "porcelain", "glow", "phosphor", "signal", "enamel", "cream", "old_copper"))


# ---- pixel helpers -----------------------------------------------------------------------------------
def _put(px, x, y, rgb):
    if 0 <= x < TILE and 0 <= y < TILE:
        px[y, x, :3] = rgb
        px[y, x, 3] = 255


def _box(px, x0, y0, x1, y1, rgb):
    """A filled rectangle, both corners included."""
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            _put(px, x, y, rgb)


def _dots(px, cells, rgb):
    for x, y in cells:
        _put(px, x, y, rgb)


def _round(cx, cy, r, inner=-1.0):
    """The pixels whose centres lie within r of (cx, cy) and further than `inner` from it."""
    return [(x, y) for y in range(TILE) for x in range(TILE) if inner < math.hypot(x - cx, y - cy) <= r]


def _turned(px, cells, cx, cy, lit, mid, dark, edge=3.0):
    """A round metal part under the light every face shares (from the upper left): its upper-left
    cells lit, its lower-right ones dark."""
    for x, y in cells:
        lean = (x - cx) + (y - cy)
        _put(px, x, y, lit if lean < -edge else dark if lean > edge else mid)


def _clock(cx, cy, r, degrees):
    """The pixel at `degrees` clockwise from twelve o'clock, r from (cx, cy)."""
    a = math.radians(degrees)
    return int(round(cx + r * math.sin(a))), int(round(cy - r * math.cos(a)))


def _stud(px, x, y, tones):
    """A small round part two pixels across (a knob, a jack, a lamp): tones = (lit, mid, dark)."""
    lit, mid, dark = tones
    _put(px, x, y, lit)
    _put(px, x + 1, y, mid)
    _put(px, x, y + 1, mid)
    _put(px, x + 1, y + 1, dark)


KNOB = (BR[5], BR[3], BR[1])

# What glows on the lit faces, as pixels of the picture; the faces below are drawn from the same
# numbers, so the light sits exactly on what is painted as glowing.
VALVE = (4, 8)                  # the rows a valve's glass takes, first and last
TUBE = (7.5, 6.5, 4.7)          # the oscilloscope's round screen: centre and radius
LAMP_ROWS = (4, 8)              # where the two rows of pilot lamps stand
GLOW = {
    "tubes": [(x + dx, y) for x in TRIO for dx in (0, 1) for y in range(VALVE[0], VALVE[1] + 1)],
    "scope": _round(*TUBE),
    "pilot_lamps": [(x + dx, y + dy) for y in LAMP_ROWS for x in TRIO for dx in (0, 1) for dy in (0, 1)],
}

AMBER = ((GL[4], GL[2], GL[1]), (BR[1], BR[0], BR[0]))      # a lamp lit, and out
GREEN = ((PH[4], PH[3], PH[2]), (PH[1], PH[0], PH[0]))
RED = ((SG[3], SG[2], SG[1]), (SG[1], SG[0], SG[0]))


def _lamps(frame):
    """The pilot lamps in a frame, as (x, y, lamp, on); a lamp is two pixels each way from (x, y).
    The upper row burns steadily (two amber, one green); below it two amber lamps take turns and
    the red one comes on once in a round."""
    upper = ((AMBER, True), (AMBER, True), (GREEN, True))
    lower = ((AMBER, frame % 4 < 2), (RED, frame >= 6), (AMBER, frame % 4 >= 2))
    return [(x, y, lamp, on) for y, row in zip(LAMP_ROWS, (upper, lower)) for x, (lamp, on) in zip(TRIO, row)]


def _lamps_out(frame):
    return [(x + dx, y + dy) for x, y, _, on in _lamps(frame) if not on for dx in (0, 1) for dy in (0, 1)]


# What of GLOW is dark in a frame: a lamp that is out takes the light of the room, like the field
# it sits in, and is gone in the dark until its turn comes.
OUT = {"pilot_lamps": _lamps_out}


def glowing(name, frame=0):
    """The pixels of a lit face that glow in one of its frames."""
    return set(GLOW[name]) - set(OUT[name](frame) if name in OUT else ())


# ---- what every face shares --------------------------------------------------------------------------
def _plate(seed):
    """The module: a dark brushed plate, the raised edge of the riveted plates (light along the top
    and left, dark along the bottom and right) and a screw in each corner."""
    px = P.mat("iron_dark", bevel=0, noise=0.10).paint(TILE, TILE, seed=seed).copy()
    for t in range(TILE):
        _put(px, t, 0, FE[4])
        _put(px, 0, t, FE[4])
        _put(px, t, TILE - 1, FE[1])
        _put(px, TILE - 1, t, FE[1])
    _put(px, 0, TILE - 1, FE[2])
    _put(px, TILE - 1, 0, FE[2])
    for x, y in CORNERS:
        _put(px, x, y, FE[5])
        _put(px, x, y + 1, FE[1])
    return px


def _sunk(px, x0, y0, x1, y1, floor):
    """A field sunk into the plate: its floor, the shadowed edge above and left of it, the lit edge
    below and right."""
    _box(px, x0, y0, x1, y1, floor)
    _box(px, x0 - 1, y0 - 1, x1, y0 - 1, FE[1])
    _box(px, x0 - 1, y0, x0 - 1, y1, FE[1])
    _box(px, x0, y1 + 1, x1 + 1, y1 + 1, FE[4])
    _box(px, x1 + 1, y0, x1 + 1, y1, FE[4])


def case():
    """The five sides that are not the instrument: the same dark plate with a shallow bevel, no screws."""
    return P.mat("iron_dark").paint(TILE, TILE, seed=7).copy()


# ---- dark faces --------------------------------------------------------------------------------------
def knife_switch():
    """Three knife switches on a slate back: two thrown in, the middle one pulled; a label under each."""
    px = _plate(2)
    _sunk(px, 3, 3, 12, 10, FE[1])
    for k, x in enumerate(TRIO):
        _box(px, x, 3, x + 1, 4, BR[2])                     # the jaws
        _put(px, x, 3, BR[4])
        _box(px, x, 9, x + 1, 10, BR[2])                    # the hinge
        _put(px, x, 9, BR[4])
        if k != 1:                                          # the blade home in its jaws
            _box(px, x, 4, x, 9, BR[4])
            _put(px, x, 5, BR[5])
            _box(px, x + 1, 5, x + 1, 8, BR[1])
        else:                                               # pulled: the blade stands out towards the room
            _box(px, x + 1, 7, x + 1, 9, BR[4])
            _put(px, x, 6, FE[5])                           # its grip
            _put(px, x + 1, 6, FE[0])
            _put(px, x, 4, FE[0])                           # the empty jaws
        _put(px, x, 12, CR[1])
        _put(px, x + 1, 12, CR[0])
    return px


_FIGURES = ("111101101101111", "010110010010111", "111001111100111", "111001111001111", "101101111001001",
            "111100111001111", "111100111101111", "111001010010010", "111101111101111", "111101111001111")
_FIGURES = tuple(tuple(f[i:i + 3] for i in range(0, 15, 3)) for f in _FIGURES)


def counter(units=0):
    """A register: three figure wheels behind a window (white figures on black drums), a maker's plate."""
    px = _plate(5)
    _sunk(px, 2, 3, 13, 9, FE[0])
    for k, figure in enumerate((2, 4, units)):
        x = 2 + 4 * k
        _box(px, x, 3, x, 9, FE[2])                         # the gap between two wheels
        for dy, row in enumerate(_FIGURES[figure]):
            for dx, on in enumerate(row):
                if on == "1":
                    _put(px, x + 1 + dx, 4 + dy, CR[2])
    _box(px, 5, 12, 10, 13, BR[2])
    _box(px, 5, 12, 10, 12, BR[4])
    _put(px, 10, 13, BR[1])
    return px


def patch_panel():
    """A jack field of three by three, one cord plugged across it: from the top left jack it hangs
    down between the columns and comes up to the middle right one."""
    px = _plate(6)
    for y in TRIO:
        for x in TRIO:
            _stud(px, x, y, (BR[4], BR[2], FE[0]))          # a brass bush, its hole in shadow
    _dots(px, [(5, 5), (5, 6), (5, 7), (5, 8), (6, 9), (7, 10), (8, 10), (9, 10), (10, 9)], CR[0])
    for x, y in ((3, 3), (11, 7)):                          # the two plugs
        _stud(px, x, y, (CR[3], CR[1], CR[0]))
    return px


def fuses():
    """Three cartridge fuses on a slate back: porcelain between brass caps, a bus bar over the upper
    clips, a label under each."""
    px = _plate(7)
    _sunk(px, 3, 3, 12, 10, FE[1])
    _box(px, 3, 3, 12, 3, BR[1])                            # the bus bar
    for x in TRIO:
        for y, (lit, dark) in ((3, (BR[4], BR[2])), (4, (BR[3], BR[1])), (9, (BR[3], BR[1])), (10, (BR[2], BR[0]))):
            _put(px, x, y, lit)                             # clip, cap ... cap, clip
            _put(px, x + 1, y, dark)
        _box(px, x, 5, x, 8, PC[2])                         # the porcelain, a step under the dial's
        _box(px, x + 1, 5, x + 1, 8, PC[0])
        _put(px, x, 5, PC[3])
        _put(px, x, 12, CR[1])
        _put(px, x + 1, 12, CR[0])
    return px


def bell():
    """A trembler bell: the brass gong, its two coils under it, the hammer standing up from them to
    the gong's rim."""
    px = _plate(8)
    gong = _round(7.5, 6.5, 4.4)
    _turned(px, gong, 7.5, 6.5, BR[4], BR[3], BR[1])
    _dots(px, [(5, 5), (6, 4)], BR[5])                      # the glint on its shoulder
    _stud(px, 7, 6, (BR[5], BR[2], BR[0]))                  # the crown nut
    for x in (5, 8):
        _stud(px, x, 12, (CU[3], CU[2], CU[0]))             # the coils
    _dots(px, [(10, 12), (11, 11)], FE[5])                  # the hammer's arm
    _stud(px, 12, 9, (FE[6], FE[5], FE[3]))                 # its ball
    return px


def louvre():
    """A ventilation louvre: four slats, each lit along its upper edge, shadow in the gap under it."""
    px = _plate(10)
    for y in range(2, 14):
        _box(px, 2, y, 13, y, (FE[4], FE[2], FE[0])[(y - 2) % 3])
    return px


def drawers():
    """Three index drawers: a label card in its holder and a cup pull on each."""
    px = _plate(11)
    for y in (2, 6, 10):
        _box(px, 2, y, 13, y, FE[4])
        _box(px, 2, y + 1, 13, y + 2, FE[3])
        _box(px, 2, y + 3, 13, y + 3, FE[1])
        _box(px, 3, y + 1, 5, y + 1, CR[2])                 # the card
        _box(px, 3, y + 2, 5, y + 2, BR[2])                 # its holder
        _box(px, 9, y + 1, 11, y + 1, BR[4])                # the pull
        _box(px, 9, y + 2, 11, y + 2, BR[1])
    return px


def emblem():
    """The station emblem at sixteen pixels, as the cast-iron emblem plate first set it down
    (iron.py): a ring ten across, the meridian down it, a five-pixel star on its upper-right shoulder."""
    ring = _round(7.5, 7.5, 4.9, inner=4.2 - 1e-9)
    return ring + [(7, y) for y in range(3, 13)] + [(11, 4), (10, 4), (12, 4), (11, 3), (11, 5)]


def nameplate():
    """An enamel nameplate: the station emblem in cream on blue."""
    px = _plate(12)
    _box(px, 2, 2, 13, 13, EN[2])
    _box(px, 2, 2, 13, 2, EN[3])
    _box(px, 2, 2, 2, 13, EN[3])
    _box(px, 2, 13, 13, 13, EN[0])
    _box(px, 13, 2, 13, 13, EN[0])
    _dots(px, emblem(), CR[3])
    return px


def relays():
    """Three relays on a slate back: the armature over a copper coil, a terminal under each."""
    px = _plate(13)
    _sunk(px, 3, 3, 12, 10, FE[1])
    for x in TRIO:
        _put(px, x, 3, FE[6])                               # the armature and its contact
        _put(px, x + 1, 3, FE[4])
        for y in range(4, 10):                              # the winding
            _put(px, x, y, CU[3] if y % 2 == 0 else CU[2])
            _put(px, x + 1, y, CU[1] if y % 2 == 0 else CU[0])
        _put(px, x, 10, FE[5])                              # the yoke
        _put(px, x + 1, 10, FE[3])
        _stud(px, x, 12, KNOB)
    return px


def bus_switch():
    """A rotary bus selector: eight contact studs round a slate disc, the brass arm on one of them."""
    px = _plate(14)
    _dots(px, _round(7.5, 7.5, 5.9), FE[1])
    _turned(px, _round(7.5, 7.5, 5.9, inner=4.9), 7.5, 7.5, FE[0], FE[1], FE[4])    # sunk: the lower right lit
    for k in range(8):
        _put(px, *_clock(7.5, 7.5, 4.0, 22.5 + 45 * k), BR[3])
    _dots(px, [(8, 6), (8, 5)], BR[3])                      # the arm
    _put(px, 9, 4, BR[5])                                   # on its stud
    _stud(px, 7, 7, (FE[6], FE[5], FE[3]))                  # the knob
    return px


# ---- light faces -------------------------------------------------------------------------------------
def dial():
    """An indicating dial: porcelain in a brass bezel, a black scale and needle."""
    px = _plate(1)
    _turned(px, _round(7.5, 7.5, 5.9, inner=4.6), 7.5, 7.5, BR[4], BR[3], BR[1])
    face = _round(7.5, 7.5, 4.6)
    _dots(px, face, PC[3])
    _dots(px, [(x, y) for x, y in face if math.hypot(x - 7.5, y - 7.5) > 3.6 and (x - 7.5) + (y - 7.5) < -2.5],
          PC[2])                                            # the bezel's shadow on it
    # the scale: twelve, nine and three o'clock two pixels each, the two lower marks one; the upper
    # diagonals stay clear for the needle
    _dots(px, [(7, 4), (8, 4), (4, 7), (4, 8), (11, 7), (11, 8), (5, 10), (10, 10)], FE[0])
    _dots(px, [(9, 6), (10, 5)], FE[0])                     # the needle
    _stud(px, 7, 7, (BR[4], BR[2], BR[1]))                  # its hub
    return px


def gauges():
    """Two gauges on the pipe that feeds them, with its valve: a pressure gauge, and a gauge glass
    between its two cocks, half full. (Two round gauges side by side read as a pair of eyes.)"""
    px = _plate(15)
    glass = TRIO[2]
    _box(px, 4, 9, 4, 11, FE[5])                            # down from the pressure gauge
    _box(px, 4, 12, glass + 1, 12, FE[5])                   # along to the glass
    _box(px, 5, 13, glass + 1, 13, FE[3])
    _stud(px, 7, 11, KNOB)                                  # the valve
    _turned(px, _round(4.5, 5.5, 3.0), 4.5, 5.5, BR[4], BR[3], BR[1], edge=2.0)
    _dots(px, _round(4.5, 5.5, 2.0), PC[3])
    _dots(px, [(4, 6), (5, 5)], FE[0])                      # its needle
    for y in (3, 10):
        _stud(px, glass, y, (BR[4], BR[2], BR[1]))          # the cocks
    _box(px, glass, 5, glass, 6, PC[3])                     # the glass, empty above
    _box(px, glass + 1, 5, glass + 1, 6, PC[2])
    _box(px, glass, 7, glass, 9, PC[1])                     # and what stands in it
    _box(px, glass + 1, 7, glass + 1, 9, PC[0])
    return px


def recorder():
    """A drum recorder behind its window: the chart on the drum (lightest where the drum faces the
    light, darker as it turns away), the inked line, the brass pen arm at its end."""
    px = _plate(16)
    _sunk(px, 3, 3, 12, 10, CR[1])
    for x, tone in zip(range(3, 13), (0, 1, 2, 2, 1, 1, 1, 1, 0, 0)):
        _box(px, x, 4, x, 9, CR[tone])
    _box(px, 3, 3, 12, 3, FE[5])                            # the drum's flanges
    _box(px, 3, 10, 12, 10, FE[3])
    _dots(px, [(4, 7), (5, 7), (6, 6), (7, 6), (8, 7), (9, 8)], FE[1])     # the line so far
    _put(px, 10, 8, BR[5])                                  # the pen
    _dots(px, [(11, 7), (12, 6)], BR[4])                    # its arm
    _put(px, 12, 5, BR[2])
    _box(px, 3, 12, 6, 12, CR[1])                           # the label
    _stud(px, 11, 12, KNOB)                                 # the winding key
    return px


# ---- lit faces ---------------------------------------------------------------------------------------
def tubes(frame=0):
    """Three valves in a dark bay, their knobs under it. The filaments breathe, each a step behind
    the one before, so the three never swell together. The glass glows (GLOW); the dome above it
    and the brass base under it do not."""
    px = _plate(3)
    top, bottom = VALVE
    _sunk(px, 3, top - 1, 12, bottom + 1, FE[0])
    for k, x in enumerate(TRIO):
        heat = (0, 1, 2, 1)[(frame + k) % 4]
        _put(px, x, top - 1, FE[5])                         # the glass dome
        _put(px, x + 1, top - 1, FE[3])
        _box(px, x, top, x + 1, bottom, GL[1] if heat else GL[0])           # the envelope
        if heat:
            _box(px, x, top + 1, x + 1, bottom - 1, GL[2])
        _box(px, x, top + 1, x, top + 2, GL[2 + heat])      # the filament
        _put(px, x, bottom + 1, BR[2])                      # the base
        _put(px, x + 1, bottom + 1, BR[0])
        _stud(px, x, 12, KNOB)
    return px


def scope(frame=0):
    """An oscilloscope: the round screen in its sunk rim, the base line, the trace running across
    it; three knobs. The screen glows (GLOW), the rim does not. Where the beam climbs or falls
    fast it is dimmer, as on a real tube."""
    px = _plate(4)
    cx, cy, r = TUBE
    _turned(px, _round(cx, cy, r + 1.2, inner=r), cx, cy, FE[0], FE[1], FE[4])     # sunk: the lower right lit
    screen = set(GLOW["scope"])
    _dots(px, screen, PH[0])
    _dots(px, [(x, 7) for x in range(TILE) if x % 2 and (x, 7) in screen], FE[0])   # the base line, dotted

    def height(x):
        return int(math.floor(7.0 - 2.6 * math.sin(2 * math.pi * (x + frame) / 8.0)))

    for x in range(TILE):
        y, after = height(x), height(x + 1)
        for between in range(min(y, after) + 1, max(y, after)):
            if (x, between) in screen:
                _put(px, x, between, PH[2])
        if (x, y) in screen:
            _put(px, x, y, PH[3])
    for x in TRIO:
        _stud(px, x, 13, KNOB)
    return px


def pilot_lamps(frame=0):
    """Two rows of pilot lamps in a black field, a label under each column; which of them burn in
    a frame is _lamps. A lamp glows while it is on (glowing); out, it does not, and neither does
    the field."""
    px = _plate(9)
    _sunk(px, 3, 3, 12, 10, FE[0])
    for x, y, lamp, on in _lamps(frame):
        _stud(px, x, y, lamp[0] if on else lamp[1])
    for x in TRIO:
        _put(px, x, 12, CR[1])
        _put(px, x + 1, 12, CR[0])
    return px


# ---- the pack ----------------------------------------------------------------------------------------
FACES = {
    "dial": dial, "knife_switch": knife_switch, "tubes": tubes, "scope": scope, "counter": counter,
    "patch_panel": patch_panel, "fuses": fuses, "bell": bell, "pilot_lamps": pilot_lamps, "louvre": louvre,
    "drawers": drawers, "nameplate": nameplate, "relays": relays, "bus_switch": bus_switch, "gauges": gauges,
    "recorder": recorder,
}
FRAMES = {"tubes": 4, "scope": 8, "counter": 10, "pilot_lamps": 8}

# the tables above speak of the same sixteen kinds, and the lit rank is what GLOW lights
assert sorted(FACES) == sorted(B.PANELS) == sorted(n for names in RANKS.values() for n in names)
assert set(RANKS["lit"]) == set(GLOW) and len(GLOW) <= 4
assert set(FRAMES) == set(FRAMETIME) and set(SMOOTH) <= set(FRAMES)
# a lamp cannot fade out: blended, its pixels would be half empty, and the game draws a pixel or does not
assert set(OUT) <= set(GLOW) and not set(OUT) & set(SMOOTH)


def frames(name):
    """The pictures of one face in the order the game shows them: one, or the frames of an animated one."""
    return [FACES[name](f) for f in range(FRAMES[name])] if name in FRAMES else [FACES[name]()]


def picture(name):
    """A face as it goes into the pack: (pixels, meta). An animated one is its frames stacked downwards."""
    if name not in FRAMES:
        return FACES[name](), None
    animation = {"frametime": FRAMETIME[name]}
    if name in SMOOTH:
        animation["interpolate"] = True
    return np.concatenate(frames(name), axis=0), {"animation": animation}


def glow(name):
    """What glows on a lit face as a picture of its own: (pixels, meta). It is the face's picture,
    frame for frame and on the same beat, and empty (alpha 0) wherever the face does not glow in
    that frame (glowing). The colours stay under the empty pixels, so whatever the game mixes into
    the rim of a lamp where it samples between two pixels is the plate beside the lamp and never
    black."""
    pixels, meta = picture(name)
    pixels = pixels.copy()
    pixels[..., 3] = 0
    for frame in range(len(pixels) // TILE):
        for x, y in glowing(name, frame):
            pixels[frame * TILE + y, x, 3] = 255
    return pixels, meta


def _mount(lamps=None):
    """What redirect does to the game's model before it maps the pictures (its `edit`): the turn the
    game gives each face of glazed terracotta goes, so the instrument stands upright; and a face
    that glows gets a second front, in the same place and of the same size as the first, that shows
    the picture `lamps` (see glow) at full brightness and without the shading by direction: a lamp
    is as bright on a wall to the east as on one to the south.

    The game does not draw the empty part of a picture, so the first front shows through everywhere
    but on the glowing pixels; its own models do the same (the fringe on the side of the grass
    block, block/cross_emissive). The two fronts have the same four corners, like the two on each
    side of the grass block: they lie at exactly the same depth, where the game shows the one it
    draws later, the one with the holes. No seam is cut into the face or left against the blocks
    beside it."""
    def edit(ref, flat):
        boxes = flat["elements"] or []
        for box in boxes:
            for face in box["faces"].values():
                face.pop("rotation", None)
        if lamps:
            (cube,) = boxes
            front = dict(cube["faces"]["south"], texture=f"{K.NS}:block/{lamps}")
            boxes.append({"from": list(cube["from"]), "to": list(cube["to"]), "faces": {"south": front},
                          "light_emission": LIT, "shade_direction_override": "up"})
        return flat
    return edit


def pack(pack_dir):
    out = []
    K.paint(pack_dir, "panel_case", case())
    for name in FACES:
        pixels, meta = picture(name)
        K.paint(pack_dir, f"panel_{name}", pixels, meta=meta)
    for name in GLOW:
        pixels, meta = glow(name)
        K.paint(pack_dir, f"panel_{name}_glow", pixels, meta=meta)
    for name, block in B.PANELS.items():
        textures = {ref: {"south": f"panel_{name}", "*": "panel_case"}
                    for ref in respack.block_pictures(K.game(), block)}
        lamps = f"panel_{name}_glow" if name in GLOW else None
        out.append(K.redirect(pack_dir, block, textures, edit=_mount(lamps)))
    return out
