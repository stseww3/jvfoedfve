"""The pictures in the sky: the comet in the moon's slot, the sun's slot blanked.

PLACEHOLDER written with the look (card sky/look) so that every early picture has a plausible sky;
the card sky/comet replaces the painting with the three versions to choose from. What stays is how
the slots are used:

    moon/<phase>.png   eight slots, the timeline's moon_phase picks one (mood.LOOKS): one comet per
                       light version, longer and brighter in the deep night, short and faint in the
                       strong afterglow
    moon/new_moon.png  a test card for a few ticks in the morning (mood.TRIALS["card"]), to check on
                       the real client which way up the game draws these pictures
    sun.png            black: the textures are added onto the sky, black draws nothing. The hour is
                       after sunset; whatever is ever painted here must not read as a sun's disc.

The moon's square is 22.6 degrees wide (the sun's 33.4) and always due west of the viewer at the
elevation 90 - moon_angle. Pictures are painted the way the player sees them facing west (up is up,
right is north) and turned into the file's orientation by seen_to_moon_file().
"""
import math

import numpy as np

from artkit import respack

from . import mood

SIZE = 256
SPAN = 22.62                 # degrees across the moon's square
HEAD_BELOW = 7.0             # the head sits this far below the centre of the square, tails go up
STRENGTH = {"blue": 1.0, "deep": 1.5, "glow": 0.55}        # how bright each look's comet is
TAIL = {"blue": 1.0, "deep": 1.25, "glow": 0.7}             # and how long its tails
PHASES = ("full_moon", "waning_gibbous", "third_quarter", "waning_crescent", "new_moon",
          "waxing_crescent", "first_quarter", "waxing_gibbous")
WHITE, CREAM, BLUE = "#fff8dc", "#ffe9a6", "#7f93d8"
CARD_PHASE = mood.TRIALS["card"]["moon_phase"]


def _rgb(text):
    return np.array([int(text[i:i + 2], 16) for i in (1, 3, 5)], dtype=float) / 255.0


def seen_to_moon_file(seen):
    """The moon's quad shows its file upside down to a viewer facing west (derived from the vertex
    order in SkyRenderer; the test card is there to confirm it)."""
    return seen[::-1].copy()


def _grid(n=SIZE):
    deg = SPAN / n
    rows, cols = np.meshgrid(np.arange(n) + 0.5, np.arange(n) + 0.5, indexing="ij")
    x = (cols - n * 0.5) * deg                       # degrees right (north) of the head
    y = (n * 0.5 - rows) * deg + HEAD_BELOW          # degrees above the head
    edge = np.minimum(np.minimum(cols, n - cols), np.minimum(rows, n - rows)) / (n * 0.06)
    return x, y, np.clip(edge, 0.0, 1.0)


def comet(strength=1.0, tail=1.0, n=SIZE):
    """A plain comet as seen: a small bright head, one dust tail leaning north, a thin blue ion
    tail. Floats 0..1, (n, n, 3); the amounts are light added onto the sky."""
    x, y, edge = _grid(n)
    t = np.clip(y / (16.0 * tail), 0.0, 1.2)
    centre = math.tan(math.radians(12.0)) * y + 2.2 * t * t
    dust = np.exp(-0.5 * ((x - centre) / (0.55 + 2.3 * t)) ** 2) * np.exp(-2.6 * t) * (y > -0.3)
    dust *= np.clip((1.15 - t) / 0.25, 0.0, 1.0)
    ion = np.exp(-0.5 * ((x + math.tan(math.radians(4.0)) * y) / 0.32) ** 2) * np.exp(-1.7 * np.clip(y / (18.0 * tail), 0.0, 2.0))
    ion *= (y > 0.2) * np.clip((18.0 * tail - y) / 3.0, 0.0, 1.0)
    coma = np.exp(-np.hypot(x, y) / 0.9)
    out = _rgb(CREAM) * (0.62 * dust)[..., None] + _rgb(BLUE) * (0.45 * ion)[..., None] + _rgb(WHITE) * (0.9 * coma)[..., None]
    cell = n // 64                                   # the nucleus: a few hard pixels of the 64 grid
    row, col = int((n * 0.5 + HEAD_BELOW / (SPAN / n)) // cell), int((n * 0.5) // cell)
    for dr, dc, a in ((0, 0, 1.0), (-1, 0, 0.8), (1, 0, 0.8), (0, -1, 0.8), (0, 1, 0.8), (-2, 0, 0.5), (-2, 1, 0.36)):
        r0, c0 = (row + dr) * cell, (col + dc) * cell
        out[r0:r0 + cell, c0:c0 + cell] = np.maximum(out[r0:r0 + cell, c0:c0 + cell], _rgb(WHITE) * a)
    return np.clip(out * strength * edge[..., None], 0.0, 1.0)


def test_card(n=SIZE):
    """As seen facing west: an arrow pointing up, a square dot to its right (north), a dim frame.
    Any flip or quarter turn of the file shows as the arrow or the dot being somewhere else."""
    out = np.zeros((n, n, 3))
    u = n // 32
    out[:u], out[-u:], out[:, :u], out[:, -u:] = 0.25, 0.25, 0.25, 0.25
    mid = n // 2
    out[8 * u:26 * u, mid - u:mid + u] = _rgb(WHITE)                 # shaft
    for k in range(6 * u):                                           # head
        out[4 * u + k, mid - k:mid + k + 1] = _rgb(WHITE)
    out[14 * u:18 * u, mid + 6 * u:mid + 10 * u] = _rgb("#ffb45e")   # dot on the north side
    return out


def pictures():
    """{phase: (n, n, 3) uint8 in the file's orientation}."""
    by_phase = {v["moon_phase"]: comet(STRENGTH[name], TAIL[name]) for name, v in mood.LOOKS.items()}
    default = by_phase[mood.LOOKS[mood.DEFAULT]["moon_phase"]]
    out = {}
    for phase in PHASES:
        seen = test_card() if phase == CARD_PHASE else by_phase.get(phase, default)
        out[phase] = (seen_to_moon_file(seen) * 255.0 + 0.5).astype(np.uint8)
    return out


def pack(pack_dir):
    out = []
    for phase, px in pictures().items():
        respack.texture(pack_dir, "environment/celestial/moon/" + phase, px)
    out.append(f"comet (placeholder) -> {len(PHASES)} moon phase pictures, test card in {CARD_PHASE}")
    respack.texture(pack_dir, "environment/celestial/sun", np.zeros((16, 16, 3), dtype=np.uint8))
    out.append("sun picture blanked")
    return out
