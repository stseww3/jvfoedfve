#!/usr/bin/env python3
"""place.py for a scene that is built for another light version than the default one.

    placelook.py <look> [--dress] <scene> --world <folder> --pw-file <file> --at X Y Z ...
    placelook.py --tick <look>          print the tick that light version is shot at and the look
                                        whose windows it has ("18000 deep"), nothing else

The sky, the fog and the colours of the light of a light version come with the time (the timeline
of scenes/obs/sky/mood.py: blue 14000, deep 18000, glow 12900). Which windows are lit does not:
windows are blocks, so a scene is built for one version, the default one, and the sky line's light
kit knows what each of the others lights (sky/_lightkit.py: the table, under()). This builds the
scene with every front glazed for the version named and hands it to place.py, whose arguments
follow the look's name; the pictures are then taken at that version's tick. A trial of the sky
line (mood.TRIALS: a look with a few values changed, held at a tick of its own) is named the same
way: its windows are those of the look it varies.

--dress also turns on the building's own lights (the sources behind the lit windows of main's
table and the wall wash; the switch DRESS of sky/lights.py, which the director keeps off until
the review of that card has passed): a picture of what the switch will do, not of the code as
it stands.

The code is that of the build/ folder this is run from, or of the folder named in the environment
variable C164_BUILD: the render station places other checkouts with its own tools. Nothing in that
code is changed; what is said here holds for the one build this process makes. The scenes are the
observatory's, those whose fronts ask scenes.obs.sky._lightkit which windows are lit.
"""
import os
import sys


def known(mood, name):
    """The name, when it is a look or a trial of the code that is shot; else the end."""
    trials = getattr(mood, "TRIALS", {})
    if name not in mood.LOOKS and name not in trials:
        sys.exit(f"no look {name!r}; there are {', '.join(mood.LOOKS)}"
                 + (f" and the trials {', '.join(trials)}" if trials else ""))
    return name


def windows_of(mood, name):
    """The look whose table lights the windows: the look itself, or the one a trial varies."""
    return name if name in mood.LOOKS else mood.TRIALS[name]["of"]


def main():
    build = os.path.abspath(os.environ.get("C164_BUILD") or os.getcwd())
    if not os.path.isfile(os.path.join(build, "place.py")):
        sys.exit(f"no place.py in {build}: run this from a build/ folder, or name one in C164_BUILD")
    sys.path.insert(0, build)
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "--tick":
        from scenes.obs.sky import mood
        print(mood.tick(known(mood, args[1])), windows_of(mood, args[1]))
        return 0
    dress = "--dress" in args
    args = [a for a in args if a != "--dress"]
    if len(args) < 2 or args[0].startswith("-"):
        sys.exit(__doc__.split("\n\n")[1])
    look, rest = args[0], args[1:]

    import place
    from scenes.obs.sky import _lightkit as L
    from scenes.obs.sky import mood
    of = windows_of(mood, known(mood, look))
    said = (f"built for look {look} (shot at tick {mood.tick(look)}): the windows are lit by "
            + ("that look's table" if of == look else f"the table of {of}, the look it is a trial of"))
    if dress:
        from scenes.obs.sky import lights
        lights.DRESS = True
        said += "; the building's own lights are on (sky/lights DRESS)"
    print(said, flush=True)
    sys.argv = [os.path.join(build, "place.py")] + rest
    with L.under(look):
        return place.main()


if __name__ == "__main__":
    sys.exit(main())
