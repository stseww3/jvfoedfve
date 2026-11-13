"""The one palette of the observatory (plan/ART-PLAN.md, section 3.1).

Every texture of the map, on blocks and on models alike, takes its colours from here and nowhere
else, so that a cast-iron bracket hangs on a cast-iron wall without a seam in colour.

    from scenes.obs.common.palette import RAMPS, mat, colour, strays

    RAMPS["iron"]            hex colours, dark to light
    colour("iron", 3)        one step as (r, g, b); negative indices count from the light end
    mat("iron")              the artkit.pixelart.Mat that paints a surface of that material
    mat("iron", bevel=0)     the same with another way of painting; the colours cannot be changed
    strays(pixels)           colours of a painted picture that are not in the palette (should be none)

A0 keeps this file. A new colour or another default for a material is asked for in the group.
"""
import numpy as np

from artkit.pixelart import Mat, hx

RAMPS = {
    # plan 3.1
    "ashlar": ("#847f77", "#a09a8e", "#b7b0a1", "#c8c1b0", "#d6cfbf", "#e2dccd"),               # warm grey-white stone
    "iron": ("#12151a", "#1b2027", "#252b34", "#303844", "#414b59", "#5d6877", "#8591a0"),      # cast iron, blue-black
    "verdigris": ("#2f6f5c", "#3d8a70", "#4fa487", "#6dbb9c", "#93d3b6"),                       # oxidized copper
    "old_copper": ("#5e4636", "#7c5f4c", "#9b7a65", "#b3937c", "#c9ab94"),                      # dull brown copper
    "brass": ("#5a3c12", "#7a551a", "#9c7424", "#bf9433", "#dcb650", "#f3d98a"),
    "dark_wood": ("#2c1d10", "#3a2716", "#4a331d", "#5b4025", "#6c4d2e"),
    "glow": ("#c96a1c", "#f09a2e", "#ffc65a", "#ffe9a6", "#fff8dc"),                            # filament amber: the one light colour
    "phosphor": ("#0f3d2c", "#1c7a55", "#3fd08d", "#8dffc4", "#e3fff0"),                        # instruments only
    "signal": ("#5e1410", "#a3201a", "#e8402e", "#ff8a6a"),                                     # warnings only
    "enamel": ("#0f1e3d", "#172c57", "#1f3a6e", "#2e4f8f"),                                     # enamel blue
    "cream": ("#a59f92", "#c6c0af", "#dfd7c5", "#f2ead6"),                                      # the plan's #f2ead6 and its shades
    # the vanilla deepslate family, for model parts that stand on or against it
    "slate": ("#242424", "#2d2d2d", "#383737", "#414141", "#4b4c4f", "#585858", "#6e6e6e"),
    # added when the parts' designs were reviewed (2026-11-13)
    "night_glass": ("#141a36", "#1c2548", "#27335f", "#3a4a80", "#5a6ea8"),                     # dark windows holding the sky
    "porcelain": ("#7b7d77", "#a2a49d", "#c6c7c0", "#e2e3dc", "#f5f5ef"),                       # insulators, fuses, dials
    "opal": ("#bfae8c", "#dccba6", "#f0e2c0", "#fbf2d8", "#fffbee"),                            # lit opal glass, frosted windows
}

# name: (ramp, how it is painted). Names without an entry here are painted "plain" with the defaults.
_MATS = {
    "ashlar": ("ashlar", dict(kind="plain", noise=0.25, bevel=1, base=3)),
    "iron": ("iron", dict(kind="metal", noise=0.14, bevel=1, base=3)),
    "iron_dark": ("iron", dict(kind="metal", noise=0.12, bevel=1, base=2)),
    "iron_flat": ("iron", dict(kind="flat", bevel=0, base=2)),
    "verdigris": ("verdigris", dict(kind="metal", noise=0.22, bevel=1, base=2)),
    "old_copper": ("old_copper", dict(kind="metal", noise=0.18, bevel=1, base=2)),
    "brass": ("brass", dict(kind="metal", noise=0.16, bevel=1, base=3)),
    "brass_dark": ("brass", dict(kind="metal", noise=0.14, bevel=1, base=1)),
    "brass_flat": ("brass", dict(kind="flat", bevel=0, base=2)),
    "dark_wood": ("dark_wood", dict(kind="wood", bevel=1, base=2)),
    "glow": ("glow", dict(kind="glow", bevel=0, base=2)),
    "phosphor": ("phosphor", dict(kind="glow", bevel=0, base=2)),
    "signal": ("signal", dict(kind="metal", noise=0.10, bevel=1, base=1)),        # painted red: handwheels
    "signal_glow": ("signal", dict(kind="glow", bevel=0, base=2)),                # red lamps
    "enamel": ("enamel", dict(kind="plain", noise=0.06, bevel=1, base=2)),
    "cream": ("cream", dict(kind="plain", noise=0.10, bevel=0, base=3)),          # paper, enamel white
    "cream_cloth": ("cream", dict(kind="cloth", bevel=0, base=2)),                # canvas, flags
    "enamel_cloth": ("enamel", dict(kind="cloth", bevel=0, base=2)),
    "slate": ("slate", dict(kind="plain", noise=0.30, bevel=1, base=3)),
    "night_glass": ("night_glass", dict(kind="plain", noise=0.08, bevel=0, base=1)),
    "porcelain": ("porcelain", dict(kind="plain", noise=0.05, bevel=1, base=3)),
    "opal": ("opal", dict(kind="glow", bevel=0, base=2)),
}
_CHANGEABLE = {"kind", "noise", "bevel", "base", "alpha"}
_cache = {}


def colour(name, step):
    """One colour of a ramp as (r, g, b)."""
    return hx(RAMPS[name][step])


def mat(name, **changes):
    """The material called `name`. Keyword arguments change how it is painted (kind, noise, bevel,
    base, alpha), never which colours it has; the same request returns the same object."""
    if name not in _MATS:
        raise KeyError(f"no material {name!r}; there are: {', '.join(sorted(_MATS))}")
    odd = set(changes) - _CHANGEABLE
    if odd:
        raise TypeError(f"mat() cannot change {', '.join(sorted(odd))}")
    key = (name, tuple(sorted(changes.items())))
    if key not in _cache:
        ramp, how = _MATS[name]
        how = dict(how, **changes)
        label = name + "".join(f"~{k}{v}" for k, v in sorted(changes.items()))
        _cache[key] = Mat(label, RAMPS[ramp], **how)
    return _cache[key]


def names():
    return sorted(_MATS)


def strays(pixels):
    """The colours of an RGB or RGBA picture that are in no ramp; fully transparent pixels are skipped.
    Returns {(r, g, b): count}. A picture made for this map should give an empty result."""
    a = np.asarray(pixels)
    rgb = a[..., :3].reshape(-1, 3)
    if a.shape[-1] == 4:
        rgb = rgb[a[..., 3].reshape(-1) > 0]
    allowed = {hx(c) for ramp in RAMPS.values() for c in ramp}
    out = {}
    cols, counts = np.unique(rgb, axis=0, return_counts=True)
    for c, n in zip(cols, counts):
        c = tuple(int(v) for v in c)
        if c not in allowed:
            out[c] = int(n)
    return out
