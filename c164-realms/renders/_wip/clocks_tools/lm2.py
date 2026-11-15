"""The light table at the map's hour for the pairs (sky, block) a ledge of the ball could be given."""
import importlib, os, sys
import numpy as np
BUILD = "/agent/repos/c164-clocks-f3-00d6/c164-realms/build"
sys.path.insert(0, BUILD)
os.chdir(BUILD)
import render
from artkit import gamelook
from artkit.gameassets import Assets
jar = "/agent/realms-study/client26/versions/26.3/26.3.jar"
assets = Assets(jar, [])
DATA = render.DATA
mod = importlib.import_module("scenes.obs_mach_clocks")
look_mod = importlib.import_module("scenes.obs_mach_clocks.mood")
biome = look_mod.BIOMES[getattr(mod, "BIOME", sorted(look_mod.BIOMES)[0])]
dimension = assets.json(f"{DATA}dimension_type/overworld.json")
lines = render.timelines(assets) + [look_mod.TIMELINES[k] for k in sorted(getattr(look_mod, "TIMELINES", {}))]
look = gamelook.Look(14000, dimension, biome, lines)
lm = look.lightmap
C601 = np.array([0.299, 0.587, 0.114])
def hexc(c):
    return "#%02x%02x%02x" % tuple(int(round(max(0, min(1, v)) * 255)) for v in c)
for s, b in ((0, 12), (0, 13), (0, 14), (0, 15), (12, 12), (13, 13), (14, 14), (15, 15)):
    c = lm[s, b]
    print(f"sky {s:2d} block {b:2d}: {hexc(c)} luma {c @ C601:.3f}  rgb {np.round(c, 3)}")
np.save("/tmp/c164_clocks/lm.npy", np.asarray(lm))
