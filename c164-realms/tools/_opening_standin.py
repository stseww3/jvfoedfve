"""TRIAL ONLY -- never for the assembly. Puts a stand-in opening into a save that export.py made,
so that verify's checks of the opening (ride_in, ride_broken) can be run before the real functions
(motion/arrival, mast c346) are there.

    python tools/_opening_standin.py <save>.zip

The stand-in does what mast described (#86008, #88393), on a seat of its own instead of the train:
  guide/first   the newcomer gets the tags c164.new and c164.rider and is set on a seat (an item
                display summoned where he stands)
  guide/train   every tick: his seat is carried up and south for 120 ticks and back for 120 (the
                air there is free in A8); at tick 250 he is off
  guide/arrive  whoever still rides: off the seat, the seat gone, function c164map:back; and the
                title at that moment (the director's #92375: as he gets off)
  guide/join    who comes back riding: the same; who comes back with c164.new gets the title then
The note beside the archive is rewritten for the new archive, with spec.arrival = {"most": 300}.
"""
import json
import os
import shutil
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export as E

OUT, BACK, OFF, MOST = 120, 240, 250, 300
STEP = (0.0, 0.2, 0.1)


def main():
    archive = os.path.abspath(sys.argv[1])
    name = os.path.basename(archive)[:-4]
    with open(archive[:-4] + ".json", encoding="utf-8") as fh:
        made = json.load(fh)
    lines = made["spec"].get("title_lines") or ["TITLE"]
    work = tempfile.mkdtemp(prefix="standin-")
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(work)
    world = os.path.join(work, name)
    data = os.path.join(world, "datapacks", E.PACK, "data")
    guide = os.path.join(data, E.ART, "function", "guide")
    os.makedirs(guide, exist_ok=True)
    art, ns = E.ART, E.NS
    go = E.train_functions(os.path.join(world, "datapacks", E.PACK)).get("go")      # the train leaves with him
    fwd = "~{} ~{} ~{}".format(*STEP)
    rev = "~{} ~{} ~{}".format(*(-v for v in STEP))
    files = {
        "first": [
            "tag @s add c164.new",
            "tag @s add c164.rider",
            "scoreboard objectives add c164ride dummy",
            "scoreboard players set @s c164ride 0",
            'summon minecraft:item_display ~ ~ ~ {Tags:["c164.seat","c164.seat.new"]}',
            "ride @s mount @e[tag=c164.seat.new,limit=1,sort=nearest]",
            "tag @e[tag=c164.seat.new] remove c164.seat.new",
            *([f"function {go}"] if go else []),
        ],
        "train": [
            "execute as @a[tag=c164.rider] run scoreboard players add @s c164ride 1",
            f"execute as @a[tag=c164.rider,scores={{c164ride=1..{OUT}}}] on vehicle at @s run tp @s {fwd}",
            f"execute as @a[tag=c164.rider,scores={{c164ride={OUT + 1}..{BACK}}}] on vehicle at @s run tp @s {rev}",
            f"execute as @a[tag=c164.rider,scores={{c164ride={OFF}..}}] at @s run function {art}:guide/arrive",
        ],
        "arrive": [
            "tag @s remove c164.rider",
            f"execute if predicate {ns}:{E.RIDING} run function {art}:guide/off",
            f"execute if entity @s[tag=c164.new] run function {art}:guide/title2",
        ],
        "off": [
            "execute on vehicle run tag @s add c164.seat.done",
            "ride @s dismount",
            "kill @e[tag=c164.seat.done]",
            f"function {ns}:back",
        ],
        "join": [
            f"execute if predicate {ns}:{E.RIDING} run function {art}:guide/off",
            "tag @s remove c164.rider",
            f"execute if entity @s[tag=c164.new] run function {art}:guide/title2",
        ],
        "title2": [
            "title @s times 20 80 30",
            *([f"title @s subtitle {E.snbt(lines[1])}"] if lines[1:] else []),
            f"title @s title {E.snbt(lines[0])}",
            "tag @s remove c164.new",
        ],
    }
    for fn, body in files.items():
        with open(os.path.join(guide, fn + ".mcfunction"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(body) + "\n")
    tick = os.path.join(data, "minecraft", "tags", "function", "tick.json")
    with open(tick, encoding="utf-8") as fh:
        tag = json.load(fh)
    tag["values"].append(f"{art}:guide/train")
    with open(tick, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(tag, fh, indent=1)
        fh.write("\n")
    os.remove(archive)
    count = E.zip_tree(world, archive, name, 0)
    shutil.rmtree(work)
    made["spec"]["arrival"] = {"most": MOST}
    made["zip"].update(bytes=os.path.getsize(archive), sha256=E.sha256_of(archive), files=count)
    made.setdefault("notes", []).append("TRIAL: a stand-in opening was put into this archive (tools/_opening_standin.py)")
    with open(archive[:-4] + ".json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(made, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(f"stand-in opening written into {os.path.basename(archive)}: {sorted(files)}; tick tag {tag['values']}; "
          f"{count} files, sha256 {made['zip']['sha256'][:16]}")


if __name__ == "__main__":
    main()
