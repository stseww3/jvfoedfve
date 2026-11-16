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
                all six    reads the title THE COMET, IN FOCUS once and hears one bell, as soon as
                           his eye is at the eyepiece: the title stands on the comet's picture
                           there (machines/scope shows it to an eye within half a block, and marks
                           that player with scope.EYE_TAG). He gets the tag c164.done, and after
                           that nothing happens to him there any more. When he takes his eye
                           off the eyepiece he has ten seconds of light before him: a shaft of
                           motes that comes down the dome's slit beside the comet and stays, and
                           a stream of points that runs from the objective down the tube's flank
                           into the eyepiece's mouth. Until his eye is there he reads
                           "Star charts: 6 of 6" like anybody who has some.
                           While machines/scope has no such tag the close is as it was: title,
                           bell and lights at once, for whoever stands on the spot
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
30 to 32 a beat for ten seconds (guide/glow finds the beat's own small function, guide/glow/01
.. 25: three commands for the shaft, each of which has the game scatter four or eight motes, and
one or two for the stream; as one list of 75 tested lines it was 77 a beat, and the loop's keeper
asked for the split). These are outside the loop's average and its limit for one tick, with the
keeper's consent (a2, 11-16 11:32, for 30 a beat).

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
from ..common import palette as P
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

# The lights of the close: ten seconds of them, in two parts (cr2, 11-16 12:38, on the pictures of
# the real machine: the first lights were three single points a beat, a dozen in sight at once and
# all of them twenty blocks off, behind the tube for the one who stands at the eyepiece).
#
# The shaft: the comet's light in the slit of the great dome. Motes of end_rod, the game's white
# point: it hangs where it is put, sinks a third of a block and goes out after three to three and
# a half seconds. A beat still costs three commands; each now sends several motes and lets the
# command scatter them about its place, along the arc of the dome's skin, through the skin and
# across the slit. In the first SHAFT_FALL beats the shaft comes down the slit from its head, a
# third of the arc a beat; after that every third of the arc gets one command a beat, at a place
# that wanders. From the fourth beat on 84 motes and more hang in the slit at once (alight()).
# They keep to one side of the slit: the comet is so far off that it is seen in the slit where the
# viewer himself stands across it, and who has just left the eyepiece stands in the tube's plane.
# The shaft takes the other side, so the comet's head and tail stay clear for him.
LIGHT = "minecraft:end_rod"
LIGHT_BEATS = 25                # ten seconds
LIGHT_LIFE = (60, 71)           # ticks a mote of end_rod lives (read off the game's code, 26.3)
SHAFT_ARC = (14.0, 78.0)        # degrees over the dome's springing: from above the slit's sill to short of its head
SHAFT_ROW = 3                   # commands a beat
SHAFT_FALL = 3                  # the beats the shaft takes to come down the slit
SHAFT_COUNT = (8, 4)            # motes a command sends: while the shaft comes down, and in every beat after
SHAFT_SPREAD = (0.8, 0.3, 0.35)     # one sigma of the scatter, blocks: along the arc, through the skin, across the slit
SHAFT_DRIFT = 0.02              # blocks a tick a mote may start with, any way: it wanders a fifth of a block
GOLDEN = (math.sqrt(5.0) - 1.0) / 2.0

# The stream: the light the tube has caught, on its way to the eye. Points of trail, the game's
# point that goes straight to a place in a given time and is gone when it is there; no wind, no
# fall, no chance in it. A beat sends one small bunch from under the objective's rim; it runs down
# the tube's lower flank in STREAM_BEATS beats and draws together on the way, and where the tube
# ends a second command takes it up into the eyepiece's mouth. So seven bunches are on the way at
# once, and the one who has stepped back from the eyepiece has them come down to him without
# turning his head. The places are quest()'s tube=; without it there is no stream.
STREAM = "minecraft:trail"
STREAM_COLOUR = int(P.RAMPS["glow"][-1].lstrip("#"), 16)    # the comet's own hottest colour (sky/comet.HOT)
STREAM_FROM = SHAFT_FALL        # the beat the first bunch leaves: the shaft has come down to the objective
STREAM_BEATS = 7                # beats down the tube: a quarter of a block a tick on the great refractor
STREAM_COUNT, STREAM_SPREAD = 5, 0.3    # points of a bunch, and one sigma of how far from each other they start
HOP_TICKS = 4                   # from the tube's end into the mouth, as fast as it came down
HOP_COUNT, HOP_SPREAD = 3, 0.05
# where the stream runs on the great refractor (tube()): degrees round the tube from its lowest
# line, away from the mount, whose saddle holds the tube 37 degrees to the other side; blocks
# from the tube's axis at the objective (its cell is 15/16) and at the tail (the body is 3/4, and
# swings a fifth of a block there); blocks past the objective it starts and behind the tail it
# turns; blocks before the eyepiece's end face it ends
STREAM_LEAN = 35.0
STREAM_OFF = (1.25, 0.95)
STREAM_PAST = (0.2, 0.15, 0.05)


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


def across(observer, middle, facing="west"):
    """Where across a slit the comet is seen by somebody who stands at `observer`: blocks from the
    slit's middle, counted as lights() counts them (for a slit that looks west, northwards)."""
    ox, oz = FACING[facing]
    return (observer[0] - middle[0]) * -oz + (observer[2] - middle[2]) * ox


def lights(radius, half, facing="west", seen=0.0, beats=LIGHT_BEATS):
    """The shaft in the slit: [(beat, (east, up, south) of the dome's middle at its springing,
    (east, up, south) one sigma of the scatter, motes)], SHAFT_ROW of them a beat.

    seen    where across the slit the comet stands for the viewer (across()); the shaft keeps to
            the other side of the slit's middle, two sigmas inside the slit's clear edge
    """
    ox, oz = FACING[facing]
    low, high = SHAFT_ARC
    along, through, wide = SHAFT_SPREAD
    side = max(0.0, half - 2.0 * wide) * (-1.0 if seen > 0 else 1.0)
    out = []
    for beat in range(beats):
        for j in range(SHAFT_ROW):
            if beat < SHAFT_FALL:       # down from the head: this beat's third of the arc, evenly
                share = (SHAFT_FALL - 1 - beat + (j + 0.5) / SHAFT_ROW) / SHAFT_FALL
            else:                       # one in every third of the arc, at a place that wanders
                share = (j + (0.5 + (beat * SHAFT_ROW + j) * GOLDEN) % 1.0) / SHAFT_ROW
            a = math.radians(low + (high - low) * share)
            off, up = radius * math.cos(a), radius * math.sin(a)
            # the command scatters along the world's axes: the arc's own two sigmas, turned into them
            level = math.hypot(along * math.sin(a), through * math.cos(a))
            rise = math.hypot(along * math.cos(a), through * math.sin(a))
            out.append((beat, (ox * off - oz * side, up, oz * off + ox * side),
                        (abs(ox) * level + abs(oz) * wide, rise, abs(oz) * level + abs(ox) * wide),
                        SHAFT_COUNT[0] if beat < SHAFT_FALL else SHAFT_COUNT[1]))
    return out


def alight(beats=LIGHT_BEATS):
    """(the fewest, the most) motes of the shaft that hang in the slit at once, from the beat the
    shaft has come down (SHAFT_FALL) to the last, whatever the game draws for their lives."""
    sent = [SHAFT_ROW * (SHAFT_COUNT[0] if beat < SHAFT_FALL else SHAFT_COUNT[1]) for beat in range(beats)]
    few, many = [], []
    for beat in range(SHAFT_FALL, beats):
        few.append(sum(n for b, n in enumerate(sent[:beat + 1]) if (beat - b) * BEAT < LIGHT_LIFE[0]))
        many.append(sum(n for b, n in enumerate(sent[:beat + 1]) if (beat - b) * BEAT < LIGHT_LIFE[1]))
    return min(few), max(many)


def tube(scope, version=None):
    """Where the stream runs on the great refractor (machines/scope), as quest() takes it:
    (where it starts, under the objective's rim; where it leaves the tube, beside the tail; where
    it ends, before the eyepiece's end face). Scene coordinates, the middle of the mount's swing."""
    sight, over = scope.SIGHT, scope.OVER
    # level and square to the tube: south, for a tube that looks west
    level = (sight[2] * over[1] - sight[1] * over[2], sight[0] * over[2] - sight[2] * over[0],
             sight[1] * over[0] - sight[0] * over[1])
    pivot, crossing = scope.pivot(version), scope.crossing(version)
    away = -1.0 if sum((pivot[i] - crossing[i]) * level[i] for i in range(3)) < 0 else 1.0
    lean = math.radians(STREAM_LEAN)
    flank = tuple(-over[i] * math.cos(lean) + away * level[i] * math.sin(lean) for i in range(3))
    top, tail = scope.objective(version), scope.eyepiece(version)
    past, behind, before = STREAM_PAST
    start = tuple(top[i] + sight[i] * past + flank[i] * STREAM_OFF[0] for i in range(3))
    rim = tuple(tail[i] - sight[i] * behind + flank[i] * STREAM_OFF[1] for i in range(3))
    mouth = tuple(tail[i] - sight[i] * before for i in range(3))
    return start, rim, mouth


def functions(charts, radius, half, facing="west", seen=0.0, stream=False, eye=None):
    """The functions of the guide's charts, {name below <namespace>:guide/: [lines]}. {ns} stands for
    the namespace; a position is the one the caller runs the function at.

    seen     where across the slit the comet stands for the one at the lens (lights())
    stream   write the stream's lines too: they name the places {start.x} .. {mouth.z}, which
             MK.function() is then to be given
    eye      the tag of a player whose eye is at the eyepiece and who sees nothing but its picture
             (machines/scope.EYE_TAG), or None: with it the close waits for that eye
    """
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
    # run as a player who stands behind the eyepiece and has not seen the comet in focus yet. With
    # an eye tag the close waits until his eye is at the eyepiece, so that the title stands on the
    # comet's picture there; until then he reads that he has all six
    at_eye = "" if eye is None else f" if entity @s[tag={eye}]"
    out["lens"] = ["function {ns}:guide/count",
                   f"execute if score @s {COUNT} matches {n_charts}..{at_eye} run return run function {{ns}}:guide/done",
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
    for beat, (dx, dy, dz), (sx, sy, sz), motes in lights(radius, half, facing, seen):
        beats.setdefault(beat, []).append(f"particle {LIGHT} ~{_num(dx)} ~{_num(dy)} ~{_num(dz)} "
                                          f"{_num(sx)} {_num(sy)} {_num(sz)} {_num(SHAFT_DRIFT)} {motes} force @s")
    if stream:
        fall = STREAM_BEATS * BEAT
        down = (f"particle {STREAM}{{target:[{{rim.x}}d,{{rim.y}}d,{{rim.z}}d],color:{STREAM_COLOUR},duration:{fall}}} "
                "{start.x} {start.y} {start.z} " + " ".join([_num(STREAM_SPREAD)] * 3) + f" 0 {STREAM_COUNT} force @s")
        hop = (f"particle {STREAM}{{target:[{{mouth.x}}d,{{mouth.y}}d,{{mouth.z}}d],color:{STREAM_COLOUR},"
               f"duration:{HOP_TICKS}}} " + "{rim.x} {rim.y} {rim.z} " + " ".join([_num(HOP_SPREAD)] * 3)
               + f" 0 {HOP_COUNT} force @s")
        for beat in range(STREAM_FROM, LIGHT_BEATS):
            if beat + STREAM_BEATS < LIGHT_BEATS:       # a bunch that is still taken up into the mouth
                beats.setdefault(beat, []).append(down)
            if beat >= STREAM_FROM + STREAM_BEATS:      # the bunch that has come down in this tick
                beats.setdefault(beat, []).append(hop)
    for beat in sorted(beats):
        out[f"glow/{beat + 1:02d}"] = beats[beat]
        glow.append(f"execute if score @s {GLOW} matches {LIGHT_BEATS - beat} run function "
                    f"{{ns}}:guide/glow/{beat + 1:02d}")
    out["glow"] = glow + [f"scoreboard players remove @s {GLOW} 1"]
    return out


def quest(canvas, charts, observer, dome, origin=(0, 0, 0), stands=None, tube=None, eye=None):
    """Register the charts' tests and the lens's on the canvas.

    charts     [(name, the middle of the chart's face (x, y, z), the y of the floor one stands on
               beside it)], chart 1 first: _guide_charts.CHARTS
    stands     for every chart the spot of that floor one stands on to read it, or None:
               _guide_charts.STAND
    observer   where the observer's feet stand behind the eyepiece
    dome       (the middle of the dome at its springing, the radius of its skin, the clear half of
               its slit's width, the way the slit looks): slit()
    tube       (where the stream of the close starts, where it leaves the tube, where it ends in
               the eyepiece's mouth): tube(); None for a close without the stream
    eye        the tag of a player whose eye is at the eyepiece (machines/scope.EYE_TAG), or None
    All in scene coordinates, plus origin. Returns 0: no display entity is placed.
    """
    middle, radius, half, facing = dome
    places = None if tube is None else dict(zip(("start", "rim", "mouth"), tube))
    for name, lines in functions(charts, radius, half, facing, across(observer, middle, facing),
                                 stream=tube is not None, eye=eye).items():
        if places is not None and name.startswith("glow/"):
            MK.function(canvas, f"guide/{name}", lines, pos=places, origin=origin)
        else:
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
    # the lights are for the eye that has left the eyepiece: at it, the picture hides the world
    away = "" if eye is None else ",tag=!" + eye
    MK.run(canvas, middle, "execute positioned {x} {y} {z} as @a[scores={" + GLOW + "=1..}" + away
           + "] run function {ns}:guide/glow", BEAT, at=(LENS_AT,), origin=origin)
    return 0


def build(canvas, origin=(0, 0, 0)):
    if not enabled():
        return 0
    charts = _package("motion", "_guide_charts")
    scope = _package("machines", "scope")
    if charts is None or scope is None:
        return 0
    n = charts.build(canvas, origin) or 0
    quest(canvas, charts.CHARTS, scope.OBSERVER[scope.VERSION], slit(), origin, stands=getattr(charts, "STAND", None),
          tube=tube(scope), eye=getattr(scope, "EYE_TAG", None))
    return n
