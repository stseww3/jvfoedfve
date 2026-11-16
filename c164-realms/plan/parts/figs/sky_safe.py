#!/usr/bin/env python3
"""The sky a world can have when its data pack carries no registry file (card sky/safe-look).

    python plan/parts/figs/sky_safe.py [--jar <26.3 client jar>] [--biome plains] [--chunks 12]
        [--head 41] [--at 20380,22600,13300] [--scan]

Without a biome and a timeline of our own the look is what the game's own files make of the hour:
the dimension type `overworld`, a vanilla biome and the timelines `day` and `moon`, all read here
from the client jar and run through the arithmetic of artkit/gamelook.py (the layers of the
attributes, the light table) and of plan/parts/sky-notes.md 3 (how the sky takes the fog). The
only things left to choose are the hour the clock is stopped at, the day (it picks the moon's
picture) and the biome the plot is filled with.

It prints
  1. the hour at which the vanilla clock puts the comet's head where the plan has it (--head,
     degrees above due west), for a head painted below, on and above the middle of the moon's
     square: the moon turns with the sun, 180 degrees behind it
  2. with --scan, the night from dusk to dawn in steps: where both bodies stand and what the
     timeline has made of sky, fog, light and stars by then
  3. for every hour of --at: the attributes, what is seen of the sky at view distance --chunks
     (overhead, at 45, 20 and 10 degrees, on the horizon, and on the horizon facing the vanilla
     sunrise or sunset), the vanilla cloud layer, and the ladder of sky/_tones.py --ladder on the
     plan's dressed stone; the plan's own three looks beside it

It prints; it judges nothing. numpy only.
"""
import argparse
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(PROJECT, "build"))

from artkit import gamelook  # noqa: E402
from artkit.gameassets import Assets  # noqa: E402

DATA = "data/minecraft/"
JAR = os.path.join(os.environ.get("MC_ROOT", "/agent/realms-study"), "client26", "versions", "26.3", "26.3.jar")
DAY = 24000
MOON_HALF = math.degrees(math.atan(gamelook.MOON_SIZE / 100.0))    # the moon's square reaches this far from its middle
SUN_HALF = math.degrees(math.atan(gamelook.SUN_SIZE / 100.0))
PHASES = ("full_moon", "waning_gibbous", "third_quarter", "waning_crescent", "new_moon", "waxing_crescent",
          "first_quarter", "waxing_gibbous")
FACES = (("top", 1.0), ("north or south", 0.8), ("east or west", 0.6))   # the game's shading of a block's faces


def _hex(c):
    return "#" + "".join(f"{max(0, min(255, int(round(float(v) * 255.0)))):02x}" for v in c[:3])


def _luma(c):
    return float(0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2])       # Rec.601, as sky/_tones.py measures


class Vanilla:
    """The game's own overworld: its dimension type, its timelines in the order of the tag."""

    def __init__(self, jar):
        self.assets = Assets(jar)
        self.dimension = self.assets.json(f"{DATA}dimension_type/overworld.json")
        self.lines = self._timelines("in_overworld")

    def _timelines(self, tag):
        out = []
        for value in self.assets.json(f"{DATA}tags/timeline/{tag}.json")["values"]:
            if value.startswith("#"):
                out += self._timelines(value.partition(":")[2])
            else:
                out.append(self.assets.json(f"{DATA}timeline/{value.partition(':')[2]}.json"))
        return out

    def biome(self, name):
        data = self.assets.json(f"{DATA}worldgen/biome/{name}.json")
        if data is None:
            raise SystemExit(f"the jar has no biome {name!r}")
        return data

    def at(self, tick, biome):
        """The visual attributes at a tick of the clock (the day and the hour: tick // 24000 is the
        day, which the moon's timeline reads)."""
        a = gamelook.attributes(tick, self.dimension, biome, self.lines)
        # A timeline blends its keyframes with the type's keyframe function, which for an angle
        # is the plain one of a number (AttributeTypes.ANGLE_DEGREES: LerpFunction.ofFloat();
        # the turn-aware ofDegrees(90) is for changes of state): the vanilla sun runs 0..360.
        for tl in self.lines:
            for key, track in tl.get("tracks", {}).items():
                name = key[len(gamelook.VISUAL):]
                if key.startswith(gamelook.VISUAL) and name in gamelook.ANGLES:
                    a[name] = gamelook._apply(gamelook.DEFAULTS[name], track.get("modifier"),
                                              gamelook._sample(track, tick, tl.get("period_ticks", DAY), angle=False))
        return a

    def moon_angle(self, tick):
        return float(self.at(tick, {})["moon_angle"]) % 360.0


def lock(v, moon_angle):
    """The hour after midnight at which the moon stands at this angle (0 overhead, 90 on the
    western horizon): (tick, the angle at that whole tick)."""
    lo, hi = 18000, 18000 + DAY // 2
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if v.moon_angle(mid) < moon_angle:
            lo = mid
        else:
            hi = mid
    best = min((lo, hi), key=lambda t: abs(v.moon_angle(t) - moon_angle))
    return best, v.moon_angle(best)


def seen(a, chunks):
    """What the sky shows: {name: colour}. The dome is a plane 16 blocks overhead that takes fog by
    distance, the fog colour is drawn towards the sky colour first (sky-notes.md 3)."""
    reach = min(chunks * 16.0, float(a["sky_fog_end_distance"]))
    mix = 1.0 - (0.25 + 0.75 * min(1.0, reach / 16.0 / 32.0)) ** 0.25
    sky, fog = a["sky_color"][:3], a["fog_color"][:3]
    haze = fog + (sky - fog) * mix
    out = {}
    for name, up in (("overhead", 90.0), ("45 degrees up", 45.0), ("20 degrees up", 20.0), ("10 degrees up", 10.0)):
        rho = 16.0 / math.tan(math.radians(up)) if up < 90.0 else 0.0
        share = min(1.0, (16.0 + 496.25 * rho / 512.0) / reach)
        out[name] = sky + (haze - sky) * share
    out["horizon"] = haze
    glow = a["sunrise_sunset_color"]
    if len(glow) == 4 and glow[3] > 0.004:
        side = "west" if math.sin(math.radians(float(a["sun_angle"]))) > 0.0 else "east"
        out[f"horizon, facing {side} (the game's own {'sunset' if side == 'west' else 'sunrise'})"] = \
            haze + (glow[:3] - haze) * glow[3]
    return out


def ladder(a, stone, glass):
    """The rows of sky/_tones.py --ladder under these attributes: [(name, colour)]."""
    table = gamelook.lightmap(a)
    east, south, top = 0.6, 0.8, 1.0
    return [("stone out of the sky's and the lamps' reach, top face", stone * table[0][0] * top),
            ("stone under the sky, east or west face", stone * table[15][0] * east),
            ("stone under the sky, north or south face", stone * table[15][0] * south),
            ("stone under the sky, top face", stone * table[15][0] * top),
            ("stone washed by a lamp (level 7), east or west face", stone * table[15][7] * east),
            ("stone beside a lamp (level 10), east or west face", stone * table[15][10] * east),
            ("stone beside a lamp (level 12), east or west face", stone * table[15][12] * east),
            ("stone beside a lamp (level 10), top face", stone * table[15][10] * top),
            ("glass of a lit window at full light", glass)]


def bodies(a):
    """Where the two squares stand: text."""
    out = []
    for name, half in (("moon", MOON_HALF), ("sun", SUN_HALF)):
        angle = float(a[f"{name}_angle"]) % 360.0
        up = 90.0 - angle if angle <= 180.0 else angle - 270.0
        side = "west" if angle <= 180.0 else "east"
        out.append(f"{name} {up:+.1f} in the {side} (square {up - half:+.1f} to {up + half:+.1f})")
    return "; ".join(out)


def report(v, tick, biome_name, chunks, stone, glass):
    a = v.at(tick, v.biome(biome_name))
    hour, day = tick % DAY, tick // DAY
    print(f"\n==== time set {tick} (hour {hour} of day {day}), biome minecraft:{biome_name}, view distance {chunks}")
    print(f"  bodies: {bodies(a)}")
    print(f"  moon's picture: {a['moon_phase']} (the day picks it: day {day} of eight)")
    glow = a["sunrise_sunset_color"]
    print(f"  attributes: sky_color {_hex(a['sky_color'])}  fog_color {_hex(a['fog_color'])}  "
          f"cloud_color {_hex(a['cloud_color'])} alpha {a['cloud_color'][3]:.2f}  "
          f"sky_light_color {_hex(a['sky_light_color'])} factor {a['sky_light_factor']:.2f}  "
          f"ambient {_hex(a['ambient_light_color'])}  block_light_tint {_hex(a['block_light_tint'])}")
    print(f"              star_brightness {a['star_brightness']:.2f} (adds {a['star_brightness'] ** 2:.2f})  "
          f"sunrise_sunset_color {_hex(glow)} alpha {glow[3]:.2f}  "
          f"fog {a['fog_start_distance']:.0f}..{a['fog_end_distance']:.0f}  sky fog end {a['sky_fog_end_distance']:.0f}")
    print("  seen of the sky:")
    for name, c in seen(a, chunks).items():
        print(f"    {_hex(c)}  {_luma(c):.2f}  {name}")
    cloud = a["cloud_color"]
    print(f"  the vanilla cloud layer, top face: {_hex(cloud)} {_luma(cloud):.2f} at opacity {cloud[3]:.2f} "
          f"(its bottom at y {a.get('cloud_height', 192.33)})")
    print("  ladder (dressed stone, brightness setting 50%):")
    for name, c in sorted(ladder(a, stone, glass), key=lambda row: _luma(row[1])):
        c = np.clip(c, 0.0, 1.0)
        print(f"    {_hex(c)}  {_luma(c):.2f}  {name}")


def plan_looks(stone, glass):
    from scenes.obs.sky import mood
    for name in mood.LOOKS:
        a = {k: gamelook.colour(x) if isinstance(x, str) and x.startswith("#") else x for k, x in mood.values(name).items()}
        print(f"\n==== the plan's look {name} (time {mood.tick(name)}), for comparison")
        print(f"    {mood.look(name)['zenith']}  {_luma(gamelook.colour(mood.look(name)['zenith'])):.2f}  overhead")
        print(f"    {mood.look(name)['horizon']}  {_luma(gamelook.colour(mood.look(name)['horizon'])):.2f}  horizon")
        for row, c in sorted(ladder(a, stone, glass), key=lambda r: _luma(r[1])):
            c = np.clip(c, 0.0, 1.0)
            print(f"    {_hex(c)}  {_luma(c):.2f}  {row}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="the sky without a registry file: hours, colours, the ladder")
    ap.add_argument("--jar", default=JAR)
    ap.add_argument("--biome", default="plains", help="a vanilla biome's name (default plains)")
    ap.add_argument("--chunks", type=int, default=12, help="the player's view distance (default 12)")
    ap.add_argument("--head", type=float, default=41.0, help="degrees the comet's head is to stand above due west")
    ap.add_argument("--at", default="", help="hours of the clock to report, comma separated")
    ap.add_argument("--scan", action="store_true", help="the night in steps: bodies, sky, fog, light, stars")
    ap.add_argument("--plan", action="store_true", help="the plan's own three looks beside it")
    args = ap.parse_args(argv)
    v = Vanilla(args.jar)

    from scenes.obs.common.palette import RAMPS
    stone, glass = gamelook.colour(RAMPS["ashlar"][3]), gamelook.colour(RAMPS["glow"][2])

    print(f"the comet's head {args.head:g} degrees above due west; the moon's square reaches {MOON_HALF:.1f} "
          f"degrees from its middle, the sun's {SUN_HALF:.1f}")
    print("  head painted          middle of the square   moon_angle   time set   (angle there)   the sun then")
    for label, below in (("7 below the middle", 7.0), ("on the middle", 0.0), ("7 above the middle", -7.0)):
        angle = 90.0 - (args.head + below)
        tick, got = lock(v, angle)
        a = v.at(tick, {})
        sun = float(a["sun_angle"]) % 360.0
        print(f"  {label:<21} {args.head + below:>6.1f} up              {angle:>6.1f}     {tick:>6}      {got:>7.2f}       "
              f"{abs(sun - 270.0) if sun > 180 else sun - 90.0:.1f} below the {'eastern' if sun > 180 else 'western'} horizon")

    if args.scan:
        biome = v.biome(args.biome)
        print(f"\nthe night, biome minecraft:{args.biome} (sky and fog are what the attributes hold, before the mixing):")
        print("    hour   moon up  side   sun up  side   sky      fog      cloud    sky light       stars  glow (side)")
        for tick in list(range(11800, 14401, 200)) + list(range(15000, 21001, 1000)) + list(range(21400, 24001, 200)):
            a = v.at(tick, biome)
            cells = []
            for name in ("moon", "sun"):
                angle = float(a[f"{name}_angle"]) % 360.0
                cells.append(f"{90.0 - angle if angle <= 180.0 else angle - 270.0:>+7.1f}  {'west' if angle <= 180.0 else 'east'}")
            glow = a["sunrise_sunset_color"]
            side = "west" if math.sin(math.radians(float(a["sun_angle"]))) > 0.0 else "east"
            print(f"  {tick:>6}  {cells[0]}  {cells[1]}   {_hex(a['sky_color'])}  {_hex(a['fog_color'])}  "
                  f"{_hex(a['cloud_color'])}  {_hex(a['sky_light_color'])} {a['sky_light_factor']:.2f}   "
                  f"{a['star_brightness']:.2f}   {_hex(glow)} {glow[3]:.2f} ({side})")

    for text in [t for t in args.at.split(",") if t.strip()]:
        report(v, int(text), args.biome, args.chunks, stone, glass)
    if args.plan:
        plan_looks(stone, glass)


if __name__ == "__main__":
    main()
