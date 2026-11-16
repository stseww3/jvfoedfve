"""python -m scenes.obs_mot_sound          writes shots.json of this test scene from the floor's numbers
python -m scenes.obs_mot_sound spots    the sound spots of the master scene as they are registered now
                                        (builds the master scene: on a worker node, not the shared machine)"""
import json
import os
import sys

from . import shots


def spots():
    from scenes import obs
    from scenes.obs.motion import sound
    rows, total = sound.spots(obs.build()), 0.0
    for event, pos, cycle, ticks, reach in rows:
        a_second = 20.0 * len(ticks) / cycle
        total += a_second
        print(f"{event:<13} ({pos[0]:7.2f}, {pos[1]:6.2f}, {pos[2]:7.2f})  {len(ticks)} in {cycle:3d} ticks, "
              f"reach {reach:g}, {a_second:.2f} a second")
    print(f"{len(rows)} spots of motion/sound in the master scene, {total:.1f} playsound commands a second")


if __name__ == "__main__":
    if sys.argv[1:] == ["spots"]:
        spots()
    else:
        path = os.path.join(os.path.dirname(__file__), "shots.json")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("[\n" + ",\n".join(" " + json.dumps(s) for s in shots()) + "\n]\n")
        print(f"{len(shots())} shots -> {path}")
