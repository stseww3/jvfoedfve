"""motion/guide-title: the map's name, shown once to whoever arrives for the first time (card
plan/packages/motion/guide.md, part one).

The map's name is written here and nowhere else: MAP_TITLE, a placeholder until the map is named,
and MAP_CREDIT, the builder's name. MAP_NAME is the name in one line; tools/export.py reads it
from this module for the world's name and for what the two packs say of themselves. Importing the
module builds nothing.

The title
    what     The name in two lines in the middle of the screen, once: MAP_TITLE[0] as the game's
             title and MAP_TITLE[1] under it at half that size, both in the cream of the map's
             plates and in the game's own letters. They come up in a second, stand for four and
             go in a second and a half (FADE_IN, STAY, FADE_OUT). Nothing else is said.
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
    room     The game draws a title four times the size of its letters and the line under it
             twice, and neither breaks nor shrinks a long one: what is wider than the screen is
             cut off at both ends. At the scale the game picks by itself a screen of 16:9 is
             427 wide (720p, 1440p, 4K) or 480 (1080p), so a title has room for TITLE_ROOM
             pixels of the font: seventeen capitals or so, and BLUE HOUR OBSERVATORY in one
             line had 121. Hence the two lines (the director, 11-16 11:30). The line under it
             would have room for 213; it is kept to SUB_ROOM, the director's figure, so that it
             stays the smaller of the two. width() measures a line in the default font, and
             functions() refuses a name that does not fit: a scene with the guide then does not
             build, tools/check.py fails, and a new name is never cut off without anybody
             having seen it.

The switch is the main scene's GUIDE (scenes/obs/__init__.py), read when the scene is built:
tools/export.py --no-guide turns it off after everything is imported. With the switch off, or in
a tree whose main scene has none, nothing is registered and the data pack has no guide/ folder;
the map's function tags name functions that are not there and pass them over.
"""
import importlib
import json

from ..common import palette as P
from . import _kit as MK

# A placeholder: when the admin names the map, these two lines change and nothing else does. The
# name's two lines, the large one and the one under it (the second may be ""), and the builder.
MAP_TITLE = ("BLUE HOUR", "OBSERVATORY")
MAP_CREDIT = "c164"
MAP_NAME = " ".join(part for part in MAP_TITLE if part)     # the name in one line

FADE_IN, STAY, FADE_OUT = 20, 80, 30    # ticks
WAIT = 40                               # ticks from the arrival to the title
MARK = "c164.new"                       # the tag of who has arrived and has not been shown the title
COLOUR = P.RAMPS["cream"][-1]           # #f2ead6, the letters of the map's plates

FIRST, JOIN, SHOW = "guide/first", "guide/join", "guide/title"

# What the game's default font advances for a character, in its own pixels (the glyph and the one
# pixel after it). Letters, digits and what is not listed: 6.
_NARROW = {" ": 4, "!": 2, '"': 4, "'": 2, "(": 4, ")": 4, "*": 4, ",": 2, ".": 2, ":": 2, ";": 2,
           "<": 5, ">": 5, "@": 7, "I": 4, "[": 4, "]": 4, "`": 3, "f": 5, "i": 2, "k": 5, "l": 3,
           "t": 4, "{": 4, "|": 2, "}": 4, "~": 7}
TITLE_ROOM = 106                        # pixels of the font: 427 of the screen, at four times the size
SUB_ROOM = 149                          # the line under it: the director's figure (the screen holds 213)


def width(text):
    """Pixels of the default font a line of plain English takes, the last letter's gap left out."""
    if not text.isascii() or not text.isprintable():
        raise ValueError(f"{text!r}: the map's words are plain English in the game's own letters")
    return sum(_NARROW.get(ch, 6) for ch in text) - (1 if text else 0)


def misfits(name=None):
    """What is wrong with a name of two lines (MAP_TITLE when none is given): a list of sentences,
    empty when the title can be shown whole on every common screen."""
    name = MAP_TITLE if name is None else name
    if isinstance(name, str) or len(name) != 2 or not all(isinstance(part, str) for part in name):
        return [f"the map's name is two lines, (the large one, the one under it), not {name!r}"]
    out = []
    if not name[0].strip():
        out.append("the map's name has no first line")
    rooms = ((TITLE_ROOM, f"the title has room for {TITLE_ROOM}: the game would cut it off at both ends of the screen"),
             (SUB_ROOM, f"the line under the title is kept to {SUB_ROOM}"))
    for part, (room, why) in zip(name, rooms):
        try:
            wide = width(part)
        except ValueError as e:
            out.append(str(e))
            continue
        if part != part.strip():
            out.append(f"{part!r} begins or ends with a blank")
        if wide > room:
            out.append(f"{part!r} is {wide} pixels of the game's letters wide and {why}")
    return out


def _text(text):
    """A line in the plates' cream, as a command takes it. Plain English only, so what JSON writes
    is what the game's own notation reads."""
    return json.dumps({"text": text, "color": COLOUR}, separators=(",", ":"))


def functions(name=None):
    """{name: [lines]} of the three functions, as MK.function() takes them, for the name of two
    lines given (MAP_TITLE). A name that would be cut off is refused."""
    name = MAP_TITLE if name is None else name
    wrong = misfits(name)
    if wrong:
        raise ValueError("motion/guide-title: " + "; ".join(wrong))
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
            f"title {marked} subtitle {_text(name[1])}",
            f"title {marked} title {_text(name[0])}",
            f"tag {marked} remove {MARK}",
        ],
    }


def guide():
    """The main scene's switch, as it stands now."""
    return bool(getattr(importlib.import_module(__package__.rsplit(".", 1)[0]), "GUIDE", False))


def title(canvas, name=None):
    """Register the three functions on the canvas."""
    for function, lines in functions(name).items():
        MK.function(canvas, function, lines)
    return 0


def build(canvas, origin=(0, 0, 0)):
    if not guide():
        return 0
    return title(canvas)
