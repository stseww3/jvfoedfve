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
    when     With the opening (motion/arrival: who is new rides up in the train): as his car
             comes up out of the cloud, over cloud and sky, and gone before the mountain is
             before him; arrival.py sends it and says when. On the platform nothing is said.
             Without the opening, as in A8, and for whom the opening ended before its title
             (he got off on the way, there was no seat for him, he left and came back): WAIT
             ticks after the map has put him on the platform. At that moment his game still
             shows its "loading terrain" picture over everything and a title sent then is used
             up behind it; two seconds later he is looking at the observatory.
    how      Three functions in the data pack, written by the motion kit (MK.function) and named
             by the map's function tags (tools/export.py: HOOKS):
               guide/first   as who is new, once: marks him (MARK) and sets the title off in
                             WAIT ticks; with the opening it marks him and hands him to the
                             train (arrival.first())
               guide/join    as whoever joins, every time: if he still carries the mark, his
                             line having dropped in those two seconds, the title is set off
                             again; for everybody else it does nothing. With the opening,
                             who left in the middle of his ride is first put on the platform
                             (arrival.join())
               guide/title   WAIT ticks later, as nobody: shows the title to whoever carries
                             the mark, is there and is not in the opening (RIDE), and takes
                             the mark off him
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

The credit plate
    what     One enamel plaque of the props line's make (props/plaques.sign(), the plate of the
             twelve that say what a thing is): the name in one line, "Built by" and MAP_CREDIT
             under it. It is the one place in the map that names a builder, and it gives no
             address.
    where    On the waiting room's front, the wall on the right of whoever walks from the car
             to the steps: the pier east of the door (site/cablecar: WAIT_ROOM["door"]), the
             plate's middle PLATE_UP over the platform, a little under the eye. The arrival view
             (S.V1) does not have it: at the plate's height the front comes into that picture
             west of x 82.4 only, and the plate hangs between x 84 and 85. No other view of the
             board is within the 16 blocks a plaque is drawn from.
    when     Where the pier stands on the canvas, and in a tree that has props/plaques. A scene
             without the station has no plate hanging in the air; a tree without the props
             line's plaques has the title and no plate, and gets the plate when they come.

The switch is the main scene's GUIDE (scenes/obs/__init__.py), read when the scene is built:
tools/export.py --no-guide turns it off after everything is imported. With the switch off, or in
a tree whose main scene has none, nothing is registered, the data pack has no guide/ folder and
no plate hangs; the map's function tags name functions that are not there and pass them over.
The opening has a switch of its own beside it, ARRIVAL (arrival.py).

RIDE_MOST is a promise to whoever verifies a save (tools/export.py): so many ticks after a
newcomer has joined he stands on the platform, at the latest and whatever the train does. With
the train on time and nobody else in the map it is the ride and half a second, 950 ticks or so.
"""
import importlib
import json
import math

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
RIDE = "c164.ride"                      # the tag of who is in the opening: put on and taken off by arrival.py
RIDE_MOST = 2600                        # ticks from a newcomer's joining to his standing on the platform, at the most
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


def show(selector, name=None):
    """The commands that show the title to the players of a selector and take the mark off them.
    A name that would be cut off is refused."""
    name = MAP_TITLE if name is None else name
    wrong = misfits(name)
    if wrong:
        raise ValueError("motion/guide-title: " + "; ".join(wrong))
    return [
        f"title {selector} times {FADE_IN} {STAY} {FADE_OUT}",
        f"title {selector} subtitle {_text(name[1])}",
        f"title {selector} title {_text(name[0])}",
        f"tag {selector} remove {MARK}",
    ]


def functions(name=None, opening=None):
    """{name: [lines]} of the three functions, as MK.function() takes them, for the name of two
    lines given (MAP_TITLE). A name that would be cut off is refused.

    opening   None: who is new is shown the title on the platform. With the opening,
              {"first": [lines], "join": [lines]} of motion/arrival: what guide/first does with
              him once he is marked, and what guide/join does before anything else."""
    walkers = f"@a[tag={MARK},tag=!{RIDE}]"
    later = f"schedule function {{ns}}:{SHOW} {WAIT}t"
    shown = show(walkers, name)
    if opening is None:
        first = ["# as whoever is new, once (the map's function tag first): the title, in two seconds",
                 f"tag @s add {MARK}", later]
        join = []
    else:
        first = ["# as whoever is new, once (the map's function tag first): on to the train",
                 f"tag @s add {MARK}"] + list(opening["first"])
        join = list(opening["join"])
    return {
        FIRST: first,
        JOIN: ["# as whoever joins (the map's function tag join): who left before his title came is owed it"]
              + join + [f"execute if entity @s[tag={MARK},tag=!{RIDE}] run {later}"],
        SHOW: ["# the map's name, once, to whoever is new, is there and is not in the train"] + shown,
    }


def _of(name):
    """A module of the master scene by its name under scenes/obs, or None in a tree without it."""
    full = f"{__package__.rsplit('.', 1)[0]}.{name}" if name else __package__.rsplit(".", 1)[0]
    try:
        return importlib.import_module(full)
    except ModuleNotFoundError as e:
        if e.name != full:
            raise               # it is there and fails to import something: say so
        return None


def guide():
    """The main scene's switch, as it stands now."""
    return bool(getattr(_of(""), "GUIDE", False))


def title(canvas, name=None):
    """Register the three functions on the canvas: with the opening's lines where the canvas has
    the train and the opening is on (motion/arrival registers its own functions itself)."""
    from . import arrival           # here and not above: arrival reads this module
    opening = None
    if arrival.train(canvas) is not None:
        opening = {"first": arrival.first(), "join": arrival.join()}
    for function, lines in functions(name, opening).items():
        MK.function(canvas, function, lines)
    return 0


# ---- the credit plate ------------------------------------------------------------------------------
PLATE_UP = 1.5      # blocks from the platform to the middle of the plate; the eye is at 1.62


def plate_words(name=None, credit=None):
    """(the name in one line and in capitals, the line under it) as the plate has them."""
    name = MAP_NAME if name is None else " ".join(part for part in name if part)
    return name.upper(), f"Built by {MAP_CREDIT if credit is None else credit}"


def plate_at():
    """(pos, facing) of the credit plate as props/plaques.sign() takes them: the middle of the plate
    on the face of the pier east of the waiting room's door, and the way that face looks. None in
    a tree without the cable station."""
    station = _of("site.cablecar")
    if station is None:
        return None
    door_x, front_z = station.WAIT_ROOM["door"]
    return (door_x + 1.5, station.FEET + PLATE_UP, front_z + 1.0), "south"


def plate(canvas, origin=(0, 0, 0)):
    """Hang the credit plate where its pier stands on the canvas; returns the number of display
    entities (0 without the pier, and in a tree without props/plaques)."""
    plaques, at = _of("props.plaques"), plate_at()
    if plaques is None or at is None:
        return 0
    (x, y, z), facing = at
    behind = (math.floor(x) + origin[0], math.floor(y) + origin[1], math.floor(z - 0.5) + origin[2])
    if not canvas.has(*behind):
        return 0
    name, line = plate_words()
    return plaques.sign(canvas, name, line, (x, y, z), facing=facing, origin=origin)


def build(canvas, origin=(0, 0, 0)):
    if not guide():
        return 0
    return title(canvas) + plate(canvas, origin)
