"""The light table of the map's hour: what a white enamel reads on an east face of a display entity."""
import importlib, os, sys
import numpy as np
BUILD = "/agent/repos/c164-clocks-f3-00d6/c164-realms/build"
sys.path.insert(0, BUILD)
os.chdir(BUILD)
import render
from artkit import gamelook
from artkit.gameassets import Assets
ROOT = render.ROOT
jar = os.path.join(ROOT, "client26", "versions", "26.3", "26.3.jar")
if not os.path.exists(jar):
    jar = "/agent/realms-study/client26/versions/26.3/26.3.jar"
print("jar", os.path.exists(jar))
assets = Assets(jar, [])
DATA = render.DATA
scene = sys.argv[1] if len(sys.argv) > 1 else "obs_mach_clocks"
mod = importlib.import_module(f"scenes.{scene}")
look_mod = importlib.import_module(f"scenes.{scene}.mood")
biome = look_mod.BIOMES[getattr(mod, "BIOME", sorted(look_mod.BIOMES)[0])]
dimension = assets.json(f"{DATA}dimension_type/overworld.json")
lines = render.timelines(assets) + [look_mod.TIMELINES[k] for k in sorted(getattr(look_mod, "TIMELINES", {}))]
look = gamelook.Look(14000, dimension, biome, lines)
lm = look.lightmap
C601 = np.array([0.299, 0.587, 0.114])
def hexc(c):
    return "#%02x%02x%02x" % tuple(int(round(max(0, min(1, v)) * 255)) for v in c)
white = np.array([0xf2, 0xea, 0xd6]) / 255.0
EW = 0.4 + 0.6 * (0.2 / np.linalg.norm([0.2, 1.0, 0.7]))
print("east face of a display entity:", round(float(EW), 4))
for s in (0, 4, 8, 15):
    for b in range(7, 16):
        c = lm[s, b]
        e = white * c * EW
        print(f"sky {s:2d} block {b:2d}: table {hexc(c)} luma {c @ C601:.3f}   enamel on east face {hexc(e)} {e @ C601:.3f}   unshaded {white * c @ C601:.3f}")
    print()
