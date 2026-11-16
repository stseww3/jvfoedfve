"""No biome and no timeline: the data pack of a Realms map holds no registry files. The look is in
the resource pack's shaders (scenes/obs/sky/_shaders.py).

The scene's BIOME is one of the game's own (minecraft:the_void). place.py takes an id with a
namespace as it stands; check.py asks whether the look knows the name, so the empty table says yes
to the game's ids (until check.py has place.py's rule: asked of s2, 11-16)."""


class _GameBiomes(dict):
    def __contains__(self, name):
        return isinstance(name, str) and name.startswith("minecraft:")


BIOMES = _GameBiomes()
TIMELINES = {}
