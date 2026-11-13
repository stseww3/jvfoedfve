#!/usr/bin/env python3
"""Check player-dependent mechanics on a local 26.3 server with a fake player.

Covers what a Realms minigame relies on: no operator rights, /trigger input, rejoin detection via
custom:leave_game, and that chat / title / action bar / dialog output reaches the player.

    player_logic_check.py --pw-file <server>/.rcon_pw [--port 25599] [--rcon-port 25598]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))

from mcbot import Bot  # noqa: E402
from rcon import Rcon  # noqa: E402

NAME = "C164Bot"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pw-file", required=True)
    ap.add_argument("--port", type=int, default=25599)
    ap.add_argument("--rcon-port", type=int, default=25598)
    args = ap.parse_args()

    with open(args.pw_file) as fh:
        rc = Rcon(port=args.rcon_port, password=fh.read().strip())

    results = []

    def check(label, ok, detail=""):
        results.append(ok)
        print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  [{detail}]" if detail else ""))

    for cmd in (
        "forceload add 0 0 15 15",
        "fill 6 -64 6 10 -64 10 minecraft:smooth_stone",
        "scoreboard objectives remove c164.trig",
        "scoreboard objectives remove c164.leave",
        "scoreboard objectives add c164.trig trigger",
        "scoreboard objectives add c164.leave minecraft.custom:minecraft.leave_game",
    ):
        rc.command(cmd)

    bot = Bot(NAME, port=args.port).connect()
    bot.pump(1.0)
    check("fake player joins and stays connected", bot.pump(0.5), f"pos={bot.position}")

    listing = rc.command("list")
    check("server lists the player", NAME in listing, listing)

    # 1. no operator rights
    bot.command("gamemode creative")
    bot.pump(1.0)
    mode = rc.command(f"data get entity {NAME} playerGameType")
    check("non-OP player cannot change game mode", "command.unknown" in " ".join(bot.texts("chat")) and mode.strip().endswith("2"), mode)

    # 2. trigger input
    bot.command("trigger c164.trig set 5")
    bot.pump(1.0)
    score = rc.command(f"scoreboard players get {NAME} c164.trig")
    check("trigger is refused until enabled", "has 5" not in score, score)
    rc.command(f"scoreboard players enable {NAME} c164.trig")
    bot.command("trigger c164.trig set 5")
    bot.pump(1.0)
    score = rc.command(f"scoreboard players get {NAME} c164.trig")
    check("trigger sets the score once enabled", "has 5" in score, score)

    # 3. output reaching the player
    bot.events.clear()
    rc.command(f'tellraw {NAME} {{"text":"hello ","extra":[{{"text":"bot","color":"gold"}}]}}')
    rc.command(f'title {NAME} title {{"text":"Round 1"}}')
    rc.command(f'title {NAME} actionbar "moss: 3"')
    rc.command(f'dialog show {NAME} {{type:"minecraft:notice",title:"Hi",body:[{{type:"minecraft:plain_message",contents:"Body"}}]}}')
    bot.pump(1.5)
    check("tellraw reaches the player", "hello bot" in bot.texts("chat"), str(bot.texts("chat")))
    check("title reaches the player", "Round 1" in bot.texts("title"), str(bot.texts("title")))
    check("action bar reaches the player", "moss: 3" in bot.texts("actionbar"), str(bot.texts("actionbar")))
    check("dialog is shown to the player", len(bot.texts("dialog")) == 1, str(bot.texts("dialog")))

    # 4. rejoin detection
    before = rc.command(f"scoreboard players get {NAME} c164.leave")
    bot.close()
    bot = Bot(NAME, port=args.port).connect()
    bot.pump(1.0)
    after = rc.command(f"scoreboard players get {NAME} c164.leave")
    check("leave_game counts a disconnect", "has 1" in after and "has 1" not in before, f"before: {before} | after: {after}")

    bot.close()
    rc.close()
    print(f"{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
