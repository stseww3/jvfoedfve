"""Custom models for the star hall test scene: none yet.

The stand-in machines and fittings (stubs.py) are all blocks, so there are no item-display models to
pack. When c179's props and A5's machines arrive they bring their own build_models(); this scene
then imports and merges them. makepack.py / render.py call build_models(), so it must exist.
"""


def build_models():
    return {}
