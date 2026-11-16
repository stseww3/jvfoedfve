"""motion/guide.py -- the six star charts: who walks up to one has it, and what the great refractor
shows the visitor who has all six.

Card plan/packages/motion/guide.md, part C (the charts are an Easter egg, not a task: nobody is
told to look for them). The charts, their models and the glint beside each are
motion/_guide_charts.py's (cloud, c329); this module reads that module's table and registers what
happens to a player:

  a chart     A player whose feet come within REACH blocks of the floor under a chart he does not
              have yet gets the tag c164.c<n> (n is the chart's row in the table, 1 to 6), hears one
              soft chime that nobody else hears, and reads "Star chart 3 of 6" over his hotbar: 3 is
              how many he has now. The chart stays where it is, for the next visitor. Where the
              table names the spot one stands on to read a chart (STAND), the feet have to be
              within REACH of that spot as well: a chart on a wall, or on a desk against one, is
              not taken through the wall by somebody who walks along its far side.
  the lens    A player who stands where the observer stands, behind the eyepiece of the great
              refractor (machines/scope.OBSERVER), and has
                all six    reads the title THE COMET, IN FOCUS once, hears one bell, and for ten
                           seconds sees points of light go up the dome's slit; he gets the tag
                           c164.done, and after that nothing happens to him there any more
                some       reads "Star charts: 3 of 6" over his hotbar for as long as he stands there
                none       nothing

Everything a player has is on the player: seven tags and two scores, c164g (how many charts he
has, counted anew from his tags whenever it is shown) and c164f (the beats of light he is still to
see). There is no state of the world, so eleven visitors do not get into each other's way, a
visitor who leaves and comes back goes on where he was, and one who drops out in the middle of the
lights sees the rest of them when he is back. The chime, the bell, the title and the lights go to
that one player (the particles with the command's list of viewers). Nothing is said in the chat,
nothing is given, no game mode is changed, there is no boss bar and no function of the owner's.

How it is driven. No function runs every tick: the tests ride on the motion loop (motion/_kit),
one chain of BEAT ticks. On tick 0 of a beat one command for every chart, a selector that finds
the players near it who lack its tag; on tick BEAT / 2 one command for the lens and one for the
lights of those who are still to see some. The commands that do something are data-pack functions
(<namespace>:guide/...), which run only when a selector has found somebody: with nobody near, a
beat costs the server eight selectors, the chain's guard and two lines of scheduling.

What an event costs, for the one player it happens to and counted with the chain's command that
found him: a chart taken 13 commands, once; a beat at the lens short of six charts 12; the lights
30 a beat for ten seconds (guide/glow finds the beat's own small function, guide/glow/01 .. 25,
three points each; as one list of 75 tested lines it was 77 a beat, and the loop's keeper asked
for the split). These are outside the loop's average and its limit for one tick, with the
keeper's consent (a2, 11-16 11:32).

The card asked for a test every 4 ticks. It is every 8 (a2's budget for the whole loop, agreed
11-16 11:13): a sprinting player covers 5.6 blocks a second and needs 11 ticks to cross the 3
blocks of a chart's reach along its middle, so a test every 8 ticks does not miss a visitor who
walks or runs past a chart on its floor, and one who stops at it has it within 0.4 s.

The switches are the master scene's: GUIDE (the whole guide layer) and GUIDE_CHARTS (this part
alone). They come into scenes/obs/__init__.py with motion/guide-title (s2, 11-16 11:22), and until
they are there they count as off: build() registers nothing while either is off or missing, or
while motion/_guide_charts.py is not in the tree. A test scene calls quest() itself.

0 display entities and 0 blocks of its own; what _guide_charts.build() places is counted there.
"""
import importlib
import math

from . import _kit as MK
from ..common import skeleton as S

REACH = 1.6                     # blocks from the floor before a chart to a player's feet
LENS_REACH = 1.0                # blocks from the observer's spot to a player's feet
BEAT = 8                        # ticks from one test to the next
LENS_AT = BEAT // 2             # the tick of a beat the lens and the lights are looked after
TAG = "c164.c{n}"               # on a player who has chart n
DONE = "c164.done"              # on a player who has seen the comet in focus
COUNT = "c164g"                 # objective: the charts a player has
GLOW = "c164f"                  # objective: the beats of light a player is still to see

CHIME = ("minecraft:block.note_block.chime", 0.6, 1.2)      # the game's event, volume, pitch
# The bell at 1.0 is the game's bell rung by hand beside one: the loudness a player knows. The
# game's sound table plays every file of the bell at 12 times the volume asked for and cuts the
# product off at 1 (sound, c361, read off the game's table), so from 0.084 up nothing changes;
# to have it softer the number is 0.065 for about eight tenths (cr2, 11-16 12:03: not now).
BELL = ("minecraft:block.bell.use", 1.0, 0.8)
SOURCE = "master"               # the volume slider both are under: the one nobody has turned off
TITLE = "THE COMET, IN FOCUS"
TITLE_TIMES = (20, 80, 30)      # ticks: fading in, standing, fading out (the arrival title's)
TAKEN = "Star chart "           # ... 3 of 6, when a chart is taken
SO_FAR = "Star charts: "        # ... 3 of 6, at the lens
OF = " of "

# The lights: end_rod, the game's white point that fades out over three to three and a half seconds
# and sinks a little. They go up the slit of the great dome, which looks west: a beat's points
# start on the arc of the dome's skin, higher from beat to beat, and each leaves along the arc.
LIGHT = "minecraft:end_rod"
LIGHT_BEATS = 25                # ten seconds
LIGHT_SPEED = 0.10              # blocks a tick it starts with; the game takes a tenth off every tick: one block of way
LIGHT_ARC = (14.0, 78.0)        # degrees over the dome's springing: from above the slit's sill to short of its head
# A beat's points: where across the slit (blocks north or south of its middle) and how far along
# the arc from the beat's own height (degrees). Three to a beat, the pattern of four beats: 27 are
# alight at once at the most (the card's limit is 40).
LIGHT_ROWS = (
    ((-1.5, 0.0), (0.2, 2.5), (1.6, -1.5)),
    ((-0.7, 1.5), (1.0, -2.0), (-1.7, 3.0)),
    ((1.4, 0.5), (-1.1, -2.5), (0.3, 2.0)),
    ((0.8, -1.0), (-1.6, 1.0), (-0.3, 3.5)),
)


def _package(line, name):
    """The package `name` of a line of the scene, or None while it is not in the tree."""
    full = f"scenes.obs.{line}.{name}"
    try:
        return importlib.import_module(full)
    except ModuleNotFoundError as e:
        if e.name and (full == e.name or full.startswith(e.name + ".")):
            return None
        raise


def enabled():
    """Are the guide layer and its charts switched on? The switches are the master scene's, and
    one that is not there is off."""
    master = importlib.import_module(__package__.rsplit(".", 1)[0])
    return bool(getattr(master, "GUIDE", False)) and bool(getattr(master, "GUIDE_CHARTS", False))


_HAS = object()                 # in a text: the number of charts the player has


def _text(*parts):
    """A text component as a command takes it: strings, and _HAS for the player's number."""
    out = []
    for part in parts:
        if part is _HAS:
            out.append('{score:{name:"@s",objective:"' + COUNT + '"}}')
        else:
            out.append('{text:"' + part.replace("\\", "\\\\").replace('"', '\\"') + '"}')
    return out[0] if len(out) == 1 else "[" + ",".join(out) + "]"


def _num(v):
    """A number as a command takes it: no exponent, no needless digits."""
    text = f"{float(v):.4f}".rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


def _sound(event):
    name, volume, pitch = event
    return f"playsound {name} {SOURCE} @s ~ ~ ~ {_num(volume)} {_num(pitch)}"


FACING = {"west": (-1, 0), "east": (1, 0), "north": (0, -1), "south": (0, 1)}      # (east, south) a slit looks


def slit():
    """The great dome's slit as the skeleton has it: (the middle of the dome at its springing, the
    radius of its skin, the half of the slit's width that is clear of its edges, the way it looks)."""
    cx, cz = S.DOME_AXIS
    return (cx, float(S.DOME_SPRING), cz), float(S.DOME_R), S.SLIT_W / 2.0 - 0.75, S.SLIT_FACING


def lights(radius, half, facing="west", beats=LIGHT_BEATS):
    """The points of light of the finale: [(beat, (east, up, south) of the dome's middle at its
    springing, (east, up, south) blocks a tick)]. A point starts on the arc that climbs from the
    slit's foot to the dome's top and leaves along it, upwards."""
    ox, oz = FACING[facing]
    low, high = LIGHT_ARC
    out = []
    for beat in range(beats):
        height = low + (high - low) * beat / float(max(1, beats - 1))
        for across, along in LIGHT_ROWS[beat % len(LIGHT_ROWS)]:
            a = math.radians(min(high, max(low, height + along)))
            off, side = radius * math.cos(a), max(-half, min(half, across))
            back = -LIGHT_SPEED * math.sin(a)
            out.append((beat, (ox * off - oz * side, radius * math.sin(a), oz * off + ox * side),
                        (ox * back, LIGHT_SPEED * math.cos(a), oz * back)))
    return out


def functions(charts, radius, half, facing="west"):
    """The functions of the guide's charts, {name below <namespace>:guide/: [lines]}. {ns} stands for
    the namespace; a position is the one the caller runs the function at."""
    n_charts = len(charts)
    count = [f"scoreboard objectives add {COUNT} dummy", f"scoreboard players set @s {COUNT} 0"]
    out = {}
    for n in range(1, n_charts + 1):
        tag = TAG.format(n=n)
        count.append(f"execute if entity @s[tag={tag}] run scoreboard players add @s {COUNT} 1")
        # run as the player who has come up to chart n, at the floor before it
        out[f"c{n}"] = [f"tag @s add {tag}", "function {ns}:guide/count", _sound(CHIME),
                        f"title @s actionbar {_text(TAKEN, _HAS, OF + str(n_charts))}"]
    out["count"] = count
    # run as a player who stands behind the eyepiece and has not seen the comet in focus yet
    out["lens"] = ["function {ns}:guide/count",
                   f"execute if score @s {COUNT} matches {n_charts}.. run return run function {{ns}}:guide/done",
                   f"execute if score @s {COUNT} matches 1.. run title @s actionbar "
                   f"{_text(SO_FAR, _HAS, OF + str(n_charts))}"]
    out["done"] = [f"tag @s add {DONE}", f"scoreboard objectives add {GLOW} dummy",
                   f"scoreboard players set @s {GLOW} {LIGHT_BEATS}",
                   "title @s times " + " ".join(str(int(t)) for t in TITLE_TIMES),
                   f"title @s title {_text(TITLE)}", _sound(BELL)]
    # run as a player who is still to see lights, at the middle of the dome at its springing: the
    # score counts down from LIGHT_BEATS, and glow sends him to the small function of the beat it
    # stands at (guide/glow/01 is the first beat's)
    glow, beats = [], {}
    for beat, (dx, dy, dz), (vx, vy, vz) in lights(radius, half, facing):
        beats.setdefault(beat, []).append(f"particle {LIGHT} ~{_num(dx)} ~{_num(dy)} ~{_num(dz)} "
                                          f"{_num(vx)} {_num(vy)} {_num(vz)} 1 0 force @s")
    for beat in sorted(beats):
        out[f"glow/{beat + 1:02d}"] = beats[beat]
        glow.append(f"execute if score @s {GLOW} matches {LIGHT_BEATS - beat} run function "
                    f"{{ns}}:guide/glow/{beat + 1:02d}")
    out["glow"] = glow + [f"scoreboard players remove @s {GLOW} 1"]
    return out


def quest(canvas, charts, observer, dome, origin=(0, 0, 0), stands=None):
    """Register the charts' tests and the lens's on the canvas.

    charts     [(name, the middle of the chart's face (x, y, z), the y of the floor one stands on
               beside it)], chart 1 first: _guide_charts.CHARTS
    stands     for every chart the spot of that floor one stands on to read it, or None:
               _guide_charts.STAND
    observer   where the observer's feet stand behind the eyepiece
    dome       (the middle of the dome at its springing, the radius of its skin, the clear half of
               its slit's width, the way the slit looks): slit()
    All in scene coordinates, plus origin. Returns 0: no display entity is placed.
    """
    middle, radius, half, facing = dome
    for name, lines in functions(charts, radius, half, facing).items():
        MK.function(canvas, f"guide/{name}", lines)
    near = ",distance=.." + _num(REACH) + "]"
    for n, (_name, face, floor) in enumerate(charts, 1):
        under = (face[0], floor, face[2])
        who = "execute positioned {x} {y} {z} as @a[tag=!" + TAG.format(n=n) + near
        call = " run function {ns}:guide/c" + str(n)
        if stands is None:
            MK.run(canvas, under, who + call, BEAT, at=(0,), origin=origin)
        else:
            MK.run(canvas, {"": under, "stand": stands[n - 1]},
                   who + " positioned {stand.x} {stand.y} {stand.z} if entity @s[" + near[1:] + call,
                   BEAT, at=(0,), origin=origin)
    MK.run(canvas, observer, "execute positioned {x} {y} {z} as @a[distance=.." + _num(LENS_REACH) + ",tag=!" + DONE
           + "] run function {ns}:guide/lens", BEAT, at=(LENS_AT,), origin=origin)
    MK.run(canvas, middle, "execute positioned {x} {y} {z} as @a[scores={" + GLOW + "=1..}] run function {ns}:guide/glow",
           BEAT, at=(LENS_AT,), origin=origin)
    return 0


def build(canvas, origin=(0, 0, 0)):
    if not enabled():
        return 0
    charts = _package("motion", "_guide_charts")
    scope = _package("machines", "scope")
    if charts is None or scope is None:
        return 0
    n = charts.build(canvas, origin) or 0
    quest(canvas, charts.CHARTS, scope.OBSERVER[scope.VERSION], slit(), origin, stands=getattr(charts, "STAND", None))
    return n
