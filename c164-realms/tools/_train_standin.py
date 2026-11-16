"""TRIAL ONLY -- never for the assembly. Runs export.py with a stand-in train in the scene's data
pack, so that what export.py does with the train as the world is saved (train_set) and verify's
check of it can be run before the real travel (motion/travel, a2 c322) is in the tree.

    python tools/_train_standin.py [--opening] make --scene obs --name T1 ...     (export.py's own arguments)

The stand-in is three switches and a clock, with the names a2 gave (#89128, #92877):
  train/park      #t.train = 0, the clock stopped: at rest until it is sent off
  train/go        the clock runs: 8 s up (1), 4 s in the station (2), 8 s down (3), 12 s at rest (0), and round again
  train/restart   both
It is written into the pack after the scene is placed, the pack is read again and the train is sent
off, as the real one keeps its timetable while the save is made.

--opening makes the save as of a scene with the opening on (spec.arrival, 300 ticks at the most):
tools/_opening_standin.py puts the stand-in functions of the opening into the archive afterwards.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export as E

UP, STAND, DOWN, REST = 160, 80, 160, 240
ROUND = UP + STAND + DOWN + REST
OBJ = E.TRAIN[1]
ON, CLOCK, STATE = "#standin.on", "#standin.clock", E.TRAIN[0]


def functions():
    going = f"execute if score {ON} {OBJ} matches 1 "
    spans = ((1, UP, 1), (UP + 1, UP + STAND, 2), (UP + STAND + 1, UP + STAND + DOWN, 3), (UP + STAND + DOWN + 1, ROUND, 0))
    return {
        "park": [
            f"scoreboard objectives add {OBJ} dummy",
            f"scoreboard players set {STATE} {OBJ} 0",
            f"scoreboard players set {ON} {OBJ} 0",
            f"scoreboard players set {CLOCK} {OBJ} 0",
        ],
        "go": [
            f"execute unless score {ON} {OBJ} matches 1 run scoreboard players set {CLOCK} {OBJ} 0",
            f"scoreboard players set {ON} {OBJ} 1",
            f"scoreboard players set {STATE} {OBJ} 1",
        ],
        "restart": [
            f"function {E.ART}:train/park",
            f"function {E.ART}:train/go",
        ],
        "standin_tick": [
            going + f"run scoreboard players add {CLOCK} {OBJ} 1",
            going + f"if score {CLOCK} {OBJ} matches {ROUND + 1}.. run scoreboard players set {CLOCK} {OBJ} 1",
            *(going + f"if score {CLOCK} {OBJ} matches {a}..{b} run scoreboard players set {STATE} {OBJ} {state}"
              for a, b, state in spans),
        ],
    }


def with_train(place):
    def placed(spec, server, *more):
        text = place(spec, server, *more)
        if "--look-only" in more:
            return text
        data = os.path.join(server.world, "datapacks", E.PACK, "data")
        folder = os.path.join(data, E.ART, "function", "train")
        os.makedirs(folder, exist_ok=True)
        for name, body in functions().items():
            with open(os.path.join(folder, name + ".mcfunction"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write("\n".join(body) + "\n")
        tick = os.path.join(data, "minecraft", "tags", "function", "tick.json")
        with open(tick, encoding="utf-8") as fh:
            tag = json.load(fh)
        tag["values"].append(f"{E.ART}:train/standin_tick")
        with open(tick, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(tag, fh, indent=1)
            fh.write("\n")
        E.say("TRIAL: a stand-in train is written into the pack: " + ", ".join(sorted(functions()))
              + f"; the tick tag is {tag['values']}")
        server.cmd("reload")
        server.cmd(f"function {E.ART}:train/restart")
        return text
    return placed


def main():
    if "--opening" in sys.argv:
        sys.argv.remove("--opening")
        E.arrival = lambda name, scene, off=False: None if off else {"most": 300}
    E.place = with_train(E.place)
    E.main()


if __name__ == "__main__":
    main()
