#!/usr/bin/env python3
"""The beat board on the real machine: what no picture shows (plan/parts/motion.md section 10).

Run by the render post's trip after the scene's shots, while the scene stands, the server runs
and the game is open:

    tools/nodetrip.py ... --after obs_mot_loop=scenes/obs_mot_loop/onreal.py

which calls, from build/,   scenes/obs_mot_loop/onreal.py --pw-file <file> --port <n> --origin X Y Z

The checks, in the order they are made (scenes/obs/motion/_onreal.py has them):

    ready     the scene stands and its loop is the one that runs
    record    an earlier run left the chains' clocks in the world: is the loop still in step with
              them (a second trip with --no-place, after the server was down: section 10, item 1)
    alive     every pose that is read is one of the plan's, on the tick the plan has it; the
              guard at the head of every chain lets a loop that is the world's go on (item 6)
    steps     the game sprints through the longest cycle: every step of every part is read once
    reload    /reload with the loop alive does not start it anew (item 1)
    broken    the queue is cleared by hand: after /reload the loop starts itself again (item 2)
    takeover  #run goes to another loop: the chains end themselves within a round of the
              quickest, and the lines after the guard are not run (items 5 and 6)
    unload    everybody far away, nothing force-loaded: the chains run on without the entities,
              and every part is right again at its next step when somebody comes back (item 3)
    stop      every part back as it was placed, and /reload does not start it (items 2 and 4)
    start     every chain sets off one tick and its offset after the start

It leaves the server running, the loop started, the camera where it stood and the same chunks
force-loaded. About 100 seconds.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scenes.obs.motion import _onreal as R  # noqa: E402
from scenes.obs_mot_loop import build  # noqa: E402


def main(argv=None):
    args, server = R.connect(argv, __doc__)
    bench = R.Bench(server, build(), "obs_mot_loop", args.origin, seconds=args.seconds)
    return bench.run([("ready", bench.ready, 5), ("record", bench.kept, 12), ("alive", bench.alive, 22),
                      ("steps", bench.every_step, 20), ("reload", bench.reload_alive, 25),
                      ("broken", bench.broken, 30), ("takeover", bench.takeover, 15),
                      ("unload", bench.unloaded, 60), ("stop", bench.stopped, 30), ("start", bench.started, 12)])


if __name__ == "__main__":
    sys.exit(main())
