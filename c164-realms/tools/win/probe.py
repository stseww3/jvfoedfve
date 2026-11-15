#!/usr/bin/env python3
"""A measurement on the test server: from how far away does the client still get display entities?

    probe.py summon --at <x> <y> <z>     two block displays above that point, tagged c164probe:
                                         glowstone, 6 blocks across, view_range 10 (640 blocks);
                                         sea lantern 12 higher, 6 across, view_range left at 1 (64)
    probe.py kill                        remove them

The shots probe_* of shots/obs-overview.json look at them from 55, 150, 158, 165 and 200 blocks.
What the game's code says (26.3): the server sends a display entity to a player within 10 chunks
= 160 blocks, measured on the ground (x and z only), whatever view_range says; the client then
draws it within view_range x 64 blocks x the "entity distance" setting.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rcon import Rcon  # noqa: E402

ROOT = os.path.abspath(os.environ.get("MC_ROOT", os.getcwd()))
TAG = "c164probe"


def display(block, x, y, z, extra=""):
    return (f"summon minecraft:block_display {x} {y} {z} {{block_state:{{Name:\"minecraft:{block}\"}},"
            "transformation:{left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f],scale:[6f,6f,6f],"
            f"translation:[-3f,-3f,-3f]}},brightness:{{sky:15,block:15}},Tags:[\"{TAG}\"]{extra}}}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=("summon", "kill"))
    ap.add_argument("--at", type=int, nargs=3, metavar=("X", "Y", "Z"))
    args = ap.parse_args()
    with open(os.path.join(ROOT, "server26", ".rcon_pw")) as fh:
        rc = Rcon(port=25598, password=fh.read().strip())
    try:
        print(rc.command(f"kill @e[tag={TAG}]").strip())
        if args.what == "summon":
            if not args.at:
                raise SystemExit("--at is needed")
            x, y, z = args.at
            print(rc.command(display("glowstone", x, y, z, ",view_range:10f")).strip())
            print(rc.command(display("sea_lantern", x, y + 12, z)).strip())
            print(rc.command(f"execute as @e[tag={TAG}] run data get entity @s view_range").strip())
    finally:
        rc.close()


if __name__ == "__main__":
    main()
