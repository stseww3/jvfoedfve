"""props/plaques: the enamel plaques that say what a thing is (motion/guide, part B; A0, 11-16 11:02).

A plaque is a plate of the station's enamel, blue with a cream edge, WIDE by HIGH (0.92 by 0.27
block, so it hangs on a pier one block wide), with a name in capitals and one sentence under it.
It is made of the game's text displays alone, no model and no picture of the pack:

    two plates of colour   a text display that holds one space shows its background as a rectangle
                           five font pixels by ten, which the scale draws out to any size
    a display for a line   the name, and the sentence on one line or two; a line is never left to
                           the game to break (line_width), so the plate knows how wide its words are

The font is the game's own (the pack adds none): the widths below are measured off the 26.3 jar.
Nothing here is drawn by the offline renderer: what a plaque looks like is seen in the game alone.

    sign(canvas, name, sentence, pos, facing)    any plaque (the credit plate of motion/guide)
    place(canvas, key, pos, facing)              one of TEXT
    site(canvas, origin)                         those of TEXT that the two tables place
    build(canvas, origin)                        site(), when the master scene says GUIDE

Where the twelve hang is not written here: the two halves of the site each keep a table,
props/_plaques_east.py and props/_plaques_west.py (HALVES), read by site_plaques():

    def plaques():
        return {"armillary": dict(pos=(x, y, z), facing="south"), ...}

pos is the middle of the plate, on the face of the wall, pier or parapet it hangs on, in scene
coordinates; facing is the way the plaque looks (the way the face of the wall looks). A table is a
function so that it reads the other packages' tables when it is asked, not when it is imported.
"""
import importlib
import math

from artkit.nbtw import Byte, Float

from ..common import palette as P
from . import _kit as K

TAG = "c164.plaque"
HALVES = ("_plaques_east", "_plaques_west")

# ---- the plate (blocks) ----------------------------------------------------------------------------
WIDE, HIGH = 0.92, 0.27     # every plaque is this size, whatever it says: a family of signs, and a pier
                            # one block wide keeps 0.04 of its stone either side
EDGE = 0.010                # the cream edge round the blue field
PAD = 0.04                  # blue left and right of the widest line, at the least
STAND = 0.010               # the edge plate off the face of the wall
LAYER = 0.004               # from the edge plate to the field, and from the field to the words
PX = 0.025                  # a font pixel of a text display at scale 1 (the game draws text 1/40 block to the pixel)
NAME_PX, LINE_PX = 0.0075, 0.0055   # a font pixel of the name and of the sentence. A capital of the
                            # sentence is 0.0385 block high: read from three blocks, a spot from ten
CAP, PITCH = 7, 10          # font pixels: the height of a capital, from one baseline to the next
GAP = 0.032                 # from the name's baseline down to the top of the sentence's capitals
LINES = 2                   # the sentence stands on this many lines at the most
WORDS = 9                   # ... and has this many words at the most (the card)

# ---- how it is shown -------------------------------------------------------------------------------
# view_range 0.25 is 16 blocks at the game's own entity distance (c353): the plaques out of doors
# stand 21 blocks and more from the cameras of the board (V2 21.5 from the armillary's base, V5 39
# from the foot of the clock tower), so no board picture holds one, and who walks up to a thing
# finds its plate. The words are read from three blocks at the most anyway.
VIEW = 0.25
# The light every display is drawn in, (sky, block), whatever stands round it: read at night, no
# lamp. Text is not shaded by the way it looks as a model's face is: the door plate, a model shown
# at (15, 12), keeps half of that on a face that looks east, and the cream of words shown at
# (15, 12) would be near 0.85. Block light 7 and no sky is 0.40 on the game's own curve at its
# default brightness; the cream is to stay under 0.45 on the board (review c332, 11-16). To be
# measured in the real client, as the door plate was.
SHOWN = (0, 7)
FIELD = P.RAMPS["enamel"][1]        # the plan's enamel blue, #172c57
RIM = P.RAMPS["cream"][3]           # the plan's cream, #f2ead6: the edge and the name
WORDS_TONE = P.RAMPS["cream"][2]    # the sentence a step under the name

# ---- the game's font -------------------------------------------------------------------------------
# What a glyph of the default font moves the pen on by, in font pixels, the pixel between two
# glyphs with it: six but for these (26.3.jar, assets/minecraft/textures/font/ascii.png; the space
# from font/include/space.json).
ADVANCE = {ch: n for n, chars in ((2, "!',.:;i|"), (3, "`l"), (4, " \"()*I[]t{}"), (5, "<>fk"), (7, "@~")) for ch in chars}


def width(text):
    """Font pixels from the left of the first glyph of a line to the right of its last."""
    strange = sorted({ch for ch in text if not 32 <= ord(ch) < 127})
    if strange:
        raise ValueError(f"a plaque is written in the game's ASCII glyphs alone: {strange!r} in {text!r}")
    return sum(ADVANCE.get(ch, 6) for ch in text) - 1


# ---- what the twelve say (the card, plan/packages/motion/guide.md; shorter is allowed, longer is not)
TEXT = {
    "cable_station": ("CABLE STATION", "The only way up the mountain."),
    "meridian_line": ("THE MERIDIAN LINE", "Brass, laid true north and south."),
    "armillary": ("ARMILLARY SPHERE", "The great circles of the sky, in brass."),
    "orrery": ("THE ORRERY", "Six planets, geared to their true periods."),
    "master_clock": ("THE MASTER CLOCK", "One pendulum. Every dial here follows it."),
    "time_room": ("TIME ROOM", "The hour goes out from here by wire."),
    "chart_room": ("CHART ROOM", "Each clear night is drawn here by hand."),
    "plate_vault": ("PLATE VAULT", "A glass plate for every clear night."),
    "great_refractor": ("THE GREAT REFRACTOR", "Tonight it is turned on the comet."),
    "time_ball": ("TIME BALL", "It drops once a day, on the second."),
    "power_house": ("POWER HOUSE", "Steam turns the dynamo that lights the lamps."),
    "sunset_terrace": ("SUNSET TERRACE", "The comet sets an hour behind the sun."),
}


def lines_of(sentence, limit):
    """The sentence on one line if `limit` font pixels hold it, else on two as even as they can be."""
    if width(sentence) <= limit:
        return [sentence]
    words, best = sentence.split(), None
    for i in range(1, len(words)):
        rows = [" ".join(words[:i]), " ".join(words[i:])]
        wide = max(map(width, rows))
        if wide <= limit and (best is None or wide < best[0]):
            best = (wide, rows)
    if best is None:
        raise ValueError(f"{sentence!r} does not stand on {LINES} lines of {limit} font pixels: write it shorter")
    return best[1]


def layout(name, sentence):
    """The lines of a plaque as [(words, font pixel in blocks, height of the baseline over the middle
    of the plate, tone)], the name first. The name is in capitals and is set smaller when NAME_PX
    does not hold it; the block of lines stands in the middle of the plate's height."""
    if name != name.upper() or not name.strip():
        raise ValueError(f"the name of a plaque is written in capitals: {name!r}")
    if len(sentence.split()) > WORDS:
        raise ValueError(f"a plaque's sentence has {WORDS} words at the most: {sentence!r}")
    inner = WIDE - 2.0 * (EDGE + PAD)
    name_px = min(NAME_PX, inner / width(name))
    rows = lines_of(sentence, int(inner / LINE_PX))
    block = CAP * name_px + GAP + CAP * LINE_PX + (len(rows) - 1) * PITCH * LINE_PX    # top of the name to the last baseline
    if block + 2.0 * LINE_PX > HIGH - 2.0 * (EDGE + PAD / 2.0):
        raise ValueError(f"the lines of {name!r} are {block:.3f} high, too much for a plate of {HIGH}")
    y = block / 2.0 - CAP * name_px
    out = [(name, name_px, y, RIM)]
    y -= GAP + CAP * LINE_PX
    for row in rows:
        out.append((row, LINE_PX, y, WORDS_TONE))
        y -= PITCH * LINE_PX
    return out


for _name, _sentence in TEXT.values():
    layout(_name, _sentence)


# ---- the displays ----------------------------------------------------------------------------------
def _argb(tone):
    """An opaque colour "#rrggbb" as the signed number a text display's background is."""
    value = 0xFF000000 | int(tone.lstrip("#"), 16)
    return value - (1 << 32) if value >= 1 << 31 else value


def _display(words, scale, yaw, view, tone=None, background=0):
    """NBT of one text display that looks the way `yaw` says (K.FACING): the words read from that
    side, left to right as K.turn(yaw, (1, 0, 0)) goes. scale is (across, up)."""
    text = {"text": words}
    if tone is not None:
        text["color"] = tone
    return {
        "id": "minecraft:text_display",
        "text": text,
        "line_width": 4000,                         # font pixels: the line is never broken by the game
        "background": int(background),              # 0: none is drawn
        "shadow": Byte(0), "see_through": Byte(0), "default_background": Byte(0),
        "alignment": "center",
        "billboard": "fixed",
        "brightness": {"sky": int(SHOWN[0]), "block": int(SHOWN[1])},
        "transformation": {
            "left_rotation": [Float(0.0), Float(0.0), Float(0.0), Float(1.0)],
            "right_rotation": [Float(0.0), Float(0.0), Float(0.0), Float(1.0)],
            "scale": [Float(scale[0] / PX), Float(scale[1] / PX), Float(1.0)],
            "translation": [Float(0.0), Float(0.0), Float(0.0)],
        },
        "Rotation": [Float((yaw + 180.0) % 360.0 - 180.0), Float(0.0)],
        "view_range": Float(view),
        "Tags": ["c164art", TAG],
    }


def _plate(canvas, at, yaw, view, tone, wide, high, off):
    """A rectangle of one colour, wide by high, its middle `off` in front of `at`. The background of
    a line that holds one space is five font pixels wide and ten high; it stands on the display's
    own height and half a pixel to the right of it."""
    px = (wide / 5.0, high / 10.0)
    dx, dy, dz = K.turn(yaw, (-px[0] / 2.0, -high / 2.0, off))
    canvas.add_entity(at[0] + dx, at[1] + dy, at[2] + dz, _display(" ", px, yaw, view, background=_argb(tone)))
    return 1


def _line(canvas, at, yaw, view, words, px, base, tone, off):
    """One line of words, its ink centred on `at` across and its baseline `base` over it. The game
    stands a single line's baseline two font pixels over the display and its ink half a pixel to
    the right of it."""
    dx, dy, dz = K.turn(yaw, (-px / 2.0, base - 2.0 * px, off))
    canvas.add_entity(at[0] + dx, at[1] + dy, at[2] + dz, _display(words, (px, px), yaw, view, tone=tone))
    return 1


def sign(canvas, name, sentence, pos, facing="south", origin=(0, 0, 0), yaw=None, view=VIEW):
    """Hang one plaque; returns the number of display entities (two plates and a display a line).

    name       the first line, in capitals; set smaller if it is wider than the plate holds.
    sentence   WORDS words at the most; it is broken into two lines here when one does not hold it.
    pos        the middle of the plate on the face it hangs on, scene coordinates; the plate is
               WIDE by HIGH and stands STAND + 2 LAYER (0.018) off that face at the most.
    facing     the way the plaque looks, which is the way that face looks; yaw (degrees, as
               K.FACING) instead for a face that is not square to the grid.
    A text display stops nobody and is seen from its front alone.
    """
    yaw = K.FACING[facing] if yaw is None else float(yaw)
    rows = layout(name, sentence)
    at = tuple(float(p) + o for p, o in zip(pos, origin))
    n = _plate(canvas, at, yaw, view, RIM, WIDE, HIGH, STAND)
    n += _plate(canvas, at, yaw, view, FIELD, WIDE - 2.0 * EDGE, HIGH - 2.0 * EDGE, STAND + LAYER)
    for words, px, base, tone in rows:
        n += _line(canvas, at, yaw, view, words, px, base, tone, STAND + 2.0 * LAYER)
    return n


def place(canvas, key, pos, facing="south", origin=(0, 0, 0), **how):
    """Hang the plaque TEXT[key]: sign() with its words."""
    name, sentence = TEXT[key]
    return sign(canvas, name, sentence, pos, facing=facing, origin=origin, **how)


def corners(pos, facing="south", yaw=None):
    """The four corners of a plaque's plate in scene coordinates, for a table's own tests: lower
    left, lower right, upper right, upper left as its reader sees them."""
    yaw = K.FACING[facing] if yaw is None else float(yaw)
    out = []
    for across, up in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        dx, dy, dz = K.turn(yaw, (across * WIDE / 2.0, up * HIGH / 2.0, STAND))
        out.append((pos[0] + dx, pos[1] + dy, pos[2] + dz))
    return out


# ---- the site --------------------------------------------------------------------------------------
def site_plaques():
    """What the tables of the two halves place, {key: dict(pos=, facing= or yaw=, view=)}. A half
    whose table is not in the tree places nothing; a key of no plaque, or one both halves place,
    is an error."""
    out = {}
    for half in HALVES:
        module = f"{__package__}.{half}"
        try:
            table = importlib.import_module(module)
        except ModuleNotFoundError as err:
            if err.name != module:
                raise
            continue
        rows = table.plaques() if callable(getattr(table, "plaques", None)) else getattr(table, "PLAQUES", {})
        for key, spec in rows.items():
            if key not in TEXT:
                raise KeyError(f"{half}: {key!r} is no plaque of props/plaques.TEXT")
            if key in out:
                raise ValueError(f"{key!r} is placed by both halves")
            out[key] = dict(spec)
    return out


def _behind(spec):
    """The cell behind the middle of a plaque: the stone it hangs on."""
    yaw = K.FACING[spec.get("facing", "south")] if spec.get("yaw") is None else float(spec["yaw"])
    dx, _, dz = K.turn(yaw, (0.0, 0.0, -0.5))
    x, y, z = spec["pos"]
    return (math.floor(x + dx), math.floor(y), math.floor(z + dz))


def site(canvas, origin=(0, 0, 0), keys=None):
    """Hang the plaques of the tables (site_plaques()), or those of `keys`. A plaque hangs only where
    the cell behind its middle stands on the canvas, so a tree or a test scene without that wall
    has none floating; the keys left out are kept in canvas.plaques_left_out. A plaque hangs once:
    a second call adds what does not hang yet. Returns the number of display entities placed."""
    origin = tuple(origin)
    hung = getattr(canvas, "plaques_hung", None)
    if hung is None:
        hung = canvas.plaques_hung = set()
    n, left = 0, []
    for key, spec in site_plaques().items():
        if (keys is not None and key not in keys) or (key, origin) in hung:
            continue
        x, y, z = _behind(spec)
        if not canvas.has(x + origin[0], y + origin[1], z + origin[2]):
            left.append(key)
            continue
        how = {k: spec[k] for k in ("facing", "yaw", "view") if spec.get(k) is not None}
        n += place(canvas, key, spec["pos"], origin=origin, **how)
        hung.add((key, origin))
    canvas.plaques_left_out = left
    return n


def dress(canvas):
    """Ask for the plaques on this canvas whatever the master scene's switch says (a test scene)."""
    canvas.plaques_dress = True


def build(canvas, origin=(0, 0, 0)):
    """What the plaques place in the master scene: nothing unless the master scene says GUIDE (the
    switch comes with motion/guide's title, c346; a tree without it has no plaques) or the canvas
    was asked to be dressed (dress())."""
    from ... import obs
    if not (getattr(obs, "GUIDE", False) or getattr(canvas, "plaques_dress", False)):
        return 0
    return site(canvas, origin)
