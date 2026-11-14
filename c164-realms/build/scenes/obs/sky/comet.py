"""The pictures in the sky: the comet in the moon's slot, the sun's slot blanked.

Card plan/packages/sky/comet.md. Three versions to choose from, one painting function with one
shared table (STYLES):

    a  jia   a soft long tail: a fine smooth coma and a long smooth dust tail; only the nucleus is
             made of hard pixels.
    b  yi    hard pixels: the whole sprite on a 64 grid in five brightness levels, drawn the way the
             vanilla sun and moon are.
    c  bing  a wide fan: a short, wide, strongly outlined tail.

How the moon slots are used:

    moon/<phase>.png   eight slots; the timeline's moon_phase picks one (mood.LOOKS). For the map,
                       pack() paints the one chosen version into every slot, brighter and longer in
                       the deep night, fainter and shorter in the strong afterglow. For the
                       comparison scene pack(compare=True) puts the three versions in the three
                       looks' slots, so one walk of the timeline shows all three.
    moon/new_moon.png  a test card for a few ticks in the morning (mood.TRIALS["card"]): which way up
                       the game draws the picture is read off it.
    sun.png            black: the textures are added onto the sky, black draws nothing. The hour is
                       after sunset; whatever is ever painted here must not read as a sun's disc.

The moon's square is 22.6 degrees wide and always due west of the viewer, its centre 90 - moon_angle
up (moon_angle 42 -> centre 48, head 41). Seen from V2 on the axis the dome apex is ~33 up, so the
head is ~8 above it, the card's rule. The comet is painted as the player sees it facing west (up is
up, right is north) and turned into the file's orientation by seen_to_moon_file().

Colours (added light, black = nothing): the nucleus takes the two brightest glow steps, the dust
tail fades from a warm white to a blue-violet, the ion tail is night_glass's brightest step. Sky
textures are added onto the sky, so the stray-colour check skips them (sky.md section 7).
"""
import numpy as np

from artkit import respack

from scenes.obs.common import palette as P

from . import mood

SIZE = 256
SPAN = 22.62                 # degrees across the moon's square
HEAD_BELOW = 7.0             # the head sits this far below the centre of the square; tails go up

# brightness and length of the chosen comet in each light version (pack(), the map). deep is the
# brightest and longest, glow the faintest and shortest, so the three are told apart at a stamp.
STRENGTH = {"blue": 1.0, "deep": 1.45, "glow": 0.6}
TAIL = {"blue": 1.0, "deep": 1.25, "glow": 0.72}

PHASES = ("full_moon", "waning_gibbous", "third_quarter", "waning_crescent", "new_moon",
          "waxing_crescent", "first_quarter", "waxing_gibbous")
CARD_PHASE = mood.TRIALS["card"]["moon_phase"]

# comparison scene: one version per light version, in that look's moon slot
COMPARE = {"blue": "a", "deep": "b", "glow": "c"}
DEFAULT_STYLE = "a"          # the version pack() paints for the map; the review sets which one

NUCLEUS = (P.RAMPS["glow"][-1], P.RAMPS["glow"][-2])    # the two brightest glow steps
DUST_WARM = P.RAMPS["glow"][-2]                         # warm white near the head
DUST_COLD = "#7c82c8"                                   # a blue-violet at the tip
ION = P.RAMPS["night_glass"][-1]                        # the brightest night_glass step

# One shared table. Each version is a smooth comet (dust tail + ion tail + coma + nucleus); "b" is
# then rounded onto the 64 grid in five levels. Lengths are in degrees, widths the Gaussian sigma.
STYLES = {
    "a": dict(coma=1.15, coma_amp=0.90, dust_len=17.0, dust_w0=0.50, dust_wg=2.3, dust_fall=2.5,
              curve=0.020, dust_amp=0.60, ion_len=19.0, ion_w=0.30, ion_lean=0.05, ion_fall=1.7,
              ion_amp=0.50, levels=0,
              nucleus=((0, 0, 1.0), (-1, 0, .70), (1, 0, .70), (0, -1, .65), (0, 1, .65), (-2, 0, .40))),
    "b": dict(coma=1.00, coma_amp=1.00, dust_len=13.5, dust_w0=0.75, dust_wg=1.9, dust_fall=2.2,
              curve=0.016, dust_amp=0.72, ion_len=14.0, ion_w=0.50, ion_lean=0.04, ion_fall=2.0,
              ion_amp=0.58, levels=5,
              nucleus=((0, 0, 1.0), (-1, 0, .80), (1, 0, .80), (0, -1, .80), (0, 1, .80), (-2, 0, .50), (-2, 1, .40))),
    "c": dict(coma=1.30, coma_amp=0.85, dust_len=10.5, dust_w0=1.15, dust_wg=3.7, dust_fall=1.7,
              curve=0.012, dust_amp=0.68, ion_len=9.5, ion_w=0.62, ion_lean=0.03, ion_fall=2.2,
              ion_amp=0.50, levels=0,
              nucleus=((0, 0, 1.0), (-1, 0, .85), (1, 0, .85), (0, -1, .80), (0, 1, .80))),
}


def _rgb(text):
    return np.array([int(text[i:i + 2], 16) for i in (1, 3, 5)], dtype=float) / 255.0


def seen_to_moon_file(seen):
    """The moon's quad shows its file upside down to a viewer facing west (derived from the vertex
    order in SkyRenderer; the test card confirms it on the real client)."""
    return seen[::-1].copy()


def _grid(n=SIZE):
    deg = SPAN / n
    rows, cols = np.meshgrid(np.arange(n) + 0.5, np.arange(n) + 0.5, indexing="ij")
    x = (cols - n * 0.5) * deg                       # degrees right (north) of the head
    y = (n * 0.5 - rows) * deg + HEAD_BELOW          # degrees above the head
    edge = np.minimum(np.minimum(cols, n - cols), np.minimum(rows, n - rows)) / (n * 0.06)
    return x, y, np.clip(edge, 0.0, 1.0)


def _nucleus(out, p, n):
    """A few hard pixels of the 64 grid at the head: the two brightest glow steps."""
    cell = max(1, n // 64)
    row = int((n * 0.5 + HEAD_BELOW / (SPAN / n)) // cell)
    col = int((n * 0.5) // cell)
    hot, warm = _rgb(NUCLEUS[0]), _rgb(NUCLEUS[1])
    for dr, dc, a in p["nucleus"]:
        r0, c0 = (row + dr) * cell, (col + dc) * cell
        if 0 <= r0 < n and 0 <= c0 < n:
            colour = hot if a >= 0.9 else warm
            out[r0:r0 + cell, c0:c0 + cell] = np.maximum(out[r0:r0 + cell, c0:c0 + cell], colour * a)
    return out


def _quantise(out, levels, n):
    """Round the sprite onto the 64 grid in `levels` brightness steps, keeping hue; a vanilla look."""
    cell = max(1, n // 64)
    m = n // cell
    small = out.reshape(m, cell, m, cell, 3).mean(axis=(1, 3))
    mag = small.max(axis=-1, keepdims=True)
    step = np.ceil(np.clip(mag, 0.0, 1.0) * (levels - 1)) / (levels - 1)
    small = np.where(mag > 1e-4, small * (step / np.maximum(mag, 1e-4)), 0.0)
    return np.repeat(np.repeat(small, cell, axis=0), cell, axis=1)


def comet(style="a", strength=1.0, tail=1.0, n=SIZE):
    """One version of the comet as seen (up is up, right is north). Floats 0..1, (n, n, 3); the
    values are light added onto the sky."""
    p = STYLES[style]
    x, y, edge = _grid(n)
    up = np.clip(y, 0.0, None)

    t = np.clip(up / (p["dust_len"] * tail), 0.0, 1.25)
    centre = p["curve"] * up ** 1.4                       # the dust tail leans and curves north (+x)
    width = p["dust_w0"] + p["dust_wg"] * t
    dust = np.exp(-0.5 * ((x - centre) / width) ** 2) * np.exp(-p["dust_fall"] * t) * (y > -0.2)
    dust *= np.clip((1.2 - t) / 0.25, 0.0, 1.0)

    s = np.clip(up / (p["ion_len"] * tail), 0.0, 1.25)
    ion = np.exp(-0.5 * ((x - p["ion_lean"] * up) / p["ion_w"]) ** 2) * np.exp(-p["ion_fall"] * s) * (y > 0.2)
    ion *= np.clip((1.2 - s) / 0.2, 0.0, 1.0)

    coma = np.exp(-np.hypot(x, y) / p["coma"])

    warm, cold = _rgb(DUST_WARM), _rgb(DUST_COLD)
    mix = np.clip(t, 0.0, 1.0)[..., None]
    out = (warm * (1.0 - mix) + cold * mix) * (p["dust_amp"] * dust)[..., None]
    out = out + _rgb(ION) * (p["ion_amp"] * ion)[..., None]
    out = out + _rgb(NUCLEUS[1]) * (p["coma_amp"] * coma)[..., None]
    out = _nucleus(out, p, n)

    out = out * strength
    if p["levels"]:
        out = _quantise(out, p["levels"], n)
    return np.clip(out * edge[..., None], 0.0, 1.0)


def test_card(n=SIZE):
    """As seen facing west: an arrow pointing up, a square dot to its right (north), a dim frame.
    Any flip or quarter turn of the file shows as the arrow or the dot being somewhere else."""
    out = np.zeros((n, n, 3))
    u = n // 32
    out[:u], out[-u:], out[:, :u], out[:, -u:] = 0.25, 0.25, 0.25, 0.25
    mid = n // 2
    out[8 * u:26 * u, mid - u:mid + u] = _rgb(NUCLEUS[0])            # shaft
    for k in range(6 * u):                                          # head
        out[4 * u + k, mid - k:mid + k + 1] = _rgb(NUCLEUS[0])
    out[14 * u:18 * u, mid + 6 * u:mid + 10 * u] = _rgb("#ffc65a")  # dot on the north side
    return out


def _by_phase(compare):
    """{phase: seen (n, n, 3)} before the file flip."""
    if compare:
        chosen = {v["moon_phase"]: comet(COMPARE[name]) for name, v in mood.LOOKS.items()}
    else:
        chosen = {v["moon_phase"]: comet(DEFAULT_STYLE, STRENGTH[name], TAIL[name])
                  for name, v in mood.LOOKS.items()}
    default = chosen[mood.LOOKS[mood.DEFAULT]["moon_phase"]]
    out = {}
    for phase in PHASES:
        out[phase] = test_card() if phase == CARD_PHASE else chosen.get(phase, default)
    return out


def pictures(compare=False):
    """{phase: (n, n, 3) uint8 in the file's orientation}."""
    return {ph: (seen_to_moon_file(seen) * 255.0 + 0.5).astype(np.uint8)
            for ph, seen in _by_phase(compare).items()}


def pack(pack_dir, compare=False):
    out = []
    for phase, px in pictures(compare).items():
        respack.texture(pack_dir, "environment/celestial/moon/" + phase, px)
    if compare:
        out.append("comet comparison: a->full_moon (14000), b->waning_gibbous (18000), "
                   f"c->third_quarter (12900); test card in {CARD_PHASE}")
    else:
        out.append(f"comet ({DEFAULT_STYLE}) -> {len(PHASES)} moon phase pictures, test card in {CARD_PHASE}")
    respack.texture(pack_dir, "environment/celestial/sun", np.zeros((16, 16, 3), dtype=np.uint8))
    out.append("sun picture blanked")
    return out
