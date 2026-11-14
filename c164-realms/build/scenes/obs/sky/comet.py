"""The pictures in the sky: the comet in the moon's slot, the sun's slot blanked.

Card plan/packages/sky/comet.md. Three versions to choose from, painted by one function from one
table (STYLES):

    a  jia   a soft long tail: a small coma and long smooth tails; only the nucleus is big pixels
    b  yi    hard pixels: the whole sprite on the 64 grid in five levels of brightness, flat tones
             with stepped outlines, the way the vanilla sun and moon are drawn
    c  bing  a wide fan: a short, wide dust tail with a firmer outline

The anatomy is the same in all three: a nucleus of a few big pixels; a small coma; a dust tail that
leans and curves north, warm white at the head and cooling towards its tip; a thin straight blue
ion tail that parts from it on the south side.

How the moon's slots are used:

    moon/<phase>.png   eight slots; the timeline's moon_phase picks one (mood.LOOKS). pack() paints
                       one version into all of them: brighter and longer in the deep night, fainter
                       and shorter in the strong afterglow (STRENGTH, TAIL), the other five as in
                       the blue hour. The versions are compared scene by scene (obs_sky_comet,
                       obs_sky_comet_b, obs_sky_comet_c), each under all three lights.
    moon/new_moon.png  a test card for a few ticks in the morning (mood.TRIALS["card"]): which way
                       up the game draws the picture is read off it
    sun.png            black: the textures are added onto the sky, black draws nothing. The hour is
                       after sunset; whatever is ever painted here must not read as a sun's disc.

Where it stands. The moon's square is 22.6 degrees wide and always due west of the viewer, its
centre 90 - moon_angle up. The head sits 7 degrees below the centre (HEAD_ELEVATION, 41 degrees with
moon_angle 42: 8 above the apex of the great dome seen from V2), the tails go up and end inside the
square in every light (the longest, in the deep night, 1.4 degrees short of its top edge).

Which way up. The comet is painted as the player sees it facing west (up is up, right is north)
and turned into the file's orientation by seen_to_moon_file(). Read off the 26.3 client's
SkyRenderer: sun and moon stand at height 100 under rotateY(-90) rotateX(angle), which carries the
quad's +x to the south (the viewer's left) and its +z towards the horizon; buildMoonPhases gives
x = -1 the sprite's U1 and z = -1 its V1, so the moon's file shows upside down and not mirrored
(the sun's file shows mirrored and not upside down). The test card is there to see it in the game.

How bright. The values are light added onto the sky. Outside the nucleus nothing adds more than
CEILING, so that on the darkest sky the comet stays under the lit windows (0.79 on the ladder of
plan/parts/sky.md section 4); report() measures it for every version and light.

Colours: the nucleus takes the two brightest glow steps, the dust tail runs from the warm white of
glow to the brightest night_glass step, which is also the ion tail's blue. The palette has no
blue-violet of its own; the dust's cool end is asked for in the group if this one will not do.
"""
import math

import numpy as np

from artkit import respack

from scenes.obs.common import palette as P

from . import mood

SIZE = 256
GRID = 64                    # the big pixels: the nucleus in every version, all of version b
SPAN = 22.62                 # degrees across the moon's square (half-size 20 at distance 100)
HEAD_BELOW = 7.0             # the head sits this far below the centre of the square; tails go up
DEFAULT_STYLE = "a"          # the version pack() paints for the map; the review settles it

# brightness and length of the comet in each light version: deep is the brightest and longest, glow
# the faintest and shortest, so that the three are told apart at the size of a stamp
STRENGTH = {"blue": 1.0, "deep": 1.45, "glow": 0.6}
TAIL = {"blue": 1.0, "deep": 1.25, "glow": 0.72}

LIT_WINDOW = 0.79            # the lit windows on the brightness ladder (grey 0..1, look blue)
CEILING = 0.70               # the most light anything outside the nucleus adds
KNEE = 0.45                  # light above this is eased towards the ceiling
END = 0.30                   # a tail dims evenly along its length and dies away over this last share

PHASES = ("full_moon", "waning_gibbous", "third_quarter", "waning_crescent", "new_moon",
          "waxing_crescent", "first_quarter", "waxing_gibbous")
CARD_PHASE = mood.TRIALS["card"]["moon_phase"]
SUN_SIZE = 128

HOT, WARM = P.RAMPS["glow"][-1], P.RAMPS["glow"][-2]    # the nucleus; warm is also coma and dust
COOL = P.RAMPS["night_glass"][-1]                       # the ion tail; what the dust cools to

_CELL = SIZE // GRID
HEAD_ROW = int((SIZE * 0.5 + HEAD_BELOW / (SPAN / SIZE)) // _CELL)      # grid cell of the nucleus
HEAD_COL = GRID // 2


def _above_centre(rows_px):
    """Degrees above the centre of the square for a height in the picture (the quad is flat)."""
    return math.degrees(math.atan((SIZE * 0.5 - rows_px) / (SIZE * 0.5) * 0.2))


# elevation of the head, due west, for every viewer: telescopes and cameras read it here
HEAD_ELEVATION = 90.0 - mood.MOON_ANGLE + _above_centre((HEAD_ROW + 0.5) * _CELL)

# One table for the three versions. Lengths and widths in degrees; a width is the sigma across the
# tail, given at the head and at the tip. Amplitudes are grey (luma) added at strength 1.
#   coma        radius where the coma has fallen to 1/e      coma_amp   its light at the nucleus
#   dust_len    where the dust tail ends                      dust_w     (at the head, at the tip)
#   flare       how the width grows along the tail (1 evenly, less: early)
#   lean, curve the tail's centre line north of the head: lean * up + curve * up^2
#   edge        2 a Gaussian across the tail; more: a flatter middle and a firmer outline
#   dust_fall   how fast it dims along its length           cool       how late it cools (1 evenly)
#   ion_*       the same for the straight ion tail; ion_lean negative: it parts to the south
#   nucleus     big pixels (rows up, columns north, brightness); 0.9 and more take the hottest step
#   steps, tones, cooling   version b only: the light at which each level begins, the grey each
#               level shows, and how far towards the cool end each level of the dust tail stands
STYLES = {
    "a": dict(coma=0.55, coma_amp=0.30, dust_len=12.5, dust_w=(0.30, 1.25), flare=1.0, lean=0.14,
              curve=0.012, edge=2.0, dust_fall=1.6, dust_amp=0.30, cool=1.2,
              ion_len=13.5, ion_w=(0.16, 0.42), ion_lean=-0.035, ion_fall=1.2, ion_amp=0.20,
              nucleus=((0, 0, 1.0), (1, 0, .72), (-1, 0, .72), (0, 1, .72), (0, -1, .72), (2, 0, .50))),
    "b": dict(coma=0.60, coma_amp=0.36, dust_len=11.5, dust_w=(0.40, 1.45), flare=1.0, lean=0.14,
              curve=0.014, edge=2.0, dust_fall=1.3, dust_amp=0.34, cool=1.0,
              ion_len=12.0, ion_w=(0.22, 0.40), ion_lean=-0.05, ion_fall=1.0, ion_amp=0.24,
              nucleus=((0, 0, 1.0), (1, 0, .56), (-1, 0, .56), (0, 1, .56), (0, -1, .56)),
              steps=(0.075, 0.15, 0.27), tones=(0.14, 0.23, 0.36), cooling=(0.75, 0.40, 0.0)),
    "c": dict(coma=0.75, coma_amp=0.32, dust_len=9.5, dust_w=(0.55, 2.70), flare=0.8, lean=0.10,
              curve=0.016, edge=3.2, dust_fall=1.1, dust_amp=0.30, cool=1.0,
              ion_len=9.0, ion_w=(0.20, 0.50), ion_lean=-0.12, ion_fall=1.3, ion_amp=0.20,
              nucleus=((0, 0, 1.0), (1, 0, .72), (-1, 0, .72), (0, 1, .72), (0, -1, .72))),
}

_LUMA = np.array([0.299, 0.587, 0.114])


def _rgb(text):
    return np.array([int(text[i:i + 2], 16) for i in (1, 3, 5)], dtype=float) / 255.0


def _unit(text):
    """A palette colour scaled to grey 1: amplitudes then say how much light, the colour which."""
    c = _rgb(text)
    return c / (c @ _LUMA)


def luma(picture):
    return picture @ _LUMA


def seen_to_moon_file(picture):
    """The moon's quad shows its file upside down to a viewer facing west (the module's notes)."""
    return picture[::-1].copy()


def _grid(m):
    """Degrees north of the head and above it at the centres of an m x m grid, and the fade that
    keeps the outer 6 percent of the square black. One degree is one at the square's centre."""
    deg = SPAN / m
    k = m / GRID
    rows, cols = np.meshgrid(np.arange(m) + 0.5, np.arange(m) + 0.5, indexing="ij")
    x = (cols - (HEAD_COL + 0.5) * k) * deg
    y = ((HEAD_ROW + 0.5) * k - rows) * deg
    edge = np.minimum(np.minimum(cols, m - cols), np.minimum(rows, m - rows)) / (m * 0.06)
    return x, y, np.clip(edge, 0.0, 1.0)


def _ramp(v, lo, hi):
    s = np.clip((v - lo) / (hi - lo), 0.0, 1.0)
    return s * s * (3.0 - 2.0 * s)


def _fields(p, tail, m):
    """The smooth comet on an m x m grid: the grey added by coma, dust tail and ion tail, and how
    far along the dust tail each point lies (0 at the head, 1 at the tip)."""
    x, y, edge = _grid(m)
    up = np.clip(y, 0.0, None)

    t = np.clip(up / (p["dust_len"] * tail), 0.0, 1.0)
    centre = p["lean"] * up + p["curve"] * up * up
    w0, w1 = p["dust_w"]
    across = np.abs((x - centre) / (w0 + (w1 - w0) * t ** p["flare"]))
    dust = np.exp(-0.5 * across ** p["edge"]) * np.exp(-p["dust_fall"] * t) * _ramp(1.0 - t, 0.0, END)
    dust *= _ramp(y, -0.35, 0.35)

    s = np.clip(up / (p["ion_len"] * tail), 0.0, 1.0)
    i0, i1 = p["ion_w"]
    ion = np.exp(-0.5 * ((x - p["ion_lean"] * up) / (i0 + (i1 - i0) * s)) ** 2)
    ion *= np.exp(-p["ion_fall"] * s) * _ramp(1.0 - s, 0.0, END) * _ramp(y, 0.0, 0.7)

    coma = np.exp(-(np.hypot(x, np.where(y > 0.0, 0.8 * y, y)) / p["coma"]) ** 1.5)
    return p["coma_amp"] * coma * edge, p["dust_amp"] * dust * edge, p["ion_amp"] * ion * edge, t


def _hold(picture):
    """Ease whatever adds more than KNEE towards CEILING, keeping its colour."""
    grey = luma(picture)
    room = CEILING - KNEE
    held = np.where(grey > KNEE, KNEE + room * (1.0 - np.exp(-(grey - KNEE) / room)), grey)
    return picture * (held / np.maximum(grey, 1e-9))[..., None]


def _nucleus_cells(p):
    return [(HEAD_ROW - up, HEAD_COL + north, b) for up, north, b in p["nucleus"]]


def _nucleus(picture, p, strength):
    """The few big pixels of the head, laid over the rest where they are the brighter."""
    cell = picture.shape[0] // GRID
    for row, col, b in _nucleus_cells(p):
        colour = _rgb(HOT if b >= 0.9 else WARM) * min(1.0, b * math.sqrt(strength))
        at = (slice(row * cell, (row + 1) * cell), slice(col * cell, (col + 1) * cell))
        picture[at] = np.maximum(picture[at], colour)
    return picture


def _smooth(p, strength, tail, n):
    coma, dust, ion, t = _fields(p, tail, n)
    warm, cool = _unit(WARM), _unit(COOL)
    mix = (t ** p["cool"])[..., None]
    out = (warm * (1.0 - mix) + cool * mix) * dust[..., None] + cool * ion[..., None] + warm * coma[..., None]
    return _hold(out * strength)


def _stepped(p, strength, tail, n):
    """Version b: the smooth comet read at the centres of the big pixels and rounded down to the
    level it reaches; under the first step nothing is drawn. Each level is one flat tone."""
    coma, dust, ion, _ = _fields(p, tail, GRID)
    body = coma + dust
    level = np.searchsorted(np.array(p["steps"]), body + ion, side="right")      # 0 nothing, 1.. the levels
    warm, cool = _unit(WARM), _unit(COOL)
    tones = [np.zeros(3)] + [(warm * (1.0 - c) + cool * c) * g for g, c in zip(p["tones"], p["cooling"])]
    blues = [np.zeros(3)] + [cool * g for g in p["tones"]]
    small = np.where((ion > body)[..., None], np.array(blues)[level], np.array(tones)[level])
    cell = n // GRID
    return _hold(np.repeat(np.repeat(small, cell, axis=0), cell, axis=1) * strength)


def comet(style=DEFAULT_STYLE, strength=1.0, tail=1.0, n=SIZE):
    """One version of the comet as seen (up is up, right is north). Floats 0..1, (n, n, 3); the
    values are light added onto the sky."""
    p = STYLES[style]
    out = (_stepped if "steps" in p else _smooth)(p, strength, tail, n)
    return np.clip(_nucleus(out, p, strength), 0.0, 1.0)


def test_card(n=SIZE):
    """As seen facing west: an arrow pointing up, a square dot to its right (north), a dim frame.
    Any flip or quarter turn of the file shows as the arrow or the dot being somewhere else."""
    out = np.zeros((n, n, 3))
    u = n // 32
    out[:u], out[-u:], out[:, :u], out[:, -u:] = 0.25, 0.25, 0.25, 0.25
    mid = n // 2
    out[8 * u:26 * u, mid - u:mid + u] = _rgb(HOT)                   # shaft
    for k in range(6 * u):                                           # head
        out[4 * u + k, mid - k:mid + k + 1] = _rgb(HOT)
    out[14 * u:18 * u, mid + 6 * u:mid + 10 * u] = _rgb(P.RAMPS["glow"][2])   # dot on the north side
    return out


def seen(style=DEFAULT_STYLE):
    """{phase: (n, n, 3) floats as seen}: the comet of each light in its phase, the blue hour's in
    the phases no light uses, the test card in its own."""
    by_look = {v["moon_phase"]: comet(style, STRENGTH[name], TAIL[name]) for name, v in mood.LOOKS.items()}
    default = by_look[mood.LOOKS[mood.DEFAULT]["moon_phase"]]
    return {phase: test_card() if phase == CARD_PHASE else by_look.get(phase, default) for phase in PHASES}


def pictures(style=DEFAULT_STYLE):
    """{phase: (n, n, 3) uint8 in the file's orientation}."""
    return {phase: (seen_to_moon_file(px) * 255.0 + 0.5).astype(np.uint8) for phase, px in seen(style).items()}


def pack(pack_dir, style=DEFAULT_STYLE):
    for phase, px in pictures(style).items():
        respack.texture(pack_dir, "environment/celestial/moon/" + phase, px)
    respack.texture(pack_dir, "environment/celestial/sun", np.zeros((SUN_SIZE, SUN_SIZE, 3), dtype=np.uint8))
    return [f"comet ({style}) -> {len(PHASES)} moon phase pictures, test card in {CARD_PHASE}",
            "sun picture blanked"]


def sky_behind(look, elevation=None):
    """Grey of the sky where the comet stands (sky.fsh: the sky colour overhead takes the fog
    colour by distance over a disc 16 blocks up; mood states what is seen at zenith and horizon)."""
    v = mood.LOOKS[look]
    e = math.radians(HEAD_ELEVATION if elevation is None else elevation)
    reach = 16.0 / math.tan(e)
    f = min(1.0, (16.0 + 496.25 * reach / 512.0) / v["sky_fog_end"])
    z = 16.0 / v["sky_fog_end"]
    zenith, horizon = _rgb(v["zenith"]), _rgb(v["horizon"])
    return float((zenith + (horizon - zenith) * (f - z) / (1.0 - z)) @ _LUMA)


def report(style):
    """What the card asks of the picture, measured for every light: a list of dicts.

    peak        the most grey added outside the nucleus      on_sky   that plus the sky behind it
    tip         elevation where the tails end                 margin   degrees left to the top edge
    area, bright   square degrees adding 0.03 and more, 0.20 and more
    frame       the bright part as a share of a 16:9 picture at fov 70 when the comet is in its
                middle (the card allows 0.5 percent)
    border      True when the outer 3 percent of the square is black
    """
    cell = SIZE // GRID
    out = []
    for look in mood.LOOKS:
        px = comet(style, STRENGTH[look], TAIL[look])
        grey = luma(px)
        body = grey.copy()
        for row, col, _ in _nucleus_cells(STYLES[style]):
            body[row * cell:(row + 1) * cell, col * cell:(col + 1) * cell] = 0.0
        lit = np.nonzero((grey > 0.02).any(axis=1))[0]
        top = _above_centre(float(lit[0]))
        deg2 = (SPAN / SIZE) ** 2
        rim = int(SIZE * 0.03)
        inner = np.zeros_like(grey, dtype=bool)
        inner[rim:-rim, rim:-rim] = True
        frame = 4.0 * math.tan(math.radians(35.0)) ** 2 * 16.0 / 9.0 * math.degrees(1.0) ** 2
        out.append(dict(
            look=look, peak=float(body.max()), on_sky=float(body.max()) + sky_behind(look),
            tip=90.0 - mood.MOON_ANGLE + top, margin=SPAN * 0.5 - top,
            area=float((grey >= 0.03).sum() * deg2), bright=float((grey >= 0.20).sum() * deg2),
            frame=float((grey >= 0.20).sum() * deg2 / frame), border=bool(grey[~inner].max() < 1.0 / 255.0)))
    return out


if __name__ == "__main__":
    print(f"head {HEAD_ELEVATION:.2f} degrees up, due west; lit windows {LIT_WINDOW}")
    for name in STYLES:
        for r in report(name):
            ok = r["on_sky"] < LIT_WINDOW and r["border"] and r["frame"] < 0.005
            print(f"{name} {r['look']:5s} peak {r['peak']:.2f} on sky {r['on_sky']:.2f}  tip {r['tip']:.1f} "
                  f"(margin {r['margin']:.1f})  area {r['area']:5.1f} bright {r['bright']:4.1f} deg2 "
                  f"= {100 * r['frame']:.3f}% of the frame  border {'black' if r['border'] else 'LIT'}"
                  f"  {'ok' if ok else 'FAIL'}")
