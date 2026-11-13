#!/usr/bin/env python3
"""Generate a throw-away datapack used to check the build pipeline against a real 26.3 server.

It contains the same small room twice, once as a native 26.3 template and once in the 26.1.2
dialect, plus load/tick/build functions. Usage:
    make_test_pack.py <world>/datapacks/c164test
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))

from nbtlib import Byte, Compound, Int, List, String  # noqa: E402

from mcstructure import Structure  # noqa: E402

PACK_FORMAT = 121  # data_major of 26.3 (version.json inside the server jar)


def room():
    s = Structure()
    s.fill(0, 0, 0, 6, 4, 6, "stone_bricks", hollow=True)
    s.fill(1, 0, 1, 5, 0, 5, "polished_tuff")
    s.fill(3, 1, 0, 3, 2, 0, "air")
    for x in (1, 5):
        for z in (1, 5):
            s.set(x, 1, z, "chiseled_tuff_bricks")
    s.set(1, 1, 3, "oak_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]")
    s.set(5, 1, 3, "oak_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]")
    s.set(3, 3, 3, "lantern[hanging=true,waterlogged=false]")
    s.set(3, 1, 5, "oak_sign[rotation=8,waterlogged=false]", nbt=Compound({
        "id": String("minecraft:sign"),
        "is_waxed": Byte(1),
        "front_text": Compound({
            "messages": List[String]([String("c164"), String("pipeline"), String("test"), String("")]),
            "color": String("black"),
            "has_glowing_text": Byte(0),
        }),
        "back_text": Compound({
            "messages": List[String]([String(""), String(""), String(""), String("")]),
            "color": String("black"),
            "has_glowing_text": Byte(0),
        }),
    }))
    s.set(1, 1, 4, "barrel[facing=up,open=false]", nbt=Compound({
        "id": String("minecraft:barrel"),
        "Items": List[Compound]([
            Compound({"Slot": Byte(0), "id": String("minecraft:moss_block"), "count": Int(7)}),
        ]),
    }))
    s.add_entity(3.5, 1.0, 3.5, Compound({
        "id": String("minecraft:marker"),
        "Tags": List[String]([String("c164.marker")]),
    }))
    s.add_entity(3.5, 2.0, 2.5, Compound({
        "id": String("minecraft:item_display"),
        "Tags": List[String]([String("c164.display")]),
        "item": Compound({"id": String("minecraft:oxidized_copper"), "count": Int(1)}),
    }))
    return s


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def main():
    out = sys.argv[1]
    write(os.path.join(out, "pack.mcmeta"), json.dumps({
        "pack": {"description": "c164 pipeline test", "min_format": PACK_FORMAT, "max_format": PACK_FORMAT},
        "filter": {"block": [
            {"namespace": "minecraft", "path": "recipe"},
            {"namespace": "minecraft", "path": "advancement"},
        ]},
    }, indent=2))

    fn = os.path.join(out, "data", "c164", "function")
    write(os.path.join(fn, "load.mcfunction"), "\n".join([
        "scoreboard objectives add c164 dummy",
        "scoreboard players set #loaded c164 1",
        "scoreboard players set #ticks c164 0",
    ]) + "\n")
    write(os.path.join(fn, "tick.mcfunction"), "scoreboard players add #ticks c164 1\n")
    write(os.path.join(fn, "build.mcfunction"), "\n".join([
        "forceload add 0 0 47 15",
        "place template c164:room_new 0 64 0",
        "place template c164:room_legacy 16 64 0",
        "fill 32 64 0 38 64 6 minecraft:polished_tuff",
        "setblock 35 65 3 minecraft:oak_stairs[facing=north,half=bottom]",
    ]) + "\n")

    tags = os.path.join(out, "data", "minecraft", "tags", "function")
    write(os.path.join(tags, "load.json"), json.dumps({"values": ["c164:load"]}))
    write(os.path.join(tags, "tick.json"), json.dumps({"values": ["c164:tick"]}))

    st = os.path.join(out, "data", "c164", "structure")
    os.makedirs(st, exist_ok=True)
    r = room()
    r.save(os.path.join(st, "room_new.nbt"), fmt="26.3")
    r.save(os.path.join(st, "room_legacy.nbt"), fmt="legacy")
    print("wrote", out, "blocks per room:", len(r.blocks))


if __name__ == "__main__":
    main()
