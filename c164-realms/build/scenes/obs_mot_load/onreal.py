#!/usr/bin/env python3
"""The load scene on the real machine: what its loop costs the server (plan/parts/motion.md
sections 7 and 10).

Run by the render post's trip after the scene's shots, while the scene stands, the server runs
and the game is open:

    tools/nodetrip.py ... --after obs_mot_load=scenes/obs_mot_load/onreal.py

which calls, from build/,   scenes/obs_mot_load/onreal.py --pw-file <file> --port <n> --origin X Y Z

The checks, in the order they are made (scenes/obs/motion/_onreal.py has them):

    ready     the scene stands and its loop is the one that runs
    ended     the beat board's loop, when it ran in this world before this scene was started,
              has ended itself: nothing of it is queued (section 10, item 5)
    alive     two wheels of every phase are read for three turns: a part that is given a phase
              is where the plan has it (the beat board has no such part)
    cost      the game sprints with the loop running and with it stopped, three times each: the
              difference is what 35 commands a tick cost

It leaves the server running and the loop started. About 60 seconds.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scenes.obs.motion import _onreal as R  # noqa: E402
from scenes.obs_mot_load import REV, SPREAD, build  # noqa: E402
from scenes.obs_mot_loop import build as board  # noqa: E402


def main(argv=None):
    args, server = R.connect(argv, __doc__)
    bench = R.Bench(server, build(), "obs_mot_load", args.origin, seconds=args.seconds)
    # two wheels of every phase: a near one and a far one
    sample = []
    for phase in range(SPREAD):
        same = [r for r in bench.readers if r.part.phase == phase]
        sample += [same[0], same[-1]]
    return bench.run([("ready", bench.ready, 12),
                      ("ended", lambda: bench.ended("obs_mot_loop", board()), 10),
                      ("alive", lambda: bench.alive(3 * REV, sample), 10),
                      ("cost", bench.cost, 70)])


if __name__ == "__main__":
    sys.exit(main())
