"""motion/guide-title: the map's name, shown once to whoever arrives for the first time (card
plan/packages/motion/guide.md, part one).

The map's name is written here and nowhere else: MAP_TITLE, a placeholder until the map is named,
and MAP_CREDIT, the builder's name. tools/export.py reads MAP_TITLE from this module for the
world's name and for what the two packs say of themselves; importing the module builds nothing.

The title
    what     MAP_TITLE over SUBTITLE in the middle of the screen, once: the two come up in a
             second, stand for four and go in a second and a half (FADE_IN, STAY, FADE_OUT). The
             name is in the cream of the map's plates, the line under it in the amber of its
             lamps; the letters are the game's own.
    who      whoever is new, and he alone. Who comes back is told nothing.
    when     WAIT ticks after the map has put him on the platform. At that moment his game still
             shows its "loading terrain" picture over everything and a title sent then is used
             up behind it; two seconds later he is looking at the observatory.
    how      Three functions in the data pack, written by the motion kit (MK.function) and named
             by the map's function tags (tools/export.py: HOOKS):
               guide/first   as who is new, once: marks him (MARK) and sets the title off in
                             WAIT ticks
               guide/join    as whoever joins, every time: if he still carries the mark, his
                             line having dropped in those two seconds, the title is set off
                             again; for everybody else it does nothing
               guide/title   WAIT ticks later, as nobody: shows the title to whoever carries
                             the mark and is there, and takes the mark off him
             The schedule is the game's own kind, "replace": one more arrival within the two
             seconds moves the one pending title to two seconds after the later arrival, for
             both. Nothing runs every tick and nothing on a loop; the three run when somebody
             joins and at no other time, seven commands for a first arrival and one for every
             other (agreed with the loop's keeper, a2, 11-16).
    room     The game draws a title four times the size of its letters and neither breaks nor
             shrinks a long one: what is wider than the screen is cut off at both ends. At the
             scale the game picks by itself a screen of 16:9 is 427 wide (720p, 1440p, 4K) or
             480 (1080p), which leaves a title TITLE_ROOM pixels of the font and a line under it
             SUB_ROOM. width() measures a text in the default font; fits() says whether the two
             lines have room. build() goes on either way: a name that is too long is the
             director's to shorten.

The switch is the main scene's GUIDE (scenes/obs/__init__.py), read when the scene is built:
tools/export.py --no-guide turns it off after everything is imported. With the switch off, or in
a tree whose main scene has none, nothing is registered and the data pack has no guide/ folder;
the map's function tags name functions that are not there and pass them over.
"""
import importlib
import json

from ..common import palette as P
from . import _kit as MK

MAP_TITLE = "BLUE HOUR OBSERVATORY"     # a placeholder: when the admin names the map, this line changes
MAP_CREDIT = "c164"                     # the builder's name on the credit plate: the same

SUBTITLE = "An evening above the clouds"
FADE_IN, STAY, FADE_OUT = 20, 80, 30    # ticks
WAIT = 40                               # ticks from the arrival to the title
MARK = "c164.new"                       # the tag of who has arrived and has not been shown the title
TITLE_COLOUR = P.RAMPS["cream"][-1]     # #f2ead6, the letters of the map's plates
SUBTITLE_COLOUR = P.RAMPS["glow"][3]    # #ffe9a6, lamplight

FIRST, JOIN, SHOW = "guide/first", "guide/join", "guide/title"

# What the game's default font advances for a character, in its own pixels (the glyph and the one
# pixel after it). Letters, digits and what is not listed: 6.
_NARROW = {" ": 4, "!": 2, '"': 4, "'": 2, "(": 4, ")": 4, "*": 4, ",": 2, ".": 2, ":": 2, ";": 2,
           "<": 5, ">": 5, "@": 7, "I": 4, "[": 4, "]": 4, "`": 3, "f": 5, "i": 2, "k": 5, "l": 3,
           "t": 4, "{": 4, "|": 2, "}": 4, "~": 7}
TITLE_SCALE, SUBTITLE_SCALE = 4, 2      # how many times its letters' size the game draws the two lines
SCREEN = 427                            # the narrowest screen of 16:9 at the scale the game picks by itself
TITLE_ROOM = SCREEN // TITLE_SCALE      # 106
SUB_ROOM = SCREEN // SUBTITLE_SCALE     # 213


def width(text):
    """Pixels of the default font a line of plain English takes, the last letter's gap left out."""
    if not text.isascii() or not text.isprintable():
        raise ValueError(f"{text!r}: the map's words are plain English in the game's own letters")
    return sum(_NARROW.get(ch, 6) for ch in text) - (1 if text else 0)


def fits(title=None, subtitle=None):
    """(does the title have room, does the line under it), on the narrowest common screen."""
    return (width(MAP_TITLE if title is None else title) <= TITLE_ROOM,
            width(SUBTITLE if subtitle is None else subtitle) <= SUB_ROOM)


def _text(text, colour):
    """A text of one colour as a command takes it. Plain English only, so what JSON writes is what
    the game's own notation reads."""
    width(text)
    return json.dumps({"text": text, "color": colour}, separators=(",", ":"))


def functions(title=None, subtitle=None):
    """{name: [lines]} of the three functions, as MK.function() takes them."""
    title = MAP_TITLE if title is None else title
    subtitle = SUBTITLE if subtitle is None else subtitle
    marked = f"@a[tag={MARK}]"
    later = f"schedule function {{ns}}:{SHOW} {WAIT}t"
    return {
        FIRST: [
            "# as whoever is new, once (the map's function tag first): the title, in two seconds",
            f"tag @s add {MARK}",
            later,
        ],
        JOIN: [
            "# as whoever joins (the map's function tag join): who left before his title came is owed it",
            f"execute if entity @s[tag={MARK}] run {later}",
        ],
        SHOW: [
            "# the map's name, once, to whoever is new and is there",
            f"title {marked} times {FADE_IN} {STAY} {FADE_OUT}",
            f"title {marked} subtitle {_text(subtitle, SUBTITLE_COLOUR)}",
            f"title {marked} title {_text(title, TITLE_COLOUR)}",
            f"tag {marked} remove {MARK}",
        ],
    }


def guide():
    """The main scene's switch, as it stands now."""
    return bool(getattr(importlib.import_module(__package__.rsplit(".", 1)[0]), "GUIDE", False))


def title(canvas):
    """Register the three functions on the canvas."""
    for name, lines in functions().items():
        MK.function(canvas, name, lines)
    return 0


def build(canvas, origin=(0, 0, 0)):
    if not guide():
        return 0
    return title(canvas)
